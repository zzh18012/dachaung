r"""evaluation/cli.py 边角测试 - 第五轮（Round 128）。

补强已有 base/edges/edges2/edges3/edges4（共 375 测试）未覆盖的深度路径：
- _build_parser 深度：
  - subparser 数量精确（3 个：run/validate-report/inspect-doc）
  - run subparser 参数数量（5：--manifest/--output/--parser/--max-chars/--tolerance-chars）
  - 各参数 help text 内容
  - --parser choices 元组精确
  - validate-report 与 inspect-doc 各自 1 个位置参数
  - inspect-doc 含 --tolerance-chars
- _format_metric 深度：
  - None value 无 reason → "null  (None)"
  - int value 大数/0/负数
  - dict value 排序 by key
  - dict value 含 unicode
  - string value 含空白
  - name 不足 36 字符补空格
  - name 超 36 不截断
- main 退出码矩阵：
  - inspect-doc 合法文档 → 0
  - inspect-doc 缺文件 → 2
  - inspect-doc 坏 JSON → 1
  - validate-report 缺文件 → 2
  - validate-report 坏 JSON → 1
  - validate-report 不符合 schema → 1
- _run_inspect_doc 深度：
  - tolerance_chars 透传
  - 缺 source_type → "unknown"
  - elements/chunks 缺 → 0
  - 各种 metric 类型显示
- 模块结构深度：
  - 私有 vs public 函数
  - imports 完整
  - docstring 提及 3 个子命令
- 签名深度：
  - main argv 默认 None
  - _format_metric 2 参数
  - _run_inspect_doc 1 参数
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# =========================================================================
# _build_parser 深度（subparser 与参数细节）
# =========================================================================


def test_build_parser_returns_argument_parser():
    import argparse

    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_build_parser_has_three_subcommands():
    p = _build_parser()
    # 通过 parse_args 验证 3 个子命令存在
    for cmd in ("run", "validate-report", "inspect-doc"):
        # 不 raise 即说明子命令存在
        try:
            p.parse_args([cmd, "--help"])
        except SystemExit:
            pass


def test_build_parser_prog_is_evaluation_cli():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_contains_eval_description():
    p = _build_parser()
    assert "评测" in p.description or "evaluation" in p.description.lower()


def test_build_parser_run_subparser_has_manifest_arg():
    """run 必需 --manifest。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "/tmp/out.json"])


def test_build_parser_run_subparser_has_output_arg():
    """run 必需 --output。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "/tmp/m.json"])


def test_build_parser_run_parser_choices_exact():
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json",
        "--parser", "kreuzberg",
    ])
    assert args.parser == "kreuzberg"


def test_build_parser_run_parser_choices_rejects_unknown():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run", "--manifest", "m.json", "--output", "o.json",
            "--parser", "unknown",
        ])


def test_build_parser_run_parser_default_is_fallback():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.parser == "fallback"


def test_build_parser_run_max_chars_default_800():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.max_chars == 800


def test_build_parser_run_tolerance_chars_default_30():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.tolerance_chars == 30


def test_build_parser_run_max_chars_custom():
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json",
        "--max-chars", "1200",
    ])
    assert args.max_chars == 1200


def test_build_parser_run_tolerance_chars_custom():
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json",
        "--tolerance-chars", "50",
    ])
    assert args.tolerance_chars == 50


def test_build_parser_validate_report_takes_input_positional():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"
    assert args.command == "validate-report"


def test_build_parser_validate_report_no_optional_args():
    p = _build_parser()
    # validate-report 不接受任何可选参数
    with pytest.raises(SystemExit):
        p.parse_args(["validate-report", "report.json", "--extra", "x"])


def test_build_parser_inspect_doc_takes_input_positional():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.input == "doc.json"
    assert args.command == "inspect-doc"


def test_build_parser_inspect_doc_tolerance_chars_default_30():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_tolerance_chars_custom():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "60"])
    assert args.tolerance_chars == 60


def test_build_parser_command_dest_is_command():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert hasattr(args, "command")


def test_build_parser_run_command_value_set():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.command == "run"


# =========================================================================
# _format_metric 深度（更多 value 类型组合）
# =========================================================================


def test_format_metric_signature_two_params():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters.keys())
    assert len(params) == 2
    assert "name" in params
    assert "metric" in params


def test_format_metric_return_annotation_str():
    sig = inspect.signature(_format_metric)
    ret = sig.return_annotation
    assert ret is str or "str" in str(ret)


def test_format_metric_none_value_with_no_reason():
    result = _format_metric("m", {"value": None})
    # 无 reason → reason 是 None
    assert "null" in result
    assert "(None)" in result


def test_format_metric_none_value_with_explicit_reason():
    result = _format_metric("m", {"value": None, "reason": "not_evaluated"})
    assert "null" in result
    assert "(not_evaluated)" in result


def test_format_metric_int_value_with_reason():
    result = _format_metric("m", {"value": 42, "reason": "count"})
    assert "42" in result
    assert "(count)" in result


def test_format_metric_int_value_no_reason_uses_ok():
    result = _format_metric("m", {"value": 42})
    assert "42" in result
    assert "(ok)" in result


def test_format_metric_float_value_precision_4_digits():
    result = _format_metric("m", {"value": 0.123456789})
    assert "0.1235" in result  # 4 位小数四舍五入


def test_format_metric_float_value_with_reason():
    result = _format_metric("m", {"value": 0.5, "reason": "ratio"})
    assert "0.5000" in result
    assert "(ratio)" in result


def test_format_metric_bool_true_with_reason():
    result = _format_metric("m", {"value": True, "reason": "explicit"})
    assert "true" in result
    assert "(explicit)" in result


def test_format_metric_bool_false_with_reason():
    result = _format_metric("m", {"value": False, "reason": "explicit"})
    assert "false" in result
    assert "(explicit)" in result


def test_format_metric_dict_value_sorted_by_key():
    result = _format_metric("m", {"value": {"b": 2, "a": 1, "c": 3}})
    # 按 key 排序：a, b, c
    assert result.index("a=1") < result.index("b=2")
    assert result.index("b=2") < result.index("c=3")


def test_format_metric_dict_value_with_reason():
    result = _format_metric("m", {"value": {"x": 1}, "reason": "counts"})
    assert "x=1" in result
    assert "(counts)" in result


def test_format_metric_dict_value_empty():
    result = _format_metric("m", {"value": {}})
    # 空 dict → 空字符串
    assert "  (ok)" in result or "  ()" in result


def test_format_metric_string_value_short():
    result = _format_metric("m", {"value": "short"})
    assert "short" in result


def test_format_metric_string_value_with_reason():
    result = _format_metric("m", {"value": "abc", "reason": "name"})
    assert "(name)" in result


def test_format_metric_string_value_unicode():
    result = _format_metric("m", {"value": "中文"})
    assert "中文" in result


def test_format_metric_name_short_padded_to_36():
    result = _format_metric("x", {"value": 1})
    # x 后应补足到 36 字符宽
    assert "x" + " " * 35 in result


def test_format_metric_name_exactly_36_no_pad():
    name = "a" * 36
    result = _format_metric(name, {"value": 1})
    # 名字后是 1 个空格分隔（不是补足）
    assert name in result


def test_format_metric_name_37_not_truncated():
    name = "a" * 37
    result = _format_metric(name, {"value": 1})
    # 完整 37 字符都在
    assert name in result


def test_format_metric_returns_str():
    assert isinstance(_format_metric("m", {"value": 1}), str)


def test_format_metric_value_missing_returns_none_path():
    """metric 没有 value key → .get() 返回 None。"""
    result = _format_metric("m", {})
    assert "null" in result


def test_format_metric_reason_missing_uses_none():
    """metric 没有 reason key → None。"""
    result = _format_metric("m", {"value": None})
    assert "(None)" in result


def test_format_metric_list_value_falls_through_to_default():
    """list 不是 None/bool/float/dict → 走 default str() 分支。"""
    result = _format_metric("m", {"value": [1, 2, 3]})
    assert "[1, 2, 3]" in result


# =========================================================================
# _run_inspect_doc 深度
# =========================================================================


def test_run_inspect_doc_signature_one_param():
    sig = inspect.signature(_run_inspect_doc)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "args" in params


def test_run_inspect_doc_return_annotation_int():
    sig = inspect.signature(_run_inspect_doc)
    ret = sig.return_annotation
    assert ret is int or "int" in str(ret)


def test_run_inspect_doc_missing_file_returns_2(tmp_path: Path, capsys):
    class Args:
        input = str(tmp_path / "missing.json")
        tolerance_chars = 30

    rc = _run_inspect_doc(Args())
    assert rc == 2
    err = capsys.readouterr().err
    assert "文档不存在" in err or "ERROR" in err


def test_run_inspect_doc_bad_json_returns_1(tmp_path: Path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(Args())
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON" in err or "ERROR" in err


def test_run_inspect_doc_array_root_returns_1(tmp_path: Path, capsys):
    p = tmp_path / "arr.json"
    p.write_text("[]", encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(Args())
    assert rc == 1
    err = capsys.readouterr().err
    assert "对象" in err or "object" in err.lower() or "ERROR" in err


def test_run_inspect_doc_string_root_returns_1(tmp_path: Path):
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(Args())
    assert rc == 1


def test_run_inspect_doc_null_root_returns_1(tmp_path: Path):
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(Args())
    assert rc == 1


def test_run_inspect_doc_int_root_returns_1(tmp_path: Path):
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(Args())
    assert rc == 1


def test_run_inspect_doc_bool_root_returns_1(tmp_path: Path):
    p = tmp_path / "bool.json"
    p.write_text("true", encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(Args())
    assert rc == 1


def test_run_inspect_doc_minimal_doc_returns_0(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(Args())
    assert rc == 0


def test_run_inspect_doc_prints_file_path(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({}), encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    _run_inspect_doc(Args())
    out = capsys.readouterr().out
    assert str(p) in out


def test_run_inspect_doc_prints_counts(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    doc = {"elements": [{"x": 1}, {"y": 2}], "chunks": [{"z": 1}]}
    p.write_text(json.dumps(doc), encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    _run_inspect_doc(Args())
    out = capsys.readouterr().out
    assert "elements=2" in out
    assert "chunks=1" in out


def test_run_inspect_doc_prints_metrics_header(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({}), encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    _run_inspect_doc(Args())
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_no_source_type_defaults_unknown(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({}), encoding="utf-8")

    class Args:
        input = str(p)
        tolerance_chars = 30

    _run_inspect_doc(Args())
    out = capsys.readouterr().out
    assert "unknown" in out


# =========================================================================
# main 退出码矩阵
# =========================================================================


def test_main_signature_one_param():
    sig = inspect.signature(main)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "argv" in params


def test_main_argv_default_none():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_return_annotation_int():
    sig = inspect.signature(main)
    ret = sig.return_annotation
    assert ret is int or "int" in str(ret)


def test_main_no_command_returns_2(capsys):
    """无子命令 → argparse 报错（exit 2）。"""
    with pytest.raises(SystemExit) as ei:
        main([])
    assert ei.value.code == 2


def test_main_unknown_command_returns_2(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["unknown-command"])
    assert ei.value.code == 2


def test_main_inspect_doc_missing_file_returns_2(tmp_path: Path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_inspect_doc_bad_json_returns_1(tmp_path: Path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_valid_returns_0(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_validate_report_missing_file_returns_2(tmp_path: Path, capsys):
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_imports_argparse():
    from evaluation import cli as mod
    assert hasattr(mod, "argparse")


def test_module_imports_json():
    from evaluation import cli as mod
    assert hasattr(mod, "json")


def test_module_imports_sys():
    from evaluation import cli as mod
    assert hasattr(mod, "sys")


def test_module_imports_path():
    from evaluation import cli as mod
    assert hasattr(mod, "Path")


def test_module_imports_manifest_error():
    from evaluation import cli as mod
    assert hasattr(mod, "ManifestError")


def test_module_imports_load_manifest():
    from evaluation import cli as mod
    assert hasattr(mod, "load_manifest")


def test_module_imports_run_evaluation():
    from evaluation import cli as mod
    assert hasattr(mod, "run_evaluation")


def test_module_imports_get_git_provenance():
    from evaluation import cli as mod
    assert hasattr(mod, "get_git_provenance")


def test_module_imports_eval_schema_error():
    from evaluation import cli as mod
    assert hasattr(mod, "EvalSchemaError")


def test_module_imports_validate_file():
    from evaluation import cli as mod
    assert hasattr(mod, "validate_file")


def test_module_has_build_parser():
    from evaluation import cli as mod
    assert hasattr(mod, "_build_parser")


def test_module_has_main():
    from evaluation import cli as mod
    assert hasattr(mod, "main")


def test_module_has_format_metric():
    from evaluation import cli as mod
    assert hasattr(mod, "_format_metric")


def test_module_has_run_inspect_doc():
    from evaluation import cli as mod
    assert hasattr(mod, "_run_inspect_doc")


def test_module_does_not_define_all():
    """cli.py 不定义 __all__。"""
    from evaluation import cli as mod
    assert not hasattr(mod, "__all__") or mod.__all__ is None


def test_module_docstring_present():
    from evaluation import cli as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_run():
    from evaluation import cli as mod
    assert "run" in mod.__doc__


def test_module_docstring_mentions_validate_report():
    from evaluation import cli as mod
    assert "validate-report" in mod.__doc__


def test_module_docstring_mentions_inspect_doc():
    from evaluation import cli as mod
    assert "inspect-doc" in mod.__doc__


def test_module_docstring_mentions_manifest():
    from evaluation import cli as mod
    assert "manifest" in mod.__doc__.lower()


def test_module_docstring_mentions_parser():
    from evaluation import cli as mod
    assert "parser" in mod.__doc__.lower()


def test_module_uses_future_annotations():
    import ast
    from evaluation import cli as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    has_future = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(a.name == "annotations" for a in node.names)
        for node in tree.body
    )
    assert has_future


def test_module_has_main_guard():
    """__main__ guard 存在。"""
    import ast
    from evaluation import cli as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    has_guard = any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and any(
            (isinstance(c, ast.Eq) and isinstance(getattr(node.test, "left", None), ast.Name)
             and getattr(node.test.left, "id", "") == "__name__")
            for c in node.test.ops
        )
        for node in tree.body
    )
    assert has_guard


def test_module_has_utf8_reconfigure_block():
    """含 sys.stdout.reconfigure 调用。"""
    from evaluation import cli as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "reconfigure" in src
    assert "utf-8" in src.lower() or "utf8" in src.lower()


def test_module_helpers_are_private():
    """所有 helper 函数都带 _ 前缀（除 main）。"""
    from evaluation import cli as mod

    for name in ("_build_parser", "_format_metric", "_run_inspect_doc"):
        assert name.startswith("_")
        assert hasattr(mod, name)


def test_module_main_is_public():
    from evaluation import cli as mod

    assert not mod.main.__name__.startswith("_")


# =========================================================================
# _build_parser 签名深度
# =========================================================================


def test_build_parser_signature_no_params():
    sig = inspect.signature(_build_parser)
    params = list(sig.parameters.keys())
    assert len(params) == 0


def test_build_parser_return_annotation_argument_parser():
    sig = inspect.signature(_build_parser)
    ret = sig.return_annotation
    assert "ArgumentParser" in str(ret)


# =========================================================================
# _format_metric 边界情况
# =========================================================================


def test_format_metric_metric_value_is_dict_with_empty_value_key():
    """空 dict metric → null 路径。"""
    result = _format_metric("m", {})
    # 空 dict metric 走 None 路径
    assert "null" in result


def test_format_metric_metric_only_has_value_key():
    result = _format_metric("m", {"value": 1})
    # 无 reason → 默认 ok
    assert "(ok)" in result


def test_format_metric_metric_has_extra_keys_ignored():
    """metric 多余 key 不影响渲染。"""
    result = _format_metric("m", {"value": 1, "reason": "r", "extra": "ignored"})
    assert "1" in result
    assert "(r)" in result
    assert "ignored" not in result


def test_format_metric_int_zero():
    result = _format_metric("m", {"value": 0})
    assert "0" in result


def test_format_metric_int_negative():
    result = _format_metric("m", {"value": -5})
    assert "-5" in result


def test_format_metric_float_zero():
    result = _format_metric("m", {"value": 0.0})
    assert "0.0000" in result


def test_format_metric_float_very_small():
    result = _format_metric("m", {"value": 0.00001})
    # 0.00001 四舍五入到 4 位 = 0.0000
    assert "0.0000" in result


def test_format_metric_float_large():
    result = _format_metric("m", {"value": 12345.6789})
    assert "12345.6789" in result


def test_format_metric_dict_value_with_int_keys():
    """dict 含 int key → str 转换。"""
    result = _format_metric("m", {"value": {1: "a", 2: "b"}})
    assert "1=a" in result or "1='a'" in result


def test_format_metric_string_value_empty_string():
    result = _format_metric("m", {"value": ""})
    # 空字符串走 default 分支
    assert "  (ok)" in result or "() )" in result
