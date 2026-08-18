"""evaluation/runner.py 第五百八十二轮 edges 测试（Round 1138）。

补强 edges156 未触及的角度（第五百一十四批，probe 实证）。

新角度（真嵌入图片 XObject 通道）：
- **图片元素真定位**——手写 Image XObject（Do 操作符、
  50×50 cm 矩阵）→ image 元素 content None +
  source_locator {page 1, bbox [10, 30, 60, 80]}——
  bbox 直接来自 cm 矩阵（真图片数据首锁）
- **图片不参与分块**——纯图板 chunks 恰空——本阶段
  image 元素无文本不进 chunker
- **零块不等于失败**——纯图板 success True + ect 1 +
  by_type {image: 1}——no_extracted_elements 只属于
  零元素板，有图不算空
- **零块指标语义**——chunk_ref null no_chunks（分母 0
  规则在真数据上触发）+ text_equal True（双侧皆空）
- **图文同页共存**——文字 + 图片同一页 → els
  [paragraph, image]，chunk 只含文字——图不切块不吞文
- forbidden tokens 第六百一十一批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _build_pdf(content_stream, n_objects) -> bytes:
    objects = dict(content_stream)
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objects[num] + b"endobj\n")
    xref_pos = len(out)
    out += b"xref\n0 " + str(n_objects).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for num in range(1, n_objects):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size " + str(n_objects).encode()
            + b"/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


def _image_only_pdf() -> bytes:
    s = b"q 50 0 0 50 10 20 cm /Im0 Do Q"
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</XObject<</Im0 5 0 R>>>>"
            b"/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: (b"<</Type/XObject/Subtype/Image/Width 1/Height 1"
            b"/ColorSpace/DeviceRGB/BitsPerComponent 8"
            b"/Length 3>>stream\n\xff\x00\x00\nendstream "),
    }, 6)


def _mixed_pdf() -> bytes:
    s = (b"q 50 0 0 50 10 20 cm /Im0 Do Q\n"
         b"BT /F1 12 Tf 10 90 Td (Caption beside image.) Tj ET")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</Font<</F1 6 0 R>>"
            b"/XObject<</Im0 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: (b"<</Type/XObject/Subtype/Image/Width 1/Height 1"
            b"/ColorSpace/DeviceRGB/BitsPerComponent 8"
            b"/Length 3>>stream\n\xff\x00\x00\nendstream "),
        6: (b"<</Type/Font/Subtype/Type1"
            b"/BaseFont/Helvetica>>"),
    }, 7)


def _board(tmp_path, pdf_bytes, doc_id):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(pdf_bytes)
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id,
                       "path": f"samples/{doc_id}.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 图片元素真定位 ----------

def test_image_element_locator_batch337(tmp_path):
    _board(tmp_path, _image_only_pdf(), "im")
    doc, errors = process_single(
        tmp_path / "samples" / "im.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert len(els) == 1
    assert els[0]["type"] == "image"
    assert els[0]["content"] is None
    assert els[0]["source_locator"] == {
        "page": 1, "bbox": [10.0, 30.0, 60.0, 80.0]}


# ---------- 图片不参与分块 ----------

def test_image_only_no_chunks_batch337(tmp_path):
    _board(tmp_path, _image_only_pdf(), "im2")
    doc, errors = process_single(
        tmp_path / "samples" / "im2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    assert doc.to_dict()["chunks"] == []


# ---------- 零块不等于失败 ----------

def test_image_only_success_batch337(tmp_path):
    r = run_evaluation(_board(tmp_path, _image_only_pdf(), "im3"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["element_count_total"] == {"value": 1, "reason": None}
    assert m["element_count_by_type"] == {
        "value": {"image": 1}, "reason": None}


# ---------- 零块指标语义 ----------

def test_image_only_metric_semantics_batch337(tmp_path):
    r = run_evaluation(_board(tmp_path, _image_only_pdf(), "im4"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_reference_intact_ratio"] == {
        "value": None, "reason": "no_chunks"}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    from evaluation.schema import validate
    validate(r, "evaluation-report.schema.json")


# ---------- 图文同页共存 ----------

def test_text_image_same_page_batch337(tmp_path):
    _board(tmp_path, _mixed_pdf(), "mx")
    doc, errors = process_single(
        tmp_path / "samples" / "mx.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    d = doc.to_dict()
    assert [e["type"] for e in d["elements"]] == \
        ["paragraph", "image"]
    assert len(d["chunks"]) == 1
    assert d["chunks"][0]["text"] == "Caption beside image."
    assert d["chunks"][0]["metadata"]["strategy"] == "sequential"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch337():
    src = _src()
    assert src.count("process_single") == 6
    assert src.count("metrics") == 13


# ---------- forbidden tokens 第六百一十一批 ----------

def test_source_no_eval_batch337():
    assert "eval(" not in _src()


def test_source_no_exec_batch337():
    assert "exec(" not in _src()


def test_source_no_compile_batch337():
    assert "compile(" not in _src()


def test_source_no_globals_batch337():
    assert "globals(" not in _src()


def test_source_no_locals_batch337():
    assert "locals(" not in _src()


def test_source_no_os_system_batch337():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch337():
    assert "subprocess" not in _src()


def test_source_no_popen_batch337():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch337():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch337():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch337():
    assert "socket" not in _src()


def test_source_no_requests_batch337():
    assert "requests" not in _src()


def test_source_no_urllib_batch337():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch337():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch337():
    assert "yield" not in _src()


def test_source_no_async_await_batch337():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch337():
    assert _src().count("open(") == 2
