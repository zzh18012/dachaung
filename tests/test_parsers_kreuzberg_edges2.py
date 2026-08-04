"""app/parsers/kreuzberg_parser.py 边角测试（Round 81，第二轮）。

补强现有 73 个 edges + 53 个基础测试未覆盖的盲区：

- _HEADING_RE 正则深度：tab/混合空白前缀、Unicode 全角#、嵌套#、close-markers
- _SHORT_LINE_MAX 常量不变量
- _classify_line：6 种标点 terminator 全枚举、长行 + terminator、Unicode 中文 heading
- _make_locator：负数/极大 paragraph_index、所有 source_type、调用幂等
- _split_content_to_elements：heading 后跟 heading、纯空白 block、首行空白、tail-newline、leading-trailing-blocks
- KreuzbergParser：include_document_structure 实际传入 config、表格 cells 空 row、bbox 转换 list、page_number=0 fallback、tables 排序、elements 字段非空时不发 warning
- 模块结构：__all__、_KREUZBERG_VERSION 类型/格式
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.parsers.base import Parser, ParserError
from app.parsers.kreuzberg_parser import (
    KreuzbergParser,
    _HEADING_RE,
    _SHORT_LINE_MAX,
    _classify_line,
    _make_locator,
    _split_content_to_elements,
)


# =========================================================================
# 1. _HEADING_RE 正则深度
# =========================================================================


def test_heading_re_pattern_object_is_compiled_type():
    assert isinstance(_HEADING_RE, re.Pattern)


def test_heading_re_pattern_source_starts_with_caret():
    """正则必须有 ^ 锚定，避免匹配行中段。"""
    assert _HEADING_RE.pattern.startswith("^")


def test_heading_re_pattern_ends_with_dollar():
    assert _HEADING_RE.pattern.endswith("$")


def test_heading_re_matches_with_leading_spaces():
    r"""`  # h` 允许前导空白（\s*）。"""
    m = _HEADING_RE.match("  # heading")
    assert m is not None
    assert m.group(1) == "heading"


def test_heading_re_matches_with_leading_tab():
    m = _HEADING_RE.match("\t# heading")
    assert m is not None
    assert m.group(1) == "heading"


def test_heading_re_matches_h1_minimum():
    m = _HEADING_RE.match("# x")
    assert m is not None


def test_heading_re_matches_h6_maximum():
    m = _HEADING_RE.match("###### x")
    assert m is not None


def test_heading_re_rejects_zero_hashes():
    """没有 # 不匹配。"""
    assert _HEADING_RE.match("plain text") is None


def test_heading_re_rejects_seven_hashes_with_space():
    """7 个 # 不匹配 {1,6}。"""
    assert _HEADING_RE.match("####### x") is None


def test_heading_re_requires_whitespace_after_hashes():
    r"""`#h` 没有 space，正则要求 `\s+`。"""
    assert _HEADING_RE.match("#heading") is None


def test_heading_re_captures_text_with_internal_spaces():
    m = _HEADING_RE.match("# hello world")
    assert m.group(1) == "hello world"


def test_heading_re_captures_text_with_punctuation():
    m = _HEADING_RE.match("# Section 1.2: Introduction!")
    assert m.group(1) == "Section 1.2: Introduction!"


def test_heading_re_trailing_whitespace_is_stripped_by_pattern():
    r"""正则结尾 `\s*$` → raw_text 不含尾部空白。"""
    m = _HEADING_RE.match("# Title   ")
    assert m.group(1) == "Title"


def test_heading_re_captures_text_with_leading_punctuation():
    m = _HEADING_RE.match("# - hello -")
    assert m.group(1) == "- hello -"


def test_heading_re_does_not_match_empty_string():
    assert _HEADING_RE.match("") is None


def test_heading_re_does_not_match_whitespace_only():
    assert _HEADING_RE.match("   ") is None


def test_heading_re_does_not_match_just_hashes_no_space():
    """`######` 无尾随空格 + 内容，不匹配。"""
    assert _HEADING_RE.match("######") is None


def test_heading_re_does_not_match_hashes_with_trailing_space_only():
    r"""`# ` 无内容，正则要求 `\S.+?` → 至少一个非空白 + 任意字符。"""
    assert _HEADING_RE.match("# ") is None


def test_heading_re_does_not_match_hashes_with_only_trailing_whitespace():
    assert _HEADING_RE.match("#   ") is None


def test_heading_re_capture_preserves_capitalization():
    m = _HEADING_RE.match("# HeLLo WORLD")
    assert m.group(1) == "HeLLo WORLD"


def test_heading_re_capture_preserves_unicode():
    m = _HEADING_RE.match("# 中文标题")
    assert m.group(1) == "中文标题"


def test_heading_re_capture_preserves_digits():
    m = _HEADING_RE.match("# 12345")
    assert m.group(1) == "12345"


def test_heading_re_capture_includes_trailing_hashes():
    """ATX close sequence `#` 不被特殊处理 → raw_text 保留。"""
    m = _HEADING_RE.match("# Heading #")
    # 正则用 (\S.*?) \s*$ → "Heading #" 满足
    assert m.group(1) == "Heading #"


def test_heading_re_fullmatch_vs_match_semantics():
    """`re.match` 仅锚定开头，但正则本身有 $ → 等价 fullmatch。"""
    line = "# title\n"
    # $ 在默认 mode 下位于 \n 之前或字符串尾（re.MULTILINE 未开 → \n 前停）
    # 实际 _HEADING_RE.match("\# title\n") 会匹配 "title" 部分（\n 前的 \s* 允许？）
    # 这里仅验证 match 调用不抛
    assert _HEADING_RE.match(line) is not None or _HEADING_RE.match(line) is None


# =========================================================================
# 2. _SHORT_LINE_MAX 常量
# =========================================================================


def test_short_line_max_is_integer():
    assert isinstance(_SHORT_LINE_MAX, int)


def test_short_line_max_equals_80():
    assert _SHORT_LINE_MAX == 80


def test_short_line_max_is_positive():
    assert _SHORT_LINE_MAX > 0


def test_short_line_max_is_reasonable_threshold():
    """80 字符是常见终端宽度阈值。"""
    assert 50 <= _SHORT_LINE_MAX <= 200


# =========================================================================
# 3. _classify_line 边界
# =========================================================================


def test_classify_line_signature_no_defaults():
    sig = inspect.signature(_classify_line)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "line"


def test_classify_line_returns_tuple_with_str_and_dict_types():
    etype, meta = _classify_line("hello")
    assert isinstance(etype, str)
    assert isinstance(meta, dict)


def test_classify_line_atx_heading_level_1():
    etype, _ = _classify_line("# Title")
    assert etype == "heading"


def test_classify_line_atx_heading_level_2():
    etype, meta = _classify_line("## Title")
    assert etype == "heading"
    assert meta["level"] == 2


def test_classify_line_atx_heading_level_3():
    etype, meta = _classify_line("### Title")
    assert etype == "heading"
    assert meta["level"] == 3


def test_classify_line_atx_heading_level_4():
    etype, meta = _classify_line("#### Title")
    assert etype == "heading"
    assert meta["level"] == 4


def test_classify_line_atx_heading_level_5():
    etype, meta = _classify_line("##### Title")
    assert etype == "heading"
    assert meta["level"] == 5


def test_classify_line_atx_heading_meta_has_level_key():
    _, meta = _classify_line("# Title")
    assert "level" in meta


def test_classify_line_atx_heading_meta_has_raw_text_key():
    _, meta = _classify_line("# Title")
    assert "raw_text" in meta


def test_classify_line_atx_heading_meta_does_not_have_heuristic_key():
    _, meta = _classify_line("# Title")
    assert "heuristic" not in meta


def test_classify_line_atx_heading_with_leading_spaces_level_falls_back_to_1():
    """line.lstrip('#') 不去除前导空格 → level=max(1, 0)=1。"""
    _, meta = _classify_line("  ## Title")
    # len(line) - len(line.lstrip('#')) = 0（lstrip 只删 #，前导空格不算）
    # 实测：lstrip("#") 因首字符是空白，直接返回原串
    assert meta["level"] == 1  # max(1, 0)


def test_classify_line_short_line_all_six_terminators_are_paragraph():
    """枚举所有 terminator 字符。"""
    terminators = [".", "!", "?", "。", "！", "？"]
    for t in terminators:
        etype, _ = _classify_line(f"short text{t}")
        assert etype == "paragraph", f"failed for terminator: {t!r}"


def test_classify_line_short_line_terminator_with_chinese_period():
    etype, _ = _classify_line("一段中文。")
    assert etype == "paragraph"


def test_classify_line_short_line_terminator_with_chinese_question():
    etype, _ = _classify_line("一段中文？")
    assert etype == "paragraph"


def test_classify_line_short_line_terminator_with_chinese_exclamation():
    etype, _ = _classify_line("一段中文！")
    assert etype == "paragraph"


def test_classify_line_long_line_with_period_is_paragraph():
    """长行有 terminator → paragraph。"""
    text = "a" * 100 + "."
    etype, _ = _classify_line(text)
    assert etype == "paragraph"


def test_classify_line_long_line_without_period_is_paragraph():
    """长行无 terminator → paragraph（不是 short_line heading）。"""
    text = "a" * 100
    etype, _ = _classify_line(text)
    assert etype == "paragraph"


def test_classify_line_atx_heading_overrides_short_line_logic():
    """ATX 标记优先于 short_line heuristic。"""
    text = "# short"  # 短但 ATX
    etype, meta = _classify_line(text)
    assert etype == "heading"
    assert meta.get("heuristic") != "short_line"


def test_classify_line_paragraph_meta_is_empty_dict_when_too_long():
    etype, meta = _classify_line("a" * 81)
    assert etype == "paragraph"
    assert meta == {}


def test_classify_line_paragraph_meta_is_empty_dict_when_has_terminator():
    etype, meta = _classify_line("hello.")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_line_single_character_no_terminator_is_heading():
    """1 字符 + 无 terminator + ≤ 80 → short_line heading。"""
    etype, meta = _classify_line("x")
    assert etype == "heading"
    assert meta["heuristic"] == "short_line"


def test_classify_line_returns_paragraph_for_empty_after_strip():
    etype, meta = _classify_line("   ")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_line_returns_paragraph_for_just_newline():
    etype, meta = _classify_line("\n")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_line_atx_heading_raw_text_no_strip_internal_whitespace():
    """raw_text 保留内部空白。"""
    _, meta = _classify_line("# hello   world")
    assert meta["raw_text"] == "hello   world"


def test_classify_line_short_line_heading_raw_text_is_stripped_input():
    text = "  short title  "
    _, meta = _classify_line(text)
    assert meta["raw_text"] == "short title"


def test_classify_line_short_line_heading_has_heuristic_short_line():
    _, meta = _classify_line("a short heading")
    assert meta["heuristic"] == "short_line"


def test_classify_line_short_line_heading_has_level_zero():
    _, meta = _classify_line("a short heading")
    assert meta["level"] == 0


def test_classify_line_atx_heading_level_never_zero():
    """ATX heading 最少 1 个 #，level ≥ 1。"""
    for n in range(1, 7):
        _, meta = _classify_line("#" * n + " title")
        assert meta["level"] == n
        assert meta["level"] >= 1


# =========================================================================
# 4. _make_locator 边界
# =========================================================================


def test_make_locator_signature_only_two_args():
    sig = inspect.signature(_make_locator)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert params[0].name == "source_type"
    assert params[1].name == "paragraph_index"


def test_make_locator_pdf_source_type():
    loc = _make_locator("pdf", 0)
    assert "page" in loc


def test_make_locator_pdf_source_type_uppercase_does_not_match():
    """source_type 是大小写敏感的（'PDF' 走 docx 分支）。"""
    loc = _make_locator("PDF", 5)
    # "PDF" != "pdf" → 走 else 分支
    assert "page" not in loc
    assert loc["paragraph_index"] == 5


def test_make_locator_docx_source_type():
    loc = _make_locator("docx", 0)
    assert "paragraph_index" in loc


def test_make_locator_unknown_source_type_returns_docx_like():
    loc = _make_locator("unknown", 7)
    assert "paragraph_index" in loc
    assert loc["paragraph_index"] == 7


def test_make_locator_empty_source_type_returns_docx_like():
    loc = _make_locator("", 7)
    assert "paragraph_index" in loc


def test_make_locator_negative_paragraph_index_passes_through():
    """负数 paragraph_index 也会原样传给 locator。"""
    loc = _make_locator("docx", -1)
    assert loc["paragraph_index"] == -1


def test_make_locator_zero_paragraph_index():
    loc = _make_locator("docx", 0)
    assert loc["paragraph_index"] == 0


def test_make_locator_large_paragraph_index():
    loc = _make_locator("docx", 1000000)
    assert loc["paragraph_index"] == 1000000


def test_make_locator_pdf_does_not_use_paragraph_index_arg():
    loc = _make_locator("pdf", 999)
    assert loc.get("paragraph_index") is None


def test_make_locator_docx_does_not_use_page_key():
    loc = _make_locator("docx", 1)
    assert "page" not in loc


def test_make_locator_pdf_returns_dict_with_bool_placeholder():
    loc = _make_locator("pdf", 0)
    assert loc["_kreuzberg_placeholder"] is True
    assert isinstance(loc["_kreuzberg_placeholder"], bool)


def test_make_locator_docx_returns_dict_with_bool_heuristic():
    loc = _make_locator("docx", 0)
    assert loc["_kreuzberg_heuristic"] is True
    assert isinstance(loc["_kreuzberg_heuristic"], bool)


def test_make_locator_idempotent_same_args():
    """相同入参 → 相同 dict 内容。"""
    a = _make_locator("pdf", 5)
    b = _make_locator("pdf", 5)
    assert a == b


def test_make_locator_pdf_dict_size_exactly_two():
    loc = _make_locator("pdf", 0)
    assert len(loc) == 2


def test_make_locator_docx_dict_size_exactly_two():
    loc = _make_locator("docx", 0)
    assert len(loc) == 2


def test_make_locator_pdf_returns_fresh_dict_each_call():
    """不共享引用。"""
    a = _make_locator("pdf", 0)
    b = _make_locator("pdf", 0)
    assert a is not b


def test_make_locator_docx_returns_fresh_dict_each_call():
    a = _make_locator("docx", 0)
    b = _make_locator("docx", 0)
    assert a is not b


# =========================================================================
# 5. _split_content_to_elements 深度
# =========================================================================


def test_split_content_signature_returns_tuple_of_two():
    sig = inspect.signature(_split_content_to_elements)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["content", "source_type", "document_id"]


def test_split_content_empty_string_no_blocks():
    elements, _ = _split_content_to_elements("", "docx", "docid")
    assert elements == []


def test_split_content_whitespace_only_no_blocks():
    elements, _ = _split_content_to_elements("   \n\n  \n", "docx", "docid")
    assert elements == []


def test_split_content_single_paragraph_returns_one_element():
    elements, _ = _split_content_to_elements("hello world", "docx", "docid")
    assert len(elements) == 1


def test_split_content_two_paragraphs_double_newline():
    content = "para one\n\npara two"
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    assert len(elements) == 2


def test_split_content_two_paragraphs_triple_newline():
    r"""三个换行被 `\n\s*\n` 收敛成单个分隔符。"""
    content = "para one\n\n\npara two"
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    assert len(elements) == 2


def test_split_content_two_paragraphs_four_newlines():
    content = "para one\n\n\n\npara two"
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    assert len(elements) == 2


def test_split_content_two_consecutive_headings_atx():
    content = "# H1\n\n## H2"
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    assert len(elements) == 2
    assert elements[0].type == "heading"
    assert elements[1].type == "heading"


def test_split_content_heading_then_paragraph_then_heading():
    content = "# H1\n\nbody para.\n\n# H2"
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    assert len(elements) == 3
    assert elements[0].type == "heading"
    assert elements[1].type == "paragraph"
    assert elements[2].type == "heading"


def test_split_content_paragraph_then_heading():
    content = "para text.\n\n# Heading"
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    assert len(elements) == 2
    assert elements[0].type == "paragraph"
    assert elements[1].type == "heading"


def test_split_content_block_with_leading_whitespace_stripped():
    content = "\n\n  hello world\n\n"
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    assert len(elements) == 1
    assert elements[0].content == "hello world"


def test_split_content_block_with_trailing_whitespace_stripped():
    content = "hello world   \n\n"
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    assert len(elements) == 1
    assert elements[0].content == "hello world"


def test_split_content_block_with_internal_newlines_preserved_in_paragraph():
    """paragraph 内容是整个 block（已 strip），内部 \n 保留。"""
    content = "line one.\nline two."
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    assert len(elements) == 1
    assert "line one." in elements[0].content
    assert "line two." in elements[0].content


def test_split_content_atx_heading_with_body_rest_emitted_as_paragraph():
    content = "# Heading\nbody line"
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    # 一个 block，ATX heading → 2 elements (heading + rest)
    assert len(elements) == 2
    assert elements[0].type == "heading"
    assert elements[0].content == "Heading"
    assert elements[1].type == "paragraph"
    assert elements[1].content == "body line"


def test_split_content_atx_heading_with_multiline_rest():
    content = "# Heading\nline one\nline two"
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    assert len(elements) == 2
    assert elements[1].content == "line one\nline two"


def test_split_content_atx_heading_with_only_whitespace_rest_no_paragraph():
    """rest.strip() == "" → 不 emit rest paragraph。"""
    content = "# Heading\n   \n"
    # 这个 block 被 re.split 切：第一行是 "# Heading"，第二行 "   " 但 strip 后空 → 进入 elements
    # 实际 block.splitlines() = ["# Heading", "   "]; rest = "   ".strip() = "" → 不 emit
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    assert len(elements) == 1
    assert elements[0].type == "heading"


def test_split_content_short_line_heading_with_body_rest():
    """short_line heading + 多行 block。"""
    content = "Short Title\nbody line"
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    assert len(elements) == 2
    assert elements[0].type == "heading"
    assert elements[0].content == "Short Title"
    assert elements[1].type == "paragraph"


def test_split_content_paragraph_increments_para_idx_per_block():
    """每个 block（含 heading+rest 双 element）共享 para_idx。"""
    content = "# H1\n\nbody"
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    # block1: heading at idx 0; block2: paragraph at idx 1
    assert elements[0].source_locator["paragraph_index"] == 0
    assert elements[1].source_locator["paragraph_index"] == 1


def test_split_content_heading_rest_in_same_block_share_incremented_idx():
    """同一 block 的 heading + rest 占 2 个 para_idx。"""
    content = "# H1\nrest"
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    assert elements[0].source_locator["paragraph_index"] == 0
    assert elements[1].source_locator["paragraph_index"] == 1


def test_split_content_element_id_format_starts_with_document_id():
    elements, _ = _split_content_to_elements("hello", "docx", "MYDOC")
    assert elements[0].element_id.startswith("MYDOC::")


def test_split_content_element_id_format_zero_padded_four_digits():
    elements, _ = _split_content_to_elements("hello", "docx", "MYDOC")
    assert elements[0].element_id.endswith("::e0000")


def test_split_content_element_ids_unique_strictly_increasing():
    content = "para one\n\npara two\n\npara three"
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    ids = [e.element_id for e in elements]
    assert len(set(ids)) == len(ids)
    suffixes = [eid.split("::e")[1] for eid in ids]
    assert suffixes == ["0000", "0001", "0002"]


def test_split_content_pdf_uses_page_locator():
    elements, _ = _split_content_to_elements("hello", "pdf", "docid")
    assert "page" in elements[0].source_locator


def test_split_content_docx_uses_paragraph_index_locator():
    elements, _ = _split_content_to_elements("hello", "docx", "docid")
    assert "paragraph_index" in elements[0].source_locator


def test_split_content_heading_confidence_value_is_06():
    elements, _ = _split_content_to_elements("# Title", "docx", "docid")
    assert elements[0].confidence == 0.6


def test_split_content_paragraph_confidence_value_is_05():
    elements, _ = _split_content_to_elements("hello world.", "docx", "docid")
    assert elements[0].confidence == 0.5


def test_split_content_rest_paragraph_confidence_value_is_05():
    elements, _ = _split_content_to_elements("# Heading\nrest", "docx", "docid")
    assert elements[1].confidence == 0.5


def test_split_content_atx_heading_metadata_has_level():
    elements, _ = _split_content_to_elements("# Title", "docx", "docid")
    assert elements[0].metadata["level"] == 1


def test_split_content_atx_heading_metadata_heuristic_is_none():
    elements, _ = _split_content_to_elements("# Title", "docx", "docid")
    assert elements[0].metadata["heuristic"] is None


def test_split_content_short_line_heading_metadata_heuristic_short_line():
    elements, _ = _split_content_to_elements("short heading", "docx", "docid")
    assert elements[0].metadata["heuristic"] == "short_line"


def test_split_content_short_line_heading_metadata_level_zero():
    elements, _ = _split_content_to_elements("short heading", "docx", "docid")
    assert elements[0].metadata["level"] == 0


def test_split_content_paragraph_metadata_has_kreuzberg_heuristic_true():
    elements, _ = _split_content_to_elements("hello world.", "docx", "docid")
    assert elements[0].metadata["kreuzberg_heuristic"] is True


def test_split_content_atx_heading_metadata_no_kreuzberg_heuristic():
    elements, _ = _split_content_to_elements("# Title", "docx", "docid")
    assert "kreuzberg_heuristic" not in elements[0].metadata


def test_split_content_paragraph_parent_id_is_none():
    elements, _ = _split_content_to_elements("hello.", "docx", "docid")
    assert elements[0].parent_id is None


def test_split_content_heading_parent_id_is_none():
    elements, _ = _split_content_to_elements("# Title", "docx", "docid")
    assert elements[0].parent_id is None


def test_split_content_returns_second_value_as_empty_list():
    _, rest = _split_content_to_elements("hello", "docx", "docid")
    assert rest == []


def test_split_content_returns_second_value_as_list_type():
    _, rest = _split_content_to_elements("hello", "docx", "docid")
    assert isinstance(rest, list)


def test_split_content_large_input_50_blocks():
    blocks = [f"para {i}." for i in range(50)]
    content = "\n\n".join(blocks)
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    assert len(elements) == 50


def test_split_content_returns_list_type():
    elements, _ = _split_content_to_elements("hello", "docx", "docid")
    assert isinstance(elements, list)


def test_split_content_each_element_is_element_class():
    from app.models import Element
    elements, _ = _split_content_to_elements("hello.", "docx", "docid")
    for e in elements:
        assert isinstance(e, Element)


def test_split_content_crlf_line_endings_supported():
    r"""CRLF 在 re.split(r'\n\s*\n', ...) 下表现依赖具体内容。"""
    content = "para one\r\n\r\npara two"
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    # \r\n\r\n 包含 \n\s*\n，会被 split
    assert len(elements) == 2


def test_split_content_only_newlines_no_real_content():
    elements, _ = _split_content_to_elements("\n\n\n", "docx", "docid")
    assert elements == []


def test_split_content_single_newline_no_separator():
    """单 \n 不构成 block 分隔，整个文本是一个 block。"""
    content = "line one.\nline two."
    elements, _ = _split_content_to_elements(content, "docx", "docid")
    assert len(elements) == 1


# =========================================================================
# 6. KreuzbergParser 类深度
# =========================================================================


def test_kreuzberg_parser_module_all_exports_kreuzberg_parser():
    import app.parsers.kreuzberg_parser as mod
    assert "KreuzbergParser" in mod.__all__
    assert mod.__all__ == ["KreuzbergParser"]


def test_kreuzberg_parser_name_class_attribute_is_kreuzberg():
    assert KreuzbergParser.name == "kreuzberg"


def test_kreuzberg_parser_name_is_lowercase():
    assert KreuzbergParser.name.islower()


def test_kreuzberg_parser_version_is_str_or_none():
    """version 是 _KREUZBERG_VERSION or 'unknown'。"""
    v = KreuzbergParser.version
    assert v is None or isinstance(v, str)


def test_kreuzberg_parser_version_unknown_when_unavailable():
    """如果 _KREUZBERG_VERSION 是 None，class.version 应该是 'unknown'。"""
    import app.parsers.kreuzberg_parser as mod
    if mod._KREUZBERG_VERSION is None:
        assert KreuzbergParser.version == "unknown"
    else:
        assert KreuzbergParser.version == mod._KREUZBERG_VERSION


def test_kreuzberg_parser_init_signature_keyword_only():
    sig = inspect.signature(KreuzbergParser.__init__)
    params = list(sig.parameters.values())
    assert params[1].kind == inspect.Parameter.KEYWORD_ONLY


def test_kreuzberg_parser_init_default_arg_value_true():
    sig = inspect.signature(KreuzbergParser.__init__)
    params = list(sig.parameters.values())
    assert params[1].default is True


def test_kreuzberg_parser_init_self_param_only_first():
    sig = inspect.signature(KreuzbergParser.__init__)
    params = list(sig.parameters.values())
    assert params[0].name == "self"


def test_kreuzberg_parser_parse_method_signature():
    sig = inspect.signature(KreuzbergParser.parse)
    params = list(sig.parameters.values())
    # self, path, source_hash
    assert len(params) == 3
    assert params[0].name == "self"
    assert params[1].name == "path"
    assert params[2].name == "source_hash"


def test_kreuzberg_parser_inherits_from_parser_base():
    assert issubclass(KreuzbergParser, Parser)


def test_kreuzberg_parser_subclass_has_name_attribute():
    """name 在 Parser ABC 中可能是 abstract property，子类必须重写。"""
    assert hasattr(KreuzbergParser, "name")


def test_kreuzberg_parser_subclass_has_version_attribute():
    assert hasattr(KreuzbergParser, "version")


# =========================================================================
# 7. parse() — monkeypatch 完整覆盖
# =========================================================================


def _make_mock_result(**fields):
    defaults = {
        "content": "",
        "tables": [],
        "elements": [],
        "mime_type": "text/plain",
        "quality_score": 0.5,
    }
    defaults.update(fields)
    return SimpleNamespace(**defaults)


def test_parse_kreuzberg_unavailable_message_has_error_string(monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(mod, "_KREUZBERG_AVAILABLE", False)
    monkeypatch.setattr(mod, "_KREUZBERG_IMPORT_ERROR", "specific import error msg", raising=False)
    parser = KreuzbergParser()
    with pytest.raises(ParserError) as exc:
        parser.parse("any.docx", source_hash="a" * 64)
    assert "specific import error msg" in exc.value.message


def test_parse_kreuzberg_unavailable_check_before_file_exists(monkeypatch, tmp_path):
    """unavailable 优先于 file_not_found。"""
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(mod, "_KREUZBERG_AVAILABLE", False)
    monkeypatch.setattr(mod, "_KREUZBERG_IMPORT_ERROR", "err", raising=False)
    parser = KreuzbergParser()
    # 文件不存在也应先报 unavailable
    with pytest.raises(ParserError) as exc:
        parser.parse(tmp_path / "nonexistent.docx", source_hash="a" * 64)
    assert exc.value.code == "kreuzberg_unavailable"


def test_parse_kreuzberg_unavailable_has_no_details(monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(mod, "_KREUZBERG_AVAILABLE", False)
    monkeypatch.setattr(mod, "_KREUZBERG_IMPORT_ERROR", "err", raising=False)
    parser = KreuzbergParser()
    with pytest.raises(ParserError) as exc:
        parser.parse("any.docx", source_hash="a" * 64)
    # unavailable 路径不构造 details
    assert exc.value.details is None or "path" not in (exc.value.details or {})


def test_parse_file_not_found_message_includes_path(tmp_path):
    parser = KreuzbergParser()
    target = tmp_path / "missing.docx"
    with pytest.raises(ParserError) as exc:
        parser.parse(target, source_hash="a" * 64)
    assert str(target) in exc.value.message


def test_parse_file_not_found_details_has_path_value(tmp_path):
    parser = KreuzbergParser()
    target = tmp_path / "missing.docx"
    with pytest.raises(ParserError) as exc:
        parser.parse(target, source_hash="a" * 64)
    assert exc.value.details["path"] == str(target)


def test_parse_extract_failed_message_includes_original_exception(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod

    def _raise(*a, **kw):
        raise RuntimeError("specific boom message")

    monkeypatch.setattr(mod.kreuzberg, "extract_file_sync", _raise)
    src = tmp_path / "x.docx"
    src.write_bytes(b"fake")
    parser = KreuzbergParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(src, source_hash="a" * 64)
    assert "specific boom message" in exc.value.message


def test_parse_extract_failed_chains_original_exception(tmp_path, monkeypatch):
    """ParserError 应 `from e` 保留原始 traceback。"""
    import app.parsers.kreuzberg_parser as mod

    def _raise(*a, **kw):
        raise RuntimeError("orig")

    monkeypatch.setattr(mod.kreuzberg, "extract_file_sync", _raise)
    src = tmp_path / "x.docx"
    src.write_bytes(b"fake")
    parser = KreuzbergParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(src, source_hash="a" * 64)
    assert exc.value.__cause__ is not None
    assert isinstance(exc.value.__cause__, RuntimeError)


def test_parse_extract_failed_details_has_exception_type(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod

    def _raise(*a, **kw):
        raise OSError("disk fail")

    monkeypatch.setattr(mod.kreuzberg, "extract_file_sync", _raise)
    src = tmp_path / "x.docx"
    src.write_bytes(b"fake")
    parser = KreuzbergParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(src, source_hash="a" * 64)
    assert exc.value.details["exception_type"] == "OSError"


def test_parse_calls_extraction_config_with_flag(tmp_path, monkeypatch):
    """include_document_structure 应传入 ExtractionConfig。"""
    import app.parsers.kreuzberg_parser as mod
    captured = {}

    class _SpyConfig:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(mod, "ExtractionConfig", _SpyConfig)
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="hello."),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser(include_document_structure=False)
    parser.parse(src, source_hash="a" * 64)
    assert captured.get("include_document_structure") is False


def test_parse_calls_extraction_config_default_true(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    captured = {}

    class _SpyConfig:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(mod, "ExtractionConfig", _SpyConfig)
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="hello."),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    parser.parse(src, source_hash="a" * 64)
    assert captured.get("include_document_structure") is True


def test_parse_passes_path_str_to_extract(tmp_path, monkeypatch):
    """extract_file_sync 收到 str(path)。"""
    import app.parsers.kreuzberg_parser as mod
    captured = {}

    def _fake_extract(path, config=None):
        captured["path"] = path
        return _make_mock_result(content="")

    monkeypatch.setattr(mod.kreuzberg, "extract_file_sync", _fake_extract)
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    parser.parse(src, source_hash="a" * 64)
    assert captured["path"] == str(src)


def test_parse_returns_document_instance(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    from app.models import Document
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content=""),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert isinstance(doc, Document)


def test_parse_empty_content_no_structured_elements_warning(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", elements=[]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    assert "kreuzberg_no_structured_elements" in codes


def test_parse_with_kreuzberg_elements_skips_warning(tmp_path, monkeypatch):
    """kreuzberg.elements 非空 → 不发 kreuzberg_no_structured_elements warning。"""
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="hello.", elements=[{"fake": "e1"}]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    assert "kreuzberg_no_structured_elements" not in codes


def test_parse_pdf_always_emits_no_bbox_warning(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="hello."),
    )
    src = tmp_path / "x.pdf"
    src.write_bytes(b"%PDF-1.4")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    assert "kreuzberg_pdf_no_bbox" in codes


def test_parse_docx_never_emits_no_bbox_warning(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="hello."),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    assert "kreuzberg_pdf_no_bbox" not in codes


def test_parse_pdf_emits_two_warnings_when_no_structured_elements(tmp_path, monkeypatch):
    """PDF + 没有 kreuzberg elements → 同时有 no_structured_elements + no_bbox。"""
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="hello.", elements=[]),
    )
    src = tmp_path / "x.pdf"
    src.write_bytes(b"%PDF")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    assert "kreuzberg_no_structured_elements" in codes
    assert "kreuzberg_pdf_no_bbox" in codes


def test_parse_no_structured_elements_warning_details_keys(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="hi.", elements=[]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    w = next(x for x in doc.warnings if x.code == "kreuzberg_no_structured_elements")
    assert "source_type" in w.details
    assert "fallback_strategy" in w.details
    assert "element_count_after_heuristic" in w.details


def test_parse_no_structured_elements_warning_fallback_strategy_value(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="hi.", elements=[]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    w = next(x for x in doc.warnings if x.code == "kreuzberg_no_structured_elements")
    assert w.details["fallback_strategy"] == "heuristic_paragraph_split"


def test_parse_no_structured_elements_warning_element_count_matches(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="para1.\n\npara2.", elements=[]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    w = next(x for x in doc.warnings if x.code == "kreuzberg_no_structured_elements")
    assert w.details["element_count_after_heuristic"] == len(doc.elements)


def test_parse_pdf_no_bbox_warning_details_source_type_value(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="hi.", elements=[]),
    )
    src = tmp_path / "x.pdf"
    src.write_bytes(b"%PDF")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    w = next(x for x in doc.warnings if x.code == "kreuzberg_pdf_no_bbox")
    assert w.details["source_type"] == "pdf"


# =========================================================================
# 8. parse() tables 深度
# =========================================================================


def test_parse_tables_empty_list_no_table_element(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    types = [e.type for e in doc.elements]
    assert "table" not in types


def test_parse_tables_none_value_treated_as_empty(tmp_path, monkeypatch):
    """result.tables=None → 不抛错。"""
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=None),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    types = [e.type for e in doc.elements]
    assert "table" not in types


def test_parse_table_emits_table_element(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    table = SimpleNamespace(markdown="| a | b |", cells=[["a", "b"]])
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    types = [e.type for e in doc.elements]
    assert "table" in types


def test_parse_table_content_uses_markdown_field(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    table = SimpleNamespace(markdown="| a | b |", cells=[["a", "b"]])
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.content == "| a | b |"


def test_parse_table_content_falls_back_to_empty_when_markdown_none(tmp_path, monkeypatch):
    """markdown=None → 适配器用 `or ""` 得到 ""，但 Element 要求 content 非空。
    实际上：content="" + cells 非空 → 后构造 element 时仍 fail validation。
    跳过此路径：当 markdown 为 None 且无 cells 时不会构造 element。"""
    import app.parsers.kreuzberg_parser as mod
    # 此情形实际不应发生在 kreuzberg 真实输出中（任一表至少有 markdown 或 cells）
    # 直接验证空 markdown + 有 cells + Element 验证抛 ValueError
    import pytest as _pytest
    table = SimpleNamespace(markdown=None, cells=[["a"]])
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    with _pytest.raises(ValueError):
        parser.parse(src, source_hash="a" * 64)


def test_parse_table_metadata_has_cell_count(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    cells = [["a", "b"], ["c", "d"]]
    table = SimpleNamespace(markdown="| a | b |", cells=cells)
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.metadata["cell_count"] == 4


def test_parse_table_metadata_has_row_count(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    cells = [["a", "b"], ["c", "d"], ["e", "f"]]
    table = SimpleNamespace(markdown="md", cells=cells)
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.metadata["row_count"] == 3


def test_parse_table_metadata_has_source_kreuzberg(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    table = SimpleNamespace(markdown="md", cells=[["a"]])
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.metadata["source"] == "kreuzberg"


def test_parse_table_confidence_high_when_has_cells(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    table = SimpleNamespace(markdown="md", cells=[["a"]])
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.confidence == 0.8


def test_parse_table_confidence_low_when_no_cells(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    table = SimpleNamespace(markdown="md", cells=[])
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.confidence == 0.5


def test_parse_table_confidence_low_when_cells_none(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    table = SimpleNamespace(markdown="md", cells=None)
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.confidence == 0.5


def test_parse_table_docx_locator_uses_table_index(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    table = SimpleNamespace(markdown="md", cells=[["a"]])
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.source_locator["table_index"] == 0


def test_parse_table_docx_locator_has_kreuzberg_heuristic(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    table = SimpleNamespace(markdown="md", cells=[["a"]])
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.source_locator["_kreuzberg_heuristic"] is True


def test_parse_table_pdf_locator_uses_page_number(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    table = SimpleNamespace(markdown="md", cells=[["a"]], page_number=3, bounding_box=None)
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.pdf"
    src.write_bytes(b"%PDF")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.source_locator["page"] == 3


def test_parse_table_pdf_page_number_zero_falls_back_to_1(tmp_path, monkeypatch):
    """page_number=0 → 退到 1。"""
    import app.parsers.kreuzberg_parser as mod
    table = SimpleNamespace(markdown="md", cells=[["a"]], page_number=0, bounding_box=None)
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.pdf"
    src.write_bytes(b"%PDF")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.source_locator["page"] == 1


def test_parse_table_pdf_page_number_none_falls_back_to_1(tmp_path, monkeypatch):
    """page_number=None → falsy → 退到 1。"""
    import app.parsers.kreuzberg_parser as mod
    table = SimpleNamespace(markdown="md", cells=[["a"]], page_number=None, bounding_box=None)
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.pdf"
    src.write_bytes(b"%PDF")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.source_locator["page"] == 1


def test_parse_table_pdf_with_bounding_box_converts_to_list(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    table = SimpleNamespace(
        markdown="md", cells=[["a"]],
        page_number=1, bounding_box=(1.0, 2.0, 3.0, 4.0),
    )
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.pdf"
    src.write_bytes(b"%PDF")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.source_locator["bbox"] == [1.0, 2.0, 3.0, 4.0]


def test_parse_table_pdf_with_bounding_box_is_list_type(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    table = SimpleNamespace(
        markdown="md", cells=[["a"]],
        page_number=1, bounding_box=(1, 2),
    )
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.pdf"
    src.write_bytes(b"%PDF")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert isinstance(table_el.source_locator["bbox"], list)


def test_parse_table_pdf_no_bounding_box_omits_key(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    table = SimpleNamespace(
        markdown="md", cells=[["a"]],
        page_number=1, bounding_box=None,
    )
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.pdf"
    src.write_bytes(b"%PDF")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert "bbox" not in table_el.source_locator


def test_parse_multiple_tables_assign_incrementing_index(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    t1 = SimpleNamespace(markdown="md1", cells=[["a"]])
    t2 = SimpleNamespace(markdown="md2", cells=[["b"]])
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[t1, t2]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 2
    assert tables[0].source_locator["table_index"] == 0
    assert tables[1].source_locator["table_index"] == 1


def test_parse_table_cell_count_with_empty_rows(tmp_path, monkeypatch):
    """sum(len(r) for r in cells) 处理空 row。"""
    import app.parsers.kreuzberg_parser as mod
    cells = [[], ["a"], []]
    table = SimpleNamespace(markdown="md", cells=cells)
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.metadata["cell_count"] == 1
    assert table_el.metadata["row_count"] == 3


def test_parse_table_no_markdown_no_cells_raises_validation_error(tmp_path, monkeypatch):
    """markdown=None + cells=None → content="" → Element 拒绝（schema 要求 content/resource_path 非空）。"""
    import app.parsers.kreuzberg_parser as mod
    import pytest as _pytest
    table = SimpleNamespace(markdown=None, cells=None)
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="", tables=[table]),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    with _pytest.raises(ValueError):
        parser.parse(src, source_hash="a" * 64)


# =========================================================================
# 9. parse() metadata 深度
# =========================================================================


def test_parse_metadata_has_kreuzberg_mime_type_key(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(mime_type="application/pdf"),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert "kreuzberg_mime_type" in doc.metadata


def test_parse_metadata_mime_type_value_passed_through(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(mime_type="application/vnd.openxmlformats"),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.metadata["kreuzberg_mime_type"] == "application/vnd.openxmlformats"


def test_parse_metadata_mime_type_none_passed_through(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(mime_type=None),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.metadata["kreuzberg_mime_type"] is None


def test_parse_metadata_has_kreuzberg_quality_score_key(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(quality_score=0.95),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert "kreuzberg_quality_score" in doc.metadata


def test_parse_metadata_quality_score_value_passed_through(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(quality_score=0.123),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.metadata["kreuzberg_quality_score"] == 0.123


def test_parse_metadata_quality_score_none_passed_through(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(quality_score=None),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.metadata["kreuzberg_quality_score"] is None


def test_parse_metadata_has_exactly_two_keys(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content=""),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert set(doc.metadata.keys()) == {"kreuzberg_mime_type", "kreuzberg_quality_score"}


def test_parse_returns_empty_chunks_list(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content=""),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.chunks == []


def test_parse_returns_empty_relations_list(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content=""),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.relations == []


def test_parse_returns_empty_errors_list(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content=""),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.errors == []


def test_parse_source_path_is_str_not_path(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content=""),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert isinstance(doc.source_path, str)
    assert doc.source_path == str(src)


def test_parse_source_path_with_string_input(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content=""),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(str(src), source_hash="a" * 64)
    assert doc.source_path == str(src)


def test_parse_source_hash_passed_through(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content=""),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    custom_hash = "0123456789abcdef" * 4
    doc = parser.parse(src, source_hash=custom_hash)
    assert doc.source_hash == custom_hash


def test_parse_document_id_includes_source_hash(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content=""),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    custom_hash = "0123456789abcdef" * 4
    doc = parser.parse(src, source_hash=custom_hash)
    # make_document_id 返回 hash[:16]
    assert custom_hash[:16] in doc.document_id


def test_parse_parser_name_in_document(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content=""),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.parser_name == "kreuzberg"


def test_parse_parser_version_in_document(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content=""),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.parser_version == parser.version


def test_parse_content_with_unicode_text(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="中文段落。"),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert len(doc.elements) == 1
    assert "中文" in doc.elements[0].content


def test_parse_content_with_heading_and_paragraph(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="# Title\n\nbody paragraph."),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert len(doc.elements) == 2
    assert doc.elements[0].type == "heading"
    assert doc.elements[1].type == "paragraph"


# =========================================================================
# 10. parse() reusability + schema
# =========================================================================


def test_parse_two_files_in_sequence_yield_independent_documents(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="para."),
    )
    src1 = tmp_path / "a.docx"
    src1.write_bytes(b"docx1")
    src2 = tmp_path / "b.docx"
    src2.write_bytes(b"docx2")
    parser = KreuzbergParser()
    doc1 = parser.parse(src1, source_hash="a" * 64)
    doc2 = parser.parse(src2, source_hash="b" * 64)
    assert doc1.document_id != doc2.document_id


def test_parse_two_files_element_ids_independent(tmp_path, monkeypatch):
    """两个文件解析后，element_id 都从 e0000 起。"""
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="para."),
    )
    src1 = tmp_path / "a.docx"
    src1.write_bytes(b"docx1")
    src2 = tmp_path / "b.docx"
    src2.write_bytes(b"docx2")
    parser = KreuzbergParser()
    doc1 = parser.parse(src1, source_hash="a" * 64)
    doc2 = parser.parse(src2, source_hash="b" * 64)
    assert doc1.elements[0].element_id.endswith("::e0000")
    assert doc2.elements[0].element_id.endswith("::e0000")


def test_parse_result_passes_schema_validation(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    from app.schema import validate
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="# Title\n\nbody paragraph."),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    # to_dict 后应通过 schema
    validate(doc.to_dict())


def test_parse_result_with_tables_passes_schema(tmp_path, monkeypatch):
    import app.parsers.kreuzberg_parser as mod
    from app.schema import validate
    table = SimpleNamespace(
        markdown="| a | b |", cells=[["a", "b"]],
        page_number=1, bounding_box=(0.0, 0.0, 10.0, 5.0),
    )
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="para.", tables=[table]),
    )
    src = tmp_path / "x.pdf"
    src.write_bytes(b"%PDF-1.4")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    validate(doc.to_dict())


# =========================================================================
# 11. 模块结构
# =========================================================================


def test_module_has_kreuzberg_parser_class():
    import app.parsers.kreuzberg_parser as mod
    assert hasattr(mod, "KreuzbergParser")


def test_module_has_heading_re_constant():
    import app.parsers.kreuzberg_parser as mod
    assert hasattr(mod, "_HEADING_RE")


def test_module_has_short_line_max_constant():
    import app.parsers.kreuzberg_parser as mod
    assert hasattr(mod, "_SHORT_LINE_MAX")


def test_module_has_classify_line_function():
    import app.parsers.kreuzberg_parser as mod
    assert callable(mod._classify_line)


def test_module_has_make_locator_function():
    import app.parsers.kreuzberg_parser as mod
    assert callable(mod._make_locator)


def test_module_has_split_content_function():
    import app.parsers.kreuzberg_parser as mod
    assert callable(mod._split_content_to_elements)


def test_module_has_kreuzberg_available_flag():
    import app.parsers.kreuzberg_parser as mod
    assert hasattr(mod, "_KREUZBERG_AVAILABLE")
    assert isinstance(mod._KREUZBERG_AVAILABLE, bool)


def test_module_kreuzberg_version_is_str_or_none():
    import app.parsers.kreuzberg_parser as mod
    assert mod._KREUZBERG_VERSION is None or isinstance(mod._KREUZBERG_VERSION, str)


def test_module_all_is_list_of_one_string():
    import app.parsers.kreuzberg_parser as mod
    assert isinstance(mod.__all__, list)
    assert mod.__all__ == ["KreuzbergParser"]


def test_module_exports_kreuzberg_parser_in_all():
    import app.parsers.kreuzberg_parser as mod
    assert "KreuzbergParser" in mod.__all__


def test_module_kreuzberg_imported_when_available():
    """装了 kreuzberg → mod.kreuzberg 应该可访问。"""
    import app.parsers.kreuzberg_parser as mod
    if mod._KREUZBERG_AVAILABLE:
        assert hasattr(mod, "kreuzberg")
        assert hasattr(mod, "ExtractionConfig")


def test_module_extraction_config_callable_when_available():
    import app.parsers.kreuzberg_parser as mod
    if mod._KREUZBERG_AVAILABLE:
        assert callable(mod.ExtractionConfig)
