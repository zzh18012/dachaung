r"""PDF 内容流操作数数字形态——pdfminer 词法器（Round 2008，a 优先级）。

psparser.py `_parse_main`：'-+'/数字 → `_parse_number`，'.'
直接 `_parse_float`；终值走 Python int()/float()（语法超集）。
零覆盖（grep 实证 parser 测试无这些操作数形态）。探针 R2008
实证：

- **T1 '.5' 前导点**：`100 .5 Td` → y=0.5 → top=781.984
- **T2 '700.' 尾随点**：float('700.')=700.0 → 与 700 等价
- **T3 '+100 +700' 正号**：int('+100') → 无符号等价
- **T4 '-.5' 负前导点**：float('-.5') → y=-0.5 越下界仍提取
  零告警（与 R1943 N2 同理：不裁剪）
- **T5 裸 '.'**：float('.') ValueError 被 suppress → **零
  token**——`100 . 700 Td` 与 `100 700 Td` 同值；三操作数
  变体 `100 . 200 700 Td` 与无点版逐位相同（Td 配对 (200,700)）
- **T6 '1e2' 科学计数**：int(1) + KWD('e2')——'e2' 作未知
  算子被静默忽略 → Td(100, **1**) → y=1 → top=781.484

判别式：T1-T4 若与等价形态 bbox 不同翻；T5 若 '.' 被解析成
数（三操作数变体 x0≠200）翻；T6 若 y=100（科学计数生效）翻。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf


def _parse(tmp_path: Path, content: bytes):
    p = tmp_path / "n.pdf"
    p.write_bytes(_pdf([content]))
    return FallbackParser().parse(p, compute_file_hash(p))


def _one_heading(d):
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "A"
    assert d.warnings == []
    return d.elements[0].source_locator["bbox"]


def test_leading_dot_operand(tmp_path):
    """T1：`100 .5 Td` → y=0.5（float('.5') 合法）。"""
    bbox = _one_heading(_parse(tmp_path, b"BT /F1 12 Tf 100 .5 Td (A) Tj ET"))
    assert bbox == pytest.approx([100.0, 781.984, 108.004, 793.984], abs=0.01)


def test_trailing_dot_operand(tmp_path):
    """T2：`100 700. Td` → float('700.')=700.0 与整数等价。"""
    bbox = _one_heading(_parse(tmp_path, b"BT /F1 12 Tf 100 700. Td (A) Tj ET"))
    assert bbox == pytest.approx([100.0, 82.484, 108.004, 94.484], abs=0.01)


def test_plus_sign_operands(tmp_path):
    """T3：`+100 +700 Td` → int('+100') 与无符号等价。"""
    bbox = _one_heading(_parse(tmp_path, b"BT /F1 12 Tf +100 +700 Td (A) Tj ET"))
    assert bbox == pytest.approx([100.0, 82.484, 108.004, 94.484], abs=0.01)


def test_negative_leading_dot_operand(tmp_path):
    """T4：`100 -.5 Td` → y=-0.5 越下界仍提取、零告警。"""
    bbox = _one_heading(_parse(tmp_path, b"BT /F1 12 Tf 100 -.5 Td (A) Tj ET"))
    assert bbox == pytest.approx([100.0, 782.984, 108.004, 794.984], abs=0.01)


def test_bare_dot_zero_token(tmp_path):
    """T5：裸 '.' 零 token——三操作数变体与无点版逐位相同（Td 配对 200,700）。"""
    with_dot = _one_heading(_parse(
        tmp_path, b"BT /F1 12 Tf 100 . 200 700 Td (A) Tj ET"))
    no_dot = _one_heading(_parse(
        tmp_path, b"BT /F1 12 Tf 100 200 700 Td (A) Tj ET"))
    assert with_dot == pytest.approx([200.0, 82.484, 208.004, 94.484], abs=0.01)
    assert with_dot == pytest.approx(no_dot, abs=0.0)


def test_scientific_notation_degrades(tmp_path):
    """T6：`100 1e2 Td` → 1 + 未知算子 e2 → Td(100,1) → y=1。"""
    bbox = _one_heading(_parse(tmp_path, b"BT /F1 12 Tf 100 1e2 Td (A) Tj ET"))
    assert bbox == pytest.approx([100.0, 781.484, 108.004, 793.484], abs=0.01)
