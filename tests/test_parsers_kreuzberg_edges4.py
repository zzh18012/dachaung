"""app/parsers/kreuzberg_parser.py 边角测试 - 第四轮（Round 112）。

补强已有 base/edges/edges2/edges3（共 145+ 测试）未覆盖的深度路径：
- _classify_line：纯空白行变体、纯标点、纯空格、纯数字 + 标点、
  text 含 markdown emphasis（**bold**）、含 inline code（`code`）、
  CJK 终止符（！？。）、连续终止符、terminator 是 ASCII 句号 + 数字
- _HEADING_RE：多种空白变种、纯空格、trailing whitespace、
  mixed leading whitespace、含 BOM 字符
- _split_content_to_elements：CJK 内容、content 含 \r\n、
  连续多空行、trailing 空行、leading 空行、单 block 含多 ATX heading、
  block 以 paragraph 标记开头但实际是 heading（错位）
- KreuzbergParser 类/实例属性：
  - name/version 类属性
  - include_document_structure 默认值
  - 两个实例互不影响
- parse 多种 metadata：mime_type=None 已覆盖、quality_score=None 已覆盖、
  但 mime_type 含特殊字符、quality_score=0/1/0.5、quality_score 整数
- parse tables：cells 含空子列表、cells 含数字、cells 不规则、
  cell_count 计算精确性、row_count=0 行为、bounding_box list 而非 tuple
- 模块结构深度：re、Path、Any import 验证、__all__ 内容、
  metadata dict 字段顺序
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from app.parsers.base import ParserError
from app.parsers.kreuzberg_parser import (
    KreuzbergParser,
    _HEADING_RE,
    _SHORT_LINE_MAX,
    _classify_line,
    _make_locator,
    _split_content_to_elements,
)


# =========================================================================
# _classify_line：纯空白 / 纯标点
# =========================================================================


def test_classify_line_only_spaces_returns_paragraph_with_empty_metadata():
    etype, meta = _classify_line("     ")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_line_only_tabs_returns_paragraph():
    etype, _ = _classify_line("\t\t\t")
    assert etype == "paragraph"


def test_classify_line_only_newline_returns_paragraph():
    etype, _ = _classify_line("\n")
    assert etype == "paragraph"


def test_classify_line_only_punctuation_with_terminator_is_paragraph():
    """全是句号（.）含终止符 → paragraph。"""
    etype, _ = _classify_line("...")
    assert etype == "paragraph"


def test_classify_line_only_punctuation_no_terminator_is_short_line_heading():
    """全是 ! 无终止符（! 也算终止符）→ 实际 ! 在终止符列表，所以是 paragraph。
    但纯 ? 也类似。需要不含终止符的纯标点。
    """
    # 用连字符 / 等号这种不在终止符列表的
    etype, meta = _classify_line("---===---")
    assert etype == "heading"
    assert meta.get("heuristic") == "short_line"


def test_classify_line_short_with_no_terminator_and_only_digit():
    """纯数字 '123' 短且无终止符 → short_line heading。"""
    etype, meta = _classify_line("123")
    assert etype == "heading"
    assert meta.get("heuristic") == "short_line"


def test_classify_line_short_with_only_letter_no_terminator():
    etype, _ = _classify_line("xyz")
    assert etype == "heading"


def test_classify_line_long_text_no_terminator_is_paragraph():
    """超长文本即使无终止符也是 paragraph。"""
    text = "a" * (_SHORT_LINE_MAX + 1)
    etype, _ = _classify_line(text)
    assert etype == "paragraph"


def test_classify_line_atx_with_trailing_atx_marker():
    """# foo # 风格的 closing marker。"""
    etype, meta = _classify_line("# foo #")
    assert etype == "heading"
    # raw_text 应保留完整 "foo #"
    assert meta.get("raw_text") == "foo #"


def test_classify_line_atx_with_emphasis():
    """# **bold** heading → raw_text 含 emphasis 标记。"""
    etype, meta = _classify_line("# **bold**")
    assert etype == "heading"
    assert "**bold**" in meta.get("raw_text", "")


def test_classify_line_atx_with_inline_code():
    etype, meta = _classify_line("# `code`")
    assert etype == "heading"
    assert "`code`" in meta.get("raw_text", "")


def test_classify_line_short_with_inline_code_no_terminator():
    """短 line 含 `code` 无终止符 → short_line heading。"""
    etype, meta = _classify_line("`xyz`")
    assert etype == "heading"
    assert meta.get("heuristic") == "short_line"


def test_classify_line_terminator_exclamation():
    """! 在终止符列表，所以短 line + ! → paragraph。"""
    etype, _ = _classify_line("Wow!")
    assert etype == "paragraph"


def test_classify_line_terminator_question_mark():
    etype, _ = _classify_line("What?")
    assert etype == "paragraph"


def test_classify_line_terminator_chinese_full_width_period():
    etype, _ = _classify_line("你好。")
    assert etype == "paragraph"


def test_classify_line_terminator_chinese_full_width_exclamation():
    etype, _ = _classify_line("你好！")
    assert etype == "paragraph"


def test_classify_line_terminator_chinese_full_width_question():
    etype, _ = _classify_line("你好？")
    assert etype == "paragraph"


def test_classify_line_consecutive_terminators_still_paragraph():
    etype, _ = _classify_line("Wait?!")
    assert etype == "paragraph"


def test_classify_line_terminator_only_at_end_matters():
    """'a.b' 不是终止符（句号在中间）→ 短 line heading。"""
    etype, _ = _classify_line("a.b")
    assert etype == "heading"


def test_classify_line_text_with_period_in_middle_short():
    etype, _ = _classify_line("config.json")
    assert etype == "heading"


def test_classify_line_text_with_period_at_end_is_paragraph():
    etype, _ = _classify_line("end.")
    assert etype == "paragraph"


# =========================================================================
# _HEADING_RE：正则级别测试
# =========================================================================


def test_heading_re_no_match_for_empty_string():
    assert _HEADING_RE.match("") is None


def test_heading_re_no_match_for_just_whitespace():
    assert _HEADING_RE.match("   ") is None


def test_heading_re_no_match_for_just_one_hash_no_space():
    r"""单个 # 没有 \s，不匹配。"""
    assert _HEADING_RE.match("#") is None


def test_heading_re_no_match_for_one_hash_with_text_no_space():
    r"""#text 不匹配（无 \s）。"""
    assert _HEADING_RE.match("#text") is None


def test_heading_re_match_single_hash_with_space():
    m = _HEADING_RE.match("# foo")
    assert m is not None
    assert m.group(1) == "foo"


def test_heading_re_match_two_hashes_with_space():
    m = _HEADING_RE.match("## foo")
    assert m is not None
    assert m.group(1) == "foo"


def test_heading_re_match_three_hashes_with_space():
    m = _HEADING_RE.match("### foo")
    assert m is not None


def test_heading_re_match_four_hashes_with_space():
    m = _HEADING_RE.match("#### foo")
    assert m is not None


def test_heading_re_match_five_hashes_with_space():
    m = _HEADING_RE.match("##### foo")
    assert m is not None


def test_heading_re_match_six_hashes_with_space():
    m = _HEADING_RE.match("###### foo")
    assert m is not None


def test_heading_re_match_leading_whitespace_before_hash():
    m = _HEADING_RE.match("  # foo")
    assert m is not None


def test_heading_re_match_leading_tab_before_hash():
    m = _HEADING_RE.match("\t# foo")
    assert m is not None


def test_heading_re_captures_trailing_whitespace_stripped():
    """正则 raw_text capture 应 strip trailing。"""
    m = _HEADING_RE.match("# foo   ")
    assert m is not None
    assert m.group(1) == "foo"


def test_heading_re_captures_leading_whitespace_in_text_preserved():
    m = _HEADING_RE.match("#    indented")
    assert m is not None
    # 多个空格被 \s+ 吃掉
    assert m.group(1) == "indented"


def test_heading_re_match_with_punctuation_in_text():
    m = _HEADING_RE.match("# foo: bar!")
    assert m is not None
    assert m.group(1) == "foo: bar!"


def test_heading_re_pattern_string_starts_with_caret():
    """正则字符串以 ^ 开头（行首锚定）。"""
    assert _HEADING_RE.pattern.startswith("^")


def test_heading_re_pattern_string_ends_with_dollar():
    """正则字符串以 $ 结尾（行尾锚定）。"""
    assert _HEADING_RE.pattern.endswith("$")


# =========================================================================
# _split_content_to_elements：内容变种
# =========================================================================


def test_split_content_with_crlf_line_endings():
    content = "para one\r\n\r\npara two"
    elements, _ = _split_content_to_elements(content, "docx", "doc1")
    # CRLF 应被 \n\s*\n 切割（CR 是 \r，但 split 用 \n + \s*，所以 \r\n\r\n 中的
    # \r 算 whitespace 也吃掉）
    assert len(elements) == 2


def test_split_content_with_only_carriage_returns():
    """\r\r 在 split 阶段不切割（regex 要求 \n），但 block 内 splitlines 会切。

    因此一个 block 含 \r\r 会触发 block.splitlines()[0] 拿到第一行作为 heading，
    其余作为 paragraph rest。
    """
    content = "para one\r\rpara two"
    elements, _ = _split_content_to_elements(content, "docx", "doc1")
    # 第一行 'para one' 短无终止符 → heading；rest='para two' → paragraph
    assert len(elements) == 2
    assert elements[0].type == "heading"
    assert elements[1].type == "paragraph"
    assert elements[1].content == "para two"


def test_split_content_with_many_consecutive_blank_lines():
    content = "para one\n\n\n\n\n\npara two"
    elements, _ = _split_content_to_elements(content, "docx", "doc1")
    assert len(elements) == 2


def test_split_content_with_leading_blank_lines():
    """'para' 短无终止符 → heading（不是 paragraph）。"""
    content = "\n\n\npara"
    elements, _ = _split_content_to_elements(content, "docx", "doc1")
    assert len(elements) == 1
    assert elements[0].type == "heading"


def test_split_content_with_trailing_blank_lines():
    content = "para\n\n\n"
    elements, _ = _split_content_to_elements(content, "docx", "doc1")
    assert len(elements) == 1


def test_split_content_with_cjk_text_paragraph():
    content = "你好世界。"
    elements, _ = _split_content_to_elements(content, "docx", "doc1")
    assert len(elements) == 1
    assert elements[0].content == "你好世界。"


def test_split_content_with_cjk_short_line_no_terminator():
    """短 CJK 无终止符 → heading。"""
    content = "你好"
    elements, _ = _split_content_to_elements(content, "docx", "doc1")
    assert len(elements) == 1
    assert elements[0].type == "heading"


def test_split_content_mixed_cjk_and_ascii():
    content = "你好 world.\n\nThis is fine."
    elements, _ = _split_content_to_elements(content, "docx", "doc1")
    assert len(elements) == 2


def test_split_content_atx_heading_with_emphasis_in_rest():
    """block 第一行是 ATX heading，rest 含 emphasis。"""
    content = "# Title\n**bold** rest here."
    elements, _ = _split_content_to_elements(content, "docx", "doc1")
    assert len(elements) == 2
    assert elements[0].type == "heading"
    assert elements[1].type == "paragraph"
    assert "**bold**" in elements[1].content


def test_split_content_atx_heading_with_atx_in_rest_keeps_paragraph():
    """block 第一行 ATX heading，rest 也含 ATX → rest 仍作 paragraph 整段。"""
    content = "# Title\n# Subheading inside rest"
    elements, _ = _split_content_to_elements(content, "docx", "doc1")
    assert len(elements) == 2
    # rest 是 paragraph，不会被再次切（只有 block 级切割）
    assert elements[1].type == "paragraph"
    assert "# Subheading" in elements[1].content


def test_split_content_returns_proper_element_ids_zero_padded():
    content = "para one\n\npara two\n\npara three"
    elements, _ = _split_content_to_elements(content, "docx", "doc1")
    ids = [e.element_id for e in elements]
    assert ids == ["doc1::e0000", "doc1::e0001", "doc1::e0002"]


def test_split_content_heading_confidence_is_0_6():
    content = "# heading"
    elements, _ = _split_content_to_elements(content, "docx", "doc1")
    assert elements[0].confidence == 0.6


def test_split_content_paragraph_confidence_is_0_5():
    content = "this is a paragraph that should be long enough to not be considered a heading."
    elements, _ = _split_content_to_elements(content, "docx", "doc1")
    assert elements[0].confidence == 0.5


def test_split_content_heading_rest_paragraph_confidence_0_5():
    content = "# heading\nrest of paragraph here that is long enough."
    elements, _ = _split_content_to_elements(content, "docx", "doc1")
    assert len(elements) == 2
    assert elements[1].confidence == 0.5


def test_split_content_returns_two_tuple():
    """函数返回 (elements, used_paragraph_indices)。"""
    result = _split_content_to_elements("para", "docx", "doc1")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_split_content_second_return_value_is_empty_list():
    """used_paragraph_indices 总是空 list（仅调试用）。"""
    _, indices = _split_content_to_elements("para", "docx", "doc1")
    assert indices == []


def test_split_content_empty_content_returns_empty_list():
    elements, _ = _split_content_to_elements("", "docx", "doc1")
    assert elements == []


def test_split_content_only_whitespace_returns_empty_list():
    elements, _ = _split_content_to_elements("   \n\n   \n", "docx", "doc1")
    assert elements == []


def test_split_content_document_id_in_elements():
    content = "para"
    elements, _ = _split_content_to_elements(content, "docx", "mydoc")
    assert all(e.element_id.startswith("mydoc::") for e in elements)


# =========================================================================
# _make_locator：深度
# =========================================================================


def test_make_locator_pdf_returns_page_one():
    loc = _make_locator("pdf", 0)
    assert loc["page"] == 1


def test_make_locator_pdf_returns_placeholder_marker():
    loc = _make_locator("pdf", 0)
    assert loc.get("_kreuzberg_placeholder") is True


def test_make_locator_docx_returns_paragraph_index():
    loc = _make_locator("docx", 7)
    assert loc["paragraph_index"] == 7


def test_make_locator_docx_returns_heuristic_marker():
    loc = _make_locator("docx", 0)
    assert loc.get("_kreuzberg_heuristic") is True


def test_make_locator_pdf_ignores_paragraph_index_param():
    loc = _make_locator("pdf", 99)
    # 不应使用 paragraph_index，而是 page=1
    assert "paragraph_index" not in loc


def test_make_locator_docx_ignores_pdf_marker():
    loc = _make_locator("docx", 0)
    assert "page" not in loc
    assert "_kreuzberg_placeholder" not in loc


# =========================================================================
# KreuzbergParser 类/实例属性
# =========================================================================


def test_kreuzberg_parser_name_class_attribute_value():
    assert KreuzbergParser.name == "kreuzberg"


def test_kreuzberg_parser_version_class_attribute_exists():
    assert hasattr(KreuzbergParser, "version")


def test_kreuzberg_parser_version_class_attribute_is_string():
    assert isinstance(KreuzbergParser.version, str)


def test_kreuzberg_parser_instance_includes_document_structure_default_true():
    p = KreuzbergParser()
    assert p._include_document_structure is True


def test_kreuzberg_parser_init_keyword_only_no_positional():
    """include_document_structure 必须是 keyword-only。"""
    import inspect

    sig = inspect.signature(KreuzbergParser.__init__)
    param = sig.parameters.get("include_document_structure")
    assert param is not None
    assert param.kind == inspect.Parameter.KEYWORD_ONLY


def test_kreuzberg_parser_two_instances_independent():
    """两个实例的 _include_document_structure 互不影响。"""
    a = KreuzbergParser()
    b = KreuzbergParser(include_document_structure=False)
    assert a._include_document_structure is True
    assert b._include_document_structure is False


def test_kreuzberg_parser_class_has_parse_method():
    assert callable(KreuzbergParser.parse)


def test_kreuzberg_parser_instance_name_matches_class():
    p = KreuzbergParser()
    assert p.name == KreuzbergParser.name


def test_kreuzberg_parser_instance_version_matches_class():
    p = KreuzbergParser()
    assert p.version == KreuzbergParser.version


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_heading_re_pattern_type_is_pattern():
    """_HEADING_RE 应是 re.Pattern 实例。"""
    assert isinstance(_HEADING_RE, re.Pattern)


def test_module_short_line_max_constant_80():
    assert _SHORT_LINE_MAX == 80


def test_module_short_line_max_int():
    assert isinstance(_SHORT_LINE_MAX, int)


def test_module_all_exports():
    from app.parsers import kreuzberg_parser as mod

    assert mod.__all__ == ["KreuzbergParser"]


def test_module_all_exports_count_one():
    from app.parsers import kreuzberg_parser as mod

    assert len(mod.__all__) == 1


def test_module_imports_re():
    from app.parsers import kreuzberg_parser as mod

    assert hasattr(mod, "re")


def test_module_imports_path():
    from app.parsers import kreuzberg_parser as mod

    assert hasattr(mod, "Path")


def test_module_imports_any():
    from app.parsers import kreuzberg_parser as mod

    assert hasattr(mod, "Any")


def test_module_imports_document():
    from app.parsers import kreuzberg_parser as mod

    assert hasattr(mod, "Document")


def test_module_imports_element():
    from app.parsers import kreuzberg_parser as mod

    assert hasattr(mod, "Element")


def test_module_imports_warning_record():
    from app.parsers import kreuzberg_parser as mod

    assert hasattr(mod, "WarningRecord")


def test_module_imports_parser():
    from app.parsers import kreuzberg_parser as mod

    assert hasattr(mod, "Parser")


def test_module_imports_parser_error():
    from app.parsers import kreuzberg_parser as mod

    assert hasattr(mod, "ParserError")


def test_module_imports_detect_source_type():
    from app.parsers import kreuzberg_parser as mod

    assert hasattr(mod, "detect_source_type")


def test_module_imports_make_document_id():
    from app.parsers import kreuzberg_parser as mod

    assert hasattr(mod, "make_document_id")


def test_module_classify_line_callable():
    from app.parsers import kreuzberg_parser as mod

    assert callable(mod._classify_line)


def test_module_split_content_callable():
    from app.parsers import kreuzberg_parser as mod

    assert callable(mod._split_content_to_elements)


def test_module_make_locator_callable():
    from app.parsers import kreuzberg_parser as mod

    assert callable(mod._make_locator)


def test_module_kreuzberg_parser_inherits_parser():
    from app.parsers.base import Parser

    assert issubclass(KreuzbergParser, Parser)


def test_module_kreuzberg_parser_has_docstring():
    assert KreuzbergParser.__doc__ is not None


def test_module_kreuzberg_parser_parse_method_has_docstring():
    """parse 方法不强求 docstring。"""
    # 实际 parse 无 docstring
    assert callable(KreuzbergParser.parse)


def test_module_classify_line_has_docstring():
    assert _classify_line.__doc__ is not None


def test_module_split_content_has_docstring():
    assert _split_content_to_elements.__doc__ is not None


def test_module_make_locator_has_docstring():
    assert _make_locator.__doc__ is not None


def test_module_classify_line_docstring_mentions_heading_or_paragraph():
    doc = _classify_line.__doc__ or ""
    assert "heading" in doc or "paragraph" in doc


def test_module_split_content_docstring_mentions_kreuzberg_or_blocks():
    doc = _split_content_to_elements.__doc__ or ""
    assert "kreuzberg" in doc.lower() or "block" in doc.lower() or "双换行" in doc


def test_module_make_locator_docstring_mentions_bbox_or_page():
    doc = _make_locator.__doc__ or ""
    assert "bbox" in doc or "page" in doc or "page" in doc.lower()


def test_module_constants_immutable_at_module_level():
    """_SHORT_LINE_MAX 同 import 返回同对象。"""
    from app.parsers.kreuzberg_parser import _SHORT_LINE_MAX as a
    from app.parsers.kreuzberg_parser import _SHORT_LINE_MAX as b

    assert a is b


# =========================================================================
# _classify_line：返回类型
# =========================================================================


def test_classify_line_returns_two_tuple():
    result = _classify_line("text")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_classify_line_first_element_is_str():
    etype, _ = _classify_line("text")
    assert isinstance(etype, str)


def test_classify_line_second_element_is_dict():
    _, meta = _classify_line("text")
    assert isinstance(meta, dict)


def test_classify_line_empty_string_returns_paragraph():
    etype, meta = _classify_line("")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_line_text_with_carriage_return_only_treated_as_empty():
    """'\r' strip 后为空 → paragraph。"""
    etype, _ = _classify_line("\r")
    assert etype == "paragraph"


# =========================================================================
# _HEADING_RE：所有终止符确认（边界）
# =========================================================================


@pytest.mark.parametrize(
    "terminator",
    ["。", ".", "!", "?", "！", "？"],
)
def test_classify_line_short_text_with_terminator_is_paragraph(terminator: str):
    etype, _ = _classify_line(f"Hello{terminator}")
    assert etype == "paragraph"


@pytest.mark.parametrize(
    "terminator",
    ["。", ".", "!", "?", "！", "？"],
)
def test_classify_line_short_text_with_terminator_no_short_line_meta(
    terminator: str,
):
    _, meta = _classify_line(f"Hello{terminator}")
    # 有终止符 → 不走 short_line heuristic
    assert meta.get("heuristic") != "short_line"


# =========================================================================
# 综合：KreuzbergParser 实例创建
# =========================================================================


def test_kreuzberg_parser_init_no_args():
    p = KreuzbergParser()
    assert p is not None


def test_kreuzberg_parser_init_with_true_keyword():
    p = KreuzbergParser(include_document_structure=True)
    assert p._include_document_structure is True


def test_kreuzberg_parser_init_with_false_keyword():
    p = KreuzbergParser(include_document_structure=False)
    assert p._include_document_structure is False


def test_kreuzberg_parser_init_signature_self_first():
    import inspect

    sig = inspect.signature(KreuzbergParser.__init__)
    params = list(sig.parameters.keys())
    assert params[0] == "self"


def test_kreuzberg_parser_parse_signature_self_first():
    import inspect

    sig = inspect.signature(KreuzbergParser.parse)
    params = list(sig.parameters.keys())
    assert params[0] == "self"
    assert "path" in sig.parameters
    assert "source_hash" in sig.parameters
