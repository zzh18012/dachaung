# -*- coding: utf-8 -*-
"""Stage 9 批次 26：chunk→unit 投影 fixture（设计 §3 要求手算锁死）。

流：STREAM = "Alpha beta gamma. Delta epsilon. Zeta eta theta."（48 字符）
unit 平铺（分隔空格归前一 unit）：u1 [0,18) u2 [18,33) u3 [33,48)
chunk 切点与流不同位：c0=[0,17) c1=[17,37) c2=[37,48)
"""
from stage9.project import locate_chunks, project_chunks_to_units

STREAM = "Alpha beta gamma. Delta epsilon. Zeta eta theta."
UNITS = [
    {"unit_id": "u1", "char_span": [0, 18]},
    {"unit_id": "u2", "char_span": [18, 33]},
    {"unit_id": "u3", "char_span": [33, 48]},
]
CHUNKS = ["Alpha beta gamma.", " Delta epsilon. Zeta", " eta theta."]


def test_locate_chunks_sequential():
    spans = locate_chunks(CHUNKS, STREAM)
    assert spans == [(0, 17), (17, 37), (37, 48)]


def test_locate_chunks_unmatched():
    spans = locate_chunks(["流中不存在", "Alpha beta"], STREAM)
    assert spans[0] is None
    assert spans[1] == (0, 10)


def test_locate_chunks_empty():
    assert locate_chunks([""], STREAM) == [None]


def test_projection_hand_computed():
    """手算：u1 归 c0（重叠 17>1）、u2 归 c1（15）、u3 归 c2（11>4）；
    u1 与 u3 均与两个 chunk 正重叠 → 跨块披露；无 unmatched。"""
    result = project_chunks_to_units(CHUNKS, STREAM, UNITS)
    assert result.attributions == {"u1": 0, "u2": 1, "u3": 2}
    assert result.cross_chunk_unit_ids == ("u1", "u3")
    assert result.unmatched_chunk_indexes == ()


def test_projection_unit_inside_single_chunk():
    result = project_chunks_to_units(
        [STREAM], STREAM, UNITS)
    assert result.attributions == {"u1": 0, "u2": 0, "u3": 0}
    assert result.cross_chunk_unit_ids == ()


def test_projection_tie_breaks_to_earlier_chunk():
    """u [5,15) 与 c0 [0,10) 重叠 5、与 c1 [10,15) 重叠 5 → 平局取先者。"""
    stream = "0123456789abcde"
    units = [{"unit_id": "u", "char_span": [5, 15]}]
    result = project_chunks_to_units(["0123456789", "abcde"], stream, units)
    assert result.attributions == {"u": 0}
    assert result.cross_chunk_unit_ids == ("u",)


def test_projection_unmatched_chunk_disclosed():
    chunks = ["流中不存在", "Alpha beta gamma. Delta epsilon. "
              "Zeta eta theta."]
    result = project_chunks_to_units(chunks, STREAM, UNITS)
    assert result.unmatched_chunk_indexes == (0,)
    assert result.chunk_spans[0] is None
    # 全部 unit 仍被 c1 覆盖
    assert set(result.attributions.values()) == {1}


def test_projection_unit_covered_by_nothing():
    """unit 区间只与 unmatched chunk 区域重叠 → 不归属（不静默计入）。"""
    stream = "aaaaabbbbb"
    units = [{"unit_id": "u", "char_span": [0, 10]}]
    result = project_chunks_to_units(["找不到的块"], stream, units)
    assert result.attributions == {}
