"""evaluation/runner.py 第六百四十五轮 edges 测试（Round 1201）。

补强 edges210 未触及的角度（第五百七十三批，probe 实证）。

新角度（同位双图 / 图不阻断合流）：
- **同位双图不去重**——两 image XObject
  画在同一 cm 矩形 → 两个独立 image
  元素、bbox 完全相同、资源双份
  （_p1_00.png / _p1_01.png）
- **y 夹图仍殿后**——图在两段文本之间
  （y 650）但元素序 [段, 段, 图, 图]，
  图类整体排在页内全部文本之后
- **图不阻断合流**——元素序被图隔开的两
  段仍合一块（2 源）；与表阻断成对照
- **近界锚全容差**——流长 57，任意 marker
  距界 ≤ 28 < 30 → 全 1.0；重复 marker
  一对一 → R 0.5
- forbidden tokens 第六百七十三批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


_PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
        b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
        b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')


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


def _img() -> bytes:
    return (b"<</Type/XObject/Subtype/Image/Width 1/Height 1"
            b"/ColorSpace/DeviceRGB/BitsPerComponent 8/Length "
            + str(len(_PNG)).encode()
            + b">>stream\n" + _PNG + b"\nendstream ")


_TOP = "Above the picture text line."
_BOT = "Below the picture text line."


def _pdf() -> bytes:
    s = (_T(_TOP, 10, 720)
         + b"q 30 0 0 30 50 650 cm /Im1 Do Q\n"
         + _T(_BOT, 10, 600)
         + b"q 30 0 0 30 50 650 cm /Im2 Do Q\n")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 7 0 R>>"
            b"/XObject<</Im1 5 0 R/Im2 6 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: _img(),
        6: _img(),
        7: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 8)


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


# ---------- 同位双图 ----------

def test_dup_image_order_batch399(tmp_path):
    _board(tmp_path, "do")
    doc, errors = process_single(
        tmp_path / "s" / "do.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == [
        "paragraph", "paragraph", "image", "image"]
    assert [e["content"] for e in els[:2]] == [_TOP, _BOT]
    assert els[2]["content"] is None
    assert els[3]["content"] is None


def test_dup_image_identical_bbox_batch399(tmp_path):
    _board(tmp_path, "db")
    doc, errors = process_single(
        tmp_path / "s" / "db.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    want = {"page": 1, "bbox": [50.0, 120.0, 80.0, 150.0]}
    assert els[2]["source_locator"] == want
    assert els[3]["source_locator"] == want


def test_dup_image_resources_batch399(tmp_path):
    _board(tmp_path, "dr")
    doc, errors = process_single(
        tmp_path / "s" / "dr.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    paths = [e["resource_path"] for e in els[2:]]
    assert len(paths) == 2 and paths[0] != paths[1]
    assert paths[0].endswith("_p1_00.png")
    assert paths[1].endswith("_p1_01.png")
    for p in paths:
        from pathlib import Path
        assert Path(p).parent.name.startswith("images-")
        assert Path(p).is_file()


# ---------- 图不阻断合流 ----------

def test_image_no_interrupt_merge_batch399(tmp_path):
    _board(tmp_path, "nm")
    doc, errors = process_single(
        tmp_path / "s" / "nm.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=60)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert [c["text"] for c in chunks] == [_TOP + " " + _BOT]
    assert len(chunks[0]["source_element_ids"]) == 2


def test_image_split_chunks_batch399(tmp_path):
    _board(tmp_path, "sc")
    doc, errors = process_single(
        tmp_path / "s" / "sc.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=50)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert [c["text"] for c in chunks] == [_TOP, _BOT]
    assert [len(c["text"]) for c in chunks] == [28, 28]
    assert all(c["metadata"]["strategy"] == "sequential"
               for c in chunks)
    assert all(len(c["source_element_ids"]) == 1
               for c in chunks)


def test_images_never_in_chunks_batch399(tmp_path):
    _board(tmp_path, "nv")
    doc, errors = process_single(
        tmp_path / "s" / "nv.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=50)
    assert errors == []
    d = doc.to_dict()
    used = {sid for c in d["chunks"]
            for sid in c["source_element_ids"]}
    img_ids = [e["element_id"] for e in d["elements"]
               if e["type"] == "image"]
    assert len(img_ids) == 2
    assert all(i not in used for i in img_ids)


# ---------- 锚 ----------

def test_line_anchor_batch399(tmp_path):
    r = run_evaluation(_board(tmp_path, "a1", [
        {"marker": "line.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_line_twice_batch399(tmp_path):
    r = run_evaluation(_board(tmp_path, "a2", [
        {"marker": "line.", "position": "after"},
        {"marker": "line.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


def test_picture_anchor_batch399(tmp_path):
    r = run_evaluation(_board(tmp_path, "a3", [
        {"marker": "picture", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_both_near_order1_batch399(tmp_path):
    r = run_evaluation(_board(tmp_path, "a4", [
        {"marker": "picture", "position": "after"},
        {"marker": "line.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


def test_both_near_order2_batch399(tmp_path):
    r = run_evaluation(_board(tmp_path, "a5", [
        {"marker": "line.", "position": "after"},
        {"marker": "picture", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


# ---------- 指标 ----------

def test_metrics_by_type_batch399(tmp_path):
    r = run_evaluation(_board(tmp_path, "mx"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 2, "image": 2}, "reason": None}
    assert m["heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}


def test_metrics_ratios_batch399(tmp_path):
    r = run_evaluation(_board(tmp_path, "mr"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["figure_caption_precision"] == {
        "value": None,
        "reason": "parser_does_not_emit_relations"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch399():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百七十三批 ----------

def test_source_no_eval_batch399():
    assert "eval(" not in _src()


def test_source_no_exec_batch399():
    assert "exec(" not in _src()


def test_source_no_compile_batch399():
    assert "compile(" not in _src()


def test_source_no_globals_batch399():
    assert "globals(" not in _src()


def test_source_no_locals_batch399():
    assert "locals(" not in _src()


def test_source_no_os_system_batch399():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch399():
    assert "subprocess" not in _src()


def test_source_no_popen_batch399():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch399():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch399():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch399():
    assert "socket" not in _src()


def test_source_no_requests_batch399():
    assert "requests" not in _src()


def test_source_no_urllib_batch399():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch399():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch399():
    assert "yield" not in _src()


def test_source_no_async_await_batch399():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch399():
    assert _src().count("open(") == 2
