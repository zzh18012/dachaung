"""evaluation/cli.py 第六十二轮 edges 测试（Round 557）。

补强 edges60 未触及的角度（第三十四批）。
"""

from __future__ import annotations

import argparse
import inspect
import json
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


# ---------- _build_parser 第三十四批


def test_build_parser_prog_evaluation_cli_batch34():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_present_batch34():
    p = _build_parser()
    assert p.description is not None
    assert "评测" in p.description


def test_build_parser_run_subparser_has_manifest_required_batch34():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    run_p = sub_action.choices["run"]
    manifest_action = run_p._option_string_actions["--manifest"]
    assert manifest_action.required is True


def test_build_parser_run_subparser_has_output_required_batch34():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    run_p = sub_action.choices["run"]
    output_action = run_p._option_string_actions["--output"]
    assert output_action.required is True


def test_build_parser_run_subparser_has_parser_choices_batch34():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    run_p = sub_action.choices["run"]
    parser_action = run_p._option_string_actions["--parser"]
    assert "fallback" in parser_action.choices
    assert "kreuzberg" in parser_action.choices


def test_build_parser_run_subparser_default_parser_batch34():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    run_p = sub_action.choices["run"]
    parser_action = run_p._option_string_actions["--parser"]
    assert parser_action.default == "fallback"


def test_build_parser_run_subparser_default_max_chars_batch34():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    run_p = sub_action.choices["run"]
    mc_action = run_p._option_string_actions["--max-chars"]
    assert mc_action.default == 800


def test_build_parser_run_subparser_default_tolerance_chars_batch34():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    run_p = sub_action.choices["run"]
    tc_action = run_p._option_string_actions["--tolerance-chars"]
    assert tc_action.default == 30


def test_build_parser_validate_report_input_positional_batch34():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    val_p = sub_action.choices["validate-report"]
    pos_actions = [a for a in val_p._actions if not a.option_strings and a.dest == "input"]
    assert len(pos_actions) == 1


def test_build_parser_inspect_doc_has_tolerance_chars_batch34():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    ins_p = sub_action.choices["inspect-doc"]
    assert "--tolerance-chars" in ins_p._option_string_actions


def test_build_parser_inspect_doc_default_tolerance_batch34():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    ins_p = sub_action.choices["inspect-doc"]
    tc_action = ins_p._option_string_actions["--tolerance-chars"]
    assert tc_action.default == 30


def test_build_parser_run_subparser_count_args_batch34():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    run_p = sub_action.choices["run"]
    # 4 个 --option + 1 个 help（默认）
    option_actions = [a for a in run_p._option_string_actions]
    assert "--manifest" in option_actions
    assert "--output" in option_actions
    assert "--parser" in option_actions
    assert "--max-chars" in option_actions
    assert "--tolerance-chars" in option_actions


# ---------- _format_metric 第三十四批


def test_format_metric_value_none_with_reason_batch34():
    out = _format_metric("name", {"value": None, "reason": "missing"})
    assert "null" in out
    assert "missing" in out


def test_format_metric_value_zero_int_batch34():
    out = _format_metric("name", {"value": 0, "reason": None})
    assert "0" in out
    assert "ok" in out


def test_format_metric_value_zero_float_batch34():
    out = _format_metric("name", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_value_one_float_batch34():
    out = _format_metric("name", {"value": 1.0, "reason": None})
    assert "1.0000" in out


def test_format_metric_value_negative_float_batch34():
    out = _format_metric("name", {"value": -0.5, "reason": None})
    assert "-0.5000" in out


def test_format_metric_value_dict_with_multiple_items_batch34():
    out = _format_metric("name", {"value": {"a": 1, "b": 2, "c": 3}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out
    assert "c=3" in out


def test_format_metric_value_dict_sorted_batch34():
    """dict 内 items 按 key 排序。"""
    out = _format_metric("name", {"value": {"zeta": 1, "alpha": 2}, "reason": None})
    # alpha 应在 zeta 之前
    assert out.index("alpha") < out.index("zeta")


def test_format_metric_value_dict_empty_batch34():
    out = _format_metric("name", {"value": {}, "reason": None})
    assert "ok" in out


def test_format_metric_value_true_no_reason_batch34():
    out = _format_metric("name", {"value": True, "reason": None})
    assert "true" in out
    assert "ok" in out


def test_format_metric_value_false_no_reason_batch34():
    out = _format_metric("name", {"value": False, "reason": None})
    assert "false" in out


def test_format_metric_name_alignment_batch34():
    """name 字段宽 36 字符。"""
    out = _format_metric("abc", {"value": 0, "reason": None})
    # name 后面有空白填充到 36
    # 检查 "abc" 之后到 value 之间至少 1 个空格
    assert "  abc" in out
    assert "                                    " in out or "abc                                 " in out


def test_format_metric_value_string_batch34():
    """value 是 str → fallback 到 default case。"""
    out = _format_metric("name", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_value_list_batch34():
    """list 不是 dict/bool/float/int → fallback。"""
    out = _format_metric("name", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in out


# ---------- _run_inspect_doc 第三十四批


def test_run_inspect_doc_input_missing_returns_2_batch34(tmp_path):
    args = MagicMock()
    args.input = str(tmp_path / "missing.json")
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 2


def test_run_inspect_doc_input_directory_returns_2_batch34(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    args = MagicMock()
    args.input = str(d)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 2


def test_run_inspect_doc_invalid_json_returns_1_batch34(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("not json {", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_top_level_list_returns_1_batch34(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_top_level_int_returns_1_batch34(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("42", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_minimal_valid_doc_returns_0_batch34(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_prints_metrics_label_batch34(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_prints_pipeline_success_batch34(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "pipeline_success" in captured.out


def test_run_inspect_doc_prints_file_path_batch34(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "file:" in captured.out
    assert str(p) in captured.out


def test_run_inspect_doc_prints_counts_batch34(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({
            "source_type": "pdf",
            "elements": [{"type": "paragraph", "content": "a", "element_id": "e1"}],
            "chunks": [{"text": "a", "source_element_ids": ["e1"]}],
        }),
        encoding="utf-8",
    )
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "counts:" in captured.out
    assert "elements=1" in captured.out
    assert "chunks=1" in captured.out


def test_run_inspect_doc_prints_parser_info_batch34(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({
            "source_type": "pdf",
            "parser_name": "fallback",
            "parser_version": "1.0",
            "elements": [],
            "chunks": [],
        }),
        encoding="utf-8",
    )
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "parser:" in captured.out
    assert "fallback" in captured.out


# ---------- main 第三十四批


def test_main_inspect_doc_with_missing_returns_2_batch34(tmp_path):
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_inspect_doc_with_directory_returns_2_batch34(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    rc = main(["inspect-doc", str(d)])
    assert rc == 2


def test_main_validate_report_with_missing_returns_2_batch34(tmp_path):
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_run_with_missing_manifest_returns_2_batch34(tmp_path):
    rc = main([
        "run",
        "--manifest", str(tmp_path / "missing.json"),
        "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 2


def test_main_run_with_invalid_manifest_json_returns_1_batch34(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("not json {", encoding="utf-8")
    rc = main([
        "run",
        "--manifest", str(p),
        "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 1


def test_main_unknown_subcommand_raises_systemexit_batch34():
    with pytest.raises(SystemExit):
        main(["unknown-command"])


def test_main_no_args_raises_systemexit_batch34():
    with pytest.raises(SystemExit):
        main([])


def test_main_run_extra_unknown_arg_raises_systemexit_batch34():
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "x", "--output", "y", "--unknown"])


def test_main_inspect_doc_extra_arg_raises_systemexit_batch34():
    with pytest.raises(SystemExit):
        main(["inspect-doc", "a.json", "extra"])


def test_main_validate_report_extra_arg_raises_systemexit_batch34():
    with pytest.raises(SystemExit):
        main(["validate-report", "a.json", "extra"])


def test_main_run_parser_invalid_choice_raises_systemexit_batch34():
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "x", "--output", "y", "--parser", "invalid"])


def test_main_run_max_chars_non_int_raises_systemexit_batch34():
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "x", "--output", "y", "--max-chars", "abc"])


def test_main_run_max_chars_negative_accepted_batch34(tmp_path):
    """argparse 接受负 int，manifest 不存在 → rc=2。"""
    rc = main([
        "run",
        "--manifest", str(tmp_path / "missing.json"),
        "--output", str(tmp_path / "out.json"),
        "--max-chars", "-5",
    ])
    assert rc == 2


def test_main_run_tolerance_chars_negative_accepted_batch34(tmp_path):
    rc = main([
        "run",
        "--manifest", str(tmp_path / "missing.json"),
        "--output", str(tmp_path / "out.json"),
        "--tolerance-chars", "-1",
    ])
    assert rc == 2


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
    "urllib",
    "socket",
    "pty.",
    "ctypes",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch34(token):
    src = inspect.getsource(cmod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch34():
    src = inspect.getsource(cmod)
    assert "评测 CLI" in src


def test_module_source_contains_argparse_import_batch34():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_source_contains_json_import_batch34():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_source_contains_sys_import_batch34():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_source_contains_pathlib_import_batch34():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_manifest_import_batch34():
    src = inspect.getsource(cmod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_module_source_contains_report_import_batch34():
    src = inspect.getsource(cmod)
    assert "from evaluation.report import get_git_provenance" in src


def test_module_source_contains_runner_import_batch34():
    src = inspect.getsource(cmod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_contains_schema_import_batch34():
    src = inspect.getsource(cmod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_module_source_contains_reconfigure_call_batch34():
    src = inspect.getsource(cmod)
    assert "sys.stdout.reconfigure" in src
    assert "sys.stderr.reconfigure" in src


def test_module_source_contains_build_parser_func_batch34():
    src = inspect.getsource(cmod)
    assert "def _build_parser(" in src


def test_module_source_contains_main_func_batch34():
    src = inspect.getsource(cmod)
    assert "def main(" in src


def test_module_source_contains_format_metric_func_batch34():
    src = inspect.getsource(cmod)
    assert "def _format_metric(" in src


def test_module_source_contains_run_inspect_doc_func_batch34():
    src = inspect.getsource(cmod)
    assert "def _run_inspect_doc(" in src


def test_module_source_contains_subparsers_batch34():
    src = inspect.getsource(cmod)
    assert "add_subparsers" in src


def test_module_source_contains_run_subcommand_batch34():
    src = inspect.getsource(cmod)
    assert '"run"' in src
    assert '"validate-report"' in src
    assert '"inspect-doc"' in src


def test_module_source_contains_file_stderr_batch34():
    src = inspect.getsource(cmod)
    assert "file=sys.stderr" in src


def test_module_source_contains_raw_description_batch34():
    src = inspect.getsource(cmod)
    assert "RawDescriptionHelpFormatter" in src


def test_module_source_contains_main_block_batch34():
    src = inspect.getsource(cmod)
    assert 'if __name__ == "__main__"' in src


def test_module_source_contains_system_exit_batch34():
    src = inspect.getsource(cmod)
    assert "raise SystemExit(main())" in src


# ---------- signatures 第四十九批


def test_signature_build_parser_no_params_batch34():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_main_argv_optional_batch34():
    sig = inspect.signature(main)
    assert "argv" in sig.parameters
    assert sig.parameters["argv"].default is None


def test_signature_main_return_int_batch34():
    sig = inspect.signature(main)
    assert sig.return_annotation == "int"


def test_signature_format_metric_params_batch34():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters.keys())
    assert params == ["name", "metric"]


def test_signature_format_metric_return_str_batch34():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation == "str"


def test_signature_run_inspect_doc_args_param_batch34():
    sig = inspect.signature(_run_inspect_doc)
    assert "args" in sig.parameters


def test_signature_run_inspect_doc_return_int_batch34():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


# ---------- module 合理性第四十九批


def test_module_has_future_annotations_batch34():
    src = inspect.getsource(cmod)
    assert "from __future__ import annotations" in src


def test_module_imports_argparse_batch34():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_imports_json_batch34():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_imports_sys_batch34():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_imports_pathlib_batch34():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_has_main_block_batch34():
    src = inspect.getsource(cmod)
    assert 'if __name__ == "__main__"' in src


def test_module_main_block_raises_system_exit_batch34():
    src = inspect.getsource(cmod)
    assert "raise SystemExit(main())" in src


# ---------- 端到端集成第四十九批


def test_e2e_inspect_doc_full_pdf_batch34(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({
            "document_id": "d1",
            "source_path": "/x.pdf",
            "source_type": "pdf",
            "parser_name": "fallback",
            "parser_version": "1.0",
            "elements": [
                {"type": "paragraph", "content": "hello", "element_id": "e1",
                 "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]}},
                {"type": "heading", "content": "title", "element_id": "h1",
                 "source_locator": {"page": 1, "bbox": [0, 0, 100, 30]}},
            ],
            "chunks": [
                {"text": "title", "source_element_ids": ["h1"]},
                {"text": "hello", "source_element_ids": ["e1"]},
            ],
        }),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "pipeline_success" in captured.out
    assert "element_count_total" in captured.out
    assert "pdf_locator_valid_ratio" in captured.out


def test_e2e_inspect_doc_idempotent_batch34(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    rc1 = main(["inspect-doc", str(p)])
    out1 = capsys.readouterr().out
    rc2 = main(["inspect-doc", str(p)])
    out2 = capsys.readouterr().out
    assert rc1 == rc2 == 0
    assert out1 == out2


def test_e2e_validate_report_invalid_returns_1_batch34(tmp_path):
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_validate_report_invalid_json_returns_1_batch34(tmp_path):
    p = tmp_path / "report.json"
    p.write_text("not json {", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_inspect_doc_with_unknown_source_type_batch34(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "weird", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_inspect_doc_full_docx_batch34(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({
            "source_type": "docx",
            "elements": [
                {"type": "paragraph", "content": "x", "element_id": "e1",
                 "source_locator": {"paragraph_index": 0, "section": 1}}
            ],
            "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
        }),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "docx_locator_valid_ratio" in captured.out


def test_e2e_inspect_doc_with_tolerance_chars_batch34(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "100"])
    assert rc == 0
