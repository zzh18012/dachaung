r"""app/parsers_fallback PDF 边角测试 - 第一百一十三轮（Round 1543）。

新角度（probe 实证）文件头/尾变体（R1530 垃圾家族测
过整体垃圾；本轮是**头部前后缀与尾部 %%EOF 的边界**
——零覆盖）：

- **%PDF-2.0 版本号** → 照常
- **头部前有垃圾字节**（\xde\xad\xbe\xef junk\n + 正常
  PDF）→ 照常（头定位允许前缀垃圾）
- **完全无 %PDF 版本行** → 照常（trailer 驱动的扫描不
  需要头）
- **⚠ 缺失尾部 %%EOF** → ParserError 'No /Root
  object!'——%%EOF 是结构定位的**必需**锚点（有
  trailer 也不行）
- **⚠ %%EOF 之后有垃圾** → 同样 ParserError——pdfminer
  要求 %%EOF 在文件末尾（规范允许尾部垃圾，实现拒绝）
- **二进制标记注释行**（%\xe2\xe3\xcf\xd3——规范推荐
  的二进制指示注释）→ 照常
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.base import ParserError
from app.parsers.fallback_parser import \
    FallbackParser

_C = "BT /F1 12 Tf 72 700 Td (BODY) Tj ET"


def _assemble(
        header: bytes = b"%PDF-1.4\n",
        footer: bytes = (b"trailer << /Root 1 0 R"
                         b" /Size 6 >>\n%%EOF")
        ) -> bytes:
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
        f"<< /Length {len(_C)} >>"
        f"\nstream\n{_C}\nendstream",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding"
        " /WinAnsiEncoding >>",
    ]
    pdf = header
    for i, o in enumerate(objs):
        pdf += (f"{i + 1} 0 obj\n{o}"
                f"\nendobj\n"
                ).encode("latin-1")
    return pdf + footer


def _ok(tmp_path, name, pdf):
    p = tmp_path / name
    p.write_bytes(pdf)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == ["BODY"]
    assert doc.warnings == []


def _err(tmp_path, name, pdf):
    p = tmp_path / name
    p.write_bytes(pdf)
    with pytest.raises(ParserError) as ei:
        FallbackParser().parse(
            p, compute_file_hash(p))
    assert "pdfplumber 打开/解析" \
        " PDF 失败" in str(ei.value)
    assert "No /Root object!" in str(ei.value)


def test_version_2_0(tmp_path):
    _ok(tmp_path, "v20.pdf",
        _assemble(b"%PDF-2.0\n"))


def test_junk_before_header(
        tmp_path):
    _ok(tmp_path, "junkpre.pdf",
        b"\xde\xad\xbe\xef junk"
        b" bytes\n" + _assemble())


def test_no_version_line(tmp_path):
    _ok(tmp_path, "noversion.pdf",
        _assemble(b""))


def test_missing_eof_marker(
        tmp_path):
    _err(tmp_path, "noeof.pdf",
         _assemble(
             footer=b"trailer << /Root"
                    b" 1 0 R /Size 6 >>"))


def test_junk_after_eof(tmp_path):
    _err(tmp_path, "junkpost.pdf",
         _assemble() + b"\ngarbage"
                       b" after eof 12345")


def test_binary_comment(tmp_path):
    _ok(tmp_path, "bincomment.pdf",
        b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        + _assemble()[9:])
