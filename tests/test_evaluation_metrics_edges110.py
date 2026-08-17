"""evaluation/metrics.py 第三百七十轮 edges 测试（Round 926）。

补强 edges109 未触及的角度（第三百零二批，probe 实证）。

新角度：
- _strip_unicode_whitespace 控制字符分区：\\x1c/\\x1f
  （Python isspace 为 True）被删，但 \\x00 保留——
  "a\\x1cb\\x00c\\x1fde" → "ab\\x00cde"
- 四个构造器直测：_ratio(True)→1.0 float、_int_metric(3.9)
  →3 截断、_bool_metric(1)→True / ("")→False、_null 原样
- heading 集 合语义：两 chunk 首 id 同为 h1 → 仍 1.0
  （set 去重）；双 heading 一中一失 → 0.5
- type "Image" 大写不识别 → no_image_elements
- elements 空 + chunk 引用 e1 → 0.0（空集合不命中）
- expectations 含 ghost_type → 按实际 0 计入 drop 2
  （未知类型视为全丢）
- document 传 list → AttributeError（dict 契约）
- forbidden tokens 第三百九十六批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import (
    _bool_metric,
    _int_metric,
    _null,
    _ratio,
    _strip_unicode_whitespace,
    compute_automatic_metrics,
)


def _run(doc, st="pdf", exp=None):
    return compute_automatic_metrics(doc, None, st, exp)


# ---------- 控制字符分区 ----------

def test_strip_control_chars_batch124():
    s = "a\x1cb\x00c\x1fde"
    assert _strip_unicode_whitespace(s) == "ab\x00cde"


# ---------- 构造器直测 ----------

def test_ratio_bool_coerces_float_batch124():
    out = _ratio(True)
    assert out == {"value": 1.0, "reason": None}
    assert isinstance(out["value"], float)


def test_int_metric_truncates_batch124():
    assert _int_metric(3.9) == {"value": 3, "reason": None}


def test_bool_metric_truthiness_batch124():
    assert _bool_metric(1) == {"value": True, "reason": None}
    assert _bool_metric("") == {"value": False, "reason": None}


def test_null_passthrough_batch124():
    assert _null("r") == {"value": None, "reason": "r"}


# ---------- heading set 语义 ----------

def test_duplicate_first_ids_dedup_batch124():
    doc = {"elements": [{"element_id": "h1", "type": "heading",
                         "content": "H"}],
           "chunks": [
               {"text": "H", "source_element_ids": ["h1"]},
               {"text": "x", "source_element_ids": ["h1"]}]}
    assert _run(doc)["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


def test_two_headings_half_batch124():
    doc = {"elements": [
        {"element_id": "h1", "type": "heading", "content": "A"},
        {"element_id": "h2", "type": "heading", "content": "B"}],
        "chunks": [
            {"text": "A", "source_element_ids": ["h1"]},
            {"text": "x", "source_element_ids": ["e9"]}]}
    assert _run(doc)["heading_boundary_compliance"] == {
        "value": 0.5, "reason": None}


# ---------- type 大小写 ----------

def test_capitalized_image_type_null_batch124():
    doc = {"elements": [{"type": "Image",
                         "resource_path": "x.png"}],
           "chunks": []}
    assert _run(doc)["image_resource_exists_ratio"] == {
        "value": None, "reason": "no_image_elements"}


# ---------- 空 elements 引用 ----------

def test_empty_elements_no_hit_batch124():
    doc = {"elements": [],
           "chunks": [{"text": "A",
                       "source_element_ids": ["e1"]}]}
    assert _run(doc)["chunk_reference_intact_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- expectations 未知类型 ----------

def test_expectation_ghost_type_drops_batch124():
    doc = {"elements": [{"element_id": "e1", "type": "paragraph",
                         "content": "A"}],
           "chunks": []}
    out = _run(doc, exp={"element_count_by_type": {
        "ghost_type": 2}})
    assert out["silent_drop_count"] == {"value": 2,
                                        "reason": None}


# ---------- document 非字典 ----------

def test_document_list_attribute_error_batch124():
    with pytest.raises(AttributeError):
        _run(["not", "dict"])


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch124():
    src = _src()
    assert 'return "".join(ch for ch in s if not ch.isspace())' in src
    assert 'metrics["error_code"] = (' in src
    assert "elem_ids = {e.get(\"element_id\") for e in elements}" in src
    assert 'images = [e for e in elements if e.get("type") == "image"]' in src


# ---------- forbidden tokens 第三百九十六批 ----------

def test_source_no_eval_batch124():
    assert "eval(" not in _src()


def test_source_no_exec_batch124():
    assert "exec(" not in _src()


def test_source_no_compile_batch124():
    assert "compile(" not in _src()


def test_source_no_globals_batch124():
    assert "globals(" not in _src()


def test_source_no_locals_batch124():
    assert "locals(" not in _src()


def test_source_no_os_system_batch124():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch124():
    assert "subprocess" not in _src()


def test_source_no_popen_batch124():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch124():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch124():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch124():
    assert "socket" not in _src()


def test_source_no_requests_batch124():
    assert "requests" not in _src()


def test_source_no_urllib_batch124():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch124():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch124():
    assert "yield" not in _src()


def test_source_no_async_await_batch124():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch124():
    assert "open(" not in _src()
