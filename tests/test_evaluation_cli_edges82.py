"""evaluation/cli.py 第一百零一轮 edges 测试（Round 713）。

补强 edges81 未触及的角度（第七十八批）。

新角度：
- _build_parser 直测（run 默认 fallback/800/30 / inspect-doc 默认 30 / validate-report 位置参数 / args.command 类型）
- argparse 类型拒绝（--parser 大写 → exit 2 / --max-chars "abc" → exit 2 / --tolerance-chars 1.5 → exit 2）
- _format_metric 精确输出串（null / bool 两个分支的 :36 对齐字面量）
- main 终极 return 2 分支（mock _build_parser 返回 bogus command）
- inspect-doc docx 文档（type=docx / docx_locator 行 null no_elements / chunk_boundary 行 null）
- stderr 与 stdout 分离（成功路径 err 为空 / inspect-doc 成功 err 为空）
- 源码补强（file=sys.stderr × 11 / print() 空行 / "metrics:" 行 / sorted keys 行 / raise SystemExit / 元信息 print 字面）
- AST 补强（_format_metric 5 Return / _run_inspect_doc 内嵌 _sort_key / main 1 GeneratorExp 0 For / 模块 import 精确名单 9 项）
- forbidden tokens 第一百八十三批
"""

from __future__ import annotations

import ast
import inspect
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _build_parser, _format_metric, main


def _doc_stub() -> dict:
    return {
        "document_id": "doc-1", "source_path": "a.docx", "parser_name": "fallback",
        "parser_version": "1.0", "source_type": "docx",
        "elements": [{"type": "paragraph", "content": "ab",
                      "source_locator": {"paragraph_index": 0}}],
        "chunks": [{"text": "ab", "source_element_ids": ["e1"]}],
    }


# ---------- _build_parser 直测 ----------

def test_parser_run_defaults_batch53():
    args = _build_parser().parse_args(
        ["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.command == "run"
    assert type(args.command) is str
    assert args.parser == "fallback"
    assert args.max_chars == 800
    assert args.tolerance_chars == 30
    assert args.manifest == "m.json"
    assert args.output == "o.json"


def test_parser_inspect_doc_default_tolerance_batch53():
    args = _build_parser().parse_args(["inspect-doc", "d.json"])
    assert args.command == "inspect-doc"
    assert args.input == "d.json"
    assert args.tolerance_chars == 30


def test_parser_validate_report_positional_batch53():
    args = _build_parser().parse_args(["validate-report", "r.json"])
    assert args.command == "validate-report"
    assert args.input == "r.json"


def test_parser_prog_and_description_batch53():
    p = _build_parser()
    assert p.prog == "evaluation.cli"
    assert "评测 CLI" in p.description


# ---------- argparse 类型拒绝 ----------

def test_parser_uppercase_choice_rejected_batch53(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["run", "--manifest", "m", "--output", "o", "--parser", "KREUZBERG"])
    assert ei.value.code == 2


def test_parser_non_int_max_chars_rejected_batch53():
    with pytest.raises(SystemExit) as ei:
        main(["run", "--manifest", "m", "--output", "o", "--max-chars", "abc"])
    assert ei.value.code == 2


def test_parser_float_tolerance_rejected_batch53():
    with pytest.raises(SystemExit) as ei:
        main(["inspect-doc", "d.json", "--tolerance-chars", "1.5"])
    assert ei.value.code == 2


# ---------- _format_metric 精确输出 ----------

def test_format_metric_null_exact_string_batch53():
    assert _format_metric("x", {"value": None, "reason": "r"}) == (
        "  x                                    null  (r)"
    )


def test_format_metric_bool_exact_string_batch53():
    assert _format_metric("x", {"value": True, "reason": None}) == (
        "  x                                    true  (ok)"
    )
    assert _format_metric("x", {"value": False, "reason": "why"}) == (
        "  x                                    false  (why)"
    )


# ---------- main 终极 return 2 ----------

def test_main_unknown_command_dead_branch_batch53(monkeypatch):
    """argparse required=True 下不可达；直接注入 bogus namespace 覆盖最后 return 2。"""
    fake_parser = MagicMock()
    fake_parser.parse_args.return_value = SimpleNamespace(command="bogus")
    monkeypatch.setattr(cli_mod, "_build_parser", lambda: fake_parser)
    assert main([]) == 2


# ---------- inspect-doc docx ----------

def test_inspect_doc_docx_output_batch53(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text(json.dumps(_doc_stub()), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "type=docx" in out
    assert "docx_locator_valid_ratio" in out
    assert "chunk_boundary_precision" in out
    # 每个指标行都是 null (reason) 或值 (ok) 的两括号尾
    metric_lines = [l for l in out.splitlines() if l.startswith("  ")]
    assert len(metric_lines) >= 15


# ---------- stderr / stdout 分离 ----------

def test_run_success_stderr_empty_batch53(monkeypatch, tmp_path, capsys):
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete", "documents": [],
    }), encoding="utf-8")
    monkeypatch.setattr(cli_mod, "run_evaluation", MagicMock(return_value={
        "per_doc": [], "devset": {"status": "incomplete"},
    }))
    monkeypatch.setattr(cli_mod, "validate_file", MagicMock())
    monkeypatch.setattr(cli_mod, "get_git_provenance",
                        lambda r: {"git_commit": "a" * 40, "git_dirty": False})
    rc = main(["run", "--manifest", str(m), "--output", str(tmp_path / "o.json")])
    assert rc == 0
    assert capsys.readouterr().err == ""


def test_inspect_doc_success_stderr_empty_batch53(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    assert capsys.readouterr().err == ""


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(cli_mod)


def test_source_stderr_count_batch53():
    assert _src().count("file=sys.stderr") == 11


def test_source_print_layout_lines_batch53():
    src = _src()
    assert "print()" in src
    assert 'print("metrics:")' in src
    assert "sorted(metrics.keys(), key=_sort_key)" in src


def test_source_meta_print_literals_batch53():
    src = _src()
    assert 'print(f"file:        {input_path}")' in src
    assert "raise SystemExit(main())" in src


def test_source_run_path_conversions_batch53():
    src = _src()
    assert "manifest_path = Path(args.manifest)" in src
    assert "output_path = Path(args.output)" in src
    assert "input_path = Path(args.input)" in src


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(cli_mod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def test_ast_format_metric_five_returns_batch53():
    assert len([n for n in ast.walk(_func("_format_metric"))
                if isinstance(n, ast.Return)]) == 5


def test_ast_inspect_doc_inner_sort_key_batch53():
    inner = [n.name for n in ast.walk(_func("_run_inspect_doc"))
             if isinstance(n, ast.FunctionDef) and n.name != "_run_inspect_doc"]
    assert inner == ["_sort_key"]


def test_ast_main_one_genexp_zero_for_batch53():
    import collections
    c = collections.Counter(type(n).__name__
                            for n in ast.walk(_func("main")))
    assert c["GeneratorExp"] == 1
    assert c["For"] == 0


def test_ast_module_imports_exact_batch53():
    mods = []
    for n in _tree().body:
        if isinstance(n, ast.Import):
            mods.extend(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            mods.append(n.module)
    assert sorted(mods) == [
        "__future__", "argparse", "evaluation.manifest", "evaluation.report",
        "evaluation.runner", "evaluation.schema", "json", "pathlib", "sys",
    ]


# ---------- forbidden tokens 第一百八十三批 ----------

def test_source_no_eval_batch53():
    assert "eval(" not in _src()


def test_source_no_exec_batch53():
    assert "exec(" not in _src()


def test_source_no_compile_batch53():
    assert "compile(" not in _src()


def test_source_no_globals_batch53():
    assert "globals(" not in _src()


def test_source_no_locals_batch53():
    assert "locals(" not in _src()


def test_source_no_os_system_batch53():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch53():
    assert "subprocess" not in _src()


def test_source_no_popen_batch53():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch53():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch53():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch53():
    assert "socket" not in _src()


def test_source_no_requests_batch53():
    assert "requests" not in _src()


def test_source_no_urllib_batch53():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch53():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch53():
    assert "yield" not in _src()


def test_source_no_async_await_batch53():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch53():
    assert _src().count("open(") == 1
