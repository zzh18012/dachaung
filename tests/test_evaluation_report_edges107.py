"""evaluation/report.py 第四百零七轮 edges 测试（Round 963）。

补强 edges106 未触及的角度（第三百三十九批，probe 实证）。

新角度：
- parser_version / parser_name 原样透传（"1.2.3" +
  "kreuzberg"）
- 越界值不钳制只平均：[2.0, -1.0] → macro 0.5
  （2 + -1 = 1，除 2；无 [0,1] 校验）
- 纯函数性：入参 per_doc 不被修改；重复调用结果全等
- 依赖缺失兜底：importlib.metadata.version 全抛
  PackageNotFoundError → 三键全 None
- summary 四键有序 [counts, success_rates,
  ratio_macro_averages, silent_drop_total]
- 全 0 → 0.0；全 1 → 1.0
- forbidden tokens 第四百三十三批（open 0 +
  subprocess.run 恰 2）
"""

from __future__ import annotations

import copy
import importlib.metadata as im
import inspect
from pathlib import Path
from unittest.mock import patch

import evaluation.report as rpt
from evaluation.report import (
    aggregate_summary,
    build_provenance,
    get_dependency_versions,
)


# ---------- 透传 ----------

def test_provenance_passthrough_batch161():
    with patch.object(rpt, "get_git_provenance",
                      return_value={"git_commit": "c",
                                    "git_dirty": False}):
        p = build_provenance(Path("."), "kreuzberg", 800,
                             "1.2.3")
    assert p["parser_version"] == "1.2.3"
    assert p["parser_name"] == "kreuzberg"


# ---------- 越界值不钳制 ----------

def test_out_of_range_averaged_batch161():
    per = [{"metrics": {"schema_valid": {"value": 2.0}}},
           {"metrics": {"schema_valid": {"value": -1.0}}}]
    assert aggregate_summary(per)["ratio_macro_averages"][
        "schema_valid"] == {"macro_average": 0.5,
                            "participating_docs": 2,
                            "not_evaluated": 0}


# ---------- 纯函数性 ----------

def test_pure_function_batch161():
    per = [{"metrics": {"element_count_total": {"value": 5}}}]
    snapshot = copy.deepcopy(per)
    s1 = aggregate_summary(per)
    s2 = aggregate_summary(per)
    assert per == snapshot
    assert s1 == s2


# ---------- 依赖缺失兜底 ----------

def test_missing_dependencies_none_batch161():
    with patch.object(im, "version",
                      side_effect=im.PackageNotFoundError):
        d = get_dependency_versions()
    assert d == {"pdfplumber": None, "python-docx": None,
                 "pypdfium2": None}


# ---------- summary 键序 ----------

def test_summary_key_order_batch161():
    assert list(aggregate_summary([])) == [
        "counts", "success_rates", "ratio_macro_averages",
        "silent_drop_total"]


# ---------- 全 0 / 全 1 ----------

def test_all_zeros_and_ones_batch161():
    z = aggregate_summary([
        {"metrics": {"schema_valid": {"value": 0.0}}},
        {"metrics": {"schema_valid": {"value": 0.0}}}])
    assert z["ratio_macro_averages"]["schema_valid"][
        "macro_average"] == 0.0
    o = aggregate_summary(
        [{"metrics": {"schema_valid": {"value": 1.0}}}])
    assert o["ratio_macro_averages"]["schema_valid"][
        "macro_average"] == 1.0


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(rpt)


def test_source_key_lines_batch161():
    src = _src()
    assert "except importlib.metadata.PackageNotFoundError:" in src
    assert "versions[pkg] = None" in src
    assert 'for pkg in ("pdfplumber", "python-docx", "pypdfium2"):' in src
    assert '"run_timestamp_iso": datetime.now().astimezone().isoformat(),' in src


# ---------- forbidden tokens 第四百三十三批 ----------

def test_source_no_eval_batch161():
    assert "eval(" not in _src()


def test_source_no_exec_batch161():
    assert "exec(" not in _src()


def test_source_no_compile_batch161():
    assert "compile(" not in _src()


def test_source_no_globals_batch161():
    assert "globals(" not in _src()


def test_source_no_locals_batch161():
    assert "locals(" not in _src()


def test_source_no_os_system_batch161():
    assert "os.system" not in _src()


def test_source_no_popen_batch161():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch161():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch161():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch161():
    assert "socket" not in _src()


def test_source_no_requests_batch161():
    assert "requests" not in _src()


def test_source_no_urllib_batch161():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch161():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch161():
    assert "yield" not in _src()


def test_source_no_async_await_batch161():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch161():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch161():
    assert _src().count("subprocess.run") == 2
