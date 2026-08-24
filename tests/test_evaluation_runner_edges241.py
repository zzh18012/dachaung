"""evaluation/runner.py 第六百七十六轮 edges 测试（Round 1350）。

补强 edges240 未触及的角度（第七百二十二批，probe 实证）。

新角度（expectations+annotation+tolerance 三合板）：
- **三合板**——同 doc 同
  时带 expectations
  {paragraph:3} +
  annotation
  Word1. after +
  tolerance_chars
  kwarg（联合态
  首锁）
- **sdc=2**——期望 3 实际
  1 → per_doc
  silent_drop_count
  {2, None}
- **cb 三元组**——tol40
  {1/14, 1.0, 2/15}
  与 sdc 同 doc 共存
- **tol 翻转独立**——
  tol0 cbp 翻 0.0 但
  sdc 仍 2（容差不扰
  expectations）
- **sdt 顶层求和**——
  summary.silent_drop_
  total == 2 == per-doc
- forbidden tokens 第七百九十一批（open 2）
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


def _run(tmp_path, tol=40):
    (tmp_path / "c.pdf").write_bytes(_wrap(ONEP))
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "a.json").write_text(
        json.dumps({
            "annotation_version": "1.0",
            "doc_id": "g1",
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
             "annotation_file": "ann/a.json",
             "expectations": {
                 "element_count_by_type": {
                     "paragraph": 3}}}]}),
        encoding="utf-8")
    mf = load_manifest(tmp_path / "m.json",
                       project_root=tmp_path)
    return run_evaluation(mf, tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=32,
                          tolerance_chars=tol)


# ---------- 三合板 ----------

def test_composite_sdc_two_batch548(tmp_path):
    r = _run(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "silent_drop_count"] == {
        "value": 2, "reason": None}


def test_composite_cbp_hit_batch548(tmp_path):
    r = _run(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "chunk_boundary_precision"] == {
        "value": 1 / 14, "reason": None}


def test_composite_cbr_one_batch548(tmp_path):
    r = _run(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}


def test_composite_f1_batch548(tmp_path):
    r = _run(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "chunk_boundary_f1"] == {
        "value": 2 / 15, "reason": None}


# ---------- tol 翻转独立 ----------

def test_tol0_cbp_zero_batch548(tmp_path):
    r = _run(tmp_path, tol=0)
    assert r["per_doc"][0]["metrics"][
        "chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}


def test_tol0_sdc_unchanged_batch548(tmp_path):
    r = _run(tmp_path, tol=0)
    assert r["per_doc"][0]["metrics"][
        "silent_drop_count"] == {
        "value": 2, "reason": None}


def test_tol0_cbr_zero_batch548(tmp_path):
    r = _run(tmp_path, tol=0)
    assert r["per_doc"][0]["metrics"][
        "chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}


def test_tol0_zero_trio_batch548(tmp_path):
    m = _run(tmp_path, tol=0)["per_doc"][0][
        "metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.0, "reason": None}


# ---------- sdt 顶层求和 ----------

def test_sdt_top_level_two_batch548(tmp_path):
    assert _run(tmp_path)["summary"][
        "silent_drop_total"] == 2


def test_sdt_equals_per_doc_batch548(tmp_path):
    r = _run(tmp_path)
    assert (r["summary"]["silent_drop_total"]
            == r["per_doc"][0]["metrics"][
                "silent_drop_count"]["value"])


def test_sdt_tol_independent_batch548(tmp_path):
    assert (_run(tmp_path, tol=0)["summary"][
        "silent_drop_total"] == 2)


# ---------- counts 不变 ----------

def test_counts_only_ect_batch548(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["counts"] == {
        "element_count_total": {
            "sum": 1, "participating_docs": 1}}


# ---------- 联合态其他指标 ----------

def test_composite_pipeline_success_batch548(
        tmp_path):
    r = _run(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "pipeline_success"] == {"value": True,
                                "reason": None}


def test_composite_schema_valid_batch548(
        tmp_path):
    r = _run(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "schema_valid"] == {"value": True,
                            "reason": None}


def test_composite_metrics_20_keys_batch548(
        tmp_path):
    r = _run(tmp_path)
    assert len(r["per_doc"][0]["metrics"]) == 20


def test_composite_success_rate_batch548(
        tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["success_rates"][
        "pipeline_success"] == {
        "success_count": 1, "total": 1,
        "rate": 1.0}


# ---------- 报告合法性 ----------

def test_report_schema_batch548(tmp_path):
    validate(_run(tmp_path),
             "evaluation-report.schema.json")


def test_report_on_disk_round_trip_batch548(
        tmp_path):
    r = _run(tmp_path)
    on_disk = json.loads(
        (tmp_path / "r.json").read_text(
            encoding="utf-8"))
    assert on_disk == r


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_pop_internal_keys_batch548():
    src = _src()
    assert 'chunk_b.pop("_tolerance_chars"' in src
    assert 'chunk_b.pop("_missing_markers"' in src


def test_source_key_counts_batch548():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("per_doc") == 12
    assert src.count("open(") == 2


# ---------- forbidden tokens 第七百九十一批 ----------

def test_source_no_eval_batch548():
    assert "eval(" not in _src()


def test_source_no_exec_batch548():
    assert "exec(" not in _src()


def test_source_no_compile_batch548():
    assert "compile(" not in _src()


def test_source_no_globals_batch548():
    assert "globals(" not in _src()


def test_source_no_locals_batch548():
    assert "locals(" not in _src()


def test_source_no_os_system_batch548():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch548():
    assert "subprocess" not in _src()


def test_source_no_popen_batch548():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch548():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch548():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch548():
    assert "socket" not in _src()


def test_source_no_requests_batch548():
    assert "requests" not in _src()


def test_source_no_urllib_batch548():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch548():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch548():
    assert "yield" not in _src()


def test_source_no_async_await_batch548():
    assert "async " not in _src()
    assert "await " not in _src()
