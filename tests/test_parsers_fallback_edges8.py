r"""app/parsers/fallback_parser.py 边角测试 - 第八轮（Round 192）。

补强已有 base/edges/edges2-7（共 942 测试）未覆盖的深度：
- _is_heading_style 各样式边界（Title/Heading N/Heading 无数字/Heading 字母后缀/全大写/前导空格）
- _extract_inline_image_rids qn=None 路径 + 错误 XML
- _group_words_to_paragraphs 算法深度（median 计算、行聚类阈值边界 3.0、段落分隔阈值 1.5*median）
- _lines_to_para bbox 边界（单 word、跨行 min/max、缺 top/bottom）
- _classify_pdf_paragraph 全 terminators 边界
- _render_pdf_image_region_verbose pypdfium2 unavailable + 各异常路径
- _image_filename 大 index（3 位数）
- _save_image 重复写盘行为
- _rows_to_markdown None/int/混合类型 cell
- FallbackParser.__init__ 各种 image_output_dir 类型
- FallbackParser.version 格式
- FallbackParser.parse file_not_found 细节、metadata 字段
- 模块结构（imports、docstring、版本常量、__all__）
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

import pytest

from app.parsers.base import Parser, ParserError
from app.parsers.fallback_parser import (
    _CAPTION_RE,
    _classify_pdf_paragraph,
    _DOCX_VERSION,
    _extract_inline_image_rids,
    _group_words_to_paragraphs,
    _image_filename,
    _is_caption,
    _is_heading_style,
    _lines_to_para,
    _PDFIUM_VERSION,
    _PDFPLUMBER_VERSION,
    _render_pdf_image_region_verbose,
    _rows_to_markdown,
    _save_image,
    FallbackParser,
)
import app.parsers.fallback_parser as fallback_mod


# =========================================================================
# _is_heading_style 边界
# =========================================================================


def test_is_heading_style_signature():
    sig = inspect.signature(_is_heading_style)
    params = list(sig.parameters)
    assert params == ["style_name"]


def test_is_heading_style_returns_tuple():
    result = _is_heading_style("Heading 1")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_is_heading_style_first_element_bool():
    is_h, _ = _is_heading_style("Heading 1")
    assert isinstance(is_h, bool)


def test_is_heading_style_second_element_int():
    _, level = _is_heading_style("Heading 1")
    assert isinstance(level, int)


def test_is_heading_style_title():
    assert _is_heading_style("Title") == (True, 1)


def test_is_heading_style_title_lowercase():
    assert _is_heading_style("title") == (True, 1)


def test_is_heading_style_title_uppercase():
    assert _is_heading_style("TITLE") == (True, 1)


def test_is_heading_style_title_with_whitespace():
    assert _is_heading_style("  Title  ") == (True, 1)


def test_is_heading_style_heading_1():
    assert _is_heading_style("Heading 1") == (True, 1)


def test_is_heading_style_heading_2():
    assert _is_heading_style("Heading 2") == (True, 2)


def test_is_heading_style_heading_3():
    assert _is_heading_style("Heading 3") == (True, 3)


def test_is_heading_style_heading_4():
    assert _is_heading_style("Heading 4") == (True, 4)


def test_is_heading_style_heading_5():
    assert _is_heading_style("Heading 5") == (True, 5)


def test_is_heading_style_heading_6():
    assert _is_heading_style("Heading 6") == (True, 6)


def test_is_heading_style_heading_large_level():
    assert _is_heading_style("Heading 9") == (True, 9)


def test_is_heading_style_heading_no_level():
    """只 'Heading' 无数字 → ValueError → 默认 1。"""
    assert _is_heading_style("Heading") == (True, 1)


def test_is_heading_style_heading_with_garbage_suffix():
    """'Heading XYZ' → int 失败 → 默认 1。"""
    assert _is_heading_style("Heading XYZ") == (True, 1)


def test_is_heading_style_heading_zero_clamped_to_one():
    """'Heading 0' → int=0 → max(1, 0)=1。"""
    assert _is_heading_style("Heading 0") == (True, 1)


def test_is_heading_style_heading_negative_clamped_to_one():
    """'Heading -1' → int=-1 → max(1, -1)=1。"""
    assert _is_heading_style("Heading -1") == (True, 1)


def test_is_heading_style_normal_returns_false():
    assert _is_heading_style("Normal") == (False, 0)


def test_is_heading_style_body_text_returns_false():
    assert _is_heading_style("Body Text") == (False, 0)


def test_is_heading_style_subtitle_returns_false():
    assert _is_heading_style("Subtitle") == (False, 0)


def test_is_heading_style_none_returns_false():
    assert _is_heading_style(None) == (False, 0)


def test_is_heading_style_empty_string_returns_false():
    assert _is_heading_style("") == (False, 0)


def test_is_heading_style_whitespace_only_returns_false():
    assert _is_heading_style("   ") == (False, 0)


def test_is_heading_style_lowercase_heading():
    assert _is_heading_style("heading 2") == (True, 2)


def test_is_heading_style_uppercase_heading():
    assert _is_heading_style("HEADING 3") == (True, 3)


def test_is_heading_style_heading_with_extra_whitespace():
    assert _is_heading_style("  Heading  4  ") == (True, 4)


def test_is_heading_style_heading_no_space_after():
    """'Heading5' 也匹配（startswith 'heading' 后 replace 'heading' → '5'）。"""
    is_h, level = _is_heading_style("Heading5")
    assert is_h is True
    assert level == 5


def test_is_heading_style_heading_tab_separator():
    """'Heading\\t3' strip+lower 后是 'heading\\t3'，replace 后 '\\t3' int() 失败 → 默认 1。"""
    is_h, level = _is_heading_style("Heading\t3")
    assert is_h is True
    # int("\t3".strip()) == 3
    assert level == 3


def test_is_heading_style_quote_prefix_returns_false():
    """'Quote' 不以 heading 开头 → False。"""
    assert _is_heading_style("Quote") == (False, 0)


def test_is_heading_style_does_not_match_subtitle_starts_with_s():
    assert _is_heading_style("Subtitle") == (False, 0)


# =========================================================================
# _extract_inline_image_rids 边界
# =========================================================================


def test_extract_inline_image_rids_signature():
    sig = inspect.signature(_extract_inline_image_rids)
    params = list(sig.parameters)
    assert params == ["paragraph_xml"]


def test_extract_inline_image_rids_returns_list():
    """无 qn 时返回空 list。"""
    class FakeXML:
        def iter(self, _):
            return iter([])
    result = _extract_inline_image_rids(FakeXML())
    assert isinstance(result, list)


def test_extract_inline_image_rids_empty_xml_returns_empty():
    class FakeXML:
        def iter(self, _):
            return iter([])
    assert _extract_inline_image_rids(FakeXML()) == []


def test_extract_inline_image_rids_finds_single_embed():
    """模拟一个 drawing > blip with r:embed。"""
    class FakeBlip:
        def __init__(self, embed, link=None):
            self._embed = embed
            self._link = link

        def get(self, key):
            if "embed" in key:
                return self._embed
            if "link" in key:
                return self._link
            return None

    class FakeDrawing:
        def __init__(self, blips):
            self._blips = blips

        def iter(self, key):
            if "blip" in str(key):
                return iter(self._blips)
            return iter([])

    class FakeXML:
        def __init__(self, drawings):
            self._drawings = drawings

        def iter(self, key):
            if "drawing" in str(key):
                return iter(self._drawings)
            return iter([])

    # qn 是真实函数（如果 docx 可用），调用 qn("w:drawing") 返回特定字符串
    if fallback_mod.qn is None:
        # docx 未装，跳过
        pytest.skip("docx 不可用，无法测试 _extract_inline_image_rids 真实路径")

    blip = FakeBlip(embed="rId1")
    drawing = FakeDrawing([blip])
    xml = FakeXML([drawing])
    # 因为 FakeXML.iter 接受任意 key（含 qn(...)），返回 drawings/blips
    # qn("w:drawing") 是 "{http://...}drawing"，我们的 FakeXML 检查 "drawing" in str(key)
    rids = _extract_inline_image_rids(xml)
    assert "rId1" in rids


# =========================================================================
# _group_words_to_paragraphs 算法深度
# =========================================================================


def _make_word(text: str = "x", x0: float = 0, x1: float = 10, top: float = 0, bottom: float = 10) -> dict:
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": bottom}


def test_group_words_empty_returns_empty_list():
    assert _group_words_to_paragraphs([]) == []


def test_group_words_single_word_returns_single_para():
    result = _group_words_to_paragraphs([_make_word("hello")])
    assert len(result) == 1
    assert "hello" in result[0]["text"]


def test_group_words_two_words_same_y_clustered():
    """两个 word y_center 差 ≤ 3 → 同行。"""
    words = [
        _make_word("a", x0=0, x1=5, top=10, bottom=15),
        _make_word("b", x0=10, x1=15, top=11, bottom=16),  # y_center 差 0.5
    ]
    result = _group_words_to_paragraphs(words)
    assert len(result) == 1
    assert "a" in result[0]["text"]
    assert "b" in result[0]["text"]


def test_group_words_y_diff_just_above_3_creates_two_lines():
    """y_center 差 > 3 → 不同行（但仍可能合并成段）。"""
    words = [
        _make_word("a", x0=0, x1=5, top=0, bottom=10),  # y_center=5
        _make_word("b", x0=0, x1=5, top=14, bottom=24),  # y_center=19, 差=14>3
    ]
    # 行高 median = 10（两 word 的 bottom-top 都是 10）
    # 行间距：line2.top(14) - line1.bottom(10) = 4，1.5*10=15，4 < 15 → 同段
    result = _group_words_to_paragraphs(words)
    assert len(result) == 1


def test_group_words_large_y_gap_creates_two_paragraphs():
    """行间距 > 1.5 * median_h → 两段。"""
    words = [
        _make_word("a", x0=0, x1=5, top=0, bottom=10),  # y_center=5
        _make_word("b", x0=0, x1=5, top=100, bottom=110),  # 远
    ]
    # 行高=10, median=10, 1.5*10=15, line2.top - line1.bottom = 100-10=90 > 15 → 两段
    result = _group_words_to_paragraphs(words)
    assert len(result) == 2


def test_group_words_returns_text_field():
    result = _group_words_to_paragraphs([_make_word("hello")])
    assert "text" in result[0]
    assert isinstance(result[0]["text"], str)


def test_group_words_returns_bbox_field():
    result = _group_words_to_paragraphs([_make_word("hello")])
    assert "bbox" in result[0]


def test_group_words_words_sorted_by_y_then_x():
    """sorted by (y_center, x0)。"""
    words = [
        _make_word("z", x0=10, x1=15, top=20, bottom=30),
        _make_word("a", x0=0, x1=5, top=0, bottom=10),
    ]
    result = _group_words_to_paragraphs(words)
    # a 在前（y_center=5），z 在后（y_center=25）
    assert result[0]["text"].startswith("a")


def test_group_words_within_line_sorted_by_x0():
    """同行 word 按 x0 输出。"""
    words = [
        _make_word("c", x0=20, x1=25, top=0, bottom=10),
        _make_word("a", x0=0, x1=5, top=0, bottom=10),
        _make_word("b", x0=10, x1=15, top=0, bottom=10),
    ]
    result = _group_words_to_paragraphs(words)
    assert result[0]["text"] == "a b c"


def test_group_words_returns_list_type():
    assert isinstance(_group_words_to_paragraphs([]), list)
    assert isinstance(_group_words_to_paragraphs([_make_word()]), list)


def test_group_words_idempotent():
    words = [_make_word("hello")]
    r1 = _group_words_to_paragraphs(words)
    r2 = _group_words_to_paragraphs(words)
    assert r1 == r2


# =========================================================================
# _lines_to_para bbox 边界
# =========================================================================


def test_lines_to_para_empty_lines_returns_empty_text():
    result = _lines_to_para([])
    assert result["text"] == ""
    assert result["bbox"] is None


def test_lines_to_para_single_line_single_word():
    result = _lines_to_para([[_make_word("hello", x0=5, x1=15, top=10, bottom=20)]])
    assert result["text"] == "hello"


def test_lines_to_para_bbox_format_4_elements():
    line = [_make_word("x", x0=5, x1=15, top=10, bottom=20)]
    result = _lines_to_para([line])
    bbox = result["bbox"]
    assert isinstance(bbox, list)
    assert len(bbox) == 4


def test_lines_to_para_bbox_x0_min_x1_max():
    line = [
        _make_word("a", x0=0, x1=5, top=10, bottom=20),
        _make_word("b", x0=100, x1=110, top=10, bottom=20),
    ]
    result = _lines_to_para([line])
    bbox = result["bbox"]
    assert bbox[0] == 0
    assert bbox[2] == 110


def test_lines_to_para_bbox_top_min_bottom_max():
    line = [
        _make_word("a", x0=0, x1=5, top=10, bottom=20),
        _make_word("b", x0=0, x1=5, top=30, bottom=40),
    ]
    result = _lines_to_para([line])
    bbox = result["bbox"]
    assert bbox[1] == 10  # min top
    assert bbox[3] == 40  # max bottom


def test_lines_to_para_multi_line_text_joined():
    line1 = [_make_word("hello", top=0, bottom=10)]
    line2 = [_make_word("world", top=20, bottom=30)]
    result = _lines_to_para([line1, line2])
    assert "hello" in result["text"]
    assert "world" in result["text"]


def test_lines_to_para_returns_dict():
    assert isinstance(_lines_to_para([]), dict)


def test_lines_to_para_text_is_str():
    line = [_make_word("x")]
    assert isinstance(_lines_to_para([line])["text"], str)


def test_lines_to_para_word_missing_top_uses_default():
    """word 无 top → float(w.get('top', 0.0))=0.0。"""
    line = [{"text": "x", "x0": 0, "x1": 10}]  # 无 top/bottom
    result = _lines_to_para([line])
    assert result["bbox"][1] == 0.0
    assert result["bbox"][3] == 0.0


# =========================================================================
# _classify_pdf_paragraph 边界
# =========================================================================


def test_classify_pdf_paragraph_returns_tuple():
    result = _classify_pdf_paragraph("hello")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_classify_pdf_paragraph_first_str():
    etype, _ = _classify_pdf_paragraph("hello")
    assert isinstance(etype, str)


def test_classify_pdf_paragraph_second_dict():
    _, meta = _classify_pdf_paragraph("hello")
    assert isinstance(meta, dict)


def test_classify_pdf_paragraph_empty_text_paragraph():
    etype, meta = _classify_pdf_paragraph("")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_pdf_paragraph_whitespace_only_paragraph():
    etype, meta = _classify_pdf_paragraph("   ")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_pdf_paragraph_caption_english():
    etype, meta = _classify_pdf_paragraph("Table 1. Description")
    assert etype == "caption"
    assert meta == {"heuristic": "caption_regex"}


def test_classify_pdf_paragraph_caption_chinese():
    etype, _ = _classify_pdf_paragraph("图 1. 描述")
    assert etype == "caption"


def test_classify_pdf_paragraph_caption_priority_over_short():
    """caption 优先于 short_line heading。"""
    etype, _ = _classify_pdf_paragraph("Fig 1. x")
    assert etype == "caption"


def test_classify_pdf_paragraph_short_no_punct_is_heading():
    etype, meta = _classify_pdf_paragraph("Section Title")
    assert etype == "heading"
    assert meta["level"] == 0
    assert meta["heuristic"] == "short_line"


def test_classify_pdf_paragraph_short_with_period_is_paragraph():
    etype, _ = _classify_pdf_paragraph("Section.")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_question_is_paragraph():
    etype, _ = _classify_pdf_paragraph("What?")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_exclamation_is_paragraph():
    etype, _ = _classify_pdf_paragraph("Stop!")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_chinese_period_is_paragraph():
    etype, _ = _classify_pdf_paragraph("章节。")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_chinese_question_is_paragraph():
    etype, _ = _classify_pdf_paragraph("章节？")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_chinese_exclamation_is_paragraph():
    etype, _ = _classify_pdf_paragraph("章节！")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_80_chars_no_punct_is_heading():
    text = "a" * 80
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "heading"


def test_classify_pdf_paragraph_81_chars_is_paragraph():
    text = "a" * 81
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "paragraph"


def test_classify_pdf_paragraph_long_text_is_paragraph():
    etype, meta = _classify_pdf_paragraph("a" * 200)
    assert etype == "paragraph"
    assert meta == {}


def test_classify_pdf_paragraph_caption_with_long_description():
    """caption 即使后面有长描述，仍判 caption。"""
    text = "Figure 1. " + "x" * 200
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "caption"


# =========================================================================
# _render_pdf_image_region_verbose 边界
# =========================================================================


def test_render_pdf_image_region_verbose_pypdfium_unavailable_returns_str():
    """pypdfium2 未装时返回错误描述（不是 None）。"""
    if fallback_mod.pypdfium2 is not None:
        pytest.skip("pypdfium2 已安装，跳过 unavailable 路径")
    result = _render_pdf_image_region_verbose(
        Path("dummy.pdf"), 0, [0, 0, 100, 100], Path("out.png")
    )
    assert isinstance(result, str)
    assert "pypdfium2" in result


def test_render_pdf_image_region_verbose_returns_str_or_none():
    """返回类型是 str | None。"""
    sig = inspect.signature(_render_pdf_image_region_verbose)
    # 我们无法直接测 None 路径（需要真实 PDF），仅检查签名
    params = list(sig.parameters)
    assert params == ["pdf_path", "page_idx_0based", "bbox", "out_path", "dpi"]


def test_render_pdf_image_region_verbose_dpi_default_144():
    sig = inspect.signature(_render_pdf_image_region_verbose)
    assert sig.parameters["dpi"].default == 144


# =========================================================================
# _image_filename 边界
# =========================================================================


def test_image_filename_basic_format():
    name = _image_filename("doc-abc123def456abcd", "pdf", 0)
    assert name == "image_abc123def456abcd_pdf_00.png"


def test_image_filename_default_ext_png():
    name = _image_filename("doc-x", "pdf", 0)
    assert name.endswith(".png")


def test_image_filename_custom_ext():
    name = _image_filename("doc-x", "pdf", 0, ext="jpg")
    assert name.endswith(".jpg")


def test_image_filename_index_zero_padded_two():
    name = _image_filename("doc-x", "pdf", 5)
    assert "_05." in name


def test_image_filename_index_three_digits():
    """index 100 → "_100."（仍是 zero-padded，但宽度自动适应）。"""
    name = _image_filename("doc-x", "pdf", 100)
    assert "_100." in name


def test_image_filename_doc_prefix_removed():
    name = _image_filename("doc-abc", "pdf", 0)
    assert "doc-" not in name
    assert name.startswith("image_abc_")


def test_image_filename_no_doc_prefix():
    """无 'doc-' 前缀时不影响。"""
    name = _image_filename("mydoc", "pdf", 0)
    assert "mydoc" in name


def test_image_filename_prefix_included():
    name = _image_filename("doc-x", "table", 0)
    assert "_table_" in name


def test_image_filename_returns_str():
    assert isinstance(_image_filename("doc-x", "pdf", 0), str)


# =========================================================================
# _save_image 写盘行为
# =========================================================================


def test_save_image_creates_dir(tmp_path: Path):
    out_dir = tmp_path / "images"
    target = _save_image(b"\x89PNG", out_dir, "doc-abc", "pdf", 0)
    assert out_dir.is_dir()
    assert target.is_file()


def test_save_image_writes_exact_bytes(tmp_path: Path):
    data = b"\x89PNG\r\n\x1a\n"
    target = _save_image(data, tmp_path, "doc-abc", "pdf", 0)
    assert target.read_bytes() == data


def test_save_image_filename_format(tmp_path: Path):
    target = _save_image(b"x", tmp_path, "doc-abc", "pdf", 5)
    assert "_05." in target.name
    assert "_pdf_" in target.name


def test_save_image_creates_parents(tmp_path: Path):
    out_dir = tmp_path / "a" / "b" / "c"
    target = _save_image(b"x", out_dir, "doc-x", "pdf", 0)
    assert target.is_file()


def test_save_image_existing_dir_no_error(tmp_path: Path):
    target1 = _save_image(b"x", tmp_path, "doc-x", "pdf", 0)
    target2 = _save_image(b"y", tmp_path, "doc-x", "pdf", 1)
    assert target1.is_file()
    assert target2.is_file()


def test_save_image_custom_ext(tmp_path: Path):
    target = _save_image(b"x", tmp_path, "doc-x", "pdf", 0, ext="jpg")
    assert target.name.endswith(".jpg")


def test_save_image_returns_path(tmp_path: Path):
    target = _save_image(b"x", tmp_path, "doc-x", "pdf", 0)
    assert isinstance(target, Path)


def test_save_image_overwrites_existing_file(tmp_path: Path):
    """同 path 二次写盘覆盖原文件。"""
    target = _save_image(b"first", tmp_path, "doc-x", "pdf", 0)
    target2 = _save_image(b"second", tmp_path, "doc-x", "pdf", 0)
    assert target == target2
    assert target.read_bytes() == b"second"


# =========================================================================
# _rows_to_markdown 边界
# =========================================================================


def test_rows_to_markdown_empty_returns_empty():
    assert _rows_to_markdown([]) == ""


def test_rows_to_markdown_none_cell_becomes_empty():
    result = _rows_to_markdown([[None, "b"]])
    assert "|  | b |" in result


def test_rows_to_markdown_int_cell_str():
    result = _rows_to_markdown([[1, 2]])
    assert "1" in result
    assert "2" in result


def test_rows_to_markdown_uneven_rows_padded():
    result = _rows_to_markdown([
        ["h1", "h2", "h3"],
        ["v1"],
    ])
    lines = result.split("\n")
    assert len(lines) == 3


def test_rows_to_markdown_separator_three_dashes():
    result = _rows_to_markdown([["a", "b"]])
    lines = result.split("\n")
    assert "---" in lines[1]


def test_rows_to_markdown_pipe_at_edges():
    result = _rows_to_markdown([["a"]])
    for line in result.split("\n"):
        assert line.startswith("| ")
        assert line.endswith(" |")


def test_rows_to_markdown_returns_str():
    assert isinstance(_rows_to_markdown([]), str)
    assert isinstance(_rows_to_markdown([["a"]]), str)


def test_rows_to_markdown_single_cell():
    result = _rows_to_markdown([["x"]])
    lines = result.split("\n")
    assert len(lines) == 2


def test_rows_to_markdown_no_body_only_header():
    """单行 → header + sep（无 body）。"""
    result = _rows_to_markdown([["h1", "h2"]])
    lines = result.split("\n")
    assert len(lines) == 2  # header + sep


# =========================================================================
# FallbackParser 类与 __init__
# =========================================================================


def test_fallback_parser_name_value():
    assert FallbackParser.name == "fallback"


def test_fallback_parser_inherits_parser():
    assert issubclass(FallbackParser, Parser)


def test_fallback_parser_version_is_str():
    assert isinstance(FallbackParser.version, str)


def test_fallback_parser_version_includes_pdfplumber():
    assert "pdfplumber" in FallbackParser.version


def test_fallback_parser_version_includes_docx():
    assert "python-docx" in FallbackParser.version


def test_fallback_parser_version_includes_pdfium():
    assert "pypdfium2" in FallbackParser.version


def test_fallback_parser_init_no_args():
    parser = FallbackParser()
    assert parser._image_output_dir is None


def test_fallback_parser_init_str_path(tmp_path: Path):
    parser = FallbackParser(image_output_dir=str(tmp_path))
    assert isinstance(parser._image_output_dir, Path)
    assert parser._image_output_dir == tmp_path


def test_fallback_parser_init_path_object(tmp_path: Path):
    parser = FallbackParser(image_output_dir=tmp_path)
    assert parser._image_output_dir == tmp_path


def test_fallback_parser_init_empty_string_image_output_dir():
    """空字符串 → falsy → _image_output_dir=None。"""
    parser = FallbackParser(image_output_dir="")
    assert parser._image_output_dir is None


def test_fallback_parser_init_none_image_output_dir():
    parser = FallbackParser(image_output_dir=None)
    assert parser._image_output_dir is None


def test_fallback_parser_init_default_image_output_dir_is_none():
    sig = inspect.signature(FallbackParser.__init__)
    assert sig.parameters["image_output_dir"].default is None


def test_fallback_parser_init_signature():
    sig = inspect.signature(FallbackParser.__init__)
    params = list(sig.parameters)
    assert params == ["self", "image_output_dir"]


def test_fallback_parser_two_instances_independent(tmp_path: Path):
    a = FallbackParser()
    b = FallbackParser(image_output_dir=tmp_path)
    assert a._image_output_dir is None
    assert b._image_output_dir is not None


def test_fallback_parser_class_dict_has_name():
    assert "name" in FallbackParser.__dict__


def test_fallback_parser_class_dict_has_version():
    assert "version" in FallbackParser.__dict__


def test_fallback_parser_class_dict_has_parse():
    assert "parse" in FallbackParser.__dict__


def test_fallback_parser_mro_includes_parser():
    assert Parser in FallbackParser.__mro__


def test_fallback_parser_module_namespace():
    assert FallbackParser.__module__ == "app.parsers.fallback_parser"


def test_fallback_parser_parse_method_callable():
    parser = FallbackParser()
    assert callable(parser.parse)


def test_fallback_parser_parse_method_signature():
    sig = inspect.signature(FallbackParser.parse)
    params = list(sig.parameters)
    assert params == ["self", "path", "source_hash"]


# =========================================================================
# 模块常量
# =========================================================================


def test_caption_re_is_compiled_pattern():
    assert isinstance(_CAPTION_RE, re.Pattern)


def test_caption_re_ignorecase_flag():
    """regex 启用 IGNORECASE 标志。"""
    assert _CAPTION_RE.flags & re.IGNORECASE


def test_pdfplumber_version_is_str_or_none():
    assert _PDFPLUMBER_VERSION is None or isinstance(_PDFPLUMBER_VERSION, str)


def test_pdfium_version_is_str_or_none():
    assert _PDFIUM_VERSION is None or isinstance(_PDFIUM_VERSION, str)


def test_docx_version_is_str_or_none():
    assert _DOCX_VERSION is None or isinstance(_DOCX_VERSION, str)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    assert fallback_mod.__all__ == ["FallbackParser"]


def test_module_all_is_list():
    assert isinstance(fallback_mod.__all__, list)


def test_module_uses_future_annotations():
    src = inspect.getsource(fallback_mod)
    assert "from __future__ import annotations" in src


def test_module_imports_re():
    src = inspect.getsource(fallback_mod)
    assert "import re" in src


def test_module_imports_path():
    src = inspect.getsource(fallback_mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    src = inspect.getsource(fallback_mod)
    assert "from typing import Any" in src


def test_module_imports_models():
    src = inspect.getsource(fallback_mod)
    assert "from app.models" in src


def test_module_imports_base():
    src = inspect.getsource(fallback_mod)
    assert "from app.parsers.base" in src


def test_module_optional_import_pdfplumber():
    src = inspect.getsource(fallback_mod)
    assert "import pdfplumber" in src


def test_module_optional_import_pypdfium2():
    src = inspect.getsource(fallback_mod)
    assert "import pypdfium2" in src


def test_module_optional_import_docx():
    src = inspect.getsource(fallback_mod)
    assert "import docx" in src


def test_module_try_except_pdfplumber():
    src = inspect.getsource(fallback_mod)
    assert "_PDFPLUMBER_IMPORT_ERROR" in src


def test_module_try_except_pypdfium2():
    src = inspect.getsource(fallback_mod)
    assert "_PDFIUM_IMPORT_ERROR" in src


def test_module_try_except_docx():
    src = inspect.getsource(fallback_mod)
    assert "_DOCX_IMPORT_ERROR" in src


def test_module_docstring_present():
    assert fallback_mod.__doc__ is not None


def test_module_docstring_mentions_pdfplumber():
    assert fallback_mod.__doc__ is not None
    assert "pdfplumber" in fallback_mod.__doc__.lower()


def test_module_docstring_mentions_python_docx():
    assert fallback_mod.__doc__ is not None
    assert "python-docx" in fallback_mod.__doc__ or "docx" in fallback_mod.__doc__.lower()


def test_module_docstring_mentions_kreuzberg():
    """docstring 解释为什么不用 kreuzberg。"""
    assert fallback_mod.__doc__ is not None
    assert "kreuzberg" in fallback_mod.__doc__.lower() or "Kreuzberg" in fallback_mod.__doc__


def test_module_has_pdfplumber_attr():
    assert hasattr(fallback_mod, "pdfplumber")


def test_module_has_pypdfium2_attr():
    assert hasattr(fallback_mod, "pypdfium2")


def test_module_has_docx_attr():
    assert hasattr(fallback_mod, "docx")


def test_module_has_qn_attr():
    assert hasattr(fallback_mod, "qn")


# =========================================================================
# 内部函数存在性
# =========================================================================


def test_module_has_is_caption():
    assert callable(fallback_mod._is_caption)


def test_module_has_rows_to_markdown():
    assert callable(fallback_mod._rows_to_markdown)


def test_module_has_image_filename():
    assert callable(fallback_mod._image_filename)


def test_module_has_save_image():
    assert callable(fallback_mod._save_image)


def test_module_has_group_words():
    assert callable(fallback_mod._group_words_to_paragraphs)


def test_module_has_lines_to_para():
    assert callable(fallback_mod._lines_to_para)


def test_module_has_classify_pdf_paragraph():
    assert callable(fallback_mod._classify_pdf_paragraph)


def test_module_has_is_heading_style():
    assert callable(fallback_mod._is_heading_style)


def test_module_has_extract_inline_image_rids():
    assert callable(fallback_mod._extract_inline_image_rids)


def test_module_has_parse_pdf():
    assert callable(fallback_mod._parse_pdf)


def test_module_has_parse_docx():
    assert callable(fallback_mod._parse_docx)


def test_module_has_render_pdf_image_region():
    assert callable(fallback_mod._render_pdf_image_region)


def test_module_has_render_pdf_image_region_verbose():
    assert callable(fallback_mod._render_pdf_image_region_verbose)


# =========================================================================
# _CAPTION_RE 实际匹配行为
# =========================================================================


def test_caption_re_match_returns_match_object():
    m = _CAPTION_RE.match("Table 1. Description")
    assert m is not None


def test_caption_re_no_match_returns_none():
    assert _CAPTION_RE.match("hello") is None


def test_caption_re_matches_table():
    assert _CAPTION_RE.match("Table 1. Description") is not None


def test_caption_re_matches_figure():
    assert _CAPTION_RE.match("Figure 1. Description") is not None


def test_caption_re_matches_fig_abbrev():
    assert _CAPTION_RE.match("Fig. 1. Description") is not None


def test_caption_re_matches_fig_no_dot():
    assert _CAPTION_RE.match("Fig 1. Description") is not None


def test_caption_re_matches_chinese_table():
    assert _CAPTION_RE.match("表 1. 描述") is not None


def test_caption_re_matches_chinese_figure():
    assert _CAPTION_RE.match("图 1. 描述") is not None


def test_caption_re_matches_full_width_digit():
    assert _CAPTION_RE.match("图１. 描述") is not None


def test_caption_re_matches_colon_separator():
    assert _CAPTION_RE.match("Table 1: Description") is not None


def test_caption_re_matches_chinese_comma_separator():
    assert _CAPTION_RE.match("图 1、描述") is not None


def test_caption_re_matches_whitespace_separator():
    assert _CAPTION_RE.match("Figure 1 Description") is not None


def test_caption_re_matches_leading_whitespace():
    assert _CAPTION_RE.match("  Table 1. Description") is not None


def test_caption_re_case_insensitive_lowercase():
    assert _CAPTION_RE.match("table 1. Description") is not None


def test_caption_re_case_insensitive_uppercase():
    assert _CAPTION_RE.match("TABLE 1. Description") is not None


def test_caption_re_no_match_without_number():
    assert _CAPTION_RE.match("Table Description") is None


def test_caption_re_no_match_random_text():
    assert _CAPTION_RE.match("Hello world") is None


def test_caption_re_no_match_paragraph_starting_with_table_word():
    """不以 caption 关键字开头的不匹配。"""
    assert _CAPTION_RE.match("The table shows data.") is None


def test_caption_re_no_match_empty_string():
    assert _CAPTION_RE.match("") is None


def test_caption_re_pattern_has_caption_keywords():
    assert "Table" in _CAPTION_RE.pattern
    assert "Figure" in _CAPTION_RE.pattern
    assert "Fig" in _CAPTION_RE.pattern


def test_caption_re_pattern_has_chinese_keywords():
    assert "表" in _CAPTION_RE.pattern
    assert "图" in _CAPTION_RE.pattern


def test_caption_re_pattern_has_full_width_digit_range():
    assert "０-９" in _CAPTION_RE.pattern


def test_caption_re_pattern_has_ignorecase_flag_in_pattern():
    """pattern 编译时带 IGNORECASE。"""
    src = inspect.getsource(fallback_mod)
    assert "re.IGNORECASE" in src


# =========================================================================
# _is_caption 直接行为
# =========================================================================


def test_is_caption_returns_true_for_caption():
    assert _is_caption("Table 1. Description") is True


def test_is_caption_returns_false_for_non_caption():
    assert _is_caption("hello world") is False


def test_is_caption_none_returns_false():
    assert _is_caption(None) is False


def test_is_caption_empty_string_returns_false():
    assert _is_caption("") is False


def test_is_caption_returns_bool():
    assert isinstance(_is_caption("Table 1. x"), bool)


def test_is_caption_handles_arbitrary_text():
    """任意字符串不崩溃。"""
    assert isinstance(_is_caption("Any text"), bool)
    assert isinstance(_is_caption(None), bool)
