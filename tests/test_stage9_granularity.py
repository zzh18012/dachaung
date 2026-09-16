# -*- coding: utf-8 -*-
"""Stage 9 批次 26：粒度诊断与 oracle 上界测试（R-B，纯合成夹具）。

覆盖：段区间聚合、oracle 均分片不跨段、上界语义（全段≤N → 1.0；
单段拆 2 → 0.0——gold 单簇 vs 两块，评审示意机理的机械验证）、
分布披露（over_grid_max）、集级 macro、预注册件字段。

零真实 gold 接触（真实 run = G⑥ 后 dev only，纪律见预注册）。
"""
import json
from pathlib import Path

import pytest

from stage9.granularity import (
    granularity_bound,
    granularity_macro,
    oracle_pieces,
    segment_spans,
)

ROOT = Path(__file__).resolve().parents[1]


def _ann(doc_id, seg_units):
    """seg_units: {gid: [unit_char_count,...]}，流按序拼接。"""
    stream = ""
    units = []
    seg_list = []
    for gid, sizes in seg_units.items():
        seg_start = len(stream)
        for i, size in enumerate(sizes):
            units.append({"unit_id": "u%04d" % len(units),
                          "kind": "sentence",
                          "char_span": [len(stream),
                                        len(stream) + size],
                          "gold_segment_id": gid})
            stream += "x" * size
        seg_list.append((gid, seg_start, len(stream)))
    return ({"doc_id": doc_id, "stream": stream, "units": units},
            seg_list)


def test_segment_spans_aggregation():
    ann, segs = _ann("d", {"g01": [10, 12], "g02": [8]})
    out = segment_spans(ann)
    assert [(s["gold_segment_id"], s["start"], s["end"], s["chars"],
             s["text_units"]) for s in out] == \
        [("g01", 0, 22, 22, 2), ("g02", 22, 30, 8, 1)]


def test_oracle_pieces_even_and_bounded():
    seg = {"gold_segment_id": "g", "start": 0, "end": 30}
    pieces = oracle_pieces(seg, 8)
    assert all(b - a <= 8 for a, b in pieces)
    assert sum(b - a for a, b in pieces) == 30
    assert len(pieces) == 4  # ceil(30/8)
    # 零长段 → 无片
    assert oracle_pieces({"gold_segment_id": "g", "start": 5,
                          "end": 5}, 8) == []


def test_bound_one_when_all_segments_fit():
    ann, _ = _ann("d", {"g01": [10], "g02": [10, 10]})
    r = granularity_bound(ann, n_grid=(30,))
    b = r["bounds"][30]
    assert b["oracle_chunks"] == 2
    assert b["split_segments"] == 0
    assert b["ari_bound"] == 1.0  # 段即块：结构天花板 1


def test_bound_zero_single_segment_split_two():
    # 评审机理的机械验证：gold 单段 4 unit 拆 2 片 → 单簇 vs 两簇
    # ARI=0（评审示意 0.646/0.306 的最小可复现同构）
    ann, _ = _ann("d", {"g01": [10, 10, 10, 10]})
    r = granularity_bound(ann, n_grid=(21,))
    b = r["bounds"][21]
    assert b["oracle_chunks"] == 2
    assert b["split_segments"] == 1
    assert b["ari_bound"] == 0.0


def test_bound_between_zero_and_one_partial_split():
    # 一段可整装、一段须拆 → 上界介于 0 与 1 之间且 < 全fit 的 1.0
    ann, _ = _ann("d", {"g01": [10, 10], "g02": [10, 10, 10, 10]})
    r = granularity_bound(ann, n_grid=(21,))
    b = r["bounds"][21]
    assert 0.0 < b["ari_bound"] < 1.0
    assert b["split_segments"] == 1


def test_distribution_disclosure_over_grid_max():
    ann, _ = _ann("d", {"g01": [10, 30], "g02": [10]})
    r = granularity_bound(ann, n_grid=(20, 50))
    assert r["segments"] == 2
    assert r["segment_chars"]["max"] == 40
    assert r["segment_chars"]["median"] == pytest.approx(25.0)
    assert r["segment_chars"]["over_grid_max"] == {"20": 1, "50": 0}


def test_macro_average_excludes_none():
    a = granularity_bound(_ann("d1", {"g01": [10, 10]})[0], n_grid=(30,))
    b = granularity_bound(_ann("d2", {"g01": [10, 10, 10, 10]})[0],
                          n_grid=(30,))
    # d2 单段 40 字 > 30 → 拆 2 → ari_bound 0；d1 全 fit → 1.0
    assert a["bounds"][30]["ari_bound"] == 1.0
    assert b["bounds"][30]["ari_bound"] == 0.0
    m = granularity_macro([a, b], n_grid=(30,))
    assert m[30] == 0.5


def test_preregistration_discipline_locked():
    raw = (ROOT / "stage9" / "granularity_preregistration.json").read_bytes()
    config = json.loads(raw.decode("utf-8"))
    for key in ("metric", "oracle_rule", "ari_bound_semantics",
                "distribution_disclosure", "discipline"):
        assert key in config
    assert "never modified" in config["discipline"]
    assert "14 dev" in config["discipline"]
