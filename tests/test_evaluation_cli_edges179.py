r"""evaluation/cli.py 边角测试 - 第一百七十九轮（Round 1378）。

新角度（probe 实证，历史 inspect-doc 板只用 fallback/pdf/docx，
仅 edges178 用了 markdown）：
- inspect-doc 直接吃 process_single 的 ipynb/html/text 产物 JSON
  （inspect 路径现场重算 metrics，输入文件本身无 metrics 字段）
- ipynb：'ipynb vstdlib/0.1.0'、ect 'heading=1, paragraph=2'、
  locator 比例 null not_pdf/not_docx、img null no_image_elements
- html：ect 含 image=1、image_resource 0.0000（p.png 不存在）
- text：hbc null no_heading_elements
- image-only ipynb（0 chunk）：counts 'elements=1 chunks=0'、
  crir null no_chunks、cmp/cmr null empty_expected_and_actual、
  tpe true
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path

from app.pipeline import process_single
from evaluation.cli import main as cli_main

NB = json.dumps({
    "cells": [
        {"cell_type": "markdown",
         "source": ["# Head\n", "para text"]},
        {"cell_type": "code",
         "source": "print(1)"}],
    "metadata": {}, "nbformat": 4})

IMG_NB = json.dumps({
    "cells": [{"cell_type": "markdown",
               "source": "![a](1.png)"}],
    "metadata": {}, "nbformat": 4})

HTML = ("<html><body><h1>H</h1><p>para</p>"
        "<img src='p.png'><p>after</p></body></html>")

TXT = "para one\n\npara two\n"


def _inspect(tmp_path, fn, parser, content):
    (tmp_path / fn).write_text(content, encoding="utf-8")
    doc, errors = process_single(
        tmp_path / fn, tmp_path / "o.json",
        parser_name=parser, max_chars=800)
    assert errors == []
    assert doc is not None
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cli_main(["inspect-doc",
                  str(tmp_path / "o.json")])
    return buf.getvalue()


def _lines(out):
    return [l.rstrip() for l in
            out.splitlines() if l.strip()]


# ---------- ipynb ----------

def test_ipynb_parser_line(tmp_path):
    out = _inspect(tmp_path, "n.ipynb", "ipynb",
                   NB)
    assert "parser:      ipynb vstdlib/0.1.0" \
        in _lines(out)


def test_ipynb_counts_line(tmp_path):
    out = _inspect(tmp_path, "n.ipynb", "ipynb",
                   NB)
    assert "counts:      elements=3 chunks=1" \
        in _lines(out)


def test_ipynb_ect_render(tmp_path):
    out = _inspect(tmp_path, "n.ipynb", "ipynb",
                   NB)
    assert any(
        "element_count_by_type" in l
        and "heading=1, paragraph=2" in l
        for l in _lines(out))


def test_ipynb_locator_ratio_nulls(tmp_path):
    out = _inspect(tmp_path, "n.ipynb", "ipynb",
                   NB)
    assert any("pdf_locator_valid_ratio"
               in l and "not_pdf_document" in l
               for l in _lines(out))
    assert any("docx_locator_valid_ratio"
               in l and "not_docx_document" in l
               for l in _lines(out))


def test_ipynb_img_ratio_no_elements(tmp_path):
    out = _inspect(tmp_path, "n.ipynb", "ipynb",
                   NB)
    assert any("image_resource_exists_ratio"
               in l
               and "no_image_elements" in l
               for l in _lines(out))


def test_ipynb_hbc_one(tmp_path):
    out = _inspect(tmp_path, "n.ipynb", "ipynb",
                   NB)
    assert any("heading_boundary_compliance"
               in l and "1.0000" in l
               for l in _lines(out))


# ---------- html ----------

def test_html_parser_line(tmp_path):
    out = _inspect(tmp_path, "d.html", "html",
                   HTML)
    assert "parser:      html vstdlib/0.1.0" \
        in _lines(out)


def test_html_counts(tmp_path):
    out = _inspect(tmp_path, "d.html", "html",
                   HTML)
    assert "counts:      elements=4 chunks=1" \
        in _lines(out)


def test_html_ect_includes_image(tmp_path):
    out = _inspect(tmp_path, "d.html", "html",
                   HTML)
    assert any(
        "element_count_by_type" in l
        and "heading=1, image=1, paragraph=2"
        in l for l in _lines(out))


def test_html_img_ratio_zero(tmp_path):
    out = _inspect(tmp_path, "d.html", "html",
                   HTML)
    assert any("image_resource_exists_ratio"
               in l and "0.0000" in l
               for l in _lines(out))


# ---------- text ----------

def test_text_parser_line(tmp_path):
    out = _inspect(tmp_path, "d.txt", "text",
                   TXT)
    assert "parser:      text vstdlib/0.1.0" \
        in _lines(out)


def test_text_hbc_no_heading(tmp_path):
    out = _inspect(tmp_path, "d.txt", "text",
                   TXT)
    assert any("heading_boundary_compliance"
               in l
               and "no_heading_elements" in l
               for l in _lines(out))


def test_text_counts(tmp_path):
    out = _inspect(tmp_path, "d.txt", "text",
                   TXT)
    assert "counts:      elements=2 chunks=1" \
        in _lines(out)


# ---------- image-only ipynb（0 chunk） ----------

def test_img_only_counts_zero_chunks(tmp_path):
    out = _inspect(tmp_path, "n2.ipynb",
                   "ipynb", IMG_NB)
    assert "counts:      elements=1 chunks=0" \
        in _lines(out)


def test_img_only_crir_no_chunks(tmp_path):
    out = _inspect(tmp_path, "n2.ipynb",
                   "ipynb", IMG_NB)
    assert any("chunk_reference_intact_ratio"
               in l and "no_chunks" in l
               for l in _lines(out))


def test_img_only_cmp_cmr_empty(tmp_path):
    out = _inspect(tmp_path, "n2.ipynb",
                   "ipynb", IMG_NB)
    assert any("text_char_multiset_precision"
               in l
               and "empty_expected_and_actual"
               in l for l in _lines(out))
    assert any("text_char_multiset_recall"
               in l
               and "empty_expected_and_actual"
               in l for l in _lines(out))


def test_img_only_tpe_true(tmp_path):
    out = _inspect(tmp_path, "n2.ipynb",
                   "ipynb", IMG_NB)
    assert any("text_preservation_equal"
               in l and "true" in l
               for l in _lines(out))


# ---------- 输入文件本身无 metrics 字段 ----------

def test_input_json_has_no_metrics(tmp_path):
    (tmp_path / "n.ipynb").write_text(
        NB, encoding="utf-8")
    process_single(
        tmp_path / "n.ipynb",
        tmp_path / "o.json",
        parser_name="ipynb", max_chars=800)
    on_disk = json.loads(
        (tmp_path / "o.json").read_text(
            encoding="utf-8"))
    assert "metrics" not in on_disk


def test_output_structure(tmp_path):
    out = _inspect(tmp_path, "n.ipynb", "ipynb",
                   NB)
    lines = _lines(out)
    assert lines[0].startswith("file:")
    assert any(l.startswith("document_id:")
               for l in lines)
    assert any(l.startswith("source:")
               for l in lines)
    assert "metrics:" in lines
