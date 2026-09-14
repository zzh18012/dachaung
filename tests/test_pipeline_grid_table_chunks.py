r"""网格表 PDF 页端到端 chunk 组成锁定（Round 1922，a 优先级）。

R1888 锁 parser 级表内文本双重提取；R1919/1920 锁相位序；
R1765 锁 markdown 纯图零 chunk。本轮锁**真实网格表 PDF 页**的
pipeline 级级联后果（探针 R1922 实证）：

- **表内文本污染正文块**：网格表 + 正文页 → 恰 2 chunk——
  表内文本被双重提取为 heading（首元素）后，与正文段落**融合
  进同一个 sequential 块**（'AA BB This body line…'）——heading
  硬边界只封口**前**块，文档开头的 heading 无前块可封
- **双表页四块型**：[A表内文+正文 seq, B表内文 seq, 表A iso,
  表B iso]——第二组表内文本 heading 才封口前块；两 isolated_table
  保持几何上下序
- **不丢不重对双重提取成立**：元素文本拼接与 chunk 文本拼接在
  normalize_text 下相等——双重提取让表内文本在 elements 与
  chunks 里**各出现两次**，无损不变式仍然保持

判别式：heading 硬边界改为"heading 自身也独立成块"则融合测试
翻红；表格元素并入 sequential 则四块型翻红。
"""

from __future__ import annotations

from pathlib import Path

from app.chunkers.structural import normalize_text
from app.pipeline import process_single
from tests.test_parser_pdf_image_numbering import _pdf

_XS = [100.0, 250.0, 400.0, 550.0]
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


def _run(tmp_path: Path, content: str):
    p = tmp_path / "d.pdf"
    p.write_bytes(_pdf([content.encode("latin-1")]))
    doc, errors = process_single(p, write_json=False)
    assert doc is not None and errors == []
    return doc


def test_grid_table_page_two_chunks_cell_text_fuses_with_body(tmp_path):
    """网格表+正文 → 恰 2 chunk：双重提取的表内文本 heading（文档首
    元素，无前块可封）与正文段落融合为一个 sequential 块；表格独立。"""
    content = _grid(700.0, 620.0, [(120.0, 640.0, "AA"), (270.0, 640.0, "BB")])
    content += f"\nBT /F1 12 Tf 72.0 100.0 Td ({_LONG}) Tj ET"
    doc = _run(tmp_path, content)
    assert [e.type for e in doc.elements] == ["heading", "paragraph", "table"]
    assert len(doc.chunks) == 2
    seq, iso = doc.chunks
    assert seq.metadata["strategy"] == "sequential"
    # 表内文本污染正文块：heading 文本与正文融合
    assert seq.text.startswith("AA BB This body line")
    assert seq.source_element_ids == [
        doc.elements[0].element_id, doc.elements[1].element_id]
    assert iso.metadata["strategy"] == "isolated_table"
    assert "| AA | BB |" in iso.text
    assert iso.source_element_ids == [doc.elements[2].element_id]


def test_double_grid_page_four_chunk_sequence(tmp_path):
    """双网格+中部正文 → 4 chunk [seq, seq, iso, iso]：第二组表内文本
    heading 封口前块；两表保持几何上下序（A 上 B 下）。"""
    content = _grid(700.0, 620.0, [(120.0, 640.0, "A1"), (270.0, 640.0, "A2")])
    content += "\n" + _grid(300.0, 220.0, [(120.0, 240.0, "B1"), (270.0, 240.0, "B2")])
    content += f"\nBT /F1 12 Tf 72.0 450.0 Td ({_LONG}) Tj ET"
    doc = _run(tmp_path, content)
    assert [c.metadata["strategy"] for c in doc.chunks] == [
        "sequential", "sequential", "isolated_table", "isolated_table"]
    first, second, table_a, table_b = doc.chunks
    # 首块 = A 表内文 + 正文（A heading 无前块）；第二块恰 B 表内文
    assert first.text.startswith("A1 A2 This body line")
    assert second.text == "B1 B2"
    assert second.source_element_ids == [doc.elements[2].element_id]
    # 两表几何上下序：A（bbox top 小）先于 B
    assert "| A1 | A2 |" in table_a.text
    assert "| B1 | B2 |" in table_b.text
    top_a = doc.elements[3].source_locator["bbox"][1]
    top_b = doc.elements[4].source_locator["bbox"][1]
    assert top_a < top_b
    assert doc.chunks.index(table_a) < doc.chunks.index(table_b)


def test_grid_page_no_loss_despite_double_extraction(tmp_path):
    """双重提取下"不丢不重"仍成立：elements 文本拼接与 chunks 文本
    拼接在 normalize_text 后相等——表内文本在两侧各出现两次。"""
    content = _grid(700.0, 620.0, [(120.0, 640.0, "AA"), (270.0, 640.0, "BB")])
    content += f"\nBT /F1 12 Tf 72.0 100.0 Td ({_LONG}) Tj ET"
    doc = _run(tmp_path, content)
    elements_text = normalize_text(
        " ".join(e.content or "" for e in doc.elements if e.content))
    chunks_text = normalize_text(" ".join(c.text for c in doc.chunks))
    assert "AA" in elements_text and "AA" in chunks_text
    assert elements_text == chunks_text
