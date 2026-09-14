r"""PDF 同位叠印文本（水印家族）锁定（Round 1932，a 优先级）。

edges200 锁**不同 x** 的栏交叠字符交错（'nRoiwgh.t'）；
**完全同位叠印**（水印/粗体阴影：同一 Td 画两遍——真实世界
DRAFT 水印即此形态）零覆盖。探针 R1932 实证（pdfplumber
字符无去重、同 x 排序稳定保插入序）：

- **O1 同文本同位两遍**：'WATER' ×2 → 单元素 content 恰
  **'WWAATTEERR'**——成对交错加倍（不是 'WATERWATER' 连接，
  也不是去重后的 'WATER'）；零告警
- **O2 异文本同位**：'AAAA' 叠 'bbbb' → 'AbbAbAbA'——两份
  字符全在（8 字符 = 4+4，无丢失）、交错序确定
- **O3 隐形叠印同型**：第二遍带 `3 Tr`（不可见渲染）→ 与 O1
  全等 'WWAATTEERR'——渲染模式既不滤字符也不构成去重键

判别式：若字符提取加同位去重（水印抑制），O1/O3 长度断言
翻红；若排序改为不稳定/按内容分组，交错串全等断言翻红。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf


def _parse(tmp_path: Path, content: bytes):
    p = tmp_path / "ov.pdf"
    p.write_bytes(_pdf([content]))
    return FallbackParser().parse(p, compute_file_hash(p))


def test_same_text_overprint_pairwise_interleave(tmp_path):
    """O1：'WATER' 同位两遍 → 恰 'WWAATTEERR'（成对交错），
    零告警。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf 72 700 Td (WATER) Tj ET\n"
               b"BT /F1 12 Tf 72 700 Td (WATER) Tj ET")
    assert len(d.elements) == 1
    assert d.elements[0].content == "WWAATTEERR"
    assert d.warnings == []


def test_different_text_overprint_no_loss(tmp_path):
    """O2：'AAAA' 叠 'bbbb' → 'AbbAbAbA'——两份字符全在、交错
    序确定（水印毁坏正文的典型形态）。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf 72 700 Td (AAAA) Tj ET\n"
               b"BT /F1 12 Tf 72 700 Td (bbbb) Tj ET")
    assert len(d.elements) == 1
    assert d.elements[0].content == "AbbAbAbA"
    assert d.warnings == []


def test_invisible_overprint_same_as_visible(tmp_path):
    """O3：第二遍 `3 Tr`（不可见）→ 与可见叠印全等
    'WWAATTEERR'——渲染模式不是去重键。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf 72 700 Td (WATER) Tj ET\n"
               b"BT /F1 12 Tf 3 Tr 72 700 Td (WATER) Tj ET")
    assert len(d.elements) == 1
    assert d.elements[0].content == "WWAATTEERR"
    assert d.warnings == []
