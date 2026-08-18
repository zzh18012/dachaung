"""evaluation/runner.py 第六百三十一轮 edges 测试（Round 1187）。

补强 edges198 未触及的角度（第五百五十九批，probe 实证）。

新角度（格图无文页的成功通道）：
- **零文本仍成功**——格 + 图、无任何 Tj →
  errors []（与 edges192 空内容失败通道成
  对照：pdf_no_text_extracted 只在零元素
  时触发，格元素在场即成功首锁）
- **元素序 [table, image]**——文本类（无）
  → 表 → 图，图 content None +
  resource_path 落盘（anyOf 通道）
- **唯一块是表 markdown**——空单元格
  "|  |  |\\n| --- | --- |" 成 isolated_
  table 块，图不产块
- **表内锚零预测界**——marker "---" 命中
  表 markdown 但单块 → P/F1
  no_predicted_boundaries / R 0.0
- **no_heading_elements**——零题文档的
  compliance reason 首锁
- forbidden tokens 第六百五十九批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _build_pdf(objects, n_obj) -> bytes:
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objects[num] + b"endobj\n")
    xref_pos = len(out)
    out += b"xref\n0 " + str(n_obj).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for num in range(1, n_obj):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size " + str(n_obj).encode()
            + b"/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


_PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
        b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
        b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')

_MD = "|  |  |\n| --- | --- |"


def _pdf() -> bytes:
    s = (b"1 w 0 G\n"
         b"10 300 100 50 re S\n60 300 0 50 re S\n"
         b"10 350 100 0 re S\n"
         b"q 30 0 0 30 50 100 cm /Im0 Do Q\n")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 400]"
            b"/Resources<</Font<</F1 5 0 R>>"
            b"/XObject<</Im0 6 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        6: (b"<</Type/XObject/Subtype/Image/Width 1/Height 1"
            b"/ColorSpace/DeviceRGB/BitsPerComponent 8/Length "
            + str(len(_PNG)).encode() + b">>stream\n" + _PNG
            + b"\nendstream "),
    }, 7)


def _board(tmp_path, doc_id, anchors=None):
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "a").mkdir(exist_ok=True)
    (tmp_path / "s" / f"{doc_id}.pdf").write_bytes(_pdf())
    docs = [{"doc_id": doc_id, "path": f"s/{doc_id}.pdf",
             "source_type": "pdf"}]
    if anchors is not None:
        (tmp_path / "a" / "a.json").write_text(json.dumps({
            "annotation_version": "1.0", "doc_id": doc_id,
            "chunk_boundary_anchors": anchors}),
            encoding="utf-8")
        docs[0]["annotation_file"] = "a/a.json"
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": docs}), encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 零文本仍成功 ----------

def test_no_text_succeeds_batch385(tmp_path):
    _board(tmp_path, "nt")
    doc, errors = process_single(
        tmp_path / "s" / "nt.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []


def test_no_text_elements_batch385(tmp_path):
    _board(tmp_path, "nt2")
    doc, errors = process_single(
        tmp_path / "s" / "nt2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == ["table", "image"]
    assert els[0]["content"] == _MD
    assert els[0]["source_locator"] == {
        "page": 1, "bbox": [10.0, 50.0, 110.0, 100.0]}
    assert els[1]["source_locator"] == {
        "page": 1, "bbox": [50.0, 270.0, 80.0, 300.0]}


def test_image_content_none_batch385(tmp_path):
    _board(tmp_path, "nt3")
    doc, errors = process_single(
        tmp_path / "s" / "nt3.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    img = doc.to_dict()["elements"][1]
    assert img["content"] is None
    assert img["resource_path"] is not None
    assert img["resource_path"].endswith(".png")


# ---------- 唯一块是表 markdown ----------

def test_no_text_chunks_batch385(tmp_path):
    _board(tmp_path, "nt4")
    doc, errors = process_single(
        tmp_path / "s" / "nt4.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert len(chunks) == 1
    assert chunks[0]["text"] == _MD
    assert chunks[0]["metadata"]["strategy"] == "isolated_table"
    assert len(chunks[0]["source_element_ids"]) == 1


# ---------- 表内锚零预测界 ----------

def test_table_anchor_zero_pred_batch385(tmp_path):
    r = run_evaluation(_board(tmp_path, "nt5", [
        {"marker": "---", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert m["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": None, "reason": "no_predicted_boundaries"}


# ---------- 指标 ----------

def test_no_text_by_type_batch385(tmp_path):
    r = run_evaluation(_board(tmp_path, "nt6"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"table": 1, "image": 1}, "reason": None}
    assert m["element_count_total"] == {
        "value": 2, "reason": None}


def test_no_text_ratios_batch385(tmp_path):
    r = run_evaluation(_board(tmp_path, "nt7"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}
    assert m["image_resource_exists_ratio"] == {"value": 1.0,
                                                "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["schema_valid"] == {"value": True, "reason": None}
    assert m["error_code"] == {"value": None, "reason": None}


def test_no_text_compliance_batch385(tmp_path):
    r = run_evaluation(_board(tmp_path, "nt8"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}


def test_no_text_multiset_batch385(tmp_path):
    r = run_evaluation(_board(tmp_path, "nt9"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}


def test_no_text_other_channels_batch385(tmp_path):
    r = run_evaluation(_board(tmp_path, "nt10"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["docx_locator_valid_ratio"] == {
        "value": None, "reason": "not_docx_document"}
    assert m["silent_drop_count"] == {
        "value": None, "reason": "no_expectations"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch385():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百五十九批 ----------

def test_source_no_eval_batch385():
    assert "eval(" not in _src()


def test_source_no_exec_batch385():
    assert "exec(" not in _src()


def test_source_no_compile_batch385():
    assert "compile(" not in _src()


def test_source_no_globals_batch385():
    assert "globals(" not in _src()


def test_source_no_locals_batch385():
    assert "locals(" not in _src()


def test_source_no_os_system_batch385():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch385():
    assert "subprocess" not in _src()


def test_source_no_popen_batch385():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch385():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch385():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch385():
    assert "socket" not in _src()


def test_source_no_requests_batch385():
    assert "requests" not in _src()


def test_source_no_urllib_batch385():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch385():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch385():
    assert "yield" not in _src()


def test_source_no_async_await_batch385():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch385():
    assert _src().count("open(") == 2
