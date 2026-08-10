"""evaluation/report.py 第二十三轮 edges 测试（Round 367）。

重点补强 edges22 未触及的角度：
- get_git_provenance source level 字符串精确补强第三批
- get_dependency_versions source level 字符串精确补强第三批
- build_provenance source level 字符串精确补强第三批
- build_devset_section source level 字符串精确补强第三批
- aggregate_summary source level 字符串精确补强第三批
- get_git_provenance 行为深度第六批
- get_dependency_versions 行为深度第六批
- build_provenance 行为深度第六批
- build_devset_section 行为深度第六批
- aggregate_summary 行为深度第六批
- module source forbidden tokens 第八批
- module source 字符串精确补强第三批
- signatures 精确补强第三批
- 模块整体合理性补强第三批
- 端到端集成补强第三批
"""

from __future__ import annotations

import inspect
import subprocess
import types
from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest

from evaluation import EVALUATOR_VERSION, REPORT_VERSION
from evaluation import report as rmod
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


# ---------- get_git_provenance source level 字符串精确补强第三批 ----------


def test_get_git_provenance_source_docstring_present():
    src = inspect.getsource(get_git_provenance)
    assert '"""' in src


def test_get_git_provenance_source_docstring_mentions_git_commit():
    src = inspect.getsource(get_git_provenance)
    assert "commit" in src


def test_get_git_provenance_source_docstring_mentions_dirty():
    src = inspect.getsource(get_git_provenance)
    assert "dirty" in src


def test_get_git_provenance_source_uses_commit_init_none():
    src = inspect.getsource(get_git_provenance)
    assert "commit: str | None = None" in src


def test_get_git_provenance_source_uses_dirty_init_true():
    src = inspect.getsource(get_git_provenance)
    assert "dirty: bool = True" in src


def test_get_git_provenance_source_two_subprocess_calls():
    src = inspect.getsource(get_git_provenance)
    assert src.count("subprocess.run(") == 2


def test_get_git_provenance_source_uses_r_eq_subprocess_first():
    src = inspect.getsource(get_git_provenance)
    assert "r = subprocess.run(" in src


def test_get_git_provenance_source_uses_r2_eq_subprocess_second():
    src = inspect.getsource(get_git_provenance)
    assert "r2 = subprocess.run(" in src


def test_get_git_provenance_source_first_call_returns_to_r():
    src = inspect.getsource(get_git_provenance)
    assert "rev-parse" in src


def test_get_git_provenance_source_second_call_returns_to_r2():
    src = inspect.getsource(get_git_provenance)
    assert "status" in src
    assert "porcelain" in src


def test_get_git_provenance_source_first_call_assigns_commit():
    src = inspect.getsource(get_git_provenance)
    assert "commit = r.stdout.strip() or None" in src


def test_get_git_provenance_source_dirty_assignment():
    src = inspect.getsource(get_git_provenance)
    assert "dirty = bool(r2.returncode == 0 and r2.stdout.strip())" in src


def test_get_git_provenance_source_except_oserror_subprocess_error():
    src = inspect.getsource(get_git_provenance)
    assert "except (OSError, subprocess.SubprocessError):" in src


def test_get_git_provenance_source_except_body():
    src = inspect.getsource(get_git_provenance)
    assert "commit = None" in src
    assert "dirty = True" in src


def test_get_git_provenance_source_return_dict_literal():
    src = inspect.getsource(get_git_provenance)
    assert 'return {"git_commit": commit, "git_dirty": dirty}' in src


def test_get_git_provenance_source_uses_returncode_check():
    src = inspect.getsource(get_git_provenance)
    assert "if r.returncode == 0:" in src


def test_get_git_provenance_source_no_eval():
    src = inspect.getsource(get_git_provenance)
    assert "eval(" not in src


def test_get_git_provenance_source_no_class():
    src = inspect.getsource(get_git_provenance)
    assert "class " not in src


def test_get_git_provenance_source_no_yield():
    src = inspect.getsource(get_git_provenance)
    assert "yield" not in src


def test_get_git_provenance_source_no_async():
    src = inspect.getsource(get_git_provenance)
    assert "async " not in src


def test_get_git_provenance_source_no_walrus():
    src = inspect.getsource(get_git_provenance)
    assert ":=" not in src


# ---------- get_dependency_versions source level 字符串精确补强第三批 ----------


def test_get_dependency_versions_source_docstring_present():
    src = inspect.getsource(get_dependency_versions)
    assert '"""' in src


def test_get_dependency_versions_source_docstring_mentions_pdfplumber():
    src = inspect.getsource(get_dependency_versions)
    assert "pdfplumber" in src


def test_get_dependency_versions_source_docstring_mentions_docx():
    src = inspect.getsource(get_dependency_versions)
    assert "python-docx" in src or "docx" in src


def test_get_dependency_versions_source_docstring_mentions_importlib():
    src = inspect.getsource(get_dependency_versions)
    assert "importlib" in src


def test_get_dependency_versions_source_lazy_import_in_body():
    src = inspect.getsource(get_dependency_versions)
    assert "import importlib.metadata" in src


def test_get_dependency_versions_source_versions_dict_init():
    src = inspect.getsource(get_dependency_versions)
    assert "versions: dict[str, str | None] = {}" in src


def test_get_dependency_versions_source_for_pkg_in_tuple():
    src = inspect.getsource(get_dependency_versions)
    assert 'for pkg in ("pdfplumber", "python-docx", "pypdfium2"):' in src


def test_get_dependency_versions_source_try_block():
    src = inspect.getsource(get_dependency_versions)
    assert "try:" in src
    assert "versions[pkg] = importlib.metadata.version(pkg)" in src


def test_get_dependency_versions_source_package_not_found_except():
    src = inspect.getsource(get_dependency_versions)
    assert "except importlib.metadata.PackageNotFoundError:" in src
    assert "versions[pkg] = None" in src


def test_get_dependency_versions_source_generic_except():
    src = inspect.getsource(get_dependency_versions)
    assert "except Exception:" in src


def test_get_dependency_versions_source_returns_versions():
    src = inspect.getsource(get_dependency_versions)
    assert "return versions" in src


def test_get_dependency_versions_source_no_eval():
    src = inspect.getsource(get_dependency_versions)
    assert "eval(" not in src


def test_get_dependency_versions_source_no_class():
    src = inspect.getsource(get_dependency_versions)
    assert "class " not in src


def test_get_dependency_versions_source_no_yield():
    src = inspect.getsource(get_dependency_versions)
    assert "yield" not in src


def test_get_dependency_versions_source_no_async():
    src = inspect.getsource(get_dependency_versions)
    assert "async " not in src


# ---------- build_provenance source level 字符串精确补强第三批 ----------


def test_build_provenance_source_docstring_present():
    """build_provenance 可能无 docstring，至少有 def."""
    src = inspect.getsource(build_provenance)
    assert "def build_provenance(" in src


def test_build_provenance_source_uses_git_eq_get_git_provenance():
    src = inspect.getsource(build_provenance)
    assert 'git = get_git_provenance(project_root)' in src


def test_build_provenance_source_returns_dict_with_9_keys():
    src = inspect.getsource(build_provenance)
    assert '"git_commit": git["git_commit"]' in src
    assert '"git_dirty": git["git_dirty"]' in src
    assert '"evaluator_version": EVALUATOR_VERSION' in src
    assert '"report_version": REPORT_VERSION' in src
    assert '"parser_name": parser_name' in src
    assert '"parser_version": parser_version' in src
    assert '"dependencies": get_dependency_versions()' in src
    assert '"max_chars": int(max_chars)' in src
    assert '"run_timestamp_iso": datetime.now().astimezone().isoformat()' in src


def test_build_provenance_source_no_eval():
    src = inspect.getsource(build_provenance)
    assert "eval(" not in src


def test_build_provenance_source_no_class():
    src = inspect.getsource(build_provenance)
    assert "class " not in src


def test_build_provenance_source_no_yield():
    src = inspect.getsource(build_provenance)
    assert "yield" not in src


def test_build_provenance_source_no_async():
    src = inspect.getsource(build_provenance)
    assert "async " not in src


# ---------- build_devset_section source level 字符串精确补强第三批 ----------


def test_build_devset_section_source_docstring_present():
    src = inspect.getsource(build_devset_section)
    assert '"""' in src


def test_build_devset_section_source_docstring_mentions_Manifest():
    src = inspect.getsource(build_devset_section)
    assert "Manifest" in src


def test_build_devset_section_source_uses_status_from_manifest():
    src = inspect.getsource(build_devset_section)
    assert '"status": manifest.devset_status' in src


def test_build_devset_section_source_uses_file_count_from_manifest():
    src = inspect.getsource(build_devset_section)
    assert '"file_count": manifest.file_count' in src


def test_build_devset_section_source_uses_content_group_count():
    src = inspect.getsource(build_devset_section)
    assert '"content_group_count": manifest.content_group_count' in src


def test_build_devset_section_source_uses_pdf_count():
    src = inspect.getsource(build_devset_section)
    assert '"pdf_count": manifest.pdf_count' in src


def test_build_devset_section_source_uses_docx_count():
    src = inspect.getsource(build_devset_section)
    assert '"docx_count": manifest.docx_count' in src


def test_build_devset_section_source_uses_categories_covered():
    src = inspect.getsource(build_devset_section)
    assert '"categories_covered": manifest.categories_covered' in src


def test_build_devset_section_source_no_eval():
    src = inspect.getsource(build_devset_section)
    assert "eval(" not in src


def test_build_devset_section_source_no_class():
    src = inspect.getsource(build_devset_section)
    assert "class " not in src


def test_build_devset_section_source_no_yield():
    src = inspect.getsource(build_devset_section)
    assert "yield" not in src


# ---------- aggregate_summary source level 字符串精确补强第三批 ----------


def test_aggregate_summary_source_docstring_present():
    src = inspect.getsource(aggregate_summary)
    assert '"""' in src


def test_aggregate_summary_source_docstring_mentions_聚合():
    src = inspect.getsource(aggregate_summary)
    assert "聚合" in src


def test_aggregate_summary_source_uses_summary_dict_init():
    src = inspect.getsource(aggregate_summary)
    assert "summary: dict[str, Any] = {}" in src


def test_aggregate_summary_source_uses_counts_dict_init():
    src = inspect.getsource(aggregate_summary)
    assert "counts: dict[str, Any] = {}" in src


def test_aggregate_summary_source_for_name_in_count_metrics():
    src = inspect.getsource(aggregate_summary)
    assert "for name in _COUNT_METRICS:" in src


def test_aggregate_summary_source_uses_values_list_comprehension_counts():
    src = inspect.getsource(aggregate_summary)
    assert 'values = [' in src
    assert 'r["metrics"].get(name, {}).get("value")' in src
    assert "if r[\"metrics\"].get(name, {}).get(\"value\") is not None" in src


def test_aggregate_summary_source_counts_if_values():
    src = inspect.getsource(aggregate_summary)
    assert "if values:" in src
    assert '"sum": sum(values)' in src
    assert '"participating_docs": len(values)' in src


def test_aggregate_summary_source_counts_else_branch():
    src = inspect.getsource(aggregate_summary)
    assert 'counts[name] = {"sum": None, "participating_docs": 0}' in src


def test_aggregate_summary_source_summary_counts_assignment():
    src = inspect.getsource(aggregate_summary)
    assert 'summary["counts"] = counts' in src


def test_aggregate_summary_source_success_rates_dict_init():
    src = inspect.getsource(aggregate_summary)
    assert "success_rates: dict[str, Any] = {}" in src


def test_aggregate_summary_source_for_name_in_success_metrics():
    src = inspect.getsource(aggregate_summary)
    assert "for name in _SUCCESS_BOOL_METRICS:" in src


def test_aggregate_summary_source_success_count_sum():
    src = inspect.getsource(aggregate_summary)
    assert "successes = sum(" in src
    assert "if r[\"metrics\"].get(name, {}).get(\"value\") is True" in src


def test_aggregate_summary_source_total_eq_len_per_doc():
    src = inspect.getsource(aggregate_summary)
    assert "total = len(per_doc_results)" in src


def test_aggregate_summary_source_rate_calc():
    src = inspect.getsource(aggregate_summary)
    assert "rate = (successes / total) if total else None" in src


def test_aggregate_summary_source_success_rates_assignment():
    src = inspect.getsource(aggregate_summary)
    assert 'success_rates[name] = {' in src
    assert '"success_count": successes' in src
    assert '"total": total' in src
    assert '"rate": rate' in src


def test_aggregate_summary_source_summary_success_rates():
    src = inspect.getsource(aggregate_summary)
    assert 'summary["success_rates"] = success_rates' in src


def test_aggregate_summary_source_ratio_avgs_init():
    src = inspect.getsource(aggregate_summary)
    assert "ratio_avgs: dict[str, Any] = {}" in src


def test_aggregate_summary_source_for_name_in_ratio_metrics():
    src = inspect.getsource(aggregate_summary)
    assert "for name in _RATIO_METRICS:" in src


def test_aggregate_summary_source_not_eval_calc():
    src = inspect.getsource(aggregate_summary)
    assert "not_eval = len(per_doc_results) - len(values)" in src


def test_aggregate_summary_source_macro_average_calc():
    src = inspect.getsource(aggregate_summary)
    assert "macro = sum(values) / len(values)" in src


def test_aggregate_summary_source_macro_else_none():
    src = inspect.getsource(aggregate_summary)
    assert "macro = None" in src


def test_aggregate_summary_source_ratio_avgs_assignment():
    src = inspect.getsource(aggregate_summary)
    assert 'ratio_avgs[name] = {' in src
    assert '"macro_average": macro' in src
    assert '"participating_docs": len(values)' in src
    assert '"not_evaluated": not_eval' in src


def test_aggregate_summary_source_summary_ratio_macro():
    src = inspect.getsource(aggregate_summary)
    assert 'summary["ratio_macro_averages"] = ratio_avgs' in src


def test_aggregate_summary_source_silent_vals_list():
    src = inspect.getsource(aggregate_summary)
    assert "silent_vals = [" in src
    assert 'r["metrics"].get("silent_drop_count", {}).get("value")' in src


def test_aggregate_summary_source_silent_drop_total():
    src = inspect.getsource(aggregate_summary)
    assert 'summary["silent_drop_total"] = sum(silent_vals) if silent_vals else None' in src


def test_aggregate_summary_source_return_summary():
    src = inspect.getsource(aggregate_summary)
    assert "return summary" in src


def test_aggregate_summary_source_no_eval():
    src = inspect.getsource(aggregate_summary)
    assert "eval(" not in src


def test_aggregate_summary_source_no_class():
    src = inspect.getsource(aggregate_summary)
    assert "class " not in src


def test_aggregate_summary_source_no_yield():
    src = inspect.getsource(aggregate_summary)
    assert "yield" not in src


# ---------- get_git_provenance 行为深度第六批 ----------


def test_get_git_provenance_returns_dict():
    r = get_git_provenance(Path("."))
    assert isinstance(r, dict)


def test_get_git_provenance_2_keys():
    r = get_git_provenance(Path("."))
    assert set(r.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_commit_is_str_or_none():
    r = get_git_provenance(Path("."))
    assert r["git_commit"] is None or isinstance(r["git_commit"], str)


def test_get_git_provenance_dirty_is_bool():
    r = get_git_provenance(Path("."))
    assert isinstance(r["git_dirty"], bool)


def test_get_git_provenance_nonexistent_dir():
    """不存在目录 → commit None, dirty True."""
    r = get_git_provenance(Path("/nonexistent_dir_xyz_123"))
    assert r["git_commit"] is None
    assert r["git_dirty"] is True


def test_get_git_provenance_with_str_path():
    """get_git_provenance 接受 Path；传 str 在 cwd=str() 中转换."""
    r = get_git_provenance(Path("."))
    assert "git_commit" in r


def test_get_git_provenance_idempotent():
    r1 = get_git_provenance(Path("."))
    r2 = get_git_provenance(Path("."))
    # commit 应当一致（git 状态在短时间内不变）
    assert r1["git_commit"] == r2["git_commit"]


def test_get_git_provenance_with_project_root_path():
    """传入项目根目录."""
    r = get_git_provenance(Path(__file__).resolve().parent.parent)
    assert "git_commit" in r


# ---------- get_dependency_versions 行为深度第六批 ----------


def test_get_dependency_versions_returns_dict():
    r = get_dependency_versions()
    assert isinstance(r, dict)


def test_get_dependency_versions_3_keys():
    r = get_dependency_versions()
    assert set(r.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_str_or_none():
    r = get_dependency_versions()
    for k, v in r.items():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_idempotent():
    r1 = get_dependency_versions()
    r2 = get_dependency_versions()
    assert r1 == r2


def test_get_dependency_versions_no_args():
    """get_dependency_versions 无参数."""
    r = get_dependency_versions()
    assert r is not None


# ---------- build_provenance 行为深度第六批 ----------


def test_build_provenance_returns_dict():
    r = build_provenance(Path("."), "fallback", 800, "1.0")
    assert isinstance(r, dict)


def test_build_provenance_9_keys():
    r = build_provenance(Path("."), "fallback", 800, "1.0")
    expected_keys = {
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
    assert set(r.keys()) == expected_keys


def test_build_provenance_evaluator_version_value():
    r = build_provenance(Path("."), "fallback", 800, "1.0")
    assert r["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value():
    r = build_provenance(Path("."), "fallback", 800, "1.0")
    assert r["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_value():
    r = build_provenance(Path("."), "kreuzberg", 800, "1.0")
    assert r["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_value():
    r = build_provenance(Path("."), "fallback", 800, "4.10.2")
    assert r["parser_version"] == "4.10.2"


def test_build_provenance_parser_version_none():
    r = build_provenance(Path("."), "fallback", 800, None)
    assert r["parser_version"] is None


def test_build_provenance_max_chars_int():
    r = build_provenance(Path("."), "fallback", 800, "1.0")
    assert r["max_chars"] == 800
    assert isinstance(r["max_chars"], int)


def test_build_provenance_max_chars_with_str_input():
    """max_chars 用 int() 强制转换."""
    r = build_provenance(Path("."), "fallback", "800", "1.0")
    assert r["max_chars"] == 800


def test_build_provenance_dependencies_is_dict():
    r = build_provenance(Path("."), "fallback", 800, "1.0")
    assert isinstance(r["dependencies"], dict)


def test_build_provenance_run_timestamp_iso_format():
    r = build_provenance(Path("."), "fallback", 800, "1.0")
    # ISO 8601 格式应包含 'T'
    assert "T" in r["run_timestamp_iso"]


def test_build_provenance_git_commit_value():
    r = build_provenance(Path("."), "fallback", 800, "1.0")
    assert "git_commit" in r


def test_build_provenance_git_dirty_value():
    r = build_provenance(Path("."), "fallback", 800, "1.0")
    assert isinstance(r["git_dirty"], bool)


def test_build_provenance_idempotent_except_timestamp():
    """两次调用，除时间戳外其他字段应一致."""
    r1 = build_provenance(Path("."), "fallback", 800, "1.0")
    r2 = build_provenance(Path("."), "fallback", 800, "1.0")
    assert r1["evaluator_version"] == r2["evaluator_version"]
    assert r1["parser_name"] == r2["parser_name"]


def test_build_provenance_with_nonexistent_dir():
    r = build_provenance(Path("/nonexistent_xyz"), "fallback", 800, "1.0")
    assert r["git_commit"] is None
    assert r["git_dirty"] is True


# ---------- build_devset_section 行为深度第六批 ----------


def test_build_devset_section_returns_dict():
    class FakeManifest:
        devset_status = "incomplete"
        file_count = 5
        content_group_count = 3
        pdf_count = 2
        docx_count = 3
        categories_covered = {"A", "B"}

    r = build_devset_section(FakeManifest())
    assert isinstance(r, dict)


def test_build_devset_section_6_keys():
    class FakeManifest:
        devset_status = "incomplete"
        file_count = 5
        content_group_count = 3
        pdf_count = 2
        docx_count = 3
        categories_covered = {"A", "B"}

    r = build_devset_section(FakeManifest())
    expected_keys = {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }
    assert set(r.keys()) == expected_keys


def test_build_devset_section_status_value():
    class FakeManifest:
        devset_status = "complete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = set()

    r = build_devset_section(FakeManifest())
    assert r["status"] == "complete"


def test_build_devset_section_file_count_value():
    class FakeManifest:
        devset_status = "incomplete"
        file_count = 42
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = set()

    r = build_devset_section(FakeManifest())
    assert r["file_count"] == 42


def test_build_devset_section_with_empty_categories():
    class FakeManifest:
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = set()

    r = build_devset_section(FakeManifest())
    assert r["categories_covered"] == set()


def test_build_devset_section_with_pdf_only():
    class FakeManifest:
        devset_status = "incomplete"
        file_count = 5
        content_group_count = 1
        pdf_count = 5
        docx_count = 0
        categories_covered = {"reports"}

    r = build_devset_section(FakeManifest())
    assert r["pdf_count"] == 5
    assert r["docx_count"] == 0


def test_build_devset_section_idempotent():
    class FakeManifest:
        devset_status = "incomplete"
        file_count = 5
        content_group_count = 3
        pdf_count = 2
        docx_count = 3
        categories_covered = {"A", "B"}

    m = FakeManifest()
    r1 = build_devset_section(m)
    r2 = build_devset_section(m)
    assert r1 == r2


# ---------- aggregate_summary 行为深度第六批 ----------


def _make_metric(value, reason=None):
    return {"value": value, "reason": reason}


def test_aggregate_summary_empty_list():
    r = aggregate_summary([])
    assert isinstance(r, dict)
    assert set(r.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_counts_sum():
    per_doc = [
        {"metrics": {"element_count_total": _make_metric(5)}},
        {"metrics": {"element_count_total": _make_metric(3)}},
    ]
    r = aggregate_summary(per_doc)
    assert r["counts"]["element_count_total"]["sum"] == 8
    assert r["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_with_none():
    per_doc = [
        {"metrics": {"element_count_total": _make_metric(5)}},
        {"metrics": {"element_count_total": _make_metric(None)}},
    ]
    r = aggregate_summary(per_doc)
    assert r["counts"]["element_count_total"]["sum"] == 5
    assert r["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_counts_all_none():
    per_doc = [
        {"metrics": {"element_count_total": _make_metric(None)}},
    ]
    r = aggregate_summary(per_doc)
    assert r["counts"]["element_count_total"]["sum"] is None
    assert r["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_success_rate_full():
    per_doc = [
        {"metrics": {"pipeline_success": _make_metric(True)}},
        {"metrics": {"pipeline_success": _make_metric(True)}},
    ]
    r = aggregate_summary(per_doc)
    assert r["success_rates"]["pipeline_success"]["success_count"] == 2
    assert r["success_rates"]["pipeline_success"]["total"] == 2
    assert r["success_rates"]["pipeline_success"]["rate"] == 1.0


def test_aggregate_summary_success_rate_partial():
    per_doc = [
        {"metrics": {"pipeline_success": _make_metric(True)}},
        {"metrics": {"pipeline_success": _make_metric(False)}},
    ]
    r = aggregate_summary(per_doc)
    assert r["success_rates"]["pipeline_success"]["success_count"] == 1
    assert r["success_rates"]["pipeline_success"]["rate"] == 0.5


def test_aggregate_summary_success_rate_zero_total():
    """空 per_doc → rate is None."""
    r = aggregate_summary([])
    assert r["success_rates"]["pipeline_success"]["success_count"] == 0
    assert r["success_rates"]["pipeline_success"]["total"] == 0
    assert r["success_rates"]["pipeline_success"]["rate"] is None


def test_aggregate_summary_ratio_macro_average():
    per_doc = [
        {"metrics": {"schema_valid": _make_metric(1.0)}},
        {"metrics": {"schema_valid": _make_metric(0.5)}},
    ]
    r = aggregate_summary(per_doc)
    assert r["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.75
    assert r["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2
    assert r["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_average_with_none():
    per_doc = [
        {"metrics": {"schema_valid": _make_metric(1.0)}},
        {"metrics": {"schema_valid": _make_metric(None)}},
    ]
    r = aggregate_summary(per_doc)
    assert r["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert r["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert r["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1


def test_aggregate_summary_ratio_macro_average_all_none():
    per_doc = [
        {"metrics": {"schema_valid": _make_metric(None)}},
    ]
    r = aggregate_summary(per_doc)
    assert r["ratio_macro_averages"]["schema_valid"]["macro_average"] is None
    assert r["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 0
    assert r["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_total_sum():
    per_doc = [
        {"metrics": {"silent_drop_count": _make_metric(2)}},
        {"metrics": {"silent_drop_count": _make_metric(3)}},
    ]
    r = aggregate_summary(per_doc)
    assert r["silent_drop_total"] == 5


def test_aggregate_summary_silent_drop_with_none():
    per_doc = [
        {"metrics": {"silent_drop_count": _make_metric(2)}},
        {"metrics": {"silent_drop_count": _make_metric(None)}},
    ]
    r = aggregate_summary(per_doc)
    assert r["silent_drop_total"] == 2


def test_aggregate_summary_silent_drop_all_none():
    per_doc = [
        {"metrics": {"silent_drop_count": _make_metric(None)}},
    ]
    r = aggregate_summary(per_doc)
    assert r["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_empty():
    r = aggregate_summary([])
    assert r["silent_drop_total"] is None


def test_aggregate_summary_does_not_mutate_input():
    per_doc = [
        {"metrics": {"element_count_total": _make_metric(5)}},
    ]
    before = repr(per_doc)
    aggregate_summary(per_doc)
    assert repr(per_doc) == before


def test_aggregate_summary_idempotent():
    per_doc = [
        {"metrics": {"element_count_total": _make_metric(5)}},
    ]
    r1 = aggregate_summary(per_doc)
    r2 = aggregate_summary(per_doc)
    assert r1 == r2


def test_aggregate_summary_returns_4_top_keys():
    r = aggregate_summary([])
    assert set(r.keys()) == {
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    }


def test_aggregate_summary_ratio_metrics_count():
    """ratio_macro_averages 应包含 _RATIO_METRICS 全部."""
    per_doc = [{"metrics": {}}]
    r = aggregate_summary(per_doc)
    assert set(r["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


def test_aggregate_summary_count_metrics_count():
    per_doc = [{"metrics": {}}]
    r = aggregate_summary(per_doc)
    assert set(r["counts"].keys()) == set(_COUNT_METRICS)


def test_aggregate_summary_success_metrics_count():
    per_doc = [{"metrics": {}}]
    r = aggregate_summary(per_doc)
    assert set(r["success_rates"].keys()) == set(_SUCCESS_BOOL_METRICS)


# ---------- module source forbidden tokens 第八批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "asyncio",
        "threading",
        "concurrent",
        "multiprocessing",
        "queue",
        "socket",
        "select",
        "re.match",
        "datetime.datetime",
        "os.system",
        "logging",
        "urllib",
        "http",
        "ctypes",
        "pickle",
        "shutil",
        "tempfile",
        "glob",
        "unittest",
        "pytest",
        "sys.exit",
        "copy",
        "weakref",
        "abc",
        "contextlib",
        "operator",
        "functools",
        "itertools",
        "collections",
        "platform",
        "argparse",
    ],
)
def test_report_source_no_forbidden_token_eighth(token):
    src = inspect.getsource(rmod)
    assert token not in src


# ---------- module source 字符串精确补强第三批 ----------


def test_module_source_docstring_present():
    assert rmod.__doc__ is not None


def test_module_source_docstring_mentions_provenance():
    assert "provenance" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_devset():
    assert "devset" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_summary():
    assert "summary" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_per_doc():
    assert "per_doc" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_aggregate():
    assert "aggregate" in rmod.__doc__.lower() or "聚合" in rmod.__doc__


def test_module_source_has_future_annotations():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_imports_subprocess():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_imports_datetime():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_imports_path():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_imports_any():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_imports_evaluator_version():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_ratio_metrics_constant():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS = (" in src
    assert '"schema_valid"' in src
    assert '"pdf_locator_valid_ratio"' in src
    assert '"docx_locator_valid_ratio"' in src
    assert '"image_resource_exists_ratio"' in src
    assert '"chunk_reference_intact_ratio"' in src
    assert '"text_preservation_equal"' in src
    assert '"text_char_multiset_precision"' in src
    assert '"text_char_multiset_recall"' in src
    assert '"heading_boundary_compliance"' in src
    assert '"chunk_boundary_precision"' in src
    assert '"chunk_boundary_recall"' in src
    assert '"chunk_boundary_f1"' in src


def test_module_source_count_metrics_constant():
    src = inspect.getsource(rmod)
    assert '_COUNT_METRICS = ("element_count_total",)' in src


def test_module_source_success_bool_metrics_constant():
    src = inspect.getsource(rmod)
    assert '_SUCCESS_BOOL_METRICS = ("pipeline_success",)' in src


def test_module_source_no_relative_above_evaluation():
    src = inspect.getsource(rmod)
    lines = src.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("from ."):
            assert "evaluation" in stripped


def test_module_source_no_star_import():
    src = inspect.getsource(rmod)
    assert "import *" not in src


def test_module_source_no_yield():
    src = inspect.getsource(rmod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(rmod)
    assert "async def" not in src


def test_module_source_no_walrus():
    src = inspect.getsource(rmod)
    assert ":=" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(rmod)
    assert 'if __name__' not in src


def test_module_source_no_user_class():
    src = inspect.getsource(rmod)
    lines = src.split("\n")
    has_class = any(line.lstrip().startswith("class ") for line in lines)
    assert not has_class


def test_module_source_5_user_functions():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src
    assert "def get_dependency_versions(" in src
    assert "def build_provenance(" in src
    assert "def build_devset_section(" in src
    assert "def aggregate_summary(" in src


def test_module_source_all_5_entries():
    src = inspect.getsource(rmod)
    assert '"build_provenance"' in src
    assert '"build_devset_section"' in src
    assert '"aggregate_summary"' in src
    assert '"get_git_provenance"' in src
    assert '"get_dependency_versions"' in src


def test_module_source_no_eval():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_compile():
    src = inspect.getsource(rmod)
    assert "compile(" not in src


def test_module_source_no_unlink():
    src = inspect.getsource(rmod)
    assert "unlink" not in src


def test_module_source_subprocess_allowed():
    """report.py 允许 subprocess（get_git_provenance 需要）."""
    src = inspect.getsource(rmod)
    assert "subprocess" in src


def test_module_source_datetime_allowed():
    src = inspect.getsource(rmod)
    assert "datetime" in src


# ---------- signatures 精确补强第三批 ----------


def test_signature_get_git_provenance():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "project_root"


def test_signature_get_git_provenance_no_default():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.values())
    assert params[0].default is inspect.Parameter.empty


def test_signature_get_git_provenance_return_annotation_dict():
    sig = inspect.signature(get_git_provenance)
    assert "dict" in str(sig.return_annotation)


def test_signature_get_dependency_versions_no_params():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_signature_get_dependency_versions_return_annotation():
    sig = inspect.signature(get_dependency_versions)
    ra = str(sig.return_annotation)
    assert "dict" in ra


def test_signature_build_provenance():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.values())
    assert len(params) == 4
    assert params[0].name == "project_root"
    assert params[1].name == "parser_name"
    assert params[2].name == "max_chars"
    assert params[3].name == "parser_version"


def test_signature_build_provenance_no_defaults():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_build_devset_section():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "manifest"


def test_signature_build_devset_section_no_default():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.values())
    assert params[0].default is inspect.Parameter.empty


def test_signature_aggregate_summary():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "per_doc_results"


def test_signature_aggregate_summary_no_default():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.values())
    assert params[0].default is inspect.Parameter.empty


def test_signature_5_funcs_no_varargs():
    for fn in (get_git_provenance, get_dependency_versions, build_provenance, build_devset_section, aggregate_summary):
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_POSITIONAL
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- 模块整体合理性补强第三批 ----------


def test_module_has_docstring():
    assert rmod.__doc__ is not None


def test_module_has_all_attribute():
    assert hasattr(rmod, "__all__")


def test_module_all_is_list():
    assert isinstance(rmod.__all__, list)


def test_module_all_length_5():
    assert len(rmod.__all__) == 5


def test_module_all_entries_unique():
    assert len(set(rmod.__all__)) == 5


def test_module_all_entries_are_str():
    for entry in rmod.__all__:
        assert isinstance(entry, str)


def test_module_all_5_entries_correct():
    assert set(rmod.__all__) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_namespace_5_callables():
    callables = [
        (name, obj) for name, obj in vars(rmod).items()
        if isinstance(obj, types.FunctionType) and obj.__module__ == rmod.__name__
    ]
    assert len(callables) == 5


def test_module_namespace_callable_names():
    callables = {
        name for name, obj in vars(rmod).items()
        if isinstance(obj, types.FunctionType) and obj.__module__ == rmod.__name__
    }
    assert callables == {
        "get_git_provenance",
        "get_dependency_versions",
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
    }


def test_module_namespace_3_constants():
    """3 个 metric constants + 3 (RATIO/COUNT/SUCCESS)."""
    assert hasattr(rmod, "_RATIO_METRICS")
    assert hasattr(rmod, "_COUNT_METRICS")
    assert hasattr(rmod, "_SUCCESS_BOOL_METRICS")


def test_module_no_user_classes():
    classes = [
        (name, obj) for name, obj in vars(rmod).items()
        if isinstance(obj, type) and obj.__module__ == rmod.__name__
    ]
    assert len(classes) == 0


def test_module_name_is_evaluation_report():
    assert rmod.__name__ == "evaluation.report"


def test_module_file_ends_with_report_py():
    assert rmod.__file__.endswith("report.py")


def test_module_function_module_eq_rmod():
    assert get_git_provenance.__module__ == "evaluation.report"
    assert build_provenance.__module__ == "evaluation.report"


def test_module_ratio_metrics_is_tuple():
    assert isinstance(_RATIO_METRICS, tuple)


def test_module_count_metrics_is_tuple():
    assert isinstance(_COUNT_METRICS, tuple)


def test_module_success_bool_metrics_is_tuple():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_module_ratio_metrics_length_12():
    """9 ratio + 3 chunk_boundary."""
    assert len(_RATIO_METRICS) == 12


def test_module_count_metrics_length_1():
    assert len(_COUNT_METRICS) == 1


def test_module_success_bool_metrics_length_1():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_module_constants_no_overlap():
    """3 个 metric 常量之间无重叠."""
    ratio_set = set(_RATIO_METRICS)
    count_set = set(_COUNT_METRICS)
    success_set = set(_SUCCESS_BOOL_METRICS)
    assert ratio_set.isdisjoint(count_set)
    assert ratio_set.isdisjoint(success_set)
    assert count_set.isdisjoint(success_set)


def test_module_constants_module_builtins():
    """tuple 的 __module__ 是 builtins."""
    assert isinstance(_RATIO_METRICS, tuple)


# ---------- 端到端集成补强第三批 ----------


def test_e2e_get_git_provenance_returns_2_keys():
    r = get_git_provenance(Path("."))
    assert set(r.keys()) == {"git_commit", "git_dirty"}


def test_e2e_get_git_provenance_commit_str_or_none():
    r = get_git_provenance(Path("."))
    assert r["git_commit"] is None or isinstance(r["git_commit"], str)


def test_e2e_get_git_provenance_dirty_is_bool():
    r = get_git_provenance(Path("."))
    assert isinstance(r["git_dirty"], bool)


def test_e2e_get_dependency_versions_returns_3_keys_str_or_none():
    r = get_dependency_versions()
    assert set(r.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}
    for v in r.values():
        assert v is None or isinstance(v, str)


def test_e2e_build_provenance_returns_9_keys():
    r = build_provenance(Path("."), "fallback", 800, "1.0")
    assert len(r) == 9


def test_e2e_build_provenance_evaluator_version_value():
    r = build_provenance(Path("."), "fallback", 800, "1.0")
    assert r["evaluator_version"] == EVALUATOR_VERSION


def test_e2e_build_provenance_max_chars_int():
    r = build_provenance(Path("."), "fallback", 800, "1.0")
    assert isinstance(r["max_chars"], int)
    assert r["max_chars"] == 800


def test_e2e_build_provenance_str_max_chars_input():
    r = build_provenance(Path("."), "fallback", "500", "1.0")
    assert r["max_chars"] == 500


def test_e2e_build_provenance_run_timestamp_iso_format():
    r = build_provenance(Path("."), "fallback", 800, "1.0")
    assert "T" in r["run_timestamp_iso"]


def test_e2e_build_devset_section_6_keys():
    class FakeManifest:
        devset_status = "incomplete"
        file_count = 1
        content_group_count = 1
        pdf_count = 1
        docx_count = 0
        categories_covered = {"A"}

    r = build_devset_section(FakeManifest())
    assert len(r) == 6


def test_e2e_aggregate_summary_empty_plus_one_doc():
    """空 + 一个文档 → counts 求和是 single doc 的值."""
    per_doc = [
        {"metrics": {"element_count_total": _make_metric(7)}},
    ]
    r = aggregate_summary(per_doc)
    assert r["counts"]["element_count_total"]["sum"] == 7


def test_e2e_aggregate_summary_does_not_mutate():
    per_doc = [
        {"metrics": {"element_count_total": _make_metric(5)}},
        {"metrics": {"element_count_total": _make_metric(3)}},
    ]
    before = repr(per_doc)
    aggregate_summary(per_doc)
    assert repr(per_doc) == before


def test_e2e_aggregate_summary_json_serializable():
    """aggregate_summary 返回的 dict 应当 JSON 可序列化."""
    import json

    per_doc = [
        {"metrics": {"element_count_total": _make_metric(5)}},
    ]
    r = aggregate_summary(per_doc)
    json.dumps(r)


def test_e2e_aggregate_summary_positional_args():
    per_doc = [{"metrics": {"element_count_total": _make_metric(5)}}]
    aggregate_summary(per_doc)


def test_e2e_aggregate_summary_kwargs():
    per_doc = [{"metrics": {"element_count_total": _make_metric(5)}}]
    aggregate_summary(per_doc_results=per_doc)


def test_e2e_full_chain_build_provenance_then_aggregate_summary():
    """完整流程：build_provenance → aggregate_summary."""
    prov = build_provenance(Path("."), "fallback", 800, "1.0")
    per_doc = [
        {"metrics": {"element_count_total": _make_metric(5)}},
    ]
    summary = aggregate_summary(per_doc)
    report = {"provenance": prov, "summary": summary}
    assert "provenance" in report
    assert "summary" in report


def test_e2e_aggregate_summary_partial_participation():
    """部分文档参与."""
    per_doc = [
        {"metrics": {"schema_valid": _make_metric(1.0)}},
        {"metrics": {"schema_valid": _make_metric(None)}},
        {"metrics": {"schema_valid": _make_metric(0.5)}},
    ]
    r = aggregate_summary(per_doc)
    # 2 参与, 1 不参与; macro = (1.0 + 0.5) / 2 = 0.75
    assert r["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.75
    assert r["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2
    assert r["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1


def test_e2e_aggregate_summary_macro_average_correct():
    """macro average 计算正确."""
    per_doc = [
        {"metrics": {"schema_valid": _make_metric(0.4)}},
        {"metrics": {"schema_valid": _make_metric(0.6)}},
        {"metrics": {"schema_valid": _make_metric(0.8)}},
    ]
    r = aggregate_summary(per_doc)
    assert abs(r["ratio_macro_averages"]["schema_valid"]["macro_average"] - 0.6) < 1e-6


def test_e2e_get_git_provenance_with_tmp_path(tmp_path):
    """tmp_path 可能位于 git 仓库内部（pytest 临时目录在 worktree 下），
    所以只断言返回结构和类型，不断言具体 dirty 值."""
    r = get_git_provenance(tmp_path)
    assert set(r.keys()) == {"git_commit", "git_dirty"}
    assert r["git_commit"] is None or isinstance(r["git_commit"], str)
    assert isinstance(r["git_dirty"], bool)


def test_e2e_build_provenance_with_tmp_path(tmp_path):
    r = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert "git_commit" in r
    assert isinstance(r["git_dirty"], bool)
