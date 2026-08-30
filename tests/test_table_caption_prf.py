"""table_caption_prf 契约测试（Stage 7 批次 12）。

契约沿用 docs/relation-consumption-contract.md（§2 参数化匹配器 /
§3 降级矩阵），annotation schema v1.1 新增 table_caption_pairs
（table_marker/caption_text）。PDF 口径 Option A（批次 12 裁决）：
题注被融合进前一段落 → 0 预测 relation，GT 照标，recall=0.0
诚实曝光。
"""

from __future__ import annotations

import math

import evaluation
from evaluation.annotation_metrics import table_caption_prf
from evaluation.report import _RATIO_METRICS

_TC_KEYS = ("table_caption_precision", "table_caption_recall",
            "table_caption_f1")

_TABLE_CONTENT = ("| Code | Element | Expected handling | Integrity marker |\n"
                  "| --- | --- | --- | --- |\n"
                  "| TXT | Text block | Preserve reading order | BOUNDARY_ALPHA |")
_CAPTION = "Table 1. Module status matrix"


def _el(eid: str, **kw) -> dict:
    base = {"element_id": eid, "type": "paragraph", "source_locator": {},
            "parent_id": None, "content": None, "resource_path": None,
            "confidence": 1.0, "metadata": {}}
    base.update(kw)
    return base


def _doc(elements: list[dict], relations: list[dict]) -> dict:
    return {
        "schema_version": "0.5.0", "document_id": "doc-test",
        "source_path": "x", "source_type": "docx", "source_hash": "a" * 64,
        "parser_name": "fallback", "parser_version": "test=1.0",
        "elements": elements, "chunks": [], "relations": relations,
        "warnings": [], "errors": [], "metadata": {},
    }


def _trel(fid: str, tid: str) -> dict:
    return {"type": "table_has_caption", "from_id": fid, "to_id": tid,
            "metadata": {"rule": "docx_adjacent_element_above"}}


def _gt(table_marker: str = "Code | Element | Expected handling",
        caption_text: str = _CAPTION) -> dict:
    return {"annotation_version": "1.1", "doc_id": "doc-test",
            "table_caption_pairs": [
                {"table_marker": table_marker, "caption_text": caption_text}
            ]}


def _perfect_doc() -> dict:
    return _doc(
        [_el("t1", type="table", content=_TABLE_CONTENT),
         _el("c1", type="caption", content=_CAPTION)],
        [_trel("t1", "c1")],
    )


# ---------- 正常路径 ----------

def test_perfect_match() -> None:
    out = table_caption_prf(_perfect_doc(), _gt())
    assert set(out) == set(_TC_KEYS)
    assert out["table_caption_precision"] == {"value": 1.0, "reason": None}
    assert out["table_caption_recall"] == {"value": 1.0, "reason": None}
    assert out["table_caption_f1"] == {"value": 1.0, "reason": None}


def test_table_content_whitespace_normalized() -> None:
    # GT marker 用单空格形态，匹配表格多行线性化文本（normalize 后命中）
    out = table_caption_prf(_perfect_doc(), _gt(
        table_marker="Code | Element | Expected handling | Integrity marker"))
    assert out["table_caption_precision"]["value"] == 1.0


def test_over_detection_two_pred_one_gt() -> None:
    doc = _doc(
        [_el("t1", type="table", content=_TABLE_CONTENT),
         _el("c1", type="caption", content=_CAPTION),
         _el("t2", type="table", content="| other | table |"),
         _el("c2", type="caption", content="Table 2. Another")],
        [_trel("t1", "c1"), _trel("t2", "c2")],
    )
    out = table_caption_prf(doc, _gt())
    assert out["table_caption_precision"]["value"] == 0.5
    assert out["table_caption_recall"]["value"] == 1.0
    assert math.isclose(out["table_caption_f1"]["value"], 2 * 0.5 / 1.5)


def test_caption_text_partial_miss_not_matched() -> None:
    doc = _doc(
        [_el("t1", type="table", content=_TABLE_CONTENT),
         _el("c1", type="caption", content="Table 1. Module status matrix")],
        [_trel("t1", "c1")],
    )
    out = table_caption_prf(doc, _gt(caption_text="Table 99. Nonexistent"))
    assert out["table_caption_precision"]["value"] == 0.0
    assert out["table_caption_recall"]["value"] == 0.0
    assert out["table_caption_f1"]["value"] == 0.0


# ---------- PDF Option A：漏检（0 预测 relation）诚实曝光 ----------

def test_pdf_option_a_zero_predicted_relations() -> None:
    # DC-MVP-001-PDF 实况：表元素存在但题注被融合进前一段落，
    # parser 不产出 table_has_caption relation。
    doc = _doc(
        [_el("e0004", type="paragraph",
             content="2. Structured elements Table 1. Module status matrix ..."),
         _el("e0006", type="table", content=_TABLE_CONTENT)],
        [],
    )
    out = table_caption_prf(doc, _gt())
    assert out["table_caption_precision"] == {
        "value": None, "reason": "no_predicted_relations"}
    assert out["table_caption_recall"] == {"value": 0.0, "reason": None}
    assert out["table_caption_f1"] == {
        "value": None, "reason": "precision_or_recall_not_evaluated"}


def test_other_relation_types_not_counted() -> None:
    # 仅有 has_caption（图）relation 时，表指标必须按 0 预测处理
    doc = _doc(
        [_el("t1", type="table", content=_TABLE_CONTENT),
         _el("c1", type="caption", content=_CAPTION)],
        [{"type": "has_caption", "from_id": "t1", "to_id": "c1",
          "metadata": {}}],
    )
    out = table_caption_prf(doc, _gt())
    assert out["table_caption_precision"]["reason"] == "no_predicted_relations"
    assert out["table_caption_recall"]["value"] == 0.0


# ---------- 降级矩阵 ----------

def test_degradation_pipeline_failed() -> None:
    out = table_caption_prf(None, _gt())
    for k in _TC_KEYS:
        assert out[k] == {"value": None, "reason": "pipeline_failed"}


def test_degradation_no_annotation() -> None:
    out = table_caption_prf(_doc([], []), None)
    for k in _TC_KEYS:
        assert out[k] == {"value": None, "reason": "no_annotation"}


def test_degradation_no_annotation_pairs() -> None:
    ann = {"annotation_version": "1.0", "doc_id": "doc-test"}
    out = table_caption_prf(_doc([], []), ann)
    for k in _TC_KEYS:
        assert out[k] == {"value": None, "reason": "no_annotation_pairs"}


def test_degradation_no_ground_truth_pairs_invalid_markers() -> None:
    # pairs 非空但 marker 非 str（schema 外输入）→ num_gt=0，有预测时
    # recall 走 no_ground_truth_pairs
    doc = _doc(
        [_el("t1", type="table", content=_TABLE_CONTENT),
         _el("c1", type="caption", content=_CAPTION)],
        [_trel("t1", "c1")],
    )
    ann = {"annotation_version": "1.1", "doc_id": "doc-test",
           "table_caption_pairs": [{"table_marker": 5,
                                    "caption_text": "x"}]}
    out = table_caption_prf(doc, ann)
    assert out["table_caption_precision"] == {"value": 0.0, "reason": None}
    assert out["table_caption_recall"] == {
        "value": None, "reason": "no_ground_truth_pairs"}
    assert out["table_caption_f1"] == {
        "value": None, "reason": "precision_or_recall_not_evaluated"}


def test_wrapper_emits_exactly_three_keys() -> None:
    out = table_caption_prf(document=_doc([], []), annotation=None)
    assert set(out) == set(_TC_KEYS)


# ---------- 版本与 macro 钉死 ----------

def test_evaluator_version_bumped_report_unchanged() -> None:
    assert evaluation.EVALUATOR_VERSION == "1.10"
    assert evaluation.REPORT_VERSION == "1.3"


def test_table_caption_not_in_macro_average() -> None:
    for k in _TC_KEYS:
        assert k not in _RATIO_METRICS
