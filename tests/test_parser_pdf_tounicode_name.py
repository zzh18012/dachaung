r"""PDF Type0 /ToUnicode 名字形态（Round 2004，a 优先级）。

pdffont.py:1143-1151——ToUnicode 非流而是**名字**时：
"Identity" ∈ {ToUnicode 名, Encoding 名, cid_ordering} 任一
命中 → IdentityUnicodeMap（CID==Unicode 码点直译）。
零覆盖（既有夹具 ToUnicode 全是流对象）。探针 R2004 实证：

- **T1 名字直接命中**：/ToUnicode /Identity-H（名）+
  Identity-H → <00410042> → CIDs 65/66 → 'AB'
- **T2 Encoding 析取命中**：/ToUnicode /ZZZMap（名，无
  Identity 子串）+ /Encoding /OneByteIdentityH → 第三
  析取仍 IdentityUnicodeMap → '(AB)' → 'AB'
- **T3 缺失对照**：无 ToUnicode → unicode_map=None →
  '(cid:65)(cid:66)'
- **T4 单字节 + 名字**：OneByteIdentityH + /ToUnicode
  /Identity-H → 'AB'

判别式：T1 若 '(cid:65)' 翻；T2 若 '(cid:65)' 翻（析取
只看 ToUnicode 名）；T3 若 'AB' 翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _build(encoding: bytes, tounicode: bytes | None,
           text_op: bytes = b"<00410042>"):
    content = b"BT /F1 12 Tf 100 700 Td " + text_op + b" Tj ET"
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 6 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: (b"<< /Type /Font /Subtype /Type0 /BaseFont /Test"
            b" /Encoding " + encoding
            + b" /DescendantFonts [ << /Type /Font"
            b" /Subtype /CIDFontType2 /BaseFont /Test /DW 1000"
            b" /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity)"
            b" /Supplement 0 >> /CIDToGIDMap /Identity"
            + (b" /ToUnicode " + tounicode if tounicode else b"")
            + b" >> ] >>"),
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
        p = Path(td) / "n.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_tounicode_name_identity_map():
    """T1：/ToUnicode /Identity-H（名）→ IdentityUnicodeMap → 'AB'。"""
    d = _build(b"/Identity-H", b"/Identity-H")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AB"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_encoding_disjunct_identity_map():
    """T2：/ToUnicode /ZZZMap + Encoding OneByteIdentityH → 析取仍 'AB'。"""
    d = _build(b"/OneByteIdentityH", b"/ZZZMap", b"(AB)")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AB"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_missing_tounicode_cid_output():
    """T3：无 ToUnicode → '(cid:65)(cid:66)'。"""
    d = _build(b"/Identity-H", None)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "(cid:65)(cid:66)"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_onebyte_with_name_tounicode():
    """T4：OneByteIdentityH + /ToUnicode /Identity-H（名）→ 'AB'。"""
    d = _build(b"/OneByteIdentityH", b"/Identity-H", b"(AB)")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AB"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []
