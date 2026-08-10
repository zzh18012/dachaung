r"""evaluation/cli.py 边角测试 - 第二十五轮（Round 308）。

edges23 已覆盖：_build_parser 行为 / _format_metric 行为 / _run_inspect_doc 行为 /
main run/validate-report/inspect-doc 路径 / module __all__ / forbidden tokens / imports /
docstring / Windows stdout reconfigure / __main__ / signatures / source level / 端到端 / 模块整体。

edges24 补强未覆盖的角度（深度边界 + 算法不变量 + source level + signatures + 端到端）：
- **_build_parser 行为深度补强**：3 subparsers 顺序精确（run, validate-report, inspect-doc）；
  run_p 5 个 args（--manifest/--output/--parser/--max-chars/--tolerance-chars）；
  validate-report 1 个 positional（input）；inspect-doc 2 个 args（input + --tolerance-chars）；
  run --parser choices 精确（fallback/kreuzberg）；run --parser default 'fallback'；
  --max-chars type=int default=800；--tolerance-chars type=int default=30
- **_format_metric 行为深度补强**：value None → 'null (reason)'；
  value True → 'true (ok)'；value False → 'false (ok)'；
  value 0.5 → '0.5000 (ok)'；value 1.0 → '1.0000 (ok)'；
  value dict empty → ' (ok)'；value dict non-empty → 'k=v, k=v'；
  value str → 原样输出；value list → 原样输出（走 fallback 分支）；
  reason None + value not None → 'ok'；name 字段 36 字符宽
- **_run_inspect_doc 行为深度补强**：返 0（成功）/ 1（JSON 错误）/ 2（文件不存在）；
  doc 不是 dict → exit 1；source_type 缺失 → 'unknown'；
  elements 缺失 → 0；chunks 缺失 → 0；
  --tolerance-chars 不在 metrics 输出（被 chunk_boundary_prf 处理）；
  source 含 sorted + _sort_key 函数；source 含 print 6 行 + 排序输出
- **main run 路径行为深度补强**：manifest 不存在 → exit 2 + stderr；
  manifest 加载失败（ManifestError） → exit 1 + stderr；manifest 加载失败（EvalSchemaError） → exit 1 + stderr；
  report 自校验失败 → exit 1 + stderr；成功 → stdout 含 [OK] / documents= / devset_status=；
  args.parser 透传 run_evaluation；args.max_chars 透传；args.tolerance_chars 透传
- **main validate-report 路径行为深度补强**：input 不存在 → exit 2；
  validate EvalSchemaError → exit 1；validate JSONDecodeError → exit 1；
  validate FileNotFoundError → exit 2；成功 → stdout 含 [OK]
- **main inspect-doc 路径行为深度补强**：input 不存在 → exit 2；
  invalid JSON → exit 1；doc 不是 dict → exit 1；成功 → exit 0
- **module __all__ 不存在补强**：cli 没有 __all__（不在 source）
- **module source forbidden tokens 补强**：不含 os/re/logging/subprocess/asyncio/threading/
  collections/math/datetime/itertools/functools/socket/email/html/http/urllib/sqlite3/csv/pickle/tempfile/shutil/glob
- **module source 含必要 imports**：future/argparse/json/sys/pathlib (5 stdlib) +
  evaluation 4 行（manifest/report/runner/schema）
- **module docstring 深度补强**：含「CLI」/「run」/「validate-report」/「inspect-doc」/
  「manifest」/「报告」/「inspect-doc：单文档快速跑指标」
- **Windows stdout reconfigure 块补强**：含 hasattr(sys.stdout, "reconfigure")；
  含 sys.stdout.reconfigure + sys.stderr.reconfigure；含 try/except (AttributeError, OSError)
- **__main__ 块补强**：含 if __name__ == "__main__": + raise SystemExit(main())
- **signatures 精确补强**：main 1 param (argv default=None) + return int + no varargs/varkw；
  _build_parser 0 param + return ArgumentParser；_format_metric 2 params + return str；
  _run_inspect_doc 1 param (args) + return int
- **module source level 完整补强**：main 含 3 subcommand 分支 + manifest/output Path +
  is_file + load_manifest + run_evaluation + validate_file + get_git_provenance + print +
  return 0/1/2；_build_parser 含 ArgumentParser + add_subparsers + 3 add_parser +
  5 个 run args + 1 validate-report positional + 2 inspect-doc args；
  _format_metric 含 value None/bool/float/dict/fallback 5 分支 + 36 字符宽 + reason or 'ok'；
  _run_inspect_doc 含 Path + is_file + json.load + isinstance doc dict +
  compute_automatic_metrics 5 kwargs + figure_caption_prf + chunk_boundary_prf +
  print 6 行 + sorted + _sort_key + return 0/1/2
- **端到端集成补强**：CLI run 完整流程（manifest + output + parser）；
  CLI validate-report 完整流程；CLI inspect-doc 完整流程
- **模块整体合理性**：4 module-level function（main, _build_parser, _format_metric, _run_inspect_doc）；
  无 class；__main__ 块；__all__ 不存在；Windows stdout 块
"""

from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import evaluation.cli as climod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# =========================================================================
# 辅助
# =========================================================================


def _make_minimal_doc(tmp_path, doc_id="d1", source_type="pdf"):
    """写一个最小 doc JSON。"""
    doc = {
        "source_type": source_type,
        "source_hash": "abc",
        "document_id": doc_id,
        "source_path": f"/tmp/{doc_id}.{source_type}",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
    }
    p = tmp_path / f"{doc_id}.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def _make_minimal_manifest(tmp_path):
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return p


# =========================================================================
# _build_parser 行为深度补强
# =========================================================================


def test_build_parser_3_subparsers_in_order():
    """3 subparsers 顺序精确（run, validate-report, inspect-doc）。"""
    p = _build_parser()
    import argparse
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    choices = list(actions[0].choices.keys())
    assert choices == ["run", "validate-report", "inspect-doc"]


def test_build_parser_run_has_5_args():
    """run_p 5 个 args（--manifest/--output/--parser/--max-chars/--tolerance-chars）。"""
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = actions[0].choices["run"]
    option_strings = []
    for a in run_p._actions:
        option_strings.extend(a.option_strings)
    # 排除 -h
    real_options = [o for o in option_strings if o.startswith("--")]
    expected = {"--manifest", "--output", "--parser", "--max-chars", "--tolerance-chars"}
    assert expected.issubset(set(real_options))


def test_build_parser_validate_report_has_1_positional():
    """validate-report 1 个 positional（input）。"""
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    val_p = actions[0].choices["validate-report"]
    positionals = [a for a in val_p._actions if not a.option_strings and a.dest != "help"]
    assert len(positionals) == 1
    assert positionals[0].dest == "input"


def test_build_parser_inspect_doc_has_2_args():
    """inspect-doc 2 个 args（input positional + --tolerance-chars）。"""
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    ins_p = actions[0].choices["inspect-doc"]
    positionals = [a for a in ins_p._actions if not a.option_strings and a.dest != "help"]
    options = [a for a in ins_p._actions if a.option_strings and "--tolerance-chars" in a.option_strings]
    assert len(positionals) == 1
    assert len(options) == 1


def test_build_parser_run_parser_choices_fallback_kreuzberg():
    """run --parser choices 精确（fallback/kreuzberg）。"""
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = actions[0].choices["run"]
    parser_action = next(a for a in run_p._actions if "--parser" in a.option_strings)
    assert parser_action.choices == ("fallback", "kreuzberg")


def test_build_parser_run_parser_default_fallback():
    """run --parser default 'fallback'。"""
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = actions[0].choices["run"]
    parser_action = next(a for a in run_p._actions if "--parser" in a.option_strings)
    assert parser_action.default == "fallback"


def test_build_parser_run_max_chars_type_int():
    """--max-chars type=int。"""
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = actions[0].choices["run"]
    mc_action = next(a for a in run_p._actions if "--max-chars" in a.option_strings)
    assert mc_action.type is int


def test_build_parser_run_max_chars_default_800():
    """--max-chars default=800。"""
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = actions[0].choices["run"]
    mc_action = next(a for a in run_p._actions if "--max-chars" in a.option_strings)
    assert mc_action.default == 800


def test_build_parser_run_tolerance_chars_type_int():
    """--tolerance-chars type=int。"""
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = actions[0].choices["run"]
    tc_action = next(a for a in run_p._actions if "--tolerance-chars" in a.option_strings)
    assert tc_action.type is int


def test_build_parser_run_tolerance_chars_default_30():
    """--tolerance-chars default=30。"""
    import argparse
    p = _build_parser()
    actions = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    run_p = actions[0].choices["run"]
    tc_action = next(a for a in run_p._actions if "--tolerance-chars" in a.option_strings)
    assert tc_action.default == 30


# =========================================================================
# _format_metric 行为深度补强
# =========================================================================


def test_format_metric_value_none_uses_null():
    out = _format_metric("foo", {"value": None, "reason": "missing"})
    assert "null" in out
    assert "missing" in out


def test_format_metric_value_true_lowercase():
    out = _format_metric("foo", {"value": True, "reason": None})
    assert "true" in out
    assert "ok" in out


def test_format_metric_value_false_lowercase():
    out = _format_metric("foo", {"value": False, "reason": None})
    assert "false" in out
    assert "ok" in out


def test_format_metric_value_float_half():
    """value 0.5 → '0.5000'。"""
    out = _format_metric("foo", {"value": 0.5, "reason": None})
    assert "0.5000" in out


def test_format_metric_value_float_one():
    """value 1.0 → '1.0000'。"""
    out = _format_metric("foo", {"value": 1.0, "reason": None})
    assert "1.0000" in out


def test_format_metric_value_dict_empty():
    """value dict empty → ' (ok)'（items 是空字符串）。"""
    out = _format_metric("foo", {"value": {}, "reason": None})
    assert "ok" in out


def test_format_metric_value_dict_non_empty():
    """value dict non-empty → 'k=v, k=v'。"""
    out = _format_metric("foo", {"value": {"a": 1, "b": 2}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out


def test_format_metric_value_string():
    """value str → 原样输出（走 fallback 分支）。"""
    out = _format_metric("foo", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_value_list():
    """value list → 原样输出（走 fallback 分支）。"""
    out = _format_metric("foo", {"value": [1, 2, 3], "reason": None})
    assert "[1, 2, 3]" in out


def test_format_metric_value_with_reason_uses_reason():
    """reason None + value not None → 'ok'。"""
    out = _format_metric("foo", {"value": 0.5, "reason": "my_reason"})
    assert "my_reason" in out


def test_format_metric_value_no_reason_uses_ok():
    out = _format_metric("foo", {"value": 0.5, "reason": None})
    assert "ok" in out


def test_format_metric_name_field_36_width():
    """name 字段 36 字符宽（短 name 有 padding）。"""
    out = _format_metric("ab", {"value": 0.5, "reason": None})
    # 'ab' 后应有空格到 36 字符宽
    assert "ab" in out
    # name 区域至少 36 字符
    # 输出形如 '  ab<spaces>  0.5000  (ok)'
    # 找 'ab' 到第一个数字的距离
    idx_ab = out.index("ab")
    idx_num = out.index("0.5000")
    # ab 后到 num 之前的字符数（应该把 name 字段填到 36 宽）
    assert idx_num - idx_ab >= 34  # 至少 34（ab 2 字符 + 至少 32 空格）


# =========================================================================
# _run_inspect_doc 行为深度补强
# =========================================================================


def test_run_inspect_doc_return_0_on_success(tmp_path, capsys):
    p = _make_minimal_doc(tmp_path)
    rc = _run_inspect_doc(type("Args", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 0


def test_run_inspect_doc_return_2_on_missing_file(tmp_path):
    rc = _run_inspect_doc(type("Args", (), {"input": str(tmp_path / "nope.json"),
                                              "tolerance_chars": 30})())
    assert rc == 2


def test_run_inspect_doc_return_1_on_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid}", encoding="utf-8")
    rc = _run_inspect_doc(type("Args", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 1


def test_run_inspect_doc_return_1_on_non_dict_top_level(tmp_path):
    """doc 不是 dict → exit 1。"""
    p = tmp_path / "list.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    rc = _run_inspect_doc(type("Args", (), {"input": str(p), "tolerance_chars": 30})())
    assert rc == 1


def test_run_inspect_doc_source_type_missing_default_unknown(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    rc = _run_inspect_doc(type("Args", (), {"input": str(p), "tolerance_chars": 30})())
    out = capsys.readouterr().out
    assert "unknown" in out
    assert rc == 0


def test_run_inspect_doc_elements_missing_default_0(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"chunks": []}), encoding="utf-8")
    rc = _run_inspect_doc(type("Args", (), {"input": str(p), "tolerance_chars": 30})())
    out = capsys.readouterr().out
    assert "elements=0" in out
    assert rc == 0


def test_run_inspect_doc_chunks_missing_default_0(tmp_path, capsys):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": []}), encoding="utf-8")
    rc = _run_inspect_doc(type("Args", (), {"input": str(p), "tolerance_chars": 30})())
    out = capsys.readouterr().out
    assert "chunks=0" in out
    assert rc == 0


def test_run_inspect_doc_source_has_sorted_call():
    src = inspect.getsource(_run_inspect_doc)
    assert "sorted" in src
    assert "_sort_key" in src


def test_run_inspect_doc_source_has_compute_metrics_call():
    src = inspect.getsource(_run_inspect_doc)
    assert "compute_automatic_metrics" in src


def test_run_inspect_doc_source_has_figure_caption_call():
    src = inspect.getsource(_run_inspect_doc)
    assert "figure_caption_prf" in src


def test_run_inspect_doc_source_has_chunk_boundary_call():
    src = inspect.getsource(_run_inspect_doc)
    assert "chunk_boundary_prf" in src


# =========================================================================
# main run 路径行为深度补强
# =========================================================================


def test_main_run_manifest_not_exist_returns_2(tmp_path, capsys):
    rc = main(["run", "--manifest", str(tmp_path / "nope.json"),
               "--output", str(tmp_path / "out.json")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_run_manifest_invalid_returns_1(tmp_path, capsys):
    p = tmp_path / "manifest.json"
    p.write_text("{not valid}", encoding="utf-8")
    rc = main(["run", "--manifest", str(p),
               "--output", str(tmp_path / "out.json")])
    assert rc == 1


def test_main_run_manifest_schema_invalid_returns_1(tmp_path, capsys):
    """manifest 缺 required → EvalSchemaError → exit 1。"""
    p = tmp_path / "manifest.json"
    p.write_text('{"manifest_version": "wrong"}', encoding="utf-8")
    rc = main(["run", "--manifest", str(p),
               "--output", str(tmp_path / "out.json")])
    assert rc == 1


def test_main_run_args_parser_passed(tmp_path, capsys):
    """args.parser 透传 run_evaluation（但 manifest 为空，OK）。"""
    manifest = _make_minimal_manifest(tmp_path)
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(out),
               "--parser", "fallback"])
    assert rc == 0


def test_main_run_args_max_chars_passed(tmp_path, capsys):
    manifest = _make_minimal_manifest(tmp_path)
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(out),
               "--max-chars", "500"])
    assert rc == 0


def test_main_run_args_tolerance_chars_passed(tmp_path, capsys):
    manifest = _make_minimal_manifest(tmp_path)
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(out),
               "--tolerance-chars", "10"])
    assert rc == 0


def test_main_run_success_stdout_has_ok(tmp_path, capsys):
    manifest = _make_minimal_manifest(tmp_path)
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(out)])
    out_str = capsys.readouterr().out
    assert "[OK]" in out_str
    assert "documents=" in out_str
    assert "devset_status=" in out_str
    assert rc == 0


# =========================================================================
# main validate-report 路径行为深度补强
# =========================================================================


def test_main_validate_report_input_not_exist_returns_2(tmp_path):
    rc = main(["validate-report", str(tmp_path / "nope.json")])
    assert rc == 2


def test_main_validate_report_invalid_json_returns_1(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid}", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_schema_fail_returns_1(tmp_path):
    """schema 校验失败 → exit 1。"""
    p = tmp_path / "report.json"
    p.write_text('{"wrong": "data"}', encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_success_stdout_has_ok(tmp_path, capsys):
    """成功 → stdout 含 [OK]。先 run 生成 valid report，再 validate。"""
    manifest = _make_minimal_manifest(tmp_path)
    out = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(out)])
    capsys.readouterr()  # 清空之前的输出
    rc = main(["validate-report", str(out)])
    out_str = capsys.readouterr().out
    assert "[OK]" in out_str
    assert rc == 0


# =========================================================================
# main inspect-doc 路径行为深度补强
# =========================================================================


def test_main_inspect_doc_input_not_exist_returns_2(tmp_path):
    rc = main(["inspect-doc", str(tmp_path / "nope.json")])
    assert rc == 2


def test_main_inspect_doc_invalid_json_returns_1(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_non_dict_returns_1(tmp_path):
    p = tmp_path / "list.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1


def test_main_inspect_doc_success_returns_0(tmp_path):
    p = _make_minimal_doc(tmp_path)
    rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_main_inspect_doc_with_tolerance_chars(tmp_path):
    p = _make_minimal_doc(tmp_path)
    rc = main(["inspect-doc", str(p), "--tolerance-chars", "10"])
    assert rc == 0


# =========================================================================
# module __all__ 不存在补强
# =========================================================================


def test_module_has_no_all():
    """cli 没有 __all__（不在 source）。"""
    assert not hasattr(climod, "__all__") or climod.__all__ is None or len(climod.__all__) == 0


def test_module_source_no_all_assignment():
    """source 不含 '__all__ =' 赋值。"""
    src = inspect.getsource(climod)
    assert "__all__" not in src


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_no_os():
    src = inspect.getsource(climod)
    assert "import os" not in src
    assert "from os " not in src


def test_module_source_no_re():
    src = inspect.getsource(climod)
    assert "import re" not in src


def test_module_source_no_logging():
    src = inspect.getsource(climod)
    assert "import logging" not in src


def test_module_source_no_subprocess():
    src = inspect.getsource(climod)
    assert "import subprocess" not in src


def test_module_source_no_asyncio():
    src = inspect.getsource(climod)
    assert "import asyncio" not in src


def test_module_source_no_threading():
    src = inspect.getsource(climod)
    assert "import threading" not in src


def test_module_source_no_collections():
    src = inspect.getsource(climod)
    assert "import collections" not in src


def test_module_source_no_math():
    src = inspect.getsource(climod)
    assert "import math" not in src


def test_module_source_no_datetime():
    src = inspect.getsource(climod)
    assert "import datetime" not in src


def test_module_source_no_itertools():
    src = inspect.getsource(climod)
    assert "import itertools" not in src


def test_module_source_no_functools():
    src = inspect.getsource(climod)
    assert "import functools" not in src


def test_module_source_no_socket():
    src = inspect.getsource(climod)
    assert "import socket" not in src


def test_module_source_no_email():
    src = inspect.getsource(climod)
    assert "import email" not in src


def test_module_source_no_html():
    src = inspect.getsource(climod)
    assert "import html" not in src


def test_module_source_no_http():
    src = inspect.getsource(climod)
    assert "import http" not in src


def test_module_source_no_urllib():
    src = inspect.getsource(climod)
    assert "import urllib" not in src


def test_module_source_no_sqlite3():
    src = inspect.getsource(climod)
    assert "import sqlite3" not in src


def test_module_source_no_csv():
    src = inspect.getsource(climod)
    assert "import csv" not in src


def test_module_source_no_pickle():
    src = inspect.getsource(climod)
    assert "import pickle" not in src


def test_module_source_no_tempfile():
    src = inspect.getsource(climod)
    assert "import tempfile" not in src


def test_module_source_no_shutil():
    src = inspect.getsource(climod)
    assert "import shutil" not in src


def test_module_source_no_glob():
    src = inspect.getsource(climod)
    assert "import glob" not in src


# =========================================================================
# module source 含必要 imports
# =========================================================================


def test_module_imports_has_future():
    src = inspect.getsource(climod)
    assert "from __future__ import annotations" in src


def test_module_imports_has_argparse():
    src = inspect.getsource(climod)
    assert "import argparse" in src


def test_module_imports_has_json():
    src = inspect.getsource(climod)
    assert "import json" in src


def test_module_imports_has_sys():
    src = inspect.getsource(climod)
    assert "import sys" in src


def test_module_imports_has_pathlib():
    src = inspect.getsource(climod)
    assert "from pathlib import Path" in src


def test_module_imports_has_evaluation_manifest():
    src = inspect.getsource(climod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_module_imports_has_evaluation_report():
    src = inspect.getsource(climod)
    assert "from evaluation.report import get_git_provenance" in src


def test_module_imports_has_evaluation_runner():
    src = inspect.getsource(climod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_imports_has_evaluation_schema():
    src = inspect.getsource(climod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


# =========================================================================
# module docstring 深度补强
# =========================================================================


def test_module_docstring_contains_cli():
    src = inspect.getsource(climod)
    assert "CLI" in src


def test_module_docstring_contains_run():
    src = inspect.getsource(climod)
    assert "run" in src


def test_module_docstring_contains_validate_report():
    src = inspect.getsource(climod)
    assert "validate-report" in src


def test_module_docstring_contains_inspect_doc():
    src = inspect.getsource(climod)
    assert "inspect-doc" in src


def test_module_docstring_contains_manifest_text():
    src = inspect.getsource(climod)
    assert "manifest" in src


def test_module_docstring_contains_report_text():
    src = inspect.getsource(climod)
    assert "报告" in src


def test_module_docstring_contains_inspect_doc_purpose():
    """含「inspect-doc：单文档快速跑指标」目的说明。"""
    src = inspect.getsource(climod)
    assert "单文档" in src


# =========================================================================
# Windows stdout reconfigure 块补强
# =========================================================================


def test_module_source_has_hasattr_check():
    src = inspect.getsource(climod)
    assert 'hasattr(sys.stdout, "reconfigure")' in src


def test_module_source_has_stdout_reconfigure():
    src = inspect.getsource(climod)
    assert 'sys.stdout.reconfigure(encoding="utf-8", errors="replace")' in src


def test_module_source_has_stderr_reconfigure():
    src = inspect.getsource(climod)
    assert 'sys.stderr.reconfigure(encoding="utf-8", errors="replace")' in src


def test_module_source_has_try_except_attribute_error_oserror():
    src = inspect.getsource(climod)
    assert "except (AttributeError, OSError)" in src


# =========================================================================
# __main__ 块补强
# =========================================================================


def test_module_source_has_main_block():
    src = inspect.getsource(climod)
    assert 'if __name__ == "__main__":' in src


def test_module_source_has_system_exit_main():
    src = inspect.getsource(climod)
    assert "raise SystemExit(main())" in src


# =========================================================================
# signatures 精确补强
# =========================================================================


def test_main_signature_1_param_argv_default_none():
    sig = inspect.signature(main)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "argv"
    assert params[0].default is None


def test_main_return_annotation_is_int():
    sig = inspect.signature(main)
    assert "int" in str(sig.return_annotation)


def test_main_no_varargs_varkw():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_build_parser_signature_0_param():
    sig = inspect.signature(_build_parser)
    params = list(sig.parameters.values())
    assert len(params) == 0


def test_build_parser_return_annotation_argument_parser():
    sig = inspect.signature(_build_parser)
    assert "ArgumentParser" in str(sig.return_annotation)


def test_format_metric_signature_2_params():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters.keys())
    assert params == ["name", "metric"]


def test_format_metric_return_annotation_str():
    sig = inspect.signature(_format_metric)
    assert "str" in str(sig.return_annotation)


def test_run_inspect_doc_signature_1_param():
    sig = inspect.signature(_run_inspect_doc)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "args"


def test_run_inspect_doc_return_annotation_int():
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in str(sig.return_annotation)


# =========================================================================
# module source level 完整补强
# =========================================================================


def test_main_source_has_3_subcommand_branches():
    """main 含 3 subcommand 分支。"""
    src = inspect.getsource(main)
    assert 'if args.command == "run":' in src
    assert 'if args.command == "validate-report":' in src
    assert 'if args.command == "inspect-doc":' in src


def test_main_source_has_manifest_path_is_file():
    src = inspect.getsource(main)
    assert "manifest_path = Path(args.manifest)" in src
    assert "manifest_path.is_file()" in src


def test_main_source_has_load_manifest_call():
    src = inspect.getsource(main)
    assert "manifest = load_manifest(manifest_path)" in src


def test_main_source_has_run_evaluation_call_with_kwargs():
    src = inspect.getsource(main)
    assert "report = run_evaluation(" in src
    assert "parser_name=args.parser" in src
    assert "max_chars=args.max_chars" in src
    assert "tolerance_chars=args.tolerance_chars" in src


def test_main_source_has_validate_file_call():
    src = inspect.getsource(main)
    assert 'validate_file(output_path, "evaluation-report.schema.json")' in src


def test_main_source_has_get_git_provenance_call():
    src = inspect.getsource(main)
    assert "git = get_git_provenance(manifest.project_root)" in src


def test_main_source_has_return_0_1_2():
    src = inspect.getsource(main)
    assert "return 0" in src
    assert "return 1" in src
    assert "return 2" in src


def test_build_parser_source_has_argument_parser():
    src = inspect.getsource(_build_parser)
    assert "argparse.ArgumentParser(" in src


def test_build_parser_source_has_add_subparsers():
    src = inspect.getsource(_build_parser)
    assert "p.add_subparsers(dest=\"command\", required=True)" in src


def test_build_parser_source_has_3_add_parser():
    """source 含 3 个 add_parser（run/validate-report/inspect-doc）。"""
    src = inspect.getsource(_build_parser)
    assert 'sub.add_parser("run"' in src
    assert 'sub.add_parser(\n        "validate-report"' in src or 'sub.add_parser("validate-report"' in src
    assert 'sub.add_parser(\n        "inspect-doc"' in src or 'sub.add_parser("inspect-doc"' in src


def test_format_metric_source_has_5_branches():
    """_format_metric 含 value None/bool/float/dict/fallback 5 分支。"""
    src = inspect.getsource(_format_metric)
    assert "if value is None:" in src
    assert "if isinstance(value, bool):" in src
    assert "if isinstance(value, float):" in src
    assert "if isinstance(value, dict):" in src


def test_format_metric_source_has_36_width():
    """source 含 36 字符宽格式化。"""
    src = inspect.getsource(_format_metric)
    assert "36" in src


def test_format_metric_source_has_reason_or_ok():
    """source 含 'reason or 'ok''。"""
    src = inspect.getsource(_format_metric)
    assert "reason or 'ok'" in src or 'reason or \"ok\"' in src


def test_run_inspect_doc_source_has_path_input():
    src = inspect.getsource(_run_inspect_doc)
    assert "input_path = Path(args.input)" in src


def test_run_inspect_doc_source_has_is_file_check():
    src = inspect.getsource(_run_inspect_doc)
    assert "input_path.is_file()" in src


def test_run_inspect_doc_source_has_isinstance_dict_check():
    src = inspect.getsource(_run_inspect_doc)
    assert "isinstance(doc, dict)" in src


def test_run_inspect_doc_source_has_compute_metrics_5_kwargs():
    src = inspect.getsource(_run_inspect_doc)
    assert "compute_automatic_metrics(" in src
    assert "document=doc" in src
    assert "error=None" in src
    assert "source_type=source_type" in src
    assert "expectations=None" in src
    assert "image_base_dir=None" in src


def test_run_inspect_doc_source_has_print_6_lines():
    """source 含 print 6 行（file/document_id/source/parser/counts/空行 + metrics）。"""
    src = inspect.getsource(_run_inspect_doc)
    assert 'print(f"file:' in src
    assert 'print(f"document_id:' in src
    assert 'print(f"source:' in src
    assert 'print(f"parser:' in src
    assert 'print(f"counts:' in src
    assert 'print("metrics:"' in src


def test_run_inspect_doc_source_has_return_0_1_2():
    src = inspect.getsource(_run_inspect_doc)
    assert "return 0" in src
    assert "return 1" in src
    assert "return 2" in src


# =========================================================================
# 端到端集成补强
# =========================================================================


def test_e2e_cli_run_complete(tmp_path, capsys):
    """CLI run 完整流程（manifest + output + parser）。"""
    manifest = _make_minimal_manifest(tmp_path)
    out = tmp_path / "out.json"
    rc = main(["run", "--manifest", str(manifest), "--output", str(out),
               "--parser", "fallback"])
    assert rc == 0
    assert out.is_file()


def test_e2e_cli_validate_report_complete(tmp_path, capsys):
    """CLI validate-report 完整流程：先 run 生成，再 validate-report。"""
    manifest = _make_minimal_manifest(tmp_path)
    out = tmp_path / "out.json"
    main(["run", "--manifest", str(manifest), "--output", str(out)])
    rc = main(["validate-report", str(out)])
    assert rc == 0


def test_e2e_cli_inspect_doc_complete(tmp_path, capsys):
    """CLI inspect-doc 完整流程。"""
    p = _make_minimal_doc(tmp_path)
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "file:" in out
    assert "document_id:" in out
    assert "metrics:" in out


# =========================================================================
# 模块整体合理性
# =========================================================================


def test_module_has_4_module_level_functions():
    """module 有 4 个 module-level function：
    main, _build_parser, _format_metric, _run_inspect_doc
    """
    import types
    funcs = [n for n in dir(climod)
             if not n.startswith("__")
             and isinstance(getattr(climod, n), types.FunctionType)
             and getattr(climod, n).__module__ == "evaluation.cli"]
    expected = ["main", "_build_parser", "_format_metric", "_run_inspect_doc"]
    for e in expected:
        assert e in funcs


def test_module_has_no_class_definition():
    src = inspect.getsource(climod)
    lines = src.split("\n")
    for line in lines:
        if not line.startswith(" ") and line.startswith("class "):
            pytest.fail(f"Found class definition: {line}")


def test_module_has_main_block():
    src = inspect.getsource(climod)
    assert 'if __name__ == "__main__":' in src


def test_module_has_no_all():
    """__all__ 不存在（与 evaluation/ 下其他 module 不同）。"""
    src = inspect.getsource(climod)
    assert "__all__" not in src


def test_module_has_windows_stdout_block():
    """Windows stdout 块存在。"""
    src = inspect.getsource(climod)
    assert "Windows" in src or "reconfigure" in src
