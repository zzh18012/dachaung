r"""pipeline heading 分类的长度阈值（Round 1588）。

新角度：R1571 锁短行家族行为——**阈值边界与
字号无关性**零覆盖：

- **孤立行长阈值**：≤80 字 → heading、≥81 字 →
  paragraph（单字无空白亦然，纯长度驱动）
- **字号无关**：9..14pt 的 'word' 全部 heading
- **多词行一致**：12 词 73 字 heading、15 词 94 字
  paragraph
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


def _lines(lines, gap=110):
    parts = []
    y = 760
    for t in lines:
        parts.append(
            f"BT /F1 10 Tf 72 {y}"
            f" Td ({t}) Tj ET")
        y -= gap
    return " ".join(parts)


def test_length_boundary_80_81(
        tmp_path):
    p = _pdf(
        tmp_path, "b.pdf",
        _lines(["w" * 80, "w" * 80,
                "w" * 81, "w" * 81]))
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    got = [(len(e.content), e.type)
           for e in doc.elements]
    assert got == [
        (80, "heading"),
        (80, "heading"),
        (81, "paragraph"),
        (81, "paragraph")]


def test_font_size_independent(
        tmp_path):
    parts = []
    y = 700
    for fs in (9, 10, 11, 12, 13, 14):
        parts.append(
            f"BT /F1 {fs} Tf 72 {y}"
            f" Td (word) Tj ET")
        y -= 80
    p = _pdf(tmp_path, "f.pdf",
             " ".join(parts))
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert [e.type
            for e in doc.elements] == [
        "heading"] * 6


def test_multiword_consistent(
        tmp_path):
    w12 = " ".join(
        f"a{i:04d}" for i in range(12))
    w15 = " ".join(
        f"b{i:04d}" for i in range(15))
    p = _pdf(
        tmp_path, "m.pdf",
        _lines([w12, w15]))
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    got = [(len(e.content), e.type)
           for e in doc.elements]
    assert got[0][1] == "heading"
    assert got[1][1] == "paragraph"
