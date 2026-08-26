r"""pipeline 超限 bq/pre 邻居隔离：双侧独
立 sequential、bq 内围栏字面（Round 1799）。

新角度：R1798 锁贴连边界——**'aaa'+
巨引用+'bbb'：3/800/100/3——引用超限
切分与代码块同谱、双侧邻居独立成链不
被吸入；bq 内 '```' 围栏不识别——字面
'```\\ncode\\n```' kind blockquote；
html 巨 pre 同构 3/800/100/3**零
覆盖：

- **巨引用三明治**：4 块、两侧各 3 字
- **bq 内围栏**：paragraph 字面保留
- **html 巨 pre**：与 md 同构
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_bq_oversize_neighbor_isolation(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "aaa\n\n> " + "好" * 900 + "\n\nbbb\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"])
            for c in doc.chunks] == [
        (3, "sequential"),
        (800, "long_paragraph_sentence_split"),
        (100, "long_paragraph_sentence_split"),
        (3, "sequential")]


def test_fence_inside_bq_literal(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("> ```\n> code\n> ```\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [(
        "paragraph", "```\ncode\n```",
        {"kind": "blockquote"})]


def test_html_pre_oversize_neighbor_isolation(
        tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<p>aaa</p><pre>" + "字" * 900
        + "</pre><p>bbb</p>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"])
            for c in doc.chunks] == [
        (3, "sequential"),
        (800, "long_paragraph_sentence_split"),
        (100, "long_paragraph_sentence_split"),
        (3, "sequential")]
