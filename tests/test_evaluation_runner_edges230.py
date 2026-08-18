"""evaluation/runner.py 第六百六十五轮 edges 测试（Round 1285）。

补强 edges229 未触及的角度（第六百五十七批，probe 实证）。

新角度（边界指标三态零税 / 标注文件缺失降级）：
- **空锚列表**——标注在场但
  chunk_boundary_anchors [] →
  cbp/cbr/cbf 全 null +
  reason "no_ground_truth_
  anchors"（区别于 _in_stream
  变体；cbp 也 null 而非 0.0
  ——三分支首锁）
- **标注文件缺失**——manifest
  指向不存在的 ann/gone.json →
  静默按无标注处理 → 全
  no_annotation（缺失降级首锁）
- **聚合三态**——空锚 →
  {None, 0, 1}（not_evaluated
  计 1）
- forbidden tokens 第七百四十四批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


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
HEAD = "A" * 80


def _pdf(tmp_path):
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()
    (tmp_path / "combo.pdf").write_bytes(_wrap(s))


def _board(tmp_path, annotation_file):
    if annotation_file == "ann/empty.json":
        (tmp_path / "ann").mkdir(exist_ok=True)
        (tmp_path / "ann" / "empty.json").write_text(
            json.dumps({
                "annotation_version": "1.0", "doc_id": "combo",
                "chunk_boundary_anchors": []}),
            encoding="utf-8")
    mf = tmp_path / "m.json"
    doc = {"doc_id": "combo", "path": "combo.pdf",
           "source_type": "pdf"}
    if annotation_file is not None:
        doc["annotation_file"] = annotation_file
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [doc]}), encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


def _run(tmp_path, annotation_file):
    _pdf(tmp_path)
    return run_evaluation(_board(tmp_path, annotation_file),
                          tmp_path / "r.json",
                          parser_name="fallback", max_chars=32)


def _metrics(r):
    m = r["per_doc"][0]["metrics"]
    return (m["chunk_boundary_precision"],
            m["chunk_boundary_recall"],
            m["chunk_boundary_f1"])


# ---------- 空锚列表 ----------

NGT = {"value": None, "reason": "no_ground_truth_anchors"}


def test_empty_anchors_all_null_batch483(tmp_path):
    assert _metrics(_run(tmp_path, "ann/empty.json")) == (
        NGT, NGT, NGT)


def test_empty_anchors_cbp_null_not_zero_batch483(tmp_path):
    r = _run(tmp_path, "ann/empty.json")
    assert r["per_doc"][0]["metrics"][
        "chunk_boundary_precision"]["value"] is None


def test_empty_anchors_aggregate_batch483(tmp_path):
    r = _run(tmp_path, "ann/empty.json")
    agg = r["summary"]["ratio_macro_averages"]
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall", "chunk_boundary_f1"):
        assert agg[k] == {"macro_average": None,
                          "participating_docs": 0,
                          "not_evaluated": 1}


# ---------- 标注文件缺失降级 ----------

NOANN = {"value": None, "reason": "no_annotation"}


def test_missing_file_no_annotation_batch483(tmp_path):
    assert _metrics(_run(tmp_path, "ann/gone.json")) == (
        NOANN, NOANN, NOANN)


def test_missing_file_aggregate_batch483(tmp_path):
    r = _run(tmp_path, "ann/gone.json")
    agg = r["summary"]["ratio_macro_averages"]
    assert agg["chunk_boundary_recall"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 1}


def test_missing_file_counts_intact_batch483(tmp_path):
    r = _run(tmp_path, "ann/gone.json")
    assert r["summary"]["counts"]["element_count_total"] == {
        "sum": 2, "participating_docs": 1}


# ---------- 无标注键 ----------

def test_no_key_no_annotation_batch483(tmp_path):
    assert _metrics(_run(tmp_path, None)) == (
        NOANN, NOANN, NOANN)


def test_missing_vs_nokey_same_reason_batch483(tmp_path):
    r_miss = _run(tmp_path, "ann/gone.json")
    r_none = _run(tmp_path, None)
    assert _metrics(r_miss) == _metrics(r_none)


# ---------- 三态对照 ----------

def test_absent_marker_cbp_zero_batch483(tmp_path):
    r = _run_absent(tmp_path)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert m["chunk_boundary_f1"] == {
        "value": None,
        "reason": "precision_or_recall_not_evaluated"}


def _run_absent(tmp_path):
    _pdf(tmp_path)
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "absent.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "combo",
        "chunk_boundary_anchors": [
            {"marker": "NotInDoc.", "position": "after"}]}),
        encoding="utf-8")
    mf = tmp_path / "m_abs.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "combo", "path": "combo.pdf",
                       "source_type": "pdf",
                       "annotation_file":
                       "ann/absent.json"}]}),
        encoding="utf-8")
    return run_evaluation(load_manifest(mf, project_root=tmp_path),
                          tmp_path / "ra.json",
                          parser_name="fallback", max_chars=32)


def test_three_states_reasons_distinct_batch483(tmp_path):
    reasons = set()
    for af in ("ann/empty.json", "ann/gone.json"):
        for d in _metrics(_run(tmp_path, af)):
            reasons.add(d["reason"])
    r_abs = _run_absent(tmp_path)
    reasons.add(r_abs["per_doc"][0]["metrics"][
        "chunk_boundary_recall"]["reason"])
    reasons.add(r_abs["per_doc"][0]["metrics"][
        "chunk_boundary_f1"]["reason"])
    assert reasons == {"no_ground_truth_anchors",
                       "no_annotation",
                       "no_ground_truth_anchors_in_stream",
                       "precision_or_recall_not_evaluated"}


# ---------- 报告面 ----------

def test_empty_anchors_round_trip_batch483(tmp_path):
    r = _run(tmp_path, "ann/empty.json")
    assert json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8")) == r


def test_empty_anchors_success_batch483(tmp_path):
    r = _run(tmp_path, "ann/empty.json")
    assert r["summary"]["success_rates"] == {
        "pipeline_success": {"success_count": 1,
                             "total": 1, "rate": 1.0}}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_counts_batch483():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第七百四十四批 ----------

def test_source_no_eval_batch483():
    assert "eval(" not in _src()


def test_source_no_exec_batch483():
    assert "exec(" not in _src()


def test_source_no_compile_batch483():
    assert "compile(" not in _src()


def test_source_no_globals_batch483():
    assert "globals(" not in _src()


def test_source_no_locals_batch483():
    assert "locals(" not in _src()


def test_source_no_os_system_batch483():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch483():
    assert "subprocess" not in _src()


def test_source_no_popen_batch483():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch483():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch483():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch483():
    assert "socket" not in _src()


def test_source_no_requests_batch483():
    assert "requests" not in _src()


def test_source_no_urllib_batch483():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch483():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch483():
    assert "yield" not in _src()


def test_source_no_async_await_batch483():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch483():
    assert _src().count("open(") == 2
