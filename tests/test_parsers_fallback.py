"""app/parsers/fallback_parser.py 内部 helper 的单元测试。

只覆盖纯函数 helper（不依赖 pdfplumber / python-docx 实际打开文件）：
- _is_caption / _CAPTION_RE：题注启发式
- _rows_to_markdown：表格 markdown 渲染
- _image_filename：图片资源命名
- _group_words_to_paragraphs：pdfplumber word 聚合（synthetic words）
- _lines_to_para：行融合为段落
- _classify_pdf_paragraph：PDF 段落启发式分类
- _is_heading_style：DOCX heading 样式识别
- FallbackParser.__init__ / name / version / 错误路径

实际 PDF/DOCX 解析走 test_pipeline_integration.py 与 test_pipeline_errors.py。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.parsers.base import ParserError
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
    _rows_to_markdown,
)


# ---------- _is_caption / _CAPTION_RE ----------


def test_is_caption_table_english():
    assert _is_caption("Table 1. Some description") is True


def test_is_caption_figure_english():
    assert _is_caption("Figure 1: Diagram") is True


def test_is_caption_fig_abbrev():
    assert _is_caption("Fig. 1 Diagram") is True


def test_is_caption_fig_no_period():
    assert _is_caption("Fig 1 Diagram") is True


def test_is_caption_chinese_table():
    assert _is_caption("表 1 描述") is True


def test_is_caption_chinese_figure():
    assert _is_caption("图 1 描述") is True


def test_is_caption_chinese_full_width_digit():
    """全宽数字 ０-９ 也接受。"""
    assert _is_caption("表 １ 描述") is True


def test_is_caption_returns_false_for_plain_text():
    assert _is_caption("This is a normal paragraph.") is False


def test_is_caption_returns_false_for_empty_string():
    assert _is_caption("") is False


def test_is_caption_returns_false_for_none():
    assert _is_caption(None) is False  # type: ignore[arg-type]


def test_is_caption_case_insensitive():
    assert _is_caption("TABLE 1: stuff") is True
    assert _is_caption("figure 1. stuff") is True


def test_is_caption_without_number_not_matched():
    assert _is_caption("Table of contents") is False


def test_is_caption_with_colon_separator():
    assert _is_caption("Figure 2: chart") is True


def test_is_caption_with_chinese_comma_separator():
    assert _is_caption("图 1、示意图") is True


def test_caption_re_is_a_compiled_pattern():
    import re
    assert isinstance(_CAPTION_RE, re.Pattern)


# ---------- _rows_to_markdown ----------


def test_rows_to_markdown_empty_returns_empty_string():
    assert _rows_to_markdown([]) == ""


def test_rows_to_markdown_header_only():
    md = _rows_to_markdown([["a", "b"]])
    assert md == "| a | b |\n| --- | --- |"


def test_rows_to_markdown_with_one_body_row():
    md = _rows_to_markdown([["a", "b"], ["1", "2"]])
    assert md == "| a | b |\n| --- | --- |\n| 1 | 2 |"


def test_rows_to_markdown_with_two_body_rows():
    md = _rows_to_markdown([["h"], ["r1"], ["r2"]])
    assert md == "| h |\n| --- |\n| r1 |\n| r2 |"


def test_rows_to_markdown_none_cells_become_empty():
    md = _rows_to_markdown([[None, "x"], [None, None]])
    assert "|  | x |" in md
    assert "|  |  |" in md


def test_rows_to_markdown_int_cells_converted_to_str():
    md = _rows_to_markdown([[1, 2], [3, 4]])
    assert "| 1 | 2 |" in md
    assert "| 3 | 4 |" in md


def test_rows_to_markdown_jagged_rows_padded_with_empty():
    md = _rows_to_markdown([["a", "b", "c"], ["x"], ["y", "z"]])
    # 第二行 pad 到 3 列
    assert "| x |  |  |" in md
    assert "| y | z |  |" in md


def test_rows_to_markdown_returns_str_type():
    assert isinstance(_rows_to_markdown([["a"]]), str)


# ---------- _image_filename ----------


def test_image_filename_basic_format():
    name = _image_filename("doc-abcdef0123456789", "p1", 0)
    assert name == "image_abcdef0123456789_p1_00.png"


def test_image_filename_index_zero_padded_two_digits():
    assert _image_filename("doc-xyz", "para0", 0).endswith("_para0_00.png")
    assert _image_filename("doc-xyz", "para0", 5).endswith("_para0_05.png")
    assert _image_filename("doc-xyz", "para0", 9).endswith("_para0_09.png")


def test_image_filename_index_two_digits_no_extra_pad():
    """index 用 {index:02d} 格式，10/99 都不额外补 0。"""
    assert _image_filename("doc-xyz", "p1", 10).endswith("_p1_10.png")
    assert _image_filename("doc-xyz", "p1", 99).endswith("_p1_99.png")


def test_image_filename_strips_doc_prefix():
    name = _image_filename("doc-abc123", "p2", 3)
    assert name.startswith("image_abc123_")


def test_image_filename_custom_extension():
    name = _image_filename("doc-abc", "p1", 0, "jpg")
    assert name.endswith(".jpg")
    assert not name.endswith(".png")


def test_image_filename_default_extension_is_png():
    name = _image_filename("doc-abc", "p1", 0)
    assert name.endswith(".png")


# ---------- _group_words_to_paragraphs ----------


def _word(text: str, x0: float, top: float, x1: float, bottom: float) -> dict:
    """构造 pdfplumber 风格的 word dict。"""
    return {"text": text, "x0": x0, "top": top, "x1": x1, "bottom": bottom}


def test_group_words_to_paragraphs_empty_input():
    assert _group_words_to_paragraphs([]) == []


def test_group_words_to_paragraphs_single_word():
    words = [_word("hello", 0.0, 0.0, 50.0, 12.0)]
    result = _group_words_to_paragraphs(words)
    assert len(result) == 1
    assert result[0]["text"] == "hello"


def test_group_words_to_paragraphs_two_words_same_line():
    """两个 word 在同一行（y_center 接近）→ 一个段落。"""
    words = [
        _word("hello", 0.0, 0.0, 50.0, 12.0),
        _word("world", 55.0, 0.0, 100.0, 12.0),
    ]
    result = _group_words_to_paragraphs(words)
    assert len(result) == 1
    assert "hello" in result[0]["text"]
    assert "world" in result[0]["text"]


def test_group_words_to_paragraphs_two_words_different_lines_same_para():
    """两行紧邻（line_top - last_bottom <= 1.5 * median_h）→ 同一段。"""
    words = [
        _word("line1", 0.0, 0.0, 50.0, 12.0),
        _word("line2", 0.0, 14.0, 50.0, 26.0),  # 行距 2，远小于 1.5 * 12
    ]
    result = _group_words_to_paragraphs(words)
    assert len(result) == 1
    assert "line1" in result[0]["text"]
    assert "line2" in result[0]["text"]


def test_group_words_to_paragraphs_two_paragraphs_when_large_gap():
    """两行间距 > 1.5 * median_h → 分两段。"""
    words = [
        _word("para1line", 0.0, 0.0, 50.0, 12.0),
        _word("para2line", 0.0, 100.0, 50.0, 112.0),  # 行距 88，远超 1.5 * 12 = 18
    ]
    result = _group_words_to_paragraphs(words)
    assert len(result) == 2


def test_group_words_to_paragraphs_returns_bbox():
    """每个段落含 bbox 字段（[x0, top, x1, bottom]）。"""
    words = [
        _word("a", 5.0, 5.0, 15.0, 17.0),
        _word("b", 20.0, 5.0, 30.0, 17.0),
    ]
    result = _group_words_to_paragraphs(words)
    assert len(result) == 1
    bbox = result[0]["bbox"]
    assert bbox is not None
    assert bbox[0] == 5.0  # x0 最小
    assert bbox[1] == 5.0  # top 最小
    assert bbox[2] == 30.0  # x1 最大
    assert bbox[3] == 17.0  # bottom 最大


def test_group_words_to_paragraphs_sorts_words_within_line_by_x0():
    """同行内 word 按 x0 排序，不依赖输入顺序。"""
    words = [
        _word("second", 60.0, 0.0, 120.0, 12.0),
        _word("first", 0.0, 0.0, 50.0, 12.0),
    ]
    result = _group_words_to_paragraphs(words)
    text = result[0]["text"]
    # first 应该出现在 second 之前
    assert text.index("first") < text.index("second")


# ---------- _lines_to_para ----------


def test_lines_to_para_empty_lines_returns_empty_text():
    result = _lines_to_para([])
    assert result["text"] == ""
    assert result["bbox"] is None


def test_lines_to_para_single_line_single_word():
    line = [_word("hello", 0.0, 0.0, 50.0, 12.0)]
    result = _lines_to_para([line])
    assert result["text"] == "hello"
    assert result["bbox"] == [0.0, 0.0, 50.0, 12.0]


def test_lines_to_para_multi_line_text_concatenated():
    """多行 word 在文本中按 line 顺序拼接。"""
    line1 = [_word("a", 0.0, 0.0, 10.0, 12.0)]
    line2 = [_word("b", 0.0, 14.0, 10.0, 26.0)]
    result = _lines_to_para([line1, line2])
    assert "a" in result["text"]
    assert "b" in result["text"]
    # 文本里 "a" 在 "b" 之前
    assert result["text"].index("a") < result["text"].index("b")


def test_lines_to_para_bbox_aggregates_across_lines():
    line1 = [_word("a", 5.0, 5.0, 15.0, 17.0)]
    line2 = [_word("b", 10.0, 25.0, 20.0, 37.0)]
    result = _lines_to_para([line1, line2])
    bbox = result["bbox"]
    assert bbox[0] == 5.0  # min x0
    assert bbox[1] == 5.0  # min top
    assert bbox[2] == 20.0  # max x1
    assert bbox[3] == 37.0  # max bottom


# ---------- _classify_pdf_paragraph ----------


def test_classify_pdf_paragraph_empty_string_returns_paragraph():
    etype, meta = _classify_pdf_paragraph("")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_pdf_paragraph_caption_returns_caption():
    etype, meta = _classify_pdf_paragraph("Table 1. Some data")
    assert etype == "caption"
    assert meta == {"heuristic": "caption_regex"}


def test_classify_pdf_paragraph_short_no_period_returns_heading():
    """短文本（<=80）且不以句号结尾 → heading。"""
    etype, meta = _classify_pdf_paragraph("Introduction")
    assert etype == "heading"
    assert meta["level"] == 0
    assert meta["heuristic"] == "short_line"


def test_classify_pdf_paragraph_short_with_period_returns_paragraph():
    etype, meta = _classify_pdf_paragraph("Done.")  # 5 字符，以 . 结尾
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_chinese_period_returns_paragraph():
    etype, meta = _classify_pdf_paragraph("完成。")  # 以中文句号结尾
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_question_mark_returns_paragraph():
    etype, meta = _classify_pdf_paragraph("Why?")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_exclamation_returns_paragraph():
    etype, meta = _classify_pdf_paragraph("Hi!")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_long_line_returns_paragraph():
    long_text = "a" * 100  # > 80
    etype, _ = _classify_pdf_paragraph(long_text)
    assert etype == "paragraph"


def test_classify_pdf_paragraph_caption_overrides_short_line():
    """caption 是 caption，不会因为短就变成 heading。

    注：caption regex 要求数字后跟分隔符（. 、 : 空白），所以 "Fig 1." 才匹配。
    """
    etype, meta = _classify_pdf_paragraph("Fig 1.")
    assert etype == "caption"


def test_classify_pdf_paragraph_strips_whitespace_first():
    """带前导空白的 caption 也要识别。"""
    etype, _ = _classify_pdf_paragraph("   Table 1. Data")
    assert etype == "caption"


# ---------- _is_heading_style ----------


def test_is_heading_style_none_returns_false():
    is_h, level = _is_heading_style(None)
    assert is_h is False
    assert level == 0


def test_is_heading_style_empty_string_returns_false():
    is_h, level = _is_heading_style("")
    assert is_h is False
    assert level == 0


def test_is_heading_style_title_returns_level_1():
    is_h, level = _is_heading_style("Title")
    assert is_h is True
    assert level == 1


def test_is_heading_style_title_case_insensitive():
    is_h, level = _is_heading_style("TITLE")
    assert is_h is True
    assert level == 1


def test_is_heading_style_heading_1():
    is_h, level = _is_heading_style("Heading 1")
    assert is_h is True
    assert level == 1


def test_is_heading_style_heading_2():
    is_h, level = _is_heading_style("Heading 2")
    assert is_h is True
    assert level == 2


def test_is_heading_style_heading_3():
    is_h, level = _is_heading_style("Heading 3")
    assert is_h is True
    assert level == 3


def test_is_heading_style_heading_with_whitespace_padding():
    is_h, level = _is_heading_style("  Heading 4  ")
    assert is_h is True
    assert level == 4


def test_is_heading_style_heading_lowercase():
    is_h, level = _is_heading_style("heading 5")
    assert is_h is True
    assert level == 5


def test_is_heading_style_heading_no_level_falls_back_to_1():
    """'Heading' 不带数字 → ValueError 路径 → 返回 level=1。"""
    is_h, level = _is_heading_style("Heading")
    assert is_h is True
    assert level == 1


def test_is_heading_style_heading_with_garbage_suffix_falls_back_to_1():
    """'Heading abc' → int() 失败 → level=1。"""
    is_h, level = _is_heading_style("Heading abc")
    assert is_h is True
    assert level == 1


def test_is_heading_style_heading_zero_clamped_to_one():
    """'Heading 0' → max(1, 0) = 1。"""
    is_h, level = _is_heading_style("Heading 0")
    assert is_h is True
    assert level == 1


def test_is_heading_style_heading_negative_clamped_to_one():
    is_h, level = _is_heading_style("Heading -1")
    # int('-1') → -1, max(1, -1) = 1
    assert is_h is True
    assert level == 1


def test_is_heading_style_normal_paragraph_returns_false():
    is_h, level = _is_heading_style("Normal")
    assert is_h is False
    assert level == 0


def test_is_heading_style_body_text_returns_false():
    is_h, level = _is_heading_style("Body Text")
    assert is_h is False
    assert level == 0


def test_is_heading_style_subtitle_returns_false():
    """subtitle 不算 heading（不匹配 'title' 也不匹配 'heading'）。"""
    is_h, level = _is_heading_style("Subtitle")
    assert is_h is False
    assert level == 0


# ---------- _extract_inline_image_rids（轻量级，需要 qn） ----------


def test_extract_inline_image_rids_empty_xml_returns_empty():
    """无 drawing 元素的 XML → 空列表。"""
    from docx.oxml.ns import qn
    from lxml import etree

    # 简单的 <w:p></w:p>
    nsmap = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    p = etree.Element(qn("w:p"))
    rids = _extract_inline_image_rids(p)
    assert rids == []


def test_extract_inline_image_rids_finds_embedded_image():
    """构造含 a:blip r:embed 的 XML → 提取 rId。"""
    from docx.oxml.ns import qn
    from lxml import etree

    xml = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                    xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
        <w:r><w:drawing>
            <a:blip r:embed="rId123"/>
        </w:drawing></w:r>
    </w:p>"""
    p = etree.fromstring(xml)
    rids = _extract_inline_image_rids(p)
    assert rids == ["rId123"]


def test_extract_inline_image_rids_multiple_images():
    from docx.oxml.ns import qn
    from lxml import etree

    xml = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                    xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
        <w:r><w:drawing><a:blip r:embed="rId1"/></w:drawing></w:r>
        <w:r><w:drawing><a:blip r:embed="rId2"/></w:drawing></w:r>
    </w:p>"""
    p = etree.fromstring(xml)
    rids = _extract_inline_image_rids(p)
    assert rids == ["rId1", "rId2"]


def test_extract_inline_image_rids_uses_link_when_no_embed():
    """无 r:embed 时，回退到 r:link。"""
    from lxml import etree

    xml = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                    xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
        <w:r><w:drawing><a:blip r:link="rIdLink"/></w:drawing></w:r>
    </w:p>"""
    p = etree.fromstring(xml)
    rids = _extract_inline_image_rids(p)
    assert rids == ["rIdLink"]


def test_extract_inline_image_rids_no_blip_returns_empty():
    """drawing 元素但无 blip → 空列表。"""
    from lxml import etree

    xml = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                    xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
        <w:r><w:drawing><a:sp/></w:drawing></w:r>
    </w:p>"""
    p = etree.fromstring(xml)
    rids = _extract_inline_image_rids(p)
    assert rids == []


# ---------- FallbackParser 类基础契约 ----------


def test_fallback_parser_name_constant():
    assert FallbackParser.name == "fallback"


def test_fallback_parser_version_includes_pdfplumber():
    """version 字符串含 pdfplumber 版本（具体版本随环境）。"""
    assert "pdfplumber=" in FallbackParser.version
    assert "python-docx=" in FallbackParser.version
    assert "pypdfium2=" in FallbackParser.version


def test_fallback_parser_init_default_no_image_dir():
    parser = FallbackParser()
    assert parser._image_output_dir is None


def test_fallback_parser_init_with_image_dir_str(tmp_path: Path):
    parser = FallbackParser(image_output_dir=str(tmp_path))
    assert parser._image_output_dir == tmp_path


def test_fallback_parser_init_with_image_dir_path(tmp_path: Path):
    parser = FallbackParser(image_output_dir=tmp_path)
    assert parser._image_output_dir == tmp_path


def test_fallback_parser_init_inherits_from_parser():
    from app.parsers.base import Parser
    parser = FallbackParser()
    assert isinstance(parser, Parser)


def test_fallback_parser_missing_file_raises(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(tmp_path / "nope.pdf", source_hash="a" * 64)
    assert exc.value.code == "file_not_found"


def test_fallback_parser_missing_file_error_details(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(tmp_path / "missing.docx", source_hash="a" * 64)
    assert "path" in exc.value.details
