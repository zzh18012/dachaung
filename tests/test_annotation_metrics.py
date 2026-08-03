"""annotation_metrics.py 的测试：figure_caption（固定 null）+ chunk_boundary P/R/F1。"""

from __future__ import annotations

import pytest

from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


def _doc_with_chunks(chunks: list[dict]) -> dict:
    return {
        "schema_version": "0.1.0",
        "document_id": "doc-test",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "test=1.0",
        "elements": [],
        "chunks": chunks,
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def _chunk(cid: str, text: str, src_ids: list[str]) -> dict:
    return {
        "chunk_id": cid,
        "text": text,
        "source_element_ids": src_ids,
        "metadata": {"strategy": "sequential", "max_chars": 800, "char_count": len(text)},
    }


# ---------- figure_caption: 始终 null ----------


def test_figure_caption_always_null_with_annotation():
    out = figure_caption_prf(document={"chunks": []}, annotation={"doc_id": "x"})
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert out[k]["value"] is None
        assert out[k]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_always_null_without_annotation():
    out = figure_caption_prf(document={"chunks": []}, annotation=None)
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert out[k]["value"] is None
        assert out[k]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


# ---------- chunk_boundary: null 路径 ----------


def test_chunk_boundary_no_document():
    out = chunk_boundary_prf(document=None, annotation={"doc_id": "x"})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"


def test_chunk_boundary_no_annotation():
    doc = _doc_with_chunks([_chunk("c0", "hello", ["e0"])])
    out = chunk_boundary_prf(document=doc, annotation=None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_no_anchors():
    doc = _doc_with_chunks([_chunk("c0", "hello", ["e0"]), _chunk("c1", "world", ["e1"])])
    annotation = {"doc_id": "x", "chunk_boundary_anchors": []}
    out = chunk_boundary_prf(document=doc, annotation=annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_only_one_chunk():
    doc = _doc_with_chunks([_chunk("c0", "hello", ["e0"])])
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [{"marker": "hello", "position": "after"}],
    }
    out = chunk_boundary_prf(document=doc, annotation=annotation)
    # 少于 2 个 chunk → 没有内部边界
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


# ---------- chunk_boundary: 正常匹配 ----------


def test_chunk_boundary_perfect_match_before_anchors():
    """3 个 chunk：c0 ends → predicted boundary at end of c0 text.
    Anchor: marker="B" position="before" → 边界在 B 的开头位置。
    如果 c0 = "A B" c1 = "C"，stream = "A B C"，c0 末尾在 3（A=0,space=1,B=2,end=3），
    "B" 起始在 2。|3-2|=1 ≤ tolerance。
    """
    chunks = [
        _chunk("c0", "A B", ["e0"]),
        _chunk("c1", "C", ["e1"]),
    ]
    doc = _doc_with_chunks(chunks)
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [
            {"marker": "B", "position": "before", "reason": "test"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0
    assert out["_tolerance_chars"]["value"] == 5


def test_chunk_boundary_no_match_outside_tolerance():
    chunks = [
        _chunk("c0", "AAAAAAAAAA", ["e0"]),  # 10 个 A
        _chunk("c1", "B", ["e1"]),
    ]
    doc = _doc_with_chunks(chunks)
    # stream = "AAAAAAAAAA B"，c0 末尾在 10，"B" 在 11（before）→ 距离 1
    # 但如果 tolerance=0，距离 1 不算
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [
            {"marker": "B", "position": "before", "reason": "test"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_one_to_one_matching():
    """一对一约束：一个预测只能命中一个标注。

    构造：1 个预测边界 + 2 个距离都很近的 anchor → 只能命中 1 个。
    precision = 1/1 = 1.0
    recall = 1/2 = 0.5
    """
    chunks = [
        _chunk("c0", "MARKER1 MARKER2", ["e0"]),
        _chunk("c1", "X", ["e1"]),
    ]
    # stream = "MARKER1 MARKER2 X"（19 字符）
    # c0 末尾 = 16（MARKER1=8 + space=1 + MARKER2=8 = 17... 实际是 16 因为没有结尾空格）
    # 重新算：len("MARKER1 MARKER2") = 16，c0 end at 16
    # MARKER1 starts at 0, MARKER2 starts at 9 (after "MARKER1 ")
    doc = _doc_with_chunks(chunks)
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [
            {"marker": "MARKER1", "position": "after", "reason": "1"},  # end at 8
            {"marker": "MARKER2", "position": "after", "reason": "2"},  # end at 17
        ],
    }
    # 预测边界在 16；anchor 在 8 和 17；距离 8 和 1
    # tolerance=5：只有 anchor2 (距离1) 命中
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0  # 1 predicted, 1 matched
    assert out["chunk_boundary_recall"]["value"] == 0.5  # 2 anchors, 1 matched


def test_chunk_boundary_missing_marker_recorded():
    chunks = [
        _chunk("c0", "hello", ["e0"]),
        _chunk("c1", "world", ["e1"]),
    ]
    doc = _doc_with_chunks(chunks)
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [
            {"marker": "MISSING", "position": "after", "reason": "x"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation)
    assert out["_missing_markers"]["value"] == ["MISSING"]
    # 因为 anchor 找不到 → recall 的分母变 0
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_tolerance_recorded_in_output():
    chunks = [_chunk("c0", "a", ["e0"]), _chunk("c1", "b", ["e1"])]
    doc = _doc_with_chunks(chunks)
    out = chunk_boundary_prf(doc, None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42
