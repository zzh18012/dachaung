"""evaluation/report.py 边角测试（Round 84，第二轮）。

补强 tests/test_evaluation_report.py（90+ 测试）+ test_evaluation_report_edges.py（65+ 测试）
未覆盖的盲区：

- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 常量
- get_git_provenance: 类型/键集合/dirty 逻辑/commit 格式/timeout
- get_dependency_versions: 路径覆盖、键顺序、importlib mock
- build_provenance: 9 键完整、timestamp ISO 格式、各种 max_chars 类型
- build_devset_section: 6 键、SimpleNamespace 输入、types preserved
- aggregate_summary: 极端值（0/1/large）、4 顶层键、metrics 字段缺失、
  ratio_macro_averages 含全 12 项、count/success 名字精确、不修改输入
- 模块结构：__all__、imports、常量类型
"""

from __future__ import annotations

import importlib.metadata
import subprocess
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from evaluation import EVALUATOR_VERSION, REPORT_VERSION
from evaluation.report import (
    __all__ as report_all,
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
# 1. 模块常量
# =========================================================================


def test_ratio_metrics_is_tuple():
    assert isinstance(_RATIO_METRICS, tuple)


def test_ratio_metrics_has_12_entries():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_contains_schema_valid():
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_contains_pdf_locator():
    assert "pdf_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_docx_locator():
    assert "docx_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_image_resource():
    assert "image_resource_exists_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_reference():
    assert "chunk_reference_intact_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_text_preservation():
    assert "text_preservation_equal" in _RATIO_METRICS


def test_ratio_metrics_contains_text_precision():
    assert "text_char_multiset_precision" in _RATIO_METRICS


def test_ratio_metrics_contains_text_recall():
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_contains_heading_boundary():
    assert "heading_boundary_compliance" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_precision():
    assert "chunk_boundary_precision" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_recall():
    assert "chunk_boundary_recall" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_f1():
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_figure_caption():
    """figure_caption_* 始终 null + reason，不参与 macro average。"""
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_ratio_metrics_unique_no_duplicates():
    assert len(set(_RATIO_METRICS)) == len(_RATIO_METRICS)


def test_count_metrics_is_tuple():
    assert isinstance(_COUNT_METRICS, tuple)


def test_count_metrics_only_element_count_total():
    assert _COUNT_METRICS == ("element_count_total",)


def test_count_metrics_single_entry():
    assert len(_COUNT_METRICS) == 1


def test_success_bool_metrics_is_tuple():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_success_bool_metrics_only_pipeline_success():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_success_bool_metrics_single_entry():
    assert len(_SUCCESS_BOOL_METRICS) == 1


# =========================================================================
# 2. get_git_provenance 第二轮
# =========================================================================


def test_get_git_provenance_returns_dict_type(tmp_path: Path):
    result = get_git_provenance(tmp_path)
    assert isinstance(result, dict)


def test_get_git_provenance_exact_two_keys(tmp_path: Path):
    result = get_git_provenance(tmp_path)
    assert set(result.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_git_commit_is_str_or_none(tmp_path: Path):
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None or isinstance(result["git_commit"], str)


def test_get_git_provenance_git_dirty_is_bool(tmp_path: Path):
    result = get_git_provenance(tmp_path)
    assert isinstance(result["git_dirty"], bool)


def test_get_git_provenance_default_dirty_when_no_git(tmp_path: Path):
    """非 git 仓库：git rev-parse 失败 → commit=None；git status --porcelain 返 128
    → returncode != 0 → dirty=False（不是默认 True，因为 subprocess 本身没抛异常）。"""
    result = get_git_provenance(tmp_path)
    # subprocess 执行成功（只是 git 返非 0），不进 except 分支
    assert result["git_commit"] is None
    # git status 返非 0 → `bool(False and ...)` = False
    assert result["git_dirty"] is False


def test_get_git_provenance_handles_timeout(monkeypatch, tmp_path: Path):
    def _timeout(*a, **kw):
        raise subprocess.TimeoutExpired(cmd="git", timeout=10)
    monkeypatch.setattr(subprocess, "run", _timeout)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_handles_file_not_found(monkeypatch, tmp_path: Path):
    def _fnf(*a, **kw):
        raise FileNotFoundError("git not installed")
    monkeypatch.setattr(subprocess, "run", _fnf)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_handles_subprocess_error(monkeypatch, tmp_path: Path):
    def _err(*a, **kw):
        raise subprocess.SubprocessError("generic error")
    monkeypatch.setattr(subprocess, "run", _err)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_empty_stdout_returns_none_commit(monkeypatch, tmp_path: Path):
    """git rev-parse HEAD 返 0 但 stdout 为空 → commit=None。"""
    def _fake_run(cmd, *args, **kwargs):
        return subprocess.CompletedProcess(
            cmd, returncode=0, stdout="", stderr=""
        )
    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None


def test_get_git_provenance_nonzero_returncode_returns_none_commit(monkeypatch, tmp_path: Path):
    """git rev-parse HEAD 返非 0 → commit=None。"""
    call_count = {"n": 0}

    def _fake_run(cmd, *args, **kwargs):
        call_count["n"] += 1
        # 第一次（rev-parse HEAD）返非 0
        if call_count["n"] == 1:
            return subprocess.CompletedProcess(
                cmd, returncode=1, stdout="", stderr="error"
            )
        # 第二次（status --porcelain）返 0 + 空（clean）
        return subprocess.CompletedProcess(
            cmd, returncode=0, stdout="", stderr=""
        )
    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is False  # 第二次返 0 + 空 stdout


def test_get_git_provenance_dirty_when_porcelain_nonempty(monkeypatch, tmp_path: Path):
    """git status --porcelain 输出非空 → dirty=True。"""
    call_count = {"n": 0}

    def _fake_run(cmd, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return subprocess.CompletedProcess(
                cmd, returncode=0, stdout="abc123\n", stderr=""
            )
        return subprocess.CompletedProcess(
            cmd, returncode=0, stdout=" M file.txt\n", stderr=""
        )
    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] == "abc123"
    assert result["git_dirty"] is True


def test_get_git_provenance_not_dirty_when_porcelain_empty(monkeypatch, tmp_path: Path):
    """git status --porcelain 输出空 → dirty=False。"""
    call_count = {"n": 0}

    def _fake_run(cmd, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return subprocess.CompletedProcess(
                cmd, returncode=0, stdout="abc123\n", stderr=""
            )
        return subprocess.CompletedProcess(
            cmd, returncode=0, stdout="", stderr=""
        )
    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_dirty"] is False


def test_get_git_provenance_porcelain_returncode_nonzero_dirty_false(monkeypatch, tmp_path: Path):
    """git status 返非 0 → bool(False and ...) = False → dirty=False（不是 True）。
    注意：dirty 默认 True 仅在 except 分支生效；这里 subprocess 本身成功（仅 returncode 非 0）。"""
    call_count = {"n": 0}

    def _fake_run(cmd, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return subprocess.CompletedProcess(
                cmd, returncode=0, stdout="abc123\n", stderr=""
            )
        return subprocess.CompletedProcess(
            cmd, returncode=1, stdout="", stderr=""
        )
    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = get_git_provenance(tmp_path)
    # bool(False and ...) = False
    assert result["git_dirty"] is False


def test_get_git_provenance_signature_one_param():
    import inspect
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "project_root"


# =========================================================================
# 3. get_dependency_versions 第二轮
# =========================================================================


def test_get_dependency_versions_returns_dict_type():
    result = get_dependency_versions()
    assert isinstance(result, dict)


def test_get_dependency_versions_exact_three_keys():
    result = get_dependency_versions()
    assert set(result.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_all_values_str_or_none():
    result = get_dependency_versions()
    for v in result.values():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_handles_package_not_found(monkeypatch):
    def _raise(name):
        raise importlib.metadata.PackageNotFoundError(name)
    monkeypatch.setattr(importlib.metadata, "version", _raise)
    result = get_dependency_versions()
    for v in result.values():
        assert v is None


def test_get_dependency_versions_handles_generic_exception(monkeypatch):
    def _raise(name):
        raise RuntimeError("unexpected")
    monkeypatch.setattr(importlib.metadata, "version", _raise)
    result = get_dependency_versions()
    for v in result.values():
        assert v is None


def test_get_dependency_versions_returns_actual_versions(monkeypatch):
    def _mock(name):
        return f"1.2.3-{name}"
    monkeypatch.setattr(importlib.metadata, "version", _mock)
    result = get_dependency_versions()
    assert result["pdfplumber"] == "1.2.3-pdfplumber"
    assert result["python-docx"] == "1.2.3-python-docx"
    assert result["pypdfium2"] == "1.2.3-pypdfium2"


def test_get_dependency_versions_partial_failure(monkeypatch):
    """部分包找到，部分失败 → 仅失败的为 None。"""
    def _mock(name):
        if name == "pdfplumber":
            return "1.0"
        if name == "python-docx":
            return "2.0"
        raise importlib.metadata.PackageNotFoundError(name)
    monkeypatch.setattr(importlib.metadata, "version", _mock)
    result = get_dependency_versions()
    assert result["pdfplumber"] == "1.0"
    assert result["python-docx"] == "2.0"
    assert result["pypdfium2"] is None


def test_get_dependency_versions_signature_no_params():
    import inspect
    sig = inspect.signature(get_dependency_versions)
    params = list(sig.parameters.values())
    assert len(params) == 0


# =========================================================================
# 4. build_provenance 第二轮
# =========================================================================


def test_build_provenance_returns_dict(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(result, dict)


def test_build_provenance_nine_keys(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert set(result.keys()) == {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    }


def test_build_provenance_evaluator_version_value(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["report_version"] == REPORT_VERSION


def test_build_provenance_max_chars_int_conversion(tmp_path: Path):
    """max_chars 通过 int() 转 int。"""
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(result["max_chars"], int)


def test_build_provenance_max_chars_float_truncated(tmp_path: Path):
    """float → int 截断小数部分。"""
    result = build_provenance(tmp_path, "fallback", 800.99, None)
    assert result["max_chars"] == 800


def test_build_provenance_max_chars_negative_value(tmp_path: Path):
    """负数 max_chars 也能转换（不强制 ≥0）。"""
    result = build_provenance(tmp_path, "fallback", -100, None)
    assert result["max_chars"] == -100


def test_build_provenance_max_chars_zero(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 0, None)
    assert result["max_chars"] == 0


def test_build_provenance_max_chars_large_value(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 10**9, None)
    assert result["max_chars"] == 10**9


def test_build_provenance_parser_name_value(tmp_path: Path):
    result = build_provenance(tmp_path, "kreuzberg", 800, None)
    assert result["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_none(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["parser_version"] is None


def test_build_provenance_parser_version_string(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, "v1.2.3")
    assert result["parser_version"] == "v1.2.3"


def test_build_provenance_run_timestamp_parseable_iso(tmp_path: Path):
    """timestamp 应是合法 ISO 格式。"""
    result = build_provenance(tmp_path, "fallback", 800, None)
    ts = result["run_timestamp_iso"]
    # datetime.fromisoformat 应能解析
    parsed = datetime.fromisoformat(ts)
    assert isinstance(parsed, datetime)


def test_build_provenance_run_timestamp_has_timezone(tmp_path: Path):
    """timestamp 应含时区信息（astimezone()）。"""
    result = build_provenance(tmp_path, "fallback", 800, None)
    ts = result["run_timestamp_iso"]
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None


def test_build_provenance_dependencies_dict(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(result["dependencies"], dict)


def test_build_provenance_dependencies_three_entries(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert len(result["dependencies"]) == 3


def test_build_provenance_git_commit_str_or_none(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["git_commit"] is None or isinstance(result["git_commit"], str)


def test_build_provenance_git_dirty_bool(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(result["git_dirty"], bool)


def test_build_provenance_signature_four_params():
    import inspect
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["project_root", "parser_name", "max_chars", "parser_version"]


# =========================================================================
# 5. build_devset_section 第二轮
# =========================================================================


def test_build_devset_section_returns_dict():
    manifest = SimpleNamespace(
        devset_status="incomplete",
        file_count=10,
        content_group_count=5,
        pdf_count=3,
        docx_count=7,
        categories_covered=["a", "b"],
    )
    result = build_devset_section(manifest)
    assert isinstance(result, dict)


def test_build_devset_section_six_keys():
    manifest = SimpleNamespace(
        devset_status="incomplete", file_count=0, content_group_count=0,
        pdf_count=0, docx_count=0, categories_covered=[],
    )
    result = build_devset_section(manifest)
    assert set(result.keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_build_devset_section_status_value():
    manifest = SimpleNamespace(
        devset_status="complete", file_count=0, content_group_count=0,
        pdf_count=0, docx_count=0, categories_covered=[],
    )
    result = build_devset_section(manifest)
    assert result["status"] == "complete"


def test_build_devset_section_file_count_value():
    manifest = SimpleNamespace(
        devset_status="x", file_count=42, content_group_count=0,
        pdf_count=0, docx_count=0, categories_covered=[],
    )
    result = build_devset_section(manifest)
    assert result["file_count"] == 42


def test_build_devset_section_pdf_count_value():
    manifest = SimpleNamespace(
        devset_status="x", file_count=0, content_group_count=0,
        pdf_count=3, docx_count=0, categories_covered=[],
    )
    result = build_devset_section(manifest)
    assert result["pdf_count"] == 3


def test_build_devset_section_docx_count_value():
    manifest = SimpleNamespace(
        devset_status="x", file_count=0, content_group_count=0,
        pdf_count=0, docx_count=9, categories_covered=[],
    )
    result = build_devset_section(manifest)
    assert result["docx_count"] == 9


def test_build_devset_section_content_group_count_value():
    manifest = SimpleNamespace(
        devset_status="x", file_count=0, content_group_count=11,
        pdf_count=0, docx_count=0, categories_covered=[],
    )
    result = build_devset_section(manifest)
    assert result["content_group_count"] == 11


def test_build_devset_section_categories_covered_value():
    manifest = SimpleNamespace(
        devset_status="x", file_count=0, content_group_count=0,
        pdf_count=0, docx_count=0, categories_covered=["x", "y"],
    )
    result = build_devset_section(manifest)
    assert result["categories_covered"] == ["x", "y"]


def test_build_devset_section_empty_categories_list():
    manifest = SimpleNamespace(
        devset_status="x", file_count=0, content_group_count=0,
        pdf_count=0, docx_count=0, categories_covered=[],
    )
    result = build_devset_section(manifest)
    assert result["categories_covered"] == []


def test_build_devset_section_field_types_preserved():
    """各字段类型应保留（int 不被强转）。"""
    manifest = SimpleNamespace(
        devset_status="x", file_count=1, content_group_count=2,
        pdf_count=3, docx_count=4, categories_covered=["a"],
    )
    result = build_devset_section(manifest)
    assert isinstance(result["file_count"], int)
    assert isinstance(result["content_group_count"], int)
    assert isinstance(result["pdf_count"], int)
    assert isinstance(result["docx_count"], int)
    assert isinstance(result["categories_covered"], list)


def test_build_devset_section_signature_one_param():
    import inspect
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "manifest"


# =========================================================================
# 6. aggregate_summary 第二轮
# =========================================================================


def test_aggregate_summary_returns_dict_type():
    result = aggregate_summary([])
    assert isinstance(result, dict)


def test_aggregate_summary_four_top_level_keys():
    result = aggregate_summary([])
    assert set(result.keys()) == {
        "counts", "success_rates", "ratio_macro_averages", "silent_drop_total"
    }


def test_aggregate_summary_empty_input_counts_dict():
    result = aggregate_summary([])
    assert isinstance(result["counts"], dict)


def test_aggregate_summary_empty_input_success_rates_dict():
    result = aggregate_summary([])
    assert isinstance(result["success_rates"], dict)


def test_aggregate_summary_empty_input_ratio_macro_averages_dict():
    result = aggregate_summary([])
    assert isinstance(result["ratio_macro_averages"], dict)


def test_aggregate_summary_empty_input_silent_drop_total_none():
    result = aggregate_summary([])
    assert result["silent_drop_total"] is None


def test_aggregate_summary_counts_single_metric_only():
    """counts 只含 element_count_total（_COUNT_METRICS）。"""
    result = aggregate_summary([])
    assert set(result["counts"].keys()) == {"element_count_total"}


def test_aggregate_summary_success_rates_single_metric_only():
    """success_rates 只含 pipeline_success。"""
    result = aggregate_summary([])
    assert set(result["success_rates"].keys()) == {"pipeline_success"}


def test_aggregate_summary_ratio_macro_averages_12_metrics():
    """ratio_macro_averages 应含全 12 个 _RATIO_METRICS。"""
    result = aggregate_summary([])
    assert set(result["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)
    assert len(result["ratio_macro_averages"]) == 12


def test_aggregate_summary_counts_with_one_value():
    per_doc = [{"metrics": {"element_count_total": {"value": 10}}}]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 10
    assert result["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_counts_sum_aggregates():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": 20}}},
        {"metrics": {"element_count_total": {"value": 30}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 60
    assert result["counts"]["element_count_total"]["participating_docs"] == 3


def test_aggregate_summary_counts_excludes_none_values():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": 30}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 40
    assert result["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_all_none_sum_is_none():
    per_doc = [
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] is None
    assert result["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_success_rate_all_pass():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    result = aggregate_summary(per_doc)
    sr = result["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 2
    assert sr["rate"] == 1.0


def test_aggregate_summary_success_rate_all_fail():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    result = aggregate_summary(per_doc)
    sr = result["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["rate"] == 0.0


def test_aggregate_summary_success_rate_half_pass():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    result = aggregate_summary(per_doc)
    sr = result["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2
    assert sr["rate"] == 0.5


def test_aggregate_summary_success_rate_empty_input():
    result = aggregate_summary([])
    sr = result["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 0
    assert sr["rate"] is None


def test_aggregate_summary_success_rate_none_value_not_counted():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": None}}},
    ]
    result = aggregate_summary(per_doc)
    sr = result["success_rates"]["pipeline_success"]
    # None 不算 success，但 total 仍含此 doc
    assert sr["success_count"] == 1
    assert sr["total"] == 2
    assert sr["rate"] == 0.5


def test_aggregate_summary_ratio_macro_average_extreme_zero():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.0}}},
        {"metrics": {"schema_valid": {"value": 0.0}}},
    ]
    result = aggregate_summary(per_doc)
    rm = result["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] == 0.0
    assert rm["participating_docs"] == 2


def test_aggregate_summary_ratio_macro_average_extreme_one():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 1.0}}},
    ]
    result = aggregate_summary(per_doc)
    rm = result["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] == 1.0


def test_aggregate_summary_ratio_macro_average_mixed_zero_one():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.0}}},
        {"metrics": {"schema_valid": {"value": 1.0}}},
    ]
    result = aggregate_summary(per_doc)
    rm = result["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] == 0.5


def test_aggregate_summary_ratio_macro_average_with_some_null():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.5}}},
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": 1.0}}},
    ]
    result = aggregate_summary(per_doc)
    rm = result["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] == 0.75
    assert rm["participating_docs"] == 2
    assert rm["not_evaluated"] == 1


def test_aggregate_summary_ratio_macro_average_all_null():
    per_doc = [
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    result = aggregate_summary(per_doc)
    rm = result["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] is None
    assert rm["participating_docs"] == 0
    assert rm["not_evaluated"] == 2


def test_aggregate_summary_silent_drop_total_single_value():
    per_doc = [{"metrics": {"silent_drop_count": {"value": 5}}}]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] == 5


def test_aggregate_summary_silent_drop_total_aggregates():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 5}}},
        {"metrics": {"silent_drop_count": {"value": 10}}},
        {"metrics": {"silent_drop_count": {"value": 0}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] == 15


def test_aggregate_summary_silent_drop_total_with_none():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 5}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] == 5


def test_aggregate_summary_silent_drop_total_all_none():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] is None


def test_aggregate_summary_does_not_mutate_input():
    per_doc = [{"metrics": {"element_count_total": {"value": 5}}}]
    import copy
    snapshot = copy.deepcopy(per_doc)
    aggregate_summary(per_doc)
    assert per_doc == snapshot


def test_aggregate_summary_handles_missing_metrics_field():
    """per_doc 完全没 metrics 字段 → aggregate_summary 抛 KeyError。
    这是已知行为：函数假定每个 doc 都有 'metrics' 字段。"""
    per_doc = [{}, {}]
    with pytest.raises(KeyError):
        aggregate_summary(per_doc)


def test_aggregate_summary_handles_per_doc_with_empty_metrics():
    per_doc = [{"metrics": {}}, {"metrics": {}}]
    result = aggregate_summary(per_doc)
    assert "counts" in result


def test_aggregate_summary_handles_metrics_value_no_value_key():
    """metrics[name] 没有 'value' key → 视为 None。"""
    per_doc = [{"metrics": {"element_count_total": {"reason": "x"}}}]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] is None


def test_aggregate_summary_unknown_metrics_ignored():
    """未知 metric 名应被忽略。"""
    per_doc = [{"metrics": {"unknown_metric": {"value": 999}}}]
    result = aggregate_summary(per_doc)
    # 不应包含 unknown_metric
    for section in ["counts", "success_rates", "ratio_macro_averages"]:
        assert "unknown_metric" not in result[section]


def test_aggregate_summary_large_input_100_docs():
    """100 个 doc 性能测试。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": i}, "pipeline_success": {"value": True}}}
        for i in range(100)
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == sum(range(100))
    assert result["success_rates"]["pipeline_success"]["success_count"] == 100


def test_aggregate_summary_signature_one_param():
    import inspect
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "per_doc_results"


def test_aggregate_summary_counts_zero_values_participate():
    """value=0 仍参与（不为 None）。"""
    per_doc = [{"metrics": {"element_count_total": {"value": 0}}}]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["participating_docs"] == 1
    assert result["counts"]["element_count_total"]["sum"] == 0


# =========================================================================
# 7. __all__ 与模块结构
# =========================================================================


def test_all_is_list():
    assert isinstance(report_all, list)


def test_all_has_five_entries():
    assert len(report_all) == 5


def test_all_contains_build_provenance():
    assert "build_provenance" in report_all


def test_all_contains_build_devset_section():
    assert "build_devset_section" in report_all


def test_all_contains_aggregate_summary():
    assert "aggregate_summary" in report_all


def test_all_contains_get_git_provenance():
    assert "get_git_provenance" in report_all


def test_all_contains_get_dependency_versions():
    assert "get_dependency_versions" in report_all


def test_all_exact_set():
    assert set(report_all) == {
        "build_provenance", "build_devset_section", "aggregate_summary",
        "get_git_provenance", "get_dependency_versions",
    }


def test_all_does_not_include_internal_constants():
    """_RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 不应在 __all__。"""
    assert "_RATIO_METRICS" not in report_all
    assert "_COUNT_METRICS" not in report_all
    assert "_SUCCESS_BOOL_METRICS" not in report_all


def test_module_imports_subprocess():
    import evaluation.report as mod
    assert hasattr(mod, "subprocess")


def test_module_imports_datetime():
    import evaluation.report as mod
    assert hasattr(mod, "datetime")


def test_module_imports_path():
    import evaluation.report as mod
    assert hasattr(mod, "Path")


def test_module_imports_evaluator_version():
    import evaluation.report as mod
    assert hasattr(mod, "EVALUATOR_VERSION")


def test_module_imports_report_version():
    import evaluation.report as mod
    assert hasattr(mod, "REPORT_VERSION")


def test_module_constants_present():
    import evaluation.report as mod
    assert hasattr(mod, "_RATIO_METRICS")
    assert hasattr(mod, "_COUNT_METRICS")
    assert hasattr(mod, "_SUCCESS_BOOL_METRICS")
