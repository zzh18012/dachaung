"""evaluation/report.py 第五十三轮 edges 测试（Round 577）。

补强 edges52 未触及的角度（第三十四批）。
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第三十四批


def test_ratio_metrics_first_is_schema_valid_batch34():
    """第一个 ratio metric 是 schema_valid。"""
    assert _RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_last_is_chunk_boundary_f1_batch34():
    """最后一个 ratio metric 是 chunk_boundary_f1。"""
    assert _RATIO_METRICS[-1] == "chunk_boundary_f1"


def test_ratio_metrics_is_tuple_batch34():
    assert isinstance(_RATIO_METRICS, tuple)


def test_count_metrics_is_tuple_batch34():
    assert isinstance(_COUNT_METRICS, tuple)


def test_success_bool_metrics_is_tuple_batch34():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_ratio_metrics_contains_pdf_locator_batch34():
    assert "pdf_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_docx_locator_batch34():
    assert "docx_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_image_resource_batch34():
    assert "image_resource_exists_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_reference_batch34():
    assert "chunk_reference_intact_ratio" in _RATIO_METRICS


def test_count_metrics_count_1_batch34():
    assert len(_COUNT_METRICS) == 1


def test_success_bool_metrics_count_1_batch34():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_ratio_metrics_not_contains_silent_drop_count_batch34():
    assert "silent_drop_count" not in _RATIO_METRICS


def test_count_metrics_not_contains_pipeline_success_batch34():
    assert "pipeline_success" not in _COUNT_METRICS


def test_success_bool_metrics_not_contains_element_count_batch34():
    assert "element_count_total" not in _SUCCESS_BOOL_METRICS


# ---------- get_git_provenance 第三十四批


def test_git_provenance_returns_two_keys_batch34(tmp_path):
    out = get_git_provenance(tmp_path)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_git_provenance_default_dirty_true_batch34(tmp_path):
    """dirty 默认 True（除非 git status --porcelain 输出空 + returncode=0）。"""
    with patch("evaluation.report.subprocess.run") as m:
        m.side_effect = OSError("fail")
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


def test_git_provenance_commit_str_or_none_batch34(tmp_path):
    with patch("evaluation.report.subprocess.run") as m:
        # 第一个返回 commit，第二个返回 dirty
        m1 = MagicMock(returncode=0, stdout="abc123\n")
        m2 = MagicMock(returncode=0, stdout="")
        m.side_effect = [m1, m2]
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"


def test_git_provenance_dirty_when_status_nonempty_batch34(tmp_path):
    with patch("evaluation.report.subprocess.run") as m:
        m1 = MagicMock(returncode=0, stdout="abc")
        m2 = MagicMock(returncode=0, stdout=" M file.txt\n")
        m.side_effect = [m1, m2]
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


def test_git_provenance_clean_if_porcelain_empty_batch34(tmp_path):
    with patch("evaluation.report.subprocess.run") as m:
        m1 = MagicMock(returncode=0, stdout="abc")
        m2 = MagicMock(returncode=0, stdout="")
        m.side_effect = [m1, m2]
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_git_provenance_commit_none_when_returncode_nonzero_batch34(tmp_path):
    with patch("evaluation.report.subprocess.run") as m:
        m1 = MagicMock(returncode=1, stdout="")
        m2 = MagicMock(returncode=0, stdout="")
        m.side_effect = [m1, m2]
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_git_provenance_commit_none_when_stdout_empty_batch34(tmp_path):
    with patch("evaluation.report.subprocess.run") as m:
        m1 = MagicMock(returncode=0, stdout="")
        m2 = MagicMock(returncode=0, stdout="")
        m.side_effect = [m1, m2]
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_git_provenance_subprocess_timeout_batch34(tmp_path):
    """subprocess.TimeoutExpired → 视为 SubprocessError → commit=None, dirty=True。"""
    with patch("evaluation.report.subprocess.run",
               side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10)):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_git_provenance_cwd_param_used_batch34(tmp_path):
    """subprocess.run 接收 cwd 参数。"""
    with patch("evaluation.report.subprocess.run") as m:
        m1 = MagicMock(returncode=0, stdout="abc")
        m2 = MagicMock(returncode=0, stdout="")
        m.side_effect = [m1, m2]
        get_git_provenance(tmp_path)
    for call in m.call_args_list:
        assert call[1]["cwd"] == str(tmp_path)


def test_git_provenance_capture_output_used_batch34(tmp_path):
    with patch("evaluation.report.subprocess.run") as m:
        m1 = MagicMock(returncode=0, stdout="abc")
        m2 = MagicMock(returncode=0, stdout="")
        m.side_effect = [m1, m2]
        get_git_provenance(tmp_path)
    for call in m.call_args_list:
        assert call[1]["capture_output"] is True


def test_git_provenance_encoding_utf8_batch34(tmp_path):
    with patch("evaluation.report.subprocess.run") as m:
        m1 = MagicMock(returncode=0, stdout="abc")
        m2 = MagicMock(returncode=0, stdout="")
        m.side_effect = [m1, m2]
        get_git_provenance(tmp_path)
    for call in m.call_args_list:
        assert call[1]["encoding"] == "utf-8"
        assert call[1]["errors"] == "replace"


def test_git_provenance_timeout_10_batch34(tmp_path):
    with patch("evaluation.report.subprocess.run") as m:
        m1 = MagicMock(returncode=0, stdout="abc")
        m2 = MagicMock(returncode=0, stdout="")
        m.side_effect = [m1, m2]
        get_git_provenance(tmp_path)
    for call in m.call_args_list:
        assert call[1]["timeout"] == 10


# ---------- get_dependency_versions 第三十四批


def test_dependency_versions_returns_dict_batch34():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_dependency_versions_three_keys_batch34():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_dependency_versions_values_str_or_none_batch34():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str)


def test_dependency_versions_with_package_not_found_batch34():
    """模拟 PackageNotFoundError → value=None。"""
    import importlib.metadata
    with patch("importlib.metadata.version",
               side_effect=importlib.metadata.PackageNotFoundError):
        out = get_dependency_versions()
    for k, v in out.items():
        assert v is None


def test_dependency_versions_with_generic_exception_batch34():
    """模拟 generic exception → value=None。"""
    with patch("importlib.metadata.version", side_effect=RuntimeError):
        out = get_dependency_versions()
    for k, v in out.items():
        assert v is None


# ---------- build_provenance 第三十四批


def test_build_provenance_returns_dict_batch34(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out, dict)


def test_build_provenance_nine_keys_batch34(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    expected = {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    }
    assert set(out.keys()) == expected


def test_build_provenance_parser_name_batch34(tmp_path):
    out = build_provenance(tmp_path, "kreuzberg", 800, "1.0")
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_none_batch34(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_parser_version_str_batch34(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "v2.0")
    assert out["parser_version"] == "v2.0"


def test_build_provenance_max_chars_int_batch34(tmp_path):
    """max_chars 强转为 int。"""
    out = build_provenance(tmp_path, "fallback", "800", None)  # type: ignore[arg-type]
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_negative_batch34(tmp_path):
    out = build_provenance(tmp_path, "fallback", -100, None)
    assert out["max_chars"] == -100


def test_build_provenance_run_timestamp_parseable_batch34(tmp_path):
    """run_timestamp_iso 是合法 ISO 时间。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    ts = out["run_timestamp_iso"]
    parsed = datetime.fromisoformat(ts)
    assert parsed is not None


def test_build_provenance_evaluator_version_batch34(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_batch34(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_dependencies_dict_batch34(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_dependencies_keys_batch34(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert set(out["dependencies"].keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_build_provenance_git_commit_via_mock_batch34(tmp_path):
    """mock git commit → provenance 含相同 commit。"""
    with patch("evaluation.report.subprocess.run") as m:
        m1 = MagicMock(returncode=0, stdout="deadbeef\n")
        m2 = MagicMock(returncode=0, stdout="")
        m.side_effect = [m1, m2]
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["git_commit"] == "deadbeef"


# ---------- build_devset_section 第三十四批


def _make_manifest_mock(devset_status="incomplete", file_count=0, content_group_count=0,
                        pdf_count=0, docx_count=0, categories_covered=None):
    m = MagicMock()
    m.devset_status = devset_status
    m.file_count = file_count
    m.content_group_count = content_group_count
    m.pdf_count = pdf_count
    m.docx_count = docx_count
    m.categories_covered = categories_covered or []
    return m


def test_build_devset_section_returns_dict_batch34():
    m = _make_manifest_mock()
    out = build_devset_section(m)
    assert isinstance(out, dict)


def test_build_devset_section_six_keys_batch34():
    m = _make_manifest_mock()
    out = build_devset_section(m)
    expected = {"status", "file_count", "content_group_count", "pdf_count",
                "docx_count", "categories_covered"}
    assert set(out.keys()) == expected


def test_build_devset_section_status_batch34():
    m = _make_manifest_mock(devset_status="complete")
    out = build_devset_section(m)
    assert out["status"] == "complete"


def test_build_devset_section_file_count_batch34():
    m = _make_manifest_mock(file_count=42)
    out = build_devset_section(m)
    assert out["file_count"] == 42


def test_build_devset_section_content_group_count_batch34():
    m = _make_manifest_mock(content_group_count=7)
    out = build_devset_section(m)
    assert out["content_group_count"] == 7


def test_build_devset_section_pdf_count_batch34():
    m = _make_manifest_mock(pdf_count=3)
    out = build_devset_section(m)
    assert out["pdf_count"] == 3


def test_build_devset_section_docx_count_batch34():
    m = _make_manifest_mock(docx_count=5)
    out = build_devset_section(m)
    assert out["docx_count"] == 5


def test_build_devset_section_categories_covered_batch34():
    m = _make_manifest_mock(categories_covered=["a", "b"])
    out = build_devset_section(m)
    assert out["categories_covered"] == ["a", "b"]


def test_build_devset_section_empty_categories_batch34():
    m = _make_manifest_mock(categories_covered=[])
    out = build_devset_section(m)
    assert out["categories_covered"] == []


# ---------- aggregate_summary 第三十四批


def test_aggregate_summary_empty_list_returns_dict_batch34():
    out = aggregate_summary([])
    assert isinstance(out, dict)


def test_aggregate_summary_has_four_keys_batch34():
    out = aggregate_summary([])
    expected = {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}
    assert set(out.keys()) == expected


def test_aggregate_summary_counts_element_count_batch34():
    """counts 含 element_count_total 求和。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": 3}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 8
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_skip_null_batch34():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_counts_all_null_returns_none_batch34():
    per_doc = [
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_success_rates_pipeline_batch34():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2
    assert sr["rate"] == 0.5


def test_aggregate_summary_success_rates_all_true_batch34():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0


def test_aggregate_summary_success_rates_empty_batch34():
    out = aggregate_summary([])
    assert out["success_rates"]["pipeline_success"]["rate"] is None
    assert out["success_rates"]["pipeline_success"]["total"] == 0


def test_aggregate_summary_ratio_macro_average_batch34():
    """ratio macro average = mean of all non-null values。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
    ]
    out = aggregate_summary(per_doc)
    rm = out["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] == 0.75
    assert rm["participating_docs"] == 2
    assert rm["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_with_null_batch34():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    rm = out["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] == 1.0
    assert rm["participating_docs"] == 1
    assert rm["not_evaluated"] == 1


def test_aggregate_summary_ratio_macro_all_null_batch34():
    per_doc = [
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    rm = out["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] is None
    assert rm["participating_docs"] == 0
    assert rm["not_evaluated"] == 2


def test_aggregate_summary_silent_drop_sum_batch34():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 2}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 7


def test_aggregate_summary_silent_drop_with_null_batch34():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 2}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 2


def test_aggregate_summary_silent_drop_all_null_batch34():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_does_not_mutate_input_batch34():
    """aggregate_summary 不修改输入 list。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    import json
    before = json.dumps(per_doc, sort_keys=True, default=str)
    aggregate_summary(per_doc)
    after = json.dumps(per_doc, sort_keys=True, default=str)
    assert before == after


def test_aggregate_summary_missing_metric_key_batch34():
    """per_doc 缺 metric key → 当空 dict 处理（不抛）。"""
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    assert "counts" in out
    assert "success_rates" in out


# ---------- module source forbidden tokens 第五十九批


# subprocess 在 report.py 中是合法的（git provenance），但其他仍禁止
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
def test_module_source_no_forbidden_tokens_batch34(token):
    src = inspect.getsource(rmod)
    assert token not in src


def test_module_source_contains_subprocess_batch34():
    """subprocess 在 report.py 中合法（git provenance 用）。"""
    src = inspect.getsource(rmod)
    assert "subprocess" in src


# ---------- module source 字符串精确补强第五十五批


def test_module_source_contains_docstring_batch34():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_contains_aggregation_rule_doc_batch34():
    src = inspect.getsource(rmod)
    assert "聚合规则" in src


def test_module_source_contains_future_annotations_batch34():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_subprocess_import_batch34():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_contains_datetime_import_batch34():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_contains_pathlib_import_batch34():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch34():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_contains_evaluator_version_import_batch34():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_contains_ratio_metrics_definition_batch34():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS = (" in src


def test_module_source_contains_count_metrics_definition_batch34():
    src = inspect.getsource(rmod)
    assert '_COUNT_METRICS = ("element_count_total",)' in src


def test_module_source_contains_success_bool_definition_batch34():
    src = inspect.getsource(rmod)
    assert '_SUCCESS_BOOL_METRICS = ("pipeline_success",)' in src


def test_module_source_contains_get_git_provenance_func_batch34():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src


def test_module_source_contains_get_dependency_versions_func_batch34():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions(" in src


def test_module_source_contains_build_provenance_func_batch34():
    src = inspect.getsource(rmod)
    assert "def build_provenance(" in src


def test_module_source_contains_build_devset_section_func_batch34():
    src = inspect.getsource(rmod)
    assert "def build_devset_section(" in src


def test_module_source_contains_aggregate_summary_func_batch34():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary(" in src


def test_module_source_contains_rev_parse_head_batch34():
    src = inspect.getsource(rmod)
    assert '"rev-parse"' in src
    assert '"HEAD"' in src


def test_module_source_contains_status_porcelain_batch34():
    src = inspect.getsource(rmod)
    assert '"status"' in src
    assert '"--porcelain"' in src


def test_module_source_contains_importlib_metadata_batch34():
    src = inspect.getsource(rmod)
    assert "import importlib.metadata" in src


def test_module_source_contains_python_docx_pkg_batch34():
    src = inspect.getsource(rmod)
    assert '"python-docx"' in src


def test_module_source_contains_pypdfium2_pkg_batch34():
    src = inspect.getsource(rmod)
    assert '"pypdfium2"' in src


def test_module_source_contains_pdfplumber_pkg_batch34():
    src = inspect.getsource(rmod)
    assert '"pdfplumber"' in src


def test_module_source_contains_macro_average_key_batch34():
    src = inspect.getsource(rmod)
    assert '"macro_average"' in src


def test_module_source_contains_participating_docs_key_batch34():
    src = inspect.getsource(rmod)
    assert '"participating_docs"' in src


def test_module_source_contains_not_evaluated_key_batch34():
    src = inspect.getsource(rmod)
    assert '"not_evaluated"' in src


def test_module_source_contains_silent_drop_total_key_batch34():
    src = inspect.getsource(rmod)
    assert '"silent_drop_total"' in src


def test_module_source_contains_run_timestamp_iso_batch34():
    src = inspect.getsource(rmod)
    assert '"run_timestamp_iso"' in src


def test_module_source_contains_datetime_now_iso_batch34():
    src = inspect.getsource(rmod)
    assert "datetime.now().astimezone().isoformat()" in src


def test_module_source_contains_all_definition_batch34():
    src = inspect.getsource(rmod)
    assert "__all__" in src


# ---------- signatures 第五十五批


def test_signature_get_git_provenance_one_param_batch34():
    sig = inspect.signature(get_git_provenance)
    assert list(sig.parameters.keys()) == ["project_root"]


def test_signature_get_git_provenance_return_dict_batch34():
    sig = inspect.signature(get_git_provenance)
    assert "dict" in str(sig.return_annotation)


def test_signature_get_dependency_versions_no_params_batch34():
    sig = inspect.signature(get_dependency_versions)
    assert list(sig.parameters.keys()) == []


def test_signature_build_provenance_params_batch34():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_provenance_parser_version_optional_batch34():
    sig = inspect.signature(build_provenance)
    # parser_version 是 required positional（无默认值），annotation 是 'str | None'
    assert sig.parameters["parser_version"].default is inspect.Parameter.empty


def test_signature_build_provenance_parser_version_annotation_batch34():
    sig = inspect.signature(build_provenance)
    # annotation: 'str | None'
    assert "str" in str(sig.parameters["parser_version"].annotation)
    assert "None" in str(sig.parameters["parser_version"].annotation)


def test_signature_build_devset_section_one_param_batch34():
    sig = inspect.signature(build_devset_section)
    assert list(sig.parameters.keys()) == ["manifest"]


def test_signature_aggregate_summary_one_param_batch34():
    sig = inspect.signature(aggregate_summary)
    assert list(sig.parameters.keys()) == ["per_doc_results"]


# ---------- module 合理性第五十五批


def test_module_has_build_provenance_batch34():
    assert callable(rmod.build_provenance)


def test_module_has_build_devset_section_batch34():
    assert callable(rmod.build_devset_section)


def test_module_has_aggregate_summary_batch34():
    assert callable(rmod.aggregate_summary)


def test_module_has_get_git_provenance_batch34():
    assert callable(rmod.get_git_provenance)


def test_module_has_get_dependency_versions_batch34():
    assert callable(rmod.get_dependency_versions)


def test_module_has_ratio_metrics_batch34():
    assert hasattr(rmod, "_RATIO_METRICS")


def test_module_has_count_metrics_batch34():
    assert hasattr(rmod, "_COUNT_METRICS")


def test_module_has_success_bool_metrics_batch34():
    assert hasattr(rmod, "_SUCCESS_BOOL_METRICS")


def test_module_all_contains_5_entries_batch34():
    assert len(rmod.__all__) == 5


def test_module_all_names_match_attributes_batch34():
    for name in rmod.__all__:
        assert hasattr(rmod, name)


# ---------- 端到端集成第五十五批


def test_e2e_build_provenance_full_batch34(tmp_path):
    """build_provenance 端到端跑通（用真实 git）。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] == "1.0"
    assert out["max_chars"] == 800
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION
    assert "git_commit" in out
    assert "git_dirty" in out
    assert isinstance(out["dependencies"], dict)
    # timestamp 应当可解析
    datetime.fromisoformat(out["run_timestamp_iso"])


def test_e2e_aggregate_full_summary_batch34():
    """完整 aggregate：3 docs，混合成功/失败。"""
    per_doc = [
        {"metrics": {
            "pipeline_success": {"value": True},
            "schema_valid": {"value": 1.0},
            "element_count_total": {"value": 5},
            "silent_drop_count": {"value": 2},
        }},
        {"metrics": {
            "pipeline_success": {"value": False},
            "schema_valid": {"value": None, "reason": "pipeline_failed"},
            "element_count_total": {"value": None, "reason": "pipeline_failed"},
            "silent_drop_count": {"value": None, "reason": "pipeline_failed"},
        }},
        {"metrics": {
            "pipeline_success": {"value": True},
            "schema_valid": {"value": 0.5},
            "element_count_total": {"value": 3},
            "silent_drop_count": {"value": 1},
        }},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 8
    assert out["success_rates"]["pipeline_success"]["success_count"] == 2
    assert out["success_rates"]["pipeline_success"]["total"] == 3
    assert out["success_rates"]["pipeline_success"]["rate"] == 2 / 3
    rm = out["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] == 0.75  # (1.0 + 0.5) / 2
    assert rm["participating_docs"] == 2
    assert rm["not_evaluated"] == 1
    assert out["silent_drop_total"] == 3


def test_e2e_aggregate_idempotent_batch34():
    per_doc = [{"metrics": {"pipeline_success": {"value": True}}}]
    out1 = aggregate_summary(per_doc)
    out2 = aggregate_summary(per_doc)
    assert out1 == out2


def test_e2e_devset_section_full_batch34():
    """build_devset_section 完整提取。"""
    m = _make_manifest_mock(
        devset_status="incomplete",
        file_count=10,
        content_group_count=4,
        pdf_count=6,
        docx_count=4,
        categories_covered=["essay", "report"],
    )
    out = build_devset_section(m)
    assert out["status"] == "incomplete"
    assert out["file_count"] == 10
    assert out["content_group_count"] == 4
    assert out["pdf_count"] == 6
    assert out["docx_count"] == 4
    assert out["categories_covered"] == ["essay", "report"]


def test_e2e_git_provenance_real_repo_batch34():
    """在当前项目根目录跑 git provenance → 应当拿到真实 commit。"""
    project_root = Path(__file__).resolve().parent.parent
    out = get_git_provenance(project_root)
    assert "git_commit" in out
    assert "git_dirty" in out
    # 实际仓库应当有 commit
    assert out["git_commit"] is not None
    assert len(out["git_commit"]) == 40  # SHA-1 hex
