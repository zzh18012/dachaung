r"""app/parsers/markdown_parser.py 边角测试 - 第十三轮（Round 1459）。

新角度（probe 实证）blockquote 深度 + 内联标记字面性 +
setext 破折号不对称（edges1-12 未碰过）：
- 嵌套引用**只剥一层** '> ' 前缀：'> > deep' → blockquote
  内容 '> deep'；三层 '> > > deepest' → '> > deepest'；
  多行嵌套 '> > a\n> > b' → '> a\n> b'
- **lazy 续行不并入**引用：'> line1\nline2' → bq 'line1' +
  独立 paragraph 'line2'（line 2）
- 引用内**不解析任何结构**：'> - item' 与 '> # head' 都整段
  进 blockquote（列表标记/井号字面保留）
- 内联标记全部字面：`code`、[text](url)、<autolink>、
  <b>inline html</b>、<!-- 注释 -->（注释**不切断段落**，
  与后续行合并成一个 paragraph）
- 转义 '\\#' 不被识别为标题（也**不解转义**，反斜杠保留）
- setext 不对称：'Title\\n===' 并入一个段落（= 不是分隔线），
  'Title\\n---\\nbody' 中 **--- 是 thematic break** → 拆成
  两个 paragraph 且 break 行消失
- '-\\tx' tab 作标记后分隔符 → 正常 list_item
- 硬换行行尾双空格**保留在内容里**（'a  \\nb'）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.markdown_parser import \
    MarkdownParser

TMP_NAME = "md_edge13_probe.md"


def _parse(tmp_path, text, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8",
                 newline="")
    return MarkdownParser().parse(
        p, compute_file_hash(p))


# ---------- 嵌套 blockquote ----------

def test_nested_bq_strips_one_level(
        tmp_path):
    doc = _parse(tmp_path, "> > deep\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "> deep"
    assert e.metadata == \
        {"kind": "blockquote"}


def test_triple_bq_two_levels_left(
        tmp_path):
    doc = _parse(tmp_path, "> > > deepest\n")
    e = doc.elements[0]
    assert e.content == "> > deepest"
    assert e.metadata["kind"] == \
        "blockquote"


def test_nested_bq_multiline_join(
        tmp_path):
    doc = _parse(
        tmp_path, "> > a\n> > b\n")
    e = doc.elements[0]
    assert e.content == "> a\n> b"
    assert e.metadata["kind"] == \
        "blockquote"


def test_lazy_line_outside_bq(
        tmp_path):
    doc = _parse(
        tmp_path, "> line1\nline2\n")
    assert [(e.content,
             e.metadata.get("kind"))
            for e in doc.elements] == [
        ("line1", "blockquote"),
        ("line2", None),
    ]
    assert doc.elements[
        1].source_locator["line"] == 2


# ---------- 引用内不解析结构 ----------

def test_bq_list_marker_literal(
        tmp_path):
    doc = _parse(tmp_path, "> - item\n")
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "- item"
    assert e.metadata["kind"] == \
        "blockquote"


def test_bq_heading_marker_literal(
        tmp_path):
    doc = _parse(tmp_path, "> # head\n")
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "# head"
    assert e.metadata["kind"] == \
        "blockquote"


# ---------- 内联标记字面性 ----------

def test_inline_code_literal(tmp_path):
    doc = _parse(
        tmp_path, "use `code` here\n")
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == \
        "use `code` here"


def test_link_literal(tmp_path):
    doc = _parse(
        tmp_path, "see [text](http://u)\n")
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == \
        "see [text](http://u)"


def test_autolink_literal(tmp_path):
    doc = _parse(
        tmp_path, "<http://x/y>\n")
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "<http://x/y>"


def test_inline_html_literal(
        tmp_path):
    doc = _parse(
        tmp_path, "<b>bold</b> tail\n")
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == \
        "<b>bold</b> tail"


def test_html_comment_no_break(
        tmp_path):
    doc = _parse(
        tmp_path, "<!-- hidden -->\nvis\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == \
        "<!-- hidden -->\nvis"


def test_escaped_hash_literal(
        tmp_path):
    doc = _parse(
        tmp_path, "\\# not heading\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "\\# not heading"


# ---------- setext --- vs === ----------

def test_setext_eq_joins_paragraph(
        tmp_path):
    doc = _parse(
        tmp_path, "Title\n===\nbody\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "Title\n===\nbody"),
    ]
    assert doc.warnings == []


def test_setext_dash_is_break(
        tmp_path):
    doc = _parse(
        tmp_path, "Title\n---\nbody\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "Title"),
        ("paragraph", "body"),
    ]
    assert doc.warnings == []
    assert doc.elements[
        1].source_locator["line"] == 3


def test_spaced_break_between_text(
        tmp_path):
    doc = _parse(
        tmp_path, "text\n- - -\nmore\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "text"),
        ("paragraph", "more"),
    ]
    assert doc.warnings == []


# ---------- 其他 ----------

def test_tab_after_marker(tmp_path):
    doc = _parse(tmp_path, "-\tx\n")
    e = doc.elements[0]
    assert e.type == "list_item"
    assert e.content == "x"
    assert e.metadata["ordered"] is False


def test_hard_break_ws_kept(
        tmp_path):
    doc = _parse(tmp_path, "a  \nb\n")
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "a  \nb"
