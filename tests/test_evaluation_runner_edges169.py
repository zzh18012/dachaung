"""evaluation/runner.py 第五百九十六轮 edges 测试（Round 1152）。

补强 edges168 未触及的角度（第五百二十四批，probe 实证）。

新角度（三列网格 / 表内 marker 失配）：
- **2×3 网格真表**——三条竖线四横线构成 3 列 2 行 →
  col_count 3 首锁（历史网格全 2 列），markdown
  逐列齐 "| A1 | B1 | C1 |…| A2 | B2 | C2 |"
- **六格字单 heading**——两行格字纵向 25pt 差仍
  同流合并 → 单 heading "A1 B1 C1 A2 B2 C2"
- **跨行 span marker**——marker "C1 A2"（跨表两行
  的字流连接处）after → F1 1.0
- **表内 markdown marker 不中界**——marker
  "| A2 | B2 |" 在 isolated 表块内部命中文本但
  非块边界 → F1 0.0 / reason None（与 edges165
  边界命中 1.0 成对照，matched-but-mid-chunk 首锁）
- forbidden tokens 第六百二十四批（open 2）
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


def _three_col_pdf() -> bytes:
    s = (b"1 w 0 G\n"
         b"10 10 120 0 re S\n10 35 120 0 re S\n10 60 120 0 re S\n"
         b"10 10 0 50 re S\n50 10 0 50 re S\n"
         b"90 10 0 50 re S\n130 10 0 50 re S\n"
         b"BT /F1 10 Tf 15 45 Td (A1) Tj ET\n"
         b"BT /F1 10 Tf 55 45 Td (B1) Tj ET\n"
         b"BT /F1 10 Tf 95 45 Td (C1) Tj ET\n"
         b"BT /F1 10 Tf 15 20 Td (A2) Tj ET\n"
         b"BT /F1 10 Tf 55 20 Td (B2) Tj ET\n"
         b"BT /F1 10 Tf 95 20 Td (C2) Tj ET")
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


def _board(tmp_path, doc_id, marker=None):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "anns").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(
        _three_col_pdf())
    doc_entry = {"doc_id": doc_id,
                 "path": f"samples/{doc_id}.pdf",
                 "source_type": "pdf"}
    if marker is not None:
        (tmp_path / "anns" / "a.json").write_text(json.dumps({
            "annotation_version": "1.0", "doc_id": doc_id,
            "chunk_boundary_anchors": [
                {"marker": marker, "position": "after"}]}),
            encoding="utf-8")
        doc_entry["annotation_file"] = "anns/a.json"
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [doc_entry]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 2×3 网格真表 ----------

def test_three_col_table_metadata_batch350(tmp_path):
    _board(tmp_path, "tc")
    doc, errors = process_single(
        tmp_path / "samples" / "tc.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    tables = [e for e in doc.to_dict()["elements"]
              if e["type"] == "table"]
    assert len(tables) == 1
    assert tables[0]["content"] == (
        "| A1 | B1 | C1 |\n| --- | --- | --- |\n| A2 | B2 | C2 |")
    assert tables[0]["metadata"] == {
        "row_count": 2, "col_count": 3, "source": "pdfplumber"}


# ---------- 六格字单 heading ----------

def test_six_cells_single_heading_batch350(tmp_path):
    _board(tmp_path, "tc2")
    doc, errors = process_single(
        tmp_path / "samples" / "tc2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == ["heading", "table"]
    assert els[0]["content"] == "A1 B1 C1 A2 B2 C2"


def test_three_col_chunks_batch350(tmp_path):
    _board(tmp_path, "tc3")
    doc, errors = process_single(
        tmp_path / "samples" / "tc3.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert [c["metadata"]["strategy"] for c in chunks] == \
        ["sequential", "isolated_table"]
    assert len(chunks[1]["source_element_ids"]) == 1


# ---------- 跨行 span marker ----------

def test_cross_row_marker_hit_batch350(tmp_path):
    r = run_evaluation(_board(tmp_path, "tc4", marker="C1 A2"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_f1"] == {"value": 1.0,
                                      "reason": None}


# ---------- 表内 markdown marker 不中界 ----------

def test_midtable_marker_miss_batch350(tmp_path):
    r = run_evaluation(
        _board(tmp_path, "tc5", marker="| A2 | B2 |"),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_f1"] == {"value": 0.0,
                                      "reason": None}


def test_midtable_marker_recall_batch350(tmp_path):
    r = run_evaluation(
        _board(tmp_path, "tc6", marker="| A2 | B2 |"),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_recall"] == {"value": 0.0,
                                          "reason": None}
    assert m["chunk_boundary_precision"] == {"value": 0.0,
                                             "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch350():
    src = _src()
    assert src.count("per_doc") == 12
    assert src.count("manifest") == 5
    assert src.count("expected_failure") == 5


# ---------- forbidden tokens 第六百二十四批 ----------

def test_source_no_eval_batch350():
    assert "eval(" not in _src()


def test_source_no_exec_batch350():
    assert "exec(" not in _src()


def test_source_no_compile_batch350():
    assert "compile(" not in _src()


def test_source_no_globals_batch350():
    assert "globals(" not in _src()


def test_source_no_locals_batch350():
    assert "locals(" not in _src()


def test_source_no_os_system_batch350():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch350():
    assert "subprocess" not in _src()


def test_source_no_popen_batch350():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch350():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch350():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch350():
    assert "socket" not in _src()


def test_source_no_requests_batch350():
    assert "requests" not in _src()


def test_source_no_urllib_batch350():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch350():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch350():
    assert "yield" not in _src()


def test_source_no_async_await_batch350():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch350():
    assert _src().count("open(") == 2
