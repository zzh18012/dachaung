r"""pipeline colgroup 透明与闭合标签带属性
（Round 1675）。

新角度：R1674 锁引用内图片——**colgroup/
col 不影响表格、闭合标签带属性容忍**零
覆盖：

- **colgroup**：'&lt;colgroup&gt;&lt;col&gt;'
  丢弃，行照常提取
- **'&lt;/p class="x"&gt;'**：闭合标签带
  属性不报错，paragraph 'x' 照常
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_colgroup_transparent(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<table><colgroup><col></colgroup>"
        "<tr><td>x</td></tr></table>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| x |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]


def test_closing_tag_with_attrs(tmp_path):
    p = tmp_path / "d.html"
    p.write_text('<p>x</p class="x">',
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "x", {})]
