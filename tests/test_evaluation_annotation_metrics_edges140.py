"""evaluation/annotation_metrics.py 第五百五十六轮 edges 测试（Round 1112）。

补强 edges139 未触及的角度（第四百八十八批，probe 实证）。

新角度（position 缺省家族全归 after）：
- **position 裸串等 after**：position "bogus" → 输出与显式
  "after" 全 dict 相等——实现是 `if position == "before"
  else after`，非 before 一律 after（裸串首锁）
- **position 缺键等 after**：anchor 不写 position →
  a.get("position", "after") 缺省即 after
- **position 非 str（int 123）等 after**：!= "before" →
  after——类型不校验
- **before 反差**：同板同锚 before → 全 0.0——证明缺省
  家族真走 after 语义而非"第三种位置"（tol 0 刀锋板：
  after 全 1.0 / before 全 0.0 / 家族全员 = after）
- forbidden tokens 第五百八十四批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(chunks):
    els = [{"element_id": f"e{i}", "type": "paragraph",
            "content": {"text": t}}
           for i, t in enumerate(chunks)]
    chs = [{"chunk_id": f"c{i}", "text": t,
            "source_element_ids": [f"e{i}"]}
           for i, t in enumerate(chunks)]
    return {"document_id": "d", "elements": els,
            "chunks": chs}


def _prf(chunks, anchors, tol=0):
    ann = {"annotation_version": "1.0", "doc_id": "d",
           "chunk_boundary_anchors": anchors}
    return chunk_boundary_prf(_doc(chunks), ann,
                              tolerance_chars=tol)


BOARD = ["head TAIL", "second chunk body text."]


# ---------- position 裸串等 after ----------

def test_position_bogus_string_is_after_batch311():
    base = _prf(BOARD, [{"marker": "TAIL",
                         "position": "after"}])
    assert base["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}
    bogus = _prf(BOARD, [{"marker": "TAIL",
                          "position": "bogus"}])
    assert bogus == base


# ---------- position 缺键等 after ----------

def test_position_absent_is_after_batch311():
    base = _prf(BOARD, [{"marker": "TAIL",
                         "position": "after"}])
    absent = _prf(BOARD, [{"marker": "TAIL"}])
    assert absent == base


# ---------- position 非 str 等 after ----------

def test_position_int_is_after_batch311():
    base = _prf(BOARD, [{"marker": "TAIL",
                         "position": "after"}])
    num = _prf(BOARD, [{"marker": "TAIL",
                        "position": 123}])
    assert num == base


# ---------- before 反差 ----------

def test_before_differs_from_default_family_batch311():
    before = _prf(BOARD, [{"marker": "TAIL",
                           "position": "before"}])
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert before[k] == {"value": 0.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch311():
    src = _src()
    assert "一对一边界语义" in src
    assert "跨过空格" in src


# ---------- forbidden tokens 第五百八十四批 ----------

def test_source_no_eval_batch311():
    assert "eval(" not in _src()


def test_source_no_exec_batch311():
    assert "exec(" not in _src()


def test_source_no_compile_batch311():
    assert "compile(" not in _src()


def test_source_no_globals_batch311():
    assert "globals(" not in _src()


def test_source_no_locals_batch311():
    assert "locals(" not in _src()


def test_source_no_os_system_batch311():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch311():
    assert "subprocess" not in _src()


def test_source_no_popen_batch311():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch311():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch311():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch311():
    assert "socket" not in _src()


def test_source_no_requests_batch311():
    assert "requests" not in _src()


def test_source_no_urllib_batch311():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch311():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch311():
    assert "yield" not in _src()


def test_source_no_async_await_batch311():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch311():
    assert "open(" not in _src()
