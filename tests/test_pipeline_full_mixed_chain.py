r"""pipeline 全类型混合链：标题+段+列表+
引用+代码+尾段单块；span 退化全景
（Round 1816）。

新角度：R1815 锁警告保序——**'## T'+
para+'- li'+'> q'+'```c```'+tail 六
元素全部一块 'T para li q c tail'（6
ids sequential）；每元素 span start=0、
end=自身长度——合并块 span 退化在 6
元素全景下复证；bq/代码元素类型均为
paragraph（kind 区分）**零覆盖：

- **六元一块**：单 chunk 全成员
- **spans**：[(0,1),(0,4),(0,2),(0,1),
  (0,1),(0,4)]
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single

TEXT = ("## T\n\npara\n\n- li\n\n> q\n\n"
        "```\nc\n```\n\ntail\n")


def test_full_mixed_chain_one_chunk(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(TEXT, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "heading", "paragraph", "list_item",
        "paragraph", "paragraph", "paragraph"]
    assert [(c.text, len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        ("T para li q c tail", 6, "sequential")]


def test_mixed_chain_spans_degenerate(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(TEXT, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    chunk = doc.chunks[0]
    assert [(s["start"], s["end"])
            for s in chunk.source_spans] == [
        (0, 1), (0, 4), (0, 2), (0, 1),
        (0, 1), (0, 4)]
    assert [s["element_id"] for s in
            chunk.source_spans] == [
        e.element_id for e in doc.elements]
