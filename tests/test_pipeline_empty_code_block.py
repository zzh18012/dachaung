r"""pipeline 空代码块警告 md_empty_code_block
（Round 1690）。

新角度：R1689 锁跨行注释——**'```py\\n```'
空块触发第 8 个警告码、行号入 reason、纯
空白块不算空**零覆盖：

- **空块独占文件**：warnings = [
  md_empty_code_block（line 1）,
  md_no_content]，doc None
- **空块夹在段落间**：成功路径 doc.warnings
  携带 'line 3 处的代码块为空'，段落照常
- **纯空白块**：'   ' 成 paragraph 内容，
  不警告；两个空块各自一条警告
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_empty_fence_alone(tmp_path):
    doc, errors = _run(tmp_path, "```py\n```\n")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    ws = errors[0].details["warnings"]
    assert [(w["code"], w["reason"]) for w in ws] == [
        ("md_empty_code_block",
         "line 1 处的代码块为空"),
        ("md_no_content",
         "Markdown 文件未提取到任何 element"
         "（可能为空文件或仅含主题分隔符）")]


def test_empty_fence_between_paragraphs(tmp_path):
    doc, errors = _run(
        tmp_path, "a\n\n```py\n```\n\nb\n")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "a"), ("paragraph", "b")]
    assert [(w.code, w.reason)
            for w in doc.warnings] == [
        ("md_empty_code_block",
         "line 3 处的代码块为空")]


def test_ws_fence_not_empty_two_fences(tmp_path):
    doc, errors = _run(tmp_path, "```\n   \n```\n")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "   ",
         {"kind": "code_block", "language": ""})]
    assert doc.warnings == []

    doc2, errors2 = _run(
        tmp_path, "```\n```\n\n```\n```\n")
    assert doc2 is None
    ws = errors2[0].details["warnings"]
    assert [(w["code"], w["reason"]) for w in ws] == [
        ("md_empty_code_block", "line 1 处的代码块为空"),
        ("md_empty_code_block", "line 4 处的代码块为空"),
        ("md_no_content",
         "Markdown 文件未提取到任何 element"
         "（可能为空文件或仅含主题分隔符）")]
