r"""evaluation/report.py 边角测试 - 第五轮（Round 134）。

补强已有 base/edges/edges2/edges3（共 371 测试）未覆盖的深度路径：
- get_git_provenance：
  - 返回 dict 结构（git_commit/git_dirty 键）
  - 异常路径（subprocess.TimeoutExpired / OSError）→ commit=null, dirty=true
  - returncode 非 0 → commit=None
  - stdout 空 → commit=None
- get_dependency_versions：
  - 返回 dict 含 3 个固定键
  - 包不存在 → None
  - 其他异常 → None
- build_provenance：
  - 9 个键
  - max_chars 转 int
  - evaluator_version / report_version 与常量一致
  - run_timestamp_iso 是 ISO 字符串
- build_devset_section：
  - 6 个键
  - 从 manifest 读取各字段
- aggregate_summary：
  - 4 个顶层键
  - counts 字段结构（sum/participating_docs）
  - success_rates 字段结构（success_count/total/rate）
  - ratio_macro_averages 字段结构（macro_average/participating_docs/not_evaluated）
  - silent_drop_total 顶层字段
  - 不混合类型不变量
- 模块结构深度
- 签名深度
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
from evaluation.report import (
    __all__ as report_all,
)


# =========================================================================
# get_git_provenance 深度
# =========================================================================


def test_get_git_provenance_returns_dict_with_two_keys(tmp_path):
    out = get_git_provenance(tmp_path)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_in_git_repo_returns_commit_str(tmp_path):
    """在真实 git 仓库（本 worktree）内调用 → commit 是 40 字符 hex。"""
    out = get_git_provenance(Path(__file__).resolve().parent)
    assert out["git_commit"] is not None
    assert isinstance(out["git_commit"], str)
    assert len(out["git_commit"]) == 40


def test_get_git_provenance_git_dirty_is_bool(tmp_path):
    out = get_git_provenance(Path(__file__).resolve().parent)
    assert isinstance(out["git_dirty"], bool)


def test_get_git_provenance_non_git_dir_commit_none(tmp_path):
    """非 git 目录 → commit=None（rev-parse 失败）。"""
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_os_exception_returns_dirty_true(tmp_path, monkeypatch):
    """OSError 触发 → commit=None, dirty=True。"""
    def _raise(*args, **kwargs):
        raise OSError("simulated")
    monkeypatch.setattr(subprocess, "run", _raise)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_timeout_returns_dirty_true(tmp_path, monkeypatch):
    """TimeoutExpired 触发 → commit=None, dirty=True。"""
    def _raise(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=10)
    monkeypatch.setattr(subprocess, "run", _raise)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_rev_parse_nonzero_returncode_commit_none(tmp_path, monkeypatch):
    """rev-parse 返回非 0 → commit 保持 None。"""
    class _Mock:
        returncode = 1
        stdout = ""

        def __init__(self):
            pass

    def _fake_run(cmd, *args, **kwargs):
        return _Mock()
    monkeypatch.setattr(subprocess, "run", _fake_run)
    out = get_git_provenance(tmp_path)
    # 第一次调用 rev-parse returncode=1 → commit=None
    # 第二次调用 status porcelain 也 returncode=1 → dirty = (1==0 and ...) = False
    assert out["git_commit"] is None
    # 当 status returncode != 0 时，dirty=False（按代码字面）
    assert out["git_dirty"] is False


def test_get_git_provenance_empty_stdout_commit_none(tmp_path, monkeypatch):
    """rev-parse stdout 空 → commit = (None or None) = None。"""
    call_count = [0]

    class _Mock:
        def __init__(self, returncode, stdout):
            self.returncode = returncode
            self.stdout = stdout

    def _fake_run(cmd, *args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return _Mock(0, "")  # rev-parse: empty stdout
        return _Mock(0, "")  # status: empty stdout → clean

    monkeypatch.setattr(subprocess, "run", _fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is False


def test_get_git_provenance_porcelain_nonempty_dirty_true(tmp_path, monkeypatch):
    """porcelain 输出非空 → dirty=True。"""
    call_count = [0]

    class _Mock:
        def __init__(self, returncode, stdout):
            self.returncode = returncode
            self.stdout = stdout

    def _fake_run(cmd, *args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return _Mock(0, "abc123\n")  # rev-parse: commit
        return _Mock(0, " M file.txt\n")  # status: dirty

    monkeypatch.setattr(subprocess, "run", _fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is True


def test_get_git_provenance_porcelain_empty_dirty_false(tmp_path, monkeypatch):
    """porcelain 输出空 → dirty=False。"""
    call_count = [0]

    class _Mock:
        def __init__(self, returncode, stdout):
            self.returncode = returncode
            self.stdout = stdout

    def _fake_run(cmd, *args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return _Mock(0, "abc123\n")
        return _Mock(0, "")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


# =========================================================================
# get_dependency_versions 深度
# =========================================================================


def test_get_dependency_versions_returns_three_keys():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_are_str_or_none():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str), f"{k}={v!r}"


def test_get_dependency_versions_pdfplumber_in_installed_env():
    """实际安装环境中 pdfplumber 应有版本号。"""
    out = get_dependency_versions()
    # 在 .venv 中 pdfplumber 已装
    assert out["pdfplumber"] is not None
    assert len(out["pdfplumber"]) > 0


def test_get_dependency_versions_handles_package_not_found(monkeypatch):
    """模拟 PackageNotFoundError → None。"""
    import importlib.metadata as md

    def _fake_version(name):
        raise md.PackageNotFoundError(name)

    monkeypatch.setattr(md, "version", _fake_version)
    out = get_dependency_versions()
    for k in ("pdfplumber", "python-docx", "pypdfium2"):
        assert out[k] is None


def test_get_dependency_versions_handles_other_exception(monkeypatch):
    """模拟其他异常 → None。"""
    import importlib.metadata as md

    def _fake_version(name):
        raise ValueError("unexpected")

    monkeypatch.setattr(md, "version", _fake_version)
    out = get_dependency_versions()
    for k in ("pdfplumber", "python-docx", "pypdfium2"):
        assert out[k] is None


# =========================================================================
# build_provenance 深度
# =========================================================================


def test_build_provenance_returns_nine_keys(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    expected = {
        "git_commit",
        "git_dirty",
        "evaluator_version",
        "report_version",
        "parser_name",
        "parser_version",
        "dependencies",
        "max_chars",
        "run_timestamp_iso",
    }
    assert set(out.keys()) == expected
    assert len(out) == 9


def test_build_provenance_evaluator_version_matches_constant(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_matches_constant(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_passed_through(tmp_path):
    out = build_provenance(tmp_path, "kreuzberg", 800, None)
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_passed_through(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.2.3")
    assert out["parser_version"] == "1.2.3"


def test_build_provenance_parser_version_none(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_max_chars_int(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_str_converted_to_int(tmp_path):
    """max_chars 传入 str(800) → 转 int 800。"""
    out = build_provenance(tmp_path, "fallback", "800", None)
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_dependencies_is_dict(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_run_timestamp_iso_is_str(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["run_timestamp_iso"], str)


def test_build_provenance_run_timestamp_iso_parseable(tmp_path):
    """ISO 时间戳能被 datetime.fromisoformat 解析。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    parsed = datetime.fromisoformat(out["run_timestamp_iso"])
    assert isinstance(parsed, datetime)


def test_build_provenance_run_timestamp_iso_has_timezone(tmp_path):
    """带时区的 ISO 字符串。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    # astimezone().isoformat() 输出含 +HH:MM
    assert "+" in out["run_timestamp_iso"] or "-" in out["run_timestamp_iso"][10:]


def test_build_provenance_git_fields_present(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert "git_commit" in out
    assert "git_dirty" in out


# =========================================================================
# build_devset_section 深度
# =========================================================================


class _FakeManifest:
    """最小 Manifest 替身，仅含 build_devset_section 用到的属性。"""

    def __init__(
        self,
        devset_status="incomplete",
        file_count=5,
        content_group_count=2,
        pdf_count=3,
        docx_count=2,
        categories_covered=("academic", "report"),
    ):
        self.devset_status = devset_status
        self.file_count = file_count
        self.content_group_count = content_group_count
        self.pdf_count = pdf_count
        self.docx_count = docx_count
        self.categories_covered = categories_covered


def test_build_devset_section_six_keys():
    out = build_devset_section(_FakeManifest())
    expected = {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }
    assert set(out.keys()) == expected
    assert len(out) == 6


def test_build_devset_section_status_field():
    m = _FakeManifest(devset_status="complete")
    assert build_devset_section(m)["status"] == "complete"


def test_build_devset_section_file_count_field():
    m = _FakeManifest(file_count=42)
    assert build_devset_section(m)["file_count"] == 42


def test_build_devset_section_content_group_count_field():
    m = _FakeManifest(content_group_count=7)
    assert build_devset_section(m)["content_group_count"] == 7


def test_build_devset_section_pdf_count_field():
    m = _FakeManifest(pdf_count=11)
    assert build_devset_section(m)["pdf_count"] == 11


def test_build_devset_section_docx_count_field():
    m = _FakeManifest(docx_count=4)
    assert build_devset_section(m)["docx_count"] == 4


def test_build_devset_section_categories_covered_tuple():
    cats = ("academic", "report", "invoice")
    m = _FakeManifest(categories_covered=cats)
    assert build_devset_section(m)["categories_covered"] == cats


def test_build_devset_section_categories_covered_list():
    cats = ["academic", "report"]
    m = _FakeManifest(categories_covered=cats)
    assert build_devset_section(m)["categories_covered"] == cats


# =========================================================================
# aggregate_summary 顶层结构
# =========================================================================


def test_aggregate_summary_top_level_keys():
    out = aggregate_summary([])
    assert set(out.keys()) == {
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    }


def test_aggregate_summary_counts_structure():
    out = aggregate_summary([])
    assert "counts" in out
    counts = out["counts"]
    # 只含 element_count_total
    assert set(counts.keys()) == {"element_count_total"}
    # 结构：sum + participating_docs
    assert set(counts["element_count_total"].keys()) == {"sum", "participating_docs"}


def test_aggregate_summary_success_rates_structure():
    out = aggregate_summary([])
    sr = out["success_rates"]
    assert set(sr.keys()) == {"pipeline_success"}
    entry = sr["pipeline_success"]
    assert set(entry.keys()) == {"success_count", "total", "rate"}


def test_aggregate_summary_ratio_macro_averages_structure():
    out = aggregate_summary([])
    rm = out["ratio_macro_averages"]
    # 12 ratio metrics
    assert set(rm.keys()) == set(_RATIO_METRICS)
    # 每个 entry 三个字段
    for k, v in rm.items():
        assert set(v.keys()) == {"macro_average", "participating_docs", "not_evaluated"}


def test_aggregate_summary_silent_drop_total_top_level():
    out = aggregate_summary([])
    assert "silent_drop_total" in out
    assert out["silent_drop_total"] is None  # 空 list → None


# =========================================================================
# aggregate_summary counts 深度
# =========================================================================


def test_aggregate_summary_counts_participating_docs_zero_when_empty():
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_counts_sum_none_when_empty():
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"]["sum"] is None


def test_aggregate_summary_counts_participating_docs_one():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}}
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["participating_docs"] == 1
    assert out["counts"]["element_count_total"]["sum"] == 5


def test_aggregate_summary_counts_participating_docs_three():
    per_doc = [
        {"metrics": {"element_count_total": {"value": v, "reason": None}}}
        for v in (1, 2, 3)
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["participating_docs"] == 3
    assert out["counts"]["element_count_total"]["sum"] == 6


def test_aggregate_summary_counts_excludes_none_participating():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 1, "reason": None}}},
        {"metrics": {"element_count_total": {"value": None, "reason": "x"}}},
        {"metrics": {"element_count_total": {"value": 3, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["participating_docs"] == 2
    assert out["counts"]["element_count_total"]["sum"] == 4


# =========================================================================
# aggregate_summary success_rates 深度
# =========================================================================


def test_aggregate_summary_success_rate_one_success_out_of_two():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": "x"}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2
    assert sr["rate"] == 0.5


def test_aggregate_summary_success_rate_counts_only_true():
    """truthy 但非 True（如 1）不计入 success。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": 1, "reason": None}}},  # 非 True
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    # 只 value is True 计 1
    assert sr["success_count"] == 1
    assert sr["total"] == 2


def test_aggregate_summary_success_rate_total_includes_none():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": None, "reason": "x"}}},
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    # total 始终是 len(per_doc_results)
    assert sr["total"] == 2
    assert sr["success_count"] == 1
    assert sr["rate"] == 0.5


# =========================================================================
# aggregate_summary ratio_macro_averages 深度
# =========================================================================


def test_aggregate_summary_ratio_macro_average_one_value():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}}
    ]
    out = aggregate_summary(per_doc)
    rm = out["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] == 1.0
    assert rm["participating_docs"] == 1
    assert rm["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_average_two_values():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.5, "reason": None}}},
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    rm = out["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] == 0.75
    assert rm["participating_docs"] == 2
    assert rm["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_average_with_null():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.5, "reason": None}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    rm = out["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] == 0.75
    assert rm["participating_docs"] == 2
    assert rm["not_evaluated"] == 1


def test_aggregate_summary_ratio_macro_average_all_null():
    per_doc = [
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "y"}}},
    ]
    out = aggregate_summary(per_doc)
    rm = out["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] is None
    assert rm["participating_docs"] == 0
    assert rm["not_evaluated"] == 2


def test_aggregate_summary_ratio_macro_average_zero_participates():
    """value=0.0 也参与 macro average。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.0, "reason": None}}},
        {"metrics": {"schema_valid": {"value": 0.0, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    rm = out["ratio_macro_averages"]["schema_valid"]
    assert rm["macro_average"] == 0.0
    assert rm["participating_docs"] == 2


# =========================================================================
# aggregate_summary silent_drop_total 深度
# =========================================================================


def test_aggregate_summary_silent_drop_total_summed():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": 5, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_total_excludes_none():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": None, "reason": "x"}}},
        {"metrics": {"silent_drop_count": {"value": 5, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_total_zero_when_all_zero():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 0, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": 0, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 0


def test_aggregate_summary_silent_drop_total_none_when_empty():
    out = aggregate_summary([])
    assert out["silent_drop_total"] is None


# =========================================================================
# aggregate_summary 不变量
# =========================================================================


def test_aggregate_summary_does_not_mix_silent_drop_into_counts():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 5, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    # silent_drop_count 不该出现在 counts 里
    assert "silent_drop_count" not in out["counts"]


def test_aggregate_summary_does_not_mix_pipeline_success_into_ratios():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    # pipeline_success 不该出现在 ratio_macro_averages
    assert "pipeline_success" not in out["ratio_macro_averages"]


def test_aggregate_summary_no_overall_score_field():
    out = aggregate_summary([])
    assert "overall_score" not in out
    assert "score" not in out
    assert "total_score" not in out


def test_aggregate_summary_idempotent():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
    ]
    out1 = aggregate_summary(per_doc)
    out2 = aggregate_summary(per_doc)
    assert out1 == out2


def test_aggregate_summary_does_not_mutate_input():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
    ]
    per_doc_before = [dict(d) for d in per_doc]
    aggregate_summary(per_doc)
    assert per_doc == per_doc_before


# =========================================================================
# aggregate_summary per-doc 缺字段
# =========================================================================


def test_aggregate_summary_handles_per_doc_without_metrics_key():
    """per_doc 无 metrics 键 → aggregate_summary 抛 KeyError（已知行为）。"""
    per_doc = [{"doc_id": "x"}]
    with pytest.raises(KeyError):
        aggregate_summary(per_doc)


def test_aggregate_summary_handles_per_doc_with_empty_metrics():
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["total"] == 1


def test_aggregate_summary_handles_metrics_with_no_value_key():
    """metric dict 没有 value 键 → 视为 None。"""
    per_doc = [
        {"metrics": {"element_count_total": {"reason": "x"}}},  # 无 value
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_all_is_list():
    assert isinstance(report_all, list)


def test_module_all_count_five():
    assert len(report_all) == 5


def test_module_all_exact_set():
    assert set(report_all) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_constants_count_metrics_is_tuple():
    assert isinstance(_COUNT_METRICS, tuple)


def test_module_constants_count_metrics_value():
    assert _COUNT_METRICS == ("element_count_total",)


def test_module_constants_success_bool_metrics_is_tuple():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_module_constants_success_bool_metrics_value():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_module_constants_ratio_metrics_is_tuple():
    assert isinstance(_RATIO_METRICS, tuple)


def test_module_constants_ratio_metrics_count_twelve():
    assert len(_RATIO_METRICS) == 12


def test_module_constants_ratio_metrics_unique():
    assert len(set(_RATIO_METRICS)) == len(_RATIO_METRICS)


def test_module_constants_ratio_metrics_excludes_pipeline_success():
    assert "pipeline_success" not in _RATIO_METRICS


def test_module_constants_ratio_metrics_excludes_silent_drop_count():
    assert "silent_drop_count" not in _RATIO_METRICS


def test_module_constants_ratio_metrics_excludes_element_count_total():
    assert "element_count_total" not in _RATIO_METRICS


def test_module_constants_ratio_metrics_excludes_figure_caption():
    for name in _RATIO_METRICS:
        assert not name.startswith("figure_caption")


def test_module_constants_disjoint_count_and_ratio():
    assert set(_COUNT_METRICS).isdisjoint(set(_RATIO_METRICS))


def test_module_constants_disjoint_success_and_ratio():
    assert set(_SUCCESS_BOOL_METRICS).isdisjoint(set(_RATIO_METRICS))


def test_module_constants_disjoint_count_and_success():
    assert set(_COUNT_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))


def test_module_docstring_present():
    import evaluation.report as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_aggregation():
    import evaluation.report as mod
    assert "聚合" in mod.__doc__ or "aggregate" in mod.__doc__.lower()


def test_module_docstring_mentions_macro_average():
    import evaluation.report as mod
    assert "macro" in mod.__doc__.lower()


def test_module_imports_subprocess():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "subprocess" in src


def test_module_imports_datetime():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "datetime" in src


def test_module_imports_path():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "Path" in src


def test_module_imports_evaluator_version():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "EVALUATOR_VERSION" in src


def test_module_imports_report_version():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "REPORT_VERSION" in src


def test_module_uses_future_annotations():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


# =========================================================================
# 签名深度
# =========================================================================


def test_get_git_provenance_signature_one_param_project_root():
    sig = inspect.signature(get_git_provenance)
    assert len(sig.parameters) == 1
    assert "project_root" in sig.parameters


def test_get_dependency_versions_signature_no_params():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_build_provenance_signature_four_params():
    sig = inspect.signature(build_provenance)
    assert len(sig.parameters) == 4
    assert list(sig.parameters.keys()) == [
        "project_root",
        "parser_name",
        "max_chars",
        "parser_version",
    ]


def test_build_provenance_no_defaults():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_build_devset_section_signature_one_param_manifest():
    sig = inspect.signature(build_devset_section)
    assert len(sig.parameters) == 1
    assert "manifest" in sig.parameters


def test_aggregate_summary_signature_one_param_per_doc_results():
    sig = inspect.signature(aggregate_summary)
    assert len(sig.parameters) == 1
    assert "per_doc_results" in sig.parameters


def test_get_git_provenance_return_annotation_is_dict():
    sig = inspect.signature(get_git_provenance)
    assert sig.return_annotation is not inspect.Signature.empty


def test_build_provenance_return_annotation_is_dict():
    sig = inspect.signature(build_provenance)
    assert sig.return_annotation is not inspect.Signature.empty


def test_aggregate_summary_return_annotation_is_dict():
    sig = inspect.signature(aggregate_summary)
    assert sig.return_annotation is not inspect.Signature.empty


# =========================================================================
# 综合：JSON 可序列化
# =========================================================================


def test_build_provenance_json_serializable(tmp_path):
    import json
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    s = json.dumps(out)
    parsed = json.loads(s)
    assert parsed == out


def test_aggregate_summary_json_serializable():
    import json
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    s = json.dumps(out)
    parsed = json.loads(s)
    assert parsed == out


def test_build_devset_section_json_serializable():
    """JSON 序列化时 tuple → list；用 list 在 FakeManifest 里避免类型差异。"""
    import json
    out = build_devset_section(_FakeManifest(categories_covered=["academic", "report"]))
    s = json.dumps(out)
    parsed = json.loads(s)
    assert parsed == out
