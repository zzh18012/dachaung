"""evaluation/runner.py 第六百七十二轮 edges 测试（Round 1327）。

补强 edges236 未触及的角度（第六百九十九批，probe 实证）。

新角度（metrics 全键枚举 / 富标注透传 / 重复 doc_id）：
- **metrics 恰 20 键**——
  per_doc[0].metrics
  完整键集首锁
  （figure_caption_*
  / error_code /
  pipeline_success 等
  全列）
- **figure_caption 三 null**
  ——标注含
  figure_caption_pairs
  实对 → 运行时仍
  {None,
  parser_does_not_
  emit_relations}
  （runner 级三键首锁）
- **heading_order 零消费**
  ——标注含
  heading_order +
  pairs → cbp 照常
  1/15 HIT
- **重复 doc_id 接受**
  ——manifest 两条
  同 doc_id g1 →
  加载成功、per_doc
  2 条均 g1、file_count
  2（不去重首锁）
- **重复板聚合**——
  counts sum 4 /
  success 2/2 /
  devset file_count 2
- **dependencies 锁**
  ——{pdfplumber:
  0.11.10,
  python-docx:1.2.0,
  pypdfium2:5.12.1}
- forbidden tokens 第七百七十二批（open 2）
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
COMBO = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
         % ("A" * 80)
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()

METRICS_20 = {
    "chunk_boundary_f1", "chunk_boundary_precision",
    "chunk_boundary_recall",
    "chunk_reference_intact_ratio",
    "docx_locator_valid_ratio",
    "element_count_by_type", "element_count_total",
    "error_code", "figure_caption_f1",
    "figure_caption_precision",
    "figure_caption_recall",
    "heading_boundary_compliance",
    "image_resource_exists_ratio",
    "pdf_locator_valid_ratio", "pipeline_success",
    "schema_valid", "silent_drop_count",
    "text_char_multiset_precision",
    "text_char_multiset_recall",
    "text_preservation_equal"}


def _rich(tmp_path):
    (tmp_path / "c.pdf").write_bytes(_wrap(COMBO))
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "a.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "g1",
        "heading_order": [{"level": 1, "text": "H"}],
        "figure_caption_pairs": [
            {"figure_marker": "f",
             "caption_text": "c"}],
        "chunk_boundary_anchors": [
            {"marker": "Word3.",
             "position": "after"}]}),
        encoding="utf-8")
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "g1", "path": "c.pdf",
             "source_type": "pdf",
             "annotation_file": "ann/a.json"}]}),
        encoding="utf-8")
    return load_manifest((tmp_path / "m.json"),
                         project_root=tmp_path)


def _rich_run(tmp_path):
    return run_evaluation(_rich(tmp_path),
                          tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=32)


def _dup_run(tmp_path):
    (tmp_path / "c.pdf").write_bytes(_wrap(COMBO))
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "g1", "path": "c.pdf",
             "source_type": "pdf"},
            {"doc_id": "g1", "path": "c.pdf",
             "source_type": "pdf"}]}),
        encoding="utf-8")
    mf = load_manifest((tmp_path / "m.json"),
                       project_root=tmp_path)
    return run_evaluation(mf, tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=32)


# ---------- metrics 恰 20 键 ----------

def test_metrics_twenty_keys_batch525(tmp_path):
    r = _rich_run(tmp_path)
    assert set(r["per_doc"][0]["metrics"]) == \
        METRICS_20


def test_metrics_key_count_twenty_batch525(tmp_path):
    r = _rich_run(tmp_path)
    assert len(r["per_doc"][0]["metrics"]) == 20


# ---------- figure_caption 三 null ----------

def test_figure_caption_trio_null_batch525(tmp_path):
    r = _rich_run(tmp_path)
    m = r["per_doc"][0]["metrics"]
    for k in ("figure_caption_precision",
              "figure_caption_recall",
              "figure_caption_f1"):
        assert m[k] == {
            "value": None,
            "reason":
                "parser_does_not_emit_relations"}


# ---------- heading_order 零消费 ----------

def test_heading_order_ignored_cbp_batch525(tmp_path):
    r = _rich_run(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "chunk_boundary_precision"] == {
        "value": 1 / 15, "reason": None}


def test_rich_annotation_success_batch525(tmp_path):
    r = _rich_run(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "pipeline_success"] == {"value": True,
                                "reason": None}


# ---------- 重复 doc_id 接受 ----------

def test_dup_doc_id_loaded_batch525(tmp_path):
    r = _dup_run(tmp_path)
    assert len(r["per_doc"]) == 2


def test_dup_doc_id_both_entries_batch525(tmp_path):
    r = _dup_run(tmp_path)
    assert [p["doc_id"] for p in r["per_doc"]] == [
        "g1", "g1"]


def test_dup_counts_sum_four_batch525(tmp_path):
    r = _dup_run(tmp_path)
    assert r["summary"]["counts"][
        "element_count_total"] == {
        "sum": 4, "participating_docs": 2}


def test_dup_success_two_halves_batch525(tmp_path):
    r = _dup_run(tmp_path)
    assert r["summary"]["success_rates"][
        "pipeline_success"] == {
        "success_count": 2, "total": 2,
        "rate": 1.0}


def test_dup_devset_file_count_batch525(tmp_path):
    r = _dup_run(tmp_path)
    assert r["devset"]["file_count"] == 2


def test_dup_report_schema_valid_batch525(tmp_path):
    validate(_dup_run(tmp_path),
             "evaluation-report.schema.json")


# ---------- dependencies 锁 ----------

def test_dependencies_versions_batch525(tmp_path):
    r = _rich_run(tmp_path)
    assert r["provenance"]["dependencies"] == {
        "pdfplumber": "0.11.10",
        "python-docx": "1.2.0",
        "pypdfium2": "5.12.1"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_counts_batch525():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("per_doc") == 12
    assert src.count("open(") == 2


# ---------- forbidden tokens 第七百七十二批 ----------

def test_source_no_eval_batch525():
    assert "eval(" not in _src()


def test_source_no_exec_batch525():
    assert "exec(" not in _src()


def test_source_no_compile_batch525():
    assert "compile(" not in _src()


def test_source_no_globals_batch525():
    assert "globals(" not in _src()


def test_source_no_locals_batch525():
    assert "locals(" not in _src()


def test_source_no_os_system_batch525():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch525():
    assert "subprocess" not in _src()


def test_source_no_popen_batch525():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch525():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch525():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch525():
    assert "socket" not in _src()


def test_source_no_requests_batch525():
    assert "requests" not in _src()


def test_source_no_urllib_batch525():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch525():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch525():
    assert "yield" not in _src()


def test_source_no_async_await_batch525():
    assert "async " not in _src()
    assert "await " not in _src()
