"""evaluation/cli.py 第二百二十七轮 edges 测试（Round 783）。

补强 edges88-91 未触及的角度（第一百四十七批）。

新角度：
- --tolerance-chars 55 反映进泄漏的内部行
  "  _tolerance_chars                     55  (ok)"
- 全指标 doc 的 metrics 区恰 21 行（20 指标 + _tolerance_chars
  泄漏行；3 bool + 7 数值 + 1 dict + 10 null）
- --output "r.json"（无目录段）：output_root=Path(".") mkdir
  exist_ok 不炸；validate_file 收到 Path("r.json")、[OK] 行
  原样打印相对名（CLI 不写盘，写盘在 run_evaluation 内 —— 用
  mock 捕获路径而非检查文件）
- 顶层 --help：usage 行 "usage: evaluation.cli [-h]
  {run,validate-report,inspect-doc} ..."（prog 锁定）
- 子命令 run --help：SystemExit 0 + --manifest 与
  --tolerance-chars 都在用法里
- forbidden tokens 第二百五十三批
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


def _full_doc(tmp):
    f = tmp / "full.json"
    f.write_text(json.dumps({
        "document_id": "d", "source_type": "pdf",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "A"},
            {"element_id": "e2", "type": "heading", "content": "B"}],
        "chunks": [{"text": "A B",
                    "source_element_ids": ["e1", "e2"]}]}),
        encoding="utf-8")
    return f


# ---------- tolerance 泄漏行 ----------

def test_tolerance_flag_shows_in_leak_line_batch54(tmp_path):
    f = tmp_path / "d.json"
    f.write_text(json.dumps({
        "document_id": "d", "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "content": "A"}],
        "chunks": [{"text": "A",
                    "source_element_ids": ["e1"]}]}),
        encoding="utf-8")
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(f), "--tolerance-chars", "55"])
    assert rc == 0
    assert ("  _tolerance_chars                     55  (ok)") \
        in out.getvalue().splitlines()


# ---------- metrics 行数 ----------

def test_full_doc_metric_line_count_batch54(tmp_path):
    out, err, co, ce = _cap()
    with co, ce:
        main(["inspect-doc", str(_full_doc(tmp_path))])
    lines = out.getvalue().splitlines()
    mi = lines.index("metrics:")
    assert len(lines) - mi - 1 == 21


# ---------- 无目录段的 --output ----------

def test_output_bare_filename_path_convention_batch54(tmp_path,
                                                      monkeypatch):
    monkeypatch.chdir(tmp_path)
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": []}), encoding="utf-8")
    got = {}
    with patch.object(cli_mod, "run_evaluation",
                      lambda man, out, **k: {"per_doc": [],
                                             "devset": {}}), \
            patch.object(cli_mod, "validate_file",
                         lambda p, s: got.update(path=p)), \
            patch.object(cli_mod, "get_git_provenance",
                         lambda r: {"git_commit": None,
                                    "git_dirty": True}):
        out, err, co, ce = _cap()
        with co, ce:
            rc = main(["run", "--manifest", str(mf),
                       "--output", "r.json"])
    assert rc == 0
    assert got["path"] == Path("r.json")
    assert out.getvalue().splitlines()[0] == "[OK] 评测完成：r.json"


# ---------- argparse help ----------

def test_top_help_usage_prog_batch54():
    out, err, co, ce = _cap()
    with pytest.raises(SystemExit):
        with co, ce:
            main(["--help"])
    assert out.getvalue().splitlines()[0] == (
        "usage: evaluation.cli [-h] {run,validate-report,inspect-doc}"
        " ...")


def test_run_subcommand_help_batch54():
    out, err, co, ce = _cap()
    with pytest.raises(SystemExit) as ei:
        with co, ce:
            main(["run", "--help"])
    assert ei.value.code == 0
    assert "--manifest" in out.getvalue()
    assert "--tolerance-chars" in out.getvalue()


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_parser_prog_batch54():
    src = _src()
    assert 'prog="evaluation.cli"' in src
    assert "subparsers(dest=\"command\", required=True)" in src


# ---------- forbidden tokens 第二百五十三批 ----------

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
