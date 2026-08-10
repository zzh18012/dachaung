"""evaluation/report.py 第二十五轮 edges 测试（Round 381）。

补强 edges24 未触及的角度：
- get_git_provenance 行为深度第八批（timeout / FileNotFoundError / empty stdout / whitespace stdout / 多次调用结构稳定 / dict key 顺序）
- get_dependency_versions 行为深度第八批（PackageNotFoundError / 通用 Exception / 3 keys exact / 每次返回 fresh dict / python-docx 带连字符）
- build_provenance 行为深度第八批（max_chars 不同输入 / parser_version None / dependencies 是 fresh dict / 时间戳格式 / key 类型）
- build_devset_section 行为深度第八批（6 keys 类型 / categories_covered iterable / 无多余 keys / 单次调用结果稳定）
- aggregate_summary 行为深度第八批（chunk_boundary 参与 / figure_caption 不参与 / silent_drop_all_none / counts 负数 / 输入不 mutate / 输出 4 keys 顺序 / ratio_macro 12 项）
- module source forbidden tokens 第十一批
- module source 字符串精确补强第八批（subprocess.run 参数序列 / try/except 类型 / return 字面量）
- signatures 第八批（5 funcs 返回类型 / 参数 kind / 参数名）
- module 合理性第八批（__all__ 5 项 / 5 callable functions / 3 constants / file path）
- 端到端集成第八批（full chain / partial participation / not_evaluated count / input mutation safety）
"""

from __future__ import annotations

import inspect
import json
import subprocess
import types
from pathlib import Path
from unittest.mock import patch

import pytest

from evaluation import EVALUATOR_VERSION, REPORT_VERSION, report as rmod
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


# ---------- get_git_provenance 行为深度第八批 ----------


def test_get_git_provenance_handles_timeout_expired():
    """subprocess 抛 TimeoutExpired（继承 SubprocessError）→ except 命中 → commit None, dirty True。"""

    def _boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=10)

    with patch("subprocess.run", side_effect=_boom):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_handles_filenotfounderror():
    """git 不在 PATH → FileNotFoundError（继承 OSError）→ except 命中。"""

    def _boom(*args, **kwargs):
        raise FileNotFoundError("git")

    with patch("subprocess.run", side_effect=_boom):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_revparse_nonzero_yields_none_commit():
    """rev-parse 返回非零 → commit None。dirty 由 porcelain 决定。"""
    fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="err")
    with patch("subprocess.run", return_value=fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None


def test_get_git_provenance_revparse_empty_stdout_yields_none_commit():
    """rev-parse 返回 0 但 stdout 为空 → commit None（`or None` 生效）。"""
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None


def test_get_git_provenance_revparse_whitespace_only_stdout_yields_none_commit():
    """rev-parse 返回 0 但 stdout 是空白 → strip 后空 → commit None。"""
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="   \n\t  ", stderr="")
    with patch("subprocess.run", return_value=fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None


def test_get_git_provenance_commit_strips_whitespace():
    fake = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="  abc1234\n  ", stderr=""
    )
    with patch("subprocess.run", return_value=fake):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] == "abc1234"


def test_get_git_provenance_porcelain_clean_yields_dirty_false():
    """porcelain stdout 为空（即使 returncode 0）→ dirty=False。"""
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=fake):
        out = get_git_provenance(Path("."))
    assert out["git_dirty"] is False


def test_get_git_provenance_porcelain_with_output_yields_dirty_true():
    fake = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=" M file.py\n", stderr=""
    )
    with patch("subprocess.run", return_value=fake):
        out = get_git_provenance(Path("."))
    assert out["git_dirty"] is True


def test_get_git_provenance_porcelain_nonzero_yields_dirty_false():
    """porcelain returncode != 0 → 短路 bool → dirty=False。"""
    fake = subprocess.CompletedProcess(args=[], returncode=128, stdout="?? ", stderr="err")
    with patch("subprocess.run", return_value=fake):
        out = get_git_provenance(Path("."))
    assert out["git_dirty"] is False


def test_get_git_provenance_returns_consistent_keys_across_calls():
    out1 = get_git_provenance(Path("."))
    out2 = get_git_provenance(Path("."))
    assert list(out1.keys()) == list(out2.keys())


def test_get_git_provenance_keys_are_str():
    out = get_git_provenance(Path("."))
    for k in out:
        assert isinstance(k, str)


# ---------- get_dependency_versions 行为深度第八批 ----------


def test_get_dependency_versions_handles_package_not_found():
    """patch importlib.metadata.version 抛 PackageNotFoundError → 该 pkg=None。"""
    import importlib.metadata

    real_version = importlib.metadata.version

    def _fake(name):
        if name == "pdfplumber":
            raise importlib.metadata.PackageNotFoundError(name)
        return real_version(name)

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    assert out["pdfplumber"] is None


def test_get_dependency_versions_handles_generic_exception():
    """patch importlib.metadata.version 抛 Exception → 该 pkg=None。"""

    def _boom(name):
        raise RuntimeError("boom")

    with patch("importlib.metadata.version", side_effect=_boom):
        out = get_dependency_versions()
    for pkg in ("pdfplumber", "python-docx", "pypdfium2"):
        assert out[pkg] is None


def test_get_dependency_versions_specific_python_docx_with_hyphen():
    """注意：包名 'python-docx'（连字符），不是 'python_docx'。"""
    out = get_dependency_versions()
    assert "python-docx" in out
    assert "python_docx" not in out


def test_get_dependency_versions_returns_fresh_dict_each_call():
    """每次调用返回新 dict，不是共享 singleton。"""
    out1 = get_dependency_versions()
    out2 = get_dependency_versions()
    assert out1 is not out2
    assert out1 == out2


def test_get_dependency_versions_three_keys_exact_via_list():
    out = get_dependency_versions()
    assert len(out) == 3
    assert list(out.keys()) == ["pdfplumber", "python-docx", "pypdfium2"]


def test_get_dependency_versions_values_str_or_none():
    out = get_dependency_versions()
    for v in out.values():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_no_extra_keys():
    out = get_dependency_versions()
    expected = {"pdfplumber", "python-docx", "pypdfium2"}
    assert set(out.keys()) == expected


# ---------- build_provenance 行为深度第八批 ----------


def test_build_provenance_keys_are_all_str():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    for k in out:
        assert isinstance(k, str)


def test_build_provenance_nine_keys_exact_via_list():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert list(out.keys()) == [
        "git_commit",
        "git_dirty",
        "evaluator_version",
        "report_version",
        "parser_name",
        "parser_version",
        "dependencies",
        "max_chars",
        "run_timestamp_iso",
    ]


def test_build_provenance_max_chars_int_pass_through():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=500, parser_version=None)
    assert out["max_chars"] == 500
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_str_numeric_converted():
    out = build_provenance(Path("."), parser_name="fallback", max_chars="800", parser_version=None)
    assert out["max_chars"] == 800


def test_build_provenance_max_chars_bool_true_converted_to_one():
    """int(True) == 1。"""
    out = build_provenance(Path("."), parser_name="fallback", max_chars=True, parser_version=None)
    assert out["max_chars"] == 1


def test_build_provenance_parser_version_preserved_when_string():
    out = build_provenance(
        Path("."), parser_name="fallback", max_chars=800, parser_version="1.2.3"
    )
    assert out["parser_version"] == "1.2.3"


def test_build_provenance_parser_name_preserved():
    out = build_provenance(
        Path("."), parser_name="kreuzberg", max_chars=800, parser_version=None
    )
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_dependencies_is_fresh_dict_each_call():
    out1 = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    out2 = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert out1["dependencies"] is not out2["dependencies"]


def test_build_provenance_run_timestamp_has_iso_format():
    """ISO 8601 时间戳至少包含 'T' 分隔。"""
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    ts = out["run_timestamp_iso"]
    assert isinstance(ts, str)
    assert "T" in ts


def test_build_provenance_evaluator_version_matches_constant():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_matches_constant():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_returns_dict_type():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert isinstance(out, dict)


# ---------- build_devset_section 行为深度第八批 ----------


class _StubManifest:
    """最小 Manifest stub，6 属性。"""

    devset_status = "incomplete"
    file_count = 4
    content_group_count = 2
    pdf_count = 2
    docx_count = 2
    categories_covered = ["normal", "edge"]


def test_build_devset_section_keys_all_str():
    out = build_devset_section(_StubManifest())
    for k in out:
        assert isinstance(k, str)


def test_build_devset_section_six_keys_exact_via_list():
    out = build_devset_section(_StubManifest())
    assert list(out.keys()) == [
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    ]


def test_build_devset_section_no_extra_keys():
    out = build_devset_section(_StubManifest())
    assert len(out) == 6


def test_build_devset_section_status_value_type():
    out = build_devset_section(_StubManifest())
    assert isinstance(out["status"], str)


def test_build_devset_section_file_count_type():
    out = build_devset_section(_StubManifest())
    assert isinstance(out["file_count"], int)


def test_build_devset_section_categories_covered_is_list():
    out = build_devset_section(_StubManifest())
    assert isinstance(out["categories_covered"], list)


def test_build_devset_section_value_propagation_status():
    class _M:
        devset_status = "complete"
        file_count = 1
        content_group_count = 1
        pdf_count = 1
        docx_count = 0
        categories_covered = []

    out = build_devset_section(_M())
    assert out["status"] == "complete"


def test_build_devset_section_value_propagation_pdf_docx():
    class _M:
        devset_status = "complete"
        file_count = 1
        content_group_count = 1
        pdf_count = 7
        docx_count = 3
        categories_covered = []

    out = build_devset_section(_M())
    assert out["pdf_count"] == 7
    assert out["docx_count"] == 3


def test_build_devset_section_with_empty_categories():
    class _M:
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []

    out = build_devset_section(_M())
    assert out["categories_covered"] == []


# ---------- aggregate_summary 行为深度第八批 ----------


def _metrics_doc(metrics: dict) -> dict:
    return {"metrics": metrics}


def test_aggregate_summary_chunk_boundary_participates_in_macro_average():
    """chunk_boundary_f1 是 ratio metric，应参与 macro average。"""
    docs = [
        _metrics_doc({"chunk_boundary_f1": {"value": 0.5}}),
        _metrics_doc({"chunk_boundary_f1": {"value": 1.0}}),
    ]
    out = aggregate_summary(docs)
    macro = out["ratio_macro_averages"]["chunk_boundary_f1"]
    assert macro["macro_average"] == pytest.approx(0.75)
    assert macro["participating_docs"] == 2
    assert macro["not_evaluated"] == 0


def test_aggregate_summary_chunk_boundary_with_skipped():
    docs = [
        _metrics_doc({"chunk_boundary_f1": {"value": 0.5}}),
        _metrics_doc({"chunk_boundary_f1": {"value": None}}),
        _metrics_doc({"chunk_boundary_f1": {"value": 1.0}}),
    ]
    out = aggregate_summary(docs)
    macro = out["ratio_macro_averages"]["chunk_boundary_f1"]
    assert macro["macro_average"] == pytest.approx(0.75)
    assert macro["participating_docs"] == 2
    assert macro["not_evaluated"] == 1


def test_aggregate_summary_figure_caption_not_in_ratio_macro_averages():
    """figure_caption_* 不在 _RATIO_METRICS 中。"""
    docs = [_metrics_doc({"figure_caption_f1": {"value": 0.9}})]
    out = aggregate_summary(docs)
    assert "figure_caption_f1" not in out["ratio_macro_averages"]
    assert "figure_caption_precision" not in out["ratio_macro_averages"]
    assert "figure_caption_recall" not in out["ratio_macro_averages"]


def test_aggregate_summary_silent_drop_total_all_none_yields_none():
    docs = [
        _metrics_doc({"silent_drop_count": {"value": None}}),
        _metrics_doc({"silent_drop_count": {"value": None}}),
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_total_some_none():
    docs = [
        _metrics_doc({"silent_drop_count": {"value": 3}}),
        _metrics_doc({"silent_drop_count": {"value": None}}),
        _metrics_doc({"silent_drop_count": {"value": 5}}),
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_total_missing_key():
    """metrics 缺 silent_drop_count key → 等价 value None → 不参与。"""
    docs = [
        _metrics_doc({}),
        _metrics_doc({"silent_drop_count": {"value": 5}}),
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 5


def test_aggregate_summary_counts_supports_negative_values():
    """counts sum 不限制符号。"""
    docs = [
        _metrics_doc({"element_count_total": {"value": -3}}),
        _metrics_doc({"element_count_total": {"value": 5}}),
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 2


def test_aggregate_summary_counts_negative_only():
    docs = [
        _metrics_doc({"element_count_total": {"value": -3}}),
        _metrics_doc({"element_count_total": {"value": -1}}),
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == -4


def test_aggregate_summary_input_not_mutated():
    """不修改输入 list 内容。"""
    docs = [
        _metrics_doc({"element_count_total": {"value": 5}}),
    ]
    docs_snapshot = [{"metrics": dict(d["metrics"])} for d in docs]
    _ = aggregate_summary(docs)
    assert docs == docs_snapshot


def test_aggregate_summary_input_dict_not_mutated():
    docs = [_metrics_doc({"element_count_total": {"value": 5}})]
    metrics_before = dict(docs[0]["metrics"])
    _ = aggregate_summary(docs)
    assert docs[0]["metrics"] == metrics_before


def test_aggregate_summary_top_level_four_keys_exact_via_list():
    docs = []
    out = aggregate_summary(docs)
    assert list(out.keys()) == ["counts", "success_rates", "ratio_macro_averages", "silent_drop_total"]


def test_aggregate_summary_ratio_macro_averages_has_12_entries():
    docs = []
    out = aggregate_summary(docs)
    assert len(out["ratio_macro_averages"]) == 12


def test_aggregate_summary_counts_has_1_entry():
    docs = []
    out = aggregate_summary(docs)
    assert len(out["counts"]) == 1


def test_aggregate_summary_success_rates_has_1_entry():
    docs = []
    out = aggregate_summary(docs)
    assert len(out["success_rates"]) == 1


def test_aggregate_summary_success_rate_with_all_true():
    docs = [
        _metrics_doc({"pipeline_success": {"value": True}}),
        _metrics_doc({"pipeline_success": {"value": True}}),
    ]
    out = aggregate_summary(docs)
    rate = out["success_rates"]["pipeline_success"]
    assert rate["success_count"] == 2
    assert rate["total"] == 2
    assert rate["rate"] == 1.0


def test_aggregate_summary_success_rate_with_all_false():
    docs = [
        _metrics_doc({"pipeline_success": {"value": False}}),
        _metrics_doc({"pipeline_success": {"value": False}}),
    ]
    out = aggregate_summary(docs)
    rate = out["success_rates"]["pipeline_success"]
    assert rate["success_count"] == 0
    assert rate["rate"] == 0.0


def test_aggregate_summary_success_rate_with_mixed():
    docs = [
        _metrics_doc({"pipeline_success": {"value": True}}),
        _metrics_doc({"pipeline_success": {"value": False}}),
        _metrics_doc({"pipeline_success": {"value": True}}),
    ]
    out = aggregate_summary(docs)
    rate = out["success_rates"]["pipeline_success"]
    assert rate["success_count"] == 2
    assert rate["total"] == 3
    assert rate["rate"] == pytest.approx(2 / 3)


def test_aggregate_summary_success_rate_missing_key_treated_as_false():
    """缺 pipeline_success → value None → 不计入 success。"""
    docs = [
        _metrics_doc({}),
        _metrics_doc({"pipeline_success": {"value": True}}),
    ]
    out = aggregate_summary(docs)
    rate = out["success_rates"]["pipeline_success"]
    # 注意 total 始终等于 len(per_doc_results)
    assert rate["success_count"] == 1
    assert rate["total"] == 2


def test_aggregate_summary_macro_average_value_is_float_when_present():
    docs = [_metrics_doc({"schema_valid": {"value": 1.0}})]
    out = aggregate_summary(docs)
    macro = out["ratio_macro_averages"]["schema_valid"]
    assert isinstance(macro["macro_average"], float)


def test_aggregate_summary_macro_average_correct_for_multiple_metrics():
    docs = [
        _metrics_doc({"schema_valid": {"value": 1.0}, "text_preservation_equal": {"value": 0.8}}),
        _metrics_doc({"schema_valid": {"value": 0.0}, "text_preservation_equal": {"value": 0.4}}),
    ]
    out = aggregate_summary(docs)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == pytest.approx(0.5)
    assert out["ratio_macro_averages"]["text_preservation_equal"]["macro_average"] == pytest.approx(0.6)


def test_aggregate_summary_not_evaluated_correct_for_single_metric():
    """单 metric 部分 skip。"""
    docs = [
        _metrics_doc({"schema_valid": {"value": 1.0}}),
        _metrics_doc({}),
        _metrics_doc({"schema_valid": {"value": None}}),
        _metrics_doc({"schema_valid": {"value": 0.5}}),
    ]
    out = aggregate_summary(docs)
    macro = out["ratio_macro_averages"]["schema_valid"]
    assert macro["participating_docs"] == 2
    assert macro["not_evaluated"] == 2
    assert macro["macro_average"] == pytest.approx(0.75)


def test_aggregate_summary_does_not_produce_combined_score():
    """不混合类型：summary 顶层不应有 'overall' / 'total_score' 等综合分。"""
    docs = [_metrics_doc({"schema_valid": {"value": 1.0}})]
    out = aggregate_summary(docs)
    for forbidden in ("overall", "total_score", "combined", "final_score"):
        assert forbidden not in out


def test_aggregate_summary_counts_participating_docs_correctness():
    docs = [
        _metrics_doc({"element_count_total": {"value": 5}}),
        _metrics_doc({"element_count_total": {"value": 10}}),
        _metrics_doc({"element_count_total": {"value": None}}),
    ]
    out = aggregate_summary(docs)
    counts = out["counts"]["element_count_total"]
    assert counts["sum"] == 15
    assert counts["participating_docs"] == 2


def test_aggregate_summary_counts_empty_yields_none_sum():
    docs = []
    out = aggregate_summary(docs)
    counts = out["counts"]["element_count_total"]
    assert counts["sum"] is None
    assert counts["participating_docs"] == 0


def test_aggregate_summary_counts_all_none_yields_none_sum():
    docs = [
        _metrics_doc({"element_count_total": {"value": None}}),
        _metrics_doc({"element_count_total": {"value": None}}),
    ]
    out = aggregate_summary(docs)
    counts = out["counts"]["element_count_total"]
    assert counts["sum"] is None
    assert counts["participating_docs"] == 0


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 常量精确补强第八批 ----------


def test_ratio_metrics_exact_12_entries():
    """精确 12 项 ratio metrics。"""
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_includes_schema_valid():
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_includes_chunk_boundary_three():
    assert "chunk_boundary_precision" in _RATIO_METRICS
    assert "chunk_boundary_recall" in _RATIO_METRICS
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_includes_text_preservation_three():
    assert "text_preservation_equal" in _RATIO_METRICS
    assert "text_char_multiset_precision" in _RATIO_METRICS
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_includes_locator_resource_chunk():
    assert "pdf_locator_valid_ratio" in _RATIO_METRICS
    assert "docx_locator_valid_ratio" in _RATIO_METRICS
    assert "image_resource_exists_ratio" in _RATIO_METRICS
    assert "chunk_reference_intact_ratio" in _RATIO_METRICS


def test_ratio_metrics_includes_heading_boundary_compliance():
    assert "heading_boundary_compliance" in _RATIO_METRICS


def test_ratio_metrics_excludes_silent_drop_count():
    assert "silent_drop_count" not in _RATIO_METRICS


def test_ratio_metrics_excludes_element_count_total():
    assert "element_count_total" not in _RATIO_METRICS


def test_ratio_metrics_excludes_pipeline_success():
    assert "pipeline_success" not in _RATIO_METRICS


def test_count_metrics_exact_one_entry():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_exact_one_entry():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_constants_mutually_exclusive_no_overlap():
    """3 个常量集合无交集。"""
    all_metrics = list(_RATIO_METRICS) + list(_COUNT_METRICS) + list(_SUCCESS_BOOL_METRICS)
    assert len(all_metrics) == len(set(all_metrics))


def test_constants_total_14_metrics():
    """ratio(12) + count(1) + success(1) = 14。"""
    assert len(_RATIO_METRICS) + len(_COUNT_METRICS) + len(_SUCCESS_BOOL_METRICS) == 14


# ---------- module source forbidden tokens 第十一批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "pickle.loads",
        "yaml.load",
        "yaml.unsafe_load",
        "subprocess.check_call",
        "subprocess.call",
        "subprocess.getoutput",
        "os.popen",
    ],
)
def test_report_source_no_forbidden_token_v4(token):
    source = inspect.getsource(rmod)
    assert token not in source


def test_report_source_no_eval_call():
    source = inspect.getsource(rmod)
    assert "eval(" not in source


def test_report_source_no_exec_call():
    source = inspect.getsource(rmod)
    assert "exec(" not in source


def test_report_source_no_compile_call():
    source = inspect.getsource(rmod)
    assert "compile(" not in source


def test_report_source_no_unlink_call():
    source = inspect.getsource(rmod)
    assert "unlink" not in source


def test_report_source_no_rmtree():
    source = inspect.getsource(rmod)
    assert "rmtree" not in source


def test_report_source_no_remove():
    source = inspect.getsource(rmod)
    assert ".remove(" not in source


def test_report_source_no_kill():
    source = inspect.getsource(rmod)
    assert ".kill(" not in source


def test_report_source_no_terminate():
    source = inspect.getsource(rmod)
    assert ".terminate(" not in source


def test_report_source_no_system_exit():
    source = inspect.getsource(rmod)
    assert "sys.exit" not in source


def test_report_source_no_exit_call():
    source = inspect.getsource(rmod)
    assert "exit(" not in source


def test_report_source_no_quit_call():
    source = inspect.getsource(rmod)
    assert "quit(" not in source


# ---------- module source 字符串精确补强第八批 ----------


def test_module_source_subprocess_run_call():
    source = inspect.getsource(rmod)
    assert "subprocess.run(" in source


def test_module_source_capture_output_true():
    source = inspect.getsource(rmod)
    assert "capture_output=True" in source


def test_module_source_encoding_utf8():
    source = inspect.getsource(rmod)
    assert 'encoding="utf-8"' in source


def test_module_source_errors_replace():
    source = inspect.getsource(rmod)
    assert 'errors="replace"' in source


def test_module_source_timeout_10():
    source = inspect.getsource(rmod)
    assert "timeout=10" in source


def test_module_source_rev_parse_command():
    source = inspect.getsource(rmod)
    assert "rev-parse" in source
    assert "HEAD" in source


def test_module_source_status_porcelain_command():
    source = inspect.getsource(rmod)
    assert "status" in source
    assert "--porcelain" in source


def test_module_source_try_except_oserror_subprocess_error():
    source = inspect.getsource(rmod)
    assert "except" in source
    assert "OSError" in source
    assert "SubprocessError" in source


def test_module_source_returns_dict_with_git_commit_and_dirty():
    source = inspect.getsource(rmod)
    assert '"git_commit"' in source
    assert '"git_dirty"' in source


def test_module_source_importlib_metadata_inline_import():
    source = inspect.getsource(rmod)
    assert "import importlib.metadata" in source


def test_module_source_three_pkg_tuple():
    source = inspect.getsource(rmod)
    assert '"pdfplumber"' in source
    assert '"python-docx"' in source
    assert '"pypdfium2"' in source


def test_module_source_aggregate_summary_docstring_no_mix():
    source = inspect.getsource(rmod)
    assert "不混合" in source


def test_module_source_no_main_block():
    source = inspect.getsource(rmod)
    assert 'if __name__' not in source


def test_module_source_has_future_annotations():
    source = inspect.getsource(rmod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_any():
    source = inspect.getsource(rmod)
    assert "from typing import Any" in source


def test_module_source_imports_path():
    source = inspect.getsource(rmod)
    assert "from pathlib import Path" in source


def test_module_source_imports_datetime():
    source = inspect.getsource(rmod)
    assert "from datetime import datetime" in source


def test_module_source_imports_subprocess_module():
    source = inspect.getsource(rmod)
    assert "import subprocess" in source


def test_module_source_count_metrics_constant_literal():
    source = inspect.getsource(rmod)
    assert '_COUNT_METRICS = ("element_count_total",)' in source


def test_module_source_success_bool_metrics_constant_literal():
    source = inspect.getsource(rmod)
    assert '_SUCCESS_BOOL_METRICS = ("pipeline_success",)' in source


# ---------- signatures 第八批 ----------


def test_signature_get_git_provenance_return_annotation_dict_str_any():
    sig = inspect.signature(get_git_provenance)
    assert sig.return_annotation == dict[str, any] or sig.return_annotation == "dict[str, Any]"


def test_signature_get_dependency_versions_return_annotation():
    sig = inspect.signature(get_dependency_versions)
    # `from __future__ import annotations` 让注解成为字符串
    ra = sig.return_annotation
    assert ra == "dict[str, str | None]" or ra == dict[str, str | None]


def test_signature_build_provenance_return_annotation():
    sig = inspect.signature(build_provenance)
    ra = sig.return_annotation
    assert ra == "dict[str, Any]" or ra == dict[str, any]


def test_signature_build_devset_section_return_annotation():
    sig = inspect.signature(build_devset_section)
    ra = sig.return_annotation
    assert ra == "dict[str, Any]" or ra == dict[str, any]


def test_signature_aggregate_summary_return_annotation():
    sig = inspect.signature(aggregate_summary)
    ra = sig.return_annotation
    assert ra == "dict[str, Any]" or ra == dict[str, any]


def test_signature_get_git_provenance_param_kind_positional_or_keyword():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_get_git_provenance_param_name_project_root():
    sig = inspect.signature(get_git_provenance)
    assert "project_root" in sig.parameters


def test_signature_build_provenance_param_names():
    sig = inspect.signature(build_provenance)
    assert set(sig.parameters) == {"project_root", "parser_name", "max_chars", "parser_version"}


def test_signature_build_provenance_param_kinds():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_build_provenance_no_defaults():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_get_dependency_versions_no_params():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_signature_build_devset_section_param_name_manifest():
    sig = inspect.signature(build_devset_section)
    assert "manifest" in sig.parameters


def test_signature_build_devset_section_param_kind():
    sig = inspect.signature(build_devset_section)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_aggregate_summary_param_name_per_doc_results():
    sig = inspect.signature(aggregate_summary)
    assert "per_doc_results" in sig.parameters


def test_signature_aggregate_summary_param_kind():
    sig = inspect.signature(aggregate_summary)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_aggregate_summary_no_default():
    sig = inspect.signature(aggregate_summary)
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_signature_5_funcs_no_varargs():
    for func in (get_git_provenance, get_dependency_versions, build_provenance, build_devset_section, aggregate_summary):
        sig = inspect.signature(func)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_5_funcs_no_kwargs():
    for func in (get_git_provenance, get_dependency_versions, build_provenance, build_devset_section, aggregate_summary):
        sig = inspect.signature(func)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- module 合理性第八批 ----------


def test_module_all_attribute_present():
    assert hasattr(rmod, "__all__")


def test_module_all_is_list():
    assert isinstance(rmod.__all__, list)


def test_module_all_exact_5_items_in_order():
    assert rmod.__all__ == [
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    ]


def test_module_all_entries_unique():
    assert len(rmod.__all__) == len(set(rmod.__all__))


def test_module_all_entries_are_str():
    for name in rmod.__all__:
        assert isinstance(name, str)


def test_module_namespace_has_5_callable_functions():
    funcs = [
        n
        for n, v in vars(rmod).items()
        if callable(v) and not n.startswith("__") and getattr(v, "__module__", "") == rmod.__name__
    ]
    assert set(funcs) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_namespace_has_3_constant_tuples():
    constants = [
        n
        for n, v in vars(rmod).items()
        if not n.startswith("__") and isinstance(v, tuple) and not callable(v)
    ]
    assert set(constants) == {"_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"}


def test_module_no_user_classes():
    classes = [
        n
        for n, v in vars(rmod).items()
        if inspect.isclass(v) and v.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_docstring_present():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 50


def test_module_docstring_mentions_macro_average():
    assert "macro" in rmod.__doc__.lower()


def test_module_docstring_mentions_counts():
    assert "counts" in rmod.__doc__.lower()


def test_module_docstring_mentions_silent_drop():
    assert "silent" in rmod.__doc__.lower()


def test_module_file_ends_with_report_py():
    import os
    sep = os.sep
    assert rmod.__file__.endswith("evaluation" + sep + "report.py") or rmod.__file__.endswith(
        "evaluation/report.py"
    )


def test_module_name_is_evaluation_report():
    assert rmod.__name__ == "evaluation.report"


def test_module_has_evaluator_version_import():
    """build_provenance 引用 EVALUATOR_VERSION，应 imported。"""
    assert hasattr(rmod, "EVALUATOR_VERSION")


def test_module_has_report_version_import():
    assert hasattr(rmod, "REPORT_VERSION")


def test_module_evaluator_version_value():
    assert rmod.EVALUATOR_VERSION == EVALUATOR_VERSION


def test_module_report_version_value():
    assert rmod.REPORT_VERSION == REPORT_VERSION


# ---------- 端到端集成第八批 ----------


def test_e2e_full_chain_empty_input():
    """build_provenance + build_devset_section + aggregate_summary 全部接通。"""
    prov = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    out = aggregate_summary([])
    # 组装最小 report
    report = {
        "provenance": prov,
        "devset": build_devset_section(_StubManifest()),
        "summary": out,
        "per_doc": [],
    }
    text = json.dumps(report)
    assert '"provenance"' in text
    assert '"summary"' in text


def test_e2e_aggregate_summary_returns_json_serializable_with_full_metrics():
    docs = [
        _metrics_doc(
            {
                "schema_valid": {"value": 1.0},
                "pipeline_success": {"value": True},
                "element_count_total": {"value": 5},
                "chunk_boundary_f1": {"value": 0.7},
                "silent_drop_count": {"value": 2},
            }
        )
    ]
    out = aggregate_summary(docs)
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


def test_e2e_aggregate_summary_positional_or_keyword():
    docs = [_metrics_doc({"schema_valid": {"value": 1.0}})]
    out1 = aggregate_summary(docs)
    out2 = aggregate_summary(per_doc_results=docs)
    assert out1 == out2


def test_e2e_build_devset_section_round_trip():
    out = build_devset_section(_StubManifest())
    serialized = json.dumps(out)
    parsed = json.loads(serialized)
    assert parsed == out


def test_e2e_build_provenance_json_serializable():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


def test_e2e_aggregate_summary_4_top_keys_consistent_across_calls():
    """重复调用结构稳定。"""
    docs = [_metrics_doc({"schema_valid": {"value": 1.0}})]
    out1 = aggregate_summary(docs)
    out2 = aggregate_summary(docs)
    assert list(out1.keys()) == list(out2.keys())


def test_e2e_aggregate_summary_with_missing_metrics_for_one_doc():
    """某 doc 完全没有 metrics，仅 success_rates total 计入。"""
    docs = [
        _metrics_doc({"schema_valid": {"value": 1.0}}),
        _metrics_doc({}),
    ]
    out = aggregate_summary(docs)
    # success_rates.total 是 len(per_doc_results) = 2
    assert out["success_rates"]["pipeline_success"]["total"] == 2


def test_e2e_aggregate_summary_full_per_metric_participation():
    """每个 ratio metric 都有 participating_docs + not_evaluated + macro_average 字段。"""
    docs = [_metrics_doc({"schema_valid": {"value": 1.0}})]
    out = aggregate_summary(docs)
    for name, info in out["ratio_macro_averages"].items():
        assert "macro_average" in info
        assert "participating_docs" in info
        assert "not_evaluated" in info


def test_e2e_aggregate_summary_partial_participation_complex():
    """模拟真实场景：5 docs，部分有 chunk_boundary，部分没有。"""
    docs = [
        _metrics_doc({"chunk_boundary_f1": {"value": 0.5}, "schema_valid": {"value": 1.0}}),
        _metrics_doc({"chunk_boundary_f1": {"value": 1.0}, "schema_valid": {"value": 1.0}}),
        _metrics_doc({"chunk_boundary_f1": {"value": None}, "schema_valid": {"value": 0.0}}),
        _metrics_doc({"schema_valid": {"value": 1.0}}),
        _metrics_doc({}),
    ]
    out = aggregate_summary(docs)
    cb = out["ratio_macro_averages"]["chunk_boundary_f1"]
    assert cb["participating_docs"] == 2
    assert cb["not_evaluated"] == 3
    assert cb["macro_average"] == pytest.approx(0.75)
    sv = out["ratio_macro_averages"]["schema_valid"]
    assert sv["participating_docs"] == 4
    assert sv["not_evaluated"] == 1


def test_e2e_full_chain_with_paired_documents():
    """2 docs with full metrics + summary aggregation。"""
    docs = [
        _metrics_doc(
            {
                "schema_valid": {"value": 1.0},
                "pipeline_success": {"value": True},
                "element_count_total": {"value": 10},
                "silent_drop_count": {"value": 1},
            }
        ),
        _metrics_doc(
            {
                "schema_valid": {"value": 1.0},
                "pipeline_success": {"value": True},
                "element_count_total": {"value": 15},
                "silent_drop_count": {"value": 0},
            }
        ),
    ]
    summary = aggregate_summary(docs)
    assert summary["counts"]["element_count_total"]["sum"] == 25
    assert summary["success_rates"]["pipeline_success"]["rate"] == 1.0
    assert summary["silent_drop_total"] == 1


def test_e2e_get_dependency_versions_real_call():
    """真实调用：返回 dict 不抛异常。"""
    out = get_dependency_versions()
    assert isinstance(out, dict)
    assert len(out) == 3


def test_e2e_get_git_provenance_real_call():
    out = get_git_provenance(Path(__file__).parent.parent)
    assert "git_commit" in out
    assert "git_dirty" in out


def test_e2e_aggregate_summary_input_not_mutated_complex():
    docs = [
        _metrics_doc({"schema_valid": {"value": 1.0}}),
        _metrics_doc({"pipeline_success": {"value": True}}),
    ]
    snapshot = json.dumps(docs, default=str)
    _ = aggregate_summary(docs)
    assert json.dumps(docs, default=str) == snapshot


def test_e2e_build_provenance_with_negative_max_chars():
    """int(-800) 仍可序列化（不限制正负）。"""
    out = build_provenance(Path("."), parser_name="fallback", max_chars=-800, parser_version=None)
    assert out["max_chars"] == -800


def test_e2e_aggregate_summary_zero_participation_yields_none_macro():
    """所有 docs 都缺该 metric → macro_average=None, participating_docs=0。"""
    docs = [
        _metrics_doc({"schema_valid": {"value": None}}),
        _metrics_doc({}),
    ]
    out = aggregate_summary(docs)
    macro = out["ratio_macro_averages"]["schema_valid"]
    assert macro["macro_average"] is None
    assert macro["participating_docs"] == 0
    assert macro["not_evaluated"] == 2
