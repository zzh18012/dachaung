"""evaluation/runner.py 第六百二十一轮 edges 测试（Round 1177）。

补强 edges189 未触及的角度（第五百四十九批，probe 实证）。

新角度（题前超大段的分块层级）：
- **题独占块**——heading(18 字) + 超长段(225 >
  200)：题自成一 sequential 块、不被段的
  forced 切割拖入——段独立走
  long_paragraph_sentence_split [180, 44]
  （两级机制叠加首锁：题界优先于预算切分）
- **句界白空间切**——有句读的超长段在句边界
  切（180 恰含前 3 句），尾块 44——与 edges161
  无白界 forced_char 成对照
- **双界锚**——题尾锚 "Text" after 与句界锚
  "bright." after 各单挂 → P 0.5 / R 1.0 /
  F1 2/3；双锚齐挂 → 全 1.0
- **compliance 保 1.0**——超大段场景下题仍居
  块首
- forbidden tokens 第六百四十九批（open 2）
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


_H = "Section Title Text"
_S1 = ("The quick brown fox jumps over the lazy dog again "
       "and again here. ")
_S2 = "Pack my box with five dozen liquor jugs right now. "
_S3 = ("How vexingly quick daft zebras jump when the sun "
       "shines bright. ")
_S4 = "Sphinx of black quartz judge my vow tonight."
_P = _S1 + _S2 + _S3 + _S4


def _pdf() -> bytes:
    def T(text, y):
        return ("BT /F1 12 Tf 10 %d Td (%s) Tj ET\n"
                % (y, text)).encode()
    s = T(_H, 750) + T(_P, 700)
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 900 800]"
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
            "chunk_boundary_anchors": anchors}), encoding="utf-8")
        docs[0]["annotation_file"] = "a/a.json"
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": docs}), encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 题独占块 ----------

def test_heading_isolated_before_oversize_batch375(tmp_path):
    _board(tmp_path, "hp")
    doc, errors = process_single(
        tmp_path / "s" / "hp.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    dd = doc.to_dict()
    assert dd["elements"][0]["metadata"] == {
        "level": 0, "heuristic": "short_line"}
    chunks = dd["chunks"]
    assert [c["metadata"]["strategy"] for c in chunks] == [
        "sequential", "long_paragraph_sentence_split",
        "long_paragraph_sentence_split"]
    assert chunks[0]["text"] == _H
    assert len(chunks[0]["source_element_ids"]) == 1
    assert [len(c["text"]) for c in chunks] == [18, 180, 44]


# ---------- 句界白空间切 ----------

def test_sentence_split_texts_batch375(tmp_path):
    _board(tmp_path, "hp2")
    doc, errors = process_single(
        tmp_path / "s" / "hp2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert chunks[1]["text"] == (_S1 + _S2 + _S3).strip()
    assert chunks[2]["text"] == _S4
    assert chunks[1]["text"].endswith("bright.")
    assert all(len(c["source_element_ids"]) == 1
               for c in chunks)


# ---------- 双界锚 ----------

def test_heading_end_anchor_batch375(tmp_path):
    r = run_evaluation(_board(tmp_path, "hp3", [
        {"marker": "Text", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


def test_sentence_end_anchor_batch375(tmp_path):
    r = run_evaluation(_board(tmp_path, "hp4", [
        {"marker": "bright.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


def test_both_anchors_batch375(tmp_path):
    r = run_evaluation(_board(tmp_path, "hp5", [
        {"marker": "Text", "position": "after"},
        {"marker": "bright.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


# ---------- 指标 ----------

def test_oversize_metrics_batch375(tmp_path):
    r = run_evaluation(_board(tmp_path, "hp6"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "paragraph": 1},
        "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch375():
    src = _src()
    assert src.count("process_single") == 6
    assert src.count("annotation") == 10
    assert src.count("expected_failure") == 5


# ---------- forbidden tokens 第六百四十九批 ----------

def test_source_no_eval_batch375():
    assert "eval(" not in _src()


def test_source_no_exec_batch375():
    assert "exec(" not in _src()


def test_source_no_compile_batch375():
    assert "compile(" not in _src()


def test_source_no_globals_batch375():
    assert "globals(" not in _src()


def test_source_no_locals_batch375():
    assert "locals(" not in _src()


def test_source_no_os_system_batch375():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch375():
    assert "subprocess" not in _src()


def test_source_no_popen_batch375():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch375():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch375():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch375():
    assert "socket" not in _src()


def test_source_no_requests_batch375():
    assert "requests" not in _src()


def test_source_no_urllib_batch375():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch375():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch375():
    assert "yield" not in _src()


def test_source_no_async_await_batch375():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch375():
    assert _src().count("open(") == 2
