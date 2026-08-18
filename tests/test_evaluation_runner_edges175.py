"""evaluation/runner.py 第六百零三轮 edges 测试（Round 1159）。

补强 edges174 未触及的角度（第五百三十一批，probe 实证）。

新角度（跨页劈裂表格）：
- **网格跨页成双表**——同一逻辑表格的网格线分
  布两页 → 每页各自认表：2 个 table 元素各挂
  本页 locator（page 1 bbox [10,0,110,50] /
  page 2 bbox [10,50,110,100]）——pdfplumber
  逐页认表，跨页不合并（首锁）
- **元素按页交错**——[heading p1, table p1,
  heading p2, table p2]：每页先文后表、页间顺
  序推进（与 edges174 同页全文前置对照）
- **块序交替**——[sequential, isolated_table,
  sequential, isolated_table] 四块交替
- forbidden tokens 第六百三十一批（open 2）
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


def _split_table_pdf() -> bytes:
    s1 = (b"1 w 0 G\n"
          b"10 50 100 50 re S\n60 50 0 50 re S\n"
          b"10 100 100 0 re S\n"
          b"BT /F1 10 Tf 15 75 Td (A1) Tj ET\n"
          b"BT /F1 10 Tf 65 75 Td (B1) Tj ET")
    s2 = (b"1 w 0 G\n"
          b"10 0 100 50 re S\n60 0 0 50 re S\n"
          b"10 50 100 0 re S\n"
          b"BT /F1 10 Tf 15 25 Td (A2) Tj ET\n"
          b"BT /F1 10 Tf 65 25 Td (B2) Tj ET")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 5 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</Font<</F1 7 0 R>>>>"
            b"/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
        5: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</Font<</F1 7 0 R>>>>"
            b"/Contents 6 0 R>>"),
        6: (b"<</Length " + str(len(s2)).encode()
            + b">>stream\n" + s2 + b"\nendstream "),
        7: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 8)


def _board(tmp_path, doc_id):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(
        _split_table_pdf())
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id,
                       "path": f"samples/{doc_id}.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 网格跨页成双表 ----------

def test_split_table_per_page_elements_batch357(tmp_path):
    _board(tmp_path, "sp")
    doc, errors = process_single(
        tmp_path / "samples" / "sp.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == [
        "heading", "table", "heading", "table"]
    assert els[1]["source_locator"] == {
        "page": 1, "bbox": [10.0, 0.0, 110.0, 50.0]}
    assert els[3]["source_locator"] == {
        "page": 2, "bbox": [10.0, 50.0, 110.0, 100.0]}
    assert els[0]["source_locator"]["page"] == 1
    assert els[2]["source_locator"]["page"] == 2


def test_split_table_markdown_batch357(tmp_path):
    _board(tmp_path, "sp2")
    doc, errors = process_single(
        tmp_path / "samples" / "sp2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert els[1]["content"] == \
        "| A1 | B1 |\n| --- | --- |"
    assert els[3]["content"] == \
        "| A2 | B2 |\n| --- | --- |"
    assert els[1]["metadata"]["row_count"] == 1
    assert els[1]["metadata"]["col_count"] == 2
    assert els[3]["metadata"]["row_count"] == 1


# ---------- 块序交替 ----------

def test_split_table_chunks_batch357(tmp_path):
    _board(tmp_path, "sp3")
    doc, errors = process_single(
        tmp_path / "samples" / "sp3.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert [c["metadata"]["strategy"] for c in chunks] == [
        "sequential", "isolated_table",
        "sequential", "isolated_table"]
    assert chunks[0]["text"] == "A1 B1"
    assert chunks[2]["text"] == "A2 B2"


# ---------- 指标 ----------

def test_split_table_metrics_batch357(tmp_path):
    r = run_evaluation(_board(tmp_path, "sp4"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 2, "table": 2}, "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["pipeline_success"] == {"value": True,
                                     "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch357():
    src = _src()
    assert src.count("error_code") == 4
    assert src.count("expected_failure") == 5
    assert src.count("annotation") == 10


# ---------- forbidden tokens 第六百三十一批 ----------

def test_source_no_eval_batch357():
    assert "eval(" not in _src()


def test_source_no_exec_batch357():
    assert "exec(" not in _src()


def test_source_no_compile_batch357():
    assert "compile(" not in _src()


def test_source_no_globals_batch357():
    assert "globals(" not in _src()


def test_source_no_locals_batch357():
    assert "locals(" not in _src()


def test_source_no_os_system_batch357():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch357():
    assert "subprocess" not in _src()


def test_source_no_popen_batch357():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch357():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch357():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch357():
    assert "socket" not in _src()


def test_source_no_requests_batch357():
    assert "requests" not in _src()


def test_source_no_urllib_batch357():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch357():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch357():
    assert "yield" not in _src()


def test_source_no_async_await_batch357():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch357():
    assert _src().count("open(") == 2
