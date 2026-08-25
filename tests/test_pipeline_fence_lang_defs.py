r"""pipeline 围栏语言字符集与链接定义原样
（Round 1648）。

新角度：R1647 锁 text_no_content——**info
串非纯词字符（c++/python3）、链接定义行
独立成文**零覆盖：

- **'c++' 语言保留**：R1635 只锁带空格参数
  破坏围栏；'+' 非 \\w 但仍进 language
- **'python3' 数字后缀**照常保留
- **链接定义原样**：'[a]: http://x' 独立成
  文也是 raw 段落（不剥离、不 md_no_content）
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


def test_fence_language_cpp(tmp_path):
    doc = _run(tmp_path, "```c++\nint x;\n```\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "int x;",
         {"kind": "code_block", "language": "c++"})]


def test_fence_language_python3(tmp_path):
    doc = _run(
        tmp_path, "```python3\nprint(1)\n```\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "print(1)",
         {"kind": "code_block",
          "language": "python3"})]


def test_link_definition_raw(tmp_path):
    doc = _run(tmp_path, "[a]: http://x\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "[a]: http://x", {})]

    doc2 = _run(
        tmp_path, "[a]: http://x\n\nuse it\n")
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("paragraph", "[a]: http://x"),
        ("paragraph", "use it")]
