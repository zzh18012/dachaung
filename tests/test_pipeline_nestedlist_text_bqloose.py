r"""pipeline 嵌套列表带文本、引用散文本与
表格后紧跟段落（Round 1718）。

新角度：R1717 锁非标准分隔——**li 内文
本 + 嵌套 ul 拍平顺序保留、`<blockquote>`
散文本成段且与内部 p 无空格合并、表格后
无空行段落独立**零覆盖：

- **`<li>a text<ul><li>b</li></ul></li>`**：
  list_item 'a text' + list_item 'b' 平级
- **`<blockquote>loose</blockquote>`**：段
  落 'loose' kind 'blockquote'
- **`<blockquote>loose<p>p</p></blockquote>`**：
  无空格合并单段 'loosep'
- **表格行后直接 'tail'**：table + 独立
  paragraph 'tail'（表格在最后数据行处结
  束，不吞后续行）
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


def test_nested_list_with_text_flattens(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<ul><li>a text<ul><li>b</li></ul></li></ul>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "a text",
         {"ordered": False, "marker": "unordered"}),
        ("list_item", "b",
         {"ordered": False, "marker": "unordered"})]


def test_bq_loose_text(tmp_path):
    doc, errors = _run(
        tmp_path, "<blockquote>loose</blockquote>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "loose", {"kind": "blockquote"})]


def test_bq_loose_and_p_merge(tmp_path):
    doc, errors = _run(
        tmp_path, "<blockquote>loose<p>p</p></blockquote>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "loosep", {"kind": "blockquote"})]


def test_table_then_para_no_blank(tmp_path):
    doc, errors = _run(
        tmp_path,
        "| a | b |\n| --- | --- |\n| x | y |\ntail\n",
        "d.md")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("table",
         "| a | b |\n| --- | --- |\n| x | y |"),
        ("paragraph", "tail")]
