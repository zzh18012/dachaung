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


# ---------- chunk_boundary: 重复 marker（bug 回归） ----------


def test_chunk_boundary_repeated_marker_finds_distinct_positions():
    """两个 anchor 用相同 marker 文本，应分别定位到 stream 中第 1 个和第 2 个出现位置。

    构造：c0 = "the cat"，c1 = "the dog" → stream = "the cat the dog"
    - "the" 第 1 次出现 at pos 0
    - "the" 第 2 次出现 at pos 8（"the cat " 长度 8）

    两个 anchor 都用 marker="the" position="before"，期望分别命中 pos 0 与 pos 8。
    预测边界：c0 末尾 = 7（"the cat" 长度 7）。

    tolerance=2 时：
    - anchor@0 与 pred@7 距离 7 → 不命中
    - anchor@8 与 pred@7 距离 1 → 命中

    precision = 1/1 = 1.0
    recall = 1/2 = 0.5（一个 anchor 命中，一个不命中）

    若 bug 未修：两个 anchor 都定位到 pos 0，距离都是 7，都不命中，
    recall 会变成 0.0。
    """
    chunks = [
        _chunk("c0", "the cat", ["e0"]),
        _chunk("c1", "the dog", ["e1"]),
    ]
    doc = _doc_with_chunks(chunks)
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [
            {"marker": "the", "position": "before", "reason": "first"},
            {"marker": "the", "position": "before", "reason": "second"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=2)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_repeated_marker_after_position():
    """position="after" 的两个相同 marker 也应分别定位到不同 stream 位置。

    构造：c0 = "X end"，c1 = "Y end"，c2 = "Z end"
    stream = "X end Y end Z end"（19 字符）
    预测边界（c0 末尾、c1 末尾）：5、11
    anchors（两个 "end" after）：第 1 个 end 在 pos 2，after → 5；第 2 个 end 在 pos 8，after → 11
    → 完美一对一匹配，precision = recall = 1.0

    若 bug 未修：两个 anchor 都定位到 pos 2 → gt_positions = [5, 5]，
    一对一约束只能命中 1 个，recall = 0.5。
    """
    chunks = [
        _chunk("c0", "X end", ["e0"]),
        _chunk("c1", "Y end", ["e1"]),
        _chunk("c2", "Z end", ["e2"]),
    ]
    doc = _doc_with_chunks(chunks)
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [
            {"marker": "end", "position": "after", "reason": "1st"},
            {"marker": "end", "position": "after", "reason": "2nd"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_repeated_marker_not_found_after_exhausted():
    """若相同 marker 出现次数 < anchor 数，多余的 anchor 应进 missing_markers。"""
    chunks = [
        _chunk("c0", "once", ["e0"]),
        _chunk("c1", "twice", ["e1"]),
    ]
    # stream = "once twice"，"once" 只出现 1 次
    doc = _doc_with_chunks(chunks)
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [
            {"marker": "once", "position": "after", "reason": "1st"},
            {"marker": "once", "position": "after", "reason": "2nd-or-missing"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=100)
    # 第 2 个 "once" 找不到 → 进 missing_markers
    assert out["_missing_markers"]["value"] == ["once"]
