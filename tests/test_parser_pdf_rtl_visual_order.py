r"""PDF 降序 x 字符——RTL 视觉序家族锁定（Round 1934，a 优先级）。

真实 RTL（阿/希伯来）PDF 常按视觉序排放：流内逻辑序、位置
降序。用负字符距 Tc=-8（净前进 -1.328pt/字符）确定性模拟该
形态。探针 R1934 实证（pdfplumber 词提取 + :121 按 (y,x0)
排序、:165 行内按 x0 升序）：

- **R1 降序单行无缝反转**："abc" 降序排放 → 单元素 content
  恰 **'cba'**——x 升序排序逆转流序，字符重叠（gap<0）融为
  单词（无 'c b a' 拆词空格）；类型 heading（short_line 启发）
- **R2 行序仍按 y**：两行皆降序 → 两元素各反转（'cba'/'fed'），
  行序不随 x 反转
- **R3 Tc 跨 BT/ET 持续**：文本状态不因 BT/ET 重置——块 1 设
  Tc=-8 后，块 2 无 Tc 仍继承降序（'zyx'），块 3 `0 Tc` 显式
  重置才恢复（'rst'）

判别式：若词拼装改流序则 'cba' 全等断言翻红；若降序字符被
拆词（大间距家族 'c b a'）则无缝断言翻红；若 BT/ET 改为重置
文本状态则 'zyx' 断言翻红。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf


def _parse(tmp_path: Path, content: bytes):
    p = tmp_path / "rtl.pdf"
    p.write_bytes(_pdf([content]))
    return FallbackParser().parse(p, compute_file_hash(p))


def test_descending_line_reversed_seamless(tmp_path):
    """R1："abc" 降序排放 → 'cba' 无缝反转，short_line 启发
    heading，bbox x0 略左移（68.544≈69.344 于 72 起点）。"""
    d = _parse(tmp_path, b"BT /F1 12 Tf -8 Tc 72 700 Td (abc) Tj ET")
    assert len(d.elements) == 1
    e = d.elements[0]
    assert e.type == "heading"
    assert e.content == "cba"
    assert e.metadata.get("heuristic") == "short_line"
    assert e.source_locator["page"] == 1
    assert e.source_locator["bbox"] == pytest.approx(
        [69.344, 82.484, 78.672, 94.484])
    assert d.warnings == []


def test_two_descending_lines_line_order_by_y(tmp_path):
    """R2：两行皆降序 → 各自反转 'cba'/'fed'，行序仍上→下
    （100pt 行距 > 1.5×行高 → 两段落元素）。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf -8 Tc 72 700 Td (abc) Tj ET\n"
               b"BT /F1 12 Tf -8 Tc 72 600 Td (def) Tj ET")
    assert [e.content for e in d.elements] == ["cba", "fed"]
    assert all(e.type == "heading" for e in d.elements)
    assert d.warnings == []


def test_tc_persists_across_bt_et_blocks(tmp_path):
    """R3：Tc 不因 BT/ET 重置——块 2 无 Tc 继承 -8（'zyx'），
    块 3 `0 Tc` 显式重置恢复（'rst'）。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf -8 Tc 72 700 Td (abc) Tj ET\n"
               b"BT /F1 12 Tf 72 600 Td (xyz) Tj ET\n"
               b"BT /F1 12 Tf 0 Tc 72 500 Td (rst) Tj ET")
    assert [e.content for e in d.elements] == ["cba", "zyx", "rst"]
    assert d.warnings == []
