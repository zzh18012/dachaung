"""PDF /Contents 非流退化形态与混合数组（Round 2021，a 优先级）。

/Contents 期望流引用或流引用数组（pdfpage._parse_contents
resolve1）；非流形态 grep 实证零覆盖（edges20 等只锁合法数组
形态）。探针 R2021 实证（好流 '(BODY)' 基线 [100, 82.484,
134.008, 94.484]）：

- **纯垃圾形态全塌缩**：数字 42 / 字符串 (str) / 空数组 []
  / 悬空引用 9 0 R / null / 字典 << >> 六形态 → 同归零文本 +
  pdf_no_text_extracted（无 BODY、无异常）
- **混合数组垃圾静默跳过**：`[4 0 R 42]`、`[9 0 R 4 0 R]`、
  `[4 0 R null]` → 好流**完整提取** 'BODY' 基线 bbox、**零
  告警**——数组元素按位消费，非流/悬空元素无声丢弃（与裸
  悬空全空形成对照）

判别式：纯垃圾若 BODY 存活或异常翻；混合若 BODY 缺失/告警
翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

CONTENT = b"BT /F1 12 Tf 100 700 Td (BODY) Tj ET"


def _parse(contents: bytes):
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents "
            + contents + b" >>"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        4: (b"<< /Length " + str(len(CONTENT)).encode()
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
        p = Path(td) / "c.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


@pytest.mark.parametrize("contents", [
    b"42",
    b"(str)",
    b"[]",
    b"9 0 R",
    b"null",
    b"<< >>",
], ids=["number", "string", "empty-array", "dangling", "null", "dict"])
def test_pure_junk_contents_no_text(contents):
    """纯垃圾 /Contents 六形态 → 零文本 + pdf_no_text_extracted。"""
    d = _parse(contents)
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def _assert_body(d):
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "BODY"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 134.008, 94.484], abs=0.01)
    assert d.warnings == []


def test_mixed_array_number_junk_skipped():
    """[4 0 R 42] → 好数据流完整提取、数字元素静默丢弃。"""
    _assert_body(_parse(b"[4 0 R 42]"))


def test_mixed_array_dangling_before():
    """[9 0 R 4 0 R] → 前置悬空引用跳过、好流照常。"""
    _assert_body(_parse(b"[9 0 R 4 0 R]"))


def test_mixed_array_null_after():
    """[4 0 R null] → 尾随 null 跳过、好流照常。"""
    _assert_body(_parse(b"[4 0 R null]"))
