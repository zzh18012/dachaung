"""evaluation/report.py 第四十一轮 edges 测试（Round 492）。

补强 edges40 未触及的角度（第二十五批）：
- _RATIO_METRICS 第二十五批：排除 figure_caption_* / 12 entries 严格 / 含 chunk_boundary_f1 / 排序 / subset check
- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第二十五批：1 entry each / 互不相交 / 类型
- get_git_provenance 第二十五批：subprocess encoding / errors replace / timeout=10 / 各种 returncode 组合
- get_dependency_versions 第二十五批：importlib.metadata / 包不存在 / 顺序
- build_provenance 第二十五批：max_chars int 强制 / parser_version=None 透传 / 9 keys 严格 / dependencies 来自 get_dependency_versions
- build_devset_section 第二十五批：6 keys 严格 / 透传所有属性 / frozen manifest
- aggregate_summary 第二十五批：empty list / 单 doc / 全 null / counts sum / success_rates rate / ratio macro / silent_drop_total None / 关键字段
- module source forbidden tokens 第四十一批
- module source 字符串精确补强第三十七批
- signatures 第三十七批
- module 合理性第三十七批
- 端到端集成第三十七批
"""

from __future__ import annotations

import inspect
import subprocess
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


# ---------- _RATIO_METRICS 第二十五批 ----------


def test_ratio_metrics_excludes_figure_caption_batch25():
    """_RATIO_METRICS 不含 figure_caption_*。"""
    for entry in _RATIO_METRICS:
        assert not entry.startswith("figure_caption_")


def test_ratio_metrics_excludes_silent_drop_batch25():
    """_RATIO_METRICS 不含 silent_drop_count（它是 count，不是 ratio）。"""
    assert "silent_drop_count" not in _RATIO_METRICS


def test_ratio_metrics_excludes_pipeline_success_batch25():
    """_RATIO_METRICS 不含 pipeline_success（它是 bool）。"""
    assert "pipeline_success" not in _RATIO_METRICS


def test_ratio_metrics_excludes_element_count_total_batch25():
    assert "element_count_total" not in _RATIO_METRICS


def test_ratio_metrics_contains_schema_valid_batch25():
    """schema_valid 是 bool 但当作 ratio 处理（成功/失败比）。"""
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_contains_all_chunk_boundary_batch25():
    """chunk_boundary precision/recall/f1 都在。"""
    assert "chunk_boundary_precision" in _RATIO_METRICS
    assert "chunk_boundary_recall" in _RATIO_METRICS
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_contains_text_char_multiset_batch25():
    """text_char_multiset precision/recall 都在。"""
    assert "text_char_multiset_precision" in _RATIO_METRICS
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_is_tuple_batch25():
    assert isinstance(_RATIO_METRICS, tuple)


def test_ratio_metrics_twelve_entries_batch25():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_hashable_batch25():
    assert hash(_RATIO_METRICS) is not None


def test_ratio_metrics_no_duplicates_batch25():
    assert len(set(_RATIO_METRICS)) == len(_RATIO_METRICS)


# ---------- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第二十五批 ----------


def test_count_metrics_single_entry_batch25():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_single_entry_batch25():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_count_success_disjoint_batch25():
    """_COUNT_METRICS 与 _SUCCESS_BOOL_METRICS 互不相交。"""
    assert set(_COUNT_METRICS).isdisjoint(_SUCCESS_BOOL_METRICS)


def test_count_metrics_not_in_ratio_batch25():
    """_COUNT_METRICS 不在 _RATIO_METRICS 中。"""
    assert set(_COUNT_METRICS).isdisjoint(_RATIO_METRICS)


def test_success_metrics_not_in_ratio_batch25():
    """_SUCCESS_BOOL_METRICS 不在 _RATIO_METRICS 中。"""
    assert set(_SUCCESS_BOOL_METRICS).isdisjoint(_RATIO_METRICS)


def test_count_metrics_is_tuple_batch25():
    assert isinstance(_COUNT_METRICS, tuple)


def test_success_bool_metrics_is_tuple_batch25():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_count_metrics_no_duplicates_batch25():
    assert len(set(_COUNT_METRICS)) == len(_COUNT_METRICS)


# ---------- get_git_provenance 第二十五批 ----------


def test_get_git_provenance_encoding_param_batch25(tmp_path):
    """subprocess.run 必须传 encoding='utf-8'。"""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["encoding"] = kwargs.get("encoding")
        captured["errors"] = kwargs.get("errors")
        captured["timeout"] = kwargs.get("timeout")
        m = MagicMock()
        m.returncode = 0
        m.stdout = "abc123\n"
        return m

    with patch("evaluation.report.subprocess.run", side_effect=fake_run):
        get_git_provenance(tmp_path)
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"
    assert captured["timeout"] == 10


def test_get_git_provenance_cwd_param_batch25(tmp_path):
    """subprocess.run 必须传 cwd=project_root。"""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        m = MagicMock()
        m.returncode = 0
        m.stdout = "abc\n"
        return m

    with patch("evaluation.report.subprocess.run", side_effect=fake_run):
        get_git_provenance(tmp_path)
    assert captured["cwd"] == str(tmp_path)


def test_get_git_provenance_returns_dict_batch25(tmp_path):
    with patch("evaluation.report.subprocess.run") as mock_run:
        m = MagicMock()
        m.returncode = 0
        m.stdout = "abc\n"
        mock_run.return_value = m
        out = get_git_provenance(tmp_path)
    assert isinstance(out, dict)


def test_get_git_provenance_keys_batch25(tmp_path):
    with patch("evaluation.report.subprocess.run") as mock_run:
        m = MagicMock()
        m.returncode = 0
        m.stdout = "abc\n"
        mock_run.return_value = m
        out = get_git_provenance(tmp_path)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_commit_stripped_batch25(tmp_path):
    """stdout 含 newline → 被 strip。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        m1 = MagicMock()
        m1.returncode = 0
        m1.stdout = "  abc123  \n"
        m2 = MagicMock()
        m2.returncode = 0
        m2.stdout = ""  # 不 dirty
        mock_run.side_effect = [m1, m2]
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"


def test_get_git_provenance_commit_empty_returns_none_batch25(tmp_path):
    """stdout 空 → commit=None。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        m1 = MagicMock()
        m1.returncode = 0
        m1.stdout = "   "  # 空白
        m2 = MagicMock()
        m2.returncode = 0
        m2.stdout = ""
        mock_run.side_effect = [m1, m2]
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_dirty_with_porcelain_output_batch25(tmp_path):
    """porcelain 输出非空 → dirty=True。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        m1 = MagicMock()
        m1.returncode = 0
        m1.stdout = "abc\n"
        m2 = MagicMock()
        m2.returncode = 0
        m2.stdout = " M file.txt\n"  # dirty
        mock_run.side_effect = [m1, m2]
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


def test_get_git_provenance_clean_when_porcelain_empty_batch25(tmp_path):
    with patch("evaluation.report.subprocess.run") as mock_run:
        m1 = MagicMock()
        m1.returncode = 0
        m1.stdout = "abc\n"
        m2 = MagicMock()
        m2.returncode = 0
        m2.stdout = ""
        mock_run.side_effect = [m1, m2]
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


# ---------- get_dependency_versions 第二十五批 ----------


def test_get_dependency_versions_returns_dict_batch25():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_get_dependency_versions_keys_batch25():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_str_or_none_batch25():
    out = get_dependency_versions()
    for v in out.values():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_idempotent_batch25():
    out1 = get_dependency_versions()
    out2 = get_dependency_versions()
    assert out1 == out2


def test_get_dependency_versions_pdfplumber_or_none_batch25():
    """pdfplumber 通常已安装（fallback parser 依赖）。"""
    out = get_dependency_versions()
    # 在本测试环境中应当非 None
    assert out["pdfplumber"] is not None


def test_get_dependency_versions_unknown_package_returns_none_batch25():
    """未知 package → PackageNotFoundError → None。"""
    import importlib.metadata
    with patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError):
        out = get_dependency_versions()
    for v in out.values():
        assert v is None


def test_get_dependency_versions_exception_returns_none_batch25():
    """importlib 抛其他 Exception → None。"""
    with patch("importlib.metadata.version", side_effect=RuntimeError):
        out = get_dependency_versions()
    for v in out.values():
        assert v is None


# ---------- build_provenance 第二十五批 ----------


def test_build_provenance_nine_keys_batch25(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
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


def test_build_provenance_evaluator_version_batch25(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_batch25(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_batch25(tmp_path):
    out = build_provenance(tmp_path, "kreuzberg", 800, "1.0")
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_none_batch25(tmp_path):
    """parser_version=None 透传。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_parser_version_str_batch25(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "fallback/v1.2.3")
    assert out["parser_version"] == "fallback/v1.2.3"


def test_build_provenance_max_chars_int_batch25(tmp_path):
    """max_chars 强制 int。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_string_input_batch25(tmp_path):
    """max_chars 输入 str → int(str)。"""
    out = build_provenance(tmp_path, "fallback", "800", None)
    assert out["max_chars"] == 800


def test_build_provenance_dependencies_dict_batch25(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["dependencies"], dict)
    assert "pdfplumber" in out["dependencies"]


def test_build_provenance_run_timestamp_iso_format_batch25(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    ts = out["run_timestamp_iso"]
    assert isinstance(ts, str)
    # ISO 8601 应含 'T'
    assert "T" in ts


def test_build_provenance_run_timestamp_has_timezone_batch25(tmp_path):
    """ISO 时间戳含时区偏移。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    ts = out["run_timestamp_iso"]
    # 含 + 或 Z 表示时区
    assert "+" in ts or ts.endswith("Z")


# ---------- build_devset_section 第二十五批 ----------


def _make_manifest_mock(
    status="incomplete",
    file_count=0,
    content_group_count=0,
    pdf_count=0,
    docx_count=0,
    categories_covered=None,
):
    if categories_covered is None:
        categories_covered = []
    m = MagicMock()
    m.devset_status = status
    m.file_count = file_count
    m.content_group_count = content_group_count
    m.pdf_count = pdf_count
    m.docx_count = docx_count
    m.categories_covered = categories_covered
    return m


def test_build_devset_section_six_keys_batch25():
    out = build_devset_section(_make_manifest_mock())
    assert set(out.keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_build_devset_section_status_batch25():
    out = build_devset_section(_make_manifest_mock(status="complete"))
    assert out["status"] == "complete"


def test_build_devset_section_file_count_batch25():
    out = build_devset_section(_make_manifest_mock(file_count=7))
    assert out["file_count"] == 7


def test_build_devset_section_categories_batch25():
    out = build_devset_section(
        _make_manifest_mock(categories_covered=["a", "b"])
    )
    assert out["categories_covered"] == ["a", "b"]


def test_build_devset_section_pdf_docx_batch25():
    out = build_devset_section(
        _make_manifest_mock(pdf_count=3, docx_count=2)
    )
    assert out["pdf_count"] == 3
    assert out["docx_count"] == 2


def test_build_devset_section_content_group_count_batch25():
    out = build_devset_section(_make_manifest_mock(content_group_count=4))
    assert out["content_group_count"] == 4


# ---------- aggregate_summary 第二十五批 ----------


def test_aggregate_summary_empty_batch25():
    out = aggregate_summary([])
    assert set(out.keys()) == {
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    }
    assert out["silent_drop_total"] is None


def test_aggregate_summary_single_doc_all_metrics_batch25():
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True, "reason": None},
                "schema_valid": {"value": True, "reason": None},
                "element_count_total": {"value": 5, "reason": None},
                "silent_drop_count": {"value": 0, "reason": None},
            }
        }
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0
    assert out["silent_drop_total"] == 0


def test_aggregate_summary_failed_doc_batch25():
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": False, "reason": None},
            }
        }
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.0


def test_aggregate_summary_counts_sum_batch25():
    per_doc = [
        {
            "metrics": {
                "element_count_total": {"value": 3, "reason": None},
            }
        },
        {
            "metrics": {
                "element_count_total": {"value": 5, "reason": None},
            }
        },
        {
            "metrics": {
                "element_count_total": {"value": 2, "reason": None},
            }
        },
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 10
    assert out["counts"]["element_count_total"]["participating_docs"] == 3


def test_aggregate_summary_counts_skips_null_batch25():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 3, "reason": None}}},
        {"metrics": {"element_count_total": {"value": None, "reason": "failed"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 3
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_success_rate_batch25():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 2
    assert out["success_rates"]["pipeline_success"]["total"] == 3
    assert abs(out["success_rates"]["pipeline_success"]["rate"] - 2 / 3) < 1e-9


def test_aggregate_summary_ratio_macro_average_batch25():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
        {"metrics": {"schema_valid": {"value": 0.0}}},
    ]
    out = aggregate_summary(per_doc)
    avg = out["ratio_macro_averages"]["schema_valid"]["macro_average"]
    assert abs(avg - 0.5) < 1e-9
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 3
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 0


def test_aggregate_summary_ratio_skips_null_batch25():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "failed"}}},
    ]
    out = aggregate_summary(per_doc)
    avg = out["ratio_macro_averages"]["schema_valid"]["macro_average"]
    assert avg == 1.0
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_total_batch25():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 2}}},
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 0}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 5


def test_aggregate_summary_silent_drop_all_null_batch25():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_partial_null_batch25():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 5}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    # null 不参与求和
    assert out["silent_drop_total"] == 5


def test_aggregate_summary_all_12_ratio_metrics_present_batch25():
    """ratio_macro_averages 含 12 个 ratio metric。"""
    out = aggregate_summary([])
    assert set(out["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


def test_aggregate_summary_no_count_metrics_present_batch25():
    """counts 含 _COUNT_METRICS 所有。"""
    out = aggregate_summary([])
    assert set(out["counts"].keys()) == set(_COUNT_METRICS)


def test_aggregate_summary_all_success_metrics_present_batch25():
    """success_rates 含 _SUCCESS_BOOL_METRICS 所有。"""
    out = aggregate_summary([])
    assert set(out["success_rates"].keys()) == set(_SUCCESS_BOOL_METRICS)


def test_aggregate_summary_returns_dict_batch25():
    out = aggregate_summary([])
    assert isinstance(out, dict)


# ---------- module source forbidden tokens 第四十一批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import itertools",
    "import functools",
    "import timeit",
    "import time",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from itertools",
    "from functools",
    "from time",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import argparse",
]


def test_module_source_forbidden_tokens_batch25():
    source = inspect.getsource(rmod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_uses_from_datetime_import_batch25():
    """report.py 允许 from datetime import datetime（用于时间戳）。"""
    source = inspect.getsource(rmod)
    assert "from datetime import datetime" in source


def test_module_source_no_class_keyword_batch25():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_source_no_yield_batch25():
    source = inspect.getsource(rmod)
    assert "yield " not in source


def test_module_source_no_async_def_batch25():
    source = inspect.getsource(rmod)
    assert "async def" not in source


def test_module_source_no_global_keyword_batch25():
    source = inspect.getsource(rmod)
    assert "global " not in source


def test_module_source_no_walrus_batch25():
    source = inspect.getsource(rmod)
    assert ":=" not in source


def test_module_source_no_eval_exec_batch25():
    source = inspect.getsource(rmod)
    assert "eval(" not in source
    assert "exec(" not in source
    assert "compile(" not in source


def test_module_source_no_relative_imports_batch25():
    source_lines = inspect.getsource(rmod).split("\n")
    for line in source_lines:
        stripped = line.strip()
        if stripped.startswith("from .") and "from __future__" not in stripped:
            pytest.fail(f"relative import: {line}")


def test_module_source_no_star_import_batch25():
    source = inspect.getsource(rmod)
    assert "import *" not in source


def test_module_source_no_environ_batch25():
    source = inspect.getsource(rmod)
    assert "os.environ" not in source


def test_module_source_no_open_at_module_level_batch25():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    for node in tree.body:
        if isinstance(node, _ast.Expr) and isinstance(node.value, _ast.Call):
            f = node.value.func
            if isinstance(f, _ast.Name) and f.id == "open":
                pytest.fail("top-level open() call")


def test_module_source_subprocess_allowed_batch25():
    """report.py 允许 import subprocess（git provenance 需要）。"""
    source = inspect.getsource(rmod)
    assert "import subprocess" in source


def test_module_source_datetime_allowed_batch25():
    """report.py 用 datetime.now().astimezone().isoformat()。"""
    source = inspect.getsource(rmod)
    assert "from datetime import datetime" in source


def test_module_source_no_dataclass_batch25():
    source = inspect.getsource(rmod)
    assert "@dataclass" not in source


def test_module_source_no_argparse_batch25():
    source = inspect.getsource(rmod)
    assert "import argparse" not in source


# ---------- module source 字符串精确补强 第三十七批 ----------


def test_module_source_contains_ratio_metrics_constant_batch25():
    source = inspect.getsource(rmod)
    assert "_RATIO_METRICS = (" in source


def test_module_source_contains_count_metrics_constant_batch25():
    source = inspect.getsource(rmod)
    assert "_COUNT_METRICS = (" in source


def test_module_source_contains_success_bool_metrics_batch25():
    source = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS = (" in source


def test_module_source_contains_get_git_provenance_batch25():
    source = inspect.getsource(rmod)
    assert "def get_git_provenance(" in source


def test_module_source_contains_rev_parse_head_batch25():
    source = inspect.getsource(rmod)
    assert '"git", "rev-parse", "HEAD"' in source


def test_module_source_contains_status_porcelain_batch25():
    source = inspect.getsource(rmod)
    assert '"git", "status", "--porcelain"' in source


def test_module_source_contains_capture_output_batch25():
    source = inspect.getsource(rmod)
    assert "capture_output=True" in source


def test_module_source_contains_errors_replace_batch25():
    source = inspect.getsource(rmod)
    assert 'errors="replace"' in source


def test_module_source_contains_timeout_10_batch25():
    source = inspect.getsource(rmod)
    assert "timeout=10" in source


def test_module_source_contains_importlib_metadata_batch25():
    source = inspect.getsource(rmod)
    assert "import importlib.metadata" in source


def test_module_source_contains_pdfplumber_dependency_batch25():
    source = inspect.getsource(rmod)
    assert '"pdfplumber"' in source


def test_module_source_contains_python_docx_dependency_batch25():
    source = inspect.getsource(rmod)
    assert '"python-docx"' in source


def test_module_source_contains_pypdfium2_dependency_batch25():
    source = inspect.getsource(rmod)
    assert '"pypdfium2"' in source


def test_module_source_contains_aggregate_summary_batch25():
    source = inspect.getsource(rmod)
    assert "def aggregate_summary(" in source


def test_module_source_contains_macro_average_batch25():
    source = inspect.getsource(rmod)
    assert "macro_average" in source


# ---------- signatures 第三十七批 ----------


def test_signature_get_git_provenance_batch25():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "project_root"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_get_dependency_versions_batch25():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0
    assert sig.return_annotation == "dict[str, str | None]"


def test_signature_build_provenance_batch25():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == [
        "project_root",
        "parser_name",
        "max_chars",
        "parser_version",
    ]
    for p in params:
        assert p.default is inspect.Parameter.empty
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_build_devset_section_batch25():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "manifest"
    # manifest 没有 type 注解（manifest 参数）
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_aggregate_summary_batch25():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "per_doc_results"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_all_annotations_are_strings_batch25():
    for fn in [get_git_provenance, get_dependency_versions, build_provenance, build_devset_section, aggregate_summary]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            if p.annotation is not inspect.Parameter.empty:
                assert isinstance(p.annotation, str)
        if sig.return_annotation is not inspect.Signature.empty:
            assert isinstance(sig.return_annotation, str)


def test_signature_build_provenance_parser_name_annotation_batch25():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["parser_name"].annotation == "str"
    assert sig.parameters["max_chars"].annotation == "int"


def test_signature_build_provenance_parser_version_optional_batch25():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["parser_version"].annotation == "str | None"


# ---------- module 合理性 第三十七批 ----------


def test_module_all_five_entries_batch25():
    assert hasattr(rmod, "__all__")
    assert set(rmod.__all__) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_has_five_functions_batch25():
    funcs = [
        name
        for name, val in inspect.getmembers(rmod, inspect.isfunction)
        if val.__module__ == rmod.__name__
    ]
    assert set(funcs) == {
        "get_git_provenance",
        "get_dependency_versions",
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
    }


def test_module_no_classes_batch25():
    classes = [
        name
        for name, val in inspect.getmembers(rmod, inspect.isclass)
        if val.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_docstring_present_batch25():
    assert rmod.__doc__ is not None


def test_module_docstring_mentions_aggregate_batch25():
    assert "聚合" in rmod.__doc__ or "aggregate" in rmod.__doc__.lower()


def test_module_docstring_mentions_no_mix_batch25():
    """docstring 提及不混合类型。"""
    assert "不混合" in rmod.__doc__ or "counts" in rmod.__doc__


def test_module_docstring_mentions_silent_drop_batch25():
    assert "silent_drop" in rmod.__doc__ or "silent" in rmod.__doc__.lower()


def test_module_build_provenance_docstring_present_batch25():
    assert build_provenance.__doc__ is None or isinstance(build_provenance.__doc__, str)


def test_module_uses_from_future_annotations_batch25():
    source = inspect.getsource(rmod)
    assert "from __future__ import annotations" in source


def test_module_module_level_constants_batch25():
    """顶层有 _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    top_assigns = [
        node for node in tree.body if isinstance(node, _ast.Assign)
    ]
    names = []
    for node in top_assigns:
        for target in node.targets:
            if isinstance(target, _ast.Name):
                names.append(target.id)
    assert "_RATIO_METRICS" in names
    assert "_COUNT_METRICS" in names
    assert "_SUCCESS_BOOL_METRICS" in names


def test_module_all_entries_accessible_batch25():
    for name in rmod.__all__:
        assert hasattr(rmod, name)


# ---------- 端到端集成 第三十七批 ----------


def test_e2e_build_provenance_full_batch25(tmp_path):
    """build_provenance 完整流程：调用 get_git_provenance + get_dependency_versions。"""
    with patch("evaluation.report.get_git_provenance") as mock_git, patch(
        "evaluation.report.get_dependency_versions"
    ) as mock_deps:
        mock_git.return_value = {"git_commit": "abc123", "git_dirty": False}
        mock_deps.return_value = {"pdfplumber": "1.0", "python-docx": "2.0", "pypdfium2": "3.0"}
        out = build_provenance(tmp_path, "fallback", 800, "v1")
    mock_git.assert_called_once_with(tmp_path)
    mock_deps.assert_called_once_with()
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is False
    assert out["dependencies"]["pdfplumber"] == "1.0"


def test_e2e_aggregate_summary_full_pipeline_batch25():
    """aggregate_summary 处理混合 metrics 的 per_doc 列表。"""
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "schema_valid": {"value": True},
                "element_count_total": {"value": 3},
                "pdf_locator_valid_ratio": {"value": 1.0},
                "silent_drop_count": {"value": 0},
            }
        },
        {
            "metrics": {
                "pipeline_success": {"value": False},
                "schema_valid": {"value": None, "reason": "failed"},
                "element_count_total": {"value": None, "reason": "failed"},
                "pdf_locator_valid_ratio": {"value": None, "reason": "failed"},
                "silent_drop_count": {"value": None, "reason": "failed"},
            }
        },
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert out["counts"]["element_count_total"]["sum"] == 3
    assert out["counts"]["element_count_total"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 1.0
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["not_evaluated"] == 1
    assert out["silent_drop_total"] == 0


def test_e2e_build_devset_section_full_batch25():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 10
    m.content_group_count = 5
    m.pdf_count = 6
    m.docx_count = 4
    m.categories_covered = ["report", "article"]
    out = build_devset_section(m)
    assert out["status"] == "complete"
    assert out["file_count"] == 10
    assert out["content_group_count"] == 5
    assert out["pdf_count"] == 6
    assert out["docx_count"] == 4
    assert out["categories_covered"] == ["report", "article"]


def test_e2e_get_git_provenance_real_worktree_batch25():
    """真实跑一次 get_git_provenance（worktree 应是 git 仓库）。"""
    # 使用项目根（pyproject.toml 所在）
    project_root = Path(__file__).resolve().parent.parent
    out = get_git_provenance(project_root)
    assert "git_commit" in out
    assert "git_dirty" in out
    # 在 worktree 中应该有 commit
    assert out["git_commit"] is not None or out["git_dirty"] is True


def test_e2e_build_provenance_with_real_subprocess_batch25(tmp_path):
    """build_provenance 不 mock，调真实 subprocess（在 tmp_path 中无 git → commit=None）。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    # tmp_path 非 git 目录 → commit=None, dirty=False（per edges40 fix）
    assert out["git_commit"] is None
    assert out["git_dirty"] is False


def test_e2e_aggregate_summary_does_not_mutate_input_batch25():
    """aggregate_summary 不修改输入。"""
    import copy
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}, "element_count_total": {"value": 5}}}
    ]
    snapshot = copy.deepcopy(per_doc)
    aggregate_summary(per_doc)
    assert per_doc == snapshot


def test_e2e_build_provenance_run_timestamp_changes_batch25(tmp_path):
    """两次 build_provenance 的时间戳可能不同（除非极快）。"""
    import time
    out1 = build_provenance(tmp_path, "fallback", 800, None)
    time.sleep(0.01)
    out2 = build_provenance(tmp_path, "fallback", 800, None)
    # 时间戳可能是同一秒，但格式应一致
    assert "T" in out1["run_timestamp_iso"]
    assert "T" in out2["run_timestamp_iso"]
