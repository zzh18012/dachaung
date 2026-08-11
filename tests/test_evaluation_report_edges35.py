"""evaluation/report.py 第三十五轮 edges 测试（Round 451）。

补强 edges34 未触及的角度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元组深度第十八批（schema_valid not in success / pipeline_success not in ratio / element_count_total not in ratio / 元组 disjoint / 各元素是 string）
- get_git_provenance 行为深度第十八批（project_root 是文件 / project_root 不存在 / stdout 多行 / value 类型 / commit None / dirty True 默认）
- get_dependency_versions 行为深度第十八批（无 IO 直接 dict / 不抛 timeout / keys count 3 / unknown 异常 / value None or str）
- build_provenance 字段深度第十八批（max_chars 负数 / parser_name 空 / dependencies 是 dict / timestamp 含时区 / 9 keys / timestamp 类型 str）
- build_devset_section 字段深度第十八批（returns dict / 6 keys / status str / categories list / 不调 setter / manifest 是 MagicMock）
- aggregate_summary 行为深度第十八批（empty list / 单 participant / 多 participant / mixed metrics / counts sum with None / silent_drop 0/multi）
- module source forbidden tokens 第三十二批
- module source 字符串精确补强第二十八批
- signatures 第二十八批
- module 合理性第二十八批
- 端到端集成第二十八批
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元组深度第十八批 ----------


def test_ratio_metrics_count_12_batch18():
    assert len(_RATIO_METRICS) == 12


def test_count_metrics_count_1_batch18():
    assert len(_COUNT_METRICS) == 1


def test_success_bool_metrics_count_1_batch18():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_count_metrics_element_count_total_batch18():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_metrics_pipeline_success_batch18():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_ratio_metrics_contains_schema_valid_batch18():
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_contains_all_chunk_boundary_batch18():
    assert "chunk_boundary_precision" in _RATIO_METRICS
    assert "chunk_boundary_recall" in _RATIO_METRICS
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_pipeline_success_batch18():
    assert "pipeline_success" not in _RATIO_METRICS


def test_ratio_metrics_does_not_contain_element_count_batch18():
    assert "element_count_total" not in _RATIO_METRICS


def test_count_metrics_does_not_contain_pipeline_success_batch18():
    assert "pipeline_success" not in _COUNT_METRICS


def test_success_metrics_does_not_contain_schema_valid_batch18():
    assert "schema_valid" not in _SUCCESS_BOOL_METRICS


def test_metric_tuples_disjoint_batch18():
    """3 个元组互不相交。"""
    s1 = set(_RATIO_METRICS)
    s2 = set(_COUNT_METRICS)
    s3 = set(_SUCCESS_BOOL_METRICS)
    assert s1.isdisjoint(s2)
    assert s1.isdisjoint(s3)
    assert s2.isdisjoint(s3)


def test_metric_tuples_all_strings_batch18():
    for t in (_RATIO_METRICS, _COUNT_METRICS, _SUCCESS_BOOL_METRICS):
        for x in t:
            assert isinstance(x, str)


def test_metric_tuples_are_tuples_batch18():
    assert isinstance(_RATIO_METRICS, tuple)
    assert isinstance(_COUNT_METRICS, tuple)
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


# ---------- get_git_provenance 行为深度第十八批 ----------


def test_get_git_provenance_returns_dict_batch18(tmp_path):
    r = get_git_provenance(tmp_path)
    assert isinstance(r, dict)


def test_get_git_provenance_keys_count_2_batch18(tmp_path):
    r = get_git_provenance(tmp_path)
    assert set(r.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_value_types_batch18(tmp_path):
    r = get_git_provenance(tmp_path)
    # git_commit 可以是 None 或 str
    assert r["git_commit"] is None or isinstance(r["git_commit"], str)
    assert isinstance(r["git_dirty"], bool)


def test_get_git_provenance_nonexistent_root_batch18():
    """不存在的 project_root → OSError → commit None + dirty True。"""
    r = get_git_provenance(Path("/nonexistent/path/that/does/not/exist"))
    assert r["git_commit"] is None
    assert r["git_dirty"] is True


def test_get_git_provenance_file_as_root_batch18(tmp_path):
    """传文件路径作为 root → git 会在该路径上失败 → 返回 None/True。"""
    p = tmp_path / "a.txt"
    p.write_text("x", encoding="utf-8")
    r = get_git_provenance(p)
    # 不会抛异常；返回 dict
    assert isinstance(r, dict)
    assert "git_commit" in r


def test_get_git_provenance_with_mock_success_batch18(tmp_path):
    """模拟 git 命令成功。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        # 第一次 rev-parse HEAD，第二次 status --porcelain
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n"),
            MagicMock(returncode=0, stdout=""),  # clean
        ]
        r = get_git_provenance(tmp_path)
    assert r["git_commit"] == "abc123"
    assert r["git_dirty"] is False


def test_get_git_provenance_with_dirty_batch18(tmp_path):
    """git status 输出非空 → dirty=True。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n"),
            MagicMock(returncode=0, stdout=" M file.txt\n"),
        ]
        r = get_git_provenance(tmp_path)
    assert r["git_dirty"] is True


def test_get_git_provenance_rev_parse_failure_batch18(tmp_path):
    """rev-parse 失败 → commit None。"""
    with patch("evaluation.report.subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=128, stdout=""),
            MagicMock(returncode=0, stdout=""),
        ]
        r = get_git_provenance(tmp_path)
    assert r["git_commit"] is None


def test_get_git_provenance_subprocess_exception_batch18(tmp_path):
    """subprocess 抛异常 → caught → 默认 None/True。"""
    with patch("evaluation.report.subprocess.run",
               side_effect=subprocess.SubprocessError("boom")):
        r = get_git_provenance(tmp_path)
    assert r["git_commit"] is None
    assert r["git_dirty"] is True


def test_get_git_provenance_oserror_batch18(tmp_path):
    """OSError 也 caught。"""
    with patch("evaluation.report.subprocess.run",
               side_effect=OSError("boom")):
        r = get_git_provenance(tmp_path)
    assert r["git_commit"] is None
    assert r["git_dirty"] is True


# ---------- get_dependency_versions 行为深度第十八批 ----------


def test_get_dependency_versions_returns_dict_batch18():
    r = get_dependency_versions()
    assert isinstance(r, dict)


def test_get_dependency_versions_keys_count_3_batch18():
    r = get_dependency_versions()
    assert len(r) == 3


def test_get_dependency_versions_keys_contents_batch18():
    r = get_dependency_versions()
    assert set(r.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_type_batch18():
    r = get_dependency_versions()
    for k, v in r.items():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_no_timeout_batch18():
    """快速返回（不挂）。"""
    import time
    t0 = time.time()
    get_dependency_versions()
    assert time.time() - t0 < 5.0


def test_get_dependency_versions_with_package_not_found_batch18():
    """mock importlib.metadata.PackageNotFoundError → None。"""
    import importlib.metadata
    with patch("importlib.metadata.version",
               side_effect=importlib.metadata.PackageNotFoundError):
        r = get_dependency_versions()
    for v in r.values():
        assert v is None


def test_get_dependency_versions_with_unknown_exception_batch18():
    """mock importlib.metadata 抛 Exception → None。"""
    with patch("importlib.metadata.version",
               side_effect=RuntimeError("unexpected")):
        r = get_dependency_versions()
    for v in r.values():
        assert v is None


# ---------- build_provenance 字段深度第十八批 ----------


def test_build_provenance_returns_dict_batch18(tmp_path):
    r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert isinstance(r, dict)


def test_build_provenance_keys_count_9_batch18(tmp_path):
    r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert len(r) == 9


def test_build_provenance_keys_names_batch18(tmp_path):
    r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    expected_keys = {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    }
    assert set(r.keys()) == expected_keys


def test_build_provenance_evaluator_version_constant_batch18(tmp_path):
    r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert r["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_constant_batch18(tmp_path):
    r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert r["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_batch18(tmp_path):
    r = build_provenance(tmp_path, "kreuzberg", 800, "2.0")
    assert r["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_none_batch18(tmp_path):
    r = build_provenance(tmp_path, "fallback", 800, None)
    assert r["parser_version"] is None


def test_build_provenance_max_chars_negative_batch18(tmp_path):
    """max_chars 负数 → int(-1)（不校验）。"""
    r = build_provenance(tmp_path, "fallback", -1, "1.0")
    assert r["max_chars"] == -1


def test_build_provenance_max_chars_string_int_batch18(tmp_path):
    """max_chars 是 string → int() 转换。"""
    r = build_provenance(tmp_path, "fallback", "800", "1.0")
    assert r["max_chars"] == 800


def test_build_provenance_max_chars_zero_batch18(tmp_path):
    r = build_provenance(tmp_path, "fallback", 0, "1.0")
    assert r["max_chars"] == 0


def test_build_provenance_dependencies_is_dict_batch18(tmp_path):
    r = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert isinstance(r["dependencies"], dict)


def test_build_provenance_timestamp_iso_batch18(tmp_path):
    r = build_provenance(tmp_path, "fallback", 800, "1.0")
    ts = r["run_timestamp_iso"]
    assert isinstance(ts, str)
    # ISO 8601 format
    assert "T" in ts


def test_build_provenance_timestamp_has_timezone_batch18(tmp_path):
    r = build_provenance(tmp_path, "fallback", 800, "1.0")
    ts = r["run_timestamp_iso"]
    # 应含时区偏移（+HH:MM）
    assert "+" in ts or "-" in ts.split("T")[1]


def test_build_provenance_parser_name_empty_batch18(tmp_path):
    r = build_provenance(tmp_path, "", 800, "1.0")
    assert r["parser_name"] == ""


# ---------- build_devset_section 字段深度第十八批 ----------


def _mk_manifest():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 5
    m.content_group_count = 2
    m.pdf_count = 3
    m.docx_count = 2
    m.categories_covered = ["cat1", "cat2"]
    return m


def test_build_devset_section_returns_dict_batch18():
    r = build_devset_section(_mk_manifest())
    assert isinstance(r, dict)


def test_build_devset_section_keys_count_6_batch18():
    r = build_devset_section(_mk_manifest())
    assert len(r) == 6


def test_build_devset_section_keys_names_batch18():
    r = build_devset_section(_mk_manifest())
    assert set(r.keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_build_devset_section_status_string_batch18():
    r = build_devset_section(_mk_manifest())
    assert r["status"] == "incomplete"


def test_build_devset_section_file_count_batch18():
    r = build_devset_section(_mk_manifest())
    assert r["file_count"] == 5


def test_build_devset_section_pdf_count_batch18():
    r = build_devset_section(_mk_manifest())
    assert r["pdf_count"] == 3


def test_build_devset_section_docx_count_batch18():
    r = build_devset_section(_mk_manifest())
    assert r["docx_count"] == 2


def test_build_devset_section_categories_list_batch18():
    r = build_devset_section(_mk_manifest())
    assert isinstance(r["categories_covered"], list)


def test_build_devset_section_does_not_call_setter_batch18():
    """build_devset_section 只读 manifest，不修改。"""
    m = _mk_manifest()
    original_status = m.devset_status
    build_devset_section(m)
    assert m.devset_status == original_status


def test_build_devset_section_with_complete_status_batch18():
    m = _mk_manifest()
    m.devset_status = "complete"
    r = build_devset_section(m)
    assert r["status"] == "complete"


# ---------- aggregate_summary 行为深度第十八批 ----------


def test_aggregate_summary_empty_batch18():
    r = aggregate_summary([])
    assert isinstance(r, dict)
    assert "counts" in r
    assert "success_rates" in r
    assert "ratio_macro_averages" in r
    assert "silent_drop_total" in r


def test_aggregate_summary_silent_drop_empty_batch18():
    r = aggregate_summary([])
    assert r["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_zero_batch18():
    per_doc = [{"metrics": {"silent_drop_count": {"value": 0}}}]
    r = aggregate_summary(per_doc)
    assert r["silent_drop_total"] == 0


def test_aggregate_summary_silent_drop_multi_batch18():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 2}}},
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    r = aggregate_summary(per_doc)
    assert r["silent_drop_total"] == 10


def test_aggregate_summary_silent_drop_with_null_batch18():
    """null 值不参与 sum。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 2}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    r = aggregate_summary(per_doc)
    assert r["silent_drop_total"] == 2


def test_aggregate_summary_success_rate_full_batch18():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    r = aggregate_summary(per_doc)
    assert r["success_rates"]["pipeline_success"]["success_count"] == 2
    assert r["success_rates"]["pipeline_success"]["total"] == 2
    assert r["success_rates"]["pipeline_success"]["rate"] == 1.0


def test_aggregate_summary_success_rate_zero_batch18():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    r = aggregate_summary(per_doc)
    assert r["success_rates"]["pipeline_success"]["success_count"] == 0
    assert r["success_rates"]["pipeline_success"]["rate"] == 0.0


def test_aggregate_summary_counts_sum_batch18():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": 10}}},
    ]
    r = aggregate_summary(per_doc)
    assert r["counts"]["element_count_total"]["sum"] == 15
    assert r["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_with_none_batch18():
    """None value 不参与 sum。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    r = aggregate_summary(per_doc)
    assert r["counts"]["element_count_total"]["sum"] == 5
    assert r["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_ratio_macro_avg_batch18():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.0}}},
    ]
    r = aggregate_summary(per_doc)
    assert r["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert r["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2


def test_aggregate_summary_ratio_all_null_batch18():
    per_doc = [
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    r = aggregate_summary(per_doc)
    assert r["ratio_macro_averages"]["schema_valid"]["macro_average"] is None
    assert r["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 0
    assert r["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1


def test_aggregate_summary_has_4_top_keys_batch18():
    r = aggregate_summary([])
    assert len(r) == 4
    assert set(r.keys()) == {
        "counts", "success_rates", "ratio_macro_averages", "silent_drop_total",
    }


def test_aggregate_summary_ratio_metrics_all_present_batch18():
    """所有 _RATIO_METRICS 都在 ratio_macro_averages 里。"""
    r = aggregate_summary([])
    for name in _RATIO_METRICS:
        assert name in r["ratio_macro_averages"]


# ---------- module source forbidden tokens 第三十二批 ----------


@pytest.mark.parametrize("forbidden", [
    "pty.spawn",
    "commands.getoutput",
    "paramiko",
    "fabric.api",
    "ftplib",
    "smtplib",
    "telnetlib",
    "webbrowser.open",
    "socket.socket",
    "asyncio.open_connection",
    "multiprocessing.Process",
    "threading.Thread",
    "ctypes.CDLL",
    "pickle.dumps",
    "shutil.rmtree",
    "sys.exit",
])
def test_module_source_forbidden_tokens_batch18(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


def test_module_source_no_network_batch18():
    src = inspect.getsource(rmod)
    assert "urllib.request" not in src
    assert "import requests" not in src


def test_module_source_no_pickle_batch18():
    src = inspect.getsource(rmod)
    assert "import pickle" not in src


# ---------- module source 字符串精确补强第二十八批 ----------


def test_module_source_has_future_annotations_batch18():
    src = inspect.getsource(rmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch18():
    src = inspect.getsource(rmod)
    assert "评测报告" in src


def test_module_source_has_subprocess_import_batch18():
    """report.py 唯一允许 subprocess（用于 git provenance）。"""
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_has_datetime_import_batch18():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_has_pathlib_import_batch18():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_import_batch18():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_evaluator_version_import_batch18():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_has_get_git_provenance_function_batch18():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src


def test_module_source_has_get_dependency_versions_function_batch18():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions(" in src


def test_module_source_has_build_provenance_function_batch18():
    src = inspect.getsource(rmod)
    assert "def build_provenance(" in src


def test_module_source_has_build_devset_section_function_batch18():
    src = inspect.getsource(rmod)
    assert "def build_devset_section(" in src


def test_module_source_has_aggregate_summary_function_batch18():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary(" in src


def test_module_source_has_all_dunder_batch18():
    src = inspect.getsource(rmod)
    assert "__all__" in src


def test_module_source_no_main_block_batch18():
    src = inspect.getsource(rmod)
    assert "__main__" not in src


# ---------- signatures 第二十八批 ----------


def test_signature_get_git_provenance_batch18():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root"]


def test_signature_get_dependency_versions_batch18():
    sig = inspect.signature(get_dependency_versions)
    params = list(sig.parameters.keys())
    assert params == []


def test_signature_build_provenance_batch18():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_devset_section_batch18():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.keys())
    assert params == ["manifest"]


def test_signature_aggregate_summary_batch18():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.keys())
    assert params == ["per_doc_results"]


# ---------- module 合理性第二十八批 ----------


def test_module_has_all_attribute_batch18():
    assert hasattr(rmod, "__all__")
    assert isinstance(rmod.__all__, list)


def test_module_all_count_5_batch18():
    assert len(rmod.__all__) == 5


def test_module_all_contents_batch18():
    assert set(rmod.__all__) == {
        "build_provenance", "build_devset_section",
        "aggregate_summary", "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_build_provenance_callable_batch18():
    assert callable(build_provenance)


def test_module_build_devset_callable_batch18():
    assert callable(build_devset_section)


def test_module_aggregate_summary_callable_batch18():
    assert callable(aggregate_summary)


def test_module_get_git_provenance_callable_batch18():
    assert callable(get_git_provenance)


def test_module_get_dependency_versions_callable_batch18():
    assert callable(get_dependency_versions)


def test_module_does_not_import_unsafe_modules_batch18():
    src = inspect.getsource(rmod)
    for unsafe in ["import pickle", "import marshal", "import shelve"]:
        assert unsafe not in src


def test_module_does_not_import_app_pipeline_batch18():
    """report.py 不应反向依赖 app.pipeline。"""
    src = inspect.getsource(rmod)
    assert "from app.pipeline" not in src


def test_module_does_not_import_evaluation_runner_batch18():
    src = inspect.getsource(rmod)
    assert "from evaluation.runner" not in src


# ---------- 端到端集成第二十八批 ----------


def test_e2e_build_provenance_full_batch18(tmp_path):
    """完整 build_provenance → dict 9 keys。"""
    r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert isinstance(r, dict)
    assert len(r) == 9
    assert r["parser_name"] == "fallback"
    assert r["max_chars"] == 800
    assert r["parser_version"] == "1.0.0"
    assert r["evaluator_version"] == EVALUATOR_VERSION
    assert r["report_version"] == REPORT_VERSION


def test_e2e_build_devset_section_from_manifest_batch18():
    """manifest → devset section。"""
    m = _mk_manifest()
    r = build_devset_section(m)
    assert r["status"] == "incomplete"
    assert r["file_count"] == 5
    assert r["content_group_count"] == 2
    assert r["pdf_count"] == 3
    assert r["docx_count"] == 2
    assert r["categories_covered"] == ["cat1", "cat2"]


def test_e2e_aggregate_summary_full_flow_batch18():
    """完整 aggregate_summary 流程：3 docs 不同 metric。"""
    per_doc = [
        {
            "metrics": {
                "pipeline_success": {"value": True},
                "schema_valid": {"value": 1.0},
                "element_count_total": {"value": 5},
                "silent_drop_count": {"value": 0},
            }
        },
        {
            "metrics": {
                "pipeline_success": {"value": False},
                "schema_valid": {"value": 0.0},
                "element_count_total": {"value": 10},
                "silent_drop_count": {"value": 2},
            }
        },
    ]
    r = aggregate_summary(per_doc)
    assert r["success_rates"]["pipeline_success"]["success_count"] == 1
    assert r["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert r["counts"]["element_count_total"]["sum"] == 15
    assert r["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5
    assert r["silent_drop_total"] == 2


def test_e2e_aggregate_summary_does_not_mutate_input_batch18():
    per_doc = [{"metrics": {"pipeline_success": {"value": True}}}]
    original = [{"metrics": {"pipeline_success": {"value": True}}}]
    aggregate_summary(per_doc)
    assert per_doc == original


def test_e2e_get_git_provenance_real_call_batch18():
    """real call in this worktree (HEAD on claude/autonomous-track)。"""
    import os
    cwd = Path(__file__).resolve().parent.parent
    r = get_git_provenance(cwd)
    assert "git_commit" in r
    assert "git_dirty" in r
    # 在 git repo 里 → commit 应是 str
    if (cwd / ".git").exists():
        assert isinstance(r["git_commit"], str)


def test_e2e_build_provenance_dependencies_real_batch18(tmp_path):
    """get_dependency_versions 在 build_provenance 内被调用。"""
    r = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert "dependencies" in r
    deps = r["dependencies"]
    assert "pdfplumber" in deps
    assert "python-docx" in deps
    assert "pypdfium2" in deps


def test_e2e_pipeline_combined_batch18(tmp_path):
    """build_provenance + build_devset_section + aggregate_summary 组合。"""
    provenance = build_provenance(tmp_path, "fallback", 800, "1.0")
    devset = build_devset_section(_mk_manifest())
    summary = aggregate_summary([
        {"metrics": {"pipeline_success": {"value": True}}},
    ])
    assert len(provenance) == 9
    assert len(devset) == 6
    assert "success_rates" in summary


def test_e2e_aggregate_summary_with_extra_metrics_batch18():
    """per_doc 含未识别 metric 也不抛异常。"""
    per_doc = [
        {"metrics": {
            "pipeline_success": {"value": True},
            "unknown_metric": {"value": 99},
        }}
    ]
    r = aggregate_summary(per_doc)  # should not raise
    assert "success_rates" in r
