# -*- coding: utf-8 -*-
"""编号不变性辅助审计（R-A，2026-09-16 裁决采纳外部评审执行序第一项）。

冻结 v1 一致率（agreement.py:283）要求对齐对 gold_segment_id 字符串
全等——同分组仅改名（g01→g03）或编号漂移（一方多切一段致后续 g 序号
整体错位）都会把一致率从 1 压到 0（已本地复现）。本审计不改冻结算法
与原始报告，提供分区规范化辅助口径。判别式：
- rename-only：原始 0.0/below_threshold、分区 1.0/pass、label_only=全部
- drift-offset：同分组、B 序号整体 +1 → 原始 0.0、分区 1.0
- genuine-split：A 三单元同段、B 拆出第三单元 → 分区把三个对齐单元
  全部判分组变化（partition_only ≥ 2），字符串口径只罚边界单元
- doc_id 不一致 → AgreementInputError
"""
import pytest

from stage9.agreement_audit import audit_agreement


def _mk(doc, segs, kinds=None):
    units = []
    stream = ""
    for i, seg in enumerate(segs):
        start = len(stream)
        stream += "unit%02d " % i
        units.append({"unit_id": "u%d" % (i + 1),
                      "kind": (kinds[i] if kinds else "sentence"),
                      "page": 1,
                      "char_span": [start, len(stream)],
                      "gold_segment_id": seg,
                      "hard_boundary_before": True})
    return {"doc_id": doc, "stream": stream, "units": units}


def test_rename_only_partition_recovers_one():
    a = _mk("d", ["g01", "g02", "g02"])
    b = _mk("d", ["g03", "g04", "g04"])
    r = audit_agreement(a, b)
    assert r["original"]["agreement"] == 0.0
    assert r["original"]["decision"] == "below_threshold"
    assert r["partition"]["agreement"] == 1.0
    assert r["partition"]["decision"] == "pass"
    assert len(r["label_only_pairs"]) == 3
    assert r["partition_only_pairs"] == []
    assert r["both_diff_pair_count"] == 0


def test_index_drift_partition_recovers_one():
    a = _mk("d", ["g00", "g01", "g02", "g03"])
    b = _mk("d", ["g01", "g02", "g03", "g04"])
    r = audit_agreement(a, b)
    assert r["original"]["agreement"] == 0.0
    assert r["partition"]["agreement"] == 1.0
    assert len(r["label_only_pairs"]) == 4


def test_genuine_split_partition_stricter():
    a = _mk("d", ["g01", "g01", "g01"])
    b = _mk("d", ["g01", "g01", "g02"])
    r = audit_agreement(a, b)
    assert r["original"]["agreement"] == pytest.approx(2 / 3)
    assert r["original"]["decision"] == "below_threshold"
    # 分区口径：拆段改变三个对齐单元的分组关系 → 全部判 diff
    assert r["partition"]["agreement"] == 0.0
    assert len(r["partition_only_pairs"]) == 2
    assert r["both_diff_pair_count"] == 1
    assert r["label_only_pairs"] == []


def test_same_labels_both_agree():
    a = _mk("d", ["g01", "g02", "g02"])
    b = _mk("d", ["g01", "g02", "g02"])
    r = audit_agreement(a, b)
    assert r["original"]["agreement"] == 1.0
    assert r["partition"]["agreement"] == 1.0
    assert r["original_segment_diff_count"] == 0
    assert r["partition_segment_diff_count"] == 0


def test_vocab_style_detection():
    a = _mk("d", ["g00", "g01"])
    b = _mk("d", ["seg-a", "seg-a"])
    r = audit_agreement(a, b)
    assert r["segment_vocab"]["style"] is None
    assert r["segment_vocab"]["overlap"] == 0


def test_doc_id_mismatch_raises():
    with pytest.raises(Exception):
        audit_agreement(_mk("d1", ["g01"]), _mk("d2", ["g01"]))


def test_zero_aligned_units_unchanged():
    a = _mk("d", ["g01"])
    b = _mk("d", ["g01"])
    b["units"][0]["char_span"] = [1, 7]  # strip 后 "nit00" ≠ "unit00"
    r = audit_agreement(a, b)
    assert r["aligned_pair_count"] == 0
    assert r["original"]["union"] == 2
    assert r["partition"]["union"] == 2
