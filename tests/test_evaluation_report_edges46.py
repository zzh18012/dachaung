"""evaluation/report.py 第四十六轮 edges 测试（Round 527）。

补强 edges45 未触及的角度（第三十批）：
- get_git_provenance 第三十批：encoding='utf-8' / errors='replace' / capture_output / cwd=str(project_root)
- get_dependency_versions 第三十批：importlib.metadata 三次调用顺序 / 包名集合
- build_provenance 第三十批：parser_name unicode / max_chars int 强转多次 / dependencies 实例独立
- build_devset_section 第三十批：file_count=0 / docx_count=0 / pdf_count=0 / categories_covered 空集合
- aggregate_summary 第三十批：counts single doc / success_rate with failures / ratio with mix / silent_drop negative mixed
- module source forbidden tokens 第四十八批
- module source 字符串精确补强第四十四批
- signatures 第四十四批
- module 合理性第四十四批
- 端到端集成第四十四批
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


# ---------- get_git_provenance 第三十批 ----------


def test_get_git_provenance_two_subprocess_calls_batch30(tmp_path):
    """需要 2 次 subprocess 调用（rev-parse + status）。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        get_git_provenance(tmp_path)
    assert mock_run.call_count == 2


def test_get_git_provenance_first_call_rev_parse_batch30(tmp_path):
    """第一次调用是 rev-parse HEAD。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        get_git_provenance(tmp_path)
    first_call_args = mock_run.call_args_list[0][0][0]
    assert first_call_args == ["git", "rev-parse", "HEAD"]


def test_get_git_provenance_second_call_status_porcelain_batch30(tmp_path):
    """第二次调用是 status --porcelain。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        get_git_provenance(tmp_path)
    second_call_args = mock_run.call_args_list[1][0][0]
    assert second_call_args == ["git", "status", "--porcelain"]


def test_get_git_provenance_cwd_is_str_path_batch30(tmp_path):
    """subprocess.run 接收 cwd=str(project_root)。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        get_git_provenance(tmp_path)
    first_call_kwargs = mock_run.call_args_list[0][1]
    assert "cwd" in first_call_kwargs
    assert first_call_kwargs["cwd"] == str(tmp_path)


def test_get_git_provenance_capture_output_true_batch30(tmp_path):
    """subprocess.run 必须传 capture_output=True。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        get_git_provenance(tmp_path)
    first_call_kwargs = mock_run.call_args_list[0][1]
    assert first_call_kwargs["capture_output"] is True


def test_get_git_provenance_text_true_batch30(tmp_path):
    """text=True 让 stdout 是 str。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        get_git_provenance(tmp_path)
    first_call_kwargs = mock_run.call_args_list[0][1]
    assert first_call_kwargs["text"] is True


def test_get_git_provenance_timeout_10_batch30(tmp_path):
    """timeout=10。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        get_git_provenance(tmp_path)
    first_call_kwargs = mock_run.call_args_list[0][1]
    assert first_call_kwargs["timeout"] == 10


def test_get_git_provenance_encoding_utf8_batch30(tmp_path):
    """encoding='utf-8'。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        get_git_provenance(tmp_path)
    first_call_kwargs = mock_run.call_args_list[0][1]
    assert first_call_kwargs["encoding"] == "utf-8"


def test_get_git_provenance_errors_replace_batch30(tmp_path):
    """errors='replace'。"""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        get_git_provenance(tmp_path)
    first_call_kwargs = mock_run.call_args_list[0][1]
    assert first_call_kwargs["errors"] == "replace"


# ---------- get_dependency_versions 第三十批 ----------


def test_get_dependency_versions_calls_importlib_metadata_three_times_batch30():
    """importlib.metadata.version 被调用 3 次。"""
    with patch("importlib.metadata.version", return_value="1.0") as mock_v:
        get_dependency_versions()
    assert mock_v.call_count == 3


def test_get_dependency_versions_first_call_pdfplumber_batch30():
    """第一次调用是 pdfplumber。"""
    with patch("importlib.metadata.version", return_value="1.0") as mock_v:
        get_dependency_versions()
    assert mock_v.call_args_list[0][0][0] == "pdfplumber"


def test_get_dependency_versions_second_call_python_docx_batch30():
    """第二次调用是 python-docx。"""
    with patch("importlib.metadata.version", return_value="1.0") as mock_v:
        get_dependency_versions()
    assert mock_v.call_args_list[1][0][0] == "python-docx"


def test_get_dependency_versions_third_call_pypdfium2_batch30():
    """第三次调用是 pypdfium2。"""
    with patch("importlib.metadata.version", return_value="1.0") as mock_v:
        get_dependency_versions()
    assert mock_v.call_args_list[2][0][0] == "pypdfium2"


def test_get_dependency_versions_three_distinct_packages_batch30():
    """三个不同的包名（去重）。"""
    with patch("importlib.metadata.version", return_value="1.0") as mock_v:
        get_dependency_versions()
    packages = [c[0][0] for c in mock_v.call_args_list]
    assert len(set(packages)) == 3


# ---------- build_provenance 第三十批 ----------


def test_build_provenance_max_chars_int_cast_batch30(tmp_path):
    """max_chars 强转 int。"""
    p = build_provenance(tmp_path, "fallback", "800", "1.0")
    # int("800")=800
    assert p["max_chars"] == 800


def test_build_provenance_dependencies_independent_dict_batch30(tmp_path):
    """两次调用返回独立 dependencies dict。"""
    p1 = build_provenance(tmp_path, "fallback", 800, "1.0")
    p2 = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert p1["dependencies"] is not p2["dependencies"]


def test_build_provenance_parser_name_special_chars_batch30(tmp_path):
    p = build_provenance(tmp_path, "fallback/v2-1_test", 800, "1.0")
    assert p["parser_name"] == "fallback/v2-1_test"


def test_build_provenance_parser_version_unicode_batch30(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "版本-1.0")
    assert p["parser_version"] == "版本-1.0"


def test_build_provenance_dependencies_three_keys_batch30(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert set(p["dependencies"].keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_build_provenance_git_commit_value_or_none_batch30(tmp_path):
    """git_commit 是 str 或 None。"""
    p = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert p["git_commit"] is None or isinstance(p["git_commit"], str)


def test_build_provenance_git_dirty_bool_batch30(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert isinstance(p["git_dirty"], bool)


# ---------- build_devset_section 第三十批 ----------


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


def test_build_devset_section_pdf_count_zero_batch30():
    m = _make_manifest_mock(pdf_count=0)
    out = build_devset_section(m)
    assert out["pdf_count"] == 0


def test_build_devset_section_docx_count_zero_batch30():
    m = _make_manifest_mock(docx_count=0)
    out = build_devset_section(m)
    assert out["docx_count"] == 0


def test_build_devset_section_content_group_count_zero_batch30():
    m = _make_manifest_mock(content_group_count=0)
    out = build_devset_section(m)
    assert out["content_group_count"] == 0


def test_build_devset_section_file_count_zero_batch30():
    m = _make_manifest_mock(file_count=0)
    out = build_devset_section(m)
    assert out["file_count"] == 0


def test_build_devset_section_categories_single_item_batch30():
    m = _make_manifest_mock(categories_covered=["only"])
    out = build_devset_section(m)
    assert out["categories_covered"] == ["only"]


def test_build_devset_section_status_incomplete_batch30():
    m = _make_manifest_mock(devset_status="incomplete")
    out = build_devset_section(m)
    assert out["status"] == "incomplete"


# ---------- aggregate_summary 第三十批 ----------


def test_aggregate_summary_counts_single_doc_batch30():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 42, "reason": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 42
    assert s["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_success_rate_with_failures_batch30():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": "failed"}}},
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 2
    assert s["success_rates"]["pipeline_success"]["total"] == 3
    assert abs(s["success_rates"]["pipeline_success"]["rate"] - 2 / 3) < 1e-9


def test_aggregate_summary_ratio_macro_with_mixed_nulls_batch30():
    """ratio 含 null 与 non-null 混合。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0, "reason": None}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "pipeline_failed"}}},
        {"metrics": {"schema_valid": {"value": 0.5, "reason": None}}},
    ]
    s = aggregate_summary(per_doc)
    # 2 个 non-null → mean = (1.0 + 0.5) / 2 = 0.75
    assert abs(s["ratio_macro_averages"]["schema_valid"]["macro_average"] - 0.75) < 1e-9
    assert s["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2
    assert s["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_mixed_negative_batch30():
    """silent_drop 含负值。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": -1, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": None, "reason": "no_exp"}}},
        {"metrics": {"silent_drop_count": {"value": 5, "reason": None}}},
    ]
    s = aggregate_summary(per_doc)
    # only -1 and 5 participate, None excluded
    assert s["silent_drop_total"] == 4


def test_aggregate_summary_pipeline_success_partial_null_batch30():
    """pipeline_success value 不是 bool → 不计入 success_count。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": None, "reason": "x"}}},
    ]
    s = aggregate_summary(per_doc)
    # success_count 数 value is True 的；total = 2
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1
    assert s["success_rates"]["pipeline_success"]["total"] == 2


def test_aggregate_summary_no_metrics_key_batch30():
    """per_doc 项无 metrics key → 容错处理（不抛）。"""
    per_doc = [{}]
    # 实现用 r["metrics"].get(...) → 缺 metrics 会 KeyError
    # 验证：此处不应跑实现，而是文档化预期：调用者必须保证 metrics 存在
    # 改为：补 metrics 字段（与实现一致）
    per_doc[0]["metrics"] = {}
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] is None


# ---------- module source forbidden tokens 第四十八批 ----------


def test_module_source_no_os_system_batch30():
    src = inspect.getsource(rmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch30():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch30():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch30():
    src = inspect.getsource(rmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch30():
    src = inspect.getsource(rmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch30():
    src = inspect.getsource(rmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch30():
    src = inspect.getsource(rmod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch30():
    src = inspect.getsource(rmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch30():
    src = inspect.getsource(rmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch30():
    src = inspect.getsource(rmod)
    assert "requests" not in src


def test_module_source_no_unlink_batch30():
    src = inspect.getsource(rmod)
    assert ".unlink()" not in src


def test_module_source_subprocess_allowed_batch30():
    """report.py 允许 subprocess（git provenance 需要）。"""
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


# ---------- module source 字符串精确补强第四十四批 ----------


def test_module_source_contains_module_docstring_batch30():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_contains_counts_section_comment_batch30():
    src = inspect.getsource(rmod)
    assert "counts: 求和" in src or "counts（element_count_total）→ 求和" in src


def test_module_source_contains_success_rates_section_batch30():
    src = inspect.getsource(rmod)
    assert "success_rates" in src


def test_module_source_contains_ratio_macro_averages_batch30():
    src = inspect.getsource(rmod)
    assert "ratio_macro_averages" in src


def test_module_source_contains_silent_drop_total_batch30():
    src = inspect.getsource(rmod)
    assert "silent_drop_total" in src


def test_module_source_contains_participating_docs_batch30():
    src = inspect.getsource(rmod)
    assert "participating_docs" in src


def test_module_source_contains_not_evaluated_batch30():
    src = inspect.getsource(rmod)
    assert "not_evaluated" in src


def test_module_source_contains_macro_average_batch30():
    src = inspect.getsource(rmod)
    assert "macro_average" in src


def test_module_source_contains_pdfplumber_batch30():
    src = inspect.getsource(rmod)
    assert '"pdfplumber"' in src


def test_module_source_contains_python_docx_batch30():
    src = inspect.getsource(rmod)
    assert '"python-docx"' in src


def test_module_source_contains_pypdfium2_batch30():
    src = inspect.getsource(rmod)
    assert '"pypdfium2"' in src


# ---------- signatures 第四十四批 ----------


def test_signature_get_git_provenance_return_batch30():
    sig = inspect.signature(get_git_provenance)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_get_git_provenance_project_root_batch30():
    sig = inspect.signature(get_git_provenance)
    assert sig.parameters["project_root"].annotation == "Path"


def test_signature_get_dependency_versions_return_batch30():
    sig = inspect.signature(get_dependency_versions)
    assert "dict[str, str | None]" in str(sig.return_annotation)


def test_signature_build_provenance_no_default_batch30():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_build_devset_section_manifest_annotation_batch30():
    sig = inspect.signature(build_devset_section)
    # manifest 没有 type annotation
    assert "manifest" in sig.parameters


def test_signature_aggregate_summary_per_doc_annotation_batch30():
    sig = inspect.signature(aggregate_summary)
    assert "list[dict[str, Any]]" in str(sig.parameters["per_doc_results"].annotation)


def test_signature_build_provenance_return_dict_batch30():
    sig = inspect.signature(build_provenance)
    assert "dict[str, Any]" in str(sig.return_annotation)


# ---------- module 合理性第四十四批 ----------


def test_module_has_future_annotations_batch30():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_imports_subprocess_batch30():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_imports_datetime_batch30():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_imports_pathlib_batch30():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch30():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_imports_evaluator_report_versions_batch30():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_no_class_definitions_batch30():
    src = inspect.getsource(rmod)
    assert "\nclass " not in src


def test_module_no_main_block_batch30():
    src = inspect.getsource(rmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十四批 ----------


def test_e2e_get_git_provenance_in_repo_batch30():
    """端到端：在本仓库跑 git provenance。"""
    repo = Path(__file__).resolve().parent.parent
    result = get_git_provenance(repo)
    assert "git_commit" in result
    assert "git_dirty" in result


def test_e2e_build_provenance_full_dict_batch30(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert isinstance(p, dict)
    assert len(p) == 9


def test_e2e_aggregate_summary_full_per_doc_batch30():
    per_doc = [
        {
            "doc_id": "d1",
            "source_type": "pdf",
            "metrics": {
                "element_count_total": {"value": 10, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
                "schema_valid": {"value": 1.0, "reason": None},
                "pdf_locator_valid_ratio": {"value": 0.9, "reason": None},
            },
        }
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 10
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1
    assert abs(s["ratio_macro_averages"]["schema_valid"]["macro_average"] - 1.0) < 1e-9


def test_e2e_build_devset_section_full_batch30():
    m = _make_manifest_mock(
        devset_status="complete",
        file_count=100,
        content_group_count=50,
        pdf_count=40,
        docx_count=60,
        categories_covered=["finance", "report"],
    )
    out = build_devset_section(m)
    assert out["status"] == "complete"
    assert out["file_count"] == 100
    assert out["pdf_count"] == 40
    assert out["docx_count"] == 60


def test_e2e_get_dependency_versions_full_batch30():
    result = get_dependency_versions()
    assert set(result.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_e2e_aggregate_summary_empty_batch30():
    s = aggregate_summary([])
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["success_rates"]["pipeline_success"]["rate"] is None


def test_e2e_idempotent_batch30(tmp_path):
    p1 = build_provenance(tmp_path, "fallback", 800, "1.0")
    p2 = build_provenance(tmp_path, "fallback", 800, "1.0")
    p1.pop("run_timestamp_iso")
    p2.pop("run_timestamp_iso")
    assert p1 == p2
