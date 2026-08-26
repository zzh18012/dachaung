r"""pipeline 引用内表格 raw 与纯换行文件
（Round 1679）。

新角度：R1678 锁 img/pre——**blockquote 内
表格语法原样、'\\n' 独占文件两家族 no_
content**零覆盖：

- **引用内表格**：'&gt; | a | b |' 剥 '&gt; '
  后不成 table，blockquote 段原样
- **纯换行 md**：md_no_content
- **纯换行 txt**：text_no_content
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_table_in_blockquote_raw(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "> | a | b |\n> | --- | --- |\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "| a | b |\n| --- | --- |",
         {"kind": "blockquote"})]


def test_newlines_only_md(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("\n\n\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    assert [w["code"] for w in
            errors[0].details["warnings"]] == [
        "md_no_content"]


def test_newlines_only_txt(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("\n\n\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    assert [w["code"] for w in
            errors[0].details["warnings"]] == [
        "text_no_content"]
