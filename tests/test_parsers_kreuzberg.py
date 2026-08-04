"""app/parsers/kreuzberg_parser.py 内部 helper 的单元测试。

只覆盖纯函数 helper（不调用 kreuzberg 库）：
- _HEADING_RE / _SHORT_LINE_MAX 常量
- _classify_line：heading/paragraph 启发式
- _make_locator：pdf/docx locator schema
- _split_content_to_elements：content 双换行切块

实际 kreuzberg 库调用走 pipeline_integration / pipeline_errors。
"""

from __future__ import annotations

import re

import pytest

from app.parsers.kreuzberg_parser import (
    KreuzbergParser,
    _HEADING_RE,
    _SHORT_LINE_MAX,
    _classify_line,
    _make_locator,
    _split_content_to_elements,
)


# ---------- 常量 ----------


def test_short_line_max_is_80():
    """启发式阈值：行长 <= 80 视作 heading 候选。"""
    assert _SHORT_LINE_MAX == 80


def test_heading_re_is_compiled_pattern():
    assert isinstance(_HEADING_RE, re.Pattern)


def test_heading_re_matches_h1():
    m = _HEADING_RE.match("# Title")
    assert m is not None
    assert m.group(1) == "Title"


def test_heading_re_matches_h6():
    m = _HEADING_RE.match("###### Deep heading")
    assert m is not None
    assert m.group(1) == "Deep heading"


def test_heading_re_rejects_h7():
    """7 个 # 不是合法 ATX heading（spec 限制 1-6）。"""
    assert _HEADING_RE.match("####### Seven") is None


def test_heading_re_rejects_no_space_after_hash():
    """无空格分隔（#Title）不算 heading（kreuzberg 实现要求空白）。"""
    assert _HEADING_RE.match("#Title") is None


def test_heading_re_requires_content_after_hash():
    """只有 # 没内容不算 heading。"""
    assert _HEADING_RE.match("# ") is None
    assert _HEADING_RE.match("#") is None


def test_heading_re_captures_trailing_text():
    m = _HEADING_RE.match("#   Hello world   ")
    assert m is not None
    assert m.group(1) == "Hello world"


def test_heading_re_does_not_match_plain_paragraph():
    assert _HEADING_RE.match("plain text") is None


# ---------- _classify_line ----------


def test_classify_line_empty_string_returns_paragraph():
    etype, meta = _classify_line("")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_line_whitespace_only_returns_paragraph():
    etype, _ = _classify_line("   \t  \n")
    assert etype == "paragraph"


def test_classify_line_atx_h1_returns_heading():
    etype, meta = _classify_line("# Title")
    assert etype == "heading"
    assert meta["level"] == 1
    assert meta["raw_text"] == "Title"


def test_classify_line_atx_h3_returns_heading():
    etype, meta = _classify_line("### Subsection")
    assert etype == "heading"
    assert meta["level"] == 3


def test_classify_line_atx_heading_no_explicit_heuristic():
    """ATX heading 走的是 regex 路径，heuristic 字段不在 meta 中。"""
    etype, meta = _classify_line("# Title")
    assert "heuristic" not in meta


def test_classify_line_short_no_period_returns_heading_with_heuristic():
    """短文本（<=80）无句号 → heading（启发式 short_line）。"""
    etype, meta = _classify_line("Introduction")
    assert etype == "heading"
    assert meta["level"] == 0
    assert meta["raw_text"] == "Introduction"
    assert meta["heuristic"] == "short_line"


def test_classify_line_short_with_period_returns_paragraph():
    etype, _ = _classify_line("Done.")
    assert etype == "paragraph"


def test_classify_line_short_with_question_mark_returns_paragraph():
    etype, _ = _classify_line("Why?")
    assert etype == "paragraph"


def test_classify_line_short_with_exclamation_returns_paragraph():
    etype, _ = _classify_line("Hi!")
    assert etype == "paragraph"


def test_classify_line_short_with_chinese_period_returns_paragraph():
    etype, _ = _classify_line("完成。")
    assert etype == "paragraph"


def test_classify_line_short_with_chinese_question_mark_returns_paragraph():
    etype, _ = _classify_line("好吗？")
    assert etype == "paragraph"


def test_classify_line_short_with_chinese_exclamation_returns_paragraph():
    etype, _ = _classify_line("嗨！")
    assert etype == "paragraph"


def test_classify_line_long_line_returns_paragraph():
    """长行（> 80）→ paragraph（即便无句号）。"""
    etype, _ = _classify_line("a" * 100)
    assert etype == "paragraph"


def test_classify_line_atx_overrides_short_line():
    """ATX heading 即使短也优先匹配 regex。"""
    etype, meta = _classify_line("# A")
    assert etype == "heading"
    assert meta["level"] == 1
    # 注：ATX 路径不走 heuristic，meta 无 heuristic 键
    assert "heuristic" not in meta


def test_classify_line_strip_applies_to_short_line_check():
    """带前导空白的短行，strip 后仍 <=80 → heading 启发式。"""
    etype, _ = _classify_line("   short title   ")
    assert etype == "heading"


# ---------- _make_locator ----------


def test_make_locator_pdf_returns_page_1_with_placeholder():
    loc = _make_locator("pdf", 0)
    assert loc["page"] == 1
    assert loc["_kreuzberg_placeholder"] is True


def test_make_locator_pdf_ignores_paragraph_index_arg():
    """PDF locator 不带 paragraph_index（schema 不允许混用）。"""
    loc = _make_locator("pdf", 5)
    assert "paragraph_index" not in loc


def test_make_locator_docx_returns_paragraph_index_with_heuristic():
    loc = _make_locator("docx", 3)
    assert loc["paragraph_index"] == 3
    assert loc["_kreuzberg_heuristic"] is True


def test_make_locator_docx_no_page_key():
    """DOCX locator 不带 page。"""
    loc = _make_locator("docx", 0)
    assert "page" not in loc


def test_make_locator_docx_includes_correct_index():
    """paragraph_index 跟随入参。"""
    for i in [0, 1, 7, 99]:
        loc = _make_locator("docx", i)
        assert loc["paragraph_index"] == i


def test_make_locator_pdf_always_page_1():
    """不管 paragraph_index 是多少，pdf locator 始终用 page=1 占位。"""
    for i in [0, 5, 100]:
        loc = _make_locator("pdf", i)
        assert loc["page"] == 1


# ---------- _split_content_to_elements ----------


def test_split_content_empty_string_returns_no_elements():
    elements, _ = _split_content_to_elements("", "docx", "doc-abc")
    assert elements == []


def test_split_content_single_paragraph():
    elements, _ = _split_content_to_elements("Just one paragraph.", "docx", "doc-abc")
    assert len(elements) == 1
    assert elements[0].type == "paragraph"
    assert elements[0].content == "Just one paragraph."


def test_split_content_two_paragraphs_double_newline_separated():
    content = "Para one.\n\nPara two."
    elements, _ = _split_content_to_elements(content, "docx", "doc-abc")
    assert len(elements) == 2
    assert elements[0].content == "Para one."
    assert elements[1].content == "Para two."


def test_split_content_heading_atx_extracted_as_heading():
    elements, _ = _split_content_to_elements("# Title\n\nbody", "docx", "doc-abc")
    types = [e.type for e in elements]
    assert "heading" in types
    heading = [e for e in elements if e.type == "heading"][0]
    assert heading.content == "Title"
    assert heading.metadata["level"] == 1


def test_split_content_heading_short_line_extracted_as_heading():
    """短行无句号 → heading（short_line 启发式）。"""
    elements, _ = _split_content_to_elements("Title\n\nbody", "docx", "doc-abc")
    types = [e.type for e in elements]
    assert "heading" in types


def test_split_content_heading_with_body_in_same_block():
    """heading 第一行 + 后续正文在同一 block（无空行分隔）。"""
    content = "# Section\n\nintro paragraph."
    elements, _ = _split_content_to_elements(content, "docx", "doc-abc")
    # 两个 block：1) heading "Section" 2) paragraph "intro paragraph."
    assert len(elements) == 2
    assert elements[0].type == "heading"
    assert elements[1].type == "paragraph"


def test_split_content_heading_with_multiline_block_emits_rest_as_paragraph():
    """同一 block 内：第一行 heading，剩余多行作为 paragraph。"""
    content = "# Title\nline2\nline3"
    elements, _ = _split_content_to_elements(content, "docx", "doc-abc")
    # 第一行是 heading，剩余 "line2\nline3" 作为 paragraph
    assert len(elements) == 2
    assert elements[0].type == "heading"
    assert elements[0].content == "Title"
    assert elements[1].type == "paragraph"
    assert "line2" in elements[1].content
    assert "line3" in elements[1].content


def test_split_content_paragraph_has_kreuzberg_heuristic_metadata():
    """非 heading 的 paragraph block 含 kreuzberg_heuristic=True。"""
    elements, _ = _split_content_to_elements("Some text.", "docx", "doc-abc")
    assert elements[0].metadata["kreuzberg_heuristic"] is True


def test_split_content_heading_atx_no_kreuzberg_heuristic_key():
    """ATX heading 不带 kreuzberg_heuristic（它走的是 regex 路径）。"""
    elements, _ = _split_content_to_elements("# Title", "docx", "doc-abc")
    assert "kreuzberg_heuristic" not in elements[0].metadata


def test_split_content_heading_confidence_is_06():
    """heading 的 confidence 固定为 0.6。"""
    elements, _ = _split_content_to_elements("# Title", "docx", "doc-abc")
    assert elements[0].confidence == 0.6


def test_split_content_paragraph_confidence_is_05():
    """普通 paragraph block 的 confidence 固定为 0.5。"""
    elements, _ = _split_content_to_elements("body content here.", "docx", "doc-abc")
    assert elements[0].confidence == 0.5


def test_split_content_rest_paragraph_after_heading_confidence_05():
    """heading 后剩余 paragraph 的 confidence 也是 0.5。"""
    content = "# Title\nrest of section"
    elements, _ = _split_content_to_elements(content, "docx", "doc-abc")
    rest_paragraph = [e for e in elements if e.type == "paragraph"][0]
    assert rest_paragraph.confidence == 0.5


def test_split_content_element_id_format_consecutive():
    elements, _ = _split_content_to_elements(
        "# A\n\nB\n\nC", "docx", "doc-abcdef0123456789"
    )
    for i, e in enumerate(elements):
        assert e.element_id == f"doc-abcdef0123456789::e{i:04d}"


def test_split_content_docx_locator_has_paragraph_index():
    elements, _ = _split_content_to_elements("paragraph 1.\n\nparagraph 2.", "docx", "doc-abc")
    # paragraph_index 应该从 0 开始递增
    assert elements[0].source_locator["paragraph_index"] == 0
    assert elements[1].source_locator["paragraph_index"] == 1


def test_split_content_pdf_locator_has_page_placeholder():
    elements, _ = _split_content_to_elements("Some text.", "pdf", "doc-abc")
    loc = elements[0].source_locator
    assert loc["page"] == 1
    assert loc["_kreuzberg_placeholder"] is True


def test_split_content_multiple_blank_lines_treated_as_single_separator():
    content = "Para one.\n\n\n\n\nPara two."
    elements, _ = _split_content_to_elements(content, "docx", "doc-abc")
    assert len(elements) == 2


def test_split_content_strips_block_whitespace():
    content = "\n\n  Para with whitespace.  \n\n"
    elements, _ = _split_content_to_elements(content, "docx", "doc-abc")
    assert len(elements) == 1
    assert elements[0].content == "Para with whitespace."


def test_split_content_second_return_value_is_empty_list():
    """第二返回值 used_paragraph_indices_per_element 仅用于调试，固定空 list。"""
    _, used = _split_content_to_elements("text", "docx", "doc-abc")
    assert used == []


# ---------- KreuzbergParser 类基础契约 ----------


def test_kreuzberg_parser_name_constant():
    assert KreuzbergParser.name == "kreuzberg"


def test_kreuzberg_parser_version_is_string_or_unknown():
    """version 是 kreuzberg.__version__ 或 'unknown'。"""
    parser = KreuzbergParser()
    assert isinstance(parser.version, str)
    assert parser.version  # 非空


def test_kreuzberg_parser_default_include_document_structure_true():
    parser = KreuzbergParser()
    assert parser._include_document_structure is True


def test_kreuzberg_parser_init_can_disable_document_structure():
    parser = KreuzbergParser(include_document_structure=False)
    assert parser._include_document_structure is False


def test_kreuzberg_parser_inherits_from_parser():
    from app.parsers.base import Parser
    parser = KreuzbergParser()
    assert isinstance(parser, Parser)
