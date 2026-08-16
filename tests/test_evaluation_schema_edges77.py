"""evaluation/schema.py 第一百零八轮 edges 测试（Round 757）。

补强 edges74-76 未触及的角度（第一百二十一批）。

新角度（annotation schema 行为锁，此前多为 manifest/report 角度）：
- boundary_anchor 结构：required [marker, position]、marker minLength 1
  （空串拒）、position enum 仅 before/after（middle 拒）、额外键仅
  reason（"reason": "x" 合法 —— anchor 可带人工说明）
- anchors 数组元素必须是 object（字符串项拒）
- annotation 顶层：最小合法体 {annotation_version, doc_id}；anchors 缺省
  合法、anchors [] 合法；顶层额外键拒（additionalProperties false）
- manifest 顶层额外键拒 / document 条目额外键拒（两级 addProps false）
- 三 schema $schema 均为 draft 2020-12；$id 命名空间 kvfs.local + title
  精确三元组（v1.0 / v1.1 / v1.0）
- forbidden tokens 第二百二十七批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    EvalSchemaError,
    load_schema,
    validate,
)

_ANN = {"annotation_version": "1.0", "doc_id": "d"}
_MAN = {"manifest_version": "1.0", "devset_status": "incomplete",
        "documents": []}


def _rejects(inst, name, fragment):
    with pytest.raises(EvalSchemaError) as ei:
        validate(inst, name)
    assert fragment in str(ei.value)


# ---------- boundary_anchor 行为 ----------

def test_anchor_empty_marker_rejected_batch54():
    _rejects({**_ANN, "chunk_boundary_anchors": [
        {"marker": "", "position": "after"}]},
        "annotation.schema.json", "should be non-empty")


def test_anchor_position_enum_batch54():
    _rejects({**_ANN, "chunk_boundary_anchors": [
        {"marker": "m", "position": "middle"}]},
        "annotation.schema.json", "'middle' is not one of ['before', 'after']")


def test_anchor_reason_key_allowed_batch54():
    validate({**_ANN, "chunk_boundary_anchors": [
        {"marker": "m", "position": "after", "reason": "x"}]},
        "annotation.schema.json")


def test_anchor_position_required_batch54():
    _rejects({**_ANN, "chunk_boundary_anchors": [{"marker": "m"}]},
             "annotation.schema.json", "'position' is a required property")


def test_anchor_string_item_rejected_batch54():
    _rejects({**_ANN, "chunk_boundary_anchors": ["m"]},
             "annotation.schema.json", "'m' is not of type 'object'")


# ---------- annotation 顶层 ----------

def test_annotation_minimal_valid_batch54():
    validate(_ANN, "annotation.schema.json")


def test_annotation_anchors_absent_and_empty_valid_batch54():
    validate({**_ANN, "chunk_boundary_anchors": []},
             "annotation.schema.json")


def test_annotation_top_extra_key_rejected_batch54():
    _rejects({**_ANN, "extra": 1}, "annotation.schema.json",
             "Additional properties are not allowed")


# ---------- manifest 两级 addProps ----------

def test_manifest_top_extra_key_rejected_batch54():
    _rejects({**_MAN, "zzz": 1}, "manifest.schema.json",
             "Additional properties are not allowed")


def test_manifest_document_entry_extra_key_rejected_batch54():
    _rejects({**_MAN, "documents": [
        {"doc_id": "d", "path": "a.pdf", "source_type": "pdf", "zz": 1}]},
        "manifest.schema.json", "Additional properties are not allowed")


# ---------- schema 文件元数据 ----------

def test_all_schemas_draft_2020_12_batch54():
    for name in ("manifest.schema.json", "evaluation-report.schema.json",
                 "annotation.schema.json"):
        assert load_schema(name)["$schema"] == \
            "https://json-schema.org/draft/2020-12/schema"


def test_schema_ids_and_titles_batch54():
    assert load_schema("manifest.schema.json")["$id"] == \
        "https://kvfs.local/schemas/manifest.schema.json"
    assert load_schema("evaluation-report.schema.json")["$id"] == \
        "https://kvfs.local/schemas/evaluation-report.schema.json"
    assert load_schema("annotation.schema.json")["$id"] == \
        "https://kvfs.local/schemas/annotation.schema.json"
    assert (load_schema("manifest.schema.json")["title"],
            load_schema("evaluation-report.schema.json")["title"],
            load_schema("annotation.schema.json")["title"]) == (
        "Evaluation Manifest v1.0", "Evaluation Report v1.1",
        "Human Annotation v1.0")


def test_boundary_anchor_def_shape_batch54():
    ba = load_schema("annotation.schema.json")["$defs"]["boundary_anchor"]
    assert ba["required"] == ["marker", "position"]
    assert ba["additionalProperties"] is False
    assert sorted(ba["properties"]) == ["marker", "position", "reason"]
    assert ba["properties"]["marker"]["minLength"] == 1
    assert ba["properties"]["position"]["enum"] == ["before", "after"]


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(schema_mod)


def test_source_draft_validator_batch54():
    assert "Draft202012Validator(schema)" in _src()


# ---------- forbidden tokens 第二百二十七批 ----------

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
