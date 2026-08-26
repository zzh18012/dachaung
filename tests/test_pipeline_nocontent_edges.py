r"""pipeline 裸引用行、表内散文本、空 tbody
全空文档（Round 1671）。

新角度：R1670 锁空列表项——**'&gt;' 独行、
table 直下文本、无行 tbody 三个空边界全走
no_content**零覆盖：

- **'&gt;' 独行**：空 blockquote 丢弃 →
  md_no_content
- **表内散文本**：'&lt;table&gt;loose&lt;/
  table&gt;' 文本不在 td 内 → 丢弃 →
  html_no_content
- **空 tbody**：无 tr → 表不产出 →
  html_no_content
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, payload, parser, suffix):
    p = tmp_path / ("d" + suffix)
    p.write_text(payload, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name=parser)


def test_bare_quote_marker_no_content(tmp_path):
    doc, errors = _run(tmp_path, ">\n",
                       "markdown", ".md")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    assert [w["code"] for w in
            errors[0].details["warnings"]] == [
        "md_no_content"]


def test_loose_text_in_table_dropped(tmp_path):
    doc, errors = _run(
        tmp_path, "<table>loose</table>",
        "html", ".html")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    assert [w["code"] for w in
            errors[0].details["warnings"]] == [
        "html_no_content"]


def test_empty_tbody_no_content(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tbody></tbody></table>",
        "html", ".html")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    assert [w["code"] for w in
            errors[0].details["warnings"]] == [
        "html_no_content"]
