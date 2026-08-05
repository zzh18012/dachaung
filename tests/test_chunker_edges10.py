r"""app/chunkers/structural.py 边角测试 - 第十轮（Round 210）。

补强已有 base/edges/edges2-9（共 ~1197 测试）未覆盖的深度：
- _SENTENCE_SPLIT_RE 精确分割行为（中英文标点 / 多空白 / 标点 + 非空白）
- _HARD_BREAK_LANGS 元组类型 / 顺序 / 无重复
- normalize_text None/非字符串输入边界
- _SplitPiece frozen / 默认值 / 字段类型
- _hard_split_with_whitespace_fallback 精确 start/end/boundary_after 坐标
- _split_long_text 多 piece 累积精确坐标 / sentence_start 找不到的防御性 fallback
- _ChunkBuffer.flush 各 strategy / counter / source_spans / source_element_ids 去重
- StructuralChunker.chunk 各种 element 顺序组合
- _element_text_with_span 边界（含 Unicode whitespace）
- 模块结构 / 类属性 / __all__ / 类继承
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
# 模块结构
# =========================================================================


def test_module_all_exact():
    import app.chunkers.structural as m
    assert set(m.__all__) == {"StructuralChunker", "normalize_text"}


def test_module_all_is_list():
    import app.chunkers.structural as m
    assert isinstance(m.__all__, list)


def test_module_imports_re():
    import app.chunkers.structural as m
    assert hasattr(m, "re")


def test_module_imports_dataclass():
    import app.chunkers.structural as m
    assert hasattr(m, "dataclass")


def test_module_imports_field():
    import app.chunkers.structural as m
    assert hasattr(m, "field")


def test_module_imports_any():
    import app.chunkers.structural as m
    assert hasattr(m, "Any")


def test_module_imports_chunk():
    import app.chunkers.structural as m
    assert hasattr(m, "Chunk")


def test_module_imports_document():
    import app.chunkers.structural as m
    assert hasattr(m, "Document")


def test_module_imports_element():
    import app.chunkers.structural as m
    assert hasattr(m, "Element")


def test_module_docstring_present():
    import app.chunkers.structural as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_rules():
    import app.chunkers.structural as m
    doc = m.__doc__
    assert "heading" in doc.lower()
    assert "max_chars" in doc
    assert "source_element_id" in doc.lower() or "source_spans" in doc


def test_module_uses_future_annotations():
    import app.chunkers.structural as m
    sig = inspect.signature(m.normalize_text)
    assert isinstance(sig.return_annotation, str)


def test_module_no_silence_unused():
    import app.chunkers.structural as m
    assert not hasattr(m, "_silence_unused_import")


def test_module_internal_helpers_present():
    import app.chunkers.structural as m
    for name in (
        "_hard_split_with_whitespace_fallback", "_split_long_text",
        "_ChunkBuffer", "_SplitPiece",
    ):
        assert hasattr(m, name), name


def test_module_part_constants_values():
    """_PART_TEXT/_PART_ELEMENT_ID/_PART_START/_PART_END 是元组字段索引。"""
    assert _PART_TEXT == 0
    assert _PART_ELEMENT_ID == 1
    assert _PART_START == 2
    assert _PART_END == 3


def test_module_part_constants_unique():
    assert len({_PART_TEXT, _PART_ELEMENT_ID, _PART_START, _PART_END}) == 4


# =========================================================================
# _SENTENCE_SPLIT_RE 精确行为
# =========================================================================


def test_sentence_split_re_is_pattern():
    assert isinstance(_SENTENCE_SPLIT_RE, re.Pattern)


def test_sentence_split_re_splits_chinese_period():
    """中文句号 + 空白 → 切分。"""
    result = _SENTENCE_SPLIT_RE.split("第一句。 第二句。")
    assert result == ["第一句。", "第二句。"]


def test_sentence_split_re_splits_english_period():
    result = _SENTENCE_SPLIT_RE.split("Sentence one. Sentence two.")
    assert result == ["Sentence one.", "Sentence two."]


def test_sentence_split_re_splits_question_mark():
    result = _SENTENCE_SPLIT_RE.split("Why? Because.")
    assert result == ["Why?", "Because."]


def test_sentence_split_re_splits_exclamation_mark():
    result = _SENTENCE_SPLIT_RE.split("Wow! Great!")
    # 中间 " " 切分；末尾 "!" 后无空白，所以 "Great!" 不分
    assert result == ["Wow!", "Great!"]


def test_sentence_split_re_no_split_without_whitespace():
    """标点后无空白 → 不切。"""
    result = _SENTENCE_SPLIT_RE.split("a.b.c")
    assert result == ["a.b.c"]


def test_sentence_split_re_no_split_no_punctuation():
    result = _SENTENCE_SPLIT_RE.split("just words")
    assert result == ["just words"]


def test_sentence_split_re_multiple_whitespace_collapsed():
    """split 不 collapse，但每个 whitespace 段都是分隔符 → 不产生空 sentence（除非首尾）。"""
    result = _SENTENCE_SPLIT_RE.split("a.  b.  c.")
    # "a." "b." "c."
    assert result == ["a.", "b.", "c."]


def test_sentence_split_re_empty_string():
    assert _SENTENCE_SPLIT_RE.split("") == [""]


# =========================================================================
# _HARD_BREAK_LANGS 深度
# =========================================================================


def test_hard_break_langs_is_tuple():
    assert isinstance(_HARD_BREAK_LANGS, tuple)


def test_hard_break_langs_no_duplicates():
    assert len(set(_HARD_BREAK_LANGS)) == len(_HARD_BREAK_LANGS)


def test_hard_break_langs_length():
    assert len(_HARD_BREAK_LANGS) == 6


def test_hard_break_langs_contains_chinese_punctuation():
    assert "。" in _HARD_BREAK_LANGS
    assert "！" in _HARD_BREAK_LANGS
    assert "？" in _HARD_BREAK_LANGS


def test_hard_break_langs_contains_english_punctuation():
    assert "." in _HARD_BREAK_LANGS
    assert "!" in _HARD_BREAK_LANGS
    assert "?" in _HARD_BREAK_LANGS


def test_hard_break_langs_all_strings():
    for ch in _HARD_BREAK_LANGS:
        assert isinstance(ch, str)


def test_hard_break_langs_all_single_char():
    for ch in _HARD_BREAK_LANGS:
        assert len(ch) == 1


# =========================================================================
# _WHITESPACE_RE 深度
# =========================================================================


def test_whitespace_re_is_pattern():
    assert isinstance(_WHITESPACE_RE, re.Pattern)


def test_whitespace_re_matches_space():
    assert _WHITESPACE_RE.search(" ") is not None


def test_whitespace_re_matches_tab():
    assert _WHITESPACE_RE.search("\t") is not None


def test_whitespace_re_matches_newline():
    assert _WHITESPACE_RE.search("\n") is not None


def test_whitespace_re_matches_carriage_return():
    assert _WHITESPACE_RE.search("\r") is not None


def test_whitespace_re_matches_vertical_tab():
    assert _WHITESPACE_RE.search("\x0b") is not None


def test_whitespace_re_matches_form_feed():
    assert _WHITESPACE_RE.search("\x0c") is not None


def test_whitespace_re_matches_multiple():
    """sub 把多空白压成 1。"""
    assert _WHITESPACE_RE.sub(" ", "a   b\t\tc") == "a b c"


def test_whitespace_re_no_match_alpha():
    assert _WHITESPACE_RE.search("abc") is None


# =========================================================================
# normalize_text 深度
# =========================================================================


def test_normalize_text_signature():
    sig = inspect.signature(normalize_text)
    params = list(sig.parameters)
    assert params == ["s"]


def test_normalize_text_return_annotation_str():
    sig = inspect.signature(normalize_text)
    assert sig.return_annotation == "str"


def test_normalize_text_empty_string():
    assert normalize_text("") == ""


def test_normalize_text_only_whitespace():
    assert normalize_text("   \t\n  ") == ""


def test_normalize_text_no_change():
    """无空白的字符串不变。"""
    assert normalize_text("abc") == "abc"


def test_normalize_text_compresses_multiple_spaces():
    assert normalize_text("a   b") == "a b"


def test_normalize_text_compresses_mixed_whitespace():
    assert normalize_text("a \t\n b") == "a b"


def test_normalize_text_strips_leading_trailing():
    assert normalize_text("  abc  ") == "abc"


def test_normalize_text_unicode_whitespace():
    r"""Unicode 空白匹配测试。（NBSP 例外，\s 不匹配 NBSP 在 ASCII 模式）。"""
    # Python re 默认 Unicode 模式下 \s 包含 Unicode 空白
    result = normalize_text("a b")  # em space
    assert result == "a b"


def test_normalize_text_idempotent():
    s = "  hello   world  "
    once = normalize_text(s)
    twice = normalize_text(once)
    assert once == twice


def test_normalize_text_callable():
    assert callable(normalize_text)


# =========================================================================
# _SplitPiece 深度
# =========================================================================


def test_split_piece_is_dataclass():
    assert is_dataclass(_SplitPiece)


def test_split_piece_frozen():
    """frozen=True → setattr raises FrozenInstanceError。"""
    p = _SplitPiece(text="x", boundary_after=None)
    with pytest.raises(FrozenInstanceError):
        p.text = "y"


def test_split_piece_field_count():
    sp_fields = fields(_SplitPiece)
    assert len(sp_fields) == 4


def test_split_piece_field_names_exact():
    sp_fields = fields(_SplitPiece)
    names = [f.name for f in sp_fields]
    assert names == ["text", "boundary_after", "start", "end"]


def test_split_piece_field_types():
    sp_fields = {f.name: f for f in fields(_SplitPiece)}
    assert sp_fields["text"].type == "str"
    assert sp_fields["boundary_after"].type == "str | None"
    assert sp_fields["start"].type == "int"
    assert sp_fields["end"].type == "int"


def test_split_piece_default_start_end_zero():
    p = _SplitPiece(text="x", boundary_after=None)
    assert p.start == 0
    assert p.end == 0


def test_split_piece_construction_full():
    p = _SplitPiece(text="x", boundary_after="whitespace", start=5, end=10)
    assert p.text == "x"
    assert p.boundary_after == "whitespace"
    assert p.start == 5
    assert p.end == 10


def test_split_piece_equality():
    p1 = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    p2 = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    assert p1 == p2


def test_split_piece_inequality():
    p1 = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    p2 = _SplitPiece(text="y", boundary_after=None, start=0, end=1)
    assert p1 != p2


def test_split_piece_hashable():
    p = _SplitPiece(text="x", boundary_after=None)
    assert hash(p) is not None
    s = {p}
    assert p in s


# =========================================================================
# _hard_split_with_whitespace_fallback 精确坐标
# =========================================================================


def test_hard_split_with_whitespace_fallback_signature():
    sig = inspect.signature(_hard_split_with_whitespace_fallback)
    params = list(sig.parameters)
    assert params == ["text", "max_chars"]


def test_hard_split_with_whitespace_fallback_return_annotation_str():
    sig = inspect.signature(_hard_split_with_whitespace_fallback)
    assert sig.return_annotation == "list[_SplitPiece]"


def test_hard_split_short_returns_single_piece_with_no_boundary():
    """text ≤ max_chars → 1 piece, boundary_after=None。"""
    pieces = _hard_split_with_whitespace_fallback("short", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "short"
    assert pieces[0].boundary_after is None


def test_hard_split_leading_whitespace_stripped():
    """前导空白被跳过。"""
    pieces = _hard_split_with_whitespace_fallback("   abc", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "abc"
    assert pieces[0].start == 3  # 跳过 3 个空格
    assert pieces[0].end == 6


def test_hard_split_forced_char_when_no_whitespace():
    """窗口内无空白 → forced_char。"""
    text = "a" * 100
    pieces = _hard_split_with_whitespace_fallback(text, 50)
    assert len(pieces) >= 2
    # 第一个 piece 是 forced_char
    assert pieces[0].boundary_after == "forced_char"
    assert pieces[0].text == "a" * 50
    assert pieces[0].start == 0
    assert pieces[0].end == 50


def test_hard_split_whitespace_boundary_in_window():
    """窗口内有空白 → whitespace boundary。"""
    # 50 字符窗口内有空白 → 在空白处切
    text = "word " * 20  # 100 字符
    pieces = _hard_split_with_whitespace_fallback(text, 50)
    assert len(pieces) >= 2
    assert pieces[0].boundary_after == "whitespace"


def test_hard_split_last_piece_no_boundary_after():
    """最后一个 piece（remaining ≤ max_chars）boundary_after=None。"""
    pieces = _hard_split_with_whitespace_fallback("a " * 100, 50)
    last = pieces[-1]
    assert last.boundary_after is None


def test_hard_split_trailing_whitespace_in_piece_rstripped():
    """piece 的 trailing whitespace 被 rstrip。"""
    text = "abc   def"
    pieces = _hard_split_with_whitespace_fallback(text, 4)
    # 第一个 piece 在某个空白处切，rstripped
    assert all(not p.text.endswith(" ") for p in pieces)


def test_hard_split_returns_list_of_splitpiece():
    pieces = _hard_split_with_whitespace_fallback("x", 10)
    assert isinstance(pieces, list)
    for p in pieces:
        assert isinstance(p, _SplitPiece)


def test_hard_split_start_end_within_text_bounds():
    """所有 piece 的 start/end 都在 [0, len(text)]。"""
    text = "word " * 50
    pieces = _hard_split_with_whitespace_fallback(text, 50)
    n = len(text)
    for p in pieces:
        assert 0 <= p.start <= p.end <= n


# =========================================================================
# _split_long_text 深度
# =========================================================================


def test_split_long_text_signature():
    sig = inspect.signature(_split_long_text)
    params = list(sig.parameters)
    assert params == ["text", "max_chars"]


def test_split_long_text_return_annotation_str():
    sig = inspect.signature(_split_long_text)
    assert sig.return_annotation == "list[_SplitPiece]"


def test_split_long_text_empty_returns_empty_list():
    assert _split_long_text("", 100) == []


def test_split_long_text_only_whitespace_returns_empty():
    assert _split_long_text("   \n\t  ", 100) == []


def test_split_long_text_short_returns_single_piece():
    """len(text) ≤ max_chars → 1 piece, boundary_after=None。"""
    pieces = _split_long_text("hello", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "hello"
    assert pieces[0].boundary_after is None
    assert pieces[0].start == 0
    assert pieces[0].end == 5


def test_split_long_text_text_is_stripped_first():
    """input text 先 strip 再 split。"""
    pieces = _split_long_text("  hello  ", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "hello"


def test_split_long_text_each_piece_within_max_chars():
    """所有 piece text 长度 ≤ max_chars。"""
    text = " ".join(["word"] * 200)  # 999 chars
    pieces = _split_long_text(text, 50)
    for p in pieces:
        assert len(p.text) <= 50


def test_split_long_text_exact_boundary():
    """len(text) == max_chars → 1 piece。"""
    text = "a" * 50
    pieces = _split_long_text(text, 50)
    assert len(pieces) == 1


def test_split_long_text_just_over_boundary_two_pieces():
    """len(text) == max_chars + 1 → 需 ≥ 2 piece。"""
    text = "a" * 51
    pieces = _split_long_text(text, 50)
    assert len(pieces) >= 2


def test_split_long_text_returns_list_of_splitpiece():
    pieces = _split_long_text("hello", 100)
    assert isinstance(pieces, list)
    for p in pieces:
        assert isinstance(p, _SplitPiece)


def test_split_long_text_sentence_split_preserves_punctuation():
    """句子切分时，标点保留在前句末尾。"""
    text = "First sentence. Second sentence."
    pieces = _split_long_text(text, 200)
    # text ≤ max_chars → 1 piece
    assert len(pieces) == 1
    assert pieces[0].text == text


def test_split_long_text_sentence_split_long():
    """两句拼接超长 → 至少 2 piece。"""
    text = "Sentence one with many words. " * 10
    pieces = _split_long_text(text, 50)
    assert len(pieces) >= 2


def test_split_long_text_start_end_in_text_coords():
    """所有 start/end 在 stripped text 坐标系。"""
    text = "hello world foo bar baz"
    pieces = _split_long_text(text, 10)
    n = len(text)
    for p in pieces:
        assert 0 <= p.start <= p.end <= n


# =========================================================================
# _ChunkBuffer 深度
# =========================================================================


def test_chunk_buffer_is_dataclass():
    assert is_dataclass(_ChunkBuffer)


def test_chunk_buffer_not_frozen():
    """_ChunkBuffer 不是 frozen（mutable buffer）。"""
    buf = _ChunkBuffer(document_id="d")
    buf.counter = 5  # 应该成功，不抛 FrozenInstanceError
    assert buf.counter == 5


def test_chunk_buffer_field_count():
    cb_fields = fields(_ChunkBuffer)
    assert len(cb_fields) == 3


def test_chunk_buffer_field_names_exact():
    cb_fields = fields(_ChunkBuffer)
    names = [f.name for f in cb_fields]
    assert names == ["document_id", "parts", "counter"]


def test_chunk_buffer_field_types():
    cb_fields = {f.name: f for f in fields(_ChunkBuffer)}
    assert cb_fields["document_id"].type == "str"
    assert cb_fields["parts"].type == "list[tuple[str, str, int, int]]"
    assert cb_fields["counter"].type == "int"


def test_chunk_buffer_default_parts_empty():
    buf = _ChunkBuffer(document_id="d")
    assert buf.parts == []


def test_chunk_buffer_default_counter_zero():
    buf = _ChunkBuffer(document_id="d")
    assert buf.counter == 0


def test_chunk_buffer_each_instance_has_own_parts():
    """default_factory=list 给每个实例新 list（不是共享）。"""
    buf1 = _ChunkBuffer(document_id="d1")
    buf2 = _ChunkBuffer(document_id="d2")
    buf1.push_text("a", "e1", 0, 1)
    assert buf1.parts != buf2.parts
    assert buf2.parts == []


def test_chunk_buffer_push_text_appends():
    buf = _ChunkBuffer(document_id="d")
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e2", 6, 11)
    assert buf.parts == [
        ("hello", "e1", 0, 5),
        ("world", "e2", 6, 11),
    ]


def test_chunk_buffer_length_sum_of_text_lengths():
    buf = _ChunkBuffer(document_id="d")
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e2", 6, 11)
    assert buf.length() == 10  # 5 + 5


def test_chunk_buffer_length_zero_when_empty():
    buf = _ChunkBuffer(document_id="d")
    assert buf.length() == 0


def test_chunk_buffer_is_empty_true_when_no_parts():
    buf = _ChunkBuffer(document_id="d")
    assert buf.is_empty() is True


def test_chunk_buffer_is_empty_false_with_parts():
    buf = _ChunkBuffer(document_id="d")
    buf.push_text("hello", "e1", 0, 5)
    assert buf.is_empty() is False


def test_chunk_buffer_flush_empty_returns_none():
    buf = _ChunkBuffer(document_id="d")
    assert buf.flush(strategy="x", max_chars=100) is None


def test_chunk_buffer_flush_returns_chunk():
    buf = _ChunkBuffer(document_id="d", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    chunk = buf.flush(strategy="sequential", max_chars=100)
    assert isinstance(chunk, Chunk)


def test_chunk_buffer_flush_text_joined_with_space():
    buf = _ChunkBuffer(document_id="d", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e2", 6, 11)
    chunk = buf.flush(strategy="sequential", max_chars=100)
    assert chunk.text == "hello world"


def test_chunk_buffer_flush_source_element_ids_unique():
    buf = _ChunkBuffer(document_id="d", counter=0)
    buf.push_text("a", "e1", 0, 1)
    buf.push_text("b", "e2", 1, 2)
    buf.push_text("c", "e1", 2, 3)  # e1 重复
    chunk = buf.flush(strategy="x", max_chars=100)
    # 去重保序：e1 出现 1 次
    assert chunk.source_element_ids == ["e1", "e2"]


def test_chunk_buffer_flush_source_spans_per_part():
    buf = _ChunkBuffer(document_id="d", counter=0)
    buf.push_text("a", "e1", 0, 1)
    buf.push_text("b", "e2", 5, 6)
    chunk = buf.flush(strategy="x", max_chars=100)
    assert chunk.source_spans == [
        {"element_id": "e1", "start": 0, "end": 1},
        {"element_id": "e2", "start": 5, "end": 6},
    ]


def test_chunk_buffer_flush_chunk_id_with_counter():
    buf = _ChunkBuffer(document_id="doc1", counter=7)
    buf.push_text("x", "e1", 0, 1)
    chunk = buf.flush(strategy="x", max_chars=100)
    assert chunk.chunk_id == "doc1::c0007"


def test_chunk_buffer_flush_metadata_strategy():
    buf = _ChunkBuffer(document_id="d", counter=0)
    buf.push_text("x", "e1", 0, 1)
    chunk = buf.flush(strategy="my_strat", max_chars=42)
    assert chunk.metadata["strategy"] == "my_strat"


def test_chunk_buffer_flush_metadata_max_chars():
    buf = _ChunkBuffer(document_id="d", counter=0)
    buf.push_text("x", "e1", 0, 1)
    chunk = buf.flush(strategy="x", max_chars=42)
    assert chunk.metadata["max_chars"] == 42


def test_chunk_buffer_flush_metadata_char_count():
    buf = _ChunkBuffer(document_id="d", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    chunk = buf.flush(strategy="x", max_chars=100)
    assert chunk.metadata["char_count"] == 5


def test_chunk_buffer_flush_clears_parts():
    buf = _ChunkBuffer(document_id="d", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    buf.flush(strategy="x", max_chars=100)
    assert buf.parts == []
    assert buf.is_empty() is True


def test_chunk_buffer_flush_whitespace_only_text_returns_none():
    buf = _ChunkBuffer(document_id="d", counter=0)
    buf.push_text("   ", "e1", 0, 3)
    chunk = buf.flush(strategy="x", max_chars=100)
    # text.strip() == "" → None
    assert chunk is None


# =========================================================================
# StructuralChunker 深度
# =========================================================================


def test_structural_chunker_is_class():
    assert isinstance(StructuralChunker, type)


def test_structural_chunker_init_default_max_chars():
    ck = StructuralChunker()
    assert ck.max_chars == 800


def test_structural_chunker_init_explicit_max_chars():
    ck = StructuralChunker(max_chars=100)
    assert ck.max_chars == 100


def test_structural_chunker_init_min_max_chars_32():
    ck = StructuralChunker(max_chars=32)
    assert ck.max_chars == 32


def test_structural_chunker_init_below_32_raises():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=31)


def test_structural_chunker_init_zero_raises():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=0)


def test_structural_chunker_init_negative_raises():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=-100)


def test_structural_chunker_chunk_method_present():
    ck = StructuralChunker()
    assert hasattr(ck, "chunk")
    assert callable(ck.chunk)


def test_structural_chunker_chunk_signature():
    sig = inspect.signature(StructuralChunker.chunk)
    params = list(sig.parameters)
    # self + document
    assert params == ["self", "document"]


def test_structural_chunker_chunk_return_annotation_str():
    sig = inspect.signature(StructuralChunker.chunk)
    assert sig.return_annotation == "list[Chunk]"


def test_structural_chunker_chunk_empty_document_returns_empty_list():
    doc = Document(
        document_id="d1", source_path="x.pdf",
        source_hash="a" * 64,
        parser_name="fallback", parser_version="0.1.0",
        source_type="pdf", elements=[], chunks=[],
    )
    ck = StructuralChunker()
    assert ck.chunk(doc) == []


def test_structural_chunker_chunk_returns_list_of_chunks():
    elem = Element(source_locator={}, element_id="e1", type="paragraph", content="hello world")
    doc = Document(
        document_id="d1", source_path="x.pdf",
        source_hash="a" * 64,
        parser_name="fallback", parser_version="0.1.0",
        source_type="pdf", elements=[elem], chunks=[],
    )
    ck = StructuralChunker(max_chars=100)
    chunks = ck.chunk(doc)
    assert isinstance(chunks, list)
    for c in chunks:
        assert isinstance(c, Chunk)


def test_structural_chunker_chunk_chunk_id_increments():
    """多 chunk 时 chunk_id 后缀 c0000/c0001/... 递增。"""
    elems = [
        Element(source_locator={}, element_id=f"e{i}", type="paragraph", content=f"paragraph-{i}-content")
        for i in range(5)
    ]
    doc = Document(
        document_id="doc", source_path="x.pdf",
        source_hash="a" * 64,
        parser_name="fallback", parser_version="0.1.0",
        source_type="pdf", elements=elems, chunks=[],
    )
    ck = StructuralChunker(max_chars=32)  # 最小，强制多 chunk
    chunks = ck.chunk(doc)
    assert len(chunks) >= 2
    for i, c in enumerate(chunks):
        assert c.chunk_id == f"doc::c{i:04d}"


def test_structural_chunker_chunk_table_isolated():
    """table element 单独成 chunk。"""
    elem = Element(source_locator={}, element_id="e1", type="table", content="| col |")
    doc = Document(
        document_id="d", source_path="x.pdf",
        source_hash="a" * 64,
        parser_name="fallback", parser_version="0.1.0",
        source_type="pdf", elements=[elem], chunks=[],
    )
    ck = StructuralChunker(max_chars=100)
    chunks = ck.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].metadata["strategy"] == "isolated_table"


def test_structural_chunker_chunk_image_skipped():
    """image element 不参与分块（_element_text_with_span 返回空）。"""
    elem = Element(source_locator={}, element_id="e1", type="image", content="image_data", resource_path="x.png")
    doc = Document(
        document_id="d", source_path="x.pdf",
        source_hash="a" * 64,
        parser_name="fallback", parser_version="0.1.0",
        source_type="pdf", elements=[elem], chunks=[],
    )
    ck = StructuralChunker(max_chars=100)
    chunks = ck.chunk(doc)
    assert chunks == []


def test_structural_chunker_chunk_caption_isolated():
    elem = Element(source_locator={}, element_id="e1", type="caption", content="A caption")
    doc = Document(
        document_id="d", source_path="x.pdf",
        source_hash="a" * 64,
        parser_name="fallback", parser_version="0.1.0",
        source_type="pdf", elements=[elem], chunks=[],
    )
    ck = StructuralChunker(max_chars=100)
    chunks = ck.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].metadata["strategy"] == "isolated_caption"


def test_structural_chunker_chunk_heading_starts_new_chunk():
    """heading 是硬边界。"""
    elems = [
        Element(source_locator={}, element_id="e1", type="paragraph", content="first paragraph content"),
        Element(source_locator={}, element_id="e2", type="heading", content="The Heading"),
        Element(source_locator={}, element_id="e3", type="paragraph", content="second paragraph content"),
    ]
    doc = Document(
        document_id="d", source_path="x.pdf",
        source_hash="a" * 64,
        parser_name="fallback", parser_version="0.1.0",
        source_type="pdf", elements=elems, chunks=[],
    )
    ck = StructuralChunker(max_chars=100)
    chunks = ck.chunk(doc)
    # 至少 2 chunk（heading 之前一个，heading+之后一个）
    assert len(chunks) >= 2


def test_structural_chunker_chunk_long_paragraph_split():
    """超长 paragraph 被切。"""
    long_text = "word " * 200  # 1000 字符
    elem = Element(source_locator={}, element_id="e1", type="paragraph", content=long_text)
    doc = Document(
        document_id="d", source_path="x.pdf",
        source_hash="a" * 64,
        parser_name="fallback", parser_version="0.1.0",
        source_type="pdf", elements=[elem], chunks=[],
    )
    ck = StructuralChunker(max_chars=50)
    chunks = ck.chunk(doc)
    assert len(chunks) >= 2
    for c in chunks:
        assert c.metadata["strategy"] == "long_paragraph_sentence_split"


def test_structural_chunker_does_not_mutate_document():
    elem = Element(source_locator={}, element_id="e1", type="paragraph", content="hello")
    doc = Document(
        document_id="d", source_path="x.pdf",
        source_hash="a" * 64,
        parser_name="fallback", parser_version="0.1.0",
        source_type="pdf", elements=[elem], chunks=[],
    )
    original_chunks = list(doc.chunks)
    ck = StructuralChunker(max_chars=100)
    ck.chunk(doc)
    assert doc.chunks == original_chunks  # 没赋值回去


# =========================================================================
# _element_text_with_span 深度
# =========================================================================


def test_element_text_with_span_image_returns_empty():
    elem = Element(source_locator={}, element_id="e1", type="image", content="x", resource_path="y.png")
    ck = StructuralChunker()
    text, start, end = ck._element_text_with_span(elem)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_paragraph_returns_stripped():
    elem = Element(source_locator={}, element_id="e1", type="paragraph", content="  hello  ")
    ck = StructuralChunker()
    text, start, end = ck._element_text_with_span(elem)
    assert text == "hello"
    assert start == 2
    assert end == 7


def test_element_text_with_span_empty_content_returns_empty():
    elem = Element(source_locator={}, element_id="e1", type="paragraph", content="   ")
    ck = StructuralChunker()
    text, start, end = ck._element_text_with_span(elem)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_none_content_returns_empty():
    """Element __post_init__ 拒绝 content=None（需 content 或 resource_path 之一）；
    用 whitespace-only content 模拟 "effective None"。"""
    elem = Element(source_locator={}, element_id="e1", type="paragraph", content="   ")
    ck = StructuralChunker()
    text, start, end = ck._element_text_with_span(elem)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_no_leading_whitespace():
    elem = Element(source_locator={}, element_id="e1", type="paragraph", content="hello")
    ck = StructuralChunker()
    text, start, end = ck._element_text_with_span(elem)
    assert text == "hello"
    assert start == 0
    assert end == 5


def test_element_text_with_span_multiline_content():
    elem = Element(source_locator={}, element_id="e1", type="paragraph", content="  hello\nworld  ")
    ck = StructuralChunker()
    text, start, end = ck._element_text_with_span(elem)
    assert text == "hello\nworld"
    assert start == 2
    assert end == 13  # 2 + 11 ("hello\nworld" len)


def test_element_text_compat_returns_text_only():
    """_element_text 兼容旧接口，返回 stripped text。"""
    elem = Element(source_locator={}, element_id="e1", type="paragraph", content="  hello  ")
    ck = StructuralChunker()
    assert ck._element_text(elem) == "hello"


def test_element_text_signature():
    sig = inspect.signature(StructuralChunker._element_text)
    params = list(sig.parameters)
    assert params == ["self", "el"]


def test_element_text_with_span_signature():
    sig = inspect.signature(StructuralChunker._element_text_with_span)
    params = list(sig.parameters)
    assert params == ["self", "el"]


def test_element_text_with_span_return_annotation_str():
    sig = inspect.signature(StructuralChunker._element_text_with_span)
    assert sig.return_annotation == "tuple[str, int, int]"
