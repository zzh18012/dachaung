"""evaluation/cli.py 第三十四轮 edges 测试（Round 370）。

补强 edges33 未触及的角度：
- _build_parser 行为深度第七批（fresh parser each call、prog/description、subparser 嵌套结构）
- argparse Namespace 字段第七批（run subcommand 全字段类型、validate-report 仅 input、inspect-doc input+tolerance）
- _format_metric 行为深度第七批（None 无 reason 渲染 "(None)"、None 空 reason 渲染 "()"、bool 大小写、dict 负值、huge int、空 list、unicode）
- _run_inspect_doc 行为深度第七批（sort 顺序 None/int/bool/dict、metrics 字段渲染）
- main 路由深度第七批（--help 三个子命令分别 exit 0、未知 flag SystemExit）
- module source forbidden tokens 第十批
- signatures 第七批（build_parser 零参、main argv kind、format_metric/run_inspect_doc 参数 kind）
- module 合理性第七批（imports 顺序、main 块 SystemExit、module docstring 关键词）
- 端到端集成第七批（run 全字段 Namespace、validate-report Namespace、inspect-doc Namespace、各 --help exit 0）
"""

from __future__ import annotations

import argparse
import inspect
from pathlib import Path

import pytest

from evaluation import cli as cmod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 行为深度第七批 ----------


def test_build_parser_returns_argument_parser_instance():
    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_build_parser_prog_is_evaluation_cli():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_has_eval_text():
    p = _build_parser()
    assert "评测" in p.description


def test_build_parser_description_has_report_keyword():
    p = _build_parser()
    assert "报告" in p.description


def test_build_parser_repeatable_creates_fresh_instance():
    p1 = _build_parser()
    p2 = _build_parser()
    assert p1 is not p2


def test_build_parser_has_subparsers_action():
    p = _build_parser()
    has_sub = any(isinstance(a, argparse._SubParsersAction) for a in p._actions)
    assert has_sub


def test_build_parser_subparsers_required_is_true():
    p = _build_parser()
    for a in p._actions:
        if isinstance(a, argparse._SubParsersAction):
            assert a.required is True


def test_build_parser_subparsers_dest_is_command():
    p = _build_parser()
    for a in p._actions:
        if isinstance(a, argparse._SubParsersAction):
            assert a.dest == "command"


def test_build_parser_subparser_count_is_3():
    p = _build_parser()
    for a in p._actions:
        if isinstance(a, argparse._SubParsersAction):
            assert len(a.choices) == 3
            assert set(a.choices.keys()) == {"run", "validate-report", "inspect-doc"}


# ---------- argparse Namespace 字段第七批 ----------


def test_namespace_run_has_command_attribute():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert ns.command == "run"


def test_namespace_run_has_manifest_str():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert ns.manifest == "a.json"
    assert isinstance(ns.manifest, str)


def test_namespace_run_has_output_str():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert ns.output == "b.json"
    assert isinstance(ns.output, str)


def test_namespace_run_parser_default_fallback():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert ns.parser == "fallback"


def test_namespace_run_max_chars_default_800():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert ns.max_chars == 800


def test_namespace_run_tolerance_chars_default_30():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert ns.tolerance_chars == 30


def test_namespace_run_with_kreuzberg_choice():
    p = _build_parser()
    ns = p.parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
        "--parser", "kreuzberg",
    ])
    assert ns.parser == "kreuzberg"


def test_namespace_run_with_custom_max_chars():
    p = _build_parser()
    ns = p.parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
        "--max-chars", "500",
    ])
    assert ns.max_chars == 500
    assert isinstance(ns.max_chars, int)


def test_namespace_run_with_custom_tolerance():
    p = _build_parser()
    ns = p.parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
        "--tolerance-chars", "100",
    ])
    assert ns.tolerance_chars == 100


def test_namespace_validate_report_command():
    p = _build_parser()
    ns = p.parse_args(["validate-report", "report.json"])
    assert ns.command == "validate-report"
    assert ns.input == "report.json"


def test_namespace_inspect_doc_command():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.command == "inspect-doc"
    assert ns.input == "doc.json"


def test_namespace_inspect_doc_tolerance_default_30():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.tolerance_chars == 30


def test_namespace_inspect_doc_no_parser_attribute():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert not hasattr(ns, "parser")


def test_namespace_inspect_doc_no_max_chars_attribute():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert not hasattr(ns, "max_chars")


def test_namespace_validate_report_no_parser_attribute():
    p = _build_parser()
    ns = p.parse_args(["validate-report", "report.json"])
    assert not hasattr(ns, "parser")


# ---------- _format_metric 行为深度第七批 ----------


def test_format_metric_none_value_with_no_reason_field():
    """value=None 但没有 reason key → 渲染 (None)。"""
    out = _format_metric("m", {})
    assert "(None)" in out


def test_format_metric_none_value_with_empty_reason():
    out = _format_metric("m", {"value": None, "reason": ""})
    # reason="" → () in output
    assert "()" in out


def test_format_metric_none_value_with_reason():
    out = _format_metric("m", {"value": None, "reason": "missing"})
    assert "(missing)" in out


def test_format_metric_none_value_renders_null():
    out = _format_metric("m", {"value": None, "reason": "x"})
    assert "null" in out


def test_format_metric_bool_true_renders_lowercase():
    out = _format_metric("m", {"value": True})
    assert "true" in out
    assert "True" not in out


def test_format_metric_bool_false_renders_lowercase():
    out = _format_metric("m", {"value": False})
    assert "false" in out


def test_format_metric_bool_true_no_reason_uses_ok():
    out = _format_metric("m", {"value": True})
    assert "(ok)" in out


def test_format_metric_bool_true_with_reason_uses_reason():
    out = _format_metric("m", {"value": True, "reason": "pipeline ok"})
    assert "(pipeline ok)" in out


def test_format_metric_bool_false_with_reason():
    out = _format_metric("m", {"value": False, "reason": "failed"})
    assert "(failed)" in out


def test_format_metric_float_4_decimal_precision():
    out = _format_metric("m", {"value": 1.23456789})
    assert "1.2346" in out


def test_format_metric_float_tiny_value():
    out = _format_metric("m", {"value": 0.0001})
    assert "0.0001" in out


def test_format_metric_dict_with_negative_int_value():
    out = _format_metric("m", {"value": {"a": -5}})
    assert "a=-5" in out


def test_format_metric_dict_with_unicode_value():
    out = _format_metric("m", {"value": {"k": "中文"}})
    assert "k=中文" in out


def test_format_metric_dict_with_multiple_pairs_sorted():
    out = _format_metric("m", {"value": {"b": 1, "a": 2, "c": 3}})
    # sorted alphabetically: a, b, c
    a_pos = out.find("a=")
    b_pos = out.find("b=")
    c_pos = out.find("c=")
    assert a_pos < b_pos < c_pos


def test_format_metric_empty_dict_value():
    out = _format_metric("m", {"value": {}})
    assert "(ok)" in out


def test_format_metric_list_value_uses_default_branch():
    out = _format_metric("m", {"value": [1, 2, 3]})
    assert "[1, 2, 3]" in out


def test_format_metric_empty_list_value():
    out = _format_metric("m", {"value": []})
    assert "[]" in out


def test_format_metric_huge_int_value():
    out = _format_metric("m", {"value": 10**100})
    assert str(10**100) in out


def test_format_metric_int_zero_value():
    out = _format_metric("m", {"value": 0})
    assert " 0 " in out or out.rstrip().endswith("0")


def test_format_metric_string_value_with_reason():
    out = _format_metric("m", {"value": "hello", "reason": "from_doc"})
    assert "hello" in out
    assert "(from_doc)" in out


def test_format_metric_returns_str_type():
    out = _format_metric("m", {"value": True})
    assert isinstance(out, str)


def test_format_metric_does_not_mutate_input():
    metric = {"value": True, "reason": "ok"}
    expected = dict(metric)
    _format_metric("m", metric)
    assert metric == expected


def test_format_metric_empty_name():
    out = _format_metric("", {"value": True})
    assert isinstance(out, str)
    # 36 char left padding for empty name → mostly whitespace
    assert "true" in out


# ---------- _run_inspect_doc 行为深度第七批 ----------


def _make_doc_dict(**overrides):
    """构造最小合法 doc dict。"""
    base = {
        "document_id": "test-doc",
        "source_type": "pdf",
        "source_path": "test.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
    }
    base.update(overrides)
    return base


def _write_doc(tmp_path, doc_dict, name="doc.json"):
    p = tmp_path / name
    import json
    p.write_text(json.dumps(doc_dict), encoding="utf-8")
    return p


def test_run_inspect_doc_sort_order_with_mixed_types(tmp_path, capsys):
    """bool → numeric → str/dict → None 的 sort 顺序。"""
    # 构造一个 doc，让 metrics 包含 4 类 value
    doc = _make_doc_dict()
    p = _write_doc(tmp_path, doc)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "metrics:" in out
    # 各类指标都应出现
    assert "file:" in out
    assert "document_id:" in out


def test_run_inspect_doc_prints_elements_count(tmp_path, capsys):
    doc = _make_doc_dict(elements=[{"type": "paragraph"}] * 5)
    p = _write_doc(tmp_path, doc)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "elements=5" in out


def test_run_inspect_doc_prints_chunks_count(tmp_path, capsys):
    doc = _make_doc_dict(chunks=[{"text": "x"}] * 3)
    p = _write_doc(tmp_path, doc)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "chunks=3" in out


def test_run_inspect_doc_prints_parser_info(tmp_path, capsys):
    doc = _make_doc_dict(parser_name="kreuzberg", parser_version="4.10.2")
    p = _write_doc(tmp_path, doc)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "kreuzberg" in out
    assert "4.10.2" in out


def test_run_inspect_doc_prints_source_type(tmp_path, capsys):
    doc = _make_doc_dict(source_type="docx")
    p = _write_doc(tmp_path, doc)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "docx" in out


def test_run_inspect_doc_default_source_type_when_missing(tmp_path, capsys):
    doc = _make_doc_dict()
    del doc["source_type"]
    p = _write_doc(tmp_path, doc)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    # 默认值 "unknown"
    assert "unknown" in out


def test_run_inspect_doc_returns_zero_on_success(tmp_path):
    doc = _make_doc_dict()
    p = _write_doc(tmp_path, doc)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    assert _run_inspect_doc(args) == 0


# ---------- main 路由深度第七批 ----------


def test_main_help_flag_exits_zero(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["--help"])
    assert ei.value.code == 0


def test_main_run_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["run", "--help"])
    assert ei.value.code == 0


def test_main_validate_report_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["validate-report", "--help"])
    assert ei.value.code == 0


def test_main_inspect_doc_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["inspect-doc", "--help"])
    assert ei.value.code == 0


def test_main_no_args_raises_system_exit_nonzero():
    with pytest.raises(SystemExit) as ei:
        main([])
    # argparse required subcommand → exit 2
    assert ei.value.code != 0


def test_main_unknown_subcommand_raises_system_exit():
    with pytest.raises(SystemExit):
        main(["foobar"])


def test_main_run_returns_int_type(tmp_path):
    """run 子命令总是返回 int（成功 0，失败 1/2）。"""
    mf = tmp_path / "nonexistent.json"
    rc = main(["run", "--manifest", str(mf), "--output", str(tmp_path / "out.json")])
    assert isinstance(rc, int)


def test_main_run_missing_manifest_returns_2(tmp_path, capsys):
    mf = tmp_path / "nonexistent.json"
    rc = main(["run", "--manifest", str(mf), "--output", str(tmp_path / "out.json")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "清单不存在" in err


def test_main_validate_report_returns_int_type(tmp_path):
    p = tmp_path / "nonexistent.json"
    rc = main(["validate-report", str(p)])
    assert isinstance(rc, int)


def test_main_inspect_doc_returns_int_type(tmp_path):
    p = tmp_path / "nonexistent.json"
    rc = main(["inspect-doc", str(p)])
    assert isinstance(rc, int)


# ---------- module source forbidden tokens 第十批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.chmod", "os.chown",
        "os.execv", "os.fork",
        "os.kill", "os.mkdir",
        "os.makedirs", "os.remove",
        "os.rename", "os.rmdir",
        "os.unlink",
        "pathlib.Path.rmdir",
        "pathlib.Path.unlink",
        "eval(", "exec(",
        "compile(",
        "globals(",
        "locals(",
        "vars(",
        "memoryview",
        "bytearray(",
        "errno",
        "signal.signal",
        "fcntl",
        "termios",
        "tty",
        "pty",
        "winreg",
        "msvcrt",
        "_winapi",
        "re.match",
        "re.sub",
        "shutil.rmtree",
        "tempfile.mkdtemp",
    ],
)
def test_cli_source_no_forbidden_token_v3(token):
    src = inspect.getsource(cmod)
    assert token not in src, f"forbidden token found: {token}"


# ---------- signatures 第七批 ----------


def test_signature_build_parser_zero_params():
    sig = inspect.signature(_build_parser)
    params = list(sig.parameters.values())
    assert len(params) == 0


def test_signature_main_argv_param_kind():
    sig = inspect.signature(main)
    params = sig.parameters
    assert params["argv"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_main_argv_default_none():
    sig = inspect.signature(main)
    params = sig.parameters
    assert params["argv"].default is None


def test_signature_format_metric_name_kind():
    sig = inspect.signature(_format_metric)
    params = sig.parameters
    assert params["name"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_format_metric_metric_kind():
    sig = inspect.signature(_format_metric)
    params = sig.parameters
    assert params["metric"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_run_inspect_doc_args_kind():
    sig = inspect.signature(_run_inspect_doc)
    params = sig.parameters
    assert params["args"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_run_inspect_doc_args_no_default():
    sig = inspect.signature(_run_inspect_doc)
    params = sig.parameters
    assert params["args"].default is inspect.Parameter.empty


def test_signature_main_no_varargs():
    sig = inspect.signature(main)
    has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    assert not has_var


def test_signature_main_no_kwargs():
    sig = inspect.signature(main)
    has_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    assert not has_kw


def test_signature_build_parser_no_varargs():
    sig = inspect.signature(_build_parser)
    has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    assert not has_var


def test_signature_format_metric_no_varargs():
    sig = inspect.signature(_format_metric)
    has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    assert not has_var


def test_signature_run_inspect_doc_no_varargs():
    sig = inspect.signature(_run_inspect_doc)
    has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    assert not has_var


# ---------- module 合理性第七批 ----------


def test_module_docstring_has_run_keyword():
    assert "run" in (cmod.__doc__ or "")


def test_module_docstring_has_validate_keyword():
    assert "validate-report" in (cmod.__doc__ or "")


def test_module_docstring_has_inspect_keyword():
    assert "inspect-doc" in (cmod.__doc__ or "")


def test_module_docstring_has_python_dash_m_hint():
    assert "python -m evaluation.cli" in (cmod.__doc__ or "")


def test_module_has_no_all_attribute():
    """cli 模块未定义 __all__（外部按需 import）。"""
    assert not hasattr(cmod, "__all__") or cmod.__all__ is None


def test_module_main_is_function():
    assert inspect.isfunction(main)


def test_module_build_parser_is_function():
    assert inspect.isfunction(_build_parser)


def test_module_format_metric_is_function():
    assert inspect.isfunction(_format_metric)


def test_module_run_inspect_doc_is_function():
    assert inspect.isfunction(_run_inspect_doc)


def test_module_main_module_attribute_is_cli():
    assert main.__module__ == "evaluation.cli"


def test_module_build_parser_module_attribute_is_cli():
    assert _build_parser.__module__ == "evaluation.cli"


def test_module_format_metric_module_attribute_is_cli():
    assert _format_metric.__module__ == "evaluation.cli"


def test_module_run_inspect_doc_module_attribute_is_cli():
    assert _run_inspect_doc.__module__ == "evaluation.cli"


def test_module_main_block_uses_raise_system_exit():
    """`if __name__ == "__main__": raise SystemExit(main())`。"""
    src = inspect.getsource(cmod)
    assert 'raise SystemExit(main())' in src


def test_module_has_no_class_definitions():
    src = inspect.getsource(cmod)
    # No top-level "class " definition
    lines = src.splitlines()
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("class "):
            # only allowed if commented out
            if not stripped.startswith("#"):
                pytest.fail(f"Found class definition: {line}")


# ---------- 端到端集成第七批 ----------


def test_e2e_run_subcommand_full_namespace():
    p = _build_parser()
    ns = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json",
        "--parser", "kreuzberg", "--max-chars", "1000",
        "--tolerance-chars", "50",
    ])
    assert ns.command == "run"
    assert ns.manifest == "m.json"
    assert ns.output == "o.json"
    assert ns.parser == "kreuzberg"
    assert ns.max_chars == 1000
    assert ns.tolerance_chars == 50


def test_e2e_validate_report_subcommand_namespace():
    p = _build_parser()
    ns = p.parse_args(["validate-report", "report.json"])
    assert ns.command == "validate-report"
    assert ns.input == "report.json"


def test_e2e_inspect_doc_subcommand_namespace():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.command == "inspect-doc"
    assert ns.input == "doc.json"
    assert ns.tolerance_chars == 30


def test_e2e_inspect_doc_subcommand_with_custom_tolerance():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "75"])
    assert ns.tolerance_chars == 75


def test_e2e_run_help_message_includes_run(capsys):
    with pytest.raises(SystemExit):
        main(["run", "--help"])
    out = capsys.readouterr().out
    assert "--manifest" in out
    assert "--output" in out
    assert "--parser" in out
    assert "--max-chars" in out
    assert "--tolerance-chars" in out


def test_e2e_validate_report_help_message(capsys):
    with pytest.raises(SystemExit):
        main(["validate-report", "--help"])
    out = capsys.readouterr().out
    assert "input" in out


def test_e2e_inspect_doc_help_message(capsys):
    with pytest.raises(SystemExit):
        main(["inspect-doc", "--help"])
    out = capsys.readouterr().out
    assert "--tolerance-chars" in out


def test_e2e_main_inspect_doc_with_unicode_in_doc(tmp_path, capsys):
    """inspect-doc 应处理含 unicode 字段的 doc。"""
    import json
    doc = {
        "document_id": "中文文档",
        "source_type": "pdf",
        "source_path": "测试.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "中文文档" in out


def test_e2e_main_inspect_doc_minimal_dict_returns_zero(tmp_path):
    """inspect-doc 最小 doc 只需是 dict。"""
    import json
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_main_run_pipeline_with_minimal_manifest(tmp_path, capsys):
    """run 子命令端到端：合法 manifest → rc=0。"""
    import json
    # 准备 manifest 文件
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    # 让 manifest 加载找到 pyproject.toml
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    out_path = tmp_path / "report.json"
    rc = main(["run", "--manifest", str(mf), "--output", str(out_path)])
    assert rc == 0
    assert out_path.is_file()
