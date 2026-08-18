"""evaluation/runner.py 第五百七十二轮 edges 测试（Round 1128）。

补强 edges146 未触及的角度（第五百零四批，probe 实证）。

新角度（双页 PDF 阈值三态）：
- **真页码归属**——双页文本 PDF 直跑 process_single →
  2 个 paragraph 元素 pages 恰为 [1, 2]——真实翻页数据
  首锁（旧 PDF 测试全是单页或空白失败版）
- **max_chars 33 劈两块**——两段文本拼流 34 字符，33 恰
  越界 → 2 chunks、success True、text_equal True
- **max_chars 30 崩 chunker**——同板 30 → chunker_failed、
  per_doc error_code 可见、指标全家 null pipeline_failed
- **max_chars 34 合一块**——恰不越界 → 1 chunk、ect 2、
  success True——33/34 一字符之隔两种命运，30 再往下
  直接崩——三态阈值全谱首锁
- forbidden tokens 第六百批（open 2）
"""

from __future__ import annotations

import inspect

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _two_page_pdf() -> bytes:
    texts = [b"First page body.", b"Second page body."]
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
            b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
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
    (tmp_path / "samples" / "t.pdf").write_bytes(_two_page_pdf())
    import json
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "p2", "path": "samples/t.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


def _run(tmp_path, max_chars):
    r = run_evaluation(_board(tmp_path), tmp_path / "r.json",
                       parser_name="fallback", max_chars=max_chars)
    return r["per_doc"][0]["metrics"]


# ---------- 真页码归属 ----------

def test_two_page_element_pages_batch327(tmp_path):
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "t.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    d = doc.to_dict() if hasattr(doc, "to_dict") else doc
    els = d["elements"]
    assert len(els) == 2
    assert [e["source_locator"]["page"] for e in els] == [1, 2]
    assert all(e["type"] == "paragraph" for e in els)


# ---------- max_chars 33 劈两块 ----------

def test_threshold_33_success_batch327(tmp_path):
    m = _run(tmp_path, 33)
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["element_count_total"] == {"value": 2, "reason": None}
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}


# ---------- max_chars 30 崩 chunker ----------

def test_threshold_30_chunker_failed_batch327(tmp_path):
    m = _run(tmp_path, 30)
    assert m["pipeline_success"] == {"value": False, "reason": None}
    assert m["error_code"] == {"value": "chunker_failed",
                               "reason": None}
    assert m["element_count_total"] == {
        "value": None, "reason": "pipeline_failed"}


# ---------- max_chars 34 合一块 ----------

def test_threshold_34_merges_batch327(tmp_path):
    m = _run(tmp_path, 34)
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["element_count_total"] == {"value": 2, "reason": None}
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch327():
    assert "def _process_one(" in _src()


# ---------- forbidden tokens 第六百批 ----------

def test_source_no_eval_batch327():
    assert "eval(" not in _src()


def test_source_no_exec_batch327():
    assert "exec(" not in _src()


def test_source_no_compile_batch327():
    assert "compile(" not in _src()


def test_source_no_globals_batch327():
    assert "globals(" not in _src()


def test_source_no_locals_batch327():
    assert "locals(" not in _src()


def test_source_no_os_system_batch327():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch327():
    assert "subprocess" not in _src()


def test_source_no_popen_batch327():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch327():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch327():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch327():
    assert "socket" not in _src()


def test_source_no_requests_batch327():
    assert "requests" not in _src()


def test_source_no_urllib_batch327():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch327():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch327():
    assert "yield" not in _src()


def test_source_no_async_await_batch327():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch327():
    assert _src().count("open(") == 2
