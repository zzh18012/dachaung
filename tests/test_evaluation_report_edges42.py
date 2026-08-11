"""evaluation/report.py 第四十二轮 edges 测试（Round 499）。

补强 edges41 未触及的角度（第二十六批）：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第二十六批：sorted 性质 / 全 str 类型 / 与 silent_drop_count 等区分
- get_git_provenance 第二十六批：cwd 接受 Path / returncode 非 0 / stdout 仅空白 → commit None / r2 stdout 有内容 → dirty True / r2 stdout 空白 → dirty False
- get_dependency_versions 第二十六批：返回的 dict 不含其它键 / 包顺序固定 / 每个值为 str 或 None
- build_provenance 第二十六批：max_chars 字符串强制 int / max_chars=0 / parser_version=None 透传 / 9 keys 严格 / evaluator_version == EVALUATOR_VERSION / report_version == REPORT_VERSION / git 字段透传
- build_devset_section 第二十六批：frozen manifest / 6 keys 严格 / 属性透传
- aggregate_summary 第二十六批：empty per_doc / 全 None / 0 显式值 / pipeline_success 混合 / schema_valid 混合 / silent_drop 混合 null 与 int
- module source forbidden tokens 第四十二批
- module source 字符串精确补强第三十八批
- signatures 第三十八批
- module 合理性第三十八批
- 端到端集成第三十八批
"""

from __future__ import annotations

import inspect
from datetime import datetime
from pathlib import Path
from typing import Any, get_type_hints
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第二十六批 ----------


def test_ratio_metrics_all_str_type_batch26():
    """_RATIO_METRICS 每项都是 str。"""
    for entry in _RATIO_METRICS:
        assert isinstance(entry, str)


def test_ratio_metrics_count_twelve_batch26():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_count_one_each_batch26():
    assert len(_COUNT_METRICS) == 1
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_ratio_metrics_count_metric_value_batch26():
    assert _COUNT_METRICS[0] == "element_count_total"


def test_ratio_metrics_success_bool_value_batch26():
    assert _SUCCESS_BOOL_METRICS[0] == "pipeline_success"


def test_ratio_metrics_no_overlap_with_count_batch26():
    for r in _RATIO_METRICS:
        assert r not in _COUNT_METRICS


def test_ratio_metrics_no_overlap_with_success_batch26():
    for r in _RATIO_METRICS:
        assert r not in _SUCCESS_BOOL_METRICS


def test_ratio_metrics_count_no_overlap_success_batch26():
    for c in _COUNT_METRICS:
        assert c not in _SUCCESS_BOOL_METRICS


def test_ratio_metrics_not_sorted_required_batch26():
    """不要求 sorted，但每个 entry 必须 hashable 且 unique。"""
    assert len(set(_RATIO_METRICS)) == len(_RATIO_METRICS)


def test_count_metrics_hashable_batch26():
    assert hash(_COUNT_METRICS) == hash(_COUNT_METRICS)


def test_success_bool_metrics_hashable_batch26():
    assert hash(_SUCCESS_BOOL_METRICS) == hash(_SUCCESS_BOOL_METRICS)


# ---------- get_git_provenance 第二十六批 ----------


def test_get_git_provenance_accepts_path_obj_batch26(tmp_path):
    """Path 对象作为 cwd 传入。"""
    (tmp_path / ".git").mkdir()  # 让 git 识别为 repo（仍可能失败，但不应崩溃）
    out = get_git_provenance(tmp_path)
    assert isinstance(out, dict)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_returncode_nonzero_batch26(tmp_path):
    """rev-parse returncode 非 0 → commit=None。"""
    def fake_run(cmd, **kwargs):
        r = MagicMock()
        r.returncode = 128
        r.stdout = ""
        r.stderr = "fatal: not a git repository"
        return r
    with patch("subprocess.run", side_effect=fake_run):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_stdout_whitespace_only_batch26(tmp_path):
    """rev-parse stdout 仅空白 → commit=None。"""
    calls = []
    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        r = MagicMock()
        r.returncode = 0
        if "rev-parse" in cmd:
            r.stdout = "   \n\t "
        else:
            r.stdout = ""
        return r
    with patch("subprocess.run", side_effect=fake_run):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_porcelain_nonempty_dirty_true_batch26(tmp_path):
    """porcelain stdout 非空 → dirty=True。"""
    def fake_run(cmd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "rev-parse" in cmd:
            r.stdout = "abc123\n"
        else:
            r.stdout = " M file.txt\n"
        return r
    with patch("subprocess.run", side_effect=fake_run):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True
    assert out["git_commit"] == "abc123"


def test_get_git_provenance_porcelain_empty_dirty_false_batch26(tmp_path):
    """porcelain stdout 空 + returncode 0 → dirty=False。"""
    def fake_run(cmd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "rev-parse" in cmd:
            r.stdout = "abc123\n"
        else:
            r.stdout = ""
        return r
    with patch("subprocess.run", side_effect=fake_run):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_get_git_provenance_porcelain_returncode_nonzero_dirty_false_batch26(tmp_path):
    """porcelain returncode 非 0 → dirty=False（bool(False and ...) = False）。"""
    def fake_run(cmd, **kwargs):
        r = MagicMock()
        if "rev-parse" in cmd:
            r.returncode = 0
            r.stdout = "abc123\n"
        else:
            r.returncode = 1
            r.stdout = " M file.txt\n"
        return r
    with patch("subprocess.run", side_effect=fake_run):
        out = get_git_provenance(tmp_path)
    # bool(returncode==0 and stdout.strip()) = bool(False and True) = False
    assert out["git_dirty"] is False


def test_get_git_provenance_oserror_fallback_batch26(tmp_path):
    """OSError 触发 fallback：commit=None, dirty=True。"""
    with patch("subprocess.run", side_effect=OSError("boom")):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_timeout_fallback_batch26(tmp_path):
    """SubprocessError（含 timeout）触发 fallback。"""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10)):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_returns_two_keys_batch26(tmp_path):
    out = get_git_provenance(tmp_path)
    assert len(out) == 2


# 需要 subprocess 导入以便 timeout 测试可用
import subprocess  # noqa: E402


# ---------- get_dependency_versions 第二十六批 ----------


def test_get_dependency_versions_keys_exactly_three_batch26():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_value_types_batch26():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_order_preserved_batch26():
    """dict 保持插入顺序：pdfplumber → python-docx → pypdfium2。"""
    out = get_dependency_versions()
    keys = list(out.keys())
    assert keys == ["pdfplumber", "python-docx", "pypdfium2"]


def test_get_dependency_versions_calls_importlib_batch26():
    """通过 importlib.metadata.version 读取。"""
    with patch("importlib.metadata.version", return_value="1.0.0") as m:
        out = get_dependency_versions()
    m.assert_called()
    assert all(v == "1.0.0" for v in out.values())


def test_get_dependency_versions_package_not_found_batch26():
    """PackageNotFoundError → None。"""
    import importlib.metadata
    with patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError):
        out = get_dependency_versions()
    assert all(v is None for v in out.values())


def test_get_dependency_versions_unexpected_exception_batch26():
    """其它异常也 → None，不崩溃。"""
    with patch("importlib.metadata.version", side_effect=RuntimeError("unexpected")):
        out = get_dependency_versions()
    assert all(v is None for v in out.values())


# ---------- build_provenance 第二十六批 ----------


def test_build_provenance_max_chars_str_coerced_batch26(tmp_path):
    """max_chars 字符串 '800' → int 800。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
        out = build_provenance(tmp_path, "fallback", "800", None)
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_zero_batch26(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 0, None)
    assert out["max_chars"] == 0


def test_build_provenance_max_chars_negative_batch26(tmp_path):
    """负数仍强制 int，不报错（业务上无意义但函数应接受）。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", -1, None)
    assert out["max_chars"] == -1


def test_build_provenance_parser_version_none_batch26(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_parser_version_empty_str_batch26(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, "")
    assert out["parser_version"] == ""


def test_build_provenance_parser_version_str_batch26(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert out["parser_version"] == "0.1.0"


def test_build_provenance_nine_keys_batch26(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, None)
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
    assert len(out) == 9


def test_build_provenance_evaluator_version_matches_batch26(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_matches_batch26(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_propagates_batch26(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "kreuzberg", 800, "4.10.2")
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_git_commit_propagates_batch26(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "deadbeef", "git_dirty": False}):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["git_commit"] == "deadbeef"
    assert out["git_dirty"] is False


def test_build_provenance_run_timestamp_iso_parseable_batch26(tmp_path):
    """run_timestamp_iso 应可被 datetime.fromisoformat 解析。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, None)
    dt = datetime.fromisoformat(out["run_timestamp_iso"])
    assert dt is not None


def test_build_provenance_dependencies_dict_batch26(tmp_path):
    """dependencies 字段是 dict（来自 get_dependency_versions）。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["dependencies"], dict)
    assert "pdfplumber" in out["dependencies"]


def test_build_provenance_calls_get_git_provenance_once_batch26(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}) as m:
        build_provenance(tmp_path, "fallback", 800, None)
    m.assert_called_once_with(tmp_path)


# ---------- build_devset_section 第二十六批 ----------


def _make_manifest(**kwargs):
    """构造一个 Manifest-like 对象（duck typing）。"""
    m = MagicMock()
    m.devset_status = kwargs.get("devset_status", "incomplete")
    m.file_count = kwargs.get("file_count", 0)
    m.content_group_count = kwargs.get("content_group_count", 0)
    m.pdf_count = kwargs.get("pdf_count", 0)
    m.docx_count = kwargs.get("docx_count", 0)
    m.categories_covered = kwargs.get("categories_covered", [])
    return m


def test_build_devset_section_six_keys_batch26():
    out = build_devset_section(_make_manifest())
    expected = {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }
    assert set(out.keys()) == expected
    assert len(out) == 6


def test_build_devset_section_status_complete_batch26():
    m = _make_manifest(devset_status="complete")
    out = build_devset_section(m)
    assert out["status"] == "complete"


def test_build_devset_section_status_incomplete_batch26():
    m = _make_manifest(devset_status="incomplete")
    out = build_devset_section(m)
    assert out["status"] == "incomplete"


def test_build_devset_section_empty_categories_batch26():
    m = _make_manifest(categories_covered=[])
    out = build_devset_section(m)
    assert out["categories_covered"] == []


def test_build_devset_section_propagates_all_attrs_batch26():
    m = _make_manifest(
        devset_status="incomplete",
        file_count=5,
        content_group_count=2,
        pdf_count=3,
        docx_count=2,
        categories_covered=["a", "b"],
    )
    out = build_devset_section(m)
    assert out["file_count"] == 5
    assert out["content_group_count"] == 2
    assert out["pdf_count"] == 3
    assert out["docx_count"] == 2
    assert out["categories_covered"] == ["a", "b"]


def test_build_devset_section_does_not_mutate_manifest_batch26():
    m = _make_manifest(categories_covered=["x"])
    build_devset_section(m)
    # MagicMock 不真存数据，但函数不应改属性
    assert m.devset_status == "incomplete"
    assert m.categories_covered == ["x"]


# ---------- aggregate_summary 第二十六批 ----------


def test_aggregate_summary_empty_per_doc_batch26():
    out = aggregate_summary([])
    assert out["silent_drop_total"] is None
    # counts: element_count_total → sum=None, participating=0
    assert out["counts"]["element_count_total"] == {"sum": None, "participating_docs": 0}
    # success_rates: pipeline_success → rate=None
    assert out["success_rates"]["pipeline_success"]["rate"] is None
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0
    assert out["success_rates"]["pipeline_success"]["total"] == 0


def test_aggregate_summary_count_explicit_zero_batch26():
    """element_count_total value=0 显式 → counts sum=0, participating=1。"""
    per_doc = [{"metrics": {"element_count_total": {"value": 0}}}]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"] == {"sum": 0, "participating_docs": 1}


def test_aggregate_summary_count_value_none_batch26():
    """element_count_total value=None → counts sum=None, participating=0。"""
    per_doc = [{"metrics": {"element_count_total": {"value": None}}}]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"] == {"sum": None, "participating_docs": 0}


def test_aggregate_summary_count_sum_two_docs_batch26():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": 7}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 12
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_pipeline_success_all_true_batch26():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 2
    assert sr["rate"] == 1.0


def test_aggregate_summary_pipeline_success_all_false_batch26():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["rate"] == 0.0


def test_aggregate_summary_pipeline_success_mixed_batch26():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 3
    assert sr["rate"] == pytest.approx(1 / 3)


def test_aggregate_summary_schema_valid_mixed_batch26():
    """schema_valid 是 ratio_metric，按 macro average 走。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": True}}},
        {"metrics": {"schema_valid": {"value": False}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    avg = out["ratio_macro_averages"]["schema_valid"]
    # True=1, False=0, None=跳过 → 2 个参与 → (1+0)/2 = 0.5
    assert avg["macro_average"] == 0.5
    assert avg["participating_docs"] == 2
    assert avg["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_mixed_batch26():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_all_none_batch26():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_zero_explicit_batch26():
    per_doc = [{"metrics": {"silent_drop_count": {"value": 0}}}]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 0


def test_aggregate_summary_ratio_all_none_batch26():
    per_doc = [
        {"metrics": {"pdf_locator_valid_ratio": {"value": None}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    avg = out["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert avg["macro_average"] is None
    assert avg["participating_docs"] == 0
    assert avg["not_evaluated"] == 2


def test_aggregate_summary_keys_count_batch26():
    """summary 顶层 4 keys: counts / success_rates / ratio_macro_averages / silent_drop_total。"""
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_counts_keys_batch26():
    out = aggregate_summary([])
    assert set(out["counts"].keys()) == {"element_count_total"}


def test_aggregate_summary_success_rates_keys_batch26():
    out = aggregate_summary([])
    assert set(out["success_rates"].keys()) == {"pipeline_success"}


def test_aggregate_summary_ratio_macro_averages_keys_count_batch26():
    out = aggregate_summary([])
    # 12 ratio metrics
    assert len(out["ratio_macro_averages"]) == 12


def test_aggregate_summary_ratio_macro_averages_keys_match_batch26():
    out = aggregate_summary([])
    assert set(out["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


def test_aggregate_summary_does_not_mutate_input_batch26():
    per_doc = [{"metrics": {"element_count_total": {"value": 5}}}]
    snapshot = {"metrics": {"element_count_total": {"value": 5}}}
    aggregate_summary(per_doc)
    assert per_doc == [snapshot]


def test_aggregate_summary_missing_metrics_key_raises_batch26():
    """per_doc 缺 metrics key → KeyError（实现直接 r['metrics'] 访问）。"""
    per_doc = [{}]
    with pytest.raises(KeyError):
        aggregate_summary(per_doc)


# ---------- module source forbidden tokens 第四十二批 ----------


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
    "import json",
    "import csv",
    "import random",
    "import hashlib",
]


def test_module_source_forbidden_tokens_batch26():
    source = inspect.getsource(rmod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_uses_from_datetime_import_batch26():
    """report.py 允许 from datetime import datetime（用于时间戳）。"""
    source = inspect.getsource(rmod)
    assert "from datetime import datetime" in source


def test_module_source_no_class_keyword_batch26():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_source_subprocess_allowed_batch26():
    """report.py 允许 import subprocess（git provenance 用）。"""
    source = inspect.getsource(rmod)
    assert "import subprocess" in source


def test_module_source_no_eval_exec_batch26():
    source = inspect.getsource(rmod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_module_source_no_relative_imports_batch26():
    source = inspect.getsource(rmod)
    assert "from ." not in source


def test_module_source_no_star_import_batch26():
    source = inspect.getsource(rmod)
    assert "import *" not in source


def test_module_source_no_environ_batch26():
    source = inspect.getsource(rmod)
    assert "os.environ" not in source
    assert "getenv" not in source


def test_module_source_no_open_at_module_level_batch26():
    """不应在 module level 调用 open()。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    for node in tree.body:
        if isinstance(node, _ast.Expr):
            assert not (isinstance(node.value, _ast.Call) and getattr(node.value.func, "id", None) == "open")


def test_module_source_no_dataclass_batch26():
    source = inspect.getsource(rmod)
    assert "@dataclass" not in source
    assert "from dataclasses" not in source


def test_module_source_no_argparse_batch26():
    source = inspect.getsource(rmod)
    assert "argparse" not in source


def test_module_source_typing_import_any_only_batch26():
    """report.py 仅 from typing import Any。"""
    source = inspect.getsource(rmod)
    assert "from typing import Any" in source


def test_module_source_no_attr_redefinition_batch26():
    """检查关键常量在 module 中只定义一次。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    names = [
        n.targets[0].id
        for n in tree.body
        if isinstance(n, _ast.Assign)
        and isinstance(n.targets[0], _ast.Name)
        and n.targets[0].id.startswith("_")
        and n.targets[0].id.endswith("_METRICS")
    ]
    assert len(names) == len(set(names))


# ---------- module source 字符串精确补强第三十八批 ----------


def test_module_source_contains_from_evaluation_import_batch26():
    source = inspect.getsource(rmod)
    assert "from evaluation import" in source


def test_module_source_contains_evaluator_version_constant_batch26():
    source = inspect.getsource(rmod)
    assert "EVALUATOR_VERSION" in source


def test_module_source_contains_report_version_constant_batch26():
    source = inspect.getsource(rmod)
    assert "REPORT_VERSION" in source


def test_module_source_contains_capture_output_batch26():
    source = inspect.getsource(rmod)
    assert "capture_output=True" in source


def test_module_source_contains_text_true_batch26():
    source = inspect.getsource(rmod)
    assert "text=True" in source


def test_module_source_contains_errors_replace_batch26():
    source = inspect.getsource(rmod)
    assert 'errors="replace"' in source


def test_module_source_contains_encoding_utf8_batch26():
    source = inspect.getsource(rmod)
    assert 'encoding="utf-8"' in source


def test_module_source_contains_timeout_10_batch26():
    source = inspect.getsource(rmod)
    assert "timeout=10" in source


def test_module_source_contains_rev_parse_head_batch26():
    source = inspect.getsource(rmod)
    assert '"rev-parse"' in source or "'rev-parse'" in source


def test_module_source_contains_status_porcelain_batch26():
    source = inspect.getsource(rmod)
    assert "status" in source and "porcelain" in source


def test_module_source_contains_importlib_metadata_batch26():
    source = inspect.getsource(rmod)
    assert "importlib.metadata" in source


def test_module_source_contains_pdfplumber_dependency_batch26():
    source = inspect.getsource(rmod)
    assert "pdfplumber" in source


def test_module_source_contains_python_docx_dependency_batch26():
    source = inspect.getsource(rmod)
    assert "python-docx" in source


def test_module_source_contains_pypdfium2_dependency_batch26():
    source = inspect.getsource(rmod)
    assert "pypdfium2" in source


def test_module_source_contains_aggregate_summary_batch26():
    source = inspect.getsource(rmod)
    assert "def aggregate_summary" in source


def test_module_source_contains_macro_average_batch26():
    source = inspect.getsource(rmod)
    assert "macro_average" in source


def test_module_source_contains_silent_drop_total_batch26():
    source = inspect.getsource(rmod)
    assert "silent_drop_total" in source


def test_module_source_contains_participating_docs_batch26():
    source = inspect.getsource(rmod)
    assert "participating_docs" in source


def test_module_source_contains_not_evaluated_batch26():
    source = inspect.getsource(rmod)
    assert "not_evaluated" in source


# ---------- signatures 第三十八批 ----------


def test_signature_get_git_provenance_batch26():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root"]


def test_signature_get_git_provenance_annotation_batch26():
    sig = inspect.signature(get_git_provenance)
    p = sig.parameters["project_root"]
    assert p.annotation == "Path"


def test_signature_get_dependency_versions_no_args_batch26():
    sig = inspect.signature(get_dependency_versions)
    assert list(sig.parameters.keys()) == []


def test_signature_build_provenance_batch26():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_provenance_annotations_batch26():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["parser_name"].annotation == "str"
    assert sig.parameters["max_chars"].annotation == "int"
    assert sig.parameters["parser_version"].annotation == "str | None"


def test_signature_build_devset_section_batch26():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.keys())
    assert params == ["manifest"]


def test_signature_aggregate_summary_batch26():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.keys())
    assert params == ["per_doc_results"]


def test_signature_aggregate_summary_annotation_batch26():
    sig = inspect.signature(aggregate_summary)
    assert sig.parameters["per_doc_results"].annotation == "list[dict[str, Any]]"


def test_signature_all_annotations_are_strings_batch26():
    """from __future__ import annotations → 所有 annotation 应是 str。"""
    for fn in [get_git_provenance, get_dependency_versions, build_provenance, build_devset_section, aggregate_summary]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            if p.annotation is not inspect.Parameter.empty:
                assert isinstance(p.annotation, str), f"{fn.__name__}.{p.name} annotation not str"


# ---------- module 合理性第三十八批 ----------


def test_module_all_five_entries_batch26():
    assert set(rmod.__all__) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_has_five_functions_batch26():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    funcs = [n.name for n in tree.body if isinstance(n, _ast.FunctionDef)]
    assert set(funcs) == {
        "get_git_provenance",
        "get_dependency_versions",
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
    }


def test_module_no_classes_batch26():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_docstring_present_batch26():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__.strip()) > 0


def test_module_docstring_mentions_aggregate_batch26():
    assert "aggregate" in rmod.__doc__.lower() or "聚合" in rmod.__doc__


def test_module_docstring_mentions_no_mix_batch26():
    assert "不混合" in rmod.__doc__ or "no mix" in rmod.__doc__.lower() or "macro" in rmod.__doc__.lower()


def test_module_docstring_mentions_silent_drop_batch26():
    assert "silent_drop" in rmod.__doc__ or "silent drop" in rmod.__doc__.lower()


def test_module_uses_from_future_annotations_batch26():
    source = inspect.getsource(rmod)
    assert "from __future__ import annotations" in source


def test_module_module_level_constants_batch26():
    """module-level 有 3 个常量：_RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    constants = [
        n.targets[0].id
        for n in tree.body
        if isinstance(n, _ast.Assign)
        and isinstance(n.targets[0], _ast.Name)
        and n.targets[0].id.startswith("_")
    ]
    assert "_RATIO_METRICS" in constants
    assert "_COUNT_METRICS" in constants
    assert "_SUCCESS_BOOL_METRICS" in constants


def test_module_all_entries_accessible_batch26():
    for name in rmod.__all__:
        assert hasattr(rmod, name)


# ---------- 端到端集成第三十八批 ----------


def test_e2e_build_provenance_full_batch26(tmp_path):
    """真实调用 build_provenance，验证返回 dict 结构正确。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out, dict)
    assert "git_commit" in out
    assert "git_dirty" in out
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION
    assert out["parser_name"] == "fallback"
    assert out["max_chars"] == 800
    assert isinstance(out["dependencies"], dict)


def test_e2e_aggregate_summary_full_pipeline_batch26():
    """3 个 doc 的真实聚合。"""
    per_doc = [
        {
            "metrics": {
                "element_count_total": {"value": 10},
                "pipeline_success": {"value": True},
                "schema_valid": {"value": True},
                "pdf_locator_valid_ratio": {"value": 1.0},
                "silent_drop_count": {"value": 0},
            }
        },
        {
            "metrics": {
                "element_count_total": {"value": 5},
                "pipeline_success": {"value": False},
                "schema_valid": {"value": False},
                "pdf_locator_valid_ratio": {"value": 0.5},
                "silent_drop_count": {"value": 2},
            }
        },
        {
            "metrics": {
                "element_count_total": {"value": None},
                "pipeline_success": {"value": True},
                "schema_valid": {"value": None},
                "pdf_locator_valid_ratio": {"value": None},
                "silent_drop_count": {"value": None},
            }
        },
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["counts"]["element_count_total"]["participating_docs"] == 2
    assert out["success_rates"]["pipeline_success"]["success_count"] == 2
    assert out["success_rates"]["pipeline_success"]["total"] == 3
    assert out["success_rates"]["pipeline_success"]["rate"] == pytest.approx(2 / 3)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == pytest.approx(0.75)
    assert out["silent_drop_total"] == 2


def test_e2e_build_devset_section_full_batch26():
    m = _make_manifest(
        devset_status="incomplete",
        file_count=10,
        content_group_count=3,
        pdf_count=4,
        docx_count=6,
        categories_covered=["reports", "memos", "specs"],
    )
    out = build_devset_section(m)
    assert out == {
        "status": "incomplete",
        "file_count": 10,
        "content_group_count": 3,
        "pdf_count": 4,
        "docx_count": 6,
        "categories_covered": ["reports", "memos", "specs"],
    }


def test_e2e_get_git_provenance_real_worktree_batch26():
    """真实在 worktree 调用 → 至少返回 2 个 key。"""
    out = get_git_provenance(Path("."))
    assert "git_commit" in out
    assert "git_dirty" in out
    # 在 git repo 内，commit 应非 None
    assert out["git_commit"] is not None or out["git_dirty"] is True


def test_e2e_build_provenance_with_real_subprocess_batch26(tmp_path):
    """build_provenance 走真实 subprocess（tmp_path 非 git 目录 → commit=None, dirty=False）。"""
    out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert out["parser_version"] == "0.1.0"
    # tmp_path 非 git repo：rev-parse 失败 commit=None；porcelain 失败 dirty=False
    # （实现：dirty=bool(r2.returncode==0 and stdout.strip())，r2 失败 → False）
    assert out["git_commit"] is None
    assert out["git_dirty"] is False


def test_e2e_aggregate_summary_does_not_mutate_input_batch26():
    per_doc = [{"metrics": {"element_count_total": {"value": 5}}}]
    import copy
    snapshot = copy.deepcopy(per_doc)
    aggregate_summary(per_doc)
    assert per_doc == snapshot


def test_e2e_build_provenance_run_timestamp_changes_batch26(tmp_path):
    """两次 build_provenance 调用，时间戳可能不同（至少不报错）。"""
    out1 = build_provenance(tmp_path, "fallback", 800, None)
    out2 = build_provenance(tmp_path, "fallback", 800, None)
    # 两次都应能解析为 ISO 时间
    datetime.fromisoformat(out1["run_timestamp_iso"])
    datetime.fromisoformat(out2["run_timestamp_iso"])


def test_e2e_aggregate_summary_figure_caption_always_null_safe_batch26():
    """figure_caption_* 不在 _RATIO_METRICS → ratio_macro_averages 不应包含。"""
    per_doc = [{"metrics": {"figure_caption_precision": {"value": None, "reason": "parser_does_not_emit_relations"}}}]
    out = aggregate_summary(per_doc)
    assert "figure_caption_precision" not in out["ratio_macro_averages"]
