"""evaluation/cli.py 第二百四十一轮 edges 测试（Round 797）。

补强 edges93 未触及的角度（第一百六十一批）。

新角度：
- inspect-doc 元信息正例行：document_id/source/parser 三行带
  实值（与 '?' 占位族对照）
- inspect-doc 无 chunks 键：counts chunks=0；heading_boundary
  0.0（有 heading 无 chunk）；chunk_ref no_chunks；而
  chunk_boundary_* 走 no_annotation（annotation None 的早退
  先于 chunks 检查 —— CLI 无标注路径的固定分支）
- run_evaluation 抛非 EvalSchemaError（OSError）→ 原样传播
  （CLI 只捕获 EvalSchemaError，未包装）
- run --help usage 首行 "usage: evaluation.cli run [-h]
  --manifest MANIFEST --output OUTPUT"
- forbidden tokens 第二百六十七批
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


# ---------- 元信息正例行 ----------

def test_inspect_doc_metadata_lines_batch54(tmp_path):
    f = tmp_path / "doc.json"
    f.write_text(json.dumps({
        "document_id": "d1", "source_path": "s.pdf",
        "source_type": "pdf", "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "content": "A"}],
        "chunks": [{"text": "A", "source_element_ids": ["e1"]}]}),
        encoding="utf-8")
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(f)])
    lines = out.getvalue().splitlines()
    assert rc == 0
    assert lines[1] == "document_id: d1"
    assert lines[2] == "source:      s.pdf  type=pdf"
    assert lines[3] == "parser:      fallback v1.0"


# ---------- 无 chunks 键 ----------

def test_inspect_doc_no_chunks_key_batch54(tmp_path):
    f = tmp_path / "nochunks.json"
    f.write_text(json.dumps({
        "document_id": "d", "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "heading",
                      "content": "A"}]}), encoding="utf-8")
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(f)])
    lines = out.getvalue().splitlines()
    assert rc == 0
    assert lines[4] == "counts:      elements=1 chunks=0"
    body = "\n".join(lines)
    assert "heading_boundary_compliance          0.0000  (ok)" in body
    assert "chunk_reference_intact_ratio         null  " \
           "(no_chunks)" in body
    assert "chunk_boundary_precision             null  " \
           "(no_annotation)" in body


# ---------- 非 Schema 异常传播 ----------

def test_run_evaluation_oserror_propagates_batch54(tmp_path):
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": []}), encoding="utf-8")
    with patch.object(cli_mod, "run_evaluation",
                      side_effect=OSError("disk")):
        out, err, co, ce = _cap()
        with pytest.raises(OSError, match="disk"):
            with co, ce:
                main(["run", "--manifest", str(mf),
                      "--output", "r.json"])


# ---------- run --help usage 首行 ----------

def test_run_help_usage_first_line_batch54():
    out, err, co, ce = _cap()
    with pytest.raises(SystemExit):
        with co, ce:
            main(["run", "--help"])
    assert out.getvalue().splitlines()[0] == (
        "usage: evaluation.cli run [-h] --manifest MANIFEST "
        "--output OUTPUT")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_entry_point_batch54():
    src = _src()
    assert "raise SystemExit(main())" in src
    assert "if __name__ == \"__main__\":" in src


# ---------- forbidden tokens 第二百六十七批 ----------

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
