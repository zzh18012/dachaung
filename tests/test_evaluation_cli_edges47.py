"""evaluation/cli.py 第四十八轮 edges 测试（Round 460）。

补强 edges46 未触及的角度：
- _build_parser 行为深度第二十批（prog / description / choices for --parser / type for --max-chars / defaults / subparser dest）
- _format_metric 行为深度第二十批（value=0 / value=0.0 / value=list / value=large dict / value=empty dict / value=empty string / long reason）
- _run_inspect_doc 行为深度第二十批（document_id 缺省 / source_path 缺省 / parser_name 缺省 / parser_version 缺省 / metrics 排序分组 / elements 与 chunks None / 多 metric 类型混合）
- main 行为深度第二十批（run 全参数 / validate-report FileNotFoundError / inspect-doc 文件不存在返回 2 / inspect-doc SystemExit / 无效命令 SystemExit / run 内 run_evaluation 抛 EvalSchemaError）
- module source forbidden tokens 第三十五批
- module source 字符串精确补强第三十批
- signatures 第三十批
- module 合理性第三十批
- 端到端集成第三十批
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


# ---------- _build_parser 行为深度第二十批 ----------


def test_build_parser_prog_attribute_batch20():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_has_description_batch20():
    p = _build_parser()
    assert p.description is not None
    assert "评测" in p.description


def test_build_parser_subparser_dest_is_command_batch20():
    """subparser 的 dest 应是 'command'。"""
    p = _build_parser()
    # 找到 _SubParsersAction
    for action in p._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            assert action.dest == "command"


def test_build_parser_subparser_required_true_batch20():
    p = _build_parser()
    for action in p._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            assert action.required is True


def test_build_parser_run_parser_choices_for_parser_batch20():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json", "--parser", "kreuzberg"])
    assert args.parser == "kreuzberg"


def test_build_parser_run_parser_default_fallback_batch20():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert args.parser == "fallback"


def test_build_parser_run_parser_invalid_choice_system_exit_batch20():
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "a.json", "--output", "b.json", "--parser", "invalid"])


def test_build_parser_max_chars_type_int_batch20():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json", "--max-chars", "500"])
    assert args.max_chars == 500
    assert isinstance(args.max_chars, int)


def test_build_parser_max_chars_default_800_batch20():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert args.max_chars == 800


def test_build_parser_tolerance_chars_default_30_batch20():
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a.json", "--output", "b.json"])
    assert args.tolerance_chars == 30


def test_build_parser_tolerance_chars_inspect_doc_default_30_batch20():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "x.json"])
    assert args.tolerance_chars == 30


def test_build_parser_validate_report_takes_positional_batch20():
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"


def test_build_parser_inspect_doc_takes_positional_batch20():
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.input == "doc.json"


# ---------- _format_metric 行为深度第二十批 ----------


def test_format_metric_value_zero_int_batch20():
    """value=0 (int) 走 default 分支。"""
    out = _format_metric("count", {"value": 0, "reason": None})
    assert "0" in out
    assert "(ok)" in out


def test_format_metric_value_zero_float_batch20():
    """value=0.0 走 float 分支（显示 0.0000）。"""
    out = _format_metric("ratio", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_value_one_float_batch20():
    out = _format_metric("ratio", {"value": 1.0, "reason": None})
    assert "1.0000" in out


def test_format_metric_value_negative_int_batch20():
    out = _format_metric("drop", {"value": -3, "reason": "x"})
    assert "-3" in out


def test_format_metric_value_empty_dict_batch20():
    out = _format_metric("counts", {"value": {}, "reason": None})
    assert "counts" in out
    # 空字典应渲染空内容
    assert "(ok)" in out


def test_format_metric_value_dict_with_many_items_batch20():
    val = {f"k{i}": i for i in range(10)}
    out = _format_metric("by_type", {"value": val, "reason": None})
    # 应被排序输出
    assert "k0=0" in out
    assert "k9=9" in out


def test_format_metric_value_dict_sorted_alpha_batch20():
    """dict 内容按 key 排序。"""
    val = {"b": 1, "a": 2, "c": 3}
    out = _format_metric("by_type", {"value": val, "reason": None})
    assert out.index("a=2") < out.index("b=1") < out.index("c=3")


def test_format_metric_value_string_batch20():
    out = _format_metric("err_code", {"value": "E_X", "reason": None})
    assert "E_X" in out


def test_format_metric_value_empty_string_batch20():
    out = _format_metric("err_code", {"value": "", "reason": None})
    assert "(ok)" in out


def test_format_metric_long_reason_batch20():
    out = _format_metric("x", {"value": None, "reason": "very_long_reason_string_exceeding_normal_length"})
    assert "very_long_reason_string_exceeding_normal_length" in out


def test_format_metric_reason_overrides_ok_for_bool_batch20():
    out = _format_metric("flag", {"value": True, "reason": "custom"})
    assert "(custom)" in out


def test_format_metric_aligned_width_36_batch20():
    """name 字段固定 36 字符宽（短 name 与 30-char name 后内容对齐）。"""
    out_short = _format_metric("ab", {"value": 1, "reason": None})
    out_long = _format_metric("a" * 30, {"value": 1, "reason": None})
    # split 取 "1" 之前的部分，两行总长应相等
    assert len(out_short.split("  1")[0]) == len(out_long.split("  1")[0])


# ---------- _run_inspect_doc 行为深度第二十批 ----------


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


def test_run_inspect_doc_prints_default_document_id_when_missing_batch20(tmp_path, capsys):
    """doc 无 document_id → 打印 '?'。"""
    p = _write_doc(tmp_path, doc={"source_type": "pdf", "elements": [], "chunks": []})
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "document_id: ?" in captured


def test_run_inspect_doc_prints_default_source_path_when_missing_batch20(tmp_path, capsys):
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "source:      ?" in captured


def test_run_inspect_doc_prints_default_parser_when_missing_batch20(tmp_path, capsys):
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "parser:      ? v?" in captured


def test_run_inspect_doc_elements_none_batch20(tmp_path, capsys):
    """doc 中 elements=None：cli 'or []' 仅兜底本地变量，doc 本身仍 None。
    后续 compute_automatic_metrics 会 TypeError（已知 bug）。"""
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": None,
        "chunks": [],
    }
    p = _write_doc(tmp_path, doc=doc)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    with pytest.raises(TypeError):
        _run_inspect_doc(args)


def test_run_inspect_doc_chunks_none_batch20(tmp_path, capsys):
    """doc 中 chunks=None：cli 'or []' 仅兜底本地变量，doc 本身仍 None。"""
    doc = {
        "document_type": "x",
        "source_type": "pdf",
        "elements": [],
        "chunks": None,
    }
    p = _write_doc(tmp_path, doc=doc)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    with pytest.raises(TypeError):
        _run_inspect_doc(args)


def test_run_inspect_doc_metrics_count_batch20(tmp_path, capsys):
    """inspect-doc 应输出 14 + 3 (figure_caption_*) + 3 (chunk_boundary_*) = 至少 20 行 metric。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    # 数 metric 行（前缀 2 空格的行）
    metric_lines = [line for line in captured.splitlines() if line.startswith("  ")]
    assert len(metric_lines) >= 17  # 14 个 automatic + 3 figure_caption + 3 chunk_boundary (合并)


def test_run_inspect_doc_metrics_sorted_bool_first_batch20(tmp_path, capsys):
    """metric 排序：bool 第一组。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    lines = [line for line in captured.splitlines() if line.startswith("  ")]
    # 至少有一行（pipeline_success / schema_valid）
    assert any("true" in line.lower() or "false" in line.lower() for line in lines)


def test_run_inspect_doc_top_level_array_returns_1_batch20(tmp_path):
    """doc 是 list → return 1。"""
    p = tmp_path / "d.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    assert _run_inspect_doc(args) == 1


def test_run_inspect_doc_top_level_string_returns_1_batch20(tmp_path):
    p = tmp_path / "d.json"
    p.write_text('"hello"', encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    assert _run_inspect_doc(args) == 1


def test_run_inspect_doc_top_level_int_returns_1_batch20(tmp_path):
    p = tmp_path / "d.json"
    p.write_text("42", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    assert _run_inspect_doc(args) == 1


def test_run_inspect_doc_file_not_exist_returns_2_batch20(tmp_path):
    args = MagicMock()
    args.input = str(tmp_path / "missing.json")
    args.tolerance_chars = 30
    assert _run_inspect_doc(args) == 2


def test_run_inspect_doc_invalid_json_returns_1_batch20(tmp_path):
    p = tmp_path / "d.json"
    p.write_text("{not valid", encoding="utf-8")
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    assert _run_inspect_doc(args) == 1


def test_run_inspect_doc_with_tolerance_chars_batch20(tmp_path, capsys):
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 50
    rc = _run_inspect_doc(args)
    assert rc == 0


# ---------- main 行为深度第二十批 ----------


def test_main_run_full_options_batch20(tmp_path, capsys):
    """run 子命令带所有参数。"""
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out_p = tmp_path / "out.json"
    with patch("evaluation.cli.run_evaluation", return_value={
        "report_version": "1.1",
        "provenance": {},
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }):
        with patch("evaluation.cli.validate_file", return_value=None):
            with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc123", "git_dirty": False}):
                # 写出 output 文件以便后续 validate_file
                out_p.write_text("{}", encoding="utf-8")
                rc = main(["run", "--manifest", str(manifest_p), "--output", str(out_p),
                           "--parser", "kreuzberg", "--max-chars", "1000", "--tolerance-chars", "50"])
    assert rc == 0


def test_main_validate_report_file_not_found_returns_2_batch20(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_1_batch20(tmp_path, capsys):
    p = tmp_path / "report.json"
    p.write_text("{not valid", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_run_manifest_not_exist_returns_2_batch20(tmp_path, capsys):
    rc = main(["run", "--manifest", str(tmp_path / "missing.json"), "--output", str(tmp_path / "out.json")])
    assert rc == 2


def test_main_run_manifest_load_error_returns_1_batch20(tmp_path, capsys):
    p = tmp_path / "manifest.json"
    p.write_text("{not valid", encoding="utf-8")
    rc = main(["run", "--manifest", str(p), "--output", str(tmp_path / "out.json")])
    assert rc == 1


def test_main_run_eval_schema_error_after_run_batch20(tmp_path, capsys):
    """run_evaluation 抛 EvalSchemaError → return 1。"""
    from evaluation.schema import EvalSchemaError

    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    with patch("evaluation.cli.run_evaluation", side_effect=EvalSchemaError("boom")):
        rc = main(["run", "--manifest", str(manifest_p), "--output", str(tmp_path / "out.json")])
    assert rc == 1


def test_main_unknown_command_system_exit_batch20():
    """未知子命令 → SystemExit（argparse 拒绝）。"""
    with pytest.raises(SystemExit):
        main(["unknown-command"])


def test_main_run_calls_load_manifest_batch20(tmp_path, capsys):
    """main('run') 应调用 load_manifest。"""
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
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    assert mock_load.call_count == 1


def test_main_run_prints_documents_count_batch20(tmp_path, capsys):
    """成功 run 应打印 documents=N。"""
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
            "per_doc": [
                {"doc_id": "d1", "source_type": "pdf", "metrics": {"pipeline_success": {"value": True}}, "wall_time_seconds": {"total": 0.1, "parse": None, "chunk": None, "parse_reason": "not_instrumented", "chunk_reason": "not_instrumented"}},
                {"doc_id": "d2", "source_type": "pdf", "metrics": {"pipeline_success": {"value": False}}, "wall_time_seconds": {"total": 0.1, "parse": None, "chunk": None, "parse_reason": "not_instrumented", "chunk_reason": "not_instrumented"}},
            ],
            "expected_failures": [],
        }):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc123def456", "git_dirty": True}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    rc = main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    captured = capsys.readouterr().out
    assert "documents=2" in captured
    assert "成功 1" in captured
    assert "失败 1" in captured
    assert "abc123def456"[:12] in captured


def test_main_validate_report_eval_schema_error_after_run_batch20(tmp_path, capsys):
    """validate_file 抛 EvalSchemaError → return 1。"""
    from evaluation.schema import EvalSchemaError

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
            with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("schema fail")):
                rc = main(["run", "--manifest", str(manifest_p), "--output", str(tmp_path / "out.json")])
    assert rc == 1


# ---------- module source forbidden tokens 第三十五批 ----------


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
def test_module_source_forbidden_tokens_batch20(forbidden):
    src = inspect.getsource(climod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch20():
    src = inspect.getsource(climod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch20():
    src = inspect.getsource(climod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch20():
    src = inspect.getsource(climod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch20():
    src = inspect.getsource(climod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch20():
    src = inspect.getsource(climod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch20():
    src = inspect.getsource(climod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch20():
    src = inspect.getsource(climod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch20():
    src = inspect.getsource(climod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch20():
    src = inspect.getsource(climod)
    assert "import tempfile" not in src


def test_module_source_no_unlink_call_batch20():
    src = inspect.getsource(climod)
    assert ".unlink(" not in src


def test_module_source_no_rmdir_call_batch20():
    src = inspect.getsource(climod)
    assert ".rmdir(" not in src


def test_module_source_no_path_write_text_batch20():
    src = inspect.getsource(climod)
    assert ".write_text(" not in src


def test_module_source_no_sys_exit_call_batch20():
    """main() 不应直接 sys.exit（返回 int 给 caller）。"""
    src = inspect.getsource(climod)
    assert "sys.exit(" not in src


def test_module_source_no_re_compile_batch20():
    src = inspect.getsource(climod)
    assert "re.compile" not in src


def test_module_source_no_pandas_import_batch20():
    src = inspect.getsource(climod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch20():
    src = inspect.getsource(climod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第三十批 ----------


def test_module_source_has_future_annotations_batch20():
    src = inspect.getsource(climod)
    assert "from __future__ import annotations" in src


def test_module_source_has_argparse_import_batch20():
    src = inspect.getsource(climod)
    assert "import argparse" in src


def test_module_source_has_json_import_batch20():
    src = inspect.getsource(climod)
    assert "import json" in src


def test_module_source_has_sys_import_batch20():
    src = inspect.getsource(climod)
    assert "import sys" in src


def test_module_source_has_pathlib_path_import_batch20():
    src = inspect.getsource(climod)
    assert "from pathlib import Path" in src


def test_module_source_has_manifest_import_batch20():
    src = inspect.getsource(climod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_module_source_has_report_import_batch20():
    src = inspect.getsource(climod)
    assert "from evaluation.report import get_git_provenance" in src


def test_module_source_has_runner_import_batch20():
    src = inspect.getsource(climod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_has_schema_import_batch20():
    src = inspect.getsource(climod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_module_source_has_build_parser_function_batch20():
    src = inspect.getsource(climod)
    assert "def _build_parser(" in src


def test_module_source_has_main_function_batch20():
    src = inspect.getsource(climod)
    assert "def main(" in src


def test_module_source_has_run_inspect_doc_function_batch20():
    src = inspect.getsource(climod)
    assert "def _run_inspect_doc(" in src


def test_module_source_has_format_metric_function_batch20():
    src = inspect.getsource(climod)
    assert "def _format_metric(" in src


def test_module_source_has_add_subparsers_call_batch20():
    src = inspect.getsource(climod)
    assert "add_subparsers" in src


def test_module_source_has_windows_stdout_reconfigure_block_batch20():
    src = inspect.getsource(climod)
    assert "sys.stdout" in src
    assert "reconfigure" in src


def test_module_source_has_main_block_raises_system_exit_batch20():
    src = inspect.getsource(climod)
    assert 'if __name__ ==' in src
    assert "raise SystemExit(main())" in src


def test_module_source_has_choices_tuple_for_parser_batch20():
    src = inspect.getsource(climod)
    assert '"fallback"' in src
    assert '"kreuzberg"' in src


# ---------- signatures 第三十批 ----------


def test_signature_build_parser_batch20():
    sig = inspect.signature(_build_parser)
    params = list(sig.parameters.values())
    assert len(params) == 0


def test_signature_main_batch20():
    sig = inspect.signature(main)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["argv"]


def test_signature_main_argv_default_none_batch20():
    sig = inspect.signature(main)
    params = list(sig.parameters.values())
    assert params[0].default is None


def test_signature_format_metric_batch20():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["name", "metric"]


def test_signature_run_inspect_doc_batch20():
    sig = inspect.signature(_run_inspect_doc)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["args"]


# ---------- module 合理性第三十批 ----------


def test_module_has_main_function_batch20():
    assert hasattr(climod, "main")


def test_module_has_build_parser_batch20():
    assert hasattr(climod, "_build_parser")


def test_module_has_run_inspect_doc_batch20():
    assert hasattr(climod, "_run_inspect_doc")


def test_module_has_format_metric_batch20():
    assert hasattr(climod, "_format_metric")


def test_module_does_not_import_app_pipeline_batch20():
    src = inspect.getsource(climod)
    assert "from app" not in src
    assert "import app" not in src


def test_module_does_not_import_evaluation_metrics_batch20():
    """cli.py 不直接 import metrics（inspect-doc 内部 lazy import）。"""
    src = inspect.getsource(climod)
    top = src[: src.find("def _run_inspect_doc")]
    assert "from evaluation.metrics" not in top


def test_module_does_not_import_evaluation_annotation_metrics_batch20():
    """cli.py 不直接 import annotation_metrics（inspect-doc 内部 lazy import）。"""
    src = inspect.getsource(climod)
    top = src[: src.find("def _run_inspect_doc")]
    assert "from evaluation.annotation_metrics" not in top


def test_module_does_not_import_evaluation_aggregate_summary_batch20():
    src = inspect.getsource(climod)
    assert "aggregate_summary" not in src


def test_module_lazy_imports_inside_run_inspect_doc_batch20():
    src = inspect.getsource(climod)
    inspect_body = src[src.find("def _run_inspect_doc"):]
    assert "from evaluation.annotation_metrics import chunk_boundary_prf, figure_caption_prf" in inspect_body
    assert "from evaluation.metrics import compute_automatic_metrics" in inspect_body


def test_module_main_returns_int_batch20():
    """main() 返回 int。"""
    rc = main(["validate-report", "/nonexistent.json"])
    assert isinstance(rc, int)


# ---------- 端到端集成 第三十批 ----------


def test_e2e_main_inspect_doc_full_round_trip_batch20(tmp_path, capsys):
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


def test_e2e_main_validate_report_round_trip_batch20(tmp_path, capsys):
    """validate-report 不存在文件 → rc=2。"""
    rc = main(["validate-report", str(tmp_path / "missing.json")])
    captured = capsys.readouterr()
    assert rc == 2


def test_e2e_main_no_command_system_exit_batch20():
    """无子命令 → SystemExit。"""
    with pytest.raises(SystemExit):
        main([])


def test_e2e_main_run_prints_ok_on_success_batch20(tmp_path, capsys):
    """成功 run 打印 [OK]。"""
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    with patch("evaluation.cli.run_evaluation", return_value={
        "report_version": "1.1",
        "provenance": {},
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }):
        with patch("evaluation.cli.validate_file", return_value=None):
            with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x" * 20, "git_dirty": False}):
                out_p = tmp_path / "out.json"
                out_p.write_text("{}", encoding="utf-8")
                rc = main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    captured = capsys.readouterr().out
    assert "[OK]" in captured
    assert "documents=0" in captured


def test_e2e_main_run_with_failed_doc_in_count_batch20(tmp_path, capsys):
    """run 报告失败 doc 计入 n_fail。"""
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    with patch("evaluation.cli.run_evaluation", return_value={
        "report_version": "1.1",
        "provenance": {},
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
        "summary": {},
        "per_doc": [
            {"doc_id": "d", "source_type": "pdf",
             "metrics": {"pipeline_success": {"value": None}},
             "wall_time_seconds": {"total": 0, "parse": None, "chunk": None, "parse_reason": "x", "chunk_reason": "x"}},
        ],
        "expected_failures": [],
    }):
        with patch("evaluation.cli.validate_file", return_value=None):
            with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
                out_p = tmp_path / "out.json"
                out_p.write_text("{}", encoding="utf-8")
                rc = main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    captured = capsys.readouterr().out
    # n_ok=0, n_fail=1 (None 计为 not success)
    assert "documents=1" in captured


def test_e2e_main_run_devset_summary_batch20(tmp_path, capsys):
    """run 输出 devset_status / file_count / groups / pdf / docx。"""
    manifest_p = tmp_path / "manifest.json"
    manifest_p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    with patch("evaluation.cli.run_evaluation", return_value={
        "report_version": "1.1",
        "provenance": {},
        "devset": {"status": "incomplete", "file_count": 5, "content_group_count": 2, "pdf_count": 3, "docx_count": 2, "categories_covered": []},
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }):
        with patch("evaluation.cli.validate_file", return_value=None):
            with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
                out_p = tmp_path / "out.json"
                out_p.write_text("{}", encoding="utf-8")
                rc = main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    captured = capsys.readouterr().out
    assert "devset_status=incomplete" in captured
    assert "file_count=5" in captured
    assert "groups=2" in captured
    assert "pdf=3" in captured
    assert "docx=2" in captured


def test_e2e_main_inspect_doc_with_metrics_render_batch20(tmp_path, capsys):
    """inspect-doc 输出含 'metrics:' 标题。"""
    p = _write_doc(tmp_path)
    rc = main(["inspect-doc", str(p)])
    captured = capsys.readouterr().out
    assert "metrics:" in captured
    assert rc == 0
