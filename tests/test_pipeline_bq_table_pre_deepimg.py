r"""pipeline 引用内表格与 pre、text 行首
空格、深层嵌套 img（Round 1713）。

新角度：R1712 锁 CRLF——**html blockquote
对 table/pre 完全透明（嵌套 bq 也不影响）、
text 'a\\n b' 合并单段行首空格保留、深层
div>p 内 img 照常提取**零覆盖：

- **bq 内 `<table>`**：表格正常提取
- **bq 内 `<pre>`**：preformatted 段落
- **bq 嵌 bq 内表格**：同样透明
- **text 'a\\n b'**：单段（行合并），行首
  空格与换行保留
- **div>div>p>img**：image 提取 resource_
  path 正常
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run_html(tmp_path, text):
    p = tmp_path / "d.html"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def test_table_in_bq(tmp_path):
    doc, errors = _run_html(
        tmp_path,
        "<blockquote><table><tr><td>x</td>"
        "</tr></table></blockquote>")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| x |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]


def test_pre_in_bq(tmp_path):
    doc, errors = _run_html(
        tmp_path, "<blockquote><pre>code</pre></blockquote>")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "code", {"kind": "preformatted"})]


def test_nested_bq_table(tmp_path):
    doc, errors = _run_html(
        tmp_path,
        "<blockquote><blockquote><table><tr>"
        "<td>y</td></tr></table></blockquote>"
        "</blockquote>")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| y |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]


def test_text_leading_space_line(tmp_path):
    p = tmp_path / "d.txt"
    p.write_bytes(b"a\n b\n")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "a\n b")]


def test_img_deep_nesting(tmp_path):
    doc, errors = _run_html(
        tmp_path,
        '<div><div><p><img src="i.png" alt="A">'
        "</p></div></div>")
    assert errors == []
    assert [(e.type, e.content, e.resource_path)
            for e in doc.elements] == [
        ("image", None, "i.png")]
