r"""PDF 文本渲染模式 Tr 3（不可见）照提（Round 1977，a 优先级）。

扫描件 OCR PDF 的识别文本层几乎全用 `3 Tr` 叠加在图像上；
广扫 tests/ 零 `3 Tr`/render mode 匹配。探针 R1977 实证
（pdfplumber chars 不过滤渲染模式，不可见与可见**完全同
权**）：

- **I1 单一 3 Tr 文本** → 'GHOSTOCR' 照提、bbox 满宽正常、
  零告警
- **I2 可见+不可见混排**（0 Tr / 3 Tr 两段）→ 两段都提、
  文档序 VISIBLE→INVISBLE、bbox 各自独立
- **I3 整页仅不可见文本**（纯 OCR 层形态）→ 照提，**非**
  pdf_no_text_extracted——空文本判定不看不可见性

判别式：若 chars 按渲染模式过滤则 I1/I3 零元素 +
pdf_no_text_extracted 翻红；若引入 invisibility 标记告警则
warnings 断言翻红。
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
    }
    objs[4] = (b"<< /Length " + str(len(content)).encode()
               + b" >>\nstream\n" + content + b"\nendstream")
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
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_invisible_only_extracted():
    """I1：单一 3 Tr → 'GHOSTOCR' 照提满宽、零告警。"""
    d = _parse(b"BT /F1 12 Tf 3 Tr 100 700 Td (GHOSTOCR) Tj ET")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "GHOSTOCR"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 169.336, 94.484], abs=0.01)
    assert d.warnings == []


def test_mixed_visible_invisible_both_extracted():
    """I2：0 Tr + 3 Tr 两段 → 都提、文档序、bbox 独立。"""
    d = _parse(b"BT /F1 12 Tf 0 Tr 100 700 Td (VISIBLE) Tj ET\n"
               b"BT /F1 12 Tf 3 Tr 100 500 Td (INVISBLE) Tj ET")
    assert [e.content for e in d.elements] == ["VISIBLE", "INVISBLE"]
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 145.36, 94.484], abs=0.01)
    assert d.elements[1].source_locator["bbox"] == pytest.approx(
        [100.0, 282.484, 154.024, 294.484], abs=0.01)
    assert d.warnings == []


def test_full_ocr_layer_page_not_empty():
    """I3：整页仅 3 Tr（纯 OCR 层）→ 照提，非
    pdf_no_text_extracted。"""
    d = _parse(b"BT /F1 12 Tf 3 Tr 72 700 Td (OCR LAYER TEXT) Tj ET")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "OCR LAYER TEXT"
    assert d.warnings == []
