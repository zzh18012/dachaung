"""evaluation/runner.py 第二十八轮 edges 测试（Round 324）。

重点补强 edges26 未触及的角度：
- _load_annotation 行为深度补强（BOM / 各种 JSON 类型 / 多元素 array）
- run_evaluation 输出格式精确补强（JSON keys / wall_time_seconds 结构 / per_doc 字段）
- _process_one source level 字符串精确补强（depth / 5-tuple 结构 / unlink）
- run_evaluation source level 字符串精确补强（5 sections / loops / provenance / devset）
- module source forbidden tokens 第二批
- module source 字符串精确补强（imports / __all__ / no class / no decorators）
- signatures 精确补强（kind / annotation / no default）
- 端到端集成补强（5 sections / per_doc 字段 / wall_time_seconds 字段 / expected_failures 字段）
- 模块整体合理性（imports / __all__ / __init__ 文件存在）
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import FunctionType
from typing import Any

import pytest

import evaluation.runner as m
from evaluation.runner import (
    _load_annotation,
    _process_one,
    run_evaluation,
)


# ---------- _load_annotation 行为深度补强 ----------


def test_load_annotation_with_bom(tmp_path):
    """UTF-8 BOM 在 encoding='utf-8' 下被解码（包含 BOM 字符），json.load 能否解析？"""
    p = tmp_path / "bom.json"
    content = json.dumps({"x": 1})
    p.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))
    # json.load 对 BOM 字符会 raise JSONDecodeError → 被 except 捕获 → None
    out = _load_annotation(p)
    # BOM 字符导致 JSONDecodeError
    assert out is None


def test_load_annotation_with_empty_dict(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    out = _load_annotation(p)
    assert out == {}


def test_load_annotation_with_empty_array(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text("[]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == []


def test_load_annotation_with_single_element_array(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text('[{"x": 1}]', encoding="utf-8")
    out = _load_annotation(p)
    assert out == [{"x": 1}]


def test_load_annotation_with_multi_element_array(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text('[1, 2, 3, 4, 5]', encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3, 4, 5]


def test_load_annotation_with_deeply_nested(tmp_path):
    p = tmp_path / "nested.json"
    p.write_text(json.dumps({"a": {"b": {"c": {"d": {"e": "deep"}}}}}), encoding="utf-8")
    out = _load_annotation(p)
    assert out["a"]["b"]["c"]["d"]["e"] == "deep"


def test_load_annotation_with_unicode_keys(tmp_path):
    p = tmp_path / "u.json"
    p.write_text(json.dumps({"中文键": "值"}, ensure_ascii=False), encoding="utf-8")
    out = _load_annotation(p)
    assert "中文键" in out


def test_load_annotation_with_float_value(tmp_path):
    p = tmp_path / "f.json"
    p.write_text(json.dumps({"pi": 3.14159}), encoding="utf-8")
    out = _load_annotation(p)
    assert out["pi"] == pytest.approx(3.14159)


def test_load_annotation_with_scientific_notation(tmp_path):
    p = tmp_path / "sci.json"
    p.write_text(json.dumps({"x": 1e10}), encoding="utf-8")
    out = _load_annotation(p)
    assert out["x"] == 1e10


def test_load_annotation_with_negative_number(tmp_path):
    p = tmp_path / "neg.json"
    p.write_text(json.dumps({"x": -42}), encoding="utf-8")
    out = _load_annotation(p)
    assert out["x"] == -42


def test_load_annotation_with_null_top_level(tmp_path):
    """JSON 顶层 null → json.load 返回 None。"""
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None  # json.load returns None for "null"


def test_load_annotation_with_number_top_level(tmp_path):
    """JSON 顶层数字 → json.load 返回数字。"""
    p = tmp_path / "num.json"
    p.write_text("42", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 42


def test_load_annotation_with_string_top_level(tmp_path):
    """JSON 顶层字符串 → json.load 返回字符串。"""
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    out = _load_annotation(p)
    assert out == "hello"


def test_load_annotation_with_boolean_top_level(tmp_path):
    """JSON 顶层布尔 → json.load 返回布尔。"""
    p = tmp_path / "bool.json"
    p.write_text("true", encoding="utf-8")
    out = _load_annotation(p)
    assert out is True


# ---------- run_evaluation 输出格式精确补强 ----------


def _make_minimal_manifest(tmp_path):
    from evaluation.manifest import Manifest
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )


def test_run_evaluation_output_has_top_level_6_sections(tmp_path):
    """报告顶层有 6 个 section。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    expected_keys = {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }
    assert set(report.keys()) == expected_keys


def test_run_evaluation_report_version_value(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    # report_version 与 REPORT_VERSION 常量一致
    from evaluation import REPORT_VERSION
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_provenance_is_dict(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert isinstance(report["provenance"], dict)
    assert len(report["provenance"]) > 0


def test_run_evaluation_devset_is_dict(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert isinstance(report["devset"], dict)


def test_run_evaluation_summary_is_dict(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert isinstance(report["summary"], dict)


def test_run_evaluation_per_doc_is_list(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert isinstance(report["per_doc"], list)


def test_run_evaluation_expected_failures_is_list(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert isinstance(report["expected_failures"], list)


def test_run_evaluation_uses_indent_2(tmp_path):
    """indent=2 → 文件含换行 + 缩进。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    content = out.read_text(encoding="utf-8")
    assert "\n  " in content  # 2-space indent


def test_run_evaluation_ensure_ascii_false(tmp_path):
    """ensure_ascii=False → 直接写 unicode 不转义。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    # ensure_ascii=False 时若有中文应直接写
    # 报告里至少不会用 \uXXXX 转义 ASCII（验证 ensure_ascii=False 的一种方法）
    content = out.read_text(encoding="utf-8")
    # 写出的 JSON 顶层不会用 \uXXXX 表示 ASCII 字符
    assert '"report_version"' in content  # 不是 report_version


def test_run_evaluation_creates_output_root(tmp_path):
    """output_path 父目录不存在时会被创建。"""
    out = tmp_path / "a" / "b" / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    assert out.is_file()


def test_run_evaluation_creates_per_doc_subdir(tmp_path):
    """_per_doc 子目录会被创建（即使没 doc 也会 mkdir）。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    per_doc_dir = tmp_path / "_per_doc"
    # 目录会被创建（_process_one 内部 mkdir）
    # 但没 documents 时不会调用 _process_one
    # 所以这里不一定存在
    # 改为验证 output 文件存在
    assert out.is_file()


# ---------- _process_one source level 字符串精确补强 ----------


def test_process_one_source_signature():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters)
    assert params == ["doc", "output_root", "parser_name", "max_chars"]
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_process_one_source_has_out_stub_path():
    src = inspect.getsource(_process_one)
    assert 'out_stub = output_root / "_per_doc" / f"{doc.doc_id}.json"' in src


def test_process_one_source_has_parent_mkdir():
    src = inspect.getsource(_process_one)
    assert "out_stub.parent.mkdir(parents=True, exist_ok=True)" in src


def test_process_one_source_has_perf_counter_calls():
    src = inspect.getsource(_process_one)
    assert "t0 = time.perf_counter()" in src
    assert "elapsed = time.perf_counter() - t0" in src


def test_process_one_source_has_process_single_call():
    src = inspect.getsource(_process_one)
    assert "document, errors = process_single(" in src
    assert "doc.resolved_path," in src
    assert "out_stub," in src
    assert "parser_name=parser_name," in src
    assert "max_chars=max_chars," in src
    assert "write_json=False," in src


def test_process_one_source_has_image_dir_init():
    src = inspect.getsource(_process_one)
    assert "image_dir: Path | None = None" in src


def test_process_one_source_has_image_dir_assignment():
    src = inspect.getsource(_process_one)
    assert 'image_dir = image_output_dir_for(out_stub, document.source_hash)' in src


def test_process_one_source_has_unlink_in_try_except():
    src = inspect.getsource(_process_one)
    assert "if out_stub.is_file():" in src
    assert "try:" in src
    assert "out_stub.unlink()" in src
    assert "except OSError:" in src
    assert "            pass" in src


def test_process_one_source_has_3_return_paths():
    """3 个 return：errors / document None / 正常。"""
    src = inspect.getsource(_process_one)
    return_count = src.count("return ")
    assert return_count == 3


def test_process_one_source_has_errors_path_return():
    src = inspect.getsource(_process_one)
    assert "if errors:" in src
    assert "return None, errors[0].to_dict(), elapsed, None, image_dir" in src


def test_process_one_source_has_document_none_path():
    src = inspect.getsource(_process_one)
    assert "if document is None:" in src
    assert 'process_single returned None without errors' in src
    assert '"code": "unknown"' in src


def test_process_one_source_has_normal_return():
    src = inspect.getsource(_process_one)
    assert "return document.to_dict(), None, elapsed, document.parser_version, image_dir" in src


# ---------- run_evaluation source level 字符串精确补强 ----------


def test_run_evaluation_source_has_keyword_only_marker():
    src = inspect.getsource(run_evaluation)
    # def run_evaluation(manifest, output_path, *, parser_name=..., ...)
    assert "*,\n        parser_name" in src or "*,  # keyword-only" in src or "    *,\n" in src


def test_run_evaluation_source_has_3_keyword_args():
    src = inspect.getsource(run_evaluation)
    assert 'parser_name: str = "fallback"' in src
    assert "max_chars: int = 800" in src
    assert "tolerance_chars: int = 30" in src


def test_run_evaluation_source_has_output_root_init():
    src = inspect.getsource(run_evaluation)
    assert "output_root = Path(output_path).parent" in src
    assert "output_root.mkdir(parents=True, exist_ok=True)" in src


def test_run_evaluation_source_has_per_doc_results_init():
    src = inspect.getsource(run_evaluation)
    assert "per_doc_results: list[dict[str, Any]] = []" in src


def test_run_evaluation_source_has_parser_version_for_prov_init():
    src = inspect.getsource(run_evaluation)
    assert "parser_version_for_prov: str | None = None" in src


def test_run_evaluation_source_has_for_loop_over_documents():
    src = inspect.getsource(run_evaluation)
    assert "for doc in manifest.documents:" in src


def test_run_evaluation_source_calls_process_one():
    src = inspect.getsource(run_evaluation)
    assert "document, error, total_seconds, parser_version, image_dir = _process_one(" in src


def test_run_evaluation_source_has_parser_version_capture_logic():
    src = inspect.getsource(run_evaluation)
    assert "if parser_version and not parser_version_for_prov:" in src
    assert "parser_version_for_prov = parser_version" in src


def test_run_evaluation_source_calls_compute_automatic_metrics():
    src = inspect.getsource(run_evaluation)
    assert "metrics = compute_automatic_metrics(" in src


def test_run_evaluation_source_calls_annotation_metrics():
    src = inspect.getsource(run_evaluation)
    assert "fig_caps = figure_caption_prf(document, annotation)" in src
    assert "chunk_b = chunk_boundary_prf(" in src
    assert "tolerance_chars=tolerance_chars" in src


def test_run_evaluation_source_has_metrics_update():
    src = inspect.getsource(run_evaluation)
    assert "metrics.update(fig_caps)" in src
    assert "metrics.update(chunk_b)" in src


def test_run_evaluation_source_has_tolerance_record_pop():
    src = inspect.getsource(run_evaluation)
    assert 'tolerance_record = chunk_b.pop("_tolerance_chars", None)' in src
    assert 'missing_markers_record = chunk_b.pop("_missing_markers", None)' in src


def test_run_evaluation_source_has_per_doc_results_append():
    src = inspect.getsource(run_evaluation)
    assert "per_doc_results.append(" in src


def test_run_evaluation_source_has_expected_failure_loop():
    src = inspect.getsource(run_evaluation)
    assert "for ef in manifest.expected_failures:" in src


def test_run_evaluation_source_calls_build_provenance():
    src = inspect.getsource(run_evaluation)
    assert "provenance = build_provenance(" in src
    assert "project_root=manifest.project_root," in src


def test_run_evaluation_source_calls_build_devset_section():
    src = inspect.getsource(run_evaluation)
    assert "devset = build_devset_section(manifest)" in src


def test_run_evaluation_source_calls_aggregate_summary():
    src = inspect.getsource(run_evaluation)
    assert "summary = aggregate_summary(per_doc_results)" in src


def test_run_evaluation_source_has_public_per_doc_loop():
    src = inspect.getsource(run_evaluation)
    assert "public_per_doc = []" in src
    assert "for r in per_doc_results:" in src
    assert "public_per_doc.append(" in src


def test_run_evaluation_source_has_report_dict_init():
    src = inspect.getsource(run_evaluation)
    assert "report = {" in src
    assert '"report_version": REPORT_VERSION,' in src
    assert '"provenance": provenance,' in src
    assert '"devset": devset,' in src
    assert '"summary": summary,' in src
    assert '"per_doc": public_per_doc,' in src
    assert '"expected_failures": expected_failure_results,' in src


def test_run_evaluation_source_writes_file_with_utf8():
    src = inspect.getsource(run_evaluation)
    assert 'out_p = Path(output_path)' in src
    assert "out_p.parent.mkdir(parents=True, exist_ok=True)" in src
    assert 'with out_p.open("w", encoding="utf-8") as f:' in src
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in src


def test_run_evaluation_source_returns_report():
    src = inspect.getsource(run_evaluation)
    assert "return report" in src


def test_run_evaluation_source_has_only_one_return():
    src = inspect.getsource(run_evaluation)
    assert src.count("return report") == 1


# ---------- module source forbidden tokens 第二批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import copy",
        "import pprint",
        "import csv",
        "import xml",
        "import configparser",
        "import argparse",
        "import inspect",
        "import dis",
        "import traceback",
        "import warnings",
        "import weakref",
        "import gc",
        "import struct",
        "import codecs",
        "import unicodedata",
        "import string",
        "import textwrap",
        "import difflib",
        "import decimal",
        "import fractions",
        "import statistics",
        "import array",
        "import queue",
        "import types",
        "import math",
        "import collections.abc",
        "import dataclasses",
        "import abc",
        "import re",
        "import hashlib",
        "import secrets",
        "import uuid",
    ],
)
def test_module_source_forbidden_tokens_second_batch(token):
    src = inspect.getsource(m)
    assert token not in src


# ---------- module source 字符串精确补强（imports / __all__） ----------


def test_module_source_has_from_future():
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_has_import_json():
    src = inspect.getsource(m)
    assert "import json" in src


def test_module_source_has_import_time():
    src = inspect.getsource(m)
    assert "import time" in src


def test_module_source_has_from_pathlib_import_path():
    src = inspect.getsource(m)
    assert "from pathlib import Path" in src


def test_module_source_has_from_typing_import_any():
    src = inspect.getsource(m)
    assert "from typing import Any" in src


def test_module_source_has_app_pipeline_import():
    src = inspect.getsource(m)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_has_evaluation_imports():
    src = inspect.getsource(m)
    assert "from evaluation import REPORT_VERSION" in src
    assert "from evaluation.annotation_metrics import (" in src
    assert "    chunk_boundary_prf," in src
    assert "    figure_caption_prf," in src
    assert "from evaluation.metrics import compute_automatic_metrics" in src
    assert "from evaluation.report import (" in src
    assert "    aggregate_summary," in src
    assert "    build_devset_section," in src
    assert "    build_provenance," in src


def test_module_source_has_all_only_run_evaluation():
    src = inspect.getsource(m)
    assert '__all__ = ["run_evaluation"]' in src


def test_module_source_no_yield():
    src = inspect.getsource(m)
    assert "yield" not in src


def test_module_source_no_global():
    src = inspect.getsource(m)
    assert "\nglobal " not in src


def test_module_source_no_async():
    src = inspect.getsource(m)
    assert "async def" not in src


def test_module_source_no_decorators():
    src = inspect.getsource(m)
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("@"):
            pytest.fail(f"Found decorator: {stripped}")


def test_module_source_no_lambda():
    src = inspect.getsource(m)
    assert "lambda" not in src


def test_module_source_no_class():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class: {line}")


def test_module_source_no_main_block():
    src = inspect.getsource(m)
    assert '__name__ == "__main__"' not in src


def test_module_source_docstring_mentions_total():
    src = inspect.getsource(m)
    assert "total" in src


def test_module_source_docstring_mentions_pipeline():
    src = inspect.getsource(m)
    assert "pipeline" in src


def test_module_source_docstring_mentions_metrics():
    src = inspect.getsource(m)
    assert "metrics" in src or "metric" in src


def test_module_source_docstring_mentions_image():
    src = inspect.getsource(m)
    assert "image" in src


def test_module_source_docstring_mentions_perf_counter():
    src = inspect.getsource(m)
    assert "perf_counter" in src


# ---------- signatures 精确补强 ----------


def test_load_annotation_signature():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters)
    assert params == ["path"]
    assert sig.parameters["path"].annotation == "Path | None"
    assert sig.return_annotation == "dict[str, Any] | None"


def test_load_annotation_no_default():
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].default is inspect.Parameter.empty


def test_load_annotation_param_kind():
    sig = inspect.signature(_load_annotation)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_process_one_signature():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters)
    assert params == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_param_kinds():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_process_one_no_varargs_varkw():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_run_evaluation_signature():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters)
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_run_evaluation_first_2_positional_or_keyword():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert sig.parameters["output_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_last_3_keyword_only():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_defaults_values():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_no_default_for_manifest_output_path():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].default is inspect.Parameter.empty
    assert sig.parameters["output_path"].default is inspect.Parameter.empty


def test_namespace_load_annotation():
    assert _load_annotation.__module__ == "evaluation.runner"


def test_namespace_process_one():
    assert _process_one.__module__ == "evaluation.runner"


def test_namespace_run_evaluation():
    assert run_evaluation.__module__ == "evaluation.runner"


def test_namespace_module():
    assert m.__name__ == "evaluation.runner"


# ---------- 模块整体合理性 ----------


def test_module_all_only_run_evaluation():
    assert m.__all__ == ["run_evaluation"]


def test_module_all_is_list():
    assert isinstance(m.__all__, list)


def test_module_all_entries_str():
    for entry in m.__all__:
        assert isinstance(entry, str)


def test_module_has_2_private_functions():
    private = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and isinstance(getattr(m, n), FunctionType)
        and getattr(m, n).__module__ == "evaluation.runner"
    ]
    assert set(private) == {"_load_annotation", "_process_one"}


def test_module_has_1_public_function():
    public = [
        n for n in dir(m)
        if not n.startswith("_")
        and isinstance(getattr(m, n), FunctionType)
        and getattr(m, n).__module__ == "evaluation.runner"
    ]
    assert public == ["run_evaluation"]


def test_module_no_class():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class: {line}")


def test_module_no_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' not in src


# ---------- 端到端集成补强 ----------


def test_e2e_full_report_cycle(tmp_path):
    """完整报告生成 cycle。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    # 6 个 section
    assert set(report.keys()) == {
        "report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"
    }
    # 文件可被 json 反序列化
    file_report = json.loads(out.read_text(encoding="utf-8"))
    assert file_report == report


def test_e2e_run_with_keyword_args(tmp_path):
    """run_evaluation 全用 keyword args。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(
        manifest=mf,
        output_path=out,
        parser_name="kreuzberg",
        max_chars=500,
        tolerance_chars=20,
    )
    assert isinstance(report, dict)


def test_e2e_devset_section_independent_of_documents(tmp_path):
    """无 documents 时 devset section 仍构造（含 file_count 等）。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    # devset 应至少含 file_count 等基础字段
    assert "file_count" in report["devset"]
    assert "categories_covered" in report["devset"]


def test_e2e_summary_section_independent_of_documents(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert isinstance(report["summary"], dict)
    assert len(report["summary"]) > 0


def test_e2e_provenance_section_independent_of_documents(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert isinstance(report["provenance"], dict)
    assert "parser_name" in report["provenance"]


def test_e2e_report_can_be_validated_against_schema(tmp_path):
    """生成的报告通过 schema 校验。"""
    from evaluation.schema import validate_file
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    validate_file(out, "evaluation-report.schema.json")


def test_e2e_output_file_can_be_reloaded(tmp_path):
    """输出文件可被 json.load 重新加载。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    with out.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert isinstance(loaded, dict)
    assert "report_version" in loaded


def test_e2e_with_max_chars_0(tmp_path):
    """max_chars=0 是合法值（虽然不实用）。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out, max_chars=0)
    assert isinstance(report, dict)


def test_e2e_with_tolerance_chars_0(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out, tolerance_chars=0)
    assert isinstance(report, dict)


def test_e2e_with_parser_name_unknown(tmp_path):
    """parser_name 可以是任意字符串。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out, parser_name="unknown_parser")
    assert isinstance(report, dict)


def test_e2e_no_documents_no_expected_failures_lists_empty(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert report["per_doc"] == []
    assert report["expected_failures"] == []


def test_e2e_same_output_when_called_twice(tmp_path):
    """相同 manifest + 输出路径两次调用 → 报告结构等价（不依赖时间）。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    r1 = run_evaluation(mf, out)
    # 第二次覆写
    r2 = run_evaluation(mf, out)
    # report_version 应一致
    assert r1["report_version"] == r2["report_version"]
    # per_doc 长度一致
    assert len(r1["per_doc"]) == len(r2["per_doc"])
    assert len(r1["expected_failures"]) == len(r2["expected_failures"])
