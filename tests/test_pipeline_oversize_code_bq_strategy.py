r"""pipeline 超限代码/引用统一切分策略与
组合隔离（Round 1775）。

新角度：R1774 锁管道行退化——**900 CJK
围栏代码与引用块切分同为
'long_paragraph_sentence_split'（首块
forced_char）；'aaa'+巨码块+'bbb' 组
合：两侧 sequential 独立、中间两块切分
——R1767 隔离模式的策略名印证**零覆盖：

- **'```'+字×900**：800 forced_char +
  100 两块同名策略
- **p+巨码+p**：sequential(3)/800/100/
  sequential(3) 四块
- **'> '+好×900**：800+100 同切
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_oversize_code_split_strategy(tmp_path):
    doc, errors = _run(
        tmp_path, "```\n" + "字" * 900 + "\n```\n")
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"],
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (800, "long_paragraph_sentence_split",
         "forced_char"),
        (100, "long_paragraph_sentence_split", None)]


def test_neighbors_isolated_around_split_code(
        tmp_path):
    doc, errors = _run(
        tmp_path,
        "aaa\n\n```\n" + "字" * 900
        + "\n```\n\nbbb\n")
    assert errors == []
    assert [(len(c.text), len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        (3, 1, "sequential"),
        (800, 1, "long_paragraph_sentence_split"),
        (100, 1, "long_paragraph_sentence_split"),
        (3, 1, "sequential")]


def test_oversize_blockquote_split(tmp_path):
    doc, errors = _run(
        tmp_path, "> " + "好" * 900 + "\n")
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"])
            for c in doc.chunks] == [
        (800, "long_paragraph_sentence_split"),
        (100, "long_paragraph_sentence_split")]
