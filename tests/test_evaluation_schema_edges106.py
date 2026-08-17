"""evaluation/schema.py 第三百九十七轮 edges 测试（Round 953）。

补强 edges105 未触及的角度（第三百二十九批，probe 实证）。

新角度（Schema 顶层结构 + errors 结构）：
- 三 Schema 顶层键序：MS/AS 含 description 九键；RS 无
  description 八键
- required 清单：MS [manifest_version, devset_status,
  documents]；RS 五项（expected_failures 不必填）；
  AS [annotation_version, doc_id]（anchors 不必填）
- AS additionalProperties False；boundary_anchor.position
  enum [before, after]；marker minLength 1
- EvalSchemaError.errors 扁平三键 [path, message,
  schema_path]；缺两必填 → 2 处、head 按字母序
  devset_status 先于 documents
- 排序按 absolute_path 字母序：devset 先于 provenance
- null 实例 → "None is not of type 'object'"；
  [] 实例 → "[] is not of type 'object'"
- load_schema 未知名 → FileNotFoundError 精确消息
- forbidden tokens 第四百二十三批（open 2）
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

_MS = load_schema("manifest.schema.json")
_RS = load_schema("evaluation-report.schema.json")
_AS = load_schema("annotation.schema.json")


# ---------- 顶层键序 ----------

def test_top_level_key_order_batch151():
    assert list(_MS) == ["$schema", "$id", "title",
                         "description", "type", "required",
                         "additionalProperties", "properties",
                         "$defs"]
    assert list(_RS) == ["$schema", "$id", "title", "type",
                         "required", "additionalProperties",
                         "properties", "$defs"]
    assert list(_AS) == list(_MS)


# ---------- required 清单 ----------

def test_required_lists_batch151():
    assert _MS["required"] == ["manifest_version",
                               "devset_status", "documents"]
    assert _RS["required"] == ["report_version", "provenance",
                               "devset", "summary", "per_doc"]
    assert "expected_failures" not in _RS["required"]
    assert _AS["required"] == ["annotation_version", "doc_id"]
    assert "chunk_boundary_anchors" not in _AS["required"]


# ---------- annotation 封闭与 anchor 字段 ----------

def test_annotation_closed_and_anchor_fields_batch151():
    assert _AS["additionalProperties"] is False
    ba = _AS["$defs"]["boundary_anchor"]
    assert ba["properties"]["position"] == {
        "enum": ["before", "after"]}
    assert ba["properties"]["marker"] == {
        "type": "string", "minLength": 1}


# ---------- errors 扁平结构 ----------

def test_errors_flat_structure_batch151():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": "1.0"},
                 "manifest.schema.json")
    e = ei.value
    assert len(e.errors) == 2
    assert all(list(er) == ["path", "message",
                            "schema_path"]
               for er in e.errors)
    assert e.errors[0]["path"] == []
    assert e.errors[0]["message"] == \
        "'devset_status' is a required property"
    assert e.errors[0]["schema_path"] == ["required"]
    assert "devset_status' is a required property" in str(e)
    assert e.errors[1]["message"] == \
        "'documents' is a required property"


# ---------- 排序按 absolute_path ----------

def test_error_sort_by_path_batch151():
    bad = {"report_version": "1.1",
           "provenance": "not-a-dict",
           "devset": "also-not", "summary": {},
           "per_doc": []}
    with pytest.raises(EvalSchemaError) as ei:
        validate(bad, "evaluation-report.schema.json")
    assert [er["path"] for er in ei.value.errors] == \
        [["devset"], ["provenance"]]
    assert "'also-not' is not of type 'object'" in str(ei.value)


# ---------- null / list 实例 ----------

def test_null_instance_batch151():
    with pytest.raises(EvalSchemaError) as ei:
        validate(None, "annotation.schema.json")
    assert "None is not of type 'object' @ path=[]" in \
        str(ei.value)


def test_list_instance_batch151():
    with pytest.raises(EvalSchemaError) as ei:
        validate([], "annotation.schema.json")
    assert "[] is not of type 'object' @ path=[]" in \
        str(ei.value)


# ---------- 未知 Schema 名 ----------

def test_load_schema_unknown_batch151():
    with pytest.raises(FileNotFoundError) as ei:
        load_schema("nope.schema.json")
    assert str(ei.value).startswith("Schema 文件不存在: ")
    assert str(ei.value).endswith("nope.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch151():
    src = _src()
    assert "errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))" in src
    assert '"schema_path": list(err.absolute_schema_path),' in src
    assert "errors=flat," in src
    assert 'raise FileNotFoundError(f"待校验文件不存在: {p}")' in src


# ---------- forbidden tokens 第四百二十三批 ----------

def test_source_no_eval_batch151():
    assert "eval(" not in _src()


def test_source_no_exec_batch151():
    assert "exec(" not in _src()


def test_source_no_compile_batch151():
    assert "compile(" not in _src()


def test_source_no_globals_batch151():
    assert "globals(" not in _src()


def test_source_no_locals_batch151():
    assert "locals(" not in _src()


def test_source_no_os_system_batch151():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch151():
    assert "subprocess" not in _src()


def test_source_no_popen_batch151():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch151():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch151():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch151():
    assert "socket" not in _src()


def test_source_no_requests_batch151():
    assert "requests" not in _src()


def test_source_no_urllib_batch151():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch151():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch151():
    assert "yield" not in _src()


def test_source_no_async_await_batch151():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch151():
    assert _src().count("open(") == 2
