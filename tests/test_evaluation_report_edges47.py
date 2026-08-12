"""evaluation/report.py 第四十七轮 edges 测试（Round 534）。

补强 edges46 未触及的角度（第三十一批）：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第三十一批：唯一性 / 排序 / 不重叠 / 顺序
- get_git_provenance 第三十一批：stderr 有内容不影响 dirty / commit 失败但 status 成功 / OSError 路径 / SubprocessError 路径
- get_dependency_versions 第三十一批：返回 dict / 包名固定 / 包名唯一 / 三个键 / 值 None 或 str
- build_provenance 第三十一批：返回 dict / 9 个 key / parser_version None / run_timestamp_iso 是 iso 字符串
- build_devset_section 第三十一批：返回 dict / 6 个 key / 接受 Manifest-like 对象（鸭子类型）
- aggregate_summary 第三十一批：counts sum 累加 / success_rate rate None when total=0 / ratio macro 计算 / silent_drop_total None when no values / 包含 counts/success_rates/ratio_macro_averages/silent_drop_total 四 key
- module source forbidden tokens 第四十九批（subprocess 允许）
- module source 字符串精确补强第四十五批
- signatures 第四十五批
- module 合理性第四十五批
- 端到端集成第四十五批
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第三十一批 ----------


def test_ratio_metrics_unique_entries_batch31():
    """_RATIO_METRICS 无重复。"""
    assert len(set(_RATIO_METRICS)) == len(_RATIO_METRICS)


def test_ratio_metrics_count_twelve_batch31():
    assert len(_RATIO_METRICS) == 12


def test_count_metrics_single_entry_batch31():
    assert _COUNT_METRICS == ("element_count_total",)


def test_count_metrics_unique_batch31():
    assert len(set(_COUNT_METRICS)) == len(_COUNT_METRICS)


def test_success_bool_metrics_single_entry_batch31():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_ratio_count_success_disjoint_batch31():
    """三类指标不重叠。"""
    set_r = set(_RATIO_METRICS)
    set_c = set(_COUNT_METRICS)
    set_s = set(_SUCCESS_BOOL_METRICS)
    assert set_r & set_c == set()
    assert set_r & set_s == set()
    assert set_c & set_s == set()


def test_ratio_metrics_is_tuple_batch31():
    assert isinstance(_RATIO_METRICS, tuple)


def test_count_metrics_is_tuple_batch31():
    assert isinstance(_COUNT_METRICS, tuple)


def test_success_bool_metrics_is_tuple_batch31():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_ratio_metrics_first_is_schema_valid_batch31():
    assert _RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_includes_chunk_boundary_batch31():
    assert "chunk_boundary_precision" in _RATIO_METRICS
    assert "chunk_boundary_recall" in _RATIO_METRICS
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_excludes_figure_caption_batch31():
    """figure_caption_* 不在 _RATIO_METRICS（始终 null）。"""
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


# ---------- get_git_provenance 第三十一批 ----------


def test_get_git_provenance_stderr_not_affect_dirty_batch31(tmp_path):
    """stderr 有内容不影响 dirty 判定（dirty 看 stdout）。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr="warnings\n"),
        ]
        result = get_git_provenance(tmp_path)
    assert result["git_dirty"] is False


def test_get_git_provenance_commit_fails_status_succeeds_batch31(tmp_path):
    """rev-parse 失败但 status 成功 → commit=None, dirty 看实际。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="error"),
            MagicMock(returncode=0, stdout=" M file\n", stderr=""),
        ]
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_os_error_path_batch31(tmp_path):
    """OSError → commit=None, dirty=True。"""
    with patch("subprocess.run", side_effect=OSError("no such command")):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_subprocess_error_path_batch31(tmp_path):
    """SubprocessError → commit=None, dirty=True。"""
    with patch("subprocess.run", side_effect=subprocess.SubprocessError("timeout")):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_both_success_clean_batch31(tmp_path):
    """两次都成功且 porcelain 空 → dirty=False。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] == "abc123"
    assert result["git_dirty"] is False


def test_get_git_provenance_returns_dict_batch31(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = get_git_provenance(tmp_path)
    assert isinstance(result, dict)


def test_get_git_provenance_keys_count_batch31(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = get_git_provenance(tmp_path)
    assert len(result) == 2


# ---------- get_dependency_versions 第三十一批 ----------


def test_get_dependency_versions_returns_dict_batch31():
    result = get_dependency_versions()
    assert isinstance(result, dict)


def test_get_dependency_versions_has_three_packages_batch31():
    result = get_dependency_versions()
    assert set(result.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_type_batch31():
    """值要么是 str 要么是 None。"""
    result = get_dependency_versions()
    for v in result.values():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_idempotent_batch31():
    r1 = get_dependency_versions()
    r2 = get_dependency_versions()
    assert r1 == r2


def test_get_dependency_versions_pdfplumber_value_or_none_batch31():
    result = get_dependency_versions()
    # 测试环境中 pdfplumber 应当已安装
    assert result["pdfplumber"] is None or "." in result["pdfplumber"]


def test_get_dependency_versions_pypdfium2_value_or_none_batch31():
    result = get_dependency_versions()
    assert result["pypdfium2"] is None or "." in result["pypdfium2"]


# ---------- build_provenance 第三十一批 ----------


def test_build_provenance_keys_count_batch31(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert len(result) == 9


def test_build_provenance_keys_set_batch31(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = build_provenance(tmp_path, "fallback", 800, "1.0")
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
    assert set(result.keys()) == expected_keys


def test_build_provenance_parser_version_none_batch31(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["parser_version"] is None


def test_build_provenance_run_timestamp_iso_format_batch31(tmp_path):
    """run_timestamp_iso 是 ISO 格式字符串。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = build_provenance(tmp_path, "fallback", 800, "1.0")
    ts = result["run_timestamp_iso"]
    assert isinstance(ts, str)
    # datetime.fromisoformat 解析成功（py3.11+ 支持带时区）
    parsed = datetime.fromisoformat(ts)
    assert parsed is not None


def test_build_provenance_evaluator_version_batch31(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert result["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_batch31(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert result["report_version"] == REPORT_VERSION


def test_build_provenance_dependencies_is_dict_batch31(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert isinstance(result["dependencies"], dict)


# ---------- build_devset_section 第三十一批 ----------


def test_build_devset_section_returns_dict_batch31():
    manifest = MagicMock(
        devset_status="complete",
        file_count=0,
        content_group_count=0,
        pdf_count=0,
        docx_count=0,
        categories_covered=[],
    )
    result = build_devset_section(manifest)
    assert isinstance(result, dict)


def test_build_devset_section_keys_count_batch31():
    manifest = MagicMock(
        devset_status="complete",
        file_count=0,
        content_group_count=0,
        pdf_count=0,
        docx_count=0,
        categories_covered=[],
    )
    result = build_devset_section(manifest)
    assert len(result) == 6


def test_build_devset_section_keys_set_batch31():
    manifest = MagicMock(
        devset_status="complete",
        file_count=0,
        content_group_count=0,
        pdf_count=0,
        docx_count=0,
        categories_covered=[],
    )
    result = build_devset_section(manifest)
    expected = {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }
    assert set(result.keys()) == expected


def test_build_devset_section_passes_status_through_batch31():
    """devset_status 透传（不自行判定）。"""
    manifest = MagicMock(
        devset_status="incomplete",
        file_count=0,
        content_group_count=0,
        pdf_count=0,
        docx_count=0,
        categories_covered=[],
    )
    result = build_devset_section(manifest)
    assert result["status"] == "incomplete"


def test_build_devset_section_duck_typed_batch31():
    """build_devset_section 接受任何含必要属性的对象。"""

    class FakeManifest:
        devset_status = "complete"
        file_count = 5
        content_group_count = 2
        pdf_count = 1
        docx_count = 4
        categories_covered = ["x", "y"]

    result = build_devset_section(FakeManifest())
    assert result["file_count"] == 5
    assert result["pdf_count"] == 1
    assert result["docx_count"] == 4


# ---------- aggregate_summary 第三十一批 ----------


def test_aggregate_summary_counts_sum_accumulates_batch31():
    """counts element_count_total 多 doc 求和。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"element_count_total": {"value": 3, "reason": None}}},
        {"metrics": {"element_count_total": {"value": None, "reason": "pipeline_failed"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 8
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_success_rate_none_when_total_zero_batch31():
    """total=0 → rate=None。"""
    out = aggregate_summary([])
    assert out["success_rates"]["pipeline_success"]["rate"] is None
    assert out["success_rates"]["pipeline_success"]["total"] == 0
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0


def test_aggregate_summary_ratio_macro_calculation_batch31():
    """ratio macro 平均值。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
        {"metrics": {"schema_valid": {"value": 0.5, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    # macro = (1.0 + 0.5) / 2 = 0.75
    assert abs(out["ratio_macro_averages"]["schema_valid"]["macro_average"] - 0.75) < 1e-9
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 0


def test_aggregate_summary_silent_drop_total_none_when_no_values_batch31():
    """无 silent_drop 值 → silent_drop_total=None。"""
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_total_sum_batch31():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": 5, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_top_level_keys_batch31():
    """summary 顶层 4 个 key。"""
    out = aggregate_summary([])
    assert set(out.keys()) == {
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    }


def test_aggregate_summary_ratio_all_none_when_no_participating_batch31():
    """所有 doc 都 null → macro=None, participating=0。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] is None
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 0
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 2


def test_aggregate_summary_counts_none_when_no_values_batch31():
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_returns_dict_batch31():
    out = aggregate_summary([])
    assert isinstance(out, dict)


# ---------- module source forbidden tokens 第四十九批（subprocess 允许） ----------


def test_module_source_no_os_system_batch31():
    src = inspect.getsource(rmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch31():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch31():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch31():
    src = inspect.getsource(rmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch31():
    src = inspect.getsource(rmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch31():
    src = inspect.getsource(rmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch31():
    src = inspect.getsource(rmod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch31():
    src = inspect.getsource(rmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch31():
    src = inspect.getsource(rmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch31():
    src = inspect.getsource(rmod)
    assert "requests" not in src


def test_module_source_no_unlink_batch31():
    src = inspect.getsource(rmod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十五批 ----------


def test_module_source_contains_module_docstring_batch31():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_contains_subprocess_import_batch31():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_contains_datetime_import_batch31():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_contains_pathlib_import_batch31():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch31():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_contains_versions_import_batch31():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_contains_ratio_metrics_const_batch31():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS = (" in src


def test_module_source_contains_count_metrics_const_batch31():
    src = inspect.getsource(rmod)
    assert '_COUNT_METRICS = ("element_count_total",)' in src


def test_module_source_contains_success_bool_metrics_const_batch31():
    src = inspect.getsource(rmod)
    assert '_SUCCESS_BOOL_METRICS = ("pipeline_success",)' in src


def test_module_source_contains_get_git_provenance_func_batch31():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance" in src


def test_module_source_contains_get_dependency_versions_func_batch31():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions" in src


def test_module_source_contains_build_provenance_func_batch31():
    src = inspect.getsource(rmod)
    assert "def build_provenance" in src


def test_module_source_contains_build_devset_section_func_batch31():
    src = inspect.getsource(rmod)
    assert "def build_devset_section" in src


def test_module_source_contains_aggregate_summary_func_batch31():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary" in src


def test_module_source_contains_git_dirty_fallback_true_batch31():
    """git_dirty 默认 True（失败时也 True）。"""
    src = inspect.getsource(rmod)
    assert "dirty: bool = True" in src


def test_module_source_contains_importlib_metadata_batch31():
    src = inspect.getsource(rmod)
    assert "importlib.metadata" in src


# ---------- signatures 第四十五批 ----------


def test_signature_get_git_provenance_return_dict_batch31():
    sig = inspect.signature(get_git_provenance)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_get_git_provenance_project_root_batch31():
    sig = inspect.signature(get_git_provenance)
    assert sig.parameters["project_root"].annotation == "Path"


def test_signature_get_dependency_versions_return_batch31():
    sig = inspect.signature(get_dependency_versions)
    assert "dict[str, str | None]" in str(sig.return_annotation)


def test_signature_get_dependency_versions_no_params_batch31():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_signature_build_provenance_params_batch31():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_provenance_return_dict_batch31():
    sig = inspect.signature(build_provenance)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_build_devset_section_param_batch31():
    sig = inspect.signature(build_devset_section)
    assert "manifest" in sig.parameters


def test_signature_aggregate_summary_params_batch31():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.keys())
    assert params == ["per_doc_results"]


def test_signature_aggregate_summary_return_dict_batch31():
    sig = inspect.signature(aggregate_summary)
    assert "dict[str, Any]" in str(sig.return_annotation)


# ---------- module 合理性第四十五批 ----------


def test_module_has_future_annotations_batch31():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_imports_subprocess_batch31():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_imports_datetime_batch31():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_imports_pathlib_batch31():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch31():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_has_all_export_batch31():
    src = inspect.getsource(rmod)
    assert "__all__" in src


def test_module_all_has_five_entries_batch31():
    src = inspect.getsource(rmod)
    for name in [
        '"build_provenance"',
        '"build_devset_section"',
        '"aggregate_summary"',
        '"get_git_provenance"',
        '"get_dependency_versions"',
    ]:
        assert name in src


def test_module_no_main_block_batch31():
    src = inspect.getsource(rmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十五批 ----------


def test_e2e_build_provenance_full_run_batch31(tmp_path):
    """端到端：build_provenance 完整跑（用 mock git）。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="deadbeef\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert result["git_commit"] == "deadbeef"
    assert result["git_dirty"] is False
    assert result["max_chars"] == 800
    assert result["parser_name"] == "fallback"
    assert result["parser_version"] == "1.0"


def test_e2e_aggregate_summary_three_docs_mixed_batch31():
    """端到端：3 个 doc 混合（成功、失败、部分评估）。"""
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True, "reason": None},
                "schema_valid": {"value": True, "reason": None},
                "element_count_total": {"value": 5, "reason": None},
                "silent_drop_count": {"value": 2, "reason": None},
            }
        },
        {
            "metrics": {
                "pipeline_success": {"value": False, "reason": None},
                "schema_valid": {"value": None, "reason": "pipeline_failed"},
                "element_count_total": {"value": None, "reason": "pipeline_failed"},
                "silent_drop_count": {"value": None, "reason": "pipeline_failed"},
            }
        },
        {
            "metrics": {
                "pipeline_success": {"value": True, "reason": None},
                "schema_valid": {"value": False, "reason": None},
                "element_count_total": {"value": 3, "reason": None},
                "silent_drop_count": {"value": 0, "reason": None},
            }
        },
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 2
    assert out["success_rates"]["pipeline_success"]["total"] == 3
    assert abs(out["success_rates"]["pipeline_success"]["rate"] - 2.0 / 3.0) < 1e-9
    assert out["counts"]["element_count_total"]["sum"] == 8
    assert out["silent_drop_total"] == 2


def test_e2e_aggregate_summary_idempotent_batch31():
    """端到端：相同输入两次得到相同结果。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
    ]
    out1 = aggregate_summary(per_doc)
    out2 = aggregate_summary(per_doc)
    assert out1 == out2


def test_e2e_build_devset_section_full_batch31():
    """端到端：devset section 提取。"""
    manifest = MagicMock(
        devset_status="incomplete",
        file_count=5,
        content_group_count=2,
        pdf_count=2,
        docx_count=3,
        categories_covered=["finance", "report"],
    )
    out = build_devset_section(manifest)
    assert out["status"] == "incomplete"
    assert out["file_count"] == 5
    assert out["content_group_count"] == 2
    assert out["pdf_count"] == 2
    assert out["docx_count"] == 3
    assert out["categories_covered"] == ["finance", "report"]


def test_e2e_get_dependency_versions_no_throw_batch31():
    """端到端：get_dependency_versions 不抛错（无副作用）。"""
    result = get_dependency_versions()
    assert isinstance(result, dict)


def test_e2e_full_pipeline_provenance_to_summary_batch31(tmp_path):
    """端到端：build_provenance → aggregate_summary 串联。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        prov = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert prov["evaluator_version"] == EVALUATOR_VERSION
    summary = aggregate_summary([])
    assert "counts" in summary


def test_e2e_aggregate_summary_empty_input_batch31():
    """端到端：空 per_doc 也能聚合。"""
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["success_rates"]["pipeline_success"]["rate"] is None
    assert out["silent_drop_total"] is None
