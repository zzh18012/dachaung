"""evaluation/runner.py 第六百二十五轮 edges 测试（Round 1181）。

补强 edges193 未触及的角度（第五百五十三批，probe 实证）。

新角度（损坏输入失败分类学）：
- **坏 DOCX**——非 zip 字节 → errors[
  docx_open_failed]（details.exception_type=
  PackageNotFoundError，打开层失败首锁——与
  空文档的 no_extracted_elements 提取层失败
  分层）
- **坏 PDF**——无 /Root 垃圾字节 → errors[
  pdfplumber_open_failed]（exception_type=
  PdfminerException）
- **双坏 devset**——error_code 分流各自编码、
  schema_valid 等全 null+pipeline_failed；
  success {0, 2, 0.0}、counts {None, 0}
- **CLI 存活**——"documents=2（成功 0，失败
  2）"、validate-report rc 0
- forbidden tokens 第六百五十三批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _board(tmp_path):
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "s" / "bad.docx").write_bytes(b"not a zip")
    (tmp_path / "s" / "bad.pdf").write_bytes(
        b"%PDF-1.4 garbage")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "bd", "path": "s/bad.docx",
             "source_type": "docx"},
            {"doc_id": "bp", "path": "s/bad.pdf",
             "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 坏 DOCX ----------

def test_corrupt_docx_error_batch379(tmp_path):
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "s" / "bad.docx").write_bytes(b"not a zip")
    doc, errors = process_single(
        tmp_path / "s" / "bad.docx", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert doc is None
    assert len(errors) == 1
    e = errors[0]
    assert e.code == "docx_open_failed"
    assert e.details["exception_type"] == \
        "PackageNotFoundError"


# ---------- 坏 PDF ----------

def test_corrupt_pdf_error_batch379(tmp_path):
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "s" / "bad.pdf").write_bytes(
        b"%PDF-1.4 garbage")
    doc, errors = process_single(
        tmp_path / "s" / "bad.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert doc is None
    assert len(errors) == 1
    e = errors[0]
    assert e.code == "pdfplumber_open_failed"
    assert e.details["exception_type"] == \
        "PdfminerException"


# ---------- 双坏 devset ----------

def test_corrupt_devset_metrics_batch379(tmp_path):
    r = run_evaluation(_board(tmp_path), tmp_path / "r.json",
                       parser_name="fallback", max_chars=200)
    by_id = {pd["doc_id"]: pd["metrics"]
             for pd in r["per_doc"]}
    assert by_id["bd"]["pipeline_success"] == {
        "value": False, "reason": None}
    assert by_id["bd"]["error_code"] == {
        "value": "docx_open_failed", "reason": None}
    assert by_id["bp"]["error_code"] == {
        "value": "pdfplumber_open_failed", "reason": None}
    for m in by_id.values():
        assert m["schema_valid"] == {
            "value": None, "reason": "pipeline_failed"}


def test_corrupt_devset_summary_batch379(tmp_path):
    r = run_evaluation(_board(tmp_path), tmp_path / "r.json",
                       parser_name="fallback", max_chars=200)
    assert r["summary"]["success_rates"][
        "pipeline_success"] == {"success_count": 0,
                                "total": 2, "rate": 0.0}
    assert r["summary"]["counts"][
        "element_count_total"] == {"sum": None,
                                   "participating_docs": 0}


# ---------- CLI 存活 ----------

def test_corrupt_cli_survives_batch379(tmp_path, capsys):
    from evaluation.cli import main
    _board(tmp_path)
    mf = tmp_path / "m.json"
    rc = main(["run", "--manifest", str(mf),
               "--output", str(tmp_path / "r.json"),
               "--parser", "fallback", "--max-chars", "200"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "documents=2（成功 0，失败 2）" in out
    rc2 = main(["validate-report", str(tmp_path / "r.json")])
    out2 = capsys.readouterr().out
    assert rc2 == 0
    assert "[OK]" in out2


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch379():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("error_code") == 4
    assert src.count("metrics") == 13


# ---------- forbidden tokens 第六百五十三批 ----------

def test_source_no_eval_batch379():
    assert "eval(" not in _src()


def test_source_no_exec_batch379():
    assert "exec(" not in _src()


def test_source_no_compile_batch379():
    assert "compile(" not in _src()


def test_source_no_globals_batch379():
    assert "globals(" not in _src()


def test_source_no_locals_batch379():
    assert "locals(" not in _src()


def test_source_no_os_system_batch379():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch379():
    assert "subprocess" not in _src()


def test_source_no_popen_batch379():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch379():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch379():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch379():
    assert "socket" not in _src()


def test_source_no_requests_batch379():
    assert "requests" not in _src()


def test_source_no_urllib_batch379():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch379():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch379():
    assert "yield" not in _src()


def test_source_no_async_await_batch379():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch379():
    assert _src().count("open(") == 2
