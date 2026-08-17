"""evaluation/report.py 第二百三十二轮 edges 测试（Round 788）。

补强 edges80-81 未触及的角度（第一百五十二批）。

新角度：
- _RATIO_METRICS 全 12 元组按序锁定（figure_caption_* 不在列）；
  _COUNT_METRICS 单元素、_SUCCESS_BOOL_METRICS 单元素
- get_dependency_versions 真实冒烟：恰 3 键、值为 str/None、
  pdfplumber 已装（读 importlib.metadata，不 mock）
- per_doc 结果缺 "metrics" 键 → KeyError('metrics') 直接传播
  （r["metrics"] 直索引，runner 侧恒提供，直接调用可崩）
- 空列表四段合并：counts sum None/0、rate None、ratio 行
  {None, 0, 0}（not_evaluated = 0-0）、silent_drop_total None
- 缺指标键与 null 值都算 not_evaluated：3 docs（1 参与 + null +
  空 metrics）→ participating 1 / not_evaluated 2 / macro 1.0
- forbidden tokens 第二百五十八批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.report as report_mod
from evaluation.report import (
    _COUNT_METRICS,
    _RATIO_METRICS,
    _SUCCESS_BOOL_METRICS,
    aggregate_summary,
    get_dependency_versions,
)

_RATIO_NAMES = (
    "schema_valid", "pdf_locator_valid_ratio",
    "docx_locator_valid_ratio", "image_resource_exists_ratio",
    "chunk_reference_intact_ratio", "text_preservation_equal",
    "text_char_multiset_precision", "text_char_multiset_recall",
    "heading_boundary_compliance", "chunk_boundary_precision",
    "chunk_boundary_recall", "chunk_boundary_f1",
)


# ---------- 常量元组 ----------

def test_ratio_metrics_tuple_locked_batch54():
    assert _RATIO_METRICS == _RATIO_NAMES
    assert "figure_caption_precision" not in _RATIO_METRICS


def test_count_and_success_tuples_batch54():
    assert _COUNT_METRICS == ("element_count_total",)
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


# ---------- 真实依赖版本 ----------

def test_dependency_versions_real_smoke_batch54():
    v = get_dependency_versions()
    assert list(v.keys()) == ["pdfplumber", "python-docx", "pypdfium2"]
    assert all(isinstance(x, str) or x is None for x in v.values())
    assert v["pdfplumber"] is not None


# ---------- 缺 metrics 键 ----------

def test_missing_metrics_key_raises_batch54():
    with pytest.raises(KeyError, match="'metrics'"):
        aggregate_summary([{"doc_id": "x"}])


# ---------- 空列表四段 ----------

def test_empty_input_all_sections_batch54():
    out = aggregate_summary([])
    assert out["counts"] == {
        "element_count_total": {"sum": None, "participating_docs": 0}}
    assert out["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 0, "rate": None}
    assert out["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 0}
    assert out["silent_drop_total"] is None


# ---------- 缺键与 null 同算 not_evaluated ----------

def test_missing_key_counts_not_evaluated_batch54():
    out = aggregate_summary([
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
        {"metrics": {}},
    ])
    row = out["ratio_macro_averages"]["schema_valid"]
    assert row == {"macro_average": 1.0, "participating_docs": 1,
                   "not_evaluated": 2}


# ---------- ratio 键序行为锁 ----------

def test_ratio_section_key_order_batch54():
    out = aggregate_summary([])
    assert list(out["ratio_macro_averages"].keys()) == list(_RATIO_NAMES)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_aggregate_lines_batch54():
    src = _src()
    assert 'r["metrics"].get(name, {}).get("value")' in src
    assert "not_eval = len(per_doc_results) - len(values)" in src
    assert 'if r["metrics"].get(name, {}).get("value") is True' in src


# ---------- forbidden tokens 第二百五十八批 ----------

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


def test_source_subprocess_run_count_two_batch54():
    assert _src().count("subprocess.run") == 2


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
