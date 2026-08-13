"""evaluation/cli.py 第九十五轮 edges 测试（Round 673）。

补强 edges75 未触及的角度（第五十一批）。

新角度：
- _build_parser 多场景（prog / description / 3 subparsers / choices / type=int / default）
- _format_metric 多类型（None value / bool / float / dict 排序 / int / str / large int / 负数）
- _format_metric 边界（空 dict value / dict 含 None value）
- main run 多场景（无参数 SystemExit / 未知子命令 SystemExit / --parser 非法 / --max-chars 非 int）
- main run 完整成功路径（manifest 加载 / run_evaluation 调用 / validate_file 调用 / 打印 [OK]）
- main run 失败路径（manifest 不存在 return 2 / ManifestError return 1 / EvalSchemaError return 1 / validate_file 失败 return 1）
- main validate-report 多场景（不存在 return 2 / EvalSchemaError return 1 / FileNotFoundError return 2 / JSONDecodeError return 1 / 成功 return 0）
- main inspect-doc 多场景（不存在 / JSON 解析失败 / 顶层非 dict / 成功 / source_type 默认 / document_id 默认 / parser 默认 / counts 0）
- 模块源码补强（argparse/json/sys/Path imports / ManifestError+load_manifest/get_git_provenance/run_evaluation/EvalSchemaError+validate_file imports / sys.stdout.reconfigure / utf-8 / errors replace / file=sys.stderr / [OK]/[ERROR]/[FAIL] 标记 / return 0/1/2 / subparsers required / docstring 关键词）
- AST 结构补强（4 函数 + 顺序 / 无 ClassDef / 无 AsyncFunctionDef / 9 imports / module docstring / module top-level if reconfigure / if __main__ / _build_parser 3 add_parser + 1 add_subparsers / main ≥5 return + ≥3 if + ≥3 try / _format_metric ≥4 if + ≥4 return + JoinedStr / _run_inspect_doc 嵌套 _sort_key + ≥4 return + sorted + ≥5 print）
- forbidden tokens 第一百四十三批
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 多场景 ----------

def test_build_parser_prog_batch51():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_batch51():
    p = _build_parser()
    assert "评测 CLI" in p.description


def test_build_parser_uses_raw_description_batch51():
    p = _build_parser()
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_3_subparsers_batch51():
    p = _build_parser()
    # 找到 subparsers action
    sub_action = None
    for a in p._actions:
        if isinstance(a, argparse._SubParsersAction):
            sub_action = a
            break
    assert sub_action is not None
    assert set(sub_action.choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_subparsers_required_batch51():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])  # 无子命令


def test_build_parser_run_choices_batch51():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json", "--parser", "kreuzberg"])
    assert args.parser == "kreuzberg"


def test_build_parser_run_invalid_choice_batch51():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "m.json", "--output", "o.json", "--parser", "invalid"])


def test_build_parser_max_chars_type_int_batch51():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json", "--max-chars", "500"])
    assert args.max_chars == 500
    assert isinstance(args.max_chars, int)


def test_build_parser_max_chars_non_int_fails_batch51():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "m.json", "--output", "o.json", "--max-chars", "abc"])


def test_build_parser_default_max_chars_800_batch51():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.max_chars == 800


def test_build_parser_default_tolerance_30_batch51():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.tolerance_chars == 30


def test_build_parser_validate_report_takes_input_batch51():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"


def test_build_parser_inspect_doc_takes_input_batch51():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.input == "doc.json"


def test_build_parser_inspect_doc_default_tolerance_batch51():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


# ---------- _format_metric 多类型 ----------

def test_format_metric_none_value_batch51():
    out = _format_metric("foo", {"value": None, "reason": "no_data"})
    assert "null" in out
    assert "no_data" in out


def test_format_metric_bool_true_batch51():
    out = _format_metric("foo", {"value": True, "reason": None})
    assert "true" in out
    assert "ok" in out


def test_format_metric_bool_false_batch51():
    out = _format_metric("foo", {"value": False, "reason": None})
    assert "false" in out


def test_format_metric_float_batch51():
    out = _format_metric("foo", {"value": 0.5, "reason": None})
    assert "0.5000" in out


def test_format_metric_int_batch51():
    out = _format_metric("foo", {"value": 42, "reason": None})
    assert "42" in out


def test_format_metric_large_int_batch51():
    out = _format_metric("foo", {"value": 9999999, "reason": None})
    assert "9999999" in out


def test_format_metric_negative_float_batch51():
    out = _format_metric("foo", {"value": -0.123, "reason": None})
    assert "-0.1230" in out


def test_format_metric_dict_batch51():
    out = _format_metric("foo", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out


def test_format_metric_dict_sorted_batch51():
    """dict value 按 key 排序输出。"""
    out = _format_metric("foo", {"value": {"z": 1, "a": 2, "m": 3}, "reason": None})
    # 应该按字母序
    a_pos = out.find("a=")
    m_pos = out.find("m=")
    z_pos = out.find("z=")
    assert a_pos < m_pos < z_pos


def test_format_metric_str_value_batch51():
    """value 是字符串 → 走 default 分支。"""
    out = _format_metric("foo", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_dict_with_none_value_batch51():
    out = _format_metric("foo", {"value": {"a": None}, "reason": None})
    assert "a=None" in out


def test_format_metric_name_padding_batch51():
    """name 至少 36 字符宽。"""
    out = _format_metric("x", {"value": 1, "reason": None})
    # 取第一行内容，name 后至少有 36 字符
    assert "  x" in out
    # 验证对齐：name 占据 36 字符
    assert len(out.split("  ", 1)[1].split("1")[0]) >= 35  # 大致对齐


def test_format_metric_no_reason_uses_ok_batch51():
    """reason None → 'ok'。"""
    out = _format_metric("foo", {"value": 1, "reason": None})
    assert "ok" in out


def test_format_metric_explicit_reason_batch51():
    out = _format_metric("foo", {"value": 1, "reason": "custom_reason"})
    assert "custom_reason" in out


# ---------- main 多场景 ----------

def test_main_no_args_system_exit_batch51():
    with pytest.raises(SystemExit):
        main([])


def test_main_unknown_subcommand_system_exit_batch51():
    with pytest.raises(SystemExit):
        main(["unknown"])


def test_main_run_manifest_missing_batch51(tmp_path, capsys):
    out = tmp_path / "out.json"
    rv = main(["run", "--manifest", str(tmp_path / "nope.json"), "--output", str(out)])
    assert rv == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert "清单不存在" in captured.err


def test_main_run_manifest_load_error_batch51(tmp_path, capsys):
    """manifest 文件不是合法 JSON → ManifestError → return 1。"""
    bad_manifest = tmp_path / "bad.json"
    bad_manifest.write_text("{not json", encoding="utf-8")
    out = tmp_path / "out.json"
    rv = main(["run", "--manifest", str(bad_manifest), "--output", str(out)])
    assert rv == 1
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_main_run_success_batch51(tmp_path, capsys):
    """完整成功路径。"""
    manifest_json = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    manifest_path = tmp_path / "m.json"
    manifest_path.write_text(json.dumps(manifest_json), encoding="utf-8")
    output = tmp_path / "out.json"

    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {"status": "complete", "file_count": 0, "content_group_count": 0,
                   "pdf_count": 0, "docx_count": 0, "categories_covered": []},
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }
    with patch("evaluation.cli.run_evaluation", return_value=fake_report):
        with patch("evaluation.cli.validate_file", return_value=None):
            with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
                rv = main(["run", "--manifest", str(manifest_path), "--output", str(output)])
    assert rv == 0
    captured = capsys.readouterr()
    assert "[OK]" in captured.out


def test_main_run_run_evaluation_fails_batch51(tmp_path, capsys):
    """run_evaluation 抛 EvalSchemaError → return 1。"""
    manifest_json = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    manifest_path = tmp_path / "m.json"
    manifest_path.write_text(json.dumps(manifest_json), encoding="utf-8")
    output = tmp_path / "out.json"

    from evaluation.schema import EvalSchemaError
    with patch("evaluation.cli.run_evaluation", side_effect=EvalSchemaError("boom")):
        rv = main(["run", "--manifest", str(manifest_path), "--output", str(output)])
    assert rv == 1
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_main_run_validate_file_fails_batch51(tmp_path, capsys):
    """validate_file 失败 → return 1。"""
    manifest_json = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    manifest_path = tmp_path / "m.json"
    manifest_path.write_text(json.dumps(manifest_json), encoding="utf-8")
    output = tmp_path / "out.json"

    fake_report = {"per_doc": [], "devset": {}}
    from evaluation.schema import EvalSchemaError
    with patch("evaluation.cli.run_evaluation", return_value=fake_report):
        with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("vfail")):
            with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc"}):
                rv = main(["run", "--manifest", str(manifest_path), "--output", str(output)])
    assert rv == 1


def test_main_validate_report_missing_batch51(tmp_path, capsys):
    rv = main(["validate-report", str(tmp_path / "nope.json")])
    assert rv == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert "报告不存在" in captured.err


def test_main_validate_report_json_decode_error_batch51(tmp_path, capsys):
    f = tmp_path / "r.json"
    f.write_text("{not json", encoding="utf-8")
    rv = main(["validate-report", str(f)])
    assert rv == 1
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_main_validate_report_schema_fail_batch51(tmp_path, capsys):
    f = tmp_path / "r.json"
    f.write_text("{}", encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("vfail")):
        rv = main(["validate-report", str(f)])
    assert rv == 1
    captured = capsys.readouterr()
    assert "[FAIL]" in captured.err


def test_main_validate_report_success_batch51(tmp_path, capsys):
    f = tmp_path / "r.json"
    f.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", return_value=None):
        rv = main(["validate-report", str(f)])
    assert rv == 0
    captured = capsys.readouterr()
    assert "[OK]" in captured.out


def test_main_validate_report_file_not_found_batch51(tmp_path, capsys):
    """validate_file 抛 FileNotFoundError → return 2。"""
    f = tmp_path / "exists.json"
    f.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", side_effect=FileNotFoundError("schema missing")):
        rv = main(["validate-report", str(f)])
    assert rv == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_main_inspect_doc_missing_batch51(tmp_path, capsys):
    rv = main(["inspect-doc", str(tmp_path / "nope.json")])
    assert rv == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert "文档不存在" in captured.err


def test_main_inspect_doc_json_decode_error_batch51(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text("{not json", encoding="utf-8")
    rv = main(["inspect-doc", str(f)])
    assert rv == 1


def test_main_inspect_doc_not_dict_batch51(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text("[]", encoding="utf-8")
    rv = main(["inspect-doc", str(f)])
    assert rv == 1


def test_main_inspect_doc_success_batch51(tmp_path, capsys):
    f = tmp_path / "d.json"
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "hello"}],
        "chunks": [{"text": "hello"}],
        "document_id": "d1",
        "source_path": "samples/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
    }
    f.write_text(json.dumps(doc), encoding="utf-8")
    rv = main(["inspect-doc", str(f)])
    assert rv == 0
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_main_inspect_doc_source_type_default_batch51(tmp_path, capsys):
    """无 source_type → 默认 'unknown'。"""
    f = tmp_path / "d.json"
    f.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    rv = main(["inspect-doc", str(f)])
    assert rv == 0
    captured = capsys.readouterr()
    assert "type=unknown" in captured.out


def test_main_inspect_doc_document_id_default_batch51(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    rv = main(["inspect-doc", str(f)])
    assert rv == 0
    captured = capsys.readouterr()
    assert "document_id: ?" in captured.out


def test_main_inspect_doc_counts_zero_batch51(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    rv = main(["inspect-doc", str(f)])
    assert rv == 0
    captured = capsys.readouterr()
    assert "elements=0" in captured.out
    assert "chunks=0" in captured.out


# ---------- 模块源码补强 ----------

def test_source_contains_argparse_import_batch51():
    src = inspect.getsource(cli_mod)
    assert "import argparse" in src


def test_source_contains_json_import_batch51():
    src = inspect.getsource(cli_mod)
    assert "import json" in src


def test_source_contains_sys_import_batch51():
    src = inspect.getsource(cli_mod)
    assert "import sys" in src


def test_source_contains_path_import_batch51():
    src = inspect.getsource(cli_mod)
    assert "from pathlib import Path" in src


def test_source_imports_manifest_helpers_batch51():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_source_imports_get_git_provenance_batch51():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.report import get_git_provenance" in src


def test_source_imports_run_evaluation_batch51():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.runner import run_evaluation" in src


def test_source_imports_schema_batch51():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_source_contains_reconfigure_utf8_batch51():
    src = inspect.getsource(cli_mod)
    assert "reconfigure" in src
    assert "utf-8" in src.lower()


def test_source_contains_errors_replace_batch51():
    src = inspect.getsource(cli_mod)
    assert "errors=\"replace\"" in src


def test_source_contains_file_stderr_batch51():
    src = inspect.getsource(cli_mod)
    assert "file=sys.stderr" in src


def test_source_contains_ok_marker_batch51():
    src = inspect.getsource(cli_mod)
    assert "[OK]" in src


def test_source_contains_error_marker_batch51():
    src = inspect.getsource(cli_mod)
    assert "[ERROR]" in src


def test_source_contains_fail_marker_batch51():
    src = inspect.getsource(cli_mod)
    assert "[FAIL]" in src


def test_source_contains_return_0_batch51():
    src = inspect.getsource(cli_mod)
    assert "return 0" in src


def test_source_contains_return_1_batch51():
    src = inspect.getsource(cli_mod)
    assert "return 1" in src


def test_source_contains_return_2_batch51():
    src = inspect.getsource(cli_mod)
    assert "return 2" in src


def test_source_contains_required_true_batch51():
    src = inspect.getsource(cli_mod)
    assert "required=True" in src


def test_source_contains_docstring_run_batch51():
    src = inspect.getsource(cli_mod)
    assert "评测 CLI" in src
    assert "run" in src
    assert "validate-report" in src
    assert "inspect-doc" in src


def test_source_contains_raw_description_batch51():
    src = inspect.getsource(cli_mod)
    assert "RawDescriptionHelpFormatter" in src


# ---------- AST 结构补强 ----------

def test_ast_has_4_top_level_functions_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 4


def test_ast_function_names_order_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_build_parser", "main", "_format_metric", "_run_inspect_doc"]


def test_ast_no_class_def_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_has_9_imports_batch51():
    """__future__ + argparse + json + sys + Path + ManifestError+load_manifest + get_git_provenance + run_evaluation + EvalSchemaError+validate_file = 9。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 9


def test_ast_module_docstring_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_module_has_reconfigure_if_batch51():
    """模块顶层有 2 个 if：reconfigure 守卫 + __main__。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    ifs = [n for n in tree.body if isinstance(n, ast.If)]
    assert len(ifs) == 2


def test_ast_module_has_if_main_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    has_if_main = False
    for n in tree.body:
        if isinstance(n, ast.If):
            # 检查 test 是 compare __name__ == '__main__'
            test = n.test
            if isinstance(test, ast.Compare):
                if isinstance(test.left, ast.Name) and test.left.id == "__name__":
                    has_if_main = True
    assert has_if_main


def test_ast_build_parser_has_3_add_parser_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_parser")
    add_parser_calls = [
        c for c in ast.walk(func)
        if isinstance(c, ast.Call)
        and isinstance(c.func, ast.Attribute)
        and c.func.attr == "add_parser"
    ]
    assert len(add_parser_calls) == 3


def test_ast_build_parser_has_add_subparsers_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_parser")
    add_sub_calls = [
        c for c in ast.walk(func)
        if isinstance(c, ast.Call)
        and isinstance(c.func, ast.Attribute)
        and c.func.attr == "add_subparsers"
    ]
    assert len(add_sub_calls) == 1


def test_ast_main_has_multiple_returns_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 5


def test_ast_main_has_4_try_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    tries = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    # run 路径 3 个（load_manifest / run_evaluation / validate_file）+ validate-report 路径 1 个 = 4
    assert len(tries) == 4


def test_ast_main_has_multiple_if_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 3


def test_ast_format_metric_has_4_returns_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_format_metric")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 4  # None + bool + float + dict + default


def test_ast_format_metric_uses_joined_str_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_format_metric")
    joined = [n for n in ast.walk(func) if isinstance(n, ast.JoinedStr)]
    assert len(joined) >= 4


def test_ast_run_inspect_doc_has_nested_sort_key_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    nested_funcs = [n for n in ast.walk(func) if isinstance(n, ast.FunctionDef) and n is not func]
    assert len(nested_funcs) == 1
    assert nested_funcs[0].name == "_sort_key"


def test_ast_run_inspect_doc_has_returns_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 4


def test_ast_run_inspect_doc_uses_sorted_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    src = ast.unparse(func)
    assert "sorted(" in src


def test_ast_run_inspect_doc_uses_print_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    print_calls = [
        c for c in ast.walk(func)
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "print"
    ]
    assert len(print_calls) >= 5


def test_ast_no_global_nonlocal_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


def test_ast_no_with_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    withs = [n for n in ast.walk(tree) if isinstance(n, ast.With)]
    # inspect-doc 内有 1 个 with open
    assert len(withs) == 1


def test_ast_no_while_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))


def test_ast_no_star_import_batch51():
    tree = ast.parse(inspect.getsource(cli_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


def test_ast_main_has_sys_exit_via_return_batch51():
    """main 直接 return int（不是 sys.exit），顶层 __main__ 调 SystemExit。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    main_func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    # 至少 5 个 return（return 0/1/2 各多次）
    returns = [n for n in ast.walk(main_func) if isinstance(n, ast.Return)]
    # 验证 return 的 value 都是 int
    int_returns = [r for r in returns if isinstance(r.value, ast.Constant) and isinstance(r.value.value, int)]
    assert len(int_returns) >= 5


# ---------- forbidden tokens 第一百四十三批 ----------

def _src() -> str:
    return inspect.getsource(cli_mod)


def test_source_no_eval_batch51():
    assert "eval(" not in _src()


def test_source_no_exec_batch51():
    assert "exec(" not in _src()


def test_source_no_compile_batch51():
    assert "compile(" not in _src()


def test_source_no_globals_batch51():
    assert "globals(" not in _src()


def test_source_no_locals_batch51():
    assert "locals(" not in _src()


def test_source_no_os_system_batch51():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch51():
    assert "subprocess" not in _src()


def test_source_no_popen_batch51():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch51():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch51():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch51():
    assert "socket" not in _src()


def test_source_no_requests_batch51():
    assert "requests" not in _src()


def test_source_no_urllib_batch51():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch51():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch51():
    assert "yield" not in _src()


def test_source_no_async_await_batch51():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch51():
    """_run_inspect_doc 1 个 with open。"""
    assert _src().count("open(") == 1
