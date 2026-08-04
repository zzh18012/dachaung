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


# ---------- source_spans ----------


def test_source_spans_simple_two_paragraphs():
    """两段都进同一个 chunk：spans 给出每段在 el.content 中的全区间。"""
    doc = _make_doc([
        ("paragraph", "Hello world."),
        ("paragraph", "Another sentence."),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert len(chunks) == 1
    spans = chunks[0].source_spans
    assert len(spans) == 2
    # 第 1 个 span：覆盖第 1 段全部
    assert spans[0]["element_id"] == doc.elements[0].element_id
    assert spans[0]["start"] == 0
    assert spans[0]["end"] == len("Hello world.")
    # 第 2 个 span：覆盖第 2 段全部
    assert spans[1]["element_id"] == doc.elements[1].element_id
    assert spans[1]["start"] == 0
    assert spans[1]["end"] == len("Another sentence.")


def test_source_spans_heading_is_hard_boundary():
    """heading 起新 chunk：第 2 chunk 的 spans 含 heading 与下一段。"""
    doc = _make_doc([
        ("paragraph", "intro paragraph."),
        ("heading", "Chapter 2"),
        ("paragraph", "body of chapter 2."),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert len(chunks) == 2
    # 第 1 chunk：只有 intro paragraph
    assert len(chunks[0].source_spans) == 1
    assert chunks[0].source_spans[0]["element_id"] == doc.elements[0].element_id
    # 第 2 chunk：heading + body
    assert len(chunks[1].source_spans) == 2
    assert chunks[1].source_spans[0]["element_id"] == doc.elements[1].element_id  # heading
    assert chunks[1].source_spans[1]["element_id"] == doc.elements[2].element_id  # body


def test_source_spans_table_isolated_chunk():
    """table 单独成 chunk：spans 仅含 table 一项。"""
    doc = _make_doc([
        ("paragraph", "before table."),
        ("table", "| A | B |\n|---|---|\n| 1 | 2 |"),
        ("paragraph", "after table."),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    table_chunks = [c for c in chunks if "| A | B |" in c.text]
    assert len(table_chunks) == 1
    tc = table_chunks[0]
    assert len(tc.source_spans) == 1
    assert tc.source_spans[0]["element_id"] == doc.elements[1].element_id
    table_text = doc.elements[1].content or ""
    assert tc.source_spans[0]["start"] == 0
    assert tc.source_spans[0]["end"] == len(table_text)


def test_source_spans_long_paragraph_within_element():
    """超长段落被切：每片 span 都在该 element.content 中，且互不重叠。"""
    long_text = "Sentence one. " * 50  # 足够长，必被切
    doc = _make_doc([("paragraph", long_text)])
    chunks = StructuralChunker(max_chars=80).chunk(doc)
    assert len(chunks) > 1
    eid = doc.elements[0].element_id
    # 每个 chunk 的 span 都指向同一 element
    for c in chunks:
        assert len(c.source_spans) == 1
        assert c.source_spans[0]["element_id"] == eid
        s, e = c.source_spans[0]["start"], c.source_spans[0]["end"]
        # 区间在 element.content 范围内
        assert 0 <= s < e <= len(long_text)
        # span 对应的 element.content 切片应包含 chunk 的非空白字符序列
        # （粗校验：span 切片非空）
        assert long_text[s:e].strip()
    # 所有 chunk 的 span 区间应当连续且覆盖（允许有空白间隙）
    span_starts = sorted(c.source_spans[0]["start"] for c in chunks)
    span_ends = sorted(c.source_spans[0]["end"] for c in chunks)
    assert span_starts[0] == 0
    assert span_ends[-1] <= len(long_text)


def test_source_spans_element_with_leading_trailing_whitespace():
    """element.content 有首尾空白时，span 应指向 stripped 部分（不含首尾空白）。"""
    doc = _make_doc([("paragraph", "  Hello world.  ")])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert len(chunks) == 1
    span = chunks[0].source_spans[0]
    assert span["start"] == 2  # 跳过 2 个前导空格
    assert span["end"] == 2 + len("Hello world.")
    # element.content 切片应等于 stripped text
    assert doc.elements[0].content[span["start"]:span["end"]] == "Hello world."


def test_source_spans_chunk_text_alignment():
    """所有 chunk 的 source_spans 区间内的 element.content 拼接，
    其非空白字符序列应等于所有 chunk.text 的非空白字符序列。

    这是 source_spans 的核心契约：用 span 切回原始 element.content，
    能恢复 chunk.text 的非空白内容。
    """
    paragraphs = [
        "First paragraph with several words.",
        "Second paragraph, also non-trivial.",
        "Third one ends with period.",
    ]
    doc = _make_doc([("paragraph", p) for p in paragraphs])
    chunks = StructuralChunker(max_chars=50).chunk(doc)
    assert len(chunks) >= 2

    # 用 span 把每个 chunk 的字符从对应 element.content 里抽出来
    el_by_id = {e.element_id: e for e in doc.elements}
    extracted_non_ws_parts = []
    for c in chunks:
        for span in c.source_spans:
            el = el_by_id[span["element_id"]]
            piece = (el.content or "")[span["start"]:span["end"]]
            extracted_non_ws_parts.append(_non_ws(piece))
    extracted = "".join(extracted_non_ws_parts)
    actual = _non_ws("".join(c.text for c in chunks))
    assert extracted == actual, (
        f"span 抽取与 chunk.text 不一致：extracted={extracted!r}, actual={actual!r}"
    )


def test_source_spans_empty_when_no_text():
    """所有 element 都是空内容 → chunker 不产生任何 chunk（无 spans 可言）。"""
    # Element 强制要求 content 或 resource_path 之一非空，所以无法真正测试
    # "all empty"。改成：单 image element，不参与分块。
    doc = _make_doc([("image", "alt text")])  # image 走 resource_path
    # 但 _make_doc 用 content 字段；为 image 加 resource_path
    img = doc.elements[0]
    doc.elements[0] = Element(
        element_id=img.element_id, type="image",
        source_locator=img.source_locator,
        content=None, resource_path="x.png",
    )
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert chunks == []


def test_source_spans_in_to_dict_output():
    """Chunk.to_dict() 包含 source_spans 字段，schema 校验通过。"""
    from app.schema import validate

    doc = _make_doc([("paragraph", "Hello."), ("paragraph", "World.")])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    doc.chunks = chunks
    d = doc.to_dict()
    # 校验整体 document schema（含 source_spans 子结构）
    validate(d)
    # 第 1 chunk 的 dict 形式确实含 source_spans
    assert "source_spans" in d["chunks"][0]
    assert len(d["chunks"][0]["source_spans"]) == 2


# ---- _element_text_with_span 直接单元测试 ----


def _element_span(el: Element) -> tuple[str, int, int]:
    """调 StructuralChunker._element_text_with_span 的便捷封装。"""
    return StructuralChunker(max_chars=800)._element_text_with_span(el)


def test_element_text_with_span_normal_text():
    el = Element(element_id="x::e0", type="paragraph", content="hello world",
                 source_locator={})
    assert _element_span(el) == ("hello world", 0, 11)


def test_element_text_with_span_leading_whitespace():
    """前导空白不算入 stripped text 的字符范围起点之外。"""
    el = Element(element_id="x::e0", type="paragraph", content="   hello",
                 source_locator={})
    stripped, start, end = _element_span(el)
    assert stripped == "hello"
    assert start == 3
    assert end == 8  # 3 + 5


def test_element_text_with_span_trailing_whitespace():
    el = Element(element_id="x::e0", type="paragraph", content="hello   ",
                 source_locator={})
    stripped, start, end = _element_span(el)
    assert stripped == "hello"
    assert start == 0
    assert end == 5


def test_element_text_with_span_both_side_whitespace():
    el = Element(element_id="x::e0", type="paragraph", content="  hi  ",
                 source_locator={})
    stripped, start, end = _element_span(el)
    assert stripped == "hi"
    assert start == 2
    assert end == 4


def test_element_text_with_span_empty_content():
    """content="" 但有 resource_path（满足 Element 不变量）。"""
    el = Element(element_id="x::e0", type="paragraph", content="",
                 resource_path="placeholder", source_locator={})
    assert _element_span(el) == ("", 0, 0)


def test_element_text_with_span_whitespace_only():
    el = Element(element_id="x::e0", type="paragraph", content="   \t\n  ",
                 source_locator={})
    assert _element_span(el) == ("", 0, 0)


def test_element_text_with_span_image_returns_empty():
    """image element 不参与分块（_element_text_with_span 强制返回空）。"""
    el = Element(element_id="x::e0", type="image", content=None,
                 resource_path="/tmp/x.png", source_locator={})
    assert _element_span(el) == ("", 0, 0)


def test_element_text_with_span_none_content():
    """content=None 但有 resource_path（满足 Element 不变量）。"""
    el = Element(element_id="x::e0", type="paragraph", content=None,
                 resource_path="placeholder", source_locator={})
    assert _element_span(el) == ("", 0, 0)


# ---- _split_long_text 边界直接测试 ----


def test_split_long_text_empty_string():
    assert _split_long_text("", 100) == []


def test_split_long_text_whitespace_only():
    assert _split_long_text("   \n\t  ", 100) == []


def test_split_long_text_below_max_returns_single_piece():
    """text ≤ max_chars → 单 piece，boundary_after=None，覆盖 [0, len)。"""
    pieces = _split_long_text("hello world", 100)
    assert len(pieces) == 1
    assert pieces[0].text == "hello world"
    assert pieces[0].boundary_after is None
    assert pieces[0].start == 0
    assert pieces[0].end == 11


def test_split_long_text_no_delimiter_no_whitespace_all_forced():
    """无句子分隔符 + 无空白 → 全 forced_char。"""
    pieces = _split_long_text("abcdefghij", 3)
    # 验证所有非末段 piece 都是 forced_char
    for p in pieces[:-1]:
        assert p.boundary_after == "forced_char"
    # 末段是 None
    assert pieces[-1].boundary_after is None
    # 不丢字符
    assert "".join(p.text for p in pieces) == "abcdefghij"


def test_split_long_text_multiple_consecutive_delimiters():
    """连续句子分隔符（"Hello.. World"）只在最后一个 . 后切（要求其后再有空白）。"""
    pieces = _split_long_text("Hello.. World", 100)
    # 整体 ≤ max_chars，应当合并为单 piece
    assert len(pieces) == 1
    assert pieces[0].text == "Hello.. World"


# ---- 集成：caption 隔离 / 连续 heading / heading-then-table / list_item ----


def test_caption_is_isolated_chunk():
    """caption element 单独成 chunk（mirror of I6 for table）。"""
    doc = _make_doc([
        ("paragraph", "intro text."),
        ("caption", "Figure 1. Diagram"),
        ("paragraph", "outro text."),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    # caption 必须单独成 chunk
    assert len(chunks) == 3
    # 中间 chunk 是 caption
    assert chunks[1].text == "Figure 1. Diagram"
    assert chunks[1].metadata["strategy"] == "isolated_caption"
    assert chunks[1].source_element_ids == [doc.elements[1].element_id]


def test_consecutive_headings_each_own_chunk():
    """3 个连续 heading → 3 个独立 chunk（heading 是硬边界）。"""
    doc = _make_doc([
        ("heading", "Chapter 1"),
        ("heading", "Chapter 2"),
        ("heading", "Chapter 3"),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert len(chunks) == 3
    assert [c.text for c in chunks] == ["Chapter 1", "Chapter 2", "Chapter 3"]


def test_heading_then_table_yields_two_chunks():
    """heading 紧跟 table → 2 个 chunk（heading + table 各自独立）。"""
    doc = _make_doc([
        ("heading", "Title"),
        ("table", "| a | b |\n|---|---|\n| 1 | 2 |"),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert len(chunks) == 2
    assert chunks[0].text == "Title"
    assert chunks[1].text == "| a | b |\n|---|---|\n| 1 | 2 |"
    assert chunks[1].metadata["strategy"] == "isolated_table"


def test_list_item_treated_as_paragraph():
    """list_item 走"其他"分支，与 paragraph 一样累积到当前 chunk。"""
    doc = _make_doc([
        ("list_item", "first item"),
        ("list_item", "second item"),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    # 两个 list_item 都应进入同一个 chunk
    assert len(chunks) == 1
    assert "first item" in chunks[0].text
    assert "second item" in chunks[0].text
    assert len(chunks[0].source_element_ids) == 2


def test_table_then_paragraph_buffer_reset():
    """table 隔离后，新 paragraph 进入新 buf（不与 table 同 chunk）。"""
    doc = _make_doc([
        ("paragraph", "before."),
        ("table", "| a | b |"),
        ("paragraph", "after."),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    # 3 chunks：before-paragraph, table, after-paragraph
    assert len(chunks) == 3
    assert chunks[0].text == "before."
    assert chunks[1].text == "| a | b |"
    assert chunks[2].text == "after."


def test_chunks_preserve_input_order_for_no_loss():
    """排序不变量：chunks 的非空白拼接 == elements 的非空白拼接（有序）。"""
    doc = _make_doc([
        ("heading", "Intro"),
        ("paragraph", "Sentence one. Sentence two."),
        ("table", "| x | y |"),
        ("caption", "Figure 1."),
        ("paragraph", "Final paragraph here."),
    ])
    chunks = StructuralChunker(max_chars=50).chunk(doc)
    assert_text_preserved(doc, chunks)


def test_paragraph_then_long_paragraph_boundary_resets():
    """短 paragraph + 长 paragraph（超 max_chars）→ 长 paragraph 单独按句切。"""
    long_text = "Sentence one. Sentence two. Sentence three. Sentence four."
    doc = _make_doc([
        ("paragraph", "short intro."),
        ("paragraph", long_text),
    ])
    # max_chars 最小值 32；让长 paragraph（>50 chars）必须切
    chunks = StructuralChunker(max_chars=32).chunk(doc)
    # 短 intro 进 chunk 0；长 paragraph 因超长，先 flush buf（emit chunk 0），
    # 然后自身按句切，至少产生 1 个 chunk
    assert len(chunks) >= 2
    assert chunks[0].text == "short intro."
    # 长 paragraph 切片累计不丢字符
    long_chunks_text = " ".join(c.text for c in chunks[1:])
    assert _non_ws(long_chunks_text) == _non_ws(long_text)


# ---------- 边角与缺漏补强（Round 28） ----------


# normalize_text 直接单测


def test_normalize_text_idempotent():
    """规范化已经是规范化形式时再次规范化应保持不变。"""
    s = "hello world"
    assert normalize_text(s) == s
    s2 = "a"
    assert normalize_text(s2) == s2


def test_normalize_text_mixed_unicode_whitespace():
    """Unicode 空白（NBSP、em space、tab）应被压成单空格。"""
    s = "a b c\td"
    assert normalize_text(s) == "a b c d"


def test_normalize_text_only_whitespace_returns_empty():
    """全是空白 → 空串。"""
    assert normalize_text("   \t\n\r  ") == ""
    assert normalize_text("　 ") == ""


# StructuralChunker.__init__ 验证


def test_structural_chunker_max_chars_minimum_accepted():
    """max_chars = 32 应被接受（边界值）。"""
    c = StructuralChunker(max_chars=32)
    assert c.max_chars == 32


def test_structural_chunker_max_chars_below_minimum_rejected():
    """max_chars = 31 应抛 ValueError。"""
    with pytest.raises(ValueError, match="max_chars"):
        StructuralChunker(max_chars=31)


def test_structural_chunker_max_chars_zero_rejected():
    """max_chars = 0 应抛 ValueError。"""
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=0)


def test_structural_chunker_max_chars_negative_rejected():
    """负数 max_chars 应抛 ValueError。"""
    with pytest.raises(ValueError):
        StructuralChunker(max_chars=-100)


def test_structural_chunker_default_max_chars_is_800():
    """默认 max_chars = 800。"""
    c = StructuralChunker()
    assert c.max_chars == 800


# _ChunkBuffer 直接单测


def test_chunk_buffer_flush_empty_returns_none():
    from app.chunkers.structural import _ChunkBuffer
    buf = _ChunkBuffer(document_id="d1")
    assert buf.flush(strategy="x", max_chars=800) is None
    assert buf.is_empty()


def test_chunk_buffer_flush_whitespace_only_returns_none():
    """只有空白 parts → flush 时 text.strip() = "" → 返回 None。"""
    from app.chunkers.structural import _ChunkBuffer
    buf = _ChunkBuffer(document_id="d1")
    buf.push_text("   ", "e1", 0, 3)
    buf.push_text("\t\n", "e1", 3, 5)
    result = buf.flush(strategy="x", max_chars=800)
    assert result is None


def test_chunk_buffer_length_sums_part_lengths():
    from app.chunkers.structural import _ChunkBuffer
    buf = _ChunkBuffer(document_id="d1")
    assert buf.length() == 0
    buf.push_text("hello", "e1", 0, 5)
    assert buf.length() == 5
    buf.push_text("world", "e2", 0, 5)
    assert buf.length() == 10


def test_chunk_buffer_source_element_ids_deduplicated():
    """同一 element 引用多次 → source_element_ids 去重，但顺序保留。"""
    from app.chunkers.structural import _ChunkBuffer
    buf = _ChunkBuffer(document_id="d1", counter=0)
    buf.push_text("a", "e1", 0, 1)
    buf.push_text("b", "e2", 0, 1)
    buf.push_text("c", "e1", 1, 2)  # e1 再次出现
    chunk = buf.flush(strategy="x", max_chars=800)
    assert chunk is not None
    # 顺序保留，去重
    assert chunk.source_element_ids == ["e1", "e2"]


def test_chunk_buffer_source_spans_preserved_per_part():
    """每个 part 一条 source_span，即使 element_id 相同。"""
    from app.chunkers.structural import _ChunkBuffer
    buf = _ChunkBuffer(document_id="d1", counter=0)
    buf.push_text("a", "e1", 0, 1)
    buf.push_text("b", "e1", 5, 6)  # 同 element 不同 span
    chunk = buf.flush(strategy="x", max_chars=800)
    assert chunk is not None
    assert len(chunk.source_spans) == 2
    assert chunk.source_spans[0] == {"element_id": "e1", "start": 0, "end": 1}
    assert chunk.source_spans[1] == {"element_id": "e1", "start": 5, "end": 6}


def test_chunk_buffer_chunk_id_includes_counter():
    """chunk_id 格式：{document_id}::c{counter:04d}。"""
    from app.chunkers.structural import _ChunkBuffer
    buf = _ChunkBuffer(document_id="doc-xyz", counter=7)
    buf.push_text("text", "e1", 0, 4)
    chunk = buf.flush(strategy="x", max_chars=800)
    assert chunk is not None
    assert chunk.chunk_id == "doc-xyz::c0007"


def test_chunk_buffer_flush_resets_parts():
    """flush 后 parts 应被清空，复用 buf 时是新开始。"""
    from app.chunkers.structural import _ChunkBuffer
    buf = _ChunkBuffer(document_id="d1", counter=0)
    buf.push_text("first", "e1", 0, 5)
    buf.flush(strategy="x", max_chars=800)
    assert buf.is_empty()
    # 再次 push 不会带上之前的 part
    buf.push_text("second", "e2", 0, 6)
    chunk = buf.flush(strategy="y", max_chars=800)
    assert chunk is not None
    assert chunk.text == "second"
    assert chunk.source_element_ids == ["e2"]


def test_chunk_buffer_metadata_includes_strategy_and_max_chars():
    """flush 出来的 chunk 的 metadata 含 strategy / max_chars / char_count。"""
    from app.chunkers.structural import _ChunkBuffer
    buf = _ChunkBuffer(document_id="d1", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    chunk = buf.flush(strategy="custom_strategy", max_chars=123)
    assert chunk is not None
    assert chunk.metadata["strategy"] == "custom_strategy"
    assert chunk.metadata["max_chars"] == 123
    assert chunk.metadata["char_count"] == 5


# 集成：仅 heading / 仅 image / 已有 chunks 等边角


def test_only_headings_each_becomes_own_chunk():
    """3 个 heading → 至少 3 个 chunk（heading 是硬边界）。"""
    doc = _make_doc([
        ("heading", "H1"),
        ("heading", "H2"),
        ("heading", "H3"),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert len(chunks) == 3
    assert [c.text for c in chunks] == ["H1", "H2", "H3"]


def test_heading_then_image_then_paragraph():
    """heading → image（被跳过）→ paragraph：image 不产生 chunk。"""
    elements = [
        Element(element_id="d::e0", type="heading", content="Title",
                source_locator={"paragraph_index": 0}),
        Element(element_id="d::e1", type="image", resource_path="/tmp/x.png",
                source_locator={"paragraph_index": 1}),
        Element(element_id="d::e2", type="paragraph", content="body",
                source_locator={"paragraph_index": 2}),
    ]
    doc = Document(
        document_id="d", source_path="/tmp/x", source_type="docx",
        source_hash="a" * 64, parser_name="test", parser_version="0",
        elements=elements,
    )
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    # image 不参与，应只剩 heading + paragraph（合在一起因为长度都小）
    texts = " ".join(c.text for c in chunks)
    assert "Title" in texts
    assert "body" in texts
    # 没有任何 chunk 应包含 resource_path 信息（chunk.text 是 element content，
    # image 的 content 是 None，不会进入 chunk）
    for c in chunks:
        assert "/tmp/x.png" not in c.text


def test_chunker_ignores_existing_chunks_field():
    """Document 已有 chunks 字段时，chunk() 不读旧 chunks，返回新切片。"""
    doc = _make_doc([("paragraph", "hello world")])
    # 给 doc 预置一些 chunks（不应影响结果）
    pre_chunk = Chunk(
        chunk_id="pre::c0", text="preset",
        source_element_ids=["d-hash0000000001::e0000"],
    )
    doc.chunks = [pre_chunk]
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    # 新 chunks 不应包含 preset
    assert all(c.chunk_id != "pre::c0" for c in chunks)
    assert len(chunks) == 1
    assert chunks[0].text == "hello world"


def test_chunk_with_list_item_accumulates_like_paragraph():
    """list_item 与 paragraph 一样累积到当前 buf。"""
    doc = _make_doc([
        ("list_item", "first item"),
        ("list_item", "second item"),
        ("list_item", "third item"),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    # 三个都应在一个 chunk 里（总长度 << 800）
    assert len(chunks) == 1
    assert "first" in chunks[0].text
    assert "second" in chunks[0].text
    assert "third" in chunks[0].text


def test_caption_treated_as_isolated():
    """caption 是 isolated 类型（与 table/image 一样单独成 chunk）。"""
    doc = _make_doc([
        ("paragraph", "intro"),
        ("caption", "Figure 1: Diagram"),
        ("paragraph", "outro"),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    # intro 单独成 chunk；caption 单独成 chunk；outro 单独成 chunk
    assert len(chunks) == 3
    assert chunks[1].text == "Figure 1: Diagram"
    assert chunks[1].metadata["strategy"] == "isolated_caption"


def test_table_metadata_strategy_is_isolated_table():
    doc = _make_doc([
        ("paragraph", "before"),
        ("table", "| a | b |"),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    table_chunk = next(c for c in chunks if "a" in c.text and "b" in c.text)
    assert table_chunk.metadata["strategy"] == "isolated_table"

