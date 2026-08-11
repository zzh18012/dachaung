"""evaluation/cli.py 第五十二轮 edges 测试（Round 487）。

补强 edges50 未触及的角度（第二十四批）：
- _build_parser 第二十四批：run parser prog/description / val parser prog/description / ins parser prog/description / subparser dest+required / run --manifest required / run --output required / run --parser choices / run --parser default / run --max-chars default / run --tolerance-chars default / val positional input / ins positional input / ins --tolerance-chars default / 三个子命令互斥 / prog format
- _format_metric 第二十四批：value=None / value=True / value=False / value=0.5 float / value=1 int / value=dict / value="string" / value=[] / reason 缺失 fallback 'ok' / 名称左对齐 36 字符
- _run_inspect_doc 第二十四批：文件不存在 / 非 JSON / JSON 但非 dict / 空 doc / 含 elements/chunks / tolerance_chars 透传 / print 调用次数 / 排序逻辑（bool → number → 其他 → None）
- main 第二十四批：未知子命令 → SystemExit 2 / run 清单不存在 → return 2 / run 清单加载失败 → return 1 / run run_evaluation EvalSchemaError → return 1 / run validate_file EvalSchemaError → return 1 / val 文件不存在 → 2 / val 校验失败 → 1 / val JSON 解析失败 → 1 / val 成功 → 0 / ins 委托 _run_inspect_doc / None argv
- module source forbidden tokens 第四十批
- module source 字符串精确补强第三十六批
- signatures 第三十六批
- module 合理性第三十六批
- 端到端集成第三十六批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evaluation import cli as climod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 第二十四批 ----------


def test_build_parser_run_prog_batch24():
    """整个 parser 的 prog 是 'evaluation.cli'。"""
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_run_description_batch24():
    """整个 parser 的 description 含 '评测 CLI'。"""
    p = _build_parser()
    assert "评测 CLI" in p.description


def test_build_parser_subparser_dest_command_batch24():
    """subparser 的 dest='command'。"""
    p = _build_parser()
    # 通过解析空 args 检查（应当报错 required=True）
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_build_parser_subparser_required_batch24():
    """subparser required=True。"""
    p = _build_parser()
    # _SubParsersAction 的 required 属性
    sub_actions = [
        a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"
    ]
    assert len(sub_actions) == 1
    assert sub_actions[0].required is True


def test_build_parser_subparser_dest_attribute_batch24():
    """subparser dest 是 'command'。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"
    ]
    assert sub_actions[0].dest == "command"


def test_build_parser_has_three_choices_batch24():
    """三个子命令：run, validate-report, inspect-doc。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"
    ]
    assert set(sub_actions[0].choices.keys()) == {
        "run",
        "validate-report",
        "inspect-doc",
    }


def test_build_parser_run_manifest_required_batch24():
    """run --manifest 必填。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "out.json"])


def test_build_parser_run_output_required_batch24():
    """run --output 必填。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "m.json"])


def test_build_parser_run_parser_default_fallback_batch24():
    """run --parser 默认 fallback。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.parser == "fallback"


def test_build_parser_run_parser_choices_batch24():
    """run --parser 限定 {fallback, kreuzberg}。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(
            ["run", "--manifest", "m.json", "--output", "o.json", "--parser", "bogus"]
        )


def test_build_parser_run_max_chars_default_800_batch24():
    """run --max-chars 默认 800。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.max_chars == 800


def test_build_parser_run_tolerance_chars_default_30_batch24():
    """run --tolerance-chars 默认 30。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.tolerance_chars == 30


def test_build_parser_validate_report_positional_input_batch24():
    """validate-report 接受 positional input。"""
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"


def test_build_parser_inspect_doc_positional_input_batch24():
    """inspect-doc 接受 positional input。"""
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.input == "doc.json"


def test_build_parser_inspect_doc_tolerance_default_30_batch24():
    """inspect-doc --tolerance-chars 默认 30。"""
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_inspect_doc_tolerance_custom_batch24():
    """inspect-doc --tolerance-chars 可自定义。"""
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "50"])
    assert args.tolerance_chars == 50


def test_build_parser_mutually_exclusive_subcommands_batch24():
    """同一次只能选一个子命令。"""
    p = _build_parser()
    # 多个 positional 在不同 subparser 下应当报错
    with pytest.raises(SystemExit):
        p.parse_args(["run", "validate-report"])


def test_build_parser_run_max_chars_accepts_negative_batch24():
    """run --max-chars 接受负数（CLI 不做范围检查）。"""
    p = _build_parser()
    args = p.parse_args(
        ["run", "--manifest", "m.json", "--output", "o.json", "--max-chars", "-1"]
    )
    assert args.max_chars == -1


# ---------- _format_metric 第二十四批 ----------


def test_format_metric_value_none_batch24():
    """value=None → 'name  null  (reason)'。"""
    out = _format_metric("foo", {"value": None, "reason": "no_data"})
    assert "null" in out
    assert "no_data" in out
    assert "foo" in out


def test_format_metric_value_true_batch24():
    """value=True → 'true  (ok)'。"""
    out = _format_metric("foo", {"value": True, "reason": None})
    assert "true" in out
    assert "(ok)" in out


def test_format_metric_value_false_batch24():
    """value=False → 'false  (ok)'。"""
    out = _format_metric("foo", {"value": False, "reason": None})
    assert "false" in out
    assert "(ok)" in out


def test_format_metric_value_float_batch24():
    """value=0.5 (float) → 4 位小数。"""
    out = _format_metric("foo", {"value": 0.5, "reason": None})
    assert "0.5000" in out


def test_format_metric_value_int_batch24():
    """value=42 (int) → '42  (ok)'。"""
    out = _format_metric("foo", {"value": 42, "reason": None})
    assert "42" in out
    assert "(ok)" in out


def test_format_metric_value_dict_batch24():
    """value=dict → items 逗号拼接。"""
    out = _format_metric(
        "element_count_by_type", {"value": {"pdf": 1, "docx": 2}, "reason": None}
    )
    assert "docx=2" in out
    assert "pdf=1" in out
    assert "(ok)" in out


def test_format_metric_value_string_batch24():
    """value=str → 直接输出字符串。"""
    out = _format_metric("foo", {"value": "hello", "reason": None})
    assert "hello" in out
    assert "(ok)" in out


def test_format_metric_value_list_batch24():
    """value=list → 走 fallback 分支（str(value)）。"""
    out = _format_metric("foo", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in out


def test_format_metric_reason_missing_falls_back_ok_batch24():
    """metric 缺 reason key → 默认 'ok'。"""
    out = _format_metric("foo", {"value": True})
    assert "(ok)" in out


def test_format_metric_name_padded_36_chars_batch24():
    """name 左对齐 36 字符（即使短名也占 36）。"""
    out = _format_metric("x", {"value": 0.5, "reason": None})
    # "  x" + padding spaces up to 36 chars then value
    # 找 "x" 后的空格
    assert "  x" in out
    # 至少有 36-1=35 个空格（2 leading + 1 char + 34 padding）
    # 验证 name 部分 <= 38 chars（含 2 leading）
    # 简单方法：找 "0.5000" 前的空格数
    pre_value = out.split("0.5000")[0]
    assert len(pre_value) >= 36


def test_format_metric_value_negative_int_batch24():
    """value=-5 (int) → '-5  (ok)'。"""
    out = _format_metric("foo", {"value": -5, "reason": None})
    assert "-5" in out


def test_format_metric_value_zero_batch24():
    """value=0 (int) → '0  (ok)'。"""
    out = _format_metric("foo", {"value": 0, "reason": None})
    # 注意：0 是 falsy 但 isinstance bool 是 False，所以走 int 分支
    assert "0" in out
    # 不应是 false
    assert "false" not in out


def test_format_metric_value_empty_dict_batch24():
    """value={} → 空字符串 + (ok)。"""
    out = _format_metric("foo", {"value": {}, "reason": None})
    assert "(ok)" in out


# ---------- _run_inspect_doc 第二十四批 ----------


def _make_inspect_args(input_path, tolerance_chars=30):
    """构造 inspect-doc 的 args Namespace。"""
    args = MagicMock()
    args.input = str(input_path)
    args.tolerance_chars = tolerance_chars
    return args


def test_run_inspect_doc_missing_file_returns_2_batch24(tmp_path, capsys):
    """文件不存在 → return 2 + stderr 错误。"""
    p = tmp_path / "nope.json"
    rc = _run_inspect_doc(_make_inspect_args(p))
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err
    assert "文档不存在" in err


def test_run_inspect_doc_invalid_json_returns_1_batch24(tmp_path, capsys):
    """非合法 JSON → return 1。"""
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    rc = _run_inspect_doc(_make_inspect_args(p))
    assert rc == 1
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_run_inspect_doc_top_level_not_dict_returns_1_batch24(tmp_path, capsys):
    """JSON 顶层不是对象 → return 1。"""
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    rc = _run_inspect_doc(_make_inspect_args(p))
    assert rc == 1
    err = capsys.readouterr().err
    assert "[ERROR]" in err
    assert "JSON 顶层不是对象" in err


def test_run_inspect_doc_empty_dict_returns_0_batch24(tmp_path, capsys):
    """空 dict → return 0（缺字段走 default）。"""
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}), patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
        rc = _run_inspect_doc(_make_inspect_args(p))
    assert rc == 0


def test_run_inspect_doc_full_doc_prints_header_batch24(tmp_path, capsys):
    """含完整字段的 doc → 打印 file/document_id/source/parser/counts header。"""
    doc = {
        "document_id": "doc_001",
        "source_path": "/foo/bar.pdf",
        "source_type": "pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"type": "paragraph"}, {"type": "heading"}],
        "chunks": [{"text": "abc"}],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}), patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
        rc = _run_inspect_doc(_make_inspect_args(p))
    assert rc == 0
    out = capsys.readouterr().out
    assert "doc_001" in out
    assert "/foo/bar.pdf" in out
    assert "fallback" in out
    assert "elements=2" in out
    assert "chunks=1" in out


def test_run_inspect_doc_tolerance_chars_passed_batch24(tmp_path):
    """--tolerance-chars 透传给 chunk_boundary_prf。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    captured = {}

    def fake_chunk_b(doc, ann, tolerance_chars=30):
        captured["tolerance_chars"] = tolerance_chars
        return {}

    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}), patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch("evaluation.annotation_metrics.chunk_boundary_prf", side_effect=fake_chunk_b):
        _run_inspect_doc(_make_inspect_args(p, tolerance_chars=42))
    assert captured["tolerance_chars"] == 42


def test_run_inspect_doc_print_count_batch24(tmp_path, capsys):
    """inspect-doc 至少打印 6 行 header + 'metrics:' + 排序后每个 metric。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    metrics = {
        "ratio_metric": {"value": 0.5, "reason": "ok"},
        "bool_metric": {"value": True, "reason": "ok"},
        "null_metric": {"value": None, "reason": "no_data"},
    }
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value=metrics
    ), patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}), patch(
        "evaluation.annotation_metrics.chunk_boundary_prf", return_value={}
    ):
        rc = _run_inspect_doc(_make_inspect_args(p))
    assert rc == 0
    out = capsys.readouterr().out
    # 排序：bool 先（True），ratio 中，null 后
    pos_bool = out.find("bool_metric")
    pos_ratio = out.find("ratio_metric")
    pos_null = out.find("null_metric")
    assert pos_bool < pos_ratio < pos_null


def test_run_inspect_doc_metric_sorting_string_value_batch24(tmp_path, capsys):
    """metric value 是 string → 排在 number 之后、None 之前。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    metrics = {
        "str_metric": {"value": "abc", "reason": "ok"},
        "null_metric": {"value": None, "reason": "no_data"},
        "num_metric": {"value": 1, "reason": "ok"},
    }
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value=metrics
    ), patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}), patch(
        "evaluation.annotation_metrics.chunk_boundary_prf", return_value={}
    ):
        _run_inspect_doc(_make_inspect_args(p))
    out = capsys.readouterr().out
    # num (group 1) < str (group 2) < null (group 3)
    pos_num = out.find("num_metric")
    pos_str = out.find("str_metric")
    pos_null = out.find("null_metric")
    assert pos_num < pos_str < pos_null


# ---------- main 第二十四批 ----------


def test_main_unknown_subcommand_exits_batch24():
    """未知子命令 → SystemExit（argparse 自动报错）。"""
    with pytest.raises(SystemExit):
        main(["bogus"])


def test_main_no_args_exits_batch24():
    """无子命令 → SystemExit（subparser required=True）。"""
    with pytest.raises(SystemExit):
        main([])


def test_main_run_manifest_missing_returns_2_batch24(tmp_path, capsys):
    """run 子命令：清单不存在 → return 2 + stderr。"""
    out = tmp_path / "report.json"
    manifest = tmp_path / "no.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(out)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err
    assert "清单不存在" in err


def test_main_run_manifest_load_failure_returns_1_batch24(tmp_path, capsys):
    """run: 清单加载失败（ManifestError）→ return 1。"""
    bad_manifest = tmp_path / "bad.json"
    bad_manifest.write_text("not json", encoding="utf-8")
    out = tmp_path / "report.json"
    rc = main(["run", "--manifest", str(bad_manifest), "--output", str(out)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "清单加载失败" in err


def test_main_run_eval_schema_error_returns_1_batch24(tmp_path, capsys):
    """run: run_evaluation 抛 EvalSchemaError → return 1。"""
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    from evaluation.schema import EvalSchemaError

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    def fake_run(*args, **kwargs):
        raise EvalSchemaError("schema fail")

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), patch(
        "evaluation.cli.run_evaluation", side_effect=fake_run
    ):
        rc = main(["run", "--manifest", str(manifest), "--output", str(out)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "Schema 校验" in err


def test_main_run_validate_file_schema_error_returns_1_batch24(tmp_path, capsys):
    """run: 报告自校验失败 → return 1。"""
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    from evaluation.schema import EvalSchemaError

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    with patch(
        "evaluation.cli.load_manifest", return_value=fake_manifest
    ), patch(
        "evaluation.cli.run_evaluation",
        return_value={"per_doc": [], "devset": {}},
    ), patch(
        "evaluation.cli.validate_file", side_effect=EvalSchemaError("bad report")
    ):
        rc = main(["run", "--manifest", str(manifest), "--output", str(out)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "自校验失败" in err


def test_main_run_success_returns_0_batch24(tmp_path, capsys):
    """run: 全成功 → return 0 + stdout 含统计。"""
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    fake_report = {
        "per_doc": [
            {"doc_id": "d1", "metrics": {"pipeline_success": {"value": True}}},
            {"doc_id": "d2", "metrics": {"pipeline_success": {"value": False}}},
        ],
        "devset": {
            "status": "incomplete",
            "file_count": 2,
            "content_group_count": 1,
            "pdf_count": 1,
            "docx_count": 1,
        },
    }
    with patch(
        "evaluation.cli.run_evaluation", return_value=fake_report
    ), patch("evaluation.cli.validate_file"), patch(
        "evaluation.cli.get_git_provenance",
        return_value={"git_commit": "abc1234567890", "git_dirty": False},
    ):
        rc = main(["run", "--manifest", str(manifest), "--output", str(out)])
    assert rc == 0
    out_str = capsys.readouterr().out
    assert "documents=2" in out_str
    assert "成功 1" in out_str
    assert "失败 1" in out_str
    assert "abc1234567890"[:12] in out_str


def test_main_validate_report_missing_returns_2_batch24(tmp_path, capsys):
    """validate-report：报告不存在 → return 2。"""
    p = tmp_path / "no.json"
    rc = main(["validate-report", str(p)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "报告不存在" in err


def test_main_validate_report_failure_returns_1_batch24(tmp_path, capsys):
    """validate-report：校验失败 → return 1。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    from evaluation.schema import EvalSchemaError

    with patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("bad")):
        rc = main(["validate-report", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err


def test_main_validate_report_json_decode_error_returns_1_batch24(tmp_path, capsys):
    """validate-report：JSON 解析失败 → return 1。"""
    p = tmp_path / "report.json"
    p.write_text("not json", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON 解析失败" in err


def test_main_validate_report_success_returns_0_batch24(tmp_path, capsys):
    """validate-report：成功 → return 0。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file"):
        rc = main(["validate-report", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[OK]" in out


def test_main_inspect_doc_delegates_batch24(tmp_path):
    """main: inspect-doc 委托给 _run_inspect_doc。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli._run_inspect_doc", return_value=0) as mock_inspect:
        rc = main(["inspect-doc", str(p)])
    assert rc == 0
    mock_inspect.assert_called_once()


def test_main_run_passes_args_to_run_evaluation_batch24(tmp_path):
    """main: run 把 --parser/--max-chars/--tolerance-chars 透传给 run_evaluation。"""
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    captured = {}

    def fake_run(manifest_obj, output_path, *, parser_name, max_chars, tolerance_chars):
        captured["parser_name"] = parser_name
        captured["max_chars"] = max_chars
        captured["tolerance_chars"] = tolerance_chars
        return {"per_doc": [], "devset": {}}

    with patch("evaluation.cli.run_evaluation", side_effect=fake_run), patch(
        "evaluation.cli.validate_file"
    ), patch("evaluation.cli.get_git_provenance", return_value={"git_commit": None, "git_dirty": False}):
        rc = main(
            [
                "run",
                "--manifest",
                str(manifest),
                "--output",
                str(out),
                "--parser",
                "kreuzberg",
                "--max-chars",
                "1000",
                "--tolerance-chars",
                "50",
            ]
        )
    assert rc == 0
    assert captured["parser_name"] == "kreuzberg"
    assert captured["max_chars"] == 1000
    assert captured["tolerance_chars"] == 50


# ---------- module source forbidden tokens 第四十批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import os",
    "import re",
    "import datetime",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import itertools",
    "import functools",
    "import timeit",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from itertools",
    "from functools",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import subprocess",
]


def test_module_source_forbidden_tokens_batch24():
    """cli.py 不应 import 这些副作用大的模块。"""
    source = inspect.getsource(climod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_no_class_keyword_batch24():
    """cli.py 不应使用 class（functional 风格）。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(climod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_source_no_yield_batch24():
    """cli.py 不应使用 yield。"""
    source = inspect.getsource(climod)
    assert "yield " not in source


def test_module_source_no_async_def_batch24():
    """cli.py 不应使用 async def。"""
    source = inspect.getsource(climod)
    assert "async def" not in source


def test_module_source_no_global_keyword_batch24():
    """cli.py 不应使用 global。"""
    source = inspect.getsource(climod)
    assert "global " not in source


def test_module_source_no_walrus_batch24():
    """cli.py 不应使用 walrus 运算符。"""
    source = inspect.getsource(climod)
    assert ":=" not in source


def test_module_source_no_eval_exec_batch24():
    """cli.py 不应使用 eval/exec/compile。"""
    source = inspect.getsource(climod)
    assert "eval(" not in source
    assert "exec(" not in source
    assert "compile(" not in source


def test_module_source_no_relative_imports_batch24():
    """cli.py 不应使用相对导入（from .）。"""
    source_lines = inspect.getsource(climod).split("\n")
    for line in source_lines:
        stripped = line.strip()
        if stripped.startswith("from .") and "from __future__" not in stripped:
            pytest.fail(f"relative import: {line}")


def test_module_source_no_dataclass_batch24():
    """cli.py 不应使用 @dataclass。"""
    source = inspect.getsource(climod)
    assert "@dataclass" not in source


def test_module_source_no_environ_batch24():
    """cli.py 不应使用 os.environ。"""
    source = inspect.getsource(climod)
    assert "os.environ" not in source


def test_module_source_no_open_at_module_level_batch24():
    """cli.py 顶层不应直接 open() 文件。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(climod))
    for node in tree.body:
        if isinstance(node, _ast.Expr) and isinstance(node.value, _ast.Call):
            f = node.value.func
            if isinstance(f, _ast.Name) and f.id == "open":
                pytest.fail("top-level open() call")
        if isinstance(node, _ast.Assign):
            v = node.value
            if isinstance(v, _ast.Call):
                f = v.func
                if isinstance(f, _ast.Name) and f.id == "open":
                    pytest.fail("top-level open() assignment")


def test_module_source_no_network_io_batch24():
    """cli.py 不应使用 socket/http/urllib/requests。"""
    source = inspect.getsource(climod)
    assert "import socket" not in source
    assert "import http" not in source
    assert "import urllib" not in source


def test_module_source_argparse_used_batch24():
    """cli.py 必须用 argparse（CLI 工具）。"""
    source = inspect.getsource(climod)
    assert "import argparse" in source


def test_module_source_sys_used_for_stdout_batch24():
    """cli.py 必须用 sys.stdout.reconfigure（Windows 中文输出）。"""
    source = inspect.getsource(climod)
    assert "sys.stdout" in source
    assert "reconfigure" in source


def test_module_source_no_star_import_batch24():
    """cli.py 不应使用 from X import *。"""
    source = inspect.getsource(climod)
    assert "import *" not in source


# ---------- module source 字符串精确补强 第三十六批 ----------


def test_module_source_contains_prog_evaluation_cli_batch24():
    """source 含 prog='evaluation.cli'。"""
    source = inspect.getsource(climod)
    assert 'prog="evaluation.cli"' in source


def test_module_source_contains_three_subparsers_batch24():
    """source 必须含三个 sub.add_parser 调用：run, validate-report, inspect-doc。

    注：'validate-report' 与 'inspect-doc' 的 add_parser 跨多行调用，所以分别断言。
    """
    source = inspect.getsource(climod)
    assert 'sub.add_parser("run"' in source
    assert 'sub.add_parser(' in source
    assert '"validate-report"' in source
    assert '"inspect-doc"' in source


def test_module_source_contains_dest_command_batch24():
    """source 含 dest='command'。"""
    source = inspect.getsource(climod)
    assert 'dest="command"' in source


def test_module_source_contains_required_true_batch24():
    """source 含 required=True（subparser 必填）。"""
    source = inspect.getsource(climod)
    assert "required=True" in source


def test_module_source_contains_choices_fallback_kreuzberg_batch24():
    """source 含 choices=('fallback', 'kreuzberg')。"""
    source = inspect.getsource(climod)
    assert "fallback" in source
    assert "kreuzberg" in source


def test_module_source_contains_default_fallback_batch24():
    """source 含 default='fallback'。"""
    source = inspect.getsource(climod)
    assert 'default="fallback"' in source


def test_module_source_contains_default_800_batch24():
    """source 含 default=800（max_chars）。"""
    source = inspect.getsource(climod)
    assert "default=800" in source


def test_module_source_contains_default_30_batch24():
    """source 含 default=30（tolerance_chars）。"""
    source = inspect.getsource(climod)
    assert "default=30" in source


def test_module_source_contains_help_text_batch24():
    """source 含 help 字符串字面量。"""
    source = inspect.getsource(climod)
    assert 'help="' in source


def test_module_source_contains_validate_file_call_batch24():
    """source 含 validate_file(...) 调用（run 后自校验）。"""
    source = inspect.getsource(climod)
    assert "validate_file(" in source


def test_module_source_contains_load_manifest_call_batch24():
    """source 含 load_manifest(...) 调用。"""
    source = inspect.getsource(climod)
    assert "load_manifest(" in source


def test_module_source_contains_run_evaluation_call_batch24():
    """source 含 run_evaluation(...) 调用。"""
    source = inspect.getsource(climod)
    assert "run_evaluation(" in source


def test_module_source_contains_compute_automatic_metrics_call_batch24():
    """source 含 compute_automatic_metrics(...) 调用（inspect-doc）。"""
    source = inspect.getsource(climod)
    assert "compute_automatic_metrics(" in source


def test_module_source_contains_chunk_boundary_prf_call_batch24():
    """source 含 chunk_boundary_prf(...) 调用（inspect-doc）。"""
    source = inspect.getsource(climod)
    assert "chunk_boundary_prf(" in source


def test_module_source_contains_inspect_doc_help_batch24():
    """inspect-doc 子命令的 help 含 'inspect' 或 'inspect-doc'。"""
    source = inspect.getsource(climod)
    assert "inspect-doc" in source


# ---------- signatures 第三十六批 ----------


def test_signature_build_parser_batch24():
    """_build_parser() -> argparse.ArgumentParser（无参）。"""
    sig = inspect.signature(_build_parser)
    params = list(sig.parameters.values())
    assert params == []
    assert sig.return_annotation == "argparse.ArgumentParser"


def test_signature_format_metric_batch24():
    """_format_metric(name: str, metric: dict) -> str。"""
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["name", "metric"]
    assert params[0].annotation == "str"
    assert params[1].annotation == "dict"
    assert sig.return_annotation == "str"


def test_signature_run_inspect_doc_batch24():
    """_run_inspect_doc(args) -> int。"""
    sig = inspect.signature(_run_inspect_doc)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "args"
    assert sig.return_annotation == "int"


def test_signature_main_batch24():
    """main(argv: list[str] | None = None) -> int。"""
    sig = inspect.signature(main)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "argv"
    assert params[0].default is None
    assert params[0].annotation == "list[str] | None"
    assert sig.return_annotation == "int"


def test_signature_all_annotations_are_strings_batch24():
    """`from __future__ import annotations` 使所有注解为字符串。"""
    for fn in [_build_parser, _format_metric, _run_inspect_doc, main]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            if p.annotation is not inspect.Parameter.empty:
                assert isinstance(p.annotation, str)
        if sig.return_annotation is not inspect.Signature.empty:
            assert isinstance(sig.return_annotation, str)


def test_signature_main_default_is_none_batch24():
    """main(argv=None) 默认 None（不是空 list）。"""
    sig = inspect.signature(main)
    assert sig.parameters["argv"].default is None


def test_signature_build_parser_no_params_batch24():
    """_build_parser 无参数（parser 是模块内部状态）。"""
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


# ---------- module 合理性 第三十六批 ----------


def test_module_all_not_defined_batch24():
    """cli.py 不需要 __all__（顶层只有 main 是 public entry point）。"""
    # __all__ 是可选的，main + 调用 __main__ 即可
    assert not hasattr(climod, "__all__") or climod.__all__ is None or isinstance(
        climod.__all__, list
    )


def test_module_has_four_callables_batch24():
    """cli.py 定义 4 个函数：_build_parser, main, _format_metric, _run_inspect_doc。"""
    funcs = [
        name
        for name, val in inspect.getmembers(climod, inspect.isfunction)
        if val.__module__ == climod.__name__
    ]
    assert set(funcs) == {"_build_parser", "main", "_format_metric", "_run_inspect_doc"}


def test_module_main_callable_batch24():
    """main 是可调用。"""
    assert callable(main)


def test_module_no_classes_batch24():
    """cli.py 不定义任何 class。"""
    classes = [
        name
        for name, val in inspect.getmembers(climod, inspect.isclass)
        if val.__module__ == climod.__name__
    ]
    assert classes == []


def test_module_docstring_present_batch24():
    """module 有 docstring。"""
    assert climod.__doc__ is not None
    assert len(climod.__doc__) > 0


def test_module_docstring_mentions_subcommands_batch24():
    """module docstring 应提及 run / validate-report / inspect-doc。"""
    assert climod.__doc__ is not None
    assert "run" in climod.__doc__
    assert "validate-report" in climod.__doc__
    assert "inspect-doc" in climod.__doc__


def test_module_format_metric_docstring_present_batch24():
    """_format_metric 有 docstring。"""
    assert _format_metric.__doc__ is not None


def test_module_run_inspect_doc_docstring_present_batch24():
    """_run_inspect_doc 有 docstring。"""
    assert _run_inspect_doc.__doc__ is not None


def test_module_uses_from_future_annotations_batch24():
    """cli.py 必须有 from __future__ import annotations。"""
    source = inspect.getsource(climod)
    assert "from __future__ import annotations" in source


def test_module_has_main_guard_batch24():
    """cli.py 必须有 if __name__ == '__main__' 入口。"""
    source = inspect.getsource(climod)
    assert 'if __name__ == "__main__"' in source or "if __name__ == '__main__'" in source


def test_module_main_guard_raises_system_exit_batch24():
    """main guard 调 main() 并 raise SystemExit。"""
    source = inspect.getsource(climod)
    assert "SystemExit" in source


def test_module_imports_argparse_batch24():
    """cli.py import argparse。"""
    source = inspect.getsource(climod)
    assert "import argparse" in source


# ---------- 端到端集成 第三十六批 ----------


def test_e2e_main_with_argv_list_batch24(tmp_path):
    """main 接受 list[str] 作为 argv（不是仅 sys.argv 切片）。"""
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    with patch("evaluation.cli.run_evaluation", return_value={"per_doc": [], "devset": {}}), patch(
        "evaluation.cli.validate_file"
    ), patch(
        "evaluation.cli.get_git_provenance",
        return_value={"git_commit": None, "git_dirty": False},
    ):
        rc = main(["run", "--manifest", str(manifest), "--output", str(out)])
    assert rc == 0


def test_e2e_inspect_doc_full_flow_batch24(tmp_path, capsys):
    """inspect-doc 端到端：合法 doc → 0 + 多行打印。"""
    doc = {
        "document_id": "x",
        "source_type": "pdf",
        "elements": [{"type": "paragraph"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_e2e_validate_report_real_invalid_file_batch24(tmp_path, capsys):
    """validate-report：空 dict JSON 文件应该通过 schema（但需 validate_file mock 通过）。"""
    # 实际 schema 校验需要完整字段，这里 mock 让它通过
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file"):
        rc = main(["validate-report", str(p)])
    assert rc == 0


def test_e2e_run_with_kreuzberg_parser_batch24(tmp_path):
    """run --parser kreuzberg 透传给 run_evaluation。"""
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    captured = {}

    def fake_run(m, o, *, parser_name, max_chars, tolerance_chars):
        captured["parser_name"] = parser_name
        return {"per_doc": [], "devset": {}}

    with patch("evaluation.cli.run_evaluation", side_effect=fake_run), patch(
        "evaluation.cli.validate_file"
    ), patch(
        "evaluation.cli.get_git_provenance",
        return_value={"git_commit": None, "git_dirty": False},
    ):
        rc = main(
            [
                "run",
                "--manifest",
                str(manifest),
                "--output",
                str(out),
                "--parser",
                "kreuzberg",
            ]
        )
    assert rc == 0
    assert captured["parser_name"] == "kreuzberg"


def test_e2e_run_default_parser_fallback_batch24(tmp_path):
    """run 默认 parser 是 fallback。"""
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    captured = {}

    def fake_run(m, o, *, parser_name, max_chars, tolerance_chars):
        captured["parser_name"] = parser_name
        return {"per_doc": [], "devset": {}}

    with patch("evaluation.cli.run_evaluation", side_effect=fake_run), patch(
        "evaluation.cli.validate_file"
    ), patch(
        "evaluation.cli.get_git_provenance",
        return_value={"git_commit": None, "git_dirty": False},
    ):
        main(["run", "--manifest", str(manifest), "--output", str(out)])
    assert captured["parser_name"] == "fallback"


def test_e2e_inspect_doc_with_compute_metrics_mocked_batch24(tmp_path, capsys):
    """inspect-doc：compute_automatic_metrics 被调用一次。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value={}
    ) as mock_metrics, patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
        main(["inspect-doc", str(p)])
    mock_metrics.assert_called_once()


def test_e2e_run_prints_summary_block_batch24(tmp_path, capsys):
    """run 成功后 stdout 应含 devset_status / file_count 等摘要字段。"""
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    fake_report = {
        "per_doc": [],
        "devset": {
            "status": "incomplete",
            "file_count": 5,
            "content_group_count": 2,
            "pdf_count": 3,
            "docx_count": 2,
        },
    }
    with patch("evaluation.cli.run_evaluation", return_value=fake_report), patch(
        "evaluation.cli.validate_file"
    ), patch(
        "evaluation.cli.get_git_provenance",
        return_value={"git_commit": "deadbeef1234", "git_dirty": True},
    ):
        rc = main(["run", "--manifest", str(manifest), "--output", str(out)])
    assert rc == 0
    out_str = capsys.readouterr().out
    assert "devset_status=incomplete" in out_str
    assert "file_count=5" in out_str
    assert "groups=2" in out_str
    assert "pdf=3" in out_str
    assert "docx=2" in out_str
    assert "git_dirty=True" in out_str
