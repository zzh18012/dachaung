r"""app/parsers 有序标记语法族边角测试（Round 1838）。

新角度（probe 实证）——_ORDERED_LIST_RE 只认数字（^\d+[.)]\s+），
字母/罗马标记从未覆盖；html ol 的 type 属性同样未覆盖：
- md 字母标记 'a. alpha' / 'A. Beta' → paragraph 字面保留
  （标记不剥离、无 list_item）；连续多行字母标记行**合并为
  一个段落**且换行保留（'a. alpha\\nb. beta'）
- md 罗马标记 'i. first' / 'iv. fourth' → 同样 paragraph 字面
  （大小写罗马都不触发有序列表）
- html <ol type="a"> / type="I" → list_item + {'ordered': True,
  'marker': 'ordered'}，**type 属性被忽略**（与 start 属性
  R1642 一致），内容不含标记
- text 家族 'a. line one' → paragraph 字面（家族分工对照：
  三家族对字母标记全部不识别，只有 html ol 显式结构里才有序）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser
from app.parsers.markdown_parser import MarkdownParser
from app.parsers.text_parser import TextParser


def _md(tmp_path: Path, text: str):
    p = tmp_path / "md_r1838.md"
    p.write_text(text, encoding="utf-8", newline="")
    return MarkdownParser().parse(p, compute_file_hash(p))


def _html(tmp_path: Path, text: str):
    p = tmp_path / "r1838.html"
    p.write_text(text, encoding="utf-8", newline="")
    return HtmlParser().parse(p, compute_file_hash(p))


def _text(tmp_path: Path, text: str):
    p = tmp_path / "r1838.txt"
    p.write_text(text, encoding="utf-8", newline="")
    return TextParser().parse(p, compute_file_hash(p))


def test_md_letter_markers_literal_paragraph(tmp_path: Path):
    doc = _md(tmp_path, "a. alpha\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "a. alpha"
    assert e.metadata == {}

    upper = _md(tmp_path, "A. Beta\n").elements[0]
    assert upper.type == "paragraph"
    assert upper.content == "A. Beta"

    merged = _md(tmp_path, "a. alpha\nb. beta\n")
    assert len(merged.elements) == 1
    assert merged.elements[0].content == "a. alpha\nb. beta"


def test_md_roman_markers_literal_paragraph(tmp_path: Path):
    doc = _md(tmp_path, "i. first\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "i. first"
    assert e.metadata == {}

    upper = _md(tmp_path, "iv. fourth\n").elements[0]
    assert upper.type == "paragraph"
    assert upper.content == "iv. fourth"


def test_html_ol_type_attribute_ignored(tmp_path: Path):
    doc = _html(
        tmp_path, '<ol type="a"><li>x</li><li>y</li></ol>')
    assert len(doc.elements) == 2
    for e in doc.elements:
        assert e.type == "list_item"
        assert e.metadata == {"ordered": True, "marker": "ordered"}

    upper = _html(
        tmp_path, '<ol type="I"><li>x</li></ol>').elements[0]
    assert upper.metadata == {"ordered": True, "marker": "ordered"}
    assert upper.content == "x"

    txt = _text(tmp_path, "a. line one\n").elements[0]
    assert txt.type == "paragraph"
    assert txt.content == "a. line one"
