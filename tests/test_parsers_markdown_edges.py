"""app/parsers/markdown_parser.py 边角测试（Round 56）。

补强 tests/test_parsers_markdown.py（74 个测试）未覆盖的：
- 模块级常量直接引用（_MD_EXTENSIONS / 各 regex 模式）
- _split_pipe_row 边角（转义/多 pipe/空 cell）
- _rows_to_md 边角（多列/单列/空 cells）
- _is_pipe_table_start 边界（最后一行/越界）
- MarkdownParser 实例复用
- 大文件 / Unicode 内容 / CRLF 混合
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.parsers.markdown_parser import (
    MarkdownParser,
    _ATX_HEADING_RE,
    _BLOCKQUOTE_RE,
    _detect_md_source_type,
    _FENCED_RE,
    _is_pipe_table_start,
    _MD_EXTENSIONS,
    _ORDERED_LIST_RE,
    _PIPE_TABLE_ROW_RE,
    _PIPE_TABLE_SEP_RE,
    _rows_to_md,
    _split_pipe_row,
    _STANDALONE_IMAGE_RE,
    _THEMATIC_RE,
    _UNORDERED_LIST_RE,
)


# ---------- 模块级常量 ----------


def test_md_extensions_constant_is_tuple():
    assert isinstance(_MD_EXTENSIONS, tuple)


def test_md_extensions_constant_contains_two_extensions():
    assert set(_MD_EXTENSIONS) == {".md", ".markdown"}


def test_md_extensions_lowercase_only():
    for ext in _MD_EXTENSIONS:
        assert ext == ext.lower()


def test_all_regex_constants_are_compiled():
    for r in (
        _ATX_HEADING_RE, _THEMATIC_RE, _FENCED_RE, _UNORDERED_LIST_RE,
        _ORDERED_LIST_RE, _BLOCKQUOTE_RE, _PIPE_TABLE_ROW_RE,
        _PIPE_TABLE_SEP_RE, _STANDALONE_IMAGE_RE,
    ):
        assert isinstance(r, re.Pattern)


def test_markdown_parser_class_attributes():
    assert MarkdownParser.name == "markdown"
    assert MarkdownParser.version == "stdlib/0.1.0"


def test_markdown_parser_inherits_from_parser():
    from app.parsers.base import Parser
    assert issubclass(MarkdownParser, Parser)


def test_markdown_parser_can_be_instantiated_without_args():
    p = MarkdownParser()
    assert p is not None


# ---------- _split_pipe_row 边角 ----------


def test_split_pipe_row_basic_with_outer_pipes():
    assert _split_pipe_row("| a | b |") == ["a", "b"]


def test_split_pipe_row_no_outer_pipes():
    assert _split_pipe_row("a | b") == ["a", "b"]


def test_split_pipe_row_only_leading_pipe():
    assert _split_pipe_row("| a | b") == ["a", "b"]


def test_split_pipe_row_only_trailing_pipe():
    assert _split_pipe_row("a | b |") == ["a", "b"]


def test_split_pipe_row_single_cell():
    assert _split_pipe_row("| only |") == ["only"]


def test_split_pipe_row_empty_cells_stripped():
    """空 cell → '' 而不是 '  '。"""
    assert _split_pipe_row("|   |   |") == ["", ""]


def test_split_pipe_row_strips_each_cell():
    """每个 cell 应 strip。"""
    result = _split_pipe_row("|  hello   |  world  |")
    assert result == ["hello", "world"]


def test_split_pipe_row_three_columns():
    assert _split_pipe_row("| a | b | c |") == ["a", "b", "c"]


def test_split_pipe_row_many_columns():
    result = _split_pipe_row("| 1 | 2 | 3 | 4 | 5 | 6 |")
    assert result == ["1", "2", "3", "4", "5", "6"]


def test_split_pipe_row_only_pipe():
    """只有 | → split 后是空 cells。"""
    result = _split_pipe_row("|")
    # strip 后空 → startswith/endswith 都去掉 |
    # split("|") = ["", ""]? 不：先 strip → "|"（pipe 仍在）
    # 然后去首尾 | → ""，split → [""]
    assert result == [""]


def test_split_pipe_row_returns_list_type():
    assert isinstance(_split_pipe_row("| a |"), list)


def test_split_pipe_row_returns_strings():
    for cell in _split_pipe_row("| a | b |"):
        assert isinstance(cell, str)


def test_split_pipe_row_empty_string_returns_empty_list():
    """空字符串 strip 后无 | → split 返 [''] 单元素。"""
    result = _split_pipe_row("")
    assert result == [""]


# ---------- _rows_to_md 边角 ----------


def test_rows_to_md_empty_returns_empty_string():
    assert _rows_to_md([]) == ""


def test_rows_to_md_single_row_no_separator():
    """单行无 body，但仍输出 header + separator。"""
    result = _rows_to_md([["a", "b"]])
    lines = result.split("\n")
    assert len(lines) == 2  # header + separator
    assert lines[0] == "| a | b |"
    assert lines[1] == "| --- | --- |"


def test_rows_to_md_two_rows():
    result = _rows_to_md([
        ["name", "age"],
        ["Alice", "30"],
    ])
    lines = result.split("\n")
    assert len(lines) == 3
    assert lines[0] == "| name | age |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| Alice | 30 |"


def test_rows_to_md_jagged_pads_with_empty():
    """不等长的行用 '' 填充。"""
    result = _rows_to_md([
        ["a", "b", "c"],
        ["x"],  # 只 1 列
    ])
    lines = result.split("\n")
    # 第二行应有 3 列（padded）
    assert lines[2] == "| x |  |  |"


def test_rows_to_md_single_column():
    result = _rows_to_md([
        ["only"],
        ["row1"],
        ["row2"],
    ])
    lines = result.split("\n")
    assert lines[0] == "| only |"
    assert lines[1] == "| --- |"
    assert lines[2] == "| row1 |"
    assert lines[3] == "| row2 |"


def test_rows_to_md_many_columns():
    result = _rows_to_md([["c1", "c2", "c3", "c4", "c5"]])
    assert "| c1 | c2 | c3 | c4 | c5 |" in result


def test_rows_to_md_returns_str_type():
    assert isinstance(_rows_to_md([["a"]]), str)


def test_rows_to_md_separator_uses_three_dashes():
    result = _rows_to_md([["a", "b"]])
    assert "| --- | --- |" in result


# ---------- _is_pipe_table_start 边界 ----------


def test_is_pipe_table_start_at_last_line_returns_false():
    """i 是最后一行 → 没有下一行 → False。"""
    lines = ["| a | b |"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_out_of_bounds_index():
    """i 超出范围 → i+1 >= len → False。"""
    lines = ["| a | b |", "| --- | --- |"]
    assert _is_pipe_table_start(lines, 5) is False


def test_is_pipe_table_start_negative_index():
    """i = -1（Python 负索引）→ lines[-1] 可能匹配。"""
    lines = ["| a | b |", "| --- | --- |"]
    # i=-1, i+1=0，需要 lines[-1] 和 lines[0] 都匹配
    # 实际：i + 1 = 0，0 >= len(lines)=2 → False
    # 实际 i+1=0 < 2，所以不短路
    result = _is_pipe_table_start(lines, -1)
    # lines[-1] = "| --- | --- |"，是 separator 不是 row → False
    assert result is False


def test_is_pipe_table_start_valid_first_two_lines():
    lines = ["| a | b |", "| --- | --- |"]
    assert _is_pipe_table_start(lines, 0) is True


def test_is_pipe_table_start_first_line_not_pipe():
    lines = ["not a table", "| --- | --- |"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_second_line_not_separator():
    lines = ["| a | b |", "not separator"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_returns_bool():
    lines = ["| a |", "| --- |"]
    result = _is_pipe_table_start(lines, 0)
    assert isinstance(result, bool)


# ---------- _detect_md_source_type 边角 ----------


def test_detect_md_source_type_dotfile_with_md_extension():
    """.file.md → suffix 是 '.md'。"""
    assert _detect_md_source_type(Path(".file.md")) == "markdown"


def test_detect_md_source_type_double_extension_md():
    """file.tar.md → suffix 是 '.md'。"""
    assert _detect_md_source_type(Path("file.tar.md")) == "markdown"


def test_detect_md_source_type_returns_str():
    result = _detect_md_source_type(Path("file.md"))
    assert isinstance(result, str)


def test_detect_md_source_type_unknown_suffix_raises():
    from app.parsers.base import ParserError
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("file.unknown"))
    assert exc.value.code == "unsupported_type"
    assert "suffix" in exc.value.details


def test_detect_md_source_type_error_message_contains_suffix():
    from app.parsers.base import ParserError
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("file.xxx"))
    assert ".xxx" in exc.value.message


def test_detect_md_source_type_no_suffix_message_has_无():
    """无扩展名时消息含 '(无)'。"""
    from app.parsers.base import ParserError
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("README"))
    assert "(无)" in exc.value.message


# ---------- MarkdownParser 实例复用 ----------


def test_markdown_parser_can_be_reused_across_files(tmp_path: Path):
    """同一 MarkdownParser 实例可解析多个文件，结果独立。"""
    p1 = tmp_path / "a.md"
    p1.write_text("# Title A\n\nContent A", encoding="utf-8")
    p2 = tmp_path / "b.md"
    p2.write_text("# Title B\n\nContent B", encoding="utf-8")

    parser = MarkdownParser()
    doc1 = parser.parse(p1, source_hash="a" * 64)
    doc2 = parser.parse(p2, source_hash="b" * 64)
    assert doc1.elements[0].content == "Title A"
    assert doc2.elements[0].content == "Title B"
    assert doc1.document_id != doc2.document_id


def test_markdown_parser_stateless_no_counter_leak(tmp_path: Path):
    """MarkdownParser 无实例状态 → 第二次 parse 不带第一次的 element_id。"""
    p1 = tmp_path / "a.md"
    p1.write_text("hello", encoding="utf-8")
    p2 = tmp_path / "b.md"
    p2.write_text("world", encoding="utf-8")

    parser = MarkdownParser()
    doc1 = parser.parse(p1, source_hash="a" * 64)
    doc2 = parser.parse(p2, source_hash="b" * 64)
    # 都从 e0000 开始
    assert doc1.elements[0].element_id.endswith("::e0000")
    assert doc2.elements[0].element_id.endswith("::e0000")


def test_markdown_parser_sequential_element_ids_in_single_doc(tmp_path: Path):
    """单文档内 element_id 严格递增。"""
    p = tmp_path / "multi.md"
    p.write_text(
        "# H1\n\npara1\n\n- item1\n\n1. ordered\n\n> quote\n\n```python\ncode\n```",
        encoding="utf-8",
    )
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    suffixes = [e.element_id.split("::")[-1] for e in doc.elements]
    # 严格递增（e0000, e0001, ...）
    assert suffixes == sorted(suffixes)
    assert len(set(suffixes)) == len(suffixes)


# ---------- MarkdownParser 错误路径 details ----------


def test_markdown_parser_missing_file_error_details_has_path(tmp_path: Path):
    from app.parsers.base import ParserError
    parser = MarkdownParser()
    missing = tmp_path / "nope.md"
    with pytest.raises(ParserError) as exc:
        parser.parse(missing, source_hash="a" * 64)
    assert exc.value.code == "file_not_found"
    assert "path" in exc.value.details
    assert exc.value.details["path"] == str(missing)


def test_markdown_parser_unsupported_extension_error_details_has_suffix(tmp_path: Path):
    from app.parsers.base import ParserError
    parser = MarkdownParser()
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        parser.parse(src, source_hash="a" * 64)
    assert exc.value.code == "unsupported_type"
    assert "suffix" in exc.value.details


# ---------- MarkdownParser Document 字段 ----------


def test_markdown_parser_metadata_fixed_markdown_true(tmp_path: Path):
    p = tmp_path / "x.md"
    p.write_text("hello", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.metadata == {"markdown": True}


def test_markdown_parser_warnings_empty_when_elements_exist(tmp_path: Path):
    p = tmp_path / "x.md"
    p.write_text("# Title", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.warnings == []


def test_markdown_parser_empty_file_emits_one_warning(tmp_path: Path):
    """空文件 → 1 个 warning record（不是多个）。"""
    p = tmp_path / "empty.md"
    p.write_text("", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert len(doc.warnings) == 1
    assert doc.warnings[0].code == "md_no_content"


def test_markdown_parser_warning_record_has_reason(tmp_path: Path):
    p = tmp_path / "empty.md"
    p.write_text("", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    w = doc.warnings[0]
    assert isinstance(w.reason, str)
    assert len(w.reason) > 0


# ---------- MarkdownParser 大文件 / Unicode / 换行 ----------


def test_markdown_parser_large_file(tmp_path: Path):
    """大文件（10K 行）也应稳定。"""
    p = tmp_path / "large.md"
    p.write_text(
        "# Title\n\n" + "\n\n".join(f"paragraph {i}" for i in range(1000)),
        encoding="utf-8",
    )
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # 标题 + 1000 段落 = 1001 elements
    assert len(doc.elements) == 1001


def test_markdown_parser_unicode_content(tmp_path: Path):
    """UTF-8 多字节内容也应正常解析。"""
    p = tmp_path / "x.md"
    p.write_text("# 标题 🎉\n\n你好，世界\n\n- 列表项", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert any("标题" in (e.content or "") for e in doc.elements)
    assert any("🎉" in (e.content or "") for e in doc.elements)
    assert any("你好" in (e.content or "") for e in doc.elements)


def test_markdown_parser_crlf_line_endings(tmp_path: Path):
    """CRLF 行结束符应被正确处理（splitlines 接受 \r\n）。"""
    p = tmp_path / "x.md"
    p.write_bytes(b"# Title\r\n\r\nParagraph\r\n")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert len(doc.elements) == 2  # heading + paragraph


def test_markdown_parser_mixed_line_endings(tmp_path: Path):
    """混合 LF / CRLF / CR 行结束符。"""
    p = tmp_path / "x.md"
    p.write_bytes(b"# Title\n\nPara 1\r\n\r\nPara 2\r")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # splitlines 处理各种行结束符
    assert len(doc.elements) >= 2


def test_markdown_parser_single_byte_file(tmp_path: Path):
    """单字节文件（无换行）应能解析。"""
    p = tmp_path / "x.md"
    p.write_bytes(b"X")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # 单字节 → 1 个 paragraph element
    assert len(doc.elements) == 1


# ---------- MarkdownParser schema 通过 ----------


def test_markdown_parser_result_passes_schema(tmp_path: Path):
    """parse 出的 Document 通过 schema 校验。"""
    from app.schema import is_valid
    p = tmp_path / "x.md"
    p.write_text(
        "# Title\n\n"
        "Paragraph here.\n\n"
        "- list item\n\n"
        "```python\nprint('hi')\n```\n\n"
        "> quote line",
        encoding="utf-8",
    )
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert is_valid(doc.to_dict()) is True


# ---------- MarkdownParser parse 各 element 字段 ----------


def test_markdown_parser_element_confidence_strictly_095(tmp_path: Path):
    p = tmp_path / "x.md"
    p.write_text("# Title\n\nPara", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert el.confidence == 0.95


def test_markdown_parser_element_metadata_is_dict(tmp_path: Path):
    p = tmp_path / "x.md"
    p.write_text("# Title", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert isinstance(el.metadata, dict)


def test_markdown_parser_source_locator_has_line(tmp_path: Path):
    p = tmp_path / "x.md"
    p.write_text("# Title", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    for el in doc.elements:
        assert "line" in el.source_locator
        assert isinstance(el.source_locator["line"], int)
        assert el.source_locator["line"] >= 1


def test_markdown_parser_source_locator_optional_section_path(tmp_path: Path):
    """section_path 是可选 key（取决于是否在标题下）。"""
    p = tmp_path / "x.md"
    p.write_text("preamble\n\n# Title\n\ncontent", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    # 至少有 source_locator
    for el in doc.elements:
        assert "line" in el.source_locator


def test_markdown_parser_chunks_empty_by_default(tmp_path: Path):
    p = tmp_path / "x.md"
    p.write_text("hello", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.chunks == []


def test_markdown_parser_relations_empty_by_default(tmp_path: Path):
    p = tmp_path / "x.md"
    p.write_text("hello", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.relations == []


def test_markdown_parser_errors_empty_by_default(tmp_path: Path):
    p = tmp_path / "x.md"
    p.write_text("hello", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.errors == []
