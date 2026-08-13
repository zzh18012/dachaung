"""evaluation/cli.py 第六十七轮 edges 测试（Round 602）。

补强 edges66 未触及的角度（第四十批）。
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import cli as cmod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 第四十批


def test_build_parser_returns_argument_parser_batch40():
    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser) if (argparse := __import__("argparse")) else True


def test_build_parser_prog_value_batch40():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_contains_eval_batch40():
    p = _build_parser()
    assert "评测" in p.description


def test_build_parser_has_subparsers_batch40():
    p = _build_parser()
    # argparse 内部属性
    assert p._subparsers is not None


def test_build_parser_no_args_raises_systemexit_batch40():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_parser_unknown_command_raises_systemexit_batch40():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["unknown-command"])


def test_build_parser_help_command_raises_systemexit_batch40(capsys):
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["--help"])
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower() or "评测" in captured.out


def test_build_parser_run_subcommand_exists_batch40():
    p = _build_parser()
    # 尝试解析 run 子命令
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert args.command == "run"


def test_build_parser_validate_report_subcommand_exists_batch40():
    p = _build_parser()
    args = p.parse_args(["validate-report", "r.json"])
    assert args.command == "validate-report"


def test_build_parser_inspect_doc_subcommand_exists_batch40():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "d.json"])
    assert args.command == "inspect-doc"


def test_build_parser_run_choices_for_parser_batch40():
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
        "--parser", "kreuzberg",
    ])
    assert args.parser == "kreuzberg"


def test_build_parser_run_invalid_parser_raises_batch40():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run", "--manifest", "a.json", "--output", "b.json",
            "--parser", "invalid",
        ])


def test_build_parser_run_default_parser_fallback_batch40():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert args.parser == "fallback"


def test_build_parser_run_default_max_chars_800_batch40():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert args.max_chars == 800


def test_build_parser_run_default_tolerance_chars_30_batch40():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert args.tolerance_chars == 30


def test_build_parser_run_custom_max_chars_batch40():
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
        "--max-chars", "1500",
    ])
    assert args.max_chars == 1500


def test_build_parser_run_custom_tolerance_chars_batch40():
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
        "--tolerance-chars", "100",
    ])
    assert args.tolerance_chars == 100


def test_build_parser_run_invalid_max_chars_raises_batch40():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run", "--manifest", "a.json", "--output", "b.json",
            "--max-chars", "abc",
        ])


def test_build_parser_inspect_doc_default_tolerance_chars_30_batch40():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "d.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_custom_tolerance_chars_batch40():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "d.json", "--tolerance-chars", "55"])
    assert args.tolerance_chars == 55


def test_build_parser_run_manifest_required_batch40():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "b.json"])


def test_build_parser_run_output_required_batch40():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "a.json"])


def test_build_parser_validate_report_input_required_batch40():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["validate-report"])


def test_build_parser_inspect_doc_input_required_batch40():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["inspect-doc"])


def test_build_parser_callable_batch40():
    assert callable(_build_parser)


def test_build_parser_no_params_batch40():
    sig = inspect.signature(_build_parser)
    assert list(sig.parameters.keys()) == []


def test_build_parser_return_annotation_argparse_batch40():
    sig = inspect.signature(_build_parser)
    assert "ArgumentParser" in str(sig.return_annotation)


# ---------- _format_metric 第四十批


def test_format_metric_callable_batch40():
    assert callable(_format_metric)


def test_format_metric_signature_two_params_batch40():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters.keys()) == ["name", "metric"]


def test_format_metric_return_annotation_str_batch40():
    sig = inspect.signature(_format_metric)
    assert "str" in str(sig.return_annotation)


def test_format_metric_with_none_value_and_reason_batch40():
    out = _format_metric("x", {"value": None, "reason": "why"})
    assert "null" in out
    assert "why" in out


def test_format_metric_with_none_value_no_reason_batch40():
    out = _format_metric("x", {"value": None, "reason": None})
    assert "null" in out
    assert "None" in out  # reason=None 被 f-string 渲染为 None


def test_format_metric_with_true_value_batch40():
    out = _format_metric("x", {"value": True, "reason": None})
    assert "true" in out  # 小写


def test_format_metric_with_false_value_batch40():
    out = _format_metric("x", {"value": False, "reason": None})
    assert "false" in out


def test_format_metric_with_int_value_batch40():
    """int 不是 float，落入 fallback 分支。"""
    out = _format_metric("x", {"value": 42, "reason": None})
    assert "42" in out


def test_format_metric_with_zero_int_batch40():
    out = _format_metric("x", {"value": 0, "reason": None})
    assert "0" in out


def test_format_metric_with_negative_int_batch40():
    out = _format_metric("x", {"value": -1, "reason": None})
    assert "-1" in out


def test_format_metric_with_float_value_batch40():
    out = _format_metric("x", {"value": 0.5, "reason": None})
    assert "0.5000" in out


def test_format_metric_with_float_zero_batch40():
    out = _format_metric("x", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_with_float_one_batch40():
    out = _format_metric("x", {"value": 1.0, "reason": None})
    assert "1.0000" in out


def test_format_metric_with_dict_value_batch40():
    out = _format_metric("x", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out


def test_format_metric_with_empty_dict_value_batch40():
    out = _format_metric("x", {"value": {}, "reason": None})
    assert isinstance(out, str)


def test_format_metric_with_string_value_batch40():
    """str 落入 fallback 分支（不是 bool/float/dict/None）。"""
    out = _format_metric("x", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_with_list_value_batch40():
    """list 落入 fallback 分支。"""
    out = _format_metric("x", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in out


def test_format_metric_with_unicode_name_batch40():
    out = _format_metric("中文", {"value": True, "reason": None})
    assert "中文" in out


def test_format_metric_with_reason_in_bool_branch_batch40():
    """bool value + 非 None reason → 显示 reason。"""
    out = _format_metric("x", {"value": True, "reason": "ok_reason"})
    assert "ok_reason" in out


def test_format_metric_with_long_name_batch40():
    name = "x" * 100
    out = _format_metric(name, {"value": True, "reason": None})
    assert name in out


def test_format_metric_returns_str_batch40():
    out = _format_metric("x", {"value": None, "reason": None})
    assert isinstance(out, str)


def test_format_metric_alignment_width_batch40():
    """name 占 36 字符宽。"""
    out = _format_metric("ab", {"value": True, "reason": None})
    # 至少包含两个前导空格 + name + 填充空格
    assert "  ab" in out


def test_format_metric_dict_value_sorted_batch40():
    """dict value 渲染时按 key 排序。"""
    out = _format_metric("x", {"value": {"b": 2, "a": 1}, "reason": None})
    # a 应在 b 前
    assert out.index("a=1") < out.index("b=2")


# ---------- _run_inspect_doc 第四十批


def _make_args(input_path, tolerance_chars=30):
    args = MagicMock()
    args.input = str(input_path)
    args.tolerance_chars = tolerance_chars
    return args


def test_run_inspect_doc_callable_batch40():
    assert callable(_run_inspect_doc)


def test_run_inspect_doc_signature_one_param_batch40():
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters.keys()) == ["args"]


def test_run_inspect_doc_return_annotation_int_batch40():
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in str(sig.return_annotation)


def test_run_inspect_doc_missing_file_returns_2_batch40(tmp_path, capsys):
    p = tmp_path / "missing.json"
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 2
    captured = capsys.readouterr()
    assert "ERROR" in captured.err


def test_run_inspect_doc_invalid_json_returns_1_batch40(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 1
    captured = capsys.readouterr()
    assert "JSON" in captured.err or "ERROR" in captured.err


def test_run_inspect_doc_top_level_not_dict_returns_1_batch40(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 1


def test_run_inspect_doc_top_level_int_returns_1_batch40(tmp_path):
    p = tmp_path / "i.json"
    p.write_text("42", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 1


def test_run_inspect_doc_top_level_string_returns_1_batch40(tmp_path):
    p = tmp_path / "s.json"
    p.write_text('"hello"', encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 1


def test_run_inspect_doc_empty_dict_returns_0_batch40(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 0


def test_run_inspect_doc_prints_metrics_header_batch40(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_prints_file_path_batch40(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "file:" in captured.out
    assert str(p) in captured.out


def test_run_inspect_doc_prints_document_id_batch40(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"document_id": "abc"}), encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "document_id:" in captured.out
    assert "abc" in captured.out


def test_run_inspect_doc_prints_source_type_batch40(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "pdf"}), encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "type=pdf" in captured.out


def test_run_inspect_doc_prints_elements_count_batch40(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [{"type": "x"}, {"type": "y"}]}), encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "elements=2" in captured.out


def test_run_inspect_doc_prints_chunks_count_batch40(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"chunks": [{"text": "a"}]}), encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "chunks=1" in captured.out


def test_run_inspect_doc_prints_parser_info_batch40(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "parser_name": "fallback",
        "parser_version": "0.1.0",
    }), encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "fallback" in captured.out
    assert "0.1.0" in captured.out


def test_run_inspect_doc_prints_default_unknown_when_missing_batch40(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    # document_id 默认 '?'
    assert "?" in captured.out


def test_run_inspect_doc_does_not_write_file_batch40(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    before = set(tmp_path.iterdir())
    _run_inspect_doc(_make_args(p))
    after = set(tmp_path.iterdir())
    assert before == after


def test_run_inspect_doc_idempotent_batch40(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    out1 = capsys.readouterr().out
    _run_inspect_doc(_make_args(p))
    out2 = capsys.readouterr().out
    assert out1 == out2


def test_run_inspect_doc_with_full_document_batch40(tmp_path, capsys):
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
    assert "chunks=1" in captured.out


def test_run_inspect_doc_with_unicode_text_batch40(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "中文文档",
        "source_type": "pdf",
    }), encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert rc == 0
    assert "中文文档" in captured.out


# ---------- main 第四十批


def test_main_callable_batch40():
    assert callable(main)


def test_main_signature_one_param_optional_batch40():
    sig = inspect.signature(main)
    assert list(sig.parameters.keys()) == ["argv"]


def test_main_argv_default_none_batch40():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_return_annotation_int_batch40():
    sig = inspect.signature(main)
    assert "int" in str(sig.return_annotation)


def test_main_no_args_raises_systemexit_batch40():
    with pytest.raises(SystemExit):
        main([])


def test_main_unknown_command_raises_systemexit_batch40():
    with pytest.raises(SystemExit):
        main(["unknown"])


def test_main_unknown_flag_raises_systemexit_batch40():
    with pytest.raises(SystemExit):
        main(["--unknown-flag"])


def test_main_run_missing_manifest_returns_2_batch40(tmp_path, capsys):
    manifest_path = tmp_path / "missing.json"
    rc = main([
        "run", "--manifest", str(manifest_path),
        "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 2


def test_main_validate_report_missing_file_returns_2_batch40(tmp_path):
    p = tmp_path / "missing.json"
    rc = main(["validate-report", str(p)])
    assert rc == 2


def test_main_inspect_doc_missing_file_returns_2_batch40(tmp_path):
    p = tmp_path / "missing.json"
    rc = main(["inspect-doc", str(p)])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_1_batch40(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_invalid_json_returns_1_batch40(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_validate_report_valid_json_batch40(tmp_path, capsys):
    """合法的最简报告 → 0。"""
    from evaluation import REPORT_VERSION
    p = tmp_path / "r.json"
    p.write_text(json.dumps({
        "report_version": REPORT_VERSION,
        "provenance": {
            "git_commit": "abc",
            "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": REPORT_VERSION,
            "parser_name": "fallback",
            "parser_version": "0.1.0",
            "dependencies": {},
            "max_chars": 800,
            "run_timestamp_iso": "2026-01-01T00:00:00+00:00",
        },
        "devset": {
            "status": "complete",
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": [],
        },
        "summary": {
            "counts": {},
            "success_rates": {},
            "ratio_macro_averages": {},
            "silent_drop_total": None,
        },
        "per_doc": [],
        "expected_failures": [],
    }), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "[OK]" in captured.out


def test_main_validate_report_invalid_schema_returns_1_batch40(tmp_path, capsys):
    """合法 JSON 但不符合 schema → 1。"""
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"wrong": "shape"}), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_run_with_valid_manifest_batch40(tmp_path, capsys):
    """端到端 run 子命令（用 patch 屏蔽真实 pipeline）。"""
    (tmp_path / "foo.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(data), encoding="utf-8")
    out_path = tmp_path / "out.json"

    # 屏蔽真实的 run_evaluation（避免触发 git 等真实环境）
    fake_report = {
        "report_version": "1.1",
        "provenance": {
            "git_commit": "abc",
            "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {},
            "max_chars": 800,
            "run_timestamp_iso": "2026-01-01T00:00:00+00:00",
        },
        "devset": {
            "status": "incomplete",
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": [],
        },
        "summary": {
            "counts": {},
            "success_rates": {},
            "ratio_macro_averages": {},
            "silent_drop_total": None,
        },
        "per_doc": [],
        "expected_failures": [],
    }

    def fake_run(*args, **kwargs):
        # 真实写文件
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(fake_report, f)
        return fake_report

    def fake_validate(*args, **kwargs):
        return None

    with patch("evaluation.cli.run_evaluation", side_effect=fake_run):
        with patch("evaluation.cli.validate_file", side_effect=fake_validate):
            with patch("evaluation.cli.get_git_provenance", return_value={
                "git_commit": "abc", "git_dirty": False,
            }):
                rc = main(["run", "--manifest", str(mpath), "--output", str(out_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "[OK]" in captured.out


def test_main_run_with_load_manifest_failure_returns_1_batch40(tmp_path, capsys):
    """manifest 加载失败（schema 不合）→ 1。"""
    p = tmp_path / "manifest.json"
    p.write_text("{invalid", encoding="utf-8")
    rc = main(["run", "--manifest", str(p), "--output", str(tmp_path / "out.json")])
    assert rc == 1


def test_main_inspect_doc_with_empty_dict_batch40(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


# ---------- module source forbidden tokens 第七十四批


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
def test_module_source_no_forbidden_tokens_batch40(token):
    src = inspect.getsource(cmod)
    assert token not in src


# ---------- module source 字符串精确补强第七十批


def test_module_source_contains_design_doc_batch40():
    src = inspect.getsource(cmod)
    assert "评测 CLI" in src


def test_module_source_contains_future_annotations_batch40():
    src = inspect.getsource(cmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_argparse_import_batch40():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_source_contains_json_import_batch40():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_source_contains_sys_import_batch40():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_source_contains_pathlib_path_import_batch40():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_manifest_import_batch40():
    src = inspect.getsource(cmod)
    assert "from evaluation.manifest import" in src


def test_module_source_contains_report_import_batch40():
    src = inspect.getsource(cmod)
    assert "from evaluation.report import" in src


def test_module_source_contains_runner_import_batch40():
    src = inspect.getsource(cmod)
    assert "from evaluation.runner import" in src


def test_module_source_contains_schema_import_batch40():
    src = inspect.getsource(cmod)
    assert "from evaluation.schema import" in src


def test_module_source_contains_build_parser_function_batch40():
    src = inspect.getsource(cmod)
    assert "def _build_parser(" in src


def test_module_source_contains_main_function_batch40():
    src = inspect.getsource(cmod)
    assert "def main(" in src


def test_module_source_contains_format_metric_function_batch40():
    src = inspect.getsource(cmod)
    assert "def _format_metric(" in src


def test_module_source_contains_run_inspect_doc_function_batch40():
    src = inspect.getsource(cmod)
    assert "def _run_inspect_doc(" in src


def test_module_source_contains_subparsers_batch40():
    src = inspect.getsource(cmod)
    assert "add_subparsers" in src


def test_module_source_contains_required_true_batch40():
    src = inspect.getsource(cmod)
    assert "required=True" in src


def test_module_source_contains_run_subparser_batch40():
    src = inspect.getsource(cmod)
    assert '"run"' in src or "'run'" in src


def test_module_source_contains_validate_report_subparser_batch40():
    src = inspect.getsource(cmod)
    assert '"validate-report"' in src or "'validate-report'" in src


def test_module_source_contains_inspect_doc_subparser_batch40():
    src = inspect.getsource(cmod)
    assert '"inspect-doc"' in src or "'inspect-doc'" in src


def test_module_source_contains_reconfigure_batch40():
    """Windows utf-8 fix。"""
    src = inspect.getsource(cmod)
    assert "reconfigure" in src


def test_module_source_contains_main_guard_batch40():
    src = inspect.getsource(cmod)
    assert 'if __name__ == "__main__"' in src


def test_module_source_contains_system_exit_batch40():
    src = inspect.getsource(cmod)
    assert "SystemExit" in src or "sys.exit" in src


# ---------- module 合理性 第七十批


def test_module_has_main_attribute_batch40():
    assert hasattr(cmod, "main")


def test_module_has_build_parser_attribute_batch40():
    assert hasattr(cmod, "_build_parser")


def test_module_has_format_metric_attribute_batch40():
    assert hasattr(cmod, "_format_metric")


def test_module_has_run_inspect_doc_attribute_batch40():
    assert hasattr(cmod, "_run_inspect_doc")


def test_module_main_callable_batch40():
    assert callable(cmod.main)


def test_module_build_parser_callable_batch40():
    assert callable(cmod._build_parser)


def test_module_format_metric_callable_batch40():
    assert callable(cmod._format_metric)


def test_module_run_inspect_doc_callable_batch40():
    assert callable(cmod._run_inspect_doc)


def test_module_no_class_definitions_batch40():
    src = inspect.getsource(cmod)
    assert "\nclass " not in src


def test_module_has_main_guard_batch40():
    src = inspect.getsource(cmod)
    assert 'if __name__ == "__main__"' in src


def test_module_has_system_exit_call_batch40():
    src = inspect.getsource(cmod)
    assert "SystemExit" in src or "sys.exit" in src


def test_module_no_module_level_code_outside_functions_batch40():
    """AST：顶层只有 import / assignment / function def / if main guard / Expr。"""
    import ast
    src = inspect.getsource(cmod)
    tree = ast.parse(src)
    # 跳过最前面的 docstring 和 reconfigure if block
    for node in tree.body:
        assert isinstance(node, (
            ast.Import, ast.ImportFrom, ast.FunctionDef,
            ast.Assign, ast.Expr, ast.If,
        ))


# ---------- 端到端集成 第七十批


def test_e2e_inspect_doc_minimal_dict_batch40(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 0


def test_e2e_inspect_doc_full_dict_batch40(tmp_path):
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
    assert rc == 0


def test_e2e_idempotent_inspect_doc_batch40(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    out1 = capsys.readouterr().out
    _run_inspect_doc(_make_args(p))
    out2 = capsys.readouterr().out
    assert out1 == out2


def test_e2e_inspect_doc_does_not_write_batch40(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    before = set(tmp_path.iterdir())
    _run_inspect_doc(_make_args(p))
    after = set(tmp_path.iterdir())
    assert before == after


def test_e2e_format_metric_each_value_type_batch40():
    _format_metric("a", {"value": None, "reason": "x"})
    _format_metric("a", {"value": True, "reason": None})
    _format_metric("a", {"value": 0.5, "reason": None})
    _format_metric("a", {"value": {"x": 1}, "reason": None})
    _format_metric("a", {"value": "str", "reason": None})
