r"""app/parsers/html_parser.py 边角测试 - 第十八轮（Round 1476）。

新角度（probe 实证）skip 栈阴影 + 表格自动闭合语义 +
bq 内 heading 的栈效应（edges1-17 未碰过；edges14 已锁
img-in-cell 丢弃与空 cell '| --- |'，避开）：
- **script 内 <div> 阴影**：div 不匹配 skip 栈顶 → 整段
  连文本丢弃，仅 script 后内容存活
- **嵌套 <style> 早弹**：'<style>a<style>b</style>c
  </style>' → 内层开第二层 skip、首个 </style> 只弹一层，
  'c' 泄漏成 loose text 与 'ok' 并段 'cok'
- **未闭合 <script> 吞掉一切**：EOF 前 skip 栈不弹 →
  html_no_content 零 element
- **</ol> 关 <ul>**：栈顶不匹配不弹但仍 flush → list_item
  照发（unordered marker）、后续段落正常
- **空 <tr>（零 cell）**：width=0 → '|  |\n|  |'（分隔行
  也是空列！），row_count 1 / col_count 0
- **缺 </tr> 丢整行**：'<tr><td>a</td><tr><td>b</td>
  </table>' → 第二个 <tr> 收尾上一行后，</table> 直接弹栈，
  开着的 b 行**静默丢失**（只余 header 行）
- **缺 </td> 自动闭合**：'<td>a<td>b</tr>' → 前格先入行、
  </tr> 收尾后格 → '| a | b |' col_count 2
- **bq 内 <h2> 更新 section 栈**：blockquote 段先发，heading
  'T' 照发（section_path 'T'），后续 body 段 section_path
  也是 'T'
- **表格后 loose text**：'</table>tail text' → paragraph
  'tail text' 紧跟 table
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser

TMP_NAME = "html_edge18_probe.html"


def _parse(tmp_path, html, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(html, encoding="utf-8",
                 newline="")
    return HtmlParser().parse(
        p, compute_file_hash(p))


# ---------- skip 栈阴影 ----------

def test_div_in_script_dropped(tmp_path):
    doc = _parse(
        tmp_path,
        "<script><div>x</div></script>"
        "<p>after</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "after"),
    ]
    assert doc.warnings == []


def test_nested_style_leaks_trailing(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<style>a<style>b</style>c"
        "</style><p>ok</p>")
    assert [e.content
            for e in doc.elements] == [
        "cok",
    ]


def test_unclosed_script_swallows_all(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<script>var x = 1;<p>gone</p>")
    assert doc.elements == []
    assert [w.code for w in doc.warnings] \
        == ["html_no_content"]


# ---------- 列表栈错配 ----------

def test_ul_closed_by_ol_flushes_li(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<ul><li>a</ol><p>after</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "a"),
        ("paragraph", "after"),
    ]
    assert doc.elements[0].metadata == {
        "ordered": False,
        "marker": "unordered",
    }


# ---------- 表格自动闭合 ----------

def test_empty_tr_zero_cols(tmp_path):
    doc = _parse(
        tmp_path,
        "<table><tr></tr></table>")
    e = doc.elements[0]
    assert e.type == "table"
    assert e.content == "|  |\n|  |"
    assert e.metadata["row_count"] == 1
    assert e.metadata["col_count"] == 0


def test_missing_end_tr_drops_open_row(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<table><tr><td>a</td>"
        "<tr><td>b</td></table>")
    e = doc.elements[0]
    assert e.content == \
        "| a |\n| --- |"
    assert e.metadata["row_count"] == 1
    assert doc.warnings == []


def test_missing_end_td_autocloses(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<table><tr><td>a<td>b</tr>"
        "</table>")
    e = doc.elements[0]
    assert e.content == \
        "| a | b |\n| --- | --- |"
    assert e.metadata["col_count"] == 2


# ---------- bq 内 heading ----------

def test_heading_in_bq_sets_section(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<blockquote>quote<h2>T</h2>"
        "</blockquote><p>body</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "quote"),
        ("heading", "T"),
        ("paragraph", "body"),
    ]
    assert doc.elements[0].metadata == {
        "kind": "blockquote"}
    assert doc.elements[1].metadata == {
        "level": 2}
    assert doc.elements[2].source_locator[
        "section_path"] == "T"


# ---------- 表格后 loose text ----------

def test_loose_text_after_table(tmp_path):
    doc = _parse(
        tmp_path,
        "<table><tr><td>a</td></tr>"
        "</table>tail text")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("table", "| a |\n| --- |"),
        ("paragraph", "tail text"),
    ]
