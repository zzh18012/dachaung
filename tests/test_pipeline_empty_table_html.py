r"""pipeline html 空表与单行表：静默消失、
无警告与表头化重建（Round 1764）。

新角度：R1763 锁 output_path——**
'&lt;table&gt;&lt;/table&gt;' 不产元素：单独
时整文件 no_extracted_elements、混段
时静默消失且无警告；单行表重建为表头+
分隔行（'| x & y | z |\\n| --- | ---
|'，标签剥除+实体解码在 cell 内）**零
覆盖：

- **空表单独**：(None,
  no_extracted_elements 嵌 html_no_content)
- **p+空表**：仅 paragraph 'keep'、
  warnings []
- **单行表两例**：content 均为
  '| v | v |\\n| --- | --- |' 形
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def test_empty_table_alone(tmp_path):
    doc, errors = _run(tmp_path, "<table></table>")
    assert doc is None
    e = errors[0]
    assert e.code == "no_extracted_elements"
    assert e.details["warnings"][0]["code"] == (
        "html_no_content")


def test_empty_table_mixed_silent(tmp_path):
    doc, errors = _run(
        tmp_path, "<p>keep</p><table></table>")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "keep")]
    assert doc.warnings == []


def test_single_row_header_rebuild(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><td><b>x</b> &amp; y</td>"
        "<td>z</td></tr></table>")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| x & y | z |\n| --- | --- |",
         {"row_count": 1, "col_count": 2,
          "source": "html_table"})]

    doc, errors = _run(
        tmp_path,
        "<table><tbody><tr><td>a</td>"
        "<td>b</td></tr></tbody></table>")
    assert errors == []
    assert doc.elements[0].content == (
        "| a | b |\n| --- | --- |")
