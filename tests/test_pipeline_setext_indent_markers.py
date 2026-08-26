r"""pipeline md setext 标题、4 空格缩进与
marker 后多空格（Round 1692）。

新角度：R1691 锁空 pre——**setext 下划线
不识别、4 空格缩进不成代码块**零覆盖：

- **'Title\\n==='**：不识别 setext，'==='
  惰性续行并入段落，内嵌换行原样保留
- **'Title\\n---'**：'---' 被 hr 丢弃只留
  'Title' 段落；前置段落后三行全并一段
- **'    code line'**：4 空格缩进被 strip，
  成普通 paragraph（无 code_block kind）；
  空行后的缩进行独立段落但同 chunk
- **'-   item'/'1.  item'**：marker 后多空格
  照常 list_item，内容 strip
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_setext_not_recognized(tmp_path):
    doc, errors = _run(tmp_path, "Title\n===\n")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "Title\n===", {})]

    doc2, errors2 = _run(tmp_path, "Title\n---\n")
    assert errors2 == []
    assert [(e2.type, e2.content, e2.metadata)
            for e2 in doc2.elements] == [
        ("paragraph", "Title", {})]


def test_setext_lazy_merge(tmp_path):
    doc, errors = _run(
        tmp_path, "para text\nTitle\n===\n")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "para text\nTitle\n===")]


def test_indent4_not_code_block(tmp_path):
    doc, errors = _run(tmp_path, "    code line\n")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "code line", {})]

    doc2, errors2 = _run(
        tmp_path, "para\n\n    code line\n")
    assert errors2 == []
    assert [(e2.type, e2.content)
            for e2 in doc2.elements] == [
        ("paragraph", "para"),
        ("paragraph", "code line")]
    assert len(doc2.chunks) == 1


def test_multi_space_after_marker(tmp_path):
    doc, errors = _run(tmp_path, "-   item a\n")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "item a",
         {"ordered": False, "marker": "unordered"})]

    doc2, errors2 = _run(tmp_path, "1.  item b\n")
    assert errors2 == []
    assert [(e2.type, e2.content, e2.metadata)
            for e2 in doc2.elements] == [
        ("list_item", "item b",
         {"ordered": True, "marker": "ordered"})]
