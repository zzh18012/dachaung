r"""app/parsers/html_parser.py 边角测试 - 第十五轮（Round 1460）。

新角度（probe 实证）实体解码 + 定义列表 + 容器合并
（edges1-14 未碰过）：
- <dl>/<dt>/<dd> **不是块**：全部文本并进一个 paragraph
  （'TermDef'；dd-only 'Def'；多 dt 串联 'ABC'；内嵌 <p>
  也并入 'TPara def'）
- 命名实体解码：&copy; → '©'、&nbsp; → \\xa0、&mdash; → '—'
  （内容中间保留 \\xa0）；**未知实体字面**（'&nosuch; stays'）；
  **分号缺失仍解码**（'&copy stays' → '© stays'）；
  实体在 <h1> 内解码且进 section_path（'A & B'）
- <div> 相邻**合并成单段**：'<div>one</div><div>two</div>'
  → 'onetwo'；div 后跟 <p> **同样并段**（'ab'）——div 不 flush
  loose 缓冲，<p> 开标签也不先 flush
- <sup>/<sub> 拍平：'x<sup>2</sup> y<sub>1</sub>' → 'x2 y1'
- <hgroup> 透传：<h1>+<h2> 两个 heading，section_path 栈
  正常（'T' → 'T > S'，正文承袭 'T > S'）
- <pre> 内实体照常解码（'a &lt; b' → 'a < b'，kind 保留）
- 嵌套 table 内容形状：外层行文本**丢失**、内层行存活，
  单表 '| |'/'| in |' + html_nested_table 告警
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser

TMP_NAME = "html_edge15_probe.html"


def _parse(tmp_path, html, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(html, encoding="utf-8",
                 newline="")
    return HtmlParser().parse(
        p, compute_file_hash(p))


# ---------- 定义列表 ----------

def test_dl_dt_dd_merged(tmp_path):
    doc = _parse(
        tmp_path,
        "<dl><dt>Term</dt><dd>Def</dd></dl>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "TermDef"),
    ]


def test_dd_only(tmp_path):
    doc = _parse(
        tmp_path, "<dl><dd>Def</dd></dl>")
    assert [e.content
            for e in doc.elements] == ["Def"]


def test_dt_multi_concat(tmp_path):
    doc = _parse(
        tmp_path,
        "<dl><dt>A</dt><dt>B</dt>"
        "<dd>C</dd></dl>")
    assert [e.content
            for e in doc.elements] == ["ABC"]


def test_dl_nested_p_merged(tmp_path):
    doc = _parse(
        tmp_path,
        "<dl><dt>T</dt>"
        "<dd><p>Para def</p></dd></dl>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "TPara def"),
    ]


# ---------- 实体解码 ----------

def test_named_entities_decoded(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<p>&copy; &nbsp; &mdash;</p>")
    assert doc.elements[
        0].content == "© \xa0 —"


def test_unknown_entity_literal(
        tmp_path):
    doc = _parse(
        tmp_path, "<p>&nosuch; stays</p>")
    assert doc.elements[
        0].content == "&nosuch; stays"


def test_entity_no_semicolon(
        tmp_path):
    doc = _parse(
        tmp_path, "<p>&copy stays</p>")
    assert doc.elements[
        0].content == "© stays"


def test_entity_in_heading(
        tmp_path):
    doc = _parse(
        tmp_path, "<h1>A &amp; B</h1>")
    e = doc.elements[0]
    assert e.type == "heading"
    assert e.content == "A & B"
    assert e.source_locator[
        "section_path"] == "A & B"


def test_pre_entity_decoded(
        tmp_path):
    doc = _parse(
        tmp_path, "<pre>a &lt; b</pre>")
    e = doc.elements[0]
    assert e.content == "a < b"
    assert e.metadata == \
        {"kind": "preformatted"}


# ---------- div 容器合并 ----------

def test_div_pair_merges(tmp_path):
    doc = _parse(
        tmp_path,
        "<div>one</div><div>two</div>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "onetwo"),
    ]


def test_div_then_p_merges(
        tmp_path):
    doc = _parse(
        tmp_path, "<div>a</div><p>b</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "ab"),
    ]


# ---------- sup / sub ----------

def test_sup_sub_flattened(tmp_path):
    doc = _parse(
        tmp_path,
        "<p>x<sup>2</sup> y<sub>1</sub></p>")
    assert doc.elements[
        0].content == "x2 y1"


# ---------- hgroup ----------

def test_hgroup_two_headings(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<hgroup><h1>T</h1><h2>S</h2>"
        "</hgroup><p>body</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "T"),
        ("heading", "S"),
        ("paragraph", "body"),
    ]
    assert doc.elements[
        1].source_locator["section_path"] \
        == "T > S"
    assert doc.elements[
        2].source_locator["section_path"] \
        == "T > S"


# ---------- 嵌套表内容形状 ----------

def test_nested_table_shape(tmp_path):
    doc = _parse(
        tmp_path,
        "<table><tr><td>outer<table>"
        "<tr><td>in</td></tr></table>"
        "</td></tr></table>")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "table"
    assert e.content == \
        "|  |\n| --- |\n| in |"
    assert e.metadata["row_count"] == 2
    assert "outer" not in e.content
    assert any(
        w.code == "html_nested_table"
        for w in doc.warnings)
