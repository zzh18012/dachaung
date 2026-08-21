"""evaluation/report.py 第五百七十四轮 edges 测试（Round 1300）。

补强 edges142 未触及的角度（第六百七十二批，probe 实证）。

新角度（异值双板宏平均算术）：
- **异值宏平均**——dlong 板
  cbp 1/15 + dshort 完美板
  cbp 1.0 → macro 恰
  (1/15+1.0)/2 = 8/15 =
  0.5333333333333333（异值
  均值首锁；前史双板均零参
  评或同值）
- **cbf 宏**——(0.125+1.0)/2
  = 0.5625；cbr 双 1.0 →
  1.0（同值侧对照）
- **完美板构造**——heading
  "A"×80 + 短段落 20 字 →
  2 块 [80, 20]，锚 =
  整段 heading after → 三
  元组 (1.0, 1.0, 1.0)
- **异值报告过 Schema**——
  混合值聚合报告 validate
  通关
- forbidden tokens 第七百五十三批（open 0）
"""

from __future__ import annotations

import inspect
import json

import evaluation.report as report_mod
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
SHORT = "Word0. Word1. Word2."
HEAD = "A" * 80


def _board(tmp_path):
    for name, para in (("long.pdf", LONG),
                       ("short.pdf", SHORT)):
        s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
             + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
             % para).encode()
        (tmp_path / name).write_bytes(_wrap(s))
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "a1.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "dlong",
        "chunk_boundary_anchors": [
            {"marker": "Word3.", "position": "after"}]}),
        encoding="utf-8")
    (tmp_path / "ann" / "a2.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "dshort",
        "chunk_boundary_anchors": [
            {"marker": HEAD, "position": "after"}]}),
        encoding="utf-8")
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "dlong", "path": "long.pdf",
             "source_type": "pdf",
             "annotation_file": "ann/a1.json"},
            {"doc_id": "dshort", "path": "short.pdf",
             "source_type": "pdf",
             "annotation_file": "ann/a2.json"}]}),
        encoding="utf-8")
    return load_manifest((tmp_path / "m.json"),
                         project_root=tmp_path)


def _run(tmp_path):
    return run_evaluation(_board(tmp_path),
                          tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=32)


def _cb(dd):
    m = dd["metrics"]
    return (m["chunk_boundary_precision"]["value"],
            m["chunk_boundary_recall"]["value"],
            m["chunk_boundary_f1"]["value"])


# ---------- 异值宏平均 ----------

def test_mixed_cbp_macro_batch498(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["ratio_macro_averages"][
        "chunk_boundary_precision"] == {
        "macro_average": 8 / 15, "participating_docs": 2,
        "not_evaluated": 0}


def test_mixed_cbf_macro_batch498(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["ratio_macro_averages"][
        "chunk_boundary_f1"] == {
        "macro_average": 0.5625, "participating_docs": 2,
        "not_evaluated": 0}


def test_mixed_cbr_macro_batch498(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["ratio_macro_averages"][
        "chunk_boundary_recall"] == {
        "macro_average": 1.0, "participating_docs": 2,
        "not_evaluated": 0}


def test_macro_eight_fifths_exact_batch498(tmp_path):
    r = _run(tmp_path)
    macro = r["summary"]["ratio_macro_averages"][
        "chunk_boundary_precision"]["macro_average"]
    assert macro == (1 / 15 + 1.0) / 2
    assert macro == 0.5333333333333333


# ---------- 双板值向量 ----------

def test_per_doc_value_vector_batch498(tmp_path):
    r = _run(tmp_path)
    vals = [p["metrics"]["chunk_boundary_precision"][
        "value"] for p in r["per_doc"]]
    assert vals == [1 / 15, 1.0]


def test_dlong_trio_batch498(tmp_path):
    r = _run(tmp_path)
    assert _cb(r["per_doc"][0]) == (1 / 15, 1.0, 0.125)


def test_dshort_perfect_trio_batch498(tmp_path):
    r = _run(tmp_path)
    assert _cb(r["per_doc"][1]) == (1.0, 1.0, 1.0)


def test_dshort_f1_reason_none_batch498(tmp_path):
    r = _run(tmp_path)
    assert r["per_doc"][1]["metrics"][
        "chunk_boundary_f1"] == {"value": 1.0,
                                 "reason": None}


# ---------- 异值报告过 Schema ----------

def test_mixed_report_schema_batch498(tmp_path):
    r = _run(tmp_path)
    validate(r, "evaluation-report.schema.json")


def test_counts_two_docs_batch498(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["counts"]["element_count_total"] == {
        "sum": 4, "participating_docs": 2}


def test_counts_only_element_key_batch498(tmp_path):
    r = _run(tmp_path)
    assert set(r["summary"]["counts"]) == {
        "element_count_total"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch498():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src


# ---------- forbidden tokens 第七百五十三批 ----------

def test_source_no_eval_batch498():
    assert "eval(" not in _src()


def test_source_no_exec_batch498():
    assert "exec(" not in _src()


def test_source_no_compile_batch498():
    assert "compile(" not in _src()


def test_source_no_globals_batch498():
    assert "globals(" not in _src()


def test_source_no_locals_batch498():
    assert "locals(" not in _src()


def test_source_no_os_system_batch498():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch498():
    assert ".call(" not in _src()


def test_source_no_popen_batch498():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch498():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch498():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch498():
    assert "socket" not in _src()


def test_source_no_requests_batch498():
    assert "requests" not in _src()


def test_source_no_urllib_batch498():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch498():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch498():
    assert "yield" not in _src()


def test_source_no_async_await_batch498():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch498():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch498():
    assert _src().count("subprocess.run") == 2
