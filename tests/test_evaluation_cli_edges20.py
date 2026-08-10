r"""evaluation/cli.py 边角测试 - 第二十轮（Round 283）。

edges19 已覆盖：_format_metric 精确字符串 / _run_inspect_doc _sort_key / 懒加载 / main argv=None /
_SubParsersAction 类型 / import 顺序 / docstring 内容 / 错误信息到 stderr / inspect-doc 行为 /
build_parser prog/description/formatter_class/conflict_handler/add_help/allow_abbrev / main block。

edges20 补强未覆盖的角度（exit codes + 集成 + sub-parser 参数）：
- **main exit codes**：run valid→0；run missing manifest→2；run malformed manifest→1；
  validate-report valid→0；validate-report invalid→1；validate-report missing→2；
  inspect-doc valid→0；inspect-doc invalid JSON→1；inspect-doc missing→2；inspect-doc top-level non-dict→1
- **run round-trip 集成**：写真实 manifest → 跑 main(['run', ...]) → 报告文件存在 → 内容含 report_version
- **validate-report round-trip**：写合法报告 → validate-report 通过
- **inspect-doc round-trip**：写合法 document → inspect-doc 通过 → stdout 含 metrics
- **sub-parser 参数精确**：run 的 --manifest required；--output required；--parser choices 精确；
  --parser default 'fallback'；--max-chars type=int default=800；--tolerance-chars type=int default=30；
  validate-report 的 input positional；inspect-doc 的 input positional + --tolerance-chars default=30
- **argparse 错误**：无 command → SystemExit；未知 command → SystemExit；run 缺 --manifest → SystemExit
- **_format_metric 长名称对齐**：name 超过 36 字符也输出（width 36 是 min）
- **_format_metric 空 dict**：{} → 输出空 string after width
- **inspect-doc 排序行为**：bool metrics 在前，再 int/float，再 dict，再 null
- **main 输出到 stdout vs stderr**：成功消息到 stdout；错误消息到 stderr
- **Windows stdout reconfigure 块**：source 含 hasattr(sys.stdout, 'reconfigure')
- **build_parser 子 parser 数**：3 个（run/validate-report/inspect-doc）
- **module source 不含禁止 imports**：os/sys（除了 sys import 本身）/logging/subprocess/asyncio/threading/concurrent
- **__all__ 不存在**（cli 模块没有 __all__）
- **module docstring 含三个子命令名**
- **main return value 类型**：始终 int（不是 None）
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# =========================================================================
# 辅助：构造合法的 manifest / report / document
# =========================================================================


def _write_minimal_manifest(tmp_path: Path) -> Path:
    """写一个最小可用 manifest，返回路径。"""
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    return p


def _write_valid_report(tmp_path: Path) -> Path:
    """写一个最小可用 evaluation-report，返回路径。"""
    p = tmp_path / "report.json"
    p.write_text(json.dumps({
        "report_version": "1.1",
        "provenance": {
            "git_commit": None,
            "git_dirty": True,
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
    }), encoding="utf-8")
    return p


def _write_minimal_document(tmp_path: Path) -> Path:
    """写一个最小 document JSON，返回路径。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "source_hash": "abc123",
        "document_id": "test-doc",
        "source_path": "/tmp/test.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0.0",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "hello",
             "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]},
        ],
    }), encoding="utf-8")
    return p


# =========================================================================
# main exit codes - run 子命令
# =========================================================================


def test_main_run_valid_manifest_exit_zero(tmp_path):
    """run + 合法 manifest → exit 0。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(output)])
    assert rc == 0


def test_main_run_missing_manifest_exit_two(tmp_path):
    """run + manifest 不存在 → exit 2。"""
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(tmp_path / "missing.json"), "--output", str(output)])
    assert rc == 2


def test_main_run_malformed_manifest_exit_one(tmp_path):
    """run + 非法 JSON → exit 1（ManifestError 路径）。"""
    bad_manifest = tmp_path / "bad.json"
    bad_manifest.write_text("{not valid json", encoding="utf-8")
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(bad_manifest), "--output", str(output)])
    assert rc == 1


def test_main_run_invalid_manifest_schema_exit_one(tmp_path):
    """run + manifest schema 失败 → exit 1（EvalSchemaError 路径）。"""
    bad_manifest = tmp_path / "bad.json"
    bad_manifest.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        # 缺 documents → schema 失败
    }), encoding="utf-8")
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(bad_manifest), "--output", str(output)])
    assert rc == 1


def test_main_run_writes_report_file(tmp_path):
    """run 成功后应在 output 路径产生 report JSON。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    assert output.is_file()
    # 内容应含 report_version
    with output.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert "report_version" in data


def test_main_run_stdout_success_message(tmp_path, capsys):
    """run 成功后 stdout 含 [OK]。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(output)])
    captured = capsys.readouterr()
    assert "[OK]" in captured.out
    assert "documents=" in captured.out


def test_main_run_stderr_error_message_missing_manifest(tmp_path, capsys):
    """run + manifest 不存在 → stderr 含 [ERROR]。"""
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(tmp_path / "missing.json"), "--output", str(output)])
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_main_run_with_custom_parser(tmp_path):
    """run --parser kreuzberg 不报错（即使 parser 失败也是 exit 0；这里 manifest 空，不实际跑）。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(output),
               "--parser", "kreuzberg"])
    # 空 manifest → 不实际 parse → exit 0
    assert rc == 0


def test_main_run_with_custom_max_chars(tmp_path):
    """run --max-chars 500 不报错。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(output),
               "--max-chars", "500"])
    assert rc == 0


def test_main_run_with_custom_tolerance_chars(tmp_path):
    """run --tolerance-chars 50 不报错。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(output),
               "--tolerance-chars", "50"])
    assert rc == 0


def test_main_run_invalid_parser_choice_exits(tmp_path):
    """run --parser unknown → argparse SystemExit(2)。"""
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    with pytest.raises(SystemExit) as e:
        main(["run", "--manifest", str(manifest), "--output", str(output),
              "--parser", "unknown"])
    assert e.value.code == 2


def test_main_run_missing_manifest_arg_exits(tmp_path):
    """run 缺 --manifest → argparse SystemExit(2)。"""
    output = tmp_path / "out.json"
    with pytest.raises(SystemExit) as e:
        main(["run", "--output", str(output)])
    assert e.value.code == 2


def test_main_run_missing_output_arg_exits(tmp_path):
    """run 缺 --output → argparse SystemExit(2)。"""
    manifest = _write_minimal_manifest(tmp_path)
    with pytest.raises(SystemExit) as e:
        main(["run", "--manifest", str(manifest)])
    assert e.value.code == 2


# =========================================================================
# main exit codes - validate-report 子命令
# =========================================================================


def test_main_validate_report_valid_exit_zero(tmp_path):
    """validate-report + 合法 report → exit 0。"""
    report = _write_valid_report(tmp_path)
    rc = main(["validate-report", str(report)])
    assert rc == 0


def test_main_validate_report_missing_exit_two(tmp_path):
    """validate-report + 文件不存在 → exit 2。"""
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_validate_report_invalid_json_exit_one(tmp_path):
    """validate-report + 非法 JSON → exit 1（JSONDecodeError 路径）。"""
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid", encoding="utf-8")
    rc = main(["validate-report", str(bad)])
    assert rc == 1


def test_main_validate_report_invalid_schema_exit_one(tmp_path):
    """validate-report + 不符合 schema → exit 1。"""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"wrong": "shape"}), encoding="utf-8")
    rc = main(["validate-report", str(bad)])
    assert rc == 1


def test_main_validate_report_stdout_ok_message(tmp_path, capsys):
    """validate-report 成功 → stdout 含 [OK]。"""
    report = _write_valid_report(tmp_path)
    main(["validate-report", str(report)])
    captured = capsys.readouterr()
    assert "[OK]" in captured.out


def test_main_validate_report_stderr_fail_message(tmp_path, capsys):
    """validate-report 失败 → stderr 含 [FAIL]。"""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"wrong": "shape"}), encoding="utf-8")
    main(["validate-report", str(bad)])
    captured = capsys.readouterr()
    assert "[FAIL]" in captured.err


def test_main_validate_report_stderr_missing_message(tmp_path, capsys):
    """validate-report + 文件不存在 → stderr 含 [ERROR]。"""
    main(["validate-report", str(tmp_path / "missing.json")])
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_main_validate_report_missing_input_arg_exits(tmp_path):
    """validate-report 缺 input → SystemExit。"""
    with pytest.raises(SystemExit) as e:
        main(["validate-report"])
    assert e.value.code == 2


# =========================================================================
# main exit codes - inspect-doc 子命令
# =========================================================================


def test_main_inspect_doc_valid_exit_zero(tmp_path):
    """inspect-doc + 合法 document → exit 0。"""
    doc = _write_minimal_document(tmp_path)
    rc = main(["inspect-doc", str(doc)])
    assert rc == 0


def test_main_inspect_doc_missing_exit_two(tmp_path):
    """inspect-doc + 文件不存在 → exit 2。"""
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_inspect_doc_invalid_json_exit_one(tmp_path):
    """inspect-doc + 非法 JSON → exit 1。"""
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid", encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    assert rc == 1


def test_main_inspect_doc_top_level_array_exit_one(tmp_path):
    """inspect-doc + top-level 非 dict → exit 1。"""
    bad = tmp_path / "bad.json"
    bad.write_text("[1, 2, 3]", encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    assert rc == 1


def test_main_inspect_doc_top_level_string_exit_one(tmp_path):
    """inspect-doc + top-level 是 string → exit 1。"""
    bad = tmp_path / "bad.json"
    bad.write_text('"just a string"', encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    assert rc == 1


def test_main_inspect_doc_top_level_int_exit_one(tmp_path):
    """inspect-doc + top-level 是 int → exit 1。"""
    bad = tmp_path / "bad.json"
    bad.write_text("42", encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    assert rc == 1


def test_main_inspect_doc_missing_input_arg_exits(tmp_path):
    """inspect-doc 缺 input → SystemExit。"""
    with pytest.raises(SystemExit) as e:
        main(["inspect-doc"])
    assert e.value.code == 2


def test_main_inspect_doc_with_custom_tolerance_chars(tmp_path):
    """inspect-doc --tolerance-chars 50 → exit 0。"""
    doc = _write_minimal_document(tmp_path)
    rc = main(["inspect-doc", str(doc), "--tolerance-chars", "50"])
    assert rc == 0


def test_main_inspect_doc_stdout_output(tmp_path, capsys):
    """inspect-doc 成功 → stdout 含 file: 与 metrics:"""
    doc = _write_minimal_document(tmp_path)
    main(["inspect-doc", str(doc)])
    captured = capsys.readouterr()
    assert "file:" in captured.out
    assert "metrics:" in captured.out


# =========================================================================
# sub-parser 参数精确验证
# =========================================================================


def test_build_parser_run_manifest_required():
    """run 子 parser 的 --manifest 是 required。"""
    p = _build_parser()
    # 找 run sub-parser
    sub = p._subparsers._group_actions[0]
    run_p = sub.choices["run"]
    manifest_action = next(a for a in run_p._actions if '--manifest' in a.option_strings)
    assert manifest_action.required is True


def test_build_parser_run_output_required():
    """run 子 parser 的 --output 是 required。"""
    p = _build_parser()
    sub = p._subparsers._group_actions[0]
    run_p = sub.choices["run"]
    output_action = next(a for a in run_p._actions if '--output' in a.option_strings)
    assert output_action.required is True


def test_build_parser_run_parser_choices_exact():
    """--parser choices 精确 ('fallback', 'kreuzberg')。"""
    p = _build_parser()
    sub = p._subparsers._group_actions[0]
    run_p = sub.choices["run"]
    parser_action = next(a for a in run_p._actions if '--parser' in a.option_strings)
    assert parser_action.choices == ("fallback", "kreuzberg")


def test_build_parser_run_parser_default_fallback():
    """--parser 默认 'fallback'。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.parser == "fallback"


def test_build_parser_run_max_chars_default_800():
    """--max-chars 默认 800。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.max_chars == 800


def test_build_parser_run_max_chars_type_int():
    """--max-chars type=int。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y", "--max-chars", "500"])
    assert args.max_chars == 500
    assert isinstance(args.max_chars, int)


def test_build_parser_run_tolerance_chars_default_30():
    """run --tolerance-chars 默认 30。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.tolerance_chars == 30


def test_build_parser_run_tolerance_chars_type_int():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y", "--tolerance-chars", "50"])
    assert args.tolerance_chars == 50
    assert isinstance(args.tolerance_chars, int)


def test_build_parser_validate_report_input_positional():
    """validate-report 的 input 是 positional（dest='input'）。"""
    p = _build_parser()
    args = p.parse_args(["validate-report", "my_report.json"])
    assert args.input == "my_report.json"


def test_build_parser_inspect_doc_input_positional():
    """inspect-doc 的 input 是 positional（dest='input'）。"""
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "my_doc.json"])
    assert args.input == "my_doc.json"


def test_build_parser_inspect_doc_tolerance_chars_default_30():
    """inspect-doc --tolerance-chars 默认 30。"""
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "x"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_no_parser_option():
    """inspect-doc 没有 --parser 选项。"""
    p = _build_parser()
    sub = p._subparsers._group_actions[0]
    ins_p = sub.choices["inspect-doc"]
    parser_actions = [a for a in ins_p._actions if '--parser' in a.option_strings]
    assert len(parser_actions) == 0


def test_build_parser_inspect_doc_no_max_chars_option():
    """inspect-doc 没有 --max-chars 选项。"""
    p = _build_parser()
    sub = p._subparsers._group_actions[0]
    ins_p = sub.choices["inspect-doc"]
    mc_actions = [a for a in ins_p._actions if '--max-chars' in a.option_strings]
    assert len(mc_actions) == 0


def test_build_parser_validate_report_no_optional_args():
    """validate-report 没有任何可选参数（只 input positional）。"""
    p = _build_parser()
    sub = p._subparsers._group_actions[0]
    val_p = sub.choices["validate-report"]
    # 除了 help（argparse 自动加的 -h/--help），应该只有 input positional
    optional_actions = [
        a for a in val_p._actions
        if a.option_strings and not set(a.option_strings).issubset({"-h", "--help"})
    ]
    assert len(optional_actions) == 0


# =========================================================================
# build_parser 子 parser 数
# =========================================================================


def test_build_parser_has_three_subcommands():
    """build_parser 注册了 3 个子命令：run/validate-report/inspect-doc。"""
    p = _build_parser()
    sub = p._subparsers._group_actions[0]
    assert set(sub.choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_subcommand_required():
    """subparser 是 required（必须指定子命令）。"""
    p = _build_parser()
    sub = p._subparsers._group_actions[0]
    assert sub.required is True


def test_build_parser_no_command_exits():
    """无子命令 → SystemExit。"""
    with pytest.raises(SystemExit) as e:
        _build_parser().parse_args([])
    assert e.value.code == 2


def test_build_parser_unknown_command_exits():
    """未知子命令 → SystemExit。"""
    with pytest.raises(SystemExit) as e:
        _build_parser().parse_args(["unknown-command"])
    assert e.value.code == 2


# =========================================================================
# _format_metric 长名称 / 边界
# =========================================================================


def test_format_metric_long_name_uses_36_width():
    """name 字段宽度 36：长 name 也输出（不截断）。"""
    long_name = "x" * 50
    out = _format_metric(long_name, {"value": None, "reason": "r"})
    # 输出含 long_name（即使超过 36）
    assert long_name in out


def test_format_metric_short_name_padded_to_36():
    """short name 被 pad 到至少 36 字符。"""
    out = _format_metric("x", {"value": None, "reason": "r"})
    # "  x" + 33 spaces + " null"
    assert "  x" + " " * 33 in out


def test_format_metric_empty_dict_value():
    """空 dict value → 输出 '' (无 items)。"""
    out = _format_metric("name", {"value": {}, "reason": None})
    # items 是空 string
    assert "ok" in out
    # 至少有 "  " + name + " " + "  (" 的 pattern
    assert "name" in out


def test_format_metric_int_with_reason():
    """int value + reason → 显示 value + (reason)。"""
    out = _format_metric("name", {"value": 5, "reason": "custom"})
    # int value 走最后 default 分支（非 bool/float/dict）
    assert "5" in out
    assert "custom" in out


def test_format_metric_negative_int_value():
    """负 int 也通过 default 分支。"""
    out = _format_metric("name", {"value": -3, "reason": None})
    assert "-3" in out


# =========================================================================
# _run_inspect_doc 排序行为
# =========================================================================


def test_run_inspect_doc_sort_bool_first(tmp_path, capsys):
    """inspect-doc 输出中 bool metrics 在 int/float 之前。"""
    doc = _write_minimal_document(tmp_path)
    main(["inspect-doc", str(doc)])
    captured = capsys.readouterr()
    # bool metrics (pipeline_success, schema_valid, text_preservation_equal) 在前
    bool_idx = captured.out.find("pipeline_success")
    int_idx = captured.out.find("element_count_total")
    assert bool_idx >= 0 and int_idx >= 0
    assert bool_idx < int_idx


def test_run_inspect_doc_null_metrics_last(tmp_path, capsys):
    """inspect-doc 输出中 null metrics 在最后。"""
    doc = _write_minimal_document(tmp_path)
    main(["inspect-doc", str(doc)])
    captured = capsys.readouterr()
    # pdf_locator_valid_ratio 在 doc 是 pdf 时不 null
    # docx_locator_valid_ratio 在 doc 是 pdf 时 null
    docx_idx = captured.out.find("docx_locator_valid_ratio")
    # 假设 element_count_total 不 null
    elem_idx = captured.out.find("element_count_total")
    assert docx_idx > elem_idx  # null 的在后


def test_run_inspect_doc_zero_chunks_no_error(tmp_path):
    """document 无 chunks → inspect-doc 也不报错。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf", "source_hash": "h",
        "elements": [],
        "chunks": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_run_inspect_doc_zero_elements_no_error(tmp_path):
    """document 无 elements → inspect-doc 也不报错。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "source_type": "pdf", "source_hash": "h",
        "elements": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_run_inspect_doc_missing_keys_no_error(tmp_path):
    """document 缺 source_type/elements/chunks keys → inspect-doc 用 default 也不报错。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"other_key": "x"}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_run_inspect_doc_output_has_file_label(tmp_path, capsys):
    """inspect-doc 输出含 'file:' 标签。"""
    doc = _write_minimal_document(tmp_path)
    main(["inspect-doc", str(doc)])
    captured = capsys.readouterr()
    assert "file:" in captured.out


def test_run_inspect_doc_output_has_metrics_label(tmp_path, capsys):
    """inspect-doc 输出含 'metrics:' 标签。"""
    doc = _write_minimal_document(tmp_path)
    main(["inspect-doc", str(doc)])
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_output_has_counts_label(tmp_path, capsys):
    """inspect-doc 输出含 'counts:' 标签。"""
    doc = _write_minimal_document(tmp_path)
    main(["inspect-doc", str(doc)])
    captured = capsys.readouterr()
    assert "counts:" in captured.out


# =========================================================================
# Windows stdout reconfigure 块
# =========================================================================


def test_module_source_contains_hasattr_reconfigure():
    """模块 source 含 hasattr(sys.stdout, 'reconfigure') 检查。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "hasattr(sys.stdout" in src
    assert "reconfigure" in src


def test_module_source_contains_utf8_reconfigure_call():
    """模块 source 含 sys.stdout.reconfigure(encoding='utf-8', errors='replace') 调用。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert 'sys.stdout.reconfigure' in src
    assert 'encoding="utf-8"' in src
    assert 'errors="replace"' in src


def test_module_source_contains_attribute_error_oserror_catch():
    """reconfigure 块 catch (AttributeError, OSError)。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "except (AttributeError, OSError)" in src


def test_module_source_contains_sys_stderr_reconfigure():
    """模块也对 sys.stderr 做 reconfigure。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "sys.stderr.reconfigure" in src


# =========================================================================
# main 返回 int 类型
# =========================================================================


def test_main_returns_int_for_run(tmp_path):
    manifest = _write_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(output)])
    assert isinstance(rc, int)


def test_main_returns_int_for_validate_report(tmp_path):
    report = _write_valid_report(tmp_path)
    rc = main(["validate-report", str(report)])
    assert isinstance(rc, int)


def test_main_returns_int_for_inspect_doc(tmp_path):
    doc = _write_minimal_document(tmp_path)
    rc = main(["inspect-doc", str(doc)])
    assert isinstance(rc, int)


# =========================================================================
# 模块 source 不含禁止内容
# =========================================================================


def test_module_source_does_not_contain_logging():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "import logging" not in src


def test_module_source_does_not_contain_subprocess():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "subprocess" not in src


def test_module_source_does_not_contain_asyncio():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "asyncio" not in src


def test_module_source_does_not_contain_threading():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "threading" not in src


def test_module_source_does_not_contain_concurrent():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "concurrent" not in src


def test_module_source_does_not_contain_os_import():
    """cli.py 不导入 os（用 pathlib.Path）。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "import os" not in src


def test_module_source_does_not_contain_re_import():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "import re" not in src


def test_module_source_does_not_contain_time_import():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "import time" not in src


def test_module_source_does_not_contain_datetime_import():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "from datetime" not in src
    assert "import datetime" not in src


# =========================================================================
# __all__ 不存在
# =========================================================================


def test_module_does_not_have_all():
    """cli 模块不定义 __all__。"""
    import evaluation.cli as m
    assert not hasattr(m, "__all__")


# =========================================================================
# 模块 docstring 详细
# =========================================================================


def test_module_docstring_mentions_run():
    import evaluation.cli as m
    assert m.__doc__
    assert "run" in m.__doc__


def test_module_docstring_mentions_validate_report():
    import evaluation.cli as m
    assert "validate-report" in m.__doc__


def test_module_docstring_mentions_inspect_doc():
    import evaluation.cli as m
    assert "inspect-doc" in m.__doc__


def test_module_docstring_mentions_python_m_evaluation_cli():
    import evaluation.cli as m
    assert "python -m evaluation.cli" in m.__doc__


def test_module_docstring_mentions_manifest_or_qing_dan():
    import evaluation.cli as m
    assert "manifest" in m.__doc__.lower() or "清单" in m.__doc__


# =========================================================================
# 模块 imports 精确
# =========================================================================


def test_module_source_contains_import_argparse():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "import argparse" in src


def test_module_source_contains_import_json():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "import json" in src


def test_module_source_contains_import_sys():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "import sys" in src


def test_module_source_contains_from_pathlib_import_path():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "from pathlib import Path" in src


def test_module_source_contains_from_evaluation_import_manifest():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "from evaluation.manifest import" in src


def test_module_source_contains_from_evaluation_import_report():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "from evaluation.report import" in src


def test_module_source_contains_from_evaluation_import_runner():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "from evaluation.runner import" in src


def test_module_source_contains_from_evaluation_import_schema():
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert "from evaluation.schema import" in src


# =========================================================================
# inspect-doc 懒加载
# =========================================================================


def test_run_inspect_doc_lazy_imports_compute_automatic_metrics():
    """inspect-doc 懒加载 compute_automatic_metrics。"""
    src = inspect.getsource(_run_inspect_doc)
    assert "from evaluation.metrics import" in src
    assert "compute_automatic_metrics" in src


def test_run_inspect_doc_lazy_imports_figure_caption_prf():
    src = inspect.getsource(_run_inspect_doc)
    assert "figure_caption_prf" in src


def test_run_inspect_doc_lazy_imports_chunk_boundary_prf():
    src = inspect.getsource(_run_inspect_doc)
    assert "chunk_boundary_prf" in src


# =========================================================================
# main 的 if __name__ == '__main__' 块
# =========================================================================


def test_module_main_block_uses_system_exit():
    """main block 是 raise SystemExit(main())。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__"' in src or "if __name__ == '__main__'" in src
    assert "raise SystemExit(main())" in src


def test_module_main_block_at_end():
    """main block 在模块末尾。"""
    import evaluation.cli as m
    src = inspect.getsource(m)
    # main block 应在最后 200 字符内
    last_part = src[-200:]
    assert 'if __name__' in last_part


# =========================================================================
# main() 输出到 stderr vs stdout 严格分离
# =========================================================================


def test_main_run_error_goes_to_stderr_not_stdout(tmp_path, capsys):
    """run 错误消息只到 stderr，stdout 不含。"""
    output = tmp_path / "out.json"
    main(["run", "--manifest", str(tmp_path / "missing.json"), "--output", str(output)])
    captured = capsys.readouterr()
    assert captured.out == ""  # stdout 为空
    assert captured.err != ""  # stderr 非空


def test_main_validate_report_success_stdout_only(tmp_path, capsys):
    """validate-report 成功消息只到 stdout。"""
    report = _write_valid_report(tmp_path)
    main(["validate-report", str(report)])
    captured = capsys.readouterr()
    assert captured.out != ""
    assert captured.err == ""


def test_main_inspect_doc_success_stdout_only(tmp_path, capsys):
    """inspect-doc 成功消息只到 stdout。"""
    doc = _write_minimal_document(tmp_path)
    main(["inspect-doc", str(doc)])
    captured = capsys.readouterr()
    assert captured.out != ""
    assert captured.err == ""
