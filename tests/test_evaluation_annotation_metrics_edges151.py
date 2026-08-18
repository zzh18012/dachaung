"""evaluation/annotation_metrics.py 第五百八十二轮 edges 测试（Round 1265）。

补强 edges150 未触及的角度（第六百三十七批，probe 实证）。

新角度（隔离 caption 界几何 / 81 距翻转）：
- **caption 恰界 d 0**——
  isolated_caption 独块 → 块界 29
  == caption 尾 29 → after 锚
  tol 0 全 1.0（隔离型恰界首锁，
  对照 mc45 标题独块）
- **before d 29 翻转**——before
  → 位 0，|0−29| = 29 → tol 28 漏 /
  tol 29 全中
- **heading 内嵌 d 81 翻转**——
  heading 在块 1 内部，尾 110，
  |110−29| = 81 → tol 80 漏 /
  tol 81 全中
- **para 前后双 miss**——after
  尾 129 = 流尾不成界；before 始
  111，d 82 → 均漏
- **双锚半配**——caption+heading
  → P 1.0 / R 0.5 / F1 2/3（tol
  0 与 30 同值，唯一界被 caption
  消耗）
- forbidden tokens 第七百二十六批（open 0）
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


def _doc(tmp_path):
    from app.pipeline import process_single
    ys = [700, 660, 620]
    s = "".join("BT /F1 12 Tf 10 %d Td (%s) Tj ET\n" % (y, t)
                for y, t in zip(ys, MIX_TEXTS)).encode()
    p = tmp_path / "mix.pdf"
    p.write_bytes(_wrap(s))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=200)
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


# ---------- 界几何 ----------

def test_geometry_lengths_batch463(tmp_path):
    dd = _doc(tmp_path)
    joined = " ".join(c["text"] for c in dd["chunks"])
    assert len(joined) == 129
    assert [len(c["text"]) for c in dd["chunks"]] == [29, 99]


def test_geometry_cap_exact_boundary_batch463(tmp_path):
    dd = _doc(tmp_path)
    joined = " ".join(c["text"] for c in dd["chunks"])
    boundary = len(dd["chunks"][0]["text"])
    cap_end = joined.index("Figure 1 An overview diagram.") \
        + len("Figure 1 An overview diagram.")
    assert boundary == 29
    assert cap_end == 29


def test_geometry_heading_d81_batch463(tmp_path):
    dd = _doc(tmp_path)
    joined = " ".join(c["text"] for c in dd["chunks"])
    heading_end = joined.index("A" * 80) + 80
    assert heading_end == 110
    assert abs(heading_end - 29) == 81


def test_geometry_para_d82_batch463(tmp_path):
    dd = _doc(tmp_path)
    joined = " ".join(c["text"] for c in dd["chunks"])
    para_start = joined.index("Is this a heading?")
    assert para_start == 111
    assert abs(para_start - 29) == 82


# ---------- caption 恰界 d 0 ----------

def test_cap_after_tol0_all_one_batch463(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Figure 1 An overview diagram.", "after")],
                0) == {
        "chunk_boundary_precision": 1.0,
        "chunk_boundary_recall": 1.0,
        "chunk_boundary_f1": 1.0}


def test_cap_after_tol29_all_one_batch463(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Figure 1 An overview diagram.", "after")],
                29) == {
        "chunk_boundary_precision": 1.0,
        "chunk_boundary_recall": 1.0,
        "chunk_boundary_f1": 1.0}


# ---------- before d 29 翻转 ----------

def test_cap_before_tol28_miss_batch463(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Figure 1 An overview diagram.", "before")],
                28) == {
        "chunk_boundary_precision": 0.0,
        "chunk_boundary_recall": 0.0,
        "chunk_boundary_f1": 0.0}


def test_cap_before_tol29_hit_batch463(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Figure 1 An overview diagram.", "before")],
                29) == {
        "chunk_boundary_precision": 1.0,
        "chunk_boundary_recall": 1.0,
        "chunk_boundary_f1": 1.0}


# ---------- heading 内嵌 d 81 翻转 ----------

def test_heading_after_tol80_miss_batch463(tmp_path):
    assert _prf(_doc(tmp_path), [("A" * 80, "after")], 80) == {
        "chunk_boundary_precision": 0.0,
        "chunk_boundary_recall": 0.0,
        "chunk_boundary_f1": 0.0}


def test_heading_after_tol81_hit_batch463(tmp_path):
    assert _prf(_doc(tmp_path), [("A" * 80, "after")], 81) == {
        "chunk_boundary_precision": 1.0,
        "chunk_boundary_recall": 1.0,
        "chunk_boundary_f1": 1.0}


# ---------- para 前后双 miss ----------

def test_para_after_miss_batch463(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Is this a heading?", "after")], 30) == {
        "chunk_boundary_precision": 0.0,
        "chunk_boundary_recall": 0.0,
        "chunk_boundary_f1": 0.0}


def test_para_before_miss_batch463(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Is this a heading?", "before")], 30) == {
        "chunk_boundary_precision": 0.0,
        "chunk_boundary_recall": 0.0,
        "chunk_boundary_f1": 0.0}


# ---------- 双锚半配 ----------

HALF = {
    "chunk_boundary_precision": 1.0,
    "chunk_boundary_recall": 0.5,
    "chunk_boundary_f1": 0.6666666666666666}


def test_cap_heading_tol0_half_batch463(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Figure 1 An overview diagram.", "after"),
                 ("A" * 80, "after")], 0) == HALF


def test_cap_heading_tol30_half_batch463(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Figure 1 An overview diagram.", "after"),
                 ("A" * 80, "after")], 30) == HALF


def test_cap_before_heading_tol30_half_batch463(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Figure 1 An overview diagram.", "before"),
                 ("A" * 80, "after")], 30) == HALF


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch463():
    src = _src()
    assert "d = abs(pv - gv)" in src
    assert "if d <= tolerance_chars:" in src


# ---------- forbidden tokens 第七百二十六批 ----------

def test_source_no_eval_batch463():
    assert "eval(" not in _src()


def test_source_no_exec_batch463():
    assert "exec(" not in _src()


def test_source_no_compile_batch463():
    assert "compile(" not in _src()


def test_source_no_globals_batch463():
    assert "globals(" not in _src()


def test_source_no_locals_batch463():
    assert "locals(" not in _src()


def test_source_no_os_system_batch463():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch463():
    assert "subprocess" not in _src()


def test_source_no_popen_batch463():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch463():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch463():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch463():
    assert "socket" not in _src()


def test_source_no_requests_batch463():
    assert "requests" not in _src()


def test_source_no_urllib_batch463():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch463():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch463():
    assert "yield" not in _src()


def test_source_no_async_await_batch463():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch463():
    assert "open(" not in _src()
