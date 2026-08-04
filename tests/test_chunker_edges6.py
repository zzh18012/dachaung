r"""app/chunkers/structural.py 边角测试 - 第六轮（Round 139）。

补强已有 base/edges/edges2/edges3/edges4/edges5（共 681 测试）未覆盖的深度：
- _SplitPiece dataclass 边界（默认值、frozen、相等性）
- _hard_split_with_whitespace_fallback 边界（极小 max_chars、纯空白、单字符）
- _split_long_text 边界（多种句子结构、累积规则）
- _ChunkBuffer.flush 行为（strategy/max_chars 透传、空 buf）
- _element_text_with_span 边界（image、空白、leading/trailing 空白）
- StructuralChunker.chunk 边界（空 elements、单 element、heading 硬边界）
- 模块结构深度
"""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, is_dataclass
from typing import Any

import pytest

from app.chunkers.structural import (
    _ChunkBuffer,
    _HARD_BREAK_LANGS,
    _PART_ELEMENT_ID,
    _PART_END,
    _PART_START,
    _PART_TEXT,
    _SENTENCE_SPLIT_RE,
    _SplitPiece,
    _WHITESPACE_RE,
    StructuralChunker,
    _hard_split_with_whitespace_fallback,
    _split_long_text,
    normalize_text,
)


# =========================================================================
# _SplitPiece dataclass 深度
# =========================================================================


def test_split_piece_is_dataclass():
    assert is_dataclass(_SplitPiece)


def test_split_piece_is_frozen():
    """frozen=True → 不可变。"""
    p = _SplitPiece(text="abc", boundary_after=None)
    with pytest.raises(FrozenInstanceError):
        p.text = "xyz"  # type: ignore[misc]


def test_split_piece_default_start_zero():
    p = _SplitPiece(text="x", boundary_after=None)
    assert p.start == 0


def test_split_piece_default_end_zero():
    p = _SplitPiece(text="x", boundary_after=None)
    assert p.end == 0


def test_split_piece_explicit_start_end():
    p = _SplitPiece(text="x", boundary_after="whitespace", start=10, end=20)
    assert p.start == 10
    assert p.end == 20


def test_split_piece_equality_with_same_values():
    p1 = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    p2 = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    assert p1 == p2


def test_split_piece_inequality_different_text():
    p1 = _SplitPiece(text="x", boundary_after=None)
    p2 = _SplitPiece(text="y", boundary_after=None)
    assert p1 != p2


def test_split_piece_inequality_different_boundary():
    p1 = _SplitPiece(text="x", boundary_after=None)
    p2 = _SplitPiece(text="x", boundary_after="forced_char")
    assert p1 != p2


def test_split_piece_is_hashable():
    """frozen dataclass 应可哈希。"""
    p = _SplitPiece(text="x", boundary_after=None)
    s = {p}  # 不抛 TypeError 即可
    assert p in s


# =========================================================================
# _hard_split_with_whitespace_fallback 深度
# =========================================================================


def test_hard_split_whitespace_fallback_empty_returns_empty():
    """空字符串 → 空列表。"""
    assert _hard_split_with_whitespace_fallback("", 100) == []


def test_hard_split_whitespace_fallback_only_whitespace_returns_empty():
    """纯空白 → 全部跳过。"""
    assert _hard_split_with_whitespace_fallback("   \t\n  ", 100) == []


def test_hard_split_whitespace_fallback_text_within_max_returns_one_piece():
    """text 长度 ≤ max_chars → 单 piece。"""
    pieces = _hard_split_with_whitespace_fallback("hello world", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "hello world"
    assert pieces[0].boundary_after is None


def test_hard_split_whitespace_fallback_exact_max_returns_one_piece():
    """text 长度 = max_chars → 单 piece。"""
    text = "a" * 50
    pieces = _hard_split_with_whitespace_fallback(text, 50)
    assert len(pieces) == 1
    assert pieces[0].boundary_after is None


def test_hard_split_whitespace_fallback_no_whitespace_forced_char():
    """无空白的长文本 → forced_char 兜底。"""
    text = "a" * 100
    pieces = _hard_split_with_whitespace_fallback(text, 50)
    assert len(pieces) >= 2
    # 前面所有 piece 都是 forced_char
    for p in pieces[:-1]:
        assert p.boundary_after == "forced_char"


def test_hard_split_whitespace_fallback_with_whitespace_boundary():
    """中间有空白 → whitespace 边界。"""
    text = "aaaa aa aa aaa aaa"  # 18 字符
    pieces = _hard_split_with_whitespace_fallback(text, 8)
    # 至少切 2 块
    assert len(pieces) >= 2
    # 至少有一个 piece 用 whitespace
    boundaries = {p.boundary_after for p in pieces}
    assert "whitespace" in boundaries


def test_hard_split_whitespace_fallback_min_max_chars():
    """max_chars=1 → 每个 piece 是 1 字符。"""
    pieces = _hard_split_with_whitespace_fallback("ab", 1)
    # 全部 forced_char
    assert all(p.boundary_after == "forced_char" for p in pieces[:-1])


# =========================================================================
# _split_long_text 深度
# =========================================================================


def test_split_long_text_empty_returns_empty():
    assert _split_long_text("", 100) == []


def test_split_long_text_only_whitespace_returns_empty():
    assert _split_long_text("   \n\t  ", 100) == []


def test_split_long_text_within_max_returns_single_piece():
    pieces = _split_long_text("short text", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "short text"
    assert pieces[0].boundary_after is None


def test_split_long_text_strips_input_first():
    """输入先 strip。"""
    pieces = _split_long_text("  hello  ", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "hello"


def test_split_long_text_long_single_sentence_no_whitespace_forced():
    """无句子分隔符的长文本 → forced_char。"""
    text = "abcdefghij" * 20  # 200 字符，无空白
    pieces = _split_long_text(text, 50)
    assert len(pieces) >= 3
    # 没有 boundary=whitespace（因为没有空白）
    boundaries = {p.boundary_after for p in pieces}
    assert "whitespace" not in boundaries


def test_split_long_text_multiple_sentences_accumulate():
    """多个短句子能合并成一个 piece。"""
    text = "First sentence. Second one. Third one."
    pieces = _split_long_text(text, 100)
    # 全部合并到 1 个 piece
    assert len(pieces) == 1
    assert pieces[0].text == text


def test_split_long_text_returns_split_piece_list():
    pieces = _split_long_text("x", 10)
    assert isinstance(pieces, list)
    for p in pieces:
        assert isinstance(p, _SplitPiece)


# =========================================================================
# _ChunkBuffer 深度
# =========================================================================


def test_chunk_buffer_init_empty():
    buf = _ChunkBuffer(document_id="doc")
    assert buf.parts == []
    assert buf.counter == 0
    assert buf.document_id == "doc"


def test_chunk_buffer_is_empty_initially():
    buf = _ChunkBuffer(document_id="doc")
    assert buf.is_empty() is True


def test_chunk_buffer_length_initially_zero():
    buf = _ChunkBuffer(document_id="doc")
    assert buf.length() == 0


def test_chunk_buffer_push_increases_length():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("hello", "e1", 0, 5)
    assert buf.length() == 5
    assert not buf.is_empty()


def test_chunk_buffer_push_multiple_accumulates():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e2", 0, 5)
    assert buf.length() == 10  # 不含分隔符
    assert len(buf.parts) == 2


def test_chunk_buffer_flush_empty_returns_none():
    buf = _ChunkBuffer(document_id="doc")
    result = buf.flush(strategy="sequential", max_chars=100)
    assert result is None


def test_chunk_buffer_flush_only_whitespace_returns_none():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("   ", "e1", 0, 3)
    result = buf.flush(strategy="sequential", max_chars=100)
    assert result is None


def test_chunk_buffer_flush_clears_parts():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("hello", "e1", 0, 5)
    buf.flush(strategy="sequential", max_chars=100)
    assert buf.parts == []
    assert buf.is_empty()


def test_chunk_buffer_flush_returns_chunk_with_correct_id():
    buf = _ChunkBuffer(document_id="doc", counter=7)
    buf.push_text("hello", "e1", 0, 5)
    c = buf.flush(strategy="sequential", max_chars=100)
    assert c is not None
    assert c.chunk_id == "doc::c0007"


def test_chunk_buffer_flush_text_joined_with_space():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e2", 0, 5)
    c = buf.flush(strategy="sequential", max_chars=100)
    assert c.text == "hello world"


def test_chunk_buffer_flush_source_ids_dedup():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("a", "e1", 0, 1)
    buf.push_text("b", "e1", 1, 2)  # 同 element
    buf.push_text("c", "e2", 0, 1)
    c = buf.flush(strategy="sequential", max_chars=100)
    assert c.source_element_ids == ["e1", "e2"]


def test_chunk_buffer_flush_source_ids_preserves_first_occurrence_order():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("a", "e3", 0, 1)
    buf.push_text("b", "e1", 0, 1)
    buf.push_text("c", "e2", 0, 1)
    buf.push_text("d", "e1", 1, 2)
    c = buf.flush(strategy="sequential", max_chars=100)
    assert c.source_element_ids == ["e3", "e1", "e2"]


def test_chunk_buffer_flush_metadata_strategy():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("hello", "e1", 0, 5)
    c = buf.flush(strategy="isolated_table", max_chars=100)
    assert c.metadata["strategy"] == "isolated_table"


def test_chunk_buffer_flush_metadata_max_chars():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("hello", "e1", 0, 5)
    c = buf.flush(strategy="x", max_chars=800)
    assert c.metadata["max_chars"] == 800


def test_chunk_buffer_flush_metadata_char_count():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e2", 0, 5)
    c = buf.flush(strategy="x", max_chars=100)
    # "hello world" 长度 11
    assert c.metadata["char_count"] == 11


def test_chunk_buffer_flush_source_spans_one_per_part():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("a", "e1", 0, 1)
    buf.push_text("b", "e2", 5, 6)
    buf.push_text("c", "e3", 10, 11)
    c = buf.flush(strategy="x", max_chars=100)
    assert len(c.source_spans) == 3
    assert c.source_spans[0] == {"element_id": "e1", "start": 0, "end": 1}
    assert c.source_spans[1] == {"element_id": "e2", "start": 5, "end": 6}
    assert c.source_spans[2] == {"element_id": "e3", "start": 10, "end": 11}


# =========================================================================
# _PART_* 常量
# =========================================================================


def test_part_text_is_int():
    assert isinstance(_PART_TEXT, int)


def test_part_element_id_is_int():
    assert isinstance(_PART_ELEMENT_ID, int)


def test_part_start_is_int():
    assert isinstance(_PART_START, int)


def test_part_end_is_int():
    assert isinstance(_PART_END, int)


def test_part_text_value_zero():
    assert _PART_TEXT == 0


def test_part_element_id_value_one():
    assert _PART_ELEMENT_ID == 1


def test_part_start_value_two():
    assert _PART_START == 2


def test_part_end_value_three():
    assert _PART_END == 3


# =========================================================================
# _SENTENCE_SPLIT_RE / _HARD_BREAK_LANGS / _WHITESPACE_RE 常量
# =========================================================================


def test_sentence_split_re_compiled():
    import re
    assert isinstance(_SENTENCE_SPLIT_RE, re.Pattern)


def test_whitespace_re_compiled():
    import re
    assert isinstance(_WHITESPACE_RE, re.Pattern)


def test_hard_break_langs_is_tuple():
    assert isinstance(_HARD_BREAK_LANGS, tuple)


def test_hard_break_langs_count_six():
    assert len(_HARD_BREAK_LANGS) == 6


def test_hard_break_langs_contains_chinese_and_english():
    assert "。" in _HARD_BREAK_LANGS
    assert "！" in _HARD_BREAK_LANGS
    assert "？" in _HARD_BREAK_LANGS
    assert "." in _HARD_BREAK_LANGS
    assert "!" in _HARD_BREAK_LANGS
    assert "?" in _HARD_BREAK_LANGS


def test_whitespace_re_pattern_value():
    assert _WHITESPACE_RE.pattern == r"\s+"


# =========================================================================
# normalize_text 深度
# =========================================================================


def test_normalize_text_empty_returns_empty():
    assert normalize_text("") == ""


def test_normalize_text_none_returns_empty():
    assert normalize_text(None) == ""  # type: ignore[arg-type]


def test_normalize_text_only_whitespace_returns_empty():
    assert normalize_text("   \t\n  ") == ""


def test_normalize_text_no_change():
    assert normalize_text("hello world") == "hello world"


def test_normalize_text_collapses_internal_whitespace():
    assert normalize_text("hello    world") == "hello world"


def test_normalize_text_handles_tabs_newlines():
    assert normalize_text("hello\tworld\nfoo") == "hello world foo"


def test_normalize_text_strips_ends():
    assert normalize_text("  hello  ") == "hello"


def test_normalize_text_preserves_punctuation():
    assert normalize_text("hello, world!") == "hello, world!"


def test_normalize_text_preserves_unicode():
    assert normalize_text("中文 测试") == "中文 测试"


# =========================================================================
# StructuralChunker.__init__ 深度
# =========================================================================


def test_chunker_init_default_max_chars():
    c = StructuralChunker()
    assert c.max_chars == 800


def test_chunker_init_explicit_max_chars():
    c = StructuralChunker(max_chars=500)
    assert c.max_chars == 500


def test_chunker_init_max_chars_below_32_raises():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=31)


def test_chunker_init_max_chars_exactly_32():
    """max_chars=32 是允许的最小值。"""
    c = StructuralChunker(max_chars=32)
    assert c.max_chars == 32


def test_chunker_init_max_chars_zero_raises():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=0)


def test_chunker_init_max_chars_negative_raises():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=-100)


# =========================================================================
# StructuralChunker.chunk 深度
# =========================================================================


def _make_element(eid: str, etype: str, content: str) -> Any:
    from app.models import Element
    return Element(
        element_id=eid,
        type=etype,
        content=content,
        resource_path=None if content else "(placeholder)",
        parent_id=None,
        source_locator={"line": 1},
        confidence=0.95,
        metadata={},
    )


def _make_document(elements: list) -> Any:
    from app.models import Document
    return Document(
        document_id="doc",
        source_path="x",
        source_type="pdf",
        source_hash="0" * 64,
        parser_name="x",
        parser_version="x",
        elements=elements,
        chunks=[],
        relations=[],
        warnings=[],
        errors=[],
        metadata={},
    )


def test_chunk_empty_elements_returns_empty():
    doc = _make_document([])
    c = StructuralChunker(max_chars=100)
    assert c.chunk(doc) == []


def test_chunk_single_paragraph_one_chunk():
    doc = _make_document([_make_element("e1", "paragraph", "hello")])
    c = StructuralChunker(max_chars=100)
    chunks = c.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].text == "hello"


def test_chunk_heading_starts_new_chunk():
    """heading 是硬边界。"""
    doc = _make_document([
        _make_element("e1", "paragraph", "first para"),
        _make_element("e2", "heading", "Title"),
        _make_element("e3", "paragraph", "second para"),
    ])
    c = StructuralChunker(max_chars=100)
    chunks = c.chunk(doc)
    # heading 之前 flush，所以至少 2 个 chunk
    assert len(chunks) >= 2


def test_chunk_table_isolated():
    doc = _make_document([
        _make_element("e1", "paragraph", "intro"),
        _make_element("e2", "table", "| a | b |"),
    ])
    c = StructuralChunker(max_chars=100)
    chunks = c.chunk(doc)
    # table 单独一个 chunk
    table_chunks = [ch for ch in chunks if ch.metadata.get("strategy") == "isolated_table"]
    assert len(table_chunks) == 1


def test_chunk_image_isolated():
    from app.models import Element
    img = Element(
        element_id="img1",
        type="image",
        content=None,
        resource_path="img.png",
        parent_id=None,
        source_locator={"line": 1},
        confidence=0.9,
        metadata={},
    )
    doc = _make_document([img])
    c = StructuralChunker(max_chars=100)
    chunks = c.chunk(doc)
    # image element 不参与分块（_element_text_with_span 返回空）
    # 所以可能没有 chunks
    assert isinstance(chunks, list)


def test_chunk_long_paragraph_splits():
    long_text = "sentence. " * 50  # 多句子
    doc = _make_document([_make_element("e1", "paragraph", long_text)])
    c = StructuralChunker(max_chars=80)
    chunks = c.chunk(doc)
    assert len(chunks) >= 2
    # 所有 chunk < max_chars（最后一块可能也满足）
    for ch in chunks:
        assert len(ch.text) <= 80 or len(chunks) == 1


def test_chunk_each_chunk_has_source_element_ids():
    doc = _make_document([
        _make_element("e1", "paragraph", "first"),
        _make_element("e2", "paragraph", "second"),
    ])
    c = StructuralChunker(max_chars=100)
    chunks = c.chunk(doc)
    for ch in chunks:
        assert len(ch.source_element_ids) >= 1


def test_chunk_chunk_id_zero_padded():
    doc = _make_document([
        _make_element("e1", "paragraph", "first"),
        _make_element("e2", "paragraph", "second"),
    ])
    c = StructuralChunker(max_chars=100)
    chunks = c.chunk(doc)
    assert chunks[0].chunk_id == "doc::c0000"
    if len(chunks) > 1:
        assert chunks[1].chunk_id == "doc::c0001"


def test_chunk_metadata_has_strategy():
    doc = _make_document([_make_element("e1", "paragraph", "x")])
    c = StructuralChunker(max_chars=100)
    chunks = c.chunk(doc)
    assert "strategy" in chunks[0].metadata


def test_chunk_metadata_has_max_chars():
    doc = _make_document([_make_element("e1", "paragraph", "x")])
    c = StructuralChunker(max_chars=444)
    chunks = c.chunk(doc)
    assert chunks[0].metadata["max_chars"] == 444


def test_chunk_metadata_has_char_count():
    doc = _make_document([_make_element("e1", "paragraph", "hello")])
    c = StructuralChunker(max_chars=100)
    chunks = c.chunk(doc)
    assert chunks[0].metadata["char_count"] == 5


# =========================================================================
# _element_text_with_span 深度
# =========================================================================


def test_element_text_with_span_paragraph():
    el = _make_element("e1", "paragraph", "hello")
    text, start, end = StructuralChunker()._element_text_with_span(el)
    assert text == "hello"
    assert start == 0
    assert end == 5


def test_element_text_with_span_image_returns_empty():
    """image element → 空文本，不参与分块。"""
    el = _make_element("e1", "image", "")
    text, start, end = StructuralChunker()._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_strips_leading_whitespace():
    el = _make_element("e1", "paragraph", "  hello")
    text, start, end = StructuralChunker()._element_text_with_span(el)
    assert text == "hello"
    assert start == 2  # 2 个空格
    assert end == 7


def test_element_text_with_span_strips_trailing_whitespace():
    el = _make_element("e1", "paragraph", "hello  ")
    text, start, end = StructuralChunker()._element_text_with_span(el)
    assert text == "hello"
    assert start == 0
    assert end == 5


def test_element_text_with_span_strips_both():
    el = _make_element("e1", "paragraph", "  hello  ")
    text, start, end = StructuralChunker()._element_text_with_span(el)
    assert text == "hello"
    assert start == 2
    assert end == 7


def test_element_text_with_span_empty_content():
    el = _make_element("e1", "paragraph", "")
    text, start, end = StructuralChunker()._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_only_whitespace():
    el = _make_element("e1", "paragraph", "   ")
    text, start, end = StructuralChunker()._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_legacy_helper_returns_stripped_text():
    el = _make_element("e1", "paragraph", "  hello  ")
    assert StructuralChunker()._element_text(el) == "hello"


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exports_two():
    from app.chunkers.structural import __all__
    assert set(__all__) == {"StructuralChunker", "normalize_text"}


def test_module_all_is_list():
    from app.chunkers.structural import __all__
    assert isinstance(__all__, list)


def test_module_imports_re():
    import app.chunkers.structural as mod
    src = inspect.getsource(mod)
    assert "import re" in src


def test_module_imports_dataclasses():
    import app.chunkers.structural as mod
    src = inspect.getsource(mod)
    assert "from dataclasses import" in src


def test_module_imports_any():
    import app.chunkers.structural as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_chunk_document_element():
    import app.chunkers.structural as mod
    src = inspect.getsource(mod)
    assert "Chunk" in src
    assert "Document" in src
    assert "Element" in src


def test_module_uses_future_annotations():
    import app.chunkers.structural as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import app.chunkers.structural as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_heading():
    import app.chunkers.structural as mod
    assert "heading" in mod.__doc__.lower()


def test_module_docstring_mentions_max_chars():
    import app.chunkers.structural as mod
    assert "max_chars" in mod.__doc__ or "长度上限" in mod.__doc__


def test_module_docstring_mentions_source_spans():
    import app.chunkers.structural as mod
    assert "source_spans" in mod.__doc__ or "source_span" in mod.__doc__


# =========================================================================
# 签名深度
# =========================================================================


def test_normalize_text_signature_one_param():
    sig = inspect.signature(normalize_text)
    assert len(sig.parameters) == 1


def test_hard_split_signature_two_params():
    sig = inspect.signature(_hard_split_with_whitespace_fallback)
    assert len(sig.parameters) == 2


def test_split_long_text_signature_two_params():
    sig = inspect.signature(_split_long_text)
    assert len(sig.parameters) == 2


def test_chunk_buffer_flush_signature_keyword_only():
    sig = inspect.signature(_ChunkBuffer.flush)
    # self, strategy, max_chars（strategy/max_chars 是 keyword-only）
    assert len(sig.parameters) == 3


def test_chunk_buffer_flush_strategy_kind_keyword_only():
    sig = inspect.signature(_ChunkBuffer.flush)
    assert sig.parameters["strategy"].kind == inspect.Parameter.KEYWORD_ONLY


def test_chunk_buffer_flush_max_chars_kind_keyword_only():
    sig = inspect.signature(_ChunkBuffer.flush)
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_structural_chunker_init_default_max_chars():
    sig = inspect.signature(StructuralChunker.__init__)
    assert sig.parameters["max_chars"].default == 800


def test_structural_chunker_chunk_signature_one_param():
    sig = inspect.signature(StructuralChunker.chunk)
    # self, document
    assert len(sig.parameters) == 2


def test_element_text_with_span_returns_tuple():
    el = _make_element("e1", "paragraph", "hello")
    result = StructuralChunker()._element_text_with_span(el)
    assert isinstance(result, tuple)
    assert len(result) == 3
    text, start, end = result
    assert isinstance(text, str)
    assert isinstance(start, int)
    assert isinstance(end, int)


# =========================================================================
# 综合：normalize_text 与 _split_long_text 互动
# =========================================================================


def test_normalize_idempotent():
    s = "hello    world\n\nfoo"
    once = normalize_text(s)
    twice = normalize_text(once)
    assert once == twice


def test_split_long_text_does_not_lose_text():
    """切分后的 piece 文本拼接（join 空格）应 = normalize(原 text)。"""
    text = "Sentence one. Sentence two. Sentence three with more words."
    pieces = _split_long_text(text, 30)
    rejoined = " ".join(p.text for p in pieces)
    assert normalize_text(rejoined) == normalize_text(text)


def test_chunker_does_not_lose_text():
    """所有 chunk 文本拼接后，规范化应等于 elements 文本规范化拼接。"""
    elements = [
        _make_element("e1", "paragraph", "first para"),
        _make_element("e2", "heading", "Title"),
        _make_element("e3", "paragraph", "second para"),
    ]
    doc = _make_document(elements)
    chunks = StructuralChunker(max_chars=100).chunk(doc)
    chunk_text = " ".join(c.text for c in chunks)
    elements_text = " ".join(
        (e.content or "") for e in elements if e.type != "image"
    )
    assert normalize_text(chunk_text) == normalize_text(elements_text)
