r"""PDF Type1 简单字体自定义宽度分支（Round 1998，a 优先级）。

edges93 只锁 Type3 /Widths；Type1 的 /FirstChar//LastChar/
/Widths 查表与 /MissingWidth 回退零覆盖。探针 R1998 + 源码
对照（pdffont.py:1053-1062）实证分支裁决：

- **内置 BaseFont 走 AFM 度量**：PDFType1Font 对 FontMetrics
  DB 命中的 BaseFont（Helvetica）**不读 /Widths**——E1
  'AB'+/Widths[400 900] 的 x1=116.008 恰等于内置 667+667
  （非自定义 400+900 的 115.6）；/FontDescriptor /MissingWidth
  同被忽略（E3 与无描述符的 E2 完全同值）
- **未知 BaseFont 才读 /Widths**：/BaseFont /ZZZUnknown →
  400+900 生效 x1=115.6；范围外字符回退 **0 宽**（E5 'AZ'
  x1=104.8=仅 A 4.8pt）；此时 /MissingWidth 生效（E6 250
  →3pt → x1=107.8）

判别式：若 pdfminer 一律读 /Widths 则 T1 翻 115.6；若内置
字体也走 /MissingWidth 则 T2 翻红；若缺宽回退非 0（默认
1000）则 T4 翻红。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _build(basefont: bytes, text: str, descriptor: bytes = b""):
    content = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET".encode()
    widths = b"/FirstChar 65 /LastChar 66 /Widths [400 900]"
    fd_ref = b" /FontDescriptor 7 0 R" if descriptor else b""
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 6 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: (b"<< /Type /Font /Subtype /Type1 " + basefont
            + b" " + widths + fd_ref + b" >>"),
    }
    if descriptor:
        objs[7] = descriptor
    out = bytearray(b"%PDF-1.4\n")
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
        p = Path(td) / "w.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


_HELV = b"/BaseFont /Helvetica"
_UNK = b"/BaseFont /ZZZUnknown"
_FD_NO_MW = (b"<< /Type /FontDescriptor /FontName /ZZZUnknown"
             b" /Flags 32 >>")
_FD_MW = (b"<< /Type /FontDescriptor /FontName /ZZZUnknown"
          b" /Flags 32 /MissingWidth 250 >>")


def test_builtin_basefont_ignores_widths():
    """T1：内置 Helvetica 不读 /Widths——x1=116.008（内置 667+667）。"""
    d = _build(_HELV, "AB")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AB"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 116.008, 94.484], abs=0.01)
    assert d.warnings == []


def test_builtin_basefont_ignores_missing_width():
    """T2：内置字体 /MissingWidth 被忽略——与无描述符同值。"""
    d = _build(_HELV, "AZ", _FD_MW)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AZ"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 115.336, 94.484], abs=0.01)
    assert d.warnings == []


def test_unknown_basefont_applies_widths():
    """T3：未知 BaseFont 读 /Widths——400+900 生效 x1=115.6。"""
    d = _build(_UNK, "AB", _FD_NO_MW)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AB"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 115.6, 92.0], abs=0.01)
    assert d.warnings == []


def test_unknown_outofrange_zero_width():
    """T4：未知字体范围外字符回退 0 宽——x1=104.8（仅 A 前进）。"""
    d = _build(_UNK, "AZ", _FD_NO_MW)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AZ"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 104.8, 92.0], abs=0.01)
    assert d.warnings == []


def test_unknown_missing_width_applies():
    """T5：未知字体 /MissingWidth 250 生效——Z 3pt → x1=107.8。"""
    d = _build(_UNK, "AZ", _FD_MW)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AZ"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 107.8, 92.0], abs=0.01)
    assert d.warnings == []
