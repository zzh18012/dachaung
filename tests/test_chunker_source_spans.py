"""Chunk.source_spans 填充契约测试（Stage 6 批次 2）。

契约：docs/chunker-source-spans-contract.md（9e1b4d4）。
逐条映射 §1 九规则 + §2 防御路径 + §3 三指标 + §4 端到端。

覆盖无丢失指标沿用 v1.1 已裁决的非空白有序字符口径
（7e1246d，同 tests/test_pipeline.py::assert_text_preserved）：
超长 element 切分时 chunk 侧 joiner 空白在 element 侧无对应物，
非空白口径是仓库既有"不丢不重"严格形态。
"""

from __future__ import annotations

import re

import pytest

from app.chunkers.structural import StructuralChunker
from app.models import Document, Element
from app.schema import validate as validate_udm

_WS = re.compile(r"\s+")


def _non_ws(s: str) -> str:
    return _WS.sub("", s)


_LOCATOR_FAMILY = {
    "markdown": "line_address",
    "html": "line_address",
    "text": "line_address",
    "docx": "structural_index",
    "pdf": "page_geometry",
    "ipynb": "container_line",
}


def _make_doc(
    elements_data: list[dict],
    doc_id: str = "d-spn0000000001",
    source_type: str = "markdown",
) -> Document:
    els = []
    for i, ed in enumerate(elements_data):
        els.append(
            Element(
                element_id=ed.get("element_id", f"{doc_id}::e{i:04d}"),
                type=ed["type"],
                content=ed["content"],
                resource_path=ed.get("resource_path"),
                source_locator=ed.get(
                    "source_locator",
                    {"family": _LOCATOR_FAMILY[source_type], "line": i + 1},
                ),
            )
        )
    return Document(
        document_id=doc_id,
        source_path=f"samples/x-{source_type}",
        source_type=source_type,
        source_hash="a" * 64,
        parser_name="stdlib",
        parser_version="1",
        elements=els,
    )


def _span_dicts(chunk) -> list[dict]:
    return [
        {"element_id": s["element_id"], "start": s["start"], "end": s["end"]}
        for s in chunk.source_spans
    ]


# ---------- §1 规则 1/2：定义与切片恒等 ----------

def test_rule2_single_span_slice_identity_sentence_split():
    """单 span chunk：chunk.text == el.content[start:end] 逐字节（句切路径）。"""
    text = " ".join(f"S{i:03d}." for i in range(25))  # 149 chars
    doc = _make_doc([{"type": "paragraph", "content": text}])
    chunks = StructuralChunker(max_chars=100).chunk(doc)
    assert len(chunks) == 2
    for c in chunks:
        assert len(c.source_spans) == 1
        (s,) = c.source_spans
        assert c.text == text[s["start"]:s["end"]]
    assert chunks[0].source_spans[0]["start"] == 0
    assert chunks[0].source_spans[0]["end"] == 95
    assert chunks[1].source_spans[0]["start"] == 96
    assert chunks[1].source_spans[0]["end"] == 149


def test_rule2_single_span_slice_identity_hard_split():
    """无句读文本硬切（whitespace 回退）路径的切片恒等与缝隙。"""
    text = " ".join(f"w{i:04d}" for i in range(40))  # 239 chars
    doc = _make_doc([{"type": "paragraph", "content": text}])
    chunks = StructuralChunker(max_chars=100).chunk(doc)
    assert len(chunks) == 3
    spans = [(s["start"], s["end"]) for c in chunks for s in c.source_spans]
    assert spans == [(0, 95), (96, 191), (192, 239)]
    for (s, e), c in zip(spans, chunks):
        assert c.text == text[s:e]
    # 缝隙语义：相邻 span 缝隙只含空白（契约规则 5）
    assert text[95] == " "
    assert text[191] == " "
    # whitespace 回退边界进入 metadata
    assert chunks[0].metadata["split_boundary_after"] == "whitespace"
    assert chunks[1].metadata["split_boundary_after"] == "whitespace"
    assert "split_boundary_after" not in chunks[2].metadata


# ---------- §1 规则 3：坐标基准（el_start 推算） ----------

def test_rule3_padded_content_offset():
    """content 首尾空白被 strip 吃掉，span 用 lstrip 长度推算起点。"""
    raw = "  前后空白文本  "
    doc = _make_doc([{"type": "paragraph", "content": raw}])
    chunks = StructuralChunker(max_chars=100).chunk(doc)
    (c,) = chunks
    (s,) = c.source_spans
    assert (s["start"], s["end"]) == (2, 8)
    assert c.text == raw[2:8] == "前后空白文本"


def test_rule3_padded_long_text_offset_mapping():
    """超长 element 的 piece 坐标 + el_start 映射（stripped→content 坐标）。"""
    core = " ".join(f"S{i:03d}." for i in range(25))  # 149
    raw = "\t" + core + "\n"  # 151，stripped 起点=1
    doc = _make_doc([{"type": "paragraph", "content": raw}])
    chunks = StructuralChunker(max_chars=100).chunk(doc)
    assert len(chunks) == 2
    (s0,) = chunks[0].source_spans
    (s1,) = chunks[1].source_spans
    assert (s0["start"], s0["end"]) == (1, 96)
    assert (s1["start"], s1["end"]) == (97, 150)
    assert chunks[0].text == raw[1:96]
    assert chunks[1].text == raw[97:150]


# ---------- §1 规则 4：累积路径整元素区间 ----------

def test_rule4_accumulation_whole_element_spans():
    doc = _make_doc(
        [
            {"type": "heading", "content": "甲标题"},
            {"type": "paragraph", "content": "第一段落文字。"},
            {"type": "paragraph", "content": "第二段落文字。"},
        ]
    )
    chunks = StructuralChunker(max_chars=100).chunk(doc)
    (c,) = chunks
    assert _span_dicts(c) == [
        {"element_id": "d-spn0000000001::e0000", "start": 0, "end": 3},
        {"element_id": "d-spn0000000001::e0001", "start": 0, "end": 7},
        {"element_id": "d-spn0000000001::e0002", "start": 0, "end": 7},
    ]
    # 多 span chunk：chunk.text == 各 span 切片按 part 顺序单空格 join
    assert c.text == "甲标题 第一段落文字。 第二段落文字。"


def test_rule4_isolated_table_and_caption_spans():
    doc = _make_doc(
        [
            {"type": "paragraph", "content": "前文。"},
            {"type": "table", "content": "| a | b |"},
            {"type": "caption", "content": "表注"},
        ]
    )
    chunks = StructuralChunker(max_chars=100).chunk(doc)
    assert [c.metadata["strategy"] for c in chunks] == [
        "sequential",
        "isolated_table",
        "isolated_caption",
    ]
    assert _span_dicts(chunks[1]) == [
        {"element_id": "d-spn0000000001::e0001", "start": 0, "end": 9}
    ]
    assert chunks[1].text == "| a | b |"


def test_rule4_heading_flush_then_accumulate():
    doc = _make_doc(
        [
            {"type": "paragraph", "content": "导语段落。"},
            {"type": "heading", "content": "乙级标题"},
            {"type": "paragraph", "content": "标题后段落。"},
        ]
    )
    chunks = StructuralChunker(max_chars=100).chunk(doc)
    assert [c.text for c in chunks] == ["导语段落。", "乙级标题 标题后段落。"]
    assert _span_dicts(chunks[0]) == [
        {"element_id": "d-spn0000000001::e0000", "start": 0, "end": 5}
    ]
    assert _span_dicts(chunks[1]) == [
        {"element_id": "d-spn0000000001::e0001", "start": 0, "end": 4},
        {"element_id": "d-spn0000000001::e0002", "start": 0, "end": 6},
    ]


# ---------- §1 规则 5：超长路径合并覆盖句间空白 ----------

def test_rule5_merge_covers_inter_sentence_whitespace():
    text = "A001. A002. A003. A004. A005. A006."  # 6 句各 5 字符
    doc = _make_doc([{"type": "paragraph", "content": text}])
    chunks = StructuralChunker(max_chars=32).chunk(doc)
    assert [c.text for c in chunks] == [
        "A001. A002. A003. A004. A005.",
        "A006.",
    ]
    (s0,) = chunks[0].source_spans
    (s1,) = chunks[1].source_spans
    # 合并 piece 的 span 覆盖句间空白（end 扩到后句结尾）
    assert (s0["start"], s0["end"]) == (0, 29)
    assert (s1["start"], s1["end"]) == (30, 35)
    assert chunks[0].text == text[0:29]
    assert text[29] == " "


# ---------- §1 规则 6：逐 part 一项、顺序保持 ----------

def test_rule6_spans_follow_part_order_ids_deduped():
    doc = _make_doc(
        [
            {"type": "heading", "content": "题"},
            {"type": "paragraph", "content": "段一"},
            {"type": "paragraph", "content": "段二"},
        ]
    )
    (c,) = StructuralChunker(max_chars=100).chunk(doc)
    # spans 逐 part 一项（3 项），ids 首现去重（也是 3 个）
    assert len(c.source_spans) == 3
    assert c.source_element_ids == [
        "d-spn0000000001::e0000",
        "d-spn0000000001::e0001",
        "d-spn0000000001::e0002",
    ]
    assert [s["start"] for s in c.source_spans] == [0, 0, 0]
    assert [s["end"] for s in c.source_spans] == [1, 2, 2]


# ---------- §1 规则 7：无文本元素无 span ----------

def test_rule7_no_text_elements_produce_no_span():
    doc = _make_doc(
        [
            {"type": "paragraph", "content": "   "},  # 纯空白跳过
            {
                "type": "image",
                "content": "",
                "resource_path": "img/a.png",
                "source_locator": {"page": 1},
            },
            {"type": "paragraph", "content": "正文段落。"},
        ]
    )
    chunks = StructuralChunker(max_chars=100).chunk(doc)
    (c,) = chunks
    assert c.source_element_ids == ["d-spn0000000001::e0002"]
    assert _span_dicts(c) == [
        {"element_id": "d-spn0000000001::e0002", "start": 0, "end": 5}
    ]


def test_rule7_empty_document_no_chunks():
    assert StructuralChunker(max_chars=100).chunk(_make_doc([])) == []


# ---------- §1 规则 8：既有输出不变（span 纯增量） ----------

def test_rule8_existing_output_shape_unchanged():
    """text/metadata/ids/chunk_id 与无 span 基线逐字节一致（手钉值）。"""
    doc = _make_doc(
        [
            {"type": "heading", "content": "甲标题"},
            {"type": "paragraph", "content": "第一段落文字。"},
            {"type": "paragraph", "content": "第二段落文字。"},
        ]
    )
    (c,) = StructuralChunker(max_chars=100).chunk(doc)
    d = c.to_dict()
    spans = d.pop("source_spans")
    assert d == {
        "chunk_id": "d-spn0000000001::c0000",
        "text": "甲标题 第一段落文字。 第二段落文字。",
        "source_element_ids": [
            "d-spn0000000001::e0000",
            "d-spn0000000001::e0001",
            "d-spn0000000001::e0002",
        ],
        "metadata": {"strategy": "sequential", "max_chars": 100, "char_count": 19},
    }
    assert len(spans) == 3


def test_rule8_long_split_metadata_unchanged():
    text = " ".join(f"w{i:04d}" for i in range(40))
    doc = _make_doc([{"type": "paragraph", "content": text}])
    chunks = StructuralChunker(max_chars=100).chunk(doc)
    assert [c.metadata["char_count"] for c in chunks] == [95, 95, 47]
    assert all(
        c.metadata["strategy"] == "long_paragraph_sentence_split" for c in chunks
    )


# ---------- §1 规则 9：版本契约 ----------

def test_rule9_spans_emit_030_docx():
    doc = _make_doc(
        [{"type": "paragraph", "content": "docx 段落"}],
        source_type="docx",
    )
    doc.chunks = StructuralChunker(max_chars=100).chunk(doc)
    d = doc.to_dict()
    assert d["schema_version"] == "0.3.0"
    validate_udm(d)


def test_rule9_manual_empty_span_stays_010_shape():
    """手写无 span Chunk 的 to_dict 不带 source_spans 键（旧形状不变）。"""
    from app.models import Chunk

    c = Chunk(chunk_id="d::c0000", text="t", source_element_ids=["e"])
    assert "source_spans" not in c.to_dict()


# ---------- §2 防御路径：ipynb cell 边界与 span 正交 ----------

def _make_ipynb_doc(elements_data, doc_id="d-nb2000000001"):
    els = []
    for i, ed in enumerate(elements_data):
        els.append(
            Element(
                element_id=ed.get("element_id", f"{doc_id}::e{i:04d}"),
                type=ed["type"],
                content=ed["content"],
                source_locator={
                    "cell_index": ed["cell_index"],
                    "cell_type": ed.get("cell_type", "markdown"),
                    "line": ed.get("line", 1),
                },
            )
        )
    return Document(
        document_id=doc_id,
        source_path="samples/x.ipynb",
        source_type="ipynb",
        source_hash="a" * 64,
        parser_name="ipynb",
        parser_version="stdlib/0.1.0",
        elements=els,
    )


def test_defense_ipynb_cells_with_spans():
    cells = [
        {"type": "paragraph", "content": "甲细胞一段。", "cell_index": 0},
        {"type": "paragraph", "content": "乙细胞二段。", "cell_index": 1},
        {"type": "paragraph", "content": "丙细胞收尾。", "cell_index": 2},
    ]
    doc = _make_ipynb_doc(cells)
    chunks = StructuralChunker(max_chars=100).chunk(doc)
    assert len(chunks) == 3  # 批次 1：逐 cell 封口
    for c, ed in zip(chunks, cells):
        (s,) = c.source_spans
        assert c.text == ed["content"][s["start"]:s["end"]]


def test_defense_ipynb_missing_cell_index_self_grouped_with_spans():
    doc_id = "d-nb2000000002"
    doc = Document(
        document_id=doc_id,
        source_path="samples/x.ipynb",
        source_type="ipynb",
        source_hash="a" * 64,
        parser_name="ipynb",
        parser_version="stdlib/0.1.0",
        elements=[
            Element(
                element_id=f"{doc_id}::e0000", type="paragraph",
                content="无定位甲。", source_locator=None,
            ),
            Element(
                element_id=f"{doc_id}::e0001", type="paragraph",
                content="无定位乙。", source_locator={"cell_type": "markdown"},
            ),
        ],
    )
    chunks = StructuralChunker(max_chars=100).chunk(doc)
    assert [c.text for c in chunks] == ["无定位甲。", "无定位乙。"]
    contents = {e.element_id: e.content for e in doc.elements}
    for c in chunks:
        assert len(c.source_spans) == 1
        (s,) = c.source_spans
        assert c.text == contents[s["element_id"]][s["start"]:s["end"]]


# ---------- §3 三指标 ----------

def _mixed_doc() -> Document:
    long_text = " ".join(f"S{i:03d}." for i in range(25))  # 149
    return _make_doc(
        [
            {"type": "heading", "content": "  混合文档标题  "},
            {"type": "paragraph", "content": "短段落一。"},
            {"type": "paragraph", "content": long_text},
            {"type": "table", "content": "| k | v |"},
            {"type": "caption", "content": " 表注文本 "},
        ]
    )


def test_metric1_slice_identity_every_span():
    doc = _mixed_doc()
    chunks = StructuralChunker(max_chars=100).chunk(doc)
    assert len(chunks) >= 4
    by_id = {e.element_id: e for e in doc.elements}
    for c in chunks:
        for s in c.source_spans:
            piece = by_id[s["element_id"]].content[s["start"]:s["end"]]
            # 该 span 切片必须逐字节出现在 chunk 文本中（单 span chunk严格恒等）
            if len(c.source_spans) == 1:
                assert c.text == piece
            else:
                assert piece in c.text


def test_metric2_coverage_non_whitespace():
    doc = _mixed_doc()
    chunks = StructuralChunker(max_chars=100).chunk(doc)
    by_id = {e.element_id: e for e in doc.elements}
    covered: dict[str, list[tuple[int, int]]] = {}
    for c in chunks:
        for s in c.source_spans:
            covered.setdefault(s["element_id"], []).append((s["start"], s["end"]))
    for eid, spans in covered.items():
        content = by_id[eid].content
        marked = [False] * len(content)
        for s, e in spans:
            for k in range(s, e):
                marked[k] = True
        for k, ch in enumerate(content):
            if not ch.isspace():
                assert marked[k], f"{eid} 非空白字符 @{k} 未被 span 覆盖"


def test_metric3_determinism_two_runs():
    doc = _mixed_doc()
    r1 = StructuralChunker(max_chars=100).chunk(doc)
    r2 = StructuralChunker(max_chars=100).chunk(doc)
    assert [c.to_dict() for c in r1] == [c.to_dict() for c in r2]


# ---------- §4 端到端 ----------

def test_e2e_markdown_pipeline_030_and_span_identity(tmp_path):
    from app.pipeline import process_single

    p = tmp_path / "doc.md"
    p.write_text(
        "# 端到端标题\n\n端到端第一段。\n\n端到端第二段。\n", encoding="utf-8"
    )
    document, errors = process_single(
        p, tmp_path / "out.json", parser_name="markdown",
        max_chars=100, write_json=False,
    )
    assert errors == [] and document is not None
    d = document.to_dict()
    assert d["schema_version"] == "0.3.0"
    validate_udm(d)
    by_id = {e.element_id: e for e in document.elements}
    assert d["chunks"]
    for chunk in d["chunks"]:
        assert chunk["source_spans"]
        for s in chunk["source_spans"]:
            piece = by_id[s["element_id"]].content[s["start"]:s["end"]]
            if len(chunk["source_spans"]) == 1:
                assert chunk["text"] == piece
            else:
                assert piece in chunk["text"]


def test_e2e_ipynb_cells_and_spans_coexist(tmp_path):
    import json as _json

    from app.pipeline import process_single

    long_cell = " ".join(f"S{i:03d}." for i in range(25))
    nb = {
        "cells": [
            {"cell_type": "markdown", "metadata": {},
             "source": ["甲细胞一段。"]},
            {"cell_type": "markdown", "metadata": {},
             "source": [long_cell]},
            {"cell_type": "markdown", "metadata": {},
             "source": ["丙细胞收尾。"]},
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p = tmp_path / "doc.ipynb"
    p.write_text(_json.dumps(nb, ensure_ascii=False), encoding="utf-8")
    document, errors = process_single(
        p, tmp_path / "out.json", parser_name="ipynb",
        max_chars=100, write_json=False,
    )
    assert errors == [] and document is not None
    d = document.to_dict()
    validate_udm(d)
    assert len(d["chunks"]) == 4  # 批次 1 期望：c0/c1/c2/c3
    cellsets = []
    for chunk in d["chunks"]:
        assert chunk["source_spans"]
        cells = {
            next(
                e["source_locator"]["cell_index"]
                for e in d["elements"] if e["element_id"] == s["element_id"]
            )
            for s in chunk["source_spans"]
        }
        cellsets.append(cells)
    assert cellsets == [{0}, {1}, {1}, {2}]


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
