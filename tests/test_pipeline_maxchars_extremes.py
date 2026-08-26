r"""pipeline max_chars 极值：负值、十亿
巨值与字符串类型（Round 1762）。

新角度：R1761 锁 32 下限——**负值同
chunker_failed 壳（'过小： -5'）；
10**9 巨值三段全并 'aaa bbb ccc'（3
ids）；字符串 '800' 触发 TypeError 也走
chunker_failed（details exception_type
'TypeError'）**零覆盖：

- **-5**：message '分块失败： max_chars
  过小： -5'
- **10**9**：单 chunk 三源
- **'800'**：message 含 "'<' not
  supported"
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _mk(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("aaa\n\nbbb\n\nccc\n", encoding="utf-8")
    return p


def test_negative_rejected(tmp_path):
    p = _mk(tmp_path)
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown",
        max_chars=-5)
    assert doc is None
    e = errors[0]
    assert e.code == "chunker_failed"
    assert e.message == "分块失败: max_chars 过小: -5"
    assert e.details == {"exception_type": "ValueError"}


def test_huge_value_merges_all(tmp_path):
    p = _mk(tmp_path)
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown",
        max_chars=10**9)
    assert errors == []
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("aaa bbb ccc", 3)]


def test_string_type_typeerror(tmp_path):
    p = _mk(tmp_path)
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown",
        max_chars="800")
    assert doc is None
    e = errors[0]
    assert e.code == "chunker_failed"
    assert "'<' not supported" in e.message
    assert e.details == {"exception_type": "TypeError"}
