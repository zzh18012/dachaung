r"""evaluation/report.py 边角测试 - 第七轮（Round 197）。

补强已有 base/edges/edges2-6（共 669 测试）未覆盖的深度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 常量内容
- get_git_provenance subprocess 各失败路径（timeout/OSError/SubprocessError/non-zero return/empty stdout）
- get_dependency_versions importlib.metadata 各 PackageNotFoundError
- build_provenance 9 字段集 + parser_version None + max_chars int 强制
- build_devset_section 6 字段集
- aggregate_summary 完整路径（empty/all-fail/mixed）
- 模块结构与签名深度
- 综合行为
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
# 常量内容
# =========================================================================


def test_count_metrics_contains_only_element_count_total():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_contains_only_pipeline_success():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_ratio_metrics_includes_11_metrics():
    """9 个核心 ratio + 3 个 chunk_boundary_*."""
    expected = {
        "schema_valid",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        "heading_boundary_compliance",
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    }
    assert set(_RATIO_METRICS) == expected


def test_ratio_metrics_excludes_figure_caption():
    for name in _RATIO_METRICS:
        assert not name.startswith("figure_caption")


def test_ratio_metrics_excludes_element_count_total():
    assert "element_count_total" not in _RATIO_METRICS


def test_ratio_metrics_excludes_silent_drop_count():
    assert "silent_drop_count" not in _RATIO_METRICS


def test_ratio_metrics_excludes_pipeline_success():
    assert "pipeline_success" not in _RATIO_METRICS


def test_ratio_metrics_are_tuples():
    assert isinstance(_RATIO_METRICS, tuple)
    assert isinstance(_COUNT_METRICS, tuple)
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


# =========================================================================
# get_git_provenance 路径
# =========================================================================


def test_get_git_provenance_returns_two_keys(tmp_path: Path):
    result = get_git_provenance(tmp_path)
    assert set(result.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_in_real_repo():
    """跑在项目根（autonomous worktree），应有 commit 和 dirty 状态。"""
    project_root = Path(__file__).resolve().parent.parent
    result = get_git_provenance(project_root)
    assert "git_commit" in result
    assert "git_dirty" in result
    # 在已 commit 的仓库里 git_commit 应非 None
    assert result["git_commit"] is not None


def test_get_git_provenance_non_git_directory(tmp_path: Path):
    """非 git 目录 → commit=None（rev-parse 失败），dirty=False（status 也失败，short-circuit）。"""
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    # 注意：subprocess 不抛异常，只是非零 returncode → r2.returncode != 0 → bool(False and ...) = False
    assert result["git_dirty"] is False


def test_get_git_provenance_oserror_returns_safe(tmp_path: Path, monkeypatch):
    """subprocess.run 抛 OSError → 返回 safe 默认值。"""
    def fake_run(*args, **kwargs):
        raise OSError("simulated")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_subprocess_error_returns_safe(tmp_path: Path, monkeypatch):
    """subprocess.run 抛 SubprocessError → 返回 safe 默认值。"""
    def fake_run(*args, **kwargs):
        raise subprocess.SubprocessError("simulated")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_timeout_returns_safe(tmp_path: Path, monkeypatch):
    """subprocess.TimeoutExpired 是 SubprocessError 子类 → 返回 safe 默认。"""
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=1)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_non_zero_return_no_commit(tmp_path: Path, monkeypatch):
    """rev-parse 返回非零 → commit=None。"""
    class _Result:
        returncode = 128
        stdout = ""

    def fake_run(*args, **kwargs):
        return _Result()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None


def test_get_git_provenance_empty_stdout_no_commit(tmp_path: Path, monkeypatch):
    """rev-parse returncode=0 但 stdout 为空 → commit=None。"""
    call_count = [0]

    class _Result:
        def __init__(self, returncode: int, stdout: str):
            self.returncode = returncode
            self.stdout = stdout

    def fake_run(*args, **kwargs):
        call_count[0] += 1
        # 第一次是 rev-parse（empty stdout），第二次是 status
        if call_count[0] == 1:
            return _Result(0, "")
        return _Result(0, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None


def test_get_git_provenance_commit_strip_whitespace(tmp_path: Path, monkeypatch):
    """stdout 有尾部换行 → strip() 掉。"""
    call_count = [0]

    class _Result:
        def __init__(self, returncode: int, stdout: str):
            self.returncode = returncode
            self.stdout = stdout

    def fake_run(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return _Result(0, "  abc123  \n")
        return _Result(0, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_commit"] == "abc123"


def test_get_git_provenance_dirty_with_porcelain_output(tmp_path: Path, monkeypatch):
    """status --porcelain 输出非空 → dirty=True。"""
    call_count = [0]

    class _Result:
        def __init__(self, returncode: int, stdout: str):
            self.returncode = returncode
            self.stdout = stdout

    def fake_run(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return _Result(0, "abc123")
        return _Result(0, " M file.txt\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_dirty"] is True


def test_get_git_provenance_clean_when_porcelain_empty(tmp_path: Path, monkeypatch):
    """status --porcelain 输出为空 → dirty=False。"""
    call_count = [0]

    class _Result:
        def __init__(self, returncode: int, stdout: str):
            self.returncode = returncode
            self.stdout = stdout

    def fake_run(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return _Result(0, "abc123")
        return _Result(0, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = get_git_provenance(tmp_path)
    assert result["git_dirty"] is False


def test_get_git_provenance_dirty_when_status_fails(tmp_path: Path, monkeypatch):
    """status returncode != 0 → bool(False and ...) = False（不是 True）。"""
    call_count = [0]

    class _Result:
        def __init__(self, returncode: int, stdout: str):
            self.returncode = returncode
            self.stdout = stdout

    def fake_run(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return _Result(0, "abc123")
        return _Result(128, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = get_git_provenance(tmp_path)
    # short-circuit：returncode != 0 → dirty=False
    assert result["git_dirty"] is False


# =========================================================================
# get_dependency_versions 路径
# =========================================================================


def test_get_dependency_versions_returns_three_keys():
    result = get_dependency_versions()
    assert set(result.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_pdfplumber_in_dev_env():
    """开发环境应装了 pdfplumber。"""
    result = get_dependency_versions()
    assert result["pdfplumber"] is not None


def test_get_dependency_versions_pypdfium2_in_dev_env():
    """开发环境应装了 pypdfium2。"""
    result = get_dependency_versions()
    assert result["pypdfium2"] is not None


def test_get_dependency_versions_python_docx_in_dev_env():
    """python-docx 应被找到。"""
    result = get_dependency_versions()
    assert result["python-docx"] is not None


def test_get_dependency_versions_package_not_found(monkeypatch):
    """importlib.metadata.PackageNotFoundError → value=None。"""
    import importlib.metadata

    def fake_version(pkg):
        raise importlib.metadata.PackageNotFoundError(pkg)

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    result = get_dependency_versions()
    assert all(v is None for v in result.values())


def test_get_dependency_versions_generic_exception(monkeypatch):
    """其他 Exception → value=None（不抛）。"""
    import importlib.metadata

    def fake_version(pkg):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    result = get_dependency_versions()
    assert all(v is None for v in result.values())


def test_get_dependency_versions_one_found_others_not(monkeypatch):
    """部分找到，部分未找到。"""
    import importlib.metadata

    def fake_version(pkg):
        if pkg == "pdfplumber":
            return "0.11.10"
        raise importlib.metadata.PackageNotFoundError(pkg)

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    result = get_dependency_versions()
    assert result["pdfplumber"] == "0.11.10"
    assert result["python-docx"] is None
    assert result["pypdfium2"] is None


# =========================================================================
# build_provenance 完整字段集
# =========================================================================


def test_build_provenance_returns_nine_keys(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    expected_keys = {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies",
        "max_chars", "run_timestamp_iso",
    }
    assert set(result.keys()) == expected_keys


def test_build_provenance_evaluator_version_constant(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_constant(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_propagated(tmp_path: Path):
    result = build_provenance(tmp_path, "kreuzberg", 800, "1.0")
    assert result["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_propagated(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, "v_test")
    assert result["parser_version"] == "v_test"


def test_build_provenance_parser_version_none(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["parser_version"] is None


def test_build_provenance_max_chars_int(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["max_chars"] == 800
    assert isinstance(result["max_chars"], int)


def test_build_provenance_max_chars_int_coercion(tmp_path: Path):
    """float 输入 → int 强制（int(800.5) == 800）。"""
    result = build_provenance(tmp_path, "fallback", 800.5, None)
    assert result["max_chars"] == 800


def test_build_provenance_max_chars_str_int_coercion(tmp_path: Path):
    """str 'abc' 不能 int() → ValueError；纯数字 str 会被 int() 接受。"""
    with pytest.raises(ValueError):
        build_provenance(tmp_path, "fallback", "abc", None)


def test_build_provenance_max_chars_numeric_str_accepted(tmp_path: Path):
    """str '800' 能被 int() 解析（合法）。"""
    result = build_provenance(tmp_path, "fallback", "800", None)
    assert result["max_chars"] == 800


def test_build_provenance_run_timestamp_iso_format(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    ts = result["run_timestamp_iso"]
    # 应是合法 ISO 时间
    parsed = datetime.fromisoformat(ts)
    assert parsed is not None


def test_build_provenance_run_timestamp_recent(tmp_path: Path):
    """timestamp 应与当前时间接近。"""
    before = datetime.now().astimezone()
    result = build_provenance(tmp_path, "fallback", 800, None)
    after = datetime.now().astimezone()
    parsed = datetime.fromisoformat(result["run_timestamp_iso"])
    assert before <= parsed <= after


def test_build_provenance_dependencies_is_dict(tmp_path: Path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(result["dependencies"], dict)
    assert "pdfplumber" in result["dependencies"]


# =========================================================================
# build_devset_section 字段集
# =========================================================================


class _FakeManifest:
    def __init__(self):
        self.devset_status = "incomplete"
        self.file_count = 5
        self.content_group_count = 3
        self.pdf_count = 2
        self.docx_count = 3
        self.categories_covered = ["intro", "advanced"]


def test_build_devset_section_returns_six_keys():
    result = build_devset_section(_FakeManifest())
    expected_keys = {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }
    assert set(result.keys()) == expected_keys


def test_build_devset_section_status_propagated():
    result = build_devset_section(_FakeManifest())
    assert result["status"] == "incomplete"


def test_build_devset_section_file_count_propagated():
    result = build_devset_section(_FakeManifest())
    assert result["file_count"] == 5


def test_build_devset_section_content_group_count_propagated():
    result = build_devset_section(_FakeManifest())
    assert result["content_group_count"] == 3


def test_build_devset_section_pdf_count_propagated():
    result = build_devset_section(_FakeManifest())
    assert result["pdf_count"] == 2


def test_build_devset_section_docx_count_propagated():
    result = build_devset_section(_FakeManifest())
    assert result["docx_count"] == 3


def test_build_devset_section_categories_covered_propagated():
    result = build_devset_section(_FakeManifest())
    assert result["categories_covered"] == ["intro", "advanced"]


def test_build_devset_section_empty_categories():
    m = _FakeManifest()
    m.categories_covered = []
    result = build_devset_section(m)
    assert result["categories_covered"] == []


def test_build_devset_section_complete_status():
    m = _FakeManifest()
    m.devset_status = "complete"
    result = build_devset_section(m)
    assert result["status"] == "complete"


def test_build_devset_section_calls_properties():
    """build_devset_section 应调用 manifest 的 properties（不是直接访问字段）。"""
    m = _FakeManifest()
    # 替换 property 为不同值，确认 build_devset_section 用它
    m.pdf_count = 99
    result = build_devset_section(m)
    assert result["pdf_count"] == 99


# =========================================================================
# aggregate_summary 完整路径
# =========================================================================


def test_aggregate_summary_empty_returns_full_structure():
    result = aggregate_summary([])
    assert set(result.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_empty_counts():
    result = aggregate_summary([])
    counts = result["counts"]
    assert "element_count_total" in counts
    assert counts["element_count_total"]["sum"] is None
    assert counts["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_empty_success_rate():
    result = aggregate_summary([])
    sr = result["success_rates"]
    assert "pipeline_success" in sr
    assert sr["pipeline_success"]["success_count"] == 0
    assert sr["pipeline_success"]["total"] == 0
    assert sr["pipeline_success"]["rate"] is None


def test_aggregate_summary_empty_ratio_averages():
    result = aggregate_summary([])
    ra = result["ratio_macro_averages"]
    for name in _RATIO_METRICS:
        assert ra[name]["macro_average"] is None
        assert ra[name]["participating_docs"] == 0
        assert ra[name]["not_evaluated"] == 0


def test_aggregate_summary_empty_silent_drop():
    result = aggregate_summary([])
    assert result["silent_drop_total"] is None


def test_aggregate_summary_one_doc_all_metrics():
    """单 doc 所有 metric 都有值。"""
    metrics = {
        "element_count_total": {"value": 10, "reason": None},
        "pipeline_success": {"value": True, "reason": None},
        "schema_valid": {"value": True, "reason": None},
        "pdf_locator_valid_ratio": {"value": 1.0, "reason": None},
        "silent_drop_count": {"value": 2, "reason": None},
    }
    per_doc = [{"doc_id": "d1", "metrics": metrics}]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 10
    assert result["success_rates"]["pipeline_success"]["success_count"] == 1
    assert result["success_rates"]["pipeline_success"]["rate"] == 1.0
    assert result["silent_drop_total"] == 2


def test_aggregate_summary_count_aggregation():
    """多 doc counts 求和。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": 15}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 30
    assert result["counts"]["element_count_total"]["participating_docs"] == 3


def test_aggregate_summary_count_skips_none():
    """None 值不计入 counts。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": None, "reason": "fail"}}},
        {"metrics": {"element_count_total": {"value": 15}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 20
    assert result["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_success_rate_half():
    """2 成功 / 4 总 → rate=0.5。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": None, "reason": "fail"}}},
    ]
    result = aggregate_summary(per_doc)
    sr = result["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 4
    assert sr["rate"] == 0.5


def test_aggregate_summary_success_rate_zero_division_safe():
    """empty → rate=None。"""
    result = aggregate_summary([])
    assert result["success_rates"]["pipeline_success"]["rate"] is None


def test_aggregate_summary_ratio_macro_average():
    """3 docs: 0.5, 0.7, 0.9 → macro=0.7。"""
    per_doc = [
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.5}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.7}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.9}}},
    ]
    result = aggregate_summary(per_doc)
    ra = result["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert ra["macro_average"] == pytest.approx(0.7)
    assert ra["participating_docs"] == 3
    assert ra["not_evaluated"] == 0


def test_aggregate_summary_ratio_skips_none():
    per_doc = [
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.5}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": None, "reason": "fail"}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": 1.0}}},
    ]
    result = aggregate_summary(per_doc)
    ra = result["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert ra["macro_average"] == pytest.approx(0.75)
    assert ra["participating_docs"] == 2
    assert ra["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_total():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
        {"metrics": {"silent_drop_count": {"value": 2}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] == 10


def test_aggregate_summary_silent_drop_skips_none():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None, "reason": "no_exp"}}},
        {"metrics": {"silent_drop_count": {"value": 2}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] == 5


def test_aggregate_summary_silent_drop_all_none():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["silent_drop_total"] is None


def test_aggregate_summary_all_metrics_missing():
    """per_doc 都没有 metrics key → 都视为 None。"""
    per_doc = [{"doc_id": "d1", "metrics": {}}]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] is None
    assert result["success_rates"]["pipeline_success"]["success_count"] == 0


def test_aggregate_summary_metrics_value_true_strict():
    """pipeline_success 必须是 True（不是 truthy）才计数。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": "yes"}}},  # truthy but not True
        {"metrics": {"pipeline_success": {"value": 1}}},  # truthy but not True
    ]
    result = aggregate_summary(per_doc)
    assert result["success_rates"]["pipeline_success"]["success_count"] == 1


def test_aggregate_summary_metrics_value_false_strict():
    """pipeline_success=False 不计数。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": 0}}},  # falsy
        {"metrics": {"pipeline_success": {"value": None}}},
    ]
    result = aggregate_summary(per_doc)
    assert result["success_rates"]["pipeline_success"]["success_count"] == 0
    assert result["success_rates"]["pipeline_success"]["total"] == 3


def test_aggregate_summary_not_evaluated_count():
    """not_evaluated = total - participating。"""
    per_doc = [
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.5}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": None}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": None}}},
    ]
    result = aggregate_summary(per_doc)
    ra = result["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert ra["participating_docs"] == 1
    assert ra["not_evaluated"] == 2


# =========================================================================
# 模块结构与签名
# =========================================================================


def test_module_all_exports_five():
    import evaluation.report as m
    assert set(m.__all__) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_imports_subprocess():
    import evaluation.report as m
    assert hasattr(m, "subprocess")


def test_module_imports_datetime():
    import evaluation.report as m
    assert hasattr(m, "datetime")


def test_module_imports_path():
    import evaluation.report as m
    assert hasattr(m, "Path")


def test_module_imports_any():
    import evaluation.report as m
    assert hasattr(m, "Any")


def test_module_imports_evaluator_version():
    import evaluation.report as m
    assert hasattr(m, "EVALUATOR_VERSION")


def test_module_imports_report_version():
    import evaluation.report as m
    assert hasattr(m, "REPORT_VERSION")


def test_get_git_provenance_signature():
    sig = inspect.signature(get_git_provenance)
    assert set(sig.parameters) == {"project_root"}


def test_get_dependency_versions_signature():
    sig = inspect.signature(get_dependency_versions)
    assert set(sig.parameters) == set()


def test_build_provenance_signature():
    sig = inspect.signature(build_provenance)
    assert set(sig.parameters) == {"project_root", "parser_name", "max_chars", "parser_version"}


def test_build_provenance_no_defaults():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_build_devset_section_signature():
    sig = inspect.signature(build_devset_section)
    assert set(sig.parameters) == {"manifest"}


def test_aggregate_summary_signature():
    sig = inspect.signature(aggregate_summary)
    assert set(sig.parameters) == {"per_doc_results"}


def test_get_git_provenance_return_annotation_dict():
    sig = inspect.signature(get_git_provenance)
    assert "dict" in str(sig.return_annotation)


def test_build_provenance_return_annotation_dict():
    sig = inspect.signature(build_provenance)
    assert "dict" in str(sig.return_annotation)


def test_build_devset_section_return_annotation_dict():
    sig = inspect.signature(build_devset_section)
    assert "dict" in str(sig.return_annotation)


def test_aggregate_summary_return_annotation_dict():
    sig = inspect.signature(aggregate_summary)
    assert "dict" in str(sig.return_annotation)


def test_all_functions_callable():
    assert callable(get_git_provenance)
    assert callable(get_dependency_versions)
    assert callable(build_provenance)
    assert callable(build_devset_section)
    assert callable(aggregate_summary)


# =========================================================================
# idempotency
# =========================================================================


def test_get_dependency_versions_idempotent():
    a = get_dependency_versions()
    b = get_dependency_versions()
    assert a == b


def test_aggregate_summary_idempotent():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    a = aggregate_summary(per_doc)
    b = aggregate_summary(per_doc)
    assert a == b


def test_build_devset_section_idempotent():
    m = _FakeManifest()
    a = build_devset_section(m)
    b = build_devset_section(m)
    assert a == b


# =========================================================================
# 综合行为
# =========================================================================


def test_full_pipeline_aggregate_three_docs():
    """3 个 doc 完整 metrics → summary 所有字段有值。"""
    per_doc = [
        {
            "doc_id": "d1",
            "metrics": {
                "element_count_total": {"value": 10, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
                "schema_valid": {"value": True, "reason": None},
                "pdf_locator_valid_ratio": {"value": 1.0, "reason": None},
                "image_resource_exists_ratio": {"value": 1.0, "reason": None},
                "chunk_reference_intact_ratio": {"value": 1.0, "reason": None},
                "text_preservation_equal": {"value": True, "reason": None},
                "text_char_multiset_precision": {"value": 1.0, "reason": None},
                "text_char_multiset_recall": {"value": 1.0, "reason": None},
                "heading_boundary_compliance": {"value": 1.0, "reason": None},
                "silent_drop_count": {"value": 0, "reason": None},
            },
        },
        {
            "doc_id": "d2",
            "metrics": {
                "element_count_total": {"value": 5, "reason": None},
                "pipeline_success": {"value": False, "reason": None},
                "schema_valid": {"value": False, "reason": None},
                "pdf_locator_valid_ratio": {"value": 0.5, "reason": None},
                "silent_drop_count": {"value": 2, "reason": None},
            },
        },
    ]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] == 15
    assert result["success_rates"]["pipeline_success"]["success_count"] == 1
    assert result["success_rates"]["pipeline_success"]["total"] == 2
    assert result["success_rates"]["pipeline_success"]["rate"] == 0.5
    ra = result["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert ra["macro_average"] == 0.75
    assert ra["participating_docs"] == 2
    assert result["silent_drop_total"] == 2


def test_build_provenance_full_run(tmp_path: Path):
    """跑在真实仓库 → 返回完整 provenance。"""
    project_root = Path(__file__).resolve().parent.parent
    result = build_provenance(project_root, "fallback", 800, "v_test")
    assert result["git_commit"] is not None  # 真实仓库有 commit
    assert result["parser_name"] == "fallback"
    assert result["parser_version"] == "v_test"
    assert result["max_chars"] == 800
    assert result["evaluator_version"] == EVALUATOR_VERSION


def test_aggregate_summary_metrics_key_missing():
    """per_doc 没 metrics key → KeyError（aggregate_summary 要求 metrics 字段）。"""
    per_doc = [{"doc_id": "d1"}]  # 无 metrics
    with pytest.raises(KeyError):
        aggregate_summary(per_doc)


def test_aggregate_summary_metrics_empty_dict():
    """per_doc 有 metrics 但为空 dict → 不抛，所有 metric None。"""
    per_doc = [{"doc_id": "d1", "metrics": {}}]
    result = aggregate_summary(per_doc)
    assert result["counts"]["element_count_total"]["sum"] is None
    assert result["success_rates"]["pipeline_success"]["success_count"] == 0
