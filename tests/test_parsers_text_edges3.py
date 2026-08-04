"""app/parsers/text_parser.py 边角测试 - 第三轮（Round 104）。

补强已有 base/edges/edges2（共 212 个测试）未覆盖的深度路径：
- _split_paragraphs：混合换行、CR only、CRLF + LF、tab 行首、内部空白保留
- _detect_text_source_type：拒绝更多扩展名
- parse 返回 Document 不变量：source_type、parser_name/version、metadata.text、confidence
- pipeline 错误：text_read_failed（OS monkey）
- 模块结构：__all__、imports、Parser 继承
- element_id 连续编号、唯一
- 大文件 stress

不修改任何源码。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.parsers.base import ParserError
from app.parsers.text_parser import (
    _TEXT_EXTENSIONS,
    TextParser,
    _detect_text_source_type,
    _split_paragraphs,
)


# =========================================================================
# 辅助
# =========================================================================


def _write_text(tmp_path: Path, text: str, name: str = "test.txt") -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _parse(tmp_path: Path, text: str, name: str = "test.txt"):
    p = _write_text(tmp_path, text, name)
    return TextParser().parse(p, source_hash="a" * 64)


# =========================================================================
# _split_paragraphs 深度
# =========================================================================


def test_split_paragraphs_empty_string():
    assert _split_paragraphs("") == []


def test_split_paragraphs_single_chunk_no_trailing_newline():
    assert _split_paragraphs("hello") == [(1, "hello")]


def test_split_paragraphs_single_chunk_with_trailing_newline():
    assert _split_paragraphs("hello\n") == [(1, "hello")]


def test_split_paragraphs_two_chunks_with_blank_line():
    result = _split_paragraphs("para1\n\npara2")
    assert len(result) == 2
    assert result[0] == (1, "para1")
    assert result[1] == (3, "para2")


def test_split_paragraphs_multiple_blank_lines_as_separator():
    result = _split_paragraphs("a\n\n\n\nb")
    assert len(result) == 2
    assert result[0] == (1, "a")
    assert result[1] == (5, "b")


def test_split_paragraphs_whitespace_only_returns_empty():
    assert _split_paragraphs("   \n   \n   ") == []


def test_split_paragraphs_cr_only_line_endings():
    """CR only 换行 → 归一为 LF。"""
    result = _split_paragraphs("a\r\nb")
    # "a\r\nb" → "a\nb" → 1 个段落（无空行分隔）
    assert len(result) == 1
    assert result[0] == (1, "a\nb")


def test_split_paragraphs_cr_only():
    """仅 CR 换行。"""
    result = _split_paragraphs("para1\rpara2")
    # CR 归一为 LF → 1 个段落
    assert len(result) == 1


def test_split_paragraphs_mixed_line_endings():
    """混合 CRLF + LF + CR。"""
    result = _split_paragraphs("a\r\n\nb\rc")
    # 归一后："a\n\nb\nc"
    # 段落 1: "a" at line 1
    # 段落 2: "b\nc" at line 3
    assert len(result) == 2


def test_split_paragraphs_internal_whitespace_preserved():
    """段落内部多余空格不被 strip（只 strip 首尾）。"""
    result = _split_paragraphs("hello    world")
    assert result == [(1, "hello    world")]


def test_split_paragraphs_tab_in_content_preserved():
    result = _split_paragraphs("hello\tworld")
    assert result == [(1, "hello\tworld")]


def test_split_paragraphs_leading_tab_in_line_preserved():
    """段落首行的 tab 被 strip（首尾 strip）但仍属于段落。"""
    result = _split_paragraphs("\tindented line")
    assert result == [(1, "indented line")]


def test_split_paragraphs_trailing_whitespace_in_line_stripped():
    """strip 后段落内容不含尾部空白。"""
    result = _split_paragraphs("hello   ")
    assert result == [(1, "hello")]


def test_split_paragraphs_returns_list_of_tuples():
    result = _split_paragraphs("a\n\nb")
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, tuple)
        assert len(item) == 2


def test_split_paragraphs_line_numbers_strictly_ascending():
    result = _split_paragraphs("a\n\nb\n\nc")
    line_nums = [ln for ln, _ in result]
    assert line_nums == sorted(line_nums)


def test_split_paragraphs_content_not_empty():
    result = _split_paragraphs("a\n\nb")
    for _, c in result:
        assert c  # 非空字符串


def test_split_paragraphs_many_chunks():
    text = "\n\n".join(f"para{i}" for i in range(50))
    result = _split_paragraphs(text)
    assert len(result) == 50


def test_split_paragraphs_returns_paragraphs_with_multiline_content():
    text = "line1\nline2\nline3"
    result = _split_paragraphs(text)
    assert len(result) == 1
    assert "line1" in result[0][1]
    assert "line3" in result[0][1]


# =========================================================================
# _detect_text_source_type 深度
# =========================================================================


def test_detect_text_source_type_accepts_lowercase_txt():
    assert _detect_text_source_type(Path("test.txt")) == "text"


def test_detect_text_source_type_accepts_lowercase_text():
    assert _detect_text_source_type(Path("test.text")) == "text"


def test_detect_text_source_type_accepts_uppercase_txt():
    assert _detect_text_source_type(Path("test.TXT")) == "text"


def test_detect_text_source_type_accepts_uppercase_text():
    assert _detect_text_source_type(Path("test.TEXT")) == "text"


def test_detect_text_source_type_accepts_mixed_case():
    assert _detect_text_source_type(Path("test.Txt")) == "text"


def test_detect_text_source_type_rejects_pdf():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("test.pdf"))


def test_detect_text_source_type_rejects_docx():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("test.docx"))


def test_detect_text_source_type_rejects_html():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("test.html"))


def test_detect_text_source_type_rejects_md():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("test.md"))


def test_detect_text_source_type_rejects_ipynb():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("test.ipynb"))


def test_detect_text_source_type_rejects_no_suffix():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("noext"))


def test_detect_text_source_type_rejects_unknown_suffix():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("test.unknown"))


def test_detect_text_source_type_error_code():
    with pytest.raises(ParserError) as ei:
        _detect_text_source_type(Path("test.unknown"))
    assert ei.value.code == "unsupported_type"


def test_detect_text_source_type_error_details_has_suffix():
    with pytest.raises(ParserError) as ei:
        _detect_text_source_type(Path("test.unknown"))
    assert ei.value.details.get("suffix") == ".unknown"


def test_detect_text_source_type_error_details_for_no_suffix():
    with pytest.raises(ParserError) as ei:
        _detect_text_source_type(Path("noext"))
    assert ei.value.details.get("suffix") == ""


def test_text_extensions_exact_two_entries():
    assert _TEXT_EXTENSIONS == (".txt", ".text")


def test_text_extensions_is_tuple():
    assert isinstance(_TEXT_EXTENSIONS, tuple)


# =========================================================================
# parse: pipeline 错误
# =========================================================================


def test_parse_missing_file_raises_file_not_found(tmp_path: Path):
    p = tmp_path / "no.txt"
    with pytest.raises(ParserError) as ei:
        TextParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "file_not_found"


def test_parse_missing_file_details_has_path(tmp_path: Path):
    p = tmp_path / "no.txt"
    with pytest.raises(ParserError) as ei:
        TextParser().parse(p, source_hash="a" * 64)
    assert str(p) in ei.value.details.get("path", "") or ei.value.details.get("path") == str(p)


def test_parse_unsupported_extension_raises(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<p>x</p>")
    with pytest.raises(ParserError) as ei:
        TextParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "unsupported_type"


def test_parse_directory_raises_file_not_found(tmp_path: Path):
    """目录不是文件 → file_not_found。"""
    d = tmp_path / "subdir"
    d.mkdir()
    with pytest.raises(ParserError) as ei:
        TextParser().parse(d, source_hash="a" * 64)
    assert ei.value.code == "file_not_found"


def test_parse_oserror_raises_text_read_failed(tmp_path: Path, monkeypatch):
    p = _write_text(tmp_path, "hello")

    real_read_text = Path.read_text

    def _raise_os(self, *args, **kwargs):
        if self == p:
            raise OSError("disk error")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _raise_os)
    with pytest.raises(ParserError) as ei:
        TextParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "text_read_failed"


def test_parse_oserror_details_has_exception_type(tmp_path: Path, monkeypatch):
    p = _write_text(tmp_path, "hello")

    real_read_text = Path.read_text

    def _raise_os(self, *args, **kwargs):
        if self == p:
            raise OSError("disk error")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _raise_os)
    with pytest.raises(ParserError) as ei:
        TextParser().parse(p, source_hash="a" * 64)
    assert ei.value.details.get("exception_type") == "OSError"


def test_parse_invalid_utf8_falls_back_to_replace(tmp_path: Path):
    """无效 UTF-8 → 用 errors=replace。"""
    p = tmp_path / "test.txt"
    p.write_bytes(b"\xff\xfe hello world")
    doc = TextParser().parse(p, source_hash="a" * 64)
    # 不抛异常，仍能 emit paragraph
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) >= 1


# =========================================================================
# parse: 返回 Document 不变量
# =========================================================================


def test_parse_returns_document_type(tmp_path: Path):
    doc = _parse(tmp_path, "hello")
    from app.models import Document
    assert isinstance(doc, Document)


def test_parse_source_type_text(tmp_path: Path):
    doc = _parse(tmp_path, "hello")
    assert doc.source_type == "text"


def test_parse_parser_name_attribute(tmp_path: Path):
    doc = _parse(tmp_path, "hello")
    assert doc.parser_name == "text"


def test_parse_parser_version_attribute(tmp_path: Path):
    doc = _parse(tmp_path, "hello")
    assert doc.parser_version == "stdlib/0.1.0"


def test_parse_metadata_text_flag_true(tmp_path: Path):
    doc = _parse(tmp_path, "hello")
    assert doc.metadata.get("text") is True


def test_parse_source_path_preserved(tmp_path: Path):
    p = _write_text(tmp_path, "hello", "custom.txt")
    doc = TextParser().parse(p, source_hash="a" * 64)
    assert doc.source_path == str(p)


def test_parse_source_hash_passed_through(tmp_path: Path):
    p = _write_text(tmp_path, "hello")
    doc = TextParser().parse(p, source_hash="b" * 64)
    assert doc.source_hash == "b" * 64


def test_parse_document_id_derived_from_hash(tmp_path: Path):
    p = _write_text(tmp_path, "hello")
    doc1 = TextParser().parse(p, source_hash="a" * 64)
    doc2 = TextParser().parse(p, source_hash="b" * 64)
    assert doc1.document_id != doc2.document_id


def test_parse_returns_document_with_empty_chunks(tmp_path: Path):
    doc = _parse(tmp_path, "hello")
    assert doc.chunks == []


def test_parse_returns_document_with_empty_relations(tmp_path: Path):
    doc = _parse(tmp_path, "hello")
    assert doc.relations == []


def test_parse_returns_document_with_empty_errors(tmp_path: Path):
    doc = _parse(tmp_path, "hello")
    assert doc.errors == []


def test_parse_empty_file_emits_no_content_warning(tmp_path: Path):
    doc = _parse(tmp_path, "")
    no_content = [w for w in doc.warnings if w.code == "text_no_content"]
    assert len(no_content) == 1


def test_parse_whitespace_only_file_emits_no_content_warning(tmp_path: Path):
    doc = _parse(tmp_path, "   \n\t\n  ")
    no_content = [w for w in doc.warnings if w.code == "text_no_content"]
    assert len(no_content) == 1


def test_parse_no_content_warning_reason_text(tmp_path: Path):
    doc = _parse(tmp_path, "")
    w = doc.warnings[0]
    assert "element" in w.reason or "提取" in w.reason


def test_parse_with_content_no_warning(tmp_path: Path):
    doc = _parse(tmp_path, "hello")
    no_content = [w for w in doc.warnings if w.code == "text_no_content"]
    assert no_content == []


# =========================================================================
# parse: element 深度
# =========================================================================


def test_parse_element_type_always_paragraph(tmp_path: Path):
    doc = _parse(tmp_path, "para1\n\npara2")
    for e in doc.elements:
        assert e.type == "paragraph"


def test_parse_element_confidence_strictly_095(tmp_path: Path):
    doc = _parse(tmp_path, "hello")
    for e in doc.elements:
        assert e.confidence == 0.95


def test_parse_element_metadata_empty_dict(tmp_path: Path):
    doc = _parse(tmp_path, "hello")
    for e in doc.elements:
        assert e.metadata == {}


def test_parse_element_parent_id_none(tmp_path: Path):
    doc = _parse(tmp_path, "hello")
    for e in doc.elements:
        assert e.parent_id is None


def test_parse_element_resource_path_none(tmp_path: Path):
    doc = _parse(tmp_path, "hello")
    for e in doc.elements:
        assert e.resource_path is None


def test_parse_element_locator_only_has_line_key(tmp_path: Path):
    """locator 只有 line，没有 section_path 等。"""
    doc = _parse(tmp_path, "hello")
    for e in doc.elements:
        assert set(e.source_locator.keys()) == {"line"}


def test_parse_element_id_continuous(tmp_path: Path):
    doc = _parse(tmp_path, "para1\n\npara2\n\npara3")
    ids = [e.element_id for e in doc.elements]
    nums = [int(eid.split("::e")[1]) for eid in ids]
    assert nums == [0, 1, 2]


def test_parse_element_id_unique(tmp_path: Path):
    doc = _parse(tmp_path, "para1\n\npara2\n\npara3")
    ids = [e.element_id for e in doc.elements]
    assert len(set(ids)) == len(ids)


def test_parse_element_id_format(tmp_path: Path):
    doc = _parse(tmp_path, "hello")
    eid = doc.elements[0].element_id
    assert "::e0000" in eid


def test_parse_locator_line_1_indexed(tmp_path: Path):
    doc = _parse(tmp_path, "first\n\nsecond")
    assert doc.elements[0].source_locator["line"] == 1
    assert doc.elements[1].source_locator["line"] == 3


def test_parse_strips_leading_trailing_whitespace(tmp_path: Path):
    doc = _parse(tmp_path, "  hello world  ")
    assert doc.elements[0].content == "hello world"


def test_parse_multiple_blank_lines_treated_as_one_separator(tmp_path: Path):
    doc = _parse(tmp_path, "a\n\n\n\nb")
    assert len(doc.elements) == 2


def test_parse_crlf_normalized(tmp_path: Path):
    """CRLF 换行归一。"""
    p = tmp_path / "test.txt"
    p.write_bytes(b"line1\r\nline2\r\n")
    doc = TextParser().parse(p, source_hash="a" * 64)
    # CRLF 归一后 "line1\nline2" → 1 个段落（无空行分隔）
    assert len(doc.elements) == 1
    assert "line1" in doc.elements[0].content
    assert "line2" in doc.elements[0].content


def test_parse_unicode_content_preserved(tmp_path: Path):
    doc = _parse(tmp_path, "你好世界\n\n日本語テスト")
    assert len(doc.elements) == 2
    assert "你好世界" in doc.elements[0].content
    assert "日本語テスト" in doc.elements[1].content


def test_parse_emoji_content_preserved(tmp_path: Path):
    doc = _parse(tmp_path, "hello 🌍 world")
    assert len(doc.elements) == 1
    assert "🌍" in doc.elements[0].content


# =========================================================================
# 大文件 stress
# =========================================================================


def test_parse_large_file_1000_paragraphs(tmp_path: Path):
    text = "\n\n".join(f"paragraph {i}" for i in range(1000))
    doc = _parse(tmp_path, text)
    assert len(doc.elements) == 1000


def test_parse_large_file_long_single_paragraph(tmp_path: Path):
    """单段落 100KB。"""
    text = "x" * 100_000
    doc = _parse(tmp_path, text)
    assert len(doc.elements) == 1
    assert len(doc.elements[0].content) == 100_000


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_contains_text_parser():
    from app.parsers import text_parser
    assert "TextParser" in text_parser.__all__


def test_module_all_only_lists_text_parser():
    from app.parsers import text_parser
    assert set(text_parser.__all__) == {"TextParser"}


def test_module_imports_path():
    from app.parsers import text_parser
    assert hasattr(text_parser, "Path")


def test_module_imports_document():
    from app.parsers import text_parser
    assert hasattr(text_parser, "Document")


def test_module_imports_element():
    from app.parsers import text_parser
    assert hasattr(text_parser, "Element")


def test_module_imports_warning_record():
    from app.parsers import text_parser
    assert hasattr(text_parser, "WarningRecord")


def test_module_imports_parser_base():
    from app.parsers import text_parser
    assert hasattr(text_parser, "Parser")


def test_module_imports_parser_error():
    from app.parsers import text_parser
    assert hasattr(text_parser, "ParserError")


def test_module_imports_make_document_id():
    from app.parsers import text_parser
    assert hasattr(text_parser, "make_document_id")


def test_text_parser_inherits_parser():
    from app.parsers.base import Parser
    assert issubclass(TextParser, Parser)


def test_text_parser_name_value():
    assert TextParser.name == "text"


def test_text_parser_version_value():
    assert TextParser.version == "stdlib/0.1.0"


def test_text_parser_has_parse_callable():
    assert callable(TextParser.parse)


def test_text_parser_docstring_present():
    """TextParser 类应有 docstring。"""
    assert TextParser.__doc__ is not None
