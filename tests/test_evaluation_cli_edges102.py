"""evaluation/cli.py 第二百九十七轮 edges 测试（Round 853）。

补强 edges101 未触及的角度（第二百二十七批）。

新角度：
- run 时 load_manifest 抛 ManifestError → rc1
  「清单加载失败」（与 EvalSchemaError 同 catch）
- inspect-doc 缺 chunks 键 → counts chunks=0（or [] 兜底）
- inspect-doc 缺 elements 键 → counts elements=0
- validate-report 的 FileNotFoundError 分支（patch 注入）
  → rc2
- inspect-doc 指标行数恰 21（14 自动 + 3 figure +
  3 chunk_boundary + 1 泄漏的 _tolerance_chars）
- --help → SystemExit 0
- forbidden tokens 第三百二十三批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main
from evaluation.manifest import ManifestError


# ---------- ManifestError rc1 ----------

def test_run_manifest_error_rc1_batch55(tmp_path, capsys):
    mf = tmp_path / "m.json"
    mf.write_text("{}", encoding="utf-8")
    with patch.object(cli_mod, "load_manifest",
                      side_effect=ManifestError("bad")):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(tmp_path / "r.json")])
    assert rc == 1
    assert "清单加载失败" in capsys.readouterr().err


# ---------- 缺键 counts ----------

def test_inspect_missing_chunks_key_batch55(tmp_path, capsys):
    f = tmp_path / "doc.json"
    f.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "content": "A"}]}), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "counts:      elements=1 chunks=0" in out


def test_inspect_missing_elements_key_batch55(tmp_path, capsys):
    f = tmp_path / "doc.json"
    f.write_text(json.dumps({
        "source_type": "pdf",
        "chunks": [{"text": "A",
                    "source_element_ids": ["e1"]}]}),
        encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "counts:      elements=0 chunks=1" in out


# ---------- validate-report FNF 分支 ----------

def test_validate_report_fnf_rc2_batch55(tmp_path, capsys):
    f = tmp_path / "r.json"
    f.write_text("{}", encoding="utf-8")
    with patch.object(cli_mod, "validate_file",
                      side_effect=FileNotFoundError(
                          "Schema 文件不存在: x")):
        rc = main(["validate-report", str(f)])
    assert rc == 2
    assert "Schema 文件不存在" in capsys.readouterr().err


# ---------- 指标行数 ----------

def test_inspect_metrics_line_count_batch55(tmp_path, capsys):
    f = tmp_path / "doc.json"
    f.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "content": "A"}],
        "chunks": [{"text": "A",
                    "source_element_ids": ["e1"]}]}),
        encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    lines = capsys.readouterr().out.splitlines()
    assert rc == 0
    start = lines.index("metrics:")
    metric_lines = [ln for ln in lines[start + 1:] if
                    ln.startswith("  ")]
    assert len(metric_lines) == 21


# ---------- --help ----------

def test_help_exit_zero_batch55(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["--help"])
    assert ei.value.code == 0
    assert "评测 CLI" in capsys.readouterr().out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "except (ManifestError, EvalSchemaError) as e:" in src
    assert "except FileNotFoundError as e:" in src
    assert 'elements = doc.get("elements") or []' in src


# ---------- forbidden tokens 第三百二十三批 ----------

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
