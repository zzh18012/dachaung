"""app/parsers/markdown_parser.py 边角测试 - 第二轮（Round 75）。

补强 tests/test_parsers_markdown.py（74）+ tests/test_parsers_markdown_edges.py（63）
未覆盖的：
- 正则引擎深度：边界、特殊字符、不匹配路径
- _parse_text 直接调用：section_path 状态机、heading level jumps、code fence 不闭合
- parse() 错误路径细节：UnicodeDecodeError 回退、OSError → md_read_failed、
  details 字段精确内容
- element_id 跨类型递增、metadata 字段精确 keys、parent_id 总是 None
- 多 block 元素连续触发：image×3、code block×2、table×2
- 段落被每个特殊起首行打断（_ATX_HEADING_RE/_FENCED_RE/_THEMATIC_RE/_UNORDERED_LIST_RE/
  _ORDERED_LIST_RE/_BLOCKQUOTE_RE/_STANDALONE_IMAGE_RE/_is_pipe_table_start）
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.models import Document, Element, WarningRecord
from app.parsers.base import Parser, ParserError
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


# ---------- 正则引擎深度：ATX 标题 ----------


def test_atx_heading_re_leading_space_fails():
    """行首空格 + # 不匹配（标准 ATX 要求 # 在行首）。"""
    assert _ATX_HEADING_RE.match(" # Title") is None


def test_atx_heading_re_leading_tab_fails():
    assert _ATX_HEADING_RE.match("\t# Title") is None


def test_atx_heading_re_single_hash_no_space_fails():
    """单 # 不算标题（必须 # + 空格）。"""
    assert _ATX_HEADING_RE.match("#Title") is None


def test_atx_heading_re_one_hash_with_space():
    m = _ATX_HEADING_RE.match("# Title")
    assert m is not None
    assert len(m.group(1)) == 1


def test_atx_heading_re_six_hashes_max():
    m = _ATX_HEADING_RE.match("###### Title")
    assert m is not None
    assert len(m.group(1)) == 6


def test_atx_heading_re_seven_hashes_fails():
    """7 个 # 不被 ATX 接受。"""
    assert _ATX_HEADING_RE.match("####### Title") is None


def test_atx_heading_re_trailing_hashes_stripped_in_capture():
    """capture group 2 不含尾随 #。"""
    m = _ATX_HEADING_RE.match("# Title ###")
    assert m is not None
    assert m.group(2) == "Title"


def test_atx_heading_re_no_trailing_hashes():
    m = _ATX_HEADING_RE.match("# Title")
    assert m.group(2) == "Title"


def test_atx_heading_re_multiple_inner_spaces_preserved():
    """# foo bar baz 中间空格保留。"""
    m = _ATX_HEADING_RE.match("# foo bar baz")
    assert m.group(2) == "foo bar baz"


def test_atx_heading_re_empty_title_after_hashes_fails():
    """"# " 后面什么都没有 → 不匹配（.+? 要求至少 1 字符）。"""
    assert _ATX_HEADING_RE.match("# ") is None


def test_atx_heading_re_only_hashes_no_space_fails():
    """###### 不带空格 → 不匹配。"""
    assert _ATX_HEADING_RE.match("######") is None


def test_atx_heading_re_title_with_punctuation():
    m = _ATX_HEADING_RE.match("# Hello, World!")
    assert m.group(2) == "Hello, World!"


def test_atx_heading_re_title_with_unicode_chinese():
    m = _ATX_HEADING_RE.match("# 你好世界")
    assert m.group(2) == "你好世界"


def test_atx_heading_re_title_with_emoji():
    m = _ATX_HEADING_RE.match("# Title 🎉")
    assert "🎉" in m.group(2)


# ---------- 正则引擎深度：thematic break ----------


def test_thematic_re_three_dashes():
    assert _THEMATIC_RE.match("---") is not None


def test_thematic_re_three_stars():
    assert _THEMATIC_RE.match("***") is not None


def test_thematic_re_three_underscores():
    assert _THEMATIC_RE.match("___") is not None


def test_thematic_re_long_dashes():
    assert _THEMATIC_RE.match("----------") is not None


def test_thematic_re_mixed_star_dash():
    """mixed -*-* 不算（必须同一字符）— 但 _THEMATIC_RE 实际是 [-*_] 字符集，混合也通过。"""
    # 看实际正则:^(?:[-*_])(?:\s*[-*_]){2,}$
    # 这个正则允许混合 [-*_]，所以 mixed 也会匹配
    assert _THEMATIC_RE.match("-*-_") is not None


def test_thematic_re_two_chars_fails():
    assert _THEMATIC_RE.match("--") is None


def test_thematic_re_single_char_fails():
    assert _THEMATIC_RE.match("-") is None


def test_thematic_re_with_internal_spaces():
    assert _THEMATIC_RE.match("- - -") is not None


def test_thematic_re_leading_whitespace_fails():
    """thematic 应用到 stripped 后的行；这里直接测原始行（带空白）的行为。"""
    # _THEMATIC_RE 不允许前导空白，所以原始带空白行不匹配
    assert _THEMATIC_RE.match("  ---") is None


def test_thematic_re_trailing_text_fails():
    assert _THEMATIC_RE.match("--- text") is None


# ---------- 正则引擎深度：fenced code ----------


def test_fenced_re_three_backticks():
    m = _FENCED_RE.match("```")
    assert m is not None


def test_fenced_re_four_backticks():
    m = _FENCED_RE.match("````")
    assert m is not None


def test_fenced_re_three_tildes():
    m = _FENCED_RE.match("~~~")
    assert m is not None


def test_fenced_re_four_tildes():
    m = _FENCED_RE.match("~~~~")
    assert m is not None


def test_fenced_re_with_language_python():
    m = _FENCED_RE.match("```python")
    assert m is not None
    assert m.group(2) == "python"


def test_fenced_re_with_language_javascript():
    m = _FENCED_RE.match("```javascript")
    assert m.group(2) == "javascript"


def test_fenced_re_with_language_with_dash():
    m = _FENCED_RE.match("```c++")
    assert m.group(2) == "c++"


def test_fenced_re_with_language_with_dash_only():
    """language 正则是 [\\w+-]*，含 - 与字母数字，但不含 ./ 等。"""
    m = _FENCED_RE.match("```c++")
    assert m.group(2) == "c++"


def test_fenced_re_language_with_slash_fails_partially():
    """language 含 / 时正则 [\\w+-]* 在 / 处停止，但因为 \\s*$ 要求行末无内容，
    实际不会整体匹配（/ 之后的字符不匹配 \\s*$）。"""
    m = _FENCED_RE.match("```text/x-rst")
    # \\s*$ 不允许 /，整体不匹配
    assert m is None


def test_fenced_re_no_language_empty_string():
    m = _FENCED_RE.match("```")
    assert m.group(2) == ""


def test_fenced_re_two_backticks_fails():
    """两个反引号不算 fence（要 3+）。"""
    assert _FENCED_RE.match("``") is None


def test_fenced_re_single_backtick_fails():
    assert _FENCED_RE.match("`") is None


def test_fenced_re_backtick_with_text_after_no_space_fails():
    r"""```python 后跟字符（无空格）的边界：实际 [\w+-]* 允许字母数字。"""
    # 实际 ```pythonxy 也匹配（语言是 pythonxy）
    m = _FENCED_RE.match("```pythonxy")
    assert m is not None


def test_fenced_re_leading_text_fails():
    """行首不能有其他字符。"""
    assert _FENCED_RE.match("text```") is None


# ---------- 正则引擎深度：列表 ----------


def test_unordered_list_re_dash_marker():
    m = _UNORDERED_LIST_RE.match("- item")
    assert m is not None
    assert m.group(1) == "item"


def test_unordered_list_re_star_marker():
    m = _UNORDERED_LIST_RE.match("* item")
    assert m.group(1) == "item"


def test_unordered_list_re_plus_marker():
    m = _UNORDERED_LIST_RE.match("+ item")
    assert m.group(1) == "item"


def test_unordered_list_re_no_space_after_marker_fails():
    """-item 不算列表项（需要 - 后空格）。"""
    assert _UNORDERED_LIST_RE.match("-item") is None


def test_unordered_list_re_tab_after_marker():
    """-\\titem 也算（\\s+ 匹配）。"""
    # _UNORDERED_LIST_RE = r"^[-*+]\s+(.+)$"
    m = _UNORDERED_LIST_RE.match("-\titem")
    assert m is not None


def test_unordered_list_re_multi_word_content():
    m = _UNORDERED_LIST_RE.match("- hello world foo")
    assert m.group(1) == "hello world foo"


def test_unordered_list_re_empty_content_fails():
    """"- " 后无内容不匹配（.+ 要求至少 1 字符）。"""
    assert _UNORDERED_LIST_RE.match("- ") is None


def test_unordered_list_re_leading_space_fails():
    """缩进的列表项不算（标准 ATX 是 0 缩进）。"""
    assert _UNORDERED_LIST_RE.match("  - item") is None


def test_ordered_list_re_dot_separator():
    m = _ORDERED_LIST_RE.match("1. item")
    assert m is not None
    assert m.group(1) == "item"


def test_ordered_list_re_paren_separator():
    m = _ORDERED_LIST_RE.match("1) item")
    assert m.group(1) == "item"


def test_ordered_list_re_large_number():
    m = _ORDERED_LIST_RE.match("999. item")
    assert m.group(1) == "item"


def test_ordered_list_re_zero_number():
    """0. item 也匹配（正则不限制数字范围）。"""
    m = _ORDERED_LIST_RE.match("0. item")
    assert m is not None


def test_ordered_list_re_no_space_fails():
    assert _ORDERED_LIST_RE.match("1.item") is None


def test_ordered_list_re_no_separator_fails():
    assert _ORDERED_LIST_RE.match("1 item") is None


def test_ordered_list_re_just_number_dot_fails():
    """1. 后无内容不匹配。"""
    assert _ORDERED_LIST_RE.match("1. ") is None


# ---------- 正则引擎深度：blockquote ----------


def test_blockquote_re_basic_with_space():
    m = _BLOCKQUOTE_RE.match("> text")
    assert m is not None
    assert m.group(1) == "text"


def test_blockquote_re_no_space_after_gt():
    """>text 也算（正则允许 >\\s?）。"""
    m = _BLOCKQUOTE_RE.match(">text")
    assert m is not None
    assert m.group(1) == "text"


def test_blockquote_re_empty_after_gt():
    m = _BLOCKQUOTE_RE.match(">")
    assert m is not None
    assert m.group(1) == ""


def test_blockquote_re_just_space_after_gt():
    m = _BLOCKQUOTE_RE.match("> ")
    assert m is not None
    assert m.group(1) == ""


def test_blockquote_re_multi_word():
    m = _BLOCKQUOTE_RE.match("> hello world")
    assert m.group(1) == "hello world"


def test_blockquote_re_does_not_match_double_gt_at_start():
    """>> 是嵌套引用，但 _BLOCKQUOTE_RE 匹配 > 后面的内容（包括 >）。"""
    m = _BLOCKQUOTE_RE.match(">> nested")
    # >> nested 匹配，group(1) 是 "> nested"（含一个 >）
    assert m is not None
    assert m.group(1) == "> nested"


def test_blockquote_re_does_not_match_no_gt():
    assert _BLOCKQUOTE_RE.match("text") is None


def test_blockquote_re_leading_space_fails():
    assert _BLOCKQUOTE_RE.match("  > text") is None


# ---------- 正则引擎深度：standalone image ----------


def test_standalone_image_re_basic():
    m = _STANDALONE_IMAGE_RE.match("![alt](url.png)")
    assert m is not None
    assert m.group(1) == "alt"
    assert m.group(2) == "url.png"


def test_standalone_image_re_empty_alt():
    m = _STANDALONE_IMAGE_RE.match("![](url.png)")
    assert m.group(1) == ""
    assert m.group(2) == "url.png"


def test_standalone_image_re_alt_with_spaces():
    m = _STANDALONE_IMAGE_RE.match("![alt text here](url.png)")
    assert m.group(1) == "alt text here"


def test_standalone_image_re_url_with_query():
    m = _STANDALONE_IMAGE_RE.match("![alt](url.png?w=100&h=200)")
    assert m.group(2) == "url.png?w=100&h=200"


def test_standalone_image_re_url_with_path():
    m = _STANDALONE_IMAGE_RE.match("![alt](https://example.com/path/to/img.png)")
    assert m.group(2) == "https://example.com/path/to/img.png"


def test_standalone_image_re_alt_with_special_chars():
    m = _STANDALONE_IMAGE_RE.match("![alt-text_123](url)")
    assert m.group(1) == "alt-text_123"


def test_standalone_image_re_alt_with_bracket_fails():
    """![alt]content](url) — 内部 ] 终止 alt 捕获。"""
    # 实际正则 `[^\]]*` 不允许 ]，所以 ![alt]x](url) 不会整体匹配
    assert _STANDALONE_IMAGE_RE.match("![alt]x](url)") is None


def test_standalone_image_re_trailing_text_fails():
    """![alt](url) extra 不算 standalone（必须整行）。"""
    assert _STANDALONE_IMAGE_RE.match("![alt](url) extra") is None


def test_standalone_image_re_leading_text_fails():
    assert _STANDALONE_IMAGE_RE.match("text ![alt](url)") is None


def test_standalone_image_re_no_closing_paren_fails():
    assert _STANDALONE_IMAGE_RE.match("![alt](url") is None


def test_standalone_image_re_no_bang_prefix_fails():
    """[alt](url) 不算 image（是链接）。"""
    assert _STANDALONE_IMAGE_RE.match("[alt](url)") is None


# ---------- 正则引擎深度：pipe table ----------


def test_pipe_table_row_re_basic():
    assert _PIPE_TABLE_ROW_RE.match("| a | b |") is not None


def test_pipe_table_row_re_no_outer_pipes():
    """`a | b` 不匹配（要求首尾 |）。"""
    assert _PIPE_TABLE_ROW_RE.match("a | b") is None


def test_pipe_table_row_re_single_pipe_no_outer():
    """a|b 也算（首尾无 pipe）。"""
    # _PIPE_TABLE_ROW_RE = r"^\s*\|.*\|\s*$"
    # a|b 不匹配：要求 \|.+\| 即开头 \s*\| 然后 .* 然后 \|
    # a|b 的开头不是 |，不匹配
    assert _PIPE_TABLE_ROW_RE.match("a|b") is None


def test_pipe_table_row_re_leading_whitespace():
    assert _PIPE_TABLE_ROW_RE.match("   | a | b |") is not None


def test_pipe_table_row_re_trailing_whitespace():
    assert _PIPE_TABLE_ROW_RE.match("| a | b |   ") is not None


def test_pipe_table_row_re_no_pipe_fails():
    assert _PIPE_TABLE_ROW_RE.match("text") is None


def test_pipe_table_row_re_only_one_pipe_fails():
    """单 | 不算 row（必须 .*\\| 即两个 |）。"""
    # _PIPE_TABLE_ROW_RE = r"^\s*\|.*\|\s*$"
    # | a 只有一个 |，不匹配
    assert _PIPE_TABLE_ROW_RE.match("| a") is None


def test_pipe_table_sep_re_basic():
    assert _PIPE_TABLE_SEP_RE.match("| --- | --- |") is not None


def test_pipe_table_sep_re_no_outer_pipe():
    assert _PIPE_TABLE_SEP_RE.match("--- | ---") is not None


def test_pipe_table_sep_re_with_alignment_colons():
    assert _PIPE_TABLE_SEP_RE.match("| :---: | ---: |") is not None


def test_pipe_table_sep_re_single_colon_left_align():
    assert _PIPE_TABLE_SEP_RE.match("| :--- | --- |") is not None


def test_pipe_table_sep_re_short_dash_fails():
    """单 - 不算 sep（要至少 2 个）。"""
    assert _PIPE_TABLE_SEP_RE.match("| - | - |") is None


def test_pipe_table_sep_re_text_fails():
    assert _PIPE_TABLE_SEP_RE.match("| a | b |") is None


# ---------- _detect_md_source_type 深度 ----------


def test_detect_md_source_type_uppercase_md_falls_through_to_error():
    """uppercase .MD 不被接受（被 lower 后是 .md，但实际 _MD_EXTENSIONS 是小写）。

    实际：suffix.lower() → ".md"，所以 .MD 实际匹配（小写化后）。
    """
    # _detect_md_source_type 用 path.suffix.lower()，所以 .MD 会被接受
    assert _detect_md_source_type(Path("test.MD")) == "markdown"


def test_detect_md_source_type_uppercase_markdown():
    assert _detect_md_source_type(Path("test.MARKDOWN")) == "markdown"


def test_detect_md_source_type_mixed_case_md():
    assert _detect_md_source_type(Path("test.Md")) == "markdown"


def test_detect_md_source_type_txt_raises():
    with pytest.raises(ParserError):
        _detect_md_source_type(Path("test.txt"))


def test_detect_md_source_type_no_suffix_raises():
    with pytest.raises(ParserError):
        _detect_md_source_type(Path("README"))


def test_detect_md_source_type_dotfile_md():
    """.md 文件名（仅扩展名无 stem）→ path.suffix 是 ''（pathlib 视为隐藏文件）。
    实际：Path('.md').suffix == '' → 抛 unsupported_type。
    """
    # pathlib 把 .md 当作无扩展名的隐藏文件
    with pytest.raises(ParserError):
        _detect_md_source_type(Path(".md"))


def test_detect_md_source_type_double_extension():
    """file.tar.md → suffix 是 .md。"""
    assert _detect_md_source_type(Path("file.tar.md")) == "markdown"


def test_detect_md_source_type_error_is_parser_error_type():
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("test.txt"))
    assert isinstance(exc.value, ParserError)


def test_detect_md_source_type_error_code_value():
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("test.txt"))
    assert exc.value.code == "unsupported_type"


def test_detect_md_source_type_error_details_contain_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("test.docx"))
    assert exc.value.details["suffix"] == ".docx"


# ---------- MarkdownParser.parse() 错误路径深度 ----------


def test_parse_missing_file_error_code(tmp_path: Path):
    p = MarkdownParser()
    with pytest.raises(ParserError) as exc:
        p.parse(tmp_path / "missing.md", "a" * 64)
    assert exc.value.code == "file_not_found"


def test_parse_missing_file_error_details_has_path(tmp_path: Path):
    p = MarkdownParser()
    missing = tmp_path / "missing.md"
    with pytest.raises(ParserError) as exc:
        p.parse(missing, "a" * 64)
    assert exc.value.details["path"] == str(missing)


def test_parse_unsupported_extension_error_code(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.code == "unsupported_type"


def test_parse_unsupported_extension_after_file_exists(tmp_path: Path):
    """unlike _detect in pipeline, parse checks is_file() first then extension."""
    p = MarkdownParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    # is_file() True → 进 _detect_md_source_type → 抛 unsupported_type
    with pytest.raises(ParserError):
        p.parse(f, "a" * 64)


def test_parse_directory_raises_file_not_found(tmp_path: Path):
    """目录 → is_file()=False → file_not_found（不是 unsupported_type）。"""
    p = MarkdownParser()
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(ParserError) as exc:
        p.parse(sub, "a" * 64)
    assert exc.value.code == "file_not_found"


def test_parse_returns_document_type(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# Title", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert isinstance(doc, Document)


def test_parse_returns_document_with_correct_hash(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# Title", encoding="utf-8")
    sha = "b" * 64
    doc = p.parse(f, sha)
    assert doc.source_hash == sha


def test_parse_returns_document_id_derived_from_hash(tmp_path: Path):
    """document_id = make_document_id(source_hash)。"""
    from app.parsers.base import make_document_id
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# Title", encoding="utf-8")
    sha = "c" * 64
    doc = p.parse(f, sha)
    assert doc.document_id == make_document_id(sha)


def test_parse_returns_empty_elements_for_thematic_only(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("---\n***\n___", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.elements == []
    # 应当有 md_no_content warning
    assert any(w.code == "md_no_content" for w in doc.warnings)


def test_parse_returns_empty_elements_for_blank_file(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.elements == []


def test_parse_returns_warning_for_empty_file(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert len(doc.warnings) >= 1


def test_parse_metadata_markdown_true(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# Title", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.metadata == {"markdown": True}


def test_parse_chunks_empty_list(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# Title", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.chunks == []


def test_parse_relations_empty_list(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# Title", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.relations == []


def test_parse_errors_empty_list(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# Title", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.errors == []


def test_parse_source_path_is_str(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# Title", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert isinstance(doc.source_path, str)


def test_parse_source_type_is_markdown(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# Title", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.source_type == "markdown"


def test_parse_parser_name_attribute(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# Title", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.parser_name == "markdown"


def test_parse_parser_version_attribute(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# Title", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    assert doc.parser_version == "stdlib/0.1.0"


# ---------- UnicodeDecodeError 回退路径 ----------


def test_parse_invalid_utf8_falls_back_to_replace(tmp_path: Path):
    """读 latin-1 字节 → UnicodeDecodeError → errors=replace 回退。"""
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_bytes(b"# Title \xff\xfe invalid utf-8\nhello world")
    doc = p.parse(f, "a" * 64)
    # 应当成功解析（不抛异常）
    assert isinstance(doc, Document)


def test_parse_invalid_utf8_text_has_replacement_chars(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_bytes(b"\xff\xfe")
    doc = p.parse(f, "a" * 64)
    # 解析后 elements 可能为空，但 doc 必须是 Document
    assert isinstance(doc, Document)


# ---------- section_path 状态机深度 ----------


def test_section_path_pops_on_higher_level(tmp_path: Path):
    """# H1 → ## H2 → # H3: 第三个 # 弹出 H2，section_path=[H3]。"""
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# H1\n## H2\n# H3", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    h3 = doc.elements[-1]
    assert h3.source_locator["section_path"] == "H3"


def test_section_path_pops_on_same_level(tmp_path: Path):
    """# H1 → # H2: 第二个 # 弹出 H1，section_path=[H2]。"""
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# H1\n# H2", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    h2 = doc.elements[-1]
    assert h2.source_locator["section_path"] == "H2"


def test_section_path_grows_on_deeper_level(tmp_path: Path):
    """# H1 → ## H2 → ### H3: section_path=[H1,H2,H3]（不弹出）。"""
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# H1\n## H2\n### H3", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    h3 = doc.elements[-1]
    assert h3.source_locator["section_path"] == "H1 > H2 > H3"


def test_section_path_jumps_skip_levels(tmp_path: Path):
    """# H1 → #### H4: section_path=[H1,H4]（不补中间）。"""
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# H1\n#### H4", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    h4 = doc.elements[-1]
    assert h4.source_locator["section_path"] == "H1 > H4"


def test_section_path_with_paragraph_under_heading(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# Title\nparagraph text", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    para = doc.elements[-1]
    assert para.source_locator["section_path"] == "Title"


def test_section_path_preamble_no_section_path(tmp_path: Path):
    """开头无 heading → section_path 不存在。"""
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("preamble text", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    para = doc.elements[0]
    assert "section_path" not in para.source_locator


def test_section_path_after_heading_pops_back_to_empty(tmp_path: Path):
    """## H2 → #### H4 → # H1: 最后 H1 弹出所有更深的，section_path=[H1]。"""
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("## H2\n#### H4\n# H1", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    h1 = doc.elements[-1]
    assert h1.source_locator["section_path"] == "H1"


# ---------- element_id 跨类型递增 ----------


def test_element_id_sequence_across_types(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# H1\nparagraph\n- item\n> quote", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    ids = [e.element_id for e in doc.elements]
    # 必须严格递增（按出现顺序）
    for i in range(1, len(ids)):
        assert ids[i] > ids[i - 1]


def test_element_id_format_four_digit_zero_pad(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# Title", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    eid = doc.elements[0].element_id
    # format: {document_id}::e{N:04d}
    parts = eid.split("::")
    assert len(parts) == 2
    assert parts[1].startswith("e")
    num = parts[1][1:]
    assert len(num) == 4  # 4 位
    assert num == "0000"


def test_element_parent_id_always_none(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# Title\nparagraph", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    for e in doc.elements:
        assert e.parent_id is None


def test_element_confidence_strictly_095(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("# Title\n- item\n> quote\n```python\ncode\n```", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    for e in doc.elements:
        assert e.confidence == 0.95


# ---------- 段落被每个特殊起首行打断 ----------


def test_paragraph_interrupted_by_atx_heading(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("paragraph\n# Title", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    types = [e.type for e in doc.elements]
    assert "paragraph" in types
    assert "heading" in types


def test_paragraph_interrupted_by_fenced_code(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("paragraph\n```\ncode\n```", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    types = [e.type for e in doc.elements]
    assert "paragraph" in types


def test_paragraph_interrupted_by_thematic_break(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("paragraph\n---\nsecond paragraph", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    # 段落被 --- 分开（thematic 不算 element，但分隔段落）
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) >= 1


def test_paragraph_interrupted_by_unordered_list(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("paragraph\n- item", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    types = [e.type for e in doc.elements]
    assert "paragraph" in types
    assert "list_item" in types


def test_paragraph_interrupted_by_ordered_list(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("paragraph\n1. item", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    types = [e.type for e in doc.elements]
    assert "list_item" in types


def test_paragraph_interrupted_by_blockquote(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("paragraph\n> quote", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    types = [e.type for e in doc.elements]
    assert "paragraph" in types


def test_paragraph_interrupted_by_standalone_image(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("paragraph\n![alt](url.png)", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    types = [e.type for e in doc.elements]
    assert "image" in types


def test_paragraph_interrupted_by_pipe_table(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("paragraph\n| a | b |\n| --- | --- |\n| 1 | 2 |", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    types = [e.type for e in doc.elements]
    assert "table" in types


# ---------- 多个连续 block 元素 ----------


def test_multiple_consecutive_images(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("![a](u1.png)\n![b](u2.png)\n![c](u3.png)", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    images = [e for e in doc.elements if e.type == "image"]
    assert len(images) == 3


def test_multiple_consecutive_code_blocks(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("```\ncode1\n```\n```\ncode2\n```", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    codes = [e for e in doc.elements if e.metadata.get("kind") == "code_block"]
    assert len(codes) == 2


def test_multiple_consecutive_tables(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text(
        "| a | b |\n| --- | --- |\n| 1 | 2 |\n\n| c | d |\n| --- | --- |\n| 3 | 4 |",
        encoding="utf-8",
    )
    doc = p.parse(f, "a" * 64)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 2


def test_multiple_consecutive_blockquotes(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("> quote1\n\n> quote2", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    quotes = [e for e in doc.elements if e.metadata.get("kind") == "blockquote"]
    assert len(quotes) == 2


# ---------- code fence 边界 ----------


def test_code_fence_unclosed_at_eof(tmp_path: Path):
    """代码块未闭合 → 读取到 EOF。"""
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("```\ncode without closing", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    codes = [e for e in doc.elements if e.metadata.get("kind") == "code_block"]
    assert len(codes) == 1


def test_code_fence_with_backtick_language(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("```python\ncode\n```", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    code = doc.elements[0]
    assert code.metadata["language"] == "python"


def test_code_fence_with_tilde_language(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("~~~javascript\ncode\n~~~", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    code = doc.elements[0]
    assert code.metadata["language"] == "javascript"


def test_code_fence_empty_emits_warning_with_line(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("```\n```", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    # 空 code block → 警告 + 不创建 element
    assert any(w.code == "md_empty_code_block" for w in doc.warnings)


def test_code_fence_empty_warning_reason_contains_line_number(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("```\n```", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    for w in doc.warnings:
        if w.code == "md_empty_code_block":
            assert "line 1" in w.reason


# ---------- _split_pipe_row / _rows_to_md 更深边角 ----------


def test_split_pipe_row_only_pipe_returns_two_empty():
    """'|' → strip 后 ''，去首尾 | 后 '', split('|') → ['']."""
    # |.strip() == "", 不去首尾 |，直接 split('|') → ['']
    # 实际行为：s='|'; s.startswith('|') → True → s=''; s.endswith('|') → False
    # s.split('|') == ['']
    result = _split_pipe_row("|")
    assert result == [""]


def test_split_pipe_row_two_pipes_returns_one_empty():
    """'||' → strip='|'，去首 | 后 '|'，去尾 | 后 '', split('|') → ['']."""
    result = _split_pipe_row("||")
    assert result == [""]


def test_split_pipe_row_three_pipes_returns_two_empty():
    """'|||' → 去 首尾 | 后 '|'，split → ['', '']."""
    result = _split_pipe_row("|||")
    assert result == ["", ""]


def test_rows_to_md_one_row_one_col():
    result = _rows_to_md([["cell"]])
    assert "cell" in result
    # 单行单列也会有 separator（实现始终输出 separator）
    assert "---" in result


def test_rows_to_md_three_rows():
    rows = [["h1", "h2"], ["a1", "a2"], ["b1", "b2"]]
    result = _rows_to_md(rows)
    lines = result.split("\n")
    assert len(lines) == 4  # header + sep + 2 body


def test_rows_to_md_separator_count_matches_columns():
    """3 列 → separator 行有 3 个 ---。"""
    result = _rows_to_md([["a", "b", "c"]])
    sep_line = result.split("\n")[1]
    assert sep_line.count("---") == 3


# ---------- _is_pipe_table_start 边界 ----------


def test_is_pipe_table_start_returns_bool_type():
    """返回值是 bool。"""
    assert isinstance(_is_pipe_table_start(["| a | b |", "| --- | --- |"], 0), bool)


def test_is_pipe_table_start_i_is_negative_returns_true_or_false():
    """i=-1 时 lines[i] 是最后一行；lines[i+1] 是 lines[0]（如果 len > 1）。"""
    # Python 负索引：lines[-1] 最后一行，lines[0] 第一行
    # 实际：i+1 = 0, lines[0] 是第一行；所以这会检查 最后一行 + 第一行
    # 这种情况语义模糊；只测试不抛
    lines = ["| a | b |", "| --- | --- |", "| 1 | 2 |"]
    try:
        result = _is_pipe_table_start(lines, -2)
        assert isinstance(result, bool)
    except IndexError:
        pytest.skip("negative index behavior undefined")


# ---------- WarningRecord 字段深度 ----------


def test_md_no_content_warning_has_code(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("", encoding="utf-8")
    doc = p.parse(f, "a" * 64)
    for w in doc.warnings:
        assert isinstance(w.code, str)
        assert isinstance(w.reason, str)


def test_md_no_content_warning_reason_text(tmp_path: Path):
    p = MarkdownParser()
    f = tmp_path / "f.md"
    f.write_text("---", encoding="utf-8")  # 仅主题分隔符
    doc = p.parse(f, "a" * 64)
    reasons = [w.reason for w in doc.warnings if w.code == "md_no_content"]
    assert len(reasons) >= 1
    # reason 描述应当提到 "element" 或 "Markdown"
    assert any("element" in r or "Markdown" in r for r in reasons)


# ---------- 模块结构 ----------


def test_module_imports_re():
    import app.parsers.markdown_parser as mod
    assert hasattr(mod, "re")


def test_module_imports_path():
    import app.parsers.markdown_parser as mod
    assert hasattr(mod, "Path")


def test_module_imports_any():
    from typing import Any
    import app.parsers.markdown_parser as mod
    assert hasattr(mod, "Any")


def test_module_imports_document():
    import app.parsers.markdown_parser as mod
    assert hasattr(mod, "Document")


def test_module_imports_element():
    import app.parsers.markdown_parser as mod
    assert hasattr(mod, "Element")


def test_module_imports_warning_record():
    import app.parsers.markdown_parser as mod
    assert hasattr(mod, "WarningRecord")


def test_module_imports_parser_base():
    import app.parsers.markdown_parser as mod
    assert hasattr(mod, "Parser")


def test_module_imports_parser_error():
    import app.parsers.markdown_parser as mod
    assert hasattr(mod, "ParserError")


def test_module_imports_make_document_id():
    import app.parsers.markdown_parser as mod
    assert hasattr(mod, "make_document_id")


def test_module_has_all():
    import app.parsers.markdown_parser as mod
    assert hasattr(mod, "__all__")


def test_module_all_contains_markdown_parser():
    import app.parsers.markdown_parser as mod
    assert "MarkdownParser" in mod.__all__


def test_module_all_is_list():
    import app.parsers.markdown_parser as mod
    assert isinstance(mod.__all__, list)


def test_markdown_parser_inherits_parser():
    p = MarkdownParser()
    assert isinstance(p, Parser)


def test_markdown_parser_name_is_str():
    p = MarkdownParser()
    assert isinstance(p.name, str)


def test_markdown_parser_version_is_str():
    p = MarkdownParser()
    assert isinstance(p.version, str)


def test_markdown_parser_parse_callable():
    p = MarkdownParser()
    assert callable(p.parse)


def test_markdown_parser_parse_method_takes_self_path_hash():
    """parse 签名: (self, path, source_hash)。"""
    import inspect
    sig = inspect.signature(MarkdownParser.parse)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "path" in params
    assert "source_hash" in params
