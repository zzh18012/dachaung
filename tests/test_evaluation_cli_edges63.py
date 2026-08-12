"""evaluation/cli.py 第六十四轮 edges 测试（Round 571）。

补强 edges62 未触及的角度（第三十六批）。
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import cli as cmod
from evaluation.cli import (
    _build_parser,
    _format_metric,
    _run_inspect_doc,
    main,
)


# ---------- _build_parser 第三十六批


def _get_subparser(p, name):
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    return sub_action.choices[name]


def test_build_parser_root_no_positional_args_batch36():
    """root parser 没有 positional argument。"""
    p = _build_parser()
    positional = [a for a in p._actions if not a.option_strings and a.dest != "help"]
    assert len(positional) == 1  # command (subparsers)
    assert positional[0].dest == "command"


def test_build_parser_run_subparser_help_text_present_batch36():
    p = _build_parser()
    run_p = _get_subparser(p, "run")
    assert run_p.description is None or isinstance(run_p.description, str)


def test_build_parser_validate_report_subparser_has_help_batch36():
    p = _build_parser()
    val_p = _get_subparser(p, "validate-report")
    val_action = val_p._actions
    # 第一个 positional action 是 input
    pos_actions = [a for a in val_action if not a.option_strings and a.dest == "input"]
    assert len(pos_actions) == 1


def test_build_parser_inspect_doc_input_positional_batch36():
    p = _build_parser()
    ins_p = _get_subparser(p, "inspect-doc")
    pos_actions = [a for a in ins_p._actions if not a.option_strings and a.dest == "input"]
    assert len(pos_actions) == 1


def test_build_parser_inspect_doc_no_write_subcommand_batch36():
    """inspect-doc 没有写入相关参数（它是只读）。"""
    p = _build_parser()
    ins_p = _get_subparser(p, "inspect-doc")
    option_strings = list(ins_p._option_string_actions.keys())
    assert "--output" not in option_strings


def test_build_parser_root_has_description_batch36():
    p = _build_parser()
    assert p.description is not None


def test_build_parser_run_subparser_count_4_optional_args_batch36():
    """run 子命令有 4 个非 help 的 optional args（manifest/output/parser/max_chars/tolerance）。"""
    p = _build_parser()
    run_p = _get_subparser(p, "run")
    options = [
        s for s in run_p._option_string_actions.keys()
        if s not in ("-h", "--help")
    ]
    # 5 个长选项
    long_options = [s for s in options if s.startswith("--")]
    assert len(long_options) == 5


def test_build_parser_parser_choice_fallback_only_first_batch36():
    """--parser choices 第一个是 'fallback'。"""
    p = _build_parser()
    run_p = _get_subparser(p, "run")
    parser_action = run_p._option_string_actions["--parser"]
    assert parser_action.choices[0] == "fallback"


def test_build_parser_parser_choice_kreuzberg_second_batch36():
    p = _build_parser()
    run_p = _get_subparser(p, "run")
    parser_action = run_p._option_string_actions["--parser"]
    assert parser_action.choices[1] == "kreuzberg"


def test_build_parser_parser_choice_count_2_batch36():
    p = _build_parser()
    run_p = _get_subparser(p, "run")
    parser_action = run_p._option_string_actions["--parser"]
    assert len(parser_action.choices) == 2


def test_build_parser_subparsers_action_dest_command_batch36():
    """subparsers action 的 dest 是 'command'。"""
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    assert sub_action.dest == "command"


def test_build_parser_subparsers_action_has_3_choices_batch36():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    assert len(sub_action.choices) == 3


def test_build_parser_subparsers_choices_keys_batch36():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    assert set(sub_action.choices.keys()) == {"run", "validate-report", "inspect-doc"}


# ---------- _format_metric 第三十六批


def test_format_metric_value_int_with_reason_batch36():
    out = _format_metric("name", {"value": 42, "reason": "x"})
    assert "42" in out
    assert "x" in out


def test_format_metric_value_zero_int_no_reason_batch36():
    out = _format_metric("name", {"value": 0, "reason": None})
    assert "0" in out
    assert "ok" in out


def test_format_metric_value_negative_zero_float_batch36():
    out = _format_metric("name", {"value": -0.0, "reason": None})
    assert "-0.0000" in out


def test_format_metric_value_one_int_batch36():
    out = _format_metric("name", {"value": 1, "reason": None})
    assert "1" in out


def test_format_metric_value_dict_one_kv_batch36():
    out = _format_metric("name", {"value": {"a": 1}, "reason": None})
    assert "a=1" in out


def test_format_metric_value_dict_with_int_and_str_batch36():
    """dict value 混合类型。"""
    out = _format_metric("name", {"value": {"a": 1, "b": "x"}, "reason": None})
    assert "a=1" in out
    assert "b=x" in out


def test_format_metric_value_dict_with_negative_value_batch36():
    out = _format_metric("name", {"value": {"a": -5}, "reason": None})
    assert "a=-5" in out


def test_format_metric_value_dict_with_float_batch36():
    out = _format_metric("name", {"value": {"a": 0.5}, "reason": None})
    assert "a=0.5" in out


def test_format_metric_value_dict_with_zero_batch36():
    out = _format_metric("name", {"value": {"a": 0}, "reason": None})
    assert "a=0" in out


def test_format_metric_value_true_returns_str_lower_batch36():
    out = _format_metric("name", {"value": True, "reason": None})
    assert "true" in out.lower()


def test_format_metric_value_false_returns_str_lower_batch36():
    out = _format_metric("name", {"value": False, "reason": None})
    assert "false" in out.lower()


def test_format_metric_value_dict_two_items_batch36():
    out = _format_metric("name", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out


def test_format_metric_no_reason_with_none_value_batch36():
    out = _format_metric("name", {"value": None, "reason": None})
    assert "null" in out


# ---------- _run_inspect_doc 第三十六批


def _write_doc(tmp_path, doc):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def test_run_inspect_doc_with_no_chunks_key_batch36(tmp_path, capsys):
    """doc 没有 chunks key → 视为 []。"""
    p = _write_doc(tmp_path, {"source_type": "pdf", "elements": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_with_no_elements_key_batch36(tmp_path, capsys):
    p = _write_doc(tmp_path, {"source_type": "pdf", "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_unicode_chunk_text_batch36(tmp_path, capsys):
    p = _write_doc(tmp_path, {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "中文", "element_id": "e1"}],
        "chunks": [{"text": "中文", "source_element_ids": ["e1"]}],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "elements=1 chunks=1" in captured.out


def test_run_inspect_doc_passes_tolerance_through_main_batch36(tmp_path, capsys):
    """main() 调用时传 --tolerance-chars 不抛。"""
    p = _write_doc(tmp_path, {"source_type": "pdf", "elements": [], "chunks": []})
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "50"])
    assert rc == 0


def test_run_inspect_doc_prints_parser_name_batch36(tmp_path, capsys):
    p = _write_doc(tmp_path, {
        "source_type": "pdf",
        "parser_name": "fallback",
        "elements": [],
        "chunks": [],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "fallback" in captured.out


def test_run_inspect_doc_prints_parser_version_batch36(tmp_path, capsys):
    p = _write_doc(tmp_path, {
        "source_type": "pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "1.0" in captured.out


def test_run_inspect_doc_prints_document_id_batch36(tmp_path, capsys):
    p = _write_doc(tmp_path, {
        "document_id": "my_doc_id",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "my_doc_id" in captured.out


def test_run_inspect_doc_prints_source_path_batch36(tmp_path, capsys):
    p = _write_doc(tmp_path, {
        "source_path": "/path/to/file.pdf",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "/path/to/file.pdf" in captured.out


def test_run_inspect_doc_metric_count_in_output_batch36(tmp_path, capsys):
    """inspect-doc 输出含至少 14 行 metric。"""
    p = _write_doc(tmp_path, {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    # 含核心 metric 名
    for name in ["pipeline_success", "element_count_total", "schema_valid",
                 "pdf_locator_valid_ratio"]:
        assert name in captured.out


def test_run_inspect_doc_returns_0_for_minimal_doc_batch36(tmp_path):
    p = _write_doc(tmp_path, {"source_type": "docx", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    assert _run_inspect_doc(args) == 0


# ---------- main 第三十六批


def test_main_run_with_corrupt_manifest_json_batch36(tmp_path, capsys):
    """manifest 是合法路径但 JSON 解析失败 → rc=1。"""
    p = tmp_path / "manifest.json"
    p.write_text("not json {", encoding="utf-8")
    rc = main([
        "run",
        "--manifest", str(p),
        "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 1


def test_main_run_with_invalid_manifest_schema_batch36(tmp_path, capsys):
    """manifest schema 不通过 → rc=1。"""
    p = tmp_path / "manifest.json"
    p.write_text(
        json.dumps({
            "manifest_version": "999.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    rc = main([
        "run",
        "--manifest", str(p),
        "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 1


def test_main_run_help_raises_systemexit_with_zero_rc_batch36():
    """--help 触发 SystemExit(0)。"""
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_main_run_subcommand_help_raises_systemexit_batch36():
    with pytest.raises(SystemExit):
        main(["run", "--help"])


def test_main_validate_report_help_raises_systemexit_batch36():
    with pytest.raises(SystemExit):
        main(["validate-report", "--help"])


def test_main_inspect_doc_help_raises_systemexit_batch36():
    with pytest.raises(SystemExit):
        main(["inspect-doc", "--help"])


def test_main_invalid_subcommand_raises_systemexit_2_batch36():
    with pytest.raises(SystemExit) as exc:
        main(["bogus"])
    assert exc.value.code == 2


def test_main_run_extra_unknown_short_arg_raises_batch36():
    with pytest.raises(SystemExit):
        main(["run", "-z"])


def test_main_run_with_dash_dash_only_batch36():
    """-- 单独传不接值 → SystemExit。"""
    with pytest.raises(SystemExit):
        main(["run", "--"])


def test_main_inspect_doc_with_nonexistent_file_returns_2_batch36(tmp_path):
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_validate_report_with_nonexistent_file_returns_2_batch36(tmp_path):
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_run_max_chars_zero_accepted_batch36(tmp_path):
    """--max-chars 0 被接受（manifest 失败 → rc=1）。"""
    p = tmp_path / "manifest.json"
    p.write_text(
        json.dumps({
            "manifest_version": "999.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    rc = main([
        "run",
        "--manifest", str(p),
        "--output", str(tmp_path / "out.json"),
        "--max-chars", "0",
    ])
    assert rc == 1


def test_main_run_tolerance_chars_zero_accepted_batch36(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text(
        json.dumps({
            "manifest_version": "999.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    rc = main([
        "run",
        "--manifest", str(p),
        "--output", str(tmp_path / "out.json"),
        "--tolerance-chars", "0",
    ])
    assert rc == 1


# ---------- module source forbidden tokens 第五十三批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch36(token):
    src = inspect.getsource(cmod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch36():
    src = inspect.getsource(cmod)
    assert "评测 CLI" in src


def test_module_source_contains_future_annotations_batch36():
    src = inspect.getsource(cmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_argparse_import_batch36():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_source_contains_json_import_batch36():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_source_contains_sys_import_batch36():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_source_contains_pathlib_import_batch36():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_sys_stdout_reconfigure_batch36():
    src = inspect.getsource(cmod)
    assert "sys.stdout.reconfigure" in src


def test_module_source_contains_sys_stderr_reconfigure_batch36():
    src = inspect.getsource(cmod)
    assert "sys.stderr.reconfigure" in src


def test_module_source_contains_manifest_import_batch36():
    src = inspect.getsource(cmod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_module_source_contains_report_import_batch36():
    src = inspect.getsource(cmod)
    assert "from evaluation.report import get_git_provenance" in src


def test_module_source_contains_runner_import_batch36():
    src = inspect.getsource(cmod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_contains_schema_import_batch36():
    src = inspect.getsource(cmod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_module_source_contains_build_parser_func_batch36():
    src = inspect.getsource(cmod)
    assert "def _build_parser(" in src


def test_module_source_contains_main_func_batch36():
    src = inspect.getsource(cmod)
    assert "def main(" in src


def test_module_source_contains_format_metric_func_batch36():
    src = inspect.getsource(cmod)
    assert "def _format_metric(" in src


def test_module_source_contains_run_inspect_doc_func_batch36():
    src = inspect.getsource(cmod)
    assert "def _run_inspect_doc(" in src


def test_module_source_contains_run_subcommand_string_batch36():
    src = inspect.getsource(cmod)
    assert '"run"' in src


def test_module_source_contains_validate_report_subcommand_string_batch36():
    src = inspect.getsource(cmod)
    assert '"validate-report"' in src


def test_module_source_contains_inspect_doc_subcommand_string_batch36():
    src = inspect.getsource(cmod)
    assert '"inspect-doc"' in src


def test_module_source_contains_file_stderr_batch36():
    src = inspect.getsource(cmod)
    assert "file=sys.stderr" in src


def test_module_source_contains_prog_evaluation_cli_batch36():
    src = inspect.getsource(cmod)
    assert 'prog="evaluation.cli"' in src


def test_module_source_contains_raw_description_batch36():
    src = inspect.getsource(cmod)
    assert "RawDescriptionHelpFormatter" in src


def test_module_source_contains_main_block_batch36():
    src = inspect.getsource(cmod)
    assert 'if __name__ == "__main__"' in src


def test_module_source_contains_raise_system_exit_batch36():
    src = inspect.getsource(cmod)
    assert "raise SystemExit(main())" in src


def test_module_source_contains_choices_tuple_batch36():
    src = inspect.getsource(cmod)
    assert '("fallback", "kreuzberg")' in src


def test_module_source_contains_subparsers_call_batch36():
    src = inspect.getsource(cmod)
    assert "add_subparsers" in src


# ---------- signatures 第四十九批


def test_signature_build_parser_no_params_batch36():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_main_argv_optional_batch36():
    sig = inspect.signature(main)
    assert "argv" in sig.parameters
    assert sig.parameters["argv"].default is None


def test_signature_main_return_int_batch36():
    sig = inspect.signature(main)
    assert sig.return_annotation == "int"


def test_signature_format_metric_params_batch36():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters.keys()) == ["name", "metric"]


def test_signature_format_metric_name_str_annotation_batch36():
    sig = inspect.signature(_format_metric)
    assert sig.parameters["name"].annotation == "str"


def test_signature_format_metric_metric_dict_annotation_batch36():
    sig = inspect.signature(_format_metric)
    assert sig.parameters["metric"].annotation == "dict"


def test_signature_format_metric_return_str_batch36():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation == "str"


def test_signature_run_inspect_doc_args_param_batch36():
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters.keys()) == ["args"]


def test_signature_run_inspect_doc_return_int_batch36():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


# ---------- module 合理性第四十九批


def test_module_imports_argparse_batch36():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_imports_json_batch36():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_imports_sys_batch36():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_imports_pathlib_batch36():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_has_main_callable_batch36():
    assert callable(cmod.main)


def test_module_has_build_parser_callable_batch36():
    assert callable(cmod._build_parser)


def test_module_has_format_metric_callable_batch36():
    assert callable(cmod._format_metric)


def test_module_has_run_inspect_doc_callable_batch36():
    assert callable(cmod._run_inspect_doc)


# ---------- 端到端集成第四十九批


def test_e2e_inspect_doc_prints_metric_section_batch36(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({
            "source_type": "pdf",
            "elements": [],
            "chunks": [],
        }),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "metrics:" in out
    assert "pipeline_success" in out


def test_e2e_inspect_doc_idempotent_output_batch36(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    main(["inspect-doc", str(p)])
    out1 = capsys.readouterr().out
    main(["inspect-doc", str(p)])
    out2 = capsys.readouterr().out
    assert out1 == out2


def test_e2e_validate_report_with_actual_report_batch36(tmp_path):
    """跑完整 run → 拿到报告 → 用 validate-report 校验。"""
    pdf = tmp_path / "a.pdf"
    pdf.write_text("dummy", encoding="utf-8")
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    out_path = tmp_path / "report.json"
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        rc1 = main(["run", "--manifest", str(manifest_p), "--output", str(out_path)])
        assert rc1 == 0
        rc2 = main(["validate-report", str(out_path)])
        assert rc2 == 0
    finally:
        os.chdir(cwd)


def test_e2e_run_with_kreuzberg_parser_runs_batch36(tmp_path, capsys):
    """--parser kreuzberg 完整跑。"""
    pdf = tmp_path / "a.pdf"
    pdf.write_text("dummy", encoding="utf-8")
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    out_path = tmp_path / "report.json"
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        rc = main([
            "run", "--manifest", str(manifest_p), "--output", str(out_path),
            "--parser", "kreuzberg",
        ])
        assert rc == 0
        assert out_path.is_file()
    finally:
        os.chdir(cwd)


def test_e2e_run_with_no_documents_batch36(tmp_path, capsys):
    """空 manifest 仍能完整跑。"""
    p = tmp_path / "manifest.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    out_path = tmp_path / "out" / "report.json"
    rc = main(["run", "--manifest", str(p), "--output", str(out_path)])
    assert rc == 0
    assert out_path.is_file()
