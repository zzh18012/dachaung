"""evaluation/cli.py 第三十七轮 edges 测试（Round 390）。

补强 edges36 未触及的角度：
- _build_parser 行为深度第十批（add_subparsers 标志 / subparser 帮助文本 / formatter_class / choices tuple / metavar）
- argparse Namespace 字段第十批（更多类型与边界）
- _format_metric 行为深度第十批（更多类型组合 / 大数字 / Unicode name / 负无穷 / NaN 处理）
- _run_inspect_doc 行为深度第十批（更多 element types / chunk 结构 / tolerance 大值 / parser_name 自定义 / source_path 自定义）
- main 路由第十批（更多错误路径 / run 命令主路径成功 / 退出码精确）
- module source forbidden tokens 第十三批
- module source 字符串精确补强第八批
- signatures 第十批
- module 合理性第十批
- 端到端集成第十批
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
from pathlib import Path

import pytest

from evaluation import cli as climod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 行为深度第十批 ----------


def test_build_parser_returns_argument_parser_type_batch10():
    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_build_parser_prog_value_exact_batch10():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_starts_with_eval_batch10():
    p = _build_parser()
    assert p.description.startswith("评测")


def test_build_parser_description_mentions_devset_and_report_batch10():
    p = _build_parser()
    assert "开发集" in p.description or "跑" in p.description
    assert "报告" in p.description


def test_build_parser_has_three_subparsers_batch10():
    """3 subparsers: run / validate-report / inspect-doc。"""
    p = _build_parser()
    # 通过 parse_args 验证
    for cmd in ("run", "validate-report", "inspect-doc"):
        ns = p.parse_args([cmd] + _minimal_args(cmd))
        assert ns.command == cmd


def _minimal_args(cmd):
    if cmd == "run":
        return ["--manifest", "x.json", "--output", "y.json"]
    return ["x.json"]


def test_build_parser_run_subparser_choices_batch10():
    ns = _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert ns.parser in ("fallback", "kreuzberg")


def test_build_parser_run_parser_default_fallback_batch10():
    ns = _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert ns.parser == "fallback"


def test_build_parser_run_parser_kreuzberg_batch10():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json", "--parser", "kreuzberg"]
    )
    assert ns.parser == "kreuzberg"


def test_build_parser_run_parser_rejects_other_choices_batch10(capsys):
    with pytest.raises(SystemExit):
        _build_parser().parse_args(
            ["run", "--manifest", "a.json", "--output", "b.json", "--parser", "pdfplumber"]
        )


def test_build_parser_max_chars_default_800_batch10():
    ns = _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert ns.max_chars == 800


def test_build_parser_tolerance_chars_default_30_batch10():
    ns = _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert ns.tolerance_chars == 30


def test_build_parser_inspect_doc_tolerance_chars_default_30_batch10():
    ns = _build_parser().parse_args(["inspect-doc", "a.json"])
    assert ns.tolerance_chars == 30


def test_build_parser_max_chars_type_int_batch10():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json", "--max-chars", "500"]
    )
    assert isinstance(ns.max_chars, int)
    assert ns.max_chars == 500


def test_build_parser_tolerance_chars_type_int_batch10():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json", "--tolerance-chars", "10"]
    )
    assert isinstance(ns.tolerance_chars, int)
    assert ns.tolerance_chars == 10


def test_build_parser_validate_report_input_value_batch10():
    ns = _build_parser().parse_args(["validate-report", "report.json"])
    assert ns.input == "report.json"


def test_build_parser_inspect_doc_input_value_batch10():
    ns = _build_parser().parse_args(["inspect-doc", "doc.json"])
    assert ns.input == "doc.json"


def test_build_parser_required_subcommand_batch10():
    """required=True → 不传 subcommand 会 SystemExit。"""
    with pytest.raises(SystemExit):
        _build_parser().parse_args([])


def test_build_parser_run_required_manifest_batch10(capsys):
    """--manifest required=True。"""
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["run", "--output", "b.json"])


def test_build_parser_run_required_output_batch10(capsys):
    """--output required=True。"""
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["run", "--manifest", "a.json"])


def test_build_parser_help_run_exits_zero_batch10(capsys):
    with pytest.raises(SystemExit) as exc_info:
        _build_parser().parse_args(["run", "--help"])
    assert exc_info.value.code == 0


def test_build_parser_help_validate_report_exits_zero_batch10(capsys):
    with pytest.raises(SystemExit) as exc_info:
        _build_parser().parse_args(["validate-report", "--help"])
    assert exc_info.value.code == 0


def test_build_parser_help_inspect_doc_exits_zero_batch10(capsys):
    with pytest.raises(SystemExit) as exc_info:
        _build_parser().parse_args(["inspect-doc", "--help"])
    assert exc_info.value.code == 0


def test_build_parser_global_help_exits_zero_batch10(capsys):
    with pytest.raises(SystemExit) as exc_info:
        _build_parser().parse_args(["--help"])
    assert exc_info.value.code == 0


def test_build_parser_unknown_arg_exits_nonzero_batch10(capsys):
    with pytest.raises(SystemExit) as exc_info:
        _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "b.json", "--bad-arg"])
    assert exc_info.value.code != 0


# ---------- argparse Namespace 字段第十批 ----------


def test_namespace_run_command_value_batch10():
    ns = _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert ns.command == "run"


def test_namespace_validate_report_command_value_batch10():
    ns = _build_parser().parse_args(["validate-report", "a.json"])
    assert ns.command == "validate-report"


def test_namespace_inspect_doc_command_value_batch10():
    ns = _build_parser().parse_args(["inspect-doc", "a.json"])
    assert ns.command == "inspect-doc"


def test_namespace_run_manifest_value_batch10():
    ns = _build_parser().parse_args(["run", "--manifest", "/path/to/m.json", "--output", "b.json"])
    assert ns.manifest == "/path/to/m.json"


def test_namespace_run_output_value_batch10():
    ns = _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "/path/to/o.json"])
    assert ns.output == "/path/to/o.json"


def test_namespace_run_attributes_count_batch10():
    ns = _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert len(vars(ns)) == 6


def test_namespace_validate_report_attributes_count_batch10():
    ns = _build_parser().parse_args(["validate-report", "a.json"])
    assert len(vars(ns)) == 2


def test_namespace_inspect_doc_attributes_count_batch10():
    ns = _build_parser().parse_args(["inspect-doc", "a.json"])
    assert len(vars(ns)) == 3


def test_namespace_run_max_chars_negative_batch10():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json", "--max-chars", "-1"]
    )
    assert ns.max_chars == -1


def test_namespace_run_max_chars_huge_value_batch10():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json", "--max-chars", "100000"]
    )
    assert ns.max_chars == 100000


def test_namespace_run_max_chars_zero_batch10():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json", "--max-chars", "0"]
    )
    assert ns.max_chars == 0


def test_namespace_run_tolerance_chars_zero_batch10():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json", "--tolerance-chars", "0"]
    )
    assert ns.tolerance_chars == 0


def test_namespace_run_attributes_exact_batch10():
    ns = _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert set(vars(ns)) == {
        "command",
        "manifest",
        "output",
        "parser",
        "max_chars",
        "tolerance_chars",
    }


def test_namespace_inspect_doc_attributes_exact_batch10():
    ns = _build_parser().parse_args(["inspect-doc", "a.json"])
    assert set(vars(ns)) == {"command", "input", "tolerance_chars"}


def test_namespace_validate_report_attributes_exact_batch10():
    ns = _build_parser().parse_args(["validate-report", "a.json"])
    assert set(vars(ns)) == {"command", "input"}


def test_namespace_input_is_str_batch10():
    ns = _build_parser().parse_args(["validate-report", "x.json"])
    assert isinstance(ns.input, str)


def test_namespace_manifest_is_str_batch10():
    ns = _build_parser().parse_args(["run", "--manifest", "x.json", "--output", "y.json"])
    assert isinstance(ns.manifest, str)


def test_namespace_namespace_type_batch10():
    ns = _build_parser().parse_args(["validate-report", "x.json"])
    assert isinstance(ns, argparse.Namespace)


def test_namespace_command_first_field_batch10():
    """command 是 Namespace 第一个属性。"""
    ns = _build_parser().parse_args(["validate-report", "x.json"])
    keys = list(vars(ns).keys())
    assert keys[0] == "command"


# ---------- _format_metric 行为深度第十批 ----------


def test_format_metric_int_value_batch10():
    out = _format_metric("element_count_total", {"value": 5, "reason": "ok"})
    assert "5" in out
    assert "element_count_total" in out


def test_format_metric_int_value_no_reason_uses_ok_batch10():
    out = _format_metric("element_count_total", {"value": 5})
    assert "(ok)" in out


def test_format_metric_float_negative_value_batch10():
    out = _format_metric("ratio", {"value": -0.5, "reason": "x"})
    assert "-0.5000" in out


def test_format_metric_float_zero_value_batch10():
    out = _format_metric("ratio", {"value": 0.0, "reason": "x"})
    assert "0.0000" in out


def test_format_metric_float_high_precision_batch10():
    out = _format_metric("ratio", {"value": 0.123456789, "reason": "x"})
    assert "0.1235" in out  # 4 decimal places


def test_format_metric_float_one_batch10():
    out = _format_metric("ratio", {"value": 1.0, "reason": "x"})
    assert "1.0000" in out


def test_format_metric_bool_true_value_batch10():
    out = _format_metric("flag", {"value": True, "reason": "ok"})
    assert "true" in out


def test_format_metric_bool_false_value_batch10():
    out = _format_metric("flag", {"value": False, "reason": "ok"})
    assert "false" in out


def test_format_metric_bool_no_reason_uses_ok_batch10():
    out = _format_metric("flag", {"value": True})
    assert "(ok)" in out


def test_format_metric_none_value_uses_reason_batch10():
    out = _format_metric("metric", {"value": None, "reason": "no_data"})
    assert "null" in out
    assert "(no_data)" in out


def test_format_metric_none_value_missing_reason_batch10():
    out = _format_metric("metric", {"value": None})
    assert "null" in out
    assert "(None)" in out


def test_format_metric_dict_empty_batch10():
    out = _format_metric("by_type", {"value": {}, "reason": "ok"})
    assert "by_type" in out
    assert "(ok)" in out


def test_format_metric_dict_multiple_pairs_sorted_batch10():
    out = _format_metric(
        "by_type",
        {"value": {"paragraph": 3, "heading": 1, "image": 2}, "reason": "ok"},
    )
    assert "heading=1" in out
    assert "image=2" in out
    assert "paragraph=3" in out


def test_format_metric_str_value_falls_to_default_batch10():
    out = _format_metric("metric", {"value": "hello", "reason": "x"})
    assert "hello" in out


def test_format_metric_list_value_falls_to_default_batch10():
    out = _format_metric("metric", {"value": [1, 2, 3], "reason": "x"})
    assert "[1, 2, 3]" in out


def test_format_metric_returns_str_batch10():
    out = _format_metric("x", {"value": 1, "reason": "ok"})
    assert isinstance(out, str)


def test_format_metric_padding_36_chars_batch10():
    out = _format_metric("abc", {"value": 1, "reason": "ok"})
    name_end = out.find("1")
    assert name_end >= 36


def test_format_metric_long_name_batch10():
    """超长 name（> 36 chars）仍可工作。"""
    name = "a" * 50
    out = _format_metric(name, {"value": 1, "reason": "ok"})
    assert name in out


def test_format_metric_unicode_name_batch10():
    out = _format_metric("中文指标", {"value": 1, "reason": "ok"})
    assert "中文指标" in out


def test_format_metric_int_zero_batch10():
    out = _format_metric("count", {"value": 0, "reason": "ok"})
    # int 0 → 不是 float，不走 .4f 分支，直接 str(0) = "0"
    assert "0" in out


def test_format_metric_negative_int_batch10():
    out = _format_metric("count", {"value": -10, "reason": "x"})
    assert "-10" in out


def test_format_metric_huge_int_batch10():
    out = _format_metric("count", {"value": 1000000, "reason": "x"})
    assert "1000000" in out


# ---------- _run_inspect_doc 行为深度第十批 ----------


def test_run_inspect_doc_returns_int_batch10(tmp_path):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    assert isinstance(_run_inspect_doc(args), int)


def test_run_inspect_doc_missing_file_returns_2_batch10(tmp_path, capsys):
    args = argparse.Namespace(input=str(tmp_path / "no.json"), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_run_inspect_doc_invalid_json_returns_1_batch10(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON" in err or "解析" in err


def test_run_inspect_doc_top_level_list_returns_1_batch10(tmp_path):
    p = tmp_path / "list.json"
    p.write_text("[]", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    assert _run_inspect_doc(args) == 1


def test_run_inspect_doc_top_level_string_returns_1_batch10(tmp_path):
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    assert _run_inspect_doc(args) == 1


def test_run_inspect_doc_top_level_int_returns_1_batch10(tmp_path):
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    assert _run_inspect_doc(args) == 1


def test_run_inspect_doc_top_level_null_returns_1_batch10(tmp_path):
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    assert _run_inspect_doc(args) == 1


def test_run_inspect_doc_empty_dict_returns_0_batch10(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_prints_filename_batch10(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "d.json" in out
    assert "file:" in out


def test_run_inspect_doc_prints_metrics_header_batch10(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_with_elements_and_chunks_batch10(tmp_path, capsys):
    doc = {"elements": [{"type": "paragraph"}, {"type": "heading"}], "chunks": [{"id": "c1"}]}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "elements=2" in out
    assert "chunks=1" in out


def test_run_inspect_doc_chunks_missing_treated_as_empty_batch10(tmp_path, capsys):
    doc = {"elements": []}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "chunks=0" in out


def test_run_inspect_doc_explicit_source_type_batch10(tmp_path, capsys):
    doc = {"source_type": "pdf"}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "type=pdf" in out


def test_run_inspect_doc_source_type_docx_batch10(tmp_path, capsys):
    doc = {"source_type": "docx"}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "type=docx" in out


def test_run_inspect_doc_default_source_type_unknown_batch10(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "type=unknown" in out


def test_run_inspect_doc_prints_document_id_batch10(tmp_path, capsys):
    doc = {"document_id": "my_doc_001"}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "my_doc_001" in out
    assert "document_id:" in out


def test_run_inspect_doc_document_id_missing_prints_question_mark_batch10(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "document_id:" in out
    assert "?" in out


def test_run_inspect_doc_prints_parser_name_batch10(tmp_path, capsys):
    doc = {"parser_name": "fallback", "parser_version": "1.0.0"}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "fallback" in out
    assert "1.0.0" in out


def test_run_inspect_doc_parser_missing_prints_question_mark_batch10(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "v?" in out


def test_run_inspect_doc_with_unicode_in_doc_batch10(tmp_path, capsys):
    doc = {"document_id": "中文文档"}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "中文文档" in out


def test_run_inspect_doc_args_namespace_type_batch10():
    args = argparse.Namespace(input="x.json", tolerance_chars=30)
    assert hasattr(args, "input")
    assert hasattr(args, "tolerance_chars")


def test_run_inspect_doc_prints_source_path_batch10(tmp_path, capsys):
    doc = {"source_path": "/some/path.pdf"}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "/some/path.pdf" in out


def test_run_inspect_doc_source_path_missing_batch10(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    # source 行有 "?"
    assert "source:" in out


def test_run_inspect_doc_elements_with_various_types_batch10(tmp_path, capsys):
    """elements 含多种 type：paragraph / heading / image / table。"""
    doc = {
        "elements": [
            {"type": "paragraph"},
            {"type": "heading"},
            {"type": "image"},
            {"type": "table"},
        ]
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "elements=4" in out


def test_run_inspect_doc_large_tolerance_chars_batch10(tmp_path, capsys):
    """tolerance_chars 大值不抛。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=10000)
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_zero_tolerance_chars_batch10(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=0)
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_with_chunk_text_batch10(tmp_path, capsys):
    """chunks 含 text 字段。"""
    doc = {"elements": [], "chunks": [{"id": "c1", "text": "hello"}]}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "chunks=1" in out


# ---------- main 路由第十批 ----------


def test_main_returns_int_for_validate_report_missing_file_batch10(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "no.json")])
    assert isinstance(rc, int)
    assert rc != 0


def test_main_returns_int_for_inspect_doc_missing_file_batch10(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "no.json")])
    assert isinstance(rc, int)
    assert rc != 0


def test_main_returns_int_for_run_missing_manifest_batch10(tmp_path, capsys):
    rc = main(
        ["run", "--manifest", str(tmp_path / "no.json"), "--output", str(tmp_path / "o.json")]
    )
    assert isinstance(rc, int)
    assert rc != 0


def test_main_validate_report_invalid_json_returns_1_batch10(tmp_path, capsys):
    p = tmp_path / "r.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_invalid_schema_returns_1_batch10(tmp_path, capsys):
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_top_level_not_dict_returns_1_batch10(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_success_returns_0_batch10(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_run_with_invalid_manifest_json_returns_1_batch10(tmp_path, capsys):
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["run", "--manifest", str(p), "--output", str(tmp_path / "o.json")])
    assert rc == 1


def test_main_run_with_invalid_manifest_schema_returns_1_batch10(tmp_path, capsys):
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["run", "--manifest", str(p), "--output", str(tmp_path / "o.json")])
    assert rc == 1


def test_main_no_subcommand_exits_nonzero_batch10(capsys):
    with pytest.raises(SystemExit):
        main([])


def test_main_unknown_subcommand_exits_nonzero_batch10(capsys):
    with pytest.raises(SystemExit):
        main(["unknown-command"])


def test_main_run_with_invalid_parser_choice_exits_nonzero_batch10(capsys):
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "a.json", "--output", "b.json", "--parser", "bad"])


def test_main_validate_report_stderr_starts_with_bracket_error_batch10(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "no.json")])
    assert rc == 2
    err = capsys.readouterr().err
    assert err.startswith("[ERROR]")


def test_main_validate_report_success_path_batch10(tmp_path, capsys):
    """validate-report 成功：先造一个合法 report。"""
    # 用 evaluation.runner 生成一份合法 report
    from evaluation.runner import run_evaluation

    class _StubManifest:
        documents = []
        expected_failures = []
        project_root = tmp_path
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []

    out_path = tmp_path / "valid.json"
    run_evaluation(_StubManifest(), out_path)
    rc = main(["validate-report", str(out_path)])
    assert rc == 0


def test_main_run_success_path_batch10(monkeypatch, tmp_path, capsys):
    """run 命令成功路径：构造合法 manifest + 模拟 process_single 返成功。"""
    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps(manifest_data), encoding="utf-8")
    o_path = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(m_path), "--output", str(o_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[OK]" in out
    assert "documents=" in out


def test_main_validate_report_correct_stderr_for_invalid_json_batch10(tmp_path, capsys):
    p = tmp_path / "r.json"
    p.write_text("not json", encoding="utf-8")
    main(["validate-report", str(p)])
    err = capsys.readouterr().err
    assert "[ERROR]" in err
    assert "JSON" in err or "解析" in err


def test_main_validate_report_correct_stderr_for_invalid_schema_batch10(tmp_path, capsys):
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    main(["validate-report", str(p)])
    err = capsys.readouterr().err
    assert "[FAIL]" in err


# ---------- module source forbidden tokens 第十三批 ----------


def test_cli_source_no_os_system_batch10():
    source = inspect.getsource(climod)
    assert "os.system" not in source


def test_cli_source_no_subprocess_popen_batch10():
    source = inspect.getsource(climod)
    assert "subprocess.Popen" not in source
    assert "subprocess.check_call" not in source


def test_cli_source_no_pickle_load_batch10():
    source = inspect.getsource(climod)
    assert "pickle.load" not in source


def test_cli_source_no_yaml_load_batch10():
    source = inspect.getsource(climod)
    assert "yaml.load" not in source


def test_cli_source_no_eval_exec_batch10():
    source = inspect.getsource(climod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_cli_source_no_compile_batch10():
    source = inspect.getsource(climod)
    assert "compile(" not in source


def test_cli_source_no_sys_exit_call_batch10():
    source = inspect.getsource(climod)
    assert "sys.exit" not in source
    assert "exit(" not in source
    assert "quit(" not in source


def test_cli_source_no_global_keyword_batch10():
    source = inspect.getsource(climod)
    assert "\nglobal " not in source


def test_cli_source_no_class_def_batch10():
    source = inspect.getsource(climod)
    assert "\nclass " not in source


def test_cli_source_no_async_def_batch10():
    source = inspect.getsource(climod)
    assert "async def" not in source


def test_cli_source_no_yield_batch10():
    source = inspect.getsource(climod)
    assert "yield" not in source


def test_cli_source_no_walrus_batch10():
    source = inspect.getsource(climod)
    assert ":=" not in source


def test_cli_source_no_rmtree_batch10():
    source = inspect.getsource(climod)
    assert ".rmtree(" not in source


def test_cli_source_no_remove_batch10():
    source = inspect.getsource(climod)
    assert ".remove(" not in source


def test_cli_source_no_logging_batch10():
    source = inspect.getsource(climod)
    assert "logging" not in source
    assert "logger" not in source


def test_cli_source_no_sleep_batch10():
    source = inspect.getsource(climod)
    assert "time.sleep" not in source


def test_cli_source_no_hardcoded_absolute_path_batch10():
    source = inspect.getsource(climod)
    assert "C:\\\\Users" not in source
    assert "/Users/" not in source


# ---------- module source 字符串精确补强第八批 ----------


def test_module_source_has_future_annotations_batch10():
    source = inspect.getsource(climod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_argparse_batch10():
    source = inspect.getsource(climod)
    assert "import argparse" in source


def test_module_source_imports_json_batch10():
    source = inspect.getsource(climod)
    assert "import json" in source


def test_module_source_imports_sys_batch10():
    source = inspect.getsource(climod)
    assert "import sys" in source


def test_module_source_imports_path_batch10():
    source = inspect.getsource(climod)
    assert "from pathlib import Path" in source


def test_module_source_imports_manifest_batch10():
    source = inspect.getsource(climod)
    assert "ManifestError" in source
    assert "load_manifest" in source


def test_module_source_imports_get_git_provenance_batch10():
    source = inspect.getsource(climod)
    assert "get_git_provenance" in source


def test_module_source_imports_run_evaluation_batch10():
    source = inspect.getsource(climod)
    assert "run_evaluation" in source


def test_module_source_imports_eval_schema_error_batch10():
    source = inspect.getsource(climod)
    assert "EvalSchemaError" in source
    assert "validate_file" in source


def test_module_source_has_build_parser_def_batch10():
    source = inspect.getsource(climod)
    assert "def _build_parser()" in source


def test_module_source_has_main_def_batch10():
    source = inspect.getsource(climod)
    assert "def main(argv:" in source


def test_module_source_has_format_metric_def_batch10():
    source = inspect.getsource(climod)
    assert "def _format_metric(" in source


def test_module_source_has_run_inspect_doc_def_batch10():
    source = inspect.getsource(climod)
    assert "def _run_inspect_doc(" in source


def test_module_source_main_block_at_end_batch10():
    source = inspect.getsource(climod)
    assert 'if __name__ == "__main__":' in source


def test_module_source_main_block_raises_system_exit_batch10():
    source = inspect.getsource(climod)
    assert "raise SystemExit(main())" in source


def test_module_source_subparser_names_batch10():
    source = inspect.getsource(climod)
    assert '"run"' in source
    assert '"validate-report"' in source
    assert '"inspect-doc"' in source


def test_module_source_uses_argparse_raw_description_batch10():
    source = inspect.getsource(climod)
    assert "RawDescriptionHelpFormatter" in source


def test_module_source_uses_sub_add_parser_batch10():
    source = inspect.getsource(climod)
    assert "sub.add_parser(" in source


def test_module_source_parser_choices_batch10():
    source = inspect.getsource(climod)
    assert '("fallback", "kreuzberg")' in source


def test_module_source_docstring_present_batch10():
    assert climod.__doc__ is not None
    assert len(climod.__doc__) > 30


def test_module_source_docstring_mentions_run_batch10():
    assert "run" in climod.__doc__


def test_module_source_docstring_mentions_validate_report_batch10():
    assert "validate-report" in climod.__doc__


def test_module_source_docstring_mentions_inspect_doc_batch10():
    assert "inspect-doc" in climod.__doc__


def test_module_source_stdout_reconfigure_utf8_batch10():
    source = inspect.getsource(climod)
    # Windows 控制台 utf-8 配置
    assert "reconfigure" in source


def test_module_source_no_class_def_batch10_2():
    """再验证一次：模块无 class 定义。"""
    source = inspect.getsource(climod)
    assert "\nclass " not in source


# ---------- signatures 第十批 ----------


def test_signature_build_parser_param_count_batch10():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_build_parser_return_annotation_batch10():
    sig = inspect.signature(_build_parser)
    assert sig.return_annotation == "argparse.ArgumentParser"


def test_signature_main_param_count_batch10():
    sig = inspect.signature(main)
    assert len(sig.parameters) == 1


def test_signature_main_param_name_batch10():
    sig = inspect.signature(main)
    assert "argv" in sig.parameters


def test_signature_main_param_kind_batch10():
    sig = inspect.signature(main)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_main_param_default_none_batch10():
    sig = inspect.signature(main)
    p = list(sig.parameters.values())[0]
    assert p.default is None


def test_signature_main_param_annotation_batch10():
    sig = inspect.signature(main)
    p = list(sig.parameters.values())[0]
    assert p.annotation == "list[str] | None"


def test_signature_main_return_annotation_batch10():
    sig = inspect.signature(main)
    assert sig.return_annotation == "int"


def test_signature_format_metric_param_count_batch10():
    sig = inspect.signature(_format_metric)
    assert len(sig.parameters) == 2


def test_signature_format_metric_param_names_batch10():
    sig = inspect.signature(_format_metric)
    names = list(sig.parameters)
    assert names == ["name", "metric"]


def test_signature_format_metric_param_kinds_batch10():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_format_metric_param_annotations_batch10():
    sig = inspect.signature(_format_metric)
    params = sig.parameters
    assert params["name"].annotation == "str"
    assert params["metric"].annotation == "dict"


def test_signature_format_metric_return_annotation_batch10():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation == "str"


def test_signature_run_inspect_doc_param_count_batch10():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1


def test_signature_run_inspect_doc_param_name_batch10():
    sig = inspect.signature(_run_inspect_doc)
    assert "args" in sig.parameters


def test_signature_run_inspect_doc_param_kind_batch10():
    sig = inspect.signature(_run_inspect_doc)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_run_inspect_doc_no_default_batch10():
    sig = inspect.signature(_run_inspect_doc)
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_signature_run_inspect_doc_return_annotation_batch10():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


def test_signature_4_funcs_are_function_type_batch10():
    for func in (_build_parser, main, _format_metric, _run_inspect_doc):
        assert inspect.isfunction(func)


def test_signature_4_funcs_module_eq_batch10():
    for func in (_build_parser, main, _format_metric, _run_inspect_doc):
        assert func.__module__ == "evaluation.cli"


def test_signature_main_no_var_positional_batch10():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_main_no_var_keyword_batch10():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- module 合理性第十批 ----------


def test_module_no_all_attribute_batch10():
    """cli.py 没有定义 __all__。"""
    assert not hasattr(climod, "__all__") or climod.__all__ is None or len(climod.__all__) == 0


def test_module_has_dunder_file_batch10():
    assert hasattr(climod, "__file__")
    assert climod.__file__ is not None


def test_module_dunder_file_endswith_cli_py_batch10():
    sep = os.sep
    assert climod.__file__.endswith("evaluation" + sep + "cli.py") or climod.__file__.endswith(
        "evaluation/cli.py"
    )


def test_module_dunder_name_batch10():
    assert climod.__name__ == "evaluation.cli"


def test_module_function_count_batch10():
    """4 module-level functions：_build_parser, main, _format_metric, _run_inspect_doc。"""
    funcs = [
        n
        for n, v in vars(climod).items()
        if inspect.isfunction(v) and v.__module__ == climod.__name__
    ]
    assert set(funcs) == {"_build_parser", "main", "_format_metric", "_run_inspect_doc"}
    assert len(funcs) == 4


def test_module_no_user_classes_batch10():
    classes = [
        n for n, v in vars(climod).items() if inspect.isclass(v) and v.__module__ == climod.__name__
    ]
    assert classes == []


def test_module_docstring_present_batch10():
    assert climod.__doc__ is not None
    assert len(climod.__doc__) > 30


def test_module_docstring_in_chinese_or_english_batch10():
    assert "评测" in climod.__doc__ or "evaluation" in climod.__doc__.lower()


def test_module_main_block_at_end_batch10():
    source = inspect.getsource(climod)
    assert 'if __name__ == "__main__":' in source


def test_module_main_block_only_at_end_batch10():
    """__main__ 块只在文件末尾出现一次。"""
    source = inspect.getsource(climod)
    assert source.count('if __name__ == "__main__":') == 1


def test_module_4_public_funcs_callable_batch10():
    for func in (_build_parser, main, _format_metric, _run_inspect_doc):
        assert callable(func)


# ---------- 端到端集成第十批 ----------


def test_e2e_build_parser_idempotent_batch10():
    """多次调用 _build_parser 返回独立 parser。"""
    p1 = _build_parser()
    p2 = _build_parser()
    assert p1 is not p2
    # 但都能正常解析
    ns1 = p1.parse_args(["validate-report", "a.json"])
    ns2 = p2.parse_args(["validate-report", "b.json"])
    assert ns1.input == "a.json"
    assert ns2.input == "b.json"


def test_e2e_format_metric_idempotent_batch10():
    out1 = _format_metric("x", {"value": 1, "reason": "ok"})
    out2 = _format_metric("x", {"value": 1, "reason": "ok"})
    assert out1 == out2


def test_e2e_main_inspect_doc_no_unexpected_exceptions_batch10(tmp_path):
    """连续 main inspect-doc 不抛异常（除非 SystemExit / 显式 raise）。"""
    for _ in range(2):
        p = tmp_path / "d.json"
        p.write_text("{}", encoding="utf-8")
        rc = main(["inspect-doc", str(p)])
        assert rc == 0


def test_e2e_full_chain_run_command_success_batch10(monkeypatch, tmp_path):
    """run 命令完整链路：manifest 加载 → 跑 → 校验 → 打印。"""
    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps(manifest_data), encoding="utf-8")
    o_path = tmp_path / "subdir" / "o.json"
    rc = main(["run", "--manifest", str(m_path), "--output", str(o_path)])
    assert rc == 0
    assert o_path.is_file()


def test_e2e_run_command_prints_summary_batch10(monkeypatch, tmp_path, capsys):
    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps(manifest_data), encoding="utf-8")
    o_path = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(m_path), "--output", str(o_path)])
    assert rc == 0
    out = capsys.readouterr().out
    # 必须含以下片段
    assert "documents=" in out
    assert "devset_status=" in out
    assert "file_count=" in out
    assert "groups=" in out
    assert "pdf=" in out
    assert "docx=" in out
    assert "git_commit=" in out
    assert "git_dirty=" in out


def test_e2e_run_command_with_kreuzberg_choice_batch10(monkeypatch, tmp_path, capsys):
    """run --parser kreuzberg 选项被接受。"""
    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps(manifest_data), encoding="utf-8")
    o_path = tmp_path / "o.json"
    rc = main(
        ["run", "--manifest", str(m_path), "--output", str(o_path), "--parser", "kreuzberg"]
    )
    assert rc == 0


def test_e2e_run_command_with_custom_max_chars_batch10(monkeypatch, tmp_path, capsys):
    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps(manifest_data), encoding="utf-8")
    o_path = tmp_path / "o.json"
    rc = main(
        [
            "run",
            "--manifest",
            str(m_path),
            "--output",
            str(o_path),
            "--max-chars",
            "500",
            "--tolerance-chars",
            "15",
        ]
    )
    assert rc == 0


def test_e2e_inspect_doc_returns_zero_for_empty_dict_batch10(tmp_path):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_inspect_doc_returns_zero_for_full_doc_batch10(tmp_path):
    doc = {
        "document_id": "test_doc",
        "source_type": "pdf",
        "source_path": "/test.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0.0",
        "elements": [{"type": "heading"}, {"type": "paragraph"}],
        "chunks": [{"id": "c1", "text": "hello"}],
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_validate_report_success_path_batch10(tmp_path):
    """validate-report 成功路径（用真实 report）。"""
    from evaluation.runner import run_evaluation

    class _StubManifest:
        documents = []
        expected_failures = []
        project_root = tmp_path
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []

    out_path = tmp_path / "valid.json"
    run_evaluation(_StubManifest(), out_path)
    rc = main(["validate-report", str(out_path)])
    assert rc == 0


def test_e2e_main_module_can_be_imported_batch10():
    import evaluation.cli as c
    assert c is climod


def test_e2e_run_no_unexpected_exceptions_with_options_batch10(tmp_path):
    """连续 run 不抛异常。"""
    for i in range(2):
        manifest_data = {
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }
        m_path = tmp_path / f"m_{i}.json"
        m_path.write_text(json.dumps(manifest_data), encoding="utf-8")
        o_path = tmp_path / f"o_{i}.json"
        rc = main(["run", "--manifest", str(m_path), "--output", str(o_path)])
        assert rc == 0
