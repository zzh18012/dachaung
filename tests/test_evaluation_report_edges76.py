"""evaluation/report.py 第二百零四轮 edges 测试（Round 746）。

补强 edges74/edges75 未触及的角度（第一百一十一批）。

新角度：
- 依赖版本选择性失败：仅 pypdfium2 抛 PackageNotFoundError →
  其余照常返回、目标 None（逐包独立 try）
- aggregate_summary 不改写输入（deepcopy 快照比对）
- 值类型未守卫：ratio 值传字符串 → sum/len TypeError（现状记录）
- counts 值 True（bool）→ sum 1（bool ⊂ int 被求和，与
  jsonschema boolean 严格性对照）
- silent_drop 浮点值求和 → 4.0（float 类型保真）
- build_provenance.dependencies 与 get_dependency_versions() 全等
- forbidden tokens 第二百一十六批
"""

from __future__ import annotations

import copy
import importlib.metadata as im
import inspect
from pathlib import Path

import pytest

import evaluation.report as report_mod
from evaluation.report import (
    aggregate_summary,
    build_provenance,
    get_dependency_versions,
)

ROOT = Path(__file__).resolve().parents[1]


def _doc(metrics):
    return {"metrics": metrics}


def _m(v):
    return {"value": v}


# ---------- 依赖选择性失败 ----------

def test_dependency_selective_package_failure_batch54(monkeypatch):
    real = im.version

    def selective(pkg):
        if pkg == "pypdfium2":
            raise im.PackageNotFoundError(pkg)
        return real(pkg)
    monkeypatch.setattr(im, "version", selective)
    v = get_dependency_versions()
    assert v["pypdfium2"] is None
    assert v["pdfplumber"] is not None
    assert v["python-docx"] is not None


# ---------- 输入不变式 ----------

def test_aggregate_does_not_mutate_input_batch54():
    inp = [{"metrics": {"element_count_total": {"value": 3},
                        "pipeline_success": {"value": True}}}]
    snap = copy.deepcopy(inp)
    aggregate_summary(inp)
    assert inp == snap


# ---------- 值类型未守卫 ----------

def test_ratio_string_value_raises_typeerror_batch54():
    with pytest.raises(TypeError):
        aggregate_summary([_doc({"text_preservation_equal": _m("0.5")})])


def test_counts_bool_value_sums_as_int_batch54():
    s = aggregate_summary([_doc({"element_count_total": _m(True)})])
    assert s["counts"]["element_count_total"] == {"sum": 1,
                                                  "participating_docs": 1}


def test_silent_drop_float_sum_batch54():
    s = aggregate_summary([_doc({"silent_drop_count": _m(1.5)}),
                           _doc({"silent_drop_count": _m(2.5)})])
    assert s["silent_drop_total"] == 4.0
    assert isinstance(s["silent_drop_total"], float)


# ---------- provenance 集成 ----------

def test_provenance_dependencies_full_equality_batch54():
    prov = build_provenance(ROOT, "fallback", 800, None)
    assert prov["dependencies"] == get_dependency_versions()
    assert set(prov["dependencies"]) == {
        "pdfplumber", "python-docx", "pypdfium2"}


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(report_mod)


def test_source_per_package_try_batch54():
    src = _src()
    assert 'for pkg in ("pdfplumber", "python-docx", "pypdfium2"):' in src
    assert "except importlib.metadata.PackageNotFoundError:" in src


# ---------- forbidden tokens 第二百一十六批 ----------

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
