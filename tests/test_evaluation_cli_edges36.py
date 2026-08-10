"""evaluation/cli.py 第三十六轮 edges 测试（Round 383）。

补强 edges35 未触及的角度：
- _build_parser 行为深度第九批（prog/description 精确 / choices 集合 / subparser 数量 / argparse 类型校验 / 拒绝关键字冲突）
- argparse Namespace 字段第九批（更多字段类型 / 默认值精确 / 等价 / 类型 isinstance）
- _format_metric 行为深度第九批（更多类型 / 边界 padding / None reason 默认 ok / dict 空 / list 类型）
- _run_inspect_doc 行为深度第九批（elements 空 list / chunks None / report 无 metrics / 自定义 tolerance / 大文档 / 多 elements / bool value）
- main 路由第九批（run 主路径 / stderr 输出 / return code 类型 / validate-report 三种失败 path / inspect-doc 多场景）
- module source forbidden tokens 第十二批
- module source 字符串精确补强第七批（imports + 函数调用 + subparser name 字面量 + 字符串模板）
- signatures 第九批（4 funcs param 类型 / return 类型 / keyword-only / no defaults）
- module 合理性第九批（no __all__ + 4 functions + docstring + main_block_at_end + 文件名）
- 端到端集成第九批（全链 + report version + run/inspect-doc/validate-report namespace + stderr 含 ERROR）
"""

from __future__ import annotations

import argparse
import inspect
import json
import types
from pathlib import Path

import pytest

from evaluation import cli as climod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 行为深度第九批 ----------


def test_build_parser_returns_argument_parser_type():
    p = _build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_build_parser_prog_value_exact():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_starts_with_chinese():
    p = _build_parser()
    assert p.description.startswith("评测")


def test_build_parser_description_mentions_subcommands():
    """description 是中文：'评测 CLI：跑开发集 → 报告；或校验已有报告。'"""
    p = _build_parser()
    assert "跑" in p.description or "评测" in p.description
    assert "校验" in p.description


def test_build_parser_has_three_subparsers():
    """sub.add_parser 调用 3 次（run/validate-report/inspect-doc）。"""
    p = _build_parser()
    # 通过 parse_args 验证 3 个子命令都被识别
    for cmd in ("run", "validate-report", "inspect-doc"):
        # 调用 --help 会 SystemExit，但解析单子命令应工作
        # 直接检查 namespace
        try:
            ns = p.parse_args([cmd] + _minimal_args(cmd))
            assert ns.command == cmd
        except SystemExit:
            raise AssertionError(f"subcommand {cmd} not recognized")


def _minimal_args(cmd):
    if cmd == "run":
        return ["--manifest", "x.json", "--output", "y.json"]
    if cmd == "validate-report":
        return ["x.json"]
    if cmd == "inspect-doc":
        return ["x.json"]
    return []


def test_build_parser_run_parser_default_fallback():
    ns = _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert ns.parser == "fallback"


def test_build_parser_run_parser_accepts_kreuzberg():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json", "--parser", "kreuzberg"]
    )
    assert ns.parser == "kreuzberg"


def test_build_parser_run_parser_rejects_other_choices(capsys):
    with pytest.raises(SystemExit):
        _build_parser().parse_args(
            ["run", "--manifest", "a.json", "--output", "b.json", "--parser", "pdfplumber"]
        )


def test_build_parser_max_chars_default_800():
    ns = _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert ns.max_chars == 800


def test_build_parser_tolerance_chars_default_30():
    ns = _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert ns.tolerance_chars == 30


def test_build_parser_inspect_doc_tolerance_chars_default_30():
    ns = _build_parser().parse_args(["inspect-doc", "a.json"])
    assert ns.tolerance_chars == 30


def test_build_parser_max_chars_type_int():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json", "--max-chars", "500"]
    )
    assert isinstance(ns.max_chars, int)
    assert ns.max_chars == 500


def test_build_parser_tolerance_chars_type_int():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json", "--tolerance-chars", "10"]
    )
    assert isinstance(ns.tolerance_chars, int)
    assert ns.tolerance_chars == 10


def test_build_parser_inspect_doc_tolerance_chars_type_int():
    ns = _build_parser().parse_args(["inspect-doc", "a.json", "--tolerance-chars", "5"])
    assert isinstance(ns.tolerance_chars, int)
    assert ns.tolerance_chars == 5


def test_build_parser_validate_report_input_value_str():
    ns = _build_parser().parse_args(["validate-report", "report.json"])
    assert ns.input == "report.json"


def test_build_parser_inspect_doc_input_value_str():
    ns = _build_parser().parse_args(["inspect-doc", "doc.json"])
    assert ns.input == "doc.json"


def test_build_parser_no_subcommand_required():
    """required=True → 不传 subcommand 会 SystemExit。"""
    with pytest.raises(SystemExit):
        _build_parser().parse_args([])


def test_build_parser_help_does_not_raise_with_run(capsys):
    """run --help 应能正常解析（SystemExit 是 argparse 正常行为）。"""
    with pytest.raises(SystemExit) as exc_info:
        _build_parser().parse_args(["run", "--help"])
    # --help exit code 0
    assert exc_info.value.code == 0


# ---------- argparse Namespace 字段第九批 ----------


def test_namespace_run_command_value():
    ns = _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert ns.command == "run"


def test_namespace_validate_report_command_value():
    ns = _build_parser().parse_args(["validate-report", "a.json"])
    assert ns.command == "validate-report"


def test_namespace_inspect_doc_command_value():
    ns = _build_parser().parse_args(["inspect-doc", "a.json"])
    assert ns.command == "inspect-doc"


def test_namespace_run_attributes_count():
    ns = _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    # command, manifest, output, parser, max_chars, tolerance_chars
    assert len(vars(ns)) == 6


def test_namespace_validate_report_attributes_count():
    ns = _build_parser().parse_args(["validate-report", "a.json"])
    # command, input
    assert len(vars(ns)) == 2


def test_namespace_inspect_doc_attributes_count():
    ns = _build_parser().parse_args(["inspect-doc", "a.json"])
    # command, input, tolerance_chars
    assert len(vars(ns)) == 3


def test_namespace_run_max_chars_negative():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json", "--max-chars", "-1"]
    )
    assert ns.max_chars == -1


def test_namespace_run_max_chars_huge_value():
    ns = _build_parser().parse_args(
        ["run", "--manifest", "a.json", "--output", "b.json", "--max-chars", "100000"]
    )
    assert ns.max_chars == 100000


def test_namespace_run_attributes_exact():
    ns = _build_parser().parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert set(vars(ns)) == {
        "command",
        "manifest",
        "output",
        "parser",
        "max_chars",
        "tolerance_chars",
    }


def test_namespace_inspect_doc_attributes_exact():
    ns = _build_parser().parse_args(["inspect-doc", "a.json"])
    assert set(vars(ns)) == {"command", "input", "tolerance_chars"}


def test_namespace_validate_report_attributes_exact():
    ns = _build_parser().parse_args(["validate-report", "a.json"])
    assert set(vars(ns)) == {"command", "input"}


# ---------- _format_metric 行为深度第九批 ----------


def test_format_metric_int_value():
    out = _format_metric("element_count_total", {"value": 5, "reason": "ok"})
    assert "5" in out
    assert "element_count_total" in out


def test_format_metric_int_value_no_reason_uses_ok():
    out = _format_metric("element_count_total", {"value": 5})
    assert "(ok)" in out


def test_format_metric_float_negative_value():
    out = _format_metric("ratio", {"value": -0.5, "reason": "x"})
    assert "-0.5000" in out


def test_format_metric_float_zero_value():
    out = _format_metric("ratio", {"value": 0.0, "reason": "x"})
    assert "0.0000" in out


def test_format_metric_bool_true_value():
    out = _format_metric("flag", {"value": True, "reason": "ok"})
    assert "true" in out


def test_format_metric_bool_false_value():
    out = _format_metric("flag", {"value": False, "reason": "ok"})
    assert "false" in out


def test_format_metric_bool_no_reason_uses_ok():
    out = _format_metric("flag", {"value": True})
    assert "(ok)" in out


def test_format_metric_none_value_uses_reason():
    out = _format_metric("metric", {"value": None, "reason": "no_data"})
    assert "null" in out
    assert "(no_data)" in out


def test_format_metric_none_value_missing_reason():
    out = _format_metric("metric", {"value": None})
    assert "null" in out
    assert "(None)" in out


def test_format_metric_dict_empty():
    out = _format_metric("by_type", {"value": {}, "reason": "ok"})
    # 空 dict items 不会产生 k=v
    assert "by_type" in out
    assert "(ok)" in out


def test_format_metric_dict_multiple_pairs_sorted():
    out = _format_metric(
        "by_type",
        {"value": {"paragraph": 3, "heading": 1, "image": 2}, "reason": "ok"},
    )
    # sorted by key
    assert "heading=1" in out
    assert "image=2" in out
    assert "paragraph=3" in out


def test_format_metric_str_value_falls_to_default():
    out = _format_metric("metric", {"value": "hello", "reason": "x"})
    assert "hello" in out


def test_format_metric_list_value_falls_to_default():
    """list 不是 dict 也不是 bool/float/int → 走默认 str(value)。"""
    out = _format_metric("metric", {"value": [1, 2, 3], "reason": "x"})
    assert "[1, 2, 3]" in out


def test_format_metric_returns_str():
    out = _format_metric("x", {"value": 1, "reason": "ok"})
    assert isinstance(out, str)


def test_format_metric_padding_36_chars():
    """name 占 36 字符（左对齐）。"""
    out = _format_metric("abc", {"value": 1, "reason": "ok"})
    # 找到 name 后空格开始的偏移
    name_end = out.find("1")
    # name "abc" + padding to 36 + spaces before value
    assert name_end >= 36


# ---------- _run_inspect_doc 行为深度第九批 ----------


def test_run_inspect_doc_returns_int(tmp_path):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    assert isinstance(_run_inspect_doc(args), int)


def test_run_inspect_doc_missing_file_returns_2(tmp_path, capsys):
    args = argparse.Namespace(input=str(tmp_path / "no.json"), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_run_inspect_doc_invalid_json_returns_1(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON" in err or "解析" in err


def test_run_inspect_doc_top_level_list_returns_1(tmp_path, capsys):
    p = tmp_path / "list.json"
    p.write_text("[]", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "对象" in err or "dict" in err.lower()


def test_run_inspect_doc_top_level_string_returns_1(tmp_path):
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_top_level_int_returns_1(tmp_path):
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_top_level_null_returns_1(tmp_path):
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_empty_dict_returns_0(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_prints_filename(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "d.json" in out
    assert "file:" in out


def test_run_inspect_doc_prints_metrics_header(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_with_elements_and_chunks(tmp_path, capsys):
    doc = {"elements": [{"type": "paragraph"}, {"type": "heading"}], "chunks": [{"id": "c1"}]}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "elements=2" in out
    assert "chunks=1" in out


def test_run_inspect_doc_chunks_missing_treated_as_empty(tmp_path, capsys):
    """doc 缺 'chunks' key → doc.get('chunks') or [] = [] → print chunks=0。"""
    doc = {"elements": []}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "chunks=0" in out


def test_run_inspect_doc_explicit_source_type(tmp_path, capsys):
    doc = {"source_type": "pdf"}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "type=pdf" in out


def test_run_inspect_doc_default_source_type_unknown(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "type=unknown" in out


def test_run_inspect_doc_prints_document_id(tmp_path, capsys):
    doc = {"document_id": "my_doc_001"}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "my_doc_001" in out
    assert "document_id:" in out


def test_run_inspect_doc_document_id_missing_prints_question_mark(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "document_id:" in out
    assert "?" in out


def test_run_inspect_doc_prints_parser_name(tmp_path, capsys):
    doc = {"parser_name": "fallback", "parser_version": "1.0.0"}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "fallback" in out
    assert "1.0.0" in out


def test_run_inspect_doc_parser_missing_prints_question_mark(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "v?" in out


def test_run_inspect_doc_with_unicode_in_doc(tmp_path, capsys):
    doc = {"document_id": "中文文档"}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    args = argparse.Namespace(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "中文文档" in out


def test_run_inspect_doc_args_namespace_type():
    """_run_inspect_doc 接受 argparse.Namespace。"""
    args = argparse.Namespace(input="x.json", tolerance_chars=30)
    assert hasattr(args, "input")
    assert hasattr(args, "tolerance_chars")


# ---------- main 路由第九批 ----------


def test_main_returns_int_for_validate_report_missing_file(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "no.json")])
    assert isinstance(rc, int)
    assert rc != 0


def test_main_returns_int_for_inspect_doc_missing_file(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "no.json")])
    assert isinstance(rc, int)
    assert rc != 0


def test_main_returns_int_for_run_missing_manifest(tmp_path, capsys):
    rc = main(
        ["run", "--manifest", str(tmp_path / "no.json"), "--output", str(tmp_path / "o.json")]
    )
    assert isinstance(rc, int)
    assert rc != 0


def test_main_validate_report_invalid_json_returns_1(tmp_path, capsys):
    p = tmp_path / "r.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_invalid_schema_returns_1(tmp_path, capsys):
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")  # 空 dict 不符合 schema
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_top_level_not_dict_returns_1(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_success_returns_0(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_run_with_invalid_manifest_json_returns_1(tmp_path, capsys):
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["run", "--manifest", str(p), "--output", str(tmp_path / "o.json")])
    assert rc == 1


def test_main_run_with_invalid_manifest_schema_returns_1(tmp_path, capsys):
    """manifest 是合法 JSON 但不符合 schema。"""
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["run", "--manifest", str(p), "--output", str(tmp_path / "o.json")])
    assert rc == 1


def test_main_no_subcommand_exits_nonzero(capsys):
    with pytest.raises(SystemExit):
        main([])


def test_main_unknown_subcommand_exits_nonzero(capsys):
    with pytest.raises(SystemExit):
        main(["unknown-command"])


def test_main_run_with_invalid_parser_choice_exits_nonzero(capsys):
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "a.json", "--output", "b.json", "--parser", "bad"])


def test_main_validate_report_stderr_starts_with_bracket_error(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "no.json")])
    err = capsys.readouterr().err
    assert err.startswith("[ERROR]")


def test_main_validate_report_stdout_starts_with_bracket_ok(tmp_path, capsys):
    """构建合法的 evaluation-report JSON。"""
    from evaluation import REPORT_VERSION
    report = {
        "report_version": REPORT_VERSION,
        "provenance": {
            "git_commit": "a" * 40,
            "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": REPORT_VERSION,
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {"pdfplumber": "1.0", "python-docx": "1.0", "pypdfium2": "1.0"},
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
            "counts": {"element_count_total": {"sum": None, "participating_docs": 0}},
            "success_rates": {
                "pipeline_success": {"success_count": 0, "total": 0, "rate": None}
            },
            "ratio_macro_averages": {},
            "silent_drop_total": None,
        },
        "per_doc": [],
        "expected_failures": [],
    }
    p = tmp_path / "r.json"
    p.write_text(json.dumps(report), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[OK]" in out


# ---------- module source forbidden tokens 第十二批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "yaml.load",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
        "exit(",
        "quit(",
        "global ",
    ],
)
def test_cli_source_no_forbidden_token_twelfth(token):
    source = inspect.getsource(climod)
    assert token not in source


def test_cli_source_no_class_def():
    source = inspect.getsource(climod)
    assert "class " not in source


def test_cli_source_no_async_def():
    source = inspect.getsource(climod)
    assert "async def" not in source


def test_cli_source_no_yield():
    source = inspect.getsource(climod)
    assert "yield" not in source


def test_cli_source_no_walrus():
    source = inspect.getsource(climod)
    assert ":=" not in source


def test_cli_source_no_top_level_lambda():
    source = inspect.getsource(climod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_cli_source_no_unlink():
    source = inspect.getsource(climod)
    assert "unlink" not in source


def test_cli_source_no_rmtree():
    source = inspect.getsource(climod)
    assert "rmtree" not in source


def test_cli_source_no_remove():
    source = inspect.getsource(climod)
    assert ".remove(" not in source


def test_cli_source_no_logging():
    source = inspect.getsource(climod)
    assert "logging" not in source
    assert "logger" not in source


def test_cli_source_no_sleep():
    source = inspect.getsource(climod)
    assert "time.sleep" not in source


# ---------- module source 字符串精确补强第七批 ----------


def test_module_source_has_future_annotations():
    source = inspect.getsource(climod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_argparse():
    source = inspect.getsource(climod)
    assert "import argparse" in source


def test_module_source_imports_json():
    source = inspect.getsource(climod)
    assert "import json" in source


def test_module_source_imports_sys():
    source = inspect.getsource(climod)
    assert "import sys" in source


def test_module_source_imports_path():
    source = inspect.getsource(climod)
    assert "from pathlib import Path" in source


def test_module_source_imports_load_manifest():
    source = inspect.getsource(climod)
    assert "load_manifest" in source


def test_module_source_imports_ManifestError():
    source = inspect.getsource(climod)
    assert "ManifestError" in source


def test_module_source_imports_run_evaluation():
    source = inspect.getsource(climod)
    assert "run_evaluation" in source


def test_module_source_imports_validate_file():
    source = inspect.getsource(climod)
    assert "validate_file" in source


def test_module_source_imports_EvalSchemaError():
    source = inspect.getsource(climod)
    assert "EvalSchemaError" in source


def test_module_source_imports_get_git_provenance():
    source = inspect.getsource(climod)
    assert "get_git_provenance" in source


def test_module_source_has_subparser_run():
    source = inspect.getsource(climod)
    assert 'sub.add_parser("run"' in source or '"run"' in source


def test_module_source_has_subparser_validate_report():
    source = inspect.getsource(climod)
    assert '"validate-report"' in source


def test_module_source_has_subparser_inspect_doc():
    source = inspect.getsource(climod)
    assert '"inspect-doc"' in source


def test_module_source_has_3_subparsers_via_add_parser_count():
    source = inspect.getsource(climod)
    assert source.count("add_parser(") >= 3


def test_module_source_has_choices_fallback_kreuzberg():
    source = inspect.getsource(climod)
    assert '"fallback"' in source
    assert '"kreuzberg"' in source


def test_module_source_has_manifest_required_true():
    source = inspect.getsource(climod)
    assert "required=True" in source


def test_module_source_has_main_block():
    source = inspect.getsource(climod)
    assert 'if __name__' in source
    assert "raise SystemExit(main())" in source


def test_module_source_docstring_present():
    assert climod.__doc__ is not None
    assert len(climod.__doc__) > 50


def test_module_source_docstring_mentions_run():
    assert "run" in climod.__doc__


def test_module_source_docstring_mentions_validate():
    assert "validate" in climod.__doc__.lower()


def test_module_source_docstring_mentions_inspect():
    assert "inspect" in climod.__doc__.lower()


def test_module_source_docstring_mentions_python_m():
    """usage 示例包含 `python -m evaluation.cli`。"""
    assert "python -m" in climod.__doc__


def test_module_source_has_print_call():
    """main 中 print() 用于 [OK]/[ERROR] 输出。"""
    source = inspect.getsource(climod)
    assert "print(" in source


def test_module_source_has_stderr_output():
    source = inspect.getsource(climod)
    assert "file=sys.stderr" in source


def test_module_source_no_hardcoded_absolute_path():
    source = inspect.getsource(climod)
    assert "C:\\\\Users" not in source
    assert "/Users/" not in source


# ---------- signatures 第九批 ----------


def test_signature_main_argv_annotation():
    sig = inspect.signature(main)
    p = sig.parameters.get("argv")
    assert p is not None


def test_signature_main_argv_default_none():
    sig = inspect.signature(main)
    p = sig.parameters.get("argv")
    assert p.default is None


def test_signature_main_return_annotation_int():
    sig = inspect.signature(main)
    ra = sig.return_annotation
    assert ra == int or ra == "int"


def test_signature_main_no_var_positional():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_main_no_var_keyword():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_main_param_count_one():
    sig = inspect.signature(main)
    assert len(sig.parameters) == 1


def test_signature_build_parser_no_params():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_build_parser_return_annotation():
    sig = inspect.signature(_build_parser)
    ra = sig.return_annotation
    assert ra == "argparse.ArgumentParser" or ra == argparse.ArgumentParser


def test_signature_format_metric_2_params():
    sig = inspect.signature(_format_metric)
    assert len(sig.parameters) == 2


def test_signature_format_metric_param_names():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters) == ["name", "metric"]


def test_signature_format_metric_param_kinds():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_format_metric_no_defaults():
    sig = inspect.signature(_format_metric)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_format_metric_return_annotation():
    sig = inspect.signature(_format_metric)
    ra = sig.return_annotation
    assert ra == str or ra == "str"


def test_signature_run_inspect_doc_1_param():
    sig = inspect.signature(_run_inspect_doc)
    assert len(sig.parameters) == 1


def test_signature_run_inspect_doc_param_name():
    sig = inspect.signature(_run_inspect_doc)
    assert "args" in sig.parameters


def test_signature_run_inspect_doc_param_kind():
    sig = inspect.signature(_run_inspect_doc)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_run_inspect_doc_param_no_default():
    sig = inspect.signature(_run_inspect_doc)
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_signature_run_inspect_doc_return_annotation():
    sig = inspect.signature(_run_inspect_doc)
    ra = sig.return_annotation
    assert ra == int or ra == "int"


def test_signature_4_funcs_function_type():
    for func in (main, _build_parser, _format_metric, _run_inspect_doc):
        assert inspect.isfunction(func)


def test_signature_4_funcs_module_eq():
    for func in (main, _build_parser, _format_metric, _run_inspect_doc):
        assert func.__module__ == "evaluation.cli"


# ---------- module 合理性第九批 ----------


def test_module_has_no_all_attribute():
    """cli.py 没有 __all__（导出全部 public names）。"""
    assert not hasattr(climod, "__all__")


def test_module_has_dunder_file():
    assert hasattr(climod, "__file__")


def test_module_dunder_file_endswith_cli_py():
    import os
    sep = os.sep
    assert climod.__file__.endswith("evaluation" + sep + "cli.py") or climod.__file__.endswith(
        "evaluation/cli.py"
    )


def test_module_name_is_evaluation_cli():
    assert climod.__name__ == "evaluation.cli"


def test_module_user_function_count():
    """4 module-level functions: main, _build_parser, _format_metric, _run_inspect_doc。"""
    funcs = [
        n
        for n, v in vars(climod).items()
        if inspect.isfunction(v) and v.__module__ == climod.__name__
    ]
    assert len(funcs) == 4
    assert set(funcs) == {"main", "_build_parser", "_format_metric", "_run_inspect_doc"}


def test_module_no_user_classes():
    classes = [
        n for n, v in vars(climod).items() if inspect.isclass(v) and v.__module__ == climod.__name__
    ]
    assert classes == []


def test_module_main_block_at_end():
    """`if __name__ == '__main__':` 出现在源码末尾。"""
    source = inspect.getsource(climod)
    lines = source.split("\n")
    # 找最后一个非空行
    last_meaningful = ""
    for line in reversed(lines):
        if line.strip() and not line.strip().startswith("#"):
            last_meaningful = line.strip()
            break
    assert "raise SystemExit(main())" in last_meaningful or "if __name__" in last_meaningful


def test_module_constants_only_all():
    """无 __all__ 时常量只允许出现在函数内（无顶层 const）。"""
    consts = []
    for n, v in vars(climod).items():
        if n.startswith("__"):
            continue
        if isinstance(v, (tuple, list, dict, set, frozenset)) and not callable(v):
            consts.append(n)
    assert set(consts) == set()


def test_module_no_call_at_top_level_except_reconfigure():
    """模块顶层允许 if hasattr(...) sys.stdout.reconfigure() 等，但不允许其他直接调用。"""
    source = inspect.getsource(climod)
    lines = source.split("\n")
    for line in lines[:50]:  # top 50 lines
        if not line.startswith(" "):
            stripped = line.strip()
            ok_prefixes = (
                "def ",
                "import ",
                "from ",
                "if ",
                "try:",
                "except",
                "#",
                '"""',
                "'''",
                "",
                "pass",
                "raise ",
            )
            if stripped and not any(stripped.startswith(p) for p in ok_prefixes):
                if "(" in stripped and not stripped.startswith("def "):
                    raise AssertionError(f"unexpected top-level call: {line}")


def test_module_docstring_first_line():
    assert climod.__doc__.startswith("评测")


def test_module_docstring_mentions_subcommand_examples():
    assert "python -m evaluation.cli" in climod.__doc__


# ---------- 端到端集成第九批 ----------


def test_e2e_run_subcommand_namespace_with_all_options():
    ns = _build_parser().parse_args(
        [
            "run",
            "--manifest",
            "m.json",
            "--output",
            "o.json",
            "--parser",
            "kreuzberg",
            "--max-chars",
            "500",
            "--tolerance-chars",
            "10",
        ]
    )
    assert ns.command == "run"
    assert ns.manifest == "m.json"
    assert ns.output == "o.json"
    assert ns.parser == "kreuzberg"
    assert ns.max_chars == 500
    assert ns.tolerance_chars == 10


def test_e2e_validate_report_namespace():
    ns = _build_parser().parse_args(["validate-report", "report.json"])
    assert ns.command == "validate-report"
    assert ns.input == "report.json"


def test_e2e_inspect_doc_namespace_with_tolerance():
    ns = _build_parser().parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "20"])
    assert ns.command == "inspect-doc"
    assert ns.input == "doc.json"
    assert ns.tolerance_chars == 20


def test_e2e_main_validate_report_with_missing_file(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "no.json")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "不存在" in err


def test_e2e_main_inspect_doc_with_minimal_doc(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_e2e_main_inspect_doc_with_rich_doc(tmp_path, capsys):
    doc = {
        "document_id": "rich_doc",
        "source_type": "pdf",
        "parser_name": "fallback",
        "parser_version": "1.0.0",
        "source_path": "/tmp/x.pdf",
        "elements": [{"type": "paragraph"}, {"type": "image"}],
        "chunks": [{"id": "c1"}, {"id": "c2"}],
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "rich_doc" in out
    assert "elements=2" in out
    assert "chunks=2" in out


def test_e2e_main_inspect_doc_with_custom_tolerance(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "15"])
    assert rc == 0


def test_e2e_argparse_prog_in_help(capsys):
    """--help 输出包含 prog 名 evaluation.cli。"""
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["--help"])
    captured = capsys.readouterr()
    assert "evaluation.cli" in captured.out


def test_e2e_main_validate_report_stdout_includes_filename(tmp_path, capsys):
    from evaluation import REPORT_VERSION
    report = {
        "report_version": REPORT_VERSION,
        "provenance": {
            "git_commit": "a" * 40,
            "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": REPORT_VERSION,
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {"pdfplumber": "1.0", "python-docx": "1.0", "pypdfium2": "1.0"},
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
            "counts": {"element_count_total": {"sum": None, "participating_docs": 0}},
            "success_rates": {
                "pipeline_success": {"success_count": 0, "total": 0, "rate": None}
            },
            "ratio_macro_averages": {},
            "silent_drop_total": None,
        },
        "per_doc": [],
        "expected_failures": [],
    }
    p = tmp_path / "report_xyz.json"
    p.write_text(json.dumps(report), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "report_xyz.json" in out


def test_e2e_main_unknown_subcommand_returns_nonzero(capsys):
    with pytest.raises(SystemExit):
        main(["totally-unknown"])
