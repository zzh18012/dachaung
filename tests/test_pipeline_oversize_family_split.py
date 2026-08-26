r"""pipeline 超长家族统一切分：li /
code fence / bq 全走 3a 分支 800+100
forced_char（Round 1831）。

新角度：R1830 锁 heading 豁免——**
非标题元素无豁免：900 字 list_item、
代码围栏、引用全走 long_paragraph_
sentence_split，首块 boundary=
forced_char，末块无 boundary 键，
元数据键序一致**零覆盖：

- **li 900**：800 forced + 100
- **fence 900**：同型
- **bq 900**：同型
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def _assert_two_way_split(doc):
    assert [(len(c.text), c.metadata["strategy"],
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (800, "long_paragraph_sentence_split",
         "forced_char"),
        (100, "long_paragraph_sentence_split", None)]
    assert sorted(doc.chunks[0].metadata) == [
        "char_count", "max_chars",
        "split_boundary_after", "strategy"]
    assert sorted(doc.chunks[1].metadata) == [
        "char_count", "max_chars", "strategy"]


def test_oversize_list_item_splits(tmp_path):
    doc, errors = _run(
        tmp_path, "- " + "L" * 900 + "\n")
    assert errors == []
    _assert_two_way_split(doc)


def test_oversize_fence_splits(tmp_path):
    doc, errors = _run(
        tmp_path, "```\n" + "C" * 900 + "\n```\n")
    assert errors == []
    _assert_two_way_split(doc)


def test_oversize_blockquote_splits(tmp_path):
    doc, errors = _run(
        tmp_path, "> " + "Q" * 900 + "\n")
    assert errors == []
    _assert_two_way_split(doc)
