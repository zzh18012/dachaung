"""evaluation/runner.py 第六百二十九轮 edges 测试（Round 1185）。

补强 edges196 未触及的角度（第五百五十七批，probe 实证）。

新角度（题下 caption 的类先于序）：
- **caption 在格下**——格区（top 170-220）
  物理高于 caption（top 290-302），但元素
  序 [heading, caption, table]——文本类按 y
  序先行、表格殿后，表格不因物理位置插队
  （类先于序 vs y 序的裁决首锁）
- **格字双现**——格内文字既成独立 heading
  元素（"Ga Gb"）又入表 markdown 单元格
  （与 edges180 五型板同构互证）
- **三块布局**——[seq(Ga Gb), iso_caption,
  iso_table]
- **caption 尾锚**——"grid." after → 界 1 →
  P 1/2 / R 1.0 / F1 2/3
- forbidden tokens 第六百五十七批（open 2）
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


def _pdf() -> bytes:
    s = (b"1 w 0 G\n"
         b"10 180 100 50 re S\n60 180 0 50 re S\n"
         b"10 230 100 0 re S\n"
         b"BT /F1 10 Tf 15 205 Td (Ga) Tj ET\n"
         b"BT /F1 10 Tf 65 205 Td (Gb) Tj ET\n"
         b"BT /F1 12 Tf 10 100 Td "
         b"(Table 1: caption below the grid.) Tj ET\n")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 400]"
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


# ---------- 类先于序 ----------

def test_caption_below_order_batch383(tmp_path):
    _board(tmp_path, "cb")
    doc, errors = process_single(
        tmp_path / "s" / "cb.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == [
        "heading", "caption", "table"]
    assert els[1]["content"] == \
        "Table 1: caption below the grid."
    assert els[2]["content"] == \
        "| Ga | Gb |\n| --- | --- |"
    assert els[2]["source_locator"]["bbox"] == [
        10.0, 170.0, 110.0, 220.0]
    assert els[1]["source_locator"]["bbox"][1] > \
        els[2]["source_locator"]["bbox"][3]


# ---------- 格字双现 ----------

def test_grid_text_dual_presence_batch383(tmp_path):
    _board(tmp_path, "cb2")
    doc, errors = process_single(
        tmp_path / "s" / "cb2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert els[0]["content"] == "Ga Gb"
    assert els[0]["metadata"] == {
        "level": 0, "heuristic": "short_line"}
    assert "Ga" in els[2]["content"]


# ---------- 三块布局 ----------

def test_caption_below_chunks_batch383(tmp_path):
    _board(tmp_path, "cb3")
    doc, errors = process_single(
        tmp_path / "s" / "cb3.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert [c["metadata"]["strategy"] for c in chunks] == [
        "sequential", "isolated_caption", "isolated_table"]
    assert chunks[0]["text"] == "Ga Gb"
    assert all(len(c["source_element_ids"]) == 1
               for c in chunks)


# ---------- caption 尾锚 ----------

def test_caption_tail_anchor_batch383(tmp_path):
    r = run_evaluation(_board(tmp_path, "cb4", [
        {"marker": "grid.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


# ---------- 指标 ----------

def test_caption_below_metrics_batch383(tmp_path):
    r = run_evaluation(_board(tmp_path, "cb5"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "caption": 1, "table": 1},
        "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch383():
    src = _src()
    assert src.count("metrics") == 13
    assert src.count("error_code") == 4
    assert src.count("process_single") == 6


# ---------- forbidden tokens 第六百五十七批 ----------

def test_source_no_eval_batch383():
    assert "eval(" not in _src()


def test_source_no_exec_batch383():
    assert "exec(" not in _src()


def test_source_no_compile_batch383():
    assert "compile(" not in _src()


def test_source_no_globals_batch383():
    assert "globals(" not in _src()


def test_source_no_locals_batch383():
    assert "locals(" not in _src()


def test_source_no_os_system_batch383():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch383():
    assert "subprocess" not in _src()


def test_source_no_popen_batch383():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch383():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch383():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch383():
    assert "socket" not in _src()


def test_source_no_requests_batch383():
    assert "requests" not in _src()


def test_source_no_urllib_batch383():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch383():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch383():
    assert "yield" not in _src()


def test_source_no_async_await_batch383():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch383():
    assert _src().count("open(") == 2
