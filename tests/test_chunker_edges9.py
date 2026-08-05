r"""app/chunkers/structural.py 边角测试 - 第九轮（Round 204）。

补强已有 base/edges/edges2-8（共 ~1044 测试）未覆盖的深度：
- _WHITESPACE_RE 行为：vertical tab/form feed/全角空格
- normalize_text 边界：None/单字符/Unicode 各类空白
- _HARD_BREAK_LANGS 元组精确值
- _split_long_text 边界：len == max_chars / max_chars+1 / max_chars+2 精确 piece 数
- _hard_split_with_whitespace_fallback 边界：window 起止 / forced_char 路径 / 多 piece 累积
- StructuralChunker __init__ ValueError（max_chars < 32 / 负数 / 0 / 31）
- chunk() 综合行为：空 document / 单 heading / 多 chunk 计数器递增
- _element_text_with_span：leading/trailing whitespace / 多行 content / image element
- _element_text 兼容旧接口
- _SplitPiece frozen dataclass / 默认值
- _ChunkBuffer push_text/length/flush/counter
- 模块 __all__ / 类属性 / 签名
"""

from __future__ import annotations

import copy
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
    StructuralChunker,
    normalize_text,
)
from app.models import Chunk, Document, Element


# =========================================================================
# _WHITESPACE_RE 深度
# =========================================================================


def test_whitespace_re_pattern_string():
    assert _WHITESPACE_RE.pattern == r"\s+"


def test_whitespace_re_compiled_type():
    assert isinstance(_WHITESPACE_RE, re.Pattern)


def test_whitespace_re_sub_normalizes_vertical_tab():
    assert _WHITESPACE_RE.sub(" ", "a\x0bb") == "a b"


def test_whitespace_re_sub_normalizes_form_feed():
    assert _WHITESPACE_RE.sub(" ", "a\x0cb") == "a b"


def test_whitespace_re_sub_normalizes_multiple_mixed_whitespace():
    assert _WHITESPACE_RE.sub(" ", "a \t\n\x0b\x0c\rb") == "a b"


def test_whitespace_re_sub_preserves_non_whitespace():
    assert _WHITESPACE_RE.sub(" ", "abc") == "abc"


def test_whitespace_re_sub_leading_trailing_whitespace_kept():
    """单独 sub 不 strip；strip 由 normalize_text 做。"""
    assert _WHITESPACE_RE.sub(" ", "  abc  ") == " abc "


def test_whitespace_re_sub_full_width_space_in_pattern():
    r"""全角空格 U+3000 是否被 \s 匹配？Python re \s 在 Unicode 模式下匹配。"""
    # re 默认 Unicode 模式 → \s 包含 U+3000
    result = _WHITESPACE_RE.sub(" ", "a　b")
    assert result == "a b"


def test_whitespace_re_sub_only_whitespace_to_single_space():
    assert _WHITESPACE_RE.sub(" ", "   \t\n  ") == " "


# =========================================================================
# normalize_text 深度
# =========================================================================


def test_normalize_text_empty_string():
    assert normalize_text("") == ""


def test_normalize_text_only_whitespace_returns_empty():
    assert normalize_text("   \t\n  ") == ""


def test_normalize_text_single_char():
    assert normalize_text("a") == "a"


def test_normalize_text_strips_leading_whitespace():
    assert normalize_text("  abc") == "abc"


def test_normalize_text_strips_trailing_whitespace():
    assert normalize_text("abc  ") == "abc"


def test_normalize_text_strips_both_ends():
    assert normalize_text("  abc  ") == "abc"


def test_normalize_text_compresses_internal_whitespace():
    assert normalize_text("a    b") == "a b"


def test_normalize_text_compresses_mixed_whitespace():
    assert normalize_text("a \t\n b") == "a b"


def test_normalize_text_handles_newlines():
    assert normalize_text("line1\nline2") == "line1 line2"


def test_normalize_text_handles_tabs():
    assert normalize_text("a\tb") == "a b"


def test_normalize_text_preserves_punctuation():
    assert normalize_text("hello, world!") == "hello, world!"


def test_normalize_text_preserves_unicode():
    assert normalize_text("中文 文本") == "中文 文本"


def test_normalize_text_returns_str_type():
    assert isinstance(normalize_text("x"), str)


def test_normalize_text_signature():
    sig = inspect.signature(normalize_text)
    params = list(sig.parameters)
    assert params == ["s"]
    # from __future__ import annotations → return annotation is string
    assert sig.return_annotation == "str"


def test_normalize_text_does_not_modify_input():
    s = "  hello   world  "
    snapshot = s
    normalize_text(s)
    assert s == snapshot


# =========================================================================
# _HARD_BREAK_LANGS 深度
# =========================================================================


def test_hard_break_langs_is_tuple():
    assert isinstance(_HARD_BREAK_LANGS, tuple)


def test_hard_break_langs_six_elements():
    assert len(_HARD_BREAK_LANGS) == 6


def test_hard_break_langs_contains_chinese_marks():
    assert "。" in _HARD_BREAK_LANGS
    assert "！" in _HARD_BREAK_LANGS
    assert "？" in _HARD_BREAK_LANGS


def test_hard_break_langs_contains_english_marks():
    assert "." in _HARD_BREAK_LANGS
    assert "!" in _HARD_BREAK_LANGS
    assert "?" in _HARD_BREAK_LANGS


def test_hard_break_langs_no_duplicates():
    assert len(_HARD_BREAK_LANGS) == len(set(_HARD_BREAK_LANGS))


# =========================================================================
# _SENTENCE_SPLIT_RE 深度
# =========================================================================


def test_sentence_split_re_pattern_string():
    assert _SENTENCE_SPLIT_RE.pattern == r"(?<=[。！？!?\.])\s+"


def test_sentence_split_re_compiled_type():
    assert isinstance(_SENTENCE_SPLIT_RE, re.Pattern)


def test_sentence_split_re_lookbehind_no_capture():
    """lookbehind 不消耗标点。"""
    parts = _SENTENCE_SPLIT_RE.split("hello. world")
    # 标点留在前一段
    assert parts[0] == "hello."
    assert parts[1] == "world"


def test_sentence_split_re_multiple_sentences():
    parts = _SENTENCE_SPLIT_RE.split("a. b. c.")
    assert parts == ["a.", "b.", "c."]


def test_sentence_split_re_no_split_no_whitespace():
    parts = _SENTENCE_SPLIT_RE.split("a.b")
    assert parts == ["a.b"]


def test_sentence_split_re_no_split_without_punctuation():
    parts = _SENTENCE_SPLIT_RE.split("a b c")
    assert parts == ["a b c"]


def test_sentence_split_re_chinese_punctuation():
    parts = _SENTENCE_SPLIT_RE.split("你好。世界")
    # 中文标点后无空白 → 不分
    assert parts == ["你好。世界"]


def test_sentence_split_re_chinese_with_space():
    parts = _SENTENCE_SPLIT_RE.split("你好。 世界")
    assert parts == ["你好。", "世界"]


# =========================================================================
# _SplitPiece 深度
# =========================================================================


def test_split_piece_is_dataclass():
    assert is_dataclass(_SplitPiece) is True


def test_split_piece_is_frozen():
    p = _SplitPiece(text="x", boundary_after=None)
    with pytest.raises(FrozenInstanceError):
        p.text = "y"  # type: ignore[misc]


def test_split_piece_field_count():
    assert len(fields(_SplitPiece)) == 4


def test_split_piece_fields_names():
    names = [f.name for f in fields(_SplitPiece)]
    assert names == ["text", "boundary_after", "start", "end"]


def test_split_piece_text_no_default():
    """text 是必填。"""
    sig = inspect.signature(_SplitPiece)
    assert sig.parameters["text"].default is inspect.Parameter.empty


def test_split_piece_boundary_after_no_default():
    sig = inspect.signature(_SplitPiece)
    assert sig.parameters["boundary_after"].default is inspect.Parameter.empty


def test_split_piece_start_default_zero():
    sig = inspect.signature(_SplitPiece)
    assert sig.parameters["start"].default == 0


def test_split_piece_end_default_zero():
    sig = inspect.signature(_SplitPiece)
    assert sig.parameters["end"].default == 0


def test_split_piece_equality():
    a = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    b = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    assert a == b


def test_split_piece_inequality_on_text():
    a = _SplitPiece(text="x", boundary_after=None)
    b = _SplitPiece(text="y", boundary_after=None)
    assert a != b


def test_split_piece_inequality_on_start():
    a = _SplitPiece(text="x", boundary_after=None, start=0)
    b = _SplitPiece(text="x", boundary_after=None, start=1)
    assert a != b


def test_split_piece_hashable():
    p = _SplitPiece(text="x", boundary_after=None)
    assert hash(p) is not None


# =========================================================================
# _hard_split_with_whitespace_fallback 深度
# =========================================================================


def test_hard_split_at_exactly_max_chars_returns_one_piece():
    """len(text) == max_chars → 一 piece，boundary_after=None。"""
    text = "a" * 100
    pieces = _hard_split_with_whitespace_fallback(text, 100)
    assert len(pieces) == 1
    assert pieces[0].text == text
    assert pieces[0].boundary_after is None


def test_hard_split_at_max_chars_plus_one():
    """len(text) == max_chars + 1 → 必须切。"""
    text = "a" * 101
    pieces = _hard_split_with_whitespace_fallback(text, 100)
    assert len(pieces) >= 2


def test_hard_split_forced_char_when_no_whitespace():
    text = "a" * 200
    pieces = _hard_split_with_whitespace_fallback(text, 100)
    # 全是字母 → forced_char 切
    assert all(p.boundary_after in ("forced_char", None) for p in pieces)
    # 最后一个 boundary_after=None
    assert pieces[-1].boundary_after is None
    # 中间都是 forced_char
    assert all(p.boundary_after == "forced_char" for p in pieces[:-1])


def test_hard_split_whitespace_at_exact_max():
    """正好在 upper 处有空白 → 在 upper 切。"""
    text = "a" * 99 + " " + "b" * 50  # 150 chars
    pieces = _hard_split_with_whitespace_fallback(text, 100)
    # 至少 2 个 piece
    assert len(pieces) >= 2
    # 第一个 piece 应是 99 个 a
    assert pieces[0].text == "a" * 99
    assert pieces[0].boundary_after == "whitespace"


def test_hard_split_leading_whitespace_skipped():
    text = "   " + "a" * 100
    pieces = _hard_split_with_whitespace_fallback(text, 50)
    # 第一个 piece 不应含前导空白
    for p in pieces:
        assert not p.text.startswith(" ")


def test_hard_split_trailing_whitespace_in_natural_end():
    """自然尾段的 rstrip → boundary_after=None。"""
    text = "a" * 50 + "   "
    pieces = _hard_split_with_whitespace_fallback(text, 100)
    assert len(pieces) == 1
    assert pieces[0].text == "a" * 50
    assert pieces[0].boundary_after is None


def test_hard_split_consecutive_whitespace_in_input():
    """文本中间多个连续空白 → ws_idx 切在空白处，跳过所有连续空白。"""
    text = "a" * 50 + "   \n\t  " + "b" * 50  # 50 + 8 + 50 = 108
    pieces = _hard_split_with_whitespace_fallback(text, 100)
    # 第一轮 lower=50, upper=100，[50..100] 找到 ws 在位置 50-57
    # ws_idx=57（最后一个空白），text[0:57] = 50 a + 7 空白 → rstrip "a"*50
    # next_i=58，has_more=True → boundary_after="whitespace"
    # 第二轮 i=58, remaining=50 ≤ 100 → 单 piece "b"*50
    assert len(pieces) == 2
    assert pieces[0].text == "a" * 50
    assert pieces[0].boundary_after == "whitespace"
    assert pieces[1].text == "b" * 50
    assert pieces[1].boundary_after is None


def test_hard_split_window_lower_is_half_max():
    """窗口起点 lower = i + max_chars//2。max_chars=100 → lower=50。"""
    # 构造 51 字符 + 50 空白 + 50 字符
    # max_chars=100，第一轮 i=0, remaining=151, lower=50, upper=100
    # [50..100] 找空白：位置 51-99 都是空白 → ws_idx=99
    text = "a" * 51 + " " * 49 + "b" * 50
    pieces = _hard_split_with_whitespace_fallback(text, 100)
    assert len(pieces) >= 2
    # 第一个 piece 应是 51 个 a
    assert pieces[0].text == "a" * 51


def test_hard_split_signature():
    sig = inspect.signature(_hard_split_with_whitespace_fallback)
    params = list(sig.parameters)
    assert params == ["text", "max_chars"]


def test_hard_split_returns_list_of_split_pieces():
    pieces = _hard_split_with_whitespace_fallback("hello world " * 50, 100)
    assert isinstance(pieces, list)
    for p in pieces:
        assert isinstance(p, _SplitPiece)


# =========================================================================
# _split_long_text 深度
# =========================================================================


def test_split_long_text_at_max_chars_no_split():
    """len(text) == max_chars → 一 piece。"""
    text = "a" * 100
    pieces = _split_long_text(text, 100)
    assert len(pieces) == 1
    assert pieces[0].text == text
    assert pieces[0].boundary_after is None


def test_split_long_text_at_max_chars_plus_one_splits():
    text = "a" * 101
    pieces = _split_long_text(text, 100)
    assert len(pieces) >= 2


def test_split_long_text_strip_then_single():
    """strip 后 len ≤ max_chars → 单 piece。"""
    text = "  " + "a" * 100 + "  "
    pieces = _split_long_text(text, 100)
    assert len(pieces) == 1
    assert pieces[0].text == "a" * 100


def test_split_long_text_empty_returns_empty_list():
    assert _split_long_text("", 100) == []


def test_split_long_text_only_whitespace_returns_empty_list():
    assert _split_long_text("   \t\n  ", 100) == []


def test_split_long_text_returns_pieces_type():
    pieces = _split_long_text("hello", 100)
    assert isinstance(pieces, list)
    assert all(isinstance(p, _SplitPiece) for p in pieces)


def test_split_long_text_signature():
    sig = inspect.signature(_split_long_text)
    params = list(sig.parameters)
    assert params == ["text", "max_chars"]


def test_split_long_text_offsets_in_stripped_coords():
    """start/end 在 stripped text 坐标系。"""
    text = "  hello world  "
    pieces = _split_long_text(text, 100)
    assert len(pieces) == 1
    # stripped text = "hello world" (11 chars)
    assert pieces[0].start == 0
    assert pieces[0].end == 11


def test_split_long_text_concatenation_preserves_all_text():
    """split → join 不丢字符（用单空格 joiner）。"""
    text = "Sentence one. " * 30  # 多个句子
    pieces = _split_long_text(text, 100)
    rejoined = " ".join(p.text for p in pieces)
    # normalize 后应等
    assert normalize_text(rejoined) == normalize_text(text)


def test_split_long_text_each_piece_within_max_chars():
    text = "a" * 1000
    pieces = _split_long_text(text, 100)
    for p in pieces:
        assert len(p.text) <= 100


def test_split_long_text_mixed_sentences_and_forced():
    text = "Short. " + "a" * 200 + ". End."
    pieces = _split_long_text(text, 100)
    # 至少 3 piece
    assert len(pieces) >= 3


# =========================================================================
# _PART_* 常量
# =========================================================================


def test_part_text_constant_value():
    assert _PART_TEXT == 0


def test_part_element_id_constant_value():
    assert _PART_ELEMENT_ID == 1


def test_part_start_constant_value():
    assert _PART_START == 2


def test_part_end_constant_value():
    assert _PART_END == 3


def test_part_constants_unique():
    values = {_PART_TEXT, _PART_ELEMENT_ID, _PART_START, _PART_END}
    assert len(values) == 4


def test_part_constants_form_sequential_indices():
    """PART_TEXT=0, ELEMENT_ID=1, START=2, END=3 → 元组顺序索引。"""
    assert _PART_TEXT < _PART_ELEMENT_ID < _PART_START < _PART_END


# =========================================================================
# _ChunkBuffer 深度
# =========================================================================


def test_chunk_buffer_is_dataclass():
    assert is_dataclass(_ChunkBuffer) is True


def test_chunk_buffer_field_count():
    assert len(fields(_ChunkBuffer)) == 3


def test_chunk_buffer_field_names():
    names = [f.name for f in fields(_ChunkBuffer)]
    assert names == ["document_id", "parts", "counter"]


def test_chunk_buffer_document_id_no_default():
    sig = inspect.signature(_ChunkBuffer)
    assert sig.parameters["document_id"].default is inspect.Parameter.empty


def test_chunk_buffer_parts_default_factory_list():
    sig = inspect.signature(_ChunkBuffer)
    # default_factory 在 signature 中表现不同，但 parts 默认空 list
    buf = _ChunkBuffer(document_id="d")
    assert buf.parts == []


def test_chunk_buffer_counter_default_zero():
    buf = _ChunkBuffer(document_id="d")
    assert buf.counter == 0


def test_chunk_buffer_parts_independent_per_instance():
    b1 = _ChunkBuffer(document_id="d1")
    b2 = _ChunkBuffer(document_id="d2")
    b1.push_text("a", "e1", 0, 1)
    assert b1.parts != b2.parts
    assert b2.parts == []


def test_chunk_buffer_push_text_appends():
    buf = _ChunkBuffer(document_id="d")
    buf.push_text("hello", "e1", 0, 5)
    assert len(buf.parts) == 1
    assert buf.parts[0] == ("hello", "e1", 0, 5)


def test_chunk_buffer_push_text_multiple():
    buf = _ChunkBuffer(document_id="d")
    buf.push_text("a", "e1", 0, 1)
    buf.push_text("b", "e1", 1, 2)
    buf.push_text("c", "e2", 0, 1)
    assert len(buf.parts) == 3


def test_chunk_buffer_length_sums_text_lengths():
    buf = _ChunkBuffer(document_id="d")
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e2", 0, 5)
    assert buf.length() == 10


def test_chunk_buffer_length_empty_returns_zero():
    buf = _ChunkBuffer(document_id="d")
    assert buf.length() == 0


def test_chunk_buffer_is_empty_true_initially():
    buf = _ChunkBuffer(document_id="d")
    assert buf.is_empty() is True


def test_chunk_buffer_is_empty_false_after_push():
    buf = _ChunkBuffer(document_id="d")
    buf.push_text("a", "e1", 0, 1)
    assert buf.is_empty() is False


def test_chunk_buffer_flush_empty_returns_none():
    buf = _ChunkBuffer(document_id="d")
    assert buf.flush(strategy="x", max_chars=800) is None


def test_chunk_buffer_flush_only_whitespace_returns_none():
    buf = _ChunkBuffer(document_id="d")
    buf.push_text("   ", "e1", 0, 3)
    assert buf.flush(strategy="x", max_chars=800) is None


def test_chunk_buffer_flush_returns_chunk():
    buf = _ChunkBuffer(document_id="d", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    result = buf.flush(strategy="seq", max_chars=800)
    assert isinstance(result, Chunk)


def test_chunk_buffer_flush_clears_parts():
    buf = _ChunkBuffer(document_id="d", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    buf.flush(strategy="seq", max_chars=800)
    assert buf.parts == []
    assert buf.is_empty() is True


def test_chunk_buffer_flush_dedups_source_ids():
    buf = _ChunkBuffer(document_id="d", counter=0)
    buf.push_text("a", "e1", 0, 1)
    buf.push_text("b", "e1", 1, 2)
    buf.push_text("c", "e2", 0, 1)
    chunk = buf.flush(strategy="x", max_chars=800)
    assert chunk is not None
    assert chunk.source_element_ids == ["e1", "e2"]


def test_chunk_buffer_flush_one_span_per_part():
    buf = _ChunkBuffer(document_id="d", counter=0)
    buf.push_text("a", "e1", 0, 1)
    buf.push_text("b", "e1", 1, 2)
    buf.push_text("c", "e2", 0, 1)
    chunk = buf.flush(strategy="x", max_chars=800)
    assert chunk is not None
    assert len(chunk.source_spans) == 3


def test_chunk_buffer_flush_text_joins_with_single_space():
    buf = _ChunkBuffer(document_id="d", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e1", 5, 10)
    chunk = buf.flush(strategy="x", max_chars=800)
    assert chunk is not None
    assert chunk.text == "hello world"


def test_chunk_buffer_flush_metadata_has_strategy_max_chars_char_count():
    buf = _ChunkBuffer(document_id="d", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    chunk = buf.flush(strategy="seq", max_chars=800)
    assert chunk is not None
    assert chunk.metadata["strategy"] == "seq"
    assert chunk.metadata["max_chars"] == 800
    assert chunk.metadata["char_count"] == 5


def test_chunk_buffer_flush_chunk_id_uses_document_id_and_counter():
    buf = _ChunkBuffer(document_id="doc-1", counter=42)
    buf.push_text("x", "e1", 0, 1)
    chunk = buf.flush(strategy="x", max_chars=800)
    assert chunk is not None
    assert chunk.chunk_id == "doc-1::c0042"


def test_chunk_buffer_flush_strategy_keyword_only():
    sig = inspect.signature(_ChunkBuffer.flush)
    assert sig.parameters["strategy"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_chunk_buffer_init_signature():
    sig = inspect.signature(_ChunkBuffer)
    params = list(sig.parameters)
    assert params == ["document_id", "parts", "counter"]


# =========================================================================
# StructuralChunker.__init__ 深度
# =========================================================================


def test_chunker_init_default_max_chars():
    c = StructuralChunker()
    assert c.max_chars == 800


def test_chunker_init_explicit_max_chars():
    c = StructuralChunker(max_chars=200)
    assert c.max_chars == 200


def test_chunker_init_max_chars_below_32_raises():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=31)


def test_chunker_init_max_chars_exactly_32_ok():
    c = StructuralChunker(max_chars=32)
    assert c.max_chars == 32


def test_chunker_init_max_chars_zero_raises():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=0)


def test_chunker_init_max_chars_negative_raises():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=-1)


def test_chunker_init_max_chars_one_raises():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=1)


def test_chunker_init_error_message_contains_value():
    with pytest.raises(ValueError) as ei:
        StructuralChunker(max_chars=10)
    assert "10" in str(ei.value)


def test_chunker_init_signature():
    sig = inspect.signature(StructuralChunker.__init__)
    params = list(sig.parameters)
    assert params == ["self", "max_chars"]
    assert sig.parameters["max_chars"].default == 800


# =========================================================================
# StructuralChunker.chunk() 综合行为
# =========================================================================


def _make_doc(elements: list[Element], document_id: str = "doc1") -> Document:
    return Document(
        document_id=document_id,
        source_path="/tmp/x.txt",
        source_type="text",
        source_hash="a" * 64,
        parser_name="text",
        parser_version="0.1.0",
        elements=elements,
    )


def _make_el(el_id: str, etype: str, content: str) -> Element:
    return Element(
        element_id=el_id, type=etype,
        source_locator={"line": 1}, content=content,
    )


def test_chunk_empty_document_returns_empty_list():
    chunker = StructuralChunker()
    doc = _make_doc([])
    assert chunker.chunk(doc) == []


def test_chunk_single_paragraph_within_max():
    chunker = StructuralChunker(max_chars=800)
    doc = _make_doc([_make_el("e1", "paragraph", "hello world")])
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].text == "hello world"


def test_chunk_single_paragraph_exactly_max():
    chunker = StructuralChunker(max_chars=100)
    doc = _make_doc([_make_el("e1", "paragraph", "a" * 100)])
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1


def test_chunk_chunk_id_zero_padded_4_digits():
    chunker = StructuralChunker(max_chars=800)
    doc = _make_doc([_make_el("e1", "paragraph", "hello")])
    chunks = chunker.chunk(doc)
    assert chunks[0].chunk_id == "doc1::c0000"


def test_chunk_chunk_id_increments():
    chunker = StructuralChunker(max_chars=32)
    elements = [_make_el(f"e{i}", "paragraph", f"some-paragraph-text-{i:02d}") for i in range(5)]
    doc = _make_doc(elements)
    chunks = chunker.chunk(doc)
    assert len(chunks) >= 2
    for idx, chunk in enumerate(chunks):
        assert chunk.chunk_id.endswith(f"c{idx:04d}")


def test_chunk_heading_triggers_flush():
    chunker = StructuralChunker(max_chars=800)
    elements = [
        _make_el("e1", "paragraph", "para before"),
        _make_el("e2", "heading", "Title"),
        _make_el("e3", "paragraph", "para after"),
    ]
    doc = _make_doc(elements)
    chunks = chunker.chunk(doc)
    # 至少 2 块：第一块含 e1（封口），第二块含 e2 + e3
    assert len(chunks) >= 2


def test_chunk_heading_first_element_no_prior_buf():
    chunker = StructuralChunker(max_chars=800)
    elements = [
        _make_el("e1", "heading", "Title"),
        _make_el("e2", "paragraph", "body"),
    ]
    doc = _make_doc(elements)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1
    # heading 进入 buf，body 累积
    assert chunks[0].text == "Title body"


def test_chunk_table_isolated():
    chunker = StructuralChunker(max_chars=800)
    elements = [
        _make_el("e1", "paragraph", "before"),
        _make_el("e2", "table", "| a | b |"),
        _make_el("e3", "paragraph", "after"),
    ]
    doc = _make_doc(elements)
    chunks = chunker.chunk(doc)
    types_in_strategy = [c.metadata.get("strategy") for c in chunks]
    assert "isolated_table" in types_in_strategy


def test_chunk_image_isolated_with_zero_span():
    """image element → _element_text_with_span 返回 ('', 0, 0)，跳过。"""
    chunker = StructuralChunker(max_chars=800)
    img = Element(
        element_id="i1", type="image",
        source_locator={"page": 1}, resource_path="img.png",
    )
    doc = _make_doc([img])
    chunks = chunker.chunk(doc)
    assert chunks == []


def test_chunk_caption_isolated():
    chunker = StructuralChunker(max_chars=800)
    elements = [
        _make_el("e1", "caption", "Figure 1"),
    ]
    doc = _make_doc(elements)
    chunks = chunker.chunk(doc)
    assert chunks[0].metadata["strategy"] == "isolated_caption"


def test_chunk_long_paragraph_sentence_split():
    chunker = StructuralChunker(max_chars=50)
    text = "Short one. " + "a" * 100 + ". End."
    elements = [_make_el("e1", "paragraph", text)]
    doc = _make_doc(elements)
    chunks = chunker.chunk(doc)
    assert len(chunks) >= 2
    # 第一个 chunk 是 short
    assert chunks[0].metadata["strategy"] in ("long_paragraph_sentence_split", "sequential")


def test_chunk_accumulated_overflow_flush():
    """多个短 paragraph 累积超 max_chars → flush。"""
    chunker = StructuralChunker(max_chars=32)
    # 每段 8 字符 + joiner 1 = 9 字符，max_chars=32 容纳 3 段（27 字符），
    # 第 4 段 projected=27+1+8=36 > 32 → flush
    elements = [_make_el(f"e{i}", "paragraph", f"wordxy{i:02d}") for i in range(10)]
    doc = _make_doc(elements)
    chunks = chunker.chunk(doc)
    assert len(chunks) >= 3


def test_chunk_source_spans_filled_for_sequential():
    chunker = StructuralChunker(max_chars=800)
    elements = [_make_el("e1", "paragraph", "hello")]
    doc = _make_doc(elements)
    chunks = chunker.chunk(doc)
    assert len(chunks[0].source_spans) == 1
    assert chunks[0].source_spans[0]["element_id"] == "e1"


def test_chunk_source_spans_filled_for_long_paragraph():
    chunker = StructuralChunker(max_chars=50)
    elements = [_make_el("e1", "paragraph", "a" * 200)]
    doc = _make_doc(elements)
    chunks = chunker.chunk(doc)
    for c in chunks:
        for span in c.source_spans:
            assert span["element_id"] == "e1"


def test_chunk_does_not_mutate_document_elements():
    chunker = StructuralChunker(max_chars=800)
    elements = [_make_el("e1", "paragraph", "hello")]
    doc = _make_doc(elements)
    snapshot = copy.deepcopy(doc.elements)
    chunker.chunk(doc)
    assert doc.elements == snapshot


def test_chunk_text_preservation_normalize():
    """不丢不重：sum(chunk.text) normalize 后 == elements content normalize 后。"""
    chunker = StructuralChunker(max_chars=50)
    elements = [
        _make_el("e1", "paragraph", "hello world " * 20),
        _make_el("e2", "heading", "Title"),
        _make_el("e3", "paragraph", "another para here"),
    ]
    doc = _make_doc(elements)
    chunks = chunker.chunk(doc)
    input_text = " ".join(e.content or "" for e in elements)
    output_text = " ".join(c.text for c in chunks)
    assert normalize_text(input_text) == normalize_text(output_text)


# =========================================================================
# _element_text_with_span 深度
# =========================================================================


def test_element_text_with_span_basic():
    chunker = StructuralChunker()
    el = _make_el("e1", "paragraph", "hello")
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 0
    assert end == 5


def test_element_text_with_span_strips_leading():
    chunker = StructuralChunker()
    el = _make_el("e1", "paragraph", "  hello")
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 2
    assert end == 7


def test_element_text_with_span_strips_trailing():
    chunker = StructuralChunker()
    el = _make_el("e1", "paragraph", "hello  ")
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 0
    assert end == 5


def test_element_text_with_span_strips_both():
    chunker = StructuralChunker()
    el = _make_el("e1", "paragraph", "  hello  ")
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 2
    assert end == 7


def test_element_text_with_span_only_whitespace_returns_empty():
    chunker = StructuralChunker()
    el = _make_el("e1", "paragraph", "   ")
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_none_content_returns_empty():
    chunker = StructuralChunker()
    el = Element(element_id="e1", type="image", source_locator={"page": 1}, resource_path="x.png")
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_image_returns_empty():
    chunker = StructuralChunker()
    el = Element(
        element_id="e1", type="image",
        source_locator={"page": 1}, content="should be ignored",
    )
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_multiline_content():
    chunker = StructuralChunker()
    el = _make_el("e1", "paragraph", "line1\nline2")
    text, start, end = chunker._element_text_with_span(el)
    # strip 不删 \n（仅 strip 两端空白）
    assert text == "line1\nline2"
    assert start == 0
    assert end == 11


def test_element_text_with_span_preserves_internal_whitespace():
    chunker = StructuralChunker()
    el = _make_el("e1", "paragraph", "  hello   world  ")
    text, start, end = chunker._element_text_with_span(el)
    # 仅 strip 两端，内部空白保留
    assert text == "hello   world"
    assert start == 2
    assert end == 15


# =========================================================================
# _element_text 兼容旧接口
# =========================================================================


def test_element_text_returns_only_text():
    chunker = StructuralChunker()
    el = _make_el("e1", "paragraph", "hello")
    assert chunker._element_text(el) == "hello"


def test_element_text_returns_empty_for_image():
    chunker = StructuralChunker()
    el = Element(element_id="i1", type="image", source_locator={"page": 1}, resource_path="x.png")
    assert chunker._element_text(el) == ""


def test_element_text_returns_empty_for_whitespace_only():
    chunker = StructuralChunker()
    el = _make_el("e1", "paragraph", "   ")
    assert chunker._element_text(el) == ""


def test_element_text_strips_outer_whitespace():
    chunker = StructuralChunker()
    el = _make_el("e1", "paragraph", "  hello  ")
    assert chunker._element_text(el) == "hello"


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import app.chunkers.structural as m
    assert set(m.__all__) == {"StructuralChunker", "normalize_text"}


def test_module_all_is_list():
    import app.chunkers.structural as m
    assert isinstance(m.__all__, list)


def test_module_all_no_duplicates():
    import app.chunkers.structural as m
    assert len(m.__all__) == len(set(m.__all__))


def test_module_imports_re():
    import app.chunkers.structural as m
    assert hasattr(m, "re")


def test_module_imports_dataclass():
    import app.chunkers.structural as m
    assert hasattr(m, "dataclass")
    assert hasattr(m, "field")


def test_module_imports_any():
    import app.chunkers.structural as m
    assert hasattr(m, "Any")


def test_module_imports_models():
    import app.chunkers.structural as m
    assert hasattr(m, "Chunk")
    assert hasattr(m, "Document")
    assert hasattr(m, "Element")


def test_module_docstring_present():
    import app.chunkers.structural as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_invariants():
    import app.chunkers.structural as m
    doc = m.__doc__
    assert "heading" in doc.lower() or "硬边界" in doc
    assert "max_chars" in doc or "长度上限" in doc
    assert "source_spans" in doc or "source_element_ids" in doc


def test_module_uses_future_annotations():
    import app.chunkers.structural as m
    sig = inspect.signature(m.StructuralChunker.chunk)
    assert isinstance(sig.return_annotation, str)


def test_module_chunk_method_signature():
    sig = inspect.signature(StructuralChunker.chunk)
    params = list(sig.parameters)
    assert params == ["self", "document"]


def test_module_all_entries_exported():
    import app.chunkers.structural as m
    for name in m.__all__:
        assert hasattr(m, name)


# =========================================================================
# 综合行为
# =========================================================================


def test_chunker_idempotent():
    chunker = StructuralChunker(max_chars=50)
    elements = [
        _make_el("e1", "heading", "Title"),
        _make_el("e2", "paragraph", "para one"),
        _make_el("e3", "paragraph", "para two"),
    ]
    doc = _make_doc(elements)
    chunks1 = chunker.chunk(doc)
    chunks2 = chunker.chunk(doc)
    assert len(chunks1) == len(chunks2)
    for c1, c2 in zip(chunks1, chunks2):
        assert c1.to_dict() == c2.to_dict()


def test_full_pipeline_with_mixed_element_types():
    chunker = StructuralChunker(max_chars=100)
    elements = [
        _make_el("e1", "heading", "Document Title"),
        _make_el("e2", "paragraph", "intro paragraph " * 10),
        _make_el("e3", "heading", "Section Two"),
        _make_el("e4", "paragraph", "second section content"),
        _make_el("e5", "table", "| col1 | col2 |"),
        _make_el("e6", "caption", "Figure caption"),
        _make_el("e7", "list_item", "first item"),
        _make_el("e8", "list_item", "second item"),
    ]
    doc = _make_doc(elements)
    chunks = chunker.chunk(doc)
    # 应有多个 chunk，包含 isolated_table 和 isolated_caption
    strategies = [c.metadata["strategy"] for c in chunks]
    assert "isolated_table" in strategies
    assert "isolated_caption" in strategies


def test_chunker_text_preservation_with_unicode_and_emoji():
    chunker = StructuralChunker(max_chars=50)
    elements = [
        _make_el("e1", "paragraph", "你好世界 🎉🎉🎉"),
        _make_el("e2", "heading", "标题"),
    ]
    doc = _make_doc(elements)
    chunks = chunker.chunk(doc)
    input_text = " ".join(e.content or "" for e in elements)
    output_text = " ".join(c.text for c in chunks)
    assert normalize_text(input_text) == normalize_text(output_text)
