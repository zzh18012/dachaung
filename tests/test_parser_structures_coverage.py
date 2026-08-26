r"""parser 结构覆盖：ol/ul 无编号、br 转空
格、setext 退化、hr 静默丢弃（Round 1784）。

新角度：R1783 锁切分判定——**html ol 与
ul 同为裸 list_item（'1.' 编号不保留）；
<br> 转空格并入同段；md setext
'Title\\n===' 不识别为标题（退化段落、
内部 \\n 保留）；'---' 主题分隔线整行
静默丢弃（无元素无警告）、两侧段落跨它
合并；嵌套引用 '> >' 剥一层标记成
'> deep' 段落**零覆盖：

- **ol/ul**：list_item×2、合并 '一 二'
- **'Title\\n==='**：paragraph 原文 +
  'body' 合并
- **'aaa --- bbb'**：无 hr 元素、无警告、
  'aaa bbb' 跨越合并
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, text, parser):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name=parser)


def test_html_list_types_no_numbering(tmp_path):
    for html, want in [
        ("<ol><li>一</li><li>二</li></ol>", "一 二"),
        ("<ul><li>a</li><li>b</li></ul>", "a b"),
    ]:
        doc, errors = _run(
            tmp_path, "d.html", html, "html")
        assert errors == []
        assert [e.type for e in doc.elements] == [
            "list_item", "list_item"]
        assert doc.chunks[0].text == want
        assert doc.chunks[0].metadata[
            "strategy"] == "sequential"


def test_html_br_becomes_space(tmp_path):
    doc, errors = _run(
        tmp_path, "d.html", "<p>line1<br>line2</p>",
        "html")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "line1 line2")]
    assert doc.chunks[0].text == "line1 line2"


def test_md_setext_degrades_literal(tmp_path):
    doc, errors = _run(
        tmp_path, "d.md", "Title\n===\n\nbody\n",
        "markdown")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "Title\n==="),
        ("paragraph", "body")]
    assert doc.chunks[0].text == "Title\n=== body"


def test_md_thematic_break_dropped(tmp_path):
    doc, errors = _run(
        tmp_path, "d.md", "aaa\n\n---\n\nbbb\n",
        "markdown")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "paragraph", "paragraph"]
    assert doc.warnings == []
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("aaa bbb", 2)]


def test_md_nested_bq_strips_one_level(tmp_path):
    doc, errors = _run(
        tmp_path, "d.md", "> > deep\n\n> top\n",
        "markdown")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "> deep"),
        ("paragraph", "top")]
    assert doc.chunks[0].text == "> deep top"
