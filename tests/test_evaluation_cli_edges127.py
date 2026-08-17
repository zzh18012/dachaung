"""evaluation/cli.py 第四百七十二轮 edges 测试（Round 1028）。

补强 edges126 未触及的角度（第四百零四批，probe 实证）。

新角度（跨工件误喂第二、三路）：
- manifest JSON 喂给 inspect-doc：rc 0、四行表头全 "?"
  回退（document_id/source/parser）、counts 0/0、
  type=unknown——documents 段被无视
- annotation JSON 喂给 inspect-doc：文件里带 doc_id
  "d1" 却渲染 document_id: ?（标注键名是 doc_id、
  inspect-doc 读 document_id——键名错位回退）
- 误喂路径下 --tolerance-chars 9 照常透传（指标块
  _tolerance_chars 行显示 9）
- manifest JSON 喂给 validate-report：rc 1、[FAIL]、
  6 处、首错 'report_version'——与文档 JSON 误喂
  （edges125）同一失败屏，两种工件殊途同归
- forbidden tokens 第四百九十八批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.cli as cli_mod
from evaluation.cli import main


def _manifest_file(tmp_path):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf"}],
        "expected_failures": []}), encoding="utf-8")
    return f


def _annotation_file(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "AB", "position": "after"}]}),
        encoding="utf-8")
    return f


# ---------- manifest → inspect-doc ----------

def test_manifest_into_inspect_header_batch226(
        tmp_path, capsys):
    rc = main(["inspect-doc", str(_manifest_file(tmp_path))])
    out = capsys.readouterr().out
    assert rc == 0
    assert "document_id: ?" in out
    assert "source:      ?  type=unknown" in out
    assert "parser:      ? v?" in out
    assert "counts:      elements=0 chunks=0" in out


def test_manifest_into_inspect_metric_count_batch226(
        tmp_path, capsys):
    main(["inspect-doc", str(_manifest_file(tmp_path))])
    out = capsys.readouterr().out
    metric_lines = [ln for ln in out.splitlines()
                    if ln.startswith("  ") and "(" in ln]
    assert len(metric_lines) == 21
    assert "  pipeline_success                     true  (ok)" in out
    assert "  schema_valid                         false  (ok)" in out


# ---------- annotation → inspect-doc ----------

def test_annotation_docid_key_mismatch_batch226(
        tmp_path, capsys):
    rc = main(["inspect-doc", str(_annotation_file(tmp_path))])
    out = capsys.readouterr().out
    assert rc == 0
    assert "document_id: ?" in out
    payload = json.loads(
        _annotation_file(tmp_path).read_text(encoding="utf-8"))
    assert payload["doc_id"] == "d1"


def test_annotation_feed_tolerance_passthrough_batch226(
        tmp_path, capsys):
    main(["inspect-doc", str(_annotation_file(tmp_path)),
          "--tolerance-chars", "9"])
    out = capsys.readouterr().out
    tol = [ln for ln in out.splitlines()
           if ln.strip().startswith("_tolerance_chars")]
    assert tol == ["  _tolerance_chars                     9"
                   "  (ok)"]


# ---------- manifest → validate-report ----------

def test_manifest_into_validate_report_batch226(
        tmp_path, capsys):
    rc = main(["validate-report",
               str(_manifest_file(tmp_path))])
    err = capsys.readouterr().err
    assert rc == 1
    assert "[FAIL]" in err
    assert "6 处" in err
    assert ("'report_version' is a required property"
            " @ path=[]") in err


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch226():
    src = _src()
    assert "inspect-doc" in src
    assert "doc.get('document_id', '?')" in src


# ---------- forbidden tokens 第四百九十八批 ----------

def test_source_no_eval_batch226():
    assert "eval(" not in _src()


def test_source_no_exec_batch226():
    assert "exec(" not in _src()


def test_source_no_compile_batch226():
    assert "compile(" not in _src()


def test_source_no_globals_batch226():
    assert "globals(" not in _src()


def test_source_no_locals_batch226():
    assert "locals(" not in _src()


def test_source_no_os_system_batch226():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch226():
    assert "subprocess" not in _src()


def test_source_no_popen_batch226():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch226():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch226():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch226():
    assert "socket" not in _src()


def test_source_no_requests_batch226():
    assert "requests" not in _src()


def test_source_no_urllib_batch226():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch226():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch226():
    assert "yield" not in _src()


def test_source_no_async_await_batch226():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch226():
    assert _src().count("open(") == 1
