r"""pipeline md 单元格内联图片/链接 raw
（Round 1668）。

新角度：R1667 锁 li 内表格——**管道表单元
格里的 ![..]() / [..]() 不解析、不产 image
元素**零覆盖：

- **图片语法 raw**：'![i](p.png)' 原样留
  在单元格文本里
- **链接语法 raw**：'[L](u)' 同样原样
- **无 image 元素**：即使图片语法独占一
  格，全文档也只有 1 个 table 元素
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    return doc


def test_img_syntax_in_cell_raw(tmp_path):
    doc = _run(
        tmp_path,
        "| a | b |\n| --- | --- |\n"
        "| x | ![i](p.png) |\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table",
         "| a | b |\n| --- | --- |\n"
         "| x | ![i](p.png) |",
         {"row_count": 2, "col_count": 2,
          "source": "markdown_pipe_table"})]


def test_link_syntax_in_cell_raw(tmp_path):
    doc = _run(
        tmp_path,
        "| a | b |\n| --- | --- |\n"
        "| x | [L](u) |\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("table",
         "| a | b |\n| --- | --- |\n"
         "| x | [L](u) |")]


def test_no_image_element_from_cell(tmp_path):
    doc = _run(
        tmp_path,
        "| a | b |\n| --- | --- |\n"
        "| ![i](p.png) | y |\n")
    assert [e.type for e in doc.elements] == [
        "table"]
    assert len(doc.elements) == 1
