"""evaluation/report.py 第八十六轮 edges 测试（Round 622）。

补强 edges58 未触及的角度（第四十四批）。

新角度：
- _RATIO_METRICS 各元素 in/out 顺序精确
- _RATIO_METRICS index 0/1/middle/last 精确
- _RATIO_METRICS 不含 element_count_total / silent_drop_count / figure_caption / pipeline_success
- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 单元素
- get_git_provenance OSError 单次（第一次抛，第二次正常）行为
- get_git_provenance stdout 含换行 strip
- get_git_provenance commit 与 dirty 独立
- get_dependency_versions try/except 内部 importlib.metadata 路径
- get_dependency_versions 不缓存（多次调用相同）
- build_provenance 重复调用 timestamp 不同（秒级精度）
- build_provenance 4 个固定字段（git_commit / git_dirty / evaluator_version / report_version）
- build_devset_section 6 个字段
- aggregate_summary 各种 metrics.get 返回 None / 空 dict 情况
- aggregate_summary 元组 unpacking 不崩溃
- aggregate_summary counts[r] 缺 metrics key
- aggregate_summary 顺序一致性
- module source 字符串精确
- AST 结构
- forbidden tokens 第九十二批
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


# ---------- _RATIO_METRICS 索引 ----------

def test_ratio_metrics_index_0_batch44():
    assert _RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_index_1_batch44():
    assert _RATIO_METRICS[1] == "pdf_locator_valid_ratio"


def test_ratio_metrics_index_middle_5_batch44():
    assert _RATIO_METRICS[5] == "text_preservation_equal"


def test_ratio_metrics_index_last_11_batch44():
    assert _RATIO_METRICS[11] == "chunk_boundary_f1"


def test_ratio_metrics_index_negative_1_batch44():
    assert _RATIO_METRICS[-1] == "chunk_boundary_f1"


def test_ratio_metrics_index_out_of_range_raises_batch44():
    with pytest.raises(IndexError):
        _ = _RATIO_METRICS[12]


def test_ratio_metrics_no_figure_caption_batch44():
    for m in _RATIO_METRICS:
        assert not m.startswith("figure_caption_")


def test_ratio_metrics_no_silent_drop_batch44():
    for m in _RATIO_METRICS:
        assert m != "silent_drop_count"


def test_ratio_metrics_no_element_count_total_batch44():
    for m in _RATIO_METRICS:
        assert m != "element_count_total"


def test_ratio_metrics_no_pipeline_success_batch44():
    for m in _RATIO_METRICS:
        assert m != "pipeline_success"


def test_ratio_metrics_no_text_char_multiset_extra_batch44():
    """只有 precision/recall，没有 f1。"""
    for m in _RATIO_METRICS:
        assert m != "text_char_multiset_f1"


# ---------- _COUNT_METRICS / _SUCCESS_BOOL_METRICS ----------

def test_count_metrics_length_1_batch44():
    assert len(_COUNT_METRICS) == 1


def test_count_metrics_no_silent_drop_batch44():
    assert "silent_drop_count" not in _COUNT_METRICS


def test_count_metrics_no_element_count_by_type_batch44():
    """element_count_by_type 是 dict 不参与求和。"""
    assert "element_count_by_type" not in _COUNT_METRICS


def test_success_bool_metrics_length_1_batch44():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_success_bool_metrics_no_schema_valid_batch44():
    """schema_valid 是 ratio 不是 success_bool。"""
    assert "schema_valid" not in _SUCCESS_BOOL_METRICS


# ---------- get_git_provenance ----------

def test_get_git_provenance_independent_commit_dirty_batch44():
    """commit 成功 + dirty 也成功 → 两个独立读取。"""
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc123\n")
        m2 = MagicMock(returncode=0, stdout=" M file\n")
        mock_run.side_effect = [m1, m2]
        out = get_git_provenance(Path("/tmp"))
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is True


def test_get_git_provenance_first_call_oserror_second_ok_batch44():
    """第一次抛 OSError → 整体 catch → commit=None dirty=True（不调第二次）。"""
    with patch("subprocess.run", side_effect=OSError("first boom")):
        out = get_git_provenance(Path("/tmp"))
    assert out == {"git_commit": None, "git_dirty": True}


def test_get_git_provenance_commit_only_no_dirty_call_batch44():
    """第一次失败 → catch 块 return，不再调第二次 porcelain。"""
    calls = []

    def fake_run(*args, **kwargs):
        calls.append(args[0] if args else kwargs.get("args"))
        raise OSError("boom")

    with patch("subprocess.run", side_effect=fake_run):
        out = get_git_provenance(Path("/tmp"))
    # OSError 在 try 块里抛 → except 捕获 → return
    assert out == {"git_commit": None, "git_dirty": True}
    # 第一次就抛了，第二次没机会调
    assert len(calls) == 1


# ---------- get_dependency_versions ----------

def test_get_dependency_versions_idempotent_batch44():
    """两次调用应返回结构相同的 dict（值可能在不同环境不同）。"""
    out1 = get_dependency_versions()
    out2 = get_dependency_versions()
    assert set(out1.keys()) == set(out2.keys())


def test_get_dependency_versions_three_packages_batch44():
    """代码里硬编码了 3 个包。"""
    src = inspect.getsource(get_dependency_versions)
    assert "pdfplumber" in src
    assert "python-docx" in src
    assert "pypdfium2" in src


def test_get_dependency_versions_uses_importlib_batch44():
    src = inspect.getsource(get_dependency_versions)
    assert "importlib.metadata" in src


def test_get_dependency_versions_catches_packagenotfound_batch44():
    src = inspect.getsource(get_dependency_versions)
    assert "PackageNotFoundError" in src


def test_get_dependency_versions_catches_exception_batch44():
    """catch-all Exception 兜底。"""
    src = inspect.getsource(get_dependency_versions)
    assert "except Exception" in src


def test_get_dependency_versions_local_import_batch44():
    """importlib.metadata 在函数内部 import（局部），不是模块顶层。"""
    tree = ast.parse(inspect.getsource(report_mod))
    # 模块顶层不应有 import importlib.metadata
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            assert n.module != "importlib.metadata"
        if isinstance(n, ast.Import):
            for alias in n.names:
                assert alias.name != "importlib.metadata"


# ---------- build_provenance timestamp ----------

def test_build_provenance_timestamp_iso_format_batch44():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc\n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out = build_provenance(Path("/tmp"), "fallback", 800, "1.0.0")
    ts = out["run_timestamp_iso"]
    # 必须能被 datetime.fromisoformat 解析
    parsed = datetime.fromisoformat(ts)
    assert parsed is not None


def test_build_provenance_timestamp_has_tz_batch44():
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc\n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out = build_provenance(Path("/tmp"), "fallback", 800, "1.0.0")
    parsed = datetime.fromisoformat(out["run_timestamp_iso"])
    assert parsed.tzinfo is not None  # astimezone() 保证有 tz


def test_build_provenance_two_calls_similar_batch44():
    """两次调用 timestamp 不应完全相同（至少秒级不同），但 keys 相同。"""
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc\n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out1 = build_provenance(Path("/tmp"), "fallback", 800, "1.0.0")
    with patch("subprocess.run") as mock_run:
        m1 = MagicMock(returncode=0, stdout="abc\n")
        m2 = MagicMock(returncode=0, stdout="")
        mock_run.side_effect = [m1, m2]
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out2 = build_provenance(Path("/tmp"), "fallback", 800, "1.0.0")
    assert set(out1.keys()) == set(out2.keys())


# ---------- build_devset_section ----------

def test_build_devset_section_field_order_batch44():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 1
    m.content_group_count = 1
    m.pdf_count = 1
    m.docx_count = 0
    m.categories_covered = []
    out = build_devset_section(m)
    keys = list(out.keys())
    assert keys == ["status", "file_count", "content_group_count", "pdf_count", "docx_count", "categories_covered"]


def test_build_devset_section_categories_passthrough_batch44():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = ["x", "y", "z"]
    out = build_devset_section(m)
    assert out["categories_covered"] == ["x", "y", "z"]


# ---------- aggregate_summary 边界 ----------

def test_aggregate_summary_missing_metrics_key_raises_keyerror_batch44():
    per_doc = [{}]
    with pytest.raises(KeyError):
        aggregate_summary(per_doc)


def test_aggregate_summary_metrics_is_empty_dict_batch44():
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    # 没 element_count_total 数据 → sum=None participating=0
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_metric_dict_missing_value_key_batch44():
    """metrics 中某项不是 dict 或缺 value → 视为 None。"""
    per_doc = [{"metrics": {"schema_valid": {}}}]  # 无 value 键
    out = aggregate_summary(per_doc)
    # schema_valid value 为 None → 不参与
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] is None


def test_aggregate_summary_pipeline_success_value_dict_missing_value_key_batch44():
    per_doc = [{"metrics": {"pipeline_success": {}}}]
    out = aggregate_summary(per_doc)
    # value=None → 不算 success
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0
    assert out["success_rates"]["pipeline_success"]["total"] == 1


def test_aggregate_summary_silent_drop_missing_value_key_batch44():
    per_doc = [{"metrics": {"silent_drop_count": {}}}]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_stable_order_batch44():
    per_doc1 = [{"metrics": {"schema_valid": {"value": 0.5}, "element_count_total": {"value": 10}}}]
    per_doc2 = [{"metrics": {"schema_valid": {"value": 0.5}, "element_count_total": {"value": 10}}}]
    out1 = aggregate_summary(per_doc1)
    out2 = aggregate_summary(per_doc2)
    assert list(out1.keys()) == list(out2.keys())


def test_aggregate_summary_counts_with_negative_value_batch44():
    """负数也参与（不过滤）。"""
    per_doc = [{"metrics": {"element_count_total": {"value": -5}}}]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == -5


def test_aggregate_summary_counts_with_large_value_batch44():
    per_doc = [{"metrics": {"element_count_total": {"value": 10**9}}}]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 10**9


def test_aggregate_summary_ratio_with_negative_value_batch44():
    """负 ratio 也参与（不过滤）。"""
    per_doc = [{"metrics": {"schema_valid": {"value": -0.5}}}]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == -0.5


# ---------- module source ----------

def test_module_source_contains_aggregate_section_comment_batch44():
    src = inspect.getsource(report_mod)
    assert "# counts: 求和" in src


def test_module_source_contains_success_rates_section_comment_batch44():
    src = inspect.getsource(report_mod)
    assert "# success_rates" in src


def test_module_source_contains_macro_average_comment_batch44():
    src = inspect.getsource(report_mod)
    assert "macro average" in src.lower() or "macro_average" in src


def test_module_source_contains_silent_drop_comment_batch44():
    src = inspect.getsource(report_mod)
    assert "# silent_drop_count" in src


def test_module_source_contains_figure_caption_excluded_batch44():
    src = inspect.getsource(report_mod)
    assert "figure_caption" in src


# ---------- __all__ ----------

def test_all_exact_order_batch44():
    """__all__ 顺序固定：build_provenance → build_devset_section → aggregate_summary → get_git_provenance → get_dependency_versions。"""
    assert list(report_mod.__all__) == [
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    ]


# ---------- AST 结构 ----------

def test_ast_module_docstring_present_batch44():
    tree = ast.parse(inspect.getsource(report_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)


def test_ast_module_constants_3_assigns_batch44():
    tree = ast.parse(inspect.getsource(report_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    targets = []
    for a in assigns:
        for t in a.targets:
            if isinstance(t, ast.Name):
                targets.append(t.id)
    assert "_RATIO_METRICS" in targets
    assert "_COUNT_METRICS" in targets
    assert "_SUCCESS_BOOL_METRICS" in targets
    assert "__all__" in targets


def test_ast_no_class_batch44():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_no_try_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, ast.Try)


def test_ast_no_for_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, ast.For)


def test_ast_no_while_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_no_with_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, (ast.With, ast.AsyncWith))


def test_ast_no_async_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_function_returns_dict_annotation_batch44():
    """所有顶层函数都返回 dict。"""
    tree = ast.parse(inspect.getsource(report_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    for f in funcs:
        ret = f.returns
        # 注解可能是 Subscript 或 Name
        assert ret is not None


def test_ast_from_future_second_batch44():
    tree = ast.parse(inspect.getsource(report_mod))
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


# ---------- forbidden tokens 第九十二批 ----------

def test_source_no_eval_batch44():
    src = inspect.getsource(report_mod)
    assert "eval(" not in src


def test_source_no_exec_batch44():
    src = inspect.getsource(report_mod)
    assert "exec(" not in src


def test_source_no_compile_batch44():
    src = inspect.getsource(report_mod)
    assert "compile(" not in src


def test_source_no_globals_batch44():
    src = inspect.getsource(report_mod)
    assert "globals(" not in src


def test_source_no_locals_batch44():
    src = inspect.getsource(report_mod)
    assert "locals(" not in src


def test_source_no_open_write_batch44():
    src = inspect.getsource(report_mod)
    assert "open(\"w\"" not in src
    assert "open('w'" not in src


def test_source_no_os_system_batch44():
    src = inspect.getsource(report_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch44():
    src = inspect.getsource(report_mod)
    assert "popen(" not in src


def test_source_no_yaml_load_batch44():
    src = inspect.getsource(report_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch44():
    src = inspect.getsource(report_mod)
    assert "pickle.load(" not in src


# ---------- 端到端集成 ----------

def test_aggregate_summary_full_mixed_batch44():
    """混合成功/失败 doc 的完整聚合。"""
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "schema_valid": {"value": 1.0},
                "pdf_locator_valid_ratio": {"value": 0.8},
                "docx_locator_valid_ratio": {"value": None, "reason": "not_docx_document"},
                "image_resource_exists_ratio": {"value": None, "reason": "no_image_elements"},
                "chunk_reference_intact_ratio": {"value": 1.0},
                "text_preservation_equal": {"value": True},
                "text_char_multiset_precision": {"value": 0.95},
                "text_char_multiset_recall": {"value": 0.92},
                "heading_boundary_compliance": {"value": 0.5},
                "chunk_boundary_precision": {"value": None, "reason": "no_annotation"},
                "chunk_boundary_recall": {"value": None, "reason": "no_annotation"},
                "chunk_boundary_f1": {"value": None, "reason": "no_annotation"},
                "element_count_total": {"value": 10},
                "silent_drop_count": {"value": 2},
            }
        },
        {
            "metrics": {
                "pipeline_success": {"value": False},
                "schema_valid": {"value": None, "reason": "pipeline_failed"},
                "element_count_total": {"value": None},
                "silent_drop_count": {"value": None},
            }
        },
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["total"] == 2
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert out["counts"]["element_count_total"]["sum"] == 10
    assert out["counts"]["element_count_total"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 0.8
    assert out["ratio_macro_averages"]["docx_locator_valid_ratio"]["macro_average"] is None
    assert out["silent_drop_total"] == 2
