# -*- coding: utf-8 -*-
"""Stage 9 批次 26：R-E 输入对等性对照组（B1-systext）测试。

外部评审 §132 R-E：B1/B2 基线吃 gold fold-ws 流，系统吃自身解析
文本——输入不对等。对照组 = B1 定长算法 × 系统解析文本，单列报告
不入选优；与 B1@ 同 N 的差值即文本源对等性损失，定位失败
（unmatched/uncovered）为量化披露不静默。

纯合成夹具；run_system_parsed_text 仅测失败分支（真实解析接线由
G⑦ 合成文档测试覆盖，G⑥ 前不触真实语料）。
"""
import pytest

from stage9.baseline_eval import (
    BASELINES,
    SYSTEM_TEXT_CONTROL,
    evaluate_doc,
    evaluate_doc_system_text,
    macro_average,
    select_baselines,
)
from stage9.normalize import fold_ws
from stage9.system_eval import run_system_parsed_text

STREAM = ("Alpha beta gamma. Delta epsilon zeta. "
          "Eta theta iota. Kappa lambda mu.")
SPANS = [(0, 17), (17, 36), (36, 52), (52, 70)]
N_GRID = (20, 30)


def _ann(doc_id="d1"):
    units = [{"unit_id": "u%04d" % i, "kind": "sentence", "page": 1,
              "char_span": list(sp), "gold_segment_id":
              "g01" if i < 2 else "g02"}
             for i, sp in enumerate(SPANS)]
    units.append({"unit_id": "u9999", "kind": "nontext", "page": 1,
                  "char_span": None, "nontext_ref": "img:figure1",
                  "gold_segment_id": "g02"})
    return {"doc_id": doc_id, "stream": STREAM, "units": units}


def test_parity_perfect_control_equals_b1():
    # 系统文本 == gold 流：同算法同输入 → 逐 N ARI 全等（对照组锚定）
    ann = _ann()
    b1 = evaluate_doc(ann, n_grid=N_GRID, baselines=("B1",))
    ctrl = evaluate_doc_system_text(ann, STREAM, n_grid=N_GRID)
    assert ctrl["na_reason"] is None
    assert ctrl["parsed_chars"] == len(fold_ws(STREAM))
    for n in N_GRID:
        assert ctrl["results"][SYSTEM_TEXT_CONTROL][n]["ari"] == \
            b1["results"]["B1"][n]["ari"]


def test_dropped_tail_disclosed_as_uncovered():
    # 解析丢尾句：可定位部分照常投影，尾部 unit uncovered 披露
    ann = _ann()
    truncated = STREAM[:SPANS[2][1]]  # 丢第 4 句
    ctrl = evaluate_doc_system_text(ann, truncated, n_grid=N_GRID)
    for n in N_GRID:
        m = ctrl["results"][SYSTEM_TEXT_CONTROL][n]
        assert m["uncovered_units"] >= 1
        assert m["na_reason"] is None


def test_garbled_insert_disclosed_as_unmatched():
    # 解析插入 gold 流中不存在的串：含该串的 chunk 定位失败计
    # unmatched，不静默吞掉
    ann = _ann()
    garbled = STREAM[:20] + " ZZZQQQXXX " + STREAM[20:]
    ctrl = evaluate_doc_system_text(ann, garbled, n_grid=N_GRID)
    assert any(ctrl["results"][SYSTEM_TEXT_CONTROL][n]
               ["unmatched_chunks"] >= 1 for n in N_GRID)


def test_empty_parsed_text_na():
    ctrl = evaluate_doc_system_text(_ann(), "   ", n_grid=N_GRID)
    assert ctrl["na_reason"] == "empty_parsed_text"
    for n in N_GRID:
        assert ctrl["results"][SYSTEM_TEXT_CONTROL][n]["ari"] is None
        assert ctrl["results"][SYSTEM_TEXT_CONTROL][n]["na_reason"] == \
            "empty_parsed_text"


def test_parse_failed_reason_passthrough():
    ctrl = evaluate_doc_system_text(_ann(), None, n_grid=N_GRID,
                                    na_reason="parse_failed:"
                                              "file_not_found")
    assert ctrl["na_reason"] == "parse_failed:file_not_found"
    assert ctrl["parsed_chars"] == 0
    assert all(ctrl["results"][SYSTEM_TEXT_CONTROL][n]["ari"] is None
               for n in N_GRID)


def test_control_not_in_selection_baselines():
    # 单列报告：对照组永不进入基线选优（评审"report separately"）
    assert SYSTEM_TEXT_CONTROL not in BASELINES
    ann = _ann()
    reports = [evaluate_doc(ann, n_grid=N_GRID)]
    macro, selection = select_baselines(reports, n_grid=N_GRID)
    assert SYSTEM_TEXT_CONTROL not in macro
    assert SYSTEM_TEXT_CONTROL not in selection


def test_control_macro_excludes_na_docs():
    ok = evaluate_doc_system_text(_ann(), STREAM, n_grid=N_GRID)
    na = evaluate_doc_system_text(_ann("d2"), None, n_grid=N_GRID,
                                  na_reason="empty_result")
    m = macro_average([ok, na], SYSTEM_TEXT_CONTROL, 20)
    assert m is not None  # N/A 文档剔除但 ok 文档保住 macro
    na_all = macro_average(
        [evaluate_doc_system_text(_ann("d3"), None, n_grid=N_GRID,
                                  na_reason="empty_result")],
        SYSTEM_TEXT_CONTROL, 20)
    assert na_all is None  # 全 N/A → None 不虚构


def test_run_system_parsed_text_missing_file():
    text, reason = run_system_parsed_text(
        "Z:/no/such/file.pdf")
    assert text is None
    assert reason == "parse_failed:file_not_found"
