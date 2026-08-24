r"""evaluation/metrics.py 边角测试 - 第一百六十八轮（Round 1368）。

新角度（probe 实证，历史 metrics 板只用 pdf/docx/text 手工 dict 或
fallback 产物，从未覆盖 markdown/html/ipynb 真实管线产物）：
- compute_automatic_metrics 直接吃 process_single 的 markdown/html/
  ipynb 产物（source_type 同名传入）
- 非 pdf/docx 文档：两个 locator 比例均 null（not_pdf_document /
  not_docx_document）——其余指标照常计算
- ipynb：heading_boundary_compliance 1.0（真实管线 heading 硬边界）
- html：image_resource_exists_ratio 0.0（不存在）→ 1.0
  （image_base_dir 下真实文件）
- markdown：表格 + 列表产物 ect 结构、sdc 对 expectations 的差值
- ipynb 失败路径：error_code 透传、全部值指标 null pipeline_failed
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.pipeline import process_single
from evaluation.metrics import compute_automatic_metrics


MD = ("# T\n\nalpha beta\n\n- a\n- b\n\n"
      "| x | y |\n| --- | --- |\n| 1 | 2 |\n")

NB = {
    "cells": [
        {"cell_type": "markdown",
         "source": ["# H\n", "para one two\n"]},
        {"cell_type": "code",
         "source": "print(1)\nprint(2)"},
        {"cell_type": "markdown",
         "source": "## Sub\n\ntail text"}],
    "metadata": {}, "nbformat": 4,
}

HTML_NOIMG = ("<html><body><h1>H</h1><p>para text</p>"
              "<p>after</p></body></html>")


def _md_doc(tmp_path):
    (tmp_path / "d.md").write_text(MD, encoding="utf-8")
    doc, errors = process_single(
        tmp_path / "d.md", None,
        parser_name="markdown", max_chars=400)
    assert errors == []
    return doc


def _ipynb_doc(tmp_path):
    (tmp_path / "n.ipynb").write_text(
        json.dumps(NB, ensure_ascii=False),
        encoding="utf-8")
    doc, errors = process_single(
        tmp_path / "n.ipynb", None,
        parser_name="ipynb", max_chars=200)
    assert errors == []
    return doc


def _html_doc(tmp_path, html=HTML_NOIMG):
    (tmp_path / "d.html").write_text(html, encoding="utf-8")
    doc, errors = process_single(
        tmp_path / "d.html", None,
        parser_name="html", max_chars=400)
    assert errors == []
    return doc


# ---------- markdown 产物 ----------

def test_md_ect_structure(tmp_path):
    m = compute_automatic_metrics(
        _md_doc(tmp_path).to_dict(), None, "markdown",
        None)
    assert m["element_count_by_type"]["value"] == {
        "heading": 1, "paragraph": 1,
        "list_item": 2, "table": 1}


def test_md_total_five(tmp_path):
    m = compute_automatic_metrics(
        _md_doc(tmp_path).to_dict(), None, "markdown",
        None)
    assert m["element_count_total"]["value"] == 5


def test_md_locator_ratios_both_null(tmp_path):
    m = compute_automatic_metrics(
        _md_doc(tmp_path).to_dict(), None, "markdown",
        None)
    assert m["pdf_locator_valid_ratio"] == {
        "value": None, "reason": "not_pdf_document"}
    assert m["docx_locator_valid_ratio"] == {
        "value": None, "reason": "not_docx_document"}


def test_md_hbc_one(tmp_path):
    m = compute_automatic_metrics(
        _md_doc(tmp_path).to_dict(), None, "markdown",
        None)
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


def test_md_tpe_true(tmp_path):
    m = compute_automatic_metrics(
        _md_doc(tmp_path).to_dict(), None, "markdown",
        None)
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
    assert m["text_char_multiset_precision"][
        "value"] == 1.0
    assert m["text_char_multiset_recall"][
        "value"] == 1.0


def test_md_img_null_no_elements(tmp_path):
    m = compute_automatic_metrics(
        _md_doc(tmp_path).to_dict(), None, "markdown",
        None)
    assert m["image_resource_exists_ratio"] == {
        "value": None, "reason": "no_image_elements"}


def test_md_sdc_no_expectations_null(tmp_path):
    m = compute_automatic_metrics(
        _md_doc(tmp_path).to_dict(), None, "markdown",
        None)
    assert m["silent_drop_count"] == {
        "value": None, "reason": "no_expectations"}


def test_md_sdc_matched_zero(tmp_path):
    m = compute_automatic_metrics(
        _md_doc(tmp_path).to_dict(), None, "markdown",
        {"element_count_by_type": {
            "heading": 1, "paragraph": 1,
            "list_item": 2, "table": 1}})
    assert m["silent_drop_count"] == {
        "value": 0, "reason": None}


def test_md_sdc_short_by_one(tmp_path):
    m = compute_automatic_metrics(
        _md_doc(tmp_path).to_dict(), None, "markdown",
        {"element_count_by_type": {
            "heading": 1, "paragraph": 2,
            "list_item": 2, "table": 1}})
    assert m["silent_drop_count"]["value"] == 1


def test_md_schema_valid_true(tmp_path):
    m = compute_automatic_metrics(
        _md_doc(tmp_path).to_dict(), None, "markdown",
        None)
    assert m["schema_valid"] == {
        "value": True, "reason": None}


# ---------- ipynb 产物 ----------

def test_ipynb_ect(tmp_path):
    m = compute_automatic_metrics(
        _ipynb_doc(tmp_path).to_dict(), None, "ipynb",
        None)
    assert m["element_count_by_type"]["value"] == {
        "heading": 2, "paragraph": 3}


def test_ipynb_total_five(tmp_path):
    m = compute_automatic_metrics(
        _ipynb_doc(tmp_path).to_dict(), None, "ipynb",
        None)
    assert m["element_count_total"]["value"] == 5


def test_ipynb_locator_ratios_null(tmp_path):
    m = compute_automatic_metrics(
        _ipynb_doc(tmp_path).to_dict(), None, "ipynb",
        None)
    assert m["pdf_locator_valid_ratio"][
        "reason"] == "not_pdf_document"
    assert m["docx_locator_valid_ratio"][
        "reason"] == "not_docx_document"


def test_ipynb_hbc_one(tmp_path):
    m = compute_automatic_metrics(
        _ipynb_doc(tmp_path).to_dict(), None, "ipynb",
        None)
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


def test_ipynb_text_perfect(tmp_path):
    m = compute_automatic_metrics(
        _ipynb_doc(tmp_path).to_dict(), None, "ipynb",
        None)
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
    assert m["text_char_multiset_precision"][
        "value"] == 1.0
    assert m["text_char_multiset_recall"][
        "value"] == 1.0


def test_ipynb_crir_one(tmp_path):
    m = compute_automatic_metrics(
        _ipynb_doc(tmp_path).to_dict(), None, "ipynb",
        None)
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}


def test_ipynb_sdc_matched_zero(tmp_path):
    m = compute_automatic_metrics(
        _ipynb_doc(tmp_path).to_dict(), None, "ipynb",
        {"element_count_by_type": {
            "heading": 2, "paragraph": 3}})
    assert m["silent_drop_count"]["value"] == 0


# ---------- ipynb 失败路径 ----------

def test_failed_ipynb_success_false():
    m = compute_automatic_metrics(
        None, {"code": "no_extracted_elements"},
        "ipynb", None)
    assert m["pipeline_success"] == {
        "value": False, "reason": None}


def test_failed_ipynb_error_code_passthrough():
    m = compute_automatic_metrics(
        None, {"code": "no_extracted_elements"},
        "ipynb", None)
    assert m["error_code"] == {
        "value": "no_extracted_elements",
        "reason": None}


def test_failed_ipynb_all_value_metrics_null():
    m = compute_automatic_metrics(
        None, {"code": "no_extracted_elements"},
        "ipynb", None)
    for name in ("schema_valid",
                 "element_count_total",
                 "pdf_locator_valid_ratio",
                 "docx_locator_valid_ratio",
                 "image_resource_exists_ratio",
                 "chunk_reference_intact_ratio",
                 "text_preservation_equal",
                 "text_char_multiset_precision",
                 "text_char_multiset_recall",
                 "heading_boundary_compliance",
                 "silent_drop_count"):
        assert m[name] == {
            "value": None,
            "reason": "pipeline_failed"}, name


# ---------- html 产物 ----------

def test_html_ect_with_image(tmp_path):
    html = ("<html><body><h1>H</h1>"
            "<img src='p.png'><p>after</p>"
            "</body></html>")
    m = compute_automatic_metrics(
        _html_doc(tmp_path, html).to_dict(), None,
        "html", None)
    assert m["element_count_by_type"]["value"] == {
        "heading": 1, "paragraph": 1, "image": 1}


def test_html_img_missing_ratio_zero(tmp_path):
    html = ("<html><body><h1>H</h1>"
            "<img src='p.png'><p>after</p>"
            "</body></html>")
    m = compute_automatic_metrics(
        _html_doc(tmp_path, html).to_dict(), None,
        "html", None)
    assert m["image_resource_exists_ratio"] == {
        "value": 0.0, "reason": None}


def test_html_img_existing_ratio_one(tmp_path):
    (tmp_path / "p.png").write_bytes(
        b"\x89PNG\r\n\x1a\n")
    html = ("<html><body><h1>H</h1>"
            "<img src='p.png'><p>after</p>"
            "</body></html>")
    m = compute_automatic_metrics(
        _html_doc(tmp_path, html).to_dict(), None,
        "html", None,
        image_base_dir=tmp_path)
    assert m["image_resource_exists_ratio"] == {
        "value": 1.0, "reason": None}


def test_html_no_img_null(tmp_path):
    m = compute_automatic_metrics(
        _html_doc(tmp_path).to_dict(), None,
        "html", None)
    assert m["image_resource_exists_ratio"] == {
        "value": None, "reason": "no_image_elements"}


def test_html_sdc_three_mismatch(tmp_path):
    html = ("<html><body><h1>H</h1>"
            "<img src='p.png'><p>after</p>"
            "</body></html>")
    m = compute_automatic_metrics(
        _html_doc(tmp_path, html).to_dict(), None,
        "html",
        {"element_count_by_type": {
            "heading": 2, "paragraph": 3, "image": 1}})
    assert m["silent_drop_count"]["value"] == 3


def test_html_hbc_one(tmp_path):
    m = compute_automatic_metrics(
        _html_doc(tmp_path).to_dict(), None,
        "html", None)
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


def test_html_text_perfect_with_image(tmp_path):
    html = ("<html><body><h1>H</h1>"
            "<img src='p.png'><p>after</p>"
            "</body></html>")
    m = compute_automatic_metrics(
        _html_doc(tmp_path, html).to_dict(), None,
        "html", None)
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
