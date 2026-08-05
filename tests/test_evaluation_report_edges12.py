r"""evaluation/report.py 边角测试 - 第十二轮（Round 230）。

补强已有 base/edges/edges2-11（共 ~1138 测试）未覆盖的深度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 精确元组等值（不只是 membership）
- 三组 metric 名互斥
- get_git_provenance / get_dependency_versions / build_provenance / build_devset_section / aggregate_summary dict 插入顺序
- aggregate_summary ratio value=True / 1 / 1.0 算术行为
- aggregate_summary count value=True / False 算术行为
- build_provenance empty parser_name / parser_version preserved
- build_provenance max_chars=0 / negative preserved
- module-level 常量 / imports / __all__ 结构
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
# _RATIO_METRICS 精确元组等值（ordered）
# =========================================================================


def test_ratio_metrics_exact_ordered_tuple():
    """元组按精确顺序包含 12 项。"""
    expected = (
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
    assert _RATIO_METRICS == expected


def test_count_metrics_exact_ordered_tuple():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_exact_ordered_tuple():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_three_metric_groups_disjoint_pairwise():
    """三组互不相交。"""
    s_ratio = set(_RATIO_METRICS)
    s_count = set(_COUNT_METRICS)
    s_bool = set(_SUCCESS_BOOL_METRICS)
    assert s_ratio & s_count == set()
    assert s_ratio & s_bool == set()
    assert s_count & s_bool == set()


def test_ratio_metrics_first_item_schema_valid():
    """顺序：schema_valid 排第一。"""
    assert _RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_last_item_chunk_boundary_f1():
    """顺序：chunk_boundary_f1 排最后。"""
    assert _RATIO_METRICS[-1] == "chunk_boundary_f1"


def test_ratio_metrics_chunk_boundary_group_consecutive():
    """顺序：chunk_boundary_precision/recall/f1 三项连续。"""
    names = list(_RATIO_METRICS)
    cb_start = names.index("chunk_boundary_precision")
    assert names[cb_start + 1] == "chunk_boundary_recall"
    assert names[cb_start + 2] == "chunk_boundary_f1"


def test_ratio_metrics_text_char_multiset_group_consecutive():
    """顺序：text_char_multiset_precision/recall 连续。"""
    names = list(_RATIO_METRICS)
    tcm_start = names.index("text_char_multiset_precision")
    assert names[tcm_start + 1] == "text_char_multiset_recall"


# =========================================================================
# get_git_provenance dict 插入顺序
# =========================================================================


def test_get_git_provenance_dict_insertion_order(tmp_path: Path, monkeypatch):
    """返回 dict 应按 git_commit → git_dirty 顺序插入。"""
    captured = {}

    class _R:
        def __init__(self, rc, out):
            self.returncode = rc
            self.stdout = out

    def fake_run(cmd, **kwargs):
        if "rev-parse" in cmd:
            captured["rev_parse"] = cmd
            return _R(0, "abc123\n")
        if "status" in cmd:
            captured["status"] = cmd
            return _R(0, "")
        return _R(1, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = get_git_provenance(tmp_path)
    keys = list(result.keys())
    assert keys[0] == "git_commit"
    assert keys[1] == "git_dirty"


def test_get_git_provenance_returns_exactly_two_keys(tmp_path: Path):
    result = get_git_provenance(tmp_path)
    assert set(result.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_dict_has_no_extra_keys(tmp_path: Path):
    result = get_git_provenance(tmp_path)
    assert len(result) == 2


# =========================================================================
# get_dependency_versions dict 插入顺序
# =========================================================================


def test_get_dependency_versions_dict_insertion_order():
    """返回 dict 应按 pdfplumber → python-docx → pypdfium2 顺序插入。"""
    result = get_dependency_versions()
    keys = list(result.keys())
    assert keys[0] == "pdfplumber"
    assert keys[1] == "python-docx"
    assert keys[2] == "pypdfium2"


def test_get_dependency_versions_returns_exactly_three_keys():
    result = get_dependency_versions()
    assert set(result.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_dict_size():
    result = get_dependency_versions()
    assert len(result) == 3


# =========================================================================
# build_provenance dict 插入顺序 / 空字符串保留
# =========================================================================


def test_build_provenance_dict_insertion_order(tmp_path: Path):
    """返回 dict 应按 9 个 key 顺序插入。"""
    result = build_provenance(tmp_path, parser_name="fallback", max_chars=800, parser_version="1.0")
    keys = list(result.keys())
    assert keys[0] == "git_commit"
    assert keys[1] == "git_dirty"
    assert keys[2] == "evaluator_version"
    assert keys[3] == "report_version"
    assert keys[4] == "parser_name"
    assert keys[5] == "parser_version"
    assert keys[6] == "dependencies"
    assert keys[7] == "max_chars"
    assert keys[8] == "run_timestamp_iso"


def test_build_provenance_empty_parser_name_preserved(tmp_path: Path):
    """parser_name='' 应原样保留（不替换为 None）。"""
    result = build_provenance(tmp_path, parser_name="", max_chars=800, parser_version="1.0")
    assert result["parser_name"] == ""


def test_build_provenance_empty_parser_version_preserved(tmp_path: Path):
    """parser_version='' 应原样保留。"""
    result = build_provenance(tmp_path, parser_name="fallback", max_chars=800, parser_version="")
    assert result["parser_version"] == ""


def test_build_provenance_none_parser_version_preserved(tmp_path: Path):
    """parser_version=None 应原样保留。"""
    result = build_provenance(tmp_path, parser_name="fallback", max_chars=800, parser_version=None)
    assert result["parser_version"] is None


def test_build_provenance_max_chars_zero_preserved(tmp_path: Path):
    """max_chars=0 应原样保留（int(0)=0）。"""
    result = build_provenance(tmp_path, parser_name="fallback", max_chars=0, parser_version="1.0")
    assert result["max_chars"] == 0


def test_build_provenance_max_chars_negative_preserved(tmp_path: Path):
    """max_chars=-1 应原样保留。"""
    result = build_provenance(tmp_path, parser_name="fallback", max_chars=-1, parser_version="1.0")
    assert result["max_chars"] == -1


def test_build_provenance_max_chars_one(tmp_path: Path):
    result = build_provenance(tmp_path, parser_name="fallback", max_chars=1, parser_version="1.0")
    assert result["max_chars"] == 1


def test_build_provenance_max_chars_int_type(tmp_path: Path):
    """max_chars 必须是 int 类型（即便输入是 bool）。"""
    result = build_provenance(tmp_path, parser_name="fallback", max_chars=True, parser_version="1.0")
    assert isinstance(result["max_chars"], int)
    assert result["max_chars"] == 1  # int(True) = 1


def test_build_provenance_evaluator_version_value(tmp_path: Path):
    """evaluator_version 来自 evaluation.EVALUATOR_VERSION 常量。"""
    result = build_provenance(tmp_path, parser_name="fallback", max_chars=800, parser_version="1.0")
    assert result["evaluator_version"] == EVALUATOR_VERSION
    assert result["evaluator_version"] == "1.1"


def test_build_provenance_report_version_value(tmp_path: Path):
    result = build_provenance(tmp_path, parser_name="fallback", max_chars=800, parser_version="1.0")
    assert result["report_version"] == REPORT_VERSION
    assert result["report_version"] == "1.1"


def test_build_provenance_run_timestamp_iso_is_iso_format(tmp_path: Path):
    """run_timestamp_iso 应能被 datetime.fromisoformat 解析。"""
    result = build_provenance(tmp_path, parser_name="fallback", max_chars=800, parser_version="1.0")
    parsed = datetime.fromisoformat(result["run_timestamp_iso"])
    assert parsed is not None


def test_build_provenance_dependencies_value_is_dict(tmp_path: Path):
    result = build_provenance(tmp_path, parser_name="fallback", max_chars=800, parser_version="1.0")
    assert isinstance(result["dependencies"], dict)


# =========================================================================
# build_devset_section dict 插入顺序
# =========================================================================


class _FakeManifest:
    """Minimal manifest stub for build_devset_section tests."""

    def __init__(self, **kwargs):
        self.devset_status = kwargs.get("devset_status", "incomplete")
        self.file_count = kwargs.get("file_count", 0)
        self.content_group_count = kwargs.get("content_group_count", 0)
        self.pdf_count = kwargs.get("pdf_count", 0)
        self.docx_count = kwargs.get("docx_count", 0)
        self.categories_covered = kwargs.get("categories_covered", [])


def test_build_devset_section_dict_insertion_order():
    """返回 dict 应按 6 个 key 顺序插入。"""
    m = _FakeManifest()
    result = build_devset_section(m)
    keys = list(result.keys())
    assert keys[0] == "status"
    assert keys[1] == "file_count"
    assert keys[2] == "content_group_count"
    assert keys[3] == "pdf_count"
    assert keys[4] == "docx_count"
    assert keys[5] == "categories_covered"


def test_build_devset_section_returns_exactly_six_keys():
    m = _FakeManifest()
    result = build_devset_section(m)
    assert set(result.keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_build_devset_section_status_value_passed_through():
    m = _FakeManifest(devset_status="complete")
    result = build_devset_section(m)
    assert result["status"] == "complete"


def test_build_devset_section_categories_empty_list():
    m = _FakeManifest(categories_covered=[])
    result = build_devset_section(m)
    assert result["categories_covered"] == []


def test_build_devset_section_categories_dict():
    """categories_covered 可以是任意类型（透传）。"""
    m = _FakeManifest(categories_covered={"a": 1, "b": 2})
    result = build_devset_section(m)
    assert result["categories_covered"] == {"a": 1, "b": 2}


def test_build_devset_section_zero_counts_propagated():
    m = _FakeManifest(file_count=0, content_group_count=0, pdf_count=0, docx_count=0)
    result = build_devset_section(m)
    assert result["file_count"] == 0
    assert result["content_group_count"] == 0
    assert result["pdf_count"] == 0
    assert result["docx_count"] == 0


def test_build_devset_section_negative_counts_propagated():
    """负数计数也会被透传（不校验）。"""
    m = _FakeManifest(file_count=-1, content_group_count=-2)
    result = build_devset_section(m)
    assert result["file_count"] == -1
    assert result["content_group_count"] == -2


# =========================================================================
# aggregate_summary top-level dict 插入顺序
# =========================================================================


def test_aggregate_summary_top_level_dict_insertion_order():
    """返回 dict 应按 counts → success_rates → ratio_macro_averages → silent_drop_total 顺序插入。"""
    result = aggregate_summary([])
    keys = list(result.keys())
    assert keys[0] == "counts"
    assert keys[1] == "success_rates"
    assert keys[2] == "ratio_macro_averages"
    assert keys[3] == "silent_drop_total"


def test_aggregate_summary_returns_exactly_four_top_keys():
    result = aggregate_summary([])
    assert set(result.keys()) == {
        "counts", "success_rates", "ratio_macro_averages", "silent_drop_total",
    }


def test_aggregate_summary_counts_section_has_exactly_one_entry():
    """counts section 仅含 element_count_total（_COUNT_METRICS 长度 1）。"""
    result = aggregate_summary([])
    assert set(result["counts"].keys()) == {"element_count_total"}


def test_aggregate_summary_success_rates_section_has_exactly_one_entry():
    """success_rates section 仅含 pipeline_success。"""
    result = aggregate_summary([])
    assert set(result["success_rates"].keys()) == {"pipeline_success"}


def test_aggregate_summary_ratio_macro_section_has_twelve_entries():
    """ratio_macro_averages section 含 12 项。"""
    result = aggregate_summary([])
    assert len(result["ratio_macro_averages"]) == 12
    assert set(result["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


# =========================================================================
# aggregate_summary ratio value=True / 1 / 1.0 算术行为
# =========================================================================


def test_aggregate_summary_ratio_value_true_treated_as_one():
    """ratio value=True（bool）：True 在算术中等于 1，参与 macro 平均。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": True}}},
        {"metrics": {"schema_valid": {"value": True}}},
    ]
    result = aggregate_summary(per_doc)
    # True + True = 2; len = 2; macro = 1.0
    assert result["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0


def test_aggregate_summary_ratio_value_mixed_true_and_false():
    """ratio value 混 True/False：True=1, False=0 → macro=0.5。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": True}}},
        {"metrics": {"schema_valid": {"value": False}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5


def test_aggregate_summary_ratio_value_int_one_treated_as_one():
    """ratio value=1（int）：参与算术。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1}}},
        {"metrics": {"schema_valid": {"value": 1}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0


def test_aggregate_summary_ratio_value_float_one_treated_as_one():
    """ratio value=1.0（float）：参与算术。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0


def test_aggregate_summary_ratio_value_zero_participates():
    """ratio value=0.0（falsy 但 not None）：仍参与 macro 平均。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.0}}},
        {"metrics": {"schema_valid": {"value": 1.0}}},
    ]
    result = aggregate_summary(per_doc)
    # 0 + 1 = 1; 1 / 2 = 0.5
    assert result["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert result["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2


def test_aggregate_summary_ratio_value_zero_string_not_participating():
    """ratio value='0'（str）：'0' is not None True → 参与，但 sum(['0']) raises TypeError。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": "0"}}},
    ]
    with pytest.raises(TypeError):
        aggregate_summary(per_doc)


def test_aggregate_summary_count_value_true_treated_as_one():
    """count value=True（bool）：True 在 sum 中等于 1。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": True}}},
        {"metrics": {"element_count_total": {"value": True}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 2


def test_aggregate_summary_count_value_false_treated_as_zero():
    """count value=False（bool）：False == 0，但 `is not None` True → 参与 sum(False) = 0。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": False}}},
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    result = aggregate_summary(per_doc)
    # False + 5 = 0 + 5 = 5
    assert result["counts"]["element_count_total"]["sum"] == 5
    assert result["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_silent_drop_value_true_treated_as_one():
    """silent_drop_count value=True：sum 中等于 1。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": True}}},
        {"metrics": {"silent_drop_count": {"value": 2}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] == 3  # 1 + 2


def test_aggregate_summary_success_rate_with_value_one_not_counted():
    """pipeline_success value=1（int）：is True False → 不计入 success_count。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": 1}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    result = aggregate_summary(per_doc)
    # 只有 True 那个计入
    assert result["success_rates"]["pipeline_success"]["success_count"] == 1
    assert result["success_rates"]["pipeline_success"]["total"] == 2


def test_aggregate_summary_success_rate_with_value_one_float_not_counted():
    """pipeline_success value=1.0：is True False → 不计入。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": 1.0}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["success_rates"]["pipeline_success"]["success_count"] == 0


# =========================================================================
# aggregate_summary counts/success/ratio entry key 集合精确
# =========================================================================


def test_aggregate_summary_counts_entry_keys_exact_set():
    """counts 每个 entry 含 sum + participating_docs 两个 key。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    result = aggregate_summary(per_doc)
    assert set(result["counts"]["element_count_total"].keys()) == {"sum", "participating_docs"}


def test_aggregate_summary_success_rates_entry_keys_exact_set():
    """success_rates 每个 entry 含 success_count + total + rate 三个 key。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    result = aggregate_summary(per_doc)
    assert set(result["success_rates"]["pipeline_success"].keys()) == {
        "success_count", "total", "rate",
    }


def test_aggregate_summary_ratio_macro_entry_keys_exact_set():
    """ratio_macro_averages 每个 entry 含 macro_average + participating_docs + not_evaluated 三个 key。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
    ]
    result = aggregate_summary(per_doc)
    assert set(result["ratio_macro_averages"]["schema_valid"].keys()) == {
        "macro_average", "participating_docs", "not_evaluated",
    }


def test_aggregate_summary_counts_entry_dict_size_two():
    per_doc = [{"metrics": {"element_count_total": {"value": 5}}}]
    result = aggregate_summary(per_doc)
    assert len(result["counts"]["element_count_total"]) == 2


def test_aggregate_summary_success_rates_entry_dict_size_three():
    per_doc = [{"metrics": {"pipeline_success": {"value": True}}}]
    result = aggregate_summary(per_doc)
    assert len(result["success_rates"]["pipeline_success"]) == 3


def test_aggregate_summary_ratio_macro_entry_dict_size_three():
    per_doc = [{"metrics": {"schema_valid": {"value": 1.0}}}]
    result = aggregate_summary(per_doc)
    assert len(result["ratio_macro_averages"]["schema_valid"]) == 3


# =========================================================================
# aggregate_summary not_evaluated 算法精确
# =========================================================================


def test_aggregate_summary_not_evaluated_excludes_participating():
    """not_evaluated = total - participating_docs。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {}},  # missing key entirely
    ]
    result = aggregate_summary(per_doc)
    # 3 total - 1 participating = 2 not_evaluated
    assert result["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 2


def test_aggregate_summary_not_evaluated_zero_when_all_participate():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.0}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 0


def test_aggregate_summary_not_evaluated_all_when_none_participate():
    per_doc = [
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 2
    assert result["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 0


# =========================================================================
# module-level 结构 / imports
# =========================================================================


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


def test_module_all_exact():
    """__all__ 精确包含 5 个公共 callable。"""
    import evaluation.report as m
    assert set(m.__all__) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_all_does_not_contain_private_constants():
    import evaluation.report as m
    assert "_RATIO_METRICS" not in m.__all__
    assert "_COUNT_METRICS" not in m.__all__
    assert "_SUCCESS_BOOL_METRICS" not in m.__all__


def test_module_all_size_five():
    import evaluation.report as m
    assert len(m.__all__) == 5


def test_module_uses_future_annotations():
    import evaluation.report as m
    assert hasattr(m, "annotations")  # from __future__ import annotations


def test_module_docstring_present():
    import evaluation.report as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_aggregation_rules():
    """docstring 提到聚合规则。"""
    import evaluation.report as m
    assert "counts" in m.__doc__ or "求和" in m.__doc__


def test_module_docstring_mentions_no_mixing():
    """docstring 应提到不混合类型。"""
    import evaluation.report as m
    assert "不混合" in m.__doc__ or "macro" in m.__doc__


# =========================================================================
# get_git_provenance 异常路径补充
# =========================================================================


def test_get_git_provenance_subprocess_called_with_cwd(tmp_path: Path, monkeypatch):
    """subprocess.run 必须以 cwd=str(project_root) 调用。"""
    captured = {}

    class _R:
        def __init__(self, rc, out):
            self.returncode = rc
            self.stdout = out

    def fake_run(cmd, **kwargs):
        captured.setdefault("cwds", []).append(kwargs.get("cwd"))
        return _R(0, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    get_git_provenance(tmp_path)
    assert captured["cwds"][0] == str(tmp_path)


def test_get_git_provenance_subprocess_called_with_encoding_utf8(tmp_path: Path, monkeypatch):
    """subprocess.run 必须以 encoding='utf-8' 调用。"""
    captured = {}

    class _R:
        def __init__(self, rc, out):
            self.returncode = rc
            self.stdout = out

    def fake_run(cmd, **kwargs):
        captured.setdefault("encodings", []).append(kwargs.get("encoding"))
        return _R(0, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    get_git_provenance(tmp_path)
    assert all(e == "utf-8" for e in captured["encodings"])
    assert len(captured["encodings"]) == 2


def test_get_git_provenance_subprocess_called_with_errors_replace(tmp_path: Path, monkeypatch):
    """subprocess.run 必须以 errors='replace' 调用。"""
    captured = {}

    class _R:
        def __init__(self, rc, out):
            self.returncode = rc
            self.stdout = out

    def fake_run(cmd, **kwargs):
        captured.setdefault("errors", []).append(kwargs.get("errors"))
        return _R(0, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    get_git_provenance(tmp_path)
    assert all(e == "replace" for e in captured["errors"])


def test_get_git_provenance_subprocess_called_with_capture_output(tmp_path: Path, monkeypatch):
    captured = {}

    class _R:
        def __init__(self, rc, out):
            self.returncode = rc
            self.stdout = out

    def fake_run(cmd, **kwargs):
        captured.setdefault("capture_output", []).append(kwargs.get("capture_output"))
        return _R(0, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    get_git_provenance(tmp_path)
    assert all(c is True for c in captured["capture_output"])


def test_get_git_provenance_subprocess_called_with_text_true(tmp_path: Path, monkeypatch):
    captured = {}

    class _R:
        def __init__(self, rc, out):
            self.returncode = rc
            self.stdout = out

    def fake_run(cmd, **kwargs):
        captured.setdefault("text", []).append(kwargs.get("text"))
        return _R(0, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    get_git_provenance(tmp_path)
    assert all(t is True for t in captured["text"])


# =========================================================================
# 综合行为：完整报告装配
# =========================================================================


def test_aggregate_summary_with_one_doc_all_metrics_set():
    """一个 doc 所有 metrics 都 set → 各 ratio macro 平均等于该值。"""
    per_doc = [{
        "metrics": {
            "schema_valid": {"value": 1.0},
            "pdf_locator_valid_ratio": {"value": 0.5},
            "docx_locator_valid_ratio": {"value": 0.5},
            "image_resource_exists_ratio": {"value": 1.0},
            "chunk_reference_intact_ratio": {"value": 1.0},
            "text_preservation_equal": {"value": True},
            "text_char_multiset_precision": {"value": 0.5},
            "text_char_multiset_recall": {"value": 0.5},
            "heading_boundary_compliance": {"value": 1.0},
            "chunk_boundary_precision": {"value": 0.5},
            "chunk_boundary_recall": {"value": 0.5},
            "chunk_boundary_f1": {"value": 0.5},
            "element_count_total": {"value": 10},
            "pipeline_success": {"value": True},
            "silent_drop_count": {"value": 2},
        }
    }]
    result = aggregate_summary(per_doc)
    assert result["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert result["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 0.5
    assert result["counts"]["element_count_total"]["sum"] == 10
    assert result["success_rates"]["pipeline_success"]["success_count"] == 1
    assert result["success_rates"]["pipeline_success"]["rate"] == 1.0
    assert result["silent_drop_total"] == 2


def test_aggregate_summary_two_docs_mixed_metrics():
    per_doc = [
        {"metrics": {
            "schema_valid": {"value": 1.0},
            "element_count_total": {"value": 5},
            "pipeline_success": {"value": True},
            "silent_drop_count": {"value": 1},
        }},
        {"metrics": {
            "schema_valid": {"value": 0.0},
            "element_count_total": {"value": 10},
            "pipeline_success": {"value": False},
            "silent_drop_count": {"value": 3},
        }},
    ]
    result = aggregate_summary(per_doc)
    assert result["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert result["counts"]["element_count_total"]["sum"] == 15
    assert result["counts"]["element_count_total"]["participating_docs"] == 2
    assert result["success_rates"]["pipeline_success"]["success_count"] == 1
    assert result["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert result["silent_drop_total"] == 4


def test_aggregate_summary_does_not_compute_figure_caption_metrics():
    """figure_caption_* 不在 _RATIO_METRICS 中，aggregate 不应处理。"""
    per_doc = [{"metrics": {"figure_caption_precision": {"value": 1.0}}}]
    result = aggregate_summary(per_doc)
    assert "figure_caption_precision" not in result["ratio_macro_averages"]
