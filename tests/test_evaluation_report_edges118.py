"""evaluation/report.py 第四百八十三轮 edges 测试（Round 1039）。

补强 edges117 未触及的角度（第四百一十五批，probe 实证）。

新角度（真实生产者 → 真实聚合者全管线）：
- 此前 aggregate_summary 测试全部手工构造 metrics dict；
  本批用 compute_automatic_metrics +
  figure_caption_prf + chunk_boundary_prf（_tolerance_chars
  pop 后）真实产出 20 键 metrics 喂入聚合
- 三文档异构（pdf 成功带 expectations / docx 成功 /
  纯 error）：counts sum 3 participating 2、success
  2/3、silent 2 同屏
- pdf/docx 定位通道分离经真实指标验证：pdf_locator
  仅 d1 参与（1.0/1/2）、docx_locator 仅 d2 参与
  （1.0/1/2）、schema_valid 2 参与 macro 1.0
- chunk_boundary_f1 全 0 参与（d1 单 chunk → 无预测
  边界 → F1 null；d2 无标注；d3 无文档）→ macro None
- figure_caption_* 三键不在 _RATIO_METRICS：真实
  null 指标从未进入 ratio 聚合（KeyError 面）
- forbidden tokens 第五百一十批（open 0；subprocess
  合法依赖不列禁词，run 恰 2）
"""

from __future__ import annotations

import inspect

import evaluation.report as rpt
from evaluation.annotation_metrics import (
    chunk_boundary_prf, figure_caption_prf)
from evaluation.metrics import compute_automatic_metrics
from evaluation.report import aggregate_summary


def _e(t, eid, loc={"page": 1, "bbox": [0, 0, 1, 1]}):
    return {"type": t, "element_id": eid, "content": "x",
            "parent_id": None, "confidence": 0.9,
            "metadata": {}, "source_locator": loc}


def _doc(elements, chunks, st):
    return {"elements": elements, "chunks": chunks,
            "source_type": st, "document_id": "x",
            "schema_version": "0.1.0", "source_path": "a",
            "source_hash": "a" * 64, "parser_name": "fb",
            "parser_version": "1", "relations": [],
            "warnings": [], "errors": [], "metadata": {}}


def _full_metrics(document, error, st, expectations,
                  annotation, tol=30):
    m = compute_automatic_metrics(document, error, st,
                                  expectations)
    m.update(figure_caption_prf(document, annotation))
    cb = chunk_boundary_prf(document, annotation,
                            tolerance_chars=tol)
    cb.pop("_tolerance_chars", None)
    m.update(cb)
    return m


def _rows():
    d1 = _doc([_e("paragraph", "p1"), _e("heading", "h1")],
              [{"chunk_id": "c", "text": "x",
                "source_element_ids": ["p1", "h1"],
                "metadata": {}}], "pdf")
    m1 = _full_metrics(
        d1, None, "pdf",
        {"element_count_by_type": {"paragraph": 3}},
        {"chunk_boundary_anchors": [
            {"marker": "x", "position": "after"}]})

    d2 = _doc([_e("paragraph", "q1",
                  loc={"paragraph_index": 2})],
              [{"chunk_id": "c", "text": "x",
                "source_element_ids": ["q1"],
                "metadata": {}}], "docx")
    m2 = _full_metrics(d2, None, "docx", None, None)

    m3 = _full_metrics(None, {"code": "E_X"}, "pdf",
                       None, None)

    return [
        {"_doc_id": "d1", "_source_type": "pdf",
         "_pipeline_success": True, "_error_code": None,
         "metrics": m1},
        {"_doc_id": "d2", "_source_type": "docx",
         "_pipeline_success": True, "_error_code": None,
         "metrics": m2},
        {"_doc_id": "d3", "_source_type": "pdf",
         "_pipeline_success": False,
         "_error_code": "E_X", "metrics": m3}]


def _summary():
    return aggregate_summary(_rows())


# ---------- counts / success / silent ----------

def test_real_counts_success_silent_batch237():
    s = _summary()
    assert s["counts"]["element_count_total"] == {
        "sum": 3, "participating_docs": 2}
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 2, "total": 3,
        "rate": 0.6666666666666666}
    assert s["silent_drop_total"] == 2


# ---------- 定位通道分离 ----------

def test_locator_channel_split_batch237():
    ra = _summary()["ratio_macro_averages"]
    assert ra["pdf_locator_valid_ratio"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 2}
    assert ra["docx_locator_valid_ratio"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 2}


def test_schema_valid_two_participants_batch237():
    ra = _summary()["ratio_macro_averages"]
    assert ra["schema_valid"] == {
        "macro_average": 1.0, "participating_docs": 2,
        "not_evaluated": 1}


# ---------- 全 null 指标 ----------

def test_boundary_f1_zero_participation_batch237():
    ra = _summary()["ratio_macro_averages"]
    assert ra["chunk_boundary_f1"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 3}


def test_figure_caption_absent_from_ratios_batch237():
    ra = _summary()["ratio_macro_averages"]
    assert "figure_caption_f1" not in ra
    assert "figure_caption_precision" not in ra
    assert "figure_caption_recall" not in ra
    assert len(ra) == 12


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(rpt)


def test_source_key_lines_batch237():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src
    assert "_COUNT_METRICS" in src


# ---------- forbidden tokens 第五百一十批 ----------

def test_source_no_eval_batch237():
    assert "eval(" not in _src()


def test_source_no_exec_batch237():
    assert "exec(" not in _src()


def test_source_no_compile_batch237():
    assert "compile(" not in _src()


def test_source_no_globals_batch237():
    assert "globals(" not in _src()


def test_source_no_locals_batch237():
    assert "locals(" not in _src()


def test_source_no_os_system_batch237():
    assert "os.system" not in _src()


def test_source_no_popen_batch237():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch237():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch237():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch237():
    assert "socket" not in _src()


def test_source_no_requests_batch237():
    assert "requests" not in _src()


def test_source_no_urllib_batch237():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch237():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch237():
    assert "yield" not in _src()


def test_source_no_async_await_batch237():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch237():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch237():
    assert _src().count("subprocess.run") == 2
