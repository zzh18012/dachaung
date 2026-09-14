r"""PDF 网格表 cell 内图片独立性锁定（Round 1929，a 优先级）。

R1888/R1922 锁 cell 文本双重提取、R1919/1920 锁三相位序、
edges16 锁 **DOCX** cell 内图片不可见；**PDF 侧网格 cell 内
图片**（第三相位完全无视表格存在）grep 零覆盖。探针 R1929
实证：

- **图独立成元素**：words→tables→images 相位序 → 元素序
  [heading(cell 文双重提取), paragraph, table, image]；图片
  bbox 落在表格 bbox 内部、渲染成功（PNG 落盘、零告警）——
  图片不折叠进表格
- **图片行全空 cell**：图片对表格 markdown 零文本贡献——
  表格三列两行，图片所在第二行 '|  |  |  |'
- **chunk 级联**：[seq(cell 文+正文融合), isolated_table]——
  图片无 chunk（R1922 C3 家族规则，PDF 网格版）

判别式：若表提取改为吸收图片（cell 标注图存在/图并入表格
元素），元素序与空行断言翻红；若相位序改为图片在表格前，
元素序翻红。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from app.pipeline import process_single
from tests.test_parser_pdf_image_numbering import _pdf

_XS = [100.0, 250.0, 400.0, 550.0]
_LONG = ("This body line sits below the table region and is long "
         "enough to classify as a paragraph.")


def _content() -> bytes:
    parts = ["1 w 0 0 0 RG"]
    for y in (700.0, 660.0, 620.0):
        parts.append(f"{_XS[0]} {y:.1f} m {_XS[-1]} {y:.1f} l S")
    for x in _XS:
        parts.append(f"{x:.1f} 620.0 m {x:.1f} 700.0 l S")
    for x, y, text in [(120.0, 675.0, "AA"), (270.0, 675.0, "BB")]:
        parts.append(f"BT /F1 12 Tf {x:.1f} {y:.1f} Td ({text}) Tj ET")
    parts.append("q 80 0 0 60 130 628 cm /Im1 Do Q")
    parts.append(f"BT /F1 12 Tf 72.0 100.0 Td ({_LONG}) Tj ET")
    return "\n".join(parts).encode("latin-1")


def _parse(tmp_path: Path):
    p = tmp_path / "gridimg.pdf"
    p.write_bytes(_pdf([_content()]))
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    doc = FallbackParser(image_output_dir=str(img_dir)).parse(
        p, compute_file_hash(p))
    return doc, img_dir


def test_grid_cell_image_independent_element(tmp_path):
    """图独立成元素：相位序 [heading, paragraph, table, image]；
    bbox 在表内、渲染落盘、零告警。"""
    doc, img_dir = _parse(tmp_path)
    assert [e.type for e in doc.elements] == [
        "heading", "paragraph", "table", "image"]
    table_bbox = doc.elements[2].source_locator["bbox"]
    img_bbox = doc.elements[3].source_locator["bbox"]
    assert table_bbox[0] <= img_bbox[0] and img_bbox[2] <= table_bbox[2]
    assert table_bbox[1] <= img_bbox[1] and img_bbox[3] <= table_bbox[3]
    assert doc.elements[3].metadata["extracted_to_disk"] is True
    assert len(list(img_dir.glob("*.png"))) == 1
    assert doc.warnings == []


def test_grid_cell_image_no_text_contribution(tmp_path):
    """图片对表格零文本贡献：三列两行，图片行 '|  |  |  |'。"""
    doc, _ = _parse(tmp_path)
    assert doc.elements[2].content == (
        "| AA | BB |  |\n| --- | --- | --- |\n|  |  |  |")


def test_grid_cell_image_chunk_cascade(tmp_path):
    """chunk：[seq(cell 文+正文融合), isolated_table]——图片无
    chunk（R1922 C3 家族规则）。"""
    p = tmp_path / "gridimg.pdf"
    p.write_bytes(_pdf([_content()]))
    doc, errors = process_single(p, write_json=False)
    assert errors == []
    assert [c.metadata["strategy"] for c in doc.chunks] == [
        "sequential", "isolated_table"]
    assert doc.chunks[0].text.startswith("AA BB This body line")
    assert doc.chunks[1].text == doc.elements[2].content
