"""evaluation/runner.py 第六百三十五轮 edges 测试（Round 1191）。

补强 edges201 未触及的角度（第五百六十三批，probe 实证）。

新角度（hex 字串 / TJ 数移 / 正数左移倒序）：
- **hex Tj 解码**——<48656C6C6F> Tj →
  "Hello"（十六进制字串解码首锁）
- **TJ 小数无效**——[(Wor) 80 (d wi) -60
  (th TJ)] TJ → "Word with TJ"（±小位移
  只改坐标不改字，无自动空格）
- **TJ 正数左移倒序**——[(Big) 3000 (Gap)]
  TJ → "GapBig"（正数 = 左移 36pt，
  后段跑到前段左侧 → pdfplumber 按
  char x 排序整段倒序首锁；负 x 起点字符
  照常提取）
- **三题三块**，双锚全 1.0
- forbidden tokens 第六百六十三批（open 2）
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
    s = (b"BT /F1 12 Tf 10 750 Td <48656C6C6F> Tj ET\n"
         b"BT /F1 12 Tf 10 700 Td "
         b"[(Wor) 80 (d wi) -60 (th TJ)] TJ ET\n"
         b"BT /F1 12 Tf 10 650 Td "
         b"[(Big) 3000 (Gap)] TJ ET\n")
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


# ---------- hex 字串 ----------

def test_hex_tj_element_batch389(tmp_path):
    _board(tmp_path, "hx")
    doc, errors = process_single(
        tmp_path / "s" / "hx.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert els[0]["content"] == "Hello"
    assert els[0]["type"] == "heading"
    assert els[0]["metadata"] == {
        "level": 0, "heuristic": "short_line"}


# ---------- TJ 数移 ----------

def test_tj_small_numbers_batch389(tmp_path):
    _board(tmp_path, "tj")
    doc, errors = process_single(
        tmp_path / "s" / "tj.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert els[1]["content"] == "Word with TJ"


def test_tj_reversal_batch389(tmp_path):
    _board(tmp_path, "rv")
    doc, errors = process_single(
        tmp_path / "s" / "rv.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert els[2]["content"] == "GapBig"
    assert "BigGap" not in els[2]["content"]


def test_operator_chunks_batch389(tmp_path):
    _board(tmp_path, "op")
    doc, errors = process_single(
        tmp_path / "s" / "op.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert [c["text"] for c in chunks] == [
        "Hello", "Word with TJ", "GapBig"]
    assert all(len(c["source_element_ids"]) == 1
               for c in chunks)


# ---------- 锚 ----------

def test_hello_anchor_batch389(tmp_path):
    r = run_evaluation(_board(tmp_path, "a1", [
        {"marker": "Hello", "position": "before"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


def test_tj_anchor_batch389(tmp_path):
    r = run_evaluation(_board(tmp_path, "a2", [
        {"marker": "TJ", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


def test_gap_anchor_batch389(tmp_path):
    r = run_evaluation(_board(tmp_path, "a3", [
        {"marker": "Gap", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


def test_both_anchors_batch389(tmp_path):
    r = run_evaluation(_board(tmp_path, "a4", [
        {"marker": "Hello", "position": "before"},
        {"marker": "TJ", "position": "after"}]),
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

def test_operator_metrics_batch389(tmp_path):
    r = run_evaluation(_board(tmp_path, "mx"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 3}, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}
    assert m["heading_boundary_compliance"] == {"value": 1.0,
                                                "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch389():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百六十三批 ----------

def test_source_no_eval_batch389():
    assert "eval(" not in _src()


def test_source_no_exec_batch389():
    assert "exec(" not in _src()


def test_source_no_compile_batch389():
    assert "compile(" not in _src()


def test_source_no_globals_batch389():
    assert "globals(" not in _src()


def test_source_no_locals_batch389():
    assert "locals(" not in _src()


def test_source_no_os_system_batch389():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch389():
    assert "subprocess" not in _src()


def test_source_no_popen_batch389():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch389():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch389():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch389():
    assert "socket" not in _src()


def test_source_no_requests_batch389():
    assert "requests" not in _src()


def test_source_no_urllib_batch389():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch389():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch389():
    assert "yield" not in _src()


def test_source_no_async_await_batch389():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch389():
    assert _src().count("open(") == 2
