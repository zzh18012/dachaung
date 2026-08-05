r"""app/parsers/markdown_parser.py 边角测试 - 第七轮（Round 184）。

补强已有 base/edges/edges2-6（共 831 测试）未覆盖的深度：
- _detect_md_source_type：大写后缀、未知后缀、无后缀
- _rows_to_md：空 list、单 row、多 row padding、列对齐填充
- _split_pipe_row：无 leading/trailing pipe、内嵌空白
- _is_pipe_table_start：i+1 越界、单行、分隔行不匹配
- ATX 标题：6 级、trailing #、7+ # 不匹配、空 title
- 围栏代码块：language 提取、~~~ fence、空内容 warning
- 引用块：连续 > 合并、空 quoted 不 push
- section_path 跟踪：多级标题、同级 pop、更高级 pop 多个
- MarkdownParser 类属性 name/version、继承 Parser
- 段落停止条件：每个特殊行类型都触发停止
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from app.models import Document, Element, WarningRecord
from app.parsers.base import Parser, ParserError
from app.parsers.markdown_parser import (
    _ATX_HEADING_RE,
    _BLOCKQUOTE_RE,
    _detect_md_source_type,
    _FENCED_RE,
    _is_pipe_table_start,
    _ORDERED_LIST_RE,
    _PIPE_TABLE_ROW_RE,
    _PIPE_TABLE_SEP_RE,
    _rows_to_md,
    _split_pipe_row,
    _STANDALONE_IMAGE_RE,
    _THEMATIC_RE,
    _UNORDERED_LIST_RE,
    MarkdownParser,
)


# =========================================================================
# _detect_md_source_type 深度
# =========================================================================


def test_detect_md_source_type_md_uppercase():
    """后缀小写化比较：.MD 也能识别。"""
    assert _detect_md_source_type(Path("a.MD")) == "markdown"


def test_detect_md_source_type_markdown_uppercase():
    assert _detect_md_source_type(Path("a.MARKDOWN")) == "markdown"


def test_detect_md_source_type_mixed_case():
    assert _detect_md_source_type(Path("a.Md")) == "markdown"


def test_detect_md_source_type_unknown_suffix_raises():
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("a.txt"))
    assert exc.value.code == "unsupported_type"


def test_detect_md_source_type_no_suffix_raises():
    with pytest.raises(ParserError):
        _detect_md_source_type(Path("README"))


def test_detect_md_source_type_error_has_details():
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("a.txt"))
    assert "suffix" in exc.value.details
    assert exc.value.details["suffix"] == ".txt"


def test_detect_md_source_type_error_message_contains_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("a.html"))
    assert ".html" in str(exc.value)


def test_detect_md_source_type_no_suffix_details_empty_string():
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("README"))
    assert exc.value.details["suffix"] == ""


# =========================================================================
# _rows_to_md 深度
# =========================================================================


def test_rows_to_md_empty_returns_empty():
    assert _rows_to_md([]) == ""


def test_rows_to_md_single_row():
    result = _rows_to_md([["a", "b"]])
    assert "a" in result
    assert "b" in result
    assert "---" in result  # 分隔行


def test_rows_to_md_single_column():
    result = _rows_to_md([["h"], ["v1"], ["v2"]])
    lines = result.split("\n")
    # header + separator + 2 body = 4 lines
    assert len(lines) == 4


def test_rows_to_md_pads_uneven_rows():
    """rows 长度不一时 padding 到 max width。"""
    result = _rows_to_md([
        ["h1", "h2", "h3"],
        ["v1"],  # 缺 h2/h3
    ])
    # 不会因缺列崩
    assert "h1" in result
    assert "v1" in result


def test_rows_to_md_separator_uses_three_dashes():
    result = _rows_to_md([["a", "b"]])
    assert "---" in result


def test_rows_to_md_no_body_just_header_and_sep():
    """单 row（仅 header）→ 输出 header + separator。"""
    result = _rows_to_md([["a", "b"]])
    lines = result.split("\n")
    assert len(lines) == 2


def test_rows_to_md_returns_str():
    assert isinstance(_rows_to_md([["a"]]), str)


def test_rows_to_md_pipe_at_edges():
    result = _rows_to_md([["a", "b"]])
    lines = result.split("\n")
    for line in lines:
        assert line.startswith("| ")
        assert line.endswith(" |")


# =========================================================================
# _split_pipe_row 深度
# =========================================================================


def test_split_pipe_row_with_leading_and_trailing_pipe():
    assert _split_pipe_row("|a|b|c|") == ["a", "b", "c"]


def test_split_pipe_row_without_pipes():
    assert _split_pipe_row("a|b|c") == ["a", "b", "c"]


def test_split_pipe_row_only_leading_pipe():
    assert _split_pipe_row("|a|b|c") == ["a", "b", "c"]


def test_split_pipe_row_only_trailing_pipe():
    assert _split_pipe_row("a|b|c|") == ["a", "b", "c"]


def test_split_pipe_row_strips_each_cell():
    assert _split_pipe_row("| a | b | c |") == ["a", "b", "c"]


def test_split_pipe_row_single_cell():
    assert _split_pipe_row("|abc|") == ["abc"]


def test_split_pipe_row_empty_string():
    """空串：strip 后空，startswith/endwith 都 false，split('|') -> ['']。"""
    result = _split_pipe_row("")
    assert result == [""]


def test_split_pipe_row_returns_list():
    assert isinstance(_split_pipe_row("|a|"), list)


# =========================================================================
# _is_pipe_table_start 深度
# =========================================================================


def test_is_pipe_table_start_at_last_line_returns_false():
    """i+1 越界 → False。"""
    lines = ["| a | b |"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_valid_table():
    lines = ["| a | b |", "| --- | --- |", "| 1 | 2 |"]
    assert _is_pipe_table_start(lines, 0) is True


def test_is_pipe_table_start_no_separator_second_line():
    lines = ["| a | b |", "| 1 | 2 |"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_first_line_not_pipe():
    lines = ["hello", "| --- | --- |"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_returns_bool():
    lines = ["| a |"]
    result = _is_pipe_table_start(lines, 0)
    assert isinstance(result, bool)


# =========================================================================
# ATX 标题深度
# =========================================================================


def test_atx_heading_regex_matches_one_to_six_hashes():
    for n in range(1, 7):
        m = _ATX_HEADING_RE.match("#" * n + " Title")
        assert m is not None


def test_atx_heading_regex_does_not_match_seven_hashes():
    m = _ATX_HEADING_RE.match("####### Title")
    assert m is None


def test_atx_heading_regex_matches_trailing_hashes():
    m = _ATX_HEADING_RE.match("## Title ##")
    assert m is not None
    assert m.group(2).strip() == "Title"


def test_atx_heading_regex_no_space_after_hashes_does_not_match():
    """`#Title`（无空格）不匹配。"""
    m = _ATX_HEADING_RE.match("#Title")
    assert m is None


def test_atx_heading_regex_extracts_level():
    m = _ATX_HEADING_RE.match("### Sub")
    assert len(m.group(1)) == 3


def test_atx_heading_regex_extracts_title():
    m = _ATX_HEADING_RE.match("# Hello World")
    assert m.group(2) == "Hello World"


def test_parse_atx_heading_level_recorded_in_metadata(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("### Section\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].metadata["level"] == 3


def test_parse_atx_heading_six_levels(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("# H1\n## H2\n### H3\n#### H4\n##### H5\n###### H6\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    levels = [el.metadata["level"] for el in doc.elements]
    assert levels == [1, 2, 3, 4, 5, 6]


def test_parse_atx_heading_with_trailing_hashes(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("## Title ##\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].content == "Title"


# =========================================================================
# 围栏代码块深度
# =========================================================================


def test_parse_fenced_code_with_language(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("```python\nprint(1)\n```\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].metadata["language"] == "python"
    assert doc.elements[0].metadata["kind"] == "code_block"


def test_parse_fenced_code_tilde_fence(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("~~~\ncode\n~~~\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert "code" in doc.elements[0].content


def test_parse_fenced_code_empty_emits_warning(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("```\n```\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    # 空 code block → warning，无 element
    warning_codes = [w.code for w in doc.warnings]
    assert "md_empty_code_block" in warning_codes


def test_parse_fenced_code_no_end_fence_takes_rest(tmp_path: Path):
    """没有结束围栏时，吸收到文件末尾。"""
    p = tmp_path / "test.md"
    p.write_text("```\ncode without end\nmore code\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    # 仍然 push 一个 code block
    assert any(el.metadata.get("kind") == "code_block" for el in doc.elements)


def test_parse_fenced_code_content_joins_lines(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("```\nline1\nline2\nline3\n```\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].content == "line1\nline2\nline3"


def test_parse_fenced_code_without_language_empty_string(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("```\ncode\n```\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].metadata["language"] == ""


# =========================================================================
# 主题分隔符深度
# =========================================================================


def test_thematic_regex_matches_three_chars():
    """主题分隔符需 ≥ 3 个字符。"""
    assert _THEMATIC_RE.match("---")
    assert _THEMATIC_RE.match("***")
    assert _THEMATIC_RE.match("___")


def test_thematic_regex_matches_longer():
    assert _THEMATIC_RE.match("----")
    assert _THEMATIC_RE.match("*****")


def test_thematic_regex_with_spaces_between():
    assert _THEMATIC_RE.match("- - -")
    assert _THEMATIC_RE.match("* * *")


def test_thematic_regex_does_not_match_two_chars():
    assert not _THEMATIC_RE.match("--")
    assert not _THEMATIC_RE.match("**")


def test_thematic_regex_does_not_match_letters():
    assert not _THEMATIC_RE.match("abc")
    assert not _THEMATIC_RE.match("---a")


def test_parse_thematic_break_skipped(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("---\n***\n___\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    # 全部 thematic → 无 element + md_no_content warning
    assert doc.elements == []
    assert any(w.code == "md_no_content" for w in doc.warnings)


def test_parse_thematic_break_skips_various_with_spaces(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("- - -\n* * *\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements == []


# =========================================================================
# 独立图片行深度
# =========================================================================


def test_standalone_image_regex_matches_full_line():
    m = _STANDALONE_IMAGE_RE.match("![alt text](url.png)")
    assert m is not None
    assert m.group(1) == "alt text"
    assert m.group(2) == "url.png"


def test_standalone_image_regex_empty_alt():
    m = _STANDALONE_IMAGE_RE.match("![](url.png)")
    assert m is not None
    assert m.group(1) == ""


def test_standalone_image_regex_no_match_with_text_after():
    m = _STANDALONE_IMAGE_RE.match("![alt](url.png) more text")
    assert m is None


def test_standalone_image_regex_no_match_inline():
    m = _STANDALONE_IMAGE_RE.match("text ![alt](url.png)")
    assert m is None


def test_standalone_image_regex_url_with_path():
    m = _STANDALONE_IMAGE_RE.match("![alt](https://example.com/path/img.png)")
    assert m is not None


def test_parse_standalone_image(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("![logo](logo.png)\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "image"
    assert doc.elements[0].resource_path == "logo.png"
    assert doc.elements[0].metadata["alt"] == "logo"
    assert doc.elements[0].content is None


# =========================================================================
# 列表项深度
# =========================================================================


def test_unordered_list_regex_minus():
    m = _UNORDERED_LIST_RE.match("- item")
    assert m is not None
    assert m.group(1) == "item"


def test_unordered_list_regex_plus():
    m = _UNORDERED_LIST_RE.match("+ item")
    assert m is not None


def test_unordered_list_regex_asterisk():
    m = _UNORDERED_LIST_RE.match("* item")
    assert m is not None


def test_unordered_list_regex_no_match_no_space():
    m = _UNORDERED_LIST_RE.match("-item")
    assert m is None


def test_unordered_list_regex_no_match_dash_dash():
    m = _UNORDERED_LIST_RE.match("-- item")
    assert m is None


def test_ordered_list_regex_dot():
    m = _ORDERED_LIST_RE.match("1. item")
    assert m is not None
    assert m.group(1) == "item"


def test_ordered_list_regex_paren():
    m = _ORDERED_LIST_RE.match("1) item")
    assert m is not None


def test_ordered_list_regex_two_digit():
    m = _ORDERED_LIST_RE.match("10. item")
    assert m is not None


def test_ordered_list_regex_no_match_no_space():
    m = _ORDERED_LIST_RE.match("1.item")
    assert m is None


def test_parse_list_item_metadata_marker(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("- a\n+ b\n* c\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    markers = [el.metadata.get("marker") for el in doc.elements]
    assert markers == ["unordered", "unordered", "unordered"]


def test_parse_list_item_metadata_ordered_flag(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("1. a\n2. b\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    for el in doc.elements:
        assert el.metadata["ordered"] is True


# =========================================================================
# 引用块深度
# =========================================================================


def test_blockquote_regex_basic():
    m = _BLOCKQUOTE_RE.match("> text")
    assert m is not None
    assert m.group(1) == "text"


def test_blockquote_regex_no_space_after_gt():
    m = _BLOCKQUOTE_RE.match(">text")
    assert m is not None
    assert m.group(1) == "text"


def test_blockquote_regex_nested_marker():
    m = _BLOCKQUOTE_RE.match(">> nested")
    # `>>` 也匹配（第二个 `>` 留在 group 1）
    assert m is not None


def test_parse_blockquote_multi_line_joined(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("> line1\n> line2\n> line3\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert doc.elements[0].content == "line1\nline2\nline3"
    assert doc.elements[0].metadata["kind"] == "blockquote"


def test_parse_blockquote_kind_in_metadata(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("> quoted\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].metadata["kind"] == "blockquote"


# =========================================================================
# section_path 跟踪深度
# =========================================================================


def test_parse_section_path_tracks_levels(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text(
        "# Chapter\n"
        "para1\n"
        "## Section\n"
        "para2\n"
        "### Sub\n"
        "para3\n",
        encoding="utf-8",
    )
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    paragraphs = [el for el in doc.elements if el.type == "paragraph"]
    assert paragraphs[0].source_locator["section_path"] == "Chapter"
    assert paragraphs[1].source_locator["section_path"] == "Chapter > Section"
    assert paragraphs[2].source_locator["section_path"] == "Chapter > Section > Sub"


def test_parse_section_path_pops_on_same_level(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text(
        "# A\n"
        "## A1\n"
        "## A2\n"  # 同级 → pop A1
        "para under A2\n",
        encoding="utf-8",
    )
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    paragraph = next(el for el in doc.elements if el.type == "paragraph")
    assert paragraph.source_locator["section_path"] == "A > A2"


def test_parse_section_path_pops_on_higher_level(tmp_path: Path):
    """高级标题弹出更深层的所有低级标题。"""
    p = tmp_path / "test.md"
    p.write_text(
        "# A\n"
        "## A1\n"
        "### A1a\n"
        "# B\n"  # level 1 → pop A1a, A1, A
        "para under B\n",
        encoding="utf-8",
    )
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    paragraph = next(el for el in doc.elements if el.type == "paragraph")
    assert paragraph.source_locator["section_path"] == "B"


def test_parse_section_path_no_headings_empty(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("just a paragraph\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    paragraph = doc.elements[0]
    # 无 heading → section_path 不在 locator 中
    assert "section_path" not in paragraph.source_locator


def test_parse_heading_no_section_path_in_locator(tmp_path: Path):
    """heading 元素的 locator 也包含当前 section_path（其本身在栈内）。"""
    p = tmp_path / "test.md"
    p.write_text("# Title\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    heading = doc.elements[0]
    # heading 推入栈后才生成 locator，所以 section_path = "Title"
    assert heading.source_locator["section_path"] == "Title"


# =========================================================================
# MarkdownParser 类属性
# =========================================================================


def test_markdown_parser_name_attribute():
    assert MarkdownParser.name == "markdown"


def test_markdown_parser_version_attribute():
    assert MarkdownParser.version == "stdlib/0.1.0"


def test_markdown_parser_inherits_parser():
    assert issubclass(MarkdownParser, Parser)


def test_markdown_parser_parse_inherited_signature():
    sig = inspect.signature(MarkdownParser.parse)
    assert set(sig.parameters) == {"self", "path", "source_hash"}


def test_markdown_parser_parse_no_defaults():
    sig = inspect.signature(MarkdownParser.parse)
    for name in ("path", "source_hash"):
        assert sig.parameters[name].default is inspect.Parameter.empty


# =========================================================================
# parse 错误路径深度
# =========================================================================


def test_parse_missing_file_raises_parser_error(tmp_path: Path):
    parser = MarkdownParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(tmp_path / "missing.md", "a" * 64)
    assert exc.value.code == "file_not_found"


def test_parse_missing_file_error_message_contains_path(tmp_path: Path):
    parser = MarkdownParser()
    missing = tmp_path / "missing.md"
    with pytest.raises(ParserError) as exc:
        parser.parse(missing, "a" * 64)
    assert str(missing) in str(exc.value)


def test_parse_unsupported_suffix_raises(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello", encoding="utf-8")
    parser = MarkdownParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert exc.value.code == "unsupported_type"


def test_parse_read_oserror_raises_parser_error(tmp_path: Path, monkeypatch):
    """读文件 OSError → 转 ParserError。"""
    p = tmp_path / "test.md"
    p.write_text("hello", encoding="utf-8")

    def fake_read_text(self, *args, **kwargs):
        raise OSError("simulated")

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    parser = MarkdownParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert exc.value.code == "md_read_failed"


def test_parse_read_oserror_error_has_exception_type(tmp_path: Path, monkeypatch):
    p = tmp_path / "test.md"
    p.write_text("hello", encoding="utf-8")

    def fake_read_text(self, *args, **kwargs):
        raise OSError("simulated")

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    parser = MarkdownParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(p, "a" * 64)
    assert "exception_type" in exc.value.details


# =========================================================================
# parse 文件编码
# =========================================================================


def test_parse_non_utf8_file_uses_replace(tmp_path: Path):
    """非 UTF-8 字节用 errors='replace' 不崩。"""
    p = tmp_path / "test.md"
    p.write_bytes(b"# \xe9\x9c\n")  # 不完整 UTF-8 序列
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    # 不抛 + 至少有一个 element
    assert len(doc.elements) >= 1


def test_parse_returns_document_instance(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("hello", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert isinstance(doc, Document)


def test_parse_metadata_markdown_flag(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("hello", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.metadata["markdown"] is True


# =========================================================================
# 段落停止条件
# =========================================================================


def test_parse_paragraph_stops_at_heading(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("para line\n# Heading\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    # paragraph + heading
    assert len(doc.elements) == 2
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[1].type == "heading"


def test_parse_paragraph_stops_at_fenced_code(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("para\n```\ncode\n```\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 2
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[1].metadata["kind"] == "code_block"


def test_parse_paragraph_stops_at_thematic_break(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("para\n---\nmore para\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    # paragraph, thematic(ignored), paragraph
    assert len(doc.elements) == 2
    assert all(el.type == "paragraph" for el in doc.elements)


def test_parse_paragraph_stops_at_list_item(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("para\n- item\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 2
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[1].type == "list_item"


def test_parse_paragraph_stops_at_blockquote(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("para\n> quote\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 2
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[1].metadata["kind"] == "blockquote"


def test_parse_paragraph_stops_at_image(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("para\n![alt](img.png)\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 2
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[1].type == "image"


def test_parse_paragraph_stops_at_blank_line(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("para1\n\npara2\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 2
    assert all(el.type == "paragraph" for el in doc.elements)


def test_parse_paragraph_multi_line(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("line1\nline2\nline3\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert len(doc.elements) == 1
    assert "line1" in doc.elements[0].content
    assert "line2" in doc.elements[0].content
    assert "line3" in doc.elements[0].content


# =========================================================================
# 表格深度
# =========================================================================


def test_pipe_table_row_regex_matches():
    assert _PIPE_TABLE_ROW_RE.match("| a | b |")


def test_pipe_table_row_regex_no_match_no_pipe():
    assert not _PIPE_TABLE_ROW_RE.match("a b")


def test_pipe_table_sep_regex_matches():
    assert _PIPE_TABLE_SEP_RE.match("| --- | --- |")


def test_pipe_table_sep_regex_with_colons():
    """列对齐语法的分隔行也匹配（被识别为 table，但 colons 不特殊处理）。"""
    assert _PIPE_TABLE_SEP_RE.match("| :---: | ---: |")


def test_parse_table_metadata_row_col_counts(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text(
        "| h1 | h2 |\n"
        "| --- | --- |\n"
        "| a | b |\n"
        "| c | d |\n",
        encoding="utf-8",
    )
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    table = doc.elements[0]
    assert table.metadata["row_count"] == 3  # header + 2 body
    assert table.metadata["col_count"] == 2


def test_parse_table_content_is_markdown(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text(
        "| h1 | h2 |\n"
        "| --- | --- |\n"
        "| a | b |\n",
        encoding="utf-8",
    )
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    content = doc.elements[0].content
    # 应包含 header + sep + body 三行
    assert "| h1 | h2 |" in content
    assert "---" in content
    assert "| a | b |" in content


def test_parse_table_source_markdown_pipe_table(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text(
        "| h1 | h2 |\n"
        "| --- | --- |\n"
        "| a | b |\n",
        encoding="utf-8",
    )
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements[0].metadata["source"] == "markdown_pipe_table"


# =========================================================================
# 综合行为
# =========================================================================


def test_parse_complex_doc(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text(
        "# Title\n"
        "\n"
        "Paragraph one.\n"
        "\n"
        "## Subsection\n"
        "\n"
        "- item 1\n"
        "- item 2\n"
        "\n"
        "```python\n"
        "code = 1\n"
        "```\n"
        "\n"
        "> a quote\n"
        "\n"
        "| a | b |\n"
        "| --- | --- |\n"
        "| 1 | 2 |\n",
        encoding="utf-8",
    )
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    types = [el.type for el in doc.elements]
    assert "heading" in types
    assert "paragraph" in types
    assert "list_item" in types
    assert "table" in types
    # code block + blockquote 都是 paragraph with kind
    kinds = [el.metadata.get("kind") for el in doc.elements if el.metadata.get("kind")]
    assert "code_block" in kinds
    assert "blockquote" in kinds


def test_parse_empty_file_emits_no_content_warning(tmp_path: Path):
    p = tmp_path / "empty.md"
    p.write_text("", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements == []
    assert any(w.code == "md_no_content" for w in doc.warnings)


def test_parse_whitespace_only_file_emits_warning(tmp_path: Path):
    p = tmp_path / "ws.md"
    p.write_text("   \n\n\t\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.elements == []
    assert any(w.code == "md_no_content" for w in doc.warnings)


def test_parse_element_ids_zero_padded(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("para1\n\npara2\n", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    ids = [el.element_id for el in doc.elements]
    # 应包含 ::e0000 / ::e0001
    assert "::e0000" in ids[0]
    assert "::e0001" in ids[1]


def test_parse_element_confidence_095(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("hello", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    for el in doc.elements:
        assert el.confidence == 0.95


def test_parse_returns_document_with_empty_chunks(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text("hello", encoding="utf-8")
    parser = MarkdownParser()
    doc = parser.parse(p, "a" * 64)
    assert doc.chunks == []
    assert doc.relations == []
    assert doc.errors == []
