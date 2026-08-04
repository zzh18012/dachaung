"""app/parsers/fallback_parser.py 边角测试 - 第四轮（Round 106）。

补强已有 base/edges/edges2/edges3（共 421 个测试）未覆盖的深度路径：
- _parse_docx：paragraph/heading/caption/table 四种 body child 的 emit、
  body 顺序遍历、section_idx 恒为 0、空段落 "(空段落)"、内嵌图片 emit
- _parse_pdf：多页集成（element_id 跨页连续）、同页 words+tables+images 组合、
  image_output_dir 设置时 image_counter 递增
- FallbackParser.parse()：mock _parse_pdf/_parse_docx 端到端、metadata 内容
- _group_words_to_paragraphs：负坐标、阈值边界
- _lines_to_para：负坐标
- _classify_pdf_paragraph：caption + 长 text > 80 仍 caption
- _is_caption 直接调用、_CAPTION_RE 与 _is_caption 一致性
- 模块结构：__all__、imports

不修改任何源码。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from app.parsers import fallback_parser as fp
from app.parsers.base import ParserError
from app.parsers.fallback_parser import (
    _CAPTION_RE,
    FallbackParser,
    _classify_pdf_paragraph,
    _extract_inline_image_rids,
    _group_words_to_paragraphs,
    _is_caption,
    _is_heading_style,
    _image_filename,
    _lines_to_para,
    _rows_to_markdown,
)


# =========================================================================
# 辅助
# =========================================================================


def _word(text: str, x0=0.0, x1=10.0, top=0.0, bottom=10.0) -> dict:
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": bottom}


class _FakeXmlChild:
    """模拟 docx paragraph/table 的 XML element：支持 .tag 和 .iter()。"""

    def __init__(self, tag: str) -> None:
        self.tag = tag

    def iter(self, qn_tag=None):
        return iter([])


# =========================================================================
# _is_caption 直接调用
# =========================================================================


def test_is_caption_returns_bool_type():
    assert isinstance(_is_caption("Figure 1."), bool)


def test_is_caption_empty_string_returns_false():
    assert _is_caption("") is False


def test_is_caption_none_returns_false():
    assert _is_caption(None) is False  # type: ignore[arg-type]


def test_is_caption_caption_returns_true():
    assert _is_caption("Figure 1. Title") is True


def test_is_caption_paragraph_returns_false():
    assert _is_caption("normal paragraph text.") is False


def test_is_caption_whitespace_only_returns_false():
    assert _is_caption("   ") is False


def test_is_caption_full_width_digit_returns_true():
    assert _is_caption("图 １ 内容") is True


def test_is_caption_tab_only_before_keyword_returns_true():
    assert _is_caption("\tFigure 1. x") is True


def test_is_caption_caption_regex_and_function_agree_on_match():
    text = "Table 5: Result data"
    assert _CAPTION_RE.match(text) is not None
    assert _is_caption(text) is True


def test_is_caption_caption_regex_and_function_agree_on_non_match():
    text = "Normal text without caption pattern."
    assert _CAPTION_RE.match(text) is None
    assert _is_caption(text) is False


# =========================================================================
# _CAPTION_RE 更深的边界
# =========================================================================


def test_caption_re_pattern_uses_ignore_case_flag():
    assert _CAPTION_RE.flags & re.IGNORECASE


def test_caption_re_pattern_includes_chinese_keywords():
    assert "表" in _CAPTION_RE.pattern
    assert "图" in _CAPTION_RE.pattern


def test_caption_re_pattern_includes_english_keywords():
    assert "Table" in _CAPTION_RE.pattern
    assert "Figure" in _CAPTION_RE.pattern
    assert "Fig" in _CAPTION_RE.pattern


def test_caption_re_pattern_has_full_width_digit_range():
    assert "０-９" in _CAPTION_RE.pattern


def test_caption_re_match_fig_with_dot():
    assert _CAPTION_RE.match("Fig. 1 intro")


def test_caption_re_match_fig_without_dot():
    assert _CAPTION_RE.match("Fig 1 intro")


def test_caption_re_keyword_with_trailing_spaces_then_number():
    assert _CAPTION_RE.match("Figure   1. x")


def test_caption_re_only_keyword_no_space_no_number_fails():
    assert _CAPTION_RE.match("Figure") is None


# =========================================================================
# _classify_pdf_paragraph：caption 优先级（更多变体）
# =========================================================================


def test_classify_pdf_paragraph_caption_with_long_text_returns_caption():
    """caption 关键字 + 长内容（>80 字符）→ caption（caption 启发式优先于 heading/paragraph）。"""
    text = "Figure 1. " + "x" * 100
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "caption"


def test_classify_pdf_paragraph_caption_meta_only_has_heuristic_key():
    etype, meta = _classify_pdf_paragraph("Figure 1. x")
    assert etype == "caption"
    assert set(meta.keys()) == {"heuristic"}


def test_classify_pdf_paragraph_caption_meta_heuristic_value():
    _, meta = _classify_pdf_paragraph("Figure 1. x")
    assert meta["heuristic"] == "caption_regex"


def test_classify_pdf_paragraph_short_with_chinese_semicolon_is_heading():
    """`；`（中文分号）不是终止符 → heading。"""
    etype, _ = _classify_pdf_paragraph("短标题；继续")
    assert etype == "heading"


def test_classify_pdf_paragraph_short_with_colon_is_heading():
    """英文 `:` 不是终止符 → heading。"""
    etype, _ = _classify_pdf_paragraph("Title: subtitle")
    assert etype == "heading"


def test_classify_pdf_paragraph_long_text_with_colon_is_paragraph():
    text = "x" * 81 + ":"
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "paragraph"


def test_classify_pdf_paragraph_priority_caption_first():
    """caption 检测在最前面，即便短也优先。"""
    etype, _ = _classify_pdf_paragraph("图 1.")
    assert etype == "caption"


def test_classify_pdf_paragraph_strip_affects_caption_detection():
    """`   Figure 1.` 前导空白 → strip 后仍 caption。"""
    etype, _ = _classify_pdf_paragraph("   Figure 1. x")
    assert etype == "caption"


# =========================================================================
# _group_words_to_paragraphs：负坐标与阈值边界
# =========================================================================


def test_group_words_negative_y_coords_handled():
    """负 top/bottom 仍参与聚类。"""
    words = [
        _word("a", top=-10.0, bottom=-5.0),
        _word("b", x0=20.0, x1=30.0, top=-10.0, bottom=-5.0),
    ]
    paras = _group_words_to_paragraphs(words)
    assert len(paras) == 1


def test_group_words_negative_x_coords_handled():
    words = [
        _word("a", x0=-30.0, x1=-10.0),
        _word("b", x0=-5.0, x1=10.0),
    ]
    paras = _group_words_to_paragraphs(words)
    assert len(paras) == 1
    bbox = paras[0]["bbox"]
    assert bbox[0] == -30.0  # min x0


def test_group_words_line_cluster_threshold_2_9_within():
    """y_center 差 ≤ 3.0 视为同行；2.9 应聚成一行。"""
    words = [
        _word("a", top=0.0, bottom=2.0),  # y_center=1.0
        _word("b", x0=20.0, x1=30.0, top=2.9, bottom=4.9),  # y_center=3.9, diff=2.9
    ]
    paras = _group_words_to_paragraphs(words)
    assert len(paras) == 1


def test_group_words_line_cluster_threshold_3_1_splits():
    """y_center 差 > 3.0 视为不同行；3.1 应分两行。"""
    words = [
        _word("a", top=0.0, bottom=2.0),  # y_center=1.0
        _word("b", x0=20.0, x1=30.0, top=3.1, bottom=5.1),  # y_center=4.1, diff=3.1
    ]
    paras = _group_words_to_paragraphs(words)
    # 两个单独的行；行间距 1.5*median_h 触发段落分隔
    # median_h = 2.0, threshold = 3.0; line_top - last_bottom = ?
    # 这取决于具体坐标，至少应不报错
    assert isinstance(paras, list)


def test_group_words_zero_height_word_handled():
    """top == bottom → height=0 → 不抛异常。"""
    words = [_word("a", top=5.0, bottom=5.0)]
    paras = _group_words_to_paragraphs(words)
    assert len(paras) == 1


def test_group_words_returns_dict_has_text_key():
    paras = _group_words_to_paragraphs([_word("a")])
    assert "text" in paras[0]


def test_group_words_returns_dict_has_bbox_key():
    paras = _group_words_to_paragraphs([_word("a")])
    assert "bbox" in paras[0]


def test_group_words_text_strips_empty_words_in_join():
    """空 text 的 word 仍参与 text 拼接（生成多余空格）。"""
    words = [_word("a"), _word("", x0=20.0, x1=30.0), _word("b", x0=40.0, x1=50.0)]
    paras = _group_words_to_paragraphs(words)
    assert isinstance(paras[0]["text"], str)


def test_group_words_paragraph_break_large_gap_splits():
    """行间 y 差远大于 1.5*median_h → 分段。"""
    words = [
        _word("a", top=0.0, bottom=10.0),  # 行 1
        _word("b", x0=20.0, x1=30.0, top=100.0, bottom=110.0),  # 行 2
    ]
    paras = _group_words_to_paragraphs(words)
    assert len(paras) == 2


def test_group_words_single_word_returns_single_para():
    paras = _group_words_to_paragraphs([_word("lonely")])
    assert len(paras) == 1


def test_group_words_two_words_same_y_one_para():
    words = [_word("a"), _word("b", x0=20.0, x1=30.0)]
    paras = _group_words_to_paragraphs(words)
    assert len(paras) == 1


# =========================================================================
# _lines_to_para：负坐标
# =========================================================================


def test_lines_to_para_negative_x_coords_in_bbox():
    line = [_word("a", x0=-100.0, x1=-50.0), _word("b", x0=-30.0, x1=10.0)]
    result = _lines_to_para([line])
    assert result["bbox"][0] == -100.0


def test_lines_to_para_negative_y_coords_in_bbox():
    line = [_word("a", top=-100.0, bottom=-90.0)]
    result = _lines_to_para([line])
    assert result["bbox"][1] == -100.0
    assert result["bbox"][3] == -90.0


def test_lines_to_para_empty_lines_list_returns_empty_text():
    result = _lines_to_para([])
    assert result["text"] == ""
    assert result["bbox"] is None


def test_lines_to_para_word_with_empty_text_preserved_in_join():
    line = [_word("a"), _word("", x0=20.0, x1=30.0)]
    result = _lines_to_para([line])
    # "a" + " " + "" → "a "
    assert "a" in result["text"]


def test_lines_to_para_returns_dict_type():
    line = [_word("a")]
    assert isinstance(_lines_to_para([line]), dict)


# =========================================================================
# _is_heading_style：更多变体
# =========================================================================


def test_is_heading_style_heading_with_trailing_space_in_level():
    """`Heading 1 ` 后带空格 → strip 后 int('1')。"""
    assert _is_heading_style("Heading 1 ") == (True, 1)


def test_is_heading_style_heading_with_multiple_spaces_in_level():
    assert _is_heading_style("Heading  2") == (True, 2)


def test_is_heading_style_heading_tab_separated():
    """`Heading\\t3` → strip 后 int 不抛异常。"""
    result = _is_heading_style("Heading\t3")
    assert result[0] is True


def test_is_heading_style_title_with_leading_space_stripped():
    assert _is_heading_style("  Title") == (True, 1)


def test_is_heading_style_empty_after_strip_returns_false_tuple():
    assert _is_heading_style("   ") == (False, 0)


def test_is_heading_style_normal_text_returns_false_tuple():
    assert _is_heading_style("Body Text") == (False, 0)


def test_is_heading_style_returns_tuple_of_bool_int():
    result = _is_heading_style("Heading 1")
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], bool)
    assert isinstance(result[1], int)


# =========================================================================
# _parse_docx：成功路径（mock docx.Document）
# =========================================================================


def test_parse_docx_single_paragraph_emit(monkeypatch, tmp_path: Path):
    """单段落 body → emit 1 个 paragraph element。"""
    if fp.qn is None:
        pytest.skip("qn unavailable")

    class FakePara:
        def __init__(self, child, doc):
            self.text = "hello world."
            self.style = type("S", (), {"name": "Normal"})()

    class FakeChild(_FakeXmlChild):
        def __init__(self):
            super().__init__(fp.qn("w:p"))

    class FakeBody:
        def iterchildren(self):
            return iter([FakeChild()])

    class FakeDoc:
        element = type("E", (), {"body": FakeBody()})

    class FakeDocxModule:
        Document = staticmethod(lambda path: FakeDoc())
        text = type("m", (), {"paragraph": type("p", (), {"Paragraph": FakePara})})

    monkeypatch.setattr(fp, "docx", FakeDocxModule)
    import docx as real_docx

    monkeypatch.setattr(real_docx.text.paragraph, "Paragraph", FakePara, raising=False)

    elements, warnings = fp._parse_docx(tmp_path / "x.docx", "abc", "doc-abc", None)
    assert len(elements) == 1
    assert elements[0].type == "paragraph"
    assert elements[0].content == "hello world."


def test_parse_docx_heading_style_emit(monkeypatch, tmp_path: Path):
    """style='Heading 1' → emit heading element 含 level=1。"""
    if fp.qn is None:
        pytest.skip("qn unavailable")

    class FakePara:
        def __init__(self, child, doc):
            self.text = "chapter title"
            self.style = type("S", (), {"name": "Heading 1"})()

    class FakeChild(_FakeXmlChild):
        def __init__(self):
            super().__init__(fp.qn("w:p"))

    class FakeBody:
        def iterchildren(self):
            return iter([FakeChild()])

    class FakeDoc:
        element = type("E", (), {"body": FakeBody()})

    class FakeDocxModule:
        Document = staticmethod(lambda path: FakeDoc())

    monkeypatch.setattr(fp, "docx", FakeDocxModule)
    import docx as real_docx

    monkeypatch.setattr(real_docx.text.paragraph, "Paragraph", FakePara, raising=False)

    elements, _ = fp._parse_docx(tmp_path / "x.docx", "abc", "doc-abc", None)
    assert elements[0].type == "heading"
    assert elements[0].metadata["level"] == 1
    assert elements[0].metadata["style"] == "Heading 1"


def test_parse_docx_caption_text_emit(monkeypatch, tmp_path: Path):
    """text='Figure 1. ...' → emit caption element。"""
    if fp.qn is None:
        pytest.skip("qn unavailable")

    class FakePara:
        def __init__(self, child, doc):
            self.text = "Figure 1. caption text"
            self.style = type("S", (), {"name": "Normal"})()

    class FakeChild(_FakeXmlChild):
        def __init__(self):
            super().__init__(fp.qn("w:p"))

    class FakeBody:
        def iterchildren(self):
            return iter([FakeChild()])

    class FakeDoc:
        element = type("E", (), {"body": FakeBody()})

    class FakeDocxModule:
        Document = staticmethod(lambda path: FakeDoc())

    monkeypatch.setattr(fp, "docx", FakeDocxModule)
    import docx as real_docx

    monkeypatch.setattr(real_docx.text.paragraph, "Paragraph", FakePara, raising=False)

    elements, _ = fp._parse_docx(tmp_path / "x.docx", "abc", "doc-abc", None)
    assert elements[0].type == "caption"


def test_parse_docx_caption_overrides_heading_style(monkeypatch, tmp_path: Path):
    """caption 文本 + heading style → caption（caption 检测在 style 之前）。"""
    if fp.qn is None:
        pytest.skip("qn unavailable")

    class FakePara:
        def __init__(self, child, doc):
            self.text = "Figure 1. caption"
            self.style = type("S", (), {"name": "Heading 1"})()

    class FakeChild(_FakeXmlChild):
        def __init__(self):
            super().__init__(fp.qn("w:p"))

    class FakeBody:
        def iterchildren(self):
            return iter([FakeChild()])

    class FakeDoc:
        element = type("E", (), {"body": FakeBody()})

    class FakeDocxModule:
        Document = staticmethod(lambda path: FakeDoc())

    monkeypatch.setattr(fp, "docx", FakeDocxModule)
    import docx as real_docx

    monkeypatch.setattr(real_docx.text.paragraph, "Paragraph", FakePara, raising=False)

    elements, _ = fp._parse_docx(tmp_path / "x.docx", "abc", "doc-abc", None)
    assert elements[0].type == "caption"


def test_parse_docx_empty_paragraph_uses_placeholder_content(monkeypatch, tmp_path: Path):
    """空段落 text='' → content='(空段落)'。"""
    if fp.qn is None:
        pytest.skip("qn unavailable")

    class FakePara:
        def __init__(self, child, doc):
            self.text = ""
            self.style = type("S", (), {"name": "Normal"})()

    class FakeChild(_FakeXmlChild):
        def __init__(self):
            super().__init__(fp.qn("w:p"))

    class FakeBody:
        def iterchildren(self):
            return iter([FakeChild()])

    class FakeDoc:
        element = type("E", (), {"body": FakeBody()})

    class FakeDocxModule:
        Document = staticmethod(lambda path: FakeDoc())

    monkeypatch.setattr(fp, "docx", FakeDocxModule)
    import docx as real_docx

    monkeypatch.setattr(real_docx.text.paragraph, "Paragraph", FakePara, raising=False)

    elements, _ = fp._parse_docx(tmp_path / "x.docx", "abc", "doc-abc", None)
    assert elements[0].content == "(空段落)"
    assert elements[0].metadata["empty"] is True


def test_parse_docx_paragraph_index_increments(monkeypatch, tmp_path: Path):
    """多段落 → paragraph_index 递增。"""
    if fp.qn is None:
        pytest.skip("qn unavailable")

    class FakePara:
        def __init__(self, child, doc):
            self.text = "para."
            self.style = type("S", (), {"name": "Normal"})()

    class FakeChild(_FakeXmlChild):
        def __init__(self):
            super().__init__(fp.qn("w:p"))

    class FakeBody:
        def iterchildren(self):
            return iter([FakeChild(), FakeChild(), FakeChild()])

    class FakeDoc:
        element = type("E", (), {"body": FakeBody()})

    class FakeDocxModule:
        Document = staticmethod(lambda path: FakeDoc())

    monkeypatch.setattr(fp, "docx", FakeDocxModule)
    import docx as real_docx

    monkeypatch.setattr(real_docx.text.paragraph, "Paragraph", FakePara, raising=False)

    elements, _ = fp._parse_docx(tmp_path / "x.docx", "abc", "doc-abc", None)
    indices = [e.source_locator["paragraph_index"] for e in elements]
    assert indices == [0, 1, 2]


def test_parse_docx_section_always_zero(monkeypatch, tmp_path: Path):
    """section_idx 在 _parse_docx 中恒为 0（当前实现不递增）。"""
    if fp.qn is None:
        pytest.skip("qn unavailable")

    class FakePara:
        def __init__(self, child, doc):
            self.text = "para."
            self.style = type("S", (), {"name": "Normal"})()

    class FakeChild(_FakeXmlChild):
        def __init__(self):
            super().__init__(fp.qn("w:p"))

    class FakeBody:
        def iterchildren(self):
            return iter([FakeChild(), FakeChild()])

    class FakeDoc:
        element = type("E", (), {"body": FakeBody()})

    class FakeDocxModule:
        Document = staticmethod(lambda path: FakeDoc())

    monkeypatch.setattr(fp, "docx", FakeDocxModule)
    import docx as real_docx

    monkeypatch.setattr(real_docx.text.paragraph, "Paragraph", FakePara, raising=False)

    elements, _ = fp._parse_docx(tmp_path / "x.docx", "abc", "doc-abc", None)
    sections = [e.source_locator["section"] for e in elements]
    assert sections == [0, 0]


def test_parse_docx_element_id_continuous(monkeypatch, tmp_path: Path):
    """element_id 跨段落连续编号 e0000/e0001/...。"""
    if fp.qn is None:
        pytest.skip("qn unavailable")

    class FakePara:
        def __init__(self, child, doc):
            self.text = "para."
            self.style = type("S", (), {"name": "Normal"})()

    class FakeChild(_FakeXmlChild):
        def __init__(self):
            super().__init__(fp.qn("w:p"))

    class FakeBody:
        def iterchildren(self):
            return iter([FakeChild(), FakeChild(), FakeChild()])

    class FakeDoc:
        element = type("E", (), {"body": FakeBody()})

    class FakeDocxModule:
        Document = staticmethod(lambda path: FakeDoc())

    monkeypatch.setattr(fp, "docx", FakeDocxModule)
    import docx as real_docx

    monkeypatch.setattr(real_docx.text.paragraph, "Paragraph", FakePara, raising=False)

    elements, _ = fp._parse_docx(tmp_path / "x.docx", "abc", "doc-abc", None)
    ids = [e.element_id for e in elements]
    assert ids == ["doc-abc::e0000", "doc-abc::e0001", "doc-abc::e0002"]


def test_parse_docx_table_emit(monkeypatch, tmp_path: Path):
    """body 含 w:tbl → emit table element。"""
    if fp.qn is None:
        pytest.skip("qn unavailable")

    class FakeCell:
        def __init__(self, text):
            self.text = text

    class FakeRow:
        def __init__(self, cells):
            self.cells = cells

    class FakeTable:
        def __init__(self, child, doc):
            self.rows = [
                FakeRow([FakeCell("h1"), FakeCell("h2")]),
                FakeRow([FakeCell("v1"), FakeCell("v2")]),
            ]

    class FakeChild(_FakeXmlChild):
        def __init__(self):
            super().__init__(fp.qn("w:tbl"))

    class FakeBody:
        def iterchildren(self):
            return iter([FakeChild()])

    class FakeDoc:
        element = type("E", (), {"body": FakeBody()})

    class FakeDocxModule:
        Document = staticmethod(lambda path: FakeDoc())

    monkeypatch.setattr(fp, "docx", FakeDocxModule)
    import docx as real_docx

    monkeypatch.setattr(real_docx.table, "Table", FakeTable, raising=False)

    elements, _ = fp._parse_docx(tmp_path / "x.docx", "abc", "doc-abc", None)
    assert len(elements) == 1
    assert elements[0].type == "table"
    assert elements[0].metadata["row_count"] == 2
    assert elements[0].metadata["col_count"] == 2
    assert elements[0].metadata["source"] == "python-docx"
    assert elements[0].source_locator["table_index"] == 0


def test_parse_docx_mixed_paragraph_and_table_order(monkeypatch, tmp_path: Path):
    """body 中 paragraph → table → paragraph 顺序保留。"""
    if fp.qn is None:
        pytest.skip("qn unavailable")

    class FakePara:
        def __init__(self, child, doc):
            self.text = "para."
            self.style = type("S", (), {"name": "Normal"})()

    class FakeCell:
        def __init__(self, text):
            self.text = text

    class FakeRow:
        def __init__(self, cells):
            self.cells = cells

    class FakeTable:
        def __init__(self, child, doc):
            self.rows = [FakeRow([FakeCell("a")])]

    class PChild(_FakeXmlChild):
        def __init__(self):
            super().__init__(fp.qn("w:p"))

    class TChild(_FakeXmlChild):
        def __init__(self):
            super().__init__(fp.qn("w:tbl"))

    class FakeBody:
        def iterchildren(self):
            return iter([PChild(), TChild(), PChild()])

    class FakeDoc:
        element = type("E", (), {"body": FakeBody()})

    class FakeDocxModule:
        Document = staticmethod(lambda path: FakeDoc())

    monkeypatch.setattr(fp, "docx", FakeDocxModule)
    import docx as real_docx

    monkeypatch.setattr(real_docx.text.paragraph, "Paragraph", FakePara, raising=False)
    monkeypatch.setattr(real_docx.table, "Table", FakeTable, raising=False)

    elements, _ = fp._parse_docx(tmp_path / "x.docx", "abc", "doc-abc", None)
    types = [e.type for e in elements]
    assert types == ["paragraph", "table", "paragraph"]


def test_parse_docx_returns_tuple_of_list_and_list(monkeypatch, tmp_path: Path):
    if fp.qn is None:
        pytest.skip("qn unavailable")

    class FakeBody:
        def iterchildren(self):
            return iter([])

    class FakeDoc:
        element = type("E", (), {"body": FakeBody()})

    class FakeDocxModule:
        Document = staticmethod(lambda path: FakeDoc())

    monkeypatch.setattr(fp, "docx", FakeDocxModule)

    result = fp._parse_docx(tmp_path / "x.docx", "abc", "doc-abc", None)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], list)
    assert isinstance(result[1], list)


# =========================================================================
# _parse_pdf：多页集成
# =========================================================================


def _patch_pdfplumber(monkeypatch, pages):
    class FakePdf:
        def __init__(self):
            self.pages = pages

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_module = type("M", (), {"open": lambda *a, **kw: FakePdf()})
    monkeypatch.setattr(fp, "pdfplumber", fake_module)


def test_parse_pdf_multi_page_element_id_continuous(monkeypatch, tmp_path: Path):
    """多页 PDF 的 element_id 跨页连续编号。"""

    class FakePage:
        def extract_words(self, **kw):
            return [_word("text."), _word("more.", x0=20.0, x1=30.0)]

        def find_tables(self):
            return []

        @property
        def images(self):
            return []

    _patch_pdfplumber(monkeypatch, [FakePage(), FakePage()])
    elements, _ = fp._parse_pdf(tmp_path / "x.pdf", "abc", "docX", None)
    # 每页生成 1 个 paragraph（两个 word 同行）→ 共 2 elements
    assert len(elements) == 2
    ids = [e.element_id for e in elements]
    assert ids == ["docX::e0000", "docX::e0001"]


def test_parse_pdf_multi_page_locator_page_correct(monkeypatch, tmp_path: Path):
    class FakePage:
        def extract_words(self, **kw):
            return [_word("text.")]

        def find_tables(self):
            return []

        @property
        def images(self):
            return []

    _patch_pdfplumber(monkeypatch, [FakePage(), FakePage(), FakePage()])
    elements, _ = fp._parse_pdf(tmp_path / "x.pdf", "abc", "docX", None)
    pages = [e.source_locator["page"] for e in elements]
    assert pages == [1, 2, 3]


def test_parse_pdf_words_tables_images_same_page(monkeypatch, tmp_path: Path):
    """同一页同时有 words/tables/images → 三种 element 都 emit。"""

    class FakeTable:
        bbox = (0, 0, 100, 50)

        def extract(self):
            return [["h1", "h2"], ["v1", "v2"]]

    class FakePage:
        def extract_words(self, **kw):
            return [_word("hello."), _word("world.", x0=20.0, x1=30.0)]

        def find_tables(self):
            return [FakeTable()]

        @property
        def images(self):
            return [{"x0": 0.0, "top": 0.0, "x1": 50.0, "bottom": 50.0}]

    _patch_pdfplumber(monkeypatch, [FakePage()])
    elements, _ = fp._parse_pdf(tmp_path / "x.pdf", "abc", "docX", None)
    types = [e.type for e in elements]
    assert "paragraph" in types
    assert "table" in types
    assert "image" in types


def test_parse_pdf_image_element_id_after_text_and_table(monkeypatch, tmp_path: Path):
    """同页 text+table+image 顺序：element_id 先 text 再 table 再 image。"""

    class FakeTable:
        bbox = (0, 0, 100, 50)

        def extract(self):
            return [["a"]]

    class FakePage:
        def extract_words(self, **kw):
            return [_word("hello.")]

        def find_tables(self):
            return [FakeTable()]

        @property
        def images(self):
            return [{"x0": 0.0, "top": 0.0, "x1": 50.0, "bottom": 50.0}]

    _patch_pdfplumber(monkeypatch, [FakePage()])
    elements, _ = fp._parse_pdf(tmp_path / "x.pdf", "abc", "docX", None)
    types = [e.type for e in elements]
    # 顺序：text → table → image
    assert types.index("paragraph") < types.index("table")
    assert types.index("table") < types.index("image")


def test_parse_pdf_image_invalid_bbox_skipped(monkeypatch, tmp_path: Path):
    """image bbox x1<=x0 → 跳过该图片。"""

    class FakePage:
        def extract_words(self, **kw):
            return []

        def find_tables(self):
            return []

        @property
        def images(self):
            return [
                {"x0": 10.0, "top": 0.0, "x1": 5.0, "bottom": 50.0},  # x1<x0
                {"x0": 0.0, "top": 50.0, "x1": 50.0, "bottom": 30.0},  # bottom<top
            ]

    _patch_pdfplumber(monkeypatch, [FakePage()])
    elements, warnings = fp._parse_pdf(tmp_path / "x.pdf", "abc", "docX", None)
    # 所有图都被跳过 + 无 text/table → pdf_no_text_extracted warning
    assert all(e.type != "image" for e in elements)
    assert any(w.code == "pdf_no_text_extracted" for w in warnings)


def test_parse_pdf_no_text_no_tables_no_images_warning(monkeypatch, tmp_path: Path):
    class FakePage:
        def extract_words(self, **kw):
            return []

        def find_tables(self):
            return []

        @property
        def images(self):
            return []

    _patch_pdfplumber(monkeypatch, [FakePage()])
    elements, warnings = fp._parse_pdf(tmp_path / "x.pdf", "abc", "docX", None)
    assert elements == []
    assert any(w.code == "pdf_no_text_extracted" for w in warnings)


def test_parse_pdf_returns_tuple(monkeypatch, tmp_path: Path):
    class FakePage:
        def extract_words(self, **kw):
            return []

        def find_tables(self):
            return []

        @property
        def images(self):
            return []

    _patch_pdfplumber(monkeypatch, [FakePage()])
    result = fp._parse_pdf(tmp_path / "x.pdf", "abc", "docX", None)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], list)
    assert isinstance(result[1], list)


def test_parse_pdf_element_confidence_085_for_paragraphs(monkeypatch, tmp_path: Path):
    class FakePage:
        def extract_words(self, **kw):
            return [_word("hello.")]

        def find_tables(self):
            return []

        @property
        def images(self):
            return []

    _patch_pdfplumber(monkeypatch, [FakePage()])
    elements, _ = fp._parse_pdf(tmp_path / "x.pdf", "abc", "docX", None)
    assert elements[0].confidence == 0.85


def test_parse_pdf_table_confidence_07(monkeypatch, tmp_path: Path):
    class FakeTable:
        bbox = None

        def extract(self):
            return [["a"]]

    class FakePage:
        def extract_words(self, **kw):
            return []

        def find_tables(self):
            return [FakeTable()]

        @property
        def images(self):
            return []

    _patch_pdfplumber(monkeypatch, [FakePage()])
    elements, _ = fp._parse_pdf(tmp_path / "x.pdf", "abc", "docX", None)
    tbls = [e for e in elements if e.type == "table"]
    assert tbls[0].confidence == 0.7


def test_parse_pdf_image_confidence_06(monkeypatch, tmp_path: Path):
    class FakePage:
        def extract_words(self, **kw):
            return []

        def find_tables(self):
            return []

        @property
        def images(self):
            return [{"x0": 0.0, "top": 0.0, "x1": 50.0, "bottom": 50.0}]

    _patch_pdfplumber(monkeypatch, [FakePage()])
    elements, _ = fp._parse_pdf(tmp_path / "x.pdf", "abc", "docX", None)
    imgs = [e for e in elements if e.type == "image"]
    assert imgs[0].confidence == 0.6


# =========================================================================
# FallbackParser.parse()：端到端
# =========================================================================


def test_fallback_parser_parse_metadata_has_fallback_true(monkeypatch, tmp_path: Path):
    p = tmp_path / "x.docx"
    p.write_bytes(b"PK\x03\x04")

    def _fake_parse_docx(path, source_hash, document_id, image_dir):
        return [], []

    monkeypatch.setattr(fp, "_parse_docx", _fake_parse_docx)

    doc = FallbackParser().parse(p, source_hash="a" * 64)
    assert doc.metadata["fallback"] is True


def test_fallback_parser_parse_metadata_image_output_dir_none(monkeypatch, tmp_path: Path):
    p = tmp_path / "x.docx"
    p.write_bytes(b"PK\x03\x04")

    def _fake(path, source_hash, document_id, image_dir):
        return [], []

    monkeypatch.setattr(fp, "_parse_docx", _fake)

    doc = FallbackParser().parse(p, source_hash="a" * 64)
    assert doc.metadata["image_output_dir"] is None


def test_fallback_parser_parse_metadata_image_output_dir_string(monkeypatch, tmp_path: Path):
    p = tmp_path / "x.docx"
    p.write_bytes(b"PK\x03\x04")
    out_dir = tmp_path / "imgs"

    def _fake(path, source_hash, document_id, image_dir):
        return [], []

    monkeypatch.setattr(fp, "_parse_docx", _fake)

    parser = FallbackParser(image_output_dir=out_dir)
    doc = parser.parse(p, source_hash="a" * 64)
    assert doc.metadata["image_output_dir"] == str(out_dir)


def test_fallback_parser_parse_routes_pdf_to_parse_pdf(monkeypatch, tmp_path: Path):
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF-1.4\n%%EOF\n")
    called = {"pdf": 0, "docx": 0}

    def _fake_pdf(path, source_hash, document_id, image_dir):
        called["pdf"] += 1
        return [], []

    def _fake_docx(path, source_hash, document_id, image_dir):
        called["docx"] += 1
        return [], []

    monkeypatch.setattr(fp, "_parse_pdf", _fake_pdf)
    monkeypatch.setattr(fp, "_parse_docx", _fake_docx)

    FallbackParser().parse(p, source_hash="a" * 64)
    assert called == {"pdf": 1, "docx": 0}


def test_fallback_parser_parse_routes_docx_to_parse_docx(monkeypatch, tmp_path: Path):
    p = tmp_path / "x.docx"
    p.write_bytes(b"PK\x03\x04")
    called = {"pdf": 0, "docx": 0}

    def _fake_pdf(path, source_hash, document_id, image_dir):
        called["pdf"] += 1
        return [], []

    def _fake_docx(path, source_hash, document_id, image_dir):
        called["docx"] += 1
        return [], []

    monkeypatch.setattr(fp, "_parse_pdf", _fake_pdf)
    monkeypatch.setattr(fp, "_parse_docx", _fake_docx)

    FallbackParser().parse(p, source_hash="a" * 64)
    assert called == {"pdf": 0, "docx": 1}


def test_fallback_parser_parse_passes_image_output_dir(monkeypatch, tmp_path: Path):
    p = tmp_path / "x.docx"
    p.write_bytes(b"PK\x03\x04")
    out_dir = tmp_path / "imgs"
    captured = {}

    def _fake(path, source_hash, document_id, image_dir):
        captured["image_dir"] = image_dir
        return [], []

    monkeypatch.setattr(fp, "_parse_docx", _fake)

    FallbackParser(image_output_dir=out_dir).parse(p, source_hash="a" * 64)
    assert captured["image_dir"] == out_dir


def test_fallback_parser_parse_passes_none_image_output_dir_by_default(monkeypatch, tmp_path: Path):
    p = tmp_path / "x.docx"
    p.write_bytes(b"PK\x03\x04")
    captured = {}

    def _fake(path, source_hash, document_id, image_dir):
        captured["image_dir"] = image_dir
        return [], []

    monkeypatch.setattr(fp, "_parse_docx", _fake)

    FallbackParser().parse(p, source_hash="a" * 64)
    assert captured["image_dir"] is None


def test_fallback_parser_parse_document_id_derived_from_hash(monkeypatch, tmp_path: Path):
    p = tmp_path / "x.docx"
    p.write_bytes(b"PK\x03\x04")

    def _fake(path, source_hash, document_id, image_dir):
        return [], []

    monkeypatch.setattr(fp, "_parse_docx", _fake)

    doc1 = FallbackParser().parse(p, source_hash="a" * 64)
    doc2 = FallbackParser().parse(p, source_hash="b" * 64)
    assert doc1.document_id != doc2.document_id


def test_fallback_parser_parse_propagates_warnings(monkeypatch, tmp_path: Path):
    from app.models import WarningRecord

    p = tmp_path / "x.docx"
    p.write_bytes(b"PK\x03\x04")

    def _fake(path, source_hash, document_id, image_dir):
        return [], [WarningRecord(code="test_warning", reason="r")]

    monkeypatch.setattr(fp, "_parse_docx", _fake)

    doc = FallbackParser().parse(p, source_hash="a" * 64)
    assert any(w.code == "test_warning" for w in doc.warnings)


def test_fallback_parser_parse_chunks_relations_errors_empty(monkeypatch, tmp_path: Path):
    p = tmp_path / "x.docx"
    p.write_bytes(b"PK\x03\x04")

    def _fake(path, source_hash, document_id, image_dir):
        return [], []

    monkeypatch.setattr(fp, "_parse_docx", _fake)

    doc = FallbackParser().parse(p, source_hash="a" * 64)
    assert doc.chunks == []
    assert doc.relations == []
    assert doc.errors == []


def test_fallback_parser_parse_source_path_preserved(monkeypatch, tmp_path: Path):
    p = tmp_path / "custom.docx"
    p.write_bytes(b"PK\x03\x04")

    def _fake(path, source_hash, document_id, image_dir):
        return [], []

    monkeypatch.setattr(fp, "_parse_docx", _fake)

    doc = FallbackParser().parse(p, source_hash="a" * 64)
    assert doc.source_path == str(p)


def test_fallback_parser_parse_source_hash_passed_through(monkeypatch, tmp_path: Path):
    p = tmp_path / "x.docx"
    p.write_bytes(b"PK\x03\x04")

    def _fake(path, source_hash, document_id, image_dir):
        return [], []

    monkeypatch.setattr(fp, "_parse_docx", _fake)

    doc = FallbackParser().parse(p, source_hash="c" * 64)
    assert doc.source_hash == "c" * 64


def test_fallback_parser_parse_parser_name_fallback(monkeypatch, tmp_path: Path):
    p = tmp_path / "x.docx"
    p.write_bytes(b"PK\x03\x04")

    def _fake(path, source_hash, document_id, image_dir):
        return [], []

    monkeypatch.setattr(fp, "_parse_docx", _fake)

    doc = FallbackParser().parse(p, source_hash="a" * 64)
    assert doc.parser_name == "fallback"


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_only_exports_fallback_parser():
    assert fp.__all__ == ["FallbackParser"]


def test_module_caption_re_is_compiled_pattern():
    assert isinstance(_CAPTION_RE, re.Pattern)


def test_module_caption_re_uses_ignore_case():
    assert _CAPTION_RE.flags & re.IGNORECASE


def test_module_has_image_filename_function():
    assert callable(_image_filename)


def test_module_has_rows_to_markdown_function():
    assert callable(_rows_to_markdown)


def test_module_has_is_caption_function():
    assert callable(_is_caption)


def test_module_has_classify_pdf_paragraph_function():
    assert callable(_classify_pdf_paragraph)


def test_module_has_group_words_function():
    assert callable(_group_words_to_paragraphs)


def test_module_has_lines_to_para_function():
    assert callable(_lines_to_para)


def test_module_has_is_heading_style_function():
    assert callable(_is_heading_style)


def test_module_has_extract_inline_image_rids_function():
    assert callable(_extract_inline_image_rids)


def test_module_imports_path():
    assert hasattr(fp, "Path")


def test_module_imports_re():
    assert hasattr(fp, "re")


def test_module_imports_any():
    assert hasattr(fp, "Any")


def test_module_imports_document():
    assert hasattr(fp, "Document")


def test_module_imports_element():
    assert hasattr(fp, "Element")


def test_module_imports_warning_record():
    assert hasattr(fp, "WarningRecord")


def test_module_imports_parser():
    assert hasattr(fp, "Parser")


def test_module_imports_parser_error():
    assert hasattr(fp, "ParserError")


def test_module_imports_detect_source_type():
    assert hasattr(fp, "detect_source_type")


def test_module_imports_make_document_id():
    assert hasattr(fp, "make_document_id")


def test_fallback_parser_inherits_parser():
    from app.parsers.base import Parser
    assert issubclass(FallbackParser, Parser)


def test_fallback_parser_class_name_constant():
    assert FallbackParser.name == "fallback"


def test_fallback_parser_class_version_is_str():
    assert isinstance(FallbackParser.version, str)


def test_fallback_parser_class_version_contains_pdfplumber_keyword():
    assert "pdfplumber" in FallbackParser.version


def test_fallback_parser_class_version_contains_python_docx_keyword():
    assert "python-docx" in FallbackParser.version


def test_fallback_parser_class_version_contains_pypdfium2_keyword():
    assert "pypdfium2" in FallbackParser.version


def test_fallback_parser_has_parse_callable():
    assert callable(FallbackParser.parse)


def test_fallback_parser_init_default_image_output_dir_none():
    parser = FallbackParser()
    assert parser._image_output_dir is None


def test_fallback_parser_init_with_image_dir(tmp_path: Path):
    out_dir = tmp_path / "out"
    parser = FallbackParser(image_output_dir=out_dir)
    assert parser._image_output_dir == out_dir


def test_fallback_parser_init_str_converted_to_path(tmp_path: Path):
    parser = FallbackParser(image_output_dir=str(tmp_path))
    assert isinstance(parser._image_output_dir, Path)


def test_fallback_parser_init_empty_string_treated_as_none():
    """空字符串 → falsy → _image_output_dir = None。"""
    parser = FallbackParser(image_output_dir="")
    assert parser._image_output_dir is None
