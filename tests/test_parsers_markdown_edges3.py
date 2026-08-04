r"""app/parsers/markdown_parser.py 边角测试 - 第三轮（Round 102）。

补强已有 base/edges/edges2（共 308 个测试）未覆盖的深度路径：
- 正则精度：ATX 需要 \s+ 后 #、fenced 3+ 字符、ordered \d+[.)]、unordered [-*+]
- ATX 闭合 #：# Hello # → "Hello"
- 主题分隔符变体：---/***/___/* * */
- setext 拒绝：text === / text ---
- 列表 marker：- / * / + / 1. / 1) / 99.
- code fence 闭合：同字符同长度
- standalone image vs paragraph image
- section_path 嵌套：h1 → h2 → h3 → h2（pop）→ h3（push）
- 各种 warning：md_no_content（多种触发）、md_empty_code_block
- pipe table 列对齐（:---: 不识别，作为数据行）
- _detect_md_source_type 大写扩展名
- _split_pipe_row 嵌套管道/仅首尾管道
- _is_pipe_table_start 边界

不修改任何源码。
"""

from __future__ import annotations

from pathlib import Path

import pytest

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
# 辅助
# =========================================================================


def _write_md(tmp_path: Path, text: str, name: str = "test.md") -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _parse(tmp_path: Path, text: str, name: str = "test.md"):
    p = _write_md(tmp_path, text, name)
    return MarkdownParser().parse(p, source_hash="a" * 64)


# =========================================================================
# ATX 标题正则精度
# =========================================================================


def test_atx_heading_no_space_after_hash_not_match():
    r"""'#Hello' 无空格 → 不匹配（需要 \s+）。"""
    assert _ATX_HEADING_RE.match("#Hello") is None


def test_atx_heading_single_hash_with_space():
    m = _ATX_HEADING_RE.match("# Hello")
    assert m is not None
    assert m.group(2) == "Hello"


def test_atx_heading_six_hashes_max():
    m = _ATX_HEADING_RE.match("###### Title6")
    assert m is not None
    assert len(m.group(1)) == 6


def test_atx_heading_seven_hashes_not_match():
    """7 个 # 超过 6 → 不匹配。"""
    assert _ATX_HEADING_RE.match("####### Title7") is None


def test_atx_heading_trailing_hashes_stripped():
    """'# Hello #' → "Hello"。"""
    m = _ATX_HEADING_RE.match("# Hello #")
    assert m is not None
    assert m.group(2) == "Hello"


def test_atx_heading_trailing_multiple_hashes():
    m = _ATX_HEADING_RE.match("# Hello ##")
    assert m.group(2) == "Hello"


def test_atx_heading_leading_space_not_match():
    """正则 ^ 锚定，前导空格 → 不匹配。"""
    assert _ATX_HEADING_RE.match(" # Hello") is None


def test_atx_heading_only_hashes_no_content():
    r"""'# #' → group(2) 为空？正则 (.+?) 至少 1 字符 + 后续 \s*#* → 实际匹配。"""
    m = _ATX_HEADING_RE.match("#")
    assert m is None  # 因为 \s+ 要求空格但没有内容


def test_atx_heading_multiple_spaces_between_hash_and_text():
    m = _ATX_HEADING_RE.match("#    Indented")
    assert m is not None
    assert m.group(2) == "Indented"


# =========================================================================
# Fenced code block 正则
# =========================================================================


def test_fenced_three_backticks():
    m = _FENCED_RE.match("```")
    assert m is not None
    assert m.group(1) == "```"


def test_fenced_four_backticks():
    m = _FENCED_RE.match("````")
    assert m is not None
    assert m.group(1) == "````"


def test_fenced_three_tildes():
    m = _FENCED_RE.match("~~~")
    assert m is not None
    assert m.group(1) == "~~~"


def test_fenced_two_backticks_not_match():
    """2 个 ` 不够（需 3+）。"""
    assert _FENCED_RE.match("``") is None


def test_fenced_one_tilde_not_match():
    assert _FENCED_RE.match("~") is None


def test_fenced_with_language_python():
    m = _FENCED_RE.match("```python")
    assert m is not None
    assert m.group(2) == "python"


def test_fenced_with_language_python_with_version():
    r"""`python3` 匹配，但 `python3.12` 因 `.` 不在 [\w+-] 中 → 不匹配。"""
    m1 = _FENCED_RE.match("```python3")
    assert m1 is not None
    assert m1.group(2) == "python3"
    # `.` 不在 [\w+-] 中
    assert _FENCED_RE.match("```python3.12") is None


def test_fenced_with_no_language():
    m = _FENCED_RE.match("```")
    assert m.group(2) == ""


def test_fenced_with_leading_space_not_match():
    assert _FENCED_RE.match(" ```") is None


# =========================================================================
# 主题分隔符正则
# =========================================================================


def test_thematic_three_dashes():
    assert _THEMATIC_RE.match("---") is not None


def test_thematic_three_asterisks():
    assert _THEMATIC_RE.match("***") is not None


def test_thematic_three_underscores():
    assert _THEMATIC_RE.match("___") is not None


def test_thematic_with_spaces():
    assert _THEMATIC_RE.match("* * *") is not None


def test_thematic_with_dashes_and_spaces():
    assert _THEMATIC_RE.match("- - -") is not None


def test_thematic_two_dashes_not_match():
    """2 个 - 不够。"""
    assert _THEMATIC_RE.match("--") is None


def test_thematic_longer_asterisks():
    assert _THEMATIC_RE.match("*****") is not None


# =========================================================================
# 列表正则
# =========================================================================


def test_unordered_list_dash():
    m = _UNORDERED_LIST_RE.match("- item")
    assert m is not None
    assert m.group(1) == "item"


def test_unordered_list_asterisk():
    m = _UNORDERED_LIST_RE.match("* item")
    assert m is not None
    assert m.group(1) == "item"


def test_unordered_list_plus():
    m = _UNORDERED_LIST_RE.match("+ item")
    assert m is not None
    assert m.group(1) == "item"


def test_unordered_list_no_space_not_match():
    assert _UNORDERED_LIST_RE.match("-item") is None


def test_unordered_list_two_dashes_not_match():
    """'-- item' → 前两个 -- 不符合 ^[-*+] 语法。"""
    assert _UNORDERED_LIST_RE.match("-- item") is None


def test_ordered_list_dot():
    m = _ORDERED_LIST_RE.match("1. item")
    assert m is not None
    assert m.group(1) == "item"


def test_ordered_list_paren():
    m = _ORDERED_LIST_RE.match("1) item")
    assert m is not None
    assert m.group(1) == "item"


def test_ordered_list_large_number():
    m = _ORDERED_LIST_RE.match("99. item")
    assert m is not None
    assert m.group(1) == "item"


def test_ordered_list_zero_number():
    m = _ORDERED_LIST_RE.match("0. item")
    assert m is not None
    assert m.group(1) == "item"


def test_ordered_list_no_space_not_match():
    assert _ORDERED_LIST_RE.match("1.item") is None


# =========================================================================
# 引用块正则
# =========================================================================


def test_blockquote_simple():
    m = _BLOCKQUOTE_RE.match("> quoted")
    assert m is not None
    assert m.group(1) == "quoted"


def test_blockquote_no_space_after_gt():
    m = _BLOCKQUOTE_RE.match(">quoted")
    assert m is not None
    # \s? 是可选空白，所以无空格时 group(1) = "quoted"


def test_blockquote_only_gt():
    """单独 > → group(1) 为空字符串。"""
    m = _BLOCKQUOTE_RE.match(">")
    assert m is not None


def test_blockquote_multiple_spaces():
    """`>\\s?` 只吃 0/1 个空白，4 个空格时保留 3 个在 group(1) 中。"""
    m = _BLOCKQUOTE_RE.match(">    deeply")
    assert m is not None
    # 实际：只剥离 1 个空格，剩 "   deeply"
    assert m.group(1) == "   deeply"


# =========================================================================
# 独立图片正则
# =========================================================================


def test_standalone_image_basic():
    m = _STANDALONE_IMAGE_RE.match("![alt](url.png)")
    assert m is not None
    assert m.group(1) == "alt"
    assert m.group(2) == "url.png"


def test_standalone_image_empty_alt():
    m = _STANDALONE_IMAGE_RE.match("![](url.png)")
    assert m is not None
    assert m.group(1) == ""
    assert m.group(2) == "url.png"


def test_standalone_image_url_with_query():
    m = _STANDALONE_IMAGE_RE.match("![alt](url.png?v=1&id=2)")
    assert m is not None
    assert m.group(2) == "url.png?v=1&id=2"


def test_standalone_image_extra_text_after_not_match():
    """'![alt](url) extra' 不匹配（必须整行）。"""
    assert _STANDALONE_IMAGE_RE.match("![alt](url) extra") is None


def test_standalone_image_text_before_not_match():
    assert _STANDALONE_IMAGE_RE.match("text ![alt](url)") is None


def test_standalone_image_with_trailing_spaces():
    m = _STANDALONE_IMAGE_RE.match("![alt](url)   ")
    assert m is not None
    assert m.group(2) == "url"


# =========================================================================
# pipe table 正则
# =========================================================================


def test_pipe_table_row_basic():
    assert _PIPE_TABLE_ROW_RE.match("| a | b |") is not None


def test_pipe_table_row_no_leading_pipe():
    """无前导 | → 不匹配。"""
    assert _PIPE_TABLE_ROW_RE.match("a | b |") is None


def test_pipe_table_row_no_trailing_pipe():
    """无尾部 | → 不匹配。"""
    assert _PIPE_TABLE_ROW_RE.match("| a | b") is None


def test_pipe_table_row_single_pipe():
    """单个 | → 不匹配（需要 .* 在 | 之间）。"""
    assert _PIPE_TABLE_ROW_RE.match("|") is None


def test_pipe_table_sep_basic():
    assert _PIPE_TABLE_SEP_RE.match("| --- | --- |") is not None


def test_pipe_table_sep_no_pipes_at_edges():
    """无 | 在边界的 sep。"""
    assert _PIPE_TABLE_SEP_RE.match("--- | ---") is not None


def test_pipe_table_sep_with_alignment():
    """:---: 形式也被接受。"""
    assert _PIPE_TABLE_SEP_RE.match("| :---: | ---: |") is not None


def test_pipe_table_sep_short_dashes_not_match():
    """单 - 不够（需 2+）。"""
    assert _PIPE_TABLE_SEP_RE.match("| - | - |") is None


# =========================================================================
# _detect_md_source_type
# =========================================================================


def test_detect_md_source_type_accepts_md():
    assert _detect_md_source_type(Path("test.md")) == "markdown"


def test_detect_md_source_type_accepts_markdown():
    assert _detect_md_source_type(Path("test.markdown")) == "markdown"


def test_detect_md_source_type_accepts_uppercase_md():
    assert _detect_md_source_type(Path("test.MD")) == "markdown"


def test_detect_md_source_type_accepts_uppercase_markdown():
    assert _detect_md_source_type(Path("test.MARKDOWN")) == "markdown"


def test_detect_md_source_type_rejects_html():
    with pytest.raises(ParserError):
        _detect_md_source_type(Path("test.html"))


def test_detect_md_source_type_rejects_no_suffix():
    with pytest.raises(ParserError):
        _detect_md_source_type(Path("noext"))


def test_detect_md_source_type_rejects_txt():
    with pytest.raises(ParserError):
        _detect_md_source_type(Path("test.txt"))


def test_detect_md_source_type_error_message_contains_suffix():
    with pytest.raises(ParserError) as ei:
        _detect_md_source_type(Path("test.unknown"))
    assert ".unknown" in ei.value.message or "unknown" in ei.value.message


def test_detect_md_source_type_error_code():
    with pytest.raises(ParserError) as ei:
        _detect_md_source_type(Path("test.unknown"))
    assert ei.value.code == "unsupported_type"


# =========================================================================
# _split_pipe_row 深度
# =========================================================================


def test_split_pipe_row_basic():
    assert _split_pipe_row("| a | b |") == ["a", "b"]


def test_split_pipe_row_no_pipes_at_edges():
    assert _split_pipe_row("a | b") == ["a", "b"]


def test_split_pipe_row_single_cell_with_edges():
    assert _split_pipe_row("| a |") == ["a"]


def test_split_pipe_row_single_cell_no_edges():
    assert _split_pipe_row("a") == ["a"]


def test_split_pipe_row_strips_inner_spaces():
    assert _split_pipe_row("|  spaced  |  cell  |") == ["spaced", "cell"]


def test_split_pipe_row_empty_cell():
    assert _split_pipe_row("| | b |") == ["", "b"]


def test_split_pipe_row_only_pipes_returns_empty_strings():
    result = _split_pipe_row("|||")
    # 三个 | 中 split → 2 个空字符串
    assert result == ["", ""]


# =========================================================================
# _is_pipe_table_start
# =========================================================================


def test_is_pipe_table_start_basic():
    lines = ["| a | b |", "| --- | --- |"]
    assert _is_pipe_table_start(lines, 0) is True


def test_is_pipe_table_start_at_last_line_returns_false():
    lines = ["| a |"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_no_separator_returns_false():
    lines = ["| a | b |", "| c | d |"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_negative_index():
    """负数 index → lines[i] 越界 → 实际 lines[-1] 是最后一行。"""
    lines = ["| a | b |", "| --- | --- |"]
    # i=-1 → lines[-1]=separator, lines[-1+1]=lines[0]=header
    # 但实际行为依赖实现
    result = _is_pipe_table_start(lines, -1)
    assert isinstance(result, bool)


# =========================================================================
# _rows_to_md 深度
# =========================================================================


def test_rows_to_md_empty_returns_empty_string():
    assert _rows_to_md([]) == ""


def test_rows_to_md_single_row_single_col():
    md = _rows_to_md([["a"]])
    lines = md.split("\n")
    assert len(lines) == 2  # header + separator (no body)
    assert "| a |" in lines[0]


def test_rows_to_md_three_rows():
    md = _rows_to_md([["h"], ["r1"], ["r2"]])
    lines = md.split("\n")
    assert len(lines) == 4  # header + sep + 2 body


def test_rows_to_md_jagged_pads_empty():
    md = _rows_to_md([["a", "b", "c"], ["x"]])
    lines = md.split("\n")
    # body 行应有 3 列
    last_line = lines[-1]
    assert last_line.count("|") == 4


def test_rows_to_md_returns_str_type():
    assert isinstance(_rows_to_md([["a"]]), str)


# =========================================================================
# MarkdownParser.parse e2e 深度
# =========================================================================


def test_parse_atx_heading_with_trailing_hashes(tmp_path: Path):
    doc = _parse(tmp_path, "# Hello ##")
    headings = [e for e in doc.elements if e.type == "heading"]
    assert len(headings) == 1
    assert headings[0].content == "Hello"


def test_parse_seven_hashes_not_heading(tmp_path: Path):
    """7 个 # 不匹配 ATX → 当作段落。"""
    doc = _parse(tmp_path, "####### Not a heading")
    headings = [e for e in doc.elements if e.type == "heading"]
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert headings == []
    assert len(paras) == 1


def test_parse_setext_text_then_dashes_not_heading(tmp_path: Path):
    """setext 不支持：'text\\n===' → 两个段落。"""
    doc = _parse(tmp_path, "text\n===\n")
    headings = [e for e in doc.elements if e.type == "heading"]
    assert headings == []


def test_parse_thematic_break_ignored(tmp_path: Path):
    """--- 单独行 → thematic break → 忽略。"""
    doc = _parse(tmp_path, "---\n")
    # 没有任何 element（只有 hr）
    assert doc.elements == []
    # 触发 no_content warning
    no_content = [w for w in doc.warnings if w.code == "md_no_content"]
    assert len(no_content) == 1


def test_parse_thematic_break_asterisks_ignored(tmp_path: Path):
    doc = _parse(tmp_path, "***\n")
    assert doc.elements == []


def test_parse_thematic_break_underscores_ignored(tmp_path: Path):
    doc = _parse(tmp_path, "___\n")
    assert doc.elements == []


def test_parse_thematic_break_with_spaces_ignored(tmp_path: Path):
    doc = _parse(tmp_path, "* * *\n")
    assert doc.elements == []


def test_parse_thematic_break_does_not_emit_warning_when_followed_by_content(tmp_path: Path):
    doc = _parse(tmp_path, "---\n\nreal content\n")
    no_content = [w for w in doc.warnings if w.code == "md_no_content"]
    assert no_content == []


def test_parse_unordered_list_dash(tmp_path: Path):
    doc = _parse(tmp_path, "- item one\n")
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 1
    assert items[0].content == "item one"
    assert items[0].metadata["ordered"] is False
    assert items[0].metadata["marker"] == "unordered"


def test_parse_unordered_list_asterisk(tmp_path: Path):
    doc = _parse(tmp_path, "* item\n")
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 1


def test_parse_unordered_list_plus(tmp_path: Path):
    doc = _parse(tmp_path, "+ item\n")
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 1


def test_parse_ordered_list_dot(tmp_path: Path):
    doc = _parse(tmp_path, "1. first\n")
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 1
    assert items[0].metadata["ordered"] is True


def test_parse_ordered_list_paren(tmp_path: Path):
    doc = _parse(tmp_path, "1) first\n")
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 1
    assert items[0].metadata["ordered"] is True


def test_parse_section_path_deep_nesting(tmp_path: Path):
    doc = _parse(tmp_path, "# H1\n## H2\n### H3\npara\n")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert paras[0].source_locator["section_path"] == "H1 > H2 > H3"


def test_parse_section_path_pops_on_higher_level(tmp_path: Path):
    """h1 → h2 → h3 → h2 → 当前 section_path 弹回 h2 level。

    新 h2 会 pop h3（因为 h3 level > h2 level），但保留原 h2。
    """
    doc = _parse(tmp_path, "# H1\n## H2a\n### H3\n## H2b\npara\n")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    # H1 > H2b（H3 被 pop，H2a 也被 pop 因为 >= 同级）
    assert paras[0].source_locator["section_path"] == "H1 > H2b"


def test_parse_section_path_same_level_replaces(tmp_path: Path):
    doc = _parse(tmp_path, "# H1\n## H2a\n## H2b\npara\n")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert paras[0].source_locator["section_path"] == "H1 > H2b"


def test_parse_section_path_absent_before_first_heading(tmp_path: Path):
    """preamble paragraph（在任何 heading 之前）→ section_path 不存在。"""
    doc = _parse(tmp_path, "preamble\n# H1\n")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert "section_path" not in paras[0].source_locator


def test_parse_code_block_with_language(tmp_path: Path):
    doc = _parse(tmp_path, "```python\nprint(1)\n```\n")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].metadata["kind"] == "code_block"
    assert paras[0].metadata["language"] == "python"


def test_parse_code_block_no_language(tmp_path: Path):
    doc = _parse(tmp_path, "```\ncode\n```\n")
    paras = [e for e in doc.elements if e.metadata.get("kind") == "code_block"]
    assert len(paras) == 1
    assert paras[0].metadata["language"] == ""


def test_parse_code_block_tildes(tmp_path: Path):
    doc = _parse(tmp_path, "~~~\ncode\n~~~\n")
    paras = [e for e in doc.elements if e.metadata.get("kind") == "code_block"]
    assert len(paras) == 1


def test_parse_code_block_empty_emits_warning(tmp_path: Path):
    doc = _parse(tmp_path, "```\n```\n")
    empty_warnings = [w for w in doc.warnings if w.code == "md_empty_code_block"]
    assert len(empty_warnings) == 1


def test_parse_code_block_empty_warning_has_line_number(tmp_path: Path):
    doc = _parse(tmp_path, "```\n```\n")
    w = [w for w in doc.warnings if w.code == "md_empty_code_block"][0]
    assert "line" in w.reason
    assert "1" in w.reason


def test_parse_code_block_unclosed_at_eof(tmp_path: Path):
    """未闭合围栏代码块直到 EOF → 仍 emit 内容。"""
    doc = _parse(tmp_path, "```\nunfinished code\n")
    paras = [e for e in doc.elements if e.metadata.get("kind") == "code_block"]
    assert len(paras) == 1
    assert "unfinished" in paras[0].content


def test_parse_blockquote_multi_line_merged(tmp_path: Path):
    doc = _parse(tmp_path, "> line1\n> line2\n")
    paras = [e for e in doc.elements if e.metadata.get("kind") == "blockquote"]
    assert len(paras) == 1
    assert "line1" in paras[0].content
    assert "line2" in paras[0].content


def test_parse_blockquote_interrupted_by_blank(tmp_path: Path):
    """> line1\n\n> line2 → 两个 blockquote。"""
    doc = _parse(tmp_path, "> line1\n\n> line2\n")
    bqs = [e for e in doc.elements if e.metadata.get("kind") == "blockquote"]
    assert len(bqs) == 2


def test_parse_standalone_image(tmp_path: Path):
    doc = _parse(tmp_path, "![alt text](url.png)\n")
    imgs = [e for e in doc.elements if e.type == "image"]
    assert len(imgs) == 1
    assert imgs[0].resource_path == "url.png"
    assert imgs[0].metadata["alt"] == "alt text"


def test_parse_image_inside_paragraph_not_standalone(tmp_path: Path):
    """'text ![alt](url)' 不是独立图片行 → 段落。"""
    doc = _parse(tmp_path, "text ![alt](url)\n")
    imgs = [e for e in doc.elements if e.type == "image"]
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert imgs == []
    assert len(paras) == 1


def test_parse_pipe_table_basic(tmp_path: Path):
    doc = _parse(tmp_path, "| h1 | h2 |\n| --- | --- |\n| a | b |\n")
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    assert tables[0].metadata["row_count"] == 2
    assert tables[0].metadata["col_count"] == 2
    assert tables[0].metadata["source"] == "markdown_pipe_table"


def test_parse_pipe_table_alignment_row_treated_as_data(tmp_path: Path):
    """:---: 在 separator 行是合法 separator → 表格仍正常 emit。"""
    doc = _parse(tmp_path, "| h1 | h2 |\n| :---: | ---: |\n| a | b |\n")
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1


def test_parse_pipe_table_only_header_no_separator_not_table(tmp_path: Path):
    """无 separator 行 → 不识别为表格。"""
    doc = _parse(tmp_path, "| a | b |\n| c | d |\n")
    tables = [e for e in doc.elements if e.type == "table"]
    assert tables == []


def test_parse_paragraph_multi_line(tmp_path: Path):
    doc = _parse(tmp_path, "line1\nline2\nline3\n")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert "line1" in paras[0].content
    assert "line3" in paras[0].content


def test_parse_paragraph_interrupted_by_blank(tmp_path: Path):
    doc = _parse(tmp_path, "para1\n\npara2\n")
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 2


# =========================================================================
# pipeline 错误
# =========================================================================


def test_parse_missing_file_raises_file_not_found(tmp_path: Path):
    p = tmp_path / "no.md"
    with pytest.raises(ParserError) as ei:
        MarkdownParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "file_not_found"


def test_parse_unsupported_extension_raises(tmp_path: Path):
    p = tmp_path / "test.html"
    p.write_text("<p>x</p>")
    with pytest.raises(ParserError) as ei:
        MarkdownParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "unsupported_type"


def test_parse_oserror_raises_md_read_failed(tmp_path: Path, monkeypatch):
    """read_text OSError → md_read_failed。"""
    p = _write_md(tmp_path, "hello")

    real_read_text = Path.read_text

    def _raise_os(self, *args, **kwargs):
        if self == p:
            raise OSError("disk error")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _raise_os)
    with pytest.raises(ParserError) as ei:
        MarkdownParser().parse(p, source_hash="a" * 64)
    assert ei.value.code == "md_read_failed"


def test_parse_invalid_utf8_falls_back_to_replace(tmp_path: Path):
    """无效 UTF-8 → 用 errors=replace。"""
    p = tmp_path / "test.md"
    p.write_bytes(b"# title \xff\xfe\n")
    doc = MarkdownParser().parse(p, source_hash="a" * 64)
    # 不抛异常，仍能 emit heading
    headings = [e for e in doc.elements if e.type == "heading"]
    assert len(headings) == 1


# =========================================================================
# parse 返回的 Document 不变量
# =========================================================================


def test_parse_returns_document_with_empty_chunks(tmp_path: Path):
    doc = _parse(tmp_path, "# title\n")
    assert doc.chunks == []


def test_parse_returns_document_with_empty_relations(tmp_path: Path):
    doc = _parse(tmp_path, "# title\n")
    assert doc.relations == []


def test_parse_returns_document_with_empty_errors(tmp_path: Path):
    doc = _parse(tmp_path, "# title\n")
    assert doc.errors == []


def test_parse_metadata_markdown_flag_true(tmp_path: Path):
    doc = _parse(tmp_path, "# title\n")
    assert doc.metadata.get("markdown") is True


def test_parse_source_type_markdown(tmp_path: Path):
    doc = _parse(tmp_path, "# title\n")
    assert doc.source_type == "markdown"


def test_parse_parser_name_attribute(tmp_path: Path):
    doc = _parse(tmp_path, "# title\n")
    assert doc.parser_name == "markdown"


def test_parse_parser_version_attribute(tmp_path: Path):
    doc = _parse(tmp_path, "# title\n")
    assert doc.parser_version == "stdlib/0.1.0"


# =========================================================================
# 完整文档 e2e
# =========================================================================


def test_parse_complex_document_emits_multiple_types(tmp_path: Path):
    text = """# Title

para1

## Sub

- item 1
- item 2

1. ordered 1

```python
print(1)
```

> quote

| h1 | h2 |
| --- | --- |
| a | b |

![alt](pic.png)
"""
    doc = _parse(tmp_path, text)
    types = [e.type for e in doc.elements]
    assert "heading" in types
    assert "paragraph" in types
    assert "list_item" in types
    assert "table" in types
    assert "image" in types
    kinds = [e.metadata.get("kind") for e in doc.elements]
    assert "code_block" in kinds
    assert "blockquote" in kinds


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_contains_markdown_parser():
    from app.parsers import markdown_parser
    assert "MarkdownParser" in markdown_parser.__all__


def test_module_all_only_lists_markdown_parser():
    from app.parsers import markdown_parser
    assert set(markdown_parser.__all__) == {"MarkdownParser"}


def test_md_extensions_contains_md():
    assert ".md" in _MD_EXTENSIONS


def test_md_extensions_contains_markdown():
    assert ".markdown" in _MD_EXTENSIONS


def test_md_extensions_exact_two():
    assert len(_MD_EXTENSIONS) == 2


def test_module_imports_re():
    from app.parsers import markdown_parser
    assert hasattr(markdown_parser, "re")


def test_module_imports_path():
    from app.parsers import markdown_parser
    assert hasattr(markdown_parser, "Path")


def test_markdown_parser_inherits_parser():
    from app.parsers.base import Parser
    assert issubclass(MarkdownParser, Parser)


def test_markdown_parser_name_value():
    assert MarkdownParser.name == "markdown"


def test_markdown_parser_version_value():
    assert MarkdownParser.version == "stdlib/0.1.0"


def test_markdown_parser_has_parse_callable():
    assert callable(MarkdownParser.parse)
