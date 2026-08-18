"""evaluation/report.py 第五百六十六轮 edges 测试（Round 1248）。

补强 edges134 未触及的角度（第六百二十批，probe 实证）。

新角度（双无标题 PDF 板零参评聚合全像）：
- **hbc 零参评**——两文档均无 heading
  → {macro None, participating 0,
  not_evaluated 2}（键不消失，与
  edges134 混合板 {1.0, 1, 1} 成对照）
- **四种 null reason 同板**——
  no_heading_elements /
  no_annotation / no_image_elements /
  not_docx_document（单板四源 null
  首锁）
- **零参评下 12 ratio 键仍在**——键
  集不随参评收缩
- **figure_caption 键 per-doc 缺席**
  ——metrics dict 无此键（非 null）
- forbidden tokens 第七百一十二批（open 0）
"""

from __future__ import annotations

import inspect
import json

import evaluation.report as report_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


def _pdf(y2: int) -> bytes:
    s = (("BT /F1 12 Tf 10 700 Td (Top line text here.) Tj ET\n"
          "BT /F1 12 Tf 10 %d Td (Lower line text here.) Tj ET\n"
          % y2).encode())
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: (b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"),
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


def _report(tmp_path):
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "s" / "g30.pdf").write_bytes(_pdf(670))
    (tmp_path / "s" / "g31.pdf").write_bytes(_pdf(669))
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "g30", "path": "s/g30.pdf",
             "source_type": "pdf"},
            {"doc_id": "g31", "path": "s/g31.pdf",
             "source_type": "pdf"}]}), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    return run_evaluation(m, tmp_path / "r.json",
                          parser_name="fallback", max_chars=200)


def _summary(tmp_path):
    return _report(tmp_path)["summary"]


# ---------- 零参评 ratio 条目 ----------

def test_hbc_zero_participation_batch446(tmp_path):
    s = _summary(tmp_path)
    assert s["ratio_macro_averages"]["heading_boundary_compliance"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 2}


def test_chunk_boundary_f1_zero_part_batch446(tmp_path):
    s = _summary(tmp_path)
    assert s["ratio_macro_averages"]["chunk_boundary_f1"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 2}


def test_docx_locator_zero_part_batch446(tmp_path):
    s = _summary(tmp_path)
    assert s["ratio_macro_averages"]["docx_locator_valid_ratio"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 2}


def test_image_ratio_zero_part_batch446(tmp_path):
    s = _summary(tmp_path)
    assert s["ratio_macro_averages"]["image_resource_exists_ratio"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 2}


def test_pdf_locator_full_part_batch446(tmp_path):
    s = _summary(tmp_path)
    assert s["ratio_macro_averages"]["pdf_locator_valid_ratio"] == {
        "macro_average": 1.0, "participating_docs": 2,
        "not_evaluated": 0}


def test_tpe_full_part_batch446(tmp_path):
    s = _summary(tmp_path)
    assert s["ratio_macro_averages"]["text_preservation_equal"] == {
        "macro_average": 1.0, "participating_docs": 2,
        "not_evaluated": 0}


# ---------- 零参评下键集不收缩 ----------

def test_ratio_keys_still_twelve_batch446(tmp_path):
    s = _summary(tmp_path)
    assert sorted(s["ratio_macro_averages"].keys()) == [
        "chunk_boundary_f1", "chunk_boundary_precision",
        "chunk_boundary_recall", "chunk_reference_intact_ratio",
        "docx_locator_valid_ratio", "heading_boundary_compliance",
        "image_resource_exists_ratio", "pdf_locator_valid_ratio",
        "schema_valid", "text_char_multiset_precision",
        "text_char_multiset_recall", "text_preservation_equal"]


# ---------- per-doc 四种 null reason ----------

def test_per_doc_no_heading_reason_batch446(tmp_path):
    r = _report(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}


def test_per_doc_no_annotation_reason_batch446(tmp_path):
    r = _report(tmp_path)
    assert r["per_doc"][0]["metrics"]["chunk_boundary_f1"] == {
        "value": None, "reason": "no_annotation"}


def test_per_doc_no_image_reason_batch446(tmp_path):
    r = _report(tmp_path)
    assert r["per_doc"][0]["metrics"]["image_resource_exists_ratio"] == {
        "value": None, "reason": "no_image_elements"}


def test_per_doc_not_docx_reason_batch446(tmp_path):
    r = _report(tmp_path)
    assert r["per_doc"][0]["metrics"][
        "docx_locator_valid_ratio"] == {
        "value": None, "reason": "not_docx_document"}


def test_figure_family_asymmetry_per_doc_batch446(tmp_path):
    r = _report(tmp_path)
    md = r["per_doc"][0]["metrics"]
    assert "figure_caption_attachment_rate" not in md
    for k in ("figure_caption_precision",
              "figure_caption_recall", "figure_caption_f1"):
        assert md[k] == {
            "value": None,
            "reason": "parser_does_not_emit_relations"}


# ---------- counts / success ----------

def test_counts_sum_three_part_two_batch446(tmp_path):
    s = _summary(tmp_path)
    assert s["counts"]["element_count_total"] == {
        "sum": 3, "participating_docs": 2}


def test_success_two_of_two_batch446(tmp_path):
    s = _summary(tmp_path)
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 2, "total": 2, "rate": 1.0}


def test_silent_drop_none_batch446(tmp_path):
    s = _summary(tmp_path)
    assert s["silent_drop_total"] is None


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch446():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src


# ---------- forbidden tokens 第七百一十二批 ----------

def test_source_no_eval_batch446():
    assert "eval(" not in _src()


def test_source_no_exec_batch446():
    assert "exec(" not in _src()


def test_source_no_compile_batch446():
    assert "compile(" not in _src()


def test_source_no_globals_batch446():
    assert "globals(" not in _src()


def test_source_no_locals_batch446():
    assert "locals(" not in _src()


def test_source_no_os_system_batch446():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch446():
    assert ".call(" not in _src()


def test_source_no_popen_batch446():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch446():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch446():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch446():
    assert "socket" not in _src()


def test_source_no_requests_batch446():
    assert "requests" not in _src()


def test_source_no_urllib_batch446():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch446():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch446():
    assert "yield" not in _src()


def test_source_no_async_await_batch446():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch446():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch446():
    assert _src().count("subprocess.run") == 2
