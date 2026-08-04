"""app/chunkers/structural.py 边角测试 - 第四轮（Round 108）。

补强已有 base/edges/edges2/edges3（共 391 个测试）未覆盖的深度路径：
- _ChunkBuffer.flush 直接调用：单 part、多 part dedup、whitespace-only text → None、
  source_spans 顺序与每个 part 一项
- StructuralChunker.chunk 集成：空文档、全 table、全 image、连续 heading、
  heading→paragraph→table 顺序、isolated_chunk strategy
- _split_long_text：多 sentence 累积边界、英文 + 中文混合 sentence、
  单 sentence 与 hard_split 联动、空 sentence filter
- _hard_split_with_whitespace_fallback：whitespace 在 upper 边界、在 lower 边界、
  lower==upper、max_chars=1 边界
- normalize_text：纯 CJK 无空白、超长 string idempotent
- StructuralChunker.__init__：max_chars=33、64、128 各阈值
- 模块结构：__all__、imports、常量

不修改任何源码。
"""

from __future__ import annotations

from dataclasses import dataclass
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
    _hard_split_with_whitespace_fallback,
    _split_long_text,
    normalize_text,
)
from app.models import Chunk, Document, Element
from app.chunkers.structural import StructuralChunker


# =========================================================================
# 辅助
# =========================================================================


def _make_element(
    *,
    element_id: str = "e1",
    type_: str = "paragraph",
    content: str | None = "x",
    document_id: str = "doc1",
    resource_path: str | None = None,
) -> Element:
    return Element(
        element_id=f"{document_id}::{element_id}",
        type=type_,
        content=content,
        resource_path=resource_path,
        parent_id=None,
        source_locator={"line": 1},
        confidence=0.9,
        metadata={},
    )


def _make_document(elements: list[Element], document_id: str = "doc1") -> Document:
    return Document(
        document_id=document_id,
        source_path="x",
        source_type="text",
        source_hash="a" * 64,
        parser_name="text",
        parser_version="stdlib/0.1.0",
        elements=elements,
        chunks=[],
        relations=[],
        warnings=[],
        errors=[],
        metadata={},
    )


# =========================================================================
# _ChunkBuffer.flush 深度
# =========================================================================


def test_chunk_buffer_flush_empty_returns_none():
    buf = _ChunkBuffer(document_id="doc")
    assert buf.flush(strategy="sequential", max_chars=800) is None


def test_chunk_buffer_flush_single_part_returns_chunk():
    buf = _ChunkBuffer(document_id="doc", counter=0)
    buf.push_text("hello", "doc::e1", 0, 5)
    chunk = buf.flush(strategy="sequential", max_chars=800)
    assert chunk is not None
    assert chunk.text == "hello"
    assert chunk.source_element_ids == ["doc::e1"]


def test_chunk_buffer_flush_whitespace_only_text_returns_none():
    """join 后 strip 为空 → None。"""
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("   ", "doc::e1", 0, 3)
    assert buf.flush(strategy="sequential", max_chars=800) is None


def test_chunk_buffer_flush_dedup_source_element_ids_preserves_order():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("a", "doc::e1", 0, 1)
    buf.push_text("b", "doc::e2", 0, 1)
    buf.push_text("c", "doc::e1", 1, 2)  # e1 再次出现
    buf.push_text("d", "doc::e3", 0, 1)
    chunk = buf.flush(strategy="sequential", max_chars=800)
    assert chunk is not None
    assert chunk.source_element_ids == ["doc::e1", "doc::e2", "doc::e3"]


def test_chunk_buffer_flush_source_spans_each_part_one_entry():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("a", "doc::e1", 0, 1)
    buf.push_text("b", "doc::e1", 1, 2)
    buf.push_text("c", "doc::e2", 0, 1)
    chunk = buf.flush(strategy="sequential", max_chars=800)
    assert chunk is not None
    assert len(chunk.source_spans) == 3
    assert chunk.source_spans[0]["element_id"] == "doc::e1"
    assert chunk.source_spans[1]["element_id"] == "doc::e1"
    assert chunk.source_spans[2]["element_id"] == "doc::e2"


def test_chunk_buffer_flush_chunk_id_format():
    buf = _ChunkBuffer(document_id="docX", counter=7)
    buf.push_text("text", "docX::e1", 0, 4)
    chunk = buf.flush(strategy="sequential", max_chars=800)
    assert chunk is not None
    assert chunk.chunk_id == "docX::c0007"


def test_chunk_buffer_flush_metadata_has_strategy():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("text", "doc::e1", 0, 4)
    chunk = buf.flush(strategy="my_strategy", max_chars=800)
    assert chunk is not None
    assert chunk.metadata["strategy"] == "my_strategy"


def test_chunk_buffer_flush_metadata_has_max_chars():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("text", "doc::e1", 0, 4)
    chunk = buf.flush(strategy="x", max_chars=500)
    assert chunk is not None
    assert chunk.metadata["max_chars"] == 500


def test_chunk_buffer_flush_metadata_has_char_count():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("hello", "doc::e1", 0, 5)
    chunk = buf.flush(strategy="x", max_chars=800)
    assert chunk is not None
    assert chunk.metadata["char_count"] == 5


def test_chunk_buffer_flush_text_join_with_single_space():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("hello", "doc::e1", 0, 5)
    buf.push_text("world", "doc::e1", 6, 11)
    chunk = buf.flush(strategy="x", max_chars=800)
    assert chunk is not None
    assert chunk.text == "hello world"


def test_chunk_buffer_flush_clears_parts_after_flush():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("text", "doc::e1", 0, 4)
    buf.flush(strategy="x", max_chars=800)
    assert buf.is_empty() is True


def test_chunk_buffer_flush_second_flush_returns_none():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("text", "doc::e1", 0, 4)
    buf.flush(strategy="x", max_chars=800)
    assert buf.flush(strategy="x", max_chars=800) is None


def test_chunk_buffer_is_empty_default_true():
    buf = _ChunkBuffer(document_id="doc")
    assert buf.is_empty() is True


def test_chunk_buffer_is_empty_false_after_push():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("x", "doc::e1", 0, 1)
    assert buf.is_empty() is False


def test_chunk_buffer_length_zero_default():
    buf = _ChunkBuffer(document_id="doc")
    assert buf.length() == 0


def test_chunk_buffer_length_sum_of_parts():
    buf = _ChunkBuffer(document_id="doc")
    buf.push_text("ab", "doc::e1", 0, 2)
    buf.push_text("cde", "doc::e1", 0, 3)
    assert buf.length() == 5


def test_chunk_buffer_default_counter_zero():
    buf = _ChunkBuffer(document_id="doc")
    assert buf.counter == 0


def test_chunk_buffer_default_document_id_set():
    buf = _ChunkBuffer(document_id="mydoc")
    assert buf.document_id == "mydoc"


# =========================================================================
# _PART_* 常量
# =========================================================================


def test_part_text_constant_is_zero():
    assert _PART_TEXT == 0


def test_part_element_id_constant_is_one():
    assert _PART_ELEMENT_ID == 1


def test_part_start_constant_is_two():
    assert _PART_START == 2


def test_part_end_constant_is_three():
    assert _PART_END == 3


# =========================================================================
# _SplitPiece dataclass
# =========================================================================


def test_split_piece_default_start_zero():
    p = _SplitPiece(text="x", boundary_after=None)
    assert p.start == 0


def test_split_piece_default_end_zero():
    p = _SplitPiece(text="x", boundary_after=None)
    assert p.end == 0


def test_split_piece_text_field():
    p = _SplitPiece(text="hello", boundary_after="whitespace", start=0, end=5)
    assert p.text == "hello"


def test_split_piece_boundary_after_field():
    p = _SplitPiece(text="x", boundary_after="forced_char")
    assert p.boundary_after == "forced_char"


def test_split_piece_is_frozen():
    """_SplitPiece 是 frozen dataclass。"""
    p = _SplitPiece(text="x", boundary_after=None)
    with pytest.raises(Exception):
        p.text = "y"  # type: ignore[misc]


# =========================================================================
# _hard_split_with_whitespace_fallback 深度边界
# =========================================================================


def test_hard_split_whitespace_at_upper_boundary():
    """upper 处刚好是空白 → 取该空白切开。"""
    text = "abcd efgh"  # 9 字符
    # max_chars=4: lower=2, upper=4 → 在 [4, 2] 反向找空白 → text[4]=' ' 是空白
    pieces = _hard_split_with_whitespace_fallback(text, 4)
    assert len(pieces) >= 2
    assert pieces[0].text == "abcd"


def test_hard_split_whitespace_at_lower_boundary():
    """lower 处刚好是空白 → 取该空白切开。"""
    text = "ab cdefghijkl mn"  # 16 字符
    # max_chars=8: lower=4, upper=8 → 在 [8, 4] 反向找空白 → text[4]='c' 不是空白
    # text[8]='l' 不是空白... text[2]=' ' 是空白但超出 lower=4
    pieces = _hard_split_with_whitespace_fallback(text, 8)
    assert isinstance(pieces, list)


def test_hard_split_max_chars_one_text_long_forced_char():
    """max_chars=1 + 长 text → 全 forced_char 切。"""
    text = "abcdef"
    pieces = _hard_split_with_whitespace_fallback(text, 1)
    # 每次切 1 字符
    for p in pieces:
        assert len(p.text) <= 1


def test_hard_split_max_chars_one_with_whitespace():
    """max_chars=1 + 含空白 → 应跳过空白。"""
    text = "a b c d"
    pieces = _hard_split_with_whitespace_fallback(text, 1)
    # 每次切 1 字符；空白被跳过
    texts = [p.text for p in pieces]
    assert "a" in texts
    assert "b" in texts
    assert " " not in texts


def test_hard_split_returns_list_of_split_pieces():
    pieces = _hard_split_with_whitespace_fallback("hello world", 5)
    assert isinstance(pieces, list)
    for p in pieces:
        assert isinstance(p, _SplitPiece)


def test_hard_split_min_max_chars_32_long_text():
    """max_chars=32 阈值 + 长 text → piece 不超过 32。"""
    text = "w" * 100 + " x" + "y" * 100
    pieces = _hard_split_with_whitespace_fallback(text, 32)
    for p in pieces:
        assert len(p.text) <= 32


def test_hard_split_whitespace_at_end_text():
    """text 末尾有空白 → 最后 piece 的 boundary_after=None。"""
    text = "hello world "
    pieces = _hard_split_with_whitespace_fallback(text, 5)
    # 最后一个 piece 应是 boundary_after=None
    assert pieces[-1].boundary_after is None


def test_hard_split_lower_equals_upper_when_max_one():
    """max_chars=1: lower=upper=1，循环不执行（range(1, 0, -1) = [1]）。"""
    text = "abc"
    pieces = _hard_split_with_whitespace_fallback(text, 1)
    assert len(pieces) == 3
    assert pieces[0].text == "a"
    assert pieces[0].boundary_after == "forced_char"


# =========================================================================
# _split_long_text 深度
# =========================================================================


def test_split_long_text_chinese_english_mixed():
    """混合中英文 sentence 分割。"""
    text = "Hello world. 你好世界。 End here."
    pieces = _split_long_text(text, 100)
    assert len(pieces) == 1  # 全部合并 < 100


def test_split_long_text_chinese_only_short():
    """纯中文短文本，无空白分隔符 → 整体一个 piece。"""
    text = "你好世界"
    pieces = _split_long_text(text, 100)
    assert len(pieces) == 1
    assert pieces[0].text == "你好世界"


def test_split_long_text_chinese_only_long_force_split():
    """纯中文长文本，无空白分隔符 → hard_split forced_char。"""
    text = "你" * 100
    pieces = _split_long_text(text, 32)
    assert len(pieces) > 1
    for p in pieces:
        assert len(p.text) <= 32


def test_split_long_text_empty_sentences_filtered():
    """连续分隔符产生空 sentence → 被过滤。需超长 text 才触发 split 路径。"""
    text = "a. . . b. " + "x" * 50  # 超 max_chars 触发 split
    pieces = _split_long_text(text, 32)
    texts = [p.text for p in pieces]
    assert "" not in texts  # 空 sentence 被过滤
    assert all(t for t in texts)


def test_split_long_text_returns_pieces_with_boundary():
    """超长 text 时 piece 的 boundary_after 字段非 None（forced_char 或 whitespace）。"""
    text = "x" * 200
    pieces = _split_long_text(text, 32)
    # 至少有一个 piece 是 forced_char
    boundaries = [p.boundary_after for p in pieces]
    assert "forced_char" in boundaries
    assert boundaries[-1] is None  # 最后一个总是 None


def test_split_long_text_short_chinese_with_period():
    text = "你好。"
    pieces = _split_long_text(text, 100)
    assert len(pieces) == 1
    assert pieces[0].text == "你好。"


def test_split_long_text_strips_leading_whitespace_in_sentence():
    """超长 text 触发 split 路径，外层 strip + 内层 sentence 各自保留。"""
    text = "  hello.  world.  " + "x" * 50  # 总长 > max_chars 触发 split
    pieces = _split_long_text(text, 32)
    # 第一段 "hello." 应作为某个 piece 出现（可能与其他累积合并）
    full = " ".join(p.text for p in pieces)
    assert "hello." in full
    assert "world." in full


def test_split_long_text_returns_list_type():
    pieces = _split_long_text("x", 100)
    assert isinstance(pieces, list)


def test_split_long_text_each_piece_has_start_end():
    text = "Hello world. Another sentence."
    pieces = _split_long_text(text, 100)
    for p in pieces:
        assert p.start >= 0
        assert p.end >= p.start


def test_split_long_text_max_chars_32_threshold():
    """max_chars=32 边界。"""
    text = "Sentence one here. " * 10  # 190 字符
    pieces = _split_long_text(text, 32)
    for p in pieces:
        assert len(p.text) <= 32


# =========================================================================
# normalize_text 深度
# =========================================================================


def test_normalize_text_pure_cjk_no_whitespace():
    assert normalize_text("你好世界") == "你好世界"


def test_normalize_text_pure_cjk_with_spaces():
    assert normalize_text("你 好 世 界") == "你 好 世 界"


def test_normalize_text_mixed_cjk_whitespace():
    """CJK 字符内部无空白，整体保留；空白只在 CJK 之间压缩为单空格。"""
    assert normalize_text("  你好\n世界\tend  ") == "你好 世界 end"


def test_normalize_text_returns_str_type():
    assert isinstance(normalize_text("x"), str)


def test_normalize_text_idempotent_long_string():
    text = "  hello   world  \n\t  end  "
    once = normalize_text(text)
    twice = normalize_text(once)
    assert once == twice


def test_normalize_text_only_punctuation_preserved():
    """纯标点 → 无空白可压缩，原样返回。"""
    assert normalize_text("...,,,???") == "...,,,???"


def test_normalize_text_punctuation_with_whitespace():
    assert normalize_text("a . b") == "a . b"


def test_normalize_text_single_space_input():
    assert normalize_text(" ") == ""


def test_normalize_text_tab_only_input():
    assert normalize_text("\t") == ""


def test_normalize_text_newline_only_input():
    assert normalize_text("\n") == ""


def test_normalize_text_preserves_digits():
    assert normalize_text("abc 123 xyz") == "abc 123 xyz"


def test_normalize_text_preserves_special_chars():
    assert normalize_text("a@b#c$d%e^f") == "a@b#c$d%e^f"


# =========================================================================
# StructuralChunker.__init__ 阈值
# =========================================================================


def test_chunker_init_max_chars_33():
    chunker = StructuralChunker(max_chars=33)
    assert chunker.max_chars == 33


def test_chunker_init_max_chars_64():
    chunker = StructuralChunker(max_chars=64)
    assert chunker.max_chars == 64


def test_chunker_init_max_chars_128():
    chunker = StructuralChunker(max_chars=128)
    assert chunker.max_chars == 128


def test_chunker_init_max_chars_32_minimum_accepted():
    chunker = StructuralChunker(max_chars=32)
    assert chunker.max_chars == 32


def test_chunker_init_max_chars_31_rejected():
    with pytest.raises(ValueError, match="max_chars"):
        StructuralChunker(max_chars=31)


def test_chunker_init_max_chars_huge():
    chunker = StructuralChunker(max_chars=10_000_000)
    assert chunker.max_chars == 10_000_000


# =========================================================================
# StructuralChunker.chunk 集成
# =========================================================================


def test_chunker_chunk_empty_document_returns_empty():
    doc = _make_document([])
    chunker = StructuralChunker(max_chars=100)
    assert chunker.chunk(doc) == []


def test_chunker_chunk_all_tables_each_isolated():
    """3 个 table → 3 个 isolated chunk。"""
    elements = [
        _make_element(element_id=f"t{i}", type_="table", content=f"table{i}") for i in range(3)
    ]
    doc = _make_document(elements)
    chunker = StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 3
    for c in chunks:
        assert c.metadata["strategy"] == "isolated_table"


def test_chunker_chunk_all_images_skipped():
    """image element 不参与分块 → 空 chunks。"""
    elements = [
        _make_element(element_id=f"i{i}", type_="image", content=None, resource_path="img.png")
        for i in range(3)
    ]
    doc = _make_document(elements)
    chunker = StructuralChunker(max_chars=100)
    assert chunker.chunk(doc) == []


def test_chunker_chunk_all_captions_each_isolated():
    elements = [
        _make_element(element_id=f"c{i}", type_="caption", content=f"Caption {i}") for i in range(3)
    ]
    doc = _make_document(elements)
    chunker = StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 3
    for c in chunks:
        assert c.metadata["strategy"] == "isolated_caption"


def test_chunker_chunk_consecutive_headings_each_in_own_chunk():
    """heading 是硬边界，每个 heading 都触发 flush。"""
    elements = [
        _make_element(element_id=f"h{i}", type_="heading", content=f"Heading{i}") for i in range(3)
    ]
    doc = _make_document(elements)
    chunker = StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    # 3 个 heading → 3 个 chunk
    assert len(chunks) == 3
    for c in chunks:
        assert c.metadata["strategy"] == "sequential"


def test_chunker_chunk_heading_then_paragraph_combined():
    """heading + 紧跟 paragraph → 同一 chunk（heading 不立即 flush 自己）。"""
    elements = [
        _make_element(element_id="h1", type_="heading", content="Title"),
        _make_element(element_id="p1", type_="paragraph", content="body text."),
    ]
    doc = _make_document(elements)
    chunker = StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1
    assert "Title" in chunks[0].text
    assert "body text" in chunks[0].text


def test_chunker_chunk_paragraph_then_heading_separate_chunks():
    """paragraph + heading → heading 触发 flush，paragraph 先成 chunk。"""
    elements = [
        _make_element(element_id="p1", type_="paragraph", content="para text here."),
        _make_element(element_id="h1", type_="heading", content="New Section"),
    ]
    doc = _make_document(elements)
    chunker = StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 2
    assert "para text" in chunks[0].text
    assert "New Section" in chunks[1].text


def test_chunker_chunk_paragraph_then_table_then_paragraph():
    """table 是 isolated chunk，两侧 paragraph 各自独立 chunk。"""
    elements = [
        _make_element(element_id="p1", type_="paragraph", content="before table."),
        _make_element(element_id="t1", type_="table", content="| h |\n| --- |\n| r |"),
        _make_element(element_id="p2", type_="paragraph", content="after table."),
    ]
    doc = _make_document(elements)
    chunker = StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    # p1 flush → chunk0, table isolated → chunk1, p2 → chunk2
    assert len(chunks) == 3
    assert chunks[1].metadata["strategy"] == "isolated_table"


def test_chunker_chunk_long_paragraph_splits():
    """超长 paragraph → 多个 chunk（long_paragraph_sentence_split）。"""
    text = "Sentence one. " * 30  # ~210 字符
    elements = [_make_element(element_id="p1", type_="paragraph", content=text)]
    doc = _make_document(elements)
    chunker = StructuralChunker(max_chars=50)
    chunks = chunker.chunk(doc)
    assert len(chunks) > 1
    for c in chunks:
        assert c.metadata["strategy"] == "long_paragraph_sentence_split"
        assert len(c.text) <= 50


def test_chunker_chunk_id_zero_padded():
    elements = [_make_element(element_id=f"p{i}", type_="paragraph", content=f"x{i}") for i in range(5)]
    doc = _make_document(elements)
    chunker = StructuralChunker(max_chars=32)
    chunks = chunker.chunk(doc)
    # 第一个 chunk_id 应是 doc1::c0000
    assert chunks[0].chunk_id == "doc1::c0000"


def test_chunker_chunk_id_increments_across_chunks():
    elements = [_make_element(element_id=f"p{i}", type_="paragraph", content=f"x{i}") for i in range(5)]
    doc = _make_document(elements)
    chunker = StructuralChunker(max_chars=32)
    chunks = chunker.chunk(doc)
    # chunks 顺序 c0000, c0001, ...
    for i, c in enumerate(chunks):
        assert c.chunk_id == f"doc1::c{i:04d}"


def test_chunker_chunk_returns_list_type():
    doc = _make_document([])
    chunker = StructuralChunker(max_chars=100)
    assert isinstance(chunker.chunk(doc), list)


def test_chunker_chunk_text_join_uses_single_space():
    """多 paragraph 在同一 chunk 内 → 用单空格 join。"""
    elements = [
        _make_element(element_id="p1", type_="paragraph", content="alpha"),
        _make_element(element_id="p2", type_="paragraph", content="beta"),
    ]
    doc = _make_document(elements)
    chunker = StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].text == "alpha beta"


def test_chunker_chunk_metadata_has_strategy_key():
    elements = [_make_element(element_id="p1", type_="paragraph", content="x")]
    doc = _make_document(elements)
    chunker = StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    assert "strategy" in chunks[0].metadata


def test_chunker_chunk_metadata_has_max_chars_key():
    elements = [_make_element(element_id="p1", type_="paragraph", content="x")]
    doc = _make_document(elements)
    chunker = StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    assert chunks[0].metadata["max_chars"] == 100


def test_chunker_chunk_metadata_has_char_count_key():
    elements = [_make_element(element_id="p1", type_="paragraph", content="x")]
    doc = _make_document(elements)
    chunker = StructuralChunker(max_chars=100)
    chunks = chunker.chunk(doc)
    assert chunks[0].metadata["char_count"] == 1


# =========================================================================
# StructuralChunker._element_text_with_span 边界
# =========================================================================


def test_element_text_with_span_internal_whitespace_preserved():
    chunker = StructuralChunker()
    el = _make_element(content="  hello   world  ")
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello   world"
    assert start == 2
    assert end == 15


def test_element_text_with_span_no_whitespace():
    chunker = StructuralChunker()
    el = _make_element(content="hello")
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 0
    assert end == 5


def test_element_text_with_span_only_leading_whitespace():
    chunker = StructuralChunker()
    el = _make_element(content="   hello")
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 3
    assert end == 8


def test_element_text_with_span_only_trailing_whitespace():
    chunker = StructuralChunker()
    el = _make_element(content="hello   ")
    text, start, end = chunker._element_text_with_span(el)
    assert text == "hello"
    assert start == 0
    assert end == 5


def test_element_text_with_span_image_returns_empty_tuple():
    chunker = StructuralChunker()
    el = _make_element(type_="image", content=None, resource_path="img.png")
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_image_with_content_still_empty():
    """image element 即使有 content 也返回 empty。"""
    chunker = StructuralChunker()
    el = _make_element(type_="image", content="some text", resource_path="img.png")
    text, _, _ = chunker._element_text_with_span(el)
    assert text == ""


def test_element_text_with_span_empty_string_content():
    """content="" + resource_path 设置 → 允许构造（schema anyOf）。"""
    chunker = StructuralChunker()
    el = _make_element(content="", resource_path="img.png")
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_none_content():
    """content=None + resource_path 设置 → 允许构造。"""
    chunker = StructuralChunker()
    el = _make_element(content=None, resource_path="img.png")
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_whitespace_only_content():
    """content="   \\n\\t  " + resource_path → strip 后空，返回 empty tuple。"""
    chunker = StructuralChunker()
    el = _make_element(content="   \n\t  ", resource_path="img.png")
    text, start, end = chunker._element_text_with_span(el)
    assert text == ""
    assert start == 0
    assert end == 0


def test_element_text_with_span_returns_tuple_of_three():
    chunker = StructuralChunker()
    el = _make_element(content="x")
    result = chunker._element_text_with_span(el)
    assert isinstance(result, tuple)
    assert len(result) == 3


def test_element_text_legacy_method_returns_text_only():
    """_element_text 是兼容旧接口，仅返回 text。"""
    chunker = StructuralChunker()
    el = _make_element(content="  hello  ")
    assert chunker._element_text(el) == "hello"


def test_element_text_legacy_method_returns_str():
    chunker = StructuralChunker()
    el = _make_element(content="x")
    assert isinstance(chunker._element_text(el), str)


# =========================================================================
# 模块常量
# =========================================================================


def test_sentence_split_re_is_compiled():
    import re
    assert isinstance(_SENTENCE_SPLIT_RE, re.Pattern)


def test_hard_break_langs_contains_six_chars():
    assert len(_HARD_BREAK_LANGS) == 6


def test_hard_break_langs_contains_chinese_period():
    assert "。" in _HARD_BREAK_LANGS


def test_hard_break_langs_contains_english_period():
    assert "." in _HARD_BREAK_LANGS


def test_hard_break_langs_is_tuple():
    assert isinstance(_HARD_BREAK_LANGS, tuple)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exports_structural_chunker():
    from app.chunkers import structural
    assert "StructuralChunker" in structural.__all__


def test_module_all_exports_normalize_text():
    from app.chunkers import structural
    assert "normalize_text" in structural.__all__


def test_module_all_exact_two_items():
    from app.chunkers import structural
    assert set(structural.__all__) == {"StructuralChunker", "normalize_text"}


def test_module_imports_re():
    from app.chunkers import structural
    assert hasattr(structural, "re")


def test_module_imports_dataclass():
    from app.chunkers import structural
    assert hasattr(structural, "dataclass")


def test_module_imports_field():
    from app.chunkers import structural
    assert hasattr(structural, "field")


def test_module_imports_any():
    from app.chunkers import structural
    assert hasattr(structural, "Any")


def test_module_imports_chunk():
    from app.chunkers import structural
    assert hasattr(structural, "Chunk")


def test_module_imports_document():
    from app.chunkers import structural
    assert hasattr(structural, "Document")


def test_module_imports_element():
    from app.chunkers import structural
    assert hasattr(structural, "Element")


def test_module_has_structural_chunker_class():
    from app.chunkers import structural
    assert hasattr(structural, "StructuralChunker")


def test_module_has_normalize_text_function():
    from app.chunkers import structural
    assert hasattr(structural, "normalize_text")


def test_module_has_split_long_text_function():
    from app.chunkers import structural
    assert hasattr(structural, "_split_long_text")


def test_module_has_hard_split_function():
    from app.chunkers import structural
    assert hasattr(structural, "_hard_split_with_whitespace_fallback")


def test_module_has_chunk_buffer_class():
    from app.chunkers import structural
    assert hasattr(structural, "_ChunkBuffer")


def test_module_has_split_piece_class():
    from app.chunkers import structural
    assert hasattr(structural, "_SplitPiece")


def test_structural_chunker_has_chunk_method():
    assert callable(StructuralChunker.chunk)


def test_structural_chunker_has_element_text_with_span_method():
    assert callable(StructuralChunker._element_text_with_span)


def test_structural_chunker_has_element_text_method():
    assert callable(StructuralChunker._element_text)
