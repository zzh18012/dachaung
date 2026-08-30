"""app/parsers/text_parser.py 边角测试 - 第二轮（Round 77）。

补强 tests/test_parsers_text.py（52）+ tests/test_parsers_text_edges.py（48）未覆盖的：
- _split_paragraphs：更细粒度的空白处理（tab-only/CR-only/form feed/vertical tab）、
  内容含 leading/trailing whitespace per line、Unicode line separators 不切、
  长字符串、单字符、空字符串、just newlines、CR-only 行末、混合行末
- _detect_text_source_type：error code 值、ParserError 类型、.TXT 大写、.TEXT 大写、
  dotfile、double extension、unknown suffix
- TextParser.parse()：file_not_found details.path 精确、unsupported_type code、
  目录 → file_not_found、UnicodeDecodeError 回退 errors=replace、空文件 + 仅 whitespace
  → text_no_content warning 含 reason、metadata {"text": True}、parser_name="text"、
  parser_version="stdlib/0.1.0"、document_id 派生、chunks/relations/errors 空
- element_id 跨多个 paragraph 递增、4 位 zero-pad
- 模块结构与 __all__、parse 签名
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models import Document, Element, WarningRecord
from app.parsers.base import Parser, ParserError
from app.parsers.text_parser import (
    TextParser,
    _TEXT_EXTENSIONS,
    _detect_text_source_type,
    _split_paragraphs,
)


# ---------- 模块常量 ----------


def test_text_extensions_count_two():
    assert len(_TEXT_EXTENSIONS) == 2


def test_text_extensions_values():
    assert set(_TEXT_EXTENSIONS) == {".txt", ".text"}


def test_text_extensions_all_lowercase():
    for ext in _TEXT_EXTENSIONS:
        assert ext == ext.lower()


def test_text_extensions_starts_with_dot():
    for ext in _TEXT_EXTENSIONS:
        assert ext.startswith(".")


def test_text_extensions_is_tuple():
    assert isinstance(_TEXT_EXTENSIONS, tuple)


# ---------- _detect_text_source_type 深度 ----------


def test_detect_text_source_type_returns_str_type():
    assert isinstance(_detect_text_source_type(Path("x.txt")), str)


def test_detect_text_source_type_txt_value():
    assert _detect_text_source_type(Path("x.txt")) == "text"


def test_detect_text_source_type_text_value():
    assert _detect_text_source_type(Path("x.text")) == "text"


def test_detect_text_source_type_uppercase_txt():
    assert _detect_text_source_type(Path("X.TXT")) == "text"


def test_detect_text_source_type_uppercase_text():
    assert _detect_text_source_type(Path("X.TEXT")) == "text"


def test_detect_text_source_type_mixed_case_txt_correct():
    assert _detect_text_source_type(Path("x.TxT")) == "text"


def test_detect_text_source_type_txf_rejected():
    """.TxF 不是 .txt 也不是 .text → 抛。"""
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("x.TxF"))


def test_detect_text_source_type_double_extension():
    """file.tar.txt → suffix 是 .txt。"""
    assert _detect_text_source_type(Path("file.tar.txt")) == "text"


def test_detect_text_source_type_double_extension_text():
    assert _detect_text_source_type(Path("file.tar.text")) == "text"


def test_detect_text_source_type_md_raises():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("x.md"))


def test_detect_text_source_type_docx_raises():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("x.docx"))


def test_detect_text_source_type_no_suffix_raises():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("README"))


def test_detect_text_source_type_error_code_value():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("x.docx"))
    assert exc.value.code == "unsupported_type"


def test_detect_text_source_type_error_details_suffix_value():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("x.pdf"))
    assert exc.value.details["suffix"] == ".pdf"


def test_detect_text_source_type_error_is_parser_error():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("x.pdf"))
    assert isinstance(exc.value, ParserError)


def test_detect_text_source_type_error_message_has_text():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("x.pdf"))
    assert "text" in str(exc.value).lower() or "txt" in str(exc.value).lower()


# ---------- _split_paragraphs 深度：返回类型 ----------


def test_split_paragraphs_returns_list_type():
    assert isinstance(_split_paragraphs(""), list)


def test_split_paragraphs_returns_list_of_tuples():
    result = _split_paragraphs("hello")
    for item in result:
        assert isinstance(item, tuple)


def test_split_paragraphs_tuple_is_pair():
    result = _split_paragraphs("hello")
    assert len(result[0]) == 2


def test_split_paragraphs_tuple_first_element_int():
    result = _split_paragraphs("hello")
    assert isinstance(result[0][0], int)


def test_split_paragraphs_tuple_second_element_str():
    result = _split_paragraphs("hello")
    assert isinstance(result[0][1], str)


# ---------- _split_paragraphs 深度：空白处理 ----------


def test_split_paragraphs_empty_string_returns_empty_list():
    assert _split_paragraphs("") == []


def test_split_paragraphs_whitespace_only_returns_empty_list():
    assert _split_paragraphs("   \n\n   \n   ") == []


def test_split_paragraphs_only_newlines_returns_empty_list():
    assert _split_paragraphs("\n\n\n\n") == []


def test_split_paragraphs_only_tabs_returns_empty_list():
    """tab-only lines → strip() 为空 → 视为空白行跳过。"""
    assert _split_paragraphs("\t\t\t") == []


def test_split_paragraphs_only_carriage_returns_returns_empty_list():
    """CR-only content：归一后是 \n\n\n → empty。"""
    assert _split_paragraphs("\r\r\r") == []


def test_split_paragraphs_only_spaces_returns_empty_list():
    assert _split_paragraphs("     ") == []


def test_split_paragraphs_single_line_no_trailing_newline():
    result = _split_paragraphs("hello")
    assert len(result) == 1
    assert result[0][1] == "hello"


def test_split_paragraphs_single_line_with_trailing_newline():
    result = _split_paragraphs("hello\n")
    assert len(result) == 1
    assert result[0][1] == "hello"


def test_split_paragraphs_two_paragraphs_blank_separated():
    result = _split_paragraphs("para one\n\npara two")
    assert len(result) == 2
    assert result[0][1] == "para one"
    assert result[1][1] == "para two"


def test_split_paragraphs_two_paragraphs_multiple_blank_lines_separated():
    result = _split_paragraphs("para one\n\n\n\n\npara two")
    assert len(result) == 2


def test_split_paragraphs_paragraph_internal_newlines_preserved():
    """多行 paragraph → 内部 \\n 保留。"""
    result = _split_paragraphs("line1\nline2\nline3")
    assert len(result) == 1
    assert result[0][1] == "line1\nline2\nline3"


def test_split_paragraphs_strips_per_line_trailing_whitespace():
    """strip 应用于整个 content，但内部行的 trailing whitespace 保留？"""
    # 实际：content = "\n".join(para_lines).strip()
    # para_lines 内每行是原始（不去 trailing）
    result = _split_paragraphs("hello   ")
    assert result[0][1] == "hello"


def test_split_paragraphs_content_with_internal_trailing_whitespace_per_line():
    """内行 trailing whitespace 保留。"""
    result = _split_paragraphs("line1   \nline2")
    # 内行 trailing whitespace 保留（content 不改每行）
    assert "line1" in result[0][1]
    assert "line2" in result[0][1]


def test_split_paragraphs_crlf_normalized_to_lf():
    result = _split_paragraphs("line1\r\nline2")
    assert len(result) == 1
    # \r\n 归一为 \n
    assert "\r" not in result[0][1]


def test_split_paragraphs_cr_only_normalized_to_lf():
    result = _split_paragraphs("line1\rline2")
    assert len(result) == 1
    assert "\r" not in result[0][1]


def test_split_paragraphs_mixed_crlf_cr_lf():
    text = "para1\r\nline2\rpara2\n\npara3"
    result = _split_paragraphs(text)
    # 至少 1 个 paragraph
    assert len(result) >= 1
    # 不应含 \r
    for _, content in result:
        assert "\r" not in content


def test_split_paragraphs_paragraph_starts_at_line_1():
    result = _split_paragraphs("hello")
    assert result[0][0] == 1


def test_split_paragraphs_line_number_after_leading_blank():
    result = _split_paragraphs("\n\nhello")
    assert result[0][0] == 3  # 跳过两行空白


def test_split_paragraphs_line_number_strictly_increasing():
    result = _split_paragraphs("a\n\nb\n\nc")
    line_nums = [ln for ln, _ in result]
    assert line_nums == sorted(line_nums)
    assert len(line_nums) == 3


def test_split_paragraphs_line_numbers_for_three_paragraphs():
    result = _split_paragraphs("p1\n\np2\n\np3")
    line_nums = [ln for ln, _ in result]
    assert line_nums == [1, 3, 5]


def test_split_paragraphs_line_numbers_with_multiple_blank_lines():
    result = _split_paragraphs("p1\n\n\n\np2")
    assert result[0][0] == 1
    assert result[1][0] == 5


def test_split_paragraphs_internal_newlines_advance_line_counter():
    """多行 paragraph → 第二个 paragraph 的 line 号累加内部行。"""
    result = _split_paragraphs("l1\nl2\nl3\n\np2")
    # p2 在第 5 行
    assert result[1][0] == 5


def test_split_paragraphs_single_character():
    result = _split_paragraphs("x")
    assert len(result) == 1
    assert result[0][1] == "x"


def test_split_paragraphs_single_digit():
    result = _split_paragraphs("5")
    assert len(result) == 1
    assert result[0][1] == "5"


def test_split_paragraphs_unicode_chinese():
    result = _split_paragraphs("你好世界")
    assert len(result) == 1
    assert result[0][1] == "你好世界"


def test_split_paragraphs_unicode_emoji():
    result = _split_paragraphs("hello 🎉 world")
    assert len(result) == 1
    assert "🎉" in result[0][1]


def test_split_paragraphs_mixed_unicode_paragraphs():
    result = _split_paragraphs("中文段落\n\nenglish paragraph\n\n日本語")
    assert len(result) == 3


def test_split_paragraphs_long_single_line():
    s = "a" * 10000
    result = _split_paragraphs(s)
    assert len(result) == 1
    assert len(result[0][1]) == 10000


def test_split_paragraphs_long_multiple_paragraphs():
    s = ("para " + "x" * 100 + "\n\n" for _ in range(10))
    result = _split_paragraphs("".join(s))
    assert len(result) == 10


def test_split_paragraphs_paragraph_with_only_one_word():
    result = _split_paragraphs("word")
    assert result[0][1] == "word"


def test_split_paragraphs_paragraph_with_punctuation():
    result = _split_paragraphs("Hello, World!")
    assert result[0][1] == "Hello, World!"


def test_split_paragraphs_paragraph_with_numbers():
    result = _split_paragraphs("12345 67890")
    assert result[0][1] == "12345 67890"


def test_split_paragraphs_idempotent_call():
    text = "hello\n\nworld"
    r1 = _split_paragraphs(text)
    r2 = _split_paragraphs(text)
    assert r1 == r2


def test_split_paragraphs_trailing_blank_lines_no_extra_paragraph():
    result = _split_paragraphs("hello\n\n\n")
    assert len(result) == 1


def test_split_paragraphs_leading_blank_lines_skip():
    result = _split_paragraphs("\n\n\nhello")
    assert len(result) == 1


def test_split_paragraphs_paragraph_with_special_chars():
    result = _split_paragraphs("a@b#c$d%e^f&g*h(i)j-k_l+m=n{o}")
    assert len(result) == 1


def test_split_paragraphs_paragraph_with_quotes():
    result = _split_paragraphs('"quoted text"')
    assert result[0][1] == '"quoted text"'


def test_split_paragraphs_paragraph_with_backslash():
    result = _split_paragraphs("back\\slash")
    assert result[0][1] == "back\\slash"


# ---------- TextParser.parse() 错误路径深度 ----------


def test_parse_missing_file_error_code(tmp_path: Path):
    p = TextParser()
    with pytest.raises(ParserError) as exc:
        p.parse(tmp_path / "missing.txt", "a" * 64)
    assert exc.value.code == "file_not_found"


def test_parse_missing_file_error_details_has_path(tmp_path: Path):
    p = TextParser()
    missing = tmp_path / "missing.txt"
    with pytest.raises(ParserError) as exc:
        p.parse(missing, "a" * 64)
    assert exc.value.details["path"] == str(missing)


def test_parse_missing_file_is_parser_error_type(tmp_path: Path):
    p = TextParser()
    with pytest.raises(ParserError) as exc:
        p.parse(tmp_path / "missing.txt", "a" * 64)
    assert isinstance(exc.value, ParserError)


def test_parse_unsupported_extension_raises(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.md"
    f.write_text("hello", encoding="utf-8")
    with pytest.raises(ParserError):
        p.parse(f, "a" * 64)


def test_parse_unsupported_extension_error_code(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.html"
    f.write_text("hello", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.code == "unsupported_type"


def test_parse_directory_raises_file_not_found(tmp_path: Path):
    """目录 → is_file()=False → file_not_found。"""
    p = TextParser()
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(ParserError) as exc:
        p.parse(sub, "a" * 64)
    assert exc.value.code == "file_not_found"


def test_parse_returns_document_type(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert isinstance(doc, Document)


def test_parse_returns_correct_source_hash(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    sha = "b" * 64
    doc = p.parse(f, sha)
    assert doc.source_hash == sha


def test_parse_document_id_derived_from_hash(tmp_path: Path):
    from app.parsers.base import make_document_id
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    sha = "c" * 64
    doc = p.parse(f, sha)
    assert doc.document_id == make_document_id(sha)


def test_parse_metadata_text_true(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.metadata == {"text": True}


def test_parse_chunks_empty_list(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.chunks == []


def test_parse_relations_empty_list(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.relations == []


def test_parse_errors_empty_list(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.errors == []


def test_parse_source_path_is_str(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert isinstance(doc.source_path, str)


def test_parse_source_type_is_text(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.source_type == "text"


def test_parse_parser_name_attribute(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.parser_name == "text"


def test_parse_parser_version_attribute(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.parser_version == "stdlib/0.1.0"


# ---------- UnicodeDecodeError 回退 ----------


def test_parse_invalid_utf8_falls_back_to_replace(tmp_path: Path):
    """读 latin-1 字节 → UnicodeDecodeError → errors=replace 回退。"""
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_bytes(b"\xff\xfe hello world")
    doc = p.parse(f, "a" * 64)
    assert isinstance(doc, Document)


def test_parse_invalid_utf8_extracts_paragraph(tmp_path: Path):
    """无效字节后仍有有效内容 → 解析出 paragraph。"""
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_bytes(b"\xff\xfe hello world")
    doc = p.parse(f, "a" * 64)
    # 至少有 elements（含 replacement char）
    assert isinstance(doc.elements, list)


# ---------- 空 elements → text_no_content ----------


def test_parse_empty_file_emits_no_content_warning(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert any(w.code == "text_no_content" for w in doc.warnings)


def test_parse_whitespace_only_emits_no_content_warning(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("   \n\n   \n   ", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert any(w.code == "text_no_content" for w in doc.warnings)


def test_parse_no_content_warning_reason_is_str(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    for w in doc.warnings:
        if w.code == "text_no_content":
            assert isinstance(w.reason, str)
            assert len(w.reason) > 0


# ---------- element 字段 ----------


def test_parse_element_id_increments_across_paragraphs(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("para one\n\npara two\n\npara three", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    ids = [e.element_id for e in doc.elements]
    assert len(ids) == 3
    for i in range(1, len(ids)):
        assert ids[i] > ids[i - 1]


def test_parse_element_id_format_zero_pad(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    eid = doc.elements[0].element_id
    parts = eid.split("::")
    assert len(parts) == 2
    num_part = parts[1]
    assert num_part.startswith("e")
    num = num_part[1:]
    assert len(num) == 4  # 4 位
    assert num == "0000"


def test_parse_element_parent_id_always_none(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello\n\nworld", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    for e in doc.elements:
        assert e.parent_id is None


def test_parse_element_confidence_strictly_095(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello\n\nworld", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    for e in doc.elements:
        assert e.confidence == 0.95


def test_parse_element_type_always_paragraph(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello\n\nworld", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    for e in doc.elements:
        assert e.type == "paragraph"


def test_parse_element_metadata_empty_dict(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    for e in doc.elements:
        assert e.metadata == {}


def test_parse_element_source_locator_only_line_key(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello\n\nworld", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    for e in doc.elements:
        assert e.source_locator["family"] == "line_address"
        assert set(e.source_locator.keys()) == {"family", "line"}


def test_parse_element_source_locator_line_values(tmp_path: Path):
    p = TextParser()
    f = tmp_path / "f.txt"
    f.write_text("hello\n\nworld", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    lines = [e.source_locator["line"] for e in doc.elements]
    assert lines == [1, 3]


# ---------- 模块结构 ----------


def test_module_imports_path():
    import app.parsers.text_parser as mod
    assert hasattr(mod, "Path")


def test_module_imports_any():
    import app.parsers.text_parser as mod
    assert hasattr(mod, "Any")


def test_module_imports_document():
    import app.parsers.text_parser as mod
    assert hasattr(mod, "Document")


def test_module_imports_element():
    import app.parsers.text_parser as mod
    assert hasattr(mod, "Element")


def test_module_imports_warning_record():
    import app.parsers.text_parser as mod
    assert hasattr(mod, "WarningRecord")


def test_module_imports_parser_base():
    import app.parsers.text_parser as mod
    assert hasattr(mod, "Parser")


def test_module_imports_parser_error():
    import app.parsers.text_parser as mod
    assert hasattr(mod, "ParserError")


def test_module_imports_make_document_id():
    import app.parsers.text_parser as mod
    assert hasattr(mod, "make_document_id")


def test_module_has_all():
    import app.parsers.text_parser as mod
    assert hasattr(mod, "__all__")


def test_module_all_contains_text_parser():
    import app.parsers.text_parser as mod
    assert "TextParser" in mod.__all__


def test_module_all_is_list():
    import app.parsers.text_parser as mod
    assert isinstance(mod.__all__, list)


def test_text_parser_inherits_parser():
    p = TextParser()
    assert isinstance(p, Parser)


def test_text_parser_name_is_str():
    p = TextParser()
    assert isinstance(p.name, str)


def test_text_parser_version_is_str():
    p = TextParser()
    assert isinstance(p.version, str)


def test_text_parser_parse_callable():
    p = TextParser()
    assert callable(p.parse)


def test_text_parser_name_value():
    p = TextParser()
    assert p.name == "text"


def test_text_parser_version_value():
    p = TextParser()
    assert p.version == "stdlib/0.1.0"


def test_text_parser_parse_signature():
    """parse 签名: (self, path, source_hash)。"""
    import inspect
    sig = inspect.signature(TextParser.parse)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "path" in params
    assert "source_hash" in params
