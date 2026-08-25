r"""app/parsers/fallback_parser.py DOCX 边角测试 - 第七十轮（Round 1493）。

新角度（probe 实证）表格嵌套/多段 cell/悬空关系（edges1-69
未碰）：

- **⚠ 嵌套 w:tbl 整表丢弃**：外层 cell 含 w:p + 内层表
  → 只留外层 cell 文本 '| outer | side |'，内层 i1/i2
  静默丢失（python-docx cell paragraphs 不含嵌套表）
- **多段 cell 以 \\n 连接**：同 tc 两个 w:p → cell 文本
  'line1\\nline2'
- **悬空 hyperlink r:id 无害**：r:id 不在 rels → 文本照
  常保留 'see link'（不崩、不告警）
- **空 tc 产空 cell**：空字符串照常成格 '| a |  |'
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

from tests.test_parsers_fallback_edges65 \
    import _build_docx

_INNER = (
    "<w:tbl><w:tr>"
    "<w:tc><w:p><w:r><w:t>i1</w:t>"
    "</w:r></w:p></w:tc>"
    "<w:tc><w:p><w:r><w:t>i2</w:t>"
    "</w:r></w:p></w:tc>"
    "</w:tr></w:tbl>")


def _parse(tmp_path, name, px):
    p = tmp_path / name
    p.write_bytes(_build_docx(px))
    return FallbackParser().parse(
        p, compute_file_hash(p))


def test_nested_tbl_dropped(tmp_path):
    doc = _parse(
        tmp_path, "nt.docx",
        "<w:tbl><w:tr>"
        "<w:tc><w:p><w:r><w:t>outer"
        "</w:t></w:r></w:p>" + _INNER
        + "</w:tc><w:tc><w:p><w:r>"
          "<w:t>side</w:t></w:r></w:p>"
          "</w:tc></w:tr></w:tbl>")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "table"
    assert e.content == \
        "| outer | side |\n" \
        "| --- | --- |"
    assert e.metadata == {
        "row_count": 1,
        "col_count": 2,
        "source": "python-docx",
    }
    assert doc.warnings == []


def test_multi_para_cell_newline_join(
        tmp_path):
    doc = _parse(
        tmp_path, "mp.docx",
        "<w:tbl><w:tr>"
        "<w:tc><w:p><w:r><w:t>line1"
        "</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>line2</w:t>"
        "</w:r></w:p></w:tc>"
        "</w:tr></w:tbl>")
    assert [e.content
            for e in doc.elements] == [
        "| line1\nline2 |\n| --- |",
    ]
    assert doc.elements[0].metadata == {
        "row_count": 1,
        "col_count": 1,
        "source": "python-docx",
    }


def test_dangling_hyperlink_harmless(
        tmp_path):
    doc = _parse(
        tmp_path, "dh.docx",
        "<w:p><w:r><w:t>see </w:t></w:r>"
        '<w:hyperlink r:id="rId99">'
        "<w:r><w:t>link</w:t></w:r>"
        "</w:hyperlink></w:p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "see link"),
    ]
    assert doc.warnings == []


def test_empty_tc_empty_cell(
        tmp_path):
    doc = _parse(
        tmp_path, "et.docx",
        "<w:tbl><w:tr>"
        "<w:tc><w:p><w:r><w:t>a</w:t>"
        "</w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t></w:t>"
        "</w:r></w:p></w:tc>"
        "</w:tr></w:tbl>")
    assert [e.content
            for e in doc.elements] == [
        "| a |  |\n| --- | --- |",
    ]
    assert doc.warnings == []
