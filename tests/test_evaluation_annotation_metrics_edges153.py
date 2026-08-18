"""evaluation/annotation_metrics.py 第五百八十四轮 edges 测试（Round 1277）。

补强 edges152 未触及的角度（第六百四十九批，probe 实证）。

新角度（句包格 tol 微翻转谱 / 回退阈值）：
- **d 谱翻转点**——W0/W2 d 7、
  W1 d 14、W13 d 16、W59 d 32
  各自 tol-1 漏 / tol 恰中（五点
  翻转谱首锁，d 32 为最宽）
- **d 0 格心**——heading 与
  Word3 tol 0 即中（模 4 格心）
- **双锚竞争**——W2+W3 tol 0/7
  均 P 1/15 / R 0.5 / F1 2/17
  （Word3 抢界 108 后 W2 无人配）
- **回退阈值 tol 21**——W2 第二
  近界 80 距 21 → tol 21 双中
  P 2/15 / R 1.0（R 0.5→1.0 单点
  翻转首锁）
- forbidden tokens 第七百三十七批（open 0）
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


# ---------- d 谱翻转点 ----------

def test_w0_tol6_miss_batch475(tmp_path):
    assert _prf(_doc(tmp_path), [("Word0.", "after")], 6) == ZERO


def test_w0_tol7_hit_batch475(tmp_path):
    assert _prf(_doc(tmp_path), [("Word0.", "after")], 7) == ONE15


def test_w2_tol6_miss_batch475(tmp_path):
    assert _prf(_doc(tmp_path), [("Word2.", "after")], 6) == ZERO


def test_w2_tol7_hit_batch475(tmp_path):
    assert _prf(_doc(tmp_path), [("Word2.", "after")], 7) == ONE15


def test_w1_tol13_miss_batch475(tmp_path):
    assert _prf(_doc(tmp_path), [("Word1.", "after")], 13) == ZERO


def test_w1_tol14_hit_batch475(tmp_path):
    assert _prf(_doc(tmp_path), [("Word1.", "after")], 14) == ONE15


def test_w13_tol15_miss_batch475(tmp_path):
    assert _prf(_doc(tmp_path), [("Word13.", "after")], 15) == ZERO


def test_w13_tol16_hit_batch475(tmp_path):
    assert _prf(_doc(tmp_path), [("Word13.", "after")], 16) == ONE15


def test_w59_tol31_miss_batch475(tmp_path):
    assert _prf(_doc(tmp_path), [("Word59.", "after")], 31) == ZERO


def test_w59_tol32_hit_batch475(tmp_path):
    assert _prf(_doc(tmp_path), [("Word59.", "after")], 32) == ONE15


# ---------- d 0 格心 ----------

def test_heading_tol0_hit_batch475(tmp_path):
    assert _prf(_doc(tmp_path), [(HEAD, "after")], 0) == ONE15


def test_w3_tol0_hit_batch475(tmp_path):
    assert _prf(_doc(tmp_path), [("Word3.", "after")], 0) == ONE15


def test_three_tol0_batch475(tmp_path):
    assert _prf(_doc(tmp_path),
                [(m, "after") for m in (
                    "Word3.", "Word7.", "Word11.")], 0) == (
        0.2, 1.0, 0.33333333333333337)


# ---------- 双锚竞争 ----------

COMPETE = (1 / 15, 0.5, 2 / 17)


def test_w2w3_tol0_compete_batch475(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Word2.", "after"), ("Word3.", "after")],
                0) == COMPETE


def test_w2w3_tol7_still_compete_batch475(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Word2.", "after"), ("Word3.", "after")],
                7) == COMPETE


def test_w2w3_f1_two_seventeenths_batch475(tmp_path):
    r = _prf(_doc(tmp_path),
             [("Word2.", "after"), ("Word3.", "after")], 0)
    assert r[2] == 0.11764705882352941
    assert r[2] == 2 / 17


# ---------- 回退阈值 tol 21 ----------

def test_w2w3_tol21_both_batch475(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Word2.", "after"), ("Word3.", "after")],
                21) == (2 / 15, 1.0, 0.23529411764705882)


def test_w2w3_recall_flip_single_point_batch475(tmp_path):
    dd = _doc(tmp_path)
    assert _prf(dd, [("Word2.", "after"), ("Word3.", "after")],
                20)[1] == 0.5
    assert _prf(dd, [("Word2.", "after"), ("Word3.", "after")],
                21)[1] == 1.0


def test_w2w3_precision_same_until21_batch475(tmp_path):
    dd = _doc(tmp_path)
    for tol in (0, 7, 14, 20):
        assert _prf(dd, [("Word2.", "after"),
                         ("Word3.", "after")], tol)[0] == 1 / 15
    assert _prf(dd, [("Word2.", "after"), ("Word3.", "after")],
                21)[0] == 2 / 15


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch475():
    src = _src()
    assert "d = abs(pv - gv)" in src
    assert "if d <= tolerance_chars:" in src


# ---------- forbidden tokens 第七百三十七批 ----------

def test_source_no_eval_batch475():
    assert "eval(" not in _src()


def test_source_no_exec_batch475():
    assert "exec(" not in _src()


def test_source_no_compile_batch475():
    assert "compile(" not in _src()


def test_source_no_globals_batch475():
    assert "globals(" not in _src()


def test_source_no_locals_batch475():
    assert "locals(" not in _src()


def test_source_no_os_system_batch475():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch475():
    assert "subprocess" not in _src()


def test_source_no_popen_batch475():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch475():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch475():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch475():
    assert "socket" not in _src()


def test_source_no_requests_batch475():
    assert "requests" not in _src()


def test_source_no_urllib_batch475():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch475():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch475():
    assert "yield" not in _src()


def test_source_no_async_await_batch475():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch475():
    assert "open(" not in _src()
