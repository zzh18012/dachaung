"""evaluation/runner.py 第六百四十七轮 edges 测试（Round 1203）。

补强 edges211 未触及的角度（第五百七十五批，probe 实证）。

新角度（横线不成表 / 同基线混字号顶部序）：
- **横线不成表**——两条全宽横线（无竖线）
  夹的文字不成 table，走 short_line
  heading（表检测需列结构首锁）
- **题向后阻断向前合**——[段独行, 题+段
  合流 49 字 2 源]，mc200 仍 2 块（阻
  断与预算无关）
- **同基线混字号**——12pt "Hello " 与
  24pt "World" 同基线 → 行内字符按字
  形顶排序："World Hello"（大字顶更高
  先排，x 序让位首锁）；行成 heading
- **单块 null 锚**——混合板单 chunk →
  锚全走 no_predicted_boundaries
- forbidden tokens 第六百七十四批（open 2）
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


def _T(text, x, y) -> bytes:
    return ("BT /F1 12 Tf %d %d Td (%s) Tj ET\n"
            % (x, y, text)).encode()


_HR_A = "Paragraph above the ruled band."
_HR_H = "Cell one content"
_HR_B = "Paragraph below the ruled band."


def _hr_pdf() -> bytes:
    s = (_T(_HR_A, 10, 400)
         + b"1 w 0 G\n"
         + b"10 310 190 0 re S\n"
         + b"10 280 190 0 re S\n"
         + _T(_HR_H, 15, 290)
         + _T(_HR_B, 10, 200))
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 6)


def _mf_pdf() -> bytes:
    s = (b"BT /F1 12 Tf 10 700 Td (Hello ) Tj ET\n"
         b"BT /F2 24 Tf 60 700 Td (World) Tj ET\n"
         b"BT /F1 12 Tf 10 650 Td "
         b"(Small after big same-page line.) Tj ET\n")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R/F2 6 0 R>>>>"
            b"/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        6: b"<</Type/Font/Subtype/Type1/BaseFont/Times-Bold>>",
    }, 7)


def _board(tmp_path, doc_id, mode, anchors=None):
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "a").mkdir(exist_ok=True)
    pdf = _hr_pdf() if mode == "hr" else _mf_pdf()
    (tmp_path / "s" / f"{doc_id}.pdf").write_bytes(pdf)
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


def _pdf(tmp_path, doc_id, mode):
    pdf = _hr_pdf() if mode == "hr" else _mf_pdf()
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "s" / f"{doc_id}.pdf").write_bytes(pdf)
    return tmp_path / "s" / f"{doc_id}.pdf"


# ---------- 横线不成表 ----------

def test_hr_no_table_batch401(tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path, "nt", "hr"), tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == [
        "paragraph", "heading", "paragraph"]
    assert [e["content"] for e in els] == [_HR_A, _HR_H, _HR_B]


def test_hr_heading_meta_batch401(tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path, "hm", "hr"), tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert els[1]["metadata"] == {
        "level": 0, "heuristic": "short_line"}


def test_hr_chunks_batch401(tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path, "hc", "hr"), tmp_path / "o.json",
        parser_name="fallback", max_chars=50)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert [c["text"] for c in chunks] == [
        _HR_A, _HR_H + " " + _HR_B]
    assert [len(c["source_element_ids"]) for c in chunks] == [1, 2]
    assert all(c["metadata"]["strategy"] == "sequential"
               for c in chunks)


def test_hr_chunks_mc200_batch401(tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path, "h2", "hr"), tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert [c["text"] for c in chunks] == [
        _HR_A, _HR_H + " " + _HR_B]
    assert [len(c["text"]) for c in chunks] == [31, 48]


# ---------- 同基线混字号 ----------

def test_mixed_font_order_batch401(tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path, "mo", "mf"), tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == ["heading", "paragraph"]
    assert els[0]["content"] == "World Hello"
    assert els[1]["content"] == "Small after big same-page line."


def test_mixed_font_bbox_batch401(tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path, "mb", "mf"), tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert els[0]["source_locator"] == {
        "page": 1,
        "bbox": [10.0, 81.20799999999997, 126.672,
                 105.20799999999997]}
    assert els[0]["metadata"] == {
        "level": 0, "heuristic": "short_line"}


def test_mixed_font_chunks_batch401(tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path, "mc", "mf"), tmp_path / "o.json",
        parser_name="fallback", max_chars=50)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert [c["text"] for c in chunks] == [
        "World Hello Small after big same-page line."]
    assert len(chunks[0]["source_element_ids"]) == 2


# ---------- 锚 ----------

def test_hr_anchor_band_batch401(tmp_path):
    r = run_evaluation(_board(tmp_path, "a1", "hr", [
        {"marker": "band.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_hr_anchor_content_batch401(tmp_path):
    r = run_evaluation(_board(tmp_path, "a2", "hr", [
        {"marker": "content", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_hr_anchor_dup_batch401(tmp_path):
    r = run_evaluation(_board(tmp_path, "a3", "hr", [
        {"marker": "band.", "position": "after"},
        {"marker": "band.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


def test_mixed_anchor_null_batch401(tmp_path):
    r = run_evaluation(_board(tmp_path, "a4", "mf", [
        {"marker": "Hello", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert m["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": None, "reason": "no_predicted_boundaries"}


def test_mixed_anchor_line_batch401(tmp_path):
    r = run_evaluation(_board(tmp_path, "a5", "mf", [
        {"marker": "line.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert m["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}


# ---------- 指标 ----------

def test_hr_metrics_batch401(tmp_path):
    r = run_evaluation(_board(tmp_path, "mx", "hr"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 2, "heading": 1}, "reason": None}
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


def test_mixed_metrics_batch401(tmp_path):
    r = run_evaluation(_board(tmp_path, "mm", "mf"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "paragraph": 1}, "reason": None}
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch401():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百七十四批 ----------

def test_source_no_eval_batch401():
    assert "eval(" not in _src()


def test_source_no_exec_batch401():
    assert "exec(" not in _src()


def test_source_no_compile_batch401():
    assert "compile(" not in _src()


def test_source_no_globals_batch401():
    assert "globals(" not in _src()


def test_source_no_locals_batch401():
    assert "locals(" not in _src()


def test_source_no_os_system_batch401():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch401():
    assert "subprocess" not in _src()


def test_source_no_popen_batch401():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch401():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch401():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch401():
    assert "socket" not in _src()


def test_source_no_requests_batch401():
    assert "requests" not in _src()


def test_source_no_urllib_batch401():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch401():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch401():
    assert "yield" not in _src()


def test_source_no_async_await_batch401():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch401():
    assert _src().count("open(") == 2
