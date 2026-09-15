r"""PDF 多级页树 + 资源/MediaBox 继承（Round 1964，a 优先级）。

既有测试全部扁平页树（root Pages → Page 直连，广扫
/Type /Pages 下的 /Parent 零匹配）；真实 PDF（章节/分册）
常多级嵌套。规范：/Resources、/MediaBox 沿 /Parent 链继
承、最近祖先胜。探针 R1964 实证（pdfminer 递归走树 + 属
性继承照常）：

- **N1 两级页树**（root [branchA[1 页] + branchB[2 页]]，
  branch 带 /Parent）→ 页序 = 树深度优先遍历序 1/2/3、
  三页文本照提零告警
- **N2 /Resources 仅在根节点**（页面无自身资源）→ 字体沿
  链继承 → 与每页自带资源逐位一致（无 (cid:) 退化）
- **N3 MediaBox 最近祖先胜**（根 612×792、branchA
  300×400、页面无自身盒）→ branchA 页高 400：y 翻转
  bbox y0 = 502.484-392 = **110.484**；branchB 页仍按根
  盒 792（y0 502.484）——同文档异页高共存

判别式：若 pdfminer 不做资源继承则 N2 文本退化 (cid:)/空
翻红；若 MediaBox 取根而非最近祖先则 N3 页 1 y0 回
502.484 翻红；若页序按 oid 而非 Kids 遍历序则 N1 页码错。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _build(res_on_root: bool = False, branch_box: bool = False) -> bytes:
    # 1 catalog / 2 root pages / 3 branchA / 4 page1 / 5 branchB /
    # 6 page2 / 7 page3 / 8-10 contents / 11 font
    res_page = b" /Resources << /Font << /F1 11 0 R >> >>"
    res_root = res_page if res_on_root else b""
    box_page = b"" if branch_box else b" /MediaBox [0 0 612 792]"
    box_branch = b" /MediaBox [0 0 300 400]" if branch_box else b""

    def _cs(text: bytes) -> bytes:
        body = b"BT /F1 12 Tf 100 280 Td (" + text + b") Tj ET"
        return (b"<< /Length " + str(len(body)).encode()
                + b" >>\nstream\n" + body + b"\nendstream")

    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 3 /MediaBox [0 0 612 792]" + res_root + b" >>",
        3: b"<< /Type /Pages /Parent 2 0 R /Kids [4 0 R] /Count 1" + box_branch + b" >>",
        4: b"<< /Type /Page /Parent 3 0 R /Contents 8 0 R" + box_page + (b"" if res_on_root else res_page) + b" >>",
        5: b"<< /Type /Pages /Parent 2 0 R /Kids [6 0 R 7 0 R] /Count 2 >>",
        6: b"<< /Type /Page /Parent 5 0 R /Contents 9 0 R" + box_page + (b"" if res_on_root else res_page) + b" >>",
        7: b"<< /Type /Page /Parent 5 0 R /Contents 10 0 R" + box_page + (b"" if res_on_root else res_page) + b" >>",
        8: _cs(b"PAGETREE"),
        9: _cs(b"SECOND"),
        10: _cs(b"THIRD!"),
        11: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
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


def _parse(**kw):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.pdf"
        p.write_bytes(_build(**kw))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_nested_tree_traversal_order():
    """N1：两级页树（branchA[1] + branchB[2]）→ 页序 = Kids
    深度优先遍历 1/2/3；'THIRD!' 以 ! 结尾落 paragraph。"""
    d = _parse()
    assert [(e.source_locator["page"], e.type, e.content)
            for e in d.elements] == [
        (1, "heading", "PAGETREE"),
        (2, "heading", "SECOND"),
        (3, "paragraph", "THIRD!"),
    ]
    assert d.warnings == []


def test_resources_inherited_from_root():
    """N2：/Resources 仅在根 Pages（页面无自身资源）→ 字体沿
    /Parent 链继承 → 与每页自带资源逐位一致。"""
    d = _parse(res_on_root=True)
    assert [(e.source_locator["page"], e.content) for e in d.elements] == [
        (1, "PAGETREE"), (2, "SECOND"), (3, "THIRD!")]
    assert "cid:" not in "".join(e.content for e in d.elements)
    assert d.warnings == []


def test_mediabox_nearest_ancestor_wins():
    """N3：branchA /MediaBox [0 0 300 400]（根 612×792）→
    页 1 按最近祖先 400 高翻转（y0=110.484，恰差 392），
    页 2/3 仍按根盒（y0=502.484）。"""
    d = _parse(branch_box=True)
    b1, b2, b3 = (e.source_locator["bbox"] for e in d.elements)
    assert b1 == pytest.approx([100.0, 110.484, 165.352, 122.484], abs=0.01)
    assert b2 == pytest.approx([100.0, 502.484, 151.336, 514.484], abs=0.01)
    assert b3 == pytest.approx([100.0, 502.484, 139.996, 514.484], abs=0.01)
    assert d.warnings == []
