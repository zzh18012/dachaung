"""evaluation/report.py 第五十七轮 edges 测试（Round 606）。

补强 edges56 未触及的角度（第四十二批）。

新角度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元素固定
- _RATIO_METRICS 顺序
- _RATIO_METRICS 各项 in/out
- _RATIO_METRICS 不含 figure_caption_*
- _RATIO_METRICS 不含 silent_drop_count
- _RATIO_METRICS 不含 element_count_total
- _RATIO_METRICS 不含 pipeline_success
- get_git_provenance 失败路径（subprocess.run raise OSError / SubprocessError）
- get_git_provenance returncode != 0 路径
- get_git_provenance stdout 空字符串
- get_git_provenance porcelain stdout 非空 → dirty=True
- get_git_provenance porcelain stdout 空 → dirty=False
- get_git_provenance porcelain returncode != 0 → dirty=True
- get_dependency_versions 包不存在 → None
- get_dependency_versions PackageNotFoundError → None
- get_dependency_versions 抛 Exception → None
- get_dependency_versions 总是返回 3 个 keys
- build_provenance 字段类型
- build_provenance max_chars 转 int
- build_provenance run_timestamp_iso 是 ISO 格式
- build_devset_section 全字段
- aggregate_summary counts None 处理
- aggregate_summary counts 0 值不参与（None 才过滤）
- aggregate_summary success_rates 全 True / 全 False / 空
- aggregate_summary ratio_macro_averages 空 values / 全 None
- aggregate_summary silent_drop_total None / 全 None
- aggregate_summary 多次调用幂等
- module source 字符串精确
- AST 结构
- forbidden tokens 第七十七批
"""

from __future__ import annotations

import ast
import inspect
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import EVALUATOR_VERSION, REPORT_VERSION
from evaluation import report as rmod
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


# ---------- _RATIO_METRICS 元素固定 第四十二批


def test_ratio_metrics_len_twelve_batch42():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_contains_schema_valid_batch42():
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_contains_pdf_locator_batch42():
    assert "pdf_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_docx_locator_batch42():
    assert "docx_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_image_resource_batch42():
    assert "image_resource_exists_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_reference_batch42():
    assert "chunk_reference_intact_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_text_preservation_equal_batch42():
    assert "text_preservation_equal" in _RATIO_METRICS


def test_ratio_metrics_contains_text_char_precision_batch42():
    assert "text_char_multiset_precision" in _RATIO_METRICS


def test_ratio_metrics_contains_text_char_recall_batch42():
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_contains_heading_boundary_batch42():
    assert "heading_boundary_compliance" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_precision_batch42():
    assert "chunk_boundary_precision" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_recall_batch42():
    assert "chunk_boundary_recall" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_f1_batch42():
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_first_schema_valid_batch42():
    assert _RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_last_chunk_boundary_f1_batch42():
    assert _RATIO_METRICS[-1] == "chunk_boundary_f1"


def test_ratio_metrics_no_figure_caption_batch42():
    """figure_caption_* 始终 null，不参与 macro average。"""
    for m in _RATIO_METRICS:
        assert not m.startswith("figure_caption_")


def test_ratio_metrics_no_silent_drop_batch42():
    assert "silent_drop_count" not in _RATIO_METRICS


def test_ratio_metrics_no_element_count_batch42():
    assert "element_count_total" not in _RATIO_METRICS


def test_ratio_metrics_no_pipeline_success_batch42():
    assert "pipeline_success" not in _RATIO_METRICS


# ---------- _COUNT_METRICS 元素固定 第四十二批


def test_count_metrics_len_one_batch42():
    assert len(_COUNT_METRICS) == 1


def test_count_metrics_only_element_count_total_batch42():
    assert _COUNT_METRICS == ("element_count_total",)


# ---------- _SUCCESS_BOOL_METRICS 元素固定 第四十二批


def test_success_bool_metrics_len_one_batch42():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_success_bool_metrics_only_pipeline_success_batch42():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


# ---------- get_git_provenance 失败路径 第四十二批


def test_get_git_provenance_oserror_returns_dirty_batch42(tmp_path):
    """OSError → commit=None, dirty=True。"""
    with patch("subprocess.run", side_effect=OSError("boom")):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_subprocess_error_returns_dirty_batch42(tmp_path):
    """SubprocessError → commit=None, dirty=True。"""
    with patch("subprocess.run", side_effect=subprocess.SubprocessError("boom")):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_timeout_returns_dirty_batch42(tmp_path):
    """TimeoutExpired 是 SubprocessError 子类。"""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10)):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_rev_parse_nonzero_batch42(tmp_path):
    """rev-parse 失败 → commit=None；但 porcelain 也跑。"""
    r1 = MagicMock(returncode=1, stdout="")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_rev_parse_stdout_empty_batch42(tmp_path):
    """rev-parse returncode=0 但 stdout 空 → commit=None。"""
    r1 = MagicMock(returncode=0, stdout="")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_rev_parse_stdout_whitespace_batch42(tmp_path):
    """rev-parse stdout 仅空白 → strip 后为空 → commit=None。"""
    r1 = MagicMock(returncode=0, stdout="   \n  ")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_rev_parse_commit_returned_batch42(tmp_path):
    """正常 rev-parse 返回 commit。"""
    r1 = MagicMock(returncode=0, stdout="abc123\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"


def test_get_git_provenance_porcelain_nonzero_keeps_dirty_false_batch42(tmp_path):
    """porcelain returncode != 0 → bool(False and X) = False（实现是短路 and）。"""
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=1, stdout="")  # porcelain 失败
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_get_git_provenance_porcelain_empty_clean_batch42(tmp_path):
    """porcelain 输出空 → dirty=False。"""
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_get_git_provenance_porcelain_only_whitespace_clean_batch42(tmp_path):
    """porcelain stdout 仅空白 → strip 后空 → dirty=False。"""
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="  \n  ")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_get_git_provenance_porcelain_with_output_dirty_batch42(tmp_path):
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout=" M file.txt\n")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


def test_get_git_provenance_returns_dict_batch42(tmp_path):
    with patch("subprocess.run"):
        out = get_git_provenance(tmp_path)
    assert isinstance(out, dict)


def test_get_git_provenance_keys_count_batch42(tmp_path):
    with patch("subprocess.run"):
        out = get_git_provenance(tmp_path)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_signature_batch42():
    sig = inspect.signature(get_git_provenance)
    assert list(sig.parameters.keys()) == ["project_root"]


def test_get_git_provenance_return_annotation_dict_batch42():
    sig = inspect.signature(get_git_provenance)
    assert "dict" in str(sig.return_annotation)


# ---------- get_dependency_versions 第四十二批


def test_get_dependency_versions_returns_dict_batch42():
    with patch("importlib.metadata.version", return_value="1.0.0"):
        out = get_dependency_versions()
    assert isinstance(out, dict)


def test_get_dependency_versions_three_packages_batch42():
    with patch("importlib.metadata.version", return_value="1.0.0"):
        out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_package_not_found_batch42():
    """importlib.metadata.PackageNotFoundError → None。"""
    import importlib.metadata
    with patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError):
        out = get_dependency_versions()
    assert out["pdfplumber"] is None
    assert out["python-docx"] is None
    assert out["pypdfium2"] is None


def test_get_dependency_versions_generic_exception_batch42():
    """其他 Exception → None。"""
    with patch("importlib.metadata.version", side_effect=RuntimeError("boom")):
        out = get_dependency_versions()
    assert out["pdfplumber"] is None
    assert out["python-docx"] is None
    assert out["pypdfium2"] is None


def test_get_dependency_versions_mixed_batch42():
    """部分包存在，部分不存在。"""
    import importlib.metadata

    def fake_version(name: str) -> str:
        if name == "pdfplumber":
            return "0.11.0"
        raise importlib.metadata.PackageNotFoundError(name)

    with patch("importlib.metadata.version", side_effect=fake_version):
        out = get_dependency_versions()
    assert out["pdfplumber"] == "0.11.0"
    assert out["python-docx"] is None
    assert out["pypdfium2"] is None


def test_get_dependency_versions_signature_batch42():
    sig = inspect.signature(get_dependency_versions)
    assert list(sig.parameters.keys()) == []


def test_get_dependency_versions_return_annotation_dict_batch42():
    sig = inspect.signature(get_dependency_versions)
    assert "dict" in str(sig.return_annotation)


# ---------- build_provenance 第四十二批


def test_build_provenance_field_types_batch42(tmp_path):
    with patch("subprocess.run"):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert isinstance(out, dict)
    assert isinstance(out["git_commit"], (str, type(None)))
    assert isinstance(out["git_dirty"], bool)
    assert isinstance(out["evaluator_version"], str)
    assert isinstance(out["report_version"], str)
    assert isinstance(out["parser_name"], str)
    assert isinstance(out["max_chars"], int)
    assert isinstance(out["run_timestamp_iso"], str)
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_keys_batch42(tmp_path):
    with patch("subprocess.run"):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert set(out.keys()) == {
        "git_commit", "git_dirty",
        "evaluator_version", "report_version",
        "parser_name", "parser_version",
        "dependencies", "max_chars",
        "run_timestamp_iso",
    }


def test_build_provenance_evaluator_version_matches_const_batch42(tmp_path):
    with patch("subprocess.run"):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_max_chars_string_to_int_batch42(tmp_path):
    """max_chars 传入字符串会被 int() 转。"""
    with patch("subprocess.run"):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            out = build_provenance(tmp_path, "fallback", "800", "0.1.0")
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_negative_batch42(tmp_path):
    """负值也接受（int 强制转换）。"""
    with patch("subprocess.run"):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            out = build_provenance(tmp_path, "fallback", -1, None)
    assert out["max_chars"] == -1


def test_build_provenance_parser_version_none_batch42(tmp_path):
    with patch("subprocess.run"):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_run_timestamp_iso_format_batch42(tmp_path):
    """timestamp ISO 8601 含 'T'。"""
    with patch("subprocess.run"):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            out = build_provenance(tmp_path, "fallback", 800, None)
    ts = out["run_timestamp_iso"]
    assert "T" in ts


def test_build_provenance_run_timestamp_parseable_batch42(tmp_path):
    """能被 datetime.fromisoformat 解析。"""
    with patch("subprocess.run"):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            out = build_provenance(tmp_path, "fallback", 800, None)
    ts = out["run_timestamp_iso"]
    parsed = datetime.fromisoformat(ts)
    assert isinstance(parsed, datetime)


def test_build_provenance_signature_batch42():
    sig = inspect.signature(build_provenance)
    assert list(sig.parameters.keys()) == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_build_provenance_no_default_for_project_root_batch42():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["project_root"].default is inspect.Parameter.empty


def test_build_provenance_no_default_for_parser_name_batch42():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["parser_name"].default is inspect.Parameter.empty


def test_build_provenance_no_default_for_max_chars_batch42():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["max_chars"].default is inspect.Parameter.empty


def test_build_provenance_no_default_for_parser_version_batch42():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["parser_version"].default is inspect.Parameter.empty


# ---------- build_devset_section 第四十二批


def _make_fake_manifest(**overrides: Any) -> MagicMock:
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 5
    m.content_group_count = 3
    m.pdf_count = 2
    m.docx_count = 3
    m.categories_covered = ["tutorial", "advanced"]
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


def test_build_devset_section_returns_dict_batch42():
    m = _make_fake_manifest()
    out = build_devset_section(m)
    assert isinstance(out, dict)


def test_build_devset_section_keys_batch42():
    m = _make_fake_manifest()
    out = build_devset_section(m)
    assert set(out.keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_build_devset_section_passes_status_batch42():
    m = _make_fake_manifest(devset_status="complete")
    out = build_devset_section(m)
    assert out["status"] == "complete"


def test_build_devset_section_passes_file_count_batch42():
    m = _make_fake_manifest(file_count=42)
    out = build_devset_section(m)
    assert out["file_count"] == 42


def test_build_devset_section_passes_pdf_count_batch42():
    m = _make_fake_manifest(pdf_count=10)
    out = build_devset_section(m)
    assert out["pdf_count"] == 10


def test_build_devset_section_passes_docx_count_batch42():
    m = _make_fake_manifest(docx_count=20)
    out = build_devset_section(m)
    assert out["docx_count"] == 20


def test_build_devset_section_passes_content_group_count_batch42():
    m = _make_fake_manifest(content_group_count=7)
    out = build_devset_section(m)
    assert out["content_group_count"] == 7


def test_build_devset_section_passes_categories_covered_batch42():
    m = _make_fake_manifest(categories_covered=["a", "b"])
    out = build_devset_section(m)
    assert out["categories_covered"] == ["a", "b"]


def test_build_devset_section_signature_batch42():
    sig = inspect.signature(build_devset_section)
    assert list(sig.parameters.keys()) == ["manifest"]


def test_build_devset_section_return_annotation_dict_batch42():
    sig = inspect.signature(build_devset_section)
    assert "dict" in str(sig.return_annotation)


# ---------- aggregate_summary counts 第四十二批


def test_aggregate_summary_counts_empty_batch42():
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"] == {"sum": None, "participating_docs": 0}


def test_aggregate_summary_counts_all_none_batch42():
    per_doc = [
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"] == {"sum": None, "participating_docs": 0}


def test_aggregate_summary_counts_zero_value_participates_batch42():
    """value=0 不是 None，参与求和。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 0}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 0
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_counts_missing_field_batch42():
    """per_doc 缺 element_count_total → 视作不参与。"""
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"] == {"sum": None, "participating_docs": 0}


def test_aggregate_summary_counts_sum_correctness_batch42():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": 20}}},
        {"metrics": {"element_count_total": {"value": 30}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 60
    assert out["counts"]["element_count_total"]["participating_docs"] == 3


def test_aggregate_summary_counts_partial_participation_batch42():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": 30}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 40
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


# ---------- aggregate_summary success_rates 第四十二批


def test_aggregate_summary_success_rates_all_true_batch42():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 2
    assert sr["rate"] == 1.0


def test_aggregate_summary_success_rates_all_false_batch42():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["rate"] == 0.0


def test_aggregate_summary_success_rates_empty_batch42():
    out = aggregate_summary([])
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 0
    assert sr["rate"] is None


def test_aggregate_summary_success_rates_missing_field_batch42():
    """per_doc 缺 pipeline_success → success_count=0, total=1。"""
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 1
    assert sr["rate"] == 0.0


def test_aggregate_summary_success_rates_none_value_batch42():
    """value=None 不算 success。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0


# ---------- aggregate_summary ratio_macro_averages 第四十二批


def test_aggregate_summary_ratio_empty_batch42():
    out = aggregate_summary([])
    for name in _RATIO_METRICS:
        rma = out["ratio_macro_averages"][name]
        assert rma["macro_average"] is None
        assert rma["participating_docs"] == 0
        assert rma["not_evaluated"] == 0


def test_aggregate_summary_ratio_all_none_batch42():
    per_doc = [
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["schema_valid"]
    assert rma["macro_average"] is None
    assert rma["participating_docs"] == 0
    assert rma["not_evaluated"] == 2


def test_aggregate_summary_ratio_zero_participates_batch42():
    """value=0.0 不是 None → 参与。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.0}}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["schema_valid"]
    assert rma["macro_average"] == 0.0
    assert rma["participating_docs"] == 1
    assert rma["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_correctness_batch42():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.0}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["schema_valid"]
    assert rma["macro_average"] == 0.5
    assert rma["participating_docs"] == 3


def test_aggregate_summary_ratio_all_metrics_present_batch42():
    """所有 _RATIO_METRICS 都有对应 entry。"""
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    for name in _RATIO_METRICS:
        assert name in out["ratio_macro_averages"]


# ---------- aggregate_summary silent_drop_total 第四十二批


def test_aggregate_summary_silent_drop_empty_batch42():
    out = aggregate_summary([])
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_all_none_batch42():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_zero_participates_batch42():
    """value=0 不是 None → 参与。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 0}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 0


def test_aggregate_summary_silent_drop_sum_correctness_batch42():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 5}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": 7}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 12


def test_aggregate_summary_silent_drop_missing_field_batch42():
    """per_doc 缺 silent_drop_count → 不参与。"""
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


# ---------- aggregate_summary 结构 / 幂等 第四十二批


def test_aggregate_summary_returns_dict_batch42():
    out = aggregate_summary([])
    assert isinstance(out, dict)


def test_aggregate_summary_top_level_keys_batch42():
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_idempotent_batch42():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out1 = aggregate_summary(per_doc)
    out2 = aggregate_summary(per_doc)
    assert json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True)


def test_aggregate_summary_signature_batch42():
    sig = inspect.signature(aggregate_summary)
    assert list(sig.parameters.keys()) == ["per_doc_results"]


def test_aggregate_summary_return_annotation_dict_batch42():
    sig = inspect.signature(aggregate_summary)
    assert "dict" in str(sig.return_annotation)


# ---------- module source 字符串精确 第四十二批


def test_module_source_contains_docstring_batch42():
    src = inspect.getsource(rmod)
    assert '"""' in src


def test_module_source_contains_future_annotations_batch42():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_subprocess_import_batch42():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_contains_datetime_import_batch42():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_contains_pathlib_path_import_batch42():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch42():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_contains_evaluator_version_import_batch42():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_contains_ratio_metrics_definition_batch42():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS = " in src


def test_module_source_contains_count_metrics_definition_batch42():
    src = inspect.getsource(rmod)
    assert "_COUNT_METRICS = " in src


def test_module_source_contains_success_bool_metrics_definition_batch42():
    src = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS = " in src


def test_module_source_contains_get_git_provenance_batch42():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src


def test_module_source_contains_get_dependency_versions_batch42():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions(" in src


def test_module_source_contains_build_provenance_batch42():
    src = inspect.getsource(rmod)
    assert "def build_provenance(" in src


def test_module_source_contains_build_devset_section_batch42():
    src = inspect.getsource(rmod)
    assert "def build_devset_section(" in src


def test_module_source_contains_aggregate_summary_batch42():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary(" in src


def test_module_source_contains_rev_parse_call_batch42():
    src = inspect.getsource(rmod)
    assert "rev-parse" in src or '"rev-parse"' in src


def test_module_source_contains_status_porcelain_call_batch42():
    src = inspect.getsource(rmod)
    assert "status" in src and "porcelain" in src


def test_module_source_contains_capture_output_batch42():
    src = inspect.getsource(rmod)
    assert "capture_output=True" in src


def test_module_source_contains_encoding_utf8_batch42():
    src = inspect.getsource(rmod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_errors_replace_batch42():
    src = inspect.getsource(rmod)
    assert 'errors="replace"' in src


def test_module_source_contains_timeout_batch42():
    src = inspect.getsource(rmod)
    assert "timeout=10" in src


def test_module_source_contains_importlib_metadata_batch42():
    src = inspect.getsource(rmod)
    assert "importlib.metadata" in src


def test_module_source_contains_three_packages_batch42():
    src = inspect.getsource(rmod)
    assert "pdfplumber" in src
    assert "python-docx" in src
    assert "pypdfium2" in src


def test_module_source_contains_iso_format_call_batch42():
    src = inspect.getsource(rmod)
    assert "isoformat()" in src


def test_module_source_contains_astimezone_batch42():
    src = inspect.getsource(rmod)
    assert "astimezone" in src


def test_module_source_contains_no_mixing_warning_batch42():
    src = inspect.getsource(rmod)
    assert "不混合" in src or "不混" in src


def test_module_source_contains_macro_average_keyword_batch42():
    src = inspect.getsource(rmod)
    assert "macro_average" in src


def test_module_source_contains_participating_docs_keyword_batch42():
    src = inspect.getsource(rmod)
    assert "participating_docs" in src


def test_module_source_contains_not_evaluated_keyword_batch42():
    src = inspect.getsource(rmod)
    assert "not_evaluated" in src


def test_module_source_contains_all_definition_batch42():
    src = inspect.getsource(rmod)
    assert "__all__" in src


# ---------- AST 结构 第四十二批


def test_ast_top_level_no_class_no_loop_no_with_batch42():
    """顶层无 class/for/while/with/try。"""
    src = inspect.getsource(rmod)
    tree = ast.parse(src)
    for node in tree.body:
        assert not isinstance(node, (ast.ClassDef, ast.For, ast.While, ast.With, ast.Try))


def test_ast_has_five_functions_batch42():
    src = inspect.getsource(rmod)
    tree = ast.parse(src)
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert "get_git_provenance" in funcs
    assert "get_dependency_versions" in funcs
    assert "build_provenance" in funcs
    assert "build_devset_section" in funcs
    assert "aggregate_summary" in funcs


def test_ast_no_async_functions_batch42():
    src = inspect.getsource(rmod)
    tree = ast.parse(src)
    async_funcs = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)]
    assert async_funcs == []


def test_ast_top_level_only_allowed_kinds_batch42():
    """顶层节点只允许：Expr / Import / ImportFrom / FunctionDef / Assign。"""
    src = inspect.getsource(rmod)
    tree = ast.parse(src)
    for node in tree.body:
        assert isinstance(node, (ast.Expr, ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign))


def test_ast_has_module_docstring_batch42():
    src = inspect.getsource(rmod)
    tree = ast.parse(src)
    assert len(tree.body) > 0
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)
    assert isinstance(first.value.value, str)


# ---------- module 合理性 第四十二批


def test_module_has_all_attribute_batch42():
    assert hasattr(rmod, "__all__")


def test_module_all_is_list_batch42():
    assert isinstance(rmod.__all__, list)


def test_module_all_five_entries_batch42():
    assert len(rmod.__all__) == 5


def test_module_all_contains_build_provenance_batch42():
    assert "build_provenance" in rmod.__all__


def test_module_all_contains_build_devset_section_batch42():
    assert "build_devset_section" in rmod.__all__


def test_module_all_contains_aggregate_summary_batch42():
    assert "aggregate_summary" in rmod.__all__


def test_module_all_contains_get_git_provenance_batch42():
    assert "get_git_provenance" in rmod.__all__


def test_module_all_contains_get_dependency_versions_batch42():
    assert "get_dependency_versions" in rmod.__all__


def test_module_does_not_export_private_batch42():
    """私有常量/函数不出现在 __all__。"""
    for name in ["_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"]:
        assert name not in rmod.__all__


def test_module_all_contains_only_strings_batch42():
    for name in rmod.__all__:
        assert isinstance(name, str)


def test_module_all_no_duplicates_batch42():
    assert len(rmod.__all__) == len(set(rmod.__all__))


def test_module_has_get_git_provenance_attr_batch42():
    assert hasattr(rmod, "get_git_provenance")


def test_module_has_get_dependency_versions_attr_batch42():
    assert hasattr(rmod, "get_dependency_versions")


def test_module_has_build_provenance_attr_batch42():
    assert hasattr(rmod, "build_provenance")


def test_module_has_build_devset_section_attr_batch42():
    assert hasattr(rmod, "build_devset_section")


def test_module_has_aggregate_summary_attr_batch42():
    assert hasattr(rmod, "aggregate_summary")


def test_module_has_ratio_metrics_attr_batch42():
    assert hasattr(rmod, "_RATIO_METRICS")


def test_module_has_count_metrics_attr_batch42():
    assert hasattr(rmod, "_COUNT_METRICS")


def test_module_has_success_bool_metrics_attr_batch42():
    assert hasattr(rmod, "_SUCCESS_BOOL_METRICS")


def test_module_functions_callable_batch42():
    assert callable(rmod.get_git_provenance)
    assert callable(rmod.get_dependency_versions)
    assert callable(rmod.build_provenance)
    assert callable(rmod.build_devset_section)
    assert callable(rmod.aggregate_summary)


# ---------- 端到端集成 第四十二批


def test_e2e_aggregate_full_pipeline_batch42():
    """完整 per_doc 包含所有指标类型。"""
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "schema_valid": {"value": 1.0},
                "element_count_total": {"value": 10},
                "pdf_locator_valid_ratio": {"value": 1.0},
                "silent_drop_count": {"value": 0},
            },
        },
        {
            "metrics": {
                "pipeline_success": {"value": False},
                "schema_valid": {"value": 0.0},
                "element_count_total": {"value": 5},
                "pdf_locator_valid_ratio": {"value": None, "reason": "not_pdf"},
                "silent_drop_count": {"value": 2},
            },
        },
    ]
    out = aggregate_summary(per_doc)
    # counts
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["counts"]["element_count_total"]["participating_docs"] == 2
    # success_rates
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["total"] == 2
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5
    # ratio_macro_averages
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 1.0
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["not_evaluated"] == 1
    # silent_drop
    assert out["silent_drop_total"] == 2


def test_e2e_build_provenance_full_round_trip_batch42(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n"),
            MagicMock(returncode=0, stdout=""),
        ]
        with patch("importlib.metadata.version", return_value="1.0.0"):
            out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is False
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] == "0.1.0"


def test_e2e_aggregate_empty_input_batch42():
    """空 per_doc 也能聚合（全部 None）。"""
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["success_rates"]["pipeline_success"]["rate"] is None
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] is None
    assert out["silent_drop_total"] is None


# ---------- module source forbidden tokens 第七十七批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch42(token):
    src = inspect.getsource(rmod)
    assert token not in src
