"""evaluation/schema.py 第五百八十八轮 edges 测试（Round 1352）。

补强 edges152 未触及的角度（第七百二十四批，probe 实证）。

新角度（ef 条目 report/manifest 严宽不对称）：
- **report ef 闭 4 键**
  ——source_type
  任何值（含合法
  'pdf'/'txt'）均
  additionalProperties
  拒（manifest 却收
  4 枚举首锁）
- **report ef 空串宽**
  ——doc_id ''/
  expected_error_
  code '' 均 VALID
  （无 minLength；
  manifest 有
  minLength 1 对差）
- **manifest ef 空串拒**
  ——'' should be
  non-empty
- **provenance 内层
  report_version 必填**
  ——缺键 required 拒
- **annotation reason
  空串宽**——reason 无
  minLength，'' VALID
- forbidden tokens 第七百九十二批（open 2）
"""

from __future__ import annotations

import copy
import inspect

import evaluation.schema as schema_mod
from evaluation.schema import validate


def _rep():
    return {
        "report_version": "1.1",
        "provenance": {
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None,
            "max_chars": 800,
            "run_timestamp_iso":
                "2026-01-01T00:00:00+00:00",
            "git_commit": None,
            "git_dirty": False,
            "dependencies": {}},
        "devset": {
            "status": "incomplete",
            "file_count": 0, "pdf_count": 0,
            "docx_count": 0,
            "content_group_count": 0,
            "categories_covered": []},
        "summary": {},
        "per_doc": [],
        "expected_failures": [{
            "doc_id": "efx",
            "expected_error_code": "file_not_found",
            "actual_error_code": "file_not_found",
            "matches": True}]}


def _man(ef=None):
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d", "path": "a.pdf",
             "source_type": "pdf"}],
        "expected_failures": [
            ef if ef is not None else {
                "doc_id": "e", "path": "x.pdf",
                "expected_error_code": "c"}]}
    return m


def _ann(**kw):
    a = {
        "annotation_version": "1.0",
        "doc_id": "d",
        "chunk_boundary_anchors": [
            {"marker": "m", "position": "after"}]}
    a.update(kw)
    return a


# ---------- 基板 ----------

def test_base_report_valid_batch550():
    validate(_rep(),
             "evaluation-report.schema.json")


# ---------- report ef 闭 4 键 ----------

def test_report_ef_source_pdf_rejected_batch550():
    r = _rep()
    r["expected_failures"][0]["source_type"] = "pdf"
    try:
        validate(r, "evaluation-report.schema.json")
        raise AssertionError("should reject")
    except schema_mod.EvalSchemaError as e:
        assert "'source_type' was unexpected" in str(e)


def test_report_ef_source_txt_rejected_batch550():
    r = _rep()
    r["expected_failures"][0]["source_type"] = "txt"
    try:
        validate(r, "evaluation-report.schema.json")
        raise AssertionError("should reject")
    except schema_mod.EvalSchemaError as e:
        assert "'source_type' was unexpected" in str(e)


# ---------- manifest ef 收枚举 ----------

def test_manifest_ef_source_txt_valid_batch550():
    ef = {"doc_id": "e", "path": "x.pdf",
          "expected_error_code": "c",
          "source_type": "txt"}
    validate(_man(ef), "manifest.schema.json")


def test_manifest_ef_source_pdf_valid_batch550():
    ef = {"doc_id": "e", "path": "x.pdf",
          "expected_error_code": "c",
          "source_type": "pdf"}
    validate(_man(ef), "manifest.schema.json")


# ---------- report ef 空串宽 ----------

def test_report_ef_docid_empty_valid_batch550():
    r = _rep()
    r["expected_failures"][0]["doc_id"] = ""
    validate(r, "evaluation-report.schema.json")


def test_report_ef_eec_empty_valid_batch550():
    r = _rep()
    r["expected_failures"][0][
        "expected_error_code"] = ""
    validate(r, "evaluation-report.schema.json")


def test_report_ef_actual_null_valid_batch550():
    r = _rep()
    r["expected_failures"][0][
        "actual_error_code"] = None
    r["expected_failures"][0]["matches"] = False
    validate(r, "evaluation-report.schema.json")


def test_report_ef_all_empty_valid_batch550():
    r = _rep()
    r["expected_failures"][0] = {
        "doc_id": "", "expected_error_code": "",
        "actual_error_code": None,
        "matches": False}
    validate(r, "evaluation-report.schema.json")


def test_report_ef_matches_str_rejected_batch550():
    r = _rep()
    r["expected_failures"][0]["matches"] = "true"
    try:
        validate(r, "evaluation-report.schema.json")
        raise AssertionError("should reject")
    except schema_mod.EvalSchemaError as e:
        assert "'true' is not of type 'boolean'" \
            in str(e)


# ---------- manifest ef 空串拒 ----------

def test_manifest_ef_docid_empty_rejected_batch550():
    ef = {"doc_id": "", "path": "x.pdf",
          "expected_error_code": "c"}
    try:
        validate(_man(ef), "manifest.schema.json")
        raise AssertionError("should reject")
    except schema_mod.EvalSchemaError as e:
        assert "'' should be non-empty" in str(e)


def test_manifest_ef_eec_empty_rejected_batch550():
    ef = {"doc_id": "e", "path": "x.pdf",
          "expected_error_code": ""}
    try:
        validate(_man(ef), "manifest.schema.json")
        raise AssertionError("should reject")
    except schema_mod.EvalSchemaError as e:
        assert "'' should be non-empty" in str(e)


def test_manifest_ef_path_empty_rejected_batch550():
    ef = {"doc_id": "e", "path": "",
          "expected_error_code": "c"}
    try:
        validate(_man(ef), "manifest.schema.json")
        raise AssertionError("should reject")
    except schema_mod.EvalSchemaError as e:
        assert "'' should be non-empty" in str(e)


# ---------- provenance 内层 report_version ----------

def test_provenance_missing_report_version_batch550():
    r = _rep()
    del r["provenance"]["report_version"]
    try:
        validate(r, "evaluation-report.schema.json")
        raise AssertionError("should reject")
    except schema_mod.EvalSchemaError as e:
        assert ("'report_version' is a required "
                "property") in str(e)
        assert "path=['provenance']" in str(e)


def test_provenance_report_version_freeform_batch550():
    r = _rep()
    r["provenance"]["report_version"] = "9.9"
    validate(r, "evaluation-report.schema.json")


# ---------- annotation reason 空串宽 ----------

def test_annotation_reason_empty_valid_batch550():
    a = _ann(chunk_boundary_anchors=[
        {"marker": "m", "position": "after",
         "reason": ""}])
    validate(a, "annotation.schema.json")


def test_annotation_reason_nonempty_valid_batch550():
    a = _ann(chunk_boundary_anchors=[
        {"marker": "m", "position": "after",
         "reason": "manual check"}])
    validate(a, "annotation.schema.json")


def test_annotation_anchors_nonarray_rejected_batch550():
    a = _ann(chunk_boundary_anchors="x")
    try:
        validate(a, "annotation.schema.json")
        raise AssertionError("should reject")
    except schema_mod.EvalSchemaError as e:
        assert "'x' is not of type 'array'" in str(e)


def test_annotation_anchors_empty_valid_batch550():
    validate(_ann(chunk_boundary_anchors=[]),
             "annotation.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch550():
    src = _src()
    assert "class EvalSchemaError(Exception):" \
        in src
    assert "def validate(" in src
    assert "Schema 文件不存在" in src


def test_source_open_count_batch550():
    assert _src().count("open(") == 2


# ---------- forbidden tokens 第七百九十二批 ----------

def test_source_no_eval_batch550():
    assert "eval(" not in _src()


def test_source_no_exec_batch550():
    assert "exec(" not in _src()


def test_source_no_compile_batch550():
    assert "compile(" not in _src()


def test_source_no_globals_batch550():
    assert "globals(" not in _src()


def test_source_no_locals_batch550():
    assert "locals(" not in _src()


def test_source_no_os_system_batch550():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch550():
    assert "subprocess" not in _src()


def test_source_no_popen_batch550():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch550():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch550():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch550():
    assert "socket" not in _src()


def test_source_no_requests_batch550():
    assert "requests" not in _src()


def test_source_no_urllib_batch550():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch550():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch550():
    assert "yield" not in _src()


def test_source_no_async_await_batch550():
    assert "async " not in _src()
    assert "await " not in _src()
