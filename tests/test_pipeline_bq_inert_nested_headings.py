r"""pipeline 引用内列表标题惰性与嵌套标题拆分
（Round 1727）。

新角度：R1726 锁 figure——**'> - item' 与
'> # T' 在引用内全惰性成原样段落、`<h3>`
嵌在 `<h2>` 内会拆开外层标题成三段**零
覆盖：

- **'> - item'**：paragraph '- item' kind
  'blockquote'（列表标记不解析）
- **'> # T'**：paragraph '# T'（标题标记
  不解析，同 fence/table 惰性）
- **`<h2>a<h3>b</h3>c</h2>`**：heading
  'a'（level 2）+ heading 'b'（level 3）+
  paragraph 'c'（嵌套标题拆分外层容器）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, name):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False,
        parser_name="html" if name.endswith("html") else "markdown")


def test_bq_list_inert(tmp_path):
    doc, errors = _run(tmp_path, "> - item\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "- item",
         {"kind": "blockquote"})]


def test_bq_heading_inert(tmp_path):
    doc, errors = _run(tmp_path, "> # T\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "# T", {"kind": "blockquote"})]


def test_nested_h3_splits_h2(tmp_path):
    doc, errors = _run(
        tmp_path, "<h2>a<h3>b</h3>c</h2>", "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "a", {"level": 2}),
        ("heading", "b", {"level": 3}),
        ("paragraph", "c", {})]
