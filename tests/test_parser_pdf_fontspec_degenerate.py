"""PDF /Font 条目 spec 退化形态（Round 2022，a 优先级）。

get_font（pdfinterp.py:212-250）分派路径 grep 实证零覆盖
（edges35 只锁未注册名 /F9 的 fontmap 缺失）。探针 R2022 实证
（好字体 '(FONT)' 基线 [100, 82.484, 132.664, 94.484]）：

- **六种垃圾形态同归零宽框**：spec 数字 42 / null / 空字典
  << >> / 未知 Subtype /Nope（else 分支照样落 Type1，源码注释
  "this is so wrong!"）、/Font 容器本身 42、/Resources null
  → 'FONT' 照出，bbox [100, 80, 100, 92]（宽 0、高恰 12、
  无 82.484 基线上延）、零告警。前四者走 dict_value→{} →
  默认 Type1 "Unknown" 字体（fontmap 命中但无度量）；后两者
  fontmap 缺失——机制不同、观测收敛（与 edges35 未注册名
  [72,80,72,92] 同一零宽公式）
- **Type0 缺 DescendantFonts**：spec["DescendantFonts"] 直接
  KeyError（非 .get）→ extract_words 阶段双告警
  pdfplumber_word_extract_failed（reason 含 "'DescendantFonts'"，
  details page=1）+ pdf_no_text_extracted
- **Type0 空数组 DescendantFonts**：`assert dfonts`（裸断言，
  非 STRICT 分支）→ AssertionError 空 str → 同双告警但 reason
  尾部为空串

判别式：垃圾形态若零宽框翻（宽≠0 或 top≠80 或告警出现翻）；
E7 若 reason 不含 DescendantFonts 翻；E8 若 reason 非空串翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

CONTENT = b"BT /F1 12 Tf 100 700 Td (FONT) Tj ET"


def _parse(resources: bytes):
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources " + resources
            + b" /Contents 4 0 R >>"),
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
        p = Path(td) / "f.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_baseline_good_font():
    """/F1 5 0 R 正常 Type1 → 'FONT' 完整宽度 + 零告警。"""
    d = _parse(b"<< /Font << /F1 5 0 R >> >>")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "FONT"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 132.664, 94.484], abs=0.01)
    assert d.warnings == []


@pytest.mark.parametrize("resources", [
    b"<< /Font << /F1 42 >> >>",
    b"<< /Font << /F1 null >> >>",
    b"<< /Font << /F1 << >> >> >>",
    b"<< /Font << /F1 << /Type /Font /Subtype /Nope >> >> >>",
    b"<< /Font 42 >>",
    b"null",
], ids=["spec-number", "spec-null", "spec-empty-dict",
        "spec-unknown-subtype", "font-container-junk", "resources-null"])
def test_junk_fontspec_zero_width_text(resources):
    """六种垃圾形态 → 'FONT' 存活、零宽框 [100,80,100,92]、零告警。"""
    d = _parse(resources)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "FONT"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 100.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_type0_missing_descendants_keyerror():
    """Type0 缺 DescendantFonts → KeyError 双告警（reason 含键名）。"""
    d = _parse(b"<< /Font << /F1 << /Type /Font /Subtype /Type0 >> >> >>")
    assert d.elements == []
    assert [w.code for w in d.warnings] == [
        "pdfplumber_word_extract_failed", "pdf_no_text_extracted"]
    assert "'DescendantFonts'" in d.warnings[0].reason
    assert d.warnings[0].details == {"page": 1}


def test_type0_empty_descendants_assertion():
    """Type0 DescendantFonts 空数组 → 裸 assert → AssertionError 空串。"""
    d = _parse(b"<< /Font << /F1 << /Type /Font /Subtype /Type0"
               b" /DescendantFonts [] >> >> >>")
    assert d.elements == []
    assert [w.code for w in d.warnings] == [
        "pdfplumber_word_extract_failed", "pdf_no_text_extracted"]
    assert not d.warnings[0].reason.split(":")[-1].strip()
    assert d.warnings[0].details == {"page": 1}
