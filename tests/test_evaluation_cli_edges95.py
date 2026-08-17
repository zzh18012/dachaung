"""evaluation/cli.py 第二百四十八轮 edges 测试（Round 804）。

补强 edges94 未触及的角度（第一百六十八批）。

新角度：
- inspect-doc 中文 document_id 原样渲染（stdout reconfigure
  utf-8 生效）
- validate-report 损坏报告 → rc 1 + "[FAIL] <path> 报告校验失败"
  前缀（与 [OK] 行对照）
- run 旗标全透传：--parser kreuzberg / --max-chars 555 /
  --tolerance-chars 77 → run_evaluation 同名 kwargs
- inspect-doc 二进制（非 UTF-8）文件 → UnicodeDecodeError 传播
  （except 只捕 JSONDecodeError，open 默认 strict）
- 未知子命令 bogus → SystemExit 2 + invalid choice
- forbidden tokens 第二百七十四批
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
from evaluation.cli import main


def _cap():
    out, err = io.StringIO(), io.StringIO()
    return out, err, contextlib.redirect_stdout(out), \
        contextlib.redirect_stderr(err)


# ---------- 中文 document_id ----------

def test_inspect_doc_chinese_document_id_batch54(tmp_path):
    f = tmp_path / "cn.json"
    f.write_text(json.dumps({
        "document_id": "中文", "source_type": "pdf",
        "elements": [], "chunks": []}), encoding="utf-8")
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(f)])
    assert rc == 0
    assert out.getvalue().splitlines()[1] == "document_id: 中文"


# ---------- [FAIL] 前缀 ----------

def test_validate_report_fail_prefix_batch54(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({"report_version": "1.1"}),
                 encoding="utf-8")
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["validate-report", str(f)])
    assert rc == 1
    assert err.getvalue().startswith(
        f"[FAIL] {f} 报告校验失败：")


# ---------- run 旗标透传 ----------

def test_run_flags_passthrough_batch54(tmp_path):
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": []}), encoding="utf-8")
    caps = {}

    def fake_run(man, outp, **kw):
        caps.update(kw)
        return {"per_doc": [], "devset": {}}

    with patch.object(cli_mod, "run_evaluation", fake_run), \
            patch.object(cli_mod, "validate_file",
                         lambda p, s: None), \
            patch.object(cli_mod, "get_git_provenance",
                         lambda r: {"git_commit": None,
                                    "git_dirty": False}):
        out, err, co, ce = _cap()
        with co, ce:
            rc = main(["run", "--manifest", str(mf),
                       "--output", "r.json",
                       "--parser", "kreuzberg",
                       "--max-chars", "555",
                       "--tolerance-chars", "77"])
    assert rc == 0
    assert caps == {"parser_name": "kreuzberg", "max_chars": 555,
                    "tolerance_chars": 77}


# ---------- 二进制文件 ----------

def test_inspect_doc_binary_file_decode_error_batch54(tmp_path):
    f = tmp_path / "bin.json"
    f.write_bytes(b"\xff\xfe\x00\x01")
    out, err, co, ce = _cap()
    with pytest.raises(UnicodeDecodeError):
        with co, ce:
            main(["inspect-doc", str(f)])


# ---------- 未知子命令 ----------

def test_unknown_subcommand_exit_two_batch54():
    out, err, co, ce = _cap()
    with pytest.raises(SystemExit) as ei:
        with co, ce:
            main(["bogus"])
    assert ei.value.code == 2
    assert "invalid choice" in err.getvalue()


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_reconfigure_lines_batch54():
    src = _src()
    assert 'sys.stdout.reconfigure(encoding="utf-8"' in src
    assert "except json.JSONDecodeError as e:" in src


# ---------- forbidden tokens 第二百七十四批 ----------

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
