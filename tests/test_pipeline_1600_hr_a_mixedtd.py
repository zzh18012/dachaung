r"""pipeline 1600 字符两块不丢、hr 后表格、
顶级 a 文本与混合 td（Round 1715）。

新角度：R1714 锁纯 hash 标题——**1600 字符
799+799 两块 join 归一无丢失（边界空白作
join 消耗）、hr 后表格照常、顶级 `<a>` 透
明、td 文本与嵌套表并存外层文本丢失**零
覆盖：

- **'w '*800（1599 字符）**：2 chunks 各
  799，' '.join 后与归一原文相等（分块
  不丢不重）
- **'---\\n' 后直接表格**：表格识别正常
- **`<a href>link text</a>`**：paragraph
  'link text'（href 丢弃）
- **td 't' + 嵌套表**：外层文本 't' 丢
  失，输出 '|  |\\n| --- |\\n| in |'
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, name):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False,
        parser_name="html" if name.endswith("html") else "markdown")


def test_1600_chars_two_chunks_no_loss(tmp_path):
    p = tmp_path / "d.txt"
    p.write_bytes(("w " * 800).encode())
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    texts = [c.text for c in doc.chunks]
    assert [len(t) for t in texts] == [799, 799]
    joined = " ".join(texts)
    para = doc.elements[0].content
    assert " ".join(joined.split()) == " ".join(para.split())


def test_hr_then_table(tmp_path):
    doc, errors = _run(
        tmp_path,
        "---\n| a | b |\n| --- | --- |\n| x | y |\n",
        "d.md")
    assert errors == []
    assert [(e.type, e.metadata) for e in doc.elements] == [
        ("table", {"row_count": 2, "col_count": 2,
                   "source": "markdown_pipe_table"})]


def test_toplevel_a_text(tmp_path):
    doc, errors = _run(
        tmp_path, '<a href="u">link text</a>', "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "link text", {})]


def test_td_text_with_nested_table(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><td>t<table><tr><td>in</td>"
        "</tr></table></td></tr></table>", "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "|  |\n| --- |\n| in |",
         {"row_count": 2, "col_count": 1,
          "source": "html_table"})]
