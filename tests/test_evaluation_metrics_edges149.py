"""evaluation/metrics.py 第五百七十轮 edges 测试（Round 1284）。

补强 edges148 未触及的角度（第六百五十六批，probe 实证）。

新角度（单字符编辑三分不对称 / 悬空引用分数）：
- **替换单字符**——首块 'B'+79A →
  msp == msr == 0.9979591836734694
  （双双微降首锁）
- **删单字符**——80A→79A →
  msp 1.0 / msr 0.9979591836734694
  （仅召回降首锁）
- **增单字符**——80A→81A →
  msp 0.9979633401221996 / msr 1.0
  （仅精度降，且值 ≠ 删侧召回
  ——分母不同首锁）
- **tpe 三变异全 False**
- **悬空引用分数**——16 块悬
  1 → 15/16=0.9375；悬 2 →
  14/16=0.875（真板分母 16
  分数首锁）
- forbidden tokens 第七百四十三批（open 0）
"""

from __future__ import annotations

import copy
import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _wrap(s: bytes) -> bytes:
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xp = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


LONG = " ".join("Word%d." % i for i in range(60))
HEAD = "A" * 80


def _doc(tmp_path):
    from app.pipeline import process_single
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()
    p = tmp_path / "combo.pdf"
    p.write_bytes(_wrap(s))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=32)
    assert errors == []
    return doc.to_dict()


def _m(base, fn):
    d = copy.deepcopy(base)
    fn(d)
    return compute_automatic_metrics(d, None, "pdf", None)


# ---------- 基态 ----------

def test_base_all_one_batch482(tmp_path):
    m = _m(_doc(tmp_path), lambda d: None)
    assert m["chunk_reference_intact_ratio"]["value"] == 1.0
    assert m["text_char_multiset_precision"]["value"] == 1.0
    assert m["text_char_multiset_recall"]["value"] == 1.0


# ---------- 替换单字符 ----------

def test_replace_both_drop_batch482(tmp_path):
    m = _m(_doc(tmp_path), lambda d: d["chunks"][0].update(
        {"text": "B" + "A" * 79}))
    assert m["text_char_multiset_precision"]["value"] == \
        0.9979591836734694
    assert m["text_char_multiset_recall"]["value"] == \
        0.9979591836734694


def test_replace_tpe_false_batch482(tmp_path):
    m = _m(_doc(tmp_path), lambda d: d["chunks"][0].update(
        {"text": "B" + "A" * 79}))
    assert m["text_preservation_equal"] == {
        "value": False, "reason": None}


# ---------- 删单字符 ----------

def test_drop_recall_only_batch482(tmp_path):
    m = _m(_doc(tmp_path), lambda d: d["chunks"][0].update(
        {"text": "A" * 79}))
    assert m["text_char_multiset_precision"]["value"] == 1.0
    assert m["text_char_multiset_recall"]["value"] == \
        0.9979591836734694


def test_drop_tpe_false_batch482(tmp_path):
    m = _m(_doc(tmp_path), lambda d: d["chunks"][0].update(
        {"text": "A" * 79}))
    assert m["text_preservation_equal"]["value"] is False


# ---------- 增单字符 ----------

def test_add_precision_only_batch482(tmp_path):
    m = _m(_doc(tmp_path), lambda d: d["chunks"][0].update(
        {"text": "A" * 81}))
    assert m["text_char_multiset_precision"]["value"] == \
        0.9979633401221996
    assert m["text_char_multiset_recall"]["value"] == 1.0


def test_add_drop_values_differ_batch482(tmp_path):
    base = _doc(tmp_path)
    drop_r = _m(base, lambda d: d["chunks"][0].update(
        {"text": "A" * 79}))["text_char_multiset_recall"][
        "value"]
    add_p = _m(base, lambda d: d["chunks"][0].update(
        {"text": "A" * 81}))["text_char_multiset_precision"][
        "value"]
    assert drop_r != add_p


def test_add_tpe_false_batch482(tmp_path):
    m = _m(_doc(tmp_path), lambda d: d["chunks"][0].update(
        {"text": "A" * 81}))
    assert m["text_preservation_equal"]["value"] is False


# ---------- 悬空引用分数 ----------

def test_dangle_one_15_16_batch482(tmp_path):
    m = _m(_doc(tmp_path), lambda d: d["chunks"][3].update(
        {"source_element_ids": ["doc-x::zzz"]}))
    assert m["chunk_reference_intact_ratio"]["value"] == \
        15 / 16
    assert m["chunk_reference_intact_ratio"]["value"] == \
        0.9375


def _dangle2(d):
    d["chunks"][3].update(
        {"source_element_ids": ["doc-x::zzz"]})
    d["chunks"][7].update(
        {"source_element_ids": ["doc-x::yyy"]})


def test_dangle_two_14_16_batch482(tmp_path):
    m = _m(_doc(tmp_path), _dangle2)
    assert m["chunk_reference_intact_ratio"]["value"] == \
        14 / 16
    assert m["chunk_reference_intact_ratio"]["value"] == \
        0.875


def test_dangle_no_text_effect_batch482(tmp_path):
    m = _m(_doc(tmp_path), lambda d: d["chunks"][3].update(
        {"source_element_ids": ["doc-x::zzz"]}))
    assert m["text_preservation_equal"]["value"] is True
    assert m["text_char_multiset_precision"]["value"] == 1.0


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch482():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", ' \
           '"paragraph", "caption", "list_item")' in src
    assert 'if e.get("type") == "heading"' in src


# ---------- forbidden tokens 第七百四十三批 ----------

def test_source_no_eval_batch482():
    assert "eval(" not in _src()


def test_source_no_exec_batch482():
    assert "exec(" not in _src()


def test_source_no_compile_batch482():
    assert "compile(" not in _src()


def test_source_no_globals_batch482():
    assert "globals(" not in _src()


def test_source_no_locals_batch482():
    assert "locals(" not in _src()


def test_source_no_os_system_batch482():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch482():
    assert "subprocess" not in _src()


def test_source_no_popen_batch482():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch482():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch482():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch482():
    assert "socket" not in _src()


def test_source_no_requests_batch482():
    assert "requests" not in _src()


def test_source_no_urllib_batch482():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch482():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch482():
    assert "yield" not in _src()


def test_source_no_async_await_batch482():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch482():
    assert "open(" not in _src()
