"""heading_order_prf 契约测试（批次 11，Option 1 序列匹配）。

覆盖裁决指定五类场景：完美匹配 / 多检 / 漏检 / 乱序 / 降级路径，
另补 level 不匹配与规范化（空白折叠）语义。
"""

from __future__ import annotations

import math

from evaluation.annotation_metrics import heading_order_prf


def _heading(eid: str, level: int, text: str) -> dict:
    return {
        "element_id": f"doc-test::{eid}",
        "type": "heading",
        "content": text,
        "resource_path": None,
        "metadata": {"level": level},
        "source_locator": {"family": "docx_paragraph", "paragraph_index": 0},
    }


def _doc(headings: list[dict]) -> dict:
    return {
        "schema_version": "0.5.0",
        "document_id": "doc-test",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "test=1.0",
        "elements": headings,
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def _gt(*pairs: tuple[int, str]) -> dict:
    return {
        "doc_id": "doc-test",
        "heading_order": [{"level": lv, "text": t} for lv, t in pairs],
    }


KEYS = ("heading_order_precision", "heading_order_recall", "heading_order_f1")


def _prf(out: dict) -> tuple:
    return (
        out["heading_order_precision"]["value"],
        out["heading_order_recall"]["value"],
        out["heading_order_f1"]["value"],
    )


# ---------- 完美匹配 ----------


def test_perfect_match_eight_of_eight():
    gt_pairs = [
        (1, "1. Overview"),
        (2, "1.1 Acceptance objectives"),
        (1, "2. Structured elements"),
        (2, "2.1 Embedded figure"),
        (1, "3. Chunking boundary test"),
        (1, "4. Locator and integrity checks"),
        (2, "4.1 Special token line"),
        (1, "5. End marker"),
    ]
    doc = _doc([_heading(f"e{i:04d}", lv, t) for i, (lv, t) in enumerate(gt_pairs)])
    p, r, f = _prf(heading_order_prf(doc, _gt(*gt_pairs)))
    assert (p, r, f) == (1.0, 1.0, 1.0)


# ---------- 多检（DC-MVP-001 实测情形：主标题被解析为 heading） ----------


def test_over_detection_title_as_heading_nine_pred_eight_gt():
    gt_pairs = [
        (1, "1. Overview"),
        (2, "1.1 Acceptance objectives"),
        (1, "2. Structured elements"),
        (2, "2.1 Embedded figure"),
        (1, "3. Chunking boundary test"),
        (1, "4. Locator and integrity checks"),
        (2, "4.1 Special token line"),
        (1, "5. End marker"),
    ]
    headings = [
        _heading("e0000", 1, "Composite Document Parsing Test"),  # 多检（主标题）
        *(_heading(f"e{i:04d}", lv, t) for i, (lv, t) in enumerate(gt_pairs, 1)),
    ]
    p, r, f = _prf(heading_order_prf(_doc(headings), _gt(*gt_pairs)))
    assert math.isclose(p, 8 / 9)
    assert r == 1.0
    assert math.isclose(f, 16 / 17)


# ---------- 漏检 ----------


def test_miss_one_of_eight():
    gt_pairs = [(1, "A"), (2, "B"), (1, "C"), (1, "D"), (1, "E"), (1, "F"), (1, "G"), (1, "H")]
    pred_pairs = gt_pairs[:3] + gt_pairs[4:]  # 漏掉第 4 条 "D"
    doc = _doc([_heading(f"e{i:04d}", lv, t) for i, (lv, t) in enumerate(pred_pairs)])
    p, r, f = _prf(heading_order_prf(doc, _gt(*gt_pairs)))
    assert p == 1.0
    assert r == 7 / 8
    assert math.isclose(f, 2 * (7 / 8) / (1 + 7 / 8))


# ---------- 乱序（LCS = 2/3） ----------


def test_disorder_lcs_two_of_three():
    doc = _doc([_heading("e0", 1, "A"), _heading("e1", 1, "C"), _heading("e2", 1, "B")])
    p, r, f = _prf(heading_order_prf(doc, _gt((1, "A"), (1, "B"), (1, "C"))))
    assert (p, r) == (2 / 3, 2 / 3)
    assert math.isclose(f, 2 / 3)


# ---------- 匹配键语义 ----------


def test_level_mismatch_breaks_match():
    doc = _doc([_heading("e0", 2, "1. Overview")])  # level 与 GT 不符
    p, r, f = _prf(heading_order_prf(doc, _gt((1, "1. Overview"))))
    assert (p, r, f) == (0.0, 0.0, 0.0)


def test_whitespace_normalized_equality():
    doc = _doc([_heading("e0", 1, "  1. \n  Overview\t ")])
    p, r, f = _prf(heading_order_prf(doc, _gt((1, "1. Overview"))))
    assert (p, r, f) == (1.0, 1.0, 1.0)


def test_case_sensitive_strict_equality():
    # normalize_text 不做大小写折叠：大小写不同 = 不匹配（严格相等口径）
    doc = _doc([_heading("e0", 1, "1. overview")])
    p, r, f = _prf(heading_order_prf(doc, _gt((1, "1. Overview"))))
    assert (p, r, f) == (0.0, 0.0, 0.0)


# ---------- 降级路径（契约矩阵） ----------


def test_pipeline_failed():
    out = heading_order_prf(None, _gt((1, "A")))
    for k in KEYS:
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_no_annotation():
    out = heading_order_prf(_doc([_heading("e0", 1, "A")]), None)
    for k in KEYS:
        assert out[k]["reason"] == "no_annotation"


def test_no_ground_truth_headings():
    out = heading_order_prf(_doc([_heading("e0", 1, "A")]), {"doc_id": "x"})
    for k in KEYS:
        assert out[k]["reason"] == "no_ground_truth_headings"

    out = heading_order_prf(_doc([_heading("e0", 1, "A")]), {"heading_order": []})
    for k in KEYS:
        assert out[k]["reason"] == "no_ground_truth_headings"


def test_no_predicted_headings():
    doc = _doc([])  # 0 个 heading 元素
    out = heading_order_prf(doc, _gt((1, "A"), (1, "B")))
    assert out["heading_order_precision"]["reason"] == "no_predicted_headings"
    assert out["heading_order_recall"] == {
        "value": 0.0,
        "reason": None,
    }
    assert out["heading_order_f1"]["reason"] == "no_predicted_headings"
