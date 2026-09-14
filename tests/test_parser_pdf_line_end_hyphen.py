r"""PDF 行尾连字符不做 dehyphenation 锁定（Round 1901，a 优先级）。

grep 零覆盖（fence-info 的连字符是 markdown 信息串；kreuzberg edges
的连字符是终止符测试——均非 PDF 行尾连字符合并语义）。现实高频：
 justified/印刷文本的断词换行。探针 R1901 实证（`_lines_to_para`
:168 行间 `" ".join`——无任何连字符合并逻辑）：

- **行尾连字符保留 + 插空格**：'inter-'（行 1 尾）+ 'national'
  （行 2 首）同段落 → **'inter- national'**——连字符原样保留且后跟
  空格，"international" 在提取文本里不可检索
- **同行连字符完好**：单行 'inter-national' 原样（无空格插入）
- **e2e 真实 PDF**：两行断词（紧邻成段）+ 远处第二段 →
  ['inter- national', 'second para']
"""

from __future__ import annotations

from pathlib import Path

from app.parsers.fallback_parser import _group_words_to_paragraphs, _parse_pdf
from tests.test_backlog_pdf_crosspage_table import _build_pdf


def _w(text: str, x0: float, top: float, bottom: float) -> dict:
    return {"text": text, "x0": x0, "x1": x0 + 8 * len(text), "top": top, "bottom": bottom}


def test_pdf_line_end_hyphen_not_joined():
    """行尾 'inter-' + 次行首 'national'（同段落间距）→ 'inter- national'
    ——连字符保留、空格插入、无 dehyphenation。"""
    paras = _group_words_to_paragraphs([
        _w("inter-", 0, 0, 8),
        _w("national", 0, 9, 17),
    ])
    assert [p["text"] for p in paras] == ["inter- national"]


def test_pdf_same_line_hyphen_intact():
    """对照：单行 'inter-national' 原样保留（无空格插入）。"""
    paras = _group_words_to_paragraphs([_w("inter-national", 0, 0, 8)])
    assert [p["text"] for p in paras] == ["inter-national"]


def test_pdf_hyphen_end_to_end_real_pdf(tmp_path):
    """e2e：真实 PDF 断词两行紧邻成段 + 远处第二段 →
    ['inter- national', 'second para']。"""
    content = "\n".join([
        "BT /F1 12 Tf 50 740 Td (inter-) Tj ET",
        "BT /F1 12 Tf 50 726 Td (national) Tj ET",
        "BT /F1 12 Tf 50 620 Td (second para) Tj ET",
    ]).encode("latin-1")
    pdf_path = tmp_path / "hyph.pdf"
    pdf_path.write_bytes(_build_pdf([content]))
    elements, warnings = _parse_pdf(pdf_path, "sha" * 21, "doc-x", None)
    assert [e.content for e in elements] == ["inter- national", "second para"]
    assert all(e.type == "heading" for e in elements)
    assert warnings == []
