"""evaluation/annotation_metrics.py 第五百八十三轮 edges 测试（Round 1271）。

补强 edges151 未触及的角度（第六百四十三批，probe 实证）。

新角度（mc98 双界竞争 / d1 微翻转）：
- **双界板**——3 块 [29, 80, 18]
  → 2 界 29/110（流仍 129）
- **para before d 1**——para 始
  111 距界 110 恰 1 → tol 0 漏 /
  tol 1 中（P 0.5 / R 1.0 / F1
  2/3，双界分母 2 首锁）
- **para after mc 翻转**——尾
  129 距界 110 恰 19 → tol 30 命
  中（mc200 时 d 100 漏——同板
  翻转首锁）
- **heading/para 竞争同界**——
  heading d 0 与 para d 1 争界
  110 → heading 胜、para 无界
  可配 → P 0.5 / R 0.5 / F1 0.5
  （贪心近距离优先竞争首锁）
- **三锚全配**——cap 29 +
  heading 110 + para 无 →
  P 1.0 / R 2/3 / F1 0.8
- forbidden tokens 第七百三十一批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
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


MIX_TEXTS = ["Figure 1 An overview diagram.", "A" * 80,
             "Is this a heading?"]

CAP = "Figure 1 An overview diagram."
HEAD = "A" * 80
PARA = "Is this a heading?"


def _doc(tmp_path):
    from app.pipeline import process_single
    ys = [700, 660, 620]
    s = "".join("BT /F1 12 Tf 10 %d Td (%s) Tj ET\n" % (y, t)
                for y, t in zip(ys, MIX_TEXTS)).encode()
    p = tmp_path / "mix.pdf"
    p.write_bytes(_wrap(s))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=98)
    assert errors == []
    return doc.to_dict()


def _ann(*pairs):
    return {"chunk_boundary_anchors": [
        {"marker": m, "position": pos} for m, pos in pairs]}


def _prf(dd, pairs, tol):
    r = chunk_boundary_prf(dd, _ann(*pairs), tol)
    return {k: r[k]["value"] for k in (
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1")}


# ---------- 双界板几何 ----------

def test_two_boundaries_batch469(tmp_path):
    dd = _doc(tmp_path)
    joined = " ".join(c["text"] for c in dd["chunks"])
    assert len(joined) == 129
    assert [len(c["text"]) for c in dd["chunks"]] == [29, 80, 18]
    b1 = len(dd["chunks"][0]["text"])
    b2 = b1 + 1 + len(dd["chunks"][1]["text"])
    assert (b1, b2) == (29, 110)


def test_para_before_d1_batch469(tmp_path):
    dd = _doc(tmp_path)
    joined = " ".join(c["text"] for c in dd["chunks"])
    para_start = joined.index(PARA)
    assert para_start == 111
    assert abs(para_start - 110) == 1


def test_para_after_d19_batch469(tmp_path):
    dd = _doc(tmp_path)
    joined = " ".join(c["text"] for c in dd["chunks"])
    para_end = joined.index(PARA) + len(PARA)
    assert para_end == 129
    assert abs(para_end - 110) == 19


# ---------- 单锚 ----------

def test_para_before_tol0_miss_batch469(tmp_path):
    assert _prf(_doc(tmp_path), [(PARA, "before")], 0) == {
        "chunk_boundary_precision": 0.0,
        "chunk_boundary_recall": 0.0,
        "chunk_boundary_f1": 0.0}


HALF_P = {
    "chunk_boundary_precision": 0.5,
    "chunk_boundary_recall": 1.0,
    "chunk_boundary_f1": 0.6666666666666666}


def test_para_before_tol1_hit_batch469(tmp_path):
    assert _prf(_doc(tmp_path), [(PARA, "before")], 1) == HALF_P


def test_heading_after_tol0_batch469(tmp_path):
    assert _prf(_doc(tmp_path), [(HEAD, "after")], 0) == HALF_P


def test_para_after_tol30_hit_batch469(tmp_path):
    assert _prf(_doc(tmp_path), [(PARA, "after")], 30) == HALF_P


# ---------- 竞争同界 ----------

def test_cap_para_all_one_batch469(tmp_path):
    assert _prf(_doc(tmp_path),
                [(CAP, "after"), (PARA, "before")], 1) == {
        "chunk_boundary_precision": 1.0,
        "chunk_boundary_recall": 1.0,
        "chunk_boundary_f1": 1.0}


def test_heading_para_competition_batch469(tmp_path):
    assert _prf(_doc(tmp_path),
                [(HEAD, "after"), (PARA, "before")], 1) == {
        "chunk_boundary_precision": 0.5,
        "chunk_boundary_recall": 0.5,
        "chunk_boundary_f1": 0.5}


# ---------- 三锚 ----------

ALL_THREE = {
    "chunk_boundary_precision": 1.0,
    "chunk_boundary_recall": 0.6666666666666666,
    "chunk_boundary_f1": 0.8}


def test_all_three_tol1_batch469(tmp_path):
    assert _prf(_doc(tmp_path),
                [(CAP, "after"), (HEAD, "after"),
                 (PARA, "before")], 1) == ALL_THREE


def test_all_three_tol30_batch469(tmp_path):
    assert _prf(_doc(tmp_path),
                [(CAP, "after"), (HEAD, "after"),
                 (PARA, "before")], 30) == ALL_THREE


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch469():
    src = _src()
    assert "d = abs(pv - gv)" in src
    assert "if d <= tolerance_chars:" in src


# ---------- forbidden tokens 第七百三十一批 ----------

def test_source_no_eval_batch469():
    assert "eval(" not in _src()


def test_source_no_exec_batch469():
    assert "exec(" not in _src()


def test_source_no_compile_batch469():
    assert "compile(" not in _src()


def test_source_no_globals_batch469():
    assert "globals(" not in _src()


def test_source_no_locals_batch469():
    assert "locals(" not in _src()


def test_source_no_os_system_batch469():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch469():
    assert "subprocess" not in _src()


def test_source_no_popen_batch469():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch469():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch469():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch469():
    assert "socket" not in _src()


def test_source_no_requests_batch469():
    assert "requests" not in _src()


def test_source_no_urllib_batch469():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch469():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch469():
    assert "yield" not in _src()


def test_source_no_async_await_batch469():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch469():
    assert "open(" not in _src()
