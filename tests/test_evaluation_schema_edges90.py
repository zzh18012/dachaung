"""evaluation/schema.py 第二百九十二轮 edges 测试（Round 848）。

补强 edges89 未触及的角度（第二百二十二批，probe 实证）。

新角度：
- evaluation-report 顶层 required 恰 5 项
  （expected_failures 是可选键）
- 顶层缺 summary → path=[] required 报错
- provenance 缺 parser_name → path=["provenance"]
- per_doc 条目缺 doc_id → path=["per_doc", 0]
- 报告的 expected_failures 条目**不接受 path 键**
  （additionalProperties 拒绝 + 三字段 required）
- forbidden tokens 第三百一十八批
"""

from __future__ import annotations

import copy
import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    EvalSchemaError,
    load_schema,
    validate,
)

REP = {
    "report_version": "1.1",
    "provenance": {"git_commit": None, "git_dirty": False,
                   "evaluator_version": "1.1",
                   "report_version": "1.1",
                   "parser_name": "fallback",
                   "parser_version": "1.0", "dependencies": {},
                   "max_chars": 800,
                   "run_timestamp_iso": "t"},
    "devset": {"status": "incomplete", "file_count": 0,
               "content_group_count": 0, "pdf_count": 0,
               "docx_count": 0, "categories_covered": []},
    "summary": {}, "per_doc": []}


def _rep(mod):
    r = copy.deepcopy(REP)
    mod(r)
    return r


# ---------- 顶层 required ----------

def test_report_top_required_list_batch55():
    s = load_schema("evaluation-report.schema.json")
    assert s["required"] == [
        "report_version", "provenance", "devset", "summary",
        "per_doc"]


def test_missing_summary_top_error_batch55():
    with pytest.raises(EvalSchemaError) as ei:
        validate(_rep(lambda r: r.pop("summary")),
                 "evaluation-report.schema.json")
    assert ei.value.errors[0]["path"] == []
    assert ei.value.errors[0]["message"] == \
        "'summary' is a required property"


# ---------- provenance 子字段 ----------

def test_provenance_missing_parser_name_batch55():
    with pytest.raises(EvalSchemaError) as ei:
        validate(_rep(lambda r: r["provenance"].pop(
            "parser_name")),
            "evaluation-report.schema.json")
    first = ei.value.errors[0]
    assert first["path"] == ["provenance"]
    assert first["message"] == \
        "'parser_name' is a required property"


# ---------- per_doc 条目 ----------

def test_per_doc_missing_doc_id_batch55():
    def _mod(r):
        r["per_doc"].append({
            "source_type": "pdf", "metrics": {},
            "wall_time_seconds": {
                "total": 1.0, "parse": None, "chunk": None,
                "parse_reason": "not_instrumented",
                "chunk_reason": "not_instrumented"}})
    with pytest.raises(EvalSchemaError) as ei:
        validate(_rep(_mod),
                 "evaluation-report.schema.json")
    first = ei.value.errors[0]
    assert first["path"] == ["per_doc", 0]
    assert first["message"] == "'doc_id' is a required property"


# ---------- ef 报告条目形态 ----------

def test_ef_report_item_rejects_path_batch55():
    def _mod(r):
        r["expected_failures"] = [
            {"doc_id": "f1", "path": "samples/x.pdf"}]
    with pytest.raises(EvalSchemaError) as ei:
        validate(_rep(_mod),
                 "evaluation-report.schema.json")
    msgs = [er["message"] for er in ei.value.errors]
    paths = [tuple(er["path"]) for er in ei.value.errors]
    assert ("expected_failures", 0) in paths
    assert "'expected_error_code' is a required property" in msgs
    assert "'actual_error_code' is a required property" in msgs
    assert "'matches' is a required property" in msgs
    assert any("Additional properties are not allowed" in m
               and "'path'" in m for m in msgs)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "validator = Draft202012Validator(schema)" in src
    assert "errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))" in src


# ---------- forbidden tokens 第三百一十八批 ----------

def test_source_no_eval_batch55():
    assert "eval(" not in _src()


def test_source_no_exec_batch55():
    assert "exec(" not in _src()


def test_source_no_compile_batch55():
    assert "compile(" not in _src()


def test_source_no_globals_batch55():
    assert "globals(" not in _src()


def test_source_no_locals_batch55():
    assert "locals(" not in _src()


def test_source_no_os_system_batch55():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch55():
    assert "subprocess" not in _src()


def test_source_no_popen_batch55():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch55():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch55():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch55():
    assert "socket" not in _src()


def test_source_no_requests_batch55():
    assert "requests" not in _src()


def test_source_no_urllib_batch55():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch55():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch55():
    assert "yield" not in _src()


def test_source_no_async_await_batch55():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch55():
    assert _src().count("open(") == 2
