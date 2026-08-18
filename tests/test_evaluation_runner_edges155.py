"""evaluation/runner.py 第五百八十轮 edges 测试（Round 1136）。

补强 edges154 未触及的角度（第五百一十二批，probe 实证）。

新角度（heading 软界 / caption 硬界对照）：
- **heading 与后段合并**——页 1 短行 heading + 页 2 句读
  paragraph → 恰 1 个 chunk strategy sequential，
  source_element_ids 含两元素 [e0000, e0001]——heading
  是软边界（flush 后继续累积），不隔离（首锁）
- **caption 硬隔离**——同构板把 heading 换成 Figure 前缀
  caption → 2 chunks：isolated_caption + sequential，
  各自 source_element_ids 单元素——caption 强制 flush
  独立成块（首锁）
- **runner 级对照**——hp 板 by_type {heading:1, paragraph:1}
  + heading compliance 1.0；cp 板 {caption:1, paragraph:1}
  + compliance null no_heading_elements
- forbidden tokens 第六百零九批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _build_two_page_pdf(texts) -> bytes:
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


def _board(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "hp.pdf").write_bytes(
        _build_two_page_pdf([b"A heading line",
                             b"Body sentence one. Body sentence two."]))
    (tmp_path / "samples" / "cp.pdf").write_bytes(
        _build_two_page_pdf([b"Figure 1: a cap here.",
                             b"Body sentence one. Body sentence two."]))
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "hp", "path": "samples/hp.pdf",
             "source_type": "pdf"},
            {"doc_id": "cp", "path": "samples/cp.pdf",
             "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- heading 与后段合并 ----------

def test_heading_merges_with_paragraph_batch335(tmp_path):
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "hp.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    d = doc.to_dict()
    assert [e["type"] for e in d["elements"]] == \
        ["heading", "paragraph"]
    assert len(d["chunks"]) == 1
    assert d["chunks"][0]["metadata"]["strategy"] == "sequential"
    assert d["chunks"][0]["text"] == \
        "A heading line Body sentence one. Body sentence two."
    assert len(d["chunks"][0]["source_element_ids"]) == 2


# ---------- caption 硬隔离 ----------

def test_caption_isolates_batch335(tmp_path):
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "cp.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    d = doc.to_dict()
    assert [e["type"] for e in d["elements"]] == \
        ["caption", "paragraph"]
    assert len(d["chunks"]) == 2
    assert d["chunks"][0]["metadata"]["strategy"] == \
        "isolated_caption"
    assert d["chunks"][1]["metadata"]["strategy"] == "sequential"
    assert d["chunks"][0]["text"] == "Figure 1: a cap here."
    assert all(len(c["source_element_ids"]) == 1
               for c in d["chunks"])


# ---------- runner 级对照 ----------

def test_heading_board_metrics_batch335(tmp_path):
    r = run_evaluation(_board(tmp_path), tmp_path / "r.json",
                       parser_name="fallback", max_chars=200)
    h = r["per_doc"][0]["metrics"]
    assert h["element_count_by_type"] == {
        "value": {"heading": 1, "paragraph": 1}, "reason": None}
    assert h["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


def test_caption_board_metrics_batch335(tmp_path):
    r = run_evaluation(_board(tmp_path), tmp_path / "r.json",
                       parser_name="fallback", max_chars=200)
    c = r["per_doc"][1]["metrics"]
    assert c["element_count_by_type"] == {
        "value": {"caption": 1, "paragraph": 1}, "reason": None}
    assert c["heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch335():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("load_annotation") == 2
    assert src.count("error_code") == 4


# ---------- forbidden tokens 第六百零九批 ----------

def test_source_no_eval_batch335():
    assert "eval(" not in _src()


def test_source_no_exec_batch335():
    assert "exec(" not in _src()


def test_source_no_compile_batch335():
    assert "compile(" not in _src()


def test_source_no_globals_batch335():
    assert "globals(" not in _src()


def test_source_no_locals_batch335():
    assert "locals(" not in _src()


def test_source_no_os_system_batch335():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch335():
    assert "subprocess" not in _src()


def test_source_no_popen_batch335():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch335():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch335():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch335():
    assert "socket" not in _src()


def test_source_no_requests_batch335():
    assert "requests" not in _src()


def test_source_no_urllib_batch335():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch335():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch335():
    assert "yield" not in _src()


def test_source_no_async_await_batch335():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch335():
    assert _src().count("open(") == 2
