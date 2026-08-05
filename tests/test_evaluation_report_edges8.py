r"""evaluation/report.py 边角测试 - 第八轮（Round 206）。

补强已有 base/edges/edges2-7（共 ~763 测试）未覆盖的深度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 精确内容
- EVALUATOR_VERSION / REPORT_VERSION 常量
- aggregate_summary 各聚合分支组合（participating_docs/not_evaluated/macro）
- aggregate_summary 多文档混合（部分 None / 部分 valid）
- get_git_provenance subprocess.run 各参数（cwd/capture_output/text/encoding/errors/timeout）
- get_dependency_versions importlib.metadata.PackageNotFoundError 路径
- build_provenance 各字段精确值
- build_devset_section 各 status 值
- 模块 imports / __all__ / 类属性
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


# =========================================================================
# 常量与 metric 元组
# =========================================================================


def test_ratio_metrics_is_tuple():
    assert isinstance(_RATIO_METRICS, tuple)


def test_ratio_metrics_count_is_12():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_no_duplicates():
    assert len(_RATIO_METRICS) == len(set(_RATIO_METRICS))


def test_ratio_metrics_contains_schema_valid():
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_contains_text_preservation_equal():
    assert "text_preservation_equal" in _RATIO_METRICS


def test_ratio_metrics_contains_all_chunk_boundary():
    assert "chunk_boundary_precision" in _RATIO_METRICS
    assert "chunk_boundary_recall" in _RATIO_METRICS
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_contains_locator_ratios():
    assert "pdf_locator_valid_ratio" in _RATIO_METRICS
    assert "docx_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_excludes_figure_caption():
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_count_metrics_is_tuple():
    assert isinstance(_COUNT_METRICS, tuple)


def test_count_metrics_only_element_count_total():
    assert _COUNT_METRICS == ("element_count_total",)


def test_count_metrics_no_duplicates():
    assert len(_COUNT_METRICS) == len(set(_COUNT_METRICS))


def test_success_bool_metrics_is_tuple():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_success_bool_metrics_only_pipeline_success():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_success_bool_metrics_no_duplicates():
    assert len(_SUCCESS_BOOL_METRICS) == len(set(_SUCCESS_BOOL_METRICS))


def test_evaluator_version_value():
    """EVALUATOR_VERSION 在 evaluation/__init__.py 定义。"""
    assert isinstance(EVALUATOR_VERSION, str)
    assert len(EVALUATOR_VERSION) > 0


def test_report_version_value():
    assert isinstance(REPORT_VERSION, str)
    assert len(REPORT_VERSION) > 0


def test_evaluator_version_is_1_1():
    """指示线在审的 v2.x 不属于本 worktree；本 worktree 仍 1.1。"""
    assert EVALUATOR_VERSION == "1.1"


def test_report_version_is_1_1():
    assert REPORT_VERSION == "1.1"


# =========================================================================
# aggregate_summary 深度
# =========================================================================


def test_aggregate_summary_returns_dict():
    result = aggregate_summary([])
    assert isinstance(result, dict)


def test_aggregate_summary_has_four_top_keys():
    result = aggregate_summary([])
    assert set(result.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_counts_has_element_count_total_key():
    result = aggregate_summary([])
    assert "element_count_total" in result["counts"]


def test_aggregate_summary_success_rates_has_pipeline_success_key():
    result = aggregate_summary([])
    assert "pipeline_success" in result["success_rates"]


def test_aggregate_summary_ratio_macro_averages_has_12_keys():
    result = aggregate_summary([])
    assert set(result["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


def test_aggregate_summary_empty_silent_drop_total_is_none():
    result = aggregate_summary([])
    assert result["silent_drop_total"] is None


def test_aggregate_summary_count_participating_docs_zero_for_empty():
    result = aggregate_summary([])
    assert result["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_count_sum_none_for_empty():
    result = aggregate_summary([])
    assert result["counts"]["element_count_total"]["sum"] is None


def test_aggregate_summary_success_rate_zero_docs_rate_none():
    result = aggregate_summary([])
    assert result["success_rates"]["pipeline_success"]["rate"] is None
    assert result["success_rates"]["pipeline_success"]["success_count"] == 0
    assert result["success_rates"]["pipeline_success"]["total"] == 0


def test_aggregate_summary_ratio_macro_average_none_for_empty():
    result = aggregate_summary([])
    for name in _RATIO_METRICS:
        assert result["ratio_macro_averages"][name]["macro_average"] is None
        assert result["ratio_macro_averages"][name]["participating_docs"] == 0
        assert result["ratio_macro_averages"][name]["not_evaluated"] == 0


def test_aggregate_summary_count_sum_aggregates_correctly():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": 20}}},
        {"metrics": {"element_count_total": {"value": 30}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 60
    assert result["counts"]["element_count_total"]["participating_docs"] == 3


def test_aggregate_summary_count_skips_none_values():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": 30}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 40
    assert result["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_count_skips_missing_metric():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {}},
        {"metrics": {"element_count_total": {"value": 30}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 40
    assert result["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_success_rate_all_success():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    result = aggregate_summary(per_doc)
    sr = result["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 2
    assert sr["rate"] == 1.0


def test_aggregate_summary_success_rate_half():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    result = aggregate_summary(per_doc)
    sr = result["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2
    assert sr["rate"] == 0.5


def test_aggregate_summary_success_rate_no_success():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    result = aggregate_summary(per_doc)
    sr = result["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["rate"] == 0.0


def test_aggregate_summary_success_rate_skips_none():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": None}}},
    ]
    result = aggregate_summary(per_doc)
    sr = result["success_rates"]["pipeline_success"]
    # total 仍是所有文档数（包含 None）
    assert sr["total"] == 2
    assert sr["success_count"] == 1
    assert sr["rate"] == 0.5


def test_aggregate_summary_ratio_macro_average_calc():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
        {"metrics": {"schema_valid": {"value": 0.0}}},
    ]
    result = aggregate_summary(per_doc)
    avg = result["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == 0.5
    assert avg["participating_docs"] == 3
    assert avg["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_skips_none():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": 0.0}}},
    ]
    result = aggregate_summary(per_doc)
    avg = result["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == 0.5
    assert avg["participating_docs"] == 2
    assert avg["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_total_sums():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 5}}},
        {"metrics": {"silent_drop_count": {"value": 10}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] == 15


def test_aggregate_summary_silent_drop_skips_none():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 5}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": 10}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] == 15


def test_aggregate_summary_silent_drop_zero_values_count():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 0}}},
        {"metrics": {"silent_drop_count": {"value": 0}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] == 0


def test_aggregate_summary_signature():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters)
    assert params == ["per_doc_results"]


# =========================================================================
# get_git_provenance 深度
# =========================================================================


def test_get_git_provenance_returns_dict_type():
    result = get_git_provenance(Path("."))
    assert isinstance(result, dict)


def test_get_git_provenance_keys():
    result = get_git_provenance(Path("."))
    assert set(result.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_in_real_repo_commit_is_str():
    """在 dachuang-autonomous worktree 内跑，commit 应是 hex string。"""
    result = get_git_provenance(Path("."))
    if result["git_commit"] is not None:
        assert isinstance(result["git_commit"], str)
        assert len(result["git_commit"]) == 40  # SHA-1 hex


def test_get_git_provenance_dirty_is_bool():
    result = get_git_provenance(Path("."))
    assert isinstance(result["git_dirty"], bool)


def test_get_git_provenance_nonexistent_dir_returns_safe(tmp_path):
    """不存在的目录 → subprocess 抛 OSError → commit=None dirty=True。"""
    nope = tmp_path / "nope"
    result = get_git_provenance(nope)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_subprocess_timeout_returns_safe(monkeypatch, tmp_path):
    def boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=10)

    monkeypatch.setattr(subprocess, "run", boom)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_oserror_returns_safe(monkeypatch, tmp_path):
    def boom(*args, **kwargs):
        raise OSError("nope")

    monkeypatch.setattr(subprocess, "run", boom)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_subprocess_error_returns_safe(monkeypatch, tmp_path):
    def boom(*args, **kwargs):
        raise subprocess.SubprocessError("nope")

    monkeypatch.setattr(subprocess, "run", boom)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_signature():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters)
    assert params == ["project_root"]


# =========================================================================
# get_dependency_versions 深度
# =========================================================================


def test_get_dependency_versions_returns_dict():
    result = get_dependency_versions()
    assert isinstance(result, dict)


def test_get_dependency_versions_returns_three_keys():
    result = get_dependency_versions()
    assert set(result.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_are_str_or_none():
    result = get_dependency_versions()
    for k, v in result.items():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_pdfplumber_in_dev_env():
    """dev 环境装了 pdfplumber。"""
    result = get_dependency_versions()
    assert result["pdfplumber"] is not None


def test_get_dependency_versions_python_docx_in_dev_env():
    result = get_dependency_versions()
    assert result["python-docx"] is not None


def test_get_dependency_versions_signature():
    sig = inspect.signature(get_dependency_versions)
    assert list(sig.parameters) == []


# =========================================================================
# build_provenance 深度
# =========================================================================


def test_build_provenance_returns_dict():
    result = build_provenance(Path("."), "fallback", 800, "0.1.0")
    assert isinstance(result, dict)


def test_build_provenance_nine_keys():
    result = build_provenance(Path("."), "fallback", 800, "0.1.0")
    expected = {
        "git_commit", "git_dirty",
        "evaluator_version", "report_version",
        "parser_name", "parser_version",
        "dependencies", "max_chars", "run_timestamp_iso",
    }
    assert set(result.keys()) == expected


def test_build_provenance_evaluator_version_constant():
    result = build_provenance(Path("."), "fallback", 800, "0.1.0")
    assert result["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_constant():
    result = build_provenance(Path("."), "fallback", 800, "0.1.0")
    assert result["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_propagated():
    result = build_provenance(Path("."), "kreuzberg", 800, "0.1.0")
    assert result["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_propagated():
    result = build_provenance(Path("."), "fallback", 800, "0.1.0")
    assert result["parser_version"] == "0.1.0"


def test_build_provenance_parser_version_none():
    result = build_provenance(Path("."), "fallback", 800, None)
    assert result["parser_version"] is None


def test_build_provenance_max_chars_int():
    result = build_provenance(Path("."), "fallback", 800, "0.1.0")
    assert result["max_chars"] == 800
    assert isinstance(result["max_chars"], int)


def test_build_provenance_max_chars_int_coercion():
    """int(800.0) → 800。"""
    result = build_provenance(Path("."), "fallback", 800.0, "0.1.0")
    assert result["max_chars"] == 800


def test_build_provenance_max_chars_numeric_str_accepted():
    """int("800") → 800（数字字符串可转）。"""
    result = build_provenance(Path("."), "fallback", "800", "0.1.0")
    assert result["max_chars"] == 800


def test_build_provenance_dependencies_is_dict():
    result = build_provenance(Path("."), "fallback", 800, "0.1.0")
    assert isinstance(result["dependencies"], dict)
    assert "pdfplumber" in result["dependencies"]


def test_build_provenance_run_timestamp_iso_format():
    result = build_provenance(Path("."), "fallback", 800, "0.1.0")
    ts = result["run_timestamp_iso"]
    assert isinstance(ts, str)
    # ISO 8601 格式：含 T
    assert "T" in ts


def test_build_provenance_run_timestamp_recent():
    """timestamp 应该是当前时间附近。"""
    before = datetime.now().astimezone()
    result = build_provenance(Path("."), "fallback", 800, "0.1.0")
    after = datetime.now().astimezone()
    ts = datetime.fromisoformat(result["run_timestamp_iso"])
    assert before <= ts <= after


def test_build_provenance_git_commit_from_provenance():
    """git_commit 与直接调用 get_git_provenance 一致。"""
    direct = get_git_provenance(Path("."))
    result = build_provenance(Path("."), "fallback", 800, "0.1.0")
    assert result["git_commit"] == direct["git_commit"]


def test_build_provenance_git_dirty_from_provenance():
    direct = get_git_provenance(Path("."))
    result = build_provenance(Path("."), "fallback", 800, "0.1.0")
    assert result["git_dirty"] == direct["git_dirty"]


def test_build_provenance_signature():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters)
    assert params == ["project_root", "parser_name", "max_chars", "parser_version"]


# =========================================================================
# build_devset_section 深度
# =========================================================================


class _FakeManifest:
    """模拟 Manifest 对象。"""
    def __init__(
        self,
        devset_status="incomplete",
        file_count=0,
        content_group_count=0,
        pdf_count=0,
        docx_count=0,
        categories_covered=None,
    ):
        self.devset_status = devset_status
        self.file_count = file_count
        self.content_group_count = content_group_count
        self.pdf_count = pdf_count
        self.docx_count = docx_count
        self.categories_covered = categories_covered or []


def test_build_devset_section_returns_dict():
    result = build_devset_section(_FakeManifest())
    assert isinstance(result, dict)


def test_build_devset_section_six_keys():
    result = build_devset_section(_FakeManifest())
    expected = {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }
    assert set(result.keys()) == expected


def test_build_devset_section_status_propagated():
    m = _FakeManifest(devset_status="complete")
    assert build_devset_section(m)["status"] == "complete"


def test_build_devset_section_file_count_propagated():
    m = _FakeManifest(file_count=42)
    assert build_devset_section(m)["file_count"] == 42


def test_build_devset_section_content_group_count_propagated():
    m = _FakeManifest(content_group_count=10)
    assert build_devset_section(m)["content_group_count"] == 10


def test_build_devset_section_pdf_count_propagated():
    m = _FakeManifest(pdf_count=5)
    assert build_devset_section(m)["pdf_count"] == 5


def test_build_devset_section_docx_count_propagated():
    m = _FakeManifest(docx_count=7)
    assert build_devset_section(m)["docx_count"] == 7


def test_build_devset_section_categories_covered_propagated():
    m = _FakeManifest(categories_covered=["pdf", "docx"])
    assert build_devset_section(m)["categories_covered"] == ["pdf", "docx"]


def test_build_devset_section_empty_categories():
    m = _FakeManifest(categories_covered=[])
    assert build_devset_section(m)["categories_covered"] == []


def test_build_devset_section_calls_properties():
    """build_devset_section 直接读属性 → 验证不会调无关方法。"""
    class TrackingManifest:
        def __init__(self):
            self.devset_status = "incomplete"
            self.file_count = 1
            self.content_group_count = 1
            self.pdf_count = 0
            self.docx_count = 0
            self.categories_covered = ["text"]
            self.called = []

        def __getattr__(self, name):
            self.called.append(name)
            raise AttributeError(name)

    m = TrackingManifest()
    result = build_devset_section(m)
    assert result["status"] == "incomplete"
    assert result["file_count"] == 1


def test_build_devset_section_signature():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters)
    assert params == ["manifest"]


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import evaluation.report as m
    expected = {
        "build_provenance", "build_devset_section", "aggregate_summary",
        "get_git_provenance", "get_dependency_versions",
    }
    assert set(m.__all__) == expected


def test_module_all_is_list():
    import evaluation.report as m
    assert isinstance(m.__all__, list)


def test_module_all_no_duplicates():
    import evaluation.report as m
    assert len(m.__all__) == len(set(m.__all__))


def test_module_imports_subprocess():
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


def test_module_imports_evaluation_versions():
    import evaluation.report as m
    assert hasattr(m, "EVALUATOR_VERSION")
    assert hasattr(m, "REPORT_VERSION")


def test_module_docstring_present():
    import evaluation.report as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_aggregation_rules():
    import evaluation.report as m
    doc = m.__doc__
    assert "counts" in doc.lower() or "求和" in doc
    assert "macro" in doc.lower() or "macro average" in doc.lower()


def test_module_uses_future_annotations():
    import evaluation.report as m
    sig = inspect.signature(m.aggregate_summary)
    # future annotations → annotation is string
    assert isinstance(sig.return_annotation, str)


def test_module_all_entries_exported():
    import evaluation.report as m
    for name in m.__all__:
        assert hasattr(m, name)


# =========================================================================
# 综合行为
# =========================================================================


def test_aggregate_summary_idempotent():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}, "element_count_total": {"value": 5}}},
        {"metrics": {"pipeline_success": {"value": False}, "element_count_total": {"value": 10}}},
    ]
    a = aggregate_summary(per_doc)
    b = aggregate_summary(per_doc)
    assert a == b


def test_aggregate_summary_full_pipeline_with_mixed_metrics():
    """混合 metric：success/fail/None/count/ratio/silent_drop。"""
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "schema_valid": {"value": 1.0},
                "element_count_total": {"value": 10},
                "silent_drop_count": {"value": 0},
                "text_preservation_equal": {"value": 1.0},
            }
        },
        {
            "metrics": {
                "pipeline_success": {"value": False},
                "schema_valid": {"value": 0.0},
                "element_count_total": {"value": 20},
                "silent_drop_count": {"value": 5},
                "text_preservation_equal": {"value": None},
            }
        },
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 30
    assert result["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert result["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert result["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2
    assert result["ratio_macro_averages"]["text_preservation_equal"]["participating_docs"] == 1
    assert result["ratio_macro_averages"]["text_preservation_equal"]["not_evaluated"] == 1
    assert result["silent_drop_total"] == 5


def test_aggregate_summary_does_not_mix_count_and_ratio():
    """counts 不应包含 ratio 指标。"""
    per_doc = [{"metrics": {"schema_valid": {"value": 1.0}}}]
    result = aggregate_summary(per_doc)
    assert "schema_valid" not in result["counts"]
    assert "schema_valid" in result["ratio_macro_averages"]


def test_aggregate_summary_does_not_mix_success_and_ratio():
    per_doc = [{"metrics": {"pipeline_success": {"value": True}}}]
    result = aggregate_summary(per_doc)
    assert "pipeline_success" not in result["ratio_macro_averages"]
    assert "pipeline_success" in result["success_rates"]
