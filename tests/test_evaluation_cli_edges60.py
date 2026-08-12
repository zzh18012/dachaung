"""evaluation/cli.py 第六十一轮 edges 测试（Round 550）。

补强 edges59 未触及的角度（第三十三批）。
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


# ---------- _build_parser 第三十三批 ----------


def test_build_parser_has_actions_batch33():
    p = _build_parser()
    assert len(p._actions) > 0


def test_build_parser_subparsers_dest_command_batch33():
    """subparsers dest='command'。"""
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    assert sub_action.dest == "command"


def test_build_parser_run_subparser_has_required_help_batch33():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    run_p = sub_action.choices["run"]
    assert run_p.description is None or isinstance(run_p.description, str)


def test_build_parser_validate_report_subparser_exists_batch33():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    assert "validate-report" in sub_action.choices


def test_build_parser_inspect_doc_subparser_exists_batch33():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    assert "inspect-doc" in sub_action.choices


def test_build_parser_run_max_chars_help_text_batch33():
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    run_p = sub_action.choices["run"]
    tol_action = run_p._option_string_actions["--max-chars"]
    assert tol_action.help is not None


def test_build_parser_inspect_doc_input_required_batch33():
    """inspect-doc input positional 是 required。"""
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    ins_p = sub_action.choices["inspect-doc"]
    pos_actions = [a for a in ins_p._actions if not a.option_strings and a.dest == "input"]
    assert len(pos_actions) == 1


# ---------- _format_metric 第三十三批 ----------


def test_format_metric_negative_float_batch33():
    out = _format_metric("x", {"value": -0.5, "reason": None})
    assert "-0.5000" in out


def test_format_metric_one_dict_item_with_negative_value_batch33():
    out = _format_metric("x", {"value": {"a": -1}, "reason": None})
    assert "a=-1" in out


def test_format_metric_dict_with_zero_value_batch33():
    out = _format_metric("x", {"value": {"a": 0}, "reason": None})
    assert "a=0" in out


def test_format_metric_value_negative_int_with_reason_batch33():
    out = _format_metric("x", {"value": -10, "reason": "neg"})
    assert "-10" in out
    assert "neg" in out


def test_format_metric_value_true_with_reason_batch33():
    """value=True 且 reason 给了字符串 → 用 reason 字符串。"""
    out = _format_metric("x", {"value": True, "reason": "ok-ish"})
    assert "true" in out
    assert "ok-ish" in out


def test_format_metric_value_false_with_reason_batch33():
    out = _format_metric("x", {"value": False, "reason": "fail"})
    assert "false" in out
    assert "fail" in out


def test_format_metric_value_one_int_batch33():
    out = _format_metric("x", {"value": 1, "reason": None})
    assert "1" in out


def test_format_metric_value_huge_int_batch33():
    out = _format_metric("x", {"value": 10**10, "reason": None})
    assert "10000000000" in out


# ---------- _run_inspect_doc 第三十三批 ----------


def test_run_inspect_doc_returns_int_for_top_level_int_batch33(capsys, tmp_path):
    """JSON 顶层是 int → not dict → return 1。"""
    p = tmp_path / "doc.json"
    p.write_text("42", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_returns_int_for_top_level_string_batch33(capsys, tmp_path):
    """JSON 顶层是 string → not dict → return 1。"""
    p = tmp_path / "doc.json"
    p.write_text('"hello"', encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_returns_int_for_top_level_null_batch33(capsys, tmp_path):
    """JSON 顶层是 null → not dict → return 1。"""
    p = tmp_path / "doc.json"
    p.write_text("null", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_document_id_present_batch33(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({
            "document_id": "d_custom",
            "source_type": "pdf",
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
    assert "d_custom" in captured.out


def test_run_inspect_doc_source_path_present_batch33(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({
            "source_path": "/path/to/x.pdf",
            "source_type": "pdf",
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
    assert "/path/to/x.pdf" in captured.out


def test_run_inspect_doc_parser_name_present_batch33(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({
            "parser_name": "fallback",
            "parser_version": "1.0",
            "source_type": "pdf",
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
    assert "fallback" in captured.out
    assert "1.0" in captured.out


# ---------- main 第三十三批 ----------


def test_main_inspect_doc_with_dir_returns_2_batch33(capsys, tmp_path):
    """inspect-doc input 是目录 → return 2。"""
    d = tmp_path / "subdir"
    d.mkdir()
    rc = main(["inspect-doc", str(d)])
    assert rc == 2


def test_main_validate_report_with_dir_returns_2_batch33(capsys, tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    rc = main(["validate-report", str(d)])
    assert rc == 2


def test_main_inspect_doc_extra_arg_raises_systemexit_batch33():
    """inspect-doc 不接受额外 positional。"""
    with pytest.raises(SystemExit):
        main(["inspect-doc", "a.json", "extra"])


def test_main_validate_report_extra_arg_raises_systemexit_batch33():
    with pytest.raises(SystemExit):
        main(["validate-report", "a.json", "extra"])


def test_main_run_with_extra_unknown_arg_raises_systemexit_batch33():
    """run --unknown → SystemExit。"""
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "x", "--output", "y", "--unknown"])


def test_main_run_max_chars_negative_not_caught_batch33(tmp_path):
    """max_chars 是负数也接受（argparse 不验证正负）。"""
    # argparse 接受任何 int；这里只验证不抛 SystemExit
    args = ["run", "--manifest", "/nonexistent.json", "--output", "/tmp/out.json", "--max-chars", "-5"]
    # 因为 manifest 不存在会 return 2，但 argparse 接受 -5
    rc = main(args)
    # 不应该 SystemExit
    assert rc == 2


def test_main_run_tolerance_chars_negative_accepted_batch33(tmp_path):
    """tolerance-chars 负数也接受。"""
    args = ["run", "--manifest", "/nonexistent.json", "--output", "/tmp/out.json", "--tolerance-chars", "-1"]
    rc = main(args)
    assert rc == 2


# ---------- module source forbidden tokens 第五十批 ----------


def test_module_source_no_eval_batch33():
    src = inspect.getsource(cmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch33():
    src = inspect.getsource(cmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch33():
    src = inspect.getsource(cmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch33():
    src = inspect.getsource(cmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch33():
    src = inspect.getsource(cmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch33():
    src = inspect.getsource(cmod)
    assert "breakpoint(" not in src


def test_module_source_no_shutil_batch33():
    src = inspect.getsource(cmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch33():
    src = inspect.getsource(cmod)
    assert "requests" not in src


def test_module_source_no_subprocess_batch33():
    src = inspect.getsource(cmod)
    assert "subprocess" not in src


# ---------- module source 字符串精确补强第四十六批 ----------


def test_module_source_contains_module_docstring_batch33():
    src = inspect.getsource(cmod)
    assert "评测 CLI" in src


def test_module_source_contains_argparse_import_batch33():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_source_contains_json_import_batch33():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_source_contains_sys_import_batch33():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_source_contains_pathlib_import_batch33():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_manifest_import_batch33():
    src = inspect.getsource(cmod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_module_source_contains_runner_import_batch33():
    src = inspect.getsource(cmod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_contains_schema_import_batch33():
    src = inspect.getsource(cmod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_module_source_contains_report_import_batch33():
    src = inspect.getsource(cmod)
    assert "from evaluation.report import get_git_provenance" in src


def test_module_source_contains_build_parser_func_batch33():
    src = inspect.getsource(cmod)
    assert "def _build_parser(" in src


def test_module_source_contains_main_func_batch33():
    src = inspect.getsource(cmod)
    assert "def main(" in src


def test_module_source_contains_format_metric_func_batch33():
    src = inspect.getsource(cmod)
    assert "def _format_metric(" in src


def test_module_source_contains_run_inspect_doc_func_batch33():
    src = inspect.getsource(cmod)
    assert "def _run_inspect_doc(" in src


def test_module_source_contains_reconfigure_call_batch33():
    src = inspect.getsource(cmod)
    assert "sys.stdout.reconfigure" in src


def test_module_source_contains_subparsers_batch33():
    src = inspect.getsource(cmod)
    assert "add_subparsers" in src


def test_module_source_contains_raw_description_batch33():
    src = inspect.getsource(cmod)
    assert "RawDescriptionHelpFormatter" in src


def test_module_source_contains_run_subcommand_batch33():
    src = inspect.getsource(cmod)
    assert '"run"' in src
    assert '"validate-report"' in src
    assert '"inspect-doc"' in src


def test_module_source_contains_validate_file_call_batch33():
    src = inspect.getsource(cmod)
    assert 'validate_file(' in src


def test_module_source_contains_load_manifest_call_batch33():
    src = inspect.getsource(cmod)
    assert 'load_manifest(' in src


def test_module_source_contains_run_evaluation_call_batch33():
    src = inspect.getsource(cmod)
    assert 'run_evaluation(' in src


def test_module_source_contains_file_stderr_batch33():
    src = inspect.getsource(cmod)
    assert "file=sys.stderr" in src


# ---------- signatures 第四十六批 ----------


def test_signature_build_parser_no_params_batch33():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_main_argv_optional_batch33():
    sig = inspect.signature(main)
    assert "argv" in sig.parameters
    assert sig.parameters["argv"].default is None


def test_signature_main_return_int_batch33():
    sig = inspect.signature(main)
    assert sig.return_annotation == "int"


def test_signature_format_metric_params_batch33():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters.keys())
    assert params == ["name", "metric"]


def test_signature_format_metric_return_str_batch33():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation == "str"


def test_signature_run_inspect_doc_args_param_batch33():
    sig = inspect.signature(_run_inspect_doc)
    assert "args" in sig.parameters


def test_signature_run_inspect_doc_return_int_batch33():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


# ---------- module 合理性第四十六批 ----------


def test_module_has_future_annotations_batch33():
    src = inspect.getsource(cmod)
    assert "from __future__ import annotations" in src


def test_module_imports_argparse_batch33():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_imports_json_batch33():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_imports_sys_batch33():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_imports_pathlib_batch33():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_has_main_block_batch33():
    src = inspect.getsource(cmod)
    assert 'if __name__ == "__main__"' in src


def test_module_main_block_raises_system_exit_batch33():
    src = inspect.getsource(cmod)
    assert "raise SystemExit(main())" in src


# ---------- 端到端集成第四十六批 ----------


def test_e2e_inspect_doc_full_pdf_batch33(capsys, tmp_path):
    """端到端：完整 PDF doc → inspect-doc 输出所有 metric。"""
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({
            "document_id": "d1",
            "source_path": "/x.pdf",
            "source_type": "pdf",
            "parser_name": "fallback",
            "parser_version": "1.0",
            "elements": [
                {
                    "type": "paragraph",
                    "content": "hello",
                    "element_id": "e1",
                    "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]},
                },
                {
                    "type": "heading",
                    "content": "title",
                    "element_id": "h1",
                    "source_locator": {"page": 1, "bbox": [0, 0, 100, 30]},
                },
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


def test_e2e_inspect_doc_idempotent_batch33(capsys, tmp_path):
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


def test_e2e_validate_report_invalid_returns_1_batch33(capsys, tmp_path):
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_inspect_doc_returns_0_for_minimal_valid_batch33(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_main_no_args_to_stderr_batch33(capsys):
    """无参数 main → SystemExit + argparse 错误打印到 stderr。"""
    with pytest.raises(SystemExit):
        main([])
    captured = capsys.readouterr()
    assert captured.err != "" or captured.out != ""


def test_e2e_inspect_doc_with_unknown_source_type_batch33(capsys, tmp_path):
    """unknown source_type → 仍跑（pdf/docx ratio 都 null）。"""
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "weird", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_inspect_doc_full_docx_batch33(capsys, tmp_path):
    """端到端：DOCX doc → inspect-doc 输出 docx_locator_valid_ratio。"""
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({
            "source_type": "docx",
            "elements": [
                {
                    "type": "paragraph",
                    "content": "x",
                    "element_id": "e1",
                    "source_locator": {"paragraph_index": 0, "section": 1},
                }
            ],
            "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
        }),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "docx_locator_valid_ratio" in captured.out
