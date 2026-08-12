"""evaluation/report.py 第五十一轮 edges 测试（Round 562）。

补强 edges50 未触及的角度（第三十二批）。
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第三十二批


def test_ratio_metrics_starts_with_schema_valid_batch32():
    """_RATIO_METRICS 第一个是 schema_valid（按定义顺序）。"""
    assert _RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_ends_with_chunk_boundary_f1_batch32():
    assert _RATIO_METRICS[-1] == "chunk_boundary_f1"


def test_ratio_metrics_pdf_locator_valid_ratio_batch32():
    assert "pdf_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_docx_locator_valid_ratio_batch32():
    assert "docx_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_image_resource_exists_ratio_batch32():
    assert "image_resource_exists_ratio" in _RATIO_METRICS


def test_ratio_metrics_chunk_reference_intact_ratio_batch32():
    assert "chunk_reference_intact_ratio" in _RATIO_METRICS


def test_ratio_metrics_text_char_multiset_precision_batch32():
    assert "text_char_multiset_precision" in _RATIO_METRICS


def test_ratio_metrics_text_char_multiset_recall_batch32():
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_heading_boundary_compliance_batch32():
    assert "heading_boundary_compliance" in _RATIO_METRICS


def test_count_metrics_first_only_batch32():
    """_COUNT_METRICS 只有 element_count_total。"""
    assert len(_COUNT_METRICS) == 1


def test_success_bool_metrics_first_only_batch32():
    """_SUCCESS_BOOL_METRICS 只有 pipeline_success。"""
    assert len(_SUCCESS_BOOL_METRICS) == 1


# ---------- get_git_provenance 第三十二批


def test_git_provenance_first_call_cwd_str_batch32(tmp_path):
    """cwd 是 str(project_root) 不是 Path。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        get_git_provenance(tmp_path)
        for call in mock_run.call_args_list:
            assert call.kwargs.get("cwd") == str(tmp_path)


def test_git_provenance_text_true_batch32(tmp_path):
    """subprocess 调用带 text=True。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        get_git_provenance(tmp_path)
        for call in mock_run.call_args_list:
            assert call.kwargs.get("text") is True


def test_git_provenance_returns_git_dirty_bool_batch32(tmp_path):
    """git_dirty 必须是 bool（不是 truthy int/string）。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        out = get_git_provenance(tmp_path)
        assert isinstance(out["git_dirty"], bool)


def test_git_provenance_returns_git_commit_str_or_none_batch32(tmp_path):
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] is None or isinstance(out["git_commit"], str)


def test_git_provenance_no_args_first_call_batch32(tmp_path):
    """subprocess.run 第一参数是 list。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        get_git_provenance(tmp_path)
        first_call = mock_run.call_args_list[0]
        args = first_call.args[0]
        assert isinstance(args, list)
        assert all(isinstance(a, str) for a in args)


def test_git_provenance_call_count_two_batch32(tmp_path):
    """每次 get_git_provenance 调用 subprocess.run 两次。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        get_git_provenance(tmp_path)
        assert mock_run.call_count == 2


# ---------- get_dependency_versions 第三十二批


def test_dependency_versions_pdfplumber_value_batch32():
    out = get_dependency_versions()
    assert "pdfplumber" in out


def test_dependency_versions_python_docx_value_batch32():
    out = get_dependency_versions()
    assert "python-docx" in out


def test_dependency_versions_pypdfium2_value_batch32():
    out = get_dependency_versions()
    assert "pypdfium2" in out


# ---------- build_provenance 第三十二批


def test_build_provenance_parser_version_string_batch32(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "v1.2.3")
    assert out["parser_version"] == "v1.2.3"


def test_build_provenance_unicode_parser_version_batch32(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "版本 1.0")
    assert out["parser_version"] == "版本 1.0"


def test_build_provenance_max_chars_int_returned_batch32(tmp_path):
    """max_chars=int 总是返回 int。"""
    out = build_provenance(tmp_path, "fallback", 1234, None)
    assert isinstance(out["max_chars"], int)
    assert out["max_chars"] == 1234


def test_build_provenance_run_timestamp_iso_parseable_batch32(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    parsed = datetime.fromisoformat(out["run_timestamp_iso"])
    assert parsed is not None


def test_build_provenance_dependencies_three_packages_batch32(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert set(out["dependencies"].keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_build_provenance_evaluator_version_value_batch32(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value_batch32(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


# ---------- build_devset_section 第三十二批


def test_build_devset_section_status_value_batch32():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    out = build_devset_section(m)
    assert out["status"] == "incomplete"


def test_build_devset_section_devset_complete_batch32():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 100
    m.content_group_count = 50
    m.pdf_count = 50
    m.docx_count = 50
    m.categories_covered = ["essay", "report", "letter"]
    out = build_devset_section(m)
    assert out["file_count"] == 100
    assert out["content_group_count"] == 50


# ---------- aggregate_summary 第三十二批


def test_aggregate_summary_three_main_sections_batch32():
    out = aggregate_summary([])
    assert "counts" in out
    assert "success_rates" in out
    assert "ratio_macro_averages" in out


def test_aggregate_summary_counts_per_metric_keys_batch32():
    out = aggregate_summary([])
    counts = out["counts"]
    assert "element_count_total" in counts
    assert counts["element_count_total"]["sum"] is None
    assert counts["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_success_rates_per_metric_keys_batch32():
    out = aggregate_summary([])
    sr = out["success_rates"]
    assert "pipeline_success" in sr
    assert sr["pipeline_success"]["success_count"] == 0
    assert sr["pipeline_success"]["total"] == 0
    assert sr["pipeline_success"]["rate"] is None


def test_aggregate_summary_ratio_macro_per_metric_keys_batch32():
    out = aggregate_summary([])
    rm = out["ratio_macro_averages"]
    for name in _RATIO_METRICS:
        assert name in rm
        assert rm[name]["macro_average"] is None
        assert rm[name]["participating_docs"] == 0
        assert rm[name]["not_evaluated"] == 0


def test_aggregate_summary_silent_drop_total_null_batch32():
    out = aggregate_summary([])
    assert out["silent_drop_total"] is None


def test_aggregate_summary_does_not_mutate_input_batch32():
    import copy
    results = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    ]
    results_before = copy.deepcopy(results)
    aggregate_summary(results)
    assert results == results_before


def test_aggregate_summary_handles_missing_metrics_key_batch32():
    """per_doc_result 缺 metrics key → KeyError（不静默吞错）。"""
    with pytest.raises(KeyError):
        aggregate_summary([{}])


# ---------- module source forbidden tokens 第五十三批


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
    "urllib",
    "socket",
    "pty.",
    "ctypes",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch32(token):
    src = inspect.getsource(rmod)
    assert token not in src


# subprocess 是合法用例


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch32():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_contains_future_annotations_batch32():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_datetime_import_batch32():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_contains_pathlib_import_batch32():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_subprocess_import_batch32():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_contains_evaluator_version_import_batch32():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_contains_ratio_metrics_const_batch32():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS = (" in src


def test_module_source_contains_count_metrics_const_batch32():
    src = inspect.getsource(rmod)
    assert "_COUNT_METRICS = " in src


def test_module_source_contains_success_bool_metrics_const_batch32():
    src = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS = " in src


def test_module_source_contains_get_git_provenance_func_batch32():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src


def test_module_source_contains_get_dependency_versions_func_batch32():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions(" in src


def test_module_source_contains_build_provenance_func_batch32():
    src = inspect.getsource(rmod)
    assert "def build_provenance(" in src


def test_module_source_contains_build_devset_section_func_batch32():
    src = inspect.getsource(rmod)
    assert "def build_devset_section(" in src


def test_module_source_contains_aggregate_summary_func_batch32():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary(" in src


def test_module_source_contains_all_batch32():
    src = inspect.getsource(rmod)
    assert "__all__" in src
    assert '"build_provenance"' in src
    assert '"build_devset_section"' in src
    assert '"aggregate_summary"' in src
    assert '"get_git_provenance"' in src
    assert '"get_dependency_versions"' in src


# ---------- signatures 第四十九批


def test_signature_get_git_provenance_one_param_batch32():
    sig = inspect.signature(get_git_provenance)
    assert list(sig.parameters.keys()) == ["project_root"]


def test_signature_get_dependency_versions_no_params_batch32():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_signature_build_provenance_params_batch32():
    sig = inspect.signature(build_provenance)
    assert list(sig.parameters.keys()) == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_devset_section_one_param_batch32():
    sig = inspect.signature(build_devset_section)
    assert len(sig.parameters) == 1


def test_signature_aggregate_summary_one_param_batch32():
    sig = inspect.signature(aggregate_summary)
    assert list(sig.parameters.keys()) == ["per_doc_results"]


# ---------- module 合理性第四十九批


def test_module_imports_subprocess_batch32():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_imports_datetime_batch32():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_imports_pathlib_batch32():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_has_build_provenance_func_batch32():
    assert callable(rmod.build_provenance)


def test_module_has_aggregate_summary_func_batch32():
    assert callable(rmod.aggregate_summary)


def test_module_has_get_git_provenance_func_batch32():
    assert callable(rmod.get_git_provenance)


def test_module_has_get_dependency_versions_func_batch32():
    assert callable(rmod.get_dependency_versions)


def test_module_has_build_devset_section_func_batch32():
    assert callable(rmod.build_devset_section)


# ---------- 端到端集成第四十九批


def test_e2e_build_provenance_with_real_dir_batch32(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] is None
    assert out["max_chars"] == 800
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION
    assert isinstance(out["dependencies"], dict)
    assert set(out["dependencies"].keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_e2e_aggregate_summary_with_mixed_results_batch32():
    results = [
        {
            "doc_id": "d1",
            "metrics": {
                "pipeline_success": {"value": True, "reason": None},
                "element_count_total": {"value": 5, "reason": None},
                "schema_valid": {"value": 1.0, "reason": None},
                "silent_drop_count": {"value": 2, "reason": None},
            },
        },
        {
            "doc_id": "d2",
            "metrics": {
                "pipeline_success": {"value": False, "reason": None},
                "element_count_total": {"value": None, "reason": "pipeline_failed"},
                "schema_valid": {"value": None, "reason": "pipeline_failed"},
                "silent_drop_count": {"value": None, "reason": "pipeline_failed"},
            },
        },
    ]
    out = aggregate_summary(results)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_e2e_aggregate_summary_all_results_batch32():
    """所有文档成功 + 全部 ratio=1.0 → macro=1.0。"""
    results = []
    for i in range(3):
        results.append({
            "doc_id": f"d{i}",
            "metrics": {
                "pipeline_success": {"value": True, "reason": None},
                "schema_valid": {"value": 1.0, "reason": None},
                "pdf_locator_valid_ratio": {"value": 1.0, "reason": None},
            },
        })
    out = aggregate_summary(results)
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 1.0


def test_e2e_idempotent_batch32():
    results = [{"metrics": {"pipeline_success": {"value": True, "reason": None}}}]
    out1 = aggregate_summary(results)
    out2 = aggregate_summary(results)
    assert out1 == out2


def test_e2e_get_dependency_versions_returns_dict_batch32():
    out = get_dependency_versions()
    assert isinstance(out, dict)
    assert len(out) == 3
