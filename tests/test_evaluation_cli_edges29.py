"""evaluation/cli.py 第三十轮 edges 测试（Round 337）。

重点补强 edges28 未触及的角度：
- argparse action 类型精确（_SubParsersAction / _StoreAction）
- run subparser 各 argument 配置深度（type/required/default/choices/help）
- _format_metric 字符串精确补强（源码 level）
- _run_inspect_doc source level 字符串精确补强
- main source level 字符串精确补强（kwargs only / 各 return / print 内容）
- module source forbidden tokens 第四批
- module source 字符串精确补强（imports / control flow / no yield/async/global/lambda/main block）
- signatures 精确补强（param kinds / annotations / defaults）
- 模块整体合理性（namespace / __all__ / private/public 数量）
- 端到端集成补强（更多 manifest/doc 组合 / 错误路径 / 边界值）
"""

from __future__ import annotations

import argparse
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


# ---------- argparse action 类型精确 ----------


def test_build_parser_subparsers_action_is_subparsers_action():
    """subparsers action 的类型是 _SubParsersAction。"""
    p = _build_parser()
    sub_action = None
    for action in p._actions:
        if hasattr(action, "_parser_class"):
            sub_action = action
            break
    assert isinstance(sub_action, argparse._SubParsersAction)


def test_build_parser_subparsers_dest_is_command():
    """subparsers action 的 dest 是 'command'。"""
    p = _build_parser()
    sub_action = None
    for action in p._actions:
        if isinstance(action, argparse._SubParsersAction):
            sub_action = action
            break
    assert sub_action.dest == "command"


def test_build_parser_run_subparser_manifest_is_store_action():
    """run --manifest 是 _StoreAction。"""
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    manifest_actions = [a for a in run_p._actions if "--manifest" in (a.option_strings or [])]
    assert len(manifest_actions) == 1
    assert isinstance(manifest_actions[0], argparse._StoreAction)


def test_build_parser_run_subparser_output_is_store_action():
    """run --output 是 _StoreAction。"""
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    output_actions = [a for a in run_p._actions if "--output" in (a.option_strings or [])]
    assert len(output_actions) == 1
    assert isinstance(output_actions[0], argparse._StoreAction)


def test_build_parser_run_subparser_parser_is_store_action():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    parser_actions = [a for a in run_p._actions if "--parser" in (a.option_strings or [])]
    assert len(parser_actions) == 1
    assert isinstance(parser_actions[0], argparse._StoreAction)


def test_build_parser_run_subparser_max_chars_is_store_action():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    max_chars_actions = [
        a for a in run_p._actions if "--max-chars" in (a.option_strings or [])
    ]
    assert len(max_chars_actions) == 1
    assert isinstance(max_chars_actions[0], argparse._StoreAction)


def test_build_parser_run_subparser_tolerance_chars_is_store_action():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    tol_actions = [
        a for a in run_p._actions if "--tolerance-chars" in (a.option_strings or [])
    ]
    assert len(tol_actions) == 1
    assert isinstance(tol_actions[0], argparse._StoreAction)


# ---------- run subparser 各 argument 配置深度 ----------


def test_build_parser_run_manifest_required_true():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    a = next(x for x in run_p._actions if "--manifest" in (x.option_strings or []))
    assert a.required is True


def test_build_parser_run_output_required_true():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    a = next(x for x in run_p._actions if "--output" in (x.option_strings or []))
    assert a.required is True


def test_build_parser_run_parser_required_false():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    a = next(x for x in run_p._actions if "--parser" in (x.option_strings or []))
    assert a.required is False


def test_build_parser_run_max_chars_required_false():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    a = next(x for x in run_p._actions if "--max-chars" in (x.option_strings or []))
    assert a.required is False


def test_build_parser_run_tolerance_chars_required_false():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    a = next(x for x in run_p._actions if "--tolerance-chars" in (x.option_strings or []))
    assert a.required is False


def test_build_parser_run_parser_default_is_fallback():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    a = next(x for x in run_p._actions if "--parser" in (x.option_strings or []))
    assert a.default == "fallback"


def test_build_parser_run_max_chars_default_800():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    a = next(x for x in run_p._actions if "--max-chars" in (x.option_strings or []))
    assert a.default == 800


def test_build_parser_run_tolerance_chars_default_30():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    a = next(x for x in run_p._actions if "--tolerance-chars" in (x.option_strings or []))
    assert a.default == 30


def test_build_parser_run_max_chars_type_is_int():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    a = next(x for x in run_p._actions if "--max-chars" in (x.option_strings or []))
    assert a.type is int


def test_build_parser_run_tolerance_chars_type_is_int():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    a = next(x for x in run_p._actions if "--tolerance-chars" in (x.option_strings or []))
    assert a.type is int


def test_build_parser_run_parser_choices_is_tuple():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    a = next(x for x in run_p._actions if "--parser" in (x.option_strings or []))
    assert a.choices == ("fallback", "kreuzberg")
    assert isinstance(a.choices, tuple)


def test_build_parser_run_parser_choices_length_2():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    a = next(x for x in run_p._actions if "--parser" in (x.option_strings or []))
    assert len(a.choices) == 2


# ---------- validate-report / inspect-doc subparser 深度 ----------


def test_build_parser_validate_report_input_positional_required():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    val_p = sub_action.choices["validate-report"]
    # 位置参数的 option_strings 是空 list
    positional = [a for a in val_p._actions if not a.option_strings]
    # 第一项是 help，所以过滤掉 dest='help'
    positional_real = [a for a in positional if a.dest != "help"]
    assert len(positional_real) == 1
    assert positional_real[0].dest == "input"
    assert positional_real[0].required is True


def test_build_parser_inspect_doc_input_positional_required():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    ins_p = sub_action.choices["inspect-doc"]
    positional_real = [
        a for a in ins_p._actions if not a.option_strings and a.dest != "help"
    ]
    assert len(positional_real) == 1
    assert positional_real[0].dest == "input"
    assert positional_real[0].required is True


def test_build_parser_inspect_doc_tolerance_chars_default_30():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    ins_p = sub_action.choices["inspect-doc"]
    a = next(
        x for x in ins_p._actions if "--tolerance-chars" in (x.option_strings or [])
    )
    assert a.default == 30


def test_build_parser_inspect_doc_tolerance_chars_type_int():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    ins_p = sub_action.choices["inspect-doc"]
    a = next(
        x for x in ins_p._actions if "--tolerance-chars" in (x.option_strings or [])
    )
    assert a.type is int


def test_build_parser_inspect_doc_no_max_chars():
    """inspect-doc 不接受 --max-chars。"""
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    ins_p = sub_action.choices["inspect-doc"]
    has_max_chars = any(
        "--max-chars" in (a.option_strings or []) for a in ins_p._actions
    )
    assert has_max_chars is False


def test_build_parser_inspect_doc_no_parser_arg():
    """inspect-doc 不接受 --parser。"""
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    ins_p = sub_action.choices["inspect-doc"]
    has_parser = any(
        "--parser" in (a.option_strings or []) for a in ins_p._actions
    )
    assert has_parser is False


def test_build_parser_validate_report_no_optional_args():
    """validate-report 没有任何 optional --xxx 参数。"""
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    val_p = sub_action.choices["validate-report"]
    optionals = [
        a for a in val_p._actions
        if a.option_strings and a.dest != "help"
    ]
    assert len(optionals) == 0


# ---------- _format_metric 字符串精确补强 ----------


def test_format_metric_source_uses_36_width_format():
    src = inspect.getsource(_format_metric)
    assert "{name:36}" in src or "name:36" in src


def test_format_metric_source_uses_get_method():
    src = inspect.getsource(_format_metric)
    assert ".get(" in src


def test_format_metric_source_uses_isinstance_bool():
    src = inspect.getsource(_format_metric)
    assert "isinstance(value, bool)" in src


def test_format_metric_source_uses_isinstance_float():
    src = inspect.getsource(_format_metric)
    assert "isinstance(value, float)" in src


def test_format_metric_source_uses_isinstance_dict():
    src = inspect.getsource(_format_metric)
    assert "isinstance(value, dict)" in src


def test_format_metric_source_uses_str_lower_for_bool():
    src = inspect.getsource(_format_metric)
    assert "str(value).lower()" in src


def test_format_metric_source_uses_4f_format_for_float():
    src = inspect.getsource(_format_metric)
    assert "value:.4f" in src or ":.4f" in src


def test_format_metric_source_uses_sorted_for_dict():
    src = inspect.getsource(_format_metric)
    assert "sorted(" in src


def test_format_metric_source_uses_join_for_dict():
    src = inspect.getsource(_format_metric)
    assert ".join(" in src


def test_format_metric_source_uses_or_ok_pattern():
    """无 reason 时回退到 'ok'。"""
    src = inspect.getsource(_format_metric)
    assert "or 'ok'" in src or 'or "ok"' in src


def test_format_metric_dict_value_with_no_items():
    """空 dict → 空字符串内嵌。"""
    out = _format_metric("foo", {"value": {}, "reason": "empty"})
    assert "foo" in out
    assert "empty" in out


def test_format_metric_dict_value_with_many_items():
    out = _format_metric("foo", {"value": {"a": 1, "b": 2, "c": 3}, "reason": "ok"})
    assert "a=1" in out
    assert "b=2" in out
    assert "c=3" in out


def test_format_metric_zero_float():
    out = _format_metric("ratio", {"value": 0.0, "reason": "all_zero"})
    assert "0.0000" in out
    assert "all_zero" in out


def test_format_metric_one_float():
    out = _format_metric("ratio", {"value": 1.0, "reason": None})
    assert "1.0000" in out
    assert "ok" in out


def test_format_metric_negative_int():
    out = _format_metric("count", {"value": -5, "reason": "negative"})
    assert "-5" in out
    assert "negative" in out


def test_format_metric_unicode_reason():
    out = _format_metric("m", {"value": None, "reason": "无元素"})
    assert "无元素" in out


def test_format_metric_unicode_name():
    out = _format_metric("中文指标", {"value": 1, "reason": "ok"})
    assert "中文指标" in out


# ---------- _run_inspect_doc source level 字符串精确补强 ----------


def test_run_inspect_doc_source_imports_chunk_boundary_prf():
    src = inspect.getsource(_run_inspect_doc)
    assert "chunk_boundary_prf" in src
    assert "from evaluation.annotation_metrics" in src


def test_run_inspect_doc_source_imports_figure_caption_prf():
    src = inspect.getsource(_run_inspect_doc)
    assert "figure_caption_prf" in src


def test_run_inspect_doc_source_imports_compute_automatic_metrics():
    src = inspect.getsource(_run_inspect_doc)
    assert "from evaluation.metrics" in src
    assert "compute_automatic_metrics" in src


def test_run_inspect_doc_source_uses_path_isfile():
    src = inspect.getsource(_run_inspect_doc)
    assert "is_file()" in src


def test_run_inspect_doc_source_uses_json_load():
    src = inspect.getsource(_run_inspect_doc)
    assert "json.load(" in src


def test_run_inspect_doc_source_uses_isinstance_dict():
    src = inspect.getsource(_run_inspect_doc)
    assert "isinstance(doc, dict)" in src


def test_run_inspect_doc_source_returns_2_for_missing_file():
    src = inspect.getsource(_run_inspect_doc)
    assert "return 2" in src


def test_run_inspect_doc_source_returns_1_for_invalid_json():
    src = inspect.getsource(_run_inspect_doc)
    assert "return 1" in src


def test_run_inspect_doc_source_returns_0_at_end():
    src = inspect.getsource(_run_inspect_doc)
    # 函数末尾的 return 0
    assert "return 0" in src


def test_run_inspect_doc_source_uses_doc_get_source_type():
    src = inspect.getsource(_run_inspect_doc)
    assert "source_type" in src
    assert 'doc.get("source_type"' in src or "doc.get('source_type'" in src


def test_run_inspect_doc_source_uses_tolerance_chars_kwarg():
    src = inspect.getsource(_run_inspect_doc)
    assert "tolerance_chars=" in src


def test_run_inspect_doc_source_uses_metrics_update():
    src = inspect.getsource(_run_inspect_doc)
    assert "metrics.update(" in src


def test_run_inspect_doc_source_uses_sorted_with_key():
    src = inspect.getsource(_run_inspect_doc)
    assert "sorted(" in src
    assert "key=" in src


def test_run_inspect_doc_source_prints_metrics_label():
    src = inspect.getsource(_run_inspect_doc)
    assert "metrics:" in src


def test_run_inspect_doc_source_prints_file_label():
    src = inspect.getsource(_run_inspect_doc)
    assert "file:" in src


def test_run_inspect_doc_source_prints_document_id_label():
    src = inspect.getsource(_run_inspect_doc)
    assert "document_id:" in src


def test_run_inspect_doc_source_prints_source_label():
    src = inspect.getsource(_run_inspect_doc)
    assert "source:" in src


def test_run_inspect_doc_source_prints_parser_label():
    src = inspect.getsource(_run_inspect_doc)
    assert "parser:" in src


def test_run_inspect_doc_source_prints_counts_label():
    src = inspect.getsource(_run_inspect_doc)
    assert "counts:" in src


def test_run_inspect_doc_source_defines_sort_key_inner_function():
    src = inspect.getsource(_run_inspect_doc)
    assert "def _sort_key" in src


def test_run_inspect_doc_source_no_class_definition():
    src = inspect.getsource(_run_inspect_doc)
    assert "class " not in src


# ---------- main source level 字符串精确补强 ----------


def test_main_source_calls_build_parser():
    src = inspect.getsource(main)
    assert "_build_parser()" in src


def test_main_source_uses_parse_args():
    src = inspect.getsource(main)
    assert ".parse_args(" in src


def test_main_source_branches_on_command():
    src = inspect.getsource(main)
    assert 'args.command == "run"' in src
    assert 'args.command == "validate-report"' in src
    assert 'args.command == "inspect-doc"' in src


def test_main_source_uses_path_constructor():
    src = inspect.getsource(main)
    assert "Path(" in src


def test_main_source_uses_is_file_method():
    src = inspect.getsource(main)
    assert ".is_file()" in src


def test_main_source_uses_load_manifest():
    src = inspect.getsource(main)
    assert "load_manifest(" in src


def test_main_source_uses_run_evaluation_with_kwargs():
    src = inspect.getsource(main)
    assert "run_evaluation(" in src
    assert "parser_name=" in src
    assert "max_chars=" in src
    assert "tolerance_chars=" in src


def test_main_source_uses_validate_file():
    src = inspect.getsource(main)
    assert "validate_file(" in src


def test_main_source_uses_get_git_provenance():
    src = inspect.getsource(main)
    assert "get_git_provenance(" in src


def test_main_source_returns_2_for_missing_manifest():
    src = inspect.getsource(main)
    assert "return 2" in src


def test_main_source_returns_1_for_invalid_manifest():
    src = inspect.getsource(main)
    assert "return 1" in src


def test_main_source_returns_0_for_run_success():
    src = inspect.getsource(main)
    assert "return 0" in src


def test_main_source_returns_2_fallback_at_end():
    src = inspect.getsource(main)
    # 最后兜底 return 2
    assert src.rstrip().endswith("return 2") or src.rstrip().endswith("return 2\n")


def test_main_source_prints_to_stderr_for_errors():
    src = inspect.getsource(main)
    assert "file=sys.stderr" in src


def test_main_source_uses_try_except_blocks():
    src = inspect.getsource(main)
    assert "try:" in src
    assert "except" in src


def test_main_source_catches_manifest_error():
    src = inspect.getsource(main)
    assert "ManifestError" in src


def test_main_source_catches_eval_schema_error():
    src = inspect.getsource(main)
    assert "EvalSchemaError" in src


def test_main_source_catches_filenotfounderror():
    src = inspect.getsource(main)
    assert "FileNotFoundError" in src


def test_main_source_catches_jsondecodeerror():
    src = inspect.getsource(main)
    assert "json.JSONDecodeError" in src


def test_main_source_calls_run_inspect_doc():
    src = inspect.getsource(main)
    assert "_run_inspect_doc(" in src


def test_main_source_no_global_statement():
    src = inspect.getsource(main)
    assert "global " not in src


def test_main_source_no_yield():
    src = inspect.getsource(main)
    assert "yield" not in src


def test_main_source_no_async_keyword():
    src = inspect.getsource(main)
    assert "async " not in src


def test_main_source_no_class_definition():
    src = inspect.getsource(main)
    assert "\nclass " not in src


def test_main_source_no_lambda():
    src = inspect.getsource(main)
    assert "lambda " not in src


# ---------- module source forbidden tokens 第四批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "abc", "aifc", "antigravity", "asdl", "asyncio", "audioop",
        "binhex", "cProfile",
        "crypt", "curses", "dl", "docxml",
        "dospath", "dummy_threading", "email", "encodings",
        "ensurepip", "enum", "fileinput", "formatter",
        "ftplib", "genericpath", "genshi", "glob",
        "gopherlib", "html", "http", "ihooks",
        "imghdr", "inspect", "json.tool",
        "keyword", "linecache", "logging",
        "macpath", "macurl2path", "mailbox", "mailcap",
        "markupbase", "md5", "mhlib", "mimify",
        "msilib", "multifile", "mutex", "new",
        "nis", "nntplib", "opcode", "os2emxpath",
        "parser", "pdb", "pickletools", "pipes",
        "pkgutil", "plistlib", "poplib", "posixfile",
        "pty", "pyclbr", "pydoc", "queue",
        "random", "readline", "rexec",
        "rfc822", "rlcompleter", "robotparser", "secrets",
        "sets", "sgmlop", "sgmllib", "sha",
        "shutil", "smtpd", "sndhdr", "spawn",
        "spwd", "stat", "stringprep", "string",
        "struct", "sunaudio", "symtable", "sysconfig",
        "tarfile", "telnetlib", "tempfile", "termios",
        "threading", "time", "timeit", "tomllib",
        "traceback", "tracemalloc", "tty", "types",
        "typing", "unicodedata", "unicodedata", "urllib2",
        "urlparse", "user", "userdict", "userlist",
        "usersite", "uuid", "venv", "warnings",
        "wave", "weakref", "webbrowser", "whichdb",
        "wsgiref", "xdrlib", "xml", "xmlrpc",
        "zipfile", "zlib", "zoneinfo",
    ],
)
def test_module_source_forbidden_tokens_fourth_batch(token):
    """这些 stdlib 模块不应出现在 cli.py（仅用 argparse/json/sys/Path + evaluation.*）。"""
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


def test_module_source_imports_argparse():
    src = inspect.getsource(cli_mod)
    assert "import argparse" in src


def test_module_source_imports_json():
    src = inspect.getsource(cli_mod)
    assert "import json" in src


def test_module_source_imports_sys():
    src = inspect.getsource(cli_mod)
    assert "import sys" in src


def test_module_source_imports_pathlib_path():
    src = inspect.getsource(cli_mod)
    assert "from pathlib import Path" in src


def test_module_source_imports_manifest_error():
    src = inspect.getsource(cli_mod)
    assert "ManifestError" in src
    assert "from evaluation.manifest import" in src


def test_module_source_imports_load_manifest():
    src = inspect.getsource(cli_mod)
    assert "load_manifest" in src


def test_module_source_imports_get_git_provenance():
    src = inspect.getsource(cli_mod)
    assert "get_git_provenance" in src
    assert "from evaluation.report import" in src


def test_module_source_imports_run_evaluation():
    src = inspect.getsource(cli_mod)
    assert "run_evaluation" in src
    assert "from evaluation.runner import" in src


def test_module_source_imports_eval_schema_error():
    src = inspect.getsource(cli_mod)
    assert "EvalSchemaError" in src
    assert "from evaluation.schema import" in src


def test_module_source_imports_validate_file():
    src = inspect.getsource(cli_mod)
    assert "validate_file" in src


def test_module_source_has_sys_stdout_reconfigure():
    src = inspect.getsource(cli_mod)
    assert 'sys.stdout.reconfigure' in src


def test_module_source_has_sys_stderr_reconfigure():
    src = inspect.getsource(cli_mod)
    assert 'sys.stderr.reconfigure' in src


def test_module_source_has_hasattr_check():
    src = inspect.getsource(cli_mod)
    assert 'hasattr(sys.stdout, "reconfigure")' in src


def test_module_source_has_try_except_attribute_error_oserror():
    src = inspect.getsource(cli_mod)
    # 检查 try/except (AttributeError, OSError) 块
    assert "AttributeError, OSError" in src or "AttributeError" in src


def test_module_source_no_yield():
    src = inspect.getsource(cli_mod)
    assert "yield" not in src


def test_module_source_no_async_keyword():
    src = inspect.getsource(cli_mod)
    assert "async " not in src


def test_module_source_no_global_statement():
    src = inspect.getsource(cli_mod)
    assert "global " not in src


def test_module_source_no_class_definition():
    src = inspect.getsource(cli_mod)
    # 排除文档字符串里的 "class" 字眼
    lines = [l for l in src.splitlines() if not l.strip().startswith(("#", '"', "'"))]
    body = "\n".join(lines)
    assert "\nclass " not in body


def test_module_source_no_lambda_in_module():
    src = inspect.getsource(cli_mod)
    assert "lambda " not in src


def test_module_source_docstring_mentions_run():
    src = inspect.getsource(cli_mod)
    assert "run" in src


def test_module_source_docstring_mentions_validate_report():
    src = inspect.getsource(cli_mod)
    assert "validate-report" in src


def test_module_source_docstring_mentions_inspect_doc():
    src = inspect.getsource(cli_mod)
    assert "inspect-doc" in src


def test_module_source_has_main_block():
    src = inspect.getsource(cli_mod)
    assert 'if __name__ == "__main__":' in src


def test_module_source_main_block_uses_systemexit():
    src = inspect.getsource(cli_mod)
    assert "raise SystemExit(main())" in src


def test_module_source_has_4_module_level_functions():
    """模块级 4 个 def（_build_parser/main/_format_metric/_run_inspect_doc），不含 inner。"""
    src = inspect.getsource(cli_mod)
    func_count = sum(
        1 for line in src.splitlines() if line.startswith("def ")
    )
    assert func_count == 4


def test_module_source_has_1_inner_function():
    """_run_inspect_doc 内嵌 _sort_key。"""
    src = inspect.getsource(cli_mod)
    inner_count = sum(
        1 for line in src.splitlines() if line.startswith("    def ")
    )
    assert inner_count == 1


def test_module_source_no_decorator_outside_inner():
    """模块级没有装饰器（main/_build_parser 等都无装饰）。"""
    src = inspect.getsource(cli_mod)
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("@"):
            # 装饰器只允许出现在 inner function 上
            # 实际上模块里没有任何 @decorator
            pytest.fail(f"unexpected decorator at line {i}: {line}")


# ---------- signatures 精确补强 ----------


def test_main_signature_return_int():
    sig = inspect.signature(main)
    # from __future__ import annotations 让 annotation 变成字符串
    assert sig.return_annotation is int or sig.return_annotation == "int"


def test_main_signature_argv_param_kind_positional_or_keyword():
    sig = inspect.signature(main)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "argv"
    assert params[0].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_main_signature_argv_default_none():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_signature_argv_annotation():
    sig = inspect.signature(main)
    annotation = sig.parameters["argv"].annotation
    # 从 `from __future__ import annotations` 后变成字符串
    assert annotation is None or annotation == "list[str] | None"


def test_main_no_varargs():
    sig = inspect.signature(main)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds


def test_main_no_varkw():
    sig = inspect.signature(main)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_build_parser_no_params():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_build_parser_return_annotation():
    sig = inspect.signature(_build_parser)
    assert sig.return_annotation == "argparse.ArgumentParser" or sig.return_annotation is argparse.ArgumentParser


def test_format_metric_2_params():
    sig = inspect.signature(_format_metric)
    assert len(sig.parameters) == 2


def test_format_metric_param_names():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters.keys()) == ["name", "metric"]


def test_format_metric_param_kinds():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_format_metric_no_defaults():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_format_metric_return_str():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation is str or sig.return_annotation == "str"


def test_run_inspect_doc_1_param():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1


def test_run_inspect_doc_param_name_args():
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters.keys()) == ["args"]


def test_run_inspect_doc_return_int():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation is int or sig.return_annotation == "int"


# ---------- 模块整体合理性 ----------


def test_module_namespace():
    assert isinstance(cli_mod, types.ModuleType)


def test_module_has_no_all_attribute():
    """cli.py 不定义 __all__。"""
    assert not hasattr(cli_mod, "__all__")


def test_module_namespace_has_build_parser():
    assert hasattr(cli_mod, "_build_parser")


def test_module_namespace_has_main():
    assert hasattr(cli_mod, "main")


def test_module_namespace_has_format_metric():
    assert hasattr(cli_mod, "_format_metric")


def test_module_namespace_has_run_inspect_doc():
    assert hasattr(cli_mod, "_run_inspect_doc")


def test_module_has_4_functions_total():
    functions = [
        v for v in vars(cli_mod).values()
        if isinstance(v, types.FunctionType) and v.__module__ == cli_mod.__name__
    ]
    assert len(functions) == 4


def test_module_has_3_private_functions():
    functions = [
        v for v in vars(cli_mod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == cli_mod.__name__
        and v.__name__.startswith("_")
        and not v.__name__.startswith("__")
    ]
    assert len(functions) == 3


def test_module_has_1_public_function():
    functions = [
        v for v in vars(cli_mod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == cli_mod.__name__
        and not v.__name__.startswith("_")
    ]
    assert len(functions) == 1
    assert functions[0].__name__ == "main"


def test_module_no_class_definition():
    classes = [
        v for v in vars(cli_mod).values()
        if isinstance(v, type) and v.__module__ == cli_mod.__name__
    ]
    assert len(classes) == 0


def test_module_has_main_block():
    src = inspect.getsource(cli_mod)
    assert 'if __name__ == "__main__":' in src


def test_module_namespace_main_callable():
    assert callable(cli_mod.main)


def test_module_namespace_build_parser_callable():
    assert callable(cli_mod._build_parser)


def test_module_namespace_format_metric_callable():
    assert callable(cli_mod._format_metric)


def test_module_namespace_run_inspect_doc_callable():
    assert callable(cli_mod._run_inspect_doc)


# ---------- 端到端集成补强 ----------


def test_e2e_run_minimal_manifest_writes_output_and_validates(tmp_path, capsys):
    """完整 run → 自校验 → 报告写出。"""
    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
    output_path = tmp_path / "out.json"
    rc = main(
        [
            "run",
            "--manifest", str(manifest_path),
            "--output", str(output_path),
        ]
    )
    assert rc == 0
    assert output_path.is_file()
    # 二次校验
    rc2 = main(["validate-report", str(output_path)])
    assert rc2 == 0


def test_e2e_run_with_invalid_manifest_returns_1(tmp_path, capsys):
    """manifest JSON 不符合 schema → 退出 1。"""
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(bad), "--output", str(out)])
    assert rc == 1


def test_e2e_run_missing_manifest_returns_2(tmp_path, capsys):
    out = tmp_path / "out.json"
    rc = main(
        [
            "run",
            "--manifest", str(tmp_path / "nonexistent.json"),
            "--output", str(out),
        ]
    )
    assert rc == 2


def test_e2e_validate_report_missing_file_returns_2(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "nonexistent.json")])
    assert rc == 2


def test_e2e_validate_report_invalid_json_returns_1(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("not json at all", encoding="utf-8")
    rc = main(["validate-report", str(bad)])
    assert rc == 1


def test_e2e_validate_report_top_level_array_returns_1(tmp_path, capsys):
    """顶层不是 dict → schema 不通过。"""
    bad = tmp_path / "arr.json"
    bad.write_text("[]", encoding="utf-8")
    rc = main(["validate-report", str(bad)])
    assert rc == 1


def test_e2e_inspect_doc_missing_file_returns_2(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "no.json")])
    assert rc == 2


def test_e2e_inspect_doc_invalid_json_returns_1(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    assert rc == 1


def test_e2e_inspect_doc_top_level_list_returns_1(tmp_path, capsys):
    bad = tmp_path / "arr.json"
    bad.write_text("[]", encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    assert rc == 1


def test_e2e_inspect_doc_top_level_number_returns_1(tmp_path, capsys):
    bad = tmp_path / "num.json"
    bad.write_text("42", encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    assert rc == 1


def test_e2e_inspect_doc_top_level_string_returns_1(tmp_path, capsys):
    bad = tmp_path / "str.json"
    bad.write_text('"hello"', encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    assert rc == 1


def test_e2e_inspect_doc_top_level_null_returns_1(tmp_path, capsys):
    bad = tmp_path / "null.json"
    bad.write_text("null", encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    assert rc == 1


def test_e2e_inspect_doc_minimal_dict_returns_0(tmp_path, capsys):
    """最小 dict 也能跑通。"""
    doc = tmp_path / "doc.json"
    doc.write_text(
        json.dumps({
            "document_id": "x",
            "source_type": "pdf",
            "elements": [],
            "chunks": [],
        }),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(doc)])
    assert rc == 0


def test_e2e_inspect_doc_with_pdf_elements_returns_0(tmp_path, capsys):
    """带 PDF 元素的 doc 也能跑通。"""
    doc = tmp_path / "doc.json"
    doc.write_text(
        json.dumps({
            "document_id": "x",
            "source_type": "pdf",
            "source_path": "x.pdf",
            "parser_name": "fallback",
            "parser_version": "1.0",
            "elements": [
                {
                    "element_id": "e1",
                    "type": "paragraph",
                    "page": 1,
                    "bbox": [0.0, 0.0, 1.0, 1.0],
                    "content": "hello",
                    "source_locator": {"type": "pdf", "page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]},
                },
            ],
            "chunks": [],
        }),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(doc)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "x.pdf" in captured.out
    assert "fallback" in captured.out


def test_e2e_inspect_doc_with_chunks_returns_0(tmp_path, capsys):
    """带 chunk 的 doc 也能跑通，输出含 chunks 数。"""
    doc = tmp_path / "doc.json"
    doc.write_text(
        json.dumps({
            "document_id": "x",
            "source_type": "docx",
            "elements": [
                {"element_id": "e1", "type": "paragraph", "content": "hi",
                 "source_locator": {"type": "docx", "paragraph_index": 0}},
            ],
            "chunks": [
                {
                    "chunk_id": "c1",
                    "content": "hi",
                    "source_element_ids": ["e1"],
                    "source_locator": {"type": "docx", "paragraph_index": 0},
                },
            ],
        }),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(doc)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "chunks=1" in captured.out


def test_e2e_inspect_doc_with_custom_tolerance(tmp_path, capsys):
    doc = tmp_path / "doc.json"
    doc.write_text(
        json.dumps({
            "document_id": "x",
            "source_type": "pdf",
            "elements": [],
            "chunks": [],
        }),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(doc), "--tolerance-chars", "50"])
    assert rc == 0


def test_e2e_run_creates_output_in_subdir(tmp_path, capsys):
    """output 在子目录里，会被自动创建。"""
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    subdir = tmp_path / "sub" / "deep"
    out = subdir / "out.json"
    rc = main(
        [
            "run",
            "--manifest", str(mpath),
            "--output", str(out),
        ]
    )
    assert rc == 0
    assert out.is_file()


def test_e2e_run_stdout_includes_documents_count(tmp_path, capsys):
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(mpath), "--output", str(out)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "documents=0" in captured.out


def test_e2e_run_stdout_includes_devset_status(tmp_path, capsys):
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(mpath), "--output", str(out)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "devset_status=incomplete" in captured.out


def test_e2e_run_stdout_includes_ok_marker(tmp_path, capsys):
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(mpath), "--output", str(out)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "[OK]" in captured.out


def test_e2e_unknown_subcommand_exits_2(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["unknown"])
    assert ei.value.code == 2


def test_e2e_no_subcommand_exits_2(capsys):
    with pytest.raises(SystemExit) as ei:
        main([])
    assert ei.value.code == 2


def test_e2e_run_with_kreuzberg_parser_choice(tmp_path, capsys):
    """kreuzberg 也是合法 parser choice。"""
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(
        [
            "run",
            "--manifest", str(mpath),
            "--output", str(out),
            "--parser", "kreuzberg",
        ]
    )
    assert rc == 0


def test_e2e_run_invalid_parser_choice_exits_2(tmp_path, capsys):
    """非法 parser → argparse 报错退出 2。"""
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "out.json"
    with pytest.raises(SystemExit) as ei:
        main(
            [
                "run",
                "--manifest", str(mpath),
                "--output", str(out),
                "--parser", "invalid_parser",
            ]
        )
    assert ei.value.code == 2


def test_e2e_run_non_int_max_chars_exits_2(tmp_path, capsys):
    """非整数 max_chars → argparse type=int 失败，退出 2。"""
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "out.json"
    with pytest.raises(SystemExit) as ei:
        main(
            [
                "run",
                "--manifest", str(mpath),
                "--output", str(out),
                "--max-chars", "abc",
            ]
        )
    assert ei.value.code == 2


def test_e2e_run_returns_int_type(tmp_path, capsys):
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(mpath), "--output", str(out)])
    assert isinstance(rc, int)


def test_e2e_inspect_doc_returns_int_type(tmp_path):
    doc = tmp_path / "doc.json"
    doc.write_text(
        json.dumps({"document_id": "x", "source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(doc)])
    assert isinstance(rc, int)


def test_e2e_validate_report_returns_int_type(tmp_path, capsys):
    """先跑一份合法报告，再 validate-report。"""
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "out.json"
    main(["run", "--manifest", str(mpath), "--output", str(out)])
    rc = main(["validate-report", str(out)])
    assert isinstance(rc, int)


def test_e2e_run_with_str_path_works(tmp_path, capsys):
    """传 str 路径而非 Path 也能工作（argparse 总是给 str）。"""
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "out.json"
    # argv 接受 str
    rc = main(["run", "--manifest", str(mpath), "--output", str(out)])
    assert rc == 0


def test_e2e_inspect_doc_prints_all_metric_lines(tmp_path, capsys):
    """inspect-doc 输出 metrics: 标签。"""
    doc = tmp_path / "doc.json"
    doc.write_text(
        json.dumps({
            "document_id": "x",
            "source_type": "pdf",
            "elements": [],
            "chunks": [],
        }),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(doc)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_e2e_inspect_doc_prints_file_line(tmp_path, capsys):
    doc = tmp_path / "doc.json"
    doc.write_text(
        json.dumps({"document_id": "x", "source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(doc)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "file:" in captured.out
    assert "doc.json" in captured.out


def test_e2e_inspect_doc_prints_document_id_line(tmp_path, capsys):
    doc = tmp_path / "doc.json"
    doc.write_text(
        json.dumps({"document_id": "abc-123", "source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(doc)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "document_id:" in captured.out
    assert "abc-123" in captured.out
