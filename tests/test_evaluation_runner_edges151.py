"""evaluation/runner.py 第五百七十六轮 edges 测试（Round 1132）。

补强 edges150 未触及的角度（第五百零八批，probe 实证）。

新角度（PDF 字面串转义 / 无白界长词）：
- **括号转义往返**——PDF 字面串 \\( \\) 转义解回真实括号：
  "Left \\(paren\\) and \\(another\\) done." → 元素 content
  恰 'Left (paren) and (another) done.'（pdfminer 解
  PDF 转义首锁；括号是字面串定界符，未转义会截断）
- **runner 级转义全胜**——同板 run_evaluation：success
  True + ect 1 + text_equal True——转义文本全链路不丢
- **无白界长词崩**——60 连 A 无空白词，max_chars 30 →
  chunker_failed"max_chars 过小"（白界优先的直接后果：
  没有白界就没有切点，宁可崩不硬切，首锁）
- **长词恰容不崩**——同板 max_chars 60 → success True
  1 chunk 全量——下界恰容与一步之崩的分界
- forbidden tokens 第六百零五批（open 2）
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


def _escapes_pdf() -> bytes:
    return _build_one_page_pdf(
        rb"BT /F1 12 Tf 10 80 Td (Left \(paren\) and "
        rb"\(another\) done.) Tj ET")


def _long_word_pdf() -> bytes:
    return _build_one_page_pdf(
        b"BT /F1 12 Tf 10 80 Td (" + b"A" * 60 + b") Tj ET")


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


# ---------- 括号转义往返 ----------

def test_paren_escapes_roundtrip_batch331(tmp_path):
    _board(tmp_path, _escapes_pdf(), "pe")
    doc, errors = process_single(
        tmp_path / "samples" / "pe.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert len(els) == 1
    assert els[0]["content"] == "Left (paren) and (another) done."


# ---------- runner 级转义全胜 ----------

def test_paren_escapes_runner_success_batch331(tmp_path):
    r = run_evaluation(_board(tmp_path, _escapes_pdf(), "pe2"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["element_count_total"] == {"value": 1, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 无白界长词崩 ----------

def test_long_word_small_max_chars_fails_batch331(tmp_path):
    _board(tmp_path, _long_word_pdf(), "lw")
    doc, errors = process_single(
        tmp_path / "samples" / "lw.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=30)
    assert len(errors) == 1
    assert errors[0].code == "chunker_failed"


def test_long_word_runner_error_code_batch331(tmp_path):
    r = run_evaluation(_board(tmp_path, _long_word_pdf(), "lw2"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=30)
    m = r["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": False, "reason": None}
    assert m["error_code"] == {"value": "chunker_failed",
                               "reason": None}
    assert m["element_count_total"] == {
        "value": None, "reason": "pipeline_failed"}


# ---------- 长词恰容不崩 ----------

def test_long_word_exact_fit_batch331(tmp_path):
    r = run_evaluation(_board(tmp_path, _long_word_pdf(), "lw3"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=60)
    m = r["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["element_count_total"] == {"value": 1, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch331():
    src = _src()
    assert src.count("chunk") == 9
    assert src.count("manifest") == 5
    assert src.count("error_code") == 4


# ---------- forbidden tokens 第六百零五批 ----------

def test_source_no_eval_batch331():
    assert "eval(" not in _src()


def test_source_no_exec_batch331():
    assert "exec(" not in _src()


def test_source_no_compile_batch331():
    assert "compile(" not in _src()


def test_source_no_globals_batch331():
    assert "globals(" not in _src()


def test_source_no_locals_batch331():
    assert "locals(" not in _src()


def test_source_no_os_system_batch331():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch331():
    assert "subprocess" not in _src()


def test_source_no_popen_batch331():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch331():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch331():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch331():
    assert "socket" not in _src()


def test_source_no_requests_batch331():
    assert "requests" not in _src()


def test_source_no_urllib_batch331():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch331():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch331():
    assert "yield" not in _src()


def test_source_no_async_await_batch331():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch331():
    assert _src().count("open(") == 2
