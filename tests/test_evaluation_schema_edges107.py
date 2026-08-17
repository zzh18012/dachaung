"""evaluation/schema.py 第四百零四轮 edges 测试（Round 960）。

补强 edges106 未触及的角度（第三百三十六批，probe 实证）。

新角度（def 级清单第二批）：
- AS 顶层恰 7 属性：[annotation_version, annotator,
  chunk_boundary_anchors, date, doc_id,
  figure_caption_pairs, heading_order]（annotator/date/
  pairs/order 四项可选——required 仅 2 项）
- chunk_boundary_anchors：array + items $ref
  #/$defs/boundary_anchor
- MS document def：8 属性 required 3；source_type enum
  [pdf, docx]
- MS expected_failure def：4 属性 required 3
  （source_type 可选）
- RS provenance def：required 9 项有序 +
  additionalProperties False（封闭）
- RS devset def：6 属性；status enum
  [complete, incomplete]
- RS summary def：恰 4 属性 [counts,
  ratio_macro_averages, silent_drop_total, success_rates]
- RS per_doc def：4 属性；metrics 仅 {"type": "object"}
  开放（不锁指标键集）
- RS 顶层 expected_failures：array + $ref
  expected_failure_result（存在但不在 required）
- forbidden tokens 第四百三十批（open 2）
"""

from __future__ import annotations

import inspect

import evaluation.schema as schema_mod
from evaluation.schema import load_schema

_MS = load_schema("manifest.schema.json")
_RS = load_schema("evaluation-report.schema.json")
_AS = load_schema("annotation.schema.json")


# ---------- AS 顶层 ----------

def test_annotation_props_seven_batch158():
    assert sorted(_AS["properties"]) == [
        "annotation_version", "annotator",
        "chunk_boundary_anchors", "date", "doc_id",
        "figure_caption_pairs", "heading_order"]
    cba = _AS["properties"]["chunk_boundary_anchors"]
    assert cba["type"] == "array"
    assert cba["items"] == {"$ref": "#/$defs/boundary_anchor"}


# ---------- MS document def ----------

def test_document_def_props_batch158():
    d = _MS["$defs"]["document"]
    assert sorted(d["properties"]) == [
        "annotation_file", "categories", "doc_id",
        "expectations", "paired_with", "path", "sha256",
        "source_type"]
    assert d["required"] == ["doc_id", "path",
                             "source_type"]
    assert d["properties"]["source_type"] == {
        "enum": ["pdf", "docx"]}


# ---------- MS expected_failure def ----------

def test_expected_failure_def_props_batch158():
    ef = _MS["$defs"]["expected_failure"]
    assert sorted(ef["properties"]) == [
        "doc_id", "expected_error_code", "path",
        "source_type"]
    assert ef["required"] == ["doc_id", "path",
                              "expected_error_code"]


# ---------- RS provenance def ----------

def test_provenance_def_nine_required_closed_batch158():
    prov = _RS["$defs"]["provenance"]
    assert prov["required"] == [
        "git_commit", "git_dirty", "evaluator_version",
        "report_version", "parser_name", "parser_version",
        "dependencies", "max_chars",
        "run_timestamp_iso"]
    assert prov["additionalProperties"] is False


# ---------- RS devset def ----------

def test_devset_def_props_batch158():
    ds = _RS["$defs"]["devset"]
    assert sorted(ds["properties"]) == [
        "categories_covered", "content_group_count",
        "docx_count", "file_count", "pdf_count", "status"]
    assert ds["properties"]["status"] == {
        "enum": ["complete", "incomplete"]}


# ---------- RS summary def ----------

def test_summary_def_four_props_batch158():
    ss = _RS["$defs"]["summary"]["properties"]
    assert sorted(ss) == ["counts", "ratio_macro_averages",
                          "silent_drop_total",
                          "success_rates"]


# ---------- RS per_doc def ----------

def test_per_doc_def_metrics_open_batch158():
    pd = _RS["$defs"]["per_doc"]["properties"]
    assert sorted(pd) == ["doc_id", "metrics",
                          "source_type",
                          "wall_time_seconds"]
    assert pd["metrics"] == {"type": "object"}


# ---------- RS 顶层 expected_failures ----------

def test_rs_top_expected_failures_optional_batch158():
    ef = _RS["properties"]["expected_failures"]
    assert ef == {
        "type": "array",
        "items": {"$ref": "#/$defs/expected_failure_result"}}
    assert "expected_failures" not in _RS["required"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch158():
    src = _src()
    assert 'SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"' in src
    assert "raise FileNotFoundError(f\"Schema 文件不存在: {p}\")" in src
    assert "flat.append(" in src


# ---------- forbidden tokens 第四百三十批 ----------

def test_source_no_eval_batch158():
    assert "eval(" not in _src()


def test_source_no_exec_batch158():
    assert "exec(" not in _src()


def test_source_no_compile_batch158():
    assert "compile(" not in _src()


def test_source_no_globals_batch158():
    assert "globals(" not in _src()


def test_source_no_locals_batch158():
    assert "locals(" not in _src()


def test_source_no_os_system_batch158():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch158():
    assert "subprocess" not in _src()


def test_source_no_popen_batch158():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch158():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch158():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch158():
    assert "socket" not in _src()


def test_source_no_requests_batch158():
    assert "requests" not in _src()


def test_source_no_urllib_batch158():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch158():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch158():
    assert "yield" not in _src()


def test_source_no_async_await_batch158():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch158():
    assert _src().count("open(") == 2
