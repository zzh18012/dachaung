"""evaluation/schema.py 第五百八十九轮 edges 测试（Round 1358）。

补强 edges153 未触及的角度（第七百三十批，probe 实证）。

新角度（summary/metric 开放 vs 其余全闭合）：
- **summary 开放**——
  summary["zzz"]
  任意键 VALID，
  counts 内层
  junk 也 VALID
  （但 summary 本身
  必须是 object）
- **metric 条目
  开放**——缺
  value 只剩
  reason VALID；
  value 可以是
  字符串
- **闭合面**——
  report 顶层/
  devset/
  provenance/ef/
  per_doc/wall/
  manifest 顶层
  与 documents/
  annotation 顶层
  与 anchor/
  heading 条目
  全部 zzz 拒
- **heading_order
  约束**——level
  min 1（0 拒带
  path）、text
  非空
- forbidden tokens 第七百九十七批（open 2）
"""

from __future__ import annotations

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
        "summary": {}, "per_doc": [],
        "expected_failures": []}


_WALL = {"total": 1.0, "parse": None, "chunk": None,
         "parse_reason": "not_instrumented",
         "chunk_reason": "not_instrumented"}


def _man():
    return {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d", "path": "a.pdf",
             "source_type": "pdf"}]}


def _ann():
    return {
        "annotation_version": "1.0",
        "doc_id": "d",
        "chunk_boundary_anchors": [
            {"marker": "m", "position": "after"}]}


def _rej(obj, schema, needle):
    try:
        validate(obj, schema)
        raise AssertionError("should reject")
    except schema_mod.EvalSchemaError as e:
        assert needle in str(e)


# ---------- summary 开放 ----------

def test_summary_open_key_valid_batch556():
    r = _rep()
    r["summary"]["zzz"] = 1
    validate(r, "evaluation-report.schema.json")


def test_summary_nested_junk_valid_batch556():
    r = _rep()
    r["summary"]["counts"] = {
        "zzz": {"sum": 1, "junk": [1, 2]}}
    validate(r, "evaluation-report.schema.json")


def test_summary_empty_valid_batch556():
    validate(_rep(), "evaluation-report.schema.json")


def test_summary_string_rejected_batch556():
    r = _rep()
    r["summary"] = "not a dict"
    _rej(r, "evaluation-report.schema.json",
         "'not a dict' is not of type 'object'")


def test_summary_list_rejected_batch556():
    r = _rep()
    r["summary"] = []
    _rej(r, "evaluation-report.schema.json",
         "is not of type 'object'")


# ---------- metric 条目开放 ----------

def test_metric_reason_only_valid_batch556():
    r = _rep()
    r["per_doc"] = [{
        "doc_id": "d", "source_type": "docx",
        "metrics": {"anything_named": {
            "reason": "x"}},
        "wall_time_seconds": dict(_WALL)}]
    validate(r, "evaluation-report.schema.json")


def test_metric_value_string_valid_batch556():
    r = _rep()
    r["per_doc"] = [{
        "doc_id": "d", "source_type": "docx",
        "metrics": {"m": {"value": "any string"}},
        "wall_time_seconds": dict(_WALL)}]
    validate(r, "evaluation-report.schema.json")


def test_metric_empty_entry_valid_batch556():
    r = _rep()
    r["per_doc"] = [{
        "doc_id": "d", "source_type": "docx",
        "metrics": {"m": {}},
        "wall_time_seconds": dict(_WALL)}]
    validate(r, "evaluation-report.schema.json")


# ---------- 闭合面：report 侧 ----------

def test_report_top_closed_batch556():
    r = _rep()
    r["zzz"] = 1
    _rej(r, "evaluation-report.schema.json",
         "'zzz' was unexpected")


def test_devset_closed_batch556():
    r = _rep()
    r["devset"]["zzz"] = 1
    _rej(r, "evaluation-report.schema.json",
         "'zzz' was unexpected")


def test_provenance_closed_batch556():
    r = _rep()
    r["provenance"]["zzz"] = 1
    _rej(r, "evaluation-report.schema.json",
         "'zzz' was unexpected")


def test_ef_entry_closed_batch556():
    r = _rep()
    r["expected_failures"] = [{
        "doc_id": "e", "expected_error_code": "c",
        "actual_error_code": None, "matches": False,
        "zzz": 1}]
    _rej(r, "evaluation-report.schema.json",
         "'zzz' was unexpected")


def test_per_doc_entry_closed_batch556():
    r = _rep()
    r["per_doc"] = [{
        "doc_id": "d", "source_type": "docx",
        "metrics": {},
        "wall_time_seconds": dict(_WALL),
        "extra": 1}]
    _rej(r, "evaluation-report.schema.json",
         "'extra' was unexpected")


def test_wall_entry_closed_batch556():
    r = _rep()
    r["per_doc"] = [{
        "doc_id": "d", "source_type": "docx",
        "metrics": {},
        "wall_time_seconds": {
            **_WALL, "zzz": 1}}]
    _rej(r, "evaluation-report.schema.json",
         "'zzz' was unexpected")


# ---------- 闭合面：manifest 侧 ----------

def test_manifest_top_closed_batch556():
    m = _man()
    m["zzz"] = 1
    _rej(m, "manifest.schema.json",
         "'zzz' was unexpected")


def test_manifest_doc_entry_closed_batch556():
    m = _man()
    m["documents"][0]["zzz"] = 1
    _rej(m, "manifest.schema.json",
         "'zzz' was unexpected")


# ---------- 闭合面：annotation 侧 ----------

def test_annotation_top_closed_batch556():
    a = _ann()
    a["zzz"] = 1
    _rej(a, "annotation.schema.json",
         "'zzz' was unexpected")


def test_anchor_entry_closed_batch556():
    a = _ann()
    a["chunk_boundary_anchors"][0]["zzz"] = 1
    _rej(a, "annotation.schema.json",
         "'zzz' was unexpected")


def test_heading_entry_closed_batch556():
    a = _ann()
    a["heading_order"] = [
        {"level": 1, "text": "t", "zzz": 1}]
    _rej(a, "annotation.schema.json",
         "'zzz' was unexpected")


# ---------- heading_order 约束 ----------

def test_heading_level_zero_rejected_batch556():
    a = _ann()
    a["heading_order"] = [{"level": 0,
                           "text": "a"}]
    _rej(a, "annotation.schema.json",
         "0 is less than the minimum of 1")


def test_heading_level_zero_path_batch556():
    a = _ann()
    a["heading_order"] = [{"level": 0,
                           "text": "a"}]
    try:
        validate(a, "annotation.schema.json")
        raise AssertionError("should reject")
    except schema_mod.EvalSchemaError as e:
        assert "path=['heading_order', 0, " \
            "'level']" in str(e)


def test_heading_text_empty_rejected_batch556():
    a = _ann()
    a["heading_order"] = [{"level": 1,
                           "text": ""}]
    _rej(a, "annotation.schema.json",
         "'' should be non-empty")


def test_heading_valid_batch556():
    a = _ann()
    a["heading_order"] = [{"level": 1, "text": "t"}]
    validate(a, "annotation.schema.json")


def test_heading_deep_level_valid_batch556():
    a = _ann()
    a["heading_order"] = [
        {"level": 6, "text": "deep"}]
    validate(a, "annotation.schema.json")


# ---------- 双开放面对照 ----------

def test_open_vs_closed_contrast_batch556():
    r_open = _rep()
    r_open["summary"]["zzz"] = 1
    validate(r_open,
             "evaluation-report.schema.json")
    r_closed = _rep()
    r_closed["devset"]["zzz"] = 1
    _rej(r_closed,
         "evaluation-report.schema.json",
         "'zzz' was unexpected")


def test_metric_open_but_per_doc_closed_batch556():
    r = _rep()
    r["per_doc"] = [{
        "doc_id": "d", "source_type": "docx",
        "metrics": {"m": {"value": True,
                          "reason": None,
                          "foo": 1}},
        "wall_time_seconds": dict(_WALL)}]
    validate(r, "evaluation-report.schema.json")
    r["per_doc"][0]["bar"] = 2
    _rej(r, "evaluation-report.schema.json",
         "'bar' was unexpected")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch556():
    src = _src()
    assert "class EvalSchemaError(Exception):" \
        in src
    assert "def validate(" in src
    assert "Schema 文件不存在" in src


def test_source_open_count_batch556():
    assert _src().count("open(") == 2


# ---------- forbidden tokens 第七百九十七批 ----------

def test_source_no_eval_batch556():
    assert "eval(" not in _src()


def test_source_no_exec_batch556():
    assert "exec(" not in _src()


def test_source_no_compile_batch556():
    assert "compile(" not in _src()


def test_source_no_globals_batch556():
    assert "globals(" not in _src()


def test_source_no_locals_batch556():
    assert "locals(" not in _src()


def test_source_no_os_system_batch556():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch556():
    assert "subprocess" not in _src()


def test_source_no_popen_batch556():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch556():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch556():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch556():
    assert "socket" not in _src()


def test_source_no_requests_batch556():
    assert "requests" not in _src()


def test_source_no_urllib_batch556():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch556():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch556():
    assert "yield" not in _src()


def test_source_no_async_await_batch556():
    assert "async " not in _src()
    assert "await " not in _src()
