r"""PDF 经典 xref 偏移损伤——条目错=静默全丢 / startxref 错=全恢复（Round 1972，a 优先级）。

既有 xref 测试全合法偏移（edges52 增量 /Prev、edges103 线
性化）；广扫 wrong offset/错位零匹配。真实世界截断/拼接文
件常见偏移漂移。探针 R1972 实证（pdfminer 恢复路径不对
称）：

- **X1 条目偏移 +10 漂移**（表结构合法、指向对象内部垃
  圾位）→ **无恢复**：零元素 + 仅泛化告警
  `pdf_no_text_extracted`——PDFXRefFallback 不接管（经典
  表语法合法即被信任，逐对象解析失败静默丢弃）
- **X2 条目偏移全归零** → 同 X1 静默全丢
- **X3 startxref 指向内容流中间**（130）→ **全恢复**：
  PDFXRef.load 失败 → PDFXRefFallback 全文件扫 "N 0 obj"
  重建 → 'XREFDMG' 照提、bbox 正常、**零告警**

判别式：若 pdfminer 对条目错位也触发 fallback 扫描则
X1/X2 恢复翻红；若 startxref 错直接判死则 X3 变
ParserError 翻红。
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _good() -> bytes:
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    body = b"BT /F1 12 Tf 100 700 Td (XREFDMG) Tj ET"
    objs[4] = (b"<< /Length " + str(len(body)).encode()
               + b" >>\nstream\n" + body + b"\nendstream")
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


def _mangle(kind: str) -> bytes:
    data = _good()
    if kind == "shift":
        return re.sub(
            rb"(\d{10}) 00000 n",
            lambda mo: ("%010d 00000 n" % (int(mo.group(1)) + 10)).encode(),
            data)
    if kind == "zero":
        return re.sub(rb"\d{10} 00000 n", b"0000000000 00000 n", data)
    return re.sub(rb"startxref\n\d+", b"startxref\n130", data)


def _parse(kind: str):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.pdf"
        p.write_bytes(_mangle(kind))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_shifted_entries_silent_total_loss():
    """X1：条目 +10 漂移 → 零元素 + pdf_no_text_extracted。"""
    d = _parse("shift")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_zeroed_entries_silent_total_loss():
    """X2：条目偏移全零 → 同 X1 静默全丢。"""
    d = _parse("zero")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_wrong_startxref_full_fallback_recovery():
    """X3：startxref 指向内容流中间 → fallback 全文件扫描
    重建 → 照提零告警。"""
    d = _parse("startxref")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "XREFDMG"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 160.0, 94.484], abs=0.01)
    assert d.warnings == []
