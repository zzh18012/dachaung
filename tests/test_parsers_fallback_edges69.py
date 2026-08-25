r"""app/parsers/fallback_parser.py DOCX 边角测试 - 第六十九轮（Round 1492）。

新角度（probe 实证）结构语义来源与合并单元格（edges1-68
未碰；w:br/Title 已由 edges24/edges10 覆盖）：

- **w:outlineLvl 被忽略**：导航窗格大纲级别（含带自定义
  style 的组合）不成标题 → 普通 paragraph（Word 语义中
  是标题，结构静默丢失）
- **w:numPr 被忽略**：编号/项目符号段落不成 list_item，
  无 marker 元数据 → 普通 paragraph（列表结构静默丢失）
- **vMerge 续行复制文本**：垂直合并的续行 cell 复读首行
  文本 → '| merged | r2 |'（python-docx 逐 tc 读文本）
- **gridSpan 复制文本**：横向跨列 cell 文本在两列重复
  → '| wide | wide |'
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

from tests.test_parsers_fallback_edges65 \
    import _build_docx


def _parse(tmp_path, name, px):
    p = tmp_path / name
    p.write_bytes(_build_docx(px))
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- 结构语义来源 ----------

def test_outline_lvl_not_heading(
        tmp_path):
    doc = _parse(
        tmp_path, "ol.docx",
        "<w:p><w:pPr>"
        '<w:outlineLvl w:val="1"/>'
        "</w:pPr><w:r><w:t>outline"
        " heading</w:t></w:r></w:p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "outline heading"),
    ]
    assert doc.elements[0].metadata == {
        "level": 0, "style": None,
        "empty": False,
    }
    assert doc.warnings == []


def test_outline_lvl_with_style_not_heading(
        tmp_path):
    doc = _parse(
        tmp_path, "ols.docx",
        "<w:p><w:pPr>"
        '<w:pStyle w:val="MyStyle"/>'
        '<w:outlineLvl w:val="2"/>'
        "</w:pPr><w:r><w:t>styled"
        " outline</w:t></w:r></w:p>")
    assert [(e.type, e.type)
            for e in doc.elements] == [
        ("paragraph", "paragraph"),
    ]
    assert doc.warnings == []


def test_numpr_not_list_item(
        tmp_path):
    doc = _parse(
        tmp_path, "np.docx",
        "<w:p><w:pPr><w:numPr>"
        '<w:ilvl w:val="0"/>'
        '<w:numId w:val="1"/>'
        "</w:numPr></w:pPr><w:r>"
        "<w:t>item one</w:t></w:r></w:p>"
        "<w:p><w:pPr><w:numPr>"
        '<w:ilvl w:val="1"/>'
        '<w:numId w:val="1"/>'
        "</w:numPr></w:pPr><w:r>"
        "<w:t>nested item</w:t>"
        "</w:r></w:p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "item one"),
        ("paragraph", "nested item"),
    ]
    assert all(
        "marker" not in e.metadata
        for e in doc.elements)
    assert doc.warnings == []


# ---------- 合并单元格 ----------

def test_vmerge_continuation_duplicates(
        tmp_path):
    doc = _parse(
        tmp_path, "vm.docx",
        "<w:tbl><w:tr>"
        "<w:tc><w:tcPr>"
        '<w:vMerge w:val="restart"/>'
        "</w:tcPr><w:p><w:r>"
        "<w:t>merged</w:t></w:r>"
        "</w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>r1"
        "</w:t></w:r></w:p></w:tc>"
        "</w:tr><w:tr>"
        "<w:tc><w:tcPr><w:vMerge/>"
        "</w:tcPr><w:p><w:r><w:t>"
        "</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>r2"
        "</w:t></w:r></w:p></w:tc>"
        "</w:tr></w:tbl>")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "table"
    assert e.content == \
        "| merged | r1 |\n" \
        "| --- | --- |\n" \
        "| merged | r2 |"
    assert e.metadata == {
        "row_count": 2,
        "col_count": 2,
        "source": "python-docx",
    }


def test_gridspan_duplicates_text(
        tmp_path):
    doc = _parse(
        tmp_path, "gs.docx",
        "<w:tbl><w:tr>"
        "<w:tc><w:tcPr>"
        '<w:gridSpan w:val="2"/>'
        "</w:tcPr><w:p><w:r>"
        "<w:t>wide</w:t></w:r>"
        "</w:p></w:tc></w:tr>"
        "<w:tr>"
        "<w:tc><w:p><w:r><w:t>c1"
        "</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>c2"
        "</w:t></w:r></w:p></w:tc>"
        "</w:tr></w:tbl>")
    assert [e.content
            for e in doc.elements] == [
        "| wide | wide |\n"
        "| --- | --- |\n"
        "| c1 | c2 |",
    ]
    assert doc.warnings == []
