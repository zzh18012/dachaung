"""evaluation/runner.py 第六百零二轮 edges 测试（Round 1158）。

补强 edges173 未触及的角度（第五百三十批，probe 实证）。

新角度（双表夹文 / 单行表 markdown / 预测边界数）：
- **表格元素居后**——同页 2 网格 + 4 段文字 →
  elements [paragraph, heading, paragraph,
  heading, table, table]——文本元素全在前、表格
  殿后（元素序首锁）
- **单行表 header-only markdown**——1 行 2 列
  网格 → "| A1 | B1 |\\n| --- | --- |" 无数据行
  （历史网格全 ≥2 行）
- **双表夹文仍分流**——5 chunks：3 sequential +
  2 isolated_table；格字 heading 与其后段落软界
  合块（2 源）
- **预测边界数 = 块数 - 1**——marker "tables."
  （文首现）命中第 1 界 → P 0.25（4 预测界）、
  R 1.0、F1 0.4（P 分母首锁）
- forbidden tokens 第六百三十批（open 2）
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


def _two_tables_pdf() -> bytes:
    s = (b"1 w 0 G\n"
         b"10 100 100 50 re S\n60 100 0 50 re S\n"
         b"10 150 100 0 re S\n"
         b"10 0 100 45 re S\n60 0 0 45 re S\n"
         b"10 45 100 0 re S\n"
         b"BT /F1 10 Tf 12 125 Td (A1) Tj ET\n"
         b"BT /F1 10 Tf 62 125 Td (B1) Tj ET\n"
         b"BT /F1 10 Tf 12 20 Td (A2) Tj ET\n"
         b"BT /F1 10 Tf 62 20 Td (B2) Tj ET\n"
         b"BT /F1 12 Tf 10 190 Td "
         b"(Sentence above both tables.) Tj ET\n"
         b"BT /F1 12 Tf 10 55 Td "
         b"(Text between the two tables.) Tj ET")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 200]"
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
        _two_tables_pdf())
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


# ---------- 表格元素居后 ----------

def test_two_tables_element_order_batch356(tmp_path):
    _board(tmp_path, "tt")
    doc, errors = process_single(
        tmp_path / "samples" / "tt.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == [
        "paragraph", "heading", "paragraph",
        "heading", "table", "table"]
    assert els[0]["content"] == "Sentence above both tables."
    assert els[1]["content"] == "A1 B1"
    assert els[2]["content"] == "Text between the two tables."
    assert els[3]["content"] == "A2 B2"


# ---------- 单行表 header-only markdown ----------

def test_single_row_table_markdown_batch356(tmp_path):
    _board(tmp_path, "tt2")
    doc, errors = process_single(
        tmp_path / "samples" / "tt2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    tables = [e for e in doc.to_dict()["elements"]
              if e["type"] == "table"]
    assert len(tables) == 2
    assert tables[0]["content"] == \
        "| A1 | B1 |\n| --- | --- |"
    assert tables[1]["content"] == \
        "| A2 | B2 |\n| --- | --- |"


# ---------- 双表夹文仍分流 ----------

def test_two_tables_chunk_flow_batch356(tmp_path):
    _board(tmp_path, "tt3")
    doc, errors = process_single(
        tmp_path / "samples" / "tt3.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert len(chunks) == 5
    assert [c["metadata"]["strategy"] for c in chunks] == [
        "sequential", "sequential", "sequential",
        "isolated_table", "isolated_table"]
    assert chunks[1]["text"] == \
        "A1 B1 Text between the two tables."
    assert len(chunks[1]["source_element_ids"]) == 2
    assert chunks[2]["text"] == "A2 B2"


# ---------- 预测边界数 = 块数 - 1 ----------

def test_four_boundaries_precision_batch356(tmp_path):
    r = run_evaluation(_board(tmp_path, "tt4",
                              marker="tables."),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.25, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.4, "reason": None}


def test_two_tables_metrics_batch356(tmp_path):
    r = run_evaluation(_board(tmp_path, "tt5"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 2, "heading": 2, "table": 2},
        "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}
    assert m["pipeline_success"] == {"value": True,
                                     "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch356():
    src = _src()
    assert src.count("metrics") == 13
    assert src.count("per_doc") == 12
    assert src.count("manifest") == 5


# ---------- forbidden tokens 第六百三十批 ----------

def test_source_no_eval_batch356():
    assert "eval(" not in _src()


def test_source_no_exec_batch356():
    assert "exec(" not in _src()


def test_source_no_compile_batch356():
    assert "compile(" not in _src()


def test_source_no_globals_batch356():
    assert "globals(" not in _src()


def test_source_no_locals_batch356():
    assert "locals(" not in _src()


def test_source_no_os_system_batch356():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch356():
    assert "subprocess" not in _src()


def test_source_no_popen_batch356():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch356():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch356():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch356():
    assert "socket" not in _src()


def test_source_no_requests_batch356():
    assert "requests" not in _src()


def test_source_no_urllib_batch356():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch356():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch356():
    assert "yield" not in _src()


def test_source_no_async_await_batch356():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch356():
    assert _src().count("open(") == 2
