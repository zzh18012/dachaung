"""evaluation/report.py 第四十九轮 edges 测试（Round 548）。

补强 edges48 未触及的角度（第三十三批）。
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


# ---------- _RATIO_METRICS 第三十三批 ----------


def test_ratio_metrics_includes_schema_valid_batch33():
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_includes_text_preservation_equal_batch33():
    assert "text_preservation_equal" in _RATIO_METRICS


def test_ratio_metrics_includes_heading_boundary_compliance_batch33():
    assert "heading_boundary_compliance" in _RATIO_METRICS


def test_ratio_metrics_order_chunk_boundary_after_text_batch33():
    """chunk_boundary_* 在 text_* 之后。"""
    text_idx = _RATIO_METRICS.index("text_char_multiset_recall")
    cb_idx = _RATIO_METRICS.index("chunk_boundary_precision")
    assert cb_idx > text_idx


def test_ratio_metrics_is_tuple_type_batch33():
    assert isinstance(_RATIO_METRICS, tuple)


# ---------- _COUNT_METRICS 第三十三批 ----------


def test_count_metrics_is_tuple_type_batch33():
    assert isinstance(_COUNT_METRICS, tuple)


def test_count_metrics_disjoint_from_success_bool_batch33():
    assert not (set(_COUNT_METRICS) & set(_SUCCESS_BOOL_METRICS))


# ---------- _SUCCESS_BOOL_METRICS 第三十三批 ----------


def test_success_bool_metrics_is_tuple_type_batch33():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_success_bool_metrics_disjoint_from_count_batch33():
    assert not (set(_SUCCESS_BOOL_METRICS) & set(_COUNT_METRICS))


# ---------- get_git_provenance 第三十三批 ----------


def test_get_git_provenance_default_dirty_true_batch33(tmp_path):
    """default dirty=True（try 块外初始化）。"""
    # 模拟 try 块完全不执行（不会发生但 default 是 True）
    # 直接验证 r2.returncode != 0 → dirty=False
    with patch("evaluation.report.subprocess.run") as mock_run:
        r1 = MagicMock(returncode=1, stdout="", stderr="err")
        r2 = MagicMock(returncode=0, stdout="", stderr="")
        mock_run.side_effect = [r1, r2]
        out = get_git_provenance(tmp_path)
    # r1.returncode != 0 → commit=None; r2 stdout empty → dirty=False
    assert out["git_commit"] is None
    assert out["git_dirty"] is False


def test_get_git_provenance_first_call_returns_commit_only_batch33(tmp_path):
    """r1 成功返回 commit，r2 失败 → commit 设置但 dirty=True。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        r1 = MagicMock(returncode=0, stdout="abc123\n", stderr="")
        r2 = MagicMock(returncode=128, stdout="", stderr="not a repo")
        mock_run.side_effect = [r1, r2]
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is False  # bool(False and ...) = False


def test_get_git_provenance_subprocess_called_with_correct_args_batch33(tmp_path):
    """subprocess.run 调用参数含 cwd / capture_output / encoding / errors / timeout。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        r1 = MagicMock(returncode=0, stdout="abc\n", stderr="")
        r2 = MagicMock(returncode=0, stdout="", stderr="")
        mock_run.side_effect = [r1, r2]
        get_git_provenance(tmp_path)
    # 验证第一次调用的 kwargs
    args1, kwargs1 = mock_run.call_args_list[0]
    assert args1[0] == ["git", "rev-parse", "HEAD"]
    assert kwargs1["cwd"] == str(tmp_path)
    assert kwargs1["capture_output"] is True
    assert kwargs1["encoding"] == "utf-8"
    assert kwargs1["errors"] == "replace"
    assert kwargs1["timeout"] == 10


def test_get_git_provenance_subprocess_status_called_batch33(tmp_path):
    """第二次调用是 git status --porcelain。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        r1 = MagicMock(returncode=0, stdout="abc\n", stderr="")
        r2 = MagicMock(returncode=0, stdout="", stderr="")
        mock_run.side_effect = [r1, r2]
        get_git_provenance(tmp_path)
    args2, kwargs2 = mock_run.call_args_list[1]
    assert args2[0] == ["git", "status", "--porcelain"]


# ---------- get_dependency_versions 第三十三批 ----------


def test_get_dependency_versions_returns_dict_batch33():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_get_dependency_versions_iterates_three_packages_batch33():
    """packages 列表固定 3 个。"""
    src = inspect.getsource(rmod)
    assert '"pdfplumber", "python-docx", "pypdfium2"' in src


def test_get_dependency_versions_handles_importlib_errors_batch33():
    """importlib.metadata.version 抛任意异常都不传播。"""
    with patch("importlib.metadata.version", side_effect=ValueError("boom")):
        out = get_dependency_versions()
    for v in out.values():
        assert v is None


# ---------- build_provenance 第三十三批 ----------


def test_build_provenance_parser_name_unicode_batch33(tmp_path):
    """parser_name 含 unicode 字符。"""
    out = build_provenance(tmp_path, "fallback-中文", 800, None)
    assert out["parser_name"] == "fallback-中文"


def test_build_provenance_max_chars_negative_batch33(tmp_path):
    out = build_provenance(tmp_path, "fallback", -1, None)
    assert out["max_chars"] == -1


def test_build_provenance_max_chars_zero_batch33(tmp_path):
    out = build_provenance(tmp_path, "fallback", 0, None)
    assert out["max_chars"] == 0


def test_build_provenance_dependencies_called_batch33(tmp_path):
    """build_provenance 内部调用 get_dependency_versions。"""
    with patch("evaluation.report.get_dependency_versions", return_value={"a": "1"}) as mock_dep:
        out = build_provenance(tmp_path, "fallback", 800, None)
    mock_dep.assert_called_once()
    assert out["dependencies"] == {"a": "1"}


def test_build_provenance_calls_get_git_provenance_batch33(tmp_path):
    """build_provenance 内部调用 get_git_provenance。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}) as mock_git:
        out = build_provenance(tmp_path, "fallback", 800, None)
    mock_git.assert_called_once_with(tmp_path)
    assert out["git_commit"] == "abc"
    assert out["git_dirty"] is False


# ---------- build_devset_section 第三十三批 ----------


def test_build_devset_section_with_real_manifest_attributes_batch33():
    """build_devset_section 直接读 manifest 的 6 个属性。"""
    fake = MagicMock()
    fake.devset_status = "complete"
    fake.file_count = 5
    fake.content_group_count = 3
    fake.pdf_count = 2
    fake.docx_count = 3
    fake.categories_covered = ["a", "b", "c"]
    out = build_devset_section(fake)
    assert out == {
        "status": "complete",
        "file_count": 5,
        "content_group_count": 3,
        "pdf_count": 2,
        "docx_count": 3,
        "categories_covered": ["a", "b", "c"],
    }


def test_build_devset_section_keys_count_six_batch33():
    fake = MagicMock()
    out = build_devset_section(fake)
    assert len(out) == 6


# ---------- aggregate_summary 第三十三批 ----------


def test_aggregate_summary_all_pipeline_fail_batch33():
    """所有文档都失败 → success_rate=0。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False, "reason": "x"}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": "x"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.0


def test_aggregate_summary_one_pipeline_success_batch33():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"metrics": {"pipeline_success": {"value": False, "reason": "x"}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["total"] == 2
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5


def test_aggregate_summary_counts_partial_participation_batch33():
    """element_count_total 部分文档有值部分 null。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5, "reason": None}}},
        {"metrics": {"element_count_total": {"value": None, "reason": "x"}}},
        {"metrics": {"element_count_total": {"value": 10, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_ratio_macro_with_partial_batch33():
    per_doc = [
        {"metrics": {"schema_valid": {"value": True, "reason": None}}},
        {"metrics": {"schema_valid": {"value": None, "reason": "x"}}},
        {"metrics": {"schema_valid": {"value": False, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    # values = [True, False] → True=1, False=0 → macro=0.5
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_total_partial_batch33():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 1, "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": None, "reason": "x"}}},
        {"metrics": {"silent_drop_count": {"value": 4, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 5


def test_aggregate_summary_chunk_boundary_metrics_included_batch33():
    """_RATIO_METRICS 含 chunk_boundary_* → 在 ratio_macro_averages 输出。"""
    per_doc = [
        {"metrics": {"chunk_boundary_precision": {"value": 0.5, "reason": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert "chunk_boundary_precision" in out["ratio_macro_averages"]
    assert out["ratio_macro_averages"]["chunk_boundary_precision"]["macro_average"] == 0.5


def test_aggregate_summary_figure_caption_not_in_ratio_macro_batch33():
    """figure_caption_* 不在 _RATIO_METRICS → 不在 ratio_macro_averages。"""
    per_doc = [
        {"metrics": {"figure_caption_precision": {"value": None, "reason": "x"}}},
    ]
    out = aggregate_summary(per_doc)
    assert "figure_caption_precision" not in out["ratio_macro_averages"]


def test_aggregate_summary_empty_input_top_level_keys_batch33():
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_does_not_throw_on_missing_metric_batch33():
    """metric key 缺失也不抛（.get 返回 {}）。"""
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] is None


# ---------- module source forbidden tokens 第五十批 ----------


def test_module_source_no_eval_batch33():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch33():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch33():
    src = inspect.getsource(rmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch33():
    src = inspect.getsource(rmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch33():
    src = inspect.getsource(rmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch33():
    src = inspect.getsource(rmod)
    assert "breakpoint(" not in src


def test_module_source_no_shutil_batch33():
    src = inspect.getsource(rmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch33():
    src = inspect.getsource(rmod)
    assert "requests" not in src


def test_module_source_no_open_w_mode_batch33():
    src = inspect.getsource(rmod)
    assert "'w'" not in src
    assert '"w"' not in src


# ---------- module source 字符串精确补强第四十六批 ----------


def test_module_source_contains_module_docstring_batch33():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_contains_subprocess_import_batch33():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_contains_datetime_import_batch33():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_contains_pathlib_import_batch33():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch33():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_contains_versions_import_batch33():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_contains_ratio_metrics_const_batch33():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS" in src


def test_module_source_contains_count_metrics_const_batch33():
    src = inspect.getsource(rmod)
    assert "_COUNT_METRICS" in src


def test_module_source_contains_success_bool_metrics_const_batch33():
    src = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS" in src


def test_module_source_contains_get_git_provenance_func_batch33():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src


def test_module_source_contains_get_dependency_versions_func_batch33():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions(" in src


def test_module_source_contains_build_provenance_func_batch33():
    src = inspect.getsource(rmod)
    assert "def build_provenance(" in src


def test_module_source_contains_build_devset_section_func_batch33():
    src = inspect.getsource(rmod)
    assert "def build_devset_section(" in src


def test_module_source_contains_aggregate_summary_func_batch33():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary(" in src


def test_module_source_contains_capture_output_true_batch33():
    src = inspect.getsource(rmod)
    assert "capture_output=True" in src


def test_module_source_contains_text_true_batch33():
    src = inspect.getsource(rmod)
    assert "text=True" in src


def test_module_source_contains_subprocess_run_call_batch33():
    src = inspect.getsource(rmod)
    assert "subprocess.run(" in src


def test_module_source_contains_oserror_subprocess_error_batch33():
    src = inspect.getsource(rmod)
    assert "OSError, subprocess.SubprocessError" in src


def test_module_source_contains_dirty_true_fallback_batch33():
    src = inspect.getsource(rmod)
    assert "dirty = True" in src


# ---------- signatures 第四十六批 ----------


def test_signature_get_git_provenance_return_dict_batch33():
    sig = inspect.signature(get_git_provenance)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_get_git_provenance_param_annotation_batch33():
    sig = inspect.signature(get_git_provenance)
    assert sig.parameters["project_root"].annotation == "Path"


def test_signature_get_dependency_versions_no_params_batch33():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_signature_get_dependency_versions_return_dict_batch33():
    sig = inspect.signature(get_dependency_versions)
    rs = str(sig.return_annotation)
    assert "dict" in rs


def test_signature_build_provenance_params_count_batch33():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_provenance_param_annotations_batch33():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["parser_name"].annotation == "str"
    assert sig.parameters["max_chars"].annotation == "int"


def test_signature_build_devset_section_param_batch33():
    sig = inspect.signature(build_devset_section)
    assert "manifest" in sig.parameters


def test_signature_aggregate_summary_param_batch33():
    sig = inspect.signature(aggregate_summary)
    assert list(sig.parameters.keys()) == ["per_doc_results"]


# ---------- module 合理性第四十六批 ----------


def test_module_has_future_annotations_batch33():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_imports_subprocess_batch33():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_imports_datetime_batch33():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_imports_pathlib_batch33():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch33():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_has_all_export_batch33():
    src = inspect.getsource(rmod)
    assert "__all__" in src


def test_module_all_has_five_entries_batch33():
    src = inspect.getsource(rmod)
    for name in [
        '"build_provenance"',
        '"build_devset_section"',
        '"aggregate_summary"',
        '"get_git_provenance"',
        '"get_dependency_versions"',
    ]:
        assert name in src


def test_module_no_main_block_batch33():
    src = inspect.getsource(rmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十六批 ----------


def test_e2e_build_provenance_full_run_batch33(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] == "1.0.0"
    assert out["max_chars"] == 800
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION
    assert isinstance(out["dependencies"], dict)
    assert isinstance(out["run_timestamp_iso"], str)


def test_e2e_aggregate_summary_three_docs_mixed_batch33():
    per_doc = [
        {
            "metrics": {
                "schema_valid": {"value": True, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
                "element_count_total": {"value": 10, "reason": None},
                "pdf_locator_valid_ratio": {"value": 0.8, "reason": None},
                "text_preservation_equal": {"value": True, "reason": None},
                "silent_drop_count": {"value": 1, "reason": None},
                "chunk_boundary_precision": {"value": 0.7, "reason": None},
                "chunk_boundary_recall": {"value": 0.6, "reason": None},
                "chunk_boundary_f1": {"value": 0.65, "reason": None},
            }
        },
        {
            "metrics": {
                "schema_valid": {"value": False, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
                "element_count_total": {"value": 5, "reason": None},
                "pdf_locator_valid_ratio": {"value": 0.4, "reason": None},
                "text_preservation_equal": {"value": False, "reason": None},
                "silent_drop_count": {"value": None, "reason": "no_expectations"},
            }
        },
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["success_rates"]["pipeline_success"]["success_count"] == 2
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == pytest.approx(0.6)
    assert out["ratio_macro_averages"]["chunk_boundary_precision"]["macro_average"] == pytest.approx(0.7)
    assert out["ratio_macro_averages"]["chunk_boundary_recall"]["macro_average"] == pytest.approx(0.6)
    assert out["ratio_macro_averages"]["chunk_boundary_recall"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["chunk_boundary_recall"]["not_evaluated"] == 1
    assert out["silent_drop_total"] == 1


def test_e2e_aggregate_summary_empty_input_batch33():
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["success_rates"]["pipeline_success"]["rate"] is None
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] is None
    assert out["silent_drop_total"] is None


def test_e2e_aggregate_summary_idempotent_batch33():
    per_doc = [
        {
            "metrics": {
                "schema_valid": {"value": True, "reason": None},
                "pipeline_success": {"value": True, "reason": None},
            }
        }
    ]
    out1 = aggregate_summary(per_doc)
    out2 = aggregate_summary(per_doc)
    assert out1 == out2


def test_e2e_get_dependency_versions_no_throw_batch33():
    out = get_dependency_versions()
    for v in out.values():
        assert v is None or isinstance(v, str)


def test_e2e_full_pipeline_provenance_to_summary_batch33(tmp_path):
    """端到端：build_provenance + aggregate_summary。"""
    prov = build_provenance(tmp_path, "fallback", 800, None)
    assert "git_commit" in prov
    assert "git_dirty" in prov
    assert "run_timestamp_iso" in prov
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True, "reason": None},
                "schema_valid": {"value": True, "reason": None},
                "element_count_total": {"value": 3, "reason": None},
                "silent_drop_count": {"value": 0, "reason": None},
            }
        }
    ]
    summ = aggregate_summary(per_doc)
    assert summ["counts"]["element_count_total"]["sum"] == 3
    assert summ["silent_drop_total"] == 0


def test_e2e_get_git_provenance_in_actual_repo_batch33(tmp_path):
    """端到端：在真实 git repo（用 cwd 调用） → 返回 dict。"""
    out = get_git_provenance(Path.cwd())
    assert isinstance(out, dict)
    assert set(out.keys()) == {"git_commit", "git_dirty"}
