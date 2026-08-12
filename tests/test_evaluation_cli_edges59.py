"""evaluation/cli.py 第六十轮 edges 测试（Round 543）。

补强 edges58 未触及的角度（第三十二批）。
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


# ---------- _build_parser 第三十二批 ----------


def test_build_parser_prog_name_batch32():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_set_batch32():
    p = _build_parser()
    assert "评测" in p.description


def test_build_parser_formatter_raw_description_batch32():
    import argparse
    p = _build_parser()
    assert p.formatter_class == argparse.RawDescriptionHelpFormatter


def test_build_parser_subcommands_full_list_batch32():
    """sub 含 run / validate-report / inspect-doc 三个。"""
    p = _build_parser()
    # 找到 subparsers action
    sub_action = None
    for action in p._actions:
        if isinstance(action, argparse._SubParsersAction):
            sub_action = action
            break
    assert sub_action is not None
    assert set(sub_action.choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_run_manifest_required_batch32():
    import argparse
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    run_p = sub_action.choices["run"]
    manifest_action = run_p._option_string_actions["--manifest"]
    assert manifest_action.required is True


def test_build_parser_run_output_required_batch32():
    import argparse
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    run_p = sub_action.choices["run"]
    output_action = run_p._option_string_actions["--output"]
    assert output_action.required is True


def test_build_parser_run_parser_choices_full_batch32():
    import argparse
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    run_p = sub_action.choices["run"]
    parser_action = run_p._option_string_actions["--parser"]
    assert set(parser_action.choices) == {"fallback", "kreuzberg"}


def test_build_parser_run_tolerance_chars_type_int_batch32():
    import argparse
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    run_p = sub_action.choices["run"]
    tol_action = run_p._option_string_actions["--tolerance-chars"]
    assert tol_action.type is int


def test_build_parser_inspect_doc_input_positional_batch32():
    """inspect-doc 的 input 是 positional。"""
    import argparse
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    ins_p = sub_action.choices["inspect-doc"]
    # positional action 不在 _option_string_actions
    pos_actions = [a for a in ins_p._actions if not a.option_strings]
    assert any(a.dest == "input" for a in pos_actions)


def test_build_parser_validate_report_input_positional_batch32():
    import argparse
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    val_p = sub_action.choices["validate-report"]
    pos_actions = [a for a in val_p._actions if not a.option_strings]
    assert any(a.dest == "input" for a in pos_actions)


def test_build_parser_inspect_doc_tolerance_chars_type_int_batch32():
    import argparse
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    ins_p = sub_action.choices["inspect-doc"]
    tol_action = ins_p._option_string_actions["--tolerance-chars"]
    assert tol_action.type is int


# ---------- _format_metric 第三十二批 ----------


def test_format_metric_value_none_no_reason_batch32():
    out = _format_metric("x", {"value": None, "reason": None})
    assert "null" in out
    assert "None" in out


def test_format_metric_value_none_with_reason_batch32():
    out = _format_metric("x", {"value": None, "reason": "why"})
    assert "null" in out
    assert "why" in out


def test_format_metric_value_true_lower_batch32():
    out = _format_metric("x", {"value": True, "reason": None})
    assert "true" in out
    assert "True" not in out


def test_format_metric_value_false_lower_batch32():
    out = _format_metric("x", {"value": False, "reason": None})
    assert "false" in out
    assert "False" not in out


def test_format_metric_value_int_batch32():
    out = _format_metric("x", {"value": 42, "reason": None})
    assert "42" in out
    assert "ok" in out


def test_format_metric_value_zero_int_batch32():
    out = _format_metric("x", {"value": 0, "reason": None})
    assert "0" in out


def test_format_metric_value_float_precision_batch32():
    """float 保留 4 位小数。"""
    out = _format_metric("x", {"value": 0.123456789, "reason": None})
    assert "0.1235" in out


def test_format_metric_value_dict_empty_batch32():
    out = _format_metric("x", {"value": {}, "reason": None})
    # 空 dict → items 是空字符串
    assert "x" in out
    assert "ok" in out


def test_format_metric_value_dict_single_item_batch32():
    out = _format_metric("x", {"value": {"a": 1}, "reason": None})
    assert "a=1" in out


def test_format_metric_value_dict_three_items_batch32():
    out = _format_metric("x", {"value": {"a": 1, "b": 2, "c": 3}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out
    assert "c=3" in out


def test_format_metric_value_negative_int_batch32():
    out = _format_metric("x", {"value": -5, "reason": None})
    assert "-5" in out


def test_format_metric_value_long_name_batch32():
    """长 name 仍 padding 到 36 字符。"""
    out = _format_metric("a" * 50, {"value": 0, "reason": None})
    assert "a" * 50 in out


def test_format_metric_value_string_batch32():
    """value 是 str → 走 fallback (return f"... {value}")。"""
    out = _format_metric("x", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_value_list_batch32():
    """value 是 list → 走 fallback。"""
    out = _format_metric("x", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in out


def test_format_metric_value_one_float_batch32():
    out = _format_metric("x", {"value": 1.0, "reason": None})
    assert "1.0000" in out


def test_format_metric_value_with_reason_when_not_none_batch32():
    """value 非 None 但 reason 给了 → 用给定 reason（reason or 'ok'）。"""
    out = _format_metric("x", {"value": 0.5, "reason": "weird_reason"})
    assert "weird_reason" in out


# ---------- _run_inspect_doc 第三十二批 ----------


def test_run_inspect_doc_path_is_directory_returns_2_batch32(capsys, tmp_path):
    """input 是目录 → 文件不存在 → return 2。"""
    d = tmp_path / "subdir"
    d.mkdir()
    args = MagicMock()
    args.input = str(d)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 2


def test_run_inspect_doc_empty_file_returns_1_batch32(capsys, tmp_path):
    """空文件 → JSON 解析失败 → return 1。"""
    p = tmp_path / "doc.json"
    p.write_text("", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_invalid_json_returns_1_batch32(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{not json}", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_full_document_batch32(capsys, tmp_path):
    """完整 doc → 返回 0 + 打印 metrics。"""
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
                }
            ],
            "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
        }),
        encoding="utf-8",
    )
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "metrics:" in captured.out
    assert "pipeline_success" in captured.out


def test_run_inspect_doc_no_chunks_batch32(capsys, tmp_path):
    """无 chunks → 仍返回 0。"""
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


def test_run_inspect_doc_no_elements_batch32(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "elements=0" in captured.out


def test_run_inspect_doc_metric_order_none_last_batch32(capsys, tmp_path):
    """metric 排序：bool/int/float 在前，None 在后。"""
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
    # None metric 应该排在最后
    none_idx = captured.out.find("null")
    true_idx = captured.out.find("true")
    if none_idx >= 0 and true_idx >= 0:
        assert none_idx > true_idx


def test_run_inspect_doc_with_tolerance_chars_batch32(capsys, tmp_path):
    """tolerance_chars 参数被传递。"""
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 99
    rc = _run_inspect_doc(args)
    assert rc == 0


# ---------- main 第三十二批 ----------


def test_main_no_args_raises_systemexit_batch32():
    """无子命令 → SystemExit（required=True）。"""
    with pytest.raises(SystemExit):
        main([])


def test_main_run_invalid_parser_choice_raises_systemexit_batch32():
    """run --parser invalid → SystemExit。"""
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "x", "--output", "y", "--parser", "invalid"])


def test_main_run_missing_manifest_arg_raises_systemexit_batch32():
    with pytest.raises(SystemExit):
        main(["run", "--output", "y"])


def test_main_run_missing_output_arg_raises_systemexit_batch32():
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "x"])


def test_main_validate_report_nonexistent_returns_2_batch32(capsys):
    rc = main(["validate-report", "/nonexistent_xyz.json"])
    assert rc == 2


def test_main_inspect_doc_nonexistent_returns_2_batch32(capsys):
    rc = main(["inspect-doc", "/nonexistent_xyz.json"])
    assert rc == 2


def test_main_unknown_subcommand_raises_systemexit_batch32():
    with pytest.raises(SystemExit):
        main(["unknown"])


def test_main_returns_int_for_validate_report_valid_batch32(capsys, tmp_path):
    """合法 validate-report 文件 → return 0 或 1（不抛）。"""
    p = tmp_path / "report.json"
    # 不合法 schema → return 1
    p.write_text("{}", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc in (0, 1, 2)


def test_main_validate_report_with_invalid_json_returns_1_batch32(capsys, tmp_path):
    p = tmp_path / "report.json"
    p.write_text("{not json}", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_with_dict_input_batch32(capsys, tmp_path):
    """合法 doc → return 0。"""
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_with_top_level_list_returns_1_batch32(capsys, tmp_path):
    """JSON 顶层是 list → return 1。"""
    p = tmp_path / "doc.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_validate_report_path_is_directory_returns_2_batch32(capsys, tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    rc = main(["validate-report", str(d)])
    assert rc == 2


# ---------- module source forbidden tokens 第四十九批 ----------


def test_module_source_no_eval_batch32():
    src = inspect.getsource(cmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch32():
    src = inspect.getsource(cmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch32():
    src = inspect.getsource(cmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch32():
    src = inspect.getsource(cmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch32():
    src = inspect.getsource(cmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch32():
    src = inspect.getsource(cmod)
    assert "breakpoint(" not in src


def test_module_source_no_shutil_batch32():
    src = inspect.getsource(cmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch32():
    src = inspect.getsource(cmod)
    assert "requests" not in src


def test_module_source_no_subprocess_batch32():
    src = inspect.getsource(cmod)
    assert "subprocess" not in src


# ---------- module source 字符串精确补强第四十五批 ----------


def test_module_source_contains_module_docstring_batch32():
    src = inspect.getsource(cmod)
    assert "评测 CLI" in src


def test_module_source_contains_argparse_import_batch32():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_source_contains_json_import_batch32():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_source_contains_sys_import_batch32():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_source_contains_pathlib_import_batch32():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_manifest_import_batch32():
    src = inspect.getsource(cmod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_module_source_contains_runner_import_batch32():
    src = inspect.getsource(cmod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_contains_schema_import_batch32():
    src = inspect.getsource(cmod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_module_source_contains_report_import_batch32():
    src = inspect.getsource(cmod)
    assert "from evaluation.report import get_git_provenance" in src


def test_module_source_contains_build_parser_func_batch32():
    src = inspect.getsource(cmod)
    assert "def _build_parser(" in src


def test_module_source_contains_main_func_batch32():
    src = inspect.getsource(cmod)
    assert "def main(" in src


def test_module_source_contains_format_metric_func_batch32():
    src = inspect.getsource(cmod)
    assert "def _format_metric(" in src


def test_module_source_contains_run_inspect_doc_func_batch32():
    src = inspect.getsource(cmod)
    assert "def _run_inspect_doc(" in src


def test_module_source_contains_reconfigure_call_batch32():
    src = inspect.getsource(cmod)
    assert "sys.stdout.reconfigure" in src


def test_module_source_contains_subparsers_batch32():
    src = inspect.getsource(cmod)
    assert "add_subparsers" in src


def test_module_source_contains_raw_description_batch32():
    src = inspect.getsource(cmod)
    assert "RawDescriptionHelpFormatter" in src


def test_module_source_contains_run_subcommand_batch32():
    src = inspect.getsource(cmod)
    assert '"run"' in src
    assert '"validate-report"' in src
    assert '"inspect-doc"' in src


def test_module_source_contains_validate_file_call_batch32():
    src = inspect.getsource(cmod)
    assert 'validate_file(' in src


def test_module_source_contains_load_manifest_call_batch32():
    src = inspect.getsource(cmod)
    assert 'load_manifest(' in src


def test_module_source_contains_run_evaluation_call_batch32():
    src = inspect.getsource(cmod)
    assert 'run_evaluation(' in src


# ---------- signatures 第四十五批 ----------


def test_signature_build_parser_no_params_batch32():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_build_parser_return_argument_parser_batch32():
    sig = inspect.signature(_build_parser)
    assert "ArgumentParser" in str(sig.return_annotation)


def test_signature_main_argv_optional_batch32():
    sig = inspect.signature(main)
    assert "argv" in sig.parameters
    assert sig.parameters["argv"].default is None


def test_signature_main_return_int_batch32():
    sig = inspect.signature(main)
    assert sig.return_annotation == "int"


def test_signature_format_metric_params_batch32():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters.keys())
    assert params == ["name", "metric"]


def test_signature_format_metric_return_str_batch32():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation == "str"


def test_signature_run_inspect_doc_args_param_batch32():
    sig = inspect.signature(_run_inspect_doc)
    assert "args" in sig.parameters


def test_signature_run_inspect_doc_return_int_batch32():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


# ---------- module 合理性第四十五批 ----------


def test_module_has_future_annotations_batch32():
    src = inspect.getsource(cmod)
    assert "from __future__ import annotations" in src


def test_module_imports_argparse_batch32():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_imports_json_batch32():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_imports_sys_batch32():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_imports_pathlib_batch32():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_has_main_block_batch32():
    """cli.py 有 __main__ 块（entry point）。"""
    src = inspect.getsource(cmod)
    assert 'if __name__ == "__main__"' in src


def test_module_main_block_raises_system_exit_batch32():
    src = inspect.getsource(cmod)
    assert "raise SystemExit(main())" in src


# ---------- 端到端集成第四十五批 ----------


def test_e2e_inspect_doc_full_pdf_batch32(capsys, tmp_path):
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


def test_e2e_inspect_doc_idempotent_batch32(capsys, tmp_path):
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
    # 输出 metric 部分（去掉 file path）应一致
    # 但 file path 一样，所以完整输出也应一致
    assert out1 == out2


def test_e2e_validate_report_invalid_returns_1_batch32(capsys, tmp_path):
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_inspect_doc_returns_0_for_minimal_valid_batch32(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_main_no_args_to_stderr_batch32(capsys):
    """无参数 main → SystemExit + argparse 错误打印到 stderr。"""
    with pytest.raises(SystemExit):
        main([])
    captured = capsys.readouterr()
    # argparse 错误信息应在 stderr
    assert captured.err != "" or captured.out != ""


def test_e2e_inspect_doc_with_unknown_source_type_batch32(capsys, tmp_path):
    """unknown source_type → 仍跑（pdf/docx ratio 都 null）。"""
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "weird", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
