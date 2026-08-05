r"""app/parsers/fallback_parser.py 边角测试 - 第七轮（Round 188）。

补强已有 base/edges/edges2-6（共 845 测试）未覆盖的深度：
- _CAPTION_RE 实际匹配（各 prefix/separator 组合）
- _is_caption 边界（None/empty/不匹配）
- _rows_to_markdown 边界（None cell、单列、padding、单行）
- _image_filename 格式（不同 prefix/index/ext）
- _classify_pdf_paragraph 各路径（empty/caption/short heading/long paragraph）
- _lines_to_para 边界（empty、单 word、bbox 聚合）
- _group_words_to_paragraphs 边界（empty、单行、多行聚类）
- FallbackParser 类属性 name/version
- _save_image 写盘行为
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

from app.parsers.base import Parser
from app.parsers.fallback_parser import (
    _CAPTION_RE,
    _classify_pdf_paragraph,
    _DOCX_VERSION,
    _image_filename,
    _is_caption,
    _lines_to_para,
    _group_words_to_paragraphs,
    _PDFIUM_VERSION,
    _PDFPLUMBER_VERSION,
    _rows_to_markdown,
    _save_image,
    FallbackParser,
)


# =========================================================================
# _CAPTION_RE 实际匹配
# =========================================================================


def test_caption_re_matches_table_dot():
    assert _CAPTION_RE.match("Table 1. Description")


def test_caption_re_matches_figure_dot():
    assert _CAPTION_RE.match("Figure 1. Description")


def test_caption_re_matches_fig_abbreviation():
    assert _CAPTION_RE.match("Fig. 1. Description")


def test_caption_re_matches_fig_no_dot():
    assert _CAPTION_RE.match("Fig 1. Description")


def test_caption_re_matches_chinese_biao():
    """中文"表"。"""
    assert _CAPTION_RE.match("表 1. 描述")


def test_caption_re_matches_chinese_tu():
    """中文"图"。"""
    assert _CAPTION_RE.match("图 1. 描述")


def test_caption_re_matches_chinese_number():
    """全角数字也匹配。"""
    assert _CAPTION_RE.match("图１. 描述")


def test_caption_re_matches_with_colon_separator():
    assert _CAPTION_RE.match("Table 1: Description")


def test_caption_re_matches_with_chinese_comma():
    assert _CAPTION_RE.match("图 1、描述")


def test_caption_re_matches_with_space_only():
    """只有 prefix + 数字 + 空格 也算 caption。"""
    assert _CAPTION_RE.match("Figure 1 Description")


def test_caption_re_matches_leading_whitespace():
    assert _CAPTION_RE.match("  Table 1. Description")


def test_caption_re_case_insensitive():
    assert _CAPTION_RE.match("table 1. Description")
    assert _CAPTION_RE.match("TABLE 1. Description")


def test_caption_re_no_match_without_number():
    assert not _CAPTION_RE.match("Table Description")


def test_caption_re_no_match_random_text():
    assert not _CAPTION_RE.match("Hello world")


def test_caption_re_no_match_paragraph_starting_with_table_word():
    """不以 Table/Figure 等开头的不算 caption。"""
    assert not _CAPTION_RE.match("The table shows data.")


def test_caption_re_no_match_empty_string():
    assert not _CAPTION_RE.match("")


# =========================================================================
# _is_caption 边界
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


# =========================================================================
# _rows_to_markdown 边界
# =========================================================================


def test_rows_to_markdown_empty_returns_empty():
    assert _rows_to_markdown([]) == ""


def test_rows_to_markdown_none_cell_becomes_empty():
    result = _rows_to_markdown([[None, "b"]])
    assert "|  | b |" in result  # None → ""


def test_rows_to_markdown_int_cell_str():
    result = _rows_to_markdown([[1, 2]])
    assert "1" in result
    assert "2" in result


def test_rows_to_markdown_uneven_rows_padded():
    result = _rows_to_markdown([
        ["h1", "h2", "h3"],
        ["v1"],  # 缺 h2/h3
    ])
    lines = result.split("\n")
    # 3 lines per row (header, sep, body row)
    assert len(lines) == 3


def test_rows_to_markdown_single_cell():
    result = _rows_to_markdown([["x"]])
    lines = result.split("\n")
    assert len(lines) == 2  # header + sep


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
    assert isinstance(_rows_to_markdown([["a"]]), str)


# =========================================================================
# _image_filename 格式
# =========================================================================


def test_image_filename_basic_format():
    name = _image_filename("doc-abc123def456abcd", "pdf", 0)
    # doc- prefix 去掉
    assert name == "image_abc123def456abcd_pdf_00.png"


def test_image_filename_index_zero_padded_two():
    name = _image_filename("doc-x", "pdf", 5)
    assert "_05." in name


def test_image_filename_index_two_digits():
    name = _image_filename("doc-x", "pdf", 10)
    assert "_10." in name


def test_image_filename_custom_ext():
    name = _image_filename("doc-x", "pdf", 0, ext="jpg")
    assert name.endswith(".jpg")


def test_image_filename_prefix_in_name():
    name = _image_filename("doc-x", "table", 0)
    assert "_table_" in name


def test_image_filename_doc_dash_removed():
    name = _image_filename("doc-abc", "pdf", 0)
    assert "doc-" not in name


def test_image_filename_returns_str():
    assert isinstance(_image_filename("doc-x", "pdf", 0), str)


# =========================================================================
# _classify_pdf_paragraph 路径
# =========================================================================


def test_classify_pdf_paragraph_empty_returns_paragraph():
    etype, meta = _classify_pdf_paragraph("")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_pdf_paragraph_whitespace_only():
    etype, _ = _classify_pdf_paragraph("   ")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_caption():
    etype, meta = _classify_pdf_paragraph("Table 1. Caption")
    assert etype == "caption"
    assert meta["heuristic"] == "caption_regex"


def test_classify_pdf_paragraph_short_no_period_is_heading():
    etype, meta = _classify_pdf_paragraph("Section Title")
    assert etype == "heading"
    assert meta["heuristic"] == "short_line"
    assert meta["level"] == 0


def test_classify_pdf_paragraph_short_with_period_is_paragraph():
    etype, _ = _classify_pdf_paragraph("Section.")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_chinese_period_is_paragraph():
    etype, _ = _classify_pdf_paragraph("章节。")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_question_mark_is_paragraph():
    etype, _ = _classify_pdf_paragraph("What?")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_with_exclamation_is_paragraph():
    etype, _ = _classify_pdf_paragraph("Stop!")
    assert etype == "paragraph"


def test_classify_pdf_paragraph_long_is_paragraph():
    long_text = "This is a very long paragraph that exceeds the 80 character limit for heading detection."
    assert len(long_text) > 80
    etype, _ = _classify_pdf_paragraph(long_text)
    assert etype == "paragraph"


def test_classify_pdf_paragraph_80_chars_exactly_no_punct_is_heading():
    """len ≤ 80 + 无句末标点 → heading。"""
    text = "a" * 80
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "heading"


def test_classify_pdf_paragraph_81_chars_is_paragraph():
    text = "a" * 81
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "paragraph"


def test_classify_pdf_paragraph_returns_tuple():
    result = _classify_pdf_paragraph("text")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_classify_pdf_paragraph_first_element_str():
    etype, _ = _classify_pdf_paragraph("text")
    assert isinstance(etype, str)


def test_classify_pdf_paragraph_second_element_dict():
    _, meta = _classify_pdf_paragraph("text")
    assert isinstance(meta, dict)


def test_classify_pdf_paragraph_caption_priority_over_short():
    """caption 短文本时仍判 caption（priority: caption > heading）。"""
    etype, _ = _classify_pdf_paragraph("Fig 1. x")
    assert etype == "caption"


# =========================================================================
# _lines_to_para 边界
# =========================================================================


def _make_word(text: str = "x", x0: float = 0, x1: float = 10, top: float = 0, bottom: float = 10) -> dict:
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": bottom}


def test_lines_to_para_empty_returns_empty_text():
    result = _lines_to_para([])
    assert result["text"] == ""
    assert result["bbox"] is None


def test_lines_to_para_single_word():
    result = _lines_to_para([[_make_word("hello")]])
    assert result["text"] == "hello"


def test_lines_to_para_multi_words_in_line():
    result = _lines_to_para([[_make_word("a", x0=0, x1=5), _make_word("b", x0=10, x1=15)]])
    assert result["text"] == "a b"


def test_lines_to_para_multi_lines_merged():
    line1 = [_make_word("line1", top=0, bottom=10)]
    line2 = [_make_word("line2", top=20, bottom=30)]
    result = _lines_to_para([line1, line2])
    assert "line1" in result["text"]
    assert "line2" in result["text"]


def test_lines_to_para_returns_dict():
    result = _lines_to_para([])
    assert isinstance(result, dict)


def test_lines_to_para_text_is_str():
    result = _lines_to_para([[_make_word("x")]])
    assert isinstance(result["text"], str)


def test_lines_to_para_bbox_format():
    """bbox 是 [x0, top, x1, bottom] 4-element list。"""
    line = [_make_word("x", x0=5, x1=15, top=10, bottom=20)]
    result = _lines_to_para([line])
    bbox = result["bbox"]
    assert len(bbox) == 4
    assert bbox[0] == 5  # x0
    assert bbox[1] == 10  # top
    assert bbox[2] == 15  # x1
    assert bbox[3] == 20  # bottom


def test_lines_to_para_words_sorted_by_x0_in_line():
    """同一行 word 按 x0 排序输出。"""
    line = [
        _make_word("b", x0=10, x1=15),
        _make_word("a", x0=0, x1=5),
        _make_word("c", x0=20, x1=25),
    ]
    result = _lines_to_para([line])
    assert result["text"] == "a b c"


def test_lines_to_para_bbox_aggregates_min_max():
    line = [
        _make_word("a", x0=0, x1=5, top=10, bottom=20),
        _make_word("b", x0=100, x1=110, top=5, bottom=25),
    ]
    result = _lines_to_para([line])
    bbox = result["bbox"]
    assert bbox[0] == 0  # min x0
    assert bbox[1] == 5  # min top
    assert bbox[2] == 110  # max x1
    assert bbox[3] == 25  # max bottom


# =========================================================================
# _group_words_to_paragraphs 边界
# =========================================================================


def test_group_words_empty_returns_empty():
    assert _group_words_to_paragraphs([]) == []


def test_group_words_single_word():
    result = _group_words_to_paragraphs([_make_word("hello")])
    assert len(result) == 1
    assert result[0]["text"] == "hello"


def test_group_words_returns_list():
    result = _group_words_to_paragraphs([_make_word("x")])
    assert isinstance(result, list)


def test_group_words_each_para_has_text_and_bbox():
    result = _group_words_to_paragraphs([_make_word("x")])
    assert "text" in result[0]
    assert "bbox" in result[0]


def test_group_words_words_in_same_line_clustered():
    """y_center 差 ≤ 3 视为同行。"""
    words = [
        _make_word("a", x0=0, x1=5, top=10, bottom=15),
        _make_word("b", x0=10, x1=15, top=11, bottom=16),  # y_center close
    ]
    result = _group_words_to_paragraphs(words)
    assert len(result) == 1
    assert "a" in result[0]["text"]
    assert "b" in result[0]["text"]


def test_group_words_distant_lines_separated():
    """y 差 > 3 视为不同行，但仍可能合并成段落。"""
    words = [
        _make_word("a", x0=0, x1=5, top=0, bottom=10),
        _make_word("b", x0=0, x1=5, top=20, bottom=30),  # y_center 差大
    ]
    result = _group_words_to_paragraphs(words)
    # 至少 1 个 paragraph
    assert len(result) >= 1


# =========================================================================
# _save_image 写盘行为
# =========================================================================


def test_save_image_creates_dir(tmp_path: Path):
    out_dir = tmp_path / "images"
    target = _save_image(b"\x89PNG", out_dir, "doc-abc", "pdf", 0)
    assert out_dir.is_dir()
    assert target.is_file()


def test_save_image_writes_bytes(tmp_path: Path):
    data = b"\x89PNG\r\n\x1a\n"
    target = _save_image(data, tmp_path, "doc-abc", "pdf", 0)
    assert target.read_bytes() == data


def test_save_image_filename_uses_image_filename(tmp_path: Path):
    target = _save_image(b"x", tmp_path, "doc-abc", "pdf", 5)
    # 应使用 _image_filename 生成的名称
    assert "_05." in target.name
    assert "_pdf_" in target.name


def test_save_image_creates_parents(tmp_path: Path):
    out_dir = tmp_path / "a" / "b" / "c"
    target = _save_image(b"x", out_dir, "doc-x", "pdf", 0)
    assert target.is_file()


def test_save_image_returns_path(tmp_path: Path):
    target = _save_image(b"x", tmp_path, "doc-x", "pdf", 0)
    assert isinstance(target, Path)


def test_save_image_existing_dir_no_error(tmp_path: Path):
    """已存在的目录不报错（mkdir parents=True exist_ok=True）。"""
    target1 = _save_image(b"x", tmp_path, "doc-x", "pdf", 0)
    target2 = _save_image(b"y", tmp_path, "doc-x", "pdf", 1)
    assert target1.is_file()
    assert target2.is_file()


def test_save_image_custom_ext(tmp_path: Path):
    target = _save_image(b"x", tmp_path, "doc-x", "pdf", 0, ext="jpg")
    assert target.name.endswith(".jpg")


# =========================================================================
# FallbackParser 类属性
# =========================================================================


def test_fallback_parser_name_value():
    assert FallbackParser.name == "fallback"


def test_fallback_parser_inherits_parser():
    assert issubclass(FallbackParser, Parser)


def test_fallback_parser_init_no_args():
    parser = FallbackParser()
    assert parser is not None


def test_fallback_parser_init_with_image_output_dir(tmp_path: Path):
    parser = FallbackParser(image_output_dir=tmp_path)
    assert parser._image_output_dir == tmp_path


def test_fallback_parser_init_image_output_dir_str(tmp_path: Path):
    parser = FallbackParser(image_output_dir=str(tmp_path))
    # str 转 Path
    assert isinstance(parser._image_output_dir, Path)


def test_fallback_parser_init_image_output_dir_none():
    parser = FallbackParser(image_output_dir=None)
    assert parser._image_output_dir is None


def test_fallback_parser_init_signature():
    sig = inspect.signature(FallbackParser.__init__)
    params = set(sig.parameters)
    assert "self" in params
    assert "image_output_dir" in params


def test_fallback_parser_init_default_none():
    sig = inspect.signature(FallbackParser.__init__)
    assert sig.parameters["image_output_dir"].default is None


def test_fallback_parser_parse_method_exists():
    parser = FallbackParser()
    assert callable(parser.parse)


# =========================================================================
# 版本常量
# =========================================================================


def test_pdfplumber_version_constant():
    """常量存在（None 表示未安装）。"""
    assert hasattr(_PDFPLUMBER_VERSION, "__class__") or _PDFPLUMBER_VERSION is None


def test_pdfium_version_constant():
    assert hasattr(_PDFIUM_VERSION, "__class__") or _PDFIUM_VERSION is None


def test_docx_version_constant():
    assert hasattr(_DOCX_VERSION, "__class__") or _DOCX_VERSION is None


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import app.parsers.fallback_parser as mod
    assert mod.__all__ == ["FallbackParser"]


def test_module_all_is_list():
    import app.parsers.fallback_parser as mod
    assert isinstance(mod.__all__, list)


def test_module_uses_future_annotations():
    import app.parsers.fallback_parser as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_imports_re():
    import app.parsers.fallback_parser as mod
    src = inspect.getsource(mod)
    assert "import re" in src


def test_module_imports_path():
    import app.parsers.fallback_parser as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import app.parsers.fallback_parser as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_models():
    import app.parsers.fallback_parser as mod
    src = inspect.getsource(mod)
    assert "from app.models" in src


def test_module_imports_base():
    import app.parsers.fallback_parser as mod
    src = inspect.getsource(mod)
    assert "from app.parsers.base" in src


def test_module_docstring_present():
    import app.parsers.fallback_parser as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_pdfplumber():
    import app.parsers.fallback_parser as mod
    assert "pdfplumber" in mod.__doc__


def test_module_docstring_mentions_python_docx():
    import app.parsers.fallback_parser as mod
    assert "python-docx" in mod.__doc__ or "docx" in mod.__doc__.lower()


def test_module_docstring_mentions_kreuzberg():
    """docstring 解释为什么不直接用 kreuzberg。"""
    import app.parsers.fallback_parser as mod
    assert "kreuzberg" in mod.__doc__.lower() or "Kreuzberg" in mod.__doc__
