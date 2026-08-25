r"""pipeline Markdown 标记变体：7 级标题/
子弹字符/括号序号（Round 1629）。

新角度：R1628 锁表格边角——**####### 超级
标题、* + - 子弹、'1)' 括号序号、混合标记**
零覆盖：

- **7 个 # 不是标题**：层级封顶 6，'#######'
  → 段落 raw
- **三种子弹字符**（* + -）均识别为
  unordered
- **'1)' 括号式序号识别为 ordered**；
  混合标记列表逐项保型（不重编号不合并）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    return doc


def test_h7_not_heading(tmp_path):
    doc = _run(
        tmp_path, "####### seven\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "####### seven", {})]


def test_bullet_variety(tmp_path):
    doc = _run(
        tmp_path, "* star\n+ plus\n- dash\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "star",
         {"ordered": False,
          "marker": "unordered"}),
        ("list_item", "plus",
         {"ordered": False,
          "marker": "unordered"}),
        ("list_item", "dash",
         {"ordered": False,
          "marker": "unordered"})]


def test_paren_ordered_and_mixed(tmp_path):
    doc = _run(
        tmp_path, "1) paren\n2) next\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "paren",
         {"ordered": True,
          "marker": "ordered"}),
        ("list_item", "next",
         {"ordered": True,
          "marker": "ordered"})]

    doc2 = _run(
        tmp_path, "1. one\n* two\n")
    assert [(e.metadata["ordered"],
             e.content)
            for e in doc2.elements] == [
        (True, "one"), (False, "two")]
