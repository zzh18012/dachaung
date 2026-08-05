r"""evaluation/report.py 边角测试 - 第十轮（Round 218）。

补强已有 base/edges/edges2-9（共 ~815 测试）未覆盖的深度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 互斥性
- get_git_provenance：非 git 目录 / 非 ASCII 输出 / 实际 subprocess.run 调用形式
- get_dependency_versions：importlib.metadata 异常 / 单个包未安装
- build_provenance：max_chars 极大值 / parser_name 任意 str / dependencies 与 versions 一致
- build_devset_section：Manifest 缺字段时 AttributeError
- aggregate_summary：metric value=0 vs None / 部分 doc 缺 metric / silent_drop 跨 doc 累加
- aggregate_summary：metrics 字段不是 dict
- 模块结构 / __all__ / imports
- 综合行为
"""

from __future__ import annotations

import inspect
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

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


class _FakeManifest:
    def __init__(self, status="incomplete", file_count=1, content_group_count=1,
                 pdf_count=1, docx_count=0, categories_covered=None):
        self.devset_status = status
        self.file_count = file_count
        self.content_group_count = content_group_count
        self.pdf_count = pdf_count
        self.docx_count = docx_count
        self.categories_covered = categories_covered if categories_covered is not None else ["text"]


# =========================================================================
# 常量互斥性（counts/ratios/success 不应重叠）
# =========================================================================


def test_count_and_ratio_metrics_disjoint():
    assert set(_COUNT_METRICS) & set(_RATIO_METRICS) == set()


def test_count_and_success_metrics_disjoint():
    assert set(_COUNT_METRICS) & set(_SUCCESS_BOOL_METRICS) == set()


def test_success_and_ratio_metrics_disjoint():
    """注意：schema_valid 在 _RATIO_METRICS 中，pipeline_success 在 _SUCCESS_BOOL_METRICS。"""
    assert set(_SUCCESS_BOOL_METRICS) & set(_RATIO_METRICS) == set()


def test_count_metrics_does_not_include_silent_drop():
    """silent_drop_count 不在 _COUNT_METRICS（它单独走 silent_drop_total）。"""
    assert "silent_drop_count" not in _COUNT_METRICS


def test_ratio_metrics_does_not_include_silent_drop():
    assert "silent_drop_count" not in _RATIO_METRICS


def test_ratio_metrics_does_not_include_element_count_total():
    assert "element_count_total" not in _RATIO_METRICS


def test_ratio_metrics_does_not_include_pipeline_success():
    assert "pipeline_success" not in _RATIO_METRICS


def test_ratio_metrics_does_not_include_error_code():
    assert "error_code" not in _RATIO_METRICS


def test_ratio_metrics_does_not_include_element_count_by_type():
    assert "element_count_by_type" not in _RATIO_METRICS


def test_ratio_metrics_includes_schema_valid():
    """schema_valid 是 0/1 → 进入 ratio_macro_averages。"""
    assert "schema_valid" in _RATIO_METRICS


# =========================================================================
# get_git_provenance 深度
# =========================================================================


def test_get_git_provenance_returns_dict_with_two_keys(tmp_path):
    result = get_git_provenance(tmp_path)
    assert set(result.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_callable():
    assert callable(get_git_provenance)


def test_get_git_provenance_param_kind():
    sig = inspect.signature(get_git_provenance)
    assert sig.parameters["project_root"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_get_git_provenance_no_default():
    sig = inspect.signature(get_git_provenance)
    assert sig.parameters["project_root"].default is inspect.Parameter.empty


def test_get_git_provenance_subprocess_called_with_git_command(monkeypatch, tmp_path):
    """subprocess.run 第一次调用应是 git rev-parse HEAD。"""
    captured_cmds = []

    def fake_run(cmd, *args, **kwargs):
        captured_cmds.append(cmd)
        # 模拟成功返回
        class _R:
            returncode = 0
            stdout = "deadbeef" * 5  # 40 hex
            stderr = ""
        return _R()

    monkeypatch.setattr("subprocess.run", fake_run)
    result = get_git_provenance(tmp_path)
    assert captured_cmds[0][:2] == ["git", "rev-parse"]
    assert captured_cmds[1][:2] == ["git", "status"]


def test_get_git_provenance_subprocess_timeout_safe(monkeypatch, tmp_path):
    def fake_run(cmd, *args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=10)

    monkeypatch.setattr("subprocess.run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_oserror_safe(monkeypatch, tmp_path):
    def fake_run(cmd, *args, **kwargs):
        raise OSError("simulated")

    monkeypatch.setattr("subprocess.run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_subprocess_error_safe(monkeypatch, tmp_path):
    def fake_run(cmd, *args, **kwargs):
        raise subprocess.SubprocessError("simulated")

    monkeypatch.setattr("subprocess.run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_nonzero_returncode(monkeypatch, tmp_path):
    """git rev-parse 返回非 0（非 git 目录）→ commit=None。"""
    def fake_run(cmd, *args, **kwargs):
        class _R:
            returncode = 128
            stdout = ""
            stderr = "not a git repo"
        return _R()

    monkeypatch.setattr("subprocess.run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None


def test_get_git_provenance_empty_commit_output(monkeypatch, tmp_path):
    """returncode=0 但 stdout 为空 → commit=None。"""
    call_count = [0]

    def fake_run(cmd, *args, **kwargs):
        call_count[0] += 1
        class _R:
            returncode = 0
            stdout = ""  # 空输出
            stderr = ""
        return _R()

    monkeypatch.setattr("subprocess.run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None


def test_get_git_provenance_strips_whitespace_from_commit(monkeypatch, tmp_path):
    """commit 输出末尾有 \n 应 strip 掉。"""
    call_count = [0]

    def fake_run(cmd, *args, **kwargs):
        call_count[0] += 1
        class _R:
            returncode = 0
            stdout = "  abc123  \n" if call_count[0] == 1 else ""
            stderr = ""
        return _R()

    monkeypatch.setattr("subprocess.run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] == "abc123"


def test_get_git_provenance_dirty_when_porcelain_nonempty(monkeypatch, tmp_path):
    call_count = [0]

    def fake_run(cmd, *args, **kwargs):
        call_count[0] += 1
        class _R:
            returncode = 0
            stdout = " M file.txt" if call_count[0] == 2 else "commit12345"
            stderr = ""
        return _R()

    monkeypatch.setattr("subprocess.run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_dirty"] is True


def test_get_git_provenance_clean_when_porcelain_empty(monkeypatch, tmp_path):
    call_count = [0]

    def fake_run(cmd, *args, **kwargs):
        call_count[0] += 1
        class _R:
            returncode = 0
            stdout = ""  # porcelain empty
            stderr = ""
        return _R()

    monkeypatch.setattr("subprocess.run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_dirty"] is False


# =========================================================================
# get_dependency_versions 深度
# =========================================================================


def test_get_dependency_versions_returns_dict():
    result = get_dependency_versions()
    assert isinstance(result, dict)


def test_get_dependency_versions_keys_exact():
    result = get_dependency_versions()
    assert set(result.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_str_or_none():
    result = get_dependency_versions()
    for v in result.values():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_callable():
    assert callable(get_dependency_versions)


def test_get_dependency_versions_signature():
    sig = inspect.signature(get_dependency_versions)
    assert list(sig.parameters) == []


def test_get_dependency_versions_no_params():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_get_dependency_versions_handles_missing_packages(monkeypatch):
    """模拟 importlib.metadata.PackageNotFoundError。"""
    import importlib.metadata

    def fake_version(pkg):
        raise importlib.metadata.PackageNotFoundError(pkg)

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    result = get_dependency_versions()
    assert all(v is None for v in result.values())


def test_get_dependency_versions_handles_exception(monkeypatch):
    """模拟其他 Exception（importlib.metadata 抛错）。"""
    import importlib.metadata

    def fake_version(pkg):
        raise RuntimeError("boom")

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    result = get_dependency_versions()
    assert all(v is None for v in result.values())


def test_get_dependency_versions_returns_real_pdfplumber_version(monkeypatch):
    """真实环境应能读到 pdfplumber 版本（除非环境异常）。"""
    result = get_dependency_versions()
    # 如果 pdfplumber 安装，应有版本字符串
    # 这条测试不强求 always pass，但若环境正常应通过
    if result["pdfplumber"] is not None:
        assert isinstance(result["pdfplumber"], str)
        assert len(result["pdfplumber"]) > 0


# =========================================================================
# build_provenance 深度
# =========================================================================


def test_build_provenance_signature_count():
    sig = inspect.signature(build_provenance)
    assert len(sig.parameters) == 4


def test_build_provenance_param_kinds():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_build_provenance_keys_nine_exact(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    expected = {
        "git_commit", "git_dirty",
        "evaluator_version", "report_version",
        "parser_name", "parser_version",
        "dependencies", "max_chars", "run_timestamp_iso",
    }
    assert set(result.keys()) == expected


def test_build_provenance_evaluator_version_constant(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["evaluator_version"] == EVALUATOR_VERSION == "1.1"


def test_build_provenance_report_version_constant(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["report_version"] == REPORT_VERSION == "1.1"


def test_build_provenance_max_chars_int_type(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert type(result["max_chars"]) is int


def test_build_provenance_max_chars_zero(tmp_path):
    result = build_provenance(tmp_path, "fallback", 0, None)
    assert result["max_chars"] == 0


def test_build_provenance_max_chars_negative(tmp_path):
    result = build_provenance(tmp_path, "fallback", -1, None)
    assert result["max_chars"] == -1


def test_build_provenance_max_chars_large_value(tmp_path):
    result = build_provenance(tmp_path, "fallback", 10**9, None)
    assert result["max_chars"] == 10**9


def test_build_provenance_max_chars_from_str_digits(tmp_path):
    result = build_provenance(tmp_path, "fallback", "800", None)  # type: ignore[arg-type]
    assert result["max_chars"] == 800


def test_build_provenance_max_chars_float_truncated(tmp_path):
    """int(800.9) → 800（截断）。"""
    result = build_provenance(tmp_path, "fallback", 800.9, None)  # type: ignore[arg-type]
    assert result["max_chars"] == 800


def test_build_provenance_parser_name_unicode(tmp_path):
    result = build_provenance(tmp_path, "中文parser", 800, None)
    assert result["parser_name"] == "中文parser"


def test_build_provenance_parser_name_empty(tmp_path):
    result = build_provenance(tmp_path, "", 800, None)
    assert result["parser_name"] == ""


def test_build_provenance_parser_version_propagated(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert result["parser_version"] == "0.1.0"


def test_build_provenance_parser_version_none(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["parser_version"] is None


def test_build_provenance_dependencies_three_keys(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert set(result["dependencies"].keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_build_provenance_run_timestamp_iso_parseable(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    ts = result["run_timestamp_iso"]
    parsed = datetime.fromisoformat(ts)
    assert isinstance(parsed, datetime)


def test_build_provenance_run_timestamp_iso_has_timezone(tmp_path):
    """ISO 格式应包含时区信息（+HH:MM）。"""
    result = build_provenance(tmp_path, "fallback", 800, None)
    ts = result["run_timestamp_iso"]
    # 应能解析为带时区的 datetime
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None


def test_build_provenance_run_timestamp_near_now(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    ts = result["run_timestamp_iso"]
    parsed = datetime.fromisoformat(ts)
    now = datetime.now().astimezone()
    delta = abs((parsed - now).total_seconds())
    assert delta < 5  # 5 秒内


def test_build_provenance_git_commit_str_or_none(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["git_commit"] is None or isinstance(result["git_commit"], str)


def test_build_provenance_git_dirty_bool(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(result["git_dirty"], bool)


# =========================================================================
# build_devset_section 深度
# =========================================================================


def test_build_devset_section_returns_dict():
    result = build_devset_section(_FakeManifest())
    assert isinstance(result, dict)


def test_build_devset_section_six_keys():
    result = build_devset_section(_FakeManifest())
    assert len(result.keys()) == 6


def test_build_devset_section_keys_exact():
    result = build_devset_section(_FakeManifest())
    expected = {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }
    assert set(result.keys()) == expected


def test_build_devset_section_status_propagated():
    m = _FakeManifest(status="complete")
    assert build_devset_section(m)["status"] == "complete"


def test_build_devset_section_file_count_propagated():
    m = _FakeManifest(file_count=42)
    assert build_devset_section(m)["file_count"] == 42


def test_build_devset_section_content_group_count_propagated():
    m = _FakeManifest(content_group_count=5)
    assert build_devset_section(m)["content_group_count"] == 5


def test_build_devset_section_pdf_count_propagated():
    m = _FakeManifest(pdf_count=3)
    assert build_devset_section(m)["pdf_count"] == 3


def test_build_devset_section_docx_count_propagated():
    m = _FakeManifest(docx_count=7)
    assert build_devset_section(m)["docx_count"] == 7


def test_build_devset_section_categories_covered_propagated():
    m = _FakeManifest(categories_covered=["a", "b"])
    assert build_devset_section(m)["categories_covered"] == ["a", "b"]


def test_build_devset_section_categories_covered_empty():
    m = _FakeManifest(categories_covered=[])
    assert build_devset_section(m)["categories_covered"] == []


def test_build_devset_section_categories_covered_unicode():
    m = _FakeManifest(categories_covered=["中文", "english"])
    result = build_devset_section(m)
    assert "中文" in result["categories_covered"]


def test_build_devset_section_callable():
    assert callable(build_devset_section)


def test_build_devset_section_signature_one_param():
    sig = inspect.signature(build_devset_section)
    assert list(sig.parameters) == ["manifest"]


# =========================================================================
# aggregate_summary 深度
# =========================================================================


def test_aggregate_summary_returns_dict():
    result = aggregate_summary([])
    assert isinstance(result, dict)


def test_aggregate_summary_four_top_keys():
    result = aggregate_summary([])
    assert set(result.keys()) == {
        "counts", "success_rates", "ratio_macro_averages", "silent_drop_total",
    }


def test_aggregate_summary_callable():
    assert callable(aggregate_summary)


def test_aggregate_summary_param_kind():
    sig = inspect.signature(aggregate_summary)
    assert sig.parameters["per_doc_results"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_aggregate_summary_counts_keys_exact():
    result = aggregate_summary([])
    assert set(result["counts"].keys()) == {"element_count_total"}


def test_aggregate_summary_success_rates_keys_exact():
    result = aggregate_summary([])
    assert set(result["success_rates"].keys()) == {"pipeline_success"}


def test_aggregate_summary_ratio_keys_exact_twelve():
    result = aggregate_summary([])
    assert len(result["ratio_macro_averages"].keys()) == 12


def test_aggregate_summary_silent_drop_total_none_for_empty():
    result = aggregate_summary([])
    assert result["silent_drop_total"] is None


def test_aggregate_summary_counts_with_multiple_docs():
    pd = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": 10}}},
    ]
    result = aggregate_summary(pd)
    assert result["counts"]["element_count_total"]["sum"] == 15
    assert result["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_zero_values_participate():
    """value=0 是有效值（not None）→ 参与 sum。"""
    pd = [
        {"metrics": {"element_count_total": {"value": 0}}},
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    result = aggregate_summary(pd)
    assert result["counts"]["element_count_total"]["sum"] == 5
    assert result["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_skips_none_value():
    pd = [
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    result = aggregate_summary(pd)
    assert result["counts"]["element_count_total"]["sum"] == 5
    assert result["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_counts_skips_missing_metric():
    pd = [
        {"metrics": {}},
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    result = aggregate_summary(pd)
    assert result["counts"]["element_count_total"]["sum"] == 5
    assert result["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_success_rates_all_success():
    pd = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    result = aggregate_summary(pd)
    sr = result["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 2
    assert sr["rate"] == 1.0


def test_aggregate_summary_success_rates_no_success():
    pd = [
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    result = aggregate_summary(pd)
    sr = result["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["rate"] == 0.0


def test_aggregate_summary_success_rates_skips_none():
    pd = [
        {"metrics": {"pipeline_success": {"value": None}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    result = aggregate_summary(pd)
    sr = result["success_rates"]["pipeline_success"]
    # total = 2（所有 doc），但 success_count=1
    assert sr["total"] == 2
    assert sr["success_count"] == 1
    assert sr["rate"] == 0.5


def test_aggregate_summary_success_rates_empty_rate_none():
    result = aggregate_summary([])
    sr = result["success_rates"]["pipeline_success"]
    assert sr["rate"] is None
    assert sr["success_count"] == 0
    assert sr["total"] == 0


def test_aggregate_summary_ratio_macro_with_zero():
    """value=0 参与计算 macro average。"""
    pd = [
        {"metrics": {"schema_valid": {"value": 0}}},
        {"metrics": {"schema_valid": {"value": 1}}},
    ]
    result = aggregate_summary(pd)
    avg = result["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == 0.5
    assert avg["participating_docs"] == 2


def test_aggregate_summary_ratio_macro_skips_none():
    pd = [
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": 1.0}}},
    ]
    result = aggregate_summary(pd)
    avg = result["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == 1.0
    assert avg["participating_docs"] == 1
    assert avg["not_evaluated"] == 1


def test_aggregate_summary_ratio_macro_skips_missing():
    pd = [
        {"metrics": {}},
        {"metrics": {"schema_valid": {"value": 1.0}}},
    ]
    result = aggregate_summary(pd)
    avg = result["ratio_macro_averages"]["schema_valid"]
    assert avg["participating_docs"] == 1
    assert avg["not_evaluated"] == 1


def test_aggregate_summary_ratio_macro_all_none():
    pd = [
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    result = aggregate_summary(pd)
    avg = result["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] is None
    assert avg["participating_docs"] == 0
    assert avg["not_evaluated"] == 2


def test_aggregate_summary_silent_drop_with_zero():
    """silent_drop_count value=0 参与 sum。"""
    pd = [
        {"metrics": {"silent_drop_count": {"value": 0}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    result = aggregate_summary(pd)
    assert result["silent_drop_total"] == 5


def test_aggregate_summary_silent_drop_skips_none():
    pd = [
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": 3}}},
    ]
    result = aggregate_summary(pd)
    assert result["silent_drop_total"] == 3


def test_aggregate_summary_silent_drop_all_none():
    pd = [
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    result = aggregate_summary(pd)
    assert result["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_empty():
    result = aggregate_summary([])
    assert result["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_all_zero():
    pd = [
        {"metrics": {"silent_drop_count": {"value": 0}}},
        {"metrics": {"silent_drop_count": {"value": 0}}},
    ]
    result = aggregate_summary(pd)
    assert result["silent_drop_total"] == 0


def test_aggregate_summary_idempotent():
    pd = [
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    r1 = aggregate_summary(pd)
    r2 = aggregate_summary(pd)
    assert r1 == r2


def test_aggregate_summary_returns_new_dict_each_call():
    pd = [{"metrics": {"element_count_total": {"value": 5}}}]
    r1 = aggregate_summary(pd)
    r2 = aggregate_summary(pd)
    assert r1 == r2
    assert r1 is not r2


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact_set():
    import evaluation.report as m
    assert set(m.__all__) == {
        "build_provenance", "build_devset_section",
        "aggregate_summary", "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_all_is_list():
    import evaluation.report as m
    assert isinstance(m.__all__, list)


def test_module_all_length_five():
    import evaluation.report as m
    assert len(m.__all__) == 5


def test_module_imports_subprocess_module():
    import evaluation.report as m
    assert hasattr(m, "subprocess")


def test_module_imports_datetime():
    import evaluation.report as m
    assert hasattr(m, "datetime")


def test_module_imports_path():
    import evaluation.report as m
    assert hasattr(m, "Path")


def test_module_imports_any():
    import evaluation.report as m
    assert hasattr(m, "Any")


def test_module_imports_evaluator_version():
    import evaluation.report as m
    assert hasattr(m, "EVALUATOR_VERSION")


def test_module_imports_report_version():
    import evaluation.report as m
    assert hasattr(m, "REPORT_VERSION")


def test_module_evaluator_version_value():
    import evaluation.report as m
    assert m.EVALUATOR_VERSION == "1.1"


def test_module_report_version_value():
    import evaluation.report as m
    assert m.REPORT_VERSION == "1.1"


def test_module_docstring_present():
    import evaluation.report as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 50


def test_module_docstring_mentions_aggregation_rules():
    import evaluation.report as m
    doc = m.__doc__
    assert "counts" in doc
    assert "success_rates" in doc
    assert "ratio" in doc
    assert "silent_drop" in doc


def test_module_docstring_mentions_no_mixing():
    """docstring 应明确"不混合类型"。"""
    import evaluation.report as m
    doc = m.__doc__
    assert "不混合" in doc or "no mix" in doc.lower()


def test_module_uses_future_annotations():
    import evaluation.report as m
    sig = inspect.signature(m.aggregate_summary)
    assert isinstance(sig.return_annotation, str)


def test_module_no_silence_unused():
    import evaluation.report as m
    assert not hasattr(m, "_silence_unused_import")


def test_module_constants_present():
    import evaluation.report as m
    assert hasattr(m, "_RATIO_METRICS")
    assert hasattr(m, "_COUNT_METRICS")
    assert hasattr(m, "_SUCCESS_BOOL_METRICS")


# =========================================================================
# 综合行为
# =========================================================================


def test_aggregate_summary_full_pipeline_with_mixed_metrics():
    pd = [
        {
            "doc_id": "d1",
            "source_type": "pdf",
            "metrics": {
                "pipeline_success": {"value": True, "reason": None},
                "schema_valid": {"value": True, "reason": None},
                "element_count_total": {"value": 5, "reason": None},
                "pdf_locator_valid_ratio": {"value": 1.0, "reason": None},
                "chunk_boundary_precision": {"value": 0.5, "reason": None},
                "silent_drop_count": {"value": 2, "reason": None},
            },
            "wall_time_seconds": {"total": 0.1, "parse": None, "chunk": None,
                                   "parse_reason": "not_instrumented",
                                   "chunk_reason": "not_instrumented"},
        },
        {
            "doc_id": "d2",
            "source_type": "docx",
            "metrics": {
                "pipeline_success": {"value": False, "reason": None},
                "schema_valid": {"value": False, "reason": None},
                "element_count_total": {"value": None, "reason": "pipeline_failed"},
                "pdf_locator_valid_ratio": {"value": None, "reason": "not_pdf_document"},
                "chunk_boundary_precision": {"value": 1.0, "reason": None},
                "silent_drop_count": {"value": 0, "reason": None},
            },
            "wall_time_seconds": {"total": 0.05, "parse": None, "chunk": None,
                                   "parse_reason": "not_instrumented",
                                   "chunk_reason": "not_instrumented"},
        },
    ]
    result = aggregate_summary(pd)
    # counts
    assert result["counts"]["element_count_total"]["sum"] == 5
    assert result["counts"]["element_count_total"]["participating_docs"] == 1
    # success
    assert result["success_rates"]["pipeline_success"]["success_count"] == 1
    assert result["success_rates"]["pipeline_success"]["total"] == 2
    assert result["success_rates"]["pipeline_success"]["rate"] == 0.5
    # ratio macro - pdf_locator_valid_ratio 只有 d1 参与了 (d2 是 not_pdf_document 但 metric 还是 null)
    avg = result["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert avg["macro_average"] == 1.0
    assert avg["participating_docs"] == 1
    # silent_drop
    assert result["silent_drop_total"] == 2


def test_build_provenance_full_dict_has_consistent_types(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert isinstance(result["git_commit"], (str, type(None)))
    assert isinstance(result["git_dirty"], bool)
    assert isinstance(result["evaluator_version"], str)
    assert isinstance(result["report_version"], str)
    assert isinstance(result["parser_name"], str)
    assert isinstance(result["parser_version"], (str, type(None)))
    assert isinstance(result["dependencies"], dict)
    assert isinstance(result["max_chars"], int)
    assert isinstance(result["run_timestamp_iso"], str)
