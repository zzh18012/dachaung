"""evaluation/cli.py 第三十五轮 edges 测试（Round 376）。

重点补强 edges34 未触及的角度：
- _build_parser 行为深度第八批（错误用法、help 文本细节）
- argparse Namespace 字段第八批（更多边界）
- _format_metric 行为深度第八批（更多类型组合）
- _run_inspect_doc 行为深度第八批（错误路径、排序细节）
- main 路由深度第八批（validate-report/inspect-doc 错误码）
- module source forbidden tokens 第十一批
- module source 字符串精确补强第六批
- signatures 第八批
- module 合理性第八批
- 端到端集成第八批
"""

from __future__ import annotations

import argparse
import inspect
import json
import types
from pathlib import Path

import pytest

from evaluation import cli as cmod
from evaluation.cli import (
    _build_parser,
    _format_metric,
    _run_inspect_doc,
    main,
)


# ---------- _build_parser 行为深度第八批 ----------


def test_build_parser_choices_for_parser_only_fallback_and_kreuzberg():
    """--parser 只能选 fallback 或 kreuzberg."""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json", "--parser", "fallback"])
    assert args.parser == "fallback"


def test_build_parser_invalid_parser_choice_raises_system_exit(capsys):
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "a.json", "--output", "b.json", "--parser", "invalid"])


def test_build_parser_max_chars_accepts_negative():
    """argparse type=int 不强制正数（业务上可能不合逻辑，但 CLI 层不挡）."""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json", "--max-chars", "-1"])
    assert args.max_chars == -1


def test_build_parser_max_chars_rejects_string():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "a.json", "--output", "b.json", "--max-chars", "abc"])


def test_build_parser_tolerance_chars_type_int():
    p = _build_parser()
    args = p.parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json", "--tolerance-chars", "100"]
    )
    assert args.tolerance_chars == 100
    assert isinstance(args.tolerance_chars, int)


def test_build_parser_inspect_doc_tolerance_chars_type_int():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "50"])
    assert args.tolerance_chars == 50
    assert isinstance(args.tolerance_chars, int)


def test_build_parser_run_requires_manifest():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "b.json"])


def test_build_parser_run_requires_output():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "a.json"])


def test_build_parser_run_requires_both():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run"])


def test_build_parser_validate_report_takes_positional_input():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"


def test_build_parser_inspect_doc_takes_positional_input():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.input == "doc.json"


def test_build_parser_validate_report_no_optional_flags():
    p = _build_parser()
    args = p.parse_args(["validate-report", "r.json"])
    # validate-report 没有 --parser / --max-chars / --tolerance-chars
    assert not hasattr(args, "parser")
    assert not hasattr(args, "max_chars")
    assert not hasattr(args, "tolerance_chars")


def test_build_parser_run_subparser_help_includes_manifest(capsys):
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--help"])
    captured = capsys.readouterr()
    assert "--manifest" in captured.out
    assert "--output" in captured.out
    assert "--parser" in captured.out
    assert "--max-chars" in captured.out
    assert "--tolerance-chars" in captured.out


def test_build_parser_inspect_doc_subparser_help_includes_tolerance(capsys):
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["inspect-doc", "--help"])
    captured = capsys.readouterr()
    assert "--tolerance-chars" in captured.out


def test_build_parser_validate_report_subparser_no_optional_flags_in_help(capsys):
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["validate-report", "--help"])
    captured = capsys.readouterr()
    assert "--manifest" not in captured.out
    assert "--parser" not in captured.out


def test_build_parser_description_exact_wording():
    p = _build_parser()
    assert p.description == "评测 CLI：跑开发集 → 报告；或校验已有报告。"


def test_build_parser_prog_exact():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_no_subparser_default_choice():
    """subparser required=True，没给子命令应 SystemExit."""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


# ---------- argparse Namespace 字段第八批 ----------


def test_namespace_run_parser_default_value_is_str():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert isinstance(args.parser, str)


def test_namespace_run_manifest_value_is_str():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert isinstance(args.manifest, str)


def test_namespace_run_output_value_is_str():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert isinstance(args.output, str)


def test_namespace_run_all_attributes():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    for attr in ("command", "manifest", "output", "parser", "max_chars", "tolerance_chars"):
        assert hasattr(args, attr), f"missing attr: {attr}"


def test_namespace_validate_report_only_command_and_input():
    p = _build_parser()
    args = p.parse_args(["validate-report", "r.json"])
    assert hasattr(args, "command")
    assert hasattr(args, "input")


def test_namespace_inspect_doc_command_and_input_and_tolerance():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "d.json"])
    assert hasattr(args, "command")
    assert hasattr(args, "input")
    assert hasattr(args, "tolerance_chars")


def test_namespace_run_dash_replaced_with_underscore():
    """--max-chars → max_chars, --tolerance-chars → tolerance_chars."""
    p = _build_parser()
    args = p.parse_args(
        ["run", "--manifest", "a", "--output", "b", "--max-chars", "100", "--tolerance-chars", "20"]
    )
    assert args.max_chars == 100
    assert args.tolerance_chars == 20


def test_namespace_inspect_doc_dash_replaced_with_underscore():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "d.json", "--tolerance-chars", "5"])
    assert args.tolerance_chars == 5


# ---------- _format_metric 行为深度第八批 ----------


def test_format_metric_int_value_with_no_reason():
    s = _format_metric("count", {"value": 42})
    assert "42" in s
    assert "ok" in s


def test_format_metric_int_value_with_reason():
    s = _format_metric("count", {"value": 42, "reason": "specific reason"})
    assert "42" in s
    assert "specific reason" in s


def test_format_metric_negative_int_value():
    s = _format_metric("delta", {"value": -5})
    assert "-5" in s


def test_format_metric_float_zero_value():
    s = _format_metric("ratio", {"value": 0.0})
    assert "0.0000" in s


def test_format_metric_float_just_below_one():
    s = _format_metric("ratio", {"value": 0.9999})
    assert "0.9999" in s


def test_format_metric_float_very_small():
    s = _format_metric("ratio", {"value": 0.00001})
    assert "0.0000" in s


def test_format_metric_float_with_reason():
    s = _format_metric("ratio", {"value": 0.5, "reason": "half"})
    assert "0.5000" in s
    assert "half" in s


def test_format_metric_dict_value_single_pair():
    s = _format_metric("counts", {"value": {"pdf": 3}})
    assert "pdf=3" in s


def test_format_metric_dict_value_with_int_value():
    s = _format_metric("counts", {"value": {"a": 1, "b": 2}})
    assert "a=1" in s
    assert "b=2" in s


def test_format_metric_dict_value_sorted_by_key():
    s = _format_metric("counts", {"value": {"b": 2, "a": 1}})
    # 排序后 a 在 b 之前
    assert s.index("a=1") < s.index("b=2")


def test_format_metric_dict_value_string_value():
    s = _format_metric("info", {"value": {"k": "v"}})
    assert "k=v" in s


def test_format_metric_dict_value_none_value():
    s = _format_metric("info", {"value": {"k": None}})
    assert "k=None" in s


def test_format_metric_dict_value_bool_value():
    s = _format_metric("info", {"value": {"k": True}})
    assert "k=True" in s


def test_format_metric_dict_value_with_reason():
    s = _format_metric("info", {"value": {"k": 1}, "reason": "details"})
    assert "k=1" in s
    assert "details" in s


def test_format_metric_tuple_value_falls_to_default():
    """tuple 不匹配 None/bool/float/dict，走 default 分支."""
    s = _format_metric("t", {"value": (1, 2)})
    assert "(1, 2)" in s


def test_format_metric_set_value_falls_to_default():
    s = _format_metric("s", {"value": {1, 2}})
    # set 的 str 表示是 {1, 2}
    assert "1" in s and "2" in s


def test_format_metric_zero_int_value():
    s = _format_metric("z", {"value": 0})
    assert "0" in s


def test_format_metric_negative_float_value():
    s = _format_metric("n", {"value": -0.5})
    assert "-0.5000" in s


def test_format_metric_unicode_name():
    s = _format_metric("中文", {"value": 1})
    assert "中文" in s


def test_format_metric_renders_padding_36_chars():
    """name 字段应被填充到 36 字符."""
    s = _format_metric("ab", {"value": 1})
    # 36 chars padding: "  " + name + spaces + value
    # 实际格式："  {name:36} ..."
    lines = s.split("\n")
    # name 部分应在第 3 个字符开始（前 2 个 space）+ 36 width
    assert s.startswith("  ab")
    # 找到 "ab" 后到 value 之间应是空格
    after_name = s[2 + 2:]  # skip "  ab"
    # 应是空格直到 value
    assert after_name.startswith(" ")


def test_format_metric_returns_non_empty_str_for_all_inputs():
    """对任何 dict 输入都不应返回空."""
    test_cases = [
        {"value": None, "reason": "x"},
        {"value": True},
        {"value": False},
        {"value": 0},
        {"value": 0.0},
        {"value": ""},
        {"value": []},
        {"value": {}},
        {"value": (1,)},
        {"value": 1.5},
    ]
    for tc in test_cases:
        s = _format_metric("n", tc)
        assert isinstance(s, str)
        assert len(s) > 0


# ---------- _run_inspect_doc 行为深度第八批 ----------


def test_run_inspect_doc_missing_file_returns_2(tmp_path, capsys):
    args = argparse.Namespace(input=str(tmp_path / "missing.json"), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_run_inspect_doc_invalid_json_returns_1(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{not valid json", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "[ERROR]" in err
    assert "JSON" in err or "json" in err


def test_run_inspect_doc_top_level_not_dict_returns_1(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_run_inspect_doc_top_level_int_returns_1(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("42", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_top_level_null_returns_1(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("null", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_empty_dict_returns_0(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_prints_filename(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "file:" in out
    assert "doc.json" in out


def test_run_inspect_doc_prints_document_id(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text('{"document_id": "doc42"}', encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "document_id:" in out
    assert "doc42" in out


def test_run_inspect_doc_document_id_missing_prints_question_mark(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "document_id:" in out
    assert "?" in out


def test_run_inspect_doc_prints_source_path(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text('{"source_path": "/some/path.pdf"}', encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "/some/path.pdf" in out


def test_run_inspect_doc_prints_parser_name(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text('{"parser_name": "fallback", "parser_version": "1.2.3"}', encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "fallback" in out
    assert "1.2.3" in out


def test_run_inspect_doc_default_source_type_unknown(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "type=unknown" in out


def test_run_inspect_doc_explicit_source_type_pdf(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text('{"source_type": "pdf"}', encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "type=pdf" in out


def test_run_inspect_doc_prints_metrics_header(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_with_elements_and_chunks(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({
            "elements": [{"element_id": "e1"}, {"element_id": "e2"}],
            "chunks": [{"chunk_id": "c1"}],
        }),
        encoding="utf-8",
    )
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "elements=2" in out
    assert "chunks=1" in out


def test_run_inspect_doc_with_unicode_in_doc(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"document_id": "测试", "source_path": "/路径/文件.pdf"}),
        encoding="utf-8",
    )
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "测试" in out


def test_run_inspect_doc_args_namespace_type():
    """_run_inspect_doc 接受 argparse.Namespace."""
    args = argparse.Namespace(input="dummy", tolerance_chars=30)
    assert isinstance(args, argparse.Namespace)


# ---------- main 路由深度第八批 ----------


def test_main_validate_report_missing_file_returns_2(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_1(tmp_path, capsys):
    p = tmp_path / "r.json"
    p.write_text("{not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON" in err or "json" in err


def test_main_validate_report_invalid_schema_returns_1(tmp_path, capsys):
    """通过的 JSON 但 schema 不合."""
    p = tmp_path / "r.json"
    p.write_text('{"random": "data"}', encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_missing_file_returns_2(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_inspect_doc_invalid_json_returns_1(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{bad", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_top_level_not_dict_returns_1(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("[1, 2]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_success_returns_0(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_run_missing_manifest_returns_2(tmp_path, capsys):
    rc = main(["run", "--manifest", str(tmp_path / "missing.json"), "--output", str(tmp_path / "o.json")])
    assert rc == 2


def test_main_run_with_invalid_manifest_json_returns_1(tmp_path, capsys):
    """manifest 文件存在但不是 JSON."""
    m = tmp_path / "m.json"
    m.write_text("{bad", encoding="utf-8")
    rc = main(["run", "--manifest", str(m), "--output", str(tmp_path / "o.json")])
    assert rc == 1


def test_main_run_with_invalid_manifest_schema_returns_1(tmp_path, capsys):
    """manifest 是 JSON 但 schema 不合."""
    m = tmp_path / "m.json"
    m.write_text('{"random": "data"}', encoding="utf-8")
    rc = main(["run", "--manifest", str(m), "--output", str(tmp_path / "o.json")])
    assert rc == 1


def test_main_returns_int_for_all_paths(tmp_path):
    """main 的所有路径都返回 int."""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert isinstance(rc, int)


def test_main_no_subcommand_exits_nonzero():
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code != 0


def test_main_unknown_subcommand_exits_nonzero():
    with pytest.raises(SystemExit) as exc_info:
        main(["bogus"])
    assert exc_info.value.code != 0


def test_main_run_with_invalid_parser_choice_exits_nonzero():
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "a", "--output", "b", "--parser", "bogus"])


# ---------- module source forbidden tokens 第十一批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "subprocess.run",
        "subprocess.call",
        "subprocess.check_output",
        "subprocess.check_call",
        "shutil.rmtree",
        "shutil.copy",
        "shutil.move",
        "glob.glob",
        "pickle.loads",
        "pickle.load",
        "marshal.loads",
        "ctypes.CDLL",
        "sys.exit",
        "__import__",
        "importlib.import_module",
        "requests.get",
        "urllib.request",
        "http.client",
        "socket.socket",
        "webbrowser.open",
        "antigravity",
        "this",
        "exit(",
        "quit(",
        "exec(",
        "eval(",
        "compile(",
    ],
)
def test_cli_source_no_forbidden_token_eleventh(token):
    src = inspect.getsource(cmod)
    assert token not in src


# ---------- module source 字符串精确补强第六批 ----------


def test_module_source_has_future_annotations():
    src = inspect.getsource(cmod)
    assert "from __future__ import annotations" in src


def test_module_source_imports_argparse():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_source_imports_json():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_source_imports_sys():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_source_imports_path():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_source_imports_manifest_error():
    src = inspect.getsource(cmod)
    assert "ManifestError" in src


def test_module_source_imports_load_manifest():
    src = inspect.getsource(cmod)
    assert "load_manifest" in src


def test_module_source_imports_get_git_provenance():
    src = inspect.getsource(cmod)
    assert "get_git_provenance" in src


def test_module_source_imports_run_evaluation():
    src = inspect.getsource(cmod)
    assert "run_evaluation" in src


def test_module_source_imports_eval_schema_error():
    src = inspect.getsource(cmod)
    assert "EvalSchemaError" in src


def test_module_source_imports_validate_file():
    src = inspect.getsource(cmod)
    assert "validate_file" in src


def test_module_source_has_4_user_functions():
    src = inspect.getsource(cmod)
    assert "def _build_parser(" in src
    assert "def main(" in src
    assert "def _format_metric(" in src
    assert "def _run_inspect_doc(" in src


def test_module_source_no_class_definitions():
    src = inspect.getsource(cmod)
    assert "\nclass " not in src
    assert not src.startswith("class ")


def test_module_source_no_yield():
    src = inspect.getsource(cmod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(cmod)
    assert "async def " not in src


def test_module_source_no_walrus():
    src = inspect.getsource(cmod)
    assert ":=" not in src


def test_module_source_no_global_keyword():
    src = inspect.getsource(cmod)
    assert "\nglobal " not in src


def test_module_source_no_lambda():
    src = inspect.getsource(cmod)
    assert "lambda " not in src


def test_module_source_no_sleep():
    src = inspect.getsource(cmod)
    assert "time.sleep" not in src


def test_module_source_no_hardcoded_absolute_path():
    src = inspect.getsource(cmod)
    assert "C:\\\\Users" not in src
    assert "C:/Users" not in src
    assert "/home/" not in src


def test_module_source_uses_argparse_raw_description():
    src = inspect.getsource(cmod)
    assert "RawDescriptionHelpFormatter" in src


def test_module_source_main_block_uses_raise_system_exit():
    src = inspect.getsource(cmod)
    assert 'if __name__ == "__main__":' in src
    assert "raise SystemExit(main())" in src


def test_module_source_subparsers_required_true():
    src = inspect.getsource(cmod)
    assert 'required=True' in src


def test_module_source_has_3_subparsers():
    src = inspect.getsource(cmod)
    assert '"run"' in src
    assert '"validate-report"' in src
    assert '"inspect-doc"' in src
    assert src.count("add_parser(") >= 3


def test_module_source_choices_for_parser():
    src = inspect.getsource(cmod)
    assert '"fallback"' in src and '"kreuzberg"' in src


def test_module_source_docstring_mentions_run():
    src = inspect.getsource(cmod)
    assert "run" in src[:600]


def test_module_source_docstring_mentions_validate():
    src = inspect.getsource(cmod)
    assert "validate" in src[:600]


def test_module_source_docstring_mentions_inspect():
    src = inspect.getsource(cmod)
    assert "inspect" in src[:600]


def test_module_source_docstring_mentions_python_m():
    src = inspect.getsource(cmod)
    assert "python -m evaluation.cli" in src[:600]


# ---------- signatures 第八批 ----------


def test_signature_main_argv_annotation():
    sig = inspect.signature(main)
    a = sig.parameters["argv"]
    assert "list" in str(a.annotation)


def test_signature_main_argv_optional():
    sig = inspect.signature(main)
    a = sig.parameters["argv"]
    assert a.default is None


def test_signature_main_return_annotation_int():
    sig = inspect.signature(main)
    ra = str(sig.return_annotation)
    assert "int" in ra


def test_signature_main_no_var_positional():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_main_no_var_keyword():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_main_2_params_count():
    """main(argv=None) 实际上只有 argv 一个参数."""
    sig = inspect.signature(main)
    assert len(sig.parameters) == 1


def test_signature_build_parser_no_params():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_build_parser_return_argparse_namespace_or_parser():
    sig = inspect.signature(_build_parser)
    ra = str(sig.return_annotation)
    assert "ArgumentParser" in ra or "Namespace" in ra or "Parser" in ra


def test_signature_format_metric_2_params():
    sig = inspect.signature(_format_metric)
    assert len(sig.parameters) == 2


def test_signature_format_metric_name_kind_positional_or_keyword():
    sig = inspect.signature(_format_metric)
    p = sig.parameters["name"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_format_metric_metric_kind_positional_or_keyword():
    sig = inspect.signature(_format_metric)
    p = sig.parameters["metric"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_format_metric_no_default():
    sig = inspect.signature(_format_metric)
    assert sig.parameters["name"].default is inspect.Parameter.empty
    assert sig.parameters["metric"].default is inspect.Parameter.empty


def test_signature_run_inspect_doc_1_param():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1


def test_signature_run_inspect_doc_args_no_default():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.parameters["args"].default is inspect.Parameter.empty


def test_signature_all_4_functions_function_type():
    assert isinstance(_build_parser, types.FunctionType)
    assert isinstance(main, types.FunctionType)
    assert isinstance(_format_metric, types.FunctionType)
    assert isinstance(_run_inspect_doc, types.FunctionType)


def test_signature_all_4_module_eq():
    assert _build_parser.__module__ == cmod.__name__
    assert main.__module__ == cmod.__name__
    assert _format_metric.__module__ == cmod.__name__
    assert _run_inspect_doc.__module__ == cmod.__name__


# ---------- module 合理性第八批 ----------


def test_module_has_no_all_attribute():
    """cli 模块没有 __all__."""
    assert not hasattr(cmod, "__all__")


def test_module_has_dunder_file():
    assert hasattr(cmod, "__file__")


def test_module_dunder_file_endswith_cli_py():
    assert cmod.__file__.replace("\\", "/").endswith("evaluation/cli.py")


def test_module_name_is_evaluation_cli():
    assert cmod.__name__ == "evaluation.cli"


def test_module_user_function_count():
    own_funcs = [
        obj for obj in vars(cmod).values()
        if isinstance(obj, types.FunctionType) and obj.__module__ == cmod.__name__
    ]
    assert len(own_funcs) == 4


def test_module_function_names():
    own_func_names = {
        obj.__name__ for obj in vars(cmod).values()
        if isinstance(obj, types.FunctionType) and obj.__module__ == cmod.__name__
    }
    assert own_func_names == {"_build_parser", "main", "_format_metric", "_run_inspect_doc"}


def test_module_main_block_at_end():
    """__main__ 块应在文件末尾."""
    src = inspect.getsource(cmod)
    main_block_pos = src.rfind('if __name__ == "__main__":')
    assert main_block_pos > 0
    # 之后应只有 raise SystemExit(main())
    after = src[main_block_pos:]
    assert "raise SystemExit(main())" in after


def test_module_constants_only_all():
    """模块级大写常量应只来自 imports."""
    for name in dir(cmod):
        if name.startswith("__"):
            continue
        if name.isupper() or (name[:1].isupper() and "_" not in name):
            obj = getattr(cmod, name)
            if isinstance(obj, str) and name != "__all__":
                src = inspect.getsource(cmod)
                pattern = f"{name} = "
                top_level_assign = any(
                    line.startswith(pattern) for line in src.splitlines()
                )
                assert not top_level_assign, (
                    f"{name} should be imported, not assigned at module level"
                )


def test_module_no_call_at_top_level():
    """模块顶层（不缩进）不应有显式的 print/exit 类副作用调用."""
    src = inspect.getsource(cmod)
    in_triple = False
    triple_quote = None
    suspicious_patterns = ("os.system(", "subprocess.", "exit(", "quit(")
    for line in src.splitlines():
        if in_triple:
            if triple_quote and triple_quote in line:
                in_triple = False
                triple_quote = None
            continue
        ls = line.lstrip()
        for q in ('"""', "'''"):
            if ls.startswith(q):
                rest = ls[3:]
                if rest.count(q) >= 1:
                    pass
                else:
                    in_triple = True
                    triple_quote = q
                break
        for pat in suspicious_patterns:
            # 允许 raise SystemExit(main()) — exit( 是 sys.exit 的禁止
            if pat == "exit(" and "SystemExit" in line:
                continue
            assert pat not in line, f"suspicious pattern {pat!r} in {line!r}"


def test_module_docstring_first_line():
    src = inspect.getsource(cmod)
    # 应以 """ 开头
    assert src.startswith('"""')


# ---------- 端到端集成第八批 ----------


def test_e2e_run_subcommand_namespace_with_all_options():
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json",
        "--parser", "kreuzberg", "--max-chars", "500", "--tolerance-chars", "10",
    ])
    assert args.command == "run"
    assert args.manifest == "m.json"
    assert args.output == "o.json"
    assert args.parser == "kreuzberg"
    assert args.max_chars == 500
    assert args.tolerance_chars == 10


def test_e2e_validate_report_namespace():
    p = _build_parser()
    args = p.parse_args(["validate-report", "r.json"])
    assert args.command == "validate-report"
    assert args.input == "r.json"


def test_e2e_inspect_doc_namespace_with_tolerance():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "d.json", "--tolerance-chars", "20"])
    assert args.command == "inspect-doc"
    assert args.input == "d.json"
    assert args.tolerance_chars == 20


def test_e2e_main_run_full_path_with_minimal_manifest(tmp_path, capsys):
    """End-to-end main run with a minimal but valid manifest."""
    # 创建一个空 manifest（合法）
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    o = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(m), "--output", str(o)])
    assert rc == 0
    assert o.is_file()
    out = capsys.readouterr().out
    assert "[OK]" in out
    assert "documents=" in out


def test_e2e_main_validate_report_with_valid_report(tmp_path, capsys):
    """构造一个合法 report 让 validate-report 通过."""
    # 先跑一遍 main run 拿到合法 report
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    o = tmp_path / "o.json"
    main(["run", "--manifest", str(m), "--output", str(o)])
    capsys.readouterr()  # clear

    rc = main(["validate-report", str(o)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[OK]" in out


def test_e2e_main_validate_report_with_missing_file(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "no.json")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_e2e_main_inspect_doc_with_minimal_doc(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "metrics:" in out
    assert "file:" in out


def test_e2e_main_inspect_doc_with_rich_doc(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "d42",
        "source_type": "pdf",
        "source_path": "/path/file.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"element_id": "e1"}],
        "chunks": [{"chunk_id": "c1"}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "d42" in out
    assert "type=pdf" in out
    assert "fallback" in out
    assert "elements=1" in out
    assert "chunks=1" in out


def test_e2e_main_inspect_doc_with_custom_tolerance(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "50"])
    assert rc == 0


def test_e2e_main_run_with_kreuzberg_choice(tmp_path, capsys):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    o = tmp_path / "o.json"
    rc = main([
        "run", "--manifest", str(m), "--output", str(o),
        "--parser", "kreuzberg", "--max-chars", "300",
    ])
    assert rc == 0


def test_e2e_main_run_with_custom_tolerance(tmp_path, capsys):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    o = tmp_path / "o.json"
    rc = main([
        "run", "--manifest", str(m), "--output", str(o),
        "--tolerance-chars", "100",
    ])
    assert rc == 0


def test_e2e_main_run_writes_report_with_correct_version(tmp_path):
    from evaluation import REPORT_VERSION
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    o = tmp_path / "o.json"
    main(["run", "--manifest", str(m), "--output", str(o)])
    report = json.loads(o.read_text(encoding="utf-8"))
    assert report["report_version"] == REPORT_VERSION


def test_e2e_main_run_stdout_includes_devset_info(tmp_path, capsys):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    o = tmp_path / "o.json"
    main(["run", "--manifest", str(m), "--output", str(o)])
    out = capsys.readouterr().out
    assert "devset_status=" in out
    assert "file_count=" in out
    assert "git_commit=" in out
    assert "git_dirty=" in out


def test_e2e_main_unknown_subcommand_returns_nonzero():
    with pytest.raises(SystemExit) as exc_info:
        main(["totally-unknown"])
    assert exc_info.value.code != 0


def test_e2e_argparse_prog_in_help(capsys):
    """--help 输出包含 prog 名."""
    with pytest.raises(SystemExit):
        main(["--help"])
    captured = capsys.readouterr()
    assert "evaluation.cli" in captured.out
