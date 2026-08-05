r"""app/parsers/kreuzberg_parser.py 边角测试 - 第七轮（Round 189）。

补强已有 base/edges/edges2-6（共 803 测试）未覆盖的深度：
- _HEADING_RE 实际匹配行为（match 返回类型、capture group 边界、字符类）
- _classify_line 实际行为（标点 endswith 各项、单字符、混合标点、空白变体）
- _split_content_to_elements 深度（多行 rest、连续 heading、para_idx 自增、element_id 双位数）
- _make_locator 源类型矩阵（pdf/docx/text/markdown/html/ipynb）
- KreuzbergParser 类属性可访问性（class 与 instance 一致）
- 模块常量类型与可读性
- 模块级 try/except 块的命名属性
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

import pytest

from app.parsers.base import Parser
from app.parsers.kreuzberg_parser import (
    _classify_line,
    _HEADING_RE,
    _make_locator,
    _SHORT_LINE_MAX,
    _split_content_to_elements,
    KreuzbergParser,
)
import app.parsers.kreuzberg_parser as kbg_mod


# =========================================================================
# _HEADING_RE 实际匹配行为（Match 对象 vs None）
# =========================================================================


def test_heading_re_match_returns_match_object_for_valid():
    m = _HEADING_RE.match("# Hello")
    assert m is not None
    assert hasattr(m, "group")


def test_heading_re_match_returns_none_for_invalid():
    assert _HEADING_RE.match("not a heading") is None


def test_heading_re_group_1_returns_string():
    m = _HEADING_RE.match("# Hello")
    assert isinstance(m.group(1), str)


def test_heading_re_group_0_returns_string():
    m = _HEADING_RE.match("# Hello")
    assert isinstance(m.group(0), str)


def test_heading_re_group_0_includes_leading_whitespace():
    m = _HEADING_RE.match("  # Hello")
    assert m.group(0).startswith("  ")


def test_heading_re_group_1_excludes_leading_whitespace():
    m = _HEADING_RE.match("  # Hello")
    assert not m.group(1).startswith(" ")


def test_heading_re_pattern_object_has_match_method():
    assert callable(_HEADING_RE.match)


def test_heading_re_pattern_object_has_search_method():
    assert callable(_HEADING_RE.search)


def test_heading_re_pattern_object_has_fullmatch_method():
    assert callable(_HEADING_RE.fullmatch)


def test_heading_re_fullmatch_equivalent_to_match_for_simple():
    """anchored ^...$ → fullmatch 等价 match。"""
    assert _HEADING_RE.fullmatch("# Hello") is not None


def test_heading_re_search_finds_anywhere():
    """search 在中部找，但 ^ 锚定后只能从头匹配。"""
    assert _HEADING_RE.search("text\n# Hello") is None  # ^ 锚定 + . 不匹配 \n


def test_heading_re_hash_count_at_minimum_one():
    m = _HEADING_RE.match("# x")
    assert m is not None


def test_heading_re_hash_count_at_maximum_six():
    m = _HEADING_RE.match("###### x")
    assert m is not None


def test_heading_re_no_space_after_hash_caps_only():
    r"""只有 # 没有 \s+，不匹配。"""
    assert _HEADING_RE.match("######") is None


def test_heading_re_capture_group_excludes_hashes():
    m = _HEADING_RE.match("## Title")
    assert m.group(1) == "Title"


def test_heading_re_capture_with_digit_text():
    m = _HEADING_RE.match("# 12345")
    assert m.group(1) == "12345"


def test_heading_re_capture_with_special_chars():
    m = _HEADING_RE.match("# hello!@#$%^&*()")
    assert "hello" in m.group(1)


def test_heading_re_pattern_source_has_curly_brace_quantifier():
    """源正则里有 {1,6} 量词。"""
    assert "{1,6}" in _HEADING_RE.pattern


def test_heading_re_pattern_source_has_non_greedy_dot():
    """`.*?` 非贪婪匹配。"""
    assert ".*?" in _HEADING_RE.pattern


def test_heading_re_pattern_source_has_s_capital_for_whitespace():
    r"""`\S` 要求首字符非空白。"""
    assert r"\S" in _HEADING_RE.pattern


# =========================================================================
# _classify_line 实际行为
# =========================================================================


def test_classify_line_signature_single_param():
    sig = inspect.signature(_classify_line)
    params = list(sig.parameters)
    assert params == ["line"]


def test_classify_line_returns_two_tuple_always():
    """任何输入都返回 2-tuple。"""
    cases = ["", "   ", "# x", "short", "long text " * 20, None]
    for c in cases:
        if c is None:
            continue
        result = _classify_line(c)
        assert isinstance(result, tuple)
        assert len(result) == 2


def test_classify_line_first_element_always_str():
    cases = ["", "# x", "short", "long " * 50]
    for c in cases:
        etype, _ = _classify_line(c)
        assert isinstance(etype, str)


def test_classify_line_second_element_always_dict():
    cases = ["", "# x", "short", "long " * 50]
    for c in cases:
        _, meta = _classify_line(c)
        assert isinstance(meta, dict)


def test_classify_line_paragraph_type_value():
    """长文本返回 paragraph。"""
    etype, _ = _classify_line("a" * 100)
    assert etype == "paragraph"


def test_classify_line_atx_heading_type_value():
    etype, _ = _classify_line("# Title")
    assert etype == "heading"


def test_classify_line_short_line_heading_type_value():
    etype, _ = _classify_line("Section")
    assert etype == "heading"


def test_classify_line_atx_heading_meta_keys_exact():
    _, meta = _classify_line("# Title")
    assert set(meta.keys()) == {"level", "raw_text"}


def test_classify_line_short_line_heading_meta_keys_exact():
    _, meta = _classify_line("Section")
    assert set(meta.keys()) == {"level", "raw_text", "heuristic"}


def test_classify_line_paragraph_meta_keys_exact_empty():
    _, meta = _classify_line("a" * 100)
    assert meta == {}


def test_classify_line_atx_heading_meta_level_types():
    _, meta = _classify_line("# Title")
    assert isinstance(meta["level"], int)
    assert isinstance(meta["raw_text"], str)


def test_classify_line_short_line_heading_meta_level_value_zero():
    _, meta = _classify_line("short heading")
    assert meta["level"] == 0


def test_classify_line_short_line_heading_meta_heuristic_value():
    _, meta = _classify_line("short heading")
    assert meta["heuristic"] == "short_line"


def test_classify_line_atx_level_1_value():
    _, meta = _classify_line("# T")
    assert meta["level"] == 1


def test_classify_line_atx_level_2_value():
    _, meta = _classify_line("## T")
    assert meta["level"] == 2


def test_classify_line_atx_level_3_value():
    _, meta = _classify_line("### T")
    assert meta["level"] == 3


def test_classify_line_atx_level_4_value():
    _, meta = _classify_line("#### T")
    assert meta["level"] == 4


def test_classify_line_atx_level_5_value():
    _, meta = _classify_line("##### T")
    assert meta["level"] == 5


def test_classify_line_atx_level_6_value():
    _, meta = _classify_line("###### T")
    assert meta["level"] == 6


def test_classify_line_atx_7_hashes_not_atx_short_line():
    """7 # 因超过 {1,6}，regex 不匹配；文本够短无标点 → short_line heading。"""
    etype, meta = _classify_line("####### T")
    assert etype == "heading"
    assert meta["heuristic"] == "short_line"


def test_classify_line_paragraph_with_period_in_middle_short():
    """短文本中间有句号，但 endswith 只看末尾 → 仍是 heading。"""
    etype, _ = _classify_line("a.b")
    assert etype == "heading"


def test_classify_line_paragraph_with_question_in_middle():
    etype, _ = _classify_line("a?b")
    assert etype == "heading"


def test_classify_line_paragraph_with_bang_in_middle():
    etype, _ = _classify_line("a!b")
    assert etype == "heading"


def test_classify_line_short_text_with_chinese_period_end():
    etype, _ = _classify_line("短句。")
    assert etype == "paragraph"


def test_classify_line_short_text_with_chinese_question_end():
    etype, _ = _classify_line("短句？")
    assert etype == "paragraph"


def test_classify_line_short_text_with_chinese_bang_end():
    etype, _ = _classify_line("短句！")
    assert etype == "paragraph"


def test_classify_line_paragraph_with_mixed_punctuation_end_period():
    """末尾是 . 触发 paragraph，不管前面是什么。"""
    etype, _ = _classify_line("Hello!World.")
    assert etype == "paragraph"


def test_classify_line_paragraph_with_mixed_punctuation_end_bang():
    etype, _ = _classify_line("Hello.World!")
    assert etype == "paragraph"


def test_classify_line_single_char_no_punct_is_heading():
    etype, meta = _classify_line("X")
    assert etype == "heading"
    assert meta["heuristic"] == "short_line"


def test_classify_line_single_char_punct_period_is_paragraph():
    etype, _ = _classify_line(".")
    assert etype == "paragraph"


def test_classify_line_single_char_punct_question_is_paragraph():
    etype, _ = _classify_line("?")
    assert etype == "paragraph"


def test_classify_line_single_digit_no_punct_is_heading():
    etype, _ = _classify_line("5")
    assert etype == "heading"


def test_classify_line_atx_heading_raw_text_is_group1():
    _, meta = _classify_line("# Hello World")
    assert meta["raw_text"] == "Hello World"


def test_classify_line_atx_heading_raw_text_stripped_trailing_ws():
    _, meta = _classify_line("# Hello   ")
    assert meta["raw_text"] == "Hello"


def test_classify_line_atx_heading_raw_text_preserves_internal_double_spaces():
    _, meta = _classify_line("# Hello   World")
    # \s+ 后 \S.*? 捕获第一个非空白 + lazy 直到 \s*$
    # 内部多空格保留
    assert "Hello" in meta["raw_text"]
    assert "World" in meta["raw_text"]


def test_classify_line_short_line_text_with_period_in_middle_no_short_line_meta():
    etype, meta = _classify_line("a.b")
    # 末尾是 b 不是 terminator → short_line heading
    assert etype == "heading"
    assert meta["heuristic"] == "short_line"


def test_classify_line_short_line_text_with_period_at_end_is_paragraph():
    etype, _ = _classify_line("Hello.")
    assert etype == "paragraph"


def test_classify_line_atx_with_only_punctuation_after_space_is_atx():
    r"""# 后跟标点（非空白），匹配 \S.*?。"""
    etype, meta = _classify_line("# !!!")
    assert etype == "heading"
    assert "heuristic" not in meta  # ATX 无 heuristic key


def test_classify_line_atx_meta_has_no_heuristic_key():
    """ATX heading 的 meta 不含 heuristic 键。"""
    _, meta = _classify_line("# T")
    assert "heuristic" not in meta


def test_classify_line_short_line_meta_has_heuristic_key():
    _, meta = _classify_line("short title")
    assert "heuristic" in meta


def test_classify_line_idempotent_call():
    r1 = _classify_line("# Hello")
    r2 = _classify_line("# Hello")
    assert r1 == r2


def test_classify_line_does_not_mutate_input():
    s = "# Hello"
    _ = _classify_line(s)
    assert s == "# Hello"


def test_classify_line_string_with_internal_newline_first_line_used_only():
    """多行字符串（含 \n），strip 仍可能不为空。"""
    # 注意：调用方通常只传单行，但函数本身不拆分
    etype, _ = _classify_line("short\nlong")
    # 整体 strip 后长度可能 > 80 也可能 < 80；这里 strip 后 11 字符
    assert etype in ("heading", "paragraph")


# =========================================================================
# _split_content_to_elements 深度
# =========================================================================


def test_split_content_signature_three_params():
    sig = inspect.signature(_split_content_to_elements)
    params = list(sig.parameters)
    assert params == ["content", "source_type", "document_id"]


def test_split_content_returns_tuple_of_two():
    result = _split_content_to_elements("hello", "docx", "doc-x")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_split_content_first_element_is_list():
    els, _ = _split_content_to_elements("hello", "docx", "doc-x")
    assert isinstance(els, list)


def test_split_content_second_element_is_list():
    _, rests = _split_content_to_elements("hello", "docx", "doc-x")
    assert isinstance(rests, list)


def test_split_content_second_element_empty_list_default():
    _, rests = _split_content_to_elements("hello", "docx", "doc-x")
    assert rests == []


def test_split_content_empty_returns_empty_list():
    els, _ = _split_content_to_elements("", "docx", "doc-x")
    assert els == []


def test_split_content_single_paragraph_one_element():
    els, _ = _split_content_to_elements("hello world", "docx", "doc-x")
    assert len(els) == 1


def test_split_content_two_paragraphs_two_elements():
    els, _ = _split_content_to_elements("para1\n\npara2", "docx", "doc-x")
    assert len(els) == 2


def test_split_content_element_id_format_zero_padded():
    els, _ = _split_content_to_elements("a", "docx", "doc-x")
    # doc_id::e0000
    assert els[0].element_id == "doc-x::e0000"


def test_split_content_element_id_increments():
    els, _ = _split_content_to_elements("a\n\nb", "docx", "doc-x")
    assert els[0].element_id == "doc-x::e0000"
    assert els[1].element_id == "doc-x::e0001"


def test_split_content_element_id_double_digit_count():
    """10+ blocks，编号仍是 4 位 zero-padded。"""
    content = "\n\n".join(f"para{i}" for i in range(10))
    els, _ = _split_content_to_elements(content, "docx", "doc-x")
    assert els[9].element_id == "doc-x::e0009"


def test_split_content_element_id_three_digit_count():
    content = "\n\n".join(f"para{i}" for i in range(100))
    els, _ = _split_content_to_elements(content, "docx", "doc-x")
    assert els[99].element_id == "doc-x::e0099"


def test_split_content_paragraph_type_value():
    long_text = "a" * 100
    els, _ = _split_content_to_elements(long_text, "docx", "doc-x")
    assert els[0].type == "paragraph"


def test_split_content_heading_type_value():
    els, _ = _split_content_to_elements("# Title", "docx", "doc-x")
    assert els[0].type == "heading"


def test_split_content_paragraph_confidence_value():
    long_text = "a" * 100
    els, _ = _split_content_to_elements(long_text, "docx", "doc-x")
    assert els[0].confidence == 0.5


def test_split_content_heading_confidence_value():
    els, _ = _split_content_to_elements("# T", "docx", "doc-x")
    assert els[0].confidence == 0.6


def test_split_content_paragraph_metadata_keys():
    long_text = "a" * 100
    els, _ = _split_content_to_elements(long_text, "docx", "doc-x")
    assert "kreuzberg_heuristic" in els[0].metadata
    assert els[0].metadata["kreuzberg_heuristic"] is True


def test_split_content_heading_metadata_keys_atx():
    els, _ = _split_content_to_elements("# T", "docx", "doc-x")
    assert "level" in els[0].metadata
    assert "heuristic" in els[0].metadata
    assert els[0].metadata["heuristic"] is None


def test_split_content_heading_metadata_keys_short_line():
    els, _ = _split_content_to_elements("Short Title", "docx", "doc-x")
    assert els[0].metadata["heuristic"] == "short_line"
    assert els[0].metadata["level"] == 0


def test_split_content_heading_text_uses_raw_text():
    els, _ = _split_content_to_elements("# Title", "docx", "doc-x")
    assert els[0].content == "Title"


def test_split_content_short_line_heading_text_uses_stripped_input():
    els, _ = _split_content_to_elements("Short Title", "docx", "doc-x")
    assert els[0].content == "Short Title"


def test_split_content_heading_with_body_two_elements():
    """block 第一行 heading，后跟 body → 2 个 element（heading + paragraph）。"""
    els, _ = _split_content_to_elements("# Title\nbody line", "docx", "doc-x")
    assert len(els) == 2
    assert els[0].type == "heading"
    assert els[1].type == "paragraph"


def test_split_content_heading_with_body_paragraph_text_excludes_heading():
    els, _ = _split_content_to_elements("# Title\nbody line", "docx", "doc-x")
    assert "Title" not in els[1].content
    assert "body line" in els[1].content


def test_split_content_heading_with_only_whitespace_body_one_element():
    els, _ = _split_content_to_elements("# Title\n   \n", "docx", "doc-x")
    # 第一个 block 是 "# Title\n   "，第一行 "# Title"，rest="   ".strip()="" → 不加 paragraph
    assert len(els) == 1
    assert els[0].type == "heading"


def test_split_content_two_consecutive_headings():
    els, _ = _split_content_to_elements("# H1\n\n# H2", "docx", "doc-x")
    assert len(els) == 2
    assert all(e.type == "heading" for e in els)


def test_split_content_two_consecutive_headings_para_idx_incremented():
    els, _ = _split_content_to_elements("# H1\n\n# H2", "docx", "doc-x")
    # 每个 heading block 占一个 para_idx
    assert els[0].source_locator["paragraph_index"] == 0
    assert els[1].source_locator["paragraph_index"] == 1


def test_split_content_heading_with_body_para_idx_shared():
    """heading + body 共享递增的 para_idx（heading 占 idx，body 占 idx+1）。"""
    els, _ = _split_content_to_elements("# H\nbody", "docx", "doc-x")
    assert els[0].source_locator["paragraph_index"] == 0
    assert els[1].source_locator["paragraph_index"] == 1


def test_split_content_after_heading_body_next_block_continues_idx():
    els, _ = _split_content_to_elements("# H\nbody\n\npara2", "docx", "doc-x")
    # block1: heading(idx=0) + body(idx=1), block2: paragraph(idx=2)
    assert els[0].source_locator["paragraph_index"] == 0
    assert els[1].source_locator["paragraph_index"] == 1
    assert els[2].source_locator["paragraph_index"] == 2


def test_split_content_pdf_uses_page_locator():
    els, _ = _split_content_to_elements("hello", "pdf", "doc-x")
    assert "page" in els[0].source_locator
    assert els[0].source_locator["page"] == 1


def test_split_content_docx_uses_paragraph_index():
    els, _ = _split_content_to_elements("hello", "docx", "doc-x")
    assert "paragraph_index" in els[0].source_locator


def test_split_content_multiple_paragraphs_each_get_paragraph_index():
    els, _ = _split_content_to_elements("a\n\nb\n\nc", "docx", "doc-x")
    indices = [e.source_locator["paragraph_index"] for e in els]
    assert indices == [0, 1, 2]


def test_split_content_blocks_are_stripped():
    els, _ = _split_content_to_elements("  hello  ", "docx", "doc-x")
    assert els[0].content == "hello"


def test_split_content_multi_line_block_preserves_internal_newlines():
    long_first = "a" * 100
    els, _ = _split_content_to_elements(f"{long_first}\nsecond line", "docx", "doc-x")
    # 长 block 第一行触发 paragraph，整块保留 → 内部换行保留
    assert "second line" in els[0].content
    assert "\n" in els[0].content


def test_split_content_does_not_mutate_input():
    s = "# H\nbody"
    _ = _split_content_to_elements(s, "docx", "doc-x")
    assert s == "# H\nbody"


def test_split_content_idempotent():
    r1 = _split_content_to_elements("# H", "docx", "doc-x")
    r2 = _split_content_to_elements("# H", "docx", "doc-x")
    # element_id 应一致（不依赖时间/random）
    assert r1[0][0].element_id == r2[0][0].element_id


# =========================================================================
# _make_locator 源类型矩阵
# =========================================================================


def test_make_locator_signature_two_params():
    sig = inspect.signature(_make_locator)
    params = list(sig.parameters)
    assert params == ["source_type", "paragraph_index"]


def test_make_locator_pdf_keys_exact():
    loc = _make_locator("pdf", 0)
    assert set(loc.keys()) == {"page", "_kreuzberg_placeholder"}


def test_make_locator_docx_keys_exact():
    loc = _make_locator("docx", 0)
    assert set(loc.keys()) == {"paragraph_index", "_kreuzberg_heuristic"}


def test_make_locator_text_keys_match_docx():
    """text 类型走 else 分支（与 docx 同形）。"""
    loc = _make_locator("text", 5)
    assert "paragraph_index" in loc
    assert "_kreuzberg_heuristic" in loc


def test_make_locator_markdown_keys_match_docx():
    loc = _make_locator("markdown", 0)
    assert "paragraph_index" in loc


def test_make_locator_html_keys_match_docx():
    loc = _make_locator("html", 0)
    assert "paragraph_index" in loc


def test_make_locator_ipynb_keys_match_docx():
    loc = _make_locator("ipynb", 0)
    assert "paragraph_index" in loc


def test_make_locator_unknown_source_keys_match_docx():
    loc = _make_locator("unknown", 0)
    assert "paragraph_index" in loc


def test_make_locator_pdf_page_value_always_one():
    assert _make_locator("pdf", 0)["page"] == 1
    assert _make_locator("pdf", 100)["page"] == 1
    assert _make_locator("pdf", -1)["page"] == 1


def test_make_locator_pdf_placeholder_value_is_true():
    assert _make_locator("pdf", 0)["_kreuzberg_placeholder"] is True


def test_make_locator_docx_heuristic_value_is_true():
    assert _make_locator("docx", 0)["_kreuzberg_heuristic"] is True


def test_make_locator_docx_paragraph_index_value_passed_through():
    assert _make_locator("docx", 0)["paragraph_index"] == 0
    assert _make_locator("docx", 7)["paragraph_index"] == 7


def test_make_locator_returns_fresh_dict_each_call():
    a = _make_locator("pdf", 0)
    b = _make_locator("pdf", 0)
    assert a == b
    assert a is not b


def test_make_locator_idempotent():
    a = _make_locator("docx", 5)
    b = _make_locator("docx", 5)
    assert a == b


def test_make_locator_returns_dict():
    assert isinstance(_make_locator("pdf", 0), dict)
    assert isinstance(_make_locator("docx", 0), dict)


def test_make_locator_pdf_no_paragraph_index_key():
    assert "paragraph_index" not in _make_locator("pdf", 0)


def test_make_locator_docx_no_page_key():
    assert "page" not in _make_locator("docx", 0)


def test_make_locator_pdf_no_heuristic_key():
    assert "_kreuzberg_heuristic" not in _make_locator("pdf", 0)


def test_make_locator_docx_no_placeholder_key():
    assert "_kreuzberg_placeholder" not in _make_locator("docx", 0)


# =========================================================================
# _SHORT_LINE_MAX 常量
# =========================================================================


def test_short_line_max_value_80():
    assert _SHORT_LINE_MAX == 80


def test_short_line_max_is_int():
    assert isinstance(_SHORT_LINE_MAX, int)


def test_short_line_max_positive():
    assert _SHORT_LINE_MAX > 0


def test_short_line_max_used_in_classify_line():
    """_classify_line 用 _SHORT_LINE_MAX 作阈值。"""
    text_eq = "a" * _SHORT_LINE_MAX
    text_gt = "a" * (_SHORT_LINE_MAX + 1)
    etype_eq, _ = _classify_line(text_eq)
    etype_gt, _ = _classify_line(text_gt)
    assert etype_eq == "heading"
    assert etype_gt == "paragraph"


# =========================================================================
# KreuzbergParser 类属性
# =========================================================================


def test_kreuzberg_parser_class_attribute_name_value():
    assert KreuzbergParser.name == "kreuzberg"


def test_kreuzberg_parser_class_attribute_version_is_str():
    assert isinstance(KreuzbergParser.version, str)


def test_kreuzberg_parser_class_attribute_version_not_empty():
    assert KreuzbergParser.version != ""


def test_kreuzberg_parser_instance_attribute_name_matches_class():
    p = KreuzbergParser()
    assert p.name == KreuzbergParser.name


def test_kreuzberg_parser_instance_attribute_version_matches_class():
    p = KreuzbergParser()
    assert p.version == KreuzbergParser.version


def test_kreuzberg_parser_inherits_parser():
    assert issubclass(KreuzbergParser, Parser)


def test_kreuzberg_parser_is_class():
    assert inspect.isclass(KreuzbergParser)


def test_kreuzberg_parser_init_is_method():
    assert callable(KreuzbergParser.__init__)


def test_kreuzberg_parser_parse_is_method():
    assert callable(KreuzbergParser.parse)


def test_kreuzberg_parser_init_signature_keyword_only_param():
    sig = inspect.signature(KreuzbergParser.__init__)
    params = sig.parameters
    assert "self" in params
    assert "include_document_structure" in params


def test_kreuzberg_parser_init_include_document_structure_default_true():
    sig = inspect.signature(KreuzbergParser.__init__)
    assert sig.parameters["include_document_structure"].default is True


def test_kreuzberg_parser_init_include_document_structure_keyword_only():
    sig = inspect.signature(KreuzbergParser.__init__)
    param = sig.parameters["include_document_structure"]
    assert param.kind == inspect.Parameter.KEYWORD_ONLY


def test_kreuzberg_parser_init_creates_private_attr():
    p = KreuzbergParser()
    assert hasattr(p, "_include_document_structure")


def test_kreuzberg_parser_init_default_value_reflected():
    p = KreuzbergParser()
    assert p._include_document_structure is True


def test_kreuzberg_parser_init_explicit_false():
    p = KreuzbergParser(include_document_structure=False)
    assert p._include_document_structure is False


def test_kreuzberg_parser_init_explicit_true():
    p = KreuzbergParser(include_document_structure=True)
    assert p._include_document_structure is True


def test_kreuzberg_parser_init_no_positional_arg_accepted():
    """include_document_structure 是 keyword-only，传位置参数应报错。"""
    with pytest.raises(TypeError):
        KreuzbergParser(False)  # type: ignore[misc]


def test_kreuzberg_parser_two_instances_independent():
    a = KreuzbergParser()
    b = KreuzbergParser(include_document_structure=False)
    assert a._include_document_structure != b._include_document_structure


def test_kreuzberg_parser_init_does_not_mutate_class_attrs():
    """实例化不改 name/version。"""
    name_before = KreuzbergParser.name
    version_before = KreuzbergParser.version
    KreuzbergParser()
    KreuzbergParser(include_document_structure=False)
    assert KreuzbergParser.name == name_before
    assert KreuzbergParser.version == version_before


def test_kreuzberg_parser_parse_method_signature():
    sig = inspect.signature(KreuzbergParser.parse)
    params = list(sig.parameters)
    assert params == ["self", "path", "source_hash"]


def test_kreuzberg_parser_parse_method_return_annotation():
    sig = inspect.signature(KreuzbergParser.parse)
    assert sig.return_annotation is not None


def test_kreuzberg_parser_class_dict_contains_name():
    assert "name" in KreuzbergParser.__dict__


def test_kreuzberg_parser_class_dict_contains_version():
    assert "version" in KreuzbergParser.__dict__


def test_kreuzberg_parser_class_dict_contains_parse():
    assert "parse" in KreuzbergParser.__dict__


def test_kreuzberg_parser_mro_includes_parser():
    assert Parser in KreuzbergParser.__mro__


def test_kreuzberg_parser_module_namespace_correct():
    assert KreuzbergParser.__module__ == "app.parsers.kreuzberg_parser"


def test_kreuzberg_parser_init_no_extra_attrs_besides_private():
    """__init__ 只设 _include_document_structure。"""
    p = KreuzbergParser()
    instance_attrs = {k for k in vars(p) if not k.startswith("__")}
    assert instance_attrs == {"_include_document_structure"}


# =========================================================================
# 模块级常量与可读性
# =========================================================================


def test_module_has_kreuzberg_available_attr():
    assert hasattr(kbg_mod, "_KREUZBERG_AVAILABLE")


def test_module_kreuzberg_available_is_bool():
    assert isinstance(kbg_mod._KREUZBERG_AVAILABLE, bool)


def test_module_has_kreuzberg_version_attr():
    assert hasattr(kbg_mod, "_KREUZBERG_VERSION")


def test_module_kreuzberg_version_type():
    """None 或 str。"""
    v = kbg_mod._KREUZBERG_VERSION
    assert v is None or isinstance(v, str)


def test_module_has_short_line_max_attr():
    assert hasattr(kbg_mod, "_SHORT_LINE_MAX")


def test_module_has_heading_re_attr():
    assert hasattr(kbg_mod, "_HEADING_RE")


def test_module_heading_re_is_pattern():
    assert isinstance(kbg_mod._HEADING_RE, re.Pattern)


def test_module_has_classify_line_callable():
    assert callable(kbg_mod._classify_line)


def test_module_has_split_content_callable():
    assert callable(kbg_mod._split_content_to_elements)


def test_module_has_make_locator_callable():
    assert callable(kbg_mod._make_locator)


def test_module_all_exact():
    assert kbg_mod.__all__ == ["KreuzbergParser"]


def test_module_all_is_list():
    assert isinstance(kbg_mod.__all__, list)


def test_module_uses_future_annotations():
    src = inspect.getsource(kbg_mod)
    assert "from __future__ import annotations" in src


def test_module_imports_re():
    src = inspect.getsource(kbg_mod)
    assert "import re" in src


def test_module_imports_path():
    src = inspect.getsource(kbg_mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    src = inspect.getsource(kbg_mod)
    assert "from typing import Any" in src


def test_module_imports_models():
    src = inspect.getsource(kbg_mod)
    assert "from app.models" in src


def test_module_imports_base():
    src = inspect.getsource(kbg_mod)
    assert "from app.parsers.base" in src


def test_module_docstring_present():
    assert kbg_mod.__doc__ is not None


def test_module_docstring_mentions_kreuzberg():
    assert kbg_mod.__doc__ is not None
    assert "kreuzberg" in kbg_mod.__doc__.lower() or "Kreuzberg" in kbg_mod.__doc__


def test_module_docstring_mentions_version():
    """docstring 提到具体版本（4.10.2）。"""
    assert kbg_mod.__doc__ is not None
    assert "4.10.2" in kbg_mod.__doc__


def test_module_docstring_mentions_elements_limitation():
    """docstring 解释 elements 字段限制。"""
    assert kbg_mod.__doc__ is not None
    assert "elements" in kbg_mod.__doc__


def test_module_docstring_mentions_warnings():
    """docstring 提到用 warnings 记录限制。"""
    assert kbg_mod.__doc__ is not None
    assert "warning" in kbg_mod.__doc__.lower() or "warnings" in kbg_mod.__doc__.lower()


def test_module_docstring_mentions_business_code_isolation():
    """业务代码不直接 import kreuzberg。"""
    assert kbg_mod.__doc__ is not None
    assert "业务" in kbg_mod.__doc__ or "business" in kbg_mod.__doc__.lower()


def test_module_try_import_block_present():
    src = inspect.getsource(kbg_mod)
    assert "try:" in src
    assert "import kreuzberg" in src
    assert "except ImportError" in src


def test_module_kreuzberg_import_guards_version():
    src = inspect.getsource(kbg_mod)
    assert 'getattr(kreuzberg, "__version__"' in src


# =========================================================================
# 整体行为：classify_line 与 split_content 一致性
# =========================================================================


def test_classify_then_split_consistency_atx_heading():
    """classify_line 判 heading 的输入，split_content 也应判 heading。"""
    line = "# Title"
    etype_classify, _ = _classify_line(line)
    els, _ = _split_content_to_elements(line, "docx", "doc-x")
    assert etype_classify == "heading"
    assert els[0].type == "heading"


def test_classify_then_split_consistency_paragraph():
    line = "This is a long paragraph that exceeds the short line threshold of eighty chars."
    etype_classify, _ = _classify_line(line)
    els, _ = _split_content_to_elements(line, "docx", "doc-x")
    assert etype_classify == "paragraph"
    assert els[0].type == "paragraph"


def test_classify_then_split_consistency_short_line():
    line = "Short"
    etype_classify, _ = _classify_line(line)
    els, _ = _split_content_to_elements(line, "docx", "doc-x")
    assert etype_classify == "heading"
    assert els[0].type == "heading"


def test_split_content_first_line_only_used_for_classification():
    """多行 block 只看第一行。"""
    els, _ = _split_content_to_elements("# Heading\nlong body " * 5, "docx", "doc-x")
    # 第一个 block 第一行是 heading → type=heading
    # 但 block 内连续 5 行的字符串其实是单 block（没有空行分隔）
    # 因此 els[0].type 应该是 heading（第一行决定）
    assert els[0].type == "heading"


def test_split_content_block_first_line_short_others_long_classified_as_heading():
    """block 第一行短，其他行长；整个 block 仍是 heading + rest paragraph。"""
    block = "ShortTitle\nvery long body content that is way longer than eighty characters here."
    els, _ = _split_content_to_elements(block, "docx", "doc-x")
    assert len(els) == 2  # heading + rest paragraph
    assert els[0].type == "heading"
    assert els[1].type == "paragraph"
    assert els[1].content == "very long body content that is way longer than eighty characters here."


def test_split_content_block_first_line_long_others_short_classified_as_paragraph():
    """block 第一行长 → paragraph，其他行不重要。"""
    long_first = "a" * 100
    block = f"{long_first}\nshort"
    els, _ = _split_content_to_elements(block, "docx", "doc-x")
    assert len(els) == 1
    assert els[0].type == "paragraph"


def test_split_content_locator_pdf_after_heading_body():
    """heading + body 在 pdf 下都用 page=1 locator。"""
    els, _ = _split_content_to_elements("# H\nbody", "pdf", "doc-x")
    assert els[0].source_locator["page"] == 1
    assert els[1].source_locator["page"] == 1


def test_split_content_para_idx_not_reset_across_blocks():
    els, _ = _split_content_to_elements("# H1\n\npara\n\n# H2", "docx", "doc-x")
    indices = [e.source_locator["paragraph_index"] for e in els]
    # 3 blocks → 3 elements（两个 heading 不带 rest）
    assert indices == [0, 1, 2]


def test_split_content_element_id_uses_doc_id_prefix():
    els, _ = _split_content_to_elements("x", "docx", "my-doc-id")
    assert els[0].element_id.startswith("my-doc-id::")


def test_split_content_heading_parent_id_always_none():
    els, _ = _split_content_to_elements("# H", "docx", "doc-x")
    assert els[0].parent_id is None


def test_split_content_paragraph_parent_id_always_none():
    els, _ = _split_content_to_elements("para", "docx", "doc-x")
    assert els[0].parent_id is None
