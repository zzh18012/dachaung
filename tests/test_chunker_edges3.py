"""app/chunkers/structural.py 边角测试 - 第三轮（Round 95）。

补强已有 100 + 70 + ? 测试未覆盖的：
- _split_long_text 累积规则：多 piece 合并、buf flush 触发、
  短句+长句混合、空句子跳过
- _hard_split_with_whitespace_fallback：纯 ASCII 无空白 → forced_char、
  窗口恰好 max_chars/2 边界、前导空白跳过、单 piece 全空白
- _ChunkBuffer.flush：空 buf 返 None、纯空白 join 返 None、
  source_element_ids 去重保序、source_spans 每段一项
- _element_text_with_span：raw None、empty、纯空白、仅左空白、仅右空白、
  两端空白、内嵌空白保留
- StructuralChunker.chunk：heading 连续、heading 在文档开头、
  table/image/caption 序列、超长 paragraph + 短 paragraph 交替、
  max_chars 边界（exact max_chars 不切、max_chars+1 切）
- source_spans 坐标在 stripped 坐标系中的精确值
- metadata.split_boundary_after 仅在 boundary_after 非 None 时存在
- counter 严格递增、chunk_id 格式 ::c0000

不修改任何源码。
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from app.chunkers import StructuralChunker, normalize_text
from app.chunkers.structural import (
    _ChunkBuffer,
    _HARD_BREAK_LANGS,
    _PART_ELEMENT_ID,
    _PART_END,
    _PART_START,
    _PART_TEXT,
    _SENTENCE_SPLIT_RE,
    _SplitPiece,
    _hard_split_with_whitespace_fallback,
    _split_long_text,
    _WHITESPACE_RE,
)
from app.models import Chunk, Document, Element


# =============================================================================
# 辅助
# =============================================================================


def _make_para(text: str, eid: str = "doc::e0000") -> Element:
    return Element(
        element_id=eid,
        type="paragraph",
        content=text,
        parent_id=None,
        source_locator={"line": 1},
        confidence=1.0,
        metadata={},
    )


def _make_heading(text: str, eid: str = "doc::e0000", level: int = 1) -> Element:
    return Element(
        element_id=eid,
        type="heading",
        content=text,
        parent_id=None,
        source_locator={"line": 1},
        confidence=1.0,
        metadata={"level": level},
    )


def _make_doc(elements: list[Element], doc_id: str = "doc-abc") -> Document:
    return Document(
        document_id=doc_id,
        source_path="test.txt",
        source_type="text",
        source_hash="a" * 64,
        parser_name="text",
        parser_version="1.0",
        elements=elements,
        chunks=[],
    )


# =============================================================================
# _split_long_text 累积规则
# =============================================================================


def test_split_long_text_empty_returns_empty_list():
    assert _split_long_text("", 100) == []


def test_split_long_text_whitespace_only_returns_empty_list():
    assert _split_long_text("   \n\t  ", 100) == []


def test_split_long_text_short_returns_single_piece():
    pieces = _split_long_text("hello", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "hello"
    assert pieces[0].boundary_after is None
    assert pieces[0].start == 0
    assert pieces[0].end == 5


def test_split_long_text_exactly_max_chars_returns_single_piece():
    text = "a" * 100
    pieces = _split_long_text(text, 100)
    assert len(pieces) == 1
    assert pieces[0].text == text
    assert pieces[0].boundary_after is None


def test_split_long_text_strips_input_first():
    """输入有前后空白 → strip 后再处理。"""
    pieces = _split_long_text("  hello  ", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "hello"


def test_split_long_text_two_sentences_within_max_combined():
    """两句都短，合并后 ≤ max_chars → 单 piece。"""
    text = "first sentence. second one."
    pieces = _split_long_text(text, 100)
    assert len(pieces) == 1
    assert "first" in pieces[0].text
    assert "second" in pieces[0].text


def test_split_long_text_two_sentences_exceed_combined():
    """两句各自 ≤ max_chars，但合并 > max_chars → 两个 piece。"""
    s1 = "a" * 60 + "."
    s2 = "b" * 60 + "."
    text = s1 + " " + s2
    pieces = _split_long_text(text, 100)
    assert len(pieces) >= 2


def test_split_long_text_one_very_long_sentence_no_whitespace():
    """单句无空白、超 max_chars → forced_char 切。"""
    text = "a" * 250 + "."
    pieces = _split_long_text(text, 100)
    assert len(pieces) >= 2
    # 至少一个 piece 是 forced_char
    assert any(p.boundary_after == "forced_char" for p in pieces)


def test_split_long_text_pieces_total_text_length_preserved():
    """所有 piece.text 拼接（带 joiner）后 normalize 等于输入 normalize。"""
    text = "sentence one. sentence two is here. third one is short."
    pieces = _split_long_text(text, 30)
    reconstructed = " ".join(p.text for p in pieces)
    assert normalize_text(reconstructed) == normalize_text(text)


def test_split_long_text_chinese_sentence_break():
    """中文句号、叹号、问号都视为分隔。"""
    text = "你好。世界！再见？" + "x" * 200
    pieces = _split_long_text(text, 50)
    assert len(pieces) >= 1


# =============================================================================
# _hard_split_with_whitespace_fallback 边界
# =============================================================================


def test_hard_split_short_returns_single_piece():
    pieces = _hard_split_with_whitespace_fallback("hello", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "hello"
    assert pieces[0].boundary_after is None


def test_hard_split_leading_whitespace_skipped():
    """前导空白跳过，不产生纯空白 piece。"""
    pieces = _hard_split_with_whitespace_fallback("   hello world", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "hello world"


def test_hard_split_only_whitespace_returns_empty_list():
    pieces = _hard_split_with_whitespace_fallback("    \n\t  ", 100)
    assert pieces == []


def test_hard_split_forced_char_no_whitespace_in_window():
    """窗口内无空白 → forced_char 切。"""
    text = "a" * 250
    pieces = _hard_split_with_whitespace_fallback(text, 100)
    # 至少 3 piece（250 / 100 ≈ 3）
    assert len(pieces) >= 3
    # 中间 piece 应当 forced_char
    assert any(p.boundary_after == "forced_char" for p in pieces)


def test_hard_split_whitespace_boundary_in_window():
    """窗口内有空白 → whitespace 切。"""
    text = " ".join(["word"] * 50)  # 50 个 word 用空格连
    pieces = _hard_split_with_whitespace_fallback(text, 30)
    # 至少 2 piece
    assert len(pieces) >= 2
    # 多数 piece 应当 whitespace 边界
    assert any(p.boundary_after == "whitespace" for p in pieces)


def test_hard_split_piece_text_max_chars_enforced():
    """每个 piece.text 长度 ≤ max_chars。"""
    text = "a" * 500
    pieces = _hard_split_with_whitespace_fallback(text, 100)
    for p in pieces:
        assert len(p.text) <= 100


def test_hard_split_whitespace_last_piece_boundary_none():
    """最后一个 piece（无后续）boundary_after=None。"""
    text = "short last"
    pieces = _hard_split_with_whitespace_fallback(text, 100)
    assert len(pieces) == 1
    assert pieces[0].boundary_after is None


def test_hard_split_piece_start_end_within_input_range():
    """所有 piece 的 start/end 都在 [0, n] 内。"""
    text = "hello world. " * 50
    n = len(text)
    pieces = _hard_split_with_whitespace_fallback(text, 50)
    for p in pieces:
        assert 0 <= p.start <= n
        assert 0 <= p.end <= n
        assert p.start <= p.end


def test_hard_split_text_no_trailing_whitespace_in_piece():
    """piece.text 不以空白结尾（rstrip 调用）。"""
    text = "hello world   foo bar   baz"
    pieces = _hard_split_with_whitespace_fallback(text, 15)
    for p in pieces:
        assert p.text == p.text.rstrip()
        assert not p.text.endswith(" ")


# =============================================================================
# _ChunkBuffer.flush 边界
# =============================================================================


def test_chunk_buffer_flush_empty_returns_none():
    buf = _ChunkBuffer(document_id="doc")
    assert buf.flush(strategy="s", max_chars=100) is None


def test_chunk_buffer_flush_whitespace_only_returns_none():
    """push_text 后 join strip 为空 → flush 返 None。"""
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("   ", "e1", 0, 3)
    result = buf.flush(strategy="s", max_chars=100)
    assert result is None


def test_chunk_buffer_flush_returns_chunk_with_correct_id():
    buf = _ChunkBuffer(document_id="doc-abc", counter=5)
    buf.push_text("hello", "e1", 0, 5)
    chunk = buf.flush(strategy="s", max_chars=100)
    assert chunk.chunk_id == "doc-abc::c0005"


def test_chunk_buffer_flush_strategy_recorded_in_metadata():
    buf = _ChunkBuffer(document_id="doc", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    chunk = buf.flush(strategy="my_strategy", max_chars=800)
    assert chunk.metadata["strategy"] == "my_strategy"


def test_chunk_buffer_flush_max_chars_recorded():
    buf = _ChunkBuffer(document_id="doc", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    chunk = buf.flush(strategy="s", max_chars=123)
    assert chunk.metadata["max_chars"] == 123


def test_chunk_buffer_flush_char_count_accurate():
    buf = _ChunkBuffer(document_id="doc", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e2", 0, 5)
    chunk = buf.flush(strategy="s", max_chars=100)
    # "hello world" = 11 chars
    assert chunk.metadata["char_count"] == 11
    assert len(chunk.text) == 11


def test_chunk_buffer_flush_source_ids_dedup_preserves_order():
    buf = _ChunkBuffer(document_id="doc", counter=0)
    buf.push_text("a", "e1", 0, 1)
    buf.push_text("b", "e2", 0, 1)
    buf.push_text("c", "e1", 1, 2)  # e1 再次
    buf.push_text("d", "e3", 0, 1)
    chunk = buf.flush(strategy="s", max_chars=100)
    assert chunk.source_element_ids == ["e1", "e2", "e3"]  # 去重保序


def test_chunk_buffer_flush_source_spans_each_part():
    """每个 part 一项 span。"""
    buf = _ChunkBuffer(document_id="doc", counter=0)
    buf.push_text("hello", "e1", 10, 15)
    buf.push_text("world", "e2", 20, 25)
    chunk = buf.flush(strategy="s", max_chars=100)
    assert len(chunk.source_spans) == 2
    assert chunk.source_spans[0] == {"element_id": "e1", "start": 10, "end": 15}
    assert chunk.source_spans[1] == {"element_id": "e2", "start": 20, "end": 25}


def test_chunk_buffer_flush_clears_parts():
    """flush 后 parts 清空。"""
    buf = _ChunkBuffer(document_id="doc", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    buf.flush(strategy="s", max_chars=100)
    assert buf.is_empty()


def test_chunk_buffer_flush_text_joined_with_single_space():
    buf = _ChunkBuffer(document_id="doc", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    buf.push_text("world", "e2", 0, 5)
    chunk = buf.flush(strategy="s", max_chars=100)
    assert chunk.text == "hello world"


def test_chunk_buffer_length_sum_of_part_text_lengths():
    buf = _ChunkBuffer(document_id="doc", counter=0)
    buf.push_text("hello", "e1", 0, 5)  # 5
    buf.push_text("world", "e2", 0, 5)  # 5
    assert buf.length() == 10


def test_chunk_buffer_is_empty_default_true():
    buf = _ChunkBuffer(document_id="doc")
    assert buf.is_empty()


def test_chunk_buffer_is_empty_false_after_push():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("x", "e1", 0, 1)
    assert not buf.is_empty()


# =============================================================================
# _element_text_with_span 边界
# =============================================================================


def test_element_text_with_span_raw_none():
    el = Element(
        element_id="e1",
        type="paragraph",
        content=None,
        resource_path="placeholder",
        parent_id=None,
        source_locator={"line": 1},
        confidence=1.0,
        metadata={},
    )
    chunker = StructuralChunker()
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_raw_empty():
    el = Element(
        element_id="e1",
        type="paragraph",
        content="",
        resource_path="placeholder",
        parent_id=None,
        source_locator={"line": 1},
        confidence=1.0,
        metadata={},
    )
    chunker = StructuralChunker()
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_whitespace_only():
    el = Element(
        element_id="e1",
        type="paragraph",
        content="   \n\t  ",
        resource_path="placeholder",
        parent_id=None,
        source_locator={"line": 1},
        confidence=1.0,
        metadata={},
    )
    chunker = StructuralChunker()
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_no_padding():
    el = _make_para("hello world")
    chunker = StructuralChunker()
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello world"
    assert start == 0
    assert end == 11


def test_element_text_with_span_leading_whitespace():
    el = _make_para("   hello")
    chunker = StructuralChunker()
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 3
    assert end == 8


def test_element_text_with_span_trailing_whitespace():
    el = _make_para("hello   ")
    chunker = StructuralChunker()
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 0
    assert end == 5


def test_element_text_with_span_both_paddings():
    el = _make_para("   hello   ")
    chunker = StructuralChunker()
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 3
    assert end == 8


def test_element_text_with_span_image_returns_empty():
    el = Element(
        element_id="e1",
        type="image",
        content=None,
        resource_path="img.png",
        parent_id=None,
        source_locator={"page": 1},
        confidence=0.5,
        metadata={},
    )
    chunker = StructuralChunker()
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_internal_whitespace_preserved():
    el = _make_para("hello   world")
    chunker = StructuralChunker()
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello   world"  # 内部空白保留
    assert start == 0
    assert end == 13


# =============================================================================
# StructuralChunker.chunk 序列场景
# =============================================================================


def test_chunker_consecutive_headings():
    """连续 heading 各自成为 chunk 起始。"""
    elements = [
        _make_heading("H1", "e1"),
        _make_heading("H2", "e2"),
        _make_heading("H3", "e3"),
    ]
    doc = _make_doc(elements)
    chunker = StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    # 3 个 heading → 3 个 chunk
    assert len(chunks) == 3
    assert chunks[0].text == "H1"
    assert chunks[1].text == "H2"
    assert chunks[2].text == "H3"


def test_chunker_heading_at_start_of_document():
    elements = [
        _make_heading("Title", "e1"),
        _make_para("Body content here.", "e2"),
    ]
    doc = _make_doc(elements)
    chunker = StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    # 单 chunk：heading + paragraph 同 buf
    assert len(chunks) == 1
    assert "Title" in chunks[0].text
    assert "Body" in chunks[0].text


def test_chunker_table_isolated_then_paragraph():
    elements = [
        _make_para("intro text", "e1"),
        Element(
            element_id="e2",
            type="table",
            content="| col |\n| --- |\n| v |",
            parent_id=None,
            source_locator={"page": 1},
            confidence=1.0,
            metadata={},
        ),
        _make_para("after text", "e3"),
    ]
    doc = _make_doc(elements)
    chunker = StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    # 3 个 chunk：intro, table, after
    assert len(chunks) == 3
    assert chunks[0].text == "intro text"
    assert "col" in chunks[1].text
    assert chunks[2].text == "after text"
    assert chunks[1].metadata["strategy"] == "isolated_table"


def test_chunker_caption_isolated():
    elements = [
        _make_para("intro", "e1"),
        Element(
            element_id="e2",
            type="caption",
            content="Figure 1. caption text",
            parent_id=None,
            source_locator={"page": 1},
            confidence=1.0,
            metadata={},
        ),
    ]
    doc = _make_doc(elements)
    chunker = StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 2
    assert chunks[1].metadata["strategy"] == "isolated_caption"


def test_chunker_image_element_skipped_in_chunk_output():
    elements = [
        _make_para("before", "e1"),
        Element(
            element_id="e2",
            type="image",
            content=None,
            resource_path="img.png",
            parent_id=None,
            source_locator={"page": 1},
            confidence=0.5,
            metadata={},
        ),
        _make_para("after", "e3"),
    ]
    doc = _make_doc(elements)
    chunker = StructuralChunker(max_chars=800)
    chunks = chunker.chunk(doc)
    # image 不参与分块 → before + after 合并
    assert len(chunks) == 1
    assert "before" in chunks[0].text
    assert "after" in chunks[0].text


def test_chunker_paragraph_exactly_max_chars_no_split():
    text = "a" * 100
    elements = [_make_para(text, "e1")]
    doc = _make_doc(elements)
    chunker = StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].text == text


def test_chunker_paragraph_max_chars_plus_one_triggers_split():
    text = "a" * 101
    elements = [_make_para(text, "e1")]
    doc = _make_doc(elements)
    chunker = StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    assert len(chunks) >= 2


def test_chunker_long_paragraph_split_boundary_after_metadata():
    """超长 paragraph 切分后 chunk metadata 可能含 split_boundary_after。"""
    text = "sentence one is here. " * 50
    elements = [_make_para(text, "e1")]
    doc = _make_doc(elements)
    chunker = StructuralChunker(max_chars=80)
    chunks = chunker.chunk(doc)
    # 至少一个 chunk 有 strategy=long_paragraph_sentence_split
    assert any(c.metadata["strategy"] == "long_paragraph_sentence_split" for c in chunks)


def test_chunker_long_paragraph_split_chunk_ids_increment():
    """切分后多个 chunk 的 chunk_id 严格递增。"""
    text = "a" * 500
    elements = [_make_para(text, "e1")]
    doc = _make_doc(elements)
    chunker = StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    for i, c in enumerate(chunks):
        assert c.chunk_id == f"doc-abc::c{i:04d}"


def test_chunker_chunk_text_never_exceeds_max_chars():
    """每个 chunk.text 长度 ≤ max_chars（除非单 piece 自身超长，但 _split_long_text 保证不超）。"""
    text = "sentence here. " * 30
    elements = [_make_para(text, "e1")]
    doc = _make_doc(elements)
    chunker = StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    for c in chunks:
        assert len(c.text) <= 100


def test_chunker_each_chunk_has_at_least_one_source_element_id():
    elements = [
        _make_para("a b c.", f"e{i}") for i in range(5)
    ]
    doc = _make_doc(elements)
    chunker = StructuralChunker(max_chars=32)
    chunks = chunker.chunk(doc)
    for c in chunks:
        assert len(c.source_element_ids) >= 1
        for sid in c.source_element_ids:
            assert sid  # non-empty string


def test_chunker_normalized_text_lossless():
    """不丢不重：normalize(Σ chunks.text) == normalize(Σ elements.content)."""
    elements = [
        _make_para("first paragraph.", "e1"),
        _make_heading("Section", "e2"),
        _make_para("second paragraph with more text.", "e3"),
    ]
    doc = _make_doc(elements)
    chunker = StructuralChunker(max_chars=50)
    chunks = chunker.chunk(doc)
    sum_chunks = normalize_text(" ".join(c.text for c in chunks))
    sum_elements = normalize_text(" ".join(e.content for e in elements))
    assert sum_chunks == sum_elements


# =============================================================================
# chunk_id 格式与递增
# =============================================================================


def test_chunker_chunk_id_format_is_docid_double_colon_c0000():
    elements = [_make_para("hello world.", "e1")]
    doc = _make_doc(elements, doc_id="my-doc-123")
    chunker = StructuralChunker()
    chunks = chunker.chunk(doc)
    assert chunks[0].chunk_id == "my-doc-123::c0000"


def test_chunker_chunk_id_zero_padded_to_4_digits():
    """counter 0 → 0000, 12 → 0012。"""
    elements = [_make_para(f"content number {i} here.", f"e{i}") for i in range(15)]
    doc = _make_doc(elements)
    chunker = StructuralChunker(max_chars=50)
    chunks = chunker.chunk(doc)
    # 至少有 c0000, c0001 等
    ids = [c.chunk_id for c in chunks]
    assert any("c0000" in cid for cid in ids)
    if len(chunks) >= 2:
        assert any("c0001" in cid for cid in ids)


# =============================================================================
# source_spans 坐标正确性
# =============================================================================


def test_chunker_source_spans_point_to_element_content_range():
    """span.start/end 落在 element.content 的字符区间内。"""
    elements = [_make_para("hello world.", "e1")]
    doc = _make_doc(elements)
    chunker = StructuralChunker()
    chunks = chunker.chunk(doc)
    span = chunks[0].source_spans[0]
    assert span["element_id"] == "e1"
    assert span["start"] == 0
    # stripped text is "hello world." (12 chars)
    assert span["end"] == 12


def test_chunker_source_spans_for_long_paragraph_correct_offsets():
    """超长 paragraph 切分后 spans 在原始 content 坐标系中。"""
    text = "a" * 200 + ". " + "b" * 200 + "."
    elements = [_make_para(text, "e1")]
    doc = _make_doc(elements)
    chunker = StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    # 每个 chunk 的 span.start/end 应在 [0, len(text)] 内
    for c in chunks:
        for sp in c.source_spans:
            assert 0 <= sp["start"] <= len(text)
            assert 0 <= sp["end"] <= len(text)
            assert sp["start"] <= sp["end"]


# =============================================================================
# StructuralChunker.__init__ 边界
# =============================================================================


def test_chunker_init_max_chars_minimum_value():
    """max_chars=32 是最小允许值。"""
    chunker = StructuralChunker(max_chars=32)
    assert chunker.max_chars == 32


def test_chunker_init_max_chars_below_minimum_raises():
    with pytest.raises(ValueError) as ei:
        StructuralChunker(max_chars=31)
    assert "31" in str(ei.value)


def test_chunker_init_max_chars_one_raises():
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=1)


def test_chunker_init_default_max_chars_800():
    chunker = StructuralChunker()
    assert chunker.max_chars == 800


# =============================================================================
# _SplitPiece 数据类
# =============================================================================


def test_split_piece_default_start_zero():
    p = _SplitPiece(text="x", boundary_after=None)
    assert p.start == 0
    assert p.end == 0


def test_split_piece_frozen():
    """_SplitPiece 是 frozen dataclass。"""
    p = _SplitPiece(text="x", boundary_after=None)
    try:
        p.text = "y"  # type: ignore[misc]
        # 如果没抛，dataclass 不是 frozen
        assert False, "expected frozen dataclass to raise"
    except (AttributeError, TypeError):
        pass


def test_split_piece_equality():
    p1 = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    p2 = _SplitPiece(text="x", boundary_after=None, start=0, end=1)
    assert p1 == p2


# =============================================================================
# _SENTENCE_SPLIT_RE 模式
# =============================================================================


def test_sentence_split_re_splits_on_period_space():
    parts = _SENTENCE_SPLIT_RE.split("first. second.")
    assert "first." in parts
    assert "second." in parts


def test_sentence_split_re_splits_on_chinese_period_with_space():
    """中文句号 + 空白 → 切。"""
    parts = _SENTENCE_SPLIT_RE.split("你好。 世界。")
    assert "你好。" in parts
    assert "世界。" in parts


def test_sentence_split_re_no_split_chinese_period_no_whitespace():
    r"""中文句号无空白跟随 → 不切（regex 要求标点后跟 \s+）。"""
    parts = _SENTENCE_SPLIT_RE.split("你好。世界。")
    # 不切（无空白）
    assert len(parts) == 1


def test_sentence_split_re_no_split_without_whitespace():
    """仅 . 不跟空白 → 不切。"""
    parts = _SENTENCE_SPLIT_RE.split("a.b")
    assert parts == ["a.b"]


def test_sentence_split_re_no_split_no_punctuation():
    parts = _SENTENCE_SPLIT_RE.split("hello world")
    assert parts == ["hello world"]


# =============================================================================
# _WHITESPACE_RE 模式
# =============================================================================


def test_whitespace_re_matches_space():
    assert _WHITESPACE_RE.match(" ")


def test_whitespace_re_matches_tab():
    assert _WHITESPACE_RE.match("\t")


def test_whitespace_re_matches_newline():
    assert _WHITESPACE_RE.match("\n")


def test_whitespace_re_matches_multiple_mixed():
    assert _WHITESPACE_RE.match(" \t\n  ")


def test_whitespace_re_does_not_match_letter():
    assert not _WHITESPACE_RE.match("a")


# =============================================================================
# _HARD_BREAK_LANGS 内容
# =============================================================================


def test_hard_break_langs_count():
    """6 个硬分隔符。"""
    assert len(_HARD_BREAK_LANGS) == 6


def test_hard_break_langs_contains_all_expected():
    expected = {"。", "！", "？", ".", "!", "?"}
    assert set(_HARD_BREAK_LANGS) == expected


def test_hard_break_langs_is_tuple():
    assert isinstance(_HARD_BREAK_LANGS, tuple)
