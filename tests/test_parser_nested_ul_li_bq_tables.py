r"""parser html 嵌套 ul 扁平、li 内 bq
抽出兄弟、连续表各成块（Round 1828）。

新角度：R1827 锁三级层级链——**
html 嵌套 <ul> 扁平化为兄弟 list_item
（无层级信息）；li 内 <blockquote>
抽出为兄弟 paragraph kind=
'blockquote'；两张连续表各自成独立
chunk（不粘连——区别于段落 glue）
**零覆盖：

- **嵌套 ul**：'a'/'b' 两兄弟无层级
- **li 内 bq**：li 'x' + 兄弟 bq 'q'
- **连续表**：两 chunk 各 1 元素
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def test_nested_ul_flattened(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<ul><li>a<ul><li>b</li></ul></li></ul>")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "a",
         {"ordered": False, "marker": "unordered"}),
        ("list_item", "b",
         {"ordered": False, "marker": "unordered"})]


def test_li_blockquote_extracted(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<ul><li>x<blockquote>q</blockquote>"
        "</li></ul>")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "x",
         {"ordered": False, "marker": "unordered"}),
        ("paragraph", "q", {"kind": "blockquote"})]


def test_consecutive_tables_separate_chunks(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><th>t1</th></tr></table>"
        "<table><tr><th>t2</th></tr></table>")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "| t1 |\n| --- |", "| t2 |\n| --- |"]
    assert [(len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        (1, "isolated_table"), (1, "isolated_table")]
