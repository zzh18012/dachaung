"""evaluation/cli.py 第二百九十轮 edges 测试（Round 846）。

补强 edges100 未触及的角度（第二百二十批）。

新角度：
- _format_metric 名字超 36 字符不截断（{name:36} 只补不裁）
- run --parser kreuzberg 显式透传（对照默认 fallback）
- inspect-doc --tolerance-chars 负数被 argparse 接受 →
  _tolerance_chars -5 行
- 未知子命令 bogus → SystemExit 2
- run 成功路径 stderr 为空（错误信息才走 stderr）
- forbidden tokens 第三百一十六批
"""

from __future__ import annotations

import inspect
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _format_metric, main


# ---------- 长名不截断 ----------

def test_format_metric_long_name_batch55():
    name = "a" * 40
    out = _format_metric(name, {"value": 5, "reason": None})
    assert out == f"  {name} 5  (ok)"
    assert out.startswith(f"  {name} ")


# ---------- parser 显式 ----------

def test_run_parser_kreuzberg_batch55(tmp_path, capsys):
    mf = tmp_path / "m.json"
    mf.write_text("{}", encoding="utf-8")
    cap: dict = {}

    def _run(*a, **k):
        cap.update(k)
        return {"per_doc": [], "devset": {}}

    m = SimpleNamespace(project_root=tmp_path)
    with patch.object(cli_mod, "load_manifest",
                      lambda p: m), \
         patch.object(cli_mod, "run_evaluation", _run), \
         patch.object(cli_mod, "validate_file",
                      lambda p, s: None), \
         patch.object(cli_mod, "get_git_provenance",
                      lambda r: {"git_commit": None,
                                 "git_dirty": False}):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(tmp_path / "r.json"),
                   "--parser", "kreuzberg"])
    assert rc == 0
    assert cap["parser_name"] == "kreuzberg"


# ---------- 负 tolerance ----------

def test_inspect_negative_tolerance_batch55(tmp_path, capsys):
    f = tmp_path / "doc.json"
    f.write_text(json.dumps({"source_type": "pdf",
                             "elements": [], "chunks": []}),
                 encoding="utf-8")
    rc = main(["inspect-doc", str(f),
               "--tolerance-chars", "-5"])
    out = capsys.readouterr().out
    assert rc == 0
    assert f"  {'_tolerance_chars':36} -5  (ok)" in out


# ---------- 未知子命令 ----------

def test_unknown_subcommand_exit_2_batch55():
    with pytest.raises(SystemExit) as ei:
        main(["bogus"])
    assert ei.value.code == 2


# ---------- 成功路径 stderr 空 ----------

def test_run_success_stderr_empty_batch55(tmp_path, capsys):
    mf = tmp_path / "m.json"
    mf.write_text("{}", encoding="utf-8")
    m = SimpleNamespace(project_root=tmp_path)
    with patch.object(cli_mod, "load_manifest",
                      lambda p: m), \
         patch.object(cli_mod, "run_evaluation",
                      lambda *a, **k: {"per_doc": [],
                                       "devset": {}}), \
         patch.object(cli_mod, "validate_file",
                      lambda p, s: None), \
         patch.object(cli_mod, "get_git_provenance",
                      lambda r: {"git_commit": None,
                                 "git_dirty": False}):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(tmp_path / "r.json")])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.err == ""
    assert "[OK]" in captured.out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert 'f"  {name:36} {value}  ({reason or \'ok\'})"' in src
    assert 'sub = p.add_subparsers(dest="command", required=True)' in src
    assert "choices=(\"fallback\", \"kreuzberg\")" in src


# ---------- forbidden tokens 第三百一十六批 ----------

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
