r"""app/parsers/fallback_parser.py 边角测试 - 第六轮（Round 167）。

补强已有 base/edges/edges2-5（共 730 测试）未覆盖的纯函数深度：
- _CAPTION_RE 正则覆盖（中英文 caption、各种分隔符）
- _is_caption 各分支
- _rows_to_markdown 深度边界（None/uneven/Unicode/超宽数字）
- _image_filename 命名格式（zero-pad、ext、prefix）
- _classify_pdf_paragraph 启发式边界
- _group_words_to_paragraphs 合成 word 列表
- _lines_to_para 多行融合
- FallbackParser 类属性与方法签名
- 模块结构与依赖（pdfplumber/docx/pypdfium2 可选 import）
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

from app.models import Document, Element, WarningRecord
from app.parsers.base import ParserError
from app.parsers.fallback_parser import (
    _CAPTION_RE,
    FallbackParser,
    _classify_pdf_paragraph,
    _group_words_to_paragraphs,
    _image_filename,
    _is_caption,
    _lines_to_para,
    _rows_to_markdown,
)


_H = "a" * 64


# =========================================================================
# _CAPTION_RE 正则覆盖
# =========================================================================


def test_caption_re_pattern_object():
    import re
    assert isinstance(_CAPTION_RE, re.Pattern)


def test_caption_re_ignorecase_flag():
    """正则带 IGNORECASE 标志。"""
    import re
    assert _CAPTION_RE.flags & re.IGNORECASE


def test_caption_re_matches_table_english():
    assert _CAPTION_RE.match("Table 1. Summary")


def test_caption_re_matches_table_chinese():
    assert _CAPTION_RE.match("表 1. 概要")


def test_caption_re_matches_figure_english():
    assert _CAPTION_RE.match("Figure 1. Diagram")


def test_caption_re_matches_fig_abbreviation():
    assert _CAPTION_RE.match("Fig. 1. Diagram")
    assert _CAPTION_RE.match("Fig 1. Diagram")


def test_caption_re_matches_figure_chinese():
    assert _CAPTION_RE.match("图 1. 示意图")


def test_caption_re_matches_full_width_digit():
    """全角数字 ０１２..."""
    assert _CAPTION_RE.match("表 １. 概要")


def test_caption_re_matches_dot_separator():
    assert _CAPTION_RE.match("Table 1. Hello")


def test_caption_re_matches_colon_separator():
    assert _CAPTION_RE.match("Table 1: Hello")


def test_caption_re_matches_chinese_dot_separator():
    """中文顿号、。"""
    assert _CAPTION_RE.match("表 1、概要")


def test_caption_re_matches_whitespace_separator():
    assert _CAPTION_RE.match("Table 1 Hello")


def test_caption_re_matches_with_leading_whitespace():
    assert _CAPTION_RE.match("   Table 1. Hello")


def test_caption_re_does_not_match_non_caption():
    assert _CAPTION_RE.match("hello world") is None


def test_caption_re_does_not_match_paragraph():
    assert _CAPTION_RE.match("This is a regular paragraph.") is None


def test_caption_re_does_not_match_lowercase_table_no_digit():
    """必须含数字。"""
    assert _CAPTION_RE.match("Table: Hello") is None


def test_caption_re_does_not_match_number_only():
    assert _CAPTION_RE.match("1. Hello") is None


def test_caption_re_does_not_match_heading_word():
    assert _CAPTION_RE.match("Methodology") is None


# =========================================================================
# _is_caption
# =========================================================================


def test_is_caption_table_english():
    assert _is_caption("Table 1. Summary") is True


def test_is_caption_figure_english():
    assert _is_caption("Figure 1. Diagram") is True


def test_is_caption_chinese():
    assert _is_caption("表 1. 概要") is True


def test_is_caption_returns_bool_type():
    assert isinstance(_is_caption("hello"), bool)


def test_is_caption_empty_string():
    assert _is_caption("") is False


def test_is_caption_none():
    assert _is_caption(None) is False  # type: ignore[arg-type]


def test_is_caption_normal_text():
    assert _is_caption("hello world") is False


def test_is_caption_paragraph_with_table_word_in_middle():
    """'as shown in Table 1' 不是 caption（不在开头）。"""
    assert _is_caption("as shown in Table 1") is False


def test_is_caption_returns_bool_for_various_inputs():
    for inp in ["", None, "x", "Table 1. y"]:
        assert isinstance(_is_caption(inp), bool)


# =========================================================================
# _rows_to_markdown 深度
# =========================================================================


def test_rows_to_markdown_empty_returns_empty():
    assert _rows_to_markdown([]) == ""


def test_rows_to_markdown_single_row():
    out = _rows_to_markdown([["a", "b"]])
    assert "| a | b |" in out
    assert "| --- | --- |" in out


def test_rows_to_markdown_two_rows():
    out = _rows_to_markdown([["h1", "h2"], ["v1", "v2"]])
    lines = out.split("\n")
    assert len(lines) == 3


def test_rows_to_markdown_pads_uneven():
    out = _rows_to_markdown([["a", "b", "c"], ["d", "e"]])
    lines = out.split("\n")
    # body 行补一个空 cell
    assert "| d | e |  |" in lines[2]


def test_rows_to_markdown_none_cell_to_empty():
    out = _rows_to_markdown([["a", None]])
    # None → ""
    assert "| a |  |" in out


def test_rows_to_markdown_int_cell_str():
    """int cell → str。"""
    out = _rows_to_markdown([[1, 2]])
    assert "| 1 | 2 |" in out


def test_rows_to_markdown_mixed_types():
    out = _rows_to_markdown([["a", 1, None, 2.5]])
    assert "| a | 1 |  | 2.5 |" in out


def test_rows_to_markdown_unicode():
    out = _rows_to_markdown([["中", "文"]])
    assert "中" in out
    assert "文" in out


def test_rows_to_markdown_separator_format():
    out = _rows_to_markdown([["a", "b", "c"]])
    lines = out.split("\n")
    assert lines[1] == "| --- | --- | --- |"


def test_rows_to_markdown_empty_cells_in_row():
    out = _rows_to_markdown([["", ""]])
    assert out == "|  |  |\n| --- | --- |"


def test_rows_to_markdown_max_width_uses_max():
    out = _rows_to_markdown([["a"], ["1", "2", "3"]])
    lines = out.split("\n")
    # 第一行被补齐到 3 列
    assert "| a |  |  |" in lines[0]


# =========================================================================
# _image_filename
# =========================================================================


def test_image_filename_default_ext_png():
    name = _image_filename("doc-abc123", "p1", 0)
    assert name.endswith(".png")


def test_image_filename_explicit_ext():
    name = _image_filename("doc-abc123", "p1", 0, "jpg")
    assert name.endswith(".jpg")


def test_image_filename_strips_doc_prefix():
    name = _image_filename("doc-abc123", "p1", 0)
    assert "doc-abc123" not in name
    assert "abc123" in name


def test_image_filename_zero_padded_index():
    """index 用 02d 格式。"""
    name = _image_filename("doc-x", "p1", 5)
    assert "_05." in name
    name10 = _image_filename("doc-x", "p1", 10)
    assert "_10." in name10


def test_image_filename_format():
    """格式：image_<doc_id_short>_<prefix>_<idx:02d>.<ext>"""
    name = _image_filename("doc-abc123", "p1", 3, "png")
    assert name == "image_abc123_p1_03.png"


def test_image_filename_prefix_para():
    name = _image_filename("doc-x", "para3", 1)
    assert "_para3_" in name


def test_image_filename_index_zero():
    name = _image_filename("doc-x", "p1", 0)
    assert "_00." in name


def test_image_filename_index_large():
    name = _image_filename("doc-x", "p1", 999)
    # 02d 仍能表示
    assert "_999." in name


# =========================================================================
# _classify_pdf_paragraph
# =========================================================================


def test_classify_caption():
    etype, meta = _classify_pdf_paragraph("Table 1. Summary")
    assert etype == "caption"
    assert meta == {"heuristic": "caption_regex"}


def test_classify_caption_chinese():
    etype, _ = _classify_pdf_paragraph("图 1. 示意图")
    assert etype == "caption"


def test_classify_short_line_no_ending_punct_is_heading():
    etype, meta = _classify_pdf_paragraph("Methodology")
    assert etype == "heading"
    assert meta.get("level") == 0
    assert meta.get("heuristic") == "short_line"


def test_classify_short_line_with_period_is_paragraph():
    """以 . 结尾的短句不算 heading。"""
    etype, _ = _classify_pdf_paragraph("End.")
    assert etype == "paragraph"


def test_classify_short_line_with_chinese_period():
    etype, _ = _classify_pdf_paragraph("结束。")
    assert etype == "paragraph"


def test_classify_short_line_with_question_mark():
    etype, _ = _classify_pdf_paragraph("Why?")
    assert etype == "paragraph"


def test_classify_short_line_with_exclamation():
    etype, _ = _classify_pdf_paragraph("Wow!")
    assert etype == "paragraph"


def test_classify_short_line_with_chinese_question():
    etype, _ = _classify_pdf_paragraph("为什么？")
    assert etype == "paragraph"


def test_classify_short_line_with_chinese_exclamation():
    etype, _ = _classify_pdf_paragraph("好！")
    assert etype == "paragraph"


def test_classify_long_line_is_paragraph():
    etype, meta = _classify_pdf_paragraph("a" * 100)
    assert etype == "paragraph"
    assert meta == {}


def test_classify_empty_string():
    etype, meta = _classify_pdf_paragraph("")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_whitespace_only():
    etype, meta = _classify_pdf_paragraph("   ")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_heading_max_80_chars():
    """len <= 80 且不结尾标点 → heading。"""
    text = "a" * 80
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "heading"


def test_classify_paragraph_81_chars():
    """len == 81 → paragraph。"""
    text = "a" * 81
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "paragraph"


def test_classify_returns_tuple():
    result = _classify_pdf_paragraph("hello")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_classify_caption_priority_over_heading():
    """caption 优先级高于 heading（即使短）。"""
    etype, _ = _classify_pdf_paragraph("Fig 1. x")
    assert etype == "caption"


# =========================================================================
# _group_words_to_paragraphs 合成 word 列表
# =========================================================================


def _word(text: str, x0: float = 0.0, top: float = 0.0, x1: float | None = None, bottom: float | None = None) -> dict:
    return {
        "text": text,
        "x0": x0,
        "x1": x1 if x1 is not None else x0 + len(text) * 5,
        "top": top,
        "bottom": bottom if bottom is not None else top + 10,
    }


def test_group_words_empty_returns_empty():
    assert _group_words_to_paragraphs([]) == []


def test_group_words_single_word():
    paras = _group_words_to_paragraphs([_word("hello")])
    assert len(paras) == 1
    assert paras[0]["text"] == "hello"


def test_group_words_same_line_merged():
    """同一行（y 接近）的多个 word 合并到一个 paragraph。"""
    paras = _group_words_to_paragraphs([
        _word("hello", x0=0, top=10),
        _word("world", x0=50, top=10),
    ])
    assert len(paras) == 1
    assert "hello" in paras[0]["text"]
    assert "world" in paras[0]["text"]


def test_group_words_distant_lines_separated():
    """y 差距大的两行 → 两个 paragraph。"""
    paras = _group_words_to_paragraphs([
        _word("line1", top=0),
        _word("line2", top=200),  # 远超 1.5 * 行高
    ])
    assert len(paras) == 2


def test_group_words_bbox_in_result():
    paras = _group_words_to_paragraphs([_word("hello", x0=5, top=10, x1=30, bottom=20)])
    assert paras[0]["bbox"] is not None
    bbox = paras[0]["bbox"]
    assert bbox[0] == 5  # x0
    assert bbox[1] == 10  # top
    assert bbox[2] == 30  # x1
    assert bbox[3] == 20  # bottom


def test_group_words_returns_list_of_dicts():
    paras = _group_words_to_paragraphs([_word("x")])
    assert isinstance(paras, list)
    assert isinstance(paras[0], dict)


# =========================================================================
# _lines_to_para
# =========================================================================


def test_lines_to_para_empty_returns_empty_text():
    result = _lines_to_para([])
    assert result["text"] == ""
    assert result["bbox"] is None


def test_lines_to_para_single_line_single_word():
    result = _lines_to_para([[_word("hello", x0=0, top=0, x1=10, bottom=10)]])
    assert result["text"] == "hello"
    assert result["bbox"] == [0, 0, 10, 10]


def test_lines_to_para_multi_words_in_line():
    result = _lines_to_para([[
        _word("hello", x0=0, top=0, x1=10, bottom=10),
        _word("world", x0=20, top=0, x1=30, bottom=10),
    ]])
    assert "hello" in result["text"]
    assert "world" in result["text"]


def test_lines_to_para_words_sorted_by_x0():
    """同一行 word 按 x0 排序。"""
    result = _lines_to_para([[
        _word("world", x0=20, top=0, x1=30, bottom=10),
        _word("hello", x0=0, top=0, x1=10, bottom=10),
    ]])
    # hello (x0=0) 在 world (x0=20) 前
    assert result["text"].index("hello") < result["text"].index("world")


def test_lines_to_para_multi_lines_merged():
    result = _lines_to_para([
        [_word("line1", x0=0, top=0, x1=20, bottom=10)],
        [_word("line2", x0=0, top=20, x1=20, bottom=30)],
    ])
    assert "line1" in result["text"]
    assert "line2" in result["text"]


def test_lines_to_para_bbox_aggregates():
    """bbox = [min(x0), min(top), max(x1), max(bottom)]。"""
    result = _lines_to_para([
        [_word("a", x0=10, top=5, x1=15, bottom=15)],
        [_word("b", x0=20, top=25, x1=25, bottom=35)],
    ])
    bbox = result["bbox"]
    assert bbox[0] == 10  # min x0
    assert bbox[1] == 5  # min top
    assert bbox[2] == 25  # max x1
    assert bbox[3] == 35  # max bottom


def test_lines_to_para_returns_dict():
    result = _lines_to_para([])
    assert isinstance(result, dict)
    assert "text" in result
    assert "bbox" in result


# =========================================================================
# FallbackParser 类属性
# =========================================================================


def test_fallback_parser_name_value():
    assert FallbackParser.name == "fallback"


def test_fallback_parser_version_contains_pdfplumber():
    assert "pdfplumber" in FallbackParser.version


def test_fallback_parser_version_contains_python_docx():
    assert "python-docx" in FallbackParser.version


def test_fallback_parser_version_contains_pypdfium2():
    assert "pypdfium2" in FallbackParser.version


def test_fallback_parser_inherits_parser():
    from app.parsers.base import Parser
    assert issubclass(FallbackParser, Parser)


def test_fallback_parser_init_no_args():
    """__init__ 的 image_output_dir 默认 None。"""
    p = FallbackParser()
    assert p is not None


def test_fallback_parser_init_with_image_output_dir(tmp_path: Path):
    p = FallbackParser(image_output_dir=tmp_path)
    assert p._image_output_dir == tmp_path


def test_fallback_parser_init_image_output_dir_str(tmp_path: Path):
    """str 路径会被 Path() 包装。"""
    p = FallbackParser(image_output_dir=str(tmp_path))
    assert isinstance(p._image_output_dir, Path)


def test_fallback_parser_init_image_output_dir_none():
    p = FallbackParser(image_output_dir=None)
    assert p._image_output_dir is None


def test_fallback_parser_init_signature():
    sig = inspect.signature(FallbackParser.__init__)
    assert set(sig.parameters) == {"self", "image_output_dir"}


def test_fallback_parser_init_default_none():
    sig = inspect.signature(FallbackParser.__init__)
    assert sig.parameters["image_output_dir"].default is None


def test_fallback_parser_parse_method_exists():
    assert callable(FallbackParser.parse)


def test_fallback_parser_parse_signature():
    sig = inspect.signature(FallbackParser.parse)
    assert set(sig.parameters) == {"self", "path", "source_hash"}


# =========================================================================
# FallbackParser.parse 错误路径
# =========================================================================


def test_parse_nonexistent_pdf_raises(tmp_path: Path):
    p = tmp_path / "missing.pdf"
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(p, _H)
    assert exc.value.code == "file_not_found"


def test_parse_nonexistent_docx_raises(tmp_path: Path):
    p = tmp_path / "missing.docx"
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(p, _H)
    assert exc.value.code == "file_not_found"


def test_parse_unsupported_extension_raises(tmp_path: Path):
    p = tmp_path / "foo.txt"
    p.write_text("hello", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(p, _H)
    assert exc.value.code == "unsupported_type"


def test_parse_file_not_found_details_has_path(tmp_path: Path):
    p = tmp_path / "missing.pdf"
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(p, _H)
    assert exc.value.details == {"path": str(p)}


def test_parse_file_not_found_message_has_path(tmp_path: Path):
    p = tmp_path / "missing.pdf"
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(p, _H)
    assert str(p) in exc.value.message


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


def test_module_optional_import_pdfplumber():
    """pdfplumber 是 try/except 可选导入。"""
    import app.parsers.fallback_parser as mod
    src = inspect.getsource(mod)
    assert "import pdfplumber" in src
    assert "except ImportError" in src


def test_module_optional_import_docx():
    import app.parsers.fallback_parser as mod
    src = inspect.getsource(mod)
    assert "import docx" in src


def test_module_optional_import_pypdfium2():
    import app.parsers.fallback_parser as mod
    src = inspect.getsource(mod)
    assert "import pypdfium2" in src


def test_module_docstring_present():
    import app.parsers.fallback_parser as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_pdfplumber():
    import app.parsers.fallback_parser as mod
    doc = mod.__doc__
    assert "pdfplumber" in doc
    assert "python-docx" in doc or "docx" in doc.lower()


def test_module_docstring_mentions_kreuzberg_limitation():
    """docstring 解释为什么需要 fallback（kreuzberg 限制）。"""
    import app.parsers.fallback_parser as mod
    doc = mod.__doc__
    assert "Kreuzberg" in doc or "kreuzberg" in doc.lower()


def test_module_has_pdfplumber_version_constant():
    """_PDFPLUMBER_VERSION 常量。"""
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "_PDFPLUMBER_VERSION")


def test_module_has_docx_version_constant():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "_DOCX_VERSION")


def test_module_has_pdfium_version_constant():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "_PDFIUM_VERSION")


def test_module_no_public_silence_unused():
    import app.parsers.fallback_parser as mod
    assert not hasattr(mod, "_silence_unused")


# =========================================================================
# 综合行为
# =========================================================================


def test_classify_idempotent():
    a = _classify_pdf_paragraph("hello world")
    b = _classify_pdf_paragraph("hello world")
    assert a == b


def test_is_caption_idempotent():
    assert _is_caption("Table 1. x") == _is_caption("Table 1. x")


def test_rows_to_markdown_idempotent():
    rows = [["a", "b"], ["1", "2"]]
    assert _rows_to_markdown(rows) == _rows_to_markdown(rows)


def test_image_filename_idempotent():
    assert _image_filename("doc-x", "p1", 0) == _image_filename("doc-x", "p1", 0)


def test_classify_does_not_mutate_input():
    text = "Table 1. Summary"
    before = text
    _classify_pdf_paragraph(text)
    assert text == before


def test_is_caption_does_not_mutate_input():
    text = "Table 1. Summary"
    before = text
    _is_caption(text)
    assert text == before
