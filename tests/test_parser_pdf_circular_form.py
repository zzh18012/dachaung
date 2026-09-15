r"""PDF Form XObject 循环引用防护（Round 1986，a 优先级）。

恶意/损坏 PDF 可让 Form XObject 自引用或互引用（CWE-835）。
pdfminer pdfinterp.execute 拒绝重入 parent_stream_ids 中的流
（仅 log.warning 到 stderr，非 PDFParser 结构化告警）；子解释
器携带 parent_stream_ids = 父的 parent_stream_ids ∪ 父的
stream_ids。覆盖 grep 确认循环引用零覆盖（dangling XObject、
image matrix forms、对象别名既有，循环防护无）。探针 R1986
实证（stderr 恰见两条 Refusing，零结构化告警，无挂起）：

- **T1 自引用**：Fm6 画 'SELFDO' 后 /Fm6 Do 自己 → 守卫拒绝
  重入 → 'SELFDO' 恰一次
- **T2 互引用**：Fm6 画 'FORMAA' + Do Fm7；Fm7 画 'FORMBB' +
  Do Fm6 → 第二层拒绝 → 两词各恰一次（行合并为单元素）
- **T3 深链负控（非循环）**：Fm6→Fm7→Fm8 画 'DEEPCHN' → 守卫
  不过度拦截 → 照提（cm 平移累积 x=400）

判别式：若守卫失效则 T1/T2 无限递归挂起或 RecursionError 翻
红；若守卫过度（任何嵌套 Do 都拒）则 T3 零元素 +
pdf_no_text_extracted 翻红；若守卫走结构化告警则 warnings 非
空翻红——三向锁死。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _form(text: bytes, xobj_refs: dict[str, int], oid_font: int) -> bytes:
    content = b"BT /F1 12 Tf 0 0 Td (" + text + b") Tj ET"
    for name, oid in xobj_refs.items():
        content += (f" q 1 0 0 1 150 10 cm /{name} Do Q".encode())
    xobjs = b""
    if xobj_refs:
        parts = [f"/{k} {v} 0 R".encode() for k, v in xobj_refs.items()]
        xobjs = b" /XObject << " + b" ".join(parts) + b" >>"
    return (b"<< /Type /XObject /Subtype /Form /BBox [0 0 400 100]"
            b" /Resources << /Font << /F1 " + f"{oid_font} 0 R".encode()
            + b" >>" + xobjs + b" >>\n/Length "
            + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream")


def _build(forms: dict[int, bytes], page_draws: bytes):
    xparts = [f"/Fm{k} {k} 0 R".encode() for k in forms]
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> /XObject << "
            + b" ".join(xparts) + b" >> >> /Contents 4 0 R >>"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    objs[4] = (b"<< /Length " + str(len(page_draws)).encode()
               + b" >>\nstream\n" + page_draws + b"\nendstream")
    objs.update(forms)
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
        p = Path(td) / "c.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_self_referencing_form():
    """T1：Fm6 自 Do → 'SELFDO' 恰一次零告警。"""
    d = _build(
        {6: _form(b"SELFDO", {"Fm6": 6}, 5)},
        b"q 1 0 0 1 100 700 cm /Fm6 Do Q")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "SELFDO"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 148.012, 94.484], abs=0.01)
    assert d.warnings == []


def test_mutually_referencing_forms():
    """T2：Fm6↔Fm7 互引用 → 'FORMBB FORMAA' 各恰一次零告警。"""
    d = _build(
        {6: _form(b"FORMAA", {"Fm1": 7}, 5),
         7: _form(b"FORMBB", {"Fm2": 6}, 5)},
        b"q 1 0 0 1 100 700 cm /Fm6 Do Q")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "FORMBB FORMAA"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 72.484, 301.336, 94.484], abs=0.01)
    assert d.warnings == []


def test_deep_chain_not_overblocked():
    """T3：Fm6→Fm7→Fm8 非循环深链 → 'DEEPCHN' 照提零告警。"""
    d = _build(
        {6: _form(b"", {"Fm7": 7}, 5),
         7: _form(b"", {"Fm8": 8}, 5),
         8: _form(b"DEEPCHN", {}, 5)},
        b"q 1 0 0 1 100 700 cm /Fm6 Do Q")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "DEEPCHN"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [400.0, 62.484, 458.668, 74.484], abs=0.01)
    assert d.warnings == []
