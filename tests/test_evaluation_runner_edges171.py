"""evaluation/runner.py 第五百九十八轮 edges 测试（Round 1154）。

补强 edges170 未触及的角度（第五百二十六批，probe 实证）。

新角度（隔离优先于 max_chars / 末尾无边界）：
- **超限表格整体成块**——2×2 格 markdown 49 字符
  @ max_chars 32 → 单 isolated_table 块全文不劈
  （chunker 隔离通道绕过长度上限，runner 级首锁）
- **超限 caption 整体成块**——71 字符 caption
  @ 32 → 单 isolated_caption 块 len 71
- **末尾无边界**——marker 落流绝对末尾（最后一块
  结束处）→ F1 0.0 / reason None——块间才有边界，
  末块之后无预测边界（首锁）
- forbidden tokens 第六百二十六批（open 2）
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


def _grid_pdf() -> bytes:
    s = (b"1 w 0 G\n"
         b"10 40 100 40 re S\n60 40 0 40 re S\n10 60 100 0 re S\n"
         b"BT /F1 10 Tf 15 65 Td (Aa Bb) Tj ET\n"
         b"BT /F1 10 Tf 65 65 Td (Cc Dd) Tj ET\n"
         b"BT /F1 10 Tf 15 45 Td (Ee Ff) Tj ET\n"
         b"BT /F1 10 Tf 65 45 Td (Gg Hh) Tj ET")
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


def _caption_pdf() -> bytes:
    s = (b"BT /F1 10 Tf 10 80 Td "
         b"(Figure 1: a caption line long enough to exceed "
         b"the tiny limit set here.) Tj ET")
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


def _board(tmp_path, doc_id, pdf, marker=None):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "anns").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(pdf)
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


# ---------- 超限表格整体成块 ----------

def test_oversized_table_single_chunk_batch352(tmp_path):
    _board(tmp_path, "ot", _grid_pdf())
    doc, errors = process_single(
        tmp_path / "samples" / "ot.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=32)
    assert errors == []
    md = [e for e in doc.to_dict()["elements"]
          if e["type"] == "table"][0]["content"]
    assert len(md) > 32
    chunks = doc.to_dict()["chunks"]
    assert len(chunks) == 2
    assert chunks[1]["metadata"]["strategy"] == "isolated_table"
    assert len(chunks[1]["text"]) == len(md) > 32
    assert chunks[1]["text"] == md
    assert len(chunks[1]["source_element_ids"]) == 1


# ---------- 超限 caption 整体成块 ----------

def test_oversized_caption_single_chunk_batch352(tmp_path):
    _board(tmp_path, "oc", _caption_pdf())
    doc, errors = process_single(
        tmp_path / "samples" / "oc.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=32)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert len(chunks) == 1
    assert chunks[0]["metadata"]["strategy"] == "isolated_caption"
    assert len(chunks[0]["text"]) == 71 > 32


# ---------- 超限板指标 ----------

def test_oversized_table_metrics_batch352(tmp_path):
    r = run_evaluation(_board(tmp_path, "ot2", _grid_pdf()),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=32)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "table": 1}, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["pipeline_success"] == {"value": True, "reason": None}


# ---------- 末尾无边界 ----------

def test_trailing_marker_miss_batch352(tmp_path):
    r = run_evaluation(
        _board(tmp_path, "ot3", _grid_pdf(),
               marker="| Gg Hh |"),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=32)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_f1"] == {"value": 0.0,
                                      "reason": None}
    assert m["chunk_boundary_precision"] == {"value": 0.0,
                                             "reason": None}
    assert m["chunk_boundary_recall"] == {"value": 0.0,
                                          "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch352():
    src = _src()
    assert src.count("process_single") == 6
    assert src.count("metrics") == 13
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百二十六批 ----------

def test_source_no_eval_batch352():
    assert "eval(" not in _src()


def test_source_no_exec_batch352():
    assert "exec(" not in _src()


def test_source_no_compile_batch352():
    assert "compile(" not in _src()


def test_source_no_globals_batch352():
    assert "globals(" not in _src()


def test_source_no_locals_batch352():
    assert "locals(" not in _src()


def test_source_no_os_system_batch352():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch352():
    assert "subprocess" not in _src()


def test_source_no_popen_batch352():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch352():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch352():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch352():
    assert "socket" not in _src()


def test_source_no_requests_batch352():
    assert "requests" not in _src()


def test_source_no_urllib_batch352():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch352():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch352():
    assert "yield" not in _src()


def test_source_no_async_await_batch352():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch352():
    assert _src().count("open(") == 2
