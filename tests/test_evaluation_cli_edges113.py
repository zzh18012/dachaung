"""evaluation/cli.py 第三百七十四轮 edges 测试（Round 930）。

补强 edges112 未触及的角度（第三百零六批，probe 实证）。

新角度：
- argparse 三种 SystemExit 2：run 缺 --manifest/--output、
  --manifest 缺值、未知子命令 frobnicate（usage 含三命令名）
- run 相对路径清单不存在 → rc 2 "清单不存在: m.json"
  （相对路径原样打印，chdir 后验证）
- inspect-doc --tolerance-chars -5 → 指标行
  "  _tolerance_chars … -5  (ok)"（负值原样入表）；
  --tolerance-chars abc → SystemExit 2
- inspect-doc 全字段头 5 行真实值（document_id /
  source_path / parser v1.2 / counts 1 1）
- forbidden tokens 第四百批
"""

from __future__ import annotations

import inspect
import json

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main


# ---------- argparse SystemExit ----------

def test_run_missing_args_system_exit_batch128(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["run"])
    assert ei.value.code == 2
    assert "--manifest, --output" in capsys.readouterr().err


def test_manifest_missing_value_system_exit_batch128():
    with pytest.raises(SystemExit) as ei:
        main(["run", "--manifest"])
    assert ei.value.code == 2


def test_unknown_command_system_exit_batch128(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["frobnicate"])
    assert ei.value.code == 2
    err = capsys.readouterr().err
    assert "invalid choice: 'frobnicate'" in err
    assert "run, validate-report, inspect-doc" in err


# ---------- run 相对路径 ----------

def test_run_relative_manifest_missing_batch128(tmp_path,
                                                monkeypatch,
                                                capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["run", "--manifest", "m.json",
               "--output", "o.json"])
    assert rc == 2
    assert capsys.readouterr().err.strip() == \
        "[ERROR] 清单不存在: m.json"


# ---------- inspect tolerance ----------

_DOC = {
    "document_id": "doc-1", "source_path": "s/h.pdf",
    "source_type": "pdf", "parser_name": "fallback",
    "parser_version": "1.2",
    "elements": [{"element_id": "e1", "type": "paragraph",
                  "content": "AB"}],
    "chunks": [{"text": "AB", "source_element_ids": ["e1"]}],
}


def test_inspect_negative_tolerance_line_batch128(tmp_path,
                                                  capsys):
    f = tmp_path / "d.json"
    f.write_text(json.dumps(_DOC), encoding="utf-8")
    rc = main(["inspect-doc", str(f), "--tolerance-chars", "-5"])
    assert rc == 0
    lines = capsys.readouterr().out.splitlines()
    tol = [ln for ln in lines if "_tolerance_chars" in ln]
    assert tol == ["  " + "_tolerance_chars".ljust(36) +
                   " -5  (ok)"]


def test_inspect_tolerance_abc_system_exit_batch128(tmp_path):
    f = tmp_path / "d.json"
    f.write_text(json.dumps(_DOC), encoding="utf-8")
    with pytest.raises(SystemExit) as ei:
        main(["inspect-doc", str(f), "--tolerance-chars", "abc"])
    assert ei.value.code == 2


# ---------- inspect 全字段头 ----------

def test_inspect_full_header_batch128(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(json.dumps(_DOC), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[1] == "document_id: doc-1"
    assert lines[2] == "source:      s/h.pdf  type=pdf"
    assert lines[3] == "parser:      fallback v1.2"
    assert lines[4] == "counts:      elements=1 chunks=1"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch128():
    src = _src()
    assert 'sub = p.add_subparsers(dest="command", required=True)' in src
    assert 'choices=("fallback", "kreuzberg")' in src
    assert 'print(f"[ERROR] 清单不存在: {manifest_path}", file=sys.stderr)' in src


# ---------- forbidden tokens 第四百批 ----------

def test_source_no_eval_batch128():
    assert "eval(" not in _src()


def test_source_no_exec_batch128():
    assert "exec(" not in _src()


def test_source_no_compile_batch128():
    assert "compile(" not in _src()


def test_source_no_globals_batch128():
    assert "globals(" not in _src()


def test_source_no_locals_batch128():
    assert "locals(" not in _src()


def test_source_no_os_system_batch128():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch128():
    assert "subprocess" not in _src()


def test_source_no_popen_batch128():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch128():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch128():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch128():
    assert "socket" not in _src()


def test_source_no_requests_batch128():
    assert "requests" not in _src()


def test_source_no_urllib_batch128():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch128():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch128():
    assert "yield" not in _src()


def test_source_no_async_await_batch128():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch128():
    assert _src().count("open(") == 1
