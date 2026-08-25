r"""pipeline HTML 解析器元素与分块家族（Round 1597）。

新角度：R1596 锁 locator——**html 的 img/表格/
列表**在 pipeline 层零覆盖：

- **元素家族**：img → type=image、content=None、
  resource_path=src 原样；table →
  markdown；li → list_item
- **分块家族**：空 content 图片**不产 chunk**；
  list_item 像 paragraph 一样累积（'one two'
  合并）；table isolated
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single

_HTML = (
    '<h1>H</h1><p>P1</p>'
    '<img src="x.png" alt="alt">'
    '<table><tr><td>a</td>'
    '<td>b</td></tr></table>'
    '<ol><li>one</li>'
    '<li>two</li></ol>')


def _run(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(_HTML, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False,
        parser_name="html")
    assert errors == []
    return doc


def test_html_element_family(
        tmp_path):
    doc = _run(tmp_path)
    got = [(e.type, e.content,
            e.resource_path)
           for e in doc.elements]
    assert got == [
        ("heading", "H", None),
        ("paragraph", "P1", None),
        ("image", None, "x.png"),
        ("table",
         "| a | b |"
         "\n| --- | --- |",
         None),
        ("list_item", "one", None),
        ("list_item", "two", None)]
    locs = [e.source_locator
            for e in doc.elements]
    assert all(
        l == {"line": 1,
              "section_path": "H"}
        for l in locs)


def test_html_chunk_family(
        tmp_path):
    doc = _run(tmp_path)
    got = [(c.text,
            c.metadata["strategy"])
           for c in doc.chunks]
    assert got == [
        ("H P1", "sequential"),
        ("| a | b |"
         "\n| --- | --- |",
         "isolated_table"),
        ("one two", "sequential")]
    img_id = [
        e.element_id
        for e in doc.elements
        if e.type == "image"][0]
    assert all(
        img_id not in c.source_element_ids
        for c in doc.chunks)
