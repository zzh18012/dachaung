r"""PDF ObjStm + xref stream（PDF 1.5+ 现代结构，Round 1963，a 优先级）。

既有测试全部经典 xref 表 + 独立对象（广扫 ObjStm/XRef/1.5
零匹配）。真实现代 PDF（Word/打印驱动产物）默认对象流 +
交叉引用流。探针 R1963 实证（pdfminer 完整支持——ObjStm
内对象照常解析、type2 xref 条目定位、文本照提零告警）：

- **O1 裸 ObjStm + 裸 xref stream**（4 对象入流：Catalog/
  Pages/Page/Font；/W [1 4 2] type2 条目指向 (objstm oid,
  index)）→ 'OBJSTM' 照提、bbox 与经典结构逐位一致
- **O2 双 Flate / 单 Flate**（ObjStm 与 xref stream 各自
  FlateDecode，/Length 声明压缩后字节数）→ 与 O1 逐位一
  致（解压透明）
- **O3 ObjStm 内对象乱序**（oid 6 在 1 前——流内 pair 表
  "num rel-offset" 决定归属，编号与物理位置无关）→ 同 O1

探针教训（不锁测试）：xref stream /Length 误写解压前长度
时行为布局依赖——某布局 pdfminer 词法扫穿 EOF 崩
ParserError，另一布局越界跳过后照常恢复 endstream，非稳
定契约。
"""

from __future__ import annotations

import tempfile
import zlib
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

CONTENT = b"BT /F1 12 Tf 72 700 Td (OBJSTM) Tj ET"
_OBJS = {
    1: b"<< /Type /Catalog /Pages 2 0 R >>",
    2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
        b" /Resources << /Font << /F1 6 0 R >> >> /Contents 4 0 R >>"),
    6: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
}
_OBJSTM_OID = 5
_XREF_OID = 7


def _objstm(flate: bool, reverse: bool):
    order = sorted(_OBJS, reverse=reverse)
    pairs: list[str] = []
    bodies: list[bytes] = []
    off = 0
    for num in order:
        body = _OBJS[num]
        pairs.append(f"{num} {off}")
        bodies.append(body)
        off += len(body) + 1
    first = len(" ".join(pairs)) + 1
    data = (" ".join(pairs) + " ").encode() + b"\n".join(bodies)
    if flate:
        data = zlib.compress(data)
    return data, first, order


def _build(objstm_flate: bool, xref_flate: bool, reverse: bool) -> bytes:
    stm_data, first, order = _objstm(objstm_flate, reverse)
    parts: list[bytes] = [b"%PDF-1.5\n"]
    offsets: dict[int, int] = {}
    filt_o = b" /Filter /FlateDecode" if objstm_flate else b""
    filt_x = b" /Filter /FlateDecode" if xref_flate else b""

    def add(oid: int, body: bytes) -> None:
        offsets[oid] = len(b"".join(parts))
        parts.append(f"{oid} 0 obj\n".encode() + body + b"\nendobj\n")

    add(4, b"<< /Length " + str(len(CONTENT)).encode()
        + b" >>\nstream\n" + CONTENT + b"\nendstream")
    add(_OBJSTM_OID, b"<< /Type /ObjStm /N 4 /First " + str(first).encode()
        + b" /Length " + str(len(stm_data)).encode() + filt_o
        + b" >>\nstream\n" + stm_data + b"\nendstream")

    entries = {0: (0, 0, 65535)}
    for i, num in enumerate(order):
        entries[num] = (2, _OBJSTM_OID, i)
    entries[4] = (1, offsets[4], 0)
    entries[_OBJSTM_OID] = (1, offsets[_OBJSTM_OID], 0)
    entries[_XREF_OID] = (1, len(b"".join(parts)), 0)
    xref_off = len(b"".join(parts))
    stream = b"".join(
        bytes([t]) + f2.to_bytes(4, "big") + f3.to_bytes(2, "big")
        for t, f2, f3 in (entries[i] for i in range(_XREF_OID + 1)))
    xdata = zlib.compress(stream) if xref_flate else stream
    add(_XREF_OID, b"<< /Type /XRef /Size " + str(_XREF_OID + 1).encode()
        + b" /W [1 4 2] /Root 1 0 R /Length " + str(len(xdata)).encode()
        + filt_x + b" >>\nstream\n" + xdata + b"\nendstream")
    return b"".join(parts) + b"startxref\n" + str(xref_off).encode() + b"\n%%EOF"


def _parse(objstm_flate: bool = False, xref_flate: bool = False,
           reverse: bool = False):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "o.pdf"
        p.write_bytes(_build(objstm_flate, xref_flate, reverse))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_raw_objstm_and_xref_stream(tmp_path):
    """O1：裸 ObjStm + 裸 xref stream（type2 条目）→ 'OBJSTM'
    heading、bbox 与经典 xref 结构逐位一致、零告警。"""
    d = _parse()
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "OBJSTM"
    assert d.elements[0].metadata == {"level": 0, "heuristic": "short_line"}
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [72.0, 82.484, 120.672, 94.484], abs=0.01)
    assert d.warnings == []


@pytest.mark.parametrize("objstm_flate,xref_flate",
                         [(True, False), (False, True), (True, True)],
                         ids=["objstm", "xrefstm", "both"])
def test_flate_variants_identical(objstm_flate, xref_flate):
    """O2：ObjStm / xref stream 任一或全部 FlateDecode（/Length
    = 压缩后字节数）→ 与裸结构逐位一致。"""
    d = _parse(objstm_flate=objstm_flate, xref_flate=xref_flate)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "OBJSTM"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [72.0, 82.484, 120.672, 94.484], abs=0.01)
    assert d.warnings == []


def test_reversed_object_order_in_objstm():
    """O3：ObjStm 内对象乱序（oid 6 在 1 前）→ pair 表
    "num rel-offset" 决定归属、编号与物理位置无关 → 同 O1。"""
    d = _parse(reverse=True)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "OBJSTM"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [72.0, 82.484, 120.672, 94.484], abs=0.01)
    assert d.warnings == []
