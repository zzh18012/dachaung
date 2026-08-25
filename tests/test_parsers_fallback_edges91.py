r"""app/parsers/fallback_parser.py PDF 边角测试 - 第九十一轮（Round 1521）。

新角度（probe 实证）加密 PDF 表面与损坏图像数据（此前
轮次零 /Encrypt 覆盖）：

- **⚠ 标准 V1/R2 加密 → ParserError**：trailer 挂
  /Encrypt（空密码校验失败）→ 抛 ParserError（'pdfplumber
  打开/解析 PDF 失败: ...'——结构化错误而非警告）
- **DCTDecode 垃圾数据不影响提取**：/Filter /DCTDecode
  流塞非 JPEG 字节 → 照常提取 TEXT + image 元素照发
  （content=None）、零警告（图像数据从不解码）
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.base import ParserError
from app.parsers.fallback_parser import \
    FallbackParser

from tests.test_parsers_fallback_edges66 \
    import _pdf


def test_encrypted_pdf_raises(
        tmp_path):
    p = _pdf(
        tmp_path, "enc.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (SECRET) Tj ET")
    raw = p.read_bytes().decode("latin-1")
    enc = ("7 0 obj"
           " << /Filter /Standard"
           " /V 1 /R 2"
           " /O (0123456789012345"
           "6789012345678901)"
           " /U (abcdefghijklmnop"
           "qrstuvwxyz012345)"
           " /P -1 >> endobj\n")
    raw = raw.replace(
        "trailer", enc + "trailer")
    raw = raw.replace(
        "/Root 1 0 R",
        "/Root 1 0 R"
        " /Encrypt 7 0 R")
    p.write_bytes(raw.encode("latin-1"))
    with pytest.raises(ParserError) as ei:
        FallbackParser().parse(
            p, compute_file_hash(p))
    assert "pdfplumber 打开/解析" \
        " PDF 失败" in str(ei.value)


def test_malformed_jpeg_tolerated(
        tmp_path):
    jpg = (b"\xff\xd8\xff\xe0"
           b"GARBAGENOTAJPEG"
           b"\xff\xd9")
    content = (
        "BT /F1 12 Tf 72 700 Td"
        " (TEXT) Tj ET"
        " q 100 0 0 100 200 200"
        " cm /Im1 Do Q")
    objs = [
        "<< /Type /Catalog"
        " /Pages 2 0 R >>",
        "<< /Type /Pages"
        " /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page"
        " /Parent 2 0 R"
        " /MediaBox [0 0 612 792]"
        " /Resources << /Font"
        " << /F1 5 0 R >> /XObject"
        " << /Im1 6 0 R >> >>"
        " /Contents 4 0 R >>",
        f"<< /Length {len(content)} >>"
        f"\nstream\n{content}"
        f"\nendstream",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding"
        " /WinAnsiEncoding >>",
        f"<< /Type /XObject"
        f" /Subtype /Image"
        f" /Width 5 /Height 5"
        f" /ColorSpace /DeviceRGB"
        f" /BitsPerComponent 8"
        f" /Filter /DCTDecode"
        f" /Length {len(jpg)} >>"
        f"\nstream\n"
        .encode("latin-1") + jpg
        + b"\nendstream",
    ]
    pdf = b"%PDF-1.4\n" + b"".join(
        f"{i + 1} 0 obj\n".encode("latin-1")
        + (o.encode("latin-1")
           if isinstance(o, str) else o)
        + b"\nendobj\n"
        for i, o in enumerate(objs))
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 7 >>\n%%EOF")
    p = tmp_path / "badjpg.pdf"
    p.write_bytes(pdf)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [(e.content, e.type)
            for e in doc.elements] == [
        ("TEXT", "heading"),
        (None, "image")]
    assert doc.warnings == []
