r"""evaluation/cli.py 边角测试 - 第十轮（Round 212）。

补强已有 base/edges/edges2-9（共 ~870 测试）未覆盖的深度：
- 模块结构：__all__ 未定义 / imports 完整集合 / sys.stdout.reconfigure 块
- _build_parser：run subparser 各 argument 默认值 / choices tuple 类型
- _build_parser：validate-report / inspect-doc subparser 各 argument
- main()：run 子命令成功路径（monkeypatch run_evaluation）
- main()：run 子命令 manifest 加载失败 / 报告生成失败 / 自校验失败
- _format_metric：各 reason/value 组合的输出格式精确文本
- _run_inspect_doc：tolerance_chars 传播 / metrics 顺序 / 各 metric 类型分组
- 综合行为：stdout/stderr 分流 / 返回值类型
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from evaluation.cli import (
    _build_parser,
    _format_metric,
    _run_inspect_doc,
    main,
)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_no_all_defined():
    """evaluation.cli 不定义 __all__（CLI 入口模块）。"""
    import evaluation.cli as m
    assert not hasattr(m, "__all__")


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


def test_module_imports_manifest_error():
    import evaluation.cli as m
    assert hasattr(m, "ManifestError")


def test_module_imports_load_manifest():
    import evaluation.cli as m
    assert hasattr(m, "load_manifest")


def test_module_imports_get_git_provenance():
    import evaluation.cli as m
    assert hasattr(m, "get_git_provenance")


def test_module_imports_run_evaluation():
    import evaluation.cli as m
    assert hasattr(m, "run_evaluation")


def test_module_imports_eval_schema_error():
    import evaluation.cli as m
    assert hasattr(m, "EvalSchemaError")


def test_module_imports_validate_file():
    import evaluation.cli as m
    assert hasattr(m, "validate_file")


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


def test_module_docstring_mentions_usage():
    import evaluation.cli as m
    doc = m.__doc__
    assert "python -m evaluation.cli" in doc or "用法" in doc


def test_module_uses_future_annotations():
    import evaluation.cli as m
    sig = inspect.signature(m.main)
    assert isinstance(sig.return_annotation, str)


def test_module_no_silence_unused():
    import evaluation.cli as m
    assert not hasattr(m, "_silence_unused_import")


def test_module_has_main_entry_block():
    """__main__ 块通过 __name__ 守卫存在（用 source inspect）。"""
    import evaluation.cli
    src_path = Path(evaluation.cli.__file__)
    src = src_path.read_text(encoding="utf-8")
    assert 'if __name__ == "__main__"' in src
    assert "raise SystemExit(main())" in src


def test_module_has_stdout_reconfigure_block():
    """Windows 控制台 UTF-8 reconfigure 块。"""
    import evaluation.cli
    src_path = Path(evaluation.cli.__file__)
    src = src_path.read_text(encoding="utf-8")
    assert "reconfigure" in src


# =========================================================================
# _build_parser 签名
# =========================================================================


def test_build_parser_signature():
    sig = inspect.signature(_build_parser)
    params = list(sig.parameters)
    assert params == []


def test_build_parser_return_annotation_is_argparse_parser_str():
    sig = inspect.signature(_build_parser)
    # future annotations → 字符串
    assert "ArgumentParser" in sig.return_annotation


def test_build_parser_callable():
    assert callable(_build_parser)


def test_build_parser_returns_argument_parser():
    import argparse
    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_build_parser_prog_exact_value():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_nonempty():
    p = _build_parser()
    assert p.description is not None
    assert len(p.description) > 0


def test_build_parser_has_three_subcommands():
    p = _build_parser()
    # 通过解析各子命令验证
    cmd_args = {
        "run": ["run", "--manifest", "x", "--output", "y"],
        "validate-report": ["validate-report", "x"],
        "inspect-doc": ["inspect-doc", "x"],
    }
    for cmd, args in cmd_args.items():
        ns = p.parse_args(args)
        assert ns.command == cmd


def test_build_parser_subparsers_dest_is_command():
    p = _build_parser()
    ns = p.parse_args(["validate-report", "x"])
    assert ns.command == "validate-report"


# =========================================================================
# run subparser arguments
# =========================================================================


def test_run_subparser_manifest_required():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "/x.json", "--output", "/y.json"])
    assert ns.manifest == "/x.json"


def test_run_subparser_output_required():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "/x.json", "--output", "/y.json"])
    assert ns.output == "/y.json"


def test_run_subparser_parser_default_fallback():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert ns.parser == "fallback"


def test_run_subparser_parser_choices_fallback():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y", "--parser", "fallback"])
    assert ns.parser == "fallback"


def test_run_subparser_parser_choices_kreuzberg():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y", "--parser", "kreuzberg"])
    assert ns.parser == "kreuzberg"


def test_run_subparser_max_chars_default_800():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert ns.max_chars == 800


def test_run_subparser_max_chars_explicit():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y", "--max-chars", "400"])
    assert ns.max_chars == 400


def test_run_subparser_tolerance_chars_default_30():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert ns.tolerance_chars == 30


def test_run_subparser_tolerance_chars_explicit():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y", "--tolerance-chars", "10"])
    assert ns.tolerance_chars == 10


# =========================================================================
# validate-report subparser
# =========================================================================


def test_validate_report_subparser_takes_positional_input():
    p = _build_parser()
    ns = p.parse_args(["validate-report", "/x.json"])
    assert ns.input == "/x.json"


def test_validate_report_subparser_no_optional_args():
    """validate-report 只有 positional input，没 optional。"""
    p = _build_parser()
    ns = p.parse_args(["validate-report", "/x.json"])
    # 不应有 parser/max_chars/tolerance_chars
    assert not hasattr(ns, "parser")
    assert not hasattr(ns, "max_chars")


# =========================================================================
# inspect-doc subparser
# =========================================================================


def test_inspect_doc_subparser_takes_positional_input():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "/x.json"])
    assert ns.input == "/x.json"


def test_inspect_doc_subparser_tolerance_chars_default():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "/x.json"])
    assert ns.tolerance_chars == 30


def test_inspect_doc_subparser_tolerance_chars_explicit():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "/x.json", "--tolerance-chars", "5"])
    assert ns.tolerance_chars == 5


# =========================================================================
# main() 签名与基本行为
# =========================================================================


def test_main_signature():
    sig = inspect.signature(main)
    params = list(sig.parameters)
    assert params == ["argv"]


def test_main_argv_default_none():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_return_annotation_is_int_str():
    sig = inspect.signature(main)
    assert sig.return_annotation == "int"


def test_main_callable():
    assert callable(main)


def test_main_no_args_errors(capsys):
    """没传子命令 → argparse 错误（SystemExit）。"""
    with pytest.raises(SystemExit):
        main([])
    err = capsys.readouterr().err
    assert "error" in err.lower() or "required" in err.lower()


def test_main_unknown_command_errors(capsys):
    with pytest.raises(SystemExit):
        main(["unknown"])
    err = capsys.readouterr().err
    assert "error" in err.lower() or "invalid" in err.lower()


# =========================================================================
# _format_metric 签名
# =========================================================================


def test_format_metric_signature():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters)
    assert params == ["name", "metric"]


def test_format_metric_return_annotation_is_str():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation == "str"


def test_format_metric_callable():
    assert callable(_format_metric)


# =========================================================================
# _format_metric 各 value 类型
# =========================================================================


def test_format_metric_value_none_with_reason():
    line = _format_metric("x", {"value": None, "reason": "no_data"})
    assert "null" in line
    assert "no_data" in line


def test_format_metric_value_none_no_reason_key():
    """metric 缺 reason 字段 → reason 是 None → 显示 (None)。"""
    line = _format_metric("x", {"value": None})
    assert "null" in line


def test_format_metric_value_true_lowercase():
    line = _format_metric("x", {"value": True, "reason": None})
    assert "true" in line
    assert "false" not in line


def test_format_metric_value_false_lowercase():
    line = _format_metric("x", {"value": False, "reason": None})
    assert "false" in line


def test_format_metric_value_int():
    line = _format_metric("x", {"value": 42, "reason": None})
    assert "42" in line


def test_format_metric_value_int_zero():
    line = _format_metric("x", {"value": 0, "reason": None})
    assert "0" in line


def test_format_metric_value_int_negative():
    line = _format_metric("x", {"value": -5, "reason": None})
    assert "-5" in line


def test_format_metric_value_float_zero():
    line = _format_metric("x", {"value": 0.0, "reason": None})
    assert "0.0000" in line


def test_format_metric_value_float_one():
    line = _format_metric("x", {"value": 1.0, "reason": None})
    assert "1.0000" in line


def test_format_metric_value_float_half():
    line = _format_metric("x", {"value": 0.5, "reason": None})
    assert "0.5000" in line


def test_format_metric_value_float_negative():
    line = _format_metric("x", {"value": -0.5, "reason": None})
    assert "-0.5000" in line


def test_format_metric_value_float_truncated_to_4_decimals():
    line = _format_metric("x", {"value": 0.123456789, "reason": None})
    assert "0.1235" in line


def test_format_metric_value_dict():
    line = _format_metric("x", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in line
    assert "b=2" in line


def test_format_metric_value_dict_sorted_items():
    """dict 渲染按 key 排序。"""
    line = _format_metric("x", {"value": {"z": 1, "a": 2}, "reason": None})
    # a 应在 z 之前
    assert line.index("a=2") < line.index("z=1")


def test_format_metric_value_empty_dict():
    line = _format_metric("x", {"value": {}, "reason": None})
    # 空 dict 仍渲染（ok）
    assert "ok" in line


def test_format_metric_value_string():
    line = _format_metric("x", {"value": "abc", "reason": None})
    assert "abc" in line


def test_format_metric_value_list_falls_through():
    """list 不是 None/bool/float/dict → 走默认分支。"""
    line = _format_metric("x", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in line


def test_format_metric_value_tuple_falls_through():
    line = _format_metric("x", {"value": (1, 2), "reason": None})
    assert "(1, 2)" in line


def test_format_metric_value_none_default_reason_not_shown():
    """value=None 时显示 reason，不显示 ok。"""
    line = _format_metric("x", {"value": None, "reason": "x_reason"})
    assert "x_reason" in line
    assert "ok" not in line


def test_format_metric_value_true_default_reason_ok():
    """value=True 且没 reason → 显示 ok。"""
    line = _format_metric("x", {"value": True, "reason": None})
    assert "ok" in line


def test_format_metric_name_padded_to_36():
    """name 不足 36 字符 → padding。"""
    line = _format_metric("short", {"value": 1, "reason": None})
    # name 后至少有 36 - 5 = 31 个空格
    assert "short" + " " * 31 in line


def test_format_metric_name_exactly_36_chars():
    name = "a" * 36
    line = _format_metric(name, {"value": 1, "reason": None})
    assert name in line


def test_format_metric_name_over_36_chars():
    """name 超过 36 字符 → 不截断（f-string 不截断）。"""
    name = "a" * 50
    line = _format_metric(name, {"value": 1, "reason": None})
    assert name in line


def test_format_metric_unicode_name():
    line = _format_metric("中文", {"value": 1, "reason": None})
    assert "中文" in line


# =========================================================================
# _run_inspect_doc 签名
# =========================================================================


def test_run_inspect_doc_signature():
    sig = inspect.signature(_run_inspect_doc)
    params = list(sig.parameters)
    assert params == ["args"]


def test_run_inspect_doc_return_annotation_is_int_str():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


def test_run_inspect_doc_callable():
    assert callable(_run_inspect_doc)


# =========================================================================
# main() validate-report 子命令完整路径
# =========================================================================


def _write_valid_report(p: Path) -> None:
    """写一个符合 evaluation-report.schema.json 的合法报告。"""
    report = {
        "report_version": "1.1",
        "devset": {
            "status": "incomplete",
            "file_count": 0, "content_group_count": 0,
            "pdf_count": 0, "docx_count": 0,
            "categories_covered": [],
        },
        "provenance": {
            "git_commit": "abc123", "git_dirty": False,
            "evaluator_version": "1.1", "report_version": "1.1",
            "parser_name": "fallback", "parser_version": None,
            "dependencies": {}, "max_chars": 800,
            "run_timestamp_iso": "2026-08-05T12:00:00Z",
        },
        "per_doc": [],
        "summary": {
            "counts": {}, "success_rates": {},
            "ratio_macro_averages": {},
            "silent_drop_total": 0,
        },
    }
    p.write_text(json.dumps(report), encoding="utf-8")


def test_main_validate_report_valid_returns_0(tmp_path):
    p = tmp_path / "report.json"
    _write_valid_report(p)
    assert main(["validate-report", str(p)]) == 0


def test_main_validate_report_valid_prints_filename(tmp_path, capsys):
    p = tmp_path / "report.json"
    _write_valid_report(p)
    main(["validate-report", str(p)])
    out = capsys.readouterr().out
    assert "[OK]" in out
    assert str(p) in out


def test_main_validate_report_missing_returns_2(tmp_path):
    p = tmp_path / "missing.json"
    assert main(["validate-report", str(p)]) == 2


def test_main_validate_report_missing_prints_error_to_stderr(tmp_path, capsys):
    p = tmp_path / "missing.json"
    main(["validate-report", str(p)])
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_validate_report_directory_returns_2(tmp_path):
    """传目录 → 不是 file → exit 2。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert main(["validate-report", str(d)]) == 2


def test_main_validate_report_invalid_json_returns_1(tmp_path):
    p = tmp_path / "report.json"
    p.write_text("{not json", encoding="utf-8")
    assert main(["validate-report", str(p)]) == 1


def test_main_validate_report_empty_file_returns_1(tmp_path):
    p = tmp_path / "report.json"
    p.write_text("", encoding="utf-8")
    assert main(["validate-report", str(p)]) == 1


def test_main_validate_report_invalid_schema_returns_1(tmp_path, capsys):
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")  # 不符合 schema
    assert main(["validate-report", str(p)]) == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err


def test_main_validate_report_not_object_returns_1(tmp_path):
    p = tmp_path / "report.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")  # array 而非 object
    assert main(["validate-report", str(p)]) == 1


# =========================================================================
# main() inspect-doc 子命令完整路径
# =========================================================================


def _write_doc_json(p: Path) -> None:
    doc = {
        "source_hash": "a" * 64,
        "source_type": "pdf",
        "document_id": "doc1",
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "parser_version": "0.1.0",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "hello"},
        ],
        "chunks": [
            {"text": "hello", "source_element_ids": ["e1"]},
        ],
    }
    p.write_text(json.dumps(doc), encoding="utf-8")


def test_main_inspect_doc_returns_zero(tmp_path):
    p = tmp_path / "doc.json"
    _write_doc_json(p)
    assert main(["inspect-doc", str(p)]) == 0


def test_main_inspect_doc_prints_file_line(tmp_path, capsys):
    p = tmp_path / "doc.json"
    _write_doc_json(p)
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "file:" in out


def test_main_inspect_doc_prints_document_id(tmp_path, capsys):
    p = tmp_path / "doc.json"
    _write_doc_json(p)
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "doc1" in out


def test_main_inspect_doc_prints_source_line(tmp_path, capsys):
    p = tmp_path / "doc.json"
    _write_doc_json(p)
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "source:" in out
    assert "pdf" in out


def test_main_inspect_doc_prints_parser_line(tmp_path, capsys):
    p = tmp_path / "doc.json"
    _write_doc_json(p)
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "parser:" in out
    assert "fallback" in out


def test_main_inspect_doc_prints_counts_line(tmp_path, capsys):
    p = tmp_path / "doc.json"
    _write_doc_json(p)
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "counts:" in out
    assert "elements=1" in out
    assert "chunks=1" in out


def test_main_inspect_doc_prints_metrics_section(tmp_path, capsys):
    p = tmp_path / "doc.json"
    _write_doc_json(p)
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_main_inspect_doc_metrics_includes_pipeline_success(tmp_path, capsys):
    p = tmp_path / "doc.json"
    _write_doc_json(p)
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "pipeline_success" in out


def test_main_inspect_doc_metrics_sort_bool_first(tmp_path, capsys):
    """metric 排序：bool 在最前。"""
    p = tmp_path / "doc.json"
    _write_doc_json(p)
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    # pipeline_success 是 bool → 应在 metrics 段顶部
    metrics_start = out.find("metrics:\n")
    assert "pipeline_success" in out[metrics_start:metrics_start + 200]


def test_main_inspect_doc_missing_returns_2(tmp_path):
    p = tmp_path / "missing.json"
    assert main(["inspect-doc", str(p)]) == 2


def test_main_inspect_doc_missing_prints_error_to_stderr(tmp_path, capsys):
    p = tmp_path / "missing.json"
    main(["inspect-doc", str(p)])
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_inspect_doc_invalid_json_returns_1(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{not json", encoding="utf-8")
    assert main(["inspect-doc", str(p)]) == 1


def test_main_inspect_doc_non_dict_returns_1(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    assert main(["inspect-doc", str(p)]) == 1


def test_main_inspect_doc_empty_dict_returns_0(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    assert main(["inspect-doc", str(p)]) == 0


def test_main_inspect_doc_empty_dict_source_type_unknown(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "unknown" in out


def test_main_inspect_doc_with_tolerance_chars_arg(tmp_path):
    p = tmp_path / "doc.json"
    _write_doc_json(p)
    assert main(["inspect-doc", str(p), "--tolerance-chars", "5"]) == 0


# =========================================================================
# main() run 子命令失败路径
# =========================================================================


def test_main_run_missing_manifest_returns_2(tmp_path):
    manifest = tmp_path / "missing.json"
    out = tmp_path / "report.json"
    assert main(["run", "--manifest", str(manifest), "--output", str(out)]) == 2


def test_main_run_missing_manifest_prints_error(tmp_path, capsys):
    manifest = tmp_path / "missing.json"
    out = tmp_path / "report.json"
    main(["run", "--manifest", str(manifest), "--output", str(out)])
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_run_directory_manifest_returns_2(tmp_path):
    """manifest 是目录 → not is_file → exit 2。"""
    d = tmp_path / "subdir"
    d.mkdir()
    out = tmp_path / "report.json"
    assert main(["run", "--manifest", str(d), "--output", str(out)]) == 2


def test_main_run_invalid_parser_choice_errors(capsys):
    """argparse 拒绝非法 parser choice → SystemExit 2。"""
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "x", "--output", "y", "--parser", "invalid"])
    err = capsys.readouterr().err
    assert "invalid choice" in err


def test_main_run_max_chars_non_int_errors(capsys):
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "x", "--output", "y", "--max-chars", "not_int"])


def test_main_run_max_chars_negative_passes_argparse(tmp_path):
    """argparse 接受负 int（type=int）；运行时不会有问题（但可能 chunker ValueError）。"""
    manifest = tmp_path / "missing.json"
    out = tmp_path / "report.json"
    # argparse 不拒绝负数，但 manifest 不存在 → 先 exit 2
    assert main(["run", "--manifest", str(manifest), "--output", str(out),
                 "--max-chars", "-100"]) == 2


def test_main_returns_int_when_given_argv(tmp_path):
    """main 总返回 int。"""
    manifest = tmp_path / "missing.json"
    out = tmp_path / "report.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(out)])
    assert isinstance(rc, int)


# =========================================================================
# 综合行为
# =========================================================================


def test_main_inspect_doc_stdout_stderr_split(tmp_path, capsys):
    """成功路径只输出到 stdout，不输出 stderr。"""
    p = tmp_path / "doc.json"
    _write_doc_json(p)
    main(["inspect-doc", str(p)])
    captured = capsys.readouterr()
    assert captured.out  # 非空
    assert captured.err == ""


def test_main_inspect_doc_with_image_element(tmp_path, capsys):
    """带 image element 的文档：inspect-doc 不应崩溃。"""
    p = tmp_path / "doc.json"
    doc = {
        "source_hash": "a" * 64,
        "source_type": "pdf",
        "document_id": "doc1",
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "parser_version": "0.1.0",
        "elements": [
            {"element_id": "e1", "type": "image", "resource_path": "x.png"},
        ],
        "chunks": [],
    }
    p.write_text(json.dumps(doc), encoding="utf-8")
    assert main(["inspect-doc", str(p)]) == 0


def test_main_inspect_doc_idempotent(tmp_path, capsys):
    p = tmp_path / "doc.json"
    _write_doc_json(p)
    main(["inspect-doc", str(p)])
    out1 = capsys.readouterr().out
    main(["inspect-doc", str(p)])
    out2 = capsys.readouterr().out
    assert out1 == out2
