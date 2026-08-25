r"""pipeline BOM/CRLF × 家族结构识别（Round 1624）。

新角度：R1623 锁行分隔符——**BOM 对结构识别
的破坏、CRLF 无害性**零覆盖：

- **BOM 破坏 md heading**：'\\ufeff# Title'
  ATX 前缀被粘住 → 段落 raw
- **CRLF 无害**：md/html 下 heading/段落识别
  全部正常
- **html 的 BOM 成独立段落**：'\\ufeff' 文本
  节点自己成一个 paragraph，排在 heading 之前
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, data, parser):
    p = tmp_path / name
    p.write_bytes(data)
    doc, errors = process_single(
        p, write_json=False, parser_name=parser)
    assert errors == []
    return doc


def test_bom_breaks_md_heading(tmp_path):
    doc = _run(
        tmp_path, "b.md",
        b"\xef\xbb\xbf# Title\n", "markdown")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "﻿# Title", {})]


def test_crlf_families_ok(tmp_path):
    doc = _run(
        tmp_path, "c.md",
        b"# Title\r\n\r\nbody\r\n", "markdown")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "Title", {"level": 1}),
        ("paragraph", "body", {})]

    doc2 = _run(
        tmp_path, "h.html",
        b"<h1>H</h1>\r\n<p>P</p>", "html")
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("heading", "H"), ("paragraph", "P")]


def test_bom_html_own_paragraph(tmp_path):
    doc = _run(
        tmp_path, "hb.html",
        b"\xef\xbb\xbf<h1>H</h1>", "html")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "﻿", {}),
        ("heading", "H", {"level": 1})]
