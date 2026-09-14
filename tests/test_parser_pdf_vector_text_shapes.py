r"""PDF 矢量轮廓文本——曲线透明性与像素字形阵无幻影表（Round 1942）。

edges104 锁**网格状** rects 驱动表格检测；pdf_no_text_extracted
已有空白页等触发锁（edges53 等）。**字体转轮廓家族**（曲线
path、像素字形 rect 阵——矢量文本的两种真实形态）零覆盖。
探针 R1942 实证：

- **K1 纯曲线页**：m/l S 描边曲线（无任何文本算子）→ 零元素
  + pdf_no_text_extracted（矢量文本对提取完全不可见）
- **K2 曲线与文本混排**：同一页曲线 + 真文本 → 恰一元素真文
  本、**零告警**——曲线完全透明不污染聚类
- **K3 像素字形 rect 阵**：两行错位小填充 rect（6x6pt、间距
  12pt、字形风格排布）→ **无幻影表**——散置 rect 不被表格
  检测吸收（edges104 网格 rect 会；字形阵不构成网格），
  零元素 + pdf_no_text_extracted

判别式：若曲线/填充形状开始产出元素则 K1/K3 元素数断言翻红；
若表格检测放宽吸收散置 rect 则 K3 幻影表断言翻红；若矢量形
状干扰文本聚类则 K2 零告警断言翻红。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf


def _parse(tmp_path: Path, content: bytes):
    p = tmp_path / "v.pdf"
    p.write_bytes(_pdf([content]))
    return FallbackParser().parse(p, compute_file_hash(p))


def test_curves_only_page_invisible(tmp_path):
    """K1：纯描边曲线 → 零元素 + pdf_no_text_extracted。"""
    d = _parse(tmp_path,
               b"1 w 72 700 m 90 710 l 108 690 l 120 700 l S\n"
               b"1 w 150 700 m 170 715 l S")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_curves_transparent_next_to_text(tmp_path):
    """K2：曲线 + 真文本 → 恰一元素真文本、零告警。"""
    d = _parse(tmp_path,
               b"1 w 72 700 m 90 710 l S\n"
               b"BT /F1 12 Tf 72 600 Td (real text) Tj ET")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "real text"
    assert d.warnings == []


def test_pixel_glyph_rect_array_no_phantom_table(tmp_path):
    """K3：两行错位小填充 rect（像素字形风格）→ 无元素、无
    幻影表、pdf_no_text_extracted。"""
    rects = []
    for row, y in [(0, 700), (0, 698), (1, 660)]:
        for i in range(12):
            x = 72 + i * 12 + (5 if row else 0)
            rects.append(f"{x} {y} 6 6 re f".encode())
    d = _parse(tmp_path, b"\n".join(rects))
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]
