"""evaluation/annotation_metrics.py 第五百八十五轮 edges 测试（Round 1283）。

补强 edges153 未触及的角度（第六百五十五批，probe 实证）。

新角度（before 位句包格 / 混位竞争）：
- **pack 始 d 1 律**——W0/W4/W8
  before 起点均恰在界 +1 →
  tol 0 全漏 / tol 1 全中
  （包始统一 d 1 首锁）
- **流首远锚**——heading before
  起点 0 距界 80 恰 80 →
  tol 79 漏 / 80 中
- **W59 before d 25**——
  tol 24 漏 / 25 中（末包始）
- **混位竞争**——W3 after +
  W4 before 同争界 108 →
  tol 0/1 仅 W3 中 P 1/15 /
  R 0.5 / F1 2/17；tol 27 起
  W4 回退界 136 (d 27) 双中
- forbidden tokens 第七百四十二批（open 0）
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


def _prf(dd, pairs, tol):
    r = chunk_boundary_prf(dd, {"chunk_boundary_anchors": [
        {"marker": m, "position": pos} for m, pos in pairs]}, tol)
    return tuple(r[k]["value"] for k in (
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1"))


ONE15 = (1 / 15, 1.0, 0.125)
ZERO = (0.0, 0.0, 0.0)


# ---------- pack 始 d 1 律 ----------

def test_w0_before_tol0_miss_batch481(tmp_path):
    assert _prf(_doc(tmp_path), [("Word0.", "before")],
                0) == ZERO


def test_w0_before_tol1_hit_batch481(tmp_path):
    assert _prf(_doc(tmp_path), [("Word0.", "before")],
                1) == ONE15


def test_w4_before_tol0_miss_batch481(tmp_path):
    assert _prf(_doc(tmp_path), [("Word4.", "before")],
                0) == ZERO


def test_w4_before_tol1_hit_batch481(tmp_path):
    assert _prf(_doc(tmp_path), [("Word4.", "before")],
                1) == ONE15


def test_w8_before_tol0_miss_batch481(tmp_path):
    assert _prf(_doc(tmp_path), [("Word8.", "before")],
                0) == ZERO


def test_w8_before_tol1_hit_batch481(tmp_path):
    assert _prf(_doc(tmp_path), [("Word8.", "before")],
                1) == ONE15


def test_w0_w4_before_dual_batch481(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Word0.", "before"), ("Word4.", "before")],
                1) == (2 / 15, 1.0, 0.23529411764705882)


# ---------- 流首远锚 ----------

def test_head_before_tol79_miss_batch481(tmp_path):
    assert _prf(_doc(tmp_path), [(HEAD, "before")],
                79) == ZERO


def test_head_before_tol80_hit_batch481(tmp_path):
    assert _prf(_doc(tmp_path), [(HEAD, "before")],
                80) == ONE15


# ---------- W59 before d 25 ----------

def test_w59_before_tol24_miss_batch481(tmp_path):
    assert _prf(_doc(tmp_path), [("Word59.", "before")],
                24) == ZERO


def test_w59_before_tol25_hit_batch481(tmp_path):
    assert _prf(_doc(tmp_path), [("Word59.", "before")],
                25) == ONE15


# ---------- 混位竞争 ----------

MIXED = [(("Word3.", "after"), ("Word4.", "before"))]


def test_mixed_tol0_single_batch481(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Word3.", "after"), ("Word4.", "before")],
                0) == (1 / 15, 0.5, 2 / 17)


def test_mixed_tol1_still_single_batch481(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Word3.", "after"), ("Word4.", "before")],
                1) == (1 / 15, 0.5, 2 / 17)


def test_mixed_tol27_both_batch481(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Word3.", "after"), ("Word4.", "before")],
                27) == (2 / 15, 1.0, 0.23529411764705882)


def test_mixed_tol28_both_batch481(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Word3.", "after"), ("Word4.", "before")],
                28) == (2 / 15, 1.0, 0.23529411764705882)


def test_mixed_recall_flip_batch481(tmp_path):
    dd = _doc(tmp_path)
    assert _prf(dd, [("Word3.", "after"),
                     ("Word4.", "before")], 26)[1] == 0.5
    assert _prf(dd, [("Word3.", "after"),
                     ("Word4.", "before")], 27)[1] == 1.0


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch481():
    src = _src()
    assert "d = abs(pv - gv)" in src
    assert "if d <= tolerance_chars:" in src


# ---------- forbidden tokens 第七百四十二批 ----------

def test_source_no_eval_batch481():
    assert "eval(" not in _src()


def test_source_no_exec_batch481():
    assert "exec(" not in _src()


def test_source_no_compile_batch481():
    assert "compile(" not in _src()


def test_source_no_globals_batch481():
    assert "globals(" not in _src()


def test_source_no_locals_batch481():
    assert "locals(" not in _src()


def test_source_no_os_system_batch481():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch481():
    assert "subprocess" not in _src()


def test_source_no_popen_batch481():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch481():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch481():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch481():
    assert "socket" not in _src()


def test_source_no_requests_batch481():
    assert "requests" not in _src()


def test_source_no_urllib_batch481():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch481():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch481():
    assert "yield" not in _src()


def test_source_no_async_await_batch481():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch481():
    assert "open(" not in _src()
