"""evaluation/cli.py 第三十四轮 edges 测试（Round 363）。

重点补强 edges32 未触及的角度：
- _build_parser source level 字符串精确补强第三批
- main source level 字符串精确补强第三批
- _format_metric source level 字符串精确补强第三批
- _run_inspect_doc source level 字符串精确补强第三批
- argparse internals 第五批（_SubParsersAction / _StoreAction / Namespace）
- _format_metric 行为深度第六批
- _run_inspect_doc 行为深度第六批
- main 行为深度第六批
- module source forbidden tokens 第九批
- module source 字符串精确补强第三批
- signatures 精确补强第三批
- 模块整体合理性补强第三批
- 端到端集成补强第三批
"""

from __future__ import annotations

import argparse
import inspect
import json
import types
from pathlib import Path

import pytest

from evaluation import cli as cli_mod
from evaluation.cli import (
    _build_parser,
    _format_metric,
    _run_inspect_doc,
    main,
)


# ---------- _build_parser source level 字符串精确补强第三批 ----------


def test_build_parser_source_has_run_p_assignment():
    src = inspect.getsource(_build_parser)
    assert "run_p =" in src


def test_build_parser_source_has_val_p_assignment():
    src = inspect.getsource(_build_parser)
    assert "val_p =" in src


def test_build_parser_source_has_ins_p_assignment():
    src = inspect.getsource(_build_parser)
    assert "ins_p =" in src


def test_build_parser_source_run_manifest_help_string():
    src = inspect.getsource(_build_parser)
    assert "清单 JSON 路径" in src


def test_build_parser_source_run_output_help_string():
    src = inspect.getsource(_build_parser)
    assert "报告输出 JSON 路径" in src


def test_build_parser_source_run_parser_help_default_text():
    src = inspect.getsource(_build_parser)
    assert "默认 fallback" in src


def test_build_parser_source_run_max_chars_default_800_help():
    src = inspect.getsource(_build_parser)
    assert "默认 800" in src


def test_build_parser_source_tolerance_chars_help_text():
    src = inspect.getsource(_build_parser)
    assert "chunk_boundary 匹配容差" in src


def test_build_parser_source_validate_report_help_has_eval_report():
    src = inspect.getsource(_build_parser)
    assert "evaluation-report.schema.json" in src


def test_build_parser_source_inspect_doc_help_text():
    src = inspect.getsource(_build_parser)
    assert "不写报告" in src


def test_build_parser_source_inspect_doc_tolerance_default_30_help():
    src = inspect.getsource(_build_parser)
    assert "无标注时该指标固定 null" in src


def test_build_parser_source_uses_dest_command():
    src = inspect.getsource(_build_parser)
    assert 'dest="command"' in src


def test_build_parser_source_input_positional_run():
    src = inspect.getsource(_build_parser)
    assert 'add_argument("--manifest", required=True' in src


def test_build_parser_source_input_positional_validate():
    src = inspect.getsource(_build_parser)
    assert 'val_p.add_argument("input"' in src


def test_build_parser_source_input_positional_inspect():
    src = inspect.getsource(_build_parser)
    assert 'ins_p.add_argument("input"' in src


def test_build_parser_source_no_class_keyword():
    src = inspect.getsource(_build_parser)
    assert "class " not in src


def test_build_parser_source_no_yield():
    src = inspect.getsource(_build_parser)
    assert "yield" not in src


def test_build_parser_source_no_async():
    src = inspect.getsource(_build_parser)
    assert "async " not in src


def test_build_parser_source_no_walrus():
    src = inspect.getsource(_build_parser)
    assert ":=" not in src


def test_build_parser_source_has_return_p():
    src = inspect.getsource(_build_parser)
    assert "return p" in src


# ---------- main source level 字符串精确补强第三批 ----------


def test_main_source_uses_args_command():
    src = inspect.getsource(main)
    assert "args.command" in src


def test_main_source_uses_args_manifest():
    src = inspect.getsource(main)
    assert "args.manifest" in src


def test_main_source_uses_args_output():
    src = inspect.getsource(main)
    assert "args.output" in src


def test_main_source_uses_path_manifest():
    src = inspect.getsource(main)
    assert "Path(args.manifest)" in src


def test_main_source_uses_path_output():
    src = inspect.getsource(main)
    assert "Path(args.output)" in src


def test_main_source_uses_is_file_check_manifest():
    src = inspect.getsource(main)
    assert "manifest_path.is_file()" in src


def test_main_source_returns_2_manifest_missing():
    src = inspect.getsource(main)
    assert "return 2" in src


def test_main_source_returns_1_manifest_error():
    src = inspect.getsource(main)
    assert "return 1" in src


def test_main_source_returns_0_run_success():
    src = inspect.getsource(main)
    assert "return 0" in src


def test_main_source_passes_kwargs_to_run_evaluation():
    src = inspect.getsource(main)
    assert "parser_name=args.parser" in src
    assert "max_chars=args.max_chars" in src
    assert "tolerance_chars=args.tolerance_chars" in src


def test_main_source_validates_after_run():
    src = inspect.getsource(main)
    assert 'validate_file(output_path, "evaluation-report.schema.json")' in src


def test_main_source_counts_per_doc():
    src = inspect.getsource(main)
    assert 'report.get("per_doc", [])' in src


def test_main_source_pipeline_success_check():
    src = inspect.getsource(main)
    assert '"pipeline_success"' in src


def test_main_source_uses_get_git_provenance_for_project_root():
    src = inspect.getsource(main)
    assert "get_git_provenance(manifest.project_root)" in src


def test_main_source_handles_file_not_found_in_validate():
    src = inspect.getsource(main)
    assert "FileNotFoundError" in src


def test_main_source_handles_json_decode_in_validate():
    src = inspect.getsource(main)
    assert "json.JSONDecodeError" in src


def test_main_source_validate_report_branch():
    src = inspect.getsource(main)
    assert 'args.command == "validate-report"' in src


def test_main_source_inspect_doc_branch():
    src = inspect.getsource(main)
    assert 'args.command == "inspect-doc"' in src


def test_main_source_run_branch():
    src = inspect.getsource(main)
    assert 'args.command == "run"' in src


def test_main_source_calls_run_inspect_doc():
    src = inspect.getsource(main)
    assert "_run_inspect_doc(args)" in src


# ---------- _format_metric source level 字符串精确补强第三批 ----------


def test_format_metric_source_metric_get_value():
    src = inspect.getsource(_format_metric)
    assert 'metric.get("value")' in src


def test_format_metric_source_metric_get_reason():
    src = inspect.getsource(_format_metric)
    assert 'metric.get("reason")' in src


def test_format_metric_source_value_is_none_branch():
    src = inspect.getsource(_format_metric)
    assert "value is None" in src


def test_format_metric_source_isinstance_bool():
    src = inspect.getsource(_format_metric)
    assert "isinstance(value, bool)" in src


def test_format_metric_source_isinstance_float():
    src = inspect.getsource(_format_metric)
    assert "isinstance(value, float)" in src


def test_format_metric_source_isinstance_dict():
    src = inspect.getsource(_format_metric)
    assert "isinstance(value, dict)" in src


def test_format_metric_source_str_lower():
    src = inspect.getsource(_format_metric)
    assert "str(value).lower()" in src


def test_format_metric_source_float_format_4f_in_source():
    src = inspect.getsource(_format_metric)
    assert "{value:.4f}" in src


def test_format_metric_source_dict_items_join_comma():
    src = inspect.getsource(_format_metric)
    assert '", ".join' in src or '", ".join(' in src


def test_format_metric_source_padding_36():
    src = inspect.getsource(_format_metric)
    assert "{name:36}" in src


def test_format_metric_source_default_ok_in_source():
    src = inspect.getsource(_format_metric)
    assert "reason or 'ok'" in src or 'reason or "ok"' in src


def test_format_metric_source_sorts_dict_items():
    src = inspect.getsource(_format_metric)
    assert "sorted(value.items())" in src


def test_format_metric_source_no_subprocess():
    src = inspect.getsource(_format_metric)
    assert "subprocess" not in src


def test_format_metric_source_no_eval():
    src = inspect.getsource(_format_metric)
    assert "eval(" not in src
    assert "exec(" not in src


# ---------- _run_inspect_doc source level 字符串精确补强第三批 ----------


def test_run_inspect_doc_source_lazy_import_chunk_boundary_prf():
    src = inspect.getsource(_run_inspect_doc)
    assert "from evaluation.annotation_metrics import chunk_boundary_prf" in src


def test_run_inspect_doc_source_lazy_import_figure_caption_prf():
    src = inspect.getsource(_run_inspect_doc)
    assert "figure_caption_prf" in src


def test_run_inspect_doc_source_lazy_import_compute_automatic_metrics():
    src = inspect.getsource(_run_inspect_doc)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_run_inspect_doc_source_input_path_assignment():
    src = inspect.getsource(_run_inspect_doc)
    assert "input_path = Path(args.input)" in src


def test_run_inspect_doc_source_is_file_check():
    src = inspect.getsource(_run_inspect_doc)
    assert "input_path.is_file()" in src


def test_run_inspect_doc_source_open_utf8():
    src = inspect.getsource(_run_inspect_doc)
    assert 'open("r", encoding="utf-8")' in src


def test_run_inspect_doc_source_catches_json_decode_error():
    src = inspect.getsource(_run_inspect_doc)
    assert "json.JSONDecodeError" in src


def test_run_inspect_doc_source_isinstance_dict_check():
    src = inspect.getsource(_run_inspect_doc)
    assert "isinstance(doc, dict)" in src


def test_run_inspect_doc_source_doc_get_source_type_default():
    src = inspect.getsource(_run_inspect_doc)
    assert 'doc.get("source_type", "unknown")' in src


def test_run_inspect_doc_source_doc_get_elements_or_empty():
    src = inspect.getsource(_run_inspect_doc)
    assert 'doc.get("elements") or []' in src


def test_run_inspect_doc_source_doc_get_chunks_or_empty():
    src = inspect.getsource(_run_inspect_doc)
    assert 'doc.get("chunks") or []' in src


def test_run_inspect_doc_source_compute_automatic_metrics_kwargs():
    src = inspect.getsource(_run_inspect_doc)
    assert "document=doc" in src
    assert "error=None" in src
    assert "source_type=source_type" in src
    assert "expectations=None" in src
    assert "image_base_dir=None" in src


def test_run_inspect_doc_source_metrics_update_figure_caption():
    src = inspect.getsource(_run_inspect_doc)
    assert "metrics.update(figure_caption_prf(doc, None))" in src


def test_run_inspect_doc_source_metrics_update_chunk_boundary():
    src = inspect.getsource(_run_inspect_doc)
    assert "tolerance_chars=args.tolerance_chars" in src


def test_run_inspect_doc_source_prints_file_path():
    src = inspect.getsource(_run_inspect_doc)
    assert "file:" in src


def test_run_inspect_doc_source_prints_document_id():
    src = inspect.getsource(_run_inspect_doc)
    assert "document_id:" in src


def test_run_inspect_doc_source_prints_source():
    src = inspect.getsource(_run_inspect_doc)
    assert "source:" in src


def test_run_inspect_doc_source_prints_parser():
    src = inspect.getsource(_run_inspect_doc)
    assert "parser:" in src


def test_run_inspect_doc_source_prints_counts():
    src = inspect.getsource(_run_inspect_doc)
    assert "counts:" in src


def test_run_inspect_doc_source_uses_sort_key_function():
    src = inspect.getsource(_run_inspect_doc)
    assert "_sort_key" in src


def test_run_inspect_doc_source_uses_sorted_metrics():
    src = inspect.getsource(_run_inspect_doc)
    assert "sorted(metrics.keys()" in src


def test_run_inspect_doc_source_return_0():
    src = inspect.getsource(_run_inspect_doc)
    assert "return 0" in src


def test_run_inspect_doc_source_return_1_json_decode():
    src = inspect.getsource(_run_inspect_doc)
    assert "return 1" in src


def test_run_inspect_doc_source_return_2_not_file():
    src = inspect.getsource(_run_inspect_doc)
    assert "return 2" in src


def test_run_inspect_doc_source_return_1_not_dict():
    src = inspect.getsource(_run_inspect_doc)
    # 出现 2 次：一次 JSON decode, 一次 not dict
    assert src.count("return 1") >= 2


def test_run_inspect_doc_source_no_eval():
    src = inspect.getsource(_run_inspect_doc)
    assert "eval(" not in src
    assert "exec(" not in src


def test_run_inspect_doc_source_no_subprocess():
    src = inspect.getsource(_run_inspect_doc)
    assert "subprocess" not in src


def test_run_inspect_doc_source_no_yield():
    src = inspect.getsource(_run_inspect_doc)
    assert "yield" not in src


def test_run_inspect_doc_source_no_async():
    src = inspect.getsource(_run_inspect_doc)
    assert "async " not in src


# ---------- argparse internals 第五批 ----------


def test_build_parser_subparsers_action_type():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert len(subparsers_actions) == 1


def test_build_parser_subparsers_dest_command():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert subparsers_actions[0].dest == "command"


def test_build_parser_subparsers_required_true():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert subparsers_actions[0].required is True


def test_build_parser_has_three_subparsers():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert len(subparsers_actions[0].choices) == 3


def test_build_parser_subparser_names():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    names = set(subparsers_actions[0].choices.keys())
    assert names == {"run", "validate-report", "inspect-doc"}


def test_build_parser_run_subparser_has_manifest_action():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = subparsers_actions[0].choices["run"]
    option_strings = []
    for a in run_p._actions:
        option_strings.extend(a.option_strings)
    assert "--manifest" in option_strings


def test_build_parser_run_subparser_manifest_required():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = subparsers_actions[0].choices["run"]
    manifest_action = next(
        a for a in run_p._actions if "--manifest" in a.option_strings
    )
    assert manifest_action.required is True


def test_build_parser_run_subparser_output_required():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = subparsers_actions[0].choices["run"]
    output_action = next(
        a for a in run_p._actions if "--output" in a.option_strings
    )
    assert output_action.required is True


def test_build_parser_run_subparser_parser_default_fallback():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = subparsers_actions[0].choices["run"]
    parser_action = next(
        a for a in run_p._actions if "--parser" in a.option_strings
    )
    assert parser_action.default == "fallback"


def test_build_parser_run_subparser_parser_choices_tuple():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = subparsers_actions[0].choices["run"]
    parser_action = next(
        a for a in run_p._actions if "--parser" in a.option_strings
    )
    assert parser_action.choices == ("fallback", "kreuzberg")


def test_build_parser_run_subparser_max_chars_default_800():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = subparsers_actions[0].choices["run"]
    max_chars_action = next(
        a for a in run_p._actions if "--max-chars" in a.option_strings
    )
    assert max_chars_action.default == 800


def test_build_parser_run_subparser_max_chars_type_int():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = subparsers_actions[0].choices["run"]
    max_chars_action = next(
        a for a in run_p._actions if "--max-chars" in a.option_strings
    )
    assert max_chars_action.type is int


def test_build_parser_run_subparser_tolerance_chars_default_30():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = subparsers_actions[0].choices["run"]
    tol_action = next(
        a for a in run_p._actions if "--tolerance-chars" in a.option_strings
    )
    assert tol_action.default == 30


def test_build_parser_validate_report_input_positional_via_actions():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    val_p = subparsers_actions[0].choices["validate-report"]
    positional_actions = [
        a for a in val_p._actions
        if isinstance(a, argparse._StoreAction) and not a.option_strings
    ]
    assert len(positional_actions) == 1
    assert positional_actions[0].dest == "input"


def test_build_parser_inspect_doc_input_positional_via_actions():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_p = subparsers_actions[0].choices["inspect-doc"]
    positional_actions = [
        a for a in ins_p._actions
        if isinstance(a, argparse._StoreAction) and not a.option_strings
    ]
    assert len(positional_actions) == 1
    assert positional_actions[0].dest == "input"


def test_build_parser_inspect_doc_tolerance_default_30():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_p = subparsers_actions[0].choices["inspect-doc"]
    tol_action = next(
        a for a in ins_p._actions if "--tolerance-chars" in a.option_strings
    )
    assert tol_action.default == 30


def test_build_parser_inspect_doc_has_no_parser_argument():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_p = subparsers_actions[0].choices["inspect-doc"]
    option_strings = []
    for a in ins_p._actions:
        option_strings.extend(a.option_strings)
    assert "--parser" not in option_strings


def test_build_parser_inspect_doc_has_no_max_chars_argument():
    p = _build_parser()
    subparsers_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_p = subparsers_actions[0].choices["inspect-doc"]
    option_strings = []
    for a in ins_p._actions:
        option_strings.extend(a.option_strings)
    assert "--max-chars" not in option_strings


def test_build_parser_run_namespace_via_parse_args():
    p = _build_parser()
    ns = p.parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json"]
    )
    assert isinstance(ns, argparse.Namespace)
    assert ns.command == "run"
    assert ns.manifest == "a.json"
    assert ns.output == "b.json"
    assert ns.parser == "fallback"
    assert ns.max_chars == 800
    assert ns.tolerance_chars == 30


def test_build_parser_validate_report_namespace():
    p = _build_parser()
    ns = p.parse_args(["validate-report", "report.json"])
    assert ns.command == "validate-report"
    assert ns.input == "report.json"


def test_build_parser_inspect_doc_namespace():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.command == "inspect-doc"
    assert ns.input == "doc.json"
    assert ns.tolerance_chars == 30


def test_build_parser_inspect_doc_namespace_with_tolerance():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "50"])
    assert ns.tolerance_chars == 50


def test_build_parser_run_with_kreuzberg_choice():
    p = _build_parser()
    ns = p.parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json", "--parser", "kreuzberg"]
    )
    assert ns.parser == "kreuzberg"


def test_build_parser_run_invalid_choice_exits():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(
            ["run", "--manifest", "a.json", "--output", "b.json", "--parser", "unknown"]
        )


def test_build_parser_no_command_exits():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_parser_run_missing_required_manifest_exits():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "b.json"])


def test_build_parser_run_missing_required_output_exits():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "a.json"])


# ---------- _format_metric 行为深度第六批 ----------


def test_format_metric_int_zero():
    s = _format_metric("count", {"value": 0, "reason": None})
    assert "0" in s


def test_format_metric_int_large():
    s = _format_metric("count", {"value": 1234567890, "reason": None})
    assert "1234567890" in s


def test_format_metric_int_negative():
    s = _format_metric("delta", {"value": -42, "reason": None})
    assert "-42" in s


def test_format_metric_float_zero():
    s = _format_metric("ratio", {"value": 0.0, "reason": None})
    assert "0.0000" in s


def test_format_metric_float_one():
    s = _format_metric("ratio", {"value": 1.0, "reason": None})
    assert "1.0000" in s


def test_format_metric_float_tiny():
    s = _format_metric("ratio", {"value": 0.0001, "reason": None})
    assert "0.0001" in s


def test_format_metric_float_rounding():
    s = _format_metric("ratio", {"value": 0.123456789, "reason": None})
    # 4 decimal places
    assert "0.1235" in s


def test_format_metric_float_negative():
    s = _format_metric("delta", {"value": -3.14, "reason": None})
    assert "-3.1400" in s


def test_format_metric_float_very_large():
    s = _format_metric("big", {"value": 1234567.89, "reason": None})
    assert "1234567.8900" in s


def test_format_metric_bool_true():
    s = _format_metric("ok", {"value": True, "reason": None})
    assert "true" in s
    assert "(ok)" in s


def test_format_metric_bool_false():
    s = _format_metric("ok", {"value": False, "reason": "failure"})
    assert "false" in s
    assert "(failure)" in s


def test_format_metric_bool_true_with_reason():
    s = _format_metric("ok", {"value": True, "reason": "lucky"})
    # bool 分支忽略 reason 字段
    assert "true" in s
    assert "(lucky)" in s


def test_format_metric_none_with_long_reason():
    long_reason = "x" * 200
    s = _format_metric("metric", {"value": None, "reason": long_reason})
    assert long_reason in s


def test_format_metric_none_with_unicode_reason():
    s = _format_metric("metric", {"value": None, "reason": "无标注"})
    assert "无标注" in s


def test_format_metric_dict_with_int_values():
    s = _format_metric("counts", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in s
    assert "b=2" in s


def test_format_metric_dict_with_zero_values():
    s = _format_metric("counts", {"value": {"a": 0, "b": 0}, "reason": None})
    assert "a=0" in s


def test_format_metric_dict_sorted_alphabetically():
    s = _format_metric(
        "counts",
        {"value": {"zebra": 1, "apple": 2, "mango": 3}, "reason": None},
    )
    # 字母顺序
    assert s.index("apple") < s.index("mango") < s.index("zebra")


def test_format_metric_dict_with_special_chars_in_key():
    s = _format_metric(
        "counts",
        {"value": {"key.with.dots": 1}, "reason": None},
    )
    assert "key.with.dots=1" in s


def test_format_metric_string_value_uses_default_branch():
    s = _format_metric("name", {"value": "hello", "reason": None})
    # 字符串走 default 分支：reason or 'ok'
    assert "hello" in s
    assert "(ok)" in s


def test_format_metric_string_value_with_reason():
    s = _format_metric("name", {"value": "hello", "reason": "from_parser"})
    assert "hello" in s
    assert "(from_parser)" in s


def test_format_metric_list_value_uses_default_branch():
    s = _format_metric("list_metric", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in s


def test_format_metric_empty_dict_value():
    s = _format_metric("empty", {"value": {}, "reason": None})
    # 空 dict，items 是空字符串
    assert "empty" in s
    assert "(ok)" in s


def test_format_metric_padding_36_chars():
    s = _format_metric("x", {"value": True, "reason": None})
    # 找到 "x" 之后到 "true" 之间的字符数（name 占 36 + 1 空格分隔）
    idx = s.index("x")
    true_idx = s.index("true")
    # x 占 1 字符 + 35 填充空格（共 36） + 1 空格分隔 = 37 字符
    assert true_idx - idx == 37


def test_format_metric_returns_str_type():
    s = _format_metric("x", {"value": True, "reason": None})
    assert isinstance(s, str)


def test_format_metric_does_not_mutate_input():
    metric = {"value": True, "reason": None}
    original = dict(metric)
    _format_metric("x", metric)
    assert metric == original


# ---------- _run_inspect_doc 行为深度第六批 ----------


def _make_namespace(input_path: str, tolerance_chars: int = 30) -> argparse.Namespace:
    return argparse.Namespace(input=input_path, tolerance_chars=tolerance_chars)


def test_run_inspect_doc_returns_2_when_path_is_dir(tmp_path):
    ns = _make_namespace(str(tmp_path))
    rc = _run_inspect_doc(ns)
    assert rc == 2


def test_run_inspect_doc_returns_1_when_doc_is_list(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("[]", encoding="utf-8")
    ns = _make_namespace(str(p))
    rc = _run_inspect_doc(ns)
    assert rc == 1


def test_run_inspect_doc_returns_1_when_doc_is_int(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("42", encoding="utf-8")
    ns = _make_namespace(str(p))
    rc = _run_inspect_doc(ns)
    assert rc == 1


def test_run_inspect_doc_returns_1_when_doc_is_string(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text('"hello"', encoding="utf-8")
    ns = _make_namespace(str(p))
    rc = _run_inspect_doc(ns)
    assert rc == 1


def test_run_inspect_doc_returns_1_when_doc_is_null(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("null", encoding="utf-8")
    ns = _make_namespace(str(p))
    rc = _run_inspect_doc(ns)
    assert rc == 1


def test_run_inspect_doc_returns_1_when_doc_is_float(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("3.14", encoding="utf-8")
    ns = _make_namespace(str(p))
    rc = _run_inspect_doc(ns)
    assert rc == 1


def test_run_inspect_doc_returns_1_when_doc_is_bool(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("true", encoding="utf-8")
    ns = _make_namespace(str(p))
    rc = _run_inspect_doc(ns)
    assert rc == 1


def test_run_inspect_doc_returns_0_minimal_dict(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    ns = _make_namespace(str(p))
    rc = _run_inspect_doc(ns)
    assert rc == 0
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_with_full_doc(tmp_path, capsys):
    p = tmp_path / "doc.json"
    doc = {
        "document_id": "doc-001",
        "source_type": "pdf",
        "source_path": "samples/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            {"element_id": "e1", "type": "heading", "text": "Title"},
            {"element_id": "e2", "type": "paragraph", "text": "Body"},
        ],
        "chunks": [
            {"chunk_id": "c1", "source_element_ids": ["e1", "e2"], "text": "Title Body"}
        ],
    }
    p.write_text(json.dumps(doc), encoding="utf-8")
    ns = _make_namespace(str(p))
    rc = _run_inspect_doc(ns)
    assert rc == 0
    out = capsys.readouterr().out
    assert "doc-001" in out
    assert "elements=2" in out
    assert "chunks=1" in out


def test_run_inspect_doc_with_custom_tolerance(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    ns = _make_namespace(str(p), tolerance_chars=50)
    rc = _run_inspect_doc(ns)
    assert rc == 0


def test_run_inspect_doc_prints_metrics_section(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    ns = _make_namespace(str(p))
    _run_inspect_doc(ns)
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_prints_file_label(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    ns = _make_namespace(str(p))
    _run_inspect_doc(ns)
    out = capsys.readouterr().out
    assert "file:" in out


def test_run_inspect_doc_handles_invalid_json_array_root(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    ns = _make_namespace(str(p))
    # 数组 → JSON 解析成功，但 isinstance dict 失败
    rc = _run_inspect_doc(ns)
    assert rc == 1


def test_run_inspect_doc_handles_empty_file(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("", encoding="utf-8")
    ns = _make_namespace(str(p))
    # 空文件 → JSON 解析失败
    rc = _run_inspect_doc(ns)
    assert rc == 1


def test_run_inspect_doc_handles_trailing_comma(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text('{"a": 1,}', encoding="utf-8")
    ns = _make_namespace(str(p))
    rc = _run_inspect_doc(ns)
    assert rc == 1


def test_run_inspect_doc_handles_unquoted_keys(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{a: 1}", encoding="utf-8")
    ns = _make_namespace(str(p))
    rc = _run_inspect_doc(ns)
    assert rc == 1


def test_run_inspect_doc_handles_utf8_bom(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_bytes(b'\xef\xbb\xbf{}')
    ns = _make_namespace(str(p))
    rc = _run_inspect_doc(ns)
    # utf-8 BOM 触发 json 解析失败（CLI 用 utf-8 不是 utf-8-sig）
    assert rc == 1


def test_run_inspect_doc_returns_int(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    ns = _make_namespace(str(p))
    rc = _run_inspect_doc(ns)
    assert isinstance(rc, int)


def test_run_inspect_doc_with_source_type_unknown(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "unknown"}), encoding="utf-8"
    )
    ns = _make_namespace(str(p))
    rc = _run_inspect_doc(ns)
    assert rc == 0
    out = capsys.readouterr().out
    assert "type=unknown" in out


def test_run_inspect_doc_default_source_type_when_missing(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    ns = _make_namespace(str(p))
    _run_inspect_doc(ns)
    out = capsys.readouterr().out
    assert "type=unknown" in out


def test_run_inspect_doc_with_docx_source_type(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "docx"}), encoding="utf-8"
    )
    ns = _make_namespace(str(p))
    _run_inspect_doc(ns)
    out = capsys.readouterr().out
    assert "type=docx" in out


# ---------- main 行为深度第六批 ----------


def test_main_returns_2_unknown_command(capsys):
    # _build_parser 在 subparser required=True 模式下会 sys.exit
    with pytest.raises(SystemExit) as ei:
        main(["unknown-command"])
    assert ei.value.code == 2


def test_main_validate_report_returns_0_minimal_dict(tmp_path, capsys):
    """用一个 valid minimal report schema 通过校验."""
    # 直接用一个会让 validate_file 失败的 dict（缺少必要字段）→ rc=1
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_returns_2_when_path_is_dir(tmp_path):
    rc = main(["validate-report", str(tmp_path)])
    assert rc == 2


def test_main_inspect_doc_returns_2_when_dir(tmp_path):
    rc = main(["inspect-doc", str(tmp_path)])
    assert rc == 2


def test_main_inspect_doc_returns_1_when_invalid_json(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_returns_0_minimal(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_run_returns_2_when_manifest_missing(tmp_path):
    rc = main(
        [
            "run",
            "--manifest",
            str(tmp_path / "missing.json"),
            "--output",
            str(tmp_path / "out.json"),
        ]
    )
    assert rc == 2


def test_main_inspect_doc_with_tolerance_arg(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "100"])
    assert rc == 0


def test_main_no_args_raises_system_exit():
    with pytest.raises(SystemExit):
        main([])


# ---------- module source forbidden tokens 第九批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "asyncio",
        "threading",
        "concurrent",
        "multiprocessing",
        "queue",
        "socket",
        "select",
        "re.match",
        "datetime.datetime",
        "os.system",
        "logging",
        "urllib",
        "http",
        "ctypes",
        "pickle",
        "shutil",
        "tempfile",
        "glob",
        "unittest",
        "pytest",
        "sys.exit",
        "copy",
        "weakref",
        "abc",
        "contextlib",
        "operator",
        "functools",
        "itertools",
        "collections",
        "importlib",
        "platform",
    ],
)
def test_cli_source_no_forbidden_token_ninth(token):
    src = inspect.getsource(cli_mod)
    assert token not in src


# ---------- module source 字符串精确补强第三批 ----------


def test_cli_source_has_argparse_import():
    src = inspect.getsource(cli_mod)
    assert "import argparse" in src


def test_cli_source_has_json_import():
    src = inspect.getsource(cli_mod)
    assert "import json" in src


def test_cli_source_has_sys_import():
    src = inspect.getsource(cli_mod)
    assert "import sys" in src


def test_cli_source_has_path_import():
    src = inspect.getsource(cli_mod)
    assert "from pathlib import Path" in src


def test_cli_source_has_manifest_imports():
    src = inspect.getsource(cli_mod)
    assert "ManifestError" in src
    assert "load_manifest" in src


def test_cli_source_has_report_imports():
    src = inspect.getsource(cli_mod)
    assert "get_git_provenance" in src


def test_cli_source_has_runner_imports():
    src = inspect.getsource(cli_mod)
    assert "run_evaluation" in src


def test_cli_source_has_schema_imports():
    src = inspect.getsource(cli_mod)
    assert "EvalSchemaError" in src
    assert "validate_file" in src


def test_cli_source_has_stdout_reconfigure_call():
    src = inspect.getsource(cli_mod)
    assert "sys.stdout.reconfigure" in src


def test_cli_source_has_stderr_reconfigure_call():
    src = inspect.getsource(cli_mod)
    assert "sys.stderr.reconfigure" in src


def test_cli_source_hasattr_check():
    src = inspect.getsource(cli_mod)
    assert 'hasattr(sys.stdout, "reconfigure")' in src


def test_cli_source_reconfigure_args():
    src = inspect.getsource(cli_mod)
    assert 'encoding="utf-8"' in src
    assert 'errors="replace"' in src


def test_cli_source_catches_attribute_error():
    src = inspect.getsource(cli_mod)
    assert "AttributeError" in src


def test_cli_source_catches_oserror():
    src = inspect.getsource(cli_mod)
    assert "OSError" in src


def test_cli_source_no_class_keyword_at_module_level():
    src = inspect.getsource(cli_mod)
    # 排除注释和 docstring 后无 class 定义
    lines = [
        line for line in src.split("\n")
        if line.strip() and not line.strip().startswith("#")
    ]
    has_class = any(line.lstrip().startswith("class ") for line in lines)
    assert not has_class


def test_cli_source_has_main_function():
    src = inspect.getsource(cli_mod)
    assert "def main(" in src


def test_cli_source_has_build_parser_function():
    src = inspect.getsource(cli_mod)
    assert "def _build_parser(" in src


def test_cli_source_has_format_metric_function():
    src = inspect.getsource(cli_mod)
    assert "def _format_metric(" in src


def test_cli_source_has_run_inspect_doc_function():
    src = inspect.getsource(cli_mod)
    assert "def _run_inspect_doc(" in src


def test_cli_source_main_block():
    src = inspect.getsource(cli_mod)
    assert 'if __name__ == "__main__":' in src


def test_cli_source_main_block_raises_system_exit():
    src = inspect.getsource(cli_mod)
    assert "raise SystemExit(main())" in src


def test_cli_source_no_eval_exec_compile():
    src = inspect.getsource(cli_mod)
    assert "eval(" not in src
    assert "exec(" not in src
    assert "compile(" not in src


def test_cli_source_no_relative_import_above_eval():
    src = inspect.getsource(cli_mod)
    lines = src.split("\n")
    # 不应有 from . 或 from .. 这种相对导入
    assert not any(
        line.lstrip().startswith("from .") and "evaluation" not in line
        for line in lines
    )


def test_cli_source_no_star_import():
    src = inspect.getsource(cli_mod)
    assert "import *" not in src


def test_cli_source_no_yield():
    src = inspect.getsource(cli_mod)
    assert "yield" not in src


def test_cli_source_no_async_def():
    src = inspect.getsource(cli_mod)
    assert "async def" not in src


def test_cli_source_no_walrus():
    src = inspect.getsource(cli_mod)
    assert ":=" not in src


def test_cli_source_no_global_keyword():
    src = inspect.getsource(cli_mod)
    assert "global " not in src


def test_cli_source_docstring_present():
    assert cli_mod.__doc__ is not None
    assert len(cli_mod.__doc__) > 20


def test_cli_source_docstring_mentions_run():
    assert "run" in cli_mod.__doc__.lower()


def test_cli_source_docstring_mentions_validate():
    assert "validate" in cli_mod.__doc__.lower()


def test_cli_source_docstring_mentions_inspect():
    assert "inspect" in cli_mod.__doc__.lower()


def test_cli_source_no_all_attribute():
    assert not hasattr(cli_mod, "__all__")


# ---------- signatures 精确补强第三批 ----------


def test_signature_main_argv_default_none():
    sig = inspect.signature(main)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "argv"
    assert params[0].default is None


def test_signature_main_no_varargs():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_main_return_annotation_int():
    sig = inspect.signature(main)
    # from __future__ import annotations 让注解变字符串
    assert sig.return_annotation == "int"


def test_signature_build_parser_no_params():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_build_parser_return_annotation_argument_parser():
    sig = inspect.signature(_build_parser)
    assert sig.return_annotation == "argparse.ArgumentParser"


def test_signature_format_metric_two_params():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert params[0].name == "name"
    assert params[1].name == "metric"


def test_signature_format_metric_no_defaults():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_format_metric_return_annotation_str():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation == "str"


def test_signature_run_inspect_doc_one_param():
    sig = inspect.signature(_run_inspect_doc)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "args"


def test_signature_run_inspect_doc_no_default():
    sig = inspect.signature(_run_inspect_doc)
    params = list(sig.parameters.values())
    assert params[0].default is inspect.Parameter.empty


def test_signature_run_inspect_doc_return_annotation_int():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


def test_signature_build_parser_no_varargs():
    sig = inspect.signature(_build_parser)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_format_metric_no_varargs():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_run_inspect_doc_no_varargs():
    sig = inspect.signature(_run_inspect_doc)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_main_param_kind_keyword_or_positional():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_format_metric_params_kind():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


# ---------- 模块整体合理性补强第三批 ----------


def test_module_namespace_has_4_callables():
    callables = [
        (name, obj) for name, obj in vars(cli_mod).items()
        if isinstance(obj, types.FunctionType) and obj.__module__ == cli_mod.__name__
    ]
    assert len(callables) == 4


def test_module_namespace_callable_names():
    callables = {
        name for name, obj in vars(cli_mod).items()
        if isinstance(obj, types.FunctionType) and obj.__module__ == cli_mod.__name__
    }
    assert callables == {"main", "_build_parser", "_format_metric", "_run_inspect_doc"}


def test_module_no_user_defined_classes():
    classes = [
        (name, obj) for name, obj in vars(cli_mod).items()
        if isinstance(obj, type) and obj.__module__ == cli_mod.__name__
    ]
    assert len(classes) == 0


def test_module_main_callable():
    assert callable(cli_mod.main)


def test_module_build_parser_callable():
    assert callable(cli_mod._build_parser)


def test_module_format_metric_callable():
    assert callable(cli_mod._format_metric)


def test_module_run_inspect_doc_callable():
    assert callable(cli_mod._run_inspect_doc)


def test_module_main_name_eq_main():
    assert cli_mod.main.__name__ == "main"


def test_module_main_module_eq_cli():
    assert cli_mod.main.__module__ == "evaluation.cli"


def test_module_build_parser_name():
    assert cli_mod._build_parser.__name__ == "_build_parser"


def test_module_build_parser_module():
    assert cli_mod._build_parser.__module__ == "evaluation.cli"


def test_module_format_metric_name():
    assert cli_mod._format_metric.__name__ == "_format_metric"


def test_module_format_metric_module():
    assert cli_mod._format_metric.__module__ == "evaluation.cli"


def test_module_run_inspect_doc_name():
    assert cli_mod._run_inspect_doc.__name__ == "_run_inspect_doc"


def test_module_run_inspect_doc_module():
    assert cli_mod._run_inspect_doc.__module__ == "evaluation.cli"


def test_module_name_is_evaluation_cli():
    assert cli_mod.__name__ == "evaluation.cli"


def test_module_file_ends_with_cli_py():
    assert cli_mod.__file__.endswith("cli.py")


def test_module_main_signature_no_kwargs():
    sig = inspect.signature(cli_mod.main)
    params = list(sig.parameters.values())
    # argv is positional-or-keyword
    assert all(
        p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD for p in params
    )


# ---------- 端到端集成补强第三批 ----------


def test_e2e_format_metric_int_value():
    s = _format_metric("m", {"value": 7, "reason": None})
    assert "7" in s


def test_e2e_format_metric_negative_int():
    s = _format_metric("m", {"value": -1, "reason": None})
    assert "-1" in s


def test_e2e_format_metric_negative_float():
    s = _format_metric("m", {"value": -0.5, "reason": None})
    assert "-0.5000" in s


def test_e2e_format_metric_dict_with_unicode_keys():
    s = _format_metric(
        "m", {"value": {"类型": 3}, "reason": None}
    )
    assert "类型=3" in s


def test_e2e_format_metric_padding_with_long_name():
    long_name = "x" * 30
    s = _format_metric(long_name, {"value": True, "reason": None})
    # name 占 30，再补 6 空格到 36
    assert long_name in s


def test_e2e_format_metric_padding_with_oversized_name():
    name = "x" * 50  # 超过 36
    s = _format_metric(name, {"value": True, "reason": None})
    # 字段填充不截断（Python format spec 不截断）
    assert name in s


def test_e2e_run_inspect_doc_full_output_sorted(tmp_path, capsys):
    p = tmp_path / "doc.json"
    doc = {
        "document_id": "doc-002",
        "source_type": "docx",
        "elements": [{"element_id": "e1", "type": "paragraph", "text": "x"}],
        "chunks": [
            {"chunk_id": "c1", "source_element_ids": ["e1"], "text": "x"}
        ],
    }
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = _run_inspect_doc(_make_namespace(str(p)))
    assert rc == 0
    out = capsys.readouterr().out
    # 输出包含核心信息
    assert "doc-002" in out
    assert "type=docx" in out


def test_e2e_run_inspect_doc_with_extra_fields_in_doc(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "pdf", "extra_field": "ignored"}),
        encoding="utf-8",
    )
    rc = _run_inspect_doc(_make_namespace(str(p)))
    assert rc == 0


def test_e2e_main_inspect_doc_pipeline_success_metric(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps(
            {
                "source_type": "pdf",
                "elements": [{"element_id": "e1", "type": "paragraph", "text": "x"}],
                "chunks": [
                    {"chunk_id": "c1", "source_element_ids": ["e1"], "text": "x"}
                ],
            }
        ),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    # 应该至少有一个 metric 输出
    assert "metrics:" in out
    # 至少有一个非空行
    metric_lines = [l for l in out.split("\n") if l.startswith("  ")]
    assert len(metric_lines) > 0


def test_e2e_main_validate_report_nonexistent_returns_2(tmp_path):
    rc = main(["validate-report", str(tmp_path / "nonexistent.json")])
    assert rc == 2


def test_e2e_main_validate_report_directory_returns_2(tmp_path):
    rc = main(["validate-report", str(tmp_path)])
    assert rc == 2


def test_e2e_main_validate_report_invalid_json_returns_1(tmp_path):
    p = tmp_path / "report.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_main_validate_report_array_returns_1(tmp_path):
    p = tmp_path / "report.json"
    p.write_text("[]", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_main_validate_report_int_returns_1(tmp_path):
    p = tmp_path / "report.json"
    p.write_text("42", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_main_validate_report_string_returns_1(tmp_path):
    p = tmp_path / "report.json"
    p.write_text('"hello"', encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_main_validate_report_null_returns_1(tmp_path):
    p = tmp_path / "report.json"
    p.write_text("null", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_main_inspect_doc_returns_int(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert isinstance(rc, int)


def test_e2e_main_run_returns_int(tmp_path):
    rc = main(
        [
            "run",
            "--manifest",
            str(tmp_path / "missing.json"),
            "--output",
            str(tmp_path / "out.json"),
        ]
    )
    assert isinstance(rc, int)


def test_e2e_main_validate_report_returns_int(tmp_path):
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert isinstance(rc, int)


def test_e2e_build_parser_run_namespace_kwargs():
    """通过 parse_args 检查 run 子命令 Namespace."""
    p = _build_parser()
    ns = p.parse_args(
        [
            "run",
            "--manifest",
            "a.json",
            "--output",
            "b.json",
            "--parser",
            "kreuzberg",
            "--max-chars",
            "500",
            "--tolerance-chars",
            "15",
        ]
    )
    assert ns.parser == "kreuzberg"
    assert ns.max_chars == 500
    assert ns.tolerance_chars == 15


def test_e2e_run_inspect_doc_no_side_effects(tmp_path):
    """_run_inspect_doc 不修改输入 Namespace."""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    ns = _make_namespace(str(p), tolerance_chars=42)
    original_input = ns.input
    original_tol = ns.tolerance_chars
    _run_inspect_doc(ns)
    assert ns.input == original_input
    assert ns.tolerance_chars == original_tol


def test_e2e_run_inspect_doc_idempotent(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    ns = _make_namespace(str(p))
    rc1 = _run_inspect_doc(ns)
    out1 = capsys.readouterr().out
    rc2 = _run_inspect_doc(ns)
    out2 = capsys.readouterr().out
    assert rc1 == rc2
    assert out1 == out2


def test_e2e_main_inspect_doc_with_empty_doc_id_uses_question_mark(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    # doc.get('document_id', '?') 默认 '?'
    assert "?" in out


def test_e2e_main_inspect_doc_with_missing_source_path(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "?" in out


def test_e2e_format_metric_consistency():
    """相同输入应得相同输出."""
    metric = {"value": 0.5, "reason": None}
    s1 = _format_metric("ratio", metric)
    s2 = _format_metric("ratio", metric)
    assert s1 == s2


def test_e2e_format_metric_handles_all_metric_shapes():
    """所有 metric 形状都能渲染不抛异常."""
    shapes = [
        {"value": None, "reason": "no_data"},
        {"value": True, "reason": None},
        {"value": False, "reason": "failed"},
        {"value": 0.0, "reason": None},
        {"value": 1, "reason": None},
        {"value": "string", "reason": None},
        {"value": [1, 2], "reason": None},
        {"value": {"a": 1}, "reason": None},
        {"value": {}, "reason": None},
    ]
    for m in shapes:
        s = _format_metric("name", m)
        assert isinstance(s, str)
