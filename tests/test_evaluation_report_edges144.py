"""evaluation/report.py 第五百七十五轮 edges 测试（Round 1306）。

补强 edges143 未触及的角度（第六百七十八批，probe 实证）。

新角度（失败文档聚合排除面）：
- **比例排除**——好锚定 +
  坏 PDF → cbp {1/15, 1
  参与, 1 未评}；plvr/tpe
  同形 {1.0, 1, 1}（失败
  文档入 not_evaluated 而
  不入分母首锁）
- **双未评键**——
  docx_locator_valid_ratio
  与 image_resource_
  exists_ratio {None, 0, 2}
  （not_docx_document +
  no_image_elements 双因
  同计首锁）
- **12 键无 figure_caption**
  ——ratio_macro_averages
  恰 12 键；figure_caption_
  * 不入聚合（per-doc 专
  属首锁）
- **counts 排除**——ect
  {sum 2, participating 1}
  （失败文档 null 不入和）
- **sdt 排除**——双文档带
  expectations（好 heading:2
  → sdc 1；坏 heading:5 →
  null/pipeline_failed）→
  silent_drop_total 恰 1
  （失败文档期望不膨胀丢落
  首锁）
- forbidden tokens 第七百五十四批（open 0）
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
STREAM = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
          % ("A" * 80)
          + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
          % LONG).encode()


def _board(tmp_path, with_expectations):
    (tmp_path / "good.pdf").write_bytes(_wrap(STREAM))
    (tmp_path / "bad.pdf").write_bytes(b"not a pdf")
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "a.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "g1",
        "chunk_boundary_anchors": [
            {"marker": "Word3.", "position": "after"}]}),
        encoding="utf-8")
    g1 = {"doc_id": "g1", "path": "good.pdf",
          "source_type": "pdf",
          "annotation_file": "ann/a.json"}
    b1 = {"doc_id": "b1", "path": "bad.pdf",
          "source_type": "pdf"}
    if with_expectations:
        g1["expectations"] = {
            "element_count_by_type": {"heading": 2}}
        b1["expectations"] = {
            "element_count_by_type": {"heading": 5}}
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [g1, b1]}), encoding="utf-8")
    return load_manifest((tmp_path / "m.json"),
                         project_root=tmp_path)


def _run(tmp_path, with_exp=False):
    return run_evaluation(_board(tmp_path, with_exp),
                          tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=32)


# ---------- 比例排除 ----------

def test_cbp_exclusion_batch504(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["ratio_macro_averages"][
        "chunk_boundary_precision"] == {
        "macro_average": 1 / 15, "participating_docs": 1,
        "not_evaluated": 1}


def test_plvr_exclusion_batch504(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["ratio_macro_averages"][
        "pdf_locator_valid_ratio"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 1}


def test_tpe_exclusion_batch504(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["ratio_macro_averages"][
        "text_preservation_equal"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 1}


# ---------- 双未评键 ----------

def test_dlvr_double_not_evaluated_batch504(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["ratio_macro_averages"][
        "docx_locator_valid_ratio"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 2}


def test_irer_double_not_evaluated_batch504(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["ratio_macro_averages"][
        "image_resource_exists_ratio"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 2}


def test_two_not_evaluated_keys_only_batch504(
        tmp_path):
    r = _run(tmp_path)
    ne2 = {k for k, v in
           r["summary"]["ratio_macro_averages"].items()
           if v["not_evaluated"] == 2}
    assert ne2 == {"docx_locator_valid_ratio",
                   "image_resource_exists_ratio"}


# ---------- 12 键无 figure_caption ----------

def test_ratio_keys_twelve_batch504(tmp_path):
    r = _run(tmp_path)
    assert len(r["summary"]["ratio_macro_averages"]) \
        == 12


def test_figure_caption_not_aggregated_batch504(
        tmp_path):
    r = _run(tmp_path)
    assert "figure_caption_precision" not in \
        r["summary"]["ratio_macro_averages"]
    assert "figure_caption_f1" in \
        r["per_doc"][0]["metrics"]


# ---------- counts 排除 ----------

def test_counts_exclusion_batch504(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["counts"]["element_count_total"] \
        == {"sum": 2, "participating_docs": 1}


def test_success_half_batch504(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["success_rates"][
        "pipeline_success"] == {
        "success_count": 1, "total": 2, "rate": 0.5}


# ---------- sdt 排除 ----------

def test_silent_drop_total_excludes_failed_batch504(
        tmp_path):
    r = _run(tmp_path, with_exp=True)
    assert r["summary"]["silent_drop_total"] == 1


def test_g1_sdc_one_batch504(tmp_path):
    r = _run(tmp_path, with_exp=True)
    assert r["per_doc"][0]["metrics"][
        "silent_drop_count"] == {"value": 1,
                                 "reason": None}


def test_b1_sdc_null_batch504(tmp_path):
    r = _run(tmp_path, with_exp=True)
    assert r["per_doc"][1]["metrics"][
        "silent_drop_count"] == {
        "value": None, "reason": "pipeline_failed"}


# ---------- 报告合法性 ----------

def test_report_schema_batch504(tmp_path):
    validate(_run(tmp_path, with_exp=True),
             "evaluation-report.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch504():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src


# ---------- forbidden tokens 第七百五十四批 ----------

def test_source_no_eval_batch504():
    assert "eval(" not in _src()


def test_source_no_exec_batch504():
    assert "exec(" not in _src()


def test_source_no_compile_batch504():
    assert "compile(" not in _src()


def test_source_no_globals_batch504():
    assert "globals(" not in _src()


def test_source_no_locals_batch504():
    assert "locals(" not in _src()


def test_source_no_os_system_batch504():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch504():
    assert ".call(" not in _src()


def test_source_no_popen_batch504():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch504():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch504():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch504():
    assert "socket" not in _src()


def test_source_no_requests_batch504():
    assert "requests" not in _src()


def test_source_no_urllib_batch504():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch504():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch504():
    assert "yield" not in _src()


def test_source_no_async_await_batch504():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch504():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch504():
    assert _src().count("subprocess.run") == 2
