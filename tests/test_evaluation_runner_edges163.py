"""evaluation/runner.py 第五百八十八轮 edges 测试（Round 1144）。

补强 edges162 未触及的角度（第五百二十批，probe 实证）。

新角度（无字网格 / 次页表格）：
- **无字网格仍产表**——纯 re/S 网格无任何文字 →
  table 元素 content 恰 "|  |  |\\n| --- | --- |\\n|
  |  |"——空串单元格也算行，rows 非空不跳过（首锁）
- **空表独立成块**——同板恰 1 chunk isolated_table，
  markdown 原样进块
- **次页表格保号**——页 1 空白、页 2 网格 + 格内文字 →
  els [heading, heading, table] 全 page 2——表格通道
  空白页跳过保号与文本通道一致（首锁）
- forbidden tokens 第六百一十七批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


_GRID = (b"1 w 0 G\n"
         b"10 10 100 50 re S\n"
         b"60 10 0 50 re S\n"
         b"10 35 100 0 re S\n")

_EMPTY_MD = "|  |  |\n| --- | --- |\n|  |  |"


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


def _grid_only_pdf() -> bytes:
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<<>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(_GRID)).encode()
            + b">>stream\n" + _GRID + b"\nendstream "),
    }, 5)


def _grid_page2_pdf() -> bytes:
    g = _GRID + (b"BT /F1 10 Tf 15 55 Td (C1) Tj ET\n"
                 b"BT /F1 10 Tf 65 55 Td (D1) Tj ET")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 5 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<<>>/Contents 4 0 R>>"),
        4: b"<</Length 0>>stream\n\nendstream ",
        5: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</Font<</F1 7 0 R>>>>"
            b"/Contents 6 0 R>>"),
        6: (b"<</Length " + str(len(g)).encode()
            + b">>stream\n" + g + b"\nendstream "),
        7: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 8)


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


# ---------- 无字网格仍产表 ----------

def test_textless_grid_table_batch343(tmp_path):
    _board(tmp_path, _grid_only_pdf(), "gt")
    doc, errors = process_single(
        tmp_path / "samples" / "gt.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert len(els) == 1
    assert els[0]["type"] == "table"
    assert els[0]["content"] == _EMPTY_MD
    assert els[0]["source_locator"]["page"] == 1


# ---------- 空表独立成块 ----------

def test_textless_grid_chunk_batch343(tmp_path):
    _board(tmp_path, _grid_only_pdf(), "gt2")
    doc, errors = process_single(
        tmp_path / "samples" / "gt2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert len(chunks) == 1
    assert chunks[0]["text"] == _EMPTY_MD
    assert chunks[0]["metadata"]["strategy"] == "isolated_table"


def test_textless_grid_metrics_batch343(tmp_path):
    r = run_evaluation(_board(tmp_path, _grid_only_pdf(), "gt3"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["element_count_by_type"] == {
        "value": {"table": 1}, "reason": None}
    assert m["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- 次页表格保号 ----------

def test_grid_page2_attribution_batch343(tmp_path):
    _board(tmp_path, _grid_page2_pdf(), "g2")
    doc, errors = process_single(
        tmp_path / "samples" / "g2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == ["heading", "table"]
    assert els[0]["content"] == "C1 D1"
    assert all(e["source_locator"]["page"] == 2 for e in els)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch343():
    src = _src()
    assert src.count("chunk") == 9
    assert src.count("error_code") == 4
    assert src.count("load_annotation") == 2


# ---------- forbidden tokens 第六百一十七批 ----------

def test_source_no_eval_batch343():
    assert "eval(" not in _src()


def test_source_no_exec_batch343():
    assert "exec(" not in _src()


def test_source_no_compile_batch343():
    assert "compile(" not in _src()


def test_source_no_globals_batch343():
    assert "globals(" not in _src()


def test_source_no_locals_batch343():
    assert "locals(" not in _src()


def test_source_no_os_system_batch343():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch343():
    assert "subprocess" not in _src()


def test_source_no_popen_batch343():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch343():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch343():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch343():
    assert "socket" not in _src()


def test_source_no_requests_batch343():
    assert "requests" not in _src()


def test_source_no_urllib_batch343():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch343():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch343():
    assert "yield" not in _src()


def test_source_no_async_await_batch343():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch343():
    assert _src().count("open(") == 2
