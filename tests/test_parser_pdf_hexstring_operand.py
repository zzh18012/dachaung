"""PDF 十六进制字符串文本操作数退化形态（Round 2019，a 优先级）。

PDF 规范允许 `<hex>` 作字符串（Tj 操作数）；历史夹具全部用
(...) 字面串（grep 实证 hex 串零覆盖，edges30 只锁 () 转义）。
pdfminer PSBaseParser hexstring token 化实测落锁（探针
R2019，基线 '(HX)' → [100, 82.484, 116.668, 94.484]）：

- **T1 hex 等价**：`<4858>` → 与字面串 '(HX)' 逐位同 bbox
- **T2 内嵌空白**：`<48 58>` → 同 T1（空白被剥）
- **T3 奇数位**：`<4>` → **(cid:4) 零宽占位**（取半字节值
  4 无字形 → (cid:N) + 宽 0，**不是**规范"尾补 0"的 0x40
  '@'），bbox [100, 82.484, 100.0, 94.484]
- **T4 非法 hex 字符**：`<4G>` → token 化失败 → Tj 无有效
  操作数 → 零文本 + pdf_no_text_extracted
- **T5 空串**：`<>` → 空字符串 show → 零文本 + 同告警
- **T6 小写 hex**：`<6878>` → 'hx' [100, 82.484, 112.672,
  94.484]

判别式：T1/T2 若 bbox 异于字面基线翻；T3 若出 '@' 或异常
翻；T4/T5 若有文本翻；T6 若大写 'HX' 翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _parse(show_op: bytes):
    content = b"BT /F1 12 Tf 100 700 Td " + show_op + b" Tj ET"
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
        p = Path(td) / "h.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_hex_equivalent_to_literal():
    """T1：<4858> 与 '(HX)' 同文本同 bbox。"""
    d = _parse(b"<4858>")
    lit = _parse(b"(HX)")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "HX"
    assert (d.elements[0].source_locator["bbox"]
            == pytest.approx(
                lit.elements[0].source_locator["bbox"], abs=0.001))
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 116.668, 94.484], abs=0.01)
    assert d.warnings == []


def test_hex_internal_whitespace_stripped():
    """T2：<48 58> 内嵌空白被剥，与 T1 逐位同。"""
    d = _parse(b"<48 58>")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "HX"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 116.668, 94.484], abs=0.01)
    assert d.warnings == []


def test_odd_hex_digit_cid_placeholder():
    """T3：<4> 奇数位 → (cid:4) 零宽占位，不是补零 '@'。"""
    d = _parse(b"<4>")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "(cid:4)"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 100.0, 94.484], abs=0.01)
    assert d.warnings == []


def test_invalid_hex_char_no_text():
    """T4：<4G> → token 化失败 → 零文本 + pdf_no_text_extracted。"""
    d = _parse(b"<4G>")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_empty_hexstring_no_text():
    """T5：<> 空串 → 零文本 + 同告警。"""
    d = _parse(b"<>")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_lowercase_hex():
    """T6：<6878> → 'hx'。"""
    d = _parse(b"<6878>")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "hx"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 112.672, 94.484], abs=0.01)
    assert d.warnings == []
