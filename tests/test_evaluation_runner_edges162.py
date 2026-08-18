"""evaluation/runner.py 第五百八十七轮 edges 测试（Round 1143）。

补强 edges161 未触及的角度（第五百一十九批，probe 实证）。

新角度（真画线表格 / 句界劈块）：
- **真画线表格**——re/S 操作符画 2×2 网格 + 格内文字 →
  pdfplumber 认出表格：table 元素 content 恰 markdown
  "| A1 | B1 |\\n| --- | --- |\\n| A2 | B2 |"、locator
  {page 1, bbox [10,40,110,90]}、metadata {row_count 2,
  col_count 2, source pdfplumber}（真表格通道首锁）
- **表格硬隔离**——isolated_table 单块，markdown 整体
  一块不劈
- **格内文字双计**——单元格文本同时产出 2 个 heading
  元素（短行无句读），by_type {heading 2, table 1}
- **句界劈块**——3 句 76 字符文本 @ max_chars 40 →
  恰 3 块每块一句（句边界优先于白界，首锁）
- forbidden tokens 第六百一十六批（open 2）
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
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
        b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>")
    objects[4] = (
        b"<</Length " + str(len(stream)).encode() + b">>stream\n"
        + stream + b"\nendstream ")
    objects[5] = b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"
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


_TABLE_MD = "| A1 | B1 |\n| --- | --- |\n| A2 | B2 |"


def _table_pdf() -> bytes:
    return _build_one_page_pdf(
        b"1 w 0 G\n"
        b"10 10 100 50 re S\n"
        b"60 10 0 50 re S\n"
        b"10 35 100 0 re S\n"
        b"BT /F1 10 Tf 15 55 Td (A1) Tj ET\n"
        b"BT /F1 10 Tf 65 55 Td (B1) Tj ET\n"
        b"BT /F1 10 Tf 15 15 Td (A2) Tj ET\n"
        b"BT /F1 10 Tf 65 15 Td (B2) Tj ET")


def _board(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "tbl.pdf").write_bytes(_table_pdf())
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "tbl", "path": "samples/tbl.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 真画线表格 ----------

def test_table_element_fields_batch342(tmp_path):
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "tbl.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    tables = [e for e in doc.to_dict()["elements"]
              if e["type"] == "table"]
    assert len(tables) == 1
    t = tables[0]
    assert t["content"] == _TABLE_MD
    assert t["source_locator"] == {
        "page": 1, "bbox": [10.0, 40.0, 110.0, 90.0]}
    assert t["metadata"] == {"row_count": 2, "col_count": 2,
                             "source": "pdfplumber"}


# ---------- 表格硬隔离 ----------

def test_table_isolated_chunk_batch342(tmp_path):
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "tbl.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert chunks[-1]["text"] == _TABLE_MD
    assert chunks[-1]["metadata"]["strategy"] == "isolated_table"
    assert len(chunks[-1]["source_element_ids"]) == 1


# ---------- 格内文字双计 ----------

def test_table_cell_text_double_counted_batch342(tmp_path):
    r = run_evaluation(_board(tmp_path), tmp_path / "r.json",
                       parser_name="fallback", max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 2, "table": 1}, "reason": None}
    assert m["element_count_total"] == {"value": 3, "reason": None}
    assert m["pipeline_success"] == {"value": True, "reason": None}


# ---------- 句界劈块 ----------

def test_sentence_split_batch342(tmp_path):
    (tmp_path / "samples2").mkdir(exist_ok=True)
    (tmp_path / "samples2" / "s.pdf").write_bytes(
        _build_one_page_pdf(
            b"BT /F1 12 Tf 10 80 Td (First sentence ends here. "
            b"Second sentence follows next. Third one closes.)"
            b" Tj ET"))
    doc, errors = process_single(
        tmp_path / "samples2" / "s.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=40)
    assert errors == []
    texts = [c["text"] for c in doc.to_dict()["chunks"]]
    assert texts == ["First sentence ends here.",
                     "Second sentence follows next.",
                     "Third one closes."]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch342():
    src = _src()
    assert src.count("metrics") == 13
    assert src.count("process_single") == 6
    assert src.count("manifest") == 5


# ---------- forbidden tokens 第六百一十六批 ----------

def test_source_no_eval_batch342():
    assert "eval(" not in _src()


def test_source_no_exec_batch342():
    assert "exec(" not in _src()


def test_source_no_compile_batch342():
    assert "compile(" not in _src()


def test_source_no_globals_batch342():
    assert "globals(" not in _src()


def test_source_no_locals_batch342():
    assert "locals(" not in _src()


def test_source_no_os_system_batch342():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch342():
    assert "subprocess" not in _src()


def test_source_no_popen_batch342():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch342():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch342():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch342():
    assert "socket" not in _src()


def test_source_no_requests_batch342():
    assert "requests" not in _src()


def test_source_no_urllib_batch342():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch342():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch342():
    assert "yield" not in _src()


def test_source_no_async_await_batch342():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch342():
    assert _src().count("open(") == 2
