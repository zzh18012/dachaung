"""evaluation/runner.py 第五百九十轮 edges 测试（Round 1147）。

补强 edges164 未触及的角度（第五百二十批，probe 实证）。

新角度（标注 × 表格 markdown 通道）：
- **表格 markdown 可作 marker**——真画线表格板，marker
  "| C1 | D1 |" after 恰落 heading 块与表格块交界 d=0 →
  P/R/F1 全 1.0——标注匹配不限于自然文本，表格块
  markdown 进拼接流（首锁）
- **表格块边界即锚点**——marker 跨在 isolated_table
  块的起点上，边界由 caption/表格隔离 flush 产生
- forbidden tokens 第六百一十九批（open 2）
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


def _table_pdf() -> bytes:
    s = (b"1 w 0 G\n"
         b"10 10 100 50 re S\n"
         b"60 10 0 50 re S\n"
         b"10 35 100 0 re S\n"
         b"BT /F1 10 Tf 15 55 Td (C1) Tj ET\n"
         b"BT /F1 10 Tf 65 55 Td (D1) Tj ET")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</Font<</F1 5 0 R>>>>"
            b"/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 6)


def _board(tmp_path, doc_id):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "anns").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(
        _table_pdf())
    (tmp_path / "anns" / f"{doc_id}.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": doc_id,
        "chunk_boundary_anchors": [
            {"marker": "| C1 | D1 |", "position": "after"}]}),
        encoding="utf-8")
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id,
                       "path": f"samples/{doc_id}.pdf",
                       "source_type": "pdf",
                       "annotation_file":
                           f"anns/{doc_id}.json"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 表格 markdown 可作 marker ----------

def test_table_markdown_marker_batch345(tmp_path):
    _board(tmp_path, "tm")
    doc, errors = process_single(
        tmp_path / "samples" / "tm.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert len(chunks) == 2
    assert chunks[0]["text"] == "C1 D1"
    assert chunks[1]["text"].startswith("| C1 | D1 |")


def test_table_marker_metrics_batch345(tmp_path):
    r = run_evaluation(_board(tmp_path, "tm2"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert m[k] == {"value": 1.0, "reason": None}


def test_table_marker_missing_shape_batch345(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "anns").mkdir(exist_ok=True)
    (tmp_path / "samples" / "tm3.pdf").write_bytes(_table_pdf())
    (tmp_path / "anns" / "tm3.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "tm3",
        "chunk_boundary_anchors": [
            {"marker": "| NOPE | ROW |", "position": "after"}]}),
        encoding="utf-8")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "tm3",
                       "path": "samples/tm3.pdf",
                       "source_type": "pdf",
                       "annotation_file": "anns/tm3.json"}]}),
        encoding="utf-8")
    r = run_evaluation(load_manifest(mf, project_root=tmp_path),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch345():
    src = _src()
    assert src.count("process_single") == 6
    assert src.count("chunk") == 9


# ---------- forbidden tokens 第六百一十九批 ----------

def test_source_no_eval_batch345():
    assert "eval(" not in _src()


def test_source_no_exec_batch345():
    assert "exec(" not in _src()


def test_source_no_compile_batch345():
    assert "compile(" not in _src()


def test_source_no_globals_batch345():
    assert "globals(" not in _src()


def test_source_no_locals_batch345():
    assert "locals(" not in _src()


def test_source_no_os_system_batch345():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch345():
    assert "subprocess" not in _src()


def test_source_no_popen_batch345():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch345():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch345():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch345():
    assert "socket" not in _src()


def test_source_no_requests_batch345():
    assert "requests" not in _src()


def test_source_no_urllib_batch345():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch345():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch345():
    assert "yield" not in _src()


def test_source_no_async_await_batch345():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch345():
    assert _src().count("open(") == 2
