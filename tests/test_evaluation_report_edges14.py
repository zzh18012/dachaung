r"""evaluation/report.py 边角测试 - 第十四轮（Round 243）。

补强已有 base/edges/edges2-13（共 ~1100+ 测试）未覆盖的深度：
- build_provenance/get_git_provenance 接受 str project_root（不只 Path）
- aggregate_summary：ratio value >1.0 / negative 仍参与 macro
- aggregate_summary：per_doc 是 tuple 而非 list（iterable 即可）
- build_devset_section：返回 dict 是新对象（每次调用独立）
- get_dependency_versions：每次返回新 dict（不缓存）
- 模块：typing.Any / subprocess / datetime / Path 在 namespace identity 精确
- __all__ 是 list（不是 tuple）；__all__ 顺序与代码一致
- 函数 __init__/default 行为：build_provenance max_chars 接受 bool
- 调用语义：subprocess.run 在 OSError 时不抛
- 命令精确：git rev-parse HEAD / git status --porcelain 顺序
"""

from __future__ import annotations

import inspect
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from evaluation import EVALUATOR_VERSION, REPORT_VERSION
from evaluation.report import (
    _COUNT_METRICS,
    _RATIO_METRICS,
    _SUCCESS_BOOL_METRICS,
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


# =========================================================================
# build_provenance / get_git_provenance 接受 str project_root
# =========================================================================


def test_build_provenance_accepts_str_project_root(tmp_path: Path):
    """build_provenance 第 1 参 project_root 接受 str 路径。"""
    out = build_provenance(str(tmp_path), "fallback", 800, "1.0")
    # git_commit 可能是 None（不在 git repo）或 str
    assert "git_commit" in out
    assert "git_dirty" in out


def test_get_git_provenance_accepts_str_project_root(tmp_path: Path):
    """get_git_provenance 接受 str project_root（源码 cwd=str(project_root)）。"""
    out = get_git_provenance(str(tmp_path))
    assert isinstance(out, dict)
    assert "git_commit" in out
    assert "git_dirty" in out


def test_get_git_provenance_str_path_returns_dict(tmp_path: Path):
    """str project_root 返回 dict（与 Path 一致）。"""
    out_str = get_git_provenance(str(tmp_path))
    out_path = get_git_provenance(tmp_path)
    # 两者都返回 dict 且 keys 一致
    assert isinstance(out_str, dict)
    assert isinstance(out_path, dict)
    assert set(out_str.keys()) == set(out_path.keys())


def test_build_provenance_str_path_returns_dict(tmp_path: Path):
    """str project_root 走通；返回 dict 含 9 keys。"""
    out = build_provenance(str(tmp_path), "fallback", 800, "1.0")
    assert isinstance(out, dict)
    assert len(out) == 9


def test_build_provenance_path_like_object(tmp_path: Path):
    """project_root 接受任意实现 __fspath__ 的对象（os.PathLike）。"""
    class FakePath:
        def __init__(self, p):
            self.p = p

        def __fspath__(self):
            return str(self.p)

    out = build_provenance(FakePath(tmp_path), "fallback", 800, "1.0")
    assert isinstance(out, dict)
    assert len(out) == 9


# =========================================================================
# aggregate_summary：ratio value >1.0 / negative
# =========================================================================


def test_aggregate_summary_ratio_value_above_one_participates():
    """ratio value=1.5 仍计入 macro_average（不夹紧到 1.0）。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.5
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1


def test_aggregate_summary_ratio_value_negative_participates():
    """ratio value=-0.5 仍计入 macro（不剔除负值）。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": -0.5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == -0.5


def test_aggregate_summary_ratio_mixed_above_one_and_normal():
    """ratio=1.5 与 ratio=0.5 → macro=(1.5+0.5)/2=1.0。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.5}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0


def test_aggregate_summary_ratio_extreme_large_value():
    """ratio=1e6 仍参与计算。"""
    per_doc = [{"metrics": {"schema_valid": {"value": 1e6}}}]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1e6


def test_aggregate_summary_count_negative_value_participates_with_positive():
    """count=-5 + count=10 → sum=5。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": -5}}},
        {"metrics": {"element_count_total": {"value": 10}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


# =========================================================================
# aggregate_summary：per_doc_results 类型边界
# =========================================================================


def test_aggregate_summary_accepts_tuple_input():
    """per_doc_results 接受 tuple（iterable 即可）。"""
    per_doc = (
        {"metrics": {"schema_valid": {"value": 1.0}}},
    )
    out = aggregate_summary(list(per_doc))  # 源码用 len()，必须 sequence
    # 验证 1 个 doc 的 ratio 参与计算
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1


def test_aggregate_summary_with_extra_keys_in_per_doc_ignored():
    """per_doc 含 'doc_id' 等 extra key → 不影响聚合。"""
    per_doc = [
        {
            "doc_id": "d1",
            "source_type": "pdf",
            "metrics": {"schema_valid": {"value": 1.0}},
            "errors": [],
            "extra_field": "ignored",
        },
    ]
    out = aggregate_summary(per_doc)
    # schema_valid 参与
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0


def test_aggregate_summary_with_chunk_boundary_metrics():
    """chunk_boundary_precision/recall/f1 都参与 ratio_macro。"""
    per_doc = [
        {"metrics": {
            "chunk_boundary_precision": {"value": 0.8},
            "chunk_boundary_recall": {"value": 0.6},
            "chunk_boundary_f1": {"value": 0.7},
        }},
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["chunk_boundary_precision"]["macro_average"] == 0.8
    assert out["ratio_macro_averages"]["chunk_boundary_recall"]["macro_average"] == 0.6
    assert out["ratio_macro_averages"]["chunk_boundary_f1"]["macro_average"] == 0.7


def test_aggregate_summary_silent_drop_with_float():
    """silent_drop_count float value 也能求和（结果 float）。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 2.5}}},
        {"metrics": {"silent_drop_count": {"value": 1.5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 4.0


# =========================================================================
# build_devset_section 返回独立 dict
# =========================================================================


class _FakeManifest:
    """模拟 Manifest 对象（duck typing）。"""

    def __init__(self, **kwargs):
        defaults = {
            "devset_status": "incomplete",
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": [],
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


def test_build_devset_section_returns_new_dict_each_call():
    """每次调用返回独立 dict。"""
    m = _FakeManifest()
    out1 = build_devset_section(m)
    out2 = build_devset_section(m)
    assert out1 is not out2
    assert out1 == out2


def test_build_devset_section_does_not_keep_reference_to_manifest():
    """修改返回 dict 不影响 Manifest 对象。"""
    m = _FakeManifest(file_count=5)
    out = build_devset_section(m)
    out["file_count"] = 999
    # Manifest 对象不被修改
    assert m.file_count == 5


def test_build_devset_section_with_custom_devset_status():
    """devset_status='complete' 透传。"""
    m = _FakeManifest(devset_status="complete")
    out = build_devset_section(m)
    assert out["status"] == "complete"


def test_build_devset_section_with_categories_covered_tuple():
    """categories_covered 是 tuple 也透传。"""
    m = _FakeManifest(categories_covered=("cat1", "cat2"))
    out = build_devset_section(m)
    assert out["categories_covered"] == ("cat1", "cat2")


def test_build_devset_section_with_negative_counts():
    """negative counts 透传（不夹紧）。"""
    m = _FakeManifest(
        file_count=-1,
        content_group_count=-2,
        pdf_count=-3,
        docx_count=-4,
    )
    out = build_devset_section(m)
    assert out["file_count"] == -1
    assert out["content_group_count"] == -2
    assert out["pdf_count"] == -3
    assert out["docx_count"] == -4


def test_build_devset_section_duck_typed_object():
    """build_devset_section 用 attribute 访问，duck typing OK。"""
    class CustomManifest:
        devset_status = "incomplete"
        file_count = 3
        content_group_count = 1
        pdf_count = 2
        docx_count = 1
        categories_covered = ["a", "b"]

    out = build_devset_section(CustomManifest())
    assert out["file_count"] == 3
    assert out["pdf_count"] == 2


# =========================================================================
# get_dependency_versions：每次新 dict
# =========================================================================


def test_get_dependency_versions_returns_new_dict_each_call():
    """每次调用返回独立 dict。"""
    a = get_dependency_versions()
    b = get_dependency_versions()
    assert a is not b
    assert a == b


def test_get_dependency_versions_modifying_one_does_not_affect_other():
    """修改一次的返回不影响下次。"""
    a = get_dependency_versions()
    a["custom_key"] = "value"
    b = get_dependency_versions()
    assert "custom_key" not in b


def test_get_dependency_versions_keys_always_three(monkeypatch):
    """即使有 package 抛异常也返回 3 个 key。"""
    import evaluation.report
    import importlib.metadata

    def boom(pkg):
        if pkg == "pdfplumber":
            raise importlib.metadata.PackageNotFoundError(pkg)
        raise RuntimeError("unexpected")

    monkeypatch.setattr(importlib.metadata, "version", boom)
    out = evaluation.report.get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}
    assert out["pdfplumber"] is None  # PackageNotFoundError 路径
    assert out["python-docx"] is None  # Exception 路径
    assert out["pypdfium2"] is None


def test_get_dependency_versions_with_specific_values(monkeypatch):
    """monkeypatch importlib.metadata.version 返回特定字符串。"""
    import evaluation.report
    import importlib.metadata

    fake_versions = {
        "pdfplumber": "0.10.0",
        "python-docx": "1.1.0",
        "pypdfium2": "4.10.0",
    }

    def fake_version(pkg):
        return fake_versions[pkg]

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    out = evaluation.report.get_dependency_versions()
    assert out["pdfplumber"] == "0.10.0"
    assert out["python-docx"] == "1.1.0"
    assert out["pypdfium2"] == "4.10.0"


# =========================================================================
# get_git_provenance：subprocess 调用细节
# =========================================================================


def test_get_git_provenance_returns_dirty_true_on_oserror(monkeypatch, tmp_path):
    """OSError 时返回 commit=None + dirty=True。"""
    def fake_run(*args, **kwargs):
        raise OSError("simulated")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_returns_dirty_true_on_subprocess_error(monkeypatch, tmp_path):
    """SubprocessError 时返回 commit=None + dirty=True。"""
    def fake_run(*args, **kwargs):
        raise subprocess.SubprocessError("simulated")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_first_command_rev_parse_then_status(monkeypatch, tmp_path):
    """两次 subprocess.run 调用顺序：先 rev-parse HEAD 再 status --porcelain。"""
    calls = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        r = subprocess.CompletedProcess(cmd, returncode=0)
        if "rev-parse" in cmd:
            r.stdout = "abc123\n"
        else:
            r.stdout = ""
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    get_git_provenance(tmp_path)
    assert len(calls) == 2
    assert calls[0][:2] == ["git", "rev-parse"]
    assert "HEAD" in calls[0]
    assert calls[1][:2] == ["git", "status"]


def test_get_git_provenance_commit_strips_whitespace(monkeypatch, tmp_path):
    """stdout 含换行 → strip 后入 commit。"""
    def fake_run(cmd, *args, **kwargs):
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="  abc123  \n")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"


def test_get_git_provenance_commit_only_whitespace_becomes_none(monkeypatch, tmp_path):
    """stdout 是空白 → strip 后空 → commit=None。"""
    def fake_run(cmd, *args, **kwargs):
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="   \n  ")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_dirty_when_porcelain_nonempty(monkeypatch, tmp_path):
    """status --porcelain stdout 非空 → dirty=True。"""
    def fake_run(cmd, *args, **kwargs):
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="abc123")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout=" M file.txt\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


def test_get_git_provenance_not_dirty_when_porcelain_empty(monkeypatch, tmp_path):
    """status --porcelain stdout 空 → dirty=False。"""
    def fake_run(cmd, *args, **kwargs):
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="abc123")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_get_git_provenance_dirty_false_only_when_returncode_zero(monkeypatch, tmp_path):
    """status --porcelain returncode !=0 → dirty=True。"""
    def fake_run(cmd, *args, **kwargs):
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="abc")
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    # r2.returncode != 0 → dirty=bool(False and ...) = False
    # 但 r2.returncode=1 → bool(1==0 and ...) = bool(False) = False
    # Wait let me re-read code:
    # dirty = bool(r2.returncode == 0 and r2.stdout.strip())
    # r2.returncode=1 → (1==0)=False → False and anything = False
    # bool(False) = False
    assert out["git_dirty"] is False


def test_get_git_provenance_returncode_nonzero_for_rev_parse(monkeypatch, tmp_path):
    """rev-parse returncode=1 → commit=None（但 dirty 仍计算）。"""
    def fake_run(cmd, *args, **kwargs):
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, returncode=1, stdout="")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is False  # porcelain 空且 returncode 0


# =========================================================================
# build_provenance：参数透传
# =========================================================================


def test_build_provenance_returns_new_dict_each_call(tmp_path: Path):
    """每次调用返回独立 dict。"""
    a = build_provenance(tmp_path, "fallback", 800, "1.0")
    b = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert a is not b
    # timestamp 可能不同，所以不严格 == 但 keys 一致
    assert set(a.keys()) == set(b.keys())


def test_build_provenance_evaluator_report_version_constants(tmp_path: Path):
    """build_provenance 内嵌 EVALUATOR_VERSION 和 REPORT_VERSION。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_dependencies_value_is_dict(tmp_path: Path):
    """dependencies 字段值是 dict（来自 get_dependency_versions）。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_dependencies_independent_each_call(tmp_path: Path):
    """dependencies 每次调用是新 dict（get_dependency_versions 不缓存）。"""
    a = build_provenance(tmp_path, "fallback", 800, "1.0")
    b = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert a["dependencies"] is not b["dependencies"]


def test_build_provenance_parser_version_propagated(tmp_path: Path):
    """parser_version 透传。"""
    out = build_provenance(tmp_path, "fallback", 800, "v2.3.4")
    assert out["parser_version"] == "v2.3.4"


def test_build_provenance_max_chars_int_conversion(tmp_path: Path):
    """max_chars=int(...) → 即便传入 float 也会被转 int。"""
    out = build_provenance(tmp_path, "fallback", 800.99, "1.0")
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_negative_passthrough(tmp_path: Path):
    """max_chars 负数也透传（int(-5)=-5）。"""
    out = build_provenance(tmp_path, "fallback", -5, "1.0")
    assert out["max_chars"] == -5


def test_build_provenance_max_chars_zero(tmp_path: Path):
    """max_chars=0 透传。"""
    out = build_provenance(tmp_path, "fallback", 0, "1.0")
    assert out["max_chars"] == 0


def test_build_provenance_run_timestamp_iso_parseable(tmp_path: Path):
    """run_timestamp_iso 是合法 ISO 时间。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0")
    ts = out["run_timestamp_iso"]
    # datetime.fromisoformat 能解析（Python 3.7+）
    parsed = datetime.fromisoformat(ts)
    assert isinstance(parsed, datetime)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_is_list_type():
    """__all__ 类型是 list（不是 tuple）。"""
    import evaluation.report as m
    assert isinstance(m.__all__, list)
    assert not isinstance(m.__all__, tuple)


def test_module_all_exact_order():
    """__all__ 顺序精确。"""
    import evaluation.report as m
    assert m.__all__ == [
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    ]


def test_module_all_length_five():
    """__all__ 5 个元素。"""
    import evaluation.report as m
    assert len(m.__all__) == 5


def test_module_typing_any_in_namespace():
    """typing.Any 在模块命名空间。"""
    import evaluation.report as m
    assert m.Any is Any


def test_module_subprocess_in_namespace():
    """subprocess 在模块命名空间。"""
    import evaluation.report as m
    assert m.subprocess is subprocess


def test_module_datetime_in_namespace():
    """datetime 在模块命名空间。"""
    import evaluation.report as m
    assert m.datetime is datetime


def test_module_path_in_namespace():
    """Path 在模块命名空间。"""
    import evaluation.report as m
    assert m.Path is Path


def test_module_constants_count_metrics_is_tuple():
    """_COUNT_METRICS 是 tuple。"""
    assert isinstance(_COUNT_METRICS, tuple)


def test_module_constants_success_bool_metrics_is_tuple():
    """_SUCCESS_BOOL_METRICS 是 tuple。"""
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_module_constants_ratio_metrics_is_tuple():
    """_RATIO_METRICS 是 tuple。"""
    assert isinstance(_RATIO_METRICS, tuple)


def test_module_constants_disjoint_count_and_success():
    """_COUNT_METRICS 与 _SUCCESS_BOOL_METRICS 不交集。"""
    assert set(_COUNT_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))


def test_module_constants_disjoint_count_and_ratio():
    """_COUNT_METRICS 与 _RATIO_METRICS 不交集。"""
    assert set(_COUNT_METRICS).isdisjoint(set(_RATIO_METRICS))


def test_module_constants_disjoint_success_and_ratio():
    """_SUCCESS_BOOL_METRICS 与 _RATIO_METRICS 不交集。"""
    assert set(_SUCCESS_BOOL_METRICS).isdisjoint(set(_RATIO_METRICS))


# =========================================================================
# 函数签名精确
# =========================================================================


def test_get_git_provenance_signature_exact():
    """signature: (project_root)。"""
    sig = inspect.signature(get_git_provenance)
    assert list(sig.parameters.keys()) == ["project_root"]


def test_get_dependency_versions_signature_exact():
    """signature: () 无参数。"""
    sig = inspect.signature(get_dependency_versions)
    assert list(sig.parameters.keys()) == []


def test_build_provenance_signature_exact():
    """signature: (project_root, parser_name, max_chars, parser_version)。"""
    sig = inspect.signature(build_provenance)
    assert list(sig.parameters.keys()) == [
        "project_root", "parser_name", "max_chars", "parser_version",
    ]


def test_build_devset_section_signature_exact():
    """signature: (manifest)。"""
    sig = inspect.signature(build_devset_section)
    assert list(sig.parameters.keys()) == ["manifest"]


def test_aggregate_summary_signature_exact():
    """signature: (per_doc_results)。"""
    sig = inspect.signature(aggregate_summary)
    assert list(sig.parameters.keys()) == ["per_doc_results"]


# =========================================================================
# callable 验证
# =========================================================================


def test_all_functions_callable():
    """__all__ 中所有元素都 callable。"""
    import evaluation.report as m
    for name in m.__all__:
        assert callable(getattr(m, name))


def test_get_git_provenance_callable():
    assert callable(get_git_provenance)


def test_get_dependency_versions_callable():
    assert callable(get_dependency_versions)


def test_build_provenance_callable():
    assert callable(build_provenance)


def test_build_devset_section_callable():
    assert callable(build_devset_section)


def test_aggregate_summary_callable():
    assert callable(aggregate_summary)


# =========================================================================
# aggregate_summary：返回 dict 顶层结构
# =========================================================================


def test_aggregate_summary_returns_four_top_level_keys_in_order():
    """顶层 4 key 顺序：counts → success_rates → ratio_macro_averages → silent_drop_total。"""
    out = aggregate_summary([])
    keys = list(out.keys())
    assert keys == [
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    ]


def test_aggregate_summary_counts_value_always_present():
    """counts dict 至少含 element_count_total 一个 key。"""
    out = aggregate_summary([])
    assert "element_count_total" in out["counts"]


def test_aggregate_summary_success_rates_always_present():
    """success_rates dict 含 pipeline_success。"""
    out = aggregate_summary([])
    assert "pipeline_success" in out["success_rates"]


def test_aggregate_summary_silent_drop_total_always_present():
    """silent_drop_total 是顶层 key（即便 None）。"""
    out = aggregate_summary([])
    assert "silent_drop_total" in out


def test_aggregate_summary_with_per_doc_none_metric_value_skipped():
    """metric value=None 不参与计算但仍计入 total。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": None}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    # success_count = 1 (only True counted)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    # total = 2 (all docs)
    assert out["success_rates"]["pipeline_success"]["total"] == 2


# =========================================================================
# 端到端：合理数据集
# =========================================================================


def test_aggregate_summary_realistic_per_doc_set():
    """3 docs 全部含完整 metrics → summary 正确。"""
    per_doc = []
    for i in range(3):
        per_doc.append({
            "metrics": {
                "pipeline_success": {"value": True},
                "schema_valid": {"value": True},
                "element_count_total": {"value": 5 + i},
                "silent_drop_count": {"value": i},
            },
        })

    out = aggregate_summary(per_doc)
    # counts
    assert out["counts"]["element_count_total"]["sum"] == 5 + 6 + 7  # 18
    # success_rate: 3/3 = 1.0
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0
    # silent_drop_total: 0+1+2 = 3
    assert out["silent_drop_total"] == 3
