r"""HTML 块级自闭合 `<pre/>` `<blockquote/>` `<ol/>` `<h2/>`（Round 2007，a 优先级）。

startendtag 委托家族续（R2006 锁 `<table/>` 唯一吞噬形态）。
html_parser.py:275-277 对非 img/br/hr 自闭合只转发 handle_starttag：
其余块级自闭合**只当开标签**——块上下文活到下一块标签或 EOF
flush，不吞噬后续块。零覆盖（grep 实证 tests/ 无这些形态）。
探针 R2007 实证：

- **T1** '<pre/>abc' → pre 块开到 EOF → paragraph kind=preformatted
- **T2** '<p>x</p><pre/>y<h1>t</h1>' → [para x, pre y, heading t]
  ——`<pre/>` 不吞 h1（块标签互相 flush，与表格吞噬形态对照）
- **T3** '<blockquote/><p>a</p>b' → p 在 blockquote 上下文被
  忽略（:232-234）→ 单 blockquote 'ab'
- **T4** '<ol/><li>a</ol><li>b' → 'a' ordered=True（栈 [ol]）/
  'b' 孤儿 ordered=False——同文档两 li 元数据对照
- **T5** '<h2/>t' → heading level 2

判别式：T2 若 y/t 被吞翻；T3 若 'a'/'b' 成独立段翻；T4 若两
li 同 ordered 翻；T5 若 level≠2 翻。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser


def _parse(tmp_path: Path, body: str):
    p = tmp_path / "b.html"
    p.write_text(body, encoding="utf-8", newline="")
    return HtmlParser().parse(p, compute_file_hash(p))


def test_pre_selfclose_flushes_at_eof(tmp_path):
    """T1：'<pre/>abc' → paragraph kind=preformatted（块活到 EOF flush）。"""
    d = _parse(tmp_path, "<pre/>abc")
    assert [(e.type, e.content) for e in d.elements] == [("paragraph", "abc")]
    assert d.elements[0].metadata == {"kind": "preformatted"}
    assert d.warnings == []


def test_pre_selfclose_not_swallow_blocks(tmp_path):
    """T2：pre 自闭合后的 h1 不被吞 → [para x, pre y, heading t]。"""
    d = _parse(tmp_path, "<p>x</p><pre/>y<h1>t</h1>")
    assert [(e.type, e.content, e.metadata) for e in d.elements] == [
        ("paragraph", "x", {}),
        ("paragraph", "y", {"kind": "preformatted"}),
        ("heading", "t", {"level": 1}),
    ]
    assert d.warnings == []


def test_blockquote_selfclose_ignores_p(tmp_path):
    """T3：blockquote 上下文中 <p> 被忽略 → 单 blockquote 'ab'。"""
    d = _parse(tmp_path, "<blockquote/><p>a</p>b")
    assert [(e.type, e.content) for e in d.elements] == [("paragraph", "ab")]
    assert d.elements[0].metadata == {"kind": "blockquote"}
    assert d.warnings == []


def test_ol_selfclose_ordered_contrast(tmp_path):
    """T4：'<ol/><li>a</ol><li>b' → a ordered=True / b 孤儿 ordered=False。"""
    d = _parse(tmp_path, "<ol/><li>a</ol><li>b")
    assert [(e.type, e.content, e.metadata) for e in d.elements] == [
        ("list_item", "a", {"ordered": True, "marker": "ordered"}),
        ("list_item", "b", {"ordered": False, "marker": "unordered"}),
    ]
    assert d.warnings == []


def test_h2_selfclose_level(tmp_path):
    """T5：'<h2/>t' → heading level 2。"""
    d = _parse(tmp_path, "<h2/>t")
    assert [(e.type, e.content, e.metadata) for e in d.elements] == [
        ("heading", "t", {"level": 2})]
    assert d.warnings == []
