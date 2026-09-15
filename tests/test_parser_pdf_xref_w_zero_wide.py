r"""PDF xref 流 /W 零宽字段与 8 字节偏移（Round 1992，a 优先级）。

规范允许 /W 任一字段宽度为 0（字段省略——gen 常见省略）
与超宽偏移（8 字节，巨文件）。全库夹具 /W 只有 [1 4 2]
（13 处）与 [1 2 1]（3 处，R1985）；零宽与 8 字节变体零
覆盖。探针 R1992 实证 pdfminer 全通：

- **T1 /W [1 4 0]**：gen 字段省略（行 5 字节）→ 'NOGENW'
  照提零告警——缺省 gen 作 0
- **T2 /W [1 8 2] + objstm type-2 行**：8 字节偏移 →
  'WIDEW' 照提零告警
- **T3 /W [1 8 0]**：8 字节偏移 + gen 省略（行 9 字节）→
  'BOTHW' 照提零告警

判别式：若按固定 [1 4 2] 步长读则行错位 → 偏移指向垃圾 →
ParserError / PDFNoValidXRef 翻红；若零宽字段被拒则 T1/T3
翻红；若 8 字节偏移被截成低 4 字节（碰巧同值不翻——但
文本在 100 字节量级文件里偏移小，8 字节高 4 位全零，截断
不可分辨，故 T2 附带 objstm type-2 行让索引字段也走 8 字
节布局参与错位检验）。
"""

from __future__ import annotations

import tempfile
import zlib
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _parse_pdf(data: bytes):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "w.pdf"
        p.write_bytes(data)
        return FallbackParser().parse(p, compute_file_hash(p))


def _build_plain(text: str, w_off: int, w_gen: int):
    body = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET".encode()
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(body)).encode()
            + b" >>\nstream\n" + body + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    out = bytearray(b"%PDF-1.5\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref_off = len(out)

    def row(t: int, off: int, gen: int) -> bytes:
        r = bytes([t]) + off.to_bytes(w_off, "big")
        if w_gen:
            r += gen.to_bytes(w_gen, "big")
        return r

    entries = [row(0, 0, 65535)]
    for oid in range(1, 6):
        entries.append(row(1, offsets[oid], 0))
    entries.append(row(1, xref_off, 0))
    xraw = b"".join(entries)
    w = f"/W [1 {w_off} {w_gen}]".encode()
    out += (b"6 0 obj\n<< /Type /XRef /Size 7 " + w
            + b" /Root 1 0 R /Length " + str(len(xraw)).encode()
            + b" >>\nstream\n" + xraw + b"\nendstream\nendobj\n")
    out += b"startxref\n" + str(xref_off).encode() + b"\n%%EOF"
    return _parse_pdf(bytes(out))


def _build_objstm_wide():
    inner: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    order = sorted(inner)
    header = b""
    payload = b""
    for oid in order:
        header += f"{oid} ".encode() + str(len(payload)).encode() + b" "
        payload += inner[oid] + b" "
    comp = zlib.compress(header + payload)
    n, first = len(order), len(header)

    body = b"BT /F1 12 Tf 100 700 Td (WIDEW) Tj ET"
    out = bytearray(b"%PDF-1.5\n")
    block4 = (b"4 0 obj\n<< /Length " + str(len(body)).encode()
              + b" >>\nstream\n" + body + b"\nendstream\nendobj\n")
    out += block4
    block7 = (b"7 0 obj\n<< /Type /ObjStm /N " + str(n).encode()
              + b" /First " + str(first).encode()
              + b" /Filter /FlateDecode /Length " + str(len(comp)).encode()
              + b" >>\nstream\n" + comp + b"\nendstream\nendobj\n")
    out += block7
    xref_off = len(out)
    off4 = len(b"%PDF-1.5\n")
    off7 = xref_off - len(block7)

    def row(t: int, off: int, gen: int) -> bytes:
        return bytes([t]) + off.to_bytes(8, "big") + gen.to_bytes(2, "big")

    rows = {0: row(0, 0, 65535),
            1: row(2, 7, order.index(1)),
            2: row(2, 7, order.index(2)),
            3: row(2, 7, order.index(3)),
            4: row(1, off4, 0),
            5: row(2, 7, order.index(5)),
            6: row(0, 0, 65535),
            7: row(1, off7, 0),
            8: row(1, xref_off, 0)}
    xraw = b"".join(rows[oid] for oid in range(9))
    out += (b"8 0 obj\n<< /Type /XRef /Size 9 /W [1 8 2] /Root 1 0 R"
            + b" /Length " + str(len(xraw)).encode()
            + b" >>\nstream\n" + xraw + b"\nendstream\nendobj\n")
    out += b"startxref\n" + str(xref_off).encode() + b"\n%%EOF"
    return _parse_pdf(bytes(out))


def test_w_no_gen_field():
    """T1：/W [1 4 0] gen 省略 → 'NOGENW' 照提零告警。"""
    d = _build_plain("NOGENW", 4, 0)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "NOGENW"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 155.332, 94.484], abs=0.01)
    assert d.warnings == []


def test_w_eight_byte_offsets_with_objstm():
    """T2：/W [1 8 2] + objstm → 'WIDEW' 照提零告警。"""
    d = _build_objstm_wide()
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "WIDEW"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 142.66, 94.484], abs=0.01)
    assert d.warnings == []


def test_w_eight_byte_no_gen():
    """T3：/W [1 8 0] → 'BOTHW' 照提零告警。"""
    d = _build_plain("BOTHW", 8, 0)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "BOTHW"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 144.664, 94.484], abs=0.01)
    assert d.warnings == []
