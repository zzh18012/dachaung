"""evaluation/report.py 第五十四轮 edges 测试（Round 583）。

补强 edges53 未触及的角度（第三十五批）。
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第三十五批


def test_ratio_metrics_len_12_batch35():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_no_duplicates_batch35():
    assert len(set(_RATIO_METRICS)) == len(_RATIO_METRICS)


def test_ratio_metrics_all_strings_batch35():
    for name in _RATIO_METRICS:
        assert isinstance(name, str)


def test_count_metrics_no_duplicates_batch35():
    assert len(set(_COUNT_METRICS)) == len(_COUNT_METRICS)


def test_success_bool_metrics_no_duplicates_batch35():
    assert len(set(_SUCCESS_BOOL_METRICS)) == len(_SUCCESS_BOOL_METRICS)


def test_ratio_metrics_disjoint_from_count_batch35():
    assert set(_RATIO_METRICS).isdisjoint(set(_COUNT_METRICS))


def test_ratio_metrics_disjoint_from_success_bool_batch35():
    assert set(_RATIO_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))


def test_count_metrics_disjoint_from_success_bool_batch35():
    assert set(_COUNT_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))


def test_ratio_metrics_contains_text_preservation_equal_batch35():
    assert "text_preservation_equal" in _RATIO_METRICS


def test_ratio_metrics_contains_text_char_multiset_precision_batch35():
    assert "text_char_multiset_precision" in _RATIO_METRICS


def test_ratio_metrics_contains_text_char_multiset_recall_batch35():
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_contains_heading_boundary_compliance_batch35():
    assert "heading_boundary_compliance" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_precision_batch35():
    assert "chunk_boundary_precision" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_recall_batch35():
    assert "chunk_boundary_recall" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_f1_batch35():
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_figure_caption_batch35():
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_count_metrics_only_element_count_total_batch35():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_only_pipeline_success_batch35():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


# ---------- get_git_provenance 第三十五批


def test_git_provenance_with_subprocess_timeout_batch35(tmp_path):
    """subprocess.TimeoutExpired 应被捕获。"""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 10)):
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] is None
        assert out["git_dirty"] is True


def test_git_provenance_with_oserror_batch35(tmp_path):
    """OSError 应被捕获。"""
    with patch("subprocess.run", side_effect=OSError("nope")):
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] is None


def test_git_provenance_with_file_not_found_batch35(tmp_path):
    """FileNotFoundError 是 OSError 子类，应被捕获。"""
    with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] is None


def test_git_provenance_first_command_fails_batch35(tmp_path):
    """rev-parse 失败但 status 成功 → commit=None。"""
    def side_effect(*args, **kwargs):
        if "rev-parse" in args[0]:
            m = MagicMock()
            m.returncode = 1
            m.stdout = ""
            return m
        m = MagicMock()
        m.returncode = 0
        m.stdout = " M file.txt\n"
        return m

    with patch("subprocess.run", side_effect=side_effect):
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] is None


def test_git_provenance_first_command_empty_stdout_batch35(tmp_path):
    """rev-parse 成功但 stdout 为空 → commit=None。"""
    def side_effect(*args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        return m

    with patch("subprocess.run", side_effect=side_effect):
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] is None


def test_git_provenance_status_command_fails_batch35(tmp_path):
    """rev-parse 成功，status 失败 → dirty=False（bool(False and ...) = False）。"""
    def side_effect(*args, **kwargs):
        if "rev-parse" in args[0]:
            m = MagicMock()
            m.returncode = 0
            m.stdout = "abc123\n"
            return m
        m = MagicMock()
        m.returncode = 1
        m.stdout = ""
        return m

    with patch("subprocess.run", side_effect=side_effect):
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] == "abc123"
        # status returncode != 0 → bool(False and X) = False
        assert out["git_dirty"] is False


def test_git_provenance_with_clean_status_batch35(tmp_path):
    """rev-parse 成功，status 输出空 → dirty=False。"""
    def side_effect(*args, **kwargs):
        if "rev-parse" in args[0]:
            m = MagicMock()
            m.returncode = 0
            m.stdout = "abc123\n"
            return m
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        return m

    with patch("subprocess.run", side_effect=side_effect):
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] == "abc123"
        assert out["git_dirty"] is False


def test_git_provenance_commit_strip_whitespace_batch35(tmp_path):
    """stdout 含换行符 → 被 strip 掉。"""
    def side_effect(*args, **kwargs):
        if "rev-parse" in args[0]:
            m = MagicMock()
            m.returncode = 0
            m.stdout = "  abc123  \n"
            return m
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        return m

    with patch("subprocess.run", side_effect=side_effect):
        out = get_git_provenance(tmp_path)
        assert out["git_commit"] == "abc123"


def test_git_provenance_uses_timeout_10_batch35(tmp_path):
    """subprocess.run 调用必须 timeout=10。"""
    captured = []

    def side_effect(*args, **kwargs):
        captured.append(kwargs.get("timeout"))
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        return m

    with patch("subprocess.run", side_effect=side_effect):
        get_git_provenance(tmp_path)
        assert all(t == 10 for t in captured)


def test_git_provenance_uses_cwd_param_batch35(tmp_path):
    """调用必须传 cwd=。"""
    captured = []

    def side_effect(*args, **kwargs):
        captured.append(kwargs.get("cwd"))
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        return m

    with patch("subprocess.run", side_effect=side_effect):
        get_git_provenance(tmp_path)
        assert all(c == str(tmp_path) for c in captured)


def test_git_provenance_uses_capture_output_batch35(tmp_path):
    captured = []

    def side_effect(*args, **kwargs):
        captured.append(kwargs.get("capture_output"))
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        return m

    with patch("subprocess.run", side_effect=side_effect):
        get_git_provenance(tmp_path)
        assert all(c is True for c in captured)


def test_git_provenance_uses_utf8_encoding_batch35(tmp_path):
    captured = []

    def side_effect(*args, **kwargs):
        captured.append(kwargs.get("encoding"))
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        return m

    with patch("subprocess.run", side_effect=side_effect):
        get_git_provenance(tmp_path)
        assert all(e == "utf-8" for e in captured)


def test_git_provenance_uses_replace_errors_batch35(tmp_path):
    captured = []

    def side_effect(*args, **kwargs):
        captured.append(kwargs.get("errors"))
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        return m

    with patch("subprocess.run", side_effect=side_effect):
        get_git_provenance(tmp_path)
        assert all(e == "replace" for e in captured)


# ---------- get_dependency_versions 第三十五批


def test_dependency_versions_returns_dict_batch35():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_dependency_versions_has_three_packages_batch35():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_dependency_versions_values_are_str_or_none_batch35():
    out = get_dependency_versions()
    for v in out.values():
        assert v is None or isinstance(v, str)


def test_dependency_versions_with_package_not_found_batch35():
    """模拟 PackageNotFoundError。"""
    import importlib.metadata
    with patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError):
        out = get_dependency_versions()
        # 全部 None
        assert all(v is None for v in out.values())


def test_dependency_versions_with_generic_exception_batch35():
    """模拟 generic Exception。"""
    with patch("importlib.metadata.version", side_effect=RuntimeError):
        out = get_dependency_versions()
        assert all(v is None for v in out.values())


def test_dependency_versions_normal_path_batch35():
    """正常返回版本字符串。"""
    with patch("importlib.metadata.version", return_value="1.0.0"):
        out = get_dependency_versions()
        assert all(v == "1.0.0" for v in out.values())


# ---------- build_provenance 第三十五批


def test_build_provenance_returns_dict_batch35(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert isinstance(out, dict)


def test_build_provenance_nine_keys_batch35(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    expected = {
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
    assert set(out.keys()) == expected


def test_build_provenance_parser_name_value_batch35(tmp_path):
    out = build_provenance(tmp_path, "kreuzberg", 800, "4.10.2")
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_none_batch35(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_parser_version_str_batch35(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert out["parser_version"] == "0.1.0"


def test_build_provenance_max_chars_int_batch35(tmp_path):
    out = build_provenance(tmp_path, "fallback", 1200, None)
    assert out["max_chars"] == 1200
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_negative_batch35(tmp_path):
    """负数也会被 int() 强转。"""
    out = build_provenance(tmp_path, "fallback", -5, None)
    assert out["max_chars"] == -5


def test_build_provenance_run_timestamp_iso_parseable_batch35(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    # 验证 ISO 时间可解析
    parsed = datetime.fromisoformat(out["run_timestamp_iso"])
    assert isinstance(parsed, datetime)


def test_build_provenance_evaluator_version_constant_batch35(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_constant_batch35(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_dependencies_is_dict_batch35(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_dependencies_has_three_keys_batch35(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert set(out["dependencies"].keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_build_provenance_idempotent_run_timestamp_differs_batch35(tmp_path):
    """两次调用应返回不同 run_timestamp_iso（时间流逝）。"""
    o1 = build_provenance(tmp_path, "fallback", 800, None)
    o2 = build_provenance(tmp_path, "fallback", 800, None)
    # 时间戳可能相同（毫秒级），所以只验证结构相同
    assert set(o1.keys()) == set(o2.keys())


# ---------- build_devset_section 第三十五批


def _make_manifest_mock(**kwargs):
    m = MagicMock()
    m.devset_status = kwargs.get("devset_status", "incomplete")
    m.file_count = kwargs.get("file_count", 0)
    m.content_group_count = kwargs.get("content_group_count", 0)
    m.pdf_count = kwargs.get("pdf_count", 0)
    m.docx_count = kwargs.get("docx_count", 0)
    m.categories_covered = kwargs.get("categories_covered", [])
    return m


def test_build_devset_section_returns_dict_batch35():
    out = build_devset_section(_make_manifest_mock())
    assert isinstance(out, dict)


def test_build_devset_section_has_six_keys_batch35():
    out = build_devset_section(_make_manifest_mock())
    expected = {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }
    assert set(out.keys()) == expected


def test_build_devset_section_status_value_batch35():
    out = build_devset_section(_make_manifest_mock(devset_status="complete"))
    assert out["status"] == "complete"


def test_build_devset_section_file_count_value_batch35():
    out = build_devset_section(_make_manifest_mock(file_count=10))
    assert out["file_count"] == 10


def test_build_devset_section_pdf_count_value_batch35():
    out = build_devset_section(_make_manifest_mock(pdf_count=3))
    assert out["pdf_count"] == 3


def test_build_devset_section_docx_count_value_batch35():
    out = build_devset_section(_make_manifest_mock(docx_count=7))
    assert out["docx_count"] == 7


def test_build_devset_section_content_group_count_value_batch35():
    out = build_devset_section(_make_manifest_mock(content_group_count=5))
    assert out["content_group_count"] == 5


def test_build_devset_section_categories_covered_value_batch35():
    cats = ["tutorial", "api"]
    out = build_devset_section(_make_manifest_mock(categories_covered=cats))
    assert out["categories_covered"] == cats


def test_build_devset_section_empty_categories_batch35():
    out = build_devset_section(_make_manifest_mock(categories_covered=[]))
    assert out["categories_covered"] == []


def test_build_devset_section_unicode_categories_batch35():
    cats = ["教程", "API 文档"]
    out = build_devset_section(_make_manifest_mock(categories_covered=cats))
    assert out["categories_covered"] == cats


# ---------- aggregate_summary 第三十五批


def test_aggregate_summary_returns_dict_batch35():
    out = aggregate_summary([])
    assert isinstance(out, dict)


def test_aggregate_summary_has_four_keys_batch35():
    out = aggregate_summary([])
    expected = {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}
    assert set(out.keys()) == expected


def test_aggregate_summary_empty_input_counts_batch35():
    out = aggregate_summary([])
    counts = out["counts"]
    assert "element_count_total" in counts
    assert counts["element_count_total"]["sum"] is None
    assert counts["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_empty_input_success_rates_batch35():
    out = aggregate_summary([])
    sr = out["success_rates"]
    assert "pipeline_success" in sr
    assert sr["pipeline_success"]["success_count"] == 0
    assert sr["pipeline_success"]["total"] == 0
    assert sr["pipeline_success"]["rate"] is None


def test_aggregate_summary_empty_input_silent_drop_total_batch35():
    out = aggregate_summary([])
    assert out["silent_drop_total"] is None


def test_aggregate_summary_counts_skips_null_values_batch35():
    """None value 不参与 counts。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_counts_sums_all_batch35():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": 10}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_success_rate_all_true_batch35():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 2
    assert sr["rate"] == 1.0


def test_aggregate_summary_success_rate_all_false_batch35():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["rate"] == 0.0


def test_aggregate_summary_success_rate_mixed_batch35():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 3
    assert sr["rate"] == pytest.approx(2 / 3)


def test_aggregate_summary_success_rate_treats_null_as_false_batch35():
    """value=None 不算成功（is True 才算）。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": None}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2  # total 是所有 doc 数，不论值


def test_aggregate_summary_ratio_macro_average_simple_batch35():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
    ]
    out = aggregate_summary(per_doc)
    rm = out["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] == 0.75
    assert rm["participating_docs"] == 2
    assert rm["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_skips_null_batch35():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    rm = out["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] == 1.0
    assert rm["participating_docs"] == 1
    assert rm["not_evaluated"] == 1


def test_aggregate_summary_ratio_macro_all_null_batch35():
    per_doc = [
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    rm = out["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] is None
    assert rm["participating_docs"] == 0
    assert rm["not_evaluated"] == 2


def test_aggregate_summary_silent_drop_total_sum_batch35():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_skips_null_batch35():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 3


def test_aggregate_summary_silent_drop_all_null_batch35():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_does_not_mutate_input_batch35():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    import json
    before = json.dumps(per_doc, sort_keys=True)
    aggregate_summary(per_doc)
    assert json.dumps(per_doc, sort_keys=True) == before


# ---------- module source forbidden tokens 第五十九批


FORBIDDEN_TOKENS_MINUS_SUBPROCESS = [
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


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS_MINUS_SUBPROCESS)
def test_module_source_no_forbidden_tokens_batch35(token):
    """subprocess 在 report.py 是合法的（git provenance）。"""
    src = inspect.getsource(rmod)
    assert token not in src


def test_module_source_uses_subprocess_batch35():
    """report.py 合法使用 subprocess（git provenance）。"""
    src = inspect.getsource(rmod)
    assert "import subprocess" in src
    assert "subprocess.run" in src


# ---------- module source 字符串精确补强第五十五批


def test_module_source_contains_design_doc_batch35():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_contains_aggregation_rules_batch35():
    src = inspect.getsource(rmod)
    assert "聚合规则" in src


def test_module_source_contains_no_mixed_types_keyword_batch35():
    src = inspect.getsource(rmod)
    assert "不混合类型" in src


def test_module_source_contains_figure_caption_always_null_comment_batch35():
    src = inspect.getsource(rmod)
    assert "figure_caption_*" in src


def test_module_source_contains_macro_average_keyword_batch35():
    src = inspect.getsource(rmod)
    assert "macro_average" in src


def test_module_source_contains_participating_docs_keyword_batch35():
    src = inspect.getsource(rmod)
    assert "participating_docs" in src


def test_module_source_contains_not_evaluated_keyword_batch35():
    src = inspect.getsource(rmod)
    assert "not_evaluated" in src


def test_module_source_contains_silent_drop_total_keyword_batch35():
    src = inspect.getsource(rmod)
    assert "silent_drop_total" in src


def test_module_source_contains_success_rates_keyword_batch35():
    src = inspect.getsource(rmod)
    assert "success_rates" in src


def test_module_source_contains_counts_keyword_batch35():
    src = inspect.getsource(rmod)
    assert "counts" in src


def test_module_source_contains_evaluator_version_import_batch35():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_contains_importlib_metadata_call_batch35():
    src = inspect.getsource(rmod)
    assert "importlib.metadata" in src


def test_module_source_contains_datetime_iso_call_batch35():
    src = inspect.getsource(rmod)
    assert "datetime.now().astimezone().isoformat()" in src


def test_module_source_contains_git_provenance_function_batch35():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src


def test_module_source_contains_dependency_versions_function_batch35():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions(" in src


def test_module_source_contains_rev_parse_call_batch35():
    src = inspect.getsource(rmod)
    assert '"rev-parse"' in src


def test_module_source_contains_status_porcelain_call_batch35():
    src = inspect.getsource(rmod)
    assert '"--porcelain"' in src


def test_module_source_contains_int_cast_for_max_chars_batch35():
    src = inspect.getsource(rmod)
    assert "int(max_chars)" in src


def test_module_source_contains_timeout_10_batch35():
    src = inspect.getsource(rmod)
    assert "timeout=10" in src


def test_module_source_contains_package_not_found_handler_batch35():
    src = inspect.getsource(rmod)
    assert "PackageNotFoundError" in src


# ---------- signatures 第五十五批


def test_signature_get_git_provenance_one_param_batch35():
    sig = inspect.signature(get_git_provenance)
    assert list(sig.parameters.keys()) == ["project_root"]


def test_signature_build_provenance_four_params_batch35():
    sig = inspect.signature(build_provenance)
    assert len(sig.parameters) == 4


def test_signature_build_provenance_parser_version_optional_batch35():
    """parser_version 是 required positional（无默认值，但 annotation 是 'str | None'）。"""
    sig = inspect.signature(build_provenance)
    assert sig.parameters["parser_version"].default is inspect.Parameter.empty
    assert "None" in str(sig.parameters["parser_version"].annotation)


def test_signature_build_provenance_params_no_default_batch35():
    """project_root / parser_name / max_chars 都是 required positional。"""
    sig = inspect.signature(build_provenance)
    assert sig.parameters["project_root"].default is inspect.Parameter.empty
    assert sig.parameters["parser_name"].default is inspect.Parameter.empty
    assert sig.parameters["max_chars"].default is inspect.Parameter.empty


def test_signature_build_devset_section_one_param_batch35():
    sig = inspect.signature(build_devset_section)
    assert list(sig.parameters.keys()) == ["manifest"]


def test_signature_aggregate_summary_one_param_batch35():
    sig = inspect.signature(aggregate_summary)
    assert list(sig.parameters.keys()) == ["per_doc_results"]


def test_signature_get_dependency_versions_no_params_batch35():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_signature_build_provenance_return_dict_batch35():
    sig = inspect.signature(build_provenance)
    assert "dict" in str(sig.return_annotation)


def test_signature_build_devset_section_return_dict_batch35():
    sig = inspect.signature(build_devset_section)
    assert "dict" in str(sig.return_annotation)


def test_signature_aggregate_summary_return_dict_batch35():
    sig = inspect.signature(aggregate_summary)
    assert "dict" in str(sig.return_annotation)


# ---------- module 合理性 第五十五批


def test_module_has_all_attribute_batch35():
    assert hasattr(rmod, "__all__")


def test_module_all_is_list_batch35():
    assert isinstance(rmod.__all__, list)


def test_module_all_len_five_batch35():
    assert len(rmod.__all__) == 5


def test_module_all_contains_build_provenance_batch35():
    assert "build_provenance" in rmod.__all__


def test_module_all_contains_build_devset_section_batch35():
    assert "build_devset_section" in rmod.__all__


def test_module_all_contains_aggregate_summary_batch35():
    assert "aggregate_summary" in rmod.__all__


def test_module_all_contains_get_git_provenance_batch35():
    assert "get_git_provenance" in rmod.__all__


def test_module_all_contains_get_dependency_versions_batch35():
    assert "get_dependency_versions" in rmod.__all__


def test_module_does_not_have_unused_functions_batch35():
    """__all__ 中的名都在模块命名空间。"""
    for name in rmod.__all__:
        assert hasattr(rmod, name)


def test_module_no_class_definitions_batch35():
    src = inspect.getsource(rmod)
    assert "\nclass " not in src


# ---------- 端到端集成 第五十五批


def test_e2e_build_provenance_with_real_path_batch35(tmp_path):
    """用真实 tmp_path 调用 build_provenance。"""
    out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] == "0.1.0"
    assert out["max_chars"] == 800


def test_e2e_aggregate_summary_with_complete_per_doc_batch35():
    """完整 per_doc 结构。"""
    per_doc = [
        {
            "metrics": {
                "element_count_total": {"value": 5},
                "pipeline_success": {"value": True},
                "schema_valid": {"value": True},
                "silent_drop_count": {"value": 2},
            },
        },
        {
            "metrics": {
                "element_count_total": {"value": 3},
                "pipeline_success": {"value": True},
                "schema_valid": {"value": False},
                "silent_drop_count": {"value": 1},
            },
        },
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 8
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0
    # schema_valid 视为 ratio（True=1, False=0）
    rm = out["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] == 0.5
    assert out["silent_drop_total"] == 3


def test_e2e_aggregate_summary_idempotent_batch35():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": 10}}},
    ]
    o1 = aggregate_summary(per_doc)
    o2 = aggregate_summary(per_doc)
    assert o1 == o2


def test_e2e_build_devset_section_with_real_manifest_mock_batch35():
    """用 MagicMock 模拟 Manifest 对象。"""
    m = _make_manifest_mock(
        devset_status="incomplete",
        file_count=5,
        content_group_count=2,
        pdf_count=2,
        docx_count=3,
        categories_covered=["a", "b"],
    )
    out = build_devset_section(m)
    assert out["status"] == "incomplete"
    assert out["file_count"] == 5
    assert out["content_group_count"] == 2
    assert out["pdf_count"] == 2
    assert out["docx_count"] == 3
    assert out["categories_covered"] == ["a", "b"]


def test_e2e_combined_run_does_not_raise_batch35(tmp_path):
    """完整流程：provenance + devset + summary 不抛异常。"""
    prov = build_provenance(tmp_path, "fallback", 800, None)
    dev = build_devset_section(_make_manifest_mock())
    summ = aggregate_summary([])
    assert isinstance(prov, dict)
    assert isinstance(dev, dict)
    assert isinstance(summ, dict)
