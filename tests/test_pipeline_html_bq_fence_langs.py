r"""pipeline html blockquote 结构透明与交替围栏
（Round 1676）。

新角度：R1675 锁 colgroup——**html 引用内
heading/list 照常提取（与 md 引用内部惰性
相反）、交替围栏语言**零覆盖：

- **h3 在 blockquote**：heading level 3
  正常产出
- **ul 在 blockquote**：list_item 正常产出
  （html 引用只是透明容器，无 md 的惰性
  规则）
- **交替围栏**：```py 与 ```js 两个
  code_block 各带语言
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_heading_in_html_bq(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<blockquote><h3>Q</h3></blockquote>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "Q", {"level": 3})]


def test_list_in_html_bq(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<blockquote><ul><li>item</li></ul>"
        "</blockquote>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "item",
         {"ordered": False, "marker": "unordered"})]


def test_alternating_fence_languages(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "```py\na\n```\n```js\nb\n```\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a",
         {"kind": "code_block", "language": "py"}),
        ("paragraph", "b",
         {"kind": "code_block", "language": "js"})]
