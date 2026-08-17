"""evaluation/schema.py 第四百三十二轮 edges 测试（Round 988）。

补强 edges110 未触及的角度（第三百六十四批，probe 实证）。

新角度（evaluation-report.schema.json def 细节）：
- 最小合法报告（provenance 9 键 + devset 6 键 + summary +
  空 per_doc）整体通过
- provenance.max_chars minimum 1 → 0 被拒（与 CLI 收
  --max-chars -800 形成跨模块张力）
- summary 是全 schema 唯一 additionalProperties true 的
  def → 额外键放行
- wall_time_seconds 只 required [total, parse, chunk] →
  3 键合法；total -0.5 违 minimum 0
- ef_result doc_id 无 minLength → "" 合法（与 manifest 的
  minLength 1 不对称）
- per_doc source_type "txt" 拒；report_version "1.0" →
  const "'1.1' was expected"
- forbidden tokens 第四百五十八批（open 2）
"""

from __future__ import annotations

import copy
import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import EvalSchemaError, load_schema, validate


def _report():
    return {
        "report_version": "1.1",
        "provenance": {
            "git_commit": None, "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {"pdfplumber": None},
            "max_chars": 800,
            "run_timestamp_iso": "2026-01-01T00:00:00+08:00"},
        "devset": {"status": "incomplete", "file_count": 0,
                   "content_group_count": 0, "pdf_count": 0,
                   "docx_count": 0, "categories_covered": []},
        "summary": {"counts": {}, "success_rates": {},
                    "ratio_macro_averages": {},
                    "silent_drop_total": None},
        "per_doc": []}


def _rej(data):
    with pytest.raises(EvalSchemaError) as ei:
        validate(data, "evaluation-report.schema.json")
    return ei.value.errors[0]


# ---------- 最小合法 ----------

def test_minimal_report_valid_batch186():
    validate(_report(), "evaluation-report.schema.json")


# ---------- max_chars minimum 1 ----------

def test_max_chars_minimum_one_batch186():
    r = _report()
    r["provenance"]["max_chars"] = 0
    flat = _rej(r)
    assert flat["message"] == "0 is less than the minimum of 1"
    assert flat["path"] == ["provenance", "max_chars"]


# ---------- summary 唯一开放 def ----------

def test_summary_def_open_batch186():
    rs = load_schema("evaluation-report.schema.json")
    assert rs["$defs"]["summary"]["additionalProperties"] is True
    r = _report()
    r["summary"]["extra_key"] = 42
    validate(r, "evaluation-report.schema.json")


# ---------- wall_time 3 键 + minimum ----------

def test_wall_time_three_keys_and_minimum_batch186():
    r = _report()
    r["per_doc"] = [{"doc_id": "d", "source_type": "pdf",
                     "metrics": {},
                     "wall_time_seconds": {
                         "total": 1.0, "parse": None,
                         "chunk": None}}]
    validate(r, "evaluation-report.schema.json")

    r2 = copy.deepcopy(r)
    r2["per_doc"][0]["wall_time_seconds"]["total"] = -0.5
    flat = _rej(r2)
    assert flat["message"] == \
        "-0.5 is less than the minimum of 0"
    assert flat["path"] == ["per_doc", 0, "wall_time_seconds",
                            "total"]


# ---------- ef doc_id 空串合法 ----------

def test_ef_empty_doc_id_valid_batch186():
    r = _report()
    r["expected_failures"] = [
        {"doc_id": "", "expected_error_code": "E",
         "actual_error_code": None, "matches": False}]
    validate(r, "evaluation-report.schema.json")


# ---------- per_doc source_type ----------

def test_per_doc_source_type_txt_rejected_batch186():
    r = _report()
    r["per_doc"] = [{"doc_id": "d", "source_type": "txt",
                     "metrics": {},
                     "wall_time_seconds": {
                         "total": None, "parse": None,
                         "chunk": None}}]
    flat = _rej(r)
    assert flat["message"] == \
        "'txt' is not one of ['pdf', 'docx']"
    assert flat["path"] == ["per_doc", 0, "source_type"]


# ---------- report_version const ----------

def test_report_version_const_batch186():
    r = _report()
    r["report_version"] = "1.0"
    flat = _rej(r)
    assert flat["message"] == "'1.1' was expected"
    assert flat["path"] == ["report_version"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch186():
    src = _src()
    assert "head = errors[0]" in src
    assert "errors=flat," in src
    assert '"message": err.message,' in src
    assert "flat: list[dict[str, Any]] = []" in src


# ---------- forbidden tokens 第四百五十八批 ----------

def test_source_no_eval_batch186():
    assert "eval(" not in _src()


def test_source_no_exec_batch186():
    assert "exec(" not in _src()


def test_source_no_compile_batch186():
    assert "compile(" not in _src()


def test_source_no_globals_batch186():
    assert "globals(" not in _src()


def test_source_no_locals_batch186():
    assert "locals(" not in _src()


def test_source_no_os_system_batch186():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch186():
    assert "subprocess" not in _src()


def test_source_no_popen_batch186():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch186():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch186():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch186():
    assert "socket" not in _src()


def test_source_no_requests_batch186():
    assert "requests" not in _src()


def test_source_no_urllib_batch186():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch186():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch186():
    assert "yield" not in _src()


def test_source_no_async_await_batch186():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch186():
    assert _src().count("open(") == 2
