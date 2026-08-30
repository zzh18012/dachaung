"""relation 消费契约测试（Stage 6 批次 6）。

契约：docs/relation-consumption-contract.md（2026-08-30 冻结）。逐条映射：
- §2 参数化匹配器：签名（relation_type/from_marker_key/to_marker_key）、
  from 侧识别文本（content+alt+resource basename）、to 侧 content、
  一对一贪心 (i,j) 序、端点缺失不计入预测
- §3 降级矩阵五路（pipeline_failed / no_annotation / no_annotation_pairs /
  no_predicted_relations / 正常）
- §5 EVALUATOR_VERSION=1.8、REPORT_VERSION=1.3
- §6 批次 7 桩测试：table_has_caption 传参演示（裁决要求③）
"""

from __future__ import annotations

import evaluation
from evaluation.annotation_metrics import (
    chunk_boundary_prf,
    figure_caption_prf,
    match_relation_pairs,
)
from evaluation.report import _RATIO_METRICS

_FC_KEYS = ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1")


def _el(eid: str, **kw) -> dict:
    base = {"element_id": eid, "type": "paragraph", "source_locator": {},
            "parent_id": None, "content": None, "resource_path": None,
            "confidence": 1.0, "metadata": {}}
    base.update(kw)
    return base


def _doc(elements: list[dict], relations: list[dict]) -> dict:
    return {
        "schema_version": "0.4.0", "document_id": "doc-test",
        "source_path": "x", "source_type": "docx", "source_hash": "a" * 64,
        "parser_name": "fallback", "parser_version": "test=1.0",
        "elements": elements, "chunks": [], "relations": relations,
        "warnings": [], "errors": [], "metadata": {},
    }


def _rel(rid: str, fid: str, tid: str, rtype: str = "has_caption") -> dict:
    return {"type": rtype, "from_id": fid, "to_id": tid, "metadata": {}}


# ---------- §2 匹配器语义 ----------


def test_match_perfect_pairs():
    doc = _doc(
        [
            _el("img1", type="image", resource_path="outputs/images-x/fig-a.png"),
            _el("cap1", type="caption", content="Figure 1. Flow"),
            _el("img2", type="image", resource_path="outputs/images-x/fig-b.png"),
            _el("cap2", type="caption", content="Figure 2. Chart"),
        ],
        [_rel("r1", "img1", "cap1"), _rel("r2", "img2", "cap2")],
    )
    pairs = [
        {"figure_marker": "fig-a.png", "caption_text": "Figure 1. Flow"},
        {"figure_marker": "fig-b.png", "caption_text": "Figure 2. Chart"},
    ]
    assert match_relation_pairs(
        doc, pairs, relation_type="has_caption",
        from_marker_key="figure_marker", to_marker_key="caption_text",
    ) == (2, 2, 2)


def test_match_from_side_alt_text():
    doc = _doc(
        [
            _el("img1", type="image", resource_path="x.png",
                metadata={"alt": "architecture diagram"}),
            _el("cap1", type="caption", content="Figure 1. X"),
        ],
        [_rel("r1", "img1", "cap1")],
    )
    pairs = [{"figure_marker": "architecture diagram", "caption_text": "Figure 1. X"}]
    assert match_relation_pairs(
        doc, pairs, relation_type="has_caption",
        from_marker_key="figure_marker", to_marker_key="caption_text",
    ) == (1, 1, 1)


def test_match_to_side_normalize_tolerates_whitespace():
    doc = _doc(
        [
            _el("img1", type="image", resource_path="a.png"),
            _el("cap1", type="caption", content="Figure  1.   Flow"),
        ],
        [_rel("r1", "img1", "cap1")],
    )
    pairs = [{"figure_marker": "a.png", "caption_text": "Figure 1. Flow"}]
    assert match_relation_pairs(
        doc, pairs, relation_type="has_caption",
        from_marker_key="figure_marker", to_marker_key="caption_text",
    ) == (1, 1, 1)


def test_match_partial_and_miss():
    doc = _doc(
        [
            _el("img1", type="image", resource_path="a.png"),
            _el("cap1", type="caption", content="Figure 1. X"),
            _el("img2", type="image", resource_path="b.png"),
            _el("cap2", type="caption", content="Figure 2. Y"),
        ],
        [_rel("r1", "img1", "cap1"), _rel("r2", "img2", "cap2")],
    )
    # GT 只有第二对（第一对漏标）→ matched=1, num_pred=2, num_gt=1
    pairs = [{"figure_marker": "b.png", "caption_text": "Figure 2. Y"}]
    assert match_relation_pairs(
        doc, pairs, relation_type="has_caption",
        from_marker_key="figure_marker", to_marker_key="caption_text",
    ) == (2, 1, 1)


def test_match_dedup_one_to_one_greedy_deterministic():
    """两个预测对都能匹配同一 GT 对 → 只有 (i,j) 序第一个命中。"""
    doc = _doc(
        [
            _el("img1", type="image", resource_path="a.png"),
            _el("img2", type="image", resource_path="a2.png"),
            _el("cap1", type="caption", content="shared"),
            _el("cap2", type="caption", content="shared"),
        ],
        [_rel("r1", "img1", "cap1"), _rel("r2", "img2", "cap2")],
    )
    pairs = [{"figure_marker": "a", "caption_text": "shared"},
             {"figure_marker": "a2", "caption_text": "shared"}]
    assert match_relation_pairs(
        doc, pairs, relation_type="has_caption",
        from_marker_key="figure_marker", to_marker_key="caption_text",
    ) == (2, 2, 2)
    # 去掉第二个 GT：两预测争一个 GT → matched=1（贪心取 (0,0)）
    pairs1 = [{"figure_marker": "a", "caption_text": "shared"}]
    assert match_relation_pairs(
        doc, pairs1, relation_type="has_caption",
        from_marker_key="figure_marker", to_marker_key="caption_text",
    ) == (2, 1, 1)


def test_match_endpoint_missing_relation_excluded():
    doc = _doc(
        [
            _el("img1", type="image", resource_path="a.png"),
            _el("cap1", type="caption", content="Figure 1. X"),
        ],
        [_rel("r1", "img1", "cap1"), _rel("ghost", "imgX", "capX")],
    )
    pairs = [{"figure_marker": "a.png", "caption_text": "Figure 1. X"}]
    assert match_relation_pairs(
        doc, pairs, relation_type="has_caption",
        from_marker_key="figure_marker", to_marker_key="caption_text",
    ) == (1, 1, 1)


def test_match_other_relation_types_ignored():
    doc = _doc(
        [
            _el("t1", type="table", content="| a |"),
            _el("cap1", type="caption", content="Table 1. X"),
        ],
        [_rel("r1", "t1", "cap1", rtype="table_has_caption")],
    )
    pairs = [{"figure_marker": "a", "caption_text": "Table 1. X"}]
    assert match_relation_pairs(
        doc, pairs, relation_type="has_caption",
        from_marker_key="figure_marker", to_marker_key="caption_text",
    ) == (0, 1, 0)


def test_match_returns_none_for_missing_inputs():
    assert match_relation_pairs(
        None, [{}], relation_type="has_caption",
        from_marker_key="f", to_marker_key="t",
    ) is None
    assert match_relation_pairs(
        _doc([], []), None, relation_type="has_caption",
        from_marker_key="f", to_marker_key="t",
    ) is None
    assert match_relation_pairs(
        _doc([], []), [], relation_type="has_caption",
        from_marker_key="f", to_marker_key="t",
    ) is None


# ---------- §6 批次 7 桩测试（裁决要求③：接口可扩展演示，无真实数据） ----------


def test_stub_table_has_caption_batch7_interface():
    """批次 7 预留：同一匹配器换参数即服务 table_has_caption。

    无需真实 table 题注关联实现——仅证明签名与语义可扩展。
    """
    doc = _doc(
        [
            _el("t1", type="table", content="| a | b |\n| --- | --- |\n| 1 | 2 |"),
            _el("tc1", type="caption", content="Table 1. Module status"),
            _el("t2", type="table", content="| c |\n| --- |\n| 3 |"),
            _el("tc2", type="caption", content="Table 2. Other"),
        ],
        [
            _rel("r1", "t1", "tc1", rtype="table_has_caption"),
            _rel("r2", "t2", "tc2", rtype="table_has_caption"),
        ],
    )
    pairs = [
        {"table_marker": "| a | b |", "table_caption_text": "Table 1. Module status"},
        {"table_marker": "| c |", "table_caption_text": "Table 2. Other"},
    ]
    assert match_relation_pairs(
        doc, pairs,
        relation_type="table_has_caption",
        from_marker_key="table_marker",
        to_marker_key="table_caption_text",
    ) == (2, 2, 2)


# ---------- §3 降级矩阵 ----------


def test_degradation_pipeline_failed():
    out = figure_caption_prf(document=None, annotation={"doc_id": "x"})
    for k in _FC_KEYS:
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_degradation_no_annotation():
    doc = _doc([_el("img1", type="image", resource_path="a.png")],
               [_rel("r1", "img1", "capX")])
    out = figure_caption_prf(document=doc, annotation=None)
    for k in _FC_KEYS:
        assert out[k]["reason"] == "no_annotation"


def test_degradation_no_annotation_pairs():
    doc = _doc([], [])
    out = figure_caption_prf(document=doc, annotation={"figure_caption_pairs": []})
    for k in _FC_KEYS:
        assert out[k]["reason"] == "no_annotation_pairs"


def test_degradation_no_predicted_relations_real_miss():
    """有 GT、零预测 → precision null / recall 0.0（真实漏检，非 skip）。"""
    doc = _doc([_el("img1", type="image", resource_path="a.png")], [])
    ann = {"figure_caption_pairs": [
        {"figure_marker": "a.png", "caption_text": "Figure 1. X"}]}
    out = figure_caption_prf(document=doc, annotation=ann)
    assert out["figure_caption_precision"]["reason"] == "no_predicted_relations"
    assert out["figure_caption_recall"]["value"] == 0.0
    assert out["figure_caption_f1"]["reason"] == "precision_or_recall_not_evaluated"


def test_normal_path_values():
    doc = _doc(
        [
            _el("img1", type="image", resource_path="a.png"),
            _el("cap1", type="caption", content="Figure 1. X"),
            _el("img2", type="image", resource_path="b.png"),
            _el("cap2", type="caption", content="Figure 2. Y"),
        ],
        [_rel("r1", "img1", "cap1"), _rel("r2", "img2", "cap2")],
    )
    ann = {"figure_caption_pairs": [
        {"figure_marker": "a.png", "caption_text": "Figure 1. X"},
        {"figure_marker": "b.png", "caption_text": "Figure 2. Y"},
    ]}
    out = figure_caption_prf(document=doc, annotation=ann)
    assert out["figure_caption_precision"]["value"] == 1.0
    assert out["figure_caption_recall"]["value"] == 1.0
    assert out["figure_caption_f1"]["value"] == 1.0


def test_wrapper_emits_exactly_three_keys():
    out = figure_caption_prf(document=_doc([], []), annotation=None)
    assert set(out) == set(_FC_KEYS)


# ---------- §5 版本 + 聚合不变 ----------


def test_evaluator_version_bumped_report_unchanged():
    assert evaluation.EVALUATOR_VERSION == "1.9"
    assert evaluation.REPORT_VERSION == "1.3"


def test_figure_caption_not_in_macro_average():
    for k in _FC_KEYS:
        assert k not in _RATIO_METRICS


def test_chunk_boundary_still_importable_and_untouched_semantics():
    out = chunk_boundary_prf(document=None, annotation={"doc_id": "x"})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"
