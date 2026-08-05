r"""evaluation/cli.py 边角测试 - 第八轮（Round 195）。

补强已有 base/edges/edges2-7（共 664 测试）未覆盖的深度：
- _build_parser prog/description/formatter/required=True、各 subparser help/choices/default
- main 各错误码完整矩阵（manifest 缺失/ManifestError/EvalSchemaError/run/validate_file）
- _format_metric value 类型边界（None/True/False/int/float 0.0/dict 空/long name padding）
- _run_inspect_doc stdout 输出顺序、metric 排序键、source_type 默认、空 elements/chunks
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import argparse
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


class _FakeArgs:
    """模拟 argparse.Namespace。"""

    def __init__(self, input: str = "", tolerance_chars: int = 30):
        self.input = input
        self.tolerance_chars = tolerance_chars


# =========================================================================
# _build_parser 深度
# =========================================================================


def test_build_parser_prog_is_evaluation_cli():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_nonempty():
    p = _build_parser()
    assert p.description is not None
    assert len(p.description) > 0


def test_build_parser_formatter_raw_description():
    p = _build_parser()
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_has_subparsers():
    p = _build_parser()
    sub_actions = [
        a for a in p._subparsers._group_actions if hasattr(a, "choices")
    ]
    assert len(sub_actions) == 1


def test_build_parser_subparsers_required_true():
    """无子命令时 argparse 应报错（required=True）。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._subparsers._group_actions if hasattr(a, "choices")
    ]
    assert sub_actions[0].required is True


def test_build_parser_subparsers_dest_is_command():
    p = _build_parser()
    sub_actions = [
        a for a in p._subparsers._group_actions if hasattr(a, "choices")
    ]
    assert sub_actions[0].dest == "command"


def test_build_parser_three_subcommands():
    p = _build_parser()
    sub_actions = [
        a for a in p._subparsers._group_actions if hasattr(a, "choices")
    ]
    choices = set(sub_actions[0].choices.keys())
    assert choices == {"run", "validate-report", "inspect-doc"}


def test_build_parser_run_manifest_required():
    p = _build_parser()
    sub = [a for a in p._subparsers._group_actions if hasattr(a, "choices")][0]
    run_p = sub.choices["run"]
    manifest_arg = next(a for a in run_p._actions if a.dest == "manifest")
    assert manifest_arg.required is True


def test_build_parser_run_output_required():
    p = _build_parser()
    sub = [a for a in p._subparsers._group_actions if hasattr(a, "choices")][0]
    run_p = sub.choices["run"]
    output_arg = next(a for a in run_p._actions if a.dest == "output")
    assert output_arg.required is True


def test_build_parser_run_parser_default_fallback():
    p = _build_parser()
    sub = [a for a in p._subparsers._group_actions if hasattr(a, "choices")][0]
    run_p = sub.choices["run"]
    parser_arg = next(a for a in run_p._actions if a.dest == "parser")
    assert parser_arg.default == "fallback"


def test_build_parser_run_parser_choices():
    p = _build_parser()
    sub = [a for a in p._subparsers._group_actions if hasattr(a, "choices")][0]
    run_p = sub.choices["run"]
    parser_arg = next(a for a in run_p._actions if a.dest == "parser")
    assert set(parser_arg.choices) == {"fallback", "kreuzberg"}


def test_build_parser_run_max_chars_default_800():
    p = _build_parser()
    sub = [a for a in p._subparsers._group_actions if hasattr(a, "choices")][0]
    run_p = sub.choices["run"]
    mc_arg = next(a for a in run_p._actions if a.dest == "max_chars")
    assert mc_arg.default == 800


def test_build_parser_run_max_chars_type_int():
    p = _build_parser()
    sub = [a for a in p._subparsers._group_actions if hasattr(a, "choices")][0]
    run_p = sub.choices["run"]
    mc_arg = next(a for a in run_p._actions if a.dest == "max_chars")
    assert mc_arg.type is int


def test_build_parser_run_tolerance_chars_default_30():
    p = _build_parser()
    sub = [a for a in p._subparsers._group_actions if hasattr(a, "choices")][0]
    run_p = sub.choices["run"]
    tc_arg = next(a for a in run_p._actions if a.dest == "tolerance_chars")
    assert tc_arg.default == 30


def test_build_parser_validate_report_input_required():
    p = _build_parser()
    sub = [a for a in p._subparsers._group_actions if hasattr(a, "choices")][0]
    val_p = sub.choices["validate-report"]
    input_arg = next(a for a in val_p._actions if a.dest == "input")
    assert input_arg.required is True


def test_build_parser_inspect_doc_input_required():
    p = _build_parser()
    sub = [a for a in p._subparsers._group_actions if hasattr(a, "choices")][0]
    ins_p = sub.choices["inspect-doc"]
    input_arg = next(a for a in ins_p._actions if a.dest == "input")
    assert input_arg.required is True


def test_build_parser_inspect_doc_tolerance_chars_default_30():
    p = _build_parser()
    sub = [a for a in p._subparsers._group_actions if hasattr(a, "choices")][0]
    ins_p = sub.choices["inspect-doc"]
    tc_arg = next(a for a in ins_p._actions if a.dest == "tolerance_chars")
    assert tc_arg.default == 30


def test_build_parser_run_max_chars_help_text():
    p = _build_parser()
    sub = [a for a in p._subparsers._group_actions if hasattr(a, "choices")][0]
    run_p = sub.choices["run"]
    mc_arg = next(a for a in run_p._actions if a.dest == "max_chars")
    assert mc_arg.help is not None
    assert "800" in mc_arg.help


def test_build_parser_run_parser_help_text():
    p = _build_parser()
    sub = [a for a in p._subparsers._group_actions if hasattr(a, "choices")][0]
    run_p = sub.choices["run"]
    parser_arg = next(a for a in run_p._actions if a.dest == "parser")
    assert parser_arg.help is not None
    assert "fallback" in parser_arg.help


# =========================================================================
# main 错误码完整矩阵
# =========================================================================


def test_main_no_args_prints_usage_and_errors(capsys):
    """无子命令（argv=[]）→ argparse error → SystemExit。"""
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == 2


def test_main_unknown_command_errors(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["foobar"])
    assert excinfo.value.code == 2


def test_main_run_missing_manifest_returns_2(tmp_path: Path, capsys):
    """manifest 文件不存在 → exit 2。"""
    missing = tmp_path / "missing.json"
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(missing), "--output", str(output)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err
    assert "清单不存在" in err


def test_main_run_manifest_directory_returns_2(tmp_path: Path, capsys):
    """manifest 是目录 → is_file()=False → exit 2。"""
    d = tmp_path / "sub"
    d.mkdir()
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(d), "--output", str(output)])
    assert rc == 2


def test_main_validate_report_missing_file_returns_2(tmp_path: Path, capsys):
    missing = tmp_path / "missing.json"
    rc = main(["validate-report", str(missing)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err
    assert "报告不存在" in err


def test_main_validate_report_directory_returns_2(tmp_path: Path, capsys):
    d = tmp_path / "sub"
    d.mkdir()
    rc = main(["validate-report", str(d)])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_1(tmp_path: Path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON 解析失败" in err


def test_main_validate_report_empty_file_returns_1(tmp_path: Path, capsys):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_not_object_returns_1(tmp_path: Path, capsys):
    """JSON 顶层是 list → 校验失败。"""
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_missing_file_returns_2(tmp_path: Path, capsys):
    missing = tmp_path / "missing.json"
    rc = main(["inspect-doc", str(missing)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "文档不存在" in err


def test_main_inspect_doc_directory_returns_2(tmp_path: Path, capsys):
    d = tmp_path / "sub"
    d.mkdir()
    rc = main(["inspect-doc", str(d)])
    assert rc == 2


def test_main_inspect_doc_invalid_json_returns_1(tmp_path: Path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON 解析失败" in err


def test_main_inspect_doc_non_dict_returns_1(tmp_path: Path, capsys):
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON 顶层不是对象" in err


def test_main_inspect_doc_empty_dict_returns_0(tmp_path: Path, capsys):
    """空 dict → 仍可跑（elements/chunks 默认 []）。"""
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_run_invalid_parser_choice_errors(tmp_path: Path, capsys):
    """--parser 不在 choices → argparse error → SystemExit 2。"""
    manifest = tmp_path / "m.json"
    manifest.write_text("{}", encoding="utf-8")
    output = tmp_path / "out.json"
    with pytest.raises(SystemExit) as excinfo:
        main([
            "run", "--manifest", str(manifest), "--output", str(output),
            "--parser", "nonexistent_parser",
        ])
    assert excinfo.value.code == 2


def test_main_run_negative_max_chars_passes_argparse(tmp_path: Path, capsys):
    """argparse 不验证值域，负值能通过 argparse。"""
    manifest = tmp_path / "m.json"
    manifest.write_text("{}", encoding="utf-8")
    output = tmp_path / "out.json"
    rc = main([
        "run", "--manifest", str(manifest), "--output", str(output),
        "--max-chars", "-1",
    ])
    # 走到 manifest 加载失败（清单空）→ exit 1
    assert rc == 1


# =========================================================================
# _format_metric value 类型边界
# =========================================================================


def test_format_metric_value_none():
    s = _format_metric("foo", {"value": None, "reason": "no_data"})
    assert "null" in s
    assert "no_data" in s


def test_format_metric_value_none_no_reason():
    s = _format_metric("foo", {"value": None, "reason": None})
    assert "null" in s
    # reason 显示 None（原样）
    assert "(None)" in s


def test_format_metric_value_true_lowercase():
    s = _format_metric("foo", {"value": True, "reason": None})
    assert "true" in s
    assert "ok" in s


def test_format_metric_value_false_lowercase():
    s = _format_metric("foo", {"value": False, "reason": None})
    assert "false" in s


def test_format_metric_value_true_with_reason():
    s = _format_metric("foo", {"value": True, "reason": "custom"})
    # 有 reason 仍显示 reason 而非 'ok'
    assert "custom" in s


def test_format_metric_value_float_four_decimals():
    s = _format_metric("foo", {"value": 0.123456789, "reason": None})
    assert "0.1235" in s


def test_format_metric_value_float_zero():
    s = _format_metric("foo", {"value": 0.0, "reason": None})
    assert "0.0000" in s


def test_format_metric_value_float_one():
    s = _format_metric("foo", {"value": 1.0, "reason": None})
    assert "1.0000" in s


def test_format_metric_value_int():
    s = _format_metric("foo", {"value": 42, "reason": None})
    assert "42" in s
    assert "ok" in s


def test_format_metric_value_zero_int():
    s = _format_metric("foo", {"value": 0, "reason": None})
    assert " 0 " in s or s.rstrip().endswith("0")


def test_format_metric_value_negative_int():
    s = _format_metric("foo", {"value": -5, "reason": None})
    assert "-5" in s


def test_format_metric_value_dict():
    s = _format_metric("foo", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in s
    assert "b=2" in s


def test_format_metric_value_dict_sorted_by_key():
    """dict value 时按 key 排序输出 items。"""
    s = _format_metric("foo", {"value": {"z": 1, "a": 2, "m": 3}, "reason": None})
    # 出现顺序应为 a, m, z
    a_pos = s.find("a=")
    m_pos = s.find("m=")
    z_pos = s.find("z=")
    assert a_pos < m_pos < z_pos


def test_format_metric_value_empty_dict():
    s = _format_metric("foo", {"value": {}, "reason": None})
    # 空 dict → items 是空字符串
    assert "()" not in s  # 没有空括号
    # 但仍含 reason 'ok'
    assert "ok" in s


def test_format_metric_value_dict_with_string_values():
    s = _format_metric("foo", {"value": {"x": "hello"}, "reason": None})
    assert "x=hello" in s


def test_format_metric_value_string():
    """str value 走最后的 default 分支。"""
    s = _format_metric("foo", {"value": "hello", "reason": None})
    assert "hello" in s


def test_format_metric_value_list():
    """list value 走 default 分支（str(value)）。"""
    s = _format_metric("foo", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in s


def test_format_metric_long_name_padded():
    """name 不足 36 字符时被填充到 36。"""
    s = _format_metric("a", {"value": 1, "reason": None})
    # name 'a' + 35 个空格 = 36 字符
    lines = s.split("\n")
    assert lines[0].startswith("  a")
    assert len(lines[0]) >= 36 + 2  # 加上 prefix '  '


def test_format_metric_exact_36_char_name():
    """name 长度恰好 36 → 不补空格也不截断。"""
    name = "a" * 36
    s = _format_metric(name, {"value": 1, "reason": None})
    # name + 至少 1 空格分隔
    assert name in s


def test_format_metric_over_36_char_name():
    """name 超过 36 字符 → format 仍包含全名（不截断）。"""
    name = "a" * 50
    s = _format_metric(name, {"value": 1, "reason": None})
    assert name in s


def test_format_metric_unicode_name():
    """Unicode name 应能渲染。"""
    s = _format_metric("指标", {"value": 0.5, "reason": None})
    assert "指标" in s
    assert "0.5000" in s


# =========================================================================
# _run_inspect_doc 输出深度
# =========================================================================


def _write_minimal_doc(tmp_path: Path) -> Path:
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_hash": "a" * 64,
        "source_type": "text",
        "document_id": "doc-x",
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
        "warnings": [],
        "parser_name": "text",
        "parser_version": "0.1.0",
    }), encoding="utf-8")
    return p


def test_run_inspect_doc_prints_file_line(tmp_path: Path, capsys):
    p = _write_minimal_doc(tmp_path)
    args = _FakeArgs(input=str(p))
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "file:" in out
    assert str(p) in out


def test_run_inspect_doc_prints_document_id(tmp_path: Path, capsys):
    p = _write_minimal_doc(tmp_path)
    args = _FakeArgs(input=str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "document_id:" in out
    assert "doc-x" in out


def test_run_inspect_doc_prints_source_line(tmp_path: Path, capsys):
    p = _write_minimal_doc(tmp_path)
    args = _FakeArgs(input=str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "source:" in out
    assert "type=text" in out


def test_run_inspect_doc_prints_parser_line(tmp_path: Path, capsys):
    p = _write_minimal_doc(tmp_path)
    args = _FakeArgs(input=str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "parser:" in out
    assert "text" in out
    assert "v0.1.0" in out


def test_run_inspect_doc_prints_counts_line(tmp_path: Path, capsys):
    p = _write_minimal_doc(tmp_path)
    args = _FakeArgs(input=str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "counts:" in out
    assert "elements=" in out
    assert "chunks=" in out


def test_run_inspect_doc_prints_metrics_header(tmp_path: Path, capsys):
    p = _write_minimal_doc(tmp_path)
    args = _FakeArgs(input=str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_prints_metric_lines_after_header(tmp_path: Path, capsys):
    p = _write_minimal_doc(tmp_path)
    args = _FakeArgs(input=str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    # 至少有 pipeline_success / schema_valid 等
    assert "pipeline_success" in out
    assert "schema_valid" in out


def test_run_inspect_doc_missing_document_id_uses_question_mark(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_hash": "a" * 64,
        "source_type": "text",
        "elements": [],
        "chunks": [],
        "warnings": [],
        "parser_name": "text",
        "parser_version": "0.1.0",
    }), encoding="utf-8")
    args = _FakeArgs(input=str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "??" in out or "?" in out  # doc.get('document_id', '?')


def test_run_inspect_doc_missing_parser_name_uses_question_mark(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_hash": "a" * 64,
        "source_type": "text",
        "document_id": "doc-x",
        "elements": [],
        "chunks": [],
        "warnings": [],
    }), encoding="utf-8")
    args = _FakeArgs(input=str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    # parser_name 缺失 → '?'；version 缺失 → '?'
    assert "v?" in out


def test_run_inspect_doc_source_type_default_unknown(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_hash": "a" * 64,
        # 无 source_type
        "document_id": "doc-x",
        "elements": [],
        "chunks": [],
        "warnings": [],
    }), encoding="utf-8")
    args = _FakeArgs(input=str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "type=unknown" in out


def test_run_inspect_doc_metric_sort_order(tmp_path: Path, capsys):
    """排序：bool/int|float/dict|null 顺序，每组内按 name 字典序。"""
    p = _write_minimal_doc(tmp_path)
    args = _FakeArgs(input=str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    # pipeline_success (bool) 应在 element_count_total (int) 之前
    success_pos = out.find("pipeline_success")
    total_pos = out.find("element_count_total")
    assert success_pos < total_pos


def test_run_inspect_doc_metric_nulls_last(tmp_path: Path, capsys):
    """null 值的 metric 排在最后。"""
    p = _write_minimal_doc(tmp_path)
    args = _FakeArgs(input=str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    # pdf_locator_valid_ratio 应是 null（source_type='text'）
    # 应该在最后区段
    pdf_pos = out.find("pdf_locator_valid_ratio")
    success_pos = out.find("pipeline_success")
    assert pdf_pos > success_pos


def test_run_inspect_doc_empty_doc_prints_zero_counts(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_hash": "a" * 64,
        "source_type": "text",
        "document_id": "doc-empty",
        "elements": [],
        "chunks": [],
        "warnings": [],
        "parser_name": "text",
        "parser_version": "0.1.0",
    }), encoding="utf-8")
    args = _FakeArgs(input=str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "elements=0" in out
    assert "chunks=0" in out


def test_run_inspect_doc_no_elements_key(tmp_path: Path, capsys):
    """doc 没有 elements 键 → 默认 []。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_hash": "a" * 64,
        "source_type": "text",
        "document_id": "doc-x",
        "chunks": [],
        "warnings": [],
    }), encoding="utf-8")
    args = _FakeArgs(input=str(p))
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_no_chunks_key(tmp_path: Path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_hash": "a" * 64,
        "source_type": "text",
        "document_id": "doc-x",
        "elements": [],
        "warnings": [],
    }), encoding="utf-8")
    args = _FakeArgs(input=str(p))
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_with_tolerance_chars(tmp_path: Path, capsys):
    p = _write_minimal_doc(tmp_path)
    args = _FakeArgs(input=str(p), tolerance_chars=100)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    # 应包含 chunk_boundary_* metric
    assert "chunk_boundary" in out


def test_run_inspect_doc_default_tolerance_chars_30(tmp_path: Path, capsys):
    p = _write_minimal_doc(tmp_path)
    args = _FakeArgs(input=str(p))  # 默认 30
    rc = _run_inspect_doc(args)
    assert rc == 0


# =========================================================================
# 模块结构与签名
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


def test_build_parser_signature():
    sig = inspect.signature(_build_parser)
    assert set(sig.parameters) == set()  # 无参数


def test_main_signature():
    sig = inspect.signature(main)
    assert set(sig.parameters) == {"argv"}
    assert sig.parameters["argv"].default is None


def test_main_return_annotation_int():
    sig = inspect.signature(main)
    assert "int" in str(sig.return_annotation)


def test_format_metric_signature():
    sig = inspect.signature(_format_metric)
    assert set(sig.parameters) == {"name", "metric"}


def test_format_metric_return_annotation_str():
    sig = inspect.signature(_format_metric)
    assert "str" in str(sig.return_annotation)


def test_run_inspect_doc_signature():
    sig = inspect.signature(_run_inspect_doc)
    assert set(sig.parameters) == {"args"}


def test_run_inspect_doc_return_annotation_int():
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in str(sig.return_annotation)


def test_build_parser_callable():
    assert callable(_build_parser)


def test_main_callable():
    assert callable(main)


def test_format_metric_callable():
    assert callable(_format_metric)


def test_run_inspect_doc_callable():
    assert callable(_run_inspect_doc)


# =========================================================================
# idempotency
# =========================================================================


def test_build_parser_idempotent():
    a = _build_parser()
    b = _build_parser()
    # 两个独立 parser 实例
    assert a is not b
    assert a.prog == b.prog


def test_format_metric_idempotent():
    a = _format_metric("foo", {"value": 1, "reason": None})
    b = _format_metric("foo", {"value": 1, "reason": None})
    assert a == b


def test_main_idempotent_validate_report(tmp_path: Path, capsys):
    """同样的 missing file 两次跑 → 同样 exit code。"""
    missing = tmp_path / "missing.json"
    rc1 = main(["validate-report", str(missing)])
    capsys.readouterr()  # 清空
    rc2 = main(["validate-report", str(missing)])
    assert rc1 == rc2 == 2


# =========================================================================
# 综合行为
# =========================================================================


def test_main_inspect_doc_full_pipeline(tmp_path: Path, capsys):
    """完整 inspect-doc：合法 doc → exit 0 + 5 行元信息 + metrics 列表。"""
    p = _write_minimal_doc(tmp_path)
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "file:" in out
    assert "document_id:" in out
    assert "source:" in out
    assert "parser:" in out
    assert "counts:" in out
    assert "metrics:" in out


def test_main_inspect_doc_via_main_with_tolerance(tmp_path: Path, capsys):
    p = _write_minimal_doc(tmp_path)
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "50"])
    assert rc == 0


def test_format_metric_value_dict_with_int_and_str_values():
    """dict 中混合 int/str value。"""
    s = _format_metric("foo", {"value": {"a": 1, "b": "x"}, "reason": None})
    assert "a=1" in s
    assert "b=x" in s


def test_format_metric_value_dict_with_none_value():
    """dict 中 None value → 'None' 字符串。"""
    s = _format_metric("foo", {"value": {"a": None}, "reason": None})
    assert "a=None" in s


def test_format_metric_value_dict_with_bool_value():
    s = _format_metric("foo", {"value": {"a": True, "b": False}, "reason": None})
    assert "a=True" in s
    assert "b=False" in s


def test_main_no_argv_uses_sys_argv(monkeypatch, capsys):
    """argv=None → 用 sys.argv[1:]。模拟空 sys.argv → argparse error。"""
    monkeypatch.setattr("sys.argv", ["evaluation.cli"])
    with pytest.raises(SystemExit) as excinfo:
        main(None)
    assert excinfo.value.code == 2


def test_main_inspect_doc_with_image_element(tmp_path: Path, capsys):
    """含 image element 的 doc → image_resource_exists_ratio null。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_hash": "a" * 64,
        "source_type": "pdf",
        "document_id": "doc-x",
        "elements": [
            {"element_id": "i1", "type": "image", "resource_path": "x.png"},
        ],
        "chunks": [],
        "warnings": [],
        "parser_name": "fallback",
        "parser_version": "0.1.0",
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "image_resource_exists_ratio" in out
