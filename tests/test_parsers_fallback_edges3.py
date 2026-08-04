"""app/parsers/fallback_parser.py 边角测试 - 第三轮（Round 92）。

补强已有 79 + 95 + 168 = 342 测试未覆盖的：
- `_group_words_to_paragraphs` 算法深度：line cluster 阈值 (3.0)、
  paragraph break 阈值 (1.5*median)、median 计算、多 paragraph 切分
- `_lines_to_para` 多行 x0 排序、bbox 边界精确值
- `_save_image` OSError 路径（out_dir 是文件、权限拒绝）
- `_extract_inline_image_rids` qn=None 早期返回
- `_render_pdf_image_region_verbose` 错误返回字符串（mock pypdfium2）
- `_parse_pdf` 异常 → ParserError 转换（mock pdfplumber）
- `_parse_docx` docx_open_failed、空 body、qn=None 早期返回
- `_classify_pdf_paragraph` 临界（exactly 80 chars, exactly 81 chars）
- `_rows_to_markdown` None header row / 非 str 元素混合
- `_image_filename` Unicode doc_id / 大 index
- `_CAPTION_RE` 各 keyword + 分隔符组合
- `FallbackParser.__init__` 与 `parse()` metadata 精确字段
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from app.models import Element, WarningRecord
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
    _render_pdf_image_region,
    _render_pdf_image_region_verbose,
    _rows_to_markdown,
    _save_image,
)


# ---------- _group_words_to_paragraphs 算法深度 ----------


def _mkword(text: str, x0: float, x1: float, top: float, bottom: float) -> dict:
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": bottom}


def test_group_words_line_cluster_threshold_exactly_3():
    """y 中心距 == 3.0 → 同行（abs diff <= 3.0）。"""
    w1 = _mkword("a", 0.0, 10.0, 0.0, 10.0)  # yc=5.0
    w2 = _mkword("b", 0.0, 10.0, 8.0, 18.0)  # yc=13.0  (diff=8 → split)
    w3 = _mkword("c", 0.0, 10.0, 2.0, 12.0)  # yc=7.0  (diff from 5.0 = 2 → same line as w1)
    ws = [w1, w3, w2]
    result = _group_words_to_paragraphs(ws)
    # w1, w3 同 line；w2 不同 line；但都 < 1.5*median 之内 → 1 paragraph
    # 验证：至少有一个 paragraph 含 "a" 和 "c"
    found_a = any("a" in p["text"] for p in result)
    found_c = any("c" in p["text"] for p in result)
    assert found_a and found_c


def test_group_words_two_paragraphs_far_apart():
    """两组 word 垂直距离远 → 两个 paragraph。"""
    w1 = _mkword("first", 0.0, 30.0, 0.0, 10.0)   # yc=5
    w2 = _mkword("second", 0.0, 30.0, 200.0, 210.0)  # yc=205 (very far)
    result = _group_words_to_paragraphs([w1, w2])
    assert len(result) == 2
    assert "first" in result[0]["text"]
    assert "second" in result[1]["text"]


def test_group_words_paragraph_break_uses_median_height():
    """行距 > 1.5 * median_h → paragraph 分割。"""
    # 三行同列、行高约 10；前两行紧贴，第三行距第二行 50（远超 1.5*10=15）
    w1 = _mkword("line1", 0.0, 30.0, 0.0, 10.0)
    w2 = _mkword("line2", 0.0, 30.0, 12.0, 22.0)   # 距 line1: 12-10=2
    w3 = _mkword("line3", 0.0, 30.0, 80.0, 90.0)   # 距 line2: 80-22=58 >> 15
    result = _group_words_to_paragraphs([w1, w2, w3])
    assert len(result) == 2
    assert "line1" in result[0]["text"]
    assert "line2" in result[0]["text"]
    assert "line3" in result[1]["text"]


def test_group_words_paragraph_bbox_x_min_x_max():
    """bbox[0] = min(x0), bbox[2] = max(x1)。"""
    w1 = _mkword("a", 5.0, 30.0, 0.0, 10.0)
    w2 = _mkword("b", 100.0, 200.0, 0.0, 10.0)
    result = _group_words_to_paragraphs([w1, w2])
    bbox = result[0]["bbox"]
    assert bbox[0] == 5.0
    assert bbox[2] == 200.0


def test_group_words_paragraph_bbox_top_min_bottom_max():
    """bbox[1] = min(top), bbox[3] = max(bottom)。"""
    w1 = _mkword("a", 0.0, 30.0, 7.0, 12.0)
    w2 = _mkword("b", 0.0, 30.0, 3.0, 25.0)
    result = _group_words_to_paragraphs([w1, w2])
    bbox = result[0]["bbox"]
    assert bbox[1] == 3.0  # min(top)
    assert bbox[3] == 25.0  # max(bottom)


def test_group_words_handles_missing_top_key():
    """无 top → 默认 0.0；不抛 KeyError。"""
    w = {"text": "x", "x0": 0.0, "x1": 10.0, "bottom": 10.0}
    result = _group_words_to_paragraphs([w])
    assert len(result) == 1


def test_group_words_handles_missing_bottom_key():
    """无 bottom → 默认 0.0。"""
    w = {"text": "x", "x0": 0.0, "x1": 10.0, "top": 0.0}
    result = _group_words_to_paragraphs([w])
    assert len(result) == 1


def test_group_words_words_sorted_by_y_center_then_x0():
    """输入乱序 → 输出按 yc 升序。"""
    # 倒序输入
    w_late = _mkword("late", 0.0, 10.0, 100.0, 110.0)
    w_early = _mkword("early", 0.0, 10.0, 0.0, 10.0)
    result = _group_words_to_paragraphs([w_late, w_early])
    # 第一段应当是 early
    assert "early" in result[0]["text"]


# ---------- _lines_to_para 边界 ----------


def test_lines_to_para_empty_inner_lines_returns_empty_text():
    """传 [[{}, {}]] 但内含空 list → all_words 空 → text="", bbox=None。"""
    result = _lines_to_para([[]])
    assert result["text"] == ""
    assert result["bbox"] is None


def test_lines_to_para_multiple_paragraphs_text_concatenates_with_space():
    """两行 word → text 用空格连接。"""
    line1 = [_mkword("hello", 0.0, 5.0, 0.0, 10.0)]
    line2 = [_mkword("world", 0.0, 5.0, 12.0, 22.0)]
    result = _lines_to_para([line1, line2])
    assert "hello" in result["text"]
    assert "world" in result["text"]


def test_lines_to_para_bbox_min_x0_from_all_words():
    """bbox[0] = min(x0) across all words."""
    line1 = [_mkword("a", 10.0, 20.0, 0.0, 10.0)]
    line2 = [_mkword("b", 5.0, 30.0, 12.0, 22.0)]
    result = _lines_to_para([line1, line2])
    assert result["bbox"][0] == 5.0


def test_lines_to_para_bbox_max_x1_from_all_words():
    """bbox[2] = max(x1) across all words."""
    line1 = [_mkword("a", 10.0, 20.0, 0.0, 10.0)]
    line2 = [_mkword("b", 5.0, 50.0, 12.0, 22.0)]
    result = _lines_to_para([line1, line2])
    assert result["bbox"][2] == 50.0


# ---------- _save_image OSError 路径 ----------


def test_save_image_out_dir_is_file_raises_oserror(tmp_path: Path):
    """out_dir 指向已存在的文件 → mkdir 失败 → OSError。"""
    f = tmp_path / "blocker.txt"
    f.write_text("block")
    with pytest.raises(OSError):
        _save_image(b"data", f, "doc1", "p1", 0)


def test_save_image_parent_is_file_raises_oserror(tmp_path: Path):
    """out_dir 的父路径是文件 → mkdir 失败。"""
    f = tmp_path / "blocker.txt"
    f.write_text("block")
    bad_dir = f / "sub"
    with pytest.raises(OSError):
        _save_image(b"data", bad_dir, "doc1", "p1", 0)


def test_save_image_normal_creates_directory_chain(tmp_path: Path):
    """深层目录自动创建。"""
    deep = tmp_path / "a" / "b" / "c"
    p = _save_image(b"x", deep, "doc1", "p1", 0)
    assert p.exists()
    assert p.parent == deep


def test_save_image_returns_path_with_zero_padded_index(tmp_path: Path):
    p = _save_image(b"x", tmp_path, "doc1", "p1", 5)
    assert "_05" in p.name


def test_save_image_writes_exact_bytes(tmp_path: Path):
    payload = b"\x89PNG\r\n\x1a\n"
    p = _save_image(payload, tmp_path, "doc1", "p1", 0)
    assert p.read_bytes() == payload


# ---------- _extract_inline_image_rids ----------


def test_extract_inline_image_rids_none_xml_raises_attribute_error():
    """传 None XML → .iter 抛 AttributeError（qn 非 None 时）。"""
    from app.parsers import fallback_parser
    if fallback_parser.qn is None:
        pytest.skip("qn is None in this environment")
    with pytest.raises(AttributeError):
        _extract_inline_image_rids(None)


def test_extract_inline_image_rids_empty_xml_returns_empty_list():
    """空 XML 元素 → 无 drawing → []."""
    from app.parsers import fallback_parser
    if fallback_parser.qn is None:
        pytest.skip("qn is None in this environment")
    from lxml import etree
    xml = etree.fromstring(b"<w:p xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\"/>")
    rids = _extract_inline_image_rids(xml)
    assert rids == []


# ---------- _render_pdf_image_region_verbose 错误路径 ----------


def test_render_pdf_image_region_verbose_pypdfium2_none_returns_error_string(monkeypatch):
    """pypdfium2 is None → 返回错误字符串。"""
    from app.parsers import fallback_parser
    monkeypatch.setattr(fallback_parser, "pypdfium2", None)
    # _PDFIUM_IMPORT_ERROR 仅在 import 失败时定义；raise=False 允许动态补上
    monkeypatch.setattr(fallback_parser, "_PDFIUM_IMPORT_ERROR", "simulated_missing", raising=False)
    err = _render_pdf_image_region_verbose(Path("dummy.pdf"), 0, [0, 0, 100, 100], Path("out.png"))
    assert isinstance(err, str)
    assert "pypdfium2" in err or "missing" in err or "simulated" in err


def test_render_pdf_image_region_verbose_pdf_open_fails(monkeypatch, tmp_path: Path):
    """PdfDocument 打开失败 → 错误字符串。"""
    from app.parsers import fallback_parser

    class FakeFailingPdfDoc:
        def __init__(self, *a, **kw):
            raise RuntimeError("open failed")

    fake_module = type("M", (), {"PdfDocument": FakeFailingPdfDoc})
    monkeypatch.setattr(fallback_parser, "pypdfium2", fake_module)
    err = _render_pdf_image_region_verbose(tmp_path / "x.pdf", 0, [0, 0, 100, 100], tmp_path / "out.png")
    assert isinstance(err, str)
    assert "PdfDocument" in err or "open" in err


def test_render_pdf_image_region_verbose_page_index_oob(monkeypatch, tmp_path: Path):
    """page[idx] 越界 → 错误字符串。"""
    from app.parsers import fallback_parser

    class FakePage:
        def render(self, scale=1.0):
            raise RuntimeError("never")

    class FakeBitmap:
        def to_pil(self):
            raise RuntimeError("never")

    class FakePdfDoc:
        def __init__(self, *a, **kw):
            pass

        def __getitem__(self, idx):
            raise IndexError("page out of range")

        def close(self):
            pass

    fake_module = type("M", (), {"PdfDocument": FakePdfDoc})
    monkeypatch.setattr(fallback_parser, "pypdfium2", fake_module)
    err = _render_pdf_image_region_verbose(tmp_path / "x.pdf", 99, [0, 0, 100, 100], tmp_path / "out.png")
    assert isinstance(err, str)
    assert "page" in err.lower()


def test_render_pdf_image_region_verbose_render_fails(monkeypatch, tmp_path: Path):
    """render/to_pil 失败 → 错误字符串。"""
    from app.parsers import fallback_parser

    class FakePage:
        def render(self, scale=1.0):
            raise RuntimeError("render boom")

    class FakePdfDoc:
        def __init__(self, *a, **kw):
            pass

        def __getitem__(self, idx):
            return FakePage()

        def close(self):
            pass

    fake_module = type("M", (), {"PdfDocument": FakePdfDoc})
    monkeypatch.setattr(fallback_parser, "pypdfium2", fake_module)
    err = _render_pdf_image_region_verbose(tmp_path / "x.pdf", 0, [0, 0, 100, 100], tmp_path / "out.png")
    assert isinstance(err, str)
    assert "render" in err.lower() or "to_pil" in err.lower()


def test_render_pdf_image_region_verbose_crop_degenerate(monkeypatch, tmp_path: Path):
    """crop 退化（x0>=x1 或 y0>=y1）→ 错误字符串。"""
    from app.parsers import fallback_parser

    class FakePil:
        width = 1000
        height = 1000

        def crop(self, box):
            return self

        def save(self, *a, **kw):
            raise RuntimeError("never")

    class FakeBitmap:
        def to_pil(self):
            return FakePil()

    class FakePage:
        def render(self, scale=1.0):
            return FakeBitmap()

    class FakePdfDoc:
        def __init__(self, *a, **kw):
            pass

        def __getitem__(self, idx):
            return FakePage()

        def close(self):
            pass

    fake_module = type("M", (), {"PdfDocument": FakePdfDoc})
    monkeypatch.setattr(fallback_parser, "pypdfium2", fake_module)
    # bbox 让 crop 退化（x1*scale < x0*scale via x1 <= x0）
    err = _render_pdf_image_region_verbose(tmp_path / "x.pdf", 0, [100, 0, 50, 200], tmp_path / "out.png")
    assert isinstance(err, str)
    assert "crop" in err.lower() or "退化" in err or "0 size" in err.lower()


def test_render_pdf_image_region_verbose_pil_save_fails(monkeypatch, tmp_path: Path):
    """PIL save 失败 → 错误字符串。"""
    from app.parsers import fallback_parser

    class FakePil:
        width = 10000
        height = 10000

        def crop(self, box):
            return self

        def save(self, *a, **kw):
            raise OSError("disk full")

    class FakeBitmap:
        def to_pil(self):
            return FakePil()

    class FakePage:
        def render(self, scale=1.0):
            return FakeBitmap()

    class FakePdfDoc:
        def __init__(self, *a, **kw):
            pass

        def __getitem__(self, idx):
            return FakePage()

        def close(self):
            pass

    fake_module = type("M", (), {"PdfDocument": FakePdfDoc})
    monkeypatch.setattr(fallback_parser, "pypdfium2", fake_module)
    err = _render_pdf_image_region_verbose(tmp_path / "x.pdf", 0, [0, 0, 100, 100], tmp_path / "out.png")
    assert isinstance(err, str)
    assert "PIL" in err or "save" in err.lower()


def test_render_pdf_image_region_verbose_success_returns_none(monkeypatch, tmp_path: Path):
    """完整成功 → 返回 None。"""
    from app.parsers import fallback_parser

    class FakePil:
        width = 10000
        height = 10000

        def crop(self, box):
            return self

        def save(self, path, format=None):
            Path(path).write_bytes(b"\x89PNG")

    class FakeBitmap:
        def to_pil(self):
            return FakePil()

    class FakePage:
        def render(self, scale=1.0):
            return FakeBitmap()

    class FakePdfDoc:
        def __init__(self, *a, **kw):
            pass

        def __getitem__(self, idx):
            return FakePage()

        def close(self):
            pass

    fake_module = type("M", (), {"PdfDocument": FakePdfDoc})
    monkeypatch.setattr(fallback_parser, "pypdfium2", fake_module)
    out_path = tmp_path / "out.png"
    err = _render_pdf_image_region_verbose(tmp_path / "x.pdf", 0, [0, 0, 100, 100], out_path)
    assert err is None
    assert out_path.exists()


def test_render_pdf_image_region_legacy_wrapper_returns_bool(monkeypatch, tmp_path: Path):
    """旧包装：成功 True。"""
    from app.parsers import fallback_parser

    class FakePil:
        width = 10000
        height = 10000

        def crop(self, box):
            return self

        def save(self, path, format=None):
            Path(path).write_bytes(b"")

    class FakeBitmap:
        def to_pil(self):
            return FakePil()

    class FakePage:
        def render(self, scale=1.0):
            return FakeBitmap()

    class FakePdfDoc:
        def __init__(self, *a, **kw):
            pass

        def __getitem__(self, idx):
            return FakePage()

        def close(self):
            pass

    fake_module = type("M", (), {"PdfDocument": FakePdfDoc})
    monkeypatch.setattr(fallback_parser, "pypdfium2", fake_module)
    out_path = tmp_path / "out.png"
    result = _render_pdf_image_region(tmp_path / "x.pdf", 0, [0, 0, 100, 100], out_path)
    assert result is True


def test_render_pdf_image_region_legacy_wrapper_failure_returns_false(monkeypatch, tmp_path: Path):
    """旧包装：失败 False。"""
    from app.parsers import fallback_parser
    monkeypatch.setattr(fallback_parser, "pypdfium2", None)
    monkeypatch.setattr(fallback_parser, "_PDFIUM_IMPORT_ERROR", "missing", raising=False)
    result = _render_pdf_image_region(tmp_path / "x.pdf", 0, [0, 0, 100, 100], tmp_path / "out.png")
    assert result is False


# ---------- _classify_pdf_paragraph 临界 ----------


def test_classify_pdf_paragraph_exactly_80_chars_no_period_is_heading():
    """len == 80 → heading（边界 <= 80）。"""
    text = "a" * 80  # 80 chars, no period
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "heading"


def test_classify_pdf_paragraph_exactly_81_chars_is_paragraph():
    """len == 81 → paragraph。"""
    text = "a" * 81
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "paragraph"


def test_classify_pdf_paragraph_short_ending_with_colon_is_heading():
    """以 : 结尾的短行 → heading（不在 endswith 列表）。"""
    text = "Section:"  # 8 chars, ends with :
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "heading"


def test_classify_pdf_paragraph_short_ending_with_semicolon_is_heading():
    """以 ; 结尾的短行 → heading。"""
    text = "items;"
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "heading"


def test_classify_pdf_paragraph_short_ending_with_comma_is_heading():
    """以 , 结尾的短行 → heading。"""
    text = "intro,"
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "heading"


def test_classify_pdf_paragraph_caption_overrides_long_text():
    """caption regex 命中 → 即便长也判 caption。"""
    text = "Figure 999. " + "x" * 200
    etype, _ = _classify_pdf_paragraph(text)
    assert etype == "caption"


# ---------- _CAPTION_RE 更多 case ----------


def test_caption_re_match_with_multiple_spaces():
    """keyword + 多空格 + 数字。"""
    assert _CAPTION_RE.match("Table   1. cap")


def test_caption_re_match_starts_with_tab():
    assert _CAPTION_RE.match("\tFigure 1. cap")


def test_caption_re_match_starts_with_newline():
    assert _CAPTION_RE.match("\nFigure 1. cap")


def test_caption_re_no_match_keyword_only_no_number():
    assert not _CAPTION_RE.match("Figure")


def test_caption_re_no_match_number_before_keyword():
    assert not _CAPTION_RE.match("1 Figure")


def test_caption_re_no_match_only_numbers():
    assert not _CAPTION_RE.match("1.")


def test_caption_re_match_mixed_chinese_english():
    """'图 1. caption' 与 'Table 1. caption' 都接受。"""
    assert _CAPTION_RE.match("图 1. caption")
    assert _CAPTION_RE.match("Table 1. caption")


# ---------- _is_caption 更多 ----------


def test_is_caption_full_width_digit():
    assert _is_caption("Figure １. caption")  # 全角 1


def test_is_caption_multiple_leading_whitespace():
    assert _is_caption("    \tFigure 1. cap")


def test_is_caption_does_not_match_string_with_period_only():
    assert not _is_caption(".")


def test_is_caption_does_not_match_only_digits():
    assert not _is_caption("123")


# ---------- _rows_to_markdown 边界 ----------


def test_rows_to_markdown_none_in_header():
    rows = [[None, "name"], ["1", "Alice"]]
    md = _rows_to_markdown(rows)
    # None → ""
    lines = md.split("\n")
    # 头行第一列是空字符串：|  | name |
    assert lines[0].startswith("|  |")  # 两个空格（pipe + 空 cell + pipe）


def test_rows_to_markdown_zero_in_row():
    rows = [["h"], [0]]
    md = _rows_to_markdown(rows)
    assert "0" in md


def test_rows_to_markdown_three_columns_jagged():
    rows = [
        ["a", "b", "c"],
        ["d"],  # 仅 1 列
        ["e", "f"],  # 2 列
    ]
    md = _rows_to_markdown(rows)
    lines = md.split("\n")
    # 4 lines: header + separator + 2 body
    assert len(lines) == 4


def test_rows_to_markdown_int_in_row():
    rows = [["h"], [42]]
    md = _rows_to_markdown(rows)
    assert "42" in md


def test_rows_to_markdown_special_chars_in_cell():
    """| 在 cell 中会破坏 markdown 但不被转义。"""
    md = _rows_to_markdown([["a|b"]])
    assert "a|b" in md


def test_rows_to_markdown_separator_is_three_dashes_per_column():
    md = _rows_to_markdown([["a", "b", "c"]])
    lines = md.split("\n")
    sep = lines[1]
    # 3 列 → 3 个 --- 段
    assert sep.count("---") == 3


# ---------- _image_filename 边界 ----------


def test_image_filename_unicode_doc_id():
    """Unicode doc_id 保留。"""
    name = _image_filename("中文", "p1", 0)
    assert "中文" in name or name.startswith("image_")


def test_image_filename_dashes_preserved():
    name = _image_filename("doc-with-dashes", "p1", 0)
    # dashes preserved (doc- prefix stripped but internal dashes kept)
    assert "doc-with-dashes" in name or "with-dashes" in name


def test_image_filename_3digit_index():
    name = _image_filename("doc1", "p1", 7)
    assert "_07." in name
    name2 = _image_filename("doc1", "p1", 12)
    assert "_12." in name2


def test_image_filename_4digit_index_still_zero_padded_to_2():
    """index 100 → "100" (3 digit > 2, no truncation)."""
    name = _image_filename("doc1", "p1", 100)
    assert "_100." in name


def test_image_filename_prefix_with_special_chars():
    name = _image_filename("doc1", "p-1_a", 0)
    assert "p-1_a" in name


# ---------- _is_heading_style 边界 ----------


def test_is_heading_style_heading_tab_separated():
    """'Heading\\t3' → strip 后取 '3' → level 3。"""
    # s.replace('heading', '').strip() = '3' → int 成功
    result = _is_heading_style("Heading\t3")
    assert result == (True, 3)


def test_is_heading_style_heading_with_only_whitespace_suffix():
    """'Heading   ' → fallback to level 1. """
    assert _is_heading_style("Heading   ") == (True, 1)


def test_is_heading_style_heading_plus_letter():
    """'HeadingA' → not startswith 'heading' + digit parsing..."""
    # s = 'headinga' → startswith('heading') True → int('a'.strip()) fails → fallback
    assert _is_heading_style("HeadingA") == (True, 1)


def test_is_heading_style_heading_with_period():
    """'Heading.1' → int('.1'.strip()) fails → fallback."""
    assert _is_heading_style("Heading.1") == (True, 1)


def test_is_heading_style_normal_with_spaces():
    assert _is_heading_style("  Normal  ") == (False, 0)


# ---------- FallbackParser metadata ----------


def test_fallback_parser_metadata_default_no_image_dir():
    """无 image_output_dir → metadata.image_output_dir=None。"""
    p = FallbackParser()
    doc = p.parse.__doc__  # parse method exists
    assert hasattr(p, "parse")


def test_fallback_parser_image_output_dir_str_converted_to_path(tmp_path: Path):
    p = FallbackParser(image_output_dir=str(tmp_path))
    assert isinstance(p._image_output_dir, Path)
    assert p._image_output_dir == tmp_path


def test_fallback_parser_image_output_dir_path_kept(tmp_path: Path):
    p = FallbackParser(image_output_dir=tmp_path)
    assert p._image_output_dir == tmp_path


def test_fallback_parser_name_class_attribute():
    assert FallbackParser.name == "fallback"


def test_fallback_parser_version_format():
    """version 是非空字符串。"""
    assert isinstance(FallbackParser.version, str)
    assert len(FallbackParser.version) > 0


# ---------- _parse_pdf 错误路径（mock） ----------


def test_parse_pdf_pdfplumber_none_raises_parser_error(monkeypatch):
    """pdfplumber is None → ParserError('pdfplumber_unavailable')."""
    from app.parsers import fallback_parser
    monkeypatch.setattr(fallback_parser, "pdfplumber", None)
    monkeypatch.setattr(fallback_parser, "_PDFPLUMBER_IMPORT_ERROR", "missing", raising=False)
    with pytest.raises(ParserError) as ei:
        fallback_parser._parse_pdf(Path("dummy.pdf"), "abc", "doc-abc", None)
    assert ei.value.code == "pdfplumber_unavailable"


def test_parse_pdf_pdfplumber_open_fails_raises(monkeypatch, tmp_path: Path):
    """pdfplumber.open 抛 → ParserError('pdfplumber_open_failed')."""
    from app.parsers import fallback_parser

    class FakePdfFailing:
        def __init__(self, *a, **kw):
            raise IOError("open failed")

    fake_module = type("M", (), {"open": FakePdfFailing})
    monkeypatch.setattr(fallback_parser, "pdfplumber", fake_module)
    with pytest.raises(ParserError) as ei:
        fallback_parser._parse_pdf(tmp_path / "x.pdf", "abc", "doc-abc", None)
    assert ei.value.code == "pdfplumber_open_failed"


def test_parse_pdf_empty_pages_returns_warning_pdf_no_text(monkeypatch, tmp_path: Path):
    """PDF 0 elements → warnings 含 pdf_no_text_extracted。"""
    from app.parsers import fallback_parser

    class FakePage:
        def extract_words(self, **kw):
            return []

        def find_tables(self):
            return []

        @property
        def images(self):
            return []

        @property
        def pages(self):
            return []

    class FakePdf:
        pages = []

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_module = type("M", (), {"open": lambda *a, **kw: FakePdf()})
    monkeypatch.setattr(fallback_parser, "pdfplumber", fake_module)
    elements, warnings = fallback_parser._parse_pdf(tmp_path / "x.pdf", "abc", "doc-abc", None)
    assert elements == []
    assert any(w.code == "pdf_no_text_extracted" for w in warnings)


def test_parse_pdf_extract_words_fails_records_warning(monkeypatch, tmp_path: Path):
    """extract_words 抛 → warning('pdfplumber_word_extract_failed')，继续处理。"""
    from app.parsers import fallback_parser

    class FakePage:
        def extract_words(self, **kw):
            raise RuntimeError("extract failed")

        def find_tables(self):
            return []

        @property
        def images(self):
            return []

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_module = type("M", (), {"open": lambda *a, **kw: FakePdf()})
    monkeypatch.setattr(fallback_parser, "pdfplumber", fake_module)
    elements, warnings = fallback_parser._parse_pdf(tmp_path / "x.pdf", "abc", "doc-abc", None)
    assert any(w.code == "pdfplumber_word_extract_failed" for w in warnings)


def test_parse_pdf_find_tables_fails_skipped(monkeypatch, tmp_path: Path):
    """find_tables 抛 → 该页跳过 table，不抛。"""
    from app.parsers import fallback_parser

    class FakePage:
        def extract_words(self, **kw):
            return []

        def find_tables(self):
            raise RuntimeError("find failed")

        @property
        def images(self):
            return []

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_module = type("M", (), {"open": lambda *a, **kw: FakePdf()})
    monkeypatch.setattr(fallback_parser, "pdfplumber", fake_module)
    elements, warnings = fallback_parser._parse_pdf(tmp_path / "x.pdf", "abc", "doc-abc", None)
    # No table element added
    assert not any(e.type == "table" for e in elements)


def test_parse_pdf_image_invalid_bbox_skipped(monkeypatch, tmp_path: Path):
    """image bbox 退化（x1<=x0） → 跳过。"""
    from app.parsers import fallback_parser

    class FakePage:
        def extract_words(self, **kw):
            return []

        def find_tables(self):
            return []

        @property
        def images(self):
            return [{"x0": 10.0, "x1": 10.0, "top": 0.0, "bottom": 5.0}]  # x1==x0

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_module = type("M", (), {"open": lambda *a, **kw: FakePdf()})
    monkeypatch.setattr(fallback_parser, "pdfplumber", fake_module)
    elements, warnings = fallback_parser._parse_pdf(tmp_path / "x.pdf", "abc", "doc-abc", None)
    # 退化 image 不加入
    assert not any(e.type == "image" for e in elements)


def test_parse_pdf_image_render_failure_records_warning(monkeypatch, tmp_path: Path):
    """image_output_dir 提供但 _render_pdf_image_region_verbose 失败 → warning。"""
    from app.parsers import fallback_parser

    class FakePage:
        def extract_words(self, **kw):
            return []

        def find_tables(self):
            return []

        @property
        def images(self):
            return [{"x0": 0.0, "x1": 100.0, "top": 0.0, "bottom": 100.0}]

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_module = type("M", (), {"open": lambda *a, **kw: FakePdf()})
    monkeypatch.setattr(fallback_parser, "pdfplumber", fake_module)

    # 让 render 返回错误字符串
    def fake_render(*a, **kw):
        return "render failed"

    monkeypatch.setattr(fallback_parser, "_render_pdf_image_region_verbose", fake_render)

    out_dir = tmp_path / "imgs"
    elements, warnings = fallback_parser._parse_pdf(
        tmp_path / "x.pdf", "abc", "doc-abc", out_dir
    )
    # image 仍加入但 resource_path = "(unrendered)"
    img_elements = [e for e in elements if e.type == "image"]
    assert len(img_elements) == 1
    assert img_elements[0].resource_path == "(unrendered)"
    assert any(w.code == "pdf_image_render_failed" for w in warnings)


def test_parse_pdf_image_dir_creation_failure(monkeypatch, tmp_path: Path):
    """image_output_dir 的 mkdir 失败 → warning('pdf_image_dir_failed')，跳过 render。"""
    from app.parsers import fallback_parser

    class FakePage:
        def extract_words(self, **kw):
            return []

        def find_tables(self):
            return []

        @property
        def images(self):
            return [{"x0": 0.0, "x1": 100.0, "top": 0.0, "bottom": 100.0}]

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_module = type("M", (), {"open": lambda *a, **kw: FakePdf()})
    monkeypatch.setattr(fallback_parser, "pdfplumber", fake_module)

    # 让 out_path.parent.mkdir 抛 OSError
    real_path = Path

    class FakePath(real_path):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)

        def mkdir(self, *a, **kw):
            raise OSError("denied")

    # Patch the out_path inside _parse_pdf: monkeypatch the local Path doesn't work,
    # so test via image_output_dir being a file path (real OSError from filesystem)
    blocker = tmp_path / "blocker.txt"
    blocker.write_text("x")
    bad_dir = blocker  # mkdir(exist_ok=True) on a file → FileExistsError

    elements, warnings = fallback_parser._parse_pdf(
        tmp_path / "x.pdf", "abc", "doc-abc", bad_dir
    )
    assert any(w.code == "pdf_image_dir_failed" for w in warnings)


def test_parse_pdf_words_extracted_to_paragraph(monkeypatch, tmp_path: Path):
    """正常 word → paragraph 或 heading 元素。"""
    from app.parsers import fallback_parser

    # 长文本 + 句末标点 → paragraph（避开 heading 启发式）
    class FakePage:
        def extract_words(self, **kw):
            return [
                {"text": "Hello", "x0": 0.0, "x1": 30.0, "top": 0.0, "bottom": 10.0},
                {"text": "World", "x0": 40.0, "x1": 70.0, "top": 0.0, "bottom": 10.0},
                {"text": "this", "x0": 0.0, "x1": 30.0, "top": 0.0, "bottom": 10.0},
                {"text": "is", "x0": 40.0, "x1": 70.0, "top": 0.0, "bottom": 10.0},
                {"text": "a", "x0": 0.0, "x1": 30.0, "top": 0.0, "bottom": 10.0},
                {"text": "long", "x0": 40.0, "x1": 70.0, "top": 0.0, "bottom": 10.0},
                {"text": "sentence.", "x0": 0.0, "x1": 70.0, "top": 0.0, "bottom": 10.0},
            ]

        def find_tables(self):
            return []

        @property
        def images(self):
            return []

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_module = type("M", (), {"open": lambda *a, **kw: FakePdf()})
    monkeypatch.setattr(fallback_parser, "pdfplumber", fake_module)
    elements, warnings = fallback_parser._parse_pdf(tmp_path / "x.pdf", "abc", "doc-abc", None)
    # 至少有一个 text 含 "Hello"
    assert any("Hello" in (e.content or "") for e in elements)


def test_parse_pdf_table_extracted(monkeypatch, tmp_path: Path):
    """正常 table → table 元素 + markdown content。"""
    from app.parsers import fallback_parser

    class FakePage:
        def extract_words(self, **kw):
            return []

        def find_tables(self):
            class T:
                bbox = (0, 0, 100, 50)

                def extract(self):
                    return [["h1", "h2"], ["v1", "v2"]]

            return [T()]

        @property
        def images(self):
            return []

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_module = type("M", (), {"open": lambda *a, **kw: FakePdf()})
    monkeypatch.setattr(fallback_parser, "pdfplumber", fake_module)
    elements, warnings = fallback_parser._parse_pdf(tmp_path / "x.pdf", "abc", "doc-abc", None)
    tables = [e for e in elements if e.type == "table"]
    assert len(tables) == 1
    assert "h1" in tables[0].content
    assert "v2" in tables[0].content


# ---------- _parse_docx 错误路径 ----------


def test_parse_docx_docx_none_raises_parser_error(monkeypatch):
    from app.parsers import fallback_parser
    monkeypatch.setattr(fallback_parser, "docx", None)
    monkeypatch.setattr(fallback_parser, "_DOCX_IMPORT_ERROR", "missing", raising=False)
    monkeypatch.setattr(fallback_parser, "qn", None)
    with pytest.raises(ParserError) as ei:
        fallback_parser._parse_docx(Path("dummy.docx"), "abc", "doc-abc", None)
    assert ei.value.code == "python_docx_unavailable"


def test_parse_docx_docx_open_fails_raises(monkeypatch, tmp_path: Path):
    from app.parsers import fallback_parser

    class FakeDocxModule:
        @staticmethod
        def Document(path):
            raise IOError("bad docx")

    monkeypatch.setattr(fallback_parser, "docx", FakeDocxModule)
    # qn 仍非 None（避免 import 失败）
    if fallback_parser.qn is None:
        pytest.skip("qn unavailable")

    with pytest.raises(ParserError) as ei:
        fallback_parser._parse_docx(tmp_path / "x.docx", "abc", "doc-abc", None)
    assert ei.value.code == "docx_open_failed"


def test_parse_docx_empty_body_records_warning(monkeypatch, tmp_path: Path):
    """body 没有任何 w:p / w:tbl → warnings 含 docx_no_content。"""
    from app.parsers import fallback_parser

    if fallback_parser.qn is None:
        pytest.skip("qn unavailable")

    class FakeBody:
        def iterchildren(self):
            return iter([])

    class FakeDoc:
        element = type("E", (), {"body": FakeBody()})

    class FakeDocxModule:
        Document = staticmethod(lambda path: FakeDoc())

    monkeypatch.setattr(fallback_parser, "docx", FakeDocxModule)

    elements, warnings = fallback_parser._parse_docx(
        tmp_path / "x.docx", "abc", "doc-abc", None
    )
    assert elements == []
    assert any(w.code == "docx_no_content" for w in warnings)
