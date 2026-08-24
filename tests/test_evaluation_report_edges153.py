"""evaluation/report.py 第五百八十四轮 edges 测试（Round 1359）。

补强 edges152 未触及的角度（第七百三十一批，probe 实证）。

新角度（.md 假充 docx / 混合板全线 pipeline_failed）：
- **后缀不匹配**
  ——path d.md +
  source_type
  docx → loader
  收（不校验后缀）
  但 fallback
  detect_source_type
  拒 → error_code
  unsupported_type
- **全线 failed**
  ——schema_valid/
  ect/tpe/hbc/crir/
  ect_by_type 全
  {None,
  pipeline_failed}
- **expectations
  失效**——有
  expectations 的
  失败 doc sdc 也是
  pipeline_failed
  （非
  no_expectations）
- **sdt None**——
  无参与者时
  silent_drop_total
  是 None 而非 0
- **混合板**——
  success 1/2
  rate 0.5 + pv
  取自好 doc
- forbidden tokens 第七百九十八批（open 0）
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import evaluation.report as report_mod
from docx import Document
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from evaluation.schema import validate


def _board(tmp_path):
    d = Document()
    d.add_paragraph("one")
    d.save(str(tmp_path / "a.docx"))
    (tmp_path / "d.md").write_text(
        "# T\n\nhello\n", encoding="utf-8")
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "good", "path": "a.docx",
             "source_type": "docx"},
            {"doc_id": "bad", "path": "d.md",
             "source_type": "docx",
             "expectations": {
                 "element_count_by_type": {
                     "paragraph": 1}}}]}),
        encoding="utf-8")
    mf = load_manifest(tmp_path / "m.json",
                       project_root=tmp_path)
    return run_evaluation(mf, tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=800)


def _solo(tmp_path):
    (tmp_path / "d.md").write_text(
        "# T\n\nhello\n", encoding="utf-8")
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "g1", "path": "d.md",
             "source_type": "docx"}]}),
        encoding="utf-8")
    mf = load_manifest(tmp_path / "m.json",
                       project_root=tmp_path)
    return run_evaluation(mf, tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=800)


# ---------- 后缀不匹配（单坏 doc） ----------

def test_md_as_docx_fails_batch557(tmp_path):
    r = _solo(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "pipeline_success"] == {
        "value": False, "reason": None}


def test_md_as_docx_error_code_batch557(
        tmp_path):
    r = _solo(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "error_code"] == {
        "value": "unsupported_type",
        "reason": None}


def test_md_as_docx_source_echo_batch557(
        tmp_path):
    r = _solo(tmp_path)
    assert r["per_doc"][0][
        "source_type"] == "docx"


def test_md_as_docx_rate_zero_batch557(
        tmp_path):
    r = _solo(tmp_path)
    assert r["summary"]["success_rates"][
        "pipeline_success"] == {
        "success_count": 0, "total": 1,
        "rate": 0.0}


def test_md_as_docx_pv_none_batch557(
        tmp_path):
    r = _solo(tmp_path)
    assert r["provenance"][
        "parser_version"] is None


# ---------- 全线 pipeline_failed ----------

def test_solo_schema_valid_failed_batch557(
        tmp_path):
    r = _solo(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "schema_valid"] == {
        "value": None, "reason": "pipeline_failed"}


def test_solo_ect_failed_batch557(tmp_path):
    r = _solo(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "element_count_total"] == {
        "value": None, "reason": "pipeline_failed"}


def test_solo_tpe_failed_batch557(tmp_path):
    r = _solo(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "text_preservation_equal"] == {
        "value": None, "reason": "pipeline_failed"}


def test_solo_wall_float_batch557(tmp_path):
    r = _solo(tmp_path)
    assert isinstance(r["per_doc"][0][
        "wall_time_seconds"]["total"], float)


# ---------- expectations 失效 ----------

def test_failed_with_expectations_sdc_batch557(
        tmp_path):
    r = _board(tmp_path)
    assert r["per_doc"][1]["metrics"][
        "silent_drop_count"] == {
        "value": None, "reason": "pipeline_failed"}


def test_failed_hbc_batch557(tmp_path):
    r = _board(tmp_path)
    assert r["per_doc"][1]["metrics"][
        "heading_boundary_compliance"] == {
        "value": None, "reason": "pipeline_failed"}


def test_failed_ect_by_type_batch557(
        tmp_path):
    r = _board(tmp_path)
    assert r["per_doc"][1]["metrics"][
        "element_count_by_type"] == {
        "value": None, "reason": "pipeline_failed"}


def test_failed_crir_batch557(tmp_path):
    r = _board(tmp_path)
    assert r["per_doc"][1]["metrics"][
        "chunk_reference_intact_ratio"] == {
        "value": None, "reason": "pipeline_failed"}


# ---------- sdt None ----------

def test_solo_sdt_none_batch557(tmp_path):
    assert _solo(tmp_path)["summary"][
        "silent_drop_total"] is None


def test_board_sdt_none_batch557(tmp_path):
    r = _board(tmp_path)
    vals = [p["metrics"]["silent_drop_count"][
        "value"] for p in r["per_doc"]]
    assert all(v is None for v in vals)
    assert r["summary"]["silent_drop_total"] \
        is None


# ---------- 混合板 ----------

def test_board_success_half_batch557(
        tmp_path):
    r = _board(tmp_path)
    assert r["summary"]["success_rates"][
        "pipeline_success"] == {
        "success_count": 1, "total": 2,
        "rate": 0.5}


def test_board_pv_from_good_batch557(
        tmp_path):
    r = _board(tmp_path)
    assert r["provenance"][
        "parser_version"] is not None


def test_board_good_tpe_true_batch557(
        tmp_path):
    r = _board(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "text_preservation_equal"] == {
        "value": True, "reason": None}


def test_board_counts_good_only_batch557(
        tmp_path):
    r = _board(tmp_path)
    assert r["summary"]["counts"] == {
        "element_count_total": {
            "sum": 1, "participating_docs": 1}}


def test_board_tpe_macro_batch557(
        tmp_path):
    r = _board(tmp_path)
    assert r["summary"]["ratio_macro_averages"][
        "text_preservation_equal"] == {
        "macro_average": 1.0,
        "participating_docs": 1,
        "not_evaluated": 1}


def test_board_docx_count_two_batch557(
        tmp_path):
    assert _board(tmp_path)["devset"][
        "docx_count"] == 2


# ---------- 报告合法性 ----------

def test_solo_report_schema_batch557(
        tmp_path):
    validate(_solo(tmp_path),
             "evaluation-report.schema.json")


def test_board_report_schema_batch557(
        tmp_path):
    validate(_board(tmp_path),
             "evaluation-report.schema.json")


def test_board_on_disk_round_trip_batch557(
        tmp_path):
    r = _board(tmp_path)
    on_disk = json.loads(
        (tmp_path / "r.json").read_text(
            encoding="utf-8"))
    assert on_disk == r


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_aggregation_keys_batch557():
    src = _src()
    assert "not_evaluated" in src
    assert "macro_average" in src


def test_source_subprocess_two_batch557():
    assert _src().count("subprocess.run") == 2


def test_source_open_zero_batch557():
    assert _src().count("open(") == 0


# ---------- forbidden tokens 第七百九十八批 ----------

def test_source_no_eval_batch557():
    assert "eval(" not in _src()


def test_source_no_exec_batch557():
    assert "exec(" not in _src()


def test_source_no_compile_batch557():
    assert "compile(" not in _src()


def test_source_no_globals_batch557():
    assert "globals(" not in _src()


def test_source_no_locals_batch557():
    assert "locals(" not in _src()


def test_source_no_os_system_batch557():
    assert "os.system" not in _src()


def test_source_no_popen_batch557():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch557():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch557():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch557():
    assert "socket" not in _src()


def test_source_no_requests_batch557():
    assert "requests" not in _src()


def test_source_no_urllib_batch557():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch557():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch557():
    assert "yield" not in _src()


def test_source_no_async_await_batch557():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch557():
    assert ".call(" not in _src()
