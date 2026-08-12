"""evaluation/report.py 第五十二轮 edges 测试（Round 569）。

补强 edges51 未触及的角度（第三十三批）。
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第三十三批


def test_ratio_metrics_count_12_batch33():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_contains_text_preservation_equal_batch33():
    assert "text_preservation_equal" in _RATIO_METRICS


def test_ratio_metrics_contains_text_char_multiset_precision_batch33():
    assert "text_char_multiset_precision" in _RATIO_METRICS


def test_ratio_metrics_contains_text_char_multiset_recall_batch33():
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_contains_heading_boundary_compliance_batch33():
    assert "heading_boundary_compliance" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_precision_batch33():
    assert "chunk_boundary_precision" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_recall_batch33():
    assert "chunk_boundary_recall" in _RATIO_METRICS


def test_ratio_metrics_not_contains_figure_caption_batch33():
    """figure_caption_* 不在 _RATIO_METRICS（始终 null）。"""
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_ratio_metrics_not_contains_element_count_batch33():
    assert "element_count_total" not in _RATIO_METRICS


def test_ratio_metrics_not_contains_pipeline_success_batch33():
    assert "pipeline_success" not in _RATIO_METRICS


def test_count_metrics_value_batch33():
    assert _COUNT_METRICS == ("element_count_total",)


def test_count_metrics_not_contains_silent_drop_batch33():
    """silent_drop_count 单独聚合，不在 _COUNT_METRICS。"""
    assert "silent_drop_count" not in _COUNT_METRICS


def test_success_bool_metrics_value_batch33():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_success_bool_metrics_not_contains_schema_valid_batch33():
    """schema_valid 是 ratio 不是 bool metric。"""
    assert "schema_valid" not in _SUCCESS_BOOL_METRICS


# ---------- get_git_provenance 第三十三批


def test_git_provenance_with_subprocess_error_batch33(tmp_path):
    """subprocess.run raises OSError → commit=None, dirty=True。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = OSError("fail")
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] is None
        assert out["git_dirty"] is True


def test_git_provenance_with_subprocess_timeout_batch33(tmp_path):
    """subprocess.run raises TimeoutExpired → commit=None, dirty=True。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=10)
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] is None
        assert out["git_dirty"] is True


def test_git_provenance_first_command_fails_batch33(tmp_path):
    """第一命令 returncode=1 → commit=None；第二命令仍跑。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="err"),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] is None


def test_git_provenance_first_command_empty_stdout_batch33(tmp_path):
    """第一命令成功但 stdout 空 → commit=None。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="  \n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] is None


def test_git_provenance_commit_value_is_str_batch33(tmp_path):
    """成功时 commit 是 str。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] == "abc123"


def test_git_provenance_dirty_when_dirty_repo_batch33(tmp_path):
    """第二命令 stdout 非空 → dirty=True。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout=" M file.txt\n", stderr=""),
        ]
        out = get_git_provenance(tmp_path)
        assert out["git_dirty"] is True


def test_git_provenance_clean_when_porcelain_empty_batch33(tmp_path):
    """第二命令 stdout 空 → dirty=False。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        out = get_git_provenance(tmp_path)
        assert out["git_dirty"] is False


def test_git_provenance_returns_two_keys_batch33(tmp_path):
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        out = get_git_provenance(tmp_path)
        assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_git_provenance_subprocess_timeout_value_10_batch33(tmp_path):
    """subprocess.run 带 timeout=10。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        get_git_provenance(tmp_path)
        for call in mock_run.call_args_list:
            assert call.kwargs.get("timeout") == 10


def test_git_provenance_subprocess_capture_output_true_batch33(tmp_path):
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        get_git_provenance(tmp_path)
        for call in mock_run.call_args_list:
            assert call.kwargs.get("capture_output") is True


def test_git_provenance_subprocess_encoding_utf8_batch33(tmp_path):
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        get_git_provenance(tmp_path)
        for call in mock_run.call_args_list:
            assert call.kwargs.get("encoding") == "utf-8"
            assert call.kwargs.get("errors") == "replace"


# ---------- get_dependency_versions 第三十三批


def test_dependency_versions_returns_dict_batch33():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_dependency_versions_keys_count_3_batch33():
    out = get_dependency_versions()
    assert len(out) == 3


def test_dependency_versions_pdfplumber_value_or_none_batch33():
    out = get_dependency_versions()
    assert out["pdfplumber"] is None or isinstance(out["pdfplumber"], str)


def test_dependency_versions_python_docx_value_or_none_batch33():
    out = get_dependency_versions()
    assert out["python-docx"] is None or isinstance(out["python-docx"], str)


def test_dependency_versions_pypdfium2_value_or_none_batch33():
    out = get_dependency_versions()
    assert out["pypdfium2"] is None or isinstance(out["pypdfium2"], str)


def test_dependency_versions_with_package_not_found_batch33():
    """模拟 PackageNotFoundError → 对应值为 None。"""
    import importlib.metadata
    with patch("importlib.metadata.version") as mock_ver:
        mock_ver.side_effect = importlib.metadata.PackageNotFoundError("x")
        out = get_dependency_versions()
        assert out["pdfplumber"] is None
        assert out["python-docx"] is None
        assert out["pypdfium2"] is None


def test_dependency_versions_with_generic_exception_batch33():
    """模拟非 PackageNotFoundError → 也返回 None。"""
    with patch("importlib.metadata.version") as mock_ver:
        mock_ver.side_effect = RuntimeError("boom")
        out = get_dependency_versions()
        assert out["pdfplumber"] is None


# ---------- build_provenance 第三十三批


def test_build_provenance_returns_dict_batch33(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out, dict)


def test_build_provenance_keys_count_9_batch33(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    expected_keys = {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    }
    assert set(out.keys()) == expected_keys


def test_build_provenance_parser_name_value_batch33(tmp_path):
    out = build_provenance(tmp_path, "kreuzberg", 800, "1.0")
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_none_batch33(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_max_chars_int_value_batch33(tmp_path):
    """max_chars 始终是 int（强转）。"""
    out = build_provenance(tmp_path, "fallback", "800", None)  # type: ignore[arg-type]
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_negative_batch33(tmp_path):
    out = build_provenance(tmp_path, "fallback", -100, None)
    assert out["max_chars"] == -100


def test_build_provenance_run_timestamp_iso_format_batch33(tmp_path):
    """run_timestamp_iso 应是 ISO 8601 格式（能 fromisoformat 解析）。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    parsed = datetime.fromisoformat(out["run_timestamp_iso"])
    assert parsed is not None


def test_build_provenance_evaluator_version_value_batch33(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value_batch33(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_dependencies_dict_batch33(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_dependencies_keys_batch33(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert set(out["dependencies"].keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_build_provenance_git_commit_value_batch33(tmp_path):
    with patch("evaluation.report.get_git_provenance") as mock_git:
        mock_git.return_value = {"git_commit": "abc123", "git_dirty": False}
        out = build_provenance(tmp_path, "fallback", 800, None)
        assert out["git_commit"] == "abc123"
        assert out["git_dirty"] is False


# ---------- build_devset_section 第三十三批


def _make_manifest_mock(
    devset_status="incomplete",
    file_count=0,
    content_group_count=0,
    pdf_count=0,
    docx_count=0,
    categories_covered=None,
):
    if categories_covered is None:
        categories_covered = []
    m = MagicMock()
    m.devset_status = devset_status
    m.file_count = file_count
    m.content_group_count = content_group_count
    m.pdf_count = pdf_count
    m.docx_count = docx_count
    m.categories_covered = categories_covered
    return m


def test_build_devset_section_returns_dict_batch33():
    out = build_devset_section(_make_manifest_mock())
    assert isinstance(out, dict)


def test_build_devset_section_keys_count_6_batch33():
    out = build_devset_section(_make_manifest_mock())
    assert set(out.keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_build_devset_section_status_value_batch33():
    out = build_devset_section(_make_manifest_mock(devset_status="complete"))
    assert out["status"] == "complete"


def test_build_devset_section_file_count_value_batch33():
    out = build_devset_section(_make_manifest_mock(file_count=42))
    assert out["file_count"] == 42


def test_build_devset_section_content_group_count_value_batch33():
    out = build_devset_section(_make_manifest_mock(content_group_count=7))
    assert out["content_group_count"] == 7


def test_build_devset_section_pdf_count_value_batch33():
    out = build_devset_section(_make_manifest_mock(pdf_count=3))
    assert out["pdf_count"] == 3


def test_build_devset_section_docx_count_value_batch33():
    out = build_devset_section(_make_manifest_mock(docx_count=5))
    assert out["docx_count"] == 5


def test_build_devset_section_categories_covered_value_batch33():
    cats = ["essay", "report"]
    out = build_devset_section(_make_manifest_mock(categories_covered=cats))
    assert out["categories_covered"] == cats


def test_build_devset_section_empty_categories_batch33():
    out = build_devset_section(_make_manifest_mock(categories_covered=[]))
    assert out["categories_covered"] == []


# ---------- aggregate_summary 第三十三批


def test_aggregate_summary_empty_list_batch33():
    out = aggregate_summary([])
    assert isinstance(out, dict)


def test_aggregate_summary_keys_count_4_batch33():
    """返回 4 个顶层 key。"""
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_counts_element_count_total_batch33():
    out = aggregate_summary([])
    assert "element_count_total" in out["counts"]


def test_aggregate_summary_counts_no_other_metrics_batch33():
    """counts 只有 element_count_total。"""
    out = aggregate_summary([])
    assert set(out["counts"].keys()) == {"element_count_total"}


def test_aggregate_summary_success_rates_pipeline_success_batch33():
    out = aggregate_summary([])
    assert "pipeline_success" in out["success_rates"]


def test_aggregate_summary_success_rates_no_other_metrics_batch33():
    out = aggregate_summary([])
    assert set(out["success_rates"].keys()) == {"pipeline_success"}


def test_aggregate_summary_counts_sum_with_int_value_batch33():
    results = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"element_count_total": {"value": 3, "reason": None}}},
    ]
    out = aggregate_summary(results)
    assert out["counts"]["element_count_total"]["sum"] == 8


def test_aggregate_summary_counts_skips_null_value_batch33():
    """value=None 的不参与 sum。"""
    results = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"element_count_total": {"value": None, "reason": "pipeline_failed"}}},
    ]
    out = aggregate_summary(results)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_success_rate_with_mixed_batch33():
    results = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": None, "reason": "x"}}},  # not True → not counted
    ]
    out = aggregate_summary(results)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["total"] == 3
    assert out["success_rates"]["pipeline_success"]["rate"] == 1 / 3


def test_aggregate_summary_success_rate_all_true_batch33():
    results = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    ]
    out = aggregate_summary(results)
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0


def test_aggregate_summary_ratio_macro_average_batch33():
    results = [
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
        {"metrics": {"schema_valid": {"value": 0.5, "reason": None}}},
    ]
    out = aggregate_summary(results)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.75


def test_aggregate_summary_ratio_macro_with_null_batch33():
    results = [
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
    ]
    out = aggregate_summary(results)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_sum_batch33():
    results = [
        {"metrics": {"silent_drop_count": {"value": 3, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": 5, "reason": None}}},
    ]
    out = aggregate_summary(results)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_with_null_batch33():
    results = [
        {"metrics": {"silent_drop_count": {"value": 3, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": None, "reason": "no_expectations"}}},
    ]
    out = aggregate_summary(results)
    assert out["silent_drop_total"] == 3


def test_aggregate_summary_silent_drop_all_null_batch33():
    results = [
        {"metrics": {"silent_drop_count": {"value": None, "reason": "x"}}},
    ]
    out = aggregate_summary(results)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_does_not_mutate_input_batch33():
    import copy
    results = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    ]
    before = copy.deepcopy(results)
    aggregate_summary(results)
    assert results == before


def test_aggregate_summary_missing_metrics_key_raises_batch33():
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
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch33(token):
    src = inspect.getsource(rmod)
    assert token not in src


# subprocess 是 report.py 合法用例（git provenance），不在 forbidden 列表


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch33():
    src = inspect.getsource(rmod)
    assert "评测报告" in src


def test_module_source_contains_future_annotations_batch33():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_subprocess_import_batch33():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_contains_datetime_import_batch33():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_contains_pathlib_import_batch33():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch33():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_contains_evaluator_version_import_batch33():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_contains_ratio_metrics_definition_batch33():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS = (" in src


def test_module_source_contains_count_metrics_definition_batch33():
    src = inspect.getsource(rmod)
    assert "_COUNT_METRICS = " in src


def test_module_source_contains_success_bool_metrics_definition_batch33():
    src = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS = " in src


def test_module_source_contains_get_git_provenance_func_batch33():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src


def test_module_source_contains_get_dependency_versions_func_batch33():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions(" in src


def test_module_source_contains_build_provenance_func_batch33():
    src = inspect.getsource(rmod)
    assert "def build_provenance(" in src


def test_module_source_contains_build_devset_section_func_batch33():
    src = inspect.getsource(rmod)
    assert "def build_devset_section(" in src


def test_module_source_contains_aggregate_summary_func_batch33():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary(" in src


def test_module_source_contains_rev_parse_command_batch33():
    src = inspect.getsource(rmod)
    assert '"rev-parse"' in src or '"rev-parse", "HEAD"' in src


def test_module_source_contains_status_porcelain_command_batch33():
    src = inspect.getsource(rmod)
    assert '"status"' in src
    assert '"--porcelain"' in src


def test_module_source_contains_importlib_metadata_batch33():
    src = inspect.getsource(rmod)
    assert "import importlib.metadata" in src


def test_module_source_contains_pdfplumber_dep_name_batch33():
    src = inspect.getsource(rmod)
    assert '"pdfplumber"' in src


def test_module_source_contains_python_docx_dep_name_batch33():
    src = inspect.getsource(rmod)
    assert '"python-docx"' in src


def test_module_source_contains_pypdfium2_dep_name_batch33():
    src = inspect.getsource(rmod)
    assert '"pypdfium2"' in src


def test_module_source_contains_all_batch33():
    src = inspect.getsource(rmod)
    assert "__all__" in src


def test_module_source_all_contains_build_provenance_batch33():
    src = inspect.getsource(rmod)
    assert '"build_provenance"' in src


def test_module_source_all_contains_build_devset_section_batch33():
    src = inspect.getsource(rmod)
    assert '"build_devset_section"' in src


def test_module_source_all_contains_aggregate_summary_batch33():
    src = inspect.getsource(rmod)
    assert '"aggregate_summary"' in src


def test_module_source_all_contains_get_git_provenance_batch33():
    src = inspect.getsource(rmod)
    assert '"get_git_provenance"' in src


def test_module_source_all_contains_get_dependency_versions_batch33():
    src = inspect.getsource(rmod)
    assert '"get_dependency_versions"' in src


# ---------- signatures 第四十九批


def test_signature_get_git_provenance_one_param_batch33():
    sig = inspect.signature(get_git_provenance)
    assert list(sig.parameters.keys()) == ["project_root"]


def test_signature_get_dependency_versions_no_params_batch33():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_signature_build_provenance_four_params_batch33():
    sig = inspect.signature(build_provenance)
    assert list(sig.parameters.keys()) == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_provenance_parser_version_optional_batch33():
    """parser_version 是 required positional（无 default），annotation 是 'str | None'。"""
    sig = inspect.signature(build_provenance)
    assert sig.parameters["parser_version"].default is inspect.Parameter.empty
    assert "str" in str(sig.parameters["parser_version"].annotation)
    assert "None" in str(sig.parameters["parser_version"].annotation)


def test_signature_build_devset_section_one_param_batch33():
    sig = inspect.signature(build_devset_section)
    assert len(sig.parameters) == 1


def test_signature_aggregate_summary_one_param_batch33():
    sig = inspect.signature(aggregate_summary)
    assert list(sig.parameters.keys()) == ["per_doc_results"]


# ---------- module 合理性第四十九批


def test_module_imports_subprocess_batch33():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_imports_datetime_batch33():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_imports_pathlib_batch33():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch33():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_imports_evaluator_version_batch33():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_has_build_provenance_func_batch33():
    assert callable(rmod.build_provenance)


def test_module_has_aggregate_summary_func_batch33():
    assert callable(rmod.aggregate_summary)


def test_module_has_get_git_provenance_func_batch33():
    assert callable(rmod.get_git_provenance)


def test_module_has_get_dependency_versions_func_batch33():
    assert callable(rmod.get_dependency_versions)


def test_module_has_build_devset_section_func_batch33():
    assert callable(rmod.build_devset_section)


def test_module_all_count_5_batch33():
    assert len(rmod.__all__) == 5


# ---------- 端到端集成第四十九批


def test_e2e_build_provenance_full_batch33(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "v1.0")
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] == "v1.0"
    assert out["max_chars"] == 800
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION
    assert isinstance(out["dependencies"], dict)


def test_e2e_aggregate_summary_full_batch33():
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


def test_e2e_aggregate_summary_idempotent_batch33():
    results = [{"metrics": {"pipeline_success": {"value": True, "reason": None}}}]
    o1 = aggregate_summary(results)
    o2 = aggregate_summary(results)
    assert o1 == o2


def test_e2e_get_dependency_versions_returns_dict_batch33():
    out = get_dependency_versions()
    assert isinstance(out, dict)
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_e2e_build_devset_section_complete_status_batch33():
    m = _make_manifest_mock(
        devset_status="complete",
        file_count=100,
        content_group_count=50,
        pdf_count=50,
        docx_count=50,
        categories_covered=["essay", "report", "letter"],
    )
    out = build_devset_section(m)
    assert out["status"] == "complete"
    assert out["file_count"] == 100
