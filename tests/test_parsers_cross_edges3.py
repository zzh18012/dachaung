r"""跨 parser 同文本对照测试 - 第三轮（Round 1417）。

新角度（probe 实证）Windows 编辑器实况编码（历史全用
\n 干净字节）：
- CRLF：txt 段落照切、md heading 照认（\r 被剥掉）
- UTF-8 BOM 三种劣化：
  - txt：'﻿BOM title' BOM 进 content
  - md：'# ' 不在行首 → **heading 识别被打断**，整行
    变 paragraph
  - html：BOM 泄成独立 '﻿' 幽灵 paragraph 元素
    （真元素之前）
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, parser,
         data):
    p = tmp_path / name
    p.write_bytes(data)
    doc, errors = process_single(
        p, None, parser_name=parser,
        max_chars=800)
    assert errors == []
    return doc


# ---------- CRLF ----------

def test_crlf_txt_paragraphs(
        tmp_path):
    doc = _run(
        tmp_path, "crlf.txt",
        "text",
        b"First crlf paragraph."
        b"\r\n\r\n"
        b"Second crlf paragraph."
        b"\r\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph",
         "First crlf paragraph."),
        ("paragraph",
         "Second crlf paragraph.")]


def test_crlf_txt_no_cr(tmp_path):
    doc = _run(
        tmp_path, "crlf.txt",
        "text",
        b"A.\r\n\r\nB.\r\n")
    for e in doc.elements:
        assert "\r" not in e.content


def test_crlf_md_heading_kept(
        tmp_path):
    doc = _run(
        tmp_path, "crlf.md",
        "markdown",
        b"# CRLF Title\r\n\r\n"
        b"crlf body.\r\n")
    assert [e.type
            for e in doc.elements] == [
        "heading", "paragraph"]
    assert doc.elements[
        0].content == "CRLF Title"
    assert doc.elements[
        1].source_locator == {
        "line": 3,
        "section_path":
            "CRLF Title"}


# ---------- BOM txt ----------

def test_bom_txt_kept_in_content(
        tmp_path):
    doc = _run(
        tmp_path, "bom.txt",
        "text",
        b"\xef\xbb\xbfBOM title\n\n"
        b"BOM body text.\n")
    assert doc.elements[
        0].content == \
        "﻿BOM title"
    assert doc.elements[
        1].content == "BOM body text."


def test_bom_txt_two_elements(
        tmp_path):
    doc = _run(
        tmp_path, "bom.txt",
        "text",
        b"\xef\xbb\xbfBOM title\n\n"
        b"BOM body text.\n")
    assert len(doc.elements) == 2


# ---------- BOM md ----------

def test_bom_md_breaks_heading(
        tmp_path):
    doc = _run(
        tmp_path, "bom.md",
        "markdown",
        b"\xef\xbb\xbf"
        b"# BOM Heading\n\n"
        b"BOM md body.\n")
    assert [e.type
            for e in doc.elements] == [
        "paragraph", "paragraph"]


def test_bom_md_content(tmp_path):
    doc = _run(
        tmp_path, "bom.md",
        "markdown",
        b"\xef\xbb\xbf"
        b"# BOM Heading\n\n"
        b"BOM md body.\n")
    assert doc.elements[
        0].content == \
        "﻿# BOM Heading"
    assert doc.elements[
        1].content == "BOM md body."


def test_bom_md_no_section_path(
        tmp_path):
    doc = _run(
        tmp_path, "bom.md",
        "markdown",
        b"\xef\xbb\xbf"
        b"# BOM Heading\n\n"
        b"BOM md body.\n")
    for e in doc.elements:
        assert "section_path" \
            not in e.source_locator


# ---------- BOM html ----------

def test_bom_html_ghost_element(
        tmp_path):
    doc = _run(
        tmp_path, "bom.html",
        "html",
        b"\xef\xbb\xbf<html><body>"
        b"<h1>B H</h1>"
        b"<p>b body</p>"
        b"</body></html>")
    assert [e.type
            for e in doc.elements] == [
        "paragraph", "heading",
        "paragraph"]


def test_bom_html_ghost_content(
        tmp_path):
    doc = _run(
        tmp_path, "bom.html",
        "html",
        b"\xef\xbb\xbf<html><body>"
        b"<h1>B H</h1>"
        b"<p>b body</p>"
        b"</body></html>")
    assert doc.elements[
        0].content == "﻿"
    assert doc.elements[
        1].content == "B H"
    assert doc.elements[
        2].content == "b body"


def test_bom_html_real_elements_intact(
        tmp_path):
    doc = _run(
        tmp_path, "bom.html",
        "html",
        b"\xef\xbb\xbf<html><body>"
        b"<h1>B H</h1>"
        b"<p>b body</p>"
        b"</body></html>")
    assert doc.elements[
        1].source_locator == {
        "line": 1,
        "section_path": "B H"}


# ---------- 横向对照 ----------

def test_crlf_all_clean_types(tmp_path):
    for name, parser, data in (
        ("a.txt", "text",
         b"One.\r\n\r\nTwo.\r\n"),
        ("b.md", "markdown",
         b"# T\r\n\r\nbody.\r\n")):
        doc = _run(tmp_path, name,
                   parser, data)
        for e in doc.elements:
            assert "﻿" \
                not in e.content
            assert "\r" \
                not in e.content
