"""evaluation/annotation_metrics.py 第五百六十三轮 edges 测试（Round 1119）。

补强 edges140 未触及的角度（第四百九十五批，probe 实证）。

新角度（marker 定位三重字面性）：
- **marker 大小写敏感**：流 "AAA bbb"、marker "aaa" → 找不到
  → _missing_markers ["aaa"] + P 0.0 + R null
  no_ground_truth_anchors_in_stream——str.find 字节级精确，
  无大小写折叠（首锁）
- **marker 不做规范化**：chunk "A  B"（双空格）流侧规范化成
  "A B"，marker "A  B" 原样查找 → 找不到 → missing；对照
  单空格 marker "A B" → 全 1.0——流侧 normalize、marker
  侧原样，两侧不对称（首锁）
- **内嵌 marker 被前锚消费**：流 "AB CD"，锚 ["AB" after →
  gt 2, "B" before]——"B" 唯一出现在 "AB" 内部但 search_from
  已推进到 2 → missing ["B"]；已定位锚照常匹配（d=0）→
  P/R/F1 全 1.0——缺失 marker 不计入 recall 分母（首锁）
- forbidden tokens 第五百九十一批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


# ---------- marker 大小写敏感 ----------

def test_marker_case_sensitive_batch318():
    doc = {"chunks": [{"text": "AAA"}, {"text": "bbb"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "aaa", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["_missing_markers"] == {"value": ["aaa"],
                                       "reason": None}
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["chunk_boundary_f1"] == {
        "value": None,
        "reason": "precision_or_recall_not_evaluated"}


# ---------- marker 不做规范化（流侧 / marker 侧不对称） ----------

def test_marker_not_normalized_batch318():
    doc = {"chunks": [{"text": "A  B"}, {"text": "CCC"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "A  B", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["_missing_markers"] == {"value": ["A  B"],
                                       "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}


def test_marker_not_normalized_control_batch318():
    doc = {"chunks": [{"text": "A  B"}, {"text": "CCC"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "A B", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert "_missing_markers" not in out
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- 内嵌 marker 被前锚消费 ----------

def test_nested_marker_consumed_batch318():
    doc = {"chunks": [{"text": "AB"}, {"text": "CD"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "AB", "position": "after"},
        {"marker": "B", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["_missing_markers"] == {"value": ["B"],
                                       "reason": None}
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch318():
    src = _src()
    assert "重新规范化拼接结果" in src
    assert "每个 anchor 的搜索起点是上一个 anchor 之后" in src


# ---------- forbidden tokens 第五百九十一批 ----------

def test_source_no_eval_batch318():
    assert "eval(" not in _src()


def test_source_no_exec_batch318():
    assert "exec(" not in _src()


def test_source_no_compile_batch318():
    assert "compile(" not in _src()


def test_source_no_globals_batch318():
    assert "globals(" not in _src()


def test_source_no_locals_batch318():
    assert "locals(" not in _src()


def test_source_no_os_system_batch318():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch318():
    assert "subprocess" not in _src()


def test_source_no_popen_batch318():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch318():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch318():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch318():
    assert "socket" not in _src()


def test_source_no_requests_batch318():
    assert "requests" not in _src()


def test_source_no_urllib_batch318():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch318():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch318():
    assert "yield" not in _src()


def test_source_no_async_await_batch318():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch318():
    assert "open(" not in _src()
