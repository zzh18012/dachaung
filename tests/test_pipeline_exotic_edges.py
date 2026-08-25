r"""app/pipeline 异形输入端到端测试（Round 1547）。

新角度（集成对照）：近期 40+ 轮锁定的**解析层**异形行
为（CID 占位符/千字号合并/零宽 bbox/超长段落）此前只
在 parser 层验证——本轮全量走 process_single（parse →
chunk → schema 校验）锁端到端不变量：

- **CID 占位符文本**：'(cid:16975)(cid:17497)' 原样进
  chunk、source_element_ids 非空、schema 通过
- **千字号吞并行**：'BIG SMALL' 单元素单 chunk
- **零宽 bbox（Tz 0）**：'ZERO' 照常、locator 带
  x1==x2 的 bbox 不违 schema
- **200 词段落**：split 成 2 chunk（≤max_chars）、
  normalize_text 语义下不丢不重、两 chunk 均有
  source_element_ids
"""

from __future__ import annotations

import re
from pathlib import Path

from app.pipeline import process_single

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")
_CID_FONT = (
    "<< /Type /Font"
    " /Subtype /Type0"
    " /BaseFont /T"
    " /Encoding /Identity-H"
    " /DescendantFonts"
    " [<< /Type /Font"
    " /Subtype /CIDFontType2"
    " /BaseFont /T"
    " /CIDSystemInfo"
    " << /Registry (Adobe)"
    " /Ordering (Identity)"
    " /Supplement 0 >>"
    " /DW 600 >>] >>")


def _pdf(tmp_path: Path, name: str,
         content: str,
         font: str = _FONT
         ) -> Path:
    objs = [
        "<< /Type /Catalog"
        " /Pages 2 0 R >>",
        "<< /Type /Pages"
        " /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page"
        " /Parent 2 0 R"
        " /MediaBox [0 0 612 792]"
        " /Resources << /Font"
        " << /F1 5 0 R >> >>"
        " /Contents 4 0 R >>",
        f"<< /Length {len(content)} >>"
        f"\nstream\n{content}\n"
        f"endstream",
        font,
    ]
    pdf = b"%PDF-1.4\n"
    for i, o in enumerate(objs):
        pdf += (f"{i + 1} 0 obj\n{o}"
                f"\nendobj\n"
                ).encode("latin-1")
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 6 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def test_cid_placeholders(tmp_path):
    p = _pdf(tmp_path, "cid.pdf",
             "BT /F1 12 Tf 72 700 Td"
             " (BODY) Tj ET",
             _CID_FONT)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert [e.content
            for e in doc.elements] == [
        "(cid:16975)(cid:17497)"]
    assert [c.text for c in
            doc.chunks] == [
        "(cid:16975)(cid:17497)"]
    assert doc.chunks[
        0].source_element_ids


def test_huge_font_merged(tmp_path):
    p = _pdf(tmp_path, "big.pdf",
             "BT /F1 1000 Tf 72 700 Td"
             " (BIG) Tj ET"
             " BT /F1 12 Tf 72 600 Td"
             " (SMALL) Tj ET")
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert [e.content
            for e in doc.elements] == [
        "BIG SMALL"]
    assert [c.text for c in
            doc.chunks] == ["BIG SMALL"]
    assert doc.chunks[
        0].source_element_ids


def test_zero_width_bbox(tmp_path):
    p = _pdf(tmp_path, "zero.pdf",
             "BT /F1 12 Tf 0 Tz 72 700"
             " Td (ZERO) Tj ET")
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox[0] == bbox[2]
    assert [c.text for c in
            doc.chunks] == ["ZERO"]


def test_long_paragraph_split(
        tmp_path):
    words = " ".join(
        f"word{i}"
        for i in range(200))
    p = _pdf(tmp_path, "long.pdf",
             f"BT /F1 12 Tf 72 700 Td"
             f" ({words}) Tj ET")
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert len(doc.chunks) == 2
    assert all(
        len(c.text) <= 800
        for c in doc.chunks)
    assert all(
        c.source_element_ids
        for c in doc.chunks)
    el_all = _normalize(
        doc.elements[0].content)
    ch_all = _normalize(
        " ".join(c.text
                 for c in doc.chunks))
    assert ch_all == el_all
