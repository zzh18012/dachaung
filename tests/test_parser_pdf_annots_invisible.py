r"""PDF /Annots 注释文本全形态静默不可见（Round 1973，a 优先级）。

真实世界审阅/批注 PDF（律师标记、评审意见）文本多在 /Annots；
广扫 tests/test_parser_pdf*.py 零 /Annots 匹配（evaluation 侧
annotation metrics 是另一语义）。探针 R1973 实证
（pdfplumber page.extract_text 只走页面内容流）：

- **A1 FreeText /Contents 'ANNOTTXT'** → 不可见
- **A2 /Highlight /Contents 'HILITETXT'** → 不可见
- **A3 FreeText 带 /AP /N 外观流**（外观流自身含合法
  BT/Tj 'APSTREAM' 绘图文本）→ **同样不可见**——注释外
  观流不是页面内容流，从不被处理

三形态均：仅 body 'BODYTXT' 照提、零告警（无任何"存在
未提取注释"的提示——纯静默缺席）。

判别式：若 fallback 未来消费 page.annots 或渲染 /AP 则
对应注释文本出现在 elements 翻红；若引入缺失告警则
warnings 断言翻红。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _build(annot: bytes, extra: dict[int, bytes] | None = None):
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >>"
            b" /Annots [6 0 R] /Contents 4 0 R >>"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: annot,
    }
    if extra:
        objs.update(extra)
    body = b"BT /F1 12 Tf 72 700 Td (BODYTXT) Tj ET"
    objs[4] = (b"<< /Length " + str(len(body)).encode()
               + b" >>\nstream\n" + body + b"\nendstream")
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
        p = Path(td) / "a.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def _assert_body_only(d):
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "BODYTXT"
    joined = " ".join(e.content or "" for e in d.elements)
    assert "ANNOTTXT" not in joined
    assert "HILITETXT" not in joined
    assert "APSTREAM" not in joined
    assert d.warnings == []


def test_freetext_contents_invisible():
    """A1：FreeText /Contents → 仅 body、零告警。"""
    d = _build(b"<< /Type /Annot /Subtype /FreeText"
               b" /Rect [100 600 300 650] /Contents (ANNOTTXT) >>")
    _assert_body_only(d)


def test_highlight_markup_invisible():
    """A2：Highlight 标记注释 /Contents → 仅 body、零告警。"""
    d = _build(b"<< /Type /Annot /Subtype /Highlight"
               b" /Rect [70 695 130 710] /Contents (HILITETXT) >>")
    _assert_body_only(d)


def test_appearance_stream_invisible():
    """A3：FreeText /AP 外观流（内含可渲染 'APSTREAM'）→ 仍仅
    body、零告警——注释外观流不是页面内容流。"""
    ap = b"BT /F1 12 Tf 0 0 Td (APSTREAM) Tj ET"
    ap_obj = (b"<< /Type /XObject /Subtype /Form /BBox [0 0 200 50]"
              b" /Resources << /Font << /F1 5 0 R >> >> /Length "
              + str(len(ap)).encode()
              + b" >>\nstream\n" + ap + b"\nendstream")
    d = _build(b"<< /Type /Annot /Subtype /FreeText"
               b" /Rect [100 600 300 650] /Contents (ANNOTTXT)"
               b" /AP << /N 7 0 R >> >>", extra={7: ap_obj})
    _assert_body_only(d)
