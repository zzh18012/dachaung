"""evaluation/cli.py 第六十六轮 edges 测试（Round 593）。

补强 edges65 未触及的角度（第三十九批）。
"""

from __future__ import annotations

import inspect
import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import cli as cmod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 第三十九批


def test_build_parser_no_args_raises_systemexit_batch39():
    """无子命令 → SystemExit（required=True）。"""
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_build_parser_help_runs_clean_batch39(capsys):
    """--help 不会抛异常（虽然 SystemExit）。"""
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--help"])
    captured = capsys.readouterr()
    assert "evaluation.cli" in captured.out or "usage" in captured.out.lower()


def test_build_parser_run_help_runs_clean_batch39(capsys):
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--help"])
    captured = capsys.readouterr()
    assert "manifest" in captured.out


def test_build_parser_validate_report_help_runs_clean_batch39(capsys):
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["validate-report", "--help"])
    captured = capsys.readouterr()
    assert "input" in captured.out


def test_build_parser_inspect_doc_help_runs_clean_batch39(capsys):
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["inspect-doc", "--help"])
    captured = capsys.readouterr()
    assert "input" in captured.out


def test_build_parser_unknown_command_raises_systemexit_batch39():
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["unknown-command"])


def test_build_parser_run_without_manifest_raises_systemexit_batch39():
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["run"])


def test_build_parser_run_without_output_raises_systemexit_batch39():
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--manifest", "x.json"])


def test_build_parser_run_full_args_batch39():
    parser = _build_parser()
    args = parser.parse_args([
        "run", "--manifest", "a.json", "--output", "b.json"
    ])
    assert args.command == "run"
    assert args.manifest == "a.json"
    assert args.output == "b.json"
    assert args.parser == "fallback"  # default
    assert args.max_chars == 800  # default
    assert args.tolerance_chars == 30  # default


def test_build_parser_run_all_args_batch39():
    parser = _build_parser()
    args = parser.parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
        "--parser", "kreuzberg", "--max-chars", "1000",
        "--tolerance-chars", "50",
    ])
    assert args.parser == "kreuzberg"
    assert args.max_chars == 1000
    assert args.tolerance_chars == 50


def test_build_parser_run_invalid_parser_choice_raises_batch39():
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([
            "run", "--manifest", "a.json", "--output", "b.json",
            "--parser", "unknown",
        ])


def test_build_parser_run_invalid_max_chars_raises_batch39():
    """--max-chars 不是 int → SystemExit。"""
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([
            "run", "--manifest", "a.json", "--output", "b.json",
            "--max-chars", "abc",
        ])


def test_build_parser_validate_report_with_input_batch39():
    parser = _build_parser()
    args = parser.parse_args(["validate-report", "report.json"])
    assert args.command == "validate-report"
    assert args.input == "report.json"


def test_build_parser_validate_report_without_input_raises_batch39():
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["validate-report"])


def test_build_parser_inspect_doc_with_input_batch39():
    parser = _build_parser()
    args = parser.parse_args(["inspect-doc", "doc.json"])
    assert args.command == "inspect-doc"
    assert args.input == "doc.json"
    assert args.tolerance_chars == 30  # default


def test_build_parser_inspect_doc_with_tolerance_batch39():
    parser = _build_parser()
    args = parser.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "100"])
    assert args.tolerance_chars == 100


def test_build_parser_inspect_doc_without_input_raises_batch39():
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["inspect-doc"])


def test_build_parser_description_contains_eval_batch39():
    parser = _build_parser()
    assert "评测" in parser.description or "evaluation" in parser.description.lower()


def test_build_parser_prog_value_batch39():
    parser = _build_parser()
    assert parser.prog == "evaluation.cli"


# ---------- _format_metric 第三十九批


def test_format_metric_with_none_value_batch39():
    out = _format_metric("x", {"value": None, "reason": "no_data"})
    assert "null" in out
    assert "no_data" in out


def test_format_metric_with_true_value_batch39():
    out = _format_metric("x", {"value": True, "reason": None})
    assert "true" in out  # 小写 bool


def test_format_metric_with_false_value_batch39():
    out = _format_metric("x", {"value": False, "reason": None})
    assert "false" in out


def test_format_metric_with_int_value_batch39():
    """int 不是 float，落入 fallback 分支。"""
    out = _format_metric("x", {"value": 5, "reason": None})
    assert "5" in out


def test_format_metric_with_zero_int_value_batch39():
    out = _format_metric("x", {"value": 0, "reason": None})
    assert "0" in out


def test_format_metric_with_float_value_batch39():
    out = _format_metric("x", {"value": 0.5, "reason": None})
    assert "0.5000" in out


def test_format_metric_with_dict_value_batch39():
    """dict 类型 value。"""
    out = _format_metric("x", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out


def test_format_metric_with_empty_dict_value_batch39():
    out = _format_metric("x", {"value": {}, "reason": None})
    # 空字典 → items 是空字符串
    assert "x" in out


def test_format_metric_with_string_value_batch39():
    """str 落入 fallback 分支。"""
    out = _format_metric("x", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_value_with_reason_fallback_batch39():
    """bool value 含 reason → 显示 reason。"""
    out = _format_metric("x", {"value": True, "reason": "explicit_reason"})
    assert "explicit_reason" in out


def test_format_metric_with_unicode_reason_batch39():
    out = _format_metric("x", {"value": None, "reason": "中文原因"})
    assert "中文原因" in out


def test_format_metric_returns_str_batch39():
    out = _format_metric("x", {"value": None, "reason": "x"})
    assert isinstance(out, str)


def test_format_metric_with_long_name_batch39():
    out = _format_metric("x" * 100, {"value": True, "reason": None})
    assert isinstance(out, str)
    assert "true" in out


def test_format_metric_alignment_width_batch39():
    """name 占 36 字符宽。"""
    out = _format_metric("ab", {"value": True, "reason": None})
    # 至少包含两个前导空格 + name + 填充空格
    assert "  ab" in out


# ---------- _run_inspect_doc 第三十九批


def _make_args(input_path, tolerance_chars=30):
    args = MagicMock()
    args.input = str(input_path)
    args.tolerance_chars = tolerance_chars
    return args


def test_run_inspect_doc_missing_file_returns_2_batch39(tmp_path, capsys):
    p = tmp_path / "missing.json"
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 2
    captured = capsys.readouterr()
    assert "ERROR" in captured.err


def test_run_inspect_doc_invalid_json_returns_1_batch39(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 1


def test_run_inspect_doc_top_level_not_dict_returns_1_batch39(tmp_path, capsys):
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 1


def test_run_inspect_doc_top_level_int_returns_1_batch39(tmp_path):
    p = tmp_path / "i.json"
    p.write_text("42", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 1


def test_run_inspect_doc_top_level_string_returns_1_batch39(tmp_path):
    p = tmp_path / "s.json"
    p.write_text('"hello"', encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 1


def test_run_inspect_doc_empty_dict_returns_0_batch39(tmp_path, capsys):
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 0


def test_run_inspect_doc_prints_metrics_header_batch39(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_prints_file_path_batch39(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "file:" in captured.out
    assert str(p) in captured.out


def test_run_inspect_doc_prints_document_id_batch39(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"document_id": "abc"}), encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "document_id:" in captured.out
    assert "abc" in captured.out


def test_run_inspect_doc_prints_source_type_batch39(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf"}), encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "type=pdf" in captured.out


def test_run_inspect_doc_prints_elements_count_batch39(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [{"type": "x"}, {"type": "y"}]}), encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "elements=2" in captured.out


def test_run_inspect_doc_prints_chunks_count_batch39(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"chunks": [{"text": "a"}]}), encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "chunks=1" in captured.out


def test_run_inspect_doc_with_parser_info_batch39(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "parser_name": "fallback",
        "parser_version": "0.1.0",
    }), encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "fallback" in captured.out
    assert "0.1.0" in captured.out


def test_run_inspect_doc_signature_one_param_batch39():
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters.keys()) == ["args"]


def test_run_inspect_doc_return_int_batch39():
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in str(sig.return_annotation)


# ---------- main 第三十九批


def test_main_no_args_raises_systemexit_batch39():
    """main 无参数 → SystemExit（argparse required=True）。"""
    with pytest.raises(SystemExit):
        main([])


def test_main_unknown_command_raises_systemexit_batch39():
    with pytest.raises(SystemExit):
        main(["unknown"])


def test_main_run_missing_manifest_returns_2_batch39(tmp_path, capsys):
    manifest_path = tmp_path / "missing.json"
    rc = main(["run", "--manifest", str(manifest_path), "--output", str(tmp_path / "out.json")])
    assert rc == 2


def test_main_validate_report_missing_file_returns_2_batch39(tmp_path, capsys):
    p = tmp_path / "missing.json"
    rc = main(["validate-report", str(p)])
    assert rc == 2


def test_main_inspect_doc_missing_file_returns_2_batch39(tmp_path, capsys):
    p = tmp_path / "missing.json"
    rc = main(["inspect-doc", str(p)])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_1_batch39(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_invalid_json_returns_1_batch39(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_callable_batch39():
    assert callable(main)


def test_main_returns_int_for_unknown_after_parse_batch39(tmp_path):
    """通过 main 走到 unknown_command 路径（argparse 拒绝，走 SystemExit）。"""
    with pytest.raises(SystemExit):
        main(["--unknown-flag"])


def test_main_signature_one_param_optional_batch39():
    sig = inspect.signature(main)
    assert list(sig.parameters.keys()) == ["argv"]


def test_main_argv_default_none_batch39():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_return_int_batch39():
    sig = inspect.signature(main)
    assert "int" in str(sig.return_annotation)


# ---------- module source forbidden tokens 第六十六批


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
def test_module_source_no_forbidden_tokens_batch39(token):
    src = inspect.getsource(cmod)
    assert token not in src


# ---------- module source 字符串精确补强第六十二批


def test_module_source_contains_design_doc_batch39():
    src = inspect.getsource(cmod)
    assert "评测 CLI" in src


def test_module_source_contains_argparse_import_batch39():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_source_contains_json_import_batch39():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_source_contains_sys_import_batch39():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_source_contains_pathlib_import_batch39():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_manifest_import_batch39():
    src = inspect.getsource(cmod)
    assert "from evaluation.manifest import" in src


def test_module_source_contains_report_import_batch39():
    src = inspect.getsource(cmod)
    assert "from evaluation.report import" in src


def test_module_source_contains_runner_import_batch39():
    src = inspect.getsource(cmod)
    assert "from evaluation.runner import" in src


def test_module_source_contains_schema_import_batch39():
    src = inspect.getsource(cmod)
    assert "from evaluation.schema import" in src


def test_module_source_contains_build_parser_function_batch39():
    src = inspect.getsource(cmod)
    assert "def _build_parser(" in src


def test_module_source_contains_main_function_batch39():
    src = inspect.getsource(cmod)
    assert "def main(" in src


def test_module_source_contains_format_metric_function_batch39():
    src = inspect.getsource(cmod)
    assert "def _format_metric(" in src


def test_module_source_contains_run_inspect_doc_function_batch39():
    src = inspect.getsource(cmod)
    assert "def _run_inspect_doc(" in src


def test_module_source_contains_subparsers_batch39():
    src = inspect.getsource(cmod)
    assert "add_subparsers" in src


def test_module_source_contains_required_true_batch39():
    src = inspect.getsource(cmod)
    assert "required=True" in src


def test_module_source_contains_run_subparser_batch39():
    src = inspect.getsource(cmod)
    assert '"run"' in src or "'run'" in src


def test_module_source_contains_validate_report_subparser_batch39():
    src = inspect.getsource(cmod)
    assert '"validate-report"' in src or "'validate-report'" in src


def test_module_source_contains_inspect_doc_subparser_batch39():
    src = inspect.getsource(cmod)
    assert '"inspect-doc"' in src or "'inspect-doc'" in src


def test_module_source_contains_future_annotations_batch39():
    src = inspect.getsource(cmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_utf8_reconfigure_batch39():
    """Windows 控制台 utf-8 修复。"""
    src = inspect.getsource(cmod)
    assert "reconfigure" in src


# ---------- module 合理性 第六十二批


def test_module_has_main_attribute_batch39():
    assert hasattr(cmod, "main")


def test_module_has_build_parser_attribute_batch39():
    assert hasattr(cmod, "_build_parser")


def test_module_has_format_metric_attribute_batch39():
    assert hasattr(cmod, "_format_metric")


def test_module_has_run_inspect_doc_attribute_batch39():
    assert hasattr(cmod, "_run_inspect_doc")


def test_module_main_callable_batch39():
    assert callable(cmod.main)


def test_module_build_parser_callable_batch39():
    assert callable(cmod._build_parser)


def test_module_no_class_definitions_batch39():
    src = inspect.getsource(cmod)
    assert "\nclass " not in src


def test_module_has_main_guard_batch39():
    """模块底部有 __main__ guard。"""
    src = inspect.getsource(cmod)
    assert 'if __name__ == "__main__"' in src


def test_module_has_system_exit_call_batch39():
    src = inspect.getsource(cmod)
    assert "SystemExit" in src or "sys.exit" in src


# ---------- 端到端集成 第六十二批


def test_e2e_inspect_doc_minimal_dict_batch39(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 0


def test_e2e_inspect_doc_full_dict_batch39(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "x",
        "source_type": "pdf",
        "source_path": "test.pdf",
        "parser_name": "fallback",
        "parser_version": "0.1.0",
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1",
                      "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }), encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert rc == 0
    assert "x" in captured.out
    assert "elements=1" in captured.out


def test_e2e_idempotent_inspect_doc_batch39(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    out1 = capsys.readouterr().out
    _run_inspect_doc(_make_args(p))
    out2 = capsys.readouterr().out
    assert out1 == out2


def test_e2e_inspect_doc_does_not_write_batch39(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    before = set(tmp_path.iterdir())
    _run_inspect_doc(_make_args(p))
    after = set(tmp_path.iterdir())
    assert before == after


def test_e2e_format_metric_each_value_type_batch39():
    """四种 value 类型都能 format 不抛异常。"""
    _format_metric("a", {"value": None, "reason": "x"})
    _format_metric("a", {"value": True, "reason": None})
    _format_metric("a", {"value": 0.5, "reason": None})
    _format_metric("a", {"value": {"x": 1}, "reason": None})
    _format_metric("a", {"value": "str", "reason": None})  # fallback
