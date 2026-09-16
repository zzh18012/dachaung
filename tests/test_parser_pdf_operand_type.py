"""PDF 内容流操作数类型混淆：Tf/Tj/TJ（Round 2018，a 优先级）。

历史轮内容流操作数全部良构（字符串/数字/名字按规范位型，
edges107 只锁过微字号 0.001 与矩阵极端）；类型混淆 grep 实证
零覆盖。pdfminer PDFContentParser 操作数弹栈经 number_value/
float_value 强转（非 STRICT 静默 0）、字符串操作数 isinstance
检查、操作符弹栈不足整体跳过。探针 R2018 实证（文本
'(TYP)'，基线 '100 700 Td' → bbox [100, 82.484, 123.34,
94.484]）：

- **T1 合法字体 + 关键字字号**：`/F1 nan Tf` → Tf 被跳过
  （无字体设置）→ Tj 无输出 → elements 空 +
  **pdf_no_text_extracted** 结构化告警
- **T2 数字 Tj**：`72 Tj` → 非字符串操作数被拒 → 同空 +
  告警
- **T3 TJ 数组混名字**：`[(N) /Bad] TJ` → 字符串元素照常
  提取、名字元素**静默丢弃**（无 kern、无告警）→ 'N'
  bbox [100, 82.484, 108.664, 94.484]
- **T4 数组 Tj**：`[(SOLO)] Tj` → Tj 拒数组操作数 → 空 +
  告警
- **T5 Tf 操作数颠倒**：`12 /F1 Tf` → 文本**存活**但字号
  强转 0 → bbox 退化为点 [100.0, 92.0, 100.0, 92.0]、零
  告警（与 T1 全空形成机制对照：字体缺失静默回退 vs Tf
  跳过）

判别式：T1/T2/T4 若有文本翻；T3 若 '/Bad' 变文本或告警
翻；T5 若全空或正常宽 bbox 翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _parse(content: bytes):
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        4: (b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"),
    }
    out = bytearray(b"%PDF-1.5\n")
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
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        p = Path(td) / "t.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_keyword_font_size_skips_tf():
    """T1：/F1 nan Tf → 无字体 → 零文本 + 结构化告警。"""
    d = _parse(b"BT /F1 nan Tf 100 700 Td (TYP) Tj ET")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_numeric_tj_rejected():
    """T2：72 Tj → 非字符串操作数 → 零文本 + 告警。"""
    d = _parse(b"BT /F1 12 Tf 100 700 Td 72 Tj ET")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_tj_array_name_element_dropped():
    """T3：[(N) /Bad] TJ → 字符串出 'N'、名字静默丢弃零告警。"""
    d = _parse(b"BT /F1 12 Tf 100 700 Td [(N) /Bad] TJ ET")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "N"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 108.664, 94.484], abs=0.01)
    assert d.warnings == []


def test_array_operand_tj_rejected():
    """T4：[(SOLO)] Tj → Tj 拒数组操作数 → 零文本 + 告警。"""
    d = _parse(b"BT /F1 12 Tf 100 700 Td [(SOLO)] Tj ET")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_swapped_tf_operands_point_bbox():
    """T5：12 /F1 Tf → 文本存活但字号 0 → 点 bbox 零告警。"""
    d = _parse(b"BT 12 /F1 Tf 100 700 Td (TYP) Tj ET")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "TYP"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 92.0, 100.0, 92.0], abs=0.01)
    assert d.warnings == []
