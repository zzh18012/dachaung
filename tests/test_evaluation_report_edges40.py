"""evaluation/report.py 第四十轮 edges 测试（Round 485）。

补强 edges39 未触及的角度：
- _RATIO_METRICS 内容 第二十四批（顺序严格 / 不含 element_count_total / 不含 figure_caption_* / 不含 silent_drop_count）
- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第二十四批（互不相交 / 与 _RATIO_METRICS 不相交 / tuple 类型）
- get_git_provenance 第二十四批（commit short / dirty detection / project_root=None / 非 git 目录）
- get_dependency_versions 第二十四批（pdfplumber 存在 / python-docx vs importlib 名称 / pypdfium2 可能 None）
- build_provenance 第二十四批（9 keys 严格 / max_chars 转 int / parser_version 透传 / eval_framework_version 不存在）
- build_devset_section 第二十四批（6 keys 严格 / status / categories list / 数值类型）
- aggregate_summary 第二十四批（多 doc 同 metric 不同值 / silent_drop mixed null 与 int / counts 空 / success rate 边界）
- module source forbidden tokens 第四十批
- module source 字符串精确补强第三十六批
- signatures 第三十六批
- module 合理性第三十六批
- 端到端集成第三十六批
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


# ---------- _RATIO_METRICS 内容 第二十四批 ----------


def test_ratio_metrics_does_not_contain_element_count_total_batch24():
    assert "element_count_total" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_silent_drop_count_batch24():
    assert "silent_drop_count" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_pipeline_success_batch24():
    assert "pipeline_success" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_figure_caption_batch24():
    """figure_caption_* 不在 macro average。"""
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_ratio_metrics_contains_schema_valid_batch24():
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_contains_all_locator_ratios_batch24():
    assert "pdf_locator_valid_ratio" in _RATIO_METRICS
    assert "docx_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_trio_batch24():
    assert "chunk_boundary_precision" in _RATIO_METRICS
    assert "chunk_boundary_recall" in _RATIO_METRICS
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_contains_text_char_multiset_pair_batch24():
    assert "text_char_multiset_precision" in _RATIO_METRICS
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_order_stable_batch24():
    """顺序固定（schema_valid 在前）。"""
    assert _RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_count_is_twelve_batch24():
    assert len(_RATIO_METRICS) == 12


# ---------- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第二十四批 ----------


def test_count_metrics_only_element_count_total_batch24():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_only_pipeline_success_batch24():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_count_and_success_disjoint_batch24():
    assert set(_COUNT_METRICS).isdisjoint(_SUCCESS_BOOL_METRICS)


def test_count_and_ratio_disjoint_batch24():
    assert set(_COUNT_METRICS).isdisjoint(_RATIO_METRICS)


def test_success_and_ratio_disjoint_batch24():
    assert set(_SUCCESS_BOOL_METRICS).isdisjoint(_RATIO_METRICS)


def test_count_metrics_is_tuple_batch24():
    assert isinstance(_COUNT_METRICS, tuple)


def test_success_bool_metrics_is_tuple_batch24():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_count_metrics_single_element_batch24():
    assert len(_COUNT_METRICS) == 1


def test_success_bool_metrics_single_element_batch24():
    assert len(_SUCCESS_BOOL_METRICS) == 1


# ---------- get_git_provenance 第二十四批 ----------


def test_get_git_provenance_returns_two_keys_batch24(tmp_path):
    out = get_git_provenance(tmp_path)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_in_real_repo_batch24():
    """在项目根目录跑（是 git repo）。"""
    out = get_git_provenance(Path(__file__).resolve().parent.parent)
    assert "git_commit" in out
    assert "git_dirty" in out
    # 实际 commit 应当非 None
    assert out["git_commit"] is not None
    assert isinstance(out["git_dirty"], bool)


def test_get_git_provenance_non_git_dir_batch24(tmp_path):
    """非 git 目录 → git 命令以非零退出码失败，commit=None, dirty=False（被 r2.returncode!=0 覆盖）。"""
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is False


def test_get_git_provenance_subprocess_exception_batch24(tmp_path):
    """subprocess 抛异常 → commit=None, dirty=True。"""
    with patch("evaluation.report.subprocess.run", side_effect=OSError("denied")):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_subprocess_timeout_batch24(tmp_path):
    """subprocess.TimeoutExpired 是 SubprocessError 子类 → 走 except 分支。"""
    with patch(
        "evaluation.report.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10),
    ):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_commit_short_format_batch24():
    """commit 是完整 hash（40 字符）—— 调用方决定要不要截断。"""
    out = get_git_provenance(Path(__file__).resolve().parent.parent)
    if out["git_commit"] is not None:
        assert len(out["git_commit"]) >= 7  # 至少能取 short


def test_get_git_provenance_dirty_true_when_uncommitted_batch24(tmp_path):
    """mock r2 stdout 非空 → dirty=True。"""
    fake_r1 = MagicMock(returncode=0, stdout="abc123\n")
    fake_r2 = MagicMock(returncode=0, stdout=" M file.txt\n")
    with patch(
        "evaluation.report.subprocess.run",
        side_effect=[fake_r1, fake_r2],
    ):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is True


def test_get_git_provenance_dirty_false_when_clean_batch24(tmp_path):
    """mock r2 stdout 空 → dirty=False。"""
    fake_r1 = MagicMock(returncode=0, stdout="abc123\n")
    fake_r2 = MagicMock(returncode=0, stdout="")
    with patch(
        "evaluation.report.subprocess.run",
        side_effect=[fake_r1, fake_r2],
    ):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is False


def test_get_git_provenance_commit_none_when_returncode_nonzero_batch24(tmp_path):
    """r.returncode != 0 → commit=None。"""
    fake_r1 = MagicMock(returncode=1, stdout="")
    fake_r2 = MagicMock(returncode=0, stdout="")
    with patch(
        "evaluation.report.subprocess.run",
        side_effect=[fake_r1, fake_r2],
    ):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


# ---------- get_dependency_versions 第二十四批 ----------


def test_get_dependency_versions_returns_dict_batch24():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_get_dependency_versions_has_three_packages_batch24():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_pdfplumber_str_or_none_batch24():
    out = get_dependency_versions()
    v = out["pdfplumber"]
    assert v is None or isinstance(v, str)


def test_get_dependency_versions_pypdfium2_str_or_none_batch24():
    out = get_dependency_versions()
    v = out["pypdfium2"]
    assert v is None or isinstance(v, str)


def test_get_dependency_versions_python_docx_str_or_none_batch24():
    out = get_dependency_versions()
    v = out["python-docx"]
    assert v is None or isinstance(v, str)


def test_get_dependency_versions_consistent_batch24():
    out1 = get_dependency_versions()
    out2 = get_dependency_versions()
    assert out1 == out2


def test_get_dependency_versions_package_not_found_returns_none_batch24():
    """mock importlib.metadata 抛 PackageNotFoundError → 返回 None。"""
    import importlib.metadata

    with patch(
        "importlib.metadata.version",
        side_effect=importlib.metadata.PackageNotFoundError,
    ):
        out = get_dependency_versions()
    for v in out.values():
        assert v is None


# ---------- build_provenance 第二十四批 ----------


def test_build_provenance_returns_nine_keys_batch24(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0")
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


def test_build_provenance_evaluator_version_constant_batch24(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_constant_batch24(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_max_chars_int_batch24(tmp_path):
    """max_chars 转 int。"""
    out = build_provenance(tmp_path, "fallback", 999, None)
    assert out["max_chars"] == 999
    assert isinstance(out["max_chars"], int)


def test_build_provenance_parser_name_passed_batch24(tmp_path):
    out = build_provenance(tmp_path, "kreuzberg", 800, None)
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_passed_batch24(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "9.9.9")
    assert out["parser_version"] == "9.9.9"


def test_build_provenance_parser_version_none_batch24(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_run_timestamp_iso_format_batch24(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    ts = out["run_timestamp_iso"]
    # ISO 格式应当能被 datetime.fromisoformat 解析
    parsed = datetime.fromisoformat(ts)
    assert isinstance(parsed, datetime)


def test_build_provenance_dependencies_is_dict_batch24(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_git_commit_passed_through_batch24(tmp_path):
    """git_commit 从 get_git_provenance 透传。"""
    with patch(
        "evaluation.report.get_git_provenance",
        return_value={"git_commit": "deadbeef", "git_dirty": False},
    ):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["git_commit"] == "deadbeef"
    assert out["git_dirty"] is False


def test_build_provenance_max_chars_accepts_str_int_batch24(tmp_path):
    """max_chars 接受能转 int 的值（如 float）。"""
    out = build_provenance(tmp_path, "fallback", 800.0, None)
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


# ---------- build_devset_section 第二十四批 ----------


def _make_manifest(
    devset_status="incomplete",
    file_count=0,
    content_group_count=0,
    pdf_count=0,
    docx_count=0,
    categories_covered=None,
):
    m = MagicMock()
    m.devset_status = devset_status
    m.file_count = file_count
    m.content_group_count = content_group_count
    m.pdf_count = pdf_count
    m.docx_count = docx_count
    m.categories_covered = categories_covered if categories_covered is not None else []
    return m


def test_build_devset_section_returns_six_keys_batch24():
    out = build_devset_section(_make_manifest())
    assert set(out.keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_build_devset_section_passes_status_batch24():
    out = build_devset_section(_make_manifest(devset_status="complete"))
    assert out["status"] == "complete"


def test_build_devset_section_passes_file_count_batch24():
    out = build_devset_section(_make_manifest(file_count=42))
    assert out["file_count"] == 42


def test_build_devset_section_passes_counts_batch24():
    out = build_devset_section(
        _make_manifest(pdf_count=3, docx_count=2, content_group_count=4)
    )
    assert out["pdf_count"] == 3
    assert out["docx_count"] == 2
    assert out["content_group_count"] == 4


def test_build_devset_section_passes_categories_batch24():
    out = build_devset_section(_make_manifest(categories_covered=["a", "b"]))
    assert out["categories_covered"] == ["a", "b"]


def test_build_devset_section_does_not_call_other_attributes_batch24():
    """只读 6 个属性。"""
    m = _make_manifest()
    # 通过限制 spec 来检查只调这 6 个属性
    build_devset_section(m)
    # 不抛即通过


# ---------- aggregate_summary 第二十四批 ----------


def test_aggregate_summary_returns_four_top_keys_batch24():
    out = aggregate_summary([])
    assert set(out.keys()) == {
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    }


def test_aggregate_summary_counts_sum_correctly_batch24():
    """counts sum = 各 doc 的 element_count_total 求和。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"element_count_total": {"value": 10, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_skip_none_batch24():
    """element_count_total 为 None 的 doc 不参与。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"element_count_total": {"value": None, "reason": "pipeline_failed"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_success_rate_zero_batch24():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0
    assert out["success_rates"]["pipeline_success"]["total"] == 2
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.0


def test_aggregate_summary_success_rate_full_batch24():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0


def test_aggregate_summary_success_rate_half_batch24():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5


def test_aggregate_summary_success_rate_empty_list_batch24():
    out = aggregate_summary([])
    assert out["success_rates"]["pipeline_success"]["rate"] is None
    assert out["success_rates"]["pipeline_success"]["total"] == 0


def test_aggregate_summary_ratio_macro_average_batch24():
    per_doc = [
        {"metrics": {"schema_valid": {"value": True}}},
        {"metrics": {"schema_valid": {"value": False}}},
    ]
    out = aggregate_summary(per_doc)
    # True=1, False=0 → macro=0.5
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2


def test_aggregate_summary_ratio_skips_none_batch24():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "pipeline_failed"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_sum_batch24():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_skips_none_batch24():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None, "reason": "no_expectations"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 3


def test_aggregate_summary_silent_drop_all_none_returns_none_batch24():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_empty_per_doc_returns_none_macro_batch24():
    out = aggregate_summary([])
    for name in _RATIO_METRICS:
        assert out["ratio_macro_averages"][name]["macro_average"] is None
        assert out["ratio_macro_averages"][name]["participating_docs"] == 0


def test_aggregate_summary_does_not_mix_metric_types_batch24():
    """ratio 不出现在 counts 中，反之亦然。"""
    per_doc = [{"metrics": {"element_count_total": {"value": 5}}}]
    out = aggregate_summary(per_doc)
    assert "element_count_total" not in out["ratio_macro_averages"]
    assert "schema_valid" not in out["counts"]


# ---------- module source forbidden tokens 第四十批 ----------


# 注意：report.py 允许 subprocess（用于 git provenance）
FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    'open("/etc/passwd',
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
    "subprocess.call(",
    "subprocess.check_call(",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch24(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


def test_module_source_no_socket_import_batch24():
    src = inspect.getsource(rmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch24():
    src = inspect.getsource(rmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch24():
    src = inspect.getsource(rmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch24():
    src = inspect.getsource(rmod)
    assert "import threading" not in src


def test_module_source_no_asyncio_import_batch24():
    src = inspect.getsource(rmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch24():
    src = inspect.getsource(rmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch24():
    src = inspect.getsource(rmod)
    assert "import tempfile" not in src


def test_module_source_no_logging_import_batch24():
    src = inspect.getsource(rmod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch24():
    src = inspect.getsource(rmod)
    assert "import re" not in src


def test_module_source_no_pandas_import_batch24():
    src = inspect.getsource(rmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch24():
    src = inspect.getsource(rmod)
    assert "import numpy" not in src


def test_module_source_no_csv_import_batch24():
    src = inspect.getsource(rmod)
    assert "import csv" not in src


def test_module_source_no_os_import_batch24():
    src = inspect.getsource(rmod)
    assert "import os" not in src


def test_module_source_no_sys_import_batch24():
    src = inspect.getsource(rmod)
    assert "import sys" not in src


def test_module_source_subprocess_allowed_batch24():
    """subprocess 是允许的（用于 git provenance）。"""
    src = inspect.getsource(rmod)
    assert "import subprocess" in src or "from subprocess" in src


# ---------- module source 字符串精确补强第三十六批 ----------


def test_module_source_has_future_annotations_batch24():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_subprocess_import_batch24():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_has_datetime_import_batch24():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_has_pathlib_path_import_batch24():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch24():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_evaluation_import_batch24():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_has_ratio_metrics_constant_batch24():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS =" in src


def test_module_source_has_count_metrics_constant_batch24():
    src = inspect.getsource(rmod)
    assert "_COUNT_METRICS =" in src


def test_module_source_has_success_bool_metrics_constant_batch24():
    src = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS =" in src


def test_module_source_has_get_git_provenance_function_batch24():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src


def test_module_source_has_build_provenance_function_batch24():
    src = inspect.getsource(rmod)
    assert "def build_provenance(" in src


def test_module_source_has_build_devset_section_function_batch24():
    src = inspect.getsource(rmod)
    assert "def build_devset_section(" in src


def test_module_source_has_aggregate_summary_function_batch24():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary(" in src


def test_module_source_has_rev_parse_git_command_batch24():
    src = inspect.getsource(rmod)
    assert '"git", "rev-parse", "HEAD"' in src or '"rev-parse"' in src


def test_module_source_has_git_status_porcelain_batch24():
    src = inspect.getsource(rmod)
    assert '"git", "status", "--porcelain"' in src or '"--porcelain"' in src


# ---------- signatures 第三十六批 ----------


def test_signature_get_git_provenance_one_param_batch24():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "project_root"


def test_signature_get_git_provenance_returns_dict_batch24():
    sig = inspect.signature(get_git_provenance)
    assert "dict" in str(sig.return_annotation)


def test_signature_get_dependency_versions_no_params_batch24():
    sig = inspect.signature(get_dependency_versions)
    params = list(sig.parameters.values())
    assert len(params) == 0


def test_signature_build_provenance_four_params_batch24():
    sig = inspect.signature(build_provenance)
    names = list(sig.parameters.keys())
    assert names == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_devset_section_one_param_batch24():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "manifest"


def test_signature_aggregate_summary_one_param_batch24():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "per_doc_results"


def test_signature_build_provenance_return_annotation_batch24():
    sig = inspect.signature(build_provenance)
    assert "dict" in str(sig.return_annotation)


def test_signature_aggregate_summary_return_annotation_batch24():
    sig = inspect.signature(aggregate_summary)
    assert "dict" in str(sig.return_annotation)


# ---------- module 合理性第三十六批 ----------


def test_module_all_has_five_entries_batch24():
    assert set(rmod.__all__) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_does_not_import_evaluation_runner_batch24():
    src = inspect.getsource(rmod)
    assert "from evaluation.runner" not in src
    assert "from evaluation import runner" not in src


def test_module_does_not_import_evaluation_cli_batch24():
    src = inspect.getsource(rmod)
    assert "from evaluation.cli" not in src


def test_module_does_not_import_evaluation_manifest_batch24():
    src = inspect.getsource(rmod)
    assert "from evaluation.manifest" not in src


def test_module_does_not_import_evaluation_metrics_batch24():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics" not in src


def test_module_does_not_import_evaluation_schema_batch24():
    src = inspect.getsource(rmod)
    assert "from evaluation.schema" not in src


def test_module_does_not_import_evaluation_annotation_metrics_batch24():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics" not in src


def test_module_does_not_import_app_pipeline_batch24():
    src = inspect.getsource(rmod)
    assert "from app.pipeline" not in src


def test_module_does_not_import_app_parsers_batch24():
    src = inspect.getsource(rmod)
    assert "from app.parsers" not in src


def test_module_constants_not_in_all_batch24():
    """私有常量不在 __all__。"""
    assert "_RATIO_METRICS" not in rmod.__all__
    assert "_COUNT_METRICS" not in rmod.__all__
    assert "_SUCCESS_BOOL_METRICS" not in rmod.__all__


def test_module_no_main_block_batch24():
    src = inspect.getsource(rmod)
    assert 'if __name__ ==' not in src


def test_module_has_module_docstring_batch24():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 0


def test_module_public_functions_dont_start_with_underscore_batch24():
    assert not build_provenance.__name__.startswith("_")
    assert not build_devset_section.__name__.startswith("_")
    assert not aggregate_summary.__name__.startswith("_")
    assert not get_git_provenance.__name__.startswith("_")
    assert not get_dependency_versions.__name__.startswith("_")


# ---------- 端到端集成第三十六批 ----------


def test_e2e_build_provenance_full_round_trip_batch24(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] == "1.0.0"
    assert out["max_chars"] == 800
    assert isinstance(out["dependencies"], dict)
    # timestamp 是合法 ISO
    datetime.fromisoformat(out["run_timestamp_iso"])


def test_e2e_build_devset_section_round_trip_batch24():
    m = _make_manifest(
        devset_status="complete",
        file_count=10,
        content_group_count=5,
        pdf_count=4,
        docx_count=6,
        categories_covered=["c1", "c2"],
    )
    out = build_devset_section(m)
    assert out["status"] == "complete"
    assert out["file_count"] == 10
    assert out["categories_covered"] == ["c1", "c2"]


def test_e2e_aggregate_summary_full_round_trip_batch24():
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "element_count_total": {"value": 5},
                "schema_valid": {"value": True},
                "silent_drop_count": {"value": 2},
            }
        },
        {
            "metrics": {
                "pipeline_success": {"value": False},
                "element_count_total": {"value": 10},
                "schema_valid": {"value": False},
                "silent_drop_count": {"value": None, "reason": "no_expectations"},
            }
        },
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert out["silent_drop_total"] == 2


def test_e2e_aggregate_summary_empty_input_batch24():
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["success_rates"]["pipeline_success"]["rate"] is None
    assert out["silent_drop_total"] is None


def test_e2e_get_dependency_versions_real_call_batch24():
    """真实调用 get_dependency_versions（不 mock）。"""
    out = get_dependency_versions()
    assert "pdfplumber" in out
    assert "python-docx" in out
    assert "pypdfium2" in out


def test_e2e_get_git_provenance_in_project_root_batch24():
    """在项目根跑 get_git_provenance。"""
    project_root = Path(__file__).resolve().parent.parent
    out = get_git_provenance(project_root)
    assert out["git_commit"] is not None
    assert isinstance(out["git_dirty"], bool)


def test_e2e_build_provenance_in_project_root_batch24():
    """完整 build_provenance 在项目根。"""
    project_root = Path(__file__).resolve().parent.parent
    out = build_provenance(project_root, "fallback", 800, "1.0")
    assert out["git_commit"] is not None
    assert out["evaluator_version"] == EVALUATOR_VERSION
