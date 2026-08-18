"""evaluation/runner.py 第五百八十一轮 edges 测试（Round 1137）。

补强 edges155 未触及的角度（第五百一十三批，probe 实证）。

新角度（三类型混排 / heading 型 expectations）：
- **caption→heading→paragraph 三页混排**——恰 2 chunks：
  isolated_caption + sequential(heading+paragraph 合并)
  ——硬界在前软界在后的复合行为首锁
- **heading 型 expectations**——expectations {heading: 2}
  配真实 1 heading → silent_drop_count 1——旧锁全是
  paragraph/table 键，heading 键真跑首锁
- **混合类型 locator 全胜**——caption/heading/paragraph
  三类型元素 pdf_locator_valid_ratio 恰 1.0
- **heading 居第二块仍合规**——heading 在 caption flush
  之后开新 buf → 位于 chunk 2 首位 → compliance 1.0
- forbidden tokens 第六百一十批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _build_pdf(texts) -> bytes:
    n_pages = len(texts)
    font_no = 3 + 2 * n_pages
    objects = {}
    kids = b" ".join(str(3 + 2 * i).encode() + b" 0 R"
                    for i in range(n_pages))
    objects[1] = b"<</Type/Catalog/Pages 2 0 R>>"
    objects[2] = (b"<</Type/Pages/Kids[" + kids + b"]/Count "
                  + str(n_pages).encode() + b">>")
    for i, t in enumerate(texts):
        page_no = 3 + 2 * i
        cont_no = page_no + 1
        objects[page_no] = (
            b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 500 100]"
            b"/Resources<</Font<</F1 " + str(font_no).encode()
            + b" 0 R>>>>/Contents "
            + str(cont_no).encode() + b" 0 R>>")
        s = b"BT /F1 12 Tf 10 80 Td (" + t + b") Tj ET"
        objects[cont_no] = (
            b"<</Length " + str(len(s)).encode() + b">>stream\n"
            + s + b"\nendstream ")
    objects[font_no] = (
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objects[num] + b"endobj\n")
    xref_pos = len(out)
    max_obj = max(objects)
    out += b"xref\n0 " + str(max_obj + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for num in range(1, max_obj + 1):
        if num in offsets:
            out += ("%010d 00000 n \n" % offsets[num]).encode()
        else:
            out += b"0000000000 65535 f \n"
    out += (b"trailer<</Size " + str(max_obj + 1).encode()
            + b"/Root 1 0 R>>\nstartxref\n" + str(xref_pos).encode()
            + b"\n%%EOF\n")
    return bytes(out)


def _write_doc(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "chp.pdf").write_bytes(_build_pdf(
        [b"Figure 1: cap first.", b"A heading line",
         b"Body sentence one ends here."]))


def _board(tmp_path, with_expectations):
    _write_doc(tmp_path)
    doc_entry = {"doc_id": "chp", "path": "samples/chp.pdf",
                 "source_type": "pdf"}
    if with_expectations:
        doc_entry["expectations"] = {
            "element_count_by_type": {"heading": 2}}
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [doc_entry]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- caption→heading→paragraph 三页混排 ----------

def test_three_type_layout_batch336(tmp_path):
    _write_doc(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "chp.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    d = doc.to_dict()
    assert [e["type"] for e in d["elements"]] == \
        ["caption", "heading", "paragraph"]
    assert len(d["chunks"]) == 2
    assert d["chunks"][0]["metadata"]["strategy"] == \
        "isolated_caption"
    assert d["chunks"][1]["metadata"]["strategy"] == "sequential"
    assert d["chunks"][1]["text"] == \
        "A heading line Body sentence one ends here."


# ---------- heading 型 expectations ----------

def test_heading_expectations_drop_batch336(tmp_path):
    r = run_evaluation(_board(tmp_path, True),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"caption": 1, "heading": 1, "paragraph": 1},
        "reason": None}
    assert m["silent_drop_count"] == {"value": 1, "reason": None}


def test_no_expectations_null_batch336(tmp_path):
    r = run_evaluation(_board(tmp_path, False),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["silent_drop_count"] == {
        "value": None, "reason": "no_expectations"}


# ---------- 混合类型 locator 全胜 ----------

def test_mixed_type_locator_batch336(tmp_path):
    r = run_evaluation(_board(tmp_path, False),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["element_count_total"] == {"value": 3, "reason": None}


# ---------- heading 居第二块仍合规 ----------

def test_heading_second_chunk_compliance_batch336(tmp_path):
    r = run_evaluation(_board(tmp_path, False),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch336():
    src = _src()
    assert src.count("annotation") == 10
    assert src.count("chunk") == 9
    assert src.count("error_code") == 4


# ---------- forbidden tokens 第六百一十批 ----------

def test_source_no_eval_batch336():
    assert "eval(" not in _src()


def test_source_no_exec_batch336():
    assert "exec(" not in _src()


def test_source_no_compile_batch336():
    assert "compile(" not in _src()


def test_source_no_globals_batch336():
    assert "globals(" not in _src()


def test_source_no_locals_batch336():
    assert "locals(" not in _src()


def test_source_no_os_system_batch336():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch336():
    assert "subprocess" not in _src()


def test_source_no_popen_batch336():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch336():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch336():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch336():
    assert "socket" not in _src()


def test_source_no_requests_batch336():
    assert "requests" not in _src()


def test_source_no_urllib_batch336():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch336():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch336():
    assert "yield" not in _src()


def test_source_no_async_await_batch336():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch336():
    assert _src().count("open(") == 2
