"""evaluation/annotation_metrics.py 第五百九十七轮 edges 测试（Round 1354）。

补强 edges165 未触及的角度（第七百二十六批，probe 实证）。

新角度（无点前缀 marker 族 / 前缀吞并）：
- **无点单锚**——
  'Word5'（无句点）
  → {1/14, 1.0,
  2/15}（与带点
  'Word5.' 同 trio
  首锁）
- **Word50 前缀**
  ——'Word50' 单锚
  同 trio
- **无点重复**——
  ['Word5','Word5']
  → {2/14, 1.0,
  4/15}（第二锚落
  Word50 前缀内仍
  命中）
- **顺序不敏感**——
  [Word50,Word5]
  与 [Word5,Word50]
  同 trio
- **永不 missing**
  ——前缀族全部
  _missing_markers
  缺席
- forbidden tokens 第七百九十四批（open 0）
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import evaluation.annotation_metrics as am_mod
from app.pipeline import process_single
from evaluation.annotation_metrics import \
    chunk_boundary_prf


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
ONEP = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
        % LONG).encode()

HIT14 = ({"value": 1 / 14, "reason": None},
         {"value": 1.0, "reason": None},
         {"value": 2 / 15, "reason": None})
DUP = ({"value": 2 / 14, "reason": None},
       {"value": 1.0, "reason": None},
       {"value": 0.25, "reason": None})


def _doc():
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "c.pdf").write_bytes(_wrap(ONEP))
        doc, errors = process_single(
            tp / "c.pdf", tp / "o.json",
            parser_name="fallback", max_chars=32)
        assert errors == []
        return doc.to_dict()


def _trio(doc, markers):
    anchors = [{"marker": m, "position": "after"}
               for m in markers]
    r = chunk_boundary_prf(doc, {
        "annotation_version": "1.0",
        "doc_id": "g",
        "chunk_boundary_anchors": anchors}, 30)
    return r


# ---------- 无点单锚 ----------

def test_dotless_word5_single_batch552():
    r = _trio(_doc(), ["Word5"])
    assert (r["chunk_boundary_precision"],
            r["chunk_boundary_recall"],
            r["chunk_boundary_f1"]) == HIT14


def test_dotless_word50_single_batch552():
    r = _trio(_doc(), ["Word50"])
    assert (r["chunk_boundary_precision"],
            r["chunk_boundary_recall"],
            r["chunk_boundary_f1"]) == HIT14


def test_dotted_equals_dotless_batch552():
    doc = _doc()
    dotted = _trio(doc, ["Word5."])
    dotless = _trio(doc, ["Word5"])
    assert (dotted["chunk_boundary_precision"],
            dotted["chunk_boundary_recall"],
            dotted["chunk_boundary_f1"]) == (
        dotless["chunk_boundary_precision"],
        dotless["chunk_boundary_recall"],
        dotless["chunk_boundary_f1"])


# ---------- 无点重复 ----------

def test_dotless_duplicate_pair_batch552():
    r = _trio(_doc(), ["Word5", "Word5"])
    assert (r["chunk_boundary_precision"],
            r["chunk_boundary_recall"],
            r["chunk_boundary_f1"]) == DUP


def test_dotless_dup_p_two_fourteenths_batch552():
    r = _trio(_doc(), ["Word5", "Word5"])
    assert r["chunk_boundary_precision"] == {
        "value": 2 / 14, "reason": None}


def test_dotless_dup_f1_quarter_batch552():
    r = _trio(_doc(), ["Word5", "Word5"])
    assert r["chunk_boundary_f1"] == {
        "value": 0.25, "reason": None}


# ---------- 顺序不敏感 ----------

def test_order_word50_first_batch552():
    r = _trio(_doc(), ["Word50", "Word5"])
    assert (r["chunk_boundary_precision"],
            r["chunk_boundary_recall"],
            r["chunk_boundary_f1"]) == DUP


def test_order_word5_first_batch552():
    r = _trio(_doc(), ["Word5", "Word50"])
    assert (r["chunk_boundary_precision"],
            r["chunk_boundary_recall"],
            r["chunk_boundary_f1"]) == DUP


def test_order_insensitive_equality_batch552():
    doc = _doc()
    a = _trio(doc, ["Word50", "Word5"])
    b = _trio(doc, ["Word5", "Word50"])
    assert a == b


# ---------- 永不 missing ----------

def test_dotless_single_no_missing_batch552():
    r = _trio(_doc(), ["Word5"])
    assert "_missing_markers" not in r


def test_dotless_dup_no_missing_batch552():
    r = _trio(_doc(), ["Word5", "Word5"])
    assert "_missing_markers" not in r


def test_mixed_order_no_missing_batch552():
    doc = _doc()
    for markers in (["Word50", "Word5"],
                    ["Word5", "Word50"]):
        assert "_missing_markers" not in \
            _trio(doc, markers)


# ---------- 输出面 ----------

def test_key_set_four_batch552():
    r = _trio(_doc(), ["Word5"])
    assert sorted(r.keys()) == [
        "_tolerance_chars", "chunk_boundary_f1",
        "chunk_boundary_precision",
        "chunk_boundary_recall"]


def test_tolerance_echo_batch552():
    r = chunk_boundary_prf(_doc(), {
        "annotation_version": "1.0",
        "doc_id": "g",
        "chunk_boundary_anchors": [
            {"marker": "Word5",
             "position": "after"}]}, 11)
    assert r["_tolerance_chars"] == {
        "value": 11, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_search_from_advance_batch552():
    src = _src()
    assert "search_from = find_pos + len(marker)" \
        in src


def test_source_literal_find_batch552():
    assert "if marker else -1" in _src()


# ---------- forbidden tokens 第七百九十四批 ----------

def test_source_no_eval_batch552():
    assert "eval(" not in _src()


def test_source_no_exec_batch552():
    assert "exec(" not in _src()


def test_source_no_compile_batch552():
    assert "compile(" not in _src()


def test_source_no_globals_batch552():
    assert "globals(" not in _src()


def test_source_no_locals_batch552():
    assert "locals(" not in _src()


def test_source_no_os_system_batch552():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch552():
    assert "subprocess" not in _src()


def test_source_no_popen_batch552():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch552():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch552():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch552():
    assert "socket" not in _src()


def test_source_no_requests_batch552():
    assert "requests" not in _src()


def test_source_no_urllib_batch552():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch552():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch552():
    assert "yield" not in _src()


def test_source_no_async_await_batch552():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_0_batch552():
    assert _src().count("open(") == 0
