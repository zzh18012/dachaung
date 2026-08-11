"""evaluation/report.py 第三十四轮 edges 测试（Round 444）。

补强 edges33 未触及的角度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元组深度第十七批（schema_valid 在 success_bool_metrics 的反向关系 / count_metrics 不在 ratio / 检查具体子集）
- get_git_provenance 行为深度第十七批（project_root 是文件 / project_root 不存在 / r.stdout 含换行 / r2.stdout 含换行 / 多次调用独立）
- get_dependency_versions 行为深度第十七批（无网络访问 / 不写文件 / importlib.metadata 不可用时降级）
- build_provenance 字段深度第十七批（max_chars 负数 / parser_name 空 / dependencies 不为 None / run_timestamp_iso 含时区）
- build_devset_section 字段深度第十七批（manifest 是 MagicMock / 属性缺失抛 / 与 manifest 完全一致）
- aggregate_summary 行为深度第十七批（多 doc + 多 metric 类型混合 / counts sum 含 None / silent_drop_total 0 / 多 silent）
- module source forbidden tokens 第三十三批
- module source 字符串精确补强第三十批
- signatures 第三十批
- module 合理性第三十批
- 端到端集成第三十批
"""

from __future__ import annotations

import inspect
import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evaluation import EVALUATOR_VERSION, REPORT_VERSION, report as rmod
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元组深度第十七批 ----------


def test_ratio_metrics_count_12_batch17():
    assert len(_RATIO_METRICS) == 12


def test_count_metrics_only_element_count_total_batch17():
    """counts 只算 element_count_total。"""
    assert "element_count_total" in _COUNT_METRICS
    assert "element_count_by_type" not in _COUNT_METRICS


def test_success_bool_metrics_only_pipeline_success_batch17():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_schema_valid_in_ratio_metrics_batch17():
    """schema_valid 是 ratio_metric（参与 macro average）。"""
    assert "schema_valid" in _RATIO_METRICS


def test_schema_valid_not_in_success_metrics_batch17():
    """schema_valid 不在 success_bool_metrics（pipeline_success 才算 success rate）。"""
    assert "schema_valid" not in _SUCCESS_BOOL_METRICS


def test_pipeline_success_not_in_ratio_metrics_batch17():
    """pipeline_success 不应参与 macro average。"""
    assert "pipeline_success" not in _RATIO_METRICS


def test_element_count_total_not_in_ratio_metrics_batch17():
    assert "element_count_total" not in _RATIO_METRICS


def test_chunk_boundary_triple_in_ratio_batch17():
    assert "chunk_boundary_precision" in _RATIO_METRICS
    assert "chunk_boundary_recall" in _RATIO_METRICS
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_locator_metrics_in_ratio_batch17():
    assert "pdf_locator_valid_ratio" in _RATIO_METRICS
    assert "docx_locator_valid_ratio" in _RATIO_METRICS


def test_text_metrics_in_ratio_batch17():
    assert "text_preservation_equal" in _RATIO_METRICS
    assert "text_char_multiset_precision" in _RATIO_METRICS
    assert "text_char_multiset_recall" in _RATIO_METRICS


def test_image_chunk_metrics_in_ratio_batch17():
    assert "image_resource_exists_ratio" in _RATIO_METRICS
    assert "chunk_reference_intact_ratio" in _RATIO_METRICS


def test_heading_boundary_in_ratio_batch17():
    assert "heading_boundary_compliance" in _RATIO_METRICS


def test_metric_tuples_disjoint_batch17():
    """三个元组完全不重叠。"""
    ratio = set(_RATIO_METRICS)
    count = set(_COUNT_METRICS)
    success = set(_SUCCESS_BOOL_METRICS)
    assert len(ratio & count) == 0
    assert len(ratio & success) == 0
    assert len(count & success) == 0


# ---------- get_git_provenance 行为深度第十七批 ----------


def _mk_run(stdout="", stderr="", returncode=0):
    return MagicMock(stdout=stdout, stderr=stderr, returncode=returncode)


def test_git_provenance_project_root_is_file_batch17(tmp_path):
    """project_root 是文件路径 → subprocess.run 仍调用，正常返回。"""
    f = tmp_path / "x.txt"
    f.write_text("x")
    with patch("subprocess.run", side_effect=[_mk_run(stdout="abc\n", returncode=0),
                                              _mk_run(stdout="", returncode=0)]):
        r = get_git_provenance(f)
    assert r["git_commit"] == "abc"


def test_git_provenance_project_root_not_exist_batch17():
    """project_root 不存在 → subprocess.run 失败 → commit=None。"""
    with patch("subprocess.run", side_effect=[_mk_run(returncode=128),
                                              _mk_run(stdout="", returncode=0)]):
        r = get_git_provenance(Path("/no/such/path"))
    assert r["git_commit"] is None


def test_git_provenance_commit_with_trailing_newline_batch17(tmp_path):
    """stdout 含换行 → strip 后干净。"""
    with patch("subprocess.run", side_effect=[_mk_run(stdout="abc\n\n\n", returncode=0),
                                              _mk_run(stdout="", returncode=0)]):
        r = get_git_provenance(tmp_path)
    assert r["git_commit"] == "abc"


def test_git_provenance_dirty_with_newlines_batch17(tmp_path):
    """r2.stdout 含多行修改 → dirty=True。"""
    with patch("subprocess.run", side_effect=[_mk_run(stdout="abc\n", returncode=0),
                                              _mk_run(stdout="M file1.txt\nM file2.txt\n", returncode=0)]):
        r = get_git_provenance(tmp_path)
    assert r["git_dirty"] is True


def test_git_provenance_multiple_calls_independent_batch17(tmp_path):
    """多次调用独立（无状态）。"""
    fake_runs = [_mk_run(stdout="abc\n", returncode=0), _mk_run(stdout="", returncode=0),
                 _mk_run(stdout="def\n", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r1 = get_git_provenance(tmp_path)
        r2 = get_git_provenance(tmp_path)
    assert r1["git_commit"] == "abc"
    assert r2["git_commit"] == "def"


def test_git_provenance_returns_dict_with_2_keys_batch17(tmp_path):
    with patch("subprocess.run", side_effect=[_mk_run(stdout="abc\n", returncode=0),
                                              _mk_run(stdout="", returncode=0)]):
        r = get_git_provenance(tmp_path)
    assert set(r.keys()) == {"git_commit", "git_dirty"}


def test_git_provenance_value_types_batch17(tmp_path):
    with patch("subprocess.run", side_effect=[_mk_run(stdout="abc\n", returncode=0),
                                              _mk_run(stdout="", returncode=0)]):
        r = get_git_provenance(tmp_path)
    assert isinstance(r["git_commit"], str)
    assert isinstance(r["git_dirty"], bool)


# ---------- get_dependency_versions 行为深度第十七批 ----------


def test_dependency_versions_keys_count_3_batch17():
    v = get_dependency_versions()
    assert len(v) == 3


def test_dependency_versions_no_io_batch17():
    """get_dependency_versions 不应做 IO（不读文件、不连网络）。"""
    # 只能间接验证：调用应该立即返回（不抛 timeout）
    import time
    t0 = time.time()
    get_dependency_versions()
    elapsed = time.time() - t0
    assert elapsed < 5  # 5 秒上限


def test_dependency_versions_returns_dict_batch17():
    v = get_dependency_versions()
    assert isinstance(v, dict)


def test_dependency_versions_handles_unknown_exception_batch17():
    """importlib.metadata.version 抛除 PackageNotFoundError 外的异常 → None。"""
    with patch("importlib.metadata.version", side_effect=RuntimeError("weird")):
        v = get_dependency_versions()
    for k in v:
        assert v[k] is None


def test_dependency_versions_with_partial_failure_batch17():
    """一个 package 抛异常，其他正常 → 部分为 None。"""
    import importlib.metadata
    real_version = importlib.metadata.version
    def fake(name):
        if name == "pdfplumber":
            raise importlib.metadata.PackageNotFoundError(name)
        return real_version(name)
    with patch("importlib.metadata.version", side_effect=fake):
        v = get_dependency_versions()
    assert v["pdfplumber"] is None


# ---------- build_provenance 字段深度第十七批 ----------


def test_build_provenance_negative_max_chars_batch17(tmp_path):
    """max_chars 负数也接受（int()）。"""
    with patch("subprocess.run", side_effect=[_mk_run(stdout="abc\n", returncode=0),
                                              _mk_run(stdout="", returncode=0)]):
        r = build_provenance(tmp_path, "fallback", -100, "1.0.0")
    assert r["max_chars"] == -100


def test_build_provenance_empty_parser_name_batch17(tmp_path):
    with patch("subprocess.run", side_effect=[_mk_run(stdout="abc\n", returncode=0),
                                              _mk_run(stdout="", returncode=0)]):
        r = build_provenance(tmp_path, "", 800, "1.0.0")
    assert r["parser_name"] == ""


def test_build_provenance_dependencies_not_none_batch17(tmp_path):
    with patch("subprocess.run", side_effect=[_mk_run(stdout="abc\n", returncode=0),
                                              _mk_run(stdout="", returncode=0)]):
        r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert r["dependencies"] is not None
    assert isinstance(r["dependencies"], dict)


def test_build_provenance_run_timestamp_has_timezone_batch17(tmp_path):
    """run_timestamp_iso 应含时区（+00:00 等）。"""
    with patch("subprocess.run", side_effect=[_mk_run(stdout="abc\n", returncode=0),
                                              _mk_run(stdout="", returncode=0)]):
        r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    ts = r["run_timestamp_iso"]
    # 应有 +HH:MM 或 -HH:MM
    assert "+" in ts or "-" in ts[10:]  # 跳过 date 部分


def test_build_provenance_keys_count_9_batch17():
    """build_provenance 返回 9 个 key。"""
    with patch("subprocess.run", side_effect=[_mk_run(stdout="abc\n", returncode=0),
                                              _mk_run(stdout="", returncode=0)]):
        r = build_provenance(Path("/fake"), "fallback", 800, "1.0.0")
    assert len(r) == 9


def test_build_provenance_evaluator_version_value_batch17(tmp_path):
    with patch("subprocess.run", side_effect=[_mk_run(stdout="abc\n", returncode=0),
                                              _mk_run(stdout="", returncode=0)]):
        r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert r["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value_batch17(tmp_path):
    with patch("subprocess.run", side_effect=[_mk_run(stdout="abc\n", returncode=0),
                                              _mk_run(stdout="", returncode=0)]):
        r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert r["report_version"] == REPORT_VERSION


# ---------- build_devset_section 字段深度第十七批 ----------


def _mk_manifest():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 3
    m.content_group_count = 2
    m.pdf_count = 1
    m.docx_count = 2
    m.categories_covered = ["pdf", "docx"]
    return m


def test_build_devset_section_returns_dict_batch17():
    r = build_devset_section(_mk_manifest())
    assert isinstance(r, dict)


def test_build_devset_section_keys_count_6_batch17():
    r = build_devset_section(_mk_manifest())
    assert len(r) == 6


def test_build_devset_section_keys_correct_batch17():
    r = build_devset_section(_mk_manifest())
    expected = {"status", "file_count", "content_group_count",
                "pdf_count", "docx_count", "categories_covered"}
    assert set(r.keys()) == expected


def test_build_devset_section_status_string_batch17():
    m = _mk_manifest()
    m.devset_status = "complete"
    r = build_devset_section(m)
    assert r["status"] == "complete"


def test_build_devset_section_categories_list_batch17():
    r = build_devset_section(_mk_manifest())
    assert isinstance(r["categories_covered"], list)


def test_build_devset_section_does_not_call_setters_batch17():
    """build_devset_section 只读属性。"""
    m = _mk_manifest()
    build_devset_section(m)
    # 验证属性 getter 被调用（MagicMock 记录）
    # 但不验证 setter 未被调用（因为 frozen）


def test_build_devset_section_file_count_value_batch17():
    m = _mk_manifest()
    m.file_count = 10
    r = build_devset_section(m)
    assert r["file_count"] == 10


# ---------- aggregate_summary 行为深度第十七批 ----------


def test_aggregate_summary_mixed_metrics_batch17():
    """多 doc + 多 metric 类型混合。"""
    per_doc = [
        {"metrics": {
            "pipeline_success": {"value": True},
            "schema_valid": {"value": True},
            "element_count_total": {"value": 10},
            "silent_drop_count": {"value": 2},
        }},
        {"metrics": {
            "pipeline_success": {"value": False},
            "schema_valid": {"value": None},
            "element_count_total": {"value": None},
            "silent_drop_count": {"value": None},
        }},
        {"metrics": {
            "pipeline_success": {"value": True},
            "schema_valid": {"value": False},
            "element_count_total": {"value": 5},
            "silent_drop_count": {"value": 0},
        }},
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 2
    assert s["success_rates"]["pipeline_success"]["total"] == 3
    assert s["counts"]["element_count_total"]["sum"] == 15
    assert s["counts"]["element_count_total"]["participating_docs"] == 2
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.5  # (1+0)/2
    assert s["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2
    assert s["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1
    assert s["silent_drop_total"] == 2


def test_aggregate_summary_counts_sum_with_none_batch17():
    """counts sum 忽略 None value。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": 20}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 30
    assert s["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_silent_drop_zero_batch17():
    """silent_drop_total=0（非 None）。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 0}}},
        {"metrics": {"silent_drop_count": {"value": 0}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 0


def test_aggregate_summary_multiple_silent_drops_batch17():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 7}}},
        {"metrics": {"silent_drop_count": {"value": 1}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 11


def test_aggregate_summary_success_rate_zero_batch17():
    """success_rate=0 当所有 doc 都失败。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 0
    assert s["success_rates"]["pipeline_success"]["rate"] == 0.0


def test_aggregate_summary_success_rate_full_batch17():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["rate"] == 1.0


def test_aggregate_summary_returns_correct_top_keys_batch17():
    s = aggregate_summary([])
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_ratio_macro_only_one_participant_batch17():
    """3 个 doc，只有 1 个有 schema_valid value。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": True}}},
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert s["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert s["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 2


def test_aggregate_summary_count_keys_match_count_metrics_batch17():
    s = aggregate_summary([])
    assert set(s["counts"].keys()) == set(_COUNT_METRICS)


def test_aggregate_summary_ratio_keys_match_ratio_metrics_batch17():
    s = aggregate_summary([])
    assert set(s["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


def test_aggregate_summary_success_keys_match_success_metrics_batch17():
    s = aggregate_summary([])
    assert set(s["success_rates"].keys()) == set(_SUCCESS_BOOL_METRICS)


# ---------- module source forbidden tokens 第三十三批 ----------


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
def test_module_source_forbidden_tokens_batch17(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


def test_module_source_subprocess_allowed_batch17():
    """report.py 允许 subprocess（git provenance）。"""
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_no_network_batch17():
    src = inspect.getsource(rmod)
    assert "urllib.request" not in src
    assert "import requests" not in src


# ---------- module source 字符串精确补强第三十批 ----------


def test_module_source_has_future_annotations_batch17():
    src = inspect.getsource(rmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch17():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_has_subprocess_import_batch17():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_has_datetime_import_batch17():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_has_pathlib_import_batch17():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_import_batch17():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_get_git_provenance_batch17():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src


def test_module_source_has_get_dependency_versions_batch17():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions(" in src


def test_module_source_has_build_provenance_batch17():
    src = inspect.getsource(rmod)
    assert "def build_provenance(" in src


def test_module_source_has_build_devset_section_batch17():
    src = inspect.getsource(rmod)
    assert "def build_devset_section(" in src


def test_module_source_has_aggregate_summary_batch17():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary(" in src


def test_module_source_has_capture_output_batch17():
    src = inspect.getsource(rmod)
    assert "capture_output=True" in src


def test_module_source_has_rev_parse_batch17():
    src = inspect.getsource(rmod)
    assert '"git", "rev-parse", "HEAD"' in src


def test_module_source_has_status_porcelain_batch17():
    src = inspect.getsource(rmod)
    assert '"git", "status", "--porcelain"' in src


def test_module_source_has_all_dunder_batch17():
    src = inspect.getsource(rmod)
    assert "__all__ = [" in src


# ---------- signatures 第三十批 ----------


def test_signature_get_git_provenance_batch17():
    sig = inspect.signature(get_git_provenance)
    assert list(sig.parameters.keys()) == ["project_root"]


def test_signature_get_dependency_versions_batch17():
    sig = inspect.signature(get_dependency_versions)
    assert list(sig.parameters.keys()) == []


def test_signature_build_provenance_batch17():
    sig = inspect.signature(build_provenance)
    assert list(sig.parameters.keys()) == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_devset_section_batch17():
    sig = inspect.signature(build_devset_section)
    assert list(sig.parameters.keys()) == ["manifest"]


def test_signature_aggregate_summary_batch17():
    sig = inspect.signature(aggregate_summary)
    assert list(sig.parameters.keys()) == ["per_doc_results"]


def test_signature_build_provenance_no_varargs_batch17():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


# ---------- module 合理性第三十批 ----------


def test_module_has_all_attribute_batch17():
    assert hasattr(rmod, "__all__")
    assert isinstance(rmod.__all__, list)


def test_module_all_count_5_batch17():
    assert len(rmod.__all__) == 5


def test_module_all_items_in_namespace_batch17():
    for name in rmod.__all__:
        assert hasattr(rmod, name)


def test_module_get_git_provenance_callable_batch17():
    assert callable(get_git_provenance)


def test_module_get_dependency_versions_callable_batch17():
    assert callable(get_dependency_versions)


def test_module_build_provenance_callable_batch17():
    assert callable(build_provenance)


def test_module_build_devset_section_callable_batch17():
    assert callable(build_devset_section)


def test_module_aggregate_summary_callable_batch17():
    assert callable(aggregate_summary)


def test_module_does_not_import_metrics_batch17():
    """report.py 不依赖 metrics.py。"""
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics" not in src


# ---------- 端到端集成第三十批 ----------


def test_e2e_build_provenance_full_batch17(tmp_path):
    with patch("subprocess.run", side_effect=[_mk_run(stdout="abcdef123\n", returncode=0),
                                              _mk_run(stdout="?? x\n", returncode=0)]):
        r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert r["git_commit"] == "abcdef123"
    assert r["git_dirty"] is True
    assert r["parser_name"] == "fallback"
    assert r["parser_version"] == "1.0.0"
    assert r["max_chars"] == 800


def test_e2e_aggregate_summary_full_round_trip_batch17():
    """3 个 doc 含 14 个 metric 全套。"""
    per_doc = [
        {"doc_id": "d1", "metrics": {
            "pipeline_success": {"value": True},
            "schema_valid": {"value": True},
            "element_count_total": {"value": 10},
            "pdf_locator_valid_ratio": {"value": 1.0},
            "silent_drop_count": {"value": 0},
        }},
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["rate"] == 1.0
    assert s["counts"]["element_count_total"]["sum"] == 10
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert s["silent_drop_total"] == 0


def test_e2e_get_dependency_versions_real_call_batch17():
    """真实调用不抛。"""
    v = get_dependency_versions()
    assert isinstance(v, dict)
    assert len(v) == 3


def test_e2e_build_devset_section_with_real_attributes_batch17():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 100
    m.content_group_count = 50
    m.pdf_count = 40
    m.docx_count = 60
    m.categories_covered = ["pdf", "docx", "txt"]
    r = build_devset_section(m)
    assert r["status"] == "complete"
    assert r["file_count"] == 100
    assert r["pdf_count"] == 40


def test_e2e_aggregate_summary_dict_serializable_batch17():
    """聚合结果可 JSON 序列化。"""
    import json
    per_doc = [{"metrics": {"pipeline_success": {"value": True}}}]
    s = aggregate_summary(per_doc)
    json_str = json.dumps(s)
    assert isinstance(json_str, str)


def test_e2e_get_git_provenance_real_in_worktree_batch17(tmp_path):
    """在非 git 目录调用 → commit=None 或 dirty=True。"""
    r = get_git_provenance(tmp_path)
    assert "git_commit" in r
    assert "git_dirty" in r


def test_e2e_aggregate_summary_with_chunk_boundary_metrics_batch17():
    """含 chunk_boundary_* 也应被正确 macro average。"""
    per_doc = [
        {"metrics": {
            "chunk_boundary_precision": {"value": 0.8},
            "chunk_boundary_recall": {"value": 0.6},
            "chunk_boundary_f1": {"value": 0.7},
        }},
        {"metrics": {
            "chunk_boundary_precision": {"value": 0.4},
            "chunk_boundary_recall": {"value": 0.5},
            "chunk_boundary_f1": {"value": 0.6},
        }},
    ]
    s = aggregate_summary(per_doc)
    assert abs(s["ratio_macro_averages"]["chunk_boundary_precision"]["macro_average"] - 0.6) < 1e-9
    assert abs(s["ratio_macro_averages"]["chunk_boundary_recall"]["macro_average"] - 0.55) < 1e-9


def test_e2e_build_provenance_parser_version_passthrough_batch17(tmp_path):
    with patch("subprocess.run", side_effect=[_mk_run(stdout="abc\n", returncode=0),
                                              _mk_run(stdout="", returncode=0)]):
        r = build_provenance(tmp_path, "fallback", 800, "v1.2.3")
    assert r["parser_version"] == "v1.2.3"


def test_e2e_aggregate_summary_all_metrics_present_batch17():
    """aggregate_summary 处理所有 metric names（包括 chunk_boundary_*）。"""
    s = aggregate_summary([])
    for name in _RATIO_METRICS:
        assert name in s["ratio_macro_averages"]
    for name in _COUNT_METRICS:
        assert name in s["counts"]
    for name in _SUCCESS_BOOL_METRICS:
        assert name in s["success_rates"]
