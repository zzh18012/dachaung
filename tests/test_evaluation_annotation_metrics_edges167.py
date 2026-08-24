"""evaluation/annotation_metrics.py 第五百九十八轮 edges 测试（Round 1360）。

补强 edges166 未触及的角度（第七百三十二批，probe 实证）。

新角度（词位-容差等差阶梯）：
- **7 字符步进**
  ——"Word%d. "
  每词 7 字符 →
  词尾到块边界距离
  0/7/14/21
  等差（probe 二分
  实证）
- **最小命中容差**
  ——Word3. 需
  tol 0、Word2.
  需 7、Word1.
  需 14、Word0.
  需 21
- **锐利边界**
  ——tol 6 拒 /
  tol 7 收（无
  中间态）
- **模式复现**
  ——每块末词
  （Word3./
  Word7./
  Word11.）均
  tol 0 命中
- forbidden tokens 第七百九十九批（open 0）
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
ZERO = ({"value": 0.0, "reason": None},
        {"value": 0.0, "reason": None},
        {"value": 0.0, "reason": None})


def _doc():
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "c.pdf").write_bytes(_wrap(ONEP))
        doc, errors = process_single(
            tp / "c.pdf", tp / "o.json",
            parser_name="fallback", max_chars=32)
        assert errors == []
        return doc.to_dict()


def _trio(doc, marker, tol):
    r = chunk_boundary_prf(doc, {
        "annotation_version": "1.0",
        "doc_id": "g",
        "chunk_boundary_anchors": [
            {"marker": marker,
             "position": "after"}]}, tol)
    return (r["chunk_boundary_precision"],
            r["chunk_boundary_recall"],
            r["chunk_boundary_f1"])


def _min_tol(doc, marker):
    for tol in range(0, 40):
        if _trio(doc, marker, tol) == HIT14:
            return tol
    return None


# ---------- 7 字符步进 ----------

def test_word3_min_tol_zero_batch558():
    assert _min_tol(_doc(), "Word3.") == 0


def test_word2_min_tol_seven_batch558():
    assert _min_tol(_doc(), "Word2.") == 7


def test_word1_min_tol_fourteen_batch558():
    assert _min_tol(_doc(), "Word1.") == 14


def test_word0_min_tol_twentyone_batch558():
    assert _min_tol(_doc(), "Word0.") == 21


def test_ladder_arithmetic_batch558():
    doc = _doc()
    tols = [_min_tol(doc, "Word%d." % i)
            for i in range(4)]
    assert tols == [21, 14, 7, 0]


def test_step_is_wordlen_batch558():
    assert len("Word0. ") == 7
    doc = _doc()
    assert (_min_tol(doc, "Word1.")
            - _min_tol(doc, "Word2.")) == 7


# ---------- 锐利边界 ----------

def test_word2_tol6_miss_batch558():
    assert _trio(_doc(), "Word2.", 6) == ZERO


def test_word2_tol7_hit_batch558():
    assert _trio(_doc(), "Word2.", 7) == HIT14


def test_word1_tol13_miss_batch558():
    assert _trio(_doc(), "Word1.", 13) == ZERO


def test_word1_tol14_hit_batch558():
    assert _trio(_doc(), "Word1.", 14) == HIT14


def test_word0_tol20_miss_batch558():
    assert _trio(_doc(), "Word0.", 20) == ZERO


def test_word0_tol21_hit_batch558():
    assert _trio(_doc(), "Word0.", 21) == HIT14


# ---------- 单调性 ----------

def test_word2_monotone_batch558():
    doc = _doc()
    assert _trio(doc, "Word2.", 7) == HIT14
    assert _trio(doc, "Word2.", 8) == HIT14
    assert _trio(doc, "Word2.", 30) == HIT14


def test_miss_below_hit_at_or_above_batch558():
    doc = _doc()
    for m, t in (("Word2.", 7), ("Word1.", 14),
                 ("Word0.", 21)):
        assert _trio(doc, m, t - 1) == ZERO
        assert _trio(doc, m, t) == HIT14


# ---------- 模式复现（每块末词） ----------

def test_word7_min_tol_zero_batch558():
    assert _min_tol(_doc(), "Word7.") == 0


def test_word11_min_tol_zero_batch558():
    assert _min_tol(_doc(), "Word11.") == 0


def test_word6_min_tol_seven_batch558():
    assert _min_tol(_doc(), "Word6.") == 7


def test_word55_min_tol_zero_batch558():
    assert _min_tol(_doc(), "Word55.") == 0


def test_last_words_all_zero_tol_batch558():
    doc = _doc()
    for w in ("Word3.", "Word7.", "Word11.",
              "Word15.", "Word19."):
        assert _trio(doc, w, 0) == HIT14


# ---------- 几何基础 ----------

def test_chunk_text_four_words_batch558():
    doc = _doc()
    assert doc["chunks"][0]["text"] == \
        "Word0. Word1. Word2. Word3."
    assert doc["chunks"][1]["text"] == \
        "Word4. Word5. Word6. Word7."


def test_chunk_count_fifteen_batch558():
    assert len(_doc()["chunks"]) == 15


def test_far_word_never_hits_low_batch558():
    doc = _doc()
    assert _trio(doc, "Word0.", 6) == ZERO
    assert _trio(doc, "Word1.", 6) == ZERO


# ---------- tolerance 回显 ----------

def test_tol_echo_in_result_batch558():
    r = chunk_boundary_prf(_doc(), {
        "annotation_version": "1.0",
        "doc_id": "g",
        "chunk_boundary_anchors": [
            {"marker": "Word2.",
             "position": "after"}]}, 7)
    assert r["_tolerance_chars"] == {
        "value": 7, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_find_advance_batch558():
    assert "find_pos + len(marker)" in _src()


def test_source_tolerance_compare_batch558():
    src = _src()
    assert "<= tolerance" in src


# ---------- forbidden tokens 第七百九十九批 ----------

def test_source_no_eval_batch558():
    assert "eval(" not in _src()


def test_source_no_exec_batch558():
    assert "exec(" not in _src()


def test_source_no_compile_batch558():
    assert "compile(" not in _src()


def test_source_no_globals_batch558():
    assert "globals(" not in _src()


def test_source_no_locals_batch558():
    assert "locals(" not in _src()


def test_source_no_os_system_batch558():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch558():
    assert "subprocess" not in _src()


def test_source_no_popen_batch558():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch558():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch558():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch558():
    assert "socket" not in _src()


def test_source_no_requests_batch558():
    assert "requests" not in _src()


def test_source_no_urllib_batch558():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch558():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch558():
    assert "yield" not in _src()


def test_source_no_async_await_batch558():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_0_batch558():
    assert _src().count("open(") == 0
