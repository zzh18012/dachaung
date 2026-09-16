"""PDF 对象体词法截断/重复/缺值（Round 2023，a 优先级）。

内容流词法（括号/八进制）已由 R2020 锁；对象体（xref 定位后
的 dict/array 词法）截断形态 grep 实证零覆盖。探针 R2023 实证
（好流 '(BODY)' 基线 [100, 82.484, 134.008, 94.484]）：

- **页 dict 未闭合**（值尾无 >>，lexer 撞 endobj/后续对象体）
  → 不崩：零元素 + pdf_no_text_extracted（页树找不到 Page）
- **Kids 数组未闭合**（`[3 0 R /Count 1 >>`）→ **完全恢复**：
  后续键值对被数组吸收为元素、`>>` 兜住 Pages dict，Kids[0]
  仍可达 → 'BODY' 基线 bbox 完整、零告警
- **双字典**（页 dict 后游离 `<< /Extra 1 >>`）→ 第二个 dict
  游离 token 静默丢弃 → 完整恢复
- **键缺值**（`<< /MediaBox >>` 值位撞闭合括号）→ PSBaseParser
  抛 Invalid dictionary construct → ParserError
  pdfplumber_open_failed（exception_type=PdfminerException，
  message 含 "Invalid dictionary construct: [/'MediaBox']"）
- **空对象体**（obj 3 直接 endobj）→ dict_value→{} 无 /Type
  → 页树跳过 → 零文本 + pdf_no_text_extracted
- **/Length null**（edges37 只锁数字错值）→ 流边界丢失 → 零
  文本 + pdf_no_text_extracted

判别式：E2/E3 若 BODY 缺失或告警翻；E1/E5/E6 若 BODY 存活翻；
E4 若异常类型/码/消息三要素任一变翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from app.parsers.base import ParserError

CONTENT = b"BT /F1 12 Tf 100 700 Td (BODY) Tj ET"
GOOD_PAGE = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
             b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>")


def _parse(page_body: bytes, length: bytes | None = None,
           pages_body: bytes | None = None):
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: pages_body or b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: page_body,
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        4: (b"<< /Length " + (length if length is not None
                             else str(len(CONTENT)).encode())
            + b" >>\nstream\n" + CONTENT + b"\nendstream"),
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


def _assert_body(d):
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "BODY"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 134.008, 94.484], abs=0.01)
    assert d.warnings == []


def test_baseline_good_page():
    _assert_body(_parse(GOOD_PAGE))


def test_page_dict_unterminated_silent_empty():
    """页 dict 无 >> → 不崩、零文本 + pdf_no_text_extracted。"""
    d = _parse(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
               b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_kids_array_unterminated_full_recovery():
    """Kids 缺 ] → 后续键值被吸收为元素、页仍可达 → 完整恢复。"""
    _assert_body(_parse(GOOD_PAGE,
                        pages_body=b"<< /Type /Pages /Kids [3 0 R /Count 1 >>"))


def test_double_dict_second_dropped():
    """页 dict 后游离第二 dict → 静默丢弃、完整恢复。"""
    _assert_body(_parse(GOOD_PAGE + b" << /Extra 1 >>"))


def test_key_missing_value_crashes():
    """<< /MediaBox >> 键缺值 → Invalid dictionary construct 异常。"""
    with pytest.raises(ParserError) as ei:
        _parse(b"<< /MediaBox >>")
    assert ei.value.code == "pdfplumber_open_failed"
    assert ei.value.details == {"exception_type": "PdfminerException"}
    assert "Invalid dictionary construct" in str(ei.value)


def test_empty_object_body_no_page():
    """obj 3 空体 → 无 /Type 页树跳过 → 零文本 + pdf_no_text_extracted。"""
    d = _parse(b"")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_length_null_loses_stream():
    """/Length null → 流边界丢失 → 零文本 + pdf_no_text_extracted。"""
    d = _parse(GOOD_PAGE, length=b"null")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]
