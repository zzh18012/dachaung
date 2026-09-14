r"""md splitlines 分隔符族与 text 保真对照测试（Round 1842）。

新角度（probe 实证，grep 核实 md 测试对 0x0c/0x0b/U+2028 零覆盖）：
markdown_parser 用 text.splitlines()（152 行）——除 \n 外
\x0c/\x0b/ /\x85/\x1c 也都当换行；text 家族只按 \n 切段：
- md **Unicode 行分隔符全部归一为 \n**：'para a' + 分隔符 + 'para b'
  → 单个 paragraph，content 内分隔符消失、变 \n（五分隔符同型）
- md **分隔符是块级真换行**：'x' + U+2028 + '# Title' → paragraph 'x'
  + heading 'Title'——分隔符后可起 ATX 标题（不只是行内换行）
- text **\x0c/\x0b 原样保留**：'before \x0c after' content 保 form
  feed；行中 \x0c 不切段（text 只按 \n 切，\x0c 仅算行内空白字符）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.markdown_parser import MarkdownParser
from app.parsers.text_parser import TextParser

FF = chr(0x0C)
VT = chr(0x0B)
U2028 = chr(0x2028)
NEL = chr(0x85)
FS = chr(0x1C)


def _md(tmp_path: Path, text: str):
    p = tmp_path / "md_r1842.md"
    p.write_text(text, encoding="utf-8", newline="")
    return MarkdownParser().parse(p, compute_file_hash(p))


def _text(tmp_path: Path, text: str):
    p = tmp_path / "r1842.txt"
    p.write_text(text, encoding="utf-8", newline="")
    return TextParser().parse(p, compute_file_hash(p))


def test_md_unicode_line_separators_become_newlines(tmp_path: Path):
    for sep in (FF, VT, U2028, NEL, FS):
        doc = _md(tmp_path, "para a" + sep + "para b\n")
        assert len(doc.elements) == 1, repr(sep)
        e = doc.elements[0]
        assert e.type == "paragraph"
        assert e.content == "para a\npara b", repr(sep)
        assert sep not in e.content


def test_md_unicode_separator_enables_heading(tmp_path: Path):
    doc = _md(tmp_path, "x" + U2028 + "# Title\n")
    assert len(doc.elements) == 2
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[0].content == "x"
    assert doc.elements[1].type == "heading"
    assert doc.elements[1].content == "Title"

    ff = _md(tmp_path, "lead" + FF + "## Sub\n").elements
    assert len(ff) == 2
    assert ff[0].content == "lead"
    assert ff[1].type == "heading"
    assert ff[1].content == "Sub"


def test_text_ff_vt_preserved_verbatim(tmp_path: Path):
    doc = _text(tmp_path, "before " + FF + " after\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "before " + FF + " after"

    vt = _text(tmp_path, "before " + VT + " after\n").elements[0]
    assert vt.content == "before " + VT + " after"

    nosplit = _text(tmp_path, "ws only" + FF + "line\n" + FF + "next\n")
    assert len(nosplit.elements) == 1
    assert nosplit.elements[0].content == "ws only" + FF + "line\n" + FF + "next"
