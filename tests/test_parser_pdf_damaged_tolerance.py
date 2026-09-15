r"""PDF 受损/退化内容容差（Round 1968，a 优先级）。

既有测试全部完好的规范文件（广扫 undeclared/corrupt/
损坏 parser 侧零匹配）；真实世界损坏常见三类。探针
R1968 实证：

- **D1 未声明字体**（Tf /F9，Resources 只有 /F1）→ 文本
  'GHOSTFONT' 照提但**零宽 bbox** [100, 80, 100, 92]——
  pdfminer 回退字体无度量、字宽全 0、x1 塌缩到 x0；零宽
  文本**不被丢弃**（:331 零宽剔除仅图片路径）；stderr 有
  pdfminer FontBBox 日志但 warnings 列表为空
- **D2 /Contents 数组 [好流, 坏 Flate]**（zlib 头+垃圾）→
  坏流解压错误被 pdfminer 静默吞掉，好流文本 'GOODTEXT'
  存活、零告警、无元素残留——部分存活语义
- **D3 负坐标文本**（Td -100 -50）→ bbox [-100, 832.484,
  -39.316, 844.484] 原样透传——无页面裁剪、无告警

判别式：若文本路径加零宽剔除则 D1 元素消失翻红；若坏流
解压错误上抛则 D2 变 ParserError 翻红；若加页面边界裁剪
则 D3 元素消失/夹紧翻红。
"""

from __future__ import annotations

import tempfile
import zlib
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _build(streams: list[bytes], flate: list[bool]) -> bytes:
    n = len(streams)
    font_oid = 4 + n
    payload = [zlib.compress(s) if f else s for s, f in zip(streams, flate)]
    kids = b" ".join(f"{4 + i} 0 R".encode() for i in range(n))
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 " + str(font_oid).encode()
            + b" 0 R >> >> /Contents [" + kids + b"] >>"),
        font_oid: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for i, (data, f) in enumerate(zip(payload, flate)):
        filt = b" /Filter /FlateDecode" if f else b""
        objs[4 + i] = (b"<< /Length " + str(len(data)).encode() + filt
                       + b" >>\nstream\n" + data + b"\nendstream")
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
    return bytes(out)


def _parse(streams: list[bytes], flate: list[bool]):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "d.pdf"
        p.write_bytes(_build(streams, flate))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_undeclared_font_zero_width_bbox_kept():
    """D1：Tf /F9（未声明）→ 文本照提、零宽 bbox [100, 80,
    100, 92]（字宽全 0 塌缩）、元素不丢弃、warnings 空。"""
    d = _parse([b"BT /F9 12 Tf 100 700 Td (GHOSTFONT) Tj ET"], [False])
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "GHOSTFONT"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 100.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_corrupt_flate_element_partial_survival():
    """D2：/Contents [好流, 坏 Flate] → 坏流静默吞、好流
    'GOODTEXT' 存活、零告警。"""
    d = _parse([b"BT /F1 12 Tf 100 700 Td (GOODTEXT) Tj ET",
                b"\x78\x9c\x00\x01\x02garbage-not-zlib"],
               [False, True])
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "GOODTEXT"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 167.344, 94.484], abs=0.01)
    assert d.warnings == []


def test_negative_coordinates_bbox_passthrough():
    """D3：Td -100 -50 → bbox [-100, 832.484, -39.316,
    844.484] 原样透传（负 x/超页 y 均不裁剪）、零告警。"""
    d = _parse([b"BT /F1 12 Tf -100 -50 Td (NEGATIVE) Tj ET"], [False])
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "NEGATIVE"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [-100.0, 832.484, -39.316, 844.484], abs=0.01)
    assert d.warnings == []
