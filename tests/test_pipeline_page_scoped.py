r"""pipeline 跨页表格与遮挡文本（Round 1573）。

新角度：表格检测均在单页内构造——**跨页拆分表格**
与**被矩形覆盖的文本**零覆盖：

- **表格跨页拆分**（每页 1 行）→ 两个独立 table 元素
  （检测按页作用域，不跨页合并），各带 markdown
- **文本被后绘制的填充矩形覆盖** → 仍然提取（向量
  提取无视 z-order 视觉遮挡）
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
         c1: str, c2: str) -> Path:
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R 4 0 R]"
           " /Count 2 >>",
        3: ("<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox"
            " [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 6 0 R >> >>"
            " /Contents 5 0 R >>"),
        4: ("<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox"
            " [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 6 0 R >> >>"
            " /Contents 7 0 R >>"),
        5: f"<< /Length {len(c1)} >>"
           f"\nstream\n{c1}\nendstream",
        6: _FONT,
        7: f"<< /Length {len(c2)} >>"
           f"\nstream\n{c2}\nendstream",
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
            b" /Size 8 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def test_table_split_across_pages(
        tmp_path):
    g1 = " ".join(
        f"{x} {y} 100 30 re S"
        for x in (72, 172)
        for y in (650,))
    g2 = " ".join(
        f"{x} {y} 100 30 re S"
        for x in (72, 172)
        for y in (610,))
    p = _pdf(
        tmp_path, "split.pdf",
        g1 + " BT /F1 10 Tf"
        " 80 655 Td (r1a) Tj ET",
        g2 + " BT /F1 10 Tf"
        " 80 615 Td (r2a) Tj ET")
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    got = [(e.type,
            e.source_locator["page"])
           for e in doc.elements]
    assert got == [
        ("heading", 1),
        ("table", 1),
        ("heading", 2),
        ("table", 2)]
    tabs = [e for e in doc.elements
            if e.type == "table"]
    assert tabs[0].content == (
        "| r1a |  |"
        "\n| --- | --- |")
    assert tabs[1].content == (
        "| r2a |  |"
        "\n| --- | --- |")


def test_covered_text_extracted(
        tmp_path):
    p = _pdf(
        tmp_path, "cover.pdf",
        "BT /F1 12 Tf 72 700"
        " Td (HIDDEN TEXT) Tj ET"
        " 0 0 0 rg"
        " 60 680 200 40 re f",
        "BT /F1 12 Tf 72 700"
        " Td (PAGE2) Tj ET")
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert [e.content
            for e in doc.elements] == [
        "HIDDEN TEXT", "PAGE2"]
