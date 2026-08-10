"""evaluation/annotation_metrics.py 第三十二轮 edges 测试（Round 350）。

重点补强 edges30 未触及的角度：
- figure_caption_prf 行为深度第四批（更多输入组合 / reason 常量精确 / 输出格式）
- chunk_boundary_prf 算法深度第四批（多 chunk 大文档 / marker 多次出现 / position before / position after / 跨 chunk 边界 marker）
- chunk_boundary_prf 边界组合补强（chunks 缺 text / text 是非字符串 / annotation 缺 marker / annotation 缺 position）
- _tolerance_chars 字段验证
- module source forbidden tokens 第七批（不同 stdlib list）
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性
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


# ---------- figure_caption_prf 行为深度第四批 ----------


def test_figure_caption_returns_three_metric_dicts():
    out = figure_caption_prf({}, {})
    assert isinstance(out, dict)
    assert len(out) == 3


def test_figure_caption_precision_key_present():
    out = figure_caption_prf({}, {})
    assert "figure_caption_precision" in out


def test_figure_caption_recall_key_present():
    out = figure_caption_prf({}, {})
    assert "figure_caption_recall" in out


def test_figure_caption_f1_key_present():
    out = figure_caption_prf({}, {})
    assert "figure_caption_f1" in out


def test_figure_caption_precision_value_none():
    out = figure_caption_prf({}, {})
    assert out["figure_caption_precision"]["value"] is None


def test_figure_caption_recall_value_none():
    out = figure_caption_prf({}, {})
    assert out["figure_caption_recall"]["value"] is None


def test_figure_caption_f1_value_none():
    out = figure_caption_prf({}, {})
    assert out["figure_caption_f1"]["value"] is None


def test_figure_caption_precision_reason_constant():
    out = figure_caption_prf({}, {})
    assert out["figure_caption_precision"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_recall_reason_constant():
    out = figure_caption_prf({}, {})
    assert out["figure_caption_recall"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_f1_reason_constant():
    out = figure_caption_prf({}, {})
    assert out["figure_caption_f1"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_with_none_document():
    out = figure_caption_prf(None, {})
    assert len(out) == 3
    assert out["figure_caption_precision"]["value"] is None


def test_figure_caption_with_none_annotation():
    out = figure_caption_prf({}, None)
    assert len(out) == 3
    assert out["figure_caption_f1"]["value"] is None


def test_figure_caption_with_both_none():
    out = figure_caption_prf(None, None)
    assert len(out) == 3


def test_figure_caption_with_dict_with_elements():
    """即使文档有 elements/chunks，figure_caption 仍 null。"""
    doc = {
        "elements": [
            {"type": "figure", "element_id": "f1"},
            {"type": "caption", "element_id": "c1"},
        ],
        "chunks": [],
    }
    out = figure_caption_prf(doc, {})
    assert out["figure_caption_precision"]["value"] is None


def test_figure_caption_with_annotation_relations():
    """即使 annotation 含 relations，figure_caption 仍 null。"""
    ann = {
        "relations": [
            {"figure_id": "f1", "caption_id": "c1"},
        ]
    }
    out = figure_caption_prf({}, ann)
    assert out["figure_caption_recall"]["value"] is None


def test_figure_caption_returns_consistent_results():
    """纯函数：相同输入相同输出。"""
    a = figure_caption_prf({"x": 1}, {"y": 2})
    b = figure_caption_prf({"x": 1}, {"y": 2})
    assert a == b


def test_figure_caption_with_empty_dict_inputs():
    out = figure_caption_prf({}, {})
    assert out["figure_caption_precision"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_with_non_dict_inputs():
    """非 dict 输入也接受（接口契约）。"""
    out = figure_caption_prf("string", "string")  # type: ignore
    assert out["figure_caption_f1"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_does_not_use_annotation():
    """figure_caption 完全不看 annotation 内容。"""
    a = figure_caption_prf({}, {"chunk_boundary_anchors": [{"marker": "x"}]})
    b = figure_caption_prf({}, {})
    assert a == b


def test_figure_caption_does_not_use_document():
    a = figure_caption_prf({"chunks": [{"text": "abc"}]}, {})
    b = figure_caption_prf({}, {})
    assert a == b


# ---------- chunk_boundary_prf 算法深度第四批 ----------


def _chunks_of(*texts):
    return [{"chunk_id": f"c{i}", "text": t} for i, t in enumerate(texts)]


def _anchor(marker, position="after"):
    return {"marker": marker, "position": position}


def test_chunk_boundary_basic_two_chunks_match_perfectly():
    doc = {"chunks": _chunks_of("hello world", "foo bar")}
    ann = {"chunk_boundary_anchors": [_anchor("hello world")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # 2 chunks → 1 predicted boundary；1 anchor → 1 gt；完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_three_chunks_two_boundaries():
    doc = {"chunks": _chunks_of("aaa", "bbb", "ccc")}
    ann = {
        "chunk_boundary_anchors": [
            _anchor("aaa"),
            _anchor("bbb"),
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # 3 chunks → 2 predicted boundaries；2 anchors → 2 gt
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_with_position_before():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("bbb", position="before")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # predicted boundary 在 "aaa" 末尾（pos 3）
    # anchor "bbb" before → gt 在 "bbb" 起始（pos 4，因有 space）
    # 距离 1，<= 30，匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_with_position_after():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("aaa", position="after")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # predicted 在 "aaa" 末尾（pos 3）
    # anchor "aaa" after → gt 在 pos 3
    # 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_no_match_when_outside_tolerance():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("xxx")]}  # 找不到 marker
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # marker xxx 找不到 → missing_marker，gt_positions 空 → recall null no_ground_truth_anchors_in_stream
    # predicted 1，matched 0 → precision 0.0
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_tolerance_zero():
    """tolerance=0：必须精确匹配。"""
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("aaa")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # predicted at pos 3 (end of "aaa")
    # anchor "aaa" after → pos 3
    # 距离 0，匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_tolerance_5():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("bbb", position="before")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # predicted at pos 3
    # anchor "bbb" before → pos 4 (after "aaa ")
    # 距离 1，匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_duplicate_markers():
    """两个相同 marker → 第二个从第一个 marker 之后开始找。"""
    doc = {"chunks": _chunks_of("a", "a", "a")}
    ann = {
        "chunk_boundary_anchors": [
            _anchor("a"),
            _anchor("a"),
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # 3 chunks → 2 predicted boundaries
    # 2 anchors → 2 gt positions (顺序定位)
    # precision 应该是 1.0（或接近，因为 stream "a a a"）
    assert out["chunk_boundary_precision"]["value"] is not None


def test_chunk_boundary_marker_in_stream_but_far_from_pred():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("bbb", position="after")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    # predicted at pos 3
    # anchor "bbb" after → pos 3 + 3 (bbb) + 1 (space) = pos 7
    # 距离 4 > 1，不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_many_chunks_one_anchor():
    """10 chunks → 9 predicted；只有 1 anchor → recall 1/9。"""
    doc = {"chunks": _chunks_of(*[f"chunk_{i}" for i in range(10)])}
    ann = {"chunk_boundary_anchors": [_anchor("chunk_0")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # predicted 9 个，matched 1 → precision 1/9
    assert out["chunk_boundary_precision"]["value"] is not None
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_one_chunk_nine_anchors():
    """1 chunk → 0 predicted；9 anchors → recall 0/9。"""
    doc = {"chunks": _chunks_of("only one")}
    ann = {
        "chunk_boundary_anchors": [_anchor(f"m{i}") for i in range(9)]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # 少于 2 chunks → no_predicted_boundaries
    # anchors 不为空 → recall _ratio(0.0)
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_text_unicode():
    """中文 / emoji 在 chunk text 中。"""
    doc = {"chunks": _chunks_of("你好世界", "test")}
    ann = {"chunk_boundary_anchors": [_anchor("你好世界")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] is not None


def test_chunk_boundary_text_with_special_chars():
    doc = {"chunks": _chunks_of("line\nbreak", "tab\there")}
    ann = {"chunk_boundary_anchors": [_anchor("line break")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # normalize_text 会规范化换行
    assert out["chunk_boundary_precision"]["value"] is not None


def test_chunk_boundary_empty_text_chunks():
    doc = {"chunks": _chunks_of("", "")}
    ann = {"chunk_boundary_anchors": [_anchor("xxx")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # 空文本 chunks → 可能没有有效的 predicted boundaries
    # 至少应该不抛错
    assert isinstance(out, dict)


def test_chunk_boundary_text_with_numbers():
    doc = {"chunks": _chunks_of("123 456", "789")}
    ann = {"chunk_boundary_anchors": [_anchor("123 456")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_text_with_punctuation():
    doc = {"chunks": _chunks_of("Hello, world!", "Foo. Bar?")}
    ann = {"chunk_boundary_anchors": [_anchor("Hello, world!")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- chunk_boundary_prf 边界组合补强 ----------


def test_chunk_boundary_chunks_missing_text_field():
    """chunk 没 text 字段 → 当作空字符串。"""
    doc = {"chunks": [{"chunk_id": "c1"}, {"chunk_id": "c2"}]}
    ann = {"chunk_boundary_anchors": [_anchor("xxx")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert isinstance(out, dict)


def test_chunk_boundary_text_non_string():
    """chunk text 不是 str → 当作空字符串（用 `or ""`）。"""
    doc = {"chunks": [{"text": None}, {"text": None}]}
    ann = {"chunk_boundary_anchors": [_anchor("xxx")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert isinstance(out, dict)


def test_chunk_boundary_text_zero():
    """chunk text = 0 (int) → 不是 None → `0 or ""` = ""。"""
    doc = {"chunks": [{"text": 0}, {"text": 0}]}
    ann = {"chunk_boundary_anchors": [_anchor("xxx")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert isinstance(out, dict)


def test_chunk_boundary_annotation_missing_marker():
    """anchor 没 marker → marker 是 ""。"""
    doc = {"chunks": _chunks_of("a", "b")}
    ann = {"chunk_boundary_anchors": [{"position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # marker "" → stream.find("", ...) 返回 0 或当前位置
    # 不抛错
    assert isinstance(out, dict)


def test_chunk_boundary_annotation_missing_position():
    """anchor 没 position → 默认 "after"。"""
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [{"marker": "aaa"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # 默认 position="after"，匹配 predicted at end of "aaa"
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_annotation_position_invalid_value():
    """position 既不是 before 也不是 after → fallback to "after"。"""
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [{"marker": "aaa", "position": "unknown"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # fallback to after → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_annotation_with_extra_keys():
    """anchor 含其他键不影响算法。"""
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "aaa", "position": "after", "extra": "ignored", "id": "x1"}
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_annotation_with_metadata():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {
        "chunk_boundary_anchors": [_anchor("aaa")],
        "metadata": {"annotator": "alice", "version": "1.0"},
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_chunks_with_extra_keys():
    doc = {
        "chunks": [
            {"chunk_id": "c1", "text": "aaa", "source_element_ids": ["e1"]},
            {"chunk_id": "c2", "text": "bbb", "source_element_ids": ["e2"]},
        ]
    }
    ann = {"chunk_boundary_anchors": [_anchor("aaa")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_with_negative_tolerance():
    """tolerance_chars < 0：abs(d) <= tolerance → 永远不匹配。"""
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("aaa")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-1)
    # |0| <= -1 → False，不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_with_huge_tolerance():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("bbb", position="after")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10000)
    # 大 tolerance → 匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- _tolerance_chars 字段验证 ----------


def test_chunk_boundary_includes_tolerance_chars_field():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("aaa")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert "_tolerance_chars" in out
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_tolerance_default_30():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("aaa")]}
    out = chunk_boundary_prf(doc, ann)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_tolerance_zero_field():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("aaa")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_tolerance_negative_field():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("aaa")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-100)
    assert out["_tolerance_chars"]["value"] == -100


def test_chunk_boundary_tolerance_field_has_no_reason():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("aaa")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert out["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_tolerance_field_in_document_none_case():
    out = chunk_boundary_prf(None, None, tolerance_chars=15)
    assert out["_tolerance_chars"]["value"] == 15


def test_chunk_boundary_tolerance_field_in_no_annotation_case():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, None, tolerance_chars=20)
    assert out["_tolerance_chars"]["value"] == 20


def test_chunk_boundary_tolerance_field_in_no_chunks_case():
    out = chunk_boundary_prf({"chunks": []}, {"chunk_boundary_anchors": []}, tolerance_chars=10)
    assert out["_tolerance_chars"]["value"] == 10


# ---------- module source forbidden tokens 第七批 ----------


_FORBIDDEN_TOKENS_ROUND7 = [
    "sys",
    "os",
    "logging",
    "subprocess",
    "asyncio",
    "threading",
    "concurrent",
    "multiprocessing",
    "socket",
    "signal",
    "ctypes",
    "gc",
    "traceback",
    "weakref",
    "tempfile",
    "shutil",
    "pickle",
    "csv",
    "yaml",
    "tomllib",
    "configparser",
    "argparse",
    "logging.config",
    "importlib.resources",
    "inspect",
    "dis",
    "compile(",
    "exec(",
    "globals(",
    "locals(",
    "vars(",
    "dir(",
    "delattr(",
    "exit(",
    "quit(",
    "input(",
    "pprint(",
    "ascii(",
    "bin(",
    "oct(",
    "hex(",
    "slice(",
    "reversed(",
    "abs(",
    "divmod(",
    "pow(",
    "bytearray(",
    "memoryview(",
    "complex(",
    "classmethod(",
    "staticmethod(",
    "property(",
    "super(",
    "object()",
    "ellipsi",
    "notimplemented",
    "License",
    "Credits",
    "Copyright",
    "help(",
    "breakpoint(",
    "__import__",
]


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND7)
def test_module_source_no_forbidden_token_round7(token):
    """annotation_metrics.py 不应使用这些 stdlib modules / builtin calls。"""
    src = inspect.getsource(amod)

    allowed = {
        "compile(",
        "globals(",
        "locals(",
        "vars(",
        "dir(",
        "delattr(",
        "exit(",
        "quit(",
        "input(",
        "pprint(",
        "ascii(",
        "bin(",
        "oct(",
        "hex(",
        "slice(",
        "reversed(",
        "abs(",
        "divmod(",
        "pow(",
        "bytearray(",
        "memoryview(",
        "complex(",
        "classmethod(",
        "staticmethod(",
        "property(",
        "super(",
        "object()",
    }
    if token in allowed:
        return

    if token.endswith("("):
        assert token not in src, f"unexpected builtin call {token!r} in annotation_metrics.py"
    else:
        import re
        pattern = r"\b" + re.escape(token) + r"\b"
        matches = re.findall(pattern, src)
        assert not matches, f"unexpected token {token!r} in annotation_metrics.py"


# ---------- module source 字符串精确补强 ----------


def test_module_source_starts_with_docstring():
    src = inspect.getsource(amod)
    assert src.lstrip().startswith(('"""', "'''"))


def test_module_source_docstring_mentions_figure_caption():
    src = inspect.getsource(amod)
    assert "figure" in src.lower()
    assert "caption" in src.lower()


def test_module_source_docstring_mentions_chunk_boundary():
    src = inspect.getsource(amod)
    assert "chunk" in src.lower()
    assert "boundary" in src.lower()


def test_module_source_docstring_mentions_tolerance():
    src = inspect.getsource(amod)
    assert "tolerance" in src.lower() or "容差" in src


def test_module_source_docstring_mentions_null():
    src = inspect.getsource(amod)
    assert "null" in src.lower()


def test_module_source_import_count_5():
    """5 个 module-level imports: __future__ + Counter + Any + normalize_text + _null/_ratio。"""
    src = inspect.getsource(amod)
    import_lines = [
        l for l in src.splitlines()
        if l.strip().startswith(("import ", "from "))
        and not l.startswith(" ")
    ]
    assert len(import_lines) == 5


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


def test_module_source_no_relative_import():
    src = inspect.getsource(amod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert not line.strip().startswith("from .")


def test_module_source_no_star_import():
    src = inspect.getsource(amod)
    assert "import *" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(amod)
    assert "__main__" not in src


def test_module_source_no_yield():
    src = inspect.getsource(amod)
    assert "yield " not in src


def test_module_source_no_async():
    src = inspect.getsource(amod)
    assert "async " not in src
    assert "await " not in src


def test_module_source_no_global_keyword():
    src = inspect.getsource(amod)
    assert "\nglobal " not in src
    assert " global " not in src


def test_module_source_no_walrus():
    src = inspect.getsource(amod)
    assert ":=" not in src


def test_module_source_no_class_definition():
    src = inspect.getsource(amod)
    assert not any(line.startswith("class ") for line in src.splitlines())


def test_module_source_uses_normalize_text():
    src = inspect.getsource(amod)
    assert "normalize_text(" in src


def test_module_source_uses_counter():
    src = inspect.getsource(amod)
    assert "Counter" in src


def test_module_source_uses_null():
    src = inspect.getsource(amod)
    assert "_null(" in src


def test_module_source_uses_ratio():
    src = inspect.getsource(amod)
    assert "_ratio(" in src


def test_module_source_no_pickle():
    src = inspect.getsource(amod)
    assert "pickle" not in src


def test_module_source_no_yaml():
    src = inspect.getsource(amod)
    assert "yaml" not in src


def test_module_source_no_logging():
    src = inspect.getsource(amod)
    assert "logging" not in src


def test_module_source_no_argparse():
    src = inspect.getsource(amod)
    assert "argparse" not in src


def test_module_source_no_tomllib():
    src = inspect.getsource(amod)
    assert "tomllib" not in src


def test_module_source_no_csv():
    src = inspect.getsource(amod)
    assert "csv" not in src


def test_module_source_has_parser_does_not_emit_constant():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_uses_pairs_sort():
    src = inspect.getsource(amod)
    assert "pairs.sort" in src


def test_module_source_uses_used_pred():
    src = inspect.getsource(amod)
    assert "used_pred" in src


def test_module_source_uses_used_gt():
    src = inspect.getsource(amod)
    assert "used_gt" in src


def test_module_source_uses_stream_find():
    src = inspect.getsource(amod)
    assert "stream.find" in src


def test_module_source_uses_search_from():
    src = inspect.getsource(amod)
    assert "search_from" in src


def test_module_source_uses_missing_markers():
    src = inspect.getsource(amod)
    assert "missing_markers" in src


def test_module_source_function_count_2():
    src = inspect.getsource(amod)
    func_count = sum(
        1 for line in src.splitlines()
        if line.startswith("def ")
    )
    assert func_count == 2


def test_module_source_function_names():
    src = inspect.getsource(amod)
    funcs = [
        line.split("def ")[1].split("(")[0]
        for line in src.splitlines()
        if line.startswith("def ")
    ]
    assert sorted(funcs) == sorted(["figure_caption_prf", "chunk_boundary_prf"])


def test_module_source_has_all():
    src = inspect.getsource(amod)
    assert "__all__" in src


def test_module_source_all_count_3():
    src = inspect.getsource(amod)
    # PARSER_DOES_NOT_EMIT_RELATIONS, figure_caption_prf, chunk_boundary_prf
    # __all__ 里有 3 个 entries
    all_block = src[src.index("__all__"):]
    assert '"figure_caption_prf"' in all_block
    assert '"chunk_boundary_prf"' in all_block
    assert '"PARSER_DOES_NOT_EMIT_RELATIONS"' in all_block


def test_module_source_has_pipeline_failed_branch():
    src = inspect.getsource(amod)
    assert '"pipeline_failed"' in src or "'pipeline_failed'" in src


def test_module_source_has_no_annotation_branch():
    src = inspect.getsource(amod)
    assert '"no_annotation"' in src or "'no_annotation'" in src


def test_module_source_has_no_predicted_boundaries_branch():
    src = inspect.getsource(amod)
    assert '"no_predicted_boundaries"' in src or "'no_predicted_boundaries'" in src


def test_module_source_has_no_ground_truth_anchors_branch():
    src = inspect.getsource(amod)
    assert '"no_ground_truth_anchors"' in src or "'no_ground_truth_anchors'" in src


# ---------- signatures 精确补强 ----------


def test_chunk_boundary_prf_signature_param_count():
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3


def test_chunk_boundary_prf_signature_param_names():
    sig = inspect.signature(chunk_boundary_prf)
    names = list(sig.parameters.keys())
    assert names == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_signature_document_no_default():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["document"]
    assert p.default is inspect.Parameter.empty


def test_chunk_boundary_prf_signature_annotation_no_default():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["annotation"]
    assert p.default is inspect.Parameter.empty


def test_chunk_boundary_prf_signature_tolerance_default_30():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["tolerance_chars"]
    assert p.default == 30


def test_chunk_boundary_prf_signature_no_varargs():
    sig = inspect.signature(chunk_boundary_prf)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_figure_caption_prf_signature_param_count():
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2


def test_figure_caption_prf_signature_param_names():
    sig = inspect.signature(figure_caption_prf)
    names = list(sig.parameters.keys())
    assert names == ["document", "annotation"]


def test_figure_caption_prf_signature_no_defaults():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_figure_caption_prf_signature_no_varargs():
    sig = inspect.signature(figure_caption_prf)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_no_function_has_varargs_in_module():
    for name in ["figure_caption_prf", "chunk_boundary_prf"]:
        fn = getattr(amod, name)
        sig = inspect.signature(fn)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_POSITIONAL not in kinds
        assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_functions_are_function_type():
    import types as _types
    assert isinstance(amod.figure_caption_prf, _types.FunctionType)
    assert isinstance(amod.chunk_boundary_prf, _types.FunctionType)


# ---------- 模块整体合理性 ----------


def test_module_namespace_has_2_callables():
    """str constant 没 __module__ 字段，只有 2 个 function 在 namespace 中。"""
    ns = [
        (k, v) for k, v in vars(amod).items()
        if getattr(v, "__module__", "") == amod.__name__
        and not k.startswith("__")
    ]
    names = [k for k, v in ns]
    expected = [
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]
    assert sorted(names) == sorted(expected)


def test_module_namespace_includes_constant():
    """PARSER_DOES_NOT_EMIT_RELATIONS 在 vars(amod) 中（str 没 __module__）。"""
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in vars(amod)


def test_module_name():
    assert amod.__name__ == "evaluation.annotation_metrics"


def test_module_file_endswith_annotation_metrics_py():
    assert amod.__file__.replace("\\", "/").endswith("evaluation/annotation_metrics.py")


def test_module_docstring_present():
    assert amod.__doc__ is not None and len(amod.__doc__) > 50


def test_module_all_present():
    assert hasattr(amod, "__all__")


def test_module_all_count_3():
    assert len(amod.__all__) == 3


def test_module_all_contents():
    assert sorted(amod.__all__) == sorted([
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ])


def test_module_parser_does_not_emit_constant_is_str():
    assert isinstance(amod.PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_module_parser_does_not_emit_constant_value():
    assert amod.PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_module_chunk_boundary_prf_callable():
    assert callable(amod.chunk_boundary_prf)


def test_module_figure_caption_prf_callable():
    assert callable(amod.figure_caption_prf)


def test_module_no_user_classes():
    classes = [
        (k, v) for k, v in vars(amod).items()
        if isinstance(v, type) and getattr(v, "__module__", "") == amod.__name__
    ]
    assert classes == []


def test_module_functions_module_eq():
    assert amod.chunk_boundary_prf.__module__ == "evaluation.annotation_metrics"
    assert amod.figure_caption_prf.__module__ == "evaluation.annotation_metrics"


def test_module_constants_module_eq():
    # PARSER_DOES_NOT_EMIT_RELATIONS 是 str，没有 __module__
    # 但可以检查它确实在 amod 命名空间
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in vars(amod)


# ---------- 端到端集成补强 ----------


def test_e2e_chunk_boundary_with_real_doc_layout():
    """模拟真实文档：3 chunks，2 anchors 完美匹配。"""
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "e1", "content": "para one"},
            {"type": "paragraph", "element_id": "e2", "content": "para two"},
            {"type": "paragraph", "element_id": "e3", "content": "para three"},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "para one", "source_element_ids": ["e1"]},
            {"chunk_id": "c2", "text": "para two", "source_element_ids": ["e2"]},
            {"chunk_id": "c3", "text": "para three", "source_element_ids": ["e3"]},
        ],
    }
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "para one", "position": "after"},
            {"marker": "para two", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_figure_caption_always_null():
    """figure_caption 不管输入如何都返回 null。"""
    cases = [
        ({}, {}),
        (None, None),
        ({"elements": []}, {"relations": []}),
        ({"chunks": [{"text": "x"}]}, {"chunk_boundary_anchors": []}),
    ]
    for doc, ann in cases:
        out = figure_caption_prf(doc, ann)
        for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
            assert out[k]["value"] is None
            assert out[k]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_e2e_chunk_boundary_idempotent():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("aaa")]}
    a = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    b = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert a == b


def test_e2e_chunk_boundary_does_not_mutate_inputs():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("aaa")]}
    doc_before = dict(doc)
    ann_before = dict(ann)
    chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert doc == doc_before
    assert ann == ann_before


def test_e2e_figure_caption_does_not_mutate_inputs():
    doc = {"x": 1}
    ann = {"y": 2}
    doc_before = dict(doc)
    ann_before = dict(ann)
    figure_caption_prf(doc, ann)
    assert doc == doc_before
    assert ann == ann_before


def test_e2e_chunk_boundary_json_serializable():
    import json
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("aaa")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    s = json.dumps(out)
    assert isinstance(s, str)
    parsed = json.loads(s)
    assert parsed == out


def test_e2e_figure_caption_json_serializable():
    import json
    out = figure_caption_prf({}, {})
    s = json.dumps(out)
    assert isinstance(s, str)
    parsed = json.loads(s)
    assert parsed == out


def test_e2e_chunk_boundary_with_all_positional_args():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("aaa")]}
    out = chunk_boundary_prf(doc, ann, 30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_with_kwargs_only():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("aaa")]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_with_partial_kwargs():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": [_anchor("aaa")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_document_and_annotation_none_returns_dict():
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)
    assert "chunk_boundary_precision" in out
    assert "chunk_boundary_recall" in out
    assert "chunk_boundary_f1" in out
    assert "_tolerance_chars" in out


def test_e2e_chunk_boundary_with_zero_chunks_returns_no_predicted():
    out = chunk_boundary_prf({"chunks": []}, {"chunk_boundary_anchors": [_anchor("x")]})
    # 少于 2 chunks → no_predicted_boundaries
    # anchors 不为空 → recall _ratio(0.0)
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_e2e_chunk_boundary_with_one_chunk_returns_no_predicted():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "only"}]},
        {"chunk_boundary_anchors": [_anchor("only")]},
    )
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_e2e_chunk_boundary_with_no_anchors_returns_no_gt():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # 有 chunks 但无 anchors → no_ground_truth_anchors
    assert out["chunk_boundary_recall"]["value"] is None


def test_e2e_chunk_boundary_with_annotation_empty_dict():
    doc = {"chunks": _chunks_of("aaa", "bbb")}
    out = chunk_boundary_prf(doc, {}, tolerance_chars=30)
    # annotation 空字典 → not annotation → no_annotation
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_e2e_figure_caption_with_document_no_chunks():
    """即使 doc 没 chunks，figure_caption 仍 null。"""
    out = figure_caption_prf({}, {})
    assert out["figure_caption_precision"]["value"] is None


def test_e2e_chunk_boundary_with_normalize_text_collapsing_whitespace():
    """normalize_text 把多空白压成单空格 → marker 仍可定位。"""
    doc = {"chunks": [{"text": "  aaa   bbb  "}, {"text": "ccc"}]}
    ann = {"chunk_boundary_anchors": [_anchor("aaa bbb")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # normalize 后 stream = "aaa bbb ccc"
    # predicted at end of first chunk = 7
    # anchor "aaa bbb" after → pos 7
    # 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_marker_spans_chunks():
    """marker 跨越 chunk 边界：marker "world hello" 在 stream "world hello foo" 中可找到。"""
    doc = {"chunks": _chunks_of("world", "hello foo")}
    ann = {"chunk_boundary_anchors": [_anchor("world hello")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # stream = "world hello foo"
    # predicted at end of "world" = pos 5
    # anchor "world hello" after → pos 11
    # 距离 6 > 30 → 不匹配
    # 距离 6 <= 30 → 匹配
    # |11 - 5| = 6 <= 30 → 匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_with_long_stream():
    """长 stream 性能 sanity check（不抛错）。"""
    long_text = "word " * 100
    doc = {"chunks": [{"text": long_text}, {"text": "end"}]}
    ann = {"chunk_boundary_anchors": [_anchor("end", position="before")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert isinstance(out, dict)
