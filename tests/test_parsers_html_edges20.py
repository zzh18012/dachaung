r"""html 空元素安全边界测试（Round 1489）。

与 markdown 崩溃家族（R1484/1486/1487：'#   \n' /
'-   \n' → ValueError 穿透）对照，probe 实证 **html 的
空元素全部安全**（不崩、静默跳过）：

- **空标题/空段/空 bq/空 pre 不产元素**：'<h1></h1>'
  （含纯空白 '<h1>   </h1>'）→ 无 element，仅文件级
  html_no_content
- **空 li 跳过不影响兄弟**：'<li></li><li>b</li>' → 只
  保留 'b'（marker 元数据完好）
- **空 table 不产元素**：'<table></table>' 无 element
  （对照 edges18 的 '<tr></tr>' 产 1x0 空表）
- **img 空 alt 仍产 image**：content=None +
  resource_path='x.png' + alt=''（空 alt 不丢图）
- **空标题不打扰 section 上下文**：h1 真标题后插空 h2
  → 只有 'T' heading + 'body' paragraph
- **嵌套空 bq 塌缩**：'<blockquote><blockquote>'
  '</blockquote>x</blockquote>' → 单 paragraph 'x'
  kind=blockquote
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


# ---------- 空元素安全（不崩） ----------

def test_empty_heading_no_element(
        tmp_path):
    for body in ("<h1></h1>",
                 "<h1>   </h1>"):
        doc = _html(tmp_path, body)
        assert doc.elements == []
        assert [w.code for w in
                doc.warnings] == \
            ["html_no_content"]


def test_empty_p_skipped_no_warning(
        tmp_path):
    doc = _html(
        tmp_path,
        "<p></p><p>after</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "after"),
    ]
    assert doc.warnings == []


def test_empty_li_skipped_sibling_kept(
        tmp_path):
    doc = _html(
        tmp_path,
        "<ul><li></li>"
        "<li>b</li></ul>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "b"),
    ]
    assert doc.elements[0].metadata == {
        "ordered": False,
        "marker": "unordered",
    }
    assert doc.warnings == []


def test_empty_table_no_element(
        tmp_path):
    doc = _html(tmp_path,
                "<table></table>")
    assert doc.elements == []
    assert [w.code for w in
            doc.warnings] == \
        ["html_no_content"]


def test_img_empty_alt_still_emitted(
        tmp_path):
    doc = _html(
        tmp_path,
        '<img src="x.png" alt="">')
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "image"
    assert e.content is None
    assert e.resource_path == "x.png"
    assert e.metadata == {"alt": ""}
    assert doc.warnings == []


# ---------- 上下文不受空元素打扰 ----------

def test_empty_h2_between_content_invisible(
        tmp_path):
    doc = _html(
        tmp_path,
        "<h1>T</h1><h2></h2>"
        "<p>body</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "T"),
        ("paragraph", "body"),
    ]
    assert doc.elements[0].metadata == {
        "level": 1,
    }
    assert doc.warnings == []


def test_nested_empty_bq_collapses(
        tmp_path):
    doc = _html(
        tmp_path,
        "<blockquote>"
        "<blockquote></blockquote>x"
        "</blockquote>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "x"),
    ]
    assert doc.elements[0].metadata == {
        "kind": "blockquote"}
    assert doc.warnings == []


def test_empty_bq_between_paragraphs(
        tmp_path):
    doc = _html(
        tmp_path,
        "<p>a</p>"
        "<blockquote></blockquote>"
        "<p>b</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "a"),
        ("paragraph", "b"),
    ]
    assert doc.warnings == []
