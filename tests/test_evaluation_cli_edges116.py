"""evaluation/cli.py 第三百九十五轮 edges 测试（Round 951）。

补强 edges115 未触及的角度（第三百二十七批，probe 实证）。

新角度：
- run 清单路径是目录 → is_file False → rc 2
  "[ERROR] 清单不存在"
- validate-report 目录输入 → rc 2 "[ERROR] 报告不存在"
- inspect-doc JSON 顶层是数组 → rc 1
  "[ERROR] JSON 顶层不是对象"
- inspect-doc 完整头部五行精确（document_id/source_path/
  parser_name/parser_version 全给值）
- inspect-doc 负容差 --tolerance-chars -5 原样透传：
  "_tolerance_chars -5 (ok)" 渲染、rc 0
- run --parser kreuzberg --max-chars 500
  --tolerance-chars 11 → kwargs 三项精确透传给
  run_evaluation，rc 0
- forbidden tokens 第四百二十一批（open 1）
"""

from __future__ import annotations

import inspect
import json
import sys
from unittest.mock import patch

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


# ---------- 目录输入 ----------

def test_run_manifest_directory_batch149(tmp_path, capsys):
    rc = main(["run", "--manifest", str(tmp_path), "--output",
               str(tmp_path / "o.json")])
    assert rc == 2
    assert capsys.readouterr().err.strip() == \
        f"[ERROR] 清单不存在: {tmp_path}"


def test_validate_report_directory_batch149(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path)])
    assert rc == 2
    assert capsys.readouterr().err.strip() == \
        f"[ERROR] 报告不存在: {tmp_path}"


# ---------- 数组顶层 ----------

def test_inspect_array_top_level_batch149(tmp_path, capsys):
    f = tmp_path / "arr.json"
    f.write_text("[]", encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 1
    assert capsys.readouterr().err.strip() == \
        "[ERROR] JSON 顶层不是对象"


# ---------- 完整头部 ----------

def test_inspect_full_header_batch149(tmp_path, capsys):
    doc = {"source_type": "pdf", "document_id": "DID-1",
           "source_path": "samples/a.pdf",
           "parser_name": "fallback", "parser_version": "1.2.3",
           "chunks": [{"text": "AB"}, {"text": "CD"}]}
    f = tmp_path / "doc.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == f"file:        {f}"
    assert lines[1] == "document_id: DID-1"
    assert lines[2] == "source:      samples/a.pdf  type=pdf"
    assert lines[3] == "parser:      fallback v1.2.3"
    assert lines[4] == "counts:      elements=0 chunks=2"
    assert lines[5] == ""
    assert lines[6] == "metrics:"


# ---------- 负容差透传 ----------

def test_inspect_negative_tolerance_batch149(tmp_path, capsys):
    doc = {"source_type": "pdf",
           "chunks": [{"text": "AB"}, {"text": "CD"}]}
    f = tmp_path / "doc.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(f), "--tolerance-chars", "-5"])
    assert rc == 0
    out = capsys.readouterr().out
    tol = [ln for ln in out.splitlines()
           if "_tolerance_chars" in ln]
    assert tol == ["  " + "_tolerance_chars".ljust(36) +
                   " -5  (ok)"]


# ---------- run kwargs 透传 ----------

def test_run_kwargs_passthrough_batch149(tmp_path, capsys):
    m = _mk_manifest(tmp_path)
    cap = {}

    def fake_run(manifest, output_path, **k):
        cap.update(k)
        return {"per_doc": [], "devset": {}}

    with patch.object(cli_mod, "run_evaluation",
                      side_effect=fake_run), \
         patch.object(cli_mod, "validate_file",
                      return_value=None), \
         patch.object(cli_mod, "get_git_provenance",
                      return_value={"git_commit": "c" * 40,
                                    "git_dirty": False}):
        rc = main(["run", "--manifest", str(m), "--output",
                   str(tmp_path / "o2.json"),
                   "--parser", "kreuzberg", "--max-chars", "500",
                   "--tolerance-chars", "11"])
    assert rc == 0
    assert cap == {"parser_name": "kreuzberg", "max_chars": 500,
                   "tolerance_chars": 11}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch149():
    src = _src()
    assert "if not manifest_path.is_file():" in src
    assert "if not input_path.is_file():" in src
    assert 'print("[ERROR] JSON 顶层不是对象", file=sys.stderr)' in src
    assert "doc.get('parser_name', '?')" in src


# ---------- forbidden tokens 第四百二十一批 ----------

def test_source_no_eval_batch149():
    assert "eval(" not in _src()


def test_source_no_exec_batch149():
    assert "exec(" not in _src()


def test_source_no_compile_batch149():
    assert "compile(" not in _src()


def test_source_no_globals_batch149():
    assert "globals(" not in _src()


def test_source_no_locals_batch149():
    assert "locals(" not in _src()


def test_source_no_os_system_batch149():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch149():
    assert "subprocess" not in _src()


def test_source_no_popen_batch149():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch149():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch149():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch149():
    assert "socket" not in _src()


def test_source_no_requests_batch149():
    assert "requests" not in _src()


def test_source_no_urllib_batch149():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch149():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch149():
    assert "yield" not in _src()


def test_source_no_async_await_batch149():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch149():
    assert _src().count("open(") == 1
