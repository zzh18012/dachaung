"""evaluation/annotation_metrics.py 第二十九轮 edges 测试（Round 332）。

重点补强 edges27 未触及的角度：
- figure_caption_prf 输出 dict 结构精确补强（all 3 keys / same reason / each value is dict / value=None）
- chunk_boundary_prf 算法精确补强（find_pos<0 fallback / empty marker / position missing defaults / 多 anchor 同 marker / extra keys ignored）
- chunk_boundary_prf 输出结构精确补强（_tolerance_chars value type / _missing_markers list type / normal 输出 keys 全）
- module source forbidden tokens 第三批（~75 stdlib）
- module source 字符串精确补强（control flow / method calls / numeric constants）
- signatures 精确补强（return types / param types）
- 模块整体合理性
- 端到端集成补强（more scenarios）
"""

from __future__ import annotations

import inspect
import types
from collections import Counter

import pytest

from evaluation import annotation_metrics as am_mod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- figure_caption_prf 输出 dict 结构精确补强 ----------


def test_figure_caption_returns_3_keys_only():
    out = figure_caption_prf({"chunks": []}, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_all_3_keys_have_same_reason():
    out = figure_caption_prf({"chunks": []}, None)
    reasons = [v["reason"] for v in out.values()]
    assert all(r == PARSER_DOES_NOT_EMIT_RELATIONS for r in reasons)


def test_figure_caption_all_3_values_are_none():
    out = figure_caption_prf({"chunks": []}, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_with_none_document():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_with_none_annotation():
    out = figure_caption_prf({"chunks": []}, None)
    assert all(v["value"] is None for v in out.values())


def test_figure_caption_with_realistic_annotation_still_returns_null():
    """即使 annotation 含 caption/figure 关系数据，仍然返回 null（parser 不输出 relation）。"""
    out = figure_caption_prf(
        {"elements": [{"type": "figure", "element_id": "f1"}]},
        {"figure_caption_pairs": [{"figure_id": "f1", "caption_id": "c1"}]},
    )
    assert all(v["value"] is None for v in out.values())


def test_figure_caption_ignores_annotation_completely():
    """figure_caption_prf 不读 annotation 内容（直接固定 null）。"""
    out1 = figure_caption_prf({"chunks": []}, None)
    out2 = figure_caption_prf({"chunks": []}, {"foo": "bar"})
    assert out1 == out2


# ---------- chunk_boundary_prf 算法精确补强 ----------


def test_chunk_boundary_with_empty_marker_added_to_missing():
    """marker 为空字符串 → find 返回 -1 → 加入 missing_markers。"""
    doc = {
        "chunks": [
            {"text": "alpha beta gamma"},
            {"text": "delta"},
        ],
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "", "position": "after"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_with_marker_not_in_stream_added_to_missing():
    """marker 不在 stream 中 → 加入 missing_markers。"""
    doc = {
        "chunks": [
            {"text": "alpha beta"},
            {"text": "gamma"},
        ],
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "nonexistent"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert "nonexistent" in out["_missing_markers"]["value"]


def test_chunk_boundary_position_default_after_when_key_missing():
    """anchor 缺 position key → 默认 "after"。"""
    doc = {
        "chunks": [
            {"text": "alpha beta"},
            {"text": "gamma"},
        ],
    }
    # marker="beta" 后位置 = beta 结束位置
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta"},  # no position key
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # stream = "alpha beta gamma"
    # beta 结束位置 = 10
    # 第 1 chunk 末尾位置 = 10
    # distance = 0 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_position_unknown_value_treated_as_after():
    """position 不是 "before" 也不是 "after"（默认走 else 分支 = after）。"""
    doc = {
        "chunks": [
            {"text": "alpha beta"},
            {"text": "gamma"},
        ],
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "weird"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 与 default after 同行为
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_extra_keys_in_anchor_ignored():
    """anchor 含未知 key → 不影响结果。"""
    doc = {
        "chunks": [
            {"text": "alpha beta"},
            {"text": "gamma"},
        ],
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after", "extra_key": "ignored"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_extra_keys_in_annotation_ignored():
    """annotation 含未知 top-level key → 不影响结果。"""
    doc = {
        "chunks": [
            {"text": "alpha beta"},
            {"text": "gamma"},
        ],
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta"},
        ],
        "extra_section": {"foo": "bar"},
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_multiple_anchors_same_marker_in_different_positions():
    """两个相同 marker，position 一个 before 一个 after。"""
    doc = {
        "chunks": [
            {"text": "alpha marker beta"},
            {"text": "gamma marker delta"},
        ],
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "marker", "position": "before"},
            {"marker": "marker", "position": "after"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=20)
    # stream = "alpha marker beta gamma marker delta"
    # 第 1 chunk end = 18
    # marker1 (before) find_from=0 → 位置 6
    # marker2 (after) find_from=6+6=12 → 位置 24+6=30
    # predicted=[18], gt=[6, 30]
    # 算法：贪心按距离排序
    # |18-6|=12, |18-30|=12 → 都在 tolerance=20 内
    # tie → 取第 1 个 → matched=1
    # precision = 1/1 = 1.0
    # recall = 1/2 = 0.5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_tolerance_chars_records_actual_value():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_tolerance_chars_default_30():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["_tolerance_chars"]["value"] == 30


# ---------- chunk_boundary_prf 输出结构精确补强 ----------


def test_chunk_boundary_normal_output_has_4_keys():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    expected_keys = {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }
    assert set(out.keys()) == expected_keys


def test_chunk_boundary_normal_output_5_keys_with_missing_markers():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "nonexistent"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    expected_keys = {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
        "_missing_markers",
    }
    assert set(out.keys()) == expected_keys


def test_chunk_boundary_each_metric_value_is_dict_with_2_keys():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    for k, v in out.items():
        assert isinstance(v, dict)
        assert set(v.keys()) == {"value", "reason"}


def test_chunk_boundary_tolerance_chars_value_can_be_0():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_tolerance_chars_value_can_be_negative():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=-1)
    assert out["_tolerance_chars"]["value"] == -1


def test_chunk_boundary_missing_markers_value_is_list():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert isinstance(out["_missing_markers"]["value"], list)


# ---------- module source forbidden tokens 第三批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "base64", "binascii", "bisect", "calendar", "concurrent",
        "contextlib", "copyreg", "csv", "fnmatch", "functools",
        "getopt", "getpass", "gettext", "heapq", "imaplib",
        "importlib", "ipaddress", "locale", "lzma", "mailbox",
        "mimetypes", "mmap", "multiprocessing", "netrc", "ntpath",
        "numbers", "operator", "optparse", "platform",
        "poplib", "posixpath", "profile", "pstats", "py_compile",
        "quopri", "reprlib", "runpy", "sched", "select",
        "shelve", "shlex", "signal", "site", "smtplib",
        "sndhdr", "socketserver", "sqlite3", "ssl", "subprocess",
        "sunau", "symtable", "tabnanny", "telnetlib", "termios",
        "timeit", "tkinter", "token", "tokenize", "trace",
        "tty", "turtle", "unittest", "urllib",
        "uu", "webbrowser", "xdrlib", "zipapp", "zipfile",
        "zipimport", "argparse", "array", "ast", "atexit",
        "builtins", "json",
    ],
)
def test_module_source_forbidden_tokens_third_batch(token):
    """这些 stdlib 模块不应出现在 annotation_metrics.py（仅 Counter/typing/normalize_text/_null/_ratio）。"""
    src = inspect.getsource(am_mod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_from_future():
    src = inspect.getsource(am_mod)
    assert "from __future__ import annotations" in src


def test_module_source_has_counter_import():
    src = inspect.getsource(am_mod)
    assert "from collections import Counter" in src


def test_module_source_has_typing_any():
    src = inspect.getsource(am_mod)
    assert "from typing import Any" in src


def test_module_source_has_normalize_text_import():
    src = inspect.getsource(am_mod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_has_metrics_helpers_import():
    src = inspect.getsource(am_mod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_has_parser_does_not_emit_constant():
    src = inspect.getsource(am_mod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_docstring_mentions_caption():
    src = inspect.getsource(am_mod)
    assert "caption" in src.lower()


def test_module_source_docstring_mentions_relation():
    src = inspect.getsource(am_mod)
    assert "relation" in src.lower()


def test_module_source_docstring_mentions_marker():
    src = inspect.getsource(am_mod)
    assert "marker" in src.lower()


def test_module_source_docstring_mentions_tolerance():
    src = inspect.getsource(am_mod)
    assert "tolerance" in src.lower()


def test_module_source_docstring_mentions_one_to_one():
    src = inspect.getsource(am_mod)
    assert "一对一" in src or "one-to-one" in src.lower()


def test_module_source_docstring_mentions_greedy():
    src = inspect.getsource(am_mod)
    assert "贪心" in src or "greedy" in src.lower()


def test_module_source_has_normalize_text_call():
    src = inspect.getsource(am_mod)
    assert "normalize_text(" in src


def test_module_source_has_join_with_space():
    src = inspect.getsource(am_mod)
    assert '" ".join(norm_chunks)' in src


def test_module_source_has_stream_normalize_after_join():
    src = inspect.getsource(am_mod)
    assert "stream = normalize_text(joined_raw)" in src


def test_module_source_has_predicted_list_init():
    src = inspect.getsource(am_mod)
    assert "predicted: list[int] = []" in src


def test_module_source_has_for_loop_over_norm_chunks():
    src = inspect.getsource(am_mod)
    assert "for i, txt in enumerate(norm_chunks):" in src


def test_module_source_has_last_chunk_break():
    src = inspect.getsource(am_mod)
    assert "if i == len(norm_chunks) - 1:" in src


def test_module_source_has_find_in_stream():
    src = inspect.getsource(am_mod)
    assert "stream.find(txt, pos)" in src


def test_module_source_has_find_pos_negative_check():
    src = inspect.getsource(am_mod)
    assert "if find_pos < 0:" in src


def test_module_source_has_pos_advance_when_not_found():
    src = inspect.getsource(am_mod)
    assert "pos += len(txt) + 1" in src


def test_module_source_has_search_from_init():
    src = inspect.getsource(am_mod)
    assert "search_from = 0" in src


def test_module_source_has_anchor_loop():
    src = inspect.getsource(am_mod)
    assert "for a in anchors:" in src


def test_module_source_has_marker_default_empty():
    src = inspect.getsource(am_mod)
    assert 'a.get("marker", "")' in src


def test_module_source_has_position_default_after():
    src = inspect.getsource(am_mod)
    assert 'a.get("position", "after")' in src


def test_module_source_has_position_before_branch():
    src = inspect.getsource(am_mod)
    assert 'if position == "before":' in src


def test_module_source_has_pairs_init():
    src = inspect.getsource(am_mod)
    assert "pairs: list[tuple[int, int, int]] = []" in src


def test_module_source_has_used_pred_used_gt_set():
    src = inspect.getsource(am_mod)
    assert "used_pred = set()" in src
    assert "used_gt = set()" in src


def test_module_source_has_distance_calc_with_abs():
    src = inspect.getsource(am_mod)
    assert "d = abs(pv - gv)" in src


def test_module_source_has_tolerance_compare():
    src = inspect.getsource(am_mod)
    assert "if d <= tolerance_chars:" in src


def test_module_source_has_pairs_sort():
    src = inspect.getsource(am_mod)
    assert "pairs.sort(key=lambda x: x[0])" in src


def test_module_source_has_matched_init():
    src = inspect.getsource(am_mod)
    assert "matched = 0" in src


def test_module_source_has_used_check_in_loop():
    src = inspect.getsource(am_mod)
    assert "if pi in used_pred or gi in used_gt:" in src


def test_module_source_has_no_main_block():
    src = inspect.getsource(am_mod)
    assert 'if __name__' not in src


def test_module_source_has_no_class():
    src = inspect.getsource(am_mod)
    assert "\nclass " not in src
    assert not src.startswith("class ")


def test_module_source_has_no_yield():
    src = inspect.getsource(am_mod)
    assert "yield" not in src


def test_module_source_has_no_async():
    src = inspect.getsource(am_mod)
    assert "async " not in src


def test_module_source_has_no_decorators():
    src = inspect.getsource(am_mod)
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("@"):
            assert False, f"unexpected decorator: {stripped}"


def test_module_source_has_no_lambda():
    """lambda 只在 sort key 里允许（不算禁止）。"""
    src = inspect.getsource(am_mod)
    # 唯一允许的 lambda：sort key
    # 检查所有 lambda 出现，必须是 sort key 那个
    lines_with_lambda = [line for line in src.splitlines() if "lambda " in line]
    for line in lines_with_lambda:
        assert "x[0]" in line, f"unexpected lambda: {line}"


# ---------- signatures 精确补强 ----------


def test_figure_caption_prf_signature_2_params():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters) == ["document", "annotation"]


def test_figure_caption_prf_param_kinds_positional_or_keyword():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_figure_caption_prf_no_default_for_document_annotation():
    sig = inspect.signature(figure_caption_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty
    assert sig.parameters["annotation"].default is inspect.Parameter.empty


def test_figure_caption_prf_return_annotation_dict():
    sig = inspect.signature(figure_caption_prf)
    assert "dict" in str(sig.return_annotation)


def test_chunk_boundary_prf_signature_3_params():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters) == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_default_tolerance_30():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_no_default_for_document_annotation():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty
    assert sig.parameters["annotation"].default is inspect.Parameter.empty


def test_chunk_boundary_prf_tolerance_annotation_int():
    sig = inspect.signature(chunk_boundary_prf)
    assert "int" in str(sig.parameters["tolerance_chars"].annotation)


def test_chunk_boundary_prf_return_annotation_dict():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict" in str(sig.return_annotation)


def test_chunk_boundary_prf_param_kinds():
    sig = inspect.signature(chunk_boundary_prf)
    kinds = [p.kind for p in sig.parameters.values()]
    assert all(k == inspect.Parameter.POSITIONAL_OR_KEYWORD for k in kinds)


def test_no_varargs_varkw_in_functions():
    for fn in (figure_caption_prf, chunk_boundary_prf):
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_POSITIONAL
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- 模块整体合理性 ----------


def test_namespace_figure_caption_prf():
    assert hasattr(am_mod, "figure_caption_prf")
    assert isinstance(getattr(am_mod, "figure_caption_prf"), types.FunctionType)


def test_namespace_chunk_boundary_prf():
    assert hasattr(am_mod, "chunk_boundary_prf")
    assert isinstance(getattr(am_mod, "chunk_boundary_prf"), types.FunctionType)


def test_namespace_parser_does_not_emit_constant():
    assert hasattr(am_mod, "PARSER_DOES_NOT_EMIT_RELATIONS")
    assert isinstance(getattr(am_mod, "PARSER_DOES_NOT_EMIT_RELATIONS"), str)


def test_namespace_parser_does_not_emit_value():
    assert am_mod.PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_module_all_3_entries_exact():
    assert am_mod.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


def test_module_all_is_list():
    assert isinstance(am_mod.__all__, list)


def test_module_all_entries_str():
    for entry in am_mod.__all__:
        assert isinstance(entry, str)


def test_module_has_2_module_level_functions():
    public_funcs = [
        n for n, v in vars(am_mod).items()
        if not n.startswith("_") and isinstance(v, types.FunctionType)
        and getattr(v, "__module__", "") == am_mod.__name__
    ]
    assert sorted(public_funcs) == ["chunk_boundary_prf", "figure_caption_prf"]


def test_module_has_1_module_level_constant():
    public_consts = [
        n for n, v in vars(am_mod).items()
        if not n.startswith("_") and not callable(v) and not isinstance(v, types.ModuleType)
    ]
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in public_consts


def test_module_no_class():
    classes = [
        n for n, v in vars(am_mod).items()
        if not n.startswith("_") and isinstance(v, type)
        and getattr(v, "__module__", "") == am_mod.__name__
    ]
    assert classes == []


def test_module_no_main_block():
    src = inspect.getsource(am_mod)
    assert 'if __name__' not in src


# ---------- 端到端集成补强 ----------


def test_e2e_perfect_match_returns_proper_metric_dict():
    doc = {
        "chunks": [
            {"text": "alpha marker"},
            {"text": "beta"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "marker"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_with_whitespace_normalization_in_stream():
    """chunk 内多余空白被 normalize 后参与匹配。"""
    doc = {
        "chunks": [
            {"text": "alpha   marker"},  # 多空格
            {"text": "beta"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "marker"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # normalize 后 "alpha marker beta"，marker 后位置匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_with_punctuation_in_marker():
    doc = {
        "chunks": [
            {"text": "alpha, beta"},
            {"text": "gamma"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": ", beta"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # stream = "alpha, beta gamma"
    # ", beta" 后位置 = 9
    # predicted = [9]
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_3_chunks_2_internal_boundaries():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
            {"text": "gamma"},
        ],
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha"},
            {"marker": "beta"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # stream = "alpha beta gamma"
    # predicted = [5, 10] (alpha end, beta end)
    # gt = [5 (alpha end), 10 (beta end)]
    # 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_no_chunks_returns_no_predicted():
    doc = {"chunks": []}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_e2e_one_chunk_returns_no_predicted():
    doc = {"chunks": [{"text": "alpha"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 1 chunk < 2 → no_predicted_boundaries
    # 但 anchors 非空 → recall = _ratio(0.0) = 0
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_e2e_2_chunks_no_anchors_returns_no_ground_truth():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
        ],
    }
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_f1"]["reason"] == "no_ground_truth_anchors"


def test_e2e_chunks_missing_text_key_uses_empty_string():
    """chunk 没有 text key → 用 "" 代替。"""
    doc = {
        "chunks": [
            {"no_text": "x"},
            {"text": "beta"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "beta"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # norm_chunks = ["", "beta"]
    # joined_raw = " beta" → stream = "beta"
    # predicted: 第 1 chunk text="" → find returns 0 → end = 0 → predicted = [0]
    # 第 2 chunk is last → break
    # marker "beta" → find_from=0 → 位置 0 → after → 4
    # |0 - 4| = 4 ≤ 10 → matched
    # precision = 1/1 = 1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_deterministic_across_calls():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha"}]}
    out1 = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    out2 = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out1 == out2


def test_e2e_figure_caption_returns_proper_metric_dict():
    out = figure_caption_prf({"chunks": []}, None)
    assert out["figure_caption_precision"]["reason"] == "parser_does_not_emit_relations"
    assert out["figure_caption_recall"]["reason"] == "parser_does_not_emit_relations"
    assert out["figure_caption_f1"]["reason"] == "parser_does_not_emit_relations"


def test_e2e_chunk_boundary_with_unicode_marker():
    doc = {
        "chunks": [
            {"text": "标题"},
            {"text": "正文"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "标题"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # stream = "标题 正文"
    # predicted = [2]  (标题 end)
    # marker "标题" → find_from=0 → 0 → after → 2
    # |2-2| = 0 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_with_many_chunks_and_few_markers():
    """5 chunks + 1 marker → precision 低，recall 高。"""
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
            {"text": "gamma"},
            {"text": "delta"},
            {"text": "epsilon"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # predicted = [5, 10, 16, 22]
    # gt = [5]
    # 1 个完美匹配 → matched=1
    # precision = 1/4 = 0.25
    # recall = 1/1 = 1.0
    assert out["chunk_boundary_precision"]["value"] == 0.25
    assert out["chunk_boundary_recall"]["value"] == 1.0
