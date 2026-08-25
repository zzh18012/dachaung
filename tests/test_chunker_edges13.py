r"""app/chunkers/structural.py 边角测试 - 第十三轮（Round 1464）。

新角度（probe 实证）header/footer 归并 + 空白跳过 + 计数器
跨策略连续（edges1-12 与 base 未碰过；base 已覆盖 caption
隔离/连续 heading/image 跳过/ids 去重，勿重复）：
- header/footer **当普通段落累积**：'head text foot text' 单
  chunk（strategy sequential）；夹在段落间也不 flush
- 纯空白 element **跳过**：' \\n\\t ' 无 chunk；夹在两个真
  段落间 → 两段**并成同一 chunk**（ids [e0, e2]）
- content=None 且只有 resource_path 的**非 image** element
  同样跳过（text 判空不区分类型）
- chunk_id 计数器**跨策略连续**：isolated_table c0000 →
  长段切分 c0001/c0002 → sequential c0003（长段路径直接
  递增 counter，缓冲 flush 前同步回 buf）
- header 超长同样走 long_paragraph_sentence_split（含
  split_boundary_after=whitespace / None 尾段）
"""

from __future__ import annotations

from app.models import Document, Element
from app.chunkers.structural import \
    StructuralChunker


def _el(eid, etype, content=None,
        **kw):
    return Element(
        element_id=eid, type=etype,
        source_locator={}, content=content,
        **kw)


def _doc(elements):
    return Document(
        document_id="d", source_path="x",
        source_type="pdf", source_hash="h",
        parser_name="p", parser_version="1",
        elements=elements)


def _chunks(elements, max_chars=100):
    return StructuralChunker(
        max_chars=max_chars).chunk(
        _doc(elements))


# ---------- header/footer 归并 ----------

def test_header_footer_accumulate():
    chunks = _chunks([
        _el("e0", "header", "head text"),
        _el("e1", "footer", "foot text"),
    ])
    assert len(chunks) == 1
    assert chunks[0].text == \
        "head text foot text"
    assert chunks[0].source_element_ids \
        == ["e0", "e1"]
    assert chunks[0].metadata[
        "strategy"] == "sequential"


def test_header_between_paragraphs_merges():
    chunks = _chunks([
        _el("e0", "paragraph", "p1"),
        _el("e1", "header", "RUN HEAD"),
        _el("e2", "paragraph", "p2"),
    ])
    assert len(chunks) == 1
    assert chunks[0].text == \
        "p1 RUN HEAD p2"
    assert chunks[0].source_element_ids \
        == ["e0", "e1", "e2"]


# ---------- 空白跳过 ----------

def test_whitespace_only_element_skipped():
    chunks = _chunks([
        _el("e0", "paragraph", "  \n\t  "),
        _el("e1", "paragraph", "real"),
    ])
    assert len(chunks) == 1
    assert chunks[0].text == "real"
    assert chunks[0].source_element_ids \
        == ["e1"]


def test_ws_between_reals_merges():
    chunks = _chunks([
        _el("e0", "paragraph", "aa"),
        _el("e1", "paragraph", "   "),
        _el("e2", "paragraph", "bb"),
    ])
    assert len(chunks) == 1
    assert chunks[0].text == "aa bb"
    assert chunks[0].source_element_ids \
        == ["e0", "e2"]


def test_resource_path_only_paragraph_skipped():
    chunks = _chunks([
        _el("e0", "paragraph", None,
            resource_path="x.txt"),
        _el("e1", "paragraph", "real"),
    ])
    assert len(chunks) == 1
    assert chunks[0].text == "real"
    assert chunks[0].source_element_ids \
        == ["e1"]


# ---------- 计数器跨策略连续 ----------

def test_counter_continuity_across_strategies():
    long_p = " ".join(
        f"word{i:02d}" for i in range(20))
    assert len(long_p) > 100
    chunks = _chunks([
        _el("e0", "table", "| t |"),
        _el("e1", "paragraph", long_p),
        _el("e2", "paragraph", "tail"),
    ])
    assert [c.chunk_id
            for c in chunks] == [
        "d::c0000", "d::c0001",
        "d::c0002", "d::c0003",
    ]
    assert [c.metadata["strategy"]
            for c in chunks] == [
        "isolated_table",
        "long_paragraph_sentence_split",
        "long_paragraph_sentence_split",
        "sequential",
    ]
    assert chunks[3].text == "tail"


# ---------- header 超长 ----------

def test_header_overlong_splits():
    long_p = " ".join(
        f"word{i:02d}" for i in range(20))
    chunks = _chunks([
        _el("e0", "header", long_p)])
    assert len(chunks) == 2
    assert all(
        c.metadata["strategy"] ==
        "long_paragraph_sentence_split"
        for c in chunks)
    assert chunks[0].metadata[
        "split_boundary_after"] == \
        "whitespace"
    assert "split_boundary_after" not in \
        chunks[1].metadata
    assert chunks[1].source_element_ids \
        == ["e0"]
