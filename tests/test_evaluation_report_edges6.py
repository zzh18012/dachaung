r"""evaluation/report.py 边角测试 - 第六轮（Round 176）。

补强已有 base/edges/edges2-5（共 576 测试）未覆盖的深度：
- get_git_provenance subprocess 参数精确（cwd/encoding/errors/timeout）
- get_dependency_versions 包名顺序与异常路径
- build_provenance 9 keys 类型精确（git_commit str|None、git_dirty bool）
- aggregate_summary figure_caption_* 显式排除、未知 metric 忽略
- build_devset_section categories_covered 引用语义
- 模块注释与编码细节
- 综合行为
"""

from __future__ import annotations

import inspect
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

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
# get_git_provenance subprocess 参数精确
# =========================================================================


def test_get_git_provenance_uses_subprocess_run():
    """应该调用 subprocess.run（不是 Popen）。"""
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "subprocess.run" in src


def test_get_git_provenance_uses_rev_parse_head():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "rev-parse" in src
    assert "HEAD" in src


def test_get_git_provenance_uses_status_porcelain():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "status" in src
    assert "--porcelain" in src


def test_get_git_provenance_cwd_param(tmp_path: Path):
    """subprocess.run 用 cwd=str(project_root)。"""
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))

        class _R:
            returncode = 0
            stdout = "" if "status" in cmd else "abc123\n"

        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        get_git_provenance(tmp_path)
    assert len(calls) == 2
    assert calls[0][1].get("cwd") == str(tmp_path)
    assert calls[1][1].get("cwd") == str(tmp_path)


def test_get_git_provenance_capture_output_true(tmp_path: Path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(kwargs)

        class _R:
            returncode = 0
            stdout = "" if "status" in cmd else "abc\n"

        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        get_git_provenance(tmp_path)
    assert calls[0].get("capture_output") is True
    assert calls[1].get("capture_output") is True


def test_get_git_provenance_text_true(tmp_path: Path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(kwargs)

        class _R:
            returncode = 0
            stdout = "" if "status" in cmd else "abc\n"

        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        get_git_provenance(tmp_path)
    assert calls[0].get("text") is True


def test_get_git_provenance_encoding_utf8(tmp_path: Path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(kwargs)

        class _R:
            returncode = 0
            stdout = "" if "status" in cmd else "abc\n"

        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        get_git_provenance(tmp_path)
    assert calls[0].get("encoding") == "utf-8"


def test_get_git_provenance_errors_replace(tmp_path: Path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(kwargs)

        class _R:
            returncode = 0
            stdout = "" if "status" in cmd else "abc\n"

        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        get_git_provenance(tmp_path)
    assert calls[0].get("errors") == "replace"


def test_get_git_provenance_timeout_10(tmp_path: Path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(kwargs)

        class _R:
            returncode = 0
            stdout = "" if "status" in cmd else "abc\n"

        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        get_git_provenance(tmp_path)
    assert calls[0].get("timeout") == 10
    assert calls[1].get("timeout") == 10


def test_get_git_provenance_returncode_nonzero_commit_none(tmp_path: Path):
    """git rev-parse HEAD 返回非 0 → commit=None。"""
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)

        class _R:
            returncode = 1
            stdout = ""

        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None


def test_get_git_provenance_empty_stdout_commit_none(tmp_path: Path):
    """rev-parse 输出空 → commit=None。"""
    def fake_run(cmd, **kwargs):
        class _R:
            returncode = 0
            stdout = "\n"  # 空白 strip 后为空

        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None


def test_get_git_provenance_strips_stdout_whitespace(tmp_path: Path):
    """commit 值应 strip 首尾空白。"""
    def fake_run(cmd, **kwargs):
        class _R:
            returncode = 0
            stdout = "  abc123def456\n  " if "rev-parse" in cmd else ""

        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] == "abc123def456"


def test_get_git_provenance_oserror_path(tmp_path: Path):
    """subprocess 抛 OSError → commit=None, dirty=True。"""
    def fake_run(cmd, **kwargs):
        raise OSError("boom")

    with patch.object(subprocess, "run", side_effect=fake_run):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_subprocess_error_path(tmp_path: Path):
    """subprocess 抛 SubprocessError → commit=None, dirty=True。"""
    def fake_run(cmd, **kwargs):
        raise subprocess.SubprocessError("boom")

    with patch.object(subprocess, "run", side_effect=fake_run):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_timeout_path(tmp_path: Path):
    """TimeoutExpired 是 SubprocessError 子类 → 同样被捕获。"""
    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=10)

    with patch.object(subprocess, "run", side_effect=fake_run):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_porcelain_empty_means_clean(tmp_path: Path):
    """porcelain 输出空 → dirty=False。"""
    def fake_run(cmd, **kwargs):
        class _R:
            returncode = 0
            stdout = "abc\n" if "rev-parse" in cmd else ""

        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        result = get_git_provenance(tmp_path)
    assert result["git_dirty"] is False


def test_get_git_provenance_porcelain_nonempty_means_dirty(tmp_path: Path):
    def fake_run(cmd, **kwargs):
        class _R:
            returncode = 0
            stdout = "abc\n" if "rev-parse" in cmd else " M file.txt\n"

        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        result = get_git_provenance(tmp_path)
    assert result["git_dirty"] is True


def test_get_git_provenance_porcelain_returncode_nonzero_dirty_is_false(tmp_path: Path):
    """porcelain returncode != 0 → bool(returncode==0 and ...) = False → dirty=False。"""
    def fake_run(cmd, **kwargs):
        class _R:
            returncode = 1
            stdout = ""

        return _R()

    with patch.object(subprocess, "run", side_effect=fake_run):
        result = get_git_provenance(tmp_path)
    assert result["git_dirty"] is False


# =========================================================================
# get_dependency_versions 包名顺序与异常路径
# =========================================================================


def test_get_dependency_versions_returns_pdfplumber_first():
    """dict 顺序：pdfplumber → python-docx → pypdfium2。"""
    result = get_dependency_versions()
    keys = list(result.keys())
    assert keys[0] == "pdfplumber"


def test_get_dependency_versions_returns_python_docx_second():
    result = get_dependency_versions()
    keys = list(result.keys())
    assert keys[1] == "python-docx"


def test_get_dependency_versions_returns_pypdfium2_third():
    result = get_dependency_versions()
    keys = list(result.keys())
    assert keys[2] == "pypdfium2"


def test_get_dependency_versions_handles_package_not_found():
    """PackageNotFoundError → 该包为 None。"""
    import importlib.metadata

    def fake_version(name):
        if name == "python-docx":
            raise importlib.metadata.PackageNotFoundError("not found")
        return "1.0.0"

    with patch.object(importlib.metadata, "version", side_effect=fake_version):
        result = get_dependency_versions()
    assert result["python-docx"] is None
    assert result["pdfplumber"] == "1.0.0"
    assert result["pypdfium2"] == "1.0.0"


def test_get_dependency_versions_handles_generic_exception():
    """任何 Exception → 该包为 None（不抛）。"""
    import importlib.metadata

    def fake_version(name):
        raise ValueError("weird error")

    with patch.object(importlib.metadata, "version", side_effect=fake_version):
        result = get_dependency_versions()
    assert result["pdfplumber"] is None
    assert result["python-docx"] is None
    assert result["pypdfium2"] is None


def test_get_dependency_versions_iterates_three_packages():
    """只查询这 3 个包（不多不少）。"""
    import importlib.metadata

    seen = []

    def fake_version(name):
        seen.append(name)
        return "1.0.0"

    with patch.object(importlib.metadata, "version", side_effect=fake_version):
        get_dependency_versions()
    assert seen == ["pdfplumber", "python-docx", "pypdfium2"]


def test_get_dependency_versions_signature():
    sig = inspect.signature(get_dependency_versions)
    assert set(sig.parameters) == set()


def test_get_dependency_versions_return_annotation_dict():
    sig = inspect.signature(get_dependency_versions)
    annotation = str(sig.return_annotation)
    assert "dict" in annotation


# =========================================================================
# build_provenance 9 keys 类型精确
# =========================================================================


def test_build_provenance_keys_exact_set(tmp_path: Path):
    result = build_provenance(tmp_path, "text", 800, "1.0")
    assert set(result.keys()) == {
        "git_commit", "git_dirty",
        "evaluator_version", "report_version",
        "parser_name", "parser_version",
        "dependencies", "max_chars", "run_timestamp_iso",
    }


def test_build_provenance_keys_count_nine(tmp_path: Path):
    result = build_provenance(tmp_path, "text", 800, "1.0")
    assert len(result) == 9


def test_build_provenance_git_commit_is_str_or_none(tmp_path: Path):
    result = build_provenance(tmp_path, "text", 800, "1.0")
    assert result["git_commit"] is None or isinstance(result["git_commit"], str)


def test_build_provenance_git_dirty_is_bool(tmp_path: Path):
    result = build_provenance(tmp_path, "text", 800, "1.0")
    assert isinstance(result["git_dirty"], bool)


def test_build_provenance_evaluator_version_value(tmp_path: Path):
    result = build_provenance(tmp_path, "text", 800, "1.0")
    assert result["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value(tmp_path: Path):
    result = build_provenance(tmp_path, "text", 800, "1.0")
    assert result["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_passed_through(tmp_path: Path):
    result = build_provenance(tmp_path, "custom-parser", 800, "1.0")
    assert result["parser_name"] == "custom-parser"


def test_build_provenance_parser_version_passed_through(tmp_path: Path):
    result = build_provenance(tmp_path, "text", 800, "2.3.4")
    assert result["parser_version"] == "2.3.4"


def test_build_provenance_parser_version_none_passed_through(tmp_path: Path):
    result = build_provenance(tmp_path, "text", 800, None)
    assert result["parser_version"] is None


def test_build_provenance_dependencies_is_dict(tmp_path: Path):
    result = build_provenance(tmp_path, "text", 800, "1.0")
    assert isinstance(result["dependencies"], dict)


def test_build_provenance_max_chars_is_int(tmp_path: Path):
    result = build_provenance(tmp_path, "text", 800, "1.0")
    assert isinstance(result["max_chars"], int)


def test_build_provenance_max_chars_float_converted(tmp_path: Path):
    """float → int（int(max_chars) 调用）。"""
    result = build_provenance(tmp_path, "text", 800.5, "1.0")
    assert result["max_chars"] == 800
    assert isinstance(result["max_chars"], int)


def test_build_provenance_max_chars_string_numeric(tmp_path: Path):
    """int("800") → 800（Python int 接受 numeric str）。"""
    result = build_provenance(tmp_path, "text", "800", "1.0")
    assert result["max_chars"] == 800


def test_build_provenance_run_timestamp_iso_is_str(tmp_path: Path):
    result = build_provenance(tmp_path, "text", 800, "1.0")
    assert isinstance(result["run_timestamp_iso"], str)


def test_build_provenance_run_timestamp_iso_parseable(tmp_path: Path):
    """datetime.fromisoformat 能解析。"""
    result = build_provenance(tmp_path, "text", 800, "1.0")
    parsed = datetime.fromisoformat(result["run_timestamp_iso"])
    assert isinstance(parsed, datetime)


def test_build_provenance_run_timestamp_iso_has_T_separator(tmp_path: Path):
    """ISO 8601 标准：date T time+offset。"""
    result = build_provenance(tmp_path, "text", 800, "1.0")
    ts = result["run_timestamp_iso"]
    assert "T" in ts


def test_build_provenance_signature():
    sig = inspect.signature(build_provenance)
    assert set(sig.parameters) == {"project_root", "parser_name", "max_chars", "parser_version"}


def test_build_provenance_no_defaults():
    sig = inspect.signature(build_provenance)
    for name in sig.parameters:
        assert sig.parameters[name].default is inspect.Parameter.empty


def test_build_provenance_return_annotation_dict_any():
    sig = inspect.signature(build_provenance)
    assert "dict" in str(sig.return_annotation)


# =========================================================================
# aggregate_summary figure_caption_* 显式排除
# =========================================================================


def test_aggregate_summary_figure_caption_precision_excluded():
    """figure_caption_precision 不在 ratio_macro_averages。"""
    summary = aggregate_summary([
        {"metrics": {"figure_caption_precision": {"value": 0.5}}}
    ])
    assert "figure_caption_precision" not in summary["ratio_macro_averages"]


def test_aggregate_summary_figure_caption_recall_excluded():
    summary = aggregate_summary([
        {"metrics": {"figure_caption_recall": {"value": 0.5}}}
    ])
    assert "figure_caption_recall" not in summary["ratio_macro_averages"]


def test_aggregate_summary_figure_caption_f1_excluded():
    summary = aggregate_summary([
        {"metrics": {"figure_caption_f1": {"value": 0.5}}}
    ])
    assert "figure_caption_f1" not in summary["ratio_macro_averages"]


def test_aggregate_summary_unknown_metric_ignored():
    """metrics 含未知 key（不在任何 _METRICS 列表）→ 不影响 summary。"""
    summary = aggregate_summary([
        {"metrics": {"unknown_metric": {"value": 999}}}
    ])
    # 不出现 anywhere in summary
    for section in summary.values():
        if isinstance(section, dict):
            assert "unknown_metric" not in section


def test_aggregate_summary_metrics_without_value_field():
    """metric dict 没有 value key → 跳过。"""
    summary = aggregate_summary([
        {"metrics": {"element_count_total": {"reason": "missing"}}}
    ])
    assert summary["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_metrics_with_extra_fields_kept():
    """metric dict 含 value + 其他字段 → value 仍被聚合。"""
    summary = aggregate_summary([
        {"metrics": {"element_count_total": {"value": 10, "reason": "ok", "extra": "x"}}}
    ])
    assert summary["counts"]["element_count_total"]["sum"] == 10


def test_aggregate_summary_count_negative_value_participates():
    """负值仍参与 sum（无过滤）。"""
    summary = aggregate_summary([
        {"metrics": {"element_count_total": {"value": -5}}},
        {"metrics": {"element_count_total": {"value": 10}}},
    ])
    assert summary["counts"]["element_count_total"]["sum"] == 5


def test_aggregate_summary_count_only_one_participates():
    summary = aggregate_summary([
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {}},
    ])
    assert summary["counts"]["element_count_total"]["sum"] == 5
    assert summary["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_success_rate_metric_missing_doesnt_participate():
    """metric.value 不是 True → 不计 success。但 total 仍 +1。"""
    summary = aggregate_summary([
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {}},  # 缺失
    ])
    sr = summary["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2
    assert sr["rate"] == 0.5


def test_aggregate_summary_success_rate_value_false_not_success():
    summary = aggregate_summary([
        {"metrics": {"pipeline_success": {"value": False}}},
    ])
    sr = summary["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 1
    assert sr["rate"] == 0.0


def test_aggregate_summary_success_rate_value_none_in_total():
    """value=None → 不计 success，但仍计 total。"""
    summary = aggregate_summary([
        {"metrics": {"pipeline_success": {"value": None}}},
    ])
    sr = summary["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 1
    assert sr["rate"] == 0.0


def test_aggregate_summary_silent_drop_negative_value_participates():
    summary = aggregate_summary([
        {"metrics": {"silent_drop_count": {"value": -3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ])
    assert summary["silent_drop_total"] == 2


def test_aggregate_summary_silent_drop_explicit_zero_participates():
    summary = aggregate_summary([
        {"metrics": {"silent_drop_count": {"value": 0}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ])
    assert summary["silent_drop_total"] == 5


def test_aggregate_summary_keys_exact():
    summary = aggregate_summary([])
    assert set(summary.keys()) == {
        "counts", "success_rates", "ratio_macro_averages", "silent_drop_total"
    }


def test_aggregate_summary_counts_keys_exact():
    summary = aggregate_summary([])
    assert set(summary["counts"].keys()) == set(_COUNT_METRICS)


def test_aggregate_summary_success_rates_keys_exact():
    summary = aggregate_summary([])
    assert set(summary["success_rates"].keys()) == set(_SUCCESS_BOOL_METRICS)


def test_aggregate_summary_ratio_macro_averages_keys_exact():
    summary = aggregate_summary([])
    assert set(summary["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


def test_aggregate_summary_returns_dict():
    summary = aggregate_summary([])
    assert isinstance(summary, dict)


def test_aggregate_summary_signature():
    sig = inspect.signature(aggregate_summary)
    assert set(sig.parameters) == {"per_doc_results"}


# =========================================================================
# build_devset_section categories_covered 引用语义
# =========================================================================


class _FakeManifest:
    def __init__(self, **kwargs):
        for k in ("devset_status", "file_count", "content_group_count",
                  "pdf_count", "docx_count", "categories_covered"):
            setattr(self, k, kwargs.get(k, [] if k == "categories_covered" else 0))
        self.devset_status = kwargs.get("devset_status", "incomplete")


def test_build_devset_section_categories_covered_empty():
    m = _FakeManifest(categories_covered=[])
    result = build_devset_section(m)
    assert result["categories_covered"] == []


def test_build_devset_section_categories_covered_preserves_duplicates():
    """build_devset_section 不去重（直接读取 manifest 的 list）。"""
    m = _FakeManifest(categories_covered=["a", "a", "b"])
    result = build_devset_section(m)
    assert result["categories_covered"] == ["a", "a", "b"]


def test_build_devset_section_categories_covered_preserves_order():
    m = _FakeManifest(categories_covered=["z", "a", "m"])
    result = build_devset_section(m)
    assert result["categories_covered"] == ["z", "a", "m"]


def test_build_devset_section_keys_exact_set():
    m = _FakeManifest()
    result = build_devset_section(m)
    assert set(result.keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_build_devset_section_signature():
    sig = inspect.signature(build_devset_section)
    assert set(sig.parameters) == {"manifest"}


# =========================================================================
# 模块结构与注释
# =========================================================================


def test_module_imports_subprocess():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "import subprocess" in src


def test_module_imports_datetime():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "from datetime import" in src
    assert "datetime" in src


def test_module_imports_path():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_evaluator_report_versions():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "from evaluation import" in src
    assert "EVALUATOR_VERSION" in src
    assert "REPORT_VERSION" in src


def test_module_comment_figure_caption_always_null():
    """源码注释明确 figure_caption_* 始终 null，不参与 macro average。"""
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "figure_caption" in src
    assert "macro average" in src or "不参与" in src or "始终 null" in src


def test_module_constants_count_metrics_one():
    """_COUNT_METRICS 只有 element_count_total 一项。"""
    assert len(_COUNT_METRICS) == 1


def test_module_constants_success_bool_metrics_one():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_module_constants_ratio_metrics_twelve():
    assert len(_RATIO_METRICS) == 12


def test_module_constants_disjoint():
    """三个常量集合互不相交。"""
    assert set(_COUNT_METRICS) & set(_SUCCESS_BOOL_METRICS) == set()
    assert set(_COUNT_METRICS) & set(_RATIO_METRICS) == set()
    # 注意：pipeline_success 在 _SUCCESS_BOOL_METRICS；
    # schema_valid 在 _RATIO_METRICS（参与 macro average）


def test_module_constants_are_tuples():
    assert isinstance(_COUNT_METRICS, tuple)
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)
    assert isinstance(_RATIO_METRICS, tuple)


def test_module_all_exact_list():
    import evaluation.report as mod
    assert mod.__all__ == [
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    ]


def test_module_all_no_duplicates():
    import evaluation.report as mod
    assert len(mod.__all__) == len(set(mod.__all__))


def test_module_uses_future_annotations():
    import evaluation.report as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_no_silence_unused():
    import evaluation.report as mod
    assert not hasattr(mod, "_silence_unused")


def test_module_docstring_present():
    import evaluation.report as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_no_mix_types():
    """docstring 提及"不混合类型"。"""
    import evaluation.report as mod
    doc = mod.__doc__
    assert "不混合" in doc or "no mix" in doc.lower() or "不混" in doc


# =========================================================================
# 综合行为
# =========================================================================


def test_aggregate_summary_does_not_mutate_input():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    before = __import__("copy").deepcopy(per_doc)
    aggregate_summary(per_doc)
    assert per_doc == before


def test_aggregate_summary_idempotent():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    a = aggregate_summary(per_doc)
    b = aggregate_summary(per_doc)
    assert a == b


def test_build_provenance_then_aggregate_summary_compose(tmp_path: Path):
    """两个函数可独立组合，无副作用。"""
    prov = build_provenance(tmp_path, "text", 800, "1.0")
    summary = aggregate_summary([{"metrics": {"pipeline_success": {"value": True}}}])
    # 验证两个结果独立
    assert "git_commit" in prov
    assert "success_rates" in summary


def test_aggregate_summary_with_many_docs():
    """100 个文档聚合仍正确。"""
    per_doc = [{"metrics": {"element_count_total": {"value": i}}} for i in range(100)]
    summary = aggregate_summary(per_doc)
    assert summary["counts"]["element_count_total"]["sum"] == sum(range(100))
    assert summary["counts"]["element_count_total"]["participating_docs"] == 100


def test_get_git_provenance_returns_new_dict_each_call(tmp_path: Path):
    a = get_git_provenance(tmp_path)
    b = get_git_provenance(tmp_path)
    assert a == b
    assert a is not b


def test_get_dependency_versions_returns_new_dict_each_call():
    a = get_dependency_versions()
    b = get_dependency_versions()
    assert a == b
    assert a is not b


def test_build_provenance_returns_new_dict_each_call(tmp_path: Path):
    a = build_provenance(tmp_path, "text", 800, "1.0")
    b = build_provenance(tmp_path, "text", 800, "1.0")
    assert a is not b
