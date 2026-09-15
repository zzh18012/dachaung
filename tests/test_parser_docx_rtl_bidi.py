r"""DOCX RTL（bidiVisual 表 / w:bidi 节 / w:rtl run）——全部忽略（Round 1971，a 优先级）。

阿拉伯/希伯来文档与部分排版工具产物；广扫 bidiVisual/
w:bidi/w:rtl 零匹配。探针 R1971 实证（python-docx 全按文
档序、视觉反转**不应用**）：

- **R1 bidiVisual 表**（3 列填 1/2/3）→ md 文档序
  '| 1 | 2 | 3 |'——视觉列反转不发生
- **R2 w:bidi 节** + 两段 → 段序 0/1、文本逐字不变
- **R3 run 级 w:rtl** → 'LTR part RTL RUN TEXT' 文档序拼
  接、不反转、零告警

判别式：若实现 bidiVisual 视觉重排则 R1 变 '| 3 | 2 | 1 |'
翻红；若 run 反转则 R3 变 'LTR part TXET NUR TLR' 翻红。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _parse(kind: str):
    d = Document()
    if kind == "table":
        t = d.add_table(rows=1, cols=3)
        for i, v in enumerate(("1", "2", "3")):
            t.rows[0].cells[i].text = v
        t._tbl.tblPr.append(parse_xml(f'<w:bidiVisual {nsdecls("w")}/>'))
    elif kind == "section":
        d.sections[-1]._sectPr.append(parse_xml(f'<w:bidi {nsdecls("w")}/>'))
        d.add_paragraph("first paragraph")
        d.add_paragraph("second paragraph")
    else:  # run
        p = d.add_paragraph()
        p.add_run("LTR part ")
        p._p.append(parse_xml(
            f'<w:r {nsdecls("w")}><w:rPr><w:rtl/></w:rPr>'
            f'<w:t>RTL RUN TEXT</w:t></w:r>'))
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "r.docx"
        d.save(p)
        return FallbackParser().parse(p, compute_file_hash(p))


def test_bidivisual_table_document_order():
    """R1：bidiVisual 表 → md 文档序 '| 1 | 2 | 3 |'、零告警。"""
    d = _parse("table")
    assert [e.type for e in d.elements] == ["table"]
    assert d.elements[0].content == "| 1 | 2 | 3 |\n| --- | --- | --- |"
    assert d.warnings == []


def test_bidi_section_paragraph_order_unchanged():
    """R2：w:bidi 节 → 段序 0/1、文本逐字不变。"""
    d = _parse("section")
    assert [(e.source_locator["paragraph_index"], e.content)
            for e in d.elements] == [(0, "first paragraph"), (1, "second paragraph")]
    assert d.warnings == []


def test_rtl_run_verbatim_document_order():
    """R3：w:rtl run → 'LTR part RTL RUN TEXT' 拼接不反转。"""
    d = _parse("run")
    assert [e.type for e in d.elements] == ["paragraph"]
    assert d.elements[0].content == "LTR part RTL RUN TEXT"
    assert d.warnings == []
