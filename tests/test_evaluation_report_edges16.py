r"""evaluation/report.py 边角测试 - 第十六轮（Round 257）。

补强已有 base/edges/edges2-15（共 ~810+ 测试）未覆盖的深度：
- 源码字符串断言（inspect.getsource）：未覆盖 token
- module 文档字符串内容
- 函数签名 introspection：每个函数的 param 名/默认/kind
- aggregate_summary 详细边界：mixed null/non-null ratio values；missing metric；partial metrics dict
- build_provenance 字段类型验证
- build_devset_section 用 stub Manifest 对象测试
- get_dependency_versions 在缺 importlib.metadata 时不抛错（已在 module load 时验证）
- _RATIO_METRICS 顺序精确（顺序敏感，不能 set 比较）
- _SUCCESS_BOOL_METRICS / _COUNT_METRICS 互不相交
- summary 4 top-level keys 顺序精确
- silent_drop_total 边界
- module namespace identity（EVALUATOR_VERSION / REPORT_VERSION / datetime / subprocess）
- helpers return dict 的字段名 + 顺序精确
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
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


# =========================================================================
# 源码字符串断言（inspect.getsource）— 未覆盖 token
# =========================================================================


def test_module_source_contains_build_provenance_def():
    import evaluation.report as m

    assert "def build_provenance(" in inspect.getsource(m)


def test_module_source_contains_build_devset_section_def():
    import evaluation.report as m

    assert "def build_devset_section(" in inspect.getsource(m)


def test_module_source_contains_aggregate_summary_def():
    import evaluation.report as m

    assert "def aggregate_summary(" in inspect.getsource(m)


def test_module_source_contains_get_git_provenance_def():
    import evaluation.report as m

    assert "def get_git_provenance(" in inspect.getsource(m)


def test_module_source_contains_get_dependency_versions_def():
    import evaluation.report as m

    assert "def get_dependency_versions(" in inspect.getsource(m)


def test_module_source_contains_subprocess_run_call():
    """源码含 subprocess.run(['git', 'rev-parse', 'HEAD']）。"""
    import evaluation.report as m

    src = inspect.getsource(m)
    assert "subprocess.run" in src
    assert '"git"' in src or "'git'" in src
    assert "rev-parse" in src


def test_module_source_contains_capture_output_kwarg():
    """subprocess.run 含 capture_output=True。"""
    import evaluation.report as m

    assert "capture_output=True" in inspect.getsource(m)


def test_module_source_contains_encoding_kwarg():
    """subprocess.run 含 encoding='utf-8'。"""
    import evaluation.report as m

    assert 'encoding="utf-8"' in inspect.getsource(m)


def test_module_source_contains_errors_kwarg():
    """subprocess.run 含 errors='replace'。"""
    import evaluation.report as m

    assert 'errors="replace"' in inspect.getsource(m)


def test_module_source_contains_timeout_kwarg():
    """subprocess.run 含 timeout=10。"""
    import evaluation.report as m

    assert "timeout=10" in inspect.getsource(m)


def test_module_source_contains_status_porcelain():
    """源码含 git status --porcelain。"""
    import evaluation.report as m

    assert "status" in inspect.getsource(m) and "porcelain" in inspect.getsource(m)


def test_module_source_contains_oserror_subprocess_except():
    """源码含 except (OSError, subprocess.SubprocessError)。"""
    import evaluation.report as m

    assert "OSError" in inspect.getsource(m)
    assert "subprocess.SubprocessError" in inspect.getsource(m)


def test_module_source_contains_importlib_metadata():
    """源码含 import importlib.metadata。"""
    import evaluation.report as m

    assert "import importlib.metadata" in inspect.getsource(m)


def test_module_source_contains_pdfplumber_docx_pypdfium():
    """源码含 pdfplumber/python-docx/pypdfium2 包名。"""
    import evaluation.report as m

    src = inspect.getsource(m)
    assert "pdfplumber" in src
    assert "python-docx" in src
    assert "pypdfium2" in src


def test_module_source_contains_package_not_found_except():
    """源码含 PackageNotFoundError。"""
    import evaluation.report as m

    assert "PackageNotFoundError" in inspect.getsource(m)


def test_module_source_contains_datetime_now():
    """源码含 datetime.now().astimezone().isoformat()。"""
    import evaluation.report as m

    src = inspect.getsource(m)
    assert "datetime.now" in src
    assert "astimezone" in src
    assert "isoformat" in src


def test_module_source_contains_evaluator_version_import():
    """源码含 from evaluation import EVALUATOR_VERSION, REPORT_VERSION。"""
    import evaluation.report as m

    src = inspect.getsource(m)
    assert "from evaluation import" in src
    assert "EVALUATOR_VERSION" in src
    assert "REPORT_VERSION" in src


def test_module_source_contains_participating_docs_token():
    """源码含 participating_docs 字段。"""
    import evaluation.report as m

    assert "participating_docs" in inspect.getsource(m)


def test_module_source_contains_not_evaluated_token():
    """源码含 not_evaluated 字段。"""
    import evaluation.report as m

    assert "not_evaluated" in inspect.getsource(m)


def test_module_source_contains_macro_average_token():
    """源码含 macro_average 字段。"""
    import evaluation.report as m

    assert "macro_average" in inspect.getsource(m)


def test_module_source_contains_silent_drop_total():
    """源码含 silent_drop_total。"""
    import evaluation.report as m

    assert "silent_drop_total" in inspect.getsource(m)


def test_module_source_contains_no_mixed_score_token():
    """源码不应含 'overall_score' / 'combined_score'（不混合类型）。"""
    import evaluation.report as m

    src = inspect.getsource(m)
    assert "overall_score" not in src
    assert "combined_score" not in src


def test_module_source_does_not_contain_print():
    """源码不含 print。"""
    import evaluation.report as m

    assert "print(" not in inspect.getsource(m)


def test_module_source_contains_pypdfium2_comment():
    """源码含 pypdfium2 __version__ 注释。"""
    import evaluation.report as m

    assert "pypdfium2 模块本身没有 __version__" in inspect.getsource(m)


# =========================================================================
# 模块 docstring
# =========================================================================


def test_module_docstring_is_nonempty_string():
    import evaluation.report as m

    assert isinstance(m.__doc__, str)
    assert len(m.__doc__) > 30


def test_module_docstring_contains_aggregation_rules():
    """docstring 描述聚合规则。"""
    import evaluation.report as m

    assert "聚合" in m.__doc__ or "aggregat" in m.__doc__.lower()


def test_module_docstring_mentions_counts():
    import evaluation.report as m

    assert "counts" in m.__doc__


def test_module_docstring_mentions_success_rates():
    import evaluation.report as m

    assert "success_rates" in m.__doc__


def test_module_docstring_mentions_silent_drop():
    import evaluation.report as m

    assert "silent_drop" in m.__doc__


# =========================================================================
# 模块 namespace 完整性
# =========================================================================


def test_module_namespace_contains_constants():
    """_RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 在 namespace。"""
    import evaluation.report as m

    assert hasattr(m, "_RATIO_METRICS")
    assert hasattr(m, "_COUNT_METRICS")
    assert hasattr(m, "_SUCCESS_BOOL_METRICS")


def test_module_namespace_contains_subprocess():
    import evaluation.report as m

    assert hasattr(m, "subprocess")
    assert m.subprocess is subprocess


def test_module_namespace_contains_datetime():
    import evaluation.report as m

    assert hasattr(m, "datetime")
    assert m.datetime is datetime


def test_module_namespace_identity_evaluator_version():
    """EVALUATOR_VERSION 值与从 evaluation 重新导入一致。"""
    import evaluation.report as m
    from evaluation import EVALUATOR_VERSION as OrigEV

    assert m.EVALUATOR_VERSION == OrigEV


def test_module_namespace_identity_report_version():
    import evaluation.report as m
    from evaluation import REPORT_VERSION as OrigRV

    assert m.REPORT_VERSION == OrigRV


def test_module_all_is_list():
    import evaluation.report as m

    assert isinstance(m.__all__, list)


def test_module_all_is_not_tuple():
    import evaluation.report as m

    assert not isinstance(m.__all__, tuple)


def test_module_all_has_5_entries():
    import evaluation.report as m

    assert len(m.__all__) == 5


def test_module_all_exact():
    import evaluation.report as m

    assert m.__all__ == [
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    ]


def test_module_all_all_names_in_namespace():
    """__all__ 中所有名字都在 module namespace。"""
    import evaluation.report as m

    for name in m.__all__:
        assert hasattr(m, name)


# =========================================================================
# 常量精确（顺序敏感）
# =========================================================================


def test_ratio_metrics_is_tuple_not_list():
    import evaluation.report as m

    assert isinstance(m._RATIO_METRICS, tuple)


def test_count_metrics_is_tuple():
    import evaluation.report as m

    assert isinstance(m._COUNT_METRICS, tuple)


def test_success_bool_metrics_is_tuple():
    import evaluation.report as m

    assert isinstance(m._SUCCESS_BOOL_METRICS, tuple)


def test_ratio_metrics_order_sensitive_exact():
    """顺序敏感：不能用 set 比较。"""
    import evaluation.report as m

    assert list(m._RATIO_METRICS) == [
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
    ]


def test_count_metrics_exact():
    import evaluation.report as m

    assert list(m._COUNT_METRICS) == ["element_count_total"]


def test_success_bool_metrics_exact():
    import evaluation.report as m

    assert list(m._SUCCESS_BOOL_METRICS) == ["pipeline_success"]


def test_three_metric_groups_disjoint():
    """3 个常量集合互不相交。"""
    import evaluation.report as m

    ratio_set = set(m._RATIO_METRICS)
    count_set = set(m._COUNT_METRICS)
    success_set = set(m._SUCCESS_BOOL_METRICS)
    assert ratio_set.isdisjoint(count_set)
    assert ratio_set.isdisjoint(success_set)
    assert count_set.isdisjoint(success_set)


def test_three_metric_groups_total_14():
    """12 + 1 + 1 = 14。"""
    import evaluation.report as m

    total = len(m._RATIO_METRICS) + len(m._COUNT_METRICS) + len(m._SUCCESS_BOOL_METRICS)
    assert total == 14


def test_ratio_metrics_does_not_contain_figure_caption():
    """figure_caption_* 始终 null，不参与 macro average。"""
    import evaluation.report as m

    for name in m._RATIO_METRICS:
        assert not name.startswith("figure_caption_")


def test_ratio_metrics_does_not_contain_silent_drop():
    """silent_drop_count 单独求和不参与 macro average。"""
    import evaluation.report as m

    assert "silent_drop_count" not in m._RATIO_METRICS


def test_ratio_metrics_does_not_contain_element_count_total():
    import evaluation.report as m

    assert "element_count_total" not in m._RATIO_METRICS


# =========================================================================
# 函数签名 introspection
# =========================================================================


def test_build_provenance_param_count_4():
    sig = inspect.signature(build_provenance)
    assert len(sig.parameters) == 4


def test_build_provenance_param_names():
    sig = inspect.signature(build_provenance)
    assert list(sig.parameters.keys()) == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_build_provenance_no_defaults():
    """4 个参数都无默认。"""
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_build_provenance_no_var_args():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_build_provenance_no_var_kwargs():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_build_provenance_param_kinds_positional_or_keyword():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_build_provenance_return_annotation_is_str():
    """future annotations → return_annotation 是 str。"""
    sig = inspect.signature(build_provenance)
    assert isinstance(sig.return_annotation, str)


def test_build_devset_section_param_count_1():
    sig = inspect.signature(build_devset_section)
    assert len(sig.parameters) == 1


def test_build_devset_section_param_name_manifest():
    sig = inspect.signature(build_devset_section)
    assert list(sig.parameters.keys()) == ["manifest"]


def test_build_devset_section_no_default():
    sig = inspect.signature(build_devset_section)
    assert sig.parameters["manifest"].default is inspect.Parameter.empty


def test_build_devset_section_no_var_args():
    sig = inspect.signature(build_devset_section)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_build_devset_section_no_var_kwargs():
    sig = inspect.signature(build_devset_section)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_aggregate_summary_param_count_1():
    sig = inspect.signature(aggregate_summary)
    assert len(sig.parameters) == 1


def test_aggregate_summary_param_name():
    sig = inspect.signature(aggregate_summary)
    assert list(sig.parameters.keys()) == ["per_doc_results"]


def test_aggregate_summary_no_var_args():
    sig = inspect.signature(aggregate_summary)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_aggregate_summary_no_var_kwargs():
    sig = inspect.signature(aggregate_summary)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_get_git_provenance_param_count_1():
    sig = inspect.signature(get_git_provenance)
    assert len(sig.parameters) == 1


def test_get_git_provenance_param_name():
    sig = inspect.signature(get_git_provenance)
    assert list(sig.parameters.keys()) == ["project_root"]


def test_get_dependency_versions_no_params():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


# =========================================================================
# helper function metadata
# =========================================================================


def test_build_provenance_module_identity():
    assert build_provenance.__module__ == "evaluation.report"


def test_build_provenance_qualname():
    assert build_provenance.__qualname__ == "build_provenance"


def test_build_devset_section_module_identity():
    assert build_devset_section.__module__ == "evaluation.report"


def test_build_devset_section_qualname():
    assert build_devset_section.__qualname__ == "build_devset_section"


def test_aggregate_summary_module_identity():
    assert aggregate_summary.__module__ == "evaluation.report"


def test_aggregate_summary_qualname():
    assert aggregate_summary.__qualname__ == "aggregate_summary"


def test_get_git_provenance_module_identity():
    assert get_git_provenance.__module__ == "evaluation.report"


def test_get_git_provenance_qualname():
    assert get_git_provenance.__qualname__ == "get_git_provenance"


def test_get_dependency_versions_module_identity():
    assert get_dependency_versions.__module__ == "evaluation.report"


def test_get_dependency_versions_qualname():
    assert get_dependency_versions.__qualname__ == "get_dependency_versions"


def test_all_functions_are_function_type():
    import types as _types

    for fn in [
        build_provenance,
        build_devset_section,
        aggregate_summary,
        get_git_provenance,
        get_dependency_versions,
    ]:
        assert isinstance(fn, _types.FunctionType)


# =========================================================================
# aggregate_summary 4 top-level keys 顺序精确
# =========================================================================


def test_aggregate_summary_empty_returns_4_keys():
    out = aggregate_summary([])
    assert len(out) == 4


def test_aggregate_summary_keys_order_exact():
    """4 top-level keys 顺序：counts → success_rates → ratio_macro_averages → silent_drop_total。"""
    out = aggregate_summary([])
    assert list(out.keys()) == [
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    ]


def test_aggregate_summary_empty_counts_dict_structure():
    """空 per_doc 时 counts['element_count_total'] 应是 {sum: None, participating_docs: 0}。"""
    out = aggregate_summary([])
    counts = out["counts"]
    assert "element_count_total" in counts
    assert counts["element_count_total"] == {"sum": None, "participating_docs": 0}


def test_aggregate_summary_empty_success_rates_dict_structure():
    out = aggregate_summary([])
    sr = out["success_rates"]
    assert sr["pipeline_success"] == {"success_count": 0, "total": 0, "rate": None}


def test_aggregate_summary_empty_ratio_macro_averages_structure():
    """空 per_doc 时每个 ratio metric 应是 {macro_average: None, participating_docs: 0, not_evaluated: 0}。"""
    import evaluation.report as m

    out = aggregate_summary([])
    rma = out["ratio_macro_averages"]
    assert set(rma.keys()) == set(m._RATIO_METRICS)
    for name, val in rma.items():
        assert val == {"macro_average": None, "participating_docs": 0, "not_evaluated": 0}


def test_aggregate_summary_empty_silent_drop_total_is_none():
    out = aggregate_summary([])
    assert out["silent_drop_total"] is None


# =========================================================================
# aggregate_summary 详细计算
# =========================================================================


def test_aggregate_summary_counts_with_one_doc():
    per_doc = [
        {
            "metrics": {
                "element_count_total": {"value": 5, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
            }
        }
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"] == {"sum": 5, "participating_docs": 1}


def test_aggregate_summary_counts_with_multiple_docs_sums():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"element_count_total": {"value": 3, "reason": None}}},
        {"metrics": {"element_count_total": {"value": 10, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 18
    assert out["counts"]["element_count_total"]["participating_docs"] == 3


def test_aggregate_summary_counts_excludes_none_values():
    """null value 不参与求和。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"element_count_total": {"value": None, "reason": "pipeline_failed"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_success_rate_with_one_true():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 1
    assert sr["rate"] == 1.0


def test_aggregate_summary_success_rate_with_one_false():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False, "reason": "error"}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 1
    assert sr["rate"] == 0.0


def test_aggregate_summary_success_rate_half():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": "error"}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2
    assert sr["rate"] == 0.5


def test_aggregate_summary_success_rate_excludes_none_value():
    """pipeline_success=None（不应发生但防御性测试）。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": None, "reason": "x"}}},
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    # success_count = 1 (only True counted); total = 2 (all per_doc)
    assert sr["success_count"] == 1
    assert sr["total"] == 2


def test_aggregate_summary_ratio_macro_average_simple():
    per_doc = [
        {"metrics": {"schema_valid": {"value": True, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["schema_valid"]
    # True == 1 → macro = 1.0
    assert rma["macro_average"] == 1.0
    assert rma["participating_docs"] == 1
    assert rma["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_average_with_floats():
    per_doc = [
        {"metrics": {"schema_valid": {"value": True, "reason": None}}},  # 1.0
        {"metrics": {"schema_valid": {"value": False, "reason": None}}},  # 0.0
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["schema_valid"]
    # macro = (1.0 + 0.0) / 2 = 0.5
    assert rma["macro_average"] == 0.5
    assert rma["participating_docs"] == 2
    assert rma["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_average_excludes_none():
    per_doc = [
        {"metrics": {"schema_valid": {"value": True, "reason": None}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["schema_valid"]
    # 1 doc participates → macro = 1.0; 1 not_evaluated
    assert rma["macro_average"] == 1.0
    assert rma["participating_docs"] == 1
    assert rma["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_total_sums():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 2, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": 5, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 7


def test_aggregate_summary_silent_drop_total_excludes_none():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 2, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": None, "reason": "no_expectations"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 2


def test_aggregate_summary_silent_drop_total_all_none_is_none():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None, "reason": "no_expectations"}}},
        {"metrics": {"silent_drop_count": {"value": None, "reason": "no_expectations"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_handles_missing_metric():
    """per_doc 完全缺某 metric → 视为 null。"""
    per_doc = [
        {"metrics": {}},  # 缺 element_count_total
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_handles_missing_metrics_key():
    """per_doc 完全缺 'metrics' key → 抛 KeyError（不是 None-safe 路径）。"""
    per_doc = [{}]
    with pytest.raises(KeyError):
        aggregate_summary(per_doc)


def test_aggregate_summary_success_rate_zero_docs_rate_none():
    """per_doc 为空时 rate=None。"""
    out = aggregate_summary([])
    assert out["success_rates"]["pipeline_success"]["rate"] is None


def test_aggregate_summary_returns_dict_type():
    out = aggregate_summary([])
    assert isinstance(out, dict)


def test_aggregate_summary_does_not_share_subdict_state():
    """两次调用返回独立的 dict（不缓存）。"""
    a = aggregate_summary([])
    b = aggregate_summary([])
    a["silent_drop_total"] = 99
    assert b["silent_drop_total"] is None


# =========================================================================
# build_devset_section（用 stub Manifest 对象）
# =========================================================================


class _StubManifest:
    """stub Manifest，模拟 evaluation.manifest.Manifest 的接口。"""

    def __init__(
        self,
        devset_status: str = "incomplete",
        file_count: int = 0,
        content_group_count: int = 0,
        pdf_count: int = 0,
        docx_count: int = 0,
        categories_covered: list[str] | None = None,
    ):
        self.devset_status = devset_status
        self.file_count = file_count
        self.content_group_count = content_group_count
        self.pdf_count = pdf_count
        self.docx_count = docx_count
        self.categories_covered = categories_covered if categories_covered is not None else []


def test_build_devset_section_returns_dict():
    out = build_devset_section(_StubManifest())
    assert isinstance(out, dict)


def test_build_devset_section_keys_count_6():
    out = build_devset_section(_StubManifest())
    assert len(out) == 6


def test_build_devset_section_keys_exact_order():
    out = build_devset_section(_StubManifest())
    assert list(out.keys()) == [
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    ]


def test_build_devset_section_passes_devset_status():
    out = build_devset_section(_StubManifest(devset_status="complete"))
    assert out["status"] == "complete"


def test_build_devset_section_passes_file_count():
    out = build_devset_section(_StubManifest(file_count=42))
    assert out["file_count"] == 42


def test_build_devset_section_passes_content_group_count():
    out = build_devset_section(_StubManifest(content_group_count=5))
    assert out["content_group_count"] == 5


def test_build_devset_section_passes_pdf_count():
    out = build_devset_section(_StubManifest(pdf_count=3))
    assert out["pdf_count"] == 3


def test_build_devset_section_passes_docx_count():
    out = build_devset_section(_StubManifest(docx_count=2))
    assert out["docx_count"] == 2


def test_build_devset_section_passes_categories_covered():
    cats = ["legal", "scientific"]
    out = build_devset_section(_StubManifest(categories_covered=cats))
    assert out["categories_covered"] == ["legal", "scientific"]


def test_build_devset_section_does_not_mutate_input():
    """不修改 manifest 对象的属性。"""
    m = _StubManifest(categories_covered=["x"])
    build_devset_section(m)
    assert m.categories_covered == ["x"]
    assert m.devset_status == "incomplete"


def test_build_devset_section_with_empty_categories():
    out = build_devset_section(_StubManifest(categories_covered=[]))
    assert out["categories_covered"] == []


# =========================================================================
# build_provenance
# =========================================================================


def test_build_provenance_returns_dict_type(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out, dict)


def test_build_provenance_keys_count_9(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert len(out) == 9


def test_build_provenance_keys_order_exact(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert list(out.keys()) == [
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


def test_build_provenance_evaluator_version_value(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_passed(tmp_path: Path):
    out = build_provenance(tmp_path, "my_parser", 800, None)
    assert out["parser_name"] == "my_parser"


def test_build_provenance_parser_version_passed(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, "1.2.3")
    assert out["parser_version"] == "1.2.3"


def test_build_provenance_parser_version_none_passed(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_max_chars_int_converted(tmp_path: Path):
    """max_chars 强制 int()。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_int_from_string(tmp_path: Path):
    """str '800' → int 800。"""
    out = build_provenance(tmp_path, "fallback", "800", None)  # type: ignore[arg-type]
    assert out["max_chars"] == 800


def test_build_provenance_run_timestamp_iso_parseable(tmp_path: Path):
    """run_timestamp_iso 是 ISO 8601 可解析。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    ts = out["run_timestamp_iso"]
    assert isinstance(ts, str)
    # 应可被 datetime.fromisoformat 解析
    parsed = datetime.fromisoformat(ts)
    assert isinstance(parsed, datetime)


def test_build_provenance_dependencies_is_dict(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_dependencies_has_3_packages(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    deps = out["dependencies"]
    assert set(deps.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_build_provenance_git_commit_is_str_or_none(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["git_commit"] is None or isinstance(out["git_commit"], str)


def test_build_provenance_git_dirty_is_bool(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["git_dirty"], bool)


def test_build_provenance_does_not_mutate_input_max_chars(tmp_path: Path):
    """max_chars='800' 输入不被修改（虽然 int() 转换不影响 str）。"""
    s = "800"
    build_provenance(tmp_path, "fallback", s, None)  # type: ignore[arg-type]
    assert s == "800"


# =========================================================================
# get_git_provenance
# =========================================================================


def test_get_git_provenance_returns_dict_with_two_keys(tmp_path: Path):
    out = get_git_provenance(tmp_path)
    assert isinstance(out, dict)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_keys_order(tmp_path: Path):
    out = get_git_provenance(tmp_path)
    assert list(out.keys()) == ["git_commit", "git_dirty"]


def test_get_git_provenance_git_commit_is_str_or_none(tmp_path: Path):
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None or isinstance(out["git_commit"], str)


def test_get_git_provenance_git_dirty_is_bool(tmp_path: Path):
    out = get_git_provenance(tmp_path)
    assert isinstance(out["git_dirty"], bool)


def test_get_git_provenance_handles_nonexistent_dir(tmp_path: Path):
    """不存在的目录也不应抛错（subprocess 会失败但被 catch）。"""
    nonexistent = tmp_path / "nonexistent"
    out = get_git_provenance(nonexistent)
    assert "git_commit" in out
    assert "git_dirty" in out


# =========================================================================
# get_dependency_versions
# =========================================================================


def test_get_dependency_versions_returns_dict():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_get_dependency_versions_has_3_keys():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_are_str_or_none():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str), f"{k} value type {type(v)}"


def test_get_dependency_versions_pdfplumber_resolvable():
    """pdfplumber 是项目依赖，应该有版本。"""
    out = get_dependency_versions()
    assert out["pdfplumber"] is not None


def test_get_dependency_versions_does_not_take_args():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


# =========================================================================
# __all__ 完整性
# =========================================================================


def test_module_all_not_including_helper_constants():
    """__all__ 不含 _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS。"""
    import evaluation.report as m

    assert "_RATIO_METRICS" not in m.__all__
    assert "_COUNT_METRICS" not in m.__all__
    assert "_SUCCESS_BOOL_METRICS" not in m.__all__


def test_module_all_contains_5_helpers():
    import evaluation.report as m

    for name in [
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    ]:
        assert name in m.__all__


# =========================================================================
# 类型 cross-check（构建 → 聚合 roundtrip）
# =========================================================================


def test_aggregate_summary_then_check_keys_match_ratio_metrics():
    """聚合后 ratio_macro_averages keys 与 _RATIO_METRICS 集合一致。"""
    import evaluation.report as m

    per_doc = [
        {"metrics": {"schema_valid": {"value": True, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert set(out["ratio_macro_averages"].keys()) == set(m._RATIO_METRICS)


def test_aggregate_summary_then_check_keys_match_count_metrics():
    import evaluation.report as m

    out = aggregate_summary([])
    assert set(out["counts"].keys()) == set(m._COUNT_METRICS)


def test_aggregate_summary_then_check_keys_match_success_bool_metrics():
    import evaluation.report as m

    out = aggregate_summary([])
    assert set(out["success_rates"].keys()) == set(m._SUCCESS_BOOL_METRICS)


def test_aggregate_summary_total_per_doc_for_not_evaluated():
    """not_evaluated = total - participating。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
        {"metrics": {"schema_valid": {"value": True, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["schema_valid"]
    assert rma["not_evaluated"] == 2
    assert rma["participating_docs"] == 1
