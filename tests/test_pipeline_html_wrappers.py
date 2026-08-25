r"""pipeline HTML 块级包装透明性（Round 1626）。

新角度：R1625 锁宽容解码——**div/section 包装、
裸 div 文本、script/style 内容**零覆盖：

- **包装透明**：div/section 内的 p/h2/表格
  原样提取（包装本身不产生元素）
- **裸 div 文本** → paragraph
- **script/style 内容整体丢弃**（.a{} 与
  var x; 不产生任何元素）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    return doc


def test_block_wrappers_transparent(tmp_path):
    doc = _run(
        tmp_path,
        "<div><p>a</p><p>b</p></div>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "a"),
        ("paragraph", "b")]

    doc2 = _run(
        tmp_path,
        "<section><h2>S</h2>"
        "<p>t</p></section>")
    assert [(e.type, e.content, e.metadata)
            for e in doc2.elements] == [
        ("heading", "S", {"level": 2}),
        ("paragraph", "t", {})]

    doc3 = _run(
        tmp_path,
        "<div><table><tr><th>x</th>"
        "</tr></table></div>")
    assert [(e.type, e.content,
             e.metadata["source"])
            for e in doc3.elements] == [
        ("table", "| x |\n| --- |",
         "html_table")]


def test_bare_div_text(tmp_path):
    doc = _run(
        tmp_path,
        "<div>bare text</div>")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "bare text", {})]


def test_script_style_dropped(tmp_path):
    doc = _run(
        tmp_path,
        "<style>.a{color:red}</style>"
        "<script>var x = 1;</script>"
        "<p>ok</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "ok")]
