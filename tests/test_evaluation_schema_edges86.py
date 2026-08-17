"""evaluation/schema.py 第二百六十四轮 edges 测试（Round 820）。

补强 edges85 未触及的角度（第一百九十一批）。

新角度（manifest schema 行为面 + report required/minimum）：
- documents path "" → minLength 拒（与 loader 侧 "为空"
  ManifestError 互补，schema 先拦）
- sha256 大写 "A"*64 / 63 位小写 → pattern 拒（只收 64 位
  小写 hex）
- devset_status "bogus" → enum 拒（消息列出双值）
- expected_failures source_type "other" 放行（enum 含 other）
- report per_doc 缺 wall_time_seconds → required 拒（"is a
  required property"）
- provenance max_chars 0 → minimum 1 拒
- validate_file 合法报告落盘通过（round-trip）
- forbidden tokens 第二百九十批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (EvalSchemaError, validate,
                               validate_file)

M = {"manifest_version": "1.0", "devset_status": "incomplete",
     "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                    "source_type": "pdf"}]}

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


def _merr(inst):
    with pytest.raises(EvalSchemaError) as ei:
        validate(inst, "manifest.schema.json")
    return ei.value.errors[0]


# ---------- path 空 ----------

def test_manifest_empty_path_rejected_batch55():
    er = _merr({**M, "documents": [
        {"doc_id": "d1", "path": "", "source_type": "pdf"}]})
    assert er["path"] == ["documents", 0, "path"]
    assert "'' should be non-empty" == er["message"]


# ---------- sha256 pattern ----------

def test_sha256_uppercase_rejected_batch55():
    er = _merr({**M, "documents": [
        {"doc_id": "d1", "path": "a", "source_type": "pdf",
         "sha256": "A" * 64}]})
    assert er["path"] == ["documents", 0, "sha256"]
    assert "does not match" in er["message"]


def test_sha256_63_chars_rejected_batch55():
    er = _merr({**M, "documents": [
        {"doc_id": "d1", "path": "a", "source_type": "pdf",
         "sha256": "a" * 63}]})
    assert er["path"] == ["documents", 0, "sha256"]


# ---------- devset_status enum ----------

def test_devset_status_bogus_rejected_batch55():
    er = _merr({**M, "devset_status": "bogus"})
    assert er["path"] == ["devset_status"]
    assert ("'bogus' is not one of ['complete', 'incomplete']"
            == er["message"])


# ---------- ef "other" 放行 ----------

def test_ef_source_type_other_valid_batch55():
    validate({**M, "expected_failures": [
        {"doc_id": "f", "path": "a", "expected_error_code": "X",
         "source_type": "other"}]}, "manifest.schema.json")


# ---------- per_doc required ----------

def test_per_doc_missing_wall_time_rejected_batch55():
    r = json.loads(json.dumps(REP))
    r["per_doc"] = [{"doc_id": "d", "source_type": "pdf",
                     "metrics": {}}]
    with pytest.raises(EvalSchemaError) as ei:
        validate(r, "evaluation-report.schema.json")
    er = ei.value.errors[0]
    assert er["path"] == ["per_doc", 0]
    assert ("'wall_time_seconds' is a required property"
            == er["message"])


# ---------- max_chars 下界 ----------

def test_provenance_max_chars_zero_rejected_batch55():
    r = json.loads(json.dumps(REP))
    r["provenance"]["max_chars"] = 0
    with pytest.raises(EvalSchemaError) as ei:
        validate(r, "evaluation-report.schema.json")
    er = ei.value.errors[0]
    assert er["path"] == ["provenance", "max_chars"]
    assert "0 is less than the minimum of 1" == er["message"]


# ---------- validate_file round-trip ----------

def test_validate_file_valid_report_batch55(tmp_path):
    f = tmp_path / "ok.json"
    f.write_text(json.dumps(REP), encoding="utf-8")
    validate_file(f, "evaluation-report.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert 'validator = Draft202012Validator(schema)' in src
    assert 'flat.append(' in src


# ---------- forbidden tokens 第二百九十批 ----------

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
