"""evaluation/report.py 第四十五轮 edges 测试（Round 520）。

补强 edges44 未触及的角度（第二十九批）：
- _RATIO_METRICS 第二十九批：顺序固定 / 不含 silent_drop / 不含 figure_caption_* / 含 chunk_boundary_*
- get_git_provenance 第二十九批：commit 含换行被 strip / stderr 非空但 returncode=0 / dirty=stdout 单行 / dirty=stdout 多行 / SubprocessError 回退
- get_dependency_versions 第二十九批：返回 dict 而非 list / 顺序与代码一致 / None 与 str 共存
- build_provenance 第二十九批：int(max_chars) 强转 / parser_name 含 unicode / max_chars float / max_chars bool
- build_devset_section 第二十九批：file_count 为 0 / categories_covered 空列表 / 字符串透传
- aggregate_summary 第二十九批：counts 全 null / success_rate rate 精确 / ratio_macro single doc / silent_drop 全 null / negative silent_drop 求和
- module source forbidden tokens 第四十六批
- module source 字符串精确补强第四十二批
- signatures 第四十二批
- module 合理性第四十二批
- 端到端集成第四十二批
"""

from __future__ import annotations

import inspect
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

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


# ---------- _RATIO_METRICS 第二十九批 ----------


def test_ratio_metrics_order_fixed_batch29():
    """_RATIO_METRICS 顺序固定（tuple）。"""
    expected = (
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
    )
    assert _RATIO_METRICS == expected


def test_ratio_metrics_excludes_silent_drop_batch29():
    assert "silent_drop_count" not in _RATIO_METRICS


def test_ratio_metrics_excludes_element_count_batch29():
    assert "element_count_total" not in _RATIO_METRICS


def test_ratio_metrics_unique_batch29():
    """无重复元素。"""
    assert len(_RATIO_METRICS) == len(set(_RATIO_METRICS))


def test_count_metrics_unique_batch29():
    assert len(_COUNT_METRICS) == len(set(_COUNT_METRICS))


def test_success_bool_metrics_unique_batch29():
    assert len(_SUCCESS_BOOL_METRICS) == len(set(_SUCCESS_BOOL_METRICS))


def test_ratio_metrics_is_tuple_batch29():
    assert isinstance(_RATIO_METRICS, tuple)


def test_count_metrics_is_tuple_batch29():
    assert isinstance(_COUNT_METRICS, tuple)


def test_success_bool_metrics_is_tuple_batch29():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_ratio_metrics_contains_text_char_multiset_batch29():
    assert "text_char_multiset_precision" in _RATIO_METRICS
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_ratio_metrics_contains_image_resource_batch29():
    assert "image_resource_exists_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_reference_batch29():
    assert "chunk_reference_intact_ratio" in _RATIO_METRICS


# ---------- get_git_provenance 第二十九批 ----------


def test_get_git_provenance_commit_with_newline_stripped_batch29(tmp_path):
    """commit stdout 含换行 → strip。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] == "abc123"


def test_get_git_provenance_commit_with_trailing_spaces_stripped_batch29(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123   \n  ", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] == "abc123"


def test_get_git_provenance_stderr_nonzero_returncode_zero_batch29(tmp_path):
    """stderr 非空但 returncode=0 → commit 仍取 stdout。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr="warning"),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] == "abc"


def test_get_git_provenance_dirty_single_line_batch29(tmp_path):
    """porcelain 输出单行 → dirty=True。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout=" M file.txt\n", stderr=""),
        ]
        result = get_git_provenance(tmp_path)
    assert result["git_dirty"] is True


def test_get_git_provenance_dirty_multi_line_batch29(tmp_path):
    """porcelain 输出多行 → dirty=True。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout=" M file1\n?? file2\n", stderr=""),
        ]
        result = get_git_provenance(tmp_path)
    assert result["git_dirty"] is True


def test_get_git_provenance_subprocess_error_falls_back_batch29(tmp_path):
    """SubprocessError → except 分支。"""
    with patch("subprocess.run", side_effect=subprocess.SubprocessError("boom")):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_first_call_fails_second_succeeds_batch29(tmp_path):
    """第一次失败（returncode=1），第二次成功但 stdout 空 → commit=None, dirty=False。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="err"),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is False


def test_get_git_provenance_returns_two_keys_exactly_batch29(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = get_git_provenance(tmp_path)
    assert set(result.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_no_input_modification_batch29(tmp_path):
    """不修改 project_root。"""
    original = Path(tmp_path)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        get_git_provenance(tmp_path)
    assert tmp_path == original


# ---------- get_dependency_versions 第二十九批 ----------


def test_get_dependency_versions_returns_dict_not_list_batch29():
    result = get_dependency_versions()
    assert isinstance(result, dict)
    assert not isinstance(result, list)


def test_get_dependency_versions_keys_exact_batch29():
    result = get_dependency_versions()
    assert set(result.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_dict_iteration_order_batch29():
    """dict 的插入顺序：python 源码 tuple 的顺序。"""
    src = inspect.getsource(rmod)
    # 源码顺序：pdfplumber, python-docx, pypdfium2
    assert src.index('"pdfplumber"') < src.index('"python-docx"')
    assert src.index('"python-docx"') < src.index('"pypdfium2"')


def test_get_dependency_versions_mixed_none_and_str_batch29():
    """至少返回 3 个值，类型一致（str 或 None）。"""
    result = get_dependency_versions()
    assert len(result) == 3
    for v in result.values():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_idempotent_two_calls_batch29():
    r1 = get_dependency_versions()
    r2 = get_dependency_versions()
    assert r1 == r2


def test_get_dependency_versions_no_kwargs_leak_batch29():
    """无参数函数。"""
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


# ---------- build_provenance 第二十九批 ----------


def test_build_provenance_max_chars_float_int_batch29(tmp_path):
    """max_chars 传 float → int() 强转。"""
    p = build_provenance(tmp_path, "fallback", 800.7, "1.0")
    assert p["max_chars"] == 800
    assert isinstance(p["max_chars"], int)


def test_build_provenance_max_chars_bool_batch29(tmp_path):
    """max_chars=True → int(True)=1。"""
    p = build_provenance(tmp_path, "fallback", True, "1.0")
    assert p["max_chars"] == 1


def test_build_provenance_parser_name_unicode_batch29(tmp_path):
    p = build_provenance(tmp_path, "fallback默认", 800, "1.0")
    assert p["parser_name"] == "fallback默认"


def test_build_provenance_parser_version_empty_str_batch29(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "")
    assert p["parser_version"] == ""


def test_build_provenance_dependencies_dict_batch29(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert isinstance(p["dependencies"], dict)


def test_build_provenance_evaluator_version_correct_batch29(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert p["evaluator_version"] == "1.1"


def test_build_provenance_report_version_correct_batch29(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert p["report_version"] == "1.1"


def test_build_provenance_run_timestamp_iso_format_batch29(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0")
    ts = p["run_timestamp_iso"]
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None  # astimezone() 注入 tz


def test_build_provenance_idempotent_except_timestamp_batch29(tmp_path):
    """两次调用除 timestamp 外一致。"""
    p1 = build_provenance(tmp_path, "fallback", 800, "1.0")
    p2 = build_provenance(tmp_path, "fallback", 800, "1.0")
    p1.pop("run_timestamp_iso")
    p2.pop("run_timestamp_iso")
    assert p1 == p2


# ---------- build_devset_section 第二十九批 ----------


def _make_manifest_mock(**overrides) -> Any:
    defaults = dict(
        devset_status="incomplete",
        file_count=10,
        content_group_count=5,
        pdf_count=4,
        docx_count=6,
        categories_covered=["a", "b", "c"],
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def test_build_devset_section_categories_empty_list_batch29():
    m = _make_manifest_mock(categories_covered=[])
    out = build_devset_section(m)
    assert out["categories_covered"] == []


def test_build_devset_section_status_unicode_batch29():
    m = _make_manifest_mock(devset_status="未完成")
    out = build_devset_section(m)
    assert out["status"] == "未完成"


def test_build_devset_section_negative_counts_batch29():
    """正常 manifest 不会负数，但实现透传不校验。"""
    m = _make_manifest_mock(file_count=-1, content_group_count=-2)
    out = build_devset_section(m)
    assert out["file_count"] == -1
    assert out["content_group_count"] == -2


def test_build_devset_section_idempotent_batch29():
    m = _make_manifest_mock()
    out1 = build_devset_section(m)
    out2 = build_devset_section(m)
    assert out1 == out2


def test_build_devset_section_pdf_plus_docx_pass_through_batch29():
    m = _make_manifest_mock(pdf_count=3, docx_count=7)
    out = build_devset_section(m)
    assert out["pdf_count"] == 3
    assert out["docx_count"] == 7


# ---------- aggregate_summary 第二十九批 ----------


def test_aggregate_summary_counts_all_null_batch29():
    """所有 doc 的 element_count_total 全 null → sum=None, participating=0。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": None, "reason": "pipeline_failed"}}},
        {"metrics": {"element_count_total": {"value": None, "reason": "pipeline_failed"}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_counts_mixed_null_and_int_batch29():
    """部分 null，部分 int → 只对 int 求和。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10, "reason": None}}},
        {"metrics": {"element_count_total": {"value": None, "reason": "pipeline_failed"}}},
        {"metrics": {"element_count_total": {"value": 20, "reason": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 30
    assert s["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_success_rate_calculation_batch29():
    """success rate = successes/total。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": "failed"}}},
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 3
    assert s["success_rates"]["pipeline_success"]["total"] == 4
    assert abs(s["success_rates"]["pipeline_success"]["rate"] - 0.75) < 1e-9


def test_aggregate_summary_success_rate_zero_batch29():
    """全 False → rate=0.0。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False, "reason": "x"}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": "x"}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 0
    assert s["success_rates"]["pipeline_success"]["rate"] == 0.0


def test_aggregate_summary_ratio_single_doc_batch29():
    """单 doc → macro_average 等于该值。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert s["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert s["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_average_batch29():
    """多 doc → macro_average = mean。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
        {"metrics": {"schema_valid": {"value": 0.5, "reason": None}}},
        {"metrics": {"schema_valid": {"value": 0.0, "reason": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert abs(s["ratio_macro_averages"]["schema_valid"]["macro_average"] - 0.5) < 1e-9
    assert s["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 3


def test_aggregate_summary_ratio_all_null_batch29():
    """全 null → macro_average=None, participating=0, not_evaluated=N。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] is None
    assert s["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 0
    assert s["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 2


def test_aggregate_summary_silent_drop_negative_values_batch29():
    """负值也会被求和（实现不校验）。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": -1, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": 5, "reason": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 4


def test_aggregate_summary_silent_drop_all_null_batch29():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None, "reason": "no_expectations"}}},
        {"metrics": {"silent_drop_count": {"value": None, "reason": "no_expectations"}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] is None


def test_aggregate_summary_not_evaluated_calculation_batch29():
    """not_evaluated = total - participating。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert s["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 2


def test_aggregate_summary_no_input_modification_batch29():
    """不修改输入。"""
    import copy
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
    ]
    snapshot = copy.deepcopy(per_doc)
    aggregate_summary(per_doc)
    assert per_doc == snapshot


def test_aggregate_summary_returns_three_subsections_batch29():
    s = aggregate_summary([])
    assert "counts" in s
    assert "success_rates" in s
    assert "ratio_macro_averages" in s
    assert "silent_drop_total" in s


# ---------- module source forbidden tokens 第四十六批 ----------


def test_module_source_no_os_system_batch29():
    src = inspect.getsource(rmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch29():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch29():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch29():
    src = inspect.getsource(rmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch29():
    src = inspect.getsource(rmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch29():
    src = inspect.getsource(rmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch29():
    src = inspect.getsource(rmod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch29():
    src = inspect.getsource(rmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch29():
    src = inspect.getsource(rmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch29():
    src = inspect.getsource(rmod)
    assert "requests" not in src


def test_module_source_no_unlink_batch29():
    src = inspect.getsource(rmod)
    assert ".unlink()" not in src


def test_module_source_subprocess_allowed_batch29():
    """report.py 允许 subprocess（git provenance 需要）。"""
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


# ---------- module source 字符串精确补强第四十二批 ----------


def test_module_source_contains_module_docstring_batch29():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_contains_count_metric_comment_batch29():
    src = inspect.getsource(rmod)
    assert "counts（element_count_total）" in src


def test_module_source_contains_silent_drop_count_batch29():
    src = inspect.getsource(rmod)
    assert "silent_drop_count" in src


def test_module_source_contains_no_mixed_types_comment_batch29():
    src = inspect.getsource(rmod)
    assert "不混合类型" in src


def test_module_source_contains_subprocess_run_call_batch29():
    src = inspect.getsource(rmod)
    assert "subprocess.run" in src


def test_module_source_contains_capture_output_batch29():
    src = inspect.getsource(rmod)
    assert "capture_output=True" in src


def test_module_source_contains_encoding_utf8_batch29():
    src = inspect.getsource(rmod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_errors_replace_batch29():
    src = inspect.getsource(rmod)
    assert 'errors="replace"' in src


def test_module_source_contains_timeout_10_batch29():
    src = inspect.getsource(rmod)
    assert "timeout=10" in src


def test_module_source_contains_porcelain_batch29():
    src = inspect.getsource(rmod)
    assert "status" in src and "porcelain" in src


def test_module_source_contains_participating_docs_batch29():
    src = inspect.getsource(rmod)
    assert "participating_docs" in src


def test_module_source_contains_not_evaluated_batch29():
    src = inspect.getsource(rmod)
    assert "not_evaluated" in src


def test_module_source_contains_macro_average_batch29():
    src = inspect.getsource(rmod)
    assert "macro_average" in src


# ---------- signatures 第四十二批 ----------


def test_signature_get_git_provenance_return_dict_batch29():
    sig = inspect.signature(get_git_provenance)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_get_dependency_versions_return_dict_batch29():
    sig = inspect.signature(get_dependency_versions)
    assert "dict[str, str | None]" in str(sig.return_annotation)


def test_signature_build_provenance_return_dict_batch29():
    sig = inspect.signature(build_provenance)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_build_devset_section_return_dict_batch29():
    sig = inspect.signature(build_devset_section)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_aggregate_summary_return_dict_batch29():
    sig = inspect.signature(aggregate_summary)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_get_git_provenance_project_root_annotation_batch29():
    sig = inspect.signature(get_git_provenance)
    assert sig.parameters["project_root"].annotation == "Path"


def test_signature_build_provenance_max_chars_annotation_batch29():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["max_chars"].annotation == "int"


def test_signature_build_provenance_parser_version_annotation_batch29():
    sig = inspect.signature(build_provenance)
    assert "str | None" in str(sig.parameters["parser_version"].annotation)


def test_signature_aggregate_summary_per_doc_annotation_batch29():
    sig = inspect.signature(aggregate_summary)
    assert "list[dict[str, Any]]" in str(sig.parameters["per_doc_results"].annotation)


# ---------- module 合理性第四十二批 ----------


def test_module_has_future_annotations_batch29():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_imports_subprocess_batch29():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_imports_datetime_batch29():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_imports_pathlib_batch29():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch29():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_no_class_definitions_batch29():
    src = inspect.getsource(rmod)
    assert "\nclass " not in src


def test_module_all_contains_five_entries_batch29():
    src = inspect.getsource(rmod)
    for name in [
        '"build_provenance"',
        '"build_devset_section"',
        '"aggregate_summary"',
        '"get_git_provenance"',
        '"get_dependency_versions"',
    ]:
        assert name in src


def test_module_no_main_block_batch29():
    src = inspect.getsource(rmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十二批 ----------


def test_e2e_build_provenance_full_dict_batch29(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert isinstance(p, dict)
    assert len(p) == 9
    assert set(p.keys()) == {
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


def test_e2e_aggregate_summary_full_pilot_batch29():
    """端到端：完整 pilot 数据。"""
    per_doc = [
        {
            "doc_id": "d1",
            "source_type": "pdf",
            "metrics": {
                "element_count_total": {"value": 10, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
                "schema_valid": {"value": True, "reason": None},
                "pdf_locator_valid_ratio": {"value": 0.9, "reason": None},
                "docx_locator_valid_ratio": {"value": None, "reason": "not_docx_document"},
                "image_resource_exists_ratio": {"value": None, "reason": "no_image_elements"},
                "chunk_reference_intact_ratio": {"value": 1.0, "reason": None},
                "text_preservation_equal": {"value": True, "reason": None},
                "text_char_multiset_precision": {"value": 0.95, "reason": None},
                "text_char_multiset_recall": {"value": 0.92, "reason": None},
                "heading_boundary_compliance": {"value": None, "reason": "no_heading_elements"},
                "chunk_boundary_precision": {"value": None, "reason": "no_annotation"},
                "chunk_boundary_recall": {"value": None, "reason": "no_annotation"},
                "chunk_boundary_f1": {"value": None, "reason": "no_annotation"},
                "silent_drop_count": {"value": 1, "reason": None},
            },
        },
        {
            "doc_id": "d2",
            "source_type": "docx",
            "metrics": {
                "element_count_total": {"value": 20, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
                "schema_valid": {"value": True, "reason": None},
                "pdf_locator_valid_ratio": {"value": None, "reason": "not_pdf_document"},
                "docx_locator_valid_ratio": {"value": 0.8, "reason": None},
                "image_resource_exists_ratio": {"value": None, "reason": "no_image_elements"},
                "chunk_reference_intact_ratio": {"value": 0.9, "reason": None},
                "text_preservation_equal": {"value": False, "reason": None},
                "text_char_multiset_precision": {"value": 0.85, "reason": None},
                "text_char_multiset_recall": {"value": 0.88, "reason": None},
                "heading_boundary_compliance": {"value": 0.7, "reason": None},
                "chunk_boundary_precision": {"value": None, "reason": "no_annotation"},
                "chunk_boundary_recall": {"value": None, "reason": "no_annotation"},
                "chunk_boundary_f1": {"value": None, "reason": "no_annotation"},
                "silent_drop_count": {"value": 2, "reason": None},
            },
        },
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 30
    assert s["success_rates"]["pipeline_success"]["success_count"] == 2
    assert abs(s["ratio_macro_averages"]["text_char_multiset_precision"]["macro_average"] - 0.9) < 1e-9
    assert s["silent_drop_total"] == 3


def test_e2e_build_devset_full_roundtrip_batch29():
    m = _make_manifest_mock(
        devset_status="incomplete",
        file_count=2,
        content_group_count=1,
        pdf_count=1,
        docx_count=1,
        categories_covered=["finance"],
    )
    out = build_devset_section(m)
    assert out == {
        "status": "incomplete",
        "file_count": 2,
        "content_group_count": 1,
        "pdf_count": 1,
        "docx_count": 1,
        "categories_covered": ["finance"],
    }


def test_e2e_aggregate_summary_idempotent_batch29():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    ]
    s1 = aggregate_summary(per_doc)
    s2 = aggregate_summary(per_doc)
    assert s1 == s2


def test_e2e_get_git_provenance_real_repo_batch29(tmp_path):
    """端到端：在真实 git repo（本仓库）跑。"""
    repo_root = Path(__file__).resolve().parent.parent
    result = get_git_provenance(repo_root)
    assert "git_commit" in result
    assert "git_dirty" in result
    # 在本仓库内 rev-parse 应当成功
    assert result["git_commit"] is not None


def test_e2e_build_provenance_dependencies_three_packages_batch29(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0")
    deps = p["dependencies"]
    assert set(deps.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_e2e_aggregate_summary_empty_per_doc_batch29():
    s = aggregate_summary([])
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["counts"]["element_count_total"]["participating_docs"] == 0
    assert s["success_rates"]["pipeline_success"]["rate"] is None
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] is None
    assert s["silent_drop_total"] is None
