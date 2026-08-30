"""app/parsers/text_parser.py 边角测试（Round 55）。

补强 tests/test_parsers_text.py（52 个测试）未覆盖的：
- 模块级常量 _TEXT_EXTENSIONS
- _split_paragraphs 极端边角（首尾换行、单字符、纯空白行混入）
- TextParser 实例复用（多次 parse 不互相影响）
- _detect_text_source_type 边角（大小写混合、长度为 0 的 suffix）
- 错误消息内容验证（details 字段）
- element_id 严格顺序
- Document metadata 固定 {"text": True}
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.parsers.text_parser import (
    TextParser,
    _TEXT_EXTENSIONS,
    _detect_text_source_type,
    _split_paragraphs,
)


# ---------- 模块级常量 ----------


def test_text_extensions_constant_is_tuple():
    assert isinstance(_TEXT_EXTENSIONS, tuple)


def test_text_extensions_constant_contains_two_extensions():
    assert set(_TEXT_EXTENSIONS) == {".txt", ".text"}


def test_text_extensions_constant_lowercase_only():
    """常量只含小写（.TXT 不在内，靠 lower() 转换）。"""
    for ext in _TEXT_EXTENSIONS:
        assert ext == ext.lower()


def test_text_parser_class_attributes():
    """TextParser 类属性：name='text', version='stdlib/0.1.0'。"""
    assert TextParser.name == "text"
    assert TextParser.version == "stdlib/0.1.0"


def test_text_parser_class_inherits_from_parser():
    from app.parsers.base import Parser
    assert issubclass(TextParser, Parser)


def test_text_parser_can_be_instantiated_without_args():
    """TextParser 无构造参数。"""
    p = TextParser()
    assert p is not None


def test_text_parser_has_parse_method():
    p = TextParser()
    assert callable(p.parse)


# ---------- _split_paragraphs 极端边角 ----------


def test_split_paragraphs_text_starts_with_newline():
    """以换行开头 → 第一行空白被跳过，正文从第 2 行起算。"""
    result = _split_paragraphs("\nhello")
    assert len(result) == 1
    start_line, content = result[0]
    assert start_line == 2  # 第 1 行空白，正文从第 2 行
    assert content == "hello"


def test_split_paragraphs_text_ends_with_newline():
    """以换行结尾 → 最后一段被收集，无尾部空段。"""
    result = _split_paragraphs("hello\n")
    assert len(result) == 1
    assert result[0] == (1, "hello")


def test_split_paragraphs_text_starts_and_ends_with_newline():
    """前后都有换行 → 单段从第 2 行算，无尾部空段。"""
    result = _split_paragraphs("\nhello\n")
    assert len(result) == 1
    assert result[0] == (2, "hello")


def test_split_paragraphs_single_character():
    """单字符内容。"""
    result = _split_paragraphs("X")
    assert result == [(1, "X")]


def test_split_paragraphs_single_digit():
    """单数字内容。"""
    result = _split_paragraphs("7")
    assert result == [(1, "7")]


def test_split_paragraphs_content_with_internal_newlines():
    """段落内的换行应保留在 content 中。"""
    # 无空行分隔 → 整体作为一个段落
    result = _split_paragraphs("line1\nline2\nline3")
    assert len(result) == 1
    assert result[0][1] == "line1\nline2\nline3"


def test_split_paragraphs_content_with_tabs():
    """tab 字符内容应保留（但首尾 strip 会去掉段首段尾空白）。

    实际：'\\ta\\n\\tb' → 收集两行 → join '\\ta\\n\\tb' → strip → 'a\\n\\tb'
    （首尾的 \\t 被去，中间 \\t 保留）。"""
    result = _split_paragraphs("\ta\n\tb")
    assert len(result) == 1
    # 内部换行 + 中间 tab 保留，但首尾 tab 被 strip
    assert result[0][1] == "a\n\tb"


def test_split_paragraphs_mixed_line_endings_crlf_cr_lf():
    """混合换行符 → 全部归一为 LF 后再切。"""
    result = _split_paragraphs("line1\r\nline2\rline3\n\nparagraph2")
    # CRLF/CR/LF 都归一为 LF → "line1\nline2\nline3\n\nparagraph2"
    # 空行分隔 → 2 个段落
    assert len(result) == 2
    assert "line1" in result[0][1]
    assert "line2" in result[0][1]
    assert "line3" in result[0][1]
    assert result[1][1] == "paragraph2"


def test_split_paragraphs_consecutive_blank_lines_treated_as_one():
    """连续空行视为单个分隔。"""
    result = _split_paragraphs("a\n\n\n\nb")
    assert len(result) == 2
    assert result[0] == (1, "a")
    # 第 2 行空白，第 3 行空白，第 4 行空白，b 在第 5 行
    assert result[1] == (5, "b")


def test_split_paragraphs_zero_paragraphs_for_empty():
    assert _split_paragraphs("") == []


def test_split_paragraphs_zero_paragraphs_for_whitespace_only():
    assert _split_paragraphs("   \n\t\n  ") == []


def test_split_paragraphs_zero_paragraphs_for_newline_only():
    assert _split_paragraphs("\n\n\n") == []


def test_split_paragraphs_returns_list_of_tuples():
    """返回 list[tuple[int, str]]。"""
    result = _split_paragraphs("hello\n\nworld")
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, tuple)
        assert len(item) == 2
        assert isinstance(item[0], int)
        assert isinstance(item[1], str)


def test_split_paragraphs_start_line_strictly_increasing():
    """start_line 应严格递增。"""
    result = _split_paragraphs("p1\n\np2\n\np3\n\np4")
    lines = [r[0] for r in result]
    assert lines == sorted(lines)
    # 严格递增（无重复）
    assert len(lines) == len(set(lines))


# ---------- _detect_text_source_type 边角 ----------


def test_detect_text_source_type_mixed_case_extension():
    """大小写混合扩展名 → lower 后识别。"""
    assert _detect_text_source_type(Path("file.Txt")) == "text"
    assert _detect_text_source_type(Path("file.tXt")) == "text"
    assert _detect_text_source_type(Path("file.TEXT")) == "text"


def test_detect_text_source_type_double_extension():
    """双扩展名 → suffix 取最后一个。"""
    # "archive.tar.txt" 的 suffix 是 ".txt"
    assert _detect_text_source_type(Path("archive.tar.txt")) == "text"


def test_detect_text_source_type_dotfile():
    """.gitignore suffix 是 ".gitignore"（整个文件名）→ 不在 _TEXT_EXTENSIONS。"""
    with pytest.raises(Exception):  # ParserError 或其他
        _detect_text_source_type(Path(".gitignore"))


def test_detect_text_source_type_no_suffix_raises():
    """无扩展名 → suffix 是空串 → raise。"""
    with pytest.raises(Exception):
        _detect_text_source_type(Path("README"))


def test_detect_text_source_type_unknown_suffix_raises():
    with pytest.raises(Exception):
        _detect_text_source_type(Path("file.unknown"))


def test_detect_text_source_type_returns_str_on_success():
    """成功时返 str（不是 bytes 或其他类型）。"""
    result = _detect_text_source_type(Path("file.txt"))
    assert isinstance(result, str)


def test_detect_text_source_type_error_includes_suffix_in_details():
    """ParserError 的 details 应含 suffix 字段。"""
    from app.parsers.base import ParserError
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("file.unknown"))
    assert "suffix" in exc.value.details
    assert exc.value.details["suffix"] == ".unknown"


# ---------- TextParser 实例复用 ----------


def test_text_parser_can_be_reused_across_files(tmp_path: Path):
    """同一 TextParser 实例可解析多个文件，结果独立。"""
    p1 = tmp_path / "a.txt"
    p1.write_text("first file content", encoding="utf-8")
    p2 = tmp_path / "b.txt"
    p2.write_text("second file content", encoding="utf-8")

    parser = TextParser()
    doc1 = parser.parse(p1, source_hash="a" * 64)
    doc2 = parser.parse(p2, source_hash="b" * 64)
    assert doc1.elements[0].content == "first file content"
    assert doc2.elements[0].content == "second file content"
    assert doc1.document_id != doc2.document_id  # 不同 hash → 不同 id


def test_text_parser_stateless_no_counter_leak(tmp_path: Path):
    """TextParser 无实例状态 → 第二次 parse 不带第一次的 element_id。"""
    p1 = tmp_path / "a.txt"
    p1.write_text("first", encoding="utf-8")
    p2 = tmp_path / "b.txt"
    p2.write_text("second", encoding="utf-8")

    parser = TextParser()
    doc1 = parser.parse(p1, source_hash="a" * 64)
    doc2 = parser.parse(p2, source_hash="b" * 64)
    # 都从 e0000 开始
    assert doc1.elements[0].element_id.endswith("::e0000")
    assert doc2.elements[0].element_id.endswith("::e0000")


def test_text_parser_sequential_element_ids_in_single_doc(tmp_path: Path):
    """单个文档内 element_id 严格递增（e0000, e0001, ...）。"""
    p = tmp_path / "multi.txt"
    p.write_text("para1\n\npara2\n\npara3\n\npara4", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, source_hash="a" * 64)
    ids = [e.element_id for e in doc.elements]
    suffixes = [eid.split("::")[-1] for eid in ids]
    assert suffixes == ["e0000", "e0001", "e0002", "e0003"]


# ---------- TextParser 错误路径 details ----------


def test_text_parser_missing_file_error_details_has_path(tmp_path: Path):
    from app.parsers.base import ParserError
    parser = TextParser()
    missing = tmp_path / "nope.txt"
    with pytest.raises(ParserError) as exc:
        parser.parse(missing, source_hash="a" * 64)
    assert exc.value.code == "file_not_found"
    assert "path" in exc.value.details
    assert exc.value.details["path"] == str(missing)


def test_text_parser_unsupported_extension_error_details_has_suffix(tmp_path: Path):
    from app.parsers.base import ParserError
    parser = TextParser()
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        parser.parse(src, source_hash="a" * 64)
    assert exc.value.code == "unsupported_type"
    assert "suffix" in exc.value.details
    assert exc.value.details["suffix"] == ".unknown"


# ---------- TextParser Document 字段 ----------


def test_text_parser_metadata_fixed_text_true(tmp_path: Path):
    """metadata 固定 {"text": True}。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.metadata == {"text": True}


def test_text_parser_warnings_empty_when_elements_exist(tmp_path: Path):
    """有 elements 时 warnings 应为空。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.warnings == []


def test_text_parser_warnings_has_one_record_when_empty(tmp_path: Path):
    """空文件时 warnings 应有 1 个 record（不是多个）。"""
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert len(doc.warnings) == 1
    assert doc.warnings[0].code == "text_no_content"


def test_text_parser_warning_record_has_reason(tmp_path: Path):
    """warning record 应有非空 reason。"""
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, source_hash="a" * 64)
    w = doc.warnings[0]
    assert w.reason
    assert isinstance(w.reason, str)
    assert len(w.reason) > 0


# ---------- TextParser schema 通过 ----------


def test_text_parser_result_passes_schema(tmp_path: Path):
    """parse 出的 Document 通过 schema 校验。"""
    from app.schema import is_valid
    p = tmp_path / "x.txt"
    p.write_text("hello\n\nworld", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert is_valid(doc.to_dict()) is True


def test_text_parser_element_confidence_strictly_095(tmp_path: Path):
    """所有 element 的 confidence 固定 0.95。"""
    p = tmp_path / "x.txt"
    p.write_text("a\n\nb\n\nc", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.confidence == 0.95


def test_text_parser_element_metadata_empty_dict(tmp_path: Path):
    """每个 element 的 metadata 是空 dict（不是 None）。"""
    p = tmp_path / "x.txt"
    p.write_text("a\n\nb", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.metadata == {}


def test_text_parser_element_parent_id_none(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("a", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.parent_id is None


def test_text_parser_source_locator_has_line_key(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("a", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert "line" in el.source_locator
        assert isinstance(el.source_locator["line"], int)
        assert el.source_locator["line"] >= 1


def test_text_parser_source_locator_only_line_key(tmp_path: Path):
    """source_locator 只含 family + line（不应有 section_path 等）。"""
    p = tmp_path / "x.txt"
    p.write_text("a", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.source_locator["family"] == "line_address"
        assert set(el.source_locator.keys()) == {"family", "line"}


# ---------- 文件大小边角 ----------


def test_text_parser_single_byte_file(tmp_path: Path):
    """单字节文件应能解析。"""
    p = tmp_path / "x.txt"
    p.write_bytes(b"X")
    parser = TextParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].content == "X"


def test_text_parser_large_file(tmp_path: Path):
    """大文件（10K 行）也应稳定。"""
    p = tmp_path / "large.txt"
    p.write_text("\n".join(f"line {i}" for i in range(10000)), encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # 无空行 → 全部作为一个段落
    assert len(doc.elements) == 1


def test_text_parser_unicode_content(tmp_path: Path):
    """UTF-8 多字节内容也应正常解析。"""
    p = tmp_path / "x.txt"
    p.write_text("你好，世界\n\nHello, World\n\n🎉 emoji", encoding="utf-8")
    parser = TextParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert len(doc.elements) == 3
    assert doc.elements[0].content == "你好，世界"
    assert doc.elements[1].content == "Hello, World"
    assert doc.elements[2].content == "🎉 emoji"


# ---------- _detect_text_source_type 错误消息 ----------


def test_detect_text_source_type_error_message_contains_suffix():
    """错误消息应含传入的 suffix（或 '(无)'）。"""
    from app.parsers.base import ParserError
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("file.unknown"))
    msg = exc.value.message
    assert ".unknown" in msg


def test_detect_text_source_type_error_message_for_no_suffix():
    """无扩展名时错误消息含 '(无)'。"""
    from app.parsers.base import ParserError
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("README"))
    msg = exc.value.message
    assert "(无)" in msg
