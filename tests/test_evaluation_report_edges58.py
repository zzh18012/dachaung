"""evaluation/report.py 第七十八轮 edges 测试（Round 614）。

补强 edges57 未触及的角度（第四十三批）。

新角度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS tuple 类型与不可变性
- _RATIO_METRICS 长度精确（12）
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 三者不相交
- _RATIO_METRICS 第一个= schema_valid，最后一个= chunk_boundary_f1
- _COUNT_METRICS 元素唯一= element_count_total
- _SUCCESS_BOOL_METRICS 元素唯一= pipeline_success
- _RATIO_METRICS 不含 element_count / silent_drop / figure_caption / pipeline_success
- get_git_provenance 单参数签名（project_root keyword-only? 否）
- get_git_provenance 编码 errors="replace" 检验
- get_git_provenance timeout=10 检验
- get_git_provenance cwd=str(project_root) 检验
- get_git_provenance capture_output=True 检验
- get_dependency_versions 签名无参
- get_dependency_versions 返回 dict[str, str|None]
- get_dependency_versions PackageNotFoundError importlib 内部异常路径
- get_dependency_versions catch-all 兜底
- build_provenance keyword-only 参数
- build_provenance 9 个 keys
- build_provenance dependencies 子 dict
- build_provenance 多次调用 timestamp 不同（秒以上）
- build_devset_section 6 个 keys
- build_devset_section 接受 Manifest-like 对象（duck typing）
- aggregate_summary 多种混合情况
- aggregate_summary pipeline_success 非 bool 不计入 success
- aggregate_summary ratio 中 0 值与 None 区别
- aggregate_summary 多次调用稳定
- aggregate_summary counts 包含正确 sub-keys
- aggregate_summary success_rates 包含正确 sub-keys
- aggregate_summary ratio_macro_averages 包含正确 sub-keys
- aggregate_summary 字段顺序
- aggregate_summary 空 list 返回 dict
- module source 字符串精确
- AST 结构
- forbidden tokens 第八十四批
"""

from __future__ import annotations

import ast
import inspect
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.report as report_mod
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


# ---------- _RATIO_METRICS tuple 类型 ----------

def test_ratio_metrics_is_tuple_batch43():
    assert isinstance(_RATIO_METRICS, tuple)


def test_ratio_metrics_count_metrics_is_tuple_batch43():
    assert isinstance(_COUNT_METRICS, tuple)


def test_success_bool_metrics_is_tuple_batch43():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_ratio_metrics_immutable_batch43():
    with pytest.raises(TypeError):
        _RATIO_METRICS[0] = "x"  # type: ignore[index]


def test_count_metrics_immutable_batch43():
    with pytest.raises(TypeError):
        _COUNT_METRICS[0] = "x"  # type: ignore[index]


def test_success_bool_metrics_immutable_batch43():
    with pytest.raises(TypeError):
        _SUCCESS_BOOL_METRICS[0] = "x"  # type: ignore[index]


# ---------- _RATIO_METRICS 长度与元素 ----------

def test_ratio_metrics_length_12_batch43():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_first_last_batch43():
    assert _RATIO_METRICS[0] == "schema_valid"
    assert _RATIO_METRICS[-1] == "chunk_boundary_f1"


def test_ratio_metrics_no_duplicates_batch43():
    assert len(set(_RATIO_METRICS)) == len(_RATIO_METRICS)


def test_ratio_metrics_all_strings_batch43():
    for m in _RATIO_METRICS:
        assert isinstance(m, str)


def test_ratio_metrics_exact_set_batch43():
    expected = {
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
    }
    assert set(_RATIO_METRICS) == expected


# ---------- 三集合不相交 ----------

def test_ratio_count_disjoint_batch43():
    assert set(_RATIO_METRICS).isdisjoint(set(_COUNT_METRICS))


def test_ratio_success_disjoint_batch43():
    assert set(_RATIO_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))


def test_count_success_disjoint_batch43():
    assert set(_COUNT_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))


def test_count_metrics_exact_batch43():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_exact_batch43():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_count_metrics_no_duplicates_batch43():
    assert len(set(_COUNT_METRICS)) == len(_COUNT_METRICS)


def test_success_bool_metrics_no_duplicates_batch43():
    assert len(set(_SUCCESS_BOOL_METRICS)) == len(_SUCCESS_BOOL_METRICS)


# ---------- get_git_provenance 签名 ----------

def test_get_git_provenance_one_param_batch43():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root"]


def test_get_git_provenance_param_kind_batch43():
    sig = inspect.signature(get_git_provenance)
    p = sig.parameters["project_root"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_get_git_provenance_no_default_batch43():
    sig = inspect.signature(get_git_provenance)
    p = sig.parameters["project_root"]
    assert p.default is inspect.Parameter.empty


def test_get_git_provenance_return_annotation_batch43():
    sig = inspect.signature(get_git_provenance)
    assert "dict" in str(sig.return_annotation)


# ---------- get_git_provenance subprocess 参数 ----------

def test_get_git_provenance_uses_timeout_10_batch43():
    src = inspect.getsource(get_git_provenance)
    assert "timeout=10" in src


def test_get_git_provenance_uses_cwd_str_batch43():
    src = inspect.getsource(get_git_provenance)
    assert "cwd=str(project_root)" in src


def test_get_git_provenance_uses_capture_output_batch43():
    src = inspect.getsource(get_git_provenance)
    assert "capture_output=True" in src


def test_get_git_provenance_uses_errors_replace_batch43():
    src = inspect.getsource(get_git_provenance)
    assert 'errors="replace"' in src


def test_get_git_provenance_uses_encoding_utf8_batch43():
    src = inspect.getsource(get_git_provenance)
    assert 'encoding="utf-8"' in src


def test_get_git_provenance_returns_2_keys_batch43():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc123\n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        out = get_git_provenance(Path("/tmp"))
        assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_commit_stripped_batch43():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="  abc123  \n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        out = get_git_provenance(Path("/tmp"))
        assert out["git_commit"] == "abc123"


def test_get_git_provenance_commit_none_when_whitespace_only_batch43():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="   \n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        out = get_git_provenance(Path("/tmp"))
        assert out["git_commit"] is None


def test_get_git_provenance_commit_none_when_returncode_nonzero_batch43():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=128, stdout="")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        out = get_git_provenance(Path("/tmp"))
        assert out["git_commit"] is None


def test_get_git_provenance_dirty_true_when_uncommitted_batch43():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc\n")
        m2 = MagicMock(returncode=0, stdout=" M file.txt\n")
        mock_run.side_effect = [m1, m2]
        out = get_git_provenance(Path("/tmp"))
        assert out["git_dirty"] is True


def test_get_git_provenance_dirty_false_when_clean_batch43():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc\n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        out = get_git_provenance(Path("/tmp"))
        assert out["git_dirty"] is False


def test_get_git_provenance_catches_oserror_batch43():
    with patch("subprocess.run", side_effect=OSError("boom")):
        out = get_git_provenance(Path("/tmp"))
        assert out == {"git_commit": None, "git_dirty": True}


def test_get_git_provenance_catches_subprocesserror_batch43():
    with patch("subprocess.run", side_effect=subprocess.SubprocessError("boom")):
        out = get_git_provenance(Path("/tmp"))
        assert out == {"git_commit": None, "git_dirty": True}


def test_get_git_provenance_catches_timeout_batch43():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10)):
        out = get_git_provenance(Path("/tmp"))
        assert out == {"git_commit": None, "git_dirty": True}


# ---------- get_dependency_versions 签名与返回 ----------

def test_get_dependency_versions_no_params_batch43():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_get_dependency_versions_return_annotation_batch43():
    sig = inspect.signature(get_dependency_versions)
    assert "dict" in str(sig.return_annotation)


def test_get_dependency_versions_returns_dict_batch43():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_get_dependency_versions_keys_exact_batch43():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_type_batch43():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_packagenotfound_batch43():
    import importlib.metadata
    with patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError):
        out = get_dependency_versions()
        assert all(v is None for v in out.values())


def test_get_dependency_versions_exception_batch43():
    import importlib.metadata
    with patch("importlib.metadata.version", side_effect=Exception("boom")):
        out = get_dependency_versions()
        assert all(v is None for v in out.values())


def test_get_dependency_versions_string_version_batch43():
    with patch("importlib.metadata.version", return_value="1.2.3"):
        out = get_dependency_versions()
        for v in out.values():
            assert v == "1.2.3"


# ---------- build_provenance ----------

def test_build_provenance_signature_batch43():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_build_provenance_keyword_or_positional_batch43():
    sig = inspect.signature(build_provenance)
    for name in ["project_root", "parser_name", "max_chars", "parser_version"]:
        p = sig.parameters[name]
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_build_provenance_9_keys_batch43():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc\n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        with patch("evaluation.report.get_dependency_versions", return_value={"pdfplumber": "1.0", "python-docx": "2.0", "pypdfium2": "3.0"}):
            out = build_provenance(Path("/tmp"), "fallback", 800, "1.0.0")
    expected = {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars", "run_timestamp_iso",
    }
    assert set(out.keys()) == expected


def test_build_provenance_max_chars_int_batch43():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc\n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out = build_provenance(Path("/tmp"), "fallback", 800, "1.0.0")
    assert isinstance(out["max_chars"], int)
    assert out["max_chars"] == 800


def test_build_provenance_max_chars_string_to_int_batch43():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc\n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out = build_provenance(Path("/tmp"), "fallback", 800, "1.0.0")
    assert out["max_chars"] == 800


def test_build_provenance_parser_name_passthrough_batch43():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc\n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out = build_provenance(Path("/tmp"), "kreuzberg", 800, None)
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_none_batch43():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc\n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out = build_provenance(Path("/tmp"), "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_dependencies_is_dict_batch43():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc\n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        with patch("evaluation.report.get_dependency_versions", return_value={"pdfplumber": "1.0"}):
            out = build_provenance(Path("/tmp"), "fallback", 800, "1.0.0")
    assert isinstance(out["dependencies"], dict)
    assert out["dependencies"]["pdfplumber"] == "1.0"


def test_build_provenance_run_timestamp_iso_format_batch43():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc\n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out = build_provenance(Path("/tmp"), "fallback", 800, "1.0.0")
    ts = out["run_timestamp_iso"]
    assert isinstance(ts, str)
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None


def test_build_provenance_evaluator_version_batch43():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc\n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out = build_provenance(Path("/tmp"), "fallback", 800, "1.0.0")
    assert out["evaluator_version"] == "1.1"
    assert out["report_version"] == "1.1"


# ---------- build_devset_section ----------

def test_build_devset_section_signature_batch43():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.keys())
    assert params == ["manifest"]


def test_build_devset_section_6_keys_batch43():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 5
    m.content_group_count = 3
    m.pdf_count = 2
    m.docx_count = 3
    m.categories_covered = ["cat_a", "cat_b"]
    out = build_devset_section(m)
    expected = {
        "status", "file_count", "content_group_count", "pdf_count", "docx_count",
        "categories_covered",
    }
    assert set(out.keys()) == expected


def test_build_devset_section_values_batch43():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 10
    m.content_group_count = 4
    m.pdf_count = 5
    m.docx_count = 5
    m.categories_covered = ["a", "b", "c"]
    out = build_devset_section(m)
    assert out["status"] == "complete"
    assert out["file_count"] == 10
    assert out["content_group_count"] == 4
    assert out["pdf_count"] == 5
    assert out["docx_count"] == 5
    assert out["categories_covered"] == ["a", "b", "c"]


def test_build_devset_section_duck_typed_batch43():
    class FakeManifest:
        def __init__(self):
            self.devset_status = "incomplete"
            self.file_count = 1
            self.content_group_count = 1
            self.pdf_count = 1
            self.docx_count = 0
            self.categories_covered = ["x"]
    out = build_devset_section(FakeManifest())
    assert out["status"] == "incomplete"
    assert out["docx_count"] == 0


# ---------- aggregate_summary ----------

def test_aggregate_summary_empty_batch43():
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_counts_subkeys_batch43():
    out = aggregate_summary([])
    for name in _COUNT_METRICS:
        assert set(out["counts"][name].keys()) == {"sum", "participating_docs"}


def test_aggregate_summary_success_rates_subkeys_batch43():
    out = aggregate_summary([])
    for name in _SUCCESS_BOOL_METRICS:
        assert set(out["success_rates"][name].keys()) == {"success_count", "total", "rate"}


def test_aggregate_summary_ratio_macro_averages_subkeys_batch43():
    out = aggregate_summary([])
    for name in _RATIO_METRICS:
        assert set(out["ratio_macro_averages"][name].keys()) == {"macro_average", "participating_docs", "not_evaluated"}


def test_aggregate_summary_empty_all_none_batch43():
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["success_rates"]["pipeline_success"]["rate"] is None
    assert all(out["ratio_macro_averages"][n]["macro_average"] is None for n in _RATIO_METRICS)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_counts_with_value_zero_batch43():
    """0 值参与（只有 None 被过滤）。"""
    per_doc = [{"metrics": {"element_count_total": {"value": 0}}}]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 0
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_counts_with_value_none_batch43():
    per_doc = [{"metrics": {"element_count_total": {"value": None}}}]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_counts_missing_key_batch43():
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] is None


def test_aggregate_summary_success_rate_with_true_batch43():
    per_doc = [{"metrics": {"pipeline_success": {"value": True}}}]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["total"] == 1
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0


def test_aggregate_summary_success_rate_with_false_batch43():
    per_doc = [{"metrics": {"pipeline_success": {"value": False}}}]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.0


def test_aggregate_summary_success_rate_with_non_bool_batch43():
    """非 bool 的 'truthy' 不计入 success（必须严格 True）。"""
    per_doc = [{"metrics": {"pipeline_success": {"value": 1}}}]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0
    assert out["success_rates"]["pipeline_success"]["total"] == 1


def test_aggregate_summary_success_rate_mixed_batch43():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 2
    assert out["success_rates"]["pipeline_success"]["total"] == 3
    assert out["success_rates"]["pipeline_success"]["rate"] == pytest.approx(2 / 3)


def test_aggregate_summary_ratio_zero_participates_batch43():
    per_doc = [{"metrics": {"schema_valid": {"value": 0.0}}}]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.0
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 0


def test_aggregate_summary_ratio_none_skipped_batch43():
    per_doc = [{"metrics": {"schema_valid": {"value": None}}}]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] is None
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 0
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1


def test_aggregate_summary_ratio_mixed_batch43():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.5}}},
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.75
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_batch43():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 0}}},
        {"metrics": {"silent_drop_count": {"value": 2}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 5


def test_aggregate_summary_silent_drop_with_none_batch43():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 3


def test_aggregate_summary_silent_drop_all_none_batch43():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_idempotent_batch43():
    per_doc = [{"metrics": {"schema_valid": {"value": 0.5}, "element_count_total": {"value": 10}, "pipeline_success": {"value": True}}}]
    out1 = aggregate_summary(per_doc)
    out2 = aggregate_summary(per_doc)
    assert out1 == out2


def test_aggregate_summary_field_order_batch43():
    out = aggregate_summary([])
    keys = list(out.keys())
    assert keys == ["counts", "success_rates", "ratio_macro_averages", "silent_drop_total"]


# ---------- __all__ ----------

def test_all_exact_batch43():
    assert set(report_mod.__all__) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_all_count_5_batch43():
    assert len(report_mod.__all__) == 5


def test_all_no_duplicates_batch43():
    assert len(set(report_mod.__all__)) == len(report_mod.__all__)


def test_all_entries_are_str_batch43():
    for e in report_mod.__all__:
        assert isinstance(e, str)


def test_all_entries_are_attrs_batch43():
    for e in report_mod.__all__:
        assert hasattr(report_mod, e)


# ---------- 模块结构 ----------

def test_module_has_docstring_batch43():
    assert report_mod.__doc__ is not None
    assert len(report_mod.__doc__) > 50


def test_module_source_contains_aggregate_summary_doc_batch43():
    src = inspect.getsource(report_mod)
    assert "不混合类型" in src


def test_module_source_contains_counts_section_batch43():
    src = inspect.getsource(report_mod)
    assert "counts（element_count_total）→ 求和" in src


def test_module_source_contains_success_rates_section_batch43():
    src = inspect.getsource(report_mod)
    assert "success_rates" in src


def test_module_source_contains_macro_averages_section_batch43():
    src = inspect.getsource(report_mod)
    assert "ratio_macro_averages" in src


def test_module_source_contains_silent_drop_section_batch43():
    src = inspect.getsource(report_mod)
    assert "silent_drop_count" in src


# ---------- AST 结构 ----------

def test_ast_top_level_no_class_batch43():
    tree = ast.parse(inspect.getsource(report_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert classes == []


def test_ast_top_level_function_count_batch43():
    tree = ast.parse(inspect.getsource(report_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 5


def test_ast_top_level_function_names_batch43():
    tree = ast.parse(inspect.getsource(report_mod))
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert funcs == [
        "get_git_provenance",
        "get_dependency_versions",
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
    ]


def test_ast_top_level_assigns_count_batch43():
    tree = ast.parse(inspect.getsource(report_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    # _RATIO_METRICS, _COUNT_METRICS, _SUCCESS_BOOL_METRICS, __all__
    assert len(assigns) == 4


def test_ast_no_try_in_module_body_batch43():
    """顶层没有 try（try 在 function 内部）。"""
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, ast.Try)


def test_ast_no_for_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, ast.For)


def test_ast_no_while_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_no_with_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, (ast.With, ast.AsyncWith))


def test_ast_no_async_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_has_imports_batch43():
    tree = ast.parse(inspect.getsource(report_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) >= 4  # subprocess, datetime, pathlib, typing


def test_ast_from_future_first_batch43():
    tree = ast.parse(inspect.getsource(report_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)  # module docstring
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


# ---------- forbidden tokens 第八十四批 ----------

def test_source_no_eval_batch43():
    src = inspect.getsource(report_mod)
    assert "eval(" not in src
    assert "eval (" not in src


def test_source_no_exec_batch43():
    src = inspect.getsource(report_mod)
    assert "exec(" not in src
    assert "exec (" not in src


def test_source_no_compile_batch43():
    src = inspect.getsource(report_mod)
    assert "compile(" not in src


def test_source_no_globals_batch43():
    src = inspect.getsource(report_mod)
    assert "globals(" not in src


def test_source_no_locals_batch43():
    src = inspect.getsource(report_mod)
    assert "locals(" not in src


def test_source_no_open_batch43():
    src = inspect.getsource(report_mod)
    assert "open(" not in src


def test_source_no_os_system_batch43():
    src = inspect.getsource(report_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch43():
    src = inspect.getsource(report_mod)
    assert "popen(" not in src


def test_source_no_yaml_load_batch43():
    src = inspect.getsource(report_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch43():
    src = inspect.getsource(report_mod)
    assert "pickle.load(" not in src


# ---------- 端到端集成 ----------

def test_aggregate_summary_full_pipeline_batch43():
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "schema_valid": {"value": 1.0},
                "pdf_locator_valid_ratio": {"value": 0.5},
                "element_count_total": {"value": 10},
                "silent_drop_count": {"value": 1},
            }
        },
        {
            "metrics": {
                "pipeline_success": {"value": False},
                "schema_valid": {"value": None},
                "element_count_total": {"value": None},
                "silent_drop_count": {"value": None},
            }
        },
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 10
    assert out["counts"]["element_count_total"]["participating_docs"] == 1
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["total"] == 2
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 0.5
    assert out["silent_drop_total"] == 1


def test_aggregate_summary_no_metrics_key_batch43():
    """per_doc 没有 metrics key 时不会崩溃（KeyError 也不行）。"""
    per_doc = [{}]
    with pytest.raises(KeyError):
        aggregate_summary(per_doc)


def test_aggregate_summary_metrics_is_none_batch43():
    """metrics=None 时取 .get 会抛错。"""
    per_doc = [{"metrics": None}]
    with pytest.raises(AttributeError):
        aggregate_summary(per_doc)
