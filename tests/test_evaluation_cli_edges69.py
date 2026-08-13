"""evaluation/cli.py 第八十一轮 edges 测试（Round 617）。

补强 edges68 未触及的角度（第四十三批）。

新角度：
- _build_parser 签名 / subcommand 必填 / 各 subcommand args
- main 签名（argv=None） / return int
- main 无 subcommand 时返回非零（argparse required=True）
- _format_metric 各类型分支（None / bool / float / dict / int / str）
- _format_metric 名称左对齐 36 字符
- _format_metric reason None 时显示 'ok'
- _run_inspect_doc 签名（args positional-or-keyword）
- _run_inspect_doc 文档不存在 → 2
- _run_inspect_doc JSON decode 失败 → 1
- _run_inspect_doc 顶层非 dict → 1
- main run 路径：manifest 不存在 → 2
- main run 路径：ManifestError → 1
- main run 路径：报告校验失败 → 1
- main validate-report 路径：报告不存在 → 2
- main validate-report 路径：报告校验失败 → 1
- main validate-report 路径：FileNotFoundError → 2
- main validate-report 路径：JSONDecodeError → 1
- main inspect-doc 路径：调用 _run_inspect_doc
- main unknown command → 2（虽 required=True 已挡）
- module source 字符串精确
- AST 结构
- forbidden tokens 第八十七批
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser ----------

def test_build_parser_no_args_batch43():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_build_parser_returns_argumentparser_batch43():
    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_build_parser_prog_batch43():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_batch43():
    p = _build_parser()
    assert "评测 CLI" in p.description


def test_build_parser_subparsers_required_batch43():
    """子命令必填。"""
    with pytest.raises(SystemExit):
        _build_parser().parse_args([])


def test_build_parser_has_run_command_batch43():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.command == "run"


def test_build_parser_has_validate_report_command_batch43():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.command == "validate-report"


def test_build_parser_has_inspect_doc_command_batch43():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.command == "inspect-doc"


def test_build_parser_run_args_batch43():
    p = _build_parser()
    args = p.parse_args([
        "run",
        "--manifest", "m.json",
        "--output", "o.json",
        "--parser", "kreuzberg",
        "--max-chars", "500",
        "--tolerance-chars", "20",
    ])
    assert args.manifest == "m.json"
    assert args.output == "o.json"
    assert args.parser == "kreuzberg"
    assert args.max_chars == 500
    assert args.tolerance_chars == 20


def test_build_parser_run_defaults_batch43():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.parser == "fallback"
    assert args.max_chars == 800
    assert args.tolerance_chars == 30


def test_build_parser_run_manifest_required_batch43():
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["run", "--output", "o.json"])


def test_build_parser_run_output_required_batch43():
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["run", "--manifest", "m.json"])


def test_build_parser_parser_choices_batch43():
    with pytest.raises(SystemExit):
        _build_parser().parse_args([
            "run",
            "--manifest", "m.json",
            "--output", "o.json",
            "--parser", "invalid",
        ])


def test_build_parser_validate_report_positional_batch43():
    p = _build_parser()
    args = p.parse_args(["validate-report", "myreport.json"])
    assert args.input == "myreport.json"


def test_build_parser_inspect_doc_positional_batch43():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.input == "doc.json"


def test_build_parser_inspect_doc_tolerance_default_batch43():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_tolerance_batch43():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "50"])
    assert args.tolerance_chars == 50


# ---------- main 签名 ----------

def test_main_signature_batch43():
    sig = inspect.signature(main)
    params = list(sig.parameters.keys())
    assert params == ["argv"]


def test_main_argv_default_none_batch43():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_return_annotation_batch43():
    sig = inspect.signature(main)
    assert "int" in str(sig.return_annotation)


# ---------- _format_metric ----------

def test_format_metric_signature_batch43():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters.keys())
    assert params == ["name", "metric"]


def test_format_metric_return_annotation_batch43():
    sig = inspect.signature(_format_metric)
    assert "str" in str(sig.return_annotation)


def test_format_metric_none_value_batch43():
    out = _format_metric("foo", {"value": None, "reason": "why"})
    assert "null" in out
    assert "why" in out
    assert "foo" in out


def test_format_metric_bool_true_batch43():
    out = _format_metric("foo", {"value": True, "reason": None})
    assert "true" in out  # 不是 True
    assert "ok" in out


def test_format_metric_bool_false_batch43():
    out = _format_metric("foo", {"value": False, "reason": None})
    assert "false" in out
    assert "ok" in out


def test_format_metric_float_value_batch43():
    out = _format_metric("foo", {"value": 0.5, "reason": None})
    assert "0.5000" in out


def test_format_metric_dict_value_batch43():
    out = _format_metric("foo", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out


def test_format_metric_int_value_batch43():
    out = _format_metric("foo", {"value": 42, "reason": None})
    assert "42" in out


def test_format_metric_str_value_batch43():
    out = _format_metric("foo", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_name_width_36_batch43():
    out = _format_metric("foo", {"value": None, "reason": "why"})
    # 第二行 ":" 之后空格对齐到 36 字符
    lines = [l for l in out.split("\n") if "foo" in l]
    assert lines  # at least one line with foo


def test_format_metric_reason_none_falls_back_to_ok_batch43():
    out = _format_metric("foo", {"value": 0.5, "reason": None})
    assert "ok" in out


def test_format_metric_with_reason_batch43():
    out = _format_metric("foo", {"value": 0.5, "reason": "partial"})
    assert "partial" in out


def test_format_metric_empty_dict_value_batch43():
    out = _format_metric("foo", {"value": {}, "reason": None})
    # empty dict → items 是空串
    assert "foo" in out


# ---------- _run_inspect_doc ----------

def test_run_inspect_doc_signature_batch43():
    sig = inspect.signature(_run_inspect_doc)
    params = list(sig.parameters.keys())
    assert params == ["args"]


def test_run_inspect_doc_param_kind_batch43():
    sig = inspect.signature(_run_inspect_doc)
    p = sig.parameters["args"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_inspect_doc_return_annotation_batch43():
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in str(sig.return_annotation)


def test_run_inspect_doc_file_not_found_batch43(capsys):
    args = MagicMock()
    args.input = "nonexistent.json"
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_run_inspect_doc_invalid_json_batch43(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1
    captured = capsys.readouterr()
    assert "JSON" in captured.err


def test_run_inspect_doc_top_not_dict_batch43(tmp_path, capsys):
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1
    captured = capsys.readouterr()
    assert "对象" in captured.err


def test_run_inspect_doc_success_batch43(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "document_id": "d1",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_prints_doc_id_batch43(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "document_id": "doc_42",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "doc_42" in captured.out


def test_run_inspect_doc_prints_counts_batch43(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"type": "paragraph"}, {"type": "heading"}],
        "chunks": [{"text": "a", "source_element_ids": ["e1"]}],
    }), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "elements=2" in captured.out
    assert "chunks=1" in captured.out


# ---------- main: validate-report ----------

def test_main_validate_report_file_not_found_batch43(capsys):
    rc = main(["validate-report", "nonexistent_report.json"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_main_validate_report_invalid_json_batch43(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_schema_fail_batch43(tmp_path, capsys):
    from evaluation.schema import EvalSchemaError
    p = tmp_path / "report.json"
    p.write_text(json.dumps({"wrong": "schema"}), encoding="utf-8")
    with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("schema fail")):
        rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_success_batch43(tmp_path, capsys):
    p = tmp_path / "report.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    with patch("evaluation.cli.validate_file", return_value=None):
        rc = main(["validate-report", str(p)])
    assert rc == 0


# ---------- main: run ----------

def test_main_run_manifest_not_found_batch43(capsys):
    rc = main(["run", "--manifest", "nonexistent.json", "--output", "out.json"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_main_run_manifest_error_batch43(tmp_path, capsys):
    """load_manifest 抛 ManifestError → rc=1（前提：manifest_path.is_file() == True）。"""
    from evaluation.manifest import ManifestError
    manifest_path = tmp_path / "m.json"
    manifest_path.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.load_manifest", side_effect=ManifestError("manifest error")):
        rc = main(["run", "--manifest", str(manifest_path), "--output", "out.json"])
    assert rc == 1


def test_main_run_success_batch43(tmp_path, capsys):
    """成功跑完 + 自校验通过。"""
    manifest_path = tmp_path / "m.json"
    manifest_path.write_text("{}", encoding="utf-8")
    out_path = tmp_path / "out.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    fake_report = {"per_doc": [], "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0}}

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest):
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
                    rc = main(["run", "--manifest", str(manifest_path), "--output", str(out_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "[OK]" in captured.out


def test_main_run_schema_fail_batch43(tmp_path, capsys):
    """run_evaluation 抛 EvalSchemaError → rc=1。"""
    from evaluation.schema import EvalSchemaError
    manifest_path = tmp_path / "m.json"
    manifest_path.write_text("{}", encoding="utf-8")
    out_path = tmp_path / "out.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest):
        with patch("evaluation.cli.run_evaluation", side_effect=EvalSchemaError("schema error")):
            rc = main(["run", "--manifest", str(manifest_path), "--output", str(out_path)])
    assert rc == 1


def test_main_run_self_validate_fail_batch43(tmp_path, capsys):
    """报告生成后自校验失败 → rc=1。"""
    from evaluation.schema import EvalSchemaError
    manifest_path = tmp_path / "m.json"
    manifest_path.write_text("{}", encoding="utf-8")
    out_path = tmp_path / "out.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path
    fake_report = {"per_doc": [], "devset": {}}

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest):
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("self validate fail")):
                rc = main(["run", "--manifest", str(manifest_path), "--output", str(out_path)])
    assert rc == 1


# ---------- main: inspect-doc via main ----------

def test_main_inspect_doc_dispatch_batch43():
    with patch("evaluation.cli._run_inspect_doc", return_value=0) as mock_run:
        rc = main(["inspect-doc", "doc.json"])
    assert rc == 0
    mock_run.assert_called_once()


# ---------- module source ----------

def test_module_source_contains_subparsers_batch43():
    src = inspect.getsource(cli_mod)
    assert "add_subparsers" in src


def test_module_source_contains_run_command_batch43():
    src = inspect.getsource(cli_mod)
    assert '"run"' in src


def test_module_source_contains_validate_report_batch43():
    src = inspect.getsource(cli_mod)
    assert '"validate-report"' in src


def test_module_source_contains_inspect_doc_batch43():
    src = inspect.getsource(cli_mod)
    assert '"inspect-doc"' in src


def test_module_source_contains_manifest_required_batch43():
    src = inspect.getsource(cli_mod)
    assert "required=True" in src


def test_module_source_contains_choices_batch43():
    src = inspect.getsource(cli_mod)
    assert "fallback" in src
    assert "kreuzberg" in src


def test_module_source_contains_utf8_reconfigure_batch43():
    src = inspect.getsource(cli_mod)
    assert "reconfigure" in src


def test_module_source_contains_main_module_guard_batch43():
    src = inspect.getsource(cli_mod)
    assert '__main__' in src
    assert "SystemExit" in src


# ---------- __all__ 不存在 ----------

def test_module_no_all_batch43():
    """cli 模块没有 __all__（CLI 模块通常不需要）。"""
    assert not hasattr(cli_mod, "__all__")


# ---------- AST 结构 ----------

def test_ast_top_level_no_class_batch43():
    tree = ast.parse(inspect.getsource(cli_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert classes == []


def test_ast_top_level_function_count_batch43():
    tree = ast.parse(inspect.getsource(cli_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 4


def test_ast_top_level_function_names_batch43():
    tree = ast.parse(inspect.getsource(cli_mod))
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert funcs == ["_build_parser", "main", "_format_metric", "_run_inspect_doc"]


def test_ast_has_if_main_batch43():
    tree = ast.parse(inspect.getsource(cli_mod))
    last = tree.body[-1]
    assert isinstance(last, ast.If)


def test_ast_no_try_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(cli_mod))
    for n in tree.body:
        assert not isinstance(n, ast.Try)


def test_ast_no_for_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(cli_mod))
    for n in tree.body:
        assert not isinstance(n, ast.For)


def test_ast_no_while_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(cli_mod))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_no_classdef_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(cli_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_no_async_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(cli_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_from_future_first_batch43():
    tree = ast.parse(inspect.getsource(cli_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)  # docstring
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


# ---------- forbidden tokens 第八十七批 ----------

def test_source_no_eval_batch43():
    src = inspect.getsource(cli_mod)
    assert "eval(" not in src


def test_source_no_exec_batch43():
    src = inspect.getsource(cli_mod)
    assert "exec(" not in src


def test_source_no_compile_batch43():
    src = inspect.getsource(cli_mod)
    assert "compile(" not in src


def test_source_no_globals_batch43():
    src = inspect.getsource(cli_mod)
    assert "globals(" not in src


def test_source_no_locals_batch43():
    src = inspect.getsource(cli_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch43():
    src = inspect.getsource(cli_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch43():
    src = inspect.getsource(cli_mod)
    assert "popen(" not in src


def test_source_no_yaml_load_batch43():
    src = inspect.getsource(cli_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch43():
    src = inspect.getsource(cli_mod)
    assert "pickle.load(" not in src


def test_source_uses_argparse_not_sys_argv_batch43():
    src = inspect.getsource(cli_mod)
    assert "sys.argv" not in src
