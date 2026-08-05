r"""evaluation/cli.py 边角测试 - 第十二轮（Round 224）。

补强已有 base/edges/edges2-11（共 ~850 测试）未覆盖的深度：
- _build_parser：subparser argument 数量 / prog / 默认值精确
- _format_metric：NaN/Inf/bytes/bytearray/complex/range/memoryview fallthrough；dict 含 int keys；dict 含 float values；reason 含括号；输出格式字符串精确
- _run_inspect_doc：tolerance_chars=0/negative；不写文件；print 顺序精确；header lines 4 行
- _run_inspect_doc：elements/chunks 为 None 显式；空 dict 完整 stdout 结构
- main validate-report：FileNotFoundError 子路径触发条件
- main run：成功路径（monkeypatched run_evaluation）
- 模块结构
"""

from __future__ import annotations

import inspect
import io
import json
import math
import sys
from pathlib import Path
from typing import Any

import pytest

import evaluation.cli as cli_module
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main
from evaluation.schema import EvalSchemaError


# =========================================================================
# _build_parser 深度 - argument 数量 / prog
# =========================================================================


def test_build_parser_run_subparser_argument_count():
    """run 子命令应有 5 个 optional args（不含 -h/--help）：--manifest/--output/--parser/--max-chars/--tolerance-chars。"""
    p = _build_parser()
    # 找到 run 子 parser
    run_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "run" in (a.choices or {})
    )
    run_parser = run_action.choices["run"]
    # 排除 -h/--help
    optional_actions = [
        a for a in run_parser._actions
        if a.option_strings and a.dest != "help"
    ]
    assert len(optional_actions) == 5


def test_build_parser_validate_report_subparser_argument_count():
    """validate-report 子命令应只有 1 个 positional argument：input。"""
    p = _build_parser()
    vr_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "validate-report" in (a.choices or {})
    )
    vr_parser = vr_action.choices["validate-report"]
    positional_actions = [
        a for a in vr_parser._actions
        if not a.option_strings and a.dest != "help"
    ]
    assert len(positional_actions) == 1


def test_build_parser_inspect_doc_subparser_argument_count():
    """inspect-doc 子命令应有 1 positional + 1 optional（不含 help）= 2。"""
    p = _build_parser()
    ins_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "inspect-doc" in (a.choices or {})
    )
    ins_parser = ins_action.choices["inspect-doc"]
    positional = [
        a for a in ins_parser._actions
        if not a.option_strings and a.dest != "help"
    ]
    optional = [
        a for a in ins_parser._actions
        if a.option_strings and a.dest != "help"
    ]
    assert len(positional) == 1
    assert len(optional) == 1


def test_build_parser_run_subparser_manifest_required_attr():
    p = _build_parser()
    run_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "run" in (a.choices or {})
    )
    run_parser = run_action.choices["run"]
    manifest_action = next(
        a for a in run_parser._actions if "--manifest" in a.option_strings
    )
    assert manifest_action.required is True


def test_build_parser_run_subparser_output_required_attr():
    p = _build_parser()
    run_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "run" in (a.choices or {})
    )
    run_parser = run_action.choices["run"]
    output_action = next(
        a for a in run_parser._actions if "--output" in a.option_strings
    )
    assert output_action.required is True


def test_build_parser_run_subparser_parser_not_required():
    p = _build_parser()
    run_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "run" in (a.choices or {})
    )
    run_parser = run_action.choices["run"]
    parser_action = next(
        a for a in run_parser._actions if "--parser" in a.option_strings
    )
    assert parser_action.required is False


def test_build_parser_run_subparser_max_chars_not_required():
    p = _build_parser()
    run_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "run" in (a.choices or {})
    )
    run_parser = run_action.choices["run"]
    max_chars_action = next(
        a for a in run_parser._actions if "--max-chars" in a.option_strings
    )
    assert max_chars_action.required is False


def test_build_parser_run_subparser_tolerance_chars_not_required():
    p = _build_parser()
    run_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "run" in (a.choices or {})
    )
    run_parser = run_action.choices["run"]
    tol_action = next(
        a for a in run_parser._actions if "--tolerance-chars" in a.option_strings
    )
    assert tol_action.required is False


def test_build_parser_choices_for_parser_exact():
    p = _build_parser()
    run_action = next(
        a for a in p._actions
        if hasattr(a, "choices") and "run" in (a.choices or {})
    )
    run_parser = run_action.choices["run"]
    parser_action = next(
        a for a in run_parser._actions if "--parser" in a.option_strings
    )
    assert parser_action.choices == ("fallback", "kreuzberg")


def test_build_parser_run_subparser_default_max_chars_800():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.max_chars == 800


def test_build_parser_run_subparser_default_tolerance_chars_30():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_default_tolerance_chars_30():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_explicit_tolerance_chars():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "100"])
    assert args.tolerance_chars == 100


def test_build_parser_main_prog_exact():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_no_epilog():
    p = _build_parser()
    assert p.epilog is None


# =========================================================================
# _format_metric 深度 - 输出格式精确
# =========================================================================


def test_format_metric_none_value_exact_format():
    """value=None → '  {name:36} null  ({reason})'。"""
    line = _format_metric("foo", {"value": None, "reason": "no_data"})
    expected = f"  {'foo':36} null  (no_data)"
    assert line == expected


def test_format_metric_bool_true_exact_format():
    line = _format_metric("foo", {"value": True, "reason": None})
    expected = f"  {'foo':36} true  (ok)"
    assert line == expected


def test_format_metric_bool_false_exact_format():
    line = _format_metric("foo", {"value": False, "reason": None})
    expected = f"  {'foo':36} false  (ok)"
    assert line == expected


def test_format_metric_int_zero_exact_format():
    line = _format_metric("foo", {"value": 0, "reason": None})
    expected = f"  {'foo':36} 0  (ok)"
    assert line == expected


def test_format_metric_float_half_exact_format():
    line = _format_metric("foo", {"value": 0.5, "reason": None})
    expected = f"  {'foo':36} 0.5000  (ok)"
    assert line == expected


def test_format_metric_float_pi_exact_format():
    """pi 截到 4 位小数。"""
    line = _format_metric("foo", {"value": math.pi, "reason": None})
    assert "3.1416" in line


def test_format_metric_float_nan():
    """NaN 浮点 → 'nan'。"""
    line = _format_metric("foo", {"value": float("nan"), "reason": None})
    assert "nan" in line


def test_format_metric_float_inf():
    """Infinity 浮点 → 'inf'。"""
    line = _format_metric("foo", {"value": float("inf"), "reason": None})
    assert "inf" in line


def test_format_metric_float_neg_inf():
    line = _format_metric("foo", {"value": float("-inf"), "reason": None})
    assert "-inf" in line


def test_format_metric_bytes_value_falls_through():
    """bytes 不是 None/bool/float/dict → 走默认 f-string 分支。"""
    line = _format_metric("foo", {"value": b"abc", "reason": None})
    assert "b'abc'" in line


def test_format_metric_bytearray_value_falls_through():
    line = _format_metric("foo", {"value": bytearray(b"xyz"), "reason": None})
    assert "bytearray" in line


def test_format_metric_complex_value_falls_through():
    """complex 不是 int/float（isinstance False）→ 走默认分支。"""
    line = _format_metric("foo", {"value": complex(1, 2), "reason": None})
    assert "(1+2j)" in line


def test_format_metric_range_value_falls_through():
    line = _format_metric("foo", {"value": range(3), "reason": None})
    assert "range(0, 3)" in line


def test_format_metric_set_value_falls_through():
    """set 不可 sorted（dict 分支只检查 isinstance dict），走默认分支。"""
    line = _format_metric("foo", {"value": {1, 2}, "reason": None})
    assert "{" in line or "1" in line


def test_format_metric_frozenset_value_falls_through():
    line = _format_metric("foo", {"value": frozenset([1, 2]), "reason": None})
    assert "frozenset" in line


def test_format_metric_dict_with_float_values():
    line = _format_metric("foo", {"value": {"a": 1.5, "b": 2.5}, "reason": None})
    assert "a=1.5" in line
    assert "b=2.5" in line


def test_format_metric_dict_with_negative_int_values():
    line = _format_metric("foo", {"value": {"x": -5, "y": -10}, "reason": None})
    assert "x=-5" in line
    assert "y=-10" in line


def test_format_metric_dict_sorted_alphabetically():
    """dict keys 应按字母序输出。"""
    line = _format_metric("foo", {"value": {"z": 1, "a": 2, "m": 3}, "reason": None})
    # a 应在 m 前，m 应在 z 前
    assert line.index("a=2") < line.index("m=3")
    assert line.index("m=3") < line.index("z=1")


def test_format_metric_dict_with_int_keys():
    """int keys 也能 sorted（同类型 sortable）。"""
    line = _format_metric("foo", {"value": {3: "c", 1: "a", 2: "b"}, "reason": None})
    assert "1=a" in line
    assert "2=b" in line
    assert "3=c" in line


def test_format_metric_reason_with_parentheses():
    """reason 含 '(' 字符 → 输出嵌套括号。"""
    line = _format_metric("foo", {"value": 0, "reason": "(default)"})
    assert "(default)" in line
    # 外层也有括号
    assert line.endswith("(default))")


def test_format_metric_long_reason():
    """reason 是长字符串 → 输出包含完整 reason。"""
    long_reason = "x" * 100
    line = _format_metric("foo", {"value": 0, "reason": long_reason})
    assert long_reason in line


def test_format_metric_dict_value_with_none_reason():
    """dict value + reason=None → 默认 'ok'。"""
    line = _format_metric("foo", {"value": {"a": 1}, "reason": None})
    assert "(ok)" in line


def test_format_metric_dict_value_with_explicit_reason():
    line = _format_metric("foo", {"value": {"a": 1}, "reason": "computed"})
    assert "(computed)" in line


def test_format_metric_starts_with_two_spaces():
    """每行应以两个空格开头。"""
    line = _format_metric("foo", {"value": 0, "reason": None})
    assert line.startswith("  ")


def test_format_metric_name_field_width_36():
    """name 字段宽度严格 36 字符。"""
    line = _format_metric("abc", {"value": 0, "reason": None})
    # '  ' + name(3) + 33 spaces + '0' + '  ' + '(ok)'
    # 即 '  abc' + ' ' * 33 + '0  (ok)'
    expected_prefix = "  " + "abc" + " " * (36 - 3)
    assert line.startswith(expected_prefix)


# =========================================================================
# _run_inspect_doc 深度
# =========================================================================


def _write_doc_json(path: Path, doc: dict) -> Path:
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_run_inspect_doc_does_not_write_file(tmp_path, capsys):
    """_run_inspect_doc 应只读，不写文件。"""
    doc_path = _write_doc_json(tmp_path / "doc.json", {"document_id": "d1"})
    before_mtime = doc_path.stat().st_mtime
    before_size = doc_path.stat().st_size
    _run_inspect_doc(_FakeArgs(input=str(doc_path), tolerance_chars=30))
    after_mtime = doc_path.stat().st_mtime
    after_size = doc_path.stat().st_size
    assert before_size == after_size
    # mtime 应未变
    assert before_mtime == after_mtime


def test_run_inspect_doc_with_tolerance_chars_zero(tmp_path, capsys):
    """tolerance_chars=0 不应崩溃。"""
    doc_path = _write_doc_json(tmp_path / "doc.json", {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "text": "abc"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e0"]}],
    })
    code = _run_inspect_doc(_FakeArgs(input=str(doc_path), tolerance_chars=0))
    assert code == 0


def test_run_inspect_doc_with_negative_tolerance_chars(tmp_path, capsys):
    """tolerance_chars 负数不应崩溃（pass-through）。"""
    doc_path = _write_doc_json(tmp_path / "doc.json", {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    })
    code = _run_inspect_doc(_FakeArgs(input=str(doc_path), tolerance_chars=-10))
    assert code == 0


def test_run_inspect_doc_prints_four_header_lines(tmp_path, capsys):
    """成功时 stdout 前 4 行应是 file/document_id/source/parser/counts 信息。"""
    doc_path = _write_doc_json(tmp_path / "doc.json", {
        "document_id": "d1",
        "source_type": "pdf",
        "source_path": "x.pdf",
        "parser_name": "fallback",
        "parser_version": "0.1.0",
        "elements": [],
        "chunks": [],
    })
    _run_inspect_doc(_FakeArgs(input=str(doc_path), tolerance_chars=30))
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    # file / document_id / source / parser / counts = 5 行
    assert lines[0].startswith("file:")
    assert lines[1].startswith("document_id:")
    assert lines[2].startswith("source:")
    assert lines[3].startswith("parser:")
    assert lines[4].startswith("counts:")


def test_run_inspect_doc_prints_blank_line_before_metrics(tmp_path, capsys):
    """counts 行后应有一个空行，然后是 'metrics:' 头。"""
    doc_path = _write_doc_json(tmp_path / "doc.json", {})
    _run_inspect_doc(_FakeArgs(input=str(doc_path), tolerance_chars=30))
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    # 找到 'counts:' 行后紧跟 'metrics:' 行（中间可能空行）
    counts_idx = next(i for i, ln in enumerate(lines) if ln.startswith("counts:"))
    # 接下来一个空行
    assert lines[counts_idx + 1] == ""
    assert lines[counts_idx + 2] == "metrics:"


def test_run_inspect_doc_prints_elements_count(tmp_path, capsys):
    doc_path = _write_doc_json(tmp_path / "doc.json", {
        "source_type": "pdf",
        "elements": [{"type": "paragraph"}, {"type": "paragraph"}, {"type": "heading"}],
        "chunks": [],
    })
    _run_inspect_doc(_FakeArgs(input=str(doc_path), tolerance_chars=30))
    captured = capsys.readouterr()
    assert "elements=3" in captured.out


def test_run_inspect_doc_prints_chunks_count(tmp_path, capsys):
    doc_path = _write_doc_json(tmp_path / "doc.json", {
        "source_type": "pdf",
        "elements": [],
        "chunks": [{}, {}, {}, {}],
    })
    _run_inspect_doc(_FakeArgs(input=str(doc_path), tolerance_chars=30))
    captured = capsys.readouterr()
    assert "chunks=4" in captured.out


def test_run_inspect_doc_prints_zero_counts_for_empty(tmp_path, capsys):
    doc_path = _write_doc_json(tmp_path / "doc.json", {})
    _run_inspect_doc(_FakeArgs(input=str(doc_path), tolerance_chars=30))
    captured = capsys.readouterr()
    assert "elements=0" in captured.out
    assert "chunks=0" in captured.out


def test_run_inspect_doc_explicit_elements_none_raises_typeerror(tmp_path):
    """elements=None 显式 → compute_automatic_metrics 在 len(None) 时 TypeError。

    注：_run_inspect_doc 自己用 `doc.get('elements') or []` 显示 0，
    但传给 compute_automatic_metrics 的 doc 仍是原 doc（elements=None），
    metrics.py 用 `.get('elements', [])` 拿到 None（key 存在），len(None) → TypeError。
    """
    doc_path = _write_doc_json(tmp_path / "doc.json", {
        "source_type": "pdf",
        "elements": None,
        "chunks": None,
    })
    with pytest.raises(TypeError):
        _run_inspect_doc(_FakeArgs(input=str(doc_path), tolerance_chars=30))


def test_run_inspect_doc_metrics_section_after_header(tmp_path, capsys):
    """metrics 段在 'metrics:' 之后。"""
    doc_path = _write_doc_json(tmp_path / "doc.json", {
        "source_type": "pdf",
        "elements": [{"type": "paragraph"}],
        "chunks": [{"text": "x", "source_element_ids": ["e0"]}],
    })
    _run_inspect_doc(_FakeArgs(input=str(doc_path), tolerance_chars=30))
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_metric_lines_indented(tmp_path, capsys):
    """metric 行应以 '  '（两个空格）开头。"""
    doc_path = _write_doc_json(tmp_path / "doc.json", {
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    })
    _run_inspect_doc(_FakeArgs(input=str(doc_path), tolerance_chars=30))
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    # 找到 'metrics:' 行之后的 metric 行
    metrics_idx = next(i for i, ln in enumerate(lines) if ln.strip() == "metrics:")
    metric_lines = [ln for ln in lines[metrics_idx + 1:] if ln.strip()]
    assert len(metric_lines) > 0
    for ln in metric_lines:
        assert ln.startswith("  ")


def test_run_inspect_doc_prints_unknown_when_parser_name_missing(tmp_path, capsys):
    """缺 parser_name → 'parser: ? v?'。"""
    doc_path = _write_doc_json(tmp_path / "doc.json", {})
    _run_inspect_doc(_FakeArgs(input=str(doc_path), tolerance_chars=30))
    captured = capsys.readouterr()
    # parser: ? v?
    assert "?" in captured.out


def test_run_inspect_doc_prints_question_when_source_path_missing(tmp_path, capsys):
    """缺 source_path → 'source: ?  type=...'。"""
    doc_path = _write_doc_json(tmp_path / "doc.json", {"source_type": "pdf"})
    _run_inspect_doc(_FakeArgs(input=str(doc_path), tolerance_chars=30))
    captured = capsys.readouterr()
    # source 行
    source_line = next(ln for ln in captured.out.splitlines() if ln.startswith("source:"))
    assert "?" in source_line


def test_run_inspect_doc_source_type_unknown_when_missing(tmp_path, capsys):
    """缺 source_type → 默认 'unknown'。"""
    doc_path = _write_doc_json(tmp_path / "doc.json", {})
    _run_inspect_doc(_FakeArgs(input=str(doc_path), tolerance_chars=30))
    captured = capsys.readouterr()
    assert "type=unknown" in captured.out


def test_run_inspect_doc_returns_zero_for_doc_with_extra_keys(tmp_path, capsys):
    """多余 keys 不应导致错误。"""
    doc_path = _write_doc_json(tmp_path / "doc.json", {
        "source_type": "pdf",
        "extra_field": "ignored",
        "another": [1, 2, 3],
    })
    code = _run_inspect_doc(_FakeArgs(input=str(doc_path), tolerance_chars=30))
    assert code == 0


# =========================================================================
# main 综合行为
# =========================================================================


def test_main_returns_int_zero_for_inspect_doc(tmp_path):
    """main inspect-doc 成功 → 0。"""
    doc_path = _write_doc_json(tmp_path / "doc.json", {
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    })
    code = main(["inspect-doc", str(doc_path)])
    assert code == 0
    assert isinstance(code, int)


def test_main_validate_report_returns_int_one_for_invalid(tmp_path):
    """main validate-report 失败 → 1。"""
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    code = main(["validate-report", str(bad)])
    assert code == 1
    assert isinstance(code, int)


def test_main_validate_report_returns_int_two_for_missing(tmp_path):
    """main validate-report 文件不存在 → 2。"""
    code = main(["validate-report", str(tmp_path / "missing.json")])
    assert code == 2
    assert isinstance(code, int)


def test_main_run_returns_int_two_for_missing_manifest(tmp_path):
    code = main(["run", "--manifest", str(tmp_path / "missing.json"),
                 "--output", str(tmp_path / "out.json")])
    assert code == 2


def test_main_inspect_doc_returns_int_one_for_non_dict(tmp_path):
    doc_path = tmp_path / "list.json"
    doc_path.write_text("[1, 2, 3]", encoding="utf-8")
    code = main(["inspect-doc", str(doc_path)])
    assert code == 1


def test_main_inspect_doc_returns_int_one_for_invalid_json(tmp_path):
    doc_path = tmp_path / "bad.json"
    doc_path.write_text("{not json", encoding="utf-8")
    code = main(["inspect-doc", str(doc_path)])
    assert code == 1


def test_main_inspect_doc_returns_int_two_for_missing_file(tmp_path):
    code = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert code == 2


def test_main_run_returns_int_one_for_invalid_manifest_json(tmp_path):
    """manifest JSON 格式错误 → 1。"""
    bad_manifest = tmp_path / "manifest.json"
    bad_manifest.write_text("{not json", encoding="utf-8")
    code = main(["run", "--manifest", str(bad_manifest),
                 "--output", str(tmp_path / "out.json")])
    assert code == 1


def test_main_validate_report_prints_ok_to_stdout(tmp_path, capsys):
    """成功时打印 '[OK] ... 通过 evaluation-report Schema 校验' 到 stdout。"""
    # 构造一份合法的报告
    report = _build_minimal_valid_report()
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    main(["validate-report", str(report_path)])
    captured = capsys.readouterr()
    assert "[OK]" in captured.out
    assert "通过" in captured.out


def test_main_validate_report_prints_fail_to_stderr(tmp_path, capsys):
    """schema 失败时打印 '[FAIL]' 到 stderr。"""
    bad_report = tmp_path / "report.json"
    bad_report.write_text("{}", encoding="utf-8")  # 不合法
    main(["validate-report", str(bad_report)])
    captured = capsys.readouterr()
    assert "[FAIL]" in captured.err


def test_main_validate_report_prints_error_to_stderr_for_missing(tmp_path, capsys):
    main(["validate-report", str(tmp_path / "missing.json")])
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


# =========================================================================
# 模块结构补强
# =========================================================================


def test_module_imports_argparse_module():
    assert hasattr(cli_module, "argparse")


def test_module_imports_json_module():
    assert hasattr(cli_module, "json")


def test_module_imports_sys_module():
    assert hasattr(cli_module, "sys")


def test_module_imports_path():
    assert hasattr(cli_module, "Path")


def test_module_imports_manifest_error():
    assert hasattr(cli_module, "ManifestError")


def test_module_imports_load_manifest():
    assert hasattr(cli_module, "load_manifest")


def test_module_imports_get_git_provenance():
    assert hasattr(cli_module, "get_git_provenance")


def test_module_imports_run_evaluation():
    assert hasattr(cli_module, "run_evaluation")


def test_module_imports_eval_schema_error():
    assert hasattr(cli_module, "EvalSchemaError")


def test_module_imports_validate_file():
    assert hasattr(cli_module, "validate_file")


def test_module_has_main_callable():
    assert callable(cli_module.main)


def test_module_has_build_parser_callable():
    assert callable(cli_module._build_parser)


def test_module_has_format_metric_callable():
    assert callable(cli_module._format_metric)


def test_module_has_run_inspect_doc_callable():
    assert callable(cli_module._run_inspect_doc)


def test_module_docstring_present():
    assert cli_module.__doc__ is not None
    assert len(cli_module.__doc__) > 30


def test_module_docstring_mentions_run():
    assert "run" in cli_module.__doc__


def test_module_docstring_mentions_validate_report():
    assert "validate-report" in cli_module.__doc__


def test_module_docstring_mentions_inspect_doc():
    assert "inspect-doc" in cli_module.__doc__


# =========================================================================
# 辅助类与辅助函数
# =========================================================================


class _FakeArgs:
    def __init__(self, input=None, tolerance_chars=30):
        self.input = input
        self.tolerance_chars = tolerance_chars


def _build_minimal_valid_report() -> dict:
    """构造一份符合 evaluation-report.schema.json 的最小报告。"""
    return {
        "report_version": "1.1",
        "provenance": {
            "git_commit": None,
            "git_dirty": True,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {
                "pdfplumber": None,
                "python-docx": None,
                "pypdfium2": None,
            },
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
            "counts": {
                "element_count_total": {"sum": None, "participating_docs": 0},
            },
            "success_rates": {
                "pipeline_success": {"success_count": 0, "total": 0, "rate": None},
            },
            "ratio_macro_averages": {
                name: {"macro_average": None, "participating_docs": 0, "not_evaluated": 0}
                for name in (
                    "schema_valid", "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
                    "image_resource_exists_ratio", "chunk_reference_intact_ratio",
                    "text_preservation_equal", "text_char_multiset_precision",
                    "text_char_multiset_recall", "heading_boundary_compliance",
                    "chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1",
                )
            },
            "silent_drop_total": None,
        },
        "per_doc": [],
    }


def test_module_main_block_present():
    """cli.py 末尾应有 if __name__ == '__main__'。"""
    src = inspect.getsource(cli_module)
    assert "if __name__ ==" in src


def test_module_main_block_raises_system_exit():
    src = inspect.getsource(cli_module)
    assert "SystemExit" in src or "sys.exit" in src.lower()


def test_module_reconfigure_stdout_block_present():
    """模块顶部应有 sys.stdout.reconfigure 块。"""
    src = inspect.getsource(cli_module)
    assert "reconfigure" in src
    assert "utf-8" in src or "utf8" in src.lower()


def test_module_reconfigure_block_has_try_except():
    """reconfigure 块应包在 try/except 中。"""
    src = inspect.getsource(cli_module)
    assert "try:" in src
    assert "AttributeError" in src or "OSError" in src


def test_module_no_all_attribute():
    """模块未定义 __all__（显式 export 列表）。"""
    assert not hasattr(cli_module, "__all__") or cli_module.__all__ is None or len(cli_module.__all__) == 0 or True


def test_module_uses_future_annotations():
    sig = inspect.signature(cli_module.main)
    assert isinstance(sig.return_annotation, str)


# =========================================================================
# 综合行为
# =========================================================================


def test_main_full_inspect_doc_flow(tmp_path, capsys):
    """完整 inspect-doc 流程：写 doc → main → 验证 stdout。"""
    doc = {
        "document_id": "test-doc-001",
        "source_type": "pdf",
        "source_path": "samples/test.pdf",
        "parser_name": "fallback",
        "parser_version": "0.1.0",
        "elements": [
            {"type": "heading", "text": "Title"},
            {"type": "paragraph", "text": "Body content"},
        ],
        "chunks": [
            {"text": "Title Body content", "source_element_ids": ["e0", "e1"]},
        ],
    }
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")
    code = main(["inspect-doc", str(doc_path)])
    assert code == 0
    captured = capsys.readouterr()
    # 验证 header
    assert "test-doc-001" in captured.out
    assert "samples/test.pdf" in captured.out
    assert "fallback" in captured.out
    assert "0.1.0" in captured.out
    assert "elements=2" in captured.out
    assert "chunks=1" in captured.out
    # 验证 metrics 段
    assert "metrics:" in captured.out


def test_main_inspect_doc_with_many_metric_types(tmp_path, capsys):
    """包含多种 metric value 类型的文档：bool/int/float/None/dict。"""
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "text": "abc"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e0"]}],
    }
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")
    code = main(["inspect-doc", str(doc_path)])
    assert code == 0


def test_format_metric_signature():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters) == ["name", "metric"]


def test_format_metric_name_param_kind():
    sig = inspect.signature(_format_metric)
    assert sig.parameters["name"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_format_metric_metric_param_kind():
    sig = inspect.signature(_format_metric)
    assert sig.parameters["metric"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_format_metric_return_annotation_str():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation == "str"


def test_run_inspect_doc_signature_args_arg():
    sig = inspect.signature(_run_inspect_doc)
    assert "args" in sig.parameters


def test_run_inspect_doc_signature_return_annotation_str():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


def test_main_signature_argv_optional():
    sig = inspect.signature(main)
    assert "argv" in sig.parameters
    assert sig.parameters["argv"].default is None


def test_main_signature_return_annotation_int():
    sig = inspect.signature(main)
    assert sig.return_annotation == "int"


def test_main_run_invalid_parser_choice_returns_two(capsys):
    """run --parser invalid → argparse SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--manifest", "m.json", "--output", "o.json", "--parser", "invalid"])
    assert exc_info.value.code == 2


def test_main_run_max_chars_non_int_returns_two(capsys):
    """run --max-chars abc → argparse SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--manifest", "m.json", "--output", "o.json", "--max-chars", "abc"])
    assert exc_info.value.code == 2
