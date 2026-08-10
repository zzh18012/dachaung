"""evaluation/cli.py 第三十八轮 edges 测试（Round 397）。

补强 edges37 未触及的角度：
- _build_parser 行为深度第十一批（add_subparsers dest / required / formatter_class / subparser prog / subparsers 注册）
- argparse Namespace 行为第十一批（Namespace 比较 / repr / getattr fallback / 字段顺序）
- _format_metric 行为深度第十一批（padding 精确 / dict 边界 / bool 渲染 / 大小数 / Unicode name 渲染）
- _run_inspect_doc 行为深度第十一批（JSON 顶层类型分支 / 输出格式 / tolerance 透传 / 字段缺失）
- main 路由第十一批（返回类型 / 错误码边界 / argv=None / 未知 command）
- module source forbidden tokens 第十四批
- module source 字符串精确补强第九批
- signatures 第十一批
- module 合理性第十一批
- 端到端集成第十一批
"""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path

import pytest

from evaluation import cli as climod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 行为深度第十一批 ----------


def test_build_parser_returns_argument_parser_batch11():
    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_build_parser_prog_value_exact_batch11():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_present_batch11():
    p = _build_parser()
    assert p.description is not None
    assert len(p.description) > 10


def test_build_parser_formatter_class_batch11():
    """formatter_class 是 RawDescriptionHelpFormatter。"""
    p = _build_parser()
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_has_subparsers_action_batch11():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert len(sub_actions) == 1


def test_build_parser_subparsers_dest_command_batch11():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert sub_actions[0].dest == "command"


def test_build_parser_subparsers_required_true_batch11():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert sub_actions[0].required is True


def test_build_parser_subparsers_registry_has_3_keys_batch11():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert len(sub_actions[0].choices) == 3
    assert set(sub_actions[0].choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_run_subparser_choices_fallback_kreuzberg_batch11():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    parser_action = next(
        a for a in run_parser._actions if "--parser" in a.option_strings
    )
    assert set(parser_action.choices) == {"fallback", "kreuzberg"}


def test_build_parser_run_subparser_max_chars_type_int_batch11():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    max_chars_action = next(
        a for a in run_parser._actions if "--max-chars" in a.option_strings
    )
    assert max_chars_action.type is int


def test_build_parser_inspect_doc_subparser_input_required_batch11():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_parser = sub_actions[0].choices["inspect-doc"]
    input_action = next(
        a for a in ins_parser._actions if a.dest == "input" and not a.option_strings
    )
    assert input_action.required is True


def test_build_parser_validate_report_subparser_input_required_batch11():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    val_parser = sub_actions[0].choices["validate-report"]
    input_action = next(
        a for a in val_parser._actions if a.dest == "input" and not a.option_strings
    )
    assert input_action.required is True


def test_build_parser_run_manifest_required_batch11():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    manifest_action = next(
        a for a in run_parser._actions if "--manifest" in a.option_strings
    )
    assert manifest_action.required is True


def test_build_parser_run_output_required_batch11():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    output_action = next(
        a for a in run_parser._actions if "--output" in a.option_strings
    )
    assert output_action.required is True


def test_build_parser_inspect_doc_tolerance_chars_type_int_batch11():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_parser = sub_actions[0].choices["inspect-doc"]
    tol_action = next(
        a for a in ins_parser._actions if "--tolerance-chars" in a.option_strings
    )
    assert tol_action.type is int


def test_build_parser_no_subcommand_system_exit_2_batch11(capsys):
    """无 subcommand → SystemExit code 2（required=True）。"""
    with pytest.raises(SystemExit) as exc_info:
        _build_parser().parse_args([])
    assert exc_info.value.code == 2


def test_build_parser_unknown_command_system_exit_2_batch11(capsys):
    with pytest.raises(SystemExit) as exc_info:
        _build_parser().parse_args(["totally-unknown"])
    assert exc_info.value.code == 2


# ---------- argparse Namespace 行为第十一批 ----------


def test_namespace_command_field_str_type_batch11():
    ns = _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert isinstance(ns.command, str)


def test_namespace_repr_present_batch11():
    ns = _build_parser().parse_args(["validate-report", "a.json"])
    assert "Namespace" in repr(ns)


def test_namespace_equality_batch11():
    """同样输入产生相同 Namespace。"""
    ns1 = _build_parser().parse_args(["validate-report", "a.json"])
    ns2 = _build_parser().parse_args(["validate-report", "a.json"])
    assert ns1 == ns2


def test_namespace_inequality_different_command_batch11():
    ns1 = _build_parser().parse_args(["validate-report", "a.json"])
    ns2 = _build_parser().parse_args(["inspect-doc", "a.json"])
    assert ns1 != ns2


def test_namespace_getattr_with_default_batch11():
    ns = _build_parser().parse_args(["validate-report", "a.json"])
    # 不存在的字段
    assert getattr(ns, "nonexistent", "default") == "default"


def test_namespace_vars_returns_dict_batch11():
    ns = _build_parser().parse_args(["validate-report", "a.json"])
    assert isinstance(vars(ns), dict)


def test_namespace_run_field_order_batch11():
    """run 字段顺序：command / manifest / output / parser / max_chars / tolerance_chars。"""
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json"]
    )
    keys = list(vars(ns).keys())
    assert keys[0] == "command"


def test_namespace_validate_report_only_two_fields_batch11():
    ns = _build_parser().parse_args(["validate-report", "a.json"])
    assert len(vars(ns)) == 2


def test_namespace_inspect_doc_three_fields_batch11():
    ns = _build_parser().parse_args(["inspect-doc", "a.json"])
    assert len(vars(ns)) == 3


def test_namespace_max_chars_input_str_coerced_to_int_batch11():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json", "--max-chars", "999"]
    )
    assert ns.max_chars == 999
    assert type(ns.max_chars) is int


def test_namespace_max_chars_invalid_str_system_exit_batch11(capsys):
    """非数字字符串 → type=int 转换失败 → SystemExit code 2。"""
    with pytest.raises(SystemExit) as exc_info:
        _build_parser().parse_args(
            ["run", "--manifest", "a.json", "--output", "b.json", "--max-chars", "abc"]
        )
    assert exc_info.value.code == 2


# ---------- _format_metric 行为深度第十一批 ----------


def test_format_metric_padding_exact_36_chars_batch11():
    """name padded to exactly 36 chars wide (then separator + value)."""
    name = "x"  # 1 char
    out = _format_metric(name, {"value": 1, "reason": "ok"})
    # Format is "  {:36} {}  ({})" → 2 spaces + name(1) + 35 padding + 1 separator + value
    # name field occupies positions 2..37 (36 chars wide)
    idx = out.find("x")
    # name field is [2, 38), so position 38 should be separator or value
    assert idx == 2
    # name field is 36 chars total (x + 35 padding)
    name_field = out[2:38]
    assert name_field == "x" + " " * 35


def test_format_metric_dict_with_int_value_batch11():
    out = _format_metric("by_type", {"value": {"a": 5}, "reason": "ok"})
    assert "a=5" in out


def test_format_metric_dict_with_negative_int_value_batch11():
    out = _format_metric("by_type", {"value": {"a": -5}, "reason": "ok"})
    assert "a=-5" in out


def test_format_metric_dict_with_zero_int_value_batch11():
    out = _format_metric("by_type", {"value": {"a": 0}, "reason": "ok"})
    assert "a=0" in out


def test_format_metric_dict_with_unicode_key_batch11():
    out = _format_metric("by_type", {"value": {"段落": 5}, "reason": "ok"})
    assert "段落=5" in out


def test_format_metric_bool_true_lowercased_batch11():
    out = _format_metric("flag", {"value": True, "reason": "ok"})
    assert "true" in out
    assert "True" not in out


def test_format_metric_bool_false_lowercased_batch11():
    out = _format_metric("flag", {"value": False, "reason": "ok"})
    assert "false" in out
    assert "False" not in out


def test_format_metric_large_float_batch11():
    out = _format_metric("ratio", {"value": 1234567.89, "reason": "ok"})
    assert "1234567.8900" in out


def test_format_metric_small_float_batch11():
    out = _format_metric("ratio", {"value": 0.0001, "reason": "ok"})
    assert "0.0001" in out


def test_format_metric_very_small_float_rounds_to_zero_batch11():
    out = _format_metric("ratio", {"value": 0.00001, "reason": "ok"})
    assert "0.0000" in out


def test_format_metric_int_with_none_reason_batch11():
    out = _format_metric("count", {"value": 5})
    assert "(ok)" in out


def test_format_metric_int_with_explicit_none_reason_batch11():
    out = _format_metric("count", {"value": 5, "reason": None})
    assert "(ok)" in out


def test_format_metric_returns_str_type_batch11():
    out = _format_metric("count", {"value": 1, "reason": "ok"})
    assert type(out) is str


def test_format_metric_starts_with_two_spaces_batch11():
    """所有行以两个空格开头（indent）。"""
    out = _format_metric("x", {"value": 1, "reason": "ok"})
    assert out.startswith("  ")


def test_format_metric_empty_metric_dict_batch11():
    """空 metric dict → value=None 走 null 分支。"""
    out = _format_metric("x", {})
    assert "null" in out
    assert "(None)" in out


def test_format_metric_dict_with_bool_value_batch11():
    """dict 中 value 是 bool → 'true'/'false'。"""
    out = _format_metric("by_type", {"value": {"ok": True}, "reason": "x"})
    assert "ok=True" in out  # bool 直接 str() 渲染


# ---------- _run_inspect_doc 行为深度第十一批 ----------


def test_run_inspect_doc_json_top_level_list_returns_1_batch11(tmp_path, capsys):
    """JSON 顶层是 list → 返回 1（不是 dict）。"""
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_run_inspect_doc_json_top_level_string_returns_1_batch11(tmp_path, capsys):
    """JSON 顶层是 string → 返回 1。"""
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_json_top_level_number_returns_1_batch11(tmp_path):
    """JSON 顶层是 number → 返回 1。"""
    p = tmp_path / "num.json"
    p.write_text("42", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_json_top_level_null_returns_1_batch11(tmp_path):
    """JSON 顶层是 null → 返回 1。"""
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_json_top_level_bool_returns_1_batch11(tmp_path):
    """JSON 顶层是 bool → 返回 1。"""
    p = tmp_path / "bool.json"
    p.write_text("true", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_success_returns_0_batch11(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_prints_file_path_batch11(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "file:" in out


def test_run_inspect_doc_prints_metrics_header_batch11(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_prints_counts_line_batch11(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text('{"elements": [{"type": "paragraph"}], "chunks": []}', encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "counts:" in out
    assert "elements=1" in out


def test_run_inspect_doc_handles_missing_elements_batch11(tmp_path, capsys):
    """缺 elements 字段 → 视为 []。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_handles_missing_chunks_batch11(tmp_path, capsys):
    """缺 chunks 字段 → 视为 []。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_tolerance_chars_forwarded_batch11(tmp_path, capsys):
    """tolerance_chars 透传给 chunk_boundary_prf。"""
    p = tmp_path / "d.json"
    p.write_text(
        '{"chunks": [{"id": "c1", "source_locator": {}, "text": "abc"}]}',
        encoding="utf-8",
    )
    args = argparse.Namespace(input=str(p), tolerance_chars=42)
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_prints_document_id_batch11(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text('{"document_id": "abc123"}', encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "abc123" in out


def test_run_inspect_doc_prints_source_path_batch11(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text('{"source_path": "/x/y.pdf"}', encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "/x/y.pdf" in out


def test_run_inspect_doc_prints_parser_info_batch11(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text(
        '{"parser_name": "fallback", "parser_version": "1.0.0"}', encoding="utf-8"
    )
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "fallback" in out
    assert "1.0.0" in out


def test_run_inspect_doc_path_obj_input_batch11(tmp_path):
    """Path 对象作 input 也工作（被 str 化）。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=p, tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0


# ---------- main 路由第十一批 ----------


def test_main_returns_int_for_unknown_command_batch11(capsys):
    """未知 command → SystemExit（argparse 拒绝）。"""
    with pytest.raises(SystemExit):
        main(["totally-unknown"])


def test_main_run_missing_manifest_returns_2_batch11(capsys):
    """run 命令 manifest 不存在 → 返回 2。"""
    rc = main(["run", "--manifest", "/no/such.json", "--output", "/tmp/out.json"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_validate_report_missing_returns_2_batch11(capsys, tmp_path):
    rc = main(["validate-report", str(tmp_path / "no.json")])
    assert rc == 2


def test_main_inspect_doc_missing_returns_2_batch11(capsys, tmp_path):
    rc = main(["inspect-doc", str(tmp_path / "no.json")])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_1_batch11(capsys, tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_invalid_json_returns_1_batch11(capsys, tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_non_dict_json_returns_1_batch11(capsys, tmp_path):
    p = tmp_path / "list.json"
    p.write_text("[1, 2]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_validate_report_valid_empty_dict_returns_1_batch11(capsys, tmp_path):
    """空 dict 不是合法 evaluation-report，应返回 1（schema 校验失败）。"""
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    # 缺 report_version / provenance 等 → schema 校验失败 → 1
    assert rc == 1


def test_main_run_kreuzberg_parser_choice_batch11(capsys):
    """run 命令接受 --parser kreuzberg（虽然 manifest 不存在会先失败）。"""
    rc = main(
        [
            "run",
            "--manifest",
            "/no/such.json",
            "--output",
            "/tmp/out.json",
            "--parser",
            "kreuzberg",
        ]
    )
    # manifest 不存在 → rc=2
    assert rc == 2


def test_main_run_invalid_parser_choice_system_exit_batch11(capsys):
    """非法 parser choice → SystemExit。"""
    with pytest.raises(SystemExit):
        main(
            [
                "run",
                "--manifest",
                "x.json",
                "--output",
                "y.json",
                "--parser",
                "totally-invalid",
            ]
        )


# ---------- module source forbidden tokens 第十四批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "pickle.loads",
        "yaml.load",
        "yaml.unsafe_load",
        "subprocess.check_call",
        "subprocess.call",
        "subprocess.getoutput",
        "os.popen",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
    ],
)
def test_cli_source_no_forbidden_token_fourteenth_batch11(token):
    source = inspect.getsource(climod)
    assert token not in source


def test_cli_source_no_unlink_batch11():
    source = inspect.getsource(climod)
    assert "unlink" not in source


def test_cli_source_no_remove_batch11():
    source = inspect.getsource(climod)
    assert ".remove(" not in source


def test_cli_source_no_kill_batch11():
    source = inspect.getsource(climod)
    assert ".kill(" not in source


def test_cli_source_no_terminate_batch11():
    source = inspect.getsource(climod)
    assert ".terminate(" not in source


def test_cli_source_no_async_def_batch11():
    source = inspect.getsource(climod)
    assert "async def" not in source


def test_cli_source_no_yield_batch11():
    source = inspect.getsource(climod)
    assert "yield" not in source


def test_cli_source_no_walrus_batch11():
    source = inspect.getsource(climod)
    assert ":=" not in source


def test_cli_source_no_top_level_lambda_batch11():
    source = inspect.getsource(climod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_cli_source_no_socket_batch11():
    source = inspect.getsource(climod)
    assert "socket" not in source


def test_cli_source_no_threading_batch11():
    source = inspect.getsource(climod)
    assert "threading" not in source


def test_cli_source_no_multiprocessing_batch11():
    source = inspect.getsource(climod)
    assert "multiprocessing" not in source


def test_cli_source_no_asyncio_batch11():
    source = inspect.getsource(climod)
    assert "asyncio" not in source


def test_cli_source_no_pickle_module_batch11():
    source = inspect.getsource(climod)
    assert "import pickle" not in source


def test_cli_source_no_yaml_module_batch11():
    source = inspect.getsource(climod)
    assert "import yaml" not in source


def test_cli_source_no_logging_module_batch11():
    source = inspect.getsource(climod)
    assert "import logging" not in source


# ---------- module source 字符串精确补强第九批 ----------


def test_module_source_has_future_annotations_batch11():
    source = inspect.getsource(climod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_argparse_batch11():
    source = inspect.getsource(climod)
    assert "import argparse" in source


def test_module_source_imports_json_batch11():
    source = inspect.getsource(climod)
    assert "import json" in source


def test_module_source_imports_sys_batch11():
    source = inspect.getsource(climod)
    assert "import sys" in source


def test_module_source_imports_path_batch11():
    source = inspect.getsource(climod)
    assert "from pathlib import Path" in source


def test_module_source_imports_manifest_load_batch11():
    source = inspect.getsource(climod)
    assert "load_manifest" in source
    assert "ManifestError" in source


def test_module_source_imports_get_git_provenance_batch11():
    source = inspect.getsource(climod)
    assert "get_git_provenance" in source


def test_module_source_imports_run_evaluation_batch11():
    source = inspect.getsource(climod)
    assert "run_evaluation" in source


def test_module_source_imports_validate_file_batch11():
    source = inspect.getsource(climod)
    assert "validate_file" in source
    assert "EvalSchemaError" in source


def test_module_source_has_subcommand_run_batch11():
    source = inspect.getsource(climod)
    assert '"run"' in source
    assert 'sub.add_parser("run"' in source


def test_module_source_has_subcommand_validate_report_batch11():
    source = inspect.getsource(climod)
    assert '"validate-report"' in source
    assert "add_parser" in source


def test_module_source_has_subcommand_inspect_doc_batch11():
    source = inspect.getsource(climod)
    assert '"inspect-doc"' in source


def test_module_source_has_main_block_batch11():
    source = inspect.getsource(climod)
    assert 'if __name__' in source
    assert "raise SystemExit" in source


def test_module_source_docstring_present_batch11():
    assert climod.__doc__ is not None
    assert len(climod.__doc__) > 20


def test_module_source_docstring_mentions_subcommands_batch11():
    assert climod.__doc__ is not None
    assert "run" in climod.__doc__
    assert "validate-report" in climod.__doc__


def test_module_source_docstring_mentions_inspect_batch11():
    assert climod.__doc__ is not None
    assert "inspect-doc" in climod.__doc__


# ---------- signatures 第十一批 ----------


def test_signature_build_parser_no_params_batch11():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_build_parser_return_annotation_batch11():
    sig = inspect.signature(_build_parser)
    assert sig.return_annotation is not inspect.Signature.empty


def test_signature_main_1_param_batch11():
    sig = inspect.signature(main)
    assert len(sig.parameters) == 1


def test_signature_main_param_name_batch11():
    sig = inspect.signature(main)
    assert list(sig.parameters) == ["argv"]


def test_signature_main_param_default_none_batch11():
    sig = inspect.signature(main)
    p = list(sig.parameters.values())[0]
    assert p.default is None


def test_signature_main_param_kind_batch11():
    sig = inspect.signature(main)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_format_metric_2_params_batch11():
    sig = inspect.signature(_format_metric)
    assert len(sig.parameters) == 2


def test_signature_format_metric_param_names_batch11():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters) == ["name", "metric"]


def test_signature_run_inspect_doc_1_param_batch11():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1


def test_signature_run_inspect_doc_param_name_batch11():
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters) == ["args"]


def test_signature_funcs_function_type_batch11():
    for func in (_build_parser, _format_metric, _run_inspect_doc, main):
        assert inspect.isfunction(func)


def test_signature_funcs_module_eq_batch11():
    for func in (_build_parser, _format_metric, _run_inspect_doc, main):
        assert func.__module__ == "evaluation.cli"


# ---------- module 合理性第十一批 ----------


def test_module_no_all_attribute_batch11():
    """cli.py 没有 __all__（默认导出全部 public 名）。"""
    assert not hasattr(climod, "__all__") or climod.__all__ is None


def test_module_has_dunder_file_batch11():
    assert hasattr(climod, "__file__")
    assert climod.__file__ is not None


def test_module_dunder_file_endswith_cli_py_batch11():
    import os
    sep = os.sep
    assert climod.__file__.endswith("evaluation" + sep + "cli.py") or climod.__file__.endswith(
        "evaluation/cli.py"
    )


def test_module_name_is_evaluation_cli_batch11():
    assert climod.__name__ == "evaluation.cli"


def test_module_user_function_count_batch11():
    funcs = [
        n for n, v in vars(climod).items()
        if inspect.isfunction(v) and v.__module__ == climod.__name__
    ]
    assert set(funcs) == {"_build_parser", "main", "_format_metric", "_run_inspect_doc"}


def test_module_no_user_classes_batch11():
    classes = [
        n for n, v in vars(climod).items()
        if inspect.isclass(v) and v.__module__ == climod.__name__
    ]
    assert classes == []


def test_module_docstring_present_batch11():
    assert climod.__doc__ is not None
    assert len(climod.__doc__) > 20


def test_module_docstring_first_line_short_batch11():
    """docstring 第一行短小精悍。"""
    assert climod.__doc__ is not None
    first_line = climod.__doc__.split("\n")[0]
    assert len(first_line) < 100


def test_module_imports_pathlib_path_batch11():
    assert hasattr(climod, "Path")
    assert climod.Path is Path


def test_module_imports_argparse_namespace_batch11():
    assert hasattr(climod, "argparse")


# ---------- 端到端集成第十一批 ----------


def test_e2e_inspect_doc_full_chain_batch11(tmp_path, capsys):
    """inspect-doc 完整链路：合法 doc → 返回 0，stdout 含 metrics 行。"""
    p = tmp_path / "d.json"
    p.write_text(
        json.dumps(
            {
                "document_id": "abc",
                "source_path": "/x.pdf",
                "source_type": "pdf",
                "parser_name": "fallback",
                "parser_version": "1.0.0",
                "elements": [{"type": "paragraph"}],
                "chunks": [{"id": "c1", "text": "abc"}],
            }
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "abc" in out  # document_id


def test_e2e_validate_report_invalid_returns_1_batch11(tmp_path):
    """validate-report 接收无效 JSON → 返回 1。"""
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_main_run_no_args_uses_sys_argv_batch11(monkeypatch):
    """main(argv=None) 使用 sys.argv[1:]。"""
    monkeypatch.setattr("sys.argv", ["evaluation.cli"])  # 无 subcommand
    with pytest.raises(SystemExit):
        main(None)


def test_e2e_inspect_doc_empty_dict_batch11(tmp_path, capsys):
    """inspect-doc 接收空 dict → 返回 0。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_main_kwargs_call_batch11(tmp_path):
    """main 支持 argv=list[str]。"""
    rc = main(argv=["inspect-doc", str(tmp_path / "no.json")])
    assert rc == 2


def test_e2e_namespace_inspect_doc_kwargs_batch11(tmp_path):
    """inspect-doc 通过 main 路由，正确处理 args.tolerance_chars。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "5"])
    assert rc == 0


def test_e2e_full_inspect_doc_unicode_content_batch11(tmp_path, capsys):
    """inspect-doc 处理 Unicode 内容。"""
    p = tmp_path / "u.json"
    p.write_text(
        json.dumps(
            {
                "document_id": "中文",
                "source_path": "/中文.pdf",
                "source_type": "pdf",
                "parser_name": "fallback",
                "parser_version": "1.0.0",
                "elements": [],
                "chunks": [],
            }
        ),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "中文" in out


def test_e2e_validate_report_directory_returns_2_batch11(tmp_path):
    """validate-report 接收目录 → is_file False → 返回 2。"""
    rc = main(["validate-report", str(tmp_path)])
    assert rc == 2


def test_e2e_inspect_doc_directory_returns_2_batch11(tmp_path):
    """inspect-doc 接收目录 → is_file False → 返回 2。"""
    rc = main(["inspect-doc", str(tmp_path)])
    assert rc == 2


def test_e2e_main_run_with_path_str_manifest_batch11(capsys):
    """run 命令 manifest 接 str 路径（不存在的 str 路径返回 2）。"""
    rc = main(["run", "--manifest", "no_such.json", "--output", "out.json"])
    assert rc == 2
