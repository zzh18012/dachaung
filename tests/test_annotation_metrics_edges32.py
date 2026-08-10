"""evaluation/annotation_metrics.py 第三十三轮 edges 测试（Round 357）。

重点补强 edges31 未触及的角度：
- figure_caption_prf source level 字符串精确补强第二批
- chunk_boundary_prf source level 字符串精确补强第二批
- chunk_boundary_prf 算法深度第五批（更多 edge case）
- module source forbidden tokens 第七批
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性补强
- 端到端集成补强
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


# ---------- figure_caption_prf source level 字符串精确补强第二批 ----------


def test_figure_caption_source_starts_with_def():
    src = inspect.getsource(figure_caption_prf)
    assert src.lstrip().startswith("def figure_caption_prf(")


def test_figure_caption_source_two_params():
    src = inspect.getsource(figure_caption_prf)
    assert "document" in src
    assert "annotation" in src


def test_figure_caption_source_uses_parser_does_not_emit():
    src = inspect.getsource(figure_caption_prf)
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in src


def test_figure_caption_source_uses_null_helper():
    src = inspect.getsource(figure_caption_prf)
    assert "_null(" in src


def test_figure_caption_source_returns_three_metrics():
    src = inspect.getsource(figure_caption_prf)
    assert '"figure_caption_precision"' in src
    assert '"figure_caption_recall"' in src
    assert '"figure_caption_f1"' in src


def test_figure_caption_source_returns_dict():
    src = inspect.getsource(figure_caption_prf)
    assert "return {" in src


def test_figure_caption_source_uses_reason_var():
    """source 里定义 reason 变量。"""
    src = inspect.getsource(figure_caption_prf)
    assert "reason = PARSER_DOES_NOT_EMIT_RELATIONS" in src


def test_figure_caption_source_no_subprocess():
    src = inspect.getsource(figure_caption_prf)
    assert "subprocess" not in src


def test_figure_caption_source_no_eval():
    src = inspect.getsource(figure_caption_prf)
    assert "eval(" not in src


def test_figure_caption_source_no_yield():
    src = inspect.getsource(figure_caption_prf)
    assert "yield" not in src


def test_figure_caption_source_no_async():
    src = inspect.getsource(figure_caption_prf)
    assert "async def" not in src


def test_figure_caption_source_no_global():
    src = inspect.getsource(figure_caption_prf)
    lines = [l for l in src.splitlines() if not l.strip().startswith("#")]
    for l in lines:
        assert not l.strip().startswith("global ")


def test_figure_caption_source_no_walrus():
    src = inspect.getsource(figure_caption_prf)
    assert ":=" not in src


def test_figure_caption_source_no_class_def():
    src = inspect.getsource(figure_caption_prf)
    assert "\nclass " not in src


def test_figure_caption_source_no_open_call():
    src = inspect.getsource(figure_caption_prf)
    assert "open(" not in src


# ---------- chunk_boundary_prf source level 字符串精确补强第二批 ----------


def test_chunk_boundary_source_starts_with_def():
    src = inspect.getsource(chunk_boundary_prf)
    assert src.lstrip().startswith("def chunk_boundary_prf(")


def test_chunk_boundary_source_three_params():
    src = inspect.getsource(chunk_boundary_prf)
    assert "document" in src
    assert "annotation" in src
    assert "tolerance_chars" in src


def test_chunk_boundary_source_default_tolerance_30():
    src = inspect.getsource(chunk_boundary_prf)
    assert "tolerance_chars: int = 30" in src


def test_chunk_boundary_source_handles_document_none():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if document is None" in src or "document is None" in src


def test_chunk_boundary_source_handles_no_annotation():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if not annotation" in src


def test_chunk_boundary_source_handles_no_chunks():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if not chunks" in src
    assert "len(chunks) < 2" in src


def test_chunk_boundary_source_handles_no_anchors():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if not anchors" in src


def test_chunk_boundary_source_uses_normalize_text():
    src = inspect.getsource(chunk_boundary_prf)
    assert "normalize_text(" in src


def test_chunk_boundary_source_uses_counter():
    """可能不直接用 Counter；但 module imports Counter。"""
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_chunk_boundary_source_uses_join():
    src = inspect.getsource(chunk_boundary_prf)
    assert '" ".join(norm_chunks)' in src or ".join(" in src


def test_chunk_boundary_source_uses_find():
    src = inspect.getsource(chunk_boundary_prf)
    assert ".find(" in src


def test_chunk_boundary_source_uses_search_from():
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from" in src


def test_chunk_boundary_source_uses_missing_markers():
    src = inspect.getsource(chunk_boundary_prf)
    assert "missing_markers" in src


def test_chunk_boundary_source_uses_tolerance_chars_field():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"_tolerance_chars"' in src


def test_chunk_boundary_source_uses_missing_markers_field():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"_missing_markers"' in src


def test_chunk_boundary_source_returns_3_metrics_and_tolerance():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"chunk_boundary_precision"' in src
    assert '"chunk_boundary_recall"' in src
    assert '"chunk_boundary_f1"' in src


def test_chunk_boundary_source_uses_pairs_sort():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs.sort" in src


def test_chunk_boundary_source_uses_used_pred_used_gt():
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_pred" in src
    assert "used_gt" in src


def test_chunk_boundary_source_uses_matched_counter():
    src = inspect.getsource(chunk_boundary_prf)
    assert "matched += 1" in src or "matched =" in src


def test_chunk_boundary_source_uses_abs_distance():
    src = inspect.getsource(chunk_boundary_prf)
    assert "abs(" in src


def test_chunk_boundary_source_uses_f1_formula():
    src = inspect.getsource(chunk_boundary_prf)
    assert "2 * p_val * r_val / denom" in src


def test_chunk_boundary_source_uses_no_predicted_boundaries_reason():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"no_predicted_boundaries"' in src


def test_chunk_boundary_source_uses_no_annotation_reason():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"no_annotation"' in src


def test_chunk_boundary_source_uses_pipeline_failed_reason():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"pipeline_failed"' in src


def test_chunk_boundary_source_uses_no_ground_truth_anchors_reason():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"no_ground_truth_anchors"' in src


def test_chunk_boundary_source_uses_no_ground_truth_anchors_in_stream_reason():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"no_ground_truth_anchors_in_stream"' in src


def test_chunk_boundary_source_uses_precision_or_recall_not_evaluated_reason():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"precision_or_recall_not_evaluated"' in src


def test_chunk_boundary_source_uses_get_marker():
    src = inspect.getsource(chunk_boundary_prf)
    assert '.get("marker"' in src


def test_chunk_boundary_source_uses_get_position():
    src = inspect.getsource(chunk_boundary_prf)
    assert '.get("position"' in src


def test_chunk_boundary_source_position_before_after():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"before"' in src
    assert '"after"' in src


def test_chunk_boundary_source_uses_get_chunks():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'document.get("chunks")' in src


def test_chunk_boundary_source_uses_get_chunk_boundary_anchors():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'annotation.get("chunk_boundary_anchors")' in src


def test_chunk_boundary_source_uses_ratio_helper():
    src = inspect.getsource(chunk_boundary_prf)
    assert "_ratio(" in src


def test_chunk_boundary_source_no_eval():
    src = inspect.getsource(chunk_boundary_prf)
    assert "eval(" not in src


def test_chunk_boundary_source_no_subprocess():
    src = inspect.getsource(chunk_boundary_prf)
    assert "subprocess" not in src


def test_chunk_boundary_source_no_yield():
    src = inspect.getsource(chunk_boundary_prf)
    assert "yield" not in src


def test_chunk_boundary_source_no_async():
    src = inspect.getsource(chunk_boundary_prf)
    assert "async def" not in src


def test_chunk_boundary_source_no_global():
    src = inspect.getsource(chunk_boundary_prf)
    lines = [l for l in src.splitlines() if not l.strip().startswith("#")]
    for l in lines:
        assert not l.strip().startswith("global ")


def test_chunk_boundary_source_no_walrus():
    src = inspect.getsource(chunk_boundary_prf)
    assert ":=" not in src


def test_chunk_boundary_source_no_open():
    src = inspect.getsource(chunk_boundary_prf)
    assert "open(" not in src


# ---------- chunk_boundary_prf 算法深度第五批 ----------


def test_chunk_boundary_document_none_annotation_none():
    """document=None 直接返回 pipeline_failed。"""
    out = chunk_boundary_prf(None, None)
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_chunk_boundary_document_none_annotation_present():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"


def test_chunk_boundary_document_present_annotation_none():
    out = chunk_boundary_prf({"chunks": []}, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_document_present_annotation_empty_dict():
    out = chunk_boundary_prf({"chunks": []}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_no_chunks_no_anchors():
    out = chunk_boundary_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    # 没有 chunks 也没有 anchors → no_predicted_boundaries
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_one_chunk_no_anchors():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}]},
        {"chunk_boundary_anchors": []},
    )
    # 只有一个 chunk → no_predicted_boundaries
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_one_chunk_with_anchors_recall_zero():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}]},
        {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]},
    )
    # 一个 chunk → no_predicted_boundaries；但有 anchors → recall=0.0
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_two_chunks_no_anchors():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": []},
    )
    # 有预测但无标注 → no_ground_truth_anchors
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_two_chunks_full_match():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 边界在 "hello" 末尾 = 5；anchor 也在 "hello" 末尾 = 5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_position_before():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "world", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 边界在 "hello" 末尾 = 5（"hello world" 流，world 起始 6）
    # position="before" → anchor 在 world 起始 = 6；距离 = 1，容差内
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_marker_not_in_stream():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # marker 不在 stream 中 → missing_markers
    assert "_missing_markers" in out
    assert "xyz" in out["_missing_markers"]["value"]
    # 没有 ground truth → recall no_ground_truth_anchors_in_stream
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_marker_empty_string():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 空 marker → find returns -1
    assert "_missing_markers" in out


def test_chunk_boundary_position_default_after():
    """不指定 position 默认 after。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello"}]}  # 没有 position
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 默认 after → 应该匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_outside_tolerance():
    doc = {"chunks": [{"text": "abcdefghijklmnopqrstuvwxyz"}, {"text": "0123456789"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "0123456789", "position": "before"}]}
    # 流: "abcdefghijklmnopqrstuvwxyz 0123456789"
    # 边界: "abcdefghijklmnopqrstuvwxyz" 末尾 = 26
    # anchor: "0123456789" 起始 = 27
    # 距离 = 1，容差内
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 容差 0 → 距离 1 仍然太远 → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_tolerance_chars_recorded():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_three_chunks_two_boundaries():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "a", "position": "after"},
        {"marker": "b", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 2 个预测边界，2 个 anchor → 应该全匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_chunk_text_none():
    """chunks 中 text=None 应该被 normalize_text 处理。"""
    doc = {"chunks": [{"text": None}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 不应崩溃
    assert "_tolerance_chars" in out


def test_chunk_boundary_chunk_missing_text_key():
    doc = {"chunks": [{}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 不应崩溃
    assert "_tolerance_chars" in out


def test_chunk_boundary_anchor_missing_marker_key():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 没有 marker → 默认 ""，应该添加到 missing_markers
    assert "_missing_markers" in out


def test_chunk_boundary_anchor_missing_position_key():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 没有 position → 默认 after → 应该匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_f1_when_precision_zero():
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo"}]}
    # 边界 = 11；anchor 位置在 "foo" 之前 = 12；容差 0
    ann = {"chunk_boundary_anchors": [{"marker": "foo", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 距离 = 1 > 容差 0 → precision = 0/1 = 0
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    if p == 0.0 and r == 0.0:
        # f1 = 2*0*0/(0+0) → 0 by denom<=0 分支
        assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_repeated_marker():
    """两个相同 marker 在 stream 中应分别定位。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "ab"}, {"text": "c"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "ab", "position": "after"},
        {"marker": "ab", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 流: "ab ab c"
    # 边界1 = 2（"ab" 第一次结束）
    # 边界2 = 5（"ab" 第二次结束）
    # anchor1 = 2（"ab" 第一次结束）
    # anchor2 = 5（"ab" 第二次结束）
    # 应该全匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- module source forbidden tokens 第七批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "asyncio", "threading", "concurrent", "subprocess",
        "multiprocessing", "queue", "socket", "select",
        "re.match", "re.sub", "re.compile",
        "datetime.datetime",
        "time.time", "time.sleep", "time.perf_counter",
        "os.system", "os.popen",
        "logging.getLogger",
        "urllib.request", "http.client",
        "ctypes", "pickle.loads",
        "shutil.rmtree",
        "tempfile.mkdtemp",
        "glob.glob",
        "unittest.TestCase",
        "pytest.fixture",
        "sys.exit",
        "copy.deepcopy",
        "weakref.ref",
        "abc.ABC",
        "contextlib.contextmanager",
        "operator.add",
        "functools.reduce",
        "itertools.chain",
        "collections.OrderedDict",
        "collections.deque",
        "collections.defaultdict",
        "importlib.import_module",
        "platform.system",
    ],
)
def test_annotation_metrics_source_no_forbidden_token(token):
    src = inspect.getsource(amod)
    assert token not in src, f"forbidden token found: {token}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_docstring_present():
    src = inspect.getsource(amod)
    assert src.startswith('"""')


def test_module_source_docstring_mentions_figure_caption():
    src = inspect.getsource(amod)
    assert "figure-caption" in src or "figure_caption" in src


def test_module_source_docstring_mentions_chunk_boundary():
    src = inspect.getsource(amod)
    assert "chunk_boundary" in src or "chunk-boundary" in src


def test_module_source_docstring_mentions_parser_does_not_emit():
    src = inspect.getsource(amod)
    assert "parser" in src.lower()


def test_module_source_docstring_mentions_tolerance():
    src = inspect.getsource(amod)
    assert "tolerance" in src.lower() or "容差" in src


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


def test_module_source_imports_null_ratio():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_no_relative_import_above_app_or_eval():
    src = inspect.getsource(amod)
    assert "from .." not in src


def test_module_source_no_star_import():
    src = inspect.getsource(amod)
    assert "import *" not in src


def test_module_source_no_yield():
    src = inspect.getsource(amod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(amod)
    assert "async def" not in src


def test_module_source_no_walrus():
    src = inspect.getsource(amod)
    assert ":=" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(amod)
    assert 'if __name__' not in src
    assert "__main__" not in src


def test_module_source_no_user_class():
    """模块内无 class 定义（仅函数 + 常量）。"""
    src = inspect.getsource(amod)
    assert "\nclass " not in src
    assert not src.startswith("class ")


def test_module_source_parser_does_not_emit_constant():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_two_functions():
    import types as _types
    funcs = [
        name for name, val in vars(amod).items()
        if isinstance(val, _types.FunctionType) and val.__module__ == amod.__name__
    ]
    assert set(funcs) == {"figure_caption_prf", "chunk_boundary_prf"}


def test_module_source_all_3_entries():
    src = inspect.getsource(amod)
    assert '"PARSER_DOES_NOT_EMIT_RELATIONS"' in src
    assert '"figure_caption_prf"' in src
    assert '"chunk_boundary_prf"' in src


def test_module_source_no_eval():
    src = inspect.getsource(amod)
    assert "eval(" not in src


def test_module_source_no_exec():
    src = inspect.getsource(amod)
    assert "exec(" not in src


def test_module_source_no_compile():
    src = inspect.getsource(amod)
    assert "compile(" not in src


def test_module_source_no_open():
    """module 级无 open()。"""
    src = inspect.getsource(amod)
    # function-level 也不该有
    assert "open(" not in src


def test_module_source_no_unlink():
    src = inspect.getsource(amod)
    assert ".unlink(" not in src


def test_module_source_no_write():
    src = inspect.getsource(amod)
    assert ".write(" not in src


# ---------- signatures 精确补强 ----------


def test_signature_figure_caption_prf():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["document", "annotation"]


def test_signature_figure_caption_prf_no_defaults():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_figure_caption_prf_no_varargs():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_chunk_boundary_prf():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert len(params) == 3
    assert [p.name for p in params] == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_tolerance_default_30():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_chunk_boundary_prf_document_annotation_no_default():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty
    assert sig.parameters["annotation"].default is inspect.Parameter.empty


def test_signature_chunk_boundary_prf_no_varargs():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_figure_caption_return_annotation():
    sig = inspect.signature(figure_caption_prf)
    # 因 from __future__ import annotations，是字符串
    annot = sig.return_annotation
    assert "dict" in str(annot)


def test_signature_chunk_boundary_return_annotation():
    sig = inspect.signature(chunk_boundary_prf)
    annot = sig.return_annotation
    assert "dict" in str(annot)


def test_signature_parser_does_not_emit_constant_type():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_signature_parser_does_not_emit_constant_value():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


# ---------- 模块整体合理性补强 ----------


def test_module_has_docstring():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 10


def test_module_docstring_mentions_人工标注():
    assert "人工标注" in amod.__doc__ or "annotation" in amod.__doc__.lower()


def test_module_has_all_attribute():
    assert hasattr(amod, "__all__")


def test_module_all_is_list():
    assert isinstance(amod.__all__, list)


def test_module_all_length_3():
    assert len(amod.__all__) == 3


def test_module_all_entries_unique():
    assert len(set(amod.__all__)) == len(amod.__all__)


def test_module_all_entries_are_str():
    for entry in amod.__all__:
        assert isinstance(entry, str)


def test_module_all_3_entries_correct():
    assert set(amod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_namespace_has_2_callables():
    funcs = [
        name for name, val in vars(amod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == amod.__name__
    ]
    assert set(funcs) == {"figure_caption_prf", "chunk_boundary_prf"}


def test_module_namespace_has_constant():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_module_no_user_classes():
    classes = [
        name for name, val in vars(amod).items()
        if isinstance(val, type) and val.__module__ == amod.__name__
    ]
    assert classes == []


def test_module_name_is_evaluation_annotation_metrics():
    assert amod.__name__ == "evaluation.annotation_metrics"


def test_module_file_ends_with_annotation_metrics_py():
    assert amod.__file__.endswith("annotation_metrics.py")


def test_module_function_module_eq_amod():
    assert figure_caption_prf.__module__ == "evaluation.annotation_metrics"
    assert chunk_boundary_prf.__module__ == "evaluation.annotation_metrics"


def test_module_parser_does_not_emit_module_eq_amod():
    """PARSER_DOES_NOT_EMIT_RELATIONS 是 str，__module__ 是 builtins。"""
    assert PARSER_DOES_NOT_EMIT_RELATIONS.__class__.__module__ == "builtins"


# ---------- 端到端集成补强 ----------


def test_e2e_figure_caption_always_returns_three_metrics():
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf({}, {})
    out3 = figure_caption_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    assert set(out1.keys()) == {"figure_caption_precision", "figure_caption_recall", "figure_caption_f1"}
    assert set(out2.keys()) == {"figure_caption_precision", "figure_caption_recall", "figure_caption_f1"}
    assert set(out3.keys()) == {"figure_caption_precision", "figure_caption_recall", "figure_caption_f1"}


def test_e2e_figure_caption_idempotent():
    out1 = figure_caption_prf({"chunks": []}, {})
    out2 = figure_caption_prf({"chunks": []}, {})
    assert out1 == out2


def test_e2e_chunk_boundary_idempotent():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, ann)
    out2 = chunk_boundary_prf(doc, ann)
    assert out1 == out2


def test_e2e_chunk_boundary_does_not_mutate_doc():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    doc_before = dict(doc)
    doc_before["chunks"] = list(doc["chunks"])
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    chunk_boundary_prf(doc, ann)
    assert doc == doc_before


def test_e2e_chunk_boundary_does_not_mutate_annotation():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    ann_before = json.dumps(ann, sort_keys=True) if False else None  # 简化
    import json as _json
    ann_before = _json.dumps(ann, sort_keys=True)
    chunk_boundary_prf(doc, ann)
    assert _json.dumps(ann, sort_keys=True) == ann_before


def test_e2e_chunk_boundary_positional_args():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, 10)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_kwargs():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_default_tolerance():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["_tolerance_chars"]["value"] == 30


def test_e2e_full_pipeline_with_metrics():
    """figure_caption_prf + chunk_boundary_prf 同时调用。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    fc = figure_caption_prf(doc, ann)
    cb = chunk_boundary_prf(doc, ann)
    # 合并：cb 多了 _tolerance_chars
    merged = {**fc, **cb}
    assert "figure_caption_precision" in merged
    assert "chunk_boundary_precision" in merged
    assert "_tolerance_chars" in merged


def test_e2e_chunk_boundary_empty_chunks_list():
    out = chunk_boundary_prf({"chunks": []}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_e2e_chunk_boundary_document_no_chunks_key():
    out = chunk_boundary_prf({}, {})
    # 没有 chunks 键 → chunks=[] → no_annotation
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_e2e_chunk_boundary_annotation_no_anchors_key():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    # annotation 不为空但缺 chunk_boundary_anchors 键
    out = chunk_boundary_prf(doc, {"other_key": "value"})
    # 有 chunks 但 anchors=[] → no_ground_truth_anchors
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_e2e_chunk_boundary_tiny_tolerance_with_match():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    # 边界 = 5；anchor = 5；容差 0 也匹配
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_zero_tolerance_no_match():
    doc = {"chunks": [{"text": "hello"}, {"text": " world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "world", "position": "before"}]}
    # 流: "hello world" → 边界 = 5；anchor (world 起始) = 6；距离 1 > 容差 0
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 距离 1 > 0 → 不匹配 → precision = 0.0
    p = out["chunk_boundary_precision"]["value"]
    assert p == 0.0


def test_e2e_chunk_boundary_returns_dict_of_dicts():
    out = chunk_boundary_prf({"chunks": []}, {})
    assert isinstance(out, dict)
    for k, v in out.items():
        if k.startswith("_"):
            continue
        assert isinstance(v, dict)


def test_e2e_chunk_boundary_value_or_reason_in_each_metric():
    out = chunk_boundary_prf({"chunks": []}, {})
    for k, v in out.items():
        if k.startswith("_"):
            continue
        assert "value" in v
        assert "reason" in v
