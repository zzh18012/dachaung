"""evaluation/cli.py 第二百五十五轮 edges 测试（Round 811）。

补强 edges95 未触及的角度（第一百七十五批）。

新角度：
- inspect-doc --tolerance-chars 77 透传且 **_tolerance_chars 键
  泄漏进输出行**（runner pop 掉该键，inspect-doc 不 pop →
  "  _tolerance_chars ... 77  (ok)"）
- inspect-doc 指标类排序行为面：首行 pipeline_success（bool 类
  按字母序），末行 silent_drop_count（null 类末尾）
- inspect-doc 顶层非对象 JSON（"[1, 2]"）→ rc 1 +
  "[ERROR] JSON 顶层不是对象"
- run 清单不存在 → rc 2 "[ERROR] 清单不存在: <path>"
- run 清单 schema 不过 → rc 1 "[ERROR] 清单加载失败:" 前缀
- inspect-doc / validate-report 文件不存在 → 各自 rc 2 文案
- forbidden tokens 第二百八十一批
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json
import tempfile
from pathlib import Path

import evaluation.cli as cli_mod
from evaluation.cli import main


def _cap():
    out, err = io.StringIO(), io.StringIO()
    return out, err, contextlib.redirect_stdout(out), \
        contextlib.redirect_stderr(err)


DOC = {"document_id": "d1", "source_type": "pdf",
       "elements": [
           {"element_id": "e1", "type": "paragraph",
            "content": "A"},
           {"element_id": "e2", "type": "paragraph",
            "content": "B"}],
       "chunks": [
           {"text": "A", "source_element_ids": ["e1"]},
           {"text": "B", "source_element_ids": ["e2"]}]}


def _write(tmp, name, obj):
    f = tmp / name
    f.write_text(json.dumps(obj), encoding="utf-8")
    return f


# ---------- _tolerance_chars 泄漏行 ----------

def test_inspect_doc_tolerance_leak_line_batch55(tmp_path):
    df = _write(tmp_path, "doc.json", DOC)
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(df), "--tolerance-chars",
                   "77"])
    assert rc == 0
    assert "  _tolerance_chars                     77  (ok)" in \
        out.getvalue().splitlines()


# ---------- 排序类行为面 ----------

def test_inspect_doc_metric_sort_bounds_batch55(tmp_path):
    df = _write(tmp_path, "doc.json", DOC)
    out, err, co, ce = _cap()
    with co, ce:
        main(["inspect-doc", str(df)])
    metric_lines = [l for l in out.getvalue().splitlines()
                    if l.startswith("  ")]
    assert metric_lines[0] == \
        "  pipeline_success                     true  (ok)"
    assert metric_lines[-1] == \
        "  silent_drop_count                    null  (no_expectations)"


# ---------- 顶层非对象 ----------

def test_inspect_doc_top_level_list_batch55(tmp_path):
    nd = tmp_path / "nd.json"
    nd.write_text("[1, 2]", encoding="utf-8")
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(nd)])
    assert rc == 1
    assert err.getvalue().strip() == "[ERROR] JSON 顶层不是对象"


# ---------- run 清单不存在 ----------

def test_run_manifest_missing_rc2_batch55(tmp_path):
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["run", "--manifest",
                   str(tmp_path / "nope.json"),
                   "--output", "r.json"])
    assert rc == 2
    assert err.getvalue().startswith("[ERROR] 清单不存在: ")


# ---------- run 清单 schema 失败 ----------

def test_run_manifest_schema_fail_rc1_batch55(tmp_path):
    bm = _write(tmp_path, "bm.json", {})
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["run", "--manifest", str(bm),
                   "--output", "r.json"])
    assert rc == 1
    assert err.getvalue().startswith(
        "[ERROR] 清单加载失败: Schema 'manifest.schema.json' "
        "校验失败")


# ---------- inspect-doc 文件不存在 ----------

def test_inspect_doc_missing_rc2_batch55(tmp_path):
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(tmp_path / "nope.json")])
    assert rc == 2
    assert err.getvalue().startswith("[ERROR] 文档不存在: ")


# ---------- validate-report 文件不存在 ----------

def test_validate_report_missing_rc2_batch55(tmp_path):
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["validate-report", str(tmp_path / "nope.json")])
    assert rc == 2
    assert err.getvalue().startswith("[ERROR] 报告不存在: ")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "metrics.update(chunk_boundary_prf(doc, None, tolerance_chars=args.tolerance_chars))" in src
    assert "if not isinstance(doc, dict):" in src
    assert ("print(f\"[ERROR] 清单不存在: {manifest_path}\", "
            "file=sys.stderr)") in src


# ---------- forbidden tokens 第二百八十一批 ----------

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
