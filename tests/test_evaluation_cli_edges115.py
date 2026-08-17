"""evaluation/cli.py 第三百八十八轮 edges 测试（Round 944）。

补强 edges114 未触及的角度（第三百二十批，probe 实证）。

新角度：
- validate-report 最小合法报告：provenance 九必填 +
  devset 六必填 + summary/per_doc 空即可 → rc 0
  "[OK] <path> 通过 evaluation-report Schema 校验"
- inspect-doc 空文档四行精确：file 行 8 空格、counts
  elements=0 chunks=0、element_count_by_type 空字典渲染
  （ljust(36) + "   (ok)"，无 items）、chunk_reference
  null (no_chunks)
- main() 缺 argv 实参 → 读 sys.argv（monkeypatch 后
  frobnicate → SystemExit 2）
- run 成功输出的 git 行：git_commit None → 'unknown'
  兜底；40 位 commit 截前 12 位
- forbidden tokens 第四百一十四批
"""

from __future__ import annotations

import inspect
import json
import sys
from unittest.mock import patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main


def _mk_manifest(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf"}]}), encoding="utf-8")
    return f


# ---------- validate-report 最小合法报告 ----------

def test_validate_report_minimal_ok_batch142(tmp_path, capsys):
    rep = {
        "report_version": "1.1",
        "provenance": {
            "git_commit": None, "git_dirty": True,
            "evaluator_version": "1.1", "report_version": "1.1",
            "parser_name": "fallback", "parser_version": None,
            "dependencies": {}, "max_chars": 800,
            "run_timestamp_iso": "2026-01-01T00:00:00+08:00"},
        "devset": {"status": "incomplete", "file_count": 0,
                   "content_group_count": 0, "pdf_count": 0,
                   "docx_count": 0, "categories_covered": []},
        "summary": {}, "per_doc": []}
    rf = tmp_path / "rep.json"
    rf.write_text(json.dumps(rep), encoding="utf-8")
    rc = main(["validate-report", str(rf)])
    assert rc == 0
    assert capsys.readouterr().out.strip() == \
        f"[OK] {rf} 通过 evaluation-report Schema 校验"


# ---------- inspect 空文档 ----------

def test_inspect_empty_elements_lines_batch142(tmp_path, capsys):
    f = tmp_path / "doc.json"
    f.write_text(json.dumps({"source_type": "pdf",
                             "elements": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == f"file:        {f}"
    assert lines[4] == "counts:      elements=0 chunks=0"
    by_type = [ln for ln in lines if "element_count_by_type" in ln]
    assert by_type == ["  " + "element_count_by_type".ljust(36) +
                       "   (ok)"]
    cr = [ln for ln in lines if "chunk_reference_intact_ratio" in ln]
    assert cr == ["  " +
                  "chunk_reference_intact_ratio".ljust(36) +
                  " null  (no_chunks)"]


# ---------- main() 默认 argv ----------

def test_main_default_argv_batch142(monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv", ["evaluation.cli", "frobnicate"])
    with pytest.raises(SystemExit) as ei:
        main()
    assert ei.value.code == 2
    assert "invalid choice: 'frobnicate'" in \
        capsys.readouterr().err


# ---------- run 成功输出 git 行 ----------

def _run_with_git(tmp_path, capsys, git):
    m = _mk_manifest(tmp_path)
    with patch.object(cli_mod, "get_git_provenance",
                      return_value=git), \
         patch.object(cli_mod, "run_evaluation",
                      return_value={"per_doc": [], "devset": {}}), \
         patch.object(cli_mod, "validate_file", return_value=None):
        rc = main(["run", "--manifest", str(m),
                   "--output", str(tmp_path / "o.json")])
    return rc, capsys.readouterr().out


def test_run_git_line_unknown_batch142(tmp_path, capsys):
    rc, out = _run_with_git(
        tmp_path, capsys, {"git_commit": None, "git_dirty": True})
    assert rc == 0
    assert "git_commit=unknown git_dirty=True" in out


def test_run_git_line_truncated_batch142(tmp_path, capsys):
    rc, out = _run_with_git(
        tmp_path, capsys,
        {"git_commit": "abcdef1234567890abcd" + "x" * 20,
         "git_dirty": False})
    assert rc == 0
    assert "git_commit=abcdef123456 git_dirty=False" in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch142():
    src = _src()
    assert "args = _build_parser().parse_args(argv)" in src
    assert "f\"      git_commit={(git.get('git_commit') or 'unknown')[:12]} \"" in src
    assert 'print(f"[OK] {input_path} 通过 evaluation-report Schema 校验")' in src
    assert "def _format_metric(name: str, metric: dict) -> str:" in src


# ---------- forbidden tokens 第四百一十四批 ----------

def test_source_no_eval_batch142():
    assert "eval(" not in _src()


def test_source_no_exec_batch142():
    assert "exec(" not in _src()


def test_source_no_compile_batch142():
    assert "compile(" not in _src()


def test_source_no_globals_batch142():
    assert "globals(" not in _src()


def test_source_no_locals_batch142():
    assert "locals(" not in _src()


def test_source_no_os_system_batch142():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch142():
    assert "subprocess" not in _src()


def test_source_no_popen_batch142():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch142():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch142():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch142():
    assert "socket" not in _src()


def test_source_no_requests_batch142():
    assert "requests" not in _src()


def test_source_no_urllib_batch142():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch142():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch142():
    assert "yield" not in _src()


def test_source_no_async_await_batch142():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch142():
    assert _src().count("open(") == 1
