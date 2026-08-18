"""evaluation/report.py 第五百六十一轮 edges 测试（Round 1208）。

补强 edges129 未触及的角度（第五百八十批，probe 实证）。

新角度（同 doc_id 不去重 / 数值不设防 / 壳形即失败）：
- **同 doc_id 不去重**——per_doc 两条
  同名 "dup" → counts 求和 7 / 计 2
  篇、success 1/2、ratio macro 0.75
  ——聚合只读 metrics，doc_id 仅是
  壳（首锁）
- **负值透传**——ect -3 → 求和 -3；
  ratio -0.5 → macro -0.5（无钳位、
  无下界校验首锁）
- **浮点 counts**——ect 4.7 → 求和
  4.7（无 int 强转）
- **壳形即失败**——pipeline_success
  直接给 {success_count, total, rate}
  dict（无 value 键）→ 按失败计 →
  {0, 2, 0.0}（包装契约：非真 value
  即 miss 首锁）
- **空 metrics 条目**——两条空壳 →
  四键 summary + success 0/2/0.0
- forbidden tokens 第六百七十八批（open 0，subprocess.run 2）
"""

from __future__ import annotations

import inspect

import evaluation.report as report_mod
from evaluation.report import aggregate_summary


def _entry(doc_id, **metrics):
    return {"doc_id": doc_id, "metrics": metrics}


def _v(value, reason=None):
    return {"value": value, "reason": reason}


# ---------- 同 doc_id 不去重 ----------

def test_dup_doc_ids_batch406():
    base = dict(
        element_count_total=_v(3),
        pdf_locator_valid_ratio=_v(0.5),
        silent_drop_count=_v(1),
    )
    r = aggregate_summary([
        _entry("dup", pipeline_success=_v(True), **base),
        _entry("dup", element_count_total=_v(4),
               pipeline_success=_v(False),
               pdf_locator_valid_ratio=_v(1.0),
               silent_drop_count=_v(None, "x")),
    ])
    assert r["counts"]["element_count_total"] == {
        "sum": 7, "participating_docs": 2}
    assert r["success_rates"]["pipeline_success"] == {
        "success_count": 1, "total": 2, "rate": 0.5}
    assert r["ratio_macro_averages"][
        "pdf_locator_valid_ratio"] == {
        "macro_average": 0.75, "participating_docs": 2,
        "not_evaluated": 0}
    assert r["silent_drop_total"] == 1


# ---------- 负值透传 ----------

def test_negative_values_batch406():
    r = aggregate_summary([
        _entry("n1", element_count_total=_v(-3),
               pdf_locator_valid_ratio=_v(-0.5)),
    ])
    assert r["counts"]["element_count_total"] == {
        "sum": -3, "participating_docs": 1}
    assert r["ratio_macro_averages"][
        "pdf_locator_valid_ratio"] == {
        "macro_average": -0.5, "participating_docs": 1,
        "not_evaluated": 0}


# ---------- 浮点 counts ----------

def test_float_counts_batch406():
    r = aggregate_summary([
        _entry("f1", element_count_total=_v(4.7)),
    ])
    assert r["counts"]["element_count_total"] == {
        "sum": 4.7, "participating_docs": 1}


# ---------- 壳形即失败 ----------

def test_shell_dict_is_miss_batch406():
    r = aggregate_summary([
        _entry("s1", pipeline_success={
            "success_count": 2, "total": 5, "rate": 0.9}),
        _entry("s2", pipeline_success={
            "success_count": 1, "total": 2, "rate": 0.5}),
    ])
    assert r["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 2, "rate": 0.0}


# ---------- 空 metrics 条目 ----------

def test_empty_metrics_entries_batch406():
    r = aggregate_summary([_entry("e1"), _entry("e2")])
    assert sorted(r.keys()) == ["counts",
                                "ratio_macro_averages",
                                "silent_drop_total",
                                "success_rates"]
    assert r["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 2, "rate": 0.0}
    assert r["silent_drop_total"] is None


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch406():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src


# ---------- forbidden tokens 第六百七十八批 ----------

def test_source_no_eval_batch406():
    assert "eval(" not in _src()


def test_source_no_exec_batch406():
    assert "exec(" not in _src()


def test_source_no_compile_batch406():
    assert "compile(" not in _src()


def test_source_no_globals_batch406():
    assert "globals(" not in _src()


def test_source_no_locals_batch406():
    assert "locals(" not in _src()


def test_source_no_os_system_batch406():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch406():
    assert ".call(" not in _src()


def test_source_no_popen_batch406():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch406():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch406():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch406():
    assert "socket" not in _src()


def test_source_no_requests_batch406():
    assert "requests" not in _src()


def test_source_no_urllib_batch406():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch406():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch406():
    assert "yield" not in _src()


def test_source_no_async_await_batch406():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch406():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch406():
    assert _src().count("subprocess.run") == 2
