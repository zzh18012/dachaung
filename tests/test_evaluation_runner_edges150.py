"""evaluation/runner.py 第五百七十五轮 edges 测试（Round 1131）。

补强 edges149 未触及的角度（第五百零七批，probe 实证）。

新角度（单页内 run 合并与段内白界劈块）：
- **双 run 合并**——同页两个 BT/Tj run（不同 Td y 坐标）
  → 恰 1 个 paragraph "Run one. Run two." page 1——
  fallback(pdfplumber) 同页多 run 归并首锁
- **段内白界三劈**——209 字符 30 词一行，max_chars 100
  → 1 元素 3 chunks（首块恰 97 字符，白界优先不越限）
- **段内白界二劈**——同板 max_chars 150 → 2 chunks 首块 146
- **段内白界一合**——max_chars 300 → 1 chunk 全量 209，
  runner 级 text_preservation_equal True
- forbidden tokens 第六百零四批（open 2）
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
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 500 100]"
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


def _two_runs_pdf() -> bytes:
    return _build_one_page_pdf(
        b"BT /F1 12 Tf 10 80 Td (Run one.) Tj ET\n"
        b"BT /F1 12 Tf 10 60 Td (Run two.) Tj ET")


def _long_line_pdf() -> bytes:
    text = b" ".join(b"word%02d" % i for i in range(30))
    return _build_one_page_pdf(
        b"BT /F1 12 Tf 10 80 Td (" + text + b") Tj ET")


def _board(tmp_path, pdf_bytes, doc_id):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(pdf_bytes)
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id,
                       "path": f"samples/{doc_id}.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


def _run(tmp_path, pdf_bytes, doc_id, max_chars):
    return run_evaluation(_board(tmp_path, pdf_bytes, doc_id),
                          tmp_path / f"r{doc_id}{max_chars}.json",
                          parser_name="fallback",
                          max_chars=max_chars)


# ---------- 双 run 合并 ----------

def test_two_runs_merge_batch330(tmp_path):
    _board(tmp_path, _two_runs_pdf(), "tr")
    doc, errors = process_single(
        tmp_path / "samples" / "tr.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    d = doc.to_dict()
    els = d["elements"]
    assert len(els) == 1
    assert els[0]["type"] == "paragraph"
    assert els[0]["content"] == "Run one. Run two."
    assert els[0]["source_locator"]["page"] == 1
    assert len(d["chunks"]) == 1


# ---------- 段内白界三劈 ----------

def test_intra_split_three_chunks_batch330(tmp_path):
    _board(tmp_path, _long_line_pdf(), "ll1")
    doc, errors = process_single(
        tmp_path / "samples" / "ll1.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=100)
    assert errors == []
    d = doc.to_dict()
    assert len(d["elements"]) == 1
    assert len(d["chunks"]) == 3
    assert len(d["chunks"][0]["text"]) == 97


# ---------- 段内白界二劈 ----------

def test_intra_split_two_chunks_batch330(tmp_path):
    _board(tmp_path, _long_line_pdf(), "ll2")
    doc, errors = process_single(
        tmp_path / "samples" / "ll2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=150)
    assert errors == []
    d = doc.to_dict()
    assert len(d["elements"]) == 1
    assert len(d["chunks"]) == 2
    assert len(d["chunks"][0]["text"]) == 146


# ---------- 段内白界一合 ----------

def test_intra_split_one_chunk_batch330(tmp_path):
    r = _run(tmp_path, _long_line_pdf(), "ll3", 300)
    m = r["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["element_count_total"] == {"value": 1, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch330():
    src = _src()
    assert src.count("process_single") == 6
    assert src.count("metrics") == 13
    assert src.count("annotation") == 10


# ---------- forbidden tokens 第六百零四批 ----------

def test_source_no_eval_batch330():
    assert "eval(" not in _src()


def test_source_no_exec_batch330():
    assert "exec(" not in _src()


def test_source_no_compile_batch330():
    assert "compile(" not in _src()


def test_source_no_globals_batch330():
    assert "globals(" not in _src()


def test_source_no_locals_batch330():
    assert "locals(" not in _src()


def test_source_no_os_system_batch330():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch330():
    assert "subprocess" not in _src()


def test_source_no_popen_batch330():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch330():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch330():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch330():
    assert "socket" not in _src()


def test_source_no_requests_batch330():
    assert "requests" not in _src()


def test_source_no_urllib_batch330():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch330():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch330():
    assert "yield" not in _src()


def test_source_no_async_await_batch330():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch330():
    assert _src().count("open(") == 2
