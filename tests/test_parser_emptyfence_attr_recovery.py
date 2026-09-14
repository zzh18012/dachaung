r"""md 空围栏静默丢弃 + html 属性级 tokenizer 恢复（Round 1848）。

新角度（probe 实证，grep 核实零覆盖）：
- **空围栏零元素**：'```\\n```'（有无 lang 均同）→ **不产生任何
  element**（空 code block 静默丢弃），后续段落行号不受影响
- **未闭合引号吞噬**：`<img src="a.png alt="x">` → html.parser 把
  'a.png alt=' 当成 src 的完整值（直到下一个引号），x 成裸属性；
  image 照发（rp='a.png alt='），alt 缺失时 metadata 仍含空串
- **属性内换行**：src 跨行（'b\\n.png'）→ resource_path **逐字保留
  换行**，image locator 取起始标签**起始行**（多行属性不推进行号）
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


def test_md_empty_fence_dropped(tmp_path: Path):
    doc = _md(tmp_path, "```\n```\n\ntail\n")
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[0].content == "tail"
    assert doc.elements[0].source_locator == {"line": 4}

    lang = _md(tmp_path, "```py\n```\n")
    assert lang.elements == []


def test_html_malformed_quote_img(tmp_path: Path):
    doc = _html(tmp_path, '<img src="a.png alt="x"> tail')
    assert len(doc.elements) == 2
    img = doc.elements[0]
    assert img.type == "image"
    assert img.resource_path == "a.png alt="
    assert img.metadata.get("alt") == ""
    assert img.source_locator == {"line": 1}
    assert doc.elements[1].type == "paragraph"
    assert doc.elements[1].content == "tail"


def test_html_newline_inside_src_attr(tmp_path: Path):
    doc = _html(tmp_path, "<p>a</p>\n<img src='b\n.png' alt='nl'>")
    assert len(doc.elements) == 2
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[0].content == "a"
    img = doc.elements[1]
    assert img.type == "image"
    assert img.resource_path == "b\n.png"
    assert img.metadata.get("alt") == "nl"
    assert img.source_locator == {"line": 2}

    multi = _html(tmp_path, '<img\nsrc="c.png"\nalt="d">')
    assert len(multi.elements) == 1
    assert multi.elements[0].resource_path == "c.png"
    assert multi.elements[0].metadata.get("alt") == "d"
    assert multi.elements[0].source_locator == {"line": 1}
