"""ipynb cell 硬边界分块契约测试（adoption 原创，Stage 6 第一批）。

契约：docs/chunker-ipynb-cell-contract.md（f8c2949 定稿）。
每个测试标注对应条款：
- §1 规则 1-9（九条核心规则）
- §2 边界定义细则（locator 缺失 cell_index 的防御路径）
- §3 三核心指标（覆盖无丢失 / 跨 cell chunk 数=0 / 非 ipynb 基线不变）
  + 端到端（.ipynb → pipeline --parser ipynb → UDM → chunker → schema）
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.chunkers import StructuralChunker, normalize_text
from app.models import Document, Element


def _make_ipynb_doc(
    elements_data,
    doc_id="d-nb0000000001",
    source_type="ipynb",
) -> Document:
    """elements_data: list of (type, content, locator)。

    ipynb 契约保证 ipynb element 的 locator 都带 cell_index；
    缺失场景（§2 防御路径）由测试显式构造。
    """
    elements = [
        Element(
            element_id=f"{doc_id}::e{i:04d}",
            type=item[0],
            content=item[1],
            source_locator=item[2],
        )
        for i, item in enumerate(elements_data)
    ]
    return Document(
        document_id=doc_id,
        source_path="/tmp/x.ipynb",
        source_type=source_type,
        source_hash="a" * 64,
        parser_name="test",
        parser_version="0",
        elements=elements,
    )


def _cell_set(doc: Document, chunk) -> set:
    """chunk → 经 source_element_ids 解析出的 cell_index 集合（§1 规则 7 链路）。"""
    by_id = {e.element_id: e for e in doc.elements}
    cells = set()
    for eid in chunk.source_element_ids:
        cells.add(by_id[eid].source_locator["cell_index"])
    return cells


def _non_ws(s: str) -> str:
    """删除全部 isspace() 字符；v1.1 已裁决的"非空白保持"口径（7e1246d）。

    超长 element 切分成多 chunk 时，chunk 间 joiner 空白在 element 侧无
    对应物——normalize_text 口径对此天然不等，非空白有序字符口径才是
    既有"不丢不重"的严格形态（test_chunker.py::assert_text_preserved）。
    """
    return "".join(ch for ch in s if not ch.isspace())


# ---------------------------------------------------------------- §1 规则 1
def test_rule1_chunk_never_spans_two_cells():
    doc = _make_ipynb_doc([
        ("paragraph", "cell zero text", {"cell_index": 0, "cell_type": "markdown", "line": 1}),
        ("paragraph", "cell one text", {"cell_index": 1, "cell_type": "markdown", "line": 1}),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert len(chunks) == 2
    assert _cell_set(doc, chunks[0]) == {0}
    assert _cell_set(doc, chunks[1]) == {1}
    assert chunks[0].text == "cell zero text"
    assert chunks[1].text == "cell one text"


# ---------------------------------------------------------------- §1 规则 3
def test_rule3_adjacent_short_cells_not_merged():
    """六个短 cell 总长远小于 max_chars，仍不得合并（H-CHK-001 单元镜像）。"""
    texts = [f"第{i}格短文本" for i in range(6)]
    doc = _make_ipynb_doc([
        ("paragraph", t, {"cell_index": i, "cell_type": "markdown", "line": 1})
        for i, t in enumerate(texts)
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert [c.text for c in chunks] == texts
    assert all(_cell_set(doc, c) == {i} for i, c in enumerate(chunks))


# ---------------------------------------------------------------- §1 规则 2
def test_rule2_long_cell_splits_within_cell():
    """超长 cell 沿用既有长文规则切分；切分产物仍只引用该 cell 的元素。"""
    long_text = "这是一个相当长的句子，用于撑爆上限。"
    while len(long_text) <= 200:
        long_text += "这是一个相当长的句子，用于撑爆上限。"
    doc = _make_ipynb_doc([
        ("paragraph", "短导语", {"cell_index": 0, "cell_type": "markdown", "line": 1}),
        ("paragraph", long_text, {"cell_index": 1, "cell_type": "code", "line": 1}),
        ("paragraph", "短结尾", {"cell_index": 2, "cell_type": "markdown", "line": 1}),
    ])
    chunks = StructuralChunker(max_chars=200).chunk(doc)
    assert len(chunks) >= 4  # 1 + >=ceil(len/200) + 1 的下界
    assert chunks[0].text == "短导语"
    assert chunks[-1].text == "短结尾"
    for c in chunks[1:-1]:
        assert len(c.text) <= 200
        assert _cell_set(doc, c) == {1}
        assert c.source_element_ids == [doc.elements[1].element_id]
        assert c.metadata["strategy"] == "long_paragraph_sentence_split"


def test_rule2_long_cell_hard_split_stays_in_cell():
    """无句子边界无空白的超长 cell：定长兜底切分，piece 仍不跨 cell。"""
    long_text = "字" * 450
    doc = _make_ipynb_doc([
        ("paragraph", "head", {"cell_index": 0, "cell_type": "code", "line": 1}),
        ("paragraph", long_text, {"cell_index": 1, "cell_type": "code", "line": 1}),
        ("paragraph", "tail", {"cell_index": 2, "cell_type": "code", "line": 1}),
    ])
    chunks = StructuralChunker(max_chars=200).chunk(doc)
    assert len(chunks) == 2 + 3  # 450/200 → 3 个 piece
    for c in chunks[1:4]:
        assert _cell_set(doc, c) == {1}
    assert normalize_text("".join(c.text for c in chunks)) == normalize_text(
        "head" + long_text + "tail"
    )


# ---------------------------------------------------------------- §1 规则 9
def test_rule9_heading_hard_boundary_within_same_cell():
    """同一 cell 内 heading 仍是硬边界；相邻 list cell 不合并（H-CHK-003 镜像）。

    基线语义（tests/test_chunker.py::test_heading_is_hard_boundary 钉死）：
    heading 封口之前的 buf、开启新 chunk，后续段落并入该 chunk。
    """
    doc = _make_ipynb_doc([
        ("paragraph", "前导段落", {"cell_index": 0, "cell_type": "markdown", "line": 1}),
        ("heading", "标题甲", {"cell_index": 0, "cell_type": "markdown", "line": 3}),
        ("paragraph", "段落一文字", {"cell_index": 0, "cell_type": "markdown", "line": 5}),
        ("paragraph", "段落二文字", {"cell_index": 0, "cell_type": "markdown", "line": 7}),
        ("list_item", "项目一", {"cell_index": 1, "cell_type": "markdown", "line": 1}),
        ("list_item", "项目二", {"cell_index": 1, "cell_type": "markdown", "line": 2}),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert len(chunks) == 3
    assert chunks[0].text == "前导段落"
    assert chunks[1].text == "标题甲 段落一文字 段落二文字"
    assert chunks[2].text == "项目一 项目二"
    assert _cell_set(doc, chunks[0]) == {0}
    assert _cell_set(doc, chunks[1]) == {0}
    assert _cell_set(doc, chunks[2]) == {1}


def test_rule9_table_isolated_within_cell():
    """table/image/caption 仍单独成 chunk（本身就不跨 cell）。"""
    doc = _make_ipynb_doc([
        ("paragraph", "before table", {"cell_index": 0, "cell_type": "markdown", "line": 1}),
        ("table", "a | b\n1 | 2", {"cell_index": 0, "cell_type": "markdown", "line": 3}),
        ("paragraph", "after table", {"cell_index": 0, "cell_type": "markdown", "line": 5}),
        ("paragraph", "next cell", {"cell_index": 1, "cell_type": "markdown", "line": 1}),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert len(chunks) == 4
    assert chunks[1].metadata["strategy"] == "isolated_table"
    assert chunks[1].source_element_ids == [doc.elements[1].element_id]
    assert all(_cell_set(doc, c) == {0} for c in chunks[:3])
    assert _cell_set(doc, chunks[3]) == {1}


def test_rule9_cell_boundary_flush_strategy_sequential():
    """cell 变化触发 flush 的 strategy 记录保持 "sequential"。"""
    doc = _make_ipynb_doc([
        ("paragraph", "first cell", {"cell_index": 0, "cell_type": "markdown", "line": 1}),
        ("paragraph", "second cell", {"cell_index": 1, "cell_type": "markdown", "line": 1}),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert all(c.metadata["strategy"] == "sequential" for c in chunks)


# ---------------------------------------------------------------- §1 规则 5
def test_rule5_chunk_metadata_keys_unchanged():
    """metadata 契约无新键：strategy/max_chars/char_count[±split_boundary_after]。"""
    doc = _make_ipynb_doc([
        ("heading", "H", {"cell_index": 0, "cell_type": "markdown", "line": 1}),
        ("paragraph", "body", {"cell_index": 0, "cell_type": "markdown", "line": 3}),
        ("paragraph", "next", {"cell_index": 1, "cell_type": "markdown", "line": 1}),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    allowed = {"strategy", "max_chars", "char_count", "split_boundary_after"}
    for c in chunks:
        assert set(c.metadata) <= allowed
        assert "section_path" not in c.metadata  # 标题上下文不写入 chunk metadata


# ---------------------------------------------------------------- §1 规则 6
def test_rule6_no_fake_body_chunks():
    """空 cell / 无 element → 无 chunk（parser 层不产 element，chunker 不虚构）。

    Element 模型要求 content 或 resource_path 至少一个非空（空 cell 在
    parser 层就不产 element）；纯空白 content 会被 _element_text 清空跳过。
    """
    doc = _make_ipynb_doc([])
    assert StructuralChunker(max_chars=800).chunk(doc) == []

    doc2 = _make_ipynb_doc([
        ("paragraph", "   ", {"cell_index": 0, "cell_type": "raw", "line": 1}),
        ("paragraph", "\n\t", {"cell_index": 1, "cell_type": "raw", "line": 1}),
    ])
    assert StructuralChunker(max_chars=800).chunk(doc2) == []


# ---------------------------------------------------------------- §1 规则 7
def test_rule7_deterministic_ids_order_provenance():
    doc = _make_ipynb_doc([
        ("heading", "T", {"cell_index": 0, "cell_type": "markdown", "line": 1}),
        ("paragraph", "a", {"cell_index": 0, "cell_type": "markdown", "line": 3}),
        ("paragraph", "b", {"cell_index": 1, "cell_type": "markdown", "line": 1}),
        ("paragraph", "c", {"cell_index": 2, "cell_type": "markdown", "line": 1}),
    ])
    r1 = StructuralChunker(max_chars=800).chunk(doc)
    r2 = StructuralChunker(max_chars=800).chunk(doc)
    assert [c.chunk_id for c in r1] == [
        "d-nb0000000001::c0000", "d-nb0000000001::c0001", "d-nb0000000001::c0002",
    ]
    # 两次运行逐字段一致（确定性）
    assert [(c.chunk_id, c.text, c.source_element_ids, c.metadata) for c in r1] == [
        (c.chunk_id, c.text, c.source_element_ids, c.metadata) for c in r2
    ]
    # 顺序 = element 顺序；provenance 经 source_element_ids → locator 确定
    # heading T 与同 cell 段落 a 并入 c0000（基线 heading 语义）
    assert r1[0].text == "T a"
    assert r1[0].source_element_ids == [
        doc.elements[0].element_id, doc.elements[1].element_id,
    ]
    assert r1[1].source_element_ids == [doc.elements[2].element_id]
    assert r1[2].source_element_ids == [doc.elements[3].element_id]


# ---------------------------------------------------------------- §1 规则 4/8 + §2
def test_rule8_non_ipynb_ignores_cell_boundaries():
    """cell 判定仅在 source_type == "ipynb" 时激活（规则 4/8）。"""
    data = [
        ("paragraph", "first para.", {"cell_index": 0, "cell_type": "markdown", "line": 1}),
        ("paragraph", "second para.", {"cell_index": 1, "cell_type": "markdown", "line": 1}),
    ]
    chunks = StructuralChunker(max_chars=800).chunk(
        _make_ipynb_doc(data, source_type="docx")
    )
    # 非 ipynb：locator 里的 cell_index 不构成边界，两句合并进一个 chunk
    # （与 96b688b 基线逐字节一致的行为）
    assert len(chunks) == 1
    assert chunks[0].text == "first para. second para."
    assert chunks[0].source_element_ids == [
        "d-nb0000000001::e0000", "d-nb0000000001::e0001",
    ]


def test_rule8_non_ipynb_baseline_exact_fields():
    """非 ipynb 基线不变：docx 输入的 chunk 全字段与 96b688b 基线推导值一致。"""
    data = [
        ("paragraph", "intro paragraph.", {"paragraph_index": 0}),
        ("heading", "Chapter 2", {"paragraph_index": 1}),
        ("paragraph", "body of chapter 2.", {"paragraph_index": 2}),
    ]
    chunks = StructuralChunker(max_chars=800).chunk(
        _make_ipynb_doc(data, doc_id="d-hx0000000001", source_type="md")
    )
    expected = [
        ("d-hx0000000001::c0000", "intro paragraph.", ["d-hx0000000001::e0000"]),
        ("d-hx0000000001::c0001", "Chapter 2 body of chapter 2.",
         ["d-hx0000000001::e0001", "d-hx0000000001::e0002"]),
    ]
    assert [(c.chunk_id, c.text, c.source_element_ids) for c in chunks] == expected


def test_section2_missing_cell_index_self_group():
    """locator 异常缺失 cell_index：该元素自成一组，不崩溃不猜测（§2）。

    连续两个缺失元素也各自成组，不互相合并。
    """
    doc = _make_ipynb_doc([
        ("paragraph", "has cell", {"cell_index": 0, "cell_type": "markdown", "line": 1}),
        ("paragraph", "no cell a", {"line": 1}),
        ("paragraph", "no cell b", {"line": 1}),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert [c.text for c in chunks] == ["has cell", "no cell a", "no cell b"]


def test_section2_missing_cell_index_not_dict_locator():
    """locator 非 dict（异常输入）：防御路径同样自成一组，不崩溃。"""
    doc = _make_ipynb_doc([
        ("paragraph", "weird locator", None),
    ])
    chunks = StructuralChunker(max_chars=800).chunk(doc)
    assert [c.text for c in chunks] == ["weird locator"]


# ---------------------------------------------------------------- §3 三指标
def _rich_doc() -> Document:
    long_text = "长句子内容重复填充。" * 30  # 300 chars > 200
    return _make_ipynb_doc([
        ("heading", "NB 标题", {"cell_index": 0, "cell_type": "markdown", "line": 1}),
        ("paragraph", "导语段落。", {"cell_index": 0, "cell_type": "markdown", "line": 3}),
        ("code_block", long_text, {"cell_index": 1, "cell_type": "code", "line": 1}),
        ("paragraph", "结论一。", {"cell_index": 2, "cell_type": "markdown", "line": 1}),
        ("paragraph", "结论二。", {"cell_index": 3, "cell_type": "markdown", "line": 1}),
    ])


def test_metric1_coverage_no_loss():
    """指标 1：正文覆盖无丢失（既有"不丢不重"口径，v1.1 非空白保持）。"""
    doc = _rich_doc()
    chunks = StructuralChunker(max_chars=200).chunk(doc)
    expected = _non_ws("".join(e.content or "" for e in doc.elements if e.type != "image"))
    actual = _non_ws("".join(c.text for c in chunks))
    assert expected == actual


def test_metric2_cross_cell_chunk_count_zero():
    """指标 2：每个 chunk 的 cell_index 集合大小恒为 1。"""
    doc = _rich_doc()
    chunks = StructuralChunker(max_chars=200).chunk(doc)
    assert len(chunks) >= 4
    for c in chunks:
        assert len(_cell_set(doc, c)) == 1


def test_metric3_non_ipynb_baseline_unchanged():
    """指标 3：同构 UDM 换 source_type 后输出与基线行为一致（逐字段）。"""
    data = [
        ("paragraph", "p one", {"paragraph_index": 0}),
        ("paragraph", "p two", {"paragraph_index": 1}),
        ("paragraph", "p three", {"paragraph_index": 2}),
    ]
    for st in ("docx", "md", "html", "text", "pdf"):
        chunks = StructuralChunker(max_chars=800).chunk(
            _make_ipynb_doc(data, doc_id="d-mt0000000001", source_type=st)
        )
        assert [(c.chunk_id, c.text) for c in chunks] == [
            ("d-mt0000000001::c0000", "p one p two p three"),
        ]


# ---------------------------------------------------------------- §3 端到端
def test_e2e_ipynb_pipeline_to_chunker(tmp_path: Path):
    """.ipynb → pipeline(--parser ipynb) → UDM → chunker → schema 校验通过。

    evaluator 的 auto 映射（ipynb→ipynb parser）由 tests/test_parser_auto.py
    的 v1.7 用例覆盖；此处走 pipeline 公开路径。
    """
    from app.pipeline import process_single

    nb = {
        "cells": [
            {"cell_type": "markdown", "source": "# 端到端标题\n\n端到端导语。",
             "metadata": {}},
            {"cell_type": "code", "source": "x = 1\n" * 100, "outputs": [],
             "execution_count": None, "metadata": {}},
            {"cell_type": "markdown", "source": "收尾单元。", "metadata": {}},
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    src = tmp_path / "e2e.ipynb"
    src.write_text(json.dumps(nb, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "out.json"

    document, errors = process_single(src, out, parser_name="ipynb", max_chars=200,
                                      write_json=True)
    assert errors == []
    assert document is not None
    assert document.source_type == "ipynb"
    assert document.chunks, "应产出 chunk"

    # write_json=True 已在写盘前通过 schema 校验（pipeline 不变量）
    assert out.exists()

    # cell 不变量：每个 chunk 的 cell 集合大小 == 1（指标 2 端到端形态）
    by_id = {e.element_id: e for e in document.elements}
    for c in document.chunks:
        cells = {by_id[eid].source_locator["cell_index"]
                 for eid in c.source_element_ids}
        assert len(cells) == 1

    # 覆盖无丢失（指标 1 端到端形态，非空白有序口径同 test_chunker.py 基线）
    expected = _non_ws(
        "".join(e.content or "" for e in document.elements if e.type != "image")
    )
    actual = _non_ws("".join(c.text for c in document.chunks))
    assert expected == actual
