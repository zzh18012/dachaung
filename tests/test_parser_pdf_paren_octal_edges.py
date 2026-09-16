"""PDF 字符串括号不平衡 + 八进制转义边界（Round 2020，a 优先级）。

edges30（R1419）锁了 \351→'Ø'、\(\) 还原、\n→(cid:10)、
反斜杠续行、() 空串；未锁：括号深度/不平衡、八进制越界、
NUL、非法八进制位（grep 实证零覆盖）。探针 R2020 实证：

- **T1 嵌套括号**：`((NEST))` → **'(NEST)'**（规范语义：
  嵌套括号是字符串内容的一部分），bbox [100, 82.484,
  139.996, 94.484]
- **T2 早闭 + 游离 ')'**：`(A)) Tj` → 串在首个 ')' 结束、
  游离 token 静默丢弃、Tj 照常执行 → 'A' 零告警
- **T3 未闭合吞噬**：`((A) Tj ET` → 整个流尾被吞成一个串
  → 无操作符执行 → 零文本 + pdf_no_text_extracted
- **T4 八进制越界**：`(\400)` → pdfminer psparser 解码在
  **extract_words 阶段**抛 "Invalid octal b'400' (256)" →
  双告警：pdfplumber_word_extract_failed（details
  page=1）+ pdf_no_text_extracted
- **T5 NUL**：`(\000)` → (cid:0) 零宽占位（同 hex 串奇数
  位的 (cid:N) 家族）[100, 82.484, 100.0, 94.484]
- **T6 非法八进制位**：`(\8)` → 词法失败 → 零文本 +
  pdf_no_text_extracted

判别式：T1 若出 'NEST'（剥内层括号）翻；T2 若异常/告警
翻；T3 若 'A' 存活翻；T4 若单告警或无告警翻；T5 若空串或
NUL 字面翻；T6 若 '\8' 当 '8' 提取翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _parse(show: bytes):
    content = b"BT /F1 12 Tf 100 700 Td " + show + b" ET"
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
        p = Path(td) / "p.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_nested_parens_are_content():
    """T1：((NEST)) → '(NEST)'（嵌套括号属字符串内容）。"""
    d = _parse(b"((NEST)) Tj")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "(NEST)"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 139.996, 94.484], abs=0.01)
    assert d.warnings == []


def test_early_close_stray_token_dropped():
    """T2：(A)) Tj → 'A' 正常、游离 ')' 静默丢弃。"""
    d = _parse(b"(A)) Tj")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "A"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 108.004, 94.484], abs=0.01)
    assert d.warnings == []


def test_unterminated_swallows_stream():
    """T3：((A) Tj ET → 流尾全吞 → 零文本 + pdf_no_text_extracted。"""
    d = _parse(b"((A) Tj")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_octal_overflow_double_warning():
    """T4：(\400) → extract_words 阶段 Invalid octal → 双告警。"""
    d = _parse(b"(\\400) Tj")
    assert d.elements == []
    assert [w.code for w in d.warnings] == [
        "pdfplumber_word_extract_failed", "pdf_no_text_extracted"]
    assert "Invalid octal" in d.warnings[0].reason
    assert d.warnings[0].details == {"page": 1}


def test_nul_octal_cid_placeholder():
    """T5：(\000) → (cid:0) 零宽占位。"""
    d = _parse(b"(\\000) Tj")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "(cid:0)"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 100.0, 94.484], abs=0.01)
    assert d.warnings == []


def test_bad_octal_digit_no_text():
    """T6：(\8) → 词法失败 → 零文本 + pdf_no_text_extracted。"""
    d = _parse(b"(\\8) Tj")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]
