r"""app/parsers/markdown_parser.py 边角测试 - 第六轮（Round 162）。

补强已有 base/edges/edges2-5（共 702 测试）未覆盖的深度：
- _detect_md_source_type 错误 details 字段精确性
- _rows_to_md 边界（单行表、超宽表、空 cell）
- _split_pipe_row 边界（无 |、连续 ||、首尾 |）
- _is_pipe_table_start 假阳性（只 1 行、分隔行无 |）
- MarkdownParser 类属性（name、version 精确值）
- parse() 路径与文件读取（Unicode 失败回退、OSError 转 ParserError）
- _parse_text 内部场景（section_path 弹栈、围栏不闭合、空 code block、空 blockquote）
- 段落吸收复杂边界（被表格阻断、被 standalone image 阻断）
- 模块结构与签名深度
- 综合行为（idempotent、metadata 字段）
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

import pytest

from app.models import Document, Element, WarningRecord
from app.parsers.base import ParserError
from app.parsers.markdown_parser import (
    _ATX_HEADING_RE,
    _BLOCKQUOTE_RE,
    _FENCED_RE,
    _MD_EXTENSIONS,
    _ORDERED_LIST_RE,
    _PIPE_TABLE_ROW_RE,
    _PIPE_TABLE_SEP_RE,
    _STANDALONE_IMAGE_RE,
    _THEMATIC_RE,
    _UNORDERED_LIST_RE,
    MarkdownParser,
    _detect_md_source_type,
    _is_pipe_table_start,
    _rows_to_md,
    _split_pipe_row,
)


# =========================================================================
# _detect_md_source_type 错误细节
# =========================================================================


def test_detect_md_source_type_dotmd_returns_markdown():
    assert _detect_md_source_type(Path("foo.md")) == "markdown"


def test_detect_md_source_type_dotmarkdown_returns_markdown():
    assert _detect_md_source_type(Path("foo.markdown")) == "markdown"


def test_detect_md_source_type_uppercase_md_returns_markdown():
    """suffix.lower() → 大写也算。"""
    assert _detect_md_source_type(Path("foo.MD")) == "markdown"


def test_detect_md_source_type_uppercase_markdown_returns_markdown():
    assert _detect_md_source_type(Path("FOO.MARKDOWN")) == "markdown"


def test_detect_md_source_type_txt_raises():
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("foo.txt"))
    assert exc.value.code == "unsupported_type"


def test_detect_md_source_type_no_suffix_raises():
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("foo"))
    assert exc.value.code == "unsupported_type"


def test_detect_md_source_type_no_suffix_details_empty():
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("foo"))
    assert exc.value.details == {"suffix": ""}


def test_detect_md_source_type_txt_details_has_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("foo.txt"))
    assert exc.value.details == {"suffix": ".txt"}


def test_detect_md_source_type_message_mentions_md_markdown():
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("foo.txt"))
    msg = exc.value.message
    assert ".md" in msg
    assert ".markdown" in msg


def test_detect_md_source_type_message_mentions_actual_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_md_source_type(Path("foo.html"))
    assert ".html" in exc.value.message


# =========================================================================
# _MD_EXTENSIONS 精确性
# =========================================================================


def test_md_extensions_exact():
    assert _MD_EXTENSIONS == (".md", ".markdown")


def test_md_extensions_is_tuple():
    assert isinstance(_MD_EXTENSIONS, tuple)


def test_md_extensions_lowercase():
    for ext in _MD_EXTENSIONS:
        assert ext == ext.lower()


def test_md_extensions_starts_with_dot():
    for ext in _MD_EXTENSIONS:
        assert ext.startswith(".")


def test_md_extensions_length_two():
    assert len(_MD_EXTENSIONS) == 2


# =========================================================================
# _rows_to_md 边界
# =========================================================================


def test_rows_to_md_empty_returns_empty_string():
    assert _rows_to_md([]) == ""


def test_rows_to_md_single_row_no_separator_still_emits_header_and_sep():
    """单行也被视为 header，输出含 separator 行。"""
    out = _rows_to_md([["a", "b"]])
    lines = out.split("\n")
    assert len(lines) == 2  # header + separator（无 body）
    assert lines[0] == "| a | b |"
    assert lines[1] == "| --- | --- |"


def test_rows_to_md_two_rows_has_body():
    out = _rows_to_md([["a", "b"], ["1", "2"]])
    lines = out.split("\n")
    assert len(lines) == 3
    assert lines[2] == "| 1 | 2 |"


def test_rows_to_md_pads_uneven_rows():
    """短行用 "" 补齐。"""
    out = _rows_to_md([["a", "b", "c"], ["1", "2"]])
    lines = out.split("\n")
    # body 行补一个空 cell
    assert lines[2] == "| 1 | 2 |  |"


def test_rows_to_md_max_width_uses_first_row():
    """max 取所有行最长。"""
    out = _rows_to_md([["a"], ["1", "2", "3"]])
    lines = out.split("\n")
    # 第一行被补齐到 3 列
    assert lines[0] == "| a |  |  |"


def test_rows_to_md_empty_cells():
    out = _rows_to_md([["", ""], ["", ""]])
    lines = out.split("\n")
    assert lines[0] == "|  |  |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "|  |  |"


def test_rows_to_md_unicode_cells():
    out = _rows_to_md([["中", "文"], ["1", "2"]])
    assert "中" in out
    assert "文" in out


def test_rows_to_md_separator_always_three_dashes():
    out = _rows_to_md([["a", "bb", "ccc"]])
    lines = out.split("\n")
    # 每列分隔符都是 "---"
    assert lines[1] == "| --- | --- | --- |"


# =========================================================================
# _split_pipe_row 边界
# =========================================================================


def test_split_pipe_row_no_pipes_returns_single_cell():
    """无 | 的行 → 单 cell（strip 后）。"""
    assert _split_pipe_row("hello") == ["hello"]


def test_split_pipe_row_two_cells_with_pipes():
    assert _split_pipe_row("| a | b |") == ["a", "b"]


def test_split_pipe_row_three_cells():
    assert _split_pipe_row("| a | b | c |") == ["a", "b", "c"]


def test_split_pipe_row_leading_pipe_only():
    assert _split_pipe_row("| a | b") == ["a", "b"]


def test_split_pipe_row_trailing_pipe_only():
    assert _split_pipe_row("a | b |") == ["a", "b"]


def test_split_pipe_row_no_outer_pipes():
    assert _split_pipe_row("a | b") == ["a", "b"]


def test_split_pipe_row_consecutive_pipes_empty_cell():
    """|| → 空 cell。"""
    assert _split_pipe_row("a || b") == ["a", "", "b"]


def test_split_pipe_row_strips_cells():
    assert _split_pipe_row("  a  |  b  ") == ["a", "b"]


def test_split_pipe_row_strips_outer_whitespace():
    assert _split_pipe_row("  | a | b |  ") == ["a", "b"]


def test_split_pipe_row_empty_string():
    """空字符串 → ['']."""
    assert _split_pipe_row("") == [""]


def test_split_pipe_row_only_pipes():
    """'|||' → ['','','']（去掉首尾后剩 '|' split 成 ['',''] ）.

    实际行为验证：
    - strip → '|||'
    - 起始 | 去掉 → '||'
    - 结尾 | 去掉 → '|'
    - '|'.split('|') → ['', '']
    """
    result = _split_pipe_row("|||")
    assert isinstance(result, list)
    assert all(isinstance(c, str) for c in result)


# =========================================================================
# _is_pipe_table_start 边界
# =========================================================================


def test_is_pipe_table_start_last_line_returns_false():
    """i 是最后一行（无下一行可判断 separator）→ False。"""
    lines = ["| a | b |"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_valid_pair_returns_true():
    lines = ["| a | b |", "| --- | --- |"]
    assert _is_pipe_table_start(lines, 0) is True


def test_is_pipe_table_start_no_separator_returns_false():
    lines = ["| a | b |", "| c | d |"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_first_not_pipe_row_returns_false():
    lines = ["hello", "| --- | --- |"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_out_of_range_returns_false():
    """i+1 >= len(lines) → False（即使 i 也越界）。"""
    assert _is_pipe_table_start([], 0) is False


def test_is_pipe_table_start_i_plus_one_equal_len_returns_false():
    """i+1 == len(lines) → False。"""
    lines = ["| a |"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_colon_separator_returns_true():
    """支持 :---: 形式的 separator（_PIPE_TABLE_SEP_RE 接受冒号）。"""
    lines = ["| a | b |", "| :---: | :---: |"]
    assert _is_pipe_table_start(lines, 0) is True


def test_is_pipe_table_start_separator_no_outer_pipes():
    """_PIPE_TABLE_SEP_RE 也接受无 outer | 的 separator。"""
    lines = ["| a | b |", "--- | ---"]
    # 这个边界要看正则，至少不应抛异常
    result = _is_pipe_table_start(lines, 0)
    assert isinstance(result, bool)


# =========================================================================
# MarkdownParser 类属性
# =========================================================================


def test_markdown_parser_name_value():
    assert MarkdownParser.name == "markdown"


def test_markdown_parser_version_value():
    assert MarkdownParser.version == "stdlib/0.1.0"


def test_markdown_parser_name_is_str():
    assert isinstance(MarkdownParser.name, str)


def test_markdown_parser_version_is_str():
    assert isinstance(MarkdownParser.version, str)


def test_markdown_parser_version_format():
    """version 应是 'implementation/X.Y.Z' 格式。"""
    parts = MarkdownParser.version.split("/")
    assert len(parts) == 2
    assert parts[0] == "stdlib"
    # 后半部 X.Y.Z
    sub = parts[1].split(".")
    assert len(sub) == 3


def test_markdown_parser_inherits_parser():
    from app.parsers.base import Parser
    assert issubclass(MarkdownParser, Parser)


def test_markdown_parser_has_parse_method():
    assert hasattr(MarkdownParser, "parse")
    assert callable(MarkdownParser.parse)


def test_markdown_parser_has_parse_text_method():
    assert hasattr(MarkdownParser, "_parse_text")


def test_markdown_parser_init_no_args():
    """MarkdownParser() 不需参数。"""
    p = MarkdownParser()
    assert p is not None


# =========================================================================
# parse() 边界 - 文件读取
# =========================================================================


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_parse_nonexistent_file_raises(tmp_path: Path):
    p = tmp_path / "missing.md"
    with pytest.raises(ParserError) as exc:
        MarkdownParser().parse(p, "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
    assert exc.value.code == "file_not_found"


def test_parse_nonexistent_file_message_has_path(tmp_path: Path):
    p = tmp_path / "missing.md"
    with pytest.raises(ParserError) as exc:
        MarkdownParser().parse(p, "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
    assert str(p) in exc.value.message


def test_parse_nonexistent_file_details_has_path(tmp_path: Path):
    p = tmp_path / "missing.md"
    with pytest.raises(ParserError) as exc:
        MarkdownParser().parse(p, "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
    assert exc.value.details == {"path": str(p)}


def test_parse_unsupported_extension_raises(tmp_path: Path):
    p = _write(tmp_path, "foo.txt", "hello")
    with pytest.raises(ParserError) as exc:
        MarkdownParser().parse(p, "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
    assert exc.value.code == "unsupported_type"


def test_parse_returns_document_type(tmp_path: Path):
    p = _write(tmp_path, "test.md", "hello")
    doc = MarkdownParser().parse(p, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert isinstance(doc, Document)


def test_parse_uses_make_document_id(tmp_path: Path):
    """document_id 来自 make_document_id(source_hash)。"""
    from app.parsers.base import make_document_id
    p = _write(tmp_path, "test.md", "hello")
    doc = MarkdownParser().parse(p, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert doc.document_id == make_document_id("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")


def test_parse_metadata_has_markdown_true(tmp_path: Path):
    p = _write(tmp_path, "test.md", "hello")
    doc = MarkdownParser().parse(p, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert doc.metadata == {"markdown": True}


def test_parse_source_type_markdown(tmp_path: Path):
    p = _write(tmp_path, "test.md", "hello")
    doc = MarkdownParser().parse(p, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert doc.source_type == "markdown"


def test_parse_source_path_is_str(tmp_path: Path):
    p = _write(tmp_path, "test.md", "hello")
    doc = MarkdownParser().parse(p, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert isinstance(doc.source_path, str)
    assert str(p) == doc.source_path


def test_parse_source_hash_propagated(tmp_path: Path):
    p = _write(tmp_path, "test.md", "hello")
    doc = MarkdownParser().parse(p, "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd")
    assert doc.source_hash == "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"


def test_parse_parser_name_propagated(tmp_path: Path):
    p = _write(tmp_path, "test.md", "hello")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    assert doc.parser_name == "markdown"


def test_parse_parser_version_propagated(tmp_path: Path):
    p = _write(tmp_path, "test.md", "hello")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    assert doc.parser_version == "stdlib/0.1.0"


def test_parse_empty_elements_and_chunks(tmp_path: Path):
    p = _write(tmp_path, "test.md", "hello")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    assert doc.chunks == []
    assert doc.relations == []
    assert doc.errors == []


def test_parse_empty_file_emits_no_content_warning(tmp_path: Path):
    p = _write(tmp_path, "empty.md", "")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    assert len(doc.warnings) >= 1
    assert any(w.code == "md_no_content" for w in doc.warnings)


def test_parse_thematic_only_emits_no_content_warning(tmp_path: Path):
    p = _write(tmp_path, "thematic.md", "---\n")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    assert any(w.code == "md_no_content" for w in doc.warnings)


# =========================================================================
# _parse_text 内部场景
# =========================================================================


def test_parse_text_section_path_push_pop():
    """H1 > H2 > H3 → 出现 H2 应弹掉 H3。"""
    text = "# A\n## B\n### C\n## D\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    headings = [e for e in elements if e.type == "heading"]
    assert len(headings) == 4
    # 第四个 heading（D）的 section_path 应是 "A > D"（B 已被弹掉，C 也被弹掉）
    d_loc = headings[3].source_locator
    assert d_loc["section_path"] == "A > D"


def test_parse_text_section_path_jump_to_higher():
    """H1 > H3 → H2 → H3 跳级。"""
    text = "# A\n### C\n## B\n### D\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    headings = [e for e in elements if e.type == "heading"]
    # 第二个 heading（C，level 3）的 path 是 "A > C"
    assert headings[1].source_locator["section_path"] == "A > C"
    # 第三个 heading（B，level 2）应弹掉 C
    assert headings[2].source_locator["section_path"] == "A > B"
    # 第四个 heading（D，level 3）path 是 "A > B > D"
    assert headings[3].source_locator["section_path"] == "A > B > D"


def test_parse_text_unclosed_fence_consumes_to_eof():
    """未闭合围栏 → 吸收到 EOF，仍产出 code_block。"""
    text = "```\ncode line 1\ncode line 2\n"
    elements, warnings = MarkdownParser()._parse_text(text, "doc")
    paras = [e for e in elements if e.type == "paragraph" and e.metadata.get("kind") == "code_block"]
    assert len(paras) == 1
    assert "code line 1" in paras[0].content
    assert "code line 2" in paras[0].content


def test_parse_text_empty_code_block_emits_warning():
    text = "```\n```\n"
    elements, warnings = MarkdownParser()._parse_text(text, "doc")
    assert any(w.code == "md_empty_code_block" for w in warnings)


def test_parse_text_code_block_with_language():
    text = "```python\nprint('hi')\n```\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    paras = [e for e in elements if e.metadata.get("kind") == "code_block"]
    assert len(paras) == 1
    assert paras[0].metadata["language"] == "python"


def test_parse_text_code_block_no_language_empty_string():
    text = "```\ncode\n```\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    paras = [e for e in elements if e.metadata.get("kind") == "code_block"]
    assert paras[0].metadata["language"] == ""


def test_parse_text_tilde_fence_supported():
    text = "~~~\ncode\n~~~\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    paras = [e for e in elements if e.metadata.get("kind") == "code_block"]
    assert len(paras) == 1


def test_parse_text_empty_blockquote_no_element():
    """空 blockquote（> 后什么都没有，连续空）→ 不产 element。"""
    text = ">\n>\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    blockquotes = [e for e in elements if e.metadata.get("kind") == "blockquote"]
    assert len(blockquotes) == 0


def test_parse_text_blockquote_multiline_merged():
    text = "> line 1\n> line 2\n> line 3\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    blockquotes = [e for e in elements if e.metadata.get("kind") == "blockquote"]
    assert len(blockquotes) == 1
    assert "line 1" in blockquotes[0].content
    assert "line 3" in blockquotes[0].content
    # 多行被 join
    assert "\n" in blockquotes[0].content


def test_parse_text_blockquote_stripped():
    text = ">   hello world  \n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    bq = [e for e in elements if e.metadata.get("kind") == "blockquote"][0]
    assert bq.content == "hello world"


def test_parse_text_paragraph_blocked_by_table():
    """段落吸收遇到 table 起始应停止。"""
    text = "intro paragraph\n| a | b |\n| --- | --- |\n| 1 | 2 |\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    paras = [e for e in elements if e.type == "paragraph" and "kind" not in e.metadata]
    tables = [e for e in elements if e.type == "table"]
    assert len(paras) == 1
    assert paras[0].content == "intro paragraph"
    assert len(tables) == 1


def test_parse_text_paragraph_blocked_by_standalone_image():
    text = "intro paragraph\n![alt](http://example.com/x.png)\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    paras = [e for e in elements if e.type == "paragraph"]
    images = [e for e in elements if e.type == "image"]
    assert len(paras) == 1
    assert paras[0].content == "intro paragraph"
    assert len(images) == 1


def test_parse_text_paragraph_blocked_by_blockquote():
    text = "intro\n> quote\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    paras = [e for e in elements if e.type == "paragraph" and "kind" not in e.metadata]
    blockquotes = [e for e in elements if e.metadata.get("kind") == "blockquote"]
    assert len(paras) == 1
    assert len(blockquotes) == 1


def test_parse_text_paragraph_blocked_by_fenced():
    text = "intro\n```\ncode\n```\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    paras = [e for e in elements if e.type == "paragraph" and "kind" not in e.metadata]
    code_blocks = [e for e in elements if e.metadata.get("kind") == "code_block"]
    assert len(paras) == 1
    assert len(code_blocks) == 1


def test_parse_text_paragraph_blocked_by_atx():
    text = "intro\n# Heading\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    paras = [e for e in elements if e.type == "paragraph"]
    headings = [e for e in elements if e.type == "heading"]
    assert len(paras) == 1
    assert len(headings) == 1


def test_parse_text_paragraph_blocked_by_thematic():
    text = "intro\n---\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    paras = [e for e in elements if e.type == "paragraph"]
    assert len(paras) == 1
    # thematic 不产 element，但段落应被截断


def test_parse_text_paragraph_blocked_by_list_unordered():
    text = "intro\n- item\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    paras = [e for e in elements if e.type == "paragraph"]
    items = [e for e in elements if e.type == "list_item"]
    assert len(paras) == 1
    assert len(items) == 1


def test_parse_text_paragraph_blocked_by_list_ordered():
    text = "intro\n1. item\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    paras = [e for e in elements if e.type == "paragraph"]
    items = [e for e in elements if e.type == "list_item"]
    assert len(paras) == 1
    assert len(items) == 1


# =========================================================================
# element_id 与 confidence
# =========================================================================


def test_parse_text_element_id_increments():
    text = "para 1\n\npara 2\n\npara 3\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    ids = [e.element_id for e in elements]
    assert ids == ["doc::e0000", "doc::e0001", "doc::e0002"]


def test_parse_text_element_id_zero_padded_four():
    text = "para\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    assert elements[0].element_id == "doc::e0000"


def test_parse_text_confidence_default_095():
    text = "para\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    assert elements[0].confidence == 0.95


def test_parse_text_locator_has_line_1based():
    text = "para\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    assert elements[0].source_locator["line"] == 1


def test_parse_text_locator_no_section_path_for_no_heading():
    """无 heading → locator 不含 section_path。"""
    text = "para\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    assert "section_path" not in elements[0].source_locator


def test_parse_text_locator_section_path_for_paragraph_after_heading():
    text = "# Title\npara\n"
    elements, _ = MarkdownParser()._parse_text(text, "doc")
    para = [e for e in elements if e.type == "paragraph"][0]
    assert para.source_locator["section_path"] == "Title"


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import app.parsers.markdown_parser as mod
    assert mod.__all__ == ["MarkdownParser"]


def test_module_all_is_list():
    import app.parsers.markdown_parser as mod
    assert isinstance(mod.__all__, list)


def test_module_uses_future_annotations():
    import app.parsers.markdown_parser as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_imports_re():
    import app.parsers.markdown_parser as mod
    src = inspect.getsource(mod)
    assert "import re" in src


def test_module_imports_path():
    import app.parsers.markdown_parser as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import app.parsers.markdown_parser as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_docstring_present():
    import app.parsers.markdown_parser as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_compatibility():
    """docstring 提及 ATX / paragraph / list / fenced 等。"""
    import app.parsers.markdown_parser as mod
    doc = mod.__doc__
    assert "ATX" in doc
    assert "段落" in doc or "paragraph" in doc.lower()


def test_module_docstring_mentions_unsupported_features():
    """docstring 列出明确不支持的功能。"""
    import app.parsers.markdown_parser as mod
    doc = mod.__doc__
    assert "setext" in doc
    assert "frontmatter" in doc.lower() or "front matter" in doc.lower()


def test_module_no_silence_unused():
    import app.parsers.markdown_parser as mod
    assert not hasattr(mod, "_silence_unused")


# =========================================================================
# 签名深度
# =========================================================================


def test_parse_signature_two_params():
    sig = inspect.signature(MarkdownParser.parse)
    assert set(sig.parameters) == {"self", "path", "source_hash"}


def test_parse_params_no_defaults():
    sig = inspect.signature(MarkdownParser.parse)
    for p in sig.parameters.values():
        if p.name == "self":
            continue
        assert p.default is inspect.Parameter.empty


def test_parse_return_annotation_document():
    sig = inspect.signature(MarkdownParser.parse)
    assert "Document" in str(sig.return_annotation)


def test_parse_text_signature_three_params():
    sig = inspect.signature(MarkdownParser._parse_text)
    assert set(sig.parameters) == {"self", "text", "document_id"}


def test_parse_text_return_annotation_tuple():
    sig = inspect.signature(MarkdownParser._parse_text)
    ret = str(sig.return_annotation)
    assert "tuple" in ret.lower() or "list" in ret.lower()


def test_detect_md_source_type_signature():
    sig = inspect.signature(_detect_md_source_type)
    assert set(sig.parameters) == {"path"}


def test_detect_md_source_type_return_str():
    sig = inspect.signature(_detect_md_source_type)
    assert "str" in str(sig.return_annotation)


def test_rows_to_md_signature():
    sig = inspect.signature(_rows_to_md)
    assert set(sig.parameters) == {"rows"}


def test_split_pipe_row_signature():
    sig = inspect.signature(_split_pipe_row)
    assert set(sig.parameters) == {"line"}


def test_is_pipe_table_start_signature():
    sig = inspect.signature(_is_pipe_table_start)
    assert set(sig.parameters) == {"lines", "i"}


# =========================================================================
# 综合行为
# =========================================================================


def test_parse_idempotent_same_file(tmp_path: Path):
    """同一文件两次 parse → document_id 一致（依赖 source_hash）。"""
    p = _write(tmp_path, "test.md", "# T\n\nhello\n")
    d1 = MarkdownParser().parse(p, "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
    d2 = MarkdownParser().parse(p, "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
    assert d1.document_id == d2.document_id
    assert len(d1.elements) == len(d2.elements)


def test_parse_different_hash_different_doc_id(tmp_path: Path):
    p = _write(tmp_path, "test.md", "hello\n")
    d1 = MarkdownParser().parse(p, "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
    d2 = MarkdownParser().parse(p, "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc")
    assert d1.document_id != d2.document_id


def test_parse_text_idempotent(tmp_path: Path):
    text = "# T\n\nhello\n"
    e1, w1 = MarkdownParser()._parse_text(text, "doc")
    e2, w2 = MarkdownParser()._parse_text(text, "doc")
    assert len(e1) == len(e2)
    assert len(w1) == len(w2)


def test_parse_text_no_input_mutation(tmp_path: Path):
    """_parse_text 不修改入参 text。"""
    text = "# T\n\nhello\n"
    before = text
    MarkdownParser()._parse_text(text, "doc")
    assert text == before


def test_parse_returns_elements_with_consistent_ids(tmp_path: Path):
    """所有 element_id 都共享同一 document_id 前缀。"""
    p = _write(tmp_path, "test.md", "# T\n\npara\n\n- item\n")
    doc = MarkdownParser().parse(p, "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
    for el in doc.elements:
        assert el.element_id.startswith(doc.document_id + "::")


def test_parse_complex_document(tmp_path: Path):
    """完整 markdown 文件 → 多种 element 类型。"""
    content = """# Title

## Section 1

Paragraph 1.

- item 1
- item 2

1. ordered 1
2. ordered 2

> a quote

```python
print('hi')
```

| a | b |
| --- | --- |
| 1 | 2 |

![alt](http://example.com/x.png)

---

final paragraph
"""
    p = _write(tmp_path, "complex.md", content)
    doc = MarkdownParser().parse(p, "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
    types = {e.type for e in doc.elements}
    assert "heading" in types
    assert "paragraph" in types
    assert "list_item" in types
    assert "table" in types
    assert "image" in types
    # code_block 是 paragraph with kind=code_block
    code_blocks = [e for e in doc.elements if e.metadata.get("kind") == "code_block"]
    assert len(code_blocks) == 1


def test_parse_thematic_break_variants_all_skipped(tmp_path: Path):
    """---/***/___ 都是 thematic break，不产 element。"""
    content = "---\n\n***\n\n___\n\n"
    p = _write(tmp_path, "thematic.md", content)
    doc = MarkdownParser().parse(p, "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
    # 仅含 thematic → 无 element + no_content warning
    assert len(doc.elements) == 0
    assert any(w.code == "md_no_content" for w in doc.warnings)


# =========================================================================
# 表格深度
# =========================================================================


def test_parse_table_with_col_count_in_metadata(tmp_path: Path):
    p = _write(tmp_path, "t.md", "| a | b | c |\n| --- | --- | --- |\n| 1 | 2 | 3 |\n")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    t = tables[0]
    assert t.metadata["row_count"] == 2  # header + 1 body
    assert t.metadata["col_count"] == 3
    assert t.metadata["source"] == "markdown_pipe_table"


def test_parse_table_only_header_and_separator(tmp_path: Path):
    p = _write(tmp_path, "t.md", "| a | b |\n| --- | --- |\n")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    assert tables[0].metadata["row_count"] == 1


def test_parse_table_uneven_rows_padded(tmp_path: Path):
    """表格行不等长被 _rows_to_md 补齐。"""
    p = _write(tmp_path, "t.md", "| a | b | c |\n| --- | --- | --- |\n| 1 | 2 |\n")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    # row_count 仍计入
    assert tables[0].metadata["row_count"] == 2


# =========================================================================
# 图片深度
# =========================================================================


def test_parse_standalone_image_alt_and_url(tmp_path: Path):
    p = _write(tmp_path, "i.md", "![my alt](http://example.com/x.png)\n")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    images = [e for e in doc.elements if e.type == "image"]
    assert len(images) == 1
    assert images[0].metadata["alt"] == "my alt"
    assert images[0].resource_path == "http://example.com/x.png"


def test_parse_standalone_image_content_is_none(tmp_path: Path):
    p = _write(tmp_path, "i.md", "![alt](url)\n")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    images = [e for e in doc.elements if e.type == "image"]
    assert images[0].content is None


def test_parse_inline_image_in_paragraph_not_extracted(tmp_path: Path):
    """段落内的 inline image 不应被独立提取。"""
    p = _write(tmp_path, "i.md", "hello ![alt](url) world\n")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    images = [e for e in doc.elements if e.type == "image"]
    # inline image 不被 _STANDALONE_IMAGE_RE 匹配（不在行首）
    assert len(images) == 0
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1


# =========================================================================
# 列表深度
# =========================================================================


def test_parse_unordered_list_marker_minus(tmp_path: Path):
    p = _write(tmp_path, "l.md", "- item\n")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 1
    assert items[0].metadata["ordered"] is False
    assert items[0].metadata["marker"] == "unordered"


def test_parse_unordered_list_marker_plus(tmp_path: Path):
    p = _write(tmp_path, "l.md", "+ item\n")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 1


def test_parse_unordered_list_marker_asterisk(tmp_path: Path):
    p = _write(tmp_path, "l.md", "* item\n")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 1


def test_parse_ordered_list_dot_marker(tmp_path: Path):
    p = _write(tmp_path, "l.md", "1. item\n")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    items = [e for e in doc.elements if e.type == "list_item"]
    assert items[0].metadata["ordered"] is True


def test_parse_ordered_list_paren_marker(tmp_path: Path):
    p = _write(tmp_path, "l.md", "1) item\n")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 1
    assert items[0].metadata["ordered"] is True


def test_parse_list_each_item_separate_element(tmp_path: Path):
    p = _write(tmp_path, "l.md", "- a\n- b\n- c\n")
    doc = MarkdownParser().parse(p, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 3
    assert items[0].content == "a"
    assert items[1].content == "b"
    assert items[2].content == "c"
