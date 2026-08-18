"""evaluation/runner.py 第五百八十九轮 edges 测试（Round 1145）。

补强 edges163 未触及的角度（第五百一十九批，probe 实证）。

新角度（跨页文表混排排序）：
- **每页先文后表**——页 1 纯文本、页 2 网格 + 格内文字
  → els 恰 [paragraph p1, heading p2, table p2]——
  逐页处理、页内文本先于表格（跨页混排排序首锁）
- **heading 断开前段**——页 1 段落与页 2 heading 不合
  块：3 chunks [sequential, sequential, isolated_table]——
  heading 强制 flush 把跨页文本切开
- forbidden tokens 第六百一十八批（open 2）
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


def _mixed_pdf() -> bytes:
    p1 = b"BT /F1 12 Tf 10 80 Td (Plain intro sentence.) Tj ET"
    p2 = (b"1 w 0 G\n"
          b"10 10 100 50 re S\n"
          b"60 10 0 50 re S\n"
          b"10 35 100 0 re S\n"
          b"BT /F1 10 Tf 15 55 Td (C1) Tj ET\n"
          b"BT /F1 10 Tf 65 55 Td (D1) Tj ET")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 5 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</Font<</F1 7 0 R>>>>"
            b"/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(p1)).encode()
            + b">>stream\n" + p1 + b"\nendstream "),
        5: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</Font<</F1 7 0 R>>>>"
            b"/Contents 6 0 R>>"),
        6: (b"<</Length " + str(len(p2)).encode()
            + b">>stream\n" + p2 + b"\nendstream "),
        7: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 8)


def _board(tmp_path, doc_id):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(
        _mixed_pdf())
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id,
                       "path": f"samples/{doc_id}.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 每页先文后表 ----------

def test_cross_page_ordering_batch344(tmp_path):
    _board(tmp_path, "mx")
    doc, errors = process_single(
        tmp_path / "samples" / "mx.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [(e["type"], e["source_locator"]["page"])
            for e in els] == [
        ("paragraph", 1), ("heading", 2), ("table", 2)]


# ---------- heading 断开前段 ----------

def test_heading_splits_cross_page_batch344(tmp_path):
    _board(tmp_path, "mx2")
    doc, errors = process_single(
        tmp_path / "samples" / "mx2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert len(chunks) == 3
    assert chunks[0]["text"] == "Plain intro sentence."
    assert chunks[0]["metadata"]["strategy"] == "sequential"
    assert chunks[1]["text"] == "C1 D1"
    assert chunks[1]["metadata"]["strategy"] == "sequential"
    assert chunks[2]["metadata"]["strategy"] == "isolated_table"


def test_mixed_board_metrics_batch344(tmp_path):
    r = run_evaluation(_board(tmp_path, "mx3"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_total"] == {"value": 3, "reason": None}
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 1, "heading": 1, "table": 1},
        "reason": None}
    assert m["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch344():
    src = _src()
    assert src.count("annotation") == 10
    assert src.count("run_evaluation") == 2
    assert src.count("metrics") == 13


# ---------- forbidden tokens 第六百一十八批 ----------

def test_source_no_eval_batch344():
    assert "eval(" not in _src()


def test_source_no_exec_batch344():
    assert "exec(" not in _src()


def test_source_no_compile_batch344():
    assert "compile(" not in _src()


def test_source_no_globals_batch344():
    assert "globals(" not in _src()


def test_source_no_locals_batch344():
    assert "locals(" not in _src()


def test_source_no_os_system_batch344():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch344():
    assert "subprocess" not in _src()


def test_source_no_popen_batch344():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch344():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch344():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch344():
    assert "socket" not in _src()


def test_source_no_requests_batch344():
    assert "requests" not in _src()


def test_source_no_urllib_batch344():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch344():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch344():
    assert "yield" not in _src()


def test_source_no_async_await_batch344():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch344():
    assert _src().count("open(") == 2
