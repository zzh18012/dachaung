"""evaluation/runner.py 第六百三十七轮 edges 测试（Round 1193）。

补强 edges203 未触及的角度（第五百六十五批，probe 实证）。

新角度（参差表格的空格补齐）：
- **4 列头 2 列体**——上半 4 格下半
  2 格的格网 → markdown 全 4 列，
  下行 "| W1 |  | W2 |  |"（合并跨
  列文字落入首列、余列补空首锁）
- **格字双现**——六字母既成独立
  heading "H1 H2 H3 H4 W1 W2"
  （y 315 与 290 两行合流）
- **row/col 计数**——{row_count: 2,
  col_count: 4}（按最大列宽计）
- forbidden tokens 第六百六十五批（open 2）
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


_MD = ("| H1 | H2 | H3 | H4 |\n"
       "| --- | --- | --- | --- |\n"
       "| W1 |  | W2 |  |")


def _pdf() -> bytes:
    def T(text, x, y):
        return ("BT /F1 10 Tf %d %d Td (%s) Tj ET\n"
                % (x, y, text)).encode()
    s = (b"1 w 0 G\n"
         b"10 280 150 60 re S\n"
         b"85 280 0 60 re S\n"
         b"47 310 0 30 re S\n"
         b"123 310 0 30 re S\n"
         b"10 310 150 0 re S\n"
         + T("H1", 20, 315) + T("H2", 57, 315)
         + T("H3", 95, 315) + T("H4", 133, 315)
         + T("W1", 40, 290) + T("W2", 115, 290))
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 400]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 6)


def _board(tmp_path, doc_id, expectations=None, anchors=None):
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "a").mkdir(exist_ok=True)
    (tmp_path / "s" / f"{doc_id}.pdf").write_bytes(_pdf())
    entry = {"doc_id": doc_id, "path": f"s/{doc_id}.pdf",
             "source_type": "pdf"}
    if expectations is not None:
        entry["expectations"] = expectations
    if anchors is not None:
        (tmp_path / "a" / "a.json").write_text(json.dumps({
            "annotation_version": "1.0", "doc_id": doc_id,
            "chunk_boundary_anchors": anchors}),
            encoding="utf-8")
        entry["annotation_file"] = "a/a.json"
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": [entry]}),
                  encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 参差补齐 ----------

def test_ragged_table_markdown_batch391(tmp_path):
    _board(tmp_path, "rg")
    doc, errors = process_single(
        tmp_path / "s" / "rg.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == ["heading", "table"]
    assert els[1]["content"] == _MD


def test_ragged_dual_heading_batch391(tmp_path):
    _board(tmp_path, "rg2")
    doc, errors = process_single(
        tmp_path / "s" / "rg2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert els[0]["content"] == "H1 H2 H3 H4 W1 W2"
    assert els[0]["metadata"] == {
        "level": 0, "heuristic": "short_line"}


def test_ragged_table_meta_batch391(tmp_path):
    _board(tmp_path, "rg3")
    doc, errors = process_single(
        tmp_path / "s" / "rg3.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert els[1]["metadata"] == {
        "row_count": 2, "col_count": 4,
        "source": "pdfplumber"}


def test_ragged_chunks_batch391(tmp_path):
    _board(tmp_path, "rg4")
    doc, errors = process_single(
        tmp_path / "s" / "rg4.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert [c["metadata"]["strategy"] for c in chunks] == [
        "sequential", "isolated_table"]
    assert chunks[0]["text"] == "H1 H2 H3 H4 W1 W2"
    assert chunks[1]["text"] == _MD
    assert all(len(c["source_element_ids"]) == 1
               for c in chunks)


# ---------- 锚 ----------

def test_ragged_w2_anchor_batch391(tmp_path):
    r = run_evaluation(_board(tmp_path, "rg5", None, [
        {"marker": "W2", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_ragged_w1_anchor_batch391(tmp_path):
    r = run_evaluation(_board(tmp_path, "rg6", None, [
        {"marker": "W1", "position": "after"}]),
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

def test_ragged_metrics_batch391(tmp_path):
    r = run_evaluation(_board(tmp_path, "rg7"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "table": 1},
        "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


def test_ragged_silent_drop_batch391(tmp_path):
    r = run_evaluation(_board(tmp_path, "rg8", {
        "element_count_by_type": {"heading": 1, "table": 1}}),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["silent_drop_count"] == {"value": 0,
                                      "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch391():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百六十五批 ----------

def test_source_no_eval_batch391():
    assert "eval(" not in _src()


def test_source_no_exec_batch391():
    assert "exec(" not in _src()


def test_source_no_compile_batch391():
    assert "compile(" not in _src()


def test_source_no_globals_batch391():
    assert "globals(" not in _src()


def test_source_no_locals_batch391():
    assert "locals(" not in _src()


def test_source_no_os_system_batch391():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch391():
    assert "subprocess" not in _src()


def test_source_no_popen_batch391():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch391():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch391():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch391():
    assert "socket" not in _src()


def test_source_no_requests_batch391():
    assert "requests" not in _src()


def test_source_no_urllib_batch391():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch391():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch391():
    assert "yield" not in _src()


def test_source_no_async_await_batch391():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch391():
    assert _src().count("open(") == 2
