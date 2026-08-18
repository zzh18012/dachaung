"""evaluation/runner.py 第六百一十七轮 edges 测试（Round 1173）。

补强 edges186 未触及的角度（第五百四十五批，probe 实证）。

新角度（跨页文本流 / 页界即题界）：
- **跨页同流**——两页各两段纯文本 → 单
  sequential 块 4 源——页界不清空顺序缓冲区
  （跨页合流首锁）
- **页界即题界**——页 2 首元素为 heading → 块界
  恰落页界：chunks [seq(页 1 两段), seq(题+段)]
- **short_line 题元数据**——PDF 短行无句读 →
  heading + {"level": 0, "heuristic":
  "short_line"}（runner 级全管道首锁）
- **双侧锚皆中**——"here." after（页 1 尾向后）
  与 "Page Two Heading" before（页 2 首向前）
  GT 均恰落同一界 → P/R/F1 全 1.0
- forbidden tokens 第六百四十五批（open 2）
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


def _two_page_pdf(heading_page2: bool) -> bytes:
    s1 = (b"BT /F1 12 Tf 10 750 Td "
          b"(First page opening line with period.) Tj ET\n"
          b"BT /F1 12 Tf 10 700 Td "
          b"(First page closing line here.) Tj ET\n")
    if heading_page2:
        s2 = (b"BT /F1 12 Tf 10 750 Td "
              b"(Page Two Heading) Tj ET\n"
              b"BT /F1 12 Tf 10 700 Td "
              b"(Second page body text follows.) Tj ET\n")
    else:
        s2 = (b"BT /F1 12 Tf 10 750 Td "
              b"(Second page continuation text.) Tj ET\n"
              b"BT /F1 12 Tf 10 700 Td "
              b"(Second page final line now.) Tj ET\n")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 5 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 800]"
            b"/Resources<</Font<</F1 7 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
        5: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 800]"
            b"/Resources<</Font<</F1 7 0 R>>>>/Contents 6 0 R>>"),
        6: (b"<</Length " + str(len(s2)).encode()
            + b">>stream\n" + s2 + b"\nendstream "),
        7: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 8)


def _board(tmp_path, doc_id, anchors=None, heading_page2=True):
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "a").mkdir(exist_ok=True)
    (tmp_path / "s" / f"{doc_id}.pdf").write_bytes(
        _two_page_pdf(heading_page2))
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


# ---------- 跨页同流 ----------

def test_cross_page_single_chunk_batch371(tmp_path):
    _board(tmp_path, "xp", heading_page2=False)
    doc, errors = process_single(
        tmp_path / "s" / "xp.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    dd = doc.to_dict()
    assert [e["type"] for e in dd["elements"]] == [
        "paragraph"] * 4
    assert [e["source_locator"]["page"]
            for e in dd["elements"]] == [1, 1, 2, 2]
    chunks = dd["chunks"]
    assert [c["metadata"]["strategy"] for c in chunks] == [
        "sequential"]
    assert len(chunks[0]["source_element_ids"]) == 4
    assert chunks[0]["text"] == (
        "First page opening line with period. "
        "First page closing line here. "
        "Second page continuation text. "
        "Second page final line now.")


# ---------- 页界即题界 ----------

def test_page_junction_elements_batch371(tmp_path):
    _board(tmp_path, "xp2", heading_page2=True)
    doc, errors = process_single(
        tmp_path / "s" / "xp2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == [
        "paragraph", "paragraph", "heading", "paragraph"]
    assert els[2]["content"] == "Page Two Heading"
    assert els[2]["metadata"] == {
        "level": 0, "heuristic": "short_line"}
    assert els[2]["source_locator"]["page"] == 2


def test_page_junction_chunks_batch371(tmp_path):
    _board(tmp_path, "xp3", heading_page2=True)
    doc, errors = process_single(
        tmp_path / "s" / "xp3.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert [c["metadata"]["strategy"] for c in chunks] == [
        "sequential", "sequential"]
    assert chunks[0]["text"] == (
        "First page opening line with period. "
        "First page closing line here.")
    assert chunks[1]["text"] == (
        "Page Two Heading Second page body text follows.")
    assert all(len(c["source_element_ids"]) == 2
               for c in chunks)


# ---------- 双侧锚皆中 ----------

def test_page_junction_prf_batch371(tmp_path):
    r = run_evaluation(_board(tmp_path, "xp4", [
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


def test_heading_before_prf_batch371(tmp_path):
    r = run_evaluation(_board(tmp_path, "xp5", [
        {"marker": "Page Two Heading", "position": "before"}]),
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

def test_page_board_by_type_batch371(tmp_path):
    r = run_evaluation(_board(tmp_path, "xp6"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 3, "heading": 1},
        "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch371():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("per_doc") == 12
    assert src.count("annotation") == 10


# ---------- forbidden tokens 第六百四十五批 ----------

def test_source_no_eval_batch371():
    assert "eval(" not in _src()


def test_source_no_exec_batch371():
    assert "exec(" not in _src()


def test_source_no_compile_batch371():
    assert "compile(" not in _src()


def test_source_no_globals_batch371():
    assert "globals(" not in _src()


def test_source_no_locals_batch371():
    assert "locals(" not in _src()


def test_source_no_os_system_batch371():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch371():
    assert "subprocess" not in _src()


def test_source_no_popen_batch371():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch371():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch371():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch371():
    assert "socket" not in _src()


def test_source_no_requests_batch371():
    assert "requests" not in _src()


def test_source_no_urllib_batch371():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch371():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch371():
    assert "yield" not in _src()


def test_source_no_async_await_batch371():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch371():
    assert _src().count("open(") == 2
