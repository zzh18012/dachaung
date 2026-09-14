r"""md 标题内行内标记/实体全字面 + section_path 传播（Round 1849）。

新角度（probe 实证，grep 核实零覆盖——edges13 只覆盖 html 侧
'<h2>bold <b>part</b> tail</h2>' 拍平；md 标题内 inline 标记/实体
与 html 标题实体均无覆盖）：
- **md 标题行内标记字面**：'# <b>bold</b> head' → content 逐字保留
  '<b>bold</b> head'（行内代码/链接同规），不剥壳不解析
- **实体家族对照**：md '# T &amp; U' → 'T &amp; U' 字面（md 不解
  实体）；html '<h1>a &amp; b</h1>' → 'a & b'（SAX 解码）——同语义
  标题两家族行为不同
- **section_path 带标记传播**：'# <b>B</b>' 后的段落
  section_path == '<b>B</b>'（原始标记文本进入路径并传播）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser
from app.parsers.markdown_parser import MarkdownParser


def _md(tmp_path: Path, text: str):
    p = tmp_path / "a.md"
    p.write_text(text, encoding="utf-8", newline="")
    return MarkdownParser().parse(p, compute_file_hash(p))


def _html(tmp_path: Path, text: str):
    p = tmp_path / "a.html"
    p.write_text(text, encoding="utf-8", newline="")
    return HtmlParser().parse(p, compute_file_hash(p))


def test_md_heading_inline_markup_literal(tmp_path: Path):
    doc = _md(tmp_path, "# <b>bold</b> head\n")
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "heading"
    assert doc.elements[0].content == "<b>bold</b> head"
    assert doc.elements[0].metadata == {"level": 1}

    code = _md(tmp_path, "# use `printf` now\n")
    assert code.elements[0].content == "use `printf` now"

    link = _md(tmp_path, "## [link](http://x) tail\n")
    assert link.elements[0].content == "[link](http://x) tail"
    assert link.elements[0].metadata == {"level": 2}


def test_heading_entity_family_contrast(tmp_path: Path):
    md_doc = _md(tmp_path, "# T &amp; U\n")
    assert md_doc.elements[0].type == "heading"
    assert md_doc.elements[0].content == "T &amp; U"

    html_doc = _html(tmp_path, "<h1>a &amp; b</h1>")
    assert html_doc.elements[0].type == "heading"
    assert html_doc.elements[0].content == "a & b"


def test_md_heading_section_path_propagation(tmp_path: Path):
    doc = _md(tmp_path, "# <b>B</b>\n\nafter\n")
    assert len(doc.elements) == 2
    assert doc.elements[0].source_locator["section_path"] == "<b>B</b>"
    para = doc.elements[1]
    assert para.type == "paragraph"
    assert para.content == "after"
    assert para.source_locator == {"line": 3, "section_path": "<b>B</b>"}
