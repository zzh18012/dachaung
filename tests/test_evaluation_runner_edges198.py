"""evaluation/runner.py 第六百三十轮 edges 测试（Round 1186）。

补强 edges197 未触及的角度（第五百五十八批，probe 实证）。

新角度（双栏逐行合流 / 句内预算切）：
- **双栏逐行合并**——同 y 左右两栏文本合并
  为单元素 "L R"（单空格连接，无栏感知，
  PDF 逐行合流首锁）
- **101 字元素句内切**——合并行 101 > 100 →
  句界切 [52, 48]；96 字行整块保留——
  chunks [52, 48, 96] 各 1 源
- **行尾锚三态**——"here now." after（界 1）
  → P 1/2 / R 1.0 / F1 2/3；"layout." after
  （流尾无界）→ 全 0.0；双锚 → P 0.5 /
  R 0.5 / F1 0.5（半命中组合值首锁）
- forbidden tokens 第六百五十八批（open 2）
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


_R1L = "Left column first row with plenty of words here now."
_R1R = "Right column first row with plenty of words too."
_R2L = "Left column second row keeps going to the finish."
_R2R = "Right column second row ends the whole layout."


def _pdf() -> bytes:
    def T(text, x, y):
        return ("BT /F1 12 Tf %d %d Td (%s) Tj ET\n"
                % (x, y, text)).encode()
    s = (T(_R1L, 10, 700) + T(_R1R, 400, 700)
         + T(_R2L, 10, 650) + T(_R2R, 400, 650))
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 700 800]"
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


# ---------- 双栏逐行合并 ----------

def test_column_row_merge_batch384(tmp_path):
    _board(tmp_path, "cl")
    doc, errors = process_single(
        tmp_path / "s" / "cl.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=100)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == ["paragraph"] * 2
    assert els[0]["content"] == _R1L + " " + _R1R
    assert els[1]["content"] == _R2L + " " + _R2R


# ---------- 句内预算切 ----------

def test_column_chunks_batch384(tmp_path):
    _board(tmp_path, "cl2")
    doc, errors = process_single(
        tmp_path / "s" / "cl2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=100)
    chunks = doc.to_dict()["chunks"]
    assert [c["metadata"]["strategy"] for c in chunks] == [
        "long_paragraph_sentence_split"] * 2 + ["sequential"]
    assert [c["text"] for c in chunks] == [
        _R1L, _R1R, _R2L + " " + _R2R]
    assert all(len(c["source_element_ids"]) == 1
               for c in chunks)
    assert [len(c["text"]) for c in chunks] == [52, 48, 96]


# ---------- 行尾锚三态 ----------

def test_column_row1_anchor_batch384(tmp_path):
    r = run_evaluation(_board(tmp_path, "cl3", [
        {"marker": "here now.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=100)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


def test_column_row2_anchor_batch384(tmp_path):
    r = run_evaluation(_board(tmp_path, "cl4", [
        {"marker": "layout.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=100)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.0, "reason": None}


def test_column_both_anchors_batch384(tmp_path):
    r = run_evaluation(_board(tmp_path, "cl5", [
        {"marker": "here now.", "position": "after"},
        {"marker": "layout.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=100)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.5, "reason": None}


# ---------- 指标 ----------

def test_column_metrics_batch384(tmp_path):
    r = run_evaluation(_board(tmp_path, "cl6"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=100)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 2}, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch384():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百五十八批 ----------

def test_source_no_eval_batch384():
    assert "eval(" not in _src()


def test_source_no_exec_batch384():
    assert "exec(" not in _src()


def test_source_no_compile_batch384():
    assert "compile(" not in _src()


def test_source_no_globals_batch384():
    assert "globals(" not in _src()


def test_source_no_locals_batch384():
    assert "locals(" not in _src()


def test_source_no_os_system_batch384():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch384():
    assert "subprocess" not in _src()


def test_source_no_popen_batch384():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch384():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch384():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch384():
    assert "socket" not in _src()


def test_source_no_requests_batch384():
    assert "requests" not in _src()


def test_source_no_urllib_batch384():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch384():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch384():
    assert "yield" not in _src()


def test_source_no_async_await_batch384():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch384():
    assert _src().count("open(") == 2
