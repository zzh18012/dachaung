"""evaluation/metrics.py 第五百六十七轮 edges 测试（Round 1266）。

补强 edges145 未触及的角度（第六百三十八批，probe 实证）。

新角度（混排板 mc 99/98/32 三档翻转 / 元素原子过冲）：
- **mc 99 恰容**——99 字符合并块
  == max_chars → 2 块 [29, 99]
  （≤ 含等号首锁）
- **mc 98 翻转**——heading 80 +
  para 18 = 99 > 98 → flush →
  3 块 [29, 80, 18] srcs [1,1,1]
- **mc 32 原子过冲**——heading
  单元素 80 > 32，元素不可拆 →
  80 字符块过冲 48（块形同 mc98
  首锁）
- **指标跨 mc 不变**——ecbt /
  hbc / tpe / multiset / intact
  在 99/98/32 三档全同值
- **para 精确 18 字符**
- forbidden tokens 第七百二十七批（open 0）
"""

from __future__ import annotations

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


MIX_TEXTS = ["Figure 1 An overview diagram.", "A" * 80,
             "Is this a heading?"]


def _doc(tmp_path, mc):
    from app.pipeline import process_single
    ys = [700, 660, 620]
    s = "".join("BT /F1 12 Tf 10 %d Td (%s) Tj ET\n" % (y, t)
                for y, t in zip(ys, MIX_TEXTS)).encode()
    p = tmp_path / "mix.pdf"
    p.write_bytes(_wrap(s))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=mc)
    assert errors == []
    return doc.to_dict()


def _m(tmp_path, mc):
    return compute_automatic_metrics(
        _doc(tmp_path, mc), None, "pdf", None)


# ---------- mc 99 恰容 ----------

def test_mc99_two_chunks_batch464(tmp_path):
    dd = _doc(tmp_path, 99)
    assert len(dd["chunks"]) == 2
    assert [len(c["text"]) for c in dd["chunks"]] == [29, 99]


def test_mc99_sequential_two_srcs_batch464(tmp_path):
    dd = _doc(tmp_path, 99)
    c1 = dd["chunks"][1]
    assert c1["metadata"]["strategy"] == "sequential"
    assert len(c1["source_element_ids"]) == 2


def test_mc99_exact_fit_batch464(tmp_path):
    dd = _doc(tmp_path, 99)
    assert len(dd["chunks"][1]["text"]) == 99


# ---------- mc 98 翻转 ----------

def test_mc98_three_chunks_batch464(tmp_path):
    assert len(_doc(tmp_path, 98)["chunks"]) == 3


def test_mc98_lens_batch464(tmp_path):
    assert [len(c["text"]) for c in _doc(tmp_path, 98)["chunks"]] \
        == [29, 80, 18]


def test_mc98_all_single_srcs_batch464(tmp_path):
    assert [len(c["source_element_ids"])
            for c in _doc(tmp_path, 98)["chunks"]] == [1, 1, 1]


def test_mc98_strategies_batch464(tmp_path):
    assert [c["metadata"]["strategy"]
            for c in _doc(tmp_path, 98)["chunks"]] == [
        "isolated_caption", "sequential", "sequential"]


# ---------- mc 32 原子过冲 ----------

def test_mc32_same_shape_as_98_batch464(tmp_path):
    assert [len(c["text"]) for c in _doc(tmp_path, 32)["chunks"]] \
        == [29, 80, 18]


def test_mc32_overshoot_48_batch464(tmp_path):
    dd = _doc(tmp_path, 32)
    heading_chunk = len(dd["chunks"][1]["text"])
    assert heading_chunk == 80
    assert heading_chunk - 32 == 48


def test_mc32_all_single_srcs_batch464(tmp_path):
    assert [len(c["source_element_ids"])
            for c in _doc(tmp_path, 32)["chunks"]] == [1, 1, 1]


# ---------- para 精确长度 ----------

def test_para_element_len_18_batch464(tmp_path):
    dd = _doc(tmp_path, 99)
    assert dd["elements"][2]["content"] == "Is this a heading?"
    assert len(dd["elements"][2]["content"]) == 18


# ---------- 指标跨 mc 不变 ----------

def test_ecbt_invariant_batch464(tmp_path):
    expected = {"value": {"caption": 1, "heading": 1,
                          "paragraph": 1}, "reason": None}
    for mc in (99, 98, 32):
        assert _m(tmp_path, mc)["element_count_by_type"] == expected


def test_hbc_invariant_batch464(tmp_path):
    expected = {"value": 1.0, "reason": None}
    for mc in (99, 98, 32):
        assert _m(tmp_path, mc)[
            "heading_boundary_compliance"] == expected


def test_tpe_multiset_invariant_batch464(tmp_path):
    for mc in (99, 98, 32):
        m = _m(tmp_path, mc)
        assert m["text_preservation_equal"] == {
            "value": True, "reason": None}
        assert m["text_char_multiset_precision"] == {
            "value": 1.0, "reason": None}
        assert m["text_char_multiset_recall"] == {
            "value": 1.0, "reason": None}


def test_intact_invariant_batch464(tmp_path):
    for mc in (99, 98, 32):
        assert _m(tmp_path, mc)[
            "chunk_reference_intact_ratio"] == {
            "value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch464():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", ' \
           '"paragraph", "caption", "list_item")' in src
    assert 'if e.get("type") == "heading"' in src


# ---------- forbidden tokens 第七百二十七批 ----------

def test_source_no_eval_batch464():
    assert "eval(" not in _src()


def test_source_no_exec_batch464():
    assert "exec(" not in _src()


def test_source_no_compile_batch464():
    assert "compile(" not in _src()


def test_source_no_globals_batch464():
    assert "globals(" not in _src()


def test_source_no_locals_batch464():
    assert "locals(" not in _src()


def test_source_no_os_system_batch464():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch464():
    assert "subprocess" not in _src()


def test_source_no_popen_batch464():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch464():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch464():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch464():
    assert "socket" not in _src()


def test_source_no_requests_batch464():
    assert "requests" not in _src()


def test_source_no_urllib_batch464():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch464():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch464():
    assert "yield" not in _src()


def test_source_no_async_await_batch464():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch464():
    assert "open(" not in _src()
