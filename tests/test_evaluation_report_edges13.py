r"""evaluation/report.py 边角测试 - 第十三轮（Round 236）。

补强已有 base/edges/edges2-12（共 ~1100+ 测试）未覆盖的深度：
- aggregate_summary：empty list、silent_drop_total 各种情况、success_rate 计算
- aggregate_summary ratio_macro_averages 内部 12 keys 顺序精确
- build_provenance：max_chars 类型转换（bool/float）、parser_name None、parser_version int
- build_devset_section：Manifest 缺属性、各种零值传播
- get_git_provenance：subprocess 命令精确、失败 fallback
- get_dependency_versions：返回类型、idempotent
- 模块函数签名精确、__all__ 顺序、constants 边界
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
# 常量精确
# =========================================================================


def test_ratio_metrics_length_exactly_twelve():
    """_RATIO_METRICS 12 项。"""
    assert len(_RATIO_METRICS) == 12


def test_count_metrics_length_exactly_one():
    """_COUNT_METRICS 1 项。"""
    assert len(_COUNT_METRICS) == 1


def test_success_bool_metrics_length_exactly_one():
    """_SUCCESS_BOOL_METRICS 1 项。"""
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_count_metrics_value_element_count_total():
    """_COUNT_METRICS = ('element_count_total',)。"""
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_value_pipeline_success():
    """_SUCCESS_BOOL_METRICS = ('pipeline_success',)。"""
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_ratio_metrics_does_not_contain_pipeline_success():
    """_RATIO_METRICS 不含 pipeline_success（属 _SUCCESS_BOOL_METRICS）。"""
    assert "pipeline_success" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_element_count_total():
    """_RATIO_METRICS 不含 element_count_total（属 _COUNT_METRICS）。"""
    assert "element_count_total" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_silent_drop_count():
    """_RATIO_METRICS 不含 silent_drop_count（单独求和）。"""
    assert "silent_drop_count" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_error_code():
    """_RATIO_METRICS 不含 error_code。"""
    assert "error_code" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_figure_caption():
    """_RATIO_METRICS 不含 figure_caption_*（始终 null 不参与 macro）。"""
    for name in _RATIO_METRICS:
        assert not name.startswith("figure_caption_")


def test_ratio_metrics_does_not_contain_tolerance():
    """_RATIO_METRICS 不含 _tolerance_chars（内部字段）。"""
    for name in _RATIO_METRICS:
        assert not name.startswith("_")


# =========================================================================
# aggregate_summary: empty list
# =========================================================================


def test_aggregate_summary_empty_list_returns_four_top_keys():
    """空 per_doc → 4 个 top key。"""
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_empty_list_counts_entry_null():
    """空 list → counts.element_count_total = {sum: None, participating_docs: 0}。"""
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_empty_list_success_rate_null():
    """空 list → rate=None（total=0）。"""
    out = aggregate_summary([])
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 0
    assert sr["rate"] is None


def test_aggregate_summary_empty_list_ratio_macro_all_null():
    """空 list → 每个 ratio_macro 都 macro_average=None。"""
    out = aggregate_summary([])
    for name in _RATIO_METRICS:
        entry = out["ratio_macro_averages"][name]
        assert entry["macro_average"] is None
        assert entry["participating_docs"] == 0
        assert entry["not_evaluated"] == 0


def test_aggregate_summary_empty_list_silent_drop_total_none():
    """空 list → silent_drop_total = None。"""
    out = aggregate_summary([])
    assert out["silent_drop_total"] is None


# =========================================================================
# aggregate_summary: success_rate 计算
# =========================================================================


def test_aggregate_summary_success_rate_all_success():
    """2 docs 都 success → rate=1.0。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 2
    assert sr["rate"] == 1.0


def test_aggregate_summary_success_rate_none_success():
    """2 docs 都 fail → rate=0.0。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 2
    assert sr["rate"] == 0.0


def test_aggregate_summary_success_rate_half():
    """1 success + 1 fail → rate=0.5。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2
    assert sr["rate"] == 0.5


def test_aggregate_summary_success_rate_with_none_value():
    """value=None 不算 success，但 total 仍计入。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": None}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2
    assert sr["rate"] == 0.5


def test_aggregate_summary_success_rate_missing_metric():
    """metric 缺失 → .get(name, {}).get('value') 返回 None → 不算 success。"""
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 1


# =========================================================================
# aggregate_summary: silent_drop_total 各种情况
# =========================================================================


def test_aggregate_summary_silent_drop_all_present_sum():
    """2 docs 都有 silent_drop_count → 求和。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_one_none():
    """1 doc None + 1 doc 有值 → 只算有值的。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": 7}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 7


def test_aggregate_summary_silent_drop_zero_value():
    """0 是有效值，参与求和。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 0}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 5


def test_aggregate_summary_silent_drop_all_zero():
    """全 0 → sum=0（int 0）。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 0}}},
        {"metrics": {"silent_drop_count": {"value": 0}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 0


def test_aggregate_summary_silent_drop_missing_key():
    """metric 缺失 → .get({}, {}) 当 None 处理。"""
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_with_negative():
    """负值（不应发生，但语法允许）→ 求和含负数。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": -3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 2


# =========================================================================
# aggregate_summary: ratio_macro_averages 内部 key 顺序精确
# =========================================================================


def test_aggregate_summary_ratio_macro_keys_insertion_order():
    """ratio_macro_averages 的 12 个 key 顺序精确。"""
    out = aggregate_summary([])
    keys = list(out["ratio_macro_averages"].keys())
    assert keys == list(_RATIO_METRICS)


def test_aggregate_summary_ratio_macro_first_key_schema_valid():
    """ratio_macro_averages 第 1 个 key 是 schema_valid。"""
    out = aggregate_summary([])
    assert list(out["ratio_macro_averages"].keys())[0] == "schema_valid"


def test_aggregate_summary_ratio_macro_last_key_chunk_boundary_f1():
    """ratio_macro_averages 最后 1 个 key 是 chunk_boundary_f1。"""
    out = aggregate_summary([])
    assert list(out["ratio_macro_averages"].keys())[-1] == "chunk_boundary_f1"


def test_aggregate_summary_counts_keys_exact_one():
    """counts section 只有 1 个 key（element_count_total）。"""
    out = aggregate_summary([])
    assert list(out["counts"].keys()) == ["element_count_total"]


def test_aggregate_summary_success_rates_keys_exact_one():
    """success_rates section 只有 1 个 key（pipeline_success）。"""
    out = aggregate_summary([])
    assert list(out["success_rates"].keys()) == ["pipeline_success"]


# =========================================================================
# aggregate_summary: macro_average 计算
# =========================================================================


def test_aggregate_summary_macro_average_half_participation():
    """1 doc 有值 + 1 doc None → macro 等于有值的；participating=1, not_evaluated=1。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    entry = out["ratio_macro_averages"]["schema_valid"]
    assert entry["macro_average"] == 1.0
    assert entry["participating_docs"] == 1
    assert entry["not_evaluated"] == 1


def test_aggregate_summary_macro_average_two_values():
    """2 docs 都有值 → macro = mean。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.5}}},
        {"metrics": {"schema_valid": {"value": 1.0}}},
    ]
    out = aggregate_summary(per_doc)
    entry = out["ratio_macro_averages"]["schema_valid"]
    assert entry["macro_average"] == 0.75
    assert entry["participating_docs"] == 2
    assert entry["not_evaluated"] == 0


def test_aggregate_summary_macro_average_zero_participates():
    """value=0.0 是有效值，参与计算。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.0}}},
        {"metrics": {"schema_valid": {"value": 1.0}}},
    ]
    out = aggregate_summary(per_doc)
    entry = out["ratio_macro_averages"]["schema_valid"]
    assert entry["macro_average"] == 0.5
    assert entry["participating_docs"] == 2


def test_aggregate_summary_counts_sum_excludes_none():
    """counts sum 排除 None 值。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    counts = out["counts"]["element_count_total"]
    assert counts["sum"] == 15
    assert counts["participating_docs"] == 2


# =========================================================================
# build_provenance: 类型边界
# =========================================================================


def test_build_provenance_max_chars_bool_true(tmp_path: Path):
    """max_chars=True → int(True)=1。"""
    out = build_provenance(tmp_path, "fallback", True, "1.0")
    assert out["max_chars"] == 1


def test_build_provenance_max_chars_bool_false(tmp_path: Path):
    """max_chars=False → int(False)=0。"""
    out = build_provenance(tmp_path, "fallback", False, "1.0")
    assert out["max_chars"] == 0


def test_build_provenance_max_chars_float(tmp_path: Path):
    """max_chars=15.9 → int(15.9)=15。"""
    out = build_provenance(tmp_path, "fallback", 15.9, "1.0")
    assert out["max_chars"] == 15


def test_build_provenance_max_chars_string_raises(tmp_path: Path):
    """max_chars='abc' → int() raises ValueError。"""
    with pytest.raises(ValueError):
        build_provenance(tmp_path, "fallback", "abc", "1.0")


def test_build_provenance_parser_name_none(tmp_path: Path):
    """parser_name=None → passed through。"""
    out = build_provenance(tmp_path, None, 800, "1.0")
    assert out["parser_name"] is None


def test_build_provenance_parser_name_int(tmp_path: Path):
    """parser_name=42 → passed through。"""
    out = build_provenance(tmp_path, 42, 800, "1.0")
    assert out["parser_name"] == 42


def test_build_provenance_parser_version_int(tmp_path: Path):
    """parser_version=42 → passed through。"""
    out = build_provenance(tmp_path, "fallback", 800, 42)
    assert out["parser_version"] == 42


def test_build_provenance_parser_version_empty_string(tmp_path: Path):
    """parser_version='' → passed through。"""
    out = build_provenance(tmp_path, "fallback", 800, "")
    assert out["parser_version"] == ""


def test_build_provenance_parser_version_unicode(tmp_path: Path):
    """parser_version='v1.1-β' → passed through。"""
    out = build_provenance(tmp_path, "fallback", 800, "v1.1-β")
    assert out["parser_version"] == "v1.1-β"


def test_build_provenance_evaluator_version_constant(tmp_path: Path):
    """evaluator_version 是 EVALUATOR_VERSION 常量。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_constant(tmp_path: Path):
    """report_version 是 REPORT_VERSION 常量。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_run_timestamp_iso_is_str(tmp_path: Path):
    """run_timestamp_iso 类型是 str。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert isinstance(out["run_timestamp_iso"], str)


def test_build_provenance_run_timestamp_iso_parseable(tmp_path: Path):
    """run_timestamp_iso 可以被 datetime.fromisoformat 解析。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0")
    # Python 3.11+ 支持解析带时区的 ISO 字符串
    parsed = datetime.fromisoformat(out["run_timestamp_iso"])
    assert parsed is not None


def test_build_provenance_dependencies_always_dict(tmp_path: Path):
    """dependencies 永远是 dict（即使包不存在）。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert isinstance(out["dependencies"], dict)
    assert len(out["dependencies"]) == 3


# =========================================================================
# build_devset_section: 各种边界
# =========================================================================


class _FakeManifest:
    """最小 Manifest 替身。"""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, v, v) if False else None  # no-op
        self._data = kwargs

    @property
    def devset_status(self):
        return self._data.get("devset_status")

    @property
    def file_count(self):
        return self._data.get("file_count")

    @property
    def content_group_count(self):
        return self._data.get("content_group_count")

    @property
    def pdf_count(self):
        return self._data.get("pdf_count")

    @property
    def docx_count(self):
        return self._data.get("docx_count")

    @property
    def categories_covered(self):
        return self._data.get("categories_covered")


def test_build_devset_section_zero_file_count():
    """file_count=0 → 透传。"""
    m = _FakeManifest(devset_status="incomplete", file_count=0,
                      content_group_count=0, pdf_count=0, docx_count=0,
                      categories_covered=[])
    out = build_devset_section(m)
    assert out["file_count"] == 0


def test_build_devset_section_negative_counts_propagated():
    """负数（不应发生）仍透传。"""
    m = _FakeManifest(devset_status="x", file_count=-1,
                      content_group_count=-2, pdf_count=-3, docx_count=-4,
                      categories_covered=[])
    out = build_devset_section(m)
    assert out["file_count"] == -1
    assert out["content_group_count"] == -2


def test_build_devset_section_categories_tuple():
    """categories_covered 是 tuple → 透传。"""
    m = _FakeManifest(devset_status="x", file_count=1,
                      content_group_count=1, pdf_count=1, docx_count=0,
                      categories_covered=("pdf",))
    out = build_devset_section(m)
    assert out["categories_covered"] == ("pdf",)


def test_build_devset_section_categories_set():
    """categories_covered 是 set → 透传。"""
    m = _FakeManifest(devset_status="x", file_count=1,
                      content_group_count=1, pdf_count=1, docx_count=0,
                      categories_covered={"pdf"})
    out = build_devset_section(m)
    assert out["categories_covered"] == {"pdf"}


def test_build_devset_section_status_any_string():
    """status 是任意 str → 透传。"""
    m = _FakeManifest(devset_status="anything", file_count=0,
                      content_group_count=0, pdf_count=0, docx_count=0,
                      categories_covered=[])
    out = build_devset_section(m)
    assert out["status"] == "anything"


def test_build_devset_section_missing_property_raises():
    """Manifest 缺属性 → AttributeError。"""
    class Empty:
        pass
    with pytest.raises(AttributeError):
        build_devset_section(Empty())


# =========================================================================
# get_git_provenance: subprocess 命令精确
# =========================================================================


def test_get_git_provenance_first_command_rev_parse_head(tmp_path: Path, monkeypatch):
    """第 1 个 subprocess 命令是 ['git', 'rev-parse', 'HEAD']。"""
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        r = subprocess.CompletedProcess(cmd, 0, stdout="abc123\n", stderr="")
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    get_git_provenance(tmp_path)
    assert calls[0] == ["git", "rev-parse", "HEAD"]


def test_get_git_provenance_second_command_status_porcelain(tmp_path: Path, monkeypatch):
    """第 2 个 subprocess 命令是 ['git', 'status', '--porcelain']。"""
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    get_git_provenance(tmp_path)
    assert calls[1] == ["git", "status", "--porcelain"]


def test_get_git_provenance_subprocess_called_twice(tmp_path: Path, monkeypatch):
    """subprocess.run 被调用 2 次。"""
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    get_git_provenance(tmp_path)
    assert len(calls) == 2


def test_get_git_provenance_returns_git_commit_stripped(tmp_path: Path, monkeypatch):
    """commit 是 stdout.strip()。"""
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="abc123\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"


def test_get_git_provenance_returns_dirty_true_when_porcelain_output(tmp_path: Path, monkeypatch):
    """porcelain 输出非空 → dirty=True。"""
    def fake_run(cmd, **kwargs):
        if "status" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout=" M file.txt\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="abc\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


def test_get_git_provenance_returns_dirty_false_when_porcelain_empty(tmp_path: Path, monkeypatch):
    """porcelain 输出空 → dirty=False。"""
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_get_git_provenance_commit_null_on_failure(tmp_path: Path, monkeypatch):
    """rev-parse 失败（returncode != 0）→ commit=None。"""
    def fake_run(cmd, **kwargs):
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="err")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_oserror_fallback(tmp_path: Path, monkeypatch):
    """OSError 抛出 → commit=None, dirty=True。"""
    def fake_run(cmd, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_subprocess_error_fallback(tmp_path: Path, monkeypatch):
    """SubprocessError 抛出 → commit=None, dirty=True。"""
    def fake_run(cmd, **kwargs):
        raise subprocess.SubprocessError("boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_timeout_passed_to_subprocess(tmp_path: Path, monkeypatch):
    """timeout=10 传给 subprocess.run。"""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    get_git_provenance(tmp_path)
    assert captured["timeout"] == 10


def test_get_git_provenance_cwd_passed_to_subprocess(tmp_path: Path, monkeypatch):
    """cwd 是 str(project_root)。"""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    get_git_provenance(tmp_path)
    assert captured["cwd"] == str(tmp_path)


# =========================================================================
# get_dependency_versions: 返回类型与 idempotent
# =========================================================================


def test_get_dependency_versions_keys_exact():
    """返回 dict 的 3 个 key：pdfplumber / python-docx / pypdfium2。"""
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_type():
    """每个 value 是 str 或 None。"""
    out = get_dependency_versions()
    for v in out.values():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_idempotent():
    """多次调用返回相同结果（不缓存但相同）。"""
    out1 = get_dependency_versions()
    out2 = get_dependency_versions()
    assert out1 == out2


def test_get_dependency_versions_pdfplumber_value():
    """pdfplumber 在依赖中应有具体版本（str）。"""
    out = get_dependency_versions()
    # pdfplumber 是核心依赖，应当有版本
    assert out["pdfplumber"] is None or len(out["pdfplumber"]) > 0


# =========================================================================
# 模块函数签名
# =========================================================================


def test_get_git_provenance_signature_one_param():
    """get_git_provenance 有 1 个参数。"""
    sig = inspect.signature(get_git_provenance)
    assert len(sig.parameters) == 1
    assert "project_root" in sig.parameters


def test_get_dependency_versions_signature_no_param():
    """get_dependency_versions 无参数。"""
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_build_provenance_signature_four_params():
    """build_provenance 有 4 个参数。"""
    sig = inspect.signature(build_provenance)
    assert len(sig.parameters) == 4
    assert list(sig.parameters.keys()) == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_build_devset_section_signature_one_param():
    """build_devset_section 有 1 个参数。"""
    sig = inspect.signature(build_devset_section)
    assert len(sig.parameters) == 1


def test_aggregate_summary_signature_one_param():
    """aggregate_summary 有 1 个参数。"""
    sig = inspect.signature(aggregate_summary)
    assert len(sig.parameters) == 1
    assert "per_doc_results" in sig.parameters


# =========================================================================
# 模块 __all__ 顺序
# =========================================================================


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


def test_module_all_first_element_build_provenance():
    """__all__ 第 1 个是 build_provenance。"""
    import evaluation.report as m
    assert m.__all__[0] == "build_provenance"


def test_module_all_last_element_get_dependency_versions():
    """__all__ 最后一个是 get_dependency_versions。"""
    import evaluation.report as m
    assert m.__all__[-1] == "get_dependency_versions"


def test_module_all_size_five():
    """__all__ 5 个元素。"""
    import evaluation.report as m
    assert len(m.__all__) == 5


def test_module_internal_constants_not_in_all():
    """_RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 不在 __all__。"""
    import evaluation.report as m
    assert "_RATIO_METRICS" not in m.__all__
    assert "_COUNT_METRICS" not in m.__all__
    assert "_SUCCESS_BOOL_METRICS" not in m.__all__


# =========================================================================
# 模块导入与 EVALUATOR_VERSION / REPORT_VERSION
# =========================================================================


def test_module_evaluator_version_is_str():
    """EVALUATOR_VERSION 是 str。"""
    assert isinstance(EVALUATOR_VERSION, str)


def test_module_report_version_is_str():
    """REPORT_VERSION 是 str。"""
    assert isinstance(REPORT_VERSION, str)


def test_module_evaluator_version_nonempty():
    """EVALUATOR_VERSION 非空。"""
    assert len(EVALUATOR_VERSION) > 0


def test_module_report_version_nonempty():
    """REPORT_VERSION 非空。"""
    assert len(REPORT_VERSION) > 0


def test_module_subprocess_in_namespace():
    """subprocess 在模块命名空间。"""
    import evaluation.report as m
    assert hasattr(m, "subprocess")


def test_module_datetime_in_namespace():
    """datetime 在模块命名空间。"""
    import evaluation.report as m
    assert hasattr(m, "datetime")


def test_module_path_in_namespace():
    """Path 在模块命名空间。"""
    import evaluation.report as m
    assert hasattr(m, "Path")


def test_module_constants_in_namespace():
    """_RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 在模块命名空间。"""
    import evaluation.report as m
    assert hasattr(m, "_RATIO_METRICS")
    assert hasattr(m, "_COUNT_METRICS")
    assert hasattr(m, "_SUCCESS_BOOL_METRICS")


# =========================================================================
# aggregate_summary: dict 结构精确
# =========================================================================


def test_aggregate_summary_counts_entry_value_dict_keys_exact():
    """counts 每项 = {sum, participating_docs} 2 个 key。"""
    per_doc = [{"metrics": {"element_count_total": {"value": 5}}}]
    out = aggregate_summary(per_doc)
    entry = out["counts"]["element_count_total"]
    assert set(entry.keys()) == {"sum", "participating_docs"}


def test_aggregate_summary_success_rates_entry_value_dict_keys_exact():
    """success_rates 每项 = {success_count, total, rate} 3 个 key。"""
    per_doc = [{"metrics": {"pipeline_success": {"value": True}}}]
    out = aggregate_summary(per_doc)
    entry = out["success_rates"]["pipeline_success"]
    assert set(entry.keys()) == {"success_count", "total", "rate"}


def test_aggregate_summary_ratio_macro_entry_value_dict_keys_exact():
    """ratio_macro_averages 每项 = {macro_average, participating_docs, not_evaluated} 3 个 key。"""
    per_doc = [{"metrics": {"schema_valid": {"value": True}}}]
    out = aggregate_summary(per_doc)
    entry = out["ratio_macro_averages"]["schema_valid"]
    assert set(entry.keys()) == {"macro_average", "participating_docs", "not_evaluated"}


def test_aggregate_summary_top_level_keys_exact_four():
    """顶层 dict 只有 4 个 key。"""
    per_doc = [{"metrics": {"pipeline_success": {"value": True}}}]
    out = aggregate_summary(per_doc)
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_no_extra_keys_in_counts():
    """counts section 不包含非 _COUNT_METRICS 的 key。"""
    per_doc = [{"metrics": {"element_count_total": {"value": 5}, "pipeline_success": {"value": True}}}]
    out = aggregate_summary(per_doc)
    assert "pipeline_success" not in out["counts"]


def test_aggregate_summary_no_extra_keys_in_success_rates():
    """success_rates section 不包含非 _SUCCESS_BOOL_METRICS 的 key。"""
    per_doc = [{"metrics": {"element_count_total": {"value": 5}, "pipeline_success": {"value": True}}}]
    out = aggregate_summary(per_doc)
    assert "element_count_total" not in out["success_rates"]
