r"""pipeline 非表格几何家族（Round 1584）。

新角度：R1583 锁超限表格——**不成格的几何**零覆盖：

- **纯对齐文本**（3×3 无矩形）→ 不识别为表格，
  每视觉行一个 heading 元素（cell 以空格连接）
- **曲线 + 虚线矩形** → 无表格、无图形元素
- **单矩形**（孤立 100×30）→ 不成格、仅文本
- **嵌套同心矩形** → 内外框不形成网格、不识别
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


def test_aligned_text_not_table(
        tmp_path):
    rows = []
    for j in range(3):
        for x in (72, 250, 430):
            rows.append(
                f"BT /F1 10 Tf {x}"
                f" {700 - j * 30} Td"
                f" (cell{j}{x}) Tj ET")
    p = _pdf(tmp_path, "t.pdf",
             " ".join(rows))
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert not any(
        e.type == "table"
        for e in doc.elements)
    assert [e.type
            for e in doc.elements] == [
        "heading"] * 3
    assert doc.elements[0].content == (
        "cell072 cell0250 cell0430")


def test_curves_and_dashed_rect(
        tmp_path):
    c = ("[2 2] 2 d"
         " 72 650 100 30 re S"
         " 72 600 50 50 100 650"
         " 122 700 172 650 100 600"
         " c S"
         " BT /F1 12 Tf 72 550"
         " Td (CURVED) Tj ET")
    p = _pdf(tmp_path, "c.pdf", c)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    got = [(e.type, e.content)
           for e in doc.elements]
    assert got == [("heading",
                    "CURVED")]


def test_single_rect_no_table(
        tmp_path):
    c = ("72 650 100 30 re S"
         " BT /F1 10 Tf 80 655"
         " Td (SOLO) Tj ET")
    p = _pdf(tmp_path, "s.pdf", c)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    got = [(e.type, e.content)
           for e in doc.elements]
    assert got == [("heading",
                    "SOLO")]


def test_nested_rects_no_table(
        tmp_path):
    c = ("72 600 200 100 re S"
         " 122 650 100 50 re S"
         " BT /F1 10 Tf 80 655"
         " Td (INOUT) Tj ET")
    p = _pdf(tmp_path, "n.pdf", c)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    got = [(e.type, e.content)
           for e in doc.elements]
    assert got == [("heading",
                    "INOUT")]
