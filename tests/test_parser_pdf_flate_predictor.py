r"""PDF FlateDecode + PNG Predictor 12（Up 子滤波）流解码（Round 1975，a 优先级）。

真实世界 Word/LaTeX 产 PDF 1.5+ 常用 predictor 压缩 objstm/
xrefstm；广扫 tests/ 零 Predictor 匹配（R1963 锁 plain Flate
ObjStm、R1945 锁图像编码垃圾，均不含 DecodeParms 预测器路
径）。pdfminer 解码侧 utils.apply_png_predictor（Up=filter 2，
stride=columns+1，尾行允许部分）。探针 R1975 实证（编码侧
镜像 Up 差分 + zlib）：

- **P1 objstm predictor**（/Columns 16，xref 流 plain Flate）
  → 'PREDICT' 照提、零告警
- **P2 xref 流 predictor**（/Columns 7 = /W 行宽，objstm
  plain Flate）→ 同上
- **P3 双流 predictor** → 同上

判别式：若解码侧忽略 DecodeParms（差分字节直当明文）则
P1/P3 条目/对象乱码 → ParserError 或 pdf_no_text_extracted
翻红；若仅支持 TIFF predictor 2 则同红。
"""

from __future__ import annotations

import tempfile
import zlib
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

OBJS = {
    1: b"<< /Type /Catalog /Pages 2 0 R >>",
    2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
        b" /Resources << /Font << /F1 6 0 R >> >> /Contents 4 0 R >>"),
    6: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
}


def _up_encode(data: bytes, columns: int) -> bytes:
    out = bytearray()
    prev = bytes(columns)
    for i in range(0, len(data), columns):
        row = data[i:i + columns]
        out.append(2)
        out.extend((row[j] - prev[j]) & 0xFF for j in range(len(row)))
        prev = row + bytes(columns - len(row))
    return bytes(out)


def _stm_dict(extra: bytes, length: int, pred: bool, columns: int) -> bytes:
    s = extra + b" /Length " + str(length).encode()
    if pred:
        s += (b" /DecodeParms << /Predictor 12 /Colors 1 /Columns "
              + str(columns).encode() + b" /BitsPerComponent 8 >>")
    return s + b" >>"


def _build(mode: str):
    body = b"BT /F1 12 Tf 100 700 Td (PREDICT) Tj ET"
    cs4 = (b"<< /Length " + str(len(body)).encode()
           + b" >>\nstream\n" + body + b"\nendstream")

    order = sorted(OBJS)
    header = b""
    payload = b""
    for oid in order:
        header += f"{oid} ".encode() + str(len(payload)).encode() + b" "
        payload += OBJS[oid] + b" "
    objstm_pred = mode in ("objstm", "both")
    objstm_data = zlib.compress(
        _up_encode(header + payload, 16) if objstm_pred else header + payload)

    out = bytearray(b"%PDF-1.5\n")
    offsets: dict[int, int] = {}
    offsets[4] = len(out)
    out += b"4 0 obj\n" + cs4 + b"\nendobj\n"

    objstm_extra = (b"<< /Type /ObjStm /N " + str(len(order)).encode()
                    + b" /First " + str(len(header)).encode()
                    + b" /Filter /FlateDecode")
    offsets[5] = len(out)
    out += (b"5 0 obj\n"
            + _stm_dict(objstm_extra, len(objstm_data), objstm_pred, 16)
            + b"\nstream\n" + objstm_data + b"\nendstream\nendobj\n")

    xref_off = len(out)
    offsets[7] = xref_off
    entries = [bytes([0]) + (0).to_bytes(4, "big") + (65535).to_bytes(2, "big")]
    for oid in range(1, 8):
        if oid in (1, 2, 3, 6):
            idx = order.index(oid)
            entries.append(bytes([2]) + (5).to_bytes(4, "big")
                           + idx.to_bytes(2, "big"))
        else:
            entries.append(bytes([1]) + offsets[oid].to_bytes(4, "big")
                           + (0).to_bytes(2, "big"))
    xraw = b"".join(entries)
    xpred = mode in ("xrefstm", "both")
    xdata = zlib.compress(_up_encode(xraw, 7) if xpred else xraw)
    out += (b"7 0 obj\n"
            + _stm_dict(b"<< /Type /XRef /Size 8 /W [1 4 2] /Root 1 0 R"
                        b" /Filter /FlateDecode", len(xdata), xpred, 7)
            + b"\nstream\n" + xdata + b"\nendstream\nendobj\n")
    out += b"startxref\n" + str(xref_off).encode() + b"\n%%EOF"

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "p.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def _assert_extracted(d):
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "PREDICT"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 152.668, 94.484], abs=0.01)
    assert d.warnings == []


def test_objstm_predictor():
    """P1：objstm Flate+Predictor 12 → 'PREDICT' 照提零告警。"""
    _assert_extracted(_build("objstm"))


def test_xrefstm_predictor():
    """P2：xref 流 Flate+Predictor 12 → 照提零告警。"""
    _assert_extracted(_build("xrefstm"))


def test_both_streams_predictor():
    """P3：双流 predictor → 照提零告警。"""
    _assert_extracted(_build("both"))
