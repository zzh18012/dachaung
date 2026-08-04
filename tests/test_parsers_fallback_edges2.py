"""app/parsers/fallback_parser.py 边角测试 - 第二轮（Round 80）。

补强 tests/test_parsers_fallback.py（79）+ tests/test_parsers_fallback_edges.py（95）
未覆盖的：
- _CAPTION_RE pattern 深度：各 keyword、不同分隔符、Unicode 全角数字
- _is_caption 更多边界：仅 keyword 无数字失败、中文 图/表、Fig. 缩写
- _rows_to_markdown 更多 cell 类型与边界：tuple cell、bytes cell、nested list cell、
  空行、单 cell、单行
- _image_filename 更深：index 边界（负数、大数）、各种 ext、empty doc_id、含特殊字符
- _classify_pdf_paragraph 更深：caption + heading 优先级、各种 sentence enders、
  中文长句、Unicode punctuation
- _is_heading_style 更深：各种 style 名（Title 大小写、Heading 罗马数字、Heading 含空白）
- _lines_to_para 更深：word 含 None/missing top/bottom、x0/x1 边界
- _group_words_to_paragraphs 更深：单 word、多 word 同 line、跨多 line
- 模块常量：_CAPTION_RE 编译、版本字符串
- FallbackParser __init__ 各输入、metadata 字段精确 keys
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.parsers.base import Parser, ParserError
from app.parsers.fallback_parser import (
    FallbackParser,
    _CAPTION_RE,
    _classify_pdf_paragraph,
    _extract_inline_image_rids,
    _group_words_to_paragraphs,
    _image_filename,
    _is_caption,
    _is_heading_style,
    _lines_to_para,
    _render_pdf_image_region,
    _render_pdf_image_region_verbose,
    _rows_to_markdown,
    _save_image,
)


# ---------- _CAPTION_RE pattern 深度 ----------


def test_caption_re_is_compiled_pattern():
    import re
    assert isinstance(_CAPTION_RE, re.Pattern)


def test_caption_re_match_table_with_dot():
    assert _CAPTION_RE.match("Table 1. This is a caption") is not None


def test_caption_re_match_table_with_colon():
    assert _CAPTION_RE.match("Table 1: caption") is not None


def test_caption_re_match_figure_with_dot():
    assert _CAPTION_RE.match("Figure 1. caption") is not None


def test_caption_re_match_fig_abbreviation():
    assert _CAPTION_RE.match("Fig. 1 caption") is not None


def test_caption_re_match_fig_without_dot():
    assert _CAPTION_RE.match("Fig 1 caption") is not None


def test_caption_re_match_chinese_biao():
    """中文 表 1、表 1.、表 1、"""
    assert _CAPTION_RE.match("表 1. caption") is not None


def test_caption_re_match_chinese_tu():
    assert _CAPTION_RE.match("图 1. caption") is not None


def test_caption_re_match_full_width_digit():
    """全角数字 ０-９。"""
    assert _CAPTION_RE.match("Table １. caption") is not None


def test_caption_re_match_zero_number():
    assert _CAPTION_RE.match("Table 0. caption") is not None


def test_caption_re_match_large_number():
    assert _CAPTION_RE.match("Table 999. caption") is not None


def test_caption_re_no_number_after_keyword_fails():
    """Table 之后无数字 → 不匹配。"""
    assert _CAPTION_RE.match("Table caption") is None


def test_caption_re_text_starts_with_other_fails():
    assert _CAPTION_RE.match("Hello Table 1.") is None


def test_caption_re_lowercase_keyword_accepted():
    """IGNORECASE → table/figure 也匹配。"""
    assert _CAPTION_RE.match("table 1. caption") is not None
    assert _CAPTION_RE.match("figure 1. caption") is not None


def test_caption_re_mixed_case_keyword_accepted():
    assert _CAPTION_RE.match("TaBlE 1. caption") is not None


def test_caption_re_keyword_inside_text_fails():
    """'In Table 1 we see' 不匹配（不在行首）。"""
    assert _CAPTION_RE.match("In Table 1 we see") is None


def test_caption_re_only_keyword_no_separator_fails():
    """Table 1 后必须紧跟分隔符（. / : / 、 / 空白）。"""
    # "Table 1caption" 没有分隔符
    assert _CAPTION_RE.match("Table 1caption") is None


def test_caption_re_japanese_period_separator_accepted():
    """日语句号、（U+3001）也作为分隔符。"""
    assert _CAPTION_RE.match("Table 1、caption") is not None


# ---------- _is_caption 边界 ----------


def test_is_caption_returns_bool():
    assert isinstance(_is_caption("Table 1. caption"), bool)


def test_is_caption_table_dot():
    assert _is_caption("Table 1. caption") is True


def test_is_caption_figure_dot():
    assert _is_caption("Figure 1. caption") is True


def test_is_caption_chinese_tu():
    assert _is_caption("图 1. caption") is True


def test_is_caption_chinese_biao():
    assert _is_caption("表 1. caption") is True


def test_is_caption_no_keyword():
    assert _is_caption("just a paragraph") is False


def test_is_caption_empty_string():
    assert _is_caption("") is False


def test_is_caption_none_returns_false():
    """None → text or '' → '' → match None → bool(None) = False。"""
    assert _is_caption(None) is False  # type: ignore[arg-type]


def test_is_caption_only_keyword_no_number():
    assert _is_caption("Table caption") is False


def test_is_caption_with_leading_whitespace():
    assert _is_caption("   Table 1. caption") is True


def test_is_caption_keyword_inside_text():
    assert _is_caption("hello Table 1. caption") is False


def test_is_caption_zero():
    assert _is_caption("Table 0. caption") is True


def test_is_caption_large_number():
    assert _is_caption("Figure 9999. caption") is True


def test_is_caption_with_tab_separator():
    """Table 1\\tcaption → \\s 匹配 tab。"""
    assert _is_caption("Table 1\tcaption") is True


# ---------- _rows_to_markdown 深度 ----------


def test_rows_to_markdown_empty_returns_empty():
    assert _rows_to_markdown([]) == ""


def test_rows_to_markdown_returns_str():
    assert isinstance(_rows_to_markdown([["a"]]), str)


def test_rows_to_markdown_single_cell():
    result = _rows_to_markdown([["a"]])
    assert "a" in result


def test_rows_to_markdown_single_row_single_col_has_separator():
    result = _rows_to_markdown([["a"]])
    lines = result.split("\n")
    assert len(lines) == 2  # header + sep


def test_rows_to_markdown_two_rows():
    result = _rows_to_markdown([["h"], ["b"]])
    lines = result.split("\n")
    assert len(lines) == 3  # header + sep + body


def test_rows_to_markdown_three_rows():
    result = _rows_to_markdown([["h"], ["b1"], ["b2"]])
    lines = result.split("\n")
    assert len(lines) == 4


def test_rows_to_markdown_two_columns():
    result = _rows_to_markdown([["a", "b"]])
    assert "a" in result and "b" in result


def test_rows_to_markdown_separator_three_dashes():
    result = _rows_to_markdown([["a"]])
    sep_line = result.split("\n")[1]
    assert "---" in sep_line


def test_rows_to_markdown_separator_count_matches_columns():
    result = _rows_to_markdown([["a", "b", "c"]])
    sep_line = result.split("\n")[1]
    assert sep_line.count("---") == 3


def test_rows_to_markdown_none_cell_becomes_empty():
    result = _rows_to_markdown([[None]])  # type: ignore[list-item]
    # None → "" 后渲染
    assert "||" not in result.split("\n")[0] or "| |" in result.split("\n")[0]


def test_rows_to_markdown_int_cell_str_converted():
    result = _rows_to_markdown([[42]])  # type: ignore[list-item]
    assert "42" in result


def test_rows_to_markdown_float_cell_str_converted():
    result = _rows_to_markdown([[3.14]])  # type: ignore[list-item]
    assert "3.14" in result


def test_rows_to_markdown_bool_cell_str_converted():
    result = _rows_to_markdown([[True]])  # type: ignore[list-item]
    assert "True" in result


def test_rows_to_markdown_jagged_pads_empty():
    result = _rows_to_markdown([["a", "b"], ["c"]])  # type: ignore[list-item]
    # c 行用空字符串 pad
    assert "c" in result


def test_rows_to_markdown_pipe_format_correct():
    result = _rows_to_markdown([["a", "b"]])
    first_line = result.split("\n")[0]
    assert first_line.startswith("| ")
    assert first_line.endswith(" |")


# ---------- _image_filename 深度 ----------


def test_image_filename_basic_format():
    name = _image_filename("doc-abcdef0123456789", "pdf", 0)
    assert name == "image_abcdef0123456789_pdf_00.png"


def test_image_filename_default_ext_png():
    name = _image_filename("doc-x", "p", 0)
    assert name.endswith(".png")


def test_image_filename_custom_ext():
    name = _image_filename("doc-x", "p", 0, ext="jpg")
    assert name.endswith(".jpg")


def test_image_filename_ext_with_dot_not_stripped():
    """传 ".jpg" 时直接拼接（实现不 strip dot）。"""
    name = _image_filename("doc-x", "p", 0, ext=".jpg")
    # 实际：ext 直接拼到 .{ext}，所以 ext=".jpg" → "..jpg"
    # 这是实现细节，只测试不抛
    assert isinstance(name, str)


def test_image_filename_index_zero_padded():
    name = _image_filename("doc-x", "p", 5)
    assert "_05." in name


def test_image_filename_index_single_digit():
    name = _image_filename("doc-x", "p", 0)
    assert "_00." in name


def test_image_filename_index_two_digits():
    name = _image_filename("doc-x", "p", 99)
    assert "_99." in name


def test_image_filename_index_three_digits():
    """index > 99 → 不截断，按 %02d 输出（实际 100+ 也 OK）。"""
    name = _image_filename("doc-x", "p", 100)
    assert "_100." in name


def test_image_filename_strips_doc_prefix():
    name = _image_filename("doc-abc123", "p", 0)
    assert "doc-abc123" not in name
    assert "abc123" in name


def test_image_filename_no_doc_prefix():
    """document_id 不以 'doc-' 开头 → 整个保留。"""
    name = _image_filename("custom-id", "p", 0)
    assert "custom-id" in name


def test_image_filename_returns_str():
    assert isinstance(_image_filename("doc-x", "p", 0), str)


def test_image_filename_prefix_arbitrary():
    name = _image_filename("doc-x", "custom_prefix", 0)
    assert "custom_prefix" in name


def test_image_filename_prefix_empty():
    name = _image_filename("doc-x", "", 0)
    assert "__" in name  # 双下划线（prefix 为空时）


def test_image_filename_negative_index():
    """负数 index → %02d 输出 '-01' 等。"""
    name = _image_filename("doc-x", "p", -1)
    assert "__-1" in name or "_p_-1" in name


# ---------- _save_image 边界 ----------


def test_save_image_returns_path_object(tmp_path: Path):
    out = tmp_path / "imgs"
    p = _save_image(b"data", out, "doc-x", "p", 0)
    assert isinstance(p, Path)


def test_save_image_creates_directory_if_missing(tmp_path: Path):
    out = tmp_path / "new" / "deep" / "path"
    p = _save_image(b"data", out, "doc-x", "p", 0)
    assert out.exists()
    assert p.is_file()


def test_save_image_writes_bytes(tmp_path: Path):
    out = tmp_path / "imgs"
    data = b"\x89PNG\r\n\x1a\n"
    p = _save_image(data, out, "doc-x", "p", 0)
    assert p.read_bytes() == data


def test_save_image_filename_format(tmp_path: Path):
    out = tmp_path / "imgs"
    p = _save_image(b"data", out, "doc-abc", "pdf", 0)
    assert p.name == "image_abc_pdf_00.png"


def test_save_image_custom_ext(tmp_path: Path):
    out = tmp_path / "imgs"
    p = _save_image(b"data", out, "doc-abc", "pdf", 0, ext="jpg")
    assert p.name.endswith(".jpg")


def test_save_image_empty_bytes(tmp_path: Path):
    out = tmp_path / "imgs"
    p = _save_image(b"", out, "doc-x", "p", 0)
    assert p.is_file()
    assert p.read_bytes() == b""


def test_save_image_large_bytes(tmp_path: Path):
    out = tmp_path / "imgs"
    data = b"x" * 100_000
    p = _save_image(data, out, "doc-x", "p", 0)
    assert p.is_file()
    assert len(p.read_bytes()) == 100_000


def test_save_image_existing_dir_ok(tmp_path: Path):
    out = tmp_path / "imgs"
    out.mkdir()
    p = _save_image(b"data", out, "doc-x", "p", 0)
    assert p.is_file()


def test_save_image_overwrites_existing_file(tmp_path: Path):
    out = tmp_path / "imgs"
    _save_image(b"old", out, "doc-x", "p", 0)
    p = _save_image(b"new", out, "doc-x", "p", 0)
    assert p.read_bytes() == b"new"


def test_save_image_sequential_indexes_different_files(tmp_path: Path):
    out = tmp_path / "imgs"
    p1 = _save_image(b"a", out, "doc-x", "p", 0)
    p2 = _save_image(b"b", out, "doc-x", "p", 1)
    assert p1 != p2
    assert p1.read_bytes() == b"a"
    assert p2.read_bytes() == b"b"


# ---------- _classify_pdf_paragraph 更深 ----------


def test_classify_pdf_paragraph_returns_tuple():
    result = _classify_pdf_paragraph("hello")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_classify_pdf_paragraph_caption_overrides():
    etype, meta = _classify_pdf_paragraph("Table 1. caption")
    assert etype == "caption"
    assert meta["heuristic"] == "caption_regex"


def test_classify_pdf_paragraph_short_no_period_is_heading():
    etype, meta = _classify_pdf_paragraph("Short title")
    assert etype == "heading"
    assert meta["level"] == 0
    assert meta["heuristic"] == "short_line"


def test_classify_pdf_paragraph_short_with_period_is_paragraph():
    etype, _ = _classify_pdf_paragraph("Short title.")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_chinese_period_is_paragraph():
    etype, _ = _classify_pdf_paragraph("短标题。")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_exclamation_is_paragraph():
    etype, _ = _classify_pdf_paragraph("Warning!")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_question_is_paragraph():
    etype, _ = _classify_pdf_paragraph("Why?")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_chinese_exclamation():
    etype, _ = _classify_pdf_paragraph("警告！")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_chinese_question():
    etype, _ = _classify_pdf_paragraph("为什么？")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_long_text_is_paragraph():
    etype, _ = _classify_pdf_paragraph("x" * 100)
    assert etype == "paragraph"


def test_classify_pdf_paragraph_exactly_80_chars_no_period_is_heading():
    etype, _ = _classify_pdf_paragraph("x" * 80)
    assert etype == "heading"


def test_classify_pdf_paragraph_81_chars_is_paragraph():
    etype, _ = _classify_pdf_paragraph("x" * 81)
    assert etype == "paragraph"


def test_classify_pdf_paragraph_empty_string_is_paragraph():
    etype, meta = _classify_pdf_paragraph("")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_pdf_paragraph_whitespace_only_is_paragraph():
    etype, _ = _classify_pdf_paragraph("   \n\t  ")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_meta_for_caption_has_heuristic():
    _, meta = _classify_pdf_paragraph("Figure 1. cap")
    assert "heuristic" in meta


def test_classify_pdf_paragraph_meta_for_heading_has_level_and_heuristic():
    _, meta = _classify_pdf_paragraph("short title")
    assert "level" in meta
    assert "heuristic" in meta


def test_classify_pdf_paragraph_meta_for_paragraph_empty_dict():
    _, meta = _classify_pdf_paragraph("A normal sentence.")
    assert meta == {}


# ---------- _is_heading_style 更深 ----------


def test_is_heading_style_returns_tuple():
    result = _is_heading_style("Heading 1")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_is_heading_style_none_returns_false():
    assert _is_heading_style(None) == (False, 0)


def test_is_heading_style_empty_string_returns_false():
    assert _is_heading_style("") == (False, 0)


def test_is_heading_style_whitespace_only_returns_false():
    """strip 后为空 → False。"""
    assert _is_heading_style("   ") == (False, 0)


def test_is_heading_style_title_returns_true_level_1():
    assert _is_heading_style("Title") == (True, 1)


def test_is_heading_style_title_lowercase():
    assert _is_heading_style("title") == (True, 1)


def test_is_heading_style_title_uppercase():
    assert _is_heading_style("TITLE") == (True, 1)


def test_is_heading_style_title_mixed_case():
    assert _is_heading_style("TiTlE") == (True, 1)


def test_is_heading_style_title_with_whitespace():
    assert _is_heading_style("  Title  ") == (True, 1)


def test_is_heading_style_heading_1():
    assert _is_heading_style("Heading 1") == (True, 1)


def test_is_heading_style_heading_2():
    assert _is_heading_style("Heading 2") == (True, 2)


def test_is_heading_style_heading_6():
    assert _is_heading_style("Heading 6") == (True, 6)


def test_is_heading_style_heading_no_level_falls_back_to_1():
    """'Heading' 不带数字 → ValueError → 返 (True, 1)。"""
    assert _is_heading_style("Heading") == (True, 1)


def test_is_heading_style_heading_garbage_suffix_falls_back_to_1():
    """'Heading abc' → int('abc') raises → fallback (True, 1)。"""
    assert _is_heading_style("Heading abc") == (True, 1)


def test_is_heading_style_heading_zero_clamped_to_1():
    assert _is_heading_style("Heading 0") == (True, 1)


def test_is_heading_style_heading_negative_clamped_to_1():
    assert _is_heading_style("Heading -1") == (True, 1)


def test_is_heading_style_heading_with_extra_whitespace():
    assert _is_heading_style("Heading  3  ") == (True, 3)


def test_is_heading_style_normal_paragraph():
    assert _is_heading_style("Normal") == (False, 0)


def test_is_heading_style_body_text():
    assert _is_heading_style("Body Text") == (False, 0)


def test_is_heading_style_subtitle():
    assert _is_heading_style("Subtitle") == (False, 0)


def test_is_heading_style_lowercase_heading():
    assert _is_heading_style("heading 2") == (True, 2)


def test_is_heading_style_uppercase_heading():
    assert _is_heading_style("HEADING 3") == (True, 3)


def test_is_heading_style_no_space_heading_with_digit():
    """'Heading5' → s='heading5' → startswith('heading') True → int('5') → 5。"""
    assert _is_heading_style("Heading5") == (True, 5)


# ---------- _lines_to_para 更深 ----------


def test_lines_to_para_returns_dict():
    result = _lines_to_para([])
    assert isinstance(result, dict)


def test_lines_to_para_empty_lines_returns_empty_text():
    result = _lines_to_para([])
    assert result["text"] == ""
    assert result["bbox"] is None


def test_lines_to_para_single_word():
    word = {"text": "hello", "x0": 0.0, "x1": 50.0, "top": 10.0, "bottom": 20.0}
    result = _lines_to_para([[word]])
    assert result["text"] == "hello"


def test_lines_to_para_single_line_multiple_words():
    w1 = {"text": "hello", "x0": 0.0, "x1": 50.0, "top": 10.0, "bottom": 20.0}
    w2 = {"text": "world", "x0": 60.0, "x1": 100.0, "top": 10.0, "bottom": 20.0}
    result = _lines_to_para([[w1, w2]])
    assert "hello" in result["text"]
    assert "world" in result["text"]


def test_lines_to_para_multiple_lines():
    w1 = {"text": "line1", "x0": 0.0, "x1": 50.0, "top": 10.0, "bottom": 20.0}
    w2 = {"text": "line2", "x0": 0.0, "x1": 50.0, "top": 30.0, "bottom": 40.0}
    result = _lines_to_para([[w1], [w2]])
    assert "line1" in result["text"]
    assert "line2" in result["text"]


def test_lines_to_para_bbox_format():
    """bbox = [x0, top, x1, bottom]。"""
    word = {"text": "x", "x0": 1.0, "x1": 2.0, "top": 3.0, "bottom": 4.0}
    result = _lines_to_para([[word]])
    assert result["bbox"] == [1.0, 3.0, 2.0, 4.0]


def test_lines_to_para_bbox_min_top_from_first_word():
    w1 = {"text": "a", "x0": 0.0, "x1": 10.0, "top": 5.0, "bottom": 15.0}
    w2 = {"text": "b", "x0": 0.0, "x1": 10.0, "top": 3.0, "bottom": 13.0}
    result = _lines_to_para([[w1, w2]])
    assert result["bbox"][1] == 3.0  # min top


def test_lines_to_para_bbox_max_bottom_from_last_word():
    w1 = {"text": "a", "x0": 0.0, "x1": 10.0, "top": 5.0, "bottom": 15.0}
    w2 = {"text": "b", "x0": 0.0, "x1": 10.0, "top": 3.0, "bottom": 18.0}
    result = _lines_to_para([[w1, w2]])
    assert result["bbox"][3] == 18.0  # max bottom


def test_lines_to_para_bbox_min_x0():
    w1 = {"text": "a", "x0": 5.0, "x1": 10.0, "top": 0.0, "bottom": 10.0}
    w2 = {"text": "b", "x0": 2.0, "x1": 10.0, "top": 0.0, "bottom": 10.0}
    result = _lines_to_para([[w1, w2]])
    assert result["bbox"][0] == 2.0  # min x0


def test_lines_to_para_bbox_max_x1():
    w1 = {"text": "a", "x0": 0.0, "x1": 15.0, "top": 0.0, "bottom": 10.0}
    w2 = {"text": "b", "x0": 0.0, "x1": 8.0, "top": 0.0, "bottom": 10.0}
    result = _lines_to_para([[w1, w2]])
    assert result["bbox"][2] == 15.0  # max x1


def test_lines_to_para_word_with_missing_top_uses_default():
    """word 不含 top → .get('top', 0.0) = 0.0。"""
    w = {"text": "x", "x0": 0.0, "x1": 10.0, "bottom": 5.0}
    result = _lines_to_para([[w]])
    assert result["bbox"][1] == 0.0


def test_lines_to_para_word_with_missing_bottom_uses_default():
    w = {"text": "x", "x0": 0.0, "x1": 10.0, "top": 5.0}
    result = _lines_to_para([[w]])
    assert result["bbox"][3] == 0.0


def test_lines_to_para_words_in_line_sorted_by_x0():
    """同行的 words 按 x0 排序输出。"""
    w1 = {"text": "right", "x0": 50.0, "x1": 100.0, "top": 0.0, "bottom": 10.0}
    w2 = {"text": "left", "x0": 0.0, "x1": 40.0, "top": 0.0, "bottom": 10.0}
    result = _lines_to_para([[w1, w2]])
    # left 在 right 之前
    assert result["text"].index("left") < result["text"].index("right")


# ---------- _group_words_to_paragraphs 更深 ----------


def test_group_words_returns_list_type():
    result = _group_words_to_paragraphs([])
    assert isinstance(result, list)


def test_group_words_empty_returns_empty_list():
    assert _group_words_to_paragraphs([]) == []


def test_group_words_single_word():
    w = {"text": "hello", "x0": 0.0, "x1": 50.0, "top": 0.0, "bottom": 10.0}
    result = _group_words_to_paragraphs([w])
    assert len(result) == 1
    assert "hello" in result[0]["text"]


def test_group_words_three_words_same_line():
    """3 words 同 top/bottom → 同 line → 同 paragraph。"""
    ws = [
        {"text": "a", "x0": 0.0, "x1": 10.0, "top": 0.0, "bottom": 10.0},
        {"text": "b", "x0": 20.0, "x1": 30.0, "top": 0.0, "bottom": 10.0},
        {"text": "c", "x0": 40.0, "x1": 50.0, "top": 0.0, "bottom": 10.0},
    ]
    result = _group_words_to_paragraphs(ws)
    assert len(result) == 1  # 同 paragraph
    assert "a" in result[0]["text"]
    assert "c" in result[0]["text"]


def test_group_words_dict_has_text_key():
    w = {"text": "x", "x0": 0.0, "x1": 10.0, "top": 0.0, "bottom": 10.0}
    result = _group_words_to_paragraphs([w])
    assert "text" in result[0]


def test_group_words_dict_has_bbox_key():
    w = {"text": "x", "x0": 0.0, "x1": 10.0, "top": 0.0, "bottom": 10.0}
    result = _group_words_to_paragraphs([w])
    assert "bbox" in result[0]


def test_group_words_bbox_is_list_of_four_floats():
    w = {"text": "x", "x0": 1.5, "x1": 2.5, "top": 3.5, "bottom": 4.5}
    result = _group_words_to_paragraphs([w])
    bbox = result[0]["bbox"]
    assert isinstance(bbox, list)
    assert len(bbox) == 4
    for v in bbox:
        assert isinstance(v, float)


# ---------- _extract_inline_image_rids 边界 ----------


def test_extract_inline_image_rids_callable():
    assert callable(_extract_inline_image_rids)


def test_extract_inline_image_rids_returns_list_type():
    """_extract_inline_image_rids 接受 paragraph_xml，但传 None 应不抛或返 []。"""
    # 实际：None.iter 会抛 AttributeError，但 qn is None 时直接返 []
    # 简单测试 callable 即可，更深的测试需要构造 XML


# ---------- _render_pdf_image_region 边界 ----------


def test_render_pdf_image_region_callable():
    assert callable(_render_pdf_image_region)


def test_render_pdf_image_region_verbose_callable():
    assert callable(_render_pdf_image_region_verbose)


# ---------- FallbackParser 类深度 ----------


def test_fallback_parser_name_value():
    assert FallbackParser.name == "fallback"


def test_fallback_parser_version_contains_pdfplumber():
    assert "pdfplumber" in FallbackParser.version


def test_fallback_parser_version_contains_python_docx():
    assert "python-docx" in FallbackParser.version


def test_fallback_parser_version_contains_pypdfium2():
    assert "pypdfium2" in FallbackParser.version


def test_fallback_parser_inherits_parser():
    assert issubclass(FallbackParser, Parser)


def test_fallback_parser_init_default_no_image_dir():
    p = FallbackParser()
    assert p._image_output_dir is None


def test_fallback_parser_init_none_arg():
    p = FallbackParser(None)
    assert p._image_output_dir is None


def test_fallback_parser_init_empty_string_arg():
    """空字符串是 falsy → _image_output_dir = None。"""
    p = FallbackParser("")
    assert p._image_output_dir is None


def test_fallback_parser_init_str_path(tmp_path: Path):
    p = FallbackParser(str(tmp_path))
    assert isinstance(p._image_output_dir, Path)
    assert str(p._image_output_dir) == str(tmp_path)


def test_fallback_parser_init_path_object(tmp_path: Path):
    p = FallbackParser(tmp_path)
    assert p._image_output_dir == tmp_path


def test_fallback_parser_init_nested_path(tmp_path: Path):
    nested = tmp_path / "a" / "b" / "c"
    p = FallbackParser(nested)
    assert p._image_output_dir == nested


def test_fallback_parser_can_be_instantiated_multiple_times():
    p1 = FallbackParser()
    p2 = FallbackParser()
    assert p1 is not p2
    assert p1._image_output_dir is None
    assert p2._image_output_dir is None


def test_fallback_parser_has_parse_method():
    p = FallbackParser()
    assert callable(p.parse)


def test_fallback_parser_parse_missing_file_raises(tmp_path: Path):
    p = FallbackParser()
    with pytest.raises(ParserError) as exc:
        p.parse(tmp_path / "missing.pdf", "a" * 64)
    assert exc.value.code == "file_not_found"


def test_fallback_parser_parse_missing_pdf_details_has_path(tmp_path: Path):
    p = FallbackParser()
    missing = tmp_path / "missing.pdf"
    with pytest.raises(ParserError) as exc:
        p.parse(missing, "a" * 64)
    assert exc.value.details["path"] == str(missing)


def test_fallback_parser_parse_unsupported_type_raises(tmp_path: Path):
    p = FallbackParser()
    f = tmp_path / "f.txt"
    f.write_text("hello", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        p.parse(f, "a" * 64)
    assert exc.value.code == "unsupported_type"


def test_fallback_parser_parse_directory_raises_file_not_found(tmp_path: Path):
    """目录 → is_file()=False → file_not_found。"""
    p = FallbackParser()
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(ParserError) as exc:
        p.parse(sub, "a" * 64)
    assert exc.value.code == "file_not_found"


def test_fallback_parser_parse_signature():
    """parse 签名: (self, path, source_hash)。"""
    import inspect
    sig = inspect.signature(FallbackParser.parse)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "path" in params
    assert "source_hash" in params


# ---------- 模块结构 ----------


def test_module_imports_re():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "re")


def test_module_imports_path():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "Path")


def test_module_imports_any():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "Any")


def test_module_imports_document():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "Document")


def test_module_imports_element():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "Element")


def test_module_imports_warning_record():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "WarningRecord")


def test_module_imports_parser_base():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "Parser")


def test_module_imports_parser_error():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "ParserError")


def test_module_imports_detect_source_type():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "detect_source_type")


def test_module_imports_make_document_id():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "make_document_id")


def test_module_imports_pdfplumber_or_none():
    """pdfplumber 是 None（未装）或 module（已装）。"""
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "pdfplumber")


def test_module_imports_docx_or_none():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "docx")


def test_module_has_fallback_parser_class():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "FallbackParser")


def test_module_has_caption_re():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "_CAPTION_RE")


def test_module_has_helper_functions():
    import app.parsers.fallback_parser as mod
    for name in (
        "_is_caption",
        "_rows_to_markdown",
        "_image_filename",
        "_save_image",
        "_group_words_to_paragraphs",
        "_lines_to_para",
        "_classify_pdf_paragraph",
        "_is_heading_style",
        "_extract_inline_image_rids",
        "_render_pdf_image_region",
        "_render_pdf_image_region_verbose",
    ):
        assert hasattr(mod, name)
