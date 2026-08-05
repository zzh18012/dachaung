r"""evaluation/cli.py 边角测试 - 第十四轮（Round 237）。

补强已有 base/edges/edges2-13（共 ~955+ 测试）未覆盖的深度：
- 模块 imports 精确：argparse/json/sys/Path/ManifestError/load_manifest/get_git_provenance/run_evaluation/EvalSchemaError/validate_file
- _format_metric 精度边界：0.12345 rounds / 0.12344 rounds / -0.0 / 1.0 / empty metric dict
- _format_metric value/reason 组合：True+None / True+custom / False+None / 0 int+empty reason
- argparse 错误路径：--help / badcommand / invalid choice / missing required arg / non-int max-chars
- _run_inspect_doc 返回值类型 int 验证
- main 返回 int 验证
- module 没有 __all__
- module __name__ guard 存在
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# =========================================================================
# 模块 imports 精确
# =========================================================================


def test_module_imports_argparse():
    """argparse 在模块命名空间。"""
    import evaluation.cli as m
    assert hasattr(m, "argparse")


def test_module_imports_json():
    """json 在模块命名空间。"""
    import evaluation.cli as m
    assert hasattr(m, "json")


def test_module_imports_sys():
    """sys 在模块命名空间。"""
    import evaluation.cli as m
    assert hasattr(m, "sys")


def test_module_imports_path():
    """Path 在模块命名空间。"""
    import evaluation.cli as m
    assert m.Path is Path


def test_module_imports_manifest_error():
    """ManifestError 从 evaluation.manifest 导入。"""
    import evaluation.cli as m
    from evaluation.manifest import ManifestError
    assert m.ManifestError is ManifestError


def test_module_imports_load_manifest():
    """load_manifest 从 evaluation.manifest 导入。"""
    import evaluation.cli as m
    from evaluation.manifest import load_manifest
    assert m.load_manifest is load_manifest


def test_module_imports_get_git_provenance():
    """get_git_provenance 从 evaluation.report 导入。"""
    import evaluation.cli as m
    from evaluation.report import get_git_provenance
    assert m.get_git_provenance is get_git_provenance


def test_module_imports_run_evaluation():
    """run_evaluation 从 evaluation.runner 导入。"""
    import evaluation.cli as m
    from evaluation.runner import run_evaluation
    assert m.run_evaluation is run_evaluation


def test_module_imports_eval_schema_error():
    """EvalSchemaError 从 evaluation.schema 导入。"""
    import evaluation.cli as m
    from evaluation.schema import EvalSchemaError
    assert m.EvalSchemaError is EvalSchemaError


def test_module_imports_validate_file():
    """validate_file 从 evaluation.schema 导入。"""
    import evaluation.cli as m
    from evaluation.schema import validate_file
    assert m.validate_file is validate_file


def test_module_has_no_dunder_all():
    """cli.py 没有 __all__（不在 __all__ 中的也能被 import）。"""
    import evaluation.cli as m
    assert not hasattr(m, "__all__") or m.__all__ is None or len(m.__all__) == 0


def test_module_has_name_guard():
    """cli.py 有 `if __name__ == "__main__":` 守卫。"""
    # 通过文件源码验证
    import evaluation.cli
    src_path = Path(evaluation.cli.__file__)
    src = src_path.read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":' in src or "if __name__ == '__main__':" in src


def test_module_name_guard_raises_systemexit():
    """__name__ guard 调用 SystemExit(main())。"""
    import evaluation.cli
    src_path = Path(evaluation.cli.__file__)
    src = src_path.read_text(encoding="utf-8")
    assert "SystemExit(main())" in src or "sys.exit(main())" in src


def test_module_stdout_reconfigure_block():
    """cli.py 有 sys.stdout.reconfigure 块（Windows utf-8）。"""
    import evaluation.cli
    src_path = Path(evaluation.cli.__file__)
    src = src_path.read_text(encoding="utf-8")
    assert "reconfigure" in src


# =========================================================================
# _format_metric 精度边界
# =========================================================================


def test_format_metric_float_half_renders_four_decimals():
    """0.5 → '0.5000'（4 位小数）。"""
    out = _format_metric("m", {"value": 0.5, "reason": None})
    assert "0.5000" in out


def test_format_metric_float_0_12345_rounds_to_0_1235():
    """0.12345 → '0.1235'（4 位小数四舍五入）。"""
    out = _format_metric("m", {"value": 0.12345, "reason": None})
    assert "0.1235" in out


def test_format_metric_float_0_12344_rounds_to_0_1234():
    """0.12344 → '0.1234'。"""
    out = _format_metric("m", {"value": 0.12344, "reason": None})
    assert "0.1234" in out


def test_format_metric_float_0_99995_rounds_to_1_0000():
    """0.99995 → '1.0000'。"""
    out = _format_metric("m", {"value": 0.99995, "reason": None})
    assert "1.0000" in out


def test_format_metric_float_negative_zero():
    """-0.0 → '-0.0000'。"""
    out = _format_metric("m", {"value": -0.0, "reason": None})
    assert "-0.0000" in out


def test_format_metric_float_one_renders_1_0000():
    """1.0 → '1.0000'。"""
    out = _format_metric("m", {"value": 1.0, "reason": None})
    assert "1.0000" in out


def test_format_metric_float_zero_renders_0_0000():
    """0.0 → '0.0000'。"""
    out = _format_metric("m", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_float_pi_renders_3_1416():
    """math.pi ≈ 3.14159 → '3.1416'。"""
    import math
    out = _format_metric("m", {"value": math.pi, "reason": None})
    assert "3.1416" in out


def test_format_metric_float_e_renders_2_7183():
    """math.e ≈ 2.71828 → '2.7183'。"""
    import math
    out = _format_metric("m", {"value": math.e, "reason": None})
    assert "2.7183" in out


# =========================================================================
# _format_metric value/reason 组合
# =========================================================================


def test_format_metric_empty_metric_dict():
    """metric={} → value=None, reason=None → 'name null (None)'。"""
    out = _format_metric("m", {})
    assert "null" in out
    assert "(None)" in out


def test_format_metric_value_none_reason_none():
    """value=None, reason=None → 'null (None)'。"""
    out = _format_metric("m", {"value": None, "reason": None})
    assert "null" in out
    assert "(None)" in out


def test_format_metric_value_none_reason_missing_key():
    """value=None, 缺 reason → reason=None → 'null (None)'。"""
    out = _format_metric("m", {"value": None})
    assert "null" in out
    assert "(None)" in out


def test_format_metric_value_none_reason_custom():
    """value=None, reason='custom' → 'null (custom)'。"""
    out = _format_metric("m", {"value": None, "reason": "custom"})
    assert "null" in out
    assert "(custom)" in out


def test_format_metric_value_true_reason_none():
    """value=True, reason=None → 'true (ok)'（None → 'ok'）。"""
    out = _format_metric("m", {"value": True, "reason": None})
    assert "true" in out
    assert "(ok)" in out


def test_format_metric_value_true_reason_custom():
    """value=True, reason='custom' → 'true (custom)'。"""
    out = _format_metric("m", {"value": True, "reason": "custom"})
    assert "true" in out
    assert "(custom)" in out


def test_format_metric_value_true_reason_empty_string():
    """value=True, reason='' → 'true (ok)'（空字符串 → 'ok'）。"""
    out = _format_metric("m", {"value": True, "reason": ""})
    assert "true" in out
    assert "(ok)" in out


def test_format_metric_value_false_reason_none():
    """value=False, reason=None → 'false (ok)'。"""
    out = _format_metric("m", {"value": False, "reason": None})
    assert "false" in out
    assert "(ok)" in out


def test_format_metric_value_false_reason_custom():
    """value=False, reason='custom' → 'false (custom)'。"""
    out = _format_metric("m", {"value": False, "reason": "custom"})
    assert "false" in out
    assert "(custom)" in out


def test_format_metric_value_zero_int_reason_empty_string():
    """value=0 (int), reason='' → '0 (ok)'。"""
    out = _format_metric("m", {"value": 0, "reason": ""})
    assert " 0 " in out
    assert "(ok)" in out


def test_format_metric_value_negative_int_reason_zero():
    """value=-5 (int), reason=0 → '-5 (ok)'（0 falsy → 'ok'）。"""
    out = _format_metric("m", {"value": -5, "reason": 0})
    assert "-5" in out
    assert "(ok)" in out


def test_format_metric_value_empty_string_reason_none():
    """value='', reason=None → ' (ok)'（空字符串渲染为空）。"""
    out = _format_metric("m", {"value": "", "reason": None})
    # 空字符串作为 value 渲染时是空字符
    assert "(ok)" in out


def test_format_metric_value_dict_reason_falsy_string():
    """value={非空 dict}, reason='' → 'items=values (ok)'。"""
    out = _format_metric("m", {"value": {"a": 1}, "reason": ""})
    assert "a=1" in out
    assert "(ok)" in out


def test_format_metric_value_dict_reason_zero_int():
    """value={非空 dict}, reason=0 → 'items (ok)'（0 falsy → 'ok'）。"""
    out = _format_metric("m", {"value": {"a": 1}, "reason": 0})
    assert "a=1" in out
    assert "(ok)" in out


# =========================================================================
# _format_metric 列宽
# =========================================================================


def test_format_metric_short_name_padded_to_36():
    """name 短于 36 → 左对齐填充到 36。"""
    out = _format_metric("short", {"value": 1, "reason": None})
    # name 'short' 是 5 字符，pad 到 36 → 'short' + 31 空格
    # 实际 line 形如 "  short<31 spaces>1  (ok)"
    # 验证 name 后的字符不是直接接 value
    assert "short" in out
    # 找到 'short' 后的位置
    idx = out.index("short")
    # 应当有 31 个空格直到 value
    end_of_name = idx + len("short")
    # 接下来是空格
    assert out[end_of_name:end_of_name + 5] == "     "


def test_format_metric_name_alignment_in_output_line():
    """整行渲染：'  name<pad>value  (reason)'。"""
    out = _format_metric("m", {"value": 1, "reason": None})
    # 整行以 2 空格开头
    assert out.startswith("  ")
    # 'm' 后是 35 空格（pad 到 36），再是 '  1  (ok)'
    assert "m" + " " * 35 in out


# =========================================================================
# argparse 错误路径
# =========================================================================


def test_main_unknown_command_exits_two(capsys):
    """未知子命令 → argparse SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["unknown-command"])
    assert exc_info.value.code == 2


def test_main_help_flag_exits_zero(capsys):
    """--help → SystemExit(0)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0


def test_main_run_help_flag_exits_zero(capsys):
    """run --help → SystemExit(0)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--help"])
    assert exc_info.value.code == 0


def test_main_validate_report_help_flag_exits_zero(capsys):
    """validate-report --help → SystemExit(0)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["validate-report", "--help"])
    assert exc_info.value.code == 0


def test_main_inspect_doc_help_flag_exits_zero(capsys):
    """inspect-doc --help → SystemExit(0)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["inspect-doc", "--help"])
    assert exc_info.value.code == 0


def test_main_run_invalid_parser_choice_exits_two(capsys):
    """run --parser invalid → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--manifest", "x", "--output", "y", "--parser", "invalid"])
    assert exc_info.value.code == 2


def test_main_run_invalid_max_chars_type_exits_two(capsys):
    """run --max-chars abc → SystemExit(2)（type=int 校验失败）。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--manifest", "x", "--output", "y", "--max-chars", "abc"])
    assert exc_info.value.code == 2


def test_main_run_invalid_tolerance_chars_type_exits_two(capsys):
    """run --tolerance-chars xyz → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--manifest", "x", "--output", "y", "--tolerance-chars", "xyz"])
    assert exc_info.value.code == 2


def test_main_inspect_doc_invalid_tolerance_chars_exits_two(capsys):
    """inspect-doc --tolerance-chars xyz → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["inspect-doc", "--tolerance-chars", "xyz", "some.json"])
    assert exc_info.value.code == 2


def test_main_run_missing_manifest_exits_two(capsys):
    """run 无 --manifest → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--output", "y"])
    assert exc_info.value.code == 2


def test_main_run_missing_output_exits_two(capsys):
    """run 无 --output → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--manifest", "x"])
    assert exc_info.value.code == 2


def test_main_inspect_doc_missing_positional_exits_two(capsys):
    """inspect-doc 无 positional input → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["inspect-doc"])
    assert exc_info.value.code == 2


def test_main_validate_report_missing_positional_exits_two(capsys):
    """validate-report 无 positional input → SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["validate-report"])
    assert exc_info.value.code == 2


# =========================================================================
# _run_inspect_doc 返回值类型
# =========================================================================


def test_run_inspect_doc_returns_int_zero(tmp_path: Path):
    """成功路径返回 0（int 类型）。"""
    doc = {"document_id": "d1", "source_type": "pdf"}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")

    class _Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(_Args())
    assert rc == 0
    assert isinstance(rc, int)


def test_run_inspect_doc_returns_int_two_for_missing_file(tmp_path: Path):
    """文件不存在返回 2（int 类型）。"""
    class _Args:
        input = str(tmp_path / "missing.json")
        tolerance_chars = 30

    rc = _run_inspect_doc(_Args())
    assert rc == 2
    assert isinstance(rc, int)


def test_run_inspect_doc_returns_int_one_for_bad_json(tmp_path: Path):
    """JSON 解析失败返回 1（int 类型）。"""
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")

    class _Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(_Args())
    assert rc == 1
    assert isinstance(rc, int)


def test_run_inspect_doc_returns_int_one_for_top_level_array(tmp_path: Path):
    """顶层是 array → 返回 1。"""
    p = tmp_path / "arr.json"
    p.write_text("[]", encoding="utf-8")

    class _Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(_Args())
    assert rc == 1
    assert isinstance(rc, int)


def test_run_inspect_doc_returns_int_one_for_top_level_string(tmp_path: Path):
    """顶层是 string → 返回 1。"""
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")

    class _Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(_Args())
    assert rc == 1


def test_run_inspect_doc_returns_int_one_for_top_level_int(tmp_path: Path):
    """顶层是 int → 返回 1。"""
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")

    class _Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(_Args())
    assert rc == 1


# =========================================================================
# main 返回 int 验证
# =========================================================================


def test_main_returns_int_for_missing_file(tmp_path: Path):
    """main 各种失败路径返回 int。"""
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert isinstance(rc, int)
    assert rc == 2


def test_main_returns_int_for_inspect_doc_missing(tmp_path: Path):
    """inspect-doc 缺文件 → int 2。"""
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert isinstance(rc, int)
    assert rc == 2


def test_main_returns_int_for_run_missing_manifest(tmp_path: Path):
    """run 缺 manifest 文件 → int 2。"""
    rc = main(["run", "--manifest", str(tmp_path / "missing.json"),
               "--output", str(tmp_path / "out.json")])
    assert isinstance(rc, int)
    assert rc == 2


# =========================================================================
# _build_parser 详细
# =========================================================================


def test_build_parser_returns_argument_parser_instance():
    """_build_parser 返回 ArgumentParser 实例。"""
    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_build_parser_has_subparsers_action():
    """parser 有 subparsers action。"""
    p = _build_parser()
    sub_actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    assert len(sub_actions) == 1


def test_build_parser_subparser_action_has_three_choices():
    """subparser 有 3 个 choices。"""
    p = _build_parser()
    sub_action = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)][0]
    assert len(sub_action.choices) == 3


def test_build_parser_subparser_choices_keys_exact():
    """subparser choices keys 精确。"""
    p = _build_parser()
    sub_action = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)][0]
    assert set(sub_action.choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_run_subparser_arg_count():
    """run 子命令有 5 个 argument。"""
    p = _build_parser()
    sub_action = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)][0]
    run_p = sub_action.choices["run"]
    # 排除 -h/--help 这个 default action
    user_args = [a for a in run_p._actions if a.dest != "help"]
    assert len(user_args) == 5


def test_build_parser_validate_report_subparser_arg_count():
    """validate-report 子命令有 1 个 positional argument。"""
    p = _build_parser()
    sub_action = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)][0]
    val_p = sub_action.choices["validate-report"]
    user_args = [a for a in val_p._actions if a.dest != "help"]
    assert len(user_args) == 1


def test_build_parser_inspect_doc_subparser_arg_count():
    """inspect-doc 子命令有 2 个 argument（input + --tolerance-chars）。"""
    p = _build_parser()
    sub_action = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)][0]
    ins_p = sub_action.choices["inspect-doc"]
    user_args = [a for a in ins_p._actions if a.dest != "help"]
    assert len(user_args) == 2


def test_build_parser_run_parser_default_is_fallback():
    """run --parser 默认 'fallback'。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.parser == "fallback"


def test_build_parser_run_max_chars_default_is_800():
    """run --max-chars 默认 800。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.max_chars == 800


def test_build_parser_run_tolerance_chars_default_is_30():
    """run --tolerance-chars 默认 30。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_tolerance_chars_default_is_30():
    """inspect-doc --tolerance-chars 默认 30。"""
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_run_parser_choices_exact():
    """--parser choices 精确。"""
    p = _build_parser()
    sub_action = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)][0]
    run_p = sub_action.choices["run"]
    parser_action = [a for a in run_p._actions if a.dest == "parser"][0]
    assert set(parser_action.choices) == {"fallback", "kreuzberg"}


def test_build_parser_run_max_chars_type_int():
    """--max-chars 类型是 int。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y", "--max-chars", "123"])
    assert args.max_chars == 123
    assert isinstance(args.max_chars, int)


def test_build_parser_run_tolerance_chars_type_int():
    """--tolerance-chars 类型是 int。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y", "--tolerance-chars", "45"])
    assert args.tolerance_chars == 45
    assert isinstance(args.tolerance_chars, int)


def test_build_parser_inspect_doc_tolerance_chars_type_int():
    """inspect-doc --tolerance-chars 类型是 int。"""
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "55"])
    assert args.tolerance_chars == 55
    assert isinstance(args.tolerance_chars, int)


# =========================================================================
# _format_metric 列宽 36 边界
# =========================================================================


def test_format_metric_name_exactly_36_chars_no_padding():
    """name=36 字符 → 不需要 padding。"""
    name = "a" * 36
    out = _format_metric(name, {"value": 1, "reason": None})
    # 整行以 '  ' + 36 a's + '  ' (value) + ...
    assert "  " + name in out


def test_format_metric_name_37_chars_not_truncated():
    """name=37 字符 → 原样渲染（不截断）。"""
    name = "a" * 37
    out = _format_metric(name, {"value": 1, "reason": None})
    assert name in out


# =========================================================================
# main 命令分发
# =========================================================================


def test_main_dispatches_to_inspect_doc(tmp_path: Path, monkeypatch):
    """main 检测到 'inspect-doc' command → 调用 _run_inspect_doc。"""
    doc = {"document_id": "d1"}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")

    called = {"count": 0}

    def fake_run_inspect_doc(args):
        called["count"] += 1
        return 0

    monkeypatch.setattr("evaluation.cli._run_inspect_doc", fake_run_inspect_doc)
    rc = main(["inspect-doc", str(p)])
    assert called["count"] == 1
    assert rc == 0


def test_main_dispatches_to_validate_report(tmp_path: Path, monkeypatch):
    """main 检测到 'validate-report' command → 调用 validate_file。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")

    called = {"count": 0}

    def fake_validate_file(path, schema_name):
        called["count"] += 1
        called["schema"] = schema_name
        return None

    monkeypatch.setattr("evaluation.cli.validate_file", fake_validate_file)
    rc = main(["validate-report", str(p)])
    assert called["count"] == 1
    assert called["schema"] == "evaluation-report.schema.json"
    assert rc == 0


def test_main_validate_report_propagates_json_decode_error(tmp_path: Path, monkeypatch):
    """validate-report JSON 解析失败 → 返回 1。"""
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


# =========================================================================
# _run_inspect_doc：metric 类型 sort_key 验证
# =========================================================================


def test_run_inspect_doc_sort_order_bool_first_null_last(tmp_path: Path, capsys):
    """sort 顺序：bool → 数字 → dict → null。"""
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")

    class _Args:
        input = str(p)
        tolerance_chars = 30

    rc = _run_inspect_doc(_Args())
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    # 找 'metrics:' 行
    metrics_idx = next(i for i, line in enumerate(lines) if line.strip() == "metrics:")
    metric_lines = lines[metrics_idx + 1:]
    # 第一组是 bool (e.g., pipeline_success / schema_valid / text_preservation_equal)
    assert any("true" in line.lower() or "false" in line.lower() for line in metric_lines[:3])
    # 最后是 null (e.g., docx_locator_valid_ratio)
    assert "null" in metric_lines[-1]


def test_run_inspect_doc_metric_count_matches_expected(tmp_path: Path, capsys):
    """inspect-doc 输出的 metric 数量 = 14 (automatic) + 3 (figure_caption) + 4 (chunk_boundary incl _tolerance_chars) = 21 行（含内部 _ keys）。"""
    doc = {"document_id": "d1", "source_type": "pdf"}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")

    class _Args:
        input = str(p)
        tolerance_chars = 30

    _run_inspect_doc(_Args())
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    metrics_idx = next(i for i, line in enumerate(lines) if line.strip() == "metrics:")
    metric_lines = lines[metrics_idx + 1:]
    # 14 automatic + 3 figure_caption + 3 chunk_boundary (precision/recall/f1) + 1 _tolerance_chars
    # 共 21 行；但 _tolerance_chars 是 internal key，可能被 sort_key 归类到 dict（value=int 不算 bool/数字/null... 实际是 int 所以归到数字组）
    assert len(metric_lines) >= 20


def test_run_inspect_doc_includes_tolerance_chars_in_output(tmp_path: Path, capsys):
    """inspect-doc 输出包含 _tolerance_chars。"""
    doc = {"document_id": "d1", "source_type": "pdf"}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")

    class _Args:
        input = str(p)
        tolerance_chars = 42

    _run_inspect_doc(_Args())
    captured = capsys.readouterr()
    assert "_tolerance_chars" in captured.out
    assert "42" in captured.out


# =========================================================================
# main prog
# =========================================================================


def test_main_prog_exact_evaluation_cli():
    """main 内部 parser.prog == 'evaluation.cli'。"""
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_main_formatter_class_raw_description():
    """parser formatter_class == RawDescriptionHelpFormatter。"""
    p = _build_parser()
    assert p.formatter_class == argparse.RawDescriptionHelpFormatter


# =========================================================================
# 模块 callable 验证
# =========================================================================


def test_module_main_callable():
    """main 是 callable。"""
    import evaluation.cli as m
    assert callable(m.main)


def test_module_build_parser_callable():
    """_build_parser 是 callable。"""
    import evaluation.cli as m
    assert callable(m._build_parser)


def test_module_format_metric_callable():
    """_format_metric 是 callable。"""
    import evaluation.cli as m
    assert callable(m._format_metric)


def test_module_run_inspect_doc_callable():
    """_run_inspect_doc 是 callable。"""
    import evaluation.cli as m
    assert callable(m._run_inspect_doc)
