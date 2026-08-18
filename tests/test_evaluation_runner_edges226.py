"""evaluation/runner.py 第六百六十一轮 edges 测试（Round 1261）。

补强 edges225 未触及的角度（第六百三十三批，probe 实证）。

新角度（异类型文档板 / 选择性 hbc 参与）：
- **三文档不相交类型板**——figcap
  {caption:1} / hh80 {heading:1} /
  qq {paragraph:1}（ect 键集互不相
  交仍合计 count 首锁）
- **选择性 hbc 参与**——4 板中恰 2
  参与（hh80 + mix），2 排除（figcap
  /qq no_heading_elements）→
  {macro 1.0, participating 2,
  not_evaluated 2}（部分参与聚合首锁）
- **同页混排板**——单页三行 gap 40 →
  [caption, heading, paragraph]，
  caption 独块（isolated_caption）
  + heading+paragraph 合并块
  （sequential）srcs [1,2]
- forbidden tokens 第七百二十三批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


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


def _one(text: str) -> bytes:
    return _wrap(("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
                  % text).encode())


MIX_TEXTS = ["Figure 1 An overview diagram.", "A" * 80,
             "Is this a heading?"]


def _mix_pdf() -> bytes:
    ys = [700, 660, 620]
    s = "".join("BT /F1 12 Tf 10 %d Td (%s) Tj ET\n" % (y, t)
                for y, t in zip(ys, MIX_TEXTS)).encode()
    return _wrap(s)


def _board(tmp_path):
    (tmp_path / "figcap.pdf").write_bytes(
        _one("Figure 1 An overview diagram."))
    (tmp_path / "hh80.pdf").write_bytes(_one("A" * 80))
    (tmp_path / "qq.pdf").write_bytes(_one("Is this a heading?"))
    (tmp_path / "mix.pdf").write_bytes(_mix_pdf())
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "figcap", "path": "figcap.pdf",
             "source_type": "pdf"},
            {"doc_id": "hh80", "path": "hh80.pdf",
             "source_type": "pdf"},
            {"doc_id": "qq", "path": "qq.pdf",
             "source_type": "pdf"},
            {"doc_id": "mix", "path": "mix.pdf",
             "source_type": "pdf"}]}), encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


def _run(tmp_path):
    return run_evaluation(_board(tmp_path), tmp_path / "r.json",
                          parser_name="fallback", max_chars=200)


def _md(r, doc_id):
    return {p["doc_id"]: p["metrics"]
            for p in r["per_doc"]}[doc_id]


# ---------- 三文档不相交类型板 ----------

def test_figcap_ect_caption_batch459(tmp_path):
    assert _md(_run(tmp_path), "figcap")[
        "element_count_by_type"] == {
        "value": {"caption": 1}, "reason": None}


def test_hh80_ect_heading_batch459(tmp_path):
    assert _md(_run(tmp_path), "hh80")[
        "element_count_by_type"] == {
        "value": {"heading": 1}, "reason": None}


def test_qq_ect_paragraph_batch459(tmp_path):
    assert _md(_run(tmp_path), "qq")[
        "element_count_by_type"] == {
        "value": {"paragraph": 1}, "reason": None}


def test_figcap_qq_hbc_null_batch459(tmp_path):
    r = _run(tmp_path)
    assert _md(r, "figcap")["heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}
    assert _md(r, "qq")["heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}


def test_hh80_hbc_one_batch459(tmp_path):
    assert _md(_run(tmp_path), "hh80")[
        "heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


# ---------- 选择性 hbc 参与 ----------

def test_hbc_agg_selective_batch459(tmp_path):
    agg = _run(tmp_path)["summary"]["ratio_macro_averages"][
        "heading_boundary_compliance"]
    assert agg == {"macro_average": 1.0, "participating_docs": 2,
                   "not_evaluated": 2}


def test_counts_sum_six_batch459(tmp_path):
    assert _run(tmp_path)["summary"]["counts"] == {
        "element_count_total": {"sum": 6, "participating_docs": 4}}


def test_success_four_batch459(tmp_path):
    assert _run(tmp_path)["summary"]["success_rates"] == {
        "pipeline_success": {"success_count": 4, "total": 4,
                             "rate": 1.0}}


def test_cbp_no_annotation_all_batch459(tmp_path):
    r = _run(tmp_path)
    for p in r["per_doc"]:
        assert p["metrics"]["chunk_boundary_precision"] == {
            "value": None, "reason": "no_annotation"}


def test_locator_agg_all_four_batch459(tmp_path):
    agg = _run(tmp_path)["summary"]["ratio_macro_averages"][
        "pdf_locator_valid_ratio"]
    assert agg == {"macro_average": 1.0, "participating_docs": 4,
                   "not_evaluated": 0}


def test_tpe_agg_all_four_batch459(tmp_path):
    agg = _run(tmp_path)["summary"]["ratio_macro_averages"][
        "text_preservation_equal"]
    assert agg == {"macro_average": 1.0, "participating_docs": 4,
                   "not_evaluated": 0}


def test_intact_agg_all_four_batch459(tmp_path):
    agg = _run(tmp_path)["summary"]["ratio_macro_averages"][
        "chunk_reference_intact_ratio"]
    assert agg == {"macro_average": 1.0, "participating_docs": 4,
                   "not_evaluated": 0}


# ---------- 同页混排板 ----------

def _mix_doc(tmp_path):
    doc, errors = process_single(tmp_path / "mix.pdf",
                                 tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=200)
    assert errors == []
    return doc.to_dict()


def test_mix_types_batch459(tmp_path):
    _board(tmp_path)
    assert [e["type"] for e in _mix_doc(tmp_path)["elements"]] == [
        "caption", "heading", "paragraph"]


def test_mix_ect_three_batch459(tmp_path):
    m = _md(_run(tmp_path), "mix")
    assert m["element_count_by_type"] == {
        "value": {"caption": 1, "heading": 1, "paragraph": 1},
        "reason": None}
    assert m["element_count_total"] == {"value": 3, "reason": None}


def test_mix_chunk_count_two_batch459(tmp_path):
    _board(tmp_path)
    assert len(_mix_doc(tmp_path)["chunks"]) == 2


def test_mix_caption_solo_chunk_batch459(tmp_path):
    _board(tmp_path)
    c0 = _mix_doc(tmp_path)["chunks"][0]
    assert c0["text"] == "Figure 1 An overview diagram."
    assert c0["metadata"]["strategy"] == "isolated_caption"
    assert len(c0["source_element_ids"]) == 1


def test_mix_merged_tail_chunk_batch459(tmp_path):
    _board(tmp_path)
    c1 = _mix_doc(tmp_path)["chunks"][1]
    assert c1["text"] == "A" * 80 + " Is this a heading?"
    assert len(c1["text"]) == 99
    assert c1["metadata"]["strategy"] == "sequential"
    assert len(c1["source_element_ids"]) == 2


def test_mix_hbc_one_batch459(tmp_path):
    assert _md(_run(tmp_path), "mix")[
        "heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


def test_mix_locator_one_batch459(tmp_path):
    assert _md(_run(tmp_path), "mix")[
        "pdf_locator_valid_ratio"] == {"value": 1.0, "reason": None}


def test_mix_tpe_true_batch459(tmp_path):
    assert _md(_run(tmp_path), "mix")[
        "text_preservation_equal"] == {"value": True, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch459():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第七百二十三批 ----------

def test_source_no_eval_batch459():
    assert "eval(" not in _src()


def test_source_no_exec_batch459():
    assert "exec(" not in _src()


def test_source_no_compile_batch459():
    assert "compile(" not in _src()


def test_source_no_globals_batch459():
    assert "globals(" not in _src()


def test_source_no_locals_batch459():
    assert "locals(" not in _src()


def test_source_no_os_system_batch459():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch459():
    assert "subprocess" not in _src()


def test_source_no_popen_batch459():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch459():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch459():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch459():
    assert "socket" not in _src()


def test_source_no_requests_batch459():
    assert "requests" not in _src()


def test_source_no_urllib_batch459():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch459():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch459():
    assert "yield" not in _src()


def test_source_no_async_await_batch459():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch459():
    assert _src().count("open(") == 2
