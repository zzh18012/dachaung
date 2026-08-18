"""evaluation/runner.py 第六百二十二轮 edges 测试（Round 1178）。

补强 edges190 未触及的角度（第五百五十批，probe 实证）。

新角度（空 DOCX 退化失败通道）：
- **管道级失败**——零段落零表格 DOCX →
  process_single 返回 doc=None + errors[
  no_extracted_elements]（details 携带
  docx_no_content 警告，首锁）
- **指标全 null**——pipeline_success False 而
  外全指标 null + reason=pipeline_failed；
  error_code {'no_extracted_elements'}
- **聚合失败语义**——counts sum None 且
  participating_docs 0（失败文档不参与计数）；
  success {0, 1, 0.0}
- **CLI 存活**——失败文档不崩 CLI：run rc 0、
  stdout "documents=1（成功 0，失败 1）"、
  validate-report rc 0（报告仍过 Schema）
- forbidden tokens 第六百五十批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from docx import Document
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _board(tmp_path):
    (tmp_path / "s").mkdir(exist_ok=True)
    d = Document()
    d.save(str(tmp_path / "s" / "empty.docx"))
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "em", "path": "s/empty.docx",
                       "source_type": "docx"}]}),
        encoding="utf-8")
    return mf


# ---------- 管道级失败 ----------

def test_empty_docx_pipeline_error_batch376(tmp_path):
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "s" / "empty.docx", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert doc is None
    assert len(errors) == 1
    e = errors[0]
    assert e.code == "no_extracted_elements"
    assert e.details["source_type"] == "docx"
    assert e.details["warnings"][0]["code"] == \
        "docx_no_content"


# ---------- 指标全 null ----------

def test_empty_docx_metrics_null_batch376(tmp_path):
    mf = _board(tmp_path)
    r = run_evaluation(load_manifest(mf, project_root=tmp_path),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": False,
                                     "reason": None}
    for k in ("schema_valid", "element_count_by_type",
              "element_count_total", "text_preservation_equal",
              "text_char_multiset_precision",
              "text_char_multiset_recall",
              "docx_locator_valid_ratio",
              "image_resource_exists_ratio",
              "heading_boundary_compliance",
              "chunk_reference_intact_ratio",
              "silent_drop_count"):
        assert m[k] == {"value": None,
                        "reason": "pipeline_failed"}, k
    assert m["error_code"] == {
        "value": "no_extracted_elements", "reason": None}


# ---------- 聚合失败语义 ----------

def test_empty_docx_summary_batch376(tmp_path):
    mf = _board(tmp_path)
    r = run_evaluation(load_manifest(mf, project_root=tmp_path),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    assert r["summary"]["counts"][
        "element_count_total"] == {"sum": None,
                                   "participating_docs": 0}
    assert r["summary"]["success_rates"][
        "pipeline_success"] == {"success_count": 0, "total": 1,
                                "rate": 0.0}


# ---------- CLI 存活 ----------

def test_empty_docx_cli_survives_batch376(tmp_path, capsys):
    from evaluation.cli import main
    mf = _board(tmp_path)
    rc = main(["run", "--manifest", str(mf),
               "--output", str(tmp_path / "r.json"),
               "--parser", "fallback", "--max-chars", "200"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "documents=1（成功 0，失败 1）" in out
    rc2 = main(["validate-report", str(tmp_path / "r.json")])
    out2 = capsys.readouterr().out
    assert rc2 == 0
    assert "[OK]" in out2


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch376():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("error_code") == 4
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百五十批 ----------

def test_source_no_eval_batch376():
    assert "eval(" not in _src()


def test_source_no_exec_batch376():
    assert "exec(" not in _src()


def test_source_no_compile_batch376():
    assert "compile(" not in _src()


def test_source_no_globals_batch376():
    assert "globals(" not in _src()


def test_source_no_locals_batch376():
    assert "locals(" not in _src()


def test_source_no_os_system_batch376():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch376():
    assert "subprocess" not in _src()


def test_source_no_popen_batch376():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch376():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch376():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch376():
    assert "socket" not in _src()


def test_source_no_requests_batch376():
    assert "requests" not in _src()


def test_source_no_urllib_batch376():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch376():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch376():
    assert "yield" not in _src()


def test_source_no_async_await_batch376():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch376():
    assert _src().count("open(") == 2
