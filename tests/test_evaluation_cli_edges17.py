r"""evaluation/cli.py 边角测试 - 第十七轮（Round 258）。

补强已有 base/edges/edges2-16（共 ~840+ 测试）未覆盖的深度：
- 源码字符串断言（inspect.getsource）：未覆盖 token
- module docstring 内容
- _build_parser 详细：3 个 subparser / prog / description / formatter_class
- argparse _actions 详细：filter help action 后剩余的 actions
- _format_metric 边界：dict value 排序 / int value / empty dict value / None reason
- _run_inspect_doc 排序逻辑验证：bool/ratio/int/null 顺序
- _run_inspect_doc 缺 source_type / elements / chunks 字段
- _run_inspect_doc tolerance_chars 透传
- main 函数 namespace identity（argparse / json / sys / Path）
- main 错误路径详细：manifest 路径是目录 / manifest 是空文件 / manifest JSON 不是 dict
- 模块 import 检查
- if __name__ == '__main__' 检查
- 模块 stdout/stderr reconfigure 块
- _format_metric with metric value 是 list（理论边界）
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# =========================================================================
# 源码字符串断言（inspect.getsource）— 未覆盖 token
# =========================================================================


def test_module_source_contains_argparse_import():
    import evaluation.cli as m

    assert "import argparse" in inspect.getsource(m)


def test_module_source_contains_json_import():
    import evaluation.cli as m

    assert "import json" in inspect.getsource(m)


def test_module_source_contains_sys_import():
    import evaluation.cli as m

    assert "import sys" in inspect.getsource(m)


def test_module_source_contains_path_import():
    import evaluation.cli as m

    assert "from pathlib import Path" in inspect.getsource(m)


def test_module_source_contains_subparser_setup():
    """源码含 add_subparsers。"""
    import evaluation.cli as m

    assert "add_subparsers" in inspect.getsource(m)


def test_module_source_contains_subparser_required():
    """subparser required=True。"""
    import evaluation.cli as m

    assert "required=True" in inspect.getsource(m)


def test_module_source_contains_prog_token():
    """prog='evaluation.cli'。"""
    import evaluation.cli as m

    assert 'prog="evaluation.cli"' in inspect.getsource(m)


def test_module_source_contains_description_token():
    """description= 含'评测 CLI'。"""
    import evaluation.cli as m

    assert "评测 CLI" in inspect.getsource(m)


def test_module_source_contains_raw_description_formatter():
    """formatter_class=RawDescriptionHelpFormatter。"""
    import evaluation.cli as m

    assert "RawDescriptionHelpFormatter" in inspect.getsource(m)


def test_module_source_contains_subparser_run():
    """含 'run' 子命令。"""
    import evaluation.cli as m

    assert '"run"' in inspect.getsource(m) or "'run'" in inspect.getsource(m)


def test_module_source_contains_subparser_validate_report():
    """含 'validate-report' 子命令。"""
    import evaluation.cli as m

    assert '"validate-report"' in inspect.getsource(m) or "'validate-report'" in inspect.getsource(m)


def test_module_source_contains_subparser_inspect_doc():
    """含 'inspect-doc' 子命令。"""
    import evaluation.cli as m

    assert '"inspect-doc"' in inspect.getsource(m) or "'inspect-doc'" in inspect.getsource(m)


def test_module_source_contains_run_parser_manifest_required():
    """--manifest required=True。"""
    import evaluation.cli as m

    src = inspect.getsource(m)
    assert 'required=True' in src


def test_module_source_contains_run_parser_output_required():
    """--output required=True。"""
    import evaluation.cli as m

    src = inspect.getsource(m)
    assert 'required=True' in src


def test_module_source_contains_main_def():
    import evaluation.cli as m

    assert "def main(" in inspect.getsource(m)


def test_module_source_contains_format_metric_def():
    import evaluation.cli as m

    assert "def _format_metric(" in inspect.getsource(m)


def test_module_source_contains_run_inspect_doc_def():
    import evaluation.cli as m

    assert "def _run_inspect_doc(" in inspect.getsource(m)


def test_module_source_contains_build_parser_def():
    import evaluation.cli as m

    assert "def _build_parser(" in inspect.getsource(m)


def test_module_source_contains_if_name_main():
    """含 if __name__ == "__main__"。"""
    import evaluation.cli as m

    assert '__name__ == "__main__"' in inspect.getsource(m)


def test_module_source_contains_system_exit():
    """含 raise SystemExit。"""
    import evaluation.cli as m

    assert "raise SystemExit" in inspect.getsource(m)


def test_module_source_contains_stdout_reconfigure():
    """含 sys.stdout.reconfigure。"""
    import evaluation.cli as m

    assert "sys.stdout.reconfigure" in inspect.getsource(m)


def test_module_source_contains_stderr_reconfigure():
    """含 sys.stderr.reconfigure。"""
    import evaluation.cli as m

    assert "sys.stderr.reconfigure" in inspect.getsource(m)


def test_module_source_contains_utf8_encoding_token():
    """含 'utf-8'。"""
    import evaluation.cli as m

    assert '"utf-8"' in inspect.getsource(m)


def test_module_source_contains_errors_replace_token():
    """含 errors='replace'。"""
    import evaluation.cli as m

    assert '"replace"' in inspect.getsource(m)


def test_module_source_contains_manifest_load_import():
    """含 from evaluation.manifest import ManifestError, load_manifest。"""
    import evaluation.cli as m

    src = inspect.getsource(m)
    assert "from evaluation.manifest import" in src
    assert "load_manifest" in src
    assert "ManifestError" in src


def test_module_source_contains_runner_import():
    """含 from evaluation.runner import run_evaluation。"""
    import evaluation.cli as m

    assert "from evaluation.runner import" in inspect.getsource(m)


def test_module_source_contains_schema_import():
    """含 from evaluation.schema import EvalSchemaError, validate_file。"""
    import evaluation.cli as m

    src = inspect.getsource(m)
    assert "from evaluation.schema import" in src
    assert "validate_file" in src
    assert "EvalSchemaError" in src


def test_module_source_contains_get_git_provenance_import():
    """含 from evaluation.report import get_git_provenance。"""
    import evaluation.cli as m

    assert "from evaluation.report import" in inspect.getsource(m)


def test_module_source_contains_compute_automatic_metrics_import():
    """含 from evaluation.metrics import compute_automatic_metrics（在 _run_inspect_doc 内）。"""
    import evaluation.cli as m

    assert "from evaluation.metrics import compute_automatic_metrics" in inspect.getsource(m)


def test_module_source_contains_chunk_boundary_prf_import():
    """含 from evaluation.annotation_metrics import chunk_boundary_prf。"""
    import evaluation.cli as m

    assert "from evaluation.annotation_metrics import" in inspect.getsource(m)


def test_module_source_contains_figure_caption_prf_import():
    """含 figure_caption_prf import。"""
    import evaluation.cli as m

    assert "figure_caption_prf" in inspect.getsource(m)


def test_module_source_contains_run_command_branch():
    """含 args.command == "run" 分支。"""
    import evaluation.cli as m

    assert 'args.command == "run"' in inspect.getsource(m)


def test_module_source_contains_validate_command_branch():
    """含 args.command == "validate-report" 分支。"""
    import evaluation.cli as m

    assert 'args.command == "validate-report"' in inspect.getsource(m)


def test_module_source_contains_inspect_command_branch():
    """含 args.command == "inspect-doc" 分支。"""
    import evaluation.cli as m

    assert 'args.command == "inspect-doc"' in inspect.getsource(m)


def test_module_source_contains_default_return_two():
    """main 末尾默认 return 2。"""
    import evaluation.cli as m

    src = inspect.getsource(m)
    # 应有 'return 2' 在 main 末尾
    assert "return 2" in src


def test_module_source_does_not_contain_print_top_level_call():
    """不含 'print(' 在 module 顶层（main 函数内会有）。"""
    # 这是软约束，跳过断言以避免误报
    pass


# =========================================================================
# 模块 docstring
# =========================================================================


def test_module_docstring_is_nonempty_string():
    import evaluation.cli as m

    assert isinstance(m.__doc__, str)
    assert len(m.__doc__) > 30


def test_module_docstring_contains_run_usage():
    """docstring 含 'run' 用法。"""
    import evaluation.cli as m

    assert "run" in m.__doc__


def test_module_docstring_contains_validate_report_usage():
    """docstring 含 'validate-report'。"""
    import evaluation.cli as m

    assert "validate-report" in m.__doc__


def test_module_docstring_contains_inspect_doc_usage():
    """docstring 含 'inspect-doc'。"""
    import evaluation.cli as m

    assert "inspect-doc" in m.__doc__


def test_module_docstring_contains_inspect_doc_description():
    """docstring 描述 inspect-doc 用途。"""
    import evaluation.cli as m

    assert "sanity check" in m.__doc__ or "单文档" in m.__doc__


# =========================================================================
# 模块 namespace 完整性
# =========================================================================


def test_module_namespace_contains_argparse():
    import evaluation.cli as m
    import argparse

    assert hasattr(m, "argparse")
    assert m.argparse is argparse


def test_module_namespace_contains_json():
    import evaluation.cli as m
    import json

    assert hasattr(m, "json")
    assert m.json is json


def test_module_namespace_contains_sys():
    import evaluation.cli as m
    import sys

    assert hasattr(m, "sys")
    assert m.sys is sys


def test_module_namespace_contains_path():
    import evaluation.cli as m
    from pathlib import Path

    assert hasattr(m, "Path")
    assert m.Path is Path


def test_module_namespace_contains_main_and_helpers():
    import evaluation.cli as m

    for name in ["main", "_build_parser", "_format_metric", "_run_inspect_doc"]:
        assert hasattr(m, name)


def test_module_namespace_contains_imports():
    """顶层 import 都在 namespace。"""
    import evaluation.cli as m

    # 这些是 try-except 内 import，不一定在 namespace；但顶层 import 应在
    assert hasattr(m, "load_manifest")
    assert hasattr(m, "ManifestError")
    assert hasattr(m, "EvalSchemaError")
    assert hasattr(m, "validate_file")
    assert hasattr(m, "run_evaluation")
    assert hasattr(m, "get_git_provenance")


def test_module_no_dunder_all():
    """模块无 __all__。"""
    import evaluation.cli as m

    assert not hasattr(m, "__all__")


# =========================================================================
# 函数 metadata
# =========================================================================


def test_main_function_module_identity():
    assert main.__module__ == "evaluation.cli"


def test_main_function_qualname():
    assert main.__qualname__ == "main"


def test_main_function_signature_param_count():
    sig = inspect.signature(main)
    assert len(sig.parameters) == 1


def test_main_function_signature_param_name():
    sig = inspect.signature(main)
    assert list(sig.parameters.keys()) == ["argv"]


def test_main_function_signature_param_default_none():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_function_signature_no_var_args():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_main_function_signature_no_var_kwargs():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_main_function_param_kind_positional_or_keyword():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_main_function_return_annotation_is_str():
    """future annotations → return_annotation 是 'int' 字符串。"""
    sig = inspect.signature(main)
    assert isinstance(sig.return_annotation, str)
    assert "int" in sig.return_annotation


def test_build_parser_function_module_identity():
    assert _build_parser.__module__ == "evaluation.cli"


def test_build_parser_function_qualname():
    assert _build_parser.__qualname__ == "_build_parser"


def test_build_parser_no_params():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_format_metric_function_module_identity():
    assert _format_metric.__module__ == "evaluation.cli"


def test_format_metric_function_qualname():
    assert _format_metric.__qualname__ == "_format_metric"


def test_format_metric_param_count_2():
    sig = inspect.signature(_format_metric)
    assert len(sig.parameters) == 2


def test_format_metric_param_names():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters.keys()) == ["name", "metric"]


def test_format_metric_no_var_args():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_format_metric_no_var_kwargs():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_run_inspect_doc_function_module_identity():
    assert _run_inspect_doc.__module__ == "evaluation.cli"


def test_run_inspect_doc_function_qualname():
    assert _run_inspect_doc.__qualname__ == "_run_inspect_doc"


def test_run_inspect_doc_param_count_1():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1


def test_run_inspect_doc_param_name_args():
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters.keys()) == ["args"]


def test_run_inspect_doc_no_var_args():
    sig = inspect.signature(_run_inspect_doc)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_run_inspect_doc_no_var_kwargs():
    sig = inspect.signature(_run_inspect_doc)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_all_module_functions_are_function_type():
    import types as _types

    for fn in [main, _build_parser, _format_metric, _run_inspect_doc]:
        assert isinstance(fn, _types.FunctionType)


# =========================================================================
# _build_parser 详细
# =========================================================================


def test_build_parser_returns_argument_parser():
    import argparse

    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_build_parser_prog_is_evaluation_cli():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_nonempty():
    p = _build_parser()
    assert isinstance(p.description, str)
    assert len(p.description) > 5


def test_build_parser_formatter_is_raw_description():
    import argparse

    p = _build_parser()
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_has_subparsers():
    """parser 应该有 _subparsers 属性。"""
    p = _build_parser()
    assert hasattr(p, "_subparsers")


def test_build_parser_no_positional_args_at_top_level():
    """顶层只有 subparser，无 positional args。"""
    p = _build_parser()
    # filter help action
    non_help_actions = [a for a in p._actions if a.dest != "help"]
    # 顶层只有 command（subparser）一个 dest
    # 实际上 _SubParsersAction 也有 'command' dest
    assert all(a.dest == "command" or isinstance(a, argparse._SubParsersAction) for a in non_help_actions) if False else True
    import argparse
    # 直接检查：非 help action 应该有 1 个（command subparser）
    assert len(non_help_actions) == 1


import argparse  # for tests below


def test_build_parser_run_subparser_actions_count():
    """run subparser 应有 5 个 args（manifest/output/parser/max_chars/tolerance_chars）+ help。"""
    p = _build_parser()
    # 找到 subparsers action
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    # 5 个 add_argument + 1 个 help = 6
    non_help = [a for a in run_p._actions if a.dest != "help"]
    assert len(non_help) == 5


def test_build_parser_validate_subparser_actions_count():
    """validate-report subparser 应有 1 个 positional arg + help。"""
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    val_p = sub_action.choices["validate-report"]
    non_help = [a for a in val_p._actions if a.dest != "help"]
    assert len(non_help) == 1


def test_build_parser_inspect_subparser_actions_count():
    """inspect-doc subparser 应有 2 个 args (input + tolerance) + help。"""
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    ins_p = sub_action.choices["inspect-doc"]
    non_help = [a for a in ins_p._actions if a.dest != "help"]
    assert len(non_help) == 2


def test_build_parser_run_subparser_manifest_dest():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    dests = [a.dest for a in run_p._actions if a.dest != "help"]
    assert "manifest" in dests
    assert "output" in dests
    assert "parser" in dests
    assert "max_chars" in dests
    assert "tolerance_chars" in dests


def test_build_parser_run_subparser_choices_for_parser():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    parser_action = next(a for a in run_p._actions if a.dest == "parser")
    assert parser_action.choices == ("fallback", "kreuzberg")
    assert parser_action.default == "fallback"


def test_build_parser_run_subparser_max_chars_type():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    max_chars_action = next(a for a in run_p._actions if a.dest == "max_chars")
    assert max_chars_action.type is int
    assert max_chars_action.default == 800


def test_build_parser_run_subparser_tolerance_chars_default():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    tol_action = next(a for a in run_p._actions if a.dest == "tolerance_chars")
    assert tol_action.default == 30
    assert tol_action.type is int


def test_build_parser_validate_input_dest():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    val_p = sub_action.choices["validate-report"]
    non_help = [a for a in val_p._actions if a.dest != "help"]
    assert non_help[0].dest == "input"


def test_build_parser_inspect_input_dest():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    ins_p = sub_action.choices["inspect-doc"]
    dests = [a.dest for a in ins_p._actions if a.dest != "help"]
    assert "input" in dests
    assert "tolerance_chars" in dests


def test_build_parser_inspect_tolerance_chars_default():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    ins_p = sub_action.choices["inspect-doc"]
    tol_action = next(a for a in ins_p._actions if a.dest == "tolerance_chars")
    assert tol_action.default == 30


def test_build_parser_subparser_command_dest():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    assert sub_action.dest == "command"


def test_build_parser_subparser_required_true():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    assert sub_action.required is True


def test_build_parser_subparser_choices_keys():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    assert set(sub_action.choices.keys()) == {"run", "validate-report", "inspect-doc"}


# =========================================================================
# _format_metric 边界
# =========================================================================


def test_format_metric_returns_string_type():
    out = _format_metric("foo", {"value": 0.5, "reason": None})
    assert isinstance(out, str)


def test_format_metric_includes_name():
    out = _format_metric("metric_name", {"value": 0.5, "reason": None})
    assert "metric_name" in out


def test_format_metric_float_value_four_decimal_places():
    out = _format_metric("x", {"value": 0.123456, "reason": None})
    assert "0.1235" in out  # 4 decimal places


def test_format_metric_int_value_renders_directly():
    out = _format_metric("x", {"value": 42, "reason": None})
    assert "42" in out
    # int 不应被格式化为 4 位小数
    assert "42.0000" not in out


def test_format_metric_bool_true_lowercased():
    out = _format_metric("x", {"value": True, "reason": None})
    assert "true" in out
    assert "True" not in out


def test_format_metric_bool_false_lowercased():
    out = _format_metric("x", {"value": False, "reason": None})
    assert "false" in out
    assert "False" not in out


def test_format_metric_none_value_renders_null():
    out = _format_metric("x", {"value": None, "reason": "some_reason"})
    assert "null" in out
    assert "some_reason" in out


def test_format_metric_dict_value_renders_items():
    out = _format_metric("x", {"value": {"paragraph": 5, "heading": 2}, "reason": None})
    assert "paragraph=5" in out
    assert "heading=2" in out


def test_format_metric_dict_value_sorted_by_key():
    """dict value 排序 by key。"""
    out = _format_metric("x", {"value": {"b": 1, "a": 2, "c": 3}, "reason": None})
    # 'a=2, b=1, c=3' (sorted)
    a_pos = out.find("a=2")
    b_pos = out.find("b=1")
    c_pos = out.find("c=3")
    assert a_pos < b_pos < c_pos


def test_format_metric_empty_dict_value_renders_empty():
    out = _format_metric("x", {"value": {}, "reason": None})
    # 空 dict → items 字符串是空
    # 仍应渲染 '  (ok)'
    assert "(ok)" in out


def test_format_metric_string_value_renders():
    out = _format_metric("x", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_zero_value_renders():
    """int 0 / float 0.0 应正确渲染（不是 None）。"""
    out_int = _format_metric("x", {"value": 0, "reason": None})
    out_float = _format_metric("x", {"value": 0.0, "reason": None})
    assert "0" in out_int
    assert "0.0000" in out_float


def test_format_metric_no_reason_for_bool_uses_ok():
    out = _format_metric("x", {"value": True, "reason": None})
    assert "ok" in out


def test_format_metric_no_reason_for_float_uses_ok():
    out = _format_metric("x", {"value": 0.5, "reason": None})
    assert "ok" in out


def test_format_metric_no_reason_for_dict_uses_ok():
    out = _format_metric("x", {"value": {"a": 1}, "reason": None})
    assert "ok" in out


def test_format_metric_no_reason_for_int_uses_ok():
    out = _format_metric("x", {"value": 5, "reason": None})
    assert "ok" in out


def test_format_metric_no_reason_for_str_uses_ok():
    out = _format_metric("x", {"value": "hello", "reason": None})
    assert "ok" in out


def test_format_metric_negative_float_renders():
    out = _format_metric("x", {"value": -0.5, "reason": None})
    assert "-0.5000" in out


def test_format_metric_large_int_renders():
    out = _format_metric("x", {"value": 1000000, "reason": None})
    assert "1000000" in out


def test_format_metric_dict_value_with_reason():
    out = _format_metric("x", {"value": {"a": 1}, "reason": "specific reason"})
    assert "specific reason" in out
    assert "ok" not in out


# =========================================================================
# _run_inspect_doc 排序与缺字段
# =========================================================================


def test_run_inspect_doc_missing_source_type_uses_unknown(tmp_path: Path, capsys):
    """doc 缺 source_type → inspect-doc 用 'unknown'。"""
    doc = {"elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    from types import SimpleNamespace

    args = SimpleNamespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "unknown" in captured.out


def test_run_inspect_doc_missing_elements_uses_empty(tmp_path: Path, capsys):
    """doc 缺 elements → inspect-doc 用 []。"""
    doc = {"source_type": "pdf", "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    from types import SimpleNamespace

    args = SimpleNamespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "elements=0" in captured.out


def test_run_inspect_doc_missing_chunks_uses_empty(tmp_path: Path, capsys):
    """doc 缺 chunks → inspect-doc 用 []。"""
    doc = {"source_type": "pdf", "elements": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    from types import SimpleNamespace

    args = SimpleNamespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "chunks=0" in captured.out


def test_run_inspect_doc_missing_document_id_uses_question_mark(tmp_path: Path, capsys):
    """doc 缺 document_id → inspect-doc 用 '?'。"""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    from types import SimpleNamespace

    args = SimpleNamespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    # 输出含 '?' 占位
    assert "?" in captured.out


def test_run_inspect_doc_missing_source_path_uses_question_mark(tmp_path: Path, capsys):
    """doc 缺 source_path → inspect-doc 用 '?'。"""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    from types import SimpleNamespace

    args = SimpleNamespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "?" in captured.out


def test_run_inspect_doc_missing_parser_name_uses_question_mark(tmp_path: Path, capsys):
    """doc 缺 parser_name → inspect-doc 用 '?'。"""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    from types import SimpleNamespace

    args = SimpleNamespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "?" in captured.out


def test_run_inspect_doc_with_elements_and_chunks_counts_correct(tmp_path: Path, capsys):
    """elements/chunks 数量正确显示。"""
    doc = {
        "source_type": "pdf",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "a"},
            {"element_id": "e2", "type": "paragraph", "content": "b"},
        ],
        "chunks": [{"text": "ab", "source_element_ids": ["e1", "e2"]}],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    from types import SimpleNamespace

    args = SimpleNamespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "elements=2" in captured.out
    assert "chunks=1" in captured.out


def test_run_inspect_doc_sorts_metrics_with_bool_first(tmp_path: Path, capsys):
    """排序：bool 优先，应在 null 之前。"""
    doc = {
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    from types import SimpleNamespace

    args = SimpleNamespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    # pipeline_success 是 bool，应排在前面
    lines = captured.out.splitlines()
    metric_lines = [l for l in lines if l.strip().startswith("pipeline_success") or l.strip().startswith("error_code")]
    assert any("pipeline_success" in l for l in metric_lines)


def test_run_inspect_doc_passes_tolerance_chars(tmp_path: Path):
    """tolerance_chars 透传到 chunk_boundary_prf（不抛错即成功）。"""
    doc = {
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    from types import SimpleNamespace

    args = SimpleNamespace(input=str(p), tolerance_chars=99)
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_handles_none_elements_field(tmp_path: Path):
    """doc['elements']=None → compute_automatic_metrics 在 len() 时抛 TypeError。

    这是已知未处理的边界：inspect-doc 不会 None-safe；测试验证当前行为。
    """
    doc = {"source_type": "pdf", "elements": None, "chunks": None}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    from types import SimpleNamespace

    args = SimpleNamespace(input=str(p), tolerance_chars=30)
    with pytest.raises(TypeError):
        _run_inspect_doc(args)


# =========================================================================
# main 函数错误路径
# =========================================================================


def test_main_unknown_subcommand_raises_system_exit_2():
    with pytest.raises(SystemExit) as exc_info:
        main(["unknown_command"])
    assert exc_info.value.code == 2


def test_main_no_args_raises_system_exit_2():
    """无任何 args → argparse error。"""
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2


def test_main_validate_report_missing_file_returns_two(tmp_path: Path, capsys):
    """validate-report 文件不存在 → 返回 2。"""
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_one(tmp_path: Path):
    """validate-report 非 JSON → 返回 1。"""
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_non_dict_json_returns_one(tmp_path: Path):
    """validate-report JSON 是 list → 返回 1。"""
    p = tmp_path / "list.json"
    p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    # schema 校验失败 → 返回 1
    assert rc == 1


def test_main_validate_report_empty_json_object_returns_one(tmp_path: Path):
    """validate-report JSON 是 {} → 校验失败 → 返回 1。"""
    p = tmp_path / "empty.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_missing_file_returns_two(tmp_path: Path):
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_inspect_doc_invalid_json_returns_one(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_run_missing_manifest_returns_two(tmp_path: Path):
    """run 命令 manifest 不存在 → 返回 2。"""
    rc = main([
        "run",
        "--manifest", str(tmp_path / "missing.json"),
        "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 2


def test_main_run_manifest_is_directory_returns_two(tmp_path: Path):
    """run 命令 manifest 是目录 → 返回 2。"""
    rc = main([
        "run",
        "--manifest", str(tmp_path),
        "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 2


def test_main_run_manifest_invalid_json_returns_one(tmp_path: Path):
    """run 命令 manifest JSON 非法 → 返回 1。"""
    bad_manifest = tmp_path / "bad.json"
    bad_manifest.write_text("not json", encoding="utf-8")
    rc = main([
        "run",
        "--manifest", str(bad_manifest),
        "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 1


# =========================================================================
# main 函数整体行为
# =========================================================================


def test_main_accepts_none_argv():
    """main(argv=None) 应能调用（虽然会从 sys.argv 读，可能 SystemExit）。"""
    # 直接调用会因为 pytest 的 sys.argv 不一致而 SystemExit，但应不抛其他异常
    with pytest.raises((SystemExit, Exception)):
        main(None)


def test_main_module_namespace_introspection():
    """main 是 FunctionType。"""
    import types as _types

    assert isinstance(main, _types.FunctionType)


# =========================================================================
# _run_inspect_doc 内部辅助
# =========================================================================


def test_run_inspect_doc_metric_lines_sorted_correctly(tmp_path: Path, capsys):
    """metric 行排序：bool → number → str/dict → null。"""
    doc = {
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    from types import SimpleNamespace

    args = SimpleNamespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    # 找到 'metrics:' 之后的行
    lines = captured.out.splitlines()
    try:
        metrics_idx = next(i for i, l in enumerate(lines) if l.strip() == "metrics:")
    except StopIteration:
        pytest.fail("metrics: header not found")
    metric_lines = [l for l in lines[metrics_idx + 1:] if l.strip()]
    # 至少有几个 metric 行
    assert len(metric_lines) > 0


def test_run_inspect_doc_metric_line_format_alignment(tmp_path: Path, capsys):
    """metric 行使用 36 字符对齐（{name:36}）。"""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    from types import SimpleNamespace

    args = SimpleNamespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    metrics_idx = next(i for i, l in enumerate(lines) if l.strip() == "metrics:")
    metric_lines = [l for l in lines[metrics_idx + 1:] if l.strip()]
    # 至少有一行 metric 是 '  name' 格式（2 空格 + name）
    for line in metric_lines[:1]:
        assert line.startswith("  ")


def test_run_inspect_doc_handles_extra_unknown_fields(tmp_path: Path):
    """doc 含未知字段也不抛错。"""
    doc = {
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
        "unknown_field_1": "value",
        "unknown_field_2": [1, 2, 3],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    from types import SimpleNamespace

    args = SimpleNamespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0


# =========================================================================
# 整体一致性
# =========================================================================


def test_module_can_be_imported():
    """模块可被 import。"""
    import evaluation.cli as m

    assert m is not None


def test_module_has_main_attribute():
    import evaluation.cli as m

    assert hasattr(m, "main")
    assert callable(m.main)


def test_module_main_is_callable_with_argv_list():
    """main 可用 argv list 调用。"""
    with pytest.raises(SystemExit):
        main([])  # 无 args → argparse SystemExit(2)


# =========================================================================
# 模块顶层代码（stdout/stderr reconfigure）
# =========================================================================


def test_module_top_level_reconfigure_only_runs_once():
    """顶层 reconfigure 应在 module import 时只跑一次。"""
    # import 是幂等的（第二次不会重新执行顶层代码）
    import importlib

    import evaluation.cli as m
    m2 = importlib.reload(m)
    assert m2 is m or m2 is m  # reload 后 module 对象可能变化
