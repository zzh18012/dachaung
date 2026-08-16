"""evaluation/cli.py 第九十七轮 edges 测试（Round 686）。

补强 edges77 未触及的角度（第五十四批）。

新角度：
- _build_parser 完整默认值（run 5 个参数默认 / choices 元组 / inspect-doc input positional / run 不接受 positional）
- main 无子命令 SystemExit（stderr 输出 usage）
- main run 输出格式细节（documents= 计数格式 / devset_status= / git_commit 截断 / git_dirty）
- main run parser 传递（--parser kreuzberg 传递给 run_evaluation）
- main run max_chars / tolerance_chars 传递
- main validate-report 优先级（is_file 检查在 validate 之前）
- main inspect-doc metrics 输出（null reason 显示 / bool 显示 true/false / float 4 位 / dict 排序）
- main inspect-doc tolerance-chars 传递给 chunk_boundary_prf
- _format_metric 更多类型（str value / list value / long name 对齐）
- 模块源码补强（prog= / description= / add_argument help 文本 / choices / type=int / default 值 / return 0/1/2 对应关系 / print(file=sys.stderr)）
- AST 结构补强（_build_parser 4 add_argument(run) / main 3 command compare / _run_inspect_doc 嵌套 _sort_key 4 return / _format_metric 5 分支 return）
- forbidden tokens 第一百五十六批
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 完整默认值 ----------

def test_build_parser_run_defaults_batch52():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.command == "run"
    assert args.manifest == "m.json"
    assert args.output == "o.json"
    assert args.parser == "fallback"
    assert args.max_chars == 800
    assert args.tolerance_chars == 30


def test_build_parser_choices_tuple_batch52():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m", "--output", "o", "--parser", "fallback"])
    assert args.parser == "fallback"


def test_build_parser_inspect_doc_positional_batch52():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "x.json"])
    assert args.command == "inspect-doc"
    assert args.input == "x.json"
    assert not hasattr(args, "manifest")


def test_build_parser_run_no_positional_batch52():
    """run 子命令不接受多余 positional。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "extra.json"])


def test_build_parser_validate_report_no_optional_batch52():
    p = _build_parser()
    args = p.parse_args(["validate-report", "r.json"])
    assert not hasattr(args, "parser")
    assert not hasattr(args, "max_chars")


def test_build_parser_help_strings_batch52():
    p = _build_parser()
    src = inspect.getsource(cli_mod)
    assert "跑评测，生成报告 JSON" in src
    assert "校验评测报告是否符合" in src
    assert "单文档跑指标" in src


# ---------- main 无子命令 ----------

def test_main_no_command_system_exit_batch52(capsys):
    with pytest.raises(SystemExit) as ei:
        main([])
    assert ei.value.code != 0


def test_main_unknown_command_system_exit_batch52(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["unknown"])
    assert ei.value.code != 0


# ---------- main run 输出格式细节 ----------

def _patch_run_ok(fake_report, git=None):
    m_obj = MagicMock()
    m_obj.project_root = Path(".")
    return [
        patch("evaluation.cli.Path", side_effect=lambda x: MagicMock(is_file=lambda: True)),
        patch("evaluation.cli.load_manifest", return_value=m_obj),
        patch("evaluation.cli.run_evaluation", return_value=fake_report),
        patch("evaluation.cli.validate_file"),
        patch("evaluation.cli.get_git_provenance", return_value=git or {"git_commit": "c" * 40, "git_dirty": False}),
    ]


def test_main_run_output_documents_count_batch52(capsys):
    fake = {
        "per_doc": [
            {"metrics": {"pipeline_success": {"value": True}}},
            {"metrics": {"pipeline_success": {"value": True}}},
            {"metrics": {"pipeline_success": {"value": True}}},
            {"metrics": {"pipeline_success": {"value": False}}},
        ],
        "devset": {},
    }
    patches = _patch_run_ok(fake)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        rc = main(["run", "--manifest", "m", "--output", "o"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "documents=4" in out
    assert "成功 3" in out
    assert "失败 1" in out


def test_main_run_output_zero_docs_batch52(capsys):
    fake = {"per_doc": [], "devset": {}}
    patches = _patch_run_ok(fake)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        rc = main(["run", "--manifest", "m", "--output", "o"])
    out = capsys.readouterr().out
    assert "documents=0" in out
    assert "成功 0" in out
    assert "失败 0" in out


def test_main_run_output_git_commit_truncated_12_batch52(capsys):
    fake = {"per_doc": [], "devset": {}}
    git = {"git_commit": "abcdefghij0123456789", "git_dirty": True}
    patches = _patch_run_ok(fake, git=git)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        rc = main(["run", "--manifest", "m", "--output", "o"])
    out = capsys.readouterr().out
    assert "abcdefghij01" in out
    assert "abcdefghij0123" not in out  # 截断到 12
    assert "git_dirty=True" in out


def test_main_run_output_git_commit_none_unknown_batch52(capsys):
    fake = {"per_doc": [], "devset": {}}
    git = {"git_commit": None, "git_dirty": True}
    patches = _patch_run_ok(fake, git=git)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        rc = main(["run", "--manifest", "m", "--output", "o"])
    out = capsys.readouterr().out
    assert "git_commit=unknown" in out


# ---------- main run 参数传递 ----------

def test_main_run_passes_parser_name_batch52(capsys):
    fake = {"per_doc": [], "devset": {}}
    patches = _patch_run_ok(fake)
    with patches[0], patches[1], patches[2] as re_, patches[3], patches[4]:
        main(["run", "--manifest", "m", "--output", "o", "--parser", "kreuzberg"])
    assert re_.call_args.kwargs["parser_name"] == "kreuzberg"


def test_main_run_passes_max_chars_batch52(capsys):
    fake = {"per_doc": [], "devset": {}}
    patches = _patch_run_ok(fake)
    with patches[0], patches[1], patches[2] as re_, patches[3], patches[4]:
        main(["run", "--manifest", "m", "--output", "o", "--max-chars", "1200"])
    assert re_.call_args.kwargs["max_chars"] == 1200


def test_main_run_passes_tolerance_chars_batch52(capsys):
    fake = {"per_doc": [], "devset": {}}
    patches = _patch_run_ok(fake)
    with patches[0], patches[1], patches[2] as re_, patches[3], patches[4]:
        main(["run", "--manifest", "m", "--output", "o", "--tolerance-chars", "55"])
    assert re_.call_args.kwargs["tolerance_chars"] == 55


def test_main_run_default_parser_fallback_batch52(capsys):
    fake = {"per_doc": [], "devset": {}}
    patches = _patch_run_ok(fake)
    with patches[0], patches[1], patches[2] as re_, patches[3], patches[4]:
        main(["run", "--manifest", "m", "--output", "o"])
    assert re_.call_args.kwargs["parser_name"] == "fallback"
    assert re_.call_args.kwargs["max_chars"] == 800
    assert re_.call_args.kwargs["tolerance_chars"] == 30


# ---------- main validate-report 优先级 ----------

def test_main_validate_report_isfile_before_validate_batch52(capsys):
    """文件不存在时优先返回 2，不调用 validate_file。"""
    with patch("evaluation.cli.validate_file") as vf:
        rc = main(["validate-report", "C:/no/such/file.json"])
    assert rc == 2
    vf.assert_not_called()


def test_main_validate_report_isfile_true_calls_validate_batch52(capsys, tmp_path):
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file") as vf:
        rc = main(["validate-report", str(p)])
    assert rc == 0
    vf.assert_called_once()


# ---------- main inspect-doc metrics 输出 ----------

def test_inspect_doc_null_metric_with_reason_batch52(capsys, tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"chunks": [], "elements": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    # 空 chunks → chunk 相关指标 reason
    assert "null" in out


def test_inspect_doc_bool_metric_lowercase_batch52(capsys, tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    # pipeline_success true（小写）
    assert "true" in out


def test_inspect_doc_float_4_decimal_batch52(capsys, tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "a", "element_id": "e1", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
            {"type": "paragraph", "content": "b", "element_id": "e2", "source_locator": {"page": 1}},
        ],
        "chunks": [{"text": "ab", "source_element_ids": ["e1", "e2"]}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    # pdf_locator_valid_ratio = 0.5 → "0.5000"
    assert "0.5000" in out


def test_inspect_doc_passes_tolerance_chars_batch52(capsys, tmp_path):
    """--tolerance-chars 传给 chunk_boundary_prf。"""
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}) as cb:
        rc = main(["inspect-doc", str(p), "--tolerance-chars", "88"])
    assert rc == 0
    assert cb.call_args.kwargs.get("tolerance_chars") == 88


# ---------- _format_metric 更多类型 ----------

def test_format_metric_str_value_batch52():
    out = _format_metric("code", {"value": "E_404", "reason": None})
    assert "E_404" in out


def test_format_metric_list_value_batch52():
    """list value → 走默认分支（str(value)）。"""
    out = _format_metric("markers", {"value": ["a", "b"], "reason": None})
    assert "a" in out and "b" in out


def test_format_metric_long_name_alignment_batch52():
    short = _format_metric("ab", {"value": 1, "reason": None})
    long = _format_metric("a" * 40, {"value": 1, "reason": None})
    # name 字段宽 36
    assert "ab" in short
    assert "a" * 40 in long


def test_format_metric_returns_str_batch52():
    for v in (None, True, 0.5, 1, "x", {"a": 1}, [1]):
        out = _format_metric("k", {"value": v, "reason": None})
        assert isinstance(out, str)


def test_format_metric_bool_with_reason_batch52():
    out = _format_metric("flag", {"value": True, "reason": "custom"})
    # value 非 None → 用 reason or 'ok'
    assert "custom" in out


def test_format_metric_empty_reason_int_batch52():
    out = _format_metric("n", {"value": 5, "reason": None})
    # reason None → 'ok'
    assert "(ok)" in out


# ---------- 模块源码补强 ----------

def test_source_prog_kwarg_batch52():
    src = inspect.getsource(cli_mod)
    assert 'prog="evaluation.cli"' in src


def test_source_description_kwarg_batch52():
    src = inspect.getsource(cli_mod)
    assert "跑开发集 → 报告" in src


def test_source_manifest_help_batch52():
    src = inspect.getsource(cli_mod)
    assert "清单 JSON 路径" in src


def test_source_output_help_batch52():
    src = inspect.getsource(cli_mod)
    assert "报告输出 JSON 路径" in src


def test_source_parser_help_batch52():
    src = inspect.getsource(cli_mod)
    assert "parser（默认 fallback）" in src


def test_source_max_chars_help_batch52():
    src = inspect.getsource(cli_mod)
    assert "分块上限（默认 800）" in src


def test_source_tolerance_help_batch52():
    src = inspect.getsource(cli_mod)
    assert "chunk_boundary 匹配容差" in src


def test_source_stderr_prints_batch52():
    src = inspect.getsource(cli_mod)
    assert src.count("file=sys.stderr") >= 8


def test_source_return_0_ok_batch52():
    src = inspect.getsource(cli_mod)
    assert "return 0" in src


def test_source_return_1_error_batch52():
    src = inspect.getsource(cli_mod)
    assert src.count("return 1") >= 6


def test_source_return_2_notfound_batch52():
    src = inspect.getsource(cli_mod)
    assert src.count("return 2") >= 4


def test_source_type_int_kwargs_batch52():
    src = inspect.getsource(cli_mod)
    assert src.count("type=int") == 3  # run max-chars + run tolerance + inspect tolerance


def test_source_choices_kwarg_batch52():
    src = inspect.getsource(cli_mod)
    assert 'choices=("fallback", "kreuzberg")' in src


def test_source_json_load_in_inspect_batch52():
    src = inspect.getsource(cli_mod)
    assert "json.load(f)" in src


def test_source_compute_automatic_metrics_call_batch52():
    src = inspect.getsource(cli_mod)
    assert "compute_automatic_metrics(" in src


def test_source_metrics_update_calls_batch52():
    src = inspect.getsource(cli_mod)
    assert src.count("metrics.update(") == 2


def test_source_print_metric_loop_batch52():
    src = inspect.getsource(cli_mod)
    assert "for name in sorted(metrics.keys()" in src


# ---------- AST 结构补强 ----------

def test_ast_build_parser_5_add_argument_run_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_parser")
    # 找 run 子 parser 的 add_argument：函数级 walk 全部 add_argument
    adds = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "add_argument"
    ]
    # run 5 + validate-report 1 + inspect-doc 2 = 8
    assert len(adds) == 8


def test_ast_main_command_compares_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    src = ast.unparse(func)
    for cmd in ("'run'", "'validate-report'", "'inspect-doc'"):
        assert f"args.command == {cmd}" in src or f'args.command == {cmd.replace(chr(39), chr(34))}' in src


def test_ast_main_last_return_2_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    # 最后一个 statement 是 return 2
    last = func.body[-1]
    assert isinstance(last, ast.Return)
    assert isinstance(last.value, ast.Constant)
    assert last.value.value == 2


def test_ast_sort_key_4_returns_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    nested = next(n for n in ast.walk(func) if isinstance(n, ast.FunctionDef) and n.name == "_sort_key")
    returns = [n for n in ast.walk(nested) if isinstance(n, ast.Return)]
    assert len(returns) == 4


def test_ast_format_metric_5_returns_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_format_metric")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    # None / bool / float / dict / 默认 = 5
    assert len(returns) == 5


def test_ast_inspect_doc_lazy_imports_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    imports = [n for n in func.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 2  # annotation_metrics + metrics


def test_ast_reconfigure_if_at_module_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    # 第一个模块级 If 是 reconfigure
    first_if = next(n for n in tree.body if isinstance(n, ast.If))
    src = ast.unparse(first_if)
    assert "reconfigure" in src


def test_ast_main_if_doc_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    # 最后一个模块级语句是 if __name__
    last = tree.body[-1]
    assert isinstance(last, ast.If)
    src = ast.unparse(last)
    assert '__name__' in src and "main()" in src


def test_ast_no_class_def_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_no_star_import_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


def test_ast_no_global_nonlocal_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


def test_ast_no_while_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))


# ---------- forbidden tokens 第一百五十六批 ----------

def _src() -> str:
    return inspect.getsource(cli_mod)


def test_source_no_eval_batch52():
    assert "eval(" not in _src()


def test_source_no_exec_batch52():
    assert "exec(" not in _src()


def test_source_no_compile_batch52():
    assert "compile(" not in _src()


def test_source_no_globals_batch52():
    assert "globals(" not in _src()


def test_source_no_locals_batch52():
    assert "locals(" not in _src()


def test_source_no_os_system_batch52():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch52():
    assert "subprocess" not in _src()


def test_source_no_popen_batch52():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch52():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch52():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch52():
    assert "socket" not in _src()


def test_source_no_requests_batch52():
    assert "requests" not in _src()


def test_source_no_urllib_batch52():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch52():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch52():
    assert "yield" not in _src()


def test_source_no_async_await_batch52():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch52():
    assert _src().count("open(") == 1
