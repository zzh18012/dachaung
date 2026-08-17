"""evaluation/schema.py 第三百八十三轮 edges 测试（Round 939）。

补强 edges103 未触及的角度（第三百一十五批，probe 实证）。

新角度（直接读三个 Schema 文件的结构性事实）：
- 三 Schema 全部通过 Draft202012Validator.check_schema
  （自身合法的 2020-12 Schema）
- 三 Schema 顶层均含 $schema 与 $id；report 第 6 键是
  additionalProperties、manifest/annotation 第 6 键 required
- manifest document def：required 恰 [doc_id, path,
  source_type]、封闭（additionalProperties false）、恰 8
  属性
- devset_status 纯 enum [complete, incomplete]
- paired_with 恰 {"type": "string"}（无 pattern 约束）
- documents 传字符串 → "'x' is not of type 'array' @
  path=['documents']"
- evaluation-report provenance def required 恰 9 项，与
  build_provenance 输出键一一对应
- summary def 无 required、恰 4 属性 [counts,
  ratio_macro_averages, silent_drop_total, success_rates]
- EvalSchemaError 是 Exception 子类，errors 原样保留、
  str 即 message
- forbidden tokens 第四百零九批
"""

from __future__ import annotations

import inspect

from jsonschema import Draft202012Validator

import evaluation.schema as schema_mod
from evaluation.schema import (
    EvalSchemaError,
    load_schema,
    validate,
)

_MS = load_schema("manifest.schema.json")
_RS = load_schema("evaluation-report.schema.json")
_AS = load_schema("annotation.schema.json")


# ---------- 三 Schema 自检 ----------

def test_three_schemas_pass_meta_schema_batch137():
    for s in (_MS, _RS, _AS):
        assert Draft202012Validator.check_schema(s) is None


def test_top_level_dollar_fields_batch137():
    for s in (_MS, _RS, _AS):
        assert "$schema" in s
        assert "$id" in s
    assert list(_RS)[5] == "additionalProperties"
    assert list(_MS)[5] == "required"
    assert list(_AS)[5] == "required"


# ---------- manifest document def ----------

def test_manifest_document_def_shape_batch137():
    dd = _MS["$defs"]["document"]
    assert dd["required"] == ["doc_id", "path", "source_type"]
    assert dd["additionalProperties"] is False
    assert sorted(dd["properties"]) == [
        "annotation_file", "categories", "doc_id",
        "expectations", "paired_with", "path", "sha256",
        "source_type"]


def test_devset_status_enum_batch137():
    assert _MS["properties"]["devset_status"] == {
        "enum": ["complete", "incomplete"]}


def test_paired_with_plain_string_batch137():
    dd = _MS["$defs"]["document"]
    assert dd["properties"]["paired_with"] == {"type": "string"}


# ---------- documents 类型错 ----------

def test_documents_string_type_error_batch137():
    import pytest
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": "1.0",
                  "devset_status": "incomplete",
                  "documents": "x"}, "manifest.schema.json")
    assert "'x' is not of type 'array' @ path=['documents']" \
        in str(ei.value)


# ---------- report provenance / summary def ----------

def test_report_provenance_nine_required_batch137():
    pr = _RS["$defs"]["provenance"]
    assert pr["required"] == [
        "git_commit", "git_dirty", "evaluator_version",
        "report_version", "parser_name", "parser_version",
        "dependencies", "max_chars", "run_timestamp_iso"]


def test_report_summary_def_shape_batch137():
    sm = _RS["$defs"]["summary"]
    assert "required" not in sm
    assert sorted(sm["properties"]) == [
        "counts", "ratio_macro_averages", "silent_drop_total",
        "success_rates"]


# ---------- EvalSchemaError 语义 ----------

def test_eval_schema_error_semantics_batch137():
    e = EvalSchemaError("m", errors=[{"path": []}])
    assert isinstance(e, Exception)
    assert e.errors == [{"path": []}]
    assert str(e) == "m"
    assert EvalSchemaError("x").errors == []


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch137():
    src = _src()
    assert "from jsonschema import Draft202012Validator" in src
    assert 'with _schema_path(name).open("r", encoding="utf-8") as f:' in src
    assert 'with p.open("r", encoding="utf-8") as f:' in src
    assert 'flat.append(' in src


# ---------- forbidden tokens 第四百零九批 ----------

def test_source_no_eval_batch137():
    assert "eval(" not in _src()


def test_source_no_exec_batch137():
    assert "exec(" not in _src()


def test_source_no_compile_batch137():
    assert "compile(" not in _src()


def test_source_no_globals_batch137():
    assert "globals(" not in _src()


def test_source_no_locals_batch137():
    assert "locals(" not in _src()


def test_source_no_os_system_batch137():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch137():
    assert "subprocess" not in _src()


def test_source_no_popen_batch137():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch137():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch137():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch137():
    assert "socket" not in _src()


def test_source_no_requests_batch137():
    assert "requests" not in _src()


def test_source_no_urllib_batch137():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch137():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch137():
    assert "yield" not in _src()


def test_source_no_async_await_batch137():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch137():
    assert _src().count("open(") == 2
