r"""app/parsers/html_parser.py 边角测试 - 第十三轮（Round 1381）。

补强 heading 边角（probe 实证）：
- 空 heading（<h2></h2>）静默跳过——不产元素、不告警
- <h7> 未知标签透明 → 普通 paragraph
- heading 内 inline 标签摊平（'bold <b>part</b> tail' →
  'bold part tail'）
- heading 内 <img> → heading 与 image 各一个元素，image 继承
  heading 的 section_path
- heading 属性（id/class）不影响内容
- 连续 heading 各自独立，section_path 逐级
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


# ---------- 空 heading ----------

def test_empty_heading_skipped():
    doc = _parse("<h2></h2><p>after</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "after")]


def test_empty_heading_only_doc_level_warning():
    """空 heading 本身无专属告警——只有整文档无内容的
    html_no_content。"""
    doc = _parse("<h2></h2>")
    assert [(w.code) for w in doc.warnings] == \
        ["html_no_content"]


def test_whitespace_heading_skipped():
    doc = _parse("<h2> </h2><p>x</p>")
    assert [e.type for e in doc.elements
            ] == ["paragraph"]


# ---------- 未知级别 ----------

def test_h7_is_paragraph():
    doc = _parse("<h7>no</h7>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "no")]


# ---------- inline 摊平 ----------

def test_inline_in_heading_flattened():
    doc = _parse("<h2>bold <b>part</b> tail</h2>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "bold part tail")]
    assert doc.elements[0].metadata["level"] == 2


def test_heading_whitespace_stripped():
    doc = _parse("<h2>   spaced   </h2>")
    assert doc.elements[0].content == "spaced"


def test_heading_attrs_ignored():
    doc = _parse(
        "<h2 id='x' class='y'>T</h2>")
    assert doc.elements[0].content == "T"
    assert doc.elements[0].metadata == {
        "level": 2}


# ---------- heading 内 img ----------

def test_img_in_heading_two_elements():
    doc = _parse(
        "<h2>title <img src='i.png' alt='IA'>"
        "</h2>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "title"), ("image", None)]


def test_img_in_heading_resource():
    doc = _parse(
        "<h2>title <img src='i.png' alt='IA'>"
        "</h2>")
    img = doc.elements[1]
    assert img.resource_path == "i.png"
    assert img.metadata == {"alt": "IA"}


def test_img_inherits_heading_section_path():
    doc = _parse(
        "<h2>title <img src='i.png'></h2>")
    img = doc.elements[1]
    assert img.source_locator["section_path"] \
        == "title"


def test_heading_sets_own_section_path():
    doc = _parse("<h2>title <img src='i.png'>"
                 "</h2>")
    h = doc.elements[0]
    assert h.source_locator["section_path"] == \
        "title"


# ---------- 连续 heading ----------

def test_consecutive_headings_independent():
    doc = _parse("<h2>A</h2><h3>B</h3>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "A"), ("heading", "B")]


def test_para_under_second_heading():
    doc = _parse(
        "<h2>A</h2><h3>B</h3><p>under</p>")
    para = doc.elements[2]
    assert para.source_locator[
        "section_path"] == "A > B"


# ---------- 全级别 ----------

def test_all_levels():
    doc = _parse(
        "<h1>a</h1><h2>b</h2><h3>c</h3>"
        "<h4>d</h4><h5>e</h5><h6>f</h6>")
    assert [e.metadata["level"]
            for e in doc.elements] == \
        [1, 2, 3, 4, 5, 6]


# ---------- schema ----------

def test_heading_board_passes_schema():
    from app.schema import is_valid
    doc = _parse(
        "<h2>title <img src='i.png'></h2>"
        "<p>tail</p>")
    assert is_valid(doc.to_dict())
