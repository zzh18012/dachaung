"""evaluation/cli.py 第五十九轮 edges 测试（Round 536）。

补强 edges57 未触及的角度（第三十一批）：
- _build_parser 第三十一批：parser choices 限定 / run subparser 有 --parser / 有 --max-chars / 有 --tolerance-chars / validate-report 子命令 / inspect-doc 子命令
- _format_metric 第三十一批：value 是 True / value 是 False / value 是 int / value 是负 float / dict 多 item
- _run_inspect_doc 第三十一批：source_type 默认 unknown / document_id 缺失 / parser_version 缺失 / chunks 缺失 / elements 缺失
- main 第三十一批：run 不存在 manifest 返回 2 / validate-report 不存在返回 2 / 未知子命令 SystemExit / inspect-doc 完整跑
- module source forbidden tokens 第四十九批
- module source 字符串精确补强第四十五批
- signatures 第四十五批
- module 合理性第四十五批
- 端到端集成第四十五批
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


# ---------- _build_parser 第三十一批 ----------


def test_build_parser_run_parser_choices_batch31():
    """--parser choices 限定 ('fallback', 'kreuzberg')。"""
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
    assert parser_action.choices == ("fallback", "kreuzberg")


def test_build_parser_run_parser_default_fallback_batch31():
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
    assert parser_action.default == "fallback"


def test_build_parser_run_max_chars_default_800_batch31():
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
    assert mc_action.default == 800


def test_build_parser_run_max_chars_type_int_batch31():
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
    assert mc_action.type is int


def test_build_parser_run_tolerance_chars_default_30_batch31():
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
    assert tc_action.default == 30


def test_build_parser_inspect_doc_tolerance_chars_default_30_batch31():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    ins_p = sub_actions[0].choices["inspect-doc"]
    tc_action = None
    for a in ins_p._actions:
        if "--tolerance-chars" in (a.option_strings or []):
            tc_action = a
            break
    assert tc_action.default == 30


def test_build_parser_has_three_subcommands_batch31():
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    choices = sub_actions[0].choices
    assert set(choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_sub_required_batch31():
    """子命令是 required。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    ]
    assert sub_actions[0].required is True


# ---------- _format_metric 第三十一批 ----------


def test_format_metric_value_true_batch31():
    """value=True → 'true'（小写）。"""
    line = _format_metric("m1", {"value": True, "reason": None})
    assert "true" in line


def test_format_metric_value_false_batch31():
    """value=False → 'false'（小写）。"""
    line = _format_metric("m1", {"value": False, "reason": None})
    assert "false" in line


def test_format_metric_value_int_batch31():
    """int 不是 bool/float/dict → 走 default branch。"""
    line = _format_metric("m1", {"value": 42, "reason": None})
    assert "42" in line


def test_format_metric_value_negative_float_batch31():
    line = _format_metric("m1", {"value": -0.5, "reason": None})
    assert "-0.5000" in line


def test_format_metric_dict_multiple_items_batch31():
    line = _format_metric("counts", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in line
    assert "b=2" in line


def test_format_metric_dict_sorted_by_key_batch31():
    """dict 渲染按 key 排序。"""
    line = _format_metric("counts", {"value": {"z": 1, "a": 2}, "reason": None})
    # a 应在 z 前
    assert line.index("a=2") < line.index("z=1")


def test_format_metric_name_padding_batch31():
    """name 至少占 36 字符。"""
    line = _format_metric("m", {"value": 1, "reason": None})
    # 取前 38 字符应含 2 空格 + name（1 char）+ padding
    assert line.startswith("  m")


def test_format_metric_value_zero_batch31():
    """0 → '0'（int）。"""
    line = _format_metric("m1", {"value": 0, "reason": None})
    assert "0" in line


def test_format_metric_value_zero_float_batch31():
    """0.0 → '0.0000'（float）。"""
    line = _format_metric("m1", {"value": 0.0, "reason": None})
    assert "0.0000" in line


# ---------- _run_inspect_doc 第三十一批 ----------


def test_run_inspect_doc_source_type_unknown_batch31(capsys, tmp_path):
    """source_type 缺失 → 默认 'unknown'。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "type=unknown" in captured.out


def test_run_inspect_doc_document_id_missing_batch31(capsys, tmp_path):
    """document_id 缺失 → '?'。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "document_id: ?" in captured.out


def test_run_inspect_doc_parser_version_missing_batch31(capsys, tmp_path):
    """parser_version 缺失 → '?'。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "v?" in captured.out


def test_run_inspect_doc_chunks_missing_batch31(capsys, tmp_path):
    """chunks 缺失 → 0。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": []}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "chunks=0" in captured.out


def test_run_inspect_doc_elements_missing_batch31(capsys, tmp_path):
    """elements 缺失 → 0。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"chunks": []}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    _run_inspect_doc(args)
    captured = capsys.readouterr()
    assert "elements=0" in captured.out


def test_run_inspect_doc_json_top_level_not_dict_batch31(capsys, tmp_path):
    """JSON 顶层是 list → 返回 1。"""
    p = tmp_path / "doc.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 1
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err


def test_run_inspect_doc_full_metrics_section_batch31(capsys, tmp_path):
    """完整跑有 metrics: 区块。"""
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps(
            {
                "document_id": "d1",
                "source_type": "pdf",
                "elements": [{"type": "paragraph"}],
                "chunks": [{"text": "abc"}],
            }
        ),
        encoding="utf-8",
    )
    args = MagicMock(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "metrics:" in captured.out
    assert "document_id: d1" in captured.out


def test_run_inspect_doc_returns_int_batch31(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    args = MagicMock(input=str(p), tolerance_chars=30)
    rc = _run_inspect_doc(args)
    assert isinstance(rc, int)


# ---------- main 第三十一批 ----------


def test_main_run_nonexistent_manifest_returns_2_batch31():
    rc = main(["run", "--manifest", "/nonexistent.json", "--output", "/tmp/out.json"])
    assert rc == 2


def test_main_validate_report_nonexistent_returns_2_batch31():
    rc = main(["validate-report", "/nonexistent.json"])
    assert rc == 2


def test_main_inspect_doc_nonexistent_returns_2_batch31():
    rc = main(["inspect-doc", "/nonexistent.json"])
    assert rc == 2


def test_main_unknown_subcommand_raises_systemexit_batch31():
    with pytest.raises(SystemExit):
        main(["unknown-command"])


def test_main_run_invalid_parser_choice_raises_systemexit_batch31():
    """--parser unknown → argparse 拒绝 → SystemExit。"""
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "m.json", "--output", "o.json", "--parser", "unknown"])


def test_main_run_missing_manifest_raises_systemexit_batch31():
    """缺 --manifest → argparse 拒绝 → SystemExit。"""
    with pytest.raises(SystemExit):
        main(["run", "--output", "o.json"])


def test_main_run_missing_output_raises_systemexit_batch31():
    with pytest.raises(SystemExit):
        main(["run", "--manifest", "m.json"])


def test_main_returns_int_for_validate_report_batch31(tmp_path):
    p = tmp_path / "r.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert isinstance(rc, int)


def test_main_run_invalid_json_manifest_returns_1_batch31(tmp_path):
    """run 子命令：manifest 是 invalid JSON → 1。"""
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(p), "--output", str(out)])
    assert rc == 1


# ---------- module source forbidden tokens 第四十九批 ----------


def test_module_source_no_subprocess_batch31():
    src = inspect.getsource(climod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch31():
    src = inspect.getsource(climod)
    assert "os.system" not in src


def test_module_source_no_eval_batch31():
    src = inspect.getsource(climod)
    assert "eval(" not in src


def test_module_source_no_exec_batch31():
    src = inspect.getsource(climod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch31():
    src = inspect.getsource(climod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch31():
    src = inspect.getsource(climod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch31():
    src = inspect.getsource(climod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch31():
    src = inspect.getsource(climod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch31():
    src = inspect.getsource(climod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch31():
    src = inspect.getsource(climod)
    assert "shutil" not in src


def test_module_source_no_requests_batch31():
    src = inspect.getsource(climod)
    assert "requests" not in src


def test_module_source_no_unlink_batch31():
    src = inspect.getsource(climod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十五批 ----------


def test_module_source_contains_module_docstring_batch31():
    src = inspect.getsource(climod)
    assert "评测 CLI" in src


def test_module_source_contains_usage_doc_batch31():
    src = inspect.getsource(climod)
    assert "validate-report" in src
    assert "inspect-doc" in src


def test_module_source_contains_argparse_import_batch31():
    src = inspect.getsource(climod)
    assert "import argparse" in src


def test_module_source_contains_json_import_batch31():
    src = inspect.getsource(climod)
    assert "import json" in src


def test_module_source_contains_sys_import_batch31():
    src = inspect.getsource(climod)
    assert "import sys" in src


def test_module_source_contains_pathlib_import_batch31():
    src = inspect.getsource(climod)
    assert "from pathlib import Path" in src


def test_module_source_contains_manifest_import_batch31():
    src = inspect.getsource(climod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_module_source_contains_runner_import_batch31():
    src = inspect.getsource(climod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_contains_schema_import_batch31():
    src = inspect.getsource(climod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_module_source_contains_build_parser_func_batch31():
    src = inspect.getsource(climod)
    assert "def _build_parser()" in src


def test_module_source_contains_main_func_batch31():
    src = inspect.getsource(climod)
    assert "def main(argv" in src


def test_module_source_contains_format_metric_func_batch31():
    src = inspect.getsource(climod)
    assert "def _format_metric(name: str, metric: dict) -> str:" in src


def test_module_source_contains_run_inspect_doc_func_batch31():
    src = inspect.getsource(climod)
    assert "def _run_inspect_doc(args) -> int:" in src


def test_module_source_contains_reconfigure_call_batch31():
    src = inspect.getsource(climod)
    assert "reconfigure" in src


def test_module_source_contains_subparsers_batch31():
    src = inspect.getsource(climod)
    assert "add_subparsers" in src


def test_module_source_contains_run_command_branch_batch31():
    src = inspect.getsource(climod)
    assert 'args.command == "run"' in src


def test_module_source_contains_validate_report_branch_batch31():
    src = inspect.getsource(climod)
    assert 'args.command == "validate-report"' in src


def test_module_source_contains_inspect_doc_branch_batch31():
    src = inspect.getsource(climod)
    assert 'args.command == "inspect-doc"' in src


def test_module_source_contains_main_block_batch31():
    src = inspect.getsource(climod)
    assert 'if __name__ == "__main__"' in src


def test_module_source_contains_raise_systemexit_batch31():
    src = inspect.getsource(climod)
    assert "raise SystemExit(main())" in src


# ---------- signatures 第四十五批 ----------


def test_signature_main_argv_annotation_batch31():
    sig = inspect.signature(main)
    assert "list[str] | None" in str(sig.parameters["argv"].annotation)


def test_signature_main_return_int_batch31():
    sig = inspect.signature(main)
    assert sig.return_annotation == "int"


def test_signature_main_argv_default_none_batch31():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_signature_build_parser_no_params_batch31():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_build_parser_return_argument_parser_batch31():
    sig = inspect.signature(_build_parser)
    assert "ArgumentParser" in str(sig.return_annotation)


def test_signature_format_metric_name_str_batch31():
    sig = inspect.signature(_format_metric)
    assert sig.parameters["name"].annotation == "str"


def test_signature_format_metric_metric_dict_batch31():
    sig = inspect.signature(_format_metric)
    assert sig.parameters["metric"].annotation == "dict"


def test_signature_format_metric_return_str_batch31():
    sig = inspect.signature(_format_metric)
    assert sig.return_annotation == "str"


def test_signature_run_inspect_doc_args_param_batch31():
    sig = inspect.signature(_run_inspect_doc)
    assert "args" in sig.parameters


def test_signature_run_inspect_doc_return_int_batch31():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


# ---------- module 合理性第四十五批 ----------


def test_module_has_future_annotations_batch31():
    src = inspect.getsource(climod)
    assert "from __future__ import annotations" in src


def test_module_imports_argparse_batch31():
    src = inspect.getsource(climod)
    assert "import argparse" in src


def test_module_imports_json_batch31():
    src = inspect.getsource(climod)
    assert "import json" in src


def test_module_imports_sys_batch31():
    src = inspect.getsource(climod)
    assert "import sys" in src


def test_module_imports_pathlib_batch31():
    src = inspect.getsource(climod)
    assert "from pathlib import Path" in src


def test_module_no_class_definitions_batch31():
    src = inspect.getsource(climod)
    assert "\nclass " not in src


# ---------- 端到端集成第四十五批 ----------


def test_e2e_main_inspect_doc_full_run_batch31(capsys, tmp_path):
    """端到端：inspect-doc 完整跑。"""
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps(
            {
                "document_id": "d_test",
                "source_type": "pdf",
                "parser_name": "fallback",
                "parser_version": "1.0",
                "elements": [{"type": "paragraph", "element_id": "p1", "content": "hello"}],
                "chunks": [{"text": "hello", "source_element_ids": ["p1"]}],
            }
        ),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "document_id: d_test" in captured.out
    assert "type=pdf" in captured.out
    assert "fallback v1.0" in captured.out
    assert "elements=1" in captured.out
    assert "chunks=1" in captured.out


def test_e2e_main_validate_report_invalid_json_returns_1_batch31(tmp_path):
    p = tmp_path / "r.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_e2e_main_no_args_raises_systemexit_batch31(capsys):
    with pytest.raises(SystemExit):
        main([])


def test_e2e_build_parser_run_full_parse_batch31():
    p = _build_parser()
    ns = p.parse_args(
        [
            "run",
            "--manifest", "m.json",
            "--output", "o.json",
            "--parser", "kreuzberg",
            "--max-chars", "500",
            "--tolerance-chars", "10",
        ]
    )
    assert ns.command == "run"
    assert ns.parser == "kreuzberg"
    assert ns.max_chars == 500
    assert ns.tolerance_chars == 10


def test_e2e_build_parser_inspect_doc_full_parse_batch31():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "20"])
    assert ns.command == "inspect-doc"
    assert ns.input == "doc.json"
    assert ns.tolerance_chars == 20


def test_e2e_format_metric_idempotent_batch31():
    m = {"value": 1.0, "reason": "ok"}
    l1 = _format_metric("m1", m)
    l2 = _format_metric("m1", m)
    assert l1 == l2


def test_e2e_inspect_doc_zero_metrics_batch31(capsys, tmp_path):
    """端到端：空 document 的 metrics 不抛错。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_inspect_doc_returns_0_with_valid_doc_batch31(tmp_path):
    """端到端：合法 doc 返回 0。"""
    p = tmp_path / "doc.json"
    p.write_text(
        json.dumps(
            {"document_id": "x", "source_type": "docx", "elements": [], "chunks": []}
        ),
        encoding="utf-8",
    )
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
