"""evaluation/cli.py 第二十六轮 edges 测试（Round 314）。

重点补强 edges24 未触及的角度：
- _build_parser 行为深度补强（默认值/choices/required）
- _format_metric 分支精确（None/bool/int/float/dict/str/fallback）
- _run_inspect_doc 行为深度补强
- main run/validate-report/inspect-doc 行为深度补强
- module source forbidden tokens
- module source 字符串精确
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


# ---------- _build_parser 行为深度 ----------


def test_build_parser_returns_argument_parser():
    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_build_parser_prog_is_evaluation_cli():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_set():
    p = _build_parser()
    assert p.description is not None
    assert "评测" in p.description or "CLI" in p.description


def test_build_parser_subparsers_required_true():
    p = _build_parser()
    # 找到 _SubParsersAction
    sub_actions = [
        a for a in p._actions
        if isinstance(a, argparse._SubParsersAction)
    ]
    assert len(sub_actions) == 1
    assert sub_actions[0].required is True


def test_build_parser_subparsers_dest_command():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions
        if isinstance(a, argparse._SubParsersAction)
    ]
    assert sub_actions[0].dest == "command"


def test_build_parser_has_3_subcommands():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions
        if isinstance(a, argparse._SubParsersAction)
    ]
    assert set(sub_actions[0].choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_run_has_5_args():
    p = _build_parser()
    run_p = p._subparsers._group_actions[0].choices["run"]  # type: ignore
    option_strings = []
    for action in run_p._actions:
        if isinstance(action, argparse._StoreAction):
            for opt in action.option_strings:
                option_strings.append(opt)
    assert "--manifest" in option_strings
    assert "--output" in option_strings
    assert "--parser" in option_strings
    assert "--max-chars" in option_strings
    assert "--tolerance-chars" in option_strings


def test_build_parser_run_manifest_required():
    p = _build_parser()
    run_p = p._subparsers._group_actions[0].choices["run"]  # type: ignore
    for action in run_p._actions:
        if "--manifest" in (action.option_strings or []):
            assert action.required is True


def test_build_parser_run_output_required():
    p = _build_parser()
    run_p = p._subparsers._group_actions[0].choices["run"]  # type: ignore
    for action in run_p._actions:
        if "--output" in (action.option_strings or []):
            assert action.required is True


def test_build_parser_run_parser_default_fallback():
    p = _build_parser()
    run_p = p._subparsers._group_actions[0].choices["run"]  # type: ignore
    for action in run_p._actions:
        if "--parser" in (action.option_strings or []):
            assert action.default == "fallback"


def test_build_parser_run_parser_choices():
    p = _build_parser()
    run_p = p._subparsers._group_actions[0].choices["run"]  # type: ignore
    for action in run_p._actions:
        if "--parser" in (action.option_strings or []):
            assert set(action.choices) == {"fallback", "kreuzberg"}


def test_build_parser_run_max_chars_default_800():
    p = _build_parser()
    run_p = p._subparsers._group_actions[0].choices["run"]  # type: ignore
    for action in run_p._actions:
        if "--max-chars" in (action.option_strings or []):
            assert action.default == 800
            assert action.type is int


def test_build_parser_run_tolerance_chars_default_30():
    p = _build_parser()
    run_p = p._subparsers._group_actions[0].choices["run"]  # type: ignore
    for action in run_p._actions:
        if "--tolerance-chars" in (action.option_strings or []):
            assert action.default == 30
            assert action.type is int


def test_build_parser_validate_report_has_1_positional():
    p = _build_parser()
    val_p = p._subparsers._group_actions[0].choices["validate-report"]  # type: ignore
    positional = [
        a for a in val_p._actions
        if isinstance(a, argparse._StoreAction) and not a.option_strings
    ]
    assert len(positional) == 1
    assert positional[0].dest == "input"


def test_build_parser_inspect_doc_has_1_positional_input():
    p = _build_parser()
    ins_p = p._subparsers._group_actions[0].choices["inspect-doc"]  # type: ignore
    positional = [
        a for a in ins_p._actions
        if isinstance(a, argparse._StoreAction) and not a.option_strings
    ]
    assert any(p.dest == "input" for p in positional)


def test_build_parser_inspect_doc_has_tolerance_chars():
    p = _build_parser()
    ins_p = p._subparsers._group_actions[0].choices["inspect-doc"]  # type: ignore
    has_tol = False
    for action in ins_p._actions:
        if "--tolerance-chars" in (action.option_strings or []):
            has_tol = True
            assert action.default == 30
            assert action.type is int
    assert has_tol


# ---------- _format_metric 分支精确 ----------


def test_format_metric_none_value():
    out = _format_metric("x", {"value": None, "reason": "pipeline_failed"})
    assert "null" in out
    assert "pipeline_failed" in out
    assert "x" in out


def test_format_metric_bool_true():
    out = _format_metric("x", {"value": True, "reason": None})
    assert "true" in out
    assert "ok" in out


def test_format_metric_bool_false():
    out = _format_metric("x", {"value": False, "reason": None})
    assert "false" in out


def test_format_metric_int_value():
    """int 不在 isinstance(value, float) 分支，落到 fallback。"""
    out = _format_metric("x", {"value": 5, "reason": None})
    assert "5" in out
    assert "ok" in out


def test_format_metric_float_value():
    out = _format_metric("x", {"value": 0.5, "reason": None})
    assert "0.5000" in out


def test_format_metric_float_zero():
    out = _format_metric("x", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_float_one():
    out = _format_metric("x", {"value": 1.0, "reason": None})
    assert "1.0000" in out


def test_format_metric_dict_value():
    out = _format_metric("x", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out
    assert "ok" in out


def test_format_metric_empty_dict():
    out = _format_metric("x", {"value": {}, "reason": None})
    # 空 dict → items 为空字符串
    assert "ok" in out


def test_format_metric_dict_sorted_by_key():
    out = _format_metric("x", {"value": {"b": 2, "a": 1}, "reason": None})
    # sorted → a 在 b 前
    assert out.index("a=1") < out.index("b=2")


def test_format_metric_str_value():
    out = _format_metric("x", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_reason_fallback_to_ok():
    out = _format_metric("x", {"value": True, "reason": None})
    assert "ok" in out


def test_format_metric_reason_present():
    out = _format_metric("x", {"value": True, "reason": "custom"})
    assert "custom" in out


def test_format_metric_name_field_width_36():
    out = _format_metric("ab", {"value": True, "reason": None})
    # 至少 4 个空格缩进 + name
    assert "  ab" in out
    # name 占位 36 字符 → 后续 value 至少在 36 字符后
    name_end = out.find("true")
    assert name_end >= 36


def test_format_metric_returns_str():
    out = _format_metric("x", {"value": None, "reason": "y"})
    assert isinstance(out, str)


# ---------- _run_inspect_doc 行为深度 ----------


def test_run_inspect_doc_missing_input_returns_2(capsys, tmp_path):
    args = argparse.Namespace(input=str(tmp_path / "missing.json"), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_run_inspect_doc_invalid_json_returns_1(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON" in err or "json" in err.lower()


def test_run_inspect_doc_non_dict_returns_1(tmp_path, capsys):
    p = tmp_path / "arr.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "对象" in err or "object" in err.lower() or "dict" in err.lower()


def test_run_inspect_doc_dict_minimal_returns_0(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "file:" in out
    assert "metrics:" in out


def test_run_inspect_doc_source_type_missing(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "type=unknown" in out


def test_run_inspect_doc_prints_counts(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"type": "paragraph"}, {"type": "heading"}],
        "chunks": [{"text": "a"}],
    }), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "elements=2" in out
    assert "chunks=1" in out


def test_run_inspect_doc_prints_metrics_sorted(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "hi",
                      "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "hi", "source_element_ids": ["p1"]}],
    }), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "pipeline_success" in out
    assert "true" in out  # pipeline_success=True


def test_run_inspect_doc_prints_metric_for_null_value(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "null" in out  # 至少一个 null metric


# ---------- main run 路径行为深度 ----------


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


def test_main_run_manifest_missing_returns_2(tmp_path, capsys):
    rc = main([
        "run",
        "--manifest", str(tmp_path / "missing.json"),
        "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_run_invalid_json_returns_1(tmp_path, capsys):
    p = tmp_path / "manifest.json"
    p.write_text("{not json", encoding="utf-8")
    rc = main([
        "run",
        "--manifest", str(p),
        "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 1
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_run_schema_reject_returns_1(tmp_path, capsys):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "invalid",
        "documents": [],
    }), encoding="utf-8")
    rc = main([
        "run",
        "--manifest", str(p),
        "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 1


def test_main_run_success_returns_0(tmp_path, capsys):
    manifest = _make_minimal_manifest(tmp_path)
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(out)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "[OK]" in captured.out
    assert "documents=0" in captured.out
    assert "devset_status=incomplete" in captured.out


def test_main_run_with_parser_arg(tmp_path, capsys):
    manifest = _make_minimal_manifest(tmp_path)
    out = tmp_path / "out.json"
    rc = main([
        "run", "--manifest", str(manifest), "--output", str(out),
        "--parser", "fallback", "--max-chars", "500", "--tolerance-chars", "20",
    ])
    assert rc == 0


def test_main_run_invalid_parser_choice_rejected(tmp_path, capsys):
    manifest = _make_minimal_manifest(tmp_path)
    out = tmp_path / "out.json"
    with pytest.raises(SystemExit):
        main([
            "run", "--manifest", str(manifest), "--output", str(out),
            "--parser", "nonexistent",
        ])


# ---------- main validate-report 路径 ----------


def test_main_validate_report_missing_returns_2(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_validate_report_invalid_json_returns_1(tmp_path, capsys):
    p = tmp_path / "report.json"
    p.write_text("{not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_validate_report_invalid_content_returns_1(tmp_path, capsys):
    p = tmp_path / "report.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err


def test_main_validate_report_success(tmp_path, capsys):
    # 先用 run 生成 valid report
    manifest = _make_minimal_manifest(tmp_path)
    out = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(out)])
    capsys.readouterr()  # 清空
    rc = main(["validate-report", str(out)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "[OK]" in captured.out


# ---------- main inspect-doc 路径 ----------


def test_main_inspect_doc_missing_returns_2(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_inspect_doc_invalid_json_returns_1(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{not json", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_non_dict_returns_1(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("[1,2]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_success_returns_0(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_with_tolerance_chars(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "10"])
    assert rc == 0


# ---------- main 无 subcommand ----------


def test_main_no_subcommand_exits_with_error():
    with pytest.raises(SystemExit):
        main([])


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


# ---------- module source 必要 imports ----------


def test_module_source_has_from_future():
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_has_import_argparse():
    src = inspect.getsource(m)
    assert "import argparse" in src


def test_module_source_has_import_json():
    src = inspect.getsource(m)
    assert "import json" in src


def test_module_source_has_import_sys():
    src = inspect.getsource(m)
    assert "import sys" in src


def test_module_source_has_from_pathlib_import_path():
    src = inspect.getsource(m)
    assert "from pathlib import Path" in src


def test_module_source_has_manifest_imports():
    src = inspect.getsource(m)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_module_source_has_report_import():
    src = inspect.getsource(m)
    assert "from evaluation.report import get_git_provenance" in src


def test_module_source_has_runner_import():
    src = inspect.getsource(m)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_has_schema_import():
    src = inspect.getsource(m)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


# ---------- module source 字符串精确 ----------


def test_module_source_has_build_parser_def():
    src = inspect.getsource(m)
    assert "def _build_parser() -> argparse.ArgumentParser:" in src


def test_module_source_has_main_def():
    src = inspect.getsource(m)
    assert "def main(argv: list[str] | None = None) -> int:" in src


def test_module_source_has_format_metric_def():
    src = inspect.getsource(m)
    assert "def _format_metric(name: str, metric: dict) -> str:" in src


def test_module_source_has_run_inspect_doc_def():
    src = inspect.getsource(m)
    assert "def _run_inspect_doc(args) -> int:" in src


def test_module_source_has_argparse_argument_call():
    src = inspect.getsource(m)
    assert "argparse.ArgumentParser(" in src


def test_module_source_has_add_subparsers():
    src = inspect.getsource(m)
    assert "p.add_subparsers(dest=" in src


def test_module_source_has_3_add_parser_calls():
    src = inspect.getsource(m)
    assert 'sub.add_parser("run"' in src
    assert '"validate-report"' in src
    assert '"inspect-doc"' in src


def test_module_source_has_required_true_in_subparsers():
    src = inspect.getsource(m)
    assert "required=True" in src


def test_module_source_has_run_command_branch():
    src = inspect.getsource(m)
    assert 'if args.command == "run":' in src


def test_module_source_has_validate_report_branch():
    src = inspect.getsource(m)
    assert 'if args.command == "validate-report":' in src


def test_module_source_has_inspect_doc_branch():
    src = inspect.getsource(m)
    assert 'if args.command == "inspect-doc":' in src


def test_module_source_has_load_manifest_call():
    src = inspect.getsource(m)
    assert "load_manifest(manifest_path)" in src


def test_module_source_has_run_evaluation_call():
    src = inspect.getsource(m)
    assert "run_evaluation(" in src


def test_module_source_has_validate_file_call_in_run():
    src = inspect.getsource(m)
    assert 'validate_file(output_path, "evaluation-report.schema.json")' in src


def test_module_source_has_validate_file_call_in_validate_report():
    src = inspect.getsource(m)
    assert 'validate_file(input_path, "evaluation-report.schema.json")' in src


def test_module_source_has_get_git_provenance_call():
    src = inspect.getsource(m)
    assert "get_git_provenance(manifest.project_root)" in src


def test_module_source_has_print_ok_run():
    src = inspect.getsource(m)
    assert '"[OK] 评测完成' in src


def test_module_source_has_print_ok_validate_report():
    src = inspect.getsource(m)
    assert '"[OK]' in src
    assert "evaluation-report Schema 校验" in src


def test_module_source_has_format_metric_5_branches():
    src = inspect.getsource(m)
    assert "if value is None:" in src
    assert "isinstance(value, bool)" in src
    assert "isinstance(value, float)" in src
    assert "isinstance(value, dict)" in src


def test_module_source_has_36_width_format():
    src = inspect.getsource(m)
    assert "{name:36}" in src


def test_module_source_has_reason_or_ok():
    src = inspect.getsource(m)
    assert "reason or 'ok'" in src


def test_module_source_has_windows_reconfigure_block():
    src = inspect.getsource(m)
    assert "hasattr(sys.stdout, " in src
    assert 'sys.stdout.reconfigure(encoding="utf-8"' in src
    assert 'sys.stderr.reconfigure(encoding="utf-8"' in src


def test_module_source_has_except_attribute_error_oserror():
    src = inspect.getsource(m)
    assert "except (AttributeError, OSError):" in src


def test_module_source_has_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' in src
    assert "raise SystemExit(main())" in src


def test_module_source_has_no_class():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class definition: {line}")


def test_module_source_has_no_all_definition():
    src = inspect.getsource(m)
    assert "__all__" not in src


# ---------- signatures 精确 ----------


def test_main_signature():
    sig = inspect.signature(main)
    assert list(sig.parameters.keys()) == ["argv"]
    assert sig.parameters["argv"].default is None
    assert sig.return_annotation == "int"


def test_main_argv_annotation():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].annotation == "list[str] | None"


def test_main_no_varargs_varkw():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_build_parser_signature():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0
    assert sig.return_annotation == "argparse.ArgumentParser"


def test_format_metric_signature():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters.keys()) == ["name", "metric"]
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "str"


def test_run_inspect_doc_signature():
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters.keys()) == ["args"]
    assert sig.return_annotation == "int"


def test_main_namespace():
    assert main.__module__ == "evaluation.cli"


def test_build_parser_namespace():
    assert _build_parser.__module__ == "evaluation.cli"


def test_format_metric_namespace():
    assert _format_metric.__module__ == "evaluation.cli"


def test_run_inspect_doc_namespace():
    assert _run_inspect_doc.__module__ == "evaluation.cli"


# ---------- module 整体合理性 ----------


def test_module_has_4_module_level_functions():
    fns = [
        n for n in dir(m)
        if not n.startswith("_")
        and isinstance(getattr(m, n), FunctionType)
        and getattr(m, n).__module__ == "evaluation.cli"
    ]
    # 公开函数只有 main；私有 _build_parser / _format_metric / _run_inspect_doc
    assert fns == ["main"]


def test_module_has_3_private_functions():
    private_fns = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and isinstance(getattr(m, n), FunctionType)
    ]
    assert set(private_fns) == {"_build_parser", "_format_metric", "_run_inspect_doc"}


def test_module_has_no_class_definition():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class definition: {line}")


def test_module_has_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' in src


def test_module_has_no_all():
    assert not hasattr(m, "__all__")


def test_module_namespace_is_evaluation_cli():
    assert m.__name__ == "evaluation.cli"


# ---------- 端到端集成 ----------


def test_e2e_run_then_validate_report_cycle(tmp_path, capsys):
    manifest = _make_minimal_manifest(tmp_path)
    out = tmp_path / "out.json"
    rc1 = main(["run", "--manifest", str(manifest), "--output", str(out)])
    assert rc1 == 0
    capsys.readouterr()
    rc2 = main(["validate-report", str(out)])
    assert rc2 == 0


def test_e2e_inspect_doc_on_pipeline_output(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "document_id": "test-doc",
        "source_path": "samples/x.pdf",
        "parser_name": "fallback",
        "parser_version": "0.1.0",
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "hi",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]}},
        ],
        "chunks": [{"text": "hi", "source_element_ids": ["p1"]}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "test-doc" in out
    assert "samples/x.pdf" in out
    assert "fallback" in out
    assert "0.1.0" in out
