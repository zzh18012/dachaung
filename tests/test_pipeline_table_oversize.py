r"""pipeline 超限表格 markdown 的分块豁免（Round 1583）。

新角度：R1570 锁段落累积、R1559 锁表格基础——
**表格 markdown 超过 max_chars** 交互零覆盖：

- **溢出单元格的行文本**（35 字词宽于 138pt 单元格）
  → 行文本不入表格、7 行各自成 paragraph 元素，
  sequential 累积 [773, 128]；**表格 markdown 977 >
  800 仍单 chunk 不切**（isolated_table 豁免 max_chars）
- **适配单元格**（24 字词入格）→ 行文本进表格
  markdown（767 < 800 单 chunk），行外段落仅剩
  单 sequential chunk 671
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
         word: str) -> Path:
    cols = [72 + i * 140
            for i in range(4)]
    rows = [750 - j * 40
            for j in range(7)]
    grid = " ".join(
        f"{x} {y} 138 38 re S"
        for x in cols
        for y in rows)
    texts = " ".join(
        f"BT /F1 10 Tf {x + 10}"
        f" {y + 12} Td"
        f" ({word.format(j=j, i=i)})"
        f" Tj ET"
        for j, y in enumerate(rows)
        for i, x in enumerate(cols))
    c = grid + " " + texts
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


def test_oversize_table_chunk_exempt(
        tmp_path):
    p = _pdf(
        tmp_path, "over.pdf",
        "word{j}{i}"
        "abcdefghijklmnopqrstuvwxyz")
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    tabs = [e for e in doc.elements
            if e.type == "table"]
    paras = [e for e in doc.elements
             if e.type == "paragraph"]
    assert len(tabs) == 1
    assert len(paras) == 7
    assert len(tabs[0].content) == 977
    got = [(len(c.text),
            c.metadata["strategy"])
           for c in doc.chunks]
    assert got == [
        (773, "sequential"),
        (128, "sequential"),
        (977, "isolated_table")]
    assert doc.chunks[2].text \
        == tabs[0].content


def test_fitted_table_single_chunk(
        tmp_path):
    p = _pdf(
        tmp_path, "fit.pdf",
        "w{j}{i}"
        "abcdefghijklmnopqrst")
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    tabs = [e for e in doc.elements
            if e.type == "table"]
    assert len(tabs) == 1
    assert len(tabs[0].content) == 767
    assert tabs[0].content.startswith(
        "| w00abcdefghijklmnopqrst")
    got = [(len(c.text),
            c.metadata["strategy"])
           for c in doc.chunks]
    assert got == [
        (671, "sequential"),
        (767, "isolated_table")]
    assert doc.chunks[1].text \
        == tabs[0].content
