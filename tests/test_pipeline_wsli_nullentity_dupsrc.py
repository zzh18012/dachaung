r"""pipeline ws li 丢弃、null 实体、重复
src 后者生效与 info tab（Round 1710）。

新角度：R1709 锁 marker crash——**ws-only
`<li>` 丢弃、'&#0;' 解码成替换字符、重复
src 属性后者生效、'```\\tpy' info 前 tab
剥除、hr 尾随空格不影响**零覆盖：

- **`<li>   </li>`**：丢弃仅剩 'x'
- **'a&#0;b'**：解码 'a\\ufffdb'（替换字
  符）
- **`<img src="a.png" src="b.png">`**：
  resource_path 'b.png'（后者生效）
- **'```\\tpy'**：language 'py'（tab 等效
  空白剥除）
- **'***   '**：尾随空格不影响 hr 识别，
  丢弃 → md_no_content
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, name):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False,
        parser_name="html" if name.endswith("html") else "markdown")


def test_ws_li_dropped(tmp_path):
    doc, errors = _run(
        tmp_path, "<ul><li>   </li><li>x</li></ul>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("list_item", "x")]


def test_null_entity_replacement(tmp_path):
    doc, errors = _run(tmp_path, "<p>a&#0;b</p>", "d.html")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "a�b")]


def test_duplicate_src_last_wins(tmp_path):
    doc, errors = _run(
        tmp_path,
        '<img src="a.png" src="b.png" alt="A">',
        "d.html")
    assert errors == []
    assert doc.elements[0].resource_path == "b.png"


def test_fence_info_tab_stripped(tmp_path):
    doc, errors = _run(tmp_path, "```\tpy\nx\n```\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "x",
         {"kind": "code_block", "language": "py"})]


def test_hr_trailing_spaces(tmp_path):
    doc, errors = _run(tmp_path, "***   \n", "d.md")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    ws = errors[0].details["warnings"]
    assert [w["code"] for w in ws] == ["md_no_content"]
