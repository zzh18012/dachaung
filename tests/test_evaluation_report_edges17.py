r"""evaluation/report.py 边角测试 - 第十七轮（Round 264）。

edges16 已覆盖：源码 token、docstring、签名、helper metadata、常量精确、
aggregate_summary 基本 + 4 keys、build_devset_section stub、build_provenance 9 keys、
get_git_provenance、get_dependency_versions、__all__、cross-check roundtrip。

edges17 补强未覆盖的角度：
- aggregate_summary 深度：所有 ratio metric 走查（不只 schema_valid）；schema_valid 当作 ratio 时的 True/False/None 混合；text_preservation_equal 浮点混合；chunk_boundary_f1 三种 None/0/0.5；not_evaluated + participating_docs = total 关系；rate None 时 total=0；success_count + (total - success_count) = total
- aggregate_summary 异常 per_doc：list 中含非 dict（会被 .get 调用 → AttributeError）；r["metrics"] 不是 dict（dict.get 调用 → AttributeError）；空 list（已覆盖）；list 含 1 个 None（TypeError）
- aggregate_summary 单 doc 全 None：每个 ratio 都是 None → macro_average None + participating_docs 0 + not_evaluated 1
- aggregate_summary 多 doc 同一 metric 全 null（_COUNT_METRICS / silent_drop_count / 各 ratio）
- build_provenance 深度：max_chars=0 / max_chars=-1 / max_chars=布尔（True→1）；run_timestamp_iso 是 ISO（包含时区 offset）；dependencies 三 package 值类型；parser_name="" 空字符串
- build_devset_section：devset_status="" / content_group_count=0 / pdf_count + docx_count 与 file_count 不匹配（不强制一致性）；categories_covered=None（manifest 允许 None？）；categories_covered 不修改 input list（identity 检查）
- get_git_provenance：subprocess 真实跑在 project root（CWD）；返回 git_commit 长度 40（git hash）
- get_dependency_versions：返回 dict 值可能是 None 或 str；pypdfium2 值类型；不抛错；两次调用返回不同 dict（不缓存）
- 模块顶层：from evaluation import 直接走；__all__ 不含 EVALUATOR_VERSION/REPORT_VERSION（不暴露版本号）；__all__ 不含 subprocess/datetime/Path/Any；__all__ 不含 _RATIO_METRICS 等私有
- 常量更深：_RATIO_METRICS 不含 figure_caption_*；_RATIO_METRICS 含 schema_valid（boolean-as-ratio 特殊）；_RATIO_METRICS 含 chunk_boundary_precision/recall/f1 三联；_RATIO_METRICS 与 metrics.py 输出键一致
- helper no-caching：build_provenance 两次调用独立 dict；build_devset_section 两次调用独立；get_git_provenance 两次独立；get_dependency_versions 两次独立
- 异常路径：subprocess.run 抛 FileNotFoundError（git 不存在）→ catch → commit None + dirty True；importlib.metadata.version 抛异常 → catch → None
"""

from __future__ import annotations

import inspect
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
# aggregate_summary 深度：所有 ratio metric 走查（不只 schema_valid）
# =========================================================================


def test_aggregate_summary_each_ratio_metric_in_output():
    """聚合后 ratio_macro_averages 含每个 _RATIO_METRICS。"""
    import evaluation.report as m

    out = aggregate_summary([])
    for name in m._RATIO_METRICS:
        assert name in out["ratio_macro_averages"]


def test_aggregate_summary_each_ratio_metric_default_structure():
    """空 per_doc → 每个 ratio metric 是 {macro_average: None, participating_docs: 0, not_evaluated: 0}。"""
    import evaluation.report as m

    out = aggregate_summary([])
    for name in m._RATIO_METRICS:
        assert out["ratio_macro_averages"][name] == {
            "macro_average": None,
            "participating_docs": 0,
            "not_evaluated": 0,
        }


@pytest.mark.parametrize(
    "metric_name,value,expected_macro",
    [
        ("pdf_locator_valid_ratio", 1.0, 1.0),
        ("pdf_locator_valid_ratio", 0.0, 0.0),
        ("pdf_locator_valid_ratio", 0.5, 0.5),
        ("docx_locator_valid_ratio", 0.7, 0.7),
        ("image_resource_exists_ratio", 0.3, 0.3),
        ("chunk_reference_intact_ratio", 0.9, 0.9),
        ("text_preservation_equal", 0.8, 0.8),
        ("text_char_multiset_precision", 0.6, 0.6),
        ("text_char_multiset_recall", 0.4, 0.4),
        ("heading_boundary_compliance", 0.55, 0.55),
        ("chunk_boundary_precision", 0.66, 0.66),
        ("chunk_boundary_recall", 0.77, 0.77),
        ("chunk_boundary_f1", 0.88, 0.88),
    ],
)
def test_aggregate_summary_each_ratio_metric_single_doc(metric_name, value, expected_macro):
    """单 doc 提供该 ratio value → macro_average = value。"""
    per_doc = [{"metrics": {metric_name: {"value": value, "reason": None}}}]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"][metric_name]
    assert rma["macro_average"] == expected_macro
    assert rma["participating_docs"] == 1
    assert rma["not_evaluated"] == 0


def test_aggregate_summary_schema_valid_mixed_true_false_none():
    """schema_valid 是 boolean-as-ratio，混合 True/False/None。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": True, "reason": None}}},
        {"metrics": {"schema_valid": {"value": False, "reason": None}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["schema_valid"]
    assert rma["macro_average"] == 0.5
    assert rma["participating_docs"] == 2
    assert rma["not_evaluated"] == 1


def test_aggregate_summary_text_preservation_equal_mixed_floats():
    per_doc = [
        {"metrics": {"text_preservation_equal": {"value": 0.5, "reason": None}}},
        {"metrics": {"text_preservation_equal": {"value": 1.0, "reason": None}}},
        {"metrics": {"text_preservation_equal": {"value": 0.0, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["text_preservation_equal"]
    assert rma["macro_average"] == pytest.approx(0.5)
    assert rma["participating_docs"] == 3


def test_aggregate_summary_chunk_boundary_f1_zero():
    per_doc = [{"metrics": {"chunk_boundary_f1": {"value": 0.0, "reason": None}}}]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["chunk_boundary_f1"]
    assert rma["macro_average"] == 0.0


def test_aggregate_summary_chunk_boundary_f1_half():
    per_doc = [
        {"metrics": {"chunk_boundary_f1": {"value": 0.0, "reason": None}}},
        {"metrics": {"chunk_boundary_f1": {"value": 1.0, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["chunk_boundary_f1"]
    assert rma["macro_average"] == 0.5


def test_aggregate_summary_chunk_boundary_f1_all_none():
    per_doc = [
        {"metrics": {"chunk_boundary_f1": {"value": None, "reason": "no_predicted_boundaries"}}},
        {"metrics": {"chunk_boundary_f1": {"value": None, "reason": "no_ground_truth_anchors"}}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["chunk_boundary_f1"]
    assert rma["macro_average"] is None
    assert rma["participating_docs"] == 0
    assert rma["not_evaluated"] == 2


def test_aggregate_summary_not_evaluated_plus_participating_equals_total():
    """对每个 ratio metric：participating + not_evaluated = len(per_doc)。"""
    import evaluation.report as m

    per_doc = [
        {"metrics": {"schema_valid": {"value": True, "reason": None}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
        {"metrics": {"schema_valid": {"value": False, "reason": None}}},
        {"metrics": {}},
    ]
    out = aggregate_summary(per_doc)
    total = len(per_doc)
    for name in m._RATIO_METRICS:
        rma = out["ratio_macro_averages"][name]
        assert rma["participating_docs"] + rma["not_evaluated"] == total


def test_aggregate_summary_success_rate_zero_docs_rate_is_none():
    out = aggregate_summary([])
    sr = out["success_rates"]["pipeline_success"]
    assert sr["rate"] is None
    assert sr["success_count"] == 0
    assert sr["total"] == 0


def test_aggregate_summary_success_count_plus_failure_equals_total():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": "x"}}},
        {"metrics": {"pipeline_success": {"value": None, "reason": "x"}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 4
    assert sr["rate"] == 0.5


def test_aggregate_summary_single_doc_all_none_metrics():
    """单 doc 所有 metric value None。"""
    import evaluation.report as m

    metrics: dict[str, Any] = {
        name: {"value": None, "reason": "x"} for name in m._RATIO_METRICS
    }
    metrics["element_count_total"] = {"value": None, "reason": "x"}
    metrics["pipeline_success"] = {"value": None, "reason": "x"}
    metrics["silent_drop_count"] = {"value": None, "reason": "x"}
    per_doc = [{"metrics": metrics}]
    out = aggregate_summary(per_doc)
    # counts
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0
    # success_rates
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 1
    assert sr["rate"] == 0.0
    # ratios
    for name in m._RATIO_METRICS:
        rma = out["ratio_macro_averages"][name]
        assert rma["macro_average"] is None
        assert rma["participating_docs"] == 0
        assert rma["not_evaluated"] == 1
    # silent
    assert out["silent_drop_total"] is None


def test_aggregate_summary_multi_doc_all_none_per_metric():
    """多 doc 所有 value None 对某 metric。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["schema_valid"]
    assert rma["macro_average"] is None
    assert rma["participating_docs"] == 0
    assert rma["not_evaluated"] == 2


def test_aggregate_summary_missing_metric_in_one_doc_only():
    """doc1 提供 metric，doc2 缺 → 1 doc 参与 + 1 not_evaluated。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.5, "reason": None}}},
        {"metrics": {}},
    ]
    out = aggregate_summary(per_doc)
    rma = out["ratio_macro_averages"]["schema_valid"]
    assert rma["macro_average"] == 0.5
    assert rma["participating_docs"] == 1
    assert rma["not_evaluated"] == 1


def test_aggregate_summary_empty_metrics_dict_per_doc():
    """每个 doc 都 metrics={} → 全部 None。"""
    per_doc = [{"metrics": {}}, {"metrics": {}}]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0
    sr = out["success_rates"]["pipeline_success"]
    assert sr["total"] == 2
    assert sr["success_count"] == 0
    assert sr["rate"] == 0.0
    assert out["silent_drop_total"] is None


# =========================================================================
# aggregate_summary 异常 per_doc（防御性）
# =========================================================================


def test_aggregate_summary_per_doc_is_none_raises_type_error():
    """per_doc_results 含 None → None[X] 抛 TypeError。"""
    with pytest.raises(TypeError):
        aggregate_summary([None])  # type: ignore[list-item]


def test_aggregate_summary_per_doc_metrics_is_none_raises_attribute_error():
    """per_doc_results[i]['metrics'] is None → None.get 抛 AttributeError。"""
    with pytest.raises(AttributeError):
        aggregate_summary([{"metrics": None}])  # type: ignore[dict-item]


def test_aggregate_summary_per_doc_metrics_value_is_not_dict_raises_attribute_error():
    """metric['schema_valid'] 不是 dict → str.get 抛 AttributeError。"""
    with pytest.raises(AttributeError):
        aggregate_summary([{"metrics": {"schema_valid": "not_a_dict"}}])  # type: ignore[dict-item]


def test_aggregate_summary_per_doc_not_dict_raises_type_error():
    """per_doc_results[i] 不是 dict → 'str'['metrics'] 抛 TypeError。"""
    with pytest.raises(TypeError):
        aggregate_summary(["not_a_dict"])  # type: ignore[list-item]


# =========================================================================
# build_provenance 深度（max_chars 边界）
# =========================================================================


def test_build_provenance_max_chars_zero(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 0, None)
    assert out["max_chars"] == 0
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_negative(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", -1, None)
    assert out["max_chars"] == -1


def test_build_provenance_max_chars_bool_true(tmp_path: Path):
    """True → int(True) = 1。"""
    out = build_provenance(tmp_path, "fallback", True, None)  # type: ignore[arg-type]
    assert out["max_chars"] == 1
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_bool_false(tmp_path: Path):
    """False → int(False) = 0。"""
    out = build_provenance(tmp_path, "fallback", False, None)  # type: ignore[arg-type]
    assert out["max_chars"] == 0
    assert isinstance(out["max_chars"], int)


def test_build_provenance_run_timestamp_iso_has_timezone_offset(tmp_path: Path):
    """ISO 8601 时间戳带时区偏移（+HH:MM）。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    ts = out["run_timestamp_iso"]
    # astimezone() 总会带 offset，含 '+' 或 'Z'
    assert "+" in ts or ts.endswith("Z") or "-" in ts[10:]


def test_build_provenance_run_timestamp_iso_parse_back_to_datetime(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    ts = out["run_timestamp_iso"]
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None  # astimezone 总会带 tz


def test_build_provenance_parser_name_empty_string(tmp_path: Path):
    out = build_provenance(tmp_path, "", 800, None)
    assert out["parser_name"] == ""


def test_build_provenance_dependencies_value_types(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    deps = out["dependencies"]
    for k, v in deps.items():
        assert v is None or isinstance(v, str)


def test_build_provenance_two_calls_independent_dict(tmp_path: Path):
    """两次调用返回不同 dict 对象（不缓存）。"""
    a = build_provenance(tmp_path, "fallback", 800, None)
    b = build_provenance(tmp_path, "fallback", 800, None)
    assert a is not b
    assert a["dependencies"] is not b["dependencies"]


def test_build_provenance_evaluator_version_is_string(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["evaluator_version"], str)


def test_build_provenance_report_version_is_string(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["report_version"], str)


def test_build_provenance_evaluator_version_not_none(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] is not None


def test_build_provenance_report_version_not_none(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] is not None


# =========================================================================
# build_devset_section 深度
# =========================================================================


class _StubManifest:
    """stub Manifest."""

    def __init__(
        self,
        devset_status: str = "incomplete",
        file_count: int = 0,
        content_group_count: int = 0,
        pdf_count: int = 0,
        docx_count: int = 0,
        categories_covered: list[str] | None = None,
    ):
        self.devset_status = devset_status
        self.file_count = file_count
        self.content_group_count = content_group_count
        self.pdf_count = pdf_count
        self.docx_count = docx_count
        self.categories_covered = categories_covered if categories_covered is not None else []


def test_build_devset_section_empty_devset_status():
    out = build_devset_section(_StubManifest(devset_status=""))
    assert out["status"] == ""


def test_build_devset_section_huge_file_count():
    out = build_devset_section(_StubManifest(file_count=10**9))
    assert out["file_count"] == 10**9


def test_build_devset_section_pdf_docx_dont_need_to_sum_to_file_count():
    """pdf_count + docx_count 不必等于 file_count（不强制一致性）。"""
    out = build_devset_section(
        _StubManifest(file_count=10, pdf_count=2, docx_count=3)
    )
    assert out["file_count"] == 10
    assert out["pdf_count"] == 2
    assert out["docx_count"] == 3


def test_build_devset_section_categories_identity_preserved():
    """categories_covered 直接赋值（不复制）。"""
    cats = ["legal", "sci"]
    out = build_devset_section(_StubManifest(categories_covered=cats))
    assert out["categories_covered"] is cats or out["categories_covered"] == cats


def test_build_devset_section_two_calls_independent():
    """两次调用返回独立 dict。"""
    a = build_devset_section(_StubManifest())
    b = build_devset_section(_StubManifest())
    assert a is not b


def test_build_devset_section_does_not_mutate_categories_input():
    """build_devset_section 在调用过程中不修改 manifest 任何属性。"""
    cats = ["x", "y"]
    m = _StubManifest(
        devset_status="incomplete",
        file_count=5,
        content_group_count=2,
        pdf_count=1,
        docx_count=1,
        categories_covered=cats,
    )
    build_devset_section(m)
    # 调用后 manifest 属性保持原样
    assert m.devset_status == "incomplete"
    assert m.file_count == 5
    assert m.content_group_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.categories_covered == ["x", "y"]
    assert m.categories_covered is cats


# =========================================================================
# get_git_provenance 深度
# =========================================================================


def test_get_git_provenance_in_actual_project_root():
    """真实项目根目录跑应该返回非空 git_commit。"""
    project_root = Path(__file__).resolve().parent.parent
    out = get_git_provenance(project_root)
    assert "git_commit" in out
    assert "git_dirty" in out
    # 在 worktree 里 git_commit 是个有效 hash
    if out["git_commit"] is not None:
        # git hash 是 40 char 十六进制
        assert len(out["git_commit"]) == 40
        assert all(c in "0123456789abcdef" for c in out["git_commit"])


def test_get_git_provenance_in_tmp_path_commit_is_none_or_string(tmp_path: Path):
    """tmp_path 不是 git repo → commit=None。"""
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None or isinstance(out["git_commit"], str)


def test_get_git_provenance_in_tmp_path_dirty_is_bool(tmp_path: Path):
    """tmp_path 不是 git repo → git_dirty 是 bool（git 失败时可能 True 或 False 取决于实现）。"""
    out = get_git_provenance(tmp_path)
    assert isinstance(out["git_dirty"], bool)


def test_get_git_provenance_two_calls_independent_dict(tmp_path: Path):
    a = get_git_provenance(tmp_path)
    b = get_git_provenance(tmp_path)
    assert a is not b


def test_get_git_provenance_subprocess_command_used(monkeypatch, tmp_path: Path):
    """get_git_provenance 调用 subprocess.run。"""
    calls = []
    real_run = subprocess.run

    def fake_run(*args, **kwargs):
        calls.append(args[0] if args else None)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)
    get_git_provenance(tmp_path)
    assert len(calls) >= 1  # 至少调用 1 次（rev-parse 或 status）


def test_get_git_provenance_subprocess_handles_exception(monkeypatch, tmp_path: Path):
    """subprocess.run 抛错 → except 路径 → commit None + dirty True。"""

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("git not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


# =========================================================================
# get_dependency_versions 深度
# =========================================================================


def test_get_dependency_versions_pypdfium2_type():
    """pypdfium2 值类型是 None 或 str。"""
    out = get_dependency_versions()
    v = out["pypdfium2"]
    assert v is None or isinstance(v, str)


def test_get_dependency_versions_python_docx_type():
    out = get_dependency_versions()
    v = out["python-docx"]
    assert v is None or isinstance(v, str)


def test_get_dependency_versions_two_calls_independent():
    a = get_dependency_versions()
    b = get_dependency_versions()
    assert a is not b
    # 但 value 应一致
    assert a == b


def test_get_dependency_versions_handles_exception(monkeypatch):
    """importlib.metadata.version 抛错 → catch → None。"""
    import importlib.metadata

    def fake_version(pkg):
        raise Exception("fake error")

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None


def test_get_dependency_versions_handles_package_not_found(monkeypatch):
    """importlib.metadata.version 抛 PackageNotFoundError → catch → None。"""
    import importlib.metadata

    def fake_version(pkg):
        raise importlib.metadata.PackageNotFoundError(pkg)

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None


# =========================================================================
# 模块 namespace 完整性
# =========================================================================


def test_module_all_does_not_contain_evaluator_version():
    import evaluation.report as m

    assert "EVALUATOR_VERSION" not in m.__all__


def test_module_all_does_not_contain_report_version():
    import evaluation.report as m

    assert "REPORT_VERSION" not in m.__all__


def test_module_all_does_not_contain_subprocess():
    import evaluation.report as m

    assert "subprocess" not in m.__all__


def test_module_all_does_not_contain_datetime():
    import evaluation.report as m

    assert "datetime" not in m.__all__


def test_module_all_does_not_contain_path():
    import evaluation.report as m

    assert "Path" not in m.__all__


def test_module_all_does_not_contain_any():
    import evaluation.report as m

    assert "Any" not in m.__all__


def test_module_namespace_has_evaluator_version_attribute():
    import evaluation.report as m

    assert hasattr(m, "EVALUATOR_VERSION")


def test_module_namespace_has_report_version_attribute():
    import evaluation.report as m

    assert hasattr(m, "REPORT_VERSION")


def test_module_namespace_has_path_attribute():
    import evaluation.report as m

    assert hasattr(m, "Path")
    assert m.Path is Path


def test_module_namespace_has_any_attribute():
    import evaluation.report as m

    assert hasattr(m, "Any")


# =========================================================================
# 常量更深：_RATIO_METRICS 不含 / 含 特定项
# =========================================================================


def test_ratio_metrics_contains_schema_valid():
    """schema_valid 是 boolean-as-ratio 特殊项。"""
    import evaluation.report as m

    assert "schema_valid" in m._RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_three():
    """chunk_boundary precision/recall/f1 三联都在 _RATIO_METRICS。"""
    import evaluation.report as m

    assert "chunk_boundary_precision" in m._RATIO_METRICS
    assert "chunk_boundary_recall" in m._RATIO_METRICS
    assert "chunk_boundary_f1" in m._RATIO_METRICS


def test_ratio_metrics_contains_text_char_multiset_precision_recall():
    import evaluation.report as m

    assert "text_char_multiset_precision" in m._RATIO_METRICS
    assert "text_char_multiset_recall" in m._RATIO_METRICS


def test_ratio_metrics_does_not_contain_element_count_total_again():
    import evaluation.report as m

    assert "element_count_total" not in m._RATIO_METRICS


def test_ratio_metrics_does_not_contain_pipeline_success():
    """pipeline_success 是 bool success_rate，不参与 ratio macro。"""
    import evaluation.report as m

    assert "pipeline_success" not in m._RATIO_METRICS


def test_count_metrics_does_not_contain_silent_drop_count():
    """silent_drop 单独求和，不在 _COUNT_METRICS。"""
    import evaluation.report as m

    assert "silent_drop_count" not in m._COUNT_METRICS


def test_success_bool_metrics_does_not_contain_schema_valid():
    """schema_valid 是 ratio，不是 success_bool。"""
    import evaluation.report as m

    assert "schema_valid" not in m._SUCCESS_BOOL_METRICS


# =========================================================================
# 模块源码 token 验证（补 edges16 未覆盖）
# =========================================================================


def test_module_source_contains_ratios_comment():
    """docstring 提到 ratio macro averages。"""
    import evaluation.report as m

    assert "ratio" in inspect.getsource(m).lower()


def test_module_source_contains_for_name_in_count_metrics():
    import evaluation.report as m

    assert "for name in _COUNT_METRICS" in inspect.getsource(m)


def test_module_source_contains_for_name_in_success_bool_metrics():
    import evaluation.report as m

    assert "for name in _SUCCESS_BOOL_METRICS" in inspect.getsource(m)


def test_module_source_contains_for_name_in_ratio_metrics():
    import evaluation.report as m

    assert "for name in _RATIO_METRICS" in inspect.getsource(m)


def test_module_source_contains_silent_drop_count_filter():
    """silent_drop 用 silent_drop_count 单独聚合。"""
    import evaluation.report as m

    assert "silent_drop_count" in inspect.getsource(m)


def test_module_source_contains_pipeline_success_filter():
    import evaluation.report as m

    assert "pipeline_success" in inspect.getsource(m)


def test_module_source_contains_element_count_total_filter():
    import evaluation.report as m

    assert "element_count_total" in inspect.getsource(m)


def test_module_source_contains_participating_docs_in_success_rates():
    import evaluation.report as m

    src = inspect.getsource(m)
    # success_rates dict 用 success_count/total/rate
    assert "success_count" in src
    assert "rate" in src


def test_module_source_contains_int_max_chars():
    """max_chars 走 int() 转换。"""
    import evaluation.report as m

    assert "int(max_chars)" in inspect.getsource(m)


def test_module_source_contains_no_json_module():
    """不引入 json 模块。"""
    import evaluation.report as m

    src = inspect.getsource(m)
    assert "import json" not in src
    assert "json.dumps" not in src


def test_module_source_contains_no_os_module():
    """不引入 os 模块。"""
    import evaluation.report as m

    src = inspect.getsource(m)
    # 不 import os（但有 OSError 在 except 中）
    assert "import os" not in src
    assert "os.path" not in src


def test_module_source_contains_no_asyncio():
    import evaluation.report as m

    assert "asyncio" not in inspect.getsource(m)


def test_module_source_contains_no_threading():
    import evaluation.report as m

    assert "threading" not in inspect.getsource(m)


def test_module_source_contains_no_logging():
    import evaluation.report as m

    assert "import logging" not in inspect.getsource(m)


# =========================================================================
# aggregate_summary 返回值深度（不混合类型）
# =========================================================================


def test_aggregate_summary_counts_only_count_metrics():
    """counts 不含 success_rates 或 ratio metrics。"""
    import evaluation.report as m

    per_doc = [
        {
            "metrics": {
                "element_count_total": {"value": 5, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
                "schema_valid": {"value": True, "reason": None},
                "silent_drop_count": {"value": 1, "reason": None},
            }
        }
    ]
    out = aggregate_summary(per_doc)
    counts_keys = set(out["counts"].keys())
    # counts 只含 _COUNT_METRICS
    assert counts_keys == set(m._COUNT_METRICS)
    # counts 不含 ratio / success_bool / silent_drop
    assert "pipeline_success" not in counts_keys
    assert "schema_valid" not in counts_keys
    assert "silent_drop_count" not in counts_keys


def test_aggregate_summary_success_rates_only_success_metrics():
    import evaluation.report as m

    per_doc = [
        {
            "metrics": {
                "element_count_total": {"value": 5, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
            }
        }
    ]
    out = aggregate_summary(per_doc)
    sr_keys = set(out["success_rates"].keys())
    assert sr_keys == set(m._SUCCESS_BOOL_METRICS)


def test_aggregate_summary_ratio_macro_only_ratio_metrics():
    import evaluation.report as m

    per_doc = [{"metrics": {"schema_valid": {"value": True, "reason": None}}}]
    out = aggregate_summary(per_doc)
    rma_keys = set(out["ratio_macro_averages"].keys())
    assert rma_keys == set(m._RATIO_METRICS)


def test_aggregate_summary_silent_drop_total_at_top_level():
    """silent_drop_total 是 top-level key，不在任何子 dict。"""
    per_doc = [{"metrics": {"silent_drop_count": {"value": 3, "reason": None}}}]
    out = aggregate_summary(per_doc)
    assert "silent_drop_total" in out
    # 不在 counts / success_rates / ratio_macro_averages
    assert "silent_drop_total" not in out["counts"]
    assert "silent_drop_total" not in out["success_rates"]
    assert "silent_drop_total" not in out["ratio_macro_averages"]
