r"""parser 裸标签：tr 无表成拼接段、li 独立
成项、列表项空格剥离（Round 1812）。

新角度：R1811 锁 ipynb 变体——**裸
<tr>（无 <table> 包裹）不是表——单元格
拼接 'xy' 成段（与 dl 同型）；裸 <li>
无 <ul> 仍是 list_item（unordered）；
'- x  ' 尾空格与 '-   y' 多空格标记
后都剥净**零覆盖：

- **裸 tr**：paragraph 'xy'
- **裸 li**：list_item 'x'
- **空格**：'x'/'y' 干净
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, text, parser):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name=parser)


def test_bare_tr_paragraph_concat(tmp_path):
    doc, errors = _run(
        tmp_path, "d.html",
        "<tr><td>x</td><td>y</td></tr>", "html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "xy", {})]


def test_bare_li_still_list_item(tmp_path):
    doc, errors = _run(
        tmp_path, "d.html", "<li>x</li>", "html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "x",
         {"ordered": False, "marker": "unordered"})]


def test_list_item_spaces_stripped(tmp_path):
    doc, errors = _run(
        tmp_path, "d.md", "- x  \n\n-   y\n",
        "markdown")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "x"), ("list_item", "y")]
