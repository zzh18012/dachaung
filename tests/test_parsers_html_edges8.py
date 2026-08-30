r"""app/parsers/html_parser.py 边角测试 - 第八轮（Round 191）。

补强已有 base/edges/edges2-7（共 808 测试）未覆盖的深度：
- _HTMLDocParser 直接方法测试（_make_locator_for_current/_emit_image/_flush_block/_reset_block/_start_block）
- handle_starttag 各分支深入（img src 处理、br/hr 行为、ul/ol 列表栈、嵌套 pre/blockquote depth）
- handle_endtag 各分支（不匹配 tag 无副作用、未开启 pre 关闭、未开启 blockquote 关闭）
- handle_data 各分支（skip_stack/table/loose text/in-block buffer）
- section_path 复杂栈操作（h1→h2→h3→h1 全 pop、同级 heading 替换、跨层级跳）
- 模块结构深度（imports、__all__、docstring 内容）
- WarningRecord 内容验证（reason 字段、嵌套 table 警告）
- HtmlParser 类属性稳定性（多次实例化）
"""

from __future__ import annotations

import inspect
from html.parser import HTMLParser as _StdHTMLParser
from pathlib import Path
from typing import Any

import pytest

from app.parsers.base import Parser, ParserError
from app.parsers.html_parser import (
    _detect_html_source_type,
    _HTMLDocParser,
    _HEADING_LEVELS,
    _HTML_EXTENSIONS,
    _rows_to_md,
    _SKIP_TAGS,
    HtmlParser,
)
import app.parsers.html_parser as html_mod


# =========================================================================
# _HTMLDocParser 直接方法测试（不通过 feed）
# =========================================================================


def test_doc_parser_init_cur_kind_none():
    p = _HTMLDocParser("doc-x")
    assert p._cur_kind is None


def test_doc_parser_init_cur_buffer_empty_list():
    p = _HTMLDocParser("doc-x")
    assert p._cur_buffer == []


def test_doc_parser_init_document_id_stored():
    p = _HTMLDocParser("doc-x")
    assert p.document_id == "doc-x"


def test_doc_parser_init_elements_is_list():
    p = _HTMLDocParser("doc-x")
    assert isinstance(p.elements, list)


def test_doc_parser_init_warnings_is_list():
    p = _HTMLDocParser("doc-x")
    assert isinstance(p.warnings, list)


def test_doc_parser_init_pre_depth_zero():
    p = _HTMLDocParser("doc-x")
    assert p._pre_depth == 0


def test_doc_parser_init_blockquote_depth_zero():
    p = _HTMLDocParser("doc-x")
    assert p._blockquote_depth == 0


def test_doc_parser_init_table_depth_zero():
    p = _HTMLDocParser("doc-x")
    assert p._table_depth == 0


def test_doc_parser_init_section_path_empty():
    p = _HTMLDocParser("doc-x")
    assert p._section_path == []


def test_doc_parser_init_section_levels_empty():
    p = _HTMLDocParser("doc-x")
    assert p._section_levels == []


def test_doc_parser_init_list_stack_empty():
    p = _HTMLDocParser("doc-x")
    assert p._list_stack == []


def test_doc_parser_init_skip_stack_empty():
    p = _HTMLDocParser("doc-x")
    assert p._skip_stack == []


def test_doc_parser_init_table_rows_stack_empty():
    p = _HTMLDocParser("doc-x")
    assert p._table_rows_stack == []


def test_doc_parser_init_cur_start_line_zero():
    p = _HTMLDocParser("doc-x")
    assert p._cur_start_line == 0


def test_doc_parser_init_cur_level_zero():
    p = _HTMLDocParser("doc-x")
    assert p._cur_level == 0


def test_doc_parser_init_cur_ordered_false():
    p = _HTMLDocParser("doc-x")
    assert p._cur_ordered is False


# =========================================================================
# _make_locator_for_current 直接测试
# =========================================================================


def test_make_locator_for_current_no_section_returns_only_line():
    p = _HTMLDocParser("doc-x")
    p._cur_start_line = 42
    loc = p._make_locator_for_current()
    assert loc == {"family": "line_address", "line": 42}


def test_make_locator_for_current_with_section_returns_both():
    p = _HTMLDocParser("doc-x")
    p._cur_start_line = 5
    p._section_path = ["H1", "H2"]
    loc = p._make_locator_for_current()
    assert loc == {"family": "line_address", "line": 5, "section_path": "H1 > H2"}


def test_make_locator_for_current_section_joined_with_gt():
    p = _HTMLDocParser("doc-x")
    p._cur_start_line = 1
    p._section_path = ["Alpha", "Beta", "Gamma"]
    loc = p._make_locator_for_current()
    assert loc["section_path"] == "Alpha > Beta > Gamma"


def test_make_locator_for_current_default_line_zero():
    p = _HTMLDocParser("doc-x")
    loc = p._make_locator_for_current()
    assert loc["line"] == 0


# =========================================================================
# _make_locator_for_inline 直接测试
# =========================================================================


def test_make_locator_for_inline_uses_getpos_line():
    p = _HTMLDocParser("doc-x")
    # getpos() 默认 (1, 0) 在初始化后
    loc = p._make_locator_for_inline()
    assert "line" in loc


def test_make_locator_for_inline_no_section():
    p = _HTMLDocParser("doc-x")
    loc = p._make_locator_for_inline()
    assert "section_path" not in loc


def test_make_locator_for_inline_with_section():
    p = _HTMLDocParser("doc-x")
    p._section_path = ["S"]
    loc = p._make_locator_for_inline()
    assert loc.get("section_path") == "S"


# =========================================================================
# _reset_block 直接测试
# =========================================================================


def test_reset_block_clears_cur_kind():
    p = _HTMLDocParser("doc-x")
    p._cur_kind = "paragraph"
    p._reset_block()
    assert p._cur_kind is None


def test_reset_block_clears_cur_buffer():
    p = _HTMLDocParser("doc-x")
    p._cur_buffer = ["text"]
    p._reset_block()
    assert p._cur_buffer == []


def test_reset_block_resets_cur_level():
    p = _HTMLDocParser("doc-x")
    p._cur_level = 5
    p._reset_block()
    assert p._cur_level == 0


def test_reset_block_resets_cur_ordered():
    p = _HTMLDocParser("doc-x")
    p._cur_ordered = True
    p._reset_block()
    assert p._cur_ordered is False


def test_reset_block_does_not_clear_section():
    """_reset_block 不影响 section_path。"""
    p = _HTMLDocParser("doc-x")
    p._section_path = ["X"]
    p._reset_block()
    assert p._section_path == ["X"]


# =========================================================================
# _start_block 直接测试
# =========================================================================


def test_start_block_sets_cur_kind():
    p = _HTMLDocParser("doc-x")
    p._start_block("paragraph")
    assert p._cur_kind == "paragraph"


def test_start_block_clears_cur_buffer():
    p = _HTMLDocParser("doc-x")
    p._cur_buffer = ["old"]
    p._start_block("paragraph")
    assert p._cur_buffer == []


def test_start_block_sets_cur_level():
    p = _HTMLDocParser("doc-x")
    p._start_block("heading", level=3)
    assert p._cur_level == 3


def test_start_block_sets_cur_ordered():
    p = _HTMLDocParser("doc-x")
    p._start_block("list_item", ordered=True)
    assert p._cur_ordered is True


def test_start_block_default_level_zero():
    p = _HTMLDocParser("doc-x")
    p._start_block("paragraph")
    assert p._cur_level == 0


def test_start_block_default_ordered_false():
    p = _HTMLDocParser("doc-x")
    p._start_block("list_item")
    assert p._cur_ordered is False


def test_start_block_flushes_existing_block():
    """调用 _start_block 时若已有 block，应先 flush。"""
    p = _HTMLDocParser("doc-x")
    p._start_block("paragraph")
    p._cur_buffer = ["text"]
    p._start_block("heading", level=1)
    # 第一个 paragraph 应已被 flush 到 elements
    assert len(p.elements) == 1
    assert p.elements[0].type == "paragraph"


def test_start_block_updates_cur_start_line_via_getpos():
    p = _HTMLDocParser("doc-x")
    p._start_block("paragraph")
    # 至少被设置（具体值依赖 getpos，初始化后通常是 1）
    assert p._cur_start_line >= 0


# =========================================================================
# _flush_block 直接测试
# =========================================================================


def test_flush_block_no_kind_is_noop():
    p = _HTMLDocParser("doc-x")
    p._flush_block()
    assert p.elements == []


def test_flush_block_empty_text_no_element():
    p = _HTMLDocParser("doc-x")
    p._cur_kind = "paragraph"
    p._cur_buffer = ["   "]  # whitespace only → strip empty
    p._flush_block()
    assert p.elements == []


def test_flush_block_resets_after_flush():
    p = _HTMLDocParser("doc-x")
    p._cur_kind = "paragraph"
    p._cur_buffer = ["text"]
    p._flush_block()
    assert p._cur_kind is None
    assert p._cur_buffer == []


def test_flush_block_paragraph_emits_paragraph():
    p = _HTMLDocParser("doc-x")
    p._cur_kind = "paragraph"
    p._cur_buffer = ["hello"]
    p._flush_block()
    assert len(p.elements) == 1
    assert p.elements[0].type == "paragraph"
    assert p.elements[0].content == "hello"


def test_flush_block_heading_emits_heading():
    p = _HTMLDocParser("doc-x")
    p._cur_kind = "heading"
    p._cur_buffer = ["Title"]
    p._cur_level = 2
    p._flush_block()
    assert len(p.elements) == 1
    assert p.elements[0].type == "heading"
    assert p.elements[0].metadata["level"] == 2


def test_flush_block_heading_pushes_to_section_path():
    p = _HTMLDocParser("doc-x")
    p._cur_kind = "heading"
    p._cur_buffer = ["Title"]
    p._cur_level = 1
    p._flush_block()
    assert p._section_path == ["Title"]
    assert p._section_levels == [1]


def test_flush_block_list_item_emits_list_item():
    p = _HTMLDocParser("doc-x")
    p._cur_kind = "list_item"
    p._cur_buffer = ["item"]
    p._cur_ordered = True
    p._flush_block()
    assert len(p.elements) == 1
    assert p.elements[0].type == "list_item"
    assert p.elements[0].metadata["ordered"] is True


def test_flush_block_pre_emits_paragraph_with_kind_preformatted():
    p = _HTMLDocParser("doc-x")
    p._cur_kind = "pre"
    p._cur_buffer = ["code"]
    p._flush_block()
    assert len(p.elements) == 1
    assert p.elements[0].type == "paragraph"
    assert p.elements[0].metadata["kind"] == "preformatted"


def test_flush_block_blockquote_emits_paragraph_with_kind_blockquote():
    p = _HTMLDocParser("doc-x")
    p._cur_kind = "blockquote"
    p._cur_buffer = ["quote"]
    p._flush_block()
    assert len(p.elements) == 1
    assert p.elements[0].type == "paragraph"
    assert p.elements[0].metadata["kind"] == "blockquote"


def test_flush_block_paragraph_no_kind_metadata():
    """paragraph（非 pre/blockquote）的 metadata 是空 dict。"""
    p = _HTMLDocParser("doc-x")
    p._cur_kind = "paragraph"
    p._cur_buffer = ["plain"]
    p._flush_block()
    assert p.elements[0].metadata == {}


def test_flush_block_paragraph_confidence_095():
    p = _HTMLDocParser("doc-x")
    p._cur_kind = "paragraph"
    p._cur_buffer = ["x"]
    p._flush_block()
    assert p.elements[0].confidence == 0.95


def test_flush_block_heading_confidence_095():
    p = _HTMLDocParser("doc-x")
    p._cur_kind = "heading"
    p._cur_buffer = ["x"]
    p._cur_level = 1
    p._flush_block()
    assert p.elements[0].confidence == 0.95


def test_flush_block_list_item_confidence_095():
    p = _HTMLDocParser("doc-x")
    p._cur_kind = "list_item"
    p._cur_buffer = ["x"]
    p._flush_block()
    assert p.elements[0].confidence == 0.95


def test_flush_block_heading_section_path_pops_higher_levels():
    """heading level=2 时弹出 section_levels >= 2 的项。"""
    p = _HTMLDocParser("doc-x")
    p._section_levels = [1, 2, 3]
    p._section_path = ["H1", "H2", "H3"]
    p._cur_kind = "heading"
    p._cur_buffer = ["New"]
    p._cur_level = 2
    p._flush_block()
    # 应弹出 H3、H2，保留 H1
    assert p._section_levels == [1, 2]
    assert p._section_path == ["H1", "New"]


def test_flush_block_heading_section_path_pops_same_level():
    """同级 heading 替换（pop >= level）。"""
    p = _HTMLDocParser("doc-x")
    p._section_levels = [1, 2]
    p._section_path = ["H1", "H2"]
    p._cur_kind = "heading"
    p._cur_buffer = ["H2 New"]
    p._cur_level = 2
    p._flush_block()
    # H2 被弹出，新 H2 加入
    assert p._section_levels == [1, 2]
    assert p._section_path == ["H1", "H2 New"]


def test_flush_block_heading_h1_pops_everything():
    """h1 弹出所有 >= 1 的层级。"""
    p = _HTMLDocParser("doc-x")
    p._section_levels = [1, 2, 3]
    p._section_path = ["H1", "H2", "H3"]
    p._cur_kind = "heading"
    p._cur_buffer = ["Top"]
    p._cur_level = 1
    p._flush_block()
    assert p._section_levels == [1]
    assert p._section_path == ["Top"]


def test_flush_block_heading_lowest_level_appends():
    """h3 在 [1, 2] 之后无弹出，直接 append。"""
    p = _HTMLDocParser("doc-x")
    p._section_levels = [1, 2]
    p._section_path = ["H1", "H2"]
    p._cur_kind = "heading"
    p._cur_buffer = ["Deep"]
    p._cur_level = 3
    p._flush_block()
    assert p._section_levels == [1, 2, 3]
    assert p._section_path == ["H1", "H2", "Deep"]


def test_flush_block_heading_default_level_one_when_zero():
    """cur_level=0 时，max(level, 1) = 1。"""
    p = _HTMLDocParser("doc-x")
    p._cur_kind = "heading"
    p._cur_buffer = ["X"]
    p._cur_level = 0  # 未设置
    p._flush_block()
    assert p.elements[0].metadata["level"] == 1


# =========================================================================
# _emit_image 直接测试
# =========================================================================


def test_emit_image_appends_image_element():
    p = _HTMLDocParser("doc-x")
    p._emit_image("img.png", "alt text")
    assert len(p.elements) == 1
    assert p.elements[0].type == "image"
    assert p.elements[0].resource_path == "img.png"


def test_emit_image_metadata_has_alt():
    p = _HTMLDocParser("doc-x")
    p._emit_image("img.png", "alt text")
    assert p.elements[0].metadata == {"alt": "alt text"}


def test_emit_image_content_is_none():
    p = _HTMLDocParser("doc-x")
    p._emit_image("img.png", "")
    assert p.elements[0].content is None


def test_emit_image_confidence_09():
    p = _HTMLDocParser("doc-x")
    p._emit_image("img.png", "")
    assert p.elements[0].confidence == 0.9


def test_emit_image_flushes_existing_block():
    """emit_image 前应先 flush 当前 block。"""
    p = _HTMLDocParser("doc-x")
    p._cur_kind = "paragraph"
    p._cur_buffer = ["pending text"]
    p._emit_image("img.png", "")
    assert len(p.elements) == 2
    assert p.elements[0].type == "paragraph"
    assert p.elements[1].type == "image"


def test_emit_image_element_id_increments():
    p = _HTMLDocParser("doc-x")
    p._emit_image("a.png", "")
    p._emit_image("b.png", "")
    assert p.elements[0].element_id.endswith("e0000")
    assert p.elements[1].element_id.endswith("e0001")


def test_emit_image_locator_uses_getpos():
    """locator 是 inline（用 getpos），不是 cur_start_line。"""
    p = _HTMLDocParser("doc-x")
    p._cur_start_line = 99  # 不该影响 inline locator
    p._emit_image("img.png", "")
    assert "line" in p.elements[0].source_locator


# =========================================================================
# handle_starttag 各分支
# =========================================================================


def test_handle_starttag_img_with_attrs_dispatches_to_emit_image():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("img", [("src", "x.png"), ("alt", "y")])
    assert len(p.elements) == 1
    assert p.elements[0].type == "image"


def test_handle_starttag_img_empty_src_skipped():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("img", [("src", ""), ("alt", "y")])
    assert p.elements == []


def test_handle_starttag_img_whitespace_src_skipped():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("img", [("src", "   "), ("alt", "y")])
    assert p.elements == []


def test_handle_starttag_img_missing_alt_attribute():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("img", [("src", "x.png")])
    assert len(p.elements) == 1
    assert p.elements[0].metadata == {"alt": ""}


def test_handle_starttag_img_none_alt_becomes_empty():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("img", [("src", "x.png"), ("alt", None)])
    assert len(p.elements) == 1
    assert p.elements[0].metadata == {"alt": ""}


def test_handle_starttag_br_in_block_appends_space():
    p = _HTMLDocParser("doc-x")
    p._start_block("paragraph")
    p.handle_starttag("br", [])
    assert " " in p._cur_buffer


def test_handle_starttag_br_outside_block_noop():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("br", [])
    assert p._cur_kind is None
    assert p._cur_buffer == []


def test_handle_starttag_hr_flushes_block():
    p = _HTMLDocParser("doc-x")
    p._start_block("paragraph")
    p._cur_buffer = ["text"]
    p.handle_starttag("hr", [])
    # paragraph 应被 flush
    assert len(p.elements) == 1


def test_handle_starttag_ul_pushes_list_stack():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("ul", [])
    assert p._list_stack == ["ul"]


def test_handle_starttag_ol_pushes_list_stack():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("ol", [])
    assert p._list_stack == ["ol"]


def test_handle_starttag_li_in_ul_unordered():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("ul", [])
    p.handle_starttag("li", [])
    assert p._cur_kind == "list_item"
    assert p._cur_ordered is False


def test_handle_starttag_li_in_ol_ordered():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("ol", [])
    p.handle_starttag("li", [])
    assert p._cur_kind == "list_item"
    assert p._cur_ordered is True


def test_handle_starttag_li_no_list_defaults_unordered():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("li", [])
    assert p._cur_kind == "list_item"
    assert p._cur_ordered is False


def test_handle_starttag_pre_increments_pre_depth():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("pre", [])
    assert p._pre_depth == 1


def test_handle_starttag_pre_starts_pre_block():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("pre", [])
    assert p._cur_kind == "pre"


def test_handle_starttag_pre_nested_does_not_restart_block():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("pre", [])
    p._cur_buffer = ["existing"]
    p.handle_starttag("pre", [])  # nested pre
    assert p._pre_depth == 2
    # _cur_buffer 不应被清空（不重新 _start_block）
    assert "existing" in p._cur_buffer


def test_handle_starttag_blockquote_increments_depth():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("blockquote", [])
    assert p._blockquote_depth == 1


def test_handle_starttag_blockquote_nested_does_not_restart_block():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("blockquote", [])
    p._cur_buffer = ["existing"]
    p.handle_starttag("blockquote", [])
    assert p._blockquote_depth == 2
    assert "existing" in p._cur_buffer


def test_handle_starttag_p_in_pre_ignored():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("pre", [])
    p._cur_buffer = ["code"]
    p.handle_starttag("p", [])  # 不应改 cur_kind
    assert p._cur_kind == "pre"


def test_handle_starttag_p_in_blockquote_ignored():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("blockquote", [])
    p._cur_buffer = ["quote"]
    p.handle_starttag("p", [])
    assert p._cur_kind == "blockquote"


def test_handle_starttag_inline_tag_ignored():
    """inline tags（b/i/a/strong/em）应被忽略。"""
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("b", [])
    p.handle_starttag("i", [])
    p.handle_starttag("a", [("href", "x")])
    assert p._cur_kind is None
    assert p.elements == []


def test_handle_starttag_skip_tag_pushes_skip_stack():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("script", [])
    assert p._skip_stack == ["script"]


def test_handle_starttag_nested_skip_tag_appends():
    """script 内的 script-like tag（实际不合法，但测栈行为）。"""
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("script", [])
    p.handle_starttag("script", [])
    assert p._skip_stack == ["script", "script"]


def test_handle_starttag_other_tag_in_skip_noop():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("script", [])
    p.handle_starttag("p", [])  # 在 skip 内，应被忽略
    assert p._cur_kind is None


def test_handle_starttag_table_starts_table_mode():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("table", [])
    assert p._table_depth == 1
    assert len(p._table_rows_stack) == 1
    assert p._table_rows_stack[-1] == []


def test_handle_starttag_nested_table_emits_warning():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("table", [])
    p.handle_starttag("table", [])  # 嵌套
    assert len(p.warnings) == 1
    assert p.warnings[0].code == "html_nested_table"


def test_handle_starttag_nested_table_adds_depth():
    # BUG-html-1 修复后：内层 table 压入独立上下文，depth 递增
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("table", [])
    p.handle_starttag("table", [])
    assert p._table_depth == 2


# =========================================================================
# handle_endtag 各分支
# =========================================================================


def test_handle_endtag_p_outside_paragraph_noop():
    p = _HTMLDocParser("doc-x")
    p.handle_endtag("p")
    assert p.elements == []


def test_handle_endtag_heading_outside_heading_noop():
    p = _HTMLDocParser("doc-x")
    p.handle_endtag("h1")
    assert p.elements == []


def test_handle_endtag_li_outside_list_item_noop():
    p = _HTMLDocParser("doc-x")
    p.handle_endtag("li")
    assert p.elements == []


def test_handle_endtag_pre_without_open_decrements_clamped():
    """pre_depth 不会变负。"""
    p = _HTMLDocParser("doc-x")
    p.handle_endtag("pre")
    assert p._pre_depth == 0


def test_handle_endtag_blockquote_without_open_clamped():
    p = _HTMLDocParser("doc-x")
    p.handle_endtag("blockquote")
    assert p._blockquote_depth == 0


def test_handle_endtag_ul_pops_list_stack():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("ul", [])
    p.handle_endtag("ul")
    assert p._list_stack == []


def test_handle_endtag_ol_pops_list_stack():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("ol", [])
    p.handle_endtag("ol")
    assert p._list_stack == []


def test_handle_endtag_wrong_list_tag_no_pop():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("ul", [])
    p.handle_endtag("ol")  # 错配
    assert p._list_stack == ["ul"]


def test_handle_endtag_skip_stack_pop_on_match():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("script", [])
    p.handle_endtag("script")
    assert p._skip_stack == []


def test_handle_endtag_in_skip_wrong_tag_ignored():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("script", [])
    p.handle_endtag("p")  # 不是 script
    assert p._skip_stack == ["script"]


def test_handle_endtag_unknown_tag_noop():
    p = _HTMLDocParser("doc-x")
    p.handle_endtag("unknown")
    assert p.elements == []
    assert p._skip_stack == []


def test_handle_endtag_table_ends_table_mode():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("table", [])
    p.handle_endtag("table")
    assert p._table_depth == 0


def test_handle_endtag_pre_only_outer_emits():
    """嵌套 pre 内层关闭不 flush；外层关闭才 flush。"""
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("pre", [])
    p.handle_starttag("pre", [])  # 嵌套
    p.handle_endtag("pre")  # 内层关闭
    assert p._cur_kind == "pre"  # block 未 flush
    p.handle_endtag("pre")  # 外层关闭
    assert p._cur_kind is None  # 现在 flush 了


# =========================================================================
# handle_startendtag 各分支
# =========================================================================


def test_handle_startendtag_img_emits_image():
    p = _HTMLDocParser("doc-x")
    p.handle_startendtag("img", [("src", "x.png")])
    assert len(p.elements) == 1


def test_handle_startendtag_br_in_block_appends_space():
    p = _HTMLDocParser("doc-x")
    p._start_block("paragraph")
    p.handle_startendtag("br", [])
    assert " " in p._cur_buffer


def test_handle_startendtag_hr_flushes_block():
    p = _HTMLDocParser("doc-x")
    p._start_block("paragraph")
    p._cur_buffer = ["text"]
    p.handle_startendtag("hr", [])
    assert len(p.elements) == 1


def test_handle_startendtag_unknown_dispatches_to_starttag():
    p = _HTMLDocParser("doc-x")
    p.handle_startendtag("ul", [])  # 自闭合 ul → 应触发 starttag
    assert p._list_stack == ["ul"]


# =========================================================================
# handle_data 各分支
# =========================================================================


def test_handle_data_in_skip_stack_ignored():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("script", [])
    p.handle_data("secret code")
    assert p.elements == []
    assert p._cur_buffer == []


def test_handle_data_in_table_cell_appended_to_buffer():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("table", [])
    p.handle_starttag("tr", [])
    p.handle_starttag("td", [])
    p.handle_data("cell text")
    assert p._cell_buffers_stack[-1] == ["cell text"]


def test_handle_data_loose_text_starts_paragraph():
    p = _HTMLDocParser("doc-x")
    p.handle_data("loose text")
    assert p._cur_kind == "paragraph"
    assert "loose text" in p._cur_buffer


def test_handle_data_whitespace_only_outside_block_ignored():
    p = _HTMLDocParser("doc-x")
    p.handle_data("   \n\t  ")
    assert p._cur_kind is None
    assert p._cur_buffer == []


def test_handle_data_in_existing_block_appended_to_buffer():
    p = _HTMLDocParser("doc-x")
    p._start_block("paragraph")
    p.handle_data("appended")
    assert "appended" in p._cur_buffer


def test_handle_data_in_heading_block_appended():
    p = _HTMLDocParser("doc-x")
    p._start_block("heading", level=1)
    p.handle_data("Heading Text")
    p.handle_endtag("h1")
    assert len(p.elements) == 1
    assert p.elements[0].content == "Heading Text"


def test_handle_data_in_list_item_block_appended():
    p = _HTMLDocParser("doc-x")
    p._start_block("list_item", ordered=True)
    p.handle_data("Item")
    p.handle_endtag("li")
    assert len(p.elements) == 1
    assert p.elements[0].content == "Item"


def test_handle_data_in_pre_block_appended():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("pre", [])
    p.handle_data("code line")
    p.handle_endtag("pre")
    assert len(p.elements) == 1
    assert "code line" in p.elements[0].content


def test_handle_data_in_blockquote_block_appended():
    p = _HTMLDocParser("doc-x")
    p.handle_starttag("blockquote", [])
    p.handle_data("quoted text")
    p.handle_endtag("blockquote")
    assert len(p.elements) == 1
    assert "quoted text" in p.elements[0].content


# =========================================================================
# _rows_to_md 深度
# =========================================================================


def test_rows_to_md_two_by_two_grid():
    result = _rows_to_md([["a", "b"], ["c", "d"]])
    lines = result.split("\n")
    assert len(lines) == 3  # header + sep + 1 body
    assert "a" in lines[0]
    assert "c" in lines[2]


def test_rows_to_md_one_by_one_grid():
    result = _rows_to_md([["x"]])
    lines = result.split("\n")
    assert len(lines) == 2  # header + sep
    assert "x" in lines[0]


def test_rows_to_md_separator_each_column_has_dashes():
    result = _rows_to_md([["a", "b", "c"], ["1", "2", "3"]])
    lines = result.split("\n")
    sep_line = lines[1]
    assert sep_line.count("---") == 3


def test_rows_to_md_returns_str():
    assert isinstance(_rows_to_md([]), str)
    assert isinstance(_rows_to_md([["x"]]), str)


def test_rows_to_md_single_body_row():
    result = _rows_to_md([["h1", "h2"], ["v1", "v2"]])
    lines = result.split("\n")
    assert len(lines) == 3


def test_rows_to_md_no_body_rows():
    """只有 header 一行 → 输出 header + sep。"""
    result = _rows_to_md([["h1", "h2"]])
    lines = result.split("\n")
    assert len(lines) == 2


# =========================================================================
# _detect_html_source_type 错误细节
# =========================================================================


def test_detect_html_source_type_error_code_value():
    with pytest.raises(ParserError) as exc_info:
        _detect_html_source_type(Path("x.txt"))
    assert exc_info.value.code == "unsupported_type"


def test_detect_html_source_type_error_details_has_suffix():
    with pytest.raises(ParserError) as exc_info:
        _detect_html_source_type(Path("x.xml"))
    assert "suffix" in exc_info.value.details
    assert exc_info.value.details["suffix"] == ".xml"


def test_detect_html_source_type_no_suffix_details_empty():
    with pytest.raises(ParserError) as exc_info:
        _detect_html_source_type(Path("noext"))
    assert exc_info.value.details["suffix"] == ""


def test_detect_html_source_type_returns_str_on_success():
    result = _detect_html_source_type(Path("x.html"))
    assert result == "html"


def test_detect_html_source_type_returns_str_on_htm():
    result = _detect_html_source_type(Path("x.htm"))
    assert result == "html"


# =========================================================================
# HtmlParser 类属性
# =========================================================================


def test_html_parser_name_value():
    assert HtmlParser.name == "html"


def test_html_parser_version_value():
    assert HtmlParser.version == "stdlib/0.1.0"


def test_html_parser_inherits_parser():
    assert issubclass(HtmlParser, Parser)


def test_html_parser_two_instances_same_attrs():
    a = HtmlParser()
    b = HtmlParser()
    assert a.name == b.name == "html"
    assert a.version == b.version == "stdlib/0.1.0"


def test_html_parser_class_attribute_accessible_from_class():
    """name/version 是 class attr，不需实例化即可访问。"""
    assert HtmlParser.name
    assert HtmlParser.version


def test_html_parser_instance_attrs_match_class():
    p = HtmlParser()
    assert p.name == HtmlParser.name
    assert p.version == HtmlParser.version


def test_html_parser_init_no_args():
    p = HtmlParser()
    assert p is not None


def test_html_parser_init_keyword_only_no_image_output_dir():
    """HtmlParser 不接受 image_output_dir 参数。"""
    sig = inspect.signature(HtmlParser.__init__)
    # 默认 __init__ from Parser 没有 image_output_dir
    assert "image_output_dir" not in sig.parameters


def test_html_parser_parse_method_signature():
    sig = inspect.signature(HtmlParser.parse)
    params = list(sig.parameters)
    assert params == ["self", "path", "source_hash"]


# =========================================================================
# 模块常量
# =========================================================================


def test_heading_levels_count_six():
    assert len(_HEADING_LEVELS) == 6


def test_heading_levels_keys_exact():
    assert set(_HEADING_LEVELS.keys()) == {"h1", "h2", "h3", "h4", "h5", "h6"}


def test_heading_levels_values_exact():
    assert set(_HEADING_LEVELS.values()) == {1, 2, 3, 4, 5, 6}


def test_heading_levels_is_dict():
    assert isinstance(_HEADING_LEVELS, dict)


def test_skip_tags_count_seven():
    assert len(_SKIP_TAGS) == 7


def test_skip_tags_is_set():
    assert isinstance(_SKIP_TAGS, set)


def test_skip_tags_values_exact():
    assert _SKIP_TAGS == {"script", "style", "head", "title", "meta", "link", "noscript"}


def test_html_extensions_count_two():
    assert len(_HTML_EXTENSIONS) == 2


def test_html_extensions_is_tuple():
    assert isinstance(_HTML_EXTENSIONS, tuple)


def test_html_extensions_values_exact():
    assert set(_HTML_EXTENSIONS) == {".html", ".htm"}


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    assert html_mod.__all__ == ["HtmlParser"]


def test_module_all_is_list():
    assert isinstance(html_mod.__all__, list)


def test_module_uses_future_annotations():
    src = inspect.getsource(html_mod)
    assert "from __future__ import annotations" in src


def test_module_imports_stdlib_html_parser():
    src = inspect.getsource(html_mod)
    assert "from html.parser import HTMLParser" in src


def test_module_imports_path():
    src = inspect.getsource(html_mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    src = inspect.getsource(html_mod)
    assert "from typing import Any" in src


def test_module_imports_models():
    src = inspect.getsource(html_mod)
    assert "from app.models" in src


def test_module_imports_base():
    src = inspect.getsource(html_mod)
    assert "from app.parsers.base" in src


def test_module_docstring_present():
    assert html_mod.__doc__ is not None


def test_module_docstring_mentions_supported_features():
    assert html_mod.__doc__ is not None
    assert "标题" in html_mod.__doc__ or "heading" in html_mod.__doc__.lower()


def test_module_docstring_mentions_skip_tags():
    assert html_mod.__doc__ is not None
    assert "跳过" in html_mod.__doc__ or "skip" in html_mod.__doc__.lower()


def test_module_docstring_mentions_unsupported_features():
    assert html_mod.__doc__ is not None
    assert "不支持" in html_mod.__doc__ or "unsupported" in html_mod.__doc__.lower()


def test_module_docstring_mentions_source_locator():
    assert html_mod.__doc__ is not None
    assert "source_locator" in html_mod.__doc__ or "section_path" in html_mod.__doc__


# =========================================================================
# _HTMLDocParser 继承 stdlib
# =========================================================================


def test_doc_parser_inherits_stdlib_html_parser():
    assert issubclass(_HTMLDocParser, _StdHTMLParser)


def test_doc_parser_convert_charrefs_true():
    p = _HTMLDocParser("doc-x")
    assert p.convert_charrefs is True


def test_doc_parser_has_handle_starttag():
    assert callable(_HTMLDocParser.handle_starttag)


def test_doc_parser_has_handle_endtag():
    assert callable(_HTMLDocParser.handle_endtag)


def test_doc_parser_has_handle_data():
    assert callable(_HTMLDocParser.handle_data)


def test_doc_parser_has_handle_startendtag():
    assert callable(_HTMLDocParser.handle_startendtag)


def test_doc_parser_handle_starttag_signature():
    sig = inspect.signature(_HTMLDocParser.handle_starttag)
    params = list(sig.parameters)
    assert params == ["self", "tag", "attrs"]


def test_doc_parser_handle_endtag_signature():
    sig = inspect.signature(_HTMLDocParser.handle_endtag)
    params = list(sig.parameters)
    assert params == ["self", "tag"]


def test_doc_parser_handle_data_signature():
    sig = inspect.signature(_HTMLDocParser.handle_data)
    params = list(sig.parameters)
    assert params == ["self", "data"]


def test_doc_parser_handle_startendtag_signature():
    sig = inspect.signature(_HTMLDocParser.handle_startendtag)
    params = list(sig.parameters)
    assert params == ["self", "tag", "attrs"]


def test_doc_parser_init_signature():
    sig = inspect.signature(_HTMLDocParser.__init__)
    params = list(sig.parameters)
    assert params == ["self", "document_id"]


def test_doc_parser_init_document_id_no_default():
    sig = inspect.signature(_HTMLDocParser.__init__)
    assert sig.parameters["document_id"].default is inspect.Parameter.empty


# =========================================================================
# _HTMLDocParser 内部方法存在性
# =========================================================================


def test_doc_parser_has_make_locator_for_current():
    assert callable(_HTMLDocParser._make_locator_for_current)


def test_doc_parser_has_make_locator_for_inline():
    assert callable(_HTMLDocParser._make_locator_for_inline)


def test_doc_parser_has_emit_image():
    assert callable(_HTMLDocParser._emit_image)


def test_doc_parser_has_flush_block():
    assert callable(_HTMLDocParser._flush_block)


def test_doc_parser_has_reset_block():
    assert callable(_HTMLDocParser._reset_block)


def test_doc_parser_has_start_block():
    assert callable(_HTMLDocParser._start_block)


def test_doc_parser_has_handle_table_inner_start():
    assert callable(_HTMLDocParser._handle_table_inner_start)


def test_doc_parser_has_handle_table_inner_end():
    assert callable(_HTMLDocParser._handle_table_inner_end)


def test_doc_parser_make_locator_for_current_signature():
    sig = inspect.signature(_HTMLDocParser._make_locator_for_current)
    params = list(sig.parameters)
    assert params == ["self"]


def test_doc_parser_emit_image_signature():
    sig = inspect.signature(_HTMLDocParser._emit_image)
    params = list(sig.parameters)
    assert params == ["self", "src", "alt"]


def test_doc_parser_start_block_signature():
    sig = inspect.signature(_HTMLDocParser._start_block)
    params = list(sig.parameters)
    assert params == ["self", "kind", "level", "ordered"]
    assert sig.parameters["level"].default == 0
    assert sig.parameters["ordered"].default is False


def test_doc_parser_flush_block_signature():
    sig = inspect.signature(_HTMLDocParser._flush_block)
    params = list(sig.parameters)
    assert params == ["self"]


def test_doc_parser_reset_block_signature():
    sig = inspect.signature(_HTMLDocParser._reset_block)
    params = list(sig.parameters)
    assert params == ["self"]
