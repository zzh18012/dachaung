"""evaluation/runner.py 第六百四十四轮 edges 测试（Round 1200）。

补强 edges209 未触及的角度（第五百七十二批，probe 实证）。

新角度（纯空白行的透明性）：
- **空白行全透明**——y 间夹一行
  "     "：紧距板与无空行板产物完全
  相同（单合并段；空白行既不成元素
  也不断段，y 间距按内容行计首锁）
- **远距正常分离**——40pt 间距仍
  两元素（分离源于距不源于空白行）
- **流尾锚零界**——"blank." after →
  全 0.0
- forbidden tokens 第六百七十二批（open 2）
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


_P1 = "First real paragraph text here."
_P2 = "Second real paragraph after the blank."
_Q1 = "Tight first paragraph line."
_Q2 = "Tight second paragraph line."


def _pdf(mode) -> bytes:
    if mode == "tight_blank":
        s = (_T(_Q1, 10, 700) + _T("     ", 10, 690)
             + _T(_Q2, 10, 680))
    elif mode == "tight_noblank":
        s = _T(_Q1, 10, 700) + _T(_Q2, 10, 690)
    else:
        s = (_T(_P1, 10, 700) + _T("     ", 10, 680)
             + _T(_P2, 10, 660))
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 6)


def _board(tmp_path, doc_id, mode, anchors=None):
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "a").mkdir(exist_ok=True)
    (tmp_path / "s" / f"{doc_id}.pdf").write_bytes(_pdf(mode))
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


# ---------- 空白行全透明 ----------

def test_blank_transparent_merge_batch398(tmp_path):
    _board(tmp_path, "tb", "tight_blank")
    doc, errors = process_single(
        tmp_path / "s" / "tb.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["content"] for e in els] == [_Q1 + " " + _Q2]


def test_blank_transparent_noblank_equal_batch398(tmp_path):
    _board(tmp_path, "tn", "tight_noblank")
    doc, errors = process_single(
        tmp_path / "s" / "tn.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert [e["content"] for e in els] == [_Q1 + " " + _Q2]


def test_blank_line_dropped_batch398(tmp_path):
    _board(tmp_path, "bd", "far")
    doc, errors = process_single(
        tmp_path / "s" / "bd.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == ["paragraph"] * 2
    assert [e["content"] for e in els] == [_P1, _P2]
    assert all(e["content"].strip() for e in els)


def test_blank_far_chunks_batch398(tmp_path):
    _board(tmp_path, "bf", "far")
    doc, errors = process_single(
        tmp_path / "s" / "bf.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=50)
    chunks = doc.to_dict()["chunks"]
    assert [c["text"] for c in chunks] == [_P1, _P2]
    assert all(len(c["source_element_ids"]) == 1
               for c in chunks)


# ---------- 锚 ----------

def test_here_anchor_batch398(tmp_path):
    r = run_evaluation(_board(tmp_path, "a1", "far", [
        {"marker": "here.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_blank_anchor_batch398(tmp_path):
    r = run_evaluation(_board(tmp_path, "a2", "far", [
        {"marker": "blank.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.0, "reason": None}


def test_both_anchors_batch398(tmp_path):
    r = run_evaluation(_board(tmp_path, "a3", "far", [
        {"marker": "here.", "position": "after"},
        {"marker": "blank.", "position": "after"}]),
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

def test_blank_metrics_batch398(tmp_path):
    r = run_evaluation(_board(tmp_path, "mx", "far"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 2}, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch398():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百七十二批 ----------

def test_source_no_eval_batch398():
    assert "eval(" not in _src()


def test_source_no_exec_batch398():
    assert "exec(" not in _src()


def test_source_no_compile_batch398():
    assert "compile(" not in _src()


def test_source_no_globals_batch398():
    assert "globals(" not in _src()


def test_source_no_locals_batch398():
    assert "locals(" not in _src()


def test_source_no_os_system_batch398():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch398():
    assert "subprocess" not in _src()


def test_source_no_popen_batch398():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch398():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch398():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch398():
    assert "socket" not in _src()


def test_source_no_requests_batch398():
    assert "requests" not in _src()


def test_source_no_urllib_batch398():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch398():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch398():
    assert "yield" not in _src()


def test_source_no_async_await_batch398():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch398():
    assert _src().count("open(") == 2
