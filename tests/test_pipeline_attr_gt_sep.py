r"""pipeline 属性值含 &gt; 与孤分隔行
（Round 1682）。

新角度：R1681 锁 info 空格/实体——**引号内
'&gt;' 容忍、'| --- |' 无表头不成表**零
覆盖：

- **属性含 '&gt;'**：'title="a&gt;b"' 引
  号保护，照常解析 paragraph 'x'
- **孤分隔行贴段**：lazy 并入段落
  'text\\n| --- | --- |'
- **分隔行独占文件**：单 paragraph 原样
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_attr_value_with_gt(tmp_path):
    p = tmp_path / "d.html"
    p.write_text('<p title="a>b">x</p>',
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "x", {})]


def test_lone_separator_lazy(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("text\n| --- | --- |\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "text\n| --- | --- |", {})]


def test_separator_only_file(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("| --- | --- |\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "| --- | --- |", {})]
