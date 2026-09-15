r"""PDF CIDFont 后代 /W 宽度数组四形态与容错（Round 1999，a 优先级）。

既有 Type0 夹具（R1994-1996、edges87/99/112）只用平的 /DW；
/W 数组零覆盖。get_widths（pdffont.py:54-88）+ PDFFont.char_width
查表回退（pdffont.py:955-971）探针 R1999 实证：

- **T1 数组态**：/W [1 [500 900]] → CID1=500(6pt)、CID2=900
  (10.8pt) → 'AB' x1=116.8
- **T2 三元组态**：/W [1 2 500] → 范围内同宽 → x1=112
- **T3 W 胜 DW**：/W [1 1 500]（只盖 CID1）→ CID2 回退
  DW 1000(12pt) → x1=118；单 'B' x1=112 证 CID2 未被盖
- **T4 前缀孤儿丢弃**：/W [1 2 [500 900]] → 数组态只消费
  r[-1]=2 → **CID1 静默掉**：'AB' x1=118；单 'A' x1=112 证
  CID1 未拿到 500（对照 T3 的方向相反）
- **T5 倒序范围 no-op**：/W [5 3 500] → range(5,4) 空 →
  双双 DW → x1=124
- **T6 后写覆盖**：/W [1 1 500 1 1 900] → dict 赋值后者胜 →
  单 'A' 10.8pt → x1=110.8

判别式：若数组态消费全部前缀则 T4 翻 116.8→错；若倒序范围
反卷（char2..char1）则 T5 翻红；若先写胜则 T6 x1=106 翻红。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _build(w_array: bytes, hex_text: str):
    tu = (f"/CIDInit /ProcSet findresource begin\n12 dict begin\n"
          "begincmap\n/CIDSystemInfo << /Registry (Adobe)"
          " /Ordering (UCS) /Supplement 0 >> def\n"
          "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
          "1 begincodespacerange\n<0000> <ffff>\n"
          "endcodespacerange\n"
          "2 beginbfchar\n<0001> <0041>\n<0002> <0042>\n"
          "endbfchar\n"
          "endcmap\nCMapName currentdict /CMap defineresource"
          " pop\nend\nend").encode()
    content = f"BT /F1 12 Tf 100 700 Td <{hex_text}> Tj ET".encode()
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 6 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: (b"<< /Type /Font /Subtype /Type0 /BaseFont /Test"
            b" /Encoding /Identity-H /DescendantFonts [ << /Type /Font"
            b" /Subtype /CIDFontType2 /BaseFont /Test /DW 1000"
            b" /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity)"
            b" /Supplement 0 >> /CIDToGIDMap /Identity /W " + w_array
            + b" >> ] /ToUnicode 7 0 R >>"),
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
        p = Path(td) / "w.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def _heading(d):
    assert [e.type for e in d.elements] == ["heading"]
    return d.elements[0]


def test_array_form_consecutive_widths():
    """T1：数组态 [1 [500 900]] → 6+10.8 → x1=116.8。"""
    d = _build(b"[1 [500 900]]", "00010002")
    e = _heading(d)
    assert e.content == "AB"
    assert e.source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 116.8, 92.0], abs=0.01)
    assert d.warnings == []


def test_range_form_uniform_width():
    """T2：三元组态 [1 2 500] → 6+6 → x1=112。"""
    d = _build(b"[1 2 500]", "00010002")
    e = _heading(d)
    assert e.content == "AB"
    assert e.source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 112.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_w_wins_partial_dw_fallback():
    """T3：/W 只盖 CID1 → 'AB' 118；单 'B' 112 证 CID2 走 DW。"""
    d = _build(b"[1 1 500]", "00010002")
    e = _heading(d)
    assert e.content == "AB"
    assert e.source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 118.0, 92.0], abs=0.01)
    d2 = _build(b"[1 1 500]", "0002")
    e2 = _heading(d2)
    assert e2.content == "B"
    assert e2.source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 112.0, 92.0], abs=0.01)
    assert d.warnings == [] and d2.warnings == []


def test_array_form_drops_prefix_orphans():
    """T4：[1 2 [500 900]] 只消费 r[-1]=2 → CID1 静默掉 → 118；单 'A' 112。"""
    d = _build(b"[1 2 [500 900]]", "00010002")
    e = _heading(d)
    assert e.content == "AB"
    assert e.source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 118.0, 92.0], abs=0.01)
    d2 = _build(b"[1 2 [500 900]]", "0001")
    e2 = _heading(d2)
    assert e2.content == "A"
    assert e2.source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 112.0, 92.0], abs=0.01)
    assert d.warnings == [] and d2.warnings == []


def test_inverted_range_noop():
    """T5：倒序范围 [5 3 500] → range(5,4) 空 → 双 DW → x1=124。"""
    d = _build(b"[5 3 500]", "00010002")
    e = _heading(d)
    assert e.content == "AB"
    assert e.source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_later_entry_overwrites():
    """T6：[1 1 500 1 1 900] 后写胜 → 单 'A' 10.8pt → x1=110.8。"""
    d = _build(b"[1 1 500 1 1 900]", "0001")
    e = _heading(d)
    assert e.content == "A"
    assert e.source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 110.8, 92.0], abs=0.01)
    assert d.warnings == []
