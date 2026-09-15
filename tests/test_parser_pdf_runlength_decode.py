r"""PDF RunLengthDecode 内容流透明解码（Round 1991，a 优先级）。

老 PDF（Acrobat 3 时代）内容流/对象流偶用 RLE：0-127 字面
n+1 字节 / 129 NOP / 130-255 重复下字节 257-n 次 / 128
EOD。grep 实证 RunLengthDecode 全库零覆盖（Flate/LZW/
ASCII85/ASCIIHex/链式数组均已被 edges51/109/exotic_codecs
锁定）。探针 R1991 实证：

- **T1 内容流 RLE**（字面段 + 重复段混合）→ 'RUNLEN' 照提
  零告警
- **T2 ObjStm /RunLengthDecode + xref 流**（交叉引用流格
  式）→ 'RLSTM' 照提零告警——对象流解码器同样走 RLE
- **T3 流中 EOD(128) + 12 字节尾部垃圾** → 解码停在 EOD、
  垃圾忽略 → 'RLEOD' 照提零告警

判别式：若 RLE 重复段计数偏一（257-n vs 256-n）则文本错位
/ 算子断裂 → 零元素 + pdf_no_text_extracted 或 ParserError
翻红；若解码器不认 EOD（按 /Length 硬读）则 T3 垃圾进流
→ 解析错翻红；若 ObjStm 路径漏 RLE 则 T2 翻 PDFNoValidXRef
或对象缺失。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _rle(data: bytes, tail: bytes = b"") -> bytes:
    out = bytearray()
    i = 0
    lit = bytearray()

    def flush() -> None:
        while lit:
            chunk = lit[:128]
            out.append(len(chunk) - 1)
            out.extend(chunk)
            del lit[:len(chunk)]

    while i < len(data):
        run = 1
        while (i + run < len(data) and run < 128
               and data[i + run] == data[i]):
            run += 1
        if run >= 3:
            flush()
            out.append(257 - run)
            out.append(data[i])
            i += run
        else:
            lit.append(data[i])
            if len(lit) == 128:
                flush()
            i += 1
    flush()
    out.append(128)
    out.extend(tail)
    return bytes(out)


def _parse_pdf(data: bytes):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "r.pdf"
        p.write_bytes(data)
        return FallbackParser().parse(p, compute_file_hash(p))


def _classic(cs_body: bytes) -> bytes:
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Filter /RunLengthDecode /Length "
            + str(len(cs_body)).encode()
            + b" >>\nstream\n" + cs_body + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    out = bytearray(b"%PDF-1.3\n")
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
    return _parse_pdf(bytes(out))


def _objstm_rle():
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
    stm = _rle(header + payload)
    n, first = len(order), len(header)

    body = b"BT /F1 12 Tf 100 700 Td (RLSTM) Tj ET"
    out = bytearray(b"%PDF-1.5\n")
    block4 = (b"4 0 obj\n<< /Length " + str(len(body)).encode()
              + b" >>\nstream\n" + body + b"\nendstream\nendobj\n")
    out += block4
    block7 = (b"7 0 obj\n<< /Type /ObjStm /N " + str(n).encode()
              + b" /First " + str(first).encode()
              + b" /Filter /RunLengthDecode /Length " + str(len(stm)).encode()
              + b" >>\nstream\n" + stm + b"\nendstream\nendobj\n")
    out += block7
    xref_off = len(out)
    off4 = len(b"%PDF-1.5\n")
    off7 = xref_off - len(block7)

    free = bytes([0]) + (0).to_bytes(4, "big") + (65535).to_bytes(2, "big")

    def e1(off: int) -> bytes:
        return bytes([1]) + off.to_bytes(4, "big") + (0).to_bytes(2, "big")

    def e2(idx: int) -> bytes:
        return bytes([2]) + (7).to_bytes(4, "big") + idx.to_bytes(2, "big")

    rows = {0: free, 1: e2(order.index(1)), 2: e2(order.index(2)),
            3: e2(order.index(3)), 4: e1(off4), 5: e2(order.index(5)),
            6: free, 7: e1(off7), 8: e1(xref_off)}
    xraw = b"".join(rows[oid] for oid in range(9))
    out += (b"8 0 obj\n<< /Type /XRef /Size 9 /W [1 4 2] /Root 1 0 R"
            + b" /Length " + str(len(xraw)).encode()
            + b" >>\nstream\n" + xraw + b"\nendstream\nendobj\n")
    out += b"startxref\n" + str(xref_off).encode() + b"\n%%EOF"
    return _parse_pdf(bytes(out))


def test_rle_content_stream():
    """T1：内容流 RLE → 'RUNLEN' 照提零告警。"""
    d = _classic(_rle(b"BT /F1 12 Tf 100 700 Td (RUNLEN) Tj ET"))
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "RUNLEN"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 149.332, 94.484], abs=0.01)
    assert d.warnings == []


def test_rle_objstm():
    """T2：ObjStm /RunLengthDecode → 'RLSTM' 照提零告警。"""
    d = _objstm_rle()
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "RLSTM"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 140.668, 94.484], abs=0.01)
    assert d.warnings == []


def test_rle_eod_stops_before_garbage():
    """T3：EOD(128) 后 12 字节垃圾被忽略 → 'RLEOD' 照提零告警。"""
    d = _classic(_rle(b"BT /F1 12 Tf 100 700 Td (RLEOD) Tj ET",
                      tail=b"\xde\xad\xbe\xef" * 3))
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "RLEOD"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 141.34, 94.484], abs=0.01)
    assert d.warnings == []
