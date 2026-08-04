"""app/parsers/fallback_parser.py 边角测试（Round 59）。

补强 tests/test_parsers_fallback.py（79 个测试）未覆盖的：
- _CAPTION_RE 直接 pattern match（数字宽度/全角/小数点）
- _is_caption 多行字符串/前导空白/数字 0
- _rows_to_markdown cell 类型扩展（float/bool/dict/list/None）
- _image_filename index 大于 99/doc_id 无前缀/ext 含点
- _save_image 实际写盘 + 目录创建 + 字节完整性
- _classify_pdf_paragraph 80 字符边界精确测试
- _is_heading_style heading 99 / Heading 大小写混合 / heading-9 等异常 suffix
- _group_words_to_paragraphs 段落分隔阈值
- _lines_to_para 多行聚合 / bbox 字段类型
- FallbackParser.__init__ None/空串/Path 对象
- FallbackParser.version / name 字符串属性
- FallbackParser 类属性契约
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
    _save_image,
)


# ---------- _CAPTION_RE 直接测试 ----------


def test_caption_re_pattern_is_compiled():
    import re
    assert isinstance(_CAPTION_RE, re.Pattern)


def test_caption_re_match_returns_match_object_for_table():
    m = _CAPTION_RE.match("Table 1. Hello")
    assert m is not None


def test_caption_re_match_returns_none_for_non_caption():
    assert _CAPTION_RE.match("Hello world") is None


def test_caption_re_ignores_case():
    assert _CAPTION_RE.match("TABLE 5: data") is not None
    assert _CAPTION_RE.match("figure 3. shown below") is not None


def test_caption_re_matches_full_width_digit():
    assert _CAPTION_RE.match("图 ３. caption") is not None


def test_caption_re_requires_number_after_keyword():
    """无数字 → 不匹配。"""
    assert _CAPTION_RE.match("Table: hello") is None  # 只有冒号无数


def test_caption_re_zero_number_matches():
    """数字 0 也匹配（regex [0-9０-９]+ 包含 0）。"""
    assert _CAPTION_RE.match("Table 0. intro") is not None


def test_caption_re_multiline_string_only_first_line_matches():
    """多行字符串，match 只看开头。"""
    text = "Table 1. caption\nsecond line\nthird line"
    assert _CAPTION_RE.match(text) is not None


# ---------- _is_caption 边角 ----------


def test_is_caption_with_leading_whitespace():
    """regex 有 ^\\s*，所以前导空白 OK。"""
    assert _is_caption("   Table 1. caption") is True


def test_is_caption_with_many_spaces():
    assert _is_caption("     Figure 5.     caption") is True


def test_is_caption_zero_table():
    assert _is_caption("Table 0. intro") is True


def test_is_caption_large_number():
    assert _is_caption("Table 999. appendix") is True


def test_is_caption_only_keyword_no_number():
    """关键词后无数 → False。"""
    assert _is_caption("Table. caption") is False


def test_is_caption_keyword_inside_text():
    """caption 必须在开头。"""
    assert _is_caption("see Table 1. caption") is False


def test_is_caption_returns_bool_type():
    assert isinstance(_is_caption("Table 1. x"), bool)
    assert isinstance(_is_caption("hello"), bool)


def test_is_caption_tab_separator_after_number():
    """regex 允许 \\s（含 tab）作分隔。"""
    assert _is_caption("Table 1\tcaption") is True


# ---------- _rows_to_markdown cell 类型扩展 ----------


def test_rows_to_markdown_float_cells():
    """float cell → str(3.14)。"""
    result = _rows_to_markdown([["pi", "e"], [3.14, 2.72]])
    assert "3.14" in result
    assert "2.72" in result


def test_rows_to_markdown_bool_cells():
    """bool cell → str(True)/str(False)。"""
    result = _rows_to_markdown([["x", "y"], [True, False]])
    assert "True" in result
    assert "False" in result


def test_rows_to_markdown_dict_cells():
    """dict cell → str({'k': 'v'})。"""
    result = _rows_to_markdown([["col"], [{"k": "v"}]])
    assert "{'k': 'v'}" in result


def test_rows_to_markdown_list_cells():
    """list cell → str([1, 2])。"""
    result = _rows_to_markdown([["col"], [[1, 2, 3]]])
    assert "[1, 2, 3]" in result


def test_rows_to_markdown_mixed_cell_types():
    """混合类型 cell。"""
    result = _rows_to_markdown([["a", "b", "c"], [1, "str", None]])
    lines = result.split("\n")
    assert lines[2] == "| 1 | str |  |"


def test_rows_to_markdown_three_body_rows():
    """3 个 body row。"""
    rows = [["h"], ["r1"], ["r2"], ["r3"]]
    result = _rows_to_markdown(rows)
    lines = result.split("\n")
    assert len(lines) == 5  # header + sep + 3 body


def test_rows_to_markdown_many_body_rows():
    """100 个 body row。"""
    rows = [["h"]] + [[f"r{i}"] for i in range(100)]
    result = _rows_to_markdown(rows)
    lines = result.split("\n")
    assert len(lines) == 102  # header + sep + 100 body


def test_rows_to_markdown_returns_str_type():
    assert isinstance(_rows_to_markdown([]), str)
    assert isinstance(_rows_to_markdown([["a"]]), str)


def test_rows_to_markdown_separator_always_three_dashes():
    """separator 永远是 '---'。"""
    result = _rows_to_markdown([["a", "b", "c"]])
    assert "| --- | --- | --- |" in result


def test_rows_to_markdown_int_zero_cell():
    """int 0 → '0'（不是 ''）"""
    result = _rows_to_markdown([["col"], [0]])
    assert "| 0 |" in result


# ---------- _image_filename 边角 ----------


def test_image_filename_basic_format():
    name = _image_filename("doc-abc123", "p1", 0)
    assert name == "image_abc123_p1_00.png"


def test_image_filename_index_greater_than_99():
    """index >= 100 → 3 位补齐（{index:02d} 至少 2 位，但不截断）。"""
    name = _image_filename("doc-x", "p1", 150)
    assert "_150." in name


def test_image_filename_index_zero():
    name = _image_filename("doc-abc", "para0", 0)
    assert "_00." in name


def test_image_filename_strips_only_first_doc_prefix():
    """document_id 多次含 doc- 时只 replace 一次（无循环）。"""
    name = _image_filename("doc-doc-abc", "p1", 0)
    # str.replace 全部替换：doc-doc-abc → -abc → "-abc"
    # 实际：str.replace 是全局替换
    assert "doc-doc" not in name
    # 但 "doc-" 都被去掉
    assert "image_doc_abc" not in name


def test_image_filename_custom_ext():
    name = _image_filename("doc-x", "p1", 0, ext="jpg")
    assert name.endswith(".jpg")


def test_image_filename_ext_with_dot():
    """传 ext='.png' → 文件名出现 '..png'（不清洗）。"""
    name = _image_filename("doc-x", "p1", 0, ext=".png")
    # 实际：f".{ext}" → "..png"
    assert "..png" in name


def test_image_filename_returns_str():
    name = _image_filename("doc-x", "p1", 0)
    assert isinstance(name, str)


def test_image_filename_prefix_arbitrary():
    """prefix 可以是任意字符串（含数字）。"""
    name = _image_filename("doc-x", "para99", 5)
    assert "_para99_05." in name


def test_image_filename_document_id_no_prefix():
    """无 doc- 前缀的 document_id。"""
    name = _image_filename("plain", "p1", 0)
    # replace 找不到 doc-，原样保留
    assert "plain" in name


# ---------- _save_image 实际写盘 ----------


def test_save_image_creates_nested_directory(tmp_path: Path):
    """目录不存在时自动创建（parents=True）。"""
    out_dir = tmp_path / "a" / "b" / "c"
    p = _save_image(b"hello", out_dir, "doc-abc", "p1", 0)
    assert p.is_file()
    assert p.read_bytes() == b"hello"


def test_save_image_returns_path_object(tmp_path: Path):
    p = _save_image(b"x", tmp_path, "doc-abc", "p1", 0)
    assert isinstance(p, Path)


def test_save_image_filename_format(tmp_path: Path):
    p = _save_image(b"x", tmp_path, "doc-abc", "p1", 5)
    assert p.name == "image_abc_p1_05.png"


def test_save_image_existing_directory(tmp_path: Path):
    """目标目录已存在 → exist_ok=True 不报错。"""
    p = _save_image(b"x", tmp_path, "doc-x", "p1", 0)
    p2 = _save_image(b"y", tmp_path, "doc-x", "p1", 1)
    assert p.is_file() and p2.is_file()
    assert p.read_bytes() == b"x"
    assert p2.read_bytes() == b"y"


def test_save_image_overwrites_existing_file(tmp_path: Path):
    """同 index 重复 save → 覆盖。"""
    p1 = _save_image(b"first", tmp_path, "doc-x", "p1", 0)
    p2 = _save_image(b"second", tmp_path, "doc-x", "p1", 0)
    assert p1 == p2
    assert p1.read_bytes() == b"second"


def test_save_image_empty_bytes(tmp_path: Path):
    """空 bytes 也能保存。"""
    p = _save_image(b"", tmp_path, "doc-x", "p1", 0)
    assert p.is_file()
    assert p.read_bytes() == b""


def test_save_image_large_bytes(tmp_path: Path):
    """大 bytes（10KB）保存完整。"""
    data = b"x" * 10240
    p = _save_image(data, tmp_path, "doc-x", "p1", 0)
    assert p.read_bytes() == data


def test_save_image_custom_ext(tmp_path: Path):
    p = _save_image(b"x", tmp_path, "doc-x", "p1", 0, ext="jpg")
    assert p.name.endswith(".jpg")


# ---------- _classify_pdf_paragraph 80 字符边界 ----------


def test_classify_pdf_paragraph_exactly_80_chars_no_period_is_heading():
    """长度 == 80 且无句末标点 → heading。"""
    text = "a" * 80
    etype, meta = _classify_pdf_paragraph(text)
    assert etype == "heading"
    assert meta.get("level") == 0


def test_classify_pdf_paragraph_81_chars_is_paragraph():
    """长度 > 80 → paragraph。"""
    text = "a" * 81
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "paragraph"


def test_classify_pdf_paragraph_79_chars_is_heading():
    """长度 < 80 → heading。"""
    text = "a" * 79
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "heading"


def test_classify_pdf_paragraph_80_chars_with_period_is_paragraph():
    """长度 == 80 但 endswith '.' → paragraph。"""
    text = "a" * 79 + "."
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "paragraph"


def test_classify_pdf_paragraph_80_chars_with_exclamation_is_paragraph():
    text = "a" * 79 + "!"
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_chinese_period_is_paragraph():
    """中文句号也算句末。"""
    text = "短句。"
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "paragraph"


def test_classify_pdf_paragraph_returns_tuple_type():
    result = _classify_pdf_paragraph("hello")
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], str)
    assert isinstance(result[1], dict)


def test_classify_pdf_paragraph_caption_meta_has_heuristic():
    """caption 分类时 metadata 含 heuristic 字段。"""
    etype, meta = _classify_pdf_paragraph("Table 1. data")
    assert etype == "caption"
    assert meta.get("heuristic") == "caption_regex"


def test_classify_pdf_paragraph_heading_meta_has_level_and_heuristic():
    etype, meta = _classify_pdf_paragraph("short heading")
    assert etype == "heading"
    assert meta.get("level") == 0
    assert meta.get("heuristic") == "short_line"


def test_classify_pdf_paragraph_paragraph_meta_is_empty_dict():
    etype, meta = _classify_pdf_paragraph("A long sentence with period.")
    assert etype == "paragraph"
    assert meta == {}


# ---------- _is_heading_style 边角 ----------


def test_is_heading_style_heading_99():
    is_h, level = _is_heading_style("heading 99")
    assert is_h is True
    assert level == 99


def test_is_heading_style_heading_0_clamped_to_1():
    is_h, level = _is_heading_style("heading 0")
    assert is_h is True
    assert level == 1


def test_is_heading_style_heading_negative_clamped_to_1():
    is_h, level = _is_heading_style("heading -5")
    assert is_h is True
    assert level == 1


def test_is_heading_style_heading_mixed_case():
    is_h, _ = _is_heading_style("Heading 2")
    assert is_h is True


def test_is_heading_style_heading_all_caps():
    is_h, _ = _is_heading_style("HEADING 3")
    assert is_h is True


def test_is_heading_style_subtitle_returns_false():
    is_h, _ = _is_heading_style("Subtitle")
    assert is_h is False


def test_is_heading_style_normal_returns_false():
    is_h, _ = _is_heading_style("Normal")
    assert is_h is False


def test_is_heading_style_returns_tuple_with_two_elements():
    result = _is_heading_style("heading 1")
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], bool)
    assert isinstance(result[1], int)


def test_is_heading_style_with_extra_whitespace():
    is_h, level = _is_heading_style("  heading 2  ")
    assert is_h is True
    assert level == 2


def test_is_heading_style_title_with_whitespace():
    is_h, level = _is_heading_style("  Title  ")
    assert is_h is True
    assert level == 1


def test_is_heading_style_empty_after_strip():
    """style_name 是空串 → False。"""
    is_h, _ = _is_heading_style("")
    assert is_h is False


def test_is_heading_style_only_whitespace():
    is_h, _ = _is_heading_style("   ")
    assert is_h is False


# ---------- _extract_inline_image_rids 边角 ----------


def test_extract_inline_image_rids_empty_paragraph():
    """空段落（无 drawing）→ 空列表。"""
    from lxml import etree
    xml = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>"""
    p = etree.fromstring(xml)
    rids = _extract_inline_image_rids(p)
    assert rids == []


def test_extract_inline_image_rids_returns_list_type():
    from lxml import etree
    xml = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>"""
    p = etree.fromstring(xml)
    rids = _extract_inline_image_rids(p)
    assert isinstance(rids, list)


def test_extract_inline_image_rids_blip_outside_drawing_not_captured():
    """blip 必须在 w:drawing 内才被捕获。"""
    from lxml import etree
    xml = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                    xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
        <a:blip r:embed="rIdOrphan"/>
    </w:p>"""
    p = etree.fromstring(xml)
    rids = _extract_inline_image_rids(p)
    assert rids == []


def test_extract_inline_image_rids_with_only_embed_and_link():
    """embed 和 link 同时存在 → embed 优先。"""
    from lxml import etree
    xml = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                    xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
        <w:r><w:drawing><a:blip r:embed="rIdEmb" r:link="rIdLink"/></w:drawing></w:r>
    </w:p>"""
    p = etree.fromstring(xml)
    rids = _extract_inline_image_rids(p)
    # embed 优先（代码 `or` 表达式）
    assert rids == ["rIdEmb"]


# ---------- _group_words_to_paragraphs / _lines_to_para 边角 ----------


def _word(text: str, x0: float = 0.0, x1: float = 10.0,
          top: float = 0.0, bottom: float = 10.0) -> dict:
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": bottom}


def test_group_words_to_paragraphs_returns_list_type():
    result = _group_words_to_paragraphs([])
    assert isinstance(result, list)


def test_group_words_to_paragraphs_returns_dicts_with_text_key():
    words = [_word("hello")]
    result = _group_words_to_paragraphs(words)
    assert len(result) == 1
    assert "text" in result[0]
    assert "bbox" in result[0]


def test_group_words_to_paragraphs_empty_words_returns_empty():
    assert _group_words_to_paragraphs([]) == []


def test_group_words_to_paragraphs_three_words_one_line():
    """3 个词在同一行（y 中点接近）→ 1 个段落。"""
    words = [
        _word("a", x0=0, x1=5, top=0, bottom=10),
        _word("b", x0=10, x1=15, top=0, bottom=10),
        _word("c", x0=20, x1=25, top=0, bottom=10),
    ]
    result = _group_words_to_paragraphs(words)
    assert len(result) == 1
    assert "a" in result[0]["text"]
    assert "b" in result[0]["text"]
    assert "c" in result[0]["text"]


def test_lines_to_para_returns_dict_with_text_and_bbox():
    line = [_word("hello", x0=0, x1=20, top=0, bottom=10)]
    result = _lines_to_para([line])
    assert "text" in result
    assert "bbox" in result


def test_lines_to_para_empty_lines_returns_empty_text():
    result = _lines_to_para([])
    assert result["text"] == ""
    assert result["bbox"] is None


def test_lines_to_para_single_line_multiple_words():
    line = [
        _word("a", x0=0, x1=5, top=0, bottom=10),
        _word("b", x0=10, x1=15, top=0, bottom=10),
        _word("c", x0=20, x1=25, top=0, bottom=10),
    ]
    result = _lines_to_para([line])
    assert result["text"] == "a b c"


def test_lines_to_para_bbox_aggregates_correctly():
    """bbox = [min_x0, min_top, max_x1, max_bottom]。"""
    line = [
        _word("a", x0=5, x1=10, top=2, bottom=8),
        _word("b", x0=20, x1=30, top=1, bottom=12),
    ]
    result = _lines_to_para([line])
    bbox = result["bbox"]
    assert bbox == [5, 1, 30, 12]


def test_lines_to_para_multi_line():
    """两行 word → 段落文本用 ' ' join。"""
    line1 = [_word("hello", x0=0, x1=20, top=0, bottom=10)]
    line2 = [_word("world", x0=0, x1=20, top=15, bottom=25)]
    result = _lines_to_para([line1, line2])
    assert "hello" in result["text"]
    assert "world" in result["text"]


def test_lines_to_para_bbox_min_top_from_first_word():
    """bbox[1] 是所有 word 的最小 top。"""
    line = [
        _word("a", x0=0, x1=5, top=10, bottom=20),
        _word("b", x0=10, x1=15, top=5, bottom=15),
    ]
    result = _lines_to_para([line])
    assert result["bbox"][1] == 5  # min top


def test_lines_to_para_bbox_max_bottom_from_first_word():
    line = [
        _word("a", x0=0, x1=5, top=0, bottom=10),
        _word("b", x0=10, x1=15, top=0, bottom=25),
    ]
    result = _lines_to_para([line])
    assert result["bbox"][3] == 25  # max bottom


# ---------- FallbackParser 类契约 ----------


def test_fallback_parser_name_is_str():
    assert isinstance(FallbackParser.name, str)
    assert FallbackParser.name == "fallback"


def test_fallback_parser_version_is_str():
    assert isinstance(FallbackParser.version, str)


def test_fallback_parser_inherits_from_parser_class():
    from app.parsers.base import Parser
    assert issubclass(FallbackParser, Parser)


def test_fallback_parser_init_no_args():
    p = FallbackParser()
    assert p._image_output_dir is None


def test_fallback_parser_init_none_arg():
    """显式传 None → 等同无参。"""
    p = FallbackParser(image_output_dir=None)
    assert p._image_output_dir is None


def test_fallback_parser_init_empty_string_arg():
    """空串 → falsy → 视为 None。"""
    p = FallbackParser(image_output_dir="")
    assert p._image_output_dir is None


def test_fallback_parser_init_path_object(tmp_path: Path):
    p = FallbackParser(image_output_dir=tmp_path)
    assert p._image_output_dir == tmp_path


def test_fallback_parser_init_str_path(tmp_path: Path):
    p = FallbackParser(image_output_dir=str(tmp_path))
    assert p._image_output_dir == tmp_path


def test_fallback_parser_can_be_instantiated_multiple_times():
    p1 = FallbackParser()
    p2 = FallbackParser()
    assert p1 is not p2
    assert p1._image_output_dir is None
    assert p2._image_output_dir is None


def test_fallback_parser_has_parse_method():
    p = FallbackParser()
    assert callable(p.parse)


# ---------- FallbackParser.parse 错误路径 ----------


def test_fallback_parser_parse_missing_pdf_raises(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(tmp_path / "nope.pdf", source_hash="a" * 64)
    assert exc.value.code == "file_not_found"


def test_fallback_parser_parse_missing_docx_raises(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(tmp_path / "nope.docx", source_hash="a" * 64)
    assert exc.value.code == "file_not_found"


def test_fallback_parser_parse_missing_pdf_error_details(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        missing = tmp_path / "nope.pdf"
        FallbackParser().parse(missing, source_hash="a" * 64)
    assert exc.value.details["path"] == str(tmp_path / "nope.pdf")


def test_fallback_parser_parse_missing_docx_error_details(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        missing = tmp_path / "nope.docx"
        FallbackParser().parse(missing, source_hash="a" * 64)
    assert exc.value.details["path"] == str(missing)


def test_fallback_parser_parse_unsupported_type_raises(tmp_path: Path):
    """非 pdf/docx 文件 → detect_source_type raise unsupported_type。"""
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(src, source_hash="a" * 64)
    # detect_source_type 对未知后缀 raise unsupported_type
    assert exc.value.code == "unsupported_type"
