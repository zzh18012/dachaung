r"""pipeline li 内 h2 抽出、img 独占 p、标题
内 br 与双 tbody（Round 1702）。

新角度：R1701 锁 dl 拼接——**li 内 h2 被抽
成兄弟 heading（该 li 消失）、img 独占 p 时
p 消失只留 image、h2 内 br 变空格（对比 td
内 br 无空格）、双 tbody 合并一表**零覆盖：

- **`<li><h2>H</h2></li><li>t</li>`**：
  heading 'H' + list_item 't'（首 li 不留
  list_item）
- **`<p><img ...></p>`**：只出 image 元素
  （content None、alt 'A'），p 消失
- **`<h2>a<br>b</h2>`**：'a b' 空格连接
- **两个 `<tbody>`**：合并 row_count 2
- **text 单字符 'x'**：一段一 chunk
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, name):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False,
        parser_name="html" if name.endswith("html") else "text")


def test_h2_in_li_extracted_sibling(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<ul><li><h2>H</h2></li><li>t</li></ul>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "H", {"level": 2}),
        ("list_item", "t",
         {"ordered": False, "marker": "unordered"})]


def test_img_only_p(tmp_path):
    doc, errors = _run(
        tmp_path,
        '<p>before</p><p><img src="i.png" alt="A"></p>',
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "before", {}),
        ("image", None, {"alt": "A"})]


def test_br_in_heading_space(tmp_path):
    doc, errors = _run(
        tmp_path, "<h2>a<br>b</h2>", "d.html")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "a b")]


def test_two_tbodys_merge(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tbody><tr><td>a</td></tr></tbody>"
        "<tbody><tr><td>b</td></tr></tbody></table>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| a |\n| --- |\n| b |",
         {"row_count": 2, "col_count": 1,
          "source": "html_table"})]


def test_text_single_char(tmp_path):
    p = tmp_path / "d.txt"
    p.write_bytes(b"x")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "x")]
    assert len(doc.chunks) == 1
