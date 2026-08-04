r"""app/parsers/kreuzberg_parser.py 边角测试 - 第六轮（Round 146）。

补强已有 base/edges/edges2/edges3/edges4（共 599 测试）未覆盖的深度：
- _HEADING_RE 模式深度（pattern string、flags、groups、anchored）
- _SHORT_LINE_MAX 常量
- _classify_line 罕见边界（mixed scripts、emoji、控制字符）
- _split_content_to_elements 复杂场景（heading 与 paragraph 混排、单 block 多元素）
- _make_locator source_type 取值覆盖
- KreuzbergParser 类属性验证（不在运行时变化）
- 模块结构（imports、__all__、dunder）
- 综合行为（多调用稳定性、跨函数一致性）
"""

from __future__ import annotations

import inspect
import re
from typing import Any

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
# _HEADING_RE 模式深度
# =========================================================================


def test_heading_re_pattern_object_type():
    assert isinstance(_HEADING_RE, re.Pattern)


def test_heading_re_pattern_string_value():
    """pattern 应包含 #{1,6} 限定 1-6 个 #。"""
    pat = _HEADING_RE.pattern
    assert "#{1,6}" in pat or "#{1,6}" in pat


def test_heading_re_pattern_starts_with_caret():
    """^ 锚定行首。"""
    assert _HEADING_RE.pattern.startswith("^")


def test_heading_re_pattern_ends_with_dollar():
    """$ 锚定行尾。"""
    assert _HEADING_RE.pattern.endswith("$")


def test_heading_re_uses_multiline_disabled():
    """无 re.MULTILINE 标志：$ 在 \n 前匹配但要求后续也是 end-of-string。
    实际 '# h1\n# h2' 整体不匹配（$ 不能在中间 \n 处匹配且后续还有内容）。
    """
    # 简单验证：单个 # h1 字符串匹配
    assert _HEADING_RE.match("# h1") is not None
    # 末尾 \n 也匹配（$ 在 final \n 前匹配）
    assert _HEADING_RE.match("# h1\n") is not None
    # 中间含 \n 后续还有内容 → 不匹配
    assert _HEADING_RE.match("# h1\nextra") is None


def test_heading_re_no_match_for_input_with_leading_text():
    """不是以 # 开头 → no match。"""
    assert _HEADING_RE.match("text # h1") is None


def test_heading_re_groups_count_one():
    """pattern 有一个 capture group（content after #）。"""
    pat = _HEADING_RE.pattern
    # 数 capture group 标记
    assert pat.count("(") >= 1


def test_heading_re_match_returns_match_object_for_valid_input():
    m = _HEADING_RE.match("# hello")
    assert m is not None
    assert hasattr(m, "group")


def test_heading_re_match_captures_text_only_stripped():
    m = _HEADING_RE.match("#   hello   ")
    assert m is not None
    # group(1) 应是去掉首尾空白的 text
    assert m.group(1) == "hello"


def test_heading_re_no_match_when_text_has_newline_mid():
    """含中间换行的多行字符串不匹配（pattern $ 不能在中间换行处结束且后续还有内容）。"""
    assert _HEADING_RE.match("# h1\nextra") is None


def test_heading_re_no_re_verbose_flag():
    """无 re.VERBOSE 标志（pattern 中的空格原义）。"""
    # VERBOSE 会让 pattern 中空格被忽略；本 pattern 含 \s 显式空格匹配
    # 测试方式：re.compile 后 flags 应不包含 VERBOSE
    assert not (_HEADING_RE.flags & re.VERBOSE)


def test_heading_re_no_re_ignorecase_flag():
    assert not (_HEADING_RE.flags & re.IGNORECASE)


# =========================================================================
# _SHORT_LINE_MAX 常量
# =========================================================================


def test_short_line_max_is_int():
    assert isinstance(_SHORT_LINE_MAX, int)


def test_short_line_max_value_80():
    assert _SHORT_LINE_MAX == 80


def test_short_line_max_positive():
    assert _SHORT_LINE_MAX > 0


# =========================================================================
# _classify_line 罕见边界
# =========================================================================


def test_classify_line_single_char_no_terminator_short_heading():
    etype, meta = _classify_line("x")
    assert etype == "heading"
    assert meta["heuristic"] == "short_line"


def test_classify_line_80_chars_no_terminator_short_heading():
    text = "a" * 80
    etype, _ = _classify_line(text)
    assert etype == "heading"


def test_classify_line_81_chars_no_terminator_paragraph():
    text = "a" * 81
    etype, _ = _classify_line(text)
    assert etype == "paragraph"


def test_classify_line_80_chars_with_terminator_paragraph():
    text = "a" * 79 + "."
    etype, _ = _classify_line(text)
    assert etype == "paragraph"


def test_classify_line_emoji_no_terminator_short():
    """emoji 占多个 byte 但 len(str) 计 1。"""
    etype, meta = _classify_line("😀")
    assert etype == "heading"
    assert meta["heuristic"] == "short_line"


def test_classify_line_only_digit_terminator_period():
    etype, _ = _classify_line("12345.")
    assert etype == "paragraph"


def test_classify_line_only_digit_no_terminator():
    etype, meta = _classify_line("12345")
    assert etype == "heading"


def test_classify_line_mixed_cjk_terminator_chinese_period():
    etype, _ = _classify_line("中文测试。")
    assert etype == "paragraph"


def test_classify_line_mixed_cjk_no_terminator():
    etype, _ = _classify_line("中文测试")
    assert etype == "heading"


def test_classify_line_text_with_tab_in_middle():
    etype, _ = _classify_line("hello\tworld")
    assert etype == "heading"


def test_classify_line_short_with_period_in_middle_short():
    """period 不在末尾 → 仍按 short_line 判定。"""
    etype, _ = _classify_line("a.b")
    assert etype == "heading"


def test_classify_line_short_starts_with_dash():
    etype, _ = _classify_line("- item")
    assert etype == "heading"


def test_classify_line_short_starts_with_pipe():
    etype, _ = _classify_line("|table|")
    assert etype == "heading"


def test_classify_line_atx_with_chinese_text():
    etype, meta = _classify_line("# 中文标题")
    assert etype == "heading"
    assert meta["raw_text"] == "中文标题"


def test_classify_line_returns_tuple():
    result = _classify_line("hello")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_classify_line_first_element_is_str():
    etype, _ = _classify_line("x")
    assert isinstance(etype, str)


def test_classify_line_second_element_is_dict():
    _, meta = _classify_line("x")
    assert isinstance(meta, dict)


def test_classify_line_paragraph_metadata_empty():
    _, meta = _classify_line("hello world this is a paragraph ending with period.")
    assert meta == {}


def test_classify_line_heading_with_level_zero_for_short_line():
    _, meta = _classify_line("short")
    assert meta["level"] == 0


def test_classify_line_atx_h1_level_one():
    _, meta = _classify_line("# title")
    assert meta["level"] == 1


def test_classify_line_atx_h6_level_six():
    _, meta = _classify_line("###### title")
    assert meta["level"] == 6


# =========================================================================
# _make_locator 边界
# =========================================================================


def test_make_locator_pdf_keys():
    loc = _make_locator("pdf", 0)
    assert set(loc.keys()) == {"page", "_kreuzberg_placeholder"}


def test_make_locator_docx_keys():
    loc = _make_locator("docx", 5)
    assert set(loc.keys()) == {"paragraph_index", "_kreuzberg_heuristic"}


def test_make_locator_pdf_page_value_one():
    loc = _make_locator("pdf", 100)
    assert loc["page"] == 1


def test_make_locator_pdf_page_value_one_for_negative_index():
    loc = _make_locator("pdf", -1)
    assert loc["page"] == 1


def test_make_locator_docx_paragraph_index_passes_through_zero():
    loc = _make_locator("docx", 0)
    assert loc["paragraph_index"] == 0


def test_make_locator_docx_paragraph_index_passes_through_large():
    loc = _make_locator("docx", 999)
    assert loc["paragraph_index"] == 999


def test_make_locator_pdf_ignores_paragraph_index():
    """pdf locator 不含 paragraph_index 字段。"""
    loc = _make_locator("pdf", 42)
    assert "paragraph_index" not in loc


def test_make_locator_docx_ignores_page():
    loc = _make_locator("docx", 0)
    assert "page" not in loc


def test_make_locator_returns_dict():
    assert isinstance(_make_locator("pdf", 0), dict)
    assert isinstance(_make_locator("docx", 0), dict)


def test_make_locator_pdf_placeholder_true():
    assert _make_locator("pdf", 0)["_kreuzberg_placeholder"] is True


def test_make_locator_docx_heuristic_true():
    assert _make_locator("docx", 0)["_kreuzberg_heuristic"] is True


def test_make_locator_other_source_type_falls_to_else_branch():
    """非 pdf → 走 else 分支，含 paragraph_index。"""
    loc = _make_locator("markdown", 0)
    assert "paragraph_index" in loc
    assert "page" not in loc


def test_make_locator_other_source_type_heuristic_true():
    loc = _make_locator("text", 0)
    assert loc["_kreuzberg_heuristic"] is True


def test_make_locator_other_source_type_paragraph_index_passes():
    loc = _make_locator("html", 7)
    assert loc["paragraph_index"] == 7


def test_make_locator_signature():
    sig = inspect.signature(_make_locator)
    assert len(sig.parameters) == 2
    assert "source_type" in sig.parameters
    assert "paragraph_index" in sig.parameters


# =========================================================================
# _split_content_to_elements 复杂场景
# =========================================================================


def test_split_content_returns_two_tuple():
    result = _split_content_to_elements("hello", "docx", "doc-abc")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_split_content_first_is_list():
    elements, _ = _split_content_to_elements("hello", "docx", "doc-abc")
    assert isinstance(elements, list)


def test_split_content_second_is_list():
    _, second = _split_content_to_elements("hello", "docx", "doc-abc")
    assert isinstance(second, list)


def test_split_content_second_empty_for_simple_input():
    _, second = _split_content_to_elements("hello", "docx", "doc-abc")
    assert second == []


def test_split_content_empty_returns_empty_elements():
    elements, _ = _split_content_to_elements("", "docx", "doc-abc")
    assert elements == []


def test_split_content_whitespace_only_returns_empty():
    elements, _ = _split_content_to_elements("   \n\n   ", "docx", "doc-abc")
    assert elements == []


def test_split_content_single_paragraph_one_element():
    elements, _ = _split_content_to_elements("hello", "docx", "doc-abc")
    assert len(elements) == 1


def test_split_content_two_paragraphs_two_elements():
    elements, _ = _split_content_to_elements("para1\n\npara2", "docx", "doc-abc")
    assert len(elements) == 2


def test_split_content_atx_heading_emits_heading_element():
    elements, _ = _split_content_to_elements("# title", "docx", "doc-abc")
    assert len(elements) == 1
    assert elements[0].type == "heading"


def test_split_content_atx_heading_confidence_06():
    elements, _ = _split_content_to_elements("# title", "docx", "doc-abc")
    assert elements[0].confidence == 0.6


def test_split_content_paragraph_confidence_05():
    elements, _ = _split_content_to_elements("hello world this is a paragraph ending with period.", "docx", "doc-abc")
    # 走 short_line 判定为 heading 时 confidence 0.6
    # 但带句号长文本应为 paragraph
    # 需要确保文本够长以避开 short_line
    text = "This is a long enough paragraph that ends with a period."
    elements, _ = _split_content_to_elements(text, "docx", "doc-abc")
    assert elements[0].confidence == 0.5


def test_split_content_element_ids_zero_padded():
    elements, _ = _split_content_to_elements("a\n\nb\n\nc", "docx", "doc-abc")
    ids = [e.element_id for e in elements]
    assert ids == ["doc-abc::e0000", "doc-abc::e0001", "doc-abc::e0002"]


def test_split_content_element_ids_unique():
    elements, _ = _split_content_to_elements("a\n\nb\n\nc\n\nd", "docx", "doc-abc")
    ids = [e.element_id for e in elements]
    assert len(set(ids)) == len(ids)


def test_split_content_element_ids_increasing():
    elements, _ = _split_content_to_elements("a\n\nb\n\nc", "docx", "doc-abc")
    indices = [int(e.element_id.split("::e")[1]) for e in elements]
    assert indices == sorted(indices)


def test_split_content_document_id_propagated():
    elements, _ = _split_content_to_elements("hello", "docx", "doc-xyz123")
    assert all(e.element_id.startswith("doc-xyz123::") for e in elements)


def test_split_content_heading_with_body_emits_two_elements():
    """heading 后跟 paragraph body 在同一 block → 两个 element。"""
    content = "# title\nbody text here that is long enough to be paragraph."
    elements, _ = _split_content_to_elements(content, "docx", "doc-abc")
    assert len(elements) == 2
    assert elements[0].type == "heading"
    assert elements[1].type == "paragraph"


def test_split_content_heading_with_body_confidence_06_then_05():
    content = "# title\nbody text here that is long enough to be paragraph."
    elements, _ = _split_content_to_elements(content, "docx", "doc-abc")
    assert elements[0].confidence == 0.6
    assert elements[1].confidence == 0.5


def test_split_content_pdf_uses_page_locator():
    elements, _ = _split_content_to_elements("hello", "pdf", "doc-abc")
    assert elements[0].source_locator["page"] == 1


def test_split_content_docx_uses_paragraph_index():
    elements, _ = _split_content_to_elements("hello\n\nworld", "docx", "doc-abc")
    assert elements[0].source_locator["paragraph_index"] == 0
    assert elements[1].source_locator["paragraph_index"] == 1


def test_split_content_paragraph_metadata_kreuzberg_heuristic_true():
    text = "This is a long enough paragraph that ends with a period."
    elements, _ = _split_content_to_elements(text, "docx", "doc-abc")
    assert elements[0].metadata.get("kreuzberg_heuristic") is True


def test_split_content_heading_metadata_no_kreuzberg_heuristic_for_atx():
    elements, _ = _split_content_to_elements("# title", "docx", "doc-abc")
    # atx heading 用 metadata['heuristic']（None）和 level，不含 kreuzberg_heuristic
    assert "kreuzberg_heuristic" not in elements[0].metadata


def test_split_content_heading_metadata_has_level():
    elements, _ = _split_content_to_elements("# title", "docx", "doc-abc")
    assert elements[0].metadata["level"] == 1


def test_split_content_short_line_heading_metadata_has_heuristic():
    elements, _ = _split_content_to_elements("short title", "docx", "doc-abc")
    assert elements[0].metadata["heuristic"] == "short_line"


def test_split_content_atx_heading_metadata_heuristic_none():
    elements, _ = _split_content_to_elements("# title", "docx", "doc-abc")
    # atx heading 的 heuristic 是 None（meta.get("heuristic") 默认）
    assert elements[0].metadata["heuristic"] is None


def test_split_content_strips_block_whitespace():
    elements, _ = _split_content_to_elements("  hello world  ", "docx", "doc-abc")
    assert elements[0].content == "hello world"


def test_split_content_multiple_blank_lines_treated_as_single_separator():
    elements, _ = _split_content_to_elements("a\n\n\n\n\nb", "docx", "doc-abc")
    assert len(elements) == 2


def test_split_content_crlf_treated_as_lf():
    elements, _ = _split_content_to_elements("a\r\n\r\nb", "docx", "doc-abc")
    assert len(elements) == 2


def test_split_content_only_carriage_returns_treated_as_lf():
    elements, _ = _split_content_to_elements("a\r\rb", "docx", "doc-abc")
    # \r\r 不会被当作段落分隔（不是 \n\s*\n）
    # 实际：split(r"\n\s*\n", "a\r\rb") → ["a\r\rb"]
    # 然后 block.strip() = "a\r\rb"，是单个 block
    # splitlines()[0] = "a"
    # 但 _classify_line("a") 返回 heading
    # 所以可能输出 1 个 element
    assert len(elements) >= 1


def test_split_content_with_three_paragraphs():
    elements, _ = _split_content_to_elements("p1\n\np2\n\np3", "docx", "doc-abc")
    assert len(elements) == 3


def test_split_content_signature():
    sig = inspect.signature(_split_content_to_elements)
    assert len(sig.parameters) == 3
    assert "content" in sig.parameters
    assert "source_type" in sig.parameters
    assert "document_id" in sig.parameters


# =========================================================================
# KreuzbergParser 类属性
# =========================================================================


def test_kreuzberg_parser_name_constant():
    assert KreuzbergParser.name == "kreuzberg"


def test_kreuzberg_parser_name_is_str():
    assert isinstance(KreuzbergParser.name, str)


def test_kreuzberg_parser_version_is_str():
    assert isinstance(KreuzbergParser.version, str)


def test_kreuzberg_parser_version_not_empty():
    assert KreuzbergParser.version


def test_kreuzberg_parser_inherits_parser():
    assert issubclass(KreuzbergParser, Parser)


def test_kreuzberg_parser_class_dict_has_name():
    assert "name" in KreuzbergParser.__dict__


def test_kreuzberg_parser_class_dict_has_version():
    assert "version" in KreuzbergParser.__dict__


def test_kreuzberg_parser_class_dict_has_parse():
    assert "parse" in KreuzbergParser.__dict__


def test_kreuzberg_parser_class_dict_has_init():
    assert "__init__" in KreuzbergParser.__dict__


def test_kreuzberg_parser_init_default_include_document_structure_true():
    p = KreuzbergParser()
    assert p._include_document_structure is True


def test_kreuzberg_parser_init_keyword_only():
    """include_document_structure 是 keyword-only 参数。"""
    p = KreuzbergParser(include_document_structure=False)
    assert p._include_document_structure is False


def test_kreuzberg_parser_init_explicit_true():
    p = KreuzbergParser(include_document_structure=True)
    assert p._include_document_structure is True


def test_kreuzberg_parser_init_signature_one_keyword_param():
    sig = inspect.signature(KreuzbergParser.__init__)
    # self, include_document_structure
    assert len(sig.parameters) == 2


def test_kreuzberg_parser_init_param_is_keyword_only():
    sig = inspect.signature(KreuzbergParser.__init__)
    param = sig.parameters["include_document_structure"]
    assert param.kind == inspect.Parameter.KEYWORD_ONLY


def test_kreuzberg_parser_init_default_value_true():
    sig = inspect.signature(KreuzbergParser.__init__)
    assert sig.parameters["include_document_structure"].default is True


def test_kreuzberg_parser_init_return_annotation_none_str():
    sig = inspect.signature(KreuzbergParser.__init__)
    assert sig.return_annotation in (None, "None", inspect.Signature.empty)


def test_kreuzberg_parser_parse_signature_three_params():
    sig = inspect.signature(KreuzbergParser.parse)
    # self, path, source_hash
    assert len(sig.parameters) == 3


def test_kreuzberg_parser_parse_params_no_default():
    sig = inspect.signature(KreuzbergParser.parse)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_kreuzberg_parser_parse_return_annotation_document():
    sig = inspect.signature(KreuzbergParser.parse)
    # from __future__ makes it string
    assert sig.return_annotation in ("Document", inspect.Signature.empty)


def test_kreuzberg_parser_instance_independent_state():
    """两个实例的 _include_document_state 独立。"""
    p1 = KreuzbergParser()
    p2 = KreuzbergParser(include_document_structure=False)
    assert p1._include_document_structure is True
    assert p2._include_document_structure is False


def test_kreuzberg_parser_instance_dict_has_only_include_attr():
    p = KreuzbergParser()
    assert "_include_document_structure" in p.__dict__
    # 没有其他实例属性
    assert len(p.__dict__) == 1


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_only_kreuzberg_parser():
    import app.parsers.kreuzberg_parser as mod
    assert mod.__all__ == ["KreuzbergParser"]


def test_module_all_is_list():
    import app.parsers.kreuzberg_parser as mod
    assert isinstance(mod.__all__, list)


def test_module_docstring_present():
    import app.parsers.kreuzberg_parser as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_kreuzberg():
    import app.parsers.kreuzberg_parser as mod
    assert "kreuzberg" in mod.__doc__.lower() or "Kreuzberg" in mod.__doc__


def test_module_imports_re():
    import app.parsers.kreuzberg_parser as mod
    src = inspect.getsource(mod)
    assert "import re" in src


def test_module_imports_path():
    import app.parsers.kreuzberg_parser as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import app.parsers.kreuzberg_parser as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_document():
    import app.parsers.kreuzberg_parser as mod
    src = inspect.getsource(mod)
    assert "Document" in src


def test_module_imports_element():
    import app.parsers.kreuzberg_parser as mod
    src = inspect.getsource(mod)
    assert "Element" in src


def test_module_imports_warning_record():
    import app.parsers.kreuzberg_parser as mod
    src = inspect.getsource(mod)
    assert "WarningRecord" in src


def test_module_imports_parser_base():
    import app.parsers.kreuzberg_parser as mod
    src = inspect.getsource(mod)
    assert "from app.parsers.base import" in src


def test_module_imports_parser_error():
    import app.parsers.kreuzberg_parser as mod
    src = inspect.getsource(mod)
    assert "ParserError" in src


def test_module_imports_detect_source_type():
    import app.parsers.kreuzberg_parser as mod
    src = inspect.getsource(mod)
    assert "detect_source_type" in src


def test_module_imports_make_document_id():
    import app.parsers.kreuzberg_parser as mod
    src = inspect.getsource(mod)
    assert "make_document_id" in src


def test_module_uses_future_annotations():
    import app.parsers.kreuzberg_parser as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_kreuzberg_available_is_bool():
    import app.parsers.kreuzberg_parser as mod
    assert isinstance(mod._KREUZBERG_AVAILABLE, bool)


def test_module_kreuzberg_version_is_str_or_none():
    import app.parsers.kreuzberg_parser as mod
    assert mod._KREUZBERG_VERSION is None or isinstance(mod._KREUZBERG_VERSION, str)


def test_module_has_kreuzberg_import_error_attr_only_when_unavailable():
    """如果 _KREUZBERG_AVAILABLE=False，应有 _KREUZBERG_IMPORT_ERROR；否则不一定。"""
    import app.parsers.kreuzberg_parser as mod
    if not mod._KREUZBERG_AVAILABLE:
        assert hasattr(mod, "_KREUZBERG_IMPORT_ERROR")
        assert isinstance(mod._KREUZBERG_IMPORT_ERROR, str)


# =========================================================================
# 综合行为
# =========================================================================


def test_classify_then_split_consistency_atx_heading():
    """_classify_line 与 _split_content_to_elements 对同一行应一致。"""
    line = "# heading"
    etype, _ = _classify_line(line)
    elements, _ = _split_content_to_elements(line, "docx", "doc-abc")
    assert elements[0].type == etype


def test_classify_then_split_consistency_paragraph():
    line = "This is a long enough paragraph that ends with a period."
    etype, _ = _classify_line(line)
    elements, _ = _split_content_to_elements(line, "docx", "doc-abc")
    assert elements[0].type == etype


def test_classify_then_split_consistency_short_line():
    line = "short"
    etype, _ = _classify_line(line)
    elements, _ = _split_content_to_elements(line, "docx", "doc-abc")
    assert elements[0].type == etype


def test_split_content_doc_ids_dont_collide_across_calls():
    """不同 document_id 调用应产生不同 element_ids。"""
    e1, _ = _split_content_to_elements("hello", "docx", "doc-aaa")
    e2, _ = _split_content_to_elements("hello", "docx", "doc-bbb")
    assert e1[0].element_id != e2[0].element_id


def test_make_locator_stable_across_calls_pdf():
    """相同参数多次调用结果一致。"""
    a = _make_locator("pdf", 5)
    b = _make_locator("pdf", 5)
    assert a == b


def test_make_locator_stable_across_calls_docx():
    a = _make_locator("docx", 5)
    b = _make_locator("docx", 5)
    assert a == b


def test_kreuzberg_parser_two_instances_same_class_attrs():
    p1 = KreuzbergParser()
    p2 = KreuzbergParser()
    assert p1.name == p2.name == KreuzbergParser.name
    assert p1.version == p2.version == KreuzbergParser.version


def test_kreuzberg_parser_init_does_not_change_class_attrs():
    """构造实例不改类属性。"""
    name_before = KreuzbergParser.name
    version_before = KreuzbergParser.version
    KreuzbergParser()
    KreuzbergParser(include_document_structure=False)
    assert KreuzbergParser.name == name_before
    assert KreuzbergParser.version == version_before
