r"""app/chunkers/structural.py 边角测试 - 第十四轮（Round 1478）。

新角度（probe 实证）真 heading 不切句 + 空文本类型跳过
的并段效应 + isolated 交替（edges1-13 未碰过；edges13 的
test_header_overlong_splits 用的是 **type='header'**——
非 heading，走的是普通超长分支，真 heading 的超长行为未锁）：
- **真 heading 超长不切**：type='heading' 150 字符 >
  max_chars=100 → 单个 150 字符 chunk、strategy=
  'sequential'（heading 分支只 push 不 split，**允许超长
  chunk**；span 0..150）
- **heading 恰好 = max_chars 时逼 flush**：100 字符
  heading + 后续 para → projected 105 > 100 → heading
  单独成 100 字符 chunk、para 成第二个 chunk（各 sequential）
- **纯空白 table 被跳过**：para + '   ' table + para →
  table 零 chunk、两段**并成一个** sequential chunk（双
  source_element_ids 跨过 table）
- **image 跳过并段**：para + image(resource_path) + para
  → 'one two three four' 单 chunk 双 ids
- **caption/table/caption 交替**：三个 isolated chunk 依
  序 c0000-c0002，strategy 依次 isolated_caption/
  isolated_table/isolated_caption
- **超长 list_item 走切句路径**：600 字符 list_item → 6 个
  chunk 全部 long_paragraph_sentence_split、每个 ≤ max_chars
"""

from __future__ import annotations

from app.models import Document, Element
from app.chunkers.structural import \
    StructuralChunker

DID = "doc-edge14"


def _el(i, t, content, **kw):
    return Element(
        element_id=f"{DID}::e{i:04d}",
        type=t, content=content,
        parent_id=None,
        source_locator={"line": 1},
        confidence=0.95, metadata={},
        **kw)


def _doc(els):
    return Document(
        document_id=DID, source_path="x",
        source_type="pdf", source_hash="h",
        parser_name="p", parser_version="v",
        elements=els, chunks=[], relations=[],
        warnings=[], errors=[], metadata={})


def _chunks(els, max_chars=100):
    return StructuralChunker(
        max_chars=max_chars).chunk(
        _doc(els))


# ---------- 真 heading 超长 ----------

def test_oversized_heading_not_split():
    chunks = _chunks([
        _el(0, "heading", "H" * 150)])
    assert len(chunks) == 1
    c = chunks[0]
    assert len(c.text) == 150
    assert c.metadata == {
        "strategy": "sequential",
        "max_chars": 100,
        "char_count": 150,
    }
    assert c.source_spans == [{
        "element_id": f"{DID}::e0000",
        "start": 0, "end": 150,
    }]


def test_exact_max_heading_forces_flush():
    chunks = _chunks([
        _el(0, "heading", "E" * 100),
        _el(1, "paragraph", "tail")])
    assert [(len(c.text),
             c.metadata["strategy"])
            for c in chunks] == [
        (100, "sequential"),
        (4, "sequential"),
    ]
    assert chunks[0].source_element_ids \
        == [f"{DID}::e0000"]
    assert chunks[1].source_element_ids \
        == [f"{DID}::e0001"]


# ---------- 空文本类型跳过 ----------

def test_ws_table_skipped_paras_merge():
    chunks = _chunks([
        _el(0, "paragraph", "alpha beta"),
        _el(1, "table", "   "),
        _el(2, "paragraph",
            "gamma delta")])
    assert len(chunks) == 1
    c = chunks[0]
    assert c.text == \
        "alpha beta gamma delta"
    assert c.source_element_ids == [
        f"{DID}::e0000",
        f"{DID}::e0002",
    ]


def test_image_skipped_paras_merge():
    img = Element(
        element_id=f"{DID}::e0001",
        type="image", content=None,
        resource_path="img.png",
        parent_id=None,
        source_locator={"page": 1},
        confidence=0.9,
        metadata={"alt": ""})
    chunks = _chunks([
        _el(0, "paragraph", "one two"),
        img,
        _el(2, "paragraph", "three four")])
    assert len(chunks) == 1
    assert chunks[0].text == \
        "one two three four"
    assert chunks[0].source_element_ids == [
        f"{DID}::e0000",
        f"{DID}::e0002",
    ]


# ---------- isolated 交替 ----------

def test_caption_table_caption_order():
    chunks = _chunks([
        _el(0, "caption", "cap one"),
        _el(1, "table", "| a | b |"),
        _el(2, "caption", "cap two")])
    assert [(c.chunk_id.split("::")[-1],
             c.text,
             c.metadata["strategy"])
            for c in chunks] == [
        ("c0000", "cap one",
         "isolated_caption"),
        ("c0001", "| a | b |",
         "isolated_table"),
        ("c0002", "cap two",
         "isolated_caption"),
    ]


# ---------- 超长 list_item ----------

def test_long_list_item_sentence_split():
    long_li = " ".join(
        f"item{i} sentence."
        for i in range(30))
    chunks = _chunks([
        _el(0, "list_item", long_li)])
    assert len(chunks) >= 2
    assert all(
        c.metadata["strategy"] ==
        "long_paragraph_sentence_split"
        for c in chunks)
    assert all(
        len(c.text) <= 100
        for c in chunks)
    assert all(
        c.source_element_ids ==
        [f"{DID}::e0000"]
        for c in chunks)
