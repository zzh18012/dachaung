"""PDF MediaBox 退化形态：pdfplumber 原始 attrs 重读绕过 Letter 回退（Round 2015，a 优先级）。

pdfminer pdfpage.py:189-204 对缺失/null/parse_rect 失败的 MediaBox
有 US Letter 回退（仅 log.warning 进 stderr），但 pdfplumber
Page.__init__（page.py:212-214）用 get_attr("MediaBox") 直接重读
原始 attrs 重新归一，回退被架空。R1943 只锁非零原点 [36 36 612
792]（有效盒），R1587 锁 CropBox 忽略/继承有效盒；退化形态 grep
实证零覆盖（"MediaBox missing"/null 字面/长度≠4 均无夹具）。
探针 R2015 实证：

- **T1 缺键**：页树+页都无 /MediaBox → _normalize_box(None) →
  TypeError 'NoneType' object is not iterable（page.py:166，标
  pragma: nocover）→ ParserError pdfplumber_open_failed
- **T2 null 字面**：PDFSyntaxParser 把 null 解析成 None
  （pdfparser.py:63-65）→ 与 T1 同分支同消息
- **T3 长度 3**：[0 0 900] 数值全过 isinstance 检查、无长度检查
  → box_raw[3] IndexError 'list index out of range'
- **T4 非数值**：[0 0 /A /B] 先死于 pdfminer parse_rect 的
  float(PSLiteral)（parse_rect 只捕 ValueError，utils.py:262-267；
  被包成 PdfminerException 透传消息）——pdfplumber 的
  MalformedPDFException "non-number coordinate" 分支此路径不可达
- **T5 对角反转**：[612 792 0 0] 双层不一致——pdfminer
  parse_rect 不排序，converter 按原点 (612,792) 平移字符
  (-612,-792)；pdfplumber _normalize_box 按规范排序当 Letter →
  不回移 → heading 'A' 成功但 bbox 位移到 [-512, 874.484,
  -503.996, 886.484]，零告警

判别式：T1-T4 若走 Letter 回退正常抽取翻；T5 若 bbox 与正常
Letter 相同（即双层一致）翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.base import ParserError
from app.parsers.fallback_parser import FallbackParser


def _parse(mediabox: str):
    content = b"BT /F1 12 Tf 100 700 Td (A) Tj ET"
    page = (b"<< /Type /Page /Parent 2 0 R" + mediabox.encode()
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
    # ParserError 逃逸时 pdfplumber 句柄未闭（close() re-raise），Windows 锁文件
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        p = Path(td) / "m.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_missing_mediabox_none_not_iterable():
    """T1：页树+页都无 /MediaBox → TypeError 'NoneType' not iterable。"""
    with pytest.raises(ParserError) as ei:
        _parse("")
    assert ei.value.code == "pdfplumber_open_failed"
    assert ei.value.details["exception_type"] == "TypeError"
    assert "NoneType" in ei.value.message


def test_null_mediabox_same_none_branch():
    """T2：/MediaBox null → 解析成 None，与 T1 同分支同消息。"""
    with pytest.raises(ParserError) as ei:
        _parse(" /MediaBox null")
    assert ei.value.code == "pdfplumber_open_failed"
    assert ei.value.details["exception_type"] == "TypeError"
    assert "NoneType" in ei.value.message


def test_len3_mediabox_index_error():
    """T3：[0 0 900] 过数值检查后 box_raw[3] 越界 IndexError。"""
    with pytest.raises(ParserError) as ei:
        _parse(" /MediaBox [0 0 900]")
    assert ei.value.code == "pdfplumber_open_failed"
    assert ei.value.details["exception_type"] == "IndexError"
    assert "index out of range" in ei.value.message


def test_name_coords_psliteral_typeerror():
    """T4：[0 0 /A /B] 死于 pdfminer float(PSLiteral)，非 MalformedPDFException。"""
    with pytest.raises(ParserError) as ei:
        _parse(" /MediaBox [0 0 /A /B]")
    assert ei.value.code == "pdfplumber_open_failed"
    assert ei.value.details["exception_type"] == "PdfminerException"
    assert "PSLiteral" in ei.value.message
    assert "non-number coordinate" not in ei.value.message


def test_reversed_corners_displaced_bbox():
    """T5：[612 792 0 0] pdfminer 平移 vs pdfplumber 排序 → 位移 bbox。"""
    d = _parse(" /MediaBox [612 792 0 0]")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "A"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [-512.0, 874.484, -503.996, 886.484], abs=0.01)
    assert d.warnings == []
