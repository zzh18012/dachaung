"""evaluation/runner.py 第六百五十一轮 edges 测试（Round 1219）。

补强 edges215 未触及的角度（第五百九十一批，probe 实证）。

新角度（xref 偏移错位自愈）：
- **xref 全错位自愈**——全部 xref 项
  偏移 +7、startxref +13 → 解析器照
  样恢复：errors []、1 个 paragraph
  "Corrupt xref board text."（字节级
  容错首锁，区别于无 /Root 的垃圾
  崩溃路径）
- **per_doc 四键**——[doc_id,
  metrics, source_type,
  wall_time_seconds]；wall_time 是
  五键 dict：parse/chunk 各 None +
  not_instrumented、total float ≥ 0
  （计时只记 total 契约首锁）
- **自愈板 run**——ps True、by_type
  {paragraph: 1}、summary 1/1/1.0
- **单块锚**——marker "text." → 单
  chunk 无预测界 → P/F1 None
  no_predicted_boundaries / R 0.0
- forbidden tokens 第六百八十九批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _pdf() -> bytes:
    s = (b"BT /F1 12 Tf 10 700 Td "
         b"(Corrupt xref board text.) Tj ET\n")
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xref_pos = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n"
                % (offsets[num] + 7)).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos + 13).encode() + b"\n%%EOF\n")
    return bytes(out)


def _pdf_path(tmp_path, doc_id):
    (tmp_path / "s").mkdir(exist_ok=True)
    p = tmp_path / "s" / f"{doc_id}.pdf"
    p.write_bytes(_pdf())
    return p


def _board(tmp_path, doc_id, anchors=None):
    _pdf_path(tmp_path, doc_id)
    docs = [{"doc_id": doc_id, "path": f"s/{doc_id}.pdf",
             "source_type": "pdf"}]
    if anchors is not None:
        (tmp_path / "a").mkdir(exist_ok=True)
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


# ---------- xref 全错位自愈 ----------

def test_xref_shift_recovers_batch417(tmp_path):
    doc, errors = process_single(
        _pdf_path(tmp_path, "xr"), tmp_path / "o.json",
        parser_name="fallback", max_chars=60)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [(e["type"], e["content"]) for e in els] == [
        ("paragraph", "Corrupt xref board text.")]


def test_recovered_single_chunk_batch417(tmp_path):
    doc, errors = process_single(
        _pdf_path(tmp_path, "rc"), tmp_path / "o.json",
        parser_name="fallback", max_chars=60)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert len(chunks) == 1
    assert chunks[0]["text"] == "Corrupt xref board text."
    assert len(chunks[0]["source_element_ids"]) == 1


# ---------- per_doc 四键 ----------

def test_per_doc_keys_batch417(tmp_path):
    r = run_evaluation(_board(tmp_path, "pk"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=60)
    pd = r["per_doc"][0]
    assert sorted(pd.keys()) == ["doc_id", "metrics",
                                 "source_type",
                                 "wall_time_seconds"]
    wt = pd["wall_time_seconds"]
    assert sorted(wt.keys()) == ["chunk", "chunk_reason",
                                 "parse", "parse_reason",
                                 "total"]
    assert wt["parse"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk"] is None
    assert wt["chunk_reason"] == "not_instrumented"
    assert isinstance(wt["total"], float)
    assert wt["total"] >= 0


# ---------- 自愈板 run ----------

def test_recovered_run_success_batch417(tmp_path):
    r = run_evaluation(_board(tmp_path, "ok"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=60)
    pd = r["per_doc"][0]
    assert pd["metrics"]["pipeline_success"] == {
        "value": True, "reason": None}
    assert pd["metrics"]["element_count_by_type"] == {
        "value": {"paragraph": 1}, "reason": None}
    assert r["summary"]["success_rates"][
        "pipeline_success"] == {"success_count": 1, "total": 1,
                                "rate": 1.0}


def test_anchor_single_chunk_batch417(tmp_path):
    r = run_evaluation(_board(tmp_path, "a1", [
        {"marker": "text.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=60)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert m["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": None, "reason": "no_predicted_boundaries"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch417():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百八十九批 ----------

def test_source_no_eval_batch417():
    assert "eval(" not in _src()


def test_source_no_exec_batch417():
    assert "exec(" not in _src()


def test_source_no_compile_batch417():
    assert "compile(" not in _src()


def test_source_no_globals_batch417():
    assert "globals(" not in _src()


def test_source_no_locals_batch417():
    assert "locals(" not in _src()


def test_source_no_os_system_batch417():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch417():
    assert "subprocess" not in _src()


def test_source_no_popen_batch417():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch417():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch417():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch417():
    assert "socket" not in _src()


def test_source_no_requests_batch417():
    assert "requests" not in _src()


def test_source_no_urllib_batch417():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch417():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch417():
    assert "yield" not in _src()


def test_source_no_async_await_batch417():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch417():
    assert _src().count("open(") == 2
