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


# ---------- 边角与缺漏补强（Round 21） ----------


def test_chunk_boundary_empty_marker_goes_to_missing_markers():
    """空字符串 marker 不参与匹配，直接进 missing_markers。"""
    chunks = [
        _chunk("c0", "hello", ["e0"]),
        _chunk("c1", "world", ["e1"]),
    ]
    doc = _doc_with_chunks(chunks)
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [
            {"marker": "", "position": "after", "reason": "empty"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation)
    assert out["_missing_markers"]["value"] == [""]
    # 空串 anchor 进了 missing → 没有可用 gt → recall 是 null
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_anchor_position_defaults_to_after():
    """position 字段缺失时默认 "after"。"""
    chunks = [
        # stream = "alpha beta"
        # "alpha" 末尾 at 5；c0 末尾也在 5 → 完美匹配
        _chunk("c0", "alpha", ["e0"]),
        _chunk("c1", "beta", ["e1"]),
    ]
    doc = _doc_with_chunks(chunks)
    annotation = {
        "doc_id": "x",
        # 没有 position 字段
        "chunk_boundary_anchors": [{"marker": "alpha"}],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_f1_zero_when_both_p_and_r_zero():
    """P=0、R=0 → denom=0 → f1 显式 = 0.0（不是 null）。"""
    chunks = [
        _chunk("c0", "AAAAAAAAAA", ["e0"]),  # 10 A
        _chunk("c1", "B", ["e1"]),
    ]
    doc = _doc_with_chunks(chunks)
    # stream = "AAAAAAAAAA B"，pred at 10，anchor "B" before at 11，距离 1
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [{"marker": "B", "position": "before"}],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["reason"] is None


def test_chunk_boundary_f1_null_when_recall_null():
    """recall 为 null 时 f1 应为 null（precision_or_recall_not_evaluated）。"""
    chunks = [
        _chunk("c0", "hello", ["e0"]),
        _chunk("c1", "world", ["e1"]),
    ]
    doc = _doc_with_chunks(chunks)
    # 一个不存在的 marker → 进 missing → gt_positions 空 → recall=null
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [{"marker": "DOES_NOT_EXIST", "position": "after"}],
    }
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    assert out["chunk_boundary_f1"]["reason"] == "precision_or_recall_not_evaluated"
    assert out["chunk_boundary_f1"]["value"] is None


def test_chunk_boundary_document_without_chunks_key():
    """document 缺少 "chunks" 字段 → 当成没有 chunks → no_predicted_boundaries。"""
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d-no-chunks",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "test=1.0",
        "elements": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [{"marker": "anything", "position": "after"}],
    }
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_default_tolerance_is_30():
    """tolerance_chars 默认值 = 30。"""
    chunks = [_chunk("c0", "a", ["e0"]), _chunk("c1", "b", ["e1"])]
    doc = _doc_with_chunks(chunks)
    # 不传 tolerance_chars → 用默认
    out = chunk_boundary_prf(doc, None)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_f1_value_with_p1_r_half():
    """P=1.0、R=0.5 → f1 = 2*1*0.5/(1+0.5) = 2/3 ≈ 0.667。"""
    chunks = [
        _chunk("c0", "MARKER1 MARKER2", ["e0"]),
        _chunk("c1", "X", ["e1"]),
    ]
    doc = _doc_with_chunks(chunks)
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [
            {"marker": "MARKER1", "position": "after"},
            {"marker": "MARKER2", "position": "after"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5
    f1 = out["chunk_boundary_f1"]["value"]
    assert f1 is not None
    assert abs(f1 - (2 / 3)) < 1e-9


def test_chunk_boundary_greedy_matching_by_distance():
    """贪心按距离排序：当一个 pred 离两个 gt 都近时，
    先用距离更近的 gt 占据，避免被远的 gt 浪费。"""
    # 构造：3 chunk，2 个 anchor
    # stream = "aaa bbb ccc"
    # c0 end at 3，c1 end at 7
    # anchor1 marker="bbb" before at 4，距离 pred@3 是 1，距离 pred@7 是 3
    # anchor2 marker="ccc" before at 8，距离 pred@7 是 1
    # 贪心：距离 1 的对先匹配（pred@3 ↔ gt@4，pred@7 ↔ gt@8）→ 全中
    chunks = [
        _chunk("c0", "aaa", ["e0"]),
        _chunk("c1", "bbb", ["e1"]),
        _chunk("c2", "ccc", ["e2"]),
    ]
    doc = _doc_with_chunks(chunks)
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [
            {"marker": "bbb", "position": "before"},
            {"marker": "ccc", "position": "before"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0  # 2 pred, 2 matched
    assert out["chunk_boundary_recall"]["value"] == 1.0  # 2 anchors, 2 matched


def test_chunk_boundary_multiple_preds_share_nearby_anchor_only_one_wins():
    """两个 pred 都靠近同一个 gt 时，一对一约束只让一个匹配。"""
    # stream = "X A Y B"
    # c0 end at 1，c1 end at 5
    # 只有 1 个 anchor: marker="A" before at 2 → 距离 pred@1 是 1，距离 pred@5 是 3
    # tolerance=2：pred@1 命中（距离 1），pred@5 不命中（距离 3）
    # precision = 1/2，recall = 1/1
    chunks = [
        _chunk("c0", "X", ["e0"]),
        _chunk("c1", "A Y", ["e1"]),
        _chunk("c2", "B", ["e2"]),
    ]
    doc = _doc_with_chunks(chunks)
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [{"marker": "A", "position": "before"}],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=2)
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_chunks_with_none_text_handled():
    """chunk.text = None 不应崩溃（normalize_text 接受 None）。"""
    chunks = [
        {"chunk_id": "c0", "text": None, "source_element_ids": ["e0"], "metadata": {}},
        _chunk("c1", "world", ["e1"]),
    ]
    doc = _doc_with_chunks(chunks)
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [{"marker": "world", "position": "before"}],
    }
    # stream = " world" 或 "world"（视 normalize 行为），不应抛异常
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # 不崩溃即通过；具体值取决于 None text 如何被处理
    assert "chunk_boundary_precision" in out
    assert "chunk_boundary_recall" in out


def test_chunk_boundary_annotation_empty_dict_treated_as_no_annotation():
    """空 dict annotation → not annotation → no_annotation 分支。"""
    chunks = [_chunk("c0", "a", ["e0"]), _chunk("c1", "b", ["e1"])]
    doc = _doc_with_chunks(chunks)
    out = chunk_boundary_prf(doc, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_all_anchors_missing_recall_null():
    """所有 anchor 都找不到 → recall=null（no_ground_truth_anchors_in_stream）。"""
    chunks = [
        _chunk("c0", "alpha", ["e0"]),
        _chunk("c1", "beta", ["e1"]),
    ]
    doc = _doc_with_chunks(chunks)
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [
            {"marker": "MISSING1", "position": "after"},
            {"marker": "MISSING2", "position": "before"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    assert set(out["_missing_markers"]["value"]) == {"MISSING1", "MISSING2"}
    # f1 因 recall 是 null → null
    assert out["chunk_boundary_f1"]["reason"] == "precision_or_recall_not_evaluated"


def test_figure_caption_return_shape_with_full_doc_and_annotation():
    """figure_caption_prf 在 doc + annotation 都齐时应返回 3 个键，值都是 null。"""
    doc = _doc_with_chunks([
        _chunk("c0", "text", ["e0"]),
    ])
    annotation = {
        "doc_id": "x",
        "figure_caption_pairs": [
            {"figure_id": "f1", "caption_id": "cap1"},
        ],
    }
    out = figure_caption_prf(doc, annotation)
    assert set(out.keys()) == {
        "figure_caption_precision", "figure_caption_recall", "figure_caption_f1"
    }
    for k, v in out.items():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_chunk_boundary_tolerance_and_missing_markers_coexist():
    """同时有 _tolerance_chars 和 _missing_markers 时，两个键都在输出里。"""
    chunks = [
        _chunk("c0", "alpha", ["e0"]),
        _chunk("c1", "beta", ["e1"]),
    ]
    doc = _doc_with_chunks(chunks)
    annotation = {
        "doc_id": "x",
        "chunk_boundary_anchors": [
            {"marker": "FOUND", "position": "after"},
            {"marker": "MISSING", "position": "before"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=15)
    assert "_tolerance_chars" in out
    assert out["_tolerance_chars"]["value"] == 15
    assert "_missing_markers" in out
    assert "MISSING" in out["_missing_markers"]["value"]
