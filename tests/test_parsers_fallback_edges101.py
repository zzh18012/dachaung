r"""app/parsers_fallback PDF 边角测试 - 第一百零一轮（Round 1531）。

新角度（probe 实证）旋转页上的表格检测（R1512 锁过
旋转文本、R1520 锁过旋转页坐标翻转，但表格检测与
/Rotate 的交互此前零覆盖）：

2×2 网格（四格 re S 矩形 + 格内文本 a1/b1/a2/b2）：

- **无旋转基线**：文本按行合并 'a1 b1'/'a2 b2'；表格
  检测出两个 1×2 表（纵向共边不合并——每行各成一表）
- **/Rotate 90 → 行变纵向单列表**：两个 2×1 表
  '| a2 |---|b2|' 等，bbox x=原 y 带、y=原 x 带；文本
  行内序反转 'a2 a1'/'b2 b1'
- **/Rotate 180 → 格文本镜像 + bbox 平移**：两个 1×2
  表 '| 2b | 2a |'，bbox x=612-原x（340..540）；文本
  '2b 2a' 先于 '1b 1a'（翻转后底行先行）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

_CELLS = " ".join(
    f"{x} {y} 100 30 re S"
    for x in (72, 172) for y in (650, 610))
_TXT = (
    "BT /F1 10 Tf 80 655 Td (a1) Tj ET"
    " BT /F1 10 Tf 180 655 Td (b1) Tj ET"
    " BT /F1 10 Tf 80 615 Td (a2) Tj ET"
    " BT /F1 10 Tf 180 615 Td (b2) Tj"
    " ET")


def _pdf(tmp_path: Path, name: str,
         rotate: int | None):
    content = _CELLS + " " + _TXT
    page = ("<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox [0 0 612 792]"
            + (f" /Rotate {rotate}"
               if rotate else "")
            + " /Resources << /Font"
            " << /F1 5 0 R >> >>"
            " /Contents 4 0 R >>")
    objs = [
        "<< /Type /Catalog"
        " /Pages 2 0 R >>",
        "<< /Type /Pages"
        " /Kids [3 0 R] /Count 1 >>",
        page,
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


def _got(tmp_path, name, rotate):
    p = _pdf(tmp_path, name, rotate)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    texts, tables = [], []
    for e in doc.elements:
        if e.type == "table":
            tables.append(
                (e.content,
                 [round(v, 1) for v in
                  e.source_locator["bbox"]],
                 e.metadata["row_count"],
                 e.metadata["col_count"]))
        else:
            texts.append(e.content)
    return texts, tables


def test_plain_two_row_tables(
        tmp_path):
    texts, tables = _got(
        tmp_path, "plain.pdf", None)
    assert texts == ["a1 b1", "a2 b2"]
    assert tables == [
        ("| a1 | b1 |\n| --- | --- |",
         [72.0, 112.0, 272.0, 142.0],
         1, 2),
        ("| a2 | b2 |\n| --- | --- |",
         [72.0, 152.0, 272.0, 182.0],
         1, 2),
    ]


def test_rotate90_columns(tmp_path):
    texts, tables = _got(
        tmp_path, "rot90.pdf", 90)
    assert texts == ["a2 a1", "b2 b1"]
    assert tables == [
        ("| a2 |\n| --- |\n| b2 |",
         [610.0, 72.0, 640.0, 272.0],
         2, 1),
        ("| a1 |\n| --- |\n| b1 |",
         [650.0, 72.0, 680.0, 272.0],
         2, 1),
    ]


def test_rotate180_mirrored(tmp_path):
    texts, tables = _got(
        tmp_path, "rot180.pdf", 180)
    assert texts == ["2b 2a", "1b 1a"]
    assert tables == [
        ("| 2b | 2a |\n| --- | --- |",
         [340.0, 610.0, 540.0, 640.0],
         1, 2),
        ("| 1b | 1a |\n| --- | --- |",
         [340.0, 650.0, 540.0, 680.0],
         1, 2),
    ]
