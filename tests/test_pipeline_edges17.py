r"""app/pipeline.py 边角测试 - 第十七轮（Round 1399）。

新角度（probe 实证）：扩展名 × parser 全错配矩阵（历史只零星
锁过 md 组合，21 个错配组合从未整表锁）——任何真实文件用
不匹配的 --parser 都在 parser 选择层被拒：
- docx×{markdown,html,text,ipynb}、md×{fallback,html,ipynb}、
  html×{fallback,markdown,ipynb}、txt×{fallback,markdown,
  ipynb}、ipynb×{fallback,markdown,html,text}、pdf×{markdown,
  html,text,ipynb} → 全部 unsupported_type
- ErrorRecord.details 恰 {path, suffix}；doc None 单错误
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from docx import Document

from app.pipeline import process_single


_MISMATCHES = [
    ("a.docx", "markdown"),
    ("a.docx", "html"),
    ("a.docx", "text"),
    ("a.docx", "ipynb"),
    ("b.md", "fallback"),
    ("b.md", "html"),
    ("b.md", "ipynb"),
    ("c.html", "fallback"),
    ("c.html", "markdown"),
    ("c.html", "ipynb"),
    ("e.txt", "fallback"),
    ("e.txt", "markdown"),
    ("e.txt", "ipynb"),
    ("f.ipynb", "fallback"),
    ("f.ipynb", "markdown"),
    ("f.ipynb", "html"),
    ("f.ipynb", "text"),
    ("g.pdf", "markdown"),
    ("g.pdf", "html"),
    ("g.pdf", "text"),
    ("g.pdf", "ipynb"),
]


def _make_files(tmp_path):
    d = Document()
    d.add_paragraph("x")
    d.save(str(tmp_path / "a.docx"))
    (tmp_path / "b.md").write_text(
        "# T\n", encoding="utf-8")
    (tmp_path / "c.html").write_text(
        "<p>x</p>", encoding="utf-8")
    (tmp_path / "e.txt").write_text(
        "x", encoding="utf-8")
    (tmp_path / "f.ipynb").write_text(
        '{"cells": [], "metadata": {},'
        ' "nbformat": 4}',
        encoding="utf-8")
    (tmp_path / "g.pdf").write_bytes(
        b"%PDF-1.4\nfake\n%%EOF")


@pytest.mark.parametrize(
    "fn,parser", _MISMATCHES)
def test_mismatch_unsupported_type(
        tmp_path, fn, parser):
    _make_files(tmp_path)
    doc, errors = process_single(
        tmp_path / fn, None,
        parser_name=parser,
        max_chars=200)
    assert doc is None
    assert len(errors) == 1
    assert errors[0].code == \
        "unsupported_type"


@pytest.mark.parametrize(
    "fn,parser", _MISMATCHES)
def test_mismatch_details_keys(
        tmp_path, fn, parser):
    _make_files(tmp_path)
    _, errors = process_single(
        tmp_path / fn, None,
        parser_name=parser,
        max_chars=200)
    assert sorted(
        errors[0].details.keys()) == [
        "path", "suffix"]


@pytest.mark.parametrize(
    "fn,parser", _MISMATCHES)
def test_mismatch_details_suffix(
        tmp_path, fn, parser):
    _make_files(tmp_path)
    _, errors = process_single(
        tmp_path / fn, None,
        parser_name=parser,
        max_chars=200)
    assert errors[0].details[
        "suffix"] == \
        Path(fn).suffix


def test_mismatch_matrix_complete():
    assert len(_MISMATCHES) == 21


def test_mismatch_no_output_file(
        tmp_path):
    _make_files(tmp_path)
    out = tmp_path / "o.json"
    process_single(
        tmp_path / "b.md", out,
        parser_name="fallback",
        max_chars=200)
    assert not out.exists()
