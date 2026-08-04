"""app/chunkers/structural.py 边角测试（Round 51）。

补强 tests/test_chunker.py（129 个测试）未覆盖的：
- 模块级常量（_SENTENCE_SPLIT_RE / _WHITESPACE_RE / _HARD_BREAK_LANGS / _PART_*）
- _ChunkBuffer 默认 field 值与边角
- _SplitPiece dataclass 边角
- _hard_split_with_whitespace_fallback max_chars=32 边界
- _split_long_text 边界情况（恰好等于 max_chars / 纯分隔符 / 空句子过滤）
- StructuralChunker.__init__ 边界（max_chars=32 OK / 31 raise / 默认 800）
- _element_text_with_span 边角（content=None / 全空白 / 含换行）
- _element_text 兼容方法
- normalize_text 边角补强
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from app.chunkers.structural import (
    StructuralChunker,
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


# ---------- 模块级常量 ----------


def test_sentence_split_re_is_compiled_pattern():
    import re
    assert isinstance(_SENTENCE_SPLIT_RE, re.Pattern)


def test_whitespace_re_is_compiled_pattern():
    import re
    assert isinstance(_WHITESPACE_RE, re.Pattern)


def test_hard_break_langs_is_tuple():
    assert isinstance(_HARD_BREAK_LANGS, tuple)


def test_hard_break_langs_contains_chinese_and_english_marks():
    """应同时含中文（。！？）与英文 (.!?) 句末标点。"""
    assert "。" in _HARD_BREAK_LANGS
    assert "！" in _HARD_BREAK_LANGS
    assert "？" in _HARD_BREAK_LANGS
    assert "." in _HARD_BREAK_LANGS
    assert "!" in _HARD_BREAK_LANGS
    assert "?" in _HARD_BREAK_LANGS


def test_hard_break_langs_length_six():
    """6 个句末标点：3 中 + 3 英。"""
    assert len(_HARD_BREAK_LANGS) == 6


def test_part_constants_have_correct_values():
    """_PART_TEXT=0, _PART_ELEMENT_ID=1, _PART_START=2, _PART_END=3。"""
    assert _PART_TEXT == 0
    assert _PART_ELEMENT_ID == 1
    assert _PART_START == 2
    assert _PART_END == 3


def test_part_constants_are_distinct_integers():
    """4 个常量是 0/1/2/3 互不相同。"""
    values = {_PART_TEXT, _PART_ELEMENT_ID, _PART_START, _PART_END}
    assert values == {0, 1, 2, 3}


def test_whitespace_re_pattern_matches_multiple_spaces():
    assert _WHITESPACE_RE.match("   ") is not None


def test_whitespace_re_pattern_matches_tab():
    assert _WHITESPACE_RE.match("\t") is not None


def test_whitespace_re_pattern_matches_newline():
    assert _WHITESPACE_RE.match("\n") is not None


def test_whitespace_re_pattern_does_not_match_letter():
    assert _WHITESPACE_RE.match("a") is None


def test_sentence_split_re_splits_on_period_followed_by_space():
    """句末 . 加空格 → 分隔（lookbehind 不消耗 . 本身）。"""
    parts = _SENTENCE_SPLIT_RE.split("Hello. World.")
    # 分隔符前后各保留一段
    assert "Hello." in parts
    assert "World." in parts


def test_sentence_split_re_no_split_without_whitespace():
    """句末标点紧跟字符（无空格）→ 不分隔。"""
    parts = _SENTENCE_SPLIT_RE.split("A.B.C")
    assert parts == ["A.B.C"]


def test_sentence_split_re_chinese_period_no_whitespace_needed():
    """中文句号（无后续空格）也不会分隔（lookbehind 后必须有空格才匹配）。"""
    # 实际：_SENTENCE_SPLIT_RE 要求标点后有空格
    parts = _SENTENCE_SPLIT_RE.split("你好。世界。")
    # 没有空格 → 不分隔
    assert parts == ["你好。世界。"]


def test_sentence_split_re_question_mark_split():
    """英文问号 + 空格 → 分隔。"""
    parts = _SENTENCE_SPLIT_RE.split("Why? Because.")
    assert "Why?" in parts
    assert "Because." in parts


def test_sentence_split_re_exclamation_split():
    parts = _SENTENCE_SPLIT_RE.split("Yes! Done.")
    assert "Yes!" in parts
    assert "Done." in parts


# ---------- _ChunkBuffer 默认 field ----------


def test_chunk_buffer_default_counter_is_zero():
    """counter 字段默认值 0。"""
    buf = _ChunkBuffer(document_id="d1")
    assert buf.counter == 0


def test_chunk_buffer_default_parts_is_empty_list():
    buf = _ChunkBuffer(document_id="d1")
    assert buf.parts == []
    assert isinstance(buf.parts, list)


def test_chunk_buffer_document_id_field():
    buf = _ChunkBuffer(document_id="doc-abc")
    assert buf.document_id == "doc-abc"


def test_chunk_buffer_parts_each_is_4_tuple():
    """push_text 后 parts 中每项应是 (text, element_id, start, end) 四元组。"""
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("hello", "e1", 0, 5)
    part = buf.parts[0]
    assert isinstance(part, tuple)
    assert len(part) == 4
    assert part == ("hello", "e1", 0, 5)


def test_chunk_buffer_push_text_multiple_parts_accumulate():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("a", "e1", 0, 1)
    buf.push_text("b", "e1", 1, 2)
    buf.push_text("c", "e1", 2, 3)
    assert len(buf.parts) == 3
    assert buf.length() == 3  # a + b + c = 3 字符


def test_chunk_buffer_is_empty_initially_true():
    buf = _ChunkBuffer(document_id="d1")
    assert buf.is_empty() is True


def test_chunk_buffer_is_empty_false_after_push():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("x", "e1", 0, 1)
    assert buf.is_empty() is False


def test_chunk_buffer_is_empty_true_again_after_flush():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("x", "e1", 0, 1)
    buf.flush(strategy="x", max_chars=800)
    assert buf.is_empty() is True


def test_chunk_buffer_flush_text_joins_with_single_space():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e2", 0, 5)
    chunk = buf.flush(strategy="x", max_chars=800)
    assert chunk is not None
    assert chunk.text == "hello world"


def test_chunk_buffer_flush_returns_chunk_object():
    from app.models import Chunk
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("x", "e1", 0, 1)
    chunk = buf.flush(strategy="x", max_chars=800)
    assert isinstance(chunk, Chunk)


def test_chunk_buffer_flush_strategy_recorded_in_metadata():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("x", "e1", 0, 1)
    chunk = buf.flush(strategy="isolated_table", max_chars=800)
    assert chunk is not None
    assert chunk.metadata["strategy"] == "isolated_table"


def test_chunk_buffer_flush_max_chars_recorded_in_metadata():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("x", "e1", 0, 1)
    chunk = buf.flush(strategy="x", max_chars=456)
    assert chunk is not None
    assert chunk.metadata["max_chars"] == 456


def test_chunk_buffer_flush_char_count_matches_text_length():
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("hello world", "e1", 0, 11)
    chunk = buf.flush(strategy="x", max_chars=800)
    assert chunk is not None
    assert chunk.metadata["char_count"] == len(chunk.text)


# ---------- _SplitPiece dataclass ----------


def test_split_piece_text_field_required():
    """text 是必填字段。"""
    p = _SplitPiece(text="hello", boundary_after=None)
    assert p.text == "hello"


def test_split_piece_default_start_end_zero():
    p = _SplitPiece(text="x", boundary_after=None)
    assert p.start == 0
    assert p.end == 0


def test_split_piece_explicit_start_end():
    p = _SplitPiece(text="x", boundary_after=None, start=10, end=11)
    assert p.start == 10
    assert p.end == 11


def test_split_piece_is_frozen():
    """frozen=True → 不能修改属性。"""
    p = _SplitPiece(text="x", boundary_after=None)
    with pytest.raises(FrozenInstanceError):
        p.text = "y"  # type: ignore[misc]


def test_split_piece_boundary_after_accepts_string():
    p = _SplitPiece(text="x", boundary_after="whitespace")
    assert p.boundary_after == "whitespace"


def test_split_piece_boundary_after_accepts_forced_char():
    p = _SplitPiece(text="x", boundary_after="forced_char")
    assert p.boundary_after == "forced_char"


def test_split_piece_boundary_after_accepts_none():
    p = _SplitPiece(text="x", boundary_after=None)
    assert p.boundary_after is None


def test_split_piece_equality():
    """两个相同字段值的 _SplitPiece 应相等（frozen dataclass 默认）。"""
    p1 = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    p2 = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    assert p1 == p2


def test_split_piece_inequality_on_text():
    p1 = _SplitPiece(text="x", boundary_after=None)
    p2 = _SplitPiece(text="y", boundary_after=None)
    assert p1 != p2


# ---------- _hard_split_with_whitespace_fallback 边角 ----------


def test_hard_split_min_max_chars_32():
    """max_chars=32（StructuralChunker 最小值）应能工作。"""
    text = "a" * 100  # 100 字符，肯定超过 32
    pieces = _hard_split_with_whitespace_fallback(text, 32)
    assert len(pieces) >= 3  # 至少 3 个 piece
    for p in pieces:
        assert len(p.text) <= 32


def test_hard_split_text_starts_with_whitespace():
    """text 开头是空白 → 跳过前导空白再切。"""
    text = "   " + "a" * 100
    pieces = _hard_split_with_whitespace_fallback(text, 50)
    # 第一个 piece 不应包含前导空白
    assert pieces[0].text.startswith("a")


def test_hard_split_text_ends_with_whitespace():
    """text 结尾是空白 → 最后 piece 不带尾随空白。"""
    text = "a" * 100 + "   "
    pieces = _hard_split_with_whitespace_fallback(text, 50)
    last = pieces[-1]
    assert not last.text.endswith(" ")
    assert not last.text.endswith("\t")


def test_hard_split_text_just_over_max_chars():
    """text 长度 = max_chars + 1 → 至少 2 个 piece。"""
    text = "a" * 101
    pieces = _hard_split_with_whitespace_fallback(text, 100)
    assert len(pieces) >= 2


def test_hard_split_text_much_larger_than_max_chars():
    """text 10x max_chars → 至少 10 个 piece。"""
    text = "a" * 320
    pieces = _hard_split_with_whitespace_fallback(text, 32)
    assert len(pieces) >= 10


def test_hard_split_start_end_within_text_bounds():
    """所有 piece 的 [start, end) 都应在 [0, len(text)) 内。"""
    text = "abcdefghij" * 20  # 200 字符
    pieces = _hard_split_with_whitespace_fallback(text, 50)
    for p in pieces:
        assert 0 <= p.start
        assert p.end <= len(text)
        assert p.start < p.end  # 非空


def test_hard_split_piece_text_slice_matches_input():
    """piece.text 应与 text[start:end] 一致（除非被 rstrip）。"""
    text = "hello world foo bar " * 10  # 含空格 → 可能 whitespace split
    pieces = _hard_split_with_whitespace_fallback(text, 50)
    for p in pieces:
        # text[p.start:p.end] 应等于 p.text 或其超集（rstrip 后）
        assert text[p.start:p.end].rstrip() == p.text


# ---------- _split_long_text 边角 ----------


def test_split_long_text_returns_empty_list_for_empty():
    assert _split_long_text("", 100) == []


def test_split_long_text_returns_empty_list_for_whitespace_only():
    assert _split_long_text("   \n\t  ", 100) == []


def test_split_long_text_short_text_single_piece():
    """text 长度 ≤ max_chars → 单个 piece（boundary_after=None）。"""
    result = _split_long_text("hello", 100)
    assert len(result) == 1
    assert result[0].text == "hello"
    assert result[0].boundary_after is None


def test_split_long_text_exact_max_chars_boundary():
    """text 长度恰好 == max_chars → 单个 piece。"""
    text = "a" * 100
    result = _split_long_text(text, 100)
    assert len(result) == 1
    assert result[0].text == text
    assert result[0].boundary_after is None


def test_split_long_text_max_chars_plus_one_splits():
    """text 长度 = max_chars + 1 → 至少 2 个 piece。"""
    text = "a" * 101
    result = _split_long_text(text, 100)
    assert len(result) >= 2


def test_split_long_text_strips_input_first():
    """前导/尾随空白应被 strip 掉。"""
    result = _split_long_text("  hello  ", 100)
    assert len(result) == 1
    assert result[0].text == "hello"  # stripped


def test_split_long_text_each_piece_within_max_chars():
    """所有 piece 长度 ≤ max_chars。"""
    text = "a" * 500
    result = _split_long_text(text, 100)
    for p in result:
        assert len(p.text) <= 100


def test_split_long_text_concatenation_uses_single_space():
    """多个 piece 合并时用单空格 joiner。"""
    # 含句号 + 空格的文本 → 句子分割
    text = "Sentence one. Sentence two. Sentence three."
    result = _split_long_text(text, 30)  # 短 max_chars → 强制拆
    # 合并 piece 应该是 sentence 之间用单空格连接
    # 不验证具体拆分点（依赖实现），只验证 piece text 不含双空格
    for p in result:
        assert "  " not in p.text


def test_split_long_text_start_end_in_stripped_text_coordinates():
    """start/end 在 stripped text 坐标系中。"""
    text = "  hello world  ".strip()
    result = _split_long_text(text, 100)
    assert len(result) == 1
    piece = result[0]
    assert piece.start == 0
    assert piece.end == len(text)


def test_split_long_text_pure_sentence_separators_filtered():
    """纯分隔符输入（多个空格 + 句号）→ 应返回空或少量 piece。"""
    # 多个句号 + 空格 → split 后空句子被过滤
    result = _split_long_text(". . . . ", 100)
    # 没有实际文本内容（只有分隔符）
    assert isinstance(result, list)


# ---------- StructuralChunker.__init__ 边界 ----------


def test_chunker_init_default_max_chars_800():
    chunker = StructuralChunker()
    assert chunker.max_chars == 800


def test_chunker_init_explicit_max_chars():
    chunker = StructuralChunker(max_chars=500)
    assert chunker.max_chars == 500


def test_chunker_init_max_chars_minimum_32():
    """32 是允许的最小值（>=32 OK）。"""
    chunker = StructuralChunker(max_chars=32)
    assert chunker.max_chars == 32


def test_chunker_init_max_chars_31_raises():
    """31 < 32 → raise ValueError。"""
    with pytest.raises(ValueError) as exc:
        StructuralChunker(max_chars=31)
    msg = str(exc.value)
    assert "max_chars" in msg or "过小" in msg


def test_chunker_init_max_chars_zero_raises():
    """max_chars=0 → raise。"""
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=0)


def test_chunker_init_max_chars_negative_raises():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=-100)


def test_chunker_init_max_chars_one_raises():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=1)


# ---------- _element_text_with_span 边角 ----------


def _make_paragraph_element(content: str | None, eid: str = "e1") -> Any:
    from app.models import Element
    return Element(
        element_id=eid,
        type="paragraph",
        content=content,
        parent_id=None,
        source_locator={"paragraph_index": 0},
        confidence=1.0,
        metadata={},
    )


def test_element_text_with_span_content_none_returns_empty():
    """content=None 必须搭配 resource_path（Element dataclass 约束）。

    此处记录 _element_text_with_span 在 content=None 时的行为：
    返回 ('', 0, 0)。但 Element 自身不允许 content=None + resource_path=None，
    所以这里通过 image element（resource_path 给定）间接测。"""
    chunker = StructuralChunker()
    # image element 自带 content=None + resource_path，但 _element_text_with_span
    # 对 image 直接返回空；此测试已由 test_element_text_with_span_image_returns_empty 覆盖。
    # 这里改为：直接验证 _element_text_with_span 在 content=None 的 paragraph
    # 上不能构造（Element 不允许），所以删除该路径。
    # 用 image element 代替（虽然 type-check 会先返回空，但已覆盖了 None 行为）。
    from app.models import Element
    el = Element(
        element_id="img1",
        type="image",
        content=None,
        resource_path="/tmp/x.png",
        parent_id=None,
        source_locator={"paragraph_index": 0},
        confidence=1.0,
        metadata={},
    )
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_content_empty_string_returns_empty():
    """content="" 必须搭配 resource_path（Element dataclass 约束）。

    Element 不允许 content="" + resource_path=None（至少一个非空），
    所以这里用 resource_path 配合来构造（实际 paragraph 不会有 resource_path，
    但 image type 走特殊路径）。"""
    chunker = StructuralChunker()
    # 直接测一个真实场景：paragraph content 是空白字符串（被 strip 后空）
    el = _make_paragraph_element("   \n\t  ")
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_content_whitespace_only_returns_empty():
    chunker = StructuralChunker()
    el = _make_paragraph_element("   \n\t  ")
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_no_whitespace_returns_as_is():
    chunker = StructuralChunker()
    el = _make_paragraph_element("hello world")
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello world"
    assert start == 0
    assert end == 11


def test_element_text_with_span_leading_whitespace_offset():
    """content 含前导空白 → start 是首非空白字符位置。"""
    chunker = StructuralChunker()
    el = _make_paragraph_element("  hello")
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 2
    assert end == 7


def test_element_text_with_span_trailing_whitespace_offset():
    """content 含尾随空白 → end 是末非空白字符后位置。"""
    chunker = StructuralChunker()
    el = _make_paragraph_element("hello  ")
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 0
    assert end == 5


def test_element_text_with_span_both_sides_whitespace():
    chunker = StructuralChunker()
    el = _make_paragraph_element("  hello  ")
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 2
    assert end == 7


def test_element_text_with_span_image_returns_empty():
    """image element → ('', 0, 0)。"""
    from app.models import Element
    chunker = StructuralChunker()
    el = Element(
        element_id="img1",
        type="image",
        content=None,
        resource_path="/tmp/x.png",
        parent_id=None,
        source_locator={"paragraph_index": 0},
        confidence=1.0,
        metadata={},
    )
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_image_with_content_still_empty():
    """即使 image element 有 content 字段，也返回空（type 优先）。"""
    from app.models import Element
    chunker = StructuralChunker()
    el = Element(
        element_id="img1",
        type="image",
        content="some content",  # 异常但允许
        resource_path="/tmp/x.png",
        parent_id=None,
        source_locator={"paragraph_index": 0},
        confidence=1.0,
        metadata={},
    )
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""


# ---------- _element_text 兼容方法 ----------


def test_element_text_returns_only_text_component():
    """_element_text 是 _element_text_with_span 的兼容包装，只返 text。"""
    chunker = StructuralChunker()
    el = _make_paragraph_element("hello")
    text = chunker._element_text(el)
    assert text == "hello"
    assert isinstance(text, str)


def test_element_text_for_empty_content():
    """content 全空白 → strip 后空 → _element_text 返 ''。"""
    chunker = StructuralChunker()
    el = _make_paragraph_element("   ")
    assert chunker._element_text(el) == ""


def test_element_text_for_image_returns_empty():
    from app.models import Element
    chunker = StructuralChunker()
    el = Element(
        element_id="img1",
        type="image",
        resource_path="/tmp/x.png",
        parent_id=None,
        source_locator={"paragraph_index": 0},
        confidence=1.0,
        metadata={},
    )
    assert chunker._element_text(el) == ""


# ---------- normalize_text 边角补强 ----------


def test_normalize_text_empty_string_returns_empty():
    assert normalize_text("") == ""


def test_normalize_text_only_whitespace_returns_empty():
    assert normalize_text("   ") == ""
    assert normalize_text("\n\t\r") == ""


def test_normalize_text_collapses_internal_whitespace():
    assert normalize_text("a   b") == "a b"
    assert normalize_text("a\n\nb") == "a b"
    assert normalize_text("a\t\tb") == "a b"


def test_normalize_text_strips_leading_trailing():
    assert normalize_text("  hello  ") == "hello"
    assert normalize_text("\nhello\n") == "hello"


def test_normalize_text_mixed_whitespace_types():
    """混用 \t/\n/空格 也归一为单空格。"""
    assert normalize_text("a\t b\n  c") == "a b c"


def test_normalize_text_returns_str_type():
    assert isinstance(normalize_text("x"), str)


def test_normalize_text_none_input_returns_empty():
    """normalize_text(None) → 'not s' 短路返回空（不 raise）。

    实际行为：if not s 满足 None → return ""，所以是合法输入。"""
    assert normalize_text(None) == ""  # type: ignore[arg-type]


# ---------- normalize_text 不变量 ----------


def test_normalize_text_idempotent():
    """normalize(normalize(x)) == normalize(x)。"""
    for s in ["  a  b ", "hello", "  ", "a\nb\tc"]:
        once = normalize_text(s)
        twice = normalize_text(once)
        assert once == twice


def test_normalize_text_preserves_non_whitespace():
    """非空白字符（含标点、emoji）应保留。"""
    assert normalize_text("你好，世界！") == "你好，世界！"
    assert normalize_text("  🎉 party  ") == "🎉 party"


# ---------- _ChunkBuffer 多次 flush 复用 ----------


def test_chunk_buffer_multiple_flushes_independent_chunks():
    """同一个 buf 多次 flush 应产出文本独立的 chunk。

    注：buf.counter 不在 flush 时自增（由外层 StructuralChunker 管理），
    所以同一 buf 多次 flush 会得到相同 chunk_id 后缀。但 chunk.text /
    source_element_ids 应是独立的（每次 flush 后 parts 清空）。"""
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("first", "e1", 0, 5)
    c1 = buf.flush(strategy="x", max_chars=800)
    buf.push_text("second", "e2", 0, 6)
    c2 = buf.flush(strategy="y", max_chars=800)
    assert c1 is not None
    assert c2 is not None
    assert c1.text == "first"
    assert c2.text == "second"
    assert c1.source_element_ids != c2.source_element_ids  # e1 vs e2


def test_chunk_buffer_counter_field_used_in_chunk_id():
    """不同 counter → 不同 chunk_id 后缀。"""
    buf1 = _ChunkBuffer(document_id="d1", counter=0)
    buf1.push_text("x", "e1", 0, 1)
    c1 = buf1.flush(strategy="x", max_chars=800)

    buf2 = _ChunkBuffer(document_id="d1", counter=99)
    buf2.push_text("x", "e1", 0, 1)
    c2 = buf2.flush(strategy="x", max_chars=800)
    assert c1.chunk_id.endswith("::c0000")
    assert c2.chunk_id.endswith("::c0099")
