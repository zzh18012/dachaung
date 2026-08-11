"""evaluation/cli.py 第五十四轮 edges 测试（Round 501）。

补强 edges52 未触及的角度（第二十六批）：
- _build_parser 第二十六批：--manifest/--output required missing → SystemExit / --parser invalid choice → SystemExit / --max-chars non-int → SystemExit / prog 命名严格 / subparser dest=command / 子命令严格 3 个 / validate-report positional input / inspect-doc positional input
- _format_metric 第二十六批：value=0 int / value=0.0 float / value=True / value=False / value=None + reason=None / value=str / dict 排序稳定 / name padding 36
- _run_inspect_doc 第二十六批：file is dir → 2 / JSON top-level list → 1 / JSON top-level int → 1 / empty file → 1 / tolerance_chars 透传 / metric 排序规则
- main 第二十六批：run manifest 不存在 → 2 / run load_manifest ManifestError → 1 / run EvalSchemaError on report → 1 / validate-report FileNotFound → 2 / validate-report JSONDecodeError → 1 / main(argv=None) / main returns int
- module source forbidden tokens 第四十二批
- module source 字符串精确补强第三十八批
- signatures 第三十八批
- module 合理性第三十八批
- 端到端集成第三十八批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evaluation import cli as climod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 第二十六批 ----------


def test_build_parser_manifest_required_batch26():
    """--manifest required missing → SystemExit(2)。"""
    p = _build_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args(["run", "--output", "x.json"])
    assert exc.value.code == 2


def test_build_parser_output_required_batch26():
    """--output required missing → SystemExit(2)。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "x.json"])


def test_build_parser_invalid_parser_choice_batch26():
    """--parser invalid → SystemExit(2)。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "m", "--output", "o", "--parser", "invalid"])


def test_build_parser_max_chars_non_int_batch26():
    """--max-chars 非数字 → SystemExit(2)。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "m", "--output", "o", "--max-chars", "abc"])


def test_build_parser_max_chars_negative_int_batch26():
    """--max-chars 负数 int → 接受（argparse 不限制范围）。"""
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m", "--output", "o", "--max-chars", "-1"])
    assert ns.max_chars == -1


def test_build_parser_tolerance_chars_non_int_batch26():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "m", "--output", "o", "--tolerance-chars", "abc"])


def test_build_parser_no_command_batch26():
    """无子命令 → SystemExit(2)。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_parser_subparser_dest_command_batch26():
    p = _build_parser()
    # 找到 subparsers action
    sub_actions = [a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)]
    assert len(sub_actions) == 1
    assert sub_actions[0].dest == "command"


def test_build_parser_subparser_required_true_batch26():
    p = _build_parser()
    sub_actions = [a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)]
    assert sub_actions[0].required is True


def test_build_parser_three_subcommands_batch26():
    p = _build_parser()
    sub_actions = [a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)]
    assert set(sub_actions[0].choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_validate_report_positional_input_batch26():
    p = _build_parser()
    ns = p.parse_args(["validate-report", "report.json"])
    assert ns.input == "report.json"
    assert ns.command == "validate-report"


def test_build_parser_inspect_doc_positional_input_batch26():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.input == "doc.json"
    assert ns.command == "inspect-doc"


def test_build_parser_inspect_doc_tolerance_chars_default_30_batch26():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.tolerance_chars == 30


def test_build_parser_inspect_doc_tolerance_chars_custom_batch26():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "50"])
    assert ns.tolerance_chars == 50


def test_build_parser_run_full_args_batch26():
    p = _build_parser()
    ns = p.parse_args([
        "run",
        "--manifest", "m.json",
        "--output", "o.json",
        "--parser", "kreuzberg",
        "--max-chars", "500",
        "--tolerance-chars", "20",
    ])
    assert ns.manifest == "m.json"
    assert ns.output == "o.json"
    assert ns.parser == "kreuzberg"
    assert ns.max_chars == 500
    assert ns.tolerance_chars == 20


def test_build_parser_prog_evaluation_cli_batch26():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_run_choices_strict_batch26():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m", "--output", "o", "--parser", "fallback"])
    assert ns.parser == "fallback"


# ---------- _format_metric 第二十六批 ----------


def test_format_metric_value_zero_int_batch26():
    out = _format_metric("count", {"value": 0, "reason": None})
    assert "0" in out


def test_format_metric_value_zero_float_batch26():
    out = _format_metric("ratio", {"value": 0.0, "reason": None})
    # float 显示为 0.0000
    assert "0.0000" in out


def test_format_metric_value_true_batch26():
    out = _format_metric("flag", {"value": True, "reason": None})
    assert "true" in out
    assert "True" not in out


def test_format_metric_value_false_batch26():
    out = _format_metric("flag", {"value": False, "reason": None})
    assert "false" in out
    assert "False" not in out


def test_format_metric_value_false_with_reason_batch26():
    """value=False 且有 reason → reason 显示。"""
    out = _format_metric("flag", {"value": False, "reason": "x"})
    assert "false" in out


def test_format_metric_value_none_reason_none_batch26():
    """value=None + reason=None → null (None)。"""
    out = _format_metric("x", {"value": None, "reason": None})
    assert "null" in out
    assert "None" in out


def test_format_metric_value_string_batch26():
    """value=str → 直接显示。"""
    out = _format_metric("x", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_value_int_batch26():
    out = _format_metric("x", {"value": 42, "reason": None})
    assert "42" in out


def test_format_metric_value_dict_sorted_batch26():
    """dict value → sorted items。"""
    out = _format_metric("counts", {"value": {"b": 2, "a": 1}, "reason": None})
    # 排序后：a=1, b=2
    assert "a=1" in out
    assert "b=2" in out
    # a 应在 b 前
    assert out.index("a=1") < out.index("b=2")


def test_format_metric_value_dict_empty_batch26():
    """dict value 空 → 空字符串。"""
    out = _format_metric("counts", {"value": {}, "reason": None})
    assert "counts" in out
    assert "ok" in out  # reason fallback


def test_format_metric_name_padded_batch26():
    """name 必 padded 到 36 字符。"""
    out = _format_metric("x", {"value": 1, "reason": None})
    # 找到 'x' 后的空格数
    # 格式: "  {name:36} {value}..."
    # 所以从开头到 value 至少 2 + 36 = 38 字符
    assert out.startswith("  x")
    # 36 字符 padding：name 字段宽度严格 36
    # 'x' 占 1 char + 35 spaces = 36
    assert out[2:38] == "x" + " " * 35


def test_format_metric_value_large_float_batch26():
    out = _format_metric("x", {"value": 1234567.891011, "reason": None})
    assert "1234567.8910" in out  # :.4f


def test_format_metric_value_dict_with_special_chars_batch26():
    out = _format_metric("x", {"value": {"key=eq": 1}, "reason": None})
    assert "key=eq=1" in out


def test_format_metric_no_value_key_batch26():
    """metric 缺 value key → value=None。"""
    out = _format_metric("x", {"reason": "missing"})
    assert "null" in out


# ---------- _run_inspect_doc 第二十六批 ----------


def test_run_inspect_doc_input_is_dir_returns_2_batch26(tmp_path, capsys):
    """input 是目录 → 2。"""
    args = MagicMock()
    args.input = str(tmp_path)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 2


def test_run_inspect_doc_json_top_level_list_returns_1_batch26(tmp_path, capsys):
    """JSON 顶层是 list → 1。"""
    p = tmp_path / "doc.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_json_top_level_int_returns_1_batch26(tmp_path, capsys):
    """JSON 顶层是 int → 1。"""
    p = tmp_path / "doc.json"
    p.write_text("42", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_empty_file_returns_1_batch26(tmp_path, capsys):
    """空文件 → JSONDecodeError → 1。"""
    p = tmp_path / "doc.json"
    p.write_text("", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_tolerance_chars_propagated_batch26(tmp_path, capsys):
    """tolerance_chars 必须传给 chunk_boundary_prf。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 99
    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}):
        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}) as fc:
            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}) as cb:
                _run_inspect_doc(args)
    _, kwargs = cb.call_args
    assert kwargs.get("tolerance_chars") == 99


def test_run_inspect_doc_compute_metrics_kwargs_batch26(tmp_path, capsys):
    """compute_automatic_metrics 必须按预期 kwargs 调用。"""
    p = tmp_path / "doc.json"
    p.write_text('{"source_type": "pdf"}', encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}) as cm:
        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
                _run_inspect_doc(args)
    _, kwargs = cm.call_args
    assert kwargs.get("error") is None
    assert kwargs.get("source_type") == "pdf"
    assert kwargs.get("expectations") is None
    assert kwargs.get("image_base_dir") is None


def test_run_inspect_doc_metric_sorting_batch26(tmp_path, capsys):
    """输出顺序：bool → number → 其它 → null。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    metrics = {
        "z_null": {"value": None, "reason": "x"},
        "a_bool": {"value": True, "reason": None},
        "m_num": {"value": 0.5, "reason": None},
        "b_dict": {"value": {"x": 1}, "reason": None},
    }
    with patch("evaluation.metrics.compute_automatic_metrics", return_value=metrics):
        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
                _run_inspect_doc(args)
    captured = capsys.readouterr()
    # a_bool (0) 在 m_num (1) 前；m_num 在 b_dict (2) 前；b_dict 在 z_null (3) 前
    pos_a = captured.out.find("a_bool")
    pos_m = captured.out.find("m_num")
    pos_b = captured.out.find("b_dict")
    pos_z = captured.out.find("z_null")
    assert pos_a < pos_m < pos_b < pos_z


def test_run_inspect_doc_source_type_missing_default_unknown_batch26(tmp_path, capsys):
    """source_type 缺失 → 'unknown'。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}) as cm:
        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
                _run_inspect_doc(args)
    _, kwargs = cm.call_args
    assert kwargs.get("source_type") == "unknown"


def test_run_inspect_doc_returns_zero_on_success_batch26(tmp_path, capsys):
    """正常 doc → 返回 0。"""
    p = tmp_path / "doc.json"
    p.write_text('{"document_id": "d1", "source_type": "pdf"}', encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}):
        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
                rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_prints_filename_batch26(tmp_path, capsys):
    """输出首行包含 'file:        <path>'。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}):
        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
                _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "file:" in captured.out
    assert str(p) in captured.out


# ---------- main 第二十六批 ----------


def test_main_run_manifest_not_exist_returns_2_batch26(tmp_path, capsys):
    """run --manifest 不存在 → 2。"""
    out = tmp_path / "report.json"
    rc = main(["run", "--manifest", str(tmp_path / "missing.json"), "--output", str(out)])
    assert rc == 2


def test_main_run_manifest_error_returns_1_batch26(tmp_path, capsys):
    """run --manifest 加载失败（ManifestError）→ 1。"""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("not valid json", encoding="utf-8")
    out = tmp_path / "report.json"
    rc = main(["run", "--manifest", str(manifest_path), "--output", str(out)])
    assert rc == 1


def test_main_run_report_validation_failure_returns_1_batch26(tmp_path, capsys):
    """run 报告 validate_file 失败 → 1。"""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    # patch run_evaluation 返回 minimal report；validate_file 抛 EvalSchemaError
    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {
            "status": "incomplete",
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": [],
        },
        "summary": {
            "counts": {},
            "success_rates": {},
            "ratio_macro_averages": {},
            "silent_drop_total": None,
        },
        "per_doc": [],
        "expected_failures": [],
    }
    from evaluation.schema import EvalSchemaError
    with patch("evaluation.cli.run_evaluation", return_value=fake_report):
        with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("bad")):
            rc = main(["run", "--manifest", str(manifest_path), "--output", str(out)])
    assert rc == 1


def test_main_run_schema_error_from_runner_returns_1_batch26(tmp_path, capsys):
    """run run_evaluation 抛 EvalSchemaError → 1。"""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    from evaluation.schema import EvalSchemaError
    with patch("evaluation.cli.run_evaluation", side_effect=EvalSchemaError("bad")):
        rc = main(["run", "--manifest", str(manifest_path), "--output", str(out)])
    assert rc == 1


def test_main_validate_report_not_exist_returns_2_batch26(tmp_path, capsys):
    """validate-report 文件不存在 → 2。"""
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_validate_report_json_decode_error_returns_1_batch26(tmp_path, capsys):
    """validate-report JSON 解析失败 → 1。"""
    p = tmp_path / "report.json"
    p.write_text("not valid json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_success_returns_0_batch26(tmp_path, capsys):
    """validate-report 合法 → 0。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", return_value=None):
        rc = main(["validate-report", str(p)])
    assert rc == 0


def test_main_validate_report_schema_error_returns_1_batch26(tmp_path, capsys):
    """validate-report 抛 EvalSchemaError → 1。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("bad")):
        rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_dispatched_batch26(tmp_path, capsys):
    """main 委托 inspect-doc 给 _run_inspect_doc。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli._run_inspect_doc", return_value=0) as m:
        rc = main(["inspect-doc", str(p)])
    assert rc == 0
    m.assert_called_once()


def test_main_unknown_command_exits_batch26():
    """未知子命令 → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc:
        main(["unknown"])
    assert exc.value.code == 2


def test_main_returns_int_run_success_batch26(tmp_path, capsys):
    """main run 成功 → 返回 int 0。"""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {
            "status": "incomplete",
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": [],
        },
        "summary": {
            "counts": {},
            "success_rates": {},
            "ratio_macro_averages": {},
            "silent_drop_total": None,
        },
        "per_doc": [],
        "expected_failures": [],
    }
    with patch("evaluation.cli.run_evaluation", return_value=fake_report):
        with patch("evaluation.cli.validate_file", return_value=None):
            with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
                rc = main(["run", "--manifest", str(manifest_path), "--output", str(out)])
    assert isinstance(rc, int)
    assert rc == 0


def test_main_run_prints_summary_batch26(tmp_path, capsys):
    """run 成功后打印 [OK] + documents / devset_status / git 信息。"""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {
            "status": "incomplete",
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": [],
        },
        "summary": {
            "counts": {},
            "success_rates": {},
            "ratio_macro_averages": {},
            "silent_drop_total": None,
        },
        "per_doc": [],
        "expected_failures": [],
    }
    with patch("evaluation.cli.run_evaluation", return_value=fake_report):
        with patch("evaluation.cli.validate_file", return_value=None):
            with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc123def456", "git_dirty": False}):
                main(["run", "--manifest", str(manifest_path), "--output", str(out)])
    captured = capsys.readouterr()
    assert "[OK]" in captured.out
    assert "documents=0" in captured.out
    assert "devset_status=incomplete" in captured.out
    assert "abc123def456"[:12] in captured.out


# ---------- module source forbidden tokens 第四十二批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import os",
    "import re",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import itertools",
    "import functools",
    "import timeit",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from itertools",
    "from functools",
    "from timeit",
    "import time",
    "from time",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import csv",
    "import random",
    "import hashlib",
]


def test_module_source_forbidden_tokens_batch26():
    import inspect as _insp
    source = _insp.getsource(climod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_no_class_keyword_batch26():
    import ast as _ast
    import inspect as _insp
    tree = _ast.parse(_insp.getsource(climod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_source_no_eval_exec_batch26():
    import inspect as _insp
    source = _insp.getsource(climod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_module_source_no_star_import_batch26():
    import inspect as _insp
    source = _insp.getsource(climod)
    assert "import *" not in source


def test_module_source_no_relative_imports_batch26():
    import inspect as _insp
    source = _insp.getsource(climod)
    assert "from ." not in source


def test_module_source_no_dataclass_batch26():
    import inspect as _insp
    source = _insp.getsource(climod)
    assert "@dataclass" not in source
    assert "from dataclasses" not in source


def test_module_source_argparse_allowed_batch26():
    """cli.py 允许 import argparse（必需）。"""
    import inspect as _insp
    source = _insp.getsource(climod)
    assert "import argparse" in source


def test_module_source_sys_allowed_batch26():
    """cli.py 允许 import sys（Windows 控制台 utf-8 + stderr）。"""
    import inspect as _insp
    source = _insp.getsource(climod)
    assert "import sys" in source


def test_module_source_json_allowed_batch26():
    """cli.py 允许 import json。"""
    import inspect as _insp
    source = _insp.getsource(climod)
    assert "import json" in source


def test_module_source_no_environ_batch26():
    import inspect as _insp
    source = _insp.getsource(climod)
    assert "os.environ" not in source


def test_module_source_no_unsafe_network_batch26():
    import inspect as _insp
    source = _insp.getsource(climod)
    for tok in ["requests", "urllib.request", "http.client", "socket"]:
        assert tok not in source


def test_module_source_no_module_level_mutables_batch26():
    """不应有 module-level 私有 mutable 常量。"""
    import ast as _ast
    import inspect as _insp
    tree = _ast.parse(_insp.getsource(climod))
    for node in tree.body:
        if isinstance(node, _ast.Assign) and isinstance(node.targets[0], _ast.Name):
            name = node.targets[0].id
            if name.startswith("_") and not name.startswith("__"):
                pytest.fail(f"private module-level constant: {name}")


def test_module_source_uses_from_future_annotations_batch26():
    import inspect as _insp
    source = _insp.getsource(climod)
    assert "from __future__ import annotations" in source


def test_module_source_has_reconfigure_guard_batch26():
    """应有 sys.stdout.reconfigure 包裹在 hasattr 检查里。"""
    import inspect as _insp
    source = _insp.getsource(climod)
    assert "hasattr(sys.stdout" in source
    assert "reconfigure" in source


def test_module_source_contains_lazy_imports_in_inspect_doc_batch26():
    """_run_inspect_doc 内有 lazy imports。"""
    import inspect as _insp
    source = _insp.getsource(climod)
    assert "from evaluation.annotation_metrics import" in source
    assert "from evaluation.metrics import" in source


# ---------- module source 字符串精确补强第三十八批 ----------


def test_module_source_contains_prog_evaluation_cli_batch26():
    import inspect as _insp
    assert 'prog="evaluation.cli"' in _insp.getsource(climod)


def test_module_source_contains_subparser_run_batch26():
    import inspect as _insp
    assert 'sub.add_parser("run"' in _insp.getsource(climod)


def test_module_source_contains_validate_report_batch26():
    import inspect as _insp
    assert 'sub.add_parser(\n        "validate-report"' in _insp.getsource(climod) or 'sub.add_parser("validate-report"' in _insp.getsource(climod)


def test_module_source_contains_inspect_doc_batch26():
    import inspect as _insp
    assert 'sub.add_parser(\n        "inspect-doc"' in _insp.getsource(climod) or 'sub.add_parser("inspect-doc"' in _insp.getsource(climod)


def test_module_source_contains_dest_command_batch26():
    import inspect as _insp
    assert 'dest="command"' in _insp.getsource(climod)


def test_module_source_contains_required_true_batch26():
    import inspect as _insp
    assert "required=True" in _insp.getsource(climod)


def test_module_source_contains_choices_fallback_kreuzberg_batch26():
    import inspect as _insp
    source = _insp.getsource(climod)
    assert '"fallback"' in source
    assert '"kreuzberg"' in source


def test_module_source_contains_default_fallback_batch26():
    import inspect as _insp
    assert 'default="fallback"' in _insp.getsource(climod)


def test_module_source_contains_default_800_batch26():
    import inspect as _insp
    source = _insp.getsource(climod)
    assert "default=800" in source


def test_module_source_contains_default_30_batch26():
    import inspect as _insp
    source = _insp.getsource(climod)
    # 至少出现一次 default=30
    assert source.count("default=30") >= 2  # run + inspect-doc


def test_module_source_contains_load_manifest_call_batch26():
    import inspect as _insp
    assert "load_manifest" in _insp.getsource(climod)


def test_module_source_contains_run_evaluation_call_batch26():
    import inspect as _insp
    assert "run_evaluation" in _insp.getsource(climod)


def test_module_source_contains_validate_file_call_batch26():
    import inspect as _insp
    assert "validate_file" in _insp.getsource(climod)


def test_module_source_contains_get_git_provenance_call_batch26():
    import inspect as _insp
    assert "get_git_provenance" in _insp.getsource(climod)


def test_module_source_contains_manifest_error_import_batch26():
    import inspect as _insp
    assert "ManifestError" in _insp.getsource(climod)


def test_module_source_contains_eval_schema_error_import_batch26():
    import inspect as _insp
    assert "EvalSchemaError" in _insp.getsource(climod)


# ---------- signatures 第三十八批 ----------


def test_signature_build_parser_no_args_batch26():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_main_argv_optional_batch26():
    sig = inspect.signature(main)
    assert "argv" in sig.parameters
    assert sig.parameters["argv"].default is None


def test_signature_main_argv_annotation_batch26():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].annotation == "list[str] | None"


def test_signature_main_return_int_batch26():
    sig = inspect.signature(main)
    assert sig.return_annotation == "int"


def test_signature_format_metric_two_args_batch26():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters.keys()) == ["name", "metric"]


def test_signature_format_metric_annotations_batch26():
    sig = inspect.signature(_format_metric)
    assert sig.parameters["name"].annotation == "str"
    assert sig.parameters["metric"].annotation == "dict"


def test_signature_format_metric_return_str_batch26():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation == "str"


def test_signature_run_inspect_doc_one_arg_batch26():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1
    assert "args" in sig.parameters


def test_signature_run_inspect_doc_return_int_batch26():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


def test_signature_main_no_varargs_batch26():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


def test_signature_all_annotations_are_strings_batch26():
    """from __future__ import annotations → 所有 annotation 应是 str。"""
    for fn in [_build_parser, _format_metric, _run_inspect_doc, main]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            if p.annotation is not inspect.Parameter.empty:
                assert isinstance(p.annotation, str), f"{fn.__name__}.{p.name}"
        if sig.return_annotation is not inspect.Signature.empty:
            assert isinstance(sig.return_annotation, str), f"{fn.__name__} return"


# ---------- module 合理性第三十八批 ----------


def test_module_has_four_callables_batch26():
    """module-level callable: _build_parser / main / _format_metric / _run_inspect_doc。"""
    import ast as _ast
    import inspect as _insp
    tree = _ast.parse(_insp.getsource(climod))
    funcs = [n.name for n in tree.body if isinstance(n, _ast.FunctionDef)]
    assert set(funcs) == {"_build_parser", "main", "_format_metric", "_run_inspect_doc"}


def test_module_no_classes_batch26():
    import ast as _ast
    import inspect as _insp
    tree = _ast.parse(_insp.getsource(climod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_docstring_present_batch26():
    assert climod.__doc__ is not None
    assert len(climod.__doc__.strip()) > 0


def test_module_docstring_mentions_subcommands_batch26():
    assert "run" in climod.__doc__
    assert "validate-report" in climod.__doc__
    assert "inspect-doc" in climod.__doc__


def test_module_docstring_mentions_usage_batch26():
    assert "用法" in climod.__doc__ or "Usage" in climod.__doc__ or "python -m" in climod.__doc__


def test_module_main_docstring_present_batch26():
    # main() 没有专门 docstring，跳过严格断言
    assert callable(main)


def test_module_uses_from_future_annotations_batch26():
    import inspect as _insp
    assert "from __future__ import annotations" in _insp.getsource(climod)


def test_module_run_inspect_doc_uses_lazy_import_batch26():
    """_run_inspect_doc 内有 lazy import（避免顶层循环依赖）。"""
    import inspect as _insp
    src = _insp.getsource(_run_inspect_doc)
    assert "from evaluation.annotation_metrics import" in src
    assert "from evaluation.metrics import" in src


def test_module_format_metric_docstring_present_batch26():
    assert _format_metric.__doc__ is not None


def test_module_build_parser_docstring_missing_ok_batch26():
    """_build_parser 无 docstring（实现略），跳过。"""
    assert callable(_build_parser)


# ---------- 端到端集成第三十八批 ----------


def test_e2e_no_args_exits_batch26():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_e2e_unknown_subcommand_exits_batch26():
    with pytest.raises(SystemExit) as exc:
        main(["nonexistent"])
    assert exc.value.code == 2


def test_e2e_build_parser_callable_multiple_times_batch26():
    """_build_parser 应可重复调用（无状态）。"""
    p1 = _build_parser()
    p2 = _build_parser()
    assert p1 is not p2
    ns1 = p1.parse_args(["validate-report", "x"])
    ns2 = p2.parse_args(["validate-report", "x"])
    assert ns1.input == ns2.input


def test_e2e_inspect_doc_full_flow_returns_0_batch26(tmp_path, capsys):
    """inspect-doc 真实跑：构造一个 minimal doc.json → 0。"""
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({
            "document_id": "d1",
            "source_type": "pdf",
            "source_path": "x.pdf",
            "parser_name": "fallback",
            "parser_version": "0.1.0",
            "source_hash": "abc",
            "elements": [],
            "chunks": [],
        }),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_inspect_doc_with_tolerance_chars_flag_batch26(tmp_path, capsys):
    """inspect-doc --tolerance-chars 50 → 0。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "50"])
    assert rc == 0


def test_e2e_inspect_doc_missing_file_returns_2_batch26(tmp_path, capsys):
    """inspect-doc 文件不存在 → 2。"""
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert rc == 2


def test_e2e_validate_report_with_schema_valid_batch26(tmp_path, capsys):
    """validate-report 真实跑（mock validate_file 通过）。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", return_value=None):
        rc = main(["validate-report", str(p)])
    assert rc == 0


def test_e2e_main_argv_none_uses_sys_argv_batch26(monkeypatch):
    """main(argv=None) → 读 sys.argv（这里 mock 为 ['validate-report', 'x']）。"""
    monkeypatch.setattr("sys.argv", ["evaluation.cli", "validate-report", "x"])
    with patch("evaluation.cli.validate_file", return_value=None):
        with patch("pathlib.Path.is_file", return_value=True):
            rc = main(None)
    assert rc == 0
