r"""自动链接/style 属性/表格 tab 单元格边角测试（Round 1839）。

新角度（probe 实证），三家族均零覆盖：
- md **裸 www / 裸 https URL 不做自动链接**：'visit
  www.example.com now' 与 'see https://example.com ok' 都是
  普通段落字面（R1833 只锁了尖括号 <autolink> 形态——那也是
  字面；裸 URL 更不转换，无 link 元数据）
- html **style 属性被忽略**：<p style="color:red">styled</p> →
  paragraph 'styled'，无 style 相关 metadata（装饰属性全弃，
  与 start/type 属性同哲学）
- md **表格单元格内 hard tab 不当分隔符**：只按竖线切列，
  'a\\tb' 整格保留 tab 字符；element content 是整段原文
  （含分隔行），row_count=2/col_count=2
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser
from app.parsers.markdown_parser import MarkdownParser


def _md(tmp_path: Path, text: str):
    p = tmp_path / "md_r1839.md"
    p.write_text(text, encoding="utf-8", newline="")
    return MarkdownParser().parse(p, compute_file_hash(p))


def _html(tmp_path: Path, text: str):
    p = tmp_path / "r1839.html"
    p.write_text(text, encoding="utf-8", newline="")
    return HtmlParser().parse(p, compute_file_hash(p))


def test_md_bare_www_and_url_stay_plain(tmp_path: Path):
    doc = _md(tmp_path, "visit www.example.com now\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "visit www.example.com now"
    assert e.metadata == {}

    url = _md(tmp_path, "see https://example.com ok\n").elements[0]
    assert url.type == "paragraph"
    assert url.content == "see https://example.com ok"


def test_html_style_attribute_ignored(tmp_path: Path):
    doc = _html(tmp_path, '<p style="color:red">styled</p>')
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "styled"
    assert e.metadata == {}

    cell = _html(tmp_path, '<td style="x">cell</td>').elements[0]
    assert cell.content == "cell"
    assert cell.metadata == {}


def test_md_table_cell_tab_not_separator(tmp_path: Path):
    doc = _md(tmp_path, "| a\tb | c |\n| --- | --- |\n| 1\t2 | 3 |\n")
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    t = tables[0]
    assert t.metadata == {
        "row_count": 2,
        "col_count": 2,
        "source": "markdown_pipe_table",
    }
    assert "\t" in t.content
    lines = t.content.split("\n")
    assert lines[0] == "| a\tb | c |"
    assert lines[2] == "| 1\t2 | 3 |"
