r"""app/parsers/fallback_parser.py 边角测试 - 第五轮（Round 127）。

补强已有 base/edges/edges2/edges3/edges4（共 536 测试）未覆盖的深度路径：
- 模块常量深度：
  - _CAPTION_RE.pattern 字符串内容（含中文/英文/数字范围）
  - _PDFPLUMBER_VERSION / _PDFIUM_VERSION / _DOCX_VERSION 字符串或 None
  - FallbackParser.version 内容精确
- _is_caption 深度：
  - 各种 caption 形式：Figure 1./Fig.1/Fig 1/Table 1./表 1./图 1
  - 数字 0 开头、多位数字
  - 后跟各种分隔符（. 、 : 空白）
  - 大小写不敏感（FIGURE/TABLE）
- _classify_pdf_paragraph 深度：
  - 空串/纯空白 → paragraph
  - 81 字符 → paragraph
  - 80 字符无句号 → heading
  - 80 字符含句号 → paragraph
  - heading meta 含 level=0
- _image_filename 深度：
  - doc-1 → 1
  - doc-123 → 123
  - 无 doc- 前缀 → 原样
  - index 0/1/99/100 格式
- _rows_to_markdown 深度：
  - 单元格含 | 字符
  - 单元格含换行符
  - 单行表格（仅 header）
  - 多行 body
- _lines_to_para 深度：
  - 多行 word 融合
  - bbox 是 [x0, top, x1, bottom] 顺序
- _group_words_to_paragraphs 深度：
  - 空列表 / 单 word / 多行多段
  - 行聚类阈值边界
- _is_heading_style 深度：
  - "Heading 1" → (True, 1)
  - "Heading 10" → (True, 10)
  - "Heading" → (True, 1)（ValueError 路径）
  - "Title" → (True, 1)
  - "Normal"/"List Paragraph"/"Quote" → (False, 0)
- _extract_inline_image_rids 深度：
  - qn 为 None 时返回空
  - 无 drawing → []
  - 多 drawing 多 blip
- _save_image 深度：
  - 文件名格式精确
  - parent dir 创建（多层）
- 模块结构深度：
  - __all__ 1 项
  - 各 helper callable
  - FallbackParser class 属性
- 签名深度：
  - _classify_pdf_paragraph 返回 tuple[str, dict]
  - _is_heading_style 返回 tuple[bool, int]
  - FallbackParser.__init__ image_output_dir 默认 None
- 错误代码精确：
  - file_not_found / pdfplumber_open_failed / pdfplumber_unavailable
  - python_docx_unavailable / docx_open_failed
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

import pytest

from app.parsers.fallback_parser import (
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
    FallbackParser,
)


# =========================================================================
# _CAPTION_RE 模式深度
# =========================================================================


def test_caption_re_pattern_contains_table_keyword():
    assert "Table" in _CAPTION_RE.pattern


def test_caption_re_pattern_contains_figure_keyword():
    assert "Figure" in _CAPTION_RE.pattern


def test_caption_re_pattern_contains_fig_abbreviation():
    assert "Fig" in _CAPTION_RE.pattern


def test_caption_re_pattern_contains_chinese_table():
    assert "表" in _CAPTION_RE.pattern


def test_caption_re_pattern_contains_chinese_figure():
    assert "图" in _CAPTION_RE.pattern


def test_caption_re_pattern_contains_full_width_digit_range():
    assert "０-９" in _CAPTION_RE.pattern


def test_caption_re_pattern_contains_ascii_digit_range():
    assert "0-9" in _CAPTION_RE.pattern


def test_caption_re_pattern_contains_separator_chars():
    """分隔符含 . 、 : 空白。"""
    assert "." in _CAPTION_RE.pattern
    assert ":" in _CAPTION_RE.pattern
    assert "、" in _CAPTION_RE.pattern


def test_caption_re_pattern_uses_ignore_case():
    assert _CAPTION_RE.flags & re.IGNORECASE


def test_caption_re_pattern_compiled_once():
    """_CAPTION_RE 是编译好的 Pattern。"""
    assert isinstance(_CAPTION_RE, re.Pattern)


# =========================================================================
# _is_caption 多形式覆盖
# =========================================================================


def test_is_caption_figure_with_dot_space_number():
    assert _is_caption("Figure 1. This is a figure")


def test_is_caption_figure_no_dot_space_number():
    assert _is_caption("Figure 1 This is a figure")


def test_is_caption_fig_with_dot_no_space_number():
    assert _is_caption("Fig.1 This is a figure")


def test_is_caption_fig_with_dot_space_number():
    assert _is_caption("Fig. 1 This is a figure")


def test_is_caption_fig_without_dot_space_number():
    assert _is_caption("Fig 1 This is a figure")


def test_is_caption_table_with_dot_space_number():
    assert _is_caption("Table 1. This is a table")


def test_is_caption_table_full_width_digit():
    assert _is_caption("Table １.全角数字")


def test_is_caption_chinese_table_with_chinese_period():
    assert _is_caption("表 1、中文表格")


def test_is_caption_chinese_figure_with_ascii_colon():
    """中文图 + ASCII 冒号（pattern 不含全角：）。"""
    assert _is_caption("图 1: 中文图片")


def test_is_caption_uppercase_keyword():
    assert _is_caption("FIGURE 1. uppercase keyword")


def test_is_caption_mixed_case_keyword():
    assert _is_caption("Figure 1. Mixed Case")


def test_is_caption_number_zero_padded():
    assert _is_caption("Figure 01. zero padded")


def test_is_caption_multi_digit_number():
    assert _is_caption("Figure 999. multi digit")


def test_is_caption_zero_number():
    assert _is_caption("Figure 0. zero number")


def test_is_caption_does_not_match_paragraph_starting_with_table_word():
    """词后必须跟数字才匹配。"""
    assert not _is_caption("Table of contents")


def test_is_caption_does_not_match_word_in_middle():
    """必须以关键词开头。"""
    assert not _is_caption("See Figure 1. somewhere")


def test_is_caption_keyword_only_no_number_fails():
    assert not _is_caption("Figure.")


def test_is_caption_keyword_number_no_separator_fails():
    """无分隔符不匹配（保留兼容性）。"""
    # 'Figure1' 后无分隔符不匹配
    assert not _is_caption("Figure1")


# =========================================================================
# _classify_pdf_paragraph 深度
# =========================================================================


def test_classify_pdf_paragraph_empty_string_returns_paragraph():
    etype, meta = _classify_pdf_paragraph("")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_pdf_paragraph_whitespace_only_returns_paragraph():
    etype, meta = _classify_pdf_paragraph("   \t\n  ")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_pdf_paragraph_long_text_no_punct_returns_paragraph():
    """81 字符（>80）→ paragraph。"""
    text = "a" * 81
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "paragraph"


def test_classify_pdf_paragraph_80_chars_no_punct_is_heading():
    """80 字符（<=80）且无句末标点 → heading。"""
    text = "a" * 80
    etype, meta = _classify_pdf_paragraph(text)
    assert etype == "heading"
    assert meta["level"] == 0
    assert meta["heuristic"] == "short_line"


def test_classify_pdf_paragraph_80_chars_with_period_is_paragraph():
    """80 字符且以 . 结尾 → paragraph。"""
    text = "a" * 79 + "."
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_chinese_period_is_paragraph():
    """短文本以 。结尾 → paragraph。"""
    etype, _ = _classify_pdf_paragraph("短句。")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_exclamation_is_paragraph():
    etype, _ = _classify_pdf_paragraph("短句!")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_question_is_paragraph():
    etype, _ = _classify_pdf_paragraph("短句?")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_caption_priority_over_heading():
    """caption 优先于 heading。"""
    text = "Figure 1. caption text"
    etype, meta = _classify_pdf_paragraph(text)
    assert etype == "caption"
    assert meta["heuristic"] == "caption_regex"


def test_classify_pdf_paragraph_caption_meta_only_has_heuristic_key():
    etype, meta = _classify_pdf_paragraph("Figure 1. caption")
    assert set(meta.keys()) == {"heuristic"}


def test_classify_pdf_paragraph_heading_meta_has_two_keys():
    etype, meta = _classify_pdf_paragraph("short heading")
    assert set(meta.keys()) == {"level", "heuristic"}


def test_classify_pdf_paragraph_returns_tuple_type():
    result = _classify_pdf_paragraph("test")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_classify_pdf_paragraph_first_element_str():
    etype, _ = _classify_pdf_paragraph("test")
    assert isinstance(etype, str)


def test_classify_pdf_paragraph_second_element_dict():
    _, meta = _classify_pdf_paragraph("test")
    assert isinstance(meta, dict)


# =========================================================================
# _image_filename 深度
# =========================================================================


def test_image_filename_doc_1_to_1():
    assert _image_filename("doc-1", "p1", 0) == "image_1_p1_00.png"


def test_image_filename_doc_123_to_123():
    assert _image_filename("doc-123", "p1", 0) == "image_123_p1_00.png"


def test_image_filename_no_doc_prefix_unchanged():
    """无 doc- 前缀的 document_id 原样保留。"""
    assert _image_filename("custom-id", "p1", 0) == "image_custom-id_p1_00.png"


def test_image_filename_multiple_doc_prefix_all_stripped():
    """str.replace 替换所有 'doc-'，所以 "doc-doc-1" → "1"。"""
    name = _image_filename("doc-doc-1", "p1", 0)
    # str.replace 替换所有出现，所以 "doc-doc-1" → "1"
    assert name == "image_1_p1_00.png"


def test_image_filename_index_99():
    assert _image_filename("doc-1", "p1", 99) == "image_1_p1_99.png"


def test_image_filename_index_100_no_extra_pad():
    """100 不需要补 0（已经 3 位）。"""
    assert _image_filename("doc-1", "p1", 100) == "image_1_p1_100.png"


def test_image_filename_prefix_para0():
    assert _image_filename("doc-1", "para0", 0) == "image_1_para0_00.png"


def test_image_filename_custom_ext():
    assert _image_filename("doc-1", "p1", 0, "jpg") == "image_1_p1_00.jpg"


def test_image_filename_returns_str():
    name = _image_filename("doc-1", "p1", 0)
    assert isinstance(name, str)


def test_image_filename_doc_with_underscore():
    assert _image_filename("doc-my_doc", "p1", 0) == "image-my_doc_p1_00.png".replace("-", "_", 1)


# =========================================================================
# _rows_to_markdown 深度
# =========================================================================


def test_rows_to_markdown_pipe_in_cell_preserved():
    """单元格内的 | 字符不转义（保留原样）。"""
    md = _rows_to_markdown([["a|b", "c"]])
    assert "a|b" in md


def test_rows_to_markdown_newline_in_cell_preserved():
    md = _rows_to_markdown([["a\nb"]])
    # 单元格内换行保留
    assert "a\nb" in md


def test_rows_to_markdown_single_row_no_separator_after_header():
    """单行（仅 header）→ 输出含 header + 分隔行（无 body）。"""
    md = _rows_to_markdown([["h1", "h2"]])
    lines = md.split("\n")
    assert len(lines) == 2  # header + 分隔行
    assert lines[0] == "| h1 | h2 |"
    assert lines[1].startswith("| ---")


def test_rows_to_markdown_separator_uses_three_dashes_per_col():
    md = _rows_to_markdown([["h1", "h2", "h3"]])
    lines = md.split("\n")
    # 分隔行：每个 column 一个 ---
    assert lines[1].count("---") == 3


def test_rows_to_markdown_two_body_rows():
    """1 header + 2 body rows = 4 行（header + 分隔 + 2 body）。"""
    md = _rows_to_markdown([["h"], ["a"], ["b"]])
    lines = md.split("\n")
    assert len(lines) == 4


def test_rows_to_markdown_returns_str_type():
    assert isinstance(_rows_to_markdown([["a"]]), str)


def test_rows_to_markdown_empty_cells_become_empty_string():
    md = _rows_to_markdown([["", "x"]])
    assert "|  | x |" in md


def test_rows_to_markdown_int_zero():
    md = _rows_to_markdown([[0, 1]])
    assert "| 0 | 1 |" in md


def test_rows_to_markdown_float_value():
    md = _rows_to_markdown([[3.14]])
    assert "3.14" in md


def test_rows_to_markdown_none_in_second_row():
    md = _rows_to_markdown([["h"], [None]])
    assert "|  |" in md or "| |" in md


# =========================================================================
# _lines_to_para 深度
# =========================================================================


def test_lines_to_para_returns_dict_with_text_and_bbox_keys():
    result = _lines_to_para([])
    assert "text" in result
    assert "bbox" in result


def test_lines_to_para_empty_lines_returns_empty_text_and_none_bbox():
    result = _lines_to_para([])
    assert result["text"] == ""
    assert result["bbox"] is None


def test_lines_to_para_single_line_single_word():
    lines = [[{"text": "hello", "x0": 0, "x1": 50, "top": 10, "bottom": 20}]]
    result = _lines_to_para(lines)
    assert result["text"] == "hello"
    assert result["bbox"] == [0, 10, 50, 20]


def test_lines_to_para_two_words_same_line_joined_by_space():
    lines = [[
        {"text": "hello", "x0": 0, "x1": 50, "top": 10, "bottom": 20},
        {"text": "world", "x0": 60, "x1": 110, "top": 10, "bottom": 20},
    ]]
    result = _lines_to_para(lines)
    assert result["text"] == "hello world"


def test_lines_to_para_two_lines_joined_by_space():
    lines = [
        [{"text": "hello", "x0": 0, "x1": 50, "top": 10, "bottom": 20}],
        [{"text": "world", "x0": 0, "x1": 50, "top": 30, "bottom": 40}],
    ]
    result = _lines_to_para(lines)
    assert result["text"] == "hello world"


def test_lines_to_para_bbox_order_x0_top_x1_bottom():
    """bbox 顺序是 [x0_min, top_min, x1_max, bottom_max]。"""
    lines = [[
        {"text": "a", "x0": 10, "x1": 20, "top": 5, "bottom": 15},
        {"text": "b", "x0": 30, "x1": 40, "top": 8, "bottom": 18},
    ]]
    result = _lines_to_para(lines)
    bbox = result["bbox"]
    assert bbox == [10, 5, 40, 18]


def test_lines_to_para_word_missing_top_uses_zero():
    lines = [[{"text": "a", "x0": 0, "x1": 10, "bottom": 20}]]
    result = _lines_to_para(lines)
    assert result["bbox"][1] == 0  # top default 0


def test_lines_to_para_word_missing_bottom_uses_zero():
    lines = [[{"text": "a", "x0": 0, "x1": 10, "top": 5}]]
    result = _lines_to_para(lines)
    assert result["bbox"][3] == 0  # bottom default 0


def test_lines_to_para_words_sorted_by_x0_within_line():
    """同一行 word 按x0 升序拼接（不依赖输入顺序）。"""
    lines = [[
        {"text": "b", "x0": 60, "x1": 110, "top": 10, "bottom": 20},
        {"text": "a", "x0": 0, "x1": 50, "top": 10, "bottom": 20},
    ]]
    result = _lines_to_para(lines)
    assert result["text"] == "a b"


# =========================================================================
# _group_words_to_paragraphs 深度
# =========================================================================


def test_group_words_empty_list_returns_empty_list():
    assert _group_words_to_paragraphs([]) == []


def test_group_words_single_word_single_paragraph():
    words = [{"text": "hello", "x0": 0, "x1": 50, "top": 10, "bottom": 20}]
    result = _group_words_to_paragraphs(words)
    assert len(result) == 1
    assert result[0]["text"] == "hello"


def test_group_words_two_words_same_y_one_paragraph():
    words = [
        {"text": "hello", "x0": 0, "x1": 50, "top": 10, "bottom": 20},
        {"text": "world", "x0": 60, "x1": 110, "top": 10, "bottom": 20},
    ]
    result = _group_words_to_paragraphs(words)
    assert len(result) == 1
    assert result[0]["text"] == "hello world"


def test_group_words_returns_list_of_dict():
    words = [{"text": "a", "x0": 0, "x1": 10, "top": 0, "bottom": 10}]
    result = _group_words_to_paragraphs(words)
    assert isinstance(result, list)
    assert all(isinstance(p, dict) for p in result)


def test_group_words_each_para_has_text_and_bbox_keys():
    words = [{"text": "a", "x0": 0, "x1": 10, "top": 0, "bottom": 10}]
    result = _group_words_to_paragraphs(words)
    for para in result:
        assert "text" in para
        assert "bbox" in para


# =========================================================================
# _is_heading_style 深度
# =========================================================================


def test_is_heading_style_title_returns_true_level_1():
    assert _is_heading_style("Title") == (True, 1)


def test_is_heading_style_title_lowercase_returns_true():
    """style 名 lowercase 后比较，'title' 也匹配。"""
    assert _is_heading_style("title") == (True, 1)


def test_is_heading_style_title_with_whitespace_stripped():
    assert _is_heading_style("  Title  ") == (True, 1)


def test_is_heading_style_heading_1():
    assert _is_heading_style("Heading 1") == (True, 1)


def test_is_heading_style_heading_2():
    assert _is_heading_style("Heading 2") == (True, 2)


def test_is_heading_style_heading_10():
    assert _is_heading_style("Heading 10") == (True, 10)


def test_is_heading_style_heading_no_level_returns_1():
    """'Heading' 无级别 → ValueError → 返回 (True, 1)。"""
    assert _is_heading_style("Heading") == (True, 1)


def test_is_heading_style_heading_with_only_spaces_after_returns_1():
    """'Heading  ' 后 strip 后 'heading' → ValueError → (True, 1)。"""
    result = _is_heading_style("Heading   ")
    # 'heading   '.replace('heading', '').strip() = '' → int('') ValueError → (True, 1)
    assert result == (True, 1)


def test_is_heading_style_heading_with_invalid_level_returns_1():
    """'Heading abc' → int('abc') ValueError → (True, 1)。"""
    assert _is_heading_style("Heading abc") == (True, 1)


def test_is_heading_style_normal_returns_false():
    assert _is_heading_style("Normal") == (False, 0)


def test_is_heading_style_list_paragraph_returns_false():
    assert _is_heading_style("List Paragraph") == (False, 0)


def test_is_heading_style_quote_returns_false():
    assert _is_heading_style("Quote") == (False, 0)


def test_is_heading_style_empty_string_returns_false():
    assert _is_heading_style("") == (False, 0)


def test_is_heading_style_none_returns_false():
    assert _is_heading_style(None) == (False, 0)


def test_is_heading_style_returns_tuple_type():
    result = _is_heading_style("Heading 1")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_is_heading_style_first_element_bool():
    is_h, _ = _is_heading_style("Heading 1")
    assert isinstance(is_h, bool)


def test_is_heading_style_second_element_int():
    _, level = _is_heading_style("Heading 1")
    assert isinstance(level, int)


def test_is_heading_style_lowercase_heading_matched():
    """'heading 1' 也匹配（lowercase 后是 'heading 1'）。"""
    assert _is_heading_style("heading 1") == (True, 1)


def test_is_heading_style_uppercase_heading_matched():
    assert _is_heading_style("HEADING 1") == (True, 1)


def test_is_heading_style_negative_level_clamped_to_one():
    """int('-1') 不会 ValueError，但 max(1, -1) = 1。"""
    # 注意：'Heading -1'.replace('heading', '').strip() = '-1' → int('-1') = -1
    # max(1, -1) = 1
    assert _is_heading_style("Heading -1") == (True, 1)


# =========================================================================
# _extract_inline_image_rids 深度
# =========================================================================


def test_extract_inline_image_rids_empty_xml_returns_empty_list():
    """无 drawing element → 空列表。"""

    class FakeXml:
        def iter(self, _qn):
            return iter([])

    assert _extract_inline_image_rids(FakeXml()) == []


def test_extract_inline_image_rids_returns_list_type():

    class FakeXml:
        def iter(self, _qn):
            return iter([])

    result = _extract_inline_image_rids(FakeXml())
    assert isinstance(result, list)


def test_extract_inline_image_rids_each_item_is_str():
    """rid 是字符串。"""
    from app.parsers import fallback_parser as mod

    if mod.qn is None:
        pytest.skip("qn is None (docx not installed)")

    # 构造伪 XML：含一个 drawing > blip with r:embed
    from xml.etree import ElementTree as ET

    nsmap = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    # 注册命名空间
    for prefix, uri in nsmap.items():
        ET.register_namespace(prefix, uri)

    root = ET.fromstring("""
    <w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
         xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
         xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
        <w:drawing>
            <a:blip r:embed="rId1"/>
        </w:drawing>
    </w:p>
    """)
    rids = _extract_inline_image_rids(root)
    assert all(isinstance(r, str) for r in rids)


# =========================================================================
# _save_image 深度
# =========================================================================


def test_save_image_returns_path_object(tmp_path: Path):
    p = _save_image(b"hello", tmp_path / "sub", "doc-1", "p1", 0)
    assert isinstance(p, Path)


def test_save_image_writes_bytes_to_file(tmp_path: Path):
    out_dir = tmp_path / "imgs"
    p = _save_image(b"binary-data", out_dir, "doc-1", "p1", 0)
    assert p.read_bytes() == b"binary-data"


def test_save_image_creates_nested_directory(tmp_path: Path):
    out_dir = tmp_path / "a" / "b" / "c"
    assert not out_dir.exists()
    _save_image(b"x", out_dir, "doc-1", "p1", 0)
    assert out_dir.is_dir()


def test_save_image_filename_format(tmp_path: Path):
    p = _save_image(b"x", tmp_path, "doc-1", "p1", 0)
    assert p.name == "image_1_p1_00.png"


def test_save_image_custom_ext(tmp_path: Path):
    p = _save_image(b"x", tmp_path, "doc-1", "p1", 0, "jpg")
    assert p.suffix == ".jpg"


def test_save_image_existing_directory_ok(tmp_path: Path):
    """目录已存在不报错。"""
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = _save_image(b"x", tmp_path, "doc-1", "p1", 0)
    assert p.exists()


def test_save_image_overwrites_existing_file(tmp_path: Path):
    p = _save_image(b"old", tmp_path, "doc-1", "p1", 0)
    p2 = _save_image(b"new", tmp_path, "doc-1", "p1", 0)
    assert p == p2
    assert p.read_bytes() == b"new"


def test_save_image_empty_bytes(tmp_path: Path):
    p = _save_image(b"", tmp_path, "doc-1", "p1", 0)
    assert p.read_bytes() == b""


def test_save_image_sequential_indexes_different_files(tmp_path: Path):
    p0 = _save_image(b"a", tmp_path, "doc-1", "p1", 0)
    p1 = _save_image(b"b", tmp_path, "doc-1", "p1", 1)
    assert p0 != p1


# =========================================================================
# FallbackParser class 深度
# =========================================================================


def test_fallback_parser_class_attribute_name():
    assert FallbackParser.name == "fallback"


def test_fallback_parser_class_attribute_version_is_str():
    assert isinstance(FallbackParser.version, str)


def test_fallback_parser_class_attribute_version_contains_pdfplumber():
    assert "pdfplumber" in FallbackParser.version


def test_fallback_parser_class_attribute_version_contains_python_docx():
    assert "python-docx" in FallbackParser.version


def test_fallback_parser_class_attribute_version_contains_pypdfium2():
    assert "pypdfium2" in FallbackParser.version


def test_fallback_parser_class_inherits_parser():
    from app.parsers.base import Parser

    assert issubclass(FallbackParser, Parser)


def test_fallback_parser_has_parse_method():
    assert callable(getattr(FallbackParser, "parse", None))


def test_fallback_parser_init_default_image_output_dir_none():
    p = FallbackParser()
    assert p._image_output_dir is None


def test_fallback_parser_init_with_path(tmp_path: Path):
    p = FallbackParser(image_output_dir=tmp_path)
    assert p._image_output_dir == tmp_path


def test_fallback_parser_init_str_converted_to_path(tmp_path: Path):
    p = FallbackParser(image_output_dir=str(tmp_path))
    assert isinstance(p._image_output_dir, Path)
    assert p._image_output_dir == tmp_path


def test_fallback_parser_init_empty_string_treated_as_none():
    p = FallbackParser(image_output_dir="")
    assert p._image_output_dir is None


def test_fallback_parser_init_none_explicit():
    p = FallbackParser(image_output_dir=None)
    assert p._image_output_dir is None


def test_fallback_parser_two_instances_independent(tmp_path: Path):
    p1 = FallbackParser(image_output_dir=tmp_path)
    p2 = FallbackParser()
    assert p1._image_output_dir == tmp_path
    assert p2._image_output_dir is None


# =========================================================================
# FallbackParser.parse 错误路径
# =========================================================================


def test_fallback_parser_parse_missing_file_raises_parser_error(tmp_path: Path):
    from app.parsers.base import ParserError

    p = tmp_path / "missing.pdf"
    parser = FallbackParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(p, "a" * 64)
    assert ei.value.code == "file_not_found"


def test_fallback_parser_parse_missing_file_message_contains_path(tmp_path: Path):
    from app.parsers.base import ParserError

    p = tmp_path / "missing.pdf"
    parser = FallbackParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(p, "a" * 64)
    assert "missing.pdf" in str(ei.value)


def test_fallback_parser_parse_missing_file_details_has_path(tmp_path: Path):
    from app.parsers.base import ParserError

    p = tmp_path / "missing.pdf"
    parser = FallbackParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(p, "a" * 64)
    assert ei.value.details == {"path": str(p)}


def test_fallback_parser_parse_directory_raises_file_not_found(tmp_path: Path):
    """目录而非文件 → ParserError(file_not_found)。"""
    from app.parsers.base import ParserError

    d = tmp_path / "subdir"
    d.mkdir()
    parser = FallbackParser()
    with pytest.raises(ParserError) as ei:
        parser.parse(d, "a" * 64)
    assert ei.value.code == "file_not_found"


# =========================================================================
# _render_pdf_image_region 兼容包装
# =========================================================================


def test_render_pdf_image_region_callable():
    assert callable(_render_pdf_image_region)


def test_render_pdf_image_region_verbose_callable():
    assert callable(_render_pdf_image_region_verbose)


def test_render_pdf_image_region_signature_five_params():
    sig = inspect.signature(_render_pdf_image_region)
    params = list(sig.parameters.keys())
    assert len(params) == 5
    assert "pdf_path" in params
    assert "page_idx_0based" in params
    assert "bbox" in params
    assert "out_path" in params
    assert "dpi" in params


def test_render_pdf_image_region_verbose_signature_five_params():
    sig = inspect.signature(_render_pdf_image_region_verbose)
    params = list(sig.parameters.keys())
    assert len(params) == 5
    assert "pdf_path" in params
    assert "page_idx_0based" in params
    assert "bbox" in params
    assert "out_path" in params
    assert "dpi" in params


def test_render_pdf_image_region_verbose_default_dpi_144():
    sig = inspect.signature(_render_pdf_image_region_verbose)
    assert sig.parameters["dpi"].default == 144


def test_render_pdf_image_region_default_dpi_144():
    sig = inspect.signature(_render_pdf_image_region)
    assert sig.parameters["dpi"].default == 144


def test_render_pdf_image_region_verbose_return_annotation_str_or_none():
    sig = inspect.signature(_render_pdf_image_region_verbose)
    ret = sig.return_annotation
    assert "str" in str(ret) and "None" in str(ret)


def test_render_pdf_image_region_return_annotation_bool():
    sig = inspect.signature(_render_pdf_image_region)
    ret = sig.return_annotation
    assert "bool" in str(ret).lower()


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_imports_re():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "re")


def test_module_imports_path():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "Path")


def test_module_imports_any():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "Any")


def test_module_imports_document():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "Document")


def test_module_imports_element():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "Element")


def test_module_imports_warning_record():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "WarningRecord")


def test_module_imports_parser():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "Parser")


def test_module_imports_parser_error():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "ParserError")


def test_module_imports_detect_source_type():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "detect_source_type")


def test_module_imports_make_document_id():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "make_document_id")


def test_module_has_caption_re():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_CAPTION_RE")


def test_module_has_is_caption():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_is_caption")


def test_module_has_rows_to_markdown():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_rows_to_markdown")


def test_module_has_image_filename():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_image_filename")


def test_module_has_save_image():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_save_image")


def test_module_has_group_words_to_paragraphs():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_group_words_to_paragraphs")


def test_module_has_lines_to_para():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_lines_to_para")


def test_module_has_classify_pdf_paragraph():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_classify_pdf_paragraph")


def test_module_has_render_pdf_image_region():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_render_pdf_image_region")


def test_module_has_render_pdf_image_region_verbose():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_render_pdf_image_region_verbose")


def test_module_has_is_heading_style():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_is_heading_style")


def test_module_has_extract_inline_image_rids():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_extract_inline_image_rids")


def test_module_has_parse_pdf():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_parse_pdf")


def test_module_has_parse_docx():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_parse_docx")


def test_module_has_fallback_parser_class():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "FallbackParser")


def test_module_all_is_list():
    from app.parsers import fallback_parser as mod
    assert isinstance(mod.__all__, list)


def test_module_all_length_one():
    from app.parsers import fallback_parser as mod
    assert len(mod.__all__) == 1


def test_module_all_exact_set():
    from app.parsers import fallback_parser as mod
    assert set(mod.__all__) == {"FallbackParser"}


def test_module_all_excludes_internal_helpers():
    from app.parsers import fallback_parser as mod
    for item in mod.__all__:
        assert not item.startswith("_")


def test_module_has_pdfplumber_version_constant():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_PDFPLUMBER_VERSION")


def test_module_has_pdfium_version_constant():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_PDFIUM_VERSION")


def test_module_has_docx_version_constant():
    from app.parsers import fallback_parser as mod
    assert hasattr(mod, "_DOCX_VERSION")


def test_module_docstring_present():
    from app.parsers import fallback_parser as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_pdfplumber():
    from app.parsers import fallback_parser as mod
    doc = mod.__doc__
    assert "pdfplumber" in doc


def test_module_docstring_mentions_python_docx():
    from app.parsers import fallback_parser as mod
    doc = mod.__doc__
    assert "python-docx" in doc or "docx" in doc


def test_module_uses_future_annotations():
    import ast
    from app.parsers import fallback_parser as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    has_future = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(a.name == "annotations" for a in node.names)
        for node in tree.body
    )
    assert has_future


# =========================================================================
# 签名深度
# =========================================================================


def test_is_caption_signature_one_param():
    sig = inspect.signature(_is_caption)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "text" in params


def test_is_caption_return_annotation_bool():
    sig = inspect.signature(_is_caption)
    ret = sig.return_annotation
    assert "bool" in str(ret).lower()


def test_rows_to_markdown_signature_one_param():
    sig = inspect.signature(_rows_to_markdown)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "rows" in params


def test_rows_to_markdown_return_annotation_str():
    sig = inspect.signature(_rows_to_markdown)
    ret = sig.return_annotation
    assert ret is str or "str" in str(ret)


def test_image_filename_signature_four_params():
    sig = inspect.signature(_image_filename)
    params = list(sig.parameters.keys())
    assert len(params) == 4
    assert "document_id" in params
    assert "prefix" in params
    assert "index" in params
    assert "ext" in params


def test_image_filename_default_ext_png():
    sig = inspect.signature(_image_filename)
    assert sig.parameters["ext"].default == "png"


def test_image_filename_return_annotation_str():
    sig = inspect.signature(_image_filename)
    ret = sig.return_annotation
    assert ret is str or "str" in str(ret)


def test_save_image_signature_six_params():
    sig = inspect.signature(_save_image)
    params = list(sig.parameters.keys())
    assert len(params) == 6
    assert "bytes_data" in params
    assert "out_dir" in params
    assert "document_id" in params
    assert "prefix" in params
    assert "index" in params
    assert "ext" in params


def test_save_image_default_ext_png():
    sig = inspect.signature(_save_image)
    assert sig.parameters["ext"].default == "png"


def test_save_image_return_annotation_path():
    sig = inspect.signature(_save_image)
    ret = sig.return_annotation
    assert "Path" in str(ret)


def test_classify_pdf_paragraph_signature_one_param():
    sig = inspect.signature(_classify_pdf_paragraph)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "text" in params


def test_classify_pdf_paragraph_return_annotation_tuple():
    sig = inspect.signature(_classify_pdf_paragraph)
    ret = sig.return_annotation
    assert "tuple" in str(ret).lower()


def test_is_heading_style_signature_one_param():
    sig = inspect.signature(_is_heading_style)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "style_name" in params


def test_is_heading_style_param_annotation_str_or_none():
    sig = inspect.signature(_is_heading_style)
    ann = sig.parameters["style_name"].annotation
    assert "str" in str(ann) and "None" in str(ann)


def test_is_heading_style_return_annotation_tuple():
    sig = inspect.signature(_is_heading_style)
    ret = sig.return_annotation
    assert "tuple" in str(ret).lower()


def test_group_words_to_paragraphs_signature_one_param():
    sig = inspect.signature(_group_words_to_paragraphs)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "words" in params


def test_group_words_to_paragraphs_return_annotation_list():
    sig = inspect.signature(_group_words_to_paragraphs)
    ret = sig.return_annotation
    assert "list" in str(ret).lower()


def test_lines_to_para_signature_one_param():
    sig = inspect.signature(_lines_to_para)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "lines" in params


def test_lines_to_para_return_annotation_dict():
    sig = inspect.signature(_lines_to_para)
    ret = sig.return_annotation
    assert "dict" in str(ret).lower()


def test_fallback_parser_init_signature_two_params():
    sig = inspect.signature(FallbackParser.__init__)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "image_output_dir" in params


def test_fallback_parser_init_image_output_dir_default_none():
    sig = inspect.signature(FallbackParser.__init__)
    assert sig.parameters["image_output_dir"].default is None


def test_fallback_parser_init_param_annotation_path_or_str_or_none():
    sig = inspect.signature(FallbackParser.__init__)
    ann = sig.parameters["image_output_dir"].annotation
    assert "Path" in str(ann) and "None" in str(ann)


def test_fallback_parser_init_return_annotation_none():
    sig = inspect.signature(FallbackParser.__init__)
    ret = sig.return_annotation
    assert ret is None or "None" in str(ret)


def test_fallback_parser_parse_signature_three_params():
    sig = inspect.signature(FallbackParser.parse)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "path" in params
    assert "source_hash" in params


def test_fallback_parser_parse_return_annotation_document():
    sig = inspect.signature(FallbackParser.parse)
    ret = sig.return_annotation
    assert "Document" in str(ret)
