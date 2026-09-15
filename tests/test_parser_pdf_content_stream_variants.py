r"""PDF 内容流结构变体——Flate / 数组拼接 / 状态跨流持续（Round 1962，a 优先级）。

既有测试全部单一裸 stream（广扫 Flate / Contents [ / 流数组
零匹配——zlib 仅用于 PNG IDAT）。真实 PDF 几乎必 Flate、
大页常拆数组。探针 R1962 实证（pdfminer 数组按序拼接、
Flate 透明解压、**图形/文本状态跨数组元素持续**——规范行
为）：

- **F1 FlateDecode 单流**：'FLATED' 照提、bbox 与裸流逐位
  一致
- **F2 数组劈开文本对象**：s1='...Td' + s2=' (ARRAY) Tj
  ET'（算子边界劈）→ 'ARRAY' 连贯；**字符串内部劈**（流尾
  \n 入串）→ 'ARR(cid:10)AY'——流界空白在开放字符串内成
  字符（规范行为，cid 10 即 LF）
- **F3 q/cm 跨流（双 Flate）**：s1 设 cm 平移 10、s2 写字
  → bbox x0 = 72+10 = **82.0**（状态持续非重置）

判别式：若数组元素改独立解析（每流重置状态）则 F3 bbox
回 72 翻红；若流界空白被剔出字符串则 F2b 变 'ARRAY' 翻红。
"""

from __future__ import annotations

import tempfile
import zlib
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _build(streams: list[bytes], flate: bool) -> bytes:
    n = len(streams)
    font_oid = 4 + n
    if flate:
        streams = [zlib.compress(s) for s in streams]
    kids = b" ".join(f"{4 + i} 0 R".encode() for i in range(n))
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 " + str(font_oid).encode()
            + b" 0 R >> >> /Contents [" + kids + b"] >>"),
        font_oid: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    filt = b" /Filter /FlateDecode" if flate else b""
    for i, s in enumerate(streams):
        objs[4 + i] = (b"<< /Length " + str(len(s)).encode() + filt
                       + b" >>\nstream\n" + s + b"\nendstream")
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


def _parse(tmp_path: Path, streams: list[bytes], flate: bool):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "s.pdf"
        p.write_bytes(_build(streams, flate))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_flate_single_stream_identical(tmp_path):
    """F1：FlateDecode 单流 → 与裸流逐位一致的 bbox。"""
    d = _parse(tmp_path, [b"BT /F1 12 Tf 72 700 Td (FLATED) Tj ET"], True)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "FLATED"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [72.0, 82.484, 118.008, 94.484], abs=0.01)
    assert d.warnings == []


def test_array_split_text_object(tmp_path):
    """F2：数组劈文本对象——算子边界劈 'ARRAY'；字符串内劈
    'ARR(cid:10)AY'（流界 \n 入串成字符）。"""
    clean = _parse(tmp_path, [b"BT /F1 12 Tf 72 700 Td",
                              b" (ARRAY) Tj ET"], False)
    assert clean.elements[0].content == "ARRAY"
    instr = _parse(tmp_path, [b"BT /F1 12 Tf 72 700 Td (ARR",
                              b"AY) Tj ET"], False)
    assert instr.elements[0].content == "ARR(cid:10)AY"
    assert instr.warnings == []


def test_graphics_state_across_streams(tmp_path):
    """F3：q/cm 在流 1、文字在流 2（双 Flate）→ 平移持续
    bbox x0=82.0。"""
    d = _parse(tmp_path, [b"q 1 0 0 1 10 0 cm",
                          b"BT /F1 12 Tf 72 700 Td (SHIFTED) Tj ET Q"], True)
    assert d.elements[0].content == "SHIFTED"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [82.0, 82.484, 133.336, 94.484], abs=0.01)
    assert d.warnings == []
