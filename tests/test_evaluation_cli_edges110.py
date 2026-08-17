"""evaluation/cli.py 第三百五十三轮 edges 测试（Round 909）。

补强 edges109 未触及的角度（第二百八十五批，probe 实证）。

新角度：
- inspect-doc 对 report 形 JSON（无 source_type/elements/chunks）
  照跑：type=unknown、counts 全 0、且 pipeline_success true
  （document 非 None + error None 的现状怪癖）
- ef-only manifest（documents 空）→ run 输出
  "documents=0（成功 0，失败 0）"
- --help → SystemExit 0，usage 含 prog "evaluation.cli"
- forbidden tokens 第三百七十九批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main


# ---------- inspect 对 report 形 JSON ----------

def test_inspect_report_shaped_object_batch107(tmp_path, capsys):
    f = tmp_path / "r.json"
    f.write_text(json.dumps({
        "report_version": "1.1", "summary": {}}), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert rc == 0
    assert lines[2] == "source:      ?  type=unknown"
    assert lines[4] == "counts:      elements=0 chunks=0"
    first = lines[lines.index("metrics:") + 1]
    assert first.startswith("  pipeline_success")
    assert " true  (ok)" in first  # document 非 None → success


# ---------- ef-only manifest ----------

def test_run_ef_only_documents_zero_batch107(tmp_path, capsys):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "b.pdf").write_bytes(b"x")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{
            "doc_id": "f1", "path": "samples/b.pdf",
            "expected_error_code": "E"}]}), encoding="utf-8")
    out = tmp_path / "r.json"
    fake = {"per_doc": [], "devset": {},
            "expected_failures": [{
                "doc_id": "f1", "expected_error_code": "E",
                "actual_error_code": "E", "matches": True}]}
    with patch.object(cli_mod, "run_evaluation",
                      return_value=fake), \
         patch.object(cli_mod, "validate_file"), \
         patch.object(cli_mod, "get_git_provenance",
                      return_value={"git_commit": None,
                                    "git_dirty": False}):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(out)])
    lines = [ln for ln in capsys.readouterr().out.splitlines()
             if ln]
    assert rc == 0
    assert lines[1] == "      documents=0（成功 0，失败 0）"


# ---------- --help ----------

def test_help_system_exit_zero_batch107(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "evaluation.cli" in out
    assert "run" in out and "validate-report" in out \
        and "inspect-doc" in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch107():
    src = _src()
    assert 'prog="evaluation.cli"' in src
    assert "source_type = doc.get(\"source_type\", \"unknown\")" in src
    assert "print(f\"[OK] {input_path} 通过" in src


# ---------- forbidden tokens 第三百七十九批 ----------

def test_source_no_eval_batch107():
    assert "eval(" not in _src()


def test_source_no_exec_batch107():
    assert "exec(" not in _src()


def test_source_no_compile_batch107():
    assert "compile(" not in _src()


def test_source_no_globals_batch107():
    assert "globals(" not in _src()


def test_source_no_locals_batch107():
    assert "locals(" not in _src()


def test_source_no_os_system_batch107():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch107():
    assert "subprocess" not in _src()


def test_source_no_popen_batch107():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch107():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch107():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch107():
    assert "socket" not in _src()


def test_source_no_requests_batch107():
    assert "requests" not in _src()


def test_source_no_urllib_batch107():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch107():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch107():
    assert "yield" not in _src()


def test_source_no_async_await_batch107():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch107():
    assert _src().count("open(") == 1
