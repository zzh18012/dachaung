r"""app/parsers/html_parser.py 边角测试 - 第十二轮（Round 1376）。

补强 edges9（rowspan/colspan）后的表格结构面（probe 实证，历史
html 测试对 thead/tbody/tfoot/colgroup/caption 零覆盖）：
- thead/tbody/tfoot 行按文档序合进同一张表；分隔行固定在第一行后
  （不区分 th/td）
- 单元格内 <br> 丢弃无分隔（'line1line2'）
- <caption> 文本被吞（表内有行也一样）；caption-only 表（无行）
  整个消失——不产 table 元素
- <figcaption> → 普通 paragraph（不是 caption 类型）
- <colgroup>/<col> 静默忽略，列宽不受影响
- 空 cell 渲染为 '|  |'
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser


def _parse(frag):
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "t.html").write_text(
            "<html><body>" + frag + "</body></html>",
            encoding="utf-8")
        return HtmlParser().parse(
            tp / "t.html",
            compute_file_hash(tp / "t.html"))


# ---------- thead / tbody / tfoot ----------

def test_thead_tbody_merged():
    doc = _parse(
        "<table><thead><tr><th>H1</th></tr>"
        "</thead><tbody><tr><td>d1</td></tr>"
        "</tbody></table>")
    assert doc.elements[0].content == (
        "| H1 |\n| --- |\n| d1 |")


def test_tfoot_document_order():
    doc = _parse(
        "<table><thead><tr><th>H</th></tr></thead>"
        "<tbody><tr><td>d</td></tr></tbody>"
        "<tfoot><tr><td>F</td></tr></tfoot>"
        "</table>")
    assert doc.elements[0].content == (
        "| H |\n| --- |\n| d |\n| F |")


def test_single_table_element():
    doc = _parse(
        "<table><thead><tr><th>H</th></tr></thead>"
        "<tbody><tr><td>d</td></tr></tbody>"
        "</table>")
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "table"


def test_separator_after_first_row_regardless():
    doc = _parse(
        "<table><tr><td>A</td><td>B</td></tr>"
        "<tr><td>1</td><td>2</td></tr></table>")
    assert doc.elements[0].content == (
        "| A | B |\n| --- | --- |\n| 1 | 2 |")


# ---------- 单元格内 <br> ----------

def test_br_in_cell_no_separator():
    doc = _parse("<table><tr><td>line1<br>line2"
                 "</td></tr></table>")
    assert doc.elements[0].content == (
        "| line1line2 |\n| --- |")


# ---------- caption 被吞 ----------

def test_caption_text_swallowed():
    doc = _parse("<table><caption>Cap</caption>"
                 "<tr><td>d</td></tr></table>")
    assert doc.elements[0].content == (
        "| d |\n| --- |")
    assert "Cap" not in doc.elements[0].content


def test_caption_only_table_vanishes():
    doc = _parse("<table><caption>C</caption>"
                 "</table><p>t</p>")
    assert [e.type for e in doc.elements
            ] == ["paragraph"]
    assert doc.elements[0].content == "t"


def test_caption_no_warning():
    doc = _parse("<table><caption>C</caption>"
                 "<tr><td>d</td></tr></table>")
    assert doc.warnings == []


# ---------- figcaption ----------

def test_figcaption_is_paragraph():
    doc = _parse("<figure><figcaption>Cap text"
                 "</figcaption></figure>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "Cap text")]


def test_figcaption_after_table():
    doc = _parse("<table><tr><td>d</td></tr>"
                 "</table><figcaption>After"
                 "</figcaption>")
    assert [(e.type, e.content[:12])
            for e in doc.elements] == [
        ("table", "| d |\n| --- "),
        ("paragraph", "After")]


# ---------- colgroup ----------

def test_colgroup_ignored():
    doc = _parse(
        "<table><colgroup><col span='2'>"
        "</colgroup><tr><td>a</td><td>b</td>"
        "</tr></table>")
    assert doc.elements[0].content == (
        "| a | b |\n| --- | --- |")


def test_col_no_warning():
    doc = _parse(
        "<table><colgroup><col></colgroup>"
        "<tr><td>a</td></tr></table>")
    assert doc.warnings == []


# ---------- 空 cell ----------

def test_empty_cell_rendered_as_space():
    doc = _parse("<table><tr><td></td><td>x</td>"
                 "</tr></table>")
    assert doc.elements[0].content == (
        "|  | x |\n| --- | --- |")


# ---------- th 属性 ----------

def test_th_scope_ignored():
    doc = _parse("<table><tr><th scope='col'>H"
                 "</th></tr></table>")
    assert doc.elements[0].content == (
        "| H |\n| --- |")
    assert doc.elements[0].metadata == {
        "row_count": 1, "col_count": 1,
        "source": "html_table"}


# ---------- schema ----------

def test_structured_table_passes_schema():
    from app.schema import is_valid
    doc = _parse(
        "<table><thead><tr><th>H</th></tr></thead>"
        "<tbody><tr><td>d</td></tr></tbody>"
        "<tfoot><tr><td>F</td></tr></tfoot>"
        "</table>")
    assert is_valid(doc.to_dict())
