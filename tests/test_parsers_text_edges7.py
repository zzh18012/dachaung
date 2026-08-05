r"""app/parsers/text_parser.py 边角测试 - 第七轮（Round 187）。

补强已有 base/edges/edges2-6（共 543 测试）未覆盖的深度：
- _TEXT_EXTENSIONS 常量精确值
- _detect_text_source_type：大写/混合大小写、未知/无后缀
- _split_paragraphs：empty/single/multi/CRLF/CR only/multiple blank line separator
- TextParser 类属性 name/version、继承 Parser
- parse 错误路径：missing file、unsupported、OSError
- parse encoding：UTF-8 with replace、BOM
- parse element locator 1-based line numbering
- 各 metadata 字段、空文件 warning
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

from app.models import Document
from app.parsers.base import Parser, ParserError
from app.parsers.text_parser import (
    _detect_text_source_type,
    _split_paragraphs,
    _TEXT_EXTENSIONS,
    TextParser,
)


# =========================================================================
# 常量
# =========================================================================


def test_text_extensions_exact():
    assert _TEXT_EXTENSIONS == (".txt", ".text")


def test_text_extensions_is_tuple():
    assert isinstance(_TEXT_EXTENSIONS, tuple)


def test_text_extensions_count_two():
    assert len(_TEXT_EXTENSIONS) == 2


# =========================================================================
# _detect_text_source_type 深度
# =========================================================================


def test_detect_text_source_type_txt():
    assert _detect_text_source_type(Path("a.txt")) == "text"


def test_detect_text_source_type_text():
    assert _detect_text_source_type(Path("a.text")) == "text"


def test_detect_text_source_type_uppercase_txt():
    assert _detect_text_source_type(Path("a.TXT")) == "text"


def test_detect_text_source_type_uppercase_text():
    assert _detect_text_source_type(Path("a.TEXT")) == "text"


def test_detect_text_source_type_mixed_case():
    assert _detect_text_source_type(Path("a.TxT")) == "text"


def test_detect_text_source_type_unknown_suffix_raises():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("a.md"))
    assert exc.value.code == "unsupported_type"


def test_detect_text_source_type_no_suffix_raises():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("README"))


def test_detect_text_source_type_html_raises():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("a.html"))


def test_detect_text_source_type_error_has_suffix_detail():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("a.unknown"))
    assert exc.value.details["suffix"] == ".unknown"


def test_detect_text_source_type_error_message_contains_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("a.unknown"))
    assert ".unknown" in str(exc.value)


def test_detect_text_source_type_returns_str():
    assert isinstance(_detect_text_source_type(Path("a.txt")), str)


def test_detect_text_source_type_no_suffix_details_empty_string():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("noext"))
    assert exc.value.details["suffix"] == ""


# =========================================================================
# _split_paragraphs 深度
# =========================================================================


def test_split_paragraphs_empty_string():
    assert _split_paragraphs("") == []


def test_split_paragraphs_single_line():
    result = _split_paragraphs("hello")
    assert len(result) == 1
    assert result[0] == (1, "hello")


def test_split_paragraphs_single_paragraph_multi_line():
    """连续行（无空行分隔）属于同一段。"""
    result = _split_paragraphs("line1\nline2\nline3")
    assert len(result) == 1
    assert result[0] == (1, "line1\nline2\nline3")


def test_split_paragraphs_two_paragraphs():
    result = _split_paragraphs("para1\n\npara2")
    assert len(result) == 2
    assert result[0] == (1, "para1")
    assert result[1] == (3, "para2")


def test_split_paragraphs_crlf_normalized():
    result = _split_paragraphs("line1\r\nline2")
    assert len(result) == 1
    assert result[0] == (1, "line1\nline2")


def test_split_paragraphs_cr_only_normalized():
    """CR 单独也归一为 LF。"""
    result = _split_paragraphs("line1\rline2")
    assert len(result) == 1
    assert result[0] == (1, "line1\nline2")


def test_split_paragraphs_crlf_paragraph_separator():
    result = _split_paragraphs("para1\r\n\r\npara2")
    assert len(result) == 2
    assert result[1] == (3, "para2")


def test_split_paragraphs_leading_blank_lines_skipped():
    """前导空行被跳过，para_start_line 是首个非空行的位置。"""
    result = _split_paragraphs("\n\n\nhello")
    assert result[0] == (4, "hello")


def test_split_paragraphs_trailing_blank_lines_ignored():
    result = _split_paragraphs("hello\n\n\n")
    assert len(result) == 1
    assert result[0] == (1, "hello")


def test_split_paragraphs_whitespace_only_lines_treated_as_blank():
    """含 tab/space 的行也被视为 blank。"""
    result = _split_paragraphs("para1\n\t \npara2")
    assert len(result) == 2
    assert result[1] == (3, "para2")


def test_split_paragraphs_line_numbers_1based():
    result = _split_paragraphs("a\n\nb\n\nc")
    starts = [s for s, _ in result]
    assert starts == [1, 3, 5]


def test_split_paragraphs_all_blank_returns_empty():
    assert _split_paragraphs("\n\n\n") == []


def test_split_paragraphs_whitespace_only_returns_empty():
    assert _split_paragraphs("   \n\t\n  ") == []


def test_split_paragraphs_returns_list_of_tuples():
    result = _split_paragraphs("hello")
    assert isinstance(result, list)
    assert isinstance(result[0], tuple)


def test_split_paragraphs_each_tuple_two_elements():
    result = _split_paragraphs("hello\n\nworld")
    for item in result:
        assert len(item) == 2


def test_split_paragraphs_first_element_int():
    result = _split_paragraphs("hello")
    assert isinstance(result[0][0], int)


def test_split_paragraphs_second_element_str():
    result = _split_paragraphs("hello")
    assert isinstance(result[0][1], str)


def test_split_paragraphs_strips_content():
    """para_lines 用 \n join 后 strip。"""
    result = _split_paragraphs("  hello  ")
    assert result[0][1] == "hello"


def test_split_paragraphs_idempotent():
    text = "para1\n\npara2"
    assert _split_paragraphs(text) == _split_paragraphs(text)


def test_split_paragraphs_does_not_mutate_input():
    text = "para1\n\npara2"
    original = text
    _split_paragraphs(text)
    assert text == original


def test_split_paragraphs_multiple_blank_lines_between_paras():
    """多个空行也只当作一个分隔。"""
    result = _split_paragraphs("para1\n\n\n\n\npara2")
    assert len(result) == 2
    # para2 在第 6 行
    assert result[1] == (6, "para2")


# =========================================================================
# TextParser 类属性
# =========================================================================


def test_text_parser_name_attribute():
    assert TextParser.name == "text"


def test_text_parser_version_attribute():
    assert TextParser.version == "stdlib/0.1.0"


def test_text_parser_inherits_parser():
    assert issubclass(TextParser, Parser)


def test_text_parser_parse_signature():
    sig = inspect.signature(TextParser.parse)
    assert set(sig.parameters) == {"self", "path", "source_hash"}


def test_text_parser_parse_no_defaults():
    sig = inspect.signature(TextParser.parse)
    for name in ("path", "source_hash"):
        assert sig.parameters[name].default is inspect.Parameter.empty


def test_text_parser_parse_return_annotation_document():
    sig = inspect.signature(TextParser.parse)
    assert "Document" in str(sig.return_annotation)


# =========================================================================
# parse 错误路径
# =========================================================================


def test_parse_missing_file_raises(tmp_path: Path):
    parser = TextParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(tmp_path / "missing.txt", "a" * 64)
    assert exc.value.code == "file_not_found"


def test_parse_missing_file_error_message_contains_path(tmp_path: Path):
    parser = TextParser()
    missing = tmp_path / "missing.txt"
    with pytest.raises(ParserError) as exc:
        parser.parse(missing, "a" * 64)
    assert str(missing) in str(exc.value)


def test_parse_missing_file_details_has_path(tmp_path: Path):
    parser = TextParser()
    missing = tmp_path / "missing.txt"
    with pytest.raises(ParserError) as exc:
        parser.parse(missing, "a" * 64)
    assert "path" in exc.value.details


def test_parse_unsupported_suffix_raises(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert exc.value.code == "unsupported_type"


def test_parse_unsupported_suffix_html(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<p>hi</p>", encoding="utf-8")
    parser = TextParser()
    with pytest.raises(ParserError):
        parser.parse(p, "a" * 64)


def test_parse_read_oserror_raises(tmp_path: Path, monkeypatch):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")

    def fake_read_text(self, *args, **kwargs):
        raise OSError("simulated")

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    parser = TextParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert exc.value.code == "text_read_failed"


def test_parse_read_oserror_has_exception_type(tmp_path: Path, monkeypatch):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")

    def fake_read_text(self, *args, **kwargs):
        raise OSError("simulated")

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    parser = TextParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert "exception_type" in exc.value.details


# =========================================================================
# parse 行为深度
# =========================================================================


def test_parse_single_paragraph(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[0].content == "hello"


def test_parse_multi_paragraph(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("para1\n\npara2\n\npara3", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 3
    assert [el.content for el in doc.elements] == ["para1", "para2", "para3"]


def test_parse_multi_line_paragraph_joined_with_newline(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("line1\nline2\nline3", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].content == "line1\nline2\nline3"


def test_parse_locator_line_number(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("para1\n\npara2", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].source_locator["line"] == 1
    assert doc.elements[1].source_locator["line"] == 3


def test_parse_locator_after_leading_blanks(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("\n\n\nactual content", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].source_locator["line"] == 4


def test_parse_element_id_zero_padded(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert "::e0000" in doc.elements[0].element_id


def test_parse_element_id_increments(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("a\n\nb", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert "::e0000" in doc.elements[0].element_id
    assert "::e0001" in doc.elements[1].element_id


def test_parse_confidence_095(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].confidence == 0.95


def test_parse_element_metadata_empty_dict(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].metadata == {}


def test_parse_element_parent_id_none(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].parent_id is None


def test_parse_element_resource_path_none(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].resource_path is None


def test_parse_returns_document_instance(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert isinstance(doc, Document)


def test_parse_returns_empty_chunks_relations_errors(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.chunks == []
    assert doc.relations == []
    assert doc.errors == []


def test_parse_metadata_text_flag(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata["text"] is True


def test_parse_source_type_text(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.source_type == "text"


def test_parse_source_path_is_str(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert isinstance(doc.source_path, str)
    assert str(p) == doc.source_path


def test_parse_source_hash_propagated(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    h = "a" * 64
    doc = parser.parse(p, h)
    assert doc.source_hash == h


def test_parse_parser_name_propagated(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.parser_name == "text"


def test_parse_parser_version_propagated(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.parser_version == "stdlib/0.1.0"


# =========================================================================
# parse 边界情况
# =========================================================================


def test_parse_empty_file_emits_no_content_warning(tmp_path: Path):
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements == []
    assert any(w.code == "text_no_content" for w in doc.warnings)


def test_parse_whitespace_only_file_emits_no_content_warning(tmp_path: Path):
    p = tmp_path / "ws.txt"
    p.write_text("   \n\t\n  ", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements == []
    assert any(w.code == "text_no_content" for w in doc.warnings)


def test_parse_no_warning_when_content_exists(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.warnings == []


def test_parse_text_extension(tmp_path: Path):
    """支持 .text 扩展名。"""
    p = tmp_path / "test.text"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1


def test_parse_crlf_file(tmp_path: Path):
    p = tmp_path / "crlf.txt"
    p.write_bytes(b"line1\r\nline2")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].content == "line1\nline2"


def test_parse_cr_only_file(tmp_path: Path):
    p = tmp_path / "cr.txt"
    p.write_bytes(b"line1\rline2")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].content == "line1\nline2"


def test_parse_unicode_content(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("你好世界\n中文段落", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert "你好" in doc.elements[0].content


def test_parse_non_utf8_falls_back_to_replace(tmp_path: Path):
    """非 UTF-8 字节用 errors=replace 不崩。"""
    p = tmp_path / "bad.txt"
    p.write_bytes(b"\xe9\x9c some text")  # 不完整 UTF-8
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    # 不抛
    assert isinstance(doc, Document)


def test_parse_idempotent(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello\n\nworld", encoding="utf-8")
    parser = TextParser()
    doc1 = parser.parse(p, "a" * 64)
    doc2 = parser.parse(p, "a" * 64)
    assert len(doc1.elements) == len(doc2.elements)
    for a, b in zip(doc1.elements, doc2.elements):
        assert a.content == b.content


def test_parse_different_hash_different_doc_id(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc1 = parser.parse(p, "a" * 64)
    doc2 = parser.parse(p, "b" * 64)
    assert doc1.document_id != doc2.document_id


def test_parse_does_not_mutate_input_file(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello\n\nworld", encoding="utf-8")
    original = p.read_text(encoding="utf-8")
    parser = TextParser()
    parser.parse(p, "a" * 64)
    assert p.read_text(encoding="utf-8") == original


# =========================================================================
# 综合行为
# =========================================================================


def test_parse_complex_document(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text(
        "Title line\n"
        "\n"
        "First paragraph with multiple words.\n"
        "\n"
        "\n"
        "Second paragraph after multiple blank lines.\n"
        "\n"
        "Third paragraph.",
        encoding="utf-8",
    )
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 4
    assert doc.elements[0].content == "Title line"
    assert doc.elements[3].content == "Third paragraph."


def test_parse_paragraph_with_internal_whitespace_lines(tmp_path: Path):
    """段内多行通过 \n join（空白保留）。"""
    p = tmp_path / "test.txt"
    p.write_text("line1\n  indented line\nline3", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    # 内部空白保留
    assert "  indented line" in doc.elements[0].content


def test_parse_long_document_many_paragraphs(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("\n\n".join(f"para{i}" for i in range(50)), encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 50


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import app.parsers.text_parser as mod
    assert mod.__all__ == ["TextParser"]


def test_module_all_is_list():
    import app.parsers.text_parser as mod
    assert isinstance(mod.__all__, list)


def test_module_uses_future_annotations():
    import app.parsers.text_parser as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_imports_path():
    import app.parsers.text_parser as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import app.parsers.text_parser as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_models():
    import app.parsers.text_parser as mod
    src = inspect.getsource(mod)
    assert "from app.models" in src


def test_module_imports_base():
    import app.parsers.text_parser as mod
    src = inspect.getsource(mod)
    assert "from app.parsers.base" in src


def test_module_docstring_present():
    import app.parsers.text_parser as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_strategy():
    import app.parsers.text_parser as mod
    assert "空行" in mod.__doc__ or "段落" in mod.__doc__


def test_module_docstring_mentions_supported_extensions():
    import app.parsers.text_parser as mod
    assert ".txt" in mod.__doc__


def test_module_docstring_mentions_unsupported_features():
    """docstring 应说明不支持的事。"""
    import app.parsers.text_parser as mod
    doc = mod.__doc__
    assert "不做" in doc or "不支持" in doc or "明确放弃" in doc
