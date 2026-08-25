r"""app/parsers_fallback PDF 边角测试 - 第九十八轮（Round 1528）。

新角度（probe 实证）水印叠印家族（真实 PDF 水印场景；
R1483 同位叠印为同字号，本轮是大字号跨行盒叠加）：

- **同基线大字号水印并成一元素**：BODY TEXT 12pt +
  DRAFT 48pt 同 y=700 → 单元素 'DRAFT BODY TEXT'、
  bbox 高 48pt 跨两字号行盒（53.9..101.9）
- **半行偏移水印同样合并**：水印 y=706 → 'DRAFT
  BODY TEXT' 仍单元素
- **⚠ 远距大字号仍并一元素**：水印 y=600（视觉上分
  离）→ 'BODY DRAFT' 单元素、bbox 82.5..201.9 跨
  119pt——大字号行盒使 pdfplumber 行分组阈值失效
- **删除线矩形无副作用**：正文旁 re S 描边 → 只提取
  文本、bbox 不变
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

from tests.test_parsers_fallback_edges66 \
    import _pdf


def _els(tmp_path, name, content):
    p = _pdf(tmp_path, name, content)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    return [(e.content,
             [round(v, 1)
              for v in
              e.source_locator["bbox"]])
            for e in doc.elements]


def test_same_baseline_watermark(
        tmp_path):
    got = _els(
        tmp_path, "wm.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (BODY TEXT) Tj ET"
        " BT /F1 48 Tf 72 700 Td"
        " (DRAFT) Tj ET")
    assert got == [
        ("DRAFT BODY TEXT",
         [72.0, 53.9, 232.0, 101.9])]


def test_halfline_offset_watermark(
        tmp_path):
    got = _els(
        tmp_path, "wm2.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (BODY TEXT) Tj ET"
        " BT /F1 48 Tf 72 706 Td"
        " (DRAFT) Tj ET")
    assert got == [
        ("DRAFT BODY TEXT",
         [72.0, 47.9, 232.0, 95.9])]


def test_distant_big_font_merges(
        tmp_path):
    got = _els(
        tmp_path, "wm3.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (BODY) Tj ET"
        " BT /F1 48 Tf 72 600 Td"
        " (DRAFT) Tj ET")
    assert got == [
        ("BODY DRAFT",
         [72.0, 82.5, 232.0, 201.9])]


def test_strikeout_rect_ignored(
        tmp_path):
    got = _els(
        tmp_path, "strike.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (OUT) Tj ET"
        " 72 705 30 1 re S")
    assert got == [
        ("OUT",
         [72.0, 82.5, 97.3, 94.5])]
