r"""pipeline 分隔线变体扩展与嵌套空容器
（Round 1685）。

新角度：R1684 锁空标题——**'\\*\\*\\*\\*'
四星、'- - -' 带空格破折号都是分隔线、嵌
套空 div 整体无内容**零覆盖：

- **'\\*\\*\\*\\*'**：分隔线丢弃（R1642
  三星版的延伸）
- **'- - -'**：带空格破折号同样丢弃（不
  成列表）
- **嵌套空容器**：'&lt;div&gt;&lt;div&gt;
  &lt;/div&gt;&lt;/div&gt;' → html_no_
  content
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_four_stars_hr(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("a\n\n****\n\nb\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "a"), ("paragraph", "b")]


def test_spaced_dashes_hr(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("a\n\n- - -\n\nb\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "a"), ("paragraph", "b")]


def test_nested_empty_containers(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<div><div></div></div>",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    assert [w["code"] for w in
            errors[0].details["warnings"]] == [
        "html_no_content"]
