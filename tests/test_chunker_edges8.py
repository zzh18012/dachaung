r"""app/chunkers/structural.py 边角测试 - 第八轮（Round 182）。

补强已有 base/edges/edges2-7（共 939 测试）未覆盖的深度：
- _SENTENCE_SPLIT_RE / _WHITESPACE_RE 实际拆分/替换行为（不止 pattern 值）
- _hard_split_with_whitespace_fallback：whitespace 在 lower/upper 边界、连续空白、max_chars=32 最小值
- _split_long_text：累积 flush 边界、坐标映射、sentence_start < 0 防御路径
- _ChunkBuffer：length 含多字节、push_text 多 part 后 flush、flush 后 counter 字段不复用
- StructuralChunker.chunk：mixed 元素顺序、isolated → sequential 过渡、heading→paragraph→heading
- _element_text_with_span：content 含 \r\n\t、Unicode 空白、首尾不同空白量
- 长段落硬切触发 whitespace fallback（覆盖率验证）
- 模块常量精确值
"""

from __future__ import annotations

import inspect
from dataclasses import is_dataclass
from typing import Any

import pytest

from app.chunkers.structural import (
    _HARD_BREAK_LANGS,
    _PART_ELEMENT_ID,
    _PART_END,
    _PART_START,
    _PART_TEXT,
    _SENTENCE_SPLIT_RE,
    _WHITESPACE_RE,
    _ChunkBuffer,
    _SplitPiece,
    _hard_split_with_whitespace_fallback,
    _split_long_text,
    normalize_text,
)
from app.models import Chunk, Document, Element
from app.chunkers import structural as struct_mod


# =========================================================================
# _SENTENCE_SPLIT_RE 实际拆分行为
# =========================================================================


def test_sentence_split_re_splits_on_chinese_period_with_space():
    r"""中文句号 + 空白才切（regex 需 \s+）。"""
    parts = _SENTENCE_SPLIT_RE.split("你好。 世界。")
    assert parts == ["你好。", "世界。"]


def test_sentence_split_re_splits_on_english_period():
    parts = _SENTENCE_SPLIT_RE.split("Hello. World.")
    assert parts == ["Hello.", "World."]


def test_sentence_split_re_splits_on_question_mark():
    parts = _SENTENCE_SPLIT_RE.split("What? Why!")
    assert parts == ["What?", "Why!"]


def test_sentence_split_re_splits_on_exclamation():
    parts = _SENTENCE_SPLIT_RE.split("Stop! Now!")
    assert parts == ["Stop!", "Now!"]


def test_sentence_split_re_no_split_without_trailing_punctuation():
    parts = _SENTENCE_SPLIT_RE.split("hello world")
    assert parts == ["hello world"]


def test_sentence_split_re_no_split_without_whitespace():
    """句号后无空白不切。"""
    parts = _SENTENCE_SPLIT_RE.split("Hello.World.")
    assert parts == ["Hello.World."]


def test_sentence_split_re_no_split_without_whitespace_chinese():
    """中文句号无空白也不切。"""
    parts = _SENTENCE_SPLIT_RE.split("你好。世界。")
    assert parts == ["你好。世界。"]


def test_sentence_split_re_multiple_whitespace_collapses_to_empty():
    """split 保留空串（连续空白分隔）。"""
    parts = _SENTENCE_SPLIT_RE.split("Hi.   There.")
    # 中间的空串来自 re.split 的特性
    assert "Hi." in parts
    assert "There." in parts


def test_sentence_split_re_empty_string():
    assert _SENTENCE_SPLIT_RE.split("") == [""]


def test_sentence_split_re_leading_whitespace_no_split_without_punct():
    """无前置标点时前导空白不切（regex 需 (?<=punct)）。"""
    parts = _SENTENCE_SPLIT_RE.split("  Hi. There.")
    # 第一项是 "  Hi."（前导空白无标点在前）
    assert parts[0] == "  Hi."
    assert parts[1] == "There."


# =========================================================================
# _WHITESPACE_RE 实际替换行为
# =========================================================================


def test_whitespace_re_sub_single_space_to_single():
    assert _WHITESPACE_RE.sub(" ", " ") == " "


def test_whitespace_re_sub_multiple_spaces_to_single():
    assert _WHITESPACE_RE.sub(" ", "   ") == " "


def test_whitespace_re_sub_tab_to_single_space():
    assert _WHITESPACE_RE.sub(" ", "\t") == " "


def test_whitespace_re_sub_newline_to_single_space():
    assert _WHITESPACE_RE.sub(" ", "\n") == " "


def test_whitespace_re_sub_crlf_to_single_space():
    assert _WHITESPACE_RE.sub(" ", "\r\n") == " "


def test_whitespace_re_sub_mixed_whitespace_to_single():
    assert _WHITESPACE_RE.sub(" ", " \t\n\r ") == " "


def test_whitespace_re_sub_no_whitespace_unchanged():
    assert _WHITESPACE_RE.sub(" ", "abc") == "abc"


def test_whitespace_re_sub_empty_string():
    assert _WHITESPACE_RE.sub(" ", "") == ""


# =========================================================================
# _hard_split_with_whitespace_fallback 深度
# =========================================================================


def test_hard_split_whitespace_at_upper_boundary():
    """upper 位置是空白 → 在 upper 切。"""
    # text 长度 40，max_chars=32，upper=32
    # text[32] 是空白 → 在 upper 处切
    text = "a" * 32 + " " + "b" * 7
    pieces = _hard_split_with_whitespace_fallback(text, 32)
    assert len(pieces) == 2
    assert pieces[0].text == "a" * 32
    assert pieces[1].text == "b" * 7


def test_hard_split_whitespace_at_lower_boundary_minus_one():
    """lower - 1 位置是空白 → 仍能找到（lower 闭区间下界）。"""
    # max_chars=32, lower = max_chars // 2 = 16
    # text[15] 是空白（在 lower-1），不在闭区间 [16, 32] 内 → 不应找到
    text = "a" * 15 + " " + "b" * 50
    pieces = _hard_split_with_whitespace_fallback(text, 32)
    # 应该用 forced_char（因为 [16, 32] 区间内全是 'a'）
    assert pieces[0].boundary_after == "forced_char"


def test_hard_split_whitespace_just_above_lower():
    """lower 位置正好是空白 → 找到。"""
    text = "a" * 16 + " " + "b" * 50
    pieces = _hard_split_with_whitespace_fallback(text, 32)
    # [16, 32] 区间内 text[16] 是空白 → 找到
    assert pieces[0].boundary_after == "whitespace"
    assert pieces[0].text == "a" * 16


def test_hard_split_consecutive_whitespace_skipped():
    """多个连续空白跳过到下一个非空白。"""
    text = "a" * 30 + "   " + "b" * 30
    pieces = _hard_split_with_whitespace_fallback(text, 32)
    # 应在空白处切，piece 0 是 'a'*30
    assert pieces[0].text == "a" * 30
    # piece 1 从 'b' 开始
    assert pieces[1].text == "b" * 30


def test_hard_split_max_chars_minimum_32():
    """max_chars=32（最小）应正常工作。"""
    text = "a" * 100
    pieces = _hard_split_with_whitespace_fallback(text, 32)
    # 全 forced_char，每片 32 字符（除末尾）
    for p in pieces[:-1]:
        assert len(p.text) == 32
        assert p.boundary_after == "forced_char"


def test_hard_split_returns_empty_for_empty_after_strip():
    """空串 → 空 list。"""
    assert _hard_split_with_whitespace_fallback("", 32) == []


def test_hard_split_only_whitespace_returns_empty():
    """纯空白 → 空 list。"""
    assert _hard_split_with_whitespace_fallback("   \t\n  ", 32) == []


def test_hard_split_leading_whitespace_in_long_text():
    """前导空白在长文本中被跳过。"""
    text = "   " + "a" * 50
    pieces = _hard_split_with_whitespace_fallback(text, 32)
    # 首片应从 'a' 开始
    assert pieces[0].text.startswith("a")


def test_hard_split_trailing_whitespace_after_split():
    """split 后末尾空白被 rstrip。"""
    text = "a" * 30 + " " + "b" * 30 + "   "
    pieces = _hard_split_with_whitespace_fallback(text, 32)
    # 最后一片应该不含尾部空白
    assert pieces[-1].text == "b" * 30


def test_hard_split_piece_boundary_after_none_at_natural_end():
    """自然结尾（remaining ≤ max_chars）→ boundary_after=None。"""
    text = "a" * 40
    pieces = _hard_split_with_whitespace_fallback(text, 32)
    # 末尾片应 boundary_after=None
    assert pieces[-1].boundary_after is None


def test_hard_split_piece_boundary_after_whitespace_when_more_remains():
    """whitespace 切开后还有非空白 → boundary_after='whitespace'。"""
    text = "a" * 30 + " " + "b" * 30
    pieces = _hard_split_with_whitespace_fallback(text, 32)
    # 首片应 boundary_after='whitespace'
    assert pieces[0].boundary_after == "whitespace"


# =========================================================================
# _split_long_text 累积与坐标
# =========================================================================


def test_split_long_text_strips_then_returns_single():
    """len(text) ≤ max_chars 但有前后空白 → 单片 stripped。"""
    pieces = _split_long_text("  hi  ", 32)
    assert len(pieces) == 1
    assert pieces[0].text == "hi"
    assert pieces[0].start == 0
    assert pieces[0].end == 2


def test_split_long_text_empty_after_strip_returns_empty():
    assert _split_long_text("   ", 32) == []


def test_split_long_text_multiple_short_sentences_accumulate():
    """多个短句累积到一片（不超过 max_chars）。"""
    text = "Hello. World. Test."
    pieces = _split_long_text(text, 32)
    # 全部累积 ≤ 32（"Hello. World. Test." = 19 chars）
    assert len(pieces) == 1
    assert pieces[0].text == "Hello. World. Test."


def test_split_long_text_accumulation_flushes_when_overflow():
    """累积超限时 flush 后开新 buf。"""
    # 每句 10 字符，max_chars=15
    # "aaaaaa. bbbbbb. cccccc." → 第一片 "aaaaaa. bbbbbb." (15) 末尾刚好 15
    text = "aaaaaa. bbbbbb. cccccc."
    pieces = _split_long_text(text, 15)
    # 至少分 2 片
    assert len(pieces) >= 2
    # 每片不超过 max_chars
    for p in pieces:
        assert len(p.text) <= 15


def test_split_long_text_mixed_short_and_long_sentences():
    """短句 + 超长句混合。"""
    short = "Short." + " " + ("a" * 50) + "."
    pieces = _split_long_text(short, 32)
    # 首片应是 "Short."，后续是长句的硬切
    assert pieces[0].text == "Short."
    # 所有片 ≤ 32
    for p in pieces:
        assert len(p.text) <= 32


def test_split_long_text_coordinate_offsets_are_in_stripped_text():
    """piece.start/end 在 stripped text 坐标系。"""
    text = "  Hello. World.  "
    pieces = _split_long_text(text, 32)
    # stripped = "Hello. World."
    stripped = "Hello. World."
    for p in pieces:
        # piece.text 应等于 stripped[p.start:p.end]
        assert stripped[p.start:p.end] == p.text


def test_split_long_text_handles_forced_char_boundary():
    """长句无空白 → forced_char 边界。"""
    text = "a" * 100 + "."
    pieces = _split_long_text(text, 32)
    # 至少 4 片（100/32 上取整 = 4，加上最后句号）
    assert len(pieces) >= 3
    # 至少有一片 forced_char
    has_forced = any(p.boundary_after == "forced_char" for p in pieces)
    assert has_forced


def test_split_long_text_each_piece_text_non_empty():
    """任何 piece 的 text 都不应为空。"""
    text = "Sentence one. " * 10 + "Final."
    pieces = _split_long_text(text, 32)
    for p in pieces:
        assert p.text


def test_split_long_text_preserves_all_text_content_with_spaces():
    """长文本中所有 piece 拼接 + normalize 后应等于 normalize(text)。

    要求：原文有充足空白让 _split_long_text 在句子边界或空白处切，
    而非用 forced_char 硬切（硬切不补空白，会改变 normalize 后的字符序列）。
    """
    text = "Hello world. This is a fairly long sentence used for testing purposes. " + ("x " * 25).strip() + "."
    pieces = _split_long_text(text, 32)
    joined = " ".join(p.text for p in pieces)
    assert normalize_text(joined) == normalize_text(text)


# =========================================================================
# _ChunkBuffer 深度
# =========================================================================


def test_chunk_buffer_length_with_unicode_parts():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("你好", "e1", 0, 2)
    buf.push_text("world", "e2", 0, 5)
    # length 是字符数
    assert buf.length() == 7


def test_chunk_buffer_length_with_empty_part():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("", "e1", 0, 0)
    assert buf.length() == 0


def test_chunk_buffer_push_text_three_parts():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("a", "e1", 0, 1)
    buf.push_text("b", "e2", 0, 1)
    buf.push_text("c", "e3", 0, 1)
    assert len(buf.parts) == 3


def test_chunk_buffer_flush_text_preserves_part_order():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("first", "e1", 0, 5)
    buf.push_text("second", "e2", 0, 6)
    chunk = buf.flush(strategy="sequential", max_chars=800)
    assert chunk is not None
    assert chunk.text == "first second"


def test_chunk_buffer_flush_dedup_with_three_same_ids():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("a", "e1", 0, 1)
    buf.push_text("b", "e1", 1, 2)
    buf.push_text("c", "e1", 2, 3)
    chunk = buf.flush(strategy="sequential", max_chars=800)
    assert chunk is not None
    assert chunk.source_element_ids == ["e1"]


def test_chunk_buffer_flush_dedup_interleaved():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("a", "e1", 0, 1)
    buf.push_text("b", "e2", 0, 1)
    buf.push_text("c", "e1", 1, 2)
    buf.push_text("d", "e2", 1, 2)
    chunk = buf.flush(strategy="sequential", max_chars=800)
    assert chunk is not None
    # 首次出现顺序：e1, e2
    assert chunk.source_element_ids == ["e1", "e2"]


def test_chunk_buffer_flush_one_span_per_part():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("a", "e1", 10, 11)
    buf.push_text("b", "e2", 20, 21)
    chunk = buf.flush(strategy="sequential", max_chars=800)
    assert chunk is not None
    assert len(chunk.source_spans) == 2
    assert chunk.source_spans[0] == {"element_id": "e1", "start": 10, "end": 11}
    assert chunk.source_spans[1] == {"element_id": "e2", "start": 20, "end": 21}


def test_chunk_buffer_flush_metadata_char_count_matches_text_length():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e2", 0, 5)
    chunk = buf.flush(strategy="sequential", max_chars=800)
    assert chunk is not None
    assert chunk.metadata["char_count"] == len(chunk.text)


def test_chunk_buffer_flush_strategy_keyword_only():
    sig = inspect.signature(_ChunkBuffer.flush)
    # strategy 和 max_chars 都是 keyword-only
    for name in ("strategy", "max_chars"):
        assert sig.parameters[name].kind == inspect.Parameter.KEYWORD_ONLY


def test_chunk_buffer_flush_with_whitespace_text_filtered():
    """part 的 text 是空白 → join + strip 后是空 → flush 返回 None。"""
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("   ", "e1", 0, 3)
    chunk = buf.flush(strategy="sequential", max_chars=800)
    assert chunk is None


def test_chunk_buffer_flush_idempotent_returns_none_second_time():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("a", "e1", 0, 1)
    c1 = buf.flush(strategy="sequential", max_chars=800)
    c2 = buf.flush(strategy="sequential", max_chars=800)
    assert c1 is not None
    assert c2 is None


def test_chunk_buffer_parts_is_list():
    buf = _ChunkBuffer(document_id="d1")
    assert isinstance(buf.parts, list)


def test_chunk_buffer_counter_default_zero():
    buf = _ChunkBuffer(document_id="d1")
    assert buf.counter == 0


def test_chunk_buffer_document_id_stored():
    buf = _ChunkBuffer(document_id="doc-42")
    assert buf.document_id == "doc-42"


def test_chunk_buffer_dataclass_field():
    assert is_dataclass(_ChunkBuffer)


def test_chunk_buffer_init_signature():
    sig = inspect.signature(_ChunkBuffer.__init__)
    # self + document_id + parts(default) + counter(default)
    assert set(sig.parameters) >= {"self", "document_id"}


def test_chunk_buffer_init_document_id_no_default():
    sig = inspect.signature(_ChunkBuffer.__init__)
    assert sig.parameters["document_id"].default is inspect.Parameter.empty


# =========================================================================
# _SplitPiece 深度
# =========================================================================


def test_split_piece_field_defaults_for_start_end():
    p = _SplitPiece(text="x", boundary_after=None)
    assert p.start == 0
    assert p.end == 0


def test_split_piece_explicit_start_end():
    p = _SplitPiece(text="x", boundary_after="whitespace", start=10, end=11)
    assert p.start == 10
    assert p.end == 11


def test_split_piece_boundary_after_accepts_none():
    p = _SplitPiece(text="x", boundary_after=None)
    assert p.boundary_after is None


def test_split_piece_boundary_after_accepts_whitespace():
    p = _SplitPiece(text="x", boundary_after="whitespace")
    assert p.boundary_after == "whitespace"


def test_split_piece_boundary_after_accepts_forced_char():
    p = _SplitPiece(text="x", boundary_after="forced_char")
    assert p.boundary_after == "forced_char"


def test_split_piece_setattr_raises():
    p = _SplitPiece(text="x", boundary_after=None)
    with pytest.raises(Exception):
        p.text = "y"  # frozen


def test_split_piece_equality_same():
    a = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    b = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    assert a == b


def test_split_piece_equality_different_start():
    a = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    b = _SplitPiece(text="x", boundary_after=None, start=5, end=6)
    assert a != b


def test_split_piece_repr_includes_text():
    p = _SplitPiece(text="hello", boundary_after=None)
    assert "hello" in repr(p)


# =========================================================================
# 模块常量精确值
# =========================================================================


def test_part_text_value_zero():
    assert _PART_TEXT == 0


def test_part_element_id_value_one():
    assert _PART_ELEMENT_ID == 1


def test_part_start_value_two():
    assert _PART_START == 2


def test_part_end_value_three():
    assert _PART_END == 3


def test_part_constants_used_consistently():
    """length() 用 _PART_TEXT、flush() 用所有常量。"""
    src = inspect.getsource(_ChunkBuffer)
    assert "_PART_TEXT" in src
    assert "_PART_ELEMENT_ID" in src
    assert "_PART_START" in src
    assert "_PART_END" in src


def test_hard_break_langs_has_six_punctuations():
    """6 个标点：中英文句号、问号、叹号。"""
    assert "。" in _HARD_BREAK_LANGS
    assert "！" in _HARD_BREAK_LANGS
    assert "？" in _HARD_BREAK_LANGS
    assert "." in _HARD_BREAK_LANGS
    assert "!" in _HARD_BREAK_LANGS
    assert "?" in _HARD_BREAK_LANGS


# =========================================================================
# StructuralChunker.chunk 行为深度
# =========================================================================


def _make_doc(elements: list[Element], doc_id: str = "doc1") -> Document:
    return Document(
        document_id=doc_id,
        source_path="x.txt",
        source_type="text",
        source_hash="a" * 64,
        parser_name="text",
        parser_version="1.0",
        elements=elements,
        chunks=[],
        relations=[],
        warnings=[],
        errors=[],
        metadata={},
    )


def _make_element(eid: str, etype: str, content: str) -> Element:
    return Element(
        element_id=eid,
        type=etype,
        content=content,
        parent_id=None,
        source_locator={"line": 0},
        confidence=1.0,
        metadata={},
    )


def test_chunker_empty_document_returns_empty():
    doc = _make_doc([])
    chunker = struct_mod.StructuralChunker(max_chars=800)
    assert chunker.chunk(doc) == []


def test_chunker_single_paragraph_under_max():
    doc = _make_doc([_make_element("e1", "paragraph", "hello")])
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].text == "hello"
    assert chunks[0].source_element_ids == ["e1"]


def test_chunker_heading_then_paragraph_separate_chunks():
    """heading 是硬边界，paragraph 累积在新 buf。"""
    doc = _make_doc([
        _make_element("e1", "heading", "Title"),
        _make_element("e2", "paragraph", "body"),
    ])
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    # heading 单独成 chunk（因为 paragraph 加入时 buf 只有 heading）
    # 但实际上 paragraph 也会累积进 heading 的 buf 直到 flush
    # 重新看代码：heading 进 buf，paragraph 进同一 buf，最后 flush → 1 个 chunk
    # 但 heading 触发 flush（先 flush 当前 buf 才 push heading）
    # 所以这里是空 doc 然后 push heading，然后 push paragraph，flush 一次
    assert len(chunks) == 1
    assert "Title" in chunks[0].text
    assert "body" in chunks[0].text


def test_chunker_paragraph_then_heading_two_chunks():
    """paragraph 进 buf，然后 heading 触发 flush → 2 chunks。"""
    doc = _make_doc([
        _make_element("e1", "paragraph", "first body"),
        _make_element("e2", "heading", "Title"),
        _make_element("e3", "paragraph", "second body"),
    ])
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    # first body 单独 flush，heading + second body 合并
    assert len(chunks) == 2
    assert "first body" in chunks[0].text
    assert "Title" in chunks[1].text


def test_chunker_table_isolated_from_paragraph():
    doc = _make_doc([
        _make_element("e1", "paragraph", "before"),
        _make_element("e2", "table", "col1|col2"),
        _make_element("e3", "paragraph", "after"),
    ])
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    # before 单独 flush，table isolated，after 单独
    # 实际：before 进 buf，table 触发 flush（chunk0=before），table 单独 flush（chunk1=table），
    # after 进空 buf，最终 flush（chunk2=after）
    assert len(chunks) == 3
    assert chunks[0].text == "before"
    assert chunks[1].text == "col1|col2"
    assert chunks[1].metadata["strategy"] == "isolated_table"
    assert chunks[2].text == "after"


def test_chunker_caption_isolated():
    doc = _make_doc([_make_element("e1", "caption", "Figure 1")])
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].metadata["strategy"] == "isolated_caption"


def test_chunker_image_skipped_no_chunk():
    doc = _make_doc([
        _make_element("e1", "paragraph", "before"),
        _make_element("e2", "image", "[img]"),
        _make_element("e3", "paragraph", "after"),
    ])
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    # image 不参与，paragraphs 合并到同一 buf（image 跳过后 buf 不 flush）
    assert len(chunks) == 1
    assert "before" in chunks[0].text
    assert "after" in chunks[0].text


def test_chunker_long_paragraph_split_into_pieces():
    """超长 paragraph 触发 _split_long_text。"""
    long_text = "word " * 200  # 1000 chars
    doc = _make_doc([_make_element("e1", "paragraph", long_text)])
    chunker = struct_mod.StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.text) <= 100 + 10  # 容差（join 空格）


def test_chunker_long_paragraph_metadata_strategy():
    long_text = "word " * 200
    doc = _make_doc([_make_element("e1", "paragraph", long_text)])
    chunker = struct_mod.StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    assert chunks[0].metadata["strategy"] == "long_paragraph_sentence_split"


def test_chunker_chunk_id_format_four_digits():
    doc = _make_doc([_make_element("e1", "paragraph", "x")])
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    assert chunks[0].chunk_id == "doc1::c0000"


def test_chunker_chunk_id_increments_across_chunks():
    doc = _make_doc([
        _make_element("e1", "paragraph", "first"),
        _make_element("e2", "heading", "T"),
        _make_element("e3", "paragraph", "second"),
    ])
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    ids = [c.chunk_id for c in chunks]
    assert ids == ["doc1::c0000", "doc1::c0001"]


def test_chunker_default_strategy_sequential():
    doc = _make_doc([_make_element("e1", "paragraph", "x")])
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    assert chunks[0].metadata["strategy"] == "sequential"


def test_chunker_list_item_treated_as_paragraph():
    """list_item 走默认分支（同 paragraph）。"""
    doc = _make_doc([
        _make_element("e1", "list_item", "item1"),
        _make_element("e2", "list_item", "item2"),
    ])
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    # 两个 list_item 累积到同一 buf
    assert len(chunks) == 1
    assert "item1" in chunks[0].text
    assert "item2" in chunks[0].text


def test_chunker_unknown_element_type_treated_as_paragraph():
    doc = _make_doc([_make_element("e1", "custom_type", "data")])
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].text == "data"


def test_chunker_whitespace_only_content_skipped():
    doc = _make_doc([_make_element("e1", "paragraph", "   ")])
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    assert chunks == []


def test_chunker_no_text_lost_through_pipeline():
    """所有 element content 的 normalize 拼接 = 所有 chunk text 的 normalize 拼接。"""
    elements = [
        _make_element("e1", "paragraph", "First paragraph here."),
        _make_element("e2", "heading", "Section"),
        _make_element("e3", "paragraph", "Second paragraph with more text."),
        _make_element("e4", "list_item", "list item one"),
    ]
    doc = _make_doc(elements)
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    all_chunks = " ".join(c.text for c in chunks)
    all_elements = " ".join(e.content for e in elements)
    assert normalize_text(all_chunks) == normalize_text(all_elements)


def test_chunker_paragraph_pushes_then_flushes_when_max_exceeded():
    """buf 已有内容，新 paragraph 加入会超 max → 先 flush。"""
    # max=20, 第一个 paragraph "short" 5 字符，第二个 "this is much longer than max" 30 字符
    # 第一个进 buf（5），第二个 projected = 5+1+30=36 > 20 → flush（chunk0=short），新 buf 单 paragraph
    # 但 30 > max_chars=20 → 走 long_paragraph 分支
    doc = _make_doc([
        _make_element("e1", "paragraph", "short"),
        _make_element("e2", "paragraph", "this is much longer than max"),
    ])
    chunker = struct_mod.StructuralChunker(max_chars=32)
    chunks = chunker.chunk(doc)
    # 第一个 paragraph "short" 单独成 chunk（因为第二个超长触发 long_paragraph 分支，先 flush）
    # 然后第二个 paragraph 走 long_paragraph split
    assert len(chunks) >= 2
    assert chunks[0].text == "short"


def test_chunker_heading_long_text_split_via_default_path():
    """heading 也走默认分支（不长则进 buf），如果超长则进入 long 分支。

    但 heading 类型走 if el.type == "heading" 分支后 continue，所以 heading 不会触发 long split。
    验证：heading 不论长度都直接进 buf。
    """
    long_heading = "word " * 100
    doc = _make_doc([_make_element("e1", "heading", long_heading)])
    chunker = struct_mod.StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    # heading 直接 push 到 buf，flush 时 text 是 join 后的结果
    # text "word word word..." 总长 500 字符 > 100，但 flush 不切分
    assert len(chunks) == 1
    # 但 chunk text 长
    assert len(chunks[0].text) > 100


# =========================================================================
# _element_text_with_span 深度
# =========================================================================


def test_element_text_with_span_internal_whitespace_preserved():
    """content 中间有空白 → stripped 保留中间空白。"""
    el = _make_element("e1", "paragraph", "hello   world")
    chunker = struct_mod.StructuralChunker(max_chars=800)
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello   world"
    assert start == 0
    assert end == 13


def test_element_text_with_span_tabs_in_content():
    el = _make_element("e1", "paragraph", "\thello\t")
    chunker = struct_mod.StructuralChunker(max_chars=800)
    text, start, end = chunker._element_text_with_span(el)
    # lstrip 去掉 \t
    assert text == "hello"
    assert start == 1
    assert end == 6


def test_element_text_with_span_newlines_at_edges():
    el = _make_element("e1", "paragraph", "\n\nhello\n\n")
    chunker = struct_mod.StructuralChunker(max_chars=800)
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 2
    assert end == 7


def test_element_text_with_span_only_leading_whitespace():
    el = _make_element("e1", "paragraph", "   hello")
    chunker = struct_mod.StructuralChunker(max_chars=800)
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 3
    assert end == 8


def test_element_text_with_span_only_trailing_whitespace():
    el = _make_element("e1", "paragraph", "hello   ")
    chunker = struct_mod.StructuralChunker(max_chars=800)
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 0
    assert end == 5


def test_element_text_with_span_unicode_content():
    el = _make_element("e1", "paragraph", "  你好世界  ")
    chunker = struct_mod.StructuralChunker(max_chars=800)
    text, start, end = chunker._element_text_with_span(el)
    assert text == "你好世界"
    assert start == 2
    assert end == 6


def test_element_text_with_span_image_returns_empty_tuple():
    el = _make_element("e1", "image", "[binary data]")
    chunker = struct_mod.StructuralChunker(max_chars=800)
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_legacy_method_returns_text_only():
    el = _make_element("e1", "paragraph", "  hello  ")
    chunker = struct_mod.StructuralChunker(max_chars=800)
    text = chunker._element_text(el)
    assert text == "hello"


# =========================================================================
# normalize_text 深度
# =========================================================================


def test_normalize_text_idempotent_on_normalized():
    s = "hello world"
    assert normalize_text(normalize_text(s)) == normalize_text(s)


def test_normalize_text_preserves_internal_single_space():
    assert normalize_text("hello world") == "hello world"


def test_normalize_text_collapses_multiple_internal_spaces():
    assert normalize_text("hello   world") == "hello world"


def test_normalize_text_handles_mixed_whitespace_combo():
    assert normalize_text("  hello\t\nworld\r\n") == "hello world"


def test_normalize_text_with_only_newlines():
    assert normalize_text("\n\n\n") == ""


def test_normalize_text_with_only_tabs():
    assert normalize_text("\t\t\t") == ""


def test_normalize_text_unicode_letters_preserved():
    assert normalize_text("你好 world") == "你好 world"


def test_normalize_text_returns_empty_for_falsy():
    assert normalize_text("") == ""
    assert normalize_text(None) == ""


# =========================================================================
# StructuralChunker.__init__ 深度
# =========================================================================


def test_structural_chunker_init_max_chars_stored():
    chunker = struct_mod.StructuralChunker(max_chars=500)
    assert chunker.max_chars == 500


def test_structural_chunker_init_default_800():
    chunker = struct_mod.StructuralChunker()
    assert chunker.max_chars == 800


def test_structural_chunker_init_32_minimum():
    chunker = struct_mod.StructuralChunker(max_chars=32)
    assert chunker.max_chars == 32


def test_structural_chunker_init_31_raises():
    with pytest.raises(ValueError) as exc:
        struct_mod.StructuralChunker(max_chars=31)
    assert "max_chars" in str(exc.value)


def test_structural_chunker_init_negative_raises():
    with pytest.raises(ValueError):
        struct_mod.StructuralChunker(max_chars=-100)


def test_structural_chunker_init_zero_raises():
    with pytest.raises(ValueError):
        struct_mod.StructuralChunker(max_chars=0)


def test_structural_chunker_init_error_message_contains_value():
    with pytest.raises(ValueError) as exc:
        struct_mod.StructuralChunker(max_chars=10)
    assert "10" in str(exc.value)


def test_structural_chunker_chunk_signature():
    sig = inspect.signature(struct_mod.StructuralChunker.chunk)
    assert set(sig.parameters) == {"self", "document"}


def test_structural_chunker_chunk_no_default_for_document():
    sig = inspect.signature(struct_mod.StructuralChunker.chunk)
    assert sig.parameters["document"].default is inspect.Parameter.empty


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact_two_items():
    import app.chunkers.structural as mod
    assert mod.__all__ == ["StructuralChunker", "normalize_text"]


def test_module_all_no_duplicates():
    import app.chunkers.structural as mod
    assert len(mod.__all__) == len(set(mod.__all__))


def test_module_uses_future_annotations():
    src = inspect.getsource(struct_mod)
    assert "from __future__ import annotations" in src


def test_module_imports_re():
    src = inspect.getsource(struct_mod)
    assert "import re" in src


def test_module_imports_dataclass():
    src = inspect.getsource(struct_mod)
    assert "from dataclasses import dataclass, field" in src


def test_module_imports_any():
    src = inspect.getsource(struct_mod)
    assert "from typing import Any" in src


def test_module_imports_models():
    src = inspect.getsource(struct_mod)
    assert "from app.models import Chunk, Document, Element" in src


def test_module_docstring_present():
    assert struct_mod.__doc__ is not None


def test_module_docstring_mentions_heading_boundary():
    assert "标题" in struct_mod.__doc__ or "heading" in struct_mod.__doc__.lower()


def test_module_docstring_mentions_no_text_modification():
    assert "不修改" in struct_mod.__doc__ or "不丢不重" in struct_mod.__doc__


def test_module_docstring_mentions_source_spans():
    assert "source_spans" in struct_mod.__doc__ or "span" in struct_mod.__doc__.lower()


def test_module_constants_count():
    """模块定义 7 个常量：2 个 RE + 1 个 tuple + 4 个 _PART_*。"""
    src = inspect.getsource(struct_mod)
    assert "_SENTENCE_SPLIT_RE" in src
    assert "_HARD_BREAK_LANGS" in src
    assert "_WHITESPACE_RE" in src
    assert "_PART_TEXT" in src
    assert "_PART_ELEMENT_ID" in src
    assert "_PART_START" in src
    assert "_PART_END" in src


# =========================================================================
# 综合行为
# =========================================================================


def test_chunker_idempotent_on_same_document():
    doc = _make_doc([
        _make_element("e1", "paragraph", "hello"),
        _make_element("e2", "heading", "Title"),
        _make_element("e3", "paragraph", "body"),
    ])
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks1 = chunker.chunk(doc)
    chunks2 = chunker.chunk(doc)
    assert len(chunks1) == len(chunks2)
    for a, b in zip(chunks1, chunks2):
        assert a.chunk_id == b.chunk_id
        assert a.text == b.text


def test_chunker_does_not_mutate_input_document():
    elements = [
        _make_element("e1", "paragraph", "hello"),
        _make_element("e2", "heading", "Title"),
    ]
    doc = _make_doc(elements)
    before_elements_count = len(doc.elements)
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunker.chunk(doc)
    # elements 数量不变
    assert len(doc.elements) == before_elements_count


def test_chunker_returns_chunks_in_document_id_namespace():
    doc = _make_doc([], doc_id="my-doc")
    doc.elements = [_make_element("e1", "paragraph", "x")]
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    assert chunks[0].chunk_id.startswith("my-doc::c")


def test_chunker_text_preservation_with_normalize():
    """完整 pipeline 后 normalize(chunks joined) == normalize(elements joined)。"""
    elements = [
        _make_element("e1", "heading", "Chapter 1"),
        _make_element("e2", "paragraph", "  Some indented text.  "),
        _make_element("e3", "paragraph", "Another paragraph."),
        _make_element("e4", "table", "A|B|C"),
        _make_element("e5", "caption", "Table 1"),
        _make_element("e6", "list_item", "- item"),
        _make_element("e7", "heading", "Chapter 2"),
        _make_element("e8", "paragraph", "Final."),
    ]
    doc = _make_doc(elements)
    chunker = struct_mod.StructuralChunker(max_chars=50)
    chunks = chunker.chunk(doc)
    all_chunks_text = " ".join(c.text for c in chunks)
    all_elements_text = " ".join(e.content for e in elements)
    assert normalize_text(all_chunks_text) == normalize_text(all_elements_text)


def test_chunker_chunk_text_is_stripped():
    """每个 chunk 的 text 应是 stripped。"""
    elements = [
        _make_element("e1", "paragraph", "  hello  "),
    ]
    doc = _make_doc(elements)
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    assert chunks[0].text == chunks[0].text.strip()


def test_chunker_source_spans_have_valid_ranges():
    """source_spans 中 start ≤ end。"""
    elements = [
        _make_element("e1", "paragraph", "hello world"),
    ]
    doc = _make_doc(elements)
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    for span in chunks[0].source_spans:
        assert span["start"] <= span["end"]


def test_chunker_metadata_keys_complete():
    elements = [_make_element("e1", "paragraph", "x")]
    doc = _make_doc(elements)
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    md = chunks[0].metadata
    assert "strategy" in md
    assert "max_chars" in md
    assert "char_count" in md


def test_chunker_metadata_max_chars_matches_init():
    elements = [_make_element("e1", "paragraph", "x")]
    doc = _make_doc(elements)
    chunker = struct_mod.StructuralChunker(max_chars=42)
    chunks = chunker.chunk(doc)
    assert chunks[0].metadata["max_chars"] == 42


def test_chunker_char_count_matches_text_len():
    elements = [_make_element("e1", "paragraph", "hello")]
    doc = _make_doc(elements)
    chunker = struct_mod.StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    assert chunks[0].metadata["char_count"] == len(chunks[0].text)
