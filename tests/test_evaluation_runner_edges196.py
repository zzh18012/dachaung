"""evaluation/runner.py 第六百二十七轮 edges 测试（Round 1183）。

补强 edges195 未触及的角度（第五百五十五批，probe 实证）。

新角度（多 Tj 字节级拼接 / 三题板）：
- **多 Tj 无自动空格**——同 BT 块内 (Hello )
  Tj (World) Tj → "Hello World"（源空格保
  留）；(NoSpace) Tj (Glued) Tj →
  "NoSpaceGlued"（无自动插空，字节级拼接
  首锁）
- **三行皆题**——三行短文本无句读 → 三个
  heading、各成独立块（题链软界连切）
- **中界锚**——"World" after（界 1）与
  "Glued" after（界 2）各单挂 → P 1/2 /
  R 1.0 / F1 2/3；双挂全 1.0
- forbidden tokens 第六百五十五批（open 2）
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
    s = (b"BT /F1 12 Tf 10 700 Td "
         b"(Hello ) Tj (World) Tj ET\n"
         b"BT /F1 12 Tf 10 650 Td "
         b"(NoSpace) Tj (Glued) Tj ET\n"
         b"BT /F1 12 Tf 10 600 Td "
         b"(One Piece) Tj ET\n")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
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


# ---------- 多 Tj 无自动空格 ----------

def test_multi_tj_concatenation_batch381(tmp_path):
    _board(tmp_path, "mj")
    doc, errors = process_single(
        tmp_path / "s" / "mj.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["content"] for e in els] == [
        "Hello World", "NoSpaceGlued", "One Piece"]
    assert all(e["type"] == "heading" for e in els)
    assert all(e["metadata"] == {
        "level": 0, "heuristic": "short_line"}
        for e in els)


# ---------- 三题板 ----------

def test_heading_chain_chunks_batch381(tmp_path):
    _board(tmp_path, "mj2")
    doc, errors = process_single(
        tmp_path / "s" / "mj2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert [c["text"] for c in chunks] == [
        "Hello World", "NoSpaceGlued", "One Piece"]
    assert all(len(c["source_element_ids"]) == 1
               for c in chunks)


# ---------- 中界锚 ----------

def test_world_anchor_batch381(tmp_path):
    r = run_evaluation(_board(tmp_path, "mj3", [
        {"marker": "World", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


def test_glued_anchor_batch381(tmp_path):
    r = run_evaluation(_board(tmp_path, "mj4", [
        {"marker": "Glued", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


def test_both_anchors_batch381(tmp_path):
    r = run_evaluation(_board(tmp_path, "mj5", [
        {"marker": "World", "position": "after"},
        {"marker": "Glued", "position": "after"}]),
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

def test_heading_chain_by_type_batch381(tmp_path):
    r = run_evaluation(_board(tmp_path, "mj6"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 3}, "reason": None}
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch381():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("annotation") == 10
    assert src.count("manifest") == 5


# ---------- forbidden tokens 第六百五十五批 ----------

def test_source_no_eval_batch381():
    assert "eval(" not in _src()


def test_source_no_exec_batch381():
    assert "exec(" not in _src()


def test_source_no_compile_batch381():
    assert "compile(" not in _src()


def test_source_no_globals_batch381():
    assert "globals(" not in _src()


def test_source_no_locals_batch381():
    assert "locals(" not in _src()


def test_source_no_os_system_batch381():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch381():
    assert "subprocess" not in _src()


def test_source_no_popen_batch381():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch381():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch381():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch381():
    assert "socket" not in _src()


def test_source_no_requests_batch381():
    assert "requests" not in _src()


def test_source_no_urllib_batch381():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch381():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch381():
    assert "yield" not in _src()


def test_source_no_async_await_batch381():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch381():
    assert _src().count("open(") == 2
