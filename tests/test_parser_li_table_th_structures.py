r"""parser html li 内嵌表格抽出为兄弟、
th 内标题剥壳、th 内图片静默空格
（Round 1821）。

新角度：R1820 锁 md 尖括号——**li 内
<table> 不留在列表项内：抽出为兄弟
table 元素（row_count 1）；<th><h2>H
</h2></th> 剥成纯文本 'H'（不发射
heading）；<th><img></th> 图片不抽出
（区别于 img-in-heading）——空单元
'|  | n |'，无 image 元素**零覆盖：

- **li 内表格**：li 'x' + 表格兄弟
- **th 内 h2**：单元纯文本 'H'
- **th 内 img**：空单元无图片
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def test_li_table_extracted(tmp_path):
    doc, errors = _run(
        tmp_path,
        '<ul><li>x<table><tr><th>a</th>'
        '<th>b</th></tr></table></li></ul>')
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "x"),
        ("table", "| a | b |\n| --- | --- |")]
    t = doc.elements[1]
    assert t.metadata == {
        "row_count": 1, "col_count": 2,
        "source": "html_table"}


def test_th_heading_stripped(tmp_path):
    doc, errors = _run(
        tmp_path,
        '<table><tr><th><h2>H</h2></th>'
        '<th>n</th></tr></table>')
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("table", "| H | n |\n| --- | --- |")]
    assert all(e.type != "heading"
               for e in doc.elements)


def test_th_img_empty_cell(tmp_path):
    doc, errors = _run(
        tmp_path,
        '<table><tr><th><img src="i.png">'
        '</th><th>n</th></tr></table>')
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "|  | n |\n| --- | --- |"]
    assert all(e.type != "image"
               for e in doc.elements)
