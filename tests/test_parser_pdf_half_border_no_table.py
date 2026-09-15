r"""PDF 半边框不成表——仅竖线/仅横线/不相交线框（Round 1951，a 优先级）。

edges104 锁完整网格成表；R1942 K3 锁散置 rect 不成表；
**单方向线条 / 线条不相交**（坏转换常见形态）零覆盖（广扫
仅竖/仅横/vertical-only 全形）。探针 R1951 实证——三形态同
归**不成表**（pdfplumber lines 策略需 H×V 相交成 cell）：

- **V1 仅竖线**：3 竖跨 620-700 + 四词 → 无 table 元素、
  两 heading 'AA BB'/'CC DD'、零告警
- **H1 仅横线**：3 横 + 同文本 → 同 V1
- **X1 不相交**：横在 620/700、竖缩短 630-690（不接触横
  线）→ 同 V1（端点接触才计数，短一截即整表消失）

判别式：若 find_tables 引入半边框/单方向容忍则元素序断言
翻红（出现 table）；对照 edges104 完整网格会成表。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf

_XS = [100.0, 250.0, 400.0, 550.0]


def _content(mode: str) -> bytes:
    parts = ["1 w 0 0 0 RG"]
    if mode == "V":
        for x in _XS:
            parts.append(f"{x:.1f} 620.0 m {x:.1f} 700.0 l S")
    elif mode == "H":
        for y in (700.0, 660.0, 620.0):
            parts.append(f"{_XS[0]} {y:.1f} m {_XS[-1]} {y:.1f} l S")
    else:
        for y in (700.0, 620.0):
            parts.append(f"{_XS[0]} {y:.1f} m {_XS[-1]} {y:.1f} l S")
        for x in _XS:
            parts.append(f"{x:.1f} 630.0 m {x:.1f} 690.0 l S")
    for x, y, t in [(120.0, 675.0, "AA"), (270.0, 675.0, "BB"),
                    (120.0, 635.0, "CC"), (270.0, 635.0, "DD")]:
        parts.append(f"BT /F1 12 Tf {x:.1f} {y:.1f} Td ({t}) Tj ET")
    return "\n".join(parts).encode("latin-1")


def _assert_no_table(tmp_path: Path, mode: str):
    p = tmp_path / "h.pdf"
    p.write_bytes(_pdf([_content(mode)]))
    d = FallbackParser().parse(p, compute_file_hash(p))
    assert [e.type for e in d.elements] == ["heading", "heading"]
    assert [e.content for e in d.elements] == ["AA BB", "CC DD"]
    assert d.warnings == []


def test_verticals_only_no_table(tmp_path):
    """V1：仅竖线 → 无 table、两 heading、零告警。"""
    _assert_no_table(tmp_path, "V")


def test_horizontals_only_no_table(tmp_path):
    """H1：仅横线 → 同 V1 不成表。"""
    _assert_no_table(tmp_path, "H")


def test_nonintersecting_lines_no_table(tmp_path):
    """X1：竖线缩短不接触横线 → 整表消失（端点接触才计数）。"""
    _assert_no_table(tmp_path, "X")
