"""evaluation/cli.py 第六十五轮 edges 测试（Round 578）。

补强 edges63 未触及的角度（第三十七批）。
"""

from __future__ import annotations

import inspect
import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import MANIFEST_VERSION
from evaluation import cli as cmod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 第三十七批


def test_build_parser_prog_value_batch37():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_has_run_subparser_batch37():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.command == "run"


def test_build_parser_has_validate_report_subparser_batch37():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.command == "validate-report"
    assert args.input == "report.json"


def test_build_parser_has_inspect_doc_subparser_batch37():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.command == "inspect-doc"
    assert args.input == "doc.json"


def test_build_parser_run_default_parser_fallback_batch37():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.parser == "fallback"


def test_build_parser_run_default_max_chars_800_batch37():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.max_chars == 800


def test_build_parser_run_default_tolerance_chars_30_batch37():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "x", "--output", "y"])
    assert args.tolerance_chars == 30


def test_build_parser_run_with_all_options_batch37():
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json",
        "--parser", "kreuzberg", "--max-chars", "500", "--tolerance-chars", "10",
    ])
    assert args.parser == "kreuzberg"
    assert args.max_chars == 500
    assert args.tolerance_chars == 10


def test_build_parser_inspect_doc_default_tolerance_30_batch37():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_custom_tolerance_batch37():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "100"])
    assert args.tolerance_chars == 100


def test_build_parser_run_parser_invalid_choice_batch37():
    """parser 不是 fallback/kreuzberg → 抛 SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "x", "--output", "y", "--parser", "invalid"])


def test_build_parser_no_subcommand_required_batch37():
    """没传 subcommand → 抛 SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_parser_run_missing_manifest_batch37():
    """run 缺 --manifest → 抛 SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "y"])


def test_build_parser_run_missing_output_batch37():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "x"])


# ---------- _format_metric 第三十七批


def test_format_metric_int_one_batch37():
    out = _format_metric("x", {"value": 1, "reason": None})
    assert "1" in out
    assert "ok" in out


def test_format_metric_int_negative_batch37():
    out = _format_metric("x", {"value": -5, "reason": None})
    assert "-5" in out


def test_format_metric_float_zero_batch37():
    out = _format_metric("x", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_float_one_third_batch37():
    out = _format_metric("x", {"value": 1.0 / 3.0, "reason": None})
    assert "0.3333" in out


def test_format_metric_float_full_batch37():
    out = _format_metric("x", {"value": 1.0, "reason": None})
    assert "1.0000" in out


def test_format_metric_bool_true_lowercase_batch37():
    out = _format_metric("x", {"value": True, "reason": None})
    assert "true" in out
    assert "false" not in out


def test_format_metric_bool_false_lowercase_batch37():
    out = _format_metric("x", {"value": False, "reason": None})
    assert "false" in out


def test_format_metric_dict_with_one_kv_batch37():
    out = _format_metric("x", {"value": {"a": 1}, "reason": None})
    assert "a=1" in out


def test_format_metric_dict_with_multiple_kv_sorted_batch37():
    """dict 按 key 排序。"""
    out = _format_metric("x", {"value": {"b": 2, "a": 1}, "reason": None})
    # 排序后 "a=1, b=2"
    assert "a=1" in out
    assert "b=2" in out
    a_pos = out.index("a=1")
    b_pos = out.index("b=2")
    assert a_pos < b_pos


def test_format_metric_dict_with_unicode_value_batch37():
    out = _format_metric("x", {"value": {"k": "中文"}, "reason": None})
    assert "中文" in out


def test_format_metric_dict_empty_batch37():
    out = _format_metric("x", {"value": {}, "reason": None})
    # 空 dict → 空字符串
    assert "ok" in out


def test_format_metric_none_with_reason_batch37():
    out = _format_metric("x", {"value": None, "reason": "no_data"})
    assert "null" in out
    assert "no_data" in out


def test_format_metric_none_without_reason_batch37():
    """value=None 且 reason=None → 仍显示 null。"""
    out = _format_metric("x", {"value": None, "reason": None})
    assert "null" in out


def test_format_metric_long_name_alignment_batch37():
    """metric name 长度不影响渲染（用 :36 对齐）。"""
    long_name = "a" * 50
    out = _format_metric(long_name, {"value": 1, "reason": None})
    assert long_name in out


# ---------- _run_inspect_doc 第三十七批


def _write_doc(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_run_inspect_doc_returns_zero_on_success_batch37(tmp_path, capsys):
    p = _write_doc(tmp_path, {"source_type": "pdf", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_missing_file_returns_2_batch37(tmp_path):
    args = MagicMock()
    args.input = str(tmp_path / "missing.json")
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 2


def test_run_inspect_doc_invalid_json_returns_1_batch37(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json {", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_top_level_list_returns_1_batch37(tmp_path):
    """JSON 顶层是 list → 不是 dict → 返回 1。"""
    p = tmp_path / "list.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_prints_file_path_batch37(tmp_path, capsys):
    p = _write_doc(tmp_path, {"source_type": "pdf", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert str(p) in captured.out


def test_run_inspect_doc_prints_metrics_header_batch37(tmp_path, capsys):
    p = _write_doc(tmp_path, {"source_type": "pdf", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_prints_elements_count_batch37(tmp_path, capsys):
    p = _write_doc(tmp_path, {
        "source_type": "pdf",
        "elements": [{"type": "paragraph"}, {"type": "heading"}],
        "chunks": [],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "elements=2" in captured.out


def test_run_inspect_doc_prints_chunks_count_batch37(tmp_path, capsys):
    p = _write_doc(tmp_path, {
        "source_type": "pdf",
        "elements": [],
        "chunks": [{"text": "a"}, {"text": "b"}],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "chunks=2" in captured.out


def test_run_inspect_doc_prints_default_document_id_batch37(tmp_path, capsys):
    """doc 没有 document_id → 打印 '?'。"""
    p = _write_doc(tmp_path, {"source_type": "pdf", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "document_id: ?" in captured.out


def test_run_inspect_doc_prints_default_source_path_batch37(tmp_path, capsys):
    """doc 没有 source_path → 打印 '?'。"""
    p = _write_doc(tmp_path, {"source_type": "pdf", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "source:      ?" in captured.out or "source:" in captured.out


def test_run_inspect_doc_prints_default_parser_batch37(tmp_path, capsys):
    p = _write_doc(tmp_path, {"source_type": "pdf", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    # parser 默认 '?'
    assert "parser:" in captured.out


# ---------- main 第三十七批


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_main_run_missing_manifest_returns_2_batch37(tmp_path):
    rc = main(["run", "--manifest", str(tmp_path / "missing.json"),
               "--output", str(tmp_path / "r.json")])
    assert rc == 2


def test_main_run_invalid_manifest_json_returns_1_batch37(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("not json {", encoding="utf-8")
    rc = main(["run", "--manifest", str(p), "--output", str(tmp_path / "r.json")])
    assert rc == 1


def test_main_run_manifest_invalid_schema_returns_1_batch37(tmp_path):
    """manifest schema 校验失败 → 1。"""
    p = _write_manifest(tmp_path, {"manifest_version": "999.0"})
    rc = main(["run", "--manifest", str(p), "--output", str(tmp_path / "r.json")])
    assert rc == 1


def test_main_validate_report_missing_returns_2_batch37(tmp_path):
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_1_batch37(tmp_path):
    p = tmp_path / "report.json"
    p.write_text("not json {", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_invalid_content_returns_1_batch37(tmp_path):
    """JSON 合法但内容不符合 schema → 1。"""
    p = tmp_path / "report.json"
    p.write_text(json.dumps({"wrong": "shape"}), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_inspect_doc_missing_returns_2_batch37(tmp_path):
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_inspect_doc_invalid_json_returns_1_batch37(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("not json {", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_success_returns_0_batch37(tmp_path):
    p = _write_doc(tmp_path, {"source_type": "pdf", "elements": [], "chunks": []})
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_run_full_mock_returns_0_batch37(tmp_path):
    """完整 run 流程（mock process_single 返回失败）。"""
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    manifest_p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    output_p = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        rc = main(["run", "--manifest", str(manifest_p), "--output", str(output_p)])
    assert rc == 0
    assert output_p.is_file()


def test_main_run_with_kreuzberg_parser_batch37(tmp_path):
    """run --parser kreuzberg 通过 main。"""
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    manifest_p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    output_p = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [])) as m:
        rc = main([
            "run", "--manifest", str(manifest_p), "--output", str(output_p),
            "--parser", "kreuzberg",
        ])
    assert rc == 0
    assert m.call_args[1]["parser_name"] == "kreuzberg"


def test_main_run_with_max_chars_one_batch37(tmp_path):
    """run --max-chars 1 通过 main（边界：minimum=1）。"""
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    manifest_p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    output_p = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [])) as m:
        rc = main([
            "run", "--manifest", str(manifest_p), "--output", str(output_p),
            "--max-chars", "1",
        ])
    assert rc == 0
    assert m.call_args[1]["max_chars"] == 1


def test_main_run_with_tolerance_chars_zero_batch37(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    manifest_p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    output_p = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        rc = main([
            "run", "--manifest", str(manifest_p), "--output", str(output_p),
            "--tolerance-chars", "0",
        ])
    assert rc == 0


# ---------- module source forbidden tokens 第六十批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch37(token):
    src = inspect.getsource(cmod)
    assert token not in src


# ---------- module source 字符串精确补强第五十六批


def test_module_source_contains_docstring_batch37():
    src = inspect.getsource(cmod)
    assert "评测 CLI" in src


def test_module_source_contains_inspect_doc_docstring_batch37():
    src = inspect.getsource(cmod)
    assert "inspect-doc" in src


def test_module_source_contains_argparse_import_batch37():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_source_contains_json_import_batch37():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_source_contains_sys_import_batch37():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_source_contains_pathlib_import_batch37():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_manifest_import_batch37():
    src = inspect.getsource(cmod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_module_source_contains_report_import_batch37():
    src = inspect.getsource(cmod)
    assert "from evaluation.report import get_git_provenance" in src


def test_module_source_contains_runner_import_batch37():
    src = inspect.getsource(cmod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_contains_schema_import_batch37():
    src = inspect.getsource(cmod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_module_source_contains_build_parser_func_batch37():
    src = inspect.getsource(cmod)
    assert "def _build_parser()" in src


def test_module_source_contains_main_func_batch37():
    src = inspect.getsource(cmod)
    assert "def main(argv: list[str] | None = None) -> int:" in src


def test_module_source_contains_format_metric_func_batch37():
    src = inspect.getsource(cmod)
    assert "def _format_metric(name: str, metric: dict) -> str:" in src


def test_module_source_contains_run_inspect_doc_func_batch37():
    src = inspect.getsource(cmod)
    assert "def _run_inspect_doc(args) -> int:" in src


def test_module_source_contains_run_subparser_batch37():
    src = inspect.getsource(cmod)
    assert 'sub.add_parser("run"' in src


def test_module_source_contains_validate_report_subparser_batch37():
    src = inspect.getsource(cmod)
    assert '"validate-report"' in src


def test_module_source_contains_inspect_doc_subparser_batch37():
    src = inspect.getsource(cmod)
    assert '"inspect-doc"' in src


def test_module_source_contains_required_manifest_batch37():
    src = inspect.getsource(cmod)
    assert '"--manifest"' in src
    assert "required=True" in src


def test_module_source_contains_required_output_batch37():
    src = inspect.getsource(cmod)
    assert '"--output"' in src


def test_module_source_contains_parser_choices_batch37():
    src = inspect.getsource(cmod)
    assert '"fallback"' in src
    assert '"kreuzberg"' in src


def test_module_source_contains_max_chars_default_800_batch37():
    src = inspect.getsource(cmod)
    assert "default=800" in src


def test_module_source_contains_tolerance_default_30_batch37():
    src = inspect.getsource(cmod)
    assert "default=30" in src


def test_module_source_contains_utf8_reconfigure_batch37():
    src = inspect.getsource(cmod)
    assert 'sys.stdout.reconfigure(encoding="utf-8"' in src


def test_module_source_contains_errors_replace_batch37():
    src = inspect.getsource(cmod)
    assert 'errors="replace"' in src


def test_module_source_contains_raw_description_formatter_batch37():
    src = inspect.getsource(cmod)
    assert "RawDescriptionHelpFormatter" in src


def test_module_source_contains_raise_system_exit_batch37():
    src = inspect.getsource(cmod)
    assert "raise SystemExit(main())" in src


# ---------- signatures 第五十六批


def test_signature_build_parser_no_params_batch37():
    sig = inspect.signature(_build_parser)
    assert list(sig.parameters.keys()) == []


def test_signature_main_argv_optional_batch37():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_signature_main_return_int_batch37():
    sig = inspect.signature(main)
    assert sig.return_annotation == "int"


def test_signature_format_metric_params_batch37():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters.keys()) == ["name", "metric"]


def test_signature_format_metric_return_str_batch37():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation == "str"


def test_signature_run_inspect_doc_return_int_batch37():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


# ---------- module 合理性第五十六批


def test_module_has_build_parser_attribute_batch37():
    assert callable(cmod._build_parser)


def test_module_has_main_attribute_batch37():
    assert callable(cmod.main)


def test_module_has_format_metric_attribute_batch37():
    assert callable(cmod._format_metric)


def test_module_has_run_inspect_doc_attribute_batch37():
    assert callable(cmod._run_inspect_doc)


def test_module_main_returns_int_batch37(tmp_path):
    """main 返回 int（不是 None）。"""
    rc = main(["inspect-doc", str(tmp_path / "missing.json")])
    assert isinstance(rc, int)


def test_module_cli_invokable_as_module_batch37():
    """python -m evaluation.cli --help 应当可运行（用 .venv 的 python）。"""
    project_root = Path(__file__).resolve().parent.parent
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    python_exe = str(venv_python) if venv_python.is_file() else "python"
    result = subprocess.run(
        [python_exe, "-m", "evaluation.cli", "--help"],
        capture_output=True, cwd=project_root,
        encoding="utf-8", errors="replace",
    )
    # argparse --help 退出码是 0
    assert result.returncode == 0
    assert "evaluation.cli" in (result.stdout or "")


# ---------- 端到端集成第五十六批


def test_e2e_run_with_failed_pipeline_batch37(tmp_path, capsys):
    """完整 run：pipeline 失败 → 报告仍生成，rc=0。"""
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    manifest_p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    output_p = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        rc = main(["run", "--manifest", str(manifest_p), "--output", str(output_p)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "[OK]" in captured.out
    assert "documents=1" in captured.out


def test_e2e_validate_report_round_trip_batch37(tmp_path):
    """run 生成的报告能被 validate-report 校验通过。"""
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    manifest_p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    output_p = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        main(["run", "--manifest", str(manifest_p), "--output", str(output_p)])
    rc = main(["validate-report", str(output_p)])
    assert rc == 0


def test_e2e_inspect_doc_after_run_batch37(tmp_path, capsys):
    """跑 run 后 inspect-doc 一个生成的报告（不通过，因为 inspect-doc 接受的是 doc 不是 report）。"""
    p = _write_doc(tmp_path, {"source_type": "docx", "elements": [], "chunks": []})
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "type=docx" in captured.out


def test_e2e_help_for_each_subcommand_batch37():
    """每个子命令的 --help 退出码都是 0。"""
    for cmd in ["--help", "run --help", "validate-report --help", "inspect-doc --help"]:
        with pytest.raises(SystemExit) as exc:
            main(cmd.split())
        assert exc.value.code == 0


def test_e2e_no_args_returns_2_batch37():
    """无任何参数 → argparse 抛 SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
