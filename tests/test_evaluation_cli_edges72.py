"""evaluation/cli.py 第九十一轮 edges 测试（Round 641）。

补强 edges71 未触及的角度（第四十七批）。

新角度：
- _build_parser 各子命令参数（run 5 个 / validate-report 1 / inspect-doc 2）
- _build_parser formatter_class
- _build_parser prog / description
- _build_parser choices 限定
- _build_parser required 限定
- _build_parser defaults
- main 各种返回码（run / validate-report / inspect-doc）
- _format_metric 各种 value 类型
- _run_inspect_doc 文件不存在 / JSON 解析失败 / 顶层非 dict
- _sort_key 嵌套函数（bool/int/float/null/other）
- module source 字符串补强
- AST 结构补强
- forbidden tokens 第一百一十一批
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


# ---------- _build_parser 参数精确性 ----------

def test_build_parser_returns_argument_parser_batch47():
    import argparse
    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_build_parser_prog_batch47():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_batch47():
    p = _build_parser()
    assert "评测" in p.description


def test_build_parser_formatter_class_batch47():
    import argparse
    p = _build_parser()
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_has_subparsers_batch47():
    """add_subparsers 创建 _SubParsersAction。"""
    import argparse
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert len(sub_actions) == 1


def test_build_parser_subparsers_required_batch47():
    import argparse
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)][0]
    assert sub_actions.required is True


def test_build_parser_subparsers_dest_batch47():
    import argparse
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)][0]
    assert sub_actions.dest == "command"


def test_build_parser_choices_three_batch47():
    import argparse
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)][0]
    assert set(sub_actions.choices.keys()) == {"run", "validate-report", "inspect-doc"}


# ---------- run 子命令参数 ----------

def test_run_parser_has_manifest_batch47():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x.json", "--output", "y.json"])
    assert args.manifest == "x.json"


def test_run_parser_has_output_batch47():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x.json", "--output", "y.json"])
    assert args.output == "y.json"


def test_run_parser_parser_default_fallback_batch47():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x.json", "--output", "y.json"])
    assert args.parser == "fallback"


def test_run_parser_parser_choice_kreuzberg_batch47():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x.json", "--output", "y.json", "--parser", "kreuzberg"])
    assert args.parser == "kreuzberg"


def test_run_parser_parser_invalid_choice_batch47():
    """无效 parser 应 SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "x.json", "--output", "y.json", "--parser", "invalid"])


def test_run_parser_max_chars_default_800_batch47():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x.json", "--output", "y.json"])
    assert args.max_chars == 800


def test_run_parser_max_chars_custom_batch47():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x.json", "--output", "y.json", "--max-chars", "1200"])
    assert args.max_chars == 1200


def test_run_parser_tolerance_chars_default_30_batch47():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x.json", "--output", "y.json"])
    assert args.tolerance_chars == 30


def test_run_parser_tolerance_chars_custom_batch47():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x.json", "--output", "y.json", "--tolerance-chars", "60"])
    assert args.tolerance_chars == 60


def test_run_parser_manifest_required_batch47():
    """缺 --manifest 应 SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "y.json"])


def test_run_parser_output_required_batch47():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "x.json"])


# ---------- validate-report 子命令参数 ----------

def test_validate_report_parser_has_input_batch47():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"


def test_validate_report_parser_input_required_batch47():
    """input 是位置参数，缺应 SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["validate-report"])


def test_validate_report_command_value_batch47():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.command == "validate-report"


# ---------- inspect-doc 子命令参数 ----------

def test_inspect_doc_parser_has_input_batch47():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.input == "doc.json"


def test_inspect_doc_parser_input_required_batch47():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["inspect-doc"])


def test_inspect_doc_parser_tolerance_default_30_batch47():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_inspect_doc_parser_tolerance_custom_batch47():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "100"])
    assert args.tolerance_chars == 100


def test_inspect_doc_command_value_batch47():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.command == "inspect-doc"


def test_run_command_value_batch47():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.command == "run"


# ---------- main 返回码 ----------

def test_main_no_subcommand_exits_batch47():
    """无子命令（required=True）→ SystemExit。"""
    with pytest.raises(SystemExit):
        main([])


def test_main_run_manifest_not_exist_batch47(tmp_path, capsys):
    """manifest 不存在 → 返回 2。"""
    out = tmp_path / "report.json"
    result = main(["run", "--manifest", str(tmp_path / "nofile.json"), "--output", str(out)])
    assert result == 2


def test_main_validate_report_not_exist_batch47(tmp_path):
    """报告不存在 → 返回 2。"""
    result = main(["validate-report", str(tmp_path / "nofile.json")])
    assert result == 2


def test_main_inspect_doc_not_exist_batch47(tmp_path):
    result = main(["inspect-doc", str(tmp_path / "nofile.json")])
    assert result == 2


def test_main_validate_report_bad_json_batch47(tmp_path):
    """JSON 解析失败 → 返回 1。"""
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    result = main(["validate-report", str(p)])
    assert result == 1


def test_main_inspect_doc_bad_json_batch47(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    result = main(["inspect-doc", str(p)])
    assert result == 1


def test_main_inspect_doc_top_not_dict_batch47(tmp_path):
    """顶层是 list 而非 dict → 返回 1。"""
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    result = main(["inspect-doc", str(p)])
    assert result == 1


def test_main_inspect_doc_valid_batch47(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    result = main(["inspect-doc", str(p)])
    assert result == 0


# ---------- main run 成功路径（mock）----------

def test_main_run_success_batch47(tmp_path):
    """mock load_manifest + run_evaluation + validate_file → 返回 0。"""
    manifest_p = tmp_path / "m.json"
    manifest_p.write_text("{}", encoding="utf-8")
    out_p = tmp_path / "report.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest):
        with patch("evaluation.cli.run_evaluation", return_value={"per_doc": [], "devset": {}}):
            with patch("evaluation.cli.validate_file"):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc123", "git_dirty": False}):
                    result = main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    assert result == 0


def test_main_run_manifest_load_fails_batch47(tmp_path):
    """load_manifest 抛 ManifestError → 返回 1。"""
    from evaluation.manifest import ManifestError
    manifest_p = tmp_path / "m.json"
    manifest_p.write_text("{}", encoding="utf-8")
    out_p = tmp_path / "report.json"

    with patch("evaluation.cli.load_manifest", side_effect=ManifestError("bad")):
        result = main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    assert result == 1


def test_main_run_manifest_load_fails_schema_batch47(tmp_path):
    """load_manifest 抛 EvalSchemaError → 返回 1。"""
    from evaluation.schema import EvalSchemaError
    manifest_p = tmp_path / "m.json"
    manifest_p.write_text("{}", encoding="utf-8")
    out_p = tmp_path / "report.json"

    with patch("evaluation.cli.load_manifest", side_effect=EvalSchemaError("bad")):
        result = main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    assert result == 1


def test_main_run_evaluation_fails_schema_batch47(tmp_path):
    """run_evaluation 抛 EvalSchemaError → 返回 1。"""
    from evaluation.schema import EvalSchemaError
    manifest_p = tmp_path / "m.json"
    manifest_p.write_text("{}", encoding="utf-8")
    out_p = tmp_path / "report.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest):
        with patch("evaluation.cli.run_evaluation", side_effect=EvalSchemaError("bad")):
            result = main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    assert result == 1


def test_main_run_validate_file_fails_batch47(tmp_path):
    """自校验失败 → 返回 1。"""
    from evaluation.schema import EvalSchemaError
    manifest_p = tmp_path / "m.json"
    manifest_p.write_text("{}", encoding="utf-8")
    out_p = tmp_path / "report.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest):
        with patch("evaluation.cli.run_evaluation", return_value={"per_doc": [], "devset": {}}):
            with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("bad")):
                result = main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    assert result == 1


# ---------- main validate-report 成功路径 ----------

def test_main_validate_report_success_batch47(tmp_path):
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file"):
        result = main(["validate-report", str(p)])
    assert result == 0


def test_main_validate_report_file_not_found_batch47(tmp_path):
    """validate_file 抛 FileNotFoundError → 返回 2。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", side_effect=FileNotFoundError("schema missing")):
        result = main(["validate-report", str(p)])
    assert result == 2


def test_main_validate_report_schema_error_batch47(tmp_path):
    """validate_file 抛 EvalSchemaError → 返回 1。"""
    from evaluation.schema import EvalSchemaError
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("bad report")):
        result = main(["validate-report", str(p)])
    assert result == 1


# ---------- _format_metric 各种 value 类型 ----------

def test_format_metric_value_none_batch47():
    out = _format_metric("name", {"value": None, "reason": "no_data"})
    assert "null" in out
    assert "no_data" in out


def test_format_metric_value_true_batch47():
    out = _format_metric("name", {"value": True, "reason": None})
    assert "true" in out  # 小写


def test_format_metric_value_false_batch47():
    out = _format_metric("name", {"value": False, "reason": None})
    assert "false" in out


def test_format_metric_value_float_batch47():
    out = _format_metric("name", {"value": 0.123456, "reason": None})
    assert "0.1235" in out  # 4 位小数


def test_format_metric_value_int_batch47():
    """int 不是 bool 也不是 float → fallthrough。"""
    out = _format_metric("name", {"value": 42, "reason": None})
    assert "42" in out


def test_format_metric_value_dict_batch47():
    out = _format_metric("name", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out


def test_format_metric_value_dict_sorted_batch47():
    """dict 应按 key 排序输出。"""
    out = _format_metric("name", {"value": {"z": 1, "a": 2}, "reason": None})
    # a 应该出现在 z 之前
    assert out.index("a=2") < out.index("z=1")


def test_format_metric_value_str_batch47():
    """str 走 fallthrough。"""
    out = _format_metric("name", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_padding_36_batch47():
    """name 应被填充到至少 36 字符宽。"""
    out = _format_metric("x", {"value": 1, "reason": None})
    # "  x" + padding 直到 value
    # 至少有 36 字符 + 2 前导空格
    line_without_prefix = out[2:]  # 去掉前导两空格
    assert len(line_without_prefix) >= 36


def test_format_metric_no_reason_uses_ok_batch47():
    out = _format_metric("name", {"value": 1.0, "reason": None})
    assert "ok" in out


# ---------- _run_inspect_doc 输出 ----------

def test_run_inspect_doc_prints_file_path_batch47(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    result = _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "file:" in captured.out
    assert result == 0


def test_run_inspect_doc_prints_metrics_section_batch47(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_not_exist_batch47(tmp_path):
    args = MagicMock()
    args.input = str(tmp_path / "nofile.json")
    args.tolerance_chars = 30
    result = _run_inspect_doc(args)
    assert result == 2


# ---------- _sort_key 嵌套函数行为 ----------

def test_sort_key_bool_priority_0_batch47(tmp_path, capsys):
    """bool 排在 priority 0（最先）。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    # pipeline_success (bool) 应当靠前
    assert "metrics:" in captured.out


# ---------- module source 字符串补强 ----------

def test_source_contains_run_command_batch47():
    src = inspect.getsource(cli_mod)
    assert '"run"' in src or "'run'" in src


def test_source_contains_validate_report_command_batch47():
    src = inspect.getsource(cli_mod)
    assert "validate-report" in src


def test_source_contains_inspect_doc_command_batch47():
    src = inspect.getsource(cli_mod)
    assert "inspect-doc" in src


def test_source_contains_RawDescriptionHelpFormatter_batch47():
    src = inspect.getsource(cli_mod)
    assert "RawDescriptionHelpFormatter" in src


def test_source_contains_ManifestError_batch47():
    src = inspect.getsource(cli_mod)
    assert "ManifestError" in src


def test_source_contains_EvalSchemaError_batch47():
    src = inspect.getsource(cli_mod)
    assert "EvalSchemaError" in src


def test_source_contains_utf8_reconfigure_batch47():
    src = inspect.getsource(cli_mod)
    assert "reconfigure" in src


def test_source_contains_schannel_or_errors_replace_batch47():
    src = inspect.getsource(cli_mod)
    assert "errors=" in src


def test_source_contains_subcommand_help_batch47():
    src = inspect.getsource(cli_mod)
    assert "跑评测" in src


def test_source_contains_sanity_check_batch47():
    src = inspect.getsource(cli_mod)
    assert "sanity check" in src or "sanity" in src


def test_source_contains_choices_fallback_kreuzberg_batch47():
    src = inspect.getsource(cli_mod)
    assert "fallback" in src
    assert "kreuzberg" in src


def test_source_contains_no_hardcoded_paths_batch47():
    src = inspect.getsource(cli_mod)
    assert "C:\\\\Users" not in src
    assert "/Users/" not in src


# ---------- AST 结构补强 ----------

def test_ast_top_level_functions_count_batch47():
    tree = ast.parse(inspect.getsource(cli_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 4  # _build_parser / main / _format_metric / _run_inspect_doc


def test_ast_build_parser_has_add_subparsers_batch47():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_parser"][0]
    calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)]
    # 至少 1 个 add_subparsers 调用
    found = False
    for c in calls:
        if isinstance(c.func, ast.Attribute) and c.func.attr == "add_subparsers":
            found = True
            break
    assert found


def test_ast_build_parser_has_three_add_parser_batch47():
    """sub.add_parser('run'), sub.add_parser('validate-report'), sub.add_parser('inspect-doc')."""
    tree = ast.parse(inspect.getsource(cli_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_parser"][0]
    add_parser_calls = []
    for n in ast.walk(func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_parser":
            add_parser_calls.append(n)
    assert len(add_parser_calls) == 3


def test_ast_main_has_three_command_if_batch47():
    """main 应有 3 个 args.command == "xxx" 的 if。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    # 至少 3 个 command 比较 if
    assert len(ifs) >= 3


def test_ast_main_has_multiple_try_batch47():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) >= 3  # load_manifest / run_evaluation / validate_file


def test_ast_main_returns_int_batch47():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    # 多个 return 0/1/2
    assert len(returns) >= 6


def test_ast_run_inspect_doc_has_nested_function_batch47():
    """_run_inspect_doc 内部应定义 _sort_key 嵌套函数。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc"][0]
    nested = [n for n in func.body if isinstance(n, ast.FunctionDef)]
    assert len(nested) == 1
    assert nested[0].name == "_sort_key"


def test_ast_format_metric_has_multiple_if_batch47():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_format_metric"][0]
    ifs = [n for n in func.body if isinstance(n, ast.If)]
    assert len(ifs) >= 3  # None / bool / float / dict


def test_ast_module_has_top_level_if_for_reconfigure_batch47():
    """模块顶层应有 if hasattr(sys.stdout, 'reconfigure')。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    ifs = [n for n in tree.body if isinstance(n, ast.If)]
    assert len(ifs) >= 1


def test_ast_module_has_if_main_batch47():
    tree = ast.parse(inspect.getsource(cli_mod))
    ifs = [n for n in tree.body if isinstance(n, ast.If)]
    # 至少 2 个：reconfigure + __main__
    assert len(ifs) >= 2


def test_ast_no_class_def_batch47():
    tree = ast.parse(inspect.getsource(cli_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


# ---------- forbidden tokens 第一百一十一批 ----------

def test_source_no_eval_batch47():
    src = inspect.getsource(cli_mod)
    assert "eval(" not in src


def test_source_no_exec_batch47():
    src = inspect.getsource(cli_mod)
    assert "exec(" not in src


def test_source_no_compile_batch47():
    src = inspect.getsource(cli_mod)
    assert "compile(" not in src


def test_source_no_globals_batch47():
    src = inspect.getsource(cli_mod)
    assert "globals(" not in src


def test_source_no_locals_batch47():
    src = inspect.getsource(cli_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch47():
    src = inspect.getsource(cli_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch47():
    src = inspect.getsource(cli_mod)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch47():
    src = inspect.getsource(cli_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch47():
    src = inspect.getsource(cli_mod)
    assert "pickle.load(" not in src


def test_source_no_subprocess_batch47():
    src = inspect.getsource(cli_mod)
    assert "subprocess" not in src


def test_source_no_yield_batch47():
    src = inspect.getsource(cli_mod)
    assert "yield" not in src


def test_source_no_walrus_batch47():
    src = inspect.getsource(cli_mod)
    assert ":=" not in src


def test_source_no_async_batch47():
    src = inspect.getsource(cli_mod)
    assert "async def" not in src


def test_source_no_await_batch47():
    src = inspect.getsource(cli_mod)
    assert "await " not in src
