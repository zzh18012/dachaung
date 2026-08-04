"""解析器的单元测试。

策略：
- DOCX 用 stdlib 的 zipfile 合成最小测试文件（不需要真实样例）
- PDF 用 stdlib 字节流合成最小 PDF（不需要真实样例）
- Kreuzberg 用合成的 DOCX 验证它能调用（不强求 elements 完整性，因为已实测它给不出）
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models import Document
from app.parsers import Parser, ParserError
from app.parsers.fallback_parser import FallbackParser
from app.parsers.kreuzberg_parser import KreuzbergParser

from tests._synthetic_docs import (
    build_docx_with_caption,
    build_empty_docx,
    build_minimal_docx,
    build_minimal_pdf,
)


# ---------- FallbackParser tests ----------

def test_fallback_docx_basic(tmp_path: Path):
    p = build_minimal_docx(tmp_path / "synthetic.docx")
    doc = FallbackParser().parse(p, source_hash="a" * 64)
    assert isinstance(doc, Document)
    assert doc.source_type == "docx"
    assert doc.parser_name == "fallback"
    # 合成的 DOCX 含 1 heading + 1 paragraph
    types = [e.type for e in doc.elements]
    assert "heading" in types
    assert types.count("paragraph") >= 1
    # DOCX source_locator 必须有 paragraph_index 或 table_index
    for e in doc.elements:
        assert "page" not in e.source_locator  # DOCX 不应有 page
        if e.type == "table":
            assert "table_index" in e.source_locator
        else:
            assert "paragraph_index" in e.source_locator


def test_fallback_docx_with_table(tmp_path: Path):
    p = build_minimal_docx(tmp_path / "synthetic.docx", with_table=True)
    doc = FallbackParser().parse(p, source_hash="b" * 64)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    t = tables[0]
    assert "A1" in t.content and "B2" in t.content
    assert t.source_locator.get("table_index") == 0


def test_fallback_pdf_basic(tmp_path: Path):
    p = build_minimal_pdf(tmp_path / "synthetic.pdf", text="(Hello World Chapter 1)")
    # 用括号包文本避免 PDF 解析问题
    doc = FallbackParser().parse(p, source_hash="c" * 64)
    assert doc.source_type == "pdf"
    # PDF 必须有 page（≥1）
    for e in doc.elements:
        assert e.source_locator.get("page", 0) >= 1
        # bbox 必须是 4 个数字（如果有）
        if "bbox" in e.source_locator:
            assert len(e.source_locator["bbox"]) == 4


def test_fallback_missing_file_raises(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(tmp_path / "nope.docx", source_hash="d" * 64)
    assert exc.value.code == "file_not_found"


def test_fallback_unsupported_extension(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello")
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(p, source_hash="e" * 64)
    assert exc.value.code == "unsupported_type"


# ---------- KreuzbergParser tests ----------

def test_kreuzberg_docx_returns_document_with_warning(tmp_path: Path):
    """Kreuzberg 实测对 DOCX 给不出 elements，必须产生 kreuzberg_no_structured_elements warning。"""
    p = build_minimal_docx(tmp_path / "synthetic.docx")
    doc = KreuzbergParser().parse(p, source_hash="f" * 64)
    assert doc.source_type == "docx"
    assert doc.parser_name == "kreuzberg"
    warning_codes = [w.code for w in doc.warnings]
    assert "kreuzberg_no_structured_elements" in warning_codes


def test_kreuzberg_pdf_has_no_bbox_warning(tmp_path: Path):
    p = build_minimal_pdf(tmp_path / "synthetic.pdf", text="(Hi)")
    doc = KreuzbergParser().parse(p, source_hash="10" * 32)
    warning_codes = [w.code for w in doc.warnings]
    assert "kreuzberg_pdf_no_bbox" in warning_codes
    # 占位 page=1
    for e in doc.elements:
        if doc.source_type == "pdf":
            assert e.source_locator.get("page") == 1


def test_kreuzberg_missing_file_raises(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        KreuzbergParser().parse(tmp_path / "nope.pdf", source_hash="1" * 64)
    assert exc.value.code == "file_not_found"


# ---------- KreuzbergParser 内部 helpers（纯函数）----------

from app.parsers.kreuzberg_parser import (
    _classify_line,
    _make_locator,
    _split_content_to_elements,
)


def test_classify_line_markdown_heading_levels():
    """markdown 风格 # / ## / ### 都被识别为 heading，level 对应 # 数量。"""
    etype, meta = _classify_line("# Title")
    assert etype == "heading"
    assert meta["level"] == 1
    assert meta["raw_text"] == "Title"

    etype, meta = _classify_line("## Subsection")
    assert etype == "heading"
    assert meta["level"] == 2

    etype, meta = _classify_line("###### Deep heading")
    assert etype == "heading"
    assert meta["level"] == 6


def test_classify_line_short_line_is_heading_heuristic():
    """短行（≤80）+ 不以句号结尾 → heading (short_line heuristic)。"""
    etype, meta = _classify_line("Chapter Two")
    assert etype == "heading"
    assert meta.get("heuristic") == "short_line"
    assert meta["level"] == 0


def test_classify_line_paragraph_when_ends_with_period():
    """短行但以句号结尾 → paragraph。"""
    etype, _ = _classify_line("Short sentence.")
    assert etype == "paragraph"


def test_classify_line_paragraph_when_long():
    """超过 80 字符的行即使不以句号结尾也是 paragraph。"""
    long_line = "a" * 100
    etype, _ = _classify_line(long_line)
    assert etype == "paragraph"


def test_classify_line_empty_returns_paragraph():
    """空行被归为 paragraph（实际 _split_content_to_elements 会跳过空 block）。"""
    etype, _ = _classify_line("")
    assert etype == "paragraph"
    etype, _ = _classify_line("   ")
    assert etype == "paragraph"


def test_classify_line_chinese_full_stop_treated_as_heading_stop():
    """以中文句号结尾 → 不视为 heading（与英文句号同等待遇）。"""
    etype, _ = _classify_line("短句。")
    assert etype == "paragraph"


def test_make_locator_pdf_vs_docx():
    """PDF locator 有 page=1 占位 + _kreuzberg_placeholder；DOCX 用 paragraph_index。"""
    pdf_loc = _make_locator("pdf", 0)
    assert pdf_loc["page"] == 1
    assert pdf_loc["_kreuzberg_placeholder"] is True

    docx_loc = _make_locator("docx", 5)
    assert docx_loc["paragraph_index"] == 5
    assert docx_loc["_kreuzberg_heuristic"] is True
    assert "page" not in docx_loc


def test_split_content_to_elements_basic_paragraphs():
    """双换行分隔的多段落 → 多个 paragraph element。"""
    content = "First paragraph here.\n\nSecond paragraph here."
    elements, _ = _split_content_to_elements(content, "docx", "doc-test00000001")
    assert len(elements) == 2
    assert all(e.type == "paragraph" for e in elements)
    assert elements[0].content == "First paragraph here."
    assert elements[1].content == "Second paragraph here."


def test_split_content_to_elements_heading_markdown():
    """markdown 风格 heading 行 → heading element。"""
    content = "# Document Title\n\nBody paragraph."
    elements, _ = _split_content_to_elements(content, "docx", "doc-test00000001")
    assert len(elements) == 2
    assert elements[0].type == "heading"
    assert elements[0].content == "Document Title"
    assert elements[0].metadata["level"] == 1
    assert elements[1].type == "paragraph"


def test_split_content_to_elements_heading_with_body():
    """单 block 内首行 heading + 后续正文 → heading + paragraph。"""
    content = "# Title\nFirst body line.\nSecond body line."
    elements, _ = _split_content_to_elements(content, "docx", "doc-test00000001")
    assert len(elements) == 2
    assert elements[0].type == "heading"
    assert elements[0].content == "Title"
    assert elements[1].type == "paragraph"
    assert "First body line." in elements[1].content
    assert "Second body line." in elements[1].content


def test_split_content_to_elements_empty_content():
    """空 content → 空 elements 列表。"""
    elements, _ = _split_content_to_elements("", "docx", "doc-test00000001")
    assert elements == []
    # 纯空白也应是空
    elements, _ = _split_content_to_elements("  \n\n  \n  ", "docx", "doc-test00000001")
    assert elements == []


def test_split_content_to_elements_pdf_uses_page_placeholder():
    """source_type=pdf → locator.page=1 占位。"""
    content = "Some content."
    elements, _ = _split_content_to_elements(content, "pdf", "doc-test00000001")
    assert len(elements) == 1
    assert elements[0].source_locator["page"] == 1
    assert elements[0].source_locator["_kreuzberg_placeholder"] is True


# ---------- KreuzbergParser 集成：warning 细节 ----------

def test_kreuzberg_docx_warning_has_fallback_strategy_detail(tmp_path: Path):
    """kreuzberg_no_structured_elements warning 的 details 应记录 fallback 策略。"""
    p = build_minimal_docx(tmp_path / "synthetic.docx")
    doc = KreuzbergParser().parse(p, source_hash="a" * 64)
    warning = next(
        w for w in doc.warnings if w.code == "kreuzberg_no_structured_elements"
    )
    assert warning.details is not None
    assert warning.details.get("fallback_strategy") == "heuristic_paragraph_split"
    assert warning.details.get("source_type") == "docx"
    # element_count_after_heuristic 必须 ≥ 0（实际 kreuzberg 对合成 docx 可能给 0 也可能给若干）
    assert warning.details.get("element_count_after_heuristic, 0") or \
        isinstance(warning.details.get("element_count_after_heuristic"), int)


def test_kreuzberg_pdf_elements_have_page_placeholder(tmp_path: Path):
    """PDF kreuzberg 解析的 elements 必须有 page=1 占位。"""
    p = build_minimal_pdf(tmp_path / "synthetic.pdf", text="(Hi)")
    doc = KreuzbergParser().parse(p, source_hash="b" * 64)
    # 即便 elements 为空，warning 也得有
    for e in doc.elements:
        if e.type in ("heading", "paragraph", "caption"):
            assert e.source_locator.get("page") == 1


def test_kreuzberg_returns_metadata(tmp_path: Path):
    """kreuzberg 的结果 metadata 字段应保留到 Document.metadata。"""
    p = build_minimal_docx(tmp_path / "synthetic.docx")
    doc = KreuzbergParser().parse(p, source_hash="c" * 64)
    # metadata 字段（kreuzberg_mime_type / kreuzberg_quality_score 可能 None，但 key 必在）
    assert "kreuzberg_mime_type" in doc.metadata
    assert "kreuzberg_quality_score" in doc.metadata


# ---------- 接口契约 ----------

def test_parser_interface_contract():
    """Parser 抽象类不能直接实例化。"""
    with pytest.raises(TypeError):
        Parser()  # type: ignore[abstract]


def test_parsers_have_name_and_version():
    for parser_cls in (FallbackParser, KreuzbergParser):
        instance = parser_cls()
        assert isinstance(instance.name, str) and instance.name
        assert isinstance(instance.version, str) and instance.version


# ---------- fallback_parser 内部 helpers（纯函数）----------

from app.parsers.fallback_parser import (
    _classify_pdf_paragraph,
    _group_words_to_paragraphs,
    _image_filename,
    _is_caption,
    _is_heading_style,
    _render_pdf_image_region_verbose,
    _rows_to_markdown,
)


def test_is_heading_style_title_and_levels():
    assert _is_heading_style("Title") == (True, 1)
    assert _is_heading_style("Heading 1") == (True, 1)
    assert _is_heading_style("Heading 3") == (True, 3)
    assert _is_heading_style("heading 2") == (True, 2)  # 大小写不敏感
    # "heading" 无数字 → 退回 level=1
    assert _is_heading_style("Heading") == (True, 1)


def test_is_heading_style_negative():
    assert _is_heading_style(None) == (False, 0)
    assert _is_heading_style("") == (False, 0)
    assert _is_heading_style("Normal") == (False, 0)
    assert _is_heading_style("Body Text") == (False, 0)
    assert _is_heading_style("List Bullet") == (False, 0)


def test_is_caption_variants():
    # 英文
    assert _is_caption("Table 1. Distribution of samples")
    assert _is_caption("Figure 5: Architecture diagram")
    assert _is_caption("Fig. 2. Overview")
    assert _is_caption("FIGURE 10 Detail")
    # 中文
    assert _is_caption("表 1 样本统计")
    assert _is_caption("图 3、示意图")
    assert _is_caption("表 9. 实验结果")


def test_is_caption_negative():
    assert not _is_caption("Hello world")
    assert not _is_caption("This is a normal paragraph.")
    assert not _is_caption("")
    assert not _is_caption(None)
    # 数字缺失不算 caption
    assert not _is_caption("Table without number")


def test_classify_pdf_paragraph_categories():
    # caption 优先
    etype, meta = _classify_pdf_paragraph("Table 1. Samples")
    assert etype == "caption"
    assert meta.get("heuristic") == "caption_regex"
    # 短行 + 不以句号结尾 → heading
    etype, _ = _classify_pdf_paragraph("Chapter Two")
    assert etype == "heading"
    # 长句 → paragraph
    etype, _ = _classify_pdf_paragraph(
        "This is a longer sentence that clearly exceeds the short-line threshold and ends with period."
    )
    assert etype == "paragraph"
    # 空字符串 → paragraph（默认）
    etype, _ = _classify_pdf_paragraph("   ")
    assert etype == "paragraph"


def test_rows_to_markdown_empty_and_single():
    assert _rows_to_markdown([]) == ""
    md = _rows_to_markdown([["a"]])
    assert "| a |" in md
    assert "| --- |" in md


def test_rows_to_markdown_pads_uneven_rows():
    """长短不齐的行应被填充到等宽。"""
    md = _rows_to_markdown([["a", "b"], ["c"]])
    lines = md.splitlines()
    # 表头 + 分隔 + 1 数据行 = 3 行
    assert len(lines) == 3
    # 第二行（数据）必须包含 c 和空（填充）
    assert "c" in lines[2]
    assert lines[2].count("|") == lines[0].count("|")


def test_rows_to_markdown_none_cell_normalized():
    md = _rows_to_markdown([[None, "x"], ["y", "z"]])
    assert "|  | x |" in md  # None → 空字符串
    assert "| y | z |" in md


def test_image_filename_pattern():
    # 文档 id 前缀 doc- 被去掉
    name = _image_filename("doc-abcdef0123", "p1", 0, "png")
    assert name == "image_abcdef0123_p1_00.png"
    # 索引 2 位
    name2 = _image_filename("doc-x", "para3", 7, "jpg")
    assert "_para3_07.jpg" in name2


def test_group_words_empty():
    assert _group_words_to_paragraphs([]) == []


def test_group_words_single_word():
    out = _group_words_to_paragraphs([
        {"text": "Hi", "x0": 0.0, "x1": 10.0, "top": 0.0, "bottom": 12.0}
    ])
    assert len(out) == 1
    assert out[0]["text"] == "Hi"
    assert out[0]["bbox"] == [0.0, 0.0, 10.0, 12.0]


def test_group_words_two_lines_cluster():
    """同一行（y 接近）的 words 应聚成一段；不同行间距大则分多段。"""
    # 第一行两个词（y 相近），第二行一个词
    words = [
        {"text": "Hello", "x0": 0.0, "x1": 30.0, "top": 0.0, "bottom": 12.0},
        {"text": "World", "x0": 35.0, "x1": 60.0, "top": 0.5, "bottom": 12.0},
        {"text": "Second", "x0": 0.0, "x1": 40.0, "top": 50.0, "bottom": 62.0},
    ]
    out = _group_words_to_paragraphs(words)
    # 行间距（top=50 - bottom=12 = 38）>> 1.5 * median_h（12）=18，应分两段
    assert len(out) == 2
    assert "Hello" in out[0]["text"] and "World" in out[0]["text"]
    assert out[1]["text"] == "Second"


# ---------- 错误路径：坏字节流 ----------

def test_fallback_docx_broken_bytes_raises(tmp_path: Path):
    """非 DOCX 字节流 → docx_open_failed。"""
    bad = tmp_path / "broken.docx"
    bad.write_bytes(b"not a docx file content")
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(bad, source_hash="x" * 64)
    assert exc.value.code == "docx_open_failed"


def test_fallback_pdf_broken_bytes_raises(tmp_path: Path):
    """非 PDF 字节流 → pdfplumber_open_failed。"""
    bad = tmp_path / "broken.pdf"
    bad.write_bytes(b"not a pdf file content")
    with pytest.raises(ParserError) as exc:
        FallbackParser().parse(bad, source_hash="y" * 64)
    assert exc.value.code == "pdfplumber_open_failed"


# ---------- DOCX caption 集成 ----------

def test_fallback_docx_caption_detection(tmp_path: Path):
    p = build_docx_with_caption(tmp_path / "caption.docx")
    doc = FallbackParser().parse(p, source_hash="c" * 64)
    captions = [e for e in doc.elements if e.type == "caption"]
    # 两段 caption（Figure 1. 和 表 2）+ 一段 paragraph
    assert len(captions) == 2
    paragraphs = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paragraphs) == 1


# ---------- DOCX 空文档警告 ----------

def test_fallback_docx_empty_body_emits_warning(tmp_path: Path):
    p = build_empty_docx(tmp_path / "empty.docx")
    doc = FallbackParser().parse(p, source_hash="e" * 64)
    assert len(doc.elements) == 0
    warning_codes = [w.code for w in doc.warnings]
    assert "docx_no_content" in warning_codes


# ---------- PDF 图片渲染错误路径 ----------

def test_render_pdf_image_region_verbose_bad_path(tmp_path: Path):
    """PDF 文件不存在 → 返回错误字符串（None 表示成功）。"""
    out = tmp_path / "out.png"
    err = _render_pdf_image_region_verbose(
        tmp_path / "nonexistent.pdf", 0, [0.0, 0.0, 100.0, 100.0], out
    )
    assert err is not None
    assert "PdfDocument" in err or "打开" in err or "failed" in err.lower()
    assert not out.exists()


def test_render_pdf_image_region_verbose_bad_page_index(tmp_path: Path):
    """页号越界 → 返回错误字符串。"""
    p = build_minimal_pdf(tmp_path / "synthetic.pdf", text="(Hello)")
    out = tmp_path / "out.png"
    err = _render_pdf_image_region_verbose(p, 999, [0.0, 0.0, 100.0, 100.0], out)
    assert err is not None
    assert "page" in err.lower()


def test_render_pdf_image_region_verbose_degenerate_bbox(tmp_path: Path):
    """退化 bbox（0 size crop）→ 错误字符串，不写文件。"""
    p = build_minimal_pdf(tmp_path / "synthetic.pdf", text="(Hello)")
    out = tmp_path / "out.png"
    # bbox 全 0 → crop 退化
    err = _render_pdf_image_region_verbose(p, 0, [0.0, 0.0, 0.0, 0.0], out)
    assert err is not None
    assert "crop" in err.lower() or "退化" in err or "size" in err.lower()


# ---------- 边角与缺漏补强（Round 30） ----------


# _is_heading_style 更多边角


def test_is_heading_style_with_whitespace():
    """含首尾空格的 style 名应被 strip。"""
    assert _is_heading_style("  Heading 1  ") == (True, 1)


def test_is_heading_style_heading_zero_floors_to_one():
    """Heading 0 → max(1, 0) = 1（heading 级别不能小于 1）。"""
    assert _is_heading_style("Heading 0") == (True, 1)


def test_is_heading_style_heading_negative_floors_to_one():
    """Heading -1 → int 解析成功 → max(1,-1)=1。"""
    # 注意：'heading-1' replace 'heading' → '-1'，int('-1')=-1，max(1,-1)=1
    assert _is_heading_style("heading-1") == (True, 1)


def test_is_heading_style_title_case_insensitive():
    """TITLE / Title / title 都识别。"""
    assert _is_heading_style("TITLE") == (True, 1)
    assert _is_heading_style("Title") == (True, 1)
    assert _is_heading_style("title") == (True, 1)


def test_is_heading_style_heading_with_non_numeric_suffix_falls_back_to_one():
    """Heading ABC → int('ABC') 抛 ValueError → fallback level=1。"""
    is_h, level = _is_heading_style("HeadingABC")
    assert is_h is True
    assert level == 1


def test_is_heading_style_normal_not_heading():
    assert _is_heading_style("Normal") == (False, 0)


def test_is_heading_style_empty_string():
    assert _is_heading_style("") == (False, 0)


# _is_caption 更多边角（含 Unicode 全角数字与混合形式）


def test_is_caption_full_width_digits():
    """全角数字 ０１２３ 也应被识别。"""
    assert _is_caption("Figure ５: Architecture")
    assert _is_caption("表 ３. 实验结果")


def test_is_caption_chinese_with_dot():
    """中文 '表 3.' 也应识别（'.' 在字符类里）。"""
    assert _is_caption("表 3. 实验设计")


def test_is_caption_dot_after_abbreviation():
    """Fig.（带缩写点）也应识别。"""
    assert _is_caption("Fig. 5: diagram")
    assert _is_caption("Fig 5: diagram")


def test_is_caption_no_separator_rejected():
    """缺分隔符（直接接内容）→ 不识别。"""
    assert not _is_caption("FigureHello")
    assert not _is_caption("TableData")


def test_is_caption_only_number_rejected():
    """只有数字（无前缀）→ 不识别。"""
    assert not _is_caption("5")
    assert not _is_caption("3.14")


def test_is_caption_full_word_required():
    """'Table' 不能是 'Tabl' 的前缀。"""
    assert not _is_caption("Tabl 3: x")


# _classify_pdf_paragraph 更多边角


def test_classify_pdf_paragraph_caption_priority_over_heading():
    """caption 优先级高于 heading：caption regex 命中应返 caption。"""
    t, meta = _classify_pdf_paragraph("Figure 5: chart")
    assert t == "caption"
    assert meta["heuristic"] == "caption_regex"


def test_classify_pdf_paragraph_short_line_with_period_is_paragraph():
    """短行但以句号结尾 → paragraph。"""
    t, _ = _classify_pdf_paragraph("End.")
    assert t == "paragraph"


def test_classify_pdf_paragraph_short_line_no_period_is_heading():
    """短行无句末标点 → heading。"""
    t, meta = _classify_pdf_paragraph("Section Title")
    assert t == "heading"
    assert meta["heuristic"] == "short_line"


def test_classify_pdf_paragraph_long_text_is_paragraph():
    t, _ = _classify_pdf_paragraph(
        "This is a very long paragraph that exceeds eighty characters "
        "and should definitely be classified as a paragraph by the heuristic."
    )
    assert t == "paragraph"


def test_classify_pdf_paragraph_chinese_short_no_period():
    """中文短行（无中文句号）→ heading。"""
    t, _ = _classify_pdf_paragraph("章节标题")
    assert t == "heading"


def test_classify_pdf_paragraph_chinese_short_with_period():
    """中文短行带句号 → paragraph。"""
    t, _ = _classify_pdf_paragraph("这是一个完整句子。")
    assert t == "paragraph"


# _lines_to_para 直接单测


def test_lines_to_para_empty_returns_empty_dict():
    from app.parsers.fallback_parser import _lines_to_para
    result = _lines_to_para([])
    assert result == {"text": "", "bbox": None}


def test_lines_to_para_single_line_multiple_words():
    """单行多 word → text 用空格连接，bbox 横向延伸。"""
    from app.parsers.fallback_parser import _lines_to_para
    line = [
        {"text": "Hello", "x0": 0.0, "x1": 50.0, "top": 10.0, "bottom": 30.0},
        {"text": "world", "x0": 60.0, "x1": 110.0, "top": 10.0, "bottom": 30.0},
    ]
    result = _lines_to_para([line])
    assert result["text"] == "Hello world"
    # bbox = [min x0, min top, max x1, max bottom]
    assert result["bbox"] == [0.0, 10.0, 110.0, 30.0]


def test_lines_to_para_two_lines_y_separation():
    """两行 → text 用空格分隔，bbox 纵向延伸。"""
    from app.parsers.fallback_parser import _lines_to_para
    lines = [
        [{"text": "first", "x0": 0.0, "x1": 30.0, "top": 10.0, "bottom": 25.0}],
        [{"text": "second", "x0": 0.0, "x1": 40.0, "top": 50.0, "bottom": 65.0}],
    ]
    result = _lines_to_para(lines)
    assert "first" in result["text"]
    assert "second" in result["text"]
    # bbox 跨两行
    assert result["bbox"] == [0.0, 10.0, 40.0, 65.0]


def test_lines_to_para_unsorted_words_in_line_sorted_by_x0():
    """同一行内 word 顺序乱 → 应按 x0 排序后再 join。"""
    from app.parsers.fallback_parser import _lines_to_para
    line = [
        {"text": "world", "x0": 60.0, "x1": 110.0, "top": 10.0, "bottom": 30.0},
        {"text": "Hello", "x0": 0.0, "x1": 50.0, "top": 10.0, "bottom": 30.0},
        {"text": "!", "x0": 120.0, "x1": 125.0, "top": 10.0, "bottom": 30.0},
    ]
    result = _lines_to_para([line])
    assert result["text"] == "Hello world !"


# _group_words_to_paragraphs 更多聚类场景


def test_group_words_three_lines_one_paragraph():
    """3 行紧贴（行距正常）→ 1 个段落。"""
    from app.parsers.fallback_parser import _group_words_to_paragraphs
    words = [
        {"text": "a", "x0": 0.0, "x1": 10.0, "top": 10.0, "bottom": 22.0},
        {"text": "b", "x0": 0.0, "x1": 10.0, "top": 30.0, "bottom": 42.0},
        {"text": "c", "x0": 0.0, "x1": 10.0, "top": 50.0, "bottom": 62.0},
    ]
    paragraphs = _group_words_to_paragraphs(words)
    # 行间距 8px << median height * 1.5 → 应聚合为 1 段
    assert len(paragraphs) == 1


def test_group_words_two_paragraphs_split_by_large_gap():
    """大行距 → 2 个段落。"""
    from app.parsers.fallback_parser import _group_words_to_paragraphs
    # 第一组：top=10, bottom=22；第二组：top=200, bottom=212
    # gap = 200 - 22 = 178 >> 22*1.5=33 → 拆段
    words = [
        {"text": "first", "x0": 0.0, "x1": 30.0, "top": 10.0, "bottom": 22.0},
        {"text": "second", "x0": 0.0, "x1": 30.0, "top": 200.0, "bottom": 212.0},
    ]
    paragraphs = _group_words_to_paragraphs(words)
    assert len(paragraphs) == 2
    assert "first" in paragraphs[0]["text"]
    assert "second" in paragraphs[1]["text"]


def test_group_words_words_with_default_top_bottom():
    """word 缺 top/bottom 字段时，默认 0.0，不应崩溃。"""
    from app.parsers.fallback_parser import _group_words_to_paragraphs
    words = [
        {"text": "x", "x0": 0.0, "x1": 10.0},  # 无 top/bottom
    ]
    paragraphs = _group_words_to_paragraphs(words)
    assert len(paragraphs) == 1
    assert paragraphs[0]["text"] == "x"


# _image_filename 更多边角


def test_image_filename_jpg_extension():
    from app.parsers.fallback_parser import _image_filename
    # 实际格式：image_<safe_doc>_<prefix>_<idx:02d>.<ext>
    # safe_doc 是去掉 'doc-' 前缀的 document_id
    assert _image_filename("doc-x", "img", 0, ext="jpg") == "image_x_img_00.jpg"


def test_image_filename_two_digit_index_padding():
    """index 用 02d 格式（两位补 0）。"""
    from app.parsers.fallback_parser import _image_filename
    assert _image_filename("doc-x", "img", 7, ext="png") == "image_x_img_07.png"
    assert _image_filename("doc-x", "img", 42, ext="png") == "image_x_img_42.png"


def test_image_filename_default_ext_is_png():
    from app.parsers.fallback_parser import _image_filename
    assert _image_filename("doc-x", "img", 0) == "image_x_img_00.png"


def test_image_filename_strips_doc_prefix():
    """document_id 含 'doc-' 前缀应被剥离。"""
    from app.parsers.fallback_parser import _image_filename
    assert _image_filename("doc-abcdef", "p1", 0) == "image_abcdef_p1_00.png"


def test_image_filename_without_doc_prefix_preserved():
    """document_id 不以 'doc-' 开头时原样使用。"""
    from app.parsers.fallback_parser import _image_filename
    assert _image_filename("custom-id", "p1", 0) == "image_custom-id_p1_00.png"


# _extract_inline_image_rids 直接单测（需要构造 docx XML element）


def test_extract_inline_image_rids_no_drawings_returns_empty():
    """XML element 内没有 <w:drawing> → 返回空 list。"""
    from app.parsers.fallback_parser import _extract_inline_image_rids
    from lxml import etree

    p_xml = etree.fromstring(
        '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
    )
    rids = _extract_inline_image_rids(p_xml)
    assert rids == []


def test_extract_inline_image_rids_finds_embedded_blip():
    """XML 内有 <w:drawing><a:blip r:embed="rId5"/>... → 返回 ['rId5']。"""
    from app.parsers.fallback_parser import _extract_inline_image_rids
    from lxml import etree

    xml_str = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
      xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
      xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <w:r><w:drawing><a:blip r:embed="rId5"/></w:drawing></w:r>
    </w:p>"""
    p_xml = etree.fromstring(xml_str)
    rids = _extract_inline_image_rids(p_xml)
    assert rids == ["rId5"]


def test_extract_inline_image_rids_multiple_drawings():
    """多个 drawing element → 收集所有 rId。"""
    from app.parsers.fallback_parser import _extract_inline_image_rids
    from lxml import etree

    xml_str = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
      xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
      xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <w:r><w:drawing><a:blip r:embed="rId1"/></w:drawing></w:r>
      <w:r><w:drawing><a:blip r:embed="rId2"/></w:drawing></w:r>
    </w:p>"""
    p_xml = etree.fromstring(xml_str)
    rids = _extract_inline_image_rids(p_xml)
    assert rids == ["rId1", "rId2"]


def test_extract_inline_image_rids_link_only():
    """r:link 而非 r:embed 也应被识别。"""
    from app.parsers.fallback_parser import _extract_inline_image_rids
    from lxml import etree

    xml_str = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
      xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
      xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <w:r><w:drawing><a:blip r:link="rId7"/></w:drawing></w:r>
    </w:p>"""
    p_xml = etree.fromstring(xml_str)
    rids = _extract_inline_image_rids(p_xml)
    assert rids == ["rId7"]
