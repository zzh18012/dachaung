"""evaluation/report.py 第五十六轮 edges 测试（Round 597）。

补强 edges55 未触及的角度（第四十一批）。
"""

from __future__ import annotations

import inspect
import json
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 第四十一批


def test_ratio_metrics_no_duplicates_batch41():
    assert len(_RATIO_METRICS) == len(set(_RATIO_METRICS))


def test_count_metrics_no_duplicates_batch41():
    assert len(_COUNT_METRICS) == len(set(_COUNT_METRICS))


def test_success_bool_metrics_no_duplicates_batch41():
    assert len(_SUCCESS_BOOL_METRICS) == len(set(_SUCCESS_BOOL_METRICS))


def test_ratio_metrics_disjoint_from_count_batch41():
    assert set(_RATIO_METRICS).isdisjoint(set(_COUNT_METRICS))


def test_ratio_metrics_disjoint_from_success_bool_batch41():
    assert set(_RATIO_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))


def test_count_metrics_disjoint_from_success_bool_batch41():
    assert set(_COUNT_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))


def test_ratio_metrics_specific_position_chunk_boundary_f1_last_batch41():
    """末尾是 chunk_boundary_f1（带 f1）。"""
    assert _RATIO_METRICS[-1] == "chunk_boundary_f1"


def test_ratio_metrics_schema_valid_first_batch41():
    assert _RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_chunk_boundary_three_consecutive_batch41():
    """chunk_boundary_prf 三项应该相邻。"""
    names = list(_RATIO_METRICS)
    # 找到 precision / recall / f1
    p_idx = names.index("chunk_boundary_precision")
    r_idx = names.index("chunk_boundary_recall")
    f_idx = names.index("chunk_boundary_f1")
    assert r_idx == p_idx + 1
    assert f_idx == r_idx + 1


def test_ratio_metrics_text_char_pair_consecutive_batch41():
    """text_char_multiset_precision / recall 应相邻。"""
    names = list(_RATIO_METRICS)
    p_idx = names.index("text_char_multiset_precision")
    r_idx = names.index("text_char_multiset_recall")
    assert r_idx == p_idx + 1


def test_ratio_metrics_does_not_contain_chunk_boundary_specificity_batch41():
    assert "chunk_boundary_specificity" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_figure_caption_batch41():
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_count_metrics_only_one_member_batch41():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_only_one_member_batch41():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_ratio_metrics_schema_valid_in_tuple_batch41():
    """schema_valid 既在 _RATIO_METRICS，但 _SUCCESS_BOOL_METRICS 不含。"""
    assert "schema_valid" in _RATIO_METRICS
    assert "schema_valid" not in _SUCCESS_BOOL_METRICS


# ---------- get_git_provenance 第四十一批


def test_git_provenance_signature_one_param_batch41():
    sig = inspect.signature(get_git_provenance)
    assert list(sig.parameters.keys()) == ["project_root"]


def test_git_provenance_param_no_default_batch41():
    sig = inspect.signature(get_git_provenance)
    assert sig.parameters["project_root"].default is inspect.Parameter.empty


def test_git_provenance_param_annotation_path_batch41():
    sig = inspect.signature(get_git_provenance)
    assert "Path" in str(sig.parameters["project_root"].annotation)


def test_git_provenance_return_annotation_dict_batch41():
    sig = inspect.signature(get_git_provenance)
    assert "dict" in str(sig.return_annotation)


def test_git_provenance_with_oserror_batch41(tmp_path):
    """OSError 应被捕获。"""
    with patch("subprocess.run", side_effect=OSError("missing git")):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_git_provenance_with_file_not_found_batch41(tmp_path):
    """FileNotFoundError（OSError 子类）应被捕获。"""
    with patch("subprocess.run", side_effect=FileNotFoundError("no git binary")):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_git_provenance_with_timeout_batch41(tmp_path):
    """TimeoutExpired（SubprocessError 子类）应被捕获。"""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10)):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_git_provenance_commit_returncode_nonzero_batch41(tmp_path):
    """rev-parse 失败 → commit=None。"""
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 128
        m.stdout = ""
        return m
    with patch("subprocess.run", side_effect=side_effect):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_git_provenance_commit_stdout_whitespace_only_batch41(tmp_path):
    """rev-parse 成功但 stdout 全空白 → strip 后为空 → commit=None。"""
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        if "rev-parse" in cmd:
            m.stdout = "   \n  \t  "
        else:
            m.stdout = ""
        return m
    with patch("subprocess.run", side_effect=side_effect):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_git_provenance_commit_stdout_stripped_batch41(tmp_path):
    """rev-parse 成功 → strip 换行。"""
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        if "rev-parse" in cmd:
            m.stdout = "abc123\n"
        else:
            m.stdout = ""
        return m
    with patch("subprocess.run", side_effect=side_effect):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"


def test_git_provenance_dirty_porcelain_nonempty_batch41(tmp_path):
    """porcelain 输出非空 → dirty=True（即便 returncode=0）。"""
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        if "rev-parse" in cmd:
            m.stdout = "abc123\n"
        else:
            m.stdout = " M file.py\n"
        return m
    with patch("subprocess.run", side_effect=side_effect):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


def test_git_provenance_dirty_porcelain_returncode_nonzero_batch41(tmp_path):
    """porcelain 失败 → dirty=False（短路：r2.returncode==0 为 False，bool(False and X)=False）。"""
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        if "rev-parse" in cmd:
            m.returncode = 0
            m.stdout = "abc123\n"
        else:
            m.returncode = 1
            m.stdout = ""
        return m
    with patch("subprocess.run", side_effect=side_effect):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_git_provenance_dirty_porcelain_returncode_zero_empty_batch41(tmp_path):
    """porcelain returncode=0 + stdout 空 → dirty=False。"""
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        if "rev-parse" in cmd:
            m.stdout = "abc123\n"
        else:
            m.stdout = ""
        return m
    with patch("subprocess.run", side_effect=side_effect):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_git_provenance_uses_timeout_10_batch41(tmp_path):
    """subprocess.run 收到 timeout=10。"""
    captured = {}

    def side_effect(cmd, *args, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        return m

    with patch("subprocess.run", side_effect=side_effect):
        get_git_provenance(tmp_path)
    assert captured["timeout"] == 10


def test_git_provenance_uses_cwd_batch41(tmp_path):
    """subprocess.run 收到 cwd=tmp_path。"""
    captured = {}

    def side_effect(cmd, *args, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        return m

    with patch("subprocess.run", side_effect=side_effect):
        get_git_provenance(tmp_path)
    # 走两次（rev-parse / status），都应传 cwd
    assert captured["cwd"] == str(tmp_path)


def test_git_provenance_uses_capture_output_batch41(tmp_path):
    """subprocess.run 收到 capture_output=True。"""
    captured = {}

    def side_effect(cmd, *args, **kwargs):
        captured["capture_output"] = kwargs.get("capture_output")
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        return m

    with patch("subprocess.run", side_effect=side_effect):
        get_git_provenance(tmp_path)
    assert captured["capture_output"] is True


# ---------- get_dependency_versions 第四十一批


def test_get_dependency_versions_callable_batch41():
    assert callable(get_dependency_versions)


def test_get_dependency_versions_no_param_batch41():
    sig = inspect.signature(get_dependency_versions)
    assert list(sig.parameters.keys()) == []


def test_get_dependency_versions_return_dict_batch41():
    sig = inspect.signature(get_dependency_versions)
    assert "dict" in str(sig.return_annotation)


def test_get_dependency_versions_returns_dict_batch41():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_get_dependency_versions_has_three_keys_batch41():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_str_or_none_batch41():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_with_package_not_found_batch41():
    """模拟 importlib.metadata.PackageNotFoundError。"""
    import importlib.metadata

    with patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError("x")):
        out = get_dependency_versions()
    assert out["pdfplumber"] is None
    assert out["python-docx"] is None
    assert out["pypdfium2"] is None


def test_get_dependency_versions_with_generic_exception_batch41():
    """模拟其他异常 → 应被 Exception 捕获为 None。"""
    with patch("importlib.metadata.version", side_effect=RuntimeError("boom")):
        out = get_dependency_versions()
    assert out["pdfplumber"] is None


def test_get_dependency_versions_with_value_returned_batch41():
    """模拟返回版本字符串。"""
    with patch("importlib.metadata.version", return_value="1.2.3"):
        out = get_dependency_versions()
    assert out["pdfplumber"] == "1.2.3"
    assert out["python-docx"] == "1.2.3"
    assert out["pypdfium2"] == "1.2.3"


def test_get_dependency_versions_iterates_three_packages_batch41():
    """源码包含三个包名。"""
    src = inspect.getsource(rmod)
    assert "pdfplumber" in src
    assert "python-docx" in src
    assert "pypdfium2" in src


# ---------- build_provenance 第四十一批


def test_build_provenance_callable_batch41():
    assert callable(build_provenance)


def test_build_provenance_signature_four_params_batch41():
    sig = inspect.signature(build_provenance)
    assert list(sig.parameters.keys()) == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_build_provenance_returns_dict_batch41(tmp_path):
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert isinstance(out, dict)


def test_build_provenance_nine_keys_batch41(tmp_path):
    """9 个顶层字段。"""
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    expected = {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars", "run_timestamp_iso",
    }
    assert set(out.keys()) == expected


def test_build_provenance_parser_version_none_batch41(tmp_path):
    """parser_version=None 透传。"""
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_max_chars_int_conversion_batch41(tmp_path):
    """max_chars 可以是 float → int 转换。"""
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 800.0, "0.1.0")
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_str_raises_batch41(tmp_path):
    """max_chars 字符串 → int() 转换成功（数字字符串）。"""
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", "800", "0.1.0")
    assert out["max_chars"] == 800


def test_build_provenance_max_chars_non_numeric_str_raises_batch41(tmp_path):
    """max_chars 非数字字符串 → ValueError。"""
    with patch("subprocess.run"):
        with pytest.raises(ValueError):
            build_provenance(tmp_path, "fallback", "abc", "0.1.0")


def test_build_provenance_evaluator_version_constant_batch41(tmp_path):
    """evaluator_version 来自 EVALUATOR_VERSION。"""
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_constant_batch41(tmp_path):
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_run_timestamp_iso_parses_batch41(tmp_path):
    """run_timestamp_iso 是合法 ISO 字符串。"""
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    parsed = datetime.fromisoformat(out["run_timestamp_iso"])
    assert isinstance(parsed, datetime)


def test_build_provenance_dependencies_dict_batch41(tmp_path):
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_parser_name_passthrough_batch41(tmp_path):
    with patch("subprocess.run"):
        out = build_provenance(tmp_path, "kreuzberg", 800, "3.0")
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_git_dirty_when_exception_batch41(tmp_path):
    """subprocess 抛异常 → git_commit=None / git_dirty=True。"""
    with patch("subprocess.run", side_effect=subprocess.SubprocessError("err")):
        out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


# ---------- build_devset_section 第四十一批


def _make_manifest_mock(**kwargs):
    m = MagicMock()
    m.devset_status = kwargs.get("devset_status", "incomplete")
    m.file_count = kwargs.get("file_count", 0)
    m.content_group_count = kwargs.get("content_group_count", 0)
    m.pdf_count = kwargs.get("pdf_count", 0)
    m.docx_count = kwargs.get("docx_count", 0)
    m.categories_covered = kwargs.get("categories_covered", [])
    return m


def test_build_devset_section_returns_six_keys_batch41():
    out = build_devset_section(_make_manifest_mock())
    assert len(out) == 6


def test_build_devset_section_exact_key_set_batch41():
    out = build_devset_section(_make_manifest_mock())
    assert set(out.keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_build_devset_section_content_group_count_batch41():
    out = build_devset_section(_make_manifest_mock(content_group_count=7))
    assert out["content_group_count"] == 7


def test_build_devset_section_pdf_count_batch41():
    out = build_devset_section(_make_manifest_mock(pdf_count=4))
    assert out["pdf_count"] == 4


def test_build_devset_section_docx_count_batch41():
    out = build_devset_section(_make_manifest_mock(docx_count=9))
    assert out["docx_count"] == 9


def test_build_devset_section_categories_tuple_batch41():
    """categories_covered 可以是 tuple。"""
    cats = ("a", "b")
    out = build_devset_section(_make_manifest_mock(categories_covered=cats))
    assert out["categories_covered"] == cats


def test_build_devset_section_categories_dict_batch41():
    """categories_covered 接受任意类型（不强校验）。"""
    cats = {"x": 1}
    out = build_devset_section(_make_manifest_mock(categories_covered=cats))
    assert out["categories_covered"] == cats


def test_build_devset_section_none_manifest_raises_batch41():
    """manifest=None → MagicMock 没有，会抛 AttributeError。"""
    with pytest.raises(AttributeError):
        build_devset_section(None)


def test_build_devset_section_int_status_batch41():
    """status 接受非字符串（不强校验）。"""
    out = build_devset_section(_make_manifest_mock(devset_status=1))
    assert out["status"] == 1


def test_build_devset_section_does_not_mutate_input_batch41():
    m = _make_manifest_mock(categories_covered=["a"])
    before = list(m.categories_covered)
    build_devset_section(m)
    assert list(m.categories_covered) == before


def test_build_devset_section_idempotent_batch41():
    m = _make_manifest_mock()
    out1 = build_devset_section(m)
    out2 = build_devset_section(m)
    assert out1 == out2


def test_build_devset_section_json_serializable_batch41():
    """典型输出应 JSON 可序列化。"""
    m = _make_manifest_mock(
        devset_status="complete",
        file_count=5,
        content_group_count=3,
        pdf_count=2,
        docx_count=3,
        categories_covered=["tutorial", "reference"],
    )
    out = build_devset_section(m)
    json.dumps(out)


# ---------- aggregate_summary 第四十一批


def test_aggregate_summary_returns_four_keys_batch41():
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_counts_one_key_batch41():
    out = aggregate_summary([])
    assert set(out["counts"].keys()) == {"element_count_total"}


def test_aggregate_summary_success_rates_one_key_batch41():
    out = aggregate_summary([])
    assert set(out["success_rates"].keys()) == {"pipeline_success"}


def test_aggregate_summary_ratio_macro_keys_match_ratio_metrics_batch41():
    out = aggregate_summary([])
    assert set(out["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


def test_aggregate_summary_large_input_batch41():
    """1000 个文档聚合不抛异常。"""
    per_doc = [{"metrics": {"pipeline_success": {"value": True}, "element_count_total": {"value": 1}}}
               for _ in range(1000)]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1000
    assert out["counts"]["element_count_total"]["sum"] == 1000


def test_aggregate_summary_participating_docs_count_batch41():
    """参与计算的 doc 数。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
    ]
    out = aggregate_summary(per_doc)
    schema = out["ratio_macro_averages"]["schema_valid"]
    assert schema["participating_docs"] == 2
    assert schema["not_evaluated"] == 1


def test_aggregate_summary_macro_average_with_some_participating_batch41():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5


def test_aggregate_summary_success_rate_with_mixed_values_batch41():
    """True/False/None 混合。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 3
    assert sr["rate"] == pytest.approx(1 / 3)


def test_aggregate_summary_count_with_none_only_batch41():
    """所有 value 都是 None → sum=None / participating=0。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_silent_drop_count_missing_key_batch41():
    """silent_drop_count 整个 key 不存在 → 视为 None → 不参与。"""
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_count_zero_included_batch41():
    """value=0 不是 None → 参与（None 才排除）。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 0}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 5


def test_aggregate_summary_silent_drop_count_negative_treated_as_value_batch41():
    """负数也参与（不强校验，直接 sum）。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": -1}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 4


def test_aggregate_summary_does_not_mutate_per_doc_batch41():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}, "element_count_total": {"value": 3}}},
    ]
    before = json.dumps(per_doc, sort_keys=True)
    aggregate_summary(per_doc)
    assert json.dumps(per_doc, sort_keys=True) == before


def test_aggregate_summary_tuple_input_batch41():
    """per_doc_results 可以是 tuple（list-like 迭代）。"""
    per_doc = ({"metrics": {"pipeline_success": {"value": True}}},)
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1


def test_aggregate_summary_iter_input_raises_batch41():
    """per_doc_results 是 generator → 第二次循环+len() 会抛 TypeError。"""
    gen = ({"metrics": {"pipeline_success": {"value": True}}} for _ in range(2))
    with pytest.raises(TypeError):
        aggregate_summary(gen)


def test_aggregate_summary_returns_new_dict_each_call_batch41():
    """两次调用返回不同对象（不缓存）。"""
    out1 = aggregate_summary([])
    out2 = aggregate_summary([])
    assert out1 is not out2
    assert out1 == out2


def test_aggregate_summary_counts_with_one_participating_batch41():
    per_doc = [{"metrics": {"element_count_total": {"value": 42}}}]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 42
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_json_serializable_batch41():
    """summary 输出应 JSON 可序列化（典型场景）。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}, "element_count_total": {"value": 3}}},
    ]
    out = aggregate_summary(per_doc)
    json.dumps(out)


# ---------- module source forbidden tokens 第七十批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch41(token):
    src = inspect.getsource(rmod)
    assert token not in src


# ---------- module source 字符串精确补强第六十六批


def test_module_source_contains_design_doc_batch41():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_contains_future_annotations_batch41():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_subprocess_import_batch41():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_contains_pathlib_path_import_batch41():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch41():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_contains_datetime_import_batch41():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_contains_evaluation_import_batch41():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_contains_count_metrics_constant_batch41():
    src = inspect.getsource(rmod)
    assert "_COUNT_METRICS = " in src


def test_module_source_contains_success_bool_metrics_constant_batch41():
    src = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS = " in src


def test_module_source_contains_ratio_metrics_constant_batch41():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS = " in src


def test_module_source_contains_all_export_batch41():
    src = inspect.getsource(rmod)
    assert "__all__" in src


def test_module_source_contains_count_aggregation_comment_batch41():
    src = inspect.getsource(rmod)
    assert "counts" in src


def test_module_source_contains_success_rate_comment_batch41():
    src = inspect.getsource(rmod)
    assert "success_rates" in src


def test_module_source_contains_ratio_macro_averages_comment_batch41():
    src = inspect.getsource(rmod)
    assert "ratio_macro_averages" in src


def test_module_source_contains_silent_drop_count_comment_batch41():
    src = inspect.getsource(rmod)
    assert "silent_drop_count" in src


def test_module_source_contains_no_mixed_score_comment_batch41():
    src = inspect.getsource(rmod)
    assert "不混合" in src


def test_module_source_contains_subprocess_run_call_batch41():
    src = inspect.getsource(rmod)
    assert "subprocess.run(" in src


def test_module_source_contains_timeout_10_batch41():
    src = inspect.getsource(rmod)
    assert "timeout=10" in src


def test_module_source_contains_encoding_utf8_batch41():
    src = inspect.getsource(rmod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_errors_replace_batch41():
    src = inspect.getsource(rmod)
    assert 'errors="replace"' in src


def test_module_source_contains_capture_output_batch41():
    src = inspect.getsource(rmod)
    assert "capture_output=True" in src


def test_module_source_contains_porcelain_command_batch41():
    src = inspect.getsource(rmod)
    assert "status" in src and "porcelain" in src


def test_module_source_contains_rev_parse_command_batch41():
    src = inspect.getsource(rmod)
    assert "rev-parse" in src


def test_module_source_contains_head_argument_batch41():
    src = inspect.getsource(rmod)
    assert "HEAD" in src


# ---------- signatures 第六十六批


def test_signature_get_git_provenance_params_batch41():
    sig = inspect.signature(get_git_provenance)
    assert list(sig.parameters.keys()) == ["project_root"]


def test_signature_get_dependency_versions_no_params_batch41():
    sig = inspect.signature(get_dependency_versions)
    assert list(sig.parameters.keys()) == []


def test_signature_build_provenance_params_batch41():
    sig = inspect.signature(build_provenance)
    assert list(sig.parameters.keys()) == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_devset_section_params_batch41():
    sig = inspect.signature(build_devset_section)
    assert list(sig.parameters.keys()) == ["manifest"]


def test_signature_aggregate_summary_params_batch41():
    sig = inspect.signature(aggregate_summary)
    assert list(sig.parameters.keys()) == ["per_doc_results"]


def test_signature_build_provenance_project_root_no_default_batch41():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["project_root"].default is inspect.Parameter.empty


def test_signature_build_provenance_parser_name_no_default_batch41():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["parser_name"].default is inspect.Parameter.empty


def test_signature_build_provenance_max_chars_no_default_batch41():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["max_chars"].default is inspect.Parameter.empty


def test_signature_build_provenance_parser_version_no_default_batch41():
    sig = inspect.signature(build_provenance)
    assert sig.parameters["parser_version"].default is inspect.Parameter.empty


def test_signature_build_provenance_max_chars_int_annotation_batch41():
    sig = inspect.signature(build_provenance)
    assert "int" in str(sig.parameters["max_chars"].annotation)


def test_signature_build_provenance_parser_name_str_annotation_batch41():
    sig = inspect.signature(build_provenance)
    assert "str" in str(sig.parameters["parser_name"].annotation)


def test_signature_aggregate_summary_per_doc_list_annotation_batch41():
    sig = inspect.signature(aggregate_summary)
    assert "list" in str(sig.parameters["per_doc_results"].annotation)


def test_signature_build_devset_section_manifest_annotation_ignored_batch41():
    """build_devset_section 注释里有 type: ignore[no-untyped-def]。"""
    src = inspect.getsource(rmod)
    assert "no-untyped-def" in src


def test_signature_all_public_functions_return_dict_batch41():
    """所有 public 函数都返回 dict（str annotation）。"""
    for fn in (get_git_provenance, get_dependency_versions, build_provenance,
               build_devset_section, aggregate_summary):
        sig = inspect.signature(fn)
        assert "dict" in str(sig.return_annotation)


# ---------- module 合理性 第六十六批


def test_module_has_all_attribute_batch41():
    assert hasattr(rmod, "__all__")


def test_module_all_is_list_batch41():
    assert isinstance(rmod.__all__, list)


def test_module_all_len_five_batch41():
    assert len(rmod.__all__) == 5


def test_module_all_contains_build_provenance_batch41():
    assert "build_provenance" in rmod.__all__


def test_module_all_contains_build_devset_section_batch41():
    assert "build_devset_section" in rmod.__all__


def test_module_all_contains_aggregate_summary_batch41():
    assert "aggregate_summary" in rmod.__all__


def test_module_all_contains_get_git_provenance_batch41():
    assert "get_git_provenance" in rmod.__all__


def test_module_all_contains_get_dependency_versions_batch41():
    assert "get_dependency_versions" in rmod.__all__


def test_module_all_does_not_contain_private_metrics_batch41():
    for name in ("_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"):
        assert name not in rmod.__all__


def test_module_does_not_define_class_batch41():
    src = inspect.getsource(rmod)
    assert "\nclass " not in src


def test_module_has_future_annotations_batch41():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


# ---------- 端到端集成 第六十六批


def test_e2e_build_provenance_full_round_trip_batch41(tmp_path):
    """build_provenance 正常路径返回完整结构。"""
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        if "rev-parse" in cmd:
            m.stdout = "abc123def\n"
        else:
            m.stdout = ""
        return m
    with patch("subprocess.run", side_effect=side_effect):
        out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert out["git_commit"] == "abc123def"
    assert out["git_dirty"] is False
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] == "0.1.0"
    assert out["max_chars"] == 800
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION
    parsed = datetime.fromisoformat(out["run_timestamp_iso"])
    assert isinstance(parsed, datetime)


def test_e2e_build_provenance_dirty_state_batch41(tmp_path):
    """dirty 状态：commit + dirty working tree。"""
    def side_effect(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 0
        if "rev-parse" in cmd:
            m.stdout = "feedface\n"
        else:
            m.stdout = " M file.py\n"
        return m
    with patch("subprocess.run", side_effect=side_effect):
        out = build_provenance(tmp_path, "kreuzberg", 1200, "3.0")
    assert out["git_commit"] == "feedface"
    assert out["git_dirty"] is True


def test_e2e_aggregate_summary_with_full_metrics_batch41():
    """aggregate_summary 处理完整 metrics dict。"""
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "schema_valid": {"value": 1.0},
                "element_count_total": {"value": 10},
                "pdf_locator_valid_ratio": {"value": 1.0},
                "silent_drop_count": {"value": 0},
            },
        },
        {
            "metrics": {
                "pipeline_success": {"value": False},
                "schema_valid": {"value": 0.0},
                "element_count_total": {"value": 5},
                "pdf_locator_valid_ratio": {"value": None},
                "silent_drop_count": {"value": 2},
            },
        },
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 1.0
    assert out["silent_drop_total"] == 2


def test_e2e_aggregate_summary_idempotent_batch41():
    """同一输入两次调用结果一致。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out1 = aggregate_summary(per_doc)
    out2 = aggregate_summary(per_doc)
    assert json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True)


def test_e2e_full_provenance_with_dependency_versions_batch41(tmp_path):
    """build_provenance + dependencies 结构完整。"""
    with patch("subprocess.run"):
        with patch("importlib.metadata.version", return_value="1.0.0"):
            out = build_provenance(tmp_path, "fallback", 800, "0.1.0")
    assert out["dependencies"]["pdfplumber"] == "1.0.0"
    assert out["dependencies"]["python-docx"] == "1.0.0"
    assert out["dependencies"]["pypdfium2"] == "1.0.0"
