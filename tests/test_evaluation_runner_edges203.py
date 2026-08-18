"""evaluation/runner.py 第六百三十六轮 edges 测试（Round 1192）。

补强 edges202 未触及的角度（第五百六十四批，probe 实证）。

新角度（旋转文本整串倒序 / 隐形文本照提）：
- **90° 旋转倒序**——Tm 0 1 -1 0 →
  "Rotated Line" 提取为 "eniL detatoR"
  （全串逐字符反转：pdfplumber 对非
  upright 字符按 x 排序与阅读序相反，
  旋转文本倒序首锁）
- **3 Tr 隐形照提**——渲染模式 3（不可
  见）文本照常进流（渲染模式被忽略首锁）
- **0 Tr 复位**——隐形态后复位正常
- **四题四块跨两页**——3 预测界 → P 1/3
  新值型；双锚顺流 2/3、逆流丢弃 1/3
- forbidden tokens 第六百六十四批（open 2）
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
    s1 = (b"BT /F1 12 Tf 0 1 -1 0 100 700 Tm "
          b"(Rotated Line) Tj ET\n"
          b"BT /F1 12 Tf 3 Tr 10 650 Td "
          b"(Invisible Text Here) Tj ET\n"
          b"BT /F1 12 Tf 0 Tr 10 600 Td "
          b"(Normal Line) Tj ET\n")
    s2 = (b"BT /F1 12 Tf 10 700 Td "
          b"(Second Page Line) Tj ET\n")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 5 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 7 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
        5: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 7 0 R>>>>/Contents 6 0 R>>"),
        6: (b"<</Length " + str(len(s2)).encode()
            + b">>stream\n" + s2 + b"\nendstream "),
        7: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 8)


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


# ---------- 旋转倒序 ----------

def test_rotated_reversal_batch390(tmp_path):
    _board(tmp_path, "rt")
    doc, errors = process_single(
        tmp_path / "s" / "rt.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert els[0]["content"] == "eniL detatoR"
    assert els[0]["content"] == "Rotated Line"[::-1]
    assert els[0]["type"] == "heading"
    assert els[0]["source_locator"]["bbox"] == [
        90.484, 31.960000000000036, 102.484, 100.0]


# ---------- 隐形照提 / 复位 ----------

def test_invisible_text_extracted_batch390(tmp_path):
    _board(tmp_path, "iv")
    doc, errors = process_single(
        tmp_path / "s" / "iv.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert els[1]["content"] == "Invisible Text Here"
    assert els[2]["content"] == "Normal Line"


# ---------- 四题四块跨两页 ----------

def test_rotated_chunks_batch390(tmp_path):
    _board(tmp_path, "ch")
    doc, errors = process_single(
        tmp_path / "s" / "ch.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert [c["text"] for c in chunks] == [
        "eniL detatoR", "Invisible Text Here",
        "Normal Line", "Second Page Line"]
    assert all(len(c["source_element_ids"]) == 1
               for c in chunks)


def test_rotated_pages_batch390(tmp_path):
    _board(tmp_path, "pg")
    doc, errors = process_single(
        tmp_path / "s" / "pg.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert [e["source_locator"]["page"] for e in els] == [
        1, 1, 1, 2]


# ---------- 锚：P 1/3 新值型 ----------

def test_here_anchor_batch390(tmp_path):
    r = run_evaluation(_board(tmp_path, "a1", [
        {"marker": "Here", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.3333333333333333, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.5, "reason": None}


def test_rev_anchor_batch390(tmp_path):
    r = run_evaluation(_board(tmp_path, "a2", [
        {"marker": "eniL detatoR", "position": "before"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.3333333333333333, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.5, "reason": None}


# ---------- 锚序 ----------

def test_order_drop_batch390(tmp_path):
    r = run_evaluation(_board(tmp_path, "a3", [
        {"marker": "Here", "position": "after"},
        {"marker": "eniL detatoR", "position": "before"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.3333333333333333, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.5, "reason": None}


def test_order_forward_batch390(tmp_path):
    r = run_evaluation(_board(tmp_path, "a4", [
        {"marker": "eniL detatoR", "position": "before"},
        {"marker": "Here", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.6666666666666666, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.8, "reason": None}


# ---------- 指标 ----------

def test_rotated_metrics_batch390(tmp_path):
    r = run_evaluation(_board(tmp_path, "mx"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 4}, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}
    assert m["heading_boundary_compliance"] == {"value": 1.0,
                                                "reason": None}
    assert m["text_char_multiset_precision"] == {"value": 1.0,
                                                 "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch390():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百六十四批 ----------

def test_source_no_eval_batch390():
    assert "eval(" not in _src()


def test_source_no_exec_batch390():
    assert "exec(" not in _src()


def test_source_no_compile_batch390():
    assert "compile(" not in _src()


def test_source_no_globals_batch390():
    assert "globals(" not in _src()


def test_source_no_locals_batch390():
    assert "locals(" not in _src()


def test_source_no_os_system_batch390():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch390():
    assert "subprocess" not in _src()


def test_source_no_popen_batch390():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch390():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch390():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch390():
    assert "socket" not in _src()


def test_source_no_requests_batch390():
    assert "requests" not in _src()


def test_source_no_urllib_batch390():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch390():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch390():
    assert "yield" not in _src()


def test_source_no_async_await_batch390():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch390():
    assert _src().count("open(") == 2
