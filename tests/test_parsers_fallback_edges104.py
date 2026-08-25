r"""app/parsers_fallback PDF 边角测试 - 第一百零四轮（Round 1534）。

新角度（probe 实证）表格检测 × 绘图算子家族（R1531/
R1533 表格轮全用 `re S` 描边；填充式单元格网格是真实
PDF 常见形态——零覆盖）：

- **仅填充 re f → 表格照常检出**：2 个 1×2 表、内容/
  bbox 与描边完全一致（填充矩形同样驱动检测——**不是**
  静默丢表）
- **re f\*（奇偶填充）→ 同上**
- **re B（填充+描边）→ 同上**
- **混合行（上行 S、下行 f）→ 同上**（两表均出）
- **闭合路径线段网格 m/l/l/l/h S → 与 re 完全等价**
  （同 2 表同 bbox——检测只看几何不看成因）
- **⚠ 左列格子只剩竖边（无横边闭合）+ 右列格子完整 →
  0 表**：文本照常提取（'a1 b1'/'a2 b2'）但表格**整
  体无声丢失**——残缺边框会毒化整片检测
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

_TXT = (
    "BT /F1 10 Tf 80 655 Td (a1) Tj ET"
    " BT /F1 10 Tf 180 655 Td (b1) Tj ET"
    " BT /F1 10 Tf 80 615 Td (a2) Tj ET"
    " BT /F1 10 Tf 180 615 Td (b2) Tj"
    " ET")
_EXPECT = [
    ("| a1 | b1 |\n| --- | --- |",
     [72.0, 112.0, 272.0, 142.0]),
    ("| a2 | b2 |\n| --- | --- |",
     [72.0, 152.0, 272.0, 182.0]),
]


def _pdf(tmp_path: Path, name: str,
         grid: str):
    content = grid + " " + _TXT
    objs = [
        "<< /Type /Catalog"
        " /Pages 2 0 R >>",
        "<< /Type /Pages"
        " /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page"
        " /Parent 2 0 R"
        " /MediaBox [0 0 612 792]"
        " /Resources << /Font"
        " << /F1 5 0 R >> >>"
        " /Contents 4 0 R >>",
        f"<< /Length {len(content)} >>"
        f"\nstream\n{content}\n"
        f"endstream",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding"
        " /WinAnsiEncoding >>",
    ]
    pdf = b"%PDF-1.4\n"
    for i, o in enumerate(objs):
        pdf += (f"{i + 1} 0 obj\n{o}"
                f"\nendobj\n"
                ).encode("latin-1")
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 6 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def _cells(op: str) -> str:
    return " ".join(
        f"{x} {y} 100 30 re {op}"
        for x in (72, 172)
        for y in (650, 610))


def _two_tables(tmp_path, name, grid):
    p = _pdf(tmp_path, name, grid)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    texts = [e.content for e in
             doc.elements
             if e.type != "table"]
    tables = [
        (e.content,
         [round(v, 1) for v in
          e.source_locator["bbox"]])
        for e in doc.elements
        if e.type == "table"]
    assert texts == ["a1 b1", "a2 b2"]
    assert tables == _EXPECT
    for e in doc.elements:
        if e.type == "table":
            assert e.metadata[
                "row_count"] == 1
            assert e.metadata[
                "col_count"] == 2


def test_fill_only(tmp_path):
    _two_tables(tmp_path, "fillf.pdf",
                _cells("f"))


def test_fill_even_odd(tmp_path):
    _two_tables(tmp_path, "fstar.pdf",
                _cells("f*"))


def test_fill_and_stroke(tmp_path):
    _two_tables(tmp_path, "fillB.pdf",
                _cells("B"))


def test_mixed_rows(tmp_path):
    grid = (" ".join(
                f"{x} 650 100 30 re S"
                for x in (72, 172))
            + " " + " ".join(
                f"{x} 610 100 30 re f"
                for x in (72, 172)))
    _two_tables(tmp_path, "mixed.pdf",
                grid)


def test_closed_path_lines(tmp_path):
    grid = " ".join(
        f"{x} {y} m {x + 100} {y} l"
        f" {x + 100} {y + 30} l"
        f" {x} {y + 30} l h S"
        for x in (72, 172)
        for y in (650, 610))
    _two_tables(tmp_path, "paths.pdf",
                grid)


def test_degenerate_left_silent_loss(
        tmp_path):
    grid = " ".join(
        [f"{x} {y} m {x} {y + 30} l"
         " h S"
         for x in (72,) for y in
         (650, 610)]
        + [f"{x} {y} m {x + 100} {y} l"
           f" {x + 100} {y + 30} l"
           f" {x} {y + 30} l h S"
           for x in (172,) for y in
           (650, 610)])
    p = _pdf(tmp_path, "degen.pdf", grid)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content for e in
            doc.elements] == [
        "a1 b1", "a2 b2"]
    assert doc.warnings == []
