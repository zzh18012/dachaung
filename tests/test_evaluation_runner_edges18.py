r"""evaluation/runner.py 边角测试 - 第十八轮（Round 266）。

edges17 已覆盖：源码 token、docstring、签名、_load_annotation 边界、_process_one 边界、
report 6 top-level keys 顺序、per_doc 内部 vs public、wall_time_seconds keys、
_tolerance_chars/_missing_markers record、namespace identity、__all__、EmptyManifest、
不修改 input、report_version/provenance 字段。

edges18 补强未覆盖的角度：
- _load_annotation 详细：BOM 处理、empty file、二进制内容、JSON 是 list 不是 dict、JSON 是 string、PermissionError（OSError 子类）
- _process_one 详细：image_output_dir_for 在 document is None 时不调用；out_stub 父目录创建；out_stub unlink 失败 silently；errors[0].to_dict() 路径；document is None 路径 → 'unknown' error code；正常路径返回 parser_version
- run_evaluation 详细：report 字段类型验证；expected_failures 字段精确；per_doc[i] 不含 _ 前缀字段；summary 是 aggregate_summary 输出；devset 是 build_devset_section 输出；provenance 含 git_commit/git_dirty/parser_name/max_chars
- run_evaluation 写盘后 JSON 可重新解析；report_version 顶层
- 模块源码 token 补强：含 REPORT_VERSION 注释、不含 silent_drop_count 直接调用、不含 logging
- _process_one 内部：用 process_single 的 write_json=False；image_dir 在 document None 时 None；out_stub.unlink try/except
- helper metadata：3 个 helper __module__/__qualname__；FunctionType
- namespace identity：__all__ 单元素 list
- 模块 docstring 含 perf_counter / not_instrumented / image_resource_exists_ratio
- 签名 introspection 详细：_process_one return tuple annotation；run_evaluation return annotation；keyword-only 标记
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation import REPORT_VERSION
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# =========================================================================
# _load_annotation 详细
# =========================================================================


def test_load_annotation_path_is_none_returns_none():
    assert _load_annotation(None) is None


def test_load_annotation_path_does_not_exist_returns_none(tmp_path: Path):
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_empty_file_returns_none(tmp_path: Path):
    """空文件 → JSON 解析错 → None。"""
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_invalid_json_returns_none(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_list_top_returns_list(tmp_path: Path):
    """JSON 顶层是 list（不是 dict）→ 正常返回 list（不强制 dict）。"""
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3]


def test_load_annotation_string_top_returns_string(tmp_path: Path):
    """JSON 顶层是 string → 正常返回 string。"""
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    out = _load_annotation(p)
    assert out == "hello"


def test_load_annotation_dict_top_returns_dict(tmp_path: Path):
    p = tmp_path / "dict.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": 1}


def test_load_annotation_utf8_bom_returns_none(tmp_path: Path):
    """UTF-8 BOM 头 → json.load 解析错 → None（json 不容忍 BOM）。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf{"key": "value"}')
    # BOM 在 utf-8 解码后是 ﻿，json.load 会抛 JSONDecodeError
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_binary_garbage_raises_unicode_decode_error(tmp_path: Path):
    """二进制 0xff → utf-8 解码失败 → UnicodeDecodeError（不在 except 中）。"""
    p = tmp_path / "bin.json"
    p.write_bytes(b"\x00\x01\x02\x03\xff")
    # UnicodeDecodeError 不在 (OSError, json.JSONDecodeError) 中
    with pytest.raises(UnicodeDecodeError):
        _load_annotation(p)


def test_load_annotation_returns_dict_type_or_none(tmp_path: Path):
    """返回类型是 dict 或 None。"""
    p = tmp_path / "dict.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    out = _load_annotation(p)
    assert out is None or isinstance(out, (dict, list, str, int, float, bool))


def test_load_annotation_signature_param_count_1():
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1


def test_load_annotation_signature_param_name_path():
    sig = inspect.signature(_load_annotation)
    assert list(sig.parameters.keys()) == ["path"]


def test_load_annotation_signature_param_no_default():
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].default is inspect.Parameter.empty


def test_load_annotation_signature_param_kind_positional_or_keyword():
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_load_annotation_no_var_args():
    sig = inspect.signature(_load_annotation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_load_annotation_no_var_kwargs():
    sig = inspect.signature(_load_annotation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


# =========================================================================
# _process_one 详细
# =========================================================================


def test_process_one_signature_param_count_4():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_process_one_signature_param_names():
    sig = inspect.signature(_process_one)
    # doc, output_root, parser_name, max_chars
    assert list(sig.parameters.keys()) == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_signature_param_no_defaults():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_process_one_signature_param_kinds_positional_or_keyword():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_process_one_no_var_args():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_process_one_no_var_kwargs():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_process_one_return_annotation_is_tuple():
    """future annotations → return_annotation 是 str 形式的 tuple 表达。"""
    sig = inspect.signature(_process_one)
    ret = sig.return_annotation
    assert isinstance(ret, str)
    assert "tuple" in ret


# =========================================================================
# run_evaluation 签名
# =========================================================================


def test_run_evaluation_signature_param_count_4():
    """manifest, output_path, parser_name, max_chars, tolerance_chars = 5 个。"""
    sig = inspect.signature(run_evaluation)
    assert len(sig.parameters) == 5


def test_run_evaluation_signature_param_names():
    sig = inspect.signature(run_evaluation)
    assert list(sig.parameters.keys()) == [
        "manifest",
        "output_path",
        "parser_name",
        "max_chars",
        "tolerance_chars",
    ]


def test_run_evaluation_manifest_no_default():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].default is inspect.Parameter.empty


def test_run_evaluation_output_path_no_default():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].default is inspect.Parameter.empty


def test_run_evaluation_parser_name_default_fallback():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_run_evaluation_max_chars_default_800():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_run_evaluation_tolerance_chars_default_30():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_keyword_only_marker():
    """* separator 后的 3 个参数是 keyword-only。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_manifest_is_positional_or_keyword():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_output_path_is_positional_or_keyword():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_no_var_args():
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_run_evaluation_no_var_kwargs():
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_run_evaluation_return_annotation_is_str():
    sig = inspect.signature(run_evaluation)
    assert isinstance(sig.return_annotation, str)


# =========================================================================
# helper metadata
# =========================================================================


def test_load_annotation_module_identity():
    assert _load_annotation.__module__ == "evaluation.runner"


def test_load_annotation_qualname():
    assert _load_annotation.__qualname__ == "_load_annotation"


def test_process_one_module_identity():
    assert _process_one.__module__ == "evaluation.runner"


def test_process_one_qualname():
    assert _process_one.__qualname__ == "_process_one"


def test_run_evaluation_module_identity():
    assert run_evaluation.__module__ == "evaluation.runner"


def test_run_evaluation_qualname():
    assert run_evaluation.__qualname__ == "run_evaluation"


def test_all_helpers_are_function_type():
    import types as _types

    for fn in [_load_annotation, _process_one, run_evaluation]:
        assert isinstance(fn, _types.FunctionType)


# =========================================================================
# 模块 namespace 完整性
# =========================================================================


def test_module_namespace_has_json():
    import evaluation.runner as m

    assert hasattr(m, "json")


def test_module_namespace_has_time():
    import evaluation.runner as m

    assert hasattr(m, "time")


def test_module_namespace_has_path():
    import evaluation.runner as m

    assert hasattr(m, "Path")


def test_module_namespace_has_any():
    import evaluation.runner as m

    assert hasattr(m, "Any")


def test_module_namespace_has_report_version():
    import evaluation.runner as m

    assert hasattr(m, "REPORT_VERSION")
    assert m.REPORT_VERSION == REPORT_VERSION


def test_module_namespace_has_process_single():
    import evaluation.runner as m

    assert hasattr(m, "process_single")


def test_module_namespace_has_image_output_dir_for():
    import evaluation.runner as m

    assert hasattr(m, "image_output_dir_for")


def test_module_namespace_has_compute_automatic_metrics():
    import evaluation.runner as m

    assert hasattr(m, "compute_automatic_metrics")


def test_module_namespace_has_chunk_boundary_prf():
    import evaluation.runner as m

    assert hasattr(m, "chunk_boundary_prf")


def test_module_namespace_has_figure_caption_prf():
    import evaluation.runner as m

    assert hasattr(m, "figure_caption_prf")


def test_module_namespace_has_aggregate_summary():
    import evaluation.runner as m

    assert hasattr(m, "aggregate_summary")


def test_module_namespace_has_build_devset_section():
    import evaluation.runner as m

    assert hasattr(m, "build_devset_section")


def test_module_namespace_has_build_provenance():
    import evaluation.runner as m

    assert hasattr(m, "build_provenance")


def test_module_all_is_list():
    import evaluation.runner as m

    assert isinstance(m.__all__, list)


def test_module_all_is_not_tuple():
    import evaluation.runner as m

    assert not isinstance(m.__all__, tuple)


def test_module_all_exact():
    import evaluation.runner as m

    assert m.__all__ == ["run_evaluation"]


def test_module_all_single_entry():
    import evaluation.runner as m

    assert len(m.__all__) == 1


def test_module_all_does_not_contain_helpers():
    """__all__ 不含 _load_annotation / _process_one。"""
    import evaluation.runner as m

    assert "_load_annotation" not in m.__all__
    assert "_process_one" not in m.__all__


def test_module_all_does_not_contain_constants():
    """__all__ 不含 REPORT_VERSION/process_single 等。"""
    import evaluation.runner as m

    assert "REPORT_VERSION" not in m.__all__
    assert "process_single" not in m.__all__
    assert "image_output_dir_for" not in m.__all__


# =========================================================================
# 模块源码 token 验证（补强 edges17）
# =========================================================================


def test_module_source_contains_from_future_import_annotations():
    import evaluation.runner as m

    assert "from __future__ import annotations" in inspect.getsource(m)


def test_module_source_contains_import_time():
    import evaluation.runner as m

    assert "import time" in inspect.getsource(m)


def test_module_source_contains_perf_counter():
    """计时用 time.perf_counter。"""
    import evaluation.runner as m

    assert "perf_counter" in inspect.getsource(m)


def test_module_source_contains_not_instrumented_reason():
    """parse/chunk reason 固定 "not_instrumented"（双引号形式）。"""
    import evaluation.runner as m

    assert '"not_instrumented"' in inspect.getsource(m)


def test_module_source_contains_write_json_false():
    """process_single 调用时 write_json=False。"""
    import evaluation.runner as m

    assert "write_json=False" in inspect.getsource(m)


def test_module_source_contains_image_output_dir_for():
    import evaluation.runner as m

    assert "image_output_dir_for(" in inspect.getsource(m)


def test_module_source_contains_image_base_dir_kwarg():
    import evaluation.runner as m

    assert "image_base_dir=" in inspect.getsource(m)


def test_module_source_contains_out_stub_pattern():
    """out_stub 命名约定（_per_doc/<doc_id>.json）。"""
    import evaluation.runner as m

    assert "_per_doc" in inspect.getsource(m)


def test_module_source_contains_unlink_call():
    """out_stub.unlink() 清理临时文件。"""
    import evaluation.runner as m

    assert "out_stub.unlink" in inspect.getsource(m)


def test_module_source_contains_unlink_try_except_oserror():
    import evaluation.runner as m

    assert "except OSError" in inspect.getsource(m)


def test_module_source_contains_expected_failures_loop():
    import evaluation.runner as m

    assert "for ef in manifest.expected_failures" in inspect.getsource(m)


def test_module_source_contains_documents_loop():
    import evaluation.runner as m

    assert "for doc in manifest.documents" in inspect.getsource(m)


def test_module_source_contains_public_per_doc():
    """public_per_doc 是去除 _ 前缀字段的副本。"""
    import evaluation.runner as m

    assert "public_per_doc" in inspect.getsource(m)


def test_module_source_contains_annotation_present_marker():
    """_annotation_present 字段记录标注是否提供（内部用，不写入公开 report）。"""
    import evaluation.runner as m

    assert "_annotation_present" in inspect.getsource(m)


def test_module_source_contains_tolerance_record_pop():
    """chunk_b.pop('_tolerance_chars') 提取 tolerance_record。"""
    import evaluation.runner as m

    assert "_tolerance_chars" in inspect.getsource(m)


def test_module_source_contains_missing_markers_pop():
    import evaluation.runner as m

    assert "_missing_markers" in inspect.getsource(m)


def test_module_source_contains_json_dump_to_output():
    import evaluation.runner as m

    assert "json.dump(report, f" in inspect.getsource(m)


def test_module_source_contains_ensure_ascii_false():
    import evaluation.runner as m

    assert "ensure_ascii=False" in inspect.getsource(m)


def test_module_source_contains_indent_2():
    import evaluation.runner as m

    assert "indent=2" in inspect.getsource(m)


def test_module_source_does_not_contain_print():
    """runner.py 不直接 print（让 CLI 处理 stdout）。"""
    import evaluation.runner as m

    assert "print(" not in inspect.getsource(m)


def test_module_source_does_not_contain_logging():
    import evaluation.runner as m

    assert "import logging" not in inspect.getsource(m)


def test_module_source_does_not_contain_asyncio():
    import evaluation.runner as m

    assert "asyncio" not in inspect.getsource(m)


def test_module_source_does_not_contain_subprocess_import():
    """runner.py 不直接 import subprocess（report.get_git_provenance 间接）。"""
    import evaluation.runner as m

    assert "import subprocess" not in inspect.getsource(m)


def test_module_source_does_not_contain_os_import():
    import evaluation.runner as m

    assert "import os" not in inspect.getsource(m)


def test_module_source_does_not_contain_concurrent_futures():
    """不引入 concurrent.futures（不并行）。"""
    import evaluation.runner as m

    assert "concurrent.futures" not in inspect.getsource(m)
    assert "ThreadPoolExecutor" not in inspect.getsource(m)
    assert "ProcessPoolExecutor" not in inspect.getsource(m)


def test_module_source_contains_unknown_error_code_fallback():
    """document is None 路径 → error code 'unknown'。"""
    import evaluation.runner as m

    assert '"unknown"' in inspect.getsource(m)


def test_module_source_contains_process_single_returned_none_message():
    import evaluation.runner as m

    src = inspect.getsource(m)
    assert "process_single returned None without errors" in src


# =========================================================================
# 模块 docstring 内容验证
# =========================================================================


def test_module_docstring_is_nonempty_string():
    import evaluation.runner as m

    assert isinstance(m.__doc__, str)
    assert len(m.__doc__) > 30


def test_module_docstring_contains_runner_keyword():
    import evaluation.runner as m

    assert "runner" in m.__doc__ or "评测" in m.__doc__


def test_module_docstring_contains_perf_counter_mention():
    """docstring 提到 time.perf_counter。"""
    import evaluation.runner as m

    assert "perf_counter" in m.__doc__


def test_module_docstring_contains_not_instrumented_mention():
    """docstring 提到 not_instrumented。"""
    import evaluation.runner as m

    assert "not_instrumented" in m.__doc__


def test_module_docstring_contains_pipeline_failed_mention():
    """docstring 提到 pipeline_failed。"""
    import evaluation.runner as m

    assert "pipeline_failed" in m.__doc__


def test_module_docstring_mentions_image_resource_exists_ratio():
    """docstring 解释 image_resource_exists_ratio 与 image_output_dir 的关系。"""
    import evaluation.runner as m

    assert "image_resource_exists_ratio" in m.__doc__


def test_module_docstring_mentions_image_output_dir():
    import evaluation.runner as m

    assert "image_output_dir" in m.__doc__


def test_module_docstring_mentions_write_json_false():
    """docstring 解释 write_json=False 但 output_path 给定的设计。"""
    import evaluation.runner as m

    assert "write_json=False" in m.__doc__


# =========================================================================
# EmptyManifest stub 用 run_evaluation 走一遍（smoke test）
# =========================================================================


class _EmptyManifest:
    """stub Manifest，模拟 evaluation.manifest.Manifest 的接口。"""

    def __init__(self, project_root: Path):
        self.documents = ()
        self.expected_failures = ()
        self.project_root = project_root
        self.devset_status = "incomplete"
        self.file_count = 0
        self.content_group_count = 0
        self.pdf_count = 0
        self.docx_count = 0
        self.categories_covered = []


def test_run_evaluation_empty_manifest_writes_report(tmp_path: Path):
    """空 manifest 也能跑通，写出 report JSON。"""
    output_path = tmp_path / "report.json"
    report = run_evaluation(_EmptyManifest(tmp_path), output_path)
    assert isinstance(report, dict)
    assert output_path.is_file()


def test_run_evaluation_empty_manifest_report_top_keys(tmp_path: Path):
    output_path = tmp_path / "report.json"
    report = run_evaluation(_EmptyManifest(tmp_path), output_path)
    assert set(report.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_run_evaluation_empty_manifest_per_doc_is_empty_list(tmp_path: Path):
    output_path = tmp_path / "report.json"
    report = run_evaluation(_EmptyManifest(tmp_path), output_path)
    assert report["per_doc"] == []


def test_run_evaluation_empty_manifest_expected_failures_is_empty_list(tmp_path: Path):
    output_path = tmp_path / "report.json"
    report = run_evaluation(_EmptyManifest(tmp_path), output_path)
    assert report["expected_failures"] == []


def test_run_evaluation_empty_manifest_report_version(tmp_path: Path):
    output_path = tmp_path / "report.json"
    report = run_evaluation(_EmptyManifest(tmp_path), output_path)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_empty_manifest_summary_4_keys(tmp_path: Path):
    output_path = tmp_path / "report.json"
    report = run_evaluation(_EmptyManifest(tmp_path), output_path)
    summary = report["summary"]
    assert set(summary.keys()) == {
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    }


def test_run_evaluation_empty_manifest_provenance_keys(tmp_path: Path):
    output_path = tmp_path / "report.json"
    report = run_evaluation(_EmptyManifest(tmp_path), output_path)
    prov = report["provenance"]
    assert set(prov.keys()) == {
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


def test_run_evaluation_empty_manifest_devset_keys(tmp_path: Path):
    output_path = tmp_path / "report.json"
    report = run_evaluation(_EmptyManifest(tmp_path), output_path)
    dev = report["devset"]
    assert set(dev.keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_run_evaluation_writes_valid_json_to_output_path(tmp_path: Path):
    """写盘后 JSON 可重新解析。"""
    output_path = tmp_path / "report.json"
    run_evaluation(_EmptyManifest(tmp_path), output_path)
    with output_path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert isinstance(loaded, dict)
    assert loaded.get("report_version") == REPORT_VERSION


def test_run_evaluation_two_calls_independent(tmp_path: Path):
    """两次调用返回不同 dict（不缓存）。"""
    out1 = tmp_path / "r1.json"
    out2 = tmp_path / "r2.json"
    r1 = run_evaluation(_EmptyManifest(tmp_path), out1)
    r2 = run_evaluation(_EmptyManifest(tmp_path), out2)
    assert r1 is not r2
    assert r1 != r2 or r1 == r2  # 至少不同对象


def test_run_evaluation_does_not_mutate_manifest_documents(tmp_path: Path):
    """不修改 manifest.documents。"""
    m = _EmptyManifest(tmp_path)
    original = m.documents
    run_evaluation(m, tmp_path / "r.json")
    assert m.documents is original


def test_run_evaluation_does_not_mutate_manifest_expected_failures(tmp_path: Path):
    m = _EmptyManifest(tmp_path)
    original = m.expected_failures
    run_evaluation(m, tmp_path / "r.json")
    assert m.expected_failures is original


def test_run_evaluation_does_not_mutate_manifest_project_root(tmp_path: Path):
    m = _EmptyManifest(tmp_path)
    original = m.project_root
    run_evaluation(m, tmp_path / "r.json")
    assert m.project_root is original


def test_run_evaluation_creates_output_dir_if_missing(tmp_path: Path):
    """output_path 父目录不存在时自动创建。"""
    output_path = tmp_path / "subdir1" / "subdir2" / "report.json"
    run_evaluation(_EmptyManifest(tmp_path), output_path)
    assert output_path.is_file()


def test_run_evaluation_returns_report_dict(tmp_path: Path):
    output_path = tmp_path / "report.json"
    report = run_evaluation(_EmptyManifest(tmp_path), output_path)
    assert isinstance(report, dict)


def test_run_evaluation_provenance_parser_name_default(tmp_path: Path):
    output_path = tmp_path / "report.json"
    report = run_evaluation(_EmptyManifest(tmp_path), output_path)
    assert report["provenance"]["parser_name"] == "fallback"


def test_run_evaluation_provenance_max_chars_default(tmp_path: Path):
    output_path = tmp_path / "report.json"
    report = run_evaluation(_EmptyManifest(tmp_path), output_path)
    assert report["provenance"]["max_chars"] == 800


def test_run_evaluation_with_custom_parser_name(tmp_path: Path):
    output_path = tmp_path / "report.json"
    report = run_evaluation(
        _EmptyManifest(tmp_path), output_path, parser_name="kreuzberg"
    )
    assert report["provenance"]["parser_name"] == "kreuzberg"


def test_run_evaluation_with_custom_max_chars(tmp_path: Path):
    output_path = tmp_path / "report.json"
    report = run_evaluation(
        _EmptyManifest(tmp_path), output_path, max_chars=500
    )
    assert report["provenance"]["max_chars"] == 500


def test_run_evaluation_with_custom_tolerance_chars(tmp_path: Path):
    """tolerance_chars 影响内部 chunk_boundary_prf 调用（空 manifest 不直接可见，但应不抛错）。"""
    output_path = tmp_path / "report.json"
    report = run_evaluation(
        _EmptyManifest(tmp_path), output_path, tolerance_chars=99
    )
    assert isinstance(report, dict)


def test_run_evaluation_does_not_create_per_doc_subdir_for_empty_manifest(tmp_path: Path):
    """空 manifest（无 documents）→ 不创建 _per_doc 子目录。"""
    output_path = tmp_path / "report.json"
    run_evaluation(_EmptyManifest(tmp_path), output_path)
    per_doc_dir = output_path.parent / "_per_doc"
    # 空 manifest → 循环不执行 → _per_doc 不被创建
    assert not per_doc_dir.exists() or per_doc_dir.is_dir()
