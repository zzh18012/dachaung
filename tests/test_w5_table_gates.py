# -*- coding: utf-8 -*-
"""W5 几何表格门测试（r89 Path A 第二步；规格
design/w5-table-detection-spec-v1.md §3.1/§5.2/§8.7）。

纯函数面：门判定边界、题注词保护、吸收池过滤、partial_coverage
贫富对照、常数守护（§8.7：0.5/4/2 在 dev 零反例，改常数必须过这批）。
"""

from __future__ import annotations

from app.parsers.fallback_parser import (
    TABLE_FIGURE_OVERLAP_DROP_FRAC,
    TABLE_MIN_ROWS,
    TABLE_MIN_WORDS,
    _bbox_intersection_area,
    _caption_protected_indices,
    _gate_pdf_table,
    _word_center_in_bbox,
)

BBOX = [0.0, 0.0, 100.0, 100.0]


def _w(text: str, x0: float, x1: float, top: float, bottom: float) -> dict:
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": bottom}


# ---------- §8.7 常数守护 ----------

def test_constants_guard():
    assert TABLE_FIGURE_OVERLAP_DROP_FRAC == 0.5
    assert TABLE_MIN_WORDS == 4
    assert TABLE_MIN_ROWS == 2


# ---------- 门边界（§3.1 规则 1/2 + §4 部分相交披露） ----------

def test_gate_zero_overlap_accepted_no_warning():
    accepted, warn, partial_cov = _gate_pdf_table(
        BBOX, rows_count=3, cols_count=1, words_inside=16,
        raster_bboxes=[], vecfig_bboxes=[])
    assert accepted
    assert warn is None
    assert not partial_cov


def test_gate_rule1_at_threshold_drops():
    # frac == 0.5 恰好触线 → 弃（规格措辞 ≥ 0.5）
    half = [0.0, 0.0, 100.0, 50.0]
    accepted, _, _ = _gate_pdf_table(
        BBOX, 3, 1, 16, [half], [])
    assert not accepted


def test_gate_rule1_partial_keeps_with_warning():
    # 0 < frac < 0.5 → 保留 + 部分相交披露
    slight = [0.0, 0.0, 100.0, 49.9]
    accepted, warn, _ = _gate_pdf_table(
        BBOX, 3, 1, 16, [slight], [])
    assert accepted
    assert warn is not None
    assert warn["family"] == "raster"
    assert 0 < warn["frac"] < 0.5


def test_gate_rule1_vector_family_wins_when_larger():
    vec = [0.0, 0.0, 100.0, 100.0]
    accepted, warn, _ = _gate_pdf_table(
        BBOX, 3, 1, 16, [], [vec])
    assert not accepted
    # 全含 raster 次之的混合面：family 取更大者
    slight = [0.0, 0.0, 100.0, 10.0]
    accepted, warn, _ = _gate_pdf_table(
        BBOX, 3, 1, 16, [slight], [vec])
    assert not accepted


def test_gate_rule2_words_boundary():
    # 3 词弃 / 4 词保（rows 合格、零重叠）
    accepted, _, _ = _gate_pdf_table(BBOX, 2, 2, 3, [], [])
    assert not accepted
    accepted, _, _ = _gate_pdf_table(BBOX, 2, 2, 4, [], [])
    assert accepted


def test_gate_rule2_rows_boundary():
    # 1 行弃 / 2 行保
    accepted, _, _ = _gate_pdf_table(BBOX, 1, 3, 16, [], [])
    assert not accepted
    accepted, _, _ = _gate_pdf_table(BBOX, 2, 3, 16, [], [])
    assert accepted


def test_gate_no_cols_constraint():
    # dev 唯一真表形态：3×1 + 16 词必须保（cols ≥ 2 约束会误杀）
    accepted, warn, _ = _gate_pdf_table(BBOX, 3, 1, 16, [], [])
    assert accepted and warn is None


# ---------- partial_coverage 贫富对照（§5.2(4) 披露面） ----------

def test_partial_coverage_sparse_flag():
    # 词数 < 行×列（贫格）→ 披露
    accepted, _, partial_cov = _gate_pdf_table(
        BBOX, 6, 4, 20, [], [])
    assert accepted
    assert partial_cov


def test_partial_coverage_dense_not_flagged():
    accepted, _, partial_cov = _gate_pdf_table(
        BBOX, 3, 1, 16, [], [])
    assert accepted
    assert not partial_cov


# ---------- 题注词保护（§5.2(3)：题注不吸收） ----------

def test_caption_line_protected():
    words = [
        _w("Table", 0, 20, 0, 10),
        _w("1:", 22, 28, 0, 10),
        _w("body", 0, 20, 20, 30),
    ]
    protected = _caption_protected_indices(words)
    assert protected == {0, 1}


def test_figure_caption_line_protected():
    words = [
        _w("Figure", 0, 24, 0, 10),
        _w("2:", 26, 32, 0, 10),
        _w("data", 0, 20, 20, 30),
    ]
    assert _caption_protected_indices(words) == {0, 1}


def test_body_line_not_protected():
    words = [
        _w("The", 0, 20, 0, 10),
        _w("model", 22, 50, 0, 10),
    ]
    assert _caption_protected_indices(words) == set()


def test_caption_continuation_line_not_protected():
    # 多行题注续行（单独不过 _is_caption）不在保护集——已披露边界
    words = [
        _w("Table", 0, 20, 0, 10),
        _w("1:", 22, 28, 0, 10),
        _w("continued", 0, 40, 20, 30),
    ]
    assert _caption_protected_indices(words) == {0, 1}


def test_caption_protection_same_line_tolerance_as_grouping():
    # y 中心差 > 3.0 → 不同视觉行（与 _group_words_to_paragraphs 同款）
    words = [
        _w("Table", 0, 20, 0, 10),
        _w("1:", 22, 28, 0, 10),
        _w("Table", 0, 20, 12, 22),   # y 中心 17 vs 5 → 分行
        _w("2:", 22, 28, 12, 22),
    ]
    assert _caption_protected_indices(words) == {0, 1, 2, 3}


# ---------- 几何基础 ----------

def test_bbox_intersection_area_disjoint_zero():
    assert _bbox_intersection_area([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0


def test_bbox_intersection_area_overlap():
    assert _bbox_intersection_area([0, 0, 10, 10], [5, 5, 15, 15]) == 25.0


def test_word_center_in_bbox():
    bbox = [0, 0, 100, 100]
    assert _word_center_in_bbox(_w("in", 10, 20, 10, 20), bbox)
    assert not _word_center_in_bbox(_w("out", 110, 120, 10, 20), bbox)
    # 词中心恰在边界上 → 含入（闭区间）
    assert _word_center_in_bbox(_w("edge", 90, 110, 40, 60), bbox)
