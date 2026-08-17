"""evaluation/metrics.py 第四百一十九轮 edges 测试（Round 975）。

补强 edges116 未触及的角度（第三百五十一批，probe 实证）。

新角度：
- bool 不对称：page=True 绕过 isinstance(page, int)（bool 是 int）
  判定有效；bbox 内 True 被 _is_valid_bbox 显式拒绝 → 混合 0.5
- type 显式 None vs 键缺失的分歧：by_type 键 None（.get 默认值
  只在键缺失时生效）与 "unknown" 并存
- docx 结构键 section=None 值被无视：键存在即有效 → 1.0
- image element 携带 content "IMG" 不参与文本比对（type 过滤）
- 仅 image elements + chunks text None → equal True +
  P/R null empty_expected_and_actual
- expectations 计数值传字符串 "2" → actual < exp 抛 TypeError
  （锁定现状）
- 乱序 "AB" vs "BA"：equal False 但多集合 P/R 双 1.0
- forbidden tokens 第四百四十五批（open 0）
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


# ---------- bool page 不对称 ----------

def test_pdf_bool_page_asymmetry_batch173():
    doc = {"elements": [
        {"type": "paragraph", "content": "A",
         "source_locator": {"page": True, "bbox": [0, 0, 1, 1]}},
        {"type": "paragraph", "content": "B",
         "source_locator": {"page": 1, "bbox": [0, 0, 1, True]}}],
        "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"] == {"value": 0.5,
                                              "reason": None}


# ---------- type None vs 缺失 ----------

def test_by_type_none_key_vs_unknown_batch173():
    doc = {"elements": [{"type": None, "content": "A"},
                        {"content": "B"}], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_by_type"] == {
        "value": {None: 1, "unknown": 1}, "reason": None}


# ---------- docx 结构键值 None ----------

def test_docx_structural_key_none_value_valid_batch173():
    doc = {"elements": [
        {"type": "paragraph", "content": "A",
         "source_locator": {"section": None}}],
        "chunks": []}
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"] == {"value": 1.0,
                                               "reason": None}


# ---------- image content 不参与比对 ----------

def test_image_content_ignored_in_text_batch173():
    doc = {"elements": [{"type": "image", "content": "IMG"},
                        {"type": "paragraph", "content": "AB"}],
           "chunks": [{"text": "AB",
                       "source_element_ids": ["e2"]}]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["text_preservation_equal"] == {"value": True,
                                              "reason": None}
    assert out["text_char_multiset_precision"] == {"value": 1.0,
                                                   "reason": None}


# ---------- 仅 image + chunks text None ----------

def test_image_only_chunk_none_text_empty_both_batch173():
    doc = {"elements": [{"type": "image", "content": None}],
           "chunks": [{"text": None}]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["text_preservation_equal"] == {"value": True,
                                              "reason": None}
    assert out["text_char_multiset_precision"] == {
        "value": None,
        "reason": "empty_expected_and_actual"}
    assert out["text_char_multiset_recall"] == {
        "value": None,
        "reason": "empty_expected_and_actual"}


# ---------- expectations 字符串计数崩溃 ----------

def test_silent_drop_string_expectation_crashes_batch173():
    doc = {"elements": [{"type": "paragraph", "content": "A"}],
           "chunks": []}
    with pytest.raises(TypeError) as ei:
        compute_automatic_metrics(
            doc, None, "pdf",
            {"element_count_by_type": {"paragraph": "2"}})
    assert "'<' not supported between instances of " \
        "'int' and 'str'" in str(ei.value)


# ---------- 乱序：equal False 但 P/R 1.0 ----------

def test_reorder_equal_false_pr_one_batch173():
    doc = {"elements": [{"type": "paragraph", "content": "AB"}],
           "chunks": [{"text": "BA"}]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["text_preservation_equal"] == {"value": False,
                                              "reason": None}
    assert out["text_char_multiset_precision"] == {"value": 1.0,
                                                   "reason": None}
    assert out["text_char_multiset_recall"] == {"value": 1.0,
                                                "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch173():
    src = _src()
    assert "pipeline_success = error is None and document is not None" in src
    assert 'return "".join(ch for ch in s if not ch.isspace())' in src
    assert "common = sum((c_expected & c_actual).values())" in src
    assert "if isinstance(v, bool):" in src


# ---------- forbidden tokens 第四百四十五批 ----------

def test_source_no_eval_batch173():
    assert "eval(" not in _src()


def test_source_no_exec_batch173():
    assert "exec(" not in _src()


def test_source_no_compile_batch173():
    assert "compile(" not in _src()


def test_source_no_globals_batch173():
    assert "globals(" not in _src()


def test_source_no_locals_batch173():
    assert "locals(" not in _src()


def test_source_no_os_system_batch173():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch173():
    assert "subprocess" not in _src()


def test_source_no_popen_batch173():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch173():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch173():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch173():
    assert "socket" not in _src()


def test_source_no_requests_batch173():
    assert "requests" not in _src()


def test_source_no_urllib_batch173():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch173():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch173():
    assert "yield" not in _src()


def test_source_no_async_await_batch173():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch173():
    assert "open(" not in _src()
