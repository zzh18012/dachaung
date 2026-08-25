r"""app/chunkers/structural.py 边角测试 - 第十五轮（Round 1499）。

新角度（probe 实证）isolated 超长不切 + header/footer
流（edges1-14 未碰；R1478 只锁了 heading 超长不切）：

- **超长 table 不切**：373 字符 table > max_chars=100 →
  单个超长 chunk、strategy='isolated_table'（table 分支
  只 push 不 split，与 heading 超长同性质的"允许超长
  chunk"）
- **超长 caption 不切**：239 字符 → 单个 isolated_caption
  超长 chunk
- **header/footer 是普通文本流**：单独成 sequential
  chunk；**夹在段间不打断缓冲**：para+header+para → 单
  chunk 'one two hdr three four' 三 ids 连续（header 不
  触发 flush/reset）
"""

from __future__ import annotations

from app.chunkers.structural import \
    StructuralChunker

from tests.test_chunker_edges14 \
    import _doc, _el


def _chunks(els, max_chars=100):
    return StructuralChunker(
        max_chars=max_chars).chunk(
        _doc(els))


# ---------- isolated 超长不切 ----------

def test_oversized_table_not_split():
    els = [_el(0, "table",
               "| a |\n| --- |\n"
               + "| x | " * 60)]
    chunks = _chunks(els)
    assert len(chunks) == 1
    c = chunks[0]
    assert c.metadata == {
        "strategy": "isolated_table",
        "max_chars": 100,
        "char_count": 373,
    }
    assert len(c.text) == 373
    assert c.source_element_ids == [els[0].element_id]


def test_oversized_caption_not_split():
    els = [_el(0, "caption", "cap " * 60)]
    chunks = _chunks(els)
    assert len(chunks) == 1
    c = chunks[0]
    assert c.metadata == {
        "strategy": "isolated_caption",
        "max_chars": 100,
        "char_count": 239,
    }
    assert len(c.text) == 239


# ---------- header/footer 文本流 ----------

def test_header_own_sequential_chunk():
    chunks = _chunks(
        [_el(0, "header",
             "page header text")])
    assert len(chunks) == 1
    c = chunks[0]
    assert c.text == "page header text"
    assert c.metadata["strategy"] == \
        "sequential"


def test_footer_own_sequential_chunk():
    chunks = _chunks(
        [_el(0, "footer",
             "page footer text")])
    assert len(chunks) == 1
    assert chunks[0].text == \
        "page footer text"
    assert chunks[0].metadata[
        "strategy"] == "sequential"


def test_header_between_paras_merges():
    els = [
        _el(0, "paragraph", "one two"),
        _el(1, "header", "hdr"),
        _el(2, "paragraph", "three four"),
    ]
    chunks = _chunks(els)
    assert len(chunks) == 1
    c = chunks[0]
    assert c.text == \
        "one two hdr three four"
    assert c.source_element_ids == [
        e.element_id for e in els]
    assert c.metadata["strategy"] == \
        "sequential"
