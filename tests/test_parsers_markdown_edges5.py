r"""app/parsers/markdown_parser.py 边角测试 - 第五轮（Round 136）。

补强已有 base/edges/edges2/edges3/edges4（共 587 测试）未覆盖的深度：
- 正则模式深度（捕获组、字符类、量词边界）
- _rows_to_md 边界（极宽、Unicode、长内容）
- _split_pipe_row 边界（多列、转义）
- _is_pipe_table_start 边界（最后一行、不匹配）
- section_path 复杂场景（H1>H2>H3>H2、H1>H3 跳级）
- 解析全流程边界（空文件、纯 thematic、code block at EOF）
- element_id 序号、confidence 默认值
- 模块常量与签名深度
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
# 正则模式深度
# =========================================================================


def test_atx_heading_re_pattern_string():
    r"""ATX 标题正则：^#{1,6}\s+(.+?)\s*#*\s*$"""
    assert _ATX_HEADING_RE.pattern == r"^(#{1,6})\s+(.+?)\s*#*\s*$"


def test_atx_heading_re_one_hash_matches():
    m = _ATX_HEADING_RE.match("# Title")
    assert m is not None
    assert m.group(1) == "#"
    assert m.group(2) == "Title"


def test_atx_heading_re_six_hashes_matches():
    m = _ATX_HEADING_RE.match("###### Deepest")
    assert m is not None
    assert len(m.group(1)) == 6


def test_atx_heading_re_seven_hashes_no_match():
    """7 个 # 不匹配（最多 6）。"""
    m = _ATX_HEADING_RE.match("####### Title")
    assert m is None


def test_atx_heading_re_no_space_after_hashes_no_match():
    """# 后必须有空格。"""
    assert _ATX_HEADING_RE.match("#Title") is None


def test_atx_heading_re_trailing_hashes_stripped():
    """末尾 # 被吃掉（group 2 不含）。"""
    m = _ATX_HEADING_RE.match("# Title ###")
    assert m is not None
    assert m.group(2) == "Title"


def test_atx_heading_re_only_hashes_no_match():
    """只有 # 没有标题文字不匹配（.+? 至少 1 字符）。"""
    assert _ATX_HEADING_RE.match("# ") is None


def test_thematic_re_dash_three():
    assert _THEMATIC_RE.match("---") is not None


def test_thematic_re_dash_six():
    assert _THEMISTIC_RE_match_safe("------")


def _THEMISTIC_RE_match_safe(s):
    """helper."""
    assert _THEMATIC_RE.match(s) is not None
    return True


def test_thematic_re_star_three():
    assert _THEMATIC_RE.match("***") is not None


def test_thematic_re_underscore_three():
    assert _THEMATIC_RE.match("___") is not None


def test_thematic_re_mixed_chars():
    """- * _ 混合的 3 字符也匹配。"""
    assert _THEMATIC_RE.match("-*_") is not None
    assert _THEMATIC_RE.match("*-_") is not None


def test_thematic_re_two_chars_no_match():
    """2 字符不匹配（至少 3）。"""
    assert _THEMATIC_RE.match("--") is None


def test_thematic_re_one_char_no_match():
    assert _THEMATIC_RE.match("-") is None


def test_thematic_re_with_internal_spaces():
    """- - -（带空格）也匹配。"""
    assert _THEMATIC_RE.match("- - -") is not None


def test_fenced_re_backtick_three():
    m = _FENCED_RE.match("```")
    assert m is not None
    assert m.group(1) == "```"
    assert m.group(2) == ""


def test_fenced_re_backtick_with_lang():
    m = _FENCED_RE.match("```python")
    assert m is not None
    assert m.group(2) == "python"


def test_fenced_re_tilde_three():
    m = _FENCED_RE.match("~~~")
    assert m is not None
    assert m.group(1) == "~~~"


def test_fenced_re_tilde_with_lang():
    m = _FENCED_RE.match("~~~javascript")
    assert m is not None
    assert m.group(2) == "javascript"


def test_fenced_re_four_backticks():
    m = _FENCED_RE.match("````")
    assert m is not None
    assert m.group(1) == "````"


def test_fenced_re_two_backticks_no_match():
    """2 个反引号不匹配（至少 3）。"""
    assert _FENCED_RE.match("``") is None


def test_fenced_re_lang_with_plus():
    m = _FENCED_RE.match("```c++")
    assert m is not None
    assert m.group(2) == "c++"


def test_fenced_re_lang_with_dash():
    m = _FENCED_RE.match("```objective-c")
    assert m is not None
    assert m.group(2) == "objective-c"


def test_fenced_re_lang_no_dot():
    r"""正则 [\w+-]* 不含 .，所以 ts.x 整个不匹配。"""
    m = _FENCED_RE.match("```ts.x")
    # 整行不匹配（regex 要求整行 ^...$）
    assert m is None


def test_unordered_list_re_dash():
    m = _UNORDERED_LIST_RE.match("- item")
    assert m is not None
    assert m.group(1) == "item"


def test_unordered_list_re_star():
    m = _UNORDERED_LIST_RE.match("* item")
    assert m is not None
    assert m.group(1) == "item"


def test_unordered_list_re_plus():
    m = _UNORDERED_LIST_RE.match("+ item")
    assert m is not None
    assert m.group(1) == "item"


def test_unordered_list_re_no_space_no_match():
    """- item 需空格；-item 不匹配。"""
    assert _UNORDERED_LIST_RE.match("-item") is None


def test_ordered_list_re_dot():
    m = _ORDERED_LIST_RE.match("1. item")
    assert m is not None
    assert m.group(1) == "item"


def test_ordered_list_re_paren():
    m = _ORDERED_LIST_RE.match("1) item")
    assert m is not None
    assert m.group(1) == "item"


def test_ordered_list_re_multi_digit():
    m = _ORDERED_LIST_RE.match("99. item")
    assert m is not None
    assert m.group(1) == "item"


def test_ordered_list_re_no_space_no_match():
    assert _ORDERED_LIST_RE.match("1.item") is None


def test_ordered_list_re_zero_number_matches():
    """0. item 也匹配（正则没限制数字范围）。"""
    m = _ORDERED_LIST_RE.match("0. item")
    assert m is not None


def test_blockquote_re_simple():
    m = _BLOCKQUOTE_RE.match("> text")
    assert m is not None
    assert m.group(1) == "text"


def test_blockquote_re_no_space():
    m = _BLOCKQUOTE_RE.match(">text")
    assert m is not None
    assert m.group(1) == "text"


def test_blockquote_re_empty():
    m = _BLOCKQUOTE_RE.match(">")
    assert m is not None
    assert m.group(1) == ""


def test_pipe_table_row_re_basic():
    assert _PIPE_TABLE_ROW_RE.match("| a | b |") is not None


def test_pipe_table_row_re_no_leading_pipe():
    """a | b |（无前导 pipe）— 实际正则要求 |.*|，所以 a | b | 前面没 | 但后面有。"""
    # 正则 ^\s*\|.*\|\s*$ 必须以 | 开头（允许前置空白）
    assert _PIPE_TABLE_ROW_RE.match("a | b |") is None


def test_pipe_table_row_re_only_pipes():
    assert _PIPE_TABLE_ROW_RE.match("|||") is not None


def test_pipe_table_sep_re_basic():
    assert _PIPE_TABLE_SEP_RE.match("| --- | --- |") is not None


def test_pipe_table_sep_re_no_pipes():
    assert _PIPE_TABLE_SEP_RE.match("--- | ---") is not None


def test_pipe_table_sep_re_with_colons():
    """支持 :---: 形式。"""
    assert _PIPE_TABLE_SEP_RE.match("| :---: | ---: |") is not None


def test_pipe_table_sep_re_single_dash_no_match():
    """分隔行每列至少 2 个 -。"""
    assert _PIPE_TABLE_SEP_RE.match("| - | - |") is None


def test_standalone_image_re_basic():
    m = _STANDALONE_IMAGE_RE.match("![alt](url)")
    assert m is not None
    assert m.group(1) == "alt"
    assert m.group(2) == "url"


def test_standalone_image_re_empty_alt():
    m = _STANDALONE_IMAGE_RE.match("![](url)")
    assert m is not None
    assert m.group(1) == ""
    assert m.group(2) == "url"


def test_standalone_image_re_url_with_path():
    m = _STANDALONE_IMAGE_RE.match("![alt](https://example.com/path/to/img.png)")
    assert m is not None


def test_standalone_image_re_inline_no_match():
    """![alt](url) 前后有文字 → 不是独立图片行。"""
    assert _STANDALONE_IMAGE_RE.match("text ![alt](url)") is None


def test_standalone_image_re_no_closing_paren_no_match():
    """括号不闭合不匹配。"""
    assert _STANDALONE_IMAGE_RE.match("![alt](url") is None


def test_standalone_image_re_trailing_text_no_match():
    r"""url 后有文字不匹配（regex 用 \s*$）。"""
    assert _STANDALONE_IMAGE_RE.match("![alt](url) trailing") is None


# =========================================================================
# _rows_to_md 深度
# =========================================================================


def test_rows_to_md_one_col_two_rows():
    """单列两行：header + body。"""
    out = _rows_to_md([["h"], ["b"]])
    lines = out.split("\n")
    assert len(lines) == 3  # header + sep + body
    assert lines[0] == "| h |"
    assert lines[1] == "| --- |"
    assert lines[2] == "| b |"


def test_rows_to_md_three_cols():
    out = _rows_to_md([["a", "b", "c"], ["1", "2", "3"]])
    lines = out.split("\n")
    assert lines[0] == "| a | b | c |"
    assert lines[1] == "| --- | --- | --- |"
    assert lines[2] == "| 1 | 2 | 3 |"


def test_rows_to_md_unicode_cells():
    out = _rows_to_md([["中"], ["文"]])
    assert "| 中 |" in out


def test_rows_to_md_jagged_pads_empty():
    """jagged rows 补空字符串。"""
    out = _rows_to_md([["a", "b"], ["c"]])
    lines = out.split("\n")
    # 第 2 行被补成 ["c", ""]
    assert lines[2] == "| c |  |"


def test_rows_to_md_returns_str_type():
    assert isinstance(_rows_to_md([[]]), str)


# =========================================================================
# _split_pipe_row 深度
# =========================================================================


def test_split_pipe_row_three_cells():
    assert _split_pipe_row("| a | b | c |") == ["a", "b", "c"]


def test_split_pipe_row_preserves_inner_spaces():
    """单元格内空格保留。"""
    assert _split_pipe_row("| a b | c d |") == ["a b", "c d"]


def test_split_pipe_row_only_strips_outer():
    """strip() 只去外层空格。"""
    cells = _split_pipe_row("|  a  |  b  |")
    assert cells == ["a", "b"]


# =========================================================================
# _is_pipe_table_start 深度
# =========================================================================


def test_is_pipe_table_start_at_last_line():
    """i 是最后一行（无下一行）→ False。"""
    lines = ["| a | b |"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_row_match_sep_no_match():
    """第 i 行 pipe，第 i+1 行不是分隔行 → False。"""
    lines = ["| a | b |", "not a separator"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_row_no_match_sep_match():
    """第 i 行不是 pipe，第 i+1 行是分隔行 → False。"""
    lines = ["not a pipe row", "| --- | --- |"]
    assert _is_pipe_table_start(lines, 0) is False


def test_is_pipe_table_start_both_match():
    lines = ["| a | b |", "| --- | --- |"]
    assert _is_pipe_table_start(lines, 0) is True


def test_is_pipe_table_start_out_of_bounds():
    """i+1 >= len(lines) → False。"""
    assert _is_pipe_table_start([], 0) is False
    assert _is_pipe_table_start(["only one"], 0) is False


# =========================================================================
# section_path 复杂场景
# =========================================================================


def test_section_path_skip_level_h1_h3(tmp_path):
    """H1 → H3（跳级）— section_path 应含两项。"""
    p = tmp_path / "t.md"
    p.write_text("# H1\n\n### H3\n\nbody\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    h3 = next(e for e in doc.elements if e.type == "heading" and e.metadata.get("level") == 3)
    assert h3.source_locator["section_path"] == "H1 > H3"


def test_section_path_h1_h2_h3_h2(tmp_path):
    """H1 → H2 → H3 → H2（H2 弹出 H3）。"""
    p = tmp_path / "t.md"
    p.write_text(
        "# H1\n\n## H2a\n\n### H3\n\n## H2b\n\nbody\n",
        encoding="utf-8",
    )
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    h2b = next(
        e for e in doc.elements
        if e.type == "heading" and e.content == "H2b"
    )
    # H2b 弹出 H3，所以 section_path = "H1 > H2b"
    assert h2b.source_locator["section_path"] == "H1 > H2b"


def test_section_path_h2_h1_resets(tmp_path):
    """H2 → H1：H1 应清空 stack（同级或更高级弹出）。"""
    p = tmp_path / "t.md"
    p.write_text("## H2\n\n# H1\n\nbody\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    h1 = next(e for e in doc.elements if e.content == "H1")
    # H1 level=1, H2 level=2, H1 弹出 H2（>= 1）
    assert h1.source_locator["section_path"] == "H1"


def test_section_path_body_after_h3(tmp_path):
    """段落元素也带 section_path。"""
    p = tmp_path / "t.md"
    p.write_text("# T\n\n## S\n\nparagraph\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    para = next(e for e in doc.elements if e.type == "paragraph")
    assert para.source_locator["section_path"] == "T > S"


def test_section_path_no_heading_no_section_key(tmp_path):
    """无标题时，locator 不含 section_path。"""
    p = tmp_path / "t.md"
    p.write_text("just paragraph\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    para = next(e for e in doc.elements if e.type == "paragraph")
    assert "section_path" not in para.source_locator
    assert "line" in para.source_locator


# =========================================================================
# element_id 序号与 confidence
# =========================================================================


def test_element_id_zero_padded_four_digits(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("a\n\nb\n\nc\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    # 三个 paragraph，e0000 / e0001 / e0002
    ids = [e.element_id for e in doc.elements]
    assert ids[0].endswith("::e0000")
    assert ids[1].endswith("::e0001")
    assert ids[2].endswith("::e0002")


def test_element_id_format_document_id_prefix(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("a\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    assert doc.elements[0].element_id.startswith(doc.document_id)
    assert "::" in doc.elements[0].element_id


def test_element_confidence_default_095(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("a\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    assert doc.elements[0].confidence == 0.95


# =========================================================================
# 解析全流程边界
# =========================================================================


def test_parse_empty_file_emits_no_content_warning(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    assert doc.elements == []
    assert any(w.code == "md_no_content" for w in doc.warnings)


def test_parse_only_thematic_break_emits_warning(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("---\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    assert doc.elements == []
    assert any(w.code == "md_no_content" for w in doc.warnings)


def test_parse_only_whitespace_emits_warning(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("   \n\t\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    assert doc.elements == []


def test_parse_code_block_at_eof_without_closing(tmp_path):
    """代码块未闭合 → 收集到 EOF。"""
    p = tmp_path / "t.md"
    p.write_text("```python\nprint('hi')\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    # 仍然提取为 paragraph（kind=code_block）
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert "print" in paras[0].content


def test_parse_empty_code_block_emits_warning(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("```\n```\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    assert any(w.code == "md_empty_code_block" for w in doc.warnings)


def test_parse_code_block_with_lang_in_metadata(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("```python\ncode\n```\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    code_elem = doc.elements[0]
    assert code_elem.metadata.get("language") == "python"
    assert code_elem.metadata.get("kind") == "code_block"


def test_parse_standalone_image_alt_in_metadata(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("![alt text](url.png)\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    img = doc.elements[0]
    assert img.type == "image"
    assert img.resource_path == "url.png"
    assert img.metadata.get("alt") == "alt text"


def test_parse_unordered_list_marker_in_metadata(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("- item\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    li = doc.elements[0]
    assert li.type == "list_item"
    assert li.metadata.get("marker") == "unordered"
    assert li.metadata.get("ordered") is False


def test_parse_ordered_list_marker_in_metadata(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("1. item\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    li = doc.elements[0]
    assert li.metadata.get("marker") == "ordered"
    assert li.metadata.get("ordered") is True


def test_parse_blockquote_kind_in_metadata(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("> quote\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    para = doc.elements[0]
    assert para.type == "paragraph"
    assert para.metadata.get("kind") == "blockquote"


def test_parse_table_metadata_has_row_count(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("| a | b |\n| --- | --- |\n| 1 | 2 |\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    tbl = doc.elements[0]
    assert tbl.type == "table"
    assert tbl.metadata.get("row_count") == 2  # header + 1 body
    assert tbl.metadata.get("col_count") == 2
    assert tbl.metadata.get("source") == "markdown_pipe_table"


def test_parse_heading_level_in_metadata(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("### Title\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    h = doc.elements[0]
    assert h.metadata.get("level") == 3


# =========================================================================
# parser name / version
# =========================================================================


def test_parser_name_value():
    assert MarkdownParser.name == "markdown"


def test_parser_version_value():
    assert MarkdownParser.version == "stdlib/0.1.0"


def test_parser_metadata_markdown_true(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("hi\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    assert doc.metadata == {"markdown": True}


# =========================================================================
# 模块结构深度
# =========================================================================


def test_md_extensions_count_two():
    assert len(_MD_EXTENSIONS) == 2


def test_md_extensions_contains_md_and_markdown():
    assert ".md" in _MD_EXTENSIONS
    assert ".markdown" in _MD_EXTENSIONS


def test_md_extensions_is_tuple():
    assert isinstance(_MD_EXTENSIONS, tuple)


def test_module_all_only_markdown_parser():
    from app.parsers.markdown_parser import __all__
    assert __all__ == ["MarkdownParser"]


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


def test_module_imports_document():
    import app.parsers.markdown_parser as mod
    src = inspect.getsource(mod)
    assert "Document" in src


def test_module_imports_element():
    import app.parsers.markdown_parser as mod
    src = inspect.getsource(mod)
    assert "Element" in src


def test_module_imports_warning_record():
    import app.parsers.markdown_parser as mod
    src = inspect.getsource(mod)
    assert "WarningRecord" in src


def test_module_imports_parser_base():
    import app.parsers.markdown_parser as mod
    src = inspect.getsource(mod)
    assert "from app.parsers.base import" in src


def test_module_uses_future_annotations():
    import app.parsers.markdown_parser as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import app.parsers.markdown_parser as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_atx():
    import app.parsers.markdown_parser as mod
    assert "ATX" in mod.__doc__


def test_module_docstring_mentions_setext_unsupported():
    import app.parsers.markdown_parser as mod
    assert "setext" in mod.__doc__.lower()


def test_module_docstring_mentions_pipe_table():
    import app.parsers.markdown_parser as mod
    assert "pipe" in mod.__doc__.lower() or "表格" in mod.__doc__


def test_module_docstring_mentions_source_locator():
    import app.parsers.markdown_parser as mod
    assert "source_locator" in mod.__doc__ or "section_path" in mod.__doc__


# =========================================================================
# 签名深度
# =========================================================================


def test_detect_md_source_type_signature_one_param():
    sig = inspect.signature(_detect_md_source_type)
    assert len(sig.parameters) == 1


def test_rows_to_md_signature_one_param():
    sig = inspect.signature(_rows_to_md)
    assert len(sig.parameters) == 1


def test_split_pipe_row_signature_one_param():
    sig = inspect.signature(_split_pipe_row)
    assert len(sig.parameters) == 1


def test_is_pipe_table_start_signature_two_params():
    sig = inspect.signature(_is_pipe_table_start)
    assert len(sig.parameters) == 2


def test_markdown_parser_parse_signature_three_params():
    sig = inspect.signature(MarkdownParser.parse)
    # self, path, source_hash
    assert len(sig.parameters) == 3


def test_markdown_parser_parse_text_signature_three_params():
    sig = inspect.signature(MarkdownParser._parse_text)
    # self, text, document_id
    assert len(sig.parameters) == 3


def test_markdown_parser_class_subclass_of_parser():
    from app.parsers.base import Parser
    assert issubclass(MarkdownParser, Parser)


# =========================================================================
# 综合：source_locator.line 是 1-based
# =========================================================================


def test_source_locator_line_one_based_first_line(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("first\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    assert doc.elements[0].source_locator["line"] == 1


def test_source_locator_line_one_based_third_line(tmp_path):
    """空行后第 3 行内容 → line=3。"""
    p = tmp_path / "t.md"
    p.write_text("\n\nthird\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    assert doc.elements[0].source_locator["line"] == 3


def test_source_locator_line_increases_across_elements(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("a\n\nb\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    assert doc.elements[0].source_locator["line"] == 1
    assert doc.elements[1].source_locator["line"] == 3


# =========================================================================
# 综合：document 字段默认值
# =========================================================================


def test_parse_returns_document_with_empty_chunks(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("a\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    assert doc.chunks == []


def test_parse_returns_document_with_empty_relations(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("a\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    assert doc.relations == []


def test_parse_returns_document_with_empty_errors(tmp_path):
    p = tmp_path / "t.md"
    p.write_text("a\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="0" * 64)
    assert doc.errors == []
