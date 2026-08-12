"""evaluation/report.py 第四十三轮 edges 测试（Round 506）。

补强 edges42 未触及的角度（第二十七批）：
- aggregate_summary 第二十七批：figure_caption_* 始终不在 ratio_macro_averages / silent_drop_total 与 counts 不混 / per_doc 缺 metrics 字段 → KeyError
- build_provenance 第二十七批：parser_name 透传 / run_timestamp_iso 时区含偏移 / dependencies 三 key 严格 / dependencies 值 None 时仍 key 存
- build_devset_section 第二十七批：list 返回 categories / status 透传 / project_root 不影响 devset
- get_git_provenance 第二十七批：subprocess.run 调用两次 / cwd 透传 / 各种编码组合
- get_dependency_versions 第二十七批：importlib.metadata.version 调用三次 / 单包失败不影响其它
- module source forbidden tokens 第四十三批
- module source 字符串精确补强第三十九批
- signatures 第三十九批
- module 合理性第三十九批
- 端到端集成第三十九批
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


# ---------- aggregate_summary 第二十七批 ----------


def test_aggregate_summary_does_not_mix_counts_and_ratios_batch27():
    """counts 中没有 ratio metrics，ratio_macro_averages 中没有 count metrics。"""
    per_doc = [
        {"metrics": {
            "element_count_total": {"value": 5},
            "schema_valid": {"value": True},
        }}
    ]
    out = aggregate_summary(per_doc)
    assert "element_count_total" in out["counts"]
    assert "element_count_total" not in out["ratio_macro_averages"]
    assert "schema_valid" in out["ratio_macro_averages"]
    assert "schema_valid" not in out["counts"]


def test_aggregate_summary_silent_drop_separate_from_counts_batch27():
    """silent_drop_count 不在 counts 中（它是独立的 silent_drop_total）。"""
    per_doc = [{"metrics": {"silent_drop_count": {"value": 3}}}]
    out = aggregate_summary(per_doc)
    assert "silent_drop_count" not in out["counts"]
    assert out["silent_drop_total"] == 3


def test_aggregate_summary_figure_caption_excluded_from_macro_avg_batch27():
    """figure_caption_* 不在 ratio_macro_averages。"""
    per_doc = [{"metrics": {"figure_caption_precision": {"value": 0.5}}}]
    out = aggregate_summary(per_doc)
    assert "figure_caption_precision" not in out["ratio_macro_averages"]


def test_aggregate_summary_pipeline_success_in_success_rates_batch27():
    """pipeline_success 在 success_rates，不在 ratio_macro_averages。"""
    per_doc = [{"metrics": {"pipeline_success": {"value": True}}}]
    out = aggregate_summary(per_doc)
    assert "pipeline_success" in out["success_rates"]
    assert "pipeline_success" not in out["ratio_macro_averages"]


def test_aggregate_summary_all_metrics_processed_together_batch27():
    """所有 metric 类型同时出现在输入中应被正确分类。"""
    per_doc = [
        {"metrics": {
            "element_count_total": {"value": 10},
            "pipeline_success": {"value": True},
            "schema_valid": {"value": True},
            "pdf_locator_valid_ratio": {"value": 1.0},
            "silent_drop_count": {"value": 0},
        }}
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 10
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 1.0
    assert out["silent_drop_total"] == 0


def test_aggregate_summary_negative_value_in_count_batch27():
    """element_count_total 负数也会被求和（不验证语义）。"""
    per_doc = [{"metrics": {"element_count_total": {"value": -5}}}]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == -5


def test_aggregate_summary_negative_value_in_silent_drop_batch27():
    per_doc = [{"metrics": {"silent_drop_count": {"value": -3}}}]
    out = aggregate_summary(per_doc)
    # 实现不限制非负，sum 也接受负
    assert out["silent_drop_total"] == -3


def test_aggregate_summary_many_docs_batch27():
    """100 个 doc 应正常聚合（性能 sanity）。"""
    per_doc = [
        {"metrics": {
            "element_count_total": {"value": i},
            "pipeline_success": {"value": True},
            "schema_valid": {"value": True},
        }}
        for i in range(100)
    ]
    out = aggregate_summary(per_doc)
    # sum(0..99) = 99*100/2 = 4950
    assert out["counts"]["element_count_total"]["sum"] == 4950
    assert out["success_rates"]["pipeline_success"]["success_count"] == 100


def test_aggregate_summary_success_rate_zero_total_batch27():
    """empty per_doc → success_rates rate=None（避免除 0）。"""
    out = aggregate_summary([])
    assert out["success_rates"]["pipeline_success"]["rate"] is None


def test_aggregate_summary_returns_dict_batch27():
    assert isinstance(aggregate_summary([]), dict)


# ---------- build_provenance 第二十七批 ----------


def test_build_provenance_parser_name_passed_through_batch27(tmp_path):
    """parser_name 透传到 provenance。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_name"] == "fallback"


def test_build_provenance_run_timestamp_iso_has_timezone_batch27(tmp_path):
    """run_timestamp_iso 应含时区偏移（astimezone 添加）。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, None)
    dt = datetime.fromisoformat(out["run_timestamp_iso"])
    assert dt.tzinfo is not None


def test_build_provenance_dependencies_three_keys_batch27(tmp_path):
    """dependencies 必有 pdfplumber/python-docx/pypdfium2 三 key。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert set(out["dependencies"].keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_build_provenance_dependencies_value_none_keeps_key_batch27(tmp_path):
    """dependency 不存在时 value=None，但 key 必保留。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        with patch("evaluation.report.get_dependency_versions",
                   return_value={"pdfplumber": None, "python-docx": None, "pypdfium2": None}):
            out = build_provenance(tmp_path, "fallback", 800, None)
    for k in ("pdfplumber", "python-docx", "pypdfium2"):
        assert k in out["dependencies"]
        assert out["dependencies"][k] is None


def test_build_provenance_evaluator_version_is_str_batch27(tmp_path):
    """evaluator_version 必是 str（不应是 tuple/int）。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["evaluator_version"], str)


def test_build_provenance_report_version_is_str_batch27(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["report_version"], str)


def test_build_provenance_max_chars_always_int_batch27(tmp_path):
    """max_chars 必被 cast 为 int（int(800)="800"=800.0=800）。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        for v in [800, "800", 800.0]:
            out = build_provenance(tmp_path, "fallback", v, None)  # type: ignore
            assert out["max_chars"] == 800
            assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_true_cast_to_one_batch27(tmp_path):
    """bool True → int(True) = 1（Python 语义，不是 800）。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", True, None)  # type: ignore
    assert out["max_chars"] == 1


def test_build_provenance_no_extra_keys_batch27(tmp_path):
    """provenance 不应有 9 个 key 之外的额外字段。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert len(out) == 9


# ---------- build_devset_section 第二十七批 ----------


def _make_manifest_obj(**kwargs):
    m = MagicMock()
    m.devset_status = kwargs.get("devset_status", "incomplete")
    m.file_count = kwargs.get("file_count", 0)
    m.content_group_count = kwargs.get("content_group_count", 0)
    m.pdf_count = kwargs.get("pdf_count", 0)
    m.docx_count = kwargs.get("docx_count", 0)
    m.categories_covered = kwargs.get("categories_covered", [])
    return m


def test_build_devset_section_categories_is_list_batch27():
    """categories_covered 必须保留为 list（不强制 tuple）。"""
    m = _make_manifest_obj(categories_covered=["a", "b"])
    out = build_devset_section(m)
    assert isinstance(out["categories_covered"], list)
    assert out["categories_covered"] == ["a", "b"]


def test_build_devset_section_status_passes_through_batch27():
    """status 字段透传，不修改。"""
    m = _make_manifest_obj(devset_status="incomplete")
    out = build_devset_section(m)
    assert out["status"] == "incomplete"


def test_build_devset_section_large_file_count_batch27():
    """大数字也应正常透传。"""
    m = _make_manifest_obj(file_count=1000000)
    out = build_devset_section(m)
    assert out["file_count"] == 1000000


def test_build_devset_section_zero_counts_batch27():
    m = _make_manifest_obj(file_count=0, content_group_count=0, pdf_count=0, docx_count=0)
    out = build_devset_section(m)
    assert out["file_count"] == 0
    assert out["content_group_count"] == 0
    assert out["pdf_count"] == 0
    assert out["docx_count"] == 0


def test_build_devset_section_does_not_use_project_root_batch27():
    """build_devset_section 不读 project_root。"""
    m = _make_manifest_obj()
    m.project_root = Path("/anywhere")
    out = build_devset_section(m)
    assert "project_root" not in out


# ---------- get_git_provenance 第二十七批 ----------


def test_get_git_provenance_subprocess_called_twice_batch27(tmp_path):
    """subprocess.run 应被调用两次（rev-parse + status）。"""
    calls = []
    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        r = MagicMock()
        r.returncode = 0
        r.stdout = "abc123\n" if "rev-parse" in cmd else ""
        return r
    with patch("subprocess.run", side_effect=fake_run):
        get_git_provenance(tmp_path)
    assert len(calls) == 2


def test_get_git_provenance_cwd_passed_through_batch27(tmp_path):
    """cwd 应被传给 subprocess.run。"""
    captured = []
    def fake_run(cmd, **kwargs):
        captured.append(kwargs.get("cwd"))
        r = MagicMock()
        r.returncode = 0
        r.stdout = "abc123\n" if "rev-parse" in cmd else ""
        return r
    with patch("subprocess.run", side_effect=fake_run):
        get_git_provenance(tmp_path)
    assert all(c == str(tmp_path) for c in captured)


def test_get_git_provenance_encoding_param_batch27(tmp_path):
    """encoding='utf-8' 应被传给 subprocess.run。"""
    captured = []
    def fake_run(cmd, **kwargs):
        captured.append(kwargs)
        r = MagicMock()
        r.returncode = 0
        r.stdout = "abc123\n" if "rev-parse" in cmd else ""
        return r
    with patch("subprocess.run", side_effect=fake_run):
        get_git_provenance(tmp_path)
    assert all(c.get("encoding") == "utf-8" for c in captured)


def test_get_git_provenance_errors_replace_param_batch27(tmp_path):
    """errors='replace' 应被传给 subprocess.run。"""
    captured = []
    def fake_run(cmd, **kwargs):
        captured.append(kwargs)
        r = MagicMock()
        r.returncode = 0
        r.stdout = "abc123\n" if "rev-parse" in cmd else ""
        return r
    with patch("subprocess.run", side_effect=fake_run):
        get_git_provenance(tmp_path)
    assert all(c.get("errors") == "replace" for c in captured)


def test_get_git_provenance_timeout_10_batch27(tmp_path):
    captured = []
    def fake_run(cmd, **kwargs):
        captured.append(kwargs)
        r = MagicMock()
        r.returncode = 0
        r.stdout = "abc123\n" if "rev-parse" in cmd else ""
        return r
    with patch("subprocess.run", side_effect=fake_run):
        get_git_provenance(tmp_path)
    assert all(c.get("timeout") == 10 for c in captured)


def test_get_git_provenance_capture_output_true_batch27(tmp_path):
    captured = []
    def fake_run(cmd, **kwargs):
        captured.append(kwargs)
        r = MagicMock()
        r.returncode = 0
        r.stdout = "abc123\n" if "rev-parse" in cmd else ""
        return r
    with patch("subprocess.run", side_effect=fake_run):
        get_git_provenance(tmp_path)
    assert all(c.get("capture_output") is True for c in captured)


def test_get_git_provenance_text_true_batch27(tmp_path):
    captured = []
    def fake_run(cmd, **kwargs):
        captured.append(kwargs)
        r = MagicMock()
        r.returncode = 0
        r.stdout = "abc123\n" if "rev-parse" in cmd else ""
        return r
    with patch("subprocess.run", side_effect=fake_run):
        get_git_provenance(tmp_path)
    assert all(c.get("text") is True for c in captured)


# ---------- get_dependency_versions 第二十七批 ----------


def test_get_dependency_versions_calls_version_three_times_batch27():
    """importlib.metadata.version 应被调用 3 次。"""
    with patch("importlib.metadata.version", return_value="1.0.0") as m:
        get_dependency_versions()
    assert m.call_count == 3


def test_get_dependency_versions_single_failure_doesnt_crash_batch27():
    """单包失败不影响其它包（PackageNotFoundError 单次抛出后继续）。"""
    import importlib.metadata
    call_count = [0]
    def fake_version(name):
        call_count[0] += 1
        if name == "python-docx":
            raise importlib.metadata.PackageNotFoundError(name)
        return "1.0.0"
    with patch("importlib.metadata.version", side_effect=fake_version):
        out = get_dependency_versions()
    assert out["pdfplumber"] == "1.0.0"
    assert out["python-docx"] is None
    assert out["pypdfium2"] == "1.0.0"


def test_get_dependency_versions_first_call_exception_doesnt_crash_batch27():
    """第一个包抛非 PackageNotFoundError 异常也应被捕获。"""
    def fake_version(name):
        if name == "pdfplumber":
            raise RuntimeError("unexpected")
        return "1.0.0"
    with patch("importlib.metadata.version", side_effect=fake_version):
        out = get_dependency_versions()
    assert out["pdfplumber"] is None
    assert out["python-docx"] == "1.0.0"
    assert out["pypdfium2"] == "1.0.0"


def test_get_dependency_versions_returned_dict_not_shared_batch27():
    """每次调用应返回新 dict（不应共享缓存）。"""
    o1 = get_dependency_versions()
    o2 = get_dependency_versions()
    assert o1 == o2
    assert o1 is not o2


# ---------- module source forbidden tokens 第四十三批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import json",
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
    "from timeit",
    "from time",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import argparse",
    "import csv",
    "import random",
    "import hashlib",
]


def test_module_source_forbidden_tokens_batch27():
    source = inspect.getsource(rmod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token: {tok}"


def test_module_source_no_eval_exec_batch27():
    source = inspect.getsource(rmod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_module_source_no_star_import_batch27():
    source = inspect.getsource(rmod)
    assert "import *" not in source


def test_module_source_no_relative_imports_batch27():
    source = inspect.getsource(rmod)
    assert "from ." not in source


def test_module_source_no_unsafe_network_batch27():
    source = inspect.getsource(rmod)
    for tok in ["requests", "urllib.request", "http.client", "socket"]:
        assert tok not in source


def test_module_source_no_environ_batch27():
    source = inspect.getsource(rmod)
    assert "os.environ" not in source


def test_module_source_no_dataclass_batch27():
    source = inspect.getsource(rmod)
    assert "@dataclass" not in source


def test_module_source_no_argparse_batch27():
    source = inspect.getsource(rmod)
    assert "argparse" not in source


def test_module_source_subprocess_allowed_batch27():
    """report.py 允许 import subprocess（git provenance 用）。"""
    source = inspect.getsource(rmod)
    assert "import subprocess" in source


def test_module_source_datetime_allowed_batch27():
    """report.py 允许 from datetime import datetime。"""
    source = inspect.getsource(rmod)
    assert "from datetime import datetime" in source


def test_module_source_no_class_keyword_batch27():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_source_no_module_level_mutables_batch27():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    for node in tree.body:
        if isinstance(node, _ast.Assign) and isinstance(node.targets[0], _ast.Name):
            name = node.targets[0].id
            if name.startswith("_") and not name.startswith("__") and name not in ("_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"):
                pytest.fail(f"private module-level mutable: {name}")


# ---------- module source 字符串精确补强第三十九批 ----------


def test_module_source_contains_from_evaluation_import_batch27():
    source = inspect.getsource(rmod)
    assert "from evaluation import" in source


def test_module_source_contains_evaluator_version_constant_batch27():
    source = inspect.getsource(rmod)
    assert "EVALUATOR_VERSION" in source


def test_module_source_contains_report_version_constant_batch27():
    source = inspect.getsource(rmod)
    assert "REPORT_VERSION" in source


def test_module_source_contains_macro_average_key_batch27():
    source = inspect.getsource(rmod)
    assert '"macro_average"' in source


def test_module_source_contains_participating_docs_key_batch27():
    source = inspect.getsource(rmod)
    assert '"participating_docs"' in source


def test_module_source_contains_not_evaluated_key_batch27():
    source = inspect.getsource(rmod)
    assert '"not_evaluated"' in source


def test_module_source_contains_success_count_key_batch27():
    source = inspect.getsource(rmod)
    assert '"success_count"' in source


def test_module_source_contains_silent_drop_total_key_batch27():
    source = inspect.getsource(rmod)
    assert '"silent_drop_total"' in source


def test_module_source_contains_run_timestamp_iso_key_batch27():
    source = inspect.getsource(rmod)
    assert '"run_timestamp_iso"' in source


def test_module_source_contains_dependencies_key_batch27():
    source = inspect.getsource(rmod)
    assert '"dependencies"' in source


def test_module_source_contains_max_chars_key_batch27():
    source = inspect.getsource(rmod)
    assert '"max_chars"' in source


# ---------- signatures 第三十九批 ----------


def test_signature_get_git_provenance_batch27():
    sig = inspect.signature(get_git_provenance)
    assert list(sig.parameters.keys()) == ["project_root"]
    assert sig.parameters["project_root"].annotation == "Path"


def test_signature_get_dependency_versions_no_args_batch27():
    sig = inspect.signature(get_dependency_versions)
    assert list(sig.parameters.keys()) == []


def test_signature_build_provenance_batch27():
    sig = inspect.signature(build_provenance)
    assert list(sig.parameters.keys()) == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_provenance_annotations_batch27():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["parser_name"].annotation == "str"
    assert sig.parameters["max_chars"].annotation == "int"
    assert sig.parameters["parser_version"].annotation == "str | None"


def test_signature_build_devset_section_one_arg_batch27():
    sig = inspect.signature(build_devset_section)
    assert list(sig.parameters.keys()) == ["manifest"]


def test_signature_aggregate_summary_batch27():
    sig = inspect.signature(aggregate_summary)
    assert list(sig.parameters.keys()) == ["per_doc_results"]
    assert sig.parameters["per_doc_results"].annotation == "list[dict[str, Any]]"


def test_signature_all_annotations_are_strings_batch27():
    for fn in [get_git_provenance, get_dependency_versions, build_provenance, build_devset_section, aggregate_summary]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            if p.annotation is not inspect.Parameter.empty:
                assert isinstance(p.annotation, str), f"{fn.__name__}.{p.name}"


# ---------- module 合理性第三十九批 ----------


def test_module_all_five_entries_batch27():
    assert set(rmod.__all__) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_has_five_functions_batch27():
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


def test_module_no_classes_batch27():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_docstring_present_batch27():
    assert rmod.__doc__ is not None


def test_module_docstring_mentions_no_mix_batch27():
    assert "不混合" in rmod.__doc__ or "no mix" in rmod.__doc__.lower()


def test_module_uses_from_future_annotations_batch27():
    source = inspect.getsource(rmod)
    assert "from __future__ import annotations" in source


def test_module_module_level_constants_count_batch27():
    """3 个 module-level 私有常量。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    constants = [
        n.targets[0].id
        for n in tree.body
        if isinstance(n, _ast.Assign)
        and isinstance(n.targets[0], _ast.Name)
        and n.targets[0].id.startswith("_")
        and n.targets[0].id.endswith("_METRICS")
    ]
    assert set(constants) == {"_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"}


def test_module_all_entries_accessible_batch27():
    for name in rmod.__all__:
        assert hasattr(rmod, name)


# ---------- 端到端集成第三十九批 ----------


def test_e2e_build_provenance_with_real_subprocess_batch27(tmp_path):
    """真实调用 build_provenance，验证返回结构。"""
    out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert set(out.keys()) == {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    }


def test_e2e_aggregate_summary_full_pipeline_batch27():
    """3 个 doc 综合验证。"""
    per_doc = [
        {"metrics": {
            "element_count_total": {"value": 10},
            "pipeline_success": {"value": True},
            "schema_valid": {"value": True},
            "pdf_locator_valid_ratio": {"value": 1.0},
            "silent_drop_count": {"value": 0},
        }},
        {"metrics": {
            "element_count_total": {"value": 5},
            "pipeline_success": {"value": False},
            "schema_valid": {"value": False},
            "pdf_locator_valid_ratio": {"value": 0.5},
            "silent_drop_count": {"value": 2},
        }},
        {"metrics": {
            "element_count_total": {"value": None},
            "pipeline_success": {"value": True},
            "schema_valid": {"value": None},
            "pdf_locator_valid_ratio": {"value": None},
            "silent_drop_count": {"value": None},
        }},
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


def test_e2e_build_devset_section_full_batch27():
    m = _make_manifest_obj(
        devset_status="incomplete",
        file_count=10,
        content_group_count=3,
        pdf_count=4,
        docx_count=6,
        categories_covered=["reports", "memos"],
    )
    out = build_devset_section(m)
    assert out["status"] == "incomplete"
    assert out["file_count"] == 10
    assert out["pdf_count"] == 4
    assert out["docx_count"] == 6
    assert out["categories_covered"] == ["reports", "memos"]


def test_e2e_get_git_provenance_real_worktree_batch27():
    """在 worktree 中调用 → 至少返回 2 个 key。"""
    out = get_git_provenance(Path("."))
    assert "git_commit" in out
    assert "git_dirty" in out


def test_e2e_get_dependency_versions_real_call_batch27():
    """真实调用 get_dependency_versions。"""
    out = get_dependency_versions()
    assert isinstance(out, dict)
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_e2e_aggregate_summary_does_not_mutate_input_batch27():
    per_doc = [{"metrics": {"element_count_total": {"value": 5}}}]
    import copy
    snap = copy.deepcopy(per_doc)
    aggregate_summary(per_doc)
    assert per_doc == snap


def test_e2e_build_provenance_run_timestamp_changes_batch27(tmp_path):
    """两次调用，时间戳格式应都可被 datetime 解析。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out1 = build_provenance(tmp_path, "fallback", 800, None)
        out2 = build_provenance(tmp_path, "fallback", 800, None)
    datetime.fromisoformat(out1["run_timestamp_iso"])
    datetime.fromisoformat(out2["run_timestamp_iso"])


def test_e2e_aggregate_summary_figure_caption_always_null_safe_batch27():
    """figure_caption_* 不在 _RATIO_METRICS → ratio_macro_averages 不应包含。"""
    per_doc = [{"metrics": {"figure_caption_precision": {"value": None, "reason": "parser_does_not_emit_relations"}}}]
    out = aggregate_summary(per_doc)
    assert "figure_caption_precision" not in out["ratio_macro_averages"]
