r"""html 大小写/属性形态/裸元素测试（Round 1501）。

probe 实证（edges1-20 与主文件未碰）：

- **大写/混合大小写标签照常**：'<H1>UPPER</H1><P>' →
  heading level 1 + paragraph；'<H2>Mixed</h2>' →
  level 2（HTMLParser 自动小写化）
- **无引号属性照常**：'<img src=pic.png alt=hi>' →
  image + alt='hi' + resource_path='pic.png'
- **'<p/>' 视为开标签**：后续文本流入该段落 → 单段
  'after'
- **十六进制实体 &#x41; → 'A'**（主文件只锁了十进制
  &#65;）
- **三重嵌套 bq 不追踪深度**：deep 文本单段
  kind=blockquote（无 depth 字段）
- **裸 '<li>'（不在 ul/ol 内）独立成 list_item**：前
  后文本各成段、互不合并
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


# ---------- 标签大小写 ----------

def test_uppercase_tags(tmp_path):
    doc = _html(
        tmp_path,
        "<H1>UPPER</H1><P>para</P>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "UPPER"),
        ("paragraph", "para"),
    ]
    assert doc.elements[0].metadata == {
        "level": 1}
    assert doc.warnings == []


def test_mixed_case_tags(tmp_path):
    doc = _html(
        tmp_path, "<H2>Mixed</h2>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "Mixed"),
    ]
    assert doc.elements[0].metadata == {
        "level": 2}


# ---------- 属性形态 ----------

def test_unquoted_attrs(tmp_path):
    doc = _html(
        tmp_path,
        "<img src=pic.png alt=hi>")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "image"
    assert e.content is None
    assert e.resource_path == "pic.png"
    assert e.metadata == {"alt": "hi"}
    assert doc.warnings == []


def test_self_closing_p_absorbs_text(
        tmp_path):
    doc = _html(tmp_path,
                "<p/>after")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "after"),
    ]
    assert doc.warnings == []


# ---------- 实体与嵌套 ----------

def test_hex_entity_decoded(tmp_path):
    doc = _html(
        tmp_path,
        "<p>A &#x41; hex</p>")
    assert [e.content
            for e in doc.elements] == [
        "A A hex",
    ]


def test_triple_nested_bq_no_depth(
        tmp_path):
    doc = _html(
        tmp_path,
        "<blockquote>"
        "<blockquote>"
        "<blockquote>deep"
        "</blockquote>"
        "</blockquote></blockquote>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "deep"),
    ]
    assert doc.elements[0].metadata == {
        "kind": "blockquote"}
    assert doc.warnings == []


def test_stray_li_own_element(
        tmp_path):
    doc = _html(
        tmp_path,
        "text then <li>orphan</li>"
        " more")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "text then"),
        ("list_item", "orphan"),
        ("paragraph", "more"),
    ]
    assert doc.elements[1].metadata == {
        "ordered": False,
        "marker": "unordered",
    }
    assert doc.warnings == []
