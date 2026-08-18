"""evaluation/runner.py 第五百七十一轮 edges 测试（Round 1127）。

补强 edges145 未触及的角度（第五百零三批，probe 实证）。

新角度（真文本 PDF 全胜行）：
- **手写带文字 PDF**——BT/Tj 操作符画 "Hello PDF world."
  → fallback(pdfplumber) 真解析出 1 个 paragraph 元素
  （真 page 1 + 真 bbox）——旧测试 PDF 全是空白版（解析
  失败 no_extracted_elements），成功行首锁
- **九指标精确值**——pipeline_success True + error_code
  null + ect 1 + pdf_locator 1.0（真数据过校验）+
  docx_locator null not_docx_document + chunk_ref 1.0 +
  text_equal True + multiset P 1.0 + heading null
  no_heading_elements
- forbidden tokens 第五百九十九批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from evaluation.schema import validate

_STREAM = b"BT /F1 12 Tf 10 80 Td (Hello PDF world.) Tj ET"
_TEXT_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
    b"/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
    b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"5 0 obj<</Length " + str(len(_STREAM)).encode() + b">>stream\n"
    + _STREAM + b"\nendstream endobj\n"
    b"trailer<</Size 6/Root 1 0 R>>\n%%EOF")


def _board(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "t.pdf").write_bytes(_TEXT_PDF)
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "p1", "path": "samples/t.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


def _run(tmp_path):
    return run_evaluation(_board(tmp_path), tmp_path / "r.json",
                          parser_name="fallback", max_chars=200)


# ---------- 真文本 PDF 全胜行 ----------

def test_real_text_pdf_success_batch326(tmp_path):
    r = _run(tmp_path)
    m = r["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["error_code"] == {"value": None, "reason": None}
    assert m["element_count_total"] == {"value": 1, "reason": None}
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 1}, "reason": None}


def test_real_text_pdf_locator_ratios_batch326(tmp_path):
    r = _run(tmp_path)
    m = r["per_doc"][0]["metrics"]
    assert m["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["docx_locator_valid_ratio"] == {
        "value": None, "reason": "not_docx_document"}


def test_real_text_pdf_text_and_chunks_batch326(tmp_path):
    r = _run(tmp_path)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}
    assert m["heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}


def test_real_text_pdf_report_validates_batch326(tmp_path):
    r = _run(tmp_path)
    validate(r, "evaluation-report.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch326():
    src = _src()
    assert "parse / chunk 在本阶段未插桩" in src
    assert "关键约束：" in src


# ---------- forbidden tokens 第五百九十九批 ----------

def test_source_no_eval_batch326():
    assert "eval(" not in _src()


def test_source_no_exec_batch326():
    assert "exec(" not in _src()


def test_source_no_compile_batch326():
    assert "compile(" not in _src()


def test_source_no_globals_batch326():
    assert "globals(" not in _src()


def test_source_no_locals_batch326():
    assert "locals(" not in _src()


def test_source_no_os_system_batch326():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch326():
    assert "subprocess" not in _src()


def test_source_no_popen_batch326():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch326():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch326():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch326():
    assert "socket" not in _src()


def test_source_no_requests_batch326():
    assert "requests" not in _src()


def test_source_no_urllib_batch326():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch326():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch326():
    assert "yield" not in _src()


def test_source_no_async_await_batch326():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch326():
    assert _src().count("open(") == 2
