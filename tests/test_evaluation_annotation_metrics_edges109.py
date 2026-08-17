"""evaluation/annotation_metrics.py 第三百四十一轮 edges 测试（Round 897）。

补强 edges108 未触及的角度（第二百七十三批，probe 实证）。

新角度：
- 顺序搜索约束：第二个 marker "AB" 在 pos 0 也出现，但
  search_from=5 强制命中 pos 6（gts [5,6] vs pred [5]
  → P 1.0 R 0.5 F1 2/3；_missing_markers 不出现）
- CJK marker：chunks ["中文内容","测试"] 边界 4，marker "内容"
  after → gt=4 → tol 0 全 1.0
- 空中间 chunk 产生额外预测边界：["AB","","CD"] → preds [2,3]
  vs 单 anchor → P 0.5 R 1.0 F1 2/3
- figure_caption_prf 对带 figure_caption_pairs 的真实标注仍
  null 三件套（本期不做关系启发式）
- __all__ 三项顺序 + PARSER_DOES_NOT_EMIT_RELATIONS 常量
- forbidden tokens 第三百六十七批
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 顺序搜索跳过更早出现 ----------

def test_sequential_search_skips_earlier_occurrence_batch95():
    out = chunk_boundary_prf(
        _doc("AB CD", "AB"),
        _ann({"marker": "CD", "position": "after"},
             {"marker": "AB", "position": "before"}), 0)
    # CD found@3 after→gt=5, search_from=5；AB 从 5 起找到 pos 6
    # （pos 0 的第一次出现被跳过）→ gts [5,6] vs preds [5]
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.5,
                                            "reason": None}
    assert abs(out["chunk_boundary_f1"]["value"] - 2 / 3) < 1e-12
    assert "_missing_markers" not in out


# ---------- CJK marker ----------

def test_cjk_marker_after_boundary_batch95():
    out = chunk_boundary_prf(
        _doc("中文内容", "测试"),
        _ann({"marker": "内容", "position": "after"}), 0)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- 空中间 chunk 额外边界 ----------

def test_empty_middle_chunk_extra_boundary_batch95():
    out = chunk_boundary_prf(
        _doc("AB", "", "CD"),
        _ann({"marker": "AB", "position": "after"}), 0)
    # stream "AB CD"；空 chunk find("") 命中 pos 3 → preds [2,3]
    assert out["chunk_boundary_precision"] == {"value": 0.5,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert abs(out["chunk_boundary_f1"]["value"] - 2 / 3) < 1e-12


# ---------- figure_caption 带 pairs ----------

def test_figure_caption_real_pairs_still_null_batch95():
    fc = figure_caption_prf(
        {"chunks": [{"text": "A"}, {"text": "B"}]},
        {"figure_caption_pairs": [{"figure": "f", "caption": "c"}]})
    assert fc == {
        "figure_caption_precision": {
            "value": None,
            "reason": PARSER_DOES_NOT_EMIT_RELATIONS},
        "figure_caption_recall": {
            "value": None,
            "reason": PARSER_DOES_NOT_EMIT_RELATIONS},
        "figure_caption_f1": {
            "value": None,
            "reason": PARSER_DOES_NOT_EMIT_RELATIONS},
    }
    assert PARSER_DOES_NOT_EMIT_RELATIONS == \
        "parser_does_not_emit_relations"


# ---------- 导出面 ----------

def test_all_exports_order_batch95():
    assert am.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch95():
    src = _src()
    assert 'joined_raw = " ".join(norm_chunks)' in src
    assert "search_from = find_pos + len(marker)" in src
    assert "pairs.sort(key=lambda x: x[0])" in src
    assert 'if position == "before":' in src


# ---------- forbidden tokens 第三百六十七批 ----------

def test_source_no_eval_batch95():
    assert "eval(" not in _src()


def test_source_no_exec_batch95():
    assert "exec(" not in _src()


def test_source_no_compile_batch95():
    assert "compile(" not in _src()


def test_source_no_globals_batch95():
    assert "globals(" not in _src()


def test_source_no_locals_batch95():
    assert "locals(" not in _src()


def test_source_no_os_system_batch95():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch95():
    assert "subprocess" not in _src()


def test_source_no_popen_batch95():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch95():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch95():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch95():
    assert "socket" not in _src()


def test_source_no_requests_batch95():
    assert "requests" not in _src()


def test_source_no_urllib_batch95():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch95():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch95():
    assert "yield" not in _src()


def test_source_no_async_await_batch95():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch95():
    assert "open(" not in _src()
