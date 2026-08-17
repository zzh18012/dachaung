"""evaluation/metrics.py 第三百四十九轮 edges 测试（Round 905）。

补强 edges106 未触及的角度（第二百八十一批，probe 实证）。

新角度：
- pdf locator page=True（bool 是 int 子类）→ 有效 1.0；
  page=1.0（float 非 int）→ 无效 0.0
- docx structural 键存在即可（paragraph_index=None → 1.0）
- chunk source_element_ids 传字符串 "e1" → 按字符迭代
  "e"/"1" 不在集合 → 0.0
- element content 为 int 5 → "".join TypeError 未防护
- chunk source_element_ids None → heading_boundary 0.0
  （ids or [] → 空）
- forbidden tokens 第三百七十五批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _el(eid, etype, **kw):
    d = {"element_id": eid, "type": etype, "content": "A"}
    d.update(kw)
    return d


# ---------- pdf page 类型怪癖 ----------

def test_pdf_page_bool_true_valid_batch103():
    doc = {"elements": [_el("e1", "image",
                            source_locator={"page": True})],
           "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


def test_pdf_page_float_invalid_batch103():
    doc = {"elements": [_el("e1", "image",
                            source_locator={"page": 1.0})],
           "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pdf_locator_valid_ratio"] == {"value": 0.0,
                                            "reason": None}


# ---------- docx 键存在性 ----------

def test_docx_structural_key_none_value_batch103():
    doc = {"elements": [_el(
        "e1", "paragraph",
        source_locator={"paragraph_index": None})],
        "chunks": []}
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["docx_locator_valid_ratio"] == {"value": 1.0,
                                             "reason": None}


# ---------- ids 字符串 ----------

def test_chunk_ref_ids_string_iterates_chars_batch103():
    doc = {"elements": [_el("e1", "paragraph")],
           "chunks": [{"text": "A",
                       "source_element_ids": "e1"}]}
    m = compute_automatic_metrics(doc, None, "text", None)
    assert m["chunk_reference_intact_ratio"] == {"value": 0.0,
                                                 "reason": None}


# ---------- content int ----------

def test_content_int_typeerror_batch103():
    doc = {"elements": [{"element_id": "e1", "type": "paragraph",
                         "content": 5}],
           "chunks": [{"text": "A",
                       "source_element_ids": ["e1"]}]}
    with pytest.raises(TypeError):
        compute_automatic_metrics(doc, None, "text", None)


# ---------- heading ids None ----------

def test_heading_chunk_ids_none_batch103():
    doc = {"elements": [_el("h1", "heading")],
           "chunks": [{"text": "A",
                       "source_element_ids": None}]}
    m = compute_automatic_metrics(doc, None, "text", None)
    assert m["heading_boundary_compliance"] == {"value": 0.0,
                                                "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch103():
    src = _src()
    assert "if not isinstance(page, int) or page < 1:" in src
    assert 'if not any(k in loc for k in structural_keys):' in src
    assert "if ids and all(sid in elem_ids for sid in ids):" in src
    assert "if not _is_valid_bbox(bbox):" in src


# ---------- forbidden tokens 第三百七十五批 ----------

def test_source_no_eval_batch103():
    assert "eval(" not in _src()


def test_source_no_exec_batch103():
    assert "exec(" not in _src()


def test_source_no_compile_batch103():
    assert "compile(" not in _src()


def test_source_no_globals_batch103():
    assert "globals(" not in _src()


def test_source_no_locals_batch103():
    assert "locals(" not in _src()


def test_source_no_os_system_batch103():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch103():
    assert "subprocess" not in _src()


def test_source_no_popen_batch103():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch103():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch103():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch103():
    assert "socket" not in _src()


def test_source_no_requests_batch103():
    assert "requests" not in _src()


def test_source_no_urllib_batch103():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch103():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch103():
    assert "yield" not in _src()


def test_source_no_async_await_batch103():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch103():
    assert "open(" not in _src()
