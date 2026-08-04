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
