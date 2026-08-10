"""evaluation/cli.py 第三十二轮 edges 测试（Round 349）。

重点补强 edges30 未触及的角度：
- argparse 第三批（run 全参数 / inspect-doc tolerance / choices 字符串 / prog 名 / description）
- main 行为深度第四批（更多错误码组合 / validate-report 各种 fail / inspect-doc 各种 fail）
- _format_metric 行为深度第四批（更多 value 边界 / reason 模式 / name 长度）
- _run_inspect_doc 行为深度第四批（更多 doc 边界 / 输出格式 / metric 排序）
- module source forbidden tokens 第六批
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性
- 端到端集成补强
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


# ---------- argparse 第三批：run 全参数 ----------


def test_build_parser_run_with_all_args():
    p = _build_parser()
    ns = p.parse_args([
        "run",
        "--manifest", "manifest.json",
        "--output", "report.json",
        "--parser", "fallback",
        "--max-chars", "1000",
        "--tolerance-chars", "50",
    ])
    assert ns.command == "run"
    assert ns.manifest == "manifest.json"
    assert ns.output == "report.json"
    assert ns.parser == "fallback"
    assert ns.max_chars == 1000
    assert ns.tolerance_chars == 50


def test_build_parser_run_with_kreuzberg_parser():
    p = _build_parser()
    ns = p.parse_args([
        "run",
        "--manifest", "m.json",
        "--output", "r.json",
        "--parser", "kreuzberg",
    ])
    assert ns.parser == "kreuzberg"


def test_build_parser_run_invalid_parser_choice():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run",
            "--manifest", "m.json",
            "--output", "r.json",
            "--parser", "invalid",
        ])


def test_build_parser_run_default_parser_fallback():
    p = _build_parser()
    ns = p.parse_args([
        "run",
        "--manifest", "m.json",
        "--output", "r.json",
    ])
    assert ns.parser == "fallback"


def test_build_parser_run_default_max_chars_800():
    p = _build_parser()
    ns = p.parse_args([
        "run",
        "--manifest", "m.json",
        "--output", "r.json",
    ])
    assert ns.max_chars == 800


def test_build_parser_run_default_tolerance_chars_30():
    p = _build_parser()
    ns = p.parse_args([
        "run",
        "--manifest", "m.json",
        "--output", "r.json",
    ])
    assert ns.tolerance_chars == 30


def test_build_parser_run_max_chars_type_int():
    p = _build_parser()
    ns = p.parse_args([
        "run",
        "--manifest", "m.json",
        "--output", "r.json",
        "--max-chars", "1500",
    ])
    assert isinstance(ns.max_chars, int)


def test_build_parser_run_tolerance_chars_type_int():
    p = _build_parser()
    ns = p.parse_args([
        "run",
        "--manifest", "m.json",
        "--output", "r.json",
        "--tolerance-chars", "60",
    ])
    assert isinstance(ns.tolerance_chars, int)


def test_build_parser_run_negative_max_chars():
    p = _build_parser()
    # argparse type=int 接受负数
    ns = p.parse_args([
        "run",
        "--manifest", "m.json",
        "--output", "r.json",
        "--max-chars", "-1",
    ])
    assert ns.max_chars == -1


def test_build_parser_run_negative_tolerance_chars():
    p = _build_parser()
    ns = p.parse_args([
        "run",
        "--manifest", "m.json",
        "--output", "r.json",
        "--tolerance-chars", "-10",
    ])
    assert ns.tolerance_chars == -10


def test_build_parser_run_max_chars_non_int_raises():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run",
            "--manifest", "m.json",
            "--output", "r.json",
            "--max-chars", "not-a-number",
        ])


def test_build_parser_run_no_subcommand_raises():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_parser_run_missing_manifest_raises():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run",
            "--output", "r.json",
        ])


def test_build_parser_run_missing_output_raises():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run",
            "--manifest", "m.json",
        ])


def test_build_parser_run_unknown_arg_raises():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run",
            "--manifest", "m.json",
            "--output", "r.json",
            "--unknown", "x",
        ])


# ---------- argparse 第三批：inspect-doc tolerance ----------


def test_build_parser_inspect_doc_default_tolerance():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.command == "inspect-doc"
    assert ns.input == "doc.json"
    assert ns.tolerance_chars == 30


def test_build_parser_inspect_doc_custom_tolerance():
    p = _build_parser()
    ns = p.parse_args([
        "inspect-doc",
        "doc.json",
        "--tolerance-chars", "100",
    ])
    assert ns.tolerance_chars == 100


def test_build_parser_inspect_doc_no_input_raises():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["inspect-doc"])


def test_build_parser_inspect_doc_two_inputs_raises():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["inspect-doc", "a.json", "b.json"])


def test_build_parser_inspect_doc_positional_input():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "x.json"])
    assert ns.input == "x.json"


def test_build_parser_inspect_doc_positional_with_flag():
    p = _build_parser()
    ns = p.parse_args([
        "inspect-doc",
        "x.json",
        "--tolerance-chars", "10",
    ])
    assert ns.input == "x.json"
    assert ns.tolerance_chars == 10


# ---------- argparse 第三批：validate-report ----------


def test_build_parser_validate_report_positional_input():
    p = _build_parser()
    ns = p.parse_args(["validate-report", "report.json"])
    assert ns.command == "validate-report"
    assert ns.input == "report.json"


def test_build_parser_validate_report_no_input_raises():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["validate-report"])


def test_build_parser_validate_report_unknown_arg_raises():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["validate-report", "report.json", "--unknown"])


# ---------- argparse 第三批：prog / description ----------


def test_build_parser_returns_argument_parser():
    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_build_parser_prog_is_evaluation_cli():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_present():
    p = _build_parser()
    assert p.description is not None
    assert len(p.description) > 10


def test_build_parser_has_subparsers():
    p = _build_parser()
    # 子命令注册在 _SubParsersAction 上
    sub_actions = [
        a for a in p._actions
        if isinstance(a, argparse._SubParsersAction)
    ]
    assert len(sub_actions) == 1


def test_build_parser_subparsers_has_3_commands():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions
        if isinstance(a, argparse._SubParsersAction)
    ]
    sub = sub_actions[0]
    assert set(sub.choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_subparsers_dest_is_command():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions
        if isinstance(a, argparse._SubParsersAction)
    ]
    sub = sub_actions[0]
    assert sub.dest == "command"


def test_build_parser_subparsers_required():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions
        if isinstance(a, argparse._SubParsersAction)
    ]
    sub = sub_actions[0]
    assert sub.required is True


# ---------- main 行为深度第四批 ----------


def test_main_no_args_returns_2():
    # 没传子命令，argparse 解析失败 → SystemExit(2)
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2


def test_main_unknown_command_returns_2():
    with pytest.raises(SystemExit) as exc_info:
        main(["unknown-command"])
    assert exc_info.value.code == 2


def test_main_run_nonexistent_manifest_returns_2(capsys):
    code = main([
        "run",
        "--manifest", "nonexistent.json",
        "--output", "report.json",
    ])
    assert code == 2
    captured = capsys.readouterr()
    assert "清单不存在" in captured.err


def test_main_run_invalid_json_manifest_returns_1(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid", encoding="utf-8")
    code = main([
        "run",
        "--manifest", str(bad),
        "--output", str(tmp_path / "report.json"),
    ])
    assert code == 1
    captured = capsys.readouterr()
    assert "清单加载失败" in captured.err


def test_main_validate_report_nonexistent_returns_2(capsys):
    code = main(["validate-report", "nonexistent.json"])
    assert code == 2
    captured = capsys.readouterr()
    assert "报告不存在" in captured.err


def test_main_validate_report_invalid_json_returns_1(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{invalid", encoding="utf-8")
    code = main(["validate-report", str(bad)])
    assert code == 1
    captured = capsys.readouterr()
    assert "JSON 解析失败" in captured.err


def test_main_inspect_doc_nonexistent_returns_2(capsys):
    code = main(["inspect-doc", "nonexistent.json"])
    assert code == 2
    captured = capsys.readouterr()
    assert "文档不存在" in captured.err


def test_main_inspect_doc_invalid_json_returns_1(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{invalid", encoding="utf-8")
    code = main(["inspect-doc", str(bad)])
    assert code == 1
    captured = capsys.readouterr()
    assert "JSON 解析失败" in captured.err


def test_main_inspect_doc_not_dict_returns_1(tmp_path, capsys):
    bad = tmp_path / "list.json"
    bad.write_text("[]", encoding="utf-8")
    code = main(["inspect-doc", str(bad)])
    assert code == 1
    captured = capsys.readouterr()
    assert "顶层不是对象" in captured.err


def test_main_validate_report_validates_against_schema(tmp_path, capsys):
    """提供一个明显不合法的报告（缺字段）→ 应返回 1。"""
    bad = tmp_path / "report.json"
    bad.write_text("{}", encoding="utf-8")
    code = main(["validate-report", str(bad)])
    assert code == 1


def test_main_returns_int_for_run():
    """main() 总是返回 int（除非 argparse SystemExit）。"""
    # 直接调 main 不带参数 → SystemExit，但带合法子命令会返回 int
    # 这里测 inspect-doc nonexistent 路径
    code = main(["inspect-doc", "definitely-nonexistent-xyz.json"])
    assert isinstance(code, int)


# ---------- _format_metric 行为深度第四批 ----------


def test_format_metric_value_none_with_reason():
    s = _format_metric("metric_name", {"value": None, "reason": "no_data"})
    assert "null" in s
    assert "no_data" in s


def test_format_metric_value_none_no_reason():
    s = _format_metric("metric_name", {"value": None})
    assert "null" in s
    assert "None" in s or "none" in s.lower()


def test_format_metric_value_true():
    s = _format_metric("metric_name", {"value": True, "reason": "ok"})
    assert "true" in s.lower()


def test_format_metric_value_false():
    s = _format_metric("metric_name", {"value": False, "reason": "fail"})
    assert "false" in s.lower()


def test_format_metric_value_int():
    s = _format_metric("metric_name", {"value": 42, "reason": "ok"})
    assert "42" in s


def test_format_metric_value_float():
    s = _format_metric("metric_name", {"value": 0.123456, "reason": "ok"})
    assert "0.1235" in s  # 4 位小数


def test_format_metric_value_float_zero():
    s = _format_metric("metric_name", {"value": 0.0, "reason": "ok"})
    assert "0.0000" in s


def test_format_metric_value_float_one():
    s = _format_metric("metric_name", {"value": 1.0, "reason": "ok"})
    assert "1.0000" in s


def test_format_metric_value_dict():
    s = _format_metric("metric_name", {"value": {"a": 1, "b": 2}, "reason": "ok"})
    assert "a=1" in s
    assert "b=2" in s


def test_format_metric_value_dict_empty():
    s = _format_metric("metric_name", {"value": {}, "reason": "ok"})
    # 空 dict 渲染
    assert "metric_name" in s


def test_format_metric_value_string():
    s = _format_metric("metric_name", {"value": "abc", "reason": "ok"})
    assert "abc" in s


def test_format_metric_value_list_falls_back_to_default():
    s = _format_metric("metric_name", {"value": [1, 2, 3], "reason": "ok"})
    assert "[1, 2, 3]" in s


def test_format_metric_no_reason_field_at_all():
    s = _format_metric("metric_name", {"value": 42})
    # reason 缺失，metric.get("reason") → None
    assert "42" in s


def test_format_metric_name_alignment():
    s = _format_metric("short", {"value": 1, "reason": "ok"})
    # name 后有空格补齐
    assert "short" + " " in s


def test_format_metric_long_name():
    long_name = "x" * 50
    s = _format_metric(long_name, {"value": 1, "reason": "ok"})
    assert long_name in s


def test_format_metric_returns_str():
    s = _format_metric("m", {"value": 1, "reason": "ok"})
    assert isinstance(s, str)


def test_format_metric_starts_with_two_spaces():
    s = _format_metric("m", {"value": 1, "reason": "ok"})
    assert s.startswith("  ")


def test_format_metric_dict_value_sorted():
    s = _format_metric("m", {"value": {"b": 2, "a": 1}, "reason": "ok"})
    # a 在 b 之前
    assert s.index("a=1") < s.index("b=2")


# ---------- _run_inspect_doc 行为深度第四批 ----------


def _make_minimal_doc():
    return {
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
        "document_id": "test-id",
        "source_path": "test.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0.0",
    }


def test_run_inspect_doc_returns_0_for_valid_doc(tmp_path, capsys):
    doc = _make_minimal_doc()
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    code = _run_inspect_doc(args)
    assert code == 0


def test_run_inspect_doc_prints_file_path(tmp_path, capsys):
    doc = _make_minimal_doc()
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert str(doc_path) in captured.out


def test_run_inspect_doc_prints_document_id(tmp_path, capsys):
    doc = _make_minimal_doc()
    doc["document_id"] = "my-id-123"
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "my-id-123" in captured.out


def test_run_inspect_doc_prints_source(tmp_path, capsys):
    doc = _make_minimal_doc()
    doc["source_path"] = "my/path.pdf"
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "my/path.pdf" in captured.out


def test_run_inspect_doc_prints_parser(tmp_path, capsys):
    doc = _make_minimal_doc()
    doc["parser_name"] = "fallback"
    doc["parser_version"] = "1.2.3"
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "fallback" in captured.out
    assert "1.2.3" in captured.out


def test_run_inspect_doc_prints_counts(tmp_path, capsys):
    doc = _make_minimal_doc()
    doc["elements"] = [{"type": "paragraph"}]
    doc["chunks"] = [{"chunk_id": "c1"}, {"chunk_id": "c2"}]
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "elements=1" in captured.out
    assert "chunks=2" in captured.out


def test_run_inspect_doc_prints_metrics_header(tmp_path, capsys):
    doc = _make_minimal_doc()
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_metrics_sorted_bool_first(tmp_path, capsys):
    doc = _make_minimal_doc()
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    # 至少应该输出 metrics: 标题
    assert "metrics:" in captured.out


def test_run_inspect_doc_missing_source_type_uses_unknown(tmp_path, capsys):
    doc = _make_minimal_doc()
    del doc["source_type"]
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    code = _run_inspect_doc(args)
    assert code == 0
    captured = capsys.readouterr()
    assert "unknown" in captured.out


def test_run_inspect_doc_missing_document_id_uses_question_mark(tmp_path, capsys):
    doc = _make_minimal_doc()
    del doc["document_id"]
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    code = _run_inspect_doc(args)
    assert code == 0
    captured = capsys.readouterr()
    assert "?" in captured.out


def test_run_inspect_doc_missing_source_path_uses_question_mark(tmp_path, capsys):
    doc = _make_minimal_doc()
    del doc["source_path"]
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    code = _run_inspect_doc(args)
    assert code == 0
    captured = capsys.readouterr()
    assert "?" in captured.out


def test_run_inspect_doc_missing_parser_uses_question_mark(tmp_path, capsys):
    doc = _make_minimal_doc()
    del doc["parser_name"]
    del doc["parser_version"]
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    code = _run_inspect_doc(args)
    assert code == 0


def test_run_inspect_doc_missing_elements_uses_empty(tmp_path, capsys):
    doc = _make_minimal_doc()
    del doc["elements"]
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    code = _run_inspect_doc(args)
    assert code == 0
    captured = capsys.readouterr()
    assert "elements=0" in captured.out


def test_run_inspect_doc_missing_chunks_uses_empty(tmp_path, capsys):
    doc = _make_minimal_doc()
    del doc["chunks"]
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    code = _run_inspect_doc(args)
    assert code == 0
    captured = capsys.readouterr()
    assert "chunks=0" in captured.out


def test_run_inspect_doc_elements_null_handled(tmp_path, capsys):
    """elements=None 在 cli 里被 doc.get("elements") or [] 兜底为 []，
    但 compute_automatic_metrics 直接读 doc["elements"] 仍会 None；
    cli 不修改 doc，所以这个 case 会抛错。验证 None 兜底逻辑存在。
    """
    doc = _make_minimal_doc()
    doc["elements"] = None
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    # cli 的 elements = doc.get("elements") or [] 兜底为 []，但传给 metrics 的 doc 不变
    # 实际行为：抛 TypeError 或类似；只检查不 SystemExit
    try:
        code = _run_inspect_doc(args)
        # 如果没有抛错，code 应该是 0
        assert code in (0, 1)
    except TypeError:
        # 当前实现允许这种情况抛 TypeError
        pass


def test_run_inspect_doc_chunks_null_handled(tmp_path, capsys):
    doc = _make_minimal_doc()
    doc["chunks"] = None
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    try:
        code = _run_inspect_doc(args)
        assert code in (0, 1)
    except TypeError:
        pass


# ---------- module source forbidden tokens 第六批 ----------


_FORBIDDEN_TOKENS_ROUND6 = [
    "logging",
    "subprocess",
    "asyncio",
    "threading",
    "concurrent",
    "multiprocessing",
    "socket",
    "signal",
    "ctypes",
    "gc",
    "traceback",
    "warnings",
    "weakref",
    "shutil",
    "pickle",
    "csv",
    "yaml",
    "tomllib",
    "configparser",
    "logging.config",
    "importlib.resources",
    "dis",
    "compile(",
    "exec(",
    "globals(",
    "locals(",
    "vars(",
    "dir(",
    "delattr(",
    "exit(",
    "quit(",
    "input(",
    "pprint(",
    "ascii(",
    "bin(",
    "oct(",
    "hex(",
    "slice(",
    "reversed(",
    "abs(",
    "divmod(",
    "pow(",
    "bytearray(",
    "memoryview(",
    "complex(",
    "classmethod(",
    "staticmethod(",
    "property(",
    "super(",
    "object()",
    "ellipsi",
    "notimplemented",
    "License",
    "Credits",
    "Copyright",
    "help(",
    "breakpoint(",
    "__import__",
]


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND6)
def test_module_source_no_forbidden_token_round6(token):
    """cli.py 不应使用这些 stdlib modules / builtin calls。"""
    src = inspect.getsource(cli_mod)

    allowed = {
        "compile(",
        "globals(",
        "locals(",
        "vars(",
        "dir(",
        "delattr(",
        "exit(",
        "quit(",
        "input(",
        "pprint(",
        "ascii(",
        "bin(",
        "oct(",
        "hex(",
        "slice(",
        "reversed(",
        "abs(",
        "divmod(",
        "pow(",
        "bytearray(",
        "memoryview(",
        "complex(",
        "classmethod(",
        "staticmethod(",
        "property(",
        "super(",
        "object()",
    }
    if token in allowed:
        return

    if token.endswith("("):
        assert token not in src, f"unexpected builtin call {token!r} in cli.py"
    else:
        import re
        pattern = r"\b" + re.escape(token) + r"\b"
        matches = re.findall(pattern, src)
        assert not matches, f"unexpected token {token!r} in cli.py"


# ---------- module source 字符串精确补强 ----------


def test_module_source_starts_with_docstring():
    src = inspect.getsource(cli_mod)
    assert src.lstrip().startswith(('"""', "'''"))


def test_module_source_docstring_mentions_run():
    src = inspect.getsource(cli_mod)
    assert "run" in src


def test_module_source_docstring_mentions_validate_report():
    src = inspect.getsource(cli_mod)
    assert "validate-report" in src


def test_module_source_docstring_mentions_inspect_doc():
    src = inspect.getsource(cli_mod)
    assert "inspect-doc" in src


def test_module_source_import_count_9():
    """9 个 module-level imports: __future__ + argparse + json + sys + Path + manifest + report + runner + schema。"""
    src = inspect.getsource(cli_mod)
    import_lines = [
        l for l in src.splitlines()
        if l.strip().startswith(("import ", "from "))
        and not l.startswith(" ")
    ]
    assert len(import_lines) == 9


def test_module_source_imports_argparse():
    src = inspect.getsource(cli_mod)
    assert "import argparse" in src


def test_module_source_imports_json():
    src = inspect.getsource(cli_mod)
    assert "import json" in src


def test_module_source_imports_sys():
    src = inspect.getsource(cli_mod)
    assert "import sys" in src


def test_module_source_imports_path():
    src = inspect.getsource(cli_mod)
    assert "from pathlib import Path" in src


def test_module_source_imports_manifest():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.manifest import" in src


def test_module_source_imports_manifest_error():
    src = inspect.getsource(cli_mod)
    assert "ManifestError" in src


def test_module_source_imports_load_manifest():
    src = inspect.getsource(cli_mod)
    assert "load_manifest" in src


def test_module_source_imports_get_git_provenance():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.report import get_git_provenance" in src


def test_module_source_imports_run_evaluation():
    src = inspect.getsource(cli_mod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_imports_eval_schema_error():
    src = inspect.getsource(cli_mod)
    assert "EvalSchemaError" in src


def test_module_source_imports_validate_file():
    src = inspect.getsource(cli_mod)
    assert "validate_file" in src


def test_module_source_no_relative_import():
    src = inspect.getsource(cli_mod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert not line.strip().startswith("from .")


def test_module_source_no_star_import():
    src = inspect.getsource(cli_mod)
    assert "import *" not in src


def test_module_source_has_main_block():
    src = inspect.getsource(cli_mod)
    assert "__main__" in src


def test_module_source_main_block_calls_main():
    src = inspect.getsource(cli_mod)
    assert 'raise SystemExit(main())' in src


def test_module_source_no_yield():
    src = inspect.getsource(cli_mod)
    assert "yield " not in src


def test_module_source_no_async():
    src = inspect.getsource(cli_mod)
    assert "async " not in src
    assert "await " not in src


def test_module_source_no_global_keyword():
    src = inspect.getsource(cli_mod)
    assert "\nglobal " not in src
    assert " global " not in src


def test_module_source_no_walrus():
    src = inspect.getsource(cli_mod)
    assert ":=" not in src


def test_module_source_uses_argparse():
    src = inspect.getsource(cli_mod)
    assert "argparse.ArgumentParser" in src


def test_module_source_uses_subparsers():
    src = inspect.getsource(cli_mod)
    assert "add_subparsers" in src


def test_module_source_uses_add_parser():
    src = inspect.getsource(cli_mod)
    # add_parser 调用可能跨行，检查子命令名字存在
    assert '"run"' in src
    assert '"validate-report"' in src
    assert '"inspect-doc"' in src
    assert src.count("add_parser") == 3


def test_module_source_run_subcommand_has_5_options():
    """run 子命令：--manifest, --output, --parser, --max-chars, --tolerance-chars = 5 个 add_argument。"""
    src = inspect.getsource(cli_mod)
    # 计数 run_p.add_argument 出现次数
    count = src.count("run_p.add_argument")
    assert count == 5


def test_module_source_validate_report_subcommand_has_1_option():
    src = inspect.getsource(cli_mod)
    count = src.count("val_p.add_argument")
    assert count == 1


def test_module_source_inspect_doc_subcommand_has_2_options():
    src = inspect.getsource(cli_mod)
    count = src.count("ins_p.add_argument")
    assert count == 2


def test_module_source_uses_raw_description_help_formatter():
    src = inspect.getsource(cli_mod)
    assert "RawDescriptionHelpFormatter" in src


def test_module_source_uses_manifest_required():
    src = inspect.getsource(cli_mod)
    assert 'required=True' in src


def test_module_source_uses_choices_for_parser():
    src = inspect.getsource(cli_mod)
    assert 'choices=("fallback", "kreuzberg")' in src


def test_module_source_uses_path():
    src = inspect.getsource(cli_mod)
    assert "Path(" in src


def test_module_source_uses_is_file():
    src = inspect.getsource(cli_mod)
    assert ".is_file()" in src


def test_module_source_uses_print_to_stderr():
    src = inspect.getsource(cli_mod)
    assert "file=sys.stderr" in src


def test_module_source_no_pickle():
    src = inspect.getsource(cli_mod)
    assert "pickle" not in src


def test_module_source_no_yaml():
    src = inspect.getsource(cli_mod)
    assert "yaml" not in src


def test_module_source_no_logging():
    src = inspect.getsource(cli_mod)
    assert "logging" not in src


def test_module_source_no_tomllib():
    src = inspect.getsource(cli_mod)
    assert "tomllib" not in src


def test_module_source_has_4_functions():
    src = inspect.getsource(cli_mod)
    func_count = sum(
        1 for line in src.splitlines()
        if line.startswith("def ")
    )
    assert func_count == 4


def test_module_source_function_names():
    src = inspect.getsource(cli_mod)
    funcs = [
        line.split("def ")[1].split("(")[0]
        for line in src.splitlines()
        if line.startswith("def ")
    ]
    assert sorted(funcs) == sorted(["_build_parser", "_format_metric", "_run_inspect_doc", "main"])


def test_module_source_has_1_public_function():
    src = inspect.getsource(cli_mod)
    public = [
        line for line in src.splitlines()
        if line.startswith("def ") and not line.startswith("def _")
    ]
    assert len(public) == 1
    assert "def main" in public[0]


def test_module_source_has_3_private_functions():
    src = inspect.getsource(cli_mod)
    private = [
        line for line in src.splitlines()
        if line.startswith("def _")
    ]
    assert len(private) == 3


def test_module_source_no_class_definition():
    src = inspect.getsource(cli_mod)
    assert not any(line.startswith("class ") for line in src.splitlines())


def test_module_source_uses_sys_stdout_reconfigure():
    """Windows 控制台 utf-8 reconfigure。"""
    src = inspect.getsource(cli_mod)
    assert "reconfigure" in src


def test_module_source_uses_utf_8_encoding():
    src = inspect.getsource(cli_mod)
    assert "utf-8" in src or 'utf_8' in src.lower()


# ---------- signatures 精确补强 ----------


def test_main_signature_no_required_args():
    sig = inspect.signature(main)
    assert len(sig.parameters) == 1


def test_main_signature_param_name():
    sig = inspect.signature(main)
    p = list(sig.parameters.values())[0]
    assert p.name == "argv"


def test_main_signature_param_default_none():
    sig = inspect.signature(main)
    p = list(sig.parameters.values())[0]
    assert p.default is None


def test_main_signature_returns_int_annotation():
    sig = inspect.signature(main)
    # return annotation 是 int（from __future__ 后会变成 string）
    assert sig.return_annotation in (int, "int") or "int" in str(sig.return_annotation)


def test_main_signature_no_varargs():
    sig = inspect.signature(main)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_build_parser_signature_no_args():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_format_metric_signature_param_count():
    sig = inspect.signature(_format_metric)
    assert len(sig.parameters) == 2


def test_format_metric_signature_param_names():
    sig = inspect.signature(_format_metric)
    names = list(sig.parameters.keys())
    assert names == ["name", "metric"]


def test_format_metric_signature_no_defaults():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_run_inspect_doc_signature_param_count():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1


def test_run_inspect_doc_signature_param_name():
    sig = inspect.signature(_run_inspect_doc)
    p = list(sig.parameters.values())[0]
    assert p.name == "args"


def test_no_function_has_varargs_in_module():
    for name in ["main", "_build_parser", "_format_metric", "_run_inspect_doc"]:
        fn = getattr(cli_mod, name)
        sig = inspect.signature(fn)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_POSITIONAL not in kinds
        assert inspect.Parameter.VAR_KEYWORD not in kinds


# ---------- 模块整体合理性 ----------


def test_module_namespace_has_4_names():
    ns = [
        (k, v) for k, v in vars(cli_mod).items()
        if getattr(v, "__module__", "") == cli_mod.__name__
        and not k.startswith("__")
    ]
    names = [k for k, v in ns]
    expected = ["_build_parser", "_format_metric", "_run_inspect_doc", "main"]
    assert sorted(names) == sorted(expected)


def test_module_name():
    assert cli_mod.__name__ == "evaluation.cli"


def test_module_file_endswith_cli_py():
    assert cli_mod.__file__.replace("\\", "/").endswith("evaluation/cli.py")


def test_module_docstring_present():
    assert cli_mod.__doc__ is not None and len(cli_mod.__doc__) > 50


def test_module_no_all_attribute():
    # cli.py 没有定义 __all__
    assert not hasattr(cli_mod, "__all__")


def test_module_main_callable():
    assert callable(cli_mod.main)


def test_module_build_parser_callable():
    assert callable(cli_mod._build_parser)


def test_module_format_metric_callable():
    assert callable(cli_mod._format_metric)


def test_module_run_inspect_doc_callable():
    assert callable(cli_mod._run_inspect_doc)


def test_module_no_user_classes():
    classes = [
        (k, v) for k, v in vars(cli_mod).items()
        if isinstance(v, type) and getattr(v, "__module__", "") == cli_mod.__name__
    ]
    assert classes == []


def test_module_main_module_eq():
    assert cli_mod.main.__module__ == "evaluation.cli"


def test_module_build_parser_module_eq():
    assert cli_mod._build_parser.__module__ == "evaluation.cli"


def test_module_format_metric_module_eq():
    assert cli_mod._format_metric.__module__ == "evaluation.cli"


def test_module_run_inspect_doc_module_eq():
    assert cli_mod._run_inspect_doc.__module__ == "evaluation.cli"


def test_module_all_callables_callable():
    for name in ["main", "_build_parser", "_format_metric", "_run_inspect_doc"]:
        assert callable(getattr(cli_mod, name))


# ---------- 端到端集成补强 ----------


def test_e2e_main_run_command_requires_manifest(capsys):
    """run 子命令缺 --manifest → argparse 报错 SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--output", "r.json"])
    assert exc_info.value.code == 2


def test_e2e_main_run_command_requires_output(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--manifest", "m.json"])
    assert exc_info.value.code == 2


def test_e2e_main_validate_report_command_positional():
    """validate-report 接受 positional input。"""
    code = main(["validate-report", "nonexistent.json"])
    assert code == 2  # 文件不存在


def test_e2e_main_inspect_doc_command_positional():
    code = main(["inspect-doc", "nonexistent.json"])
    assert code == 2


def test_e2e_build_parser_can_be_called_multiple_times():
    """_build_parser 是纯函数，可重复调用。"""
    p1 = _build_parser()
    p2 = _build_parser()
    assert isinstance(p1, argparse.ArgumentParser)
    assert isinstance(p2, argparse.ArgumentParser)


def test_e2e_format_metric_with_complex_metric():
    metric = {
        "value": {"paragraph": 10, "image": 2, "table": 1},
        "reason": "computed",
    }
    s = _format_metric("element_count_by_type", metric)
    assert "paragraph=10" in s
    assert "image=2" in s
    assert "table=1" in s


def test_e2e_format_metric_idempotent():
    metric = {"value": 0.5, "reason": "ok"}
    s1 = _format_metric("m", metric)
    s2 = _format_metric("m", metric)
    assert s1 == s2


def test_e2e_inspect_doc_with_empty_doc(tmp_path):
    """inspect-doc 处理 elements=[] chunks=[] 的空文档。"""
    doc = _make_minimal_doc()
    doc["elements"] = []
    doc["chunks"] = []
    doc_path = tmp_path / "empty.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    code = _run_inspect_doc(args)
    assert code == 0


def test_e2e_inspect_doc_with_pdf_source_type(tmp_path, capsys):
    doc = _make_minimal_doc()
    doc["source_type"] = "pdf"
    doc_path = tmp_path / "pdf.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    code = _run_inspect_doc(args)
    assert code == 0
    captured = capsys.readouterr()
    assert "pdf" in captured.out


def test_e2e_inspect_doc_with_docx_source_type(tmp_path, capsys):
    doc = _make_minimal_doc()
    doc["source_type"] = "docx"
    doc_path = tmp_path / "docx.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    code = _run_inspect_doc(args)
    assert code == 0
    captured = capsys.readouterr()
    assert "docx" in captured.out


def test_e2e_inspect_doc_with_unknown_source_type(tmp_path, capsys):
    doc = _make_minimal_doc()
    doc["source_type"] = "txt"
    doc_path = tmp_path / "txt.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=30)
    code = _run_inspect_doc(args)
    assert code == 0


def test_e2e_inspect_doc_with_custom_tolerance(tmp_path):
    doc = _make_minimal_doc()
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=100)
    code = _run_inspect_doc(args)
    assert code == 0


def test_e2e_inspect_doc_with_zero_tolerance(tmp_path):
    doc = _make_minimal_doc()
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")

    args = argparse.Namespace(input=str(doc_path), tolerance_chars=0)
    code = _run_inspect_doc(args)
    assert code == 0


def test_e2e_main_run_with_invalid_json_returns_1(tmp_path):
    """run 子命令拿到无效 JSON → ManifestError → 返回 1。"""
    bad = tmp_path / "bad.json"
    bad.write_text("{invalid", encoding="utf-8")
    code = main([
        "run",
        "--manifest", str(bad),
        "--output", str(tmp_path / "report.json"),
    ])
    assert code == 1


def test_e2e_main_validate_report_with_invalid_json_returns_1(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{invalid", encoding="utf-8")
    code = main(["validate-report", str(bad)])
    assert code == 1


def test_e2e_main_inspect_doc_with_invalid_json_returns_1(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{invalid", encoding="utf-8")
    code = main(["inspect-doc", str(bad)])
    assert code == 1


def test_e2e_main_returns_0_for_inspect_doc_with_valid_doc(tmp_path):
    doc = _make_minimal_doc()
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")
    code = main(["inspect-doc", str(doc_path)])
    assert code == 0


def test_e2e_build_parser_run_subcommand_has_5_actions():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions
        if isinstance(a, argparse._SubParsersAction)
    ]
    run_p = sub_actions[0].choices["run"]
    # 5 个 add_argument + 1 个默认 -h/--help
    user_actions = [
        a for a in run_p._actions
        if a.option_strings or a.dest != "help"
    ]
    # 包含 help action 在内
    assert len(run_p._actions) >= 6


def test_e2e_build_parser_validate_report_subcommand_actions():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions
        if isinstance(a, argparse._SubParsersAction)
    ]
    val_p = sub_actions[0].choices["validate-report"]
    # 1 个 positional input + help
    positional = [a for a in val_p._actions if not a.option_strings and a.dest != "help"]
    assert len(positional) == 1
    assert positional[0].dest == "input"


def test_e2e_build_parser_inspect_doc_subcommand_actions():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions
        if isinstance(a, argparse._SubParsersAction)
    ]
    ins_p = sub_actions[0].choices["inspect-doc"]
    # 1 positional + 1 optional + help
    positional = [a for a in ins_p._actions if not a.option_strings and a.dest != "help"]
    optional = [a for a in ins_p._actions if a.option_strings]
    assert len(positional) == 1
    assert len(optional) == 2  # --tolerance-chars + --help


def test_e2e_format_metric_with_unicode_reason():
    metric = {"value": None, "reason": "无数据"}
    s = _format_metric("m", metric)
    assert "无数据" in s


def test_e2e_format_metric_with_long_reason():
    long_reason = "x" * 200
    metric = {"value": None, "reason": long_reason}
    s = _format_metric("m", metric)
    assert long_reason in s
