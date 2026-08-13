"""evaluation/cli.py 第八十九轮 edges 测试（Round 625）。

补强 edges69 未触及的角度（第四十四批）。

新角度：
- _build_parser prog / description / formatter_class
- _build_parser subparser dest="command"
- main 各分支返回值细节
- _format_metric 各种 reason 组合
- _format_metric dict value 排序
- _format_metric name 含特殊字符
- _run_inspect_doc args 各种字段
- _run_inspect_doc 调用 compute_automatic_metrics 传参
- main run 路径 success 输出格式
- main run 路径 error 各类型
- main validate-report 路径
- main inspect-doc dispatch
- module source 字符串精确
- AST 结构
- forbidden tokens 第九十五批
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


# ---------- _build_parser 详细属性 ----------

def test_build_parser_formatter_class_batch44():
    p = _build_parser()
    assert p.formatter_class == argparse.RawDescriptionHelpFormatter


def test_build_parser_has_subparser_action_batch44():
    p = _build_parser()
    # 找到 _SubParsersAction
    found = False
    for action in p._actions:
        if isinstance(action, argparse._SubParsersAction):
            found = True
            break
    assert found


def test_build_parser_subparser_dest_batch44():
    p = _build_parser()
    for action in p._actions:
        if isinstance(action, argparse._SubParsersAction):
            assert action.dest == "command"


def test_build_parser_subparser_required_batch44():
    p = _build_parser()
    for action in p._actions:
        if isinstance(action, argparse._SubParsersAction):
            assert action.required is True


def test_build_parser_subparser_choices_count_batch44():
    p = _build_parser()
    for action in p._actions:
        if isinstance(action, argparse._SubParsersAction):
            assert len(action.choices) == 3
            assert set(action.choices.keys()) == {"run", "validate-report", "inspect-doc"}


# ---------- main run success 输出 ----------

def test_main_run_success_output_format_batch44(tmp_path, capsys):
    """成功跑完后 stdout 含 [OK] + documents + devset_status + git_commit。"""
    manifest_path = tmp_path / "m.json"
    manifest_path.write_text("{}", encoding="utf-8")
    out_path = tmp_path / "out.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    fake_report = {
        "per_doc": [
            {"metrics": {"pipeline_success": {"value": True}}},
            {"metrics": {"pipeline_success": {"value": False}}},
        ],
        "devset": {"status": "incomplete", "file_count": 2, "content_group_count": 1, "pdf_count": 1, "docx_count": 1},
    }

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest):
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abcdef1234567890", "git_dirty": False}):
                    rc = main(["run", "--manifest", str(manifest_path), "--output", str(out_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "[OK]" in captured.out
    assert "documents=2" in captured.out
    assert "成功 1" in captured.out
    assert "失败 1" in captured.out
    assert "devset_status=incomplete" in captured.out
    assert "git_commit=abcdef123456" in captured.out  # [:12]
    assert "git_dirty=False" in captured.out


def test_main_run_no_documents_batch44(tmp_path, capsys):
    manifest_path = tmp_path / "m.json"
    manifest_path.write_text("{}", encoding="utf-8")
    out_path = tmp_path / "out.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    fake_report = {
        "per_doc": [],
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0},
    }

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest):
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "xyz", "git_dirty": True}):
                    rc = main(["run", "--manifest", str(manifest_path), "--output", str(out_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "documents=0" in captured.out
    assert "成功 0" in captured.out
    assert "失败 0" in captured.out


def test_main_run_git_commit_unknown_batch44(tmp_path, capsys):
    """git_commit None → 显示 'unknown'。"""
    manifest_path = tmp_path / "m.json"
    manifest_path.write_text("{}", encoding="utf-8")
    out_path = tmp_path / "out.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path
    fake_report = {"per_doc": [], "devset": {}}

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest):
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
                    rc = main(["run", "--manifest", str(manifest_path), "--output", str(out_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "git_commit=unknown" in captured.out


# ---------- _format_metric 边界 ----------

def test_format_metric_negative_float_batch44():
    out = _format_metric("foo", {"value": -0.5, "reason": None})
    assert "-0.5000" in out


def test_format_metric_int_zero_batch44():
    out = _format_metric("foo", {"value": 0, "reason": None})
    assert "0" in out


def test_format_metric_dict_value_sorted_batch44():
    """dict value 内 items 按 key 排序。"""
    out = _format_metric("foo", {"value": {"b": 2, "a": 1, "c": 3}, "reason": None})
    # sorted → "a=1, b=2, c=3"
    assert "a=1" in out
    assert "b=2" in out
    assert "c=3" in out
    # 验证顺序：a 在 b 前
    assert out.index("a=1") < out.index("b=2") < out.index("c=3")


def test_format_metric_dict_value_with_int_values_batch44():
    out = _format_metric("foo", {"value": {"paragraph": 5, "heading": 2}, "reason": None})
    assert "heading=2" in out
    assert "paragraph=5" in out


def test_format_metric_value_is_list_batch44():
    """list value 走 default 分支（return str(value)）。"""
    out = _format_metric("foo", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in out


def test_format_metric_value_is_none_with_reason_batch44():
    out = _format_metric("foo", {"value": None, "reason": "no_data"})
    assert "null" in out
    assert "no_data" in out


def test_format_metric_value_is_true_with_reason_batch44():
    """bool True 有 reason 时仍走 bool 分支（显示 true），但 reason 替换 'ok'。"""
    out = _format_metric("foo", {"value": True, "reason": "custom"})
    assert "true" in out
    assert "custom" in out


# ---------- _run_inspect_doc 调用链 ----------

def test_run_inspect_doc_calls_compute_automatic_metrics_batch44(tmp_path):
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
    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}) as mock_m:
        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={"_tolerance_chars": {"value": 30}}):
                _run_inspect_doc(args)
    mock_m.assert_called_once()


def test_run_inspect_doc_calls_figure_caption_prf_batch44(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}):
        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}) as mock_f:
            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={"_tolerance_chars": {"value": 30}}):
                _run_inspect_doc(args)
    mock_f.assert_called_once()


def test_run_inspect_doc_calls_chunk_boundary_prf_with_tolerance_batch44(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 42
    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}):
        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={"_tolerance_chars": {"value": 42}}) as mock_c:
                _run_inspect_doc(args)
    args_call, kwargs_call = mock_c.call_args
    assert kwargs_call["tolerance_chars"] == 42


def test_run_inspect_doc_passes_none_annotation_batch44(tmp_path):
    """inspect-doc 在没有 annotation 时调用 figure_caption_prf / chunk_boundary_prf 时 annotation=None。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}):
        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}) as mock_f:
            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={"_tolerance_chars": {"value": 30}}) as mock_c:
                _run_inspect_doc(args)
    # 第二个参数（annotation）应该是 None
    f_args, _ = mock_f.call_args
    assert f_args[1] is None
    c_args, _ = mock_c.call_args
    assert c_args[1] is None


# ---------- _run_inspect_doc 输出排序 ----------

def test_run_inspect_doc_sort_metrics_batch44(tmp_path, capsys):
    """inspect-doc 排序：bool (0) < int/float (1) < other (2) < None (3)。
    同类别内按 name 字母序。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30

    fake_metrics = {
        "null_metric": {"value": None, "reason": "x"},
        "ratio_metric": {"value": 0.5, "reason": None},
        "bool_metric": {"value": True, "reason": None},
        "count_metric": {"value": 10, "reason": None},
    }

    with patch("evaluation.metrics.compute_automatic_metrics", return_value=fake_metrics):
        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={"_tolerance_chars": {"value": 30}}):
                _run_inspect_doc(args)
    captured = capsys.readouterr()
    out = captured.out
    # bool_metric (0) 必须最先；null_metric (3) 必须最后
    assert out.index("bool_metric") < out.index("ratio_metric")
    assert out.index("bool_metric") < out.index("count_metric")
    assert out.index("ratio_metric") < out.index("null_metric")
    assert out.index("count_metric") < out.index("null_metric")


# ---------- main validate-report 各种情况 ----------

def test_main_validate_report_success_output_batch44(tmp_path, capsys):
    p = tmp_path / "report.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    with patch("evaluation.cli.validate_file", return_value=None):
        rc = main(["validate-report", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "[OK]" in captured.out
    assert "evaluation-report" in captured.out


def test_main_validate_report_schema_fail_output_batch44(tmp_path, capsys):
    from evaluation.schema import EvalSchemaError
    p = tmp_path / "report.json"
    p.write_text(json.dumps({"wrong": "x"}), encoding="utf-8")
    with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("schema fail")):
        rc = main(["validate-report", str(p)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "[FAIL]" in captured.err


def test_main_validate_report_json_decode_error_batch44(tmp_path, capsys):
    """JSON 解析失败 → rc=1。"""
    p = tmp_path / "report.json"
    p.write_text("not json", encoding="utf-8")
    # validate_file 会自己 load JSON，所以不需要 mock
    with patch("evaluation.cli.validate_file", side_effect=json.JSONDecodeError("msg", "doc", 0)):
        rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_filenotfounderror_batch44(tmp_path, capsys):
    """FileNotFoundError → rc=2。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", side_effect=FileNotFoundError("not found")):
        rc = main(["validate-report", str(p)])
    assert rc == 2


# ---------- main inspect-doc ----------

def test_main_inspect_doc_dispatch_with_args_batch44():
    """inspect-doc dispatch 把 args 透传给 _run_inspect_doc。"""
    with patch("evaluation.cli._run_inspect_doc", return_value=0) as mock_run:
        rc = main(["inspect-doc", "doc.json", "--tolerance-chars", "50"])
    assert rc == 0
    args_passed = mock_run.call_args[0][0]
    assert args_passed.input == "doc.json"
    assert args_passed.tolerance_chars == 50


# ---------- main default return ----------

def test_main_unknown_command_returns_2_batch44():
    """理论上 argparse required=True 会 SystemExit，但代码末尾有 return 2 兜底。"""
    # argparse 会先 SystemExit
    with pytest.raises(SystemExit):
        main(["unknown-command"])


# ---------- _format_metric name 含特殊字符 ----------

def test_format_metric_name_with_underscores_batch44():
    out = _format_metric("foo_bar_baz", {"value": 0.5, "reason": None})
    assert "foo_bar_baz" in out


def test_format_metric_long_name_batch44():
    """name 超过 36 字符时仍正确显示。"""
    long_name = "a" * 50
    out = _format_metric(long_name, {"value": 0.5, "reason": None})
    assert long_name in out


def test_format_metric_short_name_batch44():
    out = _format_metric("x", {"value": 0.5, "reason": None})
    assert "x" in out


# ---------- module source ----------

def test_module_source_contains_subparsers_dest_batch44():
    src = inspect.getsource(cli_mod)
    assert 'dest="command"' in src


def test_module_source_contains_required_true_batch44():
    src = inspect.getsource(cli_mod)
    assert "required=True" in src


def test_module_source_contains_choices_fallback_kreuzberg_batch44():
    src = inspect.getsource(cli_mod)
    assert "fallback" in src
    assert "kreuzberg" in src


def test_module_source_contains_prog_evaluation_cli_batch44():
    src = inspect.getsource(cli_mod)
    assert 'prog="evaluation.cli"' in src


def test_module_source_contains_description_batch44():
    src = inspect.getsource(cli_mod)
    assert "评测 CLI" in src


def test_module_source_contains_raw_description_batch44():
    src = inspect.getsource(cli_mod)
    assert "RawDescriptionHelpFormatter" in src


def test_module_source_contains_run_subparser_help_batch44():
    src = inspect.getsource(cli_mod)
    assert "跑评测，生成报告 JSON" in src


def test_module_source_contains_validate_report_subparser_help_batch44():
    src = inspect.getsource(cli_mod)
    assert "校验评测报告" in src


def test_module_source_contains_inspect_doc_subparser_help_batch44():
    src = inspect.getsource(cli_mod)
    assert "单文档跑指标" in src


def test_module_source_contains_utf8_reconfigure_block_batch44():
    src = inspect.getsource(cli_mod)
    assert "sys.stdout.reconfigure" in src
    assert "sys.stderr.reconfigure" in src


def test_module_source_contains_inspect_doc_sort_logic_batch44():
    src = inspect.getsource(cli_mod)
    assert "_sort_key" in src


def test_module_source_contains_inspect_doc_no_annotation_note_batch44():
    src = inspect.getsource(cli_mod)
    assert "无标注时该指标固定 null" in src


# ---------- __all__ 不存在 ----------

def test_module_no_all_batch44():
    assert not hasattr(cli_mod, "__all__")


# ---------- AST 结构 ----------

def test_ast_top_level_no_class_batch44():
    tree = ast.parse(inspect.getsource(cli_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_top_level_function_count_batch44():
    tree = ast.parse(inspect.getsource(cli_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 4


def test_ast_top_level_function_names_batch44():
    tree = ast.parse(inspect.getsource(cli_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_build_parser", "main", "_format_metric", "_run_inspect_doc"]


def test_ast_main_has_multiple_if_branches_batch44():
    """main 内有多个 if args.command == ... 分支。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    main_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    ifs = list(ast.walk(main_func))
    ifs = [n for n in ifs if isinstance(n, ast.If)]
    # 至少 3 个 if 分支（run / validate-report / inspect-doc）
    assert len(ifs) >= 3


def test_ast_main_has_try_blocks_batch44():
    """main 内有多个 try 块（每个 command 路径都有）。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    main_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    trys = list(ast.walk(main_func))
    trys = [n for n in trys if isinstance(n, ast.Try)]
    assert len(trys) >= 3


def test_ast_run_inspect_doc_has_inner_function_batch44():
    """_run_inspect_doc 内定义了 _sort_key 内嵌函数。"""
    tree = ast.parse(inspect.getsource(cli_mod))
    insp = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc"][0]
    inner_funcs = list(ast.walk(insp))
    inner_funcs = [n for n in inner_funcs if isinstance(n, ast.FunctionDef) and n.name != "_run_inspect_doc"]
    inner_names = {n.name for n in inner_funcs}
    assert "_sort_key" in inner_names


def test_ast_no_while_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(cli_mod))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_no_classdef_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(cli_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_no_async_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(cli_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_from_future_second_batch44():
    tree = ast.parse(inspect.getsource(cli_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


def test_ast_has_main_guard_batch44():
    tree = ast.parse(inspect.getsource(cli_mod))
    last = tree.body[-1]
    assert isinstance(last, ast.If)
    # 测试 __name__ == "__main__"
    cmp = last.test
    assert isinstance(cmp, ast.Compare)


# ---------- forbidden tokens 第九十五批 ----------

def test_source_no_eval_batch44():
    src = inspect.getsource(cli_mod)
    assert "eval(" not in src


def test_source_no_exec_batch44():
    src = inspect.getsource(cli_mod)
    assert "exec(" not in src


def test_source_no_compile_batch44():
    src = inspect.getsource(cli_mod)
    assert "compile(" not in src


def test_source_no_globals_batch44():
    src = inspect.getsource(cli_mod)
    assert "globals(" not in src


def test_source_no_locals_batch44():
    src = inspect.getsource(cli_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch44():
    src = inspect.getsource(cli_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch44():
    src = inspect.getsource(cli_mod)
    assert "popen(" not in src


def test_source_no_yaml_load_batch44():
    src = inspect.getsource(cli_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch44():
    src = inspect.getsource(cli_mod)
    assert "pickle.load(" not in src


def test_source_no_sys_argv_batch44():
    """使用 argparse 而非 sys.argv。"""
    src = inspect.getsource(cli_mod)
    assert "sys.argv" not in src
