"""evaluation/runner.py 第六百三十八轮 edges 测试（Round 1194）。

补强 edges204 未触及的角度（第五百六十六批，probe 实证）。

新角度（连字符换行不去连）：
- **无去连字符**——行尾 "inter-" 与
  次行 "national" 合流为 "inter-
  national"（空格连接、连字符保留，
  不拼回 "international" 首锁）
- **三行一段**——y 700/680/660 三行
  合单 paragraph（131 字）
- **中段锚两级偏离**——"inter-"
  after（距界 103）与 "documents."
  after（距界 65）皆全 0.0（> 30 容差
  的两档距离证）
- **锚序敏感**——[here, inter] 丢弃
  → 1.0s；[inter, here] → P 1.0 /
  R 0.5 / F1 2/3
- forbidden tokens 第六百六十六批（open 2）
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


_A1 = "The configuration uses inter-"
_A2 = "national standards for all documents."
_A3 = ("Second sentence keeps the paragraph alive "
       "and long enough here.")
_B = ("Final paragraph wraps up the hyphenation probe "
      "with enough characters to overflow the budget.")

_A = (_A1 + " " + _A2 + " " + _A3)


def _pdf() -> bytes:
    def T(text, x, y):
        return ("BT /F1 12 Tf %d %d Td (%s) Tj ET\n"
                % (x, y, text)).encode()
    s = (T(_A1, 10, 700) + T(_A2, 10, 680)
         + T(_A3, 10, 660) + T(_B, 10, 620))
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 500 800]"
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


# ---------- 无去连字符 ----------

def test_hyphen_no_dehyphenation_batch392(tmp_path):
    _board(tmp_path, "hy")
    doc, errors = process_single(
        tmp_path / "s" / "hy.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == ["paragraph"] * 2
    assert els[0]["content"] == _A
    assert "inter- national" in els[0]["content"]
    assert "international" not in els[0]["content"]


def test_hyphen_chunks_batch392(tmp_path):
    _board(tmp_path, "hy2")
    doc, errors = process_single(
        tmp_path / "s" / "hy2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert [c["text"] for c in chunks] == [_A, _B]
    assert [len(c["source_element_ids"]) for c in chunks] == [1, 1]


# ---------- 中段锚两级偏离 ----------

def test_here_anchor_batch392(tmp_path):
    r = run_evaluation(_board(tmp_path, "a1", [
        {"marker": "here.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_inter_anchor_batch392(tmp_path):
    r = run_evaluation(_board(tmp_path, "a2", [
        {"marker": "inter-", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.0, "reason": None}


def test_docs_anchor_batch392(tmp_path):
    r = run_evaluation(_board(tmp_path, "a3", [
        {"marker": "documents.", "position": "after"}]),
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

def test_order_drop_batch392(tmp_path):
    r = run_evaluation(_board(tmp_path, "a4", [
        {"marker": "here.", "position": "after"},
        {"marker": "inter-", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_order_fwd_batch392(tmp_path):
    r = run_evaluation(_board(tmp_path, "a5", [
        {"marker": "inter-", "position": "after"},
        {"marker": "here.", "position": "after"}]),
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

def test_hyphen_metrics_batch392(tmp_path):
    r = run_evaluation(_board(tmp_path, "mx"),
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


def test_source_identifier_counts_batch392():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百六十六批 ----------

def test_source_no_eval_batch392():
    assert "eval(" not in _src()


def test_source_no_exec_batch392():
    assert "exec(" not in _src()


def test_source_no_compile_batch392():
    assert "compile(" not in _src()


def test_source_no_globals_batch392():
    assert "globals(" not in _src()


def test_source_no_locals_batch392():
    assert "locals(" not in _src()


def test_source_no_os_system_batch392():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch392():
    assert "subprocess" not in _src()


def test_source_no_popen_batch392():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch392():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch392():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch392():
    assert "socket" not in _src()


def test_source_no_requests_batch392():
    assert "requests" not in _src()


def test_source_no_urllib_batch392():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch392():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch392():
    assert "yield" not in _src()


def test_source_no_async_await_batch392():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch392():
    assert _src().count("open(") == 2
