r"""evaluation/report.py 边角测试 - 第十五轮（Round 250）。

补强已有 base/edges/edges2-14（共 ~810+ 测试）未覆盖的深度：
- 源码字符串断言（inspect.getsource）：含特定 token（_RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS / subprocess.run / datetime.now / EVALUATOR_VERSION / REPORT_VERSION）
- module metadata：__file__ 后缀 / __package__ / __name__ 精确
- 函数 metadata：__module__/__qualname__/__name__/FunctionType
- signature 无 VAR_POSITIONAL/VAR_KEYWORD
- __future__ annotations 影响 return_annotation 为 str
- 常量精确：_RATIO_METRICS 12 个元素顺序精确 / _COUNT_METRICS 1 个 / _SUCCESS_BOOL_METRICS 1 个
- 常量交叉关系：3 个常量互不相交 / 总和 14 = 12+1+1
- get_git_provenance subprocess.run kwargs 完整
- aggregate_summary 详细：4 top-level keys 顺序精确 / 各 sub-dict 内部结构精确
- build_provenance 详细：返回 dict 9 keys 精确顺序 / run_timestamp_iso 是 ISO parseable
- build_devset_section 6 keys 精确顺序
- get_dependency_versions 总是含 3 keys（pdfplumber/python-docx/pypdfium2）
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
# 源码字符串断言（inspect.getsource）
# =========================================================================


def test_module_source_contains_ratio_metrics_definition():
    """源码含 '_RATIO_METRICS'。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "_RATIO_METRICS" in src


def test_module_source_contains_count_metrics_definition():
    """源码含 '_COUNT_METRICS'。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "_COUNT_METRICS" in src


def test_module_source_contains_success_bool_metrics_definition():
    """源码含 '_SUCCESS_BOOL_METRICS'。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "_SUCCESS_BOOL_METRICS" in src


def test_module_source_contains_subprocess_run_call():
    """源码含 'subprocess.run('。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "subprocess.run(" in src


def test_module_source_contains_datetime_now_astimezone():
    """源码含 'datetime.now().astimezone()'。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "datetime.now().astimezone()" in src


def test_module_source_contains_importlib_metadata_import():
    """源码含 'import importlib.metadata'。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "import importlib.metadata" in src


def test_module_source_contains_future_annotations():
    """源码含 'from __future__ import annotations'。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_contains_dict_subscript_syntax():
    """源码含 'dict[str,'。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "dict[str," in src


def test_module_source_contains_evaluator_version_reference():
    """源码含 'EVALUATOR_VERSION'。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "EVALUATOR_VERSION" in src


def test_module_source_contains_report_version_reference():
    """源码含 'REPORT_VERSION'。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "REPORT_VERSION" in src


def test_module_source_no_main_guard():
    """源码不含 '__main__'。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "__main__" not in src


def test_module_source_contains_capture_output():
    """源码含 'capture_output=True'。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "capture_output=True" in src


def test_module_source_contains_timeout_value():
    """源码含 'timeout=10'。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "timeout=10" in src


def test_module_source_contains_silent_drop_total_key():
    """源码含 'silent_drop_total'。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "silent_drop_total" in src


def test_module_source_contains_ratio_macro_averages_key():
    """源码含 'ratio_macro_averages'。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "ratio_macro_averages" in src


def test_module_source_contains_success_rates_key():
    """源码含 'success_rates'。"""
    import evaluation.report as m
    src = inspect.getsource(m)
    assert "success_rates" in src


# =========================================================================
# 模块 metadata
# =========================================================================


def test_module_file_endswith_py():
    """__file__ 以 '.py' 结尾。"""
    import evaluation.report as m
    assert m.__file__.endswith(".py")


def test_module_file_contains_report():
    """__file__ 含 'report'。"""
    import evaluation.report as m
    assert "report" in m.__file__


def test_module_package_is_evaluation():
    """__package__ == 'evaluation'。"""
    import evaluation.report as m
    assert m.__package__ == "evaluation"


def test_module_name_is_evaluation_report():
    """__name__ == 'evaluation.report'。"""
    import evaluation.report as m
    assert m.__name__ == "evaluation.report"


def test_module_subprocess_is_subprocess_module():
    """subprocess is subprocess。"""
    import evaluation.report as m
    assert m.subprocess is subprocess


def test_module_datetime_is_datetime_module():
    """datetime is datetime。"""
    import evaluation.report as m
    assert m.datetime is datetime


def test_module_path_is_pathlib_path():
    """Path is pathlib.Path。"""
    import evaluation.report as m
    from pathlib import Path as P
    assert m.Path is P


def test_module_typing_any_is_typing_any():
    """Any is typing.Any。"""
    import evaluation.report as m
    from typing import Any as A
    assert m.Any is A


def test_module_imports_evaluator_version():
    """EVALUATOR_VERSION 来自 evaluation 包。"""
    import evaluation.report as m
    assert m.EVALUATOR_VERSION is EVALUATOR_VERSION


def test_module_imports_report_version():
    """REPORT_VERSION 来自 evaluation 包。"""
    import evaluation.report as m
    assert m.REPORT_VERSION is REPORT_VERSION


# =========================================================================
# __all__ 精确
# =========================================================================


def test_module_all_is_list_not_tuple():
    """__all__ 是 list 不是 tuple。"""
    import evaluation.report as m
    assert isinstance(m.__all__, list)
    assert not isinstance(m.__all__, tuple)


def test_module_all_set_exact():
    """__all__ 集合精确。"""
    import evaluation.report as m
    assert set(m.__all__) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_all_no_private():
    """__all__ 不含 '_' 开头的私有 symbol。"""
    import evaluation.report as m
    for name in m.__all__:
        assert not name.startswith("_")


def test_module_namespace_contains_all_in_all():
    """所有 __all__ 中的名字都在命名空间。"""
    import evaluation.report as m
    for name in m.__all__:
        assert hasattr(m, name)


# =========================================================================
# 常量精确
# =========================================================================


def test_count_metrics_is_tuple():
    """_COUNT_METRICS 是 tuple。"""
    from evaluation.report import _COUNT_METRICS
    assert isinstance(_COUNT_METRICS, tuple)


def test_count_metrics_exact_one_element():
    """_COUNT_METRICS 仅含 'element_count_total'。"""
    from evaluation.report import _COUNT_METRICS
    assert _COUNT_METRICS == ("element_count_total",)


def test_count_metrics_length_one():
    """_COUNT_METRICS 长度 1。"""
    from evaluation.report import _COUNT_METRICS
    assert len(_COUNT_METRICS) == 1


def test_success_bool_metrics_is_tuple():
    """_SUCCESS_BOOL_METRICS 是 tuple。"""
    from evaluation.report import _SUCCESS_BOOL_METRICS
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_success_bool_metrics_exact_one_element():
    """_SUCCESS_BOOL_METRICS 仅含 'pipeline_success'。"""
    from evaluation.report import _SUCCESS_BOOL_METRICS
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_success_bool_metrics_length_one():
    """_SUCCESS_BOOL_METRICS 长度 1。"""
    from evaluation.report import _SUCCESS_BOOL_METRICS
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_ratio_metrics_is_tuple():
    """_RATIO_METRICS 是 tuple。"""
    from evaluation.report import _RATIO_METRICS
    assert isinstance(_RATIO_METRICS, tuple)


def test_ratio_metrics_length_twelve():
    """_RATIO_METRICS 长度 12。"""
    from evaluation.report import _RATIO_METRICS
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_exact_contents_in_order():
    """_RATIO_METRICS 内容精确按定义顺序。"""
    from evaluation.report import _RATIO_METRICS
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


def test_ratio_metrics_no_duplicates():
    """_RATIO_METRICS 无重复。"""
    from evaluation.report import _RATIO_METRICS
    assert len(_RATIO_METRICS) == len(set(_RATIO_METRICS))


def test_ratio_metrics_does_not_contain_figure_caption():
    """_RATIO_METRICS 不含 figure_caption_*。"""
    from evaluation.report import _RATIO_METRICS
    for name in _RATIO_METRICS:
        assert not name.startswith("figure_caption_")


def test_ratio_metrics_does_not_contain_silent_drop():
    """_RATIO_METRICS 不含 silent_drop_count。"""
    from evaluation.report import _RATIO_METRICS
    assert "silent_drop_count" not in _RATIO_METRICS


def test_three_metric_groups_disjoint():
    """3 个常量互不相交。"""
    from evaluation.report import (
        _COUNT_METRICS, _RATIO_METRICS, _SUCCESS_BOOL_METRICS,
    )
    assert set(_COUNT_METRICS).isdisjoint(set(_RATIO_METRICS))
    assert set(_COUNT_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))
    assert set(_RATIO_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))


def test_three_metric_groups_total_count_14():
    """3 个常量合计 14 个名字。"""
    from evaluation.report import (
        _COUNT_METRICS, _RATIO_METRICS, _SUCCESS_BOOL_METRICS,
    )
    total = len(_COUNT_METRICS) + len(_RATIO_METRICS) + len(_SUCCESS_BOOL_METRICS)
    assert total == 14


def test_count_metrics_does_not_overlap_pipeline_success():
    """_COUNT_METRICS 不含 'pipeline_success'。"""
    from evaluation.report import _COUNT_METRICS
    assert "pipeline_success" not in _COUNT_METRICS


# =========================================================================
# 函数 metadata
# =========================================================================


def test_all_functions_module_attribute():
    """所有 5 个公开函数 __module__ == 'evaluation.report'。"""
    for fn in [
        build_provenance, build_devset_section, aggregate_summary,
        get_git_provenance, get_dependency_versions,
    ]:
        assert fn.__module__ == "evaluation.report"


def test_all_functions_qualname_matches_name():
    """所有 5 个函数 __qualname__ == __name__（顶层函数）。"""
    for fn in [
        build_provenance, build_devset_section, aggregate_summary,
        get_git_provenance, get_dependency_versions,
    ]:
        assert fn.__qualname__ == fn.__name__


def test_all_functions_name_exact():
    """__name__ 精确。"""
    assert build_provenance.__name__ == "build_provenance"
    assert build_devset_section.__name__ == "build_devset_section"
    assert aggregate_summary.__name__ == "aggregate_summary"
    assert get_git_provenance.__name__ == "get_git_provenance"
    assert get_dependency_versions.__name__ == "get_dependency_versions"


def test_all_functions_are_python_functions():
    """都是 Python 函数。"""
    import types
    for fn in [
        build_provenance, build_devset_section, aggregate_summary,
        get_git_provenance, get_dependency_versions,
    ]:
        assert isinstance(fn, types.FunctionType)


def test_all_functions_no_varargs():
    """所有 5 个函数无 VAR_POSITIONAL。"""
    for fn in [
        build_provenance, build_devset_section, aggregate_summary,
        get_git_provenance, get_dependency_versions,
    ]:
        sig = inspect.signature(fn)
        assert all(p.kind != inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values()), \
            f"{fn.__name__} 不应有 VAR_POSITIONAL"


def test_all_functions_no_varkw():
    """所有 5 个函数无 VAR_KEYWORD。"""
    for fn in [
        build_provenance, build_devset_section, aggregate_summary,
        get_git_provenance, get_dependency_versions,
    ]:
        sig = inspect.signature(fn)
        assert all(p.kind != inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()), \
            f"{fn.__name__} 不应有 VAR_KEYWORD"


def test_build_provenance_return_annotation_is_str():
    """build_provenance return annotation 是 str。"""
    sig = inspect.signature(build_provenance)
    assert isinstance(sig.return_annotation, str)


def test_aggregate_summary_return_annotation_is_str():
    """aggregate_summary return annotation 是 str。"""
    sig = inspect.signature(aggregate_summary)
    assert isinstance(sig.return_annotation, str)


def test_build_devset_section_return_annotation_is_str():
    """build_devset_section return annotation 是 str。"""
    sig = inspect.signature(build_devset_section)
    assert isinstance(sig.return_annotation, str)


def test_get_git_provenance_return_annotation_is_str():
    """get_git_provenance return annotation 是 str。"""
    sig = inspect.signature(get_git_provenance)
    assert isinstance(sig.return_annotation, str)


def test_get_dependency_versions_return_annotation_is_str():
    """get_dependency_versions return annotation 是 str。"""
    sig = inspect.signature(get_dependency_versions)
    assert isinstance(sig.return_annotation, str)


# =========================================================================
# build_provenance 输出 keys 顺序精确
# =========================================================================


def test_build_provenance_returns_nine_keys_exact_order(tmp_path: Path):
    """build_provenance 返回 9 keys 顺序精确。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    expected_keys = [
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
    assert list(out.keys()) == expected_keys


def test_build_provenance_returns_dict_type(tmp_path: Path):
    """build_provenance 返回 dict。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert isinstance(out, dict)


def test_build_provenance_max_chars_is_int(tmp_path: Path):
    """max_chars 是 int 类型。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert isinstance(out["max_chars"], int)


def test_build_provenance_parser_name_propagated(tmp_path: Path):
    """parser_name 透传。"""
    out = build_provenance(tmp_path, "my_parser", 800, "1.0.0")
    assert out["parser_name"] == "my_parser"


def test_build_provenance_parser_version_none_accepted(tmp_path: Path):
    """parser_version=None 接受。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_evaluator_version_value(tmp_path: Path):
    """evaluator_version 是 EVALUATOR_VERSION 常量值。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value(tmp_path: Path):
    """report_version 是 REPORT_VERSION 常量值。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_dependencies_three_keys(tmp_path: Path):
    """dependencies 含 3 个 keys。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert set(out["dependencies"].keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_build_provenance_run_timestamp_iso_is_str(tmp_path: Path):
    """run_timestamp_iso 是 str。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert isinstance(out["run_timestamp_iso"], str)


# =========================================================================
# build_devset_section 输出 keys 顺序精确
# =========================================================================


def test_build_devset_section_returns_six_keys_exact_order():
    """返回 6 keys 顺序精确。"""
    class M:
        devset_status = "incomplete"
        file_count = 1
        content_group_count = 1
        pdf_count = 1
        docx_count = 0
        categories_covered = ("math",)
    out = build_devset_section(M())
    expected_keys = [
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    ]
    assert list(out.keys()) == expected_keys


def test_build_devset_section_returns_dict_type():
    """返回 dict。"""
    class M:
        devset_status = "incomplete"
        file_count = 1
        content_group_count = 1
        pdf_count = 1
        docx_count = 0
        categories_covered = []
    out = build_devset_section(M())
    assert isinstance(out, dict)


def test_build_devset_section_categories_covered_propagated():
    """categories_covered 透传 manifest 属性。"""
    class M:
        devset_status = "complete"
        file_count = 5
        content_group_count = 2
        pdf_count = 3
        docx_count = 2
        categories_covered = ("math", "science", "history")
    out = build_devset_section(M())
    assert out["categories_covered"] == ("math", "science", "history")


# =========================================================================
# aggregate_summary 输出 4 keys 顺序精确
# =========================================================================


def test_aggregate_summary_returns_four_top_level_keys_in_order():
    """返回 4 keys 顺序：counts, success_rates, ratio_macro_averages, silent_drop_total。"""
    out = aggregate_summary([])
    expected = ["counts", "success_rates", "ratio_macro_averages", "silent_drop_total"]
    assert list(out.keys()) == expected


def test_aggregate_summary_counts_always_one_key():
    """counts dict 始终含 1 个 key（element_count_total）。"""
    out = aggregate_summary([])
    assert set(out["counts"].keys()) == {"element_count_total"}


def test_aggregate_summary_success_rates_always_one_key():
    """success_rates dict 始终含 1 个 key（pipeline_success）。"""
    out = aggregate_summary([])
    assert set(out["success_rates"].keys()) == {"pipeline_success"}


def test_aggregate_summary_ratio_macro_averages_twelve_keys():
    """ratio_macro_averages dict 始终含 12 个 keys。"""
    out = aggregate_summary([])
    assert len(out["ratio_macro_averages"]) == 12
    assert set(out["ratio_macro_averages"].keys()) == {
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


def test_aggregate_summary_returns_dict_type():
    """返回 dict。"""
    out = aggregate_summary([])
    assert isinstance(out, dict)


def test_aggregate_summary_empty_input_silent_drop_total_none():
    """空 per_doc → silent_drop_total=None。"""
    out = aggregate_summary([])
    assert out["silent_drop_total"] is None


def test_aggregate_summary_empty_input_counts_sum_none():
    """空 → counts.element_count_total.sum=None。"""
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"]["sum"] is None


def test_aggregate_summary_empty_input_counts_participating_zero():
    """空 → counts.element_count_total.participating_docs=0。"""
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_empty_input_success_rate_none():
    """空 → success_rates.pipeline_success.rate=None。"""
    out = aggregate_summary([])
    assert out["success_rates"]["pipeline_success"]["rate"] is None


def test_aggregate_summary_empty_input_success_count_zero():
    """空 → success_count=0。"""
    out = aggregate_summary([])
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0


def test_aggregate_summary_empty_input_success_total_zero():
    """空 → total=0。"""
    out = aggregate_summary([])
    assert out["success_rates"]["pipeline_success"]["total"] == 0


def test_aggregate_summary_ratio_macro_average_none_for_each():
    """空 → ratio_macro_averages 每个 metric macro_average=None。"""
    out = aggregate_summary([])
    for name, val in out["ratio_macro_averages"].items():
        assert val["macro_average"] is None, f"{name} 应是 None"
        assert val["participating_docs"] == 0
        assert val["not_evaluated"] == 0


# =========================================================================
# aggregate_summary counts 详细
# =========================================================================


def test_aggregate_summary_counts_sum_integer():
    """counts sum 是 int。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"element_count_total": {"value": 3, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 8
    assert isinstance(out["counts"]["element_count_total"]["sum"], int)


def test_aggregate_summary_counts_skips_none_value():
    """None value 不参与 counts。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"element_count_total": {"value": None, "reason": "pipeline_failed"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


# =========================================================================
# aggregate_summary success_rates 详细
# =========================================================================


def test_aggregate_summary_success_rate_calculation():
    """success_rate = successes/total。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 2
    assert out["success_rates"]["pipeline_success"]["total"] == 3
    assert abs(out["success_rates"]["pipeline_success"]["rate"] - 2 / 3) < 1e-9


def test_aggregate_summary_success_count_only_true():
    """只 value=True 计入 success_count；False/None 都不算。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": None, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["total"] == 3


# =========================================================================
# aggregate_summary ratio_macro_averages 详细
# =========================================================================


def test_aggregate_summary_ratio_macro_average_calculation():
    """macro_average = mean of values。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
        {"metrics": {"schema_valid": {"value": 0.0, "reason": None}}},
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert abs(out["ratio_macro_averages"]["schema_valid"]["macro_average"] - 2 / 3) < 1e-9
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 3
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 0


def test_aggregate_summary_ratio_not_evaluated_calculation():
    """not_evaluated = total - participating。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "pipeline_failed"}}},
        {"metrics": {"metrics_other": {}}},  # 完全无 schema_valid
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 2


# =========================================================================
# aggregate_summary silent_drop_total 详细
# =========================================================================


def test_aggregate_summary_silent_drop_total_calculation():
    """silent_drop_total = sum of values。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": 2, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 5


def test_aggregate_summary_silent_drop_skips_none():
    """None value 不参与 silent_drop_total。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": None, "reason": "no_expectations"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 3


def test_aggregate_summary_silent_drop_all_none_returns_none():
    """所有 silent_drop_count 都 None → silent_drop_total=None。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None, "reason": "no_expectations"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_missing_key_returns_none():
    """per_doc 无 silent_drop_count key → silent_drop_total=None。"""
    per_doc = [
        {"metrics": {}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


# =========================================================================
# get_dependency_versions 详细
# =========================================================================


def test_get_dependency_versions_keys_exact_three():
    """keys 集合精确 3 个。"""
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_returns_dict_type():
    """返回 dict。"""
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_get_dependency_versions_value_types():
    """value 是 str 或 None。"""
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str), f"{k} 应是 str 或 None"


def test_get_dependency_versions_no_extra_keys():
    """不含其他 key（如 'docx'）。"""
    out = get_dependency_versions()
    assert "docx" not in out
    assert "kreuzberg" not in out


# =========================================================================
# get_git_provenance 详细
# =========================================================================


def test_get_git_provenance_returns_dict_with_two_keys(tmp_path: Path):
    """返回 dict 含 2 个 keys。"""
    out = get_git_provenance(tmp_path)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_returns_dict_type(tmp_path: Path):
    """返回 dict。"""
    out = get_git_provenance(tmp_path)
    assert isinstance(out, dict)


def test_get_git_provenance_git_dirty_is_bool(tmp_path: Path):
    """git_dirty 是 bool。"""
    out = get_git_provenance(tmp_path)
    assert isinstance(out["git_dirty"], bool)


def test_get_git_provenance_git_commit_is_str_or_none(tmp_path: Path):
    """git_commit 是 str 或 None。"""
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None or isinstance(out["git_commit"], str)


# =========================================================================
# 模块 __all__ 不含私有常量
# =========================================================================


def test_module_all_does_not_contain_ratio_metrics_constant():
    """__all__ 不含 _RATIO_METRICS。"""
    import evaluation.report as m
    assert "_RATIO_METRICS" not in m.__all__


def test_module_all_does_not_contain_count_metrics_constant():
    """__all__ 不含 _COUNT_METRICS。"""
    import evaluation.report as m
    assert "_COUNT_METRICS" not in m.__all__


def test_module_all_does_not_contain_success_bool_metrics_constant():
    """__all__ 不含 _SUCCESS_BOOL_METRICS。"""
    import evaluation.report as m
    assert "_SUCCESS_BOOL_METRICS" not in m.__all__


# =========================================================================
# aggregate_summary 输入是 tuple / 非 list
# =========================================================================


def test_aggregate_summary_accepts_tuple():
    """per_doc 是 tuple → 仍能工作。"""
    per_doc = (
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    )
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1


def test_aggregate_summary_empty_tuple():
    """per_doc=() → 与 [] 一致。"""
    out = aggregate_summary(())
    assert out["success_rates"]["pipeline_success"]["total"] == 0


def test_aggregate_summary_does_not_mutate_input():
    """不修改 per_doc 输入。"""
    import copy
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    ]
    before = copy.deepcopy(per_doc)
    aggregate_summary(per_doc)
    assert per_doc == before
