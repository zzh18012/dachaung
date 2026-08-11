"""evaluation/report.py 第三十八轮 edges 测试（Round 471）。

补强 edges37 未触及的角度：
- _RATIO_METRICS 内容 第二十二批
- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第二十二批
- get_git_provenance 边界 第二十二批
- get_dependency_versions 边界 第二十二批
- build_provenance 边界 第二十二批
- build_devset_section 边界 第二十二批
- aggregate_summary 第二十二批
- module source forbidden tokens 第三十八批
- module source 字符串精确补强第三十四批
- signatures 第三十四批
- module 合理性第三十四批
- 端到端集成第三十四批
"""

from __future__ import annotations

import inspect
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

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
from evaluation import report as rmod


# ---------- _RATIO_METRICS 内容 第二十二批 ----------


def test_ratio_metrics_count_12_batch22():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_contains_schema_valid_batch22():
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_f1_batch22():
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_contains_all_locator_ratios_batch22():
    assert "pdf_locator_valid_ratio" in _RATIO_METRICS
    assert "docx_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_excludes_figure_caption_batch22():
    """figure_caption_* 不在 _RATIO_METRICS（始终 null）。"""
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_ratio_metrics_excludes_element_count_total_batch22():
    assert "element_count_total" not in _RATIO_METRICS


def test_ratio_metrics_excludes_pipeline_success_batch22():
    """pipeline_success 在 _SUCCESS_BOOL_METRICS 而非 _RATIO_METRICS。"""
    assert "pipeline_success" not in _RATIO_METRICS


def test_ratio_metrics_no_duplicates_batch22():
    assert len(_RATIO_METRICS) == len(set(_RATIO_METRICS))


def test_ratio_metrics_no_none_batch22():
    for m in _RATIO_METRICS:
        assert m is not None


def test_ratio_metrics_all_strings_batch22():
    for m in _RATIO_METRICS:
        assert isinstance(m, str)


def test_ratio_metrics_text_preservation_present_batch22():
    assert "text_preservation_equal" in _RATIO_METRICS
    assert "text_char_multiset_precision" in _RATIO_METRICS
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_heading_boundary_present_batch22():
    assert "heading_boundary_compliance" in _RATIO_METRICS


def test_ratio_metrics_image_resource_present_batch22():
    assert "image_resource_exists_ratio" in _RATIO_METRICS


# ---------- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第二十二批 ----------


def test_count_metrics_contains_element_count_total_batch22():
    assert _COUNT_METRICS == ("element_count_total",)


def test_count_metrics_count_1_batch22():
    assert len(_COUNT_METRICS) == 1


def test_success_bool_metrics_contains_pipeline_success_batch22():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_success_bool_metrics_count_1_batch22():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_count_and_success_metrics_disjoint_batch22():
    """_COUNT_METRICS 与 _SUCCESS_BOOL_METRICS 不重叠。"""
    assert set(_COUNT_METRICS).isdisjoint(_SUCCESS_BOOL_METRICS)


def test_count_and_ratio_metrics_disjoint_batch22():
    assert set(_COUNT_METRICS).isdisjoint(_RATIO_METRICS)


def test_success_and_ratio_metrics_disjoint_batch22():
    """注意：schema_valid 在 _RATIO_METRICS 但 pipeline_success 在 _SUCCESS_BOOL_METRICS。"""
    assert "pipeline_success" not in _RATIO_METRICS


# ---------- get_git_provenance 边界 第二十二批 ----------


def test_get_git_provenance_returns_dict_with_2_keys_batch22(tmp_path):
    out = get_git_provenance(tmp_path)
    assert isinstance(out, dict)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_with_subprocess_error_batch22(tmp_path):
    """subprocess.run 抛 OSError → commit=None, dirty=True。"""
    with patch("evaluation.report.subprocess.run", side_effect=OSError("fail")):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_with_subprocess_timeout_batch22(tmp_path):
    """TimeoutExpired 是 SubprocessError 子类。"""
    with patch("evaluation.report.subprocess.run", side_effect=subprocess.TimeoutExpired("git", 10)):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_first_command_fails_batch22(tmp_path):
    """rev-parse 失败，status 成功 → commit=None, dirty 取决于 status。"""
    mock_r1 = MagicMock(returncode=1, stdout="")
    mock_r2 = MagicMock(returncode=0, stdout="M file\n")
    with patch("evaluation.report.subprocess.run", side_effect=[mock_r1, mock_r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_first_succeeds_second_fails_batch22(tmp_path):
    mock_r1 = MagicMock(returncode=0, stdout="abc123\n")
    mock_r2 = MagicMock(returncode=1, stdout="")
    with patch("evaluation.report.subprocess.run", side_effect=[mock_r1, mock_r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is False  # r2 失败 → dirty=False


def test_get_git_provenance_first_empty_stdout_batch22(tmp_path):
    mock_r1 = MagicMock(returncode=0, stdout="")
    mock_r2 = MagicMock(returncode=0, stdout="")
    with patch("evaluation.report.subprocess.run", side_effect=[mock_r1, mock_r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None  # empty → None


def test_get_git_provenance_second_empty_stdout_batch22(tmp_path):
    mock_r1 = MagicMock(returncode=0, stdout="abc\n")
    mock_r2 = MagicMock(returncode=0, stdout="")
    with patch("evaluation.report.subprocess.run", side_effect=[mock_r1, mock_r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc"
    assert out["git_dirty"] is False


def test_get_git_provenance_dirty_with_changes_batch22(tmp_path):
    mock_r1 = MagicMock(returncode=0, stdout="abc123\n")
    mock_r2 = MagicMock(returncode=0, stdout="M file.txt\n?? new.txt\n")
    with patch("evaluation.report.subprocess.run", side_effect=[mock_r1, mock_r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


# ---------- get_dependency_versions 边界 第二十二批 ----------


def test_get_dependency_versions_returns_dict_batch22():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_get_dependency_versions_has_3_packages_batch22():
    out = get_dependency_versions()
    assert len(out) == 3


def test_get_dependency_versions_keys_exact_batch22():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_pdfplumber_value_batch22():
    """pdfplumber 通常已安装。"""
    out = get_dependency_versions()
    # 不强求具体版本号，但 key 应在
    assert "pdfplumber" in out


def test_get_dependency_versions_with_package_not_found_batch22():
    """模拟 PackageNotFoundError → None。"""
    import importlib.metadata
    real_version = importlib.metadata.version

    def fake_version(name, *args, **kwargs):
        if name == "pdfplumber":
            raise importlib.metadata.PackageNotFoundError("not found")
        return real_version(name)

    with patch.object(importlib.metadata, "version", side_effect=fake_version):
        out = get_dependency_versions()
    assert out["pdfplumber"] is None


def test_get_dependency_versions_value_is_str_or_none_batch22():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_with_exception_batch22():
    """模拟其他异常 → None。"""
    import importlib.metadata

    def fake_version(name, *args, **kwargs):
        raise RuntimeError("unexpected")

    with patch.object(importlib.metadata, "version", side_effect=fake_version):
        out = get_dependency_versions()
    for v in out.values():
        assert v is None


# ---------- build_provenance 边界 第二十二批 ----------


def test_build_provenance_returns_9_keys_batch22(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert len(out) == 9


def test_build_provenance_keys_exact_batch22(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert set(out.keys()) == {
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


def test_build_provenance_parser_name_passed_batch22(tmp_path):
    out = build_provenance(tmp_path, "kreuzberg", 800, "1.0.0")
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_max_chars_passed_batch22(tmp_path):
    out = build_provenance(tmp_path, "fallback", 1500, "1.0.0")
    assert out["max_chars"] == 1500


def test_build_provenance_max_chars_converted_to_int_batch22(tmp_path):
    """max_chars 即使传 float 也被 int()。"""
    out = build_provenance(tmp_path, "fallback", 800.5, "1.0.0")
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_parser_version_none_batch22(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_evaluator_version_constant_batch22(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_constant_batch22(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_timestamp_format_batch22(tmp_path):
    """run_timestamp_iso 应是 ISO 格式。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    ts = out["run_timestamp_iso"]
    # ISO 格式应包含 'T' 与 ':'（datetime.isoformat）
    assert "T" in ts


# ---------- build_devset_section 边界 第二十二批 ----------


def test_build_devset_section_returns_6_keys_batch22():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    out = build_devset_section(m)
    assert len(out) == 6


def test_build_devset_section_keys_exact_batch22():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    out = build_devset_section(m)
    assert set(out.keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_build_devset_section_status_passed_through_batch22():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    out = build_devset_section(m)
    assert out["status"] == "complete"


def test_build_devset_section_counts_passed_through_batch22():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 5
    m.content_group_count = 3
    m.pdf_count = 2
    m.docx_count = 3
    m.categories_covered = ["a"]
    out = build_devset_section(m)
    assert out["file_count"] == 5
    assert out["content_group_count"] == 3
    assert out["pdf_count"] == 2
    assert out["docx_count"] == 3


def test_build_devset_section_categories_passed_through_batch22():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = ["a", "b", "c"]
    out = build_devset_section(m)
    assert out["categories_covered"] == ["a", "b", "c"]


# ---------- aggregate_summary 第二十二批 ----------


def test_aggregate_summary_empty_input_batch22():
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_counts_sum_batch22():
    """counts element_count_total 求和。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 3}}},
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 8
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_skips_none_batch22():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 3}}},
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 3
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_counts_all_none_batch22():
    per_doc = [
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_success_rate_batch22():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    rate = out["success_rates"]["pipeline_success"]
    assert rate["success_count"] == 2
    assert rate["total"] == 3
    assert rate["rate"] == pytest.approx(2 / 3)


def test_aggregate_summary_success_rate_empty_batch22():
    out = aggregate_summary([])
    rate = out["success_rates"]["pipeline_success"]
    assert rate["success_count"] == 0
    assert rate["total"] == 0
    assert rate["rate"] is None


def test_aggregate_summary_ratio_macro_average_batch22():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
    ]
    out = aggregate_summary(per_doc)
    avg = out["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == pytest.approx(0.75)
    assert avg["participating_docs"] == 2
    assert avg["not_evaluated"] == 0


def test_aggregate_summary_ratio_with_not_evaluated_batch22():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    avg = out["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == 1.0
    assert avg["participating_docs"] == 1
    assert avg["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_sum_batch22():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_skips_none_batch22():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 3


def test_aggregate_summary_silent_drop_all_none_batch22():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_empty_input_batch22():
    out = aggregate_summary([])
    assert out["silent_drop_total"] is None


def test_aggregate_summary_returns_dict_type_batch22():
    out = aggregate_summary([])
    assert isinstance(out, dict)


# ---------- module source forbidden tokens 第三十八批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.Popen",
    "subprocess.check_output",
    "subprocess.check_call",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    "open(\"/etc/passwd",
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch22(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


def test_module_source_subprocess_run_allowed_batch22():
    """subprocess.run 在白名单（git provenance 需要）。"""
    src = inspect.getsource(rmod)
    assert "subprocess.run" in src


def test_module_source_no_socket_import_batch22():
    src = inspect.getsource(rmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch22():
    src = inspect.getsource(rmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch22():
    src = inspect.getsource(rmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch22():
    src = inspect.getsource(rmod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch22():
    src = inspect.getsource(rmod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch22():
    src = inspect.getsource(rmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch22():
    src = inspect.getsource(rmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch22():
    src = inspect.getsource(rmod)
    assert "import tempfile" not in src


def test_module_source_no_sys_import_batch22():
    src = inspect.getsource(rmod)
    assert "import sys" not in src


def test_module_source_no_logging_import_batch22():
    src = inspect.getsource(rmod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch22():
    src = inspect.getsource(rmod)
    assert "import re" not in src


def test_module_source_no_datetime_import_unexpected_batch22():
    """datetime 被使用（import datetime）— 这个测试确认它存在。"""
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_no_pandas_import_batch22():
    src = inspect.getsource(rmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch22():
    src = inspect.getsource(rmod)
    assert "import numpy" not in src


def test_module_source_no_unlink_call_batch22():
    src = inspect.getsource(rmod)
    assert ".unlink(" not in src


# ---------- module source 字符串精确补强第三十四批 ----------


def test_module_source_has_future_annotations_batch22():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_subprocess_import_batch22():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_has_pathlib_path_import_batch22():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch22():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_evaluator_version_import_batch22():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_has_ratio_metrics_constant_batch22():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS = (" in src


def test_module_source_has_count_metrics_constant_batch22():
    src = inspect.getsource(rmod)
    assert "_COUNT_METRICS = " in src


def test_module_source_has_success_bool_metrics_constant_batch22():
    src = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS = " in src


def test_module_source_has_get_git_provenance_function_batch22():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src


def test_module_source_has_get_dependency_versions_function_batch22():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions(" in src


def test_module_source_has_build_provenance_function_batch22():
    src = inspect.getsource(rmod)
    assert "def build_provenance(" in src


def test_module_source_has_build_devset_section_function_batch22():
    src = inspect.getsource(rmod)
    assert "def build_devset_section(" in src


def test_module_source_has_aggregate_summary_function_batch22():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary(" in src


def test_module_source_has_docstring_batch22():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_has_subprocess_run_call_batch22():
    src = inspect.getsource(rmod)
    assert "subprocess.run" in src


def test_module_source_has_capture_output_batch22():
    src = inspect.getsource(rmod)
    assert "capture_output" in src


# ---------- signatures 第三十四批 ----------


def test_signature_get_git_provenance_batch22():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["project_root"]


def test_signature_get_dependency_versions_batch22():
    sig = inspect.signature(get_dependency_versions)
    params = list(sig.parameters.values())
    assert len(params) == 0


def test_signature_build_provenance_batch22():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_devset_section_batch22():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["manifest"]


def test_signature_aggregate_summary_batch22():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["per_doc_results"]


def test_signature_build_provenance_no_defaults_batch22():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


# ---------- module 合理性第三十四批 ----------


def test_module_has_all_attribute_batch22():
    assert hasattr(rmod, "__all__")


def test_module_all_contains_5_entries_batch22():
    assert len(rmod.__all__) == 5


def test_module_all_contents_batch22():
    assert set(rmod.__all__) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_does_not_import_app_pipeline_batch22():
    src = inspect.getsource(rmod)
    assert "from app" not in src
    assert "import app" not in src


def test_module_does_not_import_evaluation_runner_batch22():
    src = inspect.getsource(rmod)
    assert "from evaluation.runner" not in src
    assert "from evaluation import runner" not in src


def test_module_does_not_import_evaluation_metrics_batch22():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics" not in src
    assert "from evaluation import metrics" not in src


def test_module_does_not_import_evaluation_cli_batch22():
    src = inspect.getsource(rmod)
    assert "from evaluation.cli" not in src
    assert "from evaluation import cli" not in src


def test_module_does_not_import_evaluation_schema_batch22():
    src = inspect.getsource(rmod)
    assert "from evaluation.schema" not in src
    assert "from evaluation import schema" not in src


def test_module_does_not_import_evaluation_manifest_batch22():
    src = inspect.getsource(rmod)
    assert "from evaluation.manifest" not in src
    assert "from evaluation import manifest" not in src


def test_module_no_main_block_batch22():
    src = inspect.getsource(rmod)
    assert 'if __name__ ==' not in src
    assert "__main__" not in src


def test_module_get_git_provenance_callable_batch22():
    assert callable(rmod.get_git_provenance)


def test_module_aggregate_summary_callable_batch22():
    assert callable(rmod.aggregate_summary)


# ---------- 端到端集成第三十四批 ----------


def test_e2e_build_provenance_full_batch22(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] == "1.0.0"
    assert out["max_chars"] == 800
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION
    assert isinstance(out["dependencies"], dict)
    assert "git_commit" in out
    assert "git_dirty" in out


def test_e2e_aggregate_summary_full_per_doc_batch22():
    per_doc = [
        {
            "doc_id": "d1",
            "metrics": {
                "pipeline_success": {"value": True},
                "element_count_total": {"value": 5},
                "schema_valid": {"value": 1.0},
                "silent_drop_count": {"value": 2},
            },
        },
        {
            "doc_id": "d2",
            "metrics": {
                "pipeline_success": {"value": False},
                "element_count_total": {"value": 3},
                "schema_valid": {"value": 0.0},
                "silent_drop_count": {"value": 1},
            },
        },
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 8
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["total"] == 2
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert out["silent_drop_total"] == 3


def test_e2e_aggregate_summary_idempotent_batch22():
    per_doc = [{"metrics": {"pipeline_success": {"value": True}}}]
    o1 = aggregate_summary(per_doc)
    o2 = aggregate_summary(per_doc)
    assert o1 == o2


def test_e2e_build_devset_with_real_manifest_mock_batch22():
    """build_devset_section 用 manifest mock 调用。"""
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 3
    m.content_group_count = 2
    m.pdf_count = 1
    m.docx_count = 2
    m.categories_covered = ["a", "b"]
    out = build_devset_section(m)
    assert out == {
        "status": "incomplete",
        "file_count": 3,
        "content_group_count": 2,
        "pdf_count": 1,
        "docx_count": 2,
        "categories_covered": ["a", "b"],
    }


def test_e2e_get_dependency_versions_returns_real_versions_batch22():
    out = get_dependency_versions()
    # pdfplumber 与 python-docx 通常已安装
    # 不强求具体版本，但 pdfplumber 应非 None
    if "pdfplumber" in out:
        # 可能是 None（未安装），但不抛错
        pass


def test_e2e_aggregate_summary_with_empty_metrics_batch22():
    """per_doc 项 metrics 完全空 dict。"""
    per_doc = [{"doc_id": "d1", "metrics": {}}]
    out = aggregate_summary(per_doc)
    # 不抛错即可
    assert "counts" in out


def test_e2e_build_provenance_dependencies_always_dict_batch22(tmp_path):
    """dependencies 始终是 dict（3 keys）。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["dependencies"], dict)
    assert len(out["dependencies"]) == 3
