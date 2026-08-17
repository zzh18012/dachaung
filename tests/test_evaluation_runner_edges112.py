"""evaluation/runner.py 第三百六十六轮 edges 测试（Round 922）。

补强 edges111 未触及的角度（第二百九十八批，probe 实证）。

新角度：
- _process_one：process_single 抛异常 → 直接冒出，但
  _per_doc 目录已建好（mkdir 先于调用）
- process_single 返回 (doc, errors) → runner 层丢弃 doc 只留
  errors[0] → pipeline_success False + element_count_total
  null pipeline_failed（与 metrics 层 doc+error 并存照算形成
  对照——丢弃发生在 _process_one）
- 单 chunk + 缺失 marker：no_predicted_boundaries 早退先于
  marker 搜索 → _missing_markers 记 []、recall 0.0；
  两 chunk + 缺失 marker → _missing_markers ["ZZZ"]、
  recall null no_ground_truth_anchors_in_stream
- wall_time_seconds.total 真实计时 float >= 0、parse/chunk
  None + not_instrumented
- 公开 per_doc 行恰 4 键（_annotation_present 不外泄）
- expected_failures 循环的 process_single 抛异常 → 同样冒出
  （无 try 包裹）
- forbidden tokens 第三百九十二批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import _process_one, run_evaluation


class _FakeDoc:
    parser_version = "7.7"
    source_hash = "deadbeef"

    def __init__(self, chunks=None):
        self._d = {
            "elements": [{"element_id": "e1", "type": "paragraph",
                          "content": "AB"}],
            "chunks": chunks if chunks is not None else [
                {"text": "AB", "source_element_ids": ["e1"]}],
        }

    def to_dict(self):
        return self._d


class _Err:
    def to_dict(self):
        return {"code": "E_X", "message": "boom"}


def _mk(tmp_path, docs, efs=None, ann=None):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    if ann is not None:
        (root / "ann.json").write_text(json.dumps(ann),
                                       encoding="utf-8")
    m = {"manifest_version": "1.0", "devset_status": "incomplete",
         "documents": docs}
    if efs is not None:
        m["expected_failures"] = efs
    f = tmp_path / "m.json"
    f.write_text(json.dumps(m), encoding="utf-8")
    return load_manifest(f, root)


_D1 = {"doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf"}


# ---------- _process_one 异常传播 ----------

def test_process_one_crash_dir_exists_batch120(tmp_path):
    m = _mk(tmp_path, [_D1])
    with patch.object(runner_mod, "process_single",
                      side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            _process_one(m.documents[0], tmp_path / "out",
                         "fallback", 800)
    assert (tmp_path / "out" / "_per_doc").is_dir()


# ---------- doc+errors 丢弃 ----------

def test_doc_with_errors_discarded_batch120(tmp_path):
    m = _mk(tmp_path, [_D1])

    def fake_ps(path, out_path, **kw):
        return _FakeDoc(), [_Err()]

    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        rep = run_evaluation(m, tmp_path / "r.json")
    metrics = rep["per_doc"][0]["metrics"]
    assert metrics["pipeline_success"] == {"value": False,
                                           "reason": None}
    assert metrics["error_code"] == {"value": "E_X",
                                     "reason": None}
    assert metrics["element_count_total"] == {
        "value": None, "reason": "pipeline_failed"}


# ---------- _missing_markers 两形态 ----------

def _run_with_ann(tmp_path, doc, ann, doc_obj):
    doc = dict(doc, annotation_file="ann.json")
    m = _mk(tmp_path, [doc], ann=ann)
    captured = []
    with patch.object(runner_mod, "process_single",
                      return_value=(doc_obj, [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}), \
         patch.object(runner_mod, "aggregate_summary",
                      side_effect=lambda r: captured.append(
                          list(r)) or {}):
        run_evaluation(m, tmp_path / "r.json")
    return captured[0][0]


_ANN_ZZZ = {"chunk_boundary_anchors": [
    {"marker": "ZZZ", "position": "after"}]}


def test_missing_marker_swallowed_single_chunk_batch120(tmp_path):
    row = _run_with_ann(tmp_path, _D1, _ANN_ZZZ, _FakeDoc())
    assert row["_annotation_present"] is True
    assert row["_missing_markers"] == []  # 早退先于 marker 搜索
    assert row["metrics"]["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}


def test_missing_marker_recorded_two_chunks_batch120(tmp_path):
    two_chunks = _FakeDoc(chunks=[
        {"text": "AB", "source_element_ids": ["e1"]},
        {"text": "CD", "source_element_ids": ["e1"]},
    ])
    row = _run_with_ann(tmp_path, _D1, _ANN_ZZZ, two_chunks)
    assert row["_missing_markers"] == ["ZZZ"]
    assert row["metrics"]["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}


# ---------- wall_time 真实计时 ----------

def test_wall_time_float_nonneg_batch120(tmp_path):
    m = _mk(tmp_path, [_D1])
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        rep = run_evaluation(m, tmp_path / "r.json")
    w = rep["per_doc"][0]["wall_time_seconds"]
    assert isinstance(w["total"], float)
    assert w["total"] >= 0.0
    assert w["parse"] is None
    assert w["parse_reason"] == "not_instrumented"
    assert w["chunk_reason"] == "not_instrumented"


# ---------- 公开 per_doc 4 键 ----------

def test_public_row_four_keys_batch120(tmp_path):
    m = _mk(tmp_path, [_D1])
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        rep = run_evaluation(m, tmp_path / "r.json")
    row = rep["per_doc"][0]
    assert sorted(row) == ["doc_id", "metrics", "source_type",
                           "wall_time_seconds"]
    assert "_annotation_present" not in row


# ---------- ef 循环异常传播 ----------

def test_ef_loop_crash_propagates_batch120(tmp_path):
    m = _mk(tmp_path, [_D1], efs=[{
        "doc_id": "f1", "path": "samples/a.pdf",
        "expected_error_code": "E"}])
    with patch.object(runner_mod, "process_single",
                      side_effect=[(_FakeDoc(), []),
                                   RuntimeError("boom")]), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        with pytest.raises(RuntimeError):
            run_evaluation(m, tmp_path / "r.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch120():
    src = _src()
    assert "metrics.update(fig_caps)" in src
    assert 'tolerance_record = chunk_b.pop("_tolerance_chars", None)' in src
    assert "return None, errors[0].to_dict(), elapsed, None, image_dir" in src
    assert 'out_stub.parent.mkdir(parents=True, exist_ok=True)' in src


# ---------- forbidden tokens 第三百九十二批 ----------

def test_source_no_eval_batch120():
    assert "eval(" not in _src()


def test_source_no_exec_batch120():
    assert "exec(" not in _src()


def test_source_no_compile_batch120():
    assert "compile(" not in _src()


def test_source_no_globals_batch120():
    assert "globals(" not in _src()


def test_source_no_locals_batch120():
    assert "locals(" not in _src()


def test_source_no_os_system_batch120():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch120():
    assert "subprocess" not in _src()


def test_source_no_popen_batch120():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch120():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch120():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch120():
    assert "socket" not in _src()


def test_source_no_requests_batch120():
    assert "requests" not in _src()


def test_source_no_urllib_batch120():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch120():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch120():
    assert "yield" not in _src()


def test_source_no_async_await_batch120():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch120():
    assert _src().count("open(") == 2
