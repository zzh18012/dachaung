r"""PDF 旋转文本字符倒序提取 + 隐形文本（3 Tr）幻影元素锁定（Round 1900，a 优先级）。

grep 零覆盖（无 Tm 旋转矩阵、无渲染模式构造）；现实常见：图表轴
标签（90° 旋转）、OCR 底层/水印（Tr 3 隐形）。探针 R1900 实证：

- **旋转文本字符倒序**：`Tm` 90° 矩阵（0 1 -1 0）下 'abc' → 元素
  内容 **'cba'**——pdfplumber 提取 upright=False 字符但组词时字符
  序倒排；几何隔离时自成元素（bbox 是竖条）
- **隐形文本完全无视**：`3 Tr` 渲染模式下文本在阅读器不可见，但
  渲染模式不进任何过滤——照常成元素（幻影内容进 chunks）
- **旋转词与正常行融合成乱序汤**：旋转词 y_center 落入正常行容差
  → 链式融合，元素文本 'txet normal text detator hidden text'
  （倒序词与正常词按 (y_center, x0) 混排），bbox 横跨旋转竖条
"""

from __future__ import annotations

from pathlib import Path

from app.parsers.fallback_parser import _parse_pdf
from tests.test_backlog_pdf_crosspage_table import _build_pdf


def _pdf_with(content_lines: list[str], path: Path) -> Path:
    path.write_bytes(
        _build_pdf(["\n".join(content_lines).encode("latin-1")]))
    return path


def test_pdf_rotated_text_extracted_reversed(tmp_path):
    """90° 旋转（Tm 0 1 -1 0）下 'abc' → 元素 'cba'——字符倒序；
    几何隔离时自成元素（竖条 bbox）。"""
    path = _pdf_with([
        "BT /F1 12 Tf 0 1 -1 0 550 100 Tm (abc) Tj ET",
        "BT /F1 12 Tf 50 740 Td (isolated normal) Tj ET",
    ], tmp_path / "rot.pdf")
    elements, warnings = _parse_pdf(path, "sha" * 21, "doc-x", None)
    assert [e.content for e in elements] == ["isolated normal", "cba"]
    assert elements[1].source_locator["bbox"] == [540.484, 672.656, 552.484, 692.0]
    assert warnings == []


def test_pdf_hidden_text_tr3_extracted_as_normal(tmp_path):
    """隐形文本（3 Tr）：阅读器不可见但照常成元素——渲染模式零过滤。"""
    path = _pdf_with([
        "BT /F1 12 Tf 3 Tr 50 700 Td (hidden marker) Tj ET",
        "BT /F1 12 Tf 50 740 Td (visible line) Tj ET",
    ], tmp_path / "hidden.pdf")
    elements, warnings = _parse_pdf(path, "sha" * 21, "doc-x", None)
    contents = [e.content for e in elements]
    assert "hidden marker" in contents  # 幻影元素
    assert "visible line" in contents
    hm = next(e for e in elements if e.content == "hidden marker")
    assert hm.type == "heading"  # 与正常文本同分类（无任何标记）
    assert warnings == []


def test_pdf_rotated_text_fuses_into_normal_line(tmp_path):
    """融合汤：旋转词 y_center 落入正常行容差 → 单元素混排
    'txet normal text detator hidden text'，bbox 横跨旋转竖条。"""
    path = _pdf_with([
        "BT /F1 12 Tf 50 740 Td (normal text) Tj ET",
        "BT /F1 12 Tf 0 1 -1 0 500 700 Tm (rotated text) Tj ET",
        "BT /F1 12 Tf 3 Tr 50 700 Td (hidden text) Tj ET",
        "BT /F1 12 Tf 50 650 Td (tail text) Tj ET",
    ], tmp_path / "soup.pdf")
    elements, warnings = _parse_pdf(path, "sha" * 21, "doc-x", None)
    assert [e.content for e in elements] == [
        "txet normal text detator hidden text", "tail text"]
    bbox = elements[0].source_locator["bbox"]
    assert round(bbox[2], 3) == 502.484  # x1 被旋转竖条拉宽
    assert round(bbox[3] - bbox[1], 1) == 62.5  # 跨三行 + 竖条高
    assert elements[0].type == "heading"
    assert warnings == []
