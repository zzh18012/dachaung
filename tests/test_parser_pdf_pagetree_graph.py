"""PDF 页树图退化：环/重复 Kids/指向 Catalog（Round 2024，a 优先级）。

pdfpage.create_pages 的 depth_first_search 带 visited 集合
（pdfpage.py:109-111，防递归错）。/Count 权威性已由 edges111
锁（Kids 权威、Count 忽略），**图形态**（自环/互环/重复 Kids/
Kids 指向 Catalog/悬空整数）grep 实证零覆盖。探针 R2024 实证
（好流 '(BODY)' 基线 [100, 82.484, 134.008, 94.484]）：

- **两不同页对照（C0）**：Kids [3 0 R 7 0 R] 两页 → 2 元素
  （page 1 @x100 + page 2 @x300）——重复去重的判别前提
- **重复 Kids 去重**：[3 0 R 3 0 R] → **仅 1 元素**——visited
  集合按 objid 去重，同一页引用两次只走一次（对照 C0 两元素）
- **自环断开**：Pages Kids [2 0 R 3 0 R]（含自身）→ visited
  断环、页照出 1 元素零告警
- **互环断开**：obj2 Kids [6 0 R]、obj6 Kids [2 0 R 3 0 R]
  → 1 元素零告警
- **Kids 指向 Catalog**：[1 0 R 3 0 R] → Catalog 节点 Type
  非 Pages/Page 静默跳过 → 1 元素零告警
- **Kids 悬空整数**：[42]（list_value 解析后裸 int ≠ 引用）→
  getobj(42) 抛 PdfminerException → ParserError
  pdfplumber_open_failed（message 尾部恰 "42"）

判别式：重复 Kids 若出 2 元素翻；环形态若异常/告警翻；E5 若
不崩或 message 不含 42 翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.base import ParserError
from app.parsers.fallback_parser import FallbackParser


def _stream(x: int) -> bytes:
    c = (b"BT /F1 12 Tf " + str(x).encode() + b" 700 Td (BODY) Tj ET")
    return (b"<< /Length " + str(len(c)).encode()
            + b" >>\nstream\n" + c + b"\nendstream")


def _parse(pages_body: bytes, extra: dict[int, bytes] | None = None):
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: pages_body,
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        4: _stream(100),
    }
    if extra:
        objs.update(extra)
    out = bytearray(b"%PDF-1.5\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref = len(out)
    m = max(objs)
    out += f"xref\n0 {m + 1}\n".encode() + b"0000000000 65535 f \n"
    for oid in range(1, m + 1):
        if oid in offsets:
            out += ("%010d 00000 n \n" % offsets[oid]).encode()
        else:
            out += b"0000000000 65535 f \n"
    out += (b"trailer\n<< /Size " + str(m + 1).encode()
            + b" /Root 1 0 R >>\nstartxref\n" + str(xref).encode()
            + b"\n%%EOF")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        p = Path(td) / "g.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


PAGE2 = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
         b" /Resources << /Font << /F1 5 0 R >> >> /Contents 8 0 R >>")


def _assert_single_body(d):
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "BODY"
    assert d.elements[0].source_locator["page"] == 1
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 134.008, 94.484], abs=0.01)
    assert d.warnings == []


def test_two_distinct_pages_control():
    """C0：Kids 两不同页 → 2 元素（page 1 @100 + page 2 @300）。"""
    d = _parse(b"<< /Type /Pages /Kids [3 0 R 7 0 R] /Count 2 >>",
               extra={7: PAGE2, 8: _stream(300)})
    assert len(d.elements) == 2
    assert all(e.content == "BODY" for e in d.elements)
    assert [e.source_locator["page"] for e in d.elements] == [1, 2]
    assert d.elements[1].source_locator["bbox"] == pytest.approx(
        [300.0, 82.484, 334.008, 94.484], abs=0.01)
    assert d.warnings == []


def test_duplicate_kids_deduped():
    """[3 0 R 3 0 R] → visited 按 objid 去重 → 仅 1 元素。"""
    d = _parse(b"<< /Type /Pages /Kids [3 0 R 3 0 R] /Count 2 >>")
    _assert_single_body(d)


def test_self_cycle_broken():
    """Kids 含自身 [2 0 R 3 0 R] → visited 断环 → 1 元素零告警。"""
    _assert_single_body(
        _parse(b"<< /Type /Pages /Kids [2 0 R 3 0 R] /Count 1 >>"))


def test_mutual_cycle_broken():
    """obj2→obj6→obj2 互环 → visited 断环 → 1 元素零告警。"""
    _assert_single_body(
        _parse(b"<< /Type /Pages /Kids [6 0 R] /Count 1 >>",
               extra={6: b"<< /Type /Pages /Kids [2 0 R 3 0 R] /Count 1 >>"}))


def test_kids_pointing_to_catalog_skipped():
    """Kids [1 0 R 3 0 R] → Catalog 节点静默跳过 → 1 元素零告警。"""
    _assert_single_body(
        _parse(b"<< /Type /Pages /Kids [1 0 R 3 0 R] /Count 1 >>"))


def test_kids_bare_int_crashes():
    """Kids [42] 裸整数 → getobj(42) PdfminerException → ParserError。"""
    with pytest.raises(ParserError) as ei:
        _parse(b"<< /Type /Pages /Kids [42] /Count 1 >>")
    assert ei.value.code == "pdfplumber_open_failed"
    assert ei.value.details == {"exception_type": "PdfminerException"}
    assert str(ei.value).rstrip().endswith("42")
