r"""pipeline PDF 加密与文档级元数据（Round 1567）。

新角度：真实世界高频两类**文档级**形态零覆盖：

- **加密 PDF**（trailer /Encrypt + Standard handler）→
  结构化 pdfplumber_open_failed（exception_type=
  PdfminerException），doc=None 不崩溃
- **/Info（Title/Author）与 XMP /Metadata 流** → 对
  elements/chunks 完全中性（元数据不进输出）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")


def _pdf(tmp_path: Path, name: str,
         trailer_extra: str = "",
         catalog_extra: str = "",
         extra_objs=None) -> Path:
    content = ("BT /F1 12 Tf"
               " 72 700 Td"
               " (BODY) Tj ET")
    objs = {
        1: (f"<< /Type /Catalog"
            f" /Pages 2 0 R"
            f"{catalog_extra} >>"),
        2: "<< /Type /Pages"
           " /Kids [3 0 R]"
           " /Count 1 >>",
        3: ("<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox"
            " [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 5 0 R >> >>"
            " /Contents 4 0 R >>"),
        4: f"<< /Length {len(content)} >>"
           f"\nstream\n{content}\n"
           f"endstream",
        5: _FONT,
    }
    if extra_objs:
        objs.update(extra_objs)
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
            + str(len(objs) + 1).encode()
            + trailer_extra.encode()
            + b" >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def test_encrypted_pdf(tmp_path):
    p = _pdf(
        tmp_path, "enc.pdf",
        trailer_extra=" /Encrypt 6 0 R",
        extra_objs={
            6: ("<< /Filter /Standard"
                " /V 1 /R 2"
                " /O (((((((("
                " /U ))))))))"
                " /P -1 >>")})
    doc, errors = process_single(
        p, write_json=False)
    assert doc is None
    assert len(errors) == 1
    e = errors[0]
    assert e.code \
        == "pdfplumber_open_failed"
    assert e.details[
        "exception_type"] == \
        "PdfminerException"


def test_info_and_xmp_neutral(
        tmp_path):
    xmp = ('<?xpacket begin=""'
           ' id="W5M0MpCehiHzreSzNTczkc9d"?>'
           '<x:xmpmeta xmlns:x="adobe:ns:'
           'meta/"><rdf:RDF xmlns:rdf='
           '"http://www.w3.org/1999/02/'
           '22-rdf-syntax-ns#"/></x:xmpmeta>')
    p = _pdf(
        tmp_path, "meta.pdf",
        catalog_extra=" /Metadata 6 0 R",
        trailer_extra=" /Info 7 0 R",
        extra_objs={
            6: (f"<< /Length {len(xmp)} >>"
                f"\nstream\n{xmp}\n"
                f"endstream"),
            7: ("<< /Title (DocTitle)"
                " /Author (Someone)"
                " /Producer (Probe)"
                " >>")})
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "BODY")]
    assert [c.text
            for c in doc.chunks] == [
        "BODY"]
    assert "DocTitle" \
        not in doc.elements[0].content
