r"""app/chunkers/structural.py 边角测试 - 第七轮（Round 161）。

补强已有 base/edges/edges2-6（共 792 测试）未覆盖的深度：
- 常量精确性（_SENTENCE_SPLIT_RE、_HARD_BREAK_LANGS、_WHITESPACE_RE）
- _SplitPiece frozen dataclass 行为
- _hard_split_with_whitespace_fallback 深度边界
- _split_long_text 句子累积、超长句子、混合
- _ChunkBuffer push/length/is_empty/flush 深度
- StructuralChunker.chunk 多场景
- _element_text_with_span 深度
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
import re
from dataclasses import FrozenInstanceError, fields, is_dataclass
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
    _hard_split_with_whitespace_fallback,
    _split_long_text,
    normalize_text,
)
from app.models import Chunk, Document, Element


# =========================================================================
# 常量精确性
# =========================================================================


def test_sentence_split_re_is_compiled_pattern():
    assert isinstance(_SENTENCE_SPLIT_RE, re.Pattern)


def test_sentence_split_re_pattern_value():
    """split 在句末标点后的空白处。"""
    pattern_str = _SENTENCE_SPLIT_RE.pattern
    # 应含 lookbehind 与各 break chars
    assert "。！" in pattern_str or "。" in pattern_str
    assert "." in pattern_str


def test_whitespace_re_is_compiled_pattern():
    assert isinstance(_WHITESPACE_RE, re.Pattern)


def test_whitespace_re_pattern_value():
    assert _WHITESPACE_RE.pattern == r"\s+"


def test_hard_break_langs_count_is_six():
    """6 种句末标点（3 中 + 3 英）。"""
    assert len(_HARD_BREAK_LANGS) == 6


def test_hard_break_langs_exact_members():
    expected = ("。", "！", "？", ".", "!", "?")
    assert set(_HARD_BREAK_LANGS) == set(expected)


def test_hard_break_langs_is_tuple():
    assert isinstance(_HARD_BREAK_LANGS, tuple)


def test_hard_break_langs_no_duplicates():
    assert len(_HARD_BREAK_LANGS) == len(set(_HARD_BREAK_LANGS))


def test_part_constants_values():
    """_PART_TEXT/ELEMENT_ID/START/END 是 tuple field 索引 0/1/2/3。"""
    assert _PART_TEXT == 0
    assert _PART_ELEMENT_ID == 1
    assert _PART_START == 2
    assert _PART_END == 3


def test_part_constants_distinct():
    assert len({_PART_TEXT, _PART_ELEMENT_ID, _PART_START, _PART_END}) == 4


# =========================================================================
# _SplitPiece frozen dataclass
# =========================================================================


def test_split_piece_is_dataclass():
    assert is_dataclass(_SplitPiece)


def test_split_piece_is_frozen():
    p = _SplitPiece(text="x", boundary_after=None)
    with pytest.raises(FrozenInstanceError):
        p.text = "y"


def test_split_piece_field_count():
    fs = fields(_SplitPiece)
    assert len(fs) == 4


def test_split_piece_field_names_exact():
    fs = fields(_SplitPiece)
    names = {f.name for f in fs}
    assert names == {"text", "boundary_after", "start", "end"}


def test_split_piece_text_no_default():
    """text 必填（no default）。"""
    fs = {f.name: f for f in fields(_SplitPiece)}
    # dataclass 的无默认字段 default 是 _MISSING_TYPE 实例
    from dataclasses import _MISSING_TYPE  # type: ignore[attr-defined]
    assert isinstance(fs["text"].default, _MISSING_TYPE)
    with pytest.raises(TypeError):
        _SplitPiece()  # type: ignore[call-arg]


def test_split_piece_boundary_after_required():
    """boundary_after 必填（no default）。"""
    fs = {f.name: f for f in fields(_SplitPiece)}
    from dataclasses import _MISSING_TYPE  # type: ignore[attr-defined]
    assert isinstance(fs["boundary_after"].default, _MISSING_TYPE)
    with pytest.raises(TypeError):
        _SplitPiece(text="x")  # type: ignore[call-arg]


def test_split_piece_start_default_zero():
    p = _SplitPiece(text="x", boundary_after=None)
    assert p.start == 0


def test_split_piece_end_default_zero():
    p = _SplitPiece(text="x", boundary_after=None)
    assert p.end == 0


def test_split_piece_equality_same_values():
    a = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    b = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    assert a == b


def test_split_piece_equality_different_text():
    a = _SplitPiece(text="x", boundary_after=None)
    b = _SplitPiece(text="y", boundary_after=None)
    assert a != b


def test_split_piece_hashable():
    """frozen dataclass 应可 hash。"""
    p = _SplitPiece(text="x", boundary_after=None)
    h = hash(p)
    assert isinstance(h, int)


def test_split_piece_boundary_after_accepts_string_values():
    """boundary_after 接受 'whitespace' / 'forced_char' / None。"""
    a = _SplitPiece(text="x", boundary_after="whitespace")
    b = _SplitPiece(text="x", boundary_after="forced_char")
    c = _SplitPiece(text="x", boundary_after=None)
    assert a.boundary_after == "whitespace"
    assert b.boundary_after == "forced_char"
    assert c.boundary_after is None


def test_split_piece_repr_has_class_name():
    p = _SplitPiece(text="x", boundary_after=None)
    assert "_SplitPiece" in repr(p)


# =========================================================================
# _hard_split_with_whitespace_fallback 深度
# =========================================================================


def test_hard_split_empty_text_returns_empty():
    assert _hard_split_with_whitespace_fallback("", 100) == []


def test_hard_split_text_shorter_than_max_returns_single_piece():
    pieces = _hard_split_with_whitespace_fallback("hello", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "hello"
    assert pieces[0].boundary_after is None


def test_hard_split_text_exactly_max_returns_single_piece():
    pieces = _hard_split_with_whitespace_fallback("hello", 5)
    assert len(pieces) == 1
    assert pieces[0].text == "hello"


def test_hard_split_long_text_no_whitespace_forced_char():
    """无空白的长文本 → forced_char。"""
    pieces = _hard_split_with_whitespace_fallback("aaaaaaaaaa", 5)
    assert len(pieces) >= 2
    for p in pieces[:-1]:
        assert p.boundary_after == "forced_char"


def test_hard_split_long_text_with_whitespace_at_boundary():
    """在 [i+max//2, i+max] 闭区间有空白 → whitespace。"""
    # max_chars=10, 在 [5, 10] 之间有空白（位置 7）
    pieces = _hard_split_with_whitespace_fallback("aaaaaa bbbbbbbb", 10)
    # 第一段应在位置 7 的空白切
    assert pieces[0].boundary_after == "whitespace"


def test_hard_split_leading_whitespace_skipped():
    pieces = _hard_split_with_whitespace_fallback("   hello", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "hello"


def test_hard_split_trailing_whitespace_stripped():
    pieces = _hard_split_with_whitespace_fallback("hello   ", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "hello"


def test_hard_split_only_whitespace_returns_empty():
    pieces = _hard_split_with_whitespace_fallback("    ", 100)
    assert pieces == []


def test_hard_split_piece_start_end_in_input_coords():
    """start/end 在输入 text 坐标系中。"""
    pieces = _hard_split_with_whitespace_fallback("hello world", 100)
    assert len(pieces) == 1
    assert pieces[0].start == 0
    assert pieces[0].end == 11  # len("hello world")


def test_hard_split_max_chars_minimum():
    """max_chars=1 → 每字符成 piece。"""
    pieces = _hard_split_with_whitespace_fallback("abc", 1)
    # boundary_after='forced_char' for all but last
    assert len(pieces) == 3


# =========================================================================
# _split_long_text 深度
# =========================================================================


def test_split_long_text_empty_returns_empty_list():
    assert _split_long_text("", 100) == []


def test_split_long_text_only_whitespace_returns_empty_list():
    assert _split_long_text("   \n\t  ", 100) == []


def test_split_long_text_shorter_than_max_returns_single():
    pieces = _split_long_text("hello", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "hello"
    assert pieces[0].boundary_after is None
    assert pieces[0].start == 0
    assert pieces[0].end == 5


def test_split_long_text_exactly_max_returns_single():
    pieces = _split_long_text("hello", 5)
    assert len(pieces) == 1


def test_split_long_text_long_text_split():
    """长文本切多 piece。"""
    pieces = _split_long_text("a" * 100, 10)
    assert len(pieces) > 1
    for p in pieces:
        assert len(p.text) <= 10


def test_split_long_text_multiple_sentences():
    """句子分隔 → 多 piece（若每句 <= max，可能合并为 1 个）。"""
    text = "Hello world. This is a test. Bye."
    pieces = _split_long_text(text, 100)
    # 应合并为单个 piece（总长 < 100）
    assert len(pieces) == 1


def test_split_long_text_each_piece_within_max():
    """所有 piece 都 <= max_chars。"""
    text = " ".join(["hello"] * 50)
    pieces = _split_long_text(text, 30)
    for p in pieces:
        assert len(p.text) <= 30


def test_split_long_text_strips_input():
    """strip 前导/尾随空白。"""
    pieces = _split_long_text("  hello  ", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "hello"


def test_split_long_text_does_not_lose_chars():
    """字符数守恒（拼接 piece.text 用空格，长度 + N-1 = 原 stripped len）。"""
    text = "hello world this is a long text used for testing"
    pieces = _split_long_text(text, 20)
    joined = " ".join(p.text for p in pieces)
    # 应等于原 text（已 strip）
    assert normalize_text(joined) == normalize_text(text)


# =========================================================================
# _ChunkBuffer 深度
# =========================================================================


def test_chunk_buffer_init_empty():
    buf = _ChunkBuffer(document_id="doc1")
    assert buf.document_id == "doc1"
    assert buf.parts == []
    assert buf.counter == 0


def test_chunk_buffer_is_empty_initially():
    buf = _ChunkBuffer(document_id="doc1")
    assert buf.is_empty() is True


def test_chunk_buffer_length_zero_initially():
    buf = _ChunkBuffer(document_id="doc1")
    assert buf.length() == 0


def test_chunk_buffer_push_text_adds_part():
    buf = _ChunkBuffer(document_id="doc1")
    buf.push_text("hello", "e1", 0, 5)
    assert len(buf.parts) == 1
    assert buf.parts[0] == ("hello", "e1", 0, 5)


def test_chunk_buffer_length_sums_part_text_lengths():
    buf = _ChunkBuffer(document_id="doc1")
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e2", 0, 5)
    assert buf.length() == 10  # "hello" + "world"


def test_chunk_buffer_is_empty_false_after_push():
    buf = _ChunkBuffer(document_id="doc1")
    buf.push_text("x", "e1", 0, 1)
    assert buf.is_empty() is False


def test_chunk_buffer_flush_empty_returns_none():
    buf = _ChunkBuffer(document_id="doc1")
    result = buf.flush(strategy="sequential", max_chars=800)
    assert result is None


def test_chunk_buffer_flush_returns_chunk():
    buf = _ChunkBuffer(document_id="doc1", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    result = buf.flush(strategy="sequential", max_chars=800)
    assert isinstance(result, Chunk)
    assert result.text == "hello"
    assert result.source_element_ids == ["e1"]


def test_chunk_buffer_flush_clears_parts():
    buf = _ChunkBuffer(document_id="doc1")
    buf.push_text("hello", "e1", 0, 5)
    buf.flush(strategy="sequential", max_chars=800)
    assert buf.parts == []
    assert buf.is_empty() is True


def test_chunk_buffer_flush_dedup_source_ids():
    """同一 element 多次 push → source_element_ids 去重。"""
    buf = _ChunkBuffer(document_id="doc1")
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e1", 6, 11)
    result = buf.flush(strategy="sequential", max_chars=800)
    assert result.source_element_ids == ["e1"]  # 只 1 个


def test_chunk_buffer_flush_preserves_first_occurrence_order():
    buf = _ChunkBuffer(document_id="doc1")
    buf.push_text("a", "e2", 0, 1)
    buf.push_text("b", "e1", 0, 1)
    buf.push_text("c", "e2", 1, 2)
    result = buf.flush(strategy="sequential", max_chars=800)
    # 首次出现顺序：e2, e1
    assert result.source_element_ids == ["e2", "e1"]


def test_chunk_buffer_flush_creates_one_span_per_part():
    buf = _ChunkBuffer(document_id="doc1")
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e2", 0, 5)
    result = buf.flush(strategy="sequential", max_chars=800)
    assert len(result.source_spans) == 2


def test_chunk_buffer_flush_chunk_id_format():
    buf = _ChunkBuffer(document_id="mydoc", counter=3)
    buf.push_text("x", "e1", 0, 1)
    result = buf.flush(strategy="sequential", max_chars=800)
    assert result.chunk_id == "mydoc::c0003"


def test_chunk_buffer_flush_metadata_has_required_keys():
    buf = _ChunkBuffer(document_id="doc1", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    result = buf.flush(strategy="sequential", max_chars=800)
    assert "strategy" in result.metadata
    assert "max_chars" in result.metadata
    assert "char_count" in result.metadata


def test_chunk_buffer_flush_metadata_strategy_value():
    buf = _ChunkBuffer(document_id="doc1")
    buf.push_text("x", "e1", 0, 1)
    result = buf.flush(strategy="custom_strategy", max_chars=800)
    assert result.metadata["strategy"] == "custom_strategy"


def test_chunk_buffer_flush_metadata_max_chars_value():
    buf = _ChunkBuffer(document_id="doc1")
    buf.push_text("x", "e1", 0, 1)
    result = buf.flush(strategy="x", max_chars=500)
    assert result.metadata["max_chars"] == 500


def test_chunk_buffer_flush_char_count_value():
    buf = _ChunkBuffer(document_id="doc1")
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e2", 0, 5)
    result = buf.flush(strategy="x", max_chars=800)
    # "hello world" → 11
    assert result.metadata["char_count"] == 11


def test_chunk_buffer_flush_text_joined_with_single_space():
    buf = _ChunkBuffer(document_id="doc1")
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e2", 0, 5)
    result = buf.flush(strategy="x", max_chars=800)
    assert result.text == "hello world"


def test_chunk_buffer_flush_text_stripped():
    """空文本 part 不影响；结果 strip。"""
    buf = _ChunkBuffer(document_id="doc1")
    buf.push_text("  hello  ", "e1", 0, 9)
    result = buf.flush(strategy="x", max_chars=800)
    # join 后 strip
    assert result.text == "hello"


def test_chunk_buffer_flush_all_empty_parts_returns_none():
    """所有 part 都是空白 → text strip 后为空 → None。"""
    buf = _ChunkBuffer(document_id="doc1")
    buf.push_text("   ", "e1", 0, 3)
    result = buf.flush(strategy="x", max_chars=800)
    assert result is None


def test_chunk_buffer_flush_strategy_kind_keyword_only():
    """flush 的 strategy/max_chars 是 keyword-only。"""
    sig = inspect.signature(_ChunkBuffer.flush)
    assert sig.parameters["strategy"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_chunk_buffer_push_text_signature():
    sig = inspect.signature(_ChunkBuffer.push_text)
    assert set(sig.parameters) == {"self", "text", "element_id", "start", "end"}


def test_chunk_buffer_length_signature_no_args():
    sig = inspect.signature(_ChunkBuffer.length)
    assert len(sig.parameters) == 1  # self


def test_chunk_buffer_is_empty_signature_no_args():
    sig = inspect.signature(_ChunkBuffer.is_empty)
    assert len(sig.parameters) == 1  # self


# =========================================================================
# StructuralChunker __init__ 边界
# =========================================================================


def test_structural_chunker_init_default_max_chars():
    from app.chunkers.structural import StructuralChunker
    c = StructuralChunker()
    assert c.max_chars == 800


def test_structural_chunker_init_custom_max_chars():
    from app.chunkers.structural import StructuralChunker
    c = StructuralChunker(max_chars=500)
    assert c.max_chars == 500


def test_structural_chunker_init_too_small_raises():
    from app.chunkers.structural import StructuralChunker
    with pytest.raises(ValueError) as exc:
        StructuralChunker(max_chars=31)
    assert "max_chars" in str(exc.value)


def test_structural_chunker_init_boundary_32_ok():
    """max_chars=32（边界）→ OK。"""
    from app.chunkers.structural import StructuralChunker
    c = StructuralChunker(max_chars=32)
    assert c.max_chars == 32


def test_structural_chunker_init_zero_raises():
    from app.chunkers.structural import StructuralChunker
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=0)


def test_structural_chunker_init_negative_raises():
    from app.chunkers.structural import StructuralChunker
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=-100)


# =========================================================================
# StructuralChunker.chunk 多场景
# =========================================================================


def _make_doc(elements: list[Element], doc_id: str = "test_doc") -> Document:
    return Document(
        document_id=doc_id,
        source_type="text",
        source_path="x.txt",
        elements=tuple(elements),
        chunks=(),
        relations=(),
        warnings=[],
        errors=[],
        parser_name="text",
        parser_version="1.0",
        source_hash="hash",
        metadata={},
    )


def _make_el(el_id: str, etype: str, content: str) -> Element:
    return Element(
        element_id=el_id,
        type=etype,
        content=content if content else None,
        resource_path=None if content else "placeholder",
        source_locator=None,
        parent_id=None,
        metadata={},
    )


def test_chunker_chunk_no_elements():
    from app.chunkers.structural import StructuralChunker
    doc = _make_doc([])
    c = StructuralChunker(max_chars=800)
    assert c.chunk(doc) == []


def test_chunker_chunk_single_short_paragraph():
    from app.chunkers.structural import StructuralChunker
    doc = _make_doc([_make_el("e1", "paragraph", "hello world")])
    c = StructuralChunker(max_chars=800)
    chunks = c.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].text == "hello world"


def test_chunker_chunk_heading_creates_boundary():
    """heading → 之前 buf flush，heading 入新 buf。"""
    from app.chunkers.structural import StructuralChunker
    doc = _make_doc([
        _make_el("e1", "paragraph", "first para"),
        _make_el("e2", "heading", "Section 1"),
        _make_el("e3", "paragraph", "second para"),
    ])
    c = StructuralChunker(max_chars=800)
    chunks = c.chunk(doc)
    # 应至少 2 个 chunk（heading 前后分）
    assert len(chunks) >= 2


def test_chunker_chunk_table_isolated():
    """table element → 单独成 chunk。"""
    from app.chunkers.structural import StructuralChunker
    doc = _make_doc([
        _make_el("e1", "paragraph", "before"),
        _make_el("e2", "table", "cell1|cell2"),
        _make_el("e3", "paragraph", "after"),
    ])
    c = StructuralChunker(max_chars=800)
    chunks = c.chunk(doc)
    # 找 isolated_table strategy 的 chunk
    isolated = [c for c in chunks if c.metadata.get("strategy") == "isolated_table"]
    assert len(isolated) == 1
    assert isolated[0].text == "cell1|cell2"


def test_chunker_chunk_image_skipped():
    """image element 不参与分块。"""
    from app.chunkers.structural import StructuralChunker
    doc = _make_doc([
        _make_el("e1", "image", "binary data"),
    ])
    c = StructuralChunker(max_chars=800)
    chunks = c.chunk(doc)
    # image element 跳过 → 0 chunks
    assert chunks == []


def test_chunker_chunk_caption_isolated():
    """caption element → 单独成 chunk。"""
    from app.chunkers.structural import StructuralChunker
    doc = _make_doc([
        _make_el("e1", "caption", "Figure 1 caption"),
    ])
    c = StructuralChunker(max_chars=800)
    chunks = c.chunk(doc)
    isolated = [c for c in chunks if c.metadata.get("strategy") == "isolated_caption"]
    assert len(isolated) == 1


def test_chunker_chunk_long_paragraph_split():
    """超长 paragraph → 多 chunk。"""
    from app.chunkers.structural import StructuralChunker
    long_text = " ".join(["hello"] * 100)  # ~500 chars
    doc = _make_doc([_make_el("e1", "paragraph", long_text)])
    c = StructuralChunker(max_chars=100)
    chunks = c.chunk(doc)
    assert len(chunks) > 1
    for ch in chunks:
        assert len(ch.text) <= 100


def test_chunker_chunk_empty_content_skipped():
    from app.chunkers.structural import StructuralChunker
    doc = _make_doc([
        _make_el("e1", "paragraph", ""),
        _make_el("e2", "paragraph", "   "),
    ])
    c = StructuralChunker(max_chars=800)
    assert c.chunk(doc) == []


def test_chunker_chunk_chunk_id_increments():
    from app.chunkers.structural import StructuralChunker
    doc = _make_doc([
        _make_el("e1", "heading", "S1"),
        _make_el("e2", "heading", "S2"),
        _make_el("e3", "heading", "S3"),
    ])
    c = StructuralChunker(max_chars=800)
    chunks = c.chunk(doc)
    ids = [ch.chunk_id for ch in chunks]
    # 应是 c0000, c0001, c0002
    assert ids == ["test_doc::c0000", "test_doc::c0001", "test_doc::c0002"]


def test_chunker_chunk_strategy_default_sequential():
    from app.chunkers.structural import StructuralChunker
    doc = _make_doc([_make_el("e1", "paragraph", "hello")])
    c = StructuralChunker(max_chars=800)
    chunks = c.chunk(doc)
    assert chunks[0].metadata["strategy"] == "sequential"


# =========================================================================
# _element_text_with_span 边界
# =========================================================================


def test_element_text_with_span_image_returns_empty():
    from app.chunkers.structural import StructuralChunker
    c = StructuralChunker()
    el = _make_el("e1", "image", "binary")
    text, start, end = c._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_empty_content_returns_empty():
    from app.chunkers.structural import StructuralChunker
    c = StructuralChunker()
    el = _make_el("e1", "paragraph", "")
    text, start, end = c._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_none_content_returns_empty():
    from app.chunkers.structural import StructuralChunker
    c = StructuralChunker()
    el = _make_el("e1", "paragraph", "")
    text, start, end = c._element_text_with_span(el)
    assert text == ""


def test_element_text_with_span_whitespace_only_returns_empty():
    from app.chunkers.structural import StructuralChunker
    c = StructuralChunker()
    el = _make_el("e1", "paragraph", "   \n\t  ")
    text, start, end = c._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_strips_content():
    from app.chunkers.structural import StructuralChunker
    c = StructuralChunker()
    el = _make_el("e1", "paragraph", "  hello  ")
    text, start, end = c._element_text_with_span(el)
    assert text == "hello"
    assert start == 2  # lstrip 长度
    assert end == 7  # start + len("hello")


def test_element_text_with_span_no_strip_needed():
    from app.chunkers.structural import StructuralChunker
    c = StructuralChunker()
    el = _make_el("e1", "paragraph", "hello")
    text, start, end = c._element_text_with_span(el)
    assert text == "hello"
    assert start == 0
    assert end == 5


def test_element_text_with_span_leading_only():
    from app.chunkers.structural import StructuralChunker
    c = StructuralChunker()
    el = _make_el("e1", "paragraph", "   hello")
    text, start, end = c._element_text_with_span(el)
    assert text == "hello"
    assert start == 3
    assert end == 8


def test_element_text_with_span_trailing_only():
    from app.chunkers.structural import StructuralChunker
    c = StructuralChunker()
    el = _make_el("e1", "paragraph", "hello   ")
    text, start, end = c._element_text_with_span(el)
    assert text == "hello"
    assert start == 0
    assert end == 5


def test_element_text_legacy_method_returns_text():
    from app.chunkers.structural import StructuralChunker
    c = StructuralChunker()
    el = _make_el("e1", "paragraph", "hello")
    assert c._element_text(el) == "hello"


# =========================================================================
# 模块结构 / __all__
# =========================================================================


def test_module_all_exact():
    import app.chunkers.structural as mod
    assert mod.__all__ == ["StructuralChunker", "normalize_text"]


def test_module_all_no_duplicates():
    import app.chunkers.structural as mod
    assert len(mod.__all__) == len(set(mod.__all__))


def test_module_imports_re():
    import app.chunkers.structural as mod
    src = inspect.getsource(mod)
    assert "import re" in src


def test_module_imports_dataclass_field():
    import app.chunkers.structural as mod
    src = inspect.getsource(mod)
    assert "from dataclasses import dataclass, field" in src


def test_module_imports_any():
    import app.chunkers.structural as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_models():
    import app.chunkers.structural as mod
    src = inspect.getsource(mod)
    assert "from app.models import Chunk, Document, Element" in src


def test_module_uses_future_annotations():
    import app.chunkers.structural as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import app.chunkers.structural as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_heading_boundary():
    """docstring 提及 heading 硬边界。"""
    import app.chunkers.structural as mod
    doc = mod.__doc__
    assert "heading" in doc.lower() or "标题" in doc


def test_module_docstring_mentions_source_spans():
    import app.chunkers.structural as mod
    doc = mod.__doc__
    assert "source_spans" in doc or "spans" in doc.lower()


def test_module_docstring_mentions_no_text_modification():
    """docstring 提及"不修改文本"。"""
    import app.chunkers.structural as mod
    doc = mod.__doc__
    assert "不修改" in doc or "不丢不重" in doc


def test_module_no_silence_unused():
    import app.chunkers.structural as mod
    assert not hasattr(mod, "_silence_unused")


# =========================================================================
# normalize_text 边界
# =========================================================================


def test_normalize_text_empty_returns_empty():
    assert normalize_text("") == ""


def test_normalize_text_none_returns_empty():
    assert normalize_text(None) == ""  # type: ignore[arg-type]


def test_normalize_text_no_whitespace_returns_unchanged():
    assert normalize_text("hello") == "hello"


def test_normalize_text_collapses_whitespace():
    assert normalize_text("hello   world") == "hello world"


def test_normalize_text_collapses_newlines():
    assert normalize_text("hello\nworld") == "hello world"


def test_normalize_text_collapses_tabs():
    assert normalize_text("hello\tworld") == "hello world"


def test_normalize_text_strips_leading_trailing():
    assert normalize_text("  hello  ") == "hello"


def test_normalize_text_mixed_whitespace():
    assert normalize_text("a\nb\tc  d\re") == "a b c d e"


def test_normalize_text_only_whitespace_returns_empty():
    assert normalize_text("   \n\t\r  ") == ""


def test_normalize_text_returns_str():
    assert isinstance(normalize_text("x"), str)


# =========================================================================
# 综合行为
# =========================================================================


def test_normalize_text_idempotent():
    s = "hello   world\nfoo\tbar"
    once = normalize_text(s)
    twice = normalize_text(once)
    assert once == twice


def test_split_piece_immutable_after_construction():
    p = _SplitPiece(text="x", boundary_after="whitespace", start=0, end=1)
    with pytest.raises(FrozenInstanceError):
        p.text = "y"
    with pytest.raises(FrozenInstanceError):
        p.start = 100


def test_chunk_buffer_idempotent_flush_then_flush_returns_none():
    """flush 后 parts 清空，再 flush 返回 None。"""
    buf = _ChunkBuffer(document_id="d")
    buf.push_text("x", "e1", 0, 1)
    first = buf.flush(strategy="x", max_chars=800)
    second = buf.flush(strategy="x", max_chars=800)
    assert first is not None
    assert second is None


def test_hard_split_does_not_lose_text():
    """hard split 后所有 piece.text 拼接（用空格）后规范化 == 输入规范化。"""
    text = "aaaaa bbbbb ccccc ddddd eeeee"
    pieces = _hard_split_with_whitespace_fallback(text, 10)
    joined = " ".join(p.text for p in pieces)
    assert normalize_text(joined) == normalize_text(text)


def test_module_constants_present():
    import app.chunkers.structural as mod
    assert hasattr(mod, "_SENTENCE_SPLIT_RE")
    assert hasattr(mod, "_WHITESPACE_RE")
    assert hasattr(mod, "_HARD_BREAK_LANGS")
    assert hasattr(mod, "_PART_TEXT")
    assert hasattr(mod, "_PART_ELEMENT_ID")
    assert hasattr(mod, "_PART_START")
    assert hasattr(mod, "_PART_END")
