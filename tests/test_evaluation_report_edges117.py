"""evaluation/report.py 第四百七十七轮 edges 测试（Round 1033）。

补强 edges116 未触及的角度（第四百零九批，probe 实证）。

新角度（全 summary 离散板单次聚合）：
- 3 行 metrics 板上 12 ratio 各持不同参与签名
  （participating 0/1/2/3 全都出现、not_evaluated
  = 3 - participating 恒等），macro 各自独立算——
  R1019 矩阵全列同参与（2/3），本板每列不同
- float 工件锁定：cb_f1 (0.8+0.4)/2 ==
  0.6000000000000001（非 0.6）；recall (0+1+1)/3 ==
  0.6666666666666666；text_preservation True/False
  参与 macro 得 0.5
- counts 半参与（5+None+7 → sum 12 participating 2）、
  success 2/3、silent [2,0,None] → 2（0 值参与、
  null 剔除）同屏
- forbidden tokens 第五百零四批（open 0；subprocess
  是本模块合法依赖不列禁词，run 恰 2）
"""

from __future__ import annotations

import inspect

import evaluation.report as rpt
from evaluation.report import aggregate_summary

V = lambda v: {"value": v, "reason": None}

_M1 = {"schema_valid": V(1.0),
       "pdf_locator_valid_ratio": V(None),
       "docx_locator_valid_ratio": V(1.0),
       "image_resource_exists_ratio": V(0.0),
       "chunk_reference_intact_ratio": V(None),
       "text_preservation_equal": V(True),
       "text_char_multiset_precision": V(1.0),
       "text_char_multiset_recall": V(0.0),
       "heading_boundary_compliance": V(None),
       "chunk_boundary_precision": V(1.0),
       "chunk_boundary_recall": V(None),
       "chunk_boundary_f1": V(0.8),
       "element_count_total": V(5),
       "pipeline_success": V(True),
       "silent_drop_count": V(2)}

_M2 = {"schema_valid": V(0.5),
       "image_resource_exists_ratio": V(0.0),
       "text_preservation_equal": V(False),
       "text_char_multiset_precision": V(0.0),
       "text_char_multiset_recall": V(1.0),
       "heading_boundary_compliance": V(0.5),
       "chunk_boundary_f1": V(0.4),
       "element_count_total": V(7),
       "pipeline_success": V(True),
       "silent_drop_count": V(0)}

_M3 = {"schema_valid": V(None),
       "image_resource_exists_ratio": V(1.0),
       "chunk_reference_intact_ratio": V(1.0),
       "text_preservation_equal": V(None),
       "text_char_multiset_recall": V(1.0),
       "chunk_boundary_precision": V(0.0),
       "chunk_boundary_recall": V(1.0),
       "pipeline_success": V(False)}


def _board():
    def row(sid, m):
        return {"_doc_id": sid, "_source_type": "pdf",
                "_pipeline_success": True,
                "_error_code": None, "metrics": m}
    return aggregate_summary(
        [row("d1", _M1), row("d2", _M2), row("d3", _M3)])


# ---------- 参与签名 0/1/2/3 全出现 ----------

def test_participation_signatures_batch231():
    s = _board()
    ra = s["ratio_macro_averages"]
    sig = {ra[n]["participating_docs"]
           for n in ra}
    assert sig == {0, 1, 2, 3}
    assert all(ra[n]["not_evaluated"]
               == 3 - ra[n]["participating_docs"]
               for n in ra)


def test_specific_ratio_averages_batch231():
    ra = _board()["ratio_macro_averages"]
    assert ra["schema_valid"] == {
        "macro_average": 0.75, "participating_docs": 2,
        "not_evaluated": 1}
    assert ra["pdf_locator_valid_ratio"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 3}
    assert ra["docx_locator_valid_ratio"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 2}
    assert ra["image_resource_exists_ratio"] == {
        "macro_average": 1 / 3, "participating_docs": 3,
        "not_evaluated": 0}


# ---------- float 工件 ----------

def test_float_artifacts_batch231():
    ra = _board()["ratio_macro_averages"]
    assert ra["chunk_boundary_f1"]["macro_average"] == \
        0.6000000000000001
    assert ra["text_char_multiset_recall"][
        "macro_average"] == 0.6666666666666666
    assert ra["text_preservation_equal"] == {
        "macro_average": 0.5, "participating_docs": 2,
        "not_evaluated": 1}


# ---------- counts / success / silent 同屏 ----------

def test_counts_success_silent_board_batch231():
    s = _board()
    assert s["counts"]["element_count_total"] == {
        "sum": 12, "participating_docs": 2}
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 2, "total": 3,
        "rate": 0.6666666666666666}
    assert s["silent_drop_total"] == 2


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(rpt)


def test_source_key_lines_batch231():
    src = _src()
    assert ("not_eval = len(per_doc_results)"
            " - len(values)") in src
    assert "macro = sum(values) / len(values)" in src
    assert ("summary[\"silent_drop_total\"] ="
            " sum(silent_vals) if silent_vals else None") \
        in src


# ---------- forbidden tokens 第五百零四批 ----------

def test_source_no_eval_batch231():
    assert "eval(" not in _src()


def test_source_no_exec_batch231():
    assert "exec(" not in _src()


def test_source_no_compile_batch231():
    assert "compile(" not in _src()


def test_source_no_globals_batch231():
    assert "globals(" not in _src()


def test_source_no_locals_batch231():
    assert "locals(" not in _src()


def test_source_no_os_system_batch231():
    assert "os.system" not in _src()


def test_source_no_popen_batch231():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch231():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch231():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch231():
    assert "socket" not in _src()


def test_source_no_requests_batch231():
    assert "requests" not in _src()


def test_source_no_urllib_batch231():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch231():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch231():
    assert "yield" not in _src()


def test_source_no_async_await_batch231():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch231():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch231():
    assert _src().count("subprocess.run") == 2
