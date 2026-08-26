r"""parser html 锚文本保留、style/script
内容整体丢弃（Round 1819）。

新角度：R1818 锁 max_chars 变体——**
<a href> 内联——锚文本保留 'see link
here'、href 丢弃；<style> 与 <script>
内容整体静默丢弃（CSS/JS 不发射、无警
告、后续段落照常）**零覆盖：

- **锚链接**：'see link here'
- **<style>**：仅剩正文段
- **<script>**：同上无警告
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def test_html_anchor_text_only(tmp_path):
    doc, errors = _run(
        tmp_path,
        '<p>see <a href="http://x">link</a> here</p>')
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "see link here")]


def test_html_style_dropped(tmp_path):
    doc, errors = _run(
        tmp_path,
        '<style>.x{color:red}</style><p>a</p>')
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "a"]
    assert doc.warnings == []


def test_html_script_dropped(tmp_path):
    doc, errors = _run(
        tmp_path,
        '<script>var x=1;</script><p>a</p>')
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "a"]
    assert doc.warnings == []
