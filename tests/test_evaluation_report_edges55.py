"""evaluation/report.py 第五十五轮 edges 测试（Round 590）。

补强 edges54 未触及的角度（第三十六批）。
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第三十六批


def test_ratio_metrics_is_tuple_batch36():
    assert isinstance(_RATIO_METRICS, tuple)


def test_count_metrics_is_tuple_batch36():
    assert isinstance(_COUNT_METRICS, tuple)


def test_success_bool_metrics_is_tuple_batch36():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_ratio_metrics_first_schema_valid_batch36():
    assert _RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_last_chunk_boundary_f1_batch36():
    assert _RATIO_METRICS[-1] == "chunk_boundary_f1"


def test_ratio_metrics_contains_schema_valid_batch36():
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_contains_pdf_locator_batch36():
    assert "pdf_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_docx_locator_batch36():
    assert "docx_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_image_resource_batch36():
    assert "image_resource_exists_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_reference_batch36():
    assert "chunk_reference_intact_ratio" in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_element_count_total_batch36():
    assert "element_count_total" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_pipeline_success_batch36():
    assert "pipeline_success" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_silent_drop_count_batch36():
    assert "silent_drop_count" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_error_code_batch36():
    assert "error_code" not in _RATIO_METRICS


def test_count_metrics_first_element_count_total_batch36():
    assert _COUNT_METRICS[0] == "element_count_total"


def test_count_metrics_len_one_batch36():
    assert len(_COUNT_METRICS) == 1


def test_success_bool_metrics_first_pipeline_success_batch36():
    assert _SUCCESS_BOOL_METRICS[0] == "pipeline_success"


def test_success_bool_metrics_len_one_batch36():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_count_metrics_all_strings_batch36():
    for name in _COUNT_METRICS:
        assert isinstance(name, str)


def test_success_bool_metrics_all_strings_batch36():
    for name in _SUCCESS_BOOL_METRICS:
        assert isinstance(name, str)


def test_ratio_metrics_count_12_batch36():
    """12 个 ratio 指标。"""
    assert len(_RATIO_METRICS) == 12


# ---------- get_git_provenance 第三十六批


def test_git_provenance_callable_batch36():
    assert callable(get_git_provenance)


def test_git_provenance_returns_dict_batch36(tmp_path):
    with patch("subprocess.run"):
        out = get_git_provenance(tmp_path)
    assert isinstance(out, dict)


def test_git_provenance_dict_has_two_keys_batch36(tmp_path):
    with patch("subprocess.run"):
        out = get_git_provenance(tmp_path)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_git_provenance_with_subprocess_error_batch36(tmp_path):
    """subprocess.SubprocessError 应被捕获。"""
    with patch("subprocess.run", side_effect=subprocess.SubprocessError("err")):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_git_provenance_returns_str_or_none_for_commit_batch36(tmp_path):
    with patch("subprocess.run"):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None or isinstance(out["git_commit"], str)


def test_git_provenance_returns_bool_for_dirty_batch36(tmp_path):
    with patch("subprocess.run"):
        out = get_git_provenance(tmp_path)
    assert isinstance(out["git_dirty"], bool)


def test_git_provenance_normal_clean_path_batch36(tmp_path):
    """正常路径：commit + clean working tree。"""
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        if "rev-parse" in cmd:
            m.returncode = 0
            m.stdout = "deadbeefcafe\n"
        else:
            m.returncode = 0
            m.stdout = ""
        return m
    with patch("subprocess.run", side_effect=side_effect):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "deadbeefcafe"
    assert out["git_dirty"] is False


def test_git_provenance_normal_dirty_path_batch36(tmp_path):
    """正常路径：commit + dirty working tree。"""
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        if "rev-parse" in cmd:
            m.returncode = 0
            m.stdout = "deadbeef\n"
        else:
            m.returncode = 0
            m.stdout = " M file.txt\n"
        return m
    with patch("subprocess.run", side_effect=side_effect):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "deadbeef"
    assert out["git_dirty"] is True


def test_git_provenance_commit_with_whitespace_only_batch36(tmp_path):
    """rev-parse stdout 是纯空白 → strip() 后为空 → commit=None。"""
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        m.stdout = "   \n\t  "
        return m
    with patch("subprocess.run", side_effect=side_effect):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_git_provenance_uses_cwd_param_batch36(tmp_path):
    """subprocess.run 必须传 cwd 参数。"""
    captured = {}
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        captured["kwargs"] = kwargs
        return m
    with patch("subprocess.run", side_effect=side_effect):
        get_git_provenance(tmp_path)
    assert "cwd" in captured["kwargs"]
    assert captured["kwargs"]["cwd"] == str(tmp_path)


def test_git_provenance_uses_capture_output_param_batch36(tmp_path):
    """subprocess.run 必须传 capture_output=True。"""
    captured = {}
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        captured["kwargs"] = kwargs
        return m
    with patch("subprocess.run", side_effect=side_effect):
        get_git_provenance(tmp_path)
    assert captured["kwargs"].get("capture_output") is True


def test_git_provenance_uses_timeout_param_batch36(tmp_path):
    """subprocess.run 必须传 timeout=10。"""
    captured = {}
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        captured["kwargs"] = kwargs
        return m
    with patch("subprocess.run", side_effect=side_effect):
        get_git_provenance(tmp_path)
    assert captured["kwargs"].get("timeout") == 10


def test_git_provenance_uses_utf8_encoding_batch36(tmp_path):
    """subprocess.run 必须传 encoding='utf-8'。"""
    captured = {}
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        captured["kwargs"] = kwargs
        return m
    with patch("subprocess.run", side_effect=side_effect):
        get_git_provenance(tmp_path)
    assert captured["kwargs"].get("encoding") == "utf-8"


# ---------- get_dependency_versions 第三十六批


def test_dependency_versions_callable_batch36():
    assert callable(get_dependency_versions)


def test_dependency_versions_contains_pdfplumber_batch36():
    out = get_dependency_versions()
    assert "pdfplumber" in out


def test_dependency_versions_contains_python_docx_batch36():
    out = get_dependency_versions()
    assert "python-docx" in out


def test_dependency_versions_contains_pypdfium2_batch36():
    out = get_dependency_versions()
    assert "pypdfium2" in out


def test_dependency_versions_only_three_keys_batch36():
    out = get_dependency_versions()
    assert len(out) == 3


def test_dependency_versions_partial_failure_batch36():
    """pdfplumber 找到，python-docx 抛 PackageNotFoundError，pypdfium2 抛 generic。"""
    import importlib.metadata
    call_count = {"n": 0}
    def side_effect(pkg):
        call_count["n"] += 1
        if pkg == "pdfplumber":
            return "1.0.0"
        if pkg == "python-docx":
            raise importlib.metadata.PackageNotFoundError(pkg)
        raise RuntimeError("boom")
    with patch("importlib.metadata.version", side_effect=side_effect):
        out = get_dependency_versions()
    assert out["pdfplumber"] == "1.0.0"
    assert out["python-docx"] is None
    assert out["pypdfium2"] is None


def test_dependency_versions_does_not_raise_batch36():
    """任何异常都被吞掉；返回 dict。"""
    with patch("importlib.metadata.version", side_effect=ValueError):
        out = get_dependency_versions()
    assert isinstance(out, dict)


def test_dependency_versions_does_not_accept_arguments_batch36():
    """get_dependency_versions() 不接受参数。"""
    sig = inspect.signature(get_dependency_versions)
    assert list(sig.parameters.keys()) == []


# ---------- build_provenance 第三十六批


def test_build_provenance_callable_batch36():
    assert callable(build_provenance)


def test_build_provenance_returns_git_commit_field_batch36(tmp_path):
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert "git_commit" in out


def test_build_provenance_returns_git_dirty_field_batch36(tmp_path):
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert "git_dirty" in out


def test_build_provenance_dependencies_field_correct_batch36(tmp_path):
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert set(out["dependencies"].keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_build_provenance_max_chars_str_input_batch36(tmp_path):
    """str '800' 会被 int() 强转。"""
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", "800", None)  # type: ignore[arg-type]
    assert out["max_chars"] == 800


def test_build_provenance_max_chars_zero_batch36(tmp_path):
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 0, None)
    assert out["max_chars"] == 0


def test_build_provenance_run_timestamp_iso_format_batch36(tmp_path):
    """run_timestamp_iso 必须含 'T'（ISO 时间分隔符）。"""
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert "T" in out["run_timestamp_iso"]


def test_build_provenance_run_timestamp_iso_contains_timezone_batch36(tmp_path):
    """run_timestamp_iso 必须含时区偏移（+ 或 -）。"""
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 800, None)
    # astimezone() 后会带本地时区 +HH:MM 或 -HH:MM
    assert "+" in out["run_timestamp_iso"] or out["run_timestamp_iso"].count("-") > 1


def test_build_provenance_evaluator_version_is_str_batch36(tmp_path):
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["evaluator_version"], str)


def test_build_provenance_report_version_is_str_batch36(tmp_path):
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["report_version"], str)


def test_build_provenance_signature_batch36():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root", "parser_name", "max_chars", "parser_version"]


# ---------- build_devset_section 第三十六批


def _make_manifest_mock(**kwargs):
    m = MagicMock()
    m.devset_status = kwargs.get("devset_status", "incomplete")
    m.file_count = kwargs.get("file_count", 0)
    m.content_group_count = kwargs.get("content_group_count", 0)
    m.pdf_count = kwargs.get("pdf_count", 0)
    m.docx_count = kwargs.get("docx_count", 0)
    m.categories_covered = kwargs.get("categories_covered", [])
    return m


def test_build_devset_section_callable_batch36():
    assert callable(build_devset_section)


def test_build_devset_section_signature_one_param_batch36():
    sig = inspect.signature(build_devset_section)
    assert list(sig.parameters.keys()) == ["manifest"]


def test_build_devset_section_status_default_batch36():
    out = build_devset_section(_make_manifest_mock())
    assert out["status"] == "incomplete"


def test_build_devset_section_status_complete_batch36():
    out = build_devset_section(_make_manifest_mock(devset_status="complete"))
    assert out["status"] == "complete"


def test_build_devset_section_file_count_zero_batch36():
    out = build_devset_section(_make_manifest_mock(file_count=0))
    assert out["file_count"] == 0


def test_build_devset_section_file_count_huge_batch36():
    out = build_devset_section(_make_manifest_mock(file_count=10**6))
    assert out["file_count"] == 10**6


def test_build_devset_section_pdf_plus_docx_eq_file_count_batch36():
    """pdf + docx 通常等于 file_count（但函数不强校验）。"""
    out = build_devset_section(_make_manifest_mock(
        file_count=5, pdf_count=2, docx_count=3
    ))
    assert out["pdf_count"] + out["docx_count"] == out["file_count"]


def test_build_devset_section_unicode_status_batch36():
    out = build_devset_section(_make_manifest_mock(devset_status="测试"))
    assert out["status"] == "测试"


def test_build_devset_section_categories_with_int_batch36():
    """categories_covered 接受任意可迭代（不强校验类型）。"""
    cats = [1, 2, 3]
    out = build_devset_section(_make_manifest_mock(categories_covered=cats))
    assert out["categories_covered"] == cats


def test_build_devset_section_signature_return_dict_batch36():
    sig = inspect.signature(build_devset_section)
    assert "dict" in str(sig.return_annotation)


# ---------- aggregate_summary 第三十六批


def test_aggregate_summary_callable_batch36():
    assert callable(aggregate_summary)


def test_aggregate_summary_signature_one_param_batch36():
    sig = inspect.signature(aggregate_summary)
    assert list(sig.parameters.keys()) == ["per_doc_results"]


def test_aggregate_summary_returns_dict_batch36():
    out = aggregate_summary([])
    assert isinstance(out, dict)


def test_aggregate_summary_empty_input_all_macros_none_batch36():
    """空输入 → 每个 ratio 指标 macro_average 是 None。"""
    out = aggregate_summary([])
    for name in _RATIO_METRICS:
        assert out["ratio_macro_averages"][name]["macro_average"] is None
        assert out["ratio_macro_averages"][name]["participating_docs"] == 0
        assert out["ratio_macro_averages"][name]["not_evaluated"] == 0


def test_aggregate_summary_counts_missing_field_batch36():
    """metrics 缺 element_count_total 键 → 不参与。"""
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_counts_metrics_missing_raises_batch36():
    """per_doc 完全无 metrics 键 → 抛 KeyError（直接 r["metrics"] 访问）。"""
    per_doc = [{}]
    with pytest.raises(KeyError):
        aggregate_summary(per_doc)


def test_aggregate_summary_counts_zero_values_included_batch36():
    """value=0 不是 None → 参与（None 才被排除）。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 0}}},
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_success_rate_empty_input_batch36():
    out = aggregate_summary([])
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 0
    assert sr["rate"] is None


def test_aggregate_summary_success_rate_one_doc_true_batch36():
    per_doc = [{"metrics": {"pipeline_success": {"value": True}}}]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 1
    assert sr["rate"] == 1.0


def test_aggregate_summary_success_rate_one_doc_false_batch36():
    per_doc = [{"metrics": {"pipeline_success": {"value": False}}}]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 1
    assert sr["rate"] == 0.0


def test_aggregate_summary_success_rate_with_none_value_batch36():
    """value=None 不算成功，但 total 仍计 1。"""
    per_doc = [{"metrics": {"pipeline_success": {"value": None}}}]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 1
    assert sr["rate"] == 0.0


def test_aggregate_summary_ratio_macro_all_participating_batch36():
    """所有 docs 都贡献 ratio → macro = mean。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
    ]
    out = aggregate_summary(per_doc)
    schema = out["ratio_macro_averages"]["schema_valid"]
    assert schema["macro_average"] == 0.75
    assert schema["participating_docs"] == 2
    assert schema["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_some_not_evaluated_batch36():
    """部分 docs 不贡献 → not_evaluated > 0。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    schema = out["ratio_macro_averages"]["schema_valid"]
    assert schema["macro_average"] == 1.0
    assert schema["participating_docs"] == 1
    assert schema["not_evaluated"] == 1


def test_aggregate_summary_ratio_macro_zero_value_included_batch36():
    """value=0.0 是合法参与值（None 才排除）。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.0}}},
        {"metrics": {"schema_valid": {"value": 1.0}}},
    ]
    out = aggregate_summary(per_doc)
    schema = out["ratio_macro_averages"]["schema_valid"]
    assert schema["macro_average"] == 0.5
    assert schema["participating_docs"] == 2


def test_aggregate_summary_silent_drop_sum_total_batch36():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_skips_none_batch36():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 3


def test_aggregate_summary_silent_drop_all_none_returns_none_batch36():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_does_not_mutate_input_batch36():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    import json
    before = json.dumps(per_doc, sort_keys=True)
    aggregate_summary(per_doc)
    assert json.dumps(per_doc, sort_keys=True) == before


def test_aggregate_summary_signature_return_dict_batch36():
    sig = inspect.signature(aggregate_summary)
    assert "dict" in str(sig.return_annotation)


def test_aggregate_summary_macro_average_is_float_or_none_batch36():
    out = aggregate_summary([])
    for name in _RATIO_METRICS:
        v = out["ratio_macro_averages"][name]["macro_average"]
        assert v is None or isinstance(v, float)


# ---------- module source forbidden tokens 第六十四批


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
def test_module_source_no_forbidden_tokens_batch36(token):
    """report.py 允许 subprocess（git provenance 必需），其余 token 仍被禁。"""
    src = inspect.getsource(rmod)
    assert token not in src


def test_module_source_does_contain_subprocess_import_batch36():
    """report.py 允许 subprocess（git provenance 必需）。"""
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


# ---------- module source 字符串精确补强第六十批


def test_module_source_contains_design_doc_batch36():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_contains_no_mixed_score_comment_batch36():
    src = inspect.getsource(rmod)
    assert "不混合类型" in src


def test_module_source_contains_counts_aggregation_comment_batch36():
    src = inspect.getsource(rmod)
    assert "counts" in src


def test_module_source_contains_success_rates_comment_batch36():
    src = inspect.getsource(rmod)
    assert "success_rates" in src


def test_module_source_contains_ratio_macro_comment_batch36():
    src = inspect.getsource(rmod)
    assert "ratio_macro_averages" in src


def test_module_source_contains_silent_drop_comment_batch36():
    src = inspect.getsource(rmod)
    assert "silent_drop_count" in src


def test_module_source_contains_ratio_metrics_definition_batch36():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS" in src


def test_module_source_contains_count_metrics_definition_batch36():
    src = inspect.getsource(rmod)
    assert "_COUNT_METRICS" in src


def test_module_source_contains_success_bool_metrics_definition_batch36():
    src = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS" in src


def test_module_source_contains_get_git_provenance_batch36():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src


def test_module_source_contains_get_dependency_versions_batch36():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions(" in src


def test_module_source_contains_build_provenance_batch36():
    src = inspect.getsource(rmod)
    assert "def build_provenance(" in src


def test_module_source_contains_build_devset_section_batch36():
    src = inspect.getsource(rmod)
    assert "def build_devset_section(" in src


def test_module_source_contains_aggregate_summary_batch36():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary(" in src


def test_module_source_contains_subprocess_run_call_batch36():
    src = inspect.getsource(rmod)
    assert "subprocess.run(" in src


def test_module_source_contains_encoding_utf8_batch36():
    src = inspect.getsource(rmod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_errors_replace_batch36():
    src = inspect.getsource(rmod)
    assert 'errors="replace"' in src


def test_module_source_contains_timeout_value_batch36():
    src = inspect.getsource(rmod)
    assert "timeout=10" in src


def test_module_source_contains_pathlib_path_import_batch36():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch36():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_contains_datetime_import_batch36():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_contains_evaluator_version_import_batch36():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


# ---------- signatures 第六十批


def test_signature_get_git_provenance_one_param_batch36():
    sig = inspect.signature(get_git_provenance)
    assert list(sig.parameters.keys()) == ["project_root"]


def test_signature_get_git_provenance_return_dict_batch36():
    sig = inspect.signature(get_git_provenance)
    assert "dict" in str(sig.return_annotation)


def test_signature_get_dependency_versions_no_param_batch36():
    sig = inspect.signature(get_dependency_versions)
    assert list(sig.parameters.keys()) == []


def test_signature_build_provenance_no_default_for_parser_version_batch36():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["parser_version"].default is inspect.Parameter.empty


def test_signature_build_provenance_no_default_for_parser_name_batch36():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["parser_name"].default is inspect.Parameter.empty


def test_signature_build_provenance_no_default_for_max_chars_batch36():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["max_chars"].default is inspect.Parameter.empty


def test_signature_build_provenance_no_default_for_project_root_batch36():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["project_root"].default is inspect.Parameter.empty


# ---------- module 合理性 第六十批


def test_module_has_all_attribute_batch36():
    assert hasattr(rmod, "__all__")


def test_module_all_is_list_batch36():
    assert isinstance(rmod.__all__, list)


def test_module_all_len_five_batch36():
    assert len(rmod.__all__) == 5


def test_module_all_contains_build_provenance_batch36():
    assert "build_provenance" in rmod.__all__


def test_module_all_contains_build_devset_section_batch36():
    assert "build_devset_section" in rmod.__all__


def test_module_all_contains_aggregate_summary_batch36():
    assert "aggregate_summary" in rmod.__all__


def test_module_all_contains_get_git_provenance_batch36():
    assert "get_git_provenance" in rmod.__all__


def test_module_all_contains_get_dependency_versions_batch36():
    assert "get_dependency_versions" in rmod.__all__


def test_module_does_not_define_class_batch36():
    src = inspect.getsource(rmod)
    assert "\nclass " not in src


def test_module_does_not_export_private_metrics_batch36():
    for name in ("_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"):
        assert name not in rmod.__all__


def test_module_has_future_annotations_batch36():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


# ---------- 端到端集成 第六十批


def test_e2e_build_provenance_full_round_trip_batch36(tmp_path):
    """build_provenance 正常路径返回完整结构。"""
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        if "rev-parse" in cmd:
            m.stdout = "abc123def\n"
        else:
            m.stdout = ""
        return m
    with patch("subprocess.run", side_effect=side_effect):
        out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert out["git_commit"] == "abc123def"
    assert out["git_dirty"] is False
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] == "0.1.0"
    assert out["max_chars"] == 800
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION
    parsed = datetime.fromisoformat(out["run_timestamp_iso"])
    assert isinstance(parsed, datetime)


def test_e2e_aggregate_summary_with_full_metrics_batch36():
    """aggregate_summary 处理完整 metrics dict。"""
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "schema_valid": {"value": True},
                "element_count_total": {"value": 5},
                "silent_drop_count": {"value": 2},
                "pdf_locator_valid_ratio": {"value": 1.0},
                "image_resource_exists_ratio": {"value": 0.5},
            }
        },
        {
            "metrics": {
                "pipeline_success": {"value": False},
                "schema_valid": {"value": None},
                "element_count_total": {"value": 3},
                "silent_drop_count": {"value": None},
                "pdf_locator_valid_ratio": {"value": 0.0},
                "image_resource_exists_ratio": {"value": 1.0},
            }
        },
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 8
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["total"] == 2
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 0.5
    assert out["ratio_macro_averages"]["image_resource_exists_ratio"]["macro_average"] == 0.75
    assert out["silent_drop_total"] == 2


def test_e2e_idempotent_aggregate_summary_batch36():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    o1 = aggregate_summary(per_doc)
    o2 = aggregate_summary(per_doc)
    assert o1 == o2


def test_e2e_aggregate_summary_json_serializable_batch36():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    import json
    json.dumps(out, ensure_ascii=False)


def test_e2e_build_devset_then_aggregate_consistent_batch36():
    """build_devset_section + aggregate_summary 协同（不互扰）。"""
    m = _make_manifest_mock(file_count=2, pdf_count=1, docx_count=1)
    devset = build_devset_section(m)
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    summary = aggregate_summary(per_doc)
    assert devset["file_count"] == 2
    assert summary["success_rates"]["pipeline_success"]["success_count"] == 2
