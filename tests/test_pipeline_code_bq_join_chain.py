r"""pipeline 代码块与引用块完整入合并链
（Round 1737）。

新角度：R1736 锁表格唯一打断——**代码块
与引用块都是链的正式成员：p+code+p →
'aaa code bbb'（3 ids）、p+bq+p → 'aaa
q bbb'（3 ids）、heading+code+p → 'T c
bbb'（3 ids）、bq+p → 'q bbb'（2 ids）**
零覆盖：

- **'aaa'+围栏代码+'bbb'**：单 chunk 三
  源（code_block 不打断、不旁路）
- **'aaa'+'> q'+'bbb'**：单 chunk 三源
- **'## T'+code+'bbb'**：标题链穿过代
  码块继续拉段
- **'> q'+'bbb'**：引用块作链首
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_code_block_joins_chain(tmp_path):
    doc, errors = _run(
        tmp_path, "aaa\n\n```\ncode\n```\n\nbbb\n")
    assert errors == []
    assert [(e.type, e.metadata.get("kind"))
            for e in doc.elements] == [
        ("paragraph", None), ("paragraph", "code_block"),
        ("paragraph", None)]
    assert len(doc.chunks) == 1
    assert doc.chunks[0].text == "aaa code bbb"
    assert len(doc.chunks[0].source_element_ids) == 3


def test_blockquote_joins_chain(tmp_path):
    doc, errors = _run(tmp_path, "aaa\n\n> q\n\nbbb\n")
    assert errors == []
    assert [(e.type, e.metadata.get("kind"))
            for e in doc.elements] == [
        ("paragraph", None), ("paragraph", "blockquote"),
        ("paragraph", None)]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("aaa q bbb", 3)]


def test_heading_chain_crosses_code(tmp_path):
    doc, errors = _run(
        tmp_path, "## T\n\n```\nc\n```\n\nbbb\n")
    assert errors == []
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("T c bbb", 3)]


def test_blockquote_as_chain_head(tmp_path):
    doc, errors = _run(tmp_path, "> q\n\nbbb\n")
    assert errors == []
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("q bbb", 2)]
