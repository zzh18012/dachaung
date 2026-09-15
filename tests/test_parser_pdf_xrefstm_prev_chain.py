r"""PDF xref 流 /Prev 链——增量更新家族（Round 1993，a 优先级）。

既有 /Prev 覆盖（edges52/102/103）全是**经典表**链；xref 流
→ xref 流的续链零覆盖。真实 Acrobat 增量更新对 xref 流文档：
追加新对象 + 稀疏 /Index（只列变化区间）新 xref 流 + /Prev
指向前一代 xref 流。探针 R1993 实证 pdfminer 全通：

- **T1 双代**：rev2 稀疏 /Index [(4 1)(9 1)] 更新内容流
  'OLDTXT'→'NEWTXT' → 新文本胜出，零告警
- **T2 三代链**：OLDTXT→MIDTXT→LASTXT（xref 流 obj 6/9/10
  逐代 /Prev）→ 最后一代胜出，零告警
- **T3 删除语义**：rev2 把 obj4 标 type-0 free → **free 行
  不遮蔽 /Prev 链在用条目**——'OLDTXT' 照提、零告警
  （pdfminer 对稀疏段 free 行跳过不记录，不实现"删除"）

判别式：若稀疏 /Index 不与 /Prev 合并则 obj4 找不到 → 零元素
+ pdf_no_text_extracted 翻红；若链向解析（/Prev 偏移错读）则
PDFNoValidXRef / 回退扫描文本错位翻红；若 free 行被实现为删除
则 T3 翻零元素（实际不翻——这正是要锁的行为差异）。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _parse_pdf(data: bytes):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "p.pdf"
        p.write_bytes(data)
        return FallbackParser().parse(p, compute_file_hash(p))


def _contents_obj(text: str, oid: int) -> bytes:
    body = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET".encode()
    return (f"{oid} 0 obj\n".encode()
            + b"<< /Length " + str(len(body)).encode()
            + b" >>\nstream\n" + body + b"\nendstream\nendobj\n")


def _xrefstm_obj(xref_oid: int, size: int, rows: dict[int, bytes],
                 index_pairs: list[tuple[int, int]], root: bytes,
                 prev_off: int | None) -> bytes:
    xraw = b"".join(rows[oid]
                    for s, c in index_pairs for oid in range(s, s + c))
    index_str = b" /Index [" + b" ".join(
        f"{s} {c}".encode() for s, c in index_pairs) + b"]"
    prev_str = (f" /Prev {prev_off}".encode() if prev_off is not None
                else b"")
    return (f"{xref_oid} 0 obj\n".encode()
            + b"<< /Type /XRef /Size " + str(size).encode() + index_str
            + b" /W [1 4 2] " + root + prev_str
            + b" /Length " + str(len(xraw)).encode()
            + b" >>\nstream\n" + xraw + b"\nendstream\nendobj\n")


_FREE = bytes([0]) + (0).to_bytes(4, "big") + (65535).to_bytes(2, "big")


def _inuse(off: int) -> bytes:
    return bytes([1]) + off.to_bytes(4, "big") + (0).to_bytes(2, "big")


def _base_doc() -> tuple[bytearray, dict[int, int], int]:
    """rev1：完整文档 + 全量 /Index xref 流（obj 6）。

    返回 (out, offsets, prev1_off)。"""
    out = bytearray(b"%PDF-1.5\n")
    base: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    offsets = {}
    for oid in sorted(base):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + base[oid] + b"\nendobj\n"
    offsets[4] = len(out)
    out += _contents_obj("OLDTXT", 4)
    rows = {0: _FREE}
    for oid in range(1, 6):
        rows[oid] = _inuse(offsets[oid])
    rows[6] = _inuse(len(out))
    stm = _xrefstm_obj(6, 7, rows, [(0, 7)], b"/Root 1 0 R", None)
    out += stm
    prev1 = len(out) - len(stm)
    out += b"startxref\n" + str(prev1).encode() + b"\n%%EOF\n"
    return out, offsets, prev1


def _two_rev() -> bytes:
    out, _, prev1 = _base_doc()
    off4_new = len(out)
    out += _contents_obj("NEWTXT", 4)
    rows2 = {4: _inuse(off4_new), 9: _inuse(0)}
    stm2 = _xrefstm_obj(9, 10, rows2, [(4, 1), (9, 1)],
                        b"/Root 1 0 R", prev1)
    rows2[9] = _inuse(len(out))
    stm2 = _xrefstm_obj(9, 10, rows2, [(4, 1), (9, 1)],
                        b"/Root 1 0 R", prev1)
    out += stm2
    off_stm2 = len(out) - len(stm2)
    out += b"startxref\n" + str(off_stm2).encode() + b"\n%%EOF"
    return bytes(out)


def _three_rev() -> bytes:
    out, _, prev1 = _base_doc()
    off4_mid = len(out)
    out += _contents_obj("MIDTXT", 4)
    rows2 = {4: _inuse(off4_mid), 9: _inuse(0)}
    stm2 = _xrefstm_obj(9, 11, rows2, [(4, 1), (9, 1)],
                        b"/Root 1 0 R", prev1)
    rows2[9] = _inuse(len(out))
    stm2 = _xrefstm_obj(9, 11, rows2, [(4, 1), (9, 1)],
                        b"/Root 1 0 R", prev1)
    out += stm2
    prev2 = len(out) - len(stm2)

    off4_last = len(out)
    out += _contents_obj("LASTXT", 4)
    rows3 = {4: _inuse(off4_last), 10: _inuse(0)}
    stm3 = _xrefstm_obj(10, 11, rows3, [(4, 1), (10, 1)],
                        b"/Root 1 0 R", prev2)
    rows3[10] = _inuse(len(out))
    stm3 = _xrefstm_obj(10, 11, rows3, [(4, 1), (10, 1)],
                        b"/Root 1 0 R", prev2)
    out += stm3
    off_stm3 = len(out) - len(stm3)
    out += b"startxref\n" + str(off_stm3).encode() + b"\n%%EOF"
    return bytes(out)


def _free_contents() -> bytes:
    out, _, prev1 = _base_doc()
    rows2 = {4: _FREE, 9: _inuse(0)}
    stm2 = _xrefstm_obj(9, 10, rows2, [(4, 1), (9, 1)],
                        b"/Root 1 0 R", prev1)
    rows2[9] = _inuse(len(out))
    stm2 = _xrefstm_obj(9, 10, rows2, [(4, 1), (9, 1)],
                        b"/Root 1 0 R", prev1)
    out += stm2
    off_stm2 = len(out) - len(stm2)
    out += b"startxref\n" + str(off_stm2).encode() + b"\n%%EOF"
    return bytes(out)


def test_xrefstm_prev_two_rev_new_wins():
    """T1：双代稀疏 /Index 更新 → 'NEWTXT' 胜出零告警。"""
    d = _parse_pdf(_two_rev())
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "NEWTXT"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 150.664, 94.484], abs=0.01)
    assert d.warnings == []


def test_xrefstm_prev_three_rev_last_wins():
    """T2：三代链 → 'LASTXT' 胜出零告警。"""
    d = _parse_pdf(_three_rev())
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "LASTXT"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 145.348, 94.484], abs=0.01)
    assert d.warnings == []


def test_xrefstm_prev_free_row_not_shadowing():
    """T3：free 行不遮蔽 /Prev 在用条目 → 'OLDTXT' 照提零告警。"""
    d = _parse_pdf(_free_contents())
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "OLDTXT"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 147.34, 94.484], abs=0.01)
    assert d.warnings == []
