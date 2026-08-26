r"""pipeline 引用后表格打断、img 独占 h2、
单引号属性与 form feed（Round 1730）。

新角度：R1729 锁双 img——**'> q' 后无空
行表格照常识别并打断引用、`<h2>` 仅含
img 时只剩 image（空标题静默丢弃）、单引
号属性等价、'\\x0c' 不作行分隔**零覆盖：

- **'> q\\n| a | b |...'**：blockquote 'q'
  + table（表格打断引用块）
- **`<h2><img></h2>`**：仅 image 元素，
  无 heading 无警告
- **`<img src='a.png'>`**：单引号属性正
  常解析 resource_path 'a.png'
- **text 'a\\x0cb'**：form feed 原样保留
  在段落内
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


def test_table_after_bq_interrupts(tmp_path):
    doc, errors = _run(
        tmp_path,
        "> q\n| a | b |\n| --- | --- |\n| x | y |\n",
        "d.md")
    assert errors == []
    assert [(e.type, e.metadata) for e in doc.elements] == [
        ("paragraph", {"kind": "blockquote"}),
        ("table", {"row_count": 2, "col_count": 2,
                   "source": "markdown_pipe_table"})]


def test_img_only_h2(tmp_path):
    doc, errors = _run(
        tmp_path, '<h2><img src="i.png" alt="A"></h2>',
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("image", None, {"alt": "A"})]
    assert doc.warnings == []


def test_single_quoted_attr(tmp_path):
    doc, errors = _run(
        tmp_path, "<img src='a.png' alt='A'>", "d.html")
    assert errors == []
    assert doc.elements[0].resource_path == "a.png"


def test_form_feed_preserved(tmp_path):
    p = tmp_path / "d.txt"
    p.write_bytes(b"a\x0cb\n")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "a\x0cb")]
