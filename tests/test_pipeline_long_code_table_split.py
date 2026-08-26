r"""pipeline 超长 code/pre 与表格同样切分
（Round 1725）。

新角度：R1724 锁 CJK 家族——**围栏 900
CJK、pre 900 CJK、1018 字符表格文本全部
走 max_chars 切分（code/pre 无豁免）**零
覆盖：

- **md 围栏 900 CJK**：800 forced_char +
  100（code_block 同样切）
- **html pre 900 CJK**：同上
- **表格含 1000 字符单元格**：表文本
  1018 切 799+218（whitespace 边界）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_md_fence_900_cjk_split(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("```\n" + "字" * 900 + "\n```\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert len(doc.elements[0].content) == 900
    assert [(len(c.text),
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (800, "forced_char"), (100, None)]


def test_html_pre_900_cjk_split(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<pre>" + "字" * 900 + "</pre>",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert len(doc.elements[0].content) == 900
    assert [(len(c.text),
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (800, "forced_char"), (100, None)]


def test_long_table_cell_split(tmp_path):
    p = tmp_path / "d.md"
    cell = "w " * 500
    p.write_text(f"| a |\n| --- |\n| {cell} |\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert len(doc.elements[0].content) == 1018
    assert [(len(c.text), c.metadata["strategy"])
            for c in doc.chunks] == [
        (799, "long_paragraph_sentence_split"),
        (218, "long_paragraph_sentence_split")]
