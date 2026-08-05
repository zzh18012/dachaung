r"""app/parsers/text_parser.py 边角测试 - 第八轮（Round 199）。

补强已有 base/edges/edges2-7（共 ~829 测试）未覆盖的深度：
- _TEXT_EXTENSIONS 常量
- _detect_text_source_type 各 suffix 组合
- _split_paragraphs 各空白行/CR/LF/CRLF/混合行 ending 场景
- TextParser.parse 错误矩阵（file_not_found/unsupported_type/read failed）
- element 编号/locator/metadata
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

from app.models import Document, Element
from app.parsers.base import Parser, ParserError
from app.parsers.text_parser import (
    TextParser,
    _TEXT_EXTENSIONS,
    _detect_text_source_type,
    _split_paragraphs,
)


# =========================================================================
# _TEXT_EXTENSIONS
# =========================================================================


def test_text_extensions_constant_value():
    assert _TEXT_EXTENSIONS == (".txt", ".text")


def test_text_extensions_is_tuple():
    assert isinstance(_TEXT_EXTENSIONS, tuple)


def test_text_extensions_two_items():
    assert len(_TEXT_EXTENSIONS) == 2


# =========================================================================
# _detect_text_source_type
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


def test_detect_text_source_type_pdf_rejected():
    with pytest.raises(ParserError) as excinfo:
        _detect_text_source_type(Path("a.pdf"))
    assert excinfo.value.code == "unsupported_type"


def test_detect_text_source_type_ipynb_rejected():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("a.ipynb"))


def test_detect_text_source_type_no_suffix_rejected():
    with pytest.raises(ParserError) as excinfo:
        _detect_text_source_type(Path("README"))
    assert excinfo.value.code == "unsupported_type"
    assert excinfo.value.details["suffix"] == ""


def test_detect_text_source_type_no_suffix_message_contains_kuohao():
    """无后缀 → message 含 '(无)'。"""
    with pytest.raises(ParserError) as excinfo:
        _detect_text_source_type(Path("README"))
    assert "(无)" in excinfo.value.message


def test_detect_text_source_type_double_extension():
    """多后缀只看最后一段。"""
    assert _detect_text_source_type(Path("a.b.txt")) == "text"


def test_detect_text_source_type_md_rejected():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("a.md"))


def test_detect_text_source_type_docx_rejected():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("a.docx"))


# =========================================================================
# _split_paragraphs 各场景
# =========================================================================


def test_split_paragraphs_empty_string():
    assert _split_paragraphs("") == []


def test_split_paragraphs_single_line():
    assert _split_paragraphs("hello") == [(1, "hello")]


def test_split_paragraphs_single_paragraph_multiline():
    """连续非空行 → 一个段落。"""
    text = "line1\nline2\nline3"
    result = _split_paragraphs(text)
    assert result == [(1, "line1\nline2\nline3")]


def test_split_paragraphs_two_paragraphs():
    text = "para1\n\npara2"
    assert _split_paragraphs(text) == [(1, "para1"), (3, "para2")]


def test_split_paragraphs_three_paragraphs():
    text = "a\n\nb\n\nc"
    assert _split_paragraphs(text) == [(1, "a"), (3, "b"), (5, "c")]


def test_split_paragraphs_leading_blank_lines():
    """开头有空白行 → 跳过，首段 line_no 正确。"""
    text = "\n\nhello"
    assert _split_paragraphs(text) == [(3, "hello")]


def test_split_paragraphs_trailing_blank_lines():
    text = "hello\n\n\n"
    assert _split_paragraphs(text) == [(1, "hello")]


def test_split_paragraphs_only_blank_lines():
    assert _split_paragraphs("\n\n\n") == []


def test_split_paragraphs_whitespace_only_lines_skipped():
    """含 tab/space 的行视为空白行。"""
    text = "hello\n\t \nworld"
    # 中间 "\t " 视为空白行 → 两段
    assert _split_paragraphs(text) == [(1, "hello"), (3, "world")]


def test_split_paragraphs_crlf_normalized():
    """CRLF → LF 归一后切分。"""
    text = "line1\r\nline2\r\n\r\nline3"
    result = _split_paragraphs(text)
    # CRLF normalize 后："line1\nline2\n\nline3"
    assert result == [(1, "line1\nline2"), (4, "line3")]


def test_split_paragraphs_cr_normalized():
    """单 CR → LF 归一。"""
    text = "line1\rline2\r\rline3"
    result = _split_paragraphs(text)
    assert result == [(1, "line1\nline2"), (4, "line3")]


def test_split_paragraphs_mixed_cr_lf_crlf():
    """混合 CR/LF/CRLF → 都归一为 LF。"""
    text = "a\r\nb\rc\nd"
    result = _split_paragraphs(text)
    # 归一后："a\nb\nc\nd" → 单段
    assert result == [(1, "a\nb\nc\nd")]


def test_split_paragraphs_strip_each_paragraph():
    """段落首尾的空白被 strip。"""
    text = "  hello world  "
    assert _split_paragraphs(text) == [(1, "hello world")]


def test_split_paragraphs_internal_whitespace_preserved():
    """段落内部的空白（缩进）保留。"""
    text = "line1\n    indented line\nline3"
    result = _split_paragraphs(text)
    assert result == [(1, "line1\n    indented line\nline3")]


def test_split_paragraphs_no_trailing_newline():
    assert _split_paragraphs("hello") == [(1, "hello")]


def test_split_paragraphs_single_trailing_newline():
    assert _split_paragraphs("hello\n") == [(1, "hello")]


def test_split_paragraphs_unicode_content():
    text = "你好\n\n世界"
    assert _split_paragraphs(text) == [(1, "你好"), (3, "世界")]


def test_split_paragraphs_emoji_content():
    text = "🎉🎊\n\n🎈"
    assert _split_paragraphs(text) == [(1, "🎉🎊"), (3, "🎈")]


def test_split_paragraphs_long_paragraph():
    """超长段落仍是一段。"""
    text = "a" * 10000
    result = _split_paragraphs(text)
    assert len(result) == 1
    assert len(result[0][1]) == 10000


def test_split_paragraphs_blank_lines_within_dont_split():
    """纯空白行才算分隔；含非空白字符的行不分。"""
    text = "para1\n \npara2"  # 中间是 " "（空格行视为空白）
    assert _split_paragraphs(text) == [(1, "para1"), (3, "para2")]


def test_split_paragraphs_many_paragraphs():
    """10 段。"""
    parts = [f"para{i}" for i in range(10)]
    text = "\n\n".join(parts)
    result = _split_paragraphs(text)
    assert len(result) == 10
    assert result[0] == (1, "para0")
    # para1 在第 3 行（para0 占 1 行，2 是空，3 是 para1）
    assert result[1] == (3, "para1")
    assert result[9] == (19, "para9")


def test_split_paragraphs_returns_list_of_tuples():
    result = _split_paragraphs("hello")
    assert isinstance(result, list)
    assert all(isinstance(item, tuple) for item in result)
    assert all(len(item) == 2 for item in result)


# =========================================================================
# TextParser 类属性
# =========================================================================


def test_text_parser_name_constant():
    assert TextParser.name == "text"


def test_text_parser_version_constant():
    assert TextParser.version == "stdlib/0.1.0"


def test_text_parser_inherits_parser():
    assert issubclass(TextParser, Parser)


def test_text_parser_parse_signature():
    sig = inspect.signature(TextParser.parse)
    assert set(sig.parameters) == {"self", "path", "source_hash"}


# =========================================================================
# TextParser.parse 错误矩阵
# =========================================================================


def test_parse_file_not_found(tmp_path: Path):
    parser = TextParser()
    missing = tmp_path / "missing.txt"
    with pytest.raises(ParserError) as excinfo:
        parser.parse(missing, "a" * 64)
    assert excinfo.value.code == "file_not_found"


def test_parse_unsupported_suffix(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.pdf"
    p.write_text("hello", encoding="utf-8")
    with pytest.raises(ParserError) as excinfo:
        parser.parse(p, "a" * 64)
    assert excinfo.value.code == "unsupported_type"


def test_parse_unsupported_md_suffix(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.md"
    p.write_text("hello", encoding="utf-8")
    with pytest.raises(ParserError):
        parser.parse(p, "a" * 64)


def test_parse_no_suffix_rejected(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "README"
    p.write_text("hello", encoding="utf-8")
    with pytest.raises(ParserError) as excinfo:
        parser.parse(p, "a" * 64)
    assert excinfo.value.code == "unsupported_type"


# =========================================================================
# TextParser.parse 成功路径
# =========================================================================


def test_parse_text_extension(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.text"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert isinstance(doc, Document)


def test_parse_single_paragraph(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].content == "hello world"


def test_parse_two_paragraphs(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("para1\n\npara2", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 2
    assert doc.elements[0].content == "para1"
    assert doc.elements[1].content == "para2"


def test_parse_element_id_zero_padded(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].element_id.endswith("::e0000")


def test_parse_element_id_increments(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("a\n\nb\n\nc", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    ids = [el.element_id for el in doc.elements]
    assert ids[0].endswith("::e0000")
    assert ids[1].endswith("::e0001")
    assert ids[2].endswith("::e0002")


def test_parse_element_id_with_document_id_prefix(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    source_hash = "b" * 64
    doc = parser.parse(p, source_hash)
    assert doc.elements[0].element_id.startswith(doc.document_id)


def test_parse_element_type_paragraph(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert all(el.type == "paragraph" for el in doc.elements)


def test_parse_element_locator_line(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("para1\n\npara2", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].source_locator == {"line": 1}
    assert doc.elements[1].source_locator == {"line": 3}


def test_parse_element_confidence_095(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].confidence == 0.95


def test_parse_element_parent_id_none(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert all(el.parent_id is None for el in doc.elements)


def test_parse_element_metadata_empty(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert all(el.metadata == {} for el in doc.elements)


def test_parse_element_resource_path_none(tmp_path: Path):
    """TextParser 不产生 image → resource_path 默认 None。"""
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert all(el.resource_path is None for el in doc.elements)


def test_parse_returns_document_instance(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert isinstance(doc, Document)


def test_parse_source_type_text(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert doc.source_type == "text"


def test_parse_source_type_text_with_dot_text_ext(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.text"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert doc.source_type == "text"


def test_parse_parser_name_text(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert doc.parser_name == "text"


def test_parse_parser_version(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert doc.parser_version == "stdlib/0.1.0"


def test_parse_document_empty_chunks(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert doc.chunks == []


def test_parse_document_empty_relations(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert doc.relations == []


def test_parse_document_errors_empty_on_success(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert doc.errors == []


def test_parse_document_metadata_text_true(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata == {"text": True}


def test_parse_empty_file_warning(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 0
    assert any(w.code == "text_no_content" for w in doc.warnings)


def test_parse_whitespace_only_file_warning(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "ws.txt"
    p.write_text("   \n\n\t\n   ", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 0
    assert any(w.code == "text_no_content" for w in doc.warnings)


def test_parse_utf8_unicode_content(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "uni.txt"
    p.write_text("你好世界\n\n第二段", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 2
    assert doc.elements[0].content == "你好世界"


def test_parse_invalid_utf8_uses_replace(tmp_path: Path):
    """非 UTF-8 字节 → errors=replace 不抛。"""
    parser = TextParser()
    p = tmp_path / "bad.txt"
    p.write_bytes(b"\xff\xfe\xfd invalid utf-8")
    doc = parser.parse(p, "a" * 64)
    # 不抛、能产生 Document
    assert isinstance(doc, Document)


def test_parse_crlf_line_endings(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "crlf.txt"
    p.write_bytes(b"line1\r\nline2\r\n\r\nline3")
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 2
    assert doc.elements[0].content == "line1\nline2"
    assert doc.elements[1].content == "line3"


def test_parse_cr_line_endings(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "cr.txt"
    p.write_bytes(b"line1\rline2\r\rline3")
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 2


def test_parse_does_not_inflate_blank_lines_to_paragraphs(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "blanks.txt"
    p.write_text("hello\n\n\n\n\nworld", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    # 多个连续空行 → 仍只两段
    assert len(doc.elements) == 2


def test_parse_strip_paragraph_whitespace(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "ws.txt"
    p.write_text("  hello world  ", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].content == "hello world"


def test_parse_source_path_in_document(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert str(p) in doc.source_path or doc.source_path.endswith("x.txt")


# =========================================================================
# 模块结构与签名
# =========================================================================


def test_module_all_exports_text_parser():
    import app.parsers.text_parser as m
    assert m.__all__ == ["TextParser"]


def test_module_imports_path():
    import app.parsers.text_parser as m
    assert hasattr(m, "Path")


def test_module_imports_any():
    import app.parsers.text_parser as m
    assert hasattr(m, "Any")


def test_module_imports_document():
    import app.parsers.text_parser as m
    assert hasattr(m, "Document")


def test_module_imports_element():
    import app.parsers.text_parser as m
    assert hasattr(m, "Element")


def test_module_imports_warning_record():
    import app.parsers.text_parser as m
    assert hasattr(m, "WarningRecord")


def test_module_imports_parser_base():
    import app.parsers.text_parser as m
    assert hasattr(m, "Parser")
    assert hasattr(m, "ParserError")
    assert hasattr(m, "make_document_id")


def test_detect_text_source_type_signature():
    sig = inspect.signature(_detect_text_source_type)
    assert set(sig.parameters) == {"path"}


def test_detect_text_source_type_return_annotation_str():
    sig = inspect.signature(_detect_text_source_type)
    assert "str" in str(sig.return_annotation)


def test_split_paragraphs_signature():
    sig = inspect.signature(_split_paragraphs)
    assert set(sig.parameters) == {"text"}


def test_split_paragraphs_return_annotation_list():
    sig = inspect.signature(_split_paragraphs)
    assert "list" in str(sig.return_annotation)


def test_all_internal_functions_callable():
    assert callable(_detect_text_source_type)
    assert callable(_split_paragraphs)
    assert callable(TextParser)


# =========================================================================
# idempotency
# =========================================================================


def test_detect_text_source_type_idempotent():
    a = _detect_text_source_type(Path("a.txt"))
    b = _detect_text_source_type(Path("a.txt"))
    assert a == b


def test_split_paragraphs_idempotent():
    text = "para1\n\npara2"
    a = _split_paragraphs(text)
    b = _split_paragraphs(text)
    assert a == b


def test_parse_idempotent(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("hello\n\nworld", encoding="utf-8")
    doc1 = parser.parse(p, "a" * 64)
    doc2 = parser.parse(p, "a" * 64)
    assert len(doc1.elements) == len(doc2.elements)
    assert doc1.elements[0].content == doc2.elements[0].content


# =========================================================================
# 综合行为
# =========================================================================


def test_full_pipeline_multi_paragraph(tmp_path: Path):
    """完整文本：5 段、混合空白行。"""
    parser = TextParser()
    text = "Title\n\nBody paragraph 1.\n\n\nBody paragraph 2.\n\nConclusion."
    p = tmp_path / "full.txt"
    p.write_text(text, encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert doc.source_type == "text"
    assert len(doc.elements) == 4
    contents = [el.content for el in doc.elements]
    assert contents[0] == "Title"
    assert contents[1] == "Body paragraph 1."
    assert contents[2] == "Body paragraph 2."
    assert contents[3] == "Conclusion."


def test_parse_preserves_indented_code_block(tmp_path: Path):
    """缩进保留（不重排）。"""
    parser = TextParser()
    text = "def foo():\n    return 42"
    p = tmp_path / "code.txt"
    p.write_text(text, encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].content == "def foo():\n    return 42"


def test_parse_single_paragraph_no_newline(tmp_path: Path):
    """无换行的单段。"""
    parser = TextParser()
    p = tmp_path / "x.txt"
    p.write_text("single line no newline", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].content == "single line no newline"
    assert doc.elements[0].source_locator == {"line": 1}


def test_parse_unicode_emoji_pipeline(tmp_path: Path):
    parser = TextParser()
    p = tmp_path / "emoji.txt"
    p.write_text("Hello 🎉\n\nWorld 🎊", encoding="utf-8")
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 2
    assert "🎉" in doc.elements[0].content
    assert "🎊" in doc.elements[1].content


def test_parse_locator_uses_normalized_line_numbers(tmp_path: Path):
    """locator.line 是归一化后的行号（CRLF → LF 之后）。"""
    parser = TextParser()
    p = tmp_path / "crlf.txt"
    p.write_bytes(b"para1\r\n\r\npara2")
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].source_locator == {"line": 1}
    assert doc.elements[1].source_locator == {"line": 3}
