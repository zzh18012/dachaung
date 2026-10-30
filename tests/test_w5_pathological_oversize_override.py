# -*- coding: utf-8 -*-
"""W5_GATE1_PATHOLOGICAL_OVERSIZE_INTRINSIC_OVERRIDE_V1 测试
（r97 §十一 14 条硬门清单；参数冻结 §十四：MIN_COLS=6 /
OVERSIZE_RATIO strictly > 1.0 / GATE1_OVERLAP=0.5）。

契约边界：cols>=6 仅存在于 override 分支（COLS_6 =
OVERRIDE_EVIDENCE_ONLY），基础 acceptance contract 无 cols 约束
（3×1 真表继续合法，见 test_w5_table_gates.py）。

合成几何约定：page 200×100 → page_area 20000；表 bbox
[10,10,110,90]（面积 8000）；oversize 簇 = 面积严格 > 20000；
local 簇 = 面积比 ≤ 1.0。
"""

from __future__ import annotations

import pytest

from app.parsers.fallback_parser import (
    TABLE_FIGURE_OVERLAP_DROP_FRAC,
    TABLE_PATHO_OVERSIZE_MIN_COLS,
    TABLE_PATHO_OVERSIZE_PAGE_RATIO,
    _gate1_pathological_oversize_scope,
    _gate_pdf_table,
    _gate_pdf_table_with_override,
)

BBOX = [10.0, 10.0, 110.0, 90.0]          # 面积 8000
PAGE_AREA = 20000.0                        # 200×100 页
OVERSIZE = [0.0, 0.0, 220.0, 100.0]        # 22000 > PAGE_AREA，全含 BBOX
OVERSIZE_SMALL_HIT = [-200.0, -200.0, 40.0, 90.0]  # oversize，交 BBOX 30×80
LOCAL_FULL = [0.0, 0.0, 110.0, 90.0]       # 9900 ≤ 20000，全含 BBOX
HALF_RASTER = [10.0, 10.0, 110.0, 50.0]    # 交 BBOX = 4000/8000 = 0.5
LOCAL_HALF = [10.0, 10.0, 110.0, 50.0]     # 4000 ≤ 20000 → local 族


# ---------- §十一 冻结参数守护 ----------

def test_frozen_params_guard():
    assert TABLE_PATHO_OVERSIZE_MIN_COLS == 6
    assert TABLE_PATHO_OVERSIZE_PAGE_RATIO == 1.0
    assert TABLE_FIGURE_OVERLAP_DROP_FRAC == 0.5


# ---------- 1–3：pathological oversize only × cols 边界 ----------

def test_case1_oversize_only_cols5_no_override():
    accepted, _, _ = _gate_pdf_table_with_override(
        BBOX, 3, 5, 16, [], [OVERSIZE], PAGE_AREA)
    assert not accepted


def test_case2_oversize_only_cols6_override():
    accepted, warn, partial_cov = _gate_pdf_table_with_override(
        BBOX, 3, 6, 16, [], [OVERSIZE], PAGE_AREA)
    assert accepted
    # override 接受仍按 r6 口径披露：vector frac=1.0 > 0
    assert warn is not None and warn["family"] == "vector"
    assert warn["frac"] == 1.0
    assert partial_cov  # 16 词 < 3×6 = 18 → 贫格披露照常


def test_case3_oversize_only_cols7_override():
    accepted, _, _ = _gate_pdf_table_with_override(
        BBOX, 3, 7, 16, [], [OVERSIZE], PAGE_AREA)
    assert accepted


# ---------- 4–5：其他 veto family 存在 → 不可覆盖 ----------

def test_case4_oversize_plus_raster_veto_no_override():
    accepted, _, _ = _gate_pdf_table_with_override(
        BBOX, 3, 6, 16, [HALF_RASTER], [OVERSIZE], PAGE_AREA)
    assert not accepted


def test_case5_oversize_plus_local_vector_veto_no_override():
    accepted, _, _ = _gate_pdf_table_with_override(
        BBOX, 3, 6, 16, [], [OVERSIZE, LOCAL_HALF], PAGE_AREA)
    assert not accepted


# ---------- 6–7：非 oversize 唯一 veto → 不入 override 域 ----------

def test_case6_local_vector_only_no_override():
    accepted, _, _ = _gate_pdf_table_with_override(
        BBOX, 3, 6, 16, [], [LOCAL_FULL], PAGE_AREA)
    assert not accepted


def test_case7_raster_only_no_override():
    raster_full = [10.0, 10.0, 110.0, 90.0]
    accepted, _, _ = _gate_pdf_table_with_override(
        BBOX, 3, 6, 16, [raster_full], [], PAGE_AREA)
    assert not accepted


# ---------- 8：无 figure veto → r6 正常路径 ----------

def test_case8_no_veto_normal_r6_path():
    # 3×1 + 16 词：基础 contract 无 cols 约束，照常接受
    accepted, warn, _ = _gate_pdf_table_with_override(
        BBOX, 3, 1, 16, [], [], PAGE_AREA)
    assert accepted and warn is None
    # r6 未拒 → wrapper 与 _gate_pdf_table 逐值一致
    assert _gate_pdf_table_with_override(
        BBOX, 3, 1, 16, [], [], PAGE_AREA) == _gate_pdf_table(
        BBOX, 3, 1, 16, [], [])


# ---------- 9：fail closed ----------

def test_case9_page_area_nonpositive_no_override():
    accepted, _, _ = _gate_pdf_table_with_override(
        BBOX, 3, 6, 16, [], [OVERSIZE], 0.0)
    assert not accepted
    accepted, _, _ = _gate_pdf_table_with_override(
        BBOX, 3, 6, 16, [], [OVERSIZE], -1.0)
    assert not accepted


# ---------- 10：多 oversize 簇确定性 max ----------

def test_case10_multiple_oversize_deterministic_max():
    for order in ([OVERSIZE, OVERSIZE_SMALL_HIT],
                  [OVERSIZE_SMALL_HIT, OVERSIZE]):
        # 小交簇 30×80/8000 = 0.3、大簇 1.0 → max = 1.0 → scope true
        assert _gate1_pathological_oversize_scope(
            BBOX, [], order, PAGE_AREA)
        accepted, warn, _ = _gate_pdf_table_with_override(
            BBOX, 3, 6, 16, [], order, PAGE_AREA)
        assert accepted
        assert warn["frac"] == pytest.approx(1.0)
    # 仅 0.3 交的 oversize 簇单独存在 → max 0.3 < 0.5 → scope false
    assert not _gate1_pathological_oversize_scope(
        BBOX, [], [OVERSIZE_SMALL_HIT], PAGE_AREA)


# ---------- 11–12：override 后现行 gate2 仍全效 ----------

def test_case11_cols_pass_words_below_min_still_reject():
    accepted, _, _ = _gate_pdf_table_with_override(
        BBOX, 3, 6, 3, [], [OVERSIZE], PAGE_AREA)
    assert not accepted


def test_case12_cols_pass_rows_below_min_still_reject():
    accepted, _, _ = _gate_pdf_table_with_override(
        BBOX, 1, 6, 16, [], [OVERSIZE], PAGE_AREA)
    assert not accepted


# ---------- 13：非 scope 候选行为逐值等于 r6 ----------

@pytest.mark.parametrize("raster,vecfig,rows,cols,words", [
    ([], [], 3, 1, 16),                                  # 零重叠接受
    ([], [LOCAL_FULL], 3, 6, 16),                        # local 唯一 veto
    ([[10.0, 10.0, 110.0, 90.0]], [], 3, 6, 16),         # raster 唯一 veto
    ([], [OVERSIZE_SMALL_HIT], 3, 6, 16),                # oversize 但 frac<0.5
    ([HALF_RASTER], [OVERSIZE], 3, 6, 16),               # oversize+raster 双 veto
    ([], [], 2, 2, 3, ),                                 # rule2 拒（无重叠）
    ([[0.0, 0.0, 110.0, 14.9]], [], 3, 1, 16),           # 0<frac<0.5 部分相交
])
def test_case13_non_scope_exactly_r6(raster, vecfig, rows, cols, words):
    assert _gate_pdf_table_with_override(
        BBOX, rows, cols, words, raster, vecfig, PAGE_AREA
    ) == _gate_pdf_table(BBOX, rows, cols, words, raster, vecfig)


# ---------- 14：scope 规范化等价 fixture（r97 §六逐句参考实现） ----------

def _reference_scope(bbox, raster_bboxes, vecfig_bboxes, page_area):
    """裁决 §六原文直译：三类最大 overlap frac；oversize = 簇面积比
    严格 > 1.0；空集 max = 0；ov>=0.5 ∧ ra<0.5 ∧ lo<0.5。"""
    if page_area <= 0:
        return False
    oversize = [cb for cb in vecfig_bboxes
                if (cb[2] - cb[0]) * (cb[3] - cb[1])
                > 1.0 * page_area]
    local = [cb for cb in vecfig_bboxes if cb not in oversize]

    def max_frac(boxes):
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        best = 0.0
        for b in boxes:
            w = min(bbox[2], b[2]) - max(bbox[0], b[0])
            h = min(bbox[3], b[3]) - max(bbox[1], b[1])
            if w > 0 and h > 0 and area > 0:
                best = max(best, w * h / area)
        return best

    return (max_frac(oversize) >= 0.5
            and max_frac(raster_bboxes) < 0.5
            and max_frac(local) < 0.5)


@pytest.mark.parametrize("raster,vecfig,page_area", [
    ([], [OVERSIZE], PAGE_AREA),
    ([], [OVERSIZE, LOCAL_FULL], PAGE_AREA),
    ([HALF_RASTER], [OVERSIZE], PAGE_AREA),
    ([], [LOCAL_FULL], PAGE_AREA),
    ([[10.0, 10.0, 110.0, 90.0]], [OVERSIZE], PAGE_AREA),
    # 边界：簇面积恰 = page_area → local 族（strictly > 1.0）
    ([], [[0.0, 0.0, 200.0, 100.0], OVERSIZE], PAGE_AREA),
    # 边界：oversize 族 frac 恰 0.5 → scope true（>= 0.5）；
    # 该簇面积 610×550 > 20000（oversize），交 BBOX 恰 100×40 = 0.5
    ([], [[-500.0, -500.0, 110.0, 50.0]], PAGE_AREA),
    # 边界：local 族 frac 恰 0.5 → scope false（< 0.5 才行）
    ([], [[0.0, 0.0, 110.0, 50.0]], PAGE_AREA),
    ([], [], PAGE_AREA),
    ([], [OVERSIZE], 0.0),
])
def test_case14_scope_normalization_equivalence(raster, vecfig, page_area):
    assert _gate1_pathological_oversize_scope(
        BBOX, raster, vecfig, page_area
    ) == _reference_scope(BBOX, raster, vecfig, page_area)
