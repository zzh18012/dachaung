"""evaluation/metrics.py 第二百零四轮 edges 测试（Round 744）。

补强 edges83/edges84 未触及的角度（第一百零九批）。

新角度：
- 非对称空象限：expected 有 actual 空 → equal False + precision null
  empty_actual + recall 0.0；反向 → precision 0.0 + recall null
  empty_expected（与 edges83 的双空象限互补）
- 字谜不变量："abc" vs "cba" → equal False 但 P=R=1.0（有序比对与
  多集合比对语义分离）
- docx relationship_id 只查键存在，值类型不查（int 123 → valid）
- element 缺 "type" 键 → by_type {"unknown": 1}（与 type None →
  {None: 1} 区分：.get 默认值只在键缺失时生效）
- 图片零字节文件不算实存（st_size > 0）
- image_base_dir 传字符串 → TypeError（str / Path 不支持）
- source_element_ids 传字符串：真值字符串按字符迭代 —— "a"（单字符
  恰在 id 集）→ valid；"ab" → 逐字符检查 → invalid（现状记录）
- forbidden tokens 第二百一十四批
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import (
    _chunk_reference_ratio,
    _docx_locator_ratio,
    _image_resource_ratio,
    _text_preservation,
    compute_automatic_metrics,
)


# ---------- 非对称空象限 ----------

def test_expected_only_quadrant_batch54():
    tp = _text_preservation([{"type": "paragraph", "content": "a"}], [])
    assert tp == {
        "equal": {"value": False, "reason": None},
        "precision": {"value": None, "reason": "empty_actual"},
        "recall": {"value": 0.0, "reason": None},
    }


def test_actual_only_quadrant_batch54():
    tp = _text_preservation([], [{"text": "a"}])
    assert tp == {
        "equal": {"value": False, "reason": None},
        "precision": {"value": 0.0, "reason": None},
        "recall": {"value": None, "reason": "empty_expected"},
    }


# ---------- 字谜不变量 ----------

def test_anagram_equal_false_but_full_pr_batch54():
    tp = _text_preservation([{"type": "paragraph", "content": "abc"}],
                            [{"text": "cba"}])
    assert tp["equal"]["value"] is False
    assert tp["precision"]["value"] == 1.0
    assert tp["recall"]["value"] == 1.0


# ---------- docx locator ----------

def test_docx_relationship_id_value_type_unchecked_batch54():
    out = _docx_locator_ratio(
        [{"type": "paragraph",
          "source_locator": {"relationship_id": 123}}])
    assert out == {"value": 1.0, "reason": None}


# ---------- element type 默认 ----------

def test_element_missing_type_key_counts_unknown_batch54():
    out = compute_automatic_metrics(
        {"elements": [{"content": "x"}], "chunks": []}, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"unknown": 1}


# ---------- 图片实存 ----------

def test_image_zero_byte_file_invalid_batch54(tmp_path):
    z = tmp_path / "zero.png"
    z.write_bytes(b"")
    out = _image_resource_ratio(
        [{"type": "image", "resource_path": str(z)}], None)
    assert out == {"value": 0.0, "reason": None}


def test_image_nonempty_file_valid_batch54(tmp_path):
    f = tmp_path / "ok.png"
    f.write_bytes(b"x")
    out = _image_resource_ratio(
        [{"type": "image", "resource_path": str(f)}], None)
    assert out == {"value": 1.0, "reason": None}


def test_image_base_dir_string_raises_typeerror_batch54(tmp_path):
    with pytest.raises(TypeError):
        _image_resource_ratio(
            [{"type": "image", "resource_path": "x.png"}], str(tmp_path))


# ---------- 字符串 ids 怪癖 ----------

def test_string_ids_single_char_valid_batch54():
    # "a" 真值 → 逐字符迭代 → 恰为 {"a"} → 全在 id 集
    out = _chunk_reference_ratio([{"element_id": "a"}],
                                 [{"source_element_ids": "a"}])
    assert out == {"value": 1.0, "reason": None}


def test_string_ids_multi_char_invalid_batch54():
    # "ab" 逐字符检查 'a','b' → 'b' 不在 → invalid（现状记录）
    out = _chunk_reference_ratio([{"element_id": "a"}],
                                 [{"source_element_ids": "ab"}])
    assert out == {"value": 0.0, "reason": None}


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(metrics_mod)


def test_source_type_default_unknown_batch54():
    assert 'e.get("type", "unknown")' in _src()


def test_source_image_size_guard_batch54():
    assert "p.stat().st_size > 0" in _src()


# ---------- forbidden tokens 第二百一十四批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch54():
    assert "open(" not in _src()
