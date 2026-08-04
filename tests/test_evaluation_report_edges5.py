r"""evaluation/report.py 边角测试 - 第六轮（Round 153）。

补强已有 base/edges/edges2/edges3/edges4（共 475 测试）未覆盖的深度：
- 常量精确性（_RATIO_METRICS 12 项、_COUNT_METRICS、_SUCCESS_BOOL_METRICS）
- aggregate_summary 深度（混合 None/value、0 值、空 metrics 字典）
- build_provenance 深度（max_chars 边界、parser_version 边界）
- get_dependency_versions 返回结构精确
- build_devset_section 6 key 精确
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
import json
from datetime import datetime
from pathlib import Path

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
# 常量精确性
# =========================================================================


def test_ratio_metrics_count_is_twelve():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_contains_schema_valid():
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_contains_text_preservation_equal():
    assert "text_preservation_equal" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_f1():
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_contains_heading_boundary_compliance():
    assert "heading_boundary_compliance" in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_figure_caption():
    """figure_caption_* 始终 null，不参与 macro average。"""
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_ratio_metrics_no_duplicates():
    assert len(_RATIO_METRICS) == len(set(_RATIO_METRICS))


def test_ratio_metrics_all_strings():
    for name in _RATIO_METRICS:
        assert isinstance(name, str)


def test_count_metrics_count_is_one():
    assert len(_COUNT_METRICS) == 1


def test_count_metrics_contains_element_count_total():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_count_is_one():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_success_bool_metrics_contains_pipeline_success():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_metrics_constants_are_tuples():
    assert isinstance(_RATIO_METRICS, tuple)
    assert isinstance(_COUNT_METRICS, tuple)
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


# =========================================================================
# aggregate_summary 深度
# =========================================================================


def test_aggregate_summary_empty_list_returns_none_sum():
    """空 list → counts.element_count_total.sum=None, participating_docs=0。"""
    s = aggregate_summary([])
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_empty_list_success_rate_is_none():
    """空 list → success_rates.pipeline_success.rate=None（avoid div by 0）。"""
    s = aggregate_summary([])
    assert s["success_rates"]["pipeline_success"]["rate"] is None
    assert s["success_rates"]["pipeline_success"]["success_count"] == 0
    assert s["success_rates"]["pipeline_success"]["total"] == 0


def test_aggregate_summary_empty_list_silent_drop_total_is_none():
    s = aggregate_summary([])
    assert s["silent_drop_total"] is None


def test_aggregate_summary_empty_list_ratio_macro_average_is_none():
    s = aggregate_summary([])
    for name in _RATIO_METRICS:
        assert s["ratio_macro_averages"][name]["macro_average"] is None
        assert s["ratio_macro_averages"][name]["participating_docs"] == 0
        assert s["ratio_macro_averages"][name]["not_evaluated"] == 0


def test_aggregate_summary_counts_with_zero_value_participates():
    """value=0 (not None) 应参与。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 0}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 0
    assert s["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_counts_skips_none_value():
    per_doc = [
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_counts_skips_missing_key():
    per_doc = [
        {"metrics": {}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_counts_sum_correct():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": 20}}},
        {"metrics": {"element_count_total": {"value": 30}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 60
    assert s["counts"]["element_count_total"]["participating_docs"] == 3


def test_aggregate_summary_success_rate_full_success():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 2
    assert sr["rate"] == 1.0


def test_aggregate_summary_success_rate_full_failure():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 2
    assert sr["rate"] == 0.0


def test_aggregate_summary_success_rate_mixed():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 3
    assert sr["rate"] == pytest.approx(2 / 3)


def test_aggregate_summary_success_rate_ignores_none_value():
    """None value 不算 success 也不算 failure（但仍计入 total）。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": None}}},
    ]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2


def test_aggregate_summary_success_rate_missing_key_counts_as_total():
    """missing key 仍计入 total（len(per_doc_results)）。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {}},
    ]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2


def test_aggregate_summary_ratio_macro_single_value():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
    ]
    s = aggregate_summary(per_doc)
    rma = s["ratio_macro_averages"]["schema_valid"]
    assert rma["macro_average"] == 1.0
    assert rma["participating_docs"] == 1
    assert rma["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_mixed_values():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.0}}},
    ]
    s = aggregate_summary(per_doc)
    rma = s["ratio_macro_averages"]["schema_valid"]
    assert rma["macro_average"] == 0.5
    assert rma["participating_docs"] == 2
    assert rma["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_with_none_skipped():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": 0.0}}},
    ]
    s = aggregate_summary(per_doc)
    rma = s["ratio_macro_averages"]["schema_valid"]
    assert rma["macro_average"] == 0.5
    assert rma["participating_docs"] == 2
    assert rma["not_evaluated"] == 1


def test_aggregate_summary_ratio_macro_zero_value_participates():
    """value=0 (not None) 参与。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.0}}},
    ]
    s = aggregate_summary(per_doc)
    rma = s["ratio_macro_averages"]["schema_valid"]
    assert rma["macro_average"] == 0.0
    assert rma["participating_docs"] == 1


def test_aggregate_summary_silent_drop_count_sums_values():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_count_skips_none():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_count_all_none_returns_none():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_count_zero_participates():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 0}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 0


def test_aggregate_summary_has_four_top_keys():
    s = aggregate_summary([])
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_does_not_mix_types():
    """summary 不混 'composite score'。"""
    s = aggregate_summary([
        {"metrics": {"pipeline_success": {"value": True}}}
    ])
    assert "composite_score" not in s
    assert "overall_score" not in s
    assert "summary_score" not in s


def test_aggregate_summary_ratio_macro_has_all_twelve_keys():
    s = aggregate_summary([])
    assert set(s["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


# =========================================================================
# build_provenance 深度
# =========================================================================


def test_build_provenance_max_chars_float_converted_to_int():
    p = build_provenance(Path("."), "fallback", 800.5, "1.0")
    assert p["max_chars"] == 800  # int(800.5) == 800
    assert isinstance(p["max_chars"], int)


def test_build_provenance_max_chars_negative_value():
    p = build_provenance(Path("."), "fallback", -100, "1.0")
    assert p["max_chars"] == -100


def test_build_provenance_max_chars_zero():
    p = build_provenance(Path("."), "fallback", 0, "1.0")
    assert p["max_chars"] == 0


def test_build_provenance_max_chars_string_numeric():
    """int("800") → 800（int 接受数字字符串）。"""
    p = build_provenance(Path("."), "fallback", "800", "1.0")
    assert p["max_chars"] == 800


def test_build_provenance_parser_name_empty_string():
    p = build_provenance(Path("."), "", 800, "1.0")
    assert p["parser_name"] == ""


def test_build_provenance_parser_name_with_special_chars():
    p = build_provenance(Path("."), "fallback/v2", 800, "1.0")
    assert p["parser_name"] == "fallback/v2"


def test_build_provenance_parser_version_empty_string():
    p = build_provenance(Path("."), "fallback", 800, "")
    assert p["parser_version"] == ""


def test_build_provenance_dependencies_keys():
    p = build_provenance(Path("."), "fallback", 800, "1.0")
    deps = p["dependencies"]
    assert "pdfplumber" in deps
    assert "python-docx" in deps
    assert "pypdfium2" in deps


def test_build_provenance_run_timestamp_iso_parseable():
    p = build_provenance(Path("."), "fallback", 800, "1.0")
    ts = p["run_timestamp_iso"]
    # datetime.fromisoformat handles ISO format
    parsed = datetime.fromisoformat(ts)
    assert parsed is not None


def test_build_provenance_run_timestamp_iso_has_timezone_offset():
    """astimezone() 应带 tzinfo。"""
    p = build_provenance(Path("."), "fallback", 800, "1.0")
    ts = p["run_timestamp_iso"]
    # 应含 +/- 时区偏移（不是 Z，因为 astimezone 用本地时区）
    assert ("+" in ts) or ("-" in ts[10:])  # 跳过 date 部分


def test_build_provenance_evaluator_version_value():
    p = build_provenance(Path("."), "fallback", 800, "1.0")
    assert p["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value():
    p = build_provenance(Path("."), "fallback", 800, "1.0")
    assert p["report_version"] == REPORT_VERSION


def test_build_provenance_returns_nine_keys_exact_count():
    p = build_provenance(Path("."), "fallback", 800, "1.0")
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
    assert set(p.keys()) == expected_keys


def test_build_provenance_returns_new_dict_each_call():
    a = build_provenance(Path("."), "fallback", 800, "1.0")
    b = build_provenance(Path("."), "fallback", 800, "1.0")
    assert a is not b
    # timestamps 可能不同（每次调用 datetime.now）


def test_build_provenance_json_serializable():
    p = build_provenance(Path("."), "fallback", 800, "1.0")
    s = json.dumps(p)
    assert isinstance(s, str)


# =========================================================================
# get_dependency_versions 深度
# =========================================================================


def test_get_dependency_versions_returns_three_keys_exact():
    v = get_dependency_versions()
    assert set(v.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_pdfplumber_in_dev_env():
    """开发环境装了 pdfplumber，version 应非 None。"""
    v = get_dependency_versions()
    assert v["pdfplumber"] is not None


def test_get_dependency_versions_values_types():
    v = get_dependency_versions()
    for k, val in v.items():
        assert val is None or isinstance(val, str)


def test_get_dependency_versions_no_extra_keys():
    v = get_dependency_versions()
    assert len(v) == 3  # 严格 3 keys


def test_get_dependency_versions_returns_new_dict_each_call():
    a = get_dependency_versions()
    b = get_dependency_versions()
    assert a is not b


# =========================================================================
# get_git_provenance 深度
# =========================================================================


def test_get_git_provenance_in_worktree_returns_40char_commit(tmp_path: Path):
    """tmp_path 不是 git repo → commit=None。但本 worktree 是 repo。
    用本 worktree 测试 commit 格式（40 hex chars）。"""
    p = get_git_provenance(Path("."))
    if p["git_commit"] is not None:
        assert len(p["git_commit"]) == 40
        assert all(c in "0123456789abcdef" for c in p["git_commit"])


def test_get_git_provenance_non_git_dir_returns_none_commit(tmp_path: Path):
    """非 git 目录：git rev-parse HEAD 失败 → commit=None；
    git status --porcelain 也非零 → dirty=bool(False and ...) = False。"""
    p = get_git_provenance(tmp_path)
    assert p["git_commit"] is None
    # dirty 由 bool(r2.returncode == 0 and ...) 计算，r2.returncode != 0 → False
    assert p["git_dirty"] is False


def test_get_git_provenance_returns_two_keys_exact():
    p = get_git_provenance(Path("."))
    assert set(p.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_git_dirty_is_bool_in_repo():
    p = get_git_provenance(Path("."))
    assert isinstance(p["git_dirty"], bool)


def test_get_git_provenance_in_real_repo_returns_str_commit():
    p = get_git_provenance(Path("."))
    # 在 worktree 中，commit 应是 str
    if p["git_commit"] is not None:
        assert isinstance(p["git_commit"], str)


# =========================================================================
# build_devset_section 深度
# =========================================================================


class _FakeManifest:
    def __init__(self):
        self.devset_status = "test"
        self.file_count = 5
        self.content_group_count = 3
        self.pdf_count = 2
        self.docx_count = 1
        self.categories_covered = ["cat_a", "cat_b"]


def test_build_devset_section_returns_six_keys_exact():
    m = _FakeManifest()
    d = build_devset_section(m)
    expected = {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }
    assert set(d.keys()) == expected


def test_build_devset_section_status_value():
    m = _FakeManifest()
    m.devset_status = "incomplete"
    d = build_devset_section(m)
    assert d["status"] == "incomplete"


def test_build_devset_section_file_count_value():
    m = _FakeManifest()
    m.file_count = 42
    d = build_devset_section(m)
    assert d["file_count"] == 42


def test_build_devset_section_content_group_count_value():
    m = _FakeManifest()
    m.content_group_count = 7
    d = build_devset_section(m)
    assert d["content_group_count"] == 7


def test_build_devset_section_pdf_count_value():
    m = _FakeManifest()
    m.pdf_count = 11
    d = build_devset_section(m)
    assert d["pdf_count"] == 11


def test_build_devset_section_docx_count_value():
    m = _FakeManifest()
    m.docx_count = 9
    d = build_devset_section(m)
    assert d["docx_count"] == 9


def test_build_devset_section_categories_covered_value():
    m = _FakeManifest()
    m.categories_covered = ["x", "y", "z"]
    d = build_devset_section(m)
    assert d["categories_covered"] == ["x", "y", "z"]


def test_build_devset_section_categories_covered_is_list_reference():
    """categories_covered 是直接赋值（共享引用）。"""
    m = _FakeManifest()
    m.categories_covered = ["x"]
    d = build_devset_section(m)
    assert d["categories_covered"] is m.categories_covered


def test_build_devset_section_returns_new_dict_each_call():
    m = _FakeManifest()
    a = build_devset_section(m)
    b = build_devset_section(m)
    assert a is not b
    assert a == b


def test_build_devset_section_json_serializable():
    m = _FakeManifest()
    d = build_devset_section(m)
    s = json.dumps(d)
    assert isinstance(s, str)


# =========================================================================
# 模块结构 / __all__
# =========================================================================


def test_module_all_exact_list():
    import evaluation.report as mod
    assert mod.__all__ == [
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    ]


def test_module_all_no_duplicates():
    import evaluation.report as mod
    assert len(mod.__all__) == len(set(mod.__all__))


def test_module_imports_subprocess():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "import subprocess" in src


def test_module_imports_datetime():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "from datetime import datetime" in src


def test_module_imports_path():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_evaluator_version():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "EVALUATOR_VERSION" in src
    assert "REPORT_VERSION" in src


def test_module_uses_future_annotations():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import evaluation.report as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_aggregate():
    import evaluation.report as mod
    doc = mod.__doc__
    assert "聚合" in doc or "aggregate" in doc.lower()


def test_module_docstring_mentions_no_mix():
    """docstring 提及"不混合类型"。"""
    import evaluation.report as mod
    doc = mod.__doc__
    assert "不混合" in doc or "不混" in doc


def test_module_no_silence_unused():
    import evaluation.report as mod
    assert not hasattr(mod, "_silence_unused")


def test_module_constants_present():
    import evaluation.report as mod
    assert hasattr(mod, "_RATIO_METRICS")
    assert hasattr(mod, "_COUNT_METRICS")
    assert hasattr(mod, "_SUCCESS_BOOL_METRICS")


# =========================================================================
# 签名深度
# =========================================================================


def test_get_git_provenance_param_name():
    sig = inspect.signature(get_git_provenance)
    assert "project_root" in sig.parameters


def test_get_git_provenance_param_no_default():
    sig = inspect.signature(get_git_provenance)
    assert sig.parameters["project_root"].default is inspect.Parameter.empty


def test_get_dependency_versions_no_params():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_build_provenance_param_names_exact():
    sig = inspect.signature(build_provenance)
    assert set(sig.parameters) == {"project_root", "parser_name", "max_chars", "parser_version"}


def test_build_provenance_no_defaults():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_build_provenance_return_annotation_dict():
    sig = inspect.signature(build_provenance)
    assert "dict" in str(sig.return_annotation).lower()


def test_build_devset_section_param_name():
    sig = inspect.signature(build_devset_section)
    assert "manifest" in sig.parameters


def test_build_devset_section_param_no_default():
    sig = inspect.signature(build_devset_section)
    assert sig.parameters["manifest"].default is inspect.Parameter.empty


def test_aggregate_summary_param_name():
    sig = inspect.signature(aggregate_summary)
    assert "per_doc_results" in sig.parameters


def test_aggregate_summary_param_no_default():
    sig = inspect.signature(aggregate_summary)
    assert sig.parameters["per_doc_results"].default is inspect.Parameter.empty


def test_aggregate_summary_return_annotation_dict():
    sig = inspect.signature(aggregate_summary)
    assert "dict" in str(sig.return_annotation).lower()


# =========================================================================
# 综合行为
# =========================================================================


def test_aggregate_summary_idempotent():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    a = aggregate_summary(per_doc)
    b = aggregate_summary(per_doc)
    # counts/success_rates/ratio_macro_averages 内容相同（但 dict 不同对象）
    assert a == b


def test_aggregate_summary_does_not_mutate_input():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    per_doc_before = json.loads(json.dumps(per_doc))
    aggregate_summary(per_doc)
    assert per_doc == per_doc_before


def test_aggregate_summary_then_build_provenance_independent():
    """aggregate_summary 不依赖 build_provenance 状态。"""
    s = aggregate_summary([])
    p = build_provenance(Path("."), "fallback", 800, "1.0")
    assert "counts" in s
    assert "max_chars" in p


def test_build_devset_section_then_aggregate_summary_compose():
    """可独立组合：build_devset_section 输出与 aggregate_summary 输出独立。"""
    m = _FakeManifest()
    devset = build_devset_section(m)
    summary = aggregate_summary([])
    assert "status" in devset
    assert "counts" in summary
    # 两者 keys 不重叠
    assert not (set(devset.keys()) & set(summary.keys()))


def test_get_dependency_versions_then_build_provenance_compose():
    """build_provenance 内部调用 get_dependency_versions。"""
    p = build_provenance(Path("."), "fallback", 800, "1.0")
    direct = get_dependency_versions()
    assert p["dependencies"] == direct
