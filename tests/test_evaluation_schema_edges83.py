"""evaluation/schema.py 第二百四十三轮 edges 测试（Round 799）。

补强 edges82 未触及的角度（第一百六十三批）。

新角度：
- manifest $defs required 锁：document 3 键、expected_failure
  3 键
- annotation boundary_anchor：required 2 键、marker
  minLength 1、position enum ["before","after"]（schema 侧
  枚举与 annotation_metrics 代码侧 else=after 分支形成对照）
- report $defs required 锁：per_doc 4 键、
  expected_failure_result 4 键
- 两个坏 anchor 的错误行：路径 [.., 0]/[.., 1] 按索引排序、
  schema_path 都是 items/required（$ref 穿透后落在 items 下）
- load_schema 收 Path 名（Path 与 str 拼接等价）
- forbidden tokens 第二百六十九批
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    EvalSchemaError,
    load_schema,
    validate,
)


# ---------- manifest $defs required ----------

def test_manifest_defs_required_batch54():
    man = load_schema("manifest.schema.json")
    assert man["$defs"]["document"]["required"] == [
        "doc_id", "path", "source_type"]
    assert man["$defs"]["expected_failure"]["required"] == [
        "doc_id", "path", "expected_error_code"]


# ---------- boundary_anchor 形态 ----------

def test_boundary_anchor_def_locked_batch54():
    ann = load_schema("annotation.schema.json")
    ba = ann["$defs"]["boundary_anchor"]
    assert ba["required"] == ["marker", "position"]
    assert ba["properties"]["position"] == {
        "enum": ["before", "after"]}
    assert ba["properties"]["marker"] == {"type": "string",
                                          "minLength": 1}


def test_position_middle_schema_rejected_batch54():
    with pytest.raises(EvalSchemaError):
        validate({"annotation_version": "1.0", "doc_id": "d",
                  "chunk_boundary_anchors": [
                      {"marker": "B", "position": "middle"}]},
                 "annotation.schema.json")


# ---------- report $defs required ----------

def test_report_defs_required_batch54():
    rep = load_schema("evaluation-report.schema.json")
    assert rep["$defs"]["per_doc"]["required"] == [
        "doc_id", "source_type", "metrics", "wall_time_seconds"]
    assert rep["$defs"]["expected_failure_result"]["required"] == [
        "doc_id", "expected_error_code", "actual_error_code",
        "matches"]


# ---------- 两个坏 anchor 的错误行 ----------

def test_two_bad_anchors_rows_sorted_batch54():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"annotation_version": "1.0", "doc_id": "d",
                  "chunk_boundary_anchors": [
                      {"marker": "B"}, {"position": "after"}]},
                 "annotation.schema.json")
    rows = ei.value.errors
    assert len(rows) == 2
    assert rows[0]["path"] == ["chunk_boundary_anchors", 0]
    assert rows[0]["schema_path"] == [
        "properties", "chunk_boundary_anchors", "items", "required"]
    assert rows[0]["message"] == "'position' is a required property"
    assert rows[1]["path"] == ["chunk_boundary_anchors", 1]
    assert rows[1]["message"] == "'marker' is a required property"


# ---------- load_schema 收 Path ----------

def test_load_schema_path_name_batch54():
    assert load_schema(Path("manifest.schema.json"))["type"] == \
        "object"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_join_lines_batch54():
    src = _src()
    assert "SCHEMAS_DIR / name" in src
    assert "Draft202012Validator(schema)" in src


# ---------- forbidden tokens 第二百六十九批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch54():
    assert _src().count("open(") == 2
