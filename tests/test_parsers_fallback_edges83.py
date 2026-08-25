r"""app/parsers/fallback_parser.py PDF 边角测试 - 第八十三轮（Round 1513）。

新角度（probe 实证）TJ 数组 kern 数字语义（edges43 只
测过 [()] TJ 空数组；数字位移从未测过）：

- **小正 kern 直接拼接**：[(K) 2 (e) 2 (rn)] → 'Kern'
  单元素无空格
- **⚠ 亚字符宽位移字符交织**：[(left) 300 (right)] →
  'lefrtight'（300/1000×12pt=3.6pt < 字宽 → 字符按 x
  排序交织、无空格）
- **负 kern（右移）正常拼**：[(AB) -100 (CD)] → 'ABCD'
- **⚠ 正 kern 是左移**：[(aa) 8000 (bb)] → 'bb aa'、
  bbox x0=-10.7（规范语义：位移从当前 x 减去，正数收
  紧/左移——与直觉相反）；8000/1000×12=96pt
- **巨 kern 推出页外**：50000（600pt）→ x0=-514.7 仍
  提取
- **纯数字无字符串**：[50 -20] → 零元素 +
  pdf_no_text_extracted
- **TJ+Tj 连续**：[(one)] TJ (two) Tj → 'onetwo'
- **混合正负三组**：[(A) 4000 (B) -4000 (C)] → 'B A C'
  （B 左移 48pt、C 右移回，三组空格连接按 x 排序）
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
            for e in doc.elements], \
        [w.code for w in doc.warnings]


def test_tj_small_kerns_join(
        tmp_path):
    got, warns = _els(
        tmp_path, "tj1.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " [(K) 2 (e) 2 (rn)] TJ ET")
    assert got == [
        ("Kern",
         [72.0, 82.5, 97.3, 94.5])]
    assert warns == []


def test_tj_tiny_kern_interleave(
        tmp_path):
    got, _ = _els(
        tmp_path, "tj2.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " [(left) 300 (right)] TJ ET")
    assert got == [
        ("lefrtight",
         [72.0, 82.5, 107.7, 94.5])]


def test_tj_negative_kern_join(
        tmp_path):
    got, _ = _els(
        tmp_path, "tj3.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " [(AB) -100 (CD)] TJ ET")
    assert got == [
        ("ABCD",
         [72.0, 82.5, 106.5, 94.5])]


def test_tj_positive_kern_moves_left(
        tmp_path):
    got, _ = _els(
        tmp_path, "tj4.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " [(aa) 8000 (bb)] TJ ET")
    assert got == [
        ("bb aa",
         [-10.7, 82.5, 85.3, 94.5])]


def test_tj_huge_kern_off_page(
        tmp_path):
    got, _ = _els(
        tmp_path, "tj5.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " [(aa) 50000 (bb)] TJ ET")
    assert got == [
        ("bb aa",
         [-514.7, 82.5, 85.3, 94.5])]


def test_tj_numbers_only_empty(
        tmp_path):
    got, warns = _els(
        tmp_path, "tj6.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " [50 -20] TJ ET")
    assert got == []
    assert warns == [
        "pdf_no_text_extracted"]


def test_tj_then_tj_continuous(
        tmp_path):
    got, _ = _els(
        tmp_path, "tj7.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " [(one)] TJ (two) Tj ET")
    assert got == [
        ("onetwo",
         [72.0, 82.5, 110.7, 94.5])]


def test_tj_mixed_signs_groups(
        tmp_path):
    got, _ = _els(
        tmp_path, "tj8.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " [(A) 4000 (B) -4000 (C)]"
        " TJ ET")
    assert got == [
        ("B A C",
         [32.0, 82.5, 96.7, 94.5])]
