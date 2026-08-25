r"""app/parsers/fallback_parser.py PDF 边角测试 - 第八十轮（Round 1510）。

新角度（probe 实证）同行跨 BT 合并与双栏布局（R1509 行
合并的横向对照）：

- **同 y 内容跨 BT 对象合并**：两个 BT 各放 'L1'(x72)
  /'R1'(x300) 同 y=700 → **单元素 'L1 R1'** 空格连接、
  bbox 横跨 72..315（**栏不保序**——双栏 PDF 同行文本
  会串栏）
- **任意大横向 gap 均合并**：30/100/200pt x 跳全部单
  元素 'aa bb'（无栏切分阈值）
- **正常行距双栏按行合并**：L/R 栏各 2 行（-50 行距）
  → ['L1 R1', 'L2 R2']——每行跨栏并成一个元素、bbox
  横跨两栏，阅读顺序自上而下
- **紧凑行距双栏整体并一**：-20 行距 < 行高 → 四段文
  本 'L1 R1 L2 R2' 并成**单元素**（行合并×栏合并叠加）
- **⚠ ETBT 融合操作符**：内容流缺空格致 'ET'+'BT' 融
  成单个未知操作符 'ETBT' → ET 未执行、BT 未重开，
  第二个 Td 相对首 BT 末行累计 → R 栏 bbox y 为**负**
  （-597.5）且 R 栏先出——畸形 token 静默改变状态机
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


def test_same_row_across_bt_merges(
        tmp_path):
    got = _els(
        tmp_path, "sr.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (L1) Tj ET"
        " BT /F1 12 Tf 300 700 Td"
        " (R1) Tj ET")
    assert got == [
        ("L1 R1",
         [72.0, 82.5, 315.3, 94.5]),
    ]


def test_horizontal_gap_any_size_merges(
        tmp_path):
    for gap in (30, 100, 200):
        got = _els(
            tmp_path, f"g{gap}.pdf",
            "BT /F1 12 Tf 72 700 Td"
            f" (aa) Tj {gap} 0 Td"
            " (bb) Tj ET")
        assert len(got) == 1, gap
        assert got[0][0] == "aa bb"


def test_two_col_per_row_merge(
        tmp_path):
    got = _els(
        tmp_path, "tc.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (L1) Tj 0 -50 Td (L2) Tj"
        " ET BT /F1 12 Tf 300 700"
        " Td (R1) Tj 0 -50 Td"
        " (R2) Tj ET")
    assert got == [
        ("L1 R1",
         [72.0, 82.5, 315.3, 94.5]),
        ("L2 R2",
         [72.0, 132.5, 315.3, 144.5]),
    ]


def test_tight_leading_two_col_single(
        tmp_path):
    got = _els(
        tmp_path, "tt.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (L1) Tj 0 -20 Td (L2) Tj"
        " ET BT /F1 12 Tf 300 700"
        " Td (R1) Tj 0 -20 Td"
        " (R2) Tj ET")
    assert got == [
        ("L1 R1 L2 R2",
         [72.0, 82.5, 315.3, 114.5]),
    ]


def test_fused_etbt_operator_leaks(
        tmp_path):
    """缺空格的 'ET'+'BT' 融成单个未知操作符 ETBT：
    ET 不执行、第二 BT 的 Td 相对累计 → R 栏负 y 先出。"""
    got = _els(
        tmp_path, "fz.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (L1) Tj 0 -20 Td (L2) Tj"
        " ET"
        "BT /F1 12 Tf 300 700 Td"
        " (R1) Tj 0 -20 Td (R2) Tj"
        " ET")
    assert got == [
        ("R1 R2",
         [372.0, -597.5,
          387.3, -565.5]),
        ("L1 L2",
         [72.0, 82.5, 85.3, 114.5]),
    ]
