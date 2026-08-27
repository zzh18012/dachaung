r"""html 表格子元素错位与未闭合致命面测试（Round 1502）。

probe 实证（edges1-21 未碰；edges18 的 missing-</tr> 只锁
丢行，本轮发现**整文档丢失**面）：

- **裸 '<td>' 文本流入后续段**：'<td>cell</td><p>b</p>'
  → 'cellb' 合并段（td 不成表、文本不丢但混段）
- **裸 '<tr>' 同样**：td 文本 'x' 与后续 'b' 合并 'xb'
- **⚠ table 内裸文本被丢弃**：'<table>loose<tr>...' 的
  'loose' 静默丢失（表内非 cell 文本不进任何元素）
- **全 th 单行表照常**：1x1 表 '| only |'
- **嵌套表折入外层 + 专用告警**：outer cell 空、inner 表
  成外层第二行 '|  |\n| --- |\n| inner |' +
  **html_nested_table** 告警
- **⚠ 表未闭合 + 尾随文本 → 整文档丢失**：
  '<table>...tail'（无 </table> EOF）→ html_no_content
  （表与尾文本全丢）
- **⚠ 表内 '<p>' 无 '</tr>' → 整文档丢失**：状态机被
  打断后不恢复 → html_no_content
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import \
    HtmlParser


def _html(tmp_path, body):
    p = tmp_path / "probe.html"
    p.write_text(
        f"<!DOCTYPE html><html>"
        f"<body>{body}</body></html>",
        encoding="utf-8", newline="")
    return HtmlParser().parse(
        p, compute_file_hash(p))


# ---------- 裸表格子元素 ----------

def test_stray_td_text_merges_next(
        tmp_path):
    doc = _html(
        tmp_path,
        "<p>a</p><td>cell</td>"
        "<p>b</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "a"),
        ("paragraph", "cellb"),
    ]
    assert doc.warnings == []


def test_stray_tr_text_merges_next(
        tmp_path):
    doc = _html(
        tmp_path,
        "<p>a</p><tr><td>x</td></tr>"
        "<p>b</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "a"),
        ("paragraph", "xb"),
    ]


def test_loose_text_in_table_dropped(
        tmp_path):
    doc = _html(
        tmp_path,
        "<table>loose"
        "<tr><td>cell</td></tr>"
        "</table>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("table", "| cell |\n| --- |"),
    ]
    assert doc.warnings == []


def test_all_th_single_row_table(
        tmp_path):
    doc = _html(
        tmp_path,
        "<table><tr><th>only</th>"
        "</tr></table>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("table", "| only |\n| --- |"),
    ]
    assert doc.elements[0].metadata == {
        "row_count": 1,
        "col_count": 1,
        "source": "html_table",
        # adoption 补丁：table_index 唯一 join key（2026-08-27）
        "table_index": 0,
    }


# ---------- 嵌套与未闭合 ----------

def test_nested_table_inner_parsed_independently(
        tmp_path):
    """BUG-html-1 修复后：内层独立成元素（无外层文本时不产段落）。"""
    doc = _html(
        tmp_path,
        "<table><tr><td><table>"
        "<tr><td>inner</td></tr>"
        "</table></td></tr></table>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("table",
         "| inner |\n| --- |"),
        ("table",
         "|  |\n| --- |"),
    ]
    assert [w.code for w in
            doc.warnings] == [
        "html_nested_table"]


def test_unclosed_table_eats_document(
        tmp_path):
    doc = _html(
        tmp_path,
        "<table><tr><td>x</td></tr>"
        "tail")
    assert doc.elements == []
    assert [w.code for w in
            doc.warnings] == \
        ["html_no_content"]


def test_p_inside_table_no_tr_close_eats(
        tmp_path):
    doc = _html(
        tmp_path,
        "<table><tr><td>x</td>"
        "<p>mid</p></table>")
    assert doc.elements == []
    assert [w.code for w in
            doc.warnings] == \
        ["html_no_content"]
