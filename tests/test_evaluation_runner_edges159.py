"""evaluation/runner.py 第五百八十四轮 edges 测试（Round 1140）。

补强 edges158 未触及的角度（第五百一十六批，probe 实证）。

新角度（纵向距离分段 / 无文本标注）：
- **远距双 run 分段**——同页 y=290 与 y=10 两 run
  （MediaBox 高 300）→ 2 个 paragraph 各自独立——与
  edges150 的近距合并（Δ20）对照，纵向距离是分段依据
  （远距分段首锁）
- **双段合块**——两段皆短 → 恰 1 chunk sequential 双源
  ——分段不分块
- **无文本标注态**——image-only 板挂 marker 标注 →
  P null no_predicted_boundaries / R 0.0 / F1 null
  ——标注存在但无文本流可搜（图片通道首锁）
- forbidden tokens 第六百一十三批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _build_one_page_pdf(stream, height=300) -> bytes:
    objects = {}
    objects[1] = b"<</Type/Catalog/Pages 2 0 R>>"
    objects[2] = b"<</Type/Pages/Kids[3 0 R]/Count 1>>"
    objects[3] = (
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 500 "
        + str(height).encode() + b"]"
        b"/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>")
    objects[4] = b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"
    objects[5] = (
        b"<</Length " + str(len(stream)).encode() + b">>stream\n"
        + stream + b"\nendstream ")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objects[num] + b"endobj\n")
    xref_pos = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


def _far_pdf() -> bytes:
    return _build_one_page_pdf(
        b"BT /F1 12 Tf 10 290 Td (Top line here.) Tj ET\n"
        b"BT /F1 12 Tf 10 10 Td (Bottom line far away.) Tj ET")


def _image_pdf() -> bytes:
    s = b"q 30 0 0 30 10 20 cm /Im0 Do Q"
    objects = {
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
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objects[num] + b"endobj\n")
    xref_pos = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


def _board(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "anns").mkdir(exist_ok=True)
    (tmp_path / "samples" / "far.pdf").write_bytes(_far_pdf())
    (tmp_path / "samples" / "img.pdf").write_bytes(_image_pdf())
    (tmp_path / "anns" / "img.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "img",
        "chunk_boundary_anchors": [
            {"marker": "anything", "position": "after"}]}),
        encoding="utf-8")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "far", "path": "samples/far.pdf",
             "source_type": "pdf"},
            {"doc_id": "img", "path": "samples/img.pdf",
             "source_type": "pdf",
             "annotation_file": "anns/img.json"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 远距双 run 分段 ----------

def test_far_runs_separate_paragraphs_batch339(tmp_path):
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "far.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert len(els) == 2
    assert all(e["type"] == "paragraph" for e in els)
    assert els[0]["content"] == "Top line here."
    assert els[1]["content"] == "Bottom line far away."


# ---------- 双段合块 ----------

def test_two_paragraphs_one_chunk_batch339(tmp_path):
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "far.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    d = doc.to_dict()
    assert len(d["chunks"]) == 1
    assert d["chunks"][0]["text"] == \
        "Top line here. Bottom line far away."
    assert len(d["chunks"][0]["source_element_ids"]) == 2


def test_far_board_metrics_batch339(tmp_path):
    r = run_evaluation(_board(tmp_path), tmp_path / "r.json",
                       parser_name="fallback", max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_total"] == {"value": 2, "reason": None}
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 2}, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 无文本标注态 ----------

def test_chunkless_annotation_metrics_batch339(tmp_path):
    r = run_evaluation(_board(tmp_path), tmp_path / "r.json",
                       parser_name="fallback", max_chars=200)
    m = r["per_doc"][1]["metrics"]
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert m["chunk_boundary_recall"] == {"value": 0.0,
                                          "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": None, "reason": "no_predicted_boundaries"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch339():
    src = _src()
    assert src.count("metrics") == 13
    assert src.count("manifest") == 5


# ---------- forbidden tokens 第六百一十三批 ----------

def test_source_no_eval_batch339():
    assert "eval(" not in _src()


def test_source_no_exec_batch339():
    assert "exec(" not in _src()


def test_source_no_compile_batch339():
    assert "compile(" not in _src()


def test_source_no_globals_batch339():
    assert "globals(" not in _src()


def test_source_no_locals_batch339():
    assert "locals(" not in _src()


def test_source_no_os_system_batch339():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch339():
    assert "subprocess" not in _src()


def test_source_no_popen_batch339():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch339():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch339():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch339():
    assert "socket" not in _src()


def test_source_no_requests_batch339():
    assert "requests" not in _src()


def test_source_no_urllib_batch339():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch339():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch339():
    assert "yield" not in _src()


def test_source_no_async_await_batch339():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch339():
    assert _src().count("open(") == 2
