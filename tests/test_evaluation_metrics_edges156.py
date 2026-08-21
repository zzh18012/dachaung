"""evaluation/metrics.py 第五百七十七轮 edges 测试（Round 1326）。

补强 edges155 未触及的角度（第六百九十八批，probe 实证）。

新角度（篡改 doc dict 的保真失败几何）：
- **corrupt chunk text**——
  chunk0 text 换
  'XXX corrupted.' →
  tpe {False, None}
  （真板首次翻 False
  首锁）
- **tcmp 0.9693**——
  字符多重集精度
  0.9692671394799054
  （80 字符 chunk 被换
  14 字符垃圾的精确值
  首锁）
- **tcmr 0.8367**——
  字符多重集召回
  0.8367346938775511
- **crir 15/16**——
  单 chunk sei 换
  不存在 id →
  {0.9375, None}
- **空 sei 同罪**——
  [] 与坏 id 等价
  0.9375（metrics 层
  不做 schema 拒绝，
  只算比率首锁）
- **双坏 14/16**——
  首+末两 chunk 各坏
  → {0.875, None}
- **baseline 全绿**——
  未篡改 tpe/tcmp/
  tcmr/crir 全满
- forbidden tokens 第七百七十一批（open 0）
"""

from __future__ import annotations

import copy
import inspect
import tempfile
from pathlib import Path

import evaluation.metrics as metrics_mod
from app.pipeline import process_single
from evaluation.metrics import \
    compute_automatic_metrics


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
COMBO = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
         % ("A" * 80)
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()


def _base():
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "c.pdf").write_bytes(_wrap(COMBO))
        doc, errors = process_single(
            tp / "c.pdf", tp / "o.json",
            parser_name="fallback", max_chars=32)
        assert errors == []
        return doc.to_dict()


def _m(dd):
    return compute_automatic_metrics(dd, None, "pdf",
                                     None)


# ---------- baseline 全绿 ----------

def test_baseline_all_green_batch524():
    m = _m(copy.deepcopy(_base()))
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}


def test_board_geometry_batch524():
    b = _base()
    assert len(b["chunks"]) == 16
    assert len(b["elements"]) == 2


# ---------- corrupt chunk text ----------

def test_corrupt_text_tpe_false_batch524():
    d = copy.deepcopy(_base())
    d["chunks"][0]["text"] = "XXX corrupted."
    assert _m(d)["text_preservation_equal"] == {
        "value": False, "reason": None}


def test_corrupt_text_tcmp_batch524():
    d = copy.deepcopy(_base())
    d["chunks"][0]["text"] = "XXX corrupted."
    assert _m(d)[
        "text_char_multiset_precision"] == {
        "value": 0.9692671394799054,
        "reason": None}


def test_corrupt_text_tcmr_batch524():
    d = copy.deepcopy(_base())
    d["chunks"][0]["text"] = "XXX corrupted."
    assert _m(d)[
        "text_char_multiset_recall"] == {
        "value": 0.8367346938775511,
        "reason": None}


# ---------- crir 坏引用 ----------

def test_bad_ref_crir_fifteen_sixteenths_batch524():
    d = copy.deepcopy(_base())
    d["chunks"][0][
        "source_element_ids"] = ["nonexistent-id"]
    assert _m(d)[
        "chunk_reference_intact_ratio"] == {
        "value": 0.9375, "reason": None}


def test_empty_sei_same_as_bad_batch524():
    d_bad = copy.deepcopy(_base())
    d_bad["chunks"][0][
        "source_element_ids"] = ["nonexistent-id"]
    d_empty = copy.deepcopy(_base())
    d_empty["chunks"][0]["source_element_ids"] = []
    assert (_m(d_bad)[
        "chunk_reference_intact_ratio"]
        == _m(d_empty)[
            "chunk_reference_intact_ratio"]
        == {"value": 0.9375, "reason": None})


def test_two_bad_refs_batch524():
    d = copy.deepcopy(_base())
    n = len(d["chunks"])
    d["chunks"][0][
        "source_element_ids"] = ["nonexistent-id"]
    d["chunks"][n - 1][
        "source_element_ids"] = ["also-bad"]
    assert _m(d)[
        "chunk_reference_intact_ratio"] == {
        "value": 0.875, "reason": None}


# ---------- 其他指标不受文本篡改扰动 ----------

def test_corrupt_text_schema_valid_stays_batch524():
    d = copy.deepcopy(_base())
    d["chunks"][0]["text"] = "XXX corrupted."
    assert _m(d)["schema_valid"] == {
        "value": True, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch524():
    src = _src()
    assert ('_PDF_BBOX_REQUIRED_TYPES = ('
            '"heading", "paragraph", '
            '"caption", "list_item")') in src
    assert "drops += (exp - actual)" in src


# ---------- forbidden tokens 第七百七十一批 ----------

def test_source_no_eval_batch524():
    assert "eval(" not in _src()


def test_source_no_exec_batch524():
    assert "exec(" not in _src()


def test_source_no_compile_batch524():
    assert "compile(" not in _src()


def test_source_no_globals_batch524():
    assert "globals(" not in _src()


def test_source_no_locals_batch524():
    assert "locals(" not in _src()


def test_source_no_os_system_batch524():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch524():
    assert "subprocess" not in _src()


def test_source_no_popen_batch524():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch524():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch524():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch524():
    assert "socket" not in _src()


def test_source_no_requests_batch524():
    assert "requests" not in _src()


def test_source_no_urllib_batch524():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch524():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch524():
    assert "yield" not in _src()


def test_source_no_async_await_batch524():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_0_batch524():
    assert _src().count("open(") == 0
