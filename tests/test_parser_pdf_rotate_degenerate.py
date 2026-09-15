"""PDF /Rotate 退化值：负数/超 360/实数/名字/字符串（Round 2016，a 优先级）。

双层消费图：pdfminer pdfpage.py:76
`rotate=(int_value(Rotate,0)+360)%360`——非 int **静默归 0**
（pdftypes.py:148-155 非 STRICT 分支）；pdfinterp.py:1355-1359
只对精确 90/180/270 施加矩阵。pdfplumber page.py:211-212
`rotation = get_attr("Rotate",0)%360` 用**原始值**取模——
PSLiteral（str 子类）% 360 → TypeError；bytes（PDF 字符串）%
360 → TypeError。R1451（edges57）已锁 90/180/270 正字面值、
45 静默忽略、非零原点交互；负值/>360/实数/名字/字符串 grep
实证零覆盖。探针 R2016 实证（文本 '(ROT)' 基线 bbox
[100, 82.484, 125.332, 94.484]）：

- **T1 /Rotate -90**：(−90+360)%360=270 双层一致 → 270 语义：
  字符序倒序 'TOR'，bbox [82.484, 486.668, 94.484, 512.0]
- **T2 /Rotate 450**：450%360=90 → 90 语义：文本保留 'ROT'
  竖条 bbox [697.516, 100.0, 709.516, 125.332]
- **T3 /Rotate 90.5**：pdfminer int_value 归 0 + pdfplumber
  90.5∉[90,270] 不换宽高 → 与基线**逐位一致**
- **T4 /Rotate /A**：pdfplumber 'PSLiteral' % int TypeError →
  ParserError pdfplumber_open_failed
- **T5 /Rotate (90)**：PDF 字符串 bytes % 360 → bytes
  formatting TypeError → ParserError

判别式：T1/T2 若当成 0 正常水平抽取翻；T3 若旋转翻；T4/T5
若不崩翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.base import ParserError
from app.parsers.fallback_parser import FallbackParser


def _parse(extra: str):
    content = b"BT /F1 12 Tf 100 700 Td (ROT) Tj ET"
    page = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            + extra.encode()
            + b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>")
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: page,
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
    # ParserError 逃逸时 pdfplumber 句柄未闭，Windows 锁临时文件
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        p = Path(td) / "r.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_neg90_normalized_to_270():
    """T1：-90 → 270 语义：倒序 'TOR' + 270 bbox。"""
    d = _parse(" /Rotate -90")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "TOR"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [82.484, 486.668, 94.484, 512.0], abs=0.01)
    assert d.warnings == []


def test_450_normalized_to_90():
    """T2：450%360=90 → 90 语义：竖条 bbox 文本不倒序。"""
    d = _parse(" /Rotate 450")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "ROT"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [697.516, 100.0, 709.516, 125.332], abs=0.01)
    assert d.warnings == []


def test_float_rotate_silently_zeroed():
    """T3：90.5 → pdfminer int_value 归 0，与无旋转基线逐位一致。"""
    d = _parse(" /Rotate 90.5")
    baseline = _parse("")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "ROT"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 125.332, 94.484], abs=0.01)
    assert (d.elements[0].source_locator["bbox"]
            == pytest.approx(
                baseline.elements[0].source_locator["bbox"], abs=0.001))
    assert d.warnings == []


def test_name_rotate_crashes():
    """T4：/Rotate /A → PSLiteral % int TypeError → ParserError。"""
    with pytest.raises(ParserError) as ei:
        _parse(" /Rotate /A")
    assert ei.value.code == "pdfplumber_open_failed"
    assert ei.value.details["exception_type"] == "TypeError"
    assert "%" in ei.value.message


def test_string_rotate_crashes():
    """T5：/Rotate (90) → bytes % 360 TypeError → ParserError。"""
    with pytest.raises(ParserError) as ei:
        _parse(" /Rotate (90)")
    assert ei.value.code == "pdfplumber_open_failed"
    assert ei.value.details["exception_type"] == "TypeError"
    assert "bytes formatting" in ei.value.message
