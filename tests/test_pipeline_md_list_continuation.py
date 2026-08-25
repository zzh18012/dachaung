r"""pipeline Markdown 列表延续与缩进（Round 1634）。

新角度：R1633 锁 html 文本节点——**任务列表标记
raw、缩进延续行独立成段、4 空格缩进无代码块
语义**零覆盖：

- **任务列表标记不解析**：'- [ ] todo' →
  list_item '[ ] todo'（复选框语法原样）
- **缩进延续行不属于列表项**：'  continued'
  → 独立 paragraph（与 R1608 嵌套列表一致，
  缩进即断开）
- **4 空格缩进剥除**：普通 paragraph，无
  indented-code-block 语义
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


def test_task_list_raw(tmp_path):
    doc = _run(
        tmp_path,
        "- [ ] todo\n- [x] done\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "[ ] todo",
         {"ordered": False,
          "marker": "unordered"}),
        ("list_item", "[x] done",
         {"ordered": False,
          "marker": "unordered"})]


def test_continuation_separate(tmp_path):
    doc = _run(
        tmp_path,
        "- item\n  continued text\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "item"),
        ("paragraph", "continued text")]


def test_indented_paragraph(tmp_path):
    doc = _run(
        tmp_path,
        "    four space para\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "four space para", {})]
