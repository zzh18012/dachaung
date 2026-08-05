r"""evaluation/report.py 边角测试 - 第九轮（Round 213）。

补强已有 base/edges/edges2-8（共 ~862 测试）未覆盖的深度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元组类型 / 内容 / 长度
- EVALUATOR_VERSION / REPORT_VERSION 常量
- get_git_provenance subprocess 各错误路径（TimeoutExpired / 不存在目录）
- get_dependency_versions 各包查找路径
- build_provenance 9 字段精确值 / max_chars int 强制 / run_timestamp_iso 格式
- build_devset_section 6 字段
- aggregate_summary 4 top keys / 各聚合分支 / 不混合
- 模块结构 / imports / __all__ / future annotations
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
# 模块结构
# =========================================================================


def test_module_all_exact_set():
    import evaluation.report as m
    assert set(m.__all__) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_all_is_list():
    import evaluation.report as m
    assert isinstance(m.__all__, list)


def test_module_all_length_is_five():
    import evaluation.report as m
    assert len(m.__all__) == 5


def test_module_all_no_duplicates():
    import evaluation.report as m
    assert len(set(m.__all__)) == len(m.__all__)


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


def test_module_imports_evaluator_version():
    import evaluation.report as m
    assert hasattr(m, "EVALUATOR_VERSION")


def test_module_imports_report_version():
    import evaluation.report as m
    assert hasattr(m, "REPORT_VERSION")


def test_module_docstring_present():
    import evaluation.report as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_aggregation_rules():
    import evaluation.report as m
    doc = m.__doc__
    assert "counts" in doc or "求和" in doc
    assert "macro" in doc.lower() or "平均" in doc


def test_module_uses_future_annotations():
    import evaluation.report as m
    sig = inspect.signature(m.aggregate_summary)
    assert isinstance(sig.return_annotation, str)


def test_module_no_silence_unused():
    import evaluation.report as m
    assert not hasattr(m, "_silence_unused_import")


# =========================================================================
# 模块常量
# =========================================================================


def test_ratio_metrics_is_tuple():
    assert isinstance(_RATIO_METRICS, tuple)


def test_ratio_metrics_length_is_12():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_no_duplicates():
    assert len(set(_RATIO_METRICS)) == len(_RATIO_METRICS)


def test_ratio_metrics_contains_expected_names():
    expected = {
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
    }
    assert set(_RATIO_METRICS) == expected


def test_ratio_metrics_excludes_figure_caption():
    """figure_caption_* 始终 null，不参与 macro average。"""
    for name in _RATIO_METRICS:
        assert not name.startswith("figure_caption")


def test_ratio_metrics_excludes_counts():
    assert "element_count_total" not in _RATIO_METRICS


def test_ratio_metrics_excludes_pipeline_success():
    assert "pipeline_success" not in _RATIO_METRICS


def test_count_metrics_is_tuple():
    assert isinstance(_COUNT_METRICS, tuple)


def test_count_metrics_length_is_one():
    assert len(_COUNT_METRICS) == 1


def test_count_metrics_value():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_is_tuple():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_success_bool_metrics_length_is_one():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_success_bool_metrics_value():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


# =========================================================================
# EVALUATOR_VERSION / REPORT_VERSION 常量
# =========================================================================


def test_evaluator_version_is_str():
    assert isinstance(EVALUATOR_VERSION, str)


def test_evaluator_version_value():
    """本 worktree 不动 evaluator_version（指示线在审 v2.x）。"""
    assert EVALUATOR_VERSION == "1.1"


def test_report_version_is_str():
    assert isinstance(REPORT_VERSION, str)


def test_report_version_value():
    assert REPORT_VERSION == "1.1"


def test_evaluator_version_nonempty():
    assert len(EVALUATOR_VERSION) > 0


def test_report_version_nonempty():
    assert len(REPORT_VERSION) > 0


# =========================================================================
# get_git_provenance 签名 + 路径
# =========================================================================


def test_get_git_provenance_signature():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters)
    assert params == ["project_root"]


def test_get_git_provenance_return_annotation_str():
    sig = inspect.signature(get_git_provenance)
    assert sig.return_annotation == "dict[str, Any]"


def test_get_git_provenance_callable():
    assert callable(get_git_provenance)


def test_get_git_provenance_returns_dict():
    """真实仓库根 → 返回 dict。"""
    root = Path(__file__).resolve().parent.parent
    result = get_git_provenance(root)
    assert isinstance(result, dict)


def test_get_git_provenance_keys_exact():
    root = Path(__file__).resolve().parent.parent
    result = get_git_provenance(root)
    assert set(result.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_commit_is_str_or_none():
    root = Path(__file__).resolve().parent.parent
    result = get_git_provenance(root)
    assert result["git_commit"] is None or isinstance(result["git_commit"], str)


def test_get_git_provenance_dirty_is_bool():
    root = Path(__file__).resolve().parent.parent
    result = get_git_provenance(root)
    assert isinstance(result["git_dirty"], bool)


def test_get_git_provenance_real_repo_commit_is_hex():
    root = Path(__file__).resolve().parent.parent
    result = get_git_provenance(root)
    if result["git_commit"] is not None:
        # git rev-parse HEAD 返回 40 字符 hex
        assert len(result["git_commit"]) == 40
        assert all(c in "0123456789abcdef" for c in result["git_commit"])


def test_get_git_provenance_nonexistent_dir_returns_none_commit():
    """不存在的目录 → subprocess 失败 → commit=None。"""
    result = get_git_provenance(Path("/nonexistent/path/xyz"))
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_nonexistent_dir_returns_dict():
    result = get_git_provenance(Path("/nonexistent/path/xyz"))
    assert isinstance(result, dict)
    assert set(result.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_subprocess_timeout_safe(monkeypatch, tmp_path):
    """subprocess.TimeoutExpired → 安全返回 None+True。"""
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=10)

    monkeypatch.setattr("subprocess.run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_oserror_safe(monkeypatch, tmp_path):
    """OSError → 安全返回 None+True。"""
    def fake_run(*args, **kwargs):
        raise OSError("simulated")

    monkeypatch.setattr("subprocess.run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_subprocess_error_safe(monkeypatch, tmp_path):
    """subprocess.SubprocessError → 安全返回。"""
    def fake_run(*args, **kwargs):
        raise subprocess.SubprocessError("simulated")

    monkeypatch.setattr("subprocess.run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


# =========================================================================
# get_dependency_versions 签名 + 路径
# =========================================================================


def test_get_dependency_versions_signature():
    sig = inspect.signature(get_dependency_versions)
    params = list(sig.parameters)
    assert params == []


def test_get_dependency_versions_return_annotation_str():
    sig = inspect.signature(get_dependency_versions)
    assert sig.return_annotation == "dict[str, str | None]"


def test_get_dependency_versions_callable():
    assert callable(get_dependency_versions)


def test_get_dependency_versions_returns_dict():
    result = get_dependency_versions()
    assert isinstance(result, dict)


def test_get_dependency_versions_has_three_keys():
    result = get_dependency_versions()
    assert set(result.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_str_or_none():
    result = get_dependency_versions()
    for k, v in result.items():
        assert v is None or isinstance(v, str), k


# =========================================================================
# build_provenance 签名 + 字段
# =========================================================================


def test_build_provenance_signature():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters)
    assert params == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_build_provenance_return_annotation_str():
    sig = inspect.signature(build_provenance)
    assert sig.return_annotation == "dict[str, Any]"


def test_build_provenance_callable():
    assert callable(build_provenance)


def test_build_provenance_returns_dict(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(result, dict)


def test_build_provenance_keys_exact(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    expected = {
        "git_commit", "git_dirty",
        "evaluator_version", "report_version",
        "parser_name", "parser_version",
        "dependencies", "max_chars", "run_timestamp_iso",
    }
    assert set(result.keys()) == expected


def test_build_provenance_nine_keys(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert len(result) == 9


def test_build_provenance_evaluator_version_constant(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_constant(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_propagated(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["parser_name"] == "fallback"


def test_build_provenance_parser_name_kreuzberg(tmp_path):
    result = build_provenance(tmp_path, "kreuzberg", 800, "1.2.3")
    assert result["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_propagated(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert result["parser_version"] == "0.1.0"


def test_build_provenance_parser_version_none_ok(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["parser_version"] is None


def test_build_provenance_max_chars_int_coercion_from_int(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["max_chars"] == 800
    assert isinstance(result["max_chars"], int)


def test_build_provenance_max_chars_int_coercion_from_float(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800.0, None)
    assert result["max_chars"] == 800
    assert isinstance(result["max_chars"], int)


def test_build_provenance_max_chars_int_coercion_from_str(tmp_path):
    """int("800") works. int("800.0") would fail. str 数字 OK。"""
    result = build_provenance(tmp_path, "fallback", "800", None)
    assert result["max_chars"] == 800
    assert isinstance(result["max_chars"], int)


def test_build_provenance_dependencies_is_dict(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(result["dependencies"], dict)


def test_build_provenance_dependencies_three_keys(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert set(result["dependencies"].keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_build_provenance_run_timestamp_iso_format(tmp_path):
    """run_timestamp_iso 是 ISO 8601 格式。"""
    result = build_provenance(tmp_path, "fallback", 800, None)
    ts = result["run_timestamp_iso"]
    assert isinstance(ts, str)
    assert "T" in ts  # ISO 8601 datetime 分隔


def test_build_provenance_run_timestamp_iso_parseable(tmp_path):
    """run_timestamp_iso 能被 datetime.fromisoformat 解析。"""
    result = build_provenance(tmp_path, "fallback", 800, None)
    ts = result["run_timestamp_iso"]
    datetime.fromisoformat(ts)  # 不抛即可


def test_build_provenance_run_timestamp_near_now(tmp_path):
    """run_timestamp_iso 应在调用时间附近（±60 秒）。"""
    before = datetime.now().astimezone()
    result = build_provenance(tmp_path, "fallback", 800, None)
    after = datetime.now().astimezone()
    ts = datetime.fromisoformat(result["run_timestamp_iso"])
    assert before <= ts <= after or (ts - before).total_seconds() < 5


def test_build_provenance_git_commit_str_or_none(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["git_commit"] is None or isinstance(result["git_commit"], str)


def test_build_provenance_git_dirty_bool(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(result["git_dirty"], bool)


# =========================================================================
# build_devset_section 签名 + 字段
# =========================================================================


class _FakeManifest:
    """模拟 Manifest 对象（build_devset_section 只读 6 个属性）。"""

    def __init__(self, status="incomplete", file_count=1, content_group_count=1,
                 pdf_count=1, docx_count=0, categories_covered=None):
        self.devset_status = status
        self.file_count = file_count
        self.content_group_count = content_group_count
        self.pdf_count = pdf_count
        self.docx_count = docx_count
        self.categories_covered = categories_covered if categories_covered is not None else ["text"]


def test_build_devset_section_signature():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters)
    assert params == ["manifest"]


def test_build_devset_section_return_annotation_str():
    sig = inspect.signature(build_devset_section)
    assert sig.return_annotation == "dict[str, Any]"


def test_build_devset_section_callable():
    assert callable(build_devset_section)


def test_build_devset_section_returns_dict():
    result = build_devset_section(_FakeManifest())
    assert isinstance(result, dict)


def test_build_devset_section_keys_exact():
    result = build_devset_section(_FakeManifest())
    expected = {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }
    assert set(result.keys()) == expected


def test_build_devset_section_six_keys():
    result = build_devset_section(_FakeManifest())
    assert len(result) == 6


def test_build_devset_section_status_propagated():
    result = build_devset_section(_FakeManifest(status="complete"))
    assert result["status"] == "complete"


def test_build_devset_section_file_count_propagated():
    result = build_devset_section(_FakeManifest(file_count=42))
    assert result["file_count"] == 42


def test_build_devset_section_content_group_count_propagated():
    result = build_devset_section(_FakeManifest(content_group_count=7))
    assert result["content_group_count"] == 7


def test_build_devset_section_pdf_count_propagated():
    result = build_devset_section(_FakeManifest(pdf_count=3))
    assert result["pdf_count"] == 3


def test_build_devset_section_docx_count_propagated():
    result = build_devset_section(_FakeManifest(docx_count=2))
    assert result["docx_count"] == 2


def test_build_devset_section_categories_covered_propagated():
    cats = ["text", "table"]
    result = build_devset_section(_FakeManifest(categories_covered=cats))
    assert result["categories_covered"] == cats


def test_build_devset_section_empty_categories():
    result = build_devset_section(_FakeManifest(categories_covered=[]))
    assert result["categories_covered"] == []


# =========================================================================
# aggregate_summary 签名 + 字段
# =========================================================================


def test_aggregate_summary_signature():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters)
    assert params == ["per_doc_results"]


def test_aggregate_summary_return_annotation_str():
    sig = inspect.signature(aggregate_summary)
    assert sig.return_annotation == "dict[str, Any]"


def test_aggregate_summary_callable():
    assert callable(aggregate_summary)


def test_aggregate_summary_returns_dict():
    result = aggregate_summary([])
    assert isinstance(result, dict)


def test_aggregate_summary_has_four_top_keys():
    result = aggregate_summary([])
    expected = {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}
    assert set(result.keys()) == expected


# =========================================================================
# aggregate_summary counts 深度
# =========================================================================


def test_aggregate_summary_counts_has_element_count_total_key():
    result = aggregate_summary([])
    assert "element_count_total" in result["counts"]


def test_aggregate_summary_counts_sum_none_for_empty():
    result = aggregate_summary([])
    assert result["counts"]["element_count_total"]["sum"] is None


def test_aggregate_summary_counts_participating_docs_zero_for_empty():
    result = aggregate_summary([])
    assert result["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_counts_sum_aggregates():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": 15}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 30
    assert result["counts"]["element_count_total"]["participating_docs"] == 3


def test_aggregate_summary_counts_skips_none():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": 10}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 15
    assert result["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_skips_missing_metric():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {}},  # 完全缺该 metric
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 5
    assert result["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_counts_each_entry_two_keys():
    result = aggregate_summary([])
    for k, v in result["counts"].items():
        assert set(v.keys()) == {"sum", "participating_docs"}, k


# =========================================================================
# aggregate_summary success_rates 深度
# =========================================================================


def test_aggregate_summary_success_rates_has_pipeline_success():
    result = aggregate_summary([])
    assert "pipeline_success" in result["success_rates"]


def test_aggregate_summary_success_rates_zero_docs_rate_none():
    result = aggregate_summary([])
    rate_info = result["success_rates"]["pipeline_success"]
    assert rate_info["rate"] is None
    assert rate_info["total"] == 0
    assert rate_info["success_count"] == 0


def test_aggregate_summary_success_rates_all_success():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    result = aggregate_summary(per_doc)
    rate_info = result["success_rates"]["pipeline_success"]
    assert rate_info["success_count"] == 2
    assert rate_info["total"] == 2
    assert rate_info["rate"] == 1.0


def test_aggregate_summary_success_rates_no_success():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    result = aggregate_summary(per_doc)
    rate_info = result["success_rates"]["pipeline_success"]
    assert rate_info["success_count"] == 0
    assert rate_info["rate"] == 0.0


def test_aggregate_summary_success_rates_half():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    result = aggregate_summary(per_doc)
    rate_info = result["success_rates"]["pipeline_success"]
    assert rate_info["success_count"] == 1
    assert rate_info["total"] == 2
    assert rate_info["rate"] == 0.5


def test_aggregate_summary_success_rates_skips_none_value():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": None}}},  # 不算成功
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    result = aggregate_summary(per_doc)
    rate_info = result["success_rates"]["pipeline_success"]
    # total 仍是 3（None 不算成功但也算 total）
    assert rate_info["total"] == 3
    assert rate_info["success_count"] == 1
    assert rate_info["rate"] == 1 / 3


def test_aggregate_summary_success_rates_each_entry_three_keys():
    result = aggregate_summary([])
    for k, v in result["success_rates"].items():
        assert set(v.keys()) == {"success_count", "total", "rate"}, k


# =========================================================================
# aggregate_summary ratio_macro_averages 深度
# =========================================================================


def test_aggregate_summary_ratio_macro_averages_has_12_keys():
    result = aggregate_summary([])
    assert len(result["ratio_macro_averages"]) == 12


def test_aggregate_summary_ratio_macro_averages_keys_exact():
    result = aggregate_summary([])
    assert set(result["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


def test_aggregate_summary_ratio_macro_averages_none_for_empty():
    result = aggregate_summary([])
    for k, v in result["ratio_macro_averages"].items():
        assert v["macro_average"] is None, k
        assert v["participating_docs"] == 0, k
        assert v["not_evaluated"] == 0, k


def test_aggregate_summary_ratio_macro_average_calc():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
        {"metrics": {"schema_valid": {"value": 0.0}}},
    ]
    result = aggregate_summary(per_doc)
    info = result["ratio_macro_averages"]["schema_valid"]
    assert info["macro_average"] == 0.5
    assert info["participating_docs"] == 3
    assert info["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_skips_none():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": 0.0}}},
    ]
    result = aggregate_summary(per_doc)
    info = result["ratio_macro_averages"]["schema_valid"]
    assert info["macro_average"] == 0.5
    assert info["participating_docs"] == 2
    assert info["not_evaluated"] == 1


def test_aggregate_summary_ratio_macro_skips_missing():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {}},  # 缺该 metric
    ]
    result = aggregate_summary(per_doc)
    info = result["ratio_macro_averages"]["schema_valid"]
    assert info["macro_average"] == 1.0
    assert info["participating_docs"] == 1
    assert info["not_evaluated"] == 1


def test_aggregate_summary_ratio_macro_each_entry_three_keys():
    result = aggregate_summary([])
    for k, v in result["ratio_macro_averages"].items():
        assert set(v.keys()) == {"macro_average", "participating_docs", "not_evaluated"}, k


# =========================================================================
# aggregate_summary silent_drop_total
# =========================================================================


def test_aggregate_summary_silent_drop_total_none_for_empty():
    result = aggregate_summary([])
    assert result["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_total_sums():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
        {"metrics": {"silent_drop_count": {"value": 2}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] == 10


def test_aggregate_summary_silent_drop_skips_none():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_zero_values_count():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 0}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] == 5


def test_aggregate_summary_silent_drop_all_zeros():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 0}}},
        {"metrics": {"silent_drop_count": {"value": 0}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] == 0


def test_aggregate_summary_silent_drop_all_none_returns_none():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] is None


# =========================================================================
# aggregate_summary 类型分离
# =========================================================================


def test_aggregate_summary_does_not_mix_count_and_ratio():
    """counts 不应含 ratio metric 名。"""
    result = aggregate_summary([])
    for k in result["counts"]:
        assert k not in _RATIO_METRICS
        assert k != "pipeline_success"


def test_aggregate_summary_does_not_mix_success_and_ratio():
    """success_rates 不应含 ratio metric 名。"""
    result = aggregate_summary([])
    for k in result["success_rates"]:
        assert k not in _RATIO_METRICS


def test_aggregate_summary_does_not_mix_count_and_success():
    """counts 不应含 success_rates metric 名。"""
    result = aggregate_summary([])
    for k in result["counts"]:
        assert k not in _SUCCESS_BOOL_METRICS


# =========================================================================
# aggregate_summary 综合行为
# =========================================================================


def test_aggregate_summary_idempotent():
    per_doc = [{"metrics": {"pipeline_success": {"value": True}}}]
    a = aggregate_summary(per_doc)
    b = aggregate_summary(per_doc)
    assert a == b


def test_aggregate_summary_returns_new_dict_each_call():
    per_doc = [{"metrics": {"pipeline_success": {"value": True}}}]
    a = aggregate_summary(per_doc)
    b = aggregate_summary(per_doc)
    assert a is not b


def test_aggregate_summary_full_pipeline_with_mixed_metrics():
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "element_count_total": {"value": 10},
                "schema_valid": {"value": 1.0},
                "silent_drop_count": {"value": 2},
            },
        },
        {
            "metrics": {
                "pipeline_success": {"value": False},
                "element_count_total": {"value": 5},
                "schema_valid": {"value": 0.0},
                "silent_drop_count": {"value": None},
            },
        },
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 15
    assert result["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert result["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert result["silent_drop_total"] == 2
