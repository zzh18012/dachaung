r"""app/parsers_fallback PDF 边角测试 - 第一百一十六轮（Round 1546）。

新角度（probe 实证）共享流 / 大页数 / 跨页元素序（零
覆盖）：

- **同一 /Contents 流对象被两页共享** → 两页各提取一
  份（'BODY' page 1 + 'BODY' page 2，不因共享去重）
- **300 页规模** → 300 元素、页码 1..300 连续有序无重
  复、零警告（解析 0.1s——线性）
- **跨页元素序**（页1 文本 / 页2 表格 / 页3 文本）→ 按
  页升序；**页内先文本后表格**（文本 'a1 b1'/'a2 b2'
  先于两表——非几何交错）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

_C = "BT /F1 12 Tf 72 700 Td (BODY) Tj ET"
_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")


def _parse(tmp_path, name, objs,
           size):
    pdf = b"%PDF-1.4\n"
    for oid in sorted(objs):
        o = objs[oid]
        if isinstance(o, str):
            o = o.encode("latin-1")
        pdf += (f"{oid} 0 obj\n"
                .encode("latin-1")
                + o + b"\nendobj\n")
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size " + str(size).encode()
            + b" >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return FallbackParser().parse(
        p, compute_file_hash(p))


def _page(parent, contents):
    return (f"<< /Type /Page"
            f" /Parent {parent} 0 R"
            f" /MediaBox [0 0 612 792]"
            f" /Resources << /Font"
            f" << /F1 5 0 R >> >>"
            f" /Contents {contents}"
            f" 0 R >>")


def test_shared_content_stream(
        tmp_path):
    doc = _parse(tmp_path, "shared.pdf", {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R 4 0 R]"
           " /Count 2 >>",
        3: _page(2, 6),
        4: _page(2, 6),
        6: f"<< /Length"
           f" {len(_C)} >>"
           f"\nstream\n{_C}\n"
           f"endstream",
        5: _FONT,
    }, 7)
    assert [(e.content,
             e.source_locator["page"])
            for e in doc.elements] == [
        ("BODY", 1), ("BODY", 2)]
    assert doc.warnings == []


def test_300_page_scale(tmp_path):
    n = 300
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: ("<< /Type /Pages"
            " /Kids ["
            + " ".join(
                f"{1000 + i} 0 R"
                for i in range(n))
            + f"] /Count {n} >>"),
        5: _FONT,
    }
    for i in range(n):
        objs[1000 + i] = _page(
            2, 2000 + i)
        objs[2000 + i] = (
            f"<< /Length"
            f" {len(_C)} >>"
            f"\nstream\n{_C}\n"
            f"endstream")
    doc = _parse(tmp_path, "scale.pdf",
                 objs, 2000 + n)
    pages = [e.source_locator["page"]
             for e in doc.elements]
    assert len(pages) == 300
    assert pages == list(range(1, 301))
    assert doc.warnings == []


def test_cross_page_order(tmp_path):
    grid = " ".join(
        f"{x} {y} 100 30 re S"
        for x in (72, 172)
        for y in (650, 610))
    txt = ("BT /F1 10 Tf 80 655 Td"
           " (a1) Tj ET"
           " BT /F1 10 Tf 180 655 Td"
           " (b1) Tj ET"
           " BT /F1 10 Tf 80 615 Td"
           " (a2) Tj ET"
           " BT /F1 10 Tf 180 615 Td"
           " (b2) Tj ET")
    tab = grid + " " + txt
    doc = _parse(tmp_path, "order.pdf", {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R 4 0 R"
           " 30 0 R] /Count 3 >>",
        3: _page(2, 20),
        4: _page(2, 21),
        30: _page(2, 22),
        20: f"<< /Length"
            f" {len(_C)} >>"
            f"\nstream\n{_C}\n"
            f"endstream",
        21: f"<< /Length"
            f" {len(tab)} >>"
            f"\nstream\n{tab}\n"
            f"endstream",
        22: f"<< /Length"
            f" {len(_C)} >>"
            f"\nstream\n{_C}\n"
            f"endstream",
        5: _FONT,
    }, 31)
    got = [(e.type,
            e.source_locator["page"])
           for e in doc.elements]
    assert got == [
        ("heading", 1),
        ("heading", 2),
        ("heading", 2),
        ("table", 2),
        ("table", 2),
        ("heading", 3)]
    assert doc.warnings == []
