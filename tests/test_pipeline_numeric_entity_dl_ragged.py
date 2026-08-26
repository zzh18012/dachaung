r"""pipeline 数字实体、dl 配对合并、md 参差
表格与无 src 图片（Round 1695）。

新角度：R1694 锁 BOM——**'&#65;'/'&#x42;'
十进制与十六进制实体都解码、dl 正常配对
dt+dd 无空格合并、md 参差表格以表头列数
补齐、无 src 图片整图跳过、单元格内注释
剔除拼接**零覆盖：

- **'&#65;&#x42;'**：两种数字形式都解码
  成 'AB'
- **`<dt>T</dt><dd>D</dd>`**：合并单段
  'TD'（无分隔空格，非两个段落）
- **表头 3 列 + 分隔 2 列**：col_count 3、
  分隔行补齐 '| --- | --- | --- |'、短行
  '| x |  |  |'
- **`<img alt>` 无 src**：无 image element、
  无报错
- **td 内 'a<!-- c -->b'**：注释剔除 'ab'
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run_html(tmp_path, text):
    p = tmp_path / "d.html"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def _run_md(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_numeric_entities_decoded(tmp_path):
    doc, errors = _run_html(tmp_path, "<p>&#65;&#x42;</p>")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "AB")]


def test_dl_pair_merges_one_paragraph(tmp_path):
    doc, errors = _run_html(
        tmp_path, "<dl><dt>T</dt><dd>D</dd></dl>")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "TD", {})]


def test_md_ragged_table_header_wins(tmp_path):
    doc, errors = _run_md(
        tmp_path,
        "| a | b | c |\n| --- | --- |\n| x |\n")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table",
         "| a | b | c |\n| --- | --- | --- |\n"
         "| x |  |  |",
         {"row_count": 2, "col_count": 3,
          "source": "markdown_pipe_table"})]


def test_img_no_src_skipped(tmp_path):
    doc, errors = _run_html(
        tmp_path, '<p>t</p><img alt="only alt">')
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "t")]
    assert doc.warnings == []


def test_comment_in_cell_stripped(tmp_path):
    doc, errors = _run_html(
        tmp_path,
        "<table><tr><td>a<!-- c -->b</td></tr></table>")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| ab |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]
