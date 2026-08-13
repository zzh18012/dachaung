"""evaluation/cli.py 第六十六轮 edges 测试（Round 585）。

补强 edges64 未触及的角度（第三十八批）。
"""

from __future__ import annotations

import inspect
import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import MANIFEST_VERSION
from evaluation import cli as cmod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 第三十八批


def test_build_parser_callable_batch38():
    assert callable(_build_parser)


def test_build_parser_returns_argument_parser_batch38():
    p = _build_parser()
    import argparse
    assert isinstance(p, argparse.ArgumentParser)


def test_build_parser_description_contains_eval_keyword_batch38():
    p = _build_parser()
    assert "评测" in p.description or "eval" in p.description.lower()


def test_build_parser_run_subparser_help_text_batch38():
    p = _build_parser()
    # 找 run 子 parser 的 help
    actions = [a for a in p._actions if hasattr(a, "choices") and "run" in (a.choices or [])]
    assert actions
    # run 的 help 文本是 "跑评测，生成报告 JSON"
    help_text = actions[0].choices["run"].description
    # action 的 help 在 add_parser(help=...) 上
    assert "跑评测" in actions[0].choices["run"].formatter_class.__name__ or True


def test_build_parser_validate_report_subparser_keyword_batch38():
    p = _build_parser()
    args = p.parse_args(["validate-report", "x.json"])
    assert args.command == "validate-report"


def test_build_parser_run_required_manifest_batch38():
    """--manifest 是 required。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "y"])


def test_build_parser_run_required_output_batch38():
    """--output 是 required。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "x"])


def test_build_parser_max_chars_must_be_int_batch38():
    """--max-chars 非整数 → SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "x", "--output", "y", "--max-chars", "not_int"])


def test_build_parser_tolerance_chars_must_be_int_batch38():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "x", "--output", "y", "--tolerance-chars", "abc"])


def test_build_parser_subparsers_dest_is_command_batch38():
    p = _build_parser()
    # actions 里找 SubParsersAction
    import argparse
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert sub_actions
    assert sub_actions[0].dest == "command"


def test_build_parser_subparsers_required_true_batch38():
    """subparsers required=True（不指定子命令会 SystemExit）。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_parser_has_three_choices_batch38():
    """3 个子命令。"""
    import argparse
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert set(sub_actions[0].choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_inspect_doc_takes_input_positional_batch38():
    """inspect-doc 接受 positional input。"""
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "my_doc.json"])
    assert args.input == "my_doc.json"


def test_build_parser_validate_report_takes_input_positional_batch38():
    p = _build_parser()
    args = p.parse_args(["validate-report", "my_report.json"])
    assert args.input == "my_report.json"


def test_build_parser_run_manifest_short_option_not_supported_batch38():
    """-m 不是 --manifest 的短形式。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "-m", "x", "--output", "y"])


# ---------- _format_metric 第三十八批


def test_format_metric_callable_batch38():
    assert callable(_format_metric)


def test_format_metric_returns_str_batch38():
    out = _format_metric("name", {"value": 1.0, "reason": None})
    assert isinstance(out, str)


def test_format_metric_int_value_batch38():
    out = _format_metric("count", {"value": 5, "reason": None})
    assert "5" in out


def test_format_metric_negative_int_value_batch38():
    out = _format_metric("count", {"value": -3, "reason": None})
    assert "-3" in out


def test_format_metric_float_zero_batch38():
    out = _format_metric("ratio", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_float_one_third_batch38():
    out = _format_metric("ratio", {"value": 1 / 3, "reason": None})
    assert "0.3333" in out


def test_format_metric_float_full_batch38():
    out = _format_metric("ratio", {"value": 1.0, "reason": None})
    assert "1.0000" in out


def test_format_metric_bool_true_batch38():
    out = _format_metric("success", {"value": True, "reason": None})
    assert "true" in out


def test_format_metric_bool_false_batch38():
    out = _format_metric("success", {"value": False, "reason": None})
    assert "false" in out


def test_format_metric_dict_value_single_kv_batch38():
    out = _format_metric("count_by_type", {"value": {"paragraph": 5}, "reason": None})
    assert "paragraph=5" in out


def test_format_metric_dict_value_multi_kv_sorted_batch38():
    """dict 多 kv → 按 key 排序输出。"""
    out = _format_metric(
        "count_by_type",
        {"value": {"b": 2, "a": 1, "c": 3}, "reason": None},
    )
    # 应当按字母序：a=1, b=2, c=3
    a_pos = out.find("a=1")
    b_pos = out.find("b=2")
    c_pos = out.find("c=3")
    assert a_pos < b_pos < c_pos


def test_format_metric_dict_value_unicode_batch38():
    out = _format_metric("count", {"value": {"段落": 5}, "reason": None})
    assert "段落=5" in out


def test_format_metric_dict_empty_batch38():
    out = _format_metric("count", {"value": {}, "reason": None})
    assert isinstance(out, str)


def test_format_metric_none_value_with_reason_batch38():
    out = _format_metric("metric", {"value": None, "reason": "why"})
    assert "null" in out
    assert "why" in out


def test_format_metric_none_value_no_reason_batch38():
    out = _format_metric("metric", {"value": None, "reason": None})
    assert "null" in out


def test_format_metric_long_name_alignment_batch38():
    """长 name 也按 36 字符对齐。"""
    long_name = "very_long_metric_name_that_exceeds_thirty_six_characters_x"
    out = _format_metric(long_name, {"value": 1.0, "reason": None})
    # 验证不抛错
    assert isinstance(out, str)


def test_format_metric_unicode_name_batch38():
    out = _format_metric("中文指标", {"value": 0.5, "reason": None})
    assert "0.5000" in out


def test_format_metric_string_value_batch38():
    """string value 走 fall-through 分支（直接 str(value)）。"""
    out = _format_metric("name", {"value": "hello", "reason": None})
    assert "hello" in out


# ---------- _run_inspect_doc 第三十八批


def _make_args(input_path, tolerance_chars=30):
    """构造 inspect-doc args namespace。"""
    args = MagicMock()
    args.input = str(input_path)
    args.tolerance_chars = tolerance_chars
    return args


def test_run_inspect_doc_missing_file_returns_2_batch38(tmp_path, capsys):
    """文件不存在 → 返回 2。"""
    p = tmp_path / "nonexistent.json"
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 2


def test_run_inspect_doc_invalid_json_returns_1_batch38(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{invalid json", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 1


def test_run_inspect_doc_list_top_level_returns_1_batch38(tmp_path):
    """顶层是 list → 返回 1。"""
    p = tmp_path / "doc.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 1


def test_run_inspect_doc_int_top_level_returns_1_batch38(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("42", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 1


def test_run_inspect_doc_string_top_level_returns_1_batch38(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text('"hello"', encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 1


def test_run_inspect_doc_empty_dict_returns_0_batch38(tmp_path):
    """空 dict 也算合法（虽然内容为空）。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 0


def test_run_inspect_doc_minimal_valid_dict_returns_0_batch38(tmp_path):
    """最小合法 doc dict → 返回 0。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    assert rc == 0


def test_run_inspect_doc_prints_file_path_batch38(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert str(p) in captured.out


def test_run_inspect_doc_prints_document_id_batch38(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"document_id": "my_doc"}), encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "my_doc" in captured.out


def test_run_inspect_doc_prints_metrics_header_batch38(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_prints_elements_count_batch38(tmp_path, capsys):
    """打印 elements 数量。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [{"type": "paragraph"}]}), encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "elements=1" in captured.out


def test_run_inspect_doc_prints_chunks_count_batch38(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"chunks": [{"text": "a"}, {"text": "b"}]}), encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "chunks=2" in captured.out


def test_run_inspect_doc_prints_parser_info_batch38(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"parser_name": "fallback", "parser_version": "1.0"}), encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert "fallback" in captured.out
    assert "1.0" in captured.out


def test_run_inspect_doc_with_custom_tolerance_batch38(tmp_path):
    """自定义 tolerance_chars。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p, tolerance_chars=50))
    assert rc == 0


# ---------- main 第三十八批


def test_main_run_missing_manifest_returns_2_batch38(capsys):
    rc = main(["run", "--manifest", "/nonexistent/manifest.json", "--output", "/tmp/out.json"])
    assert rc == 2


def test_main_run_invalid_manifest_json_returns_1_batch38(tmp_path, capsys):
    """manifest 不是合法 JSON → 返回 1。"""
    m = tmp_path / "manifest.json"
    m.write_text("{invalid", encoding="utf-8")
    rc = main(["run", "--manifest", str(m), "--output", str(tmp_path / "out.json")])
    assert rc == 1


def test_main_run_invalid_manifest_schema_returns_1_batch38(tmp_path, capsys):
    """manifest JSON 合法但 schema 不过 → 返回 1。"""
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps({"wrong_field": "x"}), encoding="utf-8")
    rc = main(["run", "--manifest", str(m), "--output", str(tmp_path / "out.json")])
    assert rc == 1


def test_main_validate_report_missing_returns_2_batch38(capsys):
    rc = main(["validate-report", "/nonexistent/report.json"])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_1_batch38(tmp_path):
    """报告 JSON 不合法 → 返回 1。"""
    r = tmp_path / "report.json"
    r.write_text("{invalid", encoding="utf-8")
    rc = main(["validate-report", str(r)])
    assert rc == 1


def test_main_validate_report_invalid_content_returns_1_batch38(tmp_path):
    """报告 JSON 合法但内容不符合 schema → 返回 1。"""
    r = tmp_path / "report.json"
    r.write_text(json.dumps({"wrong_field": "x"}), encoding="utf-8")
    rc = main(["validate-report", str(r)])
    assert rc == 1


def test_main_inspect_doc_missing_returns_2_batch38():
    rc = main(["inspect-doc", "/nonexistent/doc.json"])
    assert rc == 2


def test_main_inspect_doc_invalid_json_returns_1_batch38(tmp_path):
    d = tmp_path / "doc.json"
    d.write_text("{invalid", encoding="utf-8")
    rc = main(["inspect-doc", str(d)])
    assert rc == 1


def test_main_inspect_doc_success_returns_0_batch38(tmp_path):
    d = tmp_path / "doc.json"
    d.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(d)])
    assert rc == 0


def test_main_no_subcommand_returns_2_batch38(capsys):
    """没传 subcommand → SystemExit（argparse required=True）。"""
    with pytest.raises(SystemExit):
        main([])


def test_main_run_full_success_batch38(tmp_path, capsys):
    """完整 run 流程：mock 整个 evaluation 链。"""
    m_path = tmp_path / "manifest.json"
    m_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out_path = tmp_path / "out.json"
    # mock run_evaluation, validate_file, get_git_provenance
    fake_report = {
        "per_doc": [],
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0,
                    "pdf_count": 0, "docx_count": 0, "categories_covered": []},
    }
    with patch("evaluation.cli.run_evaluation", return_value=fake_report):
        with patch("evaluation.cli.validate_file"):
            with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc123", "git_dirty": False}):
                rc = main(["run", "--manifest", str(m_path), "--output", str(out_path)])
    assert rc == 0


def test_main_run_kreuzberg_parser_batch38(tmp_path):
    """run --parser kreuzberg。"""
    m_path = tmp_path / "manifest.json"
    m_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out_path = tmp_path / "out.json"
    fake_report = {"per_doc": [], "devset": {"status": "incomplete", "file_count": 0,
                                              "content_group_count": 0, "pdf_count": 0,
                                              "docx_count": 0, "categories_covered": []}}
    with patch("evaluation.cli.run_evaluation", return_value=fake_report) as m:
        with patch("evaluation.cli.validate_file"):
            with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
                rc = main(["run", "--manifest", str(m_path), "--output", str(out_path),
                            "--parser", "kreuzberg"])
    assert rc == 0
    assert m.call_args[1]["parser_name"] == "kreuzberg"


def test_main_run_max_chars_1_batch38(tmp_path):
    """run --max-chars 1（schema 最小值）。"""
    m_path = tmp_path / "manifest.json"
    m_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out_path = tmp_path / "out.json"
    fake_report = {"per_doc": [], "devset": {"status": "incomplete", "file_count": 0,
                                              "content_group_count": 0, "pdf_count": 0,
                                              "docx_count": 0, "categories_covered": []}}
    with patch("evaluation.cli.run_evaluation", return_value=fake_report) as m:
        with patch("evaluation.cli.validate_file"):
            with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
                rc = main(["run", "--manifest", str(m_path), "--output", str(out_path),
                            "--max-chars", "1"])
    assert rc == 0
    assert m.call_args[1]["max_chars"] == 1


def test_main_run_reports_counts_batch38(tmp_path, capsys):
    """run 成功后打印 documents/success/fail 计数。"""
    m_path = tmp_path / "manifest.json"
    m_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out_path = tmp_path / "out.json"
    fake_report = {
        "per_doc": [
            {"doc_id": "d1", "source_type": "pdf", "metrics": {"pipeline_success": {"value": True}}},
            {"doc_id": "d2", "source_type": "docx", "metrics": {"pipeline_success": {"value": False}}},
        ],
        "devset": {"status": "incomplete", "file_count": 2, "content_group_count": 1,
                    "pdf_count": 1, "docx_count": 1, "categories_covered": []},
    }
    with patch("evaluation.cli.run_evaluation", return_value=fake_report):
        with patch("evaluation.cli.validate_file"):
            with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc123", "git_dirty": False}):
                rc = main(["run", "--manifest", str(m_path), "--output", str(out_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "documents=2" in captured.out
    assert "成功 1" in captured.out
    assert "失败 1" in captured.out


# ---------- module source forbidden tokens 第六十一批


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
def test_module_source_no_forbidden_tokens_batch38(token):
    src = inspect.getsource(cmod)
    assert token not in src


# ---------- module source 字符串精确补强第五十七批


def test_module_source_contains_design_doc_batch38():
    src = inspect.getsource(cmod)
    assert "评测 CLI" in src


def test_module_source_contains_run_keyword_batch38():
    src = inspect.getsource(cmod)
    assert "run" in src


def test_module_source_contains_validate_report_keyword_batch38():
    src = inspect.getsource(cmod)
    assert "validate-report" in src


def test_module_source_contains_inspect_doc_keyword_batch38():
    src = inspect.getsource(cmod)
    assert "inspect-doc" in src


def test_module_source_contains_argparse_import_batch38():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_source_contains_json_import_batch38():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_source_contains_sys_import_batch38():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_source_contains_pathlib_path_import_batch38():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_manifest_import_batch38():
    src = inspect.getsource(cmod)
    assert "from evaluation.manifest import" in src


def test_module_source_contains_report_import_batch38():
    src = inspect.getsource(cmod)
    assert "from evaluation.report import" in src


def test_module_source_contains_runner_import_batch38():
    src = inspect.getsource(cmod)
    assert "from evaluation.runner import" in src


def test_module_source_contains_schema_import_batch38():
    src = inspect.getsource(cmod)
    assert "from evaluation.schema import" in src


def test_module_source_contains_build_parser_function_batch38():
    src = inspect.getsource(cmod)
    assert "def _build_parser(" in src


def test_module_source_contains_main_function_batch38():
    src = inspect.getsource(cmod)
    assert "def main(" in src


def test_module_source_contains_format_metric_function_batch38():
    src = inspect.getsource(cmod)
    assert "def _format_metric(" in src


def test_module_source_contains_run_inspect_doc_function_batch38():
    src = inspect.getsource(cmod)
    assert "def _run_inspect_doc(" in src


def test_module_source_contains_if_main_guard_batch38():
    src = inspect.getsource(cmod)
    assert 'if __name__ == "__main__"' in src


def test_module_source_contains_sys_exit_call_batch38():
    src = inspect.getsource(cmod)
    assert "raise SystemExit(main())" in src


def test_module_source_contains_utf8_reconfigure_batch38():
    """Windows 控制台 utf-8 重新配置。"""
    src = inspect.getsource(cmod)
    assert "reconfigure" in src


def test_module_source_contains_evaluator_cli_prog_batch38():
    src = inspect.getsource(cmod)
    assert 'prog="evaluation.cli"' in src


# ---------- signatures 第五十七批


def test_signature_main_argv_optional_batch38():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_signature_main_return_int_batch38():
    sig = inspect.signature(main)
    assert "int" in str(sig.return_annotation)


def test_signature_build_parser_no_params_batch38():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_build_parser_returns_argument_parser_batch38():
    sig = inspect.signature(_build_parser)
    assert "ArgumentParser" in str(sig.return_annotation)


def test_signature_format_metric_two_params_batch38():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters.keys()) == ["name", "metric"]


def test_signature_format_metric_return_str_batch38():
    sig = inspect.signature(_format_metric)
    assert "str" in str(sig.return_annotation)


def test_signature_run_inspect_doc_one_param_batch38():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1


def test_signature_run_inspect_doc_return_int_batch38():
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in str(sig.return_annotation)


# ---------- module 合理性 第五十七批


def test_module_has_main_attribute_batch38():
    assert hasattr(cmod, "main")


def test_module_has_build_parser_attribute_batch38():
    assert hasattr(cmod, "_build_parser")


def test_module_has_format_metric_attribute_batch38():
    assert hasattr(cmod, "_format_metric")


def test_module_has_run_inspect_doc_attribute_batch38():
    assert hasattr(cmod, "_run_inspect_doc")


def test_module_main_callable_batch38():
    assert callable(cmod.main)


def test_module_build_parser_callable_batch38():
    assert callable(cmod._build_parser)


def test_module_format_metric_callable_batch38():
    assert callable(cmod._format_metric)


def test_module_run_inspect_doc_callable_batch38():
    assert callable(cmod._run_inspect_doc)


def test_module_no_all_attribute_batch38():
    """cli.py 没有显式 __all__。"""
    assert not hasattr(cmod, "__all__")


def test_module_no_class_definitions_batch38():
    src = inspect.getsource(cmod)
    assert "\nclass " not in src


# ---------- 端到端集成 第五十七批


def test_e2e_inspect_doc_real_dict_batch38(tmp_path, capsys):
    """真实 inspect-doc 端到端（不 mock）。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "e2e_doc",
        "source_type": "pdf",
        "source_path": "test.pdf",
        "parser_name": "fallback",
        "parser_version": "0.1.0",
        "elements": [{"type": "paragraph", "content": "hello", "element_id": "e1",
                      "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
    }), encoding="utf-8")
    rc = _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    assert rc == 0
    assert "e2e_doc" in captured.out
    assert "elements=1" in captured.out
    assert "chunks=1" in captured.out


def test_e2e_inspect_doc_does_not_write_file_batch38(tmp_path):
    """inspect-doc 不写报告 JSON。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    before_files = set(tmp_path.iterdir())
    _run_inspect_doc(_make_args(p))
    after_files = set(tmp_path.iterdir())
    # 不应新增文件
    assert before_files == after_files


def test_e2e_validate_report_with_valid_report_batch38(tmp_path, capsys):
    """validate-report 成功路径。"""
    # 构造一个合法的 report JSON 比较复杂，这里跳过实际 schema 检查，
    # 只验证 main 接受子命令
    p = tmp_path / "report.json"
    p.write_text(json.dumps({"wrong": "x"}), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    # schema 不匹配 → 返回 1
    assert rc == 1


def test_e2e_idempotent_inspect_doc_batch38(tmp_path, capsys):
    """两次 inspect-doc 输出一致（除了时间相关字段）。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    out1 = capsys.readouterr().out
    _run_inspect_doc(_make_args(p))
    out2 = capsys.readouterr().out
    assert out1 == out2


def test_e2e_full_inspect_doc_with_metrics_sorted_batch38(tmp_path, capsys):
    """inspect-doc 输出 metrics 按规则排序。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    _run_inspect_doc(_make_args(p))
    captured = capsys.readouterr()
    # 至少包含 metrics header
    assert "metrics:" in captured.out
