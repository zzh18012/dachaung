r"""pipeline 切分块真实偏移、md bq kind
元数据、bq 内结构不解析（Round 1791）。

新角度：R1790 锁 dl/尾井号——**切分块
spans 是元素相对真实偏移：(0,723) 与
(724,1007)——边界空格 723 被跳过（与合
并块 start=0 退化形成对照）；md '> x'
是 paragraph + kind='blockquote'
（html bq 无 kind，家族有差）；bq 内
'## T'/'| 表 |' 不解析——标题表格全
字面成段**零覆盖：

- **723+283 切分**：spans (0,723)/
  (724,1007) 同元素 id
- **'> body'**：kind='blockquote'
- **bq 内表格**：整块字面段落
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _sent():
    return " ".join(
        "S%d. %s" % (i, " ".join(f"w{i}_{j}" for j in range(25)))
        for i in range(7))


def test_split_chunk_true_offsets(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("## T\n\n" + _sent() + "\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(len(c.text),
             [(s["start"], s["end"]) for s in c.source_spans])
            for c in doc.chunks] == [
        (1, [(0, 1)]),
        (723, [(0, 723)]),
        (283, [(724, 1007)])]
    para_id = doc.elements[1].element_id
    assert all(
        s["element_id"] == para_id
        for c in doc.chunks[1:] for s in c.source_spans)


def test_md_blockquote_kind_metadata(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("> body\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "body", {"kind": "blockquote"})]
    assert doc.elements[0].source_locator == {
        "line": 1}


def test_bq_inner_structures_literal(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "> ## T\n> | a | b |\n> | --- | --- |\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [(
        "paragraph",
        "## T\n| a | b |\n| --- | --- |",
        {"kind": "blockquote"})]
    assert doc.chunks[0].metadata["strategy"] == (
        "sequential")
