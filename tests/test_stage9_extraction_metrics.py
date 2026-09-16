# -*- coding: utf-8 -*-
"""Stage 9 批次 26：对象级抽取 P/R 指标测试（R-C，纯合成夹具）。

预注册：stage9/extraction_preregistration.json（先于实现提交口径）。
覆盖：PDF 页序对齐（含错位/插入稳健性）、DOCX 序数口径、零分母
null+reason 不虚构 1.0、文档级 N/A 传播、format×domain 格聚合
micro 求和与 N/A 计数披露、预注册件字段完备。

零真实 gold 接触：全部合成标注 dict + SimpleNamespace 元素。
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from stage9.extraction_metrics import (
    aggregate_extraction_cells,
    evaluate_extraction_doc,
    extract_gold_objects,
    extract_predicted_objects,
    load_extraction_preregistration,
)

ROOT = Path(__file__).resolve().parents[1]


def _ann(doc_id, nontext, units_extra=None):
    """nontext: [(ref, page_or_None)]。"""
    units = [{"unit_id": "u%04d" % i, "kind": "nontext",
              "page": pg, "nontext_ref": ref, "gold_segment_id": "g01"}
             for i, (ref, pg) in enumerate(nontext)]
    units += (units_extra or [])
    return {"doc_id": doc_id, "units": units}


def _el(etype, page=None):
    locator = {"page": page} if page is not None else {}
    return SimpleNamespace(type=etype, source_locator=locator)


# ---- 提取 ----

def test_extract_gold_objects_family_and_key():
    ann = _ann("d", [("img:figure1", 3), ("tab:table2", 3),
                     ("img:figure2", None)])
    out = extract_gold_objects(ann, "pdf")
    assert [(o["family"], o["key"]) for o in out] == \
        [("img", 3), ("tab", 3), ("img", None)]
    docx = extract_gold_objects(ann, "docx")
    assert all(o["key"] is None for o in docx)  # DOCX 恒序数口径


def test_extract_predicted_objects_only_image_table():
    els = [_el("image", 2), _el("paragraph", 9), _el("table", 4),
           _el("heading"), _el("image")]
    out = extract_predicted_objects(els)
    assert [(o["family"], o["key"]) for o in out] == \
        [("img", 2), ("tab", 4), ("img", None)]


# ---- PDF 页序对齐 ----

def test_pdf_perfect_match():
    ann = _ann("d", [("img:figure1", 2), ("img:figure2", 5),
                     ("tab:table1", 5)])
    els = [_el("image", 2), _el("image", 5), _el("table", 5)]
    rep = evaluate_extraction_doc(ann, els, "pdf")
    for fam in ("img", "tab"):
        m = rep["families"][fam]
        assert (m["tp"], m["fp"], m["fn"]) == (1 if fam == "tab" else 2,
                                               0, 0)
        assert m["precision"] == 1.0 and m["recall"] == 1.0
        assert m["f1"] == 1.0


def test_pdf_shift_miss_counts_fn_not_false_match():
    # 漏抽第一张：gold 页序 [2,5] vs pred [5]——页码对齐不会把 5 错配
    ann = _ann("d", [("img:figure1", 2), ("img:figure2", 5)])
    rep = evaluate_extraction_doc(ann, [_el("image", 5)], "pdf")
    m = rep["families"]["img"]
    assert (m["tp"], m["fp"], m["fn"]) == (1, 0, 1)
    assert m["precision"] == 1.0 and m["recall"] == 0.5


def test_pdf_spurious_extra_prediction():
    ann = _ann("d", [("img:figure1", 2)])
    rep = evaluate_extraction_doc(ann, [_el("image", 2), _el("image", 9)],
                                  "pdf")
    m = rep["families"]["img"]
    assert (m["tp"], m["fp"], m["fn"]) == (1, 1, 0)
    assert m["precision"] == 0.5 and m["recall"] == 1.0


def test_pdf_wrong_page_never_pairs():
    ann = _ann("d", [("img:figure1", 2)])
    rep = evaluate_extraction_doc(ann, [_el("image", 9)], "pdf")
    m = rep["families"]["img"]
    assert (m["tp"], m["fp"], m["fn"]) == (0, 1, 1)
    assert m["f1"] is None  # precision+recall==0 → 不虚构


def test_pdf_missing_page_never_pairs():
    # gold 缺页（合法 null）与预测缺页：无法主张身份 → FN/FP 不虚 TP
    ann = _ann("d", [("img:figure1", None)])
    rep = evaluate_extraction_doc(ann, [_el("image")], "pdf")
    m = rep["families"]["img"]
    assert (m["tp"], m["fp"], m["fn"]) == (0, 1, 1)


# ---- DOCX 序数口径 ----

def test_docx_ordinal_alignment():
    ann = _ann("d", [("img:figure1", None), ("img:figure2", None)])
    els = [_el("image"), _el("image"), _el("image")]
    rep = evaluate_extraction_doc(ann, els, "docx")
    m = rep["families"]["img"]
    assert (m["tp"], m["fp"], m["fn"]) == (2, 1, 0)
    assert m["precision"] == pytest.approx(2 / 3)


def test_docx_page_on_gold_ignored_under_ordinal_rule():
    # DOCX 口径下 gold 的 page 字段不参与（validator 侧已禁非 null；
    # 本模块按 doc_format 走序数，不读 page）
    ann = _ann("d", [("img:figure1", 3)])
    rep = evaluate_extraction_doc(ann, [_el("image")], "docx")
    assert rep["families"]["img"]["tp"] == 1


# ---- 零分母纪律 ----

def test_zero_predictions_precision_na_recall_zero():
    ann = _ann("d", [("img:figure1", 2)])
    rep = evaluate_extraction_doc(ann, [], "pdf")
    m = rep["families"]["img"]
    assert m["precision"] is None
    assert m["precision_na_reason"] == "no_predictions"  # 评审零预测 N/A
    assert m["recall"] == 0.0  # 分母 1 合法
    assert m["f1"] is None and m["f1_na_reason"] == "parent_na"


def test_zero_gold_objects_recall_na_precision_zero():
    rep = evaluate_extraction_doc(_ann("d", []), [_el("table", 4)], "pdf")
    m = rep["families"]["tab"]
    assert m["recall"] is None
    assert m["recall_na_reason"] == "no_gold_objects"
    assert m["precision"] == 0.0


def test_empty_both_sides_discloses_both_families():
    rep = evaluate_extraction_doc(_ann("d", []), [], "pdf")
    assert set(rep["families"]) == {"img", "tab"}
    for m in rep["families"].values():
        assert m["precision"] is None and m["recall"] is None


# ---- 文档级 N/A ----

def test_doc_na_propagates_all_families():
    ann = _ann("d", [("img:figure1", 2)])
    rep = evaluate_extraction_doc(ann, [], "pdf",
                                  na_reason="parse_failed:file_not_found")
    assert rep["na_reason"] == "parse_failed:file_not_found"
    for fam, m in rep["families"].items():
        assert m["precision"] is None
        assert m["precision_na_reason"] == "doc_na"
        assert m["recall_na_reason"] == "doc_na"


# ---- format × domain 聚合 ----

def _meta(doc_id, fmt, dom):
    return {"doc_id": doc_id, "format": fmt, "domain": dom,
            "split": "dev"}


def test_aggregate_micro_sum_and_na_disclosure():
    r1 = evaluate_extraction_doc(
        _ann("d1", [("img:figure1", 2), ("img:figure2", 5)]),
        [_el("image", 2), _el("image", 5)], "pdf")          # img TP2
    r2 = evaluate_extraction_doc(
        _ann("d2", [("img:figure1", 2)]),
        [_el("image", 2), _el("image", 9)], "pdf")          # img TP1 FP1
    r3 = evaluate_extraction_doc(
        _ann("d3", [("img:figure1", 2)]), [], "pdf",
        na_reason="empty_result")                            # N/A
    cells = aggregate_extraction_cells(
        [r1, r2, r3], [_meta("d1", "pdf", "academic"),
                       _meta("d2", "pdf", "academic"),
                       _meta("d3", "pdf", "tech_report")])
    aca = cells[("pdf", "academic")]
    assert aca["docs"] == 2 and aca["na_docs"] == 0
    assert (aca["img"]["tp"], aca["img"]["fp"], aca["img"]["fn"]) == \
        (3, 1, 0)
    assert aca["img"]["precision"] == 0.75
    assert aca["img"]["recall"] == 1.0
    tec = cells[("pdf", "tech_report")]
    assert tec["docs"] == 1 and tec["na_docs"] == 1
    assert tec["img"]["precision"] is None
    assert tec["img"]["precision_na_reason"] == "no_scorable_docs"
    assert tec["img"]["recall_na_reason"] == "no_scorable_docs"


def test_aggregate_missing_meta_raises():
    rep = evaluate_extraction_doc(_ann("ghost", []), [], "pdf")
    with pytest.raises(ValueError):
        aggregate_extraction_cells([rep], [_meta("other", "pdf", "x")])


def test_aggregate_family_absent_in_docs_counts_zeros():
    # 篇内只有 img 家族 → tab 格内 0/0/0 → 双 null（零对象证据）
    r = evaluate_extraction_doc(_ann("d1", [("img:figure1", None)]),
                                [_el("image")], "docx")
    cells = aggregate_extraction_cells(
        [r], [_meta("d1", "docx", "product_manual")])
    tab = cells[("docx", "product_manual")]["tab"]
    assert (tab["tp"], tab["fp"], tab["fn"]) == (0, 0, 0)
    assert tab["precision_na_reason"] == "no_predictions"
    assert tab["recall_na_reason"] == "no_gold_objects"


# ---- 预注册件 ----

def test_preregistration_fields_and_sha():
    config, sha = load_extraction_preregistration()
    assert len(sha) == 64
    for key in ("metric", "matching_rule", "na_rules", "aggregation",
                "discipline"):
        assert key in config
    assert "autojunk=False" in config["matching_rule"]["pdf"]
    assert "ordinal" in config["matching_rule"]["docx"]
    # 磁盘字节与加载一致（sha 即冻结身份）
    raw = (ROOT / "stage9" / "extraction_preregistration.json").read_bytes()
    assert json.loads(raw.decode("utf-8")) == config
