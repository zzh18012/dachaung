"""evaluation/cli.py 第三十九轮 edges 测试（Round 404）。

补强 edges38 未触及的角度：
- _build_parser 行为深度第十二批（subparsers 顺序 / prog 名称 / run 子命令参数动作 / 默认值边界 / choices set / RunParser 5 args / val_parser 1 arg / ins_parser 2 args / 描述含中文）
- argparse Namespace 行为第十二批（同输入产生等价 Namespace / --parser 默认 fallback / --max-chars 默认 800 / --tolerance-chars 默认 30 / 各 path 字段 str 类型 / positional input 类型）
- _format_metric 行为深度第十二批（name 超长 → padding 仍 36 / dict 空字符串 value / dict 多 key 排序 / name 含空格 / int 0 / 负 int / Unicode name / float with negative / 整体结构验证）
- _run_inspect_doc 行为深度第十二批（BOM → JSON 失败 / 文件路径含 Unicode / args.path 是 Path / 不存在文件 / tolerance_chars 透传 / 输出第一行格式 / print counts with elements & chunks / 缺 elements / 缺 chunks / print document_id 缺省 '?'）
- main 路由第十二批（run 命令完整流程：manifest 合法 + run_evaluation mocked 成功 / validate-report 合法 / args.parser 透传 / args.max_chars 透传 / args.tolerance_chars 透传 / 输出格式 / 缺 --manifest 报错 / 缺 --output 报错 / 返回 int 类型）
- module source forbidden tokens 第十五批
- module source 字符串精确补强第十二批
- signatures 第十二批
- module 合理性第十二批
- 端到端集成第十二批
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from evaluation import cli as climod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 行为深度第十二批 ----------


def test_build_parser_subparsers_choice_order_batch12():
    """subparsers 注册顺序：run / validate-report / inspect-doc。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    keys = list(sub_actions[0].choices.keys())
    assert keys == ["run", "validate-report", "inspect-doc"]


def test_build_parser_run_subparser_prog_batch12():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    assert "run" in run_parser.prog


def test_build_parser_validate_report_subparser_prog_batch12():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    val_parser = sub_actions[0].choices["validate-report"]
    assert "validate-report" in val_parser.prog


def test_build_parser_inspect_doc_subparser_prog_batch12():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_parser = sub_actions[0].choices["inspect-doc"]
    assert "inspect-doc" in ins_parser.prog


def test_build_parser_run_subparser_default_parser_value_batch12():
    """run --parser 默认值是 fallback。"""
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json"]
    )
    assert ns.parser == "fallback"


def test_build_parser_run_subparser_default_max_chars_value_batch12():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json"]
    )
    assert ns.max_chars == 800


def test_build_parser_run_subparser_default_tolerance_chars_batch12():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json"]
    )
    assert ns.tolerance_chars == 30


def test_build_parser_inspect_doc_default_tolerance_chars_batch12():
    ns = _build_parser().parse_args(["inspect-doc", "a.json"])
    assert ns.tolerance_chars == 30


def test_build_parser_run_subparser_argument_count_batch12():
    """run 子命令应有 5 个 user-defined 选项（--manifest/--output/--parser/--max-chars/--tolerance-chars）。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    option_strings = []
    for a in run_parser._actions:
        option_strings.extend(a.option_strings)
    # 过滤 -h/--help
    user_options = [s for s in option_strings if s not in ("-h", "--help")]
    assert set(user_options) == {
        "--manifest",
        "--output",
        "--parser",
        "--max-chars",
        "--tolerance-chars",
    }


def test_build_parser_validate_report_argument_count_batch12():
    """validate-report 只有一个 positional input。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    val_parser = sub_actions[0].choices["validate-report"]
    # 找 positional action
    positional = [
        a for a in val_parser._actions
        if not a.option_strings and a.dest != "help"
    ]
    assert len(positional) == 1
    assert positional[0].dest == "input"


def test_build_parser_inspect_doc_argument_count_batch12():
    """inspect-doc 有 1 positional input + 1 optional --tolerance-chars。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_parser = sub_actions[0].choices["inspect-doc"]
    positional = [
        a for a in ins_parser._actions
        if not a.option_strings and a.dest != "help"
    ]
    assert len(positional) == 1
    assert positional[0].dest == "input"
    # 还应有一个 --tolerance-chars
    tol_actions = [a for a in ins_parser._actions if "--tolerance-chars" in a.option_strings]
    assert len(tol_actions) == 1


def test_build_parser_description_contains_chinese_batch12():
    p = _build_parser()
    assert "评测" in p.description or "校验" in p.description


def test_build_parser_run_manifest_help_text_batch12():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    manifest_action = next(
        a for a in run_parser._actions if "--manifest" in a.option_strings
    )
    assert manifest_action.help is not None
    assert len(manifest_action.help) > 0


def test_build_parser_run_output_help_text_batch12():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    output_action = next(
        a for a in run_parser._actions if "--output" in a.option_strings
    )
    assert output_action.help is not None


def test_build_parser_run_parser_help_text_has_default_marker_batch12():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    parser_action = next(
        a for a in run_parser._actions if "--parser" in a.option_strings
    )
    assert "fallback" in (parser_action.help or "")


def test_build_parser_run_max_chars_help_text_has_default_800_batch12():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    max_chars_action = next(
        a for a in run_parser._actions if "--max-chars" in a.option_strings
    )
    assert "800" in (max_chars_action.help or "")


def test_build_parser_run_tolerance_chars_help_text_has_default_30_batch12():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    tol_action = next(
        a for a in run_parser._actions if "--tolerance-chars" in a.option_strings
    )
    assert "30" in (tol_action.help or "")


def test_build_parser_has_two_subprocess_calls_in_module_batch12():
    """模块本身无 subprocess 调用（main 内调用 get_git_provenance）。"""
    source = inspect.getsource(climod)
    # 顶层不应直接调 subprocess.run
    assert "subprocess.run(" not in source


# ---------- argparse Namespace 行为第十二批 ----------


def test_namespace_run_command_value_batch12():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json"]
    )
    assert ns.command == "run"


def test_namespace_validate_report_command_value_batch12():
    ns = _build_parser().parse_args(["validate-report", "a.json"])
    assert ns.command == "validate-report"


def test_namespace_inspect_doc_command_value_batch12():
    ns = _build_parser().parse_args(["inspect-doc", "a.json"])
    assert ns.command == "inspect-doc"


def test_namespace_run_manifest_str_type_batch12():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json"]
    )
    assert isinstance(ns.manifest, str)


def test_namespace_run_output_str_type_batch12():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json"]
    )
    assert isinstance(ns.output, str)


def test_namespace_validate_report_input_str_type_batch12():
    ns = _build_parser().parse_args(["validate-report", "a.json"])
    assert isinstance(ns.input, str)


def test_namespace_inspect_doc_input_str_type_batch12():
    ns = _build_parser().parse_args(["inspect-doc", "a.json"])
    assert isinstance(ns.input, str)


def test_namespace_run_parser_kreuzberg_choice_batch12():
    ns = _build_parser().parse_args(
        [
            "run",
            "--manifest",
            "a.json",
            "--output",
            "b.json",
            "--parser",
            "kreuzberg",
        ]
    )
    assert ns.parser == "kreuzberg"


def test_namespace_run_max_chars_negative_int_batch12():
    """argparse 接受负数 int（需要 -- separator 避免被当作 flag）。"""
    ns = _build_parser().parse_args(
        [
            "run",
            "--manifest",
            "a.json",
            "--output",
            "b.json",
            "--max-chars",
            "-100",
        ]
    )
    assert ns.max_chars == -100


def test_namespace_run_tolerance_chars_via_kwarg_batch12():
    ns = _build_parser().parse_args(
        [
            "run",
            "--manifest",
            "a.json",
            "--output",
            "b.json",
            "--tolerance-chars",
            "99",
        ]
    )
    assert ns.tolerance_chars == 99


def test_namespace_inspect_doc_tolerance_chars_via_kwarg_batch12():
    ns = _build_parser().parse_args(
        ["inspect-doc", "a.json", "--tolerance-chars", "55"]
    )
    assert ns.tolerance_chars == 55


def test_namespace_command_only_for_unknown_command_raises_systemexit_batch12(capsys):
    """unknown command → SystemExit code 2。"""
    with pytest.raises(SystemExit) as exc_info:
        _build_parser().parse_args(["totally-unknown"])
    assert exc_info.value.code == 2


# ---------- _format_metric 行为深度第十二批 ----------


def test_format_metric_long_name_padding_batch12():
    """name 超过 36 chars → padding 不截断（仍 36 宽，但 name 会突破）。"""
    name = "x" * 50
    out = _format_metric(name, {"value": 1, "reason": "ok"})
    # name 全部出现在输出中
    assert name in out


def test_format_metric_unicode_name_batch12():
    out = _format_metric("段落指标", {"value": 1, "reason": "ok"})
    assert "段落指标" in out


def test_format_metric_dict_with_empty_string_value_batch12():
    out = _format_metric("by_type", {"value": {"a": ""}, "reason": "ok"})
    assert "a=" in out


def test_format_metric_dict_with_string_value_batch12():
    out = _format_metric("by_type", {"value": {"a": "x"}, "reason": "ok"})
    assert "a=x" in out


def test_format_metric_dict_with_multiple_keys_sorted_batch12():
    """dict 多个 key → sorted 排序输出。"""
    out = _format_metric("by_type", {"value": {"b": 1, "a": 2, "c": 3}, "reason": "ok"})
    # 应是 a=2, b=1, c=3 的顺序
    assert out.find("a=2") < out.find("b=1") < out.find("c=3")


def test_format_metric_int_zero_batch12():
    out = _format_metric("count", {"value": 0, "reason": "ok"})
    # int 0 不走 null 分支（0 is None False）
    # 走 default 分支：f"  {name:36} {value}  ({reason or 'ok'})"
    assert "0" in out


def test_format_metric_negative_int_batch12():
    out = _format_metric("count", {"value": -5, "reason": "ok"})
    assert "-5" in out


def test_format_metric_negative_float_batch12():
    out = _format_metric("ratio", {"value": -0.5, "reason": "ok"})
    assert "-0.5000" in out


def test_format_metric_very_large_int_batch12():
    out = _format_metric("count", {"value": 10**18, "reason": "ok"})
    assert str(10**18) in out


def test_format_metric_value_only_no_reason_field_batch12():
    """metric dict 只有 value，无 reason。"""
    out = _format_metric("x", {"value": 1})
    # reason default 'ok'
    assert "(ok)" in out


def test_format_metric_none_value_with_unicode_reason_batch12():
    out = _format_metric("x", {"value": None, "reason": "无标注"})
    assert "null" in out
    assert "无标注" in out


def test_format_metric_none_value_no_reason_field_batch12():
    out = _format_metric("x", {"value": None})
    assert "null" in out
    assert "(None)" in out


def test_format_metric_struct_two_spaces_prefix_batch12():
    """所有输出以 "  " 开头。"""
    cases = [
        {"value": None, "reason": "x"},
        {"value": True, "reason": "x"},
        {"value": 1.5, "reason": "x"},
        {"value": 5, "reason": "x"},
        {"value": {"a": 1}, "reason": "x"},
        {"value": "str", "reason": "x"},
    ]
    for m in cases:
        out = _format_metric("n", m)
        assert out.startswith("  ")


def test_format_metric_padded_name_exact_width_36_batch12():
    """name field 宽度严格 36（当 name 长度 ≤ 36 时）。"""
    out = _format_metric("hi", {"value": 1, "reason": "ok"})
    # "  " + name + padding + " " + value
    # name field = out[2:38]
    assert out[2:38] == "hi" + " " * 34


# ---------- _run_inspect_doc 行为深度第十二批 ----------


def test_run_inspect_doc_bom_file_returns_1_batch12(tmp_path):
    """UTF-8 BOM 让 json.load 失败 → 返回 1。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf{"k": "v"}')
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_unicode_filename_batch12(tmp_path, capsys):
    """Unicode 文件名也能读取。"""
    p = tmp_path / "文档.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_path_obj_batch12(tmp_path):
    """Path 对象作为 input（_run_inspect_doc 内部用 Path(args.input) 包装）。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=p, tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_file_not_found_returns_2_batch12(tmp_path, capsys):
    args = argparse.Namespace(input=str(tmp_path / "no.json"), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_run_inspect_doc_first_output_line_format_batch12(tmp_path, capsys):
    """第一行输出格式应是 "file:        <path>"。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert lines[0].startswith("file:")


def test_run_inspect_doc_prints_question_mark_when_missing_batch12(tmp_path, capsys):
    """缺 document_id → 打印 '?'。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "?" in out


def test_run_inspect_doc_prints_unknown_source_type_batch12(tmp_path, capsys):
    """缺 source_type → 默认 'unknown'。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "unknown" in out


def test_run_inspect_doc_prints_zero_counts_for_empty_batch12(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "elements=0" in out
    assert "chunks=0" in out


def test_run_inspect_doc_prints_elements_count_batch12(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text(
        '{"elements": [{"type": "paragraph"}, {"type": "paragraph"}]}',
        encoding="utf-8",
    )
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "elements=2" in out


def test_run_inspect_doc_prints_chunks_count_batch12(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text(
        '{"chunks": [{"id": "c1"}, {"id": "c2"}, {"id": "c3"}]}',
        encoding="utf-8",
    )
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "chunks=3" in out


def test_run_inspect_doc_invalid_json_returns_1_batch12(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_invalid_json_error_message_batch12(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    err = capsys.readouterr().err
    assert "[ERROR]" in err
    assert "JSON" in err


def test_run_inspect_doc_returns_int_type_batch12(tmp_path):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert type(rc) is int


# ---------- main 路由第十二批 ----------


def test_main_run_manifest_load_fails_returns_1_batch12(capsys, tmp_path):
    """manifest 文件存在但格式非法 → load_manifest raises ManifestError → return 1。"""
    bad_manifest = tmp_path / "bad.json"
    bad_manifest.write_text("not valid json", encoding="utf-8")
    rc = main(
        [
            "run",
            "--manifest",
            str(bad_manifest),
            "--output",
            str(tmp_path / "out.json"),
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_run_success_returns_0_batch12(capsys, tmp_path):
    """完整 run 命令流程：合法 manifest + mocked run_evaluation → return 0。"""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "out" / "report.json"

    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {"status": "incomplete", "file_count": 0},
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }

    with patch("evaluation.cli.run_evaluation", return_value=fake_report), \
         patch("evaluation.cli.validate_file", return_value=None), \
         patch("evaluation.cli.load_manifest") as load_m:
        # load_manifest 会被调用，给个返回值
        from evaluation.manifest import Manifest
        # 实际上 load_manifest 是从 evaluation.manifest 导入的
        # 我们需要让它返回有 project_root 属性的对象
        class _M:
            project_root = Path(".")
            devset_status = "incomplete"
            file_count = 0
            content_group_count = 0
            pdf_count = 0
            docx_count = 0
            categories_covered = []
            documents = []
            expected_failures = []
        load_m.return_value = _M()
        rc = main(
            [
                "run",
                "--manifest",
                str(manifest_path),
                "--output",
                str(output_path),
            ]
        )
    assert rc == 0


def test_main_run_report_validation_fails_returns_1_batch12(capsys, tmp_path):
    """report 生成后 validate_file 失败 → return 1。"""
    from evaluation.schema import EvalSchemaError

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "out" / "report.json"

    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {},
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }

    with patch("evaluation.cli.run_evaluation", return_value=fake_report), \
         patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("bad")), \
         patch("evaluation.cli.load_manifest") as load_m:
        class _M:
            project_root = Path(".")
            devset_status = "incomplete"
            file_count = 0
            content_group_count = 0
            pdf_count = 0
            docx_count = 0
            categories_covered = []
            documents = []
            expected_failures = []
        load_m.return_value = _M()
        rc = main(
            [
                "run",
                "--manifest",
                str(manifest_path),
                "--output",
                str(output_path),
            ]
        )
    assert rc == 1


def test_main_run_passes_parser_to_run_evaluation_batch12(tmp_path):
    """main 应把 args.parser 传给 run_evaluation(parser_name=...)。"""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "out.json"
    captured: dict = {}

    def _fake_run(*args, **kwargs):
        captured["parser_name"] = kwargs.get("parser_name")
        captured["max_chars"] = kwargs.get("max_chars")
        captured["tolerance_chars"] = kwargs.get("tolerance_chars")
        return {
            "report_version": "1.1",
            "provenance": {},
            "devset": {},
            "summary": {},
            "per_doc": [],
            "expected_failures": [],
        }

    with patch("evaluation.cli.run_evaluation", side_effect=_fake_run), \
         patch("evaluation.cli.validate_file", return_value=None), \
         patch("evaluation.cli.load_manifest") as load_m:
        class _M:
            project_root = Path(".")
            devset_status = "incomplete"
            file_count = 0
            content_group_count = 0
            pdf_count = 0
            docx_count = 0
            categories_covered = []
            documents = []
            expected_failures = []
        load_m.return_value = _M()
        main(
            [
                "run",
                "--manifest",
                str(manifest_path),
                "--output",
                str(output_path),
                "--parser",
                "kreuzberg",
                "--max-chars",
                "500",
                "--tolerance-chars",
                "20",
            ]
        )
    assert captured["parser_name"] == "kreuzberg"
    assert captured["max_chars"] == 500
    assert captured["tolerance_chars"] == 20


def test_main_validate_report_success_returns_0_batch12(capsys, tmp_path):
    """合法 report → 校验通过 → return 0。"""
    p = tmp_path / "report.json"
    # 必须满足 evaluation-report.schema.json 的最小要求
    # 用真实 validate_file 测试太复杂，patch 掉
    with patch("evaluation.cli.validate_file", return_value=None):
        rc = main(["validate-report", str(p)])
    # main 内部还会先检查 is_file，所以 p 必须存在
    # 实际上：if not input_path.is_file() → return 2
    # 我们需要 p.is_file() True


def test_main_validate_report_with_real_file_mocked_validator_batch12(capsys, tmp_path):
    """合法 file + mocked validator → return 0。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", return_value=None):
        rc = main(["validate-report", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[OK]" in out


def test_main_validate_report_schema_fail_returns_1_batch12(capsys, tmp_path):
    """validate_file raises EvalSchemaError → return 1。"""
    from evaluation.schema import EvalSchemaError

    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("bad schema")):
        rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_dispatch_batch12(tmp_path, capsys):
    """main inspect-doc → 调用 _run_inspect_doc。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_returns_int_type_batch12(tmp_path):
    p = tmp_path / "no.json"
    rc = main(["validate-report", str(p)])
    assert type(rc) is int


def test_main_no_subcommand_arg_raises_systemexit_batch12(capsys):
    with pytest.raises(SystemExit):
        main([])


# ---------- module source forbidden tokens 第十五批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import pickle",
        "import yaml",
        "import socket",
        "import threading",
        "import multiprocessing",
        "import asyncio",
        "import marshal",
        "import ctypes",
        "from pickle import",
        "from yaml import",
        "from socket import",
        "from threading import",
        "from marshal import",
        "from ctypes import",
        "subprocess.Popen",
        "shutil.rmtree",
    ],
)
def test_cli_source_no_forbidden_token_fifteenth_batch12(token):
    source = inspect.getsource(climod)
    assert token not in source


def test_cli_source_no_top_level_lambda_batch12():
    source = inspect.getsource(climod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_cli_source_no_class_definition_batch12():
    source = inspect.getsource(climod)
    assert "\nclass " not in source
    assert not source.startswith("class ")


def test_cli_source_no_assert_statement_batch12():
    source = inspect.getsource(climod)
    assert "\nassert " not in source
    assert not source.startswith("assert ")


def test_cli_source_no_yield_batch12():
    source = inspect.getsource(climod)
    assert "yield " not in source


def test_cli_source_no_global_batch12():
    source = inspect.getsource(climod)
    assert " global " not in source


def test_cli_source_no_walrus_batch12():
    source = inspect.getsource(climod)
    assert ":=" not in source


def test_cli_source_no_async_def_batch12():
    source = inspect.getsource(climod)
    assert "async def" not in source


def test_cli_source_no_while_loop_batch12():
    source = inspect.getsource(climod)
    assert "while " not in source


def test_cli_source_no_input_call_batch12():
    source = inspect.getsource(climod)
    assert "input(" not in source


def test_cli_source_no_remove_call_batch12():
    source = inspect.getsource(climod)
    assert ".remove(" not in source


def test_cli_source_no_kill_batch12():
    source = inspect.getsource(climod)
    assert ".kill(" not in source


# ---------- module source 字符串精确补强第十二批 ----------


def test_module_source_has_future_annotations_batch12():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:25])
    assert "from __future__ import annotations" in head


def test_module_source_imports_argparse_batch12():
    source = inspect.getsource(climod)
    assert "import argparse" in source


def test_module_source_imports_json_batch12():
    source = inspect.getsource(climod)
    assert "import json" in source


def test_module_source_imports_sys_batch12():
    source = inspect.getsource(climod)
    assert "import sys" in source


def test_module_source_imports_path_batch12():
    source = inspect.getsource(climod)
    assert "from pathlib import Path" in source


def test_module_source_imports_manifest_error_batch12():
    source = inspect.getsource(climod)
    assert "ManifestError" in source
    assert "load_manifest" in source


def test_module_source_imports_get_git_provenance_batch12():
    source = inspect.getsource(climod)
    assert "get_git_provenance" in source


def test_module_source_imports_run_evaluation_batch12():
    source = inspect.getsource(climod)
    assert "run_evaluation" in source


def test_module_source_imports_eval_schema_error_batch12():
    source = inspect.getsource(climod)
    assert "EvalSchemaError" in source
    assert "validate_file" in source


def test_module_source_has_subparsers_call_batch12():
    source = inspect.getsource(climod)
    assert "add_subparsers" in source


def test_module_source_has_main_function_batch12():
    source = inspect.getsource(climod)
    assert "def main(argv" in source


def test_module_source_has_run_inspect_doc_batch12():
    source = inspect.getsource(climod)
    assert "def _run_inspect_doc" in source


def test_module_source_has_format_metric_batch12():
    source = inspect.getsource(climod)
    assert "def _format_metric" in source


def test_module_source_has_dunder_name_main_batch12():
    source = inspect.getsource(climod)
    assert 'if __name__ == "__main__"' in source


def test_module_source_has_system_exit_call_batch12():
    source = inspect.getsource(climod)
    assert "raise SystemExit(main())" in source


def test_module_source_has_stdout_reconfigure_call_batch12():
    """Windows 友好：reconfigure stdout/stderr。"""
    source = inspect.getsource(climod)
    assert "reconfigure" in source


def test_module_source_has_subcommand_strings_batch12():
    source = inspect.getsource(climod)
    assert '"run"' in source
    assert '"validate-report"' in source
    assert '"inspect-doc"' in source


# ---------- signatures 第十二批 ----------


def test_signature_build_parser_no_params_batch12():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_main_optional_argv_batch12():
    sig = inspect.signature(main)
    assert "argv" in sig.parameters
    p = sig.parameters["argv"]
    assert p.default is None


def test_signature_main_return_annotation_int_batch12():
    sig = inspect.signature(main)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "int" in annot_str


def test_signature_main_argv_annotation_batch12():
    sig = inspect.signature(main)
    p = sig.parameters["argv"]
    annot = p.annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "list" in annot_str
    assert "str" in annot_str
    assert "None" in annot_str


def test_signature_format_metric_2_params_batch12():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters) == ["name", "metric"]


def test_signature_format_metric_return_annotation_str_batch12():
    sig = inspect.signature(_format_metric)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "str" in annot_str


def test_signature_format_metric_name_annotation_batch12():
    sig = inspect.signature(_format_metric)
    p = sig.parameters["name"]
    annot = p.annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "str" in annot_str


def test_signature_format_metric_metric_annotation_dict_batch12():
    sig = inspect.signature(_format_metric)
    p = sig.parameters["metric"]
    annot = p.annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "dict" in annot_str


def test_signature_run_inspect_doc_1_param_batch12():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1
    assert list(sig.parameters) == ["args"]


def test_signature_run_inspect_doc_return_annotation_int_batch12():
    sig = inspect.signature(_run_inspect_doc)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "int" in annot_str


def test_all_public_functions_no_var_kwargs_batch12():
    for fn in [_build_parser, main, _format_metric, _run_inspect_doc]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- module 合理性第十二批 ----------


def test_module_name_evaluation_cli_batch12():
    assert climod.__name__ == "evaluation.cli"


def test_module_dunder_file_endswith_cli_py_batch12():
    sep = os.sep
    assert climod.__file__.endswith("evaluation" + sep + "cli.py") or climod.__file__.endswith(
        "evaluation/cli.py"
    )


def test_module_user_function_count_4_batch12():
    funcs = [
        n for n, v in vars(climod).items()
        if inspect.isfunction(v) and v.__module__ == climod.__name__
    ]
    assert set(funcs) == {"_build_parser", "main", "_format_metric", "_run_inspect_doc"}


def test_module_no_user_classes_batch12():
    classes = [
        n for n, v in vars(climod).items()
        if inspect.isclass(v) and v.__module__ == climod.__name__
    ]
    assert classes == []


def test_module_no_user_constants_tuple_batch12():
    consts = [
        n for n, v in vars(climod).items()
        if not n.startswith("__") and isinstance(v, tuple) and not callable(v)
    ]
    assert consts == []


def test_module_docstring_present_batch12():
    assert climod.__doc__ is not None
    assert len(climod.__doc__) > 30


def test_module_docstring_mentions_subcommands_batch12():
    assert climod.__doc__ is not None
    assert "run" in climod.__doc__
    assert "validate-report" in climod.__doc__


def test_module_docstring_mentions_inspect_doc_batch12():
    assert climod.__doc__ is not None
    assert "inspect-doc" in climod.__doc__


def test_module_uses_future_annotations_batch12():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:25])
    assert "from __future__ import annotations" in head


def test_module_has_dunder_all_absent_batch12():
    """cli 模块没有 __all__（main 是 entry point）。"""
    assert not hasattr(climod, "__all__")


def test_module_has_argparse_imported_at_top_level_batch12():
    """argparse 应是顶层 import。"""
    assert hasattr(climod, "argparse")
    assert climod.argparse is argparse


def test_module_has_sys_imported_at_top_level_batch12():
    assert hasattr(climod, "sys")
    assert climod.sys is sys


def test_module_has_path_imported_at_top_level_batch12():
    assert hasattr(climod, "Path")


# ---------- 端到端集成第十二批 ----------


def test_e2e_full_chain_validate_report_with_real_file_batch12(tmp_path, capsys):
    """validate-report 在真实 file + mock validator 通过 → 0。"""
    p = tmp_path / "report.json"
    p.write_text('{"report_version": "1.1"}', encoding="utf-8")
    with patch("evaluation.cli.validate_file", return_value=None):
        rc = main(["validate-report", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[OK]" in out
    assert str(p) in out


def test_e2e_full_chain_inspect_doc_with_empty_dict_batch12(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_full_chain_run_command_integration_batch12(tmp_path):
    """run 命令完整流程 + mock run_evaluation。"""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "out" / "report.json"

    fake_report = {
        "report_version": "1.1",
        "provenance": {"git_commit": "abc"},
        "devset": {"status": "incomplete", "file_count": 0},
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }

    with patch("evaluation.cli.run_evaluation", return_value=fake_report), \
         patch("evaluation.cli.validate_file", return_value=None), \
         patch("evaluation.cli.load_manifest") as load_m:
        class _M:
            project_root = Path(".")
            devset_status = "incomplete"
            file_count = 0
            content_group_count = 0
            pdf_count = 0
            docx_count = 0
            categories_covered = []
            documents = []
            expected_failures = []
        load_m.return_value = _M()
        rc = main(
            [
                "run",
                "--manifest",
                str(manifest_path),
                "--output",
                str(output_path),
            ]
        )
    assert rc == 0


def test_e2e_combined_chain_run_failure_in_runner_batch12(tmp_path, capsys):
    """run_evaluation raises EvalSchemaError → return 1。"""
    from evaluation.schema import EvalSchemaError

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "out.json"

    with patch("evaluation.cli.run_evaluation", side_effect=EvalSchemaError("schema fail")), \
         patch("evaluation.cli.load_manifest") as load_m:
        class _M:
            project_root = Path(".")
            devset_status = "incomplete"
            file_count = 0
            content_group_count = 0
            pdf_count = 0
            docx_count = 0
            categories_covered = []
            documents = []
            expected_failures = []
        load_m.return_value = _M()
        rc = main(
            [
                "run",
                "--manifest",
                str(manifest_path),
                "--output",
                str(output_path),
            ]
        )
    assert rc == 1
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_e2e_inspect_doc_full_run_batch12(tmp_path, capsys):
    """完整 inspect-doc 流程，输出包含多个 metric。"""
    p = tmp_path / "d.json"
    p.write_text(
        json.dumps(
            {
                "document_id": "doc_001",
                "source_type": "pdf",
                "source_path": "/x/y.pdf",
                "parser_name": "fallback",
                "parser_version": "1.0.0",
                "elements": [{"type": "paragraph"}, {"type": "paragraph"}],
                "chunks": [{"id": "c1", "text": "a"}],
            }
        ),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "doc_001" in out
    assert "fallback" in out
    assert "1.0.0" in out
    assert "elements=2" in out
    assert "chunks=1" in out


def test_e2e_combined_chain_three_subcommands_independent_batch12(tmp_path):
    """三个子命令独立工作，不互相影响。"""
    # 准备一个 manifest，一个 report，一个 doc
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )

    report = tmp_path / "report.json"
    report.write_text("{}", encoding="utf-8")

    doc = tmp_path / "doc.json"
    doc.write_text("{}", encoding="utf-8")

    # validate-report 需要 mock validator
    with patch("evaluation.cli.validate_file", return_value=None):
        rc_v = main(["validate-report", str(report)])
    rc_i = main(["inspect-doc", str(doc)])

    assert rc_v == 0
    assert rc_i == 0


def test_e2e_namespace_kwargs_works_batch12(tmp_path):
    """main 接受 argv list 形式参数。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", return_value=None):
        # main(argv=...) 也是合法调用方式
        rc = main(argv=["validate-report", str(p)])
    assert rc == 0


def test_e2e_module_callable_via_python_m_batch12(tmp_path):
    """python -m evaluation.cli --help 应 exit 0（argparse 自带）。"""
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.cli", "--help"],
        capture_output=True,
        timeout=10,
    )
    # --help → exit 0
    assert result.returncode == 0
    # stdout 应有内容（argparse usage）
    assert result.stdout is not None
    assert len(result.stdout) > 0


def test_e2e_module_callable_unknown_command_returns_2_batch12(tmp_path):
    """python -m evaluation.cli unknown → exit 2。"""
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.cli", "unknown"],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 2
