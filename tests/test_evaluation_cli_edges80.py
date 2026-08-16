"""evaluation/cli.py 第九十九轮 edges 测试（Round 699）。

补强 edges79 未触及的角度（第六十四批）。

新角度：
- _build_parser 结构（prog / run 默认 fallback-800-30 / --parser choices 拒绝 / 无子命令 SystemExit 2 / 缺 --manifest 2 / inspect-doc --tolerance-chars 77 / validate-report 位置参数名 input）
- main run kwargs 流转（--parser kreuzberg / --max-chars 500 / --tolerance-chars 77 全部透传 run_evaluation）
- run 输出 n_ok/n_fail 行（2 docs 1 成功 1 失败 + commit[:12]）
- validate-report FAIL 路径（validate_file 抛 EvalSchemaError → [FAIL] rc1 / 抛 FileNotFoundError → rc2）
- inspect-doc --tolerance-chars 77 流转到 chunk_boundary_prf
- inspect-doc 打印全部指标键（行数 == compute+fig+chunk 键数并集）
- _format_metric 全分支（None+reason → null (reason) / bool → true·false (ok) / float 0.3333 / int 0 / dict 带 reason / str 通用分支）
- 源码补强（add_subparsers 行 / choices 元组 / n_fail 行 / 成功失败文案 / isinstance 守卫 / sorted key / 两个 metrics.update / reconfigure except 元组 / type: ignore / open 恰 1）
- AST 补强（add_parser 3 个名字顺序 / add_argument 恰 8 个 / default=30 出现 2 次 / validate-report 分支 3 个 handler 顺序 / 模块级 reconfigure If / run 分支 3 个 kwargs）
- forbidden tokens 第一百六十九批
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import evaluation.cli as cli_mod
from evaluation.annotation_metrics import chunk_boundary_prf, figure_caption_prf
from evaluation.cli import _build_parser, _format_metric, main
from evaluation.metrics import compute_automatic_metrics
from evaluation.schema import EvalSchemaError


# ---------- _build_parser 结构 ----------

def test_parser_prog_batch52():
    assert _build_parser().prog == "evaluation.cli"


def test_parser_run_defaults_batch52():
    args = _build_parser().parse_args(["run", "--manifest", "m", "--output", "o"])
    assert args.command == "run"
    assert args.parser == "fallback"
    assert args.max_chars == 800
    assert args.tolerance_chars == 30


def test_parser_invalid_parser_choice_exits_batch52(capsys):
    with pytest.raises(SystemExit) as ei:
        _build_parser().parse_args(
            ["run", "--manifest", "m", "--output", "o", "--parser", "nope"]
        )
    assert ei.value.code == 2


def test_parser_no_command_exits_batch52():
    with pytest.raises(SystemExit) as ei:
        _build_parser().parse_args([])
    assert ei.value.code == 2


def test_parser_missing_manifest_exits_batch52():
    with pytest.raises(SystemExit) as ei:
        _build_parser().parse_args(["run", "--output", "o"])
    assert ei.value.code == 2


def test_parser_inspect_tolerance_flag_batch52():
    args = _build_parser().parse_args(["inspect-doc", "d.json", "--tolerance-chars", "77"])
    assert args.command == "inspect-doc"
    assert args.input == "d.json"
    assert args.tolerance_chars == 77


def test_parser_validate_input_positional_batch52():
    args = _build_parser().parse_args(["validate-report", "r.json"])
    assert args.command == "validate-report"
    assert args.input == "r.json"


# ---------- main run kwargs 流转 ----------

def test_main_run_kwargs_flow_batch52(monkeypatch, capsys, tmp_path):
    captured = {}
    mf = tmp_path / "m.json"
    mf.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli_mod, "load_manifest",
                        lambda p: SimpleNamespace(project_root=tmp_path))
    monkeypatch.setattr(
        cli_mod, "run_evaluation",
        lambda m, o, **kw: (captured.update(kw), {"per_doc": [], "devset": {}})[1],
    )
    monkeypatch.setattr(cli_mod, "validate_file", lambda *a, **k: None)
    monkeypatch.setattr(cli_mod, "get_git_provenance",
                        lambda root: {"git_commit": "c" * 40, "git_dirty": False})
    rc = main([
        "run", "--manifest", str(mf), "--output", str(tmp_path / "o.json"),
        "--parser", "kreuzberg", "--max-chars", "500", "--tolerance-chars", "77",
    ])
    assert rc == 0
    assert captured == {"parser_name": "kreuzberg", "max_chars": 500, "tolerance_chars": 77}


def test_main_run_success_fail_counts_batch52(monkeypatch, capsys, tmp_path):
    mf = tmp_path / "m.json"
    mf.write_text("{}", encoding="utf-8")
    fake = {
        "per_doc": [
            {"metrics": {"pipeline_success": {"value": True}}},
            {"metrics": {"pipeline_success": {"value": False}}},
        ],
        "devset": {},
    }
    monkeypatch.setattr(cli_mod, "load_manifest",
                        lambda p: SimpleNamespace(project_root=tmp_path))
    monkeypatch.setattr(cli_mod, "run_evaluation", lambda m, o, **kw: fake)
    monkeypatch.setattr(cli_mod, "validate_file", lambda *a, **k: None)
    monkeypatch.setattr(cli_mod, "get_git_provenance",
                        lambda root: {"git_commit": "c" * 40, "git_dirty": True})
    rc = main(["run", "--manifest", str(mf), "--output", str(tmp_path / "o.json")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "documents=2" in out
    assert "成功 1" in out
    assert "失败 1" in out
    assert "cccccccccccc" in out
    assert "git_dirty=True" in out


# ---------- validate-report FAIL 路径 ----------

def test_validate_report_eval_schema_error_fail_batch52(monkeypatch, capsys, tmp_path):
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli_mod, "validate_file",
                        MagicMock(side_effect=EvalSchemaError("bad report")))
    rc = main(["validate-report", str(p)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "[FAIL]" in err
    assert "报告校验失败" in err


def test_validate_report_filenotfound_rc2_batch52(monkeypatch, capsys, tmp_path):
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli_mod, "validate_file",
                        MagicMock(side_effect=FileNotFoundError("Schema 文件不存在")))
    rc = main(["validate-report", str(p)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "[ERROR]" in err


# ---------- inspect-doc ----------

def test_inspect_doc_tolerance_flag_flows_batch52(monkeypatch, capsys, tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    monkeypatch.setattr("evaluation.annotation_metrics.chunk_boundary_prf", MagicMock(return_value={}))
    main(["inspect-doc", str(p), "--tolerance-chars", "77"])
    capsys.readouterr()
    from evaluation.annotation_metrics import chunk_boundary_prf as cb
    assert cb.call_args.kwargs["tolerance_chars"] == 77


def test_inspect_doc_prints_all_metric_keys_batch52(capsys, tmp_path):
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    metric_lines = [ln for ln in out.splitlines() if ln.startswith("  ")]
    expected_keys = (
        set(compute_automatic_metrics(doc, None, "pdf", None))
        | set(figure_caption_prf(doc, None))
        | set(chunk_boundary_prf(doc, None))
    )
    assert rc == 0
    assert len(metric_lines) == len(expected_keys)


# ---------- _format_metric 全分支 ----------

def test_format_metric_null_with_reason_batch52():
    out = _format_metric("x_ratio", {"value": None, "reason": "no_elements"})
    assert "null" in out
    assert "(no_elements)" in out


def test_format_metric_bool_values_batch52():
    assert "true" in _format_metric("a", {"value": True, "reason": None})
    assert "false" in _format_metric("b", {"value": False, "reason": None})
    assert "(ok)" in _format_metric("a", {"value": True, "reason": None})


def test_format_metric_float_4_decimals_batch52():
    assert "0.3333" in _format_metric("r", {"value": 1 / 3, "reason": None})


def test_format_metric_int_zero_batch52():
    assert "0  (ok)" in _format_metric("n", {"value": 0, "reason": None})


def test_format_metric_dict_with_reason_batch52():
    out = _format_metric("by", {"value": {"a": 1}, "reason": "why"})
    assert "(why)" in out


def test_format_metric_str_generic_branch_batch52():
    out = _format_metric("s", {"value": "abc", "reason": None})
    assert "abc" in out
    assert "(ok)" in out


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(cli_mod)


def test_source_add_subparsers_line_batch52():
    assert 'sub = p.add_subparsers(dest="command", required=True)' in _src()


def test_source_parser_choices_batch52():
    assert 'choices=("fallback", "kreuzberg")' in _src()


def test_source_n_fail_line_batch52():
    assert "n_fail = n_docs - n_ok" in _src()


def test_source_success_fail_message_batch52():
    assert "documents={n_docs}（成功 {n_ok}，失败 {n_fail}）" in _src()


def test_source_isinstance_guard_batch52():
    assert "if not isinstance(doc, dict):" in _src()


def test_source_sorted_keys_batch52():
    assert "sorted(metrics.keys(), key=_sort_key)" in _src()


def test_source_two_metrics_updates_batch52():
    src = _src()
    assert "metrics.update(figure_caption_prf(doc, None))" in src
    assert "metrics.update(chunk_boundary_prf(doc, None, tolerance_chars=args.tolerance_chars))" in src


def test_source_reconfigure_except_tuple_batch52():
    assert "except (AttributeError, OSError):" in _src()


def test_source_type_ignore_attr_batch52():
    assert "# type: ignore[attr-defined]" in _src()


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(cli_mod))


def test_ast_add_parser_3_names_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_parser")
    calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_parser"
    ]
    assert [c.args[0].value for c in calls] == ["run", "validate-report", "inspect-doc"]


def test_ast_add_argument_count_8_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_parser")
    args_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_argument"
    ]
    assert len(args_calls) == 8  # run 5 + validate-report 1 + inspect-doc 2


def test_ast_default_30_twice_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_parser")
    src = ast.unparse(func)
    assert src.count("default=30") == 2
    assert src.count("default=800") == 1
    assert src.count("default='fallback'") == 1


def test_ast_validate_report_handlers_order_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    ifs = [n for n in func.body if isinstance(n, ast.If)]
    val_branch = ifs[1]  # validate-report
    trys = [n for n in ast.walk(val_branch) if isinstance(n, ast.Try)]
    assert len(trys) == 1
    assert [ast.unparse(h.type) for h in trys[0].handlers] == [
        "EvalSchemaError", "FileNotFoundError", "json.JSONDecodeError",
    ]


def test_ast_module_reconfigure_if_batch52():
    tree = _tree()
    module_ifs = [n for n in tree.body if isinstance(n, ast.If)]
    # reconfigure 守卫 + __main__ 守卫
    assert len(module_ifs) == 2
    src = ast.unparse(module_ifs[0])
    assert "hasattr(sys.stdout, 'reconfigure')" in src
    assert "sys.stdout.reconfigure(encoding='utf-8', errors='replace')" in src
    assert "__name__ == '__main__'" in ast.unparse(module_ifs[1])


def test_ast_run_branch_kwargs_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    src = ast.unparse(func)
    assert "parser_name=args.parser" in src
    assert "max_chars=args.max_chars" in src
    assert "tolerance_chars=args.tolerance_chars" in src


# ---------- forbidden tokens 第一百六十九批 ----------

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
