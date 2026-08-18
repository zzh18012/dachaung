"""evaluation/annotation_metrics.py 第五百八十六轮 edges 测试（Round 1289）。

补强 edges154 未触及的角度（第六百六十一批，probe 实证）。

新角度（mc100 晶格几何）：
- **mc100 边界系**——6 块 → 预测
  边界 [80, 174, 270, 366,
  462] 共 5 条 → P 分母 5
  （0.2，区别于 mc32 的
  1/15）
- **d 值谱**——W3 after d 28
  （tol 27/28 翻转）、W10
  d 16（15/16）、W30 d 48
  （47/48）、W59 d 88
  （87/88，末锚远距首锁）
- **HEAD before d 80 跨 mc
  不变**——tol 80 恰中
  （与 mc32 完全同值；流首
  几何与分块粒度解耦首锁）
- **F1 浮点痕**——单中
  F1 == 0.33333333333333337
- **双锚**——W3+W10 tol 60
  → P 0.4 / R 1.0 / F1
  0.5714285714285715
- forbidden tokens 第七百四十八批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
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
    p = tmp_path / "combo.pdf"
    p.write_bytes(_wrap(s))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=100)
    assert errors == []
    return doc.to_dict()


def _prf(dd, pairs, tol):
    r = chunk_boundary_prf(dd, {"chunk_boundary_anchors": [
        {"marker": m, "position": pos} for m, pos in pairs]}, tol)
    return tuple(r[k]["value"] for k in (
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1"))


ZERO = (0.0, 0.0, 0.0)
ONE5 = (1 / 5, 1.0, 0.33333333333333337)


# ---------- mc100 边界系 ----------

def test_mc100_chunks_six_batch487(tmp_path):
    assert len(_doc(tmp_path)["chunks"]) == 6


def test_p_denominator_five_batch487(tmp_path):
    assert _prf(_doc(tmp_path), [("Word10.", "after")],
                16) == ONE5


def test_f1_third_float_batch487(tmp_path):
    assert _prf(_doc(tmp_path), [("Word10.", "after")],
                16)[2] == 0.33333333333333337


# ---------- W3 d 28 ----------

def test_w3_tol27_miss_batch487(tmp_path):
    assert _prf(_doc(tmp_path), [("Word3.", "after")],
                27) == ZERO


def test_w3_tol28_hit_batch487(tmp_path):
    assert _prf(_doc(tmp_path), [("Word3.", "after")],
                28) == ONE5


# ---------- W10 d 16 ----------

def test_w10_tol15_miss_batch487(tmp_path):
    assert _prf(_doc(tmp_path), [("Word10.", "after")],
                15) == ZERO


def test_w10_tol16_hit_batch487(tmp_path):
    assert _prf(_doc(tmp_path), [("Word10.", "after")],
                16) == ONE5


# ---------- W30 d 48 ----------

def test_w30_tol47_miss_batch487(tmp_path):
    assert _prf(_doc(tmp_path), [("Word30.", "after")],
                47) == ZERO


def test_w30_tol48_hit_batch487(tmp_path):
    assert _prf(_doc(tmp_path), [("Word30.", "after")],
                48) == ONE5


# ---------- W59 d 88 ----------

def test_w59_tol87_miss_batch487(tmp_path):
    assert _prf(_doc(tmp_path), [("Word59.", "after")],
                87) == ZERO


def test_w59_tol88_hit_batch487(tmp_path):
    assert _prf(_doc(tmp_path), [("Word59.", "after")],
                88) == ONE5


# ---------- HEAD before d 80 跨 mc 不变 ----------

def test_head_before_tol79_miss_batch487(tmp_path):
    assert _prf(_doc(tmp_path), [(HEAD, "before")],
                79) == ZERO


def test_head_before_tol80_hit_batch487(tmp_path):
    assert _prf(_doc(tmp_path), [(HEAD, "before")],
                80) == ONE5


# ---------- 双锚 ----------

def test_dual_anchors_two_fifths_batch487(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Word3.", "after"), ("Word10.", "after")],
                60) == (0.4, 1.0, 0.5714285714285715)


def test_tol0_zero_batch487(tmp_path):
    assert _prf(_doc(tmp_path), [("Word3.", "after")],
                0) == ZERO


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch487():
    src = _src()
    assert "d = abs(pv - gv)" in src
    assert "if d <= tolerance_chars:" in src


# ---------- forbidden tokens 第七百四十八批 ----------

def test_source_no_eval_batch487():
    assert "eval(" not in _src()


def test_source_no_exec_batch487():
    assert "exec(" not in _src()


def test_source_no_compile_batch487():
    assert "compile(" not in _src()


def test_source_no_globals_batch487():
    assert "globals(" not in _src()


def test_source_no_locals_batch487():
    assert "locals(" not in _src()


def test_source_no_os_system_batch487():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch487():
    assert "subprocess" not in _src()


def test_source_no_popen_batch487():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch487():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch487():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch487():
    assert "socket" not in _src()


def test_source_no_requests_batch487():
    assert "requests" not in _src()


def test_source_no_urllib_batch487():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch487():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch487():
    assert "yield" not in _src()


def test_source_no_async_await_batch487():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch487():
    assert "open(" not in _src()
