r"""parser md 括号有序标记、md 参差
表补空、text 不解释 # 行（Round
1836）。

新角度：R1835 锁缩进标题退化——**
'1) first' 括号变体识别为 ordered
list_item；md 表 3 列头 2 列行补空
单元 '| 1 | 2 |  |'（与 html 参差
一致）；text 解析器把 '# looks
heading' 当普通段落（家族分工边
界）**零覆盖：

- **括号标记**：ordered True
- **参差 md 表**：行尾补空格单元
- **text 家族**：# 字面段落
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_paren_ordered_marker(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("1) first\n2) second\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "first",
         {"ordered": True, "marker": "ordered"}),
        ("list_item", "second",
         {"ordered": True, "marker": "ordered"})]


def test_md_ragged_table_pads(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "| a | b | c |\n| --- | --- | --- |\n"
        "| 1 | 2 |\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "| a | b | c |\n"
        "| --- | --- | --- |\n| 1 | 2 |  |"]


def test_text_hash_literal(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("# looks heading\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "# looks heading")]
