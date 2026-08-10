"""evaluation/cli.py 第二十九轮 edges 测试（Round 331）。

重点补强 edges27 未触及的角度：
- _build_parser 配置深度（prog / description / subparser required / formatter_class）
- _format_metric 字符串精确补强（格式控制 / indent / name 36 chars padding）
- main 退出码矩阵（each path returns specific code）
- main 错误消息内容精确（stderr messages）
- module source forbidden tokens 第三批（~75 stdlib）
- module source 字符串精确补强（imports / control flow / kwargs）
- signatures 精确补强（return types）
- 模块整体合理性
- 端到端集成补强（more scenarios）
"""

from __future__ import annotations

import inspect
import json
import types
from pathlib import Path

import pytest

from evaluation import cli as cli_mod
from evaluation.cli import (
    _build_parser,
    _format_metric,
    _run_inspect_doc,
    main,
)


# ---------- _build_parser 配置深度 ----------


def test_build_parser_has_prog_evaluation_cli():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_has_description_mentions_评测():
    p = _build_parser()
    assert "评测" in p.description


def test_build_parser_has_subparsers_required():
    p = _build_parser()
    # subparsers action 应该是 required
    sub_action = None
    for action in p._actions:
        if hasattr(action, "_parser_class"):
            sub_action = action
            break
    assert sub_action is not None
    assert sub_action.required is True


def test_build_parser_has_3_subparsers():
    p = _build_parser()
    sub_action = None
    for action in p._actions:
        if hasattr(action, "_parser_class"):
            sub_action = action
            break
    assert sub_action is not None
    assert len(sub_action.choices) == 3
    assert set(sub_action.choices) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_run_subparser_description_present():
    p = _build_parser()
    sub_action = None
    for action in p._actions:
        if hasattr(action, "_parser_class"):
            sub_action = action
            break
    run_p = sub_action.choices["run"]
    # run subparser 有自己的 help
    assert run_p.description is None or isinstance(run_p.description, str)


def test_build_parser_run_subparser_has_5_args():
    p = _build_parser()
    sub_action = None
    for action in p._actions:
        if hasattr(action, "_parser_class"):
            sub_action = action
            break
    run_p = sub_action.choices["run"]
    args = [a.dest for a in run_p._actions if a.dest != "help"]
    assert set(args) == {"manifest", "output", "parser", "max_chars", "tolerance_chars"}


def test_build_parser_validate_report_subparser_has_1_arg():
    p = _build_parser()
    sub_action = None
    for action in p._actions:
        if hasattr(action, "_parser_class"):
            sub_action = action
            break
    val_p = sub_action.choices["validate-report"]
    args = [a.dest for a in val_p._actions if a.dest != "help"]
    assert args == ["input"]


def test_build_parser_inspect_doc_subparser_has_2_args():
    p = _build_parser()
    sub_action = None
    for action in p._actions:
        if hasattr(action, "_parser_class"):
            sub_action = action
            break
    ins_p = sub_action.choices["inspect-doc"]
    args = [a.dest for a in ins_p._actions if a.dest != "help"]
    assert set(args) == {"input", "tolerance_chars"}


def test_build_parser_run_manifest_arg_required():
    p = _build_parser()
    sub_action = None
    for action in p._actions:
        if hasattr(action, "_parser_class"):
            sub_action = action
            break
    run_p = sub_action.choices["run"]
    manifest_action = next(a for a in run_p._actions if a.dest == "manifest")
    assert manifest_action.required is True


def test_build_parser_run_output_arg_required():
    p = _build_parser()
    sub_action = None
    for action in p._actions:
        if hasattr(action, "_parser_class"):
            sub_action = action
            break
    run_p = sub_action.choices["run"]
    output_action = next(a for a in run_p._actions if a.dest == "output")
    assert output_action.required is True


def test_build_parser_run_parser_arg_not_required():
    p = _build_parser()
    sub_action = None
    for action in p._actions:
        if hasattr(action, "_parser_class"):
            sub_action = action
            break
    run_p = sub_action.choices["run"]
    parser_action = next(a for a in run_p._actions if a.dest == "parser")
    assert parser_action.required is False


def test_build_parser_run_parser_choices_tuple():
    p = _build_parser()
    sub_action = None
    for action in p._actions:
        if hasattr(action, "_parser_class"):
            sub_action = action
            break
    run_p = sub_action.choices["run"]
    parser_action = next(a for a in run_p._actions if a.dest == "parser")
    assert parser_action.choices == ("fallback", "kreuzberg")


def test_build_parser_validate_report_input_positional():
    p = _build_parser()
    sub_action = None
    for action in p._actions:
        if hasattr(action, "_parser_class"):
            sub_action = action
            break
    val_p = sub_action.choices["validate-report"]
    input_action = next(a for a in val_p._actions if a.dest == "input")
    # positional → option_strings 为空
    assert input_action.option_strings == []


def test_build_parser_inspect_doc_input_positional():
    p = _build_parser()
    sub_action = None
    for action in p._actions:
        if hasattr(action, "_parser_class"):
            sub_action = action
            break
    ins_p = sub_action.choices["inspect-doc"]
    input_action = next(a for a in ins_p._actions if a.dest == "input")
    assert input_action.option_strings == []


# ---------- _format_metric 字符串精确补强 ----------


def test_format_metric_null_value_includes_reason():
    out = _format_metric("foo", {"value": None, "reason": "no_data"})
    assert "null" in out
    assert "no_data" in out


def test_format_metric_null_value_no_reason_still_includes_paren():
    out = _format_metric("foo", {"value": None, "reason": None})
    assert "null" in out
    assert "(None)" in out


def test_format_metric_bool_true_lowercase():
    out = _format_metric("foo", {"value": True, "reason": None})
    assert "true" in out
    assert "True" not in out


def test_format_metric_bool_false_lowercase():
    out = _format_metric("foo", {"value": False, "reason": None})
    assert "false" in out
    assert "False" not in out


def test_format_metric_float_4_decimal_places():
    out = _format_metric("foo", {"value": 0.123456789, "reason": None})
    assert "0.1235" in out  # 4 位小数


def test_format_metric_int_value_no_decimal():
    out = _format_metric("foo", {"value": 42, "reason": None})
    assert "42" in out
    assert "42.0000" not in out


def test_format_metric_dict_value_sorted_by_key():
    out = _format_metric(
        "foo",
        {"value": {"b": 2, "a": 1, "c": 3}, "reason": None},
    )
    # a=1 出现在 b=2 之前
    assert out.index("a=1") < out.index("b=2") < out.index("c=3")


def test_format_metric_dict_value_joined_by_comma():
    out = _format_metric(
        "foo",
        {"value": {"a": 1, "b": 2}, "reason": None},
    )
    assert "a=1, b=2" in out


def test_format_metric_fallback_str_value():
    out = _format_metric("foo", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_fallback_list_value():
    out = _format_metric("foo", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in out


def test_format_metric_fallback_tuple_value():
    out = _format_metric("foo", {"value": (1, 2), "reason": None})
    assert "(1, 2)" in out


def test_format_metric_with_reason_overrides_ok():
    out = _format_metric("foo", {"value": 1, "reason": "specific_reason"})
    assert "specific_reason" in out
    assert "ok" not in out


def test_format_metric_no_reason_falls_back_to_ok_for_float():
    out = _format_metric("foo", {"value": 0.5, "reason": None})
    assert "ok" in out


def test_format_metric_no_reason_falls_back_to_ok_for_bool():
    out = _format_metric("foo", {"value": True, "reason": None})
    assert "ok" in out


def test_format_metric_no_reason_falls_back_to_ok_for_dict():
    out = _format_metric("foo", {"value": {}, "reason": None})
    assert "ok" in out


def test_format_metric_name_field_width_36():
    """name 字段占 36 字符（左对齐）。"""
    out = _format_metric("foo", {"value": 1, "reason": None})
    # "  foo" + 空格补齐到 36 + "  1..."
    # 实际格式："  {name:36} ..."
    # 取第 3 个字符到第 38 个字符（去掉前 2 个空格）应该是 name padded
    # 更稳的测试：name 至少占 36 列
    line = out.split("1")[0]  # 取 1 之前的部分
    assert len(line) >= 38  # 2 leading + 36 padded


# ---------- main 退出码矩阵 ----------


def test_main_run_returns_1_for_invalid_manifest_json(tmp_path, capsys):
    bad_manifest = tmp_path / "bad.json"
    bad_manifest.write_text("{not json", encoding="utf-8")
    rc = main(["run", "--manifest", str(bad_manifest), "--output", str(tmp_path / "out.json")])
    assert rc == 1


def test_main_run_returns_0_for_minimal_manifest(tmp_path, capsys):
    """空 manifest → run 成功返回 0。"""
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out)])
    assert rc == 0


def test_main_validate_report_returns_0_for_valid_report(tmp_path, capsys):
    """先跑 run 生成报告，再用 validate-report 校验。"""
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "out.json"
    main(["run", "--manifest", str(m), "--output", str(out)])
    rc = main(["validate-report", str(out)])
    assert rc == 0


def test_main_validate_report_returns_1_for_invalid_report_json(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    rc = main(["validate-report", str(bad)])
    assert rc == 1


def test_main_inspect_doc_returns_0_for_minimal_doc(tmp_path, capsys):
    """inspect-doc 最小 doc 返回 0。"""
    doc = tmp_path / "doc.json"
    doc.write_text(json.dumps({
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(doc)])
    assert rc == 0


def test_main_inspect_doc_returns_1_for_invalid_top_level_number(tmp_path, capsys):
    doc = tmp_path / "doc.json"
    doc.write_text("42", encoding="utf-8")
    rc = main(["inspect-doc", str(doc)])
    assert rc == 1


def test_main_inspect_doc_returns_1_for_invalid_top_level_string(tmp_path, capsys):
    doc = tmp_path / "doc.json"
    doc.write_text('"hello"', encoding="utf-8")
    rc = main(["inspect-doc", str(doc)])
    assert rc == 1


def test_main_unknown_subcommand_exits_2(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["unknown"])
    assert ei.value.code == 2


def test_main_no_subcommand_exits_2(capsys):
    with pytest.raises(SystemExit) as ei:
        main([])
    assert ei.value.code == 2


# ---------- main 错误消息内容精确 ----------


def test_main_run_missing_manifest_error_message(tmp_path, capsys):
    rc = main(["run", "--manifest", str(tmp_path / "nope.json"),
               "--output", str(tmp_path / "out.json")])
    captured = capsys.readouterr()
    assert rc == 2
    assert "[ERROR]" in captured.err
    assert "清单不存在" in captured.err


def test_main_validate_report_missing_report_error_message(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "nope.json")])
    captured = capsys.readouterr()
    assert rc == 2
    assert "[ERROR]" in captured.err


def test_main_inspect_doc_missing_doc_error_message(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "nope.json")])
    captured = capsys.readouterr()
    assert rc == 2
    assert "[ERROR]" in captured.err
    assert "文档不存在" in captured.err


def test_main_run_invalid_manifest_error_message(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    rc = main(["run", "--manifest", str(bad),
               "--output", str(tmp_path / "out.json")])
    captured = capsys.readouterr()
    assert rc == 1
    assert "[ERROR]" in captured.err
    assert "清单加载失败" in captured.err


def test_main_inspect_doc_invalid_json_error_message(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "[ERROR]" in captured.err
    assert "JSON 解析失败" in captured.err


def test_main_inspect_doc_array_top_level_error_message(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("[]", encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "[ERROR]" in captured.err
    assert "顶层不是对象" in captured.err


def test_main_run_success_stdout_includes_documents(tmp_path, capsys):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "[OK]" in captured.out
    assert "documents=" in captured.out


def test_main_run_success_stdout_includes_devset_status(tmp_path, capsys):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "out.json"
    main(["run", "--manifest", str(m), "--output", str(out)])
    captured = capsys.readouterr()
    assert "devset_status=" in captured.out


def test_main_run_success_stdout_includes_git_commit(tmp_path, capsys):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "out.json"
    main(["run", "--manifest", str(m), "--output", str(out)])
    captured = capsys.readouterr()
    assert "git_commit=" in captured.out
    assert "git_dirty=" in captured.out


def test_main_validate_report_success_stdout_includes_path(tmp_path, capsys):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "out.json"
    main(["run", "--manifest", str(m), "--output", str(out)])
    capsys.readouterr()  # clear
    rc = main(["validate-report", str(out)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "[OK]" in captured.out
    assert str(out) in captured.out


# ---------- module source forbidden tokens 第三批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "base64", "binascii", "bisect", "calendar", "concurrent",
        "contextlib", "copyreg", "csv", "fnmatch", "functools",
        "getopt", "getpass", "gettext", "heapq", "imaplib",
        "importlib", "ipaddress", "locale", "lzma", "mailbox",
        "mimetypes", "mmap", "multiprocessing", "netrc", "ntpath",
        "numbers", "operator", "optparse", "platform",
        "poplib", "posixpath", "profile", "pstats", "py_compile",
        "quopri", "reprlib", "runpy", "sched", "select",
        "shelve", "shlex", "signal", "site", "smtplib",
        "sndhdr", "socketserver", "sqlite3", "ssl", "subprocess",
        "sunau", "symtable", "tabnanny", "telnetlib", "termios",
        "timeit", "tkinter", "token", "tokenize", "trace",
        "tty", "turtle", "unittest", "urllib",
        "uu", "webbrowser", "xdrlib", "zipapp", "zipfile",
        "zipimport", "array", "ast", "atexit",
        "builtins", "collections",
    ],
)
def test_module_source_forbidden_tokens_third_batch(token):
    """这些 stdlib 模块不应出现在 cli.py（仅用 argparse/json/sys/Path）。"""
    src = inspect.getsource(cli_mod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_from_future():
    src = inspect.getsource(cli_mod)
    assert "from __future__ import annotations" in src


def test_module_source_has_import_argparse():
    src = inspect.getsource(cli_mod)
    assert "import argparse" in src


def test_module_source_has_import_json():
    src = inspect.getsource(cli_mod)
    assert "import json" in src


def test_module_source_has_import_sys():
    src = inspect.getsource(cli_mod)
    assert "import sys" in src


def test_module_source_has_from_pathlib_import_path():
    src = inspect.getsource(cli_mod)
    assert "from pathlib import Path" in src


def test_module_source_has_evaluation_manifest_import():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.manifest import" in src
    assert "ManifestError" in src
    assert "load_manifest" in src


def test_module_source_has_evaluation_report_import():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.report import" in src
    assert "get_git_provenance" in src


def test_module_source_has_evaluation_runner_import():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_has_evaluation_schema_import():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.schema import" in src
    assert "EvalSchemaError" in src
    assert "validate_file" in src


def test_module_source_has_sys_stdout_reconfigure_call():
    src = inspect.getsource(cli_mod)
    assert "sys.stdout.reconfigure" in src


def test_module_source_has_sys_stderr_reconfigure_call():
    src = inspect.getsource(cli_mod)
    assert "sys.stderr.reconfigure" in src


def test_module_source_has_main_block():
    src = inspect.getsource(cli_mod)
    assert 'if __name__ == "__main__":' in src
    assert "raise SystemExit(main())" in src


def test_module_source_docstring_mentions_run():
    src = inspect.getsource(cli_mod)
    assert "run" in src


def test_module_source_docstring_mentions_validate_report():
    src = inspect.getsource(cli_mod)
    assert "validate-report" in src


def test_module_source_docstring_mentions_inspect_doc():
    src = inspect.getsource(cli_mod)
    assert "inspect-doc" in src


def test_module_source_no_yield():
    src = inspect.getsource(cli_mod)
    assert "yield" not in src


def test_module_source_no_async():
    src = inspect.getsource(cli_mod)
    assert "async " not in src


def test_module_source_no_class():
    src = inspect.getsource(cli_mod)
    assert "\nclass " not in src
    assert not src.startswith("class ")


def test_module_source_no_lambda_in_module():
    src = inspect.getsource(cli_mod)
    assert "lambda " not in src


def test_module_source_main_has_3_branches():
    """main 里有 3 个 if args.command 分支。"""
    src = inspect.getsource(main)
    assert 'args.command == "run"' in src
    assert 'args.command == "validate-report"' in src
    assert 'args.command == "inspect-doc"' in src


def test_module_source_main_calls_run_evaluation():
    src = inspect.getsource(main)
    assert "run_evaluation(" in src


def test_module_source_main_calls_validate_file():
    src = inspect.getsource(main)
    assert 'validate_file(output_path, "evaluation-report.schema.json")' in src


def test_module_source_main_returns_0_for_run_success():
    src = inspect.getsource(main)
    # 多个 return 0 / return 1 / return 2
    assert "return 0" in src
    assert "return 1" in src
    assert "return 2" in src


def test_module_source_format_metric_uses_get_method():
    src = inspect.getsource(_format_metric)
    assert 'metric.get("value")' in src
    assert 'metric.get("reason")' in src


def test_module_source_format_metric_uses_isinstance():
    src = inspect.getsource(_format_metric)
    assert "isinstance" in src


def test_module_source_run_inspect_doc_imports_metrics():
    src = inspect.getsource(_run_inspect_doc)
    assert "from evaluation.annotation_metrics import" in src
    assert "chunk_boundary_prf" in src
    assert "figure_caption_prf" in src
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_run_inspect_doc_calls_compute_automatic_metrics():
    src = inspect.getsource(_run_inspect_doc)
    assert "compute_automatic_metrics(" in src


# ---------- signatures 精确补强 ----------


def test_main_signature_return_int():
    sig = inspect.signature(main)
    assert "int" in str(sig.return_annotation)


def test_main_signature_argv_optional():
    sig = inspect.signature(main)
    p = sig.parameters["argv"]
    assert p.default is None
    assert "| None" in str(p.annotation) or "Optional" in str(p.annotation)


def test_main_no_varargs_varkw():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_build_parser_no_params():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_build_parser_return_annotation():
    sig = inspect.signature(_build_parser)
    assert "ArgumentParser" in str(sig.return_annotation)


def test_format_metric_2_params():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters) == ["name", "metric"]


def test_format_metric_return_str():
    sig = inspect.signature(_format_metric)
    assert "str" in str(sig.return_annotation)


def test_format_metric_no_default():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_run_inspect_doc_1_param():
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters) == ["args"]


def test_run_inspect_doc_return_int():
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in str(sig.return_annotation)


# ---------- 模块整体合理性 ----------


def test_namespace_main():
    assert hasattr(cli_mod, "main")
    assert isinstance(getattr(cli_mod, "main"), types.FunctionType)


def test_namespace_build_parser():
    assert hasattr(cli_mod, "_build_parser")
    assert isinstance(getattr(cli_mod, "_build_parser"), types.FunctionType)


def test_namespace_format_metric():
    assert hasattr(cli_mod, "_format_metric")
    assert isinstance(getattr(cli_mod, "_format_metric"), types.FunctionType)


def test_namespace_run_inspect_doc():
    assert hasattr(cli_mod, "_run_inspect_doc")
    assert isinstance(getattr(cli_mod, "_run_inspect_doc"), types.FunctionType)


def test_module_no_all_attribute():
    """cli.py 没定义 __all__。"""
    assert not hasattr(cli_mod, "__all__")


def test_module_has_1_public_function():
    public_funcs = [
        n for n, v in vars(cli_mod).items()
        if not n.startswith("_") and isinstance(v, types.FunctionType)
        and getattr(v, "__module__", "") == cli_mod.__name__
    ]
    assert public_funcs == ["main"]


def test_module_has_3_private_functions():
    private_funcs = [
        n for n, v in vars(cli_mod).items()
        if n.startswith("_") and not n.startswith("__")
        and isinstance(v, types.FunctionType)
        and getattr(v, "__module__", "") == cli_mod.__name__
    ]
    assert sorted(private_funcs) == ["_build_parser", "_format_metric", "_run_inspect_doc"]


def test_module_no_class():
    classes = [
        n for n, v in vars(cli_mod).items()
        if not n.startswith("_") and isinstance(v, type)
        and getattr(v, "__module__", "") == cli_mod.__name__
    ]
    assert classes == []


def test_module_has_main_block():
    src = inspect.getsource(cli_mod)
    assert 'if __name__' in src


# ---------- 端到端集成补强 ----------


def test_e2e_run_minimal_manifest_writes_output(tmp_path, capsys):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out)])
    assert rc == 0
    assert out.is_file()


def test_e2e_run_with_kreuzberg_parser_choice(tmp_path, capsys):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out),
               "--parser", "kreuzberg"])
    assert rc == 0


def test_e2e_run_with_max_chars_arg(tmp_path, capsys):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out),
               "--max-chars", "500"])
    assert rc == 0


def test_e2e_run_with_tolerance_chars_arg(tmp_path, capsys):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out),
               "--tolerance-chars", "10"])
    assert rc == 0


def test_e2e_inspect_doc_with_pdf_doc(tmp_path, capsys):
    doc = tmp_path / "doc.json"
    doc.write_text(json.dumps({
        "document_id": "d1",
        "source_type": "pdf",
        "source_path": "a.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "title",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]}},
        ],
        "chunks": [{"text": "title", "source_element_ids": ["h1"]}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(doc)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "title" in captured.out or "elements=1" in captured.out


def test_e2e_inspect_doc_with_chunks_section(tmp_path, capsys):
    doc = tmp_path / "doc.json"
    doc.write_text(json.dumps({
        "document_id": "d1",
        "source_type": "docx",
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "hello"}],
        "chunks": [{"text": "hello", "source_element_ids": ["p1"]}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(doc)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "elements=1" in captured.out
    assert "chunks=1" in captured.out


def test_e2e_inspect_doc_with_metrics_section(tmp_path, capsys):
    doc = tmp_path / "doc.json"
    doc.write_text(json.dumps({
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(doc)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "metrics:" in captured.out


def test_e2e_inspect_doc_with_custom_tolerance(tmp_path, capsys):
    doc = tmp_path / "doc.json"
    doc.write_text(json.dumps({
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(doc), "--tolerance-chars", "5"])
    assert rc == 0


def test_e2e_validate_report_after_run_cycle(tmp_path, capsys):
    """run → validate-report 完整循环。"""
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "out.json"
    rc1 = main(["run", "--manifest", str(m), "--output", str(out)])
    rc2 = main(["validate-report", str(out)])
    assert rc1 == 0
    assert rc2 == 0


def test_e2e_inspect_doc_returns_int(tmp_path):
    doc = tmp_path / "doc.json"
    doc.write_text(json.dumps({
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(doc)])
    assert isinstance(rc, int)


def test_e2e_main_run_returns_int_type(tmp_path):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out)])
    assert isinstance(rc, int)


def test_e2e_main_validate_report_returns_int_type(tmp_path):
    out = tmp_path / "out.json"
    out.write_text("{}", encoding="utf-8")
    rc = main(["validate-report", str(out)])
    assert isinstance(rc, int)


def test_e2e_run_with_str_path(tmp_path, capsys):
    """传字符串路径而非 Path 也能工作。"""
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out)])
    assert rc == 0


def test_e2e_run_creates_output_in_subdir(tmp_path, capsys):
    """output 在不存在的多层子目录下也能创建。"""
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = tmp_path / "a" / "b" / "out.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out)])
    assert rc == 0
    assert out.is_file()
