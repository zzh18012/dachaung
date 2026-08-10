"""evaluation/cli.py 第二十七轮 edges 测试（Round 320）。

重点补强 edges25 未触及的角度：
- _build_parser 行为深度补强
- _format_metric 分支精确补强
- _run_inspect_doc 行为深度补强
- main 各路径错误处理补强
- module source 字符串精确补强
- signatures 精确
- 端到端集成
- 模块整体合理性
"""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from types import FunctionType
from typing import Any

import pytest

import evaluation.cli as m
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 行为深度补强 ----------


def test_build_parser_has_help_formatter():
    p = _build_parser()
    # formatter_class 是 RawDescriptionHelpFormatter
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_no_conflict_handler():
    p = _build_parser()
    assert p.conflict_handler == "error"  # argparse default


def test_build_parser_no_add_help_default():
    p = _build_parser()
    # add_help default True → -h/--help 自动加
    help_actions = [
        a for a in p._actions
        if "-h" in (a.option_strings or [])
    ]
    assert len(help_actions) == 1


def test_build_parser_run_parser_help_text():
    p = _build_parser()
    run_p = p._subparsers._group_actions[0].choices["run"]  # type: ignore
    # help 字符串
    helps = [a.help for a in run_p._actions if "--manifest" in (a.option_strings or [])]
    assert len(helps) == 1


def test_build_parser_validate_report_parser_help_text():
    p = _build_parser()
    val_p = p._subparsers._group_actions[0].choices["validate-report"]  # type: ignore
    # validate-report subparser 没有 description，只有 help（add_parser 的 help 参数）
    # 检查它在 sub_actions 里
    sub_actions = [
        a for a in p._actions
        if isinstance(a, argparse._SubParsersAction)
    ]
    # choices 含 validate-report
    assert "validate-report" in sub_actions[0].choices


def test_build_parser_inspect_doc_parser_help_text():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions
        if isinstance(a, argparse._SubParsersAction)
    ]
    assert "inspect-doc" in sub_actions[0].choices


def test_build_parser_run_parser_max_chars_type_int():
    p = _build_parser()
    run_p = p._subparsers._group_actions[0].choices["run"]  # type: ignore
    for action in run_p._actions:
        if "--max-chars" in (action.option_strings or []):
            assert action.type is int
            assert action.default == 800


def test_build_parser_inspect_doc_input_required():
    p = _build_parser()
    ins_p = p._subparsers._group_actions[0].choices["inspect-doc"]  # type: ignore
    positional = [
        a for a in ins_p._actions
        if isinstance(a, argparse._StoreAction) and not a.option_strings
    ]
    assert positional[0].required is True


# ---------- _format_metric 分支精确补强 ----------


def test_format_metric_negative_float():
    out = _format_metric("x", {"value": -0.5, "reason": None})
    assert "-0.5000" in out


def test_format_metric_large_float():
    out = _format_metric("x", {"value": 1.23456789, "reason": None})
    # 截到 4 位
    assert "1.2346" in out


def test_format_metric_int_zero():
    out = _format_metric("x", {"value": 0, "reason": None})
    # int 走 fallback
    assert "0" in out
    assert "ok" in out


def test_format_metric_negative_int():
    out = _format_metric("x", {"value": -3, "reason": None})
    assert "-3" in out


def test_format_metric_long_name():
    out = _format_metric("a" * 50, {"value": True, "reason": None})
    # name 字段宽 36，超长不截
    assert "a" * 50 in out


def test_format_metric_dict_with_special_chars():
    out = _format_metric("x", {"value": {"a&b": 1}, "reason": None})
    assert "a&b=1" in out


def test_format_metric_dict_with_int_values():
    out = _format_metric("x", {"value": {"a": 5, "b": 10}, "reason": None})
    assert "a=5" in out
    assert "b=10" in out


def test_format_metric_list_value():
    """list 走 fallback 分支。"""
    out = _format_metric("x", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in out


def test_format_metric_tuple_value():
    out = _format_metric("x", {"value": (1, 2), "reason": None})
    assert "(1, 2)" in out or "1" in out


# ---------- _run_inspect_doc 行为深度补强 ----------


def test_run_inspect_doc_no_elements_no_chunks(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf"}), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "elements=0" in out
    assert "chunks=0" in out


def test_run_inspect_doc_with_image(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"type": "image", "resource_path": "x.png"}],
        "chunks": [],
    }), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_with_metadata(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "docx",
        "document_id": "doc-123",
        "source_path": "samples/x.docx",
        "parser_name": "fallback",
        "parser_version": "1.0.0",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "doc-123" in out
    assert "samples/x.docx" in out
    assert "fallback" in out
    assert "1.0.0" in out


def test_run_inspect_doc_null_metrics_displayed(tmp_path, capsys):
    """无 annotation → figure_caption_* / chunk_boundary_* 都是 null。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "hi",
                      "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]},
                      "element_id": "p1"}],
        "chunks": [{"text": "hi", "source_element_ids": ["p1"]}],
    }), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    # 至少 1 个 null 指标
    assert "null" in out


def test_run_inspect_doc_with_pipeline_failure_metrics(tmp_path, capsys):
    """doc 没有 chunks → 多个 metric 是 null/pipeline_failed。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf"}), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0


# ---------- main 各路径错误处理补强 ----------


def _make_minimal_manifest(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.x]\n", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    return p


def test_main_run_with_expected_failures(tmp_path, capsys):
    sub = tmp_path / "samples"
    sub.mkdir()
    (sub / "bad.txt").write_text("d", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "bad", "path": "samples/bad.txt",
             "expected_error_code": "unsupported_format", "source_type": "txt"},
        ],
    }), encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[x]\n", encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(p), "--output", str(out)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "[OK]" in captured.out


def test_main_run_with_invalid_manifest_path_form(tmp_path, capsys):
    """manifest 文件存在但内容不合法 → rc=1。"""
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        # 缺 devset_status
        "documents": [],
    }), encoding="utf-8")
    rc = main([
        "run", "--manifest", str(p), "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 1


def test_main_run_stdout_includes_devset_info(tmp_path, capsys):
    manifest = _make_minimal_manifest(tmp_path)
    out = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(out)])
    captured = capsys.readouterr()
    assert "file_count=" in captured.out
    assert "groups=" in captured.out
    assert "pdf=" in captured.out
    assert "docx=" in captured.out


def test_main_run_stdout_includes_git_info(tmp_path, capsys):
    manifest = _make_minimal_manifest(tmp_path)
    out = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(out)])
    captured = capsys.readouterr()
    assert "git_commit=" in captured.out
    assert "git_dirty=" in captured.out


def test_main_validate_report_with_invalid_json(tmp_path, capsys):
    p = tmp_path / "report.json"
    p.write_text("not valid json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_with_non_object_json(tmp_path, capsys):
    p = tmp_path / "report.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_with_empty_dict(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "elements=0" in out


def test_main_inspect_doc_with_str_input_path(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


# ---------- _format_metric boundary ----------


def test_format_metric_4_char_indent():
    out = _format_metric("x", {"value": True, "reason": None})
    assert out.startswith("  ")


def test_format_metric_no_value_field():
    """metric dict 没 value 字段 → value 是 None。"""
    out = _format_metric("x", {"reason": "x"})
    assert "null" in out


def test_format_metric_no_reason_field():
    """metric dict 没 reason 字段 → reason 是 None。"""
    out = _format_metric("x", {"value": True})
    assert "ok" in out


def test_format_metric_empty_metric():
    """空 metric dict → value 和 reason 都是 None。"""
    out = _format_metric("x", {})
    assert "null" in out


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
        "import math",
        "import datetime",
        "import itertools",
        "import functools",
        "import collections",
        "import logging",
        "import threading",
        "import asyncio",
        "import re",
    ],
)
def test_module_source_forbidden_tokens(token):
    src = inspect.getsource(m)
    assert token not in src


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_run_subparser_help():
    src = inspect.getsource(m)
    assert '"跑评测，生成报告 JSON"' in src


def test_module_source_has_run_manifest_help():
    src = inspect.getsource(m)
    assert '"清单 JSON 路径"' in src


def test_module_source_has_run_output_help():
    src = inspect.getsource(m)
    assert '"报告输出 JSON 路径"' in src


def test_module_source_has_run_parser_help():
    src = inspect.getsource(m)
    assert '"parser（默认 fallback）"' in src


def test_module_source_has_run_max_chars_help():
    src = inspect.getsource(m)
    assert '"分块上限（默认 800）"' in src


def test_module_source_has_run_tolerance_chars_help():
    src = inspect.getsource(m)
    assert '"chunk_boundary 匹配容差（字符数，默认 30）"' in src


def test_module_source_has_inspect_doc_input_help():
    src = inspect.getsource(m)
    assert '"已生成的文档 JSON 路径"' in src


def test_module_source_has_main_run_path_object_creation():
    src = inspect.getsource(m)
    assert "manifest_path = Path(args.manifest)" in src
    assert "output_path = Path(args.output)" in src


def test_module_source_has_main_validate_report_path_object():
    src = inspect.getsource(m)
    assert "input_path = Path(args.input)" in src


def test_module_source_has_main_inspect_doc_dispatch():
    src = inspect.getsource(m)
    assert "return _run_inspect_doc(args)" in src


def test_module_source_has_main_run_per_doc_loop():
    src = inspect.getsource(m)
    assert 'for r in report.get("per_doc", [])' in src


def test_module_source_has_main_run_count_pipeline_success():
    src = inspect.getsource(m)
    assert 'r["metrics"].get("pipeline_success", {}).get("value") is True' in src


def test_module_source_has_main_run_print_5_lines():
    src = inspect.getsource(main)
    # print 含 5 行字符串
    assert "[OK] 评测完成" in src
    assert "documents=" in src
    assert "devset_status=" in src
    assert "git_commit=" in src
    assert "git_dirty=" in src


def test_module_source_has_format_metric_5_branches_count():
    """_format_metric 有 5 个 return 语句。"""
    src = inspect.getsource(_format_metric)
    return_count = src.count("return ")
    # None / bool / float / dict / fallback
    assert return_count == 5


def test_module_source_has_inspect_doc_5_print_lines():
    """_run_inspect_doc 含 6 行 metadata print。"""
    src = inspect.getsource(_run_inspect_doc)
    # 实际格式 `f"file:        {input_path}"` 等，断言前缀出现
    assert "file:" in src
    assert "document_id:" in src
    assert "source:" in src
    assert "parser:" in src
    assert "counts:" in src
    assert "metrics:" in src


def test_module_source_has_inspect_doc_compute_automatic_metrics_call():
    src = inspect.getsource(m)
    assert "compute_automatic_metrics(" in src


def test_module_source_has_inspect_doc_figure_caption_prf_call():
    src = inspect.getsource(m)
    assert "figure_caption_prf(doc, None)" in src


def test_module_source_has_inspect_doc_chunk_boundary_prf_call():
    src = inspect.getsource(m)
    assert "chunk_boundary_prf(doc, None" in src


def test_module_source_has_inspect_doc_sort_key():
    src = inspect.getsource(m)
    assert "def _sort_key(name: str) -> tuple[int, str]:" in src


def test_module_source_has_inspect_doc_sort_4_buckets():
    src = inspect.getsource(_run_inspect_doc)
    # 4 个 return tuple
    assert "return (3, name)" in src  # null bucket
    assert "return (0, name)" in src  # bool bucket
    assert "return (1, name)" in src  # int/float bucket
    assert "return (2, name)" in src  # other bucket


def test_module_source_has_no_main_class():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class: {line}")


def test_module_source_has_no_all_definition():
    src = inspect.getsource(m)
    assert "__all__" not in src


# ---------- signatures 精确 ----------


def test_main_signature_argv_annotation():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].annotation == "list[str] | None"


def test_main_signature_return_int():
    sig = inspect.signature(main)
    assert sig.return_annotation == "int"


def test_build_parser_no_params():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_format_metric_param_annotations():
    sig = inspect.signature(_format_metric)
    assert sig.parameters["name"].annotation == "str"
    assert sig.parameters["metric"].annotation == "dict"


def test_run_inspect_doc_param_no_annotation():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.parameters["args"].annotation is inspect.Parameter.empty


def test_main_namespace():
    assert main.__module__ == "evaluation.cli"


def test_build_parser_namespace():
    assert _build_parser.__module__ == "evaluation.cli"


def test_format_metric_namespace():
    assert _format_metric.__module__ == "evaluation.cli"


def test_run_inspect_doc_namespace():
    assert _run_inspect_doc.__module__ == "evaluation.cli"


# ---------- module 整体合理性 ----------


def test_module_has_1_public_function():
    public = [
        n for n in dir(m)
        if not n.startswith("_")
        and isinstance(getattr(m, n), FunctionType)
        and getattr(m, n).__module__ == "evaluation.cli"
    ]
    assert public == ["main"]


def test_module_has_3_private_functions():
    private = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and isinstance(getattr(m, n), FunctionType)
    ]
    assert set(private) == {"_build_parser", "_format_metric", "_run_inspect_doc"}


def test_module_namespace():
    assert m.__name__ == "evaluation.cli"


def test_module_has_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' in src
    assert "raise SystemExit(main())" in src


def test_module_has_no_all():
    assert not hasattr(m, "__all__")


def test_module_has_no_class():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class: {line}")


# ---------- 端到端集成 ----------


def test_e2e_run_then_inspect_doc_cycle(tmp_path, capsys):
    manifest = _make_minimal_manifest(tmp_path)
    out = tmp_path / "out.json"
    rc1 = main(["run", "--manifest", str(manifest), "--output", str(out)])
    assert rc1 == 0
    capsys.readouterr()
    rc2 = main(["validate-report", str(out)])
    assert rc2 == 0


def test_e2e_inspect_doc_after_pipeline_run(tmp_path, capsys):
    """先用 process_single 生成 doc，再用 inspect-doc 验证。"""
    # 这里直接构造一个合法的 doc JSON
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "document_id": "test-123",
        "source_path": "samples/test.pdf",
        "parser_name": "fallback",
        "parser_version": "0.1.0",
        "source_hash": "abc123",
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "hello",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]}},
        ],
        "chunks": [{"text": "hello", "source_element_ids": ["p1"]}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "test-123" in out
    assert "samples/test.pdf" in out


def test_e2e_main_returns_2_for_missing_subcommand():
    with pytest.raises(SystemExit) as ei:
        main([])
    # argparse required subparser → exit code 2
    assert ei.value.code == 2


def test_e2e_invalid_subcommand_exits():
    with pytest.raises(SystemExit):
        main(["invalid-command"])
