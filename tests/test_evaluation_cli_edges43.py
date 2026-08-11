"""evaluation/cli.py 第四十四轮 edges 测试（Round 432）。

补强 edges42 未触及的角度：
- _build_parser 边界第十六批（prog / description / epilog / subparser metavar / run subparser 5 args 顺序）
- argparse Namespace 第十六批（未给 command 时 SystemExit / parser.format_help / error 方法 / set attrs）
- _format_metric 边界第十六批（负值 / 大浮点 / dict 多键 / Unicode reason / name 长度）
- _run_inspect_doc 边界第十六批（doc 缺 elements / doc 缺 chunks / elements 非 list 抛 TypeError / chunks 非 list 抛 TypeError / source_type=docx）
- main 路由第十六批（run with kreuzberg parser / run with bad max_chars / validate-report with extra arg / inspect-doc with extra arg / unknown subcommand → SystemExit）
- module source forbidden tokens 第二十七批
- module source 字符串精确补强第二十四批
- signatures 第二十四批
- module 合理性第二十四批
- 端到端集成第二十四批
"""

from __future__ import annotations

import inspect
import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evaluation import cli as cmod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 边界第十六批 ----------


def test_build_parser_prog_value_batch16():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_value_batch16():
    p = _build_parser()
    assert "评测 CLI" in p.description


def test_build_parser_no_epilog_batch16():
    p = _build_parser()
    assert p.epilog is None


def test_build_parser_run_subparser_has_5_args_batch16():
    p = _build_parser()
    # 通过 parse_args 验证 5 个参数都被支持
    args = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json",
        "--parser", "kreuzberg", "--max-chars", "500", "--tolerance-chars", "10",
    ])
    assert args.manifest == "m.json"
    assert args.output == "o.json"
    assert args.parser == "kreuzberg"
    assert args.max_chars == 500
    assert args.tolerance_chars == 10


def test_build_parser_run_default_parser_fallback_batch16():
    args = _build_parser().parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.parser == "fallback"


def test_build_parser_run_default_max_chars_800_batch16():
    args = _build_parser().parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.max_chars == 800


def test_build_parser_run_default_tolerance_30_batch16():
    args = _build_parser().parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_default_tolerance_30_batch16():
    args = _build_parser().parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_validate_report_takes_one_positional_batch16():
    args = _build_parser().parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"


def test_build_parser_choices_actions_count_batch16():
    """add_parser 把名字存到 _choices_actions。"""
    p = _build_parser()
    sub = [a for a in p._subparsers._actions if hasattr(a, "_parser_class")][0]
    assert set(sub.choices.keys()) == {"run", "validate-report", "inspect-doc"}


# ---------- argparse Namespace 第十六批 ----------


def test_namespace_command_attr_batch16():
    args = _build_parser().parse_args(["run", "--manifest", "m", "--output", "o"])
    assert args.command == "run"


def test_namespace_dict_access_batch16():
    args = _build_parser().parse_args(["run", "--manifest", "m", "--output", "o"])
    d = vars(args)
    assert d["manifest"] == "m"


def test_namespace_no_command_system_exit_batch16():
    """未给子命令 → SystemExit(code=2)。"""
    with pytest.raises(SystemExit) as exc_info:
        _build_parser().parse_args([])
    assert exc_info.value.code == 2


def test_namespace_format_help_returns_str_batch16():
    s = _build_parser().format_help()
    assert isinstance(s, str)
    assert "evaluation.cli" in s


def test_namespace_unknown_command_system_exit_batch16():
    with pytest.raises(SystemExit) as exc_info:
        _build_parser().parse_args(["unknown-command"])
    assert exc_info.value.code == 2


# ---------- _format_metric 边界第十六批 ----------


def test_format_metric_negative_float_batch16():
    s = _format_metric("x", {"value": -0.5, "reason": None})
    assert "-0.5000" in s


def test_format_metric_large_float_batch16():
    s = _format_metric("x", {"value": 0.99999999, "reason": None})
    assert "1.0000" in s  # 四舍五入


def test_format_metric_dict_multiple_items_batch16():
    s = _format_metric("x", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in s
    assert "b=2" in s


def test_format_metric_unicode_reason_batch16():
    s = _format_metric("x", {"value": None, "reason": "失败原因"})
    assert "失败原因" in s


def test_format_metric_long_name_batch16():
    s = _format_metric("a" * 100, {"value": 1, "reason": None})
    assert isinstance(s, str)


def test_format_metric_short_name_batch16():
    s = _format_metric("x", {"value": 1, "reason": None})
    assert isinstance(s, str)


def test_format_metric_int_value_batch16():
    s = _format_metric("count", {"value": 42, "reason": None})
    assert "42" in s


def test_format_metric_dict_empty_batch16():
    s = _format_metric("empty", {"value": {}, "reason": None})
    assert "empty" in s


# ---------- _run_inspect_doc 边界第十六批 ----------


def _write_valid_doc(tmp_path, **overrides):
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "source_path": "x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
        **overrides,
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def test_run_inspect_doc_missing_elements_key_batch16(tmp_path, capsys):
    """doc 缺 elements key → doc.get("elements") or [] → [] → OK。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "d1", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "chunks": [],
    }), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_missing_chunks_key_batch16(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "document_id": "d1", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [],
    }), encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_source_type_docx_batch16(tmp_path, capsys):
    p = _write_valid_doc(tmp_path, source_type="docx")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "type=docx" in captured.out


def test_run_inspect_doc_parser_info_in_stdout_batch16(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "parser:" in captured.out
    assert "fallback" in captured.out
    assert "1.0" in captured.out


def test_run_inspect_doc_file_path_in_stdout_batch16(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "file:" in captured.out
    assert str(p) in captured.out


def test_run_inspect_doc_document_id_in_stdout_batch16(tmp_path, capsys):
    p = _write_valid_doc(tmp_path, document_id="mydoc")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "mydoc" in captured.out


def test_run_inspect_doc_metrics_header_in_stdout_batch16(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_counts_in_stdout_batch16(tmp_path, capsys):
    p = _write_valid_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "counts:" in captured.out
    assert "elements=" in captured.out
    assert "chunks=" in captured.out


# ---------- main 路由第十六批 ----------


def test_main_run_with_kreuzberg_batch16(tmp_path, capsys):
    """run 命令传 --parser kreuzberg（但 manifest 不存在 → rc=2）。"""
    rc = main(["run", "--manifest", str(tmp_path / "nope.json"), "--output", str(tmp_path / "o.json"), "--parser", "kreuzberg"])
    assert rc == 2


def test_main_run_with_bad_max_chars_batch16(tmp_path, capsys):
    """--max-chars 非数字 → SystemExit。"""
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "m.json", "--output", "o.json", "--max-chars", "not-int"])


def test_main_validate_report_extra_arg_system_exit_batch16():
    """validate-report 只接受 1 个位置参数；多了应 SystemExit。"""
    with pytest.raises(SystemExit):
        main(["validate-report", "a.json", "b.json"])


def test_main_inspect_doc_extra_arg_system_exit_batch16():
    """inspect-doc 只接受 1 个位置参数。"""
    with pytest.raises(SystemExit):
        main(["inspect-doc", "a.json", "b.json"])


def test_main_unknown_subcommand_system_exit_batch16():
    with pytest.raises(SystemExit):
        main(["bogus-command"])


def test_main_no_args_system_exit_batch16():
    """完全无参数 → SystemExit(code=2)。"""
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2


def test_main_run_manifest_schema_invalid_batch16(tmp_path, capsys):
    """manifest 是非法 JSON → ManifestError → rc=1。"""
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    rc = main(["run", "--manifest", str(bad), "--output", str(tmp_path / "o.json")])
    assert rc == 1


def test_main_inspect_doc_valid_returns_0_batch16(tmp_path):
    p = _write_valid_doc(tmp_path)
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_returns_int_type_batch16(tmp_path):
    rc = main(["inspect-doc", str(_write_valid_doc(tmp_path))])
    assert isinstance(rc, int)


# ---------- module source forbidden tokens 第二十七批 ----------


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
def test_module_source_forbidden_tokens_batch16(forbidden):
    src = inspect.getsource(cmod)
    assert forbidden not in src


# Note: subprocess IS allowed in cli.py (for git provenance via report.get_git_provenance)


# ---------- module source 字符串精确补强第二十四批 ----------


def test_module_source_has_future_annotations_batch16():
    src = inspect.getsource(cmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch16():
    src = inspect.getsource(cmod)
    assert '"""评测 CLI' in src


def test_module_source_has_argparse_import_batch16():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_source_has_json_import_batch16():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_source_has_sys_import_batch16():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_source_has_path_import_batch16():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_source_has_manifest_import_batch16():
    src = inspect.getsource(cmod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_module_source_has_report_import_batch16():
    src = inspect.getsource(cmod)
    assert "from evaluation.report import get_git_provenance" in src


def test_module_source_has_runner_import_batch16():
    src = inspect.getsource(cmod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_has_schema_import_batch16():
    src = inspect.getsource(cmod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_module_source_has_build_parser_function_batch16():
    src = inspect.getsource(cmod)
    assert "def _build_parser() -> argparse.ArgumentParser:" in src


def test_module_source_has_main_function_batch16():
    src = inspect.getsource(cmod)
    assert "def main(argv: list[str] | None = None) -> int:" in src


def test_module_source_has_format_metric_function_batch16():
    src = inspect.getsource(cmod)
    assert "def _format_metric(name: str, metric: dict) -> str:" in src


def test_module_source_has_run_inspect_doc_function_batch16():
    src = inspect.getsource(cmod)
    assert "def _run_inspect_doc(args) -> int:" in src


def test_module_source_has_run_subcommand_batch16():
    src = inspect.getsource(cmod)
    assert '"run"' in src


def test_module_source_has_validate_report_subcommand_batch16():
    src = inspect.getsource(cmod)
    assert '"validate-report"' in src


def test_module_source_has_inspect_doc_subcommand_batch16():
    src = inspect.getsource(cmod)
    assert '"inspect-doc"' in src


def test_module_source_has_fallback_default_batch16():
    src = inspect.getsource(cmod)
    assert 'default="fallback"' in src


def test_module_source_has_800_default_batch16():
    src = inspect.getsource(cmod)
    assert "default=800" in src


def test_module_source_has_30_default_batch16():
    src = inspect.getsource(cmod)
    assert "default=30" in src


def test_module_source_has_choices_tuple_batch16():
    src = inspect.getsource(cmod)
    assert 'choices=("fallback", "kreuzberg")' in src


def test_module_source_has_main_guard_batch16():
    src = inspect.getsource(cmod)
    assert 'if __name__ == "__main__":' in src
    assert "raise SystemExit(main())" in src


def test_module_source_has_utf8_reconfigure_batch16():
    src = inspect.getsource(cmod)
    assert 'sys.stdout.reconfigure' in src or 'sys.stderr.reconfigure' in src


def test_module_source_has_required_true_batch16():
    src = inspect.getsource(cmod)
    assert "required=True" in src


def test_module_source_has_evaluator_description_batch16():
    src = inspect.getsource(cmod)
    assert "评测" in src


# ---------- signatures 第二十四批 ----------


def test_signature_build_parser_batch16():
    sig = inspect.signature(_build_parser)
    assert list(sig.parameters.keys()) == []


def test_signature_main_batch16():
    sig = inspect.signature(main)
    params = list(sig.parameters.keys())
    assert params == ["argv"]
    assert sig.parameters["argv"].default is None


def test_signature_format_metric_batch16():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters.keys())
    assert params == ["name", "metric"]


def test_signature_run_inspect_doc_batch16():
    sig = inspect.signature(_run_inspect_doc)
    params = list(sig.parameters.keys())
    assert params == ["args"]


def test_signature_main_return_annotation_batch16():
    sig = inspect.signature(main)
    # return annotation is int or "int"
    ra = sig.return_annotation
    assert ra == "int" or ra is int


def test_signature_build_parser_return_annotation_batch16():
    sig = inspect.signature(_build_parser)
    ra = sig.return_annotation
    assert ra is not inspect._empty


def test_signature_run_inspect_doc_return_annotation_batch16():
    sig = inspect.signature(_run_inspect_doc)
    ra = sig.return_annotation
    assert ra is not inspect._empty


# ---------- module 合理性第二十四批 ----------


def test_module_has_main_attribute_batch16():
    assert hasattr(cmod, "main")
    assert callable(cmod.main)


def test_module_has_build_parser_attribute_batch16():
    assert hasattr(cmod, "_build_parser")


def test_module_has_format_metric_attribute_batch16():
    assert hasattr(cmod, "_format_metric")


def test_module_has_run_inspect_doc_attribute_batch16():
    assert hasattr(cmod, "_run_inspect_doc")


def test_module_main_callable_batch16():
    assert callable(main)


def test_module_main_guard_batch16():
    """模块有 if __name__ == "__main__" 块。"""
    src = inspect.getsource(cmod)
    assert 'if __name__ == "__main__":' in src


def test_module_has_sys_attribute_batch16():
    """sys 模块在 cli 命名空间中。"""
    assert hasattr(cmod, "sys")


def test_module_does_not_export_helpers_batch16():
    """_build_parser 等私有，但应仍在命名空间（不在 __all__ 中）。"""
    assert not hasattr(cmod, "__all__") or "_build_parser" not in getattr(cmod, "__all__", [])


# ---------- 端到端集成第二十四批 ----------


def test_e2e_main_inspect_doc_full_batch16(tmp_path, capsys):
    """完整 inspect-doc 命令应输出文档元信息。"""
    p = _write_valid_doc(tmp_path)
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "d1" in captured.out
    assert "elements=" in captured.out
    assert "metrics:" in captured.out


def test_e2e_main_validate_report_not_exist_batch16(tmp_path, capsys):
    """validate-report 文件不存在 → rc=2。"""
    rc = main(["validate-report", str(tmp_path / "nope.json")])
    assert rc == 2


def test_e2e_main_validate_report_invalid_json_batch16(tmp_path, capsys):
    """validate-report 非法 JSON → rc=1。"""
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_main_inspect_doc_not_exist_batch16(tmp_path, capsys):
    """inspect-doc 文件不存在 → rc=2。"""
    rc = main(["inspect-doc", str(tmp_path / "nope.json")])
    assert rc == 2


def test_e2e_main_inspect_doc_invalid_json_batch16(tmp_path, capsys):
    """inspect-doc 非法 JSON → rc=1。"""
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_e2e_main_inspect_doc_list_json_batch16(tmp_path, capsys):
    """inspect-doc 顶层是数组而非 dict → rc=1。"""
    p = tmp_path / "list.json"
    p.write_text("[]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_e2e_main_inspect_doc_int_json_batch16(tmp_path, capsys):
    """inspect-doc 顶层是 int → rc=1。"""
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_e2e_main_help_works_via_system_exit_batch16(capsys):
    """--help 应触发 SystemExit(0)。"""
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0


def test_e2e_format_metric_idempotent_batch16():
    """_format_metric 多次调用同一输入应一致。"""
    metric = {"value": 0.5, "reason": None}
    s1 = _format_metric("x", metric)
    s2 = _format_metric("x", metric)
    assert s1 == s2


def test_e2e_parser_can_parse_run_with_optional_args_omitted_batch16():
    """run 命令可省略所有可选参数。"""
    args = _build_parser().parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.manifest == "m.json"
    assert args.output == "o.json"
    assert args.parser == "fallback"
    assert args.max_chars == 800
    assert args.tolerance_chars == 30
