r"""app/parsers/markdown_parser.py 边角测试 - 第十轮（Round 1373）。

补强未触达面（probe 实证，历史 markdown 测试对以下全部零覆盖）：
- HTML 实体不解码：'&amp;' '&lt;' 原样保留在 content
- 反斜杠转义不解：'\\*' 字面保留（段落级；表级转义另测）
- autolink '<https://…>' 原样保留
- 引用链接 [text][1] 原样 + 定义行 '[1]: …' 独立成段（三种：
  full / collapsed [text][] / shortcut [text]）
- 脚注 [^1] 原样 + 定义 '[^1]: …' 独立成段
- 硬换行行尾双空格保留在 content（'line one  \\nline two'）
- 行内/块级 HTML 原样保留为段落文本
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.markdown_parser import MarkdownParser


def _parse(md):
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "t.md").write_text(md, encoding="utf-8")
        return MarkdownParser().parse(
            tp / "t.md",
            compute_file_hash(tp / "t.md"))


# ---------- 实体不解码 ----------

def test_amp_entity_literal():
    assert _parse("a &amp; b\n").elements[
        0].content == "a &amp; b"


def test_lt_gt_entities_literal():
    assert _parse("a &lt;c&gt;\n").elements[
        0].content == "a &lt;c&gt;"


def test_named_entity_not_decoded():
    assert _parse("x &nbsp; y\n").elements[
        0].content == "x &nbsp; y"


def test_numeric_entity_not_decoded():
    assert _parse("&#65;\n").elements[
        0].content == "&#65;"


# ---------- 反斜杠转义不解 ----------

def test_backslash_star_literal():
    assert _parse(
        "literal \\*not em\\* here\n"
    ).elements[0].content == \
        "literal \\*not em\\* here"


def test_backslash_bracket_literal():
    assert _parse("a \\[b\\] c\n").elements[
        0].content == "a \\[b\\] c"


def test_double_backslash_literal():
    assert _parse("path C:\\\\dir\n").elements[
        0].content == "path C:\\\\dir"


# ---------- autolink ----------

def test_autolink_raw_preserved():
    assert _parse(
        "see <https://example.com> now\n"
    ).elements[0].content == \
        "see <https://example.com> now"


def test_autolink_angle_brackets_kept():
    doc = _parse("<mailto:a@b.c>\n")
    assert doc.elements[0].content == \
        "<mailto:a@b.c>"


# ---------- 引用链接 ----------

def test_full_reference_link_literal():
    doc = _parse("see [text][1] here\n\n"
                 "[1]: https://example.com\n")
    assert [e.content for e in doc.elements
            ] == ["see [text][1] here",
                  "[1]: https://example.com"]


def test_collapsed_reference_literal():
    doc = _parse("see [text][] here\n\n"
                 "[text]: https://example.com\n")
    assert [e.content for e in doc.elements
            ] == ["see [text][] here",
                  "[text]: https://example.com"]


def test_shortcut_reference_literal():
    doc = _parse("see [text] here\n\n"
                 "[text]: https://example.com\n")
    assert [e.content for e in doc.elements
            ] == ["see [text] here",
                  "[text]: https://example.com"]


def test_reference_definition_is_paragraph():
    doc = _parse("[1]: https://example.com\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph",
         "[1]: https://example.com")]


# ---------- 脚注 ----------

def test_footnote_marker_literal():
    doc = _parse("text[^1]\n\n"
                 "[^1]: note body\n")
    assert [e.content for e in doc.elements
            ] == ["text[^1]", "[^1]: note body"]


def test_footnote_definition_is_paragraph():
    doc = _parse("[^1]: note body\n")
    assert doc.elements[0].type == "paragraph"


def test_multiple_footnotes():
    doc = _parse("a[^1] b[^2]\n\n[^1]: n1\n"
                 "[^2]: n2\n")
    assert [e.content for e in doc.elements
            ] == ["a[^1] b[^2]",
                  "[^1]: n1\n[^2]: n2"]


# ---------- 硬换行 ----------

def test_hard_break_trailing_spaces_kept():
    assert _parse("line one  \nline two\n"
                  ).elements[0].content == \
        "line one  \nline two"


def test_hard_break_single_newline_no_spaces():
    assert _parse("line one\nline two\n"
                  ).elements[0].content == \
        "line one\nline two"


# ---------- HTML 原样 ----------

def test_inline_html_preserved():
    assert _parse(
        "before <b>bold</b> after\n"
    ).elements[0].content == \
        "before <b>bold</b> after"


def test_block_html_preserved():
    doc = _parse("<div>block html</div>\n\n"
                 "para\n")
    assert [e.content for e in doc.elements
            ] == ["<div>block html</div>", "para"]


def test_html_comment_preserved():
    assert _parse("<!-- note -->\n").elements[
        0].content == "<!-- note -->"


def test_br_tag_preserved():
    assert _parse("a<br>b\n").elements[
        0].content == "a<br>b"


# ---------- 无警告 + 一致性 ----------

def test_literal_board_no_warnings():
    doc = _parse("a &amp; \\* [x][1] <b>t</b>\n\n"
                 "[1]: u\n")
    assert doc.warnings == []


def test_literal_doc_identity():
    doc = _parse("plain\n")
    assert doc.source_type == "markdown"
    assert doc.parser_name == "markdown"
    assert doc.parser_version == "stdlib/0.1.0"


def test_literal_doc_passes_schema():
    from app.schema import is_valid
    doc = _parse("a &amp; \\* [x][1]\n\n"
                 "[1]: u\n")
    assert is_valid(doc.to_dict())
