"""evaluation/cli.py 第九十四轮 edges 测试（Round 665）。

补强 edges74 未触及的角度（第四十九批）。

新角度：
- _format_metric 更多类型（int value / large int / negative float / dict 多 key 排序 / dict 含 int+float 混合 / value 是 None 时不同 reason）
- _run_inspect_doc 完整路径（文件不存在 / JSONDecodeError / JSON 顶层不是 dict / 成功路径打印多行 / source_type 缺省 / document_id 缺省 / parser 缺省）
- main inspect-doc 多场景（成功 / 文件不存在 / JSON 解析失败 / 顶层非 dict）
- main run 多场景（manifest 文件不存在 → return 2 / 清单加载失败 → return 1 / run_evaluation EvalSchemaError → return 1 / validate_file 失败 → return 1 / 成功路径 → return 0）
- main 完整 dispatch（无参数抛 SystemExit / 未知子命令抛 SystemExit）
- _build_parser 完整（3 subcommands / prog / description / RawDescriptionHelpFormatter）
- argparse choices 验证（--parser choices 限制 / --max-chars type=int / --tolerance-chars 默认 30）
- 模块源码补强（argparse/json/sys/Path/ManifestError/load_manifest/get_git_provenance/run_evaluation/EvalSchemaError/validate_file imports / sys.stdout.reconfigure / file=sys.stderr / [OK] / [ERROR] / [FAIL] / return 0/1/2）
- AST 结构补强（4 函数 / module docstring / module top-level if reconfigure / if __main__ / 8 import / 3 add_parser / add_subparsers / main 多 return / _format_metric 多 if / _run_inspect_doc 嵌套 _sort_key）
- forbidden tokens 第一百三十五批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _format_metric 更多类型 ----------

def test_format_metric_int_value_batch49(capsys):
    out = _format_metric("count", {"value": 42, "reason": None})
    # int 走默认分支
    assert "42" in out
    assert "(ok)" in out


def test_format_metric_large_int_batch49():
    out = _format_metric("count", {"value": 1000000, "reason": None})
    assert "1000000" in out


def test_format_metric_negative_float_batch49():
    out = _format_metric("neg", {"value": -0.5, "reason": None})
    assert "-0.5000" in out


def test_format_metric_dict_with_int_and_float_batch49():
    out = _format_metric("mixed", {"value": {"a": 1, "b": 2.5}, "reason": None})
    assert "a=1" in out
    assert "b=2.5" in out


def test_format_metric_dict_sorted_by_key_batch49():
    """dict 按 key 字母排序。"""
    out = _format_metric("d", {"value": {"z": 1, "a": 2, "m": 3}, "reason": None})
    # 验证 a 出现在 z 之前
    a_pos = out.find("a=")
    z_pos = out.find("z=")
    assert a_pos < z_pos


def test_format_metric_none_value_with_reason_batch49():
    out = _format_metric("m", {"value": None, "reason": "pipeline_failed"})
    assert "null" in out
    assert "pipeline_failed" in out


def test_format_metric_none_value_no_reason_batch49():
    """reason 缺省时仍能渲染。"""
    out = _format_metric("m", {"value": None})
    assert "null" in out
    # reason 缺省 → (None)
    assert "(None)" in out


def test_format_metric_bool_true_with_reason_batch49():
    """bool True + reason None → 显示 true + (ok)。"""
    out = _format_metric("b", {"value": True, "reason": None})
    assert "true" in out
    assert "(ok)" in out


def test_format_metric_zero_int_batch49():
    """0 是 int，走默认分支。"""
    out = _format_metric("z", {"value": 0, "reason": None})
    # 0 应当出现在输出中
    assert " 0 " in out + " "  # 确保有 0 但不是其他数字


# ---------- _run_inspect_doc 完整路径 ----------

def test_run_inspect_doc_missing_file_batch49(capsys, tmp_path):
    args = MagicMock()
    args.input = str(tmp_path / "nope.json")
    args.tolerance_chars = 30
    out = _run_inspect_doc(args)
    assert out == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_run_inspect_doc_invalid_json_batch49(capsys, tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{not json", encoding="utf-8")
    args = MagicMock()
    args.input = str(f)
    args.tolerance_chars = 30
    out = _run_inspect_doc(args)
    assert out == 1
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_run_inspect_doc_top_level_not_dict_batch49(capsys, tmp_path):
    """JSON 顶层是 list → 不是 dict → return 1。"""
    f = tmp_path / "list.json"
    f.write_text("[1, 2, 3]", encoding="utf-8")
    args = MagicMock()
    args.input = str(f)
    args.tolerance_chars = 30
    out = _run_inspect_doc(args)
    assert out == 1
    captured = capsys.readouterr()
    assert "顶层" in captured.err or "对象" in captured.err


def test_run_inspect_doc_success_prints_multiple_lines_batch49(capsys, tmp_path):
    """成功路径打印多行输出。"""
    f = tmp_path / "doc.json"
    f.write_text(
        json.dumps(
            {
                "document_id": "d1",
                "source_type": "pdf",
                "source_path": "x.pdf",
                "parser_name": "fallback",
                "parser_version": "1.0",
                "elements": [],
                "chunks": [],
            }
        ),
        encoding="utf-8",
    )
    args = MagicMock()
    args.input = str(f)
    args.tolerance_chars = 30
    out = _run_inspect_doc(args)
    assert out == 0
    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")
    # 至少 5 行
    assert len(lines) >= 5
    assert "file:" in captured.out
    assert "document_id:" in captured.out
    assert "metrics:" in captured.out


def test_run_inspect_doc_source_type_default_batch49(capsys, tmp_path):
    """缺省 source_type → 默认 'unknown'。"""
    f = tmp_path / "doc.json"
    f.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock()
    args.input = str(f)
    args.tolerance_chars = 30
    out = _run_inspect_doc(args)
    assert out == 0
    captured = capsys.readouterr()
    assert "type=unknown" in captured.out


def test_run_inspect_doc_document_id_default_question_mark_batch49(capsys, tmp_path):
    """缺省 document_id → '?'。"""
    f = tmp_path / "doc.json"
    f.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock()
    args.input = str(f)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "document_id: ?" in captured.out


def test_run_inspect_doc_parser_default_question_mark_batch49(capsys, tmp_path):
    f = tmp_path / "doc.json"
    f.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock()
    args.input = str(f)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "parser:" in captured.out
    assert "?" in captured.out


def test_run_inspect_doc_counts_zero_batch49(capsys, tmp_path):
    """空 elements 和 chunks → counts 显示 0。"""
    f = tmp_path / "doc.json"
    f.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock()
    args.input = str(f)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "elements=0" in captured.out
    assert "chunks=0" in captured.out


def test_run_inspect_doc_counts_nonzero_batch49(capsys, tmp_path):
    f = tmp_path / "doc.json"
    f.write_text(
        json.dumps(
            {
                "elements": [{"type": "x"}, {"type": "y"}],
                "chunks": [{"text": "a"}],
            }
        ),
        encoding="utf-8",
    )
    args = MagicMock()
    args.input = str(f)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "elements=2" in captured.out
    assert "chunks=1" in captured.out


# ---------- main inspect-doc 多场景 ----------

def test_main_inspect_doc_success_batch49(capsys, tmp_path):
    f = tmp_path / "doc.json"
    f.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 0


def test_main_inspect_doc_missing_file_batch49(capsys, tmp_path):
    rc = main(["inspect-doc", str(tmp_path / "nope.json")])
    assert rc == 2


def test_main_inspect_doc_invalid_json_batch49(capsys, tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{x", encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 1


def test_main_inspect_doc_not_dict_batch49(capsys, tmp_path):
    f = tmp_path / "list.json"
    f.write_text("[1]", encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 1


def test_main_inspect_doc_with_tolerance_chars_batch49(capsys, tmp_path):
    """--tolerance-chars 参数透传。"""
    f = tmp_path / "doc.json"
    f.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(f), "--tolerance-chars", "50"])
    assert rc == 0


# ---------- main run 多场景 ----------

def test_main_run_manifest_missing_batch49(capsys, tmp_path):
    """manifest 文件不存在 → return 2。"""
    rc = main(
        [
            "run",
            "--manifest",
            str(tmp_path / "nope.json"),
            "--output",
            str(tmp_path / "out.json"),
        ]
    )
    assert rc == 2


def test_main_run_manifest_load_failure_batch49(capsys, tmp_path):
    """manifest JSON 解析失败 → ManifestError → return 1。"""
    bad_manifest = tmp_path / "bad.json"
    bad_manifest.write_text("{not json", encoding="utf-8")
    rc = main(
        [
            "run",
            "--manifest",
            str(bad_manifest),
            "--output",
            str(tmp_path / "out.json"),
        ]
    )
    assert rc == 1


def test_main_run_eval_schema_error_in_run_evaluation_batch49(capsys, tmp_path):
    """run_evaluation 抛 EvalSchemaError → return 1。"""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    with patch("evaluation.cli.run_evaluation", side_effect=__import__("evaluation.schema", fromlist=["EvalSchemaError"]).EvalSchemaError("bad")):
        rc = main(
            [
                "run",
                "--manifest",
                str(manifest),
                "--output",
                str(tmp_path / "out.json"),
            ]
        )
    assert rc == 1


def test_main_run_validate_file_failure_batch49(capsys, tmp_path):
    """validate_file 失败 → return 1。"""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    with patch("evaluation.cli.validate_file", side_effect=__import__("evaluation.schema", fromlist=["EvalSchemaError"]).EvalSchemaError("bad")):
        rc = main(
            [
                "run",
                "--manifest",
                str(manifest),
                "--output",
                str(tmp_path / "out.json"),
            ]
        )
    assert rc == 1


def test_main_run_success_returns_0_batch49(capsys, tmp_path):
    """成功路径 → return 0。"""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    # patch run_evaluation 和 validate_file 都成功
    fake_report = {
        "report_version": "1.1",
        "per_doc": [],
        "devset": {"status": "complete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0},
    }
    fake_manifest_obj = MagicMock()
    fake_manifest_obj.project_root = tmp_path
    with patch("evaluation.cli.run_evaluation", return_value=fake_report), \
         patch("evaluation.cli.load_manifest", return_value=fake_manifest_obj), \
         patch("evaluation.cli.validate_file", return_value=None), \
         patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc123", "git_dirty": False}):
        rc = main(
            [
                "run",
                "--manifest",
                str(manifest),
                "--output",
                str(tmp_path / "out.json"),
            ]
        )
    assert rc == 0


# ---------- main 完整 dispatch ----------

def test_main_no_args_raises_system_exit_batch49():
    """无参数 → argparse required=True 抛 SystemExit。"""
    with pytest.raises(SystemExit):
        main([])


def test_main_unknown_subcommand_raises_system_exit_batch49():
    with pytest.raises(SystemExit):
        main(["unknown"])


def test_main_run_invalid_parser_choice_raises_system_exit_batch49(tmp_path):
    """--parser 给非法值 → argparse choices 抛 SystemExit。"""
    with pytest.raises(SystemExit):
        main(
            [
                "run",
                "--manifest",
                str(tmp_path / "x.json"),
                "--output",
                str(tmp_path / "out.json"),
                "--parser",
                "invalid_parser",
            ]
        )


def test_main_run_invalid_max_chars_raises_system_exit_batch49(tmp_path):
    """--max-chars 给非 int → SystemExit。"""
    with pytest.raises(SystemExit):
        main(
            [
                "run",
                "--manifest",
                str(tmp_path / "x.json"),
                "--output",
                str(tmp_path / "out.json"),
                "--max-chars",
                "not_int",
            ]
        )


# ---------- _build_parser 完整 ----------

def test_build_parser_prog_batch49():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_batch49():
    p = _build_parser()
    assert "评测" in p.description


def test_build_parser_has_3_subparsers_batch49():
    """3 个 subcommands：run, validate-report, inspect-doc。"""
    p = _build_parser()
    # 找到 subparsers action
    sub_action = None
    for action in p._actions:
        if isinstance(action, type(p._subparsers._group_actions[0])) if hasattr(p, "_subparsers") and p._subparsers else False:
            sub_action = action
            break
    # 简单验证：parse_args(['run', '--help']) 应当不抛
    # 改用直接检查 choices
    assert p._subparsers is not None
    sub_action = p._subparsers._group_actions[0]
    assert set(sub_action.choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_run_subparser_has_5_args_batch49():
    """run 子命令有 5 个 args：--manifest --output --parser --max-chars --tolerance-chars。"""
    p = _build_parser()
    run_p = p._subparsers._group_actions[0].choices["run"]
    arg_strings = []
    for action in run_p._actions:
        arg_strings.extend(action.option_strings)
    # 至少包含这 5 个
    for opt in ["--manifest", "--output", "--parser", "--max-chars", "--tolerance-chars"]:
        assert opt in arg_strings


def test_build_parser_validate_report_subparser_has_input_batch49():
    p = _build_parser()
    val_p = p._subparsers._group_actions[0].choices["validate-report"]
    # 至少 1 个 positional arg
    has_positional = any(
        not action.option_strings and action.dest != "help"
        for action in val_p._actions
    )
    assert has_positional


def test_build_parser_inspect_doc_subparser_has_tolerance_chars_batch49():
    p = _build_parser()
    ins_p = p._subparsers._group_actions[0].choices["inspect-doc"]
    arg_strings = []
    for action in ins_p._actions:
        arg_strings.extend(action.option_strings)
    assert "--tolerance-chars" in arg_strings


# ---------- argparse choices 验证 ----------

def test_argparse_parser_choices_fallback_and_kreuzberg_batch49():
    """--parser choices 限定为 ('fallback', 'kreuzberg')。"""
    p = _build_parser()
    run_p = p._subparsers._group_actions[0].choices["run"]
    parser_action = next(a for a in run_p._actions if "--parser" in a.option_strings)
    assert set(parser_action.choices) == {"fallback", "kreuzberg"}


def test_argparse_max_chars_type_int_batch49():
    p = _build_parser()
    run_p = p._subparsers._group_actions[0].choices["run"]
    max_chars_action = next(a for a in run_p._actions if "--max-chars" in a.option_strings)
    assert max_chars_action.type is int


def test_argparse_max_chars_default_800_batch49():
    p = _build_parser()
    run_p = p._subparsers._group_actions[0].choices["run"]
    max_chars_action = next(a for a in run_p._actions if "--max-chars" in a.option_strings)
    assert max_chars_action.default == 800


def test_argparse_tolerance_chars_default_30_in_run_batch49():
    p = _build_parser()
    run_p = p._subparsers._group_actions[0].choices["run"]
    tol_action = next(a for a in run_p._actions if "--tolerance-chars" in a.option_strings)
    assert tol_action.default == 30


def test_argparse_tolerance_chars_default_30_in_inspect_doc_batch49():
    p = _build_parser()
    ins_p = p._subparsers._group_actions[0].choices["inspect-doc"]
    tol_action = next(a for a in ins_p._actions if "--tolerance-chars" in a.option_strings)
    assert tol_action.default == 30


# ---------- 模块源码补强 ----------

def test_source_contains_argparse_import_batch49():
    src = inspect.getsource(cli_mod)
    assert "import argparse" in src


def test_source_contains_json_import_batch49():
    src = inspect.getsource(cli_mod)
    assert "import json" in src


def test_source_contains_sys_import_batch49():
    src = inspect.getsource(cli_mod)
    assert "import sys" in src


def test_source_contains_path_import_batch49():
    src = inspect.getsource(cli_mod)
    assert "from pathlib import Path" in src


def test_source_contains_manifest_imports_batch49():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_source_contains_get_git_provenance_import_batch49():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.report import get_git_provenance" in src


def test_source_contains_run_evaluation_import_batch49():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.runner import run_evaluation" in src


def test_source_contains_validate_file_import_batch49():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_source_contains_reconfigure_call_batch49():
    src = inspect.getsource(cli_mod)
    assert "sys.stdout.reconfigure" in src


def test_source_contains_stderr_reconfigure_batch49():
    src = inspect.getsource(cli_mod)
    assert "sys.stderr.reconfigure" in src


def test_source_contains_utf8_encoding_batch49():
    src = inspect.getsource(cli_mod)
    assert 'encoding="utf-8"' in src


def test_source_contains_errors_replace_batch49():
    src = inspect.getsource(cli_mod)
    assert 'errors="replace"' in src


def test_source_contains_file_stderr_batch49():
    src = inspect.getsource(cli_mod)
    assert "file=sys.stderr" in src


def test_source_contains_ok_evaluation_complete_batch49():
    src = inspect.getsource(cli_mod)
    assert "[OK] 评测完成" in src


def test_source_contains_error_prefix_batch49():
    src = inspect.getsource(cli_mod)
    assert "[ERROR]" in src


def test_source_contains_fail_prefix_batch49():
    src = inspect.getsource(cli_mod)
    assert "[FAIL]" in src


def test_source_contains_manifest_required_batch49():
    src = inspect.getsource(cli_mod)
    assert '"--manifest", required=True' in src


def test_source_contains_output_required_batch49():
    src = inspect.getsource(cli_mod)
    assert '"--output", required=True' in src


def test_source_contains_return_0_batch49():
    src = inspect.getsource(cli_mod)
    assert "return 0" in src


def test_source_contains_return_1_batch49():
    src = inspect.getsource(cli_mod)
    assert "return 1" in src


def test_source_contains_return_2_batch49():
    src = inspect.getsource(cli_mod)
    assert "return 2" in src


def test_source_contains_subparsers_required_batch49():
    src = inspect.getsource(cli_mod)
    assert 'required=True' in src


def test_source_docstring_mentions_inspect_doc_batch49():
    src = inspect.getsource(cli_mod)
    assert "inspect-doc" in src


# ---------- AST 结构补强 ----------

def test_ast_has_4_top_level_functions_batch49():
    """4 个函数：_build_parser, main, _format_metric, _run_inspect_doc。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 4


def test_ast_function_names_batch49():
    tree = ast.parse(inspect.getsource(cli_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_build_parser", "main", "_format_metric", "_run_inspect_doc"]


def test_ast_no_class_def_batch49():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch49():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_module_has_docstring_batch49():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_module_has_top_level_if_reconfigure_batch49():
    """模块顶部有 `if hasattr(sys.stdout, "reconfigure")`。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    ifs = [n for n in tree.body if isinstance(n, ast.If)]
    assert len(ifs) >= 1


def test_ast_module_has_if_main_batch49():
    tree = ast.parse(inspect.getsource(cli_mod))
    src = ast.unparse(tree)
    # ast.unparse 使用单引号
    assert "if __name__ == '__main__'" in src or 'if __name__ == "__main__"' in src


def test_ast_module_has_8_imports_batch49():
    """8 个 import：__future__ + argparse + json + sys + Path + manifest + report + runner + schema = 9。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 9


def test_ast_build_parser_has_3_add_parser_calls_batch49():
    """3 个 sub.add_parser 调用。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_parser")
    add_parser_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_parser"
    ]
    assert len(add_parser_calls) == 3


def test_ast_build_parser_has_add_subparsers_batch49():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_parser")
    add_sub_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_subparsers"
    ]
    assert len(add_sub_calls) == 1


def test_ast_main_has_5_or_more_return_batch49():
    """main 至少 5 个 return。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 5


def test_ast_main_has_3_or_more_if_batch49():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    # 3 个 if args.command == + 多个内部 if
    assert len(ifs) >= 3


def test_ast_main_has_3_or_more_try_batch49():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    # run 子命令 3 个 try + validate-report 1 个 try
    assert len(trys) >= 3


def test_ast_format_metric_has_4_or_more_if_batch49():
    """_format_metric 至少 4 个 if（None/bool/float/dict/默认）。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_format_metric")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 4


def test_ast_format_metric_returns_fstring_batch49():
    """_format_metric 至少 5 个 return f-string。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_format_metric")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 5
    # 至少 1 个是 JoinedStr（f-string）
    joined = [n for n in returns if isinstance(n.value, ast.JoinedStr)]
    assert len(joined) >= 1


def test_ast_run_inspect_doc_has_nested_sort_key_batch49():
    """_run_inspect_doc 内有嵌套 _sort_key 函数。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    nested_funcs = [n for n in ast.walk(func) if isinstance(n, ast.FunctionDef)]
    assert any(nf.name == "_sort_key" for nf in nested_funcs)


def test_ast_run_inspect_doc_has_multiple_return_batch49():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 4


def test_ast_run_inspect_doc_has_for_with_sorted_batch49():
    """for name in sorted(metrics.keys(), key=_sort_key)。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    src = ast.unparse(func)
    assert "sorted(metrics.keys()" in src


def test_ast_run_inspect_doc_has_multiple_print_batch49():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    print_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"
    ]
    assert len(print_calls) >= 5


def test_ast_no_global_batch49():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, ast.Global) for n in ast.walk(tree))


def test_ast_no_nonlocal_batch49():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, ast.Nonlocal) for n in ast.walk(tree))


# ---------- forbidden tokens 第一百三十五批 ----------

def _src() -> str:
    return inspect.getsource(cli_mod)


def test_source_no_eval_batch49():
    assert "eval(" not in _src()


def test_source_no_exec_batch49():
    assert "exec(" not in _src()


def test_source_no_compile_batch49():
    assert "compile(" not in _src()


def test_source_no_globals_batch49():
    assert "globals(" not in _src()


def test_source_no_locals_batch49():
    assert "locals(" not in _src()


def test_source_no_os_system_batch49():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch49():
    assert "subprocess" not in _src()


def test_source_no_popen_batch49():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch49():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch49():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch49():
    assert "socket" not in _src()


def test_source_no_requests_batch49():
    assert "requests" not in _src()


def test_source_no_urllib_batch49():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch49():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch49():
    assert "yield" not in _src()


def test_source_open_only_in_run_inspect_doc_batch49():
    """open() 仅在 _run_inspect_doc 中调用 1 次。"""
    src = _src()
    assert src.count("open(") == 1
