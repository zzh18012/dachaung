"""evaluation/runner.py 第六百四十九轮 edges 测试（Round 1211）。

补强 edges213 未触及的角度（第五百八十三批，probe 实证）。

新角度（空夹页透明 / 转义括号解码）：
- **空夹页透明**——3 页文档中页 2 完
  全空白 → 仅 2 个 paragraph 元素，
  locator 页码 [1, 3] 跳过 2（空页
  不产元素、不占序、页码照跳首锁）
- **转义括号解码**——Tj 串 \\( \\) →
  文本 "(escaped parens)"（PDF 字符
  串转义序列解码首锁；marker 可含
  括号）
- **四块结构**——mc60：每行一块各
  1 源（39+1+31 > 60 不合流）
- **三界锚**——单锚 → P 1/3 / R
  1.0 / F1 0.5；重复 "page" ×2 →
  2/3 / 1.0 / 0.8；流尾 "follows."
  （距末界 34 > 30）→ 全 0.0
- forbidden tokens 第六百八十一批（open 2）
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


_R1 = b"BT /F1 12 Tf 10 700 Td (First page with " \
      b"\\(escaped parens\\) here.) Tj ET\n" \
      b"BT /F1 12 Tf 10 680 Td (Second line of page one text.) " \
      b"Tj ET\n"
_R3 = b"BT /F1 12 Tf 10 700 Td (Third page after empty page " \
      b"two.) Tj ET\n" \
      b"BT /F1 12 Tf 10 680 Td (More text on page three " \
      b"follows.) Tj ET\n"

_L1 = "First page with (escaped parens) here."
_L2 = "Second line of page one text."
_L3 = "Third page after empty page two."
_L4 = "More text on page three follows."


def _pdf() -> bytes:
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 5 0 R 7 0 R]/Count 3>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 9 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(_R1)).encode()
            + b">>stream\n" + _R1 + b"\nendstream "),
        5: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 9 0 R>>>>/Contents 6 0 R>>"),
        6: b"<</Length 0>>stream\n\nendstream ",
        7: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 9 0 R>>>>/Contents 8 0 R>>"),
        8: (b"<</Length " + str(len(_R3)).encode()
            + b">>stream\n" + _R3 + b"\nendstream "),
        9: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 10)


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


def _pdf_path(tmp_path, doc_id):
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "s" / f"{doc_id}.pdf").write_bytes(_pdf())
    return tmp_path / "s" / f"{doc_id}.pdf"


# ---------- 空夹页透明 ----------

def test_empty_middle_page_transparent_batch409(tmp_path):
    doc, errors = process_single(
        _pdf_path(tmp_path, "em"), tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == ["paragraph"] * 2
    assert [e["source_locator"]["page"] for e in els] == [1, 3]
    assert els[0]["content"] == _L1 + " " + _L2
    assert els[1]["content"] == _L3 + " " + _L4


def test_escaped_parens_decoded_batch409(tmp_path):
    doc, errors = process_single(
        _pdf_path(tmp_path, "ep"), tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert "(escaped parens)" in els[0]["content"]


def test_chunks_four_batch409(tmp_path):
    doc, errors = process_single(
        _pdf_path(tmp_path, "cf"), tmp_path / "o.json",
        parser_name="fallback", max_chars=60)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert [c["text"] for c in chunks] == [_L1, _L2, _L3, _L4]
    assert all(len(c["source_element_ids"]) == 1
               for c in chunks)


# ---------- 锚 ----------

def test_here_anchor_batch409(tmp_path):
    r = run_evaluation(_board(tmp_path, "a1", [
        {"marker": "here.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=60)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.3333333333333333, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.5, "reason": None}


def test_follows_anchor_batch409(tmp_path):
    r = run_evaluation(_board(tmp_path, "a2", [
        {"marker": "follows.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=60)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.0, "reason": None}


def test_page_anchor_batch409(tmp_path):
    r = run_evaluation(_board(tmp_path, "a3", [
        {"marker": "page", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=60)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.3333333333333333, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.5, "reason": None}


def test_page_twice_anchor_batch409(tmp_path):
    r = run_evaluation(_board(tmp_path, "a4", [
        {"marker": "page", "position": "after"},
        {"marker": "page", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=60)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.6666666666666666, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.8, "reason": None}


def test_parens_marker_batch409(tmp_path):
    r = run_evaluation(_board(tmp_path, "a5", [
        {"marker": "(escaped parens)", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=60)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.3333333333333333, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.5, "reason": None}


# ---------- 指标 ----------

def test_metrics_batch409(tmp_path):
    r = run_evaluation(_board(tmp_path, "mx"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=60)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 2}, "reason": None}
    assert m["heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch409():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百八十一批 ----------

def test_source_no_eval_batch409():
    assert "eval(" not in _src()


def test_source_no_exec_batch409():
    assert "exec(" not in _src()


def test_source_no_compile_batch409():
    assert "compile(" not in _src()


def test_source_no_globals_batch409():
    assert "globals(" not in _src()


def test_source_no_locals_batch409():
    assert "locals(" not in _src()


def test_source_no_os_system_batch409():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch409():
    assert "subprocess" not in _src()


def test_source_no_popen_batch409():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch409():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch409():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch409():
    assert "socket" not in _src()


def test_source_no_requests_batch409():
    assert "requests" not in _src()


def test_source_no_urllib_batch409():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch409():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch409():
    assert "yield" not in _src()


def test_source_no_async_await_batch409():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch409():
    assert _src().count("open(") == 2
