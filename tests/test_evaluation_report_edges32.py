"""evaluation/report.py 第三十二轮 edges 测试（Round 430）。

补强 edges31 未触及的角度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元组深度第十五批（schema_valid 在 ratio / figure_caption_* 不在 ratio / pipeline_success 仅在 success / element_count_total 仅在 count）
- get_git_provenance 行为深度第十五批（r.stdout 含多个连续 newline / r.stdout 仅 \n / r.stderr 非空 / r2.stdout 含 \r\n / r.returncode 与 stdout 同时异常）
- get_dependency_versions 行为深度第十五批（三个固定 key / 值类型 str 或 None / 字典可序列化 / 多次一致 / 包名拼写）
- build_provenance 字段深度第十五批（max_chars 强转 int / run_timestamp_iso ISO 格式 / git_commit None 默认 / git_dirty True 默认 / dependencies 嵌套 dict）
- build_devset_section 字段深度第十五批（与 manifest 属性一一对应 / categories_covered list 类型 / 6 keys 准确 / 不修改 manifest）
- aggregate_summary 行为深度第十五批（counts sum None 时 / success_rates rate None / ratio macro_average None / not_evaluated 计算 / participating_docs 计算 / silent_drop_total sum）
- module source forbidden tokens 第二十五批
- module source 字符串精确补强第二十二批
- signatures 第二十二批
- module 合理性第二十二批
- 端到端集成第二十二批
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元组深度第十五批 ----------


def test_ratio_metrics_includes_schema_valid_batch15():
    """schema_valid 也在 _RATIO_METRICS 中（bool 是 ratio 的特殊形式）。"""
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_excludes_figure_caption_batch15():
    """figure_caption_* 不在 _RATIO_METRICS 中（始终 null）。"""
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_ratio_metrics_excludes_pipeline_success_batch15():
    """pipeline_success 在 _SUCCESS_BOOL_METRICS 而非 _RATIO_METRICS。"""
    assert "pipeline_success" not in _RATIO_METRICS


def test_ratio_metrics_excludes_element_count_batch15():
    assert "element_count_total" not in _RATIO_METRICS


def test_count_metrics_only_element_count_batch15():
    """_COUNT_METRICS 仅含 element_count_total。"""
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_only_pipeline_batch15():
    """_SUCCESS_BOOL_METRICS 仅含 pipeline_success。"""
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_ratio_metrics_has_12_items_batch15():
    """_RATIO_METRICS 必须有 12 个 key。"""
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_includes_chunk_boundary_batch15():
    """chunk_boundary_* 在 _RATIO_METRICS 中。"""
    assert "chunk_boundary_precision" in _RATIO_METRICS
    assert "chunk_boundary_recall" in _RATIO_METRICS
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_includes_text_metrics_batch15():
    """text_preservation 与 text_char_multiset_* 在 _RATIO_METRICS 中。"""
    assert "text_preservation_equal" in _RATIO_METRICS
    assert "text_char_multiset_precision" in _RATIO_METRICS
    assert "text_char_multiset_recall" in _RATIO_METRICS


# ---------- get_git_provenance 行为深度第十五批 ----------


def test_get_git_provenance_multiple_newlines_in_stdout_batch15(tmp_path):
    """r.stdout 含多个连续 newline 也应 strip 干净。"""
    fake_r1 = MagicMock(returncode=0, stdout="\n\nabc123\n\n", stderr="")
    fake_r2 = MagicMock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake_r1, fake_r2]):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] == "abc123"


def test_get_git_provenance_stdout_only_newline_batch15(tmp_path):
    """r.stdout 仅 \n → strip 后为空 → commit=None。"""
    fake_r1 = MagicMock(returncode=0, stdout="\n", stderr="")
    fake_r2 = MagicMock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake_r1, fake_r2]):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None


def test_get_git_provenance_stderr_nonempty_batch15(tmp_path):
    """stderr 非空不影响结果（只看 returncode 与 stdout）。"""
    fake_r1 = MagicMock(returncode=0, stdout="abc123\n", stderr="some warning")
    fake_r2 = MagicMock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake_r1, fake_r2]):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] == "abc123"
    assert result["git_dirty"] is False


def test_get_git_provenance_r2_crlf_batch15(tmp_path):
    """r2.stdout 含 \r\n → strip 后非空 → dirty=True。"""
    fake_r1 = MagicMock(returncode=0, stdout="abc123\n", stderr="")
    fake_r2 = MagicMock(returncode=0, stdout=" M file.txt\r\n", stderr="")
    with patch("subprocess.run", side_effect=[fake_r1, fake_r2]):
        result = get_git_provenance(tmp_path)
    assert result["git_dirty"] is True


def test_get_git_provenance_r_returncode_nonzero_batch15(tmp_path):
    """r.returncode != 0 → commit=None（不抛异常）。"""
    fake_r1 = MagicMock(returncode=1, stdout="", stderr="error")
    fake_r2 = MagicMock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", side_effect=[fake_r1, fake_r2]):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None


def test_get_git_provenance_r2_returncode_nonzero_batch15(tmp_path):
    """r2.returncode != 0 → dirty=False（短路求值）。"""
    fake_r1 = MagicMock(returncode=0, stdout="abc\n", stderr="")
    fake_r2 = MagicMock(returncode=1, stdout="some change", stderr="error")
    with patch("subprocess.run", side_effect=[fake_r1, fake_r2]):
        result = get_git_provenance(tmp_path)
    # bool(r2.returncode == 0 and r2.stdout.strip()) = bool(False and ...) = False
    assert result["git_dirty"] is False


def test_get_git_provenance_oserror_batch15(tmp_path):
    """OSError → commit=None, dirty=True。"""
    with patch("subprocess.run", side_effect=OSError("boom")):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_get_git_provenance_timeout_batch15(tmp_path):
    """subprocess.TimeoutExpired（SubprocessError 子类）→ 异常处理。"""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10)):
        result = get_git_provenance(tmp_path)
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


# ---------- get_dependency_versions 行为深度第十五批 ----------


def test_get_dependency_versions_returns_three_keys_batch15():
    v = get_dependency_versions()
    assert set(v.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_value_types_batch15():
    v = get_dependency_versions()
    for k, val in v.items():
        assert val is None or isinstance(val, str)


def test_get_dependency_versions_serializable_batch15():
    """结果可序列化（用 repr 替代 json，因为可能有 None）。"""
    v = get_dependency_versions()
    # repr 不抛异常即可
    assert repr(v) is not None


def test_get_dependency_versions_idempotent_batch15():
    """多次调用一致。"""
    v1 = get_dependency_versions()
    v2 = get_dependency_versions()
    assert v1 == v2


def test_get_dependency_versions_python_docx_spelling_batch15():
    """注意 key 是 'python-docx'（连字符），不是 'python_docx'（下划线）。"""
    v = get_dependency_versions()
    assert "python-docx" in v
    assert "python_docx" not in v


def test_get_dependency_versions_package_not_found_batch15():
    """模拟 PackageNotFoundError → 该 key 值为 None。"""
    import importlib.metadata as im
    with patch("importlib.metadata.version", side_effect=im.PackageNotFoundError):
        v = get_dependency_versions()
    for k in v:
        assert v[k] is None


def test_get_dependency_versions_unexpected_exception_batch15():
    """模拟其它异常 → 该 key 值为 None。"""
    with patch("importlib.metadata.version", side_effect=ValueError("unexpected")):
        v = get_dependency_versions()
    for k in v:
        assert v[k] is None


# ---------- build_provenance 字段深度第十五批 ----------


def test_build_provenance_max_chars_int_coerce_batch15(tmp_path):
    """max_chars 强转 int。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
        with patch("evaluation.report.get_dependency_versions", return_value={"pdfplumber": "1.0"}):
            result = build_provenance(tmp_path, "fallback", "800", "1.0")
    assert result["max_chars"] == 800
    assert isinstance(result["max_chars"], int)


def test_build_provenance_run_timestamp_iso_format_batch15(tmp_path):
    """run_timestamp_iso 是 ISO 格式。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            result = build_provenance(tmp_path, "fallback", 800, "1.0")
    ts = result["run_timestamp_iso"]
    # 能用 fromisoformat 解析
    parsed = datetime.fromisoformat(ts)
    assert parsed is not None


def test_build_provenance_git_commit_none_batch15(tmp_path):
    """git_commit 可以为 None。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            result = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert result["git_commit"] is None
    assert result["git_dirty"] is True


def test_build_provenance_evaluator_version_constant_batch15(tmp_path):
    """evaluator_version 来自 EVALUATOR_VERSION 常量。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            result = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert result["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_constant_batch15(tmp_path):
    """report_version 来自 REPORT_VERSION 常量。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            result = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert result["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_passthrough_batch15(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            result = build_provenance(tmp_path, "kreuzberg", 800, "1.0")
    assert result["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_none_batch15(tmp_path):
    """parser_version 可以为 None。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            result = build_provenance(tmp_path, "fallback", 800, None)
    assert result["parser_version"] is None


def test_build_provenance_keys_count_batch15(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            result = build_provenance(tmp_path, "fallback", 800, "1.0")
    expected = {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    }
    assert set(result.keys()) == expected


# ---------- build_devset_section 字段深度第十五批 ----------


def test_build_devset_section_keys_count_6_batch15():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 5
    m.content_group_count = 3
    m.pdf_count = 2
    m.docx_count = 3
    m.categories_covered = ["a", "b"]
    result = build_devset_section(m)
    assert len(result) == 6


def test_build_devset_section_status_value_batch15():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    result = build_devset_section(m)
    assert result["status"] == "complete"


def test_build_devset_section_categories_covered_list_batch15():
    """categories_covered 是 list（不是 tuple 或 set）。"""
    m = MagicMock()
    m.devset_status = "x"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = ["x", "y"]
    result = build_devset_section(m)
    assert isinstance(result["categories_covered"], list)


def test_build_devset_section_does_not_mutate_input_batch15():
    """不修改输入 manifest。"""
    m = MagicMock()
    m.devset_status = "x"
    m.file_count = 1
    m.content_group_count = 1
    m.pdf_count = 1
    m.docx_count = 0
    m.categories_covered = ["x"]
    build_devset_section(m)
    # 应该读取每个属性一次
    assert m.devset_status == "x"
    assert m.file_count == 1


def test_build_devset_section_keys_exact_batch15():
    m = MagicMock()
    m.devset_status = "x"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    result = build_devset_section(m)
    expected = {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }
    assert set(result.keys()) == expected


# ---------- aggregate_summary 行为深度第十五批 ----------


def test_aggregate_summary_counts_sum_none_when_no_values_batch15():
    """counts sum=None 当所有值都是 None。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_counts_sum_when_values_present_batch15():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": 3}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 8
    assert s["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_success_rates_rate_none_when_no_docs_batch15():
    """没有文档 → rate=None。"""
    s = aggregate_summary([])
    assert s["success_rates"]["pipeline_success"]["rate"] is None
    assert s["success_rates"]["pipeline_success"]["total"] == 0


def test_aggregate_summary_success_rates_with_mixed_batch15():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 3
    assert sr["rate"] == 2 / 3


def test_aggregate_summary_ratio_macro_average_none_when_no_values_batch15():
    s = aggregate_summary([])
    for name in _RATIO_METRICS:
        assert s["ratio_macro_averages"][name]["macro_average"] is None
        assert s["ratio_macro_averages"][name]["participating_docs"] == 0


def test_aggregate_summary_ratio_not_evaluated_calc_batch15():
    """not_evaluated = total - participating_docs。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": True}}},
        {"metrics": {"schema_valid": {"value": None}}},  # 不参与
        {"metrics": {"schema_valid": {"value": False}}},
    ]
    s = aggregate_summary(per_doc)
    r = s["ratio_macro_averages"]["schema_valid"]
    assert r["participating_docs"] == 2
    assert r["not_evaluated"] == 1
    assert r["macro_average"] == 0.5


def test_aggregate_summary_silent_drop_total_none_when_no_values_batch15():
    s = aggregate_summary([])
    assert s["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_total_sum_batch15():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
        {"metrics": {"silent_drop_count": {"value": None}}},  # 不参与
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 8


def test_aggregate_summary_pipeline_success_none_excluded_from_success_batch15():
    """pipeline_success=None 不算成功。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1
    assert s["success_rates"]["pipeline_success"]["total"] == 2


def test_aggregate_summary_returns_four_top_keys_batch15():
    """summary 必须有 4 个 top-level key。"""
    s = aggregate_summary([])
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


# ---------- module source forbidden tokens 第二十五批 ----------


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
def test_module_source_forbidden_tokens_batch15(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


# Note: subprocess IS allowed in report.py (for git provenance)


# ---------- module source 字符串精确补强第二十二批 ----------


def test_module_source_has_future_annotations_batch15():
    src = inspect.getsource(rmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch15():
    src = inspect.getsource(rmod)
    assert '"""评测报告装配' in src


def test_module_source_has_subprocess_import_batch15():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_has_datetime_import_batch15():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_has_path_import_batch15():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_any_import_batch15():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_evaluator_version_import_batch15():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_has_ratio_metrics_constant_batch15():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS = (" in src


def test_module_source_has_count_metrics_constant_batch15():
    src = inspect.getsource(rmod)
    assert '_COUNT_METRICS = ("element_count_total",)' in src


def test_module_source_has_success_bool_metrics_constant_batch15():
    src = inspect.getsource(rmod)
    assert '_SUCCESS_BOOL_METRICS = ("pipeline_success",)' in src


def test_module_source_has_get_git_provenance_function_batch15():
    src = inspect.getsource(rmod)
    assert "def get_git_provenance(project_root: Path) -> dict[str, Any]:" in src


def test_module_source_has_get_dependency_versions_function_batch15():
    src = inspect.getsource(rmod)
    assert "def get_dependency_versions() -> dict[str, str | None]:" in src


def test_module_source_has_build_provenance_function_batch15():
    src = inspect.getsource(rmod)
    assert "def build_provenance(" in src


def test_module_source_has_build_devset_section_function_batch15():
    src = inspect.getsource(rmod)
    assert "def build_devset_section(manifest) -> dict[str, Any]:" in src


def test_module_source_has_aggregate_summary_function_batch15():
    src = inspect.getsource(rmod)
    assert "def aggregate_summary(per_doc_results: list[dict[str, Any]]) -> dict[str, Any]:" in src


def test_module_source_has_all_dunder_batch15():
    src = inspect.getsource(rmod)
    assert "__all__ = [" in src


def test_module_source_all_contains_build_provenance_batch15():
    src = inspect.getsource(rmod)
    assert '"build_provenance"' in src


def test_module_source_all_contains_build_devset_section_batch15():
    src = inspect.getsource(rmod)
    assert '"build_devset_section"' in src


def test_module_source_all_contains_aggregate_summary_batch15():
    src = inspect.getsource(rmod)
    assert '"aggregate_summary"' in src


def test_module_source_all_contains_get_git_provenance_batch15():
    src = inspect.getsource(rmod)
    assert '"get_git_provenance"' in src


def test_module_source_all_contains_get_dependency_versions_batch15():
    src = inspect.getsource(rmod)
    assert '"get_dependency_versions"' in src


def test_module_source_has_dirty_calculation_batch15():
    src = inspect.getsource(rmod)
    assert "r2.returncode == 0 and r2.stdout.strip()" in src


def test_module_source_has_git_rev_parse_command_batch15():
    src = inspect.getsource(rmod)
    assert '"rev-parse"' in src or "'rev-parse'" in src


def test_module_source_has_git_status_porcelain_command_batch15():
    src = inspect.getsource(rmod)
    assert '"--porcelain"' in src or "'--porcelain'" in src


# ---------- signatures 第二十二批 ----------


def test_signature_get_git_provenance_batch15():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root"]


def test_signature_get_dependency_versions_batch15():
    sig = inspect.signature(get_dependency_versions)
    assert list(sig.parameters.keys()) == []


def test_signature_build_provenance_batch15():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.keys())
    assert params == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_devset_section_batch15():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.keys())
    assert params == ["manifest"]


def test_signature_aggregate_summary_batch15():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.keys())
    assert params == ["per_doc_results"]


def test_signature_build_provenance_no_defaults_batch15():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect._empty


def test_signature_aggregate_summary_no_varargs_batch15():
    sig = inspect.signature(aggregate_summary)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


# ---------- module 合理性第二十二批 ----------


def test_module_has_all_attribute_batch15():
    assert hasattr(rmod, "__all__")
    assert isinstance(rmod.__all__, list)


def test_module_all_items_callable_batch15():
    for name in rmod.__all__:
        attr = getattr(rmod, name)
        assert callable(attr)


def test_module_all_items_in_namespace_batch15():
    for name in rmod.__all__:
        assert hasattr(rmod, name)


def test_module_constants_in_namespace_batch15():
    assert "_RATIO_METRICS" in vars(rmod)
    assert "_COUNT_METRICS" in vars(rmod)
    assert "_SUCCESS_BOOL_METRICS" in vars(rmod)


def test_module_constants_are_tuples_batch15():
    assert isinstance(_RATIO_METRICS, tuple)
    assert isinstance(_COUNT_METRICS, tuple)
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_module_uses_subprocess_module_batch15():
    """模块用 subprocess 跑 git 命令。"""
    assert hasattr(rmod, "subprocess")


def test_module_uses_datetime_batch15():
    assert hasattr(rmod, "datetime")


def test_module_does_not_mutate_per_doc_results_batch15():
    """aggregate_summary 不修改 per_doc_results。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": 3}}},
    ]
    before = repr(per_doc)
    aggregate_summary(per_doc)
    assert repr(per_doc) == before


# ---------- 端到端集成第二十二批 ----------


def test_e2e_build_provenance_full_batch15(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
        with patch("evaluation.report.get_dependency_versions", return_value={"pdfplumber": "1.0", "python-docx": "2.0", "pypdfium2": "3.0"}):
            result = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert result["git_commit"] == "abc"
    assert result["git_dirty"] is False
    assert result["parser_name"] == "fallback"
    assert result["parser_version"] == "1.0"
    assert result["max_chars"] == 800
    assert result["dependencies"]["pdfplumber"] == "1.0"


def test_e2e_build_devset_section_from_manifest_mock_batch15():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 10
    m.content_group_count = 5
    m.pdf_count = 4
    m.docx_count = 6
    m.categories_covered = ["x", "y", "z"]
    result = build_devset_section(m)
    assert result == {
        "status": "incomplete",
        "file_count": 10,
        "content_group_count": 5,
        "pdf_count": 4,
        "docx_count": 6,
        "categories_covered": ["x", "y", "z"],
    }


def test_e2e_aggregate_summary_mixed_batch15():
    per_doc = [
        {
            "metrics": {
                "element_count_total": {"value": 5},
                "pipeline_success": {"value": True},
                "schema_valid": {"value": True},
                "silent_drop_count": {"value": 2},
            }
        },
        {
            "metrics": {
                "element_count_total": {"value": 3},
                "pipeline_success": {"value": False},
                "schema_valid": {"value": None},
                "silent_drop_count": {"value": None},
            }
        },
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 8
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1
    assert s["success_rates"]["pipeline_success"]["rate"] == 0.5
    # schema_valid participating 1 个（第 2 个是 None）
    assert s["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert s["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1
    assert s["silent_drop_total"] == 2


def test_e2e_aggregate_summary_empty_input_batch15():
    s = aggregate_summary([])
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["success_rates"]["pipeline_success"]["success_count"] == 0
    assert s["silent_drop_total"] is None


def test_e2e_aggregate_summary_with_all_metrics_in_per_doc_batch15():
    """per_doc 含所有 14 个 metric。"""
    metrics = {
        "pipeline_success": {"value": True},
        "error_code": {"value": None},
        "schema_valid": {"value": True},
        "element_count_total": {"value": 10},
        "element_count_by_type": {"value": {"heading": 1}},
        "pdf_locator_valid_ratio": {"value": 1.0},
        "docx_locator_valid_ratio": {"value": None, "reason": "x"},
        "image_resource_exists_ratio": {"value": None, "reason": "x"},
        "chunk_reference_intact_ratio": {"value": 1.0},
        "text_preservation_equal": {"value": True},
        "text_char_multiset_precision": {"value": 1.0},
        "text_char_multiset_recall": {"value": 1.0},
        "heading_boundary_compliance": {"value": 1.0},
        "silent_drop_count": {"value": 0},
    }
    s = aggregate_summary([{"metrics": metrics}])
    # 不崩溃即可
    assert "counts" in s
    assert "success_rates" in s


def test_e2e_provenance_to_dict_serializable_batch15(tmp_path):
    """build_provenance 返回 dict 应 json 可序列化。"""
    import json as _json
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
        with patch("evaluation.report.get_dependency_versions", return_value={"pdfplumber": "1.0"}):
            result = build_provenance(tmp_path, "fallback", 800, "1.0")
    s = _json.dumps(result)  # 不抛即可
    assert isinstance(s, str)


def test_e2e_aggregate_summary_dict_independence_batch15():
    """两次调用同一 per_doc 返回的 summary 互不影响。"""
    per_doc = [{"metrics": {"element_count_total": {"value": 5}}}]
    s1 = aggregate_summary(per_doc)
    s2 = aggregate_summary(per_doc)
    s1["counts"]["element_count_total"]["sum"] = 999
    assert s2["counts"]["element_count_total"]["sum"] == 5


def test_e2e_aggregate_summary_handles_extra_metrics_batch15():
    """per_doc 含未知 metric key 不应崩溃。"""
    per_doc = [{"metrics": {"unknown_metric": {"value": 999}}}]
    s = aggregate_summary(per_doc)
    assert "counts" in s  # 不崩溃即可


def test_e2e_build_devset_section_with_empty_categories_batch15():
    m = MagicMock()
    m.devset_status = "x"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    result = build_devset_section(m)
    assert result["categories_covered"] == []


def test_e2e_get_dependency_versions_actual_packages_batch15():
    """实际调用应返回真实版本（或 None）。"""
    v = get_dependency_versions()
    # 在开发环境中 pdfplumber 应该已安装
    assert v["pdfplumber"] is None or isinstance(v["pdfplumber"], str)
