r"""pipeline md checkbox 原样、列表后围栏、
对齐冒号归一与 BOM（Round 1694）。

新角度：R1693 锁嵌套列表——**checkbox 语法
无感知、':---:' 对齐冒号重建时剥离、BOM
挡住 md 标题识别、html ol start 属性忽略**
零覆盖：

- **'- [ ] todo'**：'[ ] todo' 原样 list_item
  （无 checkbox 元数据）
- **列表后 0 缩进围栏**：list_item 与
  code_block 各自独立 element
- **'| :---: | ---: |'**：表格照常，重建的
  对齐行归一为 '| --- | --- |'
- **'\\ufeff# T'**：BOM 使标题降级 paragraph
  原样保留；text 侧 '\\ufeffhello' 段落保留
- **`<ol start="5">`**：start 属性忽略，仅
  ordered list_item
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, name, binary=False):
    p = tmp_path / name
    if binary:
        p.write_bytes(text)
    else:
        p.write_text(text, encoding="utf-8")
    parser = ("html" if name.endswith("html")
              else "text" if name.endswith("txt")
              else "markdown")
    return process_single(
        p, write_json=False, parser_name=parser)


def test_md_checkbox_raw(tmp_path):
    doc, errors = _run(
        tmp_path, "- [ ] todo\n- [x] done\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "[ ] todo",
         {"ordered": False, "marker": "unordered"}),
        ("list_item", "[x] done",
         {"ordered": False, "marker": "unordered"})]


def test_md_fence_after_list(tmp_path):
    doc, errors = _run(
        tmp_path, "- item\n```py\ncode\n```\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "item",
         {"ordered": False, "marker": "unordered"}),
        ("paragraph", "code",
         {"kind": "code_block", "language": "py"})]


def test_md_align_colons_normalized(tmp_path):
    doc, errors = _run(
        tmp_path,
        "| a | b |\n| :---: | ---: |\n| x | y |\n",
        "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table",
         "| a | b |\n| --- | --- |\n| x | y |",
         {"row_count": 2, "col_count": 2,
          "source": "markdown_pipe_table"})]


def test_bom_and_ol_start(tmp_path):
    doc, errors = _run(
        tmp_path, "﻿# T\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "﻿# T", {})]

    doc2, errors2 = _run(
        tmp_path, "﻿hello\n".encode("utf-8"),
        "d.txt", binary=True)
    assert errors2 == []
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("paragraph", "﻿hello")]

    doc3, errors3 = _run(
        tmp_path, '<ol start="5"><li>x</li></ol>',
        "d.html")
    assert errors3 == []
    assert [(e.type, e.content, e.metadata)
            for e in doc3.elements] == [
        ("list_item", "x",
         {"ordered": True, "marker": "ordered"})]
