r"""app/parsers/html_parser.py 边角测试 - 第十六轮（Round 1466）。

新角度（probe 实证）空白保留 + br 语义 + 属性兼容性
（edges1-15 未碰过；base 已覆盖 style/title/doctype 跳过）：
- **内部空白原样保留**：'a    b\\n\\t c' 不折叠（与浏览器
  渲染不同，SAX 文本直接进 buffer）
- **br 每个贡献一个空格**：'a<br><br>b' → 'a  b'（两个
  空格保留）；**只有 br 的 p 是空**→ 0 元素 + html_no_content
- **<ol start>/<li value> 被忽略**：metadata 只有
  ordered/marker，无起始编号信息
- **img data: URI 原样进 resource_path**
- **自闭合 '<p/>'** 当开标签处理（'after' 成段）
- **无引号属性**正常解析（<td width=100>）
- **注释含标签**整体隐藏；**大写实体 &AMP; 解码**（html5
  实体表大小写不敏感）
- heading 内 <a> 拼接成标题文本；**heading 内 <img> 拆出
  独立 image element**（heading 只剩文本）
- **嵌套 blockquote 合并为一个**（不同于 markdown 只剥
  一层：html 完全不保留层级）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser

TMP_NAME = "html_edge16_probe.html"


def _parse(tmp_path, html, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(html, encoding="utf-8",
                 newline="")
    return HtmlParser().parse(
        p, compute_file_hash(p))


# ---------- 空白保留 ----------

def test_internal_ws_preserved(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<p>a    b\n\t c</p>")
    assert doc.elements[
        0].content == "a    b\n\t c"


def test_double_br_double_space(
        tmp_path):
    doc = _parse(
        tmp_path, "<p>a<br><br>b</p>")
    assert doc.elements[
        0].content == "a  b"


def test_p_only_br_empty(tmp_path):
    doc = _parse(tmp_path, "<p><br></p>")
    assert doc.elements == []
    assert [w.code for w in doc.warnings] \
        == ["html_no_content"]


# ---------- ol 编号属性 ----------

def test_ol_start_ignored(tmp_path):
    doc = _parse(
        tmp_path,
        "<ol start='5'><li>five</li>"
        "<li>six</li></ol>")
    assert [(e.content, e.metadata)
            for e in doc.elements] == [
        ("five", {"ordered": True,
                  "marker": "ordered"}),
        ("six", {"ordered": True,
                 "marker": "ordered"}),
    ]


def test_li_value_ignored(tmp_path):
    doc = _parse(
        tmp_path,
        "<ol><li value='3'>three</li></ol>")
    e = doc.elements[0]
    assert e.metadata == \
        {"ordered": True,
         "marker": "ordered"}


# ---------- data: URI ----------

def test_img_data_uri(tmp_path):
    doc = _parse(
        tmp_path,
        "<img src='data:image/png;"
        "base64,AAAA'>")
    e = doc.elements[0]
    assert e.type == "image"
    assert e.content is None
    assert e.resource_path == \
        "data:image/png;base64,AAAA"
    assert e.metadata["alt"] == ""


# ---------- 标签形式兼容 ----------

def test_self_closing_p(tmp_path):
    doc = _parse(
        tmp_path, "<p/>after")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "after"),
    ]


def test_unquoted_attr(tmp_path):
    doc = _parse(
        tmp_path,
        "<td width=100>x</td>")
    assert doc.elements[
        0].content == "x"


def test_comment_with_tag_hidden(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<!-- <p>hidden</p> --><p>vis</p>")
    assert [e.content
            for e in doc.elements] == ["vis"]
    assert doc.warnings == []


def test_uppercase_entity(tmp_path):
    doc = _parse(
        tmp_path, "<p>&AMP; up</p>")
    assert doc.elements[
        0].content == "& up"


# ---------- heading 内嵌 ----------

def test_a_in_heading(tmp_path):
    doc = _parse(
        tmp_path,
        "<h1><a href='u'>Linked</a>"
        " tail</h1>")
    e = doc.elements[0]
    assert e.type == "heading"
    assert e.content == "Linked tail"


def test_img_in_heading_splits(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<h1>Text <img src='i.png'></h1>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "Text"),
        ("image", None),
    ]
    assert doc.elements[
        1].resource_path == "i.png"


# ---------- 嵌套 blockquote ----------

def test_nested_bq_single(tmp_path):
    doc = _parse(
        tmp_path,
        "<blockquote><blockquote>"
        "deep quote</blockquote>"
        "</blockquote>")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.content == "deep quote"
    assert e.metadata == \
        {"kind": "blockquote"}
