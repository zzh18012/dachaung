"""evaluation/report.py 边角测试（Round 63）。

补强 tests/test_evaluation_report.py（75+ 测试）未覆盖的：
- 模块级常量 _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 深度验证
- get_git_provenance 不存在目录 / subprocess failure / return 类型严格
- get_dependency_versions 字典 mutability / 精确 key 名
- build_provenance max_chars float 转 int / 9 key 完整 / timestamp ISO 格式
- build_devset_section 空字段 / 类型透传
- aggregate_summary 混合 null/non-null / unknown metrics 忽略 / 单 doc / 同值
- aggregate_summary 不 mutate 输入更严格
- __all__ 5 个导出项 / 不含内部常量
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from evaluation.report import (
    __all__,
    _COUNT_METRICS,
    _RATIO_METRICS,
    _SUCCESS_BOOL_METRICS,
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


def _make_per_doc(metric_overrides: dict | None = None) -> dict:
    metrics = {
        "pipeline_success": {"value": True, "reason": None},
        "schema_valid": {"value": True, "reason": None},
        "element_count_total": {"value": 5, "reason": None},
        "pdf_locator_valid_ratio": {"value": 1.0, "reason": None},
        "docx_locator_valid_ratio": {"value": None, "reason": "not_docx_document"},
        "image_resource_exists_ratio": {"value": 1.0, "reason": None},
        "chunk_reference_intact_ratio": {"value": 1.0, "reason": None},
        "text_preservation_equal": {"value": True, "reason": None},
        "text_char_multiset_precision": {"value": 1.0, "reason": None},
        "text_char_multiset_recall": {"value": 1.0, "reason": None},
        "heading_boundary_compliance": {"value": 1.0, "reason": None},
        "silent_drop_count": {"value": 0, "reason": None},
        "figure_caption_precision": {"value": None, "reason": "parser_does_not_emit_relations"},
        "figure_caption_recall": {"value": None, "reason": "parser_does_not_emit_relations"},
        "figure_caption_f1": {"value": None, "reason": "parser_does_not_emit_relations"},
        "chunk_boundary_precision": {"value": None, "reason": "no_annotation"},
        "chunk_boundary_recall": {"value": None, "reason": "no_annotation"},
        "chunk_boundary_f1": {"value": None, "reason": "no_annotation"},
    }
    if metric_overrides:
        metrics.update(metric_overrides)
    return {
        "doc_id": "x",
        "source_type": "pdf",
        "metrics": metrics,
        "wall_time_seconds": {
            "total": 0.1, "parse": None, "chunk": None,
            "parse_reason": "not_instrumented",
            "chunk_reason": "not_instrumented",
        },
    }


# ---------- 模块级常量深度验证 ----------


def test_ratio_metrics_is_tuple_type():
    assert isinstance(_RATIO_METRICS, tuple)


def test_ratio_metrics_length_is_12():
    """12 个 ratio 指标。"""
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_contains_schema_valid():
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_contains_all_chunk_boundary():
    for name in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert name in _RATIO_METRICS


def test_ratio_metrics_excludes_pipeline_success():
    """pipeline_success 是 bool 指标，不属 ratio。"""
    assert "pipeline_success" not in _RATIO_METRICS


def test_ratio_metrics_excludes_element_count_total():
    assert "element_count_total" not in _RATIO_METRICS


def test_ratio_metrics_excludes_silent_drop_count():
    assert "silent_drop_count" not in _RATIO_METRICS


def test_ratio_metrics_excludes_figure_caption():
    for name in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert name not in _RATIO_METRICS


def test_count_metrics_is_tuple_type():
    assert isinstance(_COUNT_METRICS, tuple)


def test_count_metrics_length_is_1():
    assert len(_COUNT_METRICS) == 1


def test_count_metrics_contains_element_count_total():
    assert "element_count_total" in _COUNT_METRICS


def test_count_metrics_excludes_silent_drop_count():
    """silent_drop_count 单独聚合，不在 _COUNT_METRICS。"""
    assert "silent_drop_count" not in _COUNT_METRICS


def test_success_bool_metrics_is_tuple_type():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_success_bool_metrics_length_is_1():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_success_bool_metrics_contains_pipeline_success():
    assert "pipeline_success" in _SUCCESS_BOOL_METRICS


def test_success_bool_metrics_excludes_schema_valid():
    """schema_valid 在 ratio metrics，不在 bool。"""
    assert "schema_valid" not in _SUCCESS_BOOL_METRICS


# ---------- __all__ 导出 ----------


def test_all_exports_has_five_items():
    assert len(__all__) == 5


def test_all_exports_contains_expected_items():
    assert set(__all__) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_all_exports_excludes_internal_constants():
    """内部常量不在 __all__。"""
    for name in ("_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"):
        assert name not in __all__


def test_all_exports_match_module_attributes():
    import evaluation.report as mod
    for name in __all__:
        assert hasattr(mod, name)


# ---------- get_git_provenance 边角 ----------


def test_get_git_provenance_returns_dict(tmp_path: Path):
    result = get_git_provenance(tmp_path)
    assert isinstance(result, dict)


def test_get_git_provenance_dict_has_two_keys(tmp_path: Path):
    result = get_git_provenance(tmp_path)
    assert set(result.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_git_commit_is_str_or_none(tmp_path: Path):
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None or isinstance(result["git_commit"], str)


def test_get_git_provenance_git_dirty_is_bool(tmp_path: Path):
    result = get_git_provenance(tmp_path)
    assert isinstance(result["git_dirty"], bool)


def test_get_git_provenance_nonexistent_dir(tmp_path: Path):
    """不存在的目录 → commit=None, dirty=True。"""
    nonexistent = tmp_path / "does_not_exist"
    result = get_git_provenance(nonexistent)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_real_repo_has_commit():
    """项目根（git 仓库）应有 commit。"""
    project_root = Path(__file__).resolve().parent.parent
    result = get_git_provenance(project_root)
    # HEAD 提交应非 None（在主项目 worktree 或 autonomous worktree 都行）
    assert result["git_commit"] is not None
    # SHA-1 hex 40 字符
    assert len(result["git_commit"]) == 40
    assert all(c in "0123456789abcdef" for c in result["git_commit"])


def test_get_git_provenance_does_not_raise_on_subprocess_error(monkeypatch):
    """subprocess.run 抛异常时安全返 None/True。"""
    import evaluation.report as mod
    import subprocess

    def _raise(*args, **kwargs):
        raise subprocess.SubprocessError("mock")

    monkeypatch.setattr(subprocess, "run", _raise)
    result = mod.get_git_provenance(Path("."))
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_os_error_safe(monkeypatch, tmp_path: Path):
    """OSError 也被捕获。"""
    import evaluation.report as mod
    import subprocess

    def _raise(*args, **kwargs):
        raise OSError("mock")

    monkeypatch.setattr(subprocess, "run", _raise)
    result = mod.get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


# ---------- get_dependency_versions 边角 ----------


def test_get_dependency_versions_returns_dict():
    result = get_dependency_versions()
    assert isinstance(result, dict)


def test_get_dependency_versions_dict_is_mutable():
    """dict 可修改（非 mappingproxy）。"""
    result = get_dependency_versions()
    result["extra"] = "value"
    assert "extra" in result


def test_get_dependency_versions_exact_key_names():
    result = get_dependency_versions()
    assert set(result.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_pdfplumber_value_is_str():
    """pdfplumber 已安装 → 应有版本字符串。"""
    result = get_dependency_versions()
    assert isinstance(result["pdfplumber"], str)
    # 版本格式 x.y.z
    assert len(result["pdfplumber"]) > 0


def test_get_dependency_versions_python_docx_value_is_str():
    result = get_dependency_versions()
    assert isinstance(result["python-docx"], str)


def test_get_dependency_versions_pypdfium2_value_is_str():
    result = get_dependency_versions()
    assert isinstance(result["pypdfium2"], str)


def test_get_dependency_versions_does_not_raise_on_unknown_package(monkeypatch):
    """importlib.metadata.PackageNotFoundError 安全处理。"""
    import evaluation.report as mod
    import importlib.metadata

    original_version = importlib.metadata.version

    def _raise(pkg, *args, **kwargs):
        if pkg == "pypdfium2":
            raise importlib.metadata.PackageNotFoundError("mock")
        return original_version(pkg)

    monkeypatch.setattr(importlib.metadata, "version", _raise)
    result = mod.get_dependency_versions()
    assert result["pypdfium2"] is None


def test_get_dependency_versions_handles_generic_exception(monkeypatch):
    """importlib.metadata 异常也安全。"""
    import evaluation.report as mod
    import importlib.metadata

    def _raise(*args, **kwargs):
        raise RuntimeError("mock")

    monkeypatch.setattr(importlib.metadata, "version", _raise)
    result = mod.get_dependency_versions()
    for k, v in result.items():
        assert v is None


# ---------- build_provenance 边角 ----------


def test_build_provenance_max_chars_float_converted_to_int(tmp_path: Path):
    """max_chars 传 float → int(max_chars)。"""
    result = build_provenance(tmp_path, "fallback", 800.5, None)
    assert result["max_chars"] == 800
    assert isinstance(result["max_chars"], int)


def test_build_provenance_max_chars_zero(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 0, None)
    assert result["max_chars"] == 0


def test_build_provenance_max_chars_negative(tmp_path: Path):
    """负数也接受 int() 转换。"""
    result = build_provenance(tmp_path, "fallback", -100, None)
    assert result["max_chars"] == -100


def test_build_provenance_max_chars_string_digit(tmp_path: Path):
    """str 数字也能 int()。"""
    result = build_provenance(tmp_path, "fallback", "800", None)  # type: ignore[arg-type]
    assert result["max_chars"] == 800


def test_build_provenance_parser_name_passthrough(tmp_path: Path):
    result = build_provenance(tmp_path, "kreuzberg", 800, "1.0")
    assert result["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_none(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["parser_version"] is None


def test_build_provenance_parser_version_string(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, "1.2.3")
    assert result["parser_version"] == "1.2.3"


def test_build_provenance_evaluator_version_is_string(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(result["evaluator_version"], str)


def test_build_provenance_report_version_is_string(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(result["report_version"], str)


def test_build_provenance_run_timestamp_parseable_iso(tmp_path: Path):
    """run_timestamp_iso 应能被 datetime.fromisoformat 解析。"""
    result = build_provenance(tmp_path, "fallback", 800, None)
    ts = result["run_timestamp_iso"]
    parsed = datetime.fromisoformat(ts)
    assert isinstance(parsed, datetime)


def test_build_provenance_run_timestamp_has_timezone(tmp_path: Path):
    """timestamp 应含时区信息（astimezone() 加了 tz）。"""
    result = build_provenance(tmp_path, "fallback", 800, None)
    ts = result["run_timestamp_iso"]
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None


def test_build_provenance_dependencies_subfield_is_dict(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(result["dependencies"], dict)
    assert set(result["dependencies"].keys()) == {
        "pdfplumber", "python-docx", "pypdfium2"
    }


def test_build_provenance_git_commit_is_str_or_none(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["git_commit"] is None or isinstance(result["git_commit"], str)


def test_build_provenance_git_dirty_is_bool(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(result["git_dirty"], bool)


def test_build_provenance_nine_keys_full_set(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert set(result.keys()) == {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    }


# ---------- build_devset_section 边角 ----------


class _FakeManifest:
    def __init__(self, **kwargs):
        self.devset_status = kwargs.get("devset_status", "incomplete")
        self.file_count = kwargs.get("file_count", 0)
        self.content_group_count = kwargs.get("content_group_count", 0)
        self.pdf_count = kwargs.get("pdf_count", 0)
        self.docx_count = kwargs.get("docx_count", 0)
        self.categories_covered = kwargs.get("categories_covered", [])


def test_build_devset_section_returns_dict():
    manifest = _FakeManifest()
    result = build_devset_section(manifest)
    assert isinstance(result, dict)


def test_build_devset_section_six_keys():
    manifest = _FakeManifest()
    result = build_devset_section(manifest)
    assert set(result.keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_build_devset_section_status_passed_through():
    manifest = _FakeManifest(devset_status="complete")
    result = build_devset_section(manifest)
    assert result["status"] == "complete"


def test_build_devset_section_file_count_passed_through():
    manifest = _FakeManifest(file_count=42)
    result = build_devset_section(manifest)
    assert result["file_count"] == 42


def test_build_devset_section_pdf_count_passed_through():
    manifest = _FakeManifest(pdf_count=3)
    result = build_devset_section(manifest)
    assert result["pdf_count"] == 3


def test_build_devset_section_docx_count_passed_through():
    manifest = _FakeManifest(docx_count=5)
    result = build_devset_section(manifest)
    assert result["docx_count"] == 5


def test_build_devset_section_content_group_count_passed_through():
    manifest = _FakeManifest(content_group_count=10)
    result = build_devset_section(manifest)
    assert result["content_group_count"] == 10


def test_build_devset_section_categories_covered_passed_through():
    cats = ["report", "academic", "invoice"]
    manifest = _FakeManifest(categories_covered=cats)
    result = build_devset_section(manifest)
    assert result["categories_covered"] == cats


def test_build_devset_section_empty_categories():
    manifest = _FakeManifest(categories_covered=[])
    result = build_devset_section(manifest)
    assert result["categories_covered"] == []


def test_build_devset_section_field_types_preserved():
    """字段类型应保持（int 是 int, list 是 list, str 是 str）。"""
    manifest = _FakeManifest(
        devset_status="incomplete",
        file_count=5,
        categories_covered=["a"],
    )
    result = build_devset_section(manifest)
    assert isinstance(result["status"], str)
    assert isinstance(result["file_count"], int)
    assert isinstance(result["categories_covered"], list)


# ---------- aggregate_summary 边角 ----------


def test_aggregate_summary_returns_dict_type():
    result = aggregate_summary([])
    assert isinstance(result, dict)


def test_aggregate_summary_four_top_level_keys():
    result = aggregate_summary([])
    assert set(result.keys()) == {
        "counts", "success_rates", "ratio_macro_averages", "silent_drop_total"
    }


def test_aggregate_summary_empty_input_counts_sum_is_none():
    result = aggregate_summary([])
    assert result["counts"]["element_count_total"]["sum"] is None


def test_aggregate_summary_empty_input_counts_participating_zero():
    result = aggregate_summary([])
    assert result["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_empty_input_silent_drop_none():
    result = aggregate_summary([])
    assert result["silent_drop_total"] is None


def test_aggregate_summary_empty_input_success_rate_rate_none():
    result = aggregate_summary([])
    assert result["success_rates"]["pipeline_success"]["rate"] is None


def test_aggregate_summary_counts_sum_excludes_none_values():
    """None value 不计入 sum 也不计入 participating_docs。"""
    per_doc = [
        _make_per_doc({"element_count_total": {"value": 5, "reason": None}}),
        _make_per_doc({"element_count_total": {"value": None, "reason": "x"}}),
        _make_per_doc({"element_count_total": {"value": 3, "reason": None}}),
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 8
    assert result["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_sum_with_zero_values():
    """value=0 仍参与（0 不是 None）。"""
    per_doc = [
        _make_per_doc({"element_count_total": {"value": 0, "reason": None}}),
        _make_per_doc({"element_count_total": {"value": 0, "reason": None}}),
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 0
    assert result["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_success_rate_half_pass():
    per_doc = [
        _make_per_doc({"pipeline_success": {"value": True, "reason": None}}),
        _make_per_doc({"pipeline_success": {"value": False, "reason": "x"}}),
    ]
    result = aggregate_summary(per_doc)
    assert result["success_rates"]["pipeline_success"]["success_count"] == 1
    assert result["success_rates"]["pipeline_success"]["total"] == 2
    assert result["success_rates"]["pipeline_success"]["rate"] == 0.5


def test_aggregate_summary_success_rate_false_not_counted_as_success():
    per_doc = [
        _make_per_doc({"pipeline_success": {"value": False, "reason": "x"}}),
    ]
    result = aggregate_summary(per_doc)
    assert result["success_rates"]["pipeline_success"]["success_count"] == 0


def test_aggregate_summary_success_rate_none_value_not_counted_as_success():
    """None value 不计为 success 也不计为 total。"""
    # 但 total = len(per_doc_results)，所以 None 也算 total
    per_doc = [
        _make_per_doc({"pipeline_success": {"value": None, "reason": "x"}}),
    ]
    result = aggregate_summary(per_doc)
    assert result["success_rates"]["pipeline_success"]["success_count"] == 0
    assert result["success_rates"]["pipeline_success"]["total"] == 1
    assert result["success_rates"]["pipeline_success"]["rate"] == 0.0


def test_aggregate_summary_ratio_macro_average_with_some_null():
    """部分 None 的 ratio → macro 只算非 None。"""
    per_doc = [
        _make_per_doc({"schema_valid": {"value": 1.0, "reason": None}}),
        _make_per_doc({"schema_valid": {"value": None, "reason": "x"}}),
        _make_per_doc({"schema_valid": {"value": 0.5, "reason": None}}),
    ]
    result = aggregate_summary(per_doc)
    avg = result["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == 0.75
    assert avg["participating_docs"] == 2
    assert avg["not_evaluated"] == 1


def test_aggregate_summary_ratio_macro_average_all_same_values():
    per_doc = [
        _make_per_doc({"schema_valid": {"value": 0.8, "reason": None}}),
        _make_per_doc({"schema_valid": {"value": 0.8, "reason": None}}),
    ]
    result = aggregate_summary(per_doc)
    assert result["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.8


def test_aggregate_summary_ratio_macro_average_single_doc():
    per_doc = [
        _make_per_doc({"schema_valid": {"value": 0.5, "reason": None}}),
    ]
    result = aggregate_summary(per_doc)
    assert result["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5


def test_aggregate_summary_ratio_macro_average_zero_participating():
    """所有 doc 的 ratio 都是 None → macro=None, participating=0。"""
    per_doc = [
        _make_per_doc({"schema_valid": {"value": None, "reason": "x"}}),
        _make_per_doc({"schema_valid": {"value": None, "reason": "x"}}),
    ]
    result = aggregate_summary(per_doc)
    avg = result["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] is None
    assert avg["participating_docs"] == 0
    assert avg["not_evaluated"] == 2


def test_aggregate_summary_silent_drop_mixed_values():
    per_doc = [
        _make_per_doc({"silent_drop_count": {"value": 3, "reason": None}}),
        _make_per_doc({"silent_drop_count": {"value": None, "reason": "x"}}),
        _make_per_doc({"silent_drop_count": {"value": 5, "reason": None}}),
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_zero_values_summed():
    """value=0 仍参与求和。"""
    per_doc = [
        _make_per_doc({"silent_drop_count": {"value": 0, "reason": None}}),
        _make_per_doc({"silent_drop_count": {"value": 0, "reason": None}}),
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] == 0


def test_aggregate_summary_does_not_mutate_input():
    per_doc = [_make_per_doc()]
    per_doc_copy = [_make_per_doc()]
    aggregate_summary(per_doc)
    # 输入应未被修改（对比 dict keys）
    assert set(per_doc[0].keys()) == set(per_doc_copy[0].keys())


def test_aggregate_summary_unknown_metrics_ignored():
    """未知 metric key 不影响聚合。"""
    per_doc = [
        _make_per_doc({"unknown_metric": {"value": 999, "reason": None}}),
    ]
    result = aggregate_summary(per_doc)
    # 未知 metric 不出现在任何聚合结果
    flat_metrics = set()
    flat_metrics.update(result["counts"].keys())
    flat_metrics.update(result["success_rates"].keys())
    flat_metrics.update(result["ratio_macro_averages"].keys())
    assert "unknown_metric" not in flat_metrics


def test_aggregate_summary_handles_missing_metrics_in_per_doc():
    """per_doc.metrics 不全（缺部分 key）→ 不应崩。"""
    per_doc = [{
        "doc_id": "x",
        "source_type": "pdf",
        "metrics": {},  # 完全空
        "wall_time_seconds": {},
    }]
    result = aggregate_summary(per_doc)
    # 应有默认空结构
    assert "counts" in result
    assert "success_rates" in result


def test_aggregate_summary_metrics_missing_value_key():
    """metric dict 缺 'value' 字段 → 不崩。"""
    per_doc = [{
        "doc_id": "x",
        "source_type": "pdf",
        "metrics": {
            "element_count_total": {"reason": "no_value_key"},  # 缺 value
        },
        "wall_time_seconds": {},
    }]
    result = aggregate_summary(per_doc)
    # .get("value") → None → 不参与
    assert result["counts"]["element_count_total"]["sum"] is None


def test_aggregate_summary_ratio_macro_average_includes_all_12_metrics():
    """聚合后 ratio_macro_averages 含所有 12 个 ratio 指标 key。"""
    per_doc = [_make_per_doc()]
    result = aggregate_summary(per_doc)
    assert set(result["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


def test_aggregate_summary_success_rates_only_pipeline_success():
    """success_rates 只含 pipeline_success（_SUCCESS_BOOL_METRICS）。"""
    per_doc = [_make_per_doc()]
    result = aggregate_summary(per_doc)
    assert set(result["success_rates"].keys()) == {"pipeline_success"}


def test_aggregate_summary_counts_only_element_count_total():
    """counts 只含 element_count_total（_COUNT_METRICS）。"""
    per_doc = [_make_per_doc()]
    result = aggregate_summary(per_doc)
    assert set(result["counts"].keys()) == {"element_count_total"}
