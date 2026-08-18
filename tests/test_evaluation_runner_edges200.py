"""evaluation/runner.py 第六百三十二轮 edges 测试（Round 1188）。

补强 edges199 未触及的角度（第五百六十批，probe 实证）。

新角度（栏交叠字符交错 / 锚序敏感）：
- **交叠栏字符交错**——左栏宽过右栏 x 起点时
  pdfplumber 按 char x 排序 → "now." 与
  "Right" 交错成 "nRoiwgh.t"（字节级交错
  首锁，无空格无去重，9 字符恰为 4+5）
- **越界字符仍提取**——行 2 文本 x1 623.6 >
  MediaBox 600，char 照常入流
- **同界双锚异值**——"too." after（界 1）
  → 全 1.0；"nRoiwgh.t" after（流中 57，
  距界 43 > 30）→ 全 0.0
- **锚序敏感**——[too, mangled] 顺序搜索时
  mangled 在 too 之前 → 找不到被静默丢弃 →
  全 1.0；倒序 [mangled, too] → GT 双存 →
  P 1.0 / R 0.5 / F1 2/3（顺序搜索语义首锁）
- forbidden tokens 第六百六十批（open 2）
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


_L = "Left column first row with plenty of words here now."
_R = "Right column first row with plenty of words too."
_B = ("Bottom full width line with plenty of extra characters "
      "so appending it after row one blows the budget wide open here.")

_MERGED = ("Left column first row with plenty of words here "
           "nRoiwgh.t column first row with plenty of words too.")


def _pdf() -> bytes:
    def T(text, x, y):
        return ("BT /F1 12 Tf %d %d Td (%s) Tj ET\n"
                % (x, y, text)).encode()
    s = T(_L, 10, 700) + T(_R, 260, 700) + T(_B, 10, 650)
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 600 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 6)


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


# ---------- 交叠栏字符交错 ----------

def test_overlap_elements_batch386(tmp_path):
    _board(tmp_path, "ov")
    doc, errors = process_single(
        tmp_path / "s" / "ov.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == ["paragraph"] * 2
    assert els[0]["content"] == _MERGED
    assert els[0]["content"].find("nRoiwgh.t") == 48
    assert els[1]["content"] == _B


def test_overlap_bboxes_batch386(tmp_path):
    _board(tmp_path, "ov2")
    doc, errors = process_single(
        tmp_path / "s" / "ov2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert els[0]["source_locator"]["bbox"] == [
        10.0, 90.48400000000004, 507.41600000000005,
        102.48400000000004]
    b1 = els[1]["source_locator"]["bbox"]
    assert b1[0] == 10.0
    assert b1[2] == 623.632000000001
    assert b1[2] > 600


def test_overlap_chunks_batch386(tmp_path):
    _board(tmp_path, "ov3")
    doc, errors = process_single(
        tmp_path / "s" / "ov3.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert [c["metadata"]["strategy"] for c in chunks] == [
        "sequential", "sequential"]
    assert [c["text"] for c in chunks] == [_MERGED, _B]
    assert [len(c["source_element_ids"]) for c in chunks] == [1, 1]


# ---------- 同界双锚异值 ----------

def test_too_anchor_batch386(tmp_path):
    r = run_evaluation(_board(tmp_path, "ov4", [
        {"marker": "too.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_mangled_anchor_batch386(tmp_path):
    r = run_evaluation(_board(tmp_path, "ov5", [
        {"marker": "nRoiwgh.t", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.0, "reason": None}


# ---------- 锚序敏感 ----------

def test_anchor_order_drop_batch386(tmp_path):
    r = run_evaluation(_board(tmp_path, "ov6", [
        {"marker": "too.", "position": "after"},
        {"marker": "nRoiwgh.t", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_anchor_order_reversed_batch386(tmp_path):
    r = run_evaluation(_board(tmp_path, "ov7", [
        {"marker": "nRoiwgh.t", "position": "after"},
        {"marker": "too.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


# ---------- 指标 ----------

def test_overlap_metrics_batch386(tmp_path):
    r = run_evaluation(_board(tmp_path, "ov8"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 2}, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {"value": 1.0,
                                                 "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch386():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百六十批 ----------

def test_source_no_eval_batch386():
    assert "eval(" not in _src()


def test_source_no_exec_batch386():
    assert "exec(" not in _src()


def test_source_no_compile_batch386():
    assert "compile(" not in _src()


def test_source_no_globals_batch386():
    assert "globals(" not in _src()


def test_source_no_locals_batch386():
    assert "locals(" not in _src()


def test_source_no_os_system_batch386():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch386():
    assert "subprocess" not in _src()


def test_source_no_popen_batch386():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch386():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch386():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch386():
    assert "socket" not in _src()


def test_source_no_requests_batch386():
    assert "requests" not in _src()


def test_source_no_urllib_batch386():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch386():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch386():
    assert "yield" not in _src()


def test_source_no_async_await_batch386():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch386():
    assert _src().count("open(") == 2
