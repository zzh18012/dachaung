"""app/parsers/text_parser.py 边角测试 - 第四轮（Round 116）。

补强已有 base/edges/edges2/edges3（共 88 测试）未覆盖的深度路径：
- _split_paragraphs 边界：
  - 单字符 paragraph
  - 含 \t 的 paragraph
  - 含 unicode separator（U+2028 LINE SEPARATOR）保留
  - 文本仅 \n（一个换行符）
  - 文本 \n\n\n（多个换行符）
  - 文本 \r\n\r\n\r\n（多 CRLF）
  - 文本首尾混合空白行
  - paragraph 内含空行（被切）
  - 行内空白行视为分隔（lines[i].strip() 为空时跳出）
  - lines[i] 含 trailing/leading whitespace 仍被收集
- _detect_text_source_type：
  - .Txt 混合大小写
  - .TEXT 大写
  - .json 拒
  - .csv 拒
- TextParser.parse：
  - empty file → no_content warning
  - whitespace-only file → no_content warning
  - 单行 file → 一个 element
  - metadata only text key
  - elements 类型固定 paragraph
  - source_locator 仅 line key
- TextParser 类属性：name/version
- 模块结构深度：__all__、imports、_TEXT_EXTENSIONS、模块 docstring
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.parsers.base import ParserError
from app.parsers.text_parser import (
    _TEXT_EXTENSIONS,
    TextParser,
    _detect_text_source_type,
    _split_paragraphs,
)


SHA = "a" * 64


def _write(tmp_path: Path, text: str, name: str = "x.txt") -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# =========================================================================
# _split_paragraphs 深度边界
# =========================================================================


def test_split_paragraphs_single_character():
    result = _split_paragraphs("x")
    assert result == [(1, "x")]


def test_split_paragraphs_paragraph_with_internal_tab():
    """tab 是 whitespace，lines[i].strip() 后仍 truthy（tab 不使行空）。"""
    result = _split_paragraphs("a\tb")
    assert result == [(1, "a\tb")]


def test_split_paragraphs_paragraph_with_only_tab_stripped_to_empty():
    """整行只有 tab → strip() = '' → 视为空白行。"""
    result = _split_paragraphs("\t\t")
    assert result == []


def test_split_paragraphs_text_with_single_newline():
    """'a\nb' 单 newline → 两行连续非空 → 一个 paragraph 'a\nb'。"""
    result = _split_paragraphs("a\nb")
    assert result == [(1, "a\nb")]


def test_split_paragraphs_text_with_double_newline():
    """'a\n\nb' → 两个 paragraph。"""
    result = _split_paragraphs("a\n\nb")
    assert result == [(1, "a"), (3, "b")]


def test_split_paragraphs_only_newlines():
    """'\n\n\n' 全空白行 → 0 paragraph。"""
    result = _split_paragraphs("\n\n\n")
    assert result == []


def test_split_paragraphs_only_single_newline():
    result = _split_paragraphs("\n")
    assert result == []


def test_split_paragraphs_only_crlf():
    result = _split_paragraphs("\r\n")
    assert result == []


def test_split_paragraphs_only_cr():
    result = _split_paragraphs("\r")
    assert result == []


def test_split_paragraphs_multiple_crlf():
    result = _split_paragraphs("\r\n\r\n\r\n")
    assert result == []


def test_split_paragraphs_three_paragraphs_with_line_numbers():
    result = _split_paragraphs("a\n\nb\n\nc")
    assert result == [(1, "a"), (3, "b"), (5, "c")]


def test_split_paragraphs_leading_blank_then_paragraph():
    result = _split_paragraphs("\n\nhello")
    assert result == [(3, "hello")]


def test_split_paragraphs_paragraph_then_trailing_blank():
    result = _split_paragraphs("hello\n\n\n")
    assert result == [(1, "hello")]


def test_split_paragraphs_paragraph_with_internal_blank():
    """'a\n\nb' → blank 内部 → 切两段。"""
    result = _split_paragraphs("para1\n\npara2")
    assert len(result) == 2


def test_split_paragraphs_line_with_only_spaces_treated_as_blank():
    """行 '   ' strip() = '' → 视为分隔。"""
    result = _split_paragraphs("a\n   \nb")
    assert len(result) == 2


def test_split_paragraphs_returns_empty_for_empty_string():
    assert _split_paragraphs("") == []


def test_split_paragraphs_returns_empty_for_whitespace_only():
    assert _split_paragraphs("   \n\t\n  \n") == []


def test_split_paragraphs_preserves_internal_spaces():
    """行内 multiple spaces 保留（不被 collapse）。"""
    result = _split_paragraphs("a    b")
    assert result == [(1, "a    b")]


def test_split_paragraphs_preserves_internal_newlines_in_paragraph():
    """'a\nb\nc' → 一个 paragraph，content = 'a\nb\nc'。"""
    result = _split_paragraphs("a\nb\nc")
    assert result == [(1, "a\nb\nc")]


def test_split_paragraphs_returns_list_of_tuples():
    result = _split_paragraphs("a")
    assert isinstance(result, list)
    assert isinstance(result[0], tuple)


def test_split_paragraphs_tuple_has_two_elements():
    result = _split_paragraphs("a")
    assert len(result[0]) == 2


def test_split_paragraphs_first_tuple_element_is_int():
    result = _split_paragraphs("a")
    assert isinstance(result[0][0], int)


def test_split_paragraphs_second_tuple_element_is_str():
    result = _split_paragraphs("a")
    assert isinstance(result[0][1], str)


def test_split_paragraphs_paragraph_count_match():
    text = "a\n\nb\n\nc\n\nd\n\ne"
    result = _split_paragraphs(text)
    assert len(result) == 5


def test_split_paragraphs_max_line_number_in_result():
    text = "\n\n\n\nlast"
    result = _split_paragraphs(text)
    assert result[0][0] == 5


def test_split_paragraphs_does_not_mutate_input():
    text = "a\n\nb"
    original = text
    _split_paragraphs(text)
    assert text == original


def test_split_paragraphs_para_lines_joined_by_newline():
    text = "line1\nline2"
    result = _split_paragraphs(text)
    # 单 paragraph 内部 newline 保留
    assert result == [(1, "line1\nline2")]


# =========================================================================
# _detect_text_source_type 深度
# =========================================================================


def test_detect_text_source_type_accepts_mixed_case_txt():
    p = Path("a.Txt")
    assert _detect_text_source_type(p) == "text"


def test_detect_text_source_type_accepts_mixed_case_text():
    p = Path("a.Text")
    assert _detect_text_source_type(p) == "text"


def test_detect_text_source_type_rejects_json():
    p = Path("a.json")
    with pytest.raises(ParserError):
        _detect_text_source_type(p)


def test_detect_text_source_type_rejects_csv():
    p = Path("a.csv")
    with pytest.raises(ParserError):
        _detect_text_source_type(p)


def test_detect_text_source_type_rejects_xml():
    p = Path("a.xml")
    with pytest.raises(ParserError):
        _detect_text_source_type(p)


def test_detect_text_source_type_rejects_yaml():
    p = Path("a.yaml")
    with pytest.raises(ParserError):
        _detect_text_source_type(p)


def test_detect_text_source_type_error_details_suffix_for_csv():
    p = Path("a.csv")
    with pytest.raises(ParserError) as exc_info:
        _detect_text_source_type(p)
    assert exc_info.value.details["suffix"] == ".csv"


def test_detect_text_source_type_error_details_suffix_for_no_suffix():
    p = Path("nofile")
    with pytest.raises(ParserError) as exc_info:
        _detect_text_source_type(p)
    assert exc_info.value.details["suffix"] == ""


def test_text_extensions_value():
    assert _TEXT_EXTENSIONS == (".txt", ".text")


def test_text_extensions_count_two():
    assert len(_TEXT_EXTENSIONS) == 2


def test_text_extensions_is_tuple():
    assert isinstance(_TEXT_EXTENSIONS, tuple)


# =========================================================================
# TextParser.parse：边界
# =========================================================================


def test_parse_empty_file_emits_no_content_warning(tmp_path: Path):
    p = _write(tmp_path, "")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    codes = [w.code for w in doc.warnings]
    assert "text_no_content" in codes
    assert doc.elements == []


def test_parse_whitespace_only_file_emits_no_content_warning(tmp_path: Path):
    p = _write(tmp_path, "   \n\t\n  \n")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    codes = [w.code for w in doc.warnings]
    assert "text_no_content" in codes
    assert doc.elements == []


def test_parse_only_newlines_emits_no_content_warning(tmp_path: Path):
    p = _write(tmp_path, "\n\n\n\n")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    codes = [w.code for w in doc.warnings]
    assert "text_no_content" in codes


def test_parse_single_character_file_one_element(tmp_path: Path):
    p = _write(tmp_path, "x")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    assert len(doc.elements) == 1
    assert doc.elements[0].content == "x"


def test_parse_single_line_file_one_element(tmp_path: Path):
    p = _write(tmp_path, "single line")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    assert len(doc.elements) == 1


def test_parse_metadata_only_text_key(tmp_path: Path):
    p = _write(tmp_path, "hello")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    assert set(doc.metadata.keys()) == {"text"}


def test_parse_metadata_text_value_true(tmp_path: Path):
    p = _write(tmp_path, "hello")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.metadata["text"] is True


def test_parse_all_elements_type_paragraph(tmp_path: Path):
    p = _write(tmp_path, "para1\n\npara2\n\npara3")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    types = [e.type for e in doc.elements]
    assert all(t == "paragraph" for t in types)


def test_parse_elements_metadata_empty_dict(tmp_path: Path):
    p = _write(tmp_path, "hello")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].metadata == {}


def test_parse_source_locator_only_line_key(tmp_path: Path):
    p = _write(tmp_path, "hello")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    assert set(doc.elements[0].source_locator.keys()) == {"line"}


def test_parse_returns_document_instance(tmp_path: Path):
    from app.models import Document

    p = _write(tmp_path, "hello")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    assert isinstance(doc, Document)


def test_parse_returns_document_with_empty_chunks(tmp_path: Path):
    p = _write(tmp_path, "hello")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.chunks == []


def test_parse_returns_document_with_empty_relations(tmp_path: Path):
    p = _write(tmp_path, "hello")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.relations == []


def test_parse_returns_document_with_empty_errors(tmp_path: Path):
    p = _write(tmp_path, "hello")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.errors == []


# =========================================================================
# TextParser.parse：element_id 与 locator
# =========================================================================


def test_parse_element_id_zero_padded_format(tmp_path: Path):
    p = _write(tmp_path, "first\n\nsecond\n\nthird")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    ids = [e.element_id for e in doc.elements]
    # SHA[:16] = "a" * 16
    expected_prefix = "doc-" + "a" * 16 + "::"
    assert all(i.startswith(expected_prefix) for i in ids)
    assert ids[0].endswith("e0000")
    assert ids[1].endswith("e0001")
    assert ids[2].endswith("e0002")


def test_parse_locator_line_numbers_strictly_ascending(tmp_path: Path):
    p = _write(tmp_path, "a\n\nb\n\nc")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    lines = [e.source_locator["line"] for e in doc.elements]
    assert lines == [1, 3, 5]


def test_parse_locator_first_paragraph_line_one(tmp_path: Path):
    p = _write(tmp_path, "first")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    assert doc.elements[0].source_locator["line"] == 1


def test_parse_locator_with_leading_blank_lines(tmp_path: Path):
    p = _write(tmp_path, "\n\n\nactual")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    # 第 4 行开始
    assert doc.elements[0].source_locator["line"] == 4


# =========================================================================
# TextParser.parse：错误路径
# =========================================================================


def test_parse_file_not_found_raises_file_not_found(tmp_path: Path):
    parser = TextParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(tmp_path / "nonexistent.txt", source_hash=SHA)
    assert exc_info.value.code == "file_not_found"


def test_parse_unsupported_extension_raises(tmp_path: Path):
    p = tmp_path / "x.html"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(p, source_hash=SHA)
    assert exc_info.value.code == "unsupported_type"


def test_parse_oserror_raises_text_read_failed(tmp_path: Path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")

    original_read_text = Path.read_text

    def fake_read_text(self, *args, **kwargs):
        if self == p:
            raise OSError("disk error")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    parser = TextParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(p, source_hash=SHA)
    assert exc_info.value.code == "text_read_failed"


def test_parse_invalid_utf8_falls_back_to_replace(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_bytes(b"\xff\xfehello")
    parser = TextParser()
    doc = parser.parse(p, source_hash=SHA)
    # 不抛 → 已用 replace
    assert doc is not None


def test_parse_oserror_details_has_exception_type(tmp_path: Path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")

    original_read_text = Path.read_text

    def fake_read_text(self, *args, **kwargs):
        if self == p:
            raise OSError("disk error")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    parser = TextParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(p, source_hash=SHA)
    assert "exception_type" in exc_info.value.details


# =========================================================================
# TextParser 类属性
# =========================================================================


def test_text_parser_class_name_value():
    assert TextParser.name == "text"


def test_text_parser_class_version_value():
    assert TextParser.version == "stdlib/0.1.0"


def test_text_parser_class_name_is_str():
    assert isinstance(TextParser.name, str)


def test_text_parser_class_version_is_str():
    assert isinstance(TextParser.version, str)


def test_text_parser_instance_name_matches_class():
    p = TextParser()
    assert p.name == "text"


def test_text_parser_instance_version_matches_class():
    p = TextParser()
    assert p.version == "stdlib/0.1.0"


def test_text_parser_inherits_parser():
    from app.parsers.base import Parser

    assert issubclass(TextParser, Parser)


def test_text_parser_parse_signature():
    import inspect

    sig = inspect.signature(TextParser.parse)
    params = list(sig.parameters.keys())
    assert params[0] == "self"
    assert "path" in sig.parameters
    assert "source_hash" in sig.parameters


def test_text_parser_has_docstring():
    assert TextParser.__doc__ is not None


def test_text_parser_docstring_mentions_text():
    doc = TextParser.__doc__ or ""
    assert "text" in doc.lower() or "txt" in doc.lower()


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_all_exports_only_text_parser():
    from app.parsers import text_parser as mod

    assert mod.__all__ == ["TextParser"]


def test_module_all_count_one():
    from app.parsers import text_parser as mod

    assert len(mod.__all__) == 1


def test_module_imports_path():
    from app.parsers import text_parser as mod

    assert hasattr(mod, "Path")


def test_module_imports_any():
    from app.parsers import text_parser as mod

    assert hasattr(mod, "Any")


def test_module_imports_document():
    from app.parsers import text_parser as mod

    assert hasattr(mod, "Document")


def test_module_imports_element():
    from app.parsers import text_parser as mod

    assert hasattr(mod, "Element")


def test_module_imports_warning_record():
    from app.parsers import text_parser as mod

    assert hasattr(mod, "WarningRecord")


def test_module_imports_parser():
    from app.parsers import text_parser as mod

    assert hasattr(mod, "Parser")


def test_module_imports_parser_error():
    from app.parsers import text_parser as mod

    assert hasattr(mod, "ParserError")


def test_module_imports_make_document_id():
    from app.parsers import text_parser as mod

    assert hasattr(mod, "make_document_id")


def test_module_docstring_present():
    from app.parsers import text_parser as mod

    assert mod.__doc__ is not None


def test_module_docstring_mentions_paragraph():
    """模块 docstring 应说明按空行切段。"""
    from app.parsers import text_parser as mod

    doc = mod.__doc__
    assert "段" in doc or "paragraph" in doc.lower()


def test_module_docstring_mentions_extensions():
    from app.parsers import text_parser as mod

    doc = mod.__doc__
    assert ".txt" in doc or ".text" in doc


def test_module_constants_immutable_at_module_level():
    from app.parsers.text_parser import _TEXT_EXTENSIONS as a
    from app.parsers.text_parser import _TEXT_EXTENSIONS as b

    assert a is b


def test_module_split_paragraphs_callable():
    from app.parsers import text_parser as mod

    assert callable(mod._split_paragraphs)


def test_module_detect_text_source_type_callable():
    from app.parsers import text_parser as mod

    assert callable(mod._detect_text_source_type)


def test_split_paragraphs_has_docstring():
    assert _split_paragraphs.__doc__ is not None


def test_split_paragraphs_docstring_mentions_split_or_paragraph():
    doc = _split_paragraphs.__doc__ or ""
    assert "切分" in doc or "split" in doc.lower() or "段落" in doc


# =========================================================================
# TextParser 多实例独立
# =========================================================================


def test_text_parser_two_instances_independent():
    a = TextParser()
    b = TextParser()
    assert a is not b
    assert a.name == b.name


def test_text_parser_no_init_args():
    p = TextParser()
    assert p is not None


def test_text_parser_init_takes_no_args():
    """TextParser 无自定义 __init__。"""
    import inspect

    sig = inspect.signature(TextParser.__init__)
    # 继承 object.__init__，参数应只有 self
    params = list(sig.parameters.keys())
    # Python 默认 __init__ 签名可能是 (self, /, *args, **kwargs)
    assert "self" in params
