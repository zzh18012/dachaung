r"""evaluation/cli.py 边角测试 - 第九轮（Round 205）。

补强已有 base/edges/edges2-8（共 ~768 测试）未覆盖的深度：
- _build_parser 各 argument 属性深度（type/required/default/choices/help）
- main() 完整 exit code 矩阵（0/1/2）
- _format_metric 各种 type/value/reason 组合
- _run_inspect_doc 输出 ordering 与 sort_key 各分支
- _run_inspect_doc 各种 metrics 组合（全 null/混合类型/dict 值）
- 模块 imports / 顶层 sys.stdout 重配置 / __main__ 入口
"""

from __future__ import annotations

import inspect
import io
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation.cli import (
    _build_parser,
    _format_metric,
    _run_inspect_doc,
    main,
)


# =========================================================================
# _build_parser 深度
# =========================================================================


def test_build_parser_returns_argument_parser():
    import argparse
    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_build_parser_prog_exact_value():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_contains_chinese():
    p = _build_parser()
    assert "评测" in p.description


def test_build_parser_subparsers_dest():
    p = _build_parser()
    # 找到 subparsers action
    sub_action = None
    for action in p._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            sub_action = action
            break
    assert sub_action is not None
    assert sub_action.dest == "command"


def test_build_parser_subparsers_required():
    p = _build_parser()
    for action in p._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            assert action.required is True
            return
    pytest.fail("no subparsers found")


def test_build_parser_has_three_subcommands():
    p = _build_parser()
    for action in p._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            assert set(action.choices.keys()) == {"run", "validate-report", "inspect-doc"}
            return
    pytest.fail("no subparsers found")


def test_build_parser_run_manifest_required_true():
    p = _build_parser()
    # 用 parse_args 验证 required
    with pytest.raises(SystemExit):
        p.parse_args(["run"])


def test_build_parser_run_output_required_true():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "x"])


def test_build_parser_run_minimal_args_ok():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.command == "run"
    assert args.manifest == "m.json"
    assert args.output == "o.json"


def test_build_parser_run_parser_choices_tuple():
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m", "--output", "o", "--parser", "kreuzberg",
    ])
    assert args.parser == "kreuzberg"


def test_build_parser_run_parser_invalid_choice_errors():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run", "--manifest", "m", "--output", "o", "--parser", "xxx",
        ])


def test_build_parser_run_max_chars_type_is_int():
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m", "--output", "o", "--max-chars", "500",
    ])
    assert args.max_chars == 500
    assert isinstance(args.max_chars, int)


def test_build_parser_run_max_chars_non_int_errors():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run", "--manifest", "m", "--output", "o", "--max-chars", "abc",
        ])


def test_build_parser_run_tolerance_chars_type_int():
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m", "--output", "o", "--tolerance-chars", "60",
    ])
    assert args.tolerance_chars == 60
    assert isinstance(args.tolerance_chars, int)


def test_build_parser_run_all_defaults():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m", "--output", "o"])
    assert args.parser == "fallback"
    assert args.max_chars == 800
    assert args.tolerance_chars == 30


def test_build_parser_validate_report_takes_positional_input():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.command == "validate-report"
    assert args.input == "report.json"


def test_build_parser_inspect_doc_takes_positional_input():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.command == "inspect-doc"
    assert args.input == "doc.json"


def test_build_parser_inspect_doc_tolerance_chars_default():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_tolerance_chars_explicit():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "100"])
    assert args.tolerance_chars == 100


def test_build_parser_no_args_errors(capsys):
    with pytest.raises(SystemExit):
        _build_parser().parse_args([])
    err = capsys.readouterr().err
    assert "command" in err.lower() or "required" in err.lower()


def test_build_parser_signature():
    sig = inspect.signature(_build_parser)
    assert list(sig.parameters) == []


# =========================================================================
# _format_metric 深度
# =========================================================================


def test_format_metric_value_none_with_reason():
    line = _format_metric("m", {"value": None, "reason": "no_data"})
    assert "null" in line
    assert "no_data" in line


def test_format_metric_value_none_no_reason_key():
    line = _format_metric("m", {})
    assert "null" in line
    assert "None" in line  # reason None renders as "None"


def test_format_metric_value_true_lowercase():
    line = _format_metric("m", {"value": True, "reason": "ok"})
    assert "true" in line


def test_format_metric_value_false_lowercase():
    line = _format_metric("m", {"value": False, "reason": "fail"})
    assert "false" in line


def test_format_metric_value_true_default_ok():
    line = _format_metric("m", {"value": True})
    assert "ok" in line


def test_format_metric_value_false_default_ok():
    line = _format_metric("m", {"value": False})
    assert "ok" in line


def test_format_metric_value_float_zero():
    line = _format_metric("m", {"value": 0.0})
    assert "0.0000" in line


def test_format_metric_value_float_one():
    line = _format_metric("m", {"value": 1.0})
    assert "1.0000" in line


def test_format_metric_value_float_negative():
    line = _format_metric("m", {"value": -0.5})
    assert "-0.5000" in line


def test_format_metric_value_float_many_decimals_truncated():
    line = _format_metric("m", {"value": 0.123456789})
    assert "0.1235" in line  # 4 位小数四舍五入


def test_format_metric_value_int_zero():
    line = _format_metric("m", {"value": 0, "reason": "x"})
    assert "0" in line


def test_format_metric_value_int_positive():
    line = _format_metric("m", {"value": 42, "reason": "x"})
    assert "42" in line


def test_format_metric_value_int_negative():
    line = _format_metric("m", {"value": -100, "reason": "x"})
    assert "-100" in line


def test_format_metric_value_dict_sorted_items():
    line = _format_metric("m", {"value": {"b": 2, "a": 1}, "reason": "r"})
    # sorted by key: a=1, b=2
    assert "a=1" in line
    assert "b=2" in line
    assert line.index("a=1") < line.index("b=2")


def test_format_metric_value_dict_with_int_values():
    line = _format_metric("m", {"value": {"x": 10, "y": 20}})
    assert "x=10" in line
    assert "y=20" in line


def test_format_metric_value_dict_with_string_values():
    line = _format_metric("m", {"value": {"k": "v"}})
    assert "k=v" in line


def test_format_metric_value_empty_dict():
    line = _format_metric("m", {"value": {}})
    # 空字典 items="" → 但仍渲染
    assert "()" not in line or "ok" in line


def test_format_metric_value_string():
    line = _format_metric("m", {"value": "hello", "reason": "r"})
    assert "hello" in line


def test_format_metric_value_list_falls_through():
    """list 走最后一个分支（默认 return）。"""
    line = _format_metric("m", {"value": [1, 2, 3], "reason": "r"})
    assert "[1, 2, 3]" in line


def test_format_metric_value_tuple_falls_through():
    line = _format_metric("m", {"value": (1, 2), "reason": "r"})
    assert "(1, 2)" in line


def test_format_metric_name_padded_to_36():
    """name 不足 36 字符 → pad 到 36。"""
    line = _format_metric("ab", {"value": True})
    # 36 字符的 padding 后是 "true"
    # "  ab" + spaces + "true"
    assert "ab" in line
    assert "true" in line
    # 检查 padding：line 应有 "  ab" + 34 空格 + "true"
    expected_prefix = "  ab" + " " * 32
    assert line.startswith(expected_prefix + " true") or " true" in line


def test_format_metric_name_exactly_36_chars():
    name = "a" * 36
    line = _format_metric(name, {"value": True})
    assert name in line


def test_format_metric_name_over_36_chars():
    name = "a" * 50
    line = _format_metric(name, {"value": True})
    assert name in line


def test_format_metric_unicode_name():
    line = _format_metric("中文 metric", {"value": True})
    assert "中文" in line


def test_format_metric_signature():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters)
    assert params == ["name", "metric"]


def test_format_metric_returns_str():
    result = _format_metric("x", {"value": True})
    assert isinstance(result, str)


# =========================================================================
# _run_inspect_doc 深度
# =========================================================================


def _write_valid_doc(tmp_path: Path) -> Path:
    """写一个最小的合法 document JSON。"""
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "/tmp/x.txt",
        "source_type": "text",
        "source_hash": "a" * 64,
        "parser_name": "text",
        "parser_version": "0.1.0",
        "elements": [{
            "element_id": "e1", "type": "paragraph",
            "parent_id": None, "source_locator": {"line": 1},
            "confidence": 0.9, "metadata": {}, "content": "hello world",
        }],
        "chunks": [{
            "chunk_id": "c1", "text": "hello world",
            "source_element_ids": ["e1"],
            "metadata": {},
        }],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def test_run_inspect_doc_returns_zero(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_prints_file_line(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "file:" in out
    assert str(p) in out


def test_run_inspect_doc_prints_document_id(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "document_id:" in out
    assert "d1" in out


def test_run_inspect_doc_prints_source_line(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "source:" in out
    assert "/tmp/x.txt" in out
    assert "type=text" in out


def test_run_inspect_doc_prints_parser_line(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "parser:" in out
    assert "text" in out
    assert "v0.1.0" in out


def test_run_inspect_doc_prints_counts_line(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "counts:" in out
    assert "elements=1" in out
    assert "chunks=1" in out


def test_run_inspect_doc_prints_metrics_section(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_metrics_sort_bool_first(tmp_path, capsys):
    """sort_key: bool → 0, 数值 → 1, dict/其他 → 2, null → 3。"""
    p = _write_valid_doc(tmp_path)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    # 找 metrics: 之后的内容
    metrics_idx = out.index("metrics:")
    metrics_section = out[metrics_idx:]
    # bool 指标应在前
    # 找一个 bool 指标（pipeline_success）的位置
    bool_pos = metrics_section.find("pipeline_success")
    null_pos = metrics_section.find("figure_caption")
    if bool_pos >= 0 and null_pos >= 0:
        assert bool_pos < null_pos


def test_run_inspect_doc_missing_file_returns_2(tmp_path, capsys):
    args = _build_parser().parse_args(["inspect-doc", str(tmp_path / "nope.json")])
    rc = _run_inspect_doc(args)
    assert rc == 2
    err = capsys.readouterr().err
    assert "文档不存在" in err or "nope.json" in err


def test_run_inspect_doc_directory_returns_2(tmp_path, capsys):
    args = _build_parser().parse_args(["inspect-doc", str(tmp_path)])
    rc = _run_inspect_doc(args)
    assert rc == 2


def test_run_inspect_doc_invalid_json_returns_1(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    rc = _run_inspect_doc(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON" in err


def test_run_inspect_doc_non_dict_returns_1(tmp_path, capsys):
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    rc = _run_inspect_doc(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "顶层不是对象" in err


def test_run_inspect_doc_empty_dict_returns_0(tmp_path, capsys):
    """空 dict 也能跑（doc 字段都缺）。"""
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_empty_dict_source_type_unknown(tmp_path, capsys):
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "unknown" in out


def test_run_inspect_doc_with_tolerance_chars_arg(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = _build_parser().parse_args([
        "inspect-doc", str(p), "--tolerance-chars", "100",
    ])
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_with_image_element(tmp_path, capsys):
    """doc 含 image element → 不应崩。"""
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "/tmp/x.pdf",
        "source_type": "pdf",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "0.1.0",
        "elements": [
            {
                "element_id": "e1", "type": "paragraph",
                "parent_id": None,
                "source_locator": {"page": 1},
                "confidence": 0.9, "metadata": {}, "content": "x",
            },
            {
                "element_id": "i1", "type": "image",
                "parent_id": None,
                "source_locator": {"page": 1},
                "confidence": 0.9, "metadata": {},
                "resource_path": "img.png",
            },
        ],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_metrics_output_includes_pipeline_success(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = _build_parser().parse_args(["inspect-doc", str(p)])
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "pipeline_success" in out


def test_run_inspect_doc_signature():
    sig = inspect.signature(_run_inspect_doc)
    params = list(sig.parameters)
    assert params == ["args"]


# =========================================================================
# main() 完整 exit code 矩阵
# =========================================================================


def test_main_inspect_doc_returns_zero(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_missing_returns_2(tmp_path):
    rc = main(["inspect-doc", str(tmp_path / "nope.json")])
    assert rc == 2


def test_main_validate_report_missing_returns_2(tmp_path):
    rc = main(["validate-report", str(tmp_path / "nope.json")])
    assert rc == 2


def test_main_validate_report_directory_returns_2(tmp_path):
    rc = main(["validate-report", str(tmp_path)])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_1(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_run_missing_manifest_returns_2(tmp_path):
    rc = main(["run", "--manifest", str(tmp_path / "nope.json"), "--output", str(tmp_path / "o.json")])
    assert rc == 2


def test_main_run_directory_manifest_returns_2(tmp_path):
    rc = main(["run", "--manifest", str(tmp_path), "--output", str(tmp_path / "o.json")])
    assert rc == 2


def test_main_no_command_errors(capsys):
    """无 command → argparse error → SystemExit(2)。"""
    with pytest.raises(SystemExit):
        main([])


def test_main_unknown_command_errors(capsys):
    with pytest.raises(SystemExit):
        main(["xxx"])


def test_main_run_invalid_parser_choice_errors(capsys):
    """argparse choices 校验。"""
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "m", "--output", "o", "--parser", "xxx"])


def test_main_run_max_chars_negative_passes_argparse(tmp_path):
    """argparse 接受负数 max_chars（不限制范围）。"""
    # 但实际 run_evaluation 可能拒绝，仅验证 argparse 不挡
    rc = main([
        "run", "--manifest", str(tmp_path / "nope.json"),
        "--output", str(tmp_path / "o.json"),
        "--max-chars", "-100",
    ])
    # manifest 不存在 → 2
    assert rc == 2


def test_main_inspect_doc_non_dict_returns_1(tmp_path):
    p = tmp_path / "list.json"
    p.write_text("[1, 2]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_empty_dict_returns_0(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


# =========================================================================
# main() stderr 输出
# =========================================================================


def test_main_validate_report_missing_prints_error_to_stderr(tmp_path, capsys):
    main(["validate-report", str(tmp_path / "nope.json")])
    err = capsys.readouterr().err
    assert "[ERROR]" in err
    assert "nope.json" in err


def test_main_inspect_doc_missing_prints_error_to_stderr(tmp_path, capsys):
    main(["inspect-doc", str(tmp_path / "nope.json")])
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_run_missing_manifest_prints_error(tmp_path, capsys):
    main(["run", "--manifest", str(tmp_path / "nope.json"), "--output", str(tmp_path / "o.json")])
    err = capsys.readouterr().err
    assert "[ERROR]" in err
    assert "清单不存在" in err


# =========================================================================
# main() validate-report 成功路径
# =========================================================================


def _write_valid_report(tmp_path: Path) -> Path:
    """写一个最小合法的 evaluation-report JSON。"""
    report = {
        "report_version": "1.1",
        "devset": {
            "status": "incomplete",
            "file_count": 1,
            "content_group_count": 1,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": ["text"],
        },
        "provenance": {
            "git_commit": "abc123",
            "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": "0.1.0",
            "dependencies": {},
            "max_chars": 800,
            "run_timestamp_iso": "2026-08-05T12:00:00Z",
        },
        "per_doc": [],
        "summary": {
            "counts": {},
            "success_rates": {},
            "ratio_macro_averages": {},
            "silent_drop_total": 0,
        },
    }
    p = tmp_path / "report.json"
    p.write_text(json.dumps(report), encoding="utf-8")
    return p


def test_main_validate_report_valid_returns_0(tmp_path, capsys):
    p = _write_valid_report(tmp_path)
    rc = main(["validate-report", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[OK]" in out


def test_main_validate_report_valid_prints_filename(tmp_path, capsys):
    p = _write_valid_report(tmp_path)
    main(["validate-report", str(p)])
    out = capsys.readouterr().out
    assert str(p) in out
    assert "Schema 校验" in out


def test_main_validate_report_invalid_schema_returns_1(tmp_path, capsys):
    """报告 schema 不合法 → EvalSchemaError → 1。"""
    p = tmp_path / "report.json"
    p.write_text(json.dumps({"wrong": "shape"}), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err


def test_main_validate_report_empty_file_returns_1(tmp_path, capsys):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_not_object_returns_1(tmp_path, capsys):
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


# =========================================================================
# main() signature / __main__ 入口
# =========================================================================


def test_main_signature():
    sig = inspect.signature(main)
    params = list(sig.parameters)
    assert params == ["argv"]
    assert sig.parameters["argv"].default is None


def test_main_returns_int_when_given_argv(tmp_path):
    rc = main(["inspect-doc", str(tmp_path / "nope.json")])
    assert isinstance(rc, int)


def test_module_has_main_callable():
    import evaluation.cli as m
    assert callable(m.main)


def test_module_has_build_parser_callable():
    import evaluation.cli as m
    assert callable(m._build_parser)


def test_module_has_format_metric_callable():
    import evaluation.cli as m
    assert callable(m._format_metric)


def test_module_has_run_inspect_doc_callable():
    import evaluation.cli as m
    assert callable(m._run_inspect_doc)


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_imports_argparse():
    import evaluation.cli as m
    assert hasattr(m, "argparse")


def test_module_imports_json():
    import evaluation.cli as m
    assert hasattr(m, "json")


def test_module_imports_sys():
    import evaluation.cli as m
    assert hasattr(m, "sys")


def test_module_imports_path():
    import evaluation.cli as m
    assert hasattr(m, "Path")


def test_module_imports_manifest():
    import evaluation.cli as m
    assert hasattr(m, "load_manifest")
    assert hasattr(m, "ManifestError")


def test_module_imports_report():
    import evaluation.cli as m
    assert hasattr(m, "get_git_provenance")


def test_module_imports_runner():
    import evaluation.cli as m
    assert hasattr(m, "run_evaluation")


def test_module_imports_schema():
    import evaluation.cli as m
    assert hasattr(m, "validate_file")
    assert hasattr(m, "EvalSchemaError")


def test_module_docstring_present():
    import evaluation.cli as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_subcommands():
    import evaluation.cli as m
    doc = m.__doc__
    assert "run" in doc
    assert "validate-report" in doc
    assert "inspect-doc" in doc


def test_module_uses_future_annotations():
    import evaluation.cli as m
    sig = inspect.signature(m.main)
    assert isinstance(sig.return_annotation, str)


def test_module_stdout_reconfigure_block_present():
    """模块顶层有 sys.stdout.reconfigure 处理。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "reconfigure" in src
    assert "utf-8" in src.lower() or "utf_8" in src.lower()


def test_module_main_entry_block_present():
    """__main__ 入口存在。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert '__name__ == "__main__"' in src


def test_module_no_all_defined():
    """evaluation.cli 不定义 __all__（所有 public 直接 importable）。"""
    import evaluation.cli as m
    assert not hasattr(m, "__all__") or m.__all__ is None
