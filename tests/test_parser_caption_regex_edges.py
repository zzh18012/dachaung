r"""题注正则边角——字母编号/前缀陷阱/缩写点（Round 1961，a 优先级）。

`_CAPTION_RE = ^\s*(?:Table|Figure|Fig\.?|表|图)\s*[0-9０-９]+[\.、:\s]`
（fallback_parser.py:50，DOCX/PDF 共用）。edges15 锁
'Figure 1:'/'TABLE 2:' 与全角冒号不匹配；**字母编号**（增刊
Figure S1/A1 常见）、**前缀陷阱**（Tablet）、**缩写点形态**
未锁。探针 R1961 实证：

- **C1 'Figure S1: supplementary'**：数字位是字母 → 不匹
  配 → DOCX 落 paragraph（style Normal）；PDF 级联
  short_line → heading——**增刊题注双格式全漏**
- **C2 'Tablet 1: pad device here'**：Table 后接 t → 不匹
  配 → paragraph（负类不误收）
- **C3 'Fig. 3: caption text'**：Fig\.? 吃点 + 空格 + 数字
  → 匹配 caption（缩写正形态）

判别式：若 regex 放宽到 [0-9A-Za-z] 编号则 C1 翻红；若前
缀改词边界锚定则 C2 行为变（误收消失路径）。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from docx import Document

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf


def _docx(tmp_path: Path, text: str):
    with tempfile.TemporaryDirectory() as td:
        d = Document()
        d.add_paragraph(text)
        p = Path(td) / "c.docx"
        d.save(p)
        return FallbackParser().parse(p, compute_file_hash(p))


def _pdf_parse(tmp_path: Path, text: str):
    p = tmp_path / "c.pdf"
    p.write_bytes(_pdf([f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET".encode("latin-1")]))
    return FallbackParser().parse(p, compute_file_hash(p))


def test_plain_and_abbrev_caption_forms(tmp_path):
    """对照 + C3：'Figure 1:' 与 'Fig. 3:' 均 caption。"""
    d1 = _docx(tmp_path, "Figure 1: plain")
    assert d1.elements[0].type == "caption"
    d3 = _docx(tmp_path, "Fig. 3: caption text")
    assert d3.elements[0].type == "caption"
    assert d3.warnings == []


def test_letter_numbering_misses_both_formats(tmp_path):
    """C1：'Figure S1:'（增刊字母编号）→ DOCX paragraph +
    PDF 级联 heading——双格式全漏。"""
    dd = _docx(tmp_path, "Figure S1: supplementary")
    assert dd.elements[0].type == "paragraph"
    dp = _pdf_parse(tmp_path, "Figure S1: supplementary")
    assert dp.elements[0].type == "heading"
    assert dp.elements[0].metadata == {"level": 0, "heuristic": "short_line"}
    assert dp.warnings == []


def test_prefix_trap_not_caption(tmp_path):
    """C2：'Tablet 1:' 前缀陷阱 → 不误收 → paragraph。"""
    d = _docx(tmp_path, "Tablet 1: pad device here")
    assert d.elements[0].type == "paragraph"
    assert d.elements[0].content == "Tablet 1: pad device here"
    assert d.warnings == []
