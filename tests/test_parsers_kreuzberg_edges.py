"""app/parsers/kreuzberg_parser.py 边角测试（Round 60）。

补强 tests/test_parsers_kreuzberg.py（53 个测试）未覆盖的：
- _classify_line heading level 6 边界 / 7 hashes 拒绝 / 返 tuple
- _make_locator pdf/docx 返 dict 含 2 个固定 key
- _split_content_to_elements CRLF 分隔/heading level 6/多行 block rest
- KreuzbergParser.parse monkeypatch 完整覆盖：
  - kreuzberg_unavailable（_KREUZBERG_AVAILABLE=False）
  - file_not_found
  - kreuzberg_extract_failed（extract_file_sync raise）
  - 空 content → 0 elements + warning
  - 有 content → 启发式切分
  - PDF → kreuzberg_pdf_no_bbox warning
  - DOCX → no_structured_elements warning
  - tables 字段处理（cells/bbox/page_number）
  - metadata.mime_type / quality_score 透传
- KreuzbergParser 类属性与实例化
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.parsers.base import ParserError
from app.parsers.kreuzberg_parser import (
    KreuzbergParser,
    _HEADING_RE,
    _SHORT_LINE_MAX,
    _classify_line,
    _make_locator,
    _split_content_to_elements,
)


# ---------- _classify_line 边角 ----------


def test_classify_line_returns_tuple_type():
    result = _classify_line("hello")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_classify_line_heading_level_6_atx():
    etype, meta = _classify_line("###### Heading Six")
    assert etype == "heading"
    assert meta["level"] == 6


def test_classify_line_heading_seven_hashes_not_atx():
    """7 hashes 不匹配 atx regex（{1,6}）→ 走 short_line 分支。"""
    line = "####### Not ATX"
    etype, meta = _classify_line(line)
    # 7 hashes + 文本，长度 14 ≤ 80 且无句号 → short_line heading
    assert etype == "heading"
    assert meta.get("heuristic") == "short_line"


def test_classify_line_heading_with_trailing_whitespace_in_text():
    etype, meta = _classify_line("# Heading   ")
    # regex r"\s*$" 允许尾部空白；raw_text strip 后 "Heading"
    assert etype == "heading"
    assert meta["raw_text"] == "Heading"


def test_classify_line_short_line_with_comma_is_heading():
    """逗号不算句末标点 → 短行视为 heading。"""
    etype, _ = _classify_line("see also,")
    assert etype == "heading"


def test_classify_line_short_line_with_semicolon_is_heading():
    etype, _ = _classify_line("intro;")
    assert etype == "heading"


def test_classify_line_exactly_80_chars_no_period():
    """== 80 chars 且无句末 → heading。"""
    text = "a" * 80
    etype, _ = _classify_line(text)
    assert etype == "heading"


def test_classify_line_81_chars_no_period_is_paragraph():
    text = "a" * 81
    etype, _ = _classify_line(text)
    assert etype == "paragraph"


def test_classify_line_paragraph_meta_is_empty_dict():
    etype, meta = _classify_line("A long sentence with period.")
    assert etype == "paragraph"
    assert meta == {}


def test_classify_line_short_line_meta_has_raw_text():
    etype, meta = _classify_line("short heading")
    assert meta["raw_text"] == "short heading"


# ---------- _make_locator 边角 ----------


def test_make_locator_returns_dict_type():
    assert isinstance(_make_locator("docx", 0), dict)
    assert isinstance(_make_locator("pdf", 0), dict)


def test_make_locator_pdf_has_exactly_two_keys():
    loc = _make_locator("pdf", 0)
    assert set(loc.keys()) == {"page", "_kreuzberg_placeholder"}


def test_make_locator_docx_has_exactly_two_keys():
    loc = _make_locator("docx", 0)
    assert set(loc.keys()) == {"paragraph_index", "_kreuzberg_heuristic"}


def test_make_locator_pdf_page_value_is_1():
    """PDF locator 的 page 始终为 1（kreuzberg 给不出）。"""
    assert _make_locator("pdf", 0)["page"] == 1
    assert _make_locator("pdf", 99)["page"] == 1
    assert _make_locator("pdf", -1)["page"] == 1


def test_make_locator_docx_paragraph_index_passes_through():
    """docx locator 的 paragraph_index 是传入参数。"""
    assert _make_locator("docx", 0)["paragraph_index"] == 0
    assert _make_locator("docx", 5)["paragraph_index"] == 5
    assert _make_locator("docx", 99)["paragraph_index"] == 99


def test_make_locator_pdf_placeholder_value_true():
    assert _make_locator("pdf", 0)["_kreuzberg_placeholder"] is True


def test_make_locator_docx_heuristic_value_true():
    assert _make_locator("docx", 0)["_kreuzberg_heuristic"] is True


# ---------- _split_content_to_elements 边角 ----------


def test_split_content_returns_tuple_type():
    result = _split_content_to_elements("hello", "docx", "doc-abc")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_split_content_first_return_is_list():
    els, _ = _split_content_to_elements("hello", "docx", "doc-abc")
    assert isinstance(els, list)


def test_split_content_empty_string_returns_no_elements():
    els, _ = _split_content_to_elements("", "docx", "doc-abc")
    assert els == []


def test_split_content_whitespace_only_returns_no_elements():
    els, _ = _split_content_to_elements("   \n\n   \n\n   ", "docx", "doc-abc")
    assert els == []


def test_split_content_heading_level_6_atx():
    els, _ = _split_content_to_elements("###### H6", "docx", "doc-abc")
    assert len(els) == 1
    assert els[0].type == "heading"
    assert els[0].metadata["level"] == 6


def test_split_content_atx_heading_with_rest_multiline():
    """ATX heading + 多行后续 → heading + paragraph。"""
    block = "# Title\nline 2\nline 3\nline 4"
    els, _ = _split_content_to_elements(block, "docx", "doc-abc")
    # heading + rest paragraph
    assert len(els) == 2
    assert els[0].type == "heading"
    assert els[0].content == "Title"
    assert els[1].type == "paragraph"
    assert "line 2" in els[1].content
    assert "line 3" in els[1].content
    assert "line 4" in els[1].content


def test_split_content_crlf_line_endings_treated_as_lf():
    """CRLF 被当 LF 处理。"""
    content = "para1\r\n\r\npara2"
    els, _ = _split_content_to_elements(content, "docx", "doc-abc")
    assert len(els) == 2
    assert els[0].content == "para1"
    assert els[1].content == "para2"


def test_split_content_large_input_100_blocks():
    """100 块 paragraph 稳定。"""
    content = "\n\n".join(f"paragraph {i}" for i in range(100))
    els, _ = _split_content_to_elements(content, "docx", "doc-abc")
    assert len(els) == 100


def test_split_content_element_ids_strictly_increasing():
    content = "p1\n\np2\n\n# H\n\np3"
    els, _ = _split_content_to_elements(content, "docx", "doc-abc")
    suffixes = [e.element_id.split("::")[-1] for e in els]
    assert suffixes == sorted(suffixes)
    assert len(set(suffixes)) == len(suffixes)


def test_split_content_pdf_uses_placeholder_locator():
    els, _ = _split_content_to_elements("para text", "pdf", "doc-abc")
    assert els[0].source_locator["page"] == 1
    assert els[0].source_locator["_kreuzberg_placeholder"] is True


def test_split_content_docx_uses_heuristic_locator():
    els, _ = _split_content_to_elements("para text", "docx", "doc-abc")
    assert "paragraph_index" in els[0].source_locator
    assert els[0].source_locator["_kreuzberg_heuristic"] is True


def test_split_content_paragraph_meta_has_kreuzberg_heuristic():
    """真正 paragraph（> 80 chars 或带句号）应有 kreuzberg_heuristic。"""
    els, _ = _split_content_to_elements(
        "This is a long paragraph that exceeds the short line threshold and ends with period.",
        "docx", "doc-abc",
    )
    assert els[0].type == "paragraph"
    assert els[0].metadata.get("kreuzberg_heuristic") is True


def test_split_content_short_line_heading_meta_has_heuristic_short_line():
    els, _ = _split_content_to_elements("short title", "docx", "doc-abc")
    assert els[0].type == "heading"
    assert els[0].metadata.get("heuristic") == "short_line"


def test_split_content_atx_heading_meta_no_kreuzberg_heuristic():
    """ATX heading metadata 不应有 kreuzberg_heuristic key。"""
    els, _ = _split_content_to_elements("# Heading", "docx", "doc-abc")
    assert "kreuzberg_heuristic" not in els[0].metadata


def test_split_content_atx_heading_meta_has_heuristic_none():
    """ATX heading 没有 heuristic → meta['heuristic'] = None。"""
    els, _ = _split_content_to_elements("# Heading", "docx", "doc-abc")
    assert "heuristic" in els[0].metadata
    # 显式 None（meta.get("heuristic") 返 None）
    assert els[0].metadata["heuristic"] is None


def test_split_content_confidence_values():
    """heading=0.6, paragraph=0.5, rest paragraph=0.5。"""
    content = "# H\n\nThis is a long rest paragraph that exceeds the short line threshold."
    els, _ = _split_content_to_elements(content, "docx", "doc-abc")
    assert els[0].confidence == 0.6  # heading
    assert els[1].confidence == 0.5  # paragraph


# ---------- KreuzbergParser 类属性 ----------


def test_kreuzberg_parser_class_name_is_kreuzberg():
    assert KreuzbergParser.name == "kreuzberg"


def test_kreuzberg_parser_class_version_is_str():
    assert isinstance(KreuzbergParser.version, str)


def test_kreuzberg_parser_class_version_not_empty():
    assert len(KreuzbergParser.version) > 0


def test_kreuzberg_parser_init_default():
    p = KreuzbergParser()
    assert p._include_document_structure is True


def test_kreuzberg_parser_init_explicit_true():
    p = KreuzbergParser(include_document_structure=True)
    assert p._include_document_structure is True


def test_kreuzberg_parser_init_explicit_false():
    p = KreuzbergParser(include_document_structure=False)
    assert p._include_document_structure is False


def test_kreuzberg_parser_init_keyword_only():
    """include_document_structure 是 keyword-only 参数。"""
    import inspect
    sig = inspect.signature(KreuzbergParser.__init__)
    params = list(sig.parameters.values())
    # self + include_document_structure，且后者有 * 前缀（keyword-only）
    assert len(params) == 2
    # 检查 keyword-only 标记（PARAM_KIND is KEYWORD_ONLY）
    assert params[1].kind == inspect.Parameter.KEYWORD_ONLY


def test_kreuzberg_parser_inherits_from_parser_class():
    from app.parsers.base import Parser
    assert issubclass(KreuzbergParser, Parser)


def test_kreuzberg_parser_has_parse_method():
    p = KreuzbergParser()
    assert callable(p.parse)


# ---------- KreuzbergParser.parse 错误路径 ----------


def _make_mock_result(**fields):
    """构造一个最小合法的 kreuzberg result 对象。"""
    defaults = {
        "content": "",
        "tables": [],
        "elements": [],
        "mime_type": "text/plain",
        "quality_score": 0.5,
    }
    defaults.update(fields)
    return SimpleNamespace(**defaults)


def test_kreuzberg_parser_parse_kreuzberg_unavailable(monkeypatch):
    """_KREUZBERG_AVAILABLE=False → raise kreuzberg_unavailable。"""
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(mod, "_KREUZBERG_AVAILABLE", False)
    # _KREUZBERG_IMPORT_ERROR 仅在 ImportError 时定义；用 raising=False 容错
    monkeypatch.setattr(mod, "_KREUZBERG_IMPORT_ERROR", "mock error", raising=False)

    parser = KreuzbergParser()
    # 即使文件不存在，也应该先报 unavailable
    with pytest.raises(ParserError) as exc:
        parser.parse("any.docx", source_hash="a" * 64)
    assert exc.value.code == "kreuzberg_unavailable"
    assert "mock error" in exc.value.message


def test_kreuzberg_parser_parse_missing_docx_file(tmp_path: Path):
    parser = KreuzbergParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(tmp_path / "nope.docx", source_hash="a" * 64)
    assert exc.value.code == "file_not_found"
    assert "path" in exc.value.details


def test_kreuzberg_parser_parse_missing_pdf_file(tmp_path: Path):
    parser = KreuzbergParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(tmp_path / "nope.pdf", source_hash="a" * 64)
    assert exc.value.code == "file_not_found"


def test_kreuzberg_parser_parse_missing_docx_error_details_has_path(tmp_path: Path):
    parser = KreuzbergParser()
    missing = tmp_path / "nope.docx"
    with pytest.raises(ParserError) as exc:
        parser.parse(missing, source_hash="a" * 64)
    assert exc.value.details["path"] == str(missing)


def test_kreuzberg_parser_parse_extract_failed(tmp_path: Path, monkeypatch):
    """kreuzberg.extract_file_sync raise → kreuzberg_extract_failed。"""
    import app.parsers.kreuzberg_parser as mod

    def _raise(*args, **kwargs):
        raise RuntimeError("kreuzberg boom")

    # 替换 kreuzberg 模块的 extract_file_sync
    monkeypatch.setattr(mod.kreuzberg, "extract_file_sync", _raise)

    src = tmp_path / "x.docx"
    src.write_bytes(b"fake docx content")
    parser = KreuzbergParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(src, source_hash="a" * 64)
    assert exc.value.code == "kreuzberg_extract_failed"
    assert exc.value.details["exception_type"] == "RuntimeError"


def test_kreuzberg_parser_parse_extract_failed_propagates_exception_type(
    tmp_path: Path, monkeypatch
):
    """exception_type 来自实际异常类。"""
    import app.parsers.kreuzberg_parser as mod

    def _raise(*args, **kwargs):
        raise ValueError("different error")

    monkeypatch.setattr(mod.kreuzberg, "extract_file_sync", _raise)
    src = tmp_path / "x.docx"
    src.write_bytes(b"fake")
    parser = KreuzbergParser()
    with pytest.raises(ParserError) as exc:
        parser.parse(src, source_hash="a" * 64)
    assert exc.value.details["exception_type"] == "ValueError"


# ---------- KreuzbergParser.parse 成功路径 ----------


def test_kreuzberg_parser_parse_empty_content_no_elements(
    tmp_path: Path, monkeypatch
):
    """content="" → 0 elements + 1 个 kreuzberg_no_structured_elements warning。"""
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content=""),
    )

    src = tmp_path / "x.docx"
    src.write_bytes(b"empty docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.elements == []
    # 没有 content 也没有 elements → 警告
    codes = [w.code for w in doc.warnings]
    assert "kreuzberg_no_structured_elements" in codes


def test_kreuzberg_parser_parse_with_content_emits_elements(
    tmp_path: Path, monkeypatch
):
    """有 content → 启发式切分。"""
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(
            content="# H\n\nThis is a long paragraph that ends with a period."
        ),
    )

    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    # heading + paragraph = 2 elements
    assert len(doc.elements) == 2
    types = [e.type for e in doc.elements]
    assert "heading" in types
    assert "paragraph" in types


def test_kreuzberg_parser_parse_pdf_emits_no_bbox_warning(
    tmp_path: Path, monkeypatch
):
    """PDF source → kreuzberg_pdf_no_bbox warning。"""
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="some text"),
    )

    src = tmp_path / "x.pdf"
    src.write_bytes(b"%PDF-1.4 fake")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    assert "kreuzberg_pdf_no_bbox" in codes


def test_kreuzberg_parser_parse_docx_no_no_bbox_warning(
    tmp_path: Path, monkeypatch
):
    """DOCX source → 不应有 kreuzberg_pdf_no_bbox warning。"""
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="text"),
    )

    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    assert "kreuzberg_pdf_no_bbox" not in codes


def test_kreuzberg_parser_parse_with_kreuzberg_elements_no_warning(
    tmp_path: Path, monkeypatch
):
    """kreuzberg.elements 非空 → 不 emit kreuzberg_no_structured_elements。"""
    import app.parsers.kreuzberg_parser as mod
    fake_elements = [{"type": "paragraph"}]
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(
            content="text", elements=fake_elements,
        ),
    )

    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    codes = [w.code for w in doc.warnings]
    assert "kreuzberg_no_structured_elements" not in codes


def test_kreuzberg_parser_parse_metadata_records_mime_type(
    tmp_path: Path, monkeypatch
):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(
            content="x", mime_type="application/vnd.openxmlformats...",
        ),
    )

    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.metadata["kreuzberg_mime_type"] == "application/vnd.openxmlformats..."


def test_kreuzberg_parser_parse_metadata_records_quality_score(
    tmp_path: Path, monkeypatch
):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="x", quality_score=0.95),
    )

    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.metadata["kreuzberg_quality_score"] == 0.95


def test_kreuzberg_parser_parse_metadata_keys_full_set(
    tmp_path: Path, monkeypatch
):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="x"),
    )

    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert set(doc.metadata.keys()) == {
        "kreuzberg_mime_type", "kreuzberg_quality_score"
    }


def test_kreuzberg_parser_parse_tables_emits_table_element(
    tmp_path: Path, monkeypatch
):
    """tables 字段非空 → emit table element。"""
    import app.parsers.kreuzberg_parser as mod
    fake_table = SimpleNamespace(
        markdown="| a | b |\n| --- | --- |",
        cells=[["a", "b"]],
        page_number=0,
        bounding_box=None,
    )
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(
            content="text", tables=[fake_table],
        ),
    )

    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_els = [e for e in doc.elements if e.type == "table"]
    assert len(table_els) == 1
    assert table_els[0].metadata["row_count"] == 1
    assert table_els[0].metadata["cell_count"] == 2
    assert table_els[0].metadata["source"] == "kreuzberg"


def test_kreuzberg_parser_parse_pdf_table_with_bbox(
    tmp_path: Path, monkeypatch
):
    """PDF table 含 bounding_box → locator 含 bbox。"""
    import app.parsers.kreuzberg_parser as mod
    fake_table = SimpleNamespace(
        markdown="md",
        cells=[["x"]],
        page_number=2,
        bounding_box=(1.0, 2.0, 3.0, 4.0),
    )
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(
            content="text", tables=[fake_table],
        ),
    )

    src = tmp_path / "x.pdf"
    src.write_bytes(b"%PDF fake")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.source_locator["page"] == 2
    assert table_el.source_locator["bbox"] == [1.0, 2.0, 3.0, 4.0]


def test_kreuzberg_parser_parse_pdf_table_no_bbox(
    tmp_path: Path, monkeypatch
):
    """PDF table 无 bounding_box → locator 只含 page。"""
    import app.parsers.kreuzberg_parser as mod
    fake_table = SimpleNamespace(
        markdown="md", cells=[["x"]], page_number=0, bounding_box=None,
    )
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(
            content="text", tables=[fake_table],
        ),
    )

    src = tmp_path / "x.pdf"
    src.write_bytes(b"%PDF fake")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    # page_number=0 → fallback to 1
    assert table_el.source_locator["page"] == 1
    assert "bbox" not in table_el.source_locator


def test_kreuzberg_parser_parse_table_confidence_with_cells(
    tmp_path: Path, monkeypatch
):
    """table 有 cells → confidence=0.8。"""
    import app.parsers.kreuzberg_parser as mod
    fake_table = SimpleNamespace(
        markdown="md", cells=[["a", "b"]], page_number=0, bounding_box=None,
    )
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(tables=[fake_table]),
    )

    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.confidence == 0.8


def test_kreuzberg_parser_parse_table_confidence_without_cells(
    tmp_path: Path, monkeypatch
):
    """table cells=None 或空 → confidence=0.5。"""
    import app.parsers.kreuzberg_parser as mod
    fake_table = SimpleNamespace(
        markdown="md", cells=None, page_number=0, bounding_box=None,
    )
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(tables=[fake_table]),
    )

    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    table_el = next(e for e in doc.elements if e.type == "table")
    assert table_el.confidence == 0.5


# ---------- Document 字段完整性 ----------


def test_kreuzberg_parser_parse_chunks_empty_by_default(
    tmp_path: Path, monkeypatch
):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="x"),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.chunks == []


def test_kreuzberg_parser_parse_relations_empty_by_default(
    tmp_path: Path, monkeypatch
):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="x"),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.relations == []


def test_kreuzberg_parser_parse_errors_empty_by_default(
    tmp_path: Path, monkeypatch
):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="x"),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.errors == []


def test_kreuzberg_parser_parse_source_path_preserved(
    tmp_path: Path, monkeypatch
):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="x"),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.source_path == str(src)


def test_kreuzberg_parser_parse_source_hash_passed_through(
    tmp_path: Path, monkeypatch
):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="x"),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="b" * 64)
    assert doc.source_hash == "b" * 64


def test_kreuzberg_parser_parse_parser_name_is_kreuzberg(
    tmp_path: Path, monkeypatch
):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="x"),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert doc.parser_name == "kreuzberg"


def test_kreuzberg_parser_parse_parser_version_is_string(
    tmp_path: Path, monkeypatch
):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="x"),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert isinstance(doc.parser_version, str)


def test_kreuzberg_parser_parse_warning_has_reason_string(
    tmp_path: Path, monkeypatch
):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content=""),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    for w in doc.warnings:
        assert isinstance(w.reason, str)
        assert len(w.reason) > 0


def test_kreuzberg_parser_parse_warning_has_details_dict(
    tmp_path: Path, monkeypatch
):
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="x"),
    )
    src = tmp_path / "x.pdf"
    src.write_bytes(b"%PDF")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    pdf_bbox_warning = next(
        (w for w in doc.warnings if w.code == "kreuzberg_pdf_no_bbox"), None
    )
    assert pdf_bbox_warning is not None
    assert "source_type" in pdf_bbox_warning.details
    assert pdf_bbox_warning.details["source_type"] == "pdf"


# ---------- KreuzbergParser 实例复用 ----------


def test_kreuzberg_parser_can_be_reused_across_files(
    tmp_path: Path, monkeypatch
):
    """同一实例可解析多文件，结果独立。"""
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="hello"),
    )
    p1 = tmp_path / "a.docx"
    p1.write_bytes(b"docx")
    p2 = tmp_path / "b.docx"
    p2.write_bytes(b"docx")

    parser = KreuzbergParser()
    doc1 = parser.parse(p1, source_hash="a" * 64)
    doc2 = parser.parse(p2, source_hash="b" * 64)
    assert doc1.document_id != doc2.document_id
    assert doc1.source_path != doc2.source_path


def test_kreuzberg_parser_stateless_no_counter_leak(
    tmp_path: Path, monkeypatch
):
    """多次 parse 不带状态泄漏（element_id 从 e0000 起）。"""
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="para"),
    )
    p1 = tmp_path / "a.docx"
    p1.write_bytes(b"docx")
    p2 = tmp_path / "b.docx"
    p2.write_bytes(b"docx")

    parser = KreuzbergParser()
    doc1 = parser.parse(p1, source_hash="a" * 64)
    doc2 = parser.parse(p2, source_hash="b" * 64)
    assert doc1.elements[0].element_id.endswith("::e0000")
    assert doc2.elements[0].element_id.endswith("::e0000")


# ---------- schema 通过 ----------


def test_kreuzberg_parser_parse_result_passes_schema(
    tmp_path: Path, monkeypatch
):
    """parse 出的 Document 通过 schema 校验。"""
    from app.schema import is_valid
    import app.parsers.kreuzberg_parser as mod
    monkeypatch.setattr(
        mod.kreuzberg, "extract_file_sync",
        lambda *a, **kw: _make_mock_result(content="# H\n\nparagraph"),
    )
    src = tmp_path / "x.docx"
    src.write_bytes(b"docx")
    parser = KreuzbergParser()
    doc = parser.parse(src, source_hash="a" * 64)
    assert is_valid(doc.to_dict()) is True
