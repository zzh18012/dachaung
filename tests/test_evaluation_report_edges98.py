"""evaluation/report.py 第三百四十四轮 edges 测试（Round 900）。

补强 edges97 未触及的角度（第二百七十六批，probe 实证）。

新角度：
- 真实环境三依赖全已安装（非空 str；pdfplumber/python-docx/
  pypdfium2）
- 真实非 git 目录 → {git_commit: None, git_dirty: False}
- aggregate_summary([]) 全形状精确锁定（含顶层键序、
  ratio 组 12 项及其首三项顺序）
- success 值为字符串 "true" 不计数（is True 严格）→ rate 0.0
- ratio 3 文档仅 1 值 → participating 1 / not_evaluated 2
- build_provenance 键序九项
- forbidden tokens 第三百七十批（report 变体：subprocess.run 计 2）
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation.report import (
    aggregate_summary,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


def _pd(metrics):
    return {"metrics": metrics}


def _m(name, value):
    return {name: {"value": value, "reason": None}}


# ---------- 真实依赖 ----------

def test_dependency_versions_real_installed_batch98():
    v = get_dependency_versions()
    for pkg in ("pdfplumber", "python-docx", "pypdfium2"):
        assert isinstance(v[pkg], str), pkg
        assert v[pkg] != "", pkg


# ---------- 真实非 git 目录 ----------

def test_non_git_dir_provenance_batch98(tmp_path):
    out = get_git_provenance(tmp_path)
    assert out == {"git_commit": None, "git_dirty": False}


# ---------- 空聚合全形状 ----------

def test_empty_aggregate_full_shape_batch98():
    s = aggregate_summary([])
    assert list(s) == ["counts", "success_rates",
                       "ratio_macro_averages",
                       "silent_drop_total"]
    assert s["counts"] == {
        "element_count_total": {"sum": None,
                                "participating_docs": 0}}
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 0, "rate": None}
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 0}
    assert s["silent_drop_total"] is None


def test_ratio_group_twelve_and_order_batch98():
    s = aggregate_summary([])
    rg = s["ratio_macro_averages"]
    assert len(rg) == 12
    assert list(rg)[:3] == ["schema_valid", "pdf_locator_valid_ratio",
                            "docx_locator_valid_ratio"]


# ---------- 字符串 "true" 不计数 ----------

def test_success_string_true_not_counted_batch98():
    s = aggregate_summary([_pd(_m("pipeline_success", "true"))])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 1, "rate": 0.0}


# ---------- not_evaluated 计数 ----------

def test_ratio_not_evaluated_count_batch98():
    s = aggregate_summary([
        _pd(_m("schema_valid", 1.0)),
        _pd({}),
        _pd(_m("schema_valid", None)),
    ])
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 2}


# ---------- provenance 键序 ----------

def test_provenance_key_order_batch98(tmp_path):
    with patch.object(report_mod, "get_git_provenance",
                      return_value={"git_commit": None,
                                    "git_dirty": False}), \
         patch.object(report_mod, "get_dependency_versions",
                      return_value={}):
        p = build_provenance(tmp_path, "fallback", 800, None)
    assert list(p) == [
        "git_commit", "git_dirty", "evaluator_version",
        "report_version", "parser_name", "parser_version",
        "dependencies", "max_chars", "run_timestamp_iso",
    ]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch98():
    src = _src()
    assert 'for pkg in ("pdfplumber", "python-docx", "pypdfium2"):' in src
    assert 'dirty = bool(r2.returncode == 0 and r2.stdout.strip())' in src
    assert '"rate": rate,' in src


# ---------- forbidden tokens 第三百七十批（report 变体）----------

def test_source_no_eval_batch98():
    assert "eval(" not in _src()


def test_source_no_exec_batch98():
    assert "exec(" not in _src()


def test_source_no_compile_batch98():
    assert "compile(" not in _src()


def test_source_no_globals_batch98():
    assert "globals(" not in _src()


def test_source_no_locals_batch98():
    assert "locals(" not in _src()


def test_source_no_os_system_batch98():
    assert "os.system" not in _src()


def test_source_subprocess_run_count_is_2_batch98():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch98():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch98():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch98():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch98():
    assert "socket" not in _src()


def test_source_no_requests_batch98():
    assert "requests" not in _src()


def test_source_no_urllib_batch98():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch98():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch98():
    assert "yield" not in _src()


def test_source_no_async_await_batch98():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch98():
    assert "open(" not in _src()
