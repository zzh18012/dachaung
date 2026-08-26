r"""pipeline text tab 保留、ol 散文本插序与
CRLF markdown（Round 1712）。

新角度：R1711 锁无值 src——**text 内 '\\t'
原样保留、`<li>` 间散文本成段落且顺序插在
两项之间、CRLF 结尾的表格/标题/列表全部
识别（内容归一 '\\n'）**零覆盖：

- **text 'a\\tb'**：tab 保留不转空格
- **`<li>a</li>loose<li>b</li>`**：list_
  item 'a' + paragraph 'loose' + list_item
  'b'（散文本插序，不打断列表）
- **CRLF 表格**：识别正常，重建用 '\\n'
- **CRLF 标题 + 段落**：正常
- **CRLF 列表**：两个 list_item 正常
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run_html(tmp_path, text):
    p = tmp_path / "d.html"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def _run_md_bytes(tmp_path, data):
    p = tmp_path / "d.md"
    p.write_bytes(data)
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_text_tab_preserved(tmp_path):
    p = tmp_path / "d.txt"
    p.write_bytes(b"a\tb\n")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "a\tb")]


def test_loose_text_in_ol_interleaved(tmp_path):
    doc, errors = _run_html(
        tmp_path, "<ol><li>a</li>loose<li>b</li></ol>")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "a",
         {"ordered": True, "marker": "ordered"}),
        ("paragraph", "loose", {}),
        ("list_item", "b",
         {"ordered": True, "marker": "ordered"})]


def test_crlf_md_table(tmp_path):
    doc, errors = _run_md_bytes(
        tmp_path,
        b"| a | b |\r\n| --- | --- |\r\n| x | y |\r\n")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| a | b |\n| --- | --- |\n| x | y |",
         {"row_count": 2, "col_count": 2,
          "source": "markdown_pipe_table"})]


def test_crlf_md_heading_para(tmp_path):
    doc, errors = _run_md_bytes(tmp_path, b"# T\r\npara\r\n")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "T", {"level": 1}),
        ("paragraph", "para", {})]


def test_crlf_md_list(tmp_path):
    doc, errors = _run_md_bytes(tmp_path, b"- a\r\n- b\r\n")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "a",
         {"ordered": False, "marker": "unordered"}),
        ("list_item", "b",
         {"ordered": False, "marker": "unordered"})]
