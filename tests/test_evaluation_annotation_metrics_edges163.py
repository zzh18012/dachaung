"""evaluation/annotation_metrics.py 第五百九十四轮 edges 测试（Round 1337）。

补强 edges162 未触及的角度（第七百零九批，probe 实证）。

新角度（tolerance 敏感翻转 / 一对一竞争）：
- **tol 0 归零**——
  Word1.（离界）
  tol 0 → 全零 trio
  {0.0, 0.0, 0.0}
  reason None
  （marker 找到但
  不匹配）
- **tol 30 翻命中**
  ——同锚 tol 30 →
  {1/14, 1.0, 2/15}
  （tolerance 敏感
  翻转首锁，修正
  edges162 的不敏感
  为恰重合特例）
- **Word3 双稳**——
  恰落边界 → 两档
  全 HIT（不敏感
  复核）
- **一对一竞争**——
  [Word1, Word3]
  mix → tol 0/30 均
  {1/14, 0.5, 0.125}
  （两锚争同一边界，
  matched 恒 1，
  竞争不因容差放开
  而双配首锁）
- forbidden tokens 第七百八十批（open 0）
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

ZERO = ({"value": 0.0, "reason": None},
        {"value": 0.0, "reason": None},
        {"value": 0.0, "reason": None})
HIT14 = ({"value": 1 / 14, "reason": None},
         {"value": 1.0, "reason": None},
         {"value": 2 / 15, "reason": None})
MIX = ({"value": 1 / 14, "reason": None},
       {"value": 0.5, "reason": None},
       {"value": 0.125, "reason": None})


def _doc():
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "c.pdf").write_bytes(_wrap(ONEP))
        doc, errors = process_single(
            tp / "c.pdf", tp / "o.json",
            parser_name="fallback", max_chars=32)
        assert errors == []
        return doc.to_dict()


def _trio(anchors, tol):
    ann = {"annotation_version": "1.0",
           "doc_id": "x",
           "chunk_boundary_anchors": anchors}
    r = chunk_boundary_prf(_doc(), ann, tol)
    return (r["chunk_boundary_precision"],
            r["chunk_boundary_recall"],
            r["chunk_boundary_f1"])


def _w(n):
    return {"marker": "Word%d." % n,
            "position": "after"}


# ---------- tol 0 归零 ----------

def test_word1_tol0_zero_batch535():
    assert _trio([_w(1)], 0) == ZERO


def test_word1_tol0_reasons_none_batch535():
    t = _trio([_w(1)], 0)
    for part in t:
        assert part["reason"] is None


# ---------- tol 30 翻命中 ----------

def test_word1_tol30_hit_batch535():
    assert _trio([_w(1)], 30) == HIT14


def test_word1_flip_batch535():
    assert _trio([_w(1)], 0) != _trio([_w(1)], 30)


def test_word0_tol0_zero_batch535():
    assert _trio([_w(0)], 0)[0] == {
        "value": 0.0, "reason": None}


def test_word0_tol30_hit_batch535():
    assert _trio([_w(0)], 30) == HIT14


# ---------- Word3 双稳 ----------

def test_word3_tol0_hit_batch535():
    assert _trio([_w(3)], 0) == HIT14


def test_word3_both_tols_equal_batch535():
    assert _trio([_w(3)], 0) == _trio([_w(3)], 30)


# ---------- 一对一竞争 ----------

def test_mix_tol0_contention_batch535():
    assert _trio([_w(1), _w(3)], 0) == MIX


def test_mix_tol30_contention_batch535():
    assert _trio([_w(1), _w(3)], 30) == MIX


def test_mix_contention_constant_batch535():
    assert _trio([_w(1), _w(3)], 0) \
        == _trio([_w(1), _w(3)], 30)


def test_mix_cbr_half_batch535():
    assert _trio([_w(1), _w(3)], 30)[1] == {
        "value": 0.5, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_used_pred_batch535():
    assert "used_pred" in _src()
    assert "used_gt" in _src()


# ---------- forbidden tokens 第七百八十批 ----------

def test_source_no_eval_batch535():
    assert "eval(" not in _src()


def test_source_no_exec_batch535():
    assert "exec(" not in _src()


def test_source_no_compile_batch535():
    assert "compile(" not in _src()


def test_source_no_globals_batch535():
    assert "globals(" not in _src()


def test_source_no_locals_batch535():
    assert "locals(" not in _src()


def test_source_no_os_system_batch535():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch535():
    assert "subprocess" not in _src()


def test_source_no_popen_batch535():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch535():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch535():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch535():
    assert "socket" not in _src()


def test_source_no_requests_batch535():
    assert "requests" not in _src()


def test_source_no_urllib_batch535():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch535():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch535():
    assert "yield" not in _src()


def test_source_no_async_await_batch535():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_0_batch535():
    assert _src().count("open(") == 0
