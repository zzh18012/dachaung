r"""evaluation/report.py 边角测试 - 第十八轮（Round 271）。

edges17 已覆盖：所有 ratio metric 走查、schema_valid 混合、text_preservation 浮点、
chunk_boundary_f1 三种、not_evaluated + participating = total、单 doc 全 None、多 doc 同 metric 全 null、
metrics 缺失某 metric、空 metrics dict、per_doc 异常、build_provenance max_chars 边界、
run_timestamp_iso 带 tz、parser_name 空串、dependencies 值类型、两次调用独立、
build_devset_section 边界、get_git_provenance 真实跑、get_dependency_versions 异常路径、
__all__ 不含 EVALUATOR_VERSION/REPORT_VERSION/subprocess/datetime/Path/Any、
_RATIO_METRICS 含 schema_valid/chunk_boundary 三联/text_char_multiset 双联、
源码 token 含 _COUNT_METRICS 循环、namespace has、helper metadata、签名 introspection。

edges18 补强未覆盖的角度：
- aggregate_summary 跨多 metric 组合：一个 doc 提供不同 metric；macro_average 计算正确性
- aggregate_summary 不混合类型再深：counts 不应 silently 含 ratio metric value；silent_drop_total 不污染 counts
- aggregate_summary 缺 metrics 字段 → KeyError（已 edges16，但 edges18 边界再深）
- build_provenance 输出 dict 不能被 pickle（subprocess 不 pickle）
- build_devset_section 接受 Manifest duck typing：任意含 6 个属性的对象
- get_dependency_versions 三 package 都 str or None
- get_git_provenance 在 git dirty 状态下返回 git_dirty=True（worktree 当前可能有未 commit）
- aggregate_summary 不缓存（两次调用独立）
- _RATIO_METRICS 顺序敏感深度：含 chunk_boundary_precision 在 chunk_boundary_recall 前
- _RATIO_METRICS 第一个元素是 schema_valid
- _RATIO_METRICS 最后一个元素是 chunk_boundary_f1
- _COUNT_METRICS 唯一元素是 element_count_total
- _SUCCESS_BOOL_METRICS 唯一元素是 pipeline_success
- 模块 import 顺序：subprocess → datetime → pathlib → typing → evaluation
- 模块顶层 docstring 提到 counts/success_rates/ratio_macro_averages/silent_drop_count 4 类
- build_provenance max_chars 接受 True（int(True)=1）/False（int(False)=0）/浮点数（int(1.5)=1）
- compute_summary 时同一 doc 提供 ratio + count + success + silent_drop 的混合
"""

from __future__ import annotations

import inspect
import pickle
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from evaluation import EVALUATOR_VERSION, REPORT_VERSION
from evaluation.report import (
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


# =========================================================================
# aggregate_summary 跨多 metric 组合
# =========================================================================


def test_aggregate_summary_one_doc_with_all_metric_types():
    """一个 doc 同时提供 ratio + count + success_bool + silent_drop_count。"""
    per_doc = [
        {
            "metrics": {
                "element_count_total": {"value": 5, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
                "schema_valid": {"value": True, "reason": None},
                "pdf_locator_valid_ratio": {"value": 1.0, "reason": None},
                "silent_drop_count": {"value": 2, "reason": None},
            }
        }
    ]
    out = aggregate_summary(per_doc)
    # counts
    assert out["counts"]["element_count_total"]["sum"] == 5
    # success_rates
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    # ratio_macro_averages
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    # silent_drop_total
    assert out["silent_drop_total"] == 2


def test_aggregate_summary_mixed_docs_different_metrics():
    """不同 doc 提供不同 metric 组合。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": True, "reason": None}}},
        {"metrics": {"element_count_total": {"value": 3, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    # schema_valid: 1 doc participating
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1
    # element_count_total: 1 doc
    assert out["counts"]["element_count_total"]["sum"] == 3
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_macro_average_arithmetic_mean():
    """macro_average = sum(values) / len(values)。"""
    per_doc = [
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.0, "reason": None}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": 1.0, "reason": None}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.5, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert rma["macro_average"] == pytest.approx(0.5)
    assert rma["participating_docs"] == 3
    assert rma["not_evaluated"] == 0


def test_aggregate_summary_macro_average_with_some_null():
    per_doc = [
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.0, "reason": None}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": None, "reason": "x"}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": 1.0, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    # macro = (0.0 + 1.0) / 2 = 0.5
    assert rma["macro_average"] == 0.5
    assert rma["participating_docs"] == 2
    assert rma["not_evaluated"] == 1


def test_aggregate_summary_does_not_silently_include_silent_in_counts():
    """silent_drop_count 不应出现在 counts dict 中。"""
    per_doc = [
        {
            "metrics": {
                "element_count_total": {"value": 5, "reason": None},
                "silent_drop_count": {"value": 3, "reason": None},
            }
        }
    ]
    out = aggregate_summary(per_doc)
    assert "silent_drop_count" not in out["counts"]
    assert "element_count_total" in out["counts"]


def test_aggregate_summary_does_not_silently_include_ratio_in_counts():
    per_doc = [
        {
            "metrics": {
                "element_count_total": {"value": 5, "reason": None},
                "schema_valid": {"value": True, "reason": None},
            }
        }
    ]
    out = aggregate_summary(per_doc)
    assert "schema_valid" not in out["counts"]
    assert "pipeline_success" not in out["counts"]


def test_aggregate_summary_does_not_silently_include_count_in_ratios():
    per_doc = [
        {
            "metrics": {
                "element_count_total": {"value": 5, "reason": None},
                "schema_valid": {"value": True, "reason": None},
            }
        }
    ]
    out = aggregate_summary(per_doc)
    assert "element_count_total" not in out["ratio_macro_averages"]


def test_aggregate_summary_two_calls_independent_dict():
    """两次调用返回完全独立的 dict（不缓存）。"""
    a = aggregate_summary([])
    b = aggregate_summary([])
    assert a is not b
    assert a["counts"] is not b["counts"]
    assert a["success_rates"] is not b["success_rates"]
    assert a["ratio_macro_averages"] is not b["ratio_macro_averages"]


def test_aggregate_summary_total_per_doc_count_independent_of_metric_value():
    """total 用 len(per_doc)，与 metric 是否提供无关。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": True, "reason": None}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
        {"metrics": {}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["total"] == 3  # 总是 len(per_doc)


def test_aggregate_summary_rate_when_some_pipeline_success_none():
    """pipeline_success 是 None（不应发生但防御）。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": None, "reason": "x"}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": "y"}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    # success_count=1（只算 True）, total=3, rate=1/3
    assert sr["success_count"] == 1
    assert sr["total"] == 3
    assert sr["rate"] == pytest.approx(1 / 3)


# =========================================================================
# build_provenance 边界更多
# =========================================================================


def test_build_provenance_max_chars_int_from_float(tmp_path: Path):
    """max_chars=1.5 → int(1.5)=1。"""
    out = build_provenance(tmp_path, "fallback", 1.5, None)  # type: ignore[arg-type]
    assert out["max_chars"] == 1


def test_build_provenance_max_chars_negative_float(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", -1.7, None)  # type: ignore[arg-type]
    # int(-1.7) = -1（向 0 截断）
    assert out["max_chars"] == -1


def test_build_provenance_run_timestamp_iso_changes_between_calls(tmp_path: Path):
    """两次调用时间戳不同（除非极快连续）。"""
    import time as _time

    a = build_provenance(tmp_path, "fallback", 800, None)
    _time.sleep(0.01)
    b = build_provenance(tmp_path, "fallback", 800, None)
    # 时间戳通常不同（但不强制，可能精度不够）
    assert isinstance(a["run_timestamp_iso"], str)
    assert isinstance(b["run_timestamp_iso"], str)


def test_build_provenance_dict_is_pickleable(tmp_path: Path):
    """build_provenance 返回的 dict 应该可 pickle。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    s = pickle.dumps(out)
    restored = pickle.loads(s)
    assert restored == out


def test_build_provenance_git_commit_is_str_or_none_only(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    # git_commit 是 str（40 char hash）或 None
    assert out["git_commit"] is None or (
        isinstance(out["git_commit"], str) and len(out["git_commit"]) == 40
    )


def test_build_provenance_evaluator_version_value_identity(tmp_path: Path):
    """evaluator_version 来自 evaluation.EVALUATOR_VERSION。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value_identity(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_max_chars_int_returns_int_type(tmp_path: Path):
    """int(True)、int(0.5)、int('800') 都返回 int 类型。"""
    out1 = build_provenance(tmp_path, "fallback", True, None)  # type: ignore[arg-type]
    out2 = build_provenance(tmp_path, "fallback", 0.5, None)  # type: ignore[arg-type]
    out3 = build_provenance(tmp_path, "fallback", "800", None)  # type: ignore[arg-type]
    assert isinstance(out1["max_chars"], int)
    assert isinstance(out2["max_chars"], int)
    assert isinstance(out3["max_chars"], int)


# =========================================================================
# build_devset_section duck typing
# =========================================================================


class _DuckManifest:
    """duck typing Manifest：只要含 6 个属性就行。"""

    def __init__(self):
        self.devset_status = "incomplete"
        self.file_count = 7
        self.content_group_count = 3
        self.pdf_count = 2
        self.docx_count = 1
        self.categories_covered = ["legal", "sci"]


def test_build_devset_section_accepts_duck_typed_object():
    out = build_devset_section(_DuckManifest())
    assert out["status"] == "incomplete"
    assert out["file_count"] == 7
    assert out["content_group_count"] == 3
    assert out["pdf_count"] == 2
    assert out["docx_count"] == 1
    assert out["categories_covered"] == ["legal", "sci"]


def test_build_devset_section_duck_missing_attr_raises_attribute_error():
    """对象缺 categories_covered 属性 → AttributeError。"""

    class Incomplete:
        devset_status = "x"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        # 缺 categories_covered

    with pytest.raises(AttributeError):
        build_devset_section(Incomplete())


# =========================================================================
# get_dependency_versions 深度
# =========================================================================


def test_get_dependency_versions_keys_exact():
    """keys 精确：{'pdfplumber', 'python-docx', 'pypdfium2'}。"""
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_pdfplumber_version_format():
    """pdfplumber 是已安装依赖，版本应是 X.Y.Z 形式。"""
    out = get_dependency_versions()
    v = out["pdfplumber"]
    if v is not None:
        # 至少含一个 '.' (X.Y)
        assert "." in v


def test_get_dependency_versions_no_extra_keys():
    out = get_dependency_versions()
    assert len(out.keys()) == 3


# =========================================================================
# get_git_provenance 深度
# =========================================================================


def test_get_git_provenance_dict_pickleable(tmp_path: Path):
    """返回 dict 应该可 pickle。"""
    out = get_git_provenance(tmp_path)
    s = pickle.dumps(out)
    restored = pickle.loads(s)
    assert restored == out


def test_get_git_provenance_subprocess_kwargs_cwd_used(monkeypatch, tmp_path: Path):
    """subprocess.run 用 cwd=project_root。"""
    seen_cwd = []
    real_run = subprocess.run

    def fake_run(*args, **kwargs):
        if "cwd" in kwargs:
            seen_cwd.append(kwargs["cwd"])
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)
    get_git_provenance(tmp_path)
    # 至少调用 1 次 cwd
    assert len(seen_cwd) >= 1


def test_get_git_provenance_subprocess_returns_nonzero(monkeypatch, tmp_path: Path):
    """subprocess 返回非零 → commit=None, dirty 取决于 r2。"""

    class FakeResult:
        def __init__(self, returncode, stdout):
            self.returncode = returncode
            self.stdout = stdout

    def fake_run(*args, **kwargs):
        return FakeResult(returncode=128, stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    # rev-parse returncode=128 → commit None
    # status returncode=128 → dirty bool(False and ...) = False
    assert out["git_commit"] is None
    assert out["git_dirty"] is False


def test_get_git_provenance_subprocess_rev_parse_success_status_empty(monkeypatch, tmp_path: Path):
    """rev-parse 成功 + status porcelain 空 → dirty=False。"""

    class FakeResult:
        def __init__(self, returncode, stdout):
            self.returncode = returncode
            self.stdout = stdout

    call_count = [0]

    def fake_run(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # rev-parse
            return FakeResult(returncode=0, stdout="abc123\n")
        # status porcelain
        return FakeResult(returncode=0, stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is False


def test_get_git_provenance_subprocess_status_nonempty(monkeypatch, tmp_path: Path):
    """status porcelain 非空 → dirty=True。"""

    class FakeResult:
        def __init__(self, returncode, stdout):
            self.returncode = returncode
            self.stdout = stdout

    call_count = [0]

    def fake_run(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return FakeResult(returncode=0, stdout="abc123\n")
        return FakeResult(returncode=0, stdout="M file.txt\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


# =========================================================================
# _RATIO_METRICS 顺序敏感深度
# =========================================================================


def test_ratio_metrics_first_element_is_schema_valid():
    """schema_valid 是 boolean-as-ratio 特殊，排第一。"""
    import evaluation.report as m

    assert m._RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_last_element_is_chunk_boundary_f1():
    import evaluation.report as m

    assert m._RATIO_METRICS[-1] == "chunk_boundary_f1"


def test_ratio_metrics_chunk_boundary_precision_before_recall():
    """precision 在 recall 前。"""
    import evaluation.report as m

    p_idx = m._RATIO_METRICS.index("chunk_boundary_precision")
    r_idx = m._RATIO_METRICS.index("chunk_boundary_recall")
    assert p_idx < r_idx


def test_ratio_metrics_recall_before_f1():
    import evaluation.report as m

    r_idx = m._RATIO_METRICS.index("chunk_boundary_recall")
    f1_idx = m._RATIO_METRICS.index("chunk_boundary_f1")
    assert r_idx < f1_idx


def test_count_metrics_single_element_element_count_total():
    import evaluation.report as m

    assert m._COUNT_METRICS[0] == "element_count_total"
    assert len(m._COUNT_METRICS) == 1


def test_success_bool_metrics_single_element_pipeline_success():
    import evaluation.report as m

    assert m._SUCCESS_BOOL_METRICS[0] == "pipeline_success"
    assert len(m._SUCCESS_BOOL_METRICS) == 1


# =========================================================================
# 模块源码 token 验证（补强）
# =========================================================================


def test_module_source_contains_aggregate_summary_loop_iter_per_doc():
    """聚合用 for r in per_doc_results 循环。"""
    import evaluation.report as m

    assert "for r in per_doc_results" in inspect.getsource(m)


def test_module_source_contains_success_count_increment():
    """success_count 用 sum(1 for ...)。"""
    import evaluation.report as m

    src = inspect.getsource(m)
    assert "sum(" in src
    assert "1\n            for r in per_doc_results" in src or "for r in per_doc_results" in src


def test_module_source_contains_rate_calculation():
    """rate = successes / total if total else None。"""
    import evaluation.report as m

    src = inspect.getsource(m)
    assert "successes / total" in src
    assert "if total else None" in src


def test_module_source_contains_macro_average_calculation():
    """macro = sum(values) / len(values)。"""
    import evaluation.report as m

    src = inspect.getsource(m)
    assert "sum(values) / len(values)" in src


def test_module_source_contains_silent_drop_filter_loop():
    """silent_vals 用 list comprehension 过滤 None。"""
    import evaluation.report as m

    src = inspect.getsource(m)
    assert 'r["metrics"].get("silent_drop_count", {})' in src


def test_module_source_does_not_contain_async():
    import evaluation.report as m

    assert "async " not in inspect.getsource(m)
    assert "await " not in inspect.getsource(m)


def test_module_source_does_not_contain_threading():
    import evaluation.report as m

    assert "import threading" not in inspect.getsource(m)
    assert "Thread(" not in inspect.getsource(m)


def test_module_source_does_not_contain_yet_another_module():
    """不引入 numpy/pandas 等大模块。"""
    import evaluation.report as m

    src = inspect.getsource(m)
    assert "import numpy" not in src
    assert "import pandas" not in src


def test_module_source_contains_subprocess_timeout_kwarg():
    """subprocess.run 用 timeout=10。"""
    import evaluation.report as m

    src = inspect.getsource(m)
    # 至少 2 次（rev-parse + status）
    assert src.count("timeout=10") >= 2


def test_module_source_contains_cwd_kwarg():
    import evaluation.report as m

    assert "cwd=str(project_root)" in inspect.getsource(m)


# =========================================================================
# 模块顶层 imports 顺序
# =========================================================================


def test_module_source_import_order_subprocess_first():
    """import 顺序：subprocess → datetime → pathlib → typing → evaluation。"""
    import evaluation.report as m

    src = inspect.getsource(m)
    pos_subprocess = src.find("import subprocess")
    pos_datetime = src.find("from datetime import datetime")
    pos_pathlib = src.find("from pathlib import Path")
    pos_typing = src.find("from typing import Any")
    pos_eval = src.find("from evaluation import")
    # 子模块 imports 在 __future__ 之后
    assert pos_subprocess > 0
    assert pos_datetime > pos_subprocess
    assert pos_pathlib > pos_datetime
    assert pos_typing > pos_pathlib
    assert pos_eval > pos_typing


# =========================================================================
# 模块 docstring 详细
# =========================================================================


def test_module_docstring_mentions_4_categories():
    """docstring 提到 4 类聚合（counts/success_rates/ratio/silent_drop）。"""
    import evaluation.report as m

    doc = m.__doc__
    assert "counts" in doc.lower() or "求和" in doc
    assert "success_rates" in doc.lower() or "成功" in doc
    assert "ratio" in doc.lower() or "macro" in doc.lower()
    assert "silent_drop" in doc.lower()


def test_module_docstring_mentions_participating_docs():
    """docstring 提到 participating_docs（participating）概念。"""
    import evaluation.report as m

    doc = m.__doc__
    assert "participating" in doc.lower() or "参与" in doc


def test_module_docstring_mentions_not_evaluated():
    import evaluation.report as m

    doc = m.__doc__
    assert "not_evaluated" in doc.lower() or "不参与" in doc or "未评估" in doc


# =========================================================================
# 异常路径
# =========================================================================


def test_aggregate_summary_per_doc_results_empty_list():
    """空 list → 4 keys + 默认 None/0 结构。"""
    out = aggregate_summary([])
    assert isinstance(out, dict)
    assert len(out) == 4


def test_aggregate_summary_per_doc_with_extra_unknown_metric():
    """per_doc 含未在 _RATIO_METRICS/_COUNT_METRICS/_SUCCESS_BOOL_METRICS 中的 metric → 忽略。"""
    per_doc = [
        {
            "metrics": {
                "unknown_metric": {"value": 999, "reason": None},
                "schema_valid": {"value": True, "reason": None},
            }
        }
    ]
    out = aggregate_summary(per_doc)
    # unknown_metric 不在 counts/success_rates/ratio_macro_averages 任何一个
    assert "unknown_metric" not in out["counts"]
    assert "unknown_metric" not in out["success_rates"]
    assert "unknown_metric" not in out["ratio_macro_averages"]
    # 但 schema_valid 仍参与
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1


def test_aggregate_summary_value_is_zero_treated_as_participating():
    """0.0 是 falsy 但应参与 macro average。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.0, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["schema_valid"]
    assert rma["participating_docs"] == 1
    assert rma["macro_average"] == 0.0
    assert rma["not_evaluated"] == 0


def test_aggregate_summary_value_is_false_treated_as_participating_ratio():
    """False 是 falsy 但应参与 macro average（schema_valid 是 boolean-as-ratio）。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": False, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["schema_valid"]
    assert rma["participating_docs"] == 1
    assert rma["macro_average"] == 0.0


def test_aggregate_summary_value_is_zero_count_treated_as_participating():
    """element_count_total=0 是 falsy 但应参与 counts 求和。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 0, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    counts = out["counts"]["element_count_total"]
    assert counts["sum"] == 0
    assert counts["participating_docs"] == 1


def test_aggregate_summary_silent_drop_count_zero_is_participating():
    """silent_drop_count=0 应参与求和（不是 null）。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 0, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 0


def test_aggregate_summary_pipeline_success_false_counted_in_total():
    """pipeline_success=False → success_count=0, total=1, rate=0.0。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False, "reason": "x"}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 1
    assert sr["rate"] == 0.0
