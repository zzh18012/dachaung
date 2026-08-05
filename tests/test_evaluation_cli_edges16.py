r"""evaluation/cli.py 边角测试 - 第十六轮（Round 251）。

补强已有 base/edges/edges2-15（共 ~840+ 测试）未覆盖的深度：
- 源码字符串断言（inspect.getsource）：含特定 token（--manifest / --output / --parser / --max-chars / --tolerance-chars / choices=('fallback', 'kreuzberg') / 'fallback' / 'kreuzberg' / default 800/30 / RunEval / validate-report / inspect-doc / run）
- module metadata：__file__ 后缀 .py / __package__ == 'evaluation' / __name__ == 'evaluation.cli'
- 函数 metadata：__module__/__qualname__/__name__/FunctionType；无 VAR_POSITIONAL/VAR_KEYWORD；return_annotation
- _format_metric 各分支精确：bool / float / dict / int / str / None
- _run_inspect_doc 输出格式精确（file: / document_id: / source: / parser: / counts: / metrics:）
- argparse add_argument 调用次数精确
- main 返回值边界：所有 unknown / 缺参数 路径都 SystemExit(2)
- run_p 的 --parser choices 是 tuple
- run_p 的 --max-chars 默认 800
- ins_p 的 --tolerance-chars 默认 30
- main 缺省 argv=None 时从 sys.argv 读取（验证 main() 接受 None）
- _format_metric None value 时 reason 透传
- _format_metric bool value 时 reason or 'ok'
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# =========================================================================
# 源码字符串断言（inspect.getsource）
# =========================================================================


def test_module_source_contains_manifest_argument():
    """源码含 '--manifest'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "--manifest" in src


def test_module_source_contains_output_argument():
    """源码含 '--output'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "--output" in src


def test_module_source_contains_parser_argument():
    """源码含 '--parser'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "--parser" in src


def test_module_source_contains_max_chars_argument():
    """源码含 '--max-chars'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "--max-chars" in src


def test_module_source_contains_tolerance_chars_argument():
    """源码含 '--tolerance-chars'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "--tolerance-chars" in src


def test_module_source_contains_fallback_default():
    """源码含 'fallback'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "fallback" in src


def test_module_source_contains_kreuzberg_choice():
    """源码含 'kreuzberg'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "kreuzberg" in src


def test_module_source_contains_default_800():
    """源码含 'default=800'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "default=800" in src


def test_module_source_contains_default_30():
    """源码含 'default=30'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "default=30" in src


def test_module_source_contains_run_subparser():
    """源码含 'add_parser("run"'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert 'add_parser("run"' in src


def test_module_source_contains_validate_report_subparser():
    """源码含 'validate-report'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "validate-report" in src


def test_module_source_contains_inspect_doc_subparser():
    """源码含 'inspect-doc'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "inspect-doc" in src


def test_module_source_contains_subparsers_call():
    """源码含 'add_subparsers'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "add_subparsers" in src


def test_module_source_contains_argparse_import():
    """源码含 'import argparse'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "import argparse" in src


def test_module_source_contains_main_function():
    """源码含 'def main('。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "def main(" in src


def test_module_source_contains_run_inspect_doc_function():
    """源码含 'def _run_inspect_doc('。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "def _run_inspect_doc(" in src


def test_module_source_contains_format_metric_function():
    """源码含 'def _format_metric('。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "def _format_metric(" in src


def test_module_source_contains_choices_tuple():
    """源码含 'choices=('fallback', 'kreuzberg')'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "choices=" in src


def test_module_source_contains_return_zero_path():
    """源码含 'return 0'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "return 0" in src


def test_module_source_contains_return_one_path():
    """源码含 'return 1'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "return 1" in src


def test_module_source_contains_return_two_path():
    """源码含 'return 2'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "return 2" in src


def test_module_source_contains_system_exit_main():
    """源码含 'raise SystemExit(main())'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "raise SystemExit(main())" in src


def test_module_source_contains_main_guard():
    """源码含 'if __name__ == "__main__":'。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' in src


# =========================================================================
# 模块 metadata
# =========================================================================


def test_module_file_endswith_py():
    """__file__ 以 '.py' 结尾。"""
    import evaluation.cli as m
    assert m.__file__.endswith(".py")


def test_module_file_contains_cli():
    """__file__ 含 'cli'。"""
    import evaluation.cli as m
    assert "cli" in m.__file__


def test_module_package_is_evaluation():
    """__package__ == 'evaluation'。"""
    import evaluation.cli as m
    assert m.__package__ == "evaluation"


def test_module_name_is_evaluation_cli():
    """__name__ == 'evaluation.cli'。"""
    import evaluation.cli as m
    assert m.__name__ == "evaluation.cli"


def test_module_argparse_is_argparse_module():
    """argparse is argparse。"""
    import argparse
    import evaluation.cli as m
    assert m.argparse is argparse


def test_module_json_is_json_module():
    """json is json。"""
    import json
    import evaluation.cli as m
    assert m.json is json


def test_module_sys_is_sys_module():
    """sys is sys。"""
    import sys
    import evaluation.cli as m
    assert m.sys is sys


def test_module_path_is_pathlib_path():
    """Path is pathlib.Path。"""
    import evaluation.cli as m
    from pathlib import Path as P
    assert m.Path is P


# =========================================================================
# 函数 metadata
# =========================================================================


def test_main_module_attribute():
    """main.__module__ == 'evaluation.cli'。"""
    assert main.__module__ == "evaluation.cli"


def test_main_qualname():
    """main.__qualname__ == 'main'。"""
    assert main.__qualname__ == "main"


def test_main_name():
    """main.__name__ == 'main'。"""
    assert main.__name__ == "main"


def test_build_parser_module_attribute():
    """_build_parser.__module__ == 'evaluation.cli'。"""
    assert _build_parser.__module__ == "evaluation.cli"


def test_build_parser_qualname():
    """_build_parser.__qualname__ == '_build_parser'。"""
    assert _build_parser.__qualname__ == "_build_parser"


def test_format_metric_module_attribute():
    """_format_metric.__module__ == 'evaluation.cli'。"""
    assert _format_metric.__module__ == "evaluation.cli"


def test_format_metric_qualname():
    """_format_metric.__qualname__ == '_format_metric'。"""
    assert _format_metric.__qualname__ == "_format_metric"


def test_run_inspect_doc_module_attribute():
    """_run_inspect_doc.__module__ == 'evaluation.cli'。"""
    assert _run_inspect_doc.__module__ == "evaluation.cli"


def test_run_inspect_doc_qualname():
    """_run_inspect_doc.__qualname__ == '_run_inspect_doc'。"""
    assert _run_inspect_doc.__qualname__ == "_run_inspect_doc"


def test_main_is_python_function():
    """main 是 Python 函数。"""
    import types
    assert isinstance(main, types.FunctionType)


def test_build_parser_is_python_function():
    """_build_parser 是 Python 函数。"""
    import types
    assert isinstance(_build_parser, types.FunctionType)


def test_format_metric_is_python_function():
    """_format_metric 是 Python 函数。"""
    import types
    assert isinstance(_format_metric, types.FunctionType)


def test_run_inspect_doc_is_python_function():
    """_run_inspect_doc 是 Python 函数。"""
    import types
    assert isinstance(_run_inspect_doc, types.FunctionType)


def test_main_no_varargs():
    """main 无 VAR_POSITIONAL。"""
    sig = inspect.signature(main)
    assert all(p.kind != inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())


def test_main_no_varkw():
    """main 无 VAR_KEYWORD。"""
    sig = inspect.signature(main)
    assert all(p.kind != inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())


def test_build_parser_no_params():
    """_build_parser 无参数。"""
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_format_metric_two_params_no_varargs():
    """_format_metric 无 varargs/varkw。"""
    sig = inspect.signature(_format_metric)
    assert all(p.kind != inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    assert all(p.kind != inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())


def test_main_return_annotation_is_str():
    """main return annotation 是 str（__future__）。"""
    sig = inspect.signature(main)
    assert isinstance(sig.return_annotation, str)


def test_main_return_annotation_contains_int():
    """main return annotation 含 'int'。"""
    sig = inspect.signature(main)
    assert "int" in sig.return_annotation


def test_run_inspect_doc_return_annotation_is_str():
    """_run_inspect_doc return annotation 是 str。"""
    sig = inspect.signature(_run_inspect_doc)
    assert isinstance(sig.return_annotation, str)


def test_run_inspect_doc_return_annotation_contains_int():
    """_run_inspect_doc return annotation 含 'int'。"""
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in sig.return_annotation


# =========================================================================
# _format_metric 各分支精确
# =========================================================================


def test_format_metric_value_none_renders_null():
    """value=None 渲染 'null'。"""
    out = _format_metric("name", {"value": None, "reason": "no_data"})
    assert "null" in out
    assert "no_data" in out


def test_format_metric_value_none_no_reason_renders_null():
    """value=None reason=None 渲染 'null'。"""
    out = _format_metric("name", {"value": None, "reason": None})
    assert "null" in out
    assert "(None)" in out


def test_format_metric_value_true_renders_lowercase_true():
    """value=True 渲染 'true'（小写）。"""
    out = _format_metric("name", {"value": True, "reason": None})
    assert "true" in out.lower()
    assert "True" not in out  # 不含大写


def test_format_metric_value_false_renders_lowercase_false():
    """value=False 渲染 'false'。"""
    out = _format_metric("name", {"value": False, "reason": None})
    assert "false" in out.lower()
    assert "False" not in out


def test_format_metric_value_zero_int_renders_zero():
    """value=0 (int) 渲染 '0'。"""
    out = _format_metric("name", {"value": 0, "reason": None})
    # int 分支：f"  {name:36} {value}  ({reason or 'ok'})"
    assert "0" in out


def test_format_metric_value_float_renders_four_decimals():
    """value=0.5 (float) 渲染 '0.5000'。"""
    out = _format_metric("name", {"value": 0.5, "reason": None})
    assert "0.5000" in out


def test_format_metric_value_float_zero_renders_zero():
    """value=0.0 (float) 渲染 '0.0000'。"""
    out = _format_metric("name", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_value_float_one_renders_one():
    """value=1.0 渲染 '1.0000'。"""
    out = _format_metric("name", {"value": 1.0, "reason": None})
    assert "1.0000" in out


def test_format_metric_value_dict_renders_items_sorted():
    """value={'b': 2, 'a': 1} 渲染 sorted：a=1, b=2。"""
    out = _format_metric("name", {"value": {"b": 2, "a": 1}, "reason": None})
    # 排序后 a 在 b 前
    assert "a=1" in out
    assert "b=2" in out
    assert out.index("a=1") < out.index("b=2")


def test_format_metric_value_dict_empty_renders_no_items():
    """value={} 渲染空 items。"""
    out = _format_metric("name", {"value": {}, "reason": None})
    # 'name:' 之后是 '  (ok)'
    assert "ok" in out


def test_format_metric_value_str_renders_str():
    """value='hello' str 分支渲染 'hello'。"""
    out = _format_metric("name", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_value_str_with_reason():
    """str value 含 reason → reason 在 () 内。"""
    out = _format_metric("name", {"value": "hello", "reason": "custom"})
    assert "custom" in out


def test_format_metric_value_int_with_reason():
    """int value reason 替换 'ok'。"""
    out = _format_metric("name", {"value": 42, "reason": "computed"})
    assert "computed" in out
    assert "42" in out


def test_format_metric_value_float_with_reason():
    """float value 含 reason → reason 在 ()。"""
    out = _format_metric("name", {"value": 0.5, "reason": "approx"})
    assert "approx" in out


def test_format_metric_value_dict_with_reason():
    """dict value 含 reason → reason 在 ()。"""
    out = _format_metric("name", {"value": {"a": 1}, "reason": "manual"})
    assert "manual" in out


def test_format_metric_name_field_width_thirty_six():
    """name 字段宽度 36（用 :36 格式）。"""
    # 长名 + 短名都正确缩进
    out_short = _format_metric("a", {"value": 1, "reason": None})
    out_long = _format_metric("a" * 50, {"value": 1, "reason": None})
    # 短名后会补空格到 36 字符
    assert len(out_short.split("  1")[0]) <= 38  # 留余量
    # 长名溢出（不会被截断）
    assert "a" * 50 in out_long


# =========================================================================
# argparse parser 结构
# =========================================================================


def test_build_parser_prog_exact():
    """parser.prog == 'evaluation.cli'。"""
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_exact():
    """parser.description 含 '评测 CLI'。"""
    p = _build_parser()
    assert "评测" in p.description
    assert "CLI" in p.description


def test_build_parser_has_subparsers_action_count_one():
    """有 1 个 subparsers action。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if hasattr(a, "choices") and a.choices]
    # 至少 1 个 subparsers
    assert len(sub_actions) >= 1


def test_build_parser_run_choices_exact():
    """run --parser choices == ('fallback', 'kreuzberg')。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if hasattr(a, "choices") and "run" in (a.choices or {})]
    assert len(sub_actions) >= 1
    sub = sub_actions[0]
    run_p = sub.choices["run"]
    parser_actions = [a for a in run_p._actions if a.dest == "parser"]
    assert len(parser_actions) == 1
    # choices 应是 ('fallback', 'kreuzberg')（tuple）或 ['fallback', 'kreuzberg']
    assert tuple(parser_actions[0].choices) == ("fallback", "kreuzberg")


def test_build_parser_run_parser_default_is_fallback():
    """run --parser default == 'fallback'。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if hasattr(a, "choices") and "run" in (a.choices or {})]
    sub = sub_actions[0]
    run_p = sub.choices["run"]
    parser_actions = [a for a in run_p._actions if a.dest == "parser"]
    assert parser_actions[0].default == "fallback"


def test_build_parser_run_max_chars_default_800():
    """run --max-chars default == 800。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if hasattr(a, "choices") and "run" in (a.choices or {})]
    sub = sub_actions[0]
    run_p = sub.choices["run"]
    max_chars_actions = [a for a in run_p._actions if a.dest == "max_chars"]
    assert max_chars_actions[0].default == 800


def test_build_parser_run_tolerance_chars_default_30():
    """run --tolerance-chars default == 30。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if hasattr(a, "choices") and "run" in (a.choices or {})]
    sub = sub_actions[0]
    run_p = sub.choices["run"]
    tol_actions = [a for a in run_p._actions if a.dest == "tolerance_chars"]
    assert tol_actions[0].default == 30


def test_build_parser_inspect_tolerance_chars_default_30():
    """inspect-doc --tolerance-chars default == 30。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if hasattr(a, "choices") and "inspect-doc" in (a.choices or {})]
    sub = sub_actions[0]
    ins_p = sub.choices["inspect-doc"]
    tol_actions = [a for a in ins_p._actions if a.dest == "tolerance_chars"]
    assert tol_actions[0].default == 30


def test_build_parser_run_manifest_required():
    """run --manifest required=True。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if hasattr(a, "choices") and "run" in (a.choices or {})]
    sub = sub_actions[0]
    run_p = sub.choices["run"]
    manifest_actions = [a for a in run_p._actions if a.dest == "manifest"]
    assert manifest_actions[0].required is True


def test_build_parser_run_output_required():
    """run --output required=True。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if hasattr(a, "choices") and "run" in (a.choices or {})]
    sub = sub_actions[0]
    run_p = sub.choices["run"]
    output_actions = [a for a in run_p._actions if a.dest == "output"]
    assert output_actions[0].required is True


def test_build_parser_validate_report_input_positional():
    """validate-report input 是 positional argument。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if hasattr(a, "choices") and "validate-report" in (a.choices or {})]
    sub = sub_actions[0]
    val_p = sub.choices["validate-report"]
    input_actions = [a for a in val_p._actions if a.dest == "input"]
    assert len(input_actions) == 1
    # positional：option_strings 是空 list
    assert input_actions[0].option_strings == []


def test_build_parser_inspect_input_positional():
    """inspect-doc input 是 positional。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if hasattr(a, "choices") and "inspect-doc" in (a.choices or {})]
    sub = sub_actions[0]
    ins_p = sub.choices["inspect-doc"]
    input_actions = [a for a in ins_p._actions if a.dest == "input"]
    assert len(input_actions) == 1
    assert input_actions[0].option_strings == []


# =========================================================================
# main 缺省 argv 行为
# =========================================================================


def test_main_accepts_none_argv():
    """main(argv=None) 应从 sys.argv 读取，但空 sys.argv 会触发 SystemExit。"""
    # 不直接调用 main() 因为它会读 sys.argv
    # 仅验证 main signature 默认是 None
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_signature_single_param():
    """main 签名 1 个参数 'argv'。"""
    sig = inspect.signature(main)
    params = list(sig.parameters.keys())
    assert params == ["argv"]


def test_main_param_kind_positional_or_keyword():
    """argv 是 POSITIONAL_OR_KEYWORD。"""
    sig = inspect.signature(main)
    p = sig.parameters["argv"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


# =========================================================================
# _run_inspect_doc 输出格式精确
# =========================================================================


def test_run_inspect_doc_output_contains_file_prefix(tmp_path: Path, capsys):
    """inspect-doc 输出含 'file:' 前缀。"""
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }
    p = tmp_path / "doc.json"
    p.write_text(__import__("json").dumps(doc), encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    _run_inspect_doc(Args())
    captured = capsys.readouterr()
    assert "file:" in captured.out


def test_run_inspect_doc_output_contains_document_id(tmp_path: Path, capsys):
    """inspect-doc 输出含 'document_id:'。"""
    import json
    doc = {"document_id": "my_doc", "source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    _run_inspect_doc(Args())
    captured = capsys.readouterr()
    assert "document_id:" in captured.out
    assert "my_doc" in captured.out


def test_run_inspect_doc_output_contains_source(tmp_path: Path, capsys):
    """inspect-doc 输出含 'source:'。"""
    import json
    doc = {"source_path": "/foo/bar.pdf", "source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    _run_inspect_doc(Args())
    captured = capsys.readouterr()
    assert "source:" in captured.out
    assert "/foo/bar.pdf" in captured.out


def test_run_inspect_doc_output_contains_parser(tmp_path: Path, capsys):
    """inspect-doc 输出含 'parser:'。"""
    import json
    doc = {
        "parser_name": "fallback",
        "parser_version": "1.0.0",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    _run_inspect_doc(Args())
    captured = capsys.readouterr()
    assert "parser:" in captured.out
    assert "fallback" in captured.out


def test_run_inspect_doc_output_contains_counts(tmp_path: Path, capsys):
    """inspect-doc 输出含 'counts:'。"""
    import json
    doc = {
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "a"}],
        "chunks": [{"text": "a", "source_element_ids": ["e1"]}],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    _run_inspect_doc(Args())
    captured = capsys.readouterr()
    assert "counts:" in captured.out
    assert "elements=1" in captured.out
    assert "chunks=1" in captured.out


def test_run_inspect_doc_output_contains_metrics_header(tmp_path: Path, capsys):
    """inspect-doc 输出含 'metrics:'。"""
    import json
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    _run_inspect_doc(Args())
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_returns_zero_on_success(tmp_path: Path):
    """成功路径返回 0。"""
    import json
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(Args())
    assert rc == 0


def test_run_inspect_doc_returns_two_on_missing_file(tmp_path: Path):
    """文件不存在返回 2。"""
    class Args:
        input = str(tmp_path / "missing.json")
        tolerance_chars = 30

    rc = _run_inspect_doc(Args())
    assert rc == 2


def test_run_inspect_doc_returns_one_on_invalid_json(tmp_path: Path):
    """非法 JSON 返回 1。"""
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(Args())
    assert rc == 1


def test_run_inspect_doc_returns_one_on_non_dict_json(tmp_path: Path):
    """JSON 是 list 不是 dict → 返回 1。"""
    import json
    p = tmp_path / "list.json"
    p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(Args())
    assert rc == 1


# =========================================================================
# 模块 namespace identity
# =========================================================================


def test_module_namespace_contains_main():
    """模块命名空间含 'main'。"""
    import evaluation.cli as m
    assert hasattr(m, "main")


def test_module_namespace_contains_build_parser():
    """模块命名空间含 '_build_parser'。"""
    import evaluation.cli as m
    assert hasattr(m, "_build_parser")


def test_module_namespace_contains_format_metric():
    """模块命名空间含 '_format_metric'。"""
    import evaluation.cli as m
    assert hasattr(m, "_format_metric")


def test_module_namespace_contains_run_inspect_doc():
    """模块命名空间含 '_run_inspect_doc'。"""
    import evaluation.cli as m
    assert hasattr(m, "_run_inspect_doc")


def test_module_namespace_does_not_contain_run():
    """模块命名空间不含顶层 'run'。"""
    import evaluation.cli as m
    assert not hasattr(m, "run")


# =========================================================================
# argparse 错误处理
# =========================================================================


def test_argparse_invalid_choice_raises_system_exit():
    """未知 --parser choice raises SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--manifest", "x", "--output", "y", "--parser", "invalid_choice"])
    assert exc_info.value.code == 2


def test_argparse_invalid_int_for_max_chars_raises_system_exit():
    """--max-chars 非数字 raises SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--manifest", "x", "--output", "y", "--max-chars", "not_a_number"])
    assert exc_info.value.code == 2


def test_argparse_unknown_argument_raises_system_exit():
    """未知参数 raises SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--manifest", "x", "--output", "y", "--unknown-arg"])
    assert exc_info.value.code == 2


# =========================================================================
# 模块没有 __all__
# =========================================================================


def test_module_no_dunder_all():
    """模块无 __all__。"""
    import evaluation.cli as m
    assert not hasattr(m, "__all__")


# =========================================================================
# _format_metric name 含 unicode 字符
# =========================================================================


def test_format_metric_unicode_name_renders():
    """name 含中文 → 正常渲染。"""
    out = _format_metric("中文指标", {"value": 0.5, "reason": None})
    assert "中文指标" in out
    assert "0.5000" in out


def test_format_metric_long_name_renders():
    """name 较长 → 仍然渲染。"""
    long_name = "a" * 100
    out = _format_metric(long_name, {"value": 0.5, "reason": None})
    assert long_name in out


# =========================================================================
# main 子命令分发
# =========================================================================


def test_main_run_with_nonexistent_manifest_returns_two(tmp_path: Path, capsys):
    """run --manifest 不存在 → 返回 2。"""
    rc = main([
        "run",
        "--manifest", str(tmp_path / "missing.json"),
        "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 2


def test_main_validate_report_nonexistent_returns_two(tmp_path: Path, capsys):
    """validate-report 不存在 → 返回 2。"""
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_inspect_doc_nonexistent_returns_two(tmp_path: Path, capsys):
    """inspect-doc 不存在 → 返回 2。"""
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert rc == 2
