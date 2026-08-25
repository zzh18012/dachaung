r"""app/parsers_fallback PDF 边角测试 - 第一百零三轮（Round 1533）。

新角度（probe 实证）线性化布局 / 前向 /Prev 链（R1532
锁的是经典**向后** /Prev；真实线性化 PDF 的结构是
startxref 指向**文件头部**的首页 xref，其 trailer 带
/Root 且 /Prev **指向前方**（更高偏移）的文件尾主 xref
——此前零覆盖）：

- **完整线性化布局**（首页 xref 全量 + 尾部 free-only
  0 1 小节）→ 正常提取 'BODY'（pdfminer 沿 /Prev 不分
  方向）
- **真首页切分**：首页 xref 仅 1-4（obj5 free），尾部
  小节 5 1 更新 obj5 → 正常——跨段对象解析成功
- **/Prev 自指**（= 自身 xref 偏移）→ ParserError
  'maximum recursion depth exceeded'（无限链被 Python
  递归上限截断后由 parser 捕获，**不挂起**）
- **/Prev=99999 越界** → 正常（回退扫描救援）
- **/Prev=0** → 正常（同样救援）
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.base import ParserError
from app.parsers.fallback_parser import \
    FallbackParser

_C = "BT /F1 12 Tf 72 700 Td (BODY) Tj ET"
_O = {
    1: b"<< /Type /Catalog /Pages 2 0 R >>",
    2: b"<< /Type /Pages /Kids [3 0 R]"
       b" /Count 1 >>",
    3: (b"<< /Type /Page /Parent 2 0 R"
        b" /MediaBox [0 0 612 792]"
        b" /Resources << /Font"
        b" << /F1 5 0 R >> >>"
        b" /Contents 4 0 R >>"),
    4: (f"<< /Length {len(_C)} >>"
        f"\nstream\n{_C}\nendstream"
        ).encode("latin-1"),
    5: b"<< /Type /Font /Subtype /Type1"
       b" /BaseFont /Helvetica"
       b" /Encoding /WinAnsiEncoding >>",
}


def _linearized(split_5: bool) -> bytes:
    pdf = b"%PDF-1.4\n"
    offs = {}
    for i in sorted(_O):
        offs[i] = len(pdf)
        pdf += (f"{i} 0 obj\n".encode("latin-1")
                + _O[i] + b"\nendobj\n")
    x1 = len(pdf)
    if split_5:
        pdf += b"xref\n0 5\n0000000000 65535 f \n"
        for i in range(1, 5):
            pdf += (f"{offs[i]:010d} 00000 n \n"
                    .encode("latin-1"))
    else:
        pdf += b"xref\n0 6\n0000000000 65535 f \n"
        for i in range(1, 6):
            pdf += (f"{offs[i]:010d} 00000 n \n"
                    .encode("latin-1"))
    pdf += b"@TRAILER@\n%%EOF\n"
    x2 = len(pdf)
    if split_5:
        pdf += (b"xref\n5 1\n"
                + f"{offs[5]:010d} 00000 n \n"
                .encode("latin-1"))
    else:
        pdf += b"xref\n0 1\n" \
               b"0000000000 65535 f \n"
    pdf += b"trailer << /Size 6 >>\n%%EOF\n"
    pdf = pdf.replace(
        b"@TRAILER@",
        b"trailer << /Size 6 /Root 1 0 R"
        b" /Prev " + str(x2).encode() + b" >>")
    pdf += (b"startxref\n" + str(x1).encode()
            + b"\n%%EOF")
    return pdf


def _prev_kind(prev: str) -> bytes:
    pdf = b"%PDF-1.4\n"
    offs = {}
    for i in sorted(_O):
        offs[i] = len(pdf)
        pdf += (f"{i} 0 obj\n".encode("latin-1")
                + _O[i] + b"\nendobj\n")
    x = len(pdf)
    pdf += b"xref\n0 6\n0000000000 65535 f \n"
    for i in range(1, 6):
        pdf += (f"{offs[i]:010d} 00000 n \n"
                .encode("latin-1"))
    p = {"self": x, "bogus": 99999,
         "zero": 0}[prev]
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 6 /Prev "
            + str(p).encode() + b" >>\n")
    pdf += (b"startxref\n" + str(x).encode()
            + b"\n%%EOF")
    return pdf


def _write(tmp_path: Path, name: str,
           pdf: bytes) -> Path:
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def _ok(p: Path):
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == ["BODY"]
    assert doc.warnings == []


def test_linearized_full(tmp_path):
    _ok(_write(tmp_path, "lin.pdf",
               _linearized(False)))


def test_linearized_split(tmp_path):
    _ok(_write(tmp_path, "linsplit.pdf",
               _linearized(True)))


def test_prev_self_loop(tmp_path):
    p = _write(tmp_path, "selfloop.pdf",
               _prev_kind("self"))
    with pytest.raises(ParserError) as ei:
        FallbackParser().parse(
            p, compute_file_hash(p))
    assert "pdfplumber 打开/解析" \
        " PDF 失败" in str(ei.value)
    assert "maximum recursion depth" \
        " exceeded" in str(ei.value)


def test_prev_bogus_offset(tmp_path):
    _ok(_write(tmp_path, "prevbogus.pdf",
               _prev_kind("bogus")))


def test_prev_zero(tmp_path):
    _ok(_write(tmp_path, "prevzero.pdf",
               _prev_kind("zero")))
