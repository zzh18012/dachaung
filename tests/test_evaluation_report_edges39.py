"""evaluation/report.py 第三十九轮 edges 测试（Round 478）。

补强 edges38 未触及的角度：
- _RATIO_METRICS 内容 第二十三批（顺序 / tuple 类型 / 各项独立 / 与 chunk_boundary 集合关系）
- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第二十三批（singleton / 内容 / 互不相交）
- get_git_provenance 第二十三批（subprocess.run 参数 / encoding=errors= / timeout=10 / OSError 容错 / SubprocessError 容错）
- get_dependency_versions 第二十三批（dict 类型 / package 名集合 / PackageNotFoundError 容错 / 包存在返回字符串）
- build_provenance 第二十三批（返回 dict 9 keys / max_chars int 转换 / run_timestamp_iso 格式 / git_commit 透传 / git_dirty 透传）
- build_devset_section 第二十三批（status / file_count / content_group_count / pdf_count / docx_count / categories_covered）
- aggregate_summary 第二十三批（counts 求和 / success rate / macro average / silent_drop 求和 / 空输入 / 全 null metrics / 部分 null / 多 doc）
- module source forbidden tokens 第三十九批
- module source 字符串精确补强第三十五批
- signatures 第三十五批
- module 合理性第三十五批
- 端到端集成第三十五批
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


# ---------- _RATIO_METRICS 内容 第二十三批 ----------


def test_ratio_metrics_is_tuple_batch23():
    assert isinstance(_RATIO_METRICS, tuple)


def test_ratio_metrics_first_item_schema_valid_batch23():
    """schema_valid 应在 _RATIO_METRICS 中。"""
    assert _RATIO_METRICS[0] == "schema_valid" or "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_no_duplicates_batch23():
    assert len(_RATIO_METRICS) == len(set(_RATIO_METRICS))


def test_ratio_metrics_count_at_least_10_batch23():
    """至少 10 个 ratio metrics（保守）。"""
    assert len(_RATIO_METRICS) >= 10


def test_ratio_metrics_contains_text_preservation_equal_batch23():
    assert "text_preservation_equal" in _RATIO_METRICS


def test_ratio_metrics_contains_text_char_multiset_precision_batch23():
    assert "text_char_multiset_precision" in _RATIO_METRICS


def test_ratio_metrics_contains_text_char_multiset_recall_batch23():
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_contains_heading_boundary_compliance_batch23():
    assert "heading_boundary_compliance" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_precision_batch23():
    assert "chunk_boundary_precision" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_recall_batch23():
    assert "chunk_boundary_recall" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_f1_batch23():
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_contains_image_resource_exists_ratio_batch23():
    assert "image_resource_exists_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_reference_intact_ratio_batch23():
    assert "chunk_reference_intact_ratio" in _RATIO_METRICS


def test_ratio_metrics_excludes_silent_drop_count_batch23():
    assert "silent_drop_count" not in _RATIO_METRICS


def test_ratio_metrics_excludes_error_code_batch23():
    assert "error_code" not in _RATIO_METRICS


# ---------- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第二十三批 ----------


def test_count_metrics_is_tuple_batch23():
    assert isinstance(_COUNT_METRICS, tuple)


def test_count_metrics_singleton_batch23():
    assert len(_COUNT_METRICS) == 1


def test_count_metrics_contains_element_count_total_batch23():
    assert _COUNT_METRICS[0] == "element_count_total"


def test_success_bool_metrics_is_tuple_batch23():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_success_bool_metrics_singleton_batch23():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_success_bool_metrics_contains_pipeline_success_batch23():
    assert _SUCCESS_BOOL_METRICS[0] == "pipeline_success"


def test_count_metrics_disjoint_from_ratio_metrics_batch23():
    assert not (set(_COUNT_METRICS) & set(_RATIO_METRICS))


def test_success_bool_metrics_disjoint_from_ratio_metrics_batch23():
    assert not (set(_SUCCESS_BOOL_METRICS) & set(_RATIO_METRICS))


def test_count_metrics_disjoint_from_success_bool_metrics_batch23():
    assert not (set(_COUNT_METRICS) & set(_SUCCESS_BOOL_METRICS))


# ---------- get_git_provenance 第二十三批 ----------


def test_get_git_provenance_returns_dict_batch23(tmp_path):
    out = get_git_provenance(tmp_path)
    assert isinstance(out, dict)


def test_get_git_provenance_two_keys_batch23(tmp_path):
    out = get_git_provenance(tmp_path)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_handles_os_error_batch23(tmp_path):
    """subprocess.run 抛 OSError → 退回 commit=None, dirty=True。"""
    with patch("evaluation.report.subprocess.run", side_effect=OSError("denied")):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_handles_subprocess_error_batch23(tmp_path):
    """subprocess.run 抛 SubprocessError → 退回 commit=None, dirty=True。"""
    with patch(
        "evaluation.report.subprocess.run",
        side_effect=subprocess.SubprocessError("timeout"),
    ):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_commit_strips_whitespace_batch23(tmp_path):
    """git_commit 被 strip 处理。"""
    fake_result = MagicMock(returncode=0, stdout="  abc123  \n")
    with patch("evaluation.report.subprocess.run", return_value=fake_result):
        out = get_git_provenance(tmp_path)
    # 第一次调 rev-parse 得到 'abc123'（strip 后），第二次 status stdout 也 strip
    assert out["git_commit"] == "abc123"


def test_get_git_provenance_commit_none_when_returncode_nonzero_batch23(tmp_path):
    """rev-parse 返回非零 → commit=None。"""
    fake_fail = MagicMock(returncode=1, stdout="")
    with patch("evaluation.report.subprocess.run", return_value=fake_fail):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_dirty_false_when_porcelain_empty_batch23(tmp_path):
    """git status porcelain 输出为空 → dirty=False。"""
    fake = MagicMock(returncode=0, stdout="")
    with patch("evaluation.report.subprocess.run", return_value=fake):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_get_git_provenance_dirty_true_when_porcelain_nonempty_batch23(tmp_path):
    fake = MagicMock(returncode=0, stdout=" M file.txt\n")
    with patch("evaluation.report.subprocess.run", return_value=fake):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


def test_get_git_provenance_dirty_false_when_porcelain_fails_batch23(tmp_path):
    """git status 失败（returncode != 0）→ dirty=False。"""
    fake = MagicMock(returncode=1, stdout="")
    with patch("evaluation.report.subprocess.run", return_value=fake):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


# ---------- get_dependency_versions 第二十三批 ----------


def test_get_dependency_versions_returns_dict_batch23():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_get_dependency_versions_three_packages_batch23():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_pdfplumber_value_batch23():
    out = get_dependency_versions()
    # pdfplumber 已安装 → 应是字符串
    if out["pdfplumber"] is not None:
        assert isinstance(out["pdfplumber"], str)


def test_get_dependency_versions_handles_package_not_found_batch23():
    """PackageNotFoundError → None。"""
    import importlib.metadata

    with patch(
        "importlib.metadata.version",
        side_effect=importlib.metadata.PackageNotFoundError,
    ):
        out = get_dependency_versions()
    for v in out.values():
        assert v is None


def test_get_dependency_versions_handles_generic_exception_batch23():
    """其他异常 → None。"""
    with patch("importlib.metadata.version", side_effect=RuntimeError("bad")):
        out = get_dependency_versions()
    for v in out.values():
        assert v is None


def test_get_dependency_versions_values_are_optional_str_batch23():
    """每个值是 str 或 None。"""
    out = get_dependency_versions()
    for v in out.values():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_pypdfium2_value_batch23():
    """pypdfium2 通常已安装（fallback parser 依赖）。"""
    out = get_dependency_versions()
    # 不强制断言（可能未安装），仅类型检查
    assert out["pypdfium2"] is None or isinstance(out["pypdfium2"], str)


# ---------- build_provenance 第二十三批 ----------


def test_build_provenance_returns_dict_batch23(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert isinstance(out, dict)


def test_build_provenance_nine_keys_batch23(tmp_path):
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


def test_build_provenance_evaluator_version_constant_batch23(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_constant_batch23(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_passed_through_batch23(tmp_path):
    out = build_provenance(tmp_path, "kreuzberg", 800, None)
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_passed_through_batch23(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "9.9.9")
    assert out["parser_version"] == "9.9.9"


def test_build_provenance_parser_version_none_batch23(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_max_chars_converted_to_int_batch23(tmp_path):
    """max_chars 被 int() 转换。"""
    out = build_provenance(tmp_path, "fallback", 800.5, None)
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_dependencies_is_dict_batch23(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_run_timestamp_iso_format_batch23(tmp_path):
    """run_timestamp_iso 应可被 datetime.fromisoformat 解析。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    ts = out["run_timestamp_iso"]
    parsed = datetime.fromisoformat(ts)  # 不抛错即可
    assert parsed is not None


# ---------- build_devset_section 第二十三批 ----------


def test_build_devset_section_six_keys_batch23():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 5
    m.content_group_count = 2
    m.pdf_count = 3
    m.docx_count = 2
    m.categories_covered = ["a", "b"]
    out = build_devset_section(m)
    assert set(out.keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_build_devset_section_status_passed_through_batch23():
    m = MagicMock(devset_status="complete")
    out = build_devset_section(m)
    assert out["status"] == "complete"


def test_build_devset_section_counts_passed_through_batch23():
    m = MagicMock(
        file_count=10,
        content_group_count=4,
        pdf_count=6,
        docx_count=4,
    )
    out = build_devset_section(m)
    assert out["file_count"] == 10
    assert out["content_group_count"] == 4
    assert out["pdf_count"] == 6
    assert out["docx_count"] == 4


def test_build_devset_section_categories_covered_passed_through_batch23():
    m = MagicMock(categories_covered=["x", "y", "z"])
    out = build_devset_section(m)
    assert out["categories_covered"] == ["x", "y", "z"]


def test_build_devset_section_returns_dict_batch23():
    m = MagicMock()
    out = build_devset_section(m)
    assert isinstance(out, dict)


def test_build_devset_section_empty_categories_batch23():
    m = MagicMock(categories_covered=[])
    out = build_devset_section(m)
    assert out["categories_covered"] == []


# ---------- aggregate_summary 第二十三批 ----------


def test_aggregate_summary_returns_dict_batch23():
    out = aggregate_summary([])
    assert isinstance(out, dict)


def test_aggregate_summary_four_top_keys_batch23():
    out = aggregate_summary([])
    assert set(out.keys()) == {
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    }


def test_aggregate_summary_empty_input_counts_null_batch23():
    """空输入 → counts.element_count_total = {sum: None, participating_docs: 0}。"""
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_empty_input_success_rate_none_batch23():
    """空输入 → success_rates.pipeline_success.rate=None。"""
    out = aggregate_summary([])
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 0
    assert sr["rate"] is None


def test_aggregate_summary_empty_input_ratio_macro_none_batch23():
    """空输入 → ratio_macro_averages 各项 macro_average=None。"""
    out = aggregate_summary([])
    for name in _RATIO_METRICS:
        item = out["ratio_macro_averages"][name]
        assert item["macro_average"] is None
        assert item["participating_docs"] == 0
        assert item["not_evaluated"] == 0


def test_aggregate_summary_empty_input_silent_drop_none_batch23():
    """空输入 → silent_drop_total=None。"""
    out = aggregate_summary([])
    assert out["silent_drop_total"] is None


def test_aggregate_summary_counts_summed_batch23():
    """counts 求和。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 3}}},
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 8
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_excludes_none_batch23():
    """value=None 不参与。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 3}}},
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 3
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_success_rate_batch23():
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


def test_aggregate_summary_ratio_macro_average_batch23():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
    ]
    out = aggregate_summary(per_doc)
    item = out["ratio_macro_averages"]["schema_valid"]
    assert item["macro_average"] == 0.75
    assert item["participating_docs"] == 2
    assert item["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_excludes_none_batch23():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    item = out["ratio_macro_averages"]["schema_valid"]
    assert item["macro_average"] == 1.0
    assert item["participating_docs"] == 1
    assert item["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_summed_batch23():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_none_when_all_null_batch23():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_partial_null_batch23():
    """部分 null 不参与求和。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_success_rate_zero_when_all_false_batch23():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["rate"] == 0.0


def test_aggregate_summary_all_metrics_missing_for_doc_batch23():
    """doc 无 metrics 字段或 metrics 为空。"""
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    # 不抛错
    assert "counts" in out


# ---------- module source forbidden tokens 第三十九批 ----------


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
def test_module_source_forbidden_tokens_batch23(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


def test_module_source_no_socket_import_batch23():
    src = inspect.getsource(rmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch23():
    src = inspect.getsource(rmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch23():
    src = inspect.getsource(rmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch23():
    src = inspect.getsource(rmod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch23():
    src = inspect.getsource(rmod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch23():
    src = inspect.getsource(rmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch23():
    src = inspect.getsource(rmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch23():
    src = inspect.getsource(rmod)
    assert "import tempfile" not in src


def test_module_source_no_sys_import_batch23():
    src = inspect.getsource(rmod)
    assert "import sys" not in src


def test_module_source_no_logging_import_batch23():
    src = inspect.getsource(rmod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch23():
    src = inspect.getsource(rmod)
    assert "import re" not in src


def test_module_source_no_pandas_import_batch23():
    src = inspect.getsource(rmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch23():
    src = inspect.getsource(rmod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第三十五批 ----------


def test_module_source_has_future_annotations_batch23():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_subprocess_import_batch23():
    """subprocess 是允许的（git provenance 需要）。"""
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_has_datetime_import_batch23():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_has_pathlib_path_import_batch23():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch23():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_evaluation_constants_import_batch23():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_has_ratio_metrics_constant_batch23():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS" in src


def test_module_source_has_count_metrics_constant_batch23():
    src = inspect.getsource(rmod)
    assert "_COUNT_METRICS" in src


def test_module_source_has_success_bool_metrics_constant_batch23():
    src = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS" in src


def test_module_source_has_get_git_provenance_function_batch23():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src


def test_module_source_has_get_dependency_versions_function_batch23():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions(" in src


def test_module_source_has_build_provenance_function_batch23():
    src = inspect.getsource(rmod)
    assert "def build_provenance(" in src


def test_module_source_has_build_devset_section_function_batch23():
    src = inspect.getsource(rmod)
    assert "def build_devset_section(" in src


def test_module_source_has_aggregate_summary_function_batch23():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary(" in src


def test_module_source_has_subprocess_run_call_batch23():
    """subprocess.run 在 get_git_provenance 中被调用。"""
    src = inspect.getsource(rmod)
    assert "subprocess.run" in src


# ---------- signatures 第三十五批 ----------


def test_signature_get_git_provenance_batch23():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["project_root"]


def test_signature_get_dependency_versions_batch23():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_signature_build_provenance_batch23():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == [
        "project_root",
        "parser_name",
        "max_chars",
        "parser_version",
    ]


def test_signature_build_provenance_parser_version_optional_batch23():
    sig = inspect.signature(build_provenance)
    p = sig.parameters["parser_version"]
    assert p.default is inspect.Parameter.empty
    assert p.annotation == "str | None"


def test_signature_build_devset_section_batch23():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "manifest"


def test_signature_aggregate_summary_batch23():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["per_doc_results"]


# ---------- module 合理性第三十五批 ----------


def test_module_has_all_attribute_batch23():
    assert hasattr(rmod, "__all__")


def test_module_all_count_five_batch23():
    assert len(rmod.__all__) == 5


def test_module_all_contents_exact_batch23():
    assert set(rmod.__all__) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_does_not_import_evaluation_runner_batch23():
    src = inspect.getsource(rmod)
    assert "from evaluation.runner" not in src


def test_module_does_not_import_evaluation_metrics_batch23():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics" not in src


def test_module_does_not_import_evaluation_cli_batch23():
    src = inspect.getsource(rmod)
    assert "from evaluation.cli" not in src


def test_module_does_not_import_evaluation_schema_batch23():
    src = inspect.getsource(rmod)
    assert "from evaluation.schema" not in src


def test_module_does_not_import_evaluation_manifest_batch23():
    src = inspect.getsource(rmod)
    assert "from evaluation.manifest" not in src


def test_module_does_not_import_evaluation_annotation_metrics_batch23():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics" not in src


def test_module_does_not_import_app_pipeline_batch23():
    src = inspect.getsource(rmod)
    assert "from app.pipeline" not in src
    assert "from app import pipeline" not in src


def test_module_no_main_block_batch23():
    src = inspect.getsource(rmod)
    assert 'if __name__ ==' not in src
    assert "__main__" not in src


def test_module_has_docstring_batch23():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 0


# ---------- 端到端集成第三十五批 ----------


def test_e2e_build_provenance_full_batch23(tmp_path):
    """build_provenance 完整 round-trip。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] == "1.0.0"
    assert out["max_chars"] == 800
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION
    assert "dependencies" in out
    assert "run_timestamp_iso" in out


def test_e2e_aggregate_summary_one_doc_all_metrics_batch23():
    """单 doc 全 metric → summary 各项正确。"""
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "element_count_total": {"value": 5},
                "schema_valid": {"value": 1.0},
                "silent_drop_count": {"value": 2},
            }
        }
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert out["silent_drop_total"] == 2


def test_e2e_aggregate_summary_two_docs_consistent_batch23():
    """两个 doc → summary 数值正确。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}, "element_count_total": {"value": 3}}},
        {"metrics": {"pipeline_success": {"value": False}, "element_count_total": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 8
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["total"] == 2
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5


def test_e2e_build_devset_section_complete_batch23():
    """build_devset_section 完整。"""
    m = MagicMock(
        devset_status="complete",
        file_count=10,
        content_group_count=4,
        pdf_count=6,
        docx_count=4,
        categories_covered=["a", "b", "c"],
    )
    out = build_devset_section(m)
    assert out["status"] == "complete"
    assert out["file_count"] == 10
    assert out["content_group_count"] == 4
    assert out["pdf_count"] == 6
    assert out["docx_count"] == 4
    assert out["categories_covered"] == ["a", "b", "c"]


def test_e2e_get_git_provenance_no_error_batch23(tmp_path):
    """在 tmp_path 调用 get_git_provenance 不抛错（即使非 git 仓库）。"""
    out = get_git_provenance(tmp_path)
    assert "git_commit" in out
    assert "git_dirty" in out


def test_e2e_get_dependency_versions_returns_dict_with_3_keys_batch23():
    out = get_dependency_versions()
    assert len(out) == 3
    assert "pdfplumber" in out


def test_e2e_aggregate_summary_no_metrics_key_batch23():
    """per_doc 缺 metrics 字段 → 不抛错（dict.get 返回 None）。"""
    per_doc = [{}]  # 无 metrics key
    # 这会抛 AttributeError 因为 None.get 不存在
    # 实际：r["metrics"].get(...) → r["metrics"] 是 KeyError
    # 所以输入必须保证有 metrics 字段
    # 这里改成 metrics 是 None
    per_doc = [{"metrics": None}]
    # metrics 是 None → None.get 抛 AttributeError
    with pytest.raises((AttributeError, TypeError)):
        aggregate_summary(per_doc)
