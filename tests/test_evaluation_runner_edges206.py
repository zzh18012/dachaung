"""evaluation/runner.py 第六百三十九轮 edges 测试（Round 1195）。

补强 edges205 未触及的角度（第五百六十七批，probe 实证）。

新角度（跨页续表 / 页内类先于序）：
- **表不跨页续**——两页各一格网 →
  两个独立 table 元素（表检测按页，
  不合并续表首锁）
- **页内类先于序**——元素序 [题 p1,
  段 p1, 表 p1, 题 p2, 段 p2, 表 p2]
  （页为外键、页内文本类按 y 先于表，
  全局 text-then-table 的页级修正首锁）
- **四块交错**——[seq(题+段 2 源),
  iso_表, seq(题+段 2 源), iso_表]
  （孤立表中断顺序缓冲区）
- **重复锚双现**——"grid." ×1 →
  P 1/3 / R 1.0 / F1 0.5；×2 顺流
  双挂 → P 2/3 / R 1.0 / F1 0.8
- forbidden tokens 第六百六十七批（open 2）
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


def _page(a, b, p) -> bytes:
    return (b"1 w 0 G\n"
            b"10 300 100 50 re S\n60 300 0 50 re S\n"
            b"10 350 100 0 re S\n"
            + ("BT /F1 10 Tf 15 325 Td (%s) Tj ET\n" % a).encode()
            + ("BT /F1 10 Tf 65 325 Td (%s) Tj ET\n" % b).encode()
            + ("BT /F1 12 Tf 10 100 Td (%s) Tj ET\n" % p).encode())


def _pdf() -> bytes:
    s1 = _page("Ga", "Gb", "First page text after grid.")
    s2 = _page("Gc", "Gd", "Second page text after grid.")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 5 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 400]"
            b"/Resources<</Font<</F1 7 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
        5: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 400]"
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


# ---------- 表不跨页续 ----------

def test_crosspage_elements_batch393(tmp_path):
    _board(tmp_path, "cp")
    doc, errors = process_single(
        tmp_path / "s" / "cp.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == [
        "heading", "paragraph", "table",
        "heading", "paragraph", "table"]
    assert [e["source_locator"]["page"] for e in els] == [
        1, 1, 1, 2, 2, 2]


def test_crosspage_tables_batch393(tmp_path):
    _board(tmp_path, "cp2")
    doc, errors = process_single(
        tmp_path / "s" / "cp2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert els[2]["content"] == "| Ga | Gb |\n| --- | --- |"
    assert els[5]["content"] == "| Gc | Gd |\n| --- | --- |"
    assert els[2]["source_locator"]["bbox"] == [
        10.0, 50.0, 110.0, 100.0]
    assert els[5]["source_locator"]["bbox"] == [
        10.0, 50.0, 110.0, 100.0]


# ---------- 四块交错 ----------

def test_crosspage_chunks_batch393(tmp_path):
    _board(tmp_path, "cp3")
    doc, errors = process_single(
        tmp_path / "s" / "cp3.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert [c["metadata"]["strategy"] for c in chunks] == [
        "sequential", "isolated_table",
        "sequential", "isolated_table"]
    assert chunks[0]["text"] == "Ga Gb First page text after grid."
    assert chunks[2]["text"] == \
        "Gc Gd Second page text after grid."
    assert [len(c["source_element_ids"]) for c in chunks] == [
        2, 1, 2, 1]


# ---------- 重复锚双现 ----------

def test_crosspage_single_anchor_batch393(tmp_path):
    r = run_evaluation(_board(tmp_path, "cp4", [
        {"marker": "grid.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.3333333333333333, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.5, "reason": None}


def test_crosspage_double_anchor_batch393(tmp_path):
    r = run_evaluation(_board(tmp_path, "cp5", [
        {"marker": "grid.", "position": "after"},
        {"marker": "grid.", "position": "after"}]),
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

def test_crosspage_metrics_batch393(tmp_path):
    r = run_evaluation(_board(tmp_path, "cp6"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 2, "paragraph": 2, "table": 2},
        "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}
    assert m["element_count_total"] == {"value": 6,
                                        "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch393():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百六十七批 ----------

def test_source_no_eval_batch393():
    assert "eval(" not in _src()


def test_source_no_exec_batch393():
    assert "exec(" not in _src()


def test_source_no_compile_batch393():
    assert "compile(" not in _src()


def test_source_no_globals_batch393():
    assert "globals(" not in _src()


def test_source_no_locals_batch393():
    assert "locals(" not in _src()


def test_source_no_os_system_batch393():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch393():
    assert "subprocess" not in _src()


def test_source_no_popen_batch393():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch393():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch393():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch393():
    assert "socket" not in _src()


def test_source_no_requests_batch393():
    assert "requests" not in _src()


def test_source_no_urllib_batch393():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch393():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch393():
    assert "yield" not in _src()


def test_source_no_async_await_batch393():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch393():
    assert _src().count("open(") == 2
