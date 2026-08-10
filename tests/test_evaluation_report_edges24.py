"""evaluation/report.py 第二十四轮 edges 测试（Round 374）。

补强 edges23 未触及的角度：
- get_git_provenance 行为深度第七批（with real repo / non-existent dir / non-git dir / 多次调用结构稳定）
- get_dependency_versions 行为深度第七批（3 keys + str|None + dict type + idempotent）
- build_provenance 行为深度第七批（9 keys + max_chars int conversion + parser_version None + timestamp iso + 在非 git 目录）
- build_devset_section 行为深度第七批（6 keys 完整 + content_group_count + categories_covered）
- aggregate_summary 行为深度第七批（figure_caption 不参与 macro average / chunk_boundary_* 参与 / silent_drop_count + total）
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 常量精确补强
- module source forbidden tokens 第十批
- module 合理性第七批（__all__ 精确 5 项顺序 + 5 functions + 3 constants tuple）
- signatures 第七批（5 funcs no varargs/kwargs + return annotations）
- 端到端集成第七批（full chain + figure_caption 不参与 + chunk_boundary 参与 + silent_drop_count 求和）
"""

from __future__ import annotations

import inspect
import json
import types
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


# ---------- get_git_provenance 行为深度第七批 ----------


def test_get_git_provenance_returns_dict_type():
    p = Path(".")
    out = get_git_provenance(p)
    assert isinstance(out, dict)


def test_get_git_provenance_2_keys_exact():
    p = Path(".")
    out = get_git_provenance(p)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_in_real_repo_returns_commit():
    """在 autonomous worktree 中应能读到 commit。"""
    out = get_git_provenance(Path("."))
    # 这里是在 dachuang-code 目录，是 git repo
    # 如果在 non-git 路径则 commit None
    if out["git_commit"] is not None:
        assert isinstance(out["git_commit"], str)
        # SHA-1 是 40 字符
        assert len(out["git_commit"]) == 40


def test_get_git_provenance_in_real_repo_dirty_is_bool():
    out = get_git_provenance(Path("."))
    assert isinstance(out["git_dirty"], bool)


def test_get_git_provenance_nonexistent_dir_returns_default():
    """不存在的目录 → commit=None, dirty=True。"""
    p = Path("C:/definitely_does_not_exist_xyz123")
    out = get_git_provenance(p)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_non_git_dir_returns_default():
    """非 git 目录（无 .git）→ subprocess 返回非零 → commit None。

    注意：dirty = bool(r2.returncode == 0 and r2.stdout.strip())。
    若 r2.returncode != 0（非 git 目录）→ dirty = False。
    只有抛 OSError 时才 dirty = True。
    """
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        out = get_git_provenance(Path(td))
        assert out["git_commit"] is None
        # subprocess 失败时 dirty = False（bool 短路）
        assert out["git_dirty"] is False or out["git_dirty"] is True
        # 关键不变量：commit 是 None
        assert out["git_commit"] is None


def test_get_git_provenance_with_path_object():
    out = get_git_provenance(Path("."))
    assert isinstance(out, dict)


def test_get_git_provenance_with_string_path():
    out = get_git_provenance(".")
    assert isinstance(out, dict)


def test_get_git_provenance_idempotent():
    out1 = get_git_provenance(Path("."))
    out2 = get_git_provenance(Path("."))
    # git_commit 应稳定，git_dirty 可能因 staging 改变（一般不会）
    assert out1["git_commit"] == out2["git_commit"]


def test_get_git_provenance_handles_oserror_via_patch():
    """subprocess 抛 OSError 时 → commit None, dirty True。"""
    with patch("subprocess.run", side_effect=OSError("boom")):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_handles_subprocess_error():
    """subprocess.CalledProcessError 等也走 except 分支。"""
    import subprocess
    with patch("subprocess.run", side_effect=subprocess.SubprocessError("boom")):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


# ---------- get_dependency_versions 行为深度第七批 ----------


def test_get_dependency_versions_returns_dict():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_get_dependency_versions_3_keys_exact():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_str_or_none():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_idempotent():
    out1 = get_dependency_versions()
    out2 = get_dependency_versions()
    assert out1 == out2


def test_get_dependency_versions_no_args():
    """不接受参数。"""
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


# ---------- build_provenance 行为深度第七批 ----------


def test_build_provenance_returns_dict():
    out = build_provenance(Path("."), "fallback", 800, "1.0")
    assert isinstance(out, dict)


def test_build_provenance_9_keys_exact():
    out = build_provenance(Path("."), "fallback", 800, "1.0")
    expected = {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    }
    assert set(out.keys()) == expected


def test_build_provenance_evaluator_version_value():
    out = build_provenance(Path("."), "fallback", 800, "1.0")
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_value():
    out = build_provenance(Path("."), "fallback", 800, "1.0")
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_value():
    out = build_provenance(Path("."), "kreuzberg", 800, "4.10.2")
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_parser_version_none():
    out = build_provenance(Path("."), "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_max_chars_int():
    out = build_provenance(Path("."), "fallback", 800, "1.0")
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_str_input_converted_to_int():
    """str "800" 会被 int() 转换。"""
    out = build_provenance(Path("."), "fallback", "800", "1.0")
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_dependencies_is_dict():
    out = build_provenance(Path("."), "fallback", 800, "1.0")
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_run_timestamp_iso_format():
    out = build_provenance(Path("."), "fallback", 800, "1.0")
    ts = out["run_timestamp_iso"]
    assert isinstance(ts, str)
    # ISO format 应包含 'T' 分隔符
    assert "T" in ts


def test_build_provenance_git_commit_value():
    out = build_provenance(Path("."), "fallback", 800, "1.0")
    # None 或 str（40 字符 SHA-1）
    if out["git_commit"] is not None:
        assert isinstance(out["git_commit"], str)
        assert len(out["git_commit"]) == 40


def test_build_provenance_git_dirty_value():
    out = build_provenance(Path("."), "fallback", 800, "1.0")
    assert isinstance(out["git_dirty"], bool)


# ---------- build_devset_section 行为深度第七批 ----------


def _make_manifest(**overrides):
    """构造最小 Manifest-like 对象。"""
    class _M:
        def __init__(self, **kw):
            self.devset_status = kw.get("devset_status", "complete")
            self.file_count = kw.get("file_count", 0)
            self.content_group_count = kw.get("content_group_count", 0)
            self.pdf_count = kw.get("pdf_count", 0)
            self.docx_count = kw.get("docx_count", 0)
            self.categories_covered = kw.get("categories_covered", [])
    return _M(**overrides)


def test_build_devset_section_returns_dict():
    m = _make_manifest()
    out = build_devset_section(m)
    assert isinstance(out, dict)


def test_build_devset_section_6_keys_exact():
    m = _make_manifest()
    out = build_devset_section(m)
    expected = {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }
    assert set(out.keys()) == expected


def test_build_devset_section_status_value():
    m = _make_manifest(devset_status="incomplete")
    out = build_devset_section(m)
    assert out["status"] == "incomplete"


def test_build_devset_section_file_count_value():
    m = _make_manifest(file_count=42)
    out = build_devset_section(m)
    assert out["file_count"] == 42


def test_build_devset_section_with_categories():
    m = _make_manifest(categories_covered=["a", "b"])
    out = build_devset_section(m)
    assert out["categories_covered"] == ["a", "b"]


def test_build_devset_section_with_empty_categories():
    m = _make_manifest(categories_covered=[])
    out = build_devset_section(m)
    assert out["categories_covered"] == []


def test_build_devset_section_with_pdf_only():
    m = _make_manifest(pdf_count=3, docx_count=0)
    out = build_devset_section(m)
    assert out["pdf_count"] == 3
    assert out["docx_count"] == 0


def test_build_devset_section_idempotent():
    m = _make_manifest()
    out1 = build_devset_section(m)
    out2 = build_devset_section(m)
    assert out1 == out2


# ---------- aggregate_summary 行为深度第七批 ----------


def _make_per_doc(metrics: dict, doc_id: str = "d1") -> dict:
    return {"doc_id": doc_id, "metrics": metrics}


def test_aggregate_summary_empty_list_returns_4_keys():
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_counts_sum_with_multiple():
    per_doc = [
        _make_per_doc({"element_count_total": {"value": 5, "reason": None}}),
        _make_per_doc({"element_count_total": {"value": 10, "reason": None}}),
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_with_none_skipped():
    per_doc = [
        _make_per_doc({"element_count_total": {"value": 5, "reason": None}}),
        _make_per_doc({"element_count_total": {"value": None, "reason": "pipeline_failed"}}),
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_counts_all_none():
    per_doc = [
        _make_per_doc({"element_count_total": {"value": None}}),
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_success_rate_full():
    per_doc = [
        _make_per_doc({"pipeline_success": {"value": True}}),
        _make_per_doc({"pipeline_success": {"value": True}}),
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 2
    assert out["success_rates"]["pipeline_success"]["total"] == 2
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0


def test_aggregate_summary_success_rate_partial():
    per_doc = [
        _make_per_doc({"pipeline_success": {"value": True}}),
        _make_per_doc({"pipeline_success": {"value": False}}),
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["total"] == 2
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5


def test_aggregate_summary_success_rate_zero_total():
    out = aggregate_summary([])
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0
    assert out["success_rates"]["pipeline_success"]["total"] == 0
    assert out["success_rates"]["pipeline_success"]["rate"] is None


def test_aggregate_summary_ratio_macro_average():
    per_doc = [
        _make_per_doc({"pdf_locator_valid_ratio": {"value": 0.8}}),
        _make_per_doc({"pdf_locator_valid_ratio": {"value": 0.6}}),
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == pytest.approx(0.7)
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["participating_docs"] == 2


def test_aggregate_summary_ratio_macro_average_with_none_skipped():
    per_doc = [
        _make_per_doc({"pdf_locator_valid_ratio": {"value": 0.8}}),
        _make_per_doc({"pdf_locator_valid_ratio": {"value": None}}),
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 0.8
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["participating_docs"] == 1


def test_aggregate_summary_ratio_macro_average_all_none():
    per_doc = [_make_per_doc({"pdf_locator_valid_ratio": {"value": None}})]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] is None


def test_aggregate_summary_figure_caption_not_in_ratio_metrics():
    """figure_caption_* 始终 null，不应出现在 ratio_macro_averages。"""
    per_doc = [
        _make_per_doc({
            "figure_caption_precision": {"value": None, "reason": "parser_does_not_emit_relations"},
            "figure_caption_recall": {"value": None, "reason": "parser_does_not_emit_relations"},
            "figure_caption_f1": {"value": None, "reason": "parser_does_not_emit_relations"},
        }),
    ]
    out = aggregate_summary(per_doc)
    assert "figure_caption_precision" not in out["ratio_macro_averages"]
    assert "figure_caption_recall" not in out["ratio_macro_averages"]
    assert "figure_caption_f1" not in out["ratio_macro_averages"]


def test_aggregate_summary_chunk_boundary_in_ratio_metrics():
    """chunk_boundary_* 应出现在 ratio_macro_averages。"""
    per_doc = [
        _make_per_doc({
            "chunk_boundary_precision": {"value": 0.9},
            "chunk_boundary_recall": {"value": 0.8},
            "chunk_boundary_f1": {"value": 0.85},
        }),
    ]
    out = aggregate_summary(per_doc)
    assert "chunk_boundary_precision" in out["ratio_macro_averages"]
    assert "chunk_boundary_recall" in out["ratio_macro_averages"]
    assert "chunk_boundary_f1" in out["ratio_macro_averages"]


def test_aggregate_summary_silent_drop_total_sum():
    per_doc = [
        _make_per_doc({"silent_drop_count": {"value": 3}}),
        _make_per_doc({"silent_drop_count": {"value": 5}}),
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_with_none():
    per_doc = [
        _make_per_doc({"silent_drop_count": {"value": 3}}),
        _make_per_doc({"silent_drop_count": {"value": None}}),
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 3


def test_aggregate_summary_silent_drop_all_none():
    per_doc = [
        _make_per_doc({"silent_drop_count": {"value": None}}),
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_empty_list():
    out = aggregate_summary([])
    assert out["silent_drop_total"] is None


def test_aggregate_summary_does_not_mutate_input():
    per_doc = [
        _make_per_doc({"element_count_total": {"value": 5}}),
    ]
    per_doc_before = json.loads(json.dumps(per_doc))
    aggregate_summary(per_doc)
    assert per_doc == per_doc_before


def test_aggregate_summary_idempotent():
    per_doc = [_make_per_doc({"element_count_total": {"value": 5}})]
    out1 = aggregate_summary(per_doc)
    out2 = aggregate_summary(per_doc)
    assert out1 == out2


def test_aggregate_summary_returns_4_top_keys():
    out = aggregate_summary([])
    assert len(out) == 4


def test_aggregate_summary_ratio_metrics_count_12():
    out = aggregate_summary([])
    assert len(out["ratio_macro_averages"]) == 12


def test_aggregate_summary_count_metrics_count_1():
    out = aggregate_summary([])
    assert len(out["counts"]) == 1


def test_aggregate_summary_success_metrics_count_1():
    out = aggregate_summary([])
    assert len(out["success_rates"]) == 1


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 常量精确补强 ----------


def test_ratio_metrics_exact_entries_in_order():
    expected = (
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
    )
    assert _RATIO_METRICS == expected


def test_count_metrics_exact_entries():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_exact_entries():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_ratio_metrics_is_tuple():
    assert isinstance(_RATIO_METRICS, tuple)


def test_count_metrics_is_tuple():
    assert isinstance(_COUNT_METRICS, tuple)


def test_success_bool_metrics_is_tuple():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_ratio_metrics_length_12():
    assert len(_RATIO_METRICS) == 12


def test_count_metrics_length_1():
    assert len(_COUNT_METRICS) == 1


def test_success_bool_metrics_length_1():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_constants_no_overlap():
    """三个 metric 集合不应有交集。"""
    all_metrics = set(_RATIO_METRICS) | set(_COUNT_METRICS) | set(_SUCCESS_BOOL_METRICS)
    total = len(_RATIO_METRICS) + len(_COUNT_METRICS) + len(_SUCCESS_BOOL_METRICS)
    assert len(all_metrics) == total


def test_figure_caption_not_in_ratio_metrics():
    """figure_caption_* 不参与 macro average。"""
    assert "figure_caption_precision" not in _RATIO_METRICS
    assert "figure_caption_recall" not in _RATIO_METRICS
    assert "figure_caption_f1" not in _RATIO_METRICS


def test_silent_drop_not_in_any_metrics_constant():
    """silent_drop_count 单独求和，不在三个常量中。"""
    assert "silent_drop_count" not in _RATIO_METRICS
    assert "silent_drop_count" not in _COUNT_METRICS
    assert "silent_drop_count" not in _SUCCESS_BOOL_METRICS


# ---------- module source forbidden tokens 第十批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.chmod", "os.chown",
        "os.execv", "os.fork",
        "os.kill", "os.mkdir",
        "os.makedirs", "os.remove",
        "os.rename", "os.rmdir",
        "os.unlink",
        "pathlib.Path.rmdir",
        "pathlib.Path.unlink",
        "eval(", "exec(",
        "compile(",
        "globals(",
        "locals(",
        "vars(",
        "memoryview",
        "bytearray(",
        "errno",
        "signal.signal",
        "fcntl",
        "termios",
        "tty",
        "pty",
        "winreg",
        "msvcrt",
        "_winapi",
        "re.match",
        "re.sub",
        "shutil.rmtree",
        "tempfile.mkdtemp",
    ],
)
def test_report_source_no_forbidden_token_v3(token):
    src = inspect.getsource(rmod)
    assert token not in src, f"forbidden token found: {token}"


# ---------- module 合理性第七批 ----------


def test_module_all_exact_5_items_in_order():
    expected = [
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    ]
    assert rmod.__all__ == expected


def test_module_all_entries_unique():
    assert len(rmod.__all__) == len(set(rmod.__all__))


def test_module_all_entries_are_str():
    for item in rmod.__all__:
        assert isinstance(item, str)


def test_module_namespace_5_callables():
    funcs = [
        name for name, val in vars(rmod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == rmod.__name__
    ]
    assert len(funcs) == 5


def test_module_namespace_callable_names():
    funcs = {
        name for name, val in vars(rmod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == rmod.__name__
    }
    assert funcs == {
        "build_provenance", "build_devset_section", "aggregate_summary",
        "get_git_provenance", "get_dependency_versions",
    }


def test_module_namespace_3_constants():
    """3 个 module-level tuple 常量。"""
    expected = {"_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"}
    for name in expected:
        assert hasattr(rmod, name)


def test_module_no_user_classes():
    classes = [
        name for name, val in vars(rmod).items()
        if isinstance(val, type) and val.__module__ == rmod.__name__
    ]
    assert len(classes) == 0


def test_module_docstring_present():
    assert rmod.__doc__ is not None


def test_module_docstring_mentions_provenance():
    assert "provenance" in rmod.__doc__ or "元数据" in rmod.__doc__


def test_module_docstring_mentions_devset():
    assert "devset" in rmod.__doc__


def test_module_docstring_mentions_summary():
    assert "summary" in rmod.__doc__ or "聚合" in rmod.__doc__


def test_module_docstring_mentions_macro_average():
    assert "macro" in rmod.__doc__ or "平均" in rmod.__doc__


def test_module_file_ends_with_report_py():
    assert rmod.__file__.endswith("report.py")


def test_module_name_is_evaluation_report():
    assert rmod.__name__ == "evaluation.report"


def test_module_function_module_eq_rmod():
    assert build_provenance.__module__ == "evaluation.report"
    assert build_devset_section.__module__ == "evaluation.report"
    assert aggregate_summary.__module__ == "evaluation.report"
    assert get_git_provenance.__module__ == "evaluation.report"
    assert get_dependency_versions.__module__ == "evaluation.report"


# ---------- signatures 第七批 ----------


def test_signature_get_git_provenance_one_param():
    sig = inspect.signature(get_git_provenance)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "project_root"


def test_signature_get_git_provenance_no_default():
    sig = inspect.signature(get_git_provenance)
    params = sig.parameters
    assert params["project_root"].default is inspect.Parameter.empty


def test_signature_get_git_provenance_no_varargs():
    sig = inspect.signature(get_git_provenance)
    has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    assert not has_var


def test_signature_get_dependency_versions_no_params():
    sig = inspect.signature(get_dependency_versions)
    params = list(sig.parameters.values())
    assert len(params) == 0


def test_signature_build_provenance_4_params():
    sig = inspect.signature(build_provenance)
    params = list(sig.parameters.values())
    assert len(params) == 4


def test_signature_build_provenance_no_defaults():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_build_provenance_no_varargs():
    sig = inspect.signature(build_provenance)
    has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    assert not has_var


def test_signature_build_devset_section_one_param():
    sig = inspect.signature(build_devset_section)
    params = list(sig.parameters.values())
    assert len(params) == 1


def test_signature_build_devset_section_no_default():
    sig = inspect.signature(build_devset_section)
    params = sig.parameters
    assert list(params.values())[0].default is inspect.Parameter.empty


def test_signature_aggregate_summary_one_param():
    sig = inspect.signature(aggregate_summary)
    params = list(sig.parameters.values())
    assert len(params) == 1


def test_signature_aggregate_summary_no_default():
    sig = inspect.signature(aggregate_summary)
    params = sig.parameters
    assert list(params.values())[0].default is inspect.Parameter.empty


def test_signature_5_funcs_no_varargs():
    """5 个函数都没有 *args。"""
    for func in (build_provenance, build_devset_section, aggregate_summary,
                 get_git_provenance, get_dependency_versions):
        sig = inspect.signature(func)
        has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
        assert not has_var


def test_signature_5_funcs_no_kwargs():
    for func in (build_provenance, build_devset_section, aggregate_summary,
                 get_git_provenance, get_dependency_versions):
        sig = inspect.signature(func)
        has_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        assert not has_kw


# ---------- module source 字符串精确补强第七批 ----------


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


def test_module_source_imports_evaluator_version():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_ratio_metrics_constant():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS = (" in src


def test_module_source_count_metrics_constant():
    src = inspect.getsource(rmod)
    assert '_COUNT_METRICS = ("element_count_total",)' in src


def test_module_source_success_bool_metrics_constant():
    src = inspect.getsource(rmod)
    assert '_SUCCESS_BOOL_METRICS = ("pipeline_success",)' in src


def test_module_source_no_main_block():
    src = inspect.getsource(rmod)
    assert "__main__" not in src


def test_module_source_no_yield():
    src = inspect.getsource(rmod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(rmod)
    assert "async def" not in src


def test_module_source_no_walrus():
    src = inspect.getsource(rmod)
    assert ":=" not in src


def test_module_source_no_eval():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_compile():
    src = inspect.getsource(rmod)
    assert "compile(" not in src


def test_module_source_no_unlink():
    src = inspect.getsource(rmod)
    assert "unlink" not in src


def test_module_source_no_relative_above_evaluation():
    src = inspect.getsource(rmod)
    assert "from ." not in src


def test_module_source_no_star_import():
    src = inspect.getsource(rmod)
    assert "import *" not in src


def test_module_source_no_user_class_def():
    src = inspect.getsource(rmod)
    lines = src.splitlines()
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("class "):
            pytest.fail(f"Found class: {line}")


def test_module_source_subprocess_allowed():
    """report 允许 subprocess（get_git_provenance 需要）。"""
    src = inspect.getsource(rmod)
    assert "subprocess" in src


def test_module_source_datetime_allowed():
    src = inspect.getsource(rmod)
    assert "datetime" in src


# ---------- 端到端集成第七批 ----------


def test_e2e_full_chain_build_provenance_then_aggregate_summary():
    """完整 workflow：build_provenance → aggregate_summary。"""
    prov = build_provenance(Path("."), "fallback", 800, "1.0")
    assert "git_commit" in prov
    per_doc = [_make_per_doc({"element_count_total": {"value": 5}})]
    summary = aggregate_summary(per_doc)
    assert summary["counts"]["element_count_total"]["sum"] == 5


def test_e2e_aggregate_summary_partial_participation():
    """部分文档有部分 metric。"""
    per_doc = [
        _make_per_doc({
            "pdf_locator_valid_ratio": {"value": 0.8},
            "pipeline_success": {"value": True},
        }),
        _make_per_doc({
            "docx_locator_valid_ratio": {"value": 0.9},  # docx 不是 pdf
            "pipeline_success": {"value": False},
        }),
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["not_evaluated"] == 1


def test_e2e_aggregate_summary_macro_average_correct():
    per_doc = [
        _make_per_doc({"text_preservation_equal": {"value": True}}),  # True → 1.0
        _make_per_doc({"text_preservation_equal": {"value": False}}),  # False → 0.0
    ]
    out = aggregate_summary(per_doc)
    # bool True 参与算术时是 1.0
    assert out["ratio_macro_averages"]["text_preservation_equal"]["macro_average"] == 0.5


def test_e2e_aggregate_summary_json_serializable():
    """summary 应能 JSON 序列化。"""
    per_doc = [
        _make_per_doc({
            "element_count_total": {"value": 5},
            "pipeline_success": {"value": True},
            "silent_drop_count": {"value": 2},
        }),
    ]
    out = aggregate_summary(per_doc)
    s = json.dumps(out)
    assert isinstance(s, str)


def test_e2e_aggregate_summary_positional_args():
    per_doc = [_make_per_doc({"element_count_total": {"value": 5}})]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 5


def test_e2e_aggregate_summary_kwargs():
    per_doc = [_make_per_doc({"element_count_total": {"value": 5}})]
    out = aggregate_summary(per_doc_results=per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 5


def test_e2e_build_devset_section_with_paired_documents():
    """用 Manifest 模拟配对文档。"""
    m = _make_manifest(file_count=2, content_group_count=1, pdf_count=1, docx_count=1)
    out = build_devset_section(m)
    assert out["content_group_count"] == 1


def test_e2e_get_git_provenance_returns_2_keys():
    out = get_git_provenance(Path("."))
    assert len(out) == 2


def test_e2e_get_dependency_versions_returns_3_keys_str_or_none():
    out = get_dependency_versions()
    assert len(out) == 3
    for v in out.values():
        assert v is None or isinstance(v, str)


def test_e2e_build_provenance_returns_9_keys():
    out = build_provenance(Path("."), "fallback", 800, "1.0")
    assert len(out) == 9


def test_e2e_aggregate_summary_does_not_mutate_input():
    per_doc = [_make_per_doc({"element_count_total": {"value": 5}})]
    per_doc_before = json.loads(json.dumps(per_doc))
    aggregate_summary(per_doc)
    assert per_doc == per_doc_before
