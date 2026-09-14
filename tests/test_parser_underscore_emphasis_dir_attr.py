r"""下划线强调族/词内下划线/html dir 属性测试（Round 1840）。

新角度（probe 实证，grep 核实零覆盖——`_em_` 不在任何 md parser
测试、`__strong__` 与词内 `a_b_c` 全库零覆盖、dir 属性全库零覆盖）：
- md **下划线强调全部字面**：'plain _em_ text' / 'double __strong__
  text' 都是普通段落，标记原样保留、metadata 空（星号形 `**b**`
  字面已在 edges4/edges11 锁过；下划线形单/双均未锁）
- md **词内下划线不触发任何转换**：'code a_b_c and foo_bar_baz
  here' / 'pre_alpha_post' 整段字面（identifier 原样，无 emphasis
  元数据）
- html **dir 属性被忽略、RTL 文本原样保留**：<p dir="rtl">مرحبا
  hello</p> → paragraph，content 是 'مرحبا hello'（阿拉伯字符逐字
  保留），无 dir/ltr 相关 metadata（与 style/type/start 同哲学）；
  <div dir="ltr"><span>mix</span></div> 同样压平成 'mix'
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser
from app.parsers.markdown_parser import MarkdownParser


def _md(tmp_path: Path, text: str):
    p = tmp_path / "md_r1840.md"
    p.write_text(text, encoding="utf-8", newline="")
    return MarkdownParser().parse(p, compute_file_hash(p))


def _html(tmp_path: Path, text: str):
    p = tmp_path / "r1840.html"
    p.write_text(text, encoding="utf-8", newline="")
    return HtmlParser().parse(p, compute_file_hash(p))


def test_md_underscore_emphasis_literal(tmp_path: Path):
    doc = _md(tmp_path, "plain _em_ text\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "plain _em_ text"
    assert e.metadata == {}

    strong = _md(tmp_path, "double __strong__ text\n").elements[0]
    assert strong.type == "paragraph"
    assert strong.content == "double __strong__ text"
    assert strong.metadata == {}


def test_md_intra_word_underscore_literal(tmp_path: Path):
    doc = _md(tmp_path, "code a_b_c and foo_bar_baz here\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "code a_b_c and foo_bar_baz here"
    assert e.metadata == {}

    ident = _md(tmp_path, "pre_alpha_post\n").elements[0]
    assert ident.type == "paragraph"
    assert ident.content == "pre_alpha_post"


def test_html_dir_attribute_ignored_rtl_preserved(tmp_path: Path):
    doc = _html(tmp_path, '<p dir="rtl">مرحبا hello</p>')
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "مرحبا hello"
    assert e.metadata == {}

    flat = _html(tmp_path, '<div dir="ltr"><span>mix</span></div>')
    assert len(flat.elements) == 1
    assert flat.elements[0].content == "mix"
    assert flat.elements[0].metadata == {}
