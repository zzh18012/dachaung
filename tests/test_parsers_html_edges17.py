r"""app/parsers/html_parser.py 边角测试 - 第十七轮（Round 1471）。

新角度（probe 实证）隐式闭合 + 罕见容器（edges1-16 未碰
过；base/edges10/edges11 已锁 noscript/video/svg/button/
input 等，避开）：
- **<p> 不隐式闭合**：'<p>one<p>two' → **合并单段** 'onetwo'
  （html.parser 不实现 HTML 的 p 自动闭合；与 R1466 的 div
  并段同源）
- **<template> 内容照常提取**且与后续文本并段（'t
  contentvis'——template 不在 _SKIP_TAGS）
- **<details>/<summary> 合并**：'Summarydetail body' 单段
- **孤儿 td/tr**（表格外）→ 纯 paragraph（无表格结构）
- **heading 内 <br>** → 空格拼接（'line1 line2'，仍单个
  heading）
- **EOF 未闭合 <b>** → 文本照常完整提取
- **blockquote 双 <p> 精确合并** 'p1p2'（base 只断言 ≥1
  且文本在场，未锁精确形状）
- p 与 p 之间的纯空白**不并段**（两 paragraph——对照 div
  的并段行为）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser

TMP_NAME = "html_edge17_probe.html"


def _parse(tmp_path, html, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(html, encoding="utf-8",
                 newline="")
    return HtmlParser().parse(
        p, compute_file_hash(p))


# ---------- 隐式闭合 ----------

def test_implicit_p_close_merges(
        tmp_path):
    doc = _parse(
        tmp_path, "<p>one<p>two")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "onetwo"),
    ]
    assert doc.warnings == []


# ---------- template ----------

def test_template_content_extracted(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<template>t content</template>"
        "<p>vis</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "t contentvis"),
    ]


# ---------- details/summary ----------

def test_details_summary_merged(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<details><summary>Summary"
        "</summary>detail body"
        "</details>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph",
         "Summarydetail body"),
    ]


# ---------- 孤儿表格元素 ----------

def test_orphan_td_paragraph(
        tmp_path):
    doc = _parse(
        tmp_path, "<td>loose cell</td>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "loose cell"),
    ]


def test_orphan_tr_paragraph(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<tr><td>x</td></tr>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "x"),
    ]


# ---------- heading 内 br ----------

def test_br_in_heading_space(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<h1>line1<br>line2</h1>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "line1 line2"),
    ]
    assert doc.elements[
        0].metadata["level"] == 1


# ---------- 未闭合内联 ----------

def test_unclosed_b_at_eof(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<p>start <b>bold never closed")
    assert [e.content
            for e in doc.elements] == [
        "start bold never closed",
    ]


# ---------- blockquote 精确合并 ----------

def test_bq_two_p_exact_merge(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<blockquote><p>p1</p>"
        "<p>p2</p></blockquote>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "p1p2"),
    ]
    assert doc.elements[
        0].metadata["kind"] == \
        "blockquote"


# ---------- p 间空白不并段 ----------

def test_ws_between_p_not_merged(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<p>a</p>   \n  <p>b</p>")
    assert [e.content
            for e in doc.elements] == [
        "a", "b",
    ]
