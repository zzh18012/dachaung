"""evaluation/report.py 第三十七轮 edges 测试（Round 464）。

补强 edges36 未触及的角度。
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


# ---------- _RATIO_METRICS 内容深度第二十一批 ----------


def test_ratio_metrics_has_chunk_boundary_precision_batch21():
    assert "chunk_boundary_precision" in _RATIO_METRICS


def test_ratio_metrics_has_chunk_boundary_recall_batch21():
    assert "chunk_boundary_recall" in _RATIO_METRICS


def test_ratio_metrics_has_chunk_boundary_f1_batch21():
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_has_text_preservation_equal_batch21():
    assert "text_preservation_equal" in _RATIO_METRICS


def test_ratio_metrics_has_text_char_multiset_precision_batch21():
    assert "text_char_multiset_precision" in _RATIO_METRICS


def test_ratio_metrics_has_text_char_multiset_recall_batch21():
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_has_heading_boundary_compliance_batch21():
    assert "heading_boundary_compliance" in _RATIO_METRICS


def test_ratio_metrics_has_image_resource_exists_ratio_batch21():
    assert "image_resource_exists_ratio" in _RATIO_METRICS


def test_ratio_metrics_has_chunk_reference_intact_ratio_batch21():
    assert "chunk_reference_intact_ratio" in _RATIO_METRICS


def test_ratio_metrics_has_pdf_locator_valid_ratio_batch21():
    assert "pdf_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_has_docx_locator_valid_ratio_batch21():
    assert "docx_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_silent_drop_count_batch21():
    assert "silent_drop_count" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_pipeline_success_batch21():
    assert "pipeline_success" not in _RATIO_METRICS


# ---------- get_git_provenance 边界第二十一批 ----------


def test_get_git_provenance_returns_dict_keys_2_batch21(tmp_path):
    result = get_git_provenance(tmp_path)
    assert len(result) == 2


def test_get_git_provenance_keys_exact_batch21(tmp_path):
    result = get_git_provenance(tmp_path)
    assert set(result.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_git_commit_type_optional_str_batch21(tmp_path):
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None or isinstance(result["git_commit"], str)


def test_get_git_provenance_git_dirty_type_bool_batch21(tmp_path):
    result = get_git_provenance(tmp_path)
    assert isinstance(result["git_dirty"], bool)


def test_get_git_provenance_commit_short_hash_batch21(tmp_path):
    """commit 应是 40 字符 SHA-1 或 None。"""
    fake = MagicMock(returncode=0, stdout="abc123def456789012345678901234567890abcd\n", stderr="")
    with patch("subprocess.run", return_value=fake):
        result = get_git_provenance(tmp_path)
    assert len(result["git_commit"]) == 40


def test_get_git_provenance_oserror_returns_dirty_true_batch21(tmp_path):
    """OSError 触发兜底，commit=None dirty=True。"""
    with patch("subprocess.run", side_effect=OSError("simulated")):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_subprocess_error_returns_dirty_true_batch21(tmp_path):
    """subprocess.SubprocessError 触发兜底。"""
    with patch("subprocess.run", side_effect=subprocess.SubprocessError("x")):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_stdout_with_whitespace_batch21(tmp_path):
    """commit 应被 strip。"""
    fake = MagicMock(returncode=0, stdout="  commit123  \n", stderr="")
    with patch("subprocess.run", return_value=fake):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] == "commit123"


# ---------- get_dependency_versions 边界第二十一批 ----------


def test_get_dependency_versions_always_returns_3_keys_batch21():
    v = get_dependency_versions()
    assert len(v) == 3


def test_get_dependency_versions_pdfplumber_present_batch21():
    v = get_dependency_versions()
    assert "pdfplumber" in v


def test_get_dependency_versions_python_docx_present_batch21():
    v = get_dependency_versions()
    assert "python-docx" in v


def test_get_dependency_versions_pypdfium2_present_batch21():
    v = get_dependency_versions()
    assert "pypdfium2" in v


def test_get_dependency_versions_handles_all_package_not_found_batch21():
    """所有包都 PackageNotFound。"""
    with patch("importlib.metadata.version", side_effect=__import__("importlib").metadata.PackageNotFoundError):
        v = get_dependency_versions()
    assert all(val is None for val in v.values())


def test_get_dependency_versions_partial_failure_batch21():
    """部分包异常，部分正常。"""
    real_pdfplumber = None
    try:
        real_pdfplumber = __import__("importlib").metadata.version("pdfplumber")
    except Exception:
        pass

    def side(name):
        if name == "pdfplumber":
            return real_pdfplumber or "0.0.0"
        raise __import__("importlib").metadata.PackageNotFoundError(name)

    with patch("importlib.metadata.version", side_effect=side):
        v = get_dependency_versions()
    assert v["pdfplumber"] is not None
    assert v["python-docx"] is None
    assert v["pypdfium2"] is None


# ---------- build_provenance 边界第二十一批 ----------


def test_build_provenance_max_chars_float_truncated_batch21(tmp_path):
    """max_chars 是 float 时 int() 截断。"""
    p = build_provenance(tmp_path, "fallback", 800.99, None)
    assert p["max_chars"] == 800


def test_build_provenance_timestamp_iso_has_t_separator_batch21(tmp_path):
    """ISO 时间戳含 T 分隔符。"""
    p = build_provenance(tmp_path, "fallback", 800, None)
    assert "T" in p["run_timestamp_iso"]


def test_build_provenance_timestamp_has_offset_batch21(tmp_path):
    """ISO 时间戳含时区偏移（+HH:MM）。"""
    p = build_provenance(tmp_path, "fallback", 800, None)
    ts = p["run_timestamp_iso"]
    # 应有 + 或 - 表示时区偏移
    has_offset = ("+" in ts.split("T")[1]) or ("-" in ts.split("T")[1])
    assert has_offset


def test_build_provenance_parser_name_empty_string_batch21(tmp_path):
    p = build_provenance(tmp_path, "", 800, None)
    assert p["parser_name"] == ""


def test_build_provenance_dependencies_3_keys_batch21(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, None)
    assert len(p["dependencies"]) == 3


def test_build_provenance_evaluator_version_constant_value_batch21(tmp_path):
    """evaluator_version 来自 EVALUATOR_VERSION（不应硬编码）。"""
    p = build_provenance(tmp_path, "fallback", 800, None)
    assert p["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_constant_value_batch21(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, None)
    assert p["report_version"] == REPORT_VERSION


# ---------- build_devset_section 边界第二十一批 ----------


def _make_manifest_mock(**kwargs):
    m = MagicMock()
    m.devset_status = kwargs.get("devset_status", "incomplete")
    m.file_count = kwargs.get("file_count", 0)
    m.content_group_count = kwargs.get("content_group_count", 0)
    m.pdf_count = kwargs.get("pdf_count", 0)
    m.docx_count = kwargs.get("docx_count", 0)
    m.categories_covered = kwargs.get("categories_covered", [])
    return m


def test_build_devset_section_status_complete_batch21():
    out = build_devset_section(_make_manifest_mock(devset_status="complete"))
    assert out["status"] == "complete"


def test_build_devset_section_status_incomplete_batch21():
    out = build_devset_section(_make_manifest_mock(devset_status="incomplete"))
    assert out["status"] == "incomplete"


def test_build_devset_section_content_group_zero_batch21():
    out = build_devset_section(_make_manifest_mock(content_group_count=0))
    assert out["content_group_count"] == 0


def test_build_devset_section_content_group_multiple_batch21():
    out = build_devset_section(_make_manifest_mock(content_group_count=10))
    assert out["content_group_count"] == 10


def test_build_devset_section_pdf_zero_batch21():
    out = build_devset_section(_make_manifest_mock(pdf_count=0))
    assert out["pdf_count"] == 0


def test_build_devset_section_docx_zero_batch21():
    out = build_devset_section(_make_manifest_mock(docx_count=0))
    assert out["docx_count"] == 0


def test_build_devset_section_pdf_only_batch21():
    out = build_devset_section(_make_manifest_mock(pdf_count=5, docx_count=0))
    assert out["pdf_count"] == 5
    assert out["docx_count"] == 0


def test_build_devset_section_docx_only_batch21():
    out = build_devset_section(_make_manifest_mock(pdf_count=0, docx_count=3))
    assert out["pdf_count"] == 0
    assert out["docx_count"] == 3


# ---------- aggregate_summary 边界第二十一批 ----------


def test_aggregate_summary_counts_missing_metric_batch21():
    """per_doc 完全缺 element_count_total。"""
    per_doc = [{"metrics": {}}]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_counts_partial_missing_batch21():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {}},  # 完全缺 metric
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 5
    assert s["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_success_rate_with_partial_missing_batch21():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {}},
    ]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2


def test_aggregate_summary_ratio_macro_with_all_values_batch21():
    per_doc = [
        {"metrics": {"schema_valid": {"value": True}}},
        {"metrics": {"schema_valid": {"value": False}}},
    ]
    s = aggregate_summary(per_doc)
    avg = s["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == 0.5
    assert avg["participating_docs"] == 2
    assert avg["not_evaluated"] == 0


def test_aggregate_summary_silent_drop_mixed_null_and_value_batch21():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 5}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": 3}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_with_missing_metric_batch21():
    per_doc = [
        {"metrics": {}},
        {"metrics": {"silent_drop_count": {"value": 2}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 2


def test_aggregate_summary_does_not_sum_ratio_metrics_batch21():
    """ratio 类 metric 不应被 sum（counts 只含 element_count_total）。"""
    per_doc = [
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.5}}},
    ]
    s = aggregate_summary(per_doc)
    # counts 中不应有 pdf_locator_valid_ratio
    assert "pdf_locator_valid_ratio" not in s["counts"]


def test_aggregate_summary_returns_dict_batch21():
    s = aggregate_summary([])
    assert isinstance(s, dict)


def test_aggregate_summary_4_top_keys_names_batch21():
    s = aggregate_summary([])
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_counts_only_has_element_count_total_batch21():
    s = aggregate_summary([])
    assert set(s["counts"].keys()) == {"element_count_total"}


def test_aggregate_summary_success_rates_only_has_pipeline_success_batch21():
    s = aggregate_summary([])
    assert set(s["success_rates"].keys()) == {"pipeline_success"}


def test_aggregate_summary_ratio_macro_has_12_metrics_batch21():
    s = aggregate_summary([])
    assert len(s["ratio_macro_averages"]) == 12


# ---------- module source forbidden tokens 第三十五批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
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
def test_module_source_forbidden_tokens_batch21(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


def test_module_source_no_socket_import_batch21():
    src = inspect.getsource(rmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch21():
    src = inspect.getsource(rmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch21():
    src = inspect.getsource(rmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch21():
    src = inspect.getsource(rmod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch21():
    src = inspect.getsource(rmod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch21():
    src = inspect.getsource(rmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch21():
    src = inspect.getsource(rmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch21():
    src = inspect.getsource(rmod)
    assert "import tempfile" not in src


def test_module_source_no_unlink_call_batch21():
    src = inspect.getsource(rmod)
    assert ".unlink(" not in src


def test_module_source_no_path_write_text_batch21():
    src = inspect.getsource(rmod)
    assert ".write_text(" not in src


def test_module_source_no_sys_exit_batch21():
    src = inspect.getsource(rmod)
    assert "sys.exit" not in src


def test_module_source_no_re_compile_batch21():
    src = inspect.getsource(rmod)
    assert "re.compile" not in src


def test_module_source_no_pandas_import_batch21():
    src = inspect.getsource(rmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch21():
    src = inspect.getsource(rmod)
    assert "import numpy" not in src


def test_module_source_no_path_open_batch21():
    """report.py 不直接 open 文件（写盘由 runner 做）。"""
    src = inspect.getsource(rmod)
    assert "open(" not in src


def test_module_source_subprocess_allowed_batch21():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


# ---------- module source 字符串精确补强第三十一批 ----------


def test_module_source_has_future_annotations_batch21():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_subprocess_import_batch21():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_has_datetime_import_batch21():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_has_pathlib_path_import_batch21():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch21():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_evaluator_version_import_batch21():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_has_all_list_with_5_entries_batch21():
    src = inspect.getsource(rmod)
    assert '"build_provenance"' in src
    assert '"build_devset_section"' in src
    assert '"aggregate_summary"' in src
    assert '"get_git_provenance"' in src
    assert '"get_dependency_versions"' in src


def test_module_source_has_docstring_about_aggregation_batch21():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_has_capture_output_true_batch21():
    src = inspect.getsource(rmod)
    assert "capture_output=True" in src


def test_module_source_has_text_true_batch21():
    src = inspect.getsource(rmod)
    assert "text=True" in src


def test_module_source_has_errors_replace_batch21():
    src = inspect.getsource(rmod)
    assert 'errors="replace"' in src


def test_module_source_has_encoding_utf8_batch21():
    src = inspect.getsource(rmod)
    assert 'encoding="utf-8"' in src


def test_module_source_has_timeout_10_batch21():
    src = inspect.getsource(rmod)
    assert "timeout=10" in src


# ---------- signatures 第三十一批 ----------


def test_signature_get_git_provenance_batch21():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["project_root"]


def test_signature_get_dependency_versions_batch21():
    sig = inspect.signature(get_dependency_versions)
    params = list(sig.parameters.values())
    assert len(params) == 0


def test_signature_build_provenance_batch21():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_provenance_no_defaults_batch21():
    """build_provenance 所有参数都必填。"""
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.values())
    for p in params:
        assert p.default is inspect.Parameter.empty


def test_signature_build_devset_section_batch21():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.values())
    assert len(params) == 1


def test_signature_aggregate_summary_batch21():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["per_doc_results"]


# ---------- module 合理性 第三十一批 ----------


def test_module_has_all_attribute_batch21():
    assert hasattr(rmod, "__all__")


def test_module_all_count_5_batch21():
    assert len(rmod.__all__) == 5


def test_module_all_entries_are_strings_batch21():
    for n in rmod.__all__:
        assert isinstance(n, str)


def test_module_does_not_import_app_pipeline_batch21():
    src = inspect.getsource(rmod)
    assert "from app" not in src


def test_module_does_not_import_evaluation_metrics_batch21():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics" not in src


def test_module_does_not_import_evaluation_cli_batch21():
    src = inspect.getsource(rmod)
    assert "from evaluation.cli" not in src


def test_module_does_not_import_evaluation_runner_batch21():
    src = inspect.getsource(rmod)
    assert "from evaluation.runner" not in src


def test_module_does_not_import_evaluation_annotation_metrics_batch21():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics" not in src


def test_module_constants_not_in_all_batch21():
    for k in ("_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"):
        assert k not in rmod.__all__


def test_module_no_main_block_batch21():
    src = inspect.getsource(rmod)
    assert 'if __name__ ==' not in src


def test_module_evaluator_version_imported_not_defined_batch21():
    """EVALUATOR_VERSION 是 import 进来的，不是本模块定义。"""
    src = inspect.getsource(rmod)
    assert "EVALUATOR_VERSION = " not in src


# ---------- 端到端集成 第三十一批 ----------


def test_e2e_build_provenance_full_structure_batch21(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert isinstance(p["git_commit"], (str, type(None)))
    assert isinstance(p["git_dirty"], bool)
    assert isinstance(p["dependencies"], dict)
    assert isinstance(p["run_timestamp_iso"], str)
    assert isinstance(p["max_chars"], int)
    assert p["parser_version"] == "1.0.0"


def test_e2e_aggregate_summary_full_flow_batch21():
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "schema_valid": {"value": True},
                "element_count_total": {"value": 10},
                "silent_drop_count": {"value": 2},
                "pdf_locator_valid_ratio": {"value": 1.0},
            }
        },
        {
            "metrics": {
                "pipeline_success": {"value": False},
                "schema_valid": {"value": None},
                "element_count_total": {"value": None},
                "silent_drop_count": {"value": None},
                "pdf_locator_valid_ratio": {"value": 0.5},
            }
        },
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1
    assert s["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert s["counts"]["element_count_total"]["sum"] == 10
    assert s["silent_drop_total"] == 2
    avg = s["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert avg["macro_average"] == 0.75
    assert avg["participating_docs"] == 2


def test_e2e_build_devset_with_full_categories_batch21():
    m = _make_manifest_mock(
        devset_status="complete",
        file_count=10,
        pdf_count=5,
        docx_count=5,
        content_group_count=5,
        categories_covered=["pdf", "docx", "table_heavy"],
    )
    out = build_devset_section(m)
    assert out["status"] == "complete"
    assert out["categories_covered"] == ["pdf", "docx", "table_heavy"]


def test_e2e_get_git_provenance_with_mocked_full_success_batch21(tmp_path):
    fake_ok1 = MagicMock(returncode=0, stdout="abc123\n", stderr="")
    fake_ok2 = MagicMock(returncode=0, stdout="M file.txt\n", stderr="")
    with patch("subprocess.run", side_effect=[fake_ok1, fake_ok2]):
        out = get_git_provenance(tmp_path)
    assert out == {"git_commit": "abc123", "git_dirty": True}


def test_e2e_pipeline_combined_batch21(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    m = _make_manifest_mock(file_count=1)
    d = build_devset_section(m)
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "schema_valid": {"value": True},
                "element_count_total": {"value": 1},
            }
        }
    ]
    s = aggregate_summary(per_doc)
    assert p["parser_version"] == "1.0.0"
    assert d["file_count"] == 1
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1


def test_e2e_aggregate_summary_with_extra_metrics_batch21():
    """per_doc 含未声明的 metric 应被忽略。"""
    per_doc = [
        {"metrics": {"unknown_metric": {"value": 999}}},
        {"metrics": {"another_unknown": {"value": "x"}}},
    ]
    s = aggregate_summary(per_doc)
    # 4 个 top key 都不被 unknown_metric 影响
    assert "unknown_metric" not in s["counts"]
    assert "another_unknown" not in s["ratio_macro_averages"]
    assert s["success_rates"]["pipeline_success"]["success_count"] == 0


def test_e2e_get_dependency_versions_returns_3_keys_batch21():
    v = get_dependency_versions()
    assert len(v) == 3
    assert all(isinstance(k, str) for k in v.keys())
