"""evaluation/report.py 第二十六轮 edges 测试（Round 388）。

补强 edges25 未触及的角度：
- get_git_provenance 行为深度第九批（subprocess timeouts / 多次 rev-parse 调用顺序 / 不同 stdout 格式）
- get_dependency_versions 行为深度第九批（patch 不同分支 / 单 pkg 失败不影响其他 / 字符串版本号 / None 与 str 混合）
- build_provenance 行为深度第九批（不同 parser_version 类型 / max_chars 不同类型 / parser_name 不同值 / 各 key 类型）
- build_devset_section 行为深度第九批（不同 manifest 实现 / categories 不同类型 / count 类型）
- aggregate_summary 行为深度第九批（mixed participation / counts 与 success_rates 隔离 / 不混合综合分 / silent_drop 多种形式 / JSON 可序列化）
- module source forbidden tokens 第十二批
- module source 字符串精确补强第九批
- signatures 第九批
- module 合理性第九批
- 端到端集成第九批
"""

from __future__ import annotations

import inspect
import json
import subprocess
import types
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

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


# ---------- get_git_provenance 行为深度第九批 ----------


def test_get_git_provenance_handles_subprocess_timeout_in_rev_parse():
    """第一次 rev-parse 调用就 timeout → except 命中。"""
    call_count = [0]

    def _boom(*args, **kwargs):
        call_count[0] += 1
        raise subprocess.TimeoutExpired(cmd=args[0] if args else "x", timeout=10)

    with patch("subprocess.run", side_effect=_boom):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_handles_subprocess_timeout_in_porcelain():
    """rev-parse 成功，porcelain 失败 → except 命中。"""
    fake_ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc1234\n", stderr="")
    call_count = [0]

    def _conditional(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return fake_ok
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=10)

    with patch("subprocess.run", side_effect=_conditional):
        out = get_git_provenance(Path("."))
    # 第一次成功，第二次抛 → 整体 except → commit None
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_returns_dict_with_two_keys():
    out = get_git_provenance(Path("."))
    assert len(out) == 2


def test_get_git_provenance_keys_exact():
    out = get_git_provenance(Path("."))
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_value_git_commit_str_or_none():
    out = get_git_provenance(Path("."))
    assert out["git_commit"] is None or isinstance(out["git_commit"], str)


def test_get_git_provenance_value_git_dirty_bool():
    out = get_git_provenance(Path("."))
    assert isinstance(out["git_dirty"], bool)


def test_get_git_provenance_real_call_in_project():
    """在 autonomous worktree 真实调用，commit 应为 40 char SHA-1 或 None。"""
    out = get_git_provenance(Path(__file__).parent.parent)
    if out["git_commit"] is not None:
        assert len(out["git_commit"]) == 40


def test_get_git_provenance_does_not_raise_on_any_input():
    """各种输入都不抛。"""
    get_git_provenance(Path("."))
    get_git_provenance(Path("/nonexistent_xyz_123"))
    get_git_provenance(None)  # type: ignore[arg-type]


# ---------- get_dependency_versions 行为深度第九批 ----------


def test_get_dependency_versions_only_pdfplumber_fails():
    """patch 让 pdfplumber 失败，其他两个正常。"""
    import importlib.metadata

    real_version = importlib.metadata.version

    def _fake(name):
        if name == "pdfplumber":
            raise importlib.metadata.PackageNotFoundError(name)
        return real_version(name)

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    assert out["pdfplumber"] is None
    # 其他两个应仍能取到（或 None，视环境）


def test_get_dependency_versions_only_pypdfium2_fails():
    import importlib.metadata

    real_version = importlib.metadata.version

    def _fake(name):
        if name == "pypdfium2":
            raise RuntimeError("boom")
        return real_version(name)

    with patch("importlib.metadata.version", side_effect=_fake):
        out = get_dependency_versions()
    assert out["pypdfium2"] is None


def test_get_dependency_versions_dict_does_not_share_state():
    """两次调用不共享内部 dict。"""
    out1 = get_dependency_versions()
    out2 = get_dependency_versions()
    out1["new_key"] = "x"
    assert "new_key" not in out2


def test_get_dependency_versions_call_does_not_raise():
    """调用不抛。"""
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_get_dependency_versions_independent_of_path():
    """与 path 参数无关。"""
    out1 = get_dependency_versions()
    out2 = get_dependency_versions()
    assert out1 == out2


# ---------- build_provenance 行为深度第九批 ----------


def test_build_provenance_with_path_str_project_root():
    """project_root 接 str。"""
    out = build_provenance(".", parser_name="fallback", max_chars=800, parser_version=None)
    assert isinstance(out, dict)


def test_build_provenance_max_chars_zero():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=0, parser_version=None)
    assert out["max_chars"] == 0


def test_build_provenance_max_chars_negative():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=-100, parser_version=None)
    assert out["max_chars"] == -100


def test_build_provenance_max_chars_huge():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=10**9, parser_version=None)
    assert out["max_chars"] == 10**9


def test_build_provenance_parser_version_zero_string():
    out = build_provenance(
        Path("."), parser_name="fallback", max_chars=800, parser_version="0.0.0"
    )
    assert out["parser_version"] == "0.0.0"


def test_build_provenance_parser_version_empty_string():
    out = build_provenance(
        Path("."), parser_name="fallback", max_chars=800, parser_version=""
    )
    assert out["parser_version"] == ""


def test_build_provenance_parser_name_kreuzberg():
    out = build_provenance(
        Path("."), parser_name="kreuzberg", max_chars=800, parser_version=None
    )
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_dependencies_value_is_dict():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_dependencies_3_keys():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert len(out["dependencies"]) == 3


def test_build_provenance_run_timestamp_valid_iso():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    ts = out["run_timestamp_iso"]
    # datetime.fromisoformat 能解析
    parsed = datetime.fromisoformat(ts)
    assert parsed is not None


def test_build_provenance_evaluator_version_value():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_dict_serializable():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


# ---------- build_devset_section 行为深度第九批 ----------


class _StubManifest:
    devset_status = "incomplete"
    file_count = 5
    content_group_count = 3
    pdf_count = 2
    docx_count = 3
    categories_covered = ["normal", "edge", "extreme"]


def test_build_devset_section_with_categories_list():
    out = build_devset_section(_StubManifest())
    assert isinstance(out["categories_covered"], list)


def test_build_devset_section_status_string():
    out = build_devset_section(_StubManifest())
    assert isinstance(out["status"], str)


def test_build_devset_section_file_count_int():
    out = build_devset_section(_StubManifest())
    assert isinstance(out["file_count"], int)


def test_build_devset_section_value_propagation():
    class _M:
        devset_status = "complete"
        file_count = 1
        content_group_count = 1
        pdf_count = 0
        docx_count = 1
        categories_covered = []

    out = build_devset_section(_M())
    assert out["status"] == "complete"
    assert out["docx_count"] == 1


def test_build_devset_section_with_empty_categories():
    class _M:
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []

    out = build_devset_section(_M())
    assert out["categories_covered"] == []


def test_build_devset_section_idempotent():
    out1 = build_devset_section(_StubManifest())
    out2 = build_devset_section(_StubManifest())
    assert out1 == out2


def test_build_devset_section_does_not_mutate_manifest():
    m = _StubManifest()
    snapshot_categories = list(m.categories_covered)
    _ = build_devset_section(m)
    assert m.categories_covered == snapshot_categories


def test_build_devset_section_returns_dict():
    out = build_devset_section(_StubManifest())
    assert isinstance(out, dict)


def test_build_devset_section_json_serializable():
    out = build_devset_section(_StubManifest())
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


# ---------- aggregate_summary 行为深度第九批 ----------


def _metrics_doc(metrics: dict) -> dict:
    return {"metrics": metrics}


def test_aggregate_summary_does_not_mix_types():
    """顶层 keys 是分类的，不混合。"""
    docs = [_metrics_doc({"schema_valid": {"value": 1.0}})]
    out = aggregate_summary(docs)
    assert "counts" in out
    assert "success_rates" in out
    assert "ratio_macro_averages" in out
    assert "silent_drop_total" in out


def test_aggregate_summary_counts_isolated_from_success_rates():
    """element_count_total 不影响 success_rates。"""
    docs = [
        _metrics_doc({"element_count_total": {"value": 100}, "pipeline_success": {"value": False}}),
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 100
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0


def test_aggregate_summary_success_rates_total_always_len_per_doc_results():
    """success_rates.total = len(per_doc_results)（即使缺 pipeline_success）。"""
    docs = [
        _metrics_doc({}),
        _metrics_doc({"pipeline_success": {"value": True}}),
        _metrics_doc({"pipeline_success": {"value": False}}),
    ]
    out = aggregate_summary(docs)
    assert out["success_rates"]["pipeline_success"]["total"] == 3
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1


def test_aggregate_summary_silent_drop_total_int_when_present():
    docs = [
        _metrics_doc({"silent_drop_count": {"value": 3}}),
        _metrics_doc({"silent_drop_count": {"value": 7}}),
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 10


def test_aggregate_summary_silent_drop_total_is_int():
    docs = [_metrics_doc({"silent_drop_count": {"value": 5}})]
    out = aggregate_summary(docs)
    assert isinstance(out["silent_drop_total"], int)


def test_aggregate_summary_silent_drop_total_none_when_empty():
    docs = []
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_json_serializable():
    docs = [
        _metrics_doc({"schema_valid": {"value": 1.0}, "pipeline_success": {"value": True}}),
    ]
    out = aggregate_summary(docs)
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


def test_aggregate_summary_input_not_mutated_complex():
    docs = [
        _metrics_doc({"schema_valid": {"value": 1.0}}),
        _metrics_doc({"pipeline_success": {"value": True}}),
        _metrics_doc({"silent_drop_count": {"value": 5}}),
    ]
    snapshot = json.dumps(docs, default=str)
    _ = aggregate_summary(docs)
    assert json.dumps(docs, default=str) == snapshot


def test_aggregate_summary_chunk_boundary_with_some_skipped():
    docs = [
        _metrics_doc({"chunk_boundary_f1": {"value": 0.5}}),
        _metrics_doc({"chunk_boundary_f1": {"value": None}}),
        _metrics_doc({"chunk_boundary_f1": {"value": 1.0}}),
        _metrics_doc({"chunk_boundary_f1": {"value": 0.0}}),
    ]
    out = aggregate_summary(docs)
    macro = out["ratio_macro_averages"]["chunk_boundary_f1"]
    assert macro["participating_docs"] == 3
    assert macro["not_evaluated"] == 1
    assert macro["macro_average"] == pytest.approx(0.5)


def test_aggregate_summary_figure_caption_excluded_from_macro_average():
    """figure_caption_* 不在 _RATIO_METRICS，不参与 macro_average。"""
    docs = [_metrics_doc({"figure_caption_f1": {"value": 0.9}})]
    out = aggregate_summary(docs)
    assert "figure_caption_f1" not in out["ratio_macro_averages"]


def test_aggregate_summary_chunk_reference_intact_participates():
    docs = [
        _metrics_doc({"chunk_reference_intact_ratio": {"value": 0.8}}),
        _metrics_doc({"chunk_reference_intact_ratio": {"value": 1.0}}),
    ]
    out = aggregate_summary(docs)
    macro = out["ratio_macro_averages"]["chunk_reference_intact_ratio"]
    assert macro["macro_average"] == pytest.approx(0.9)


def test_aggregate_summary_schema_valid_participates():
    docs = [
        _metrics_doc({"schema_valid": {"value": 1}}),
        _metrics_doc({"schema_valid": {"value": 0}}),
    ]
    out = aggregate_summary(docs)
    macro = out["ratio_macro_averages"]["schema_valid"]
    assert macro["macro_average"] == pytest.approx(0.5)


def test_aggregate_summary_no_overall_score_field():
    docs = [_metrics_doc({"schema_valid": {"value": 1.0}})]
    out = aggregate_summary(docs)
    for forbidden in ("overall_score", "total_score", "combined_score", "final_score"):
        assert forbidden not in out


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 常量精确补强 ----------


def test_ratio_metrics_exact_count_12():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_exact_count_one():
    assert len(_COUNT_METRICS) == 1


def test_ratio_metrics_exact_success_bool_one():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_count_metrics_value():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_value():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_constants_mutually_exclusive():
    all_metrics = list(_RATIO_METRICS) + list(_COUNT_METRICS) + list(_SUCCESS_BOOL_METRICS)
    assert len(all_metrics) == len(set(all_metrics))


def test_constants_total_14():
    assert len(_RATIO_METRICS) + len(_COUNT_METRICS) + len(_SUCCESS_BOOL_METRICS) == 14


def test_ratio_metrics_all_strings():
    for name in _RATIO_METRICS:
        assert isinstance(name, str)


def test_count_metrics_all_strings():
    for name in _COUNT_METRICS:
        assert isinstance(name, str)


def test_success_bool_metrics_all_strings():
    for name in _SUCCESS_BOOL_METRICS:
        assert isinstance(name, str)


# ---------- module source forbidden tokens 第十二批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "pickle.loads",
        "yaml.load",
        "yaml.unsafe_load",
        "subprocess.check_call",
        "subprocess.call",
        "subprocess.getoutput",
        "os.popen",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
    ],
)
def test_report_source_no_forbidden_token_twelfth(token):
    source = inspect.getsource(rmod)
    assert token not in source


def test_report_source_no_unlink():
    source = inspect.getsource(rmod)
    assert "unlink" not in source


def test_report_source_no_remove():
    source = inspect.getsource(rmod)
    assert ".remove(" not in source


def test_report_source_no_kill():
    source = inspect.getsource(rmod)
    assert ".kill(" not in source


def test_report_source_no_terminate():
    source = inspect.getsource(rmod)
    assert ".terminate(" not in source


def test_report_source_no_async_def():
    source = inspect.getsource(rmod)
    assert "async def" not in source


def test_report_source_no_yield():
    source = inspect.getsource(rmod)
    assert "yield" not in source


def test_report_source_no_walrus():
    source = inspect.getsource(rmod)
    assert ":=" not in source


def test_report_source_no_top_level_lambda():
    source = inspect.getsource(rmod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_report_source_no_print():
    source = inspect.getsource(rmod)
    assert "print(" not in source


def test_report_source_no_logging():
    source = inspect.getsource(rmod)
    assert "logging" not in source
    assert "logger" not in source


# ---------- module source 字符串精确补强第九批 ----------


def test_module_source_has_future_annotations():
    source = inspect.getsource(rmod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_subprocess():
    source = inspect.getsource(rmod)
    assert "import subprocess" in source


def test_module_source_imports_datetime():
    source = inspect.getsource(rmod)
    assert "from datetime import datetime" in source


def test_module_source_imports_path():
    source = inspect.getsource(rmod)
    assert "from pathlib import Path" in source


def test_module_source_imports_typing_any():
    source = inspect.getsource(rmod)
    assert "from typing import Any" in source


def test_module_source_imports_evaluator_version():
    source = inspect.getsource(rmod)
    assert "EVALUATOR_VERSION" in source


def test_module_source_imports_report_version():
    source = inspect.getsource(rmod)
    assert "REPORT_VERSION" in source


def test_module_source_has_get_git_provenance_def():
    source = inspect.getsource(rmod)
    assert "def get_git_provenance(" in source


def test_module_source_has_get_dependency_versions_def():
    source = inspect.getsource(rmod)
    assert "def get_dependency_versions(" in source


def test_module_source_has_build_provenance_def():
    source = inspect.getsource(rmod)
    assert "def build_provenance(" in source


def test_module_source_has_build_devset_section_def():
    source = inspect.getsource(rmod)
    assert "def build_devset_section(" in source


def test_module_source_has_aggregate_summary_def():
    source = inspect.getsource(rmod)
    assert "def aggregate_summary(" in source


def test_module_source_has_subprocess_run_call():
    source = inspect.getsource(rmod)
    assert "subprocess.run(" in source


def test_module_source_rev_parse_command():
    source = inspect.getsource(rmod)
    assert "rev-parse" in source
    assert "HEAD" in source


def test_module_source_status_porcelain_command():
    source = inspect.getsource(rmod)
    assert "status" in source
    assert "--porcelain" in source


def test_module_source_capture_output_true():
    source = inspect.getsource(rmod)
    assert "capture_output=True" in source


def test_module_source_encoding_utf8():
    source = inspect.getsource(rmod)
    assert 'encoding="utf-8"' in source


def test_module_source_errors_replace():
    source = inspect.getsource(rmod)
    assert 'errors="replace"' in source


def test_module_source_timeout_10():
    source = inspect.getsource(rmod)
    assert "timeout=10" in source


def test_module_source_try_except_oserror_subprocess_error():
    source = inspect.getsource(rmod)
    assert "except" in source
    assert "OSError" in source
    assert "SubprocessError" in source


def test_module_source_three_pkg_tuple():
    source = inspect.getsource(rmod)
    assert '"pdfplumber"' in source
    assert '"python-docx"' in source
    assert '"pypdfium2"' in source


def test_module_source_no_main_block():
    source = inspect.getsource(rmod)
    assert "if __name__" not in source


def test_module_source_docstring_present():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 30


def test_module_source_docstring_mentions_macro():
    assert "macro" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_silent():
    assert "silent" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_counts():
    assert "counts" in rmod.__doc__.lower()


def test_module_source_docstring_no_mix_word():
    """docstring 提到不混合。"""
    assert "不混合" in rmod.__doc__


# ---------- signatures 第九批 ----------


def test_signature_get_git_provenance_1_param():
    sig = inspect.signature(get_git_provenance)
    assert len(sig.parameters) == 1


def test_signature_get_git_provenance_param_name():
    sig = inspect.signature(get_git_provenance)
    assert "project_root" in sig.parameters


def test_signature_get_git_provenance_param_kind():
    sig = inspect.signature(get_git_provenance)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_get_git_provenance_no_default():
    sig = inspect.signature(get_git_provenance)
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_signature_get_dependency_versions_no_params():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_signature_build_provenance_4_params():
    sig = inspect.signature(build_provenance)
    assert len(sig.parameters) == 4


def test_signature_build_provenance_param_names():
    sig = inspect.signature(build_provenance)
    assert list(sig.parameters) == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_signature_build_provenance_param_kinds():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_build_provenance_no_defaults():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_build_devset_section_1_param():
    sig = inspect.signature(build_devset_section)
    assert len(sig.parameters) == 1


def test_signature_build_devset_section_param_name_manifest():
    sig = inspect.signature(build_devset_section)
    assert "manifest" in sig.parameters


def test_signature_aggregate_summary_1_param():
    sig = inspect.signature(aggregate_summary)
    assert len(sig.parameters) == 1


def test_signature_aggregate_summary_param_name_per_doc_results():
    sig = inspect.signature(aggregate_summary)
    assert "per_doc_results" in sig.parameters


def test_signature_funcs_function_type():
    for func in (
        get_git_provenance,
        get_dependency_versions,
        build_provenance,
        build_devset_section,
        aggregate_summary,
    ):
        assert inspect.isfunction(func)


def test_signature_funcs_module_eq():
    for func in (
        get_git_provenance,
        get_dependency_versions,
        build_provenance,
        build_devset_section,
        aggregate_summary,
    ):
        assert func.__module__ == "evaluation.report"


# ---------- module 合理性第九批 ----------


def test_module_all_value():
    assert rmod.__all__ == [
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    ]


def test_module_all_is_list():
    assert isinstance(rmod.__all__, list)


def test_module_all_entries_unique():
    assert len(rmod.__all__) == len(set(rmod.__all__))


def test_module_all_entries_str():
    for name in rmod.__all__:
        assert isinstance(name, str)


def test_module_has_dunder_file():
    assert hasattr(rmod, "__file__")


def test_module_dunder_file_endswith_report_py():
    import os
    sep = os.sep
    assert rmod.__file__.endswith("evaluation" + sep + "report.py") or rmod.__file__.endswith(
        "evaluation/report.py"
    )


def test_module_name_is_evaluation_report():
    assert rmod.__name__ == "evaluation.report"


def test_module_user_function_count():
    funcs = [
        n for n, v in vars(rmod).items()
        if inspect.isfunction(v) and v.__module__ == rmod.__name__
    ]
    assert set(funcs) == {
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    }


def test_module_user_constant_count():
    consts = [
        n for n, v in vars(rmod).items()
        if not n.startswith("__") and isinstance(v, tuple) and not callable(v)
    ]
    assert set(consts) == {"_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"}


def test_module_no_user_classes():
    classes = [
        n for n, v in vars(rmod).items()
        if inspect.isclass(v) and v.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_has_evaluator_version_attribute():
    assert hasattr(rmod, "EVALUATOR_VERSION")


def test_module_has_report_version_attribute():
    assert hasattr(rmod, "REPORT_VERSION")


def test_module_docstring_present():
    assert rmod.__doc__ is not None


# ---------- 端到端集成第九批 ----------


def test_e2e_full_chain_minimal_input():
    prov = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    out = aggregate_summary([])
    report = {
        "provenance": prov,
        "devset": build_devset_section(_StubManifest()),
        "summary": out,
        "per_doc": [],
    }
    text = json.dumps(report)
    parsed = json.loads(text)
    assert parsed == report


def test_e2e_full_chain_json_serializable():
    docs = [
        _metrics_doc(
            {
                "schema_valid": {"value": 1.0},
                "pipeline_success": {"value": True},
                "element_count_total": {"value": 5},
                "silent_drop_count": {"value": 2},
                "chunk_boundary_f1": {"value": 0.7},
            }
        )
    ]
    summary = aggregate_summary(docs)
    text = json.dumps(summary)
    parsed = json.loads(text)
    assert parsed == summary


def test_e2e_aggregate_summary_kwargs_call():
    docs = [_metrics_doc({"schema_valid": {"value": 1.0}})]
    out1 = aggregate_summary(docs)
    out2 = aggregate_summary(per_doc_results=docs)
    assert out1 == out2


def test_e2e_build_devset_section_round_trip():
    out = build_devset_section(_StubManifest())
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


def test_e2e_build_provenance_does_not_raise_on_real_call():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=800, parser_version=None)
    assert isinstance(out, dict)


def test_e2e_aggregate_summary_zero_participation_returns_none_macro():
    """所有 docs 都缺该 metric → macro_average=None。"""
    docs = [_metrics_doc({}) for _ in range(3)]
    out = aggregate_summary(docs)
    for name in _RATIO_METRICS:
        macro = out["ratio_macro_averages"][name]
        assert macro["macro_average"] is None
        assert macro["participating_docs"] == 0
        assert macro["not_evaluated"] == 3


def test_e2e_aggregate_summary_consistent_structure():
    """summary 结构 keys 一致。"""
    out1 = aggregate_summary([])
    out2 = aggregate_summary([_metrics_doc({"schema_valid": {"value": 1.0}})])
    assert list(out1.keys()) == list(out2.keys())


def test_e2e_build_provenance_with_negative_max_chars():
    out = build_provenance(Path("."), parser_name="fallback", max_chars=-800, parser_version=None)
    assert out["max_chars"] == -800


def test_e2e_combined_call_chain_idempotent():
    """全链重复调用结构稳定。"""
    out1_summary = aggregate_summary([])
    out2_summary = aggregate_summary([])
    assert out1_summary == out2_summary

    out1_devset = build_devset_section(_StubManifest())
    out2_devset = build_devset_section(_StubManifest())
    assert out1_devset == out2_devset
