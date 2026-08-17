"""evaluation/report.py 第三百九十三轮 edges 测试（Round 949）。

补强 edges104 未触及的角度（第三百二十五批，probe 实证）。

新角度：
- bool False 参与 ratio macro（不是 None 不过滤）：
  schema_valid [False, True] → macro 0.5 participating 2
- 同批里 null 值被过滤：pdf_locator [0.5, None] →
  macro 0.5 participating 1 not_evaluated 1
- 空 per_doc：rate {success_count 0, total 0, rate None}、
  counts {sum None, participating 0}、silent None、
  ratio 12 键全 None
- pipeline_success False → success_count 0 total 1 rate 0.0
- subprocess.run 抛 OSError → {"git_commit": None,
  "git_dirty": True} 兜底
- build_provenance max_chars "800" 字符串 → int 800；
  provenance 9 键有序
- get_dependency_versions 恰 3 键 [pdfplumber, python-docx,
  pypdfium2]，本环境全非 None
- silent_drop 混合 [2, None, 3] → 5；全 None → None
- _RATIO_METRICS 恰 12 项、figure_caption_* 不在内、
  首 3 项 [schema_valid, pdf_locator_valid_ratio,
  docx_locator_valid_ratio]；_COUNT/_SUCCESS 单项元组
- __all__ 5 项有序
- forbidden tokens 第四百一十九批（open 0 + subprocess.run 2）
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import patch

import evaluation.report as rpt
from evaluation.report import (
    aggregate_summary,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


# ---------- bool False 参与 macro ----------

def test_false_participates_in_macro_batch147():
    per = [{"metrics": {"schema_valid": {"value": False},
                        "pdf_locator_valid_ratio": {"value": 0.5}}},
           {"metrics": {"schema_valid": {"value": True},
                        "pdf_locator_valid_ratio": {
                            "value": None, "reason": "x"}}}]
    s = aggregate_summary(per)
    rma = s["ratio_macro_averages"]
    assert rma["schema_valid"] == {"macro_average": 0.5,
                                   "participating_docs": 2,
                                   "not_evaluated": 0}
    assert rma["pdf_locator_valid_ratio"] == {
        "macro_average": 0.5, "participating_docs": 1,
        "not_evaluated": 1}


# ---------- 空 per_doc ----------

def test_empty_per_doc_shapes_batch147():
    s = aggregate_summary([])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 0, "rate": None}
    assert s["counts"]["element_count_total"] == {
        "sum": None, "participating_docs": 0}
    assert s["silent_drop_total"] is None
    assert len(s["ratio_macro_averages"]) == 12
    assert all(v["macro_average"] is None
               for v in s["ratio_macro_averages"].values())


# ---------- pipeline False → rate 0.0 ----------

def test_pipeline_false_rate_zero_batch147():
    per = [{"metrics": {"pipeline_success": {"value": False}}}]
    assert aggregate_summary(per)["success_rates"][
        "pipeline_success"] == {"success_count": 0, "total": 1,
                                "rate": 0.0}


# ---------- OSError 兜底 ----------

def test_git_oserror_fallback_batch147():
    with patch.object(rpt.subprocess, "run",
                      side_effect=OSError("no git")):
        assert get_git_provenance(Path(".")) == {
            "git_commit": None, "git_dirty": True}


# ---------- max_chars 强转 int ----------

def test_build_provenance_max_chars_coerce_batch147():
    with patch.object(rpt, "get_git_provenance",
                      return_value={"git_commit": "c",
                                    "git_dirty": False}):
        p = build_provenance(Path("."), "fallback", "800", None)
    assert p["max_chars"] == 800
    assert isinstance(p["max_chars"], int)
    assert list(p) == ["git_commit", "git_dirty",
                       "evaluator_version", "report_version",
                       "parser_name", "parser_version",
                       "dependencies", "max_chars",
                       "run_timestamp_iso"]


# ---------- 依赖版本 ----------

def test_dependency_versions_three_keys_batch147():
    d = get_dependency_versions()
    assert list(d) == ["pdfplumber", "python-docx", "pypdfium2"]
    assert all(isinstance(v, str) and v for v in d.values())


# ---------- silent_drop 混合 ----------

def test_silent_mixed_and_all_none_batch147():
    per = [{"metrics": {"silent_drop_count": {"value": 2}}},
           {"metrics": {"silent_drop_count": {
               "value": None, "reason": "r"}}},
           {"metrics": {"silent_drop_count": {"value": 3}}}]
    assert aggregate_summary(per)["silent_drop_total"] == 5
    per2 = [{"metrics": {"silent_drop_count": {"value": None}}}]
    assert aggregate_summary(per2)["silent_drop_total"] is None


# ---------- 元组形状 ----------

def test_ratio_tuple_shape_batch147():
    assert len(rpt._RATIO_METRICS) == 12
    assert "figure_caption_precision" not in rpt._RATIO_METRICS
    assert "figure_caption_recall" not in rpt._RATIO_METRICS
    assert "element_count_total" not in rpt._RATIO_METRICS
    assert rpt._RATIO_METRICS[:3] == (
        "schema_valid", "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio")
    assert rpt._COUNT_METRICS == ("element_count_total",)
    assert rpt._SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_all_five_ordered_batch147():
    assert rpt.__all__ == [
        "build_provenance", "build_devset_section",
        "aggregate_summary", "get_git_provenance",
        "get_dependency_versions"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(rpt)


def test_source_key_lines_batch147():
    src = _src()
    assert 'if r["metrics"].get(name, {}).get("value") is True' in src
    assert "rate = (successes / total) if total else None" in src
    assert "macro = sum(values) / len(values)" in src
    assert 'summary["silent_drop_total"] = sum(silent_vals) if silent_vals else None' in src


# ---------- forbidden tokens 第四百一十九批 ----------

def test_source_no_eval_batch147():
    assert "eval(" not in _src()


def test_source_no_exec_batch147():
    assert "exec(" not in _src()


def test_source_no_compile_batch147():
    assert "compile(" not in _src()


def test_source_no_globals_batch147():
    assert "globals(" not in _src()


def test_source_no_locals_batch147():
    assert "locals(" not in _src()


def test_source_no_os_system_batch147():
    assert "os.system" not in _src()


def test_source_no_subprocess_token_batch147():
    # report 自身 import subprocess（git 调用），只约束不出现
    # 该字符串拼接以外的危险用法由 run 计数管
    src = _src()
    assert "subprocess.Popen" not in src
    assert "subprocess.call" not in src


def test_source_no_popen_batch147():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch147():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch147():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch147():
    assert "socket" not in _src()


def test_source_no_requests_batch147():
    assert "requests" not in _src()


def test_source_no_urllib_batch147():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch147():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch147():
    assert "yield" not in _src()


def test_source_no_async_await_batch147():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch147():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch147():
    assert _src().count("subprocess.run") == 2
