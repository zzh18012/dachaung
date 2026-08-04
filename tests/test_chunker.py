"""结构分块器的单元测试。"""

from __future__ import annotations

import pytest

from app.chunkers import StructuralChunker, normalize_text
from app.chunkers.structural import _split_long_text
from app.models import Chunk, Document, Element


def _make_doc(elements_data, source_type="docx", doc_id="d-hash0000000001") -> Document:
    """elements_data: list of (type, content[, locator])。"""
    elements = []
    for i, item in enumerate(elements_data):
        etype, content = item[0], item[1]
        locator = item[2] if len(item) > 2 else {"paragraph_index": i}
        elements.append(
            Element(
                element_id=f"{doc_id}::e{i:04d}",
                type=etype,
                content=content,
                source_locator=locator,
            )
        )
    return Document(
        document_id=doc_id,
        source_path="/tmp/x",
        source_type=source_type,
        source_hash="a" * 64,
        parser_name="test",
        parser_version="0",
        elements=elements,
    )


def _non_ws(s: str) -> str:
    """删除全部 isspace() 字符；与 evaluation/metrics.py v1.1 口径一致。"""
    return "".join(ch for ch in s if not ch.isspace())


def assert_text_preserved(doc: Document, chunks: list[Chunk]) -> None:
    """有序非空白字符保持校验：删除全部空白后比较有序序列。"""
    expected = _non_ws(
        "".join(e.content or "" for e in doc.elements if e.type != "image")
    )
    actual = _non_ws("".join(c.text for c in chunks))
    assert expected == actual, (
        f"非空白字符不一致：expected {len(expected)} chars, "
        f"actual {len(actual)} chars"
    )


def _pieces(text: str, max_chars: int) -> list[tuple[str, str | None]]:
    """_split_long_text 输出转 (text, boundary_after) 元组列表，便于断言。"""
    return [(p.text, p.boundary_after) for p in _split_long_text(text, max_chars)]


def test_simple_two_paragraphs_one_chunk():
    doc = _make_doc([
        ("paragraph", "Hello world."),
        ("paragraph", "Another sentence."),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert len(chunks) == 1
    c = chunks[0]
    assert "Hello world." in c.text
    assert "Another sentence." in c.text
    assert len(c.source_element_ids) == 2


def test_heading_is_hard_boundary():
    doc = _make_doc([
        ("paragraph", "intro paragraph."),
        ("heading", "Chapter 2"),
        ("paragraph", "body of chapter 2."),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    # heading 是硬边界：先 intro 一个 chunk，再 Chapter 2 + body 一个 chunk
    assert len(chunks) == 2
    assert "intro paragraph" in chunks[0].text
    assert "Chapter 2" in chunks[1].text
    assert "body of chapter 2" in chunks[1].text


def test_table_is_isolated_chunk():
    doc = _make_doc([
        ("paragraph", "before table."),
        ("table", "| A | B |\n|---|---|\n| 1 | 2 |"),
        ("paragraph", "after table."),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    # before 单独 chunk → table 单独 chunk → after 单独 chunk（中间的 paragraph 不会和 table 混）
    table_chunks = [c for c in chunks if "| A | B |" in c.text]
    assert len(table_chunks) == 1
    # table chunk 只引用 table element
    tc = table_chunks[0]
    table_element_ids = [e.element_id for e in doc.elements if e.type == "table"]
    assert tc.source_element_ids == table_element_ids


def test_max_chars_force_split():
    """v5.1：纯 ASCII 无空白输入；精确 3 chunk；前两段 forced_char，末段无键。"""
    doc = _make_doc([("paragraph", "a" * 500)])
    chunks = StructuralChunker(max_chars=200).chunk(doc)
    # 精确 3 chunk，长度依次 200/200/100
    assert len(chunks) == 3
    assert [len(c.text) for c in chunks] == [200, 200, 100]
    # 每个 chunk 满足 len <= max_chars 与 char_count 一致性
    for c in chunks:
        assert len(c.text) <= 200
        assert c.metadata["char_count"] == len(c.text)
        assert c.metadata["strategy"] == "long_paragraph_sentence_split"
        assert c.metadata["max_chars"] == 200
    # 前两个 chunk split_boundary_after == "forced_char"
    assert chunks[0].metadata["split_boundary_after"] == "forced_char"
    assert chunks[1].metadata["split_boundary_after"] == "forced_char"
    # 最后一个 chunk 不含该键
    assert "split_boundary_after" not in chunks[2].metadata
    # 有序非空白字符保持
    assert_text_preserved(doc, chunks)


def test_no_loss_no_duplicate_concatenation():
    """核心：所有 chunk 文本拼接（规范化后）应等于所有 element content 拼接（规范化后）。

    normalize_text 规则：所有空白（含 \\r\\n\\t）压成单空格，strip 两端。
    """
    doc = _make_doc([
        ("heading", "Chapter 1"),
        ("paragraph", "Intro sentence one. Intro sentence two."),
        ("heading", "Chapter 2"),
        ("paragraph", "Body of chapter two. With details."),
        ("table", "| A | B |\n|---|---|\n| 1 | 2 |"),
        ("paragraph", "Final paragraph."),
    ])
    chunks = StructuralChunker(max_chars=120).chunk(doc)

    expected = " ".join(
        e.content for e in doc.elements
        if e.type != "image" and e.content
    )
    actual = " ".join(c.text for c in chunks)

    assert normalize_text(expected) == normalize_text(actual), (
        "分块前后文本不一致：\n"
        f"expected ({len(normalize_text(expected))} chars): {normalize_text(expected)[:200]}\n"
        f"actual   ({len(normalize_text(actual))} chars): {normalize_text(actual)[:200]}"
    )


def test_every_chunk_has_source_element_id():
    doc = _make_doc([
        ("paragraph", "a."),
        ("heading", "H"),
        ("paragraph", "b."),
        ("table", "x"),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    for c in chunks:
        assert len(c.source_element_ids) >= 1
    # 所有 element 至少被引用一次（除 image）
    referenced = {eid for c in chunks for eid in c.source_element_ids}
    all_ids = {e.element_id for e in doc.elements if e.type != "image" and e.content}
    assert all_ids.issubset(referenced), f"未引用: {all_ids - referenced}"


def test_max_chars_too_small_rejected():
    with pytest.raises(ValueError, match="max_chars"):
        StructuralChunker(max_chars=10)


def test_image_elements_skipped():
    doc = _make_doc([
        ("paragraph", "intro."),
        ("image", "/path/to/img.png"),  # image：content 是路径
    ])
    # image element 的 content 是路径，但 chunker._element_text 对 image 返回空
    # 所以 image 不会被分块
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    for c in chunks:
        assert "/path/to/img.png" not in c.text


def test_empty_document_yields_no_chunks():
    doc = _make_doc([])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert chunks == []


def test_normalize_text_rules():
    assert normalize_text("  hello   world  ") == "hello world"
    assert normalize_text("a\r\nb\tc") == "a b c"
    assert normalize_text("") == ""
    assert normalize_text(None) == ""


# ---- F1-F17：内部函数测试（直接调 _split_long_text，允许 max_chars < 32）----


def test_F1_helloworldx_forced_char_no_whitespace():
    """F1: 真正无空白 → forced_char（旧 "hello world", max=5 在 idx=5 恰好空白，已废）。"""
    assert _pieces("helloworldx", 5) == [
        ("hello", "forced_char"),
        ("world", "forced_char"),
        ("x", None),
    ]


def test_F2_whitespace_exactly_at_upper():
    """F2: 空白恰在 upper=8，闭区间 [4,8] 包含 upper。"""
    assert _pieces("abcdefgh world", 8) == [
        ("abcdefgh", "whitespace"),
        ("world", None),
    ]


def test_F3_rightmost_whitespace_in_window():
    """F3: 窗口 [4,8] 内空白位于 5 与 8，必须选最右 8。"""
    assert _pieces("aa bb cc dd ee ff", 8) == [
        ("aa bb cc", "whitespace"),
        ("dd ee ff", None),
    ]


def test_F4_only_early_whitespace_forces_char():
    """F4: 空白 idx=3 早于 lower=4，在 upper=8 强切；末段 "hij"（不丢 h）。"""
    assert _pieces("abc defghij", 8) == [
        ("abc defg", "forced_char"),
        ("hij", None),
    ]


def test_F5_normal_whitespace_fallback():
    """F5: 正常空白回退。"""
    assert _pieces("ab cd efghij", 8) == [
        ("ab cd", "whitespace"),
        ("efghij", None),
    ]


def test_F6_long_whitespace_run_no_empty_piece():
    """F6: 长空白跨越切点；3 piece，无纯空白 piece。"""
    assert _pieces("a" * 10 + " " * 100 + "b" * 40, 32) == [
        ("a" * 10, "whitespace"),
        ("b" * 32, "forced_char"),
        ("b" * 8, None),
    ]


def test_F7_leading_whitespace_stripped_at_entry():
    """F7: 入口 strip 消化首部空白。"""
    assert _pieces("   leading", 8) == [("leading", None)]


def test_F8_trailing_whitespace_stripped_at_entry():
    """F8: 入口 strip 消化尾部空白。"""
    assert _pieces("trailing   ", 8) == [("trailing", None)]


def test_F9_pure_whitespace_returns_empty():
    """F9: 纯空白 → 空 list。"""
    assert _pieces("   ", 8) == []


def test_F10_empty_string_returns_empty():
    """F10: 空串 → 空 list。"""
    assert _pieces("", 8) == []


def test_F11_continuous_chinese_forced_char():
    """F11: 连续中文，无空白，全 forced_char。"""
    assert _pieces("今天天气真好我们要出去玩耍", 6) == [
        ("今天天气真好", "forced_char"),
        ("我们要出去玩", "forced_char"),
        ("耍", None),
    ]


def test_F12_mixed_chinese_english_whitespace():
    """F12: 中英混排。"""
    assert _pieces("hello 你好 world", 8) == [
        ("hello 你好", "whitespace"),
        ("world", None),
    ]


def test_F13_exact_max_chars_no_split():
    """F13: 等于上限，不进硬切。"""
    assert _pieces("abc", 3) == [("abc", None)]


def test_F14_one_over_max_chars():
    """F14: 超 1 字符。"""
    assert _pieces("abcd", 3) == [
        ("abc", "forced_char"),
        ("d", None),
    ]


def test_F15_three_or_more_pieces():
    """F15: 三片以上连续切分。"""
    assert _pieces("abcdefghij", 4) == [
        ("abcd", "forced_char"),
        ("efgh", "forced_char"),
        ("ij", None),
    ]


def test_F16_natural_sentences_accumulation_no_metadata():
    """F16: 多个自然短句累积；全部 boundary_after=None。"""
    pieces = _pieces("a. b. c. d. e. f. g. h. i. j. k. l.", 20)
    assert len(pieces) >= 2
    for _text, boundary in pieces:
        assert boundary is None


@pytest.mark.parametrize(
    "sep",
    ["\t", "\n", "\r", "\u00A0", "\u2003", "\u3000"],
    ids=["TAB", "LF", "CR", "NBSP", "EM_SPACE", "IDEOGRAPHIC_SPACE"],
)
def test_F17_unicode_whitespace_parameterized(sep):
    """F17: TAB/LF/CR/NBSP/em-space/ideographic-space 均被 isspace() 命中并选为边界。

    空白 idx=5 ∈ 窗口 [4,8]。
    """
    text = f"abcde{sep}defghi"
    assert _pieces(text, 8) == [
        ("abcde", "whitespace"),
        ("defghi", None),
    ]


# ---- I1-I8：StructuralChunker 集成测试（max_chars >= 32）----


def test_I1_english_whitespace_fallback_integration():
    """I1: 英文空白回退；末段不带 metadata。"""
    text = "hello world this is a long english paragraph that needs splitting"
    doc = _make_doc([("paragraph", text)])
    chunks = StructuralChunker(max_chars=32).chunk(doc)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c.text) <= 32
        assert c.metadata["char_count"] == len(c.text)
        assert c.metadata["strategy"] == "long_paragraph_sentence_split"
        assert c.metadata["max_chars"] == 32
    ws_chunks = [
        c for c in chunks
        if c.metadata.get("split_boundary_after") == "whitespace"
    ]
    assert len(ws_chunks) >= 1
    assert "split_boundary_after" not in chunks[-1].metadata
    assert_text_preserved(doc, chunks)


def test_I2_ascii_forced_char_integration():
    """I2: 纯 ASCII 无空白 → forced_char；末段无键。"""
    doc = _make_doc([("paragraph", "a" * 200)])
    chunks = StructuralChunker(max_chars=32).chunk(doc)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c.text) <= 32
    fc_chunks = [
        c for c in chunks
        if c.metadata.get("split_boundary_after") == "forced_char"
    ]
    assert len(fc_chunks) >= 1
    assert "split_boundary_after" not in chunks[-1].metadata
    # 末段长度 = 200 mod 32 = 8
    assert len(chunks[-1].text) == 200 % 32
    assert_text_preserved(doc, chunks)


def test_I3_long_whitespace_three_chunks_integration():
    """I3: 长空白用例的三个最终 chunk 及 metadata。"""
    text = "a" * 10 + " " * 100 + "b" * 40
    doc = _make_doc([("paragraph", text)])
    chunks = StructuralChunker(max_chars=32).chunk(doc)
    assert len(chunks) == 3
    assert chunks[0].text == "a" * 10
    assert chunks[0].metadata["split_boundary_after"] == "whitespace"
    assert chunks[1].text == "b" * 32
    assert chunks[1].metadata["split_boundary_after"] == "forced_char"
    assert chunks[2].text == "b" * 8
    assert "split_boundary_after" not in chunks[2].metadata
    assert_text_preserved(doc, chunks)


def test_I4_natural_sentence_capacity_flush():
    """I4: 自然短句容量 flush；所有 chunk 不带 split_boundary_after。

    原文总长 19 + 1 + 19 + 1 + 21 = 61 字符（含两个句间空格）。
    max_chars=64 时 61 ≤ 64 不进入 3a；max_chars=32 时 61 > 32 进入 3a。
    三个自然短句长度 19/19/21，单独均 ≤ 32，不触发硬切。
    因容量不足分别 flush；所有最终 chunk 的 boundary_after 必须为 None。
    """
    text = "short sentence one. short sentence two. short sentence three."
    # 校验长度计算：19 + 1 + 19 + 1 + 21 = 61
    assert len(text) == 61
    sentences = [
        "short sentence one.",
        "short sentence two.",
        "short sentence three.",
    ]
    assert [len(s) for s in sentences] == [19, 19, 21]

    doc = _make_doc([("paragraph", text)])
    chunks = StructuralChunker(max_chars=32).chunk(doc)
    assert len(chunks) == 3
    for c in chunks:
        assert "split_boundary_after" not in c.metadata
        assert c.metadata["strategy"] == "long_paragraph_sentence_split"
    assert [c.text for c in chunks] == sentences
    assert_text_preserved(doc, chunks)


def test_I5_last_chunk_no_metadata():
    """I5: 末段 chunk 无 split_boundary_after 键。"""
    text = "a" * 40 + ". b" * 10
    doc = _make_doc([("paragraph", text)])
    chunks = StructuralChunker(max_chars=32).chunk(doc)
    assert len(chunks) >= 2
    assert "split_boundary_after" not in chunks[-1].metadata
    assert_text_preserved(doc, chunks)


def test_I6_table_chunk_no_metadata():
    """I6: table 路径不进入 3a，metadata 不含 split_boundary_after。"""
    doc = _make_doc([
        ("paragraph", "before."),
        ("table", "| A | B |\n|---|---|\n| 1 | 2 |"),
        ("paragraph", "after."),
    ])
    chunks = StructuralChunker(max_chars=32).chunk(doc)
    table_chunks = [c for c in chunks if "| A | B |" in c.text]
    assert len(table_chunks) == 1
    tc = table_chunks[0]
    assert "split_boundary_after" not in tc.metadata
    assert tc.metadata["strategy"] == "isolated_table"


def test_I7_chunk_id_consecutive_after_empty_element():
    """I7: 跳过空白元素时 chunk_id 仍连续无空洞。

    element content="   "（仅空白）：Element 验证要求 content 或 resource_path
    非空，纯空串通不过；用空白串通过验证，_element_text 再 strip 成空串跳过。
    """
    doc = _make_doc([
        ("paragraph", "   "),
        ("paragraph", "a" * 50),
    ])
    chunks = StructuralChunker(max_chars=32).chunk(doc)
    assert len(chunks) == 2
    assert chunks[0].chunk_id.endswith("::c0000")
    assert chunks[1].chunk_id.endswith("::c0001")


def test_I8_identical_input_identical_output():
    """I8: 相同输入两次调用结果完全一致（含 metadata、chunk_id、char_count）。"""
    doc = _make_doc([("paragraph", "a" * 50)])
    chunker = StructuralChunker(max_chars=32)
    chunks1 = chunker.chunk(doc)
    chunks2 = chunker.chunk(doc)
    assert chunks1 == chunks2
