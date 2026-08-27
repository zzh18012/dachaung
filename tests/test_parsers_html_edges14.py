r"""app/parsers/html_parser.py 边角测试 - 第十四轮（Round 1456）。

新角度（probe 实证）跨标签交互（edges1-13 未碰过）：
- **未闭合 <tr> 整表消失**：`<table><tr><td>a<td>b</table>`
  → 0 元素 + html_no_content（开行缓冲在 </table> 时被
  丢弃）；补 </tr> 后正常出表
- 同种嵌套 <pre><pre>：文本**合并**为单个 preformatted
  'outerinnertail'
- <pre> 内 <blockquote>：pre 被**提前 flush** 成 'code'，
  'quote' 独立 blockquote，剩余 'more' 是**无 kind** 的
  普通 paragraph
- <blockquote> 内 <p> 被忽略（仍是一个 blockquote）
- 表格内 <img> **丢失**（单元格空 '| |'）；<br> 在单元格
  **不加空格**（'ab'）；单元格内联标签正常拼接 'bold rest'
- 空src="" 图片跳过；孤儿 <li> → unordered；<ul> 内嵌
  <ol> 的 li → ordered=True
- 游离 </p> 把 loose 段落**提前封口**；大写 <P>/<H2> 正常；
  &nbsp; → \xa0 保留在内容中间
- <script> 内含字面 '<script>' 字符串：skip 栈正确嵌套，
  后续内容存活
- 表格承袭 section_path；纯表头表 row_count=1；th/td 混排
  无区分
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser

TMP_NAME = "html_edge14_probe.html"


def _parse(tmp_path, html, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(html, encoding="utf-8",
                 newline="")
    return HtmlParser().parse(
        p, compute_file_hash(p))


# ---------- 未闭合 tr ----------

def test_unclosed_tr_table_vanishes(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<table><tr><td>a<td>b</table>")
    assert doc.elements == []
    assert [w.code for w in doc.warnings] \
        == ["html_no_content"]


def test_unclosed_tr_with_close_ok(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<table><tr><td>a<td>b</tr></table>")
    e = doc.elements[0]
    assert e.type == "table"
    assert e.content == \
        "| a | b |\n| --- | --- |"
    assert e.metadata["row_count"] == 1


def test_unclosed_td_only_vanishes(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<table><tr><td>a</table>")
    assert doc.elements == []
    assert [w.code for w in doc.warnings] \
        == ["html_no_content"]


# ---------- 嵌套块 ----------

def test_nested_pre_merged(tmp_path):
    doc = _parse(
        tmp_path,
        "<pre>outer<pre>inner</pre>tail</pre>")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.content == "outerinnertail"
    assert e.metadata == {
        "kind": "preformatted"}


def test_bq_in_pre_triple(tmp_path):
    doc = _parse(
        tmp_path,
        "<pre>code<blockquote>quote</blockquote>more</pre>")
    assert [(e.content, e.metadata)
            for e in doc.elements] == [
        ("code", {"kind": "preformatted"}),
        ("quote", {"kind": "blockquote"}),
        ("more", {}),
    ]


def test_p_in_blockquote_ignored(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<blockquote><p>para in bq</p></blockquote>")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.content == "para in bq"
    assert e.metadata == {
        "kind": "blockquote"}


# ---------- 表格内元素 ----------

def test_img_in_table_emitted(
        tmp_path):
    # BUG-html-2 修复后：cell 内 img 复用 body 图片路径
    # （提交 1 曾按丢弃现状锁定）
    doc = _parse(
        tmp_path,
        "<table><tr><td><img src='x.png'>"
        "</td></tr></table>")
    assert [(e.type, e.resource_path)
            for e in doc.elements] == [
        ("image", "x.png"),
        ("table", None),
    ]
    assert doc.elements[1].content == \
        "|  |\n| --- |"
    assert doc.elements[1].metadata["col_count"] == 1


def test_br_in_cell_no_space(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<table><tr><td>a<br>b</td></tr></table>")
    assert doc.elements[0].content == \
        "| ab |\n| --- |"


def test_cell_inline_concat(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<table><tr><td><b>bold</b> rest"
        "</td></tr></table>")
    assert doc.elements[0].content == \
        "| bold rest |\n| --- |"


# ---------- 图片 / 列表 ----------

def test_img_empty_src_skipped(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<img src=''><img src='ok.png'>")
    assert len(doc.elements) == 1
    assert doc.elements[
        0].resource_path == "ok.png"


def test_orphan_li_unordered(
        tmp_path):
    doc = _parse(
        tmp_path, "<li>orphan</li>")
    e = doc.elements[0]
    assert e.type == "list_item"
    assert e.metadata["ordered"] is False
    assert e.metadata["marker"] == \
        "unordered"


def test_nested_list_ordering(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<ul><li>a<ol><li>b</li></ol></li></ul>")
    assert [(e.content,
             e.metadata["ordered"])
            for e in doc.elements] == [
        ("a", False), ("b", True),
    ]


# ---------- 游离标签 / 大写 ----------

def test_stray_p_close_flushes(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<div>loose</p><p>next")
    assert [e.content
            for e in doc.elements] == [
        "loose", "next"]


def test_uppercase_tags(tmp_path):
    doc = _parse(
        tmp_path,
        "<P>UP</P><H2>Title</H2>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "UP"),
        ("heading", "Title"),
    ]
    assert doc.elements[
        1].metadata["level"] == 2


def test_nbsp_preserved(tmp_path):
    doc = _parse(
        tmp_path, "<p>a&nbsp;b</p>")
    assert doc.elements[0].content == \
        "a\xa0b"


# ---------- script 嵌套 ----------

def test_script_literal_nested(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<script>var a='<script>';</script>"
        "<p>after</p>")
    assert [e.content
            for e in doc.elements] == ["after"]
    assert doc.warnings == []


# ---------- 表格与 section ----------

def test_table_section_path(tmp_path):
    doc = _parse(
        tmp_path,
        "<h1>S</h1><table><tr><td>x"
        "</td></tr></table>")
    assert doc.elements[
        1].source_locator["section_path"] \
        == "S"


def test_header_only_table(tmp_path):
    doc = _parse(
        tmp_path,
        "<table><tr><th>h1</th><th>h2</th>"
        "</tr></table>")
    e = doc.elements[0]
    assert e.metadata["row_count"] == 1
    assert e.metadata["col_count"] == 2


def test_th_td_mix(tmp_path):
    doc = _parse(
        tmp_path,
        "<table><tr><th>H</th><td>D</td>"
        "</tr></table>")
    assert doc.elements[0].content == \
        "| H | D |\n| --- | --- |"
