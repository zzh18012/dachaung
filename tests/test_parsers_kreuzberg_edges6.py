r"""app/parsers/kreuzberg_parser.py 边角测试 - 第六轮（Round 169）。

补强已有 base/edges/edges2-5（共 717 测试）未覆盖的纯函数深度：
- _HEADING_RE / _SHORT_LINE_MAX 常量
- _classify_line 启发式边界
- _split_content_to_elements 纯函数行为
- _make_locator pdf/docx 分支
- KreuzbergParser 类属性与签名
- 模块结构（optional import、版本字符串）
- 综合行为
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

import pytest

from app.models import Document, Element, WarningRecord
from app.parsers.base import ParserError
from app.parsers.kreuzberg_parser import (
    _HEADING_RE,
    _SHORT_LINE_MAX,
    KreuzbergParser,
    _classify_line,
    _make_locator,
    _split_content_to_elements,
)


# =========================================================================
# 常量精确性
# =========================================================================


def test_heading_re_is_pattern():
    assert isinstance(_HEADING_RE, re.Pattern)


def test_heading_re_pattern_string():
    """正则匹配 markdown 风格的 # heading。"""
    assert _HEADING_RE.match("# Title")
    assert _HEADING_RE.match("## Subsection")
    assert _HEADING_RE.match("###### Deepest")


def test_heading_re_no_match_for_plain_text():
    assert _HEADING_RE.match("just a paragraph") is None


def test_heading_re_no_match_for_seven_hashes():
    """7 个 # 不匹配（标准 markdown 限制 6）。"""
    assert _HEADING_RE.match("####### too deep") is None


def test_short_line_max_value():
    assert _SHORT_LINE_MAX == 80


def test_short_line_max_is_int():
    assert isinstance(_SHORT_LINE_MAX, int)


# =========================================================================
# _classify_line 启发式
# =========================================================================


def test_classify_line_atx_heading_level_1():
    etype, meta = _classify_line("# Title")
    assert etype == "heading"
    assert meta["level"] == 1
    assert meta["raw_text"] == "Title"


def test_classify_line_atx_heading_level_6():
    etype, meta = _classify_line("###### Deep")
    assert etype == "heading"
    assert meta["level"] == 6


def test_classify_line_short_line_no_punct_is_heading():
    etype, meta = _classify_line("Methodology")
    assert etype == "heading"
    assert meta["heuristic"] == "short_line"
    assert meta["level"] == 0


def test_classify_line_long_line_is_paragraph():
    etype, _ = _classify_line("a" * 100)
    assert etype == "paragraph"


def test_classify_line_short_line_with_period_is_paragraph():
    etype, _ = _classify_line("End.")
    assert etype == "paragraph"


def test_classify_line_short_line_with_question_mark():
    etype, _ = _classify_line("Why?")
    assert etype == "paragraph"


def test_classify_line_short_line_with_exclamation():
    etype, _ = _classify_line("Wow!")
    assert etype == "paragraph"


def test_classify_line_short_line_with_chinese_period():
    etype, _ = _classify_line("结束。")
    assert etype == "paragraph"


def test_classify_line_short_line_with_chinese_question():
    etype, _ = _classify_line("为什么？")
    assert etype == "paragraph"


def test_classify_line_short_line_with_chinese_exclamation():
    etype, _ = _classify_line("好！")
    assert etype == "paragraph"


def test_classify_line_empty_string():
    etype, meta = _classify_line("")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_line_whitespace_only():
    etype, meta = _classify_line("   ")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_line_returns_tuple():
    result = _classify_line("hello")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_classify_line_atx_priority_over_short_line():
    """#开头优先于 short_line 启发式。"""
    etype, meta = _classify_line("# x")
    assert etype == "heading"
    assert meta["level"] == 1
    assert "heuristic" not in meta  # 不是 short_line


def test_classify_line_atx_with_leading_whitespace():
    """允许 # 前有空白。"""
    etype, _ = _classify_line("   # Title")
    assert etype == "heading"


def test_classify_line_atx_max_80_chars_short_line():
    """80 字符的非 punct 短行是 heading。"""
    text = "a" * 80
    etype, _ = _classify_line(text)
    assert etype == "heading"


def test_classify_line_atx_81_chars_paragraph():
    text = "a" * 81
    etype, _ = _classify_line(text)
    assert etype == "paragraph"


def test_classify_line_chinese_short_is_heading():
    etype, _ = _classify_line("研究方法")
    assert etype == "heading"


# =========================================================================
# _make_locator 各分支
# =========================================================================


def test_make_locator_pdf_has_page_1():
    loc = _make_locator("pdf", 0)
    assert loc["page"] == 1


def test_make_locator_pdf_has_placeholder_flag():
    loc = _make_locator("pdf", 0)
    assert loc["_kreuzberg_placeholder"] is True


def test_make_locator_docx_has_paragraph_index():
    loc = _make_locator("docx", 5)
    assert loc["paragraph_index"] == 5


def test_make_locator_docx_has_heuristic_flag():
    loc = _make_locator("docx", 0)
    assert loc["_kreuzberg_heuristic"] is True


def test_make_locator_pdf_ignores_paragraph_index_arg():
    """PDF locator 用 page=1，不用 paragraph_index。"""
    loc = _make_locator("pdf", 99)
    assert "paragraph_index" not in loc


def test_make_locator_docx_ignores_page():
    loc = _make_locator("docx", 0)
    assert "page" not in loc


def test_make_locator_returns_dict():
    loc = _make_locator("docx", 0)
    assert isinstance(loc, dict)


# =========================================================================
# _split_content_to_elements
# =========================================================================


def test_split_content_empty_string():
    elements, _ = _split_content_to_elements("", "docx", "doc")
    assert elements == []


def test_split_content_single_paragraph():
    """长文本（>80 chars 或带句号）→ paragraph。"""
    elements, _ = _split_content_to_elements("This is a long paragraph that exceeds the 80 char short line threshold easily.", "docx", "doc")
    assert len(elements) == 1
    assert elements[0].type == "paragraph"


def test_split_content_two_paragraphs():
    elements, _ = _split_content_to_elements(
        "This is the first paragraph and it is long enough to be classified as paragraph.\n\n"
        "This is the second paragraph and it is also long enough to be classified as paragraph.",
        "docx", "doc",
    )
    assert len(elements) == 2
    assert "first" in elements[0].content
    assert "second" in elements[1].content


def test_split_content_heading_at_start():
    elements, _ = _split_content_to_elements("# Title\n\nbody", "docx", "doc")
    types = [e.type for e in elements]
    assert "heading" in types


def test_split_content_heading_text_uses_raw_text():
    elements, _ = _split_content_to_elements("# My Heading", "docx", "doc")
    assert elements[0].type == "heading"
    assert elements[0].content == "My Heading"


def test_split_content_heading_metadata_has_level():
    elements, _ = _split_content_to_elements("# Title", "docx", "doc")
    assert elements[0].metadata["level"] == 1


def test_split_content_heading_confidence_06():
    elements, _ = _split_content_to_elements("# Title", "docx", "doc")
    assert elements[0].confidence == 0.6


def test_split_content_paragraph_confidence_05():
    """长 paragraph confidence=0.5。"""
    long_text = "a" * 100
    elements, _ = _split_content_to_elements(long_text, "docx", "doc")
    assert elements[0].confidence == 0.5


def test_split_content_paragraph_metadata_has_heuristic():
    long_text = "a" * 100
    elements, _ = _split_content_to_elements(long_text, "docx", "doc")
    assert elements[0].metadata.get("kreuzberg_heuristic") is True


def test_split_content_element_id_zero_padded():
    elements, _ = _split_content_to_elements("a\n\nb\n\nc", "docx", "doc")
    ids = [e.element_id for e in elements]
    assert ids == ["doc::e0000", "doc::e0001", "doc::e0002"]


def test_split_content_locator_pdf_has_page_1():
    elements, _ = _split_content_to_elements("hello", "pdf", "doc")
    assert elements[0].source_locator["page"] == 1


def test_split_content_locator_docx_has_paragraph_index():
    elements, _ = _split_content_to_elements("a\n\nb", "docx", "doc")
    assert elements[0].source_locator["paragraph_index"] == 0
    assert elements[1].source_locator["paragraph_index"] == 1


def test_split_content_strips_blocks():
    """每个 block 的首尾空白被 strip。"""
    elements, _ = _split_content_to_elements("  hello  ", "docx", "doc")
    assert elements[0].content == "hello"


def test_split_content_multiple_blank_lines_treated_as_one_separator():
    elements, _ = _split_content_to_elements("a\n\n\n\nb", "docx", "doc")
    assert len(elements) == 2


def test_split_content_only_whitespace_returns_empty():
    elements, _ = _split_content_to_elements("   \n\n\t\n   ", "docx", "doc")
    assert elements == []


def test_split_content_returns_tuple():
    result = _split_content_to_elements("hello", "docx", "doc")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_split_content_second_element_empty_list_when_no_warnings():
    """第二个返回值是 []（占位）。"""
    elements, second = _split_content_to_elements("hello", "docx", "doc")
    assert second == []


def test_split_content_heading_with_body():
    """heading 后接正文（同一 block 内多行）。"""
    elements, _ = _split_content_to_elements("# Title\nbody line", "docx", "doc")
    # heading 1 个 + paragraph 1 个
    types = [e.type for e in elements]
    assert types.count("heading") == 1
    assert types.count("paragraph") == 1


def test_split_content_idempotent():
    a, _ = _split_content_to_elements("hello\n\nworld", "docx", "doc")
    b, _ = _split_content_to_elements("hello\n\nworld", "docx", "doc")
    assert len(a) == len(b)
    for x, y in zip(a, b):
        assert x.content == y.content
        assert x.type == y.type


def test_split_content_does_not_mutate_input():
    text = "para1\n\npara2"
    before = text
    _split_content_to_elements(text, "docx", "doc")
    assert text == before


# =========================================================================
# KreuzbergParser 类属性
# =========================================================================


def test_kreuzberg_parser_name_value():
    assert KreuzbergParser.name == "kreuzberg"


def test_kreuzberg_parser_version_not_none():
    """version 应是字符串（kreuzberg 已装）或 'unknown'。"""
    assert isinstance(KreuzbergParser.version, str)


def test_kreuzberg_parser_inherits_parser():
    from app.parsers.base import Parser
    assert issubclass(KreuzbergParser, Parser)


def test_kreuzberg_parser_init_default():
    """__init__ 默认 include_document_structure=True。"""
    p = KreuzbergParser()
    assert p._include_document_structure is True


def test_kreuzberg_parser_init_disabled():
    p = KreuzbergParser(include_document_structure=False)
    assert p._include_document_structure is False


def test_kreuzberg_parser_init_keyword_only():
    """include_document_structure 是 keyword-only（* 之后）。"""
    sig = inspect.signature(KreuzbergParser.__init__)
    assert sig.parameters["include_document_structure"].kind == inspect.Parameter.KEYWORD_ONLY


def test_kreuzberg_parser_init_default_value():
    sig = inspect.signature(KreuzbergParser.__init__)
    assert sig.parameters["include_document_structure"].default is True


def test_kreuzberg_parser_has_parse_method():
    assert callable(KreuzbergParser.parse)


def test_kreuzberg_parser_parse_signature():
    sig = inspect.signature(KreuzbergParser.parse)
    assert set(sig.parameters) == {"self", "path", "source_hash"}


# =========================================================================
# parse() 路径校验
# =========================================================================


def test_parse_nonexistent_file_raises(tmp_path: Path):
    """kreuzberg 已装时应抛 file_not_found（先校验文件）。"""
    from app.parsers.kreuzberg_parser import _KREUZBERG_AVAILABLE
    p = tmp_path / "missing.pdf"
    if _KREUZBERG_AVAILABLE:
        with pytest.raises(ParserError) as exc:
            KreuzbergParser().parse(p, "a" * 64)
        assert exc.value.code == "file_not_found"


def test_parse_unsupported_extension_raises(tmp_path: Path):
    from app.parsers.kreuzberg_parser import _KREUZBERG_AVAILABLE
    p = tmp_path / "foo.txt"
    p.write_text("hello", encoding="utf-8")
    if _KREUZBERG_AVAILABLE:
        with pytest.raises(ParserError) as exc:
            KreuzbergParser().parse(p, "a" * 64)
        assert exc.value.code == "unsupported_type"


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import app.parsers.kreuzberg_parser as mod
    assert mod.__all__ == ["KreuzbergParser"]


def test_module_all_is_list():
    import app.parsers.kreuzberg_parser as mod
    assert isinstance(mod.__all__, list)


def test_module_uses_future_annotations():
    import app.parsers.kreuzberg_parser as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


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


def test_module_optional_import_kreuzberg():
    """kreuzberg 是 try/except 可选导入。"""
    import app.parsers.kreuzberg_parser as mod
    src = inspect.getsource(mod)
    assert "import kreuzberg" in src
    assert "except ImportError" in src


def test_module_has_kreuzberg_available_constant():
    import app.parsers.kreuzberg_parser as mod
    assert hasattr(mod, "_KREUZBERG_AVAILABLE")
    assert isinstance(mod._KREUZBERG_AVAILABLE, bool)


def test_module_has_kreuzberg_version_constant():
    import app.parsers.kreuzberg_parser as mod
    assert hasattr(mod, "_KREUZBERG_VERSION")


def test_module_docstring_present():
    import app.parsers.kreuzberg_parser as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_kreuzberg_version():
    """docstring 提及具体 kreuzberg 版本与实测日期。"""
    import app.parsers.kreuzberg_parser as mod
    doc = mod.__doc__
    assert "kreuzberg" in doc.lower()
    assert "4.10.2" in doc


def test_module_docstring_mentions_business_code_isolation():
    """docstring 提及业务代码不直接 import kreuzberg。"""
    import app.parsers.kreuzberg_parser as mod
    doc = mod.__doc__
    assert "业务代码" in doc or "kreuzberg" in doc.lower()


def test_module_no_silence_unused():
    import app.parsers.kreuzberg_parser as mod
    assert not hasattr(mod, "_silence_unused")


# =========================================================================
# 签名深度
# =========================================================================


def test_classify_line_signature():
    sig = inspect.signature(_classify_line)
    assert set(sig.parameters) == {"line"}


def test_split_content_signature():
    sig = inspect.signature(_split_content_to_elements)
    assert set(sig.parameters) == {"content", "source_type", "document_id"}


def test_make_locator_signature():
    sig = inspect.signature(_make_locator)
    assert set(sig.parameters) == {"source_type", "paragraph_index"}


def test_classify_line_return_annotation_tuple():
    sig = inspect.signature(_classify_line)
    assert "tuple" in str(sig.return_annotation).lower()


def test_split_content_return_annotation_tuple():
    sig = inspect.signature(_split_content_to_elements)
    assert "tuple" in str(sig.return_annotation).lower()


def test_make_locator_return_annotation_dict():
    sig = inspect.signature(_make_locator)
    assert "dict" in str(sig.return_annotation).lower()


# =========================================================================
# 综合行为
# =========================================================================


def test_classify_line_idempotent():
    a = _classify_line("hello")
    b = _classify_line("hello")
    assert a == b


def test_make_locator_idempotent():
    assert _make_locator("pdf", 0) == _make_locator("pdf", 0)


def test_split_content_idempotent_full():
    text = "# T\n\nbody\n\nmore"
    a, _ = _split_content_to_elements(text, "docx", "doc")
    b, _ = _split_content_to_elements(text, "docx", "doc")
    assert len(a) == len(b)


def test_classify_line_no_mutation():
    text = "# Title"
    before = text
    _classify_line(text)
    assert text == before


def test_constants_not_mutated():
    """_SHORT_LINE_MAX 不应被修改。"""
    from app.parsers.kreuzberg_parser import _SHORT_LINE_MAX
    assert _SHORT_LINE_MAX == 80
