"""evaluation/runner.py 第六百六十七轮 edges 测试（Round 1297）。

补强 edges231 未触及的角度（第六百六十九批，probe 实证）。

新角度（双板锚定聚合 / 跨文档恒等）：
- **双锚同板**——两份同板锚定
  PDF 同 devset → cbp
  {1/15, 2, 0} / cbr {1.0,
  2, 0} / cbf {0.125, 2, 0}
  （participating_docs 2
  首锁）
- **跨文档 metrics 恒等**——
  两 per_doc 的 metrics
  dict 完全相等（确定性
  首锁；edges184 为异板）
- **noann 劈叉参与**——d2
  去标注 → 三键 {macro 不
  参与值, 1 参与, 1 未评}
  而 counts {sum 4,
  participating 2} 不动
  （计数与比例分流首锁）
- **空锚劈叉 reason**——d2
  空锚 → 同聚合形态但 d2
  reason no_ground_truth_
  anchors（区别 no_
  annotation）
- **success 面**——{2, 2,
  1.0} 三模式皆同
- forbidden tokens 第七百五十一批（open 2）
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
STREAM = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
          + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
          % LONG).encode()


def _board(tmp_path, mode):
    (tmp_path / "c1.pdf").write_bytes(_wrap(STREAM))
    (tmp_path / "c2.pdf").write_bytes(_wrap(STREAM))
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "a1.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "Word3.", "position": "after"}]}),
        encoding="utf-8")
    if mode == "both":
        (tmp_path / "ann" / "a2.json").write_text(json.dumps({
            "annotation_version": "1.0", "doc_id": "d2",
            "chunk_boundary_anchors": [
                {"marker": "Word3.", "position": "after"}]}),
            encoding="utf-8")
    elif mode == "empty":
        (tmp_path / "ann" / "a2.json").write_text(json.dumps({
            "annotation_version": "1.0", "doc_id": "d2",
            "chunk_boundary_anchors": []}),
            encoding="utf-8")
    docs = [{"doc_id": "d1", "path": "c1.pdf",
             "source_type": "pdf",
             "annotation_file": "ann/a1.json"},
            {"doc_id": "d2", "path": "c2.pdf",
             "source_type": "pdf"}]
    if mode in ("both", "empty"):
        docs[1]["annotation_file"] = "ann/a2.json"
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs}), encoding="utf-8")
    return load_manifest((tmp_path / "m.json"),
                         project_root=tmp_path)


def _run(tmp_path, mode):
    return run_evaluation(_board(tmp_path, mode),
                          tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=32)


# ---------- 双锚同板 ----------

def test_both_doc_ids_order_batch495(tmp_path):
    r = _run(tmp_path, "both")
    assert [p["doc_id"] for p in r["per_doc"]] == ["d1", "d2"]


def test_both_cbp_macro_batch495(tmp_path):
    r = _run(tmp_path, "both")
    assert r["summary"]["ratio_macro_averages"][
        "chunk_boundary_precision"] == {
        "macro_average": 1 / 15, "participating_docs": 2,
        "not_evaluated": 0}


def test_both_cbr_macro_batch495(tmp_path):
    r = _run(tmp_path, "both")
    assert r["summary"]["ratio_macro_averages"][
        "chunk_boundary_recall"] == {
        "macro_average": 1.0, "participating_docs": 2,
        "not_evaluated": 0}


def test_both_cbf_macro_batch495(tmp_path):
    r = _run(tmp_path, "both")
    assert r["summary"]["ratio_macro_averages"][
        "chunk_boundary_f1"] == {
        "macro_average": 0.125, "participating_docs": 2,
        "not_evaluated": 0}


# ---------- 跨文档 metrics 恒等 ----------

def test_both_metrics_identical_batch495(tmp_path):
    r = _run(tmp_path, "both")
    assert r["per_doc"][0]["metrics"] == \
        r["per_doc"][1]["metrics"]


def test_both_d2_cbp_value_batch495(tmp_path):
    r = _run(tmp_path, "both")
    assert r["per_doc"][1]["metrics"][
        "chunk_boundary_precision"] == {
        "value": 1 / 15, "reason": None}


# ---------- noann 劈叉参与 ----------

def test_noann_participation_split_batch495(tmp_path):
    r = _run(tmp_path, "noann")
    agg = r["summary"]["ratio_macro_averages"]
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert agg[k]["participating_docs"] == 1
        assert agg[k]["not_evaluated"] == 1


def test_noann_macro_unchanged_batch495(tmp_path):
    r = _run(tmp_path, "noann")
    agg = r["summary"]["ratio_macro_averages"]
    assert agg["chunk_boundary_precision"][
        "macro_average"] == 1 / 15
    assert agg["chunk_boundary_recall"][
        "macro_average"] == 1.0
    assert agg["chunk_boundary_f1"][
        "macro_average"] == 0.125


def test_noann_d2_reasons_batch495(tmp_path):
    r = _run(tmp_path, "noann")
    m = r["per_doc"][1]["metrics"]
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert m[k] == {"value": None,
                        "reason": "no_annotation"}


def test_noann_counts_unchanged_batch495(tmp_path):
    r_no = _run(tmp_path, "noann")
    r_b = _run(tmp_path, "both")
    assert r_no["summary"]["counts"] == \
        r_b["summary"]["counts"]


# ---------- 空锚劈叉 reason ----------

def test_empty_participation_split_batch495(tmp_path):
    r = _run(tmp_path, "empty")
    agg = r["summary"]["ratio_macro_averages"]
    assert agg["chunk_boundary_precision"] == {
        "macro_average": 1 / 15, "participating_docs": 1,
        "not_evaluated": 1}


def test_empty_d2_reasons_batch495(tmp_path):
    r = _run(tmp_path, "empty")
    m = r["per_doc"][1]["metrics"]
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert m[k] == {
            "value": None,
            "reason": "no_ground_truth_anchors"}


# ---------- counts / success 面 ----------

def test_counts_doc_total_batch495(tmp_path):
    r = _run(tmp_path, "both")
    assert r["summary"]["counts"]["element_count_total"] == {
        "sum": 4, "participating_docs": 2}


def test_success_all_modes_batch495(tmp_path):
    for mode in ("both", "noann", "empty"):
        r = _run(tmp_path, mode)
        assert r["summary"]["success_rates"][
            "pipeline_success"] == {
            "success_count": 2, "total": 2, "rate": 1.0}


def test_devset_file_count_two_batch495(tmp_path):
    r = _run(tmp_path, "both")
    assert r["devset"] == {
        "status": "incomplete", "file_count": 2,
        "content_group_count": 2, "pdf_count": 2,
        "docx_count": 0, "categories_covered": []}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_counts_batch495():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("per_doc") == 12
    assert src.count("open(") == 2


# ---------- forbidden tokens 第七百五十一批 ----------

def test_source_no_eval_batch495():
    assert "eval(" not in _src()


def test_source_no_exec_batch495():
    assert "exec(" not in _src()


def test_source_no_compile_batch495():
    assert "compile(" not in _src()


def test_source_no_globals_batch495():
    assert "globals(" not in _src()


def test_source_no_locals_batch495():
    assert "locals(" not in _src()


def test_source_no_os_system_batch495():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch495():
    assert "subprocess" not in _src()


def test_source_no_popen_batch495():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch495():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch495():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch495():
    assert "socket" not in _src()


def test_source_no_requests_batch495():
    assert "requests" not in _src()


def test_source_no_urllib_batch495():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch495():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch495():
    assert "yield" not in _src()


def test_source_no_async_await_batch495():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch495():
    assert ".call(" not in _src()
