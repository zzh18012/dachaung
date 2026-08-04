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
