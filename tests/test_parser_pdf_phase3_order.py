r"""PDF 三相位全序 + 图片顺序来源锁定（Round 1920，a 优先级）。

R1919 锁了段落→表格两相位序；本轮补第三相位（图片）与图片
元素序的来源。探针 R1920 实证（_parse_pdf :260/:291/:330 三循环）：

- **三相位全序**：同页图在顶（bbox top≈12）、表在中（top≈292）、
  文在底（top≈682）→ 元素序 [heading(表内文本), paragraph(正文),
  table, image]——图片**最后**发射，几何序完全倒置
- **图片元素序 = 内容流序**：底部图先画、顶部图后画 → 底图
  （top 642）是第一个 image 元素且拿 _p1_00 文件名，顶图（top 92）
  是第二、拿 _p1_01——page.images 按内容流序返回，不做几何排序
- **页序压倒相位序**：页 1 = 文+图、页 2 = 表 →
  [paragraph(p1), image(p1), heading(p2), table(p2)]——页 1 的
  image 先于页 2 的 table；"图片页内最后"不是"全局最后"

判别式：images 循环挪到段落循环之前 → 三测全红；page.images
若改为按 top 排序 → Q2 测试翻红。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf

_XS = [100.0, 250.0, 550.0]
_LONG = (
    "This body line sits below the table region and is long enough "
    "to classify as a paragraph."
)


def _grid(y_top: float, y_bot: float, cells: list[tuple[float, float, str]]) -> str:
    parts = ["1 w 0 0 0 RG"]
    for y in (y_top, (y_top + y_bot) / 2, y_bot):
        parts.append(f"{_XS[0]} {y:.1f} m {_XS[-1]} {y:.1f} l S")
    for x in _XS:
        parts.append(f"{x:.1f} {y_bot:.1f} m {x:.1f} {y_top:.1f} l S")
    for x, y, text in cells:
        parts.append(f"BT /F1 12 Tf {x:.1f} {y:.1f} Td ({text}) Tj ET")
    return "\n".join(parts)


def _text_line(y: float) -> str:
    return f"BT /F1 12 Tf 72.0 {y:.1f} Td ({_LONG}) Tj ET"


def _parse(tmp_path: Path, contents: list[bytes], img_dir: Path | None = None):
    p = tmp_path / "d.pdf"
    p.write_bytes(_pdf(contents))
    parser = (FallbackParser(image_output_dir=str(img_dir))
              if img_dir is not None else FallbackParser())
    return parser.parse(p, compute_file_hash(p))


def test_three_phase_order_image_last_despite_geometric_inversion(tmp_path):
    """图顶/表中/文底 → [heading, paragraph, table, image]：图片最后
    发射；正文段落元素下标 < table < image，几何 top 恰好相反。"""
    content = "q 100 0 0 100 450 680 cm /Im1 Do Q"
    content += "\n" + _grid(500.0, 420.0, [(120.0, 440.0, "T1"), (270.0, 440.0, "T2")])
    content += "\n" + _text_line(100.0)
    doc = _parse(tmp_path, [content.encode("latin-1")])
    types = [e.type for e in doc.elements]
    assert types == ["heading", "paragraph", "table", "image"]
    body, table, image = doc.elements[1], doc.elements[2], doc.elements[3]
    # 几何倒置：正文在页底（top 最大），图片在页首（top 最小）
    assert body.source_locator["bbox"][1] > table.source_locator["bbox"][1]
    assert table.source_locator["bbox"][1] > image.source_locator["bbox"][1]
    # 元素序与几何序完全相反
    assert doc.elements.index(body) < doc.elements.index(table) < doc.elements.index(image)


def test_image_element_order_follows_content_stream_not_geometry(tmp_path):
    """底图先画（top≈642）、顶图后画（top≈92）→ 底图是第一个 image
    元素并拿 _p1_00 文件名；page.images 按内容流序，无几何排序。"""
    content = ("q 100 0 0 100 450 50 cm /Im1 Do Q\n"
               "q 100 0 0 100 450 600 cm /Im1 Do Q")
    img_dir = tmp_path / "imgs"
    doc = _parse(tmp_path, [content.encode("latin-1")], img_dir)
    images = [e for e in doc.elements if e.type == "image"]
    assert len(images) == 2
    first, second = images
    # 判别式：内容流序（底图先）——几何排序假设下两断言均翻红
    assert first.source_locator["bbox"][1] > second.source_locator["bbox"][1]
    assert Path(first.resource_path).name.endswith("_p1_00.png")
    assert Path(second.resource_path).name.endswith("_p1_01.png")
    assert (img_dir / Path(first.resource_path).name).exists()


def test_page_order_dominates_phase_order_across_pages(tmp_path):
    """页 1 = 文+图、页 2 = 表 → [paragraph(p1), image(p1), heading(p2),
    table(p2)]——页 1 的 image 先于页 2 的 table；页内相位序不变。"""
    page1 = "q 100 0 0 100 450 700 cm /Im1 Do Q\n" + _text_line(100.0)
    page2 = _grid(700.0, 620.0, [(120.0, 640.0, "U1"), (270.0, 640.0, "U2")])
    doc = _parse(tmp_path, [page1.encode("latin-1"), page2.encode("latin-1")])
    types = [e.type for e in doc.elements]
    pages = [e.source_locator["page"] for e in doc.elements]
    assert types == ["paragraph", "image", "heading", "table"]
    assert pages == [1, 1, 2, 2]
    # 页 1 的 image（页内相位"最后"）仍先于页 2 的任何元素
    image_idx = types.index("image")
    assert all(i > image_idx for i in range(image_idx + 1, len(types)))
