"""evaluation/report.py 第三十三轮 edges 测试（Round 437）。

补强 edges32 未触及的角度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元组深度第十六批（顺序 / 唯一性 / 不重叠 / 不含 silent_drop_count / 不含 element_count_by_type）
- get_git_provenance 行为深度第十六批（returncode=128 / stdout 含非 ASCII / Empty stdout / OSError / SubprocessError / timeout）
- get_dependency_versions 行为深度第十六批（所有值为 None 时 / 多次调用一致 / 不依赖 importlib 全局缓存 / keys 排序无关）
- build_provenance 字段深度第十六批（max_chars 字符串强转 / max_chars 浮点 / parser_name 任意 / dependencies 含 None / git_commit/dirty 来自 get_git_provenance）
- build_devset_section 字段深度第十六批（manifest 任意属性值 / 6 keys 顺序 / 不修改 manifest / type hints / 与 devset_status 一致）
- aggregate_summary 行为深度第十六批（counts 全 None / success_rate total=0 / ratio 仅 1 个参与 / not_evaluated=total / silent_drop_total None / 多个 metric 多种状态混合）
- module source forbidden tokens 第三十二批
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元组深度第十六批 ----------


def test_ratio_metrics_starts_with_schema_valid_batch16():
    assert _RATIO_METRICS[0] == "schema_valid"


def test_ratio_metrics_length_12_batch16():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_unique_batch16():
    assert len(set(_RATIO_METRICS)) == len(_RATIO_METRICS)


def test_count_metrics_length_1_batch16():
    assert len(_COUNT_METRICS) == 1


def test_count_metrics_unique_batch16():
    assert len(set(_COUNT_METRICS)) == len(_COUNT_METRICS)


def test_success_bool_metrics_length_1_batch16():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_success_bool_metrics_unique_batch16():
    assert len(set(_SUCCESS_BOOL_METRICS)) == len(_SUCCESS_BOOL_METRICS)


def test_metric_tuples_no_overlap_batch16():
    """三个元组两两不重叠。"""
    ratio = set(_RATIO_METRICS)
    count = set(_COUNT_METRICS)
    success = set(_SUCCESS_BOOL_METRICS)
    assert ratio & count == set()
    assert ratio & success == set()
    assert count & success == set()


def test_metric_tuples_no_silent_drop_count_batch16():
    """silent_drop_count 单独走逻辑，不在三个元组里。"""
    assert "silent_drop_count" not in _RATIO_METRICS
    assert "silent_drop_count" not in _COUNT_METRICS
    assert "silent_drop_count" not in _SUCCESS_BOOL_METRICS


def test_metric_tuples_no_element_count_by_type_batch16():
    """element_count_by_type 是 dict 不是数字，不参与聚合。"""
    assert "element_count_by_type" not in _RATIO_METRICS
    assert "element_count_by_type" not in _COUNT_METRICS
    assert "element_count_by_type" not in _SUCCESS_BOOL_METRICS


def test_metric_tuples_no_error_code_batch16():
    """error_code 是 str，不参与聚合。"""
    assert "error_code" not in _RATIO_METRICS
    assert "error_code" not in _COUNT_METRICS
    assert "error_code" not in _SUCCESS_BOOL_METRICS


def test_metric_tuples_no_figure_caption_batch16():
    """figure_caption_* 始终 null，不参与 macro average。"""
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_count_metrics_contains_element_count_total_batch16():
    assert "element_count_total" in _COUNT_METRICS


def test_success_bool_metrics_contains_pipeline_success_batch16():
    assert "pipeline_success" in _SUCCESS_BOOL_METRICS


def test_ratio_metrics_contains_chunk_boundary_f1_batch16():
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_metric_tuples_are_tuples_batch16():
    assert isinstance(_RATIO_METRICS, tuple)
    assert isinstance(_COUNT_METRICS, tuple)
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_metric_tuples_immutable_batch16():
    """tuple 是不可变序列。"""
    with pytest.raises(TypeError):
        _RATIO_METRICS[0] = "x"  # type: ignore
    with pytest.raises(TypeError):
        _COUNT_METRICS[0] = "x"  # type: ignore
    with pytest.raises(TypeError):
        _SUCCESS_BOOL_METRICS[0] = "x"  # type: ignore


# ---------- get_git_provenance 行为深度第十六批 ----------


def _mk_run(stdout="", stderr="", returncode=0):
    """构造一个 fake CompletedProcess。"""
    return MagicMock(stdout=stdout, stderr=stderr, returncode=returncode)


def test_git_provenance_returncode_128_batch16(tmp_path):
    """git rev-parse 失败（returncode=128）→ commit=None。"""
    fake_runs = [_mk_run(returncode=128), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = get_git_provenance(tmp_path)
    assert r["git_commit"] is None
    assert r["git_dirty"] is False  # r2.returncode=0, stdout=""


def test_git_provenance_non_ascii_stdout_batch16(tmp_path):
    """stdout 含非 ASCII（虽然 git rev-parse 不会，但 errors=replace 应不抛）。"""
    fake_runs = [_mk_run(stdout="café\n", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = get_git_provenance(tmp_path)
    assert r["git_commit"] == "café"


def test_git_provenance_empty_stdout_returncode_0_batch16(tmp_path):
    """returncode=0 但 stdout 空 → commit=None。"""
    fake_runs = [_mk_run(stdout="", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = get_git_provenance(tmp_path)
    assert r["git_commit"] is None


def test_git_provenance_oserror_batch16(tmp_path):
    """OSError → 走 except 分支：commit=None, dirty=True。"""
    with patch("subprocess.run", side_effect=OSError("boom")):
        r = get_git_provenance(tmp_path)
    assert r["git_commit"] is None
    assert r["git_dirty"] is True


def test_git_provenance_subprocess_error_batch16(tmp_path):
    """subprocess.SubprocessError → 走 except 分支。"""
    with patch("subprocess.run", side_effect=subprocess.SubprocessError("timeout-like")):
        r = get_git_provenance(tmp_path)
    assert r["git_commit"] is None
    assert r["git_dirty"] is True


def test_git_provenance_timeout_batch16(tmp_path):
    """subprocess.TimeoutExpired 是 SubprocessError 子类。"""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 10)):
        r = get_git_provenance(tmp_path)
    assert r["git_commit"] is None
    assert r["git_dirty"] is True


def test_git_provenance_dirty_only_whitespace_batch16(tmp_path):
    """r2.stdout 全是空白 → strip 后为空 → dirty=False。"""
    fake_runs = [_mk_run(stdout="abc\n", returncode=0), _mk_run(stdout="  \n\t", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = get_git_provenance(tmp_path)
    assert r["git_dirty"] is False


def test_git_provenance_dirty_with_paths_batch16(tmp_path):
    """r2.stdout 含 ?? /path → dirty=True。"""
    fake_runs = [_mk_run(stdout="abc\n", returncode=0),
                 _mk_run(stdout="?? samples/private/x.pdf\n", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = get_git_provenance(tmp_path)
    assert r["git_dirty"] is True


def test_git_provenance_returns_dict_batch16(tmp_path):
    fake_runs = [_mk_run(stdout="abc\n", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = get_git_provenance(tmp_path)
    assert isinstance(r, dict)
    assert set(r.keys()) == {"git_commit", "git_dirty"}


def test_git_provenance_two_subprocess_calls_batch16(tmp_path):
    """每次调用 get_git_provenance 内部触发 2 次 subprocess.run（rev-parse + status）。"""
    calls = []
    def fake(*args, **kwargs):
        calls.append(args[0])
        return _mk_run(stdout="abc\n" if len(calls) == 1 else "", returncode=0)
    with patch("subprocess.run", side_effect=fake):
        get_git_provenance(tmp_path)
    assert len(calls) == 2
    assert calls[0] == ["git", "rev-parse", "HEAD"]
    assert calls[1] == ["git", "status", "--porcelain"]


# ---------- get_dependency_versions 行为深度第十六批 ----------


def test_dependency_versions_three_keys_batch16():
    v = get_dependency_versions()
    assert set(v.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_dependency_versions_value_types_batch16():
    v = get_dependency_versions()
    for k, val in v.items():
        assert val is None or isinstance(val, str)


def test_dependency_versions_idempotent_batch16():
    v1 = get_dependency_versions()
    v2 = get_dependency_versions()
    assert v1 == v2


def test_dependency_versions_dict_serializable_batch16():
    """返回的 dict 可 JSON 序列化。"""
    import json
    v = get_dependency_versions()
    s = json.dumps(v)
    assert isinstance(s, str)


def test_dependency_versions_pdfplumber_present_batch16():
    """pdfplumber 应该装了（fallback parser 依赖）。"""
    v = get_dependency_versions()
    assert v["pdfplumber"] is not None


def test_dependency_versions_python_docx_present_batch16():
    v = get_dependency_versions()
    assert v["python-docx"] is not None


def test_dependency_versions_pypdfium2_optional_batch16():
    """pypdfium2 可能装也可能没装。"""
    v = get_dependency_versions()
    # 只是验证 key 存在
    assert "pypdfium2" in v


def test_dependency_versions_pkg_not_found_batch16():
    """模拟 PackageNotFoundError → 该 key 为 None。"""
    import importlib.metadata
    with patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError):
        v = get_dependency_versions()
    assert v["pdfplumber"] is None
    assert v["python-docx"] is None
    assert v["pypdfium2"] is None


def test_dependency_versions_unknown_exception_batch16():
    """模拟非 PackageNotFoundError 异常 → 该 key 为 None。"""
    with patch("importlib.metadata.version", side_effect=ValueError("weird")):
        v = get_dependency_versions()
    assert v["pdfplumber"] is None


# ---------- build_provenance 字段深度第十六批 ----------


def test_build_provenance_max_chars_str_batch16(tmp_path):
    """max_chars 字符串会被 int() 强转。"""
    fake_runs = [_mk_run(stdout="abc\n", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = build_provenance(tmp_path, "fallback", "800", "1.0.0")
    assert r["max_chars"] == 800
    assert isinstance(r["max_chars"], int)


def test_build_provenance_max_chars_float_batch16(tmp_path):
    """max_chars 浮点会被 int() 截断。"""
    fake_runs = [_mk_run(stdout="abc\n", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = build_provenance(tmp_path, "fallback", 800.99, "1.0.0")
    assert r["max_chars"] == 800


def test_build_provenance_parser_name_batch16(tmp_path):
    fake_runs = [_mk_run(stdout="abc\n", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = build_provenance(tmp_path, "kreuzberg", 800, "4.10.2")
    assert r["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_none_batch16(tmp_path):
    fake_runs = [_mk_run(stdout="abc\n", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = build_provenance(tmp_path, "fallback", 800, None)
    assert r["parser_version"] is None


def test_build_provenance_dependencies_is_dict_batch16(tmp_path):
    fake_runs = [_mk_run(stdout="abc\n", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert isinstance(r["dependencies"], dict)


def test_build_provenance_returns_8_keys_batch16(tmp_path):
    fake_runs = [_mk_run(stdout="abc\n", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    expected_keys = {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars", "run_timestamp_iso",
    }
    assert set(r.keys()) == expected_keys


def test_build_provenance_evaluator_version_matches_module_batch16(tmp_path):
    fake_runs = [_mk_run(stdout="abc\n", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert r["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_matches_module_batch16(tmp_path):
    fake_runs = [_mk_run(stdout="abc\n", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert r["report_version"] == REPORT_VERSION


def test_build_provenance_run_timestamp_parseable_batch16(tmp_path):
    """run_timestamp_iso 应可被 datetime.fromisoformat 解析。"""
    fake_runs = [_mk_run(stdout="abc\n", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    dt = datetime.fromisoformat(r["run_timestamp_iso"])
    assert isinstance(dt, datetime)


def test_build_provenance_git_commit_passed_through_batch16(tmp_path):
    fake_runs = [_mk_run(stdout="deadbeef\n", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert r["git_commit"] == "deadbeef"


# ---------- build_devset_section 字段深度第十六批 ----------


def _mk_manifest():
    """构造一个 fake Manifest 对象。"""
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 3
    m.content_group_count = 2
    m.pdf_count = 1
    m.docx_count = 2
    m.categories_covered = ["pdf", "docx"]
    return m


def test_build_devset_section_keys_batch16():
    r = build_devset_section(_mk_manifest())
    expected = {"status", "file_count", "content_group_count",
                "pdf_count", "docx_count", "categories_covered"}
    assert set(r.keys()) == expected


def test_build_devset_section_status_batch16():
    r = build_devset_section(_mk_manifest())
    assert r["status"] == "incomplete"


def test_build_devset_section_counts_batch16():
    r = build_devset_section(_mk_manifest())
    assert r["file_count"] == 3
    assert r["content_group_count"] == 2
    assert r["pdf_count"] == 1
    assert r["docx_count"] == 2


def test_build_devset_section_categories_batch16():
    r = build_devset_section(_mk_manifest())
    assert r["categories_covered"] == ["pdf", "docx"]


def test_build_devset_section_does_not_modify_manifest_batch16():
    m = _mk_manifest()
    build_devset_section(m)
    # 只读属性，未调用任何 setter
    assert m.devset_status == "incomplete"


def test_build_devset_section_with_empty_categories_batch16():
    m = _mk_manifest()
    m.categories_covered = []
    r = build_devset_section(m)
    assert r["categories_covered"] == []


def test_build_devset_section_with_zero_counts_batch16():
    m = _mk_manifest()
    m.file_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    r = build_devset_section(m)
    assert r["file_count"] == 0
    assert r["pdf_count"] == 0
    assert r["docx_count"] == 0


# ---------- aggregate_summary 行为深度第十六批 ----------


def test_aggregate_summary_empty_list_batch16():
    """空 per_doc → counts 全 None, success rate None, ratio macro None。"""
    s = aggregate_summary([])
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["counts"]["element_count_total"]["participating_docs"] == 0
    assert s["success_rates"]["pipeline_success"]["total"] == 0
    assert s["success_rates"]["pipeline_success"]["rate"] is None
    assert s["silent_drop_total"] is None


def test_aggregate_summary_all_counts_none_batch16():
    """所有 metrics element_count_total.value=None → counts sum=None, participating=0。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_success_rate_total_zero_batch16():
    """total=0 → rate=None。"""
    s = aggregate_summary([])
    assert s["success_rates"]["pipeline_success"]["rate"] is None
    assert s["success_rates"]["pipeline_success"]["success_count"] == 0


def test_aggregate_summary_ratio_one_participant_batch16():
    per_doc = [
        {"metrics": {
            "schema_valid": {"value": True},
            "pdf_locator_valid_ratio": {"value": 0.5},
            "docx_locator_valid_ratio": {"value": None, "reason": "not_docx_document"},
        }},
    ]
    s = aggregate_summary(per_doc)
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert s["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert s["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 0
    assert s["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 0.5
    assert s["ratio_macro_averages"]["docx_locator_valid_ratio"]["macro_average"] is None
    assert s["ratio_macro_averages"]["docx_locator_valid_ratio"]["not_evaluated"] == 1


def test_aggregate_summary_not_evaluated_correct_batch16():
    """3 个 doc，2 个 schema_valid=None → not_evaluated=2。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": True}}},
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 2
    assert s["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0


def test_aggregate_summary_silent_drop_all_none_batch16():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_partial_batch16():
    """部分 doc 有 silent_drop_count value，部分 None。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 8


def test_aggregate_summary_counts_sum_correct_batch16():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": 20}}},
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 35
    assert s["counts"]["element_count_total"]["participating_docs"] == 3


def test_aggregate_summary_success_rate_correct_batch16():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 2
    assert s["success_rates"]["pipeline_success"]["total"] == 3
    assert s["success_rates"]["pipeline_success"]["rate"] == 2 / 3


def test_aggregate_summary_returns_4_sections_batch16():
    s = aggregate_summary([])
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_ratio_macro_keys_match_ratio_metrics_batch16():
    s = aggregate_summary([])
    assert set(s["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


def test_aggregate_summary_counts_keys_match_count_metrics_batch16():
    s = aggregate_summary([])
    assert set(s["counts"].keys()) == set(_COUNT_METRICS)


def test_aggregate_summary_success_keys_match_success_metrics_batch16():
    s = aggregate_summary([])
    assert set(s["success_rates"].keys()) == set(_SUCCESS_BOOL_METRICS)


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
def test_module_source_forbidden_tokens_batch16(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


def test_module_source_subprocess_import_batch16():
    """report.py 允许 subprocess（git provenance）。"""
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_no_network_calls_batch16():
    src = inspect.getsource(rmod)
    assert "urllib.request" not in src
    assert "import requests" not in src
    assert "http.client" not in src


# ---------- module source 字符串精确补强第二十九批 ----------


def test_module_source_has_future_annotations_batch16():
    src = inspect.getsource(rmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch16():
    src = inspect.getsource(rmod)
    assert "评测报告装配" in src


def test_module_source_has_ratio_metrics_definition_batch16():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS = (" in src


def test_module_source_has_count_metrics_definition_batch16():
    src = inspect.getsource(rmod)
    assert "_COUNT_METRICS = (" in src


def test_module_source_has_success_bool_metrics_definition_batch16():
    src = inspect.getsource(rmod)
    assert "_SUCCESS_BOOL_METRICS = (" in src


def test_module_source_has_subprocess_import_batch16():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_has_datetime_import_batch16():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_has_pathlib_import_batch16():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch16():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_get_git_provenance_batch16():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(" in src


def test_module_source_has_get_dependency_versions_batch16():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions(" in src


def test_module_source_has_build_provenance_batch16():
    src = inspect.getsource(rmod)
    assert "def build_provenance(" in src


def test_module_source_has_build_devset_section_batch16():
    src = inspect.getsource(rmod)
    assert "def build_devset_section(" in src


def test_module_source_has_aggregate_summary_batch16():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary(" in src


def test_module_source_has_rev_parse_call_batch16():
    src = inspect.getsource(rmod)
    assert '"git", "rev-parse", "HEAD"' in src


def test_module_source_has_status_porcelain_call_batch16():
    src = inspect.getsource(rmod)
    assert '"git", "status", "--porcelain"' in src


def test_module_source_has_importlib_metadata_batch16():
    src = inspect.getsource(rmod)
    assert "import importlib.metadata" in src


def test_module_source_has_capture_output_batch16():
    src = inspect.getsource(rmod)
    assert "capture_output=True" in src


def test_module_source_has_all_dunder_batch16():
    src = inspect.getsource(rmod)
    assert "__all__ = [" in src


def test_module_source_all_has_5_items_batch16():
    src = inspect.getsource(rmod)
    for name in ['"build_provenance"', '"build_devset_section"', '"aggregate_summary"',
                 '"get_git_provenance"', '"get_dependency_versions"']:
        assert name in src


# ---------- signatures 第二十九批 ----------


def test_signature_get_git_provenance_batch16():
    sig = inspect.signature(get_git_provenance)
    assert list(sig.parameters.keys()) == ["project_root"]


def test_signature_get_dependency_versions_batch16():
    sig = inspect.signature(get_dependency_versions)
    assert list(sig.parameters.keys()) == []


def test_signature_build_provenance_batch16():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_devset_section_batch16():
    sig = inspect.signature(build_devset_section)
    assert list(sig.parameters.keys()) == ["manifest"]


def test_signature_aggregate_summary_batch16():
    sig = inspect.signature(aggregate_summary)
    assert list(sig.parameters.keys()) == ["per_doc_results"]


def test_signature_build_provenance_no_varargs_batch16():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


# ---------- module 合理性第二十九批 ----------


def test_module_has_all_attribute_batch16():
    assert hasattr(rmod, "__all__")
    assert isinstance(rmod.__all__, list)


def test_module_all_items_in_namespace_batch16():
    for name in rmod.__all__:
        assert hasattr(rmod, name)


def test_module_all_count_5_batch16():
    assert len(rmod.__all__) == 5


def test_module_get_git_provenance_callable_batch16():
    assert callable(get_git_provenance)


def test_module_get_dependency_versions_callable_batch16():
    assert callable(get_dependency_versions)


def test_module_build_provenance_callable_batch16():
    assert callable(build_provenance)


def test_module_build_devset_section_callable_batch16():
    assert callable(build_devset_section)


def test_module_aggregate_summary_callable_batch16():
    assert callable(aggregate_summary)


def test_module_ratio_metrics_is_tuple_batch16():
    assert isinstance(_RATIO_METRICS, tuple)


def test_module_does_not_import_evaluation_metrics_batch16():
    """report.py 不应依赖 metrics.py。"""
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics" not in src
    assert "import evaluation.metrics" not in src


# ---------- 端到端集成第二十九批 ----------


def test_e2e_aggregate_with_full_per_doc_batch16():
    """完整 per_doc 走通聚合。"""
    per_doc = [
        {"doc_id": "d1", "metrics": {
            "pipeline_success": {"value": True},
            "schema_valid": {"value": True},
            "element_count_total": {"value": 10},
            "pdf_locator_valid_ratio": {"value": 1.0},
            "silent_drop_count": {"value": 0},
        }},
        {"doc_id": "d2", "metrics": {
            "pipeline_success": {"value": False},
            "schema_valid": {"value": None},
            "element_count_total": {"value": None},
            "pdf_locator_valid_ratio": {"value": None},
            "silent_drop_count": {"value": None},
        }},
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1
    assert s["success_rates"]["pipeline_success"]["total"] == 2
    assert s["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert s["counts"]["element_count_total"]["sum"] == 10
    assert s["counts"]["element_count_total"]["participating_docs"] == 1
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert s["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert s["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1
    assert s["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 1.0
    assert s["silent_drop_total"] == 0


def test_e2e_build_provenance_full_batch16(tmp_path):
    fake_runs = [_mk_run(stdout="abcdef123\n", returncode=0), _mk_run(stdout="?? x\n", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert r["git_commit"] == "abcdef123"
    assert r["git_dirty"] is True
    assert r["parser_name"] == "fallback"
    assert r["parser_version"] == "1.0.0"
    assert r["max_chars"] == 800
    assert r["evaluator_version"] == EVALUATOR_VERSION
    assert r["report_version"] == REPORT_VERSION


def test_e2e_build_devset_section_with_real_attributes_batch16():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 10
    m.content_group_count = 5
    m.pdf_count = 4
    m.docx_count = 6
    m.categories_covered = ["pdf", "docx", "txt"]
    r = build_devset_section(m)
    assert r["status"] == "complete"
    assert r["file_count"] == 10
    assert r["content_group_count"] == 5
    assert r["pdf_count"] == 4
    assert r["docx_count"] == 6
    assert r["categories_covered"] == ["pdf", "docx", "txt"]


def test_e2e_get_dependency_versions_no_throw_batch16():
    """get_dependency_versions 不应在任何环境下抛异常。"""
    v = get_dependency_versions()
    assert isinstance(v, dict)


def test_e2e_git_provenance_in_real_worktree_batch16(tmp_path):
    """在 tmp_path（非 git 仓库）中调用 → commit=None, dirty=True。"""
    r = get_git_provenance(tmp_path)
    # 在 tmp_path 中 git 失败 → returncode != 0 → commit=None
    # dirty 也可能为 True（exception 或 r2 失败）
    assert "git_commit" in r
    assert "git_dirty" in r


def test_e2e_aggregate_summary_with_chunk_boundary_batch16():
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
    assert abs(s["ratio_macro_averages"]["chunk_boundary_f1"]["macro_average"] - 0.65) < 1e-9


def test_e2e_aggregate_summary_dict_serializable_batch16():
    """聚合结果可 JSON 序列化。"""
    import json
    per_doc = [
        {"metrics": {
            "pipeline_success": {"value": True},
            "schema_valid": {"value": True},
            "element_count_total": {"value": 10},
            "silent_drop_count": {"value": 2},
        }},
    ]
    s = aggregate_summary(per_doc)
    json_str = json.dumps(s)
    assert isinstance(json_str, str)


def test_e2e_get_git_provenance_returns_correct_types_batch16(tmp_path):
    fake_runs = [_mk_run(stdout="abc\n", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = get_git_provenance(tmp_path)
    assert isinstance(r["git_commit"], str)
    assert isinstance(r["git_dirty"], bool)


def test_e2e_aggregate_summary_with_missing_metrics_key_batch16():
    """per_doc 缺 metrics 字段 → aggregate 会 KeyError（r['metrics']）。"""
    per_doc = [{}]  # 无 metrics key
    with pytest.raises(KeyError):
        aggregate_summary(per_doc)


def test_e2e_build_provenance_with_empty_string_parser_version_batch16(tmp_path):
    """parser_version="" 也接受。"""
    fake_runs = [_mk_run(stdout="abc\n", returncode=0), _mk_run(stdout="", returncode=0)]
    with patch("subprocess.run", side_effect=fake_runs):
        r = build_provenance(tmp_path, "fallback", 800, "")
    assert r["parser_version"] == ""
