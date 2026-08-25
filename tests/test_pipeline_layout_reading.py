r"""pipeline 版面：双栏交错与短行分类（Round 1571）。

新角度：R1570 锁行距；**水平版面**零覆盖：

- **双栏文本**（x=72 / x=350 同行）→ 按视觉行合并：
  'left0 right0 left1 right1 left2 right2'——阅读顺序
  交错（已知限制，锁行为）
- **短行家族**（14pt 标题行 + 两行 10pt 短文本、远距）
  → 全部分类 heading；sequential 策略下各占独立
  chunk（不与后文合并）
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


def test_two_columns_interleaved(
        tmp_path):
    lines = []
    for i in range(3):
        lines.append(
            f"BT /F1 10 Tf 72"
            f" {700 - i * 20} Td"
            f" (left{i}) Tj ET"
            f" BT /F1 10 Tf 350"
            f" {700 - i * 20} Td"
            f" (right{i}) Tj ET")
    p = _pdf(tmp_path, "c.pdf",
             " ".join(lines))
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (el,) = doc.elements
    assert el.content == (
        "left0 right0"
        " left1 right1"
        " left2 right2")
    (c,) = doc.chunks
    assert c.text == el.content


def test_short_lines_all_headings(
        tmp_path):
    c = ("BT /F1 14 Tf 72 750"
         " Td (Chapter Heading)"
         " Tj ET"
         " BT /F1 10 Tf 72 600"
         " Td (alpha beta gamma)"
         " Tj ET"
         " BT /F1 10 Tf 72 500"
         " Td (delta epsilon zeta)"
         " Tj ET")
    p = _pdf(tmp_path, "h.pdf", c)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert [e.type
            for e in doc.elements] == [
        "heading", "heading",
        "heading"]
    assert [c.text
            for c in doc.chunks] == [
        "Chapter Heading",
        "alpha beta gamma",
        "delta epsilon zeta"]
    assert all(
        len(c.source_element_ids) == 1
        for c in doc.chunks)
