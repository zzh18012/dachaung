"""PDF 页树节点识别变体（Round 2011，a 优先级）。

pdfpage.create_pages（pdfminer/pdfpage.py:91-150）实读：
/Count 从不被消费（枚举纯走 Kids DFS）；visited 集合防
Kids 环（:111-116，与 R1986 Form XObject 重入守卫不同层）；
非 STRICT 下 lowercase /type 兜底（:112-114 See #64）；
节点无任何 type 键 → 两分支都不进 → 静默丢页；catalog 无
/Pages → 兜底扫全部 xref 对象找 /Type /Page（:142-149）。
覆盖 grep：四形态零覆盖（circular_form 是 Form XObject 环，
pagetree_inherit 的 Count 全部算术正确）。探针 R2011 实证：

- **T1 /Count 99 + 单 Kid** → Kids 走查胜 → 'TREEWIN' 照提
  零告警
- **T2 中间 Pages 节点 Kids 自引用** → visited 跳过、不挂
  起 → 照提零告警
- **T3 页节点小写 /type /Page** → 兜底识别 → 照提零告警
- **T4 页节点无 type 键（/Contents 在场）** → 主走查丢弃 +
  兜底也找不到 → 0 元素 + 仅 pdf_no_text_extracted
- **T5 catalog 无 /Pages** → xref 全扫兜底 → 照提零告警

判别式：T1 若信 Count 翻（多余空页/异常）；T2 若挂起或
RecursionError 翻；T3 若零元素翻；T4 若照提翻；T5 若
ParserError/零元素翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

FONT = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
CONTENT = b"BT /F1 12 Tf 100 700 Td (TREEWIN) Tj ET"
PAGE_OK = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
           b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>")
CAT = b"<< /Type /Catalog /Pages 2 0 R >>"
PAGES1 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"


def _build(objs: dict[int, bytes]) -> bytes:
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
    return bytes(out)


def _parse(objs: dict[int, bytes]):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.pdf"
        p.write_bytes(_build(objs))
        return FallbackParser().parse(p, compute_file_hash(p))


def _base(pages: bytes, page: bytes,
          extra: dict[int, bytes] | None = None,
          catalog: bytes = CAT) -> dict[int, bytes]:
    objs: dict[int, bytes] = {
        1: catalog,
        2: pages,
        3: page,
        4: (b"<< /Length " + str(len(CONTENT)).encode()
            + b" >>\nstream\n" + CONTENT + b"\nendstream"),
        5: FONT,
    }
    if extra:
        objs.update(extra)
    return objs


def _assert_one(d):
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "TREEWIN"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 155.332, 94.484], abs=0.01)
    assert d.warnings == []


def test_count_lie_kids_win():
    """T1：/Count 99 + 单 Kid → Kids 走查胜，照提零告警。"""
    _assert_one(_parse(_base(b"<< /Type /Pages /Kids [3 0 R] /Count 99 >>",
                             PAGE_OK)))


def test_kids_selfcycle_no_hang():
    """T2：中间节点 Kids 自引用 → visited 跳过，不挂起照提。"""
    _assert_one(_parse(_base(
        b"<< /Type /Pages /Kids [8 0 R 3 0 R] /Count 2 >>", PAGE_OK,
        {6: b"<< >>", 7: b"<< >>",
         8: b"<< /Type /Pages /Parent 2 0 R /Kids [8 0 R] >>"})))


def test_lowercase_type_page():
    """T3：小写 /type /Page → 非 STRICT 兜底识别照提。"""
    _assert_one(_parse(_base(PAGES1,
                             b"<< /type /Page /Parent 2 0 R"
                             b" /MediaBox [0 0 612 792]"
                             b" /Resources << /Font << /F1 5 0 R >> >>"
                             b" /Contents 4 0 R >>")))


def test_page_no_type_key_dropped():
    """T4：页节点无 type 键 → 静默丢页 → 0 元素 + 仅 pdf_no_text_extracted。"""
    d = _parse(_base(PAGES1,
                     b"<< /Parent 2 0 R /MediaBox [0 0 612 792]"
                     b" /Resources << /Font << /F1 5 0 R >> >>"
                     b" /Contents 4 0 R >>"))
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_catalog_no_pages_xref_fallback():
    """T5：catalog 无 /Pages → xref 全扫兜底找到页照提。"""
    _assert_one(_parse(_base(PAGES1, PAGE_OK, catalog=b"<< /Type /Catalog >>")))
