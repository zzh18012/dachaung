r"""app/parsers_fallback PDF 边角测试 - 第一百零二轮（Round 1532）。

新角度（probe 实证）经典 xref 表 / startxref 家族（此前
100+ 轮的最小 PDF 全部**无 xref 表**——纯 trailer 扫描模
式；xref 流（R1524）之后，经典 xref + startxref + /Prev
链零覆盖）：

结构解析：
- **正经经典 xref + 正确 startxref** → 正常提取（对照）
- **/Prev 链（startxref 指向末段）**：obj5 前段 free、
  末段 in-use 更新 → 正常（向后链解析成功）
- **/Root 只在前方段**：startxref 指向前段（其 trailer
  无 /Root）→ ParserError——只沿 /Prev 向后找，不向前
- **无 startxref 双 trailer**：取**第一个** trailer（无
  /Root → ParserError），并非最后一个
- **伪造 startxref 偏移 77777** → 仍正常（整表不可用 →
  回退全文档扫描救援）
- **/Root 5 1 R 代数不匹配**（obj 实为 5 0）→ 容忍
- **扫描模式重复对象定义**：**字节序最后一个胜出**

⚠ 静默丢失家族（正确 startxref + 个别条目指向垃圾偏移
9——表整体可用故**不触发**回退扫描，逐对象信任坏条目）：
- **内容流（obj4）坏** → elements=[] + 仅
  pdf_no_text_extracted 警告（文本无声蒸发）
- **页对象（obj3）坏** → 同上
- **字体（obj5）坏** → 仍提出 'BODY'、零警告（仅
  stderr FontBBox 降级）
- **Catalog（obj1）坏** → 正常（该失败会触发回退救援）
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


def _classic(tmp_path: Path, name: str,
             sx_offset: int | None = None,
             no_sx: bool = False,
             gen_ref: bool = False,
             wrong_off: tuple = ()):
    pdf = b"%PDF-1.4\n"
    offs = {}
    for i in sorted(_O):
        offs[i] = len(pdf)
        pdf += (f"{i} 0 obj\n".encode("latin-1")
                + _O[i] + b"\nendobj\n")
    x = len(pdf)
    pdf += b"xref\n0 6\n0000000000 65535 f \n"
    for i in range(1, 6):
        if i in wrong_off:
            pdf += b"0000000009 00000 n \n"
        else:
            pdf += (f"{offs[i]:010d} 00000 n \n"
                    .encode("latin-1"))
    root = b"5 1 R" if gen_ref else b"1 0 R"
    pdf += (b"trailer << /Root " + root
            + b" /Size 6 >>\n")
    if no_sx:
        pdf += b"%%EOF"
    else:
        sx = x if sx_offset is None \
            else sx_offset
        pdf += (b"startxref\n"
                + str(sx).encode()
                + b"\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def _prev_chain(tmp_path: Path, name: str,
                sx: str):
    pdf = b"%PDF-1.4\n"
    offs = {}
    for i in sorted(_O):
        offs[i] = len(pdf)
        pdf += (f"{i} 0 obj\n".encode("latin-1")
                + _O[i] + b"\nendobj\n")
    x1 = len(pdf)
    pdf += b"xref\n0 6\n0000000000 65535 f \n"
    for i in range(1, 6):
        if i == 5:
            pdf += b"0000000000 00000 f \n"
        else:
            pdf += (f"{offs[i]:010d} 00000 n \n"
                    .encode("latin-1"))
    pdf += b"trailer << /Size 6 >>\n%%EOF\n"
    x2 = len(pdf)
    pdf += (b"xref\n5 1\n"
            + f"{offs[5]:010d} 00000 n \n"
            .encode("latin-1"))
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 6 /Prev "
            + str(x1).encode() + b" >>\n")
    if sx == "x2":
        pdf += (b"startxref\n"
                + str(x2).encode()
                + b"\n%%EOF")
    elif sx == "x1":
        pdf += (b"startxref\n"
                + str(x1).encode()
                + b"\n%%EOF")
    else:
        pdf += b"%%EOF"
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def _ok(p: Path):
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == ["BODY"]
    assert doc.warnings == []


def _silent_empty(p: Path):
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements == []
    assert [w.code for w in
            doc.warnings] == [
        "pdf_no_text_extracted"]


def _err(p: Path):
    with pytest.raises(ParserError) as ei:
        FallbackParser().parse(
            p, compute_file_hash(p))
    assert "pdfplumber 打开/解析" \
        " PDF 失败" in str(ei.value)
    assert "No /Root object!" in str(ei.value)


def test_classic_xref(tmp_path):
    _ok(_classic(tmp_path, "classic.pdf"))


def test_prev_chain_resolves(tmp_path):
    _ok(_prev_chain(tmp_path,
                    "prev2.pdf", "x2"))


def test_root_only_forward(tmp_path):
    _err(_prev_chain(tmp_path,
                     "prev1.pdf", "x1"))


def test_no_startxref_first_trailer(
        tmp_path):
    _err(_prev_chain(tmp_path,
                     "nosx.pdf", "none"))


def test_bogus_startxref(tmp_path):
    _ok(_classic(tmp_path, "sxbad.pdf",
                 sx_offset=77777))


def test_generation_mismatch(tmp_path):
    _ok(_classic(tmp_path, "gen.pdf",
                 gen_ref=True))


def test_wrong_offsets_no_startxref(
        tmp_path):
    _ok(_classic(tmp_path, "nosx.pdf",
                 no_sx=True,
                 wrong_off=(4, 5)))


def test_wrong_content_offset_silent(
        tmp_path):
    _silent_empty(_classic(
        tmp_path, "w4.pdf",
        wrong_off=(4,)))


def test_wrong_page_offset_silent(
        tmp_path):
    _silent_empty(_classic(
        tmp_path, "w3.pdf",
        wrong_off=(3,)))


def test_wrong_font_offset_ok(
        tmp_path):
    _ok(_classic(tmp_path, "w5.pdf",
                 wrong_off=(5,)))


def test_wrong_catalog_offset_ok(
        tmp_path):
    _ok(_classic(tmp_path, "w1.pdf",
                 wrong_off=(1,)))


def test_duplicate_last_wins(
        tmp_path):
    variants = {
        "dupA.pdf": ("FIRSTDEF", "SECONDDEF"),
        "dupB.pdf": ("SECONDDEF", "FIRSTDEF"),
    }
    expect = {"dupA.pdf": "SECONDDEF",
              "dupB.pdf": "FIRSTDEF"}
    for name, order in variants.items():
        pdf = b"%PDF-1.4\n"
        for oid, o in _O.items():
            if oid == 4:
                for txt in order:
                    pdf += (
                        f"4 0 obj\n<< /Length"
                        f" {len(txt)} >>\n"
                        f"stream\nBT /F1 12 Tf"
                        f" 72 700 Td ({txt})"
                        f" Tj ET\nendstream"
                        f"\nendobj\n"
                        ).encode("latin-1")
            else:
                pdf += (f"{oid} 0 obj\n"
                        .encode("latin-1")
                        + o + b"\nendobj\n")
        pdf += (b"trailer << /Root 1 0 R"
                b" /Size 6 >>\n%%EOF")
        p = tmp_path / name
        p.write_bytes(pdf)
        doc = FallbackParser().parse(
            p, compute_file_hash(p))
        assert [e.content
                for e in doc.elements] == [
            expect[name]]
        assert doc.warnings == []
