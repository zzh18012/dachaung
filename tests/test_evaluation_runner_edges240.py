"""evaluation/runner.py 第六百七十五轮 edges 测试（Round 1345）。

补强 edges239 未触及的角度（第七百一十七批，probe 实证）。

新角度（标注 doc_id 错配不核 / 标注文件缺失）：
- **doc_id 错配照常**
  ——annotation
  doc_id 'WRONG-ID'
  vs manifest g1 →
  cbp 照常 1/14 HIT
  （runner 不交叉
  核对 doc_id 首锁）
- **标注文件缺失**
  ——annotation_
  file 指向不存在
  文件 → cbp {None,
  no_annotation}
- **缺失不致败**——
  error None、
  pipeline_success
  True、schema_valid
  True（缺标注仅
  豁免不失败首锁）
- **双板对比**——
  好标注 HIT vs
  缺标注 null
- forbidden tokens 第七百八十七批（open 2）
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


def _run(tmp_path, ann_doc_id, ann_exists=True):
    (tmp_path / "c.pdf").write_bytes(_wrap(ONEP))
    (tmp_path / "ann").mkdir(exist_ok=True)
    if ann_exists:
        (tmp_path / "ann" / "a.json").write_text(
            json.dumps({
                "annotation_version": "1.0",
                "doc_id": ann_doc_id,
                "chunk_boundary_anchors": [
                    {"marker": "Word3.",
                     "position": "after"}]}),
            encoding="utf-8")
    else:
        ann_name = "ghost.json"
    ann_name = ann_name if not ann_exists \
        else "a.json"
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "g1", "path": "c.pdf",
             "source_type": "pdf",
             "annotation_file":
                 "ann/" + ann_name}]}),
        encoding="utf-8")
    mf = load_manifest(tmp_path / "m.json",
                       project_root=tmp_path)
    return run_evaluation(mf, tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=32)


# ---------- doc_id 错配照常 ----------

def test_mismatch_doc_id_hit_batch543(tmp_path):
    r = _run(tmp_path, "WRONG-ID")
    assert r["per_doc"][0]["metrics"][
        "chunk_boundary_precision"] == {
        "value": 1 / 14, "reason": None}


def test_mismatch_doc_id_cbr_batch543(tmp_path):
    r = _run(tmp_path, "WRONG-ID")
    assert r["per_doc"][0]["metrics"][
        "chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}


def test_match_doc_id_hit_batch543(tmp_path):
    r = _run(tmp_path, "g1")
    assert r["per_doc"][0]["metrics"][
        "chunk_boundary_precision"] == {
        "value": 1 / 14, "reason": None}


def test_mismatch_equals_match_batch543(tmp_path):
    wrong = _run(tmp_path, "WRONG-ID")
    right = _run(tmp_path, "g1")
    assert (wrong["per_doc"][0]["metrics"]
            ["chunk_boundary_precision"]
            == right["per_doc"][0]["metrics"]
            ["chunk_boundary_precision"])


# ---------- 标注文件缺失 ----------

def test_missing_ann_cbp_null_batch543(tmp_path):
    r = _run(tmp_path, "g1", ann_exists=False)
    assert r["per_doc"][0]["metrics"][
        "chunk_boundary_precision"] == {
        "value": None,
        "reason": "no_annotation"}


# ---------- 缺失不致败 ----------

def test_missing_ann_error_none_batch543(
        tmp_path):
    r = _run(tmp_path, "g1", ann_exists=False)
    assert r["per_doc"][0]["metrics"][
        "error_code"] == {"value": None,
                          "reason": None}


def test_missing_ann_success_true_batch543(
        tmp_path):
    r = _run(tmp_path, "g1", ann_exists=False)
    assert r["per_doc"][0]["metrics"][
        "pipeline_success"] == {"value": True,
                                "reason": None}


def test_missing_ann_schema_valid_batch543(
        tmp_path):
    r = _run(tmp_path, "g1", ann_exists=False)
    assert r["per_doc"][0]["metrics"][
        "schema_valid"] == {"value": True,
                            "reason": None}


def test_missing_ann_success_rate_batch543(
        tmp_path):
    r = _run(tmp_path, "g1", ann_exists=False)
    assert r["summary"]["success_rates"][
        "pipeline_success"] == {
        "success_count": 1, "total": 1,
        "rate": 1.0}


# ---------- 报告合法性 ----------

def test_report_schema_batch543(tmp_path):
    validate(_run(tmp_path, "g1",
                  ann_exists=False),
             "evaluation-report.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_counts_batch543():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("per_doc") == 12
    assert src.count("open(") == 2


# ---------- forbidden tokens 第七百八十七批 ----------

def test_source_no_eval_batch543():
    assert "eval(" not in _src()


def test_source_no_exec_batch543():
    assert "exec(" not in _src()


def test_source_no_compile_batch543():
    assert "compile(" not in _src()


def test_source_no_globals_batch543():
    assert "globals(" not in _src()


def test_source_no_locals_batch543():
    assert "locals(" not in _src()


def test_source_no_os_system_batch543():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch543():
    assert "subprocess" not in _src()


def test_source_no_popen_batch543():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch543():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch543():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch543():
    assert "socket" not in _src()


def test_source_no_requests_batch543():
    assert "requests" not in _src()


def test_source_no_urllib_batch543():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch543():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch543():
    assert "yield" not in _src()


def test_source_no_async_await_batch543():
    assert "async " not in _src()
    assert "await " not in _src()
