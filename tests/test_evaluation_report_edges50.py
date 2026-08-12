"""evaluation/report.py 第五十轮 edges 测试（Round 555）。

补强 edges49 未触及的角度（第三十一批）。
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第三十一批


def test_ratio_metrics_count_twelve_batch31():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_contains_schema_valid_batch31():
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_contains_text_preservation_equal_batch31():
    assert "text_preservation_equal" in _RATIO_METRICS


def test_ratio_metrics_contains_all_chunk_boundary_batch31():
    assert "chunk_boundary_precision" in _RATIO_METRICS
    assert "chunk_boundary_recall" in _RATIO_METRICS
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_figure_caption_not_included_batch31():
    """figure_caption_* 始终 null，不参与 macro average。"""
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_ratio_metrics_is_tuple_batch31():
    assert isinstance(_RATIO_METRICS, tuple)


def test_count_metrics_is_tuple_batch31():
    assert isinstance(_COUNT_METRICS, tuple)


def test_count_metrics_one_entry_batch31():
    assert _COUNT_METRICS == ("element_count_total",)


def test_count_metrics_contains_element_count_batch31():
    assert "element_count_total" in _COUNT_METRICS


def test_success_bool_metrics_is_tuple_batch31():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_success_bool_metrics_one_entry_batch31():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_success_bool_metrics_contains_pipeline_success_batch31():
    assert "pipeline_success" in _SUCCESS_BOOL_METRICS


def test_no_overlap_between_count_and_ratio_batch31():
    """count metrics 和 ratio metrics 不重叠。"""
    overlap = set(_COUNT_METRICS) & set(_RATIO_METRICS)
    assert overlap == set()


def test_no_overlap_between_success_and_ratio_batch31():
    """success_bool metrics 和 ratio metrics 不重叠。"""
    overlap = set(_SUCCESS_BOOL_METRICS) & set(_RATIO_METRICS)
    assert overlap == set()


# ---------- get_git_provenance 第三十一批


def test_git_provenance_returns_dict_batch31(tmp_path):
    """在非 git 目录 → commit=None, dirty=False 或 True 取决于 git status 返回。"""
    out = get_git_provenance(tmp_path)
    assert isinstance(out, dict)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_git_provenance_subprocess_called_with_cwd_batch31(tmp_path):
    """subprocess.run 被调用且 cwd 设为 project_root。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc123\n", stderr="")
        out = get_git_provenance(tmp_path)
        assert mock_run.call_count == 2
        # 所有调用的 cwd 都是 tmp_path
        for call in mock_run.call_args_list:
            assert call.kwargs.get("cwd") == str(tmp_path)


def test_git_provenance_subprocess_timeout_batch31(tmp_path):
    """subprocess 调用带 timeout=10。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        get_git_provenance(tmp_path)
        for call in mock_run.call_args_list:
            assert call.kwargs.get("timeout") == 10


def test_git_provenance_encoding_utf8_batch31(tmp_path):
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        get_git_provenance(tmp_path)
        for call in mock_run.call_args_list:
            assert call.kwargs.get("encoding") == "utf-8"


def test_git_provenance_errors_replace_batch31(tmp_path):
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        get_git_provenance(tmp_path)
        for call in mock_run.call_args_list:
            assert call.kwargs.get("errors") == "replace"


def test_git_provenance_capture_output_batch31(tmp_path):
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        get_git_provenance(tmp_path)
        for call in mock_run.call_args_list:
            assert call.kwargs.get("capture_output") is True


def test_git_provenance_first_command_rev_parse_batch31(tmp_path):
    """第一次调用：git rev-parse HEAD。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        get_git_provenance(tmp_path)
        first_call_args = mock_run.call_args_list[0].args
        assert first_call_args[0] == ["git", "rev-parse", "HEAD"]


def test_git_provenance_second_command_status_porcelain_batch31(tmp_path):
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        get_git_provenance(tmp_path)
        second_call_args = mock_run.call_args_list[1].args
        assert second_call_args[0] == ["git", "status", "--porcelain"]


def test_git_provenance_commit_when_rev_parse_succeeds_batch31(tmp_path):
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),  # clean
        ]
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] == "abc123"


def test_git_provenance_no_commit_when_rev_parse_fails_batch31(tmp_path):
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=128, stdout="", stderr="error"),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] is None


def test_git_provenance_dirty_when_status_output_nonempty_batch31(tmp_path):
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="M some_file.py\n", stderr=""),
        ]
        out = get_git_provenance(tmp_path)
        assert out["git_dirty"] is True


def test_git_provenance_clean_when_status_output_empty_batch31(tmp_path):
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        out = get_git_provenance(tmp_path)
        assert out["git_dirty"] is False


def test_git_provenance_dirty_false_when_status_fails_batch31(tmp_path):
    """status 返回 128（非 git 目录）→ dirty=False（bool(128==0 and ...) = False）。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=128, stdout="", stderr=""),
            MagicMock(returncode=128, stdout="", stderr=""),
        ]
        out = get_git_provenance(tmp_path)
        assert out["git_dirty"] is False


def test_git_provenance_oserror_fallback_batch31(tmp_path):
    """OSError → commit=None, dirty=True。"""
    with patch("evaluation.report.subprocess.run", side_effect=OSError("nope")):
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] is None
        assert out["git_dirty"] is True


def test_git_provenance_subprocess_error_fallback_batch31(tmp_path):
    with patch("evaluation.report.subprocess.run", side_effect=subprocess.SubprocessError("nope")):
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] is None
        assert out["git_dirty"] is True


def test_git_provenance_timeout_exception_fallback_batch31(tmp_path):
    """TimeoutExpired 是 SubprocessError 子类。"""
    with patch("evaluation.report.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10)):
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] is None
        assert out["git_dirty"] is True


# ---------- get_dependency_versions 第三十一批


def test_dependency_versions_returns_dict_batch31():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_dependency_versions_three_packages_batch31():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_dependency_versions_values_str_or_none_batch31():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str)


# ---------- build_provenance 第三十一批


def test_build_provenance_keys_batch31(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0")
    expected = {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    }
    assert set(out.keys()) == expected


def test_build_provenance_evaluator_version_batch31(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_batch31(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_batch31(tmp_path):
    out = build_provenance(tmp_path, "my_parser", 800, "v1")
    assert out["parser_name"] == "my_parser"


def test_build_provenance_parser_version_none_batch31(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_max_chars_int_batch31(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_negative_batch31(tmp_path):
    """max_chars 负数也被接受（int(-5) = -5）。"""
    out = build_provenance(tmp_path, "fallback", -5, None)
    assert out["max_chars"] == -5


def test_build_provenance_max_chars_zero_batch31(tmp_path):
    out = build_provenance(tmp_path, "fallback", 0, None)
    assert out["max_chars"] == 0


def test_build_provenance_max_chars_str_to_int_batch31(tmp_path):
    """max_chars="800" → int(800)。"""
    out = build_provenance(tmp_path, "fallback", "800", None)
    assert out["max_chars"] == 800


def test_build_provenance_run_timestamp_iso_format_batch31(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    ts = out["run_timestamp_iso"]
    # ISO 格式应该可被 datetime.fromisoformat 解析
    datetime.fromisoformat(ts)


def test_build_provenance_dependencies_present_batch31(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert "dependencies" in out
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_unicode_parser_name_batch31(tmp_path):
    """parser_name 支持 unicode。"""
    out = build_provenance(tmp_path, "中文解析器", 800, None)
    assert out["parser_name"] == "中文解析器"


# ---------- build_devset_section 第三十一批


def test_build_devset_section_keys_batch31():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 5
    m.content_group_count = 3
    m.pdf_count = 2
    m.docx_count = 3
    m.categories_covered = ["essay", "report"]
    out = build_devset_section(m)
    assert set(out.keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_build_devset_section_passes_status_batch31():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 10
    m.content_group_count = 5
    m.pdf_count = 5
    m.docx_count = 5
    m.categories_covered = ["a"]
    out = build_devset_section(m)
    assert out["status"] == "complete"
    assert out["file_count"] == 10
    assert out["content_group_count"] == 5
    assert out["pdf_count"] == 5
    assert out["docx_count"] == 5
    assert out["categories_covered"] == ["a"]


def test_build_devset_section_passes_categories_covered_batch31():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = ["essay", "report", "letter"]
    out = build_devset_section(m)
    assert out["categories_covered"] == ["essay", "report", "letter"]


# ---------- aggregate_summary 第三十一批


def test_aggregate_summary_empty_batch31():
    out = aggregate_summary([])
    assert "counts" in out
    assert "success_rates" in out
    assert "ratio_macro_averages" in out
    assert "silent_drop_total" in out


def test_aggregate_summary_silent_drop_total_null_no_data_batch31():
    out = aggregate_summary([])
    assert out["silent_drop_total"] is None


def test_aggregate_summary_all_pipeline_fail_batch31():
    """所有文档 pipeline 失败 → success_count=0。"""
    results = [
        {"metrics": {"pipeline_success": {"value": False, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": None}}},
    ]
    out = aggregate_summary(results)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0
    assert out["success_rates"]["pipeline_success"]["total"] == 2
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.0


def test_aggregate_summary_all_pipeline_success_batch31():
    results = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    ]
    out = aggregate_summary(results)
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0


def test_aggregate_summary_mixed_pipeline_batch31():
    results = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": None}}},
    ]
    out = aggregate_summary(results)
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5


def test_aggregate_summary_counts_summed_batch31():
    results = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"element_count_total": {"value": 7, "reason": None}}},
    ]
    out = aggregate_summary(results)
    assert out["counts"]["element_count_total"]["sum"] == 12
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_none_skipped_batch31():
    """value=None 不参与。"""
    results = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"element_count_total": {"value": None, "reason": "pipeline_failed"}}},
    ]
    out = aggregate_summary(results)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_counts_no_data_batch31():
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_ratio_macro_batch31():
    results = [
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
        {"metrics": {"schema_valid": {"value": 0.5, "reason": None}}},
    ]
    out = aggregate_summary(results)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.75
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 0


def test_aggregate_summary_ratio_none_skipped_batch31():
    results = [
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "pipeline_failed"}}},
    ]
    out = aggregate_summary(results)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_total_batch31():
    results = [
        {"metrics": {"silent_drop_count": {"value": 3, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": 5, "reason": None}}},
    ]
    out = aggregate_summary(results)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_none_skipped_batch31():
    results = [
        {"metrics": {"silent_drop_count": {"value": 3, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": None, "reason": "no_expectations"}}},
    ]
    out = aggregate_summary(results)
    assert out["silent_drop_total"] == 3


def test_aggregate_summary_no_input_rate_null_batch31():
    out = aggregate_summary([])
    assert out["success_rates"]["pipeline_success"]["rate"] is None


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
def test_module_source_no_forbidden_tokens_batch31(token):
    src = inspect.getsource(rmod)
    assert token not in src


# subprocess 是合法用例（git provenance），不在 forbidden 列表


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch31():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_contains_future_annotations_batch31():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_subprocess_import_batch31():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_contains_datetime_import_batch31():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_contains_pathlib_import_batch31():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_import_batch31():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_contains_evaluator_version_import_batch31():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_contains_ratio_metrics_const_batch31():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS = (" in src


def test_module_source_contains_count_metrics_const_batch31():
    src = inspect.getsource(rmod)
    assert "_COUNT_METRICS = " in src


def test_module_source_contains_success_bool_metrics_const_batch31():
    src = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS = " in src


def test_module_source_contains_get_git_provenance_func_batch31():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src


def test_module_source_contains_get_dependency_versions_func_batch31():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions(" in src


def test_module_source_contains_build_provenance_func_batch31():
    src = inspect.getsource(rmod)
    assert "def build_provenance(" in src


def test_module_source_contains_build_devset_section_func_batch31():
    src = inspect.getsource(rmod)
    assert "def build_devset_section(" in src


def test_module_source_contains_aggregate_summary_func_batch31():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary(" in src


def test_module_source_contains_subprocess_run_call_batch31():
    src = inspect.getsource(rmod)
    assert "subprocess.run(" in src


def test_module_source_contains_rev_parse_batch31():
    src = inspect.getsource(rmod)
    assert '"git", "rev-parse", "HEAD"' in src


def test_module_source_contains_status_porcelain_batch31():
    src = inspect.getsource(rmod)
    assert '"git", "status", "--porcelain"' in src


def test_module_source_contains_all_batch31():
    src = inspect.getsource(rmod)
    assert "__all__" in src
    assert '"build_provenance"' in src
    assert '"build_devset_section"' in src
    assert '"aggregate_summary"' in src
    assert '"get_git_provenance"' in src
    assert '"get_dependency_versions"' in src


# ---------- signatures 第四十九批


def test_signature_get_git_provenance_params_batch31():
    sig = inspect.signature(get_git_provenance)
    assert list(sig.parameters.keys()) == ["project_root"]


def test_signature_get_dependency_versions_no_params_batch31():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_signature_build_provenance_params_batch31():
    sig = inspect.signature(build_provenance)
    assert list(sig.parameters.keys()) == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_devset_section_params_batch31():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.keys())
    assert len(params) == 1


def test_signature_aggregate_summary_params_batch31():
    sig = inspect.signature(aggregate_summary)
    assert list(sig.parameters.keys()) == ["per_doc_results"]


def test_signature_build_provenance_return_dict_batch31():
    sig = inspect.signature(build_provenance)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_build_devset_section_return_dict_batch31():
    sig = inspect.signature(build_devset_section)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_aggregate_summary_return_dict_batch31():
    sig = inspect.signature(aggregate_summary)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_get_git_provenance_return_dict_batch31():
    sig = inspect.signature(get_git_provenance)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_get_dependency_versions_return_dict_batch31():
    sig = inspect.signature(get_dependency_versions)
    assert sig.return_annotation == "dict[str, str | None]"


# ---------- module 合理性第四十九批


def test_module_has_future_annotations_batch31():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_imports_subprocess_batch31():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_has_get_git_provenance_func_batch31():
    assert callable(rmod.get_git_provenance)


def test_module_has_get_dependency_versions_func_batch31():
    assert callable(rmod.get_dependency_versions)


def test_module_has_build_provenance_func_batch31():
    assert callable(rmod.build_provenance)


def test_module_has_build_devset_section_func_batch31():
    assert callable(rmod.build_devset_section)


def test_module_has_aggregate_summary_func_batch31():
    assert callable(rmod.aggregate_summary)


def test_module_has_all_batch31():
    assert hasattr(rmod, "__all__")
    assert "build_provenance" in rmod.__all__
    assert "build_devset_section" in rmod.__all__
    assert "aggregate_summary" in rmod.__all__
    assert "get_git_provenance" in rmod.__all__
    assert "get_dependency_versions" in rmod.__all__


# ---------- 端到端集成第四十九批


def test_e2e_build_provenance_full_batch31(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] == "1.0"
    assert out["max_chars"] == 800
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION
    assert isinstance(out["git_commit"], (str, type(None)))
    assert isinstance(out["git_dirty"], bool)
    assert isinstance(out["dependencies"], dict)
    datetime.fromisoformat(out["run_timestamp_iso"])


def test_e2e_aggregate_summary_real_data_batch31():
    """完整 per_doc 列表 → summary 聚合。"""
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
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert out["silent_drop_total"] == 2


def test_e2e_idempotent_batch31():
    results = [{"metrics": {"pipeline_success": {"value": True, "reason": None}}}]
    out1 = aggregate_summary(results)
    out2 = aggregate_summary(results)
    # 排除 run_timestamp（在 build_provenance 里，aggregate_summary 没有时间戳）
    assert out1 == out2


def test_e2e_get_dependency_versions_no_throw_batch31():
    """get_dependency_versions 不抛异常。"""
    out = get_dependency_versions()
    # 包含三个键
    assert "pdfplumber" in out
    assert "python-docx" in out
    assert "pypdfium2" in out
