r"""pipeline marker 后纯空格 crash 家族、tab
分隔标题与空单元格表（Round 1709）。

新角度：R1708 锁 '##   ' crash——**'-   '
与 '1.   '（marker 后仅空格）同样触发
unexpected_parser_error、'#\\tT' tab 可作
标题分隔符、'>   ' 引用丢弃走 no_content**
零覆盖：

- **'>   '**：引用丢弃，doc None +
  md_no_content 嵌套警告
- **'-   '**：list_item 空 content →
  unexpected_parser_error
- **'1.   '**：同 crash 家族
- **'#\\tT'**：tab 等效空格分隔，heading
  'T'
- **'~~~   '**：info 空白剥除 language ''
- **'|  |  |' 空单元格表**：合法 row_count
  1 col 2 占位
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_bq_ws_only_dropped(tmp_path):
    doc, errors = _run(tmp_path, ">   \n")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    ws = errors[0].details["warnings"]
    assert [(w["code"], w["reason"]) for w in ws] == [
        ("md_no_content",
         "Markdown 文件未提取到任何 element"
         "（可能为空文件或仅含主题分隔符）")]


def test_list_marker_ws_crash(tmp_path):
    doc, errors = _run(tmp_path, "-   \n")
    assert doc is None
    assert [e.code for e in errors] == [
        "unexpected_parser_error"]
    assert "必须至少有 content 或 resource_path" \
        in errors[0].message


def test_ordered_marker_ws_crash(tmp_path):
    doc, errors = _run(tmp_path, "1.   \n")
    assert doc is None
    assert [e.code for e in errors] == [
        "unexpected_parser_error"]
    assert "必须至少有 content 或 resource_path" \
        in errors[0].message


def test_hash_tab_separator(tmp_path):
    doc, errors = _run(tmp_path, "#\tT\n")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "T", {"level": 1})]


def test_tilde_ws_info_and_empty_table(tmp_path):
    doc, errors = _run(tmp_path, "~~~   \nx\n~~~\n")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "x",
         {"kind": "code_block", "language": ""})]

    doc2, errors2 = _run(
        tmp_path, "|  |  |\n| --- | --- |\n")
    assert errors2 == []
    assert [(e.type, e.content, e.metadata)
            for e in doc2.elements] == [
        ("table", "|  |  |\n| --- | --- |",
         {"row_count": 1, "col_count": 2,
          "source": "markdown_pipe_table"})]
