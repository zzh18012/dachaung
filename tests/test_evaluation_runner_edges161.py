"""evaluation/runner.py 第五百八十六轮 edges 测试（Round 1142）。

补强 edges160 未触及的角度（第五百一十八批，probe 实证）。

新角度（无白界 forced_char 劈块真跑）：
- **81 连 k @ 50 → 2 块 [50, 31]**——无空白段落超长 →
  forced_char 硬切恰在 max_chars 处，尾块 31——
  strategy long_paragraph_sentence_split、首块
  split_boundary_after forced_char（runner 级真 PDF
  首锁；chunker 直调层旧锁 test_chunker*）
- **硬切不丢字**——同板 runner 级 text_equal True +
  chunk_ref 1.0——forced 切割全量保全
- **对照 edges151 语义修正**——60 连 A @ 30 崩的真实
  原因是构造器地板 max_chars>=32，不是无白界本身；
  地板之上无白界走 forced_char 而非崩
- forbidden tokens 第六百一十五批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _build_one_page_pdf(stream) -> bytes:
    objects = {}
    objects[1] = b"<</Type/Catalog/Pages 2 0 R>>"
    objects[2] = b"<</Type/Pages/Kids[3 0 R]/Count 1>>"
    objects[3] = (
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 900 100]"
        b"/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>")
    objects[4] = b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"
    objects[5] = (
        b"<</Length " + str(len(stream)).encode() + b">>stream\n"
        + stream + b"\nendstream ")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objects[num] + b"endobj\n")
    xref_pos = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


def _board(tmp_path, doc_id):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(
        _build_one_page_pdf(
            b"BT /F1 12 Tf 10 80 Td (" + b"k" * 81
            + b") Tj ET"))
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id,
                       "path": f"samples/{doc_id}.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 81 连 k @ 50 → 2 块 ----------

def test_forced_char_split_batch341(tmp_path):
    _board(tmp_path, "fc")
    doc, errors = process_single(
        tmp_path / "samples" / "fc.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=50)
    assert errors == []
    d = doc.to_dict()
    assert [len(c["text"]) for c in d["chunks"]] == [50, 31]
    assert d["chunks"][0]["metadata"]["strategy"] == \
        "long_paragraph_sentence_split"
    assert d["chunks"][0]["metadata"]["split_boundary_after"] == \
        "forced_char"
    assert d["chunks"][1]["metadata"]["strategy"] == \
        "long_paragraph_sentence_split"
    assert ("split_boundary_after"
            not in d["chunks"][1]["metadata"])


# ---------- 硬切不丢字 ----------

def test_forced_char_preserves_batch341(tmp_path):
    r = run_evaluation(_board(tmp_path, "fc2"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}


# ---------- 地板之上一块恰容 ----------

def test_forced_char_one_chunk_batch341(tmp_path):
    r = run_evaluation(_board(tmp_path, "fc3"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=81)
    m = r["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch341():
    src = _src()
    assert src.count("process_single") == 6
    assert src.count("annotation") == 10
    assert src.count("run_evaluation") == 2


# ---------- forbidden tokens 第六百一十五批 ----------

def test_source_no_eval_batch341():
    assert "eval(" not in _src()


def test_source_no_exec_batch341():
    assert "exec(" not in _src()


def test_source_no_compile_batch341():
    assert "compile(" not in _src()


def test_source_no_globals_batch341():
    assert "globals(" not in _src()


def test_source_no_locals_batch341():
    assert "locals(" not in _src()


def test_source_no_os_system_batch341():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch341():
    assert "subprocess" not in _src()


def test_source_no_popen_batch341():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch341():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch341():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch341():
    assert "socket" not in _src()


def test_source_no_requests_batch341():
    assert "requests" not in _src()


def test_source_no_urllib_batch341():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch341():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch341():
    assert "yield" not in _src()


def test_source_no_async_await_batch341():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch341():
    assert _src().count("open(") == 2
