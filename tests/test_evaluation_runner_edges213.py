"""evaluation/runner.py 第六百四十八轮 edges 测试（Round 1205）。

补强 edges212 未触及的角度（第五百七十七批，probe 实证）。

新角度（并排双表不合并 / Tj 前后空白归一）：
- **并排双表**——左格网（x 10..110）与
  右格网（x 200..300）同 y 带 → 两个
  独立 table 元素（x 空档阻断表合并
  首锁）；格字双现为单条 heading
  "LA LB RA RB LC LD RC RD"
- **三块结构**——[heading seq, 左表
  iso, 右表 iso] 各 1 源；mc200 与
  mc50 相同
- **双界锚半查**——3 块 2 预测界，单
  锚 → P 0.5 / R 1.0 / F1 2/3；重复
  "LA"（heading 与 md1 双现）→ 一对
  一耗尽 → 0.5/0.5/0.5
- **Tj 前后空白归一**——"(  Hello
  padded   world  )" → 行内容
  "Hello padded world"（strip + 内部
  压单空格首锁）
- forbidden tokens 第六百七十六批（open 2）
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


_H = "LA LB RA RB LC LD RC RD"
_MD1 = "| LA | LB |\n| --- | --- |\n| LC | LD |"
_MD2 = "| RA | RB |\n| --- | --- |\n| RC | RD |"


def _side_pdf() -> bytes:
    s = (b"1 w 0 G\n"
         + b"10 300 100 60 re S\n" + b"60 300 0 60 re S\n"
         + b"10 330 100 0 re S\n"
         + b"200 300 100 60 re S\n" + b"250 300 0 60 re S\n"
         + b"200 330 100 0 re S\n"
         + _T("LA", 15, 340) + _T("LB", 65, 340)
         + _T("LC", 15, 310) + _T("LD", 65, 310)
         + _T("RA", 205, 340) + _T("RB", 255, 340)
         + _T("RC", 205, 310) + _T("RD", 255, 310))
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 6)


def _pad_pdf() -> bytes:
    s = (b"BT /F1 12 Tf 10 700 Td "
         b"(  Hello   padded   world  ) Tj ET\n"
         b"BT /F1 12 Tf 10 650 Td (plain line here.) Tj ET\n")
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
    pdf = _side_pdf() if mode == "side" else _pad_pdf()
    (tmp_path / "s" / f"{doc_id}.pdf").write_bytes(pdf)
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


def _pdf(tmp_path, doc_id, mode):
    pdf = _side_pdf() if mode == "side" else _pad_pdf()
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "s" / f"{doc_id}.pdf").write_bytes(pdf)
    return tmp_path / "s" / f"{doc_id}.pdf"


# ---------- 并排双表 ----------

def test_side_by_side_tables_batch403(tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path, "sb", "side"), tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == ["heading", "table", "table"]
    assert els[0]["content"] == _H
    assert els[1]["content"] == _MD1
    assert els[2]["content"] == _MD2


def test_side_by_side_counts_batch403(tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path, "cn", "side"), tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    for e in els[1:]:
        assert e["metadata"]["row_count"] == 2
        assert e["metadata"]["col_count"] == 2


def test_side_by_side_chunks_batch403(tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path, "ck", "side"), tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert [c["text"] for c in chunks] == [_H, _MD1, _MD2]
    assert [c["metadata"]["strategy"] for c in chunks] == [
        "sequential", "isolated_table", "isolated_table"]
    assert all(len(c["source_element_ids"]) == 1
               for c in chunks)


# ---------- Tj 前后空白归一 ----------

def test_padded_normalize_batch403(tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path, "pn", "pad"), tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == ["heading", "paragraph"]
    assert els[0]["content"] == "Hello padded world"
    assert els[1]["content"] == "plain line here."


def test_padded_chunks_merged_batch403(tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path, "pm", "pad"), tmp_path / "o.json",
        parser_name="fallback", max_chars=50)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert [c["text"] for c in chunks] == [
        "Hello padded world plain line here."]
    assert len(chunks[0]["source_element_ids"]) == 2


def test_padded_chunks_split_batch403(tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path, "ps", "pad"), tmp_path / "o.json",
        parser_name="fallback", max_chars=32)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert [c["text"] for c in chunks] == [
        "Hello padded world", "plain line here."]
    assert [len(c["text"]) for c in chunks] == [18, 16]
    assert all(len(c["source_element_ids"]) == 1
               for c in chunks)


# ---------- 锚 ----------

def test_side_anchor_la_batch403(tmp_path):
    r = run_evaluation(_board(tmp_path, "a1", "side", [
        {"marker": "LA", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


def test_side_anchor_dup_batch403(tmp_path):
    r = run_evaluation(_board(tmp_path, "a2", "side", [
        {"marker": "LA", "position": "after"},
        {"marker": "LA", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.5, "reason": None}


def test_side_anchor_pipe_batch403(tmp_path):
    r = run_evaluation(_board(tmp_path, "a3", "side", [
        {"marker": "LC |", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


def test_padded_anchor_world_batch403(tmp_path):
    r = run_evaluation(_board(tmp_path, "a4", "pad", [
        {"marker": "world", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=32)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_padded_anchor_here_batch403(tmp_path):
    r = run_evaluation(_board(tmp_path, "a5", "pad", [
        {"marker": "here.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=32)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_padded_anchor_merged_null_batch403(tmp_path):
    r = run_evaluation(_board(tmp_path, "a6", "pad", [
        {"marker": "world", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert m["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": None, "reason": "no_predicted_boundaries"}


# ---------- 指标 ----------

def test_side_metrics_batch403(tmp_path):
    r = run_evaluation(_board(tmp_path, "mx", "side"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "table": 2}, "reason": None}
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


def test_padded_metrics_batch403(tmp_path):
    r = run_evaluation(_board(tmp_path, "mp", "pad"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "paragraph": 1}, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch403():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百七十六批 ----------

def test_source_no_eval_batch403():
    assert "eval(" not in _src()


def test_source_no_exec_batch403():
    assert "exec(" not in _src()


def test_source_no_compile_batch403():
    assert "compile(" not in _src()


def test_source_no_globals_batch403():
    assert "globals(" not in _src()


def test_source_no_locals_batch403():
    assert "locals(" not in _src()


def test_source_no_os_system_batch403():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch403():
    assert "subprocess" not in _src()


def test_source_no_popen_batch403():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch403():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch403():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch403():
    assert "socket" not in _src()


def test_source_no_requests_batch403():
    assert "requests" not in _src()


def test_source_no_urllib_batch403():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch403():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch403():
    assert "yield" not in _src()


def test_source_no_async_await_batch403():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch403():
    assert _src().count("open(") == 2
