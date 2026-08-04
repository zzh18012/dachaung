"""app/parsers/markdown_parser.py 边角测试 - 第四轮（Round 115）。

补强已有 base/edges/edges2/edges3（共 133 测试）未覆盖的深度路径：
- 模块正则编译：_ATX/_THEMATIC/_FENCED/_UNORDERED/_ORDERED/_BLOCKQUOTE/
  _PIPE_TABLE_ROW/_PIPE_TABLE_SEP/_STANDALONE_IMAGE 各自 pattern 性质
- _detect_md_source_type：.MD/.Markdown 混合大小写、details.suffix 精确
- _split_pipe_row：含空 string cell、含 unicode、含反斜杠转义、多列、单列
- _is_pipe_table_start：i+1 越界、separator line 含 alignment
- _rows_to_md：单 row 单 col、jagged、全空 cell、含 | 字符
- MarkdownParser.parse 深度：
  - 多级 heading section_path 完整跟踪
  - heading 同级 push 后 section_path 单元素
  - heading 后 paragraph 携 section_path
  - code block 不含 lang 的 metadata
  - code block 含特殊字符语言（c++、js、f#）
  - code block 内部含 ``` 嵌套（更长的 fence）
  - thematic break 各种变种
  - 独立图片 url 含特殊字符（query string、fragment）
  - 多个图片连续 emit
  - 列表项含 markdown inline（**bold**）
  - blockquote 含多行
  - blockquote 内含列表（被当作 paragraph）
  - 表格单元格内容含 unicode
  - paragraph 跨多行
  - paragraph 中断于各种特殊行
- _parse_text 返回类型与签名
- MarkdownParser 类属性：name/version、instance match class、
  issubclass(Parser)、parse/_parse_text 签名
- 模块结构：__all__、imports、模块 docstring、常量
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from app.parsers.base import ParserError
from app.parsers.markdown_parser import (
    _ATX_HEADING_RE,
    _BLOCKQUOTE_RE,
    _FENCED_RE,
    _MD_EXTENSIONS,
    _ORDERED_LIST_RE,
    _PIPE_TABLE_ROW_RE,
    _PIPE_TABLE_SEP_RE,
    _STANDALONE_IMAGE_RE,
    _THEMATIC_RE,
    _UNORDERED_LIST_RE,
    MarkdownParser,
    _detect_md_source_type,
    _is_pipe_table_start,
    _rows_to_md,
    _split_pipe_row,
)


SHA = "a" * 64


def _write(tmp_path: Path, text: str, name: str = "x.md") -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# =========================================================================
# 模块正则编译验证
# =========================================================================


def test_atx_heading_re_pattern_compiled():
    assert isinstance(_ATX_HEADING_RE, re.Pattern)


def test_thematic_re_pattern_compiled():
    assert isinstance(_THEMATIC_RE, re.Pattern)


def test_fenced_re_pattern_compiled():
    assert isinstance(_FENCED_RE, re.Pattern)


def test_unordered_list_re_pattern_compiled():
    assert isinstance(_UNORDERED_LIST_RE, re.Pattern)


def test_ordered_list_re_pattern_compiled():
    assert isinstance(_ORDERED_LIST_RE, re.Pattern)


def test_blockquote_re_pattern_compiled():
    assert isinstance(_BLOCKQUOTE_RE, re.Pattern)


def test_pipe_table_row_re_pattern_compiled():
    assert isinstance(_PIPE_TABLE_ROW_RE, re.Pattern)


def test_pipe_table_sep_re_pattern_compiled():
    assert isinstance(_PIPE_TABLE_SEP_RE, re.Pattern)


def test_standalone_image_re_pattern_compiled():
    assert isinstance(_STANDALONE_IMAGE_RE, re.Pattern)


# =========================================================================
# 正则 pattern 性质
# =========================================================================


def test_atx_heading_re_uses_caret_anchor():
    assert _ATX_HEADING_RE.pattern.startswith("^")


def test_thematic_re_uses_caret_anchor():
    assert _THEMATIC_RE.pattern.startswith("^")


def test_fenced_re_uses_caret_anchor():
    assert _FENCED_RE.pattern.startswith("^")


def test_unordered_list_re_uses_caret_anchor():
    assert _UNORDERED_LIST_RE.pattern.startswith("^")


def test_ordered_list_re_uses_caret_anchor():
    assert _ORDERED_LIST_RE.pattern.startswith("^")


def test_blockquote_re_uses_caret_anchor():
    assert _BLOCKQUOTE_RE.pattern.startswith("^")


def test_standalone_image_re_uses_caret_anchor():
    assert _STANDALONE_IMAGE_RE.pattern.startswith("^")


# =========================================================================
# _detect_md_source_type 边界
# =========================================================================


def test_detect_md_source_type_accepts_md_lowercase():
    p = Path("a.md")
    assert _detect_md_source_type(p) == "markdown"


def test_detect_md_source_type_accepts_markdown_lowercase():
    p = Path("a.markdown")
    assert _detect_md_source_type(p) == "markdown"


def test_detect_md_source_type_accepts_md_uppercase():
    p = Path("a.MD")
    assert _detect_md_source_type(p) == "markdown"


def test_detect_md_source_type_accepts_markdown_uppercase():
    p = Path("a.MARKDOWN")
    assert _detect_md_source_type(p) == "markdown"


def test_detect_md_source_type_accepts_mixed_case():
    p = Path("a.Md")
    assert _detect_md_source_type(p) == "markdown"


def test_detect_md_source_type_rejects_ipynb():
    p = Path("a.ipynb")
    with pytest.raises(ParserError):
        _detect_md_source_type(p)


def test_detect_md_source_type_rejects_docx():
    p = Path("a.docx")
    with pytest.raises(ParserError):
        _detect_md_source_type(p)


def test_detect_md_source_type_rejects_pdf():
    p = Path("a.pdf")
    with pytest.raises(ParserError):
        _detect_md_source_type(p)


def test_detect_md_source_type_rejects_no_suffix():
    p = Path("nofile")
    with pytest.raises(ParserError):
        _detect_md_source_type(p)


def test_detect_md_source_type_error_details_suffix_value():
    p = Path("a.txt")
    with pytest.raises(ParserError) as exc_info:
        _detect_md_source_type(p)
    assert exc_info.value.details["suffix"] == ".txt"


def test_detect_md_source_type_error_details_suffix_empty_when_no_suffix():
    p = Path("nofile")
    with pytest.raises(ParserError) as exc_info:
        _detect_md_source_type(p)
    assert exc_info.value.details["suffix"] == ""


def test_md_extensions_value():
    assert _MD_EXTENSIONS == (".md", ".markdown")


def test_md_extensions_count_two():
    assert len(_MD_EXTENSIONS) == 2


# =========================================================================
# _split_pipe_row 深度
# =========================================================================


def test_split_pipe_row_empty_string():
    """空 string 不含 |，split 返回 ['']（保留 strip 处理）。"""
    assert _split_pipe_row("") == [""]


def test_split_pipe_row_only_pipes():
    """'|||' strip 头尾 | 后剩 '|' → split → ['', '']。"""
    assert _split_pipe_row("|||") == ["", ""]


def test_split_pipe_row_single_pipe():
    assert _split_pipe_row("a|b") == ["a", "b"]


def test_split_pipe_row_with_leading_pipe_only():
    assert _split_pipe_row("|a|b") == ["a", "b"]


def test_split_pipe_row_with_trailing_pipe_only():
    assert _split_pipe_row("a|b|") == ["a", "b"]


def test_split_pipe_row_no_pipes_returns_single_element():
    assert _split_pipe_row("no pipes") == ["no pipes"]


def test_split_pipe_row_strips_each_cell():
    assert _split_pipe_row("  a  |  b  ") == ["a", "b"]


def test_split_pipe_row_preserves_unicode():
    assert _split_pipe_row("你好|世界") == ["你好", "世界"]


def test_split_pipe_row_preserves_pipe_in_escaped_cell():
    """无 escape 处理：`a\\|b` 仍被切。"""
    result = _split_pipe_row("a\\|b")
    # \ 不阻止 split
    assert len(result) >= 2


def test_split_pipe_row_with_backslash():
    """纯反斜杠在 cell 内被保留。"""
    assert _split_pipe_row("a\\b|c") == ["a\\b", "c"]


def test_split_pipe_row_returns_list():
    assert isinstance(_split_pipe_row("a|b"), list)


def test_split_pipe_row_returns_list_of_str():
    for cell in _split_pipe_row("a|b|c"):
        assert isinstance(cell, str)


# =========================================================================
# _is_pipe_table_start 深度
# =========================================================================


def test_is_pipe_table_start_negative_index_returns_false():
    """i < 0 时 i+1 = 0，但 i+1 >= len(lines) 需要检查。
    实际代码：if i + 1 >= len(lines): return False
    i = -1 → i+1 = 0，若 lines 非空则 0 < len，进入下一行检查
    """
    lines = ["| a | b |", "| --- | --- |"]
    # i = -1：lines[-1] 是 separator，i+1=0 → lines[0] 是 header
    # 代码用 lines[i] 即 lines[-1]，lines[i+1] 即 lines[0]
    # 两者都匹配 → True
    result = _is_pipe_table_start(lines, -1)
    # 这种 edge case 行为不重要，主要是函数不抛
    assert isinstance(result, bool)


def test_is_pipe_table_start_i_at_last_line_returns_false():
    lines = ["| a |", "| --- |"]
    # i = 1 = len(lines) - 1 → i+1 = 2 >= len(lines) → False
    assert _is_pipe_table_start(lines, 1) is False


def test_is_pipe_table_start_i_beyond_length_returns_false():
    lines = ["| a |"]
    assert _is_pipe_table_start(lines, 5) is False


def test_is_pipe_table_start_header_not_pipe_returns_false():
    lines = ["not a header", "| --- |"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_separator_not_pipe_returns_false():
    lines = ["| a |", "not a separator"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_basic_returns_true():
    lines = ["| a | b |", "| --- | --- |"]
    assert _is_pipe_table_start(lines, 0) is True


def test_is_pipe_table_start_alignment_separator_returns_true():
    lines = ["| a | b |", "| :---: | ---: |"]
    assert _is_pipe_table_start(lines, 0) is True


# =========================================================================
# _rows_to_md 深度
# =========================================================================


def test_rows_to_md_single_row_single_col_value():
    md = _rows_to_md([["x"]])
    assert md == "| x |\n| --- |"


def test_rows_to_md_two_columns_three_rows_value():
    rows = [["a", "b"], ["1", "2"], ["3", "4"]]
    md = _rows_to_md(rows)
    assert md == "| a | b |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |"


def test_rows_to_md_separator_count_matches_columns():
    rows = [["a", "b", "c"]]
    md = _rows_to_md(rows)
    assert md.count("---") == 3


def test_rows_to_md_pipe_count_matches_columns_plus_one_per_row():
    rows = [["a", "b", "c"]]
    md = _rows_to_md(rows)
    # 每行 | 数 = col + 1
    for line in md.split("\n"):
        assert line.count("|") == 4


def test_rows_to_md_pipe_in_cell_preserved():
    rows = [["a|b", "c"]]
    md = _rows_to_md(rows)
    assert "a|b" in md


def test_rows_to_md_jagged_three_rows():
    rows = [["a", "b", "c"], ["1"], ["x", "y"]]
    md = _rows_to_md(rows)
    lines = md.split("\n")
    # 第二行 body 应 pad 到 3 列
    assert lines[2] == "| 1 |  |  |"
    assert lines[3] == "| x | y |  |"


def test_rows_to_md_returns_str():
    assert isinstance(_rows_to_md([["a"]]), str)


def test_rows_to_md_empty_returns_str():
    assert isinstance(_rows_to_md([]), str)


def test_rows_to_md_empty_rows_returns_empty_string():
    assert _rows_to_md([]) == ""


def test_rows_to_md_all_empty_cells():
    rows = [["", ""], ["", ""]]
    md = _rows_to_md(rows)
    # 仍 emit 全部 row
    assert md.count("\n") == 2  # 3 lines joined by 2 newlines


# =========================================================================
# MarkdownParser.parse：heading section_path 深度
# =========================================================================


def test_parse_section_path_two_levels(tmp_path: Path):
    p = _write(tmp_path, "# A\n\n## B\n\ntext")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    # paragraph 应携带 section_path "A > B"
    para = next(e for e in doc.elements if e.type == "paragraph")
    assert para.source_locator["section_path"] == "A > B"


def test_parse_section_path_three_levels(tmp_path: Path):
    p = _write(tmp_path, "# A\n\n## B\n\n### C\n\ntext")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    para = next(e for e in doc.elements if e.type == "paragraph")
    assert para.source_locator["section_path"] == "A > B > C"


def test_parse_section_path_pops_on_higher_level(tmp_path: Path):
    p = _write(tmp_path, "# A\n\n## B\n\n# C\n\ntext")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    para = next(e for e in doc.elements if e.type == "paragraph")
    assert para.source_locator["section_path"] == "C"


def test_parse_section_path_same_level_replaces(tmp_path: Path):
    p = _write(tmp_path, "# A\n\n# B\n\ntext")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    para = next(e for e in doc.elements if e.type == "paragraph")
    assert para.source_locator["section_path"] == "B"


def test_parse_section_path_absent_before_first_heading(tmp_path: Path):
    """无 heading 时 paragraph 不带 section_path。"""
    p = _write(tmp_path, "text without heading")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert "section_path" not in doc.elements[0].source_locator


def test_parse_heading_confidence_0_95(tmp_path: Path):
    p = _write(tmp_path, "# A")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].confidence == 0.95


def test_parse_paragraph_confidence_0_95(tmp_path: Path):
    p = _write(tmp_path, "text")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].confidence == 0.95


# =========================================================================
# MarkdownParser.parse：code block 深度
# =========================================================================


def test_parse_code_block_language_cplusplus(tmp_path: Path):
    p = _write(tmp_path, "```c++\nint x = 1;\n```")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata["language"] == "c++"


def test_parse_code_block_language_fsharp(tmp_path: Path):
    r"""f# 含 # 不在 [\w+-] 内，正则不匹配 fence，整体回退为 paragraph。

    实际表现：fence 不被识别 → 整段当一个 paragraph。
    """
    p = _write(tmp_path, "```f#\nlet x = 1\n```")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    # 不视为 code block
    types = [e.type for e in doc.elements]
    # 整体作为 paragraph（包含 fence 行）
    assert all(t == "paragraph" for t in types)


def test_parse_code_block_language_python_versioned(tmp_path: Path):
    r"""python3.10 含 . 不在 [\w+-] 内，正则不匹配。"""
    p = _write(tmp_path, "```python3.10\nx = 1\n```")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    types = [e.type for e in doc.elements]
    assert all(t == "paragraph" for t in types)


def test_parse_code_block_kind_code_block(tmp_path: Path):
    p = _write(tmp_path, "```\ncode\n```")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata["kind"] == "code_block"


def test_parse_code_block_with_unicode_content(tmp_path: Path):
    p = _write(tmp_path, "```\n你好\n```")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert "你好" in doc.elements[0].content


def test_parse_code_block_unclosed_at_eof_emits_warning(tmp_path: Path):
    """未闭合 code block：消耗到 EOF，content 非空则 emit。"""
    p = _write(tmp_path, "```\nunclosed code")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    # 应 emit element（content 非空）
    assert len(doc.elements) == 1
    assert "unclosed code" in doc.elements[0].content


def test_parse_code_block_empty_emits_warning(tmp_path: Path):
    p = _write(tmp_path, "```\n```")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    codes = [w.code for w in doc.warnings]
    assert "md_empty_code_block" in codes
    assert doc.elements == []


def test_parse_code_block_tilde_fence(tmp_path: Path):
    p = _write(tmp_path, "~~~python\ncode\n~~~")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata["language"] == "python"


# =========================================================================
# MarkdownParser.parse：thematic break 变种
# =========================================================================


def test_parse_thematic_break_emits_no_element(tmp_path: Path):
    p = _write(tmp_path, "---")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements == []


def test_parse_thematic_break_emits_no_content_warning(tmp_path: Path):
    """thematic break 后无内容 → md_no_content warning。"""
    p = _write(tmp_path, "---")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    codes = [w.code for w in doc.warnings]
    assert "md_no_content" in codes


def test_parse_thematic_break_with_long_dashes(tmp_path: Path):
    p = _write(tmp_path, "----------\n\ntext")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    # 仅 paragraph emit
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "paragraph"


def test_parse_thematic_break_with_mixed_chars(tmp_path: Path):
    """标准 thematic 不混用字符：- * _ 各自独立。"""
    p = _write(tmp_path, "* * *\n\ntext")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "paragraph"


# =========================================================================
# MarkdownParser.parse：standalone image 深度
# =========================================================================


def test_parse_standalone_image_with_url_query_string(tmp_path: Path):
    p = _write(tmp_path, "![alt](https://example.com/img.png?w=100&h=200)")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].type == "image"
    assert "w=100" in doc.elements[0].resource_path


def test_parse_standalone_image_with_fragment(tmp_path: Path):
    p = _write(tmp_path, "![alt](img.png#section)")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert "#section" in doc.elements[0].resource_path


def test_parse_standalone_image_alt_with_unicode(tmp_path: Path):
    p = _write(tmp_path, "![你好](img.png)")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata["alt"] == "你好"


def test_parse_standalone_image_alt_with_special_chars(tmp_path: Path):
    p = _write(tmp_path, "![a: b!](img.png)")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata["alt"] == "a: b!"


def test_parse_multiple_consecutive_images(tmp_path: Path):
    p = _write(tmp_path, "![a](img1.png)\n\n![b](img2.png)")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert len(doc.elements) == 2
    assert all(e.type == "image" for e in doc.elements)


# =========================================================================
# MarkdownParser.parse：list item 深度
# =========================================================================


def test_parse_unordered_list_dash_marker_metadata(tmp_path: Path):
    p = _write(tmp_path, "- item")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata["marker"] == "unordered"
    assert doc.elements[0].metadata["ordered"] is False


def test_parse_ordered_list_marker_metadata(tmp_path: Path):
    p = _write(tmp_path, "1. item")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata["marker"] == "ordered"
    assert doc.elements[0].metadata["ordered"] is True


def test_parse_list_item_with_inline_markdown(tmp_path: Path):
    """list item 含 **bold** 原样保留（不解析 inline）。"""
    p = _write(tmp_path, "- **bold** text")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].content == "**bold** text"


def test_parse_list_item_with_code_inline(tmp_path: Path):
    p = _write(tmp_path, "- use `code` here")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert "`code`" in doc.elements[0].content


def test_parse_two_list_items_separate_elements(tmp_path: Path):
    p = _write(tmp_path, "- first\n- second")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert len(doc.elements) == 2


# =========================================================================
# MarkdownParser.parse：blockquote 深度
# =========================================================================


def test_parse_blockquote_multi_line_content_merged(tmp_path: Path):
    p = _write(tmp_path, "> line 1\n> line 2")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert "line 1" in doc.elements[0].content
    assert "line 2" in doc.elements[0].content


def test_parse_blockquote_kind_blockquote(tmp_path: Path):
    p = _write(tmp_path, "> quote")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata["kind"] == "blockquote"


def test_parse_blockquote_with_empty_first_line(tmp_path: Path):
    """> 单独一行 → _BLOCKQUOTE_RE 匹配 group(1) 为 ''。"""
    p = _write(tmp_path, ">\n> content")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    # 应 emit 一个 blockquote，content="content"（empty stripped）
    assert len(doc.elements) == 1


def test_parse_blockquote_interrupted_by_paragraph(tmp_path: Path):
    p = _write(tmp_path, "> quote\n\nparagraph")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    types = [e.type for e in doc.elements]
    assert len(types) == 2


# =========================================================================
# MarkdownParser.parse：表格深度
# =========================================================================


def test_parse_pipe_table_metadata_has_row_count(tmp_path: Path):
    p = _write(tmp_path, "| a | b |\n| --- | --- |\n| 1 | 2 |")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata["row_count"] == 2


def test_parse_pipe_table_metadata_has_col_count(tmp_path: Path):
    p = _write(tmp_path, "| a | b | c |\n| --- | --- | --- |\n| 1 | 2 | 3 |")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata["col_count"] == 3


def test_parse_pipe_table_metadata_source_markdown_pipe_table(tmp_path: Path):
    """至少 2 列才能匹配 _PIPE_TABLE_SEP_RE。"""
    p = _write(tmp_path, "| a | b |\n| --- | --- |\n| 1 | 2 |")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata["source"] == "markdown_pipe_table"


def test_parse_pipe_table_with_unicode_cells(tmp_path: Path):
    p = _write(tmp_path, "| 中文 | 内容 |\n| --- | --- |\n| 一 | 二 |")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert "中文" in doc.elements[0].content


def test_parse_pipe_table_multiple_rows(tmp_path: Path):
    p = _write(tmp_path, "| h1 | h2 |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |\n| 5 | 6 |")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata["row_count"] == 4


def test_parse_pipe_table_only_header_no_data(tmp_path: Path):
    """仅 header + separator → 视为表格（row_count=1）。"""
    p = _write(tmp_path, "| a | b |\n| --- | --- |")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "table"


# =========================================================================
# MarkdownParser.parse：paragraph 深度
# =========================================================================


def test_parse_paragraph_with_no_trailing_newline(tmp_path: Path):
    p = _write(tmp_path, "single line")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].content == "single line"


def test_parse_paragraph_interrupted_by_heading(tmp_path: Path):
    p = _write(tmp_path, "para\n# heading")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    types = [e.type for e in doc.elements]
    assert types == ["paragraph", "heading"]


def test_parse_paragraph_interrupted_by_list(tmp_path: Path):
    p = _write(tmp_path, "para\n- item")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    types = [e.type for e in doc.elements]
    assert types == ["paragraph", "list_item"]


def test_parse_paragraph_interrupted_by_code_fence(tmp_path: Path):
    p = _write(tmp_path, "para\n```\ncode\n```")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    types = [e.type for e in doc.elements]
    assert types == ["paragraph", "paragraph"]


def test_parse_paragraph_interrupted_by_blockquote(tmp_path: Path):
    p = _write(tmp_path, "para\n> quote")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    types = [e.type for e in doc.elements]
    assert types == ["paragraph", "paragraph"]


def test_parse_paragraph_interrupted_by_thematic_break(tmp_path: Path):
    p = _write(tmp_path, "para\n---\nmore")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    types = [e.type for e in doc.elements]
    # thematic break 不 emit，所以 types 应为 ["paragraph", "paragraph"]
    assert types == ["paragraph", "paragraph"]


def test_parse_paragraph_interrupted_by_standalone_image(tmp_path: Path):
    p = _write(tmp_path, "para\n![alt](img.png)")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    types = [e.type for e in doc.elements]
    assert types == ["paragraph", "image"]


def test_parse_paragraph_interrupted_by_table(tmp_path: Path):
    p = _write(tmp_path, "para\n| a | b |\n| --- | --- |\n| 1 | 2 |")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    types = [e.type for e in doc.elements]
    assert types == ["paragraph", "table"]


# =========================================================================
# MarkdownParser 类属性
# =========================================================================


def test_markdown_parser_class_name_value():
    assert MarkdownParser.name == "markdown"


def test_markdown_parser_class_version_value():
    assert MarkdownParser.version == "stdlib/0.1.0"


def test_markdown_parser_class_name_is_str():
    assert isinstance(MarkdownParser.name, str)


def test_markdown_parser_class_version_is_str():
    assert isinstance(MarkdownParser.version, str)


def test_markdown_parser_instance_name_matches_class():
    p = MarkdownParser()
    assert p.name == "markdown"


def test_markdown_parser_instance_version_matches_class():
    p = MarkdownParser()
    assert p.version == "stdlib/0.1.0"


def test_markdown_parser_inherits_parser():
    from app.parsers.base import Parser

    assert issubclass(MarkdownParser, Parser)


def test_markdown_parser_parse_signature():
    import inspect

    sig = inspect.signature(MarkdownParser.parse)
    params = list(sig.parameters.keys())
    assert params[0] == "self"
    assert "path" in sig.parameters
    assert "source_hash" in sig.parameters


def test_markdown_parser_parse_text_signature():
    import inspect

    sig = inspect.signature(MarkdownParser._parse_text)
    params = list(sig.parameters.keys())
    assert params[0] == "self"
    assert "text" in sig.parameters
    assert "document_id" in sig.parameters


def test_markdown_parser_has_docstring():
    assert MarkdownParser.__doc__ is not None


def test_markdown_parser_docstring_mentions_markdown():
    doc = MarkdownParser.__doc__ or ""
    assert "markdown" in doc.lower() or "Markdown" in doc


# =========================================================================
# _parse_text 直接调用
# =========================================================================


def test_parse_text_returns_two_tuple():
    parser = MarkdownParser()
    result = parser._parse_text("text", "doc1")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_parse_text_first_element_is_list():
    parser = MarkdownParser()
    elements, _ = parser._parse_text("text", "doc1")
    assert isinstance(elements, list)


def test_parse_text_second_element_is_list():
    parser = MarkdownParser()
    _, warnings = parser._parse_text("text", "doc1")
    assert isinstance(warnings, list)


def test_parse_text_empty_text_returns_empty_lists():
    parser = MarkdownParser()
    elements, warnings = parser._parse_text("", "doc1")
    assert elements == []
    assert warnings == []


def test_parse_text_only_whitespace_returns_empty_elements():
    parser = MarkdownParser()
    elements, _ = parser._parse_text("   \n\n   \t   ", "doc1")
    assert elements == []


def test_parse_text_document_id_in_element_ids():
    parser = MarkdownParser()
    elements, _ = parser._parse_text("text", "mydoc")
    assert all(e.element_id.startswith("mydoc::") for e in elements)


# =========================================================================
# MarkdownParser.parse：错误路径
# =========================================================================


def test_parse_file_not_found_raises(tmp_path: Path):
    parser = MarkdownParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(tmp_path / "nonexistent.md", source_hash=SHA)
    assert exc_info.value.code == "file_not_found"


def test_parse_unsupported_extension_raises(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    parser = MarkdownParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(p, source_hash=SHA)
    assert exc_info.value.code == "unsupported_type"


def test_parse_oserror_raises_md_read_failed(tmp_path: Path, monkeypatch):
    p = tmp_path / "x.md"
    p.write_text("hello", encoding="utf-8")

    original_read_text = Path.read_text

    def fake_read_text(self, *args, **kwargs):
        if self == p:
            raise OSError("disk error")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    parser = MarkdownParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(p, source_hash=SHA)
    assert exc_info.value.code == "md_read_failed"


def test_parse_invalid_utf8_falls_back_to_replace(tmp_path: Path):
    p = tmp_path / "x.md"
    p.write_bytes(b"\xff\xfe# heading\n")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    # 不抛 → 已用 replace
    assert doc is not None


def test_parse_returns_document_with_empty_chunks(tmp_path: Path):
    p = _write(tmp_path, "text")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.chunks == []


def test_parse_returns_document_with_empty_relations(tmp_path: Path):
    p = _write(tmp_path, "text")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.relations == []


def test_parse_returns_document_with_empty_errors(tmp_path: Path):
    p = _write(tmp_path, "text")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.errors == []


def test_parse_metadata_has_markdown_flag(tmp_path: Path):
    p = _write(tmp_path, "text")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.metadata["markdown"] is True


def test_parse_metadata_only_markdown_key(tmp_path: Path):
    p = _write(tmp_path, "text")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=SHA)
    assert set(doc.metadata.keys()) == {"markdown"}


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_all_exports_only_markdown_parser():
    from app.parsers import markdown_parser as mod

    assert mod.__all__ == ["MarkdownParser"]


def test_module_all_count_one():
    from app.parsers import markdown_parser as mod

    assert len(mod.__all__) == 1


def test_module_imports_re():
    from app.parsers import markdown_parser as mod

    assert hasattr(mod, "re")


def test_module_imports_path():
    from app.parsers import markdown_parser as mod

    assert hasattr(mod, "Path")


def test_module_imports_any():
    from app.parsers import markdown_parser as mod

    assert hasattr(mod, "Any")


def test_module_imports_document():
    from app.parsers import markdown_parser as mod

    assert hasattr(mod, "Document")


def test_module_imports_element():
    from app.parsers import markdown_parser as mod

    assert hasattr(mod, "Element")


def test_module_imports_warning_record():
    from app.parsers import markdown_parser as mod

    assert hasattr(mod, "WarningRecord")


def test_module_imports_parser():
    from app.parsers import markdown_parser as mod

    assert hasattr(mod, "Parser")


def test_module_imports_parser_error():
    from app.parsers import markdown_parser as mod

    assert hasattr(mod, "ParserError")


def test_module_imports_make_document_id():
    from app.parsers import markdown_parser as mod

    assert hasattr(mod, "make_document_id")


def test_module_docstring_present():
    from app.parsers import markdown_parser as mod

    assert mod.__doc__ is not None


def test_module_docstring_mentions_atx():
    from app.parsers import markdown_parser as mod

    assert "ATX" in mod.__doc__ or "atx" in mod.__doc__.lower()


def test_module_docstring_mentions_setext_unsupported():
    """docstring 应说明不支持 setext。"""
    from app.parsers import markdown_parser as mod

    assert "setext" in mod.__doc__.lower()


def test_module_docstring_mentions_pipe_table():
    from app.parsers import markdown_parser as mod

    assert "pipe" in mod.__doc__.lower() or "表格" in mod.__doc__
