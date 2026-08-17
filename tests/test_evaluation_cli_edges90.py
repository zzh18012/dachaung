"""evaluation/cli.py 第二百一十三轮 edges 测试（Round 769）。

补强 edges88-89 未触及的角度（第一百三十三批）。

新角度：
- run 成功块完整五行：[OK] + documents=2（成功 1，失败 1）+ devset 行 +
  git_commit[:12] + git_dirty（非空 per_doc 变体）
- run 自校验失败两分支：validate_file 抛 EvalSchemaError → rc 1
  "[ERROR] 报告自校验失败"；抛 FileNotFoundError → 未捕获直接传播
  （run 的自校验只捕 EvalSchemaError，与 validate-report 的
  FileNotFoundError 分支不对称，现状记录）
- validate-report 的 FileNotFoundError 分支：rc 2 "[ERROR] schema gone"
- inspect-doc --tolerance-chars 55 透传 chunk_boundary_prf（函数内
  import → patch annotation_metrics 命名空间）
- inspect-doc 缺 source_type → header "type=unknown" +
  双 locator null（not_pdf_document / not_docx_document）
- _format_metric：value None + reason None → "null  (None)"
  （null 分支原样渲染 reason，不落 'ok'）；bool True/False 小写渲染；
  int 42 → "42  (ok)"
- main(["--help"]) → SystemExit 0 + usage 上 stdout
- forbidden tokens 第二百三十九批
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

import evaluation.annotation_metrics as am
import evaluation.cli as cli_mod
from evaluation.cli import _format_metric, main
from evaluation.schema import EvalSchemaError


def _cap():
    out, err = io.StringIO(), io.StringIO()
    return out, err, contextlib.redirect_stdout(out), \
        contextlib.redirect_stderr(err)


_FAKE = {
    "per_doc": [
        {"doc_id": "a", "source_type": "pdf",
         "metrics": {"pipeline_success": {"value": True, "reason": None}},
         "wall_time_seconds": {"total": 1, "parse": None, "chunk": None}},
        {"doc_id": "b", "source_type": "docx",
         "metrics": {"pipeline_success": {"value": False, "reason": "x"}},
         "wall_time_seconds": {"total": 2, "parse": None, "chunk": None}},
    ],
    "devset": {"status": "incomplete", "file_count": 2,
               "content_group_count": 1, "pdf_count": 1, "docx_count": 1},
}


def _manifest(tmp):
    mf = tmp / "m.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": []}), encoding="utf-8")
    return mf


def _git(r):
    return {"git_commit": "a" * 40, "git_dirty": False}


def test_run_success_block_five_lines_batch54(tmp_path):
    mf = _manifest(tmp_path)
    out_p = tmp_path / "r.json"
    with patch.object(cli_mod, "run_evaluation", lambda *a, **k: _FAKE), \
            patch.object(cli_mod, "validate_file", lambda p, s: None), \
            patch.object(cli_mod, "get_git_provenance", _git):
        out, err, co, ce = _cap()
        with co, ce:
            rc = main(["run", "--manifest", str(mf), "--output",
                       str(out_p)])
    assert rc == 0
    lines = out.getvalue().splitlines()
    assert lines[0] == f"[OK] 评测完成：{out_p}"
    assert lines[1] == "      documents=2（成功 1，失败 1）"
    assert lines[2] == ("      devset_status=incomplete file_count=2 "
                        "groups=1 pdf=1 docx=1")
    assert lines[3] == "      git_commit=aaaaaaaaaaaa git_dirty=False"


def test_run_self_check_schema_error_rc1_batch54(tmp_path):
    mf = _manifest(tmp_path)
    with patch.object(cli_mod, "run_evaluation", lambda *a, **k: _FAKE), \
            patch.object(cli_mod, "validate_file",
                         side_effect=EvalSchemaError("bad")), \
            patch.object(cli_mod, "get_git_provenance", _git):
        out, err, co, ce = _cap()
        with co, ce:
            rc = main(["run", "--manifest", str(mf), "--output",
                       str(tmp_path / "r.json")])
    assert rc == 1
    assert err.getvalue().strip() == "[ERROR] 报告自校验失败: bad"


def test_run_self_check_fnf_propagates_batch54(tmp_path):
    mf = _manifest(tmp_path)
    with patch.object(cli_mod, "run_evaluation", lambda *a, **k: _FAKE), \
            patch.object(cli_mod, "validate_file",
                         side_effect=FileNotFoundError("schema gone")), \
            patch.object(cli_mod, "get_git_provenance", _git):
        with pytest.raises(FileNotFoundError):
            main(["run", "--manifest", str(mf), "--output",
                  str(tmp_path / "r.json")])


def test_validate_report_fnf_rc2_batch54(tmp_path):
    rf = tmp_path / "r.json"
    rf.write_text("{}", encoding="utf-8")
    with patch.object(cli_mod, "validate_file",
                      side_effect=FileNotFoundError("schema gone")):
        out, err, co, ce = _cap()
        with co, ce:
            rc = main(["validate-report", str(rf)])
    assert rc == 2
    assert err.getvalue().strip() == "[ERROR] schema gone"


# ---------- inspect-doc ----------

def test_inspect_tolerance_passthrough_batch54(tmp_path):
    df = tmp_path / "d.json"
    df.write_text(json.dumps({"document_id": "d", "source_type": "pdf",
                              "elements": [], "chunks": []}),
                  encoding="utf-8")
    seen = {}
    with patch.object(am, "chunk_boundary_prf",
                      lambda doc, ann, tolerance_chars=30:
                      seen.update(tol=tolerance_chars) or {}), \
            patch.object(am, "figure_caption_prf", lambda d, a: {}):
        out, err, co, ce = _cap()
        with co, ce:
            rc = main(["inspect-doc", str(df), "--tolerance-chars", "55"])
    assert rc == 0
    assert seen["tol"] == 55


def test_inspect_missing_source_type_unknown_batch54(tmp_path):
    df = tmp_path / "d.json"
    df.write_text(json.dumps({"document_id": "d", "elements": [],
                              "chunks": []}), encoding="utf-8")
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(df)])
    assert rc == 0
    lines = out.getvalue().splitlines()
    assert "source:      ?  type=unknown" in lines
    assert ("  docx_locator_valid_ratio             null  "
            "(not_docx_document)") in lines
    assert ("  pdf_locator_valid_ratio              null  "
            "(not_pdf_document)") in lines


# ---------- _format_metric ----------

def test_format_metric_null_none_reason_batch54():
    assert _format_metric("n", {"value": None, "reason": None}) == \
        "  n" + " " * 36 + "null  (None)"


def test_format_metric_bool_lowercase_batch54():
    assert _format_metric("n", {"value": True, "reason": None}) == \
        "  n" + " " * 36 + "true  (ok)"
    assert _format_metric("n", {"value": False, "reason": "r"}) == \
        "  n" + " " * 36 + "false  (r)"


def test_format_metric_int_42_batch54():
    assert _format_metric("n", {"value": 42, "reason": None}) == \
        "  n" + " " * 36 + "42  (ok)"


# ---------- argparse --help ----------

def test_help_systemexit_zero_batch54():
    out, err, co, ce = _cap()
    with pytest.raises(SystemExit) as ei:
        with co, ce:
            main(["--help"])
    assert ei.value.code == 0
    assert "usage" in out.getvalue()


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_run_self_check_guard_batch54():
    src = _src()
    assert "报告自校验失败" in src
    assert 'except FileNotFoundError as e:' in src
    assert "raise SystemExit(main())" in src
    assert src.count("args.tolerance_chars") == 2


# ---------- forbidden tokens 第二百三十九批 ----------

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
