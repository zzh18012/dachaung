"""evaluation/report.py 第二十二轮 edges 测试（Round 360）。

重点补强 edges21 未触及的角度：
- get_git_provenance source level 字符串精确补强第二批
- get_dependency_versions source level 字符串精确补强第二批
- build_provenance source level 字符串精确补强第二批
- build_devset_section source level 字符串精确补强第二批
- aggregate_summary source level 字符串精确补强第二批
- module source forbidden tokens 第七批（注意 subprocess 是合法的）
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性补强
- 端到端集成补强
"""

from __future__ import annotations

import inspect
import json
import subprocess
import types
from datetime import datetime
from pathlib import Path
from typing import Any

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


# ---------- get_git_provenance source level 字符串精确补强第二批 ----------


def test_get_git_provenance_source_starts_with_def():
    src = inspect.getsource(get_git_provenance)
    assert src.lstrip().startswith("def get_git_provenance(")


def test_get_git_provenance_source_one_param():
    src = inspect.getsource(get_git_provenance)
    assert "project_root: Path" in src


def test_get_git_provenance_source_returns_dict():
    src = inspect.getsource(get_git_provenance)
    assert "-> dict[str, Any]" in src


def test_get_git_provenance_source_uses_subprocess_run():
    src = inspect.getsource(get_git_provenance)
    assert "subprocess.run(" in src


def test_get_git_provenance_source_uses_rev_parse_head():
    src = inspect.getsource(get_git_provenance)
    assert '"git", "rev-parse", "HEAD"' in src


def test_get_git_provenance_source_uses_status_porcelain():
    src = inspect.getsource(get_git_provenance)
    assert '"git", "status", "--porcelain"' in src


def test_get_git_provenance_source_uses_capture_output():
    src = inspect.getsource(get_git_provenance)
    assert "capture_output=True" in src


def test_get_git_provenance_source_uses_text_true():
    src = inspect.getsource(get_git_provenance)
    assert "text=True" in src


def test_get_git_provenance_source_uses_encoding_utf8():
    src = inspect.getsource(get_git_provenance)
    assert 'encoding="utf-8"' in src


def test_get_git_provenance_source_uses_errors_replace():
    src = inspect.getsource(get_git_provenance)
    assert 'errors="replace"' in src


def test_get_git_provenance_source_uses_timeout_10():
    src = inspect.getsource(get_git_provenance)
    assert "timeout=10" in src


def test_get_git_provenance_source_uses_oserror_subprocess_error():
    src = inspect.getsource(get_git_provenance)
    assert "OSError" in src
    assert "subprocess.SubprocessError" in src


def test_get_git_provenance_source_uses_cwd():
    src = inspect.getsource(get_git_provenance)
    assert "cwd=" in src


def test_get_git_provenance_source_uses_initial_values():
    src = inspect.getsource(get_git_provenance)
    assert "commit: str | None = None" in src
    assert "dirty: bool = True" in src


def test_get_git_provenance_source_returns_dict_with_2_keys():
    src = inspect.getsource(get_git_provenance)
    assert '"git_commit"' in src
    assert '"git_dirty"' in src


def test_get_git_provenance_source_uses_returncode_check():
    src = inspect.getsource(get_git_provenance)
    assert "r.returncode == 0" in src
    assert "r2.returncode == 0" in src


def test_get_git_provenance_source_uses_stdout_strip():
    src = inspect.getsource(get_git_provenance)
    assert ".stdout.strip()" in src


def test_get_git_provenance_source_uses_bool_for_dirty():
    src = inspect.getsource(get_git_provenance)
    assert "dirty = bool(" in src


# ---------- get_dependency_versions source level 字符串精确补强第二批 ----------


def test_get_dependency_versions_source_starts_with_def():
    src = inspect.getsource(get_dependency_versions)
    assert src.lstrip().startswith("def get_dependency_versions(")


def test_get_dependency_versions_source_no_params():
    src = inspect.getsource(get_dependency_versions)
    # 没有参数
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_get_dependency_versions_source_returns_dict():
    src = inspect.getsource(get_dependency_versions)
    assert "-> dict[str, str | None]" in src


def test_get_dependency_versions_source_lazy_import_importlib():
    src = inspect.getsource(get_dependency_versions)
    assert "import importlib.metadata" in src


def test_get_dependency_versions_source_3_packages():
    src = inspect.getsource(get_dependency_versions)
    assert '"pdfplumber"' in src
    assert '"python-docx"' in src
    assert '"pypdfium2"' in src


def test_get_dependency_versions_source_uses_importlib_metadata_version():
    src = inspect.getsource(get_dependency_versions)
    assert "importlib.metadata.version(pkg)" in src


def test_get_dependency_versions_source_uses_package_not_found():
    src = inspect.getsource(get_dependency_versions)
    assert "importlib.metadata.PackageNotFoundError" in src


def test_get_dependency_versions_source_uses_generic_exception():
    src = inspect.getsource(get_dependency_versions)
    assert "except Exception" in src


def test_get_dependency_versions_source_returns_versions_dict():
    src = inspect.getsource(get_dependency_versions)
    assert "return versions" in src


# ---------- build_provenance source level 字符串精确补强第二批 ----------


def test_build_provenance_source_starts_with_def():
    src = inspect.getsource(build_provenance)
    assert src.lstrip().startswith("def build_provenance(")


def test_build_provenance_source_4_params():
    src = inspect.getsource(build_provenance)
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.values())
    assert len(params) == 4
    assert [p.name for p in params] == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_build_provenance_source_returns_dict():
    src = inspect.getsource(build_provenance)
    assert "-> dict[str, Any]" in src


def test_build_provenance_source_calls_get_git_provenance():
    src = inspect.getsource(build_provenance)
    assert "get_git_provenance(project_root)" in src


def test_build_provenance_source_calls_get_dependency_versions():
    src = inspect.getsource(build_provenance)
    assert "get_dependency_versions()" in src


def test_build_provenance_source_returns_8_keys():
    src = inspect.getsource(build_provenance)
    assert '"git_commit"' in src
    assert '"git_dirty"' in src
    assert '"evaluator_version"' in src
    assert '"report_version"' in src
    assert '"parser_name"' in src
    assert '"parser_version"' in src
    assert '"dependencies"' in src
    assert '"max_chars"' in src
    assert '"run_timestamp_iso"' in src


def test_build_provenance_source_uses_evaluator_version():
    src = inspect.getsource(build_provenance)
    assert "EVALUATOR_VERSION" in src


def test_build_provenance_source_uses_report_version():
    src = inspect.getsource(build_provenance)
    assert "REPORT_VERSION" in src


def test_build_provenance_source_uses_int_max_chars():
    src = inspect.getsource(build_provenance)
    assert "int(max_chars)" in src


def test_build_provenance_source_uses_datetime_now_astimezone():
    src = inspect.getsource(build_provenance)
    assert "datetime.now().astimezone().isoformat()" in src


def test_build_provenance_source_no_eval():
    src = inspect.getsource(build_provenance)
    assert "eval(" not in src


# ---------- build_devset_section source level 字符串精确补强第二批 ----------


def test_build_devset_section_source_starts_with_def():
    src = inspect.getsource(build_devset_section)
    assert src.lstrip().startswith("def build_devset_section(")


def test_build_devset_section_source_one_param():
    src = inspect.getsource(build_devset_section)
    assert "manifest" in src


def test_build_devset_section_source_returns_dict():
    src = inspect.getsource(build_devset_section)
    assert "-> dict[str, Any]" in src


def test_build_devset_section_source_6_keys():
    src = inspect.getsource(build_devset_section)
    assert '"status"' in src
    assert '"file_count"' in src
    assert '"content_group_count"' in src
    assert '"pdf_count"' in src
    assert '"docx_count"' in src
    assert '"categories_covered"' in src


def test_build_devset_section_source_uses_manifest_devset_status():
    src = inspect.getsource(build_devset_section)
    assert "manifest.devset_status" in src


def test_build_devset_section_source_uses_manifest_file_count():
    src = inspect.getsource(build_devset_section)
    assert "manifest.file_count" in src


def test_build_devset_section_source_uses_manifest_categories_covered():
    src = inspect.getsource(build_devset_section)
    assert "manifest.categories_covered" in src


def test_build_devset_section_source_no_eval():
    src = inspect.getsource(build_devset_section)
    assert "eval(" not in src


# ---------- aggregate_summary source level 字符串精确补强第二批 ----------


def test_aggregate_summary_source_starts_with_def():
    src = inspect.getsource(aggregate_summary)
    assert src.lstrip().startswith("def aggregate_summary(")


def test_aggregate_summary_source_one_param():
    src = inspect.getsource(aggregate_summary)
    assert "per_doc_results: list[dict[str, Any]]" in src


def test_aggregate_summary_source_returns_dict():
    src = inspect.getsource(aggregate_summary)
    assert "-> dict[str, Any]" in src


def test_aggregate_summary_source_4_top_keys():
    src = inspect.getsource(aggregate_summary)
    assert '"counts"' in src
    assert '"success_rates"' in src
    assert '"ratio_macro_averages"' in src
    assert '"silent_drop_total"' in src


def test_aggregate_summary_source_uses_count_metrics_constant():
    src = inspect.getsource(aggregate_summary)
    assert "_COUNT_METRICS" in src


def test_aggregate_summary_source_uses_success_bool_metrics_constant():
    src = inspect.getsource(aggregate_summary)
    assert "_SUCCESS_BOOL_METRICS" in src


def test_aggregate_summary_source_uses_ratio_metrics_constant():
    src = inspect.getsource(aggregate_summary)
    assert "_RATIO_METRICS" in src


def test_aggregate_summary_source_uses_sum_for_counts():
    src = inspect.getsource(aggregate_summary)
    assert '"sum": sum(values)' in src


def test_aggregate_summary_source_uses_participating_docs():
    src = inspect.getsource(aggregate_summary)
    assert '"participating_docs"' in src


def test_aggregate_summary_source_uses_success_count():
    src = inspect.getsource(aggregate_summary)
    assert '"success_count"' in src


def test_aggregate_summary_source_uses_total():
    src = inspect.getsource(aggregate_summary)
    assert '"total"' in src


def test_aggregate_summary_source_uses_rate():
    src = inspect.getsource(aggregate_summary)
    assert '"rate"' in src


def test_aggregate_summary_source_uses_macro_average():
    src = inspect.getsource(aggregate_summary)
    assert '"macro_average"' in src


def test_aggregate_summary_source_uses_not_evaluated():
    src = inspect.getsource(aggregate_summary)
    assert '"not_evaluated"' in src


def test_aggregate_summary_source_uses_silent_drop_count():
    src = inspect.getsource(aggregate_summary)
    assert '"silent_drop_count"' in src


def test_aggregate_summary_source_uses_silent_drop_total():
    src = inspect.getsource(aggregate_summary)
    assert '"silent_drop_total"' in src


def test_aggregate_summary_source_uses_get_value():
    src = inspect.getsource(aggregate_summary)
    assert '.get("value")' in src


def test_aggregate_summary_source_uses_get_metrics():
    src = inspect.getsource(aggregate_summary)
    assert 'r["metrics"]' in src


def test_aggregate_summary_source_returns_summary():
    src = inspect.getsource(aggregate_summary)
    assert "return summary" in src


def test_aggregate_summary_source_initializes_summary_dict():
    src = inspect.getsource(aggregate_summary)
    assert "summary: dict[str, Any] = {}" in src


def test_aggregate_summary_source_uses_count_branch_with_loop():
    src = inspect.getsource(aggregate_summary)
    assert "for name in _COUNT_METRICS:" in src


def test_aggregate_summary_source_uses_success_branch_with_loop():
    src = inspect.getsource(aggregate_summary)
    assert "for name in _SUCCESS_BOOL_METRICS:" in src


def test_aggregate_summary_source_uses_ratio_branch_with_loop():
    src = inspect.getsource(aggregate_summary)
    assert "for name in _RATIO_METRICS:" in src


def test_aggregate_summary_source_uses_macro_calc():
    src = inspect.getsource(aggregate_summary)
    assert "sum(values) / len(values)" in src


# ---------- module source forbidden tokens 第七批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "asyncio", "threading", "concurrent", "multiprocessing",
        "queue", "socket", "select",
        "re.match", "re.sub", "re.compile",
        "datetime.datetime",  # 单独 datetime 是合法的
        "time.time", "time.sleep",
        "os.system", "os.popen",
        "logging.getLogger",
        "urllib.request", "http.client",
        "ctypes", "pickle.loads",
        "shutil.rmtree",
        "tempfile.mkdtemp",
        "glob.glob",
        "unittest.TestCase",
        "pytest.fixture",
        "sys.exit",
        "copy.deepcopy",
        "weakref.ref",
        "abc.ABC",
        "contextlib.contextmanager",
        "operator.add",
        "functools.reduce",
        "itertools.chain",
        "collections.OrderedDict",
        "collections.deque",
        "collections.defaultdict",
        "importlib.import_module",
        "platform.system",
    ],
)
def test_report_source_no_forbidden_token(token):
    src = inspect.getsource(rmod)
    assert token not in src, f"forbidden token found: {token}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_docstring_present():
    src = inspect.getsource(rmod)
    assert src.startswith('"""')


def test_module_source_docstring_mentions_provenance():
    assert "provenance" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_devset():
    assert "devset" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_summary():
    assert "summary" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_per_doc():
    assert "per_doc" in rmod.__doc__


def test_module_source_docstring_mentions_aggregate():
    assert "聚合" in rmod.__doc__ or "aggregate" in rmod.__doc__.lower()


def test_module_source_has_future_annotations():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_imports_subprocess():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_imports_datetime():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_imports_path():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_imports_any():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_imports_evaluation_versions():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_3_metric_constants():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS = (" in src
    assert "_COUNT_METRICS = (" in src
    assert "_SUCCESS_BOOL_METRICS = (" in src


def test_module_source_ratio_metrics_12_entries():
    """_RATIO_METRICS 含 12 个 ratio 指标。"""
    assert len(_RATIO_METRICS) == 12


def test_module_source_count_metrics_1_entry():
    assert len(_COUNT_METRICS) == 1


def test_module_source_success_bool_metrics_1_entry():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_module_source_no_relative_above_root():
    src = inspect.getsource(rmod)
    assert "from .." not in src


def test_module_source_no_star_import():
    src = inspect.getsource(rmod)
    assert "import *" not in src


def test_module_source_no_yield():
    src = inspect.getsource(rmod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(rmod)
    assert "async def" not in src


def test_module_source_no_walrus():
    src = inspect.getsource(rmod)
    assert ":=" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(rmod)
    assert 'if __name__' not in src


def test_module_source_no_user_class():
    classes = [
        name for name, val in vars(rmod).items()
        if isinstance(val, type) and val.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_source_5_user_functions():
    funcs = [
        name for name, val in vars(rmod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == rmod.__name__
    ]
    assert set(funcs) == {
        "get_git_provenance", "get_dependency_versions",
        "build_provenance", "build_devset_section", "aggregate_summary",
    }


def test_module_source_all_5_entries():
    src = inspect.getsource(rmod)
    assert '__all__ = [' in src
    assert '"build_provenance"' in src
    assert '"build_devset_section"' in src
    assert '"aggregate_summary"' in src
    assert '"get_git_provenance"' in src
    assert '"get_dependency_versions"' in src


def test_module_source_no_eval():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_compile():
    src = inspect.getsource(rmod)
    assert "compile(" not in src


def test_module_source_subprocess_allowed():
    """subprocess 在 report.py 中合法（get_git_provenance 需要）。"""
    src = inspect.getsource(rmod)
    assert "subprocess" in src


def test_module_source_datetime_allowed():
    src = inspect.getsource(rmod)
    assert "datetime" in src


def test_module_source_no_unlink():
    src = inspect.getsource(rmod)
    assert ".unlink(" not in src


def test_module_source_no_write():
    src = inspect.getsource(rmod)
    assert ".write(" not in src


# ---------- signatures 精确补强 ----------


def test_signature_get_git_provenance():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "project_root"


def test_signature_get_dependency_versions():
    sig = inspect.signature(get_dependency_versions)
    params = list(sig.parameters.values())
    assert len(params) == 0


def test_signature_build_provenance():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.values())
    assert len(params) == 4
    assert [p.name for p in params] == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_provenance_no_defaults():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_build_provenance_no_varargs():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_build_devset_section():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "manifest"


def test_signature_aggregate_summary():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "per_doc_results"


def test_signature_aggregate_summary_no_varargs():
    sig = inspect.signature(aggregate_summary)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_get_git_provenance_no_varargs():
    sig = inspect.signature(get_git_provenance)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


# ---------- 模块整体合理性补强 ----------


def test_module_has_docstring():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 10


def test_module_has_all_attribute():
    assert hasattr(rmod, "__all__")


def test_module_all_is_list():
    assert isinstance(rmod.__all__, list)


def test_module_all_length_5():
    assert len(rmod.__all__) == 5


def test_module_all_entries_unique():
    assert len(set(rmod.__all__)) == len(rmod.__all__)


def test_module_all_entries_are_str():
    for entry in rmod.__all__:
        assert isinstance(entry, str)


def test_module_namespace_5_callables():
    funcs = [
        name for name, val in vars(rmod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == rmod.__name__
    ]
    assert set(funcs) == {
        "get_git_provenance", "get_dependency_versions",
        "build_provenance", "build_devset_section", "aggregate_summary",
    }


def test_module_namespace_3_constants():
    """3 个 metric constants。"""
    assert hasattr(rmod, "_RATIO_METRICS")
    assert hasattr(rmod, "_COUNT_METRICS")
    assert hasattr(rmod, "_SUCCESS_BOOL_METRICS")


def test_module_no_user_classes():
    classes = [
        name for name, val in vars(rmod).items()
        if isinstance(val, type) and val.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_name_is_evaluation_report():
    assert rmod.__name__ == "evaluation.report"


def test_module_file_ends_with_report_py():
    assert rmod.__file__.endswith("report.py")


def test_module_function_module_eq_rmod():
    assert get_git_provenance.__module__ == "evaluation.report"
    assert build_provenance.__module__ == "evaluation.report"
    assert aggregate_summary.__module__ == "evaluation.report"


def test_module_constants_module_builtins():
    """tuple 的 __module__ 是 builtins。"""
    assert _RATIO_METRICS.__class__.__module__ == "builtins"


def test_module_ratio_metrics_is_tuple():
    assert isinstance(_RATIO_METRICS, tuple)


def test_module_count_metrics_is_tuple():
    assert isinstance(_COUNT_METRICS, tuple)


def test_module_success_bool_metrics_is_tuple():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_module_count_metrics_subset_of_known():
    assert set(_COUNT_METRICS) == {"element_count_total"}


def test_module_success_bool_metrics_subset_of_known():
    assert set(_SUCCESS_BOOL_METRICS) == {"pipeline_success"}


def test_module_imports_evaluator_version():
    assert rmod.EVALUATOR_VERSION == EVALUATOR_VERSION


def test_module_imports_report_version():
    assert rmod.REPORT_VERSION == REPORT_VERSION


def test_module_imports_subprocess():
    assert rmod.subprocess is subprocess


def test_module_imports_datetime():
    assert rmod.datetime is datetime


def test_module_imports_path():
    assert rmod.Path is Path


# ---------- 端到端集成补强 ----------


def test_e2e_get_git_provenance_returns_dict_with_2_keys():
    out = get_git_provenance(Path("."))
    assert isinstance(out, dict)
    assert "git_commit" in out
    assert "git_dirty" in out


def test_e2e_get_git_provenance_in_repo_commit_str_or_none():
    """在 git repo 内 commit 是 str 或 None。"""
    out = get_git_provenance(Path("."))
    assert out["git_commit"] is None or isinstance(out["git_commit"], str)


def test_e2e_get_git_provenance_dirty_is_bool():
    out = get_git_provenance(Path("."))
    assert isinstance(out["git_dirty"], bool)


def test_e2e_get_git_provenance_nonexistent_dir():
    out = get_git_provenance(Path("/does/not/exist"))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_e2e_get_dependency_versions_returns_dict():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_e2e_get_dependency_versions_3_keys():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_e2e_get_dependency_versions_str_or_none():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str)


def test_e2e_build_provenance_returns_dict():
    out = build_provenance(Path("."), "fallback", 800, "test")
    assert isinstance(out, dict)


def test_e2e_build_provenance_9_keys():
    out = build_provenance(Path("."), "fallback", 800, "test")
    assert set(out.keys()) == {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    }


def test_e2e_build_provenance_evaluator_version_value():
    out = build_provenance(Path("."), "fallback", 800, "test")
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_e2e_build_provenance_report_version_value():
    out = build_provenance(Path("."), "fallback", 800, "test")
    assert out["report_version"] == REPORT_VERSION


def test_e2e_build_provenance_max_chars_int():
    out = build_provenance(Path("."), "fallback", 800, "test")
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_e2e_build_provenance_max_chars_str_input():
    """max_chars 会被 int() 转换。"""
    out = build_provenance(Path("."), "fallback", "800", "test")
    assert out["max_chars"] == 800


def test_e2e_build_provenance_run_timestamp_iso_format():
    out = build_provenance(Path("."), "fallback", 800, "test")
    # ISO 格式：包含 T
    assert "T" in out["run_timestamp_iso"]


def test_e2e_build_devset_section_returns_dict():
    """build_devset_section 接受 Manifest-like object。"""
    class FakeManifest:
        devset_status = "complete"
        file_count = 5
        content_group_count = 2
        pdf_count = 3
        docx_count = 2
        categories_covered = ["a", "b"]
    out = build_devset_section(FakeManifest())
    assert isinstance(out, dict)


def test_e2e_build_devset_section_6_keys():
    class FakeManifest:
        devset_status = "complete"
        file_count = 5
        content_group_count = 2
        pdf_count = 3
        docx_count = 2
        categories_covered = ["a", "b"]
    out = build_devset_section(FakeManifest())
    assert set(out.keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_e2e_aggregate_summary_empty():
    out = aggregate_summary([])
    assert isinstance(out, dict)
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["success_rates"]["pipeline_success"]["rate"] is None
    assert out["silent_drop_total"] is None


def test_e2e_aggregate_summary_one_doc_all_success():
    per_doc = [{
        "metrics": {
            "pipeline_success": {"value": True, "reason": None},
            "schema_valid": {"value": True, "reason": None},
            "element_count_total": {"value": 5, "reason": None},
            "pdf_locator_valid_ratio": {"value": 1.0, "reason": None},
            "silent_drop_count": {"value": 0, "reason": None},
        }
    }]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0
    assert out["silent_drop_total"] == 0


def test_e2e_aggregate_summary_does_not_mutate_input():
    per_doc = [{
        "metrics": {
            "pipeline_success": {"value": True, "reason": None},
            "element_count_total": {"value": 5, "reason": None},
        }
    }]
    import json as _json
    before = _json.dumps(per_doc, sort_keys=True)
    aggregate_summary(per_doc)
    assert _json.dumps(per_doc, sort_keys=True) == before


def test_e2e_aggregate_summary_idempotent():
    per_doc = [{
        "metrics": {
            "pipeline_success": {"value": True, "reason": None},
            "element_count_total": {"value": 5, "reason": None},
        }
    }]
    out1 = aggregate_summary(per_doc)
    out2 = aggregate_summary(per_doc)
    assert out1 == out2


def test_e2e_aggregate_summary_positional_args():
    out = aggregate_summary([])
    assert isinstance(out, dict)


def test_e2e_aggregate_summary_kwargs():
    out = aggregate_summary(per_doc_results=[])
    assert isinstance(out, dict)


def test_e2e_aggregate_summary_3_ratio_metrics_present():
    """ratio_macro_averages 包含 12 个 ratio。"""
    out = aggregate_summary([])
    assert len(out["ratio_macro_averages"]) == 12


def test_e2e_aggregate_summary_1_count_metric():
    out = aggregate_summary([])
    assert len(out["counts"]) == 1


def test_e2e_aggregate_summary_1_success_metric():
    out = aggregate_summary([])
    assert len(out["success_rates"]) == 1


def test_e2e_aggregate_summary_partial_participation():
    """一些文档没有某 metric → 不参与 macro average。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": True}}},
        {"metrics": {}},  # 没有 schema_valid
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1


def test_e2e_aggregate_summary_macro_average_correct():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.75


def test_e2e_aggregate_summary_json_serializable():
    per_doc = [{
        "metrics": {
            "pipeline_success": {"value": True, "reason": None},
            "element_count_total": {"value": 5, "reason": None},
        }
    }]
    out = aggregate_summary(per_doc)
    assert json.dumps(out)  # 不抛


def test_e2e_build_provenance_kwargs():
    out = build_provenance(
        project_root=Path("."),
        parser_name="fallback",
        max_chars=800,
        parser_version="test",
    )
    assert out["parser_name"] == "fallback"


def test_e2e_build_provenance_positional():
    out = build_provenance(Path("."), "fallback", 800, "test")
    assert out["parser_name"] == "fallback"


def test_e2e_full_chain_aggregate_devset_provenance():
    """完整链：aggregate → devset → provenance。"""
    per_doc = [{"metrics": {"pipeline_success": {"value": True}}}]
    summary = aggregate_summary(per_doc)

    class FakeManifest:
        devset_status = "complete"
        file_count = 1
        content_group_count = 1
        pdf_count = 1
        docx_count = 0
        categories_covered = ["x"]
    devset = build_devset_section(FakeManifest())

    provenance = build_provenance(Path("."), "fallback", 800, "test")

    # 组装报告
    report = {
        "summary": summary,
        "devset": devset,
        "provenance": provenance,
    }
    serialized = json.dumps(report, default=str)
    assert "summary" in serialized
    assert "devset" in serialized
    assert "provenance" in serialized
