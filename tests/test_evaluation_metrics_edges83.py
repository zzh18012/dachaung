"""evaluation/metrics.py 第二百零二轮 edges 测试（Round 730）。

补强 edges80/edges81/edges82 未触及的角度（第九十五批）。

新角度：
- chunks 键显式 None → TypeError（_text_preservation 迭代 None 无守卫，现状记录）
- elements 带 "type": None → by_type {None: 1}（.get 默认值不生效，现状记录）
- error 缺 "code" 键 → KeyError（error["code"] 无守卫，现状记录）
- 多集合精确分数（"aab" vs "abb" → P=R=2/3、equal False）
- heading element_id None → 0.0（None 不在 id 集）
- _text_preservation([], []) → equal True + 双 null empty_expected_and_actual
- 模块 docstring 口径 D / "每个字符取 min" 注释 / Counter 导入行
- forbidden tokens 第二百批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import (
    _heading_boundary_ratio,
    _text_preservation,
    compute_automatic_metrics,
)


# ---------- 未守卫路径现状记录 ----------

def test_chunks_none_raises_typeerror_batch53():
    with pytest.raises(TypeError):
        compute_automatic_metrics({"elements": [], "chunks": None},
                                  None, "pdf", None)


def test_element_type_none_key_counts_as_none_batch53():
    out = compute_automatic_metrics({"elements": [{"type": None}], "chunks": []},
                                    None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {None: 1}


def test_error_missing_code_raises_keyerror_batch53():
    with pytest.raises(KeyError):
        compute_automatic_metrics({"elements": [], "chunks": []},
                                  {"message": "m"}, "pdf", None)


# ---------- 多集合精确分数 ----------

def test_multiset_partial_overlap_exact_batch53():
    tp = _text_preservation([{"type": "paragraph", "content": "aab"}],
                            [{"text": "abb"}])
    assert tp["precision"]["value"] == pytest.approx(2 / 3)
    assert tp["recall"]["value"] == pytest.approx(2 / 3)
    assert tp["equal"]["value"] is False


def test_multiset_superset_actual_batch53():
    # expected "ab"，actual "abab"：common=2，P=2/4，R=2/2
    tp = _text_preservation([{"type": "paragraph", "content": "ab"}],
                            [{"text": "abab"}])
    assert tp["precision"]["value"] == pytest.approx(0.5)
    assert tp["recall"]["value"] == 1.0


# ---------- heading / 空矩阵 ----------

def test_heading_none_id_not_matched_batch53():
    hb = _heading_boundary_ratio([{"type": "heading", "element_id": None}],
                                 [{"source_element_ids": ["x"]}])
    assert hb == {"value": 0.0, "reason": None}


def test_text_preservation_both_empty_batch53():
    tp = _text_preservation([], [])
    assert tp == {
        "equal": {"value": True, "reason": None},
        "precision": {"value": None, "reason": "empty_expected_and_actual"},
        "recall": {"value": None, "reason": "empty_expected_and_actual"},
    }


def test_text_preservation_image_only_elements_batch53():
    # image 不进 expected → expected 空；actual 空 → 双 null
    tp = _text_preservation([{"type": "image", "content": "x"}], [])
    assert tp["precision"]["reason"] == "empty_expected_and_actual"
    assert tp["recall"]["reason"] == "empty_expected_and_actual"


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(metrics_mod)


def test_source_docstring_v11_semantics_batch53():
    src = _src()
    assert "口径 D" in src
    assert "每个字符取 min" in src
    assert "from collections import Counter" in src
    assert "故意忽略空白差异" in src


def test_source_null_reason_constant_batch53():
    src = _src()
    assert '_NOT_EVALUATED = "not_evaluated"' in src
    assert src.count('_NOT_EVALUATED') == 1  # 定义后未使用（现状）


# ---------- forbidden tokens 第二百批 ----------

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
