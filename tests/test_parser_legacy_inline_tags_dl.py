r"""html 遗留行内标签族与 md 定义列表测试（Round 1843）。

新角度（probe 实证，grep -c 核实 u/s/del/ins/big/small/font/center
八标签与 md ': def' 定义列表语法全库零覆盖）：
- **六遗留行内标签剥壳**：u/s/del/ins/big/small 标签剥离、内文保留
  （'plain underline text' 等），无 strike/underline 相关 metadata；
  del 的 datetime 属性同样整弃（属性忽略家族再+1）
- **font/center 遗留标签**：color/size 属性丢弃只留内文；center 块
  压平成普通 paragraph，无居中语义
- md **定义列表不识别**：'term\\n: definition' 合并单段且换行保留
  （': def' 不产生 term/definition 元素，全家族无此语法）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser
from app.parsers.markdown_parser import MarkdownParser


def _html(tmp_path: Path, text: str):
    p = tmp_path / "r1843.html"
    p.write_text(text, encoding="utf-8", newline="")
    return HtmlParser().parse(p, compute_file_hash(p))


def _md(tmp_path: Path, text: str):
    p = tmp_path / "md_r1843.md"
    p.write_text(text, encoding="utf-8", newline="")
    return MarkdownParser().parse(p, compute_file_hash(p))


def test_html_legacy_inline_tags_flatten(tmp_path: Path):
    doc = _html(tmp_path, "<p>plain <u>underline</u> text</p>")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "plain underline text"
    assert e.metadata == {}

    pairs = [
        ("<p><s>struck</s> and <del>deleted</del></p>", "struck and deleted"),
        ("<p><ins>inserted</ins> vs <small>tiny</small></p>", "inserted vs tiny"),
        ("<p><big>large</big> rest</p>", "large rest"),
    ]
    for text, want in pairs:
        got = _html(tmp_path, text).elements[0]
        assert got.type == "paragraph"
        assert got.content == want
        assert got.metadata == {}

    dated = _html(tmp_path, '<del datetime="2026-01-01">dated del</del> alone')
    assert len(dated.elements) == 1
    assert dated.elements[0].content == "dated del alone"
    assert dated.elements[0].metadata == {}


def test_html_font_center_flatten(tmp_path: Path):
    doc = _html(tmp_path, '<font color="red">warn</font> tail')
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "warn tail"
    assert e.metadata == {}

    inline = _html(tmp_path, '<p>pre <font size="3">mid</font> post</p>')
    assert inline.elements[0].content == "pre mid post"

    center = _html(tmp_path, "<center>centered title</center>")
    assert len(center.elements) == 1
    assert center.elements[0].type == "paragraph"
    assert center.elements[0].content == "centered title"
    assert center.elements[0].metadata == {}


def test_md_definition_list_not_parsed(tmp_path: Path):
    doc = _md(tmp_path, "term\n: definition text\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "term\n: definition text"
    assert e.metadata == {}

    more = _md(tmp_path, "term\n: def\nmore para\n").elements[0]
    assert more.content == "term\n: def\nmore para"
    assert more.type == "paragraph"
