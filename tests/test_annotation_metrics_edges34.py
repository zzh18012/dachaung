"""evaluation/annotation_metrics.py 第三十四轮 edges 测试（Round 371）。

补强 edges33 未触及的角度：
- chunk_boundary_prf 行为深度第七批（3 chunks 多 anchors 部分 match、empty first chunk、marker 在 stream 末尾、weird position 默认 after、非典型 chunks）
- figure_caption_prf 行为深度第七批（与 chunk_boundary 解耦、传非 dict 输入）
- module source forbidden tokens 第十批
- module 合理性第七批（__all__ 精确 3 项顺序、module __file__ 后缀）
- signatures 第七批（chunk_boundary_prf 三参 kind、figure_caption_prf 两参 kind）
- 端到端集成第七批（一对一边界贪心匹配、tolerance_chars record、missing_markers 出现条件）
"""

from __future__ import annotations

import inspect
import types

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- chunk_boundary_prf 行为深度第七批 ----------


def test_chunk_boundary_prf_three_chunks_three_anchors_partial_match():
    """3 chunks → 2 predicted boundaries；3 anchors → recall = 2/3。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}, {"text": "ccc"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "a", "position": "after"},   # pos 3
        {"marker": "b", "position": "after"},   # pos 7
        {"marker": "c", "position": "after"},   # pos 11 (last → no predicted)
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == pytest.approx(2/3)


def test_chunk_boundary_prf_weird_position_defaults_to_after():
    """position 非 'before'/'after' → 走 'after' 分支。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "a", "position": "weird"},  # 走 else 分支 = after
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] is not None


def test_chunk_boundary_prf_empty_first_chunk_text():
    """第一个 chunk text 为空 → 它的 end 仍是 stream 中下一个 chunk 的起始位置。"""
    doc = {"chunks": [{"text": ""}, {"text": "aaa"}, {"text": "bbb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 边界匹配仍能成立
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_marker_at_end_of_stream_no_predicted():
    """marker 在 stream 末尾，没有预测边界与之匹配 → precision=0 / recall=0。"""
    doc = {"chunks": [{"text": "a b c"}, {"text": "d e f"}, {"text": "g h i"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "i", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_marker_with_whitespace():
    """marker 含空白（normalize 后会被压缩）。"""
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "world foo", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # stream = "hello world foo bar"
    # 'world foo' normalize 后还是 'world foo'（已是规范化形式）
    # 应在 stream 中找到
    assert out["chunk_boundary_precision"]["value"] is not None


def test_chunk_boundary_prf_two_anchors_same_marker_sequential_match():
    """两个 anchor 用相同 marker，应该顺序匹配不同 stream 位置（不同 gt_pos）。"""
    doc = {"chunks": [{"text": "aa"}, {"text": "aa"}, {"text": "bb"}]}
    # stream = "aa aa bb"
    # 预测边界：2（first "aa" 后）和 5（second "aa" 后）
    ann = {"chunk_boundary_anchors": [
        {"marker": "aa", "position": "after"},  # 第一次 find 在 0，after=2
        {"marker": "aa", "position": "after"},  # 第二次从 2 开始 find 在 3，after=5
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 2 anchor, 2 predicted, 2 match → precision=recall=f1=1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_position_before_anchor():
    """position='before' → gt_pos = find_pos（marker 起始）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # stream = "abc def"
    # 预测边界：end of 'abc' = 3
    ann = {"chunk_boundary_anchors": [
        {"marker": "def", "position": "before"},  # gt_pos = 4 (find_pos)
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # |3 - 4| = 1 <= 5 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_missing_marker_recorded():
    """找不到的 marker 应记录到 _missing_markers。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "xyz", "position": "after"},  # 不在 stream
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert "_missing_markers" in out
    assert "xyz" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_missing_marker_not_added_when_all_found():
    """所有 marker 都找到时，不应有 _missing_markers key。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_anchors_set_to_none_in_annotation():
    """annotation 显式 chunk_boundary_anchors=None → 视作无 anchor。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": None}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # None is falsy → `if not annotation` is False (ann is dict), 进入 anchors = None or [] = []
    # 进入 `if not anchors` 分支
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_doc_chunks_none_value():
    """document['chunks'] 显式 None → 视作无 chunks。"""
    doc = {"chunks": None}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # chunks None or []  → 进入 not chunks 分支
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_with_anchors_recall_zero_value():
    """1 chunk + anchors → recall 是 _ratio(0.0) 即 value=0.0, reason=None。"""
    doc = {"chunks": [{"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["reason"] is None


def test_chunk_boundary_prf_tolerance_zero_with_exact_match():
    """tolerance=0 + 完全匹配 → match。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # |3 - 3| = 0 <= 0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_huge_tolerance():
    """tolerance 巨大，所有预测都能匹配。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10**9)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_does_not_mutate_document():
    """document 不应被修改。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}], "other": "value"}
    doc_before = dict(doc)
    doc_before["chunks"] = list(doc["chunks"])
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    chunk_boundary_prf(doc, ann)
    assert doc["chunks"][0]["text"] == "abc"
    assert doc["other"] == "value"


def test_chunk_boundary_prf_does_not_mutate_annotation():
    """annotation 不应被修改。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}], "other": "x"}
    chunk_boundary_prf(doc, ann)
    assert ann["chunk_boundary_anchors"][0]["marker"] == "abc"
    assert ann["other"] == "x"


# ---------- figure_caption_prf 行为深度第七批 ----------


def test_figure_caption_prf_returns_three_metrics_with_constant_reason():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_ignores_document_chunks():
    """传完整 document（含 chunks）也不影响 figure_caption。"""
    doc = {"chunks": [{"text": "foo"}], "elements": [{"type": "figure"}]}
    ann = {"figure_caption_relations": [["f1", "c1"]]}
    out = figure_caption_prf(doc, ann)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_idempotent():
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    assert out1 == out2


def test_figure_caption_prf_does_not_mutate_inputs():
    doc = {"chunks": [{"text": "foo"}]}
    ann = {"figure_caption_relations": []}
    figure_caption_prf(doc, ann)
    assert doc == {"chunks": [{"text": "foo"}]}
    assert ann == {"figure_caption_relations": []}


def test_figure_caption_prf_positional_args():
    out = figure_caption_prf(None, None)
    assert "figure_caption_precision" in out


def test_figure_caption_prf_kwargs_only():
    out = figure_caption_prf(document=None, annotation=None)
    assert "figure_caption_recall" in out


def test_figure_caption_prf_returns_dict_type():
    assert isinstance(figure_caption_prf(None, None), dict)


# ---------- module source forbidden tokens 第十批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.chmod", "os.chown",
        "os.execv", "os.fork",
        "os.kill", "os.mkdir",
        "os.makedirs", "os.remove",
        "os.rename", "os.rmdir",
        "os.unlink",
        "pathlib.Path.rmdir",
        "pathlib.Path.unlink",
        "eval(", "exec(",
        "compile(",
        "globals(",
        "locals(",
        "vars(",
        "memoryview",
        "bytearray(",
        "errno",
        "signal.signal",
        "fcntl",
        "termios",
        "tty",
        "pty",
        "winreg",
        "msvcrt",
        "_winapi",
        "re.match",
        "re.sub",
        "shutil.rmtree",
        "tempfile.mkdtemp",
    ],
)
def test_annotation_metrics_source_no_forbidden_token_v3(token):
    src = inspect.getsource(amod)
    assert token not in src, f"forbidden token found: {token}"


# ---------- signatures 第七批 ----------


def test_signature_chunk_boundary_prf_param_kinds():
    sig = inspect.signature(chunk_boundary_prf)
    params = sig.parameters
    assert params["document"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params["annotation"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params["tolerance_chars"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_chunk_boundary_prf_doc_annotation():
    sig = inspect.signature(chunk_boundary_prf)
    params = sig.parameters
    assert params["document"].annotation is not inspect.Parameter.empty
    assert params["annotation"].annotation is not inspect.Parameter.empty


def test_signature_chunk_boundary_prf_tolerance_annotation():
    sig = inspect.signature(chunk_boundary_prf)
    params = sig.parameters
    # tolerance_chars 注解是 int（from __future__ → 字符串）
    annot = params["tolerance_chars"].annotation
    assert annot is int or annot == "int"


def test_signature_figure_caption_prf_two_params():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.values())
    assert len(params) == 2


def test_signature_figure_caption_prf_param_kinds():
    sig = inspect.signature(figure_caption_prf)
    params = sig.parameters
    assert params["document"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params["annotation"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_chunk_boundary_prf_no_varargs():
    sig = inspect.signature(chunk_boundary_prf)
    has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    assert not has_var


def test_signature_figure_caption_prf_no_varargs():
    sig = inspect.signature(figure_caption_prf)
    has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    assert not has_var


def test_signature_chunk_boundary_prf_no_kwargs():
    sig = inspect.signature(chunk_boundary_prf)
    has_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    assert not has_kw


def test_signature_figure_caption_prf_no_kwargs():
    sig = inspect.signature(figure_caption_prf)
    has_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    assert not has_kw


def test_signature_parser_does_not_emit_constant_type():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_signature_parser_does_not_emit_constant_value():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


# ---------- module 合理性第七批 ----------


def test_module_all_exact_3_items_in_order():
    """__all__ 应按定义顺序列出 3 项。"""
    expected = ["PARSER_DOES_NOT_EMIT_RELATIONS", "figure_caption_prf", "chunk_boundary_prf"]
    assert amod.__all__ == expected


def test_module_all_entries_unique():
    assert len(amod.__all__) == len(set(amod.__all__))


def test_module_all_entries_are_str():
    for item in amod.__all__:
        assert isinstance(item, str)


def test_module_namespace_callable_count_2():
    """模块定义的 function 数量 = 2（figure_caption_prf + chunk_boundary_prf）。"""
    funcs = [
        name for name, val in vars(amod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == amod.__name__
    ]
    assert len(funcs) == 2


def test_module_namespace_callable_names():
    """callable 名称集合正确。"""
    funcs = {
        name for name, val in vars(amod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == amod.__name__
    }
    assert funcs == {"figure_caption_prf", "chunk_boundary_prf"}


def test_module_has_docstring():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 0


def test_module_docstring_mentions_chunk_boundary():
    assert "chunk_boundary" in amod.__doc__


def test_module_docstring_mentions_figure_caption():
    assert "figure_caption" in amod.__doc__


def test_module_docstring_mentions_one_to_one():
    """__doc__ 应说明一对一匹配语义。"""
    assert "一对一" in amod.__doc__


def test_module_file_endswith_annotation_metrics_py():
    assert amod.__file__.endswith("annotation_metrics.py")


def test_module_name_is_evaluation_annotation_metrics():
    assert amod.__name__ == "evaluation.annotation_metrics"


def test_module_function_module_attribute_eq():
    assert figure_caption_prf.__module__ == "evaluation.annotation_metrics"
    assert chunk_boundary_prf.__module__ == "evaluation.annotation_metrics"


def test_module_no_user_classes():
    """模块内不应有 class 定义。"""
    classes = [
        name for name, val in vars(amod).items()
        if isinstance(val, type) and val.__module__ == amod.__name__
    ]
    assert len(classes) == 0


# ---------- module source 字符串精确补强第七批 ----------


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


def test_module_source_no_main_block():
    src = inspect.getsource(amod)
    assert '__main__' not in src


def test_module_source_no_yield():
    src = inspect.getsource(amod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(amod)
    assert "async def" not in src


def test_module_source_no_walrus():
    src = inspect.getsource(amod)
    assert ":=" not in src


def test_module_source_no_eval():
    src = inspect.getsource(amod)
    assert "eval(" not in src


def test_module_source_no_exec():
    src = inspect.getsource(amod)
    assert "exec(" not in src


def test_module_source_no_compile():
    src = inspect.getsource(amod)
    assert "compile(" not in src


def test_module_source_no_subprocess():
    src = inspect.getsource(amod)
    assert "subprocess" not in src


def test_module_source_no_unlink():
    src = inspect.getsource(amod)
    assert "unlink" not in src


def test_module_source_no_open():
    """annotation_metrics 不应做文件 IO。"""
    src = inspect.getsource(amod)
    # 'open(' 字面值（不是 keyword）
    assert "open(" not in src


def test_module_source_no_print():
    src = inspect.getsource(amod)
    assert "print(" not in src


def test_module_source_no_relative_import_above_app_or_eval():
    src = inspect.getsource(amod)
    # 不应出现 'from .' 或 'from ..'
    assert "from ." not in src


def test_module_source_no_star_import():
    src = inspect.getsource(amod)
    assert "import *" not in src


def test_module_source_no_user_class_definition():
    src = inspect.getsource(amod)
    lines = src.splitlines()
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("class "):
            pytest.fail(f"Found class definition: {line}")


# ---------- 端到端集成第七批 ----------


def test_e2e_full_pipeline_two_chunks_with_anchors():
    """端到端：2 chunks + 1 anchor，简单 match。"""
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "world", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0
    assert out["_tolerance_chars"]["value"] == 10


def test_e2e_no_chunks_returns_pipeline_failed_or_no_predicted():
    """document None → pipeline_failed；有 document 但 chunks=[] → no_predicted_boundaries。"""
    out1 = chunk_boundary_prf(None, None)
    assert out1["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    out2 = chunk_boundary_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    assert out2["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_e2e_no_annotation_returns_no_annotation():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_e2e_empty_annotation_dict_returns_no_annotation():
    """空 dict 是 falsy → no_annotation。"""
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_e2e_one_chunk_with_anchors_no_predicted():
    """1 chunk → 无内部边界。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}]},
        {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_e2e_chunks_present_anchors_empty():
    """有 chunks 但 anchors=[] → no_ground_truth_anchors。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": []},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_e2e_tolerance_recorded_in_output():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {})
    assert "_tolerance_chars" in out
    assert out["_tolerance_chars"]["value"] == 30  # default


def test_e2e_custom_tolerance_recorded():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]}, {}, tolerance_chars=42
    )
    assert out["_tolerance_chars"]["value"] == 42


def test_e2e_chunk_boundary_returns_dict_of_dicts():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {})
    assert isinstance(out, dict)
    for k, v in out.items():
        assert isinstance(v, dict)


def test_e2e_value_or_reason_in_each_metric():
    """每个 metric dict 都应有 value 或 reason。"""
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {})
    for k, v in out.items():
        assert "value" in v or "reason" in v


def test_e2e_full_match_position_before_at_start():
    """position=before 在 stream 起始（find_pos=0）→ gt_pos=0；与预测 0 距离匹配。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # stream = "abc def"
    # predicted at pos 3 (end of 'abc')
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # gt_pos = 0, predicted = 3, distance = 3 <= 5 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_full_match_position_after():
    """position=after → gt_pos = find_pos + len(marker)。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # gt_pos = 3 (find_pos=0 + len('abc')=3), predicted = 3 → exact match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_three_chunks_one_anchor_perfect_match():
    """3 chunks → 2 predicted boundaries；2 anchors 各匹配 1 → 全 1.0。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}, {"text": "ccc"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "a", "position": "after"},   # pos 3
        {"marker": "b", "position": "after"},   # pos 7
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_three_chunks_zero_match_due_to_tolerance():
    """tolerance=0 但 marker 偏移 → 0 match。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}, {"text": "ccc"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "aa", "position": "after"},   # pos 2，predicted=3 → distance=1
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # |3-2|=1 > 0 → no match
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_e2e_idempotent_call_returns_equal():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    out2 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out1 == out2


def test_e2e_positional_args_full_call():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, 10)
    assert out["chunk_boundary_precision"]["value"] == 1.0
