r"""pipeline 纯图文档零 chunk 与纯标题单 chunk
（Round 1661）。

新角度：R1660 锁分块流——**只有 image 元素
的文档 chunks 为空（合法）、纯标题文档单
chunk**零覆盖：

- **md/html 纯图**：1 个 image 元素、0 个
  chunk——图片完全绕过分块，空 chunk 列
  表不报错
- **纯标题**：'# T' → 单 chunk 'T'（1 id）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_md_image_only_zero_chunks(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("![alt](x.png)\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("image", None, {"alt": "alt"})]
    assert doc.chunks == []


def test_html_image_only_zero_chunks(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<img src='x.png' alt='A'>",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("image", None, {"alt": "A"})]
    assert doc.chunks == []


def test_heading_only_single_chunk(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("# T\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("T", 1)]
