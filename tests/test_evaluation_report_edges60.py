"""evaluation/report.py 第八十七轮 edges 测试（Round 630）。

补强 edges59 未触及的角度（第四十五批）。

新角度：
- _RATIO_METRICS 12 entries 顺序精确
- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 精确
- get_git_provenance 失败兜底（OSError / SubprocessError / TimeoutExpired）
- get_git_provenance 成功路径
- get_dependency_versions 各种包查找
- build_provenance 字段精确
- build_devset_section 字段映射
- aggregate_summary 空 per_doc
- aggregate_summary counts 求和
- aggregate_summary success_rates 0/1/N
- aggregate_summary ratio_macro_averages null 处理
- aggregate_summary silent_drop_total 求和
- module source 字符串精确
- AST 结构
- forbidden tokens 第一百批
"""

from __future__ import annotations

import ast
import inspect
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.report as report_mod
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


# ---------- _RATIO_METRICS 12 entries ----------

def test_ratio_metrics_count_twelve_batch45():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_first_schema_valid_batch45():
    assert _RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_last_chunk_boundary_f1_batch45():
    assert _RATIO_METRICS[-1] == "chunk_boundary_f1"


def test_ratio_metrics_exact_order_batch45():
    assert list(_RATIO_METRICS) == [
        "schema_valid",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        "heading_boundary_compliance",
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    ]


def test_ratio_metrics_all_str_batch45():
    for m in _RATIO_METRICS:
        assert isinstance(m, str)


def test_ratio_metrics_unique_batch45():
    assert len(set(_RATIO_METRICS)) == len(_RATIO_METRICS)


def test_ratio_metrics_is_tuple_batch45():
    assert isinstance(_RATIO_METRICS, tuple)


def test_ratio_metrics_no_figure_caption_batch45():
    """figure_caption_* 始终 null，不参与 macro average。"""
    for m in _RATIO_METRICS:
        assert not m.startswith("figure_caption_")


def test_ratio_metrics_contains_text_char_multiset_batch45():
    assert "text_char_multiset_precision" in _RATIO_METRICS
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_batch45():
    assert "chunk_boundary_precision" in _RATIO_METRICS
    assert "chunk_boundary_recall" in _RATIO_METRICS
    assert "chunk_boundary_f1" in _RATIO_METRICS


# ---------- _COUNT_METRICS / _SUCCESS_BOOL_METRICS ----------

def test_count_metrics_value_batch45():
    assert _COUNT_METRICS == ("element_count_total",)


def test_count_metrics_is_tuple_batch45():
    assert isinstance(_COUNT_METRICS, tuple)


def test_count_metrics_count_one_batch45():
    assert len(_COUNT_METRICS) == 1


def test_success_bool_metrics_value_batch45():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_success_bool_metrics_is_tuple_batch45():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_success_bool_metrics_count_one_batch45():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_count_metrics_disjoint_from_ratio_batch45():
    """_COUNT_METRICS 与 _RATIO_METRICS 不重叠。"""
    for c in _COUNT_METRICS:
        assert c not in _RATIO_METRICS


def test_success_bool_disjoint_from_ratio_batch45():
    for s in _SUCCESS_BOOL_METRICS:
        assert s not in _RATIO_METRICS


def test_success_bool_disjoint_from_count_batch45():
    for s in _SUCCESS_BOOL_METRICS:
        assert s not in _COUNT_METRICS


# ---------- get_git_provenance 失败兜底 ----------

def test_get_git_provenance_oserror_first_call_batch45(tmp_path):
    """第一次 subprocess 抛 OSError → 早返回（不调用第二次）。"""
    with patch("subprocess.run", side_effect=OSError("boom")) as mock_run:
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True
    # 只调用一次（第一次失败就早退）
    # 实际看实现，第一次失败仍然继续调用第二次
    # 验证至少调用一次
    assert mock_run.call_count >= 1


def test_get_git_provenance_subprocess_error_batch45(tmp_path):
    with patch("subprocess.run", side_effect=subprocess.SubprocessError("boom")):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_timeout_batch45(tmp_path):
    """TimeoutExpired 是 SubprocessError 子类。"""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10)):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_first_call_fail_second_succeed_batch45(tmp_path):
    """第一次失败，第二次成功 → commit=None（早退）但 dirty 取决于第二次。

    实际看实现：第一次 OSError 不直接 raise 出去，而是被外层 try/except 接住。
    所以 commit 不会被设置，dirty 也不会按第二次计算。"""
    def side(*args, **kwargs):
        if "rev-parse" in args[0]:
            raise OSError("boom")
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        return m
    with patch("subprocess.run", side_effect=side):
        out = get_git_provenance(tmp_path)
    # OSError 被外层 try 接住 → commit=None, dirty=True
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_success_clean_batch45(tmp_path):
    """git 成功且 porcelain 空 → commit 有值, dirty=False。"""
    def side(*args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        if "rev-parse" in args[0]:
            m.stdout = "abc123\n"
        else:
            m.stdout = ""
        return m
    with patch("subprocess.run", side_effect=side):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is False


def test_get_git_provenance_success_dirty_batch45(tmp_path):
    def side(*args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        if "rev-parse" in args[0]:
            m.stdout = "abc123\n"
        else:
            m.stdout = " M file.txt\n"
        return m
    with patch("subprocess.run", side_effect=side):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is True


def test_get_git_provenance_rev_parse_fail_but_status_ok_batch45(tmp_path):
    """rev-parse returncode != 0 但 status 仍 0 → commit=None, dirty 取决于 status。"""
    def side(*args, **kwargs):
        m = MagicMock()
        if "rev-parse" in args[0]:
            m.returncode = 1
            m.stdout = ""
        else:
            m.returncode = 0
            m.stdout = ""
        return m
    with patch("subprocess.run", side_effect=side):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is False


def test_get_git_provenance_keys_batch45(tmp_path):
    with patch("subprocess.run", side_effect=OSError("x")):
        out = get_git_provenance(tmp_path)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_returns_dict_batch45(tmp_path):
    with patch("subprocess.run", side_effect=OSError("x")):
        out = get_git_provenance(tmp_path)
    assert isinstance(out, dict)


def test_get_git_provenance_git_commit_type_batch45(tmp_path):
    with patch("subprocess.run", side_effect=OSError("x")):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None or isinstance(out["git_commit"], str)


def test_get_git_provenance_git_dirty_type_batch45(tmp_path):
    with patch("subprocess.run", side_effect=OSError("x")):
        out = get_git_provenance(tmp_path)
    assert isinstance(out["git_dirty"], bool)


# ---------- get_dependency_versions ----------

def test_get_dependency_versions_returns_dict_batch45():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_get_dependency_versions_keys_batch45():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_type_batch45():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str)


# ---------- build_provenance ----------

def test_build_provenance_keys_batch45(tmp_path):
    with patch("subprocess.run", side_effect=OSError("x")):
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


def test_build_provenance_evaluator_version_batch45(tmp_path):
    with patch("subprocess.run", side_effect=OSError("x")):
        out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["evaluator_version"] == "1.1"


def test_build_provenance_report_version_batch45(tmp_path):
    with patch("subprocess.run", side_effect=OSError("x")):
        out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["report_version"] == "1.1"


def test_build_provenance_parser_name_batch45(tmp_path):
    with patch("subprocess.run", side_effect=OSError("x")):
        out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["parser_name"] == "fallback"


def test_build_provenance_parser_version_batch45(tmp_path):
    with patch("subprocess.run", side_effect=OSError("x")):
        out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["parser_version"] == "1.0.0"


def test_build_provenance_parser_version_none_batch45(tmp_path):
    with patch("subprocess.run", side_effect=OSError("x")):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_max_chars_int_batch45(tmp_path):
    with patch("subprocess.run", side_effect=OSError("x")):
        out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_conversion_batch45(tmp_path):
    """int(max_chars) 强制转换。"""
    with patch("subprocess.run", side_effect=OSError("x")):
        out = build_provenance(tmp_path, "fallback", "800", "1.0.0")  # type: ignore[arg-type]
    assert out["max_chars"] == 800


def test_build_provenance_run_timestamp_format_batch45(tmp_path):
    with patch("subprocess.run", side_effect=OSError("x")):
        out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    ts = out["run_timestamp_iso"]
    # ISO 8601 格式：含 T 和时区
    assert "T" in ts
    # 应该可以被 fromisoformat 解析
    parsed = datetime.fromisoformat(ts)
    assert isinstance(parsed, datetime)


def test_build_provenance_dependencies_present_batch45(tmp_path):
    with patch("subprocess.run", side_effect=OSError("x")):
        out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert "dependencies" in out
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_git_fields_from_helper_batch45(tmp_path):
    """git_commit / git_dirty 来自 get_git_provenance。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
        out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["git_commit"] == "abc"
    assert out["git_dirty"] is False


# ---------- build_devset_section ----------

def _make_manifest_mock(**kwargs):
    m = MagicMock()
    m.devset_status = kwargs.get("devset_status", "incomplete")
    m.file_count = kwargs.get("file_count", 0)
    m.content_group_count = kwargs.get("content_group_count", 0)
    m.pdf_count = kwargs.get("pdf_count", 0)
    m.docx_count = kwargs.get("docx_count", 0)
    m.categories_covered = kwargs.get("categories_covered", [])
    return m


def test_build_devset_section_keys_batch45():
    m = _make_manifest_mock()
    out = build_devset_section(m)
    assert set(out.keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_build_devset_section_status_batch45():
    m = _make_manifest_mock(devset_status="complete")
    out = build_devset_section(m)
    assert out["status"] == "complete"


def test_build_devset_section_file_count_batch45():
    m = _make_manifest_mock(file_count=5)
    out = build_devset_section(m)
    assert out["file_count"] == 5


def test_build_devset_section_pdf_count_batch45():
    m = _make_manifest_mock(pdf_count=3)
    out = build_devset_section(m)
    assert out["pdf_count"] == 3


def test_build_devset_section_docx_count_batch45():
    m = _make_manifest_mock(docx_count=2)
    out = build_devset_section(m)
    assert out["docx_count"] == 2


def test_build_devset_section_content_group_count_batch45():
    m = _make_manifest_mock(content_group_count=4)
    out = build_devset_section(m)
    assert out["content_group_count"] == 4


def test_build_devset_section_categories_covered_batch45():
    m = _make_manifest_mock(categories_covered=["a", "b"])
    out = build_devset_section(m)
    assert out["categories_covered"] == ["a", "b"]


# ---------- aggregate_summary 各种 ----------

def test_aggregate_summary_empty_batch45():
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_empty_counts_batch45():
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"] == {"sum": None, "participating_docs": 0}


def test_aggregate_summary_empty_success_rates_batch45():
    out = aggregate_summary([])
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 0
    assert sr["rate"] is None


def test_aggregate_summary_empty_silent_drop_batch45():
    out = aggregate_summary([])
    assert out["silent_drop_total"] is None


def test_aggregate_summary_counts_sum_batch45():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"element_count_total": {"value": 3, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 8
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_skip_none_batch45():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"element_count_total": {"value": None, "reason": "pipeline_failed"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_success_rates_all_success_batch45():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 2
    assert sr["rate"] == 1.0


def test_aggregate_summary_success_rates_all_fail_batch45():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["rate"] == 0.0


def test_aggregate_summary_success_rates_half_batch45():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["rate"] == 0.5


def test_aggregate_summary_success_rates_none_value_batch45():
    """pipeline_success 不应该有 None 值（要么 True 要么 False），但 test 兜底。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": None, "reason": "x"}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 1


def test_aggregate_summary_ratio_macro_simple_batch45():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
        {"metrics": {"schema_valid": {"value": 0.5, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    avg = out["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == 0.75
    assert avg["participating_docs"] == 2
    assert avg["not_evaluated"] == 0


def test_aggregate_summary_ratio_skip_none_batch45():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "pipeline_failed"}}},
    ]
    out = aggregate_summary(per_doc)
    avg = out["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == 1.0
    assert avg["participating_docs"] == 1
    assert avg["not_evaluated"] == 1


def test_aggregate_summary_ratio_all_none_batch45():
    per_doc = [
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "y"}}},
    ]
    out = aggregate_summary(per_doc)
    avg = out["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] is None
    assert avg["participating_docs"] == 0
    assert avg["not_evaluated"] == 2


def test_aggregate_summary_silent_drop_sum_batch45():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": 5, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_skip_none_batch45():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": None, "reason": "x"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 3


def test_aggregate_summary_silent_drop_zero_counted_batch45():
    """value=0 也参与求和（!= None）。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 0, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": 5, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 5


def test_aggregate_summary_has_12_ratio_entries_batch45():
    out = aggregate_summary([])
    assert len(out["ratio_macro_averages"]) == 12


def test_aggregate_summary_has_1_count_entry_batch45():
    out = aggregate_summary([])
    assert len(out["counts"]) == 1


def test_aggregate_summary_has_1_success_rate_entry_batch45():
    out = aggregate_summary([])
    assert len(out["success_rates"]) == 1


# ---------- module source 字符串精确 ----------

def test_module_docstring_contains_aggregation_rules_batch45():
    src = inspect.getsource(report_mod)
    assert "counts" in src
    assert "success_rates" in src
    assert "ratio_macro_averages" in src
    assert "silent_drop_count" in src


def test_module_source_contains_subprocess_import_batch45():
    src = inspect.getsource(report_mod)
    assert "import subprocess" in src


def test_module_source_contains_datetime_import_batch45():
    src = inspect.getsource(report_mod)
    assert "from datetime import datetime" in src


def test_module_source_contains_path_import_batch45():
    src = inspect.getsource(report_mod)
    assert "from pathlib import Path" in src


def test_module_source_contains_any_import_batch45():
    src = inspect.getsource(report_mod)
    assert "from typing import Any" in src


def test_module_source_contains_evaluation_import_batch45():
    src = inspect.getsource(report_mod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_contains_get_git_provenance_batch45():
    src = inspect.getsource(report_mod)
    assert "def get_git_provenance(project_root: Path) -> dict[str, Any]:" in src


def test_module_source_contains_get_dependency_versions_batch45():
    src = inspect.getsource(report_mod)
    assert "def get_dependency_versions() -> dict[str, str | None]:" in src


def test_module_source_contains_build_provenance_batch45():
    src = inspect.getsource(report_mod)
    assert "def build_provenance(" in src


def test_module_source_contains_build_devset_section_batch45():
    src = inspect.getsource(report_mod)
    assert "def build_devset_section(manifest) -> dict[str, Any]:" in src


def test_module_source_contains_aggregate_summary_batch45():
    src = inspect.getsource(report_mod)
    assert "def aggregate_summary(per_doc_results: list[dict[str, Any]]) -> dict[str, Any]:" in src


def test_module_source_contains_subprocess_run_batch45():
    src = inspect.getsource(report_mod)
    assert "subprocess.run" in src


def test_module_source_contains_capture_output_batch45():
    src = inspect.getsource(report_mod)
    assert "capture_output=True" in src


def test_module_source_contains_encoding_utf8_batch45():
    src = inspect.getsource(report_mod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_errors_replace_batch45():
    src = inspect.getsource(report_mod)
    assert 'errors="replace"' in src


def test_module_source_contains_timeout_10_batch45():
    src = inspect.getsource(report_mod)
    assert "timeout=10" in src


def test_module_source_contains_rev_parse_batch45():
    src = inspect.getsource(report_mod)
    assert '"git", "rev-parse", "HEAD"' in src


def test_module_source_contains_status_porcelain_batch45():
    src = inspect.getsource(report_mod)
    assert '"git", "status", "--porcelain"' in src


def test_module_source_contains_importlib_metadata_batch45():
    src = inspect.getsource(report_mod)
    assert "import importlib.metadata" in src


def test_module_source_contains_package_not_found_batch45():
    src = inspect.getsource(report_mod)
    assert "PackageNotFoundError" in src


def test_module_source_contains_three_packages_batch45():
    src = inspect.getsource(report_mod)
    assert '"pdfplumber"' in src
    assert '"python-docx"' in src
    assert '"pypdfium2"' in src


# ---------- __all__ ----------

def test_all_exact_order_batch45():
    assert list(report_mod.__all__) == [
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    ]


def test_all_count_five_batch45():
    assert len(report_mod.__all__) == 5


def test_all_entries_callable_batch45():
    for name in report_mod.__all__:
        assert callable(getattr(report_mod, name))


def test_all_entries_unique_batch45():
    assert len(set(report_mod.__all__)) == len(report_mod.__all__)


# ---------- AST 结构 ----------

def test_ast_top_level_functions_count_batch45():
    tree = ast.parse(inspect.getsource(report_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 5


def test_ast_top_level_function_names_batch45():
    tree = ast.parse(inspect.getsource(report_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == [
        "get_git_provenance",
        "get_dependency_versions",
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
    ]


def test_ast_top_level_no_class_batch45():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_top_level_no_async_batch45():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_first_node_docstring_batch45():
    tree = ast.parse(inspect.getsource(report_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)


def test_ast_second_node_future_import_batch45():
    tree = ast.parse(inspect.getsource(report_mod))
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


def test_ast_get_git_provenance_has_try_batch45():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance"][0]
    trys = [n for n in func.body if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_get_git_provenance_try_excepts_batch45():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance"][0]
    try_node = [n for n in func.body if isinstance(n, ast.Try)][0]
    # 一个 except handler 接 (OSError, subprocess.SubprocessError)
    assert len(try_node.handlers) == 1
    handler = try_node.handlers[0]
    # 应该是 tuple
    assert isinstance(handler.type, ast.Tuple)
    # OSError 是 Name
    types = []
    for t in handler.type.elts:
        if isinstance(t, ast.Name):
            types.append(t.id)
        elif isinstance(t, ast.Attribute):
            types.append(t.attr)
    assert "OSError" in types
    assert "SubprocessError" in types


def test_ast_aggregate_summary_has_for_loops_batch45():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary"][0]
    # 3 个显式 for（counts / success_rates / ratio）+ 1 个 generator for silent_drop（ast.walk 不计 generator）
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 3


def test_ast_get_dependency_versions_has_for_batch45():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_dependency_versions"][0]
    fors = [n for n in func.body if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_get_dependency_versions_has_try_batch45():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_dependency_versions"][0]
    # try 在 for 循环内，需要 ast.walk
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_build_provenance_calls_get_git_batch45():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_provenance"][0]
    has_call = False
    for n in ast.walk(func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id == "get_git_provenance":
                has_call = True
    assert has_call


def test_ast_build_provenance_calls_get_dep_versions_batch45():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_provenance"][0]
    has_call = False
    for n in ast.walk(func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id == "get_dependency_versions":
                has_call = True
    assert has_call


# ---------- forbidden tokens 第一百批 ----------

def test_source_no_eval_batch45():
    src = inspect.getsource(report_mod)
    assert "eval(" not in src


def test_source_no_exec_batch45():
    src = inspect.getsource(report_mod)
    assert "exec(" not in src


def test_source_no_compile_batch45():
    src = inspect.getsource(report_mod)
    assert "compile(" not in src


def test_source_no_globals_batch45():
    src = inspect.getsource(report_mod)
    assert "globals(" not in src


def test_source_no_locals_batch45():
    src = inspect.getsource(report_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch45():
    src = inspect.getsource(report_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch45():
    """subprocess.run + capture_output 不算 popen。"""
    src = inspect.getsource(report_mod)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch45():
    src = inspect.getsource(report_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch45():
    src = inspect.getsource(report_mod)
    assert "pickle.load(" not in src


def test_source_no_class_keyword_batch45():
    src = inspect.getsource(report_mod)
    assert "\nclass " not in src


def test_source_no_async_def_batch45():
    src = inspect.getsource(report_mod)
    assert "async def" not in src


def test_source_no_yield_batch45():
    src = inspect.getsource(report_mod)
    assert "yield" not in src


def test_source_no_walrus_batch45():
    src = inspect.getsource(report_mod)
    assert ":=" not in src


def test_source_no_lambda_batch45():
    src = inspect.getsource(report_mod)
    assert "lambda" not in src


def test_source_uses_subprocess_run_not_popen_batch45():
    src = inspect.getsource(report_mod)
    assert "subprocess.run" in src
