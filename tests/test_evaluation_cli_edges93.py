"""evaluation/cli.py 第二百三十四轮 edges 测试（Round 790）。

补强 edges91-92 未触及的角度（第一百五十四批）。

新角度：
- validate-report：合法完整报告 → rc 0 +
  "[OK] <path> 通过 evaluation-report Schema 校验"；
  坏 JSON → rc 1 + "[ERROR] JSON 解析失败"（与 FNF rc 2 区分）
- --parser bogus → argparse SystemExit 2 + "invalid choice"
  （choices 白名单）；缺 --output → SystemExit 2 + "required"
- inspect-doc '?' 占位族：document_id ? / source ? type=unknown /
  parser ? v? / counts elements=N chunks=M（缺元信息键的 doc）
- inspect-doc 顶层 list → rc 1 "[ERROR] JSON 顶层不是对象"
- _format_metric：float 0.5 → "0.5000"；dict {"b":2,"a":1} →
  "a=1, b=2"（按 key 排序）
- run 汇总行：混合 per_doc（1 True 1 False）→
  "documents=2（成功 1，失败 1）"；git_commit 12 字符截断
  "abcdef123456"；None → "unknown"
- forbidden tokens 第二百六十批
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _format_metric, main

_FULL_REPORT = {
    "report_version": "1.1",
    "provenance": {
        "run_timestamp_iso": "2026-08-17T00:00:00+00:00",
        "git_commit": None, "git_dirty": False,
        "evaluator_version": "1.1", "report_version": "1.1",
        "parser_name": "fallback", "parser_version": "1.0",
        "dependencies": {}, "max_chars": 800},
    "devset": {"status": "incomplete", "file_count": 0,
               "content_group_count": 0, "pdf_count": 0,
               "docx_count": 0, "categories_covered": []},
    "summary": {"counts": {}, "success_rates": {},
                "ratio_macro_averages": {}, "silent_drop_total": 0},
    "per_doc": [],
}


def _cap():
    out, err = io.StringIO(), io.StringIO()
    return out, err, contextlib.redirect_stdout(out), \
        contextlib.redirect_stderr(err)


# ---------- validate-report ----------

def test_validate_report_ok_line_batch54(tmp_path):
    f = tmp_path / "good.json"
    f.write_text(json.dumps(_FULL_REPORT), encoding="utf-8")
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["validate-report", str(f)])
    assert rc == 0
    assert out.getvalue().strip() == (
        f"[OK] {f} 通过 evaluation-report Schema 校验")


def test_validate_report_bad_json_rc1_batch54(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{oops", encoding="utf-8")
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["validate-report", str(f)])
    assert rc == 1
    assert err.getvalue().startswith("[ERROR] JSON 解析失败")


# ---------- argparse 白名单与必填 ----------

def test_parser_invalid_choice_exit_two_batch54():
    out, err, co, ce = _cap()
    with pytest.raises(SystemExit) as ei:
        with co, ce:
            main(["run", "--manifest", "m", "--output", "o",
                  "--parser", "bogus"])
    assert ei.value.code == 2
    assert "invalid choice" in err.getvalue()


def test_run_missing_output_required_batch54():
    out, err, co, ce = _cap()
    with pytest.raises(SystemExit) as ei:
        with co, ce:
            main(["run", "--manifest", "m"])
    assert ei.value.code == 2
    assert "required" in err.getvalue()


# ---------- inspect-doc '?' 占位族 ----------

def test_inspect_doc_placeholder_family_batch54(tmp_path):
    f = tmp_path / "min.json"
    f.write_text(json.dumps({
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "content": "A"}],
        "chunks": [{"text": "A", "source_element_ids": ["e1"]}]}),
        encoding="utf-8")
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(f)])
    lines = out.getvalue().splitlines()
    assert rc == 0
    assert lines[1] == "document_id: ?"
    assert lines[2] == "source:      ?  type=unknown"
    assert lines[3] == "parser:      ? v?"
    assert lines[4] == "counts:      elements=1 chunks=1"


def test_inspect_doc_top_level_list_batch54(tmp_path):
    f = tmp_path / "lst.json"
    f.write_text("[]", encoding="utf-8")
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(f)])
    assert rc == 1
    assert err.getvalue().strip() == "[ERROR] JSON 顶层不是对象"


# ---------- _format_metric ----------

def test_format_metric_float_four_decimals_batch54():
    assert _format_metric("x", {"value": 0.5, "reason": None}) == \
        "  x                                    0.5000  (ok)"


def test_format_metric_dict_sorted_items_batch54():
    assert _format_metric("x", {"value": {"b": 2, "a": 1},
                                "reason": None}) == \
        "  x                                    a=1, b=2  (ok)"


# ---------- run 汇总行 ----------

def _fake_report(**dev_extra):
    dev = {"status": "incomplete", "file_count": 2,
           "content_group_count": 2, "pdf_count": 1, "docx_count": 1}
    dev.update(dev_extra)
    return {"per_doc": [
        {"doc_id": "a", "metrics": {"pipeline_success":
                                    {"value": True, "reason": None}}},
        {"doc_id": "b", "metrics": {"pipeline_success":
                                    {"value": False, "reason": None}}}],
        "devset": dev}


def _run_with_report(tmp_path, git):
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": []}), encoding="utf-8")
    with patch.object(cli_mod, "run_evaluation",
                      lambda man, outp, **k: _fake_report()), \
            patch.object(cli_mod, "validate_file",
                         lambda p, s: None), \
            patch.object(cli_mod, "get_git_provenance",
                         lambda r: git):
        out, err, co, ce = _cap()
        with co, ce:
            rc = main(["run", "--manifest", str(mf),
                       "--output", "r.json"])
    return rc, out.getvalue().splitlines()


def test_run_summary_counts_and_git_truncation_batch54(tmp_path):
    rc, lines = _run_with_report(
        tmp_path, {"git_commit": "abcdef1234567890",
                   "git_dirty": True})
    assert rc == 0
    assert lines[1] == "      documents=2（成功 1，失败 1）"
    assert lines[-1] == \
        "      git_commit=abcdef123456 git_dirty=True"


def test_run_git_commit_none_unknown_batch54(tmp_path):
    rc, lines = _run_with_report(
        tmp_path, {"git_commit": None, "git_dirty": False})
    assert rc == 0
    assert lines[-1].strip() == "git_commit=unknown git_dirty=False"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_truncation_and_defaults_batch54():
    src = _src()
    assert "(git.get('git_commit') or 'unknown')[:12]" in src
    assert "choices=(\"fallback\", \"kreuzberg\")" in src
    assert "doc.get('parser_name', '?')" in src


# ---------- forbidden tokens 第二百六十批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch54():
    assert _src().count("open(") == 1
