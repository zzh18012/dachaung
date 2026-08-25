r"""app/parsers/fallback_parser.py PDF 边角测试 - 第七十八轮（Round 1508）。

新角度（probe 实证，修正 R1494/R1495 的解释误差）：

- **连续 Td 是相对位移（累计）**：同一 BT 内 '72 700 Td'
  后再 '72 650 Td' → 第二行**绝对 y=1350**（不是 650），
  超出 MediaBox(792) → 变换后 bbox y 为**负**（-567.52），
  输出顺序第二行先出（页面上方优先）
- **Tm 是绝对重置**：'1 0 0 1 72 650 Tm' → 真正 y=650，
  bbox y=132.48，顺序正常 aaa 先出
- **解释修正**：R1494 tr3 顺序倒置 / R1495"页内 y 升
  序"实为**自上而下阅读顺序**——当时探针的两个 Td 累
  计把第二行放到了比预期高 650pt 处；本轮 Tm 对照组证
  实。既有 observables 不变，仅因果解释更正
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
             [round(v, 2)
              for v in
              e.source_locator["bbox"]])
            for e in doc.elements]


def test_consecutive_td_cumulative(
        tmp_path):
    got = _els(
        tmp_path, "tdc.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (aaa) Tj 72 650 Td"
        " (bbb) Tj ET")
    assert got == [
        ("bbb",
         [144.0, -567.52,
          164.02, -555.52]),
        ("aaa",
         [72.0, 82.48,
          92.02, 94.48]),
    ]


def test_tm_absolute_reset(tmp_path):
    got = _els(
        tmp_path, "tmr.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (aaa) Tj"
        " 1 0 0 1 72 650 Tm"
        " (bbb) Tj ET")
    assert got == [
        ("aaa",
         [72.0, 82.48,
          92.02, 94.48]),
        ("bbb",
         [72.0, 132.48,
          92.02, 144.48]),
    ]


def test_td_delta_one_line_down(
        tmp_path):
    """负 delta 的 Td 累计：700 + (-50) = 650 正常下一行。"""
    got = _els(
        tmp_path, "tdd.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (aaa) Tj 0 -50 Td"
        " (bbb) Tj ET")
    assert [c for c, _ in got] == [
        "aaa", "bbb"]
    assert got[1][1][0] == 72.0
    assert got[1][1][3] > got[0][1][3]
