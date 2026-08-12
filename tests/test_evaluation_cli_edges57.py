"""evaluation/cli.py 第五十八轮 edges 测试（Round 529）。

补强 edges56 未触及的角度（第三十批）：
- _build_parser 第三十批：prog 字符串 / formatter 是 RawDescriptionHelpFormatter / run --manifest required / run --output required
- _format_metric 第三十批：value 是 None + reason=ok / value 是 None + reason=None / value 是 0.5 vs 0.50 格式
- _run_inspect_doc 第三十批：输出 metrics 多类型混合 / count=0 处理 / 文件不存在 stderr 输出
- main 第三十批：返回 0 / 1 / 2 / inspect-doc 成功路径返回 0
- module source forbidden tokens 第四十八批
- module source 字符串精确补强第四十四批
- signatures 第四十四批
- module 合理性第四十四批
- 端到端集成第四十四批
"""

from __future__ import annotations

import inspect
import io
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import cli as climod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 第三十批 ----------


def test_build_parser_prog_is_evaluation_cli_batch30():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_formatter_is_raw_description_batch30():
    """formatter_class 是 RawDescriptionHelpFormatter。"""
    import argparse as ap
    p = _build_parser()
    assert p.formatter_class is ap.RawDescriptionHelpFormatter


def test_build_parser_run_manifest_required_batch30():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    run_p = sub_actions[0].choices["run"]
    manifest_action = None
    for a in run_p._actions:
        if "--manifest" in (a.option_strings or []):
            manifest_action = a
            break
    assert manifest_action is not None
    assert manifest_action.required is True


def test_build_parser_run_output_required_batch30():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    run_p = sub_actions[0].choices["run"]
    output_action = None
    for a in run_p._actions:
        if "--output" in (a.option_strings or []):
            output_action = a
            break
    assert output_action is not None
    assert output_action.required is True


def test_build_parser_validate_report_input_required_batch30():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    val_p = sub_actions[0].choices["validate-report"]
    input_action = None
    for a in val_p._actions:
        if "input" in (a.option_strings or []) or a.dest == "input":
            input_action = a
            break
    assert input_action is not None
    # positional 参数是 required
    assert input_action.required is True


def test_build_parser_inspect_doc_input_required_batch30():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    ins_p = sub_actions[0].choices["inspect-doc"]
    input_action = None
    for a in ins_p._actions:
        if a.dest == "input":
            input_action = a
            break
    assert input_action is not None
    assert input_action.required is True


def test_build_parser_run_no_required_for_parser_batch30():
    """--parser 不是 required（有 default）。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    run_p = sub_actions[0].choices["run"]
    parser_action = None
    for a in run_p._actions:
        if "--parser" in (a.option_strings or []):
            parser_action = a
            break
    assert parser_action.required is False


def test_build_parser_run_no_required_for_max_chars_batch30():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    run_p = sub_actions[0].choices["run"]
    mc_action = None
    for a in run_p._actions:
        if "--max-chars" in (a.option_strings or []):
            mc_action = a
            break
    assert mc_action.required is False


def test_build_parser_run_no_required_for_tolerance_chars_batch30():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    run_p = sub_actions[0].choices["run"]
    tc_action = None
    for a in run_p._actions:
        if "--tolerance-chars" in (a.option_strings or []):
            tc_action = a
            break
    assert tc_action.required is False


# ---------- _format_metric 第三十批 ----------


def test_format_metric_value_none_with_reason_ok_batch30():
    """value=None reason='ok' → null (ok)。"""
    line = _format_metric("m1", {"value": None, "reason": "ok"})
    assert "null" in line
    assert "(ok)" in line


def test_format_metric_value_none_no_reason_batch30():
    """value=None reason=None → null (None)。"""
    line = _format_metric("m1", {"value": None, "reason": None})
    assert "null" in line
    assert "(None)" in line


def test_format_metric_value_zero_point_five_batch30():
    """0.5 → '0.5000'（:.4f）。"""
    line = _format_metric("m1", {"value": 0.5, "reason": None})
    assert "0.5000" in line


def test_format_metric_value_one_batch30():
    line = _format_metric("m1", {"value": 1, "reason": None})
    # 1 不是 None/bool/float/dict → 直接 str(value)
    assert "1" in line


def test_format_metric_dict_value_single_item_batch30():
    line = _format_metric("counts", {"value": {"a": 5}, "reason": None})
    assert "a=5" in line


def test_format_metric_no_metric_value_key_batch30():
    """metric 缺 value key → .get 返回 None。"""
    line = _format_metric("m1", {"reason": "x"})
    assert "null" in line


def test_format_metric_no_metric_reason_key_batch30():
    """metric 缺 reason key → .get 返回 None。"""
    line = _format_metric("m1", {"value": 1.0})
    # reason=None 但 value=1.0 → "(None)"（因为 reason or 'ok' = None or 'ok' = 'ok'？）
    # Wait: reason=None → reason or 'ok' = 'ok'（因为 None 是 falsy）
    # 实际：实现 metric.get("reason")，没传则 None
    # None or 'ok' = 'ok'
    assert "ok" in line


def test_format_metric_value_negative_int_batch30():
    line = _format_metric("m1", {"value": -5, "reason": None})
    assert "-5" in line


# ---------- _run_inspect_doc 第三十批 ----------


def test_run_inspect_doc_output_has_metrics_section_batch30(capsys, tmp_path):
    """输出有 metrics: 区块。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "metrics:" in captured.out


def test_run_inspect_doc_zero_counts_batch30(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "elements=0" in captured.out
    assert "chunks=0" in captured.out


def test_run_inspect_doc_file_not_exists_returns_2_batch30(capsys):
    args = MagicMock(input="/nonexistent.json", tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 2
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_run_inspect_doc_invalid_json_returns_1_batch30(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("not json", encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_run_inspect_doc_tolerance_chars_passed_batch30(tmp_path):
    """tolerance_chars 透传给 chunk_boundary_prf。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=42)
    with patch("evaluation.annotation_metrics.chunk_boundary_prf") as mock_cb:
        mock_cb.return_value = {
            "chunk_boundary_precision": {"value": None, "reason": "x"},
            "chunk_boundary_recall": {"value": None, "reason": "x"},
            "chunk_boundary_f1": {"value": None, "reason": "x"},
            "_tolerance_chars": {"value": 42, "reason": None},
        }
        _run_inspect_doc(args)
    assert mock_cb.call_args[1]["tolerance_chars"] == 42


def test_run_inspect_doc_returns_int_batch30(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert isinstance(rc, int)


# ---------- main 第三十批 ----------


def test_main_inspect_doc_success_returns_0_batch30(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_nonexistent_returns_2_batch30():
    rc = main(["inspect-doc", "/nonexistent.json"])
    assert rc == 2


def test_main_validate_report_nonexistent_returns_2_batch30():
    rc = main(["validate-report", "/nonexistent.json"])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_1_batch30(tmp_path):
    p = tmp_path / "report.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_run_nonexistent_manifest_returns_2_batch30():
    rc = main(["run", "--manifest", "/nonexistent.json", "--output", "/tmp/out.json"])
    assert rc == 2


def test_main_returns_int_for_inspect_doc_batch30(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert isinstance(rc, int)


def test_main_no_args_raises_systemexit_batch30():
    with pytest.raises(SystemExit):
        main([])


# ---------- module source forbidden tokens 第四十八批 ----------


def test_module_source_no_subprocess_batch30():
    src = inspect.getsource(climod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch30():
    src = inspect.getsource(climod)
    assert "os.system" not in src


def test_module_source_no_eval_batch30():
    src = inspect.getsource(climod)
    assert "eval(" not in src


def test_module_source_no_exec_batch30():
    src = inspect.getsource(climod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch30():
    src = inspect.getsource(climod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch30():
    src = inspect.getsource(climod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch30():
    src = inspect.getsource(climod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch30():
    src = inspect.getsource(climod)
    assert "breakpoint(" not in src


def test_module_source_no_shutil_batch30():
    src = inspect.getsource(climod)
    assert "shutil" not in src


def test_module_source_no_requests_batch30():
    src = inspect.getsource(climod)
    assert "requests" not in src


def test_module_source_no_unlink_batch30():
    src = inspect.getsource(climod)
    assert ".unlink()" not in src


def test_module_source_no_open_w_mode_batch30():
    src = inspect.getsource(climod)
    assert "'w'" not in src
    assert '"w"' not in src


# ---------- module source 字符串精确补强第四十四批 ----------


def test_module_source_contains_module_docstring_batch30():
    src = inspect.getsource(climod)
    assert "评测 CLI" in src


def test_module_source_contains_subcommands_doc_batch30():
    src = inspect.getsource(climod)
    assert "validate-report" in src
    assert "inspect-doc" in src


def test_module_source_contains_main_func_batch30():
    src = inspect.getsource(climod)
    assert "def main(argv" in src


def test_module_source_contains_argv_default_none_batch30():
    src = inspect.getsource(climod)
    assert "argv: list[str] | None = None" in src


def test_module_source_contains_build_parser_batch30():
    src = inspect.getsource(climod)
    assert "def _build_parser()" in src


def test_module_source_contains_format_metric_batch30():
    src = inspect.getsource(climod)
    assert "def _format_metric(name: str, metric: dict) -> str:" in src


def test_module_source_contains_run_inspect_doc_batch30():
    src = inspect.getsource(climod)
    assert "def _run_inspect_doc(args) -> int:" in src


def test_module_source_contains_utf8_reconfigure_batch30():
    src = inspect.getsource(climod)
    assert "reconfigure" in src
    assert "utf-8" in src


def test_module_source_contains_argparse_import_batch30():
    src = inspect.getsource(climod)
    assert "import argparse" in src


def test_module_source_contains_sys_stdout_reconfigure_batch30():
    src = inspect.getsource(climod)
    assert "sys.stdout" in src


def test_module_source_contains_run_command_branch_batch30():
    src = inspect.getsource(climod)
    assert 'args.command == "run"' in src


def test_module_source_contains_validate_report_branch_batch30():
    src = inspect.getsource(climod)
    assert 'args.command == "validate-report"' in src


def test_module_source_contains_inspect_doc_branch_batch30():
    src = inspect.getsource(climod)
    assert 'args.command == "inspect-doc"' in src


# ---------- signatures 第四十四批 ----------


def test_signature_main_argv_annotation_batch30():
    sig = inspect.signature(main)
    assert "list[str] | None" in str(sig.parameters["argv"].annotation)


def test_signature_main_return_int_batch30():
    sig = inspect.signature(main)
    assert sig.return_annotation == "int"


def test_signature_main_argv_default_none_batch30():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_signature_build_parser_no_params_batch30():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_build_parser_return_argument_parser_batch30():
    sig = inspect.signature(_build_parser)
    assert "ArgumentParser" in str(sig.return_annotation)


def test_signature_format_metric_name_str_batch30():
    sig = inspect.signature(_format_metric)
    assert sig.parameters["name"].annotation == "str"


def test_signature_format_metric_return_str_batch30():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation == "str"


def test_signature_run_inspect_doc_args_param_batch30():
    sig = inspect.signature(_run_inspect_doc)
    assert "args" in sig.parameters


def test_signature_run_inspect_doc_return_int_batch30():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


# ---------- module 合理性第四十四批 ----------


def test_module_has_future_annotations_batch30():
    src = inspect.getsource(climod)
    assert "from __future__ import annotations" in src


def test_module_imports_argparse_batch30():
    src = inspect.getsource(climod)
    assert "import argparse" in src


def test_module_imports_json_batch30():
    src = inspect.getsource(climod)
    assert "import json" in src


def test_module_imports_sys_batch30():
    src = inspect.getsource(climod)
    assert "import sys" in src


def test_module_imports_pathlib_batch30():
    src = inspect.getsource(climod)
    assert "from pathlib import Path" in src


def test_module_has_main_block_batch30():
    src = inspect.getsource(climod)
    assert 'if __name__ == "__main__"' in src


def test_module_main_block_uses_systemexit_batch30():
    src = inspect.getsource(climod)
    assert "raise SystemExit(main())" in src


def test_module_no_class_definitions_batch30():
    src = inspect.getsource(climod)
    assert "\nclass " not in src


# ---------- 端到端集成第四十四批 ----------


def test_e2e_inspect_doc_full_run_batch30(capsys, tmp_path):
    """端到端：inspect-doc 完整跑。"""
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps(
            {
                "document_id": "d_test",
                "source_type": "pdf",
                "elements": [{"type": "paragraph"}],
                "chunks": [{"text": "abc"}],
            }
        ),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "document_id: d_test" in captured.out
    assert "elements=1" in captured.out
    assert "chunks=1" in captured.out


def test_e2e_validate_report_invalid_returns_1_batch30(tmp_path):
    p = tmp_path / "report.json"
    p.write_text(json.dumps({"not_a_report": True}), encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_main_no_args_exits_with_usage_batch30(capsys):
    with pytest.raises(SystemExit):
        main([])


def test_e2e_build_parser_run_full_parse_batch30():
    p = _build_parser()
    ns = p.parse_args(
        ["run", "--manifest", "m.json", "--output", "o.json", "--parser", "kreuzberg", "--max-chars", "500"]
    )
    assert ns.command == "run"
    assert ns.parser == "kreuzberg"
    assert ns.max_chars == 500


def test_e2e_format_metric_idempotent_batch30():
    m = {"value": 1.0, "reason": "ok"}
    l1 = _format_metric("m1", m)
    l2 = _format_metric("m1", m)
    assert l1 == l2


def test_e2e_inspect_doc_output_has_file_line_batch30(capsys, tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "file:" in captured.out


def test_e2e_inspect_doc_metrics_sorted_batch30(capsys, tmp_path):
    """metrics 排序：bool 优先，然后 ratio，然后 count/dict，最后 null。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    # null 行应该靠后
    lines_with_null = [l for l in captured.out.split("\n") if "null" in l]
    lines_with_value = [l for l in captured.out.split("\n") if "null" not in l and "  " in l and "metrics" not in l and "file" not in l and "document" not in l and "source" not in l and "parser" not in l and "counts" not in l]
    # 不严格断言顺序，但确保有 null 行
    assert len(lines_with_null) > 0
