"""evaluation/cli.py 第二百六十二轮 edges 测试（Round 818）。

补强 edges96 未触及的角度（第一百八十六批）。

新角度：
- inspect-doc 坏 JSON "{oops" 与空文件 ""：均走
  JSONDecodeError 分支 → rc 1 "[ERROR] JSON 解析失败:" 前缀
- run --max-chars abc → argparse type=int → SystemExit 2 +
  "invalid int"
- inspect-doc --tolerance-chars abc → 同上 SystemExit 2
- run 空清单完整摘要块：documents=0（成功 0，失败 0）/
  devset_status=incomplete file_count=0 groups=0 pdf=0
  docx=0 / git_commit=unknown git_dirty=False
- _format_metric int 值走通用分支："  n" + ljust(36) + " 5  (ok)"
- forbidden tokens 第二百八十八批
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


def _cap():
    out, err = io.StringIO(), io.StringIO()
    return out, err, contextlib.redirect_stdout(out), \
        contextlib.redirect_stderr(err)


# ---------- 坏 / 空 JSON ----------

def test_inspect_doc_malformed_json_rc1_batch55(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{oops", encoding="utf-8")
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(bad)])
    assert rc == 1
    assert err.getvalue().startswith("[ERROR] JSON 解析失败:")


def test_inspect_doc_empty_file_rc1_batch55(tmp_path):
    emp = tmp_path / "emp.json"
    emp.write_text("", encoding="utf-8")
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(emp)])
    assert rc == 1
    assert err.getvalue().startswith("[ERROR] JSON 解析失败:")


# ---------- 非整数旗标 ----------

def test_max_chars_non_int_exit_two_batch55():
    out, err, co, ce = _cap()
    with pytest.raises(SystemExit) as ei, co, ce:
        main(["run", "--manifest", "m", "--output", "o",
              "--max-chars", "abc"])
    assert ei.value.code == 2
    assert "invalid int" in err.getvalue()


def test_tolerance_chars_non_int_exit_two_batch55():
    out, err, co, ce = _cap()
    with pytest.raises(SystemExit) as ei, co, ce:
        main(["inspect-doc", "x", "--tolerance-chars", "abc"])
    assert ei.value.code == 2
    assert "invalid int" in err.getvalue()


# ---------- 空清单摘要块 ----------

def test_run_empty_manifest_summary_block_batch55(tmp_path):
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": []}),
                  encoding="utf-8")

    def fake_run(man, outp, **kw):
        return {"per_doc": [], "devset": {
            "status": "incomplete", "file_count": 0,
            "content_group_count": 0, "pdf_count": 0,
            "docx_count": 0}}

    with patch.object(cli_mod, "run_evaluation", fake_run), \
            patch.object(cli_mod, "validate_file",
                         lambda p, s: None), \
            patch.object(cli_mod, "get_git_provenance",
                         lambda r: {"git_commit": None,
                                    "git_dirty": False}):
        out, err, co, ce = _cap()
        with co, ce:
            rc = main(["run", "--manifest", str(mf),
                       "--output", str(tmp_path / "r.json")])
    assert rc == 0
    lines = out.getvalue().splitlines()
    assert lines[1] == "      documents=0（成功 0，失败 0）"
    assert lines[2] == ("      devset_status=incomplete "
                        "file_count=0 groups=0 pdf=0 docx=0")
    assert lines[3] == "      git_commit=unknown git_dirty=False"


# ---------- _format_metric int ----------

def test_format_metric_int_generic_branch_batch55():
    assert _format_metric("n", {"value": 5,
                                "reason": None}) == \
        "  n                                    5  (ok)"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "except json.JSONDecodeError as e:" in src
    assert 'print(f"[ERROR] JSON 解析失败: {e}", file=sys.stderr)' in src
    assert 'f"  {name:36} {value}  ({reason or \'ok\'})"' in src


# ---------- forbidden tokens 第二百八十八批 ----------

def test_source_no_eval_batch55():
    assert "eval(" not in _src()


def test_source_no_exec_batch55():
    assert "exec(" not in _src()


def test_source_no_compile_batch55():
    assert "compile(" not in _src()


def test_source_no_globals_batch55():
    assert "globals(" not in _src()


def test_source_no_locals_batch55():
    assert "locals(" not in _src()


def test_source_no_os_system_batch55():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch55():
    assert "subprocess" not in _src()


def test_source_no_popen_batch55():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch55():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch55():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch55():
    assert "socket" not in _src()


def test_source_no_requests_batch55():
    assert "requests" not in _src()


def test_source_no_urllib_batch55():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch55():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch55():
    assert "yield" not in _src()


def test_source_no_async_await_batch55():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch55():
    assert _src().count("open(") == 1
