r"""pipeline chunk strategy 全谱三值：
sequential / long_paragraph_sentence_split /
isolated_table（Round 1773）。

新角度：R1772 锁表格豁免——**strategy
仅三值：合并链一切成员 'sequential'（段/
列表/代码/引用/标题拉段）；超限元素切分
'long_paragraph_sentence_split'（词界与
CJK forced_char 同名）；真表格
'isolated_table'**零覆盖：

- **短段/列表/代码/引用各单独**：全
  'sequential'
- **1019 词段与 900 CJK**：两块均
  'long_paragraph_sentence_split'
- **'## T'+'bbb'**：'sequential'；表：
  'isolated_table'
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_chain_members_all_sequential(tmp_path):
    for text in ["x\n", "- a\n", "```\nc\n```\n",
                 "> q\n"]:
        doc, errors = _run(tmp_path, text)
        assert errors == []
        assert all(
            c.metadata["strategy"] == "sequential"
            for c in doc.chunks), text


def test_oversize_split_strategy(tmp_path):
    doc, errors = _run(
        tmp_path,
        " ".join(f"w{i}" for i in range(226)) + "\n")
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"])
            for c in doc.chunks] == [
        (799, "long_paragraph_sentence_split"),
        (219, "long_paragraph_sentence_split")]

    doc, errors = _run(tmp_path, "好" * 900 + "\n")
    assert errors == []
    assert [c.metadata["strategy"]
            for c in doc.chunks] == [
        "long_paragraph_sentence_split",
        "long_paragraph_sentence_split"]
    assert doc.chunks[0].metadata[
        "split_boundary_after"] == "forced_char"


def test_pull_sequential_table_isolated(tmp_path):
    doc, errors = _run(
        tmp_path,
        "## T\n\nbbb\n\n| a | b |\n| --- | --- |\n")
    assert errors == []
    assert [c.metadata["strategy"]
            for c in doc.chunks] == [
        "sequential", "isolated_table"]
