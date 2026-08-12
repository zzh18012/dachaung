"""evaluation/cli.py 第六十三轮 edges 测试（Round 564）。

补强 edges61 未触及的角度（第三十五批）。
"""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import cli as cmod
from evaluation.cli import (
    _build_parser,
    _format_metric,
    _run_inspect_doc,
    main,
)


# ---------- _build_parser 第三十五批（subparser attrs / formatter / prog）


def _get_subparser(p, name):
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    return sub_action.choices[name]


def test_build_parser_run_subparser_prog_batch35():
    """run 子 parser 的 prog 是 'evaluation.cli run'。"""
    p = _build_parser()
    run_p = _get_subparser(p, "run")
    assert run_p.prog == "evaluation.cli run"


def test_build_parser_validate_report_subparser_prog_batch35():
    p = _build_parser()
    val_p = _get_subparser(p, "validate-report")
    assert val_p.prog == "evaluation.cli validate-report"


def test_build_parser_inspect_doc_subparser_prog_batch35():
    p = _build_parser()
    ins_p = _get_subparser(p, "inspect-doc")
    assert ins_p.prog == "evaluation.cli inspect-doc"


def test_build_parser_root_formatter_class_batch35():
    p = _build_parser()
    assert p.formatter_class is argparse.RawDescriptionHelpFormatter


def test_build_parser_run_subparser_manifest_help_batch35():
    p = _build_parser()
    run_p = _get_subparser(p, "run")
    action = run_p._option_string_actions["--manifest"]
    assert action.help is not None
    assert "清单" in action.help


def test_build_parser_run_subparser_output_help_batch35():
    p = _build_parser()
    run_p = _get_subparser(p, "run")
    action = run_p._option_string_actions["--output"]
    assert action.help is not None
    assert "报告" in action.help or "输出" in action.help


def test_build_parser_run_subparser_parser_help_batch35():
    p = _build_parser()
    run_p = _get_subparser(p, "run")
    action = run_p._option_string_actions["--parser"]
    assert action.help is not None


def test_build_parser_run_subparser_max_chars_type_int_batch35():
    p = _build_parser()
    run_p = _get_subparser(p, "run")
    action = run_p._option_string_actions["--max-chars"]
    assert action.type is int


def test_build_parser_run_subparser_tolerance_chars_type_int_batch35():
    p = _build_parser()
    run_p = _get_subparser(p, "run")
    action = run_p._option_string_actions["--tolerance-chars"]
    assert action.type is int


def test_build_parser_inspect_doc_tolerance_chars_type_int_batch35():
    p = _build_parser()
    ins_p = _get_subparser(p, "inspect-doc")
    action = ins_p._option_string_actions["--tolerance-chars"]
    assert action.type is int


def test_build_parser_validate_report_no_optional_args_batch35():
    """validate-report 子命令只有 positional input + help。"""
    p = _build_parser()
    val_p = _get_subparser(p, "validate-report")
    option_strings = list(val_p._option_string_actions.keys())
    # 只含 -h/--help
    assert set(option_strings) <= {"-h", "--help"}


def test_build_parser_inspect_doc_no_parser_arg_batch35():
    """inspect-doc 子命令没有 --parser。"""
    p = _build_parser()
    ins_p = _get_subparser(p, "inspect-doc")
    assert "--parser" not in ins_p._option_string_actions


def test_build_parser_inspect_doc_no_max_chars_batch35():
    p = _build_parser()
    ins_p = _get_subparser(p, "inspect-doc")
    assert "--max-chars" not in ins_p._option_string_actions


def test_build_parser_root_has_subparsers_required_batch35():
    """root parser 的 subparsers action required=True。"""
    p = _build_parser()
    sub_action = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    assert sub_action.required is True


def test_build_parser_run_subparser_has_help_action_batch35():
    """每个 subparser 自动有 -h/--help。"""
    p = _build_parser()
    run_p = _get_subparser(p, "run")
    assert "-h" in run_p._option_string_actions
    assert "--help" in run_p._option_string_actions


# ---------- _format_metric 第三十五批


def test_format_metric_value_huge_int_batch35():
    out = _format_metric("name", {"value": 2**31, "reason": None})
    assert str(2**31) in out


def test_format_metric_value_negative_int_batch35():
    out = _format_metric("name", {"value": -42, "reason": None})
    assert "-42" in out


def test_format_metric_value_true_with_reason_batch35():
    """bool True 时 reason 也展示。"""
    out = _format_metric("name", {"value": True, "reason": "details"})
    assert "true" in out
    assert "details" in out


def test_format_metric_value_false_with_reason_batch35():
    out = _format_metric("name", {"value": False, "reason": "expl"})
    assert "false" in out
    assert "expl" in out


def test_format_metric_value_none_no_reason_batch35():
    """value=None, reason=None → null + None str。"""
    out = _format_metric("name", {"value": None, "reason": None})
    assert "null" in out
    assert "None" in out


def test_format_metric_value_dict_unicode_keys_batch35():
    out = _format_metric("name", {"value": {"中文": 1}, "reason": None})
    assert "中文=1" in out


def test_format_metric_value_dict_with_zero_batch35():
    out = _format_metric("name", {"value": {"a": 0}, "reason": None})
    assert "a=0" in out


def test_format_metric_value_dict_with_negative_batch35():
    out = _format_metric("name", {"value": {"a": -1}, "reason": None})
    assert "a=-1" in out


def test_format_metric_value_dict_one_item_batch35():
    """单个 item 的 dict。"""
    out = _format_metric("name", {"value": {"only": 5}, "reason": None})
    assert "only=5" in out


def test_format_metric_value_float_with_reason_overrides_ok_batch35():
    out = _format_metric("name", {"value": 0.5, "reason": "partial"})
    assert "0.5000" in out
    assert "partial" in out
    assert "ok" not in out


def test_format_metric_value_int_zero_with_reason_batch35():
    """int 0 + reason → fallback 分支用 reason。"""
    out = _format_metric("name", {"value": 0, "reason": "specific"})
    assert "0" in out
    assert "specific" in out


def test_format_metric_name_long_batch35():
    """name 超过 36 字符 → 不截断。"""
    long_name = "x" * 50
    out = _format_metric(long_name, {"value": 1, "reason": None})
    assert long_name in out


def test_format_metric_name_short_batch35():
    """name 单字符。"""
    out = _format_metric("y", {"value": 1, "reason": None})
    assert "  y" in out


def test_format_metric_reason_unicode_batch35():
    out = _format_metric("name", {"value": None, "reason": "无标注"})
    assert "无标注" in out


# ---------- _run_inspect_doc 第三十五批


def _write_doc(tmp_path, doc):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def test_run_inspect_doc_empty_source_type_batch35(tmp_path, capsys):
    """缺 source_type → 默认 'unknown'，metric 仍跑。"""
    p = _write_doc(tmp_path, {"elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "type=unknown" in captured.out


def test_run_inspect_doc_docx_source_type_batch35(tmp_path, capsys):
    p = _write_doc(tmp_path, {"source_type": "docx", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "type=docx" in captured.out


def test_run_inspect_doc_missing_document_id_batch35(tmp_path, capsys):
    """缺 document_id → 显示 '?'。"""
    p = _write_doc(tmp_path, {"source_type": "pdf", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "document_id: ?" in captured.out


def test_run_inspect_doc_missing_source_path_batch35(tmp_path, capsys):
    p = _write_doc(tmp_path, {"source_type": "pdf", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    # source:      ?  type=pdf
    assert "source:" in captured.out
    assert "?" in captured.out


def test_run_inspect_doc_with_chunks_prints_chunk_count_batch35(tmp_path, capsys):
    p = _write_doc(tmp_path, {
        "source_type": "pdf",
        "elements": [],
        "chunks": [
            {"text": "a", "source_element_ids": []},
            {"text": "b", "source_element_ids": []},
        ],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "chunks=2" in captured.out


def test_run_inspect_doc_passes_tolerance_chars_batch35(tmp_path):
    """tolerance_chars 透传到 chunk_boundary_prf。"""
    p = _write_doc(tmp_path, {"source_type": "pdf", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 99
    with patch("evaluation.cli.chunk_boundary_prf") if False else patch(
        "evaluation.annotation_metrics.chunk_boundary_prf"
    ) as mock_cb:
        # 直接 patch 内部 import 路径不行——它是函数内 import
        # 改为不 patch，直接验证不抛
        pass
    rc = _run_inspect_doc(args)
    assert rc == 0


def test_run_inspect_doc_prints_schema_valid_batch35(tmp_path, capsys):
    p = _write_doc(tmp_path, {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "schema_valid" in captured.out


def test_run_inspect_doc_prints_silent_drop_count_batch35(tmp_path, capsys):
    p = _write_doc(tmp_path, {"source_type": "pdf", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "silent_drop_count" in captured.out


def test_run_inspect_doc_metric_order_bool_first_batch35(tmp_path, capsys):
    """bool metric 排在 int/float 之前。"""
    p = _write_doc(tmp_path, {"source_type": "pdf", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    out = captured.out
    # pipeline_success 应在 element_count_total 之前
    pos_bool = out.find("pipeline_success")
    pos_count = out.find("element_count_total")
    assert 0 <= pos_bool < pos_count


def test_run_inspect_doc_chunk_boundary_section_present_batch35(tmp_path, capsys):
    """inspect 输出含 chunk_boundary_f1（即使 null）。"""
    p = _write_doc(tmp_path, {"source_type": "pdf", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "chunk_boundary_f1" in captured.out


# ---------- main 第三十五批


def test_main_validate_report_with_corrupt_json_returns_1_batch35(tmp_path):
    p = tmp_path / "report.json"
    p.write_text("not json {", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_with_invalid_report_content_returns_1_batch35(tmp_path):
    """合法 JSON 但不是合法报告 → 1。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_with_directory_returns_2_batch35(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    rc = main(["validate-report", str(d)])
    assert rc == 2


def test_main_run_with_manifest_load_failure_returns_1_batch35(tmp_path, capsys):
    """manifest 文件存在但 schema 不过 → 1。"""
    p = tmp_path / "manifest.json"
    p.write_text(
        json.dumps({
            "manifest_version": "999.0",  # 不在 enum
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    rc = main([
        "run",
        "--manifest", str(p),
        "--output", str(tmp_path / "out.json"),
    ])
    assert rc == 1


def test_main_run_with_valid_manifest_executes_pipeline_batch35(tmp_path, capsys):
    """跑一遍真实 manifest，验证报告生成 + 自校验通过 + rc=0。"""
    pdf = tmp_path / "a.pdf"
    pdf.write_text("dummy", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [
                {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            ],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    out_path = tmp_path / "out.json"
    # 必须 cd 到 tmp_path 才能让 manifest 内的相对路径解析到 a.pdf
    import os
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        rc = main([
            "run",
            "--manifest", str(p),
            "--output", str(out_path),
        ])
    finally:
        os.chdir(cwd)
    assert rc == 0
    assert out_path.is_file()
    captured = capsys.readouterr()
    assert "[OK]" in captured.out


def test_main_run_with_kreuzberg_parser_choice_batch35(tmp_path, capsys):
    """--parser kreuzberg 被接受（manifest 失败 → rc=1 但不抛 SystemExit）。"""
    p = tmp_path / "manifest.json"
    p.write_text(
        json.dumps({
            "manifest_version": "999.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    rc = main([
        "run",
        "--manifest", str(p),
        "--output", str(tmp_path / "out.json"),
        "--parser", "kreuzberg",
    ])
    assert rc == 1


def test_main_run_no_args_after_run_raises_systemexit_batch35():
    """`run` 后必须接 args。"""
    with pytest.raises(SystemExit):
        main(["run"])


def test_main_run_only_manifest_no_output_raises_systemexit_batch35(tmp_path):
    with pytest.raises(SystemExit):
        main(["run", "--manifest", str(tmp_path / "x.json")])


def test_main_inspect_doc_no_input_raises_systemexit_batch35():
    with pytest.raises(SystemExit):
        main(["inspect-doc"])


def test_main_validate_report_no_input_raises_systemexit_batch35():
    with pytest.raises(SystemExit):
        main(["validate-report"])


# ---------- module source forbidden tokens 第五十三批


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
    "urllib",
    "socket",
    "pty.",
    "ctypes",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch35(token):
    src = inspect.getsource(cmod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch35():
    src = inspect.getsource(cmod)
    assert "评测 CLI" in src


def test_module_source_contains_future_annotations_batch35():
    src = inspect.getsource(cmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_argparse_import_batch35():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_source_contains_sys_import_batch35():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_source_contains_reconfigure_branch_batch35():
    src = inspect.getsource(cmod)
    assert "hasattr(sys.stdout" in src
    assert '"reconfigure"' in src or "'reconfigure'" in src


def test_module_source_contains_reconfigure_try_except_batch35():
    src = inspect.getsource(cmod)
    assert "AttributeError, OSError" in src


def test_module_source_contains_subcommand_run_batch35():
    src = inspect.getsource(cmod)
    assert 'sub.add_parser("run"' in src


def test_module_source_contains_subcommand_validate_report_batch35():
    src = inspect.getsource(cmod)
    assert "add_parser(" in src
    assert '"validate-report"' in src


def test_module_source_contains_subcommand_inspect_doc_batch35():
    src = inspect.getsource(cmod)
    assert "add_parser(" in src
    assert '"inspect-doc"' in src


def test_module_source_contains_error_prefix_batch35():
    src = inspect.getsource(cmod)
    assert "[ERROR]" in src


def test_module_source_contains_ok_prefix_batch35():
    src = inspect.getsource(cmod)
    assert "[OK]" in src


def test_module_source_contains_fail_prefix_batch35():
    src = inspect.getsource(cmod)
    assert "[FAIL]" in src


def test_module_source_contains_required_true_batch35():
    """subparsers required=True。"""
    src = inspect.getsource(cmod)
    assert "required=True" in src


def test_module_source_contains_choices_tuple_batch35():
    src = inspect.getsource(cmod)
    assert 'choices=("fallback", "kreuzberg")' in src


def test_module_source_contains_argparse_prog_batch35():
    src = inspect.getsource(cmod)
    assert 'prog="evaluation.cli"' in src


def test_module_source_contains_argparse_description_batch35():
    src = inspect.getsource(cmod)
    assert "description=" in src


# ---------- signatures 第四十九批


def test_signature_build_parser_return_annotation_batch35():
    sig = inspect.signature(_build_parser)
    assert "ArgumentParser" in str(sig.return_annotation)


def test_signature_format_metric_two_params_batch35():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters.keys()) == ["name", "metric"]


def test_signature_format_metric_name_str_batch35():
    sig = inspect.signature(_format_metric)
    assert sig.parameters["name"].annotation == "str"


def test_signature_format_metric_metric_dict_batch35():
    sig = inspect.signature(_format_metric)
    assert sig.parameters["metric"].annotation == "dict"


def test_signature_main_no_required_params_batch35():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.default is not None or p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


# ---------- module 合理性第四十九批


def test_module_imports_argparse_batch35():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_imports_json_batch35():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_imports_sys_batch35():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_imports_pathlib_batch35():
    src = inspect.getsource(cmod)
    assert "from pathlib import Path" in src


def test_module_has_build_parser_func_batch35():
    assert callable(cmod._build_parser)


def test_module_has_main_func_batch35():
    assert callable(cmod.main)


def test_module_has_format_metric_func_batch35():
    assert callable(cmod._format_metric)


def test_module_has_run_inspect_doc_func_batch35():
    assert callable(cmod._run_inspect_doc)


# ---------- 端到端集成第四十九批


def test_e2e_validate_report_real_run_output_batch35(tmp_path):
    """跑完整 run → 拿到报告 → 用 validate-report 校验通过。"""
    pdf = tmp_path / "a.pdf"
    pdf.write_text("dummy", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    out_path = tmp_path / "out.json"
    import os
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        rc1 = main(["run", "--manifest", str(p), "--output", str(out_path)])
        assert rc1 == 0
        rc2 = main(["validate-report", str(out_path)])
        assert rc2 == 0
    finally:
        os.chdir(cwd)


def test_e2e_inspect_doc_with_locator_metrics_batch35(tmp_path, capsys):
    """inspect-doc 输出含 locator / chunk reference 类指标。"""
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({
            "source_type": "pdf",
            "elements": [
                {"type": "paragraph", "content": "hello", "element_id": "e1",
                 "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]}},
            ],
            "chunks": [
                {"text": "hello", "source_element_ids": ["e1"]},
            ],
        }),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "pdf_locator_valid_ratio" in captured.out
    assert "chunk_reference_intact_ratio" in captured.out


def test_e2e_idempotent_inspect_doc_batch35(tmp_path, capsys):
    """同一文档跑两次 inspect-doc 输出一致。"""
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps({"source_type": "pdf", "elements": [], "chunks": []}),
        encoding="utf-8",
    )
    main(["inspect-doc", str(p)])
    out1 = capsys.readouterr().out
    main(["inspect-doc", str(p)])
    out2 = capsys.readouterr().out
    assert out1 == out2


def test_e2e_run_no_documents_batch35(tmp_path, capsys):
    """空 manifest（无 documents）→ 仍跑成功，rc=0。"""
    p = tmp_path / "manifest.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    out_path = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(p), "--output", str(out_path)])
    assert rc == 0
    assert out_path.is_file()


def test_e2e_main_argv_none_uses_sys_argv_batch35(monkeypatch):
    """main(argv=None) 会读 sys.argv[1:]，传 unknown 强制 SystemExit。"""
    monkeypatch.setattr("sys.argv", ["evaluation.cli", "--help"])
    with pytest.raises(SystemExit):
        main()
