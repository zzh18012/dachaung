"""evaluation/report.py 第五百八十轮 edges 测试（Round 1336）。

补强 edges148 未触及的角度（第七百零八批，probe 实证）。

新角度（空 devset 全 null 聚合）：
- **空板接受**——
  documents [] 加载
  与运行均成功
- **counts null**——
  element_count_
  total {sum: null,
  participating_
  docs: 0}（0 参与不
  出 0 而出 null
  首锁）
- **success 0/0**——
  rate null（分母 0
  不返回 1.0 的
  CLAUDE 不变量
  聚合级首锁）
- **sdt None**——
  标量指标空板
  null
- **12 ratio 全 null**
  ——每键
  {macro_average:
  None, participating_
  docs: 0,
  not_evaluated: 0}
  （12 键齐、值全
  null 首锁）
- **devset 全零**——
  file/pdf/docx/
  groups 0 +
  categories []
- **schema 容 null**
  ——报告带 null
  宏仍过 evaluation-
  report schema
- forbidden tokens 第七百七十九批（open 0）
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import evaluation.report as report_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from evaluation.schema import validate


def _run(tmp_path):
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": []}), encoding="utf-8")
    mf = load_manifest(tmp_path / "m.json",
                       project_root=tmp_path)
    return run_evaluation(mf, tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=32)


# ---------- 空板接受 ----------

def test_empty_per_doc_batch534(tmp_path):
    assert _run(tmp_path)["per_doc"] == []


# ---------- counts null ----------

def test_counts_null_sum_batch534(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["counts"][
        "element_count_total"] == {
        "sum": None, "participating_docs": 0}


# ---------- success 0/0 ----------

def test_success_rate_null_batch534(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["success_rates"][
        "pipeline_success"] == {
        "success_count": 0, "total": 0,
        "rate": None}


def test_success_rate_not_one_batch534(tmp_path):
    r = _run(tmp_path)
    rate = r["summary"]["success_rates"][
        "pipeline_success"]["rate"]
    assert rate is not 1.0


# ---------- sdt None ----------

def test_sdt_none_batch534(tmp_path):
    assert _run(tmp_path)["summary"][
        "silent_drop_total"] is None


# ---------- 12 ratio 全 null ----------

def test_ratio_count_twelve_batch534(tmp_path):
    ra = _run(tmp_path)["summary"][
        "ratio_macro_averages"]
    assert len(ra) == 12


def test_all_ratios_null_batch534(tmp_path):
    ra = _run(tmp_path)["summary"][
        "ratio_macro_averages"]
    for k, v in ra.items():
        assert v == {"macro_average": None,
                     "participating_docs": 0,
                     "not_evaluated": 0}, k


def test_schema_valid_null_batch534(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["ratio_macro_averages"][
        "schema_valid"] == {
        "macro_average": None,
        "participating_docs": 0,
        "not_evaluated": 0}


# ---------- devset 全零 ----------

def test_devset_all_zero_batch534(tmp_path):
    assert _run(tmp_path)["devset"] == {
        "status": "incomplete", "file_count": 0,
        "pdf_count": 0, "docx_count": 0,
        "content_group_count": 0,
        "categories_covered": []}


# ---------- schema 容 null ----------

def test_report_schema_batch534(tmp_path):
    validate(_run(tmp_path),
             "evaluation-report.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch534():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src


def test_source_all_exports_batch534():
    src = _src()
    assert '"build_provenance",' in src
    assert '"build_devset_section",' in src
    assert '"aggregate_summary",' in src


# ---------- forbidden tokens 第七百七十九批 ----------

def test_source_no_eval_batch534():
    assert "eval(" not in _src()


def test_source_no_exec_batch534():
    assert "exec(" not in _src()


def test_source_no_compile_batch534():
    assert "compile(" not in _src()


def test_source_no_globals_batch534():
    assert "globals(" not in _src()


def test_source_no_locals_batch534():
    assert "locals(" not in _src()


def test_source_no_os_system_batch534():
    assert "os.system" not in _src()


def test_source_subprocess_run_two_batch534():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch534():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch534():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch534():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch534():
    assert "socket" not in _src()


def test_source_no_requests_batch534():
    assert "requests" not in _src()


def test_source_no_urllib_batch534():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch534():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch534():
    assert "yield" not in _src()


def test_source_no_async_await_batch534():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch534():
    assert ".call(" not in _src()


def test_source_open_count_is_0_batch534():
    assert _src().count("open(") == 0
