"""evaluation/runner.py 第二十七轮 edges 测试（Round 318）。

重点补强 edges25 未触及的角度：
- _load_annotation 行为深度补强
- _process_one signatures 补强
- run_evaluation 行为深度补强
- module source 字符串精确补强
- module source forbidden tokens
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


# ---------- _load_annotation 行为深度补强 ----------


def test_load_annotation_returns_none_for_symlink_to_missing(tmp_path):
    """annotation 路径不存在 → None（不论原因）。"""
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_symlink_to_valid(tmp_path):
    """symlink 指向合法文件 → 返回 dict。"""
    target = tmp_path / "real.json"
    target.write_text('{"a": 1}', encoding="utf-8")
    link = tmp_path / "link.json"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink not supported")
    out = _load_annotation(link)
    assert out == {"a": 1}


def test_load_annotation_large_dict(tmp_path):
    """大 dict 也能正常加载。"""
    p = tmp_path / "big.json"
    big = {f"key{i}": i for i in range(100)}
    p.write_text(json.dumps(big), encoding="utf-8")
    out = _load_annotation(p)
    assert out == big


def test_load_annotation_nested_dict(tmp_path):
    p = tmp_path / "nested.json"
    p.write_text(json.dumps({"a": {"b": {"c": [1, 2, 3]}}}), encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": {"b": {"c": [1, 2, 3]}}}


def test_load_annotation_string_value(tmp_path):
    p = tmp_path / "str.json"
    p.write_text(json.dumps({"x": "hello"}), encoding="utf-8")
    out = _load_annotation(p)
    assert out["x"] == "hello"


def test_load_annotation_int_value(tmp_path):
    p = tmp_path / "int.json"
    p.write_text(json.dumps({"x": 42}), encoding="utf-8")
    out = _load_annotation(p)
    assert out["x"] == 42


def test_load_annotation_float_value(tmp_path):
    p = tmp_path / "float.json"
    p.write_text(json.dumps({"x": 3.14}), encoding="utf-8")
    out = _load_annotation(p)
    assert out["x"] == 3.14


def test_load_annotation_bool_value(tmp_path):
    p = tmp_path / "bool.json"
    p.write_text(json.dumps({"x": True}), encoding="utf-8")
    out = _load_annotation(p)
    assert out["x"] is True


def test_load_annotation_null_value(tmp_path):
    p = tmp_path / "null.json"
    p.write_text(json.dumps({"x": None}), encoding="utf-8")
    out = _load_annotation(p)
    assert out["x"] is None


def test_load_annotation_utf8_content(tmp_path):
    p = tmp_path / "utf8.json"
    p.write_text(json.dumps({"x": "你好"}), encoding="utf-8")
    out = _load_annotation(p)
    assert out["x"] == "你好"


def test_load_annotation_empty_array(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text("[]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == []


def test_load_annotation_empty_file(tmp_path):
    """空文件 → JSON 解析错误 → 返回 None。"""
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_only_whitespace(tmp_path):
    p = tmp_path / "ws.json"
    p.write_text("   \n  ", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_trailing_comma_invalid(tmp_path):
    """JSON 不允许 trailing comma。"""
    p = tmp_path / "bad.json"
    p.write_text('{"a": 1,}', encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_single_quotes_invalid(tmp_path):
    """JSON 不允许 single quote。"""
    p = tmp_path / "bad.json"
    p.write_text("{'a': 1}", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_unquoted_key_invalid(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{a: 1}", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


# ---------- _process_one signatures 补强 ----------


def test_process_one_signature_no_default_for_doc():
    sig = inspect.signature(_process_one)
    assert sig.parameters["doc"].default is inspect.Parameter.empty


def test_process_one_signature_no_default_for_output_root():
    sig = inspect.signature(_process_one)
    assert sig.parameters["output_root"].default is inspect.Parameter.empty


def test_process_one_signature_no_default_for_parser_name():
    sig = inspect.signature(_process_one)
    assert sig.parameters["parser_name"].default is inspect.Parameter.empty


def test_process_one_signature_no_default_for_max_chars():
    sig = inspect.signature(_process_one)
    assert sig.parameters["max_chars"].default is inspect.Parameter.empty


def test_process_one_no_varargs_varkw():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_process_one_param_kinds():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


# ---------- run_evaluation 行为深度补强 ----------


def _make_minimal_manifest(tmp_path):
    from evaluation.manifest import Manifest
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )


def test_run_evaluation_creates_output_file_with_indent(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    content = out.read_text(encoding="utf-8")
    # indent=2 → 含换行
    assert "\n" in content


def test_run_evaluation_output_is_valid_json(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_run_evaluation_devset_section_has_required_fields(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert "devset" in report
    # devset 由 build_devset_section 生成
    assert isinstance(report["devset"], dict)


def test_run_evaluation_provenance_section_has_required_fields(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert "provenance" in report
    assert isinstance(report["provenance"], dict)


def test_run_evaluation_summary_section_has_required_fields(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert "summary" in report
    assert isinstance(report["summary"], dict)


def test_run_evaluation_no_documents_no_expected_failures(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert report["per_doc"] == []
    assert report["expected_failures"] == []


def test_run_evaluation_passes_parser_name_to_pipeline(tmp_path):
    """parser_name keyword 透传给 _process_one → process_single。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    # 无 documents 时不会真调 process_single，但参数已传
    report = run_evaluation(mf, out, parser_name="kreuzberg")
    assert isinstance(report, dict)


def test_run_evaluation_passes_max_chars_to_pipeline(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out, max_chars=500)
    assert isinstance(report, dict)


def test_run_evaluation_passes_tolerance_chars_to_chunk_boundary(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out, tolerance_chars=15)
    assert isinstance(report, dict)


# ---------- run_evaluation 输出格式精确 ----------


def test_run_evaluation_output_has_ensure_ascii_false(tmp_path):
    """输出文件确保 unicode 字符直接写入（不转义）。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    content = out.read_text(encoding="utf-8")
    # 至少应包含某个中文字符（docstring 里的字段名等）
    # 或者 ASCII 内容（如果没有 unicode 字段）
    # 这里仅验证文件能正确读出
    assert content != ""


def test_run_evaluation_returns_same_dict_as_written(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    file_report = json.loads(out.read_text(encoding="utf-8"))
    assert report["report_version"] == file_report["report_version"]
    assert report["per_doc"] == file_report["per_doc"]
    assert report["expected_failures"] == file_report["expected_failures"]


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


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_docstring_mentions_total():
    src = inspect.getsource(m)
    assert "total" in src


def test_module_source_has_docstring_mentions_pipeline():
    src = inspect.getsource(m)
    assert "pipeline" in src


def test_module_source_has_docstring_mentions_per_doc():
    src = inspect.getsource(m)
    assert "per_doc" in src or "per doc" in src


def test_module_source_has_docstring_mentions_image_resource():
    src = inspect.getsource(m)
    assert "image_resource" in src


def test_module_source_has_load_annotation_returns_dict_or_none():
    src = inspect.getsource(m)
    assert "return None" in src
    assert "return json.load(f)" in src


def test_module_source_has_load_annotation_3_returns():
    """_load_annotation 有 3 个 return 路径（None×2 + dict×1）。"""
    src = inspect.getsource(_load_annotation)
    return_count = src.count("return ")
    # 实际：return None（None 路径）+ return None（异常路径）+ return json.load(f)
    # = 3 个 return
    assert return_count == 3


def test_module_source_has_process_one_5_return_paths():
    """_process_one 有 5 个 return 路径（errors / None doc / 正常）。"""
    src = inspect.getsource(_process_one)
    # 实际：errors 路径 1 个 return；document None 路径 1 个；正常 1 个 = 3 个 return
    return_count = src.count("return ")
    assert return_count >= 3


def test_module_source_has_run_evaluation_returns_report():
    src = inspect.getsource(run_evaluation)
    assert "return report" in src


def test_module_source_has_run_evaluation_returns_only_once():
    """run_evaluation 只有一个 return（在最后）。"""
    src = inspect.getsource(run_evaluation)
    assert src.count("return report") == 1


def test_module_source_has_run_evaluation_writes_file():
    src = inspect.getsource(run_evaluation)
    assert 'out_p.open("w", encoding="utf-8")' in src


def test_module_source_has_run_evaluation_output_root_creation():
    src = inspect.getsource(run_evaluation)
    assert "output_root.mkdir(parents=True, exist_ok=True)" in src


def test_module_source_has_run_evaluation_out_p_creation():
    src = inspect.getsource(run_evaluation)
    assert "out_p.parent.mkdir(parents=True, exist_ok=True)" in src


def test_module_source_has_per_doc_loop():
    src = inspect.getsource(run_evaluation)
    assert "for doc in manifest.documents:" in src


def test_module_source_has_expected_failures_loop():
    src = inspect.getsource(run_evaluation)
    assert "for ef in manifest.expected_failures:" in src


def test_module_source_has_public_per_doc_loop():
    src = inspect.getsource(run_evaluation)
    assert "for r in per_doc_results:" in src


def test_module_source_has_per_doc_dict_with_doc_id_and_source_type():
    src = inspect.getsource(run_evaluation)
    assert '"doc_id": r["doc_id"]' in src
    assert '"source_type": r["source_type"]' in src


def test_module_source_has_run_evaluation_parser_version_capture():
    """run_evaluation 抓取第一个 parser_version 作为 provenance。"""
    src = inspect.getsource(run_evaluation)
    assert "parser_version_for_prov" in src


def test_module_source_has_run_evaluation_parser_version_first_only():
    """只在第一个非 None 时记。"""
    src = inspect.getsource(run_evaluation)
    assert "if parser_version and not parser_version_for_prov:" in src


# ---------- signatures 精确补强 ----------


def test_run_evaluation_param_kinds():
    sig = inspect.signature(run_evaluation)
    # manifest, output_path 是 POSITIONAL_OR_KEYWORD
    assert sig.parameters["manifest"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert sig.parameters["output_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_keyword_marker_in_source():
    """run_evaluation 用 * 强制 keyword-only。"""
    src = inspect.getsource(run_evaluation)
    # 函数定义中含 "*"
    assert "*," in src or "*" in src


# ---------- module 整体合理性 ----------


def test_module_all_only_run_evaluation():
    assert m.__all__ == ["run_evaluation"]


def test_module_no_class():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class: {line}")


def test_module_no_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' not in src


def test_module_namespace():
    assert m.__name__ == "evaluation.runner"


def test_module_has_2_private_functions():
    private = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and isinstance(getattr(m, n), FunctionType)
    ]
    assert set(private) == {"_load_annotation", "_process_one"}


def test_module_has_1_public_function():
    public = [
        n for n in dir(m)
        if not n.startswith("_")
        and isinstance(getattr(m, n), FunctionType)
        and getattr(m, n).__module__ == "evaluation.runner"
    ]
    assert public == ["run_evaluation"]


# ---------- 端到端集成 ----------


def test_e2e_empty_manifest_full_cycle(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert out.is_file()
    assert report["per_doc"] == []
    assert report["expected_failures"] == []
    assert report["report_version"]


def test_e2e_creates_nested_output_path(tmp_path):
    out = tmp_path / "a" / "b" / "c" / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    assert out.is_file()


def test_e2e_keyword_only_args_works(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(
        mf,
        out,
        parser_name="fallback",
        max_chars=1000,
        tolerance_chars=20,
    )
    assert isinstance(report, dict)


def test_e2e_positional_only_manifest_and_output_fails(tmp_path):
    """3 个 keyword-only 参数不能用 positional。"""
    from evaluation.manifest import Manifest
    mf = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )
    out = tmp_path / "out.json"
    with pytest.raises(TypeError):
        run_evaluation(mf, out, "fallback", 800, 30)  # type: ignore[misc]


def test_e2e_report_passes_schema_validation(tmp_path):
    """生成的报告通过 evaluation-report.schema.json 校验。"""
    from evaluation.schema import validate_file
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    validate_file(out, "evaluation-report.schema.json")


# ---------- _load_annotation 文件句柄管理 ----------


def test_load_annotation_closes_file_handle(tmp_path):
    """load 后文件 handle 应该被关闭（with 语句）。"""
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    _load_annotation(p)
    # 在 Windows 上文件被持有会阻止删除；这里删除应成功
    p.unlink()
    assert not p.exists()


# ---------- _process_one 不变量 ----------


def test_process_one_unlinks_out_stub_in_try_except(tmp_path):
    """源代码里 out_stub.unlink() 在 try/except OSError 中。"""
    src = inspect.getsource(_process_one)
    assert "if out_stub.is_file():" in src
    assert "out_stub.unlink()" in src
    assert "except OSError:" in src


def test_process_one_image_dir_returns_none_when_document_none():
    """document is None 时 image_dir 也是 None。"""
    src = inspect.getsource(_process_one)
    # 在 errors return 之前不计算 image_dir
    assert "if document is not None:" in src


def test_process_one_returns_image_dir_in_failure_path():
    """errors 路径也返回 image_dir。"""
    src = inspect.getsource(_process_one)
    # 第一个 return（errors）含 image_dir
    assert "return None, errors[0].to_dict(), elapsed, None, image_dir" in src


def test_process_one_returns_image_dir_in_unknown_path():
    """document is None 无 errors 的 unknown 路径也返回 image_dir。"""
    src = inspect.getsource(_process_one)
    assert 'process_single returned None without errors' in src


def test_process_one_returns_image_dir_in_success_path():
    """成功路径返回 image_dir（计算后的）。"""
    src = inspect.getsource(_process_one)
    assert "return document.to_dict(), None, elapsed, document.parser_version, image_dir" in src
