r"""app/parsers/markdown_parser.py 边角测试 - 第十五轮（Round 1470）。

新角度（probe 实证）info 字符串约束 + 图片语法字面性
（edges1-14 未碰过；base 已锁 standalone image RE 与
'python'/'' 语言，RE 级拒绝未锁 e2e）：
- **info 带引号/空格即杀死围栏**：'```python title="x"' →
  围栏**不开**，整块成 paragraph 且**尾部 ``` 反开空栏**
  → md_empty_code_block 告警链
- **info 带点同样杀围栏**：'```python.py' → 同上
- **info 两端空白剥离**：'```  python  ' → language='python'；
  纯空白 info → language=''
- **语言大小写保留**：'Python' 原样进 metadata
- **图片语法在结构内全部字面**：blockquote/列表项内
  '![alt](i.png)' 不产 image element；**行内有其他文本**
  （前后缀/两图相连/夹文本）→ 单 paragraph 字面；
  **表格单元格内**同样字面保留
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.markdown_parser import \
    MarkdownParser

TMP_NAME = "md_edge15_probe.md"


def _parse(tmp_path, text, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8",
                 newline="")
    return MarkdownParser().parse(
        p, compute_file_hash(p))


# ---------- info 字符串约束 ----------

def test_info_extra_kills_fence(
        tmp_path):
    doc = _parse(
        tmp_path,
        '```python title="x"\n'
        "code\n```\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph",
         '```python title="x"\ncode'),
    ]
    assert [w.code for w in doc.warnings] \
        == ["md_empty_code_block"]


def test_info_dot_kills_fence(
        tmp_path):
    doc = _parse(
        tmp_path,
        "```python.py\ncode\n```\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph",
         "```python.py\ncode"),
    ]
    assert [w.code for w in doc.warnings] \
        == ["md_empty_code_block"]


def test_info_spaces_stripped(
        tmp_path):
    doc = _parse(
        tmp_path,
        "```  python  \ncode\n```\n")
    e = doc.elements[0]
    assert e.content == "code"
    assert e.metadata["language"] == \
        "python"


def test_info_only_spaces_empty(
        tmp_path):
    doc = _parse(
        tmp_path,
        "```   \ncode\n```\n")
    e = doc.elements[0]
    assert e.metadata["language"] == ""


def test_fence_lang_case_preserved(
        tmp_path):
    doc = _parse(
        tmp_path,
        "```Python\ncode\n```\n")
    assert doc.elements[
        0].metadata["language"] == \
        "Python"


# ---------- 图片语法字面性 ----------

def test_img_in_bq_literal(tmp_path):
    doc = _parse(
        tmp_path,
        "> ![alt](i.png)\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "![alt](i.png)"
    assert e.metadata["kind"] == \
        "blockquote"


def test_img_in_list_literal(
        tmp_path):
    doc = _parse(
        tmp_path,
        "- ![alt](i.png)\n")
    e = doc.elements[0]
    assert e.type == "list_item"
    assert e.content == "![alt](i.png)"
    assert e.resource_path is None


def test_img_with_text_literal(
        tmp_path):
    doc = _parse(
        tmp_path,
        "before ![alt](i.png) after\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == \
        "before ![alt](i.png) after"
    assert doc.warnings == []


def test_two_images_one_line_literal(
        tmp_path):
    doc = _parse(
        tmp_path,
        "![a](x.png)![b](y.png)\n")
    assert len(doc.elements) == 1
    assert doc.elements[0].type == \
        "paragraph"
    assert doc.elements[0].content == \
        "![a](x.png)![b](y.png)"


def test_img_in_table_cell_literal(
        tmp_path):
    doc = _parse(
        tmp_path,
        "| a | b |\n"
        "| --- | --- |\n"
        "| ![i](p.png) | t |\n")
    e = doc.elements[0]
    assert e.type == "table"
    assert "| ![i](p.png) | t |" \
        in e.content
    assert e.metadata["row_count"] == 2
