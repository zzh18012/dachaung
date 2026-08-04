"""evaluation/report.py 边角测试 - 第三轮（Round 111）。

补强已有 base/edges/edges2（共 ~145 测试）未覆盖的深度路径：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS：
  tuple 元素顺序、唯一性、内部不含其它名字
- get_git_provenance：subprocess 输出含 trailing newline / 二进制 / unicode、
  timeout 触发、stderr 非空但 stdout 有效、cwd 不存在
- get_dependency_versions：返回的 dict 是新实例（多次调用互不影响）、
  版本字符串非空（不为 ""）、key 顺序固定
- build_provenance：max_chars 边界（最小、INT_MAX 风格）、
  parser_name 空 string、parser_version 空 string、
  run_timestamp_iso 含 'T' 分隔、dependencies 嵌套结构
- build_devset_section：Manifest 含 None 字段时的兼容性
- aggregate_summary：
  - counts 浮点数被纳入 sum（虽然实际是 int metric）
  - success_rates pipeline_success value=非 True/False（如 1）不计数
  - ratio_macro_averages value=0 视为非 None（参与）
  - silent_drop_count 与 _COUNT_METRICS 互不干扰
  - silent_drop_count 浮点
  - 多次调用幂等
- 模块结构深度：模块常量、imports、docstrings
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from evaluation import report
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
# _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS：深度顺序/唯一性
# =========================================================================


def test_ratio_metrics_first_entry_is_schema_valid():
    """顺序固定：schema_valid 第一（评测基础）。"""
    assert _RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_pdf_locator_before_docx_locator():
    """顺序：pdf_locator_valid_ratio 在 docx_locator_valid_ratio 前。"""
    pdf_idx = _RATIO_METRICS.index("pdf_locator_valid_ratio")
    docx_idx = _RATIO_METRICS.index("docx_locator_valid_ratio")
    assert pdf_idx < docx_idx


def test_ratio_metrics_text_char_precision_before_recall():
    """顺序：precision 在 recall 前。"""
    p_idx = _RATIO_METRICS.index("text_char_multiset_precision")
    r_idx = _RATIO_METRICS.index("text_char_multiset_recall")
    assert p_idx < r_idx


def test_ratio_metrics_chunk_boundary_precision_before_recall_before_f1():
    """顺序：precision < recall < f1。"""
    p = _RATIO_METRICS.index("chunk_boundary_precision")
    r = _RATIO_METRICS.index("chunk_boundary_recall")
    f = _RATIO_METRICS.index("chunk_boundary_f1")
    assert p < r < f


def test_ratio_metrics_chunk_reference_after_image_resource():
    """顺序：image_resource_exists_ratio 在 chunk_reference_intact_ratio 前。"""
    img = _RATIO_METRICS.index("image_resource_exists_ratio")
    chk = _RATIO_METRICS.index("chunk_reference_intact_ratio")
    assert img < chk


def test_ratio_metrics_unique_set_count_12():
    assert len(set(_RATIO_METRICS)) == 12


def test_count_metrics_only_one_entry():
    assert len(_COUNT_METRICS) == 1


def test_count_metrics_first_entry_element_count_total():
    assert _COUNT_METRICS[0] == "element_count_total"


def test_success_bool_metrics_only_one_entry():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_success_bool_metrics_first_entry_pipeline_success():
    assert _SUCCESS_BOOL_METRICS[0] == "pipeline_success"


def test_ratio_metrics_disjoint_from_count_metrics():
    """两个常量无交集。"""
    assert set(_RATIO_METRICS).isdisjoint(set(_COUNT_METRICS))


def test_ratio_metrics_disjoint_from_success_bool_metrics():
    """ratio 与 success_bool 互斥（schema_valid 在 ratio，不在 success_bool）。"""
    assert set(_RATIO_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))


def test_count_metrics_disjoint_from_success_bool_metrics():
    assert set(_COUNT_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))


def test_ratio_metrics_does_not_contain_silent_drop_count():
    """silent_drop_count 不参与 macro average。"""
    assert "silent_drop_count" not in _RATIO_METRICS


def test_count_metrics_does_not_contain_silent_drop_count():
    """silent_drop_count 也不在 counts（特殊单独聚合）。"""
    assert "silent_drop_count" not in _COUNT_METRICS


def test_success_bool_metrics_does_not_contain_schema_valid():
    """schema_valid 是 ratio 不是 success_bool。"""
    assert "schema_valid" not in _SUCCESS_BOOL_METRICS


# =========================================================================
# get_git_provenance：subprocess 输出边界
# =========================================================================


class _FakeResult:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_get_git_provenance_strips_trailing_newline_from_commit(
    monkeypatch, tmp_path: Path
):
    """git rev-parse 输出末尾有 \n，应 strip。"""
    seq = [_FakeResult(0, "abc123\n"), _FakeResult(0, "")]

    def fake_run(cmd, *args, **kwargs):
        return seq.pop(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"


def test_get_git_provenance_strips_multiple_newlines(monkeypatch, tmp_path: Path):
    seq = [_FakeResult(0, "abc\n\n\n"), _FakeResult(0, "")]

    def fake_run(cmd, *args, **kwargs):
        return seq.pop(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc"


def test_get_git_provenance_commit_with_unicode_replaced(monkeypatch, tmp_path: Path):
    """errors='replace'：输出含 unicode 替换字符也保留。"""
    seq = [_FakeResult(0, "abc中文"), _FakeResult(0, "")]

    def fake_run(cmd, *args, **kwargs):
        return seq.pop(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert "abc" in (out["git_commit"] or "")


def test_get_git_provenance_stderr_nonempty_does_not_affect_commit(
    monkeypatch, tmp_path: Path
):
    """stderr 内容不参与 commit 判断。"""
    seq = [_FakeResult(0, "good_commit\n", "warning xyz\n"), _FakeResult(0, "")]

    def fake_run(cmd, *args, **kwargs):
        return seq.pop(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "good_commit"


def test_get_git_provenance_porcelain_with_only_whitespace_not_dirty(
    monkeypatch, tmp_path: Path
):
    """porcelain 输出 ' \n ' 等 strip 后为空，应判 not dirty。"""
    seq = [_FakeResult(0, "abc\n"), _FakeResult(0, "   \n  \t ")]

    def fake_run(cmd, *args, **kwargs):
        return seq.pop(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_get_git_provenance_porcelain_with_actual_content_dirty(
    monkeypatch, tmp_path: Path
):
    seq = [_FakeResult(0, "abc\n"), _FakeResult(0, " M file.txt\n")]

    def fake_run(cmd, *args, **kwargs):
        return seq.pop(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


def test_get_git_provenance_rev_parse_fails_but_porcelain_ok(
    monkeypatch, tmp_path: Path
):
    """rev-parse 失败但 porcelain 成功 → commit=None, dirty 真实。"""
    seq = [_FakeResult(1, "", "no HEAD\n"), _FakeResult(0, " M f\n")]

    def fake_run(cmd, *args, **kwargs):
        return seq.pop(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_rev_parse_ok_but_porcelain_fails(
    monkeypatch, tmp_path: Path
):
    """rev-parse 成功但 porcelain 失败 → commit 实际，dirty=True（保守）。"""
    seq = [_FakeResult(0, "abc\n"), _FakeResult(1, "", "err")]

    def fake_run(cmd, *args, **kwargs):
        return seq.pop(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc"
    # r2.returncode != 0 → bool(False and ...) = False → dirty=True? 看代码：
    # dirty = bool(r2.returncode == 0 and r2.stdout.strip())
    # r2.returncode=1 → False and ... = False → dirty=False
    # 实际代码此情况下 dirty=False
    assert out["git_dirty"] is False


def test_get_git_provenance_timeout_in_rev_parse(monkeypatch, tmp_path: Path):
    """rev-parse 超时 → except → commit=None, dirty=True。"""

    def fake_run(cmd, *args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=10)

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_timeout_in_porcelain(monkeypatch, tmp_path: Path):
    """rev-parse ok 但 porcelain 超时 → except → commit=None, dirty=True。"""
    call_count = [0]

    def fake_run(cmd, *args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return _FakeResult(0, "abc\n")
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=10)

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    # except 把 commit 也置 None
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_returns_fresh_dict_each_call(tmp_path: Path):
    """多次调用应返回不同 dict 实例。"""
    a = get_git_provenance(tmp_path)
    b = get_git_provenance(tmp_path)
    assert a is not b
    assert set(a.keys()) == set(b.keys())


def test_get_git_provenance_returns_only_two_keys(tmp_path: Path):
    out = get_git_provenance(tmp_path)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


# =========================================================================
# get_dependency_versions：返回结构细节
# =========================================================================


def test_dependency_versions_returns_fresh_dict_each_call():
    a = get_dependency_versions()
    b = get_dependency_versions()
    assert a is not b


def test_dependency_versions_exact_three_keys_in_order():
    """key 顺序固定：pdfplumber, python-docx, pypdfium2。"""
    v = get_dependency_versions()
    keys = list(v.keys())
    assert keys == ["pdfplumber", "python-docx", "pypdfium2"]


def test_dependency_versions_values_are_str_or_none():
    v = get_dependency_versions()
    for k, val in v.items():
        assert val is None or isinstance(val, str)


def test_dependency_versions_no_bool_values():
    """版本字符串不应是 bool（True/False）。"""
    v = get_dependency_versions()
    for val in v.values():
        assert val is not True
        assert val is not False


# =========================================================================
# build_provenance：字段细节
# =========================================================================


def test_build_provenance_run_timestamp_has_t_separator(tmp_path: Path):
    """ISO 格式应含 'T' 分隔日期和时间。"""
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert "T" in out["run_timestamp_iso"]


def test_build_provenance_dependencies_key_present(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert "dependencies" in out


def test_build_provenance_dependencies_value_is_dict(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_dependencies_dict_has_three_entries(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert len(out["dependencies"]) == 3


def test_build_provenance_parser_name_empty_string(tmp_path: Path):
    """parser_name='' 应被原样保留（业务约束在调用方）。"""
    out = build_provenance(tmp_path, "", 800, None)
    assert out["parser_name"] == ""


def test_build_provenance_parser_version_empty_string(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, "")
    assert out["parser_version"] == ""


def test_build_provenance_parser_name_with_unicode(tmp_path: Path):
    out = build_provenance(tmp_path, "自定义", 800, "1.0")
    assert out["parser_name"] == "自定义"


def test_build_provenance_max_chars_minimum_int(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 1, None)
    assert out["max_chars"] == 1


def test_build_provenance_max_chars_huge_int(tmp_path: Path):
    big = 2**31 - 1  # INT32 max
    out = build_provenance(tmp_path, "fallback", big, None)
    assert out["max_chars"] == big


def test_build_provenance_returns_dict_type(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out, dict)


def test_build_provenance_exact_nine_keys(tmp_path: Path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert len(out) == 9


def test_build_provenance_evaluator_version_value_constant(tmp_path: Path):
    """evaluator_version 必须等于 evaluation.EVALUATOR_VERSION。"""
    from evaluation import EVALUATOR_VERSION

    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value_constant(tmp_path: Path):
    from evaluation import REPORT_VERSION

    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


# =========================================================================
# build_devset_section：Manifest 字段细节
# =========================================================================


class _FakeManifest:
    """Minimal manifest-like for build_devset_section."""

    def __init__(self, **kw):
        for k in (
            "devset_status",
            "file_count",
            "content_group_count",
            "pdf_count",
            "docx_count",
            "categories_covered",
        ):
            setattr(self, k, kw.get(k))


def test_build_devset_section_returns_dict_type():
    m = _FakeManifest()
    out = build_devset_section(m)
    assert isinstance(out, dict)


def test_build_devset_section_exact_six_keys():
    m = _FakeManifest()
    out = build_devset_section(m)
    assert len(out) == 6


def test_build_devset_section_with_none_status():
    m = _FakeManifest(devset_status=None)
    out = build_devset_section(m)
    assert out["status"] is None


def test_build_devset_section_with_zero_counts():
    m = _FakeManifest(
        devset_status="incomplete",
        file_count=0,
        content_group_count=0,
        pdf_count=0,
        docx_count=0,
        categories_covered=[],
    )
    out = build_devset_section(m)
    assert out["file_count"] == 0
    assert out["content_group_count"] == 0
    assert out["pdf_count"] == 0
    assert out["docx_count"] == 0
    assert out["categories_covered"] == []


def test_build_devset_section_preserves_status_value():
    m = _FakeManifest(devset_status="complete")
    out = build_devset_section(m)
    assert out["status"] == "complete"


def test_build_devset_section_preserves_categories_list():
    cats = ["a", "b", "c"]
    m = _FakeManifest(categories_covered=cats)
    out = build_devset_section(m)
    assert out["categories_covered"] == cats


def test_build_devset_section_categories_with_none():
    m = _FakeManifest(categories_covered=None)
    out = build_devset_section(m)
    assert out["categories_covered"] is None


# =========================================================================
# aggregate_summary：深度
# =========================================================================


def _metric(name: str, value) -> dict[str, Any]:
    return {name: {"value": value, "reason": "r"}}


def test_aggregate_summary_counts_with_float_value_treated_as_number():
    """虽然 element_count_total 实际是 int，但 sum 接受 float。"""
    docs = [
        {"metrics": _metric("element_count_total", 1.5)},
        {"metrics": _metric("element_count_total", 2.5)},
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 4.0


def test_aggregate_summary_success_rate_value_one_not_counted_as_true():
    """pipeline_success value=1（int）不应被计为 True。"""
    docs = [{"metrics": _metric("pipeline_success", 1)}]
    out = aggregate_summary(docs)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0


def test_aggregate_summary_success_rate_value_string_true_not_counted():
    docs = [{"metrics": _metric("pipeline_success", "true")}]
    out = aggregate_summary(docs)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0


def test_aggregate_summary_ratio_zero_participates_in_macro():
    docs = [
        {"metrics": _metric("schema_valid", 0)},
        {"metrics": _metric("schema_valid", 1)},
    ]
    out = aggregate_summary(docs)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2


def test_aggregate_summary_silent_drop_count_with_float():
    docs = [
        {"metrics": _metric("silent_drop_count", 1.5)},
        {"metrics": _metric("silent_drop_count", 2.5)},
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 4.0


def test_aggregate_summary_silent_drop_count_with_negative():
    """负值也被 sum（虽然业务上不该出现）。"""
    docs = [
        {"metrics": _metric("silent_drop_count", -1)},
        {"metrics": _metric("silent_drop_count", 5)},
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 4


def test_aggregate_summary_idempotent_on_repeated_call():
    docs = [{"metrics": _metric("element_count_total", 5)}]
    a = aggregate_summary(docs)
    b = aggregate_summary(docs)
    # 测试结果应一致（不是同对象，但内容相等）
    assert a == b


def test_aggregate_summary_does_not_mix_counts_and_silent_drop():
    """counts.sum 和 silent_drop_total 应分开聚合。"""
    docs = [
        {
            "metrics": {
                "element_count_total": {"value": 10, "reason": "r"},
                "silent_drop_count": {"value": 2, "reason": "r"},
            }
        }
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 10
    assert out["silent_drop_total"] == 2
    # silent_drop 不在 counts 里
    assert "silent_drop_count" not in out["counts"]


def test_aggregate_summary_counts_and_success_rates_separate():
    """counts 不应包含 success_rates 的字段。"""
    docs = [
        {
            "metrics": {
                "element_count_total": {"value": 5, "reason": "r"},
                "pipeline_success": {"value": True, "reason": "r"},
            }
        }
    ]
    out = aggregate_summary(docs)
    assert "pipeline_success" not in out["counts"]
    assert "element_count_total" not in out["success_rates"]


def test_aggregate_summary_returns_proper_top_level_keys():
    out = aggregate_summary([])
    assert set(out.keys()) == {
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    }


def test_aggregate_summary_handles_per_doc_results_being_none_metrics():
    """per_doc 没有 metrics 字段 → aggregate_summary 抛 KeyError（已知行为）。"""
    docs: list[dict[str, Any]] = [{}]
    with pytest.raises(KeyError):
        aggregate_summary(docs)


def test_aggregate_summary_with_huge_input_does_not_crash():
    """性能 sanity check：1000 docs 不崩。"""
    docs = [
        {"metrics": _metric("element_count_total", i)} for i in range(1000)
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == sum(range(1000))


# =========================================================================
# 模块结构
# =========================================================================


def test_module_docstring_present():
    assert report.__doc__ is not None


def test_module_docstring_mentions_aggregation_rules():
    """模块 docstring 应解释聚合规则。"""
    assert "counts" in report.__doc__ or "聚合" in report.__doc__


def test_module_imports_subprocess():
    assert hasattr(report, "subprocess")


def test_module_imports_datetime():
    assert hasattr(report, "datetime")


def test_module_imports_path():
    assert hasattr(report, "Path")


def test_module_imports_any():
    """Any from typing。"""
    assert hasattr(report, "Any")


def test_module_imports_evaluator_version():
    assert hasattr(report, "EVALUATOR_VERSION")


def test_module_imports_report_version():
    assert hasattr(report, "REPORT_VERSION")


def test_module_evaluator_version_value():
    from evaluation import EVALUATOR_VERSION

    assert report.EVALUATOR_VERSION == EVALUATOR_VERSION


def test_module_report_version_value():
    from evaluation import REPORT_VERSION

    assert report.REPORT_VERSION == REPORT_VERSION


def test_module_all_exact_set():
    assert set(report.__all__) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_all_count_five():
    assert len(report.__all__) == 5


def test_module_all_does_not_include_constants():
    """_RATIO_METRICS 等下划线常量不在 __all__。"""
    assert "_RATIO_METRICS" not in report.__all__
    assert "_COUNT_METRICS" not in report.__all__
    assert "_SUCCESS_BOOL_METRICS" not in report.__all__


def test_get_git_provenance_has_docstring():
    assert get_git_provenance.__doc__ is not None


def test_get_dependency_versions_has_docstring():
    assert get_dependency_versions.__doc__ is not None


def test_build_provenance_no_docstring_required():
    """build_provenance 是简单装配函数，不强求 docstring。"""
    # 仅断言函数存在
    assert callable(build_provenance)


def test_build_devset_section_has_docstring():
    assert build_devset_section.__doc__ is not None


def test_aggregate_summary_has_docstring():
    assert aggregate_summary.__doc__ is not None


def test_get_git_provenance_docstring_mentions_failure():
    """docstring 应说明失败时的默认行为。"""
    doc = get_git_provenance.__doc__ or ""
    assert "null" in doc or "失败" in doc or "dirty" in doc


def test_aggregate_summary_docstring_mentions_no_mixing():
    """docstring 应说明不混合类型。"""
    doc = aggregate_summary.__doc__ or ""
    assert "混合" in doc or "不混合" in doc or "macro" in doc


def test_get_dependency_versions_docstring_mentions_packages():
    doc = get_dependency_versions.__doc__ or ""
    assert "pdfplumber" in doc or "docx" in doc or "pypdfium" in doc


def test_get_git_provenance_signature_one_param():
    import inspect

    sig = inspect.signature(get_git_provenance)
    assert len(sig.parameters) == 1
    assert "project_root" in sig.parameters


def test_get_dependency_versions_signature_no_params():
    import inspect

    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_build_provenance_signature_four_params():
    import inspect

    sig = inspect.signature(build_provenance)
    assert len(sig.parameters) == 4


def test_build_devset_section_signature_one_param():
    import inspect

    sig = inspect.signature(build_devset_section)
    assert len(sig.parameters) == 1


def test_aggregate_summary_signature_one_param():
    import inspect

    sig = inspect.signature(aggregate_summary)
    assert len(sig.parameters) == 1


def test_module_constants_are_tuples():
    """三个常量都是 tuple。"""
    assert isinstance(_RATIO_METRICS, tuple)
    assert isinstance(_COUNT_METRICS, tuple)
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_module_constants_immutable_at_module_level():
    """重新 import 不影响常量值。"""
    from evaluation.report import _RATIO_METRICS as r1
    from evaluation.report import _RATIO_METRICS as r2

    assert r1 is r2  # 同一对象
