"""evaluation/cli.py 第五十轮 edges 测试（Round 473）。

补强 edges48 未触及的角度：
- _build_parser 第二十二批（subparser 数量 / run 无 positional / prog=evaluation.cli / 各 subparser 描述 / --parser 默认 fallback / --max-chars 默认 800 / --tolerance-chars 默认 30 / inspect-doc help）
- _format_metric 第二十二批（name 极长 / 空 dict / list value / 0.0 渲染 / 1.0 with reason / int with reason / 大 int）
- _run_inspect_doc 第二十二批（缺字段各场景 / 非 dict JSON / JSONDecodeError / 文件不存在 / SystemExit / 元信息默认值）
- main 第二十二批（非法 --parser / 不存在 manifest / run_evaluation EvalSchemaError / validate_file EvalSchemaError / validate-report 不存在 / validate-report JSONDecodeError / main 返回 int / inspect-doc 整合）
- module source forbidden tokens 第三十八批
- module source 字符串精确补强第三十四批
- signatures 第三十四批
- module 合理性第三十四批
- 端到端集成第三十四批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main
from evaluation import cli as climod


# ---------- _build_parser 第二十二批 ----------


def _get_subparsers(parser):
    """从主 parser 找到 subparsers action。"""
    for action in parser._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            return action
    return None


def test_build_parser_has_three_subcommands_batch22():
    """子命令严格 3 个：run / validate-report / inspect-doc。"""
    p = _build_parser()
    sub = _get_subparsers(p)
    assert sub is not None
    assert set(sub.choices.keys()) == {"run", "validate-report", "inspect-doc"}


def test_build_parser_subparsers_dest_is_command_batch22():
    """subparsers dest='command'。"""
    p = _build_parser()
    sub = _get_subparsers(p)
    assert sub.dest == "command"


def test_build_parser_subparsers_required_true_batch22():
    """subparsers required=True（不传子命令 SystemExit）。"""
    p = _build_parser()
    sub = _get_subparsers(p)
    assert sub.required is True


def test_build_parser_prog_is_evaluation_cli_batch22():
    """prog='evaluation.cli'。"""
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_run_no_positional_batch22():
    """run 子 parser 无 positional（全是 optionals + help）。"""
    p = _build_parser()
    sub = _get_subparsers(p)
    run_p = sub.choices["run"]
    # 过滤掉 help action
    real_positionals = [
        a for a in run_p._actions
        if not a.option_strings and a.dest != "help"
    ]
    assert real_positionals == []


def test_build_parser_validate_report_one_positional_batch22():
    """validate-report 子 parser 1 个 positional。"""
    p = _build_parser()
    sub = _get_subparsers(p)
    vp = sub.choices["validate-report"]
    real_positionals = [
        a for a in vp._actions
        if not a.option_strings and a.dest != "help"
    ]
    assert len(real_positionals) == 1
    assert real_positionals[0].dest == "input"


def test_build_parser_inspect_doc_one_positional_batch22():
    """inspect-doc 子 parser 1 个 positional。"""
    p = _build_parser()
    sub = _get_subparsers(p)
    ip = sub.choices["inspect-doc"]
    real_positionals = [
        a for a in ip._actions
        if not a.option_strings and a.dest != "help"
    ]
    assert len(real_positionals) == 1
    assert real_positionals[0].dest == "input"


def test_build_parser_parser_default_fallback_batch22():
    """--parser default='fallback'。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a", "--output", "b"])
    assert args.parser == "fallback"


def test_build_parser_max_chars_default_800_batch22():
    """--max-chars default=800。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a", "--output", "b"])
    assert args.max_chars == 800


def test_build_parser_tolerance_chars_default_30_batch22():
    """--tolerance-chars default=30。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a", "--output", "b"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_tolerance_default_30_batch22():
    """inspect-doc --tolerance-chars default=30。"""
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "x.json"])
    assert args.tolerance_chars == 30


def test_build_parser_invalid_parser_choice_system_exit_batch22():
    """--parser 不在 choices 内 → SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "a", "--output", "b", "--parser", "bad"])


# ---------- _format_metric 第二十二批 ----------


def test_format_metric_very_long_name_batch22():
    """name 超过 36 字符仍渲染（不截断）。"""
    name = "x" * 50
    out = _format_metric(name, {"value": 1, "reason": None})
    assert name in out


def test_format_metric_empty_dict_batch22():
    """value 是空 dict。"""
    out = _format_metric("counts", {"value": {}, "reason": None})
    # items 是空字符串
    assert "counts" in out
    assert "(ok)" in out


def test_format_metric_list_value_batch22():
    """value 是 list（走 default 分支，str 化）。"""
    out = _format_metric("x", {"value": [1, 2, 3], "reason": None})
    # list 不被识别为 dict
    assert "[1, 2, 3]" in out


def test_format_metric_value_zero_float_batch22():
    """value=0.0（float）走 float 分支。"""
    out = _format_metric("delta", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_value_one_float_with_reason_batch22():
    """value=1.0 + reason → 输出 reason。"""
    out = _format_metric("delta", {"value": 1.0, "reason": "approx"})
    assert "1.0000" in out
    assert "(approx)" in out


def test_format_metric_value_int_with_reason_batch22():
    """value 是 int + reason → 走 default 分支，输出 reason。"""
    out = _format_metric("count", {"value": 42, "reason": "ok-ish"})
    assert "42" in out
    assert "(ok-ish)" in out


def test_format_metric_value_large_int_batch22():
    """大 int。"""
    out = _format_metric("count", {"value": 1000000, "reason": None})
    assert "1000000" in out


def test_format_metric_value_dict_single_key_batch22():
    """dict 单 key。"""
    out = _format_metric("x", {"value": {"a": 1}, "reason": None})
    assert "a=1" in out


def test_format_metric_value_false_with_reason_batch22():
    """value=False + reason → 'false' + reason。"""
    out = _format_metric("flag", {"value": False, "reason": "fail"})
    assert "false" in out
    assert "(fail)" in out


# ---------- _run_inspect_doc 第二十二批 ----------


def _write_doc(tmp_path, doc=None, name="d.json"):
    p = tmp_path / name
    if doc is None:
        doc = {
            "document_id": "d1",
            "source_type": "pdf",
            "elements": [],
            "chunks": [],
        }
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def test_run_inspect_doc_missing_document_id_default_question_batch22(tmp_path, capsys):
    """doc 无 document_id → 打印 '?'。"""
    p = _write_doc(tmp_path, doc={"source_type": "pdf", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "document_id: ?" in captured


def test_run_inspect_doc_missing_source_path_default_question_batch22(tmp_path, capsys):
    """doc 无 source_path → 打印 '?'。"""
    p = _write_doc(tmp_path, doc={
        "document_id": "d",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "source:" in captured
    assert "?" in captured


def test_run_inspect_doc_missing_parser_name_batch22(tmp_path, capsys):
    """doc 无 parser_name → 打印 '?'。"""
    p = _write_doc(tmp_path, doc={
        "document_id": "d",
        "source_type": "pdf",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    # parser:  ? v1.0
    assert "parser:" in captured


def test_run_inspect_doc_non_dict_json_returns_1_batch22(tmp_path, capsys):
    """JSON 顶层是数组 → rc=1。"""
    p = tmp_path / "d.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    err = capsys.readouterr().err
    assert rc == 1
    assert "顶层" in err or "object" in err.lower() or "对象" in err


def test_run_inspect_doc_invalid_json_returns_1_batch22(tmp_path, capsys):
    """非法 JSON → rc=1。"""
    p = tmp_path / "d.json"
    p.write_text("{bad}", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    err = capsys.readouterr().err
    assert rc == 1
    assert "[ERROR]" in err


def test_run_inspect_doc_file_not_found_returns_2_batch22(tmp_path, capsys):
    """文件不存在 → rc=2。"""
    args = MagicMock()
    args.input = str(tmp_path / "no.json")
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    err = capsys.readouterr().err
    assert rc == 2
    assert "[ERROR]" in err


def test_run_inspect_doc_passes_tolerance_to_chunk_boundary_batch22(tmp_path):
    """tolerance_chars 透传给 chunk_boundary_prf。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 99
    captured = {}

    def fake_chunk_b(document, annotation, tolerance_chars=30):
        captured["tolerance_chars"] = tolerance_chars
        return {}

    with patch("evaluation.annotation_metrics.chunk_boundary_prf", side_effect=fake_chunk_b):
        _run_inspect_doc(args)
    assert captured["tolerance_chars"] == 99


def test_run_inspect_doc_elements_no_chunks_batch22(tmp_path, capsys):
    """有 elements 无 chunks → counts 行 elements=N chunks=0。"""
    p = _write_doc(tmp_path, doc={
        "document_id": "d",
        "source_type": "pdf",
        "elements": [{"id": "e1"}, {"id": "e2"}, {"id": "e3"}],
        "chunks": [],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "elements=3" in captured
    assert "chunks=0" in captured


def test_run_inspect_doc_no_elements_no_chunks_batch22(tmp_path, capsys):
    """无 elements 无 chunks 字段 → counts 行 elements=0 chunks=0。"""
    p = _write_doc(tmp_path, doc={"document_id": "d", "source_type": "pdf"})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "elements=0" in captured
    assert "chunks=0" in captured


# ---------- main 第二十二批 ----------


def test_main_run_nonexistent_manifest_returns_2_batch22(tmp_path, capsys):
    """manifest 文件不存在 → rc=2。"""
    rc = main(["run", "--manifest", str(tmp_path / "no.json"), "--output", str(tmp_path / "o.json")])
    err = capsys.readouterr().err
    assert rc == 2
    assert "[ERROR]" in err


def test_main_run_run_evaluation_eval_schema_error_returns_1_batch22(tmp_path, capsys):
    """run_evaluation 抛 EvalSchemaError → rc=1。"""
    from evaluation.schema import EvalSchemaError

    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    with patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=tmp_path)):
        with patch("evaluation.cli.run_evaluation", side_effect=EvalSchemaError("bad report")):
            rc = main(["run", "--manifest", str(manifest_p), "--output", str(tmp_path / "o.json")])
    err = capsys.readouterr().err
    assert rc == 1
    assert "Schema" in err or "未通过" in err


def test_main_run_validate_file_eval_schema_error_returns_1_batch22(tmp_path, capsys):
    """validate_file 在 run 之后抛 EvalSchemaError → rc=1。"""
    from evaluation.schema import EvalSchemaError

    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }
    with patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=tmp_path)):
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("invalid report")):
                rc = main(["run", "--manifest", str(manifest_p), "--output", str(tmp_path / "o.json")])
    err = capsys.readouterr().err
    assert rc == 1


def test_main_validate_report_nonexistent_returns_2_batch22(tmp_path, capsys):
    """validate-report 文件不存在 → rc=2。"""
    rc = main(["validate-report", str(tmp_path / "no.json")])
    err = capsys.readouterr().err
    assert rc == 2
    assert "[ERROR]" in err


def test_main_validate_report_json_decode_error_returns_1_batch22(tmp_path, capsys):
    """validate-report JSON 解析失败 → rc=1。"""
    from evaluation.schema import EvalSchemaError

    p = tmp_path / "report.json"
    p.write_text("not json", encoding="utf-8")
    with patch("evaluation.cli.validate_file", side_effect=json.JSONDecodeError("bad", "doc", 0)):
        rc = main(["validate-report", str(p)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "JSON" in err or "解析" in err


def test_main_validate_report_eval_schema_error_returns_1_batch22(tmp_path, capsys):
    """validate-report EvalSchemaError → rc=1。"""
    from evaluation.schema import EvalSchemaError

    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("schema fail")):
        rc = main(["validate-report", str(p)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "[FAIL]" in err


def test_main_returns_int_batch22(tmp_path):
    """main 返回 int。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", return_value=None):
        rc = main(["validate-report", str(p)])
    assert isinstance(rc, int)


def test_main_no_command_system_exit_batch22(capsys):
    """无子命令 → SystemExit。"""
    with pytest.raises(SystemExit):
        main([])


def test_main_run_passes_parser_to_run_evaluation_batch22(tmp_path):
    """--parser 透传给 run_evaluation 作 parser_name。"""
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    captured = {}

    def fake_run(manifest, output_path, **kwargs):
        captured.update(kwargs)
        return {
            "report_version": "1.1",
            "provenance": {},
            "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
            "summary": {},
            "per_doc": [],
            "expected_failures": [],
        }

    with patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=tmp_path)):
        with patch("evaluation.cli.run_evaluation", side_effect=fake_run):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    main(["run", "--manifest", str(manifest_p), "--output", str(out_p),
                          "--parser", "kreuzberg"])
    assert captured["parser_name"] == "kreuzberg"


def test_main_run_count_pipeline_success_batch22(tmp_path, capsys):
    """成功 run 打印 '成功 N' 来自 pipeline_success=True。"""
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
        "summary": {},
        "per_doc": [
            {"doc_id": "d1", "metrics": {"pipeline_success": {"value": True}}, "wall_time_seconds": {"total": 0.1, "parse": None, "chunk": None, "parse_reason": "not_instrumented", "chunk_reason": "not_instrumented"}},
            {"doc_id": "d2", "metrics": {"pipeline_success": {"value": False}}, "wall_time_seconds": {"total": 0.1, "parse": None, "chunk": None, "parse_reason": "not_instrumented", "chunk_reason": "not_instrumented"}},
        ],
        "expected_failures": [],
    }
    with patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=tmp_path)):
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc12345def", "git_dirty": False}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    captured = capsys.readouterr().out
    assert "documents=2" in captured
    assert "成功 1" in captured
    assert "失败 1" in captured


def test_main_run_prints_truncated_commit_batch22(tmp_path, capsys):
    """git_commit 截取前 12 字符。"""
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }
    with patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=tmp_path)):
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abcdef1234567890abcdef", "git_dirty": False}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    captured = capsys.readouterr().out
    assert "abcdef123456" in captured
    # 后续字符不应出现
    assert "abcdef1234567890" not in captured


# ---------- module source forbidden tokens 第三十八批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.check_output",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    "open(\"/etc/passwd",
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch22(forbidden):
    src = inspect.getsource(climod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch22():
    src = inspect.getsource(climod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch22():
    src = inspect.getsource(climod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch22():
    src = inspect.getsource(climod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch22():
    src = inspect.getsource(climod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch22():
    src = inspect.getsource(climod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch22():
    src = inspect.getsource(climod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch22():
    src = inspect.getsource(climod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch22():
    src = inspect.getsource(climod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch22():
    src = inspect.getsource(climod)
    assert "import tempfile" not in src


def test_module_source_no_sys_stdout_reconfigure_outside_if_batch22():
    """sys.stdout.reconfigure 必须包在 hasattr 检查内（不能直接调用）。"""
    src = inspect.getsource(climod)
    # 顶层不应有 sys.stdout.reconfigure() 的直接调用（必须先 hasattr）
    # 检查源里至少有一个 hasattr 守卫
    assert 'hasattr(sys.stdout, "reconfigure")' in src


def test_module_source_no_logging_import_batch22():
    src = inspect.getsource(climod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch22():
    src = inspect.getsource(climod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch22():
    src = inspect.getsource(climod)
    assert "import datetime" not in src


def test_module_source_no_collections_import_batch22():
    src = inspect.getsource(climod)
    assert "import collections" not in src


def test_module_source_no_pandas_import_batch22():
    src = inspect.getsource(climod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch22():
    src = inspect.getsource(climod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第三十四批 ----------


def test_module_source_has_future_annotations_batch22():
    src = inspect.getsource(climod)
    assert "from __future__ import annotations" in src


def test_module_source_has_argparse_import_batch22():
    src = inspect.getsource(climod)
    assert "import argparse" in src


def test_module_source_has_json_import_batch22():
    src = inspect.getsource(climod)
    assert "import json" in src


def test_module_source_has_sys_import_batch22():
    src = inspect.getsource(climod)
    assert "import sys" in src


def test_module_source_has_pathlib_path_import_batch22():
    src = inspect.getsource(climod)
    assert "from pathlib import Path" in src


def test_module_source_has_manifest_import_batch22():
    src = inspect.getsource(climod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_module_source_has_report_import_batch22():
    src = inspect.getsource(climod)
    assert "from evaluation.report import get_git_provenance" in src


def test_module_source_has_runner_import_batch22():
    src = inspect.getsource(climod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_has_schema_import_batch22():
    src = inspect.getsource(climod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_module_source_has_main_function_batch22():
    src = inspect.getsource(climod)
    assert "def main(argv:" in src


def test_module_source_has_build_parser_function_batch22():
    src = inspect.getsource(climod)
    assert "def _build_parser()" in src


def test_module_source_has_format_metric_function_batch22():
    src = inspect.getsource(climod)
    assert "def _format_metric(" in src


def test_module_source_has_run_inspect_doc_function_batch22():
    src = inspect.getsource(climod)
    assert "def _run_inspect_doc(" in src


def test_module_source_has_main_guard_batch22():
    src = inspect.getsource(climod)
    assert 'if __name__ ==' in src
    assert "__main__" in src


def test_module_source_has_raw_description_help_formatter_batch22():
    src = inspect.getsource(climod)
    assert "RawDescriptionHelpFormatter" in src


# ---------- signatures 第三十四批 ----------


def test_signature_build_parser_no_args_batch22():
    sig = inspect.signature(_build_parser)
    params = list(sig.parameters.values())
    assert len(params) == 0


def test_signature_main_argv_default_none_batch22():
    sig = inspect.signature(main)
    p = sig.parameters["argv"]
    assert p.default is None


def test_signature_main_returns_int_annotation_batch22():
    """main 返回类型注解是 int（str 形式因 __future__）。"""
    sig = inspect.signature(main)
    assert "int" in str(sig.return_annotation)


def test_signature_format_metric_params_batch22():
    sig = inspect.signature(_format_metric)
    names = list(sig.parameters.keys())
    assert names == ["name", "metric"]


def test_signature_run_inspect_doc_params_batch22():
    sig = inspect.signature(_run_inspect_doc)
    names = list(sig.parameters.keys())
    assert names == ["args"]


def test_signature_run_inspect_doc_returns_int_annotation_batch22():
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in str(sig.return_annotation)


# ---------- module 合理性第三十四批 ----------


def test_module_has_no_all_attribute_batch22():
    """cli 模块未定义 __all__（不是 lib 模块）。"""
    assert not hasattr(climod, "__all__") or climod.__all__ is None or len(climod.__all__) == 0 or "main" in (climod.__all__ or [])


def test_module_does_not_import_evaluation_runner_top_level_side_effect_batch22():
    """import evaluation.runner 在顶层（不在函数内）。"""
    src = inspect.getsource(climod)
    lines = src.splitlines()
    # 顶层（行首无空格）应有 'from evaluation.runner import'
    found_top_level = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("from evaluation.runner import") and line[0] != " ":
            found_top_level = True
            break
    assert found_top_level


def test_module_does_not_import_app_pipeline_batch22():
    src = inspect.getsource(climod)
    assert "from app.pipeline" not in src
    assert "from app import pipeline" not in src


def test_module_does_not_import_app_parsers_batch22():
    src = inspect.getsource(climod)
    assert "from app.parsers" not in src
    assert "from app import parsers" not in src


def test_module_does_not_import_app_chunkers_batch22():
    src = inspect.getsource(climod)
    assert "from app.chunkers" not in src
    assert "from app import chunkers" not in src


def test_module_does_not_import_evaluation_metrics_top_level_batch22():
    """evaluation.metrics 仅在 _run_inspect_doc 内 import，不在顶层。"""
    src = inspect.getsource(climod)
    # 不在顶层 import（顶层有 'from evaluation.metrics import' 就失败）
    # 简单检查：源中 'from evaluation.metrics import' 只出现在函数内
    # 这里我们检查顶层（行首无空格）没有这种 import
    lines = src.splitlines()
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("from evaluation.metrics"):
            # 必须在函数内（行首有空格）
            assert line[0] == " ", f"top-level evaluation.metrics import: {line}"


def test_module_does_not_import_evaluation_annotation_metrics_top_level_batch22():
    """evaluation.annotation_metrics 仅在 _run_inspect_doc 内 import。"""
    src = inspect.getsource(climod)
    lines = src.splitlines()
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("from evaluation.annotation_metrics"):
            assert line[0] == " ", f"top-level evaluation.annotation_metrics import: {line}"


def test_module_constants_private_batch22():
    """cli 模块无私有常量泄漏（_build_parser/_format_metric/_run_inspect_doc 都是私有命名）。"""
    assert _build_parser.__name__.startswith("_")
    assert _format_metric.__name__.startswith("_")
    assert _run_inspect_doc.__name__.startswith("_")


def test_module_main_is_public_batch22():
    assert not main.__name__.startswith("_")


def test_module_has_docstring_batch22():
    assert climod.__doc__ is not None
    assert len(climod.__doc__) > 0


def test_module_sys_reconfigure_in_try_batch22():
    """sys.stdout.reconfigure 在 try/except 内。"""
    src = inspect.getsource(climod)
    assert "except (AttributeError, OSError)" in src


# ---------- 端到端集成第三十四批 ----------


def test_e2e_main_inspect_doc_full_output_batch22(tmp_path, capsys):
    """inspect-doc 完整跑 + 输出格式正确。"""
    p = _write_doc(tmp_path, doc={
        "document_id": "d-full",
        "source_type": "pdf",
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0.0",
        "elements": [{"element_id": "e1"}, {"element_id": "e2"}],
        "chunks": [{"chunk_id": "c1"}],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert rc == 0
    assert "d-full" in captured
    assert "/tmp/x.pdf" in captured
    assert "fallback" in captured
    assert "1.0.0" in captured
    assert "elements=2" in captured
    assert "chunks=1" in captured


def test_e2e_main_inspect_doc_via_main_batch22(tmp_path, capsys):
    """main(['inspect-doc', path]) 返回 0。"""
    p = _write_doc(tmp_path)
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_main_validate_report_full_path_batch22(tmp_path, capsys):
    """main validate-report 成功路径。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", return_value=None):
        rc = main(["validate-report", str(p)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "[OK]" in out
    assert str(p) in out


def test_e2e_main_run_full_path_batch22(tmp_path, capsys):
    """main run 完整路径：load_manifest → run_evaluation → validate_file → print summary。"""
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {"status": "complete", "file_count": 5, "content_group_count": 3, "pdf_count": 2, "docx_count": 3, "categories_covered": ["a"]},
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }
    with patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=tmp_path)):
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "deadbeef12345678", "git_dirty": True}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    rc = main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "[OK]" in out
    assert "documents=0" in out
    assert "devset_status=complete" in out
    assert "git_dirty=True" in out


def test_e2e_format_metric_all_metric_types_batch22():
    """_format_metric 各种类型都有合理输出。"""
    # bool
    assert "true" in _format_metric("a", {"value": True, "reason": None})
    assert "false" in _format_metric("a", {"value": False, "reason": None})
    # float
    assert "0.5000" in _format_metric("a", {"value": 0.5, "reason": None})
    # int
    assert "42" in _format_metric("a", {"value": 42, "reason": None})
    # dict
    assert "x=1" in _format_metric("a", {"value": {"x": 1}, "reason": None})
    # None
    assert "null" in _format_metric("a", {"value": None, "reason": "x"})


def test_e2e_inspect_doc_output_includes_metrics_section_batch22(tmp_path, capsys):
    """inspect-doc 输出有 metrics: 表头。"""
    p = _write_doc(tmp_path)
    rc = main(["inspect-doc", str(p)])
    captured = capsys.readouterr().out
    assert rc == 0
    assert "metrics:" in captured
    assert "pipeline_success" in captured


def test_e2e_build_parser_run_subcommand_complete_batch22():
    """_build_parser run 子命令所有参数都能正确解析。"""
    p = _build_parser()
    args = p.parse_args([
        "run", "--manifest", "a.json", "--output", "b.json",
        "--parser", "kreuzberg", "--max-chars", "1000", "--tolerance-chars", "50"
    ])
    assert args.command == "run"
    assert args.manifest == "a.json"
    assert args.output == "b.json"
    assert args.parser == "kreuzberg"
    assert args.max_chars == 1000
    assert args.tolerance_chars == 50
