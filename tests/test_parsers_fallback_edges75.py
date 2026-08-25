r"""app/parsers/fallback_parser.py PDF 边角测试 - 第七十五轮（Round 1500，里程碑轮）。

新角度（probe 实证）内容流 tokenization 鲁棒性（edges1-74
未碰）：

- **无空格 token 全容忍**：'(compact)Tj' / 'BT/F1 12 Tf'
  → 照常提取（PSBaseParser 按类型切词，不依赖空白）
- **换行/纯 CR 分隔照常**：\\n 与 \\r 做分隔符均可
- **% 注释透明**：行首注释与**操作数之间**的行内注释
  （'12 % size\\n Tf'）均跳过
- **重复 Tj 只显示一次**：'(a) Tj Tj' → 'a'（第二次 Tj
  弹空栈无效，不重复）
- **连续 Td 取最后位置**：两个 Td → 文本落在第二个位置
  （600 偏移不进 content，仅定位）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

from tests.test_parsers_fallback_edges66 \
    import _pdf


def _contents(tmp_path, name, content):
    p = _pdf(tmp_path, name, content)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    return ([e.content
             for e in doc.elements],
            [w.code for w in doc.warnings])


# ---------- 紧凑 token ----------

def test_no_space_tokens(tmp_path):
    got, warns = _contents(
        tmp_path, "ns.pdf",
        "BT/F1 12 Tf 72 700 Td"
        "(compact)Tj ET")
    assert got == ["compact"]
    assert warns == []


def test_op_no_space_after_operand(
        tmp_path):
    got, _ = _contents(
        tmp_path, "ns2.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (x)Tj ET")
    assert got == ["x"]


# ---------- 分隔符形态 ----------

def test_newline_separated_ops(
        tmp_path):
    got, warns = _contents(
        tmp_path, "nl.pdf",
        "BT\n/F1 12 Tf\n72 700 Td\n"
        "(multi)\nTj\nET")
    assert got == ["multi"]
    assert warns == []


def test_cr_only_separators(
        tmp_path):
    got, _ = _contents(
        tmp_path, "cr.pdf",
        "BT\r/F1 12 Tf\r72 700 Td\r"
        "(cr)\rTj\rET")
    assert got == ["cr"]


# ---------- 注释 ----------

def test_line_comment_skipped(
        tmp_path):
    got, _ = _contents(
        tmp_path, "c1.pdf",
        "% c\nBT /F1 12 Tf 72 700"
        " Td (after comment) Tj ET")
    assert got == ["after comment"]


def test_inline_comment_between_args(
        tmp_path):
    got, warns = _contents(
        tmp_path, "c2.pdf",
        "BT /F1 12 % size\n Tf"
        " 72 700 Td (mid) Tj ET")
    assert got == ["mid"]
    assert warns == []


# ---------- 重复操作符 ----------

def test_double_tj_shows_once(
        tmp_path):
    got, warns = _contents(
        tmp_path, "dt.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (a) Tj Tj ET")
    assert got == ["a"]
    assert warns == []


def test_double_td_last_wins(
        tmp_path):
    got, _ = _contents(
        tmp_path, "dd.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " 72 650 Td"
        " (after two td) Tj ET")
    assert got == ["after two td"]
