"""evaluation/annotation_metrics.py 第二百零二轮 edges 测试（Round 721）。

补强 edges81/edges82 未触及的角度（第八十六批）。

新角度：
- figure_caption_prf 完全忽略参数（任意 document/annotation 均固定 null 三键）
- 1 chunk / 0 chunks × 有无 anchors 四象限（recall 0.0 ratio vs 全 null）
- annotation []（falsy）走 no_annotation
- 空 marker / 缺 marker 键 → 进 _missing_markers，recall no_ground_truth_anchors_in_stream
- position 缺省 = after
- 贪心一对一：近的 pred 抢走 anchor（P=0.5 R=1.0 f1=2/3）
- 精确双命中（P=R=f1=1.0）
- tolerance=0 时 d=1 不匹配 → P=R=0.0 → f1 走 denom<=0 分支 = 0.0
- 一个 anchor 缺失一个命中（num_gt=1，_missing_markers 记录）
- search_from 前进防共享：anchors [ab, b] / [b, ab] 交叠一对一
- 空 text chunk 产生位置 0 的 pred（现状记录）
- marker 必须匹配规范化后文本（双空格 marker 找不到）
- _tolerance_chars 五条路径全记录
- AST（figure If0·Return1·Subscript4 / chunk If15·For7·Return5·Continue3·Break1·ListComp1·AnnAssign5·Subscript37）
- 源码补强（_null×14 / _ratio×5 / _tolerance_chars×5 / no_pred×4 / search_from×3 / used_pred·used_gt×3）
- forbidden tokens 第一百九十一批
"""

from __future__ import annotations

import ast
import inspect

import pytest

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


def _doc(*texts) -> dict:
    return {"chunks": [{"text": t} for t in texts]}


# ---------- figure_caption_prf ----------

@pytest.mark.parametrize("doc,ann", [
    (None, None),
    ({"chunks": []}, {"chunk_boundary_anchors": []}),
    ("anything", 12345),  # 类型不强制，函数体不读参数
])
def test_figure_caption_ignores_args_batch53(doc, ann):
    out = figure_caption_prf(doc, ann)
    assert list(out.keys()) == ["figure_caption_precision",
                                "figure_caption_recall", "figure_caption_f1"]
    for v in out.values():
        assert v == {"value": None, "reason": PARSER_DOES_NOT_EMIT_RELATIONS}


def test_figure_caption_constant_value_batch53():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


# ---------- chunk 数量四象限 ----------

def test_one_chunk_with_anchors_batch53():
    out = chunk_boundary_prf(_doc("abc"), {"chunk_boundary_anchors": [{"marker": "b"}]})
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert out["chunk_boundary_recall"] == {"value": 0.0, "reason": None}
    assert out["chunk_boundary_f1"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert out["_tolerance_chars"] == {"value": 30, "reason": None}


def test_one_chunk_without_anchors_batch53():
    out = chunk_boundary_prf(_doc("abc"), {"chunk_boundary_anchors": []})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert out[k] == {"value": None, "reason": "no_predicted_boundaries"}, k


def test_zero_chunks_with_anchors_batch53():
    out = chunk_boundary_prf({"chunks": []},
                             {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert out["chunk_boundary_recall"] == {"value": 0.0, "reason": None}


def test_two_chunks_without_anchors_batch53():
    out = chunk_boundary_prf(_doc("aa", "bb"),
                             {"chunk_boundary_anchors": []})  # truthy 但无 anchors
    for k in ("chunk_boundary_precision", "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert out[k] == {"value": None, "reason": "no_ground_truth_anchors"}, k


# ---------- annotation falsy ----------

def test_annotation_empty_list_no_annotation_batch53():
    out = chunk_boundary_prf(_doc("aa", "bb"), [])
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


# ---------- 空 marker / 缺 marker 键 ----------

def test_empty_marker_goes_missing_batch53():
    out = chunk_boundary_prf(_doc("aa", "bb"),
                             {"chunk_boundary_anchors": [{"marker": ""}]})
    assert out["_missing_markers"] == {"value": [""], "reason": None}
    assert out["chunk_boundary_recall"]["reason"] == \
        "no_ground_truth_anchors_in_stream"
    assert out["chunk_boundary_precision"] == {"value": 0.0, "reason": None}


def test_missing_marker_key_defaults_empty_batch53():
    out = chunk_boundary_prf(_doc("aa", "bb"),
                             {"chunk_boundary_anchors": [{"position": "before"}]})
    assert out["_missing_markers"]["value"] == [""]


# ---------- position 缺省 ----------

def test_position_defaults_to_after_batch53():
    # chunks AAAA/BBBB/CCCC：pred p0=4；marker AAAA 无 position → after → gt=4
    out = chunk_boundary_prf(_doc("AAAA", "BBBB", "CCCC"),
                             {"chunk_boundary_anchors": [{"marker": "AAAA"}]})
    assert out["chunk_boundary_precision"]["value"] == 0.5  # p0 命中，p1(9) 距 4 为 5 也命中?
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- 贪心一对一 ----------

def test_closer_pred_steals_anchor_batch53():
    # stream "AAAA BBBB CCCC"，preds=[4, 9]，anchor BBBB before → gt=5
    # d(p0)=1 < d(p1)=4 → p0 抢到 → matched=1 → P=0.5 R=1.0
    out = chunk_boundary_prf(
        _doc("AAAA", "BBBB", "CCCC"),
        {"chunk_boundary_anchors": [{"marker": "BBBB", "position": "before"}]},
        tolerance_chars=10)
    assert out["chunk_boundary_precision"]["value"] == pytest.approx(0.5)
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 / 3)


def test_exact_double_hit_batch53():
    out = chunk_boundary_prf(
        _doc("AAAA", "BBBB", "CCCC"),
        {"chunk_boundary_anchors": [
            {"marker": "AAAA", "position": "after"},   # gt=4 = p0
            {"marker": "CCCC", "position": "before"},  # gt=10 vs p1=9
        ]},
        tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_tolerance_zero_distance_one_fails_batch53():
    # pred=4，anchor AAAA before → gt=0，d=4 > 0 → 0 匹配
    out = chunk_boundary_prf(
        _doc("AAAA", "BBBB"),
        {"chunk_boundary_anchors": [{"marker": "AAAA", "position": "before"}]},
        tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0  # denom<=0 分支


# ---------- 部分 anchor 缺失 ----------

def test_one_found_one_missing_anchor_batch53():
    out = chunk_boundary_prf(
        _doc("AAAA", "BBBB", "CCCC"),
        {"chunk_boundary_anchors": [
            {"marker": "BBBB", "position": "before"},  # gt=5
            {"marker": "ZZZ"},                          # 不在流中
        ]})
    assert out["_missing_markers"]["value"] == ["ZZZ"]
    assert out["chunk_boundary_recall"]["value"] == 1.0  # 剩余 1 个 anchor 命中
    assert out["chunk_boundary_precision"]["value"] == pytest.approx(0.5)


# ---------- search_from 一对一 ----------

def test_overlap_markers_ab_then_b_batch53():
    # stream "ab c"：anchor "ab" after → gt=2（search_from 推到 2）；"b" 从 2 起找不到
    out = chunk_boundary_prf(_doc("ab", "c"),
                             {"chunk_boundary_anchors": [
                                 {"marker": "ab"}, {"marker": "b"}]})
    assert out["_missing_markers"]["value"] == ["b"]
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_overlap_markers_b_then_ab_batch53():
    # anchor "b" after → gt=1（search_from=1）；"ab" 从 1 起找不到
    out = chunk_boundary_prf(_doc("ab", "c"),
                             {"chunk_boundary_anchors": [
                                 {"marker": "b"}, {"marker": "ab"}]})
    assert out["_missing_markers"]["value"] == ["ab"]
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- 空 text chunk 现状 ----------

def test_none_text_chunk_yields_pred_at_zero_batch53():
    # norm ["", "ab", "cd"] → stream "ab cd"；空 chunk 产出 pred=0 并把 pos 推到 1，
    # 使 "ab"（在 0 处）find 不到 → 唯一 pred 是 0；anchor "ab" after → gt=3，d=3 命中
    out = chunk_boundary_prf(
        {"chunks": [{"text": None}, {"text": "ab"}, {"text": "cd"}]},
        {"chunk_boundary_anchors": [{"marker": "ab"}]})
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- marker 必须匹配规范化文本 ----------

def test_marker_must_match_normalized_batch53():
    # chunk "a  b" 规范化为 "a b"；双空格 marker 找不到
    out = chunk_boundary_prf(_doc("a  b", "cd"),
                             {"chunk_boundary_anchors": [{"marker": "a  b"}]})
    assert out["_missing_markers"]["value"] == ["a  b"]
    assert out["chunk_boundary_recall"]["reason"] == \
        "no_ground_truth_anchors_in_stream"


# ---------- _tolerance_chars 全路径 ----------

@pytest.mark.parametrize("doc,ann,tol", [
    (None, None, 99),
    (_doc("aa", "bb"), None, 0),
    (_doc("abc"), {"chunk_boundary_anchors": [{"marker": "b"}]}, 7),
    (_doc("aa", "bb"), {}, -1),
    (_doc("AAAA", "BBBB"), {"chunk_boundary_anchors": [{"marker": "AAAA"}]}, 12345),
])
def test_tolerance_recorded_all_paths_batch53(doc, ann, tol):
    out = chunk_boundary_prf(doc, ann, tolerance_chars=tol)
    assert out["_tolerance_chars"] == {"value": tol, "reason": None}


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(am)


def test_source_null_ratio_counts_batch53():
    src = _src()
    assert src.count("_null(") == 14
    assert src.count("_ratio(") == 5
    assert src.count('"_tolerance_chars"') == 5
    assert src.count("no_predicted_boundaries") == 4


def test_source_matching_lines_batch53():
    src = _src()
    assert src.count("search_from") == 3
    assert src.count("missing_markers") == 5
    assert src.count("used_pred") == 3
    assert src.count("used_gt") == 3
    assert "pairs.append((d, pi, gi))" in src
    assert "pairs.sort(key=lambda x: x[0])" in src
    assert "if d <= tolerance_chars:" in src


def test_source_normalize_import_batch53():
    assert "from app.chunkers.structural import normalize_text" in _src()


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(am))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _counts(func) -> dict:
    import collections
    return collections.Counter(type(n).__name__ for n in ast.walk(func))


def test_ast_figure_caption_structure_batch53():
    c = _counts(_func("figure_caption_prf"))
    assert (c["If"], c["For"], c["Return"], c["Subscript"]) == (0, 0, 1, 4)


def test_ast_chunk_boundary_structure_batch53():
    c = _counts(_func("chunk_boundary_prf"))
    assert (c["If"], c["For"], c["Return"], c["Continue"], c["Break"],
            c["ListComp"], c["AnnAssign"], c["Subscript"]) == \
        (15, 7, 5, 3, 1, 1, 5, 37)


# ---------- forbidden tokens 第一百九十一批 ----------

def test_source_no_eval_batch53():
    assert "eval(" not in _src()


def test_source_no_exec_batch53():
    assert "exec(" not in _src()


def test_source_no_compile_batch53():
    assert "compile(" not in _src()


def test_source_no_globals_batch53():
    assert "globals(" not in _src()


def test_source_no_locals_batch53():
    assert "locals(" not in _src()


def test_source_no_os_system_batch53():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch53():
    assert "subprocess" not in _src()


def test_source_no_popen_batch53():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch53():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch53():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch53():
    assert "socket" not in _src()


def test_source_no_requests_batch53():
    assert "requests" not in _src()


def test_source_no_urllib_batch53():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch53():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch53():
    assert "yield" not in _src()


def test_source_no_async_await_batch53():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch53():
    assert "open(" not in _src()
