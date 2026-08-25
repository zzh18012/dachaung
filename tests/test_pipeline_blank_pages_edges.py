r"""pipeline 空白页与页缘文本（Round 1574）。

新角度：R1573 锁页作用域；**空白页家族与 MediaBox
边缘文本**零覆盖：

- **空白中间页**（空内容流 / 纯空白 Tj）→ 不产出
  元素也不报错，物理页码保留（P1→1、P3→3；
  两页连空后 P4→4）
- **页缘文本**（y=791 越过 792 顶边 / y=1 贴底）→
  照常提取，bbox 允许负坐标（向量提取无视裁剪）

构建教训：多页 PDF 字体对象放高 oid（50），
低 oid 会与第 2 页对象号冲突。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.pipeline import process_single

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")


def _pdf(tmp_path: Path, name: str,
         pages: list) -> Path:
    n = len(pages)
    kids = " ".join(
        f"{3 + 2 * i} 0 R"
        for i in range(n))
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: (f"<< /Type /Pages"
            f" /Kids [{kids}]"
            f" /Count {n} >>"),
        50: _FONT,
    }
    for i, c in enumerate(pages):
        c = c or ""
        objs[3 + 2 * i] = (
            "<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox"
            " [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 50 0 R >> >>"
            f" /Contents"
            f" {4 + 2 * i} 0 R >>")
        objs[4 + 2 * i] = (
            f"<< /Length {len(c)} >>"
            f"\nstream\n{c}\nendstream")
    pdf = b"%PDF-1.4\n"
    for oid in sorted(objs):
        o = objs[oid]
        if isinstance(o, str):
            o = o.encode("latin-1")
        pdf += (f"{oid} 0 obj\n"
                ).encode() + o \
            + b"\nendobj\n"
    pdf += (b"trailer"
            b" << /Root 1 0 R"
            b" /Size 51 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def _t(text: str, y: int) -> str:
    return (f"BT /F1 12 Tf 72 {y}"
            f" Td ({text}) Tj ET")


def test_empty_middle_page(
        tmp_path):
    p = _pdf(
        tmp_path, "empty-mid.pdf",
        [_t("P1", 700), "", _t("P3", 700)])
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    got = [(e.content,
            e.source_locator["page"])
           for e in doc.elements]
    assert got == [("P1", 1), ("P3", 3)]
    assert [c.text
            for c in doc.chunks] == [
        "P1", "P3"]


def test_two_blank_pages_between(
        tmp_path):
    ws = ("BT /F1 12 Tf 72 700"
          " Td (   ) Tj ET")
    p = _pdf(
        tmp_path, "blank-many.pdf",
        [_t("P1", 700), ws, "",
         _t("P4", 700)])
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    got = [(e.content,
            e.source_locator["page"])
           for e in doc.elements]
    assert got == [("P1", 1), ("P4", 4)]


def test_edge_text_extracted(
        tmp_path):
    p = _pdf(
        tmp_path, "edges.pdf",
        [_t("TOPEDGE", 791)
         + " " + _t("BOTEDGE", 1)])
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    got = [(e.content,
            e.source_locator["bbox"])
           for e in doc.elements]
    assert [g[0] for g in got] == [
        "TOPEDGE", "BOTEDGE"]
    assert got[0][1] == pytest.approx(
        [72.0, -8.516, 130.68, 3.484],
        abs=1e-6)
    assert got[1][1] == pytest.approx(
        [72.0, 781.484, 130.68,
         793.484], abs=1e-6)
