"""evaluation/cli.py 第四百三十七轮 edges 测试（Round 993）。

补强 edges121 未触及的角度（第三百六十九批，probe 实证）。

新角度：
- run 流程：run_evaluation 未落盘（mock）→ validate_file
  抛 FileNotFoundError "待校验文件不存在" → cli 只捕
  EvalSchemaError → 原样向上传播（崩溃而非 rc 码）
- inspect-doc 空文件 "" → JSON 解析失败 rc 1
- inspect-doc 顶层字符串 '"hello"' → "JSON 顶层不是对象"
  rc 1
- inspect-doc 空 dict {} → rc 0 + "counts:
  elements=0 chunks=0"
- forbidden tokens 第四百六十三批（open 1）
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": []}), encoding="utf-8")
    return mf


# ---------- FileNotFoundError 传播 ----------

def test_validate_file_filenotfound_propagates_batch191(
        tmp_path, capsys):
    mf = _setup(tmp_path)
    out = tmp_path / "never.json"
    with pytest.raises(FileNotFoundError, match="待校验文件不存在"), \
            patch.object(cli_mod, "run_evaluation",
                         return_value={"per_doc": [],
                                       "devset": {}}), \
            patch.object(cli_mod, "get_git_provenance",
                         return_value={"git_commit": None,
                                       "git_dirty": False}):
        main(["run", "--manifest", str(mf), "--output", str(out)])
    assert not out.exists()


# ---------- 空文件 ----------

def test_inspect_empty_file_rc1_batch191(tmp_path, capsys):
    ef = tmp_path / "empty.json"
    ef.write_text("", encoding="utf-8")
    rc = main(["inspect-doc", str(ef)])
    assert rc == 1
    assert capsys.readouterr().err.startswith(
        "[ERROR] JSON 解析失败: Expecting value")


# ---------- 顶层字符串 ----------

def test_inspect_string_top_level_rc1_batch191(tmp_path, capsys):
    sf = tmp_path / "str.json"
    sf.write_text('"hello"', encoding="utf-8")
    rc = main(["inspect-doc", str(sf)])
    assert rc == 1
    assert capsys.readouterr().err.strip() == \
        "[ERROR] JSON 顶层不是对象"


# ---------- 空 dict ----------

def test_inspect_empty_dict_zero_counts_batch191(tmp_path,
                                                 capsys):
    df = tmp_path / "d.json"
    df.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(df)])
    assert rc == 0
    assert "counts:      elements=0 chunks=0" in \
        capsys.readouterr().out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch191():
    src = _src()
    assert 'sys.stdout.reconfigure(encoding="utf-8", errors="replace")' in src
    assert "if not isinstance(doc, dict):" in src
    assert 'print("[ERROR] JSON 顶层不是对象", file=sys.stderr)' in src
    assert 'print(f"counts:      elements={len(elements)} chunks={len(chunks)}")' in src


# ---------- forbidden tokens 第四百六十三批 ----------

def test_source_no_eval_batch191():
    assert "eval(" not in _src()


def test_source_no_exec_batch191():
    assert "exec(" not in _src()


def test_source_no_compile_batch191():
    assert "compile(" not in _src()


def test_source_no_globals_batch191():
    assert "globals(" not in _src()


def test_source_no_locals_batch191():
    assert "locals(" not in _src()


def test_source_no_os_system_batch191():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch191():
    assert "subprocess" not in _src()


def test_source_no_popen_batch191():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch191():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch191():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch191():
    assert "socket" not in _src()


def test_source_no_requests_batch191():
    assert "requests" not in _src()


def test_source_no_urllib_batch191():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch191():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch191():
    assert "yield" not in _src()


def test_source_no_async_await_batch191():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch191():
    assert _src().count("open(") == 1
