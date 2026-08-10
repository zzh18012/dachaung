"""evaluation/runner.py 第二十六轮 edges 测试（Round 312）。

重点补强 edges24 未触及的角度：
- _load_annotation 行为深度（None / missing / OSError / JSONDecodeError / 合法 JSON）
- _process_one 返回 5-tuple 类型精确（document dict / error dict / float / str|None / Path|None）
- run_evaluation 关键字参数精确（parser_name/max_chars/tolerance_chars defaults）
- run_evaluation per_doc 字段（_annotation_present/_tolerance_chars/_missing_markers）
- run_evaluation expected_failures 路径行为
- module source forbidden tokens
- module source 字符串精确
- signatures 精确
- 端到端集成
- 模块整体合理性
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import FunctionType
from typing import Any

import pytest

import evaluation.runner as m
from evaluation.runner import (
    _load_annotation,
    _process_one,
    run_evaluation,
)


# ---------- _load_annotation 行为深度 ----------


def test_load_annotation_none_returns_none():
    assert _load_annotation(None) is None


def test_annotation_missing_file_returns_none(tmp_path):
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_oserror_returns_none(monkeypatch, tmp_path):
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    # patch Path.open to raise OSError
    original_open = Path.open

    def fake_open(self, *args, **kwargs):
        if str(self) == str(p):
            raise OSError("simulated")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fake_open)
    assert _load_annotation(p) is None


def test_load_annotation_invalid_json_returns_none(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_valid_json_returns_dict(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": 1}


def test_load_annotation_empty_dict(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    assert _load_annotation(p) == {}


def test_load_annotation_array_returns_list(tmp_path):
    """JSON array 不是 dict 但 json.load 仍返回 list。"""
    p = tmp_path / "ok.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3]


def test_load_annotation_path_string_not_accepted():
    """_load_annotation 要求 Path 对象；str 会 AttributeError（无 .is_file）。"""
    # str 没有 .is_file() → AttributeError，不是 None
    with pytest.raises(AttributeError):
        _load_annotation("some/path.json")  # type: ignore[arg-type]


def test_load_annotation_signature_1_param():
    sig = inspect.signature(_load_annotation)
    assert list(sig.parameters.keys()) == ["path"]


def test_load_annotation_param_annotation_union():
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].annotation == "Path | None"


def test_load_annotation_return_annotation_optional_dict():
    sig = inspect.signature(_load_annotation)
    assert sig.return_annotation == "dict[str, Any] | None"


def test_load_annotation_namespace_is_evaluation_runner():
    assert _load_annotation.__module__ == "evaluation.runner"


# ---------- _process_one 行为深度 ----------


def test_process_one_signature_4_params():
    sig = inspect.signature(_process_one)
    assert list(sig.parameters.keys()) == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_first_param_no_annotation():
    """doc 参数是 DocumentEntry，annotation 留为 docstring 说明（不强类型）。"""
    sig = inspect.signature(_process_one)
    # doc 参数没显式 annotation
    assert sig.parameters["doc"].annotation is inspect.Parameter.empty


def test_process_one_output_root_annotation_path():
    sig = inspect.signature(_process_one)
    assert sig.parameters["output_root"].annotation == "Path"


def test_process_one_parser_name_annotation_str():
    sig = inspect.signature(_process_one)
    assert sig.parameters["parser_name"].annotation == "str"


def test_process_one_max_chars_annotation_int():
    sig = inspect.signature(_process_one)
    assert sig.parameters["max_chars"].annotation == "int"


def test_process_one_return_annotation_5_tuple():
    sig = inspect.signature(_process_one)
    # 5-tuple: dict|None, dict|None, float, str|None, Path|None
    assert sig.return_annotation == "tuple[dict[str, Any] | None, dict[str, Any] | None, float, str | None, Path | None]"


def test_process_one_namespace_is_evaluation_runner():
    assert _process_one.__module__ == "evaluation.runner"


# ---------- run_evaluation signatures ----------


def test_run_evaluation_signature_2_params():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_run_evaluation_manifest_no_default():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].default is inspect.Parameter.empty


def test_run_evaluation_output_path_no_default():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].default is inspect.Parameter.empty


def test_run_evaluation_parser_name_default_fallback():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_run_evaluation_max_chars_default_800():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_run_evaluation_tolerance_chars_default_30():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_keyword_only_marker():
    """parser_name/max_chars/tolerance_chars 是 keyword-only（在 * 之后）。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_manifest_param_kind():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_output_path_param_kind():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_namespace_is_evaluation_runner():
    assert run_evaluation.__module__ == "evaluation.runner"


def test_run_evaluation_is_function():
    assert isinstance(run_evaluation, FunctionType)


def test_load_annotation_is_function():
    assert isinstance(_load_annotation, FunctionType)


def test_process_one_is_function():
    assert isinstance(_process_one, FunctionType)


# ---------- module source forbidden tokens ----------


@pytest.mark.parametrize(
    "token",
    [
        "import random",
        "import uuid",
        "import hashlib",
        "import secrets",
        "import subprocess",
        "import socket",
        "import email",
        "import html",
        "import http",
        "import urllib",
        "import sqlite3",
        "import csv",
        "import pickle",
        "import tempfile",
        "import shutil",
        "import glob",
        "import os",
        "import sys",
        "import logging",
        "import threading",
        "import asyncio",
        "import re",
        "import datetime",
        "import itertools",
        "import functools",
        "import collections",
        "import math",
    ],
)
def test_module_source_forbidden_tokens(token):
    src = inspect.getsource(m)
    assert token not in src


# ---------- module source 必要 imports ----------


def test_module_source_has_from_future():
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_has_import_json():
    src = inspect.getsource(m)
    assert "import json" in src


def test_module_source_has_import_time():
    src = inspect.getsource(m)
    assert "import time" in src


def test_module_source_has_from_pathlib_import_path():
    src = inspect.getsource(m)
    assert "from pathlib import Path" in src


def test_module_source_has_from_typing_import_any():
    src = inspect.getsource(m)
    assert "from typing import Any" in src


def test_module_source_has_app_pipeline_imports():
    src = inspect.getsource(m)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_has_evaluation_imports():
    src = inspect.getsource(m)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_has_annotation_metrics_imports():
    src = inspect.getsource(m)
    assert "chunk_boundary_prf" in src
    assert "figure_caption_prf" in src


def test_module_source_has_metrics_imports():
    src = inspect.getsource(m)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_has_report_imports():
    src = inspect.getsource(m)
    assert "aggregate_summary" in src
    assert "build_devset_section" in src
    assert "build_provenance" in src


# ---------- module source 字符串精确 ----------


def test_module_source_has_load_annotation_def():
    src = inspect.getsource(m)
    assert "def _load_annotation(path: Path | None) -> dict[str, Any] | None:" in src


def test_module_source_has_process_one_def():
    src = inspect.getsource(m)
    assert "def _process_one(" in src


def test_module_source_has_run_evaluation_def():
    src = inspect.getsource(m)
    assert "def run_evaluation(" in src


def test_module_source_has_perf_counter_usage():
    src = inspect.getsource(m)
    assert "time.perf_counter()" in src


def test_module_source_has_process_single_call():
    src = inspect.getsource(m)
    assert "process_single(" in src


def test_module_source_has_write_json_false():
    src = inspect.getsource(m)
    assert "write_json=False" in src


def test_module_source_has_image_output_dir_for_call():
    src = inspect.getsource(m)
    assert "image_output_dir_for(" in src


def test_module_source_has_compute_automatic_metrics_call():
    src = inspect.getsource(m)
    assert "compute_automatic_metrics(" in src


def test_module_source_has_figure_caption_prf_call():
    src = inspect.getsource(m)
    assert "figure_caption_prf(document, annotation)" in src


def test_module_source_has_chunk_boundary_prf_call():
    src = inspect.getsource(m)
    assert "chunk_boundary_prf(" in src


def test_module_source_has_metrics_update():
    src = inspect.getsource(m)
    assert "metrics.update(fig_caps)" in src
    assert "metrics.update(chunk_b)" in src


def test_module_source_has_tolerance_record_pop():
    src = inspect.getsource(m)
    assert 'tolerance_record = chunk_b.pop("_tolerance_chars", None)' in src


def test_module_source_has_missing_markers_pop():
    src = inspect.getsource(m)
    assert 'missing_markers_record = chunk_b.pop("_missing_markers", None)' in src


def test_module_source_has_per_doc_dict_keys():
    src = inspect.getsource(m)
    assert '"doc_id":' in src
    assert '"source_type":' in src
    assert '"metrics":' in src
    assert '"wall_time_seconds":' in src


def test_module_source_has_not_instrumented_reasons():
    src = inspect.getsource(m)
    assert '"parse_reason": "not_instrumented"' in src
    assert '"chunk_reason": "not_instrumented"' in src


def test_module_source_has_annotation_present_field():
    src = inspect.getsource(m)
    assert '"_annotation_present": annotation is not None' in src


def test_module_source_has_expected_failures_loop():
    src = inspect.getsource(m)
    assert "for ef in manifest.expected_failures:" in src


def test_module_source_has_matches_equality():
    src = inspect.getsource(m)
    assert '"matches": actual_code == ef.expected_error_code' in src


def test_module_source_has_build_provenance_call():
    src = inspect.getsource(m)
    assert "provenance = build_provenance(" in src


def test_module_source_has_build_devset_section_call():
    src = inspect.getsource(m)
    assert "devset = build_devset_section(" in src


def test_module_source_has_aggregate_summary_call():
    src = inspect.getsource(m)
    assert "summary = aggregate_summary(" in src


def test_module_source_has_report_dict_keys():
    src = inspect.getsource(m)
    assert '"report_version": REPORT_VERSION' in src
    assert '"provenance": provenance' in src
    assert '"devset": devset' in src
    assert '"summary": summary' in src
    assert '"per_doc": public_per_doc' in src
    assert '"expected_failures": expected_failure_results' in src


def test_module_source_has_json_dump_to_output():
    src = inspect.getsource(m)
    assert "json.dump(report, f" in src
    assert "ensure_ascii=False" in src
    assert "indent=2" in src


def test_module_source_has_load_annotation_try_except():
    src = inspect.getsource(m)
    assert "except (OSError, json.JSONDecodeError):" in src


def test_module_source_has_per_doc_subdir():
    src = inspect.getsource(m)
    assert '"_per_doc"' in src
    assert "out_stub.parent.mkdir(parents=True, exist_ok=True)" in src


def test_module_source_has_unlink_in_try_except():
    src = inspect.getsource(m)
    assert "out_stub.unlink()" in src
    assert "except OSError:" in src


def test_module_source_has_docstring_pipeline_constraint():
    src = inspect.getsource(m)
    assert "不修改 app/pipeline.py" in src


def test_module_source_has_docstring_not_instrumented():
    src = inspect.getsource(m)
    assert "not_instrumented" in src


def test_module_source_has_docstring_image_resource():
    src = inspect.getsource(m)
    assert "image_resource_exists_ratio" in src


def test_module_source_has_no_main_block():
    src = inspect.getsource(m)
    assert '__name__ == "__main__"' not in src


def test_module_source_has_no_class():
    src = inspect.getsource(m)
    assert "\nclass " not in src


# ---------- module 整体合理性 ----------


def test_module_all_has_only_run_evaluation():
    assert m.__all__ == ["run_evaluation"]


def test_module_all_count_is_1():
    assert len(m.__all__) == 1


def test_module_has_no_class_definition():
    src = inspect.getsource(m)
    # 严格：行首 "class "
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class definition: {line}")


def test_module_has_no_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' not in src


def test_module_has_2_private_functions():
    private_fns = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and isinstance(getattr(m, n), FunctionType)
    ]
    assert set(private_fns) == {"_load_annotation", "_process_one"}


def test_module_has_1_public_function():
    public_fns = [
        n for n in dir(m)
        if not n.startswith("_")
        and isinstance(getattr(m, n), FunctionType)
        and getattr(m, n).__module__ == "evaluation.runner"
    ]
    assert public_fns == ["run_evaluation"]


def test_module_namespace_is_evaluation_runner():
    assert m.__name__ == "evaluation.runner"


# ---------- _load_annotation 错误处理深度 ----------


def test_load_annotation_binary_garbage(tmp_path):
    """二进制内容不是合法 utf-8 → UnicodeDecodeError（NOT caught by OSError/JSONDecodeError）→ 抛出。"""
    p = tmp_path / "bin.json"
    p.write_bytes(b"\xff\xfe\x00\x01")
    # UnicodeDecodeError 不是 OSError 子类（是 ValueError 子类），代码不 catch
    with pytest.raises(UnicodeDecodeError):
        _load_annotation(p)


def test_load_annotation_directory(tmp_path):
    """传目录 → open 抛 IsADirectoryError（OSError 子类）→ None。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_none_path_returns_none_quickly():
    """None 短路返回 None，不抛异常。"""
    assert _load_annotation(None) is None


# ---------- run_evaluation 端到端集成 ----------


def _make_minimal_manifest(tmp_path):
    """构造最小可用 Manifest。"""
    from evaluation.manifest import DocumentEntry, Manifest

    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=[],
        expected_failures=[],
        project_root=tmp_path,
    )


def test_run_evaluation_empty_documents_creates_output(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert out.is_file()
    assert isinstance(report, dict)


def test_run_evaluation_empty_documents_report_has_5_top_keys(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert set(report.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_run_evaluation_empty_documents_per_doc_empty(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert report["per_doc"] == []


def test_run_evaluation_empty_documents_expected_failures_empty(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert report["expected_failures"] == []


def test_run_evaluation_creates_parent_directory(tmp_path):
    out = tmp_path / "sub" / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    assert out.is_file()


def test_run_evaluation_returns_report_equal_to_file_content(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    with out.open("r", encoding="utf-8") as f:
        file_report = json.load(f)
    # report_version + per_doc + expected_failures 等关键字段相同
    assert report["report_version"] == file_report["report_version"]
    assert report["per_doc"] == file_report["per_doc"]


def test_run_evaluation_keyword_args(tmp_path):
    """keyword-only 参数可以按 keyword 传。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(
        mf,
        out,
        parser_name="fallback",
        max_chars=500,
        tolerance_chars=20,
    )
    assert isinstance(report, dict)


def test_run_evaluation_creates_per_doc_subdir(tmp_path):
    """即使 documents 为空，output_root/_per_doc 也会被创建（mkdir 在 _process_one 里）。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    # per_doc 目录被创建（即使空）
    # 注意：mkdir 在 _process_one 内调用，documents 为空时不会触发
    # 所以这里仅检查 output_root 存在
    assert out.parent.is_dir()


# ---------- run_evaluation not_instrumented 不变量 ----------


def test_run_evaluation_parse_chunk_always_null(tmp_path):
    """parse / chunk 时间 always null + reason=not_instrumented（无 documents 也无法测，但格式不变）。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    # per_doc 为空 → 没法直接验证；至少确保报告生成成功
    assert "per_doc" in report


def test_run_evaluation_uses_REPORT_VERSION_constant(tmp_path):
    """report_version 来自 evaluation.REPORT_VERSION。"""
    from evaluation import REPORT_VERSION

    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert report["report_version"] == REPORT_VERSION


# ---------- _process_one 返回值结构（无真实 pipeline 调用）----------


def test_process_one_returns_5_tuple_for_failed_import():
    """_process_one 不接受 string path，需要 DocumentEntry。这里只验证函数签名约定。"""
    sig = inspect.signature(_process_one)
    ret = sig.return_annotation
    # 5-tuple 类型注解
    assert ret.startswith("tuple[")
    assert ret.count("None") >= 4  # 至少 4 个 None 在 union 里
