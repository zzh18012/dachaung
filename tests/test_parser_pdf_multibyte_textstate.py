r"""PDF 多字节字体文本状态选择归零 + 竖排 TJ（Round 2003，a 优先级）。

pdfdevice.py:115-116 `if font.is_multibyte(): wordspace = 0`
——Tw 对 Type0 失效而 Tc（charspace）不受影响，零覆盖
（edges44 只锁简单字体 Tw/Tc）；pdfdevice.py:213-214 竖排
TJ 数字沿列位移（y -= obj·dxscale）零覆盖。探针 R2003 实证：

- **T1/T2 Tw 归零**：OneByteIdentityH '(A B)'（空格 0x20
  未映射 → 'A(cid:32)B'）无 Tw 与 15 Tw **完全同值**
  x1=136（3×DW1000×12pt）——wordspace 被归零
- **T3 简单字体对照**：Helvetica '(A B)' + 15 Tw →
  x1=134.344 = 19.344（667+278+667 千分比×12）+ **15**
  （wordspace=Tw·scaling，无 0.001·fontsize 因子）——
  Tw 生效且单位为点×Tz%
- **T4 竖排 TJ 数字**：Identity-V [(A) -250 (B)] →
  B 原点 y -= -250·0.012 → **+3 上移**（对照 R2000 纯
  堆叠 24pt：union 高 21=A 12 + B 12 − 重叠 3）→ 'A B'
  （y 重叠 3pt 不足以合词）
- **T5 Tc 保留**：OneByteIdentityH '(AB)' 5 Tc →
  x1=129=124+5（charspace 不归零）且 5pt 间隙 > 3pt 词
  裂变阈值 → 内容 'A B'

判别式：T2 若 +15 翻；T3 若 121.144（千分比单位）翻；
T4 若 B 下移或 24 高翻；T5 若 124 或 128.2 翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _build(font6: bytes, content: bytes):
    tu = (f"/CIDInit /ProcSet findresource begin\n12 dict begin\n"
          "begincmap\n/CIDSystemInfo << /Registry (Adobe)"
          " /Ordering (UCS) /Supplement 0 >> def\n"
          "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
          "1 begincodespacerange\n<00> <ff>\n"
          "endcodespacerange\n"
          "2 beginbfchar\n<41> <0041>\n<42> <0042>\n"
          "endbfchar\n"
          "endcmap\nCMapName currentdict /CMap defineresource"
          " pop\nend\nend").encode()
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 6 0 R /F2 5 0 R >> >>"
            b" /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: font6,
        7: (b"<< /Length " + str(len(tu)).encode()
            + b" >>\nstream\n" + tu + b"\nendstream"),
    }
    out = bytearray(b"%PDF-1.5\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref = len(out)
    m = max(objs)
    out += f"xref\n0 {m + 1}\n".encode() + b"0000000000 65535 f \n"
    for oid in range(1, m + 1):
        out += ("%010d 00000 n \n" % offsets[oid]).encode()
    out += (b"trailer\n<< /Size " + str(m + 1).encode()
            + b" /Root 1 0 R >>\nstartxref\n" + str(xref).encode()
            + b"\n%%EOF")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "m.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


_TYPE0H = (b"<< /Type /Font /Subtype /Type0 /BaseFont /Test"
           b" /Encoding /OneByteIdentityH"
           b" /DescendantFonts [ << /Type /Font"
           b" /Subtype /CIDFontType2 /BaseFont /Test /DW 1000"
           b" /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity)"
           b" /Supplement 0 >> /CIDToGIDMap /Identity"
           b" >> ] /ToUnicode 7 0 R >>")

_TYPE0V = (b"<< /Type /Font /Subtype /Type0 /BaseFont /Test"
           b" /Encoding /OneByteIdentityV"
           b" /DescendantFonts [ << /Type /Font"
           b" /Subtype /CIDFontType2 /BaseFont /Test /DW 1000"
           b" /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity)"
           b" /Supplement 0 >> /CIDToGIDMap /Identity"
           b" >> ] /ToUnicode 7 0 R >>")


def test_multibyte_space_unmapped_baseline():
    """T1：无 Tw → 'A(cid:32)B' x1=136（空格 CID 32 未映射仍计宽）。"""
    d = _build(_TYPE0H, b"BT /F1 12 Tf 100 700 Td (A B) Tj ET")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "A(cid:32)B"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 136.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_multibyte_tw_zeroed():
    """T2：15 Tw → wordspace 归零 → 与 T1 完全同值 x1=136。"""
    d = _build(_TYPE0H, b"BT /F1 12 Tf 15 Tw 100 700 Td (A B) Tj ET")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "A(cid:32)B"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 136.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_simple_font_tw_applies():
    """T3：Helvetica '(A B)' + 15 Tw → x1=134.344（19.344+15 点单位）。"""
    d = _build(_TYPE0H, b"BT /F2 12 Tf 15 Tw 100 700 Td (A B) Tj ET")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "A B"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 134.344, 94.484], abs=0.01)
    assert d.warnings == []


def test_vertical_tj_number_shifts_up():
    """T4：竖排 [(A) -250 (B)] → B 上移 3pt → union [94, 90.56, 106, 111.56]。"""
    d = _build(_TYPE0V, b"BT /F1 12 Tf 100 700 Td [(A) -250 (B)] TJ ET")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "A B"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [94.0, 90.56, 106.0, 111.56], abs=0.01)
    assert d.warnings == []


def test_multibyte_tc_kept_and_splits():
    """T5：5 Tc → charspace 保留 x1=129 且 5pt 间隙裂词 → 'A B'。"""
    d = _build(_TYPE0H, b"BT /F1 12 Tf 5 Tc 100 700 Td (AB) Tj ET")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "A B"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 129.0, 92.0], abs=0.01)
    assert d.warnings == []
