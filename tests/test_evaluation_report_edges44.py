"""evaluation/report.py 第四十四轮 edges 测试（Round 513）。

补强 edges43 未触及的角度（第二十八批）：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第二十八批：长度 / 内容 / 顺序 / 不重叠
- get_git_provenance 第二十八批：returncode=1 / 输出空 str / timeout 异常 / OSError
- get_dependency_versions 第二十八批：返回 3 个 key / 各 key 值类型 / 多次调用独立
- build_provenance 第二十八批：max_chars=0 / max_chars=负 / parser_version=None / parser_name 空 / run_timestamp_iso 含时区
- build_devset_section 第二十八批：6 个 key / 透传 / 大数字
- aggregate_summary 第二十八批：1000 个 doc 性能 / 多 metric 同时 / counts/ratio/silent_drop 同时
- module source forbidden tokens 第四十五批（subprocess 允许）
- module source 字符串精确补强第四十一批
- signatures 第四十一批
- module 合理性第四十一批
- 端到端集成第四十一批
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


# ---------- 常量集合 第二十八批 ----------


def test_ratio_metrics_length_12_batch28():
    assert len(_RATIO_METRICS) == 12


def test_count_metrics_length_1_batch28():
    assert len(_COUNT_METRICS) == 1


def test_success_bool_metrics_length_1_batch28():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_count_metrics_value_batch28():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_value_batch28():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_ratio_metrics_contains_schema_valid_batch28():
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_contains_all_locators_batch28():
    assert "pdf_locator_valid_ratio" in _RATIO_METRICS
    assert "docx_locator_valid_ratio" in _RATIO_METRICS


def test_ratio_metrics_contains_text_preservation_equal_batch28():
    assert "text_preservation_equal" in _RATIO_METRICS


def test_ratio_metrics_contains_chunk_boundary_prf_batch28():
    assert "chunk_boundary_precision" in _RATIO_METRICS
    assert "chunk_boundary_recall" in _RATIO_METRICS
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_excludes_figure_caption_batch28():
    """figure_caption_* 不在 ratio_macro_averages（固定 null）。"""
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_count_and_success_disjoint_batch28():
    """count 与 success 指标不重叠。"""
    assert set(_COUNT_METRICS).isdisjoint(_SUCCESS_BOOL_METRICS)


def test_count_and_ratio_disjoint_batch28():
    assert set(_COUNT_METRICS).isdisjoint(_RATIO_METRICS)


def test_success_and_ratio_disjoint_batch28():
    """注意：pipeline_success 在 success_bool；schema_valid 在 ratio（也算 bool）。"""
    assert "pipeline_success" not in _RATIO_METRICS  # pipeline_success 在 success_bool


# ---------- get_git_provenance 第二十八批 ----------


def test_get_git_provenance_returncode_nonzero_commit_none_batch28(tmp_path):
    """returncode != 0 → commit=None。"""
    with patch("subprocess.run") as mock_run:
        # 第一次 rev-parse returncode=1，第二次 status returncode=0 stdout=""
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="err"),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None


def test_get_git_provenance_returncode_nonzero_dirty_false_batch28(tmp_path):
    """第二次 porcelain returncode=0 stdout 空时 dirty=False。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = get_git_provenance(tmp_path)
    assert result["git_dirty"] is False


def test_get_git_provenance_empty_stdout_commit_none_batch28(tmp_path):
    """stdout 空字符串 → commit=None。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None


def test_get_git_provenance_timeout_falls_back_batch28(tmp_path):
    """subprocess.TimeoutExpired → except 分支 → commit=None dirty=True。"""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10)):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_oserror_falls_back_batch28(tmp_path):
    """OSError → except 分支 → commit=None dirty=True。"""
    with patch("subprocess.run", side_effect=OSError("boom")):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_returns_dict_batch28(tmp_path):
    result = get_git_provenance(tmp_path)
    assert isinstance(result, dict)


def test_get_git_provenance_two_keys_batch28(tmp_path):
    """返回 dict 只含 git_commit 与 git_dirty。"""
    result = get_git_provenance(tmp_path)
    assert set(result.keys()) == {"git_commit", "git_dirty"}


# ---------- get_dependency_versions 第二十八批 ----------


def test_get_dependency_versions_three_keys_batch28():
    result = get_dependency_versions()
    assert set(result.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_pdfplumber_is_str_or_none_batch28():
    result = get_dependency_versions()
    v = result["pdfplumber"]
    assert v is None or isinstance(v, str)


def test_get_dependency_versions_docx_is_str_or_none_batch28():
    result = get_dependency_versions()
    v = result["python-docx"]
    assert v is None or isinstance(v, str)


def test_get_dependency_versions_pypdfium2_is_str_or_none_batch28():
    result = get_dependency_versions()
    v = result["pypdfium2"]
    assert v is None or isinstance(v, str)


def test_get_dependency_versions_idempotent_batch28():
    r1 = get_dependency_versions()
    r2 = get_dependency_versions()
    assert r1 == r2


def test_get_dependency_versions_package_not_found_returns_none_batch28():
    """模拟 PackageNotFoundError → None。"""
    import importlib.metadata
    with patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError):
        result = get_dependency_versions()
    assert all(v is None for v in result.values())


def test_get_dependency_versions_general_exception_returns_none_batch28():
    """模拟一般异常 → None。"""
    with patch("importlib.metadata.version", side_effect=RuntimeError):
        result = get_dependency_versions()
    assert all(v is None for v in result.values())


# ---------- build_provenance 第二十八批 ----------


def test_build_provenance_max_chars_zero_batch28(tmp_path):
    p = build_provenance(tmp_path, "fallback", 0, "1.0")
    assert p["max_chars"] == 0


def test_build_provenance_max_chars_negative_batch28(tmp_path):
    p = build_provenance(tmp_path, "fallback", -100, "1.0")
    assert p["max_chars"] == -100


def test_build_provenance_parser_version_none_batch28(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, None)
    assert p["parser_version"] is None


def test_build_provenance_parser_name_empty_batch28(tmp_path):
    p = build_provenance(tmp_path, "", 800, "1.0")
    assert p["parser_name"] == ""


def test_build_provenance_run_timestamp_has_timezone_batch28(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0")
    ts = p["run_timestamp_iso"]
    # isoformat with timezone 含 +HH:MM
    assert "+" in ts or "-" in ts[10:]  # 时区指示符（去掉日期部分）


def test_build_provenance_run_timestamp_parseable_batch28(tmp_path):
    """时间戳是合法 ISO 格式。"""
    p = build_provenance(tmp_path, "fallback", 800, "1.0")
    ts = p["run_timestamp_iso"]
    parsed = datetime.fromisoformat(ts)
    assert parsed is not None


def test_build_provenance_evaluator_version_constant_batch28(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert p["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_constant_batch28(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert p["report_version"] == REPORT_VERSION


def test_build_provenance_nine_keys_batch28(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0")
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


# ---------- build_devset_section 第二十八批 ----------


def _make_manifest_mock(**overrides) -> Any:
    """构造 Manifest mock。"""
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


def test_build_devset_section_six_keys_batch28():
    m = _make_manifest_mock()
    out = build_devset_section(m)
    assert set(out.keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_build_devset_section_status_pass_through_batch28():
    m = _make_manifest_mock(devset_status="complete")
    out = build_devset_section(m)
    assert out["status"] == "complete"


def test_build_devset_section_file_count_pass_through_batch28():
    m = _make_manifest_mock(file_count=42)
    out = build_devset_section(m)
    assert out["file_count"] == 42


def test_build_devset_section_zero_counts_batch28():
    m = _make_manifest_mock(file_count=0, content_group_count=0, pdf_count=0, docx_count=0)
    out = build_devset_section(m)
    assert out["file_count"] == 0


def test_build_devset_section_large_counts_batch28():
    m = _make_manifest_mock(file_count=10**9)
    out = build_devset_section(m)
    assert out["file_count"] == 10**9


def test_build_devset_section_categories_sorted_list_batch28():
    m = _make_manifest_mock(categories_covered=["z", "a", "m"])
    out = build_devset_section(m)
    # 实现直接透传（manifest 内已排序）
    assert out["categories_covered"] == ["z", "a", "m"]


# ---------- aggregate_summary 第二十八批 ----------


def test_aggregate_summary_1000_docs_batch28():
    """1000 个 doc 的性能。"""
    per_doc = [
        {
            "doc_id": f"d{i}",
            "source_type": "pdf",
            "metrics": {
                "element_count_total": {"value": i, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
                "schema_valid": {"value": True, "reason": None},
                "pdf_locator_valid_ratio": {"value": 1.0, "reason": None},
                "docx_locator_valid_ratio": {"value": None, "reason": "not_docx_document"},
                "image_resource_exists_ratio": {"value": None, "reason": "no_image_elements"},
                "chunk_reference_intact_ratio": {"value": 1.0, "reason": None},
                "text_preservation_equal": {"value": True, "reason": None},
                "text_char_multiset_precision": {"value": 1.0, "reason": None},
                "text_char_multiset_recall": {"value": 1.0, "reason": None},
                "heading_boundary_compliance": {"value": None, "reason": "no_heading_elements"},
                "chunk_boundary_precision": {"value": None, "reason": "no_annotation"},
                "chunk_boundary_recall": {"value": None, "reason": "no_annotation"},
                "chunk_boundary_f1": {"value": None, "reason": "no_annotation"},
                "silent_drop_count": {"value": 0, "reason": None},
            },
        }
        for i in range(1000)
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == sum(range(1000))
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1000


def test_aggregate_summary_multiple_metrics_batch28():
    per_doc = [
        {
            "metrics": {
                "element_count_total": {"value": 5, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
                "schema_valid": {"value": True, "reason": None},
                "pdf_locator_valid_ratio": {"value": 1.0, "reason": None},
                "docx_locator_valid_ratio": {"value": None, "reason": "x"},
                "image_resource_exists_ratio": {"value": None, "reason": "x"},
                "chunk_reference_intact_ratio": {"value": 1.0, "reason": None},
                "text_preservation_equal": {"value": True, "reason": None},
                "text_char_multiset_precision": {"value": 1.0, "reason": None},
                "text_char_multiset_recall": {"value": 1.0, "reason": None},
                "heading_boundary_compliance": {"value": 1.0, "reason": None},
                "chunk_boundary_precision": {"value": None, "reason": "x"},
                "chunk_boundary_recall": {"value": None, "reason": "x"},
                "chunk_boundary_f1": {"value": None, "reason": "x"},
                "silent_drop_count": {"value": 2, "reason": None},
            },
        }
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 5
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert s["silent_drop_total"] == 2


def test_aggregate_summary_empty_batch28():
    s = aggregate_summary([])
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["counts"]["element_count_total"]["participating_docs"] == 0
    assert s["success_rates"]["pipeline_success"]["success_count"] == 0
    assert s["success_rates"]["pipeline_success"]["rate"] is None
    assert s["silent_drop_total"] is None


def test_aggregate_summary_returns_dict_batch28():
    s = aggregate_summary([])
    assert isinstance(s, dict)


def test_aggregate_summary_four_top_keys_batch28():
    s = aggregate_summary([])
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_silent_drop_mixed_batch28():
    """部分 doc silent_drop_count=null 不参与。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 5, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": None, "reason": "no_expectations"}}},
        {"metrics": {"silent_drop_count": {"value": 3, "reason": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 8


# ---------- module source forbidden tokens 第四十五批 ----------


def test_module_source_no_os_system_batch28():
    src = inspect.getsource(rmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch28():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch28():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch28():
    src = inspect.getsource(rmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch28():
    src = inspect.getsource(rmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch28():
    src = inspect.getsource(rmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch28():
    src = inspect.getsource(rmod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch28():
    """report.py 不直接写文件（写盘由 runner 做）。"""
    src = inspect.getsource(rmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch28():
    src = inspect.getsource(rmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch28():
    src = inspect.getsource(rmod)
    assert "requests" not in src


def test_module_source_no_unlink_batch28():
    src = inspect.getsource(rmod)
    assert ".unlink()" not in src


def test_module_source_subprocess_allowed_batch28():
    """report.py 允许 subprocess（git provenance 需要）。"""
    src = inspect.getsource(rmod)
    assert "import subprocess" in src  # 正向断言（特殊允许）


# ---------- module source 字符串精确补强第四十一批 ----------


def test_module_source_contains_ratio_metrics_batch28():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS" in src


def test_module_source_contains_count_metrics_batch28():
    src = inspect.getsource(rmod)
    assert "_COUNT_METRICS" in src


def test_module_source_contains_success_bool_metrics_batch28():
    src = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS" in src


def test_module_source_contains_build_provenance_batch28():
    src = inspect.getsource(rmod)
    assert "def build_provenance" in src


def test_module_source_contains_build_devset_section_batch28():
    src = inspect.getsource(rmod)
    assert "def build_devset_section" in src


def test_module_source_contains_aggregate_summary_batch28():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary" in src


def test_module_source_contains_get_git_provenance_batch28():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance" in src


def test_module_source_contains_get_dependency_versions_batch28():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions" in src


def test_module_source_contains_evaluator_version_batch28():
    src = inspect.getsource(rmod)
    assert "EVALUATOR_VERSION" in src


def test_module_source_contains_report_version_batch28():
    src = inspect.getsource(rmod)
    assert "REPORT_VERSION" in src


def test_module_source_contains_importlib_metadata_batch28():
    src = inspect.getsource(rmod)
    assert "importlib.metadata" in src


def test_module_source_contains_datetime_batch28():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


# ---------- signatures 第四十一批 ----------


def test_signature_get_git_provenance_batch28():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root"]


def test_signature_build_provenance_batch28():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_get_dependency_versions_batch28():
    sig = inspect.signature(get_dependency_versions)
    params = list(sig.parameters.keys())
    assert params == []


def test_signature_aggregate_summary_batch28():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.keys())
    assert params == ["per_doc_results"]


def test_signature_build_devset_section_batch28():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.keys())
    assert params == ["manifest"]


def test_signature_build_provenance_no_default_batch28():
    """build_provenance 所有参数都是 required。"""
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


# ---------- module 合理性第四十一批 ----------


def test_module_has_future_annotations_batch28():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_imports_subprocess_batch28():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_imports_datetime_batch28():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_imports_pathlib_batch28():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch28():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_imports_evaluator_version_batch28():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_all_export_five_entries_batch28():
    src = inspect.getsource(rmod)
    for name in [
        '"build_provenance"',
        '"build_devset_section"',
        '"aggregate_summary"',
        '"get_git_provenance"',
        '"get_dependency_versions"',
    ]:
        assert name in src


def test_module_no_main_block_batch28():
    src = inspect.getsource(rmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十一批 ----------


def test_e2e_build_provenance_full_batch28(tmp_path):
    """端到端：build_provenance 跑完整流程。"""
    p = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert p["parser_name"] == "fallback"
    assert p["parser_version"] == "1.0.0"
    assert p["max_chars"] == 800
    assert isinstance(p["dependencies"], dict)


def test_e2e_build_devset_full_batch28():
    """端到端：build_devset_section 跑完整流程。"""
    m = _make_manifest_mock(
        devset_status="complete",
        file_count=10,
        content_group_count=5,
        pdf_count=4,
        docx_count=6,
        categories_covered=["x", "y"],
    )
    out = build_devset_section(m)
    assert out["status"] == "complete"
    assert out["file_count"] == 10
    assert out["categories_covered"] == ["x", "y"]


def test_e2e_aggregate_summary_with_real_metrics_batch28():
    """端到端：aggregate_summary 用接近真实的 per_doc 数据。"""
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
                "text_char_multiset_precision": {"value": 1.0, "reason": None},
                "text_char_multiset_recall": {"value": 1.0, "reason": None},
                "heading_boundary_compliance": {"value": 0.5, "reason": None},
                "chunk_boundary_precision": {"value": None, "reason": "no_annotation"},
                "chunk_boundary_recall": {"value": None, "reason": "no_annotation"},
                "chunk_boundary_f1": {"value": None, "reason": "no_annotation"},
                "silent_drop_count": {"value": 1, "reason": None},
            },
        },
        {
            "doc_id": "d2",
            "source_type": "pdf",
            "metrics": {
                "element_count_total": {"value": 20, "reason": None},
                "pipeline_success": {"value": False, "reason": None},
                "schema_valid": {"value": False, "reason": None},
                "pdf_locator_valid_ratio": {"value": None, "reason": "pipeline_failed"},
                "docx_locator_valid_ratio": {"value": None, "reason": "not_docx_document"},
                "image_resource_exists_ratio": {"value": None, "reason": "no_image_elements"},
                "chunk_reference_intact_ratio": {"value": None, "reason": "no_chunks"},
                "text_preservation_equal": {"value": False, "reason": None},
                "text_char_multiset_precision": {"value": 0.0, "reason": None},
                "text_char_multiset_recall": {"value": 0.0, "reason": None},
                "heading_boundary_compliance": {"value": None, "reason": "no_heading_elements"},
                "chunk_boundary_precision": {"value": None, "reason": "no_annotation"},
                "chunk_boundary_recall": {"value": None, "reason": "no_annotation"},
                "chunk_boundary_f1": {"value": None, "reason": "no_annotation"},
                "silent_drop_count": {"value": None, "reason": "no_expectations"},
            },
        },
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 30
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1
    assert s["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert s["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 0.9
    assert s["ratio_macro_averages"]["pdf_locator_valid_ratio"]["participating_docs"] == 1
    assert s["ratio_macro_averages"]["pdf_locator_valid_ratio"]["not_evaluated"] == 1
    assert s["silent_drop_total"] == 1


def test_e2e_get_dependency_versions_returns_dict_batch28():
    result = get_dependency_versions()
    assert isinstance(result, dict)


def test_e2e_get_git_provenance_returns_dict_batch28(tmp_path):
    result = get_git_provenance(tmp_path)
    assert "git_commit" in result
    assert "git_dirty" in result


def test_e2e_aggregate_summary_idempotent_batch28():
    """两次聚合得到相同结果。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}}
    ]
    s1 = aggregate_summary(per_doc)
    s2 = aggregate_summary(per_doc)
    assert s1 == s2


def test_e2e_no_side_effects_batch28():
    """调用不修改输入。"""
    import copy
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}}
    ]
    before = copy.deepcopy(per_doc)
    aggregate_summary(per_doc)
    assert per_doc == before
