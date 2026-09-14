r"""html CRLF 内容剥离 + 行计数 + 裸 CR 换行（Round 1858）。

新角度（probe 实证；edges:380/392 只断言**元素个数**——内容级
'\r' 剥离、行定位数值、裸 CR 计行全库零覆盖；ipynb CRLF 已被
crlf_text_ipynb 锁故弃用）：
- **内容 \r 剥离**：'<p>a\\r\\nb</p>' → content 'a\\nb'（非
  'a\\r\\nb'）；table cell / img alt / pre 同步归一
- **行定位**：CRLF 按**单行**计数（P2 在 line 4 而非 5）；
  裸 '\\r'（无 \\n）也推进行号（y 在 line 2）
- **section_path**：CRLF 分隔下 'T' 照常传播到后续段落
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser


def _parse(raw: bytes):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "a.html"
        p.write_bytes(raw)
        return HtmlParser().parse(p, compute_file_hash(p))


def test_html_crlf_text_and_locators():
    doc = _parse(b"<h1>T</h1>\r\n<p>a\r\nb</p>\r\n<p>c</p>")
    assert [(e.type, e.content) for e in doc.elements] == [
        ("heading", "T"), ("paragraph", "a\nb"), ("paragraph", "c")]
    assert [e.source_locator["line"] for e in doc.elements] == [1, 2, 4]
    assert all(e.source_locator.get("section_path") == "T"
               for e in doc.elements)


def test_html_cr_only_counts_lines():
    doc = _parse(b"<p>x</p>\r<p>y</p>")
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "x"), ("paragraph", "y")]
    assert [e.source_locator["line"] for e in doc.elements] == [1, 2]


def test_html_crlf_normalized_in_table_alt_pre():
    doc = _parse(b"<table><tr><td>a\r\nb</td></tr></table>")
    assert doc.elements[0].type == "table"
    assert doc.elements[0].content == "| a\nb |\n| --- |"

    doc = _parse(b'<img src="x.png" alt="a\r\nb">')
    assert doc.elements[0].metadata == {"alt": "a\nb"}

    doc = _parse(b"<pre>a\r\nb</pre>")
    assert [(e.type, e.content, e.metadata) for e in doc.elements] == [
        ("paragraph", "a\nb", {"kind": "preformatted"})]
