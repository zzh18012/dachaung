"""解析器的单元测试。

策略：
- DOCX 用 stdlib 的 zipfile 合成最小测试文件（不需要真实样例）
- PDF 用 stdlib 字节流合成最小 PDF（不需要真实样例）
- Kreuzberg 用合成的 DOCX 验证它能调用（不强求 elements 完整性，因为已实测它给不出）
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from app.models import Document
from app.parsers import Parser, ParserError
from app.parsers.fallback_parser import FallbackParser
from app.parsers.kreuzberg_parser import KreuzbergParser


# ---------- helpers: 合成最小 DOCX ----------

def _build_minimal_docx(tmp_path: Path, with_table: bool = False) -> Path:
    """用 stdlib zipfile 构造一个最小 DOCX。"""
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    doc_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:pPr><w:outlineLvl w:val="1"/></w:pPr></w:style>
</w:styles>'''
    body_parts = [
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Chapter 1</w:t></w:r></w:p>',
        '<w:p><w:r><w:t>Sentence one. Sentence two.</w:t></w:r></w:p>',
    ]
    if with_table:
        body_parts.append(
            '<w:tbl>'
            '<w:tr><w:tc><w:p><w:r><w:t>A1</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>B1</w:t></w:r></w:p></w:tc></w:tr>'
            '<w:tr><w:tc><w:p><w:r><w:t>A2</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>B2</w:t></w:r></w:p></w:tc></w:tr>'
            '</w:tbl>'
        )
    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body>' + ''.join(body_parts) + '</w:body></w:document>'
    )
    path = tmp_path / "synthetic.docx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/document.xml", doc_xml)
    return path


# ---------- helpers: 合成最小 PDF ----------

def _build_minimal_pdf(tmp_path: Path, text: str = "Hello World Chapter 1") -> Path:
    objs = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    ]
    stream = b'BT /F1 24 Tf 100 700 Td (' + text.encode('latin-1') + b') Tj ET'
    objs.append(b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream')
    objs.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')

    pdf = b'%PDF-1.4\n'
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += f'{i} 0 obj\n'.encode() + body + b'\nendobj\n'
    xref_pos = len(pdf)
    n = len(objs) + 1
    pdf += b'xref\n' + f'0 {n}\n'.encode() + b'0000000000 65535 f \n'
    for off in offsets:
        pdf += f'{off:010d} 00000 n \n'.encode()
    pdf += b'trailer\n<< /Size ' + str(n).encode() + b' /Root 1 0 R >>\nstartxref\n'
    pdf += str(xref_pos).encode() + b'\n%%EOF'

    path = tmp_path / "synthetic.pdf"
    path.write_bytes(pdf)
    return path


# ---------- FallbackParser tests ----------

def test_fallback_docx_basic(tmp_path: Path):
    p = _build_minimal_docx(tmp_path)
    doc = FallbackParser().parse(p, source_hash="a" * 64)
    assert isinstance(doc, Document)
    assert doc.source_type == "docx"
    assert doc.parser_name == "fallback"
    # 合成的 DOCX 含 1 heading + 1 paragraph
    types = [e.type for e in doc.elements]
    assert "heading" in types
    assert types.count("paragraph") >= 1
    # DOCX source_locator 必须有 paragraph_index 或 table_index
    for e in doc.elements:
        assert "page" not in e.source_locator  # DOCX 不应有 page
        if e.type == "table":
            assert "table_index" in e.source_locator
        else:
            assert "paragraph_index" in e.source_locator


def test_fallback_docx_with_table(tmp_path: Path):
    p = _build_minimal_docx(tmp_path, with_table=True)
    doc = FallbackParser().parse(p, source_hash="b" * 64)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    t = tables[0]
    assert "A1" in t.content and "B2" in t.content
    assert t.source_locator.get("table_index") == 0


def test_fallback_pdf_basic(tmp_path: Path):
    p = _build_minimal_pdf(tmp_path, text="(Hello World Chapter 1)")
    # 用括号包文本避免 PDF 解析问题
    doc = FallbackParser().parse(p, source_hash="c" * 64)
    assert doc.source_type == "pdf"
    # PDF 必须有 page（≥1）
    for e in doc.elements:
        assert e.source_locator.get("page", 0) >= 1
        # bbox 必须是 4 个数字（如果有）
        if "bbox" in e.source_locator:
            assert len(e.source_locator["bbox"]) == 4


def test_fallback_missing_file_raises(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(tmp_path / "nope.docx", source_hash="d" * 64)
    assert exc.value.code == "file_not_found"


def test_fallback_unsupported_extension(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello")
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(p, source_hash="e" * 64)
    assert exc.value.code == "unsupported_type"


# ---------- KreuzbergParser tests ----------

def test_kreuzberg_docx_returns_document_with_warning(tmp_path: Path):
    """Kreuzberg 实测对 DOCX 给不出 elements，必须产生 kreuzberg_no_structured_elements warning。"""
    p = _build_minimal_docx(tmp_path)
    doc = KreuzbergParser().parse(p, source_hash="f" * 64)
    assert doc.source_type == "docx"
    assert doc.parser_name == "kreuzberg"
    warning_codes = [w.code for w in doc.warnings]
    assert "kreuzberg_no_structured_elements" in warning_codes


def test_kreuzberg_pdf_has_no_bbox_warning(tmp_path: Path):
    p = _build_minimal_pdf(tmp_path, text="(Hi)")
    doc = KreuzbergParser().parse(p, source_hash="10" * 32)
    warning_codes = [w.code for w in doc.warnings]
    assert "kreuzberg_pdf_no_bbox" in warning_codes
    # 占位 page=1
    for e in doc.elements:
        if doc.source_type == "pdf":
            assert e.source_locator.get("page") == 1


def test_kreuzberg_missing_file_raises(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        KreuzbergParser().parse(tmp_path / "nope.pdf", source_hash="1" * 64)
    assert exc.value.code == "file_not_found"


# ---------- 接口契约 ----------

def test_parser_interface_contract():
    """Parser 抽象类不能直接实例化。"""
    with pytest.raises(TypeError):
        Parser()  # type: ignore[abstract]


def test_parsers_have_name_and_version():
    for parser_cls in (FallbackParser, KreuzbergParser):
        instance = parser_cls()
        assert isinstance(instance.name, str) and instance.name
        assert isinstance(instance.version, str) and instance.version
