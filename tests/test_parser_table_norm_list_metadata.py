r"""parser 表格规范化与列表元数据：对齐行归
一、紧凑单元格重排、ordered/marker
（Round 1792）。

新角度：R1791 锁切分块偏移——**':---'
与 '---:' 对齐行归一为 '---'（对齐信息
丢失、表仍识别）；'|a|b|' 紧凑单元格识
别后重排为 '| a | b |'；list_item 携带
{'ordered': bool, 'marker': ...}——md
'1.'→ordered、'- '/'*'→unordered、
html ol/ul 同谱**零覆盖：

- **':--- | ---:'**：重建 '--- | ---'
- **'|a|b|'**：重建 '| a | b |'
- **'1.'/'- '/'*'/'<ol>'**：
  ordered/marker 四型同谱
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_alignment_separator_normalized(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "| a | b |\n| :--- | ---: |\n| 1 | 2 |\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [(
        "table",
        "| a | b |\n| --- | --- |\n| 1 | 2 |",
        {"row_count": 2, "col_count": 2,
         "source": "markdown_pipe_table"})]


def test_tight_cells_respaced(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("|a|b|\n|---|---|\n|1|2|\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "| a | b |\n| --- | --- |\n| 1 | 2 |"]


def test_list_item_ordered_metadata(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("1. one\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert doc.elements[0].metadata == {
        "ordered": True, "marker": "ordered"}
    p = tmp_path / "e.md"
    p.write_text("* star\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert doc.elements[0].metadata == {
        "ordered": False, "marker": "unordered"}
    p = tmp_path / "f.html"
    p.write_text("<ol><li>x</li></ol>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert doc.elements[0].metadata == {
        "ordered": True, "marker": "ordered"}
