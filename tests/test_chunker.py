"""结构分块器的单元测试。"""

from __future__ import annotations

import pytest

from app.chunkers import StructuralChunker, normalize_text
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
    long_text = "Sentence one. " * 100  # ~1500 chars
    doc = _make_doc([("paragraph", long_text.strip())])
    chunks = StructuralChunker(max_chars=200).chunk(doc)
    assert len(chunks) >= 2
    for c in chunks:
        # 单 chunk 文本应大致不超过 max_chars（句子边界可能略超，但不应翻倍）
        assert len(c.text) <= 250, f"chunk {c.chunk_id} too long: {len(c.text)}"


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
