r"""PDF xref 流 /Index 稀疏子节 + ObjStm /Extends 链（Round
1984，a 优先级）。

真实大文件/增量更新的常见形态：xref 流 /Index [start count
...] 只列实际存在的 oid 区间（中间留洞），甚至可省略 0 号
free 头行；ObjStm 分段后段 /Extends 指向前段。覆盖 grep 确
认 /Prev（edges52/102/103）、Linearized（edges103）、多子节
经典表（edges103）已锁，/Index 与 /Extends 零覆盖。探针
R1984 实证 pdfminer 全通：

- **T1 /Index [0 6 7 2 9 1]**：oid 6 留洞、8 行 type-0
  free、font 放 oid 9 仍在 objstm → 'SPARSIDX' 照提
- **T2 ObjStm /Extends 链**：5 号装 catalog/pages/page、
  10 号 /Extends 5 装 font → 'EXTCHAIN' 照提（各段独立索
  引，/Extends 对读者透明）
- **T3 /Index [1 5 7 2 9 1]**：无 0 号行（free 头省略）→
  'NOZEROROW' 照提

判别式：若 /Index 被忽略（按 0..Size 稠密读）则 T1/T3 行
数错位 → type-2 索引指错对象 → ParserError 或对象缺失翻
红；若 /Extends 被误当依赖（后段不能独立解码）则 T2 翻
红；若 free 头行被强制要求则 T3 翻 PDFNoValidXRef → 回退
路径（R1972 已锁回退行为，此处形状不同）。
"""

from __future__ import annotations

import tempfile
import zlib
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _objstm_bytes(objs: dict[int, bytes]):
    order = sorted(objs)
    header = b""
    payload = b""
    for oid in order:
        header += f"{oid} ".encode() + str(len(payload)).encode() + b" "
        payload += objs[oid] + b" "
    return zlib.compress(header + payload), len(header), len(order)


def _parse_pdf(data: bytes):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "s.pdf"
        p.write_bytes(data)
        return FallbackParser().parse(p, compute_file_hash(p))


def _sparse(index_pairs: list[tuple[int, int]], text: str):
    objs_stm: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 9 0 R >> >> /Contents 4 0 R >>"),
        9: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    comp, first, n = _objstm_bytes(objs_stm)
    body = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET".encode()

    out = bytearray(b"%PDF-1.5\n")
    out += (b"4 0 obj\n<< /Length " + str(len(body)).encode()
            + b" >>\nstream\n" + body + b"\nendstream\nendobj\n")
    out += (b"5 0 obj\n<< /Type /ObjStm /N " + str(n).encode()
            + b" /First " + str(first).encode()
            + b" /Filter /FlateDecode /Length " + str(len(comp)).encode()
            + b" >>\nstream\n" + comp + b"\nendstream\nendobj\n")
    xref_off = len(out)

    off4 = len(b"%PDF-1.5\n")
    off5 = off4 + len(
        b"4 0 obj\n<< /Length " + str(len(body)).encode()
        + b" >>\nstream\n" + body + b"\nendstream\nendobj\n")

    free = bytes([0]) + (0).to_bytes(4, "big") + (65535).to_bytes(2, "big")

    def e1(off: int) -> bytes:
        return bytes([1]) + off.to_bytes(4, "big") + (0).to_bytes(2, "big")

    def e2(idx: int) -> bytes:
        return bytes([2]) + (5).to_bytes(4, "big") + idx.to_bytes(2, "big")

    order = sorted(objs_stm)
    rows: dict[int, bytes] = {
        0: free,
        1: e2(order.index(1)),
        2: e2(order.index(2)),
        3: e2(order.index(3)),
        4: e1(off4),
        5: e1(off5),
        7: e1(xref_off),
        8: free,
        9: e2(order.index(9)),
    }
    xraw = b"".join(rows[oid]
                    for start, count in index_pairs
                    for oid in range(start, start + count))
    index_str = b" /Index [" + b" ".join(
        f"{s} {c}".encode() for s, c in index_pairs) + b"]"
    out += (b"7 0 obj\n<< /Type /XRef /Size 10" + index_str
            + b" /W [1 4 2] /Root 1 0 R /Length "
            + str(len(xraw)).encode()
            + b" >>\nstream\n" + xraw + b"\nendstream\nendobj\n")
    out += b"startxref\n" + str(xref_off).encode() + b"\n%%EOF"
    return _parse_pdf(bytes(out))


def _extends_chain():
    comp_a, first_a, n_a = _objstm_bytes({
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 6 0 R >> >> /Contents 4 0 R >>"),
    })
    comp_b, first_b, n_b = _objstm_bytes({
        6: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    })
    body = b"BT /F1 12 Tf 100 700 Td (EXTCHAIN) Tj ET"

    out = bytearray(b"%PDF-1.5\n")
    out += (b"4 0 obj\n<< /Length " + str(len(body)).encode()
            + b" >>\nstream\n" + body + b"\nendstream\nendobj\n")
    out += (b"5 0 obj\n<< /Type /ObjStm /N " + str(n_a).encode()
            + b" /First " + str(first_a).encode()
            + b" /Filter /FlateDecode /Length " + str(len(comp_a)).encode()
            + b" >>\nstream\n" + comp_a + b"\nendstream\nendobj\n")
    block10 = (b"10 0 obj\n<< /Type /ObjStm /Extends 5 0 R /N "
               + str(n_b).encode()
               + b" /First " + str(first_b).encode()
               + b" /Filter /FlateDecode /Length " + str(len(comp_b)).encode()
               + b" >>\nstream\n" + comp_b + b"\nendstream\nendobj\n")
    out += block10
    xref_off = len(out)

    off4 = len(b"%PDF-1.5\n")
    off5 = off4 + len(
        b"4 0 obj\n<< /Length " + str(len(body)).encode()
        + b" >>\nstream\n" + body + b"\nendstream\nendobj\n")
    off10 = xref_off - len(block10)

    free = bytes([0]) + (0).to_bytes(4, "big") + (65535).to_bytes(2, "big")

    def e1(off: int) -> bytes:
        return bytes([1]) + off.to_bytes(4, "big") + (0).to_bytes(2, "big")

    def e2(stm: int, idx: int) -> bytes:
        return bytes([2]) + stm.to_bytes(4, "big") + idx.to_bytes(2, "big")

    rows: dict[int, bytes] = {
        0: free,
        1: e2(5, 0),
        2: e2(5, 1),
        3: e2(5, 2),
        4: e1(off4),
        5: e1(off5),
        6: e2(10, 0),
        7: e1(xref_off),
        8: free,
        9: free,
        10: e1(off10),
    }
    xraw = b"".join(rows[oid] for oid in range(11))
    out += (b"7 0 obj\n<< /Type /XRef /Size 11 /W [1 4 2] /Root 1 0 R"
            + b" /Length " + str(len(xraw)).encode()
            + b" >>\nstream\n" + xraw + b"\nendstream\nendobj\n")
    out += b"startxref\n" + str(xref_off).encode() + b"\n%%EOF"
    return _parse_pdf(bytes(out))


def test_sparse_index_with_gaps():
    """T1：/Index [0 6 7 2 9 1] 洞 6/8 + type-0 行 → 照提零告警。"""
    d = _sparse([(0, 6), (7, 2), (9, 1)], "SPARSIDX")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "SPARSIDX"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 160.684, 94.484], abs=0.01)
    assert d.warnings == []


def test_objstm_extends_chain():
    """T2：两个 ObjStm /Extends 链、对象跨段 → 照提零告警。"""
    d = _extends_chain()
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "EXTCHAIN"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 160.672, 94.484], abs=0.01)
    assert d.warnings == []


def test_index_without_zero_row():
    """T3：/Index 省略 0 号 free 头行 → 照提零告警。"""
    d = _sparse([(1, 5), (7, 2), (9, 1)], "NOZEROROW")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "NOZEROROW"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 180.664, 94.484], abs=0.01)
    assert d.warnings == []
