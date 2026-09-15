r"""PDF 对象别名/共享引用（Round 1969，a 优先级）。

生成器常共享对象（同内容流多处引用/同 Form 多次 Do）。
既有测试每流唯一引用（广扫 [4 0 R 4 0 R]/共享 contents 零
匹配）。探针 R1969 实证：

- **A1 /Contents [4 0 R 4 0 R] 同流两次**（同位重叠）→
  pdfplumber 字符按 x 归并 → 'DDUUPP' **字符交错双写**、
  bbox 宽 25.332 与单份 'DUP' 相同（重复字符占同 x 槽，
  几何不变）
- **A2 两页共享 /Contents 4 0 R** → 'SHARED' 在页 1 与页
  2 各提取一次、bbox 逐位一致
- **A3 Form XObject 两次 Do**（cm 平移 y 700/300）→ 同页
  两个独立 'FORMTXT' 元素（top 82.484 / 482.484，恰差
  400）

判别式：若按对象去重则 A1 变 'DUP'/A2 单页翻红；若按字
符坐标去重（重叠合并）则 A1 变 'DUP' 翻红；A3 锁 Form 重
入非缓存语义。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

_FONT = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"


def _cs(body: bytes) -> bytes:
    return (b"<< /Length " + str(len(body)).encode()
            + b" >>\nstream\n" + body + b"\nendstream")


def _wrap(objs: dict[int, bytes], root_kids: list[int]) -> bytes:
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[2] = (b"<< /Type /Pages /Kids ["
               + b" ".join(f"{k} 0 R".encode() for k in root_kids)
               + b"] /Count " + str(len(root_kids)).encode() + b" >>")
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
    return bytes(out)


def _parse(variant: str):
    if variant == "dup_contents":
        objs = {
            3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
                b" /Resources << /Font << /F1 5 0 R >> >>"
                b" /Contents [4 0 R 4 0 R] >>"),
            4: _cs(b"BT /F1 12 Tf 100 700 Td (DUP) Tj ET"),
            5: _FONT,
        }
        kids = [3]
    elif variant == "shared_pages":
        page = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
                b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>")
        objs = {3: page, 4: _cs(b"BT /F1 12 Tf 100 700 Td (SHARED) Tj ET"),
                5: _FONT, 6: page}
        kids = [3, 6]
    else:  # form_twice
        form_body = b"BT /F1 12 Tf 0 0 Td (FORMTXT) Tj ET"
        objs = {
            3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
                b" /Resources << /Font << /F1 5 0 R >>"
                b" /XObject << /Fx 6 0 R >> >> /Contents 4 0 R >>"),
            4: _cs(b"q 1 0 0 1 100 700 cm /Fx Do Q\n"
                   b"q 1 0 0 1 100 300 cm /Fx Do Q"),
            5: _FONT,
            6: (b"<< /Type /XObject /Subtype /Form /BBox [0 0 200 20]"
                b" /Resources << /Font << /F1 5 0 R >> >> /Length "
                + str(len(form_body)).encode()
                + b" >>\nstream\n" + form_body + b"\nendstream"),
        }
        kids = [3]
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "a.pdf"
        p.write_bytes(_wrap(objs, kids))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_duplicated_contents_reference_interleaves():
    """A1：/Contents [4 0 R 4 0 R] → 'DDUUPP' 字符交错、bbox
    宽 25.332 与单份 'DUP' 相同、零告警。"""
    d = _parse("dup_contents")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "DDUUPP"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 125.332, 94.484], abs=0.01)
    assert d.warnings == []


def test_shared_contents_across_pages():
    """A2：两页共享 /Contents → 'SHARED' 页 1/2 各一次、bbox
    逐位一致。"""
    d = _parse("shared_pages")
    assert [(e.source_locator["page"], e.content) for e in d.elements] == [
        (1, "SHARED"), (2, "SHARED")]
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        d.elements[1].source_locator["bbox"], abs=0.001)
    assert d.warnings == []


def test_form_xobject_reinvocation_two_elements():
    """A3：Form 两次 Do（y 700/300）→ 同页两个独立元素、
    top 恰差 400。"""
    d = _parse("form_twice")
    assert [e.content for e in d.elements] == ["FORMTXT", "FORMTXT"]
    assert all(e.source_locator["page"] == 1 for e in d.elements)
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 157.996, 94.484], abs=0.01)
    assert d.elements[1].source_locator["bbox"] == pytest.approx(
        [100.0, 482.484, 157.996, 494.484], abs=0.01)
    assert d.warnings == []
