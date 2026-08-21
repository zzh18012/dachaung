"""evaluation/annotation_metrics.py 第五百八十八轮 edges 测试（Round 1301）。

补强 edges156 未触及的角度（第六百七十三批，probe 实证）。

新角度（多 token marker / 规范化敏感）：
- **双 token marker 跨界**——
  "Word3. Word4." gt after =
  115，最近预测 108 落在
  marker 区间 [102,115] 内
  → d 7：tol 7 中 / tol 6 三
  0.0（界内匹配首锁）
- **before/after 翻转不对称**
  ——同 marker：before gt
  102（d 6）翻转点 6；
  after gt 115（d 7）翻转点
  7（position 语义平移 gt
  marker 长 13 的几何首锁）
- **三 token marker**——
  "Word3. Word4. Word5."
  gt 121 → 最近 108 d 13 →
  tol 30 中（marker 长于界
  间距仍取最近）
- **规范化敏感**——双空格 /
  tab marker → 流中不可寻
  （normalize 压单空格）→
  _missing_markers + cbr
  no_ground_truth_anchors_
  in_stream + cbf precision_
  or_recall_not_evaluated
  （文本在而形不在首锁）
- **容忍与大小写**——前导
  空格 marker 命中（流内邻
  空格）；小写 marker →
  missing（find 大小写敏感）
- forbidden tokens 第七百五十批（open 0）
"""

from __future__ import annotations

import inspect

from app.chunkers.structural import normalize_text
from app.pipeline import process_single
from evaluation.annotation_metrics import chunk_boundary_prf


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
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()
    p = tmp_path / "c.pdf"
    p.write_bytes(_wrap(s))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=32)
    assert errors == []
    return doc.to_dict()


def _vals(dd, marker, position, tol):
    r = chunk_boundary_prf(
        dd, {"chunk_boundary_anchors": [
            {"marker": marker, "position": position}]},
        tolerance_chars=tol)
    missing = r.pop("_missing_markers", None)
    r.pop("_tolerance_chars", None)
    vals = (r["chunk_boundary_precision"]["value"],
            r["chunk_boundary_recall"]["value"],
            r["chunk_boundary_f1"]["value"])
    return vals, (missing or {}).get("value")


HIT = (1 / 15, 1.0, 0.125)
ZERO = (0.0, 0.0, 0.0)
M2 = "Word3. Word4."


# ---------- 双 token marker 跨界 ----------

def test_stream_segment_batch499(tmp_path):
    dd = _doc(tmp_path)
    norm_chunks = [normalize_text(c.get("text") or "")
                   for c in dd["chunks"]]
    stream = normalize_text(" ".join(norm_chunks))
    assert stream[100:120] == ". Word3. Word4. Word"


def test_after_tol7_hit_batch499(tmp_path):
    vals, missing = _vals(_doc(tmp_path), M2, "after", 7)
    assert vals == HIT
    assert missing is None


def test_after_tol6_zero_batch499(tmp_path):
    vals, _ = _vals(_doc(tmp_path), M2, "after", 6)
    assert vals == ZERO


def test_after_tol30_hit_batch499(tmp_path):
    vals, _ = _vals(_doc(tmp_path), M2, "after", 30)
    assert vals == HIT


# ---------- before/after 翻转不对称 ----------

def test_before_tol6_hit_batch499(tmp_path):
    vals, _ = _vals(_doc(tmp_path), M2, "before", 6)
    assert vals == HIT


def test_before_tol5_zero_batch499(tmp_path):
    vals, _ = _vals(_doc(tmp_path), M2, "before", 5)
    assert vals == ZERO


def test_flip_asymmetry_batch499(tmp_path):
    dd = _doc(tmp_path)
    vals_b6, _ = _vals(dd, M2, "before", 6)
    vals_a6, _ = _vals(dd, M2, "after", 6)
    assert vals_b6 == HIT and vals_a6 == ZERO


# ---------- 三 token marker ----------

def test_three_token_tol30_batch499(tmp_path):
    vals, missing = _vals(
        _doc(tmp_path), "Word3. Word4. Word5.", "after",
        30)
    assert vals == HIT
    assert missing is None


def test_three_token_tol12_zero_batch499(tmp_path):
    vals, _ = _vals(
        _doc(tmp_path), "Word3. Word4. Word5.", "after",
        12)
    assert vals == ZERO


# ---------- 规范化敏感 ----------

def test_double_space_missing_batch499(tmp_path):
    vals, missing = _vals(
        _doc(tmp_path), "Word3.  Word4.", "after", 30)
    assert missing == ["Word3.  Word4."]
    assert vals == (0.0, None, None)


def test_double_space_full_trio_batch499(tmp_path):
    dd = _doc(tmp_path)
    r = chunk_boundary_prf(
        dd, {"chunk_boundary_anchors": [
            {"marker": "Word3.  Word4.",
             "position": "after"}]}, tolerance_chars=30)
    assert r["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert r["chunk_boundary_f1"] == {
        "value": None,
        "reason": "precision_or_recall_not_evaluated"}


def test_tab_marker_missing_batch499(tmp_path):
    _, missing = _vals(
        _doc(tmp_path), "Word3.\tWord4.", "after", 30)
    assert missing == ["Word3.\tWord4."]


# ---------- 容忍与大小写 ----------

def test_leading_space_marker_found_batch499(tmp_path):
    vals, missing = _vals(
        _doc(tmp_path), " Word3.", "after", 30)
    assert vals == HIT
    assert missing is None


def test_lowercase_marker_missing_batch499(tmp_path):
    vals, missing = _vals(
        _doc(tmp_path), "word3.", "after", 30)
    assert missing == ["word3."]
    assert vals == (0.0, None, None)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(
        __import__("evaluation.annotation_metrics",
                   fromlist=["x"]))


def test_source_key_lines_batch499():
    src = _src()
    assert "d = abs(pv - gv)" in src
    assert "if d <= tolerance_chars:" in src
    assert "stream.find(marker, search_from)" in src


# ---------- forbidden tokens 第七百五十批 ----------

def test_source_no_eval_batch499():
    assert "eval(" not in _src()


def test_source_no_exec_batch499():
    assert "exec(" not in _src()


def test_source_no_compile_batch499():
    assert "compile(" not in _src()


def test_source_no_globals_batch499():
    assert "globals(" not in _src()


def test_source_no_locals_batch499():
    assert "locals(" not in _src()


def test_source_no_os_system_batch499():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch499():
    assert "subprocess" not in _src()


def test_source_no_popen_batch499():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch499():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch499():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch499():
    assert "socket" not in _src()


def test_source_no_requests_batch499():
    assert "requests" not in _src()


def test_source_no_urllib_batch499():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch499():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch499():
    assert "yield" not in _src()


def test_source_no_async_await_batch499():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_0_batch499():
    assert _src().count("open(") == 0
