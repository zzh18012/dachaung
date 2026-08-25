r"""pipeline Markdown 结构边角：setext 不对称/
嵌套列表/超长代码块（Round 1608）。

新角度：R1607 锁 html 列表表格——**markdown 的
setext 下划线不对称、缩进子列表、超长围栏代码**
零覆盖（R1598 只锁了 type+content，未锁 metadata）：

- **setext 不对称**：`====` 不识别 → 下划线留在
  段落内容里；`------` 被当水平线丢弃 → 只留
  上方文本
- **缩进子列表不解析**：2 空格缩进的 `- inner`
  → paragraph，原始 '- ' 标记保留；顶层项仍是
  list_item
- **围栏代码块 metadata**：{'kind':
  'code_block', 'language': 'python'}（语言保留）；
  超长代码同样走
  long_paragraph_sentence_split 硬拆
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


def test_setext_asymmetry(tmp_path):
    doc = _run(
        tmp_path,
        "Title One\n==========\n\n"
        "Sub Two\n-------\n\npara\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph",
         "Title One\n=========="),
        ("paragraph", "Sub Two"),
        ("paragraph", "para")]


def test_nested_list_not_parsed(tmp_path):
    doc = _run(
        tmp_path,
        "- outer\n  - inner\n- flat\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "outer",
         {"ordered": False,
          "marker": "unordered"}),
        ("paragraph", "- inner", {}),
        ("list_item", "flat",
         {"ordered": False,
          "marker": "unordered"})]


def test_oversized_code_block(tmp_path):
    code = "\n".join(
        f"line {i:03d} of code"
        for i in range(60))
    doc = _run(
        tmp_path,
        f"```python\n{code}\n```\n")
    (el,) = doc.elements
    assert el.type == "paragraph"
    assert len(el.content) == 1019
    assert el.metadata == {
        "kind": "code_block",
        "language": "python"}
    c1, c2 = doc.chunks
    assert c1.metadata["strategy"] == (
        "long_paragraph_sentence_split")
    assert c2.metadata["strategy"] == (
        "long_paragraph_sentence_split")
    assert (len(c1.text), len(c2.text)) == (
        798, 220)
    assert c1.text.startswith("line 000 of code")
    assert c2.text.startswith("line 047")
