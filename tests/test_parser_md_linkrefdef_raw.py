r"""md 链接引用定义不识别：原样段落、无解析、按段落规则合并（Round 1847）。

新角度（probe 实证，grep 核实 '\[ref\]: url' 形式全库零覆盖——
markdown_edges10 只覆盖脚注定义 '\[\^1\]: …' 独立成段）：
- **定义行原样成段**：'[ref]: http://example.com "Title"' → paragraph
  逐字保留，不解析、不消解、无链接语义
- **定义+使用相邻合并**：定义行与 'see [ref] here' 之间无空行 →
  单一段落（'\\n' 连接），[ref] 字面保留（不替换为 URL）
- **多定义相邻/标题行跟进**：两个定义行相邻 → 合并单段；定义的
  '"Title"' 标题行同样并入段落（定义不吞噬后续行，按普通段落合并）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.markdown_parser import MarkdownParser


def _parse(tmp_path: Path, text: str):
    p = tmp_path / "a.md"
    p.write_text(text, encoding="utf-8", newline="")
    return MarkdownParser().parse(p, compute_file_hash(p))


def test_linkrefdef_standalone_raw_paragraph(tmp_path: Path):
    doc = _parse(tmp_path, '[ref]: http://example.com "Title"\n\npara text\n')
    assert len(doc.elements) == 2
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[0].content == '[ref]: http://example.com "Title"'
    assert doc.elements[0].source_locator == {"line": 1}
    assert doc.elements[1].content == "para text"
    assert doc.elements[1].source_locator == {"line": 3}


def test_linkrefdef_with_use_merges_literal(tmp_path: Path):
    doc = _parse(tmp_path, "[ref]: http://example.com\nsee [ref] here\n")
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[0].content == "[ref]: http://example.com\nsee [ref] here"
    assert doc.elements[0].source_locator == {"line": 1}


def test_linkrefdef_adjacent_defs_and_title_line(tmp_path: Path):
    doc = _parse(tmp_path, "[a]: http://x/1\n[b]: http://x/2\n\npara\n")
    assert len(doc.elements) == 2
    assert doc.elements[0].content == "[a]: http://x/1\n[b]: http://x/2"
    assert doc.elements[0].source_locator == {"line": 1}
    assert doc.elements[1].content == "para"
    assert doc.elements[1].source_locator == {"line": 4}

    t = _parse(tmp_path, '[ref]: http://x\n"Title"\n\npara\n')
    assert t.elements[0].content == '[ref]: http://x\n"Title"'
    assert t.elements[1].content == "para"
    assert t.elements[1].source_locator == {"line": 4}
