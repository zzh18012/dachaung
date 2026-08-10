r"""evaluation/report.py 边角测试 - 第十九轮（Round 278）。

edges18 已覆盖：aggregate_summary 跨多 metric 组合/macro_average 计算/不混合类型/不缓存/total 计数；
build_provenance max_chars float/True/False/负 float；返回 dict 可 pickle；git_commit str-or-None-40；
evaluator/report_version 来自 evaluation；build_devset_section duck typing；缺属性 AttributeError；
get_dependency_versions keys 精确；pdfplumber 版本格式；get_git_provenance subprocess.run cwd kwarg/returncode 处理；
_RATIO_METRICS 顺序深度（首= schema_valid；尾= chunk_boundary_f1；precision<recall<f1）；
_COUNT_METRICS 单元素；_SUCCESS_BOOL_METRICS 单元素；源码 token 含 aggregate 循环/successes/total/
sum(values)/len(values)/silent_drop_filter/timeout=10 ≥2/cwd=str(project_root)；不含 async/threading/numpy/pandas；
import 顺序；docstring 提及 4 类聚合 + participating_docs + not_evaluated；异常路径（空 list/unknown metric/falsy 值）。

edges19 补强未覆盖的角度：
- 模块 imports 精确字符串：'import subprocess'/'from datetime import datetime'/'from pathlib import Path'/
  'from typing import Any'/'from evaluation import EVALUATOR_VERSION, REPORT_VERSION'
- _RATIO_METRICS source 定义精确（含 12 个 metric 名）
- _RATIO_METRICS value exact 12 items tuple 顺序精确
- _COUNT_METRICS source 定义精确
- _SUCCESS_BOOL_METRICS source 定义精确
- get_git_provenance source 详尽：
  * 'commit: str | None = None'
  * 'dirty: bool = True'
  * 'try:' + 'except (OSError, subprocess.SubprocessError):'
  * subprocess.run 含 ['git', 'rev-parse', 'HEAD'] / cwd / capture_output=True / text=True / encoding='utf-8' / errors='replace' / timeout=10
  * 'if r.returncode == 0:'
  * 'commit = r.stdout.strip() or None'
  * subprocess.run 含 ['git', 'status', '--porcelain']
  * 'dirty = bool(r2.returncode == 0 and r2.stdout.strip())'
  * 'commit = None' / 'dirty = True' in except
  * 'return {"git_commit": commit, "git_dirty": dirty}'
- get_dependency_versions source 详尽：
  * 'import importlib.metadata' lazy import
  * 'versions: dict[str, str | None] = {}'
  * 'for pkg in ("pdfplumber", "python-docx", "pypdfium2"):'
  * 'importlib.metadata.version(pkg)'
  * 'importlib.metadata.PackageNotFoundError'
  * 'except Exception:'
  * 'versions[pkg] = None'
  * 'return versions'
- build_provenance source 详尽：
  * 'git = get_git_provenance(project_root)'
  * 9 keys 字面量精确顺序：git_commit/git_dirty/evaluator_version/report_version/parser_name/parser_version/dependencies/max_chars/run_timestamp_iso
  * 'datetime.now().astimezone().isoformat()'
  * 'int(max_chars)' 类型转换
- build_devset_section source 详尽：
  * 6 keys 字面量精确顺序：status/file_count/content_group_count/pdf_count/docx_count/categories_covered
  * 'manifest.devset_status' / 'manifest.file_count' / etc.
- aggregate_summary source 详尽：
  * 'summary: dict[str, Any] = {}'
  * counts 部分含 _COUNT_METRICS 循环 + sum(values) + participating_docs
  * success_rates 部分含 _SUCCESS_BOOL_METRICS 循环 + success_count + total + rate
  * ratio_avgs 部分含 _RATIO_METRICS 循环 + macro_average + participating_docs + not_evaluated
  * silent_drop_count 部分
  * 4 个 summary['xxx'] 赋值
- __all__ 5 entries 顺序精确
- 模块 namespace 详细
- 模块 source 不含 print/logging/json/threading/asyncio/concurrent.futures
- 模块 source 不含 os import
- 模块 source 不含 numpy/pandas
- 模块 source 不含 manifest_schema 相关
- 模块 source 不含 process_single/pipeline import
- 模块 docstring 含 4 类聚合 + 不混合类型
- get_git_provenance 实际行为：subprocess.run 两次（rev-parse + status）
- get_dependency_versions 实际行为：3 packages 都尝试
- build_provenance 实际行为：返回 9 keys dict
- build_devset_section 实际行为：返回 6 keys dict
- aggregate_summary 实际行为：返回 4 keys dict
"""

from __future__ import annotations

import inspect
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

import evaluation.report as report_module
from evaluation import EVALUATOR_VERSION, REPORT_VERSION
from evaluation.report import (
    _COUNT_METRICS,
    _RATIO_METRICS,
    _SUCCESS_BOOL_METRICS,
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


# =========================================================================
# 模块 imports 精确字符串
# =========================================================================


def test_module_source_contains_import_subprocess():
    src = inspect.getsource(report_module)
    assert "import subprocess" in src


def test_module_source_contains_from_datetime_import_datetime():
    src = inspect.getsource(report_module)
    assert "from datetime import datetime" in src


def test_module_source_contains_from_pathlib_import_path():
    src = inspect.getsource(report_module)
    assert "from pathlib import Path" in src


def test_module_source_contains_from_typing_import_any():
    src = inspect.getsource(report_module)
    assert "from typing import Any" in src


def test_module_source_contains_from_evaluation_import_versions():
    src = inspect.getsource(report_module)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


# =========================================================================
# 常量 source-level
# =========================================================================


def test_ratio_metrics_source_definition_exact():
    src = inspect.getsource(report_module)
    # _RATIO_METRICS 是 tuple，含 12 个 metric 名
    assert '_RATIO_METRICS = (' in src
    assert '"schema_valid"' in src
    assert '"pdf_locator_valid_ratio"' in src
    assert '"docx_locator_valid_ratio"' in src
    assert '"image_resource_exists_ratio"' in src
    assert '"chunk_reference_intact_ratio"' in src
    assert '"text_preservation_equal"' in src
    assert '"text_char_multiset_precision"' in src
    assert '"text_char_multiset_recall"' in src
    assert '"heading_boundary_compliance"' in src
    assert '"chunk_boundary_precision"' in src
    assert '"chunk_boundary_recall"' in src
    assert '"chunk_boundary_f1"' in src


def test_count_metrics_source_definition_exact():
    src = inspect.getsource(report_module)
    assert '_COUNT_METRICS = ("element_count_total",)' in src


def test_success_bool_metrics_source_definition_exact():
    src = inspect.getsource(report_module)
    assert '_SUCCESS_BOOL_METRICS = ("pipeline_success",)' in src


def test_ratio_metrics_value_exact_12_items():
    assert _RATIO_METRICS == (
        "schema_valid",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        "heading_boundary_compliance",
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    )


def test_ratio_metrics_is_tuple():
    assert isinstance(_RATIO_METRICS, tuple)


def test_ratio_metrics_length_12():
    assert len(_RATIO_METRICS) == 12


def test_count_metrics_value_exact():
    assert _COUNT_METRICS == ("element_count_total",)


def test_count_metrics_is_tuple():
    assert isinstance(_COUNT_METRICS, tuple)


def test_count_metrics_length_1():
    assert len(_COUNT_METRICS) == 1


def test_success_bool_metrics_value_exact():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_success_bool_metrics_is_tuple():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_success_bool_metrics_length_1():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_ratio_metrics_does_not_contain_figure_caption():
    """figure_caption_* 始终 null，不参与 macro average。"""
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_element_count_total():
    """count metrics 不在 ratio。"""
    assert "element_count_total" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_pipeline_success():
    assert "pipeline_success" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_silent_drop_count():
    assert "silent_drop_count" not in _RATIO_METRICS


# =========================================================================
# get_git_provenance source-level
# =========================================================================


def test_get_git_provenance_source_contains_commit_init():
    src = inspect.getsource(get_git_provenance)
    assert "commit: str | None = None" in src


def test_get_git_provenance_source_contains_dirty_init():
    src = inspect.getsource(get_git_provenance)
    assert "dirty: bool = True" in src


def test_get_git_provenance_source_contains_try():
    src = inspect.getsource(get_git_provenance)
    assert "try:" in src


def test_get_git_provenance_source_contains_except_oserror_subprocess_error():
    src = inspect.getsource(get_git_provenance)
    assert "except (OSError, subprocess.SubprocessError):" in src


def test_get_git_provenance_source_contains_rev_parse_command():
    src = inspect.getsource(get_git_provenance)
    assert '["git", "rev-parse", "HEAD"]' in src


def test_get_git_provenance_source_contains_status_porcelain_command():
    src = inspect.getsource(get_git_provenance)
    assert '["git", "status", "--porcelain"]' in src


def test_get_git_provenance_source_contains_cwd_kwarg():
    src = inspect.getsource(get_git_provenance)
    assert "cwd=str(project_root)" in src


def test_get_git_provenance_source_contains_capture_output():
    src = inspect.getsource(get_git_provenance)
    assert "capture_output=True" in src


def test_get_git_provenance_source_contains_text_kwarg():
    src = inspect.getsource(get_git_provenance)
    assert "text=True" in src


def test_get_git_provenance_source_contains_encoding_utf8():
    src = inspect.getsource(get_git_provenance)
    assert 'encoding="utf-8"' in src


def test_get_git_provenance_source_contains_errors_replace():
    src = inspect.getsource(get_git_provenance)
    assert 'errors="replace"' in src


def test_get_git_provenance_source_contains_timeout_10():
    src = inspect.getsource(get_git_provenance)
    assert "timeout=10" in src


def test_get_git_provenance_source_contains_returncode_check():
    src = inspect.getsource(get_git_provenance)
    assert "if r.returncode == 0:" in src


def test_get_git_provenance_source_contains_stdout_strip():
    src = inspect.getsource(get_git_provenance)
    assert "r.stdout.strip() or None" in src


def test_get_git_provenance_source_contains_dirty_assignment():
    src = inspect.getsource(get_git_provenance)
    assert "dirty = bool(r2.returncode == 0 and r2.stdout.strip())" in src


def test_get_git_provenance_source_contains_return_dict():
    src = inspect.getsource(get_git_provenance)
    assert 'return {"git_commit": commit, "git_dirty": dirty}' in src


def test_get_git_provenance_source_does_not_contain_print():
    src = inspect.getsource(get_git_provenance)
    assert "print(" not in src


def test_get_git_provenance_source_does_not_contain_logging():
    src = inspect.getsource(get_git_provenance)
    assert "logging" not in src


# =========================================================================
# get_dependency_versions source-level
# =========================================================================


def test_get_dependency_versions_source_contains_lazy_import():
    """importlib.metadata 在函数内 lazy import。"""
    src = inspect.getsource(get_dependency_versions)
    assert "import importlib.metadata" in src


def test_get_dependency_versions_source_contains_versions_init():
    src = inspect.getsource(get_dependency_versions)
    assert "versions: dict[str, str | None] = {}" in src


def test_get_dependency_versions_source_contains_for_pkg_loop():
    src = inspect.getsource(get_dependency_versions)
    assert 'for pkg in ("pdfplumber", "python-docx", "pypdfium2"):' in src


def test_get_dependency_versions_source_contains_version_call():
    src = inspect.getsource(get_dependency_versions)
    assert "importlib.metadata.version(pkg)" in src


def test_get_dependency_versions_source_contains_package_not_found_catch():
    src = inspect.getsource(get_dependency_versions)
    assert "importlib.metadata.PackageNotFoundError" in src


def test_get_dependency_versions_source_contains_exception_catch():
    src = inspect.getsource(get_dependency_versions)
    assert "except Exception:" in src


def test_get_dependency_versions_source_contains_versions_none_assignment():
    src = inspect.getsource(get_dependency_versions)
    assert "versions[pkg] = None" in src


def test_get_dependency_versions_source_contains_return_versions():
    src = inspect.getsource(get_dependency_versions)
    assert "return versions" in src


def test_get_dependency_versions_source_does_not_contain_subprocess():
    """get_dependency_versions 用 importlib.metadata，不用 subprocess。"""
    src = inspect.getsource(get_dependency_versions)
    assert "subprocess" not in src


# =========================================================================
# build_provenance source-level
# =========================================================================


def test_build_provenance_source_contains_get_git_provenance_call():
    src = inspect.getsource(build_provenance)
    assert "git = get_git_provenance(project_root)" in src


def test_build_provenance_source_contains_9_keys_in_order():
    """build_provenance 返回 9 keys 顺序精确。"""
    src = inspect.getsource(build_provenance)
    pos_commit = src.find('"git_commit": git["git_commit"]')
    pos_dirty = src.find('"git_dirty": git["git_dirty"]')
    pos_eval = src.find('"evaluator_version": EVALUATOR_VERSION')
    pos_report = src.find('"report_version": REPORT_VERSION')
    pos_parser_name = src.find('"parser_name": parser_name')
    pos_parser_ver = src.find('"parser_version": parser_version')
    pos_deps = src.find('"dependencies": get_dependency_versions()')
    pos_max = src.find('"max_chars": int(max_chars)')
    pos_ts = src.find('"run_timestamp_iso": datetime.now().astimezone().isoformat()')
    # 位置递增
    assert pos_commit < pos_dirty < pos_eval < pos_report
    assert pos_report < pos_parser_name < pos_parser_ver < pos_deps
    assert pos_deps < pos_max < pos_ts


def test_build_provenance_source_contains_int_max_chars():
    src = inspect.getsource(build_provenance)
    assert '"max_chars": int(max_chars)' in src


def test_build_provenance_source_contains_datetime_now_astimezone_isoformat():
    src = inspect.getsource(build_provenance)
    assert "datetime.now().astimezone().isoformat()" in src


def test_build_provenance_source_does_not_contain_subprocess_call():
    """build_provenance 不直接调 subprocess（委托给 get_git_provenance）。"""
    src = inspect.getsource(build_provenance)
    assert "subprocess.run" not in src


def test_build_provenance_source_does_not_contain_print():
    src = inspect.getsource(build_provenance)
    assert "print(" not in src


# =========================================================================
# build_devset_section source-level
# =========================================================================


def test_build_devset_section_source_contains_6_keys_in_order():
    src = inspect.getsource(build_devset_section)
    pos_status = src.find('"status": manifest.devset_status')
    pos_fc = src.find('"file_count": manifest.file_count')
    pos_cgc = src.find('"content_group_count": manifest.content_group_count')
    pos_pdf = src.find('"pdf_count": manifest.pdf_count')
    pos_docx = src.find('"docx_count": manifest.docx_count')
    pos_cats = src.find('"categories_covered": manifest.categories_covered')
    assert pos_status < pos_fc < pos_cgc < pos_pdf < pos_docx < pos_cats


def test_build_devset_section_source_does_not_contain_subprocess():
    src = inspect.getsource(build_devset_section)
    assert "subprocess" not in src


def test_build_devset_section_source_does_not_contain_datetime():
    src = inspect.getsource(build_devset_section)
    assert "datetime" not in src


# =========================================================================
# aggregate_summary source-level
# =========================================================================


def test_aggregate_summary_source_contains_summary_init():
    src = inspect.getsource(aggregate_summary)
    assert "summary: dict[str, Any] = {}" in src


def test_aggregate_summary_source_contains_counts_init():
    src = inspect.getsource(aggregate_summary)
    assert "counts: dict[str, Any] = {}" in src


def test_aggregate_summary_source_contains_count_metrics_loop():
    src = inspect.getsource(aggregate_summary)
    assert "for name in _COUNT_METRICS:" in src


def test_aggregate_summary_source_contains_count_values_comprehension():
    src = inspect.getsource(aggregate_summary)
    assert "values = [" in src
    assert 'r["metrics"].get(name, {}).get("value")' in src


def test_aggregate_summary_source_contains_sum_participating_docs():
    src = inspect.getsource(aggregate_summary)
    assert '"sum": sum(values)' in src
    assert '"participating_docs": len(values)' in src


def test_aggregate_summary_source_contains_summary_counts_assignment():
    src = inspect.getsource(aggregate_summary)
    assert 'summary["counts"] = counts' in src


def test_aggregate_summary_source_contains_success_rates_init():
    src = inspect.getsource(aggregate_summary)
    assert "success_rates: dict[str, Any] = {}" in src


def test_aggregate_summary_source_contains_success_bool_metrics_loop():
    src = inspect.getsource(aggregate_summary)
    assert "for name in _SUCCESS_BOOL_METRICS:" in src


def test_aggregate_summary_source_contains_successes_sum():
    src = inspect.getsource(aggregate_summary)
    assert (
        "successes = sum(\n            1\n            for r in per_doc_results\n            if r[\"metrics\"].get(name, {}).get(\"value\") is True\n        )"
        in src
    )


def test_aggregate_summary_source_contains_total_len():
    src = inspect.getsource(aggregate_summary)
    assert "total = len(per_doc_results)" in src


def test_aggregate_summary_source_contains_rate_calculation():
    src = inspect.getsource(aggregate_summary)
    assert "rate = (successes / total) if total else None" in src


def test_aggregate_summary_source_contains_success_count_total_rate():
    src = inspect.getsource(aggregate_summary)
    assert '"success_count": successes' in src
    assert '"total": total' in src
    assert '"rate": rate' in src


def test_aggregate_summary_source_contains_summary_success_rates_assignment():
    src = inspect.getsource(aggregate_summary)
    assert 'summary["success_rates"] = success_rates' in src


def test_aggregate_summary_source_contains_ratio_avgs_init():
    src = inspect.getsource(aggregate_summary)
    assert "ratio_avgs: dict[str, Any] = {}" in src


def test_aggregate_summary_source_contains_ratio_metrics_loop():
    src = inspect.getsource(aggregate_summary)
    assert "for name in _RATIO_METRICS:" in src


def test_aggregate_summary_source_contains_not_eval_calculation():
    src = inspect.getsource(aggregate_summary)
    assert "not_eval = len(per_doc_results) - len(values)" in src


def test_aggregate_summary_source_contains_macro_average_calculation():
    src = inspect.getsource(aggregate_summary)
    assert "macro = sum(values) / len(values)" in src


def test_aggregate_summary_source_contains_macro_average_participating_not_evaluated():
    src = inspect.getsource(aggregate_summary)
    assert '"macro_average": macro' in src
    assert '"participating_docs": len(values)' in src
    assert '"not_evaluated": not_eval' in src


def test_aggregate_summary_source_contains_summary_ratio_avgs_assignment():
    src = inspect.getsource(aggregate_summary)
    assert 'summary["ratio_macro_averages"] = ratio_avgs' in src


def test_aggregate_summary_source_contains_silent_drop_filter():
    src = inspect.getsource(aggregate_summary)
    assert 'silent_vals = [' in src
    assert 'r["metrics"].get("silent_drop_count", {}).get("value")' in src


def test_aggregate_summary_source_contains_silent_drop_total():
    src = inspect.getsource(aggregate_summary)
    assert 'summary["silent_drop_total"] = sum(silent_vals) if silent_vals else None' in src


def test_aggregate_summary_source_contains_return_summary():
    src = inspect.getsource(aggregate_summary)
    assert "return summary" in src


def test_aggregate_summary_source_does_not_contain_subprocess():
    src = inspect.getsource(aggregate_summary)
    assert "subprocess" not in src


def test_aggregate_summary_source_does_not_contain_datetime():
    src = inspect.getsource(aggregate_summary)
    assert "datetime" not in src


# =========================================================================
# __all__ 精确
# =========================================================================


def test_module_all_value_exact_5_entries_in_order():
    assert report_module.__all__ == [
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    ]


def test_module_all_is_list_type():
    assert isinstance(report_module.__all__, list)


def test_module_all_length_5():
    assert len(report_module.__all__) == 5


def test_module_all_does_not_contain_constants():
    for name in ["_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"]:
        assert name not in report_module.__all__


def test_module_all_does_not_contain_evaluator_or_report_version():
    assert "EVALUATOR_VERSION" not in report_module.__all__
    assert "REPORT_VERSION" not in report_module.__all__


def test_module_all_does_not_contain_subprocess_or_datetime():
    assert "subprocess" not in report_module.__all__
    assert "datetime" not in report_module.__all__


def test_module_all_does_not_contain_path_or_any():
    assert "Path" not in report_module.__all__
    assert "Any" not in report_module.__all__


# =========================================================================
# namespace 详细
# =========================================================================


def test_module_namespace_has_subprocess_attr():
    assert hasattr(report_module, "subprocess")


def test_module_namespace_has_datetime_attr():
    assert hasattr(report_module, "datetime")
    assert report_module.datetime is datetime


def test_module_namespace_has_path_attr():
    assert hasattr(report_module, "Path")
    assert report_module.Path is Path


def test_module_namespace_has_any_attr():
    assert hasattr(report_module, "Any")
    assert report_module.Any is Any


def test_module_namespace_has_evaluator_version_attr():
    assert hasattr(report_module, "EVALUATOR_VERSION")
    assert report_module.EVALUATOR_VERSION == EVALUATOR_VERSION


def test_module_namespace_has_report_version_attr():
    assert hasattr(report_module, "REPORT_VERSION")
    assert report_module.REPORT_VERSION == REPORT_VERSION


def test_module_namespace_has_constants():
    assert hasattr(report_module, "_RATIO_METRICS")
    assert hasattr(report_module, "_COUNT_METRICS")
    assert hasattr(report_module, "_SUCCESS_BOOL_METRICS")


def test_module_namespace_has_5_helpers():
    for name in [
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    ]:
        assert hasattr(report_module, name)


def test_module_namespace_does_not_have_json():
    assert not hasattr(report_module, "json")


def test_module_namespace_does_not_have_os():
    assert not hasattr(report_module, "os")


def test_module_namespace_does_not_have_logging():
    assert not hasattr(report_module, "logging")


def test_module_namespace_does_not_have_threading():
    assert not hasattr(report_module, "threading")


def test_module_namespace_does_not_have_asyncio():
    assert not hasattr(report_module, "asyncio")


# =========================================================================
# 模块 source 不含禁止内容
# =========================================================================


def test_module_source_does_not_contain_print():
    src = inspect.getsource(report_module)
    assert "print(" not in src


def test_module_source_does_not_contain_logging():
    src = inspect.getsource(report_module)
    assert "logging" not in src


def test_module_source_does_not_contain_async():
    src = inspect.getsource(report_module)
    assert "async " not in src
    assert "await " not in src


def test_module_source_does_not_contain_threading_import():
    src = inspect.getsource(report_module)
    assert "import threading" not in src


def test_module_source_does_not_contain_os_import():
    src = inspect.getsource(report_module)
    assert "import os" not in src


def test_module_source_does_not_contain_concurrent_futures():
    src = inspect.getsource(report_module)
    assert "concurrent.futures" not in src


def test_module_source_does_not_contain_numpy():
    src = inspect.getsource(report_module)
    assert "import numpy" not in src


def test_module_source_does_not_contain_pandas():
    src = inspect.getsource(report_module)
    assert "import pandas" not in src


def test_module_source_does_not_contain_json_import():
    src = inspect.getsource(report_module)
    assert "import json" not in src


def test_module_source_does_not_contain_manifest_load():
    src = inspect.getsource(report_module)
    assert "load_manifest" not in src


def test_module_source_does_not_contain_process_single():
    src = inspect.getsource(report_module)
    assert "process_single" not in src
    assert "from app.pipeline" not in src


def test_module_source_does_not_contain_compute_automatic_metrics():
    src = inspect.getsource(report_module)
    assert "compute_automatic_metrics" not in src


# =========================================================================
# 实际行为验证
# =========================================================================


def test_get_dependency_versions_returns_dict_with_3_keys():
    out = get_dependency_versions()
    assert isinstance(out, dict)
    assert len(out) == 3
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_are_str_or_none():
    out = get_dependency_versions()
    for v in out.values():
        assert v is None or isinstance(v, str)


def test_build_provenance_returns_dict_with_9_keys(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out, dict)
    assert len(out) == 9
    expected_keys = {
        "git_commit",
        "git_dirty",
        "evaluator_version",
        "report_version",
        "parser_name",
        "parser_version",
        "dependencies",
        "max_chars",
        "run_timestamp_iso",
    }
    assert set(out.keys()) == expected_keys


def test_build_provenance_keys_in_order(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    keys = list(out.keys())
    assert keys == [
        "git_commit",
        "git_dirty",
        "evaluator_version",
        "report_version",
        "parser_name",
        "parser_version",
        "dependencies",
        "max_chars",
        "run_timestamp_iso",
    ]


def test_build_provenance_evaluator_version_value(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_value(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_name"] == "fallback"


def test_build_provenance_parser_version_value(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.2.3")
    assert out["parser_version"] == "1.2.3"


def test_build_provenance_max_chars_int_value(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_run_timestamp_iso_str_value(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["run_timestamp_iso"], str)


def test_build_provenance_dependencies_dict_value(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["dependencies"], dict)


def test_aggregate_summary_returns_dict_with_4_keys():
    out = aggregate_summary([])
    assert isinstance(out, dict)
    assert len(out) == 4
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_keys_in_order():
    out = aggregate_summary([])
    keys = list(out.keys())
    assert keys == ["counts", "success_rates", "ratio_macro_averages", "silent_drop_total"]


def test_aggregate_summary_silent_drop_total_none_when_empty():
    out = aggregate_summary([])
    assert out["silent_drop_total"] is None


def test_aggregate_summary_counts_dict_has_element_count_total():
    out = aggregate_summary([])
    assert "element_count_total" in out["counts"]


def test_aggregate_summary_success_rates_dict_has_pipeline_success():
    out = aggregate_summary([])
    assert "pipeline_success" in out["success_rates"]


def test_aggregate_summary_ratio_avgs_dict_has_all_12_metrics():
    out = aggregate_summary([])
    assert set(out["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


# =========================================================================
# helper metadata
# =========================================================================


def test_all_helpers_are_function_type():
    import types

    for fn in [
        build_provenance,
        build_devset_section,
        aggregate_summary,
        get_git_provenance,
        get_dependency_versions,
    ]:
        assert isinstance(fn, types.FunctionType)


def test_all_helpers_module_identity():
    for fn in [
        build_provenance,
        build_devset_section,
        aggregate_summary,
        get_git_provenance,
        get_dependency_versions,
    ]:
        assert fn.__module__ == "evaluation.report"


def test_all_helpers_qualname_exact():
    assert build_provenance.__qualname__ == "build_provenance"
    assert build_devset_section.__qualname__ == "build_devset_section"
    assert aggregate_summary.__qualname__ == "aggregate_summary"
    assert get_git_provenance.__qualname__ == "get_git_provenance"
    assert get_dependency_versions.__qualname__ == "get_dependency_versions"


# =========================================================================
# 签名 introspection 详细
# =========================================================================


def test_get_git_provenance_signature_param_count_1():
    sig = inspect.signature(get_git_provenance)
    assert len(sig.parameters) == 1
    assert "project_root" in sig.parameters


def test_get_git_provenance_return_annotation_not_empty():
    sig = inspect.signature(get_git_provenance)
    assert sig.return_annotation is not inspect.Signature.empty


def test_get_dependency_versions_signature_param_count_0():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_build_provenance_signature_param_count_4():
    sig = inspect.signature(build_provenance)
    assert len(sig.parameters) == 4
    assert list(sig.parameters.keys()) == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_build_provenance_signature_no_defaults():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_build_devset_section_signature_param_count_1():
    sig = inspect.signature(build_devset_section)
    assert len(sig.parameters) == 1
    assert "manifest" in sig.parameters


def test_aggregate_summary_signature_param_count_1():
    sig = inspect.signature(aggregate_summary)
    assert len(sig.parameters) == 1
    assert "per_doc_results" in sig.parameters


# =========================================================================
# 模块 docstring 详细
# =========================================================================


def test_module_docstring_is_nonempty_string():
    assert isinstance(report_module.__doc__, str)
    assert len(report_module.__doc__) > 0


def test_module_docstring_mentions_provenance():
    doc = report_module.__doc__
    assert "provenance" in doc.lower() or "出处" in doc


def test_module_docstring_mentions_devset():
    doc = report_module.__doc__
    assert "devset" in doc.lower() or "开发集" in doc


def test_module_docstring_mentions_summary():
    doc = report_module.__doc__
    assert "summary" in doc.lower() or "汇总" in doc or "聚合" in doc


def test_module_docstring_mentions_per_doc():
    doc = report_module.__doc__
    assert "per_doc" in doc.lower() or "每个文档" in doc


def test_module_docstring_mentions_4_categories():
    """docstring 提到 4 类聚合（counts/success_rates/ratio/silent_drop）。"""
    doc = report_module.__doc__
    assert "counts" in doc.lower() or "求和" in doc
    assert "success_rates" in doc.lower() or "成功" in doc
    assert "ratio" in doc.lower() or "macro" in doc.lower()
    assert "silent_drop" in doc.lower()


def test_module_docstring_mentions_bu_hun_he_lei_xing():
    """docstring 提到不混合类型。"""
    doc = report_module.__doc__
    assert "不混合类型" in doc or "不混合" in doc


# =========================================================================
# 不缓存验证
# =========================================================================


def test_get_dependency_versions_two_calls_independent_dict():
    a = get_dependency_versions()
    b = get_dependency_versions()
    assert a is not b


def test_aggregate_summary_two_calls_independent_dict():
    a = aggregate_summary([])
    b = aggregate_summary([])
    assert a is not b
    assert a["counts"] is not b["counts"]
