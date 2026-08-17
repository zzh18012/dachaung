"""evaluation/cli.py 第四百五十八轮 edges 测试（Round 1014）。

补强 edges124 未触及的角度（第三百九十批，probe 实证）。

新角度（跨工件误喂回合）：
- 评测报告 JSON 喂给 inspect-doc：rc 0，三处 "?" 回退
  （document_id / source / parser），type=unknown；
  pipeline_success true 与 schema_valid false 同屏共存；
  error_code null 的 reason None 渲染成 "(None)"；空 dict
  指标 element_count_by_type 行内无 "="；21 行指标与四桶
  次序 bool→数值→dict→null 全锁
- 文档 JSON 喂给 validate-report：rc 1 [FAIL]，6 处缺失，
  首错 'report_version' is a required property @ path=[]
- forbidden tokens 第四百八十四批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.cli as cli_mod
from evaluation.cli import main


def _report_file(tmp_path):
    report = {
        "report_version": "1.1",
        "provenance": {}, "devset": {}, "summary": {},
        "per_doc": [], "expected_failures": []}
    f = tmp_path / "rep.json"
    f.write_text(json.dumps(report), encoding="utf-8")
    return f


def _doc_file(tmp_path):
    doc = {"schema_version": "0.1.0", "document_id": "d",
           "source_type": "pdf", "elements": [], "chunks": [],
           "relations": [], "warnings": [], "errors": [],
           "metadata": {}}
    f = tmp_path / "doc.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    return f


# ---------- 报告 → inspect-doc：表头 ----------

def test_report_into_inspect_header_batch212(tmp_path, capsys):
    rc = main(["inspect-doc", str(_report_file(tmp_path))])
    out = capsys.readouterr().out
    assert rc == 0
    assert "document_id: ?" in out
    assert "source:      ?  type=unknown" in out
    assert "parser:      ? v?" in out
    assert "counts:      elements=0 chunks=0" in out


# ---------- 报告 → inspect-doc：指标行 ----------

def test_report_into_inspect_metric_lines_batch212(
        tmp_path, capsys):
    main(["inspect-doc", str(_report_file(tmp_path))])
    out = capsys.readouterr().out
    assert "  pipeline_success                     true  (ok)" in out
    assert "  schema_valid                         false  (ok)" in out
    assert "  error_code                           null  (None)" in out
    ecbt = [ln for ln in out.splitlines()
            if ln.strip().startswith("element_count_by_type")]
    assert len(ecbt) == 1 and "=" not in ecbt[0]
    assert ecbt[0].rstrip().endswith("(ok)")
    metric_lines = [ln for ln in out.splitlines()
                    if ln.startswith("  ") and "(" in ln]
    assert len(metric_lines) == 21


# ---------- 报告 → inspect-doc：四桶次序 ----------

def test_report_into_inspect_bucket_order_batch212(
        tmp_path, capsys):
    main(["inspect-doc", str(_report_file(tmp_path))])
    out = capsys.readouterr().out
    names = [ln.strip().split()[0]
             for ln in out.splitlines()
             if ln.startswith("  ") and "(" in ln]
    assert names[0] == "pipeline_success"
    assert names[-1] == "text_char_multiset_recall"
    i = {n: names.index(n) for n in
         ("_tolerance_chars", "element_count_total",
          "element_count_by_type", "chunk_boundary_f1")}
    assert (i["_tolerance_chars"]
            < i["element_count_total"]
            < i["element_count_by_type"]
            < i["chunk_boundary_f1"])


# ---------- 文档 → validate-report ----------

def test_doc_into_validate_report_fail_batch212(
        tmp_path, capsys):
    rc = main(["validate-report", str(_doc_file(tmp_path))])
    cap = capsys.readouterr()
    assert rc == 1
    assert "[FAIL]" in cap.err
    assert "'report_version' is a required property" in cap.err
    assert "6 处" in cap.err
    assert cap.out == ""


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch212():
    src = _src()
    assert "null  ({reason})" in src
    assert "({reason or 'ok'})" in src
    assert "source_type = doc.get(\"source_type\", \"unknown\")" in src


# ---------- forbidden tokens 第四百八十四批 ----------

def test_source_no_eval_batch212():
    assert "eval(" not in _src()


def test_source_no_exec_batch212():
    assert "exec(" not in _src()


def test_source_no_compile_batch212():
    assert "compile(" not in _src()


def test_source_no_globals_batch212():
    assert "globals(" not in _src()


def test_source_no_locals_batch212():
    assert "locals(" not in _src()


def test_source_no_os_system_batch212():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch212():
    assert "subprocess" not in _src()


def test_source_no_popen_batch212():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch212():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch212():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch212():
    assert "socket" not in _src()


def test_source_no_requests_batch212():
    assert "requests" not in _src()


def test_source_no_urllib_batch212():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch212():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch212():
    assert "yield" not in _src()


def test_source_no_async_await_batch212():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch212():
    assert _src().count("open(") == 1
