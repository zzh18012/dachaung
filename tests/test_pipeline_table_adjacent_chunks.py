r"""pipeline 真表恒孤立、pipe 退化为段
落、邻接三块型（Round 1829）。

新角度：R1828 锁 isolated_table 策略
名——**首探误读（1-col pipe 当表），
读 chunker 源码 + 复探纠正：单列
pipe 行是 paragraph 非 table；真
（≥2 列）表恒 isolated_table，前后
邻居各成 sequential 块，永不合并**
零覆盖：

- **单列 pipe**：paragraph 元素
- **头+表+段**：3 块 [seq, iso, seq]
- **表+段 / 段+表+段**：2 块 / 3 块
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_single_col_pipe_is_paragraph(tmp_path):
    doc, errors = _run(tmp_path, "| a |\n| --- |\n")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "| a |\n| --- |")]
    assert doc.chunks[0].metadata["strategy"] == \
        "sequential"


def test_head_table_para_three_chunks(tmp_path):
    doc, errors = _run(
        tmp_path,
        "# T\n\n| a | b |\n| --- | --- |\n\nafter\n")
    assert errors == []
    assert [(c.text, len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        ("T", 1, "sequential"),
        ("| a | b |\n| --- | --- |", 1,
         "isolated_table"),
        ("after", 1, "sequential")]


def test_table_neighbors_never_merge(tmp_path):
    doc, errors = _run(
        tmp_path,
        "| a | b |\n| --- | --- |\n\nafter\n")
    assert errors == []
    assert [(len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        (1, "isolated_table"), (1, "sequential")]
    doc, errors = _run(
        tmp_path,
        "p1\n\n| a | b |\n| --- | --- |\n\np2\n")
    assert errors == []
    assert [(c.text, c.metadata["strategy"])
            for c in doc.chunks] == [
        ("p1", "sequential"),
        ("| a | b |\n| --- | --- |",
         "isolated_table"),
        ("p2", "sequential")]
