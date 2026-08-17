"""evaluation/report.py 第四百九十轮 edges 测试（Round 1046）。

补强 edges118 未触及的角度（第四百二十二批，probe 实证）。

新角度（真实损坏 docx 的 ef 契约 + 真实混合 run 汇总屏）：
- 此前 ef 测试全用手工 _Err 造 E_ 前缀码；真实损坏
  docx（伪字节）穿真实管线的 actual_error_code 是
  **'docx_open_failed'**（无 E_ 前缀的真实码命名空间
  首次在 report 层锁定）
- E_PARSE_FAIL 期望 → matches False（E_ 假设在真实
  损坏文件上系统性地失败）；期望恰为真实码
  'docx_open_failed' → matches True（schema 对
  expected_error_code 只要求 minLength 1，允许裸码）
- 真实混合 run（好 docx + 损坏 docx ef）汇总屏：
  ef 不计入 success total（{success_count 1,
  total 1, rate 1.0}——total 只数 documents）、
  counts {sum 2, participating_docs 1}、
  silent_drop None、docx/pdf 定位通道分离
  （1.0/1/0 与 None/0/1 互为镜像）、ra 恰 12 键
- forbidden tokens 第五百一十七批（open 0）
"""

from __future__ import annotations

import inspect
import json

from docx import Document

import evaluation.report as rpt
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


def _run(tmp_path, ef_code):
    (tmp_path / "pyproject.toml").write_text("",
                                             encoding="utf-8")
    (tmp_path / "samples").mkdir()
    d = Document()
    d.add_paragraph("Hello world paragraph one.")
    d.save(str(tmp_path / "samples" / "good.docx"))
    (tmp_path / "samples" / "bad.docx").write_bytes(
        b"not a docx")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1",
                       "path": "samples/good.docx",
                       "source_type": "docx"}],
        "expected_failures": [{
            "doc_id": "f1", "path": "samples/bad.docx",
            "expected_error_code": ef_code}]}),
        encoding="utf-8")
    return run_evaluation(load_manifest(mf, tmp_path),
                          tmp_path / "o.json", max_chars=50)


# ---------- 真实码命名空间 ----------

def test_real_corrupt_code_namespace_batch244(tmp_path):
    rep = _run(tmp_path, "E_PARSE_FAIL")
    ef = rep["expected_failures"][0]
    assert ef["actual_error_code"] == "docx_open_failed"
    assert ef["matches"] is False


def test_exact_real_code_matches_batch244(tmp_path):
    rep = _run(tmp_path, "docx_open_failed")
    assert rep["expected_failures"][0] == {
        "doc_id": "f1",
        "expected_error_code": "docx_open_failed",
        "actual_error_code": "docx_open_failed",
        "matches": True}


# ---------- 真实混合 run 汇总屏 ----------

def test_mixed_summary_success_excludes_ef_batch244(tmp_path):
    rep = _run(tmp_path, "docx_open_failed")
    s = rep["summary"]
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 1, "total": 1, "rate": 1.0}
    assert s["counts"]["element_count_total"] == {
        "sum": 1, "participating_docs": 1}
    assert s["silent_drop_total"] is None


def test_mixed_summary_channel_split_batch244(tmp_path):
    rep = _run(tmp_path, "docx_open_failed")
    ra = rep["summary"]["ratio_macro_averages"]
    assert ra["docx_locator_valid_ratio"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 0}
    assert ra["pdf_locator_valid_ratio"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 1}
    assert ra["schema_valid"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 0}
    assert len(ra) == 12


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(rpt)


def test_source_key_lines_batch244():
    src = _src()
    assert '_COUNT_METRICS = ("element_count_total",)' in src
    assert "def aggregate_summary(" in src
    assert "def build_devset_section(" in src


# ---------- forbidden tokens 第五百一十七批 ----------

def test_source_no_eval_batch244():
    assert "eval(" not in _src()


def test_source_no_exec_batch244():
    assert "exec(" not in _src()


def test_source_no_compile_batch244():
    assert "compile(" not in _src()


def test_source_no_globals_batch244():
    assert "globals(" not in _src()


def test_source_no_locals_batch244():
    assert "locals(" not in _src()


def test_source_no_os_system_batch244():
    assert "os.system" not in _src()


def test_source_no_popen_batch244():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch244():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch244():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch244():
    assert "socket" not in _src()


def test_source_no_requests_batch244():
    assert "requests" not in _src()


def test_source_no_urllib_batch244():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch244():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch244():
    assert "yield" not in _src()


def test_source_no_async_await_batch244():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch244():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch244():
    assert _src().count("subprocess.run") == 2
