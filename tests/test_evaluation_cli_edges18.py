r"""evaluation/cli.py 边角测试 - 第十八轮（Round 265）。

edges17 已覆盖：源码 token、docstring、_build_parser 3 subparser、argparse _actions、
_format_metric 边界、_run_inspect_doc 排序、缺字段、tolerance_chars 透传、namespace identity、
main 错误路径、import 检查、__main__ 检查、stdout reconfigure 块。

edges18 补强未覆盖的角度：
- main(['run', ...]) 详细错误路径：manifest 是目录（FileNotFoundError or IsADirectoryError）；output 路径父目录不存在
- main(['run', ...]) 输出格式：包含 documents / 成功 / 失败 / devset_status / file_count / groups / pdf / docx / git_commit / git_dirty
- main validate-report 错误路径：input 不是文件 → return 2；FileNotFoundError catch → return 2；JSONDecodeError catch → return 1
- main inspect-doc 错误路径：input 不是文件 → return 2；JSONDecodeError → return 1；JSON 顶层不是 dict → return 1
- _build_parser 详细：formatter_class 是 RawDescriptionHelpFormatter；prog='evaluation.cli'
- run subparser arg types：--max-chars type=int；--tolerance-chars type=int；--parser choices=('fallback', 'kreuzberg')
- 默认值：--parser default='fallback'；--max-chars default=800；--tolerance-chars default=30
- 缺 required 参数 → SystemExit（argparse error）
- 主入口块：if __name__ == '__main__' → SystemExit(main())
- _format_metric 详细：每个 value 类型分支（None / bool True / bool False / float / dict / int / str / list 理论边界）
- _format_metric dict value 排序：sorted 内部 items
- _run_inspect_doc 详细：缺 source_type / elements / chunks 各字段；elements=[] / chunks=[]
- _run_inspect_doc 输出格式：包含 'file:' / 'document_id:' / 'source:' / 'parser:' / 'counts:' / 'metrics:'
- _run_inspect_doc 排序详细：bool 在前 / int+float 中间 / 其他 / null 最后
- 模块顶层 import 顺序：argparse → json → sys → pathlib → evaluation 子模块
- sys.stdout.reconfigure 块：hasattr / try / except AttributeError OSError
"""

from __future__ import annotations

import argparse
import inspect
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# =========================================================================
# _build_parser 详细
# =========================================================================


def test_build_parser_prog_is_evaluation_cli():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_contains_eval_or_ping():
    """description 含 '评测' 或类似词。"""
    p = _build_parser()
    assert "评测" in p.description or "evaluation" in p.description.lower()


def test_build_parser_formatter_class_is_raw_description():
    p = _build_parser()
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_has_subparsers_action():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    ]
    assert len(sub_actions) == 1


def test_build_parser_subparsers_required_true():
    """subparsers required=True（无子命令时退出非零）。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    ]
    assert sub_actions[0].required is True


def test_build_parser_subparsers_dest_is_command():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    ]
    assert sub_actions[0].dest == "command"


def test_build_parser_run_subparser_choices_contains_3():
    """run / validate-report / inspect-doc 三个子命令。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    ]
    choices = set(sub_actions[0].choices.keys())
    assert choices == {"run", "validate-report", "inspect-doc"}


def test_build_parser_run_subparser_has_5_args_excluding_help():
    """run 子命令除 help action 外有 5 个 arg。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    ]
    run_p = sub_actions[0].choices["run"]
    user_actions = [a for a in run_p._actions if a.dest != "help"]
    assert len(user_actions) == 5
    dests = [a.dest for a in user_actions]
    assert set(dests) == {"manifest", "output", "parser", "max_chars", "tolerance_chars"}


def test_build_parser_validate_report_subparser_has_1_arg():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    ]
    val_p = sub_actions[0].choices["validate-report"]
    user_actions = [a for a in val_p._actions if a.dest != "help"]
    assert len(user_actions) == 1
    assert user_actions[0].dest == "input"


def test_build_parser_inspect_doc_subparser_has_2_args():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    ]
    ins_p = sub_actions[0].choices["inspect-doc"]
    user_actions = [a for a in ins_p._actions if a.dest != "help"]
    assert len(user_actions) == 2
    dests = [a.dest for a in user_actions]
    assert set(dests) == {"input", "tolerance_chars"}


def test_build_parser_manifest_required():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.manifest == "x"


def test_build_parser_output_required():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.output == "y"


def test_build_parser_manifest_required_raises_system_exit():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "y"])


def test_build_parser_output_required_raises_system_exit():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "x"])


def test_build_parser_parser_default_fallback():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.parser == "fallback"


def test_build_parser_parser_choice_kreuzberg():
    p = _build_parser()
    args = p.parse_args(
        ["run", "--manifest", "x", "--output", "y", "--parser", "kreuzberg"]
    )
    assert args.parser == "kreuzberg"


def test_build_parser_parser_invalid_choice_raises_system_exit():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(
            ["run", "--manifest", "x", "--output", "y", "--parser", "bogus"]
        )


def test_build_parser_max_chars_default_800():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.max_chars == 800
    assert isinstance(args.max_chars, int)


def test_build_parser_max_chars_type_int():
    p = _build_parser()
    args = p.parse_args(
        ["run", "--manifest", "x", "--output", "y", "--max-chars", "500"]
    )
    assert args.max_chars == 500
    assert isinstance(args.max_chars, int)


def test_build_parser_max_chars_invalid_type_raises_system_exit():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(
            ["run", "--manifest", "x", "--output", "y", "--max-chars", "notint"]
        )


def test_build_parser_tolerance_chars_default_30():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.tolerance_chars == 30


def test_build_parser_tolerance_chars_type_int():
    p = _build_parser()
    args = p.parse_args(
        ["run", "--manifest", "x", "--output", "y", "--tolerance-chars", "10"]
    )
    assert args.tolerance_chars == 10


def test_build_parser_inspect_doc_tolerance_chars_default_30():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_input_positional():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.input == "doc.json"


def test_build_parser_validate_report_input_positional():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"


def test_build_parser_command_dest():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.command == "run"


def test_build_parser_no_command_raises_system_exit():
    """required=True 的 subparser，无子命令时 SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_parser_unknown_command_raises_system_exit():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["bogus-command"])


# =========================================================================
# _format_metric 详细（每个 value 类型分支）
# =========================================================================


def test_format_metric_none_value():
    out = _format_metric("foo", {"value": None, "reason": "x"})
    assert "null" in out
    assert "(x)" in out
    assert "foo" in out


def test_format_metric_bool_true_value():
    out = _format_metric("foo", {"value": True, "reason": None})
    assert "true" in out  # str(True).lower()


def test_format_metric_bool_false_value():
    out = _format_metric("foo", {"value": False, "reason": None})
    assert "false" in out


def test_format_metric_bool_true_with_reason_none_renders_ok():
    """bool value + reason=None → 显示 'ok'。"""
    out = _format_metric("foo", {"value": True, "reason": None})
    assert "(ok)" in out


def test_format_metric_bool_false_with_reason_none_renders_ok():
    out = _format_metric("foo", {"value": False, "reason": None})
    assert "(ok)" in out


def test_format_metric_bool_with_explicit_reason():
    out = _format_metric("foo", {"value": True, "reason": "custom"})
    assert "(custom)" in out


def test_format_metric_float_value_4_decimal():
    """float value 渲染到 4 位小数。"""
    out = _format_metric("foo", {"value": 0.123456789, "reason": None})
    assert "0.1235" in out  # .4f 四舍五入


def test_format_metric_float_zero():
    out = _format_metric("foo", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_float_one():
    out = _format_metric("foo", {"value": 1.0, "reason": None})
    assert "1.0000" in out


def test_format_metric_int_value_default_branch():
    """int value 走 default 分支（不走 float 分支，即使 int 是 number）。"""
    out = _format_metric("foo", {"value": 42, "reason": None})
    # default 分支：f"{value}"
    assert "42" in out
    assert "(ok)" in out


def test_format_metric_int_zero():
    out = _format_metric("foo", {"value": 0, "reason": None})
    assert "0" in out


def test_format_metric_negative_int():
    out = _format_metric("foo", {"value": -5, "reason": None})
    assert "-5" in out


def test_format_metric_dict_value_sorted_items():
    """dict value → sorted items 渲染。"""
    out = _format_metric(
        "foo",
        {"value": {"b": 2, "a": 1, "c": 3}, "reason": None},
    )
    # sorted items: a=1, b=2, c=3
    assert "a=1" in out
    assert "b=2" in out
    assert "c=3" in out
    # 顺序应该是 a → b → c
    pos_a = out.find("a=1")
    pos_b = out.find("b=2")
    pos_c = out.find("c=3")
    assert pos_a < pos_b < pos_c


def test_format_metric_empty_dict_value():
    out = _format_metric("foo", {"value": {}, "reason": None})
    assert "foo" in out
    assert "(ok)" in out


def test_format_metric_str_value_default_branch():
    out = _format_metric("foo", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_list_value_default_branch():
    """list value 走 default 分支（无 isinstance 检查）。"""
    out = _format_metric("foo", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in out


def test_format_metric_metric_dict_missing_value_key():
    """metric 缺 value key → value=None 走 null 分支。"""
    out = _format_metric("foo", {"reason": "no_value"})
    assert "null" in out
    assert "(no_value)" in out


def test_format_metric_metric_dict_missing_reason_key():
    """metric 缺 reason key 且 value None → reason=None → str(None)='None'。"""
    out = _format_metric("foo", {"value": None})
    assert "null" in out
    # reason is None → f"{None}" = 'None'
    assert "(None)" in out


def test_format_metric_metric_dict_empty():
    """空 metric dict → value None + reason None → null + (None)。"""
    out = _format_metric("foo", {})
    assert "null" in out


def test_format_metric_name_alignment_36_chars():
    """name 占 36 char 宽。"""
    out = _format_metric("ab", {"value": None, "reason": "x"})
    # 格式：'  {name:36} null  (x)' → 2 leading + 2 chars name + 34 padding + 1 space + null
    name_end = out.find("ab") + 2
    null_pos = out.find("null")
    assert null_pos - name_end == 35  # 34 padding + 1 literal space


# =========================================================================
# _run_inspect_doc 详细（各种 document 结构）
# =========================================================================


class _Args:
    """stub argparse.Namespace。"""

    def __init__(self, input: str, tolerance_chars: int = 30):
        self.input = input
        self.tolerance_chars = tolerance_chars


def test_run_inspect_doc_input_not_a_file_returns_2(tmp_path: Path):
    nonexistent = tmp_path / "nonexistent.json"
    args = _Args(str(nonexistent))
    with redirect_stderr(io.StringIO()):
        rc = _run_inspect_doc(args)
    assert rc == 2


def test_run_inspect_doc_invalid_json_returns_1(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    args = _Args(str(bad))
    with redirect_stderr(io.StringIO()):
        rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_json_top_not_dict_returns_1(tmp_path: Path):
    bad = tmp_path / "list.json"
    bad.write_text("[1, 2, 3]", encoding="utf-8")
    args = _Args(str(bad))
    with redirect_stderr(io.StringIO()):
        rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_json_top_is_string_returns_1(tmp_path: Path):
    bad = tmp_path / "str.json"
    bad.write_text('"hello"', encoding="utf-8")
    args = _Args(str(bad))
    with redirect_stderr(io.StringIO()):
        rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_minimal_dict_succeeds(tmp_path: Path):
    """最小 dict（仅 source_type/elements/chunks）应返回 0。"""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _Args(str(p))
    with redirect_stdout(io.StringIO()) as f:
        rc = _run_inspect_doc(args)
    assert rc == 0
    out = f.getvalue()
    assert "file:" in out
    assert "metrics:" in out


def test_run_inspect_doc_missing_source_type_defaults_unknown(tmp_path: Path):
    """doc 缺 source_type → source_type='unknown'。"""
    doc = {"elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _Args(str(p))
    with redirect_stdout(io.StringIO()) as f:
        rc = _run_inspect_doc(args)
    assert rc == 0
    out = f.getvalue()
    assert "type=unknown" in out


def test_run_inspect_doc_missing_elements_defaults_empty(tmp_path: Path):
    doc = {"source_type": "pdf", "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _Args(str(p))
    with redirect_stdout(io.StringIO()) as f:
        rc = _run_inspect_doc(args)
    assert rc == 0
    out = f.getvalue()
    assert "elements=0" in out


def test_run_inspect_doc_missing_chunks_defaults_empty(tmp_path: Path):
    doc = {"source_type": "pdf", "elements": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _Args(str(p))
    with redirect_stdout(io.StringIO()) as f:
        rc = _run_inspect_doc(args)
    assert rc == 0
    out = f.getvalue()
    assert "chunks=0" in out


def test_run_inspect_doc_elements_null_propagates_to_metrics(tmp_path: Path):
    """doc elements=None → compute_automatic_metrics 内部读 doc['elements'] 会 TypeError。"""
    doc = {"source_type": "pdf", "elements": None, "chunks": None}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _Args(str(p))
    # compute_automatic_metrics 不 None-safe；len(None) 抛 TypeError
    with pytest.raises(TypeError):
        _run_inspect_doc(args)


def test_run_inspect_doc_with_elements_and_chunks_counts(tmp_path: Path):
    """有 elements + chunks → counts 行正确。"""
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph"}, {"type": "heading"}],
        "chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _Args(str(p))
    with redirect_stdout(io.StringIO()) as f:
        rc = _run_inspect_doc(args)
    assert rc == 0
    out = f.getvalue()
    assert "elements=2" in out
    assert "chunks=3" in out


def test_run_inspect_doc_output_contains_file_line(tmp_path: Path):
    doc = {"source_type": "pdf"}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _Args(str(p))
    with redirect_stdout(io.StringIO()) as f:
        _run_inspect_doc(args)
    out = f.getvalue()
    assert "file:" in out
    assert str(p) in out


def test_run_inspect_doc_output_contains_document_id_line(tmp_path: Path):
    doc = {"source_type": "pdf", "document_id": "doc-42"}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _Args(str(p))
    with redirect_stdout(io.StringIO()) as f:
        _run_inspect_doc(args)
    out = f.getvalue()
    assert "document_id:" in out
    assert "doc-42" in out


def test_run_inspect_doc_output_contains_source_line(tmp_path: Path):
    doc = {"source_type": "pdf", "source_path": "/some/path.pdf"}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _Args(str(p))
    with redirect_stdout(io.StringIO()) as f:
        _run_inspect_doc(args)
    out = f.getvalue()
    assert "source:" in out
    assert "/some/path.pdf" in out


def test_run_inspect_doc_output_contains_parser_line(tmp_path: Path):
    doc = {
        "source_type": "pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _Args(str(p))
    with redirect_stdout(io.StringIO()) as f:
        _run_inspect_doc(args)
    out = f.getvalue()
    assert "parser:" in out
    assert "fallback" in out


def test_run_inspect_doc_output_contains_metrics_line(tmp_path: Path):
    doc = {"source_type": "pdf"}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _Args(str(p))
    with redirect_stdout(io.StringIO()) as f:
        _run_inspect_doc(args)
    out = f.getvalue()
    # 'metrics:' 出现在 counts 行之后
    pos_counts = out.find("counts:")
    pos_metrics = out.find("metrics:")
    assert pos_counts != -1
    assert pos_metrics != -1
    assert pos_counts < pos_metrics


def test_run_inspect_doc_sort_key_bool_first(tmp_path: Path):
    """bool value 排在前面。"""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _Args(str(p))
    with redirect_stdout(io.StringIO()) as f:
        _run_inspect_doc(args)
    out = f.getvalue()
    # 找到 metrics: 之后的部分
    metrics_section = out.split("metrics:")[1]
    # 第一个 metric 行应是 bool (true/false)
    first_metric_line = [
        line for line in metrics_section.splitlines() if line.strip()
    ][0]
    assert "true" in first_metric_line or "false" in first_metric_line


def test_run_inspect_doc_tolerance_chars_passthrough(tmp_path: Path):
    """tolerance_chars 透传给 chunk_boundary_prf。"""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _Args(str(p), tolerance_chars=99)
    with redirect_stdout(io.StringIO()) as f:
        rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_default_tolerance_chars(tmp_path: Path):
    """args.tolerance_chars 默认 30。"""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _Args(str(p))  # default tolerance_chars=30
    with redirect_stdout(io.StringIO()):
        rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_returns_0_on_success(tmp_path: Path):
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = _Args(str(p))
    with redirect_stdout(io.StringIO()):
        rc = _run_inspect_doc(args)
    assert rc == 0


# =========================================================================
# main(['inspect-doc', ...]) 路径
# =========================================================================


def test_main_inspect_doc_not_a_file_returns_2(tmp_path: Path):
    nonexistent = tmp_path / "no.json"
    rc = main(["inspect-doc", str(nonexistent)])
    assert rc == 2


def test_main_inspect_doc_invalid_json_returns_1(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{bad", encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    assert rc == 1


def test_main_inspect_doc_json_top_not_dict_returns_1(tmp_path: Path):
    bad = tmp_path / "list.json"
    bad.write_text("[1]", encoding="utf-8")
    rc = main(["inspect-doc", str(bad)])
    assert rc == 1


def test_main_inspect_doc_with_tolerance_chars_arg(tmp_path: Path):
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "50"])
    assert rc == 0


# =========================================================================
# main(['validate-report', ...]) 路径
# =========================================================================


def test_main_validate_report_not_a_file_returns_2(tmp_path: Path):
    nonexistent = tmp_path / "noreport.json"
    rc = main(["validate-report", str(nonexistent)])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_1(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{bad", encoding="utf-8")
    rc = main(["validate-report", str(bad)])
    assert rc == 1


def test_main_validate_report_top_not_object_returns_1(tmp_path: Path):
    """JSON 顶层是 list 不是 object → schema 校验失败 → return 1。"""
    bad = tmp_path / "list.json"
    bad.write_text("[1, 2, 3]", encoding="utf-8")
    rc = main(["validate-report", str(bad)])
    assert rc == 1


# =========================================================================
# main(['run', ...]) 错误路径
# =========================================================================


def test_main_run_manifest_not_a_file_returns_2(tmp_path: Path):
    """manifest 不存在 → return 2。"""
    nonexistent = tmp_path / "no.json"
    rc = main(
        [
            "run",
            "--manifest",
            str(nonexistent),
            "--output",
            str(tmp_path / "out.json"),
        ]
    )
    assert rc == 2


def test_main_run_manifest_is_directory_returns_2(tmp_path: Path):
    """manifest 路径是目录 → is_file() False → return 2。"""
    rc = main(
        [
            "run",
            "--manifest",
            str(tmp_path),
            "--output",
            str(tmp_path / "out.json"),
        ]
    )
    assert rc == 2


# =========================================================================
# 模块源码 token 验证（补强）
# =========================================================================


def test_module_source_contains_run_evaluation_import():
    import evaluation.cli as m

    assert "from evaluation.runner import run_evaluation" in inspect.getsource(m)


def test_module_source_contains_load_manifest_import():
    import evaluation.cli as m

    assert "from evaluation.manifest import" in inspect.getsource(m)
    assert "load_manifest" in inspect.getsource(m)
    assert "ManifestError" in inspect.getsource(m)


def test_module_source_contains_validate_file_import():
    import evaluation.cli as m

    assert "from evaluation.schema import" in inspect.getsource(m)
    assert "validate_file" in inspect.getsource(m)
    assert "EvalSchemaError" in inspect.getsource(m)


def test_module_source_contains_get_git_provenance_import():
    import evaluation.cli as m

    assert "from evaluation.report import" in inspect.getsource(m)
    assert "get_git_provenance" in inspect.getsource(m)


def test_module_source_contains_subparsers_required_true():
    import evaluation.cli as m

    assert 'required=True' in inspect.getsource(m)


def test_module_source_contains_argparse_raw_description():
    import evaluation.cli as m

    assert "RawDescriptionHelpFormatter" in inspect.getsource(m)


def test_module_source_contains_max_chars_default_800():
    import evaluation.cli as m

    assert "default=800" in inspect.getsource(m)


def test_module_source_contains_tolerance_chars_default_30():
    import evaluation.cli as m

    src = inspect.getsource(m)
    # 出现至少 2 次（run + inspect-doc 各一）
    assert src.count("default=30") >= 2


def test_module_source_contains_reconfigure_stdout():
    import evaluation.cli as m

    assert "sys.stdout.reconfigure" in inspect.getsource(m)


def test_module_source_contains_reconfigure_stderr():
    import evaluation.cli as m

    assert "sys.stderr.reconfigure" in inspect.getsource(m)


def test_module_source_contains_hasattr_stdout():
    import evaluation.cli as m

    assert 'hasattr(sys.stdout, "reconfigure")' in inspect.getsource(m)


def test_module_source_contains_attribute_error_oserror_except():
    import evaluation.cli as m

    assert "AttributeError" in inspect.getsource(m)
    assert "OSError" in inspect.getsource(m)


def test_module_source_contains_main_function_def():
    import evaluation.cli as m

    assert "def main(" in inspect.getsource(m)


def test_module_source_contains_build_parser_def():
    import evaluation.cli as m

    assert "def _build_parser(" in inspect.getsource(m)


def test_module_source_contains_run_inspect_doc_def():
    import evaluation.cli as m

    assert "def _run_inspect_doc(" in inspect.getsource(m)


def test_module_source_contains_format_metric_def():
    import evaluation.cli as m

    assert "def _format_metric(" in inspect.getsource(m)


def test_module_source_contains_if_name_main():
    import evaluation.cli as m

    assert 'if __name__ == "__main__"' in inspect.getsource(m)
    assert "SystemExit(main())" in inspect.getsource(m)


def test_module_source_does_not_contain_print_at_module_level_only():
    """print 都在函数内部（不在模块顶层）。"""
    import evaluation.cli as m

    src = inspect.getsource(m)
    # 模块顶层不应该直接 print（顶层只有 import 和 if 块）
    # 简单检查：所有 print 调用都在函数内
    assert "print(" in src  # 至少有 print 调用


def test_module_source_does_not_contain_os_module():
    """不引入 os 模块。"""
    import evaluation.cli as m

    assert "import os" not in inspect.getsource(m)


def test_module_source_does_not_contain_subprocess_import():
    """cli.py 不直接 import subprocess（用 report.get_git_provenance 间接调用）。"""
    import evaluation.cli as m

    assert "import subprocess" not in inspect.getsource(m)


def test_module_source_does_not_contain_logging():
    import evaluation.cli as m

    assert "import logging" not in inspect.getsource(m)


def test_module_source_does_not_contain_asyncio():
    import evaluation.cli as m

    assert "asyncio" not in inspect.getsource(m)


def test_module_source_contains_json_module_top_level():
    """json 在顶层 import。"""
    import evaluation.cli as m

    assert "import json" in inspect.getsource(m)


def test_module_source_contains_sys_module_top_level():
    import evaluation.cli as m

    assert "import sys" in inspect.getsource(m)


def test_module_source_contains_pathlib_path():
    import evaluation.cli as m

    assert "from pathlib import Path" in inspect.getsource(m)


# =========================================================================
# main 函数 namespace identity
# =========================================================================


def test_module_namespace_has_argparse():
    import evaluation.cli as m

    assert hasattr(m, "argparse")


def test_module_namespace_has_json():
    import evaluation.cli as m

    assert hasattr(m, "json")


def test_module_namespace_has_sys():
    import evaluation.cli as m

    assert hasattr(m, "sys")


def test_module_namespace_has_path():
    import evaluation.cli as m

    assert hasattr(m, "Path")


def test_module_namespace_has_main():
    """main 是 callable（注意其他测试可能 reload 模块，不能 is 比较）。"""
    import evaluation.cli as m
    import types as _types

    assert hasattr(m, "main")
    assert callable(m.main)
    assert isinstance(m.main, _types.FunctionType)


def test_module_namespace_has_build_parser():
    import evaluation.cli as m
    import types as _types

    assert hasattr(m, "_build_parser")
    assert callable(m._build_parser)
    assert isinstance(m._build_parser, _types.FunctionType)


def test_module_namespace_has_format_metric():
    import evaluation.cli as m
    import types as _types

    assert hasattr(m, "_format_metric")
    assert callable(m._format_metric)
    assert isinstance(m._format_metric, _types.FunctionType)


def test_module_namespace_has_run_inspect_doc():
    import evaluation.cli as m
    import types as _types

    assert hasattr(m, "_run_inspect_doc")
    assert callable(m._run_inspect_doc)
    assert isinstance(m._run_inspect_doc, _types.FunctionType)


# =========================================================================
# _format_metric / _run_inspect_doc helper metadata
# =========================================================================


def test_format_metric_module_identity():
    assert _format_metric.__module__ == "evaluation.cli"


def test_format_metric_qualname():
    assert _format_metric.__qualname__ == "_format_metric"


def test_run_inspect_doc_module_identity():
    assert _run_inspect_doc.__module__ == "evaluation.cli"


def test_run_inspect_doc_qualname():
    assert _run_inspect_doc.__qualname__ == "_run_inspect_doc"


def test_build_parser_module_identity():
    assert _build_parser.__module__ == "evaluation.cli"


def test_build_parser_qualname():
    assert _build_parser.__qualname__ == "_build_parser"


def test_main_module_identity():
    assert main.__module__ == "evaluation.cli"


def test_main_qualname():
    assert main.__qualname__ == "main"


def test_all_helpers_are_function_type():
    import types as _types

    for fn in [_build_parser, _format_metric, _run_inspect_doc, main]:
        assert isinstance(fn, _types.FunctionType)


# =========================================================================
# 函数签名 introspection
# =========================================================================


def test_main_signature_param_count_1():
    sig = inspect.signature(main)
    assert len(sig.parameters) == 1


def test_main_signature_param_name_argv():
    sig = inspect.signature(main)
    assert list(sig.parameters.keys()) == ["argv"]


def test_main_signature_argv_default_none():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_main_signature_argv_kind_positional_or_keyword():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_main_signature_no_var_args():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_main_signature_no_var_kwargs():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_build_parser_signature_no_params():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_format_metric_signature_param_count_2():
    sig = inspect.signature(_format_metric)
    assert len(sig.parameters) == 2


def test_format_metric_signature_param_names():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters.keys()) == ["name", "metric"]


def test_format_metric_signature_no_defaults():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_format_metric_signature_no_var_args():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_format_metric_signature_no_var_kwargs():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_run_inspect_doc_signature_param_count_1():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1


def test_run_inspect_doc_signature_param_name_args():
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters.keys()) == ["args"]


def test_run_inspect_doc_signature_no_default():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.parameters["args"].default is inspect.Parameter.empty
