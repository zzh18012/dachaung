r"""PDF 名字对象 #-hex 转义双侧解码（Round 1976，a 优先级）。

PDF 规范允许名字含 #-hex 转义（资源键/内容流引用/
BaseFont 均可能带）；广扫 tests/ 零匹配。探针 R1976 实证
（pdfminer 词法层解码 #XX，两侧在**解码值**相遇）：

- **N1 资源字典键转义**：/Font << /F#31 5 0 R >>、内容流
  用 /F1 → 'NAMEESC' 照提、宽度指标正常（bbox 宽
  59.34 = 7 字符满宽，BaseFont /Hel#76etica 亦解码）
- **N2 内容流名转义**：字典键 /F1、Tf 用 /F#31 → 同上
- **N3 图像 XObject 键转义**：/XObject << /Im#31 6 0 R >>、
  Do 用 /Im1 → image 元素照放 bbox [200, 492, 300, 592]

判别式：若任一侧不解码 #XX 则资源名不匹配 → 字体缺失
（R1968 GHOSTFONT 零宽形态）或 pdf_no_text_extracted /
图像缺失翻红。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _parse(font_key: bytes, tf_name: bytes, xobj_key: bytes | None = None):
    if xobj_key is not None:
        res = (b"<< /Font << " + font_key + b" 5 0 R >>"
               + b" /XObject << " + xobj_key + b" 6 0 R >> >>")
    else:
        res = b"<< /Font << " + font_key + b" 5 0 R >> >>"
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources " + res + b" /Contents 4 0 R >>"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Hel#76etica >>",
    }
    img = b"\xff\x00\x00"
    body = b"BT " + tf_name + b" 12 Tf 100 700 Td (NAMEESC) Tj ET"
    if xobj_key is not None:
        body += b"\nq 100 0 0 100 200 200 cm /Im1 Do Q"
    objs[4] = (b"<< /Length " + str(len(body)).encode()
               + b" >>\nstream\n" + body + b"\nendstream")
    objs[6] = (b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1"
               b" /ColorSpace /DeviceRGB /BitsPerComponent 8 /Length "
               + str(len(img)).encode() + b" >>\nstream\n" + img + b"\nendstream")
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
        p = Path(td) / "n.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def _assert_text(d):
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "NAMEESC"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 159.336, 94.484], abs=0.01)
    assert d.warnings == []


def test_dict_key_escaped():
    """N1：资源键 /F#31 + 内容流 /F1 → 照提满宽零告警。"""
    _assert_text(_parse(b"/F#31", b"/F1"))


def test_content_name_escaped():
    """N2：字典键 /F1 + Tf 用 /F#31 → 照提满宽零告警。"""
    _assert_text(_parse(b"/F1", b"/F#31"))


def test_image_xobject_key_escaped():
    """N3：/Im#31 键 + Do 用 /Im1 → image 照放、文本照提。"""
    d = _parse(b"/F1", b"/F1", b"/Im#31")
    assert [e.type for e in d.elements] == ["heading", "image"]
    assert d.elements[1].source_locator["bbox"] == pytest.approx(
        [200.0, 492.0, 300.0, 592.0], abs=0.01)
    assert d.warnings == []
