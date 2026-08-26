r"""parser md 任务列表字面、html 嵌套表
行提升外文本丢、标题内锚文本保
（Round 1824）。

新角度：R1823 锁 ol start 忽略——**
'- [ ] todo' 复选框语法整体字面
（raw 哲学）；td 内嵌 <table> 内层行
提升进外表（row_count 2）且外单元
文本 'out' 丢失（静默）；<h2> 内
<a> 剥壳文本留 'T lnk'**零覆盖：

- **任务列表**：'[ ] todo'/'[x] done'
- **嵌套表**：'|  |' 首行空 + '| in |'
- **标题内锚**：heading 'T lnk' level 2
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _html(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def test_md_task_list_literal(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("- [ ] todo\n- [x] done\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "[ ] todo"),
        ("list_item", "[x] done")]
    assert all(e.metadata["marker"] == "unordered"
               for e in doc.elements)


def test_nested_table_row_hoisted(tmp_path):
    doc, errors = _html(
        tmp_path,
        "<table><tr><td>out<table><tr>"
        "<td>in</td></tr></table></td></tr>"
        "</table>")
    assert errors == []
    assert len(doc.elements) == 1
    t = doc.elements[0]
    assert t.content == "|  |\n| --- |\n| in |"
    assert t.metadata == {
        "row_count": 2, "col_count": 1,
        "source": "html_table"}


def test_heading_anchor_text_kept(tmp_path):
    doc, errors = _html(
        tmp_path, '<h2>T <a href="u">lnk</a></h2>')
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "T lnk", {"level": 2})]
