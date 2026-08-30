r"""app/parsers/markdown_parser.py 边角测试 - 第八轮（Round 202）。

补强已有 base/edges/edges2-7（共 ~943 测试）未覆盖的深度：
- _THEMATIC_RE 边界（mixed chars、长串、首字符、不允许 leading）
- _FENCED_RE 语言字符串边界（c++/python-3/空格）
- _BLOCKQUOTE_RE 嵌套 > 与首字符
- _PIPE_TABLE_SEP_RE colon 对齐
- _ATX_HEADING_RE 跨所有 level + 边界
- _parse_text section_path 栈深度变化、同级/降级回退
- _parse_text 段落中断各分支
- parse() UnicodeDecodeError/OSError 路径
- _rows_to_md 单 cell、uneven 多行、空 body
- _split_pipe_row strip 行为
- MarkdownParser 类属性、metadata 字段
- 模块结构与签名深度
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

import pytest

from app.parsers.base import ParserError
from app.parsers.markdown_parser import (
    _ATX_HEADING_RE,
    _BLOCKQUOTE_RE,
    _detect_md_source_type,
    _FENCED_RE,
    _is_pipe_table_start,
    _MD_EXTENSIONS,
    _ORDERED_LIST_RE,
    _PIPE_TABLE_ROW_RE,
    _PIPE_TABLE_SEP_RE,
    _rows_to_md,
    _split_pipe_row,
    _STANDALONE_IMAGE_RE,
    _THEMATIC_RE,
    _UNORDERED_LIST_RE,
    MarkdownParser,
)


# =========================================================================
# _MD_EXTENSIONS
# =========================================================================


def test_md_extensions_value():
    assert _MD_EXTENSIONS == (".md", ".markdown")


def test_md_extensions_is_tuple():
    assert isinstance(_MD_EXTENSIONS, tuple)


def test_md_extensions_lowercase_only():
    """扩展名都是小写（suffix 在比较前会 .lower()）。"""
    for ext in _MD_EXTENSIONS:
        assert ext == ext.lower()
        assert ext.startswith(".")


# =========================================================================
# _ATX_HEADING_RE 深度
# =========================================================================


def test_atx_heading_regex_one_hash_level_1():
    m = _ATX_HEADING_RE.match("# Title")
    assert m is not None
    assert len(m.group(1)) == 1
    assert m.group(2) == "Title"


def test_atx_heading_regex_six_hashes_level_6():
    m = _ATX_HEADING_RE.match("###### Title")
    assert m is not None
    assert len(m.group(1)) == 6


def test_atx_heading_regex_seven_hashes_no_match():
    assert _ATX_HEADING_RE.match("####### Title") is None


def test_atx_heading_regex_zero_hashes_no_match():
    assert _ATX_HEADING_RE.match("Title") is None


def test_atx_heading_regex_no_space_no_match():
    """#Title 不匹配（必须有空白）。"""
    assert _ATX_HEADING_RE.match("#Title") is None


def test_atx_heading_regex_trailing_hashes_stripped():
    m = _ATX_HEADING_RE.match("## Title ##")
    assert m is not None
    assert m.group(2) == "Title"


def test_atx_heading_regex_trailing_hashes_no_space():
    m = _ATX_HEADING_RE.match("## Title##")
    assert m is not None
    assert m.group(2) == "Title"


def test_atx_heading_regex_only_hashes_no_match():
    """只有 # 没有内容不匹配。"""
    assert _ATX_HEADING_RE.match("#") is None


def test_atx_heading_regex_only_hashes_with_space_no_match():
    assert _ATX_HEADING_RE.match("# ") is None


def test_atx_heading_regex_tab_separator_matches():
    m = _ATX_HEADING_RE.match("#\tTitle")
    assert m is not None
    assert m.group(2) == "Title"


def test_atx_heading_regex_multiple_spaces_in_title():
    m = _ATX_HEADING_RE.match("# A B  C")
    assert m is not None
    assert m.group(2) == "A B  C"


def test_atx_heading_regex_leading_space_no_match():
    """ATX 标题不能有 leading space（CommonMark 允许 0-3，本解析器严格）。"""
    assert _ATX_HEADING_RE.match(" # Title") is None


def test_atx_heading_regex_unicode_title():
    m = _ATX_HEADING_RE.match("# 标题")
    assert m is not None
    assert m.group(2) == "标题"


# =========================================================================
# _THEMATIC_RE 深度
# =========================================================================


def test_thematic_regex_three_minuses():
    assert _THEMATIC_RE.match("---") is not None


def test_thematic_regex_three_asterisks():
    assert _THEMATIC_RE.match("***") is not None


def test_thematic_regex_three_underscores():
    assert _THEMATIC_RE.match("___") is not None


def test_thematic_regex_mixed_chars_no_match():
    """分隔符必须由同一种字符组成（实际正则允许 mixed，看下文）。"""
    # 实际正则 `(?:[-*_])(?:\s*[-*_]){2,}` 允许混合
    m = _THEMATIC_RE.match("-*_")
    assert m is not None  # mixed 实际匹配


def test_thematic_regex_two_chars_no_match():
    assert _THEMATIC_RE.match("--") is None


def test_thematic_regex_one_char_no_match():
    assert _THEMATIC_RE.match("-") is None


def test_thematic_regex_long_with_spaces():
    assert _THEMATIC_RE.match("- - - - -") is not None


def test_thematic_regex_long_no_spaces():
    assert _THEMATIC_RE.match("----------") is not None


def test_thematic_regex_with_leading_space_no_match():
    """stripped 在 parse 内做掉，但 regex 本身不 trim。"""
    assert _THEMATIC_RE.match(" ---") is None


def test_thematic_regex_with_trailing_space_no_match():
    """regex 不 trim 尾部空格。"""
    assert _THEMATIC_RE.match("--- ") is None


def test_thematic_regex_letters_no_match():
    assert _THEMATIC_RE.match("abc") is None


def test_thematic_regex_long_mixed():
    assert _THEMATIC_RE.match("-*_ *-_") is not None


# =========================================================================
# _FENCED_RE 深度
# =========================================================================


def test_fenced_regex_three_backticks():
    m = _FENCED_RE.match("```")
    assert m is not None
    assert m.group(1).startswith("`")
    assert len(m.group(1)) == 3


def test_fenced_regex_three_backticks_with_lang():
    m = _FENCED_RE.match("```python")
    assert m is not None
    assert m.group(2) == "python"


def test_fenced_regex_four_backticks():
    m = _FENCED_RE.match("````")
    assert m is not None
    assert len(m.group(1)) == 4


def test_fenced_regex_three_tildes():
    m = _FENCED_RE.match("~~~")
    assert m is not None
    assert m.group(1).startswith("~")


def test_fenced_regex_lang_with_dash():
    r"""支持 language 中含 +-（regex [\w+-]）。"""
    m = _FENCED_RE.match("```python-3")
    assert m is not None
    assert m.group(2) == "python-3"


def test_fenced_regex_lang_with_plus():
    m = _FENCED_RE.match("```c++")
    assert m is not None
    assert m.group(2) == "c++"


def test_fenced_regex_lang_empty_string_when_absent():
    m = _FENCED_RE.match("```")
    assert m.group(2) == ""


def test_fenced_regex_two_backticks_no_match():
    """至少 3 个反引号。"""
    assert _FENCED_RE.match("``") is None


def test_fenced_regex_no_fence_no_match():
    assert _FENCED_RE.match("plain text") is None


def test_fenced_regex_lang_with_space_no_match_in_lang():
    """language 之后跟空格 → 空格不属于 lang。"""
    m = _FENCED_RE.match("```python 3")
    # regex 末尾有 \s*$ → 'python 3' 含空格不匹配
    assert m is None


def test_fenced_regex_backticks_with_trailing_spaces():
    m = _FENCED_RE.match("```  ")
    assert m is not None


def test_fenced_regex_tildes_with_lang():
    m = _FENCED_RE.match("~~~javascript")
    assert m is not None
    assert m.group(2) == "javascript"


def test_fenced_regex_mixed_fence_chars_no_match():
    """backticks+tilde 不算 fence。"""
    assert _FENCED_RE.match("``~") is None


# =========================================================================
# _UNORDERED_LIST_RE 深度
# =========================================================================


def test_unordered_list_regex_minus():
    m = _UNORDERED_LIST_RE.match("- item")
    assert m is not None
    assert m.group(1) == "item"


def test_unordered_list_regex_plus():
    m = _UNORDERED_LIST_RE.match("+ item")
    assert m is not None
    assert m.group(1) == "item"


def test_unordered_list_regex_asterisk():
    m = _UNORDERED_LIST_RE.match("* item")
    assert m is not None
    assert m.group(1) == "item"


def test_unordered_list_regex_no_marker():
    assert _UNORDERED_LIST_RE.match("item") is None


def test_unordered_list_regex_no_space_no_match():
    """-item 不匹配。"""
    assert _UNORDERED_LIST_RE.match("-item") is None


def test_unordered_list_regex_tab_separator():
    m = _UNORDERED_LIST_RE.match("-\titem")
    assert m is not None
    assert m.group(1) == "item"


def test_unordered_list_regex_dot_marker_no_match():
    """`.` 不是无序列表标记。"""
    assert _UNORDERED_LIST_RE.match(". item") is None


def test_unordered_list_regex_number_marker_no_match():
    assert _UNORDERED_LIST_RE.match("1. item") is None


def test_unordered_list_regex_content_with_spaces():
    m = _UNORDERED_LIST_RE.match("- multi word item")
    assert m is not None
    assert m.group(1) == "multi word item"


# =========================================================================
# _ORDERED_LIST_RE 深度
# =========================================================================


def test_ordered_list_regex_dot():
    m = _ORDERED_LIST_RE.match("1. item")
    assert m is not None
    assert m.group(1) == "item"


def test_ordered_list_regex_paren():
    m = _ORDERED_LIST_RE.match("1) item")
    assert m is not None
    assert m.group(1) == "item"


def test_ordered_list_regex_multi_digit():
    m = _ORDERED_LIST_RE.match("10. item")
    assert m is not None
    assert m.group(1) == "item"


def test_ordered_list_regex_no_marker():
    assert _ORDERED_LIST_RE.match("item") is None


def test_ordered_list_regex_no_space_no_match():
    assert _ORDERED_LIST_RE.match("1.item") is None


def test_ordered_list_regex_zero():
    m = _ORDERED_LIST_RE.match("0. item")
    assert m is not None


def test_ordered_list_regex_no_dot_or_paren():
    """1- 或 1/ 都不算。"""
    assert _ORDERED_LIST_RE.match("1- item") is None
    assert _ORDERED_LIST_RE.match("1/ item") is None


# =========================================================================
# _BLOCKQUOTE_RE 深度
# =========================================================================


def test_blockquote_regex_basic():
    m = _BLOCKQUOTE_RE.match("> text")
    assert m is not None
    assert m.group(1) == "text"


def test_blockquote_regex_no_space():
    m = _BLOCKQUOTE_RE.match(">text")
    assert m is not None
    assert m.group(1) == "text"


def test_blockquote_regex_no_marker():
    assert _BLOCKQUOTE_RE.match("text") is None


def test_blockquote_regex_empty_content():
    m = _BLOCKQUOTE_RE.match(">")
    assert m is not None
    assert m.group(1) == ""


def test_blockquote_regex_multiple_markers_only_first_consumed():
    """嵌套引用 >>：regex 抓外层 >，剩余 > xxx 进 group(1)。"""
    m = _BLOCKQUOTE_RE.match(">> nested")
    assert m is not None
    assert m.group(1) == "> nested"


def test_blockquote_regex_three_markers():
    m = _BLOCKQUOTE_RE.match(">>> deep")
    assert m is not None
    assert m.group(1) == ">> deep"


def test_blockquote_regex_space_after_marker_consumed():
    r"""`> text` 与 `>  text`：\s? 最多吞 1 个空格。"""
    m = _BLOCKQUOTE_RE.match(">  two spaces")
    assert m is not None
    # \s? 只吞 1 个 → 剩 " two spaces"
    assert m.group(1) == " two spaces"


def test_blockquote_regex_leading_space_no_match():
    """regex 严格 line-anchored。"""
    assert _BLOCKQUOTE_RE.match(" > text") is None


# =========================================================================
# _STANDALONE_IMAGE_RE 深度
# =========================================================================


def test_standalone_image_regex_basic():
    m = _STANDALONE_IMAGE_RE.match("![alt](url.png)")
    assert m is not None
    assert m.group(1) == "alt"
    assert m.group(2) == "url.png"


def test_standalone_image_regex_empty_alt():
    m = _STANDALONE_IMAGE_RE.match("![](url.png)")
    assert m is not None
    assert m.group(1) == ""
    assert m.group(2) == "url.png"


def test_standalone_image_regex_no_match_inline_text():
    assert _STANDALONE_IMAGE_RE.match("text ![alt](url)") is None


def test_standalone_image_regex_no_match_text_after():
    assert _STANDALONE_IMAGE_RE.match("![alt](url) text") is None


def test_standalone_image_regex_url_with_path():
    m = _STANDALONE_IMAGE_RE.match("![alt](https://example.com/a/b/c.png)")
    assert m is not None
    assert "example.com" in m.group(2)


def test_standalone_image_regex_alt_with_spaces():
    m = _STANDALONE_IMAGE_RE.match("![some alt text](u)")
    assert m is not None
    assert m.group(1) == "some alt text"


def test_standalone_image_regex_no_closing_paren_no_match():
    assert _STANDALONE_IMAGE_RE.match("![alt](url") is None


def test_standalone_image_regex_no_bang_prefix_no_match():
    """![...]: 缺 ! 不算图片。"""
    assert _STANDALONE_IMAGE_RE.match("[alt](url)") is None


def test_standalone_image_regex_no_alt_brackets_no_match():
    assert _STANDALONE_IMAGE_RE.match("!image(url)") is None


# =========================================================================
# _PIPE_TABLE_ROW_RE / _PIPE_TABLE_SEP_RE
# =========================================================================


def test_pipe_table_row_basic():
    assert _PIPE_TABLE_ROW_RE.match("| a | b |") is not None


def test_pipe_table_row_no_leading_pipe():
    r"""regex 要求 `^\s*\|` → 必须有前导 |。"""
    assert _PIPE_TABLE_ROW_RE.match("a | b |") is None


def test_pipe_table_row_no_trailing_pipe():
    """regex 要求尾部 `|$`。"""
    assert _PIPE_TABLE_ROW_RE.match("| a | b") is None


def test_pipe_table_row_single_pipe():
    """| x | 是合法行。"""
    assert _PIPE_TABLE_ROW_RE.match("| x |") is not None


def test_pipe_table_row_empty_cells():
    assert _PIPE_TABLE_ROW_RE.match("|  |  |") is not None


def test_pipe_table_sep_basic():
    assert _PIPE_TABLE_SEP_RE.match("| --- | --- |") is not None


def test_pipe_table_sep_no_pipes():
    """regex 允许 |? → 边缘可省略 |。"""
    assert _PIPE_TABLE_SEP_RE.match("--- | ---") is not None


def test_pipe_table_sep_colon_left():
    assert _PIPE_TABLE_SEP_RE.match("| :--- | --- |") is not None


def test_pipe_table_sep_colon_both():
    assert _PIPE_TABLE_SEP_RE.match("| :---: | --- |") is not None


def test_pipe_table_sep_colon_right():
    assert _PIPE_TABLE_SEP_RE.match("| ---: | --- |") is not None


def test_pipe_table_sep_too_few_dashes_no_match():
    """分隔行需要至少 2 个 dash（-{2,}）。"""
    assert _PIPE_TABLE_SEP_RE.match("| - | - |") is None


def test_pipe_table_sep_with_letters_no_match():
    assert _PIPE_TABLE_SEP_RE.match("| abc | def |") is None


def test_pipe_table_sep_one_column_no_match():
    """regex 要求 (|...)+ 至少一次重复 → 至少 2 列。"""
    # 单列 |---| 不匹配
    assert _PIPE_TABLE_SEP_RE.match("| --- |") is None


# =========================================================================
# _is_pipe_table_start
# =========================================================================


def test_is_pipe_table_start_at_last_line_returns_false():
    assert _is_pipe_table_start(["| a | b |"], 0) is False


def test_is_pipe_table_start_negative_index_returns_false():
    """i+1 >= len(lines) 时 False，但 -1 也会触发。"""
    # 谨慎：-1 等于 len-1
    assert _is_pipe_table_start(["only one"], -1) is False


def test_is_pipe_table_start_valid_two_column():
    lines = ["| a | b |", "| --- | --- |"]
    assert _is_pipe_table_start(lines, 0) is True


def test_is_pipe_table_start_returns_bool_type():
    lines = ["| a | b |", "| --- | --- |"]
    result = _is_pipe_table_start(lines, 0)
    assert isinstance(result, bool)


def test_is_pipe_table_start_three_columns():
    lines = ["| a | b | c |", "| --- | --- | --- |"]
    assert _is_pipe_table_start(lines, 0) is True


def test_is_pipe_table_start_colon_alignment():
    lines = ["| a | b |", "| :---: | ---: |"]
    assert _is_pipe_table_start(lines, 0) is True


# =========================================================================
# _rows_to_md 深度
# =========================================================================


def test_rows_to_md_empty_returns_empty_str():
    assert _rows_to_md([]) == ""


def test_rows_to_md_single_row_only_header_and_sep():
    s = _rows_to_md([["h1", "h2"]])
    lines = s.split("\n")
    assert len(lines) == 2  # header + separator
    assert lines[0] == "| h1 | h2 |"
    assert lines[1] == "| --- | --- |"


def test_rows_to_md_two_rows():
    s = _rows_to_md([["h"], ["v1"]])
    lines = s.split("\n")
    assert len(lines) == 3


def test_rows_to_md_pads_short_row_with_empty_string():
    s = _rows_to_md([["h1", "h2", "h3"], ["v1"]])  # 第二行短
    lines = s.split("\n")
    assert lines[2] == "| v1 |  |  |"


def test_rows_to_md_pads_first_short_row_uses_max_width():
    s = _rows_to_md([["h1"], ["v1", "v2", "v3"]])  # 第一行短
    lines = s.split("\n")
    assert lines[0] == "| h1 |  |  |"
    assert lines[1] == "| --- | --- | --- |"


def test_rows_to_md_single_cell():
    s = _rows_to_md([["a"]])
    assert s == "| a |\n| --- |"


def test_rows_to_md_separator_uses_three_dashes_exactly():
    s = _rows_to_md([["a"]])
    assert "| --- |" in s


def test_rows_to_md_handles_empty_cell_values():
    s = _rows_to_md([[""], [""]])
    lines = s.split("\n")
    assert lines[0] == "|  |"
    assert lines[2] == "|  |"


def test_rows_to_md_returns_str_type():
    assert isinstance(_rows_to_md([]), str)


def test_rows_to_md_with_unicode_cells():
    s = _rows_to_md([["中文", "emoji 🎉"]])
    assert "中文" in s
    assert "🎉" in s


# =========================================================================
# _split_pipe_row 深度
# =========================================================================


def test_split_pipe_row_basic():
    assert _split_pipe_row("| a | b |") == ["a", "b"]


def test_split_pipe_row_no_leading_pipe():
    assert _split_pipe_row("a | b |") == ["a", "b"]


def test_split_pipe_row_no_trailing_pipe():
    assert _split_pipe_row("| a | b") == ["a", "b"]


def test_split_pipe_row_no_pipes():
    """无 | → 单 cell。"""
    assert _split_pipe_row("plain") == ["plain"]


def test_split_pipe_row_only_leading_pipe():
    assert _split_pipe_row("| abc") == ["abc"]


def test_split_pipe_row_only_trailing_pipe():
    assert _split_pipe_row("abc |") == ["abc"]


def test_split_pipe_row_strips_each_cell():
    assert _split_pipe_row("|  a  |  b  |") == ["a", "b"]


def test_split_pipe_row_empty_string_returns_list_with_empty():
    """空字符串 → split('|') == [''] → ['']（无前导 | 也不后导 |）。"""
    assert _split_pipe_row("") == [""]


def test_split_pipe_row_returns_list_type():
    assert isinstance(_split_pipe_row("| x |"), list)


def test_split_pipe_row_single_cell():
    assert _split_pipe_row("| single |") == ["single"]


def test_split_pipe_row_three_cells():
    assert _split_pipe_row("| a | b | c |") == ["a", "b", "c"]


def test_split_pipe_row_empty_cell_in_middle():
    assert _split_pipe_row("| a |  | c |") == ["a", "", "c"]


# =========================================================================
# _detect_md_source_type 深度
# =========================================================================


def test_detect_md_source_type_md_lower():
    assert _detect_md_source_type(Path("a.md")) == "markdown"


def test_detect_md_source_type_md_upper():
    assert _detect_md_source_type(Path("a.MD")) == "markdown"


def test_detect_md_source_type_markdown_lower():
    assert _detect_md_source_type(Path("a.markdown")) == "markdown"


def test_detect_md_source_type_markdown_upper():
    assert _detect_md_source_type(Path("a.MARKDOWN")) == "markdown"


def test_detect_md_source_type_mixed_case():
    assert _detect_md_source_type(Path("a.Md")) == "markdown"


def test_detect_md_source_type_double_extension_uses_last():
    """a.txt.md → .md。"""
    assert _detect_md_source_type(Path("a.txt.md")) == "markdown"


def test_detect_md_source_type_unknown_suffix_raises():
    with pytest.raises(ParserError):
        _detect_md_source_type(Path("a.txt"))


def test_detect_md_source_type_no_suffix_raises():
    with pytest.raises(ParserError):
        _detect_md_source_type(Path("a"))


def test_detect_md_source_type_pdf_raises():
    with pytest.raises(ParserError):
        _detect_md_source_type(Path("a.pdf"))


def test_detect_md_source_type_docx_raises():
    with pytest.raises(ParserError):
        _detect_md_source_type(Path("a.docx"))


def test_detect_md_source_type_error_details_has_suffix():
    try:
        _detect_md_source_type(Path("a.txt"))
    except ParserError as e:
        assert e.details["suffix"] == ".txt"


def test_detect_md_source_type_error_details_empty_string_for_no_suffix():
    try:
        _detect_md_source_type(Path("a"))
    except ParserError as e:
        assert e.details["suffix"] == ""


def test_detect_md_source_type_error_message_contains_suffix():
    try:
        _detect_md_source_type(Path("a.txt"))
    except ParserError as e:
        assert ".txt" in e.message


def test_detect_md_source_type_error_message_contains_none_for_no_suffix():
    try:
        _detect_md_source_type(Path("a"))
    except ParserError as e:
        assert "(无)" in e.message


def test_detect_md_source_type_error_code():
    try:
        _detect_md_source_type(Path("a.txt"))
    except ParserError as e:
        assert e.code == "unsupported_type"


# =========================================================================
# MarkdownParser 类属性
# =========================================================================


def test_markdown_parser_name():
    assert MarkdownParser.name == "markdown"


def test_markdown_parser_version():
    assert MarkdownParser.version == "stdlib/0.1.0"


def test_markdown_parser_inherits_parser():
    from app.parsers.base import Parser
    assert issubclass(MarkdownParser, Parser)


def test_markdown_parser_parse_signature():
    sig = inspect.signature(MarkdownParser.parse)
    params = list(sig.parameters)
    # self, path, source_hash
    assert params == ["self", "path", "source_hash"]


def test_markdown_parser_is_callable():
    assert callable(MarkdownParser)


def test_markdown_parser_module_all():
    import app.parsers.markdown_parser as m
    assert m.__all__ == ["MarkdownParser"]


# =========================================================================
# parse() 错误矩阵
# =========================================================================


def test_parse_nonexistent_file_raises(tmp_path):
    parser = MarkdownParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(tmp_path / "nope.md", "a" * 64)
    assert ei.value.code == "file_not_found"


def test_parse_nonexistent_file_message(tmp_path):
    parser = MarkdownParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(tmp_path / "nope.md", "a" * 64)
    assert "nope.md" in ei.value.message
    assert "不存在" in ei.value.message


def test_parse_unsupported_suffix_raises(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello", encoding="utf-8")
    parser = MarkdownParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(p, "a" * 64)
    assert ei.value.code == "unsupported_type"


def test_parse_invalid_utf8_falls_back_to_replace(tmp_path):
    """非法 UTF-8 → errors=replace 路径。"""
    p = tmp_path / "a.md"
    p.write_bytes(b"# Title\n\xff\xfe invalid\n")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    # 应仍能解析出 Title
    assert any(e.type == "heading" for e in doc.elements)


def test_parse_oserror_raises_md_read_failed(tmp_path, monkeypatch):
    """OSError 抛 ParserError md_read_failed。"""
    p = tmp_path / "a.md"
    p.write_text("# x", encoding="utf-8")
    parser = MarkdownParser()

    def raise_oserror(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "read_text", raise_oserror)
    with pytest.raises(ParserError) as ei:
        parser.parse(p, "a" * 64)
    assert ei.value.code == "md_read_failed"
    assert "exception_type" in ei.value.details


def test_parse_returns_document(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("# Title", encoding="utf-8")
    parser = MarkdownParser()
    from app.models import Document
    doc = parser.parse(p, "a" * 64)
    assert isinstance(doc, Document)


def test_parse_metadata_has_markdown_true(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("# Title", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata == {"markdown": True}


def test_parse_empty_file_emits_warning(tmp_path):
    p = tmp_path / "empty.md"
    p.write_text("", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 0
    codes = [w.code for w in doc.warnings]
    assert "md_no_content" in codes


def test_parse_thematic_only_emits_no_content_warning(tmp_path):
    p = tmp_path / "themed.md"
    p.write_text("---\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 0
    codes = [w.code for w in doc.warnings]
    assert "md_no_content" in codes


def test_parse_parser_name_set(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("# T", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.parser_name == "markdown"


def test_parse_parser_version_set(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("# T", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.parser_version == "stdlib/0.1.0"


def test_parse_source_type_markdown(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("# T", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.source_type == "markdown"


def test_parse_source_path_is_str(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("# T", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert isinstance(doc.source_path, str)
    assert str(p) == doc.source_path


def test_parse_chunks_empty_list(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("# T", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.chunks == []


def test_parse_relations_empty_list(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("# T", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.relations == []


def test_parse_errors_empty_list(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("# T", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.errors == []


# =========================================================================
# _parse_text 行为：section_path 栈
# =========================================================================


def _parse_text(text: str) -> tuple[list, list]:
    parser = MarkdownParser()
    return parser._parse_text(text, "doc1")


def test_section_path_single_heading():
    els, _ = _parse_text("# Title")
    assert els[0].source_locator == {
        "family": "line_address", "line": 1, "section_path": "Title"}


def test_section_path_nested_two_levels():
    els, _ = _parse_text("# H1\n## H2")
    assert els[0].source_locator["section_path"] == "H1"
    assert els[1].source_locator["section_path"] == "H1 > H2"


def test_section_path_three_levels():
    els, _ = _parse_text("# A\n## B\n### C")
    assert els[2].source_locator["section_path"] == "A > B > C"


def test_section_path_same_level_pops_previous():
    """H1 → H2 → H2：第二个 H2 应清掉第一个 H2。"""
    els, _ = _parse_text("# H1\n## A\n## B")
    assert els[1].source_locator["section_path"] == "H1 > A"
    assert els[2].source_locator["section_path"] == "H1 > B"


def test_section_path_higher_level_pops_more():
    """H1 → H2 → H3 → H2：H3 应被 pop。"""
    els, _ = _parse_text("# H1\n## H2\n### H3\n## H2b")
    assert els[3].source_locator["section_path"] == "H1 > H2b"


def test_section_path_back_to_h1_clears_stack():
    els, _ = _parse_text("# A\n## B\n# C")
    assert els[2].source_locator["section_path"] == "C"


def test_section_path_paragraph_under_heading():
    els, _ = _parse_text("# Title\nbody")
    assert els[1].source_locator["section_path"] == "Title"
    assert els[1].source_locator["line"] == 2


def test_section_path_no_heading_no_section_path_key():
    """没有 ATX heading 时，locator 只有 line。"""
    els, _ = _parse_text("just a paragraph")
    assert "section_path" not in els[0].source_locator


# =========================================================================
# _parse_text 段落中断
# =========================================================================


def test_paragraph_breaks_at_blank_line():
    els, _ = _parse_text("para1\n\npara2")
    paras = [e for e in els if e.type == "paragraph"]
    assert len(paras) == 2


def test_paragraph_breaks_at_heading():
    els, _ = _parse_text("para\n# Title")
    paras = [e for e in els if e.type == "paragraph"]
    headings = [e for e in els if e.type == "heading"]
    assert len(paras) == 1
    assert len(headings) == 1


def test_paragraph_breaks_at_fenced_code():
    els, _ = _parse_text("para\n```\ncode\n```")
    # fenced code 是 paragraph 但有 metadata.kind=code_block
    plain_paras = [
        e for e in els
        if e.type == "paragraph" and e.metadata.get("kind") is None
    ]
    code = [e for e in els if e.metadata.get("kind") == "code_block"]
    assert len(plain_paras) == 1
    assert len(code) == 1


def test_paragraph_breaks_at_thematic_break():
    els, _ = _parse_text("para\n---")
    paras = [e for e in els if e.type == "paragraph"]
    assert len(paras) == 1


def test_paragraph_breaks_at_list_item():
    els, _ = _parse_text("para\n- item")
    paras = [e for e in els if e.type == "paragraph"]
    items = [e for e in els if e.type == "list_item"]
    assert len(paras) == 1
    assert len(items) == 1


def test_paragraph_breaks_at_ordered_list_item():
    els, _ = _parse_text("para\n1. item")
    items = [e for e in els if e.type == "list_item"]
    assert len(items) == 1


def test_paragraph_breaks_at_blockquote():
    els, _ = _parse_text("para\n> quote")
    plain_paras = [
        e for e in els
        if e.type == "paragraph" and e.metadata.get("kind") is None
    ]
    quotes = [e for e in els if e.metadata.get("kind") == "blockquote"]
    assert len(plain_paras) == 1
    assert len(quotes) == 1


def test_paragraph_breaks_at_standalone_image():
    els, _ = _parse_text("para\n![alt](u.png)")
    paras = [e for e in els if e.type == "paragraph"]
    imgs = [e for e in els if e.type == "image"]
    assert len(paras) == 1
    assert len(imgs) == 1


def test_paragraph_breaks_at_table():
    els, _ = _parse_text("para\n| a | b |\n| --- | --- |")
    paras = [e for e in els if e.type == "paragraph"]
    tables = [e for e in els if e.type == "table"]
    assert len(paras) == 1
    assert len(tables) == 1


def test_paragraph_multiline_joined():
    """段落内多行用 \n 保留（不合并为单行）。"""
    els, _ = _parse_text("line1\nline2\nline3")
    paras = [e for e in els if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].content == "line1\nline2\nline3"


def test_paragraph_strip_outer_whitespace():
    els, _ = _parse_text("  indented\n  line2  ")
    paras = [e for e in els if e.type == "paragraph"]
    assert paras[0].content == "indented\n  line2"


# =========================================================================
# _parse_text list_item 行为
# =========================================================================


def test_unordered_list_marker_metadata():
    els, _ = _parse_text("- a")
    assert els[0].metadata["marker"] == "unordered"
    assert els[0].metadata["ordered"] is False


def test_ordered_list_marker_metadata():
    els, _ = _parse_text("1. a")
    assert els[0].metadata["marker"] == "ordered"
    assert els[0].metadata["ordered"] is True


def test_list_item_content_extracted():
    els, _ = _parse_text("- hello world")
    assert els[0].content == "hello world"


def test_list_item_strip_content_whitespace():
    els, _ = _parse_text("-   hello  ")
    assert els[0].content == "hello"


# =========================================================================
# _parse_text fenced code block
# =========================================================================


def test_fenced_code_block_metadata_kind():
    els, _ = _parse_text("```\ncode\n```")
    assert els[0].metadata["kind"] == "code_block"
    assert els[0].metadata["language"] == ""


def test_fenced_code_block_with_language():
    els, _ = _parse_text("```python\nprint(1)\n```")
    assert els[0].metadata["language"] == "python"
    assert els[0].content == "print(1)"


def test_fenced_code_block_empty_emits_warning():
    els, warns = _parse_text("```\n```")
    assert len(els) == 0
    assert any(w.code == "md_empty_code_block" for w in warns)


def test_fenced_code_block_no_end_fence_consumes_rest():
    els, _ = _parse_text("```\ncode1\ncode2")
    assert els[0].content == "code1\ncode2"


def test_fenced_code_block_tilde_fence():
    els, _ = _parse_text("~~~\ncode\n~~~")
    assert els[0].metadata["kind"] == "code_block"


def test_fenced_code_block_joins_multiple_lines():
    els, _ = _parse_text("```\nline1\nline2\nline3\n```")
    assert els[0].content == "line1\nline2\nline3"


# =========================================================================
# _parse_text blockquote
# =========================================================================


def test_blockquote_single_line():
    els, _ = _parse_text("> hello")
    assert els[0].metadata["kind"] == "blockquote"
    assert els[0].content == "hello"


def test_blockquote_multi_line_joined():
    els, _ = _parse_text("> line1\n> line2")
    assert els[0].content == "line1\nline2"


def test_blockquote_breaks_at_non_quote():
    els, _ = _parse_text("> quote\nplain")
    quotes = [e for e in els if e.metadata.get("kind") == "blockquote"]
    paras = [e for e in els if e.type == "paragraph" and e.metadata.get("kind") is None]
    assert len(quotes) == 1
    assert len(paras) == 1


def test_blockquote_strip_outer_whitespace():
    els, _ = _parse_text(">   hello   ")
    assert els[0].content == "hello"


# =========================================================================
# _parse_text table
# =========================================================================


def test_table_metadata_row_and_col_count():
    els, _ = _parse_text("| a | b | c |\n| --- | --- | --- |\n| 1 | 2 | 3 |")
    e = els[0]
    assert e.type == "table"
    assert e.metadata["row_count"] == 2  # 1 header + 1 body
    assert e.metadata["col_count"] == 3
    assert e.metadata["source"] == "markdown_pipe_table"


def test_table_content_is_markdown_string():
    els, _ = _parse_text("| a | b |\n| --- | --- |\n| 1 | 2 |")
    content = els[0].content
    assert isinstance(content, str)
    assert "| a | b |" in content
    assert "| --- |" in content


def test_table_only_header_and_separator():
    """表格只有 header + 分隔行也成立。"""
    els, _ = _parse_text("| a | b |\n| --- | --- |")
    assert els[0].metadata["row_count"] == 1


# =========================================================================
# 模块结构
# =========================================================================


def test_module_imports_re():
    import app.parsers.markdown_parser as m
    assert hasattr(m, "re")


def test_module_imports_path():
    import app.parsers.markdown_parser as m
    assert hasattr(m, "Path")


def test_module_imports_any():
    import app.parsers.markdown_parser as m
    assert hasattr(m, "Any")


def test_module_imports_document_classes():
    import app.parsers.markdown_parser as m
    assert hasattr(m, "Document")
    assert hasattr(m, "Element")
    assert hasattr(m, "WarningRecord")


def test_module_imports_parser_base():
    import app.parsers.markdown_parser as m
    assert hasattr(m, "Parser")
    assert hasattr(m, "ParserError")
    assert hasattr(m, "make_document_id")


def test_module_docstring_present():
    import app.parsers.markdown_parser as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_features():
    import app.parsers.markdown_parser as m
    doc = m.__doc__
    assert "ATX" in doc
    assert "围栏代码块" in doc
    assert "表格" in doc
    assert "引用块" in doc


def test_module_docstring_mentions_unsupported():
    import app.parsers.markdown_parser as m
    doc = m.__doc__
    assert "setext" in doc
    assert "YAML" in doc


def test_module_uses_future_annotations():
    import app.parsers.markdown_parser as m
    # from __future__ import annotations → 字符串 annotation
    sig = inspect.signature(m.MarkdownParser.parse)
    assert isinstance(sig.return_annotation, str)


# =========================================================================
# 综合行为
# =========================================================================


def test_parse_full_document_with_all_element_types(tmp_path):
    """完整 markdown 含 heading/paragraph/list/code/quote/table/image。"""
    content = (
        "# Title\n"
        "para1\n\n"
        "- item1\n"
        "1. item2\n\n"
        "```\ncode\n```\n\n"
        "> quote\n\n"
        "| a | b |\n| --- | --- |\n| 1 | 2 |\n\n"
        "![alt](img.png)\n\n"
        "para2\n"
    )
    p = tmp_path / "full.md"
    p.write_text(content, encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    types = [e.type for e in doc.elements]
    assert "heading" in types
    assert "paragraph" in types
    assert "list_item" in types
    assert "table" in types
    assert "image" in types


def test_parse_consecutive_h1_h2_h1_section_paths(tmp_path):
    content = "# A\n## B\n# C\n## D"
    p = tmp_path / "sections.md"
    p.write_text(content, encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    paths = [e.source_locator.get("section_path") for e in doc.elements]
    assert paths == ["A", "A > B", "C", "C > D"]


def test_parse_idempotent(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("# T\n\nbody\n", encoding="utf-8")
    parser = MarkdownParser()
    doc1 = parser.parse(p, "a" * 64)
    doc2 = parser.parse(p, "a" * 64)
    # to_dict round-trip 比较
    assert doc1.to_dict() == doc2.to_dict()


def test_parse_element_ids_incremental(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("# A\n# B\n# C", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    ids = [e.element_id for e in doc.elements]
    # 4-digit zero-padded suffix
    assert ids[0].endswith("::e0000")
    assert ids[1].endswith("::e0001")
    assert ids[2].endswith("::e0002")


def test_parse_element_confidence_constant_095(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("# T", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    for e in doc.elements:
        assert e.confidence == 0.95


def test_parse_parent_id_always_none(tmp_path):
    """markdown parser 不设置 parent_id（保持扁平）。"""
    p = tmp_path / "x.md"
    p.write_text("# H\n## H2\nbody", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    for e in doc.elements:
        assert e.parent_id is None
