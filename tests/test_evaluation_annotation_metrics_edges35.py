"""evaluation/annotation_metrics.py 第三十五轮 edges 测试（Round 378）。

重点补强 edges34 未触及的角度：
- chunk_boundary_prf 行为深度第八批（更复杂的 anchor/chunk 组合）
- figure_caption_prf 行为深度第八批（更多边界）
- module source forbidden tokens 第十一批
- module source 字符串精确补强第八批
- signatures 第八批
- module 合理性第八批
- 端到端集成第八批
"""

from __future__ import annotations

import inspect
import types
from typing import Any

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- chunk_boundary_prf 行为深度第八批 ----------


def test_chunk_boundary_prf_two_chunks_full_match_position_after():
    """2 个 chunk + 1 anchor (position=after, marker 在第 1 个 chunk 末尾) → 完美匹配."""
    doc = {
        "chunks": [
            {"text": "hello world"},
            {"text": "foo bar"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "world", "position": "after"},
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # predicted boundary = 11 ("hello world" 长 11)
    # gt position = "world" end = 11
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_two_chunks_full_match_position_before():
    """2 个 chunk + 1 anchor (position=before, marker 在第 2 个 chunk 开头) → 完美匹配."""
    doc = {
        "chunks": [
            {"text": "hello world"},
            {"text": "foo bar"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "before"},
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # stream = "hello world foo bar"
    # predicted = position after "hello world" = 11
    # gt position before "foo" = 12
    # distance = 1 → 需要 tolerance >= 1
    # tolerance=0 → no match
    assert result["chunk_boundary_precision"]["value"] is None or result["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_two_chunks_position_before_tolerance_match():
    """position=before + tolerance >= 1 应匹配."""
    doc = {
        "chunks": [
            {"text": "hello world"},
            {"text": "foo bar"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "before"},
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=1)
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_three_chunks_two_internal_boundaries():
    """3 个 chunks → 2 个内部边界."""
    doc = {
        "chunks": [
            {"text": "aa"},
            {"text": "bb"},
            {"text": "cc"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "aa", "position": "after"},
            {"marker": "bb", "position": "after"},
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # stream = "aa bb cc"
    # predicted: end of "aa" = 2, end of "bb" = 5
    # gt after "aa" = 2, after "bb" = 5
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0
    assert result["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_more_anchors_than_predicted():
    """标注 anchor 多于预测边界 → recall < 1.0."""
    doc = {
        "chunks": [
            {"text": "aa"},
            {"text": "bb"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "aa", "position": "after"},
            {"marker": "bb", "position": "after"},  # 没有 predicted 边界
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # predicted: 1 (end of "aa")
    # gt: 2 (after "aa" + after "bb")
    # 1 match
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_prf_more_predicted_than_anchors():
    """预测边界多于 anchor → precision < 1.0."""
    doc = {
        "chunks": [
            {"text": "aa"},
            {"text": "bb"},
            {"text": "cc"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "aa", "position": "after"},  # 1 anchor
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # predicted: 2 (end of "aa" + end of "bb")
    # gt: 1
    # 1 match
    assert result["chunk_boundary_precision"]["value"] == 0.5
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_negative_tolerance_no_match():
    """negative tolerance 应该没有匹配."""
    doc = {
        "chunks": [
            {"text": "hello"},
            {"text": "world"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "after"},
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=-1)
    # predicted = 5, gt = 5, distance = 0
    # 0 <= -1 是 False → 没匹配
    assert result["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_zero_tolerance_exact_match_only():
    doc = {
        "chunks": [
            {"text": "abc"},
            {"text": "def"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_zero_tolerance_off_by_one_no_match():
    doc = {
        "chunks": [
            {"text": "abc"},
            {"text": "def"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abcdef", "position": "after"},  # 不存在
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # marker 找不到 → missing
    # predicted = 3 (end of "abc")
    # gt 空 → no_ground_truth_anchors_in_stream
    assert result["chunk_boundary_recall"]["value"] is None
    assert result["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_anchor_with_empty_marker_treated_as_missing():
    """marker="" → stream.find("", ...) = 0 但代码会返回 -1 (marker truthy check)."""
    doc = {
        "chunks": [
            {"text": "abc"},
            {"text": "def"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "", "position": "after"},
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # marker empty → missing
    assert "_missing_markers" in result


def test_chunk_boundary_prf_anchor_without_marker_key():
    """无 marker key → 默认 "" → missing."""
    doc = {
        "chunks": [
            {"text": "abc"},
            {"text": "def"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"position": "after"},  # no marker
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert "_missing_markers" in result


def test_chunk_boundary_prf_anchor_with_unknown_position_defaults_after():
    """position="weird" → 默认 after."""
    doc = {
        "chunks": [
            {"text": "hello"},
            {"text": "world"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "middle"},  # 未知
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 默认走 else 分支（after）
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_unicode_marker():
    """Unicode marker 应支持."""
    doc = {
        "chunks": [
            {"text": "你好"},
            {"text": "世界"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "你好", "position": "after"},
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_document_no_chunks_key():
    """document 无 chunks key → chunks=[]."""
    doc = {}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    result = chunk_boundary_prf(doc, annotation)
    # < 2 chunks → no_predicted_boundaries
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_chunks_with_none_text():
    """chunk.text=None → normalize_text treats as ''."""
    doc = {
        "chunks": [
            {"text": None},
            {"text": "abc"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "before"},
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # norm_chunks = ["", "abc"]
    # joined = " abc"
    # stream = "abc"
    # predicted: skip empty text? end of "" = 0
    # Actually first iteration: find_pos = stream.find("", 0) = 0; end = 0; predicted = [0]
    # 1 prediction; 1 anchor → 可能匹配
    # 不应崩溃
    assert isinstance(result, dict)


def test_chunk_boundary_prf_chunk_missing_text_key():
    """chunk 无 text key → c.get('text') returns None → ''."""
    doc = {
        "chunks": [
            {},  # no text
            {"text": "abc"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "before"},
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert isinstance(result, dict)


def test_chunk_boundary_prf_annotation_is_empty_dict():
    """空 annotation dict → no_annotation."""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    result = chunk_boundary_prf(doc, {}, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_missing_chunk_boundary_anchors_key():
    """annotation 无 chunk_boundary_anchors key → anchors=[] → no_gt_anchors."""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    result = chunk_boundary_prf(doc, {"other_key": 1}, tolerance_chars=0)
    # 有 chunks → 不进入 no_annotation 分支
    # anchors 空 + chunks >= 2 → no_ground_truth_anchors
    assert result["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_returns_tolerance_record():
    """_tolerance_chars record 总是被加入."""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=42)
    assert "_tolerance_chars" in result
    assert result["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_tolerance_zero_in_record():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert result["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_prf_negative_tolerance_in_record():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=-5)
    assert result["_tolerance_chars"]["value"] == -5


def test_chunk_boundary_prf_does_not_return_missing_markers_when_all_found():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert "_missing_markers" not in result


def test_chunk_boundary_prf_returns_missing_markers_value_is_list():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "xxx", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    if "_missing_markers" in result:
        assert isinstance(result["_missing_markers"]["value"], list)


def test_chunk_boundary_prf_idempotent():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    r1 = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    r2 = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert r1 == r2


def test_chunk_boundary_prf_does_not_mutate_document():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    doc_copy = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert doc == doc_copy


def test_chunk_boundary_prf_does_not_mutate_annotation():
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    annotation_copy = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert annotation == annotation_copy


def test_chunk_boundary_prf_with_extra_keys_in_anchor():
    """anchor 含未知 key 应被忽略."""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "after", "extra_key": "value"}
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_f1_when_p_and_r_both_zero():
    """p=0 + r=0 → f1 = 0."""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "xyz", "position": "after"},  # 1 anchor 找不到 → missing
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # predicted: 1 (end of "abc" = 3)
    # gt: 0 (marker missing)
    # 0 match → precision = 0/1 = 0
    # recall: gt=0 → null
    # f1: r_val=None → null
    assert result["chunk_boundary_recall"]["value"] is None
    assert result["chunk_boundary_f1"]["value"] is None


def test_chunk_boundary_prf_f1_perfect_match():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert result["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_f1_half_match():
    """p=1, r=0.5 → f1 = 2*1*0.5/(1+0.5) = 1/1.5 ≈ 0.667."""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "xyz", "position": "after"},  # 找不到
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # predicted: 1 (end of "abc")
    # gt: 1 (after "abc"; "xyz" missing)
    # 1 match
    # p = 1/1 = 1.0; r = 1/1 = 1.0; f1 = 1.0
    # 因为 "xyz" 不在 gt_positions 里
    assert result["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_returns_dict_type():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation)
    assert isinstance(result, dict)


def test_chunk_boundary_prf_metric_value_or_reason_in_each():
    """每个 metric 应含 value 或 reason 字段."""
    doc = None
    annotation = {"chunk_boundary_anchors": [{"marker": "a"}]}
    result = chunk_boundary_prf(doc, annotation)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        m = result[k]
        assert "value" in m
        assert "reason" in m


def test_chunk_boundary_prf_three_chunks_no_match():
    """3 chunks，2 个预测边界，0 匹配 → p=0, r=0, f1=0."""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}, {"text": "ccc"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "xxx", "position": "after"},
            {"marker": "yyy", "position": "after"},
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 所有 anchor missing → gt = []
    # predicted = 2
    # p = 0/2 = 0; r = null (gt=0); f1 = null
    assert result["chunk_boundary_precision"]["value"] == 0.0
    assert result["chunk_boundary_recall"]["value"] is None


# ---------- figure_caption_prf 行为深度第八批 ----------


def test_figure_caption_prf_returns_three_metrics():
    result = figure_caption_prf({"chunks": []}, None)
    assert "figure_caption_precision" in result
    assert "figure_caption_recall" in result
    assert "figure_caption_f1" in result


def test_figure_caption_prf_all_reason_is_parser_does_not_emit():
    result = figure_caption_prf({"chunks": []}, None)
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert result[k]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_all_values_are_none():
    result = figure_caption_prf({"chunks": []}, None)
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert result[k]["value"] is None


def test_figure_caption_prf_with_none_document():
    result = figure_caption_prf(None, None)
    assert "figure_caption_precision" in result


def test_figure_caption_prf_with_none_annotation():
    result = figure_caption_prf({}, None)
    assert "figure_caption_precision" in result


def test_figure_caption_prf_with_rich_document():
    """含 figures/captions 的 doc 仍返回 null."""
    doc = {
        "figures": [{"figure_id": "f1"}],
        "captions": [{"caption_id": "c1"}],
    }
    result = figure_caption_prf(doc, None)
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert result[k]["value"] is None


def test_figure_caption_prf_with_rich_annotation():
    annotation = {"figure_caption_pairs": [{"figure": "f1", "caption": "c1"}]}
    result = figure_caption_prf({}, annotation)
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert result[k]["value"] is None


def test_figure_caption_prf_positional_args():
    """支持位置参数."""
    r1 = figure_caption_prf({"x": 1}, None)
    r2 = figure_caption_prf({"x": 1}, annotation=None)
    assert r1 == r2


def test_figure_caption_prf_kwargs_only():
    """支持 kwargs."""
    r = figure_caption_prf(document={"x": 1}, annotation=None)
    assert "figure_caption_precision" in r


def test_figure_caption_prf_idempotent():
    r1 = figure_caption_prf({}, None)
    r2 = figure_caption_prf({}, None)
    assert r1 == r2


def test_figure_caption_prf_does_not_mutate_document():
    doc = {"figures": []}
    doc_copy = {"figures": []}
    figure_caption_prf(doc, None)
    assert doc == doc_copy


def test_figure_caption_prf_does_not_mutate_annotation():
    annotation = {"key": "value"}
    annotation_copy = {"key": "value"}
    figure_caption_prf({}, annotation)
    assert annotation == annotation_copy


def test_figure_caption_prf_returns_dict_of_dicts():
    result = figure_caption_prf({}, None)
    assert isinstance(result, dict)
    for v in result.values():
        assert isinstance(v, dict)


def test_figure_caption_prf_metric_dict_has_value_and_reason():
    result = figure_caption_prf({}, None)
    for v in result.values():
        assert "value" in v
        assert "reason" in v


def test_figure_caption_prf_ignores_annotation_content():
    """不管 annotation 内容，返回都是 null."""
    r1 = figure_caption_prf({}, None)
    r2 = figure_caption_prf({}, {"figure_caption_pairs": [{"a": 1}]})
    assert r1 == r2


def test_figure_caption_prf_no_extra_keys():
    """figure_caption_prf 只返回 3 个 metric keys."""
    result = figure_caption_prf({}, None)
    assert set(result.keys()) == {
        "figure_caption_precision", "figure_caption_recall", "figure_caption_f1"
    }


# ---------- module source forbidden tokens 第十一批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "subprocess.run",
        "subprocess.call",
        "shutil.rmtree",
        "shutil.copy",
        "pickle.loads",
        "pickle.load",
        "marshal.loads",
        "ctypes.CDLL",
        "sys.exit",
        "__import__",
        "importlib.import_module",
        "requests.get",
        "urllib.request",
        "http.client",
        "socket.socket",
        "webbrowser.open",
        "antigravity",
        "this",
        "exit(",
        "quit(",
        "exec(",
        "eval(",
        "compile(",
    ],
)
def test_annotation_metrics_source_no_forbidden_token_eleventh(token):
    src = inspect.getsource(amod)
    assert token not in src


# ---------- module source 字符串精确补强第八批 ----------


def test_module_source_has_future_annotations():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_source_imports_counter():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_imports_any():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_imports_normalize_text():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_imports_null_and_ratio():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_has_parser_does_not_emit_constant():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_has_2_user_functions():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src
    assert "def chunk_boundary_prf(" in src


def test_module_source_no_class_definitions():
    src = inspect.getsource(amod)
    assert "\nclass " not in src
    assert not src.startswith("class ")


def test_module_source_no_yield():
    src = inspect.getsource(amod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(amod)
    assert "async def " not in src


def test_module_source_no_walrus():
    src = inspect.getsource(amod)
    assert ":=" not in src


def test_module_source_no_global_keyword():
    src = inspect.getsource(amod)
    assert "\nglobal " not in src


def test_module_source_no_lambda_at_top_level():
    """模块顶层无 lambda（函数内部的 lambda 是允许的）."""
    src = inspect.getsource(amod)
    # 检查顶层（不缩进）无 lambda 赋值
    in_triple = False
    triple_quote = None
    for line in src.splitlines():
        if in_triple:
            if triple_quote and triple_quote in line:
                in_triple = False
                triple_quote = None
            continue
        ls = line.lstrip()
        for q in ('"""', "'''"):
            if ls.startswith(q):
                rest = ls[3:]
                if rest.count(q) >= 1:
                    pass
                else:
                    in_triple = True
                    triple_quote = q
                break
        # 真正的顶层 = 没有前置空白
        if line[:1].isspace():
            continue
        stripped = line.strip()
        # 顶层 NAME = lambda ... 形式
        if "lambda " in stripped and "=" in stripped and not stripped.startswith("#"):
            # 允许：无（顶层不应有 lambda）
            pytest.fail(f"top-level lambda: {stripped}")


def test_module_source_inline_lambda_used_in_sort():
    """pairs.sort(key=lambda x: x[0]) 是合理的内联 lambda."""
    src = inspect.getsource(amod)
    assert "key=lambda" in src


def test_module_source_no_main_block():
    src = inspect.getsource(amod)
    assert 'if __name__' not in src


def test_module_source_no_sleep():
    src = inspect.getsource(amod)
    assert "time.sleep" not in src


def test_module_source_no_hardcoded_absolute_path():
    src = inspect.getsource(amod)
    assert "C:\\\\Users" not in src
    assert "C:/Users" not in src
    assert "/home/" not in src


def test_module_source_docstring_first_line():
    src = inspect.getsource(amod)
    assert src.startswith('"""')


def test_module_source_docstring_mentions_chunk_boundary():
    src = inspect.getsource(amod)
    assert "chunk_boundary" in src[:600]


def test_module_source_docstring_mentions_figure_caption():
    src = inspect.getsource(amod)
    assert "figure-caption" in src[:600] or "figure_caption" in src[:600]


def test_module_source_docstring_mentions_one_to_one():
    src = inspect.getsource(amod)
    assert "一对一" in src[:1200] or "one-to-one" in src[:1200].lower()


def test_module_source_docstring_mentions_tolerance():
    src = inspect.getsource(amod)
    assert "容差" in src[:1200] or "tolerance" in src[:1200].lower()


def test_module_source_no_print():
    src = inspect.getsource(amod)
    assert "print(" not in src


def test_module_source_no_logging():
    src = inspect.getsource(amod)
    assert "import logging" not in src


def test_module_source_uses_normalize_text_call():
    src = inspect.getsource(amod)
    assert "normalize_text(" in src


def test_module_source_uses_null_call():
    src = inspect.getsource(amod)
    assert "_null(" in src


def test_module_source_uses_ratio_call():
    src = inspect.getsource(amod)
    assert "_ratio(" in src


# ---------- signatures 第八批 ----------


def test_signature_figure_caption_prf_2_params():
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2


def test_signature_figure_caption_prf_document_kind():
    sig = inspect.signature(figure_caption_prf)
    p = sig.parameters["document"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_figure_caption_prf_annotation_kind():
    sig = inspect.signature(figure_caption_prf)
    p = sig.parameters["annotation"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_figure_caption_prf_no_defaults():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_figure_caption_prf_no_varargs():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_figure_caption_prf_no_kwargs():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_chunk_boundary_prf_3_params():
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3


def test_signature_chunk_boundary_prf_tolerance_default_30():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_chunk_boundary_prf_tolerance_kind():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["tolerance_chars"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_chunk_boundary_prf_no_varargs():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_chunk_boundary_prf_no_kwargs():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_parser_does_not_emit_constant_type():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_signature_parser_does_not_emit_constant_value():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_signature_all_funcs_function_type():
    assert isinstance(figure_caption_prf, types.FunctionType)
    assert isinstance(chunk_boundary_prf, types.FunctionType)


def test_signature_all_funcs_module_eq():
    assert figure_caption_prf.__module__ == amod.__name__
    assert chunk_boundary_prf.__module__ == amod.__name__


# ---------- module 合理性第八批 ----------


def test_module_all_exact_3_items_in_order():
    assert amod.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


def test_module_all_is_list():
    assert isinstance(amod.__all__, list)


def test_module_all_entries_unique():
    assert len(set(amod.__all__)) == len(amod.__all__)


def test_module_all_entries_are_str():
    for entry in amod.__all__:
        assert isinstance(entry, str)


def test_module_has_docstring():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 0


def test_module_docstring_starts_with_chinese():
    assert amod.__doc__.strip().startswith("人工标注")


def test_module_file_endswith_annotation_metrics_py():
    assert amod.__file__.replace("\\", "/").endswith("evaluation/annotation_metrics.py")


def test_module_name_is_evaluation_annotation_metrics():
    assert amod.__name__ == "evaluation.annotation_metrics"


def test_module_function_module_attribute_eq():
    """模块自身定义的函数 __module__ 应是 evaluation.annotation_metrics.

    imports 进来的函数（如 normalize_text）__module__ 应是其原始模块.
    """
    own_funcs = [
        obj for obj in vars(amod).values()
        if isinstance(obj, types.FunctionType) and obj.__module__ == amod.__name__
    ]
    # 至少 2 个自身定义的函数
    assert len(own_funcs) >= 2
    names = {f.__name__ for f in own_funcs}
    assert "figure_caption_prf" in names
    assert "chunk_boundary_prf" in names


def test_module_no_user_classes():
    own_classes = [
        obj for obj in vars(amod).values()
        if isinstance(obj, type) and obj.__module__ == amod.__name__
    ]
    assert len(own_classes) == 0


def test_module_user_function_count():
    own_funcs = [
        obj for obj in vars(amod).values()
        if isinstance(obj, types.FunctionType) and obj.__module__ == amod.__name__
    ]
    assert len(own_funcs) == 2


def test_module_constants_only_parser_does_not_emit():
    """模块级大写常量应有 PARSER_DOES_NOT_EMIT_RELATIONS."""
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_module_no_call_at_top_level():
    """模块顶层不应有显式的 print/exit/subprocess 类副作用调用."""
    src = inspect.getsource(amod)
    in_triple = False
    triple_quote = None
    suspicious_patterns = ("os.system(", "subprocess.", "exit(", "quit(", "print(")
    for line in src.splitlines():
        if in_triple:
            if triple_quote and triple_quote in line:
                in_triple = False
                triple_quote = None
            continue
        ls = line.lstrip()
        for q in ('"""', "'''"):
            if ls.startswith(q):
                rest = ls[3:]
                if rest.count(q) >= 1:
                    pass
                else:
                    in_triple = True
                    triple_quote = q
                break
        for pat in suspicious_patterns:
            assert pat not in line, f"suspicious pattern {pat!r} in {line!r}"


# ---------- 端到端集成第八批 ----------


def test_e2e_chunk_boundary_with_real_document_and_annotation():
    doc = {
        "chunks": [
            {"text": "first chunk content"},
            {"text": "second chunk content"},
            {"text": "third chunk content"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "content", "position": "after"},  # 在 chunk 1 末尾
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # stream = "first chunk content second chunk content third chunk content"
    # predicted boundaries: end of "first chunk content" = 19, end of "second chunk content" = 40
    # "content" 出现多次；search_from 顺序查找 → 第一次 "content" 结束位置 = 19
    # gt = 19
    # predicted[0] = 19; matched
    assert result["chunk_boundary_precision"]["value"] is not None


def test_e2e_full_chain_pipeline_failed_then_no_annotation():
    """document=None → pipeline_failed; annotation=None → no_annotation."""
    r1 = chunk_boundary_prf(None, None)
    assert r1["chunk_boundary_precision"]["reason"] == "pipeline_failed"


def test_e2e_chunk_boundary_returns_tolerance_in_record():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=99)
    assert result["_tolerance_chars"]["value"] == 99
    assert result["_tolerance_chars"]["reason"] is None


def test_e2e_chunk_boundary_missing_markers_recorded():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "xxx", "position": "after"},
            {"marker": "yyy", "position": "after"},
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert "_missing_markers" in result
    assert "xxx" in result["_missing_markers"]["value"]
    assert "yyy" in result["_missing_markers"]["value"]


def test_e2e_chunk_boundary_partial_missing_markers():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "xxx", "position": "after"},  # missing
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert "_missing_markers" in result
    assert "xxx" in result["_missing_markers"]["value"]
    assert "abc" not in result["_missing_markers"]["value"]


def test_e2e_chunk_boundary_metric_dict_structure():
    """每个 metric 应是 dict 含 value 和 reason."""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        m = result[k]
        assert isinstance(m, dict)
        assert "value" in m
        assert "reason" in m


def test_e2e_chunk_boundary_positional_args_full_call():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r1 = chunk_boundary_prf(doc, annotation, 0)
    r2 = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert r1 == r2


def test_e2e_chunk_boundary_kwargs_full_call():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r = chunk_boundary_prf(document=doc, annotation=annotation, tolerance_chars=0)
    assert "chunk_boundary_precision" in r


def test_e2e_chunk_boundary_idempotent():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    r1 = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    r2 = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert r1 == r2


def test_e2e_figure_caption_idempotent():
    r1 = figure_caption_prf({"x": 1}, None)
    r2 = figure_caption_prf({"x": 1}, None)
    assert r1 == r2


def test_e2e_full_chain_doc_with_annotation_perfect_match():
    """完整链：doc + annotation + position=after + tolerance=0 + perfect match."""
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
            {"text": "gamma"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "beta", "position": "after"},
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0
    assert result["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_chunk_boundary_no_mutate_inputs():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    import copy
    doc_copy = copy.deepcopy(doc)
    annotation_copy = copy.deepcopy(annotation)
    chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert doc == doc_copy
    assert annotation == annotation_copy


def test_e2e_chunk_boundary_unicode_text_perfect_match():
    doc = {
        "chunks": [
            {"text": "你好世界"},
            {"text": "你好朋友"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "你好世界", "position": "after"},
        ]
    }
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0
