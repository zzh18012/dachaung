"""evaluation/runner.py 第六百七十四轮 edges 测试（Round 1339）。

补强 edges238 未触及的角度（第七百一十一批，probe 实证）。

新角度（tolerance_chars kwarg 全链 / ef 无残留）：
- **tol0 全零**——
  tolerance_chars=0
  + Word1. 锚 →
  cbp/cbr 均
  {0.0, None}（runner
  级 tolerance 透传
  首锁）
- **tol30 翻命中**
  ——{1/14, 1.0}；
  macro 联动
  0.0 vs 1/14
- **报告无 tolerance**
  ——即便
  tolerance_chars=0
  报告 JSON 亦无
  'tolerance' 字样
  （不记录面首锁）
- **ef 无残留**——
  ef 处理后 _per_doc
  目录存在但空
  （stub unlink 锁）
- forbidden tokens 第七百八十二批（open 2）
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from evaluation.schema import validate


def _wrap(s: bytes) -> bytes:
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xp = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


LONG = " ".join("Word%d." % i for i in range(60))
ONEP = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
        % LONG).encode()


def _mf(tmp_path):
    (tmp_path / "c.pdf").write_bytes(_wrap(ONEP))
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "a.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "g1",
        "chunk_boundary_anchors": [
            {"marker": "Word1.",
             "position": "after"}]}),
        encoding="utf-8")
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "g1", "path": "c.pdf",
             "source_type": "pdf",
             "annotation_file": "ann/a.json"}],
        "expected_failures": [
            {"doc_id": "ef1", "path": "nope.pdf",
             "expected_error_code":
                 "file_not_found"}]}),
        encoding="utf-8")
    return load_manifest(tmp_path / "m.json",
                         project_root=tmp_path)


def _run(tmp_path, tol):
    return run_evaluation(_mf(tmp_path),
                          tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=32,
                          tolerance_chars=tol)


# ---------- tol0 全零 ----------

def test_tol0_cbp_zero_batch537(tmp_path):
    r = _run(tmp_path, 0)
    assert r["per_doc"][0]["metrics"][
        "chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}


def test_tol0_cbr_zero_batch537(tmp_path):
    r = _run(tmp_path, 0)
    assert r["per_doc"][0]["metrics"][
        "chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}


# ---------- tol30 翻命中 ----------

def test_tol30_cbp_hit_batch537(tmp_path):
    r = _run(tmp_path, 30)
    assert r["per_doc"][0]["metrics"][
        "chunk_boundary_precision"] == {
        "value": 1 / 14, "reason": None}


def test_tol30_cbr_hit_batch537(tmp_path):
    r = _run(tmp_path, 30)
    assert r["per_doc"][0]["metrics"][
        "chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}


def test_macro_follows_tolerance_batch537(
        tmp_path):
    r0 = _run(tmp_path, 0)
    r30 = _run(tmp_path, 30)
    m0 = r0["summary"]["ratio_macro_averages"][
        "chunk_boundary_precision"]
    m30 = r30["summary"]["ratio_macro_averages"][
        "chunk_boundary_precision"]
    assert m0["macro_average"] == 0.0
    assert m30["macro_average"] == 1 / 14
    assert m0["participating_docs"] == 1
    assert m30["participating_docs"] == 1


# ---------- 报告无 tolerance ----------

def test_no_tolerance_in_report_batch537(tmp_path):
    r = _run(tmp_path, 0)
    assert "tolerance" not in json.dumps(r)


# ---------- ef 无残留 ----------

def test_per_doc_dir_empty_batch537(tmp_path):
    _run(tmp_path, 30)
    pd = tmp_path / "_per_doc"
    assert pd.is_dir()
    assert list(pd.iterdir()) == []


def test_ef_processed_batch537(tmp_path):
    r = _run(tmp_path, 30)
    assert r["expected_failures"][0][
        "matches"] is True


# ---------- 报告合法性 ----------

def test_report_schema_batch537(tmp_path):
    validate(_run(tmp_path, 0),
             "evaluation-report.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_counts_batch537():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("per_doc") == 12
    assert src.count("open(") == 2


def test_source_tolerance_param_batch537():
    assert "tolerance_chars: int = 30" in _src()


# ---------- forbidden tokens 第七百八十二批 ----------

def test_source_no_eval_batch537():
    assert "eval(" not in _src()


def test_source_no_exec_batch537():
    assert "exec(" not in _src()


def test_source_no_compile_batch537():
    assert "compile(" not in _src()


def test_source_no_globals_batch537():
    assert "globals(" not in _src()


def test_source_no_locals_batch537():
    assert "locals(" not in _src()


def test_source_no_os_system_batch537():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch537():
    assert "subprocess" not in _src()


def test_source_no_popen_batch537():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch537():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch537():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch537():
    assert "socket" not in _src()


def test_source_no_requests_batch537():
    assert "requests" not in _src()


def test_source_no_urllib_batch537():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch537():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch537():
    assert "yield" not in _src()


def test_source_no_async_await_batch537():
    assert "async " not in _src()
    assert "await " not in _src()
