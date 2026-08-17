"""evaluation/report.py 第五百三十九轮 edges 测试（Round 1095）。

补强 edges123-125 未触及的角度（第四百七十一批，probe 实证）。

新角度（aggregate_summary 单元缝：False 的双重身份 +
null/缺席不可辨 + 名册门禁）：
- **False 入宏作 0**：text_preservation_equal
  [1.0, False] → macro 0.5 / participating 2 ——bool
  False 不是 null，作为数值 0 进算术平均（与
  not_evaluated 的 null 语义分道）
- **null 与缺席不可辨**：[0.5 有值, null 带 reason,
  键整缺] → {0.5, 1, 2}——null-value 与 absent-key
  在 not_evaluated 里合并同一格
- **未知指标键被无视**：bogus_metric=5 → counts /
  success_rates / ratio 三区全不见——聚合按名册
  （_RATIO/_COUNT/_SUCCESS）门禁，不透传自定义键
- **False 双重身份**：单文档 pipeline_success=False +
  schema_valid=False → success {0, 1, 0.0} 且 ratio
  {0.0, 1, 0}——同一个 False 同时入两本账
- **参与度算术**：5 文档 [None, 0.25, 缺, 1.0, None]
  → macro 0.625 / participating 2 / not_evaluated 3
- forbidden tokens 第五百六十六批（report 变体：15 项
  去 subprocess + open 0 + subprocess.run 计 2）
"""

from __future__ import annotations

import inspect

import evaluation.report as report_mod
from evaluation.report import aggregate_summary


def _m(**kw):
    return {"metrics": {k: {"value": v, "reason": None}
                        for k, v in kw.items()}}


# ---------- False 入宏作 0 ----------

def test_false_joins_macro_as_zero_batch294():
    out = aggregate_summary([_m(text_preservation_equal=1.0),
                             _m(text_preservation_equal=False)])
    assert out["ratio_macro_averages"][
        "text_preservation_equal"] == {
        "macro_average": 0.5, "participating_docs": 2,
        "not_evaluated": 0}


# ---------- null 与缺席不可辨 ----------

def test_null_vs_absent_indistinguishable_batch294():
    out = aggregate_summary([
        _m(chunk_boundary_f1=0.5),
        _m(chunk_boundary_f1=None),
        _m()])
    assert out["ratio_macro_averages"][
        "chunk_boundary_f1"] == {
        "macro_average": 0.5, "participating_docs": 1,
        "not_evaluated": 2}


# ---------- 未知指标键被无视 ----------

def test_bogus_metric_key_ignored_batch294():
    out = aggregate_summary([_m(bogus_metric=5,
                                element_count_total=3)])
    assert out["counts"] == {
        "element_count_total": {
            "sum": 3, "participating_docs": 1}}
    flat = (set(out["success_rates"])
            | set(out["ratio_macro_averages"]))
    assert "bogus_metric" not in flat


# ---------- False 双重身份 ----------

def test_false_double_ledger_batch294():
    out = aggregate_summary([
        _m(pipeline_success=False, schema_valid=False)])
    assert out["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 1, "rate": 0.0}
    assert out["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 0.0, "participating_docs": 1,
        "not_evaluated": 0}


# ---------- 参与度算术 ----------

def test_partition_arithmetic_batch294():
    out = aggregate_summary([
        _m(chunk_boundary_precision=None),
        _m(chunk_boundary_precision=0.25),
        _m(),
        _m(chunk_boundary_precision=1.0),
        _m(chunk_boundary_precision=None)])
    assert out["ratio_macro_averages"][
        "chunk_boundary_precision"] == {
        "macro_average": 0.625, "participating_docs": 2,
        "not_evaluated": 3}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch294():
    src = _src()
    assert 'summary["success_rates"] = success_rates' in src
    assert ('summary["ratio_macro_averages"] '
            '= ratio_avgs') in src


# ---------- forbidden tokens 第五百六十六批（report 变体）----------

def test_source_no_eval_batch294():
    assert "eval(" not in _src()


def test_source_no_exec_batch294():
    assert "exec(" not in _src()


def test_source_no_compile_batch294():
    assert "compile(" not in _src()


def test_source_no_globals_batch294():
    assert "globals(" not in _src()


def test_source_no_locals_batch294():
    assert "locals(" not in _src()


def test_source_no_os_system_batch294():
    assert "os.system" not in _src()


def test_source_no_popen_batch294():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch294():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch294():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch294():
    assert "socket" not in _src()


def test_source_no_requests_batch294():
    assert "requests" not in _src()


def test_source_no_urllib_batch294():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch294():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch294():
    assert "yield" not in _src()


def test_source_no_async_await_batch294():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch294():
    assert _src().count("open(") == 0


def test_source_subprocess_run_count_is_2_batch294():
    assert _src().count("subprocess.run") == 2
