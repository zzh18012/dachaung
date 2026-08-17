"""evaluation/schema.py 第三百九十轮 edges 测试（Round 946）。

补强 edges104 未触及的角度（第三百二十二批，probe 实证）。

新角度（Schema 文件结构性事实第二批）：
- $defs 清单：manifest 恰 [document, expected_failure]；
  report 恰 5 项；annotation 恰 [boundary_anchor]；
  wall_time_seconds 不在 $defs（内联在 per_doc def 里）
- manifest expectations def：封闭、element_count_by_type
  值约束 {integer, minimum 0}、required_markers 数组
  （string minLength 1）
- 三 Schema $id 均为 https://kvfs.local/schemas/<文件名>
- wall_time 内联 def：required 恰 [total, parse, chunk]、
  不封闭、total/parse 均 [number, null] minimum 0
- expected_failure_result def：required 4 项、matches
  恰 boolean、actual_error_code [string, null]
- per_doc def：required 4、不封闭；报告 properties.per_doc
  是 items $ref wiring
- boundary_anchor def：required 恰 [marker, position]、
  恰 3 属性
- SCHEMAS_DIR 恰 4 文件（含 app 的 document.schema.json）
- validate 顶层字符串 → "'hello' is not of type 'object'"
- forbidden tokens 第四百一十六批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    load_schema,
    validate,
)

_MS = load_schema("manifest.schema.json")
_RS = load_schema("evaluation-report.schema.json")
_AS = load_schema("annotation.schema.json")


# ---------- $defs 清单 ----------

def test_defs_inventory_batch144():
    assert sorted(_MS["$defs"]) == ["document",
                                    "expected_failure"]
    assert sorted(_RS["$defs"]) == [
        "devset", "expected_failure_result", "per_doc",
        "provenance", "summary"]
    assert sorted(_AS["$defs"]) == ["boundary_anchor"]
    assert "wall_time_seconds" not in _RS["$defs"]


# ---------- expectations def ----------

def test_expectations_def_shape_batch144():
    exp = _MS["$defs"]["document"]["properties"]["expectations"]
    assert exp["additionalProperties"] is False
    ect = exp["properties"]["element_count_by_type"]
    assert ect["additionalProperties"] == {
        "type": "integer", "minimum": 0}
    rm = exp["properties"]["required_markers"]
    assert rm["type"] == "array"
    assert rm["items"] == {"type": "string", "minLength": 1}


# ---------- $id ----------

def test_dollar_ids_batch144():
    assert _MS["$id"] == \
        "https://kvfs.local/schemas/manifest.schema.json"
    assert _RS["$id"] == "https://kvfs.local/schemas/" \
        "evaluation-report.schema.json"
    assert _AS["$id"] == "https://kvfs.local/schemas/" \
        "annotation.schema.json"


# ---------- wall_time 内联 ----------

def test_wall_time_inline_def_batch144():
    wt = _RS["$defs"]["per_doc"]["properties"][
        "wall_time_seconds"]
    assert wt["required"] == ["total", "parse", "chunk"]
    assert wt["additionalProperties"] is False
    assert sorted(wt["properties"]) == [
        "chunk", "chunk_reason", "parse", "parse_reason",
        "total"]
    assert wt["properties"]["total"] == {
        "type": ["number", "null"], "minimum": 0}


# ---------- expected_failure_result ----------

def test_efr_def_shape_batch144():
    efr = _RS["$defs"]["expected_failure_result"]
    assert efr["required"] == [
        "doc_id", "expected_error_code", "actual_error_code",
        "matches"]
    assert efr["properties"]["matches"] == {"type": "boolean"}
    assert efr["properties"]["actual_error_code"] == {
        "type": ["string", "null"]}


# ---------- per_doc wiring ----------

def test_per_doc_def_and_wiring_batch144():
    pd = _RS["$defs"]["per_doc"]
    assert pd["required"] == [
        "doc_id", "source_type", "metrics",
        "wall_time_seconds"]
    assert pd["additionalProperties"] is False
    assert _RS["properties"]["per_doc"] == {
        "type": "array", "items": {"$ref": "#/$defs/per_doc"}}


# ---------- boundary_anchor ----------

def test_boundary_anchor_def_batch144():
    ba = _AS["$defs"]["boundary_anchor"]
    assert ba["required"] == ["marker", "position"]
    assert sorted(ba["properties"]) == [
        "marker", "position", "reason"]


# ---------- SCHEMAS_DIR 4 文件 ----------

def test_schemas_dir_four_files_batch144():
    assert sorted(p.name for p in SCHEMAS_DIR.iterdir()) == [
        "annotation.schema.json", "document.schema.json",
        "evaluation-report.schema.json",
        "manifest.schema.json"]


# ---------- 顶层字符串 ----------

def test_string_top_level_batch144():
    with pytest.raises(EvalSchemaError) as ei:
        validate("hello", "annotation.schema.json")
    assert "'hello' is not of type 'object'" in str(ei.value)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch144():
    src = _src()
    assert 'SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"' in src
    assert "if not p.is_file():" in src
    assert 'validator = Draft202012Validator(schema)' in src


# ---------- forbidden tokens 第四百一十六批 ----------

def test_source_no_eval_batch144():
    assert "eval(" not in _src()


def test_source_no_exec_batch144():
    assert "exec(" not in _src()


def test_source_no_compile_batch144():
    assert "compile(" not in _src()


def test_source_no_globals_batch144():
    assert "globals(" not in _src()


def test_source_no_locals_batch144():
    assert "locals(" not in _src()


def test_source_no_os_system_batch144():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch144():
    assert "subprocess" not in _src()


def test_source_no_popen_batch144():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch144():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch144():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch144():
    assert "socket" not in _src()


def test_source_no_requests_batch144():
    assert "requests" not in _src()


def test_source_no_urllib_batch144():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch144():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch144():
    assert "yield" not in _src()


def test_source_no_async_await_batch144():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch144():
    assert _src().count("open(") == 2
