r"""pipeline 列表元数据与 text 段落分割（Round 1599）。

新角度：R1598 锁 markdown raw——**列表 marker
元数据、text 段落分割规则、空 text**零覆盖：

- **markdown 列表**：有序项 {'ordered': True,
  'marker': 'ordered'}、无序项 {'ordered': False,
  'marker': 'unordered'}（编号/符号本身剥除）
- **text 解析器**：空行分段（3 段）；单个换行
  保留在同段内
- **空 .txt** → no_extracted_elements
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, text,
         parser):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False,
        parser_name=parser)
    return doc, errors


def test_markdown_list_markers(
        tmp_path):
    doc, errors = _run(
        tmp_path, "l.md",
        "1. first\n2. second\n\n"
        "- bullet\n",
        "markdown")
    assert errors == []
    got = [(e.type, e.content,
            e.metadata)
           for e in doc.elements]
    assert got == [
        ("list_item", "first",
         {"ordered": True,
          "marker": "ordered"}),
        ("list_item", "second",
         {"ordered": True,
          "marker": "ordered"}),
        ("list_item", "bullet",
         {"ordered": False,
          "marker": "unordered"})]


def test_text_blank_line_splits(
        tmp_path):
    doc, errors = _run(
        tmp_path, "p.txt",
        "Para one.\n\nPara two.\n\n"
        "Para three.\n",
        "text")
    assert errors == []
    got = [e.content
           for e in doc.elements]
    assert got == [
        "Para one.", "Para two.",
        "Para three."]

    doc2, errors2 = _run(
        tmp_path, "s.txt",
        "Plain line.\nAnother.",
        "text")
    assert errors2 == []
    (el,) = doc2.elements
    assert el.content == (
        "Plain line.\nAnother.")


def test_empty_text_file(tmp_path):
    doc, errors = _run(
        tmp_path, "e.txt", "",
        "text")
    assert doc is None
    assert [e.code
            for e in errors] == [
        "no_extracted_elements"]
