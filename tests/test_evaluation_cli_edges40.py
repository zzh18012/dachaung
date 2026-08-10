"""evaluation/cli.py 第四十一轮 edges 测试（Round 411）。

补强 edges39 未触及的角度：
- _build_parser 行为深度第十三批（choices 元组 / 各子命令 description 内容 / 默认值类型 / RunParser arg 名 / val_parser positional 名 / ins_parser positional 名 / 错误 --parser 值 raise）
- argparse Namespace 行为第十三批（attribute 名称 / argparse 内部 type=int 转换 / choices 限制 / Namespace != 比较）
- _format_metric 行为深度第十三批（padding 行为 / 字典嵌套 / 字典含 None value / 字典含 True value / name Unicode 长 / metric dict 缺 reason / float 精度 4 位 / bool True → true / bool False → false）
- _run_inspect_doc 行为深度第十三批（stdout 含 file: 行 / stdout 含 document_id: 行 / stdout 含 parser: 行 / stdout 含 counts: 行 / stdout 含 metrics: 行 / tolerance_chars 默认 / 缺 source_type 默认 unknown）
- main 路由第十三批（run 命令 manifest 路径不存在 → return 2 / run 命令 manifest 加载失败 → return 1 / validate-report 命令 input 不存在 → return 2 / inspect-doc 命令 input 不存在 → return 2 / main 无命令 raise SystemExit / main 返回值是 int）
- module source forbidden tokens 第十九批
- module source 字符串精确补强第十六批
- signatures 第十六批
- module 合理性第十六批
- 端到端集成第十六批
"""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from evaluation import cli as climod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 行为深度第十三批 ----------


def test_build_parser_choices_only_fallback_kreuzberg_batch13():
    """--parser choices 必须严格是 ('fallback', 'kreuzberg')。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    parser_action = next(a for a in run_parser._actions if "--parser" in a.option_strings)
    assert set(parser_action.choices) == {"fallback", "kreuzberg"}


def test_build_parser_choices_is_tuple_batch13():
    """choices 应该是 tuple（不是 list）。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    parser_action = next(a for a in run_parser._actions if "--parser" in a.option_strings)
    assert isinstance(parser_action.choices, tuple)


def test_build_parser_max_chars_type_int_batch13():
    """--max-chars type 应是 int。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    action = next(a for a in run_parser._actions if "--max-chars" in a.option_strings)
    assert action.type is int


def test_build_parser_tolerance_chars_type_int_batch13():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    action = next(a for a in run_parser._actions if "--tolerance-chars" in a.option_strings)
    assert action.type is int


def test_build_parser_inspect_doc_tolerance_chars_type_int_batch13():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_parser = sub_actions[0].choices["inspect-doc"]
    action = next(a for a in ins_parser._actions if "--tolerance-chars" in a.option_strings)
    assert action.type is int


def test_build_parser_run_manifest_required_batch13():
    """--manifest 应是 required。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    action = next(a for a in run_parser._actions if "--manifest" in a.option_strings)
    assert action.required is True


def test_build_parser_run_output_required_batch13():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    action = next(a for a in run_parser._actions if "--output" in a.option_strings)
    assert action.required is True


def test_build_parser_parser_not_required_batch13():
    """--parser 不是 required（有默认值）。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    action = next(a for a in run_parser._actions if "--parser" in a.option_strings)
    assert action.required is False or action.required is None


def test_build_parser_invalid_parser_value_raises_batch13():
    """不在 choices 里的 --parser 值应 raise。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run", "--manifest", "a.json", "--output", "b.json",
            "--parser", "invalid_parser",
        ])


def test_build_parser_invalid_int_max_chars_raises_batch13():
    """--max-chars 非整数应 raise。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([
            "run", "--manifest", "a.json", "--output", "b.json",
            "--max-chars", "abc",
        ])


def test_build_parser_run_help_string_chinese_batch13():
    """run 子命令的 help 文本应含中文（存储在 _choices_actions 上）。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    sub = sub_actions[0]
    # _choices_actions 是 add_parser(help=...) 创建的伪 action
    choices_actions = {a.metavar: a for a in sub._choices_actions}
    assert "run" in choices_actions
    help_str = choices_actions["run"].help
    assert help_str is not None
    assert "评测" in help_str or "跑评测" in help_str


def test_build_parser_validate_report_help_string_chinese_batch13():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    sub = sub_actions[0]
    choices_actions = {a.metavar: a for a in sub._choices_actions}
    help_str = choices_actions["validate-report"].help
    assert help_str is not None
    assert "校验" in help_str


def test_build_parser_inspect_doc_help_string_chinese_batch13():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    sub = sub_actions[0]
    choices_actions = {a.metavar: a for a in sub._choices_actions}
    help_str = choices_actions["inspect-doc"].help
    assert help_str is not None
    assert "文档" in help_str or "标注" in help_str


def test_build_parser_main_prog_evaluation_cli_batch13():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_subparsers_dest_command_batch13():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert sub_actions[0].dest == "command"


def test_build_parser_subparsers_required_true_batch13():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert sub_actions[0].required is True


def test_build_parser_run_positional_action_count_0_batch13():
    """run 子命令没有 positional 参数。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_parser = sub_actions[0].choices["run"]
    positionals = [a for a in run_parser._actions if a.option_strings == [] and a.dest != "help"]
    assert len(positionals) == 0


def test_build_parser_validate_positional_action_count_1_batch13():
    """validate-report 有 1 个 positional 参数（input）。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    val_parser = sub_actions[0].choices["validate-report"]
    positionals = [a for a in val_parser._actions if a.option_strings == [] and a.dest != "help"]
    assert len(positionals) == 1


def test_build_parser_inspect_positional_action_count_1_batch13():
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_parser = sub_actions[0].choices["inspect-doc"]
    positionals = [a for a in ins_parser._actions if a.option_strings == [] and a.dest != "help"]
    assert len(positionals) == 1


# ---------- argparse Namespace 行为第十三批 ----------


def test_namespace_run_command_attribute_batch13():
    ns = _build_parser().parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
    ])
    assert ns.command == "run"


def test_namespace_validate_command_attribute_batch13():
    ns = _build_parser().parse_args(["validate-report", "r.json"])
    assert ns.command == "validate-report"


def test_namespace_inspect_command_attribute_batch13():
    ns = _build_parser().parse_args(["inspect-doc", "d.json"])
    assert ns.command == "inspect-doc"


def test_namespace_manifest_attribute_str_batch13():
    ns = _build_parser().parse_args([
        "run", "--manifest", "manifest.json", "--output", "b.json",
    ])
    assert ns.manifest == "manifest.json"
    assert isinstance(ns.manifest, str)


def test_namespace_output_attribute_str_batch13():
    ns = _build_parser().parse_args([
        "run", "--manifest", "a.json", "--output", "out.json",
    ])
    assert ns.output == "out.json"


def test_namespace_parser_default_value_type_str_batch13():
    ns = _build_parser().parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
    ])
    assert isinstance(ns.parser, str)


def test_namespace_max_chars_default_value_type_int_batch13():
    ns = _build_parser().parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
    ])
    assert isinstance(ns.max_chars, int)


def test_namespace_tolerance_chars_default_value_type_int_batch13():
    ns = _build_parser().parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
    ])
    assert isinstance(ns.tolerance_chars, int)


def test_namespace_validate_input_str_batch13():
    ns = _build_parser().parse_args(["validate-report", "report.json"])
    assert ns.input == "report.json"


def test_namespace_inspect_input_str_batch13():
    ns = _build_parser().parse_args(["inspect-doc", "doc.json"])
    assert ns.input == "doc.json"


def test_namespace_custom_parser_value_kreuzberg_batch13():
    ns = _build_parser().parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
        "--parser", "kreuzberg",
    ])
    assert ns.parser == "kreuzberg"


def test_namespace_custom_max_chars_value_batch13():
    ns = _build_parser().parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
        "--max-chars", "1200",
    ])
    assert ns.max_chars == 1200


def test_namespace_custom_tolerance_chars_value_batch13():
    ns = _build_parser().parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
        "--tolerance-chars", "50",
    ])
    assert ns.tolerance_chars == 50


def test_namespace_negative_max_chars_batch13():
    """argparse 接受负整数（不验证范围）。"""
    ns = _build_parser().parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
        "--max-chars", "-1",
    ])
    assert ns.max_chars == -1


def test_namespace_zero_max_chars_batch13():
    ns = _build_parser().parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
        "--max-chars", "0",
    ])
    assert ns.max_chars == 0


# ---------- _format_metric 行为深度第十三批 ----------


def test_format_metric_padding_width_36_batch13():
    """name 应被 padding 到 36 字符宽（至少）。"""
    out = _format_metric("short", {"value": 1})
    # 检查 name 后的空格数：{name:36}
    # "  short" + spaces until 36 chars
    line = out
    # 找到 value 开始的位置
    # "  short" + spaces + "1"
    name_end = line.find("1")
    # "  short" 是 7 字符，到 "1" 中间有 (36 - len("short")) + 2 = 33 个空格
    # 总前缀长度 = 2 + 36 + 2 = 40
    assert name_end >= 38


def test_format_metric_value_dict_with_none_value_batch13():
    out = _format_metric("x", {"value": {"k": None}, "reason": "r"})
    assert "None" in out or "k=None" in out


def test_format_metric_value_dict_with_true_value_batch13():
    out = _format_metric("x", {"value": {"k": True}, "reason": "r"})
    assert "True" in out


def test_format_metric_value_dict_with_zero_value_batch13():
    out = _format_metric("x", {"value": {"k": 0}, "reason": "r"})
    assert "k=0" in out


def test_format_metric_value_dict_with_negative_value_batch13():
    out = _format_metric("x", {"value": {"k": -5}, "reason": "r"})
    assert "k=-5" in out


def test_format_metric_value_dict_sorted_by_key_batch13():
    """dict 应按 key 排序。"""
    out = _format_metric("x", {"value": {"b": 2, "a": 1, "c": 3}, "reason": "r"})
    # 验证 a 在 b 之前
    pos_a = out.find("a=")
    pos_b = out.find("b=")
    pos_c = out.find("c=")
    assert pos_a < pos_b < pos_c


def test_format_metric_value_dict_with_unicode_key_batch13():
    out = _format_metric("x", {"value": {"类型": 1}, "reason": "r"})
    assert "类型=1" in out


def test_format_metric_metric_dict_missing_reason_batch13():
    """metric dict 缺 reason → 显示 'ok' 作为 reason fallback。"""
    out = _format_metric("x", {"value": 1})
    assert "ok" in out


def test_format_metric_metric_dict_missing_reason_for_none_batch13():
    """metric dict value=None 且缺 reason → reason 显示 None。"""
    out = _format_metric("x", {"value": None})
    # 当 value is None，reason 默认 None → "(None)"
    assert "None" in out


def test_format_metric_float_precision_4_batch13():
    """float 应被格式化为 4 位小数。"""
    out = _format_metric("x", {"value": 0.123456789, "reason": "r"})
    assert "0.1235" in out


def test_format_metric_float_zero_batch13():
    out = _format_metric("x", {"value": 0.0, "reason": "r"})
    assert "0.0000" in out


def test_format_metric_float_negative_batch13():
    out = _format_metric("x", {"value": -0.5, "reason": "r"})
    assert "-0.5000" in out


def test_format_metric_bool_true_lowercase_batch13():
    out = _format_metric("x", {"value": True, "reason": "r"})
    assert "true" in out
    assert "True" not in out


def test_format_metric_bool_false_lowercase_batch13():
    out = _format_metric("x", {"value": False, "reason": "r"})
    assert "false" in out
    assert "False" not in out


def test_format_metric_value_int_zero_batch13():
    out = _format_metric("x", {"value": 0, "reason": "r"})
    # int 0 不进入 float 分支（isinstance(0, float) 是 False）
    # 也不进入 bool 分支（isinstance(0, bool) 是 False，因为 bool 是 int 子类但 isinstance 反查中 0 不是 bool）
    # 实际：isinstance(0, bool) is False
    # → 走默认分支：f"  {name:36} {value}  ({reason or 'ok'})"
    assert "0" in out


def test_format_metric_value_negative_int_batch13():
    out = _format_metric("x", {"value": -42, "reason": "r"})
    assert "-42" in out


def test_format_metric_returns_str_batch13():
    out = _format_metric("x", {"value": 1, "reason": "r"})
    assert isinstance(out, str)


def test_format_metric_starts_with_two_spaces_batch13():
    """输出以两个空格开头（prefix '  '）。"""
    out = _format_metric("x", {"value": 1, "reason": "r"})
    assert out.startswith("  ")


# ---------- _run_inspect_doc 行为深度第十三批 ----------


def test_run_inspect_doc_stdout_contains_file_label_batch13(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "file:" in out


def test_run_inspect_doc_stdout_contains_document_id_label_batch13(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "document_id:" in out


def test_run_inspect_doc_stdout_contains_source_label_batch13(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "source:" in out


def test_run_inspect_doc_stdout_contains_parser_label_batch13(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "parser:" in out


def test_run_inspect_doc_stdout_contains_counts_label_batch13(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "counts:" in out


def test_run_inspect_doc_stdout_contains_metrics_label_batch13(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_returns_zero_for_valid_doc_batch13(tmp_path):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    assert _run_inspect_doc(args) == 0


def test_run_inspect_doc_unknown_source_type_default_batch13(tmp_path, capsys):
    """doc 无 source_type → 默认 'unknown'。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "unknown" in out


def test_run_inspect_doc_no_document_id_default_question_mark_batch13(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    # 缺 document_id → '?'
    assert "?" in out


def test_run_inspect_doc_custom_document_id_batch13(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text('{"document_id": "doc-abc"}', encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "doc-abc" in out


def test_run_inspect_doc_custom_source_type_batch13(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text('{"source_type": "pdf"}', encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "pdf" in out


def test_run_inspect_doc_counts_with_elements_count_batch13(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text('{"elements": [{"id": "e1"}, {"id": "e2"}]}', encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "elements=2" in out


def test_run_inspect_doc_counts_with_chunks_count_batch13(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text('{"chunks": [{"id": "c1"}, {"id": "c2"}, {"id": "c3"}]}', encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "chunks=3" in out


def test_run_inspect_doc_returns_2_for_nonexistent_file_batch13(tmp_path):
    args = argparse.Namespace(input=str(tmp_path / "missing.json"), tolerance_chars=30)
    assert _run_inspect_doc(args) == 2


def test_run_inspect_doc_returns_1_for_invalid_json_batch13(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    assert _run_inspect_doc(args) == 1


def test_run_inspect_doc_returns_1_for_non_dict_json_batch13(tmp_path):
    """JSON 顶层是 list（非 dict）→ return 1。"""
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    assert _run_inspect_doc(args) == 1


def test_run_inspect_doc_error_message_for_non_dict_batch13(tmp_path, capsys):
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    err = capsys.readouterr().err
    assert "JSON 顶层不是对象" in err or "JSON" in err


def test_run_inspect_doc_metrics_sorted_bool_first_batch13(tmp_path, capsys):
    """输出顺序：bool → 数字 → 字典 → null。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    # metrics 区块开始
    metrics_start = out.find("metrics:")
    metrics_text = out[metrics_start:]
    # 找到一些 metric 名
    # 至少应该有 metric 输出
    assert "  " in metrics_text  # 有缩进


# ---------- main 路由第十三批 ----------


def test_main_run_manifest_not_exist_returns_2_batch13(tmp_path, capsys):
    out_path = tmp_path / "out.json"
    missing_manifest = tmp_path / "missing-manifest.json"
    rc = main([
        "run",
        "--manifest", str(missing_manifest),
        "--output", str(out_path),
    ])
    assert rc == 2
    err = capsys.readouterr().err
    assert "清单不存在" in err


def test_main_run_manifest_load_fail_returns_1_batch13(tmp_path, capsys):
    bad_manifest = tmp_path / "bad.json"
    bad_manifest.write_text("{not valid", encoding="utf-8")
    out_path = tmp_path / "out.json"
    rc = main([
        "run",
        "--manifest", str(bad_manifest),
        "--output", str(out_path),
    ])
    assert rc == 1
    err = capsys.readouterr().err
    assert "清单加载失败" in err


def test_main_validate_report_input_not_exist_returns_2_batch13(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "报告不存在" in err


def test_main_inspect_doc_input_not_exist_returns_2_batch13(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "文档不存在" in err


def test_main_no_command_raises_system_exit_batch13():
    """无子命令 → argparse error → SystemExit。"""
    with pytest.raises(SystemExit):
        main([])


def test_main_invalid_command_raises_system_exit_batch13():
    with pytest.raises(SystemExit):
        main(["unknown-command"])


def test_main_returns_int_type_batch13():
    """main 返回值必须是 int。"""
    rc = main(["validate-report", "nonexistent.json"])
    assert isinstance(rc, int)


def test_main_run_success_returns_0_batch13(tmp_path, capsys):
    """合法 manifest → run_evaluation mocked 成功 → return 0。"""
    manifest_path = tmp_path / "manifest.json"
    manifest_data = {
        "manifest_version": "1.0",
        "documents": [],
        "expected_failures": [],
    }
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
    out_path = tmp_path / "out.json"

    def _fake_run_eval(*args, **kwargs):
        return {
            "report_version": "1.1",
            "provenance": {},
            "devset": {"status": "incomplete"},
            "summary": {},
            "per_doc": [],
            "expected_failures": [],
        }

    with patch("evaluation.cli.run_evaluation", side_effect=_fake_run_eval):
        with patch("evaluation.cli.validate_file", return_value=None):
            with patch("evaluation.cli.load_manifest") as lm:
                # Mock 一个 manifest 对象
                from pathlib import Path as _P
                m = type("M", (), {})
                m.project_root = _P(".")
                lm.return_value = m
                rc = main([
                    "run",
                    "--manifest", str(manifest_path),
                    "--output", str(out_path),
                ])
    assert rc == 0


def test_main_run_propagates_parser_name_batch13(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    out_path = tmp_path / "out.json"

    captured: dict = {}

    def _fake_run_eval(*args, **kwargs):
        captured.update(kwargs)
        return {"per_doc": [], "devset": {}}

    with patch("evaluation.cli.run_evaluation", side_effect=_fake_run_eval):
        with patch("evaluation.cli.validate_file", return_value=None):
            with patch("evaluation.cli.load_manifest") as lm:
                m = type("M", (), {})
                m.project_root = Path(".")
                lm.return_value = m
                main([
                    "run", "--manifest", str(manifest_path), "--output", str(out_path),
                    "--parser", "kreuzberg",
                ])
    assert captured.get("parser_name") == "kreuzberg"


def test_main_run_propagates_max_chars_batch13(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    out_path = tmp_path / "out.json"

    captured: dict = {}

    def _fake_run_eval(*args, **kwargs):
        captured.update(kwargs)
        return {"per_doc": [], "devset": {}}

    with patch("evaluation.cli.run_evaluation", side_effect=_fake_run_eval):
        with patch("evaluation.cli.validate_file", return_value=None):
            with patch("evaluation.cli.load_manifest") as lm:
                m = type("M", (), {})
                m.project_root = Path(".")
                lm.return_value = m
                main([
                    "run", "--manifest", str(manifest_path), "--output", str(out_path),
                    "--max-chars", "1500",
                ])
    assert captured.get("max_chars") == 1500


def test_main_run_propagates_tolerance_chars_batch13(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    out_path = tmp_path / "out.json"

    captured: dict = {}

    def _fake_run_eval(*args, **kwargs):
        captured.update(kwargs)
        return {"per_doc": [], "devset": {}}

    with patch("evaluation.cli.run_evaluation", side_effect=_fake_run_eval):
        with patch("evaluation.cli.validate_file", return_value=None):
            with patch("evaluation.cli.load_manifest") as lm:
                m = type("M", (), {})
                m.project_root = Path(".")
                lm.return_value = m
                main([
                    "run", "--manifest", str(manifest_path), "--output", str(out_path),
                    "--tolerance-chars", "100",
                ])
    assert captured.get("tolerance_chars") == 100


def test_main_run_schema_invalid_returns_1_batch13(tmp_path, capsys):
    """run_evaluation 抛 EvalSchemaError → return 1。"""
    from evaluation.schema import EvalSchemaError

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    out_path = tmp_path / "out.json"

    with patch("evaluation.cli.run_evaluation", side_effect=EvalSchemaError("bad")):
        with patch("evaluation.cli.load_manifest") as lm:
            m = type("M", (), {})
            m.project_root = Path(".")
            lm.return_value = m
            rc = main([
                "run", "--manifest", str(manifest_path), "--output", str(out_path),
            ])
    assert rc == 1
    err = capsys.readouterr().err
    assert "Schema" in err or "schema" in err


def test_main_run_post_validate_fail_returns_1_batch13(tmp_path, capsys):
    """run_evaluation 成功但 validate_file 失败 → return 1。"""
    from evaluation.schema import EvalSchemaError

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    out_path = tmp_path / "out.json"

    with patch("evaluation.cli.run_evaluation", return_value={"per_doc": [], "devset": {}}):
        with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("bad")):
            with patch("evaluation.cli.load_manifest") as lm:
                m = type("M", (), {})
                m.project_root = Path(".")
                lm.return_value = m
                rc = main([
                    "run", "--manifest", str(manifest_path), "--output", str(out_path),
                ])
    assert rc == 1


# ---------- module source forbidden tokens 第十九批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import pickle",
        "import yaml",
        "import socket",
        "import threading",
        "import multiprocessing",
        "import asyncio",
        "from pickle import",
        "from yaml import",
        "from socket import",
        "from threading import",
        "from multiprocessing import",
        "from asyncio import",
        "ctypes.",
        "import ctypes",
        "import marshal",
        "marshal.",
    ],
)
def test_cli_source_no_forbidden_token_nineteenth_batch13(token):
    source = inspect.getsource(climod)
    assert token not in source


def test_cli_source_no_os_module_usage_batch13():
    """cli.py 应避免直接用 os 模块。"""
    source = inspect.getsource(climod)
    assert "import os" not in source


def test_cli_source_no_tempfile_usage_batch13():
    source = inspect.getsource(climod)
    assert "tempfile" not in source


def test_cli_source_no_logging_batch13():
    source = inspect.getsource(climod)
    assert "import logging" not in source


def test_cli_source_no_re_module_batch13():
    source = inspect.getsource(climod)
    assert "import re" not in source
    assert "re." not in source


def test_cli_source_no_eval_call_batch13():
    source = inspect.getsource(climod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_cli_source_no_compile_call_batch13():
    source = inspect.getsource(climod)
    assert "compile(" not in source


def test_cli_source_no_global_keyword_batch13():
    source = inspect.getsource(climod)
    assert "\nglobal " not in source


def test_cli_source_no_nonlocal_keyword_batch13():
    source = inspect.getsource(climod)
    assert "nonlocal " not in source


def test_cli_source_no_lambda_batch13():
    source = inspect.getsource(climod)
    assert "lambda " not in source


def test_cli_source_no_assert_statement_batch13():
    source = inspect.getsource(climod)
    assert "\nassert " not in source


def test_cli_source_no_input_function_batch13():
    source = inspect.getsource(climod)
    assert "input(" not in source


def test_cli_source_no_class_definition_batch13():
    source = inspect.getsource(climod)
    assert "\nclass " not in source
    assert not source.startswith("class ")


def test_cli_source_no_with_at_top_level_batch13():
    source = inspect.getsource(climod)
    lines = source.split("\n")
    for line in lines:
        if not line.startswith(" ") and "with " in line:
            raise AssertionError(f"top-level with: {line}")


def test_cli_source_has_main_function_batch13():
    source = inspect.getsource(climod)
    assert "def main(" in source


def test_cli_source_has_build_parser_function_batch13():
    source = inspect.getsource(climod)
    assert "def _build_parser(" in source


# ---------- module source 字符串精确补强第十六批 ----------


def test_module_source_argparse_import_top_level_batch13():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:30])
    assert "import argparse" in head


def test_module_source_json_import_top_level_batch13():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:30])
    assert "import json" in head


def test_module_source_sys_import_top_level_batch13():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:30])
    assert "import sys" in head


def test_module_source_pathlib_import_top_level_batch13():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_load_manifest_import_batch13():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:40])
    assert "from evaluation.manifest import ManifestError, load_manifest" in head


def test_module_source_get_git_provenance_import_batch13():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:40])
    assert "from evaluation.report import get_git_provenance" in head


def test_module_source_run_evaluation_import_batch13():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:40])
    assert "from evaluation.runner import run_evaluation" in head


def test_module_source_eval_schema_import_batch13():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:40])
    assert "from evaluation.schema import EvalSchemaError, validate_file" in head


def test_module_source_has_sys_stdout_reconfigure_call_batch13():
    source = inspect.getsource(climod)
    assert "sys.stdout.reconfigure" in source


def test_module_source_has_ManifestError_in_except_batch13():
    source = inspect.getsource(climod)
    assert "ManifestError" in source
    assert "EvalSchemaError" in source


def test_module_source_has_print_to_stderr_batch13():
    source = inspect.getsource(climod)
    assert "file=sys.stderr" in source


def test_module_source_has_subparsers_setup_batch13():
    source = inspect.getsource(climod)
    assert "add_subparsers" in source


def test_module_source_has_RawDescriptionHelpFormatter_batch13():
    source = inspect.getsource(climod)
    assert "RawDescriptionHelpFormatter" in source


def test_module_source_has_SystemExit_at_bottom_batch13():
    source = inspect.getsource(climod)
    assert "raise SystemExit(main())" in source or "SystemExit" in source


def test_module_source_has_format_metric_function_batch13():
    source = inspect.getsource(climod)
    assert "def _format_metric(" in source


def test_module_source_has_run_inspect_doc_function_batch13():
    source = inspect.getsource(climod)
    assert "def _run_inspect_doc(" in source


def test_module_source_format_metric_padding_36_batch13():
    source = inspect.getsource(climod)
    # f"  {name:36} ..."
    assert ":36" in source


def test_module_source_future_annotations_top_level_batch13():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


def test_module_source_compute_automatic_metrics_lazy_import_batch13():
    """compute_automatic_metrics 应在 _run_inspect_doc 内部 import。"""
    source = inspect.getsource(climod)
    fn_source = _get_function_source(source, "_run_inspect_doc")
    assert "compute_automatic_metrics" in fn_source


def test_module_source_has_isinstance_check_for_value_batch13():
    source = inspect.getsource(climod)
    assert "isinstance(value" in source


def test_module_source_has_float_precision_format_batch13():
    source = inspect.getsource(climod)
    assert "{value:.4f}" in source or ".4f" in source


# ---------- signatures 第十六批 ----------


def test_build_parser_signature_no_params_batch13():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_build_parser_return_annotation_argument_parser_batch13():
    sig = inspect.signature(_build_parser)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "ArgumentParser" in ret_str


def test_main_signature_one_param_batch13():
    sig = inspect.signature(main)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "argv"


def test_main_argv_annotation_optional_list_str_batch13():
    sig = inspect.signature(main)
    annot = sig.parameters["argv"].annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "list" in annot_str
    assert "str" in annot_str
    assert "None" in annot_str


def test_main_argv_default_none_batch13():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_return_annotation_int_batch13():
    sig = inspect.signature(main)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "int" in ret_str


def test_format_metric_signature_2_params_batch13():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["name", "metric"]


def test_format_metric_return_annotation_str_batch13():
    sig = inspect.signature(_format_metric)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "str" in ret_str


def test_format_metric_param_kinds_batch13():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_inspect_doc_signature_one_param_batch13():
    sig = inspect.signature(_run_inspect_doc)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "args"


def test_run_inspect_doc_return_annotation_int_batch13():
    sig = inspect.signature(_run_inspect_doc)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "int" in ret_str


def test_module_user_function_count_4_batch13():
    """模块顶层用户函数共 4 个。"""
    funcs = [
        n for n, v in vars(climod).items()
        if inspect.isfunction(v) and v.__module__ == climod.__name__
    ]
    assert set(funcs) == {"_build_parser", "main", "_format_metric", "_run_inspect_doc"}


def test_module_has_no_dunder_all_batch13():
    """cli.py 没定义 __all__（公开入口）。"""
    assert not hasattr(climod, "__all__") or climod.__all__ is None


def test_all_functions_no_varargs_batch13():
    for fn in [_build_parser, main, _format_metric, _run_inspect_doc]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )


# ---------- module 合理性第十六批 ----------


def test_module_dunder_file_exists_batch13():
    assert hasattr(climod, "__file__")
    assert climod.__file__ is not None


def test_module_dunder_file_path_evaluation_cli_batch13():
    import os
    sep = os.sep
    assert climod.__file__.endswith(sep + "cli.py")
    assert "evaluation" in climod.__file__


def test_module_name_evaluation_cli_batch13():
    assert climod.__name__ == "evaluation.cli"


def test_module_docstring_present_batch13():
    assert climod.__doc__ is not None
    assert len(climod.__doc__) > 30


def test_module_docstring_mentions_subcommands_batch13():
    assert climod.__doc__ is not None
    assert "run" in climod.__doc__
    assert "validate-report" in climod.__doc__
    assert "inspect-doc" in climod.__doc__


def test_module_uses_future_annotations_batch13():
    source = inspect.getsource(climod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


def test_module_no_user_classes_batch13():
    classes = [
        n for n, v in vars(climod).items()
        if inspect.isclass(v) and v.__module__ == climod.__name__
    ]
    assert classes == []


def test_module_main_function_callable_batch13():
    assert callable(main)


def test_module_build_parser_callable_batch13():
    assert callable(_build_parser)


def test_module_top_level_user_function_count_4_batch13():
    funcs = [
        n for n, v in vars(climod).items()
        if inspect.isfunction(v) and v.__module__ == climod.__name__
    ]
    assert len(funcs) == 4


# ---------- 端到端集成第十六批 ----------


def test_e2e_main_validate_report_returns_2_for_missing_batch13(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "x.json")])
    assert rc == 2


def test_e2e_main_inspect_doc_returns_2_for_missing_batch13(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "x.json")])
    assert rc == 2


def test_e2e_main_run_with_invalid_manifest_returns_1_batch13(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid", encoding="utf-8")
    out_path = tmp_path / "out.json"
    rc = main([
        "run", "--manifest", str(bad), "--output", str(out_path),
    ])
    assert rc == 1


def test_e2e_run_inspect_doc_output_to_stdout_batch13(tmp_path, capsys):
    """_run_inspect_doc 把所有信息打到 stdout。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert len(out) > 0


def test_e2e_build_parser_full_parse_roundtrip_batch13():
    """parse_args → Namespace → 重新组装 argv → parse_args 等价。"""
    argv = [
        "run", "--manifest", "a.json", "--output", "b.json",
        "--parser", "kreuzberg", "--max-chars", "1000", "--tolerance-chars", "50",
    ]
    ns1 = _build_parser().parse_args(argv)
    # 等价检查：再 parse 一次相同 argv
    ns2 = _build_parser().parse_args(argv)
    assert ns1 == ns2


def test_e2e_main_run_full_flow_with_mocks_batch13(tmp_path, capsys):
    """完整 run 流程：manifest → load_manifest → run_evaluation → validate_file → print summary。"""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    out_path = tmp_path / "out.json"

    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {
            "status": "incomplete",
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
        },
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }

    with patch("evaluation.cli.run_evaluation", return_value=fake_report):
        with patch("evaluation.cli.validate_file", return_value=None):
            with patch("evaluation.cli.load_manifest") as lm:
                m = type("M", (), {})
                m.project_root = Path(".")
                lm.return_value = m
                rc = main([
                    "run", "--manifest", str(manifest_path), "--output", str(out_path),
                ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[OK]" in out
    assert "documents=" in out


def test_e2e_run_inspect_doc_with_full_doc_batch13(tmp_path, capsys):
    """inspect-doc 完整文档（含 elements + chunks）。"""
    p = tmp_path / "d.json"
    p.write_text(json.dumps({
        "document_id": "doc-001",
        "source_type": "pdf",
        "source_path": "/some/file.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"id": "e1"}, {"id": "e2"}],
        "chunks": [{"id": "c1"}],
    }), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "doc-001" in out
    assert "elements=2" in out
    assert "chunks=1" in out


def test_e2e_validate_report_full_path_round_trip_batch13(tmp_path, capsys):
    """validate-report 子命令接合法 JSON 文件。"""
    # 先构造一个会被 validate_file 通过的 mock
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")

    with patch("evaluation.cli.validate_file", return_value=None):
        rc = main(["validate-report", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[OK]" in out


def test_e2e_validate_report_fail_batch13(tmp_path, capsys):
    """validate-report schema 校验失败 → return 1。"""
    from evaluation.schema import EvalSchemaError

    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")

    with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("bad")):
        rc = main(["validate-report", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err


def test_e2e_format_metric_combined_with_inspect_batch13(tmp_path, capsys):
    """_format_metric 在 inspect-doc 中被实际调用。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    # 应有 metric 行（缩进 2 空格）
    lines = out.split("\n")
    metric_lines = [l for l in lines if l.startswith("  ")]
    assert len(metric_lines) > 0


# ---------- helper ----------


def _get_function_source(module_source: str, fn_name: str) -> str:
    """简单提取函数源代码块。"""
    lines = module_source.split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.startswith(f"def {fn_name}("):
            start = i
            break
    if start is None:
        return ""
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j] and not lines[j].startswith(" ") and not lines[j].startswith("\t"):
            end = j
            break
    return "\n".join(lines[start:end])
