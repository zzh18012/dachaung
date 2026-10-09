r"""W2 显式引用通道契约测试（r85 Q2；docs/
explicit-reference-relation-contract.md design freeze v1）。"""

from __future__ import annotations

import pytest

from app.models import Relation
from app.parsers.fallback_parser import match_reference_relations
from tests.test_caption_relation_contract import _cap, _el, _img, _rels


def _t(eid: str, locator: dict):
    return _el(eid, "table", "", locator)


def _p(eid: str, content: str, locator: dict | None = None):
    return _el(eid, "paragraph", content,
               locator or {"family": "structural_index",
                           "paragraph_index": 0})


def _cap_rel(cap_id: str, obj_id: str, rtype="has_caption"):
    return Relation(type=rtype, from_id=obj_id, to_id=cap_id,
                    metadata={"rule": "docx_adjacent_paragraph"})


# ---------- §4 caption-label 层 ----------

def test_caption_label_resolution():
    els = [
        _img("i1", {"family": "structural_index", "paragraph_index": 1}),
        _img("i2", {"family": "structural_index", "paragraph_index": 2}),
        _cap("c2", "Figure 2: model architecture",
             {"family": "structural_index", "paragraph_index": 3}),
        _p("p1", "Our model (Figure 2) achieves state-of-the-art results.",
           {"family": "structural_index", "paragraph_index": 4}),
    ]
    rels = _rels(match_reference_relations(els, [_cap_rel("c2", "i2")]))
    assert rels == [{
        "type": "references_figure", "from_id": "p1", "to_id": "i2",
        "metadata": {"resolution_method": "ordinal_document_order",
                     "confidence": "deterministic",
                     "label_source": "caption_label", "label": "Figure 2"},
    }]


def test_caption_label_takes_precedence_over_ordinal():
    # 标签命中 i2（文档序第 2 个 image）而非 ordinal 第 1 个
    els = [
        _img("i1", {"family": "structural_index", "paragraph_index": 1}),
        _img("i2", {"family": "structural_index", "paragraph_index": 2}),
        _cap("c1", "Figure 1: overview",
             {"family": "structural_index", "paragraph_index": 3}),
        _p("p1", "Figure 1 shows the framework.",
           {"family": "structural_index", "paragraph_index": 4}),
    ]
    rels = _rels(match_reference_relations(els, [_cap_rel("c1", "i2")]))
    assert rels[0]["to_id"] == "i2"
    assert rels[0]["metadata"]["label_source"] == "caption_label"


# ---------- §4 ordinal-fallback 层 ----------

def test_ordinal_fallback_resolution():
    els = [
        _img("i1", {"family": "structural_index", "paragraph_index": 1}),
        _img("i2", {"family": "structural_index", "paragraph_index": 2}),
        _img("i3", {"family": "structural_index", "paragraph_index": 3}),
        _p("p1", "As shown in Figure 2, the pipeline has three stages.",
           {"family": "structural_index", "paragraph_index": 4}),
    ]
    rels = _rels(match_reference_relations(els, []))
    assert rels == [{
        "type": "references_figure", "from_id": "p1", "to_id": "i2",
        "metadata": {"resolution_method": "ordinal_document_order",
                     "confidence": "deterministic",
                     "label_source": "ordinal_fallback", "label": "Figure 2"},
    }]


def test_table_ordinal_fallback_and_fullwidth_digits():
    els = [
        _t("t1", {"family": "structural_index", "paragraph_index": 1}),
        _t("t2", {"family": "structural_index", "paragraph_index": 2}),
        _p("p1", "实验结果见表２，各项指标均有提升。",
           {"family": "structural_index", "paragraph_index": 3}),
    ]
    rels = _rels(match_reference_relations(els, []))
    assert rels == [{
        "type": "references_table", "from_id": "p1", "to_id": "t2",
        "metadata": {"resolution_method": "ordinal_document_order",
                     "confidence": "deterministic",
                     "label_source": "ordinal_fallback", "label": "表２"},
    }]


# ---------- §5 排除与负向（r85 验收 negative sentence cases）----------

def test_out_of_range_label_no_edge():
    els = [
        _img("i1", {"family": "structural_index", "paragraph_index": 1}),
        _p("p1", "Figure 99 does not exist in this document.",
           {"family": "structural_index", "paragraph_index": 2}),
    ]
    assert match_reference_relations(els, []) == []


def test_unnumbered_generic_mention_no_edge():
    els = [
        _img("i1", {"family": "structural_index", "paragraph_index": 1}),
        _p("p1", "See the figure below for details.",
           {"family": "structural_index", "paragraph_index": 2}),
        _p("p2", "结果如上表所示。",
           {"family": "structural_index", "paragraph_index": 3}),
    ]
    assert match_reference_relations(els, []) == []


def test_caption_element_not_from_side():
    els = [
        _img("i1", {"family": "structural_index", "paragraph_index": 1}),
        _img("i2", {"family": "structural_index", "paragraph_index": 2}),
        _cap("c1", "Figure 1: overview",
             {"family": "structural_index", "paragraph_index": 3}),
    ]
    # 题注元素自身提及 Figure 1，但 caption 不作 from 侧 → 零边
    assert match_reference_relations(els, []) == []


def test_latin_inner_word_noise_disclosed():
    # glued 形是主目标（无空格抽取），词内噪声（"turntable 5" 命中
    # "table 5"）为契约 §3 已知代价——本用例钉住该行为，非缺陷
    els = [
        _t("t1", {"family": "structural_index", "paragraph_index": 1}),
        _t("t2", {"family": "structural_index", "paragraph_index": 2}),
        _t("t3", {"family": "structural_index", "paragraph_index": 3}),
        _t("t4", {"family": "structural_index", "paragraph_index": 4}),
        _t("t5", {"family": "structural_index", "paragraph_index": 5}),
        _p("p1", "The turntable 5 spins.",
           {"family": "structural_index", "paragraph_index": 6}),
    ]
    rels = _rels(match_reference_relations(els, []))
    assert len(rels) == 1
    assert rels[0]["metadata"]["label"] == "table 5"


# ---------- §3 多重度 ----------

def test_same_label_deduped_within_element():
    els = [
        _img("i1", {"family": "structural_index", "paragraph_index": 1}),
        _p("p1", "Figure 1 shows X. See Figure 1 again for details.",
           {"family": "structural_index", "paragraph_index": 2}),
    ]
    rels = _rels(match_reference_relations(els, []))
    assert len(rels) == 1


def test_both_families_multiple_labels():
    els = [
        _img("i1", {"family": "structural_index", "paragraph_index": 1}),
        _t("t1", {"family": "structural_index", "paragraph_index": 2}),
        _p("p1", "Figure 1 and Table 1 are related.",
           {"family": "structural_index", "paragraph_index": 3}),
    ]
    rels = _rels(match_reference_relations(els, []))
    assert {(r["type"], r["to_id"]) for r in rels} == {
        ("references_figure", "i1"), ("references_table", "t1")}


def test_spaceless_extraction_form_matched():
    els = [
        _img("i1", {"family": "structural_index", "paragraph_index": 1}),
        _img("i2", {"family": "structural_index", "paragraph_index": 2}),
        _p("p1", "asshowninFigure2thepipelinehasthreestages",
           {"family": "structural_index", "paragraph_index": 3}),
    ]
    rels = _rels(match_reference_relations(els, []))
    assert rels[0]["to_id"] == "i2"
    assert rels[0]["metadata"]["label"] == "Figure2"


# ---------- determinism ----------

def test_determinism():
    els = [
        _img("i1", {"family": "structural_index", "paragraph_index": 1}),
        _t("t1", {"family": "structural_index", "paragraph_index": 2}),
        _p("p1", "Figure 1 and Table 1 are shown.",
           {"family": "structural_index", "paragraph_index": 3}),
    ]
    assert (match_reference_relations(els, []) ==
            match_reference_relations(els, []))
