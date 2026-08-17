"""evaluation/report.py 第三百六十五轮 edges 测试（Round 921）。

补强 edges100 未触及的角度（第二百九十七批，probe 实证）。

新角度：
- build_provenance：max_chars 800.0 → int 800、-5 原样透传；
  parser_version None 透传
- ratio 聚合遇 bool True 按整数 1 入算：[True, 0.5] →
  macro 0.75（bool-as-int 怪癖）
- success 统计严格 `is True`：value 1（int）不计入、True 计入
  → 1/2 = 0.5
- counts 求和 True + 2 → 3
- get_git_provenance 接受 str 型 project_root（非 git 目录 →
  {None, False}）
- 三版本常量：MANIFEST_VERSION "1.0" 与 EVALUATOR/
  REPORT "1.1" 并存（跨模块分层锁死）
- build_devset_section：categories_covered 每次新 list
  （property 非缓存）+ 全 6 键有序
- forbidden tokens 第三百九十一批（subprocess.run 恰 2 次）
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import evaluation
import evaluation.report as report_mod
from evaluation.report import (
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_git_provenance,
)


def _cp(rc, out):
    return CompletedProcess(args=[], returncode=rc, stdout=out,
                            stderr="")


# ---------- build_provenance 类型转换 ----------

def test_provenance_max_chars_float_to_int_batch119(tmp_path):
    with patch("subprocess.run",
               side_effect=[_cp(0, "c1\n"), _cp(0, "")]), \
         patch("evaluation.report.get_dependency_versions",
               return_value={"a": "1"}):
        p = build_provenance(tmp_path, "fallback", 800.0, None)
    assert p["max_chars"] == 800
    assert isinstance(p["max_chars"], int)
    assert p["parser_version"] is None


def test_provenance_negative_max_chars_batch119(tmp_path):
    with patch("subprocess.run",
               side_effect=[_cp(0, "c1\n"), _cp(0, "")]), \
         patch("evaluation.report.get_dependency_versions",
               return_value={}):
        p = build_provenance(tmp_path, "kreuzberg", -5, "3.1")
    assert p["max_chars"] == -5
    assert p["parser_name"] == "kreuzberg"
    assert p["parser_version"] == "3.1"


# ---------- bool-as-int 聚合怪癖 ----------

def test_ratio_bool_true_in_average_batch119():
    s = aggregate_summary([
        {"metrics": {"schema_valid": {"value": True}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
    ])
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 0.75, "participating_docs": 2,
        "not_evaluated": 0}


def test_success_strict_is_true_batch119():
    s = aggregate_summary([
        {"metrics": {"pipeline_success": {"value": 1}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ])
    assert s["success_rates"] == {"pipeline_success": {
        "success_count": 1, "total": 2, "rate": 0.5}}


def test_counts_bool_true_sums_as_one_batch119():
    s = aggregate_summary([
        {"metrics": {"element_count_total": {"value": True}}},
        {"metrics": {"element_count_total": {"value": 2}}},
    ])
    assert s["counts"] == {"element_count_total": {
        "sum": 3, "participating_docs": 2}}


# ---------- str project_root ----------

def test_git_provenance_str_root_batch119():
    with tempfile.TemporaryDirectory() as td:
        out = get_git_provenance(td)
    assert out == {"git_commit": None, "git_dirty": False}
    assert isinstance(out["git_dirty"], bool)


# ---------- 版本常量分层 ----------

def test_version_constants_layered_batch119():
    assert evaluation.MANIFEST_VERSION == "1.0"
    assert evaluation.EVALUATOR_VERSION == "1.1"
    assert evaluation.REPORT_VERSION == "1.1"


# ---------- build_devset_section ----------

class _FakeM:
    devset_status = "incomplete"
    file_count = 0
    content_group_count = 0
    pdf_count = 0
    docx_count = 0
    categories = ("a", "b")

    @property
    def categories_covered(self):
        return sorted(self.categories)


def test_devset_section_key_order_and_new_list_batch119():
    d = build_devset_section(_FakeM())
    assert list(d) == ["status", "file_count", "content_group_count",
                       "pdf_count", "docx_count",
                       "categories_covered"]
    assert d["categories_covered"] == ["a", "b"]
    fm = _FakeM()
    first = build_devset_section(fm)["categories_covered"]
    second = build_devset_section(fm)["categories_covered"]
    assert first is not second  # property 每次新建


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch119():
    src = _src()
    assert '"max_chars": int(max_chars),' in src
    assert 'if r["metrics"].get(name, {}).get("value") is True' in src
    assert "macro = sum(values) / len(values)" in src


# ---------- forbidden tokens 第三百九十一批 ----------

def test_source_no_eval_batch119():
    assert "eval(" not in _src()


def test_source_no_exec_batch119():
    assert "exec(" not in _src()


def test_source_no_compile_batch119():
    assert "compile(" not in _src()


def test_source_no_globals_batch119():
    assert "globals(" not in _src()


def test_source_no_locals_batch119():
    assert "locals(" not in _src()


def test_source_no_os_system_batch119():
    assert "os.system" not in _src()


def test_source_no_subprocess_run_count_batch119():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch119():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch119():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch119():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch119():
    assert "socket" not in _src()


def test_source_no_requests_batch119():
    assert "requests" not in _src()


def test_source_no_urllib_batch119():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch119():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch119():
    assert "yield" not in _src()


def test_source_no_async_await_batch119():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch119():
    assert "open(" not in _src()
