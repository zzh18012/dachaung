"""evaluation/metrics.py 第四百一十二轮 edges 测试（Round 968）。

补强 edges115 未触及的角度（第三百四十四批，probe 实证）。

新角度：
- 元素缺 source_locator 键 → `or {}` 兜底 → 无效 →
  pdf/docx locator 均 0.0
- error 与 document 并存怪癖：success False +
  error_code E_PARSE，但 `if document is None` 门通过
  → schema_valid 照算（此处 False）、
  element_count_total 照算（1）——错误不阻断下游指标
- expectations {} → null no_expectations；
  element_count_by_type {} → null
  no_expectations_element_count（两级空两种 reason）
- 超额计数不为负：actual 2 vs expected 1 → 0
- forbidden tokens 第四百三十八批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _run(doc, err=None, st="pdf", exp=None):
    return compute_automatic_metrics(doc, err, st, exp)


# ---------- 缺 source_locator ----------

def test_missing_locator_zero_both_batch166():
    doc = {"elements": [{"type": "paragraph",
                         "content": "A"}], "chunks": []}
    assert _run(doc)["pdf_locator_valid_ratio"] == {
        "value": 0.0, "reason": None}
    assert _run(doc, st="docx")[
        "docx_locator_valid_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- error 与 document 并存 ----------

def test_error_and_document_coexist_batch166():
    doc = {"elements": [{"type": "paragraph",
                         "content": "A"}], "chunks": []}
    m = _run(doc, err={"code": "E_PARSE", "message": "x"})
    assert m["pipeline_success"] == {"value": False,
                                     "reason": None}
    assert m["error_code"] == {"value": "E_PARSE",
                               "reason": None}
    assert m["schema_valid"] == {"value": False,
                                 "reason": None}
    assert m["element_count_total"] == {"value": 1,
                                        "reason": None}
    assert m["element_count_by_type"]["value"] == {
        "paragraph": 1}


# ---------- expectations 两级空 ----------

def test_empty_expectations_two_levels_batch166():
    doc = {"elements": [{"type": "paragraph",
                         "content": "A"}], "chunks": []}
    assert _run(doc, exp={})["silent_drop_count"] == {
        "value": None, "reason": "no_expectations"}
    assert _run(doc, exp={
        "element_count_by_type": {}})[
        "silent_drop_count"] == {
        "value": None,
        "reason": "no_expectations_element_count"}


# ---------- 超额不为负 ----------

def test_overcount_zero_batch166():
    doc = {"elements": [
        {"type": "paragraph", "content": "A"},
        {"type": "paragraph", "content": "B"}],
        "chunks": []}
    assert _run(doc, exp={
        "element_count_by_type": {"paragraph": 1}})[
        "silent_drop_count"] == {"value": 0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch166():
    src = _src()
    assert "pipeline_success = error is None and document is not None" in src
    assert "if document is None:" in src
    assert "if not expectations:" in src
    assert "if not expected_counts:" in src


# ---------- forbidden tokens 第四百三十八批 ----------

def test_source_no_eval_batch166():
    assert "eval(" not in _src()


def test_source_no_exec_batch166():
    assert "exec(" not in _src()


def test_source_no_compile_batch166():
    assert "compile(" not in _src()


def test_source_no_globals_batch166():
    assert "globals(" not in _src()


def test_source_no_locals_batch166():
    assert "locals(" not in _src()


def test_source_no_os_system_batch166():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch166():
    assert "subprocess" not in _src()


def test_source_no_popen_batch166():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch166():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch166():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch166():
    assert "socket" not in _src()


def test_source_no_requests_batch166():
    assert "requests" not in _src()


def test_source_no_urllib_batch166():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch166():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch166():
    assert "yield" not in _src()


def test_source_no_async_await_batch166():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch166():
    assert "open(" not in _src()
