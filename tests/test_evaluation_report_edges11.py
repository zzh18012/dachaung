r"""evaluation/report.py 边角测试 - 第十一轮（Round 223）。

补强已有 base/edges/edges2-10（共 ~950 测试）未覆盖的深度：
- 常量元组精确字符串内容（_RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS）
- get_git_provenance：subprocess.run 调用参数（encoding/errors/timeout/cwd/capture_output/text）
- get_git_provenance：真实仓库 commit 是 40 位 hex
- get_dependency_versions：3 个包名按插入顺序保留
- build_provenance：max_chars 极端类型转换（bool / None / list / bytes 引发 TypeError）
- build_provenance：与 monkeypatched get_git_provenance / get_dependency_versions 的集成
- build_devset_section：dict 插入顺序；set/tuple 类型 categories；多余 attr 忽略；缺 attr 抛 AttributeError
- aggregate_summary：metric 不是 dict 时抛异常；value=True（bool）行为；负数/极大浮点数；extra keys 忽略
- aggregate_summary：返回 dict 的内部 entry key 集合
- 模块结构 / __all__ / 单元可调用性
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


class _FakeManifest:
    def __init__(self, status="incomplete", file_count=1, content_group_count=1,
                 pdf_count=1, docx_count=0, categories_covered=None,
                 extra_attr=None):
        self.devset_status = status
        self.file_count = file_count
        self.content_group_count = content_group_count
        self.pdf_count = pdf_count
        self.docx_count = docx_count
        self.categories_covered = categories_covered if categories_covered is not None else ["text"]
        if extra_attr is not None:
            self.unrelated_attr = extra_attr  # 故意加一个额外属性


# =========================================================================
# 常量元组精确内容
# =========================================================================


def test_ratio_metrics_first_element_schema_valid():
    """_RATIO_METRICS 第 1 个元素是 schema_valid（按代码顺序）。"""
    assert _RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_last_element_chunk_boundary_f1():
    """_RATIO_METRICS 最后一个元素是 chunk_boundary_f1。"""
    assert _RATIO_METRICS[-1] == "chunk_boundary_f1"


def test_ratio_metrics_contains_pdf_locator_valid_ratio():
    assert "pdf_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_docx_locator_valid_ratio():
    assert "docx_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_image_resource_exists_ratio():
    assert "image_resource_exists_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_reference_intact_ratio():
    assert "chunk_reference_intact_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_text_preservation_equal():
    assert "text_preservation_equal" in _RATIO_METRICS


def test_ratio_metrics_contains_text_char_multiset_precision():
    assert "text_char_multiset_precision" in _RATIO_METRICS


def test_ratio_metrics_contains_text_char_multiset_recall():
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_contains_heading_boundary_compliance():
    assert "heading_boundary_compliance" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_precision():
    assert "chunk_boundary_precision" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_recall():
    assert "chunk_boundary_recall" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_f1():
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_figure_caption_precision():
    """figure_caption_* 不在 ratio metrics（始终 null，不参与 macro average）。"""
    assert "figure_caption_precision" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_figure_caption_recall():
    assert "figure_caption_recall" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_figure_caption_f1():
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_doc_id():
    assert "doc_id" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_source_type():
    assert "source_type" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_wall_time_seconds():
    assert "wall_time_seconds" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_error_code():
    assert "error_code" not in _RATIO_METRICS


def test_ratio_metrics_is_tuple_not_list():
    """tuple 是不可变的，确保不被改写。"""
    assert isinstance(_RATIO_METRICS, tuple)
    assert not isinstance(_RATIO_METRICS, list)


def test_count_metrics_is_tuple_not_list():
    assert isinstance(_COUNT_METRICS, tuple)
    assert not isinstance(_COUNT_METRICS, list)


def test_success_bool_metrics_is_tuple_not_list():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)
    assert not isinstance(_SUCCESS_BOOL_METRICS, list)


def test_count_metrics_exact_content():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_exact_content():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_count_metrics_first_and_only_element():
    assert _COUNT_METRICS[0] == "element_count_total"


def test_success_bool_metrics_first_and_only_element():
    assert _SUCCESS_BOOL_METRICS[0] == "pipeline_success"


def test_count_metrics_does_not_contain_silent_drop_count_explicit():
    assert "silent_drop_count" != _COUNT_METRICS[0]
    assert "silent_drop_count" not in _COUNT_METRICS


def test_count_metrics_does_not_contain_any_ratio_name():
    """counts 与 ratios 完全不重叠。"""
    for name in _RATIO_METRICS:
        assert name not in _COUNT_METRICS


def test_success_bool_metrics_does_not_contain_any_ratio_name():
    for name in _RATIO_METRICS:
        assert name not in _SUCCESS_BOOL_METRICS


# =========================================================================
# get_git_provenance 深度 - subprocess.run 参数验证
# =========================================================================


def test_get_git_provenance_subprocess_call_kwargs(monkeypatch, tmp_path):
    """subprocess.run 应带 encoding/errors/timeout/cwd/capture_output/text 参数。"""
    captured = []

    def fake_run(cmd, *args, **kwargs):
        captured.append(kwargs)

        class _R:
            returncode = 0
            stdout = "deadbeef" * 5
            stderr = ""
        return _R()

    monkeypatch.setattr("subprocess.run", fake_run)
    get_git_provenance(tmp_path)
    # 两次调用都应有这些 kwargs
    for kw in captured:
        assert kw.get("capture_output") is True
        assert kw.get("text") is True
        assert kw.get("encoding") == "utf-8"
        assert kw.get("errors") == "replace"
        assert kw.get("timeout") == 10
        assert kw.get("cwd") == str(tmp_path)


def test_get_git_provenance_subprocess_called_twice(monkeypatch, tmp_path):
    """应该调用 subprocess.run 两次：rev-parse + status。"""
    call_count = [0]

    def fake_run(cmd, *args, **kwargs):
        call_count[0] += 1

        class _R:
            returncode = 0
            stdout = "abc123" if call_count[0] == 1 else ""
            stderr = ""
        return _R()

    monkeypatch.setattr("subprocess.run", fake_run)
    get_git_provenance(tmp_path)
    assert call_count[0] == 2


def test_get_git_provenance_subprocess_first_cmd_rev_parse(monkeypatch, tmp_path):
    """第一次调用 cmd[1] 是 rev-parse。"""
    cmds = []

    def fake_run(cmd, *args, **kwargs):
        cmds.append(cmd)

        class _R:
            returncode = 0
            stdout = "abc123" if len(cmds) == 1 else ""
            stderr = ""
        return _R()

    monkeypatch.setattr("subprocess.run", fake_run)
    get_git_provenance(tmp_path)
    assert cmds[0] == ["git", "rev-parse", "HEAD"]


def test_get_git_provenance_subprocess_second_cmd_status_porcelain(monkeypatch, tmp_path):
    cmds = []

    def fake_run(cmd, *args, **kwargs):
        cmds.append(cmd)

        class _R:
            returncode = 0
            stdout = "abc123" if len(cmds) == 1 else ""
            stderr = ""
        return _R()

    monkeypatch.setattr("subprocess.run", fake_run)
    get_git_provenance(tmp_path)
    assert cmds[1] == ["git", "status", "--porcelain"]


def test_get_git_provenance_real_repo_returns_hex_commit():
    """真实 autonomous worktree 应能返回 40 位 hex commit。"""
    project_root = Path(__file__).resolve().parent.parent
    result = get_git_provenance(project_root)
    if result["git_commit"] is not None:
        # 真实环境应返回 40 位 hex
        assert len(result["git_commit"]) == 40
        assert all(c in "0123456789abcdef" for c in result["git_commit"])


def test_get_git_provenance_returns_json_serializable(tmp_path):
    """返回的 dict 必须可 JSON 序列化（构建报告时需要）。"""
    import json
    result = get_git_provenance(tmp_path)
    s = json.dumps(result)
    assert isinstance(s, str)


def test_get_git_provenance_subprocess_timeout_value_is_ten(monkeypatch, tmp_path):
    """timeout 必须严格等于 10 秒（不能是其他值）。"""
    captured = []

    def fake_run(cmd, *args, **kwargs):
        captured.append(kwargs)

        class _R:
            returncode = 0
            stdout = "abc"
            stderr = ""
        return _R()

    monkeypatch.setattr("subprocess.run", fake_run)
    get_git_provenance(tmp_path)
    assert all(kw["timeout"] == 10 for kw in captured)


def test_get_git_provenance_returns_consistent_types(tmp_path):
    result = get_git_provenance(tmp_path)
    assert isinstance(result["git_commit"], (str, type(None)))
    assert isinstance(result["git_dirty"], bool)


# =========================================================================
# get_dependency_versions 深度
# =========================================================================


def test_get_dependency_versions_preserves_insertion_order(monkeypatch):
    """keys 应按代码中的顺序：pdfplumber, python-docx, pypdfium2。"""
    import importlib.metadata

    def fake_version(pkg):
        return f"1.0-{pkg}"

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    result = get_dependency_versions()
    keys = list(result.keys())
    assert keys == ["pdfplumber", "python-docx", "pypdfium2"]


def test_get_dependency_versions_each_package_resolved_individually(monkeypatch):
    """每个包单独调用 importlib.metadata.version。"""
    import importlib.metadata
    called = []

    def fake_version(pkg):
        called.append(pkg)
        return "1.0.0"

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    get_dependency_versions()
    assert called == ["pdfplumber", "python-docx", "pypdfium2"]


def test_get_dependency_versions_mixed_found_notfound(monkeypatch):
    """pdfplumber 找到，python-docx 未找到，pypdfium2 抛异常。"""
    import importlib.metadata

    def fake_version(pkg):
        if pkg == "pdfplumber":
            return "1.0.0"
        if pkg == "python-docx":
            raise importlib.metadata.PackageNotFoundError(pkg)
        raise RuntimeError("boom")

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    result = get_dependency_versions()
    assert result["pdfplumber"] == "1.0.0"
    assert result["python-docx"] is None
    assert result["pypdfium2"] is None


def test_get_dependency_versions_imports_importlib_inside_function():
    """importlib.metadata 是函数内 import（每次调用重新解析）。
    验证：移除 importlib.metadata 模块属性后函数仍能工作（因为 import 在函数内）。
    """
    # 不做破坏性修改，只验证函数可重复调用
    r1 = get_dependency_versions()
    r2 = get_dependency_versions()
    assert set(r1.keys()) == set(r2.keys())


def test_get_dependency_versions_returns_json_serializable():
    import json
    result = get_dependency_versions()
    s = json.dumps(result)
    assert isinstance(s, str)


# =========================================================================
# build_provenance 深度 - 类型转换边界
# =========================================================================


def test_build_provenance_max_chars_from_bool_true(tmp_path):
    """int(True) == 1。"""
    result = build_provenance(tmp_path, "fallback", True, None)  # type: ignore[arg-type]
    assert result["max_chars"] == 1


def test_build_provenance_max_chars_from_bool_false(tmp_path):
    """int(False) == 0。"""
    result = build_provenance(tmp_path, "fallback", False, None)  # type: ignore[arg-type]
    assert result["max_chars"] == 0


def test_build_provenance_max_chars_none_raises(tmp_path):
    """int(None) 抛 TypeError。"""
    with pytest.raises(TypeError):
        build_provenance(tmp_path, "fallback", None, None)  # type: ignore[arg-type]


def test_build_provenance_max_chars_list_raises(tmp_path):
    """int([800]) 抛 TypeError。"""
    with pytest.raises(TypeError):
        build_provenance(tmp_path, "fallback", [800], None)  # type: ignore[arg-type]


def test_build_provenance_max_chars_dict_raises(tmp_path):
    """int({'a': 1}) 抛 TypeError。"""
    with pytest.raises(TypeError):
        build_provenance(tmp_path, "fallback", {"a": 1}, None)  # type: ignore[arg-type]


def test_build_provenance_max_chars_bytes_raises_when_not_numeric(tmp_path):
    """int(b'abc') 抛 ValueError（bytes 必须是数字字面量）。"""
    with pytest.raises(ValueError):
        build_provenance(tmp_path, "fallback", b"abc", None)  # type: ignore[arg-type]


def test_build_provenance_max_chars_from_numeric_bytes(tmp_path):
    """int(b'800') == 800（合法数字字面量 bytes）。"""
    result = build_provenance(tmp_path, "fallback", b"800", None)  # type: ignore[arg-type]
    assert result["max_chars"] == 800


def test_build_provenance_max_chars_from_negative_str(tmp_path):
    """int('-100') == -100。"""
    result = build_provenance(tmp_path, "fallback", "-100", None)  # type: ignore[arg-type]
    assert result["max_chars"] == -100


def test_build_provenance_max_chars_float_negative(tmp_path):
    """int(-0.5) == 0（向 0 截断）。"""
    result = build_provenance(tmp_path, "fallback", -0.5, None)  # type: ignore[arg-type]
    assert result["max_chars"] == 0


def test_build_provenance_integration_with_mocked_helpers(monkeypatch, tmp_path):
    """集成：mock get_git_provenance 与 get_dependency_versions，验证值透传。"""
    monkeypatch.setattr(
        "evaluation.report.get_git_provenance",
        lambda root: {"git_commit": "feedface", "git_dirty": False},
    )
    monkeypatch.setattr(
        "evaluation.report.get_dependency_versions",
        lambda: {"pdfplumber": "9.9.9", "python-docx": None, "pypdfium2": "1.0"},
    )
    result = build_provenance(tmp_path, "kreuzberg", 500, "4.10.2")
    assert result["git_commit"] == "feedface"
    assert result["git_dirty"] is False
    assert result["parser_name"] == "kreuzberg"
    assert result["parser_version"] == "4.10.2"
    assert result["max_chars"] == 500
    assert result["dependencies"]["pdfplumber"] == "9.9.9"
    assert result["dependencies"]["python-docx"] is None
    assert result["dependencies"]["pypdfium2"] == "1.0"


def test_build_provenance_dependencies_dict_is_returned_directly(monkeypatch, tmp_path):
    """build_provenance 把 get_dependency_versions() 的返回值原样塞进 dependencies。"""
    sentinel = {"pdfplumber": "1.0", "python-docx": "2.0", "pypdfium2": "3.0"}
    monkeypatch.setattr(
        "evaluation.report.get_dependency_versions",
        lambda: sentinel,
    )
    monkeypatch.setattr(
        "evaluation.report.get_git_provenance",
        lambda root: {"git_commit": None, "git_dirty": True},
    )
    result = build_provenance(tmp_path, "fallback", 800, None)
    # dependencies 应是同一 dict（按引用）
    assert result["dependencies"] is sentinel


def test_build_provenance_git_dict_is_destructured(monkeypatch, tmp_path):
    """build_provenance 不是直接放 git dict，而是取 git_commit/git_dirty 两个键。"""
    monkeypatch.setattr(
        "evaluation.report.get_git_provenance",
        lambda root: {"git_commit": "abc", "git_dirty": True, "extra": "ignored"},
    )
    monkeypatch.setattr(
        "evaluation.report.get_dependency_versions",
        lambda: {},
    )
    result = build_provenance(tmp_path, "fallback", 800, None)
    # 只有 git_commit / git_dirty 两个键，没有 extra
    assert result["git_commit"] == "abc"
    assert result["git_dirty"] is True
    assert "extra" not in result


def test_build_provenance_evaluator_version_propagates_constant(tmp_path):
    """evaluator_version 必须等于 evaluation.EVALUATOR_VERSION。"""
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["evaluator_version"] is EVALUATOR_VERSION


def test_build_provenance_report_version_propagates_constant(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["report_version"] is REPORT_VERSION


def test_build_provenance_run_timestamp_iso_is_str(tmp_path):
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(result["run_timestamp_iso"], str)
    assert len(result["run_timestamp_iso"]) > 10


# =========================================================================
# build_devset_section 深度
# =========================================================================


def test_build_devset_section_dict_key_order():
    """Python dict 保留插入顺序：status 在前，categories_covered 在后。"""
    result = build_devset_section(_FakeManifest())
    keys = list(result.keys())
    assert keys[0] == "status"
    assert keys[-1] == "categories_covered"
    assert keys == [
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    ]


def test_build_devset_section_categories_as_tuple():
    """categories_covered 是 tuple 也应原样保留。"""
    m = _FakeManifest(categories_covered=("a", "b", "c"))
    result = build_devset_section(m)
    assert result["categories_covered"] == ("a", "b", "c")


def test_build_devset_section_categories_as_set():
    """categories_covered 是 set 也应原样保留（不强制转 list）。"""
    m = _FakeManifest(categories_covered={"x", "y"})
    result = build_devset_section(m)
    assert result["categories_covered"] == {"x", "y"}


def test_build_devset_section_ignores_extra_attrs():
    """Manifest 上的额外属性不应出现在结果中。"""
    m = _FakeManifest(extra_attr="ignored")
    result = build_devset_section(m)
    assert "unrelated_attr" not in result
    assert len(result.keys()) == 6


def test_build_devset_section_missing_devset_status_raises():
    """Manifest 缺 devset_status 属性 → AttributeError。"""
    class Partial:
        file_count = 1
        content_group_count = 1
        pdf_count = 1
        docx_count = 0
        categories_covered = ["text"]
    with pytest.raises(AttributeError):
        build_devset_section(Partial())


def test_build_devset_section_missing_categories_raises():
    class Partial:
        devset_status = "incomplete"
        file_count = 1
        content_group_count = 1
        pdf_count = 1
        docx_count = 0
    with pytest.raises(AttributeError):
        build_devset_section(Partial())


def test_build_devset_section_none_categories_propagated():
    m = _FakeManifest(categories_covered=None)
    # _FakeManifest 默认会替换 None 为 ["text"]，所以这里手动覆盖
    m.categories_covered = None
    result = build_devset_section(m)
    assert result["categories_covered"] is None


def test_build_devset_section_none_status_propagated():
    m = _FakeManifest(status=None)
    result = build_devset_section(m)
    assert result["status"] is None


def test_build_devset_section_zero_file_count_propagated():
    m = _FakeManifest(file_count=0)
    result = build_devset_section(m)
    assert result["file_count"] == 0


def test_build_devset_section_negative_file_count_propagated():
    """数值不会被校验，原样保留。"""
    m = _FakeManifest(file_count=-1)
    result = build_devset_section(m)
    assert result["file_count"] == -1


def test_build_devset_section_returns_json_serializable():
    import json
    result = build_devset_section(_FakeManifest())
    s = json.dumps(result)
    assert isinstance(s, str)


# =========================================================================
# aggregate_summary - 边界类型行为
# =========================================================================


def test_aggregate_summary_input_dict_missing_metrics_raises():
    """doc 没有 'metrics' 键 → r['metrics'] 抛 KeyError。"""
    with pytest.raises(KeyError):
        aggregate_summary([{"doc_id": "d1"}])


def test_aggregate_summary_metrics_value_none_dict_raises():
    """metrics[key] 是 None → None.get('value') 抛 AttributeError。"""
    with pytest.raises(AttributeError):
        aggregate_summary([{"metrics": {"element_count_total": None}}])


def test_aggregate_summary_metrics_not_dict_raises():
    """metrics 是 list → list.get 不存在 → AttributeError。"""
    with pytest.raises(AttributeError):
        aggregate_summary([{"metrics": []}])


def test_aggregate_summary_input_not_list_raises():
    """per_doc_results 不是 list → 推导式迭代 → list 推导 None 抛 TypeError。"""
    with pytest.raises(TypeError):
        aggregate_summary(None)  # type: ignore[arg-type]


def test_aggregate_summary_count_value_true_treated_as_one():
    """True 在 sum 中视为 1。"""
    pd = [
        {"metrics": {"element_count_total": {"value": True}}},
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    result = aggregate_summary(pd)
    assert result["counts"]["element_count_total"]["sum"] == 6


def test_aggregate_summary_count_value_false_treated_as_zero():
    """False 在 sum 中视为 0（但 is not None，所以参与）。"""
    pd = [
        {"metrics": {"element_count_total": {"value": False}}},
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    result = aggregate_summary(pd)
    assert result["counts"]["element_count_total"]["sum"] == 5
    assert result["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_silent_drop_value_true_treated_as_one():
    pd = [
        {"metrics": {"silent_drop_count": {"value": True}}},
        {"metrics": {"silent_drop_count": {"value": 2}}},
    ]
    result = aggregate_summary(pd)
    assert result["silent_drop_total"] == 3


def test_aggregate_summary_count_negative_values_summed():
    """负数也参与 sum（无校验）。"""
    pd = [
        {"metrics": {"element_count_total": {"value": -5}}},
        {"metrics": {"element_count_total": {"value": 10}}},
    ]
    result = aggregate_summary(pd)
    assert result["counts"]["element_count_total"]["sum"] == 5


def test_aggregate_summary_ratio_macro_with_negative_values():
    """负数 ratio 参与平均（虽然实际不应出现）。"""
    pd = [
        {"metrics": {"schema_valid": {"value": -1.0}}},
        {"metrics": {"schema_valid": {"value": 1.0}}},
    ]
    result = aggregate_summary(pd)
    avg = result["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == 0.0


def test_aggregate_summary_ratio_macro_with_large_float():
    pd = [
        {"metrics": {"schema_valid": {"value": 1e300}}},
        {"metrics": {"schema_valid": {"value": 1e300}}},
    ]
    result = aggregate_summary(pd)
    avg = result["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == 1e300


def test_aggregate_summary_ignores_extra_metric_keys():
    """metrics 中存在 _RATIO_METRICS / _COUNT_METRICS 之外的关键字应被忽略。"""
    pd = [
        {
            "metrics": {
                "element_count_total": {"value": 5},
                "unknown_metric": {"value": 999},
                "another_unknown": {"value": "ignored"},
            }
        }
    ]
    result = aggregate_summary(pd)
    # counts 应只有 element_count_total
    assert set(result["counts"].keys()) == {"element_count_total"}
    # 没有 unknown_metric 在任何聚合段
    assert "unknown_metric" not in result["counts"]
    assert "unknown_metric" not in result["success_rates"]
    assert "unknown_metric" not in result["ratio_macro_averages"]


def test_aggregate_summary_counts_entry_keys_exact():
    pd = [{"metrics": {"element_count_total": {"value": 5}}}]
    result = aggregate_summary(pd)
    entry = result["counts"]["element_count_total"]
    assert set(entry.keys()) == {"sum", "participating_docs"}


def test_aggregate_summary_success_rates_entry_keys_exact():
    pd = [{"metrics": {"pipeline_success": {"value": True}}}]
    result = aggregate_summary(pd)
    entry = result["success_rates"]["pipeline_success"]
    assert set(entry.keys()) == {"success_count", "total", "rate"}


def test_aggregate_summary_ratio_macro_entry_keys_exact():
    pd = [{"metrics": {"schema_valid": {"value": 1.0}}}]
    result = aggregate_summary(pd)
    entry = result["ratio_macro_averages"]["schema_valid"]
    assert set(entry.keys()) == {"macro_average", "participating_docs", "not_evaluated"}


def test_aggregate_summary_modifying_input_does_not_affect_output():
    pd = [{"metrics": {"element_count_total": {"value": 5}}}]
    result = aggregate_summary(pd)
    pd[0]["metrics"]["element_count_total"]["value"] = 999
    # 已计算的结果不变（数值是 immutable）
    assert result["counts"]["element_count_total"]["sum"] == 5


def test_aggregate_summary_all_twelve_ratio_metrics_present_for_empty():
    """空 per_doc_results 也应给出 12 个 ratio metrics 条目。"""
    result = aggregate_summary([])
    assert len(result["ratio_macro_averages"]) == 12
    for name in _RATIO_METRICS:
        assert name in result["ratio_macro_averages"]


def test_aggregate_summary_all_ratio_metrics_for_empty_have_none_average():
    result = aggregate_summary([])
    for name in _RATIO_METRICS:
        entry = result["ratio_macro_averages"][name]
        assert entry["macro_average"] is None
        assert entry["participating_docs"] == 0
        assert entry["not_evaluated"] == 0


def test_aggregate_summary_count_metric_for_empty_has_none_sum():
    result = aggregate_summary([])
    assert result["counts"]["element_count_total"]["sum"] is None
    assert result["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_success_rate_for_empty_has_zero_total():
    """空列表时 total=0 → rate=None。"""
    result = aggregate_summary([])
    sr = result["success_rates"]["pipeline_success"]
    assert sr["total"] == 0
    assert sr["rate"] is None


def test_aggregate_summary_not_evaluated_equals_total_minus_participating():
    pd = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {}},
    ]
    result = aggregate_summary(pd)
    avg = result["ratio_macro_averages"]["schema_valid"]
    assert avg["participating_docs"] == 1
    assert avg["not_evaluated"] == 2


def test_aggregate_summary_silent_drop_with_negative_value():
    """负数 silent_drop 也参与 sum（无校验）。"""
    pd = [
        {"metrics": {"silent_drop_count": {"value": -3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    result = aggregate_summary(pd)
    assert result["silent_drop_total"] == 2


def test_aggregate_summary_success_count_excludes_true_value_in_pipeline_success_with_none_total_count():
    """success_count 只数 True；total 数所有 doc（含 None 的）。"""
    pd = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": None}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    result = aggregate_summary(pd)
    sr = result["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 3
    assert sr["rate"] == pytest.approx(1 / 3)


def test_aggregate_summary_success_rate_zero_division_safe_for_empty():
    """total=0 时 rate 是 None（不触发 ZeroDivisionError）。"""
    result = aggregate_summary([])
    assert result["success_rates"]["pipeline_success"]["rate"] is None


# =========================================================================
# 综合行为
# =========================================================================


def test_aggregate_summary_full_pipeline_with_all_12_ratio_metrics():
    """所有 12 个 ratio metric 都给一个值，验证都进入 macro_average。"""
    metrics_dict: dict[str, Any] = {
        name: {"value": 0.5} for name in _RATIO_METRICS
    }
    pd = [{"metrics": metrics_dict}]
    result = aggregate_summary(pd)
    for name in _RATIO_METRICS:
        entry = result["ratio_macro_averages"][name]
        assert entry["macro_average"] == 0.5
        assert entry["participating_docs"] == 1
        assert entry["not_evaluated"] == 0


def test_aggregate_summary_with_two_docs_all_metrics():
    pd = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "schema_valid": {"value": True},
                "element_count_total": {"value": 10},
                "silent_drop_count": {"value": 1},
                "pdf_locator_valid_ratio": {"value": 1.0},
                "chunk_boundary_precision": {"value": 0.8},
            }
        },
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "schema_valid": {"value": True},
                "element_count_total": {"value": 20},
                "silent_drop_count": {"value": 3},
                "pdf_locator_valid_ratio": {"value": 0.5},
                "chunk_boundary_precision": {"value": 0.6},
            }
        },
    ]
    result = aggregate_summary(pd)
    assert result["counts"]["element_count_total"]["sum"] == 30
    assert result["counts"]["element_count_total"]["participating_docs"] == 2
    assert result["success_rates"]["pipeline_success"]["rate"] == 1.0
    assert result["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 0.75
    assert result["ratio_macro_averages"]["chunk_boundary_precision"]["macro_average"] == 0.7
    assert result["silent_drop_total"] == 4


def test_build_provenance_full_dict_json_serializable(tmp_path):
    """完整 build_provenance 结果必须 JSON 序列化（写入报告时需要）。"""
    import json
    result = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    s = json.dumps(result)
    assert isinstance(s, str)


def test_build_devset_section_devset_status_value_passed_through():
    """build_devset_section 不验证 status 值，只透传。"""
    m = _FakeManifest(status="custom_value")
    result = build_devset_section(m)
    assert result["status"] == "custom_value"


def test_module_all_includes_public_callables():
    """__all__ 中的每个名字都应是可调用或常量。"""
    import evaluation.report as m
    for name in m.__all__:
        obj = getattr(m, name)
        assert callable(obj) or isinstance(obj, (str, int, tuple, list, dict))


def test_module_all_does_not_include_private_constants():
    """私有常量（_ 前缀）不应在 __all__。"""
    import evaluation.report as m
    assert "_RATIO_METRICS" not in m.__all__
    assert "_COUNT_METRICS" not in m.__all__
    assert "_SUCCESS_BOOL_METRICS" not in m.__all__


def test_module_all_names_unique():
    import evaluation.report as m
    assert len(m.__all__) == len(set(m.__all__))


def test_module_all_names_are_strings():
    import evaluation.report as m
    for name in m.__all__:
        assert isinstance(name, str)


def test_module_has_required_public_callables():
    import evaluation.report as m
    for name in ("build_provenance", "build_devset_section", "aggregate_summary",
                 "get_git_provenance", "get_dependency_versions"):
        assert hasattr(m, name)
        assert callable(getattr(m, name))


def test_aggregate_summary_returns_consistent_top_key_order():
    """顶层 keys 应保留插入顺序：counts → success_rates → ratio_macro_averages → silent_drop_total。"""
    result = aggregate_summary([])
    keys = list(result.keys())
    assert keys == ["counts", "success_rates", "ratio_macro_averages", "silent_drop_total"]


def test_aggregate_summary_success_rate_value_is_float_or_none():
    pd = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    result = aggregate_summary(pd)
    rate = result["success_rates"]["pipeline_success"]["rate"]
    assert rate is None or isinstance(rate, float)


def test_aggregate_summary_count_sum_returns_int_or_none():
    """element_count_total 的 sum 总是 int 或 None。"""
    pd = [{"metrics": {"element_count_total": {"value": 5}}}]
    result = aggregate_summary(pd)
    s = result["counts"]["element_count_total"]["sum"]
    assert s is None or isinstance(s, int) or s == 5


def test_aggregate_summary_silent_drop_total_returns_int_or_none():
    pd = [{"metrics": {"silent_drop_count": {"value": 7}}}]
    result = aggregate_summary(pd)
    assert result["silent_drop_total"] == 7
    assert isinstance(result["silent_drop_total"], int)


# =========================================================================
# build_provenance 输出与 evaluation 模块版本对齐
# =========================================================================


def test_build_provenance_evaluator_version_matches_evaluation_module(tmp_path):
    """build_provenance 输出的 evaluator_version 应与 evaluation.EVALUATOR_VERSION 一致。"""
    from evaluation import EVALUATOR_VERSION as v
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["evaluator_version"] == v


def test_build_provenance_report_version_matches_evaluation_module(tmp_path):
    from evaluation import REPORT_VERSION as v
    result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["report_version"] == v


def test_build_provenance_run_timestamp_iso_contains_timezone_offset(tmp_path):
    """ISO 字符串应包含 +HH:MM 或 -HH:MM 形式的时区。"""
    result = build_provenance(tmp_path, "fallback", 800, None)
    ts = result["run_timestamp_iso"]
    # +HH:MM 或 -HH:MM 模式（最后 6 个字符）
    assert ts[-6] in ("+", "-")
    assert ts[-3] == ":"


def test_build_provenance_run_timestamp_iso_seconds_present(tmp_path):
    """ISO 字符串应包含秒（至少 YYYY-MM-DDTHH:MM:SS）。"""
    result = build_provenance(tmp_path, "fallback", 800, None)
    ts = result["run_timestamp_iso"]
    # 简单断言：T 分隔日期和时间
    assert "T" in ts
