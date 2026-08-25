r"""app/parsers/fallback_parser.py PDF 边角测试 - 第七十九轮（Round 1509）。

新角度（probe 实证，R1508 Td 累计语义的对照轮；edges43
的 TL/T* 家族测的是全空白操作数，本轮流的是定位语义）：

- **分立 BT 对象的 Td 各自绝对**：'ET BT ... 72 650 Td'
  → bbb 真 y=650，顺序正常 aaa/bbb（与 R1508 同 BT 累
  计对照）
- **TD 相对位移且顺带设 TL**：'0 -50 TD' 后 T* 再走
  -50 → aaa/bbb/ccc 三行各降 50pt、三个独立元素
- **⚠ 紧凑行距行重叠合并**：'0 -20 TD' 的 12pt 字行间
  距 20pt < 行高 → pdfminer 按行盒分组时**三行并成一个
  元素** 'a b c'（空格连接、bbox 高 52pt 跨三行）——
  行距小于行高时元素粒度突变
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


def test_separate_bt_td_absolute(
        tmp_path):
    got = _els(
        tmp_path, "btr.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (aaa) Tj ET"
        " BT /F1 12 Tf 72 650 Td"
        " (bbb) Tj ET")
    assert got == [
        ("aaa",
         [72.0, 82.5, 92.0, 94.5]),
        ("bbb",
         [72.0, 132.5, 92.0, 144.5]),
    ]


def test_td_moves_and_sets_leading(
        tmp_path):
    got = _els(
        tmp_path, "tdo.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (aaa) Tj 0 -50 TD"
        " (bbb) Tj T* (ccc) Tj ET")
    assert [c for c, _ in got] == [
        "aaa", "bbb", "ccc"]
    assert got[0][1][1] == 82.5
    assert got[1][1][1] == 132.5
    assert got[2][1][1] == 182.5


def test_tight_leading_merges_lines(
        tmp_path):
    got = _els(
        tmp_path, "ttl.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (a) Tj 0 -20 TD (b) Tj"
        " T* (c) Tj ET")
    assert got == [
        ("a b c",
         [72.0, 82.5, 78.7, 134.5]),
    ]
