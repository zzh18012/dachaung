r"""pipeline 反斜杠围栏失效、空 tr 占位与
CJK forced_char 切分（Round 1721）。

新角度：R1720 锁 br 收尾——**'```\\py' 反
斜杠使围栏整个失效、空 `<tr>` 成占位表头、
CJK 长文无空白边界 forced_char 强制切 800、
段间散 img 顺序保留**零覆盖：

- **'```\\py\\nx\\n```'**：不成围栏，退化
  段落 '```\\py\\nx'（含开头反引号原样）
- **`<tr></tr>` + 数据行**：空行成占位表
  头 '|  |\\n| --- |'，'x' 为数据行
- **CJK 1080 字符**：首块 800（metadata
  split_boundary_after 'forced_char'——无
  空白可用强制切），次块 280
- **p/img/p**：paragraph 'a' + image +
  paragraph 'b' 顺序保留
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


def test_fence_backslash_lang_degrades(tmp_path):
    doc, errors = _run(tmp_path, "```\\py\nx\n```\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "```\\py\nx", {})]


def test_empty_tr_placeholder_header(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr></tr><tr><td>x</td></tr></table>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "|  |\n| --- |\n| x |",
         {"row_count": 2, "col_count": 1,
          "source": "html_table"})]


def test_cjk_long_split_forced_char(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("这是一段测试文本。" * 120,
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert len(doc.elements) == 1
    assert len(doc.elements[0].content) == 1080
    assert [(len(c.text),
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (800, "forced_char"), (280, None)]


def test_loose_img_between_paragraphs(tmp_path):
    doc, errors = _run(
        tmp_path,
        '<p>a</p><img src="i.png" alt="A"><p>b</p>',
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.resource_path)
            for e in doc.elements] == [
        ("paragraph", "a", None),
        ("image", None, "i.png"),
        ("paragraph", "b", None)]
