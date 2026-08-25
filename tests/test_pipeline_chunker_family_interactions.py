r"""pipeline 分块器 × 家族元数据交互（Round 1611）。

新角度：R1610 锁 ipynb 单元边角——**caption 识别
仅限 fallback、家族共享 heading 累积、text 词界拆分**
零覆盖：

- **markdown 的 'Table 1: …' 不是 caption**：
  caption 检测只活在 fallback 解析器（R1593 的
  PDF/DOCX），md 中是普通段落并入 sequential
- **md heading + 段落合并**：与 PDF 相同的
  heading 累积规则（R1595）跨家族生效
- **text 超长段**（1799 字符）：11 字符词 + 空格
  → 66 词恰 791，拆 791/791/215（词界非 800 硬切）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, text, parser):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name=parser)
    assert errors == []
    return doc


def test_md_caption_like_not_caption(
        tmp_path):
    doc = _run(
        tmp_path, "c.md",
        "Before.\n\nTable 1: caption text\n\n"
        "After.\n", "markdown")
    assert [(e.type, e.metadata)
            for e in doc.elements] == [
        ("paragraph", {}), ("paragraph", {}),
        ("paragraph", {})]
    (c,) = doc.chunks
    assert c.text == (
        "Before. Table 1: caption text After.")
    assert c.metadata["strategy"] == "sequential"
    assert len(c.source_element_ids) == 3


def test_md_heading_para_merge(tmp_path):
    doc = _run(
        tmp_path, "h.md",
        "# Head\n\nBody follows.\n", "markdown")
    (c,) = doc.chunks
    assert c.text == "Head Body follows."
    assert c.metadata["strategy"] == "sequential"
    assert len(c.source_element_ids) == 2
    assert doc.elements[0].type == "heading"


def test_text_oversize_split(tmp_path):
    words = [f"txtword{i:04d}"
             for i in range(150)]
    doc = _run(
        tmp_path, "t.txt",
        " ".join(words) + "\n", "text")
    el = doc.elements[0]
    assert len(el.content) == 1799
    got = [len(c.text) for c in doc.chunks]
    assert got == [791, 791, 215]
    for c in doc.chunks:
        assert c.metadata["strategy"] == (
            "long_paragraph_sentence_split")
        (sp,) = c.source_spans
        assert c.text == (
            el.content[sp["start"]:sp["end"]])
    assert doc.chunks[1].text.startswith(
        "txtword0066")
    assert doc.chunks[2].text.startswith(
        "txtword0132")
