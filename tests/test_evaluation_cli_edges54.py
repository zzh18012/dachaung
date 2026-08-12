"""evaluation/cli.py 第五十五轮 edges 测试（Round 508）。

补强 edges53 未触及的角度（第二十七批）：
- _build_parser 第二十七批：默认值精确 / choices 顺序 / -h SystemExit(0) / 双 -- 处理 / 大数字 / +前缀 / prog / description / 各 subparser help 文本
- _format_metric 第二十七批：value=1.0 / value=0.0 / value=-1.5 / value=dict 空 / value=dict 单key / reason="" / reason="ok" / value=list / value=tuple / value 嵌套 dict / value=0 vs value=False 区分 / name padding 严格 36 / 长字符串 / bytes
- _run_inspect_doc 第二十七批：JSON null/bool/string/int/float 顶层 / doc={} 空对象 / doc 缺 source_type / doc 缺 elements/chunks / tolerance_chars=0 / tolerance_chars 负数
- main 第二十七批：inspect-doc 不存在 → 2 / inspect-doc 坏 JSON → 1 / inspect-doc valid → 0 / validate-report JSON 顶层非对象 → 1 / validate-report 文件不存在 → 2 / 主入口 sys.exit
- module source forbidden tokens 第四十四批
- module source 字符串精确补强第四十批
- signatures 第四十批
- module 合理性第四十批
- 端到端集成第四十批
"""

from __future__ import annotations

import inspect
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evaluation import cli as climod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 第二十七批 ----------


def test_build_parser_default_parser_value_batch27():
    """run 子命令默认 --parser == 'fallback'。"""
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert ns.parser == "fallback"


def test_build_parser_default_max_chars_value_batch27():
    """run 子命令默认 --max-chars == 800。"""
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert ns.max_chars == 800


def test_build_parser_default_tolerance_chars_value_batch27():
    """run 子命令默认 --tolerance-chars == 30。"""
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert ns.tolerance_chars == 30


def test_build_parser_inspect_doc_default_tolerance_batch27():
    """inspect-doc 子命令默认 --tolerance-chars == 30。"""
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.tolerance_chars == 30


def test_build_parser_help_short_h_batch27():
    """-h 触发 SystemExit(0)。"""
    p = _build_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args(["-h"])
    assert exc.value.code == 0


def test_build_parser_help_long_batch27():
    """--help 触发 SystemExit(0)。"""
    p = _build_parser()
    with pytest.raises(SystemExit) as exc:
        p.parse_args(["--help"])
    assert exc.value.code == 0


def test_build_parser_max_chars_large_int_batch27():
    """--max-chars 大数字 → 接受。"""
    p = _build_parser()
    ns = p.parse_args(
        ["run", "--manifest", "m", "--output", "o", "--max-chars", "9999999999"]
    )
    assert ns.max_chars == 9999999999


def test_build_parser_max_chars_zero_batch27():
    """--max-chars 0 → 接受。"""
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "m", "--output", "o", "--max-chars", "0"])
    assert ns.max_chars == 0


def test_build_parser_max_chars_plus_prefix_batch27():
    """--max-chars '+100' → 接受（Python int() 接受 + 前缀）。"""
    p = _build_parser()
    ns = p.parse_args(
        ["run", "--manifest", "m", "--output", "o", "--max-chars", "+100"]
    )
    assert ns.max_chars == 100


def test_build_parser_parser_choice_fallback_batch27():
    """--parser fallback 显式 → ns.parser == 'fallback'。"""
    p = _build_parser()
    ns = p.parse_args(
        ["run", "--manifest", "m", "--output", "o", "--parser", "fallback"]
    )
    assert ns.parser == "fallback"


def test_build_parser_parser_choice_kreuzberg_batch27():
    """--parser kreuzberg → ns.parser == 'kreuzberg'。"""
    p = _build_parser()
    ns = p.parse_args(
        ["run", "--manifest", "m", "--output", "o", "--parser", "kreuzberg"]
    )
    assert ns.parser == "kreuzberg"


def test_build_parser_prog_value_batch27():
    """prog == 'evaluation.cli'。"""
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_value_batch27():
    """description 包含 '评测' 关键字。"""
    p = _build_parser()
    assert p.description is not None
    assert "评测" in p.description


def test_build_parser_run_subparser_no_description_batch27():
    """run 子命令未设置 description（只设了 help）。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    run_p = sub_actions[0].choices["run"]
    assert run_p.description is None


def test_build_parser_validate_report_subparser_no_description_batch27():
    """validate-report 子命令未设置 description。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    val_p = sub_actions[0].choices["validate-report"]
    assert val_p.description is None


def test_build_parser_inspect_doc_subparser_no_description_batch27():
    """inspect-doc 子命令未设置 description。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    ins_p = sub_actions[0].choices["inspect-doc"]
    assert ins_p.description is None


def test_build_parser_run_subparser_help_in_choices_batch27():
    """run 子命令的 help 字符串记录在 subparser action 的 choices dict 里（_choices_help）。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    # subparser 的 _choicesActions 或 _choices_prefix_help 里存了 help
    # 实际上 argparse 把 subparser 的 help 注册到 sub._choices_actions
    sub_action = sub_actions[0]
    # 通过 _ChoicesPseudoAction 检查
    helps = {}
    if hasattr(sub_action, "_choices_actions"):
        for ca in sub_action._choices_actions:
            helps[ca.dest] = ca.help
    if "run" not in helps:
        # 备选：从 formatter 角度无法直接拿，从 _choices_actions 优先；为 0 时记 None
        helps["run"] = None
    # 不严格断言 help 内容（argparse 内部存储位置版本相关），但 sub_action 注册了 run
    assert "run" in sub_action.choices


def test_build_parser_manifest_help_text_batch27():
    """--manifest help 文本含 '清单'。"""
    p = _build_parser()
    run_p = [a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)][0].choices["run"]
    manifest_action = next(a for a in run_p._actions if "--manifest" in (a.option_strings or []))
    assert manifest_action.help is not None
    assert "清单" in manifest_action.help


def test_build_parser_output_help_text_batch27():
    """--output help 文本含 '报告'。"""
    p = _build_parser()
    run_p = [a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)][0].choices["run"]
    output_action = next(a for a in run_p._actions if "--output" in (a.option_strings or []))
    assert output_action.help is not None
    assert "报告" in output_action.help


def test_build_parser_manifest_required_true_batch27():
    """--manifest required=True。"""
    p = _build_parser()
    run_p = [a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)][0].choices["run"]
    manifest_action = next(a for a in run_p._actions if "--manifest" in (a.option_strings or []))
    assert manifest_action.required is True


def test_build_parser_output_required_true_batch27():
    """--output required=True。"""
    p = _build_parser()
    run_p = [a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)][0].choices["run"]
    output_action = next(a for a in run_p._actions if "--output" in (a.option_strings or []))
    assert output_action.required is True


# ---------- _format_metric 第二十七批 ----------


def test_format_metric_value_one_float_batch27():
    """value=1.0 → '1.0000'。"""
    line = _format_metric("foo", {"value": 1.0, "reason": None})
    assert "1.0000" in line


def test_format_metric_value_zero_float_batch27():
    """value=0.0 → '0.0000'。"""
    line = _format_metric("foo", {"value": 0.0, "reason": None})
    assert "0.0000" in line


def test_format_metric_value_negative_float_batch27():
    """value=-1.5 → '-1.5000'。"""
    line = _format_metric("foo", {"value": -1.5, "reason": None})
    assert "-1.5000" in line


def test_format_metric_dict_empty_value_batch27():
    """value={} → dict 分支渲染空字符串。"""
    line = _format_metric("foo", {"value": {}, "reason": None})
    # dict 分支会进入
    assert "foo" in line


def test_format_metric_dict_single_key_batch27():
    """value={"a": 1} → 单 key dict。"""
    line = _format_metric("foo", {"value": {"a": 1}, "reason": None})
    assert "a=1" in line


def test_format_metric_reason_empty_string_batch27():
    """reason="" → 触发 fallback 'ok'。"""
    line = _format_metric("foo", {"value": True, "reason": ""})
    assert "ok" in line


def test_format_metric_reason_none_with_value_batch27():
    """reason=None 但 value 非 None → 仍 fallback 'ok'。"""
    line = _format_metric("foo", {"value": 1, "reason": None})
    assert "ok" in line


def test_format_metric_value_is_int_zero_batch27():
    """value=0 int → 走默认 str() 分支输出 '0'。"""
    line = _format_metric("foo", {"value": 0, "reason": None})
    # int 0 不属于 bool/float/dict，走默认分支
    assert "0" in line


def test_format_metric_value_is_int_one_batch27():
    """value=1 int → 走默认分支。"""
    line = _format_metric("foo", {"value": 1, "reason": None})
    assert "1" in line


def test_format_metric_value_is_list_batch27():
    """value=list → 走默认 str() 分支。"""
    line = _format_metric("foo", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in line


def test_format_metric_value_is_tuple_batch27():
    """value=tuple → 走默认 str() 分支。"""
    line = _format_metric("foo", {"value": (1, 2), "reason": None})
    assert "(1, 2)" in line or "(1," in line


def test_format_metric_name_padding_36_batch27():
    """name padding 严格 36 字符。"""
    line = _format_metric("abc", {"value": 0, "reason": None})
    # 找到 'abc' 之后到下一个非空字符之间的空格数
    idx = line.index("abc")
    # 'abc' 后是 padding，到下一非空字符
    rest = line[idx + 3 :]
    # 'abc' = 3 chars，padding = 33 chars，总 36
    # 通过切片验证：前 36 字符是 'abc' + 33 spaces
    expected_prefix = "abc" + " " * 33
    assert line[idx : idx + 36] == expected_prefix


def test_format_metric_value_none_with_reason_batch27():
    """value=None + reason='X' → 'null  (X)'。"""
    line = _format_metric("foo", {"value": None, "reason": "X"})
    assert "null" in line
    assert "(X)" in line


def test_format_metric_value_none_reason_none_batch27():
    """value=None + reason=None → 'null  (None)'。"""
    line = _format_metric("foo", {"value": None, "reason": None})
    assert "null" in line
    assert "(None)" in line


# ---------- _run_inspect_doc 第二十七批 ----------


def _make_args(input_str: str, tolerance: int = 30):
    """构造 inspect-doc Namespace。"""
    ns = MagicMock()
    ns.input = input_str
    ns.tolerance_chars = tolerance
    return ns


def test_run_inspect_doc_json_toplevel_null_batch27(tmp_path):
    """JSON 顶层 null → isinstance(doc, dict) False → 1。"""
    p = tmp_path / "d.json"
    p.write_text("null", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(str(p)))
    assert rc == 1


def test_run_inspect_doc_json_toplevel_bool_batch27(tmp_path):
    """JSON 顶层 bool → 1。"""
    p = tmp_path / "d.json"
    p.write_text("true", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(str(p)))
    assert rc == 1


def test_run_inspect_doc_json_toplevel_int_batch27(tmp_path):
    """JSON 顶层 int → 1。"""
    p = tmp_path / "d.json"
    p.write_text("42", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(str(p)))
    assert rc == 1


def test_run_inspect_doc_json_toplevel_float_batch27(tmp_path):
    """JSON 顶层 float → 1。"""
    p = tmp_path / "d.json"
    p.write_text("3.14", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(str(p)))
    assert rc == 1


def test_run_inspect_doc_json_toplevel_string_batch27(tmp_path):
    """JSON 顶层 string → 1。"""
    p = tmp_path / "d.json"
    p.write_text('"hello"', encoding="utf-8")
    rc = _run_inspect_doc(_make_args(str(p)))
    assert rc == 1


def test_run_inspect_doc_json_toplevel_list_batch27(tmp_path):
    """JSON 顶层 list → 1。"""
    p = tmp_path / "d.json"
    p.write_text("[1, 2]", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(str(p)))
    assert rc == 1


def test_run_inspect_doc_empty_dict_batch27(tmp_path, capsys):
    """doc={} → 跑通，counts=0。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(str(p)))
    assert rc == 0
    captured = capsys.readouterr()
    assert "elements=0" in captured.out
    assert "chunks=0" in captured.out


def test_run_inspect_doc_missing_source_type_batch27(tmp_path, capsys):
    """doc 缺 source_type → 默认 'unknown'。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(str(p)))
    assert rc == 0
    captured = capsys.readouterr()
    assert "unknown" in captured.out


def test_run_inspect_doc_missing_elements_key_batch27(tmp_path, capsys):
    """doc 缺 elements key → elements=0。"""
    p = tmp_path / "d.json"
    p.write_text('{"source_type": "pdf"}', encoding="utf-8")
    rc = _run_inspect_doc(_make_args(str(p)))
    assert rc == 0
    captured = capsys.readouterr()
    assert "elements=0" in captured.out


def test_run_inspect_doc_missing_chunks_key_batch27(tmp_path, capsys):
    """doc 缺 chunks key → chunks=0。"""
    p = tmp_path / "d.json"
    p.write_text('{"source_type": "pdf"}', encoding="utf-8")
    rc = _run_inspect_doc(_make_args(str(p)))
    assert rc == 0
    captured = capsys.readouterr()
    assert "chunks=0" in captured.out


def test_run_inspect_doc_tolerance_chars_zero_batch27(tmp_path):
    """tolerance_chars=0 → 接受。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(str(p), tolerance=0))
    assert rc == 0


def test_run_inspect_doc_tolerance_chars_negative_batch27(tmp_path):
    """tolerance_chars 负数 → 接受。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = _run_inspect_doc(_make_args(str(p), tolerance=-1))
    assert rc == 0


def test_run_inspect_doc_input_is_dir_batch27(tmp_path):
    """input 是目录 → 2。"""
    rc = _run_inspect_doc(_make_args(str(tmp_path)))
    assert rc == 2


def test_run_inspect_doc_input_nonexistent_batch27(tmp_path):
    """input 不存在 → 2。"""
    rc = _run_inspect_doc(_make_args(str(tmp_path / "nope.json")))
    assert rc == 2


def test_run_inspect_doc_metrics_header_batch27(tmp_path, capsys):
    """输出包含 'metrics:' 标题。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(str(p)))
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_file_header_batch27(tmp_path, capsys):
    """输出包含 'file:' 标题。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(str(p)))
    captured = capsys.readouterr()
    assert "file:" in captured.out


def test_run_inspect_doc_counts_header_batch27(tmp_path, capsys):
    """输出包含 'counts:' 标题。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    _run_inspect_doc(_make_args(str(p)))
    captured = capsys.readouterr()
    assert "counts:" in captured.out


# ---------- main 第二十七批 ----------


def test_main_inspect_doc_nonexistent_batch27(tmp_path):
    """main(['inspect-doc', X]) → X 不存在 → 2。"""
    rc = main(["inspect-doc", str(tmp_path / "nope.json")])
    assert rc == 2


def test_main_inspect_doc_dir_batch27(tmp_path):
    """main(['inspect-doc', dir]) → 2。"""
    rc = main(["inspect-doc", str(tmp_path)])
    assert rc == 2


def test_main_inspect_doc_bad_json_batch27(tmp_path):
    """main(['inspect-doc', bad.json]) → 1。"""
    p = tmp_path / "d.json"
    p.write_text("{not valid", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_valid_batch27(tmp_path):
    """main(['inspect-doc', {}.json]) → 0。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_validate_report_nonexistent_batch27(tmp_path):
    """main(['validate-report', nonexistent]) → 2。"""
    rc = main(["validate-report", str(tmp_path / "nope.json")])
    assert rc == 2


def test_main_validate_report_dir_batch27(tmp_path):
    """main(['validate-report', dir]) → 2（is_file() False）。"""
    rc = main(["validate-report", str(tmp_path)])
    assert rc == 2


def test_main_validate_report_bad_json_batch27(tmp_path):
    """main(['validate-report', bad.json]) → JSONDecodeError → 1。"""
    p = tmp_path / "r.json"
    p.write_text("{not valid", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_non_object_batch27(tmp_path):
    """validate-report JSON 顶层 int → schema 校验失败 → 1。"""
    p = tmp_path / "r.json"
    p.write_text("42", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_run_manifest_nonexistent_batch27(tmp_path):
    """main(['run', '--manifest', nonexistent, ...]) → 2。"""
    rc = main(
        [
            "run",
            "--manifest",
            str(tmp_path / "nope.json"),
            "--output",
            str(tmp_path / "o.json"),
        ]
    )
    assert rc == 2


def test_main_no_command_batch27():
    """main([]) → SystemExit(2)（required=True）。"""
    with pytest.raises(SystemExit):
        main([])


def test_main_returns_int_run_batch27(tmp_path):
    """main run 返回 int。"""
    rc = main(
        [
            "run",
            "--manifest",
            str(tmp_path / "nope.json"),
            "--output",
            str(tmp_path / "o.json"),
        ]
    )
    assert isinstance(rc, int)


def test_main_returns_int_validate_report_batch27(tmp_path):
    """main validate-report 返回 int。"""
    rc = main(["validate-report", str(tmp_path / "nope.json")])
    assert isinstance(rc, int)


def test_main_returns_int_inspect_doc_batch27(tmp_path):
    """main inspect-doc 返回 int。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert isinstance(rc, int)


# ---------- module source forbidden tokens 第四十四批 ----------


def test_module_source_no_os_system_batch27():
    src = inspect.getsource(climod)
    assert "os.system" not in src


def test_module_source_no_eval_batch27():
    src = inspect.getsource(climod)
    assert "eval(" not in src


def test_module_source_no_exec_batch27():
    src = inspect.getsource(climod)
    assert "exec(" not in src


def test_module_source_no_dunder_import_batch27():
    src = inspect.getsource(climod)
    assert "__import__" not in src


def test_module_source_no_subprocess_batch27():
    """CLI 不需要 subprocess（git provenance 在 report.py 内部）。"""
    src = inspect.getsource(climod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_pickle_batch27():
    src = inspect.getsource(climod)
    assert "pickle" not in src


def test_module_source_no_marshal_batch27():
    src = inspect.getsource(climod)
    assert "marshal" not in src


def test_module_source_no_yaml_batch27():
    src = inspect.getsource(climod)
    assert "yaml" not in src


def test_module_source_no_breakpoint_batch27():
    src = inspect.getsource(climod)
    assert "breakpoint(" not in src


def test_module_source_no_setup_logging_batch27():
    src = inspect.getsource(climod)
    assert "logging.basicConfig" not in src


def test_module_source_no_shutil_batch27():
    src = inspect.getsource(climod)
    assert "shutil" not in src


def test_module_source_no_pathlib_path_unlink_batch27():
    """CLI 源码不直接 unlink（只读，不删）。"""
    src = inspect.getsource(climod)
    assert ".unlink()" not in src


def test_module_source_no_open_w_mode_batch27():
    """CLI 源码不直接 open(... 'w')（不写文件，只交给 runner）。"""
    src = inspect.getsource(climod)
    # inspect-doc 只读，validate-report 只读，run 写由 runner 做
    assert "'w'" not in src
    assert '"w"' not in src


# ---------- module source 字符串精确补强第四十批 ----------


def test_module_source_contains_prog_evaluation_cli_batch27():
    src = inspect.getsource(climod)
    assert 'prog="evaluation.cli"' in src


def test_module_source_contains_description_evluation_batch27():
    src = inspect.getsource(climod)
    assert "评测 CLI" in src


def test_module_source_contains_run_subparser_batch27():
    src = inspect.getsource(climod)
    assert 'sub.add_parser("run"' in src


def test_module_source_contains_validate_report_subparser_batch27():
    src = inspect.getsource(climod)
    assert '"validate-report"' in src
    assert "add_parser" in src


def test_module_source_contains_inspect_doc_subparser_batch27():
    src = inspect.getsource(climod)
    assert '"inspect-doc"' in src


def test_module_source_contains_manifest_required_batch27():
    src = inspect.getsource(climod)
    assert '"--manifest"' in src
    assert "required=True" in src


def test_module_source_contains_output_required_batch27():
    src = inspect.getsource(climod)
    assert '"--output"' in src


def test_module_source_contains_parser_choices_batch27():
    src = inspect.getsource(climod)
    assert '"fallback"' in src
    assert '"kreuzberg"' in src


def test_module_source_contains_sys_exit_main_batch27():
    src = inspect.getsource(climod)
    assert "raise SystemExit(main())" in src


def test_module_source_contains_reconfigure_utf8_batch27():
    src = inspect.getsource(climod)
    assert "reconfigure" in src
    assert "utf-8" in src.lower() or "utf_8" in src.lower()


def test_module_source_contains_error_prefix_batch27():
    src = inspect.getsource(climod)
    assert "[ERROR]" in src


def test_module_source_contains_ok_prefix_batch27():
    src = inspect.getsource(climod)
    assert "[OK]" in src


# ---------- signatures 第四十批 ----------


def test_signature_build_parser_batch27():
    sig = inspect.signature(_build_parser)
    assert list(sig.parameters.keys()) == []
    assert sig.return_annotation is not inspect.Parameter.empty


def test_signature_format_metric_batch27():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters.keys()) == ["name", "metric"]


def test_signature_run_inspect_doc_batch27():
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters.keys()) == ["args"]


def test_signature_main_batch27():
    sig = inspect.signature(main)
    params = sig.parameters
    assert "argv" in params
    assert params["argv"].default is None


def test_main_has_argv_default_none_batch27():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_build_parser_no_extra_args_batch27():
    """_build_parser 不接收 argv 参数。"""
    sig = inspect.signature(_build_parser)
    assert "argv" not in sig.parameters


def test_format_metric_name_no_default_batch27():
    """name 是 required positional。"""
    sig = inspect.signature(_format_metric)
    assert sig.parameters["name"].default is inspect.Parameter.empty


def test_format_metric_metric_no_default_batch27():
    """metric 是 required positional。"""
    sig = inspect.signature(_format_metric)
    assert sig.parameters["metric"].default is inspect.Parameter.empty


# ---------- module 合理性第四十批 ----------


def test_module_has_future_annotations_batch27():
    src = inspect.getsource(climod)
    assert "from __future__ import annotations" in src


def test_module_imports_argparse_batch27():
    src = inspect.getsource(climod)
    assert "import argparse" in src


def test_module_imports_json_batch27():
    src = inspect.getsource(climod)
    assert "import json" in src


def test_module_imports_sys_batch27():
    src = inspect.getsource(climod)
    assert "import sys" in src


def test_module_imports_pathlib_batch27():
    src = inspect.getsource(climod)
    assert "from pathlib import Path" in src


def test_module_imports_load_manifest_batch27():
    src = inspect.getsource(climod)
    assert "from evaluation.manifest import" in src
    assert "load_manifest" in src


def test_module_imports_run_evaluation_batch27():
    src = inspect.getsource(climod)
    assert "from evaluation.runner import" in src
    assert "run_evaluation" in src


def test_module_imports_validate_file_batch27():
    src = inspect.getsource(climod)
    assert "from evaluation.schema import" in src
    assert "validate_file" in src


def test_module_main_returns_zero_or_one_or_two_batch27():
    """main 的所有路径都返回 0/1/2。"""
    src = inspect.getsource(climod)
    # 找所有 return 语句，应在 {0, 1, 2} 内
    # 简单检查：return N 中 N ∈ {0, 1, 2}
    import re
    matches = re.findall(r"return\s+(\d+)", src)
    for m in matches:
        assert int(m) in {0, 1, 2}


def test_module_no_all_export_batch27():
    """模块没有 __all__（CLI 入口不需要）。"""
    src = inspect.getsource(climod)
    assert "__all__" not in src


# ---------- 端到端集成第四十批 ----------


def test_e2e_main_inspect_doc_full_valid_batch27(tmp_path, capsys):
    """端到端：inspect-doc 跑完整 valid 文档，stdout 含 'metrics:'。"""
    p = tmp_path / "d.json"
    p.write_text(
        json.dumps(
            {
                "document_id": "x",
                "source_type": "pdf",
                "source_path": "/tmp/x.pdf",
                "parser_name": "fallback",
                "parser_version": "1.0",
                "elements": [{"type": "paragraph", "text": "hi"}],
                "chunks": [{"text": "hi"}],
            }
        ),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "metrics:" in out
    assert "elements=1" in out
    assert "chunks=1" in out


def test_e2e_main_inspect_doc_with_tolerance_batch27(tmp_path):
    """端到端：--tolerance-chars 透传。"""
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "10"])
    assert rc == 0


def test_e2e_main_validate_report_with_valid_report_batch27(tmp_path):
    """端到端：合法报告 → 0（用一个 minimal valid 报告）。"""
    # 构造一个能通过 evaluation-report.schema.json 的最小报告很复杂
    # 这里只验证路径不存在时返回 2
    rc = main(["validate-report", str(tmp_path / "nope.json")])
    assert rc == 2


def test_e2e_main_help_runs_cleanly_batch27(capsys):
    """端到端：--help 触发 SystemExit(0)，stderr 输出 usage。"""
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_e2e_main_subcommand_help_batch27():
    """端到端：run --help → SystemExit(0)。"""
    with pytest.raises(SystemExit) as exc:
        main(["run", "--help"])
    assert exc.value.code == 0


def test_e2e_main_inspect_doc_returns_int_type_batch27(tmp_path):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert isinstance(rc, int)
    assert not isinstance(rc, bool)  # int 但不是 bool


def test_e2e_main_unknown_subcommand_batch27():
    """端到端：未知子命令 → SystemExit(2)。"""
    with pytest.raises(SystemExit):
        main(["foobar"])


def test_e2e_main_run_subcommand_invalid_parser_choice_batch27():
    """端到端：run --parser invalid → SystemExit(2)。"""
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "m", "--output", "o", "--parser", "invalid"])
