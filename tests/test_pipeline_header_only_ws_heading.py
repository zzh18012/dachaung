r"""pipeline 仅表头表格、colspan 忽略与纯
空格标题结构化错误（Round 1708）。

新角度：R1707 锁 nbformat3——**'##   '（##
后纯空格）触发 unexpected_parser_error
（markdown crash 家族新成员）、header-only
表 row_count 1、colspan 属性忽略、tfoot
并入普通行**零覆盖：

- **md 表头 + 分隔行（无数据行）**：表
  存在 row_count 1（表头计行）
- **html 仅 `<th>` 行**：row_count 1 同理
- **`colspan="2"`**：属性忽略，列数以表
  头为准 col_count 1
- **'##   ' 纯空格标题**：errors =
  [unexpected_parser_error]，message 含
  '必须至少有 content 或 resource_path'
  （结构化错误不崩进程，待修复家族）
- **`<tfoot>`**：并入普通数据行
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


def test_md_header_sep_only_table(tmp_path):
    doc, errors = _run(
        tmp_path, "| a | b |\n| --- | --- |\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| a | b |\n| --- | --- |",
         {"row_count": 1, "col_count": 2,
          "source": "markdown_pipe_table"})]
    assert len(doc.chunks) == 1


def test_html_header_only_table(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><th>H1</th><th>H2</th></tr></table>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| H1 | H2 |\n| --- | --- |",
         {"row_count": 1, "col_count": 2,
          "source": "html_table"})]


def test_colspan_ignored(tmp_path):
    doc, errors = _run(
        tmp_path,
        '<table><tr><th>H</th></tr>'
        '<tr><td colspan="2">v</td></tr></table>',
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| H |\n| --- |\n| v |",
         {"row_count": 2, "col_count": 1,
          "source": "html_table"})]


def test_md_ws_only_heading_structured_error(tmp_path):
    doc, errors = _run(tmp_path, "##   \n", "d.md")
    assert doc is None
    assert [e.code for e in errors] == [
        "unexpected_parser_error"]
    assert "必须至少有 content 或 resource_path" \
        in errors[0].message
    assert errors[0].details["parser_name"] == "markdown"


def test_tfoot_merged_as_row(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><th>H</th></tr>"
        "<tfoot><tr><td>f</td></tr></tfoot></table>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| H |\n| --- |\n| f |",
         {"row_count": 2, "col_count": 1,
          "source": "html_table"})]
