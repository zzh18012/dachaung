"""evaluation/cli.py 第二十八轮 edges 测试（Round 326）。

重点补强 edges26 未触及的角度：
- _build_parser 行为深度补强（subparser dest / required / choices / defaults / prog）
- _format_metric 行为深度补强（更多 value 类型）
- _run_inspect_doc 行为深度补强（错误处理 / metric display）
- main 各路径错误处理补强（更多 exit code 路径 / stderr 内容）
- module source 字符串精确补强
- module source forbidden tokens 第二批
- signatures 精确补强
- 端到端集成补强
- 模块整体合理性
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import FunctionType
from typing import Any

import pytest

import evaluation.cli as m
from evaluation.cli import (
    _build_parser,
    _format_metric,
    _run_inspect_doc,
    main,
)


# ---------- _build_parser 行为深度补强 ----------


def test_build_parser_default_parser_fallback():
    """--parser 默认 fallback。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.parser == "fallback"


def test_build_parser_default_max_chars_800():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.max_chars == 800


def test_build_parser_default_tolerance_chars_30():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.tolerance_chars == 30


def test_build_parser_subparser_dest_command():
    """subparser 的 dest 是 'command'。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.command == "run"


def test_build_parser_validate_report_no_extra_args():
    """validate-report 只需 input。"""
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"
    assert args.command == "validate-report"


def test_build_parser_inspect_doc_default_tolerance():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_custom_tolerance():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "100"])
    assert args.tolerance_chars == 100


def test_build_parser_run_invalid_parser_choice():
    """parser 只能 fallback 或 kreuzberg。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run", "--manifest", "m.json", "--output", "o.json",
            "--parser", "invalid_parser",
        ])


def test_build_parser_run_parser_kreuzberg():
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json",
        "--parser", "kreuzberg",
    ])
    assert args.parser == "kreuzberg"


def test_build_parser_run_manifest_required():
    """--manifest 是 required。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "o.json"])


def test_build_parser_run_output_required():
    """--output 是 required。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "m.json"])


def test_build_parser_run_max_chars_type_int():
    """--max-chars 接受 int。"""
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json",
        "--max-chars", "1500",
    ])
    assert args.max_chars == 1500
    assert isinstance(args.max_chars, int)


def test_build_parser_run_max_chars_negative():
    """argparse 接受负数 int。"""
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json",
        "--max-chars", "-1",
    ])
    assert args.max_chars == -1


def test_build_parser_run_max_chars_string_fails():
    """--max-chars 非数字 → SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run", "--manifest", "m.json", "--output", "o.json",
            "--max-chars", "abc",
        ])


def test_build_parser_no_subcommand_fails():
    """无 subcommand → SystemExit（required=True）。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_parser_unknown_subcommand_fails():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["unknown-cmd"])


def test_build_parser_help_does_not_raise_attribute():
    """--help 触发 SystemExit 但不应抛 AttributeError。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["--help"])


def test_build_parser_run_unknown_arg_fails():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run", "--manifest", "m.json", "--output", "o.json",
            "--unknown", "x",
        ])


# ---------- _format_metric 行为深度补强 ----------


def test_format_metric_with_int_value():
    """int value 走 fallback 路径。"""
    out = _format_metric("count", {"value": 42, "reason": None})
    assert "42" in out
    assert "ok" in out


def test_format_metric_with_negative_int():
    out = _format_metric("neg", {"value": -5, "reason": None})
    assert "-5" in out


def test_format_metric_with_zero_int():
    out = _format_metric("zero", {"value": 0, "reason": None})
    # 0 不是 None 也不是 bool/float/dict → fallback
    assert " 0 " in out or out.endswith(" 0  (ok)")


def test_format_metric_with_zero_float():
    out = _format_metric("zero", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_with_one_dot_zero_float():
    out = _format_metric("f", {"value": 1.0, "reason": None})
    assert "1.0000" in out


def test_format_metric_with_negative_float():
    out = _format_metric("neg", {"value": -0.5, "reason": None})
    assert "-0.5000" in out


def test_format_metric_with_huge_float():
    out = _format_metric("big", {"value": 1e10, "reason": None})
    assert "10000000000.0000" in out


def test_format_metric_with_tiny_float():
    out = _format_metric("small", {"value": 0.0001, "reason": None})
    assert "0.0001" in out


def test_format_metric_with_empty_dict_value():
    out = _format_metric("empty", {"value": {}, "reason": None})
    # 空 dict → items 是空字符串
    assert "empty" in out
    assert "ok" in out


def test_format_metric_with_dict_one_key():
    out = _format_metric("d", {"value": {"x": 1}, "reason": None})
    assert "x=1" in out


def test_format_metric_with_dict_multi_keys_sorted():
    """dict value 按 key 排序。"""
    out = _format_metric("d", {"value": {"b": 2, "a": 1, "c": 3}, "reason": None})
    # 应该按 a, b, c 排序
    a_idx = out.index("a=1")
    b_idx = out.index("b=2")
    c_idx = out.index("c=3")
    assert a_idx < b_idx < c_idx


def test_format_metric_with_dict_value_str_value():
    """dict value 是字符串也能渲染。"""
    out = _format_metric("d", {"value": {"x": "hello"}, "reason": None})
    assert "x=hello" in out


def test_format_metric_with_dict_value_none():
    out = _format_metric("d", {"value": {"x": None}, "reason": None})
    assert "x=None" in out


def test_format_metric_with_dict_value_list():
    """dict value 是 list 用 repr 渲染。"""
    out = _format_metric("d", {"value": {"x": [1, 2]}, "reason": None})
    assert "x=[1, 2]" in out


def test_format_metric_with_string_value():
    out = _format_metric("s", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_with_list_value():
    out = _format_metric("l", {"value": [1, 2, 3], "reason": None})
    # list 走 fallback → str(value)
    assert "[1, 2, 3]" in out


def test_format_metric_with_tuple_value():
    out = _format_metric("t", {"value": (1, 2), "reason": None})
    assert "(1, 2)" in out


def test_format_metric_with_set_value():
    """set 走 fallback → str(value)。"""
    out = _format_metric("s", {"value": {1, 2, 3}, "reason": None})
    # set repr 含 {1, 2, 3}（顺序不定）
    assert "1" in out and "2" in out and "3" in out


def test_format_metric_with_unicode_value():
    out = _format_metric("u", {"value": "你好", "reason": None})
    assert "你好" in out


def test_format_metric_with_long_name_36_chars():
    """name 字段 36 字符宽度。"""
    name = "a" * 36
    out = _format_metric(name, {"value": 1, "reason": None})
    # 应该刚好 36 字符然后空格
    assert name in out


def test_format_metric_with_long_name_over_36_chars():
    """name 超过 36 字符时不截断。"""
    name = "a" * 50
    out = _format_metric(name, {"value": 1, "reason": None})
    assert name in out


def test_format_metric_returns_str():
    out = _format_metric("x", {"value": 1, "reason": None})
    assert isinstance(out, str)


def test_format_metric_starts_with_2_space_indent():
    out = _format_metric("x", {"value": 1, "reason": None})
    assert out.startswith("  ")


def test_format_metric_with_reason_falls_back_to_ok():
    """reason is None + value not None → 'ok'。"""
    out = _format_metric("x", {"value": 1, "reason": None})
    assert "(ok)" in out


def test_format_metric_with_reason_string():
    out = _format_metric("x", {"value": 1, "reason": "custom"})
    assert "(custom)" in out


def test_format_metric_with_unicode_reason():
    out = _format_metric("x", {"value": None, "reason": "失败"})
    assert "失败" in out


# ---------- _run_inspect_doc 行为深度补强 ----------


def test_run_inspect_doc_returns_0_for_valid_doc(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "hi"}],
        "chunks": [{"text": "hi", "source_element_ids": ["p1"]}],
    }), encoding="utf-8")
    args = type("Args", (), {"input": str(p), "tolerance_chars": 30})()
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "file:" in out
    assert "metrics:" in out


def test_run_inspect_doc_with_empty_doc(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    args = type("Args", (), {"input": str(p), "tolerance_chars": 30})()
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_missing_file_returns_2(tmp_path, capsys):
    p = tmp_path / "missing.json"
    args = type("Args", (), {"input": str(p), "tolerance_chars": 30})()
    rc = _run_inspect_doc(args)
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_run_inspect_doc_invalid_json_returns_1(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    args = type("Args", (), {"input": str(p), "tolerance_chars": 30})()
    rc = _run_inspect_doc(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON 解析失败" in err


def test_run_inspect_doc_array_top_level_returns_1(tmp_path, capsys):
    """JSON 顶层是 array 而非 dict。"""
    p = tmp_path / "arr.json"
    p.write_text("[]", encoding="utf-8")
    args = type("Args", (), {"input": str(p), "tolerance_chars": 30})()
    rc = _run_inspect_doc(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "不是对象" in err


def test_run_inspect_doc_with_unknown_source_type(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "unknown",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    args = type("Args", (), {"input": str(p), "tolerance_chars": 30})()
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_with_no_source_type_defaults_unknown(tmp_path, capsys):
    """source_type 缺失 → 默认 'unknown'。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = type("Args", (), {"input": str(p), "tolerance_chars": 30})()
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "type=unknown" in out


def test_run_inspect_doc_with_image_elements(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"type": "image", "element_id": "i1", "resource_path": "x.png"}],
        "chunks": [],
    }), encoding="utf-8")
    args = type("Args", (), {"input": str(p), "tolerance_chars": 30})()
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_with_pilot_chunks(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "docx",
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "hi"}],
        "chunks": [
            {"text": "hi", "source_element_ids": ["p1"]},
            {"text": "", "source_element_ids": []},
        ],
    }), encoding="utf-8")
    args = type("Args", (), {"input": str(p), "tolerance_chars": 30})()
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_with_pathlib_path(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = type("Args", (), {"input": p, "tolerance_chars": 30})()
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_displays_document_id(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "doc-001",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    args = type("Args", (), {"input": str(p), "tolerance_chars": 30})()
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "doc-001" in out


def test_run_inspect_doc_displays_parser_info(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "parser_name": "fallback",
        "parser_version": "1.0",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    args = type("Args", (), {"input": str(p), "tolerance_chars": 30})()
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "fallback" in out
    assert "1.0" in out


def test_run_inspect_doc_displays_metrics_section(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    args = type("Args", (), {"input": str(p), "tolerance_chars": 30})()
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_metrics_sorted_bool_first(tmp_path, capsys):
    """bool metric 应该排在最前。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "x"}],
        "chunks": [{"text": "x", "source_element_ids": ["p1"]}],
    }), encoding="utf-8")
    args = type("Args", (), {"input": str(p), "tolerance_chars": 30})()
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    # metrics: 之后第一个 metric 应该是 bool（pipeline_success）
    metrics_idx = out.index("metrics:")
    after = out[metrics_idx:]
    # 找第一个 metric name（非空行）
    lines = [l for l in after.splitlines() if l.strip()]
    # lines[0] 是 "metrics:"，lines[1] 是第一个 metric
    assert "pipeline_success" in lines[1]


# ---------- main 各路径错误处理补强 ----------


def test_main_run_returns_2_when_manifest_missing(tmp_path, capsys):
    out = tmp_path / "o.json"
    rc = main([
        "run", "--manifest", str(tmp_path / "no.json"),
        "--output", str(out),
    ])
    assert rc == 2
    err = capsys.readouterr().err
    assert "清单不存在" in err


def test_main_validate_report_returns_2_when_report_missing(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "no.json")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_inspect_doc_returns_2_when_doc_missing(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "no.json")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_validate_report_returns_1_when_invalid_json(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON 解析失败" in err


def test_main_inspect_doc_returns_1_when_invalid_json(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON 解析失败" in err


def test_main_inspect_doc_returns_1_when_array_top_level(tmp_path, capsys):
    p = tmp_path / "arr.json"
    p.write_text("[]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_returns_0_for_valid_doc(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_with_custom_tolerance(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "100"])
    assert rc == 0


def test_main_run_with_invalid_manifest_returns_1(tmp_path, capsys):
    """manifest invalid → ManifestError → return 1。"""
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    out = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(bad), "--output", str(out)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_run_full_cycle_with_minimal_manifest(tmp_path, capsys):
    """完整 run cycle → return 0。"""
    samples = tmp_path / "samples"
    samples.mkdir()
    (samples / "x.pdf").write_text("", encoding="utf-8")
    manifest_p = tmp_path / "m.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(manifest_p), "--output", str(out)])
    assert rc == 0
    assert out.is_file()
    captured = capsys.readouterr()
    assert "[OK]" in captured.out


def test_main_run_with_unknown_subcommand_exits_2(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["unknown-cmd"])
    assert ei.value.code == 2


def test_main_run_no_subcommand_exits_2(capsys):
    with pytest.raises(SystemExit) as ei:
        main([])
    assert ei.value.code == 2


def test_main_run_with_str_path_to_pathlib():
    """main 接受 str argv，内部转 Path。"""
    # 仅验证不抛 TypeError
    rc = main(["validate-report", "/nonexistent/path/no.json"])
    assert rc == 2


def test_main_run_with_pathlib_path_in_argv():
    """argv 元素是 str（不能是 Path）。"""
    # argparse 要求 argv 是 list[str]


def test_main_returns_int_for_run_path(tmp_path, capsys):
    """main 总返回 int。"""
    rc = main(["validate-report", str(tmp_path / "no.json")])
    assert isinstance(rc, int)


def test_main_returns_int_for_inspect_doc(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "no.json")])
    assert isinstance(rc, int)


# ---------- module source forbidden tokens 第二批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import copy",
        "import pprint",
        "import csv",
        "import xml",
        "import configparser",
        "import inspect",
        "import dis",
        "import traceback",
        "import warnings",
        "import weakref",
        "import gc",
        "import struct",
        "import codecs",
        "import unicodedata",
        "import string",
        "import textwrap",
        "import difflib",
        "import decimal",
        "import fractions",
        "import statistics",
        "import array",
        "import queue",
        "import types",
        "import math",
        "import collections.abc",
        "import dataclasses",
        "import abc",
        "import re",
        "import hashlib",
        "import secrets",
        "import uuid",
        "import time",
    ],
)
def test_module_source_forbidden_tokens_second_batch(token):
    src = inspect.getsource(m)
    assert token not in src


# ---------- module source 字符串精确补强 ----------


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


def test_module_source_has_evaluation_imports():
    src = inspect.getsource(m)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src
    assert "from evaluation.report import get_git_provenance" in src
    assert "from evaluation.runner import run_evaluation" in src
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_module_source_has_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' in src
    assert "raise SystemExit(main())" in src


def test_module_source_has_sys_stdout_reconfigure():
    src = inspect.getsource(m)
    assert "sys.stdout.reconfigure" in src
    assert "sys.stderr.reconfigure" in src


def test_module_source_has_try_except_for_reconfigure():
    """reconfigure 包在 try/except 里（兼容非 Windows）。"""
    src = inspect.getsource(m)
    assert "except (AttributeError, OSError):" in src


def test_module_source_no_yield():
    src = inspect.getsource(m)
    assert "yield" not in src


def test_module_source_no_global():
    src = inspect.getsource(m)
    assert "\nglobal " not in src


def test_module_source_no_async():
    src = inspect.getsource(m)
    assert "async def" not in src


def test_module_source_no_class():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class: {line}")


def test_module_source_no_decorators():
    src = inspect.getsource(m)
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("@"):
            pytest.fail(f"Found decorator: {stripped}")


def test_module_source_no_lambda_in_main():
    """main 函数体不应有 lambda。"""
    src = inspect.getsource(main)
    assert "lambda" not in src


def test_module_source_has_docstring_mentions_run():
    src = inspect.getsource(m)
    assert "run" in src


def test_module_source_has_docstring_mentions_validate_report():
    src = inspect.getsource(m)
    assert "validate-report" in src


def test_module_source_has_docstring_mentions_inspect_doc():
    src = inspect.getsource(m)
    assert "inspect-doc" in src


# ---------- signatures 精确补强 ----------


def test_main_signature():
    sig = inspect.signature(main)
    params = list(sig.parameters)
    assert params == ["argv"]
    assert sig.parameters["argv"].default is None
    assert sig.parameters["argv"].annotation == "list[str] | None"
    assert sig.return_annotation == "int"


def test_build_parser_signature():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0
    assert sig.return_annotation == "argparse.ArgumentParser"


def test_format_metric_signature():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters)
    assert params == ["name", "metric"]
    assert sig.parameters["name"].annotation == "str"
    assert sig.parameters["metric"].annotation == "dict"
    assert sig.return_annotation == "str"


def test_run_inspect_doc_signature():
    sig = inspect.signature(_run_inspect_doc)
    params = list(sig.parameters)
    assert params == ["args"]
    assert sig.return_annotation == "int"


def test_main_param_kind():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_build_parser_no_params():
    sig = inspect.signature(_build_parser)
    for p in sig.parameters.values():
        pytest.fail(f"Should have no params: {p}")


def test_namespace_main():
    assert main.__module__ == "evaluation.cli"


def test_namespace_build_parser():
    assert _build_parser.__module__ == "evaluation.cli"


def test_namespace_format_metric():
    assert _format_metric.__module__ == "evaluation.cli"


def test_namespace_run_inspect_doc():
    assert _run_inspect_doc.__module__ == "evaluation.cli"


def test_namespace_module():
    assert m.__name__ == "evaluation.cli"


# ---------- 模块整体合理性 ----------


def test_module_no_all_attribute():
    """cli.py 没定义 __all__。"""
    assert not hasattr(m, "__all__")


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
        and getattr(m, n).__module__ == "evaluation.cli"
    ]
    assert set(private) == {"_build_parser", "_format_metric", "_run_inspect_doc"}


def test_module_no_class():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class: {line}")


# ---------- 端到端集成补强 ----------


def test_e2e_run_then_validate_report_cycle(tmp_path, capsys):
    """完整 run → validate-report 循环。"""
    manifest_p = tmp_path / "m.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(manifest_p), "--output", str(out)])
    assert rc == 0
    rc2 = main(["validate-report", str(out)])
    assert rc2 == 0


def test_e2e_inspect_doc_on_pipeline_output(tmp_path, capsys):
    """inspect-doc 一个完整文档 JSON。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "docx",
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "title",
             "source_locator": {"paragraph_index": 0}},
            {"type": "paragraph", "element_id": "p1", "content": "body",
             "source_locator": {"paragraph_index": 1}},
        ],
        "chunks": [
            {"text": "title", "source_element_ids": ["h1"]},
            {"text": "body", "source_element_ids": ["p1"]},
        ],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "docx" in out  # source_type 显示
    assert "metrics:" in out
    # elements 数量正确显示
    assert "elements=2" in out
    assert "chunks=2" in out


def test_e2e_validate_report_on_invalid_report(tmp_path, capsys):
    """validate-report 一个无效报告 JSON。"""
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"some": "stuff"}), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err


def test_e2e_run_with_full_features(tmp_path, capsys):
    """run 含 documents + expected_failures。"""
    samples = tmp_path / "samples"
    samples.mkdir()
    (samples / "x.pdf").write_text("", encoding="utf-8")
    (samples / "bad.txt").write_text("", encoding="utf-8")
    manifest_p = tmp_path / "m.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "x", "path": "samples/x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [
            {"doc_id": "bad", "path": "samples/bad.txt",
             "expected_error_code": "unsupported_format", "source_type": "txt"}
        ],
    }), encoding="utf-8")
    out = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(manifest_p), "--output", str(out)])
    # x.pdf 是空文件 → parser 可能失败，但 rc 是 0（评测完成 ≠ 文档解析成功）
    assert rc == 0


def test_e2e_inspect_doc_with_image_resource(tmp_path, capsys):
    """inspect-doc 含 image element。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"data")
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [
            {"type": "image", "element_id": "i1", "resource_path": str(img)},
        ],
        "chunks": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_inspect_doc_stdout_contains_metrics_count(tmp_path, capsys):
    """inspect-doc stdout 含 elements 和 chunks 数量。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"type": "paragraph"}, {"type": "heading"}],
        "chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "elements=2" in out
    assert "chunks=3" in out


def test_e2e_validate_report_stdout_contains_path(tmp_path, capsys):
    """validate-report 成功 stdout 含路径。"""
    manifest_p = tmp_path / "m.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "o.json"
    main(["run", "--manifest", str(manifest_p), "--output", str(out)])
    capsys.readouterr()  # 清空
    rc = main(["validate-report", str(out)])
    assert rc == 0
    captured = capsys.readouterr()
    assert str(out) in captured.out
    assert "[OK]" in captured.out


def test_e2e_main_call_returns_int_type():
    """main 返回值类型是 int。"""
    rc = main(["validate-report", "/nonexistent"])
    assert isinstance(rc, int)
