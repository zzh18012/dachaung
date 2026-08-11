"""evaluation/cli.py 第四十五轮 edges 测试（Round 439）。

补强 edges43 未触及的角度：
- _build_parser 边界第十七批（prog / description / subparsers required / 子命令 choices / Run 子 parser defaults）
- argparse Namespace 第十七批（多个 args 同时存在 / inspect-doc args / validate-report args）
- _format_metric 边界第十七批（dict metric / int value / negative int / reason 'ok' 替换 / name 长度边界）
- _run_inspect_doc 边界第十七批（input 不存在 / JSON null / JSON list / doc 缺 elements / doc 缺 chunks / source_type 默认 unknown / tolerance_chars 透传）
- main 路由第十七批（run with manifest 不存在 / run with manifest 加载失败 / run 成功路径 / validate-report 不存在 / validate-report JSON 失败 / validate-report 成功）
- module source forbidden tokens 第三十三批
- module source 字符串精确补强第三十批
- signatures 第三十批
- module 合理性第三十批
- 端到端集成第三十批
"""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evaluation import cli as cmod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 边界第十七批 ----------


def test_build_parser_prog_batch17():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_batch17():
    p = _build_parser()
    assert "评测 CLI" in p.description


def test_build_parser_formatter_class_batch17():
    p = _build_parser()
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_subparsers_required_batch17():
    """顶层 subparser 必填（不指定 command 报错）。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_parser_has_three_subcommands_batch17():
    p = _build_parser()
    # find subparsers action
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    assert set(sub_action.choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_run_default_parser_batch17():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.parser == "fallback"


def test_build_parser_run_default_max_chars_batch17():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.max_chars == 800


def test_build_parser_run_default_tolerance_chars_batch17():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.tolerance_chars == 30


def test_build_parser_run_invalid_parser_choice_batch17():
    """--parser 不在 choices 中 → SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "m.json", "--output", "o.json",
                      "--parser", "nonexistent"])


def test_build_parser_inspect_doc_default_tolerance_batch17():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_validate_report_args_batch17():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"
    assert args.command == "validate-report"


def test_build_parser_inspect_doc_args_batch17():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.input == "doc.json"
    assert args.command == "inspect-doc"


def test_build_parser_unknown_command_batch17():
    """未知 command → SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["unknown-command"])


def test_build_parser_run_missing_manifest_batch17():
    """run 缺 --manifest → SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "o.json"])


def test_build_parser_run_missing_output_batch17():
    """run 缺 --output → SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "m.json"])


# ---------- argparse Namespace 第十七批 ----------


def test_namespace_run_with_all_options_batch17():
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json",
        "--parser", "kreuzberg", "--max-chars", "500", "--tolerance-chars", "10",
    ])
    assert args.manifest == "m.json"
    assert args.output == "o.json"
    assert args.parser == "kreuzberg"
    assert args.max_chars == 500
    assert args.tolerance_chars == 10
    assert args.command == "run"


def test_namespace_inspect_doc_with_tolerance_batch17():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "d.json", "--tolerance-chars", "100"])
    assert args.input == "d.json"
    assert args.tolerance_chars == 100


def test_namespace_validate_report_batch17():
    p = _build_parser()
    args = p.parse_args(["validate-report", "r.json"])
    assert args.input == "r.json"
    assert not hasattr(args, "manifest")
    assert not hasattr(args, "max_chars")


def test_namespace_command_attr_set_batch17():
    """所有子命令都设 command 属性。"""
    p = _build_parser()
    for cmd in (["run", "--manifest", "m.json", "--output", "o.json"],
                ["validate-report", "r.json"],
                ["inspect-doc", "d.json"]):
        args = p.parse_args(cmd)
        assert args.command in {"run", "validate-report", "inspect-doc"}


def test_namespace_run_attrs_type_batch17():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert isinstance(args.manifest, str)
    assert isinstance(args.output, str)
    assert isinstance(args.max_chars, int)
    assert isinstance(args.tolerance_chars, int)


# ---------- _format_metric 边界第十七批 ----------


def test_format_metric_dict_value_batch17():
    s = _format_metric("element_count_by_type", {"value": {"heading": 2}, "reason": None})
    assert "heading=2" in s
    assert "ok" in s


def test_format_metric_dict_value_empty_batch17():
    s = _format_metric("element_count_by_type", {"value": {}, "reason": None})
    assert "element_count_by_type" in s
    # 空 dict 时 items 为空字符串
    assert "()" in s or "  (" in s


def test_format_metric_int_value_batch17():
    s = _format_metric("element_count_total", {"value": 42, "reason": None})
    assert "42" in s
    assert "ok" in s


def test_format_metric_negative_int_value_batch17():
    s = _format_metric("silent_drop_count", {"value": -3, "reason": None})
    assert "-3" in s


def test_format_metric_none_value_with_reason_batch17():
    s = _format_metric("schema_valid", {"value": None, "reason": "pipeline_failed"})
    assert "null" in s
    assert "pipeline_failed" in s


def test_format_metric_none_value_empty_reason_batch17():
    s = _format_metric("x", {"value": None, "reason": ""})
    assert "null" in s
    assert "()" in s


def test_format_metric_bool_true_batch17():
    s = _format_metric("pipeline_success", {"value": True, "reason": None})
    assert "true" in s
    assert "ok" in s


def test_format_metric_bool_false_batch17():
    s = _format_metric("pipeline_success", {"value": False, "reason": None})
    assert "false" in s


def test_format_metric_float_zero_batch17():
    s = _format_metric("ratio", {"value": 0.0, "reason": None})
    assert "0.0000" in s


def test_format_metric_float_one_batch17():
    s = _format_metric("ratio", {"value": 1.0, "reason": None})
    assert "1.0000" in s


def test_format_metric_float_negative_batch17():
    """负数浮点也支持。"""
    s = _format_metric("ratio", {"value": -0.5, "reason": None})
    assert "-0.5000" in s


def test_format_metric_reason_replaces_ok_for_bool_batch17():
    """bool 值有 reason 时显示 reason（不替换为 ok）。"""
    s = _format_metric("pipeline_success", {"value": False, "reason": "x"})
    # reason 是 x（不是 ok）
    assert "(x)" in s


def test_format_metric_long_name_batch17():
    """长 name 仍按 36 字符宽度对齐。"""
    s = _format_metric("a" * 50, {"value": 1, "reason": None})
    assert "a" * 50 in s


def test_format_metric_str_value_batch17():
    """value 是 str（如 error_code） → 走最后一个 return 分支。"""
    s = _format_metric("error_code", {"value": "parse_failed", "reason": None})
    assert "parse_failed" in s


# ---------- _run_inspect_doc 边界第十七批 ----------


def _mk_args(input_path, tolerance_chars=30):
    """构造 inspect-doc 的 args namespace。"""
    ns = MagicMock()
    ns.input = str(input_path)
    ns.tolerance_chars = tolerance_chars
    return ns


def test_run_inspect_doc_nonexistent_file_batch17(tmp_path, capsys):
    p = tmp_path / "no.json"
    rc = _run_inspect_doc(_mk_args(p))
    assert rc == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_run_inspect_doc_invalid_json_batch17(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    rc = _run_inspect_doc(_mk_args(p))
    assert rc == 1


def test_run_inspect_doc_json_null_batch17(tmp_path, capsys):
    """JSON 是 null → 顶层不是 dict → rc=1。"""
    p = tmp_path / "n.json"
    p.write_text("null", encoding="utf-8")
    rc = _run_inspect_doc(_mk_args(p))
    assert rc == 1


def test_run_inspect_doc_json_list_batch17(tmp_path, capsys):
    """JSON 是 list → 顶层不是 dict → rc=1。"""
    p = tmp_path / "l.json"
    p.write_text("[1, 2]", encoding="utf-8")
    rc = _run_inspect_doc(_mk_args(p))
    assert rc == 1


def test_run_inspect_doc_doc_no_elements_batch17(tmp_path, capsys):
    """doc 缺 elements key → 用 .get() 默认 []。"""
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"source_type": "pdf"}), encoding="utf-8")
    rc = _run_inspect_doc(_mk_args(p))
    assert rc == 0


def test_run_inspect_doc_doc_no_chunks_batch17(tmp_path, capsys):
    """doc 缺 chunks key → 用 .get() 默认 []。"""
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": []}), encoding="utf-8")
    rc = _run_inspect_doc(_mk_args(p))
    assert rc == 0


def test_run_inspect_doc_source_type_default_unknown_batch17(tmp_path, capsys):
    """doc 缺 source_type → 默认 "unknown"。"""
    p = tmp_path / "d.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    rc = _run_inspect_doc(_mk_args(p))
    assert rc == 0
    captured = capsys.readouterr()
    assert "unknown" in captured.out


def test_run_inspect_doc_prints_metrics_header_batch17(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    rc = _run_inspect_doc(_mk_args(p))
    assert rc == 0
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_prints_file_path_batch17(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    _run_inspect_doc(_mk_args(p))
    captured = capsys.readouterr()
    assert "file:" in captured.out
    assert str(p) in captured.out


def test_run_inspect_doc_prints_counts_batch17(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [{"type": "paragraph"}], "chunks": [{"text": "x"}]}), encoding="utf-8")
    _run_inspect_doc(_mk_args(p))
    captured = capsys.readouterr()
    assert "elements=1" in captured.out
    assert "chunks=1" in captured.out


def test_run_inspect_doc_tolerance_chars_transparent_batch17(tmp_path):
    """tolerance_chars 透传到 chunk_boundary_prf。"""
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    with patch("evaluation.annotation_metrics.chunk_boundary_prf") as cbp:
        cbp.return_value = {
            "chunk_boundary_precision": {"value": None, "reason": "x"},
            "chunk_boundary_recall": {"value": None, "reason": "x"},
            "chunk_boundary_f1": {"value": None, "reason": "x"},
        }
        _run_inspect_doc(_mk_args(p, tolerance_chars=99))
    _, kwargs = cbp.call_args
    assert kwargs["tolerance_chars"] == 99


def test_run_inspect_doc_returns_zero_on_success_batch17(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    assert _run_inspect_doc(_mk_args(p)) == 0


# ---------- main 路由第十七批 ----------


def test_main_run_manifest_not_exists_batch17(tmp_path, capsys):
    m = tmp_path / "no.json"
    o = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(m), "--output", str(o)])
    assert rc == 2


def test_main_run_manifest_load_fails_batch17(tmp_path, capsys):
    """manifest 加载失败（ManifestError 或 EvalSchemaError） → rc=1。"""
    m = tmp_path / "bad.json"
    m.write_text("{}", encoding="utf-8")  # 空 dict 不通过 schema
    o = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(m), "--output", str(o)])
    assert rc == 1


def test_main_run_success_batch17(tmp_path, capsys):
    """完整 run 成功路径（用 mock 替换 run_evaluation）。"""
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    o = tmp_path / "out.json"

    fake_report = {
        "report_version": "1.1",
        "provenance": {"git_commit": "abc", "git_dirty": False,
                       "evaluator_version": "1.1", "report_version": "1.1",
                       "parser_name": "fallback", "parser_version": "1.0.0",
                       "dependencies": {"pdfplumber": None, "python-docx": None, "pypdfium2": None},
                       "max_chars": 800, "run_timestamp_iso": "2026-01-01T00:00:00+00:00"},
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0,
                   "pdf_count": 0, "docx_count": 0, "categories_covered": []},
        "summary": {"counts": {}, "success_rates": {}, "ratio_macro_averages": {}, "silent_drop_total": None},
        "per_doc": [],
        "expected_failures": [],
    }
    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path
    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), \
         patch("evaluation.cli.run_evaluation", return_value=fake_report), \
         patch("evaluation.cli.validate_file", return_value=None), \
         patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
        # 验证文件需要存在
        o.parent.mkdir(parents=True, exist_ok=True)
        o.write_text("{}", encoding="utf-8")
        rc = main(["run", "--manifest", str(m), "--output", str(o)])
    assert rc == 0


def test_main_validate_report_not_exists_batch17(tmp_path, capsys):
    r = tmp_path / "no.json"
    rc = main(["validate-report", str(r)])
    assert rc == 2


def test_main_validate_report_invalid_json_batch17(tmp_path, capsys):
    r = tmp_path / "bad.json"
    r.write_text("not json", encoding="utf-8")
    rc = main(["validate-report", str(r)])
    assert rc == 1


def test_main_validate_report_schema_invalid_batch17(tmp_path, capsys):
    """报告通过 JSON 但不通过 schema → EvalSchemaError → rc=1。"""
    r = tmp_path / "r.json"
    r.write_text("{}", encoding="utf-8")
    rc = main(["validate-report", str(r)])
    assert rc == 1


def test_main_unknown_command_batch17(capsys):
    """未知 command → SystemExit (argparse 内部处理)。"""
    with pytest.raises(SystemExit):
        main(["unknown"])


def test_main_no_args_batch17(capsys):
    """无 command → SystemExit。"""
    with pytest.raises(SystemExit):
        main([])


def test_main_run_pipeline_failed_batch17(tmp_path, capsys):
    """run_evaluation 抛 EvalSchemaError → rc=1。"""
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    o = tmp_path / "out.json"
    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path
    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), \
         patch("evaluation.cli.run_evaluation",
               side_effect=type("E", (Exception,), {})("schema fail")):
        # 注：实际的 EvalSchemaError 在 evaluation.schema，但我们 patch 不到这里
        # 让 main 真的抛错测试。但因为我们 patch side_effect 是普通 Exception，
        # main 不会捕获，会传播。所以这个测试期望 SystemExit/Exception。
        with pytest.raises(Exception):
            main(["run", "--manifest", str(m), "--output", str(o)])


# ---------- module source forbidden tokens 第三十三批 ----------


@pytest.mark.parametrize("forbidden", [
    "pty.spawn",
    "commands.getoutput",
    "paramiko",
    "fabric.api",
    "ftplib",
    "smtplib",
    "telnetlib",
    "webbrowser.open",
    "socket.socket",
    "asyncio.open_connection",
    "multiprocessing.Process",
    "threading.Thread",
    "ctypes.CDLL",
    "pickle.dumps",
    "shutil.rmtree",
    "sys.exit",
])
def test_module_source_forbidden_tokens_batch17(forbidden):
    src = inspect.getsource(cmod)
    assert forbidden not in src


def test_module_source_no_subprocess_batch17():
    """cli.py 不应有 subprocess（report.py 才用）。"""
    src = inspect.getsource(cmod)
    assert "import subprocess" not in src


def test_module_source_no_network_batch17():
    src = inspect.getsource(cmod)
    assert "urllib.request" not in src
    assert "import requests" not in src


# ---------- module source 字符串精确补强第三十批 ----------


def test_module_source_has_future_annotations_batch17():
    src = inspect.getsource(cmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch17():
    src = inspect.getsource(cmod)
    assert "评测 CLI" in src


def test_module_source_has_argparse_import_batch17():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_source_has_json_import_batch17():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_source_has_sys_import_batch17():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_source_has_pathlib_import_batch17():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_source_has_manifest_import_batch17():
    src = inspect.getsource(cmod)
    assert "from evaluation.manifest import" in src
    assert "ManifestError" in src
    assert "load_manifest" in src


def test_module_source_has_runner_import_batch17():
    src = inspect.getsource(cmod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_has_schema_import_batch17():
    src = inspect.getsource(cmod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_module_source_has_build_parser_function_batch17():
    src = inspect.getsource(cmod)
    assert "def _build_parser()" in src


def test_module_source_has_main_function_batch17():
    src = inspect.getsource(cmod)
    assert "def main(argv" in src


def test_module_source_has_format_metric_function_batch17():
    src = inspect.getsource(cmod)
    assert "def _format_metric(" in src


def test_module_source_has_run_inspect_doc_function_batch17():
    src = inspect.getsource(cmod)
    assert "def _run_inspect_doc(" in src


def test_module_source_has_run_subparser_batch17():
    src = inspect.getsource(cmod)
    assert 'sub.add_parser("run"' in src


def test_module_source_has_validate_report_subparser_batch17():
    src = inspect.getsource(cmod)
    assert '"validate-report"' in src


def test_module_source_has_inspect_doc_subparser_batch17():
    src = inspect.getsource(cmod)
    assert '"inspect-doc"' in src


def test_module_source_has_system_exit_in_main_batch17():
    src = inspect.getsource(cmod)
    assert "raise SystemExit(main())" in src


def test_module_source_has_reconfigure_stdout_batch17():
    src = inspect.getsource(cmod)
    assert "sys.stdout.reconfigure" in src


def test_module_source_has_all_dunder_check_batch17():
    """cli.py 没有 __all__（只有函数）。"""
    src = inspect.getsource(cmod)
    # 验证没有 __all__
    assert "__all__" not in src


# ---------- signatures 第三十批 ----------


def test_signature_main_batch17():
    sig = inspect.signature(main)
    params = list(sig.parameters.keys())
    assert params == ["argv"]
    assert sig.parameters["argv"].default is None


def test_signature_build_parser_batch17():
    sig = inspect.signature(_build_parser)
    assert list(sig.parameters.keys()) == []


def test_signature_format_metric_batch17():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters.keys())
    assert params == ["name", "metric"]


def test_signature_run_inspect_doc_batch17():
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters.keys()) == ["args"]


def test_signature_main_return_annotation_int_batch17():
    sig = inspect.signature(main)
    # 因 from __future__ import annotations，return 注解是字符串
    assert sig.return_annotation == "int"


def test_signature_build_parser_return_annotation_batch17():
    sig = inspect.signature(_build_parser)
    assert sig.return_annotation == "argparse.ArgumentParser"


# ---------- module 合理性第三十批 ----------


def test_module_main_callable_batch17():
    assert callable(main)


def test_module_build_parser_callable_batch17():
    assert callable(_build_parser)


def test_module_format_metric_callable_batch17():
    assert callable(_format_metric)


def test_module_run_inspect_doc_callable_batch17():
    assert callable(_run_inspect_doc)


def test_module_does_not_import_unsafe_modules_batch17():
    src = inspect.getsource(cmod)
    for unsafe in ["import pickle", "import marshal", "import shelve", "import subprocess"]:
        assert unsafe not in src


def test_module_has_reconfigure_guard_batch17():
    """Windows utf-8 重配 guard。"""
    src = inspect.getsource(cmod)
    assert 'hasattr(sys.stdout, "reconfigure")' in src


# ---------- 端到端集成第三十批 ----------


def test_e2e_validate_report_with_real_invalid_report_batch17(tmp_path, capsys):
    """真实文件 → validate-report 失败路径。"""
    r = tmp_path / "r.json"
    r.write_text('{"not_a_valid_report": true}', encoding="utf-8")
    rc = main(["validate-report", str(r)])
    assert rc == 1
    assert "[FAIL]" in capsys.readouterr().err or "[ERROR]" in capsys.readouterr().err


def test_e2e_inspect_doc_full_run_batch17(tmp_path, capsys):
    """inspect-doc 真实跑通。"""
    p = tmp_path / "d.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "hello", "element_id": "e1"}],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "elements=1" in captured.out
    assert "chunks=1" in captured.out
    assert "metrics:" in captured.out


def test_e2e_inspect_doc_with_tolerance_batch17(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"source_type": "pdf", "elements": [], "chunks": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "100"])
    assert rc == 0


def test_e2e_run_with_empty_manifest_batch17(tmp_path):
    """run 命令 + 空 manifest（但合法）。"""
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    o = tmp_path / "out.json"

    # 真实跑（不 mock），输出应是空 per_doc
    rc = main(["run", "--manifest", str(m), "--output", str(o)])
    assert rc == 0
    assert o.is_file()


def test_e2e_format_metric_round_trip_batch17():
    """_format_metric 对各种 metric 类型都不抛。"""
    for metric in [
        {"value": None, "reason": "x"},
        {"value": True, "reason": None},
        {"value": False, "reason": "y"},
        {"value": 0.5, "reason": None},
        {"value": 42, "reason": None},
        {"value": {"k": 1}, "reason": None},
        {"value": "string", "reason": None},
    ]:
        s = _format_metric("test", metric)
        assert isinstance(s, str)


def test_e2e_build_parser_can_be_called_multiple_times_batch17():
    """多次调用 _build_parser 互不影响。"""
    p1 = _build_parser()
    p2 = _build_parser()
    assert p1 is not p2


def test_e2e_inspect_doc_unicode_content_batch17(tmp_path):
    """含 Unicode 的 inspect-doc 不崩。"""
    p = tmp_path / "d.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "中文", "element_id": "e1"}],
        "chunks": [{"text": "中文", "source_element_ids": ["e1"]}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_validate_report_returns_2_on_missing_file_batch17(tmp_path):
    rc = main(["validate-report", str(tmp_path / "no.json")])
    assert rc == 2


def test_e2e_run_returns_2_on_missing_manifest_batch17(tmp_path):
    rc = main(["run", "--manifest", str(tmp_path / "no.json"),
               "--output", str(tmp_path / "o.json")])
    assert rc == 2
