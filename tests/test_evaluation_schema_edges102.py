"""evaluation/schema.py 第三百六十九轮 edges 测试（Round 925）。

补强 edges101 未触及的角度（第三百零一批，probe 实证）。

新角度：
- annotation 顶层 required 恰 [annotation_version, doc_id]——
  chunk_boundary_anchors 竟不在 required（可选标注）
- boundary_anchor def 全形：required [marker, position]、
  封闭、marker minLength 1、position 无 type 纯 enum
  [before, after]、reason 可选 string
- chunk def：required 4 项 [chunk_id, text,
  source_element_ids, metadata]；chunk_id / text 均
  minLength 1；source_spans 可选 $ref source_span
- document 的 metadata prop 仅 {"type": "object"}；
  顶层 13 props 与 13 required 完全一致（全必填）
- validate 合法实例返回 None（无异常）
- EvalSchemaError.errors 每条键序 [path, message,
  schema_path]
- SCHEMAS_DIR：名 "schemas"、目录存在、恰 4 个 schema
- validate_file 接受 str 路径
- forbidden tokens 第三百九十五批
"""

from __future__ import annotations

import inspect
import json

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    load_schema,
    validate,
    validate_file,
)


# ---------- annotation 顶层 ----------

def test_annotation_top_required_two_batch123():
    a = load_schema("annotation.schema.json")
    assert a["required"] == ["annotation_version", "doc_id"]
    assert "chunk_boundary_anchors" not in a["required"]
    assert a["properties"]["chunk_boundary_anchors"] == {
        "type": "array",
        "items": {"$ref": "#/$defs/boundary_anchor"},
    }


# ---------- boundary_anchor def ----------

def test_boundary_anchor_full_shape_batch123():
    ba = load_schema("annotation.schema.json")["$defs"][
        "boundary_anchor"]
    assert ba["required"] == ["marker", "position"]
    assert ba["additionalProperties"] is False
    assert ba["properties"]["marker"] == {
        "type": "string", "minLength": 1}
    assert ba["properties"]["position"] == {
        "enum": ["before", "after"]}
    assert ba["properties"]["reason"] == {"type": "string"}
    assert "type" not in ba["properties"]["position"]


# ---------- chunk def ----------

def test_chunk_def_required_and_props_batch123():
    ch = load_schema("document.schema.json")["$defs"]["chunk"]
    assert ch["required"] == ["chunk_id", "text",
                              "source_element_ids", "metadata"]
    props = ch["properties"]
    assert props["chunk_id"] == {"type": "string", "minLength": 1}
    assert props["text"] == {"type": "string", "minLength": 1}
    assert props["source_element_ids"] == {
        "type": "array", "minItems": 1,
        "items": {"type": "string", "minLength": 1}}
    assert props["source_spans"] == {
        "type": "array",
        "items": {"$ref": "#/$defs/source_span"},
    }


# ---------- document metadata / 全必填 ----------

def test_document_metadata_unconstrained_batch123():
    d = load_schema("document.schema.json")
    assert d["properties"]["metadata"] == {"type": "object"}
    assert len(d["properties"]) == 13
    assert sorted(d["properties"]) == sorted(d["required"])


# ---------- validate 返回值 ----------

def test_validate_valid_returns_none_batch123():
    out = validate(
        {"manifest_version": "1.0",
         "devset_status": "incomplete", "documents": []},
        "manifest.schema.json")
    assert out is None


# ---------- errors 条目键序 ----------

def test_error_entry_key_order_batch123():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": 1},
                 "manifest.schema.json")
    assert len(ei.value.errors) == 4  # 缺 2 必填 + type + const
    for entry in ei.value.errors:
        assert list(entry) == ["path", "message", "schema_path"]


# ---------- SCHEMAS_DIR ----------

def test_schemas_dir_inventory_batch123():
    assert SCHEMAS_DIR.name == "schemas"
    assert SCHEMAS_DIR.is_dir()
    assert sorted(p.name for p in SCHEMAS_DIR.glob("*.json")) == [
        "annotation.schema.json", "document.schema.json",
        "evaluation-report.schema.json", "manifest.schema.json",
    ]


# ---------- validate_file str 路径 ----------

def test_validate_file_str_path_batch123(tmp_path):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": []}), encoding="utf-8")
    assert validate_file(str(f), "manifest.schema.json") is None


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch123():
    src = _src()
    assert '"schema_path": list(err.absolute_schema_path),' in src
    assert 'f"{head.message} @ path={list(head.absolute_path)}"' in src
    assert "self.errors = errors or []" in src


# ---------- forbidden tokens 第三百九十五批 ----------

def test_source_no_eval_batch123():
    assert "eval(" not in _src()


def test_source_no_exec_batch123():
    assert "exec(" not in _src()


def test_source_no_compile_batch123():
    assert "compile(" not in _src()


def test_source_no_globals_batch123():
    assert "globals(" not in _src()


def test_source_no_locals_batch123():
    assert "locals(" not in _src()


def test_source_no_os_system_batch123():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch123():
    assert "subprocess" not in _src()


def test_source_no_popen_batch123():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch123():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch123():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch123():
    assert "socket" not in _src()


def test_source_no_requests_batch123():
    assert "requests" not in _src()


def test_source_no_urllib_batch123():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch123():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch123():
    assert "yield" not in _src()


def test_source_no_async_await_batch123():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch123():
    assert _src().count("open(") == 2
