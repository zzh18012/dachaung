"""evaluation/schema.py 第四百六十七轮 edges 测试（Round 1023）。

补强 edges115 未触及的角度（第三百九十九批，probe 实证）。

新角度：
- per_doc 开闭不对称（行为面）：metrics prop 仅
  {"type": "object"} → 报告里塞任意 bogus 指标键照过
  RS；但 per_doc 自身 additionalProperties false →
  多一个顶层键即拒——同一条目两级一开一闭
- validate_file 标量载荷：文件内容 [] / 42 / null /
  "str" → 全走 EvalSchemaError "is not of type
  'object'"（不是 JSONDecodeError——JSON 合法、
  类型不符）
- forbidden tokens 第四百九十三批（open 2）
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (EvalSchemaError, validate,
                               validate_file)


def _report():
    return {
        "report_version": "1.1",
        "provenance": {
            "git_commit": None, "git_dirty": True,
            "evaluator_version": "1.1",
            "report_version": "1.1", "parser_name": "fallback",
            "parser_version": None, "dependencies": {},
            "max_chars": 800,
            "run_timestamp_iso": "2026-08-17T00:00:00+08:00"},
        "devset": {"status": "incomplete", "file_count": 0,
                   "content_group_count": 0, "pdf_count": 0,
                   "docx_count": 0, "categories_covered": []},
        "summary": {"counts": {}, "success_rates": {},
                    "ratio_macro_averages": {},
                    "silent_drop_total": None},
        "per_doc": [{
            "doc_id": "d", "source_type": "pdf",
            "metrics": {"custom_bogus_metric": {
                "value": 42, "reason": None}},
            "wall_time_seconds": {
                "total": 0.1, "parse": None, "chunk": None,
                "parse_reason": "not_instrumented",
                "chunk_reason": "not_instrumented"}}],
        "expected_failures": []}


# ---------- per_doc 开闭不对称 ----------

def test_metric_open_vs_per_doc_closed_batch221():
    validate(_report(), "evaluation-report.schema.json")
    closed = _report()
    closed["per_doc"] = [dict(_report()["per_doc"][0],
                              extra_key=1)]
    with pytest.raises(EvalSchemaError) as ei:
        validate(closed, "evaluation-report.schema.json")
    assert "Additional properties" in str(ei.value)
    assert "extra_key" in str(ei.value)


# ---------- 标量载荷 ----------

def test_validate_file_scalar_payloads_batch221(tmp_path):
    f = tmp_path / "p.json"
    for payload in ("[]", "42", "null", '"str"'):
        f.write_text(payload, encoding="utf-8")
        with pytest.raises(EvalSchemaError,
                           match="is not of type 'object'"):
            validate_file(f, "manifest.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch221():
    src = _src()
    assert ("errors = sorted(validator.iter_errors(instance)"
            in src)
    assert '"message": err.message,' in src
    assert "校验失败 ({len(errors)} 处)：" in src


# ---------- forbidden tokens 第四百九十三批 ----------

def test_source_no_eval_batch221():
    assert "eval(" not in _src()


def test_source_no_exec_batch221():
    assert "exec(" not in _src()


def test_source_no_compile_batch221():
    assert "compile(" not in _src()


def test_source_no_globals_batch221():
    assert "globals(" not in _src()


def test_source_no_locals_batch221():
    assert "locals(" not in _src()


def test_source_no_os_system_batch221():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch221():
    assert "subprocess" not in _src()


def test_source_no_popen_batch221():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch221():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch221():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch221():
    assert "socket" not in _src()


def test_source_no_requests_batch221():
    assert "requests" not in _src()


def test_source_no_urllib_batch221():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch221():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch221():
    assert "yield" not in _src()


def test_source_no_async_await_batch221():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch221():
    assert _src().count("open(") == 2
