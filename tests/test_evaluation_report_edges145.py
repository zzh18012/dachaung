"""evaluation/report.py 第五百七十六轮 edges 测试（Round 1312）。

补强 edges144 未触及的角度（第六百八十四批，probe 实证）。

新角度（无标题 hbc 聚合排除 / 跨文档 sdt 求和）：
- **hbc 半参与**——双
  标题板（hbc 1.0）+
  无标题板（hbc None/
  no_heading_elements）
  → {1.0, 1 参与, 1
  未评}（no_heading
  入 not_evaluated
  首锁）
- **ne1 恰一键**——
  not_evaluated==1
  的键集恰
  {heading_boundary_
  compliance}
- **ne2 五键**——cbp/
  cbr/cbf（双无标注）
  + dlvr/irer（双非
  docx/无图）
- **sdt 跨文档求和**
  ——d1 heading:3→1
  + d2 paragraph:2→1
  → silent_drop_total
  恰 2（双好文档正落
  求和面首锁，区别
  edges144 排除面）
- **全绿聚合**——
  tpe/plvr/crir/tcmp
  均 {1.0, 2, 0}
- **counts 双参与**
  ——{sum 4, 2}（3+1
  异构仍同和）
- **success 满员**
  ——{2, 2, 1.0}
- forbidden tokens 第七百五十九批（open 0）
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
STREAM_2H = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
             % ("A" * 80)
             + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
             % ("B" * 80)
             + "BT /F1 12 Tf 10 620 Td (%s) Tj ET\n"
             % LONG).encode()
STREAM_1P = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
             % LONG).encode()


def _run(tmp_path):
    (tmp_path / "h.pdf").write_bytes(_wrap(STREAM_2H))
    (tmp_path / "p.pdf").write_bytes(_wrap(STREAM_1P))
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "h.pdf",
             "source_type": "pdf",
             "expectations": {
                 "element_count_by_type": {"heading": 3}}},
            {"doc_id": "d2", "path": "p.pdf",
             "source_type": "pdf",
             "expectations": {
                 "element_count_by_type": {
                     "paragraph": 2}}}]}),
        encoding="utf-8")
    mf = load_manifest((tmp_path / "m.json"),
                       project_root=tmp_path)
    return run_evaluation(mf, tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=32)


# ---------- hbc 半参与 ----------

def test_hbc_half_participation_batch510(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["ratio_macro_averages"][
        "heading_boundary_compliance"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 1}


def test_hbc_d2_null_reason_batch510(tmp_path):
    r = _run(tmp_path)
    assert r["per_doc"][1]["metrics"][
        "heading_boundary_compliance"] == {
        "value": None,
        "reason": "no_heading_elements"}


def test_hbc_d1_one_batch510(tmp_path):
    r = _run(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


# ---------- ne1 / ne2 键集 ----------

def test_ne1_only_hbc_batch510(tmp_path):
    r = _run(tmp_path)
    rma = r["summary"]["ratio_macro_averages"]
    ne1 = {k for k, v in rma.items()
           if v["not_evaluated"] == 1}
    assert ne1 == {"heading_boundary_compliance"}


def test_ne2_five_keys_batch510(tmp_path):
    r = _run(tmp_path)
    rma = r["summary"]["ratio_macro_averages"]
    ne2 = {k for k, v in rma.items()
           if v["not_evaluated"] == 2}
    assert ne2 == {"chunk_boundary_precision",
                   "chunk_boundary_recall",
                   "chunk_boundary_f1",
                   "docx_locator_valid_ratio",
                   "image_resource_exists_ratio"}


def test_cbp_double_not_evaluated_batch510(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["ratio_macro_averages"][
        "chunk_boundary_precision"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 2}


# ---------- sdt 跨文档求和 ----------

def test_sdt_sum_two_batch510(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["silent_drop_total"] == 2


def test_sdc_per_doc_one_each_batch510(tmp_path):
    r = _run(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "silent_drop_count"] == {"value": 1,
                                 "reason": None}
    assert r["per_doc"][1]["metrics"][
        "silent_drop_count"] == {"value": 1,
                                 "reason": None}


# ---------- 全绿聚合 ----------

def test_allgreen_participation_two_batch510(
        tmp_path):
    r = _run(tmp_path)
    rma = r["summary"]["ratio_macro_averages"]
    for key in ("text_preservation_equal",
                "pdf_locator_valid_ratio",
                "chunk_reference_intact_ratio",
                "text_char_multiset_precision"):
        assert rma[key] == {"macro_average": 1.0,
                            "participating_docs": 2,
                            "not_evaluated": 0}


# ---------- counts / success ----------

def test_counts_hetero_sum_batch510(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["counts"][
        "element_count_total"] == {
        "sum": 4, "participating_docs": 2}


def test_success_full_batch510(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["success_rates"][
        "pipeline_success"] == {
        "success_count": 2, "total": 2, "rate": 1.0}


def test_ratio_keys_twelve_batch510(tmp_path):
    r = _run(tmp_path)
    assert len(r["summary"][
        "ratio_macro_averages"]) == 12


# ---------- 报告合法性 ----------

def test_report_schema_batch510(tmp_path):
    validate(_run(tmp_path),
             "evaluation-report.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch510():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src


# ---------- forbidden tokens 第七百五十九批 ----------

def test_source_no_eval_batch510():
    assert "eval(" not in _src()


def test_source_no_exec_batch510():
    assert "exec(" not in _src()


def test_source_no_compile_batch510():
    assert "compile(" not in _src()


def test_source_no_globals_batch510():
    assert "globals(" not in _src()


def test_source_no_locals_batch510():
    assert "locals(" not in _src()


def test_source_no_os_system_batch510():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch510():
    assert ".call(" not in _src()


def test_source_no_popen_batch510():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch510():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch510():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch510():
    assert "socket" not in _src()


def test_source_no_requests_batch510():
    assert "requests" not in _src()


def test_source_no_urllib_batch510():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch510():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch510():
    assert "yield" not in _src()


def test_source_no_async_await_batch510():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch510():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch510():
    assert _src().count("subprocess.run") == 2
