"""evaluation/runner.py 第六百一十二轮 edges 测试（Round 1168）。

补强 edges182 未触及的角度（第五百四十批，probe 实证）。

新角度（同页双图绘制序 / 零预测界）：
- **双图绘制序**——/Im0（页面上部）与 /Im1（页面
  下部）同页：元素序 = 内容流绘制序，与垂直位置
  无关（高先画→Im0 先列；低先画→Im1 先列，首锁
  ——与文本元素按 y 序成对照）
- **双图无块**——两 image 均不产 chunk；唯一
  sequential 块 1 源，两图 id 均不入 sources
- **image_resource 双图 1.0**——by_type {paragraph:
  1, image: 2}，资源存在率双图齐活
- **零预测界**——单 chunk 文档（N-1=0 预测界）
  挂锚 → P/F1 null + reason=no_predicted_
  boundaries，R 仍 0.0（首锁：P/F1 分母为 0
  走 null 通道而 R 分母是 GT 数）
- forbidden tokens 第六百四十批（open 2）
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


def _img_obj() -> bytes:
    return (b"<</Type/XObject/Subtype/Image/Width 1/Height 1"
            b"/ColorSpace/DeviceRGB/BitsPerComponent 8"
            b"/Length 3>>stream\n" + b"\xff\x00\x00"
            + b"\nendstream ")


def _two_img_pdf(first_drawn_high: bool) -> bytes:
    hi = b"q 40 0 0 40 50 300 cm /Im0 Do Q\n"
    lo = b"q 30 0 0 30 50 100 cm /Im1 Do Q\n"
    txt = (b"BT /F1 12 Tf 10 380 Td "
           b"(Two images on one page.) Tj ET\n")
    s = hi + lo + txt if first_drawn_high else lo + hi + txt
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 400]"
            b"/Resources<</XObject<</Im0 6 0 R/Im1 7 0 R>>"
            b"/Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        6: _img_obj(),
        7: _img_obj(),
    }, 8)


def _board(tmp_path, doc_id, anchors=None, high_first=True):
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "s" / f"{doc_id}.pdf").write_bytes(
        _two_img_pdf(high_first))
    docs = [{"doc_id": doc_id, "path": f"s/{doc_id}.pdf",
             "source_type": "pdf"}]
    if anchors is not None:
        (tmp_path / "a").mkdir(exist_ok=True)
        (tmp_path / "a" / "a.json").write_text(json.dumps({
            "annotation_version": "1.0", "doc_id": doc_id,
            "chunk_boundary_anchors": anchors}), encoding="utf-8")
        docs[0]["annotation_file"] = "a/a.json"
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": docs}), encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 双图绘制序 ----------

def test_two_images_draw_order_batch366(tmp_path):
    _board(tmp_path, "ti", high_first=True)
    doc, errors = process_single(
        tmp_path / "s" / "ti.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == [
        "paragraph", "image", "image"]
    assert els[0]["content"] == "Two images on one page."
    assert els[1]["source_locator"] == {
        "page": 1, "bbox": [50.0, 60.0, 90.0, 100.0]}
    assert els[2]["source_locator"] == {
        "page": 1, "bbox": [50.0, 270.0, 80.0, 300.0]}


def test_two_images_draw_order_reversed_batch366(tmp_path):
    _board(tmp_path, "ti2", high_first=False)
    doc, errors = process_single(
        tmp_path / "s" / "ti2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == [
        "paragraph", "image", "image"]
    assert els[1]["source_locator"] == {
        "page": 1, "bbox": [50.0, 270.0, 80.0, 300.0]}
    assert els[2]["source_locator"] == {
        "page": 1, "bbox": [50.0, 60.0, 90.0, 100.0]}


# ---------- 双图无块 ----------

def test_two_images_no_chunks_batch366(tmp_path):
    _board(tmp_path, "ti3")
    doc, errors = process_single(
        tmp_path / "s" / "ti3.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    dd = doc.to_dict()
    img_ids = [e["element_id"] for e in dd["elements"]
               if e["type"] == "image"]
    assert len(img_ids) == 2
    chunks = dd["chunks"]
    assert [c["metadata"]["strategy"] for c in chunks] == [
        "sequential"]
    assert len(chunks[0]["source_element_ids"]) == 1
    assert all(iid not in chunks[0]["source_element_ids"]
               for iid in img_ids)


# ---------- 指标 ----------

def test_two_images_metrics_batch366(tmp_path):
    r = run_evaluation(_board(tmp_path, "ti4"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 1, "image": 2},
        "reason": None}
    assert m["image_resource_exists_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 零预测界 ----------

def test_zero_predicted_boundaries_batch366(tmp_path):
    r = run_evaluation(_board(tmp_path, "ti5", [
        {"marker": "page.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert m["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": None, "reason": "no_predicted_boundaries"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch366():
    src = _src()
    assert src.count("process_single") == 6
    assert src.count("annotation") == 10
    assert src.count("expected_failure") == 5


# ---------- forbidden tokens 第六百四十批 ----------

def test_source_no_eval_batch366():
    assert "eval(" not in _src()


def test_source_no_exec_batch366():
    assert "exec(" not in _src()


def test_source_no_compile_batch366():
    assert "compile(" not in _src()


def test_source_no_globals_batch366():
    assert "globals(" not in _src()


def test_source_no_locals_batch366():
    assert "locals(" not in _src()


def test_source_no_os_system_batch366():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch366():
    assert "subprocess" not in _src()


def test_source_no_popen_batch366():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch366():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch366():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch366():
    assert "socket" not in _src()


def test_source_no_requests_batch366():
    assert "requests" not in _src()


def test_source_no_urllib_batch366():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch366():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch366():
    assert "yield" not in _src()


def test_source_no_async_await_batch366():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch366():
    assert _src().count("open(") == 2
