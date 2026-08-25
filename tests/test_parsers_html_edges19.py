r"""app/parsers/html_parser.py 边角测试 - 第十九轮（Round 1481）。

新角度（probe 实证）非元素语法构造 + img 边界 + 跨上下文
flush 丢 kind（edges1-18 未碰过；comment 已由 edges/edges3/
edges16 锁定、dup-src 后者覆盖与数字实体已由 edges3 锁定，
避开）：
- **CDATA 整段丢弃**：'<![CDATA[raw <b>stuff</b>]]>' 被
  html.parser 当 bogus comment，仅后续段落存活
- **处理指令丢弃**：'<?php echo 1; ?>' 同 bogus comment
- **DOCTYPE 丢弃**：'<!DOCTYPE html>' 不产 element
- **img src 纯空白**：strip 后空 → 不发 image、alt 一并
  丢弃（连 html_no_content 都不触发——只剩其他段落时）
- **alt 内实体反转义**：alt='&amp;&lt;x&gt;' → '&<x>'
- **bq 内 table 杀 kind**：table 触发 flush 清空 bq 上下文
  → table 照发，其后的 'tail' 段**丢 blockquote kind**
- **bq 内 ul 的 li 无 kind**：li 走 list_item 分支（本就
  无 kind 字段），bq 不传递
- **pre 内 table**：'code' 先成 preformatted 段、table 照
  发，pre 上下文同样被 flush 打断
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser

TMP_NAME = "html_edge19_probe.html"


def _parse(tmp_path, html, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(html, encoding="utf-8",
                 newline="")
    return HtmlParser().parse(
        p, compute_file_hash(p))


# ---------- 非元素语法构造 ----------

def test_cdata_dropped(tmp_path):
    doc = _parse(
        tmp_path,
        "<![CDATA[raw <b>stuff</b>]]>"
        "<p>after</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "after"),
    ]
    assert doc.warnings == []


def test_pi_dropped(tmp_path):
    doc = _parse(
        tmp_path,
        "<?php echo 1; ?><p>after pi</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "after pi"),
    ]


def test_doctype_dropped(tmp_path):
    doc = _parse(
        tmp_path,
        "<!DOCTYPE html>"
        "<p>after doctype</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "after doctype"),
    ]


# ---------- img 边界 ----------

def test_img_ws_src_no_image(tmp_path):
    doc = _parse(
        tmp_path,
        '<p>t</p><img src="   " alt="blank">')
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "t"),
    ]
    assert doc.warnings == []


def test_entity_in_alt_unescaped(tmp_path):
    doc = _parse(
        tmp_path,
        '<img src="a.png" '
        'alt="&amp;&lt;x&gt;">')
    e = doc.elements[0]
    assert e.type == "image"
    assert e.resource_path == "a.png"
    assert e.metadata == {"alt": "&<x>"}


# ---------- 跨上下文 flush 丢 kind ----------

def test_table_in_bq_kills_kind(tmp_path):
    doc = _parse(
        tmp_path,
        "<blockquote><table><tr><td>x"
        "</td></tr></table>tail"
        "</blockquote>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("table", "| x |\n| --- |"),
        ("paragraph", "tail"),
    ]
    assert "kind" not in \
        doc.elements[1].metadata


def test_ul_in_bq_li_no_kind(tmp_path):
    doc = _parse(
        tmp_path,
        "<blockquote><ul><li>li in bq"
        "</li></ul></blockquote>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "li in bq"),
    ]
    assert doc.elements[0].metadata == {
        "ordered": False,
        "marker": "unordered",
    }


def test_pre_with_table_flush_split(
        tmp_path):
    doc = _parse(
        tmp_path,
        "<pre>code<table><tr><td>t"
        "</td></tr></table></pre>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "code"),
        ("table", "| t |\n| --- |"),
    ]
    assert doc.elements[0].metadata == {
        "kind": "preformatted"}
