"""evaluation/report.py 第四十八轮 edges 测试（Round 541）。

补强 edges47 未触及的角度（第三十二批）。
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


# ---------- _RATIO_METRICS 第三十二批 ----------


def test_ratio_metrics_count_is_twelve_batch32():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_zero_is_schema_valid_batch32():
    assert _RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_last_is_chunk_boundary_f1_batch32():
    assert _RATIO_METRICS[-1] == "chunk_boundary_f1"


def test_ratio_metrics_index_of_text_preservation_equal_batch32():
    assert _RATIO_METRICS.index("text_preservation_equal") == 5


def test_ratio_metrics_contains_pdf_locator_batch32():
    assert "pdf_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_docx_locator_batch32():
    assert "docx_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_image_resource_batch32():
    assert "image_resource_exists_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_reference_batch32():
    assert "chunk_reference_intact_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_text_char_multiset_precision_batch32():
    assert "text_char_multiset_precision" in _RATIO_METRICS


def test_ratio_metrics_contains_text_char_multiset_recall_batch32():
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_precision_batch32():
    assert "chunk_boundary_precision" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_recall_batch32():
    assert "chunk_boundary_recall" in _RATIO_METRICS


def test_ratio_metrics_no_duplicates_batch32():
    assert len(_RATIO_METRICS) == len(set(_RATIO_METRICS))


# ---------- _COUNT_METRICS 第三十二批 ----------


def test_count_metrics_count_one_batch32():
    assert len(_COUNT_METRICS) == 1


def test_count_metrics_first_is_element_count_total_batch32():
    assert _COUNT_METRICS[0] == "element_count_total"


def test_count_metrics_no_duplicates_batch32():
    assert len(_COUNT_METRICS) == len(set(_COUNT_METRICS))


def test_count_metrics_disjoint_from_ratio_batch32():
    assert not (set(_COUNT_METRICS) & set(_RATIO_METRICS))


# ---------- _SUCCESS_BOOL_METRICS 第三十二批 ----------


def test_success_bool_metrics_count_one_batch32():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_success_bool_metrics_first_is_pipeline_success_batch32():
    assert _SUCCESS_BOOL_METRICS[0] == "pipeline_success"


def test_success_bool_metrics_disjoint_from_ratio_batch32():
    assert not (set(_SUCCESS_BOOL_METRICS) & set(_RATIO_METRICS))


def test_success_bool_metrics_disjoint_from_count_batch32():
    assert not (set(_SUCCESS_BOOL_METRICS) & set(_COUNT_METRICS))


# ---------- get_git_provenance 第三十二批 ----------


def test_get_git_provenance_no_git_repo_batch32(tmp_path):
    """目录不是 git repo → git 命令 returncode!=0 但无异常 → commit=null, dirty=False。"""
    d = tmp_path / "notrepo"
    d.mkdir()
    out = get_git_provenance(d)
    assert out["git_commit"] is None
    # git status --porcelain 返回非零 → dirty = bool(False and ...) = False
    assert out["git_dirty"] is False


def test_get_git_provenance_timeout_returns_dirty_true_batch32(tmp_path):
    """TimeoutExpired → catch → dirty=true。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=10)
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_oserror_returns_dirty_true_batch32(tmp_path):
    """OSError → catch → dirty=true。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = OSError("boom")
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_first_call_fails_second_clean_batch32(tmp_path):
    """rev-parse fails but status succeeds clean → commit=None, dirty=False。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        r1 = MagicMock(returncode=1, stdout="", stderr="err")
        r2 = MagicMock(returncode=0, stdout="", stderr="")
        mock_run.side_effect = [r1, r2]
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is False


def test_get_git_provenance_first_success_second_dirty_batch32(tmp_path):
    """rev-parse succeeds, status non-empty → commit set, dirty=true。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        r1 = MagicMock(returncode=0, stdout="abc123\n", stderr="")
        r2 = MagicMock(returncode=0, stdout=" M file.txt\n", stderr="")
        mock_run.side_effect = [r1, r2]
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is True


def test_get_git_provenance_first_returns_empty_string_batch32(tmp_path):
    """rev-parse returncode=0 but stdout empty → commit=None。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        r1 = MagicMock(returncode=0, stdout="", stderr="")
        r2 = MagicMock(returncode=0, stdout="", stderr="")
        mock_run.side_effect = [r1, r2]
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_returns_dict_keys_count_batch32(tmp_path):
    out = get_git_provenance(tmp_path)
    assert isinstance(out, dict)
    assert len(out) == 2


# ---------- get_dependency_versions 第三十二批 ----------


def test_get_dependency_versions_pdfplumber_or_none_batch32():
    out = get_dependency_versions()
    assert "pdfplumber" in out
    assert out["pdfplumber"] is None or isinstance(out["pdfplumber"], str)


def test_get_dependency_versions_python_docx_or_none_batch32():
    out = get_dependency_versions()
    assert "python-docx" in out
    assert out["python-docx"] is None or isinstance(out["python-docx"], str)


def test_get_dependency_versions_pypdfium2_or_none_batch32():
    out = get_dependency_versions()
    assert "pypdfium2" in out
    assert out["pypdfium2"] is None or isinstance(out["pypdfium2"], str)


def test_get_dependency_versions_three_keys_batch32():
    out = get_dependency_versions()
    assert len(out) == 3


def test_get_dependency_versions_package_not_found_batch32():
    """PackageNotFoundError → value=None。"""
    import importlib.metadata as md
    with patch("importlib.metadata.version") as mock_v:
        mock_v.side_effect = md.PackageNotFoundError("not found")
        out = get_dependency_versions()
    for v in out.values():
        assert v is None


def test_get_dependency_versions_other_exception_batch32():
    """其他 Exception → value=None。"""
    with patch("importlib.metadata.version") as mock_v:
        mock_v.side_effect = RuntimeError("boom")
        out = get_dependency_versions()
    for v in out.values():
        assert v is None


def test_get_dependency_versions_idempotent_batch32():
    out1 = get_dependency_versions()
    out2 = get_dependency_versions()
    assert out1 == out2


# ---------- build_provenance 第三十二批 ----------


def test_build_provenance_keys_set_batch32(tmp_path):
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


def test_build_provenance_max_chars_int_batch32(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_parser_name_passes_through_batch32(tmp_path):
    out = build_provenance(tmp_path, "kreuzberg", 500, None)
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_passes_through_batch32(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "9.9")
    assert out["parser_version"] == "9.9"


def test_build_provenance_parser_version_none_passes_through_batch32(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_evaluator_version_value_batch32(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value_batch32(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_timestamp_iso_format_batch32(tmp_path):
    """isoformat 应可被 datetime.fromisoformat 解析。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    dt = datetime.fromisoformat(out["run_timestamp_iso"])
    assert isinstance(dt, datetime)


def test_build_provenance_dependencies_is_dict_batch32(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_max_chars_string_to_int_batch32(tmp_path):
    """int(max_chars) 把 string 转 int。"""
    out = build_provenance(tmp_path, "fallback", "800", None)
    assert out["max_chars"] == 800


# ---------- build_devset_section 第三十二批 ----------


def test_build_devset_section_keys_set_batch32():
    fake = MagicMock()
    fake.devset_status = "complete"
    fake.file_count = 5
    fake.content_group_count = 3
    fake.pdf_count = 2
    fake.docx_count = 3
    fake.categories_covered = ["a", "b"]
    out = build_devset_section(fake)
    assert set(out.keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_build_devset_section_status_passes_through_batch32():
    fake = MagicMock()
    fake.devset_status = "incomplete"
    fake.file_count = 0
    fake.content_group_count = 0
    fake.pdf_count = 0
    fake.docx_count = 0
    fake.categories_covered = []
    out = build_devset_section(fake)
    assert out["status"] == "incomplete"


def test_build_devset_section_all_values_pass_through_batch32():
    fake = MagicMock()
    fake.devset_status = "partial"
    fake.file_count = 10
    fake.content_group_count = 7
    fake.pdf_count = 4
    fake.docx_count = 6
    fake.categories_covered = ["report", "memo"]
    out = build_devset_section(fake)
    assert out["file_count"] == 10
    assert out["content_group_count"] == 7
    assert out["pdf_count"] == 4
    assert out["docx_count"] == 6
    assert out["categories_covered"] == ["report", "memo"]


def test_build_devset_section_returns_dict_batch32():
    fake = MagicMock()
    out = build_devset_section(fake)
    assert isinstance(out, dict)


def test_build_devset_section_keys_count_six_batch32():
    fake = MagicMock()
    out = build_devset_section(fake)
    assert len(out) == 6


# ---------- aggregate_summary 第三十二批 ----------


def test_aggregate_summary_single_doc_all_metrics_batch32():
    per_doc = [
        {
            "metrics": {
                "schema_valid": {"value": True, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
                "element_count_total": {"value": 5, "reason": None},
                "pdf_locator_valid_ratio": {"value": 1.0, "reason": None},
                "silent_drop_count": {"value": 2, "reason": None},
            }
        }
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["counts"]["element_count_total"]["participating_docs"] == 1
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert out["silent_drop_total"] == 2


def test_aggregate_summary_three_docs_partial_participation_batch32():
    per_doc = [
        {
            "metrics": {
                "schema_valid": {"value": True, "reason": None},
                "pdf_locator_valid_ratio": {"value": 1.0, "reason": None},
                "silent_drop_count": {"value": 3, "reason": None},
                "element_count_total": {"value": 4, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
            }
        },
        {
            "metrics": {
                "schema_valid": {"value": None, "reason": "pipeline_failed"},
                "pdf_locator_valid_ratio": {"value": None, "reason": "pipeline_failed"},
                "silent_drop_count": {"value": None, "reason": "no_expectations"},
                "element_count_total": {"value": None, "reason": "pipeline_failed"},
                "pipeline_success": {"value": False, "reason": None},
            }
        },
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 4
    assert out["counts"]["element_count_total"]["participating_docs"] == 1
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["total"] == 2
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1
    assert out["silent_drop_total"] == 3


def test_aggregate_summary_all_none_macro_average_batch32():
    per_doc = [
        {
            "metrics": {
                "schema_valid": {"value": None, "reason": "x"},
                "pdf_locator_valid_ratio": {"value": None, "reason": "x"},
            }
        }
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] is None
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 0
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1


def test_aggregate_summary_macro_average_calculation_batch32():
    per_doc = [
        {
            "metrics": {
                "schema_valid": {"value": 1.0, "reason": None},
                "pdf_locator_valid_ratio": {"value": 0.5, "reason": None},
            }
        },
        {
            "metrics": {
                "schema_valid": {"value": 0.0, "reason": None},
                "pdf_locator_valid_ratio": {"value": 1.0, "reason": None},
            }
        },
    ]
    out = aggregate_summary(per_doc)
    # schema_valid macro = (1.0 + 0.0) / 2 = 0.5
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    # pdf_locator macro = (0.5 + 1.0) / 2 = 0.75
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 0.75


def test_aggregate_summary_silent_drop_total_with_mix_batch32():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 5, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": None, "reason": "no_expectations"}}},
        {"metrics": {"silent_drop_count": {"value": 3, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_total_none_batch32():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None, "reason": "x"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_counts_no_participating_batch32():
    per_doc = [
        {"metrics": {"element_count_total": {"value": None, "reason": "x"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_success_rate_with_zero_total_batch32():
    out = aggregate_summary([])
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0
    assert out["success_rates"]["pipeline_success"]["total"] == 0
    assert out["success_rates"]["pipeline_success"]["rate"] is None


def test_aggregate_summary_returns_dict_batch32():
    out = aggregate_summary([])
    assert isinstance(out, dict)


def test_aggregate_summary_top_level_keys_count_batch32():
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_idempotent_batch32():
    per_doc = [
        {"metrics": {"schema_valid": {"value": True, "reason": None}}}
    ]
    out1 = aggregate_summary(per_doc)
    out2 = aggregate_summary(per_doc)
    assert out1 == out2


def test_aggregate_summary_counts_for_element_count_total_batch32():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10, "reason": None}}},
        {"metrics": {"element_count_total": {"value": 20, "reason": None}}},
        {"metrics": {"element_count_total": {"value": 30, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 60
    assert out["counts"]["element_count_total"]["participating_docs"] == 3


def test_aggregate_summary_no_input_modification_batch32():
    import json
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10, "reason": None}}},
    ]
    before = json.dumps(per_doc, sort_keys=True)
    aggregate_summary(per_doc)
    assert json.dumps(per_doc, sort_keys=True) == before


# ---------- module source forbidden tokens 第四十九批 ----------


def test_module_source_no_eval_batch32():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch32():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch32():
    src = inspect.getsource(rmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch32():
    src = inspect.getsource(rmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch32():
    src = inspect.getsource(rmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch32():
    src = inspect.getsource(rmod)
    assert "breakpoint(" not in src


def test_module_source_no_shutil_batch32():
    src = inspect.getsource(rmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch32():
    src = inspect.getsource(rmod)
    assert "requests" not in src


def test_module_source_no_open_w_mode_batch32():
    src = inspect.getsource(rmod)
    assert "'w'" not in src
    assert '"w"' not in src


# ---------- module source 字符串精确补强第四十五批 ----------


def test_module_source_contains_module_docstring_batch32():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_contains_subprocess_import_batch32():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_contains_datetime_import_batch32():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_contains_pathlib_import_batch32():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch32():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_contains_versions_import_batch32():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_contains_ratio_metrics_const_batch32():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS" in src


def test_module_source_contains_count_metrics_const_batch32():
    src = inspect.getsource(rmod)
    assert "_COUNT_METRICS" in src


def test_module_source_contains_success_bool_metrics_const_batch32():
    src = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS" in src


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


def test_module_source_contains_capture_output_batch32():
    src = inspect.getsource(rmod)
    assert "capture_output=True" in src


def test_module_source_contains_encoding_utf8_batch32():
    src = inspect.getsource(rmod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_errors_replace_batch32():
    src = inspect.getsource(rmod)
    assert 'errors="replace"' in src


def test_module_source_contains_subprocess_timeout_batch32():
    src = inspect.getsource(rmod)
    assert "timeout=10" in src


def test_module_source_contains_subprocess_error_batch32():
    src = inspect.getsource(rmod)
    assert "subprocess.SubprocessError" in src


def test_module_source_contains_git_dirty_fallback_true_batch32():
    src = inspect.getsource(rmod)
    assert "dirty = True" in src


def test_module_source_contains_importlib_metadata_batch32():
    src = inspect.getsource(rmod)
    assert "importlib.metadata" in src


def test_module_source_contains_package_not_found_batch32():
    src = inspect.getsource(rmod)
    assert "PackageNotFoundError" in src


def test_module_source_contains_python_docx_batch32():
    src = inspect.getsource(rmod)
    assert '"python-docx"' in src


def test_module_source_contains_pdfplumber_batch32():
    src = inspect.getsource(rmod)
    assert '"pdfplumber"' in src


def test_module_source_contains_pypdfium2_batch32():
    src = inspect.getsource(rmod)
    assert '"pypdfium2"' in src


# ---------- signatures 第四十五批 ----------


def test_signature_get_git_provenance_param_batch32():
    sig = inspect.signature(get_git_provenance)
    assert sig.parameters["project_root"].annotation == "Path"
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_get_dependency_versions_no_params_batch32():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0
    assert "dict[str, str | None]" in str(sig.return_annotation)


def test_signature_build_provenance_params_batch32():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_provenance_return_dict_batch32():
    sig = inspect.signature(build_provenance)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_build_devset_section_param_batch32():
    sig = inspect.signature(build_devset_section)
    # manifest 没有 annotation（type: ignore[no-untyped-def]）
    assert "manifest" in sig.parameters


def test_signature_aggregate_summary_params_batch32():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.keys())
    assert params == ["per_doc_results"]


def test_signature_aggregate_summary_return_dict_batch32():
    sig = inspect.signature(aggregate_summary)
    assert "dict[str, Any]" in str(sig.return_annotation)


# ---------- module 合理性第四十五批 ----------


def test_module_has_future_annotations_batch32():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_imports_subprocess_batch32():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_imports_datetime_batch32():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_imports_pathlib_batch32():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch32():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_has_all_export_batch32():
    src = inspect.getsource(rmod)
    assert "__all__" in src


def test_module_all_has_five_entries_batch32():
    src = inspect.getsource(rmod)
    for name in [
        '"build_provenance"',
        '"build_devset_section"',
        '"aggregate_summary"',
        '"get_git_provenance"',
        '"get_dependency_versions"',
    ]:
        assert name in src


def test_module_no_main_block_batch32():
    src = inspect.getsource(rmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十五批 ----------


def test_e2e_build_provenance_full_run_batch32(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] == "1.0.0"
    assert out["max_chars"] == 800
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION
    assert isinstance(out["dependencies"], dict)


def test_e2e_aggregate_summary_three_docs_mixed_batch32():
    per_doc = [
        {
            "metrics": {
                "schema_valid": {"value": True, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
                "element_count_total": {"value": 10, "reason": None},
                "pdf_locator_valid_ratio": {"value": 0.8, "reason": None},
                "text_preservation_equal": {"value": True, "reason": None},
                "silent_drop_count": {"value": 1, "reason": None},
            }
        },
        {
            "metrics": {
                "schema_valid": {"value": False, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
                "element_count_total": {"value": 5, "reason": None},
                "pdf_locator_valid_ratio": {"value": 0.4, "reason": None},
                "text_preservation_equal": {"value": False, "reason": None},
                "silent_drop_count": {"value": None, "reason": "no_expectations"},
            }
        },
        {
            "metrics": {
                "schema_valid": {"value": None, "reason": "pipeline_failed"},
                "pipeline_success": {"value": False, "reason": None},
                "element_count_total": {"value": None, "reason": "pipeline_failed"},
                "pdf_locator_valid_ratio": {"value": None, "reason": "pipeline_failed"},
                "text_preservation_equal": {"value": None, "reason": "pipeline_failed"},
                "silent_drop_count": {"value": None, "reason": "pipeline_failed"},
            }
        },
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["counts"]["element_count_total"]["participating_docs"] == 2
    assert out["success_rates"]["pipeline_success"]["success_count"] == 2
    assert out["success_rates"]["pipeline_success"]["total"] == 3
    assert out["success_rates"]["pipeline_success"]["rate"] == pytest.approx(2 / 3)
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == pytest.approx(0.6)
    assert out["silent_drop_total"] == 1


def test_e2e_aggregate_summary_empty_input_batch32():
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["success_rates"]["pipeline_success"]["rate"] is None
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] is None
    assert out["silent_drop_total"] is None


def test_e2e_aggregate_summary_idempotent_batch32():
    per_doc = [
        {
            "metrics": {
                "schema_valid": {"value": True, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
            }
        }
    ]
    out1 = aggregate_summary(per_doc)
    out2 = aggregate_summary(per_doc)
    assert out1 == out2


def test_e2e_get_dependency_versions_no_throw_batch32():
    out = get_dependency_versions()
    # 不抛异常且所有值都是 str 或 None
    for v in out.values():
        assert v is None or isinstance(v, str)


def test_e2e_full_pipeline_provenance_to_summary_batch32(tmp_path):
    """端到端：build_provenance + aggregate_summary。"""
    prov = build_provenance(tmp_path, "fallback", 800, None)
    assert "git_commit" in prov
    assert "git_dirty" in prov

    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True, "reason": None},
                "schema_valid": {"value": True, "reason": None},
                "element_count_total": {"value": 3, "reason": None},
                "silent_drop_count": {"value": 0, "reason": None},
            }
        }
    ]
    summ = aggregate_summary(per_doc)
    assert summ["counts"]["element_count_total"]["sum"] == 3
    assert summ["silent_drop_total"] == 0
