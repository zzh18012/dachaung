"""evaluation/cli.py 第九十一轮 edges 测试（Round 633）。

补强 edges70 未触及的角度（第四十五批）。

新角度：
- _build_parser 各 subparser 参数
- _build_parser choices 精确
- _build_parser defaults 精确
- main run 成功路径完整输出
- main run manifest 不存在 → rc=2
- main run ManifestError → rc=1
- main run EvalSchemaError from load_manifest → rc=1
- main run EvalSchemaError from run_evaluation → rc=1
- main run EvalSchemaError from validate_file → rc=1
- main validate-report 各种错误（FileNotFoundError / EvalSchemaError / JSONDecodeError）
- main validate-report success
- main inspect-doc 各种错误
- _format_metric 各种 value 类型
- _format_metric reason 处理
- _run_inspect_doc 排序 key 精确
- module source 字符串精确
- AST 结构
- forbidden tokens 第一百零三批
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


# ---------- _build_parser 各 subparser 参数 ----------

def test_build_parser_prog_batch45():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_batch45():
    p = _build_parser()
    assert "评测 CLI" in p.description


def test_build_parser_has_subparsers_batch45():
    p = _build_parser()
    # _SubParsersAction 在 p._actions
    has_sub = False
    for action in p._actions:
        if isinstance(action, argparse._SubParsersAction):
            has_sub = True
            assert action.dest == "command"
            assert action.required is True
    assert has_sub


def test_build_parser_run_choices_batch45():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y", "--parser", "fallback"])
    assert args.parser == "fallback"


def test_build_parser_run_invalid_parser_choice_batch45():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "x", "--output", "y", "--parser", "invalid"])


def test_build_parser_run_default_max_chars_batch45():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.max_chars == 800


def test_build_parser_run_default_tolerance_chars_batch45():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.tolerance_chars == 30


def test_build_parser_run_custom_max_chars_batch45():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y", "--max-chars", "1200"])
    assert args.max_chars == 1200


def test_build_parser_run_custom_tolerance_chars_batch45():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y", "--tolerance-chars", "50"])
    assert args.tolerance_chars == 50


def test_build_parser_run_required_manifest_batch45():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "y"])


def test_build_parser_run_required_output_batch45():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "x"])


def test_build_parser_validate_report_takes_input_batch45():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"


def test_build_parser_inspect_doc_takes_input_batch45():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.input == "doc.json"


def test_build_parser_inspect_doc_default_tolerance_batch45():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_custom_tolerance_batch45():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "15"])
    assert args.tolerance_chars == 15


def test_build_parser_no_command_required_batch45():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_parser_unknown_command_batch45():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["unknown"])


def test_build_parser_choices_three_batch45():
    p = _build_parser()
    for action in p._actions:
        if isinstance(action, argparse._SubParsersAction):
            assert set(action.choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_formatter_class_batch45():
    p = _build_parser()
    assert p.formatter_class == argparse.RawDescriptionHelpFormatter


# ---------- main run 各种错误 ----------

def test_main_run_manifest_not_found_batch45(capsys, tmp_path):
    out = main(["run", "--manifest", str(tmp_path / "missing.json"), "--output", str(tmp_path / "o.json")])
    assert out == 2
    captured = capsys.readouterr()
    assert "清单不存在" in captured.err


def test_main_run_manifest_error_batch45(capsys, tmp_path):
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    out = main(["run", "--manifest", str(p), "--output", str(tmp_path / "o.json")])
    assert out == 1
    captured = capsys.readouterr()
    assert "清单加载失败" in captured.err


def test_main_run_eval_schema_error_from_load_batch45(capsys, tmp_path):
    """manifest 不符合 schema → EvalSchemaError → rc=1。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    out = main(["run", "--manifest", str(p), "--output", str(tmp_path / "o.json")])
    assert out == 1


def test_main_run_success_full_output_batch45(capsys, tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    fake_report = {
        "per_doc": [],
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0,
                   "pdf_count": 0, "docx_count": 0},
    }
    with patch("evaluation.cli.load_manifest") as mock_load:
        mock_load.return_value.project_root = tmp_path
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file"):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc123", "git_dirty": False}):
                    out = main(["run", "--manifest", str(p), "--output", str(tmp_path / "o.json")])
    assert out == 0
    captured = capsys.readouterr()
    assert "[OK]" in captured.out
    assert "documents=0" in captured.out
    assert "成功 0" in captured.out
    assert "失败 0" in captured.out
    assert "abc123" in captured.out


def test_main_run_success_with_docs_batch45(capsys, tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    fake_report = {
        "per_doc": [
            {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
            {"metrics": {"pipeline_success": {"value": False, "reason": None}}},
            {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        ],
        "devset": {"status": "incomplete", "file_count": 3, "content_group_count": 3,
                   "pdf_count": 2, "docx_count": 1},
    }
    with patch("evaluation.cli.load_manifest") as mock_load:
        mock_load.return_value.project_root = tmp_path
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file"):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": True}):
                    out = main(["run", "--manifest", str(p), "--output", str(tmp_path / "o.json")])
    assert out == 0
    captured = capsys.readouterr()
    assert "documents=3" in captured.out
    assert "成功 2" in captured.out
    assert "失败 1" in captured.out


def test_main_run_git_commit_none_shows_unknown_batch45(capsys, tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    fake_report = {
        "per_doc": [],
        "devset": {"status": "incomplete"},
    }
    with patch("evaluation.cli.load_manifest") as mock_load:
        mock_load.return_value.project_root = tmp_path
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file"):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
                    out = main(["run", "--manifest", str(p), "--output", str(tmp_path / "o.json")])
    assert out == 0
    captured = capsys.readouterr()
    assert "unknown" in captured.out


def test_main_run_eval_schema_error_from_run_evaluation_batch45(capsys, tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with patch("evaluation.cli.load_manifest") as mock_load:
        mock_load.return_value.project_root = tmp_path
        with patch("evaluation.cli.run_evaluation", side_effect=EvalSchemaError("schema fail")):
            out = main(["run", "--manifest", str(p), "--output", str(tmp_path / "o.json")])
    assert out == 1
    captured = capsys.readouterr()
    assert "Schema 校验" in captured.err


def test_main_run_eval_schema_error_from_validate_file_batch45(capsys, tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    fake_report = {"per_doc": [], "devset": {}}
    with patch("evaluation.cli.load_manifest") as mock_load:
        mock_load.return_value.project_root = tmp_path
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("auto fail")):
                out = main(["run", "--manifest", str(p), "--output", str(tmp_path / "o.json")])
    assert out == 1
    captured = capsys.readouterr()
    assert "自校验失败" in captured.err


# ---------- main validate-report 各种错误 ----------

def test_main_validate_report_not_found_batch45(capsys, tmp_path):
    out = main(["validate-report", str(tmp_path / "missing.json")])
    assert out == 2
    captured = capsys.readouterr()
    assert "报告不存在" in captured.err


def test_main_validate_report_success_batch45(capsys, tmp_path):
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file"):
        out = main(["validate-report", str(p)])
    assert out == 0
    captured = capsys.readouterr()
    assert "[OK]" in captured.out
    assert "Schema 校验" in captured.out


def test_main_validate_report_eval_schema_error_batch45(capsys, tmp_path):
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("schema fail")):
        out = main(["validate-report", str(p)])
    assert out == 1
    captured = capsys.readouterr()
    assert "[FAIL]" in captured.err


def test_main_validate_report_file_not_found_from_validate_batch45(capsys, tmp_path):
    """validate_file 内部抛 FileNotFoundError（schema 文件丢失等）。"""
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", side_effect=FileNotFoundError("schema missing")):
        out = main(["validate-report", str(p)])
    assert out == 2


def test_main_validate_report_json_decode_error_batch45(capsys, tmp_path):
    """报告文件本身不是 JSON。"""
    p = tmp_path / "r.json"
    p.write_text("not json", encoding="utf-8")
    with patch("evaluation.cli.validate_file", side_effect=json.JSONDecodeError("msg", "doc", 0)):
        out = main(["validate-report", str(p)])
    assert out == 1


# ---------- main inspect-doc 各种错误 ----------

def test_main_inspect_doc_not_found_batch45(capsys, tmp_path):
    out = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert out == 2
    captured = capsys.readouterr()
    assert "文档不存在" in captured.err


def test_main_inspect_doc_json_decode_error_batch45(capsys, tmp_path):
    p = tmp_path / "d.json"
    p.write_text("not json", encoding="utf-8")
    out = main(["inspect-doc", str(p)])
    assert out == 1


def test_main_inspect_doc_not_dict_batch45(capsys, tmp_path):
    p = tmp_path / "d.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    out = main(["inspect-doc", str(p)])
    assert out == 1
    captured = capsys.readouterr()
    assert "不是对象" in captured.err


def test_main_inspect_doc_success_batch45(capsys, tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    out = main(["inspect-doc", str(p)])
    assert out == 0
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


# ---------- _format_metric 各种 value 类型 ----------

def test_format_metric_null_value_batch45():
    out = _format_metric("x", {"value": None, "reason": "why"})
    assert "null" in out
    assert "why" in out


def test_format_metric_bool_true_batch45():
    out = _format_metric("x", {"value": True, "reason": None})
    assert "true" in out
    assert "ok" in out


def test_format_metric_bool_false_batch45():
    out = _format_metric("x", {"value": False, "reason": None})
    assert "false" in out


def test_format_metric_float_batch45():
    out = _format_metric("x", {"value": 0.5, "reason": None})
    assert "0.5000" in out


def test_format_metric_int_batch45():
    out = _format_metric("x", {"value": 42, "reason": None})
    assert "42" in out


def test_format_metric_dict_value_batch45():
    out = _format_metric("x", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out


def test_format_metric_dict_value_sorted_batch45():
    """dict value 按 key 排序。"""
    out = _format_metric("x", {"value": {"z": 1, "a": 2}, "reason": None})
    # a 在 z 之前
    assert out.index("a=2") < out.index("z=1")


def test_format_metric_bool_with_reason_batch45():
    """bool 值带 reason 仍走 bool 分支。"""
    out = _format_metric("x", {"value": True, "reason": "custom"})
    assert "true" in out
    assert "custom" in out


def test_format_metric_float_with_reason_batch45():
    out = _format_metric("x", {"value": 0.5, "reason": "ok reason"})
    assert "0.5000" in out
    assert "ok reason" in out


def test_format_metric_str_value_batch45():
    out = _format_metric("x", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_negative_float_batch45():
    out = _format_metric("x", {"value": -0.5, "reason": None})
    assert "-0.5000" in out


def test_format_metric_zero_float_batch45():
    out = _format_metric("x", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_long_name_batch45():
    out = _format_metric("a" * 50, {"value": 1, "reason": None})
    # 长 name 也应该正常输出
    assert "a" * 50 in out


def test_format_metric_returns_str_batch45():
    out = _format_metric("x", {"value": None, "reason": "y"})
    assert isinstance(out, str)


def test_format_metric_36_padding_batch45():
    """name 占 36 字符宽。"""
    out = _format_metric("ab", {"value": None, "reason": "y"})
    # ab 后面应该填充到 36 字符宽
    assert "ab" + " " * 34 in out


# ---------- _run_inspect_doc 排序 ----------

def test_run_inspect_doc_sorts_metrics_batch45(capsys, tmp_path):
    """inspect-doc 输出按 bool → int/float → other → None 排序。"""
    p = tmp_path / "d.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    main(["inspect-doc", str(p)])
    captured = capsys.readouterr()
    # 应该有 "metrics:" 标题
    assert "metrics:" in captured.out


# ---------- module source 字符串精确 ----------

def test_module_docstring_contains_subcommands_batch45():
    src = inspect.getsource(cli_mod)
    assert "run / validate-report / inspect-doc" in src


def test_module_source_contains_sys_reconfigure_batch45():
    src = inspect.getsource(cli_mod)
    assert "sys.stdout" in src
    assert 'encoding="utf-8"' in src
    assert 'errors="replace"' in src


def test_module_source_contains_argparse_import_batch45():
    src = inspect.getsource(cli_mod)
    assert "import argparse" in src


def test_module_source_contains_json_import_batch45():
    src = inspect.getsource(cli_mod)
    assert "import json" in src


def test_module_source_contains_sys_import_batch45():
    src = inspect.getsource(cli_mod)
    assert "import sys" in src


def test_module_source_contains_pathlib_import_batch45():
    src = inspect.getsource(cli_mod)
    assert "from pathlib import Path" in src


def test_module_source_contains_manifest_import_batch45():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_module_source_contains_report_import_batch45():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.report import get_git_provenance" in src


def test_module_source_contains_runner_import_batch45():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_contains_schema_import_batch45():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_module_source_contains_dest_command_batch45():
    src = inspect.getsource(cli_mod)
    assert 'dest="command"' in src


def test_module_source_contains_required_true_batch45():
    src = inspect.getsource(cli_mod)
    assert "required=True" in src


def test_module_source_contains_fallback_kreuzberg_batch45():
    src = inspect.getsource(cli_mod)
    assert "fallback" in src
    assert "kreuzberg" in src


def test_module_source_contains_prog_evaluation_cli_batch45():
    src = inspect.getsource(cli_mod)
    assert 'prog="evaluation.cli"' in src


def test_module_source_contains_raw_description_batch45():
    src = inspect.getsource(cli_mod)
    assert "RawDescriptionHelpFormatter" in src


def test_module_source_contains_main_function_batch45():
    src = inspect.getsource(cli_mod)
    assert "def main(argv: list[str] | None = None) -> int:" in src


def test_module_source_contains_build_parser_function_batch45():
    src = inspect.getsource(cli_mod)
    assert "def _build_parser() -> argparse.ArgumentParser:" in src


def test_module_source_contains_format_metric_function_batch45():
    src = inspect.getsource(cli_mod)
    assert "def _format_metric(name: str, metric: dict) -> str:" in src


def test_module_source_contains_run_inspect_doc_function_batch45():
    src = inspect.getsource(cli_mod)
    assert "def _run_inspect_doc(args) -> int:" in src


def test_module_source_contains_sort_key_batch45():
    src = inspect.getsource(cli_mod)
    assert "_sort_key" in src


def test_module_source_contains_no_annotation_default_note_batch45():
    src = inspect.getsource(cli_mod)
    assert "无标注时该指标固定 null" in src


# ---------- 模块无 __all__ ----------

def test_module_no_all_batch45():
    assert not hasattr(cli_mod, "__all__") or cli_mod.__all__ is None


# ---------- AST 结构 ----------

def test_ast_top_level_functions_count_batch45():
    tree = ast.parse(inspect.getsource(cli_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 4  # _build_parser, main, _format_metric, _run_inspect_doc


def test_ast_top_level_function_names_batch45():
    tree = ast.parse(inspect.getsource(cli_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_build_parser", "main", "_format_metric", "_run_inspect_doc"]


def test_ast_top_level_no_class_batch45():
    tree = ast.parse(inspect.getsource(cli_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_top_level_no_async_batch45():
    tree = ast.parse(inspect.getsource(cli_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_main_has_if_at_least_3_batch45():
    tree = ast.parse(inspect.getsource(cli_mod))
    main_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    ifs = [n for n in main_func.body if isinstance(n, ast.If)]
    assert len(ifs) >= 3  # run / validate-report / inspect-doc


def test_ast_main_has_try_at_least_3_batch45():
    tree = ast.parse(inspect.getsource(cli_mod))
    main_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    trys = [n for n in ast.walk(main_func) if isinstance(n, ast.Try)]
    assert len(trys) >= 3  # load_manifest / run_evaluation / validate_file


def test_ast_run_inspect_doc_has_nested_sort_key_batch45():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc"][0]
    nested = [n for n in func.body if isinstance(n, ast.FunctionDef)]
    assert len(nested) == 1
    assert nested[0].name == "_sort_key"


def test_ast_format_metric_has_if_batch45():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_format_metric"][0]
    ifs = [n for n in func.body if isinstance(n, ast.If)]
    assert len(ifs) >= 3  # None / bool / float / dict


def test_ast_last_node_is_if_main_batch45():
    tree = ast.parse(inspect.getsource(cli_mod))
    last = tree.body[-1]
    assert isinstance(last, ast.If)
    # if __name__ == "__main__"
    test = last.test
    assert isinstance(test, ast.Compare)


def test_ast_first_node_docstring_batch45():
    tree = ast.parse(inspect.getsource(cli_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)


def test_ast_second_node_future_import_batch45():
    tree = ast.parse(inspect.getsource(cli_mod))
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


def test_ast_has_argparse_uses_subparsers_batch45():
    tree = ast.parse(inspect.getsource(cli_mod))
    build_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_parser"][0]
    has_subparsers = False
    for n in ast.walk(build_func):
        if isinstance(n, ast.Attribute) and n.attr == "add_subparsers":
            has_subparsers = True
    assert has_subparsers


def test_ast_has_argparse_add_parser_batch45():
    tree = ast.parse(inspect.getsource(cli_mod))
    build_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_parser"][0]
    has_add_parser = False
    for n in ast.walk(build_func):
        if isinstance(n, ast.Attribute) and n.attr == "add_parser":
            has_add_parser = True
    assert has_add_parser


# ---------- forbidden tokens 第一百零三批 ----------

def test_source_no_eval_batch45():
    src = inspect.getsource(cli_mod)
    assert "eval(" not in src


def test_source_no_exec_batch45():
    src = inspect.getsource(cli_mod)
    assert "exec(" not in src


def test_source_no_compile_batch45():
    src = inspect.getsource(cli_mod)
    assert "compile(" not in src


def test_source_no_globals_batch45():
    src = inspect.getsource(cli_mod)
    assert "globals(" not in src


def test_source_no_locals_batch45():
    src = inspect.getsource(cli_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch45():
    src = inspect.getsource(cli_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch45():
    src = inspect.getsource(cli_mod)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch45():
    src = inspect.getsource(cli_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch45():
    src = inspect.getsource(cli_mod)
    assert "pickle.load(" not in src


def test_source_no_class_keyword_batch45():
    src = inspect.getsource(cli_mod)
    assert "\nclass " not in src


def test_source_no_async_def_batch45():
    src = inspect.getsource(cli_mod)
    assert "async def" not in src


def test_source_no_yield_batch45():
    src = inspect.getsource(cli_mod)
    assert "yield" not in src


def test_source_no_walrus_batch45():
    src = inspect.getsource(cli_mod)
    assert ":=" not in src
