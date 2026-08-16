"""evaluation/metrics.py 第二百零九轮 edges 测试（Round 765）。

补强 edges83-87 未触及的角度（第一百二十九批）。

新角度：
- resource_path 指向已存在目录 → is_file() False → 0.0（不计有效）
- source_element_ids 用元组 ("e1",) 与列表同待遇 → 1.0（all() 不挑类型）
- 未守卫 TypeError 家族：content 传 int、chunk text 传 int（≥2 chunk）、
  elements 键显式 None（len）、expectations 计数传字符串 "2"（str 与 int
  比较失败）
- source_type "txt"：pdf/docx 两指标同时 null（not_pdf_document /
  not_docx_document 各自 reason，第三种文档类型双不适用）
- element 无 source_locator 键 → loc={} → page None → 0.0
- DOCX locator 同时带 relationship_id 与 page → page 键存在优先拒
- bbox 单元素 bool（[1, True, 3, 4]）→ 第二元素拒绝整条
- forbidden tokens 第二百三十五批
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import pytest

from evaluation.metrics import compute_automatic_metrics


def _doc(elements, chunks=()):
    return {"elements": list(elements), "chunks": list(chunks)}


# ---------- resource_path 目录 ----------

def test_resource_path_directory_invalid_batch54():
    tmp = Path(tempfile.mkdtemp())
    d = _doc([{"type": "image", "resource_path": str(tmp)}])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["image_resource_exists_ratio"] == {"value": 0.0,
                                                  "reason": None}


# ---------- 元组 ids ----------

def test_tuple_source_element_ids_accepted_batch54():
    d = _doc([{"element_id": "e1", "type": "paragraph", "content": "a"}],
             [{"text": "a", "source_element_ids": ("e1",)}])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"] == {"value": 1.0,
                                                   "reason": None}


# ---------- 未守卫 TypeError 家族 ----------

def test_content_int_typeerror_batch54():
    with pytest.raises(TypeError):
        compute_automatic_metrics(
            _doc([{"type": "paragraph", "content": 5}]), None, "pdf", None)


def test_chunk_text_int_typeerror_batch54():
    with pytest.raises(TypeError):
        compute_automatic_metrics(
            _doc([], [{"text": 5}, {"text": "a"}]), None, "pdf", None)


def test_elements_key_none_typeerror_batch54():
    with pytest.raises(TypeError):
        compute_automatic_metrics({"elements": None, "chunks": []},
                                  None, "pdf", None)


def test_expectations_string_count_typeerror_batch54():
    with pytest.raises(TypeError):
        compute_automatic_metrics(
            _doc([{"type": "paragraph"}]), None, "pdf",
            {"element_count_by_type": {"paragraph": "2"}})


# ---------- source_type txt ----------

def test_txt_source_both_locators_null_batch54():
    out = compute_automatic_metrics(_doc([]), None, "txt", None)
    assert out["pdf_locator_valid_ratio"] == {
        "value": None, "reason": "not_pdf_document"}
    assert out["docx_locator_valid_ratio"] == {
        "value": None, "reason": "not_docx_document"}


# ---------- locator 形态 ----------

def test_element_without_locator_key_invalid_batch54():
    out = compute_automatic_metrics(_doc([{"type": "paragraph"}]),
                                    None, "pdf", None)
    assert out["pdf_locator_valid_ratio"] == {"value": 0.0, "reason": None}


def test_docx_page_beats_relationship_id_batch54():
    d = _doc([{"type": "paragraph",
               "source_locator": {"relationship_id": "r", "page": 1}}])
    out = compute_automatic_metrics(d, None, "docx", None)
    assert out["docx_locator_valid_ratio"] == {"value": 0.0, "reason": None}


def test_bbox_single_bool_element_rejects_batch54():
    d = _doc([{"type": "paragraph",
               "source_locator": {"page": 1, "bbox": [1, True, 3, 4]}}])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"] == {"value": 0.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    import evaluation.metrics as m
    return inspect.getsource(m)


def test_source_guard_lines_batch54():
    src = _src()
    assert "isinstance(v, bool):" in src
    assert 'e.get("source_locator") or {}' in src
    assert '"page" in loc or "bbox" in loc' in src


# ---------- forbidden tokens 第二百三十五批 ----------

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
