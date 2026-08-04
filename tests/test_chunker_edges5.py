r"""app/chunkers/structural.py 边角测试 - 第五轮（Round 129）。

补强已有 base/edges/edges2/edges3/edges4（共 506 测试）未覆盖的深度路径：
- _SplitPiece 深度：
  - boundary_after 三个值（whitespace/forced_char/None）
  - frozen=True → 不可变
  - hashable
- _PART_* 常量值精确
- _SENTENCE_SPLIT_RE pattern 内容
- _HARD_BREAK_LANGS 内容
- _WHITESPACE_RE 行为
- normalize_text 深度：
  - 空串 / None / 单空白 / 全空白
  - 混合空白（tab/newline/CR）
  - 中英文混合
- _hard_split_with_whitespace_fallback 深度：
  - max_chars=32 边界
  - 单 char piece
  - 全空白 piece 跳过
  - ws 在 lower/upper/中间
  - 多 piece 累积
- _split_long_text 深度：
  - 单句不超长
  - 多句累积超长
  - 句子边界（中文/英文/混用）
  - piece.start/end 坐标
- _ChunkBuffer 深度：
  - flush metadata 精确字段
  - source_spans 结构
  - chunk_id 格式
  - 多次 push 同 element
  - counter 字段
- StructuralChunker.__init__ 深度：
  - max_chars < 32 ValueError
  - max_chars = 32 接受
  - 默认 800
  - ValueError message 含 max_chars
- StructuralChunker.chunk 深度：
  - 不同 element type 的 strategy 值
  - heading 硬边界封口
  - table/image/caption isolated
  - 长 paragraph 句子切分
  - source_spans 坐标
- _element_text_with_span 深度：
  - lstrip 长度推算 start
  - 空白内容
  - image
- 模块结构深度：
  - imports 完整
  - __all__ 2 项
  - 各 helper callable
- 签名深度：
  - chunker methods 返回类型
  - 各函数参数精确
"""
# Note: docstring uses raw string to avoid SyntaxWarning for \s in regex patterns.

from __future__ import annotations

import inspect
import re
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path

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
    StructuralChunker,
)
from app.models import Chunk, Document, Element


# =========================================================================
# _PART_* 常量值精确
# =========================================================================


def test_part_text_constant_value_zero():
    assert _PART_TEXT == 0


def test_part_element_id_constant_value_one():
    assert _PART_ELEMENT_ID == 1


def test_part_start_constant_value_two():
    assert _PART_START == 2


def test_part_end_constant_value_three():
    assert _PART_END == 3


def test_part_constants_distinct():
    assert len({_PART_TEXT, _PART_ELEMENT_ID, _PART_START, _PART_END}) == 4


def test_part_constants_ordered():
    assert _PART_TEXT < _PART_ELEMENT_ID < _PART_START < _PART_END


# =========================================================================
# _SplitPiece 深度
# =========================================================================


def test_split_piece_is_dataclass():
    assert is_dataclass(_SplitPiece)


def test_split_piece_is_frozen():
    p = _SplitPiece(text="x", boundary_after=None)
    with pytest.raises(FrozenInstanceError):
        p.text = "y"  # type: ignore[misc]


def test_split_piece_hashable():
    p = _SplitPiece(text="x", boundary_after=None)
    assert hash(p) == hash(_SplitPiece(text="x", boundary_after=None))


def test_split_piece_default_start_zero():
    p = _SplitPiece(text="x", boundary_after=None)
    assert p.start == 0


def test_split_piece_default_end_zero():
    p = _SplitPiece(text="x", boundary_after=None)
    assert p.end == 0


def test_split_piece_explicit_start_end():
    p = _SplitPiece(text="x", boundary_after=None, start=5, end=10)
    assert p.start == 5
    assert p.end == 10


def test_split_piece_boundary_after_whitespace():
    p = _SplitPiece(text="x", boundary_after="whitespace")
    assert p.boundary_after == "whitespace"


def test_split_piece_boundary_after_forced_char():
    p = _SplitPiece(text="x", boundary_after="forced_char")
    assert p.boundary_after == "forced_char"


def test_split_piece_boundary_after_none():
    p = _SplitPiece(text="x", boundary_after=None)
    assert p.boundary_after is None


def test_split_piece_equality_same_values():
    p1 = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    p2 = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    assert p1 == p2


def test_split_piece_equality_different_text():
    p1 = _SplitPiece(text="x", boundary_after=None)
    p2 = _SplitPiece(text="y", boundary_after=None)
    assert p1 != p2


def test_split_piece_field_count():
    import dataclasses

    fields = dataclasses.fields(_SplitPiece)
    assert len(fields) == 4


def test_split_piece_field_names_exact():
    import dataclasses

    fields = dataclasses.fields(_SplitPiece)
    names = {f.name for f in fields}
    assert names == {"text", "boundary_after", "start", "end"}


# =========================================================================
# _SENTENCE_SPLIT_RE pattern 内容
# =========================================================================


def test_sentence_split_re_is_compiled_pattern():
    assert isinstance(_SENTENCE_SPLIT_RE, re.Pattern)


def test_sentence_split_re_pattern_contains_chinese_period():
    assert "。" in _SENTENCE_SPLIT_RE.pattern


def test_sentence_split_re_pattern_contains_chinese_exclamation():
    assert "！" in _SENTENCE_SPLIT_RE.pattern


def test_sentence_split_re_pattern_contains_chinese_question():
    assert "？" in _SENTENCE_SPLIT_RE.pattern


def test_sentence_split_re_pattern_contains_english_punctuations():
    assert "!" in _SENTENCE_SPLIT_RE.pattern
    assert "?" in _SENTENCE_SPLIT_RE.pattern
    assert "." in _SENTENCE_SPLIT_RE.pattern


def test_sentence_split_re_pattern_uses_lookbehind():
    assert "?<=" in _SENTENCE_SPLIT_RE.pattern


def test_sentence_split_re_split_chinese_sentences():
    r"""中文标点直接相邻无空白 → 不切（需要 \s+ 才切）。"""
    text = "第一句。第二句！第三句？"
    parts = _SENTENCE_SPLIT_RE.split(text)
    # 无空白分隔 → 整段不切
    assert parts == ["第一句。第二句！第三句？"]


def test_sentence_split_re_split_chinese_sentences_with_whitespace():
    r"""中文标点后跟空白 → 切。"""
    text = "第一句。 第二句！ 第三句？"
    parts = _SENTENCE_SPLIT_RE.split(text)
    assert "第一句。" in parts
    assert "第二句！" in parts


def test_sentence_split_re_split_english_sentences():
    text = "First sentence. Second sentence!"
    parts = _SENTENCE_SPLIT_RE.split(text)
    assert "First sentence." in parts


def test_sentence_split_re_no_split_when_no_punct():
    text = "no punctuation here"
    parts = _SENTENCE_SPLIT_RE.split(text)
    assert parts == ["no punctuation here"]


def test_sentence_split_re_no_split_when_punct_directly_adjacent():
    r"""标点直接相邻无空白 → 不切（需 \s+）。"""
    text = "first.second"
    parts = _SENTENCE_SPLIT_RE.split(text)
    assert parts == ["first.second"]


# =========================================================================
# _HARD_BREAK_LANGS 内容
# =========================================================================


def test_hard_break_langs_is_tuple():
    assert isinstance(_HARD_BREAK_LANGS, tuple)


def test_hard_break_langs_length_six():
    assert len(_HARD_BREAK_LANGS) == 6


def test_hard_break_langs_contains_chinese_punctuations():
    assert "。" in _HARD_BREAK_LANGS
    assert "！" in _HARD_BREAK_LANGS
    assert "？" in _HARD_BREAK_LANGS


def test_hard_break_langs_contains_english_punctuations():
    assert "." in _HARD_BREAK_LANGS
    assert "!" in _HARD_BREAK_LANGS
    assert "?" in _HARD_BREAK_LANGS


def test_hard_break_langs_exact_set():
    assert set(_HARD_BREAK_LANGS) == {"。", "！", "？", ".", "!", "?"}


# =========================================================================
# _WHITESPACE_RE 行为
# =========================================================================


def test_whitespace_re_is_compiled_pattern():
    assert isinstance(_WHITESPACE_RE, re.Pattern)


def test_whitespace_re_pattern_is_one_or_more():
    assert _WHITESPACE_RE.pattern == r"\s+"


def test_whitespace_re_sub_collapses_spaces():
    assert _WHITESPACE_RE.sub(" ", "a   b") == "a b"


def test_whitespace_re_sub_collapses_tabs():
    assert _WHITESPACE_RE.sub(" ", "a\tb") == "a b"


def test_whitespace_re_sub_collapses_newlines():
    assert _WHITESPACE_RE.sub(" ", "a\nb") == "a b"


def test_whitespace_re_sub_collapses_mixed():
    assert _WHITESPACE_RE.sub(" ", "a \t\n b") == "a b"


# =========================================================================
# normalize_text 深度
# =========================================================================


def test_normalize_text_empty_string_returns_empty():
    assert normalize_text("") == ""


def test_normalize_text_none_returns_empty():
    # not s → 返回 ""
    assert normalize_text(None) == ""  # type: ignore[arg-type]


def test_normalize_text_single_space():
    assert normalize_text(" ") == ""


def test_normalize_text_all_whitespace_returns_empty():
    assert normalize_text("   \t\n  ") == ""


def test_normalize_text_no_change_already_normalized():
    assert normalize_text("hello world") == "hello world"


def test_normalize_text_collapses_multiple_spaces():
    assert normalize_text("hello   world") == "hello world"


def test_normalize_text_strips_leading_trailing():
    assert normalize_text("  hello  ") == "hello"


def test_normalize_text_mixed_whitespace():
    assert normalize_text("a\t b\n c") == "a b c"


def test_normalize_text_idempotent():
    text = "  some   random \t text \n with  whitespace  "
    once = normalize_text(text)
    twice = normalize_text(once)
    assert once == twice


def test_normalize_text_returns_str_type():
    assert isinstance(normalize_text("x"), str)


def test_normalize_text_preserves_punctuation():
    assert normalize_text("hello, world!") == "hello, world!"


def test_normalize_text_preserves_unicode():
    assert normalize_text("  中文  测试  ") == "中文 测试"


def test_normalize_text_emoji_preserved():
    assert normalize_text("a 🎉 b") == "a 🎉 b"


# =========================================================================
# _hard_split_with_whitespace_fallback 深度
# =========================================================================


def test_hard_split_signature_two_params():
    sig = inspect.signature(_hard_split_with_whitespace_fallback)
    params = list(sig.parameters.keys())
    assert len(params) == 2
    assert "text" in params
    assert "max_chars" in params


def test_hard_split_returns_list_of_split_pieces():
    result = _hard_split_with_whitespace_fallback("hello world", 32)
    assert isinstance(result, list)
    assert all(isinstance(p, _SplitPiece) for p in result)


def test_hard_split_empty_text_returns_empty_list():
    """空 text 直接跳过循环。"""
    assert _hard_split_with_whitespace_fallback("", 32) == []


def test_hard_split_whitespace_only_returns_empty_list():
    """全空白 → 全部跳过。"""
    assert _hard_split_with_whitespace_fallback("   \t\n  ", 32) == []


def test_hard_split_text_under_max_returns_single_piece():
    result = _hard_split_with_whitespace_fallback("hello", 32)
    assert len(result) == 1
    assert result[0].text == "hello"
    assert result[0].boundary_after is None


def test_hard_split_text_exact_max_returns_single_piece():
    text = "a" * 32
    result = _hard_split_with_whitespace_fallback(text, 32)
    # remaining = 32 ≤ max_chars 32 → 单 piece
    assert len(result) == 1


def test_hard_split_text_above_max_with_whitespace():
    text = "a" * 30 + " " + "b" * 30
    result = _hard_split_with_whitespace_fallback(text, 32)
    assert len(result) == 2
    # 第一个 piece 在 whitespace 处切
    assert result[0].boundary_after == "whitespace"


def test_hard_split_text_above_max_no_whitespace_forced_char():
    text = "a" * 100
    result = _hard_split_with_whitespace_fallback(text, 32)
    # 多 piece，全部 forced_char（除最后一个）
    assert all(p.boundary_after in ("forced_char", None) for p in result)
    # 最后一个 piece boundary_after 是 None
    assert result[-1].boundary_after is None


def test_hard_split_leading_whitespace_skipped():
    text = "   hello"
    result = _hard_split_with_whitespace_fallback(text, 32)
    assert len(result) == 1
    assert result[0].text == "hello"


def test_hard_split_each_piece_max_chars_or_less():
    text = " ".join(["word" + str(i) for i in range(20)])
    result = _hard_split_with_whitespace_fallback(text, 32)
    for p in result:
        assert len(p.text) <= 32


def test_hard_split_start_end_in_input_coords():
    text = "aaa bbb ccc"
    result = _hard_split_with_whitespace_fallback(text, 32)
    # 单 piece，start=0, end=len(stripped piece text)
    assert result[0].start == 0
    assert result[0].end == len(result[0].text)


# =========================================================================
# _split_long_text 深度
# =========================================================================


def test_split_long_text_signature_two_params():
    sig = inspect.signature(_split_long_text)
    params = list(sig.parameters.keys())
    assert len(params) == 2
    assert "text" in params
    assert "max_chars" in params


def test_split_long_text_returns_list_type():
    assert isinstance(_split_long_text("hello", 32), list)


def test_split_long_text_each_item_is_split_piece():
    for p in _split_long_text("hello", 32):
        assert isinstance(p, _SplitPiece)


def test_split_long_text_empty_returns_empty():
    assert _split_long_text("", 32) == []


def test_split_long_text_whitespace_only_returns_empty():
    assert _split_long_text("   \t\n  ", 32) == []


def test_split_long_text_short_text_single_piece():
    result = _split_long_text("hello", 32)
    assert len(result) == 1
    assert result[0].text == "hello"
    assert result[0].boundary_after is None


def test_split_long_text_exact_max_chars_single_piece():
    text = "a" * 32
    result = _split_long_text(text, 32)
    assert len(result) == 1
    assert result[0].text == text


def test_split_long_text_each_piece_max_chars_or_less():
    text = "。".join(["sentence " + str(i) for i in range(30)])
    for p in _split_long_text(text, 32):
        assert len(p.text) <= 32


def test_split_long_text_piece_start_end_in_stripped_coords():
    text = "  hello world  "
    result = _split_long_text(text, 32)
    # 入口 strip 后 text = "hello world"
    assert result[0].start == 0
    assert result[0].end == len("hello world")


def test_split_long_text_chinese_mixed_english():
    text = "中文 sentence. Another 中文."
    result = _split_long_text(text, 32)
    assert len(result) >= 1


def test_split_long_text_strips_input():
    """text 入口 strip。"""
    text = "   hello   "
    result = _split_long_text(text, 32)
    assert result[0].text == "hello"


def test_split_long_text_sentence_with_period():
    text = "Hello world. Another sentence."
    result = _split_long_text(text, 32)
    # 短文本 → 单 piece
    assert len(result) == 1


def test_split_long_text_long_paragraph_multiple_pieces():
    text = " ".join(["word"] * 100)
    result = _split_long_text(text, 32)
    assert len(result) > 1


# =========================================================================
# _ChunkBuffer 深度
# =========================================================================


def test_chunk_buffer_is_dataclass():
    assert is_dataclass(_ChunkBuffer)


def test_chunk_buffer_default_factory_independent():
    b1 = _ChunkBuffer(document_id="d1")
    b2 = _ChunkBuffer(document_id="d2")
    b1.push_text("a", "e1", 0, 1)
    assert b2.is_empty()


def test_chunk_buffer_document_id_field():
    b = _ChunkBuffer(document_id="doc-1")
    assert b.document_id == "doc-1"


def test_chunk_buffer_counter_default_zero():
    b = _ChunkBuffer(document_id="doc-1")
    assert b.counter == 0


def test_chunk_buffer_counter_settable():
    b = _ChunkBuffer(document_id="doc-1")
    b.counter = 5
    assert b.counter == 5


def test_chunk_buffer_push_text_appends_to_parts():
    b = _ChunkBuffer(document_id="d")
    b.push_text("hello", "e1", 0, 5)
    assert len(b.parts) == 1
    assert b.parts[0] == ("hello", "e1", 0, 5)


def test_chunk_buffer_push_multiple_texts():
    b = _ChunkBuffer(document_id="d")
    b.push_text("a", "e1", 0, 1)
    b.push_text("b", "e2", 0, 1)
    assert len(b.parts) == 2


def test_chunk_buffer_length_sum_text_lengths():
    b = _ChunkBuffer(document_id="d")
    b.push_text("hello", "e1", 0, 5)
    b.push_text("world", "e2", 0, 5)
    assert b.length() == 10  # 不含 separator


def test_chunk_buffer_is_empty_true_default():
    b = _ChunkBuffer(document_id="d")
    assert b.is_empty()


def test_chunk_buffer_is_empty_false_after_push():
    b = _ChunkBuffer(document_id="d")
    b.push_text("x", "e1", 0, 1)
    assert not b.is_empty()


def test_chunk_buffer_flush_empty_returns_none():
    b = _ChunkBuffer(document_id="d")
    assert b.flush(strategy="s", max_chars=800) is None


def test_chunk_buffer_flush_whitespace_only_returns_none():
    b = _ChunkBuffer(document_id="d")
    b.push_text("   ", "e1", 0, 3)
    # join+strip 后是空 → None
    assert b.flush(strategy="s", max_chars=800) is None


def test_chunk_buffer_flush_clears_parts():
    b = _ChunkBuffer(document_id="d")
    b.push_text("hello", "e1", 0, 5)
    b.flush(strategy="s", max_chars=800)
    assert b.is_empty()


def test_chunk_buffer_flush_returns_chunk():
    b = _ChunkBuffer(document_id="d")
    b.push_text("hello", "e1", 0, 5)
    c = b.flush(strategy="s", max_chars=800)
    assert isinstance(c, Chunk)


def test_chunk_buffer_flush_chunk_id_uses_counter():
    b = _ChunkBuffer(document_id="doc-1", counter=7)
    b.push_text("x", "e1", 0, 1)
    c = b.flush(strategy="s", max_chars=800)
    assert c.chunk_id == "doc-1::c0007"


def test_chunk_buffer_flush_dedup_source_element_ids_preserves_order():
    b = _ChunkBuffer(document_id="d")
    b.push_text("a", "e2", 0, 1)
    b.push_text("b", "e1", 0, 1)
    b.push_text("c", "e2", 0, 1)
    c = b.flush(strategy="s", max_chars=800)
    # 首次出现顺序：e2, e1（e2 不重复）
    assert c.source_element_ids == ["e2", "e1"]


def test_chunk_buffer_flush_metadata_has_strategy_max_chars_char_count():
    b = _ChunkBuffer(document_id="d")
    b.push_text("hello", "e1", 0, 5)
    c = b.flush(strategy="sequential", max_chars=800)
    assert c.metadata["strategy"] == "sequential"
    assert c.metadata["max_chars"] == 800
    assert c.metadata["char_count"] == 5


def test_chunk_buffer_flush_source_spans_structure():
    b = _ChunkBuffer(document_id="d")
    b.push_text("hello", "e1", 0, 5)
    b.push_text("world", "e2", 10, 15)
    c = b.flush(strategy="s", max_chars=800)
    assert len(c.source_spans) == 2
    for span in c.source_spans:
        assert "element_id" in span
        assert "start" in span
        assert "end" in span


def test_chunk_buffer_flush_text_join_with_single_space():
    b = _ChunkBuffer(document_id="d")
    b.push_text("hello", "e1", 0, 5)
    b.push_text("world", "e2", 0, 5)
    c = b.flush(strategy="s", max_chars=800)
    assert c.text == "hello world"


def test_chunk_buffer_flush_strips_text():
    b = _ChunkBuffer(document_id="d")
    b.push_text("  hello  ", "e1", 0, 9)
    c = b.flush(strategy="s", max_chars=800)
    # join + strip 后是 "hello"
    assert c.text == "hello"


def test_chunk_buffer_field_count():
    import dataclasses

    fields = dataclasses.fields(_ChunkBuffer)
    assert len(fields) == 3  # document_id, parts, counter


def test_chunk_buffer_field_names_exact():
    import dataclasses

    names = {f.name for f in dataclasses.fields(_ChunkBuffer)}
    assert names == {"document_id", "parts", "counter"}


# =========================================================================
# StructuralChunker.__init__ 深度
# =========================================================================


def test_chunker_init_default_max_chars_800():
    c = StructuralChunker()
    assert c.max_chars == 800


def test_chunker_init_explicit_max_chars():
    c = StructuralChunker(max_chars=200)
    assert c.max_chars == 200


def test_chunker_init_max_chars_32_minimum_accepted():
    c = StructuralChunker(max_chars=32)
    assert c.max_chars == 32


def test_chunker_init_max_chars_31_rejected():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=31)


def test_chunker_init_max_chars_zero_rejected():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=0)


def test_chunker_init_max_chars_negative_rejected():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=-100)


def test_chunker_init_value_error_message_contains_max_chars():
    with pytest.raises(ValueError) as ei:
        StructuralChunker(max_chars=10)
    assert "10" in str(ei.value)


def test_chunker_init_value_error_message_mentions_too_small():
    """ValueError 消息提及 max_chars 过小。"""
    with pytest.raises(ValueError) as ei:
        StructuralChunker(max_chars=10)
    assert "过小" in str(ei.value) or "too small" in str(ei.value).lower() or "小" in str(ei.value)


def test_chunker_init_huge_max_chars_accepted():
    c = StructuralChunker(max_chars=1_000_000)
    assert c.max_chars == 1_000_000


# =========================================================================
# StructuralChunker.chunk 深度（不同 element type 的 strategy）
# =========================================================================


def _make_doc(elements: list[Element], document_id: str = "doc-1") -> Document:
    return Document(
        document_id=document_id,
        source_path="/tmp/test.pdf",
        source_type="pdf",
        source_hash="a" * 64,
        parser_name="fallback",
        parser_version="1.0",
        elements=elements,
        chunks=[],
        relations=[],
        warnings=[],
        errors=[],
        metadata={},
    )


def _make_element(
    element_id: str, etype: str, content: str | None = "x", parent_id: str | None = None
) -> Element:
    # Element 的 __post_init__ 要求 content 或 resource_path 至少一个非空。
    # 对 image/空 content 情况提供 resource_path 占位符。
    resource_path = None
    if not content:
        resource_path = "(placeholder)"
    return Element(
        element_id=element_id,
        type=etype,
        content=content,
        resource_path=resource_path,
        parent_id=parent_id,
        source_locator={"page": 1, "bbox": [0, 0, 100, 100]},
        confidence=0.85,
        metadata={},
    )


def test_chunker_chunk_empty_document_returns_empty_list():
    c = StructuralChunker(max_chars=800)
    doc = _make_doc([])
    assert c.chunk(doc) == []


def test_chunker_chunk_returns_list_of_chunks():
    c = StructuralChunker(max_chars=800)
    doc = _make_doc([_make_element("e1", "paragraph", "hello")])
    result = c.chunk(doc)
    assert isinstance(result, list)
    assert all(isinstance(ch, Chunk) for ch in result)


def test_chunker_chunk_paragraph_strategy_sequential():
    c = StructuralChunker(max_chars=800)
    doc = _make_doc([_make_element("e1", "paragraph", "hello")])
    chunks = c.chunk(doc)
    assert chunks[0].metadata["strategy"] == "sequential"


def test_chunker_chunk_table_strategy_isolated_table():
    c = StructuralChunker(max_chars=800)
    doc = _make_doc([_make_element("e1", "table", "| col |")])
    chunks = c.chunk(doc)
    assert chunks[0].metadata["strategy"] == "isolated_table"


def test_chunker_chunk_caption_strategy_isolated_caption():
    c = StructuralChunker(max_chars=800)
    doc = _make_doc([_make_element("e1", "caption", "Figure 1. caption")])
    chunks = c.chunk(doc)
    assert chunks[0].metadata["strategy"] == "isolated_caption"


def test_chunker_chunk_image_element_skipped():
    """image element 不参与分块（_element_text_with_span 返回 ("",0,0)）。"""
    c = StructuralChunker(max_chars=800)
    doc = _make_doc([_make_element("e1", "image", None)])
    chunks = c.chunk(doc)
    assert chunks == []


def test_chunker_chunk_heading_then_paragraph_strategy_sequential():
    """heading 进入 buf，后续 paragraph 累积，最终 flush strategy=sequential。"""
    c = StructuralChunker(max_chars=800)
    doc = _make_doc([
        _make_element("e1", "heading", "Title"),
        _make_element("e2", "paragraph", "content"),
    ])
    chunks = c.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].metadata["strategy"] == "sequential"
    # heading 与 paragraph 都在 chunk
    assert "e1" in chunks[0].source_element_ids
    assert "e2" in chunks[0].source_element_ids


def test_chunker_chunk_consecutive_headings_each_in_own_chunk():
    c = StructuralChunker(max_chars=800)
    doc = _make_doc([
        _make_element("e1", "heading", "Title 1"),
        _make_element("e2", "heading", "Title 2"),
    ])
    chunks = c.chunk(doc)
    assert len(chunks) == 2
    assert chunks[0].source_element_ids == ["e1"]
    assert chunks[1].source_element_ids == ["e2"]


def test_chunker_chunk_chunk_id_format():
    c = StructuralChunker(max_chars=800)
    doc = _make_doc([_make_element("e1", "paragraph", "hello")])
    chunks = c.chunk(doc)
    assert chunks[0].chunk_id == "doc-1::c0000"


def test_chunker_chunk_chunk_id_increments():
    c = StructuralChunker(max_chars=800)
    doc = _make_doc([
        _make_element("e1", "heading", "T1"),
        _make_element("e2", "heading", "T2"),
        _make_element("e3", "heading", "T3"),
    ])
    chunks = c.chunk(doc)
    assert [c.chunk_id for c in chunks] == ["doc-1::c0000", "doc-1::c0001", "doc-1::c0002"]


def test_chunker_chunk_long_paragraph_strategy_long_paragraph_sentence_split():
    c = StructuralChunker(max_chars=32)
    text = "word " * 20  # 100 chars > 32
    doc = _make_doc([_make_element("e1", "paragraph", text)])
    chunks = c.chunk(doc)
    assert all(ch.metadata["strategy"] == "long_paragraph_sentence_split" for ch in chunks)


def test_chunker_chunk_metadata_contains_strategy_max_chars_char_count():
    c = StructuralChunker(max_chars=200)
    doc = _make_doc([_make_element("e1", "paragraph", "hello")])
    chunks = c.chunk(doc)
    m = chunks[0].metadata
    assert "strategy" in m
    assert "max_chars" in m
    assert "char_count" in m


def test_chunker_chunk_source_spans_each_chunk_has_list():
    c = StructuralChunker(max_chars=800)
    doc = _make_doc([_make_element("e1", "paragraph", "hello")])
    chunks = c.chunk(doc)
    assert isinstance(chunks[0].source_spans, list)


def test_chunker_chunk_source_spans_element_id_matches():
    c = StructuralChunker(max_chars=800)
    doc = _make_doc([_make_element("e1", "paragraph", "hello")])
    chunks = c.chunk(doc)
    assert chunks[0].source_spans[0]["element_id"] == "e1"


def test_chunker_chunk_no_chunks_for_blank_paragraph():
    """空 paragraph 不参与分块。"""
    c = StructuralChunker(max_chars=800)
    doc = _make_doc([_make_element("e1", "paragraph", "")])
    assert c.chunk(doc) == []


def test_chunker_chunk_no_chunks_for_whitespace_paragraph():
    c = StructuralChunker(max_chars=800)
    doc = _make_doc([_make_element("e1", "paragraph", "   ")])
    assert c.chunk(doc) == []


# =========================================================================
# _element_text_with_span 深度
# =========================================================================


def test_element_text_with_span_image_returns_empty_tuple():
    c = StructuralChunker()
    el = _make_element("e1", "image", None)
    assert c._element_text_with_span(el) == ("", 0, 0)


def test_element_text_with_span_empty_content():
    c = StructuralChunker()
    el = _make_element("e1", "paragraph", "")
    assert c._element_text_with_span(el) == ("", 0, 0)


def test_element_text_with_span_none_content():
    c = StructuralChunker()
    el = _make_element("e1", "paragraph", None)
    assert c._element_text_with_span(el) == ("", 0, 0)


def test_element_text_with_span_whitespace_only():
    c = StructuralChunker()
    el = _make_element("e1", "paragraph", "   ")
    assert c._element_text_with_span(el) == ("", 0, 0)


def test_element_text_with_span_strips_leading_whitespace():
    c = StructuralChunker()
    el = _make_element("e1", "paragraph", "  hello")
    text, start, end = c._element_text_with_span(el)
    assert text == "hello"
    assert start == 2  # 2 个前导空格
    assert end == 7


def test_element_text_with_span_strips_trailing_whitespace():
    c = StructuralChunker()
    el = _make_element("e1", "paragraph", "hello  ")
    text, start, end = c._element_text_with_span(el)
    assert text == "hello"
    assert start == 0
    assert end == 5


def test_element_text_with_span_strips_both_whitespace():
    c = StructuralChunker()
    el = _make_element("e1", "paragraph", "  hello  ")
    text, start, end = c._element_text_with_span(el)
    assert text == "hello"
    assert start == 2
    assert end == 7


def test_element_text_with_span_internal_whitespace_preserved():
    c = StructuralChunker()
    el = _make_element("e1", "paragraph", "hello world")
    text, start, end = c._element_text_with_span(el)
    assert text == "hello world"
    assert start == 0
    assert end == 11


def test_element_text_with_span_returns_tuple_of_three():
    c = StructuralChunker()
    el = _make_element("e1", "paragraph", "hello")
    result = c._element_text_with_span(el)
    assert isinstance(result, tuple)
    assert len(result) == 3


def test_element_text_with_span_image_with_content_still_empty():
    """image 即使有 content 也返回空。"""
    c = StructuralChunker()
    el = _make_element("e1", "image", "an image")
    assert c._element_text_with_span(el) == ("", 0, 0)


def test_element_text_legacy_method_returns_str():
    c = StructuralChunker()
    el = _make_element("e1", "paragraph", "hello")
    result = c._element_text(el)
    assert isinstance(result, str)


def test_element_text_legacy_method_returns_text_only():
    c = StructuralChunker()
    el = _make_element("e1", "paragraph", "  hello  ")
    assert c._element_text(el) == "hello"


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_imports_re():
    from app.chunkers import structural as mod
    assert hasattr(mod, "re")


def test_module_imports_dataclass():
    from app.chunkers import structural as mod
    assert hasattr(mod, "dataclass")


def test_module_imports_field():
    from app.chunkers import structural as mod
    assert hasattr(mod, "field")


def test_module_imports_any():
    from app.chunkers import structural as mod
    assert hasattr(mod, "Any")


def test_module_imports_chunk():
    from app.chunkers import structural as mod
    assert hasattr(mod, "Chunk")


def test_module_imports_document():
    from app.chunkers import structural as mod
    assert hasattr(mod, "Document")


def test_module_imports_element():
    from app.chunkers import structural as mod
    assert hasattr(mod, "Element")


def test_module_has_structural_chunker_class():
    from app.chunkers import structural as mod
    assert hasattr(mod, "StructuralChunker")


def test_module_has_normalize_text():
    from app.chunkers import structural as mod
    assert hasattr(mod, "normalize_text")


def test_module_has_chunk_buffer_class():
    from app.chunkers import structural as mod
    assert hasattr(mod, "_ChunkBuffer")


def test_module_has_split_piece_class():
    from app.chunkers import structural as mod
    assert hasattr(mod, "_SplitPiece")


def test_module_has_split_long_text():
    from app.chunkers import structural as mod
    assert hasattr(mod, "_split_long_text")


def test_module_has_hard_split():
    from app.chunkers import structural as mod
    assert hasattr(mod, "_hard_split_with_whitespace_fallback")


def test_module_has_sentence_split_re():
    from app.chunkers import structural as mod
    assert hasattr(mod, "_SENTENCE_SPLIT_RE")


def test_module_has_whitespace_re():
    from app.chunkers import structural as mod
    assert hasattr(mod, "_WHITESPACE_RE")


def test_module_has_hard_break_langs():
    from app.chunkers import structural as mod
    assert hasattr(mod, "_HARD_BREAK_LANGS")


def test_module_has_part_constants():
    from app.chunkers import structural as mod
    assert hasattr(mod, "_PART_TEXT")
    assert hasattr(mod, "_PART_ELEMENT_ID")
    assert hasattr(mod, "_PART_START")
    assert hasattr(mod, "_PART_END")


def test_module_all_is_list():
    from app.chunkers import structural as mod
    assert isinstance(mod.__all__, list)


def test_module_all_length_two():
    from app.chunkers import structural as mod
    assert len(mod.__all__) == 2


def test_module_all_exact_set():
    from app.chunkers import structural as mod
    assert set(mod.__all__) == {"StructuralChunker", "normalize_text"}


def test_module_all_excludes_internal():
    from app.chunkers import structural as mod
    for item in mod.__all__:
        assert not item.startswith("_")


def test_module_docstring_present():
    from app.chunkers import structural as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_chunker():
    from app.chunkers import structural as mod
    doc = mod.__doc__
    assert "分块" in doc or "chunker" in doc.lower() or "Chunker" in doc


def test_module_docstring_mentions_heading():
    from app.chunkers import structural as mod
    doc = mod.__doc__
    assert "heading" in doc.lower() or "标题" in doc


def test_module_docstring_mentions_source_spans():
    from app.chunkers import structural as mod
    doc = mod.__doc__
    assert "source_spans" in doc or "span" in doc.lower()


def test_module_uses_future_annotations():
    import ast
    from app.chunkers import structural as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    has_future = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(a.name == "annotations" for a in node.names)
        for node in tree.body
    )
    assert has_future


# =========================================================================
# 签名深度
# =========================================================================


def test_normalize_text_signature_one_param():
    sig = inspect.signature(normalize_text)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "s" in params


def test_normalize_text_return_annotation_str():
    sig = inspect.signature(normalize_text)
    ret = sig.return_annotation
    assert ret is str or "str" in str(ret)


def test_structural_chunker_init_signature_two_params():
    sig = inspect.signature(StructuralChunker.__init__)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "max_chars" in params


def test_structural_chunker_init_max_chars_default_800():
    sig = inspect.signature(StructuralChunker.__init__)
    assert sig.parameters["max_chars"].default == 800


def test_structural_chunker_chunk_signature_two_params():
    sig = inspect.signature(StructuralChunker.chunk)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "document" in params


def test_structural_chunker_chunk_return_annotation_list_chunk():
    sig = inspect.signature(StructuralChunker.chunk)
    ret = sig.return_annotation
    assert "list" in str(ret).lower() and "Chunk" in str(ret)


def test_element_text_with_span_signature_two_params():
    sig = inspect.signature(StructuralChunker._element_text_with_span)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "el" in params


def test_element_text_with_span_return_annotation_tuple():
    sig = inspect.signature(StructuralChunker._element_text_with_span)
    ret = sig.return_annotation
    assert "tuple" in str(ret).lower()


def test_chunk_buffer_flush_signature_keyword_only():
    sig = inspect.signature(_ChunkBuffer.flush)
    assert sig.parameters["strategy"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_chunk_buffer_push_text_signature_four_params():
    sig = inspect.signature(_ChunkBuffer.push_text)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "text" in params
    assert "element_id" in params
    assert "start" in params
    assert "end" in params


def test_chunk_buffer_length_signature_one_param():
    sig = inspect.signature(_ChunkBuffer.length)
    params = list(sig.parameters.keys())
    assert len(params) == 1


def test_chunk_buffer_is_empty_signature_one_param():
    sig = inspect.signature(_ChunkBuffer.is_empty)
    params = list(sig.parameters.keys())
    assert len(params) == 1
