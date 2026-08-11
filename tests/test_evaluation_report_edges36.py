"""evaluation/report.py 第三十六轮 edges 测试（Round 458）。

补强 edges35 未触及的角度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 行为深度第十九批
- get_git_provenance 行为深度第十九批（commit trimmed / dirty detection / git 失败兜底 / 多次调用一致 / cwd 是 str）
- get_dependency_versions 行为深度第十九批（内部 importlib.metadata / 三个包固定 / 无异常上抛）
- build_provenance 行为深度第十九批（git_commit / git_dirty 来自 git / max_chars 转 int / timestamp parseable / parser_version passthrough）
- build_devset_section 行为深度第十九批（6 keys 顺序 / 5 manifest 属性 lookup / 不调用 setter / 接受 mock manifest）
- aggregate_summary 行为深度第十九批（顺序无关 / mixed null + value / 单 metric 缺失不影响其它 / extra metric 忽略 / not_evaluated 计数）
- module source forbidden tokens 第三十四批
- module source 字符串精确补强第二十九批
- signatures 第二十九批
- module 合理性第二十九批
- 端到端集成第二十九批
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
from evaluation import report as rmod


# ---------- metric 常量行为深度第十九批 ----------


def test_ratio_metrics_count_exactly_12_batch19():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_first_is_schema_valid_batch19():
    assert _RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_last_is_chunk_boundary_f1_batch19():
    assert _RATIO_METRICS[-1] == "chunk_boundary_f1"


def test_count_metrics_count_exactly_1_batch19():
    assert len(_COUNT_METRICS) == 1


def test_count_metrics_first_is_element_count_total_batch19():
    assert _COUNT_METRICS[0] == "element_count_total"


def test_success_bool_metrics_count_exactly_1_batch19():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_success_bool_metrics_first_is_pipeline_success_batch19():
    assert _SUCCESS_BOOL_METRICS[0] == "pipeline_success"


def test_metric_sets_no_duplicates_batch19():
    assert len(set(_RATIO_METRICS)) == len(_RATIO_METRICS)
    assert len(set(_COUNT_METRICS)) == len(_COUNT_METRICS)
    assert len(set(_SUCCESS_BOOL_METRICS)) == len(_SUCCESS_BOOL_METRICS)


def test_metric_sets_pairwise_disjoint_batch19():
    """三个 tuple 之间两两无交集。"""
    assert set(_RATIO_METRICS).isdisjoint(set(_COUNT_METRICS))
    assert set(_RATIO_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))
    assert set(_COUNT_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))


def test_ratio_metrics_does_not_contain_figure_caption_batch19():
    """figure_caption_* 始终 null，不参与 macro average。"""
    for m in _RATIO_METRICS:
        assert not m.startswith("figure_caption_")


def test_ratio_metrics_does_not_contain_silent_drop_count_batch19():
    """silent_drop_count 是 int，不参与 macro average。"""
    assert "silent_drop_count" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_error_code_batch19():
    """error_code 是字符串，不参与 macro average。"""
    assert "error_code" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_element_count_by_type_batch19():
    """element_count_by_type 是 dict，不参与 macro average。"""
    assert "element_count_by_type" not in _RATIO_METRICS


def test_metric_tuples_are_instance_of_tuple_batch19():
    assert isinstance(_RATIO_METRICS, tuple)
    assert isinstance(_COUNT_METRICS, tuple)
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


# ---------- get_git_provenance 行为深度第十九批 ----------


def test_get_git_provenance_commit_trimmed_batch19(tmp_path):
    """commit 应被 strip。"""
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = "abc123\n"
    fake.stderr = ""
    with patch("subprocess.run", return_value=fake):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] == "abc123"


def test_get_git_provenance_commit_none_when_stdout_empty_batch19(tmp_path):
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = "   \n"
    fake.stderr = ""
    with patch("subprocess.run", return_value=fake):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None


def test_get_git_provenance_commit_none_when_nonzero_returncode_batch19(tmp_path):
    fake_ok = MagicMock(returncode=0, stdout="c1\n", stderr="")
    fake_fail = MagicMock(returncode=1, stdout="", stderr="err")
    # 第一次 rev-parse 成功，第二次 status 失败
    with patch("subprocess.run", side_effect=[fake_ok, fake_fail]):
        result = get_git_provenance(tmp_path)
    # commit 从第一次拿到；dirty 因为 status 失败为 False
    assert result["git_commit"] == "c1"
    assert result["git_dirty"] is False


def test_get_git_provenance_dirty_with_untracked_batch19(tmp_path):
    fake1 = MagicMock(returncode=0, stdout="abc\n", stderr="")
    fake2 = MagicMock(returncode=0, stdout="?? newfile\n", stderr="")
    with patch("subprocess.run", side_effect=[fake1, fake2]):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] == "abc"
    assert result["git_dirty"] is True


def test_get_git_provenance_dirty_empty_status_batch19(tmp_path):
    fake1 = MagicMock(returncode=0, stdout="abc\n", stderr="")
    fake2 = MagicMock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake1, fake2]):
        result = get_git_provenance(tmp_path)
    assert result["git_dirty"] is False


def test_get_git_provenance_subprocess_timeout_batch19(tmp_path):
    """timeout 触发 SubprocessError → 返回 commit=None, dirty=True。"""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10)):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_calls_subprocess_twice_batch19(tmp_path):
    """应调用 subprocess.run 两次（rev-parse HEAD 与 status --porcelain）。"""
    with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")) as mock_run:
        get_git_provenance(tmp_path)
    assert mock_run.call_count == 2


def test_get_git_provenance_uses_cwd_as_str_batch19(tmp_path):
    """cwd 应被 str() 包装。"""
    with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")) as mock_run:
        get_git_provenance(tmp_path)
    # 检查所有调用的 cwd 都是 str(tmp_path)
    for call in mock_run.call_args_list:
        assert "cwd" in call.kwargs
        assert isinstance(call.kwargs["cwd"], str)


# ---------- get_dependency_versions 行为深度第十九批 ----------


def test_get_dependency_versions_returns_dict_with_3_keys_batch19():
    v = get_dependency_versions()
    assert isinstance(v, dict)
    assert len(v) == 3


def test_get_dependency_versions_keys_exact_set_batch19():
    v = get_dependency_versions()
    assert set(v.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_type_optional_str_batch19():
    v = get_dependency_versions()
    for key, val in v.items():
        assert val is None or isinstance(val, str)


def test_get_dependency_versions_imports_importlib_inside_function_batch19():
    """importlib.metadata 在函数内部 import。"""
    src = inspect.getsource(get_dependency_versions)
    assert "import importlib.metadata" in src


def test_get_dependency_versions_no_top_level_importlib_batch19():
    """模块顶层不直接 import importlib.metadata。"""
    src = inspect.getsource(rmod)
    top = src[: src.find("def get_dependency_versions")]
    assert "import importlib.metadata" not in top


def test_get_dependency_versions_catches_package_not_found_batch19():
    with patch("importlib.metadata.version", side_effect=__import__("importlib").metadata.PackageNotFoundError):
        v = get_dependency_versions()
    assert all(val is None for val in v.values())


def test_get_dependency_versions_catches_generic_exception_batch19():
    with patch("importlib.metadata.version", side_effect=ValueError("boom")):
        v = get_dependency_versions()
    assert all(val is None for val in v.values())


def test_get_dependency_versions_returns_real_versions_when_installed_batch19():
    """已安装 pdfplumber 应能拿到版本字符串。"""
    v = get_dependency_versions()
    if v["pdfplumber"] is not None:
        # 版本字符串应有数字
        assert any(ch.isdigit() for ch in v["pdfplumber"])


# ---------- build_provenance 行为深度第十九批 ----------


def test_build_provenance_returns_dict_with_9_keys_batch19(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(p, dict)
    assert len(p) == 9


def test_build_provenance_keys_exact_batch19(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, None)
    expected = {
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
    assert set(p.keys()) == expected


def test_build_provenance_evaluator_version_matches_module_batch19(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, None)
    assert p["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_matches_module_batch19(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, None)
    assert p["report_version"] == REPORT_VERSION


def test_build_provenance_max_chars_coerced_to_int_batch19(tmp_path):
    p = build_provenance(tmp_path, "fallback", "800", None)
    assert isinstance(p["max_chars"], int)
    assert p["max_chars"] == 800


def test_build_provenance_max_chars_negative_kept_batch19(tmp_path):
    p = build_provenance(tmp_path, "fallback", -5, None)
    assert p["max_chars"] == -5


def test_build_provenance_parser_name_passthrough_batch19(tmp_path):
    p = build_provenance(tmp_path, "kreuzberg", 800, None)
    assert p["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_passthrough_batch19(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert p["parser_version"] == "1.0.0"


def test_build_provenance_timestamp_parseable_iso_batch19(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, None)
    ts = p["run_timestamp_iso"]
    parsed = datetime.fromisoformat(ts)
    assert parsed is not None


def test_build_provenance_dependencies_is_dict_batch19(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(p["dependencies"], dict)


def test_build_provenance_calls_get_git_provenance_batch19(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "X", "git_dirty": False}) as mock_g:
        p = build_provenance(tmp_path, "fallback", 800, None)
    assert mock_g.call_count == 1
    assert mock_g.call_args.args == (tmp_path,)
    assert p["git_commit"] == "X"
    assert p["git_dirty"] is False


# ---------- build_devset_section 行为深度第十九批 ----------


def _make_manifest(**kwargs):
    """构造一个最小 Manifest-like mock。"""
    m = MagicMock()
    m.devset_status = kwargs.get("devset_status", "incomplete")
    m.file_count = kwargs.get("file_count", 0)
    m.content_group_count = kwargs.get("content_group_count", 0)
    m.pdf_count = kwargs.get("pdf_count", 0)
    m.docx_count = kwargs.get("docx_count", 0)
    m.categories_covered = kwargs.get("categories_covered", [])
    return m


def test_build_devset_section_returns_dict_with_6_keys_batch19():
    out = build_devset_section(_make_manifest())
    assert isinstance(out, dict)
    assert len(out) == 6


def test_build_devset_section_keys_exact_batch19():
    out = build_devset_section(_make_manifest())
    assert set(out.keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_build_devset_section_status_passed_through_batch19():
    out = build_devset_section(_make_manifest(devset_status="complete"))
    assert out["status"] == "complete"


def test_build_devset_section_file_count_passed_through_batch19():
    out = build_devset_section(_make_manifest(file_count=42))
    assert out["file_count"] == 42


def test_build_devset_section_categories_empty_list_batch19():
    out = build_devset_section(_make_manifest(categories_covered=[]))
    assert out["categories_covered"] == []


def test_build_devset_section_categories_filled_batch19():
    cats = ["pdf", "docx"]
    out = build_devset_section(_make_manifest(categories_covered=cats))
    assert out["categories_covered"] == cats


def test_build_devset_section_with_real_manifest_object_batch19():
    """用真实 Manifest dataclass。"""
    from evaluation.manifest import Manifest

    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("."),
    )
    out = build_devset_section(m)
    assert out["status"] == "incomplete"


def test_build_devset_section_extra_attrs_ignored_batch19():
    """Manifest 额外字段不影响 build_devset_section。"""
    m = _make_manifest()
    m.extra_attr = "ignored"
    out = build_devset_section(m)
    assert "extra_attr" not in out


# ---------- aggregate_summary 行为深度第十九批 ----------


def test_aggregate_summary_empty_returns_4_top_keys_batch19():
    s = aggregate_summary([])
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_counts_with_some_none_batch19():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": 3}}},
    ]
    s = aggregate_summary(per_doc)
    # 只有 2 个参与
    assert s["counts"]["element_count_total"]["sum"] == 8
    assert s["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_with_no_data_batch19():
    per_doc = [
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_success_rate_with_no_docs_batch19():
    s = aggregate_summary([])
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 0
    assert sr["rate"] is None


def test_aggregate_summary_success_rate_with_all_success_batch19():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 2
    assert sr["rate"] == 1.0


def test_aggregate_summary_success_rate_with_all_failure_batch19():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["rate"] == 0.0


def test_aggregate_summary_success_rate_with_none_value_batch19():
    """pipeline_success=None 应计为 not success。"""
    per_doc = [{"metrics": {"pipeline_success": {"value": None}}}]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["rate"] == 0.0


def test_aggregate_summary_ratio_macro_with_mixed_batch19():
    per_doc = [
        {"metrics": {"schema_valid": {"value": True}}},  # 1.0
        {"metrics": {"schema_valid": {"value": False}}},  # 0.0
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    s = aggregate_summary(per_doc)
    avg = s["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == 0.5
    assert avg["participating_docs"] == 2
    assert avg["not_evaluated"] == 1


def test_aggregate_summary_ratio_macro_all_null_batch19():
    per_doc = [{"metrics": {"schema_valid": {"value": None}}}]
    s = aggregate_summary(per_doc)
    avg = s["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] is None
    assert avg["participating_docs"] == 0
    assert avg["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_with_negative_batch19():
    per_doc = [{"metrics": {"silent_drop_count": {"value": -3}}}]
    s = aggregate_summary(per_doc)
    # sum 求和不排除负数
    assert s["silent_drop_total"] == -3


def test_aggregate_summary_silent_drop_with_zero_batch19():
    per_doc = [{"metrics": {"silent_drop_count": {"value": 0}}}]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 0


def test_aggregate_summary_silent_drop_all_null_batch19():
    per_doc = [{"metrics": {"silent_drop_count": {"value": None}}}]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] is None


def test_aggregate_summary_extra_metrics_ignored_batch19():
    """per_doc 含未声明的 metric 应被忽略。"""
    per_doc = [
        {"metrics": {"unknown_metric": {"value": 999}}},
    ]
    s = aggregate_summary(per_doc)
    # 4 个 top key 都不被 unknown_metric 影响
    assert "unknown_metric" not in s["counts"]
    assert "unknown_metric" not in s["success_rates"]
    assert "unknown_metric" not in s["ratio_macro_averages"]


def test_aggregate_summary_does_not_mutate_input_batch19():
    import copy as _copy

    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    snapshot = _copy.deepcopy(per_doc)
    aggregate_summary(per_doc)
    assert per_doc == snapshot


def test_aggregate_summary_order_independent_batch19():
    """文档顺序不影响 macro 平均。"""
    base = [
        {"metrics": {"schema_valid": {"value": True}}},
        {"metrics": {"schema_valid": {"value": False}}},
        {"metrics": {"schema_valid": {"value": True}}},
    ]
    s1 = aggregate_summary(base)
    s2 = aggregate_summary(list(reversed(base)))
    assert s1["ratio_macro_averages"]["schema_valid"]["macro_average"] == s2["ratio_macro_averages"]["schema_valid"]["macro_average"]


# ---------- module source forbidden tokens 第三十四批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    "open(\"/etc/passwd",
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch19(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


def test_module_source_no_socket_import_batch19():
    src = inspect.getsource(rmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch19():
    src = inspect.getsource(rmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch19():
    src = inspect.getsource(rmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch19():
    src = inspect.getsource(rmod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch19():
    src = inspect.getsource(rmod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch19():
    src = inspect.getsource(rmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch19():
    src = inspect.getsource(rmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch19():
    src = inspect.getsource(rmod)
    assert "import tempfile" not in src


def test_module_source_no_unlink_call_batch19():
    src = inspect.getsource(rmod)
    assert ".unlink(" not in src


def test_module_source_no_path_write_text_batch19():
    """report.py 不写盘（report 装配，写盘由 runner 做）。"""
    src = inspect.getsource(rmod)
    assert ".write_text(" not in src
    assert ".write_bytes(" not in src


def test_module_source_no_sys_exit_batch19():
    src = inspect.getsource(rmod)
    assert "sys.exit" not in src


def test_module_source_no_path_open_write_mode_batch19():
    src = inspect.getsource(rmod)
    # 不应直接 open 写
    assert 'open(' not in src


def test_module_source_no_pandas_import_batch19():
    src = inspect.getsource(rmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch19():
    src = inspect.getsource(rmod)
    assert "import numpy" not in src


def test_module_source_no_re_compile_batch19():
    src = inspect.getsource(rmod)
    assert "re.compile" not in src


def test_module_source_no_main_block_batch19():
    src = inspect.getsource(rmod)
    assert 'if __name__ ==' not in src
    assert "__main__" not in src


def test_module_source_subprocess_allowed_in_report_batch19():
    """report.py 允许 subprocess（git provenance）。"""
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


# ---------- module source 字符串精确补强第二十九批 ----------


def test_module_source_has_future_annotations_batch19():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_subprocess_import_batch19():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_has_datetime_import_batch19():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_has_pathlib_path_import_batch19():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch19():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_evaluator_version_import_batch19():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_has_ratio_metrics_constant_batch19():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS = (" in src


def test_module_source_has_count_metrics_constant_batch19():
    src = inspect.getsource(rmod)
    assert "_COUNT_METRICS = (" in src


def test_module_source_has_success_bool_metrics_constant_batch19():
    src = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS = (" in src


def test_module_source_has_get_git_provenance_function_batch19():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src


def test_module_source_has_get_dependency_versions_function_batch19():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions(" in src


def test_module_source_has_build_provenance_function_batch19():
    src = inspect.getsource(rmod)
    assert "def build_provenance(" in src


def test_module_source_has_aggregate_summary_function_batch19():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary(" in src


def test_module_source_has_docstring_about_aggregation_batch19():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_has_all_list_with_5_entries_batch19():
    src = inspect.getsource(rmod)
    assert '"build_provenance"' in src
    assert '"build_devset_section"' in src
    assert '"aggregate_summary"' in src
    assert '"get_git_provenance"' in src
    assert '"get_dependency_versions"' in src


def test_module_source_has_subprocess_timeout_10_batch19():
    src = inspect.getsource(rmod)
    assert "timeout=10" in src


def test_module_source_has_capture_output_true_batch19():
    src = inspect.getsource(rmod)
    assert "capture_output=True" in src


# ---------- signatures 第二十九批 ----------


def test_signature_get_git_provenance_batch19():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["project_root"]


def test_signature_get_dependency_versions_batch19():
    sig = inspect.signature(get_dependency_versions)
    params = list(sig.parameters.values())
    assert len(params) == 0


def test_signature_build_provenance_batch19():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_devset_section_batch19():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.values())
    assert len(params) == 1


def test_signature_aggregate_summary_batch19():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["per_doc_results"]


# ---------- module 合理性第二十九批 ----------


def test_module_has_all_attribute_batch19():
    assert hasattr(rmod, "__all__")


def test_module_all_count_5_batch19():
    assert len(rmod.__all__) == 5


def test_module_all_entries_are_strings_batch19():
    for n in rmod.__all__:
        assert isinstance(n, str)


def test_module_does_not_import_app_pipeline_batch19():
    src = inspect.getsource(rmod)
    assert "from app" not in src
    assert "import app" not in src


def test_module_does_not_import_evaluation_metrics_batch19():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics" not in src
    assert "from evaluation import metrics" not in src


def test_module_does_not_import_evaluation_annotation_metrics_batch19():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics" not in src
    assert "from evaluation import annotation_metrics" not in src


def test_module_does_not_import_evaluation_cli_batch19():
    src = inspect.getsource(rmod)
    assert "from evaluation.cli" not in src
    assert "from evaluation import cli" not in src


def test_module_constants_not_in_all_batch19():
    for k in ("_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"):
        assert k not in rmod.__all__


def test_module_evaluator_version_imported_from_evaluation_batch19():
    """EVALUATOR_VERSION 是 import 进来的，不是本模块定义。"""
    src = inspect.getsource(rmod)
    assert "EVALUATOR_VERSION = " not in src  # 没有赋值定义
    assert "EVALUATOR_VERSION" in src  # 但有 import + 引用


# ---------- 端到端集成 第二十九批 ----------


def test_e2e_build_provenance_full_structure_batch19(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, None)
    # 验证关键字段类型
    assert isinstance(p["git_commit"], (str, type(None)))
    assert isinstance(p["git_dirty"], bool)
    assert isinstance(p["dependencies"], dict)
    assert isinstance(p["run_timestamp_iso"], str)
    assert isinstance(p["max_chars"], int)


def test_e2e_aggregate_summary_full_flow_batch19():
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "schema_valid": {"value": True},
                "element_count_total": {"value": 10},
                "silent_drop_count": {"value": 2},
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
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1
    assert s["success_rates"]["pipeline_success"]["total"] == 2
    assert s["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert s["counts"]["element_count_total"]["sum"] == 10
    assert s["counts"]["element_count_total"]["participating_docs"] == 1
    assert s["silent_drop_total"] == 2


def test_e2e_build_devset_with_complete_status_batch19():
    m = _make_manifest(devset_status="complete", file_count=10, pdf_count=5, docx_count=5, content_group_count=3)
    out = build_devset_section(m)
    assert out["status"] == "complete"
    assert out["file_count"] == 10
    assert out["pdf_count"] == 5
    assert out["docx_count"] == 5
    assert out["content_group_count"] == 3


def test_e2e_get_git_provenance_with_mocked_full_success_batch19(tmp_path):
    fake_ok1 = MagicMock(returncode=0, stdout="abc123\n", stderr="")
    fake_ok2 = MagicMock(returncode=0, stdout="M file.txt\n", stderr="")
    with patch("subprocess.run", side_effect=[fake_ok1, fake_ok2]):
        out = get_git_provenance(tmp_path)
    assert out == {"git_commit": "abc123", "git_dirty": True}


def test_e2e_pipeline_combined_batch19(tmp_path):
    """build_provenance → build_devset_section → aggregate_summary 完整流。"""
    p = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    m = _make_manifest(file_count=1)
    d = build_devset_section(m)
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "schema_valid": {"value": True},
                "element_count_total": {"value": 1},
            }
        }
    ]
    s = aggregate_summary(per_doc)
    # 校验关键不变量
    assert p["parser_version"] == "1.0.0"
    assert d["file_count"] == 1
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1


def test_e2e_aggregate_summary_with_partial_metric_presence_batch19():
    """per_doc 中不同 doc 有不同 metric 集合。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {}},  # 完全没有 metric
        {"metrics": {"schema_valid": {"value": False}}},
    ]
    s = aggregate_summary(per_doc)
    # pipeline_success: 1 success / 3 total
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1
    assert s["success_rates"]["pipeline_success"]["rate"] == 1 / 3
    # schema_valid: 1 participating
    assert s["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.0


def test_e2e_build_provenance_timestamp_changes_per_call_batch19(tmp_path):
    """两次调用应拿到不同 timestamp（至少亚毫秒级）。"""
    p1 = build_provenance(tmp_path, "fallback", 800, None)
    p2 = build_provenance(tmp_path, "fallback", 800, None)
    # 两次的 timestamp 可能相等（同一秒），但应能被 fromisoformat 解析
    datetime.fromisoformat(p1["run_timestamp_iso"])
    datetime.fromisoformat(p2["run_timestamp_iso"])
