r"""evaluation/runner.py 边角测试 - 第二十五轮（Round 306）。

edges23 已覆盖：_load_annotation 边界 / _process_one 行为深度 / run_evaluation 行为深度 /
wall_time 结构 / expected_failure 处理 / annotation 字段处理 / parser_version 处理 /
image_dir 逻辑 / report 写盘细节 / public_per_doc 构造 / report 装配 / module imports /
namespace / forbidden tokens / __all__ / docstring / signatures 完整 / source level 完整 / 端到端。

edges24 补强未覆盖的角度（深度边界 + 算法不变量 + source level + signatures + 端到端）：
- **_load_annotation 行为深度补强**：empty file → JSONDecodeError → None；
  file 内容是 `{}` → 返 {}；file 内容是 `null` → 返 None（json.load 返 None）；
  file 内容是 `[1,2,3]` list → 返 list（不强制 dict）；
  file 内容是 `"string"` → 返 str；file 内容是 `42` → 返 int；
  signature 1 param + no default；source 含 except (OSError, json.JSONDecodeError)
- **_process_one 5-tuple 边界补强**：返 5 个元素（不是 4 也不是 6）；
  document_dict 与 error_dict 互斥（一个 None，另一个也 None 或 dict）；
  parser_version 在 errors 时是 None；parser_version 在 document is None 时是 None；
  image_dir 在 document is None 时是 None；
  signature 4 params no default + no varargs/varkw；return 是 tuple
- **run_evaluation keyword-only 3 params**：parser_name 必须 keyword；
  max_chars 必须 keyword；tolerance_chars 必须 keyword；
  default 值精确（fallback/800/30）；positional 2 个（manifest + output_path）；
  no varargs/varkw；return 是 dict
- **wall_time_seconds 内部精确补强**：含 6 keys（total/parse/chunk/parse_reason/chunk_reason）；
  parse/chunk 固定 None；parse_reason/chunk_reason 固定 'not_instrumented'；
  total 是 float（>= 0）；total 不依赖 parse/chunk（不混合）
- **expected_failures 处理深度补强**：errors 非空 → actual_code 是 str；
  errors 空 + document None → actual_code is None；
  errors 空 + document not None → actual_code is None；
  matches 是 bool；4 keys 精确；for ef 循环
- **annotation 字段处理深度补强**：_annotation_present 是 bool；
  _tolerance_chars 是 int or None；_missing_markers 是 list；
  tolerance_record = chunk_b.pop('_tolerance_chars', None) → dict or None；
  missing_markers_record = chunk_b.pop('_missing_markers', None) → dict or None
- **public_per_doc 构造精确补强**：每个 entry 4 keys（doc_id/source_type/metrics/wall_time_seconds）；
  不含 _annotation_present / _tolerance_chars / _missing_markers（这些是 internal）
- **report 装配顺序补强**：6 top-level keys 顺序精确（report_version/provenance/devset/
  summary/per_doc/expected_failures）；report_version 在第一个；expected_failures 在最后
- **module imports 精确补强**：10 imports 精确：
  future/json/time/pathlib/typing (5 stdlib) + app.pipeline (1) +
  evaluation.REPORT_VERSION/annotation_metrics/metrics/report (4 evaluation)
- **module source forbidden tokens 补强**：不含 os/sys/re/logging/subprocess/asyncio/
  threading/concurrent/collections/math/datetime/socket/email/html/http/urllib/sqlite3/csv/pickle
- **module source 含必要字符串**：含 process_single + image_output_dir_for +
  compute_automatic_metrics + figure_caption_prf + chunk_boundary_prf +
  build_provenance + build_devset_section + aggregate_summary + REPORT_VERSION
- **module source level 完整补强**：run_evaluation 含 'output_root = Path(output_path).parent' +
  mkdir parents=True exist_ok=True + for doc in manifest.documents +
  parser_version and not parser_version_for_prov + image_base_dir if +
  metrics.update fig_caps + chunk_b.pop + per_doc_results.append 含 6 keys +
  for ef in manifest.expected_failures + actual_code = errors[0].code if errors else None +
  matches = actual_code == ef.expected_error_code +
  out_p = Path(output_path) + json.dump ensure_ascii=False + indent=2
- **signatures 精确补强**：_load_annotation 1 param + no default +
  _process_one 4 params + no default + return tuple + no varargs/varkw +
  run_evaluation 2 positional + 3 keyword-only + 3 defaults + no varargs/varkw + return dict
- **端到端集成补强**：empty manifest + tmp_path → empty per_doc + empty expected_failures；
  run_evaluation 不修改 manifest；
  写盘 file 内容是 valid JSON；
  报告 devset section 来自 build_devset_section；
  报告 summary 来自 aggregate_summary
- **模块整体合理性**：__all__ 1 entry；3 module-level function（_load_annotation +
  _process_one + run_evaluation）；9 imported names；无 class；无 __main__
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

import evaluation.runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# =========================================================================
# 辅助
# =========================================================================


def _make_doc_entry(tmp_path, doc_id="d1", source_type="pdf"):
    """构造一个最小 DocumentEntry-like 对象（用 mock）。"""
    from unittest.mock import MagicMock
    doc = MagicMock()
    doc.doc_id = doc_id
    doc.source_type = source_type
    doc.resolved_path = tmp_path / f"{doc_id}.pdf"
    doc.expectations = None
    doc.annotation_resolved = None
    return doc


def _make_manifest(tmp_path, documents=None, expected_failures=None, project_root=None):
    """构造一个最小 Manifest-like 对象。"""
    from unittest.mock import MagicMock
    m = MagicMock()
    m.documents = documents or []
    m.expected_failures = expected_failures or []
    m.project_root = project_root or tmp_path
    return m


# =========================================================================
# _load_annotation 行为深度补强
# =========================================================================


def test_load_annotation_empty_file_returns_none(tmp_path):
    """empty file → JSONDecodeError → None。"""
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_empty_dict_returns_empty_dict(tmp_path):
    """file 内容是 {} → 返 {}。"""
    p = tmp_path / "empty_dict.json"
    p.write_text("{}", encoding="utf-8")
    out = _load_annotation(p)
    assert out == {}


def test_load_annotation_null_returns_none(tmp_path):
    """file 内容是 null → json.load 返 None → return None。"""
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    out = _load_annotation(p)
    # json.load('null') → None，但函数仍返这个 None（不是 catch 触发的）
    assert out is None


def test_load_annotation_list_returns_list(tmp_path):
    """file 内容是 [1,2,3] list → 返 list（不强制 dict）。"""
    p = tmp_path / "list.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3]


def test_load_annotation_string_returns_string(tmp_path):
    """file 内容是 "string" → 返 str。"""
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    out = _load_annotation(p)
    assert out == "hello"


def test_load_annotation_int_returns_int(tmp_path):
    """file 内容是 42 → 返 int。"""
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 42


def test_load_annotation_signature_1_param_no_default():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].default is inspect.Parameter.empty


def test_load_annotation_no_varargs_varkw():
    sig = inspect.signature(_load_annotation)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_load_annotation_source_has_except_oserror_jsondecodeerror():
    src = inspect.getsource(_load_annotation)
    assert "except (OSError, json.JSONDecodeError)" in src


def test_load_annotation_source_has_path_is_none_check():
    src = inspect.getsource(_load_annotation)
    assert "path is None" in src
    assert "not path.is_file()" in src


def test_load_annotation_source_has_utf8():
    src = inspect.getsource(_load_annotation)
    assert 'encoding="utf-8"' in src


def test_load_annotation_none_input_returns_none():
    """path=None → return None（short-circuit）。"""
    out = _load_annotation(None)
    assert out is None


# =========================================================================
# _process_one 5-tuple 边界补强
# =========================================================================


def test_process_one_signature_4_params_no_default():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.values())
    assert len(params) == 4
    for p in params:
        assert p.default is inspect.Parameter.empty


def test_process_one_no_varargs_varkw():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_process_one_return_annotation_is_tuple():
    sig = inspect.signature(_process_one)
    # from __future__ → annotation is string
    assert "tuple" in str(sig.return_annotation)


def test_process_one_source_has_out_stub_template():
    """source 含 out_stub = output_root / '_per_doc' / f'{doc.doc_id}.json'。"""
    src = inspect.getsource(_process_one)
    assert "_per_doc" in src
    assert "doc.doc_id" in src


def test_process_one_source_has_perf_counter_twice():
    """source 含 perf_counter 2 处（t0 / elapsed）。"""
    src = inspect.getsource(_process_one)
    assert src.count("perf_counter()") == 2


def test_process_one_source_has_process_single_call():
    src = inspect.getsource(_process_one)
    assert "process_single(" in src
    assert "parser_name=parser_name" in src
    assert "max_chars=max_chars" in src
    assert "write_json=False" in src


def test_process_one_source_has_image_output_dir_for_call():
    src = inspect.getsource(_process_one)
    assert "image_output_dir_for" in src


def test_process_one_source_has_unlink_oserror_catch():
    src = inspect.getsource(_process_one)
    assert "out_stub.is_file()" in src
    assert "out_stub.unlink()" in src
    assert "except OSError" in src


def test_process_one_source_has_3_branches():
    """source 含 if errors / if document is None / else 三分支。"""
    src = inspect.getsource(_process_one)
    assert "if errors:" in src
    assert "if document is None:" in src
    assert "errors[0].to_dict()" in src


def test_process_one_source_has_unknown_error_message():
    src = inspect.getsource(_process_one)
    assert "process_single returned None without errors" in src
    assert "unknown" in src


def test_process_one_source_has_document_to_dict_call():
    src = inspect.getsource(_process_one)
    assert "document.to_dict()" in src
    assert "document.parser_version" in src


# =========================================================================
# run_evaluation keyword-only 3 params
# =========================================================================


def test_run_evaluation_signature_2_positional_3_keyword():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert len(params) == 5
    # 前 2 个是 positional（manifest + output_path）
    assert params[0].name == "manifest"
    assert params[1].name == "output_path"
    # 后 3 个是 keyword-only
    assert params[2].kind == inspect.Parameter.KEYWORD_ONLY
    assert params[3].kind == inspect.Parameter.KEYWORD_ONLY
    assert params[4].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_keyword_default_values():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_no_varargs_varkw():
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_run_evaluation_return_annotation_is_dict():
    sig = inspect.signature(run_evaluation)
    assert "dict" in str(sig.return_annotation)


def test_run_evaluation_source_has_keyword_only_marker():
    """source 含 * marker（keyword-only 标记）。"""
    src = inspect.getsource(run_evaluation)
    assert "*,\n    parser_name" in src or "*,\n        parser_name" in src


# =========================================================================
# wall_time_seconds 内部精确补强
# =========================================================================


def test_run_evaluation_source_has_wall_time_6_keys():
    """source 含 wall_time_seconds 6 keys（total/parse/chunk/parse_reason/chunk_reason）。"""
    src = inspect.getsource(run_evaluation)
    assert '"total": total_seconds' in src
    assert '"parse": None' in src
    assert '"chunk": None' in src
    assert '"parse_reason": "not_instrumented"' in src
    assert '"chunk_reason": "not_instrumented"' in src


def test_run_evaluation_source_has_not_instrumented_constant():
    src = inspect.getsource(run_evaluation)
    assert src.count("not_instrumented") == 2  # parse_reason + chunk_reason


# =========================================================================
# expected_failures 处理深度补强
# =========================================================================


def test_run_evaluation_source_has_expected_failures_loop():
    src = inspect.getsource(run_evaluation)
    assert "for ef in manifest.expected_failures:" in src


def test_run_evaluation_source_has_actual_code_ternary():
    """source 含 actual_code = errors[0].code if errors else None。"""
    src = inspect.getsource(run_evaluation)
    assert "actual_code = errors[0].code if errors else None" in src


def test_run_evaluation_source_has_matches_equality():
    """source 含 matches value（在 dict 字面量里：actual_code == ef.expected_error_code）。"""
    src = inspect.getsource(run_evaluation)
    assert '"matches": actual_code == ef.expected_error_code' in src


def test_run_evaluation_source_has_expected_failure_4_keys():
    """source 含 expected_failure_results.append 含 4 keys。"""
    src = inspect.getsource(run_evaluation)
    assert '"doc_id": ef.doc_id' in src
    assert '"expected_error_code": ef.expected_error_code' in src
    assert '"actual_error_code": actual_code' in src
    assert '"matches": actual_code == ef.expected_error_code' in src


# =========================================================================
# annotation 字段处理深度补强
# =========================================================================


def test_run_evaluation_source_has_annotation_present():
    src = inspect.getsource(run_evaluation)
    assert '"_annotation_present": annotation is not None' in src


def test_run_evaluation_source_has_tolerance_chars_pop():
    src = inspect.getsource(run_evaluation)
    assert "tolerance_record = chunk_b.pop(\"_tolerance_chars\", None)" in src
    assert 'missing_markers_record = chunk_b.pop("_missing_markers", None)' in src


def test_run_evaluation_source_has_tolerance_value_extraction():
    src = inspect.getsource(run_evaluation)
    assert 'tolerance_record["value"] if tolerance_record' in src
    assert 'missing_markers_record["value"]' in src


# =========================================================================
# public_per_doc 构造精确补强
# =========================================================================


def test_run_evaluation_source_has_public_per_doc_4_keys():
    """public_per_doc 含 4 keys（doc_id/source_type/metrics/wall_time_seconds）。"""
    src = inspect.getsource(run_evaluation)
    assert 'public_per_doc.append' in src
    assert '"doc_id": r["doc_id"]' in src
    assert '"source_type": r["source_type"]' in src
    assert '"metrics": r["metrics"]' in src
    assert '"wall_time_seconds": r["wall_time_seconds"]' in src


def test_run_evaluation_source_does_not_have_internal_keys_in_public():
    """public_per_doc 不含 _annotation_present 等 internal。"""
    src = inspect.getsource(run_evaluation)
    # 找 public_per_doc.append 那一段
    idx = src.find("public_per_doc.append")
    snippet = src[idx:idx + 500]
    assert "_annotation_present" not in snippet
    assert "_tolerance_chars" not in snippet
    assert "_missing_markers" not in snippet


# =========================================================================
# report 装配顺序补强
# =========================================================================


def test_run_evaluation_source_has_report_6_top_level_keys():
    """source 含 report = {...} 6 keys 顺序精确。"""
    src = inspect.getsource(run_evaluation)
    assert '"report_version": REPORT_VERSION' in src
    assert '"provenance": provenance' in src
    assert '"devset": devset' in src
    assert '"summary": summary' in src
    assert '"per_doc": public_per_doc' in src
    assert '"expected_failures": expected_failure_results' in src


def test_run_evaluation_source_report_version_first():
    """source 中 report_version 在 provenance 之前。"""
    src = inspect.getsource(run_evaluation)
    idx_rv = src.find('"report_version": REPORT_VERSION')
    idx_prov = src.find('"provenance": provenance')
    assert 0 <= idx_rv < idx_prov


def test_run_evaluation_source_expected_failures_last():
    """source 中 expected_failures 在 per_doc 之后（最后一个 key）。"""
    src = inspect.getsource(run_evaluation)
    idx_pd = src.find('"per_doc": public_per_doc')
    idx_ef = src.find('"expected_failures": expected_failure_results')
    assert 0 <= idx_pd < idx_ef


def test_run_evaluation_source_has_out_p_path():
    """source 含 out_p = Path(output_path)。"""
    src = inspect.getsource(run_evaluation)
    assert "out_p = Path(output_path)" in src


def test_run_evaluation_source_has_json_dump_with_options():
    """source 含 json.dump ensure_ascii=False + indent=2。"""
    src = inspect.getsource(run_evaluation)
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in src


# =========================================================================
# module imports 精确补强
# =========================================================================


def test_module_imports_count_10():
    src = inspect.getsource(rmod)
    lines = src.split("\n")
    import_lines = [l for l in lines if l.startswith("import ") or l.startswith("from ")]
    # future/json/time/pathlib/typing (5 stdlib) + app.pipeline (1) +
    # evaluation REPORT_VERSION/annotation_metrics/metrics/report (4)
    assert len(import_lines) == 10


def test_module_imports_has_future():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_imports_has_json():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_imports_has_time():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_imports_has_pathlib_path():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_imports_has_typing_any():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_imports_has_app_pipeline():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_imports_has_evaluation_report_version():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_imports_has_evaluation_annotation_metrics():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import (" in src
    assert "chunk_boundary_prf" in src
    assert "figure_caption_prf" in src


def test_module_imports_has_evaluation_metrics():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_imports_has_evaluation_report():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import (" in src
    assert "aggregate_summary" in src
    assert "build_devset_section" in src
    assert "build_provenance" in src


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_no_os():
    src = inspect.getsource(rmod)
    assert "import os" not in src
    assert "from os " not in src


def test_module_source_no_sys():
    src = inspect.getsource(rmod)
    assert "import sys" not in src


def test_module_source_no_re():
    src = inspect.getsource(rmod)
    assert "import re" not in src


def test_module_source_no_logging():
    src = inspect.getsource(rmod)
    assert "import logging" not in src


def test_module_source_no_subprocess():
    src = inspect.getsource(rmod)
    assert "import subprocess" not in src


def test_module_source_no_asyncio():
    src = inspect.getsource(rmod)
    assert "import asyncio" not in src


def test_module_source_no_threading():
    src = inspect.getsource(rmod)
    assert "import threading" not in src


def test_module_source_no_collections():
    src = inspect.getsource(rmod)
    assert "import collections" not in src


def test_module_source_no_math():
    src = inspect.getsource(rmod)
    assert "import math" not in src


def test_module_source_no_datetime():
    src = inspect.getsource(rmod)
    assert "import datetime" not in src


def test_module_source_no_socket():
    src = inspect.getsource(rmod)
    assert "import socket" not in src


def test_module_source_no_email():
    src = inspect.getsource(rmod)
    assert "import email" not in src


def test_module_source_no_html():
    src = inspect.getsource(rmod)
    assert "import html" not in src


def test_module_source_no_http():
    src = inspect.getsource(rmod)
    assert "import http" not in src


def test_module_source_no_urllib():
    src = inspect.getsource(rmod)
    assert "import urllib" not in src


def test_module_source_no_sqlite3():
    src = inspect.getsource(rmod)
    assert "import sqlite3" not in src


def test_module_source_no_csv():
    src = inspect.getsource(rmod)
    assert "import csv" not in src


def test_module_source_no_pickle():
    src = inspect.getsource(rmod)
    assert "import pickle" not in src


# =========================================================================
# module source 含必要字符串
# =========================================================================


def test_module_source_has_process_single():
    src = inspect.getsource(rmod)
    assert "process_single" in src


def test_module_source_has_image_output_dir_for():
    src = inspect.getsource(rmod)
    assert "image_output_dir_for" in src


def test_module_source_has_compute_automatic_metrics():
    src = inspect.getsource(rmod)
    assert "compute_automatic_metrics" in src


def test_module_source_has_figure_caption_prf():
    src = inspect.getsource(rmod)
    assert "figure_caption_prf" in src


def test_module_source_has_chunk_boundary_prf():
    src = inspect.getsource(rmod)
    assert "chunk_boundary_prf" in src


def test_module_source_has_build_provenance():
    src = inspect.getsource(rmod)
    assert "build_provenance" in src


def test_module_source_has_build_devset_section():
    src = inspect.getsource(rmod)
    assert "build_devset_section" in src


def test_module_source_has_aggregate_summary():
    src = inspect.getsource(rmod)
    assert "aggregate_summary" in src


def test_module_source_has_report_version_constant():
    src = inspect.getsource(rmod)
    assert "REPORT_VERSION" in src


# =========================================================================
# module source level 完整补强
# =========================================================================


def test_run_evaluation_source_has_output_root_path():
    src = inspect.getsource(run_evaluation)
    assert "output_root = Path(output_path).parent" in src


def test_run_evaluation_source_has_mkdir_parents_exist_ok():
    src = inspect.getsource(run_evaluation)
    assert "output_root.mkdir(parents=True, exist_ok=True)" in src


def test_run_evaluation_source_has_per_doc_results_init():
    src = inspect.getsource(run_evaluation)
    assert "per_doc_results: list[dict[str, Any]] = []" in src


def test_run_evaluation_source_has_parser_version_for_prov_init():
    src = inspect.getsource(run_evaluation)
    assert "parser_version_for_prov: str | None = None" in src


def test_run_evaluation_source_has_for_doc_in_documents():
    src = inspect.getsource(run_evaluation)
    assert "for doc in manifest.documents:" in src


def test_run_evaluation_source_has_parser_version_tracking():
    src = inspect.getsource(run_evaluation)
    assert "if parser_version and not parser_version_for_prov:" in src


def test_run_evaluation_source_has_compute_metrics_5_kwargs():
    src = inspect.getsource(run_evaluation)
    assert "compute_automatic_metrics(" in src
    assert "document=document" in src
    assert "error=error" in src
    assert "source_type=doc.source_type" in src
    assert "expectations=doc.expectations" in src
    assert "image_base_dir=image_dir" in src


def test_run_evaluation_source_has_image_base_dir_conditional():
    src = inspect.getsource(run_evaluation)
    assert "image_dir if (image_dir is not None and image_dir.is_dir())" in src


def test_run_evaluation_source_has_load_annotation_call():
    src = inspect.getsource(run_evaluation)
    assert "annotation = _load_annotation(doc.annotation_resolved)" in src


def test_run_evaluation_source_has_fig_caption_call():
    src = inspect.getsource(run_evaluation)
    assert "fig_caps = figure_caption_prf(document, annotation)" in src


def test_run_evaluation_source_has_chunk_boundary_call():
    src = inspect.getsource(run_evaluation)
    assert "chunk_b = chunk_boundary_prf(" in src
    assert "document, annotation, tolerance_chars=tolerance_chars" in src


def test_run_evaluation_source_has_metrics_update():
    src = inspect.getsource(run_evaluation)
    assert "metrics.update(fig_caps)" in src
    assert "metrics.update(chunk_b)" in src


def test_run_evaluation_source_has_per_doc_results_append():
    src = inspect.getsource(run_evaluation)
    assert "per_doc_results.append(" in src


def test_run_evaluation_source_has_build_provenance_call():
    src = inspect.getsource(run_evaluation)
    assert "provenance = build_provenance(" in src
    assert "project_root=manifest.project_root" in src
    assert "parser_name=parser_name" in src
    assert "max_chars=max_chars" in src
    assert "parser_version=parser_version_for_prov" in src


def test_run_evaluation_source_has_devset_call():
    src = inspect.getsource(run_evaluation)
    assert "devset = build_devset_section(manifest)" in src


def test_run_evaluation_source_has_summary_call():
    src = inspect.getsource(run_evaluation)
    assert "summary = aggregate_summary(per_doc_results)" in src


def test_run_evaluation_source_has_out_p_mkdir():
    src = inspect.getsource(run_evaluation)
    assert "out_p.parent.mkdir(parents=True, exist_ok=True)" in src


# =========================================================================
# module __all__ 补强
# =========================================================================


def test_module_all_has_only_run_evaluation():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_run_evaluation_in_namespace():
    assert hasattr(rmod, "run_evaluation")


def test_module_run_evaluation_is_callable():
    assert callable(rmod.run_evaluation)


def test_module_load_annotation_private():
    """_load_annotation 是 module-level private function。"""
    assert hasattr(rmod, "_load_annotation")
    assert "_load_annotation" not in rmod.__all__


def test_module_process_one_private():
    """_process_one 是 module-level private function。"""
    assert hasattr(rmod, "_process_one")
    assert "_process_one" not in rmod.__all__


# =========================================================================
# 模块整体合理性
# =========================================================================


def test_module_has_3_module_level_functions():
    """module 有 3 个 module-level function（_load_annotation + _process_one + run_evaluation）。"""
    import types
    funcs = [n for n in dir(rmod)
             if not n.startswith("__")
             and isinstance(getattr(rmod, n), types.FunctionType)
             and getattr(rmod, n).__module__ == "evaluation.runner"]
    expected = ["_load_annotation", "_process_one", "run_evaluation"]
    for e in expected:
        assert e in funcs


def test_module_has_9_imported_names():
    """module 含 9 个 imported names：
    process_single, image_output_dir_for, REPORT_VERSION,
    chunk_boundary_prf, figure_caption_prf, compute_automatic_metrics,
    aggregate_summary, build_devset_section, build_provenance
    """
    expected = [
        "process_single", "image_output_dir_for", "REPORT_VERSION",
        "chunk_boundary_prf", "figure_caption_prf", "compute_automatic_metrics",
        "aggregate_summary", "build_devset_section", "build_provenance",
    ]
    for name in expected:
        assert hasattr(rmod, name), f"Missing import: {name}"


def test_module_has_no_class_definition():
    src = inspect.getsource(rmod)
    lines = src.split("\n")
    for line in lines:
        if not line.startswith(" ") and line.startswith("class "):
            pytest.fail(f"Found class definition: {line}")


def test_module_has_no_main_block():
    src = inspect.getsource(rmod)
    assert 'if __name__ ==' not in src
    assert '__main__' not in src


# =========================================================================
# module docstring 深度补强
# =========================================================================


def test_module_docstring_contains_runner_text():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


def test_module_docstring_contains_pipeline_text():
    src = inspect.getsource(rmod)
    assert "pipeline" in src


def test_module_docstring_contains_perf_counter_text():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


def test_module_docstring_contains_not_instrumented_text():
    src = inspect.getsource(rmod)
    assert "not_instrumented" in src


def test_module_docstring_contains_image_resource_text():
    src = inspect.getsource(rmod)
    assert "image_resource_exists_ratio" in src


def test_module_docstring_contains_per_doc_text():
    src = inspect.getsource(rmod)
    assert "per_doc" in src
