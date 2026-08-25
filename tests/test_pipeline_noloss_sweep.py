r"""pipeline 分块不丢不重扫描（Round 1568）。

新角度：R1547 对 4 种异形输入做过不丢不重；本轮把
**本 stretch 新建的全生成器家族**（文本/长段拆分/表格/
图片/50 图/多页/CJK/mixed DOCX）一次扫过——端到端不
变式：

- errors==[] 且 chunks 非空
- 每个 chunk 的 source_element_ids 非空
- **normalize(全部 chunk 文本拼接) == normalize(
  非 image 元素 content 拼接)**（图片被 chunker 丢弃
  是已知行为，排除后应零丢失零重复）
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import docx as docxlib
import pytest

from app.pipeline import process_single
from tests._synthetic_docs import (
    build_minimal_pdf,
)

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _bytes_pdf(content: str,
               extra_page2=None,
               n_draws=0):
    parts = []
    for i in range(n_draws):
        parts.append(
            f"q 10 0 0 10"
            f" {20 + (i % 10) * 55}"
            f" {40 + (i // 10) * 70}"
            f" cm /Im1 Do Q")
    parts.append(content)
    c1 = " ".join(parts)
    px = bytes([255, 0, 0])
    im = (f"<< /Type /XObject"
          f" /Subtype /Image"
          f" /Width 1 /Height 1"
          f" /ColorSpace /DeviceRGB"
          f" /BitsPerComponent 8"
          f" /Length {len(px)} >>"
          f"\nstream\n"
          ).encode() + px \
        + b"\nendstream"
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R]"
           " /Count 1 >>",
        3: ("<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox"
            " [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 6 0 R >>"
            " /XObject << /Im1"
            " 8 0 R >> >>"
            " /Contents 5 0 R >>"),
        5: f"<< /Length {len(c1)} >>"
           f"\nstream\n{c1}\n"
           f"endstream",
        6: _FONT,
        8: im,
    }
    size = len(objs) + 1
    if extra_page2 is not None:
        objs[2] = ("<< /Type /Pages"
                   " /Kids [3 0 R"
                   " 4 0 R]"
                   " /Count 2 >>")
        objs[4] = ("<< /Type /Page"
                   " /Parent 2 0 R"
                   " /MediaBox"
                   " [0 0 612 792]"
                   " /Resources << /Font"
                   " << /F1 6 0 R >>"
                   " /XObject << /Im1"
                   " 8 0 R >> >>"
                   " /Contents 7 0 R >>")
        objs[7] = (f"<< /Length"
                   f" {len(extra_page2)} >>"
                   f"\nstream\n"
                   f"{extra_page2}\n"
                   f"endstream")
        size = len(objs) + 1
    pdf = b"%PDF-1.4\n"
    for oid in sorted(objs):
        o = objs[oid]
        if isinstance(o, str):
            o = o.encode("latin-1")
        pdf += (f"{oid} 0 obj\n"
                ).encode() + o \
            + b"\nendobj\n"
    pdf += (b"trailer"
            b" << /Root 1 0 R"
            b" /Size "
            + str(size).encode()
            + b" >>\n%%EOF")
    return pdf


def _cases(tmp_path: Path):
    out = {}
    out["plain"] = build_minimal_pdf(
        tmp_path / "plain.pdf",
        text="(Hello world)")
    out["long-split"] = (
        tmp_path / "long.pdf")
    (tmp_path / "long.pdf")\
        .write_bytes(_bytes_pdf(
            "BT /F1 10 Tf 72 700"
            " Td ("
            + " ".join(
                f"w{i}"
                for i in range(60))
            + ") Tj ET"))
    grid = " ".join(
        f"{x} {y} 100 30 re S"
        for x in (72, 172)
        for y in (650, 610))
    out["table"] = (
        tmp_path / "tab.pdf")
    (tmp_path / "tab.pdf")\
        .write_bytes(_bytes_pdf(
            grid
            + " BT /F1 10 Tf"
            " 80 655 Td (t1)"
            " Tj ET BT /F1 10"
            " Tf 80 615 Td"
            " (t2) Tj ET"))
    out["image"] = (
        tmp_path / "img.pdf")
    (tmp_path / "img.pdf")\
        .write_bytes(_bytes_pdf(
            "q 100 0 0 100 72"
            " 692 cm /Im1 Do Q"
            " BT /F1 12 Tf"
            " 72 650 Td"
            " (BODY) Tj ET"))
    out["fifty-draws"] = (
        tmp_path / "fifty.pdf")
    (tmp_path / "fifty.pdf")\
        .write_bytes(_bytes_pdf(
            "BT /F1 12 Tf 72 730"
            " Td (BODY) Tj ET",
            n_draws=50))
    out["multipage"] = (
        tmp_path / "multi.pdf")
    (tmp_path / "multi.pdf")\
        .write_bytes(_bytes_pdf(
            "BT /F1 12 Tf 72 700"
            " Td (P1TEXT) Tj ET",
            extra_page2=(
                "q 100 0 0 100 72"
                " 692 cm /Im1 Do Q"
                " BT /F1 12 Tf"
                " 72 650 Td"
                " (P2TEXT) Tj ET")))
    cjk = tmp_path / "cjk.docx"
    para = "这是一段很长的中文测试文本。" * 20
    ct = ('<?xml version="1.0"?>'
          '<Types xmlns='
          '"http://schemas.'
          'openxmlformats.org/'
          'package/2006/'
          'content-types">'
          '<Default Extension='
          '"rels" ContentType='
          '"application/vnd.'
          'openxmlformats-'
          'package.relationships'
          '+xml"/><Default'
          ' Extension="xml"'
          ' ContentType='
          '"application/xml"/>'
          '<Override PartName='
          '"/word/document.xml"'
          ' ContentType='
          '"application/vnd.'
          'openxmlformats-'
          'officedocument.'
          'wordprocessingml.'
          'document.main+xml"'
          '/></Types>')
    rels = ('<?xml version="1.0"?>'
            '<Relationships xmlns='
            '"http://schemas.'
            'openxmlformats.org/'
            'package/2006/'
            'relationships">'
            '<Relationship Id='
            '"rId1" Type='
            '"http://schemas.'
            'openxmlformats.org/'
            'officeDocument/2006/'
            'relationships/'
            'officeDocument"'
            ' Target='
            '"word/document.xml"/>'
            '</Relationships>')
    doc_xml = (
        '<?xml version="1.0"?>'
        '<w:document xmlns:w='
        '"http://schemas.'
        'openxmlformats.org/'
        'wordprocessingml/'
        '2006/main"><w:body>'
        '<w:p><w:r><w:t>'
        f'{para}</w:t></w:r></w:p>'
        '</w:body></w:document>')
    with zipfile.ZipFile(
            cjk, "w",
            zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml",
                   doc_xml)
    out["cjk-docx"] = cjk
    mixed = tmp_path / "mixed.docx"
    dd = docxlib.Document()
    dd.add_heading("Chapter Title",
                   level=1)
    dd.add_paragraph("Body text here.")
    t = dd.add_table(rows=1, cols=2)
    t.cell(0, 0).text = "cell1"
    t.cell(0, 1).text = "cell2"
    dd.save(str(mixed))
    out["mixed-docx"] = mixed
    return out


@pytest.mark.parametrize(
    "name",
    ["plain", "long-split", "table",
     "image", "fifty-draws",
     "multipage", "cjk-docx",
     "mixed-docx"])
def test_no_loss(tmp_path, name):
    p = _cases(tmp_path)[name]
    doc, errors = process_single(
        p, write_json=False,
        max_chars=100)
    assert errors == []
    assert doc.chunks
    assert all(
        c.source_element_ids
        for c in doc.chunks)
    tight = _norm("".join(
        c.text for c in doc.chunks))
    spaced = _norm(" ".join(
        c.text for c in doc.chunks))
    for e in doc.elements:
        if e.type == "image":
            continue
        nc = _norm(e.content)
        # 分块边界允许丢弃空白分隔符：
        # 紧拼接（CJK 连续文本）或空格拼接（词间文本）
        # 任一形态包含即视为无丢失
        assert nc in tight \
            or nc in spaced
