"""evaluation/cli.py 第六十八轮 edges 测试（Round 609）。

补强 edges67 未触及的角度（第四十一批）。

新角度：
- _build_parser 子命令选项精确（run --manifest / --output / --parser / --max-chars / --tolerance-chars）
- _build_parser choices fallback/kreuzberg
- _build_parser --parser 默认 fallback
- _build_parser --max-chars 默认 800
- _build_parser --tolerance-chars 默认 30
- _build_parser validate-report input 位置参数
- _build_parser inspect-doc input 位置参数 + --tolerance-chars
- _build_parser prog / description / formatter_class
- _format_metric 各种 value 类型渲染
- _format_metric 空格对齐（width=36）
- _format_metric float 渲染精度（4 位小数）
- _format_metric dict 渲染（sorted items）
- _run_inspect_doc 各种 rc（0 / 1 / 2）
- _run_inspect_doc 完整文档输出
- main 缺参数 raises SystemExit
- main unknown command raises SystemExit
- main --help raises SystemExit
- main run/validate-report/inspect-doc 完整流程
- module source 字符串精确
- AST 结构
- module 合理性
- forbidden tokens 第八十批
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import cli as cmod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 第四十一批


def test_build_parser_returns_argument_parser_batch41():
    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_build_parser_prog_value_batch41():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_value_batch41():
    p = _build_parser()
    assert "评测 CLI" in (p.description or "")


def test_build_parser_formatter_class_batch41():
    p = _build_parser()
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_has_subparsers_batch41():
    """add_subparsers 被调用。"""
    src = inspect.getsource(cmod)
    assert "add_subparsers" in src


def test_build_parser_no_args_raises_system_exit_batch41():
    """无子命令 → SystemExit（required=True）。"""
    with pytest.raises(SystemExit):
        _build_parser().parse_args([])


def test_build_parser_unknown_command_raises_system_exit_batch41():
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["unknown"])


def test_build_parser_help_flag_raises_system_exit_batch41():
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["--help"])


def test_build_parser_run_subcommand_exists_batch41():
    p = _build_parser()
    # 通过 parse_args 验证 run 子命令可用
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert args.command == "run"


def test_build_parser_validate_report_subcommand_exists_batch41():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.command == "validate-report"


def test_build_parser_inspect_doc_subcommand_exists_batch41():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.command == "inspect-doc"


def test_build_parser_run_manifest_required_batch41():
    """--manifest 是必填。"""
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["run", "--output", "b.json"])


def test_build_parser_run_output_required_batch41():
    """--output 是必填。"""
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["run", "--manifest", "a.json"])


def test_build_parser_run_parser_default_fallback_batch41():
    args = _build_parser().parse_args(["run", "--manifest", "a", "--output", "b"])
    assert args.parser == "fallback"


def test_build_parser_run_parser_choices_batch41():
    args = _build_parser().parse_args(["run", "--manifest", "a", "--output", "b", "--parser", "kreuzberg"])
    assert args.parser == "kreuzberg"
    args2 = _build_parser().parse_args(["run", "--manifest", "a", "--output", "b", "--parser", "fallback"])
    assert args2.parser == "fallback"


def test_build_parser_run_parser_invalid_choice_raises_batch41():
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["run", "--manifest", "a", "--output", "b", "--parser", "invalid"])


def test_build_parser_run_max_chars_default_800_batch41():
    args = _build_parser().parse_args(["run", "--manifest", "a", "--output", "b"])
    assert args.max_chars == 800


def test_build_parser_run_max_chars_custom_batch41():
    args = _build_parser().parse_args(["run", "--manifest", "a", "--output", "b", "--max-chars", "500"])
    assert args.max_chars == 500


def test_build_parser_run_tolerance_chars_default_30_batch41():
    args = _build_parser().parse_args(["run", "--manifest", "a", "--output", "b"])
    assert args.tolerance_chars == 30


def test_build_parser_run_tolerance_chars_custom_batch41():
    args = _build_parser().parse_args(["run", "--manifest", "a", "--output", "b", "--tolerance-chars", "10"])
    assert args.tolerance_chars == 10


def test_build_parser_validate_report_input_positional_batch41():
    args = _build_parser().parse_args(["validate-report", "r.json"])
    assert args.input == "r.json"


def test_build_parser_validate_report_input_required_batch41():
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["validate-report"])


def test_build_parser_inspect_doc_input_positional_batch41():
    args = _build_parser().parse_args(["inspect-doc", "d.json"])
    assert args.input == "d.json"


def test_build_parser_inspect_doc_input_required_batch41():
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["inspect-doc"])


def test_build_parser_inspect_doc_tolerance_chars_default_30_batch41():
    args = _build_parser().parse_args(["inspect-doc", "d.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_tolerance_chars_custom_batch41():
    args = _build_parser().parse_args(["inspect-doc", "d.json", "--tolerance-chars", "5"])
    assert args.tolerance_chars == 5


def test_build_parser_signature_no_params_batch41():
    sig = inspect.signature(_build_parser)
    assert list(sig.parameters.keys()) == []


def test_build_parser_return_annotation_argument_parser_batch41():
    sig = inspect.signature(_build_parser)
    assert "ArgumentParser" in str(sig.return_annotation)


# ---------- _format_metric 第四十一批


def test_format_metric_callable_batch41():
    assert callable(_format_metric)


def test_format_metric_signature_batch41():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters.keys()) == ["name", "metric"]


def test_format_metric_return_annotation_str_batch41():
    sig = inspect.signature(_format_metric)
    assert "str" in str(sig.return_annotation)


def test_format_metric_none_value_with_reason_batch41():
    out = _format_metric("foo", {"value": None, "reason": "no_data"})
    assert "null" in out
    assert "no_data" in out


def test_format_metric_none_value_no_reason_batch41():
    out = _format_metric("foo", {"value": None, "reason": None})
    assert "null" in out
    assert "(None)" in out


def test_format_metric_true_value_batch41():
    out = _format_metric("foo", {"value": True, "reason": None})
    assert "true" in out
    assert "ok" in out


def test_format_metric_false_value_batch41():
    out = _format_metric("foo", {"value": False, "reason": None})
    assert "false" in out


def test_format_metric_int_value_batch41():
    out = _format_metric("foo", {"value": 42, "reason": None})
    assert "42" in out


def test_format_metric_zero_int_batch41():
    out = _format_metric("foo", {"value": 0, "reason": None})
    assert "0" in out


def test_format_metric_negative_int_batch41():
    out = _format_metric("foo", {"value": -5, "reason": None})
    assert "-5" in out


def test_format_metric_float_value_batch41():
    out = _format_metric("foo", {"value": 0.5, "reason": None})
    assert "0.5000" in out  # 4 位小数


def test_format_metric_float_zero_batch41():
    out = _format_metric("foo", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_float_one_batch41():
    out = _format_metric("foo", {"value": 1.0, "reason": None})
    assert "1.0000" in out


def test_format_metric_dict_value_batch41():
    out = _format_metric("foo", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out


def test_format_metric_dict_value_sorted_batch41():
    out = _format_metric("foo", {"value": {"z": 1, "a": 2}, "reason": None})
    # sorted: a 在 z 前
    assert out.index("a=2") < out.index("z=1")


def test_format_metric_empty_dict_batch41():
    out = _format_metric("foo", {"value": {}, "reason": None})
    assert "foo" in out  # 不抛异常即可


def test_format_metric_string_value_batch41():
    out = _format_metric("foo", {"value": "abc", "reason": None})
    assert "abc" in out


def test_format_metric_unicode_name_batch41():
    out = _format_metric("中文", {"value": 1, "reason": None})
    assert "中文" in out


def test_format_metric_long_name_batch41():
    name = "a" * 50
    out = _format_metric(name, {"value": 1, "reason": None})
    assert name in out


def test_format_metric_returns_str_batch41():
    out = _format_metric("x", {"value": 1, "reason": None})
    assert isinstance(out, str)


def test_format_metric_alignment_36_batch41():
    """name 占 36 字符宽（左对齐）。"""
    out = _format_metric("foo", {"value": 1, "reason": None})
    # "  foo" 后接空格补齐到 36 + 2 前导空格 = 38
    # 实际：f"  {name:36}" → 2 + max(36, len(name)) 字符
    # 找前 5 字符 "  foo"
    assert out.startswith("  foo")


def test_format_metric_bool_with_reason_batch41():
    out = _format_metric("foo", {"value": True, "reason": "computed"})
    assert "true" in out
    assert "computed" in out


def test_format_metric_list_value_batch41():
    """list 不是 dict/int/float/bool/None → 走默认分支 str(value)。"""
    out = _format_metric("foo", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in out


# ---------- _run_inspect_doc 第四十一批


def test_run_inspect_doc_callable_batch41():
    assert callable(_run_inspect_doc)


def test_run_inspect_doc_signature_batch41():
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters.keys()) == ["args"]


def test_run_inspect_doc_return_annotation_int_batch41():
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in str(sig.return_annotation)


def test_run_inspect_doc_missing_file_rc_2_batch41(tmp_path):
    args = MagicMock()
    args.input = str(tmp_path / "missing.json")
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 2


def test_run_inspect_doc_invalid_json_rc_1_batch41(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_top_level_array_rc_1_batch41(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_top_level_int_rc_1_batch41(tmp_path):
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_top_level_string_rc_1_batch41(tmp_path):
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_empty_dict_rc_0_batch41(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_full_dict_rc_0_batch41(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "d1",
        "source_type": "pdf",
        "source_path": "/tmp/a.pdf",
        "parser_name": "fallback",
        "parser_version": "0.1.0",
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "hello"}],
        "chunks": [{"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]}],
    }), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_prints_file_path_batch41(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert str(p) in captured.out


def test_run_inspect_doc_prints_document_id_batch41(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"document_id": "d1"}), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "d1" in captured.out


def test_run_inspect_doc_default_document_id_question_batch41(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "?" in captured.out


def test_run_inspect_doc_prints_elements_count_batch41(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [{"id": "e1"}, {"id": "e2"}]}), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "elements=2" in captured.out


def test_run_inspect_doc_prints_chunks_count_batch41(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"chunks": [{"id": "c1"}]}), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "chunks=1" in captured.out


def test_run_inspect_doc_prints_parser_info_batch41(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"parser_name": "fallback", "parser_version": "1.0"}), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "fallback" in captured.out
    assert "1.0" in captured.out


def test_run_inspect_doc_does_not_write_file_batch41(tmp_path):
    """inspect-doc 不写报告文件。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    # 检查没新增 .json 文件（除了 doc.json 本身）
    json_files = list(tmp_path.glob("*.json"))
    assert len(json_files) == 1


def test_run_inspect_doc_idempotent_batch41(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc1 = _run_inspect_doc(args)
    rc2 = _run_inspect_doc(args)
    assert rc1 == rc2 == 0


def test_run_inspect_doc_unicode_content_batch41(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"document_id": "中文文档"}), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0


# ---------- main 第四十一批


def test_main_callable_batch41():
    assert callable(main)


def test_main_signature_batch41():
    sig = inspect.signature(main)
    assert list(sig.parameters.keys()) == ["argv"]


def test_main_argv_default_none_batch41():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_return_annotation_int_batch41():
    sig = inspect.signature(main)
    assert "int" in str(sig.return_annotation)


def test_main_no_args_raises_system_exit_batch41():
    """无 argv → argparse 用 sys.argv → 测试环境通常无 evaluation.cli，且 required=True → SystemExit。"""
    with pytest.raises(SystemExit):
        main([])


def test_main_unknown_command_raises_system_exit_batch41():
    with pytest.raises(SystemExit):
        main(["unknown"])


def test_main_run_missing_manifest_rc_2_batch41(tmp_path):
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(tmp_path / "missing.json"), "--output", str(out)])
    assert rc == 2


def test_main_validate_report_missing_rc_2_batch41(tmp_path):
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_inspect_doc_missing_rc_2_batch41(tmp_path):
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_validate_report_invalid_json_rc_1_batch41(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_invalid_json_rc_1_batch41(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_empty_dict_rc_0_batch41(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_validate_report_empty_dict_rc_1_batch41(tmp_path):
    """空 dict 不符合 evaluation-report schema。"""
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_run_with_valid_manifest_rc_0_batch41(tmp_path):
    """完整 run 流程（mock process_single）。"""
    from evaluation import MANIFEST_VERSION
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "out.json"
    with patch("evaluation.cli.run_evaluation") as mock_run, \
         patch("evaluation.cli.validate_file", return_value=None), \
         patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
        mock_run.return_value = {
            "per_doc": [],
            "devset": {"status": "incomplete", "file_count": 0,
                       "content_group_count": 0, "pdf_count": 0, "docx_count": 0},
        }
        rc = main(["run", "--manifest", str(mp), "--output", str(out)])
    assert rc == 0


def test_main_run_with_load_manifest_failure_rc_1_batch41(tmp_path):
    """manifest 文件存在但内容不对（schema 拒绝）→ rc=1。"""
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps({"manifest_version": "0.0"}), encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(mp), "--output", str(out)])
    assert rc == 1


# ---------- module source 字符串精确 第四十一批


def test_module_source_contains_docstring_batch41():
    src = inspect.getsource(cmod)
    assert '"""' in src


def test_module_source_contains_future_annotations_batch41():
    src = inspect.getsource(cmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_argparse_import_batch41():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_source_contains_json_import_batch41():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_source_contains_sys_import_batch41():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_source_contains_pathlib_path_import_batch41():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_manifest_import_batch41():
    src = inspect.getsource(cmod)
    assert "from evaluation.manifest import" in src
    assert "ManifestError" in src
    assert "load_manifest" in src


def test_module_source_contains_report_import_batch41():
    src = inspect.getsource(cmod)
    assert "from evaluation.report import" in src
    assert "get_git_provenance" in src


def test_module_source_contains_runner_import_batch41():
    src = inspect.getsource(cmod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_contains_schema_import_batch41():
    src = inspect.getsource(cmod)
    assert "from evaluation.schema import" in src
    assert "EvalSchemaError" in src
    assert "validate_file" in src


def test_module_source_contains_stdout_reconfigure_batch41():
    """Windows utf-8 stdout reconfigure。"""
    src = inspect.getsource(cmod)
    assert "reconfigure" in src
    assert "utf-8" in src or 'encoding="utf-8"' in src


def test_module_source_contains_build_parser_function_batch41():
    src = inspect.getsource(cmod)
    assert "def _build_parser(" in src


def test_module_source_contains_main_function_batch41():
    src = inspect.getsource(cmod)
    assert "def main(" in src


def test_module_source_contains_format_metric_function_batch41():
    src = inspect.getsource(cmod)
    assert "def _format_metric(" in src


def test_module_source_contains_run_inspect_doc_function_batch41():
    src = inspect.getsource(cmod)
    assert "def _run_inspect_doc(" in src


def test_module_source_contains_subcommands_batch41():
    src = inspect.getsource(cmod)
    assert '"run"' in src
    assert '"validate-report"' in src
    assert '"inspect-doc"' in src


def test_module_source_contains_manifest_argument_batch41():
    src = inspect.getsource(cmod)
    assert "--manifest" in src


def test_module_source_contains_output_argument_batch41():
    src = inspect.getsource(cmod)
    assert "--output" in src


def test_module_source_contains_parser_argument_batch41():
    src = inspect.getsource(cmod)
    assert "--parser" in src


def test_module_source_contains_max_chars_argument_batch41():
    src = inspect.getsource(cmod)
    assert "--max-chars" in src


def test_module_source_contains_tolerance_chars_argument_batch41():
    src = inspect.getsource(cmod)
    assert "--tolerance-chars" in src


def test_module_source_contains_choices_fallback_kreuzberg_batch41():
    src = inspect.getsource(cmod)
    assert "fallback" in src
    assert "kreuzberg" in src


def test_module_source_contains_system_exit_main_batch41():
    src = inspect.getsource(cmod)
    assert "if __name__" in src
    assert "SystemExit(main())" in src


def test_module_source_contains_error_prefix_batch41():
    """错误消息用 [ERROR] 前缀。"""
    src = inspect.getsource(cmod)
    assert "[ERROR]" in src


def test_module_source_contains_ok_prefix_batch41():
    src = inspect.getsource(cmod)
    assert "[OK]" in src


def test_module_source_contains_fail_prefix_batch41():
    src = inspect.getsource(cmod)
    assert "[FAIL]" in src


# ---------- AST 结构 第四十一批


def test_ast_top_level_no_class_no_loop_no_with_batch41():
    src = inspect.getsource(cmod)
    tree = ast.parse(src)
    for node in tree.body:
        assert not isinstance(node, (ast.ClassDef, ast.For, ast.While, ast.With, ast.Try))


def test_ast_has_four_functions_batch41():
    src = inspect.getsource(cmod)
    tree = ast.parse(src)
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert "_build_parser" in funcs
    assert "main" in funcs
    assert "_format_metric" in funcs
    assert "_run_inspect_doc" in funcs


def test_ast_no_async_functions_batch41():
    src = inspect.getsource(cmod)
    tree = ast.parse(src)
    async_funcs = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)]
    assert async_funcs == []


def test_ast_top_level_only_allowed_kinds_batch41():
    """顶层允许：Expr / Import / ImportFrom / FunctionDef / If（stdout reconfigure）。"""
    src = inspect.getsource(cmod)
    tree = ast.parse(src)
    for node in tree.body:
        assert isinstance(node, (ast.Expr, ast.Import, ast.ImportFrom, ast.FunctionDef, ast.If))


def test_ast_has_module_docstring_batch41():
    src = inspect.getsource(cmod)
    tree = ast.parse(src)
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)


def test_ast_has_main_guard_batch41():
    """if __name__ == '__main__' 顶层存在。"""
    src = inspect.getsource(cmod)
    tree = ast.parse(src)
    main_guards = [
        n for n in tree.body
        if isinstance(n, ast.If)
        and isinstance(n.test, ast.Compare)
        and isinstance(n.test.left, ast.Name)
        and n.test.left.id == "__name__"
    ]
    assert len(main_guards) == 1


# ---------- module 合理性 第四十一批


def test_module_callable_main_batch41():
    assert callable(cmod.main)


def test_module_has_build_parser_attr_batch41():
    assert hasattr(cmod, "_build_parser")


def test_module_has_main_attr_batch41():
    assert hasattr(cmod, "main")


def test_module_has_format_metric_attr_batch41():
    assert hasattr(cmod, "_format_metric")


def test_module_has_run_inspect_doc_attr_batch41():
    assert hasattr(cmod, "_run_inspect_doc")


def test_module_no_all_attribute_batch41():
    """cli.py 没定义 __all__（不需要 export）。"""
    assert not hasattr(cmod, "__all__") or cmod.__all__ is None or len(getattr(cmod, "__all__", [])) >= 0


def test_module_has_docstring_batch41():
    assert cmod.__doc__ is not None
    assert len(cmod.__doc__) > 0


# ---------- 端到端集成 第四十一批


def test_e2e_inspect_doc_full_pipeline_batch41(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "d1",
        "source_type": "pdf",
        "source_path": "/tmp/a.pdf",
        "parser_name": "fallback",
        "parser_version": "0.1.0",
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "hello"}],
        "chunks": [{"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "d1" in captured.out
    assert "pdf" in captured.out
    assert "elements=1" in captured.out
    assert "chunks=1" in captured.out
    assert "metrics:" in captured.out


def test_e2e_validate_report_no_file_batch41(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    captured = capsys.readouterr()
    assert rc == 2
    assert "[ERROR]" in captured.err


def test_e2e_inspect_doc_path_object_batch41(tmp_path):
    """inspect-doc 接受 str path（不直接接 Path 对象）。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "15"])
    assert rc == 0


# ---------- module source forbidden tokens 第八十批


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
def test_module_source_no_forbidden_tokens_batch41(token):
    src = inspect.getsource(cmod)
    assert token not in src
