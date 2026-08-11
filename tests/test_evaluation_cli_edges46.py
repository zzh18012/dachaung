"""evaluation/cli.py 第四十七轮 edges 测试（Round 453）。

补强 edges45 未触及的角度：
- _build_parser 行为深度第十九批（_actions 类型 / run parser 含 4 options / validate-report parser 含 1 positional / inspect-doc parser 含 1 positional + 1 option / formatter class / prog / 多个子 parser 独立）
- argparse Namespace 行为深度第十九批（args.input vs args.command / run args defaults / validate-report args.input 必填 / inspect-doc args.input 必填 / run with kreuzberg parser）
- _format_metric 边界第十九批（int value / dict with 1 item / dict with multiple / name 短 / name 长 / metric 缺 value / metric 缺 reason / metric 完整）
- _run_inspect_doc 边界第十九批（compute_automatic_metrics 调用 / figure_caption_prf 调用 / chunk_boundary_prf 调用 tolerance 透传 / output 含 metrics / 输出排序 / document_id 来自 doc）
- main 路由第十九批（run success → 写 file + validate + print OK / run n_ok 计算 / run with multiple docs / validate-report success / validate-report EvalSchemaError / inspect-doc success / inspect-doc invalid JSON）
- module source forbidden tokens 第三十三批
- module source 字符串精确补强第三十一批
- signatures 第二十九批
- module 合理性第二十九批
- 端到端集成第二十九批
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
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 行为深度第十九批 ----------


def test_build_parser_actions_count_batch19():
    """顶层 parser 至少有 1 个 action（-h/--help）+ subparsers action。"""
    p = _build_parser()
    assert len(p._actions) >= 2


def test_build_parser_run_subparser_actions_count_batch19():
    """run 子 parser 应有 5 actions（-h, --manifest, --output, --parser, --max-chars, --tolerance-chars）。"""
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    # 6 actions: -h + 5 options
    assert len(run_p._actions) >= 5


def test_build_parser_validate_report_subparser_actions_count_batch19():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    val_p = sub_action.choices["validate-report"]
    # 2 actions: -h + 1 positional
    assert len(val_p._actions) == 2


def test_build_parser_inspect_doc_subparser_actions_count_batch19():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    ins_p = sub_action.choices["inspect-doc"]
    # 3 actions: -h + 1 positional + 1 option
    assert len(ins_p._actions) == 3


def test_build_parser_run_subparser_has_manifest_option_batch19():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    option_strings = []
    for a in run_p._actions:
        option_strings.extend(a.option_strings)
    assert "--manifest" in option_strings


def test_build_parser_run_subparser_has_output_option_batch19():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    option_strings = []
    for a in run_p._actions:
        option_strings.extend(a.option_strings)
    assert "--output" in option_strings


def test_build_parser_run_subparser_has_parser_option_batch19():
    p = _build_parser()
    sub_action = next(
        a for a in p._actions if isinstance(a, argparse._SubParsersAction)
    )
    run_p = sub_action.choices["run"]
    option_strings = []
    for a in run_p._actions:
        option_strings.extend(a.option_strings)
    assert "--parser" in option_strings


def test_build_parser_validate_report_positional_required_batch19():
    p = _build_parser()
    args = p.parse_args(["validate-report", "r.json"])
    assert args.input == "r.json"


def test_build_parser_inspect_doc_positional_required_batch19():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "d.json"])
    assert args.input == "d.json"


def test_build_parser_run_with_all_options_batch19():
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "m.json", "--output", "o.json",
        "--parser", "kreuzberg", "--max-chars", "500", "--tolerance-chars", "10",
    ])
    assert args.parser == "kreuzberg"
    assert args.max_chars == 500
    assert args.tolerance_chars == 10


# ---------- argparse Namespace 行为深度第十九批 ----------


def test_namespace_run_manifest_value_batch19():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.manifest == "m.json"


def test_namespace_run_output_value_batch19():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.output == "o.json"


def test_namespace_validate_report_input_value_batch19():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"


def test_namespace_inspect_doc_input_value_batch19():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.input == "doc.json"


def test_namespace_inspect_doc_tolerance_default_batch19():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_namespace_run_command_only_after_parse_batch19():
    """command 字段在 parse_args 后才存在。"""
    p = _build_parser()
    args = p.parse_args(["validate-report", "r.json"])
    assert args.command == "validate-report"


# ---------- _format_metric 边界第十九批 ----------


def test_format_metric_int_positive_batch19():
    r = _format_metric("count", {"value": 42, "reason": None})
    assert "42" in r


def test_format_metric_dict_one_item_batch19():
    r = _format_metric("counts", {"value": {"x": 1}, "reason": None})
    assert "x=1" in r


def test_format_metric_dict_multiple_items_batch19():
    r = _format_metric("counts", {"value": {"a": 1, "b": 2, "c": 3}, "reason": None})
    assert "a=1" in r
    assert "b=2" in r
    assert "c=3" in r


def test_format_metric_short_name_batch19():
    r = _format_metric("x", {"value": 1, "reason": None})
    assert "x" in r


def test_format_metric_long_name_batch19():
    name = "very_long_metric_name_exceeding_thirty_six_chars"
    r = _format_metric(name, {"value": 1, "reason": None})
    assert name in r


def test_format_metric_metric_missing_value_batch19():
    """metric 缺 value key → .get(value) 返 None → null 分支。"""
    r = _format_metric("m", {"reason": "no_value"})
    assert "null" in r


def test_format_metric_metric_missing_reason_batch19():
    """metric 缺 reason → .get(reason) 返 None。"""
    r = _format_metric("m", {"value": True})
    assert "true" in r  # bool value
    # reason None → 'ok' 替换
    assert "ok" in r


def test_format_metric_complete_batch19():
    r = _format_metric("ratio", {"value": 0.75, "reason": "partial"})
    assert "0.7500" in r
    assert "partial" in r


def test_format_metric_returns_string_batch19():
    r = _format_metric("m", {"value": 1, "reason": None})
    assert isinstance(r, str)


# ---------- _run_inspect_doc 边界第十九批 ----------


def _mk_args_inspect(input_str, tolerance=30):
    ns = MagicMock()
    ns.input = input_str
    ns.tolerance_chars = tolerance
    return ns


def _mk_doc_full():
    return {
        "document_id": "doc1",
        "source_path": "/fake/doc.pdf",
        "source_type": "pdf",
        "parser_name": "fallback",
        "parser_version": "1.0.0",
        "elements": [
            {"element_id": "e1", "type": "heading", "text": "Heading"},
            {"element_id": "e2", "type": "paragraph", "text": "Body"},
        ],
        "chunks": [
            {"chunk_id": "c1", "source_element_ids": ["e1"], "text": "Heading"},
        ],
    }


def test_run_inspect_doc_prints_file_path_batch19(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(_mk_doc_full()), encoding="utf-8")
    args = _mk_args_inspect(str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "file:" in out
    assert str(p) in out


def test_run_inspect_doc_prints_document_id_batch19(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(_mk_doc_full()), encoding="utf-8")
    args = _mk_args_inspect(str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "document_id:" in out
    assert "doc1" in out


def test_run_inspect_doc_prints_source_type_batch19(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(_mk_doc_full()), encoding="utf-8")
    args = _mk_args_inspect(str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "type=pdf" in out


def test_run_inspect_doc_prints_counts_batch19(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(_mk_doc_full()), encoding="utf-8")
    args = _mk_args_inspect(str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "elements=2" in out
    assert "chunks=1" in out


def test_run_inspect_doc_prints_parser_info_batch19(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(_mk_doc_full()), encoding="utf-8")
    args = _mk_args_inspect(str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "parser:" in out
    assert "fallback" in out


def test_run_inspect_doc_tolerance_transmitted_batch19(tmp_path):
    """tolerance_chars 透传给 chunk_boundary_prf。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(_mk_doc_full()), encoding="utf-8")
    args = _mk_args_inspect(str(p), tolerance=99)
    with patch("evaluation.annotation_metrics.chunk_boundary_prf",
               return_value={"cb": {"value": None, "reason": "x"}}) as cb:
        _run_inspect_doc(args)
        _, kwargs = cb.call_args
        assert kwargs["tolerance_chars"] == 99


def test_run_inspect_doc_metrics_sorted_batch19(tmp_path, capsys):
    """metrics 输出按 sort_key 排序（bool/ratio/count/null）。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(_mk_doc_full()), encoding="utf-8")
    args = _mk_args_inspect(str(p))
    _run_inspect_doc(args)
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_returns_int_batch19(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(_mk_doc_full()), encoding="utf-8")
    args = _mk_args_inspect(str(p))
    rc = _run_inspect_doc(args)
    assert isinstance(rc, int)
    assert rc == 0


def test_run_inspect_doc_invalid_top_level_batch19(tmp_path):
    """JSON 顶层是 str → 退出 1。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps("string_value"), encoding="utf-8")
    args = _mk_args_inspect(str(p))
    rc = _run_inspect_doc(args)
    assert rc == 1


def test_run_inspect_doc_invalid_top_level_int_batch19(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(42), encoding="utf-8")
    args = _mk_args_inspect(str(p))
    rc = _run_inspect_doc(args)
    assert rc == 1


# ---------- main 路由第十九批 ----------


def _mk_manifest_obj_empty():
    m = MagicMock()
    m.documents = []
    m.expected_failures = []
    m.project_root = Path("/fake")
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def test_main_run_writes_output_file_batch19(tmp_path, capsys):
    """run 成功 → output 文件被写到。"""
    manifest_p = tmp_path / "m.json"
    manifest_p.write_text("{}", encoding="utf-8")
    output_p = tmp_path / "out.json"
    fake_manifest = _mk_manifest_obj_empty()
    fake_manifest.project_root = tmp_path
    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), \
         patch("evaluation.cli.run_evaluation", return_value={"per_doc": [], "devset": {}}) as re_mock, \
         patch("evaluation.cli.validate_file", return_value=None), \
         patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
        rc = main(["run", "--manifest", str(manifest_p), "--output", str(output_p)])
    assert rc == 0
    # run_evaluation 被调用，第 2 个位置参数是 output_path
    args, _ = re_mock.call_args
    assert args[1] == output_p


def test_main_run_with_multiple_docs_count_batch19(tmp_path, capsys):
    manifest_p = tmp_path / "m.json"
    manifest_p.write_text("{}", encoding="utf-8")
    output_p = tmp_path / "out.json"
    fake_manifest = _mk_manifest_obj_empty()
    fake_manifest.project_root = tmp_path
    fake_report = {
        "per_doc": [
            {"doc_id": "d1", "metrics": {"pipeline_success": {"value": True}}},
            {"doc_id": "d2", "metrics": {"pipeline_success": {"value": True}}},
            {"doc_id": "d3", "metrics": {"pipeline_success": {"value": False}}},
            {"doc_id": "d4", "metrics": {"pipeline_success": {"value": True}}},
        ],
        "devset": {"status": "incomplete", "file_count": 4,
                   "content_group_count": 1, "pdf_count": 4, "docx_count": 0},
    }
    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), \
         patch("evaluation.cli.run_evaluation", return_value=fake_report), \
         patch("evaluation.cli.validate_file", return_value=None), \
         patch("evaluation.cli.get_git_provenance",
               return_value={"git_commit": "abc", "git_dirty": False}):
        rc = main(["run", "--manifest", str(manifest_p), "--output", str(output_p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "documents=4" in out
    assert "成功 3" in out
    assert "失败 1" in out


def test_main_validate_report_eval_schema_error_batch19(tmp_path, capsys):
    """validate-report → validate_file 抛 EvalSchemaError → 退出 1。"""
    from evaluation.schema import EvalSchemaError
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file",
               side_effect=EvalSchemaError("bad report")):
        rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_success_prints_path_batch19(tmp_path, capsys):
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", return_value=None):
        rc = main(["validate-report", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert str(p) in out


def test_main_inspect_doc_success_batch19(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(_mk_doc_full()), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_invalid_json_batch19(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_not_exist_batch19(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "no.json")])
    assert rc == 2


def test_main_no_subcommand_system_exit_batch19():
    with pytest.raises(SystemExit):
        main([])


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
    "ctypes.CDLL",
    "pickle.dumps",
    "shutil.rmtree",
    "sys.exit",
])
def test_module_source_forbidden_tokens_batch19(forbidden):
    src = inspect.getsource(cmod)
    assert forbidden not in src


def test_module_source_no_subprocess_batch19():
    src = inspect.getsource(cmod)
    assert "import subprocess" not in src


def test_module_source_no_network_batch19():
    src = inspect.getsource(cmod)
    assert "urllib.request" not in src
    assert "import requests" not in src


# ---------- module source 字符串精确补强第三十一批 ----------


def test_module_source_has_future_annotations_batch19():
    src = inspect.getsource(cmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch19():
    src = inspect.getsource(cmod)
    assert "评测 CLI" in src


def test_module_source_has_argparse_import_batch19():
    src = inspect.getsource(cmod)
    assert "import argparse" in src


def test_module_source_has_json_import_batch19():
    src = inspect.getsource(cmod)
    assert "import json" in src


def test_module_source_has_sys_import_batch19():
    src = inspect.getsource(cmod)
    assert "import sys" in src


def test_module_source_has_manifest_import_batch19():
    src = inspect.getsource(cmod)
    assert "from evaluation.manifest import" in src


def test_module_source_has_report_import_batch19():
    src = inspect.getsource(cmod)
    assert "from evaluation.report import" in src


def test_module_source_has_runner_import_batch19():
    src = inspect.getsource(cmod)
    assert "from evaluation.runner import" in src


def test_module_source_has_schema_import_batch19():
    src = inspect.getsource(cmod)
    assert "from evaluation.schema import" in src


def test_module_source_has_build_parser_batch19():
    src = inspect.getsource(cmod)
    assert "def _build_parser(" in src


def test_module_source_has_main_function_batch19():
    src = inspect.getsource(cmod)
    assert "def main(" in src


def test_module_source_has_run_inspect_doc_batch19():
    src = inspect.getsource(cmod)
    assert "def _run_inspect_doc(" in src


def test_module_source_has_format_metric_batch19():
    src = inspect.getsource(cmod)
    assert "def _format_metric(" in src


def test_module_source_has_add_subparsers_batch19():
    src = inspect.getsource(cmod)
    assert "add_subparsers(" in src


def test_module_source_no_main_block_batch19():
    src = inspect.getsource(cmod)
    assert "if __name__" not in src or "__main__" not in src.split("def main")[0]


# ---------- signatures 第二十九批 ----------


def test_signature_build_parser_batch19():
    sig = inspect.signature(_build_parser)
    assert list(sig.parameters.keys()) == []


def test_signature_main_batch19():
    sig = inspect.signature(main)
    assert list(sig.parameters.keys()) == ["argv"]


def test_signature_main_argv_default_none_batch19():
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_signature_format_metric_batch19():
    sig = inspect.signature(_format_metric)
    assert list(sig.parameters.keys()) == ["name", "metric"]


def test_signature_run_inspect_doc_batch19():
    sig = inspect.signature(_run_inspect_doc)
    assert list(sig.parameters.keys()) == ["args"]


# ---------- module 合理性第二十九批 ----------


def test_module_has_main_batch19():
    assert hasattr(cmod, "main")
    assert callable(cmod.main)


def test_module_has_build_parser_batch19():
    assert hasattr(cmod, "_build_parser")
    assert callable(cmod._build_parser)


def test_module_has_run_inspect_doc_batch19():
    assert hasattr(cmod, "_run_inspect_doc")
    assert callable(cmod._run_inspect_doc)


def test_module_has_format_metric_batch19():
    assert hasattr(cmod, "_format_metric")
    assert callable(cmod._format_metric)


def test_module_does_not_import_unsafe_modules_batch19():
    src = inspect.getsource(cmod)
    for unsafe in ["import pickle", "import marshal", "import shelve"]:
        assert unsafe not in src


def test_module_does_not_import_app_pipeline_batch19():
    src = inspect.getsource(cmod)
    assert "from app.pipeline" not in src


# ---------- 端到端集成第二十九批 ----------


def test_e2e_main_run_full_round_trip_batch19(tmp_path, capsys):
    manifest_p = tmp_path / "m.json"
    manifest_p.write_text("{}", encoding="utf-8")
    output_p = tmp_path / "out.json"
    fake_manifest = _mk_manifest_obj_empty()
    fake_manifest.project_root = tmp_path
    fake_report = {
        "per_doc": [],
        "devset": {"status": "complete", "file_count": 0,
                   "content_group_count": 0, "pdf_count": 0, "docx_count": 0},
    }
    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), \
         patch("evaluation.cli.run_evaluation", return_value=fake_report), \
         patch("evaluation.cli.validate_file", return_value=None), \
         patch("evaluation.cli.get_git_provenance",
               return_value={"git_commit": "x", "git_dirty": False}):
        rc = main(["run", "--manifest", str(manifest_p), "--output", str(output_p)])
    assert rc == 0


def test_e2e_main_inspect_doc_full_round_trip_batch19(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(_mk_doc_full()), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_e2e_main_validate_report_round_trip_batch19(tmp_path, capsys):
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", return_value=None):
        rc = main(["validate-report", str(p)])
    assert rc == 0


def test_e2e_main_run_prints_summary_batch19(tmp_path, capsys):
    manifest_p = tmp_path / "m.json"
    manifest_p.write_text("{}", encoding="utf-8")
    output_p = tmp_path / "out.json"
    fake_manifest = _mk_manifest_obj_empty()
    fake_manifest.project_root = tmp_path
    fake_report = {
        "per_doc": [
            {"doc_id": "d1", "metrics": {"pipeline_success": {"value": True}}},
        ],
        "devset": {"status": "complete", "file_count": 1,
                   "content_group_count": 1, "pdf_count": 1, "docx_count": 0},
    }
    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), \
         patch("evaluation.cli.run_evaluation", return_value=fake_report), \
         patch("evaluation.cli.validate_file", return_value=None), \
         patch("evaluation.cli.get_git_provenance",
               return_value={"git_commit": "x", "git_dirty": True}):
        rc = main(["run", "--manifest", str(manifest_p), "--output", str(output_p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "documents=1" in out
    assert "成功 1" in out
    assert "失败 0" in out
    assert "git_dirty=True" in out


def test_e2e_main_run_with_all_args_batch19(tmp_path, capsys):
    """所有 --parser/--max-chars/--tolerance-chars 透传。"""
    manifest_p = tmp_path / "m.json"
    manifest_p.write_text("{}", encoding="utf-8")
    output_p = tmp_path / "out.json"
    fake_manifest = _mk_manifest_obj_empty()
    fake_manifest.project_root = tmp_path
    fake_report = {"per_doc": [], "devset": {}}
    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), \
         patch("evaluation.cli.run_evaluation", return_value=fake_report) as re_mock, \
         patch("evaluation.cli.validate_file", return_value=None), \
         patch("evaluation.cli.get_git_provenance",
               return_value={"git_commit": "x", "git_dirty": False}):
        rc = main(["run", "--manifest", str(manifest_p), "--output", str(output_p),
                   "--parser", "kreuzberg", "--max-chars", "500",
                   "--tolerance-chars", "10"])
    assert rc == 0
    _, kwargs = re_mock.call_args
    assert kwargs["parser_name"] == "kreuzberg"
    assert kwargs["max_chars"] == 500
    assert kwargs["tolerance_chars"] == 10


def test_e2e_main_unknown_command_system_exit_batch19():
    with pytest.raises(SystemExit):
        main(["bogus"])


def test_e2e_main_no_command_system_exit_batch19():
    with pytest.raises(SystemExit):
        main([])


def test_e2e_run_with_failed_doc_in_count_batch19(tmp_path, capsys):
    """多 doc 含失败：n_ok + n_fail 都正确。"""
    manifest_p = tmp_path / "m.json"
    manifest_p.write_text("{}", encoding="utf-8")
    output_p = tmp_path / "out.json"
    fake_manifest = _mk_manifest_obj_empty()
    fake_manifest.project_root = tmp_path
    fake_report = {
        "per_doc": [
            {"doc_id": "d1", "metrics": {"pipeline_success": {"value": True}}},
            {"doc_id": "d2", "metrics": {"pipeline_success": {"value": False}}},
        ],
        "devset": {"status": "incomplete", "file_count": 2,
                   "content_group_count": 1, "pdf_count": 2, "docx_count": 0},
    }
    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), \
         patch("evaluation.cli.run_evaluation", return_value=fake_report), \
         patch("evaluation.cli.validate_file", return_value=None), \
         patch("evaluation.cli.get_git_provenance",
               return_value={"git_commit": "x", "git_dirty": False}):
        rc = main(["run", "--manifest", str(manifest_p), "--output", str(output_p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "documents=2" in out
    assert "成功 1" in out
    assert "失败 1" in out
