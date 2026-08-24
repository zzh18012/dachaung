r"""app/pipeline.py 边角测试 - 第十四轮（Round 1375）。

退化文档走全栈（probe 实证）：
- image-only notebook → process_single 成功、2 元素、**0 chunk**、
  schema 仍 VALID、JSON 落盘 chunks:[]（分块器跳过 image 后无
  可分块内容——与 no_extracted_elements 不同，解析有产物所以
  不报错）
- metrics 上：chunk_reference_intact_ratio null no_chunks、
  文本三指标 empty_expected_and_actual（tpe True）、
  heading_boundary no_heading_elements、sdc 0
- svg-only html（<title> 被全局 skip 吞掉）→ 0 元素 →
  no_extracted_elements 结构化错误
- markdown 实体/转义字面值穿过 chunker 原样保留
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.pipeline import process_single


IMG_ONLY_NB = json.dumps({
    "cells": [{"cell_type": "markdown",
               "source": "![a](1.png)\n![b](2.png)"}],
    "metadata": {}, "nbformat": 4})

SVG_ONLY = ("<html><body><svg><title>c</title>"
            "</svg></body></html>")


def _run(tmp_path, fn, parser, content, mc=200):
    (tmp_path / fn).write_text(content, encoding="utf-8")
    return process_single(
        tmp_path / fn, tmp_path / "o.json",
        parser_name=parser, max_chars=mc)


# ---------- image-only notebook：0 chunk 成功路径 ----------

def test_img_only_no_errors(tmp_path):
    doc, errors = _run(tmp_path, "n.ipynb", "ipynb",
                       IMG_ONLY_NB)
    assert errors == []
    assert doc is not None


def test_img_only_two_elements(tmp_path):
    doc, _ = _run(tmp_path, "n.ipynb", "ipynb",
                  IMG_ONLY_NB)
    assert [(e.type, e.resource_path)
            for e in doc.elements] == [
        ("image", "1.png"), ("image", "2.png")]


def test_img_only_zero_chunks(tmp_path):
    doc, _ = _run(tmp_path, "n.ipynb", "ipynb",
                  IMG_ONLY_NB)
    assert doc.chunks == []


def test_img_only_schema_still_valid(tmp_path):
    doc, _ = _run(tmp_path, "n.ipynb", "ipynb",
                  IMG_ONLY_NB)
    from app.schema import is_valid
    assert is_valid(doc.to_dict())


def test_img_only_written_empty_chunks(tmp_path):
    _run(tmp_path, "n.ipynb", "ipynb", IMG_ONLY_NB)
    on_disk = json.loads(
        (tmp_path / "o.json").read_text(
            encoding="utf-8"))
    assert on_disk["chunks"] == []
    assert len(on_disk["elements"]) == 2


# ---------- image-only notebook 的 metrics ----------

def _metrics(tmp_path):
    from evaluation.metrics import (
        compute_automatic_metrics)
    doc, _ = _run(tmp_path, "n.ipynb", "ipynb",
                  IMG_ONLY_NB)
    return compute_automatic_metrics(
        doc.to_dict(), None, "ipynb",
        {"element_count_by_type": {"image": 2}})


def test_img_only_crir_no_chunks(tmp_path):
    m = _metrics(tmp_path)
    assert m["chunk_reference_intact_ratio"] == {
        "value": None, "reason": "no_chunks"}


def test_img_only_tpe_true(tmp_path):
    m = _metrics(tmp_path)
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}


def test_img_only_cmp_cmr_empty(tmp_path):
    m = _metrics(tmp_path)
    assert m["text_char_multiset_precision"] == {
        "value": None,
        "reason": "empty_expected_and_actual"}
    assert m["text_char_multiset_recall"] == {
        "value": None,
        "reason": "empty_expected_and_actual"}


def test_img_only_hbc_no_heading(tmp_path):
    m = _metrics(tmp_path)
    assert m["heading_boundary_compliance"] == {
        "value": None,
        "reason": "no_heading_elements"}


def test_img_only_sdc_zero(tmp_path):
    m = _metrics(tmp_path)
    assert m["silent_drop_count"] == {
        "value": 0, "reason": None}


def test_img_only_img_ratio_zero(tmp_path):
    m = _metrics(tmp_path)
    assert m["image_resource_exists_ratio"] == {
        "value": 0.0, "reason": None}


def test_img_only_schema_valid_metric(tmp_path):
    m = _metrics(tmp_path)
    assert m["schema_valid"] == {
        "value": True, "reason": None}


# ---------- svg-only html：0 元素错误路径 ----------

def test_svg_only_no_extracted_elements(tmp_path):
    doc, errors = _run(tmp_path, "d.html",
                       "html", SVG_ONLY)
    assert doc is None
    assert errors[0].code == \
        "no_extracted_elements"


def test_svg_only_details_source_type(tmp_path):
    _, errors = _run(tmp_path, "d.html", "html",
                     SVG_ONLY)
    assert errors[0].details[
        "source_type"] == "html"


def test_svg_only_no_output_written(tmp_path):
    _run(tmp_path, "d.html", "html", SVG_ONLY)
    assert not (tmp_path / "o.json").exists()


# ---------- markdown 字面值穿过 chunker ----------

def test_entities_survive_chunking(tmp_path):
    doc, errors = _run(
        tmp_path, "d.md", "markdown",
        "a &amp; b &lt;c&gt;\n\n"
        "second &nbsp; para\n")
    assert errors == []
    assert doc.chunks[0].text == (
        "a &amp; b &lt;c&gt; "
        "second &nbsp; para")


def test_escapes_survive_chunking(tmp_path):
    doc, errors = _run(
        tmp_path, "d.md", "markdown",
        "literal \\*not em\\* here\n")
    assert errors == []
    assert doc.chunks[0].text == \
        "literal \\*not em\\* here"


def test_footnote_def_survives(tmp_path):
    doc, errors = _run(
        tmp_path, "d.md", "markdown",
        "text[^1]\n\n[^1]: note body\n")
    assert errors == []
    assert doc.chunks[0].text == (
        "text[^1] [^1]: note body")


def test_form_paragraph_survives(tmp_path):
    doc, errors = _run(
        tmp_path, "d.html", "html",
        "<html><body><form>F</form>"
        "<p>after</p></body></html>")
    assert errors == []
    assert doc.chunks[0].text == "Fafter"
