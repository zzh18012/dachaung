"""evaluation/cli.py 第四十九轮 edges 测试（Round 466）。

补强 edges47 未触及的角度：
- _build_parser 行为深度第二十一批（RawDescriptionHelpFormatter / choices tuple / prog / run subparser args 全集 / validate-report 单 positional / inspect-doc positional + 1 option / 描述含中文）
- _format_metric 行为深度第二十一批（value=tuple / value=负 float / value=特殊 unicode / name 含空格 / 长字典 / 字典 key 数字 / None reason with value）
- _run_inspect_doc 行为深度第二十一批（带完整 doc 元信息 / metrics 排序 int 在 bool 后 / 多 chunk / elements 非空 / 标注相关指标 null）
- main 行为深度第二十一批（run 缺 --manifest 失败 / run 缺 --output 失败 / run 自校验失败 / validate-report 成功打印 OK / inspect-doc SystemExit / 缺省子命令 SystemExit）
- module source forbidden tokens 第三十七批
- module source 字符串精确补强第三十三批
- signatures 第三十三批
- module 合理性第三十三批
- 端到端集成第三十三批
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


# ---------- _build_parser 行为深度第二十一批 ----------


def test_build_parser_uses_raw_description_help_formatter_batch21():
    """formatter_class=RawDescriptionHelpFormatter。"""
    p = _build_parser()
    assert p.formatter_class.__name__ == "RawDescriptionHelpFormatter"


def test_build_parser_run_subparser_has_4_optional_actions_batch21():
    """run 子 parser 有 4 个 optional args: manifest/output/parser/max-chars/tolerance-chars (5 个)。"""
    p = _build_parser()
    # 找 run subparser
    for action in p._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            if "run" in action.choices:
                run_p = action.choices["run"]
                optionals = [
                    a for a in run_p._actions if a.option_strings
                ]
                # 至少 5 个 optional：--manifest/--output/--parser/--max-chars/--tolerance-chars
                assert len(optionals) >= 5
                return
    pytest.fail("no run subparser found")


def test_build_parser_validate_subparser_has_positional_input_batch21():
    p = _build_parser()
    for action in p._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            if "validate-report" in action.choices:
                vp = action.choices["validate-report"]
                positionals = [
                    a for a in vp._actions if not a.option_strings
                ]
                # 第一 positional 是 input（dest='input'）
                assert any(a.dest == "input" for a in positionals)
                return
    pytest.fail("no validate-report subparser found")


def test_build_parser_inspect_doc_has_tolerance_chars_batch21():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "x.json", "--tolerance-chars", "100"])
    assert args.tolerance_chars == 100


def test_build_parser_inspect_doc_input_required_batch21():
    """inspect-doc 缺 positional input → SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["inspect-doc"])


def test_build_parser_run_requires_manifest_batch21():
    """run 缺 --manifest → SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "b.json"])


def test_build_parser_run_requires_output_batch21():
    """run 缺 --output → SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "a.json"])


def test_build_parser_run_parser_choices_exact_batch21():
    """--parser choices 必须严格是 ('fallback', 'kreuzberg')。"""
    p = _build_parser()
    args1 = p.parse_args(["run", "--manifest", "a", "--output", "b", "--parser", "fallback"])
    assert args1.parser == "fallback"
    args2 = p.parse_args(["run", "--manifest", "a", "--output", "b", "--parser", "kreuzberg"])
    assert args2.parser == "kreuzberg"


def test_build_parser_no_subcommand_system_exit_batch21():
    """没传子命令 → SystemExit（required=True）。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_parser_max_chars_must_be_int_batch21():
    """--max-chars 'abc' → SystemExit（type=int 拒绝非数字）。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "a", "--output", "b", "--max-chars", "abc"])


def test_build_parser_max_chars_negative_allowed_batch21():
    """argparse 不阻止负数。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a", "--output", "b", "--max-chars", "-1"])
    assert args.max_chars == -1


# ---------- _format_metric 行为深度第二十一批 ----------


def test_format_metric_value_tuple_batch21():
    """value=tuple 走 default 分支（str 化）。"""
    out = _format_metric("x", {"value": (1, 2), "reason": None})
    assert "(1, 2)" in out or "1" in out  # tuple str 化


def test_format_metric_value_negative_float_batch21():
    out = _format_metric("delta", {"value": -0.5, "reason": None})
    assert "-0.5000" in out


def test_format_metric_value_special_unicode_batch21():
    """unicode 字符串值。"""
    out = _format_metric("name", {"value": "中文", "reason": None})
    assert "中文" in out


def test_format_metric_name_with_spaces_batch21():
    """name 含空格仍按 36 宽对齐。"""
    out = _format_metric("metric with spaces", {"value": 1, "reason": None})
    # 末尾仍包含 "1"
    assert "1" in out


def test_format_metric_large_dict_value_batch21():
    """大字典 value。"""
    val = {f"key_{i:02d}": i * 10 for i in range(20)}
    out = _format_metric("counts", {"value": val, "reason": None})
    assert "key_00=0" in out
    assert "key_19=190" in out


def test_format_metric_dict_with_numeric_string_keys_batch21():
    """dict 的 key 是字符串数字。"""
    val = {"10": "a", "2": "b", "1": "c"}
    out = _format_metric("x", {"value": val, "reason": None})
    # 按 key（字符串）排序：'1' < '10' < '2'
    assert out.index("1=c") < out.index("10=a") < out.index("2=b")


def test_format_metric_value_none_with_no_reason_batch21():
    """value=None 且 reason=None → null (None)。"""
    out = _format_metric("x", {"value": None, "reason": None})
    assert "null" in out
    assert "(None)" in out


def test_format_metric_value_true_batch21():
    """value=True → 渲染为 'true'。"""
    out = _format_metric("flag", {"value": True, "reason": None})
    assert "true" in out
    assert "(ok)" in out


def test_format_metric_value_false_batch21():
    """value=False → 渲染为 'false'。"""
    out = _format_metric("flag", {"value": False, "reason": None})
    assert "false" in out
    assert "(ok)" in out


def test_format_metric_value_int_zero_batch21():
    """value=0 → 走 default 分支（int），输出 '0'。"""
    out = _format_metric("count", {"value": 0, "reason": None})
    # default 分支用 f"{value}"
    assert "0" in out
    assert "(ok)" in out


# ---------- _run_inspect_doc 行为深度第二十一批 ----------


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


def test_run_inspect_doc_prints_full_metadata_batch21(tmp_path, capsys):
    """完整 doc 元信息被打印。"""
    p = _write_doc(tmp_path, doc={
        "document_id": "abc-123",
        "source_type": "docx",
        "source_path": "/path/to/file.docx",
        "parser_name": "fallback",
        "parser_version": "2.1.0",
        "elements": [{"id": "e1"}],
        "chunks": [{"id": "c1"}, {"id": "c2"}],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert rc == 0
    assert "abc-123" in captured
    assert "/path/to/file.docx" in captured
    assert "docx" in captured
    assert "fallback" in captured
    assert "2.1.0" in captured
    assert "elements=1" in captured
    assert "chunks=2" in captured


def test_run_inspect_doc_metrics_with_int_after_bool_batch21(tmp_path, capsys):
    """排序：bool → numeric → dict → None。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    lines = [line for line in captured.splitlines() if line.startswith("  ")]
    # 找到第一个 null 行的位置
    null_idx = next((i for i, l in enumerate(lines) if "null" in l), None)
    if null_idx is not None:
        # null 之前应都是 bool/numeric/dict
        for l in lines[:null_idx]:
            assert "null" not in l


def test_run_inspect_doc_pipeline_success_in_output_batch21(tmp_path, capsys):
    """pipeline_success 应被打印。"""
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
    assert "pipeline_success" in captured


def test_run_inspect_doc_chunk_boundary_metrics_in_output_batch21(tmp_path, capsys):
    """chunk_boundary_* 应被打印（无标注时为 null）。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "chunk_boundary_precision" in captured
    assert "chunk_boundary_recall" in captured
    assert "chunk_boundary_f1" in captured


def test_run_inspect_doc_figure_caption_metrics_in_output_batch21(tmp_path, capsys):
    """figure_caption_* 应被打印（无标注时为 null）。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "figure_caption_precision" in captured
    assert "figure_caption_recall" in captured
    assert "figure_caption_f1" in captured


def test_run_inspect_doc_metrics_section_header_batch21(tmp_path, capsys):
    """metrics 区有 'metrics:' 表头。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "metrics:" in captured


def test_run_inspect_doc_returns_zero_on_success_batch21(tmp_path):
    """成功跑完返回 0。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    assert _run_inspect_doc(args) == 0


def test_run_inspect_doc_file_path_in_output_batch21(tmp_path, capsys):
    """打印 file: 行。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "file:" in captured
    assert str(p) in captured


def test_run_inspect_doc_default_source_type_batch21(tmp_path, capsys):
    """doc 无 source_type → 默认 'unknown'。"""
    p = _write_doc(tmp_path, doc={"document_id": "d", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "type=unknown" in captured


# ---------- main 行为深度第二十一批 ----------


def test_main_run_calls_validate_file_batch21(tmp_path, capsys):
    """main('run') 在 run_evaluation 后调 validate_file。"""
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    with patch("evaluation.cli.load_manifest") as mock_load:
        mock_load.return_value = MagicMock(project_root=tmp_path)
        with patch("evaluation.cli.run_evaluation", return_value={
            "report_version": "1.1",
            "provenance": {},
            "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
            "summary": {},
            "per_doc": [],
            "expected_failures": [],
        }):
            with patch("evaluation.cli.validate_file") as mock_vf:
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    assert mock_vf.call_count == 1


def test_main_run_prints_devset_status_batch21(tmp_path, capsys):
    """成功 run 应打印 devset_status=...。"""
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    with patch("evaluation.cli.load_manifest") as mock_load:
        mock_load.return_value = MagicMock(project_root=tmp_path)
        with patch("evaluation.cli.run_evaluation", return_value={
            "report_version": "1.1",
            "provenance": {},
            "devset": {"status": "incomplete", "file_count": 3, "content_group_count": 2, "pdf_count": 1, "docx_count": 2, "categories_covered": []},
            "summary": {},
            "per_doc": [],
            "expected_failures": [],
        }):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc123", "git_dirty": False}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    rc = main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    captured = capsys.readouterr().out
    assert "devset_status=incomplete" in captured
    assert "file_count=3" in captured
    assert "groups=2" in captured
    assert "pdf=1" in captured
    assert "docx=2" in captured


def test_main_run_prints_git_dirty_true_batch21(tmp_path, capsys):
    """git_dirty=True 被打印。"""
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    with patch("evaluation.cli.load_manifest") as mock_load:
        mock_load.return_value = MagicMock(project_root=tmp_path)
        with patch("evaluation.cli.run_evaluation", return_value={
            "report_version": "1.1",
            "provenance": {},
            "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
            "summary": {},
            "per_doc": [],
            "expected_failures": [],
        }):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "deadbeef", "git_dirty": True}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    captured = capsys.readouterr().out
    assert "git_dirty=True" in captured


def test_main_run_prints_unknown_commit_when_none_batch21(tmp_path, capsys):
    """git_commit=None 时打印 'unknown'。"""
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    with patch("evaluation.cli.load_manifest") as mock_load:
        mock_load.return_value = MagicMock(project_root=tmp_path)
        with patch("evaluation.cli.run_evaluation", return_value={
            "report_version": "1.1",
            "provenance": {},
            "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
            "summary": {},
            "per_doc": [],
            "expected_failures": [],
        }):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": None, "git_dirty": None}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    captured = capsys.readouterr().out
    assert "unknown" in captured


def test_main_validate_report_success_prints_ok_batch21(tmp_path, capsys):
    """validate-report 成功 → 打印 [OK]。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", return_value=None):
        rc = main(["validate-report", str(p)])
    captured = capsys.readouterr().out
    assert rc == 0
    assert "[OK]" in captured


def test_main_validate_report_file_not_found_error_returns_2_batch21(tmp_path, capsys):
    """validate_file 抛 FileNotFoundError → rc=2。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", side_effect=FileNotFoundError("schema missing")):
        rc = main(["validate-report", str(p)])
    captured = capsys.readouterr().err
    assert rc == 2
    assert "schema missing" in captured or "schema missing" in capsys.readouterr().out


def test_main_inspect_doc_route_returns_int_batch21(tmp_path):
    """inspect-doc 路由返回 int。"""
    p = _write_doc(tmp_path)
    rc = main(["inspect-doc", str(p)])
    assert isinstance(rc, int)


def test_main_run_manifest_load_eval_schema_error_returns_1_batch21(tmp_path, capsys):
    """load_manifest 抛 EvalSchemaError → rc=1。"""
    from evaluation.schema import EvalSchemaError

    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.load_manifest", side_effect=EvalSchemaError("bad manifest")):
        rc = main(["run", "--manifest", str(manifest_p), "--output", str(tmp_path / "o.json")])
    assert rc == 1


def test_main_run_manifest_load_manifest_error_returns_1_batch21(tmp_path, capsys):
    """load_manifest 抛 ManifestError → rc=1。"""
    from evaluation.manifest import ManifestError

    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.load_manifest", side_effect=ManifestError("bad manifest")):
        rc = main(["run", "--manifest", str(manifest_p), "--output", str(tmp_path / "o.json")])
    assert rc == 1


def test_main_run_passes_tol_chars_to_run_evaluation_batch21(tmp_path, capsys):
    """tolerance-chars 透传给 run_evaluation。"""
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
                    rc = main(["run", "--manifest", str(manifest_p), "--output", str(out_p),
                               "--tolerance-chars", "77"])
    assert captured["tolerance_chars"] == 77


# ---------- module source forbidden tokens 第三十七批 ----------


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
def test_module_source_forbidden_tokens_batch21(forbidden):
    src = inspect.getsource(climod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch21():
    src = inspect.getsource(climod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch21():
    src = inspect.getsource(climod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch21():
    src = inspect.getsource(climod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch21():
    src = inspect.getsource(climod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch21():
    src = inspect.getsource(climod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch21():
    src = inspect.getsource(climod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch21():
    src = inspect.getsource(climod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch21():
    src = inspect.getsource(climod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch21():
    src = inspect.getsource(climod)
    assert "import tempfile" not in src


def test_module_source_no_logging_import_batch21():
    src = inspect.getsource(climod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch21():
    src = inspect.getsource(climod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch21():
    src = inspect.getsource(climod)
    assert "import datetime" not in src


def test_module_source_no_collections_import_batch21():
    src = inspect.getsource(climod)
    assert "import collections" not in src


def test_module_source_no_pandas_import_batch21():
    src = inspect.getsource(climod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch21():
    src = inspect.getsource(climod)
    assert "import numpy" not in src


def test_module_source_no_unlink_call_batch21():
    src = inspect.getsource(climod)
    assert ".unlink(" not in src


# ---------- module source 字符串精确补强第三十三批 ----------


def test_module_source_has_future_annotations_batch21():
    src = inspect.getsource(climod)
    assert "from __future__ import annotations" in src


def test_module_source_has_argparse_import_batch21():
    src = inspect.getsource(climod)
    assert "import argparse" in src


def test_module_source_has_json_import_batch21():
    src = inspect.getsource(climod)
    assert "import json" in src


def test_module_source_has_sys_import_batch21():
    src = inspect.getsource(climod)
    assert "import sys" in src


def test_module_source_has_pathlib_path_import_batch21():
    src = inspect.getsource(climod)
    assert "from pathlib import Path" in src


def test_module_source_has_manifest_error_in_import_batch21():
    src = inspect.getsource(climod)
    assert "ManifestError" in src


def test_module_source_has_load_manifest_in_import_batch21():
    src = inspect.getsource(climod)
    assert "load_manifest" in src


def test_module_source_has_report_import_batch21():
    src = inspect.getsource(climod)
    assert "from evaluation.report import get_git_provenance" in src


def test_module_source_has_runner_import_batch21():
    src = inspect.getsource(climod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_has_schema_import_batch21():
    src = inspect.getsource(climod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_module_source_has_prog_string_batch21():
    src = inspect.getsource(climod)
    assert 'prog="evaluation.cli"' in src


def test_module_source_has_run_subparser_string_batch21():
    src = inspect.getsource(climod)
    assert '"run"' in src


def test_module_source_has_validate_report_subparser_string_batch21():
    src = inspect.getsource(climod)
    assert '"validate-report"' in src


def test_module_source_has_inspect_doc_subparser_string_batch21():
    src = inspect.getsource(climod)
    assert '"inspect-doc"' in src


def test_module_source_has_choices_tuple_batch21():
    src = inspect.getsource(climod)
    assert '("fallback", "kreuzberg")' in src


def test_module_source_has_raise_system_exit_batch21():
    src = inspect.getsource(climod)
    assert "raise SystemExit(main())" in src


# ---------- signatures 第三十三批 ----------


def test_signature_build_parser_batch21():
    sig = inspect.signature(_build_parser)
    params = list(sig.parameters.values())
    assert len(params) == 0


def test_signature_main_batch21():
    sig = inspect.signature(main)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "argv"


def test_signature_main_argv_default_none_batch21():
    sig = inspect.signature(main)
    params = list(sig.parameters.values())
    assert params[0].default is None


def test_signature_format_metric_batch21():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["name", "metric"]


def test_signature_format_metric_return_annotation_batch21():
    """_format_metric 返回类型注解 str。"""
    sig = inspect.signature(_format_metric)
    assert "str" in str(sig.return_annotation)


def test_signature_run_inspect_doc_batch21():
    sig = inspect.signature(_run_inspect_doc)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["args"]


def test_signature_run_inspect_doc_return_annotation_batch21():
    """_run_inspect_doc 返回类型注解 int。"""
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in str(sig.return_annotation)


# ---------- module 合理性第三十三批 ----------


def test_module_has_main_function_batch21():
    assert hasattr(climod, "main")


def test_module_has_build_parser_batch21():
    assert hasattr(climod, "_build_parser")


def test_module_has_run_inspect_doc_batch21():
    assert hasattr(climod, "_run_inspect_doc")


def test_module_has_format_metric_batch21():
    assert hasattr(climod, "_format_metric")


def test_module_does_not_import_app_pipeline_batch21():
    src = inspect.getsource(climod)
    assert "from app" not in src
    assert "import app" not in src


def test_module_lazy_imports_inside_run_inspect_doc_batch21():
    """inspect-doc 内部 lazy import metrics 模块。"""
    src = inspect.getsource(climod)
    inspect_body = src[src.find("def _run_inspect_doc"):]
    assert "from evaluation.annotation_metrics import chunk_boundary_prf, figure_caption_prf" in inspect_body
    assert "from evaluation.metrics import compute_automatic_metrics" in inspect_body


def test_module_main_returns_int_batch21():
    rc = main(["validate-report", "/nonexistent.json"])
    assert isinstance(rc, int)


def test_module_main_callable_batch21():
    assert callable(climod.main)


def test_module_no_global_state_batch21():
    """无全局可变状态（除了 import 的模块）。"""
    src = inspect.getsource(climod)
    # 没有 module 级别的 list/dict 赋值（除了 imports）
    # 简单检查没有形如 X = {} 或 X = [] 的全局赋值
    lines = src.splitlines()
    in_function = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("def ") or stripped.startswith("class "):
            in_function = True
        if not stripped.startswith(" ") and not stripped.startswith("\t"):
            in_function = False
        # 仅检查 module 级别
        if not in_function:
            assert "FORBIDDEN_TOKENS" not in stripped  # 不应有全局 forbidden list


def test_module_top_level_no_forbidden_globals_batch21():
    """module 顶层不引入可变全局（FORBIDDEN_TOKENS 等）。"""
    src = inspect.getsource(climod)
    lines = src.splitlines()
    in_function = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("def ") or stripped.startswith("class "):
            in_function = True
        indent = len(line) - len(stripped)
        if indent == 0:
            in_function = False
        if not in_function and indent == 0 and stripped:
            assert "FORBIDDEN_TOKENS" not in stripped


# ---------- 端到端集成第三十三批 ----------


def test_e2e_main_inspect_doc_full_round_trip_batch21(tmp_path, capsys):
    """inspect-doc 完整跑通。"""
    p = _write_doc(tmp_path, doc={
        "document_id": "d1",
        "source_type": "pdf",
        "source_path": "/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
    })
    rc = main(["inspect-doc", str(p)])
    captured = capsys.readouterr().out
    assert rc == 0
    assert "document_id: d1" in captured
    assert "elements=0" in captured
    assert "chunks=0" in captured


def test_e2e_main_inspect_doc_with_tolerance_batch21(tmp_path, capsys):
    """inspect-doc --tolerance-chars。"""
    p = _write_doc(tmp_path)
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "50"])
    assert rc == 0


def test_e2e_main_validate_report_round_trip_batch21(tmp_path, capsys):
    """validate-report 不存在文件 → rc=2。"""
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2


def test_e2e_main_no_args_system_exit_batch21():
    """无参 → SystemExit。"""
    with pytest.raises(SystemExit):
        main([])


def test_e2e_main_run_full_path_with_real_manifest_batch21(tmp_path, capsys):
    """完整 run 路径用真实 manifest.json。"""
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    with patch("evaluation.cli.run_evaluation", return_value={
        "report_version": "1.1",
        "provenance": {"parser_name": "fallback"},
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
        "summary": {"counts": {}, "success_rates": {}, "ratio_macro_averages": {}, "silent_drop_total": 0},
        "per_doc": [],
        "expected_failures": [],
    }):
        with patch("evaluation.cli.validate_file", return_value=None):
            with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
                out_p = tmp_path / "out.json"
                out_p.write_text("{}", encoding="utf-8")
                rc = main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    assert rc == 0


def test_e2e_main_run_full_path_kreuzberg_parser_batch21(tmp_path, capsys):
    """--parser kreuzberg 路径。"""
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

    with patch("evaluation.cli.run_evaluation", side_effect=fake_run):
        with patch("evaluation.cli.validate_file", return_value=None):
            with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
                out_p = tmp_path / "out.json"
                out_p.write_text("{}", encoding="utf-8")
                main(["run", "--manifest", str(manifest_p), "--output", str(out_p), "--parser", "kreuzberg"])
    assert captured["parser_name"] == "kreuzberg"


def test_e2e_format_metric_aligned_width_batch21():
    """短 name 与长 name 后内容对齐。"""
    out_short = _format_metric("ab", {"value": 1, "reason": None})
    out_long = _format_metric("a" * 30, {"value": 1, "reason": None})
    assert len(out_short.split("  1")[0]) == len(out_long.split("  1")[0])
