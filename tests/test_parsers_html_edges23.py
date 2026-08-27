r"""html 未闭合块标签恢复 vs 表格致命面测试（Round 1503）。

probe 实证（R1502 只锁了表内 '<p>' 与表+尾文本两类；本
轮系统扫未闭合家族）：

- **未闭合 bq/pre/ul/h1 EOF 全恢复**：元素照常产出、
  kind/marker/level 元数据齐全（HTMLParser 惰性闭合）
- **未闭合 '<p>' 相邻合并**：'<p>before<p>second' →
  **'beforesecond'** 单段（隐式 p 闭合不识别，文本连
  流）
- **未闭合 '<b>' inline 无害**：'a bold'
- **⚠ 未闭合表在文档中部 → 只丢表本身**：第二个表
  （无 </table> EOF）静默丢 y，前后段完好（对照 R1502
  的表+尾文本整文档丢——尾文本是否存在于表后是分界）
- **⚠ 仅未闭合 td/tr/table → 整文档丢**：html_no_content
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import \
    HtmlParser


def _html(tmp_path, body):
    p = tmp_path / "probe.html"
    p.write_text(
        f"<!DOCTYPE html><html>"
        f"<body>{body}</body></html>",
        encoding="utf-8", newline="")
    return HtmlParser().parse(
        p, compute_file_hash(p))


# ---------- 块标签未闭合恢复 ----------

def test_unclosed_block_tags_recover(
        tmp_path):
    cases = [
        ("<blockquote>quoted",
         [("paragraph", "quoted")],
         {"kind": "blockquote"}),
        ("<pre>code",
         [("paragraph", "code")],
         {"kind": "preformatted"}),
        ("<ul><li>item",
         [("list_item", "item")],
         {"ordered": False,
          "marker": "unordered"}),
        ("<h1>title",
         [("heading", "title")],
         {"level": 1}),
    ]
    for body, expect, meta in cases:
        doc = _html(
            tmp_path,
            "<p>before</p>" + body)
        got = [(e.type, e.content)
               for e in doc.elements]
        assert got == [
            ("paragraph", "before"),
            *expect,
        ], body
        assert doc.elements[1].metadata \
            == meta, body
        assert doc.warnings == [], body


def test_unclosed_p_merges(tmp_path):
    doc = _html(
        tmp_path,
        "<p>before<p>second")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "beforesecond"),
    ]
    assert doc.warnings == []


def test_unclosed_b_inline_harmless(
        tmp_path):
    doc = _html(
        tmp_path,
        "<p>a <b>bold")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "a bold"),
    ]


# ---------- 表格未闭合梯度 ----------

def test_unclosed_table_mid_doc_partial(
        tmp_path):
    doc = _html(
        tmp_path,
        "<p>before</p><table>"
        "<tr><td>x</td></tr></table>"
        "<p>after</p><table>"
        "<tr><td>y</td>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "before"),
        ("table", "| x |\n| --- |"),
        ("paragraph", "after"),
    ]
    assert doc.warnings == []


def test_unclosed_td_only_eats_all(
        tmp_path):
    doc = _html(
        tmp_path,
        "<table><tr><td>x")
    assert doc.elements == []
    assert [w.code for w in
            doc.warnings] == \
        ["html_no_content"]
