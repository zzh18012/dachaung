r"""pipeline 表格最小形状（Round 1590）。

新角度：R1584 锁非表格几何——**最小可识别形状**
零覆盖：

- **1 行 × 2 列**（共享竖边）→ 识别为表格
  （markdown 自动补表头分隔行），且文本**同时**
  产出独立 heading 元素（双重提取，已知行为）
- **2 行 × 1 列**（共享横边）→ 不识别（列数 <2）
- **对角错位矩形** → 不识别（无共享边不成网格）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")


def _pdf(tmp_path: Path, name: str,
         c: str) -> Path:
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R]"
           " /Count 1 >>",
        3: ("<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox"
            " [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 5 0 R >> >>"
            " /Contents 4 0 R >>"),
        4: f"<< /Length {len(c)} >>"
           f"\nstream\n{c}\nendstream",
        5: _FONT,
    }
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
            b" /Size 6 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def test_one_row_two_cols_table(
        tmp_path):
    c = ("72 650 100 30 re S"
         " 172 650 100 30 re S"
         " BT /F1 10 Tf 80 655"
         " Td (a) Tj ET"
         " BT /F1 10 Tf 180 655"
         " Td (b) Tj ET")
    p = _pdf(tmp_path, "r.pdf", c)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    got = [(e.type, e.content)
           for e in doc.elements]
    assert got == [
        ("heading", "a b"),
        ("table",
         "| a | b |"
         "\n| --- | --- |")]
    tab = doc.elements[1]
    assert tab.metadata["row_count"] == 1
    assert tab.metadata["col_count"] == 2


def test_two_rows_one_col_no_table(
        tmp_path):
    c = ("72 650 100 30 re S"
         " 72 610 100 30 re S"
         " BT /F1 10 Tf 80 655"
         " Td (a) Tj ET"
         " BT /F1 10 Tf 80 615"
         " Td (b) Tj ET")
    p = _pdf(tmp_path, "c.pdf", c)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    got = [(e.type, e.content)
           for e in doc.elements]
    assert got == [("heading", "a"),
                   ("heading", "b")]


def test_diagonal_rects_no_table(
        tmp_path):
    c = ("72 650 100 30 re S"
         " 182 610 100 30 re S"
         " BT /F1 10 Tf 80 655"
         " Td (x) Tj ET"
         " BT /F1 10 Tf 190 615"
         " Td (y) Tj ET")
    p = _pdf(tmp_path, "d.pdf", c)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    got = [(e.type, e.content)
           for e in doc.elements]
    assert got == [("heading", "x"),
                   ("heading", "y")]
