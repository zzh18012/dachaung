r"""跨 parser 同文本对照测试 - 第二轮（Round 1410）。

新角度（probe 实证）：R1403 四 parser 同文本板在指标层的
横向对照（历史指标测试都在 pdf/docx 上，四 stdlib 类型的
指标行为从未并排锁）：
- pdfloc/docxloc 四类全 null（not_pdf_document /
  not_docx_document）
- hbc：有 heading 的 md/html/ipynb 全 1.0；**txt 无
  heading → null + no_heading_elements**
- tpe 四类全 True；sdc 无 expectations → null；
  sdc 算术 = 逐类 abs 差求和（{heading:2, paragraph:5}
  对 {paragraph:2} → 2+3=5）
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.pipeline import process_single


_NB = json.dumps({
    "cells": [
        {"cell_type": "markdown",
         "metadata": {},
         "source": [
             "# Same Title\n",
             "Same body text "
             "here.\n"]}],
    "metadata": {},
    "nbformat": 4,
    "nbformat_minor": 5})

_BOARDS = {
    "markdown": (
        "# Same Title\n\n"
        "Same body text here.\n",
        "a.md"),
    "html": (
        "<html><body>"
        "<h1>Same Title</h1>"
        "<p>Same body text here.</p>"
        "</body></html>",
        "b.html"),
    "text": (
        "Same Title\n\n"
        "Same body text here.\n",
        "c.txt"),
    "ipynb": (_NB, "d.ipynb"),
}


def _metrics(tmp_path, parser,
             expectations=None):
    content, name = _BOARDS[parser]
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    doc, errors = process_single(
        p, None, parser_name=parser,
        max_chars=800)
    assert errors == []
    from evaluation.metrics import \
        compute_automatic_metrics
    return compute_automatic_metrics(
        doc.to_dict(), None, parser,
        expectations)


# ---------- locator 指标 ----------

def test_pdfloc_null_all_four(
        tmp_path):
    for parser in _BOARDS:
        m = _metrics(tmp_path,
                     parser)
        assert m[
            "pdf_locator_valid_ratio"
        ] == {"value": None,
              "reason":
                  "not_pdf_document"}


def test_docxloc_null_all_four(
        tmp_path):
    for parser in _BOARDS:
        m = _metrics(tmp_path,
                     parser)
        assert m[
            "docx_locator_valid_ratio"
        ] == {"value": None,
              "reason":
                  "not_docx_document"}


# ---------- hbc ----------

def test_hbc_one_for_heading_parsers(
        tmp_path):
    for parser in ("markdown",
                   "html",
                   "ipynb"):
        m = _metrics(tmp_path,
                     parser)
        assert m[
            "heading_boundary_"
            "compliance"] == {
            "value": 1.0,
            "reason": None}


def test_hbc_txt_no_heading_elements(
        tmp_path):
    m = _metrics(tmp_path, "text")
    assert m[
        "heading_boundary_"
        "compliance"] == {
        "value": None,
        "reason":
            "no_heading_elements"}


# ---------- 文本与计数 ----------

def test_tpe_true_all_four(
        tmp_path):
    for parser in _BOARDS:
        m = _metrics(tmp_path,
                     parser)
        assert m[
            "text_preservation_equal"
        ] == {"value": True,
              "reason": None}


def test_ect_three_heading(
        tmp_path):
    for parser in ("markdown",
                   "html",
                   "ipynb"):
        m = _metrics(tmp_path,
                     parser)
        assert m[
            "element_count_by_type"
        ]["value"] == {
            "heading": 1,
            "paragraph": 1}


def test_ect_txt_paragraphs(
        tmp_path):
    m = _metrics(tmp_path, "text")
    assert m[
        "element_count_by_type"
    ]["value"] == {"paragraph": 2}


# ---------- sdc ----------

def test_sdc_null_no_expectations(
        tmp_path):
    for parser in _BOARDS:
        m = _metrics(tmp_path,
                     parser)
        assert m[
            "silent_drop_count"
        ] == {"value": None,
              "reason":
                  "no_expectations"}


def test_sdc_txt_exact_zero(
        tmp_path):
    m = _metrics(
        tmp_path, "text",
        {"element_count_by_type":
         {"paragraph": 2}})
    assert m[
        "silent_drop_count"] == {
        "value": 0, "reason": None}


def test_sdc_txt_missing_type(
        tmp_path):
    """期望 heading 1、实际 0 →
    abs 差 1。"""
    m = _metrics(
        tmp_path, "text",
        {"element_count_by_type":
         {"heading": 1}})
    assert m[
        "silent_drop_count"] == {
        "value": 1, "reason": None}


def test_sdc_txt_abs_diff_sum(
        tmp_path):
    """{heading:2, paragraph:5}
    对实际 {paragraph:2}：
    |2-0|+|5-2| = 5。"""
    m = _metrics(
        tmp_path, "text",
        {"element_count_by_type":
         {"heading": 2,
          "paragraph": 5}})
    assert m[
        "silent_drop_count"] == {
        "value": 5, "reason": None}


# ---------- irer ----------

def test_irer_null_no_images(
        tmp_path):
    for parser in _BOARDS:
        m = _metrics(tmp_path,
                     parser)
        assert m[
            "image_resource_"
            "exists_ratio"] == {
            "value": None,
            "reason":
                "no_image_elements"}
