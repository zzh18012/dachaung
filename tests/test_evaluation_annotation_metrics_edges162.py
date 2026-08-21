"""evaluation/annotation_metrics.py 第五百九十三轮 edges 测试（Round 1331）。

补强 edges161 未触及的角度（第七百零三批，probe 实证）。

新角度（tolerance 扫描 / _tolerance_chars 回显）：
- **输出恰 4 键**——
  chunk_boundary_prf
  返回键集
  {_tolerance_chars,
  chunk_boundary_f1,
  chunk_boundary_
  precision,
  chunk_boundary_
  recall} 首锁
- **tolerance 不敏感**
  ——1P 板 Word3. after
  锚恰落 pred 边界 →
  tol 0/5/30/200/
  100000 五档 trio
  全同 {1/14, 1.0,
  2/15}（容差不扰
  精确重合首锁）
- **_tolerance_chars
  回显**——各档
  {value: N,
  reason: None}
  逐档回显首锁
- **f1 = 2/15**——
  2·(1/14)/(1/14+1)
  精确值
- forbidden tokens 第七百七十五批（open 0）
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

ANN = {"annotation_version": "1.0", "doc_id": "x",
       "chunk_boundary_anchors": [
           {"marker": "Word3.",
            "position": "after"}]}

TOLS = (0, 5, 30, 200, 100000)


def _doc():
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "c.pdf").write_bytes(_wrap(ONEP))
        doc, errors = process_single(
            tp / "c.pdf", tp / "o.json",
            parser_name="fallback", max_chars=32)
        assert errors == []
        return doc.to_dict()


def _r(tol):
    return chunk_boundary_prf(_doc(), ANN, tol)


# ---------- 输出恰 4 键 ----------

def test_output_four_keys_batch529():
    assert set(_r(30)) == {
        "_tolerance_chars", "chunk_boundary_f1",
        "chunk_boundary_precision",
        "chunk_boundary_recall"}


# ---------- tolerance 不敏感 ----------

def test_trio_constant_across_tols_batch529():
    ref = _r(30)
    for t in TOLS:
        r = _r(t)
        assert (r["chunk_boundary_precision"]
                == ref["chunk_boundary_precision"])
        assert (r["chunk_boundary_recall"]
                == ref["chunk_boundary_recall"])
        assert (r["chunk_boundary_f1"]
                == ref["chunk_boundary_f1"])


def test_cbp_one_fourteenth_batch529():
    assert _r(30)["chunk_boundary_precision"] == {
        "value": 1 / 14, "reason": None}


def test_cbr_one_batch529():
    assert _r(0)["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}


def test_f1_two_fifteenths_batch529():
    assert _r(100000)["chunk_boundary_f1"] == {
        "value": 2 / 15, "reason": None}


# ---------- _tolerance_chars 回显 ----------

def test_tolerance_echo_each_batch529():
    for t in TOLS:
        assert _r(t)["_tolerance_chars"] == {
            "value": t, "reason": None}


def test_tolerance_echo_int_batch529():
    assert isinstance(
        _r(7)["_tolerance_chars"]["value"], int)


def test_tolerance_zero_specific_batch529():
    assert _r(0)["_tolerance_chars"] == {
        "value": 0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_tolerance_line_batch529():
    assert '"_tolerance_chars"' in _src()


def test_source_pairs_sort_batch529():
    assert "pairs.sort(key=lambda x: x[0])" \
        in _src()


# ---------- forbidden tokens 第七百七十五批 ----------

def test_source_no_eval_batch529():
    assert "eval(" not in _src()


def test_source_no_exec_batch529():
    assert "exec(" not in _src()


def test_source_no_compile_batch529():
    assert "compile(" not in _src()


def test_source_no_globals_batch529():
    assert "globals(" not in _src()


def test_source_no_locals_batch529():
    assert "locals(" not in _src()


def test_source_no_os_system_batch529():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch529():
    assert "subprocess" not in _src()


def test_source_no_popen_batch529():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch529():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch529():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch529():
    assert "socket" not in _src()


def test_source_no_requests_batch529():
    assert "requests" not in _src()


def test_source_no_urllib_batch529():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch529():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch529():
    assert "yield" not in _src()


def test_source_no_async_await_batch529():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_0_batch529():
    assert _src().count("open(") == 0
