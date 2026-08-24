r"""evaluation/report.py 边角测试 - 第一百五十四轮（Round 1380）。

新角度（probe 实证，历史 aggregate 板全是手拼 metrics dict，从未
用真实管线产物）：aggregate_summary 吃 process_single +
compute_automatic_metrics 的真实结果——
- markdown + text 双好文档：hbc macro 只 1 个参与（text 文档
  no_heading_elements → not_evaluated +1）——null 的两种来源
  （pipeline_failed / no_heading_elements）在聚合层都算
  not_evaluated
- markdown 好 + ipynb 坏（真实 ParserError 透传）：rate 0.5、
  counts 只 1 个参与
- silent_drop_total 无 expectations 全程 None
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.pipeline import process_single
from evaluation.metrics import compute_automatic_metrics
from evaluation.report import aggregate_summary


def _pd(tmp_path, fn, parser, st, content,
        expectations=None):
    (tmp_path / fn).write_text(content,
                               encoding="utf-8")
    doc, errors = process_single(
        tmp_path / fn, None,
        parser_name=parser, max_chars=800)
    assert errors == []
    m = compute_automatic_metrics(
        doc.to_dict(), None, st, expectations)
    return {
        "doc_id": fn, "source_type": st,
        "metrics": m,
        "wall_time_seconds": {
            "total": 0.5, "parse": None,
            "chunk": None,
            "parse_reason": "not_instrumented",
            "chunk_reason": "not_instrumented"}}


def _md_pd(tmp_path, doc_id="a.md"):
    return _pd(tmp_path, doc_id, "markdown",
               "markdown",
               "# H\n\npara one two\n")


def _txt_pd(tmp_path, doc_id="b.txt"):
    return _pd(tmp_path, doc_id, "text",
               "text", "plain\n\nsecond\n")


# ---------- 双好文档 ----------

def test_counts_sum_both_docs(tmp_path):
    s = aggregate_summary(
        [_md_pd(tmp_path), _txt_pd(tmp_path)])
    assert s["counts"][
        "element_count_total"] == {
        "sum": 4, "participating_docs": 2}


def test_success_rate_one(tmp_path):
    s = aggregate_summary(
        [_md_pd(tmp_path), _txt_pd(tmp_path)])
    assert s["success_rates"][
        "pipeline_success"] == {
        "success_count": 2, "total": 2,
        "rate": 1.0}


def test_hbc_text_doc_not_evaluated(tmp_path):
    s = aggregate_summary(
        [_md_pd(tmp_path), _txt_pd(tmp_path)])
    assert s["ratio_macro_averages"][
        "heading_boundary_compliance"] == {
        "macro_average": 1.0,
        "participating_docs": 1,
        "not_evaluated": 1}


def test_tpe_both_participate(tmp_path):
    s = aggregate_summary(
        [_md_pd(tmp_path), _txt_pd(tmp_path)])
    assert s["ratio_macro_averages"][
        "text_preservation_equal"] == {
        "macro_average": 1.0,
        "participating_docs": 2,
        "not_evaluated": 0}


def test_sdt_none_no_expectations(tmp_path):
    s = aggregate_summary(
        [_md_pd(tmp_path), _txt_pd(tmp_path)])
    assert s["silent_drop_total"] is None


# ---------- 好 + 坏混合（真实错误透传） ----------

def _bad_ipynb_pd(tmp_path):
    (tmp_path / "bad.ipynb").write_text(
        "not json", encoding="utf-8")
    doc, errors = process_single(
        tmp_path / "bad.ipynb", None,
        parser_name="ipynb", max_chars=800)
    assert doc is None and errors
    m = compute_automatic_metrics(
        None, errors[0].to_dict(), "ipynb",
        None)
    return {
        "doc_id": "bad.ipynb",
        "source_type": "ipynb", "metrics": m,
        "wall_time_seconds": {
            "total": 0.3, "parse": None,
            "chunk": None,
            "parse_reason": "not_instrumented",
            "chunk_reason": "not_instrumented"}}


def test_mixed_rate_half(tmp_path):
    s = aggregate_summary(
        [_md_pd(tmp_path),
         _bad_ipynb_pd(tmp_path)])
    assert s["success_rates"][
        "pipeline_success"] == {
        "success_count": 1, "total": 2,
        "rate": 0.5}


def test_mixed_counts_one_participant(tmp_path):
    s = aggregate_summary(
        [_md_pd(tmp_path),
         _bad_ipynb_pd(tmp_path)])
    assert s["counts"][
        "element_count_total"] == {
        "sum": 2, "participating_docs": 1}


def test_mixed_hbc_failed_not_evaluated(
        tmp_path):
    s = aggregate_summary(
        [_md_pd(tmp_path),
         _bad_ipynb_pd(tmp_path)])
    assert s["ratio_macro_averages"][
        "heading_boundary_compliance"] == {
        "macro_average": 1.0,
        "participating_docs": 1,
        "not_evaluated": 1}


def test_mixed_tpe_failed_not_evaluated(
        tmp_path):
    s = aggregate_summary(
        [_md_pd(tmp_path),
         _bad_ipynb_pd(tmp_path)])
    assert s["ratio_macro_averages"][
        "text_preservation_equal"] == {
        "macro_average": 1.0,
        "participating_docs": 1,
        "not_evaluated": 1}


# ---------- expectations 参与 sdt ----------

def test_sdt_participates_with_expectations(
        tmp_path):
    md = _md_pd(tmp_path,
                "e.md")
    # 重建带 expectations 的版本
    (tmp_path / "e.md").write_text(
        "# H\n\npara one two\n",
        encoding="utf-8")
    doc, _ = process_single(
        tmp_path / "e.md", None,
        parser_name="markdown", max_chars=800)
    m = compute_automatic_metrics(
        doc.to_dict(), None, "markdown",
        {"element_count_by_type": {
            "heading": 1, "paragraph": 1}})
    per_doc = [{
        "doc_id": "e.md",
        "source_type": "markdown",
        "metrics": m,
        "wall_time_seconds": {
            "total": 0.5, "parse": None,
            "chunk": None,
            "parse_reason": "not_instrumented",
            "chunk_reason": "not_instrumented"}}]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 0


# ---------- 聚合结构 ----------

def test_summary_top_keys(tmp_path):
    s = aggregate_summary(
        [_md_pd(tmp_path)])
    assert list(s.keys()) == [
        "counts", "success_rates",
        "ratio_macro_averages",
        "silent_drop_total"]


def test_success_rates_only_pipeline(tmp_path):
    s = aggregate_summary(
        [_md_pd(tmp_path)])
    assert list(s["success_rates"].keys()) == \
        ["pipeline_success"]
