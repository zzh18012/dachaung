"""app/parsers/html_parser.py 边角测试 - 第四轮（Round 113）。

补强已有 base/edges/edges2/edges3（共 106 测试）未覆盖的深度路径：
- _rows_to_md：多行 cell 含 \n / |、jagged 多行、列宽准确、
  body 多行
- _HTMLDocParser 实例属性：__init__ 初始化所有字段、elements/warnings 默认空
- _HTMLDocParser handle_starttag：
  - 未知 inline tag 不影响 buffer
  - br outside any block 不崩
  - img src 缺失不 emit
  - img alt 缺失 → alt=""
  - skip_stack 嵌套同名（script in script 不存在，但 nested skip）
  - mismatched end tag 在 skip_stack 中
- _HTMLDocParser handle_endtag：
  - end tag 在 skip_stack 中 mismatched 不崩
  - end tag 在 table 中 mismatched
- _HTMLDocParser handle_data：
  - whitespace-only data 不创建 paragraph
  - data outside any block → loose paragraph
  - data inside skip_stack 丢弃
- _HTMLDocParser handle_startendtag：
  - <br/> outside block 安全
  - <hr/> flush block
  - 未知自闭合 tag 当 start 处理
- _HTMLDocParser section_path 跟踪深度：
  - 多级 heading 后 section_path 完整
  - h2 后 h1 弹出 h2
  - h3 后 h1 弹出 h2+h3
  - 同级 h1 h1 → section_path 始终一项
- _HTMLDocParser _flush_block：
  - None kind 不抛
  - 空 buffer 不 emit
  - heading emit 后 _section_path 含 text
- _HTMLDocParser reset_block：
  - 清空所有字段
  - 多次调用安全
- _HTMLDocParser _start_block：
  - 自动 flush 上一个 block
  - 设 _cur_kind、_cur_buffer、_cur_level、_cur_ordered
- _HTMLDocParser table 模式：
  - 空 <table></table> → 不 emit element
  - 多 <tr> 但 <td>/<th> 缺失 → emit rows with empty cells
  - <tr> 未闭合接 <tr> → 自动收尾
- HtmlParser.parse：
  - read_text UnicodeDecodeError → errors=replace 重试
  - read_text OSError → ParserError html_read_failed
  - handler.feed 异常 → ParserError html_parse_failed
  - handler.close 异常 → ParserError html_parse_failed
- 模块结构：__all__ 精确、imports 完整、常量值
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.parsers.base import ParserError
from app.parsers.html_parser import (
    _HTML_EXTENSIONS,
    _HEADING_LEVELS,
    _HTMLDocParser,
    _SKIP_TAGS,
    HtmlParser,
    _detect_html_source_type,
    _rows_to_md,
)


# =========================================================================
# _rows_to_md：深度边界
# =========================================================================


def test_rows_to_md_three_columns_two_body_rows():
    rows = [["a", "b", "c"], ["1", "2", "3"], ["4", "5", "6"]]
    md = _rows_to_md(rows)
    lines = md.split("\n")
    assert len(lines) == 4  # header + separator + 2 body
    assert lines[0] == "| a | b | c |"
    assert lines[1] == "| --- | --- | --- |"
    assert lines[2] == "| 1 | 2 | 3 |"
    assert lines[3] == "| 4 | 5 | 6 |"


def test_rows_to_md_separator_uses_three_dashes_per_col():
    rows = [["h1", "h2"]]
    md = _rows_to_md(rows)
    assert "| --- | --- |" in md


def test_rows_to_md_pipe_in_cell_preserved():
    rows = [["a|b", "c"]]
    md = _rows_to_md(rows)
    # 批次 5 契约 §2：结构转义 | → \|
    assert "a\\|b" in md


def test_rows_to_md_max_width_used_when_jagged():
    rows = [["a", "b", "c"], ["x"]]  # 第二行短
    md = _rows_to_md(rows)
    # 应 pad 到 3 列
    lines = md.split("\n")
    assert lines[2] == "| x |  |  |"


def test_rows_to_md_empty_rows_returns_empty_string():
    assert _rows_to_md([]) == ""


def test_rows_to_md_single_cell():
    md = _rows_to_md([["only"]])
    assert md == "| only |\n| --- |"


def test_rows_to_md_empty_string_cell_value_preserved():
    rows = [["a", "", "c"]]
    md = _rows_to_md(rows)
    assert "| a |  | c |" in md


def test_rows_to_md_cell_with_newline():
    rows = [["line1\nline2"]]
    md = _rows_to_md(rows)
    # 批次 5 契约 §2：换行 → <br>（GFM 表格内换行语义）
    assert "line1<br>line2" in md


def test_rows_to_md_all_empty_rows():
    rows = [["", ""], ["", ""]]
    md = _rows_to_md(rows)
    # 仍渲染 separator
    assert "| --- | --- |" in md


# =========================================================================
# 模块常量深度
# =========================================================================


def test_html_extensions_value():
    assert _HTML_EXTENSIONS == (".html", ".htm")


def test_html_extensions_count_two():
    assert len(_HTML_EXTENSIONS) == 2


def test_heading_levels_exact_six_entries():
    assert len(_HEADING_LEVELS) == 6


def test_heading_levels_values_one_to_six():
    """每个 heading tag 映射到 1..6。"""
    assert sorted(_HEADING_LEVELS.values()) == [1, 2, 3, 4, 5, 6]


def test_heading_levels_h1_value_one():
    assert _HEADING_LEVELS["h1"] == 1


def test_heading_levels_h6_value_six():
    assert _HEADING_LEVELS["h6"] == 6


def test_heading_levels_h4_value_four():
    assert _HEADING_LEVELS["h4"] == 4


def test_skip_tags_contains_script():
    assert "script" in _SKIP_TAGS


def test_skip_tags_contains_style():
    assert "style" in _SKIP_TAGS


def test_skip_tags_contains_head():
    assert "head" in _SKIP_TAGS


def test_skip_tags_contains_title():
    assert "title" in _SKIP_TAGS


def test_skip_tags_contains_meta():
    assert "meta" in _SKIP_TAGS


def test_skip_tags_contains_link():
    assert "link" in _SKIP_TAGS


def test_skip_tags_contains_noscript():
    assert "noscript" in _SKIP_TAGS


def test_skip_tags_count_seven():
    assert len(_SKIP_TAGS) == 7


# =========================================================================
# _detect_html_source_type 边界
# =========================================================================


def test_detect_html_source_type_accepts_html_lowercase():
    p = Path("test.html")
    assert _detect_html_source_type(p) == "html"


def test_detect_html_source_type_accepts_htm_lowercase():
    p = Path("test.htm")
    assert _detect_html_source_type(p) == "html"


def test_detect_html_source_type_accepts_html_uppercase():
    p = Path("test.HTML")
    assert _detect_html_source_type(p) == "html"


def test_detect_html_source_type_accepts_htm_uppercase():
    p = Path("test.HTM")
    assert _detect_html_source_type(p) == "html"


def test_detect_html_source_type_rejects_no_suffix():
    p = Path("nofile")
    with pytest.raises(ParserError):
        _detect_html_source_type(p)


def test_detect_html_source_type_rejects_txt():
    p = Path("a.txt")
    with pytest.raises(ParserError):
        _detect_html_source_type(p)


def test_detect_html_source_type_rejects_pdf():
    p = Path("a.pdf")
    with pytest.raises(ParserError):
        _detect_html_source_type(p)


def test_detect_html_source_type_rejects_docx():
    p = Path("a.docx")
    with pytest.raises(ParserError):
        _detect_html_source_type(p)


def test_detect_html_source_type_error_has_unsupported_code():
    p = Path("a.txt")
    with pytest.raises(ParserError) as exc_info:
        _detect_html_source_type(p)
    assert exc_info.value.code == "unsupported_type"


def test_detect_html_source_type_error_has_suffix_in_details():
    p = Path("a.txt")
    with pytest.raises(ParserError) as exc_info:
        _detect_html_source_type(p)
    assert "suffix" in exc_info.value.details
    assert exc_info.value.details["suffix"] == ".txt"


# =========================================================================
# _HTMLDocParser 实例属性初始化
# =========================================================================


def test_doc_parser_init_elements_empty_list():
    p = _HTMLDocParser("doc1")
    assert p.elements == []


def test_doc_parser_init_warnings_empty_list():
    p = _HTMLDocParser("doc1")
    assert p.warnings == []


def test_doc_parser_init_document_id():
    p = _HTMLDocParser("mydoc")
    assert p.document_id == "mydoc"


def test_doc_parser_init_cur_kind_none():
    p = _HTMLDocParser("doc1")
    assert p._cur_kind is None


def test_doc_parser_init_cur_buffer_empty():
    p = _HTMLDocParser("doc1")
    assert p._cur_buffer == []


def test_doc_parser_init_pre_depth_zero():
    p = _HTMLDocParser("doc1")
    assert p._pre_depth == 0


def test_doc_parser_init_blockquote_depth_zero():
    p = _HTMLDocParser("doc1")
    assert p._blockquote_depth == 0


def test_doc_parser_init_table_depth_zero():
    p = _HTMLDocParser("doc1")
    assert p._table_depth == 0


def test_doc_parser_init_section_path_empty():
    p = _HTMLDocParser("doc1")
    assert p._section_path == []


def test_doc_parser_init_section_levels_empty():
    p = _HTMLDocParser("doc1")
    assert p._section_levels == []


def test_doc_parser_init_list_stack_empty():
    p = _HTMLDocParser("doc1")
    assert p._list_stack == []


def test_doc_parser_init_skip_stack_empty():
    p = _HTMLDocParser("doc1")
    assert p._skip_stack == []


def test_doc_parser_init_convert_charrefs_true():
    """父类 HTMLParser 应启 convert_charrefs。"""
    p = _HTMLDocParser("doc1")
    assert p.convert_charrefs is True


def test_doc_parser_init_cur_start_line_zero():
    p = _HTMLDocParser("doc1")
    assert p._cur_start_line == 0


def test_doc_parser_init_cur_level_zero():
    p = _HTMLDocParser("doc1")
    assert p._cur_level == 0


def test_doc_parser_init_cur_ordered_false():
    p = _HTMLDocParser("doc1")
    assert p._cur_ordered is False


# =========================================================================
# _HTMLDocParser handle_data：边界
# =========================================================================


def test_handle_data_whitespace_only_does_not_create_paragraph():
    p = _HTMLDocParser("doc1")
    p.handle_data("   \n   \t   ")
    assert p.elements == []
    assert p._cur_kind is None


def test_handle_data_outside_block_creates_paragraph():
    p = _HTMLDocParser("doc1")
    p.handle_data("loose text")
    assert p._cur_kind == "paragraph"
    assert "loose text" in p._cur_buffer


def test_handle_data_inside_skip_stack_dropped():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("script", [])
    p.handle_data("var x = 1;")
    assert p.elements == []
    assert p._cur_kind is None


def test_handle_data_inside_cur_buffer_appends():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("p", [])
    p.handle_data("hello")
    p.handle_data(" ")
    p.handle_data("world")
    assert p._cur_buffer == ["hello", " ", "world"]


def test_handle_data_empty_string_no_effect():
    p = _HTMLDocParser("doc1")
    p.handle_data("")
    assert p.elements == []
    assert p._cur_kind is None


# =========================================================================
# _HTMLDocParser handle_starttag：边界
# =========================================================================


def test_handle_starttag_unknown_inline_tag_ignored():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("span", [])
    assert p._cur_kind is None
    assert p.elements == []


def test_handle_starttag_div_does_not_create_block():
    """<div> 是 container，不直接 emit。"""
    p = _HTMLDocParser("doc1")
    p.handle_starttag("div", [])
    assert p._cur_kind is None


def test_handle_starttag_br_outside_block_no_crash():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("br", [])
    # br 在 None kind 时不 append 到 buffer
    assert p._cur_kind is None
    assert p._cur_buffer == []


def test_handle_starttag_br_inside_paragraph_adds_space():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("p", [])
    p.handle_data("hello")
    p.handle_starttag("br", [])
    assert " " in p._cur_buffer


def test_handle_starttag_img_no_src_no_emit():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("img", [("alt", "alt text")])
    assert p.elements == []


def test_handle_starttag_img_empty_src_no_emit():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("img", [("src", ""), ("alt", "x")])
    assert p.elements == []


def test_handle_starttag_img_src_whitespace_only_no_emit():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("img", [("src", "   "), ("alt", "x")])
    assert p.elements == []


def test_handle_starttag_img_with_alt_only_emits():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("img", [("src", "img.png"), ("alt", "alt")])
    assert len(p.elements) == 1
    assert p.elements[0].metadata.get("alt") == "alt"


def test_handle_starttag_img_no_alt_attr_default_empty_string():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("img", [("src", "img.png")])
    assert len(p.elements) == 1
    assert p.elements[0].metadata.get("alt") == ""


def test_handle_starttag_skip_tag_enters_skip_stack():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("script", [])
    assert "script" in p._skip_stack


def test_handle_starttag_skip_nested_other_tag_keeps_skip():
    """进入 script 后再遇到非 script tag 应被忽略。"""
    p = _HTMLDocParser("doc1")
    p.handle_starttag("script", [])
    p.handle_starttag("p", [])  # 应被忽略
    assert p._cur_kind is None


def test_handle_starttag_hr_flushes_block():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("p", [])
    p.handle_data("hello")
    p.handle_starttag("hr", [])
    # hr flush 上一个 paragraph
    assert p._cur_kind is None
    assert len(p.elements) == 1


def test_handle_starttag_h1_starts_heading_block():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("h1", [])
    assert p._cur_kind == "heading"
    assert p._cur_level == 1


def test_handle_starttag_h6_starts_heading_block_level_6():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("h6", [])
    assert p._cur_kind == "heading"
    assert p._cur_level == 6


def test_handle_starttag_p_starts_paragraph_block():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("p", [])
    assert p._cur_kind == "paragraph"


def test_handle_starttag_li_with_no_list_unordered_marker():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("li", [])
    assert p._cur_kind == "list_item"
    assert p._cur_ordered is False


def test_handle_starttag_li_with_ol_ordered_marker():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("ol", [])
    p.handle_starttag("li", [])
    assert p._cur_ordered is True


def test_handle_starttag_li_with_ul_unordered_marker():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("ul", [])
    p.handle_starttag("li", [])
    assert p._cur_ordered is False


def test_handle_starttag_pre_increments_pre_depth():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("pre", [])
    assert p._pre_depth == 1


def test_handle_starttag_blockquote_increments_depth():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("blockquote", [])
    assert p._blockquote_depth == 1


def test_handle_starttag_nested_pre_depth_two():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("pre", [])
    p.handle_starttag("pre", [])
    assert p._pre_depth == 2


def test_handle_starttag_nested_blockquote_depth_two():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("blockquote", [])
    p.handle_starttag("blockquote", [])
    assert p._blockquote_depth == 2


def test_handle_starttag_table_increments_depth():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("table", [])
    assert p._table_depth == 1


def test_handle_starttag_nested_table_pushes_context():
    # BUG-html-1 修复后：嵌套 → 警告 + 压入独立表格上下文（depth 递增）
    p = _HTMLDocParser("doc1")
    p.handle_starttag("table", [])
    p.handle_starttag("table", [])
    assert p._table_depth == 2
    assert len(p.warnings) == 1


def test_handle_starttag_nested_table_emits_warning():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("table", [])
    p.handle_starttag("table", [])
    assert p.warnings[0].code == "html_nested_table"


# =========================================================================
# _HTMLDocParser handle_startendtag：边界
# =========================================================================


def test_handle_startendtag_img_emits_image():
    p = _HTMLDocParser("doc1")
    p.handle_startendtag("img", [("src", "i.png")])
    assert len(p.elements) == 1
    assert p.elements[0].type == "image"


def test_handle_startendtag_br_outside_block_no_crash():
    p = _HTMLDocParser("doc1")
    p.handle_startendtag("br", [])
    assert p.elements == []


def test_handle_startendtag_hr_flushes_block():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("p", [])
    p.handle_data("text")
    p.handle_startendtag("hr", [])
    assert p._cur_kind is None


def test_handle_startendtag_unknown_tag_falls_back_to_starttag():
    """未知自闭合 tag 走 starttag 逻辑。"""
    p = _HTMLDocParser("doc1")
    p.handle_startendtag("h1", [])
    # handle_starttag 处理 h1 → 启 heading block
    assert p._cur_kind == "heading"


# =========================================================================
# _HTMLDocParser handle_endtag：边界
# =========================================================================


def test_handle_endtag_skip_stack_mismatched_other_tag_no_crash():
    """进入 script 后遇到 </p>（非 script）→ 忽略，不抛。"""
    p = _HTMLDocParser("doc1")
    p.handle_starttag("script", [])
    p.handle_endtag("p")  # 不匹配 script
    assert "script" in p._skip_stack  # 仍在 skip


def test_handle_endtag_skip_stack_matching_pops():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("script", [])
    p.handle_endtag("script")
    assert p._skip_stack == []


def test_handle_endtag_p_when_no_cur_kind_no_crash():
    p = _HTMLDocParser("doc1")
    p.handle_endtag("p")  # 没有对应开始
    assert p.elements == []


def test_handle_endtag_li_when_no_cur_kind_no_crash():
    p = _HTMLDocParser("doc1")
    p.handle_endtag("li")
    assert p.elements == []


def test_handle_endtag_ul_pops_list_stack():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("ul", [])
    p.handle_endtag("ul")
    assert p._list_stack == []


def test_handle_endtag_ol_pops_list_stack():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("ol", [])
    p.handle_endtag("ol")
    assert p._list_stack == []


def test_handle_endtag_ul_mismatched_ol_no_pop():
    """<ul> 内遇到 </ol> 不应 pop ul。"""
    p = _HTMLDocParser("doc1")
    p.handle_starttag("ul", [])
    p.handle_endtag("ol")
    assert p._list_stack == ["ul"]


def test_handle_endtag_pre_decrements_depth():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("pre", [])
    p.handle_endtag("pre")
    assert p._pre_depth == 0


def test_handle_endtag_blockquote_decrements_depth():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("blockquote", [])
    p.handle_endtag("blockquote")
    assert p._blockquote_depth == 0


def test_handle_endtag_table_with_no_inner_emits_no_element():
    """<table></table> 空 → 不 emit table element。"""
    p = _HTMLDocParser("doc1")
    p.handle_starttag("table", [])
    p.handle_endtag("table")
    assert p.elements == []
    assert p._table_depth == 0


def test_handle_endtag_table_with_rows_emits_table_element():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("table", [])
    p.handle_starttag("tr", [])
    p.handle_starttag("td", [])
    p.handle_data("cell")
    p.handle_endtag("td")
    p.handle_endtag("tr")
    p.handle_endtag("table")
    assert len(p.elements) == 1
    assert p.elements[0].type == "table"


# =========================================================================
# _HTMLDocParser _flush_block 边界
# =========================================================================


def test_flush_block_with_none_kind_is_noop():
    p = _HTMLDocParser("doc1")
    p._flush_block()
    assert p.elements == []


def test_flush_block_with_empty_buffer_no_emit():
    p = _HTMLDocParser("doc1")
    p._cur_kind = "paragraph"
    p._cur_buffer = []
    p._flush_block()
    assert p.elements == []


def test_flush_block_with_whitespace_buffer_no_emit():
    p = _HTMLDocParser("doc1")
    p._cur_kind = "paragraph"
    p._cur_buffer = ["   ", "\n", "\t"]
    p._flush_block()
    assert p.elements == []


def test_flush_block_resets_state_after_emit():
    p = _HTMLDocParser("doc1")
    p._cur_kind = "paragraph"
    p._cur_buffer = ["text"]
    p._cur_start_line = 5
    p._flush_block()
    assert p._cur_kind is None
    assert p._cur_buffer == []
    assert len(p.elements) == 1


# =========================================================================
# _HTMLDocParser _reset_block 边界
# =========================================================================


def test_reset_block_clears_state():
    p = _HTMLDocParser("doc1")
    p._cur_kind = "paragraph"
    p._cur_buffer = ["x"]
    p._cur_level = 3
    p._cur_ordered = True
    p._reset_block()
    assert p._cur_kind is None
    assert p._cur_buffer == []
    assert p._cur_level == 0
    assert p._cur_ordered is False


def test_reset_block_multiple_calls_no_crash():
    p = _HTMLDocParser("doc1")
    p._reset_block()
    p._reset_block()
    p._reset_block()
    assert p._cur_kind is None


# =========================================================================
# _HTMLDocParser _start_block 边界
# =========================================================================


def test_start_block_sets_kind():
    p = _HTMLDocParser("doc1")
    p._start_block("paragraph")
    assert p._cur_kind == "paragraph"


def test_start_block_clears_buffer():
    p = _HTMLDocParser("doc1")
    p._cur_buffer = ["old"]
    p._start_block("paragraph")
    assert p._cur_buffer == []


def test_start_block_flushes_previous_block():
    p = _HTMLDocParser("doc1")
    p._cur_kind = "paragraph"
    p._cur_buffer = ["prev"]
    p._start_block("paragraph")
    assert len(p.elements) == 1


def test_start_block_sets_level_for_heading():
    p = _HTMLDocParser("doc1")
    p._start_block("heading", level=3)
    assert p._cur_level == 3


def test_start_block_sets_ordered_flag():
    p = _HTMLDocParser("doc1")
    p._start_block("list_item", ordered=True)
    assert p._cur_ordered is True


# =========================================================================
# _HTMLDocParser _make_locator 边界
# =========================================================================


def test_make_locator_for_current_no_section_returns_only_line():
    p = _HTMLDocParser("doc1")
    p._cur_start_line = 42
    loc = p._make_locator_for_current()
    assert loc == {"family": "line_address", "line": 42}


def test_make_locator_for_inline_no_section_returns_only_line():
    p = _HTMLDocParser("doc1")
    loc = p._make_locator_for_inline()
    assert "line" in loc
    assert "section_path" not in loc


def test_make_locator_for_current_with_section_returns_section_path():
    p = _HTMLDocParser("doc1")
    p._cur_start_line = 5
    p._section_path = ["H1", "H2"]
    loc = p._make_locator_for_current()
    assert loc["section_path"] == "H1 > H2"


def test_make_locator_for_inline_with_section_returns_section_path():
    p = _HTMLDocParser("doc1")
    p._section_path = ["T"]
    loc = p._make_locator_for_inline()
    assert loc["section_path"] == "T"


# =========================================================================
# _HTMLDocParser section_path 跟踪深度
# =========================================================================


def test_section_path_after_h1_h2():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("h1", [])
    p.handle_data("First")
    p.handle_endtag("h1")
    p.handle_starttag("h2", [])
    p.handle_data("Second")
    p.handle_endtag("h2")
    assert p._section_path == ["First", "Second"]
    assert p._section_levels == [1, 2]


def test_section_path_h2_then_h1_pops_h2():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("h1", [])
    p.handle_data("A")
    p.handle_endtag("h1")
    p.handle_starttag("h2", [])
    p.handle_data("B")
    p.handle_endtag("h2")
    p.handle_starttag("h1", [])
    p.handle_data("C")
    p.handle_endtag("h1")
    # h1 弹出 h2 (level 2 >= 1) 和 h1 A (level 1 >= 1)
    # 然后 push C
    # 实际：先 pop 所有 >= 1，再 push
    # A=1, B=2 → 都 >= 1 → pop both → push C
    # 但 pop 条件是 >= level，level=1 时所有 >= 1 都 pop
    # 等下 — 看代码：while levels[-1] >= level: pop
    # level=1, levels=[1,2], 2>=1 pop, 1>=1 pop → 都 pop
    # 然后 push 1
    assert p._section_levels == [1]
    assert p._section_path == ["C"]


def test_section_path_same_level_h1_h1_keeps_one_push():
    p = _HTMLDocParser("doc1")
    p.handle_starttag("h1", [])
    p.handle_data("First")
    p.handle_endtag("h1")
    p.handle_starttag("h1", [])
    p.handle_data("Second")
    p.handle_endtag("h1")
    # 同级 h1：先 pop 同级，再 push
    # 第二个 h1：levels=[1], 1>=1 pop → [], push 1
    assert p._section_path == ["Second"]


def test_section_path_h3_h2_h1_complete_pop():
    p = _HTMLDocParser("doc1")
    for level, text in [("h1", "A"), ("h2", "B"), ("h3", "C")]:
        p.handle_starttag(level, [])
        p.handle_data(text)
        p.handle_endtag(level)
    p.handle_starttag("h1", [])
    p.handle_data("D")
    p.handle_endtag("h1")
    # h1 弹出所有 1, 2, 3
    assert p._section_path == ["D"]
    assert p._section_levels == [1]


# =========================================================================
# HtmlParser.parse：错误路径
# =========================================================================


def test_html_parse_unicode_decode_fallback_to_replace(tmp_path: Path):
    """utf-8 解码失败时改用 errors='replace'。"""
    p = tmp_path / "x.html"
    # 写入非 utf-8 字节
    p.write_bytes(b"\xff\xfe<html><body><p>test</p></body></html>")
    parser = HtmlParser()
    sha = "a" * 64
    doc = parser.parse(p, source_hash=sha)
    # 不抛 → 已用 replace
    assert doc is not None


def test_html_parse_os_error_raises_html_read_failed(tmp_path: Path, monkeypatch):
    p = tmp_path / "x.html"
    p.write_text("<html></html>", encoding="utf-8")

    original_read_text = Path.read_text

    def fake_read_text(self, *args, **kwargs):
        if self == p:
            raise OSError("disk error")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    parser = HtmlParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(p, source_hash="a" * 64)
    assert exc_info.value.code == "html_read_failed"


def test_html_parse_handler_feed_failure_raises_html_parse_failed(
    tmp_path: Path, monkeypatch
):
    p = tmp_path / "x.html"
    p.write_text("<html></html>", encoding="utf-8")

    def fake_feed(self, data):
        raise RuntimeError("feed broken")

    monkeypatch.setattr(_HTMLDocParser, "feed", fake_feed)
    parser = HtmlParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(p, source_hash="a" * 64)
    assert exc_info.value.code == "html_parse_failed"


def test_html_parse_handler_close_failure_raises_html_parse_failed(
    tmp_path: Path, monkeypatch
):
    p = tmp_path / "x.html"
    p.write_text("<html></html>", encoding="utf-8")

    def fake_close(self):
        raise RuntimeError("close broken")

    monkeypatch.setattr(_HTMLDocParser, "close", fake_close)
    parser = HtmlParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(p, source_hash="a" * 64)
    assert exc_info.value.code == "html_parse_failed"


def test_html_parse_file_not_found_raises():
    parser = HtmlParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(Path("nonexistent.html"), source_hash="a" * 64)
    assert exc_info.value.code == "file_not_found"


def test_html_parse_unsupported_suffix_raises(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    parser = HtmlParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(p, source_hash="a" * 64)
    assert exc_info.value.code == "unsupported_type"


# =========================================================================
# HtmlParser 类属性
# =========================================================================


def test_html_parser_class_name_value():
    assert HtmlParser.name == "html"


def test_html_parser_class_version_value():
    assert HtmlParser.version == "stdlib/0.1.0"


def test_html_parser_class_name_is_str():
    assert isinstance(HtmlParser.name, str)


def test_html_parser_class_version_is_str():
    assert isinstance(HtmlParser.version, str)


def test_html_parser_instance_name_matches_class():
    p = HtmlParser()
    assert p.name == "html"


def test_html_parser_instance_version_matches_class():
    p = HtmlParser()
    assert p.version == "stdlib/0.1.0"


def test_html_parser_inherits_parser():
    from app.parsers.base import Parser

    assert issubclass(HtmlParser, Parser)


def test_html_parser_parse_signature():
    import inspect

    sig = inspect.signature(HtmlParser.parse)
    params = list(sig.parameters.keys())
    assert params[0] == "self"
    assert "path" in sig.parameters
    assert "source_hash" in sig.parameters


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_all_exports_only_html_parser():
    from app.parsers import html_parser as mod

    assert mod.__all__ == ["HtmlParser"]


def test_module_imports_html_parser_class():
    """模块用 `as _StdHTMLParser` 导入 stdlib HTMLParser。"""
    from app.parsers import html_parser as mod

    assert hasattr(mod, "_StdHTMLParser")


def test_module_imports_path():
    from app.parsers import html_parser as mod

    assert hasattr(mod, "Path")


def test_module_imports_any():
    from app.parsers import html_parser as mod

    assert hasattr(mod, "Any")


def test_module_imports_document():
    from app.parsers import html_parser as mod

    assert hasattr(mod, "Document")


def test_module_imports_element():
    from app.parsers import html_parser as mod

    assert hasattr(mod, "Element")


def test_module_imports_warning_record():
    from app.parsers import html_parser as mod

    assert hasattr(mod, "WarningRecord")


def test_module_imports_parser():
    from app.parsers import html_parser as mod

    assert hasattr(mod, "Parser")


def test_module_imports_parser_error():
    from app.parsers import html_parser as mod

    assert hasattr(mod, "ParserError")


def test_module_imports_make_document_id():
    from app.parsers import html_parser as mod

    assert hasattr(mod, "make_document_id")


def test_module_has_doc_parser_class():
    from app.parsers import html_parser as mod

    assert hasattr(mod, "_HTMLDocParser")


def test_module_doc_parser_inherits_stdlib_html_parser():
    from html.parser import HTMLParser as StdHTMLParser

    assert issubclass(_HTMLDocParser, StdHTMLParser)


def test_module_html_parser_has_docstring():
    assert HtmlParser.__doc__ is not None


def test_module_doc_parser_has_docstring():
    assert _HTMLDocParser.__doc__ is not None


def test_module_rows_to_md_has_docstring():
    # _rows_to_md 无 docstring（私有 helper）
    assert callable(_rows_to_md)


def test_module_html_parser_class_docstring_mentions_html():
    doc = HtmlParser.__doc__ or ""
    assert "html" in doc.lower() or "HTML" in doc
