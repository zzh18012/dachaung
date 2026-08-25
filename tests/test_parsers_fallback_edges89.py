r"""app/parsers/fallback_parser.py PDF 边角测试 - 第八十九轮（Round 1519）。

新角度（probe 实证）Tc 字距与 Tw 词距操作符（此前轮
次测过 Tz/Ts/TL 但从未碰 Tc/Tw）：

- **Tc 2 正常**：'(ab cd)' → 'ab cd'（bbox 宽 37.4）
- **⚠ Tc 30 字距炸开插空格**：'(ab)' → 'a b'（每字符
  +30pt → pdfplumber 判定字符间隙为词界插入空格）
- **⚠ Tc 负值字符反转**：-8 Tc '(ab)' → 'ba'（b 起点
  提前到 70.7 < a 的 72 → x 排序倒置）
- **Tw 80 宽词距仍单元素**：'(a b)' → 'a b'（bbox 跨
  96.7pt 但同行不分裂）
- **⚠ Tw 负值空格消失**：-10 Tw '(a b)' → 'ab'（空格
  宽度 3.33-10 < 0 → 相邻词无缝贴合、无空格）
- **Tw 驱动空格位移**：50 Tw '( ) Tj (x) Tj' → x0=
  125.3（纯空格 Tj 不出元素但推进 53.3pt）
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


def test_tc_small_normal(tmp_path):
    got = _els(
        tmp_path, "tc2.pdf",
        "BT /F1 12 Tf 2 Tc 72 700 Td"
        " (ab cd) Tj ET")
    assert got == [
        ("ab cd",
         [72.0, 82.5, 109.4, 94.5])]


def test_tc_huge_splits_chars(
        tmp_path):
    got = _els(
        tmp_path, "tc30.pdf",
        "BT /F1 12 Tf 30 Tc 72 700"
        " Td (ab) Tj ET")
    assert got == [
        ("a b",
         [72.0, 82.5, 115.3, 94.5])]


def test_tc_negative_reverses(
        tmp_path):
    got = _els(
        tmp_path, "tcneg.pdf",
        "BT /F1 12 Tf -8 Tc 72 700"
        " Td (ab) Tj ET")
    assert got == [
        ("ba",
         [70.7, 82.5, 78.7, 94.5])]


def test_tw_huge_single_element(
        tmp_path):
    got = _els(
        tmp_path, "tw80.pdf",
        "BT /F1 12 Tf 80 Tw 72 700"
        " Td (a b) Tj ET")
    assert got == [
        ("a b",
         [72.0, 82.5, 168.7, 94.5])]


def test_tw_negative_collapses(
        tmp_path):
    got = _els(
        tmp_path, "twneg.pdf",
        "BT /F1 12 Tf -10 Tw 72 700"
        " Td (a b) Tj ET")
    assert got == [
        ("ab",
         [72.0, 82.5, 78.7, 94.5])]


def test_tw_space_displacement(
        tmp_path):
    got = _els(
        tmp_path, "twonly.pdf",
        "BT /F1 12 Tf 50 Tw 72 700"
        " Td ( ) Tj (x) Tj ET")
    assert got == [
        ("x",
         [125.3, 82.5, 131.3, 94.5])]
