"""evaluation/report.py 第二百一十一轮 edges 测试（Round 767）。

补强 edges77-78 未触及的角度（第一百三十一批）。

新角度：
- counts 值 0 参与（0 is not None）：{"sum": 0, "participating_docs": 1}，
  与缺键 / 值 None 的 {"sum": None, "participating_docs": 0} 对照
- success_rates：metrics 完全缺 pipeline_success → total 仍计 1、
  success_count 0、rate 0.0（total 无条件 len(per_doc)）
- ratio 混合 1.0 / None / 0.0 → macro 0.5、participating 2、
  not_evaluated 1
- silent_drop [0] → 0（列表非空短路，0 不是 None）；2+None+3 → 5
- get_git_provenance 不存在的 cwd → OSError 分支 → 全默认
- rev-parse rc 0 但 stdout 全空白 → commit None（strip or None），
  porcelain 干净 → dirty False（两条命令独立）
- build_devset_section 键序 6 键固定
- build_provenance max_chars float 1.9 → int → 1（截断非四舍五入）
- run_timestamp_iso 可 fromisoformat 解析且带 tzinfo
- ratio 全 None ×3 → macro None participating 0 not_evaluated 3
- success rate 1/3 精确 float
- get_dependency_versions 三键有序、值全 str（已安装）
- forbidden tokens 第二百三十七批（subprocess 用 run 计数 2 替代）
"""

from __future__ import annotations

import inspect
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation.report import (
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


def _m(**kw):
    d = {n: {"value": None, "reason": "x"} for n in
         ("element_count_total", "pipeline_success", "schema_valid")}
    d.update(kw)
    return {"metrics": d}


# ---------- counts 0 参与 ----------

def test_counts_zero_participates_batch54():
    out = aggregate_summary([_m(element_count_total={"value": 0,
                                                     "reason": None})])
    assert out["counts"]["element_count_total"] == {"sum": 0,
                                                    "participating_docs": 1}


def test_counts_absent_and_none_excluded_batch54():
    out = aggregate_summary([
        _m(),
        _m(element_count_total={"value": None, "reason": "r"}),
    ])
    assert out["counts"]["element_count_total"] == {"sum": None,
                                                    "participating_docs": 0}


# ---------- success total 无条件 ----------

def test_success_missing_metric_still_counted_batch54():
    out = aggregate_summary([{"metrics": {}}])
    assert out["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 1, "rate": 0.0}


def test_success_rate_one_third_batch54():
    docs = [_m(pipeline_success={"value": v, "reason": None})
            for v in (True, False, False)]
    out = aggregate_summary(docs)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["rate"] == 1 / 3


# ---------- ratio 混合 ----------

def test_ratio_mixed_macro_half_batch54():
    out = aggregate_summary([
        _m(schema_valid={"value": 1.0, "reason": None}),
        _m(),
        _m(schema_valid={"value": 0.0, "reason": None}),
    ])
    assert out["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 0.5, "participating_docs": 2, "not_evaluated": 1}


def test_ratio_all_none_three_docs_batch54():
    out = aggregate_summary([_m(), _m(), _m()])
    assert out["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": None, "participating_docs": 0, "not_evaluated": 3}


# ---------- silent_drop ----------

def test_silent_drop_zero_sum_not_none_batch54():
    out = aggregate_summary([_m(silent_drop_count={"value": 0,
                                                   "reason": None})])
    assert out["silent_drop_total"] == 0


def test_silent_drop_skips_none_batch54():
    out = aggregate_summary([
        _m(silent_drop_count={"value": 2, "reason": None}),
        _m(),
        _m(silent_drop_count={"value": 3, "reason": None}),
    ])
    assert out["silent_drop_total"] == 5


# ---------- git provenance ----------

def test_git_provenance_nonexistent_cwd_batch54():
    assert get_git_provenance(Path("Z:/no/such/dir")) == {
        "git_commit": None, "git_dirty": True}


class _FakeR:
    def __init__(self, rc, out):
        self.returncode = rc
        self.stdout = out


def test_revparse_empty_stdout_commit_none_batch54():
    with patch.object(report_mod.subprocess, "run",
                      side_effect=[_FakeR(0, "   \n"), _FakeR(0, "")]):
        assert get_git_provenance(Path(".")) == {
            "git_commit": None, "git_dirty": False}


# ---------- devset 键序 ----------

class _FakeMan:
    devset_status = "incomplete"
    file_count = 2
    content_group_count = 1
    pdf_count = 1
    docx_count = 1
    categories_covered = ["a"]


def test_devset_section_key_order_batch54():
    assert list(build_devset_section(_FakeMan()).keys()) == [
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered"]


# ---------- build_provenance ----------

def test_max_chars_float_truncates_batch54():
    with patch.object(report_mod, "get_git_provenance",
                      lambda r: {"git_commit": "c", "git_dirty": False}), \
            patch.object(report_mod, "get_dependency_versions",
                         lambda: {}):
        p = build_provenance(Path("."), "fallback", 1.9, None)
    assert p["max_chars"] == 1
    assert isinstance(p["max_chars"], int)


def test_timestamp_parseable_with_tz_batch54():
    with patch.object(report_mod, "get_git_provenance",
                      lambda r: {"git_commit": "c", "git_dirty": False}), \
            patch.object(report_mod, "get_dependency_versions",
                         lambda: {}):
        p = build_provenance(Path("."), "fallback", 800, None)
    ts = datetime.fromisoformat(p["run_timestamp_iso"])
    assert ts.tzinfo is not None


# ---------- dependency versions ----------

def test_dependency_versions_three_str_batch54():
    dv = get_dependency_versions()
    assert list(dv) == ["pdfplumber", "python-docx", "pypdfium2"]
    assert all(isinstance(v, str) for v in dv.values())


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_zero_guard_lines_batch54():
    src = _src()
    assert 'if values:' in src
    assert "if silent_vals" in src
    assert "sum(values) / len(values)" in src
    assert "r.stdout.strip() or None" in src


# ---------- forbidden tokens 第二百三十七批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_subprocess_run_count_two_batch54():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch54():
    assert "open(" not in _src()
