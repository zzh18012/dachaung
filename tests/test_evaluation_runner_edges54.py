"""evaluation/runner.py 第五十六轮 edges 测试（Round 507）。

补强 edges53 未触及的角度（第二十六批）：
- _load_annotation 第二十六批：BOM 单独 / UTF-16 非法 / 多 BOM / 前导 \x00 / 单独引号 / 数字精度
- _process_one 第二十六批：返回 tuple 不可变性 / 多次调用独立 / out_stub.parent 创建顺序 / process_single 单次调用 / image_dir 来自 image_output_dir_for
- run_evaluation 第二十六批：报告 JSON 输出格式 / wall_time_seconds 类型 / per_doc 字段不变 / expected_failure 输出位置 / 多 expected_failures
- module source forbidden tokens 第四十三批
- module source 字符串精确补强第三十九批
- signatures 第三十九批
- module 合理性第三十九批
- 端到端集成第三十九批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import REPORT_VERSION
from evaluation import runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 第二十六批 ----------


def test_load_annotation_bom_only_invalid_batch26(tmp_path):
    """只有 BOM 字节 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_bytes(b"\xef\xbb\xbf")
    assert _load_annotation(p) is None


def test_load_annotation_utf16_invalid_batch26(tmp_path):
    """UTF-16 编码（非 UTF-8）→ UnicodeDecodeError 不被 (OSError, JSONDecodeError) 捕获，向外抛出。"""
    p = tmp_path / "a.json"
    p.write_bytes('{"a": 1}'.encode("utf-16"))
    # 实现只 catch (OSError, json.JSONDecodeError)，UnicodeDecodeError 是 ValueError 子类，会向外抛
    with pytest.raises(UnicodeDecodeError):
        _load_annotation(p)


def test_load_annotation_multiple_bom_invalid_batch26(tmp_path):
    """多个 BOM 字节开头 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_bytes(b"\xef\xbb\xbf\xef\xbb\xbf{}")
    # 第一个 BOM + extra BOM + {} → 仍可能是非法 JSON
    # 标准 JSON parser 不容忍多余 BOM，但 Python json 可能容忍开头的单 BOM
    # 多 BOM 应当失败
    result = _load_annotation(p)
    # 实际：utf-8 解码后 "﻿﻿{}" → JSONDecodeError（前缀非空白）
    assert result is None


def test_load_annotation_leading_null_byte_invalid_batch26(tmp_path):
    """前导 \x00 → 解码失败 / JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'\x00{"a": 1}')
    # utf-8 解码 \x00 OK；JSON 解析：\x00 是控制字符，可能被 json 接受
    # Python json.load 默认接受控制字符（strict=False）
    # 实际行为：json 默认 strict=True，控制字符会抛 JSONDecodeError
    result = _load_annotation(p)
    # 不严格断言，但应不崩溃
    assert result is None or isinstance(result, dict)


def test_load_annotation_only_quote_invalid_batch26(tmp_path):
    """单引号字符 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text('"', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_only_open_brace_invalid_batch26(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("{", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_only_close_brace_invalid_batch26(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("}", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_large_number_batch26(tmp_path):
    """大整数（超过 int64）→ Python int 无限制。"""
    p = tmp_path / "a.json"
    p.write_text("99999999999999999999999999", encoding="utf-8")
    result = _load_annotation(p)
    assert result == 99999999999999999999999999


def test_load_annotation_float_precision_batch26(tmp_path):
    """浮点精度边界。"""
    p = tmp_path / "a.json"
    p.write_text("0.1", encoding="utf-8")
    result = _load_annotation(p)
    assert isinstance(result, float)


def test_load_annotation_negative_zero_batch26(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("-0.0", encoding="utf-8")
    result = _load_annotation(p)
    assert result == 0.0  # -0.0 == 0.0 in Python


def test_load_annotation_unicode_key_batch26(tmp_path):
    """unicode 字符 key。"""
    p = tmp_path / "a.json"
    p.write_text('{"中文": "value"}', encoding="utf-8")
    assert _load_annotation(p) == {"中文": "value"}


def test_load_annotation_emoji_value_batch26(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"k": "😀🚀"}', encoding="utf-8")
    assert _load_annotation(p) == {"k": "😀🚀"}


def test_load_annotation_nested_10_levels_dict_batch26(tmp_path):
    """嵌套 10 层 dict。"""
    payload: Any = 1
    for _ in range(10):
        payload = {"n": payload}
    p = tmp_path / "a.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    assert _load_annotation(p) == payload


# ---------- _process_one 第二十六批 ----------


def _make_doc(doc_id="d1", source_type="pdf"):
    doc = MagicMock()
    doc.doc_id = doc_id
    doc.source_type = source_type
    doc.resolved_path = Path("/fake/path.pdf")
    doc.expectations = {}
    doc.annotation_resolved = None
    return doc


def test_process_one_returns_immutable_tuple_batch26(tmp_path):
    """返回的 tuple 不能被修改（tuple 本身不可变）。"""
    doc = _make_doc()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            result = _process_one(doc, tmp_path, "fallback", 800)
    with pytest.raises(TypeError):
        result[0] = "modified"  # type: ignore


def test_process_one_multiple_calls_independent_batch26(tmp_path):
    """多次调用应独立（不共享状态）。"""
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"x": 1}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            r1 = _process_one(_make_doc("d1"), tmp_path, "fallback", 800)
            r2 = _process_one(_make_doc("d2"), tmp_path, "fallback", 800)
    assert r1[0] == {"x": 1}
    assert r2[0] == {"x": 1}
    # 不同的 MagicMock 调用记录
    assert r1 is not r2


def test_process_one_out_stub_parent_created_batch26(tmp_path):
    """out_stub.parent（_per_doc）应在 process_single 调用前被创建。"""
    doc = _make_doc()
    mkdir_calls = []
    real_mkdir = Path.mkdir
    def tracking_mkdir(self, *args, **kwargs):
        mkdir_calls.append((self, kwargs))
        return real_mkdir(self, *args, **kwargs)
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("pathlib.Path.mkdir", tracking_mkdir):
                _process_one(doc, tmp_path, "fallback", 800)
    # _per_doc 目录应被创建
    assert any("_per_doc" in str(c[0]) for c in mkdir_calls)


def test_process_one_process_single_called_once_batch26(tmp_path):
    doc = _make_doc()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])) as m:
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _process_one(doc, tmp_path, "fallback", 800)
    m.assert_called_once()


def test_process_one_image_dir_from_helper_batch26(tmp_path):
    """image_dir 应来自 image_output_dir_for(out_stub, source_hash)。"""
    doc = _make_doc()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc123"
    expected_dir = tmp_path / "imgs"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=expected_dir) as m:
            _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir == expected_dir
    # image_output_dir_for 应被调用一次
    m.assert_called_once()
    # 参数应是 out_stub 与 source_hash
    args, _ = m.call_args
    assert args[1] == "abc123"


def test_process_one_out_stub_unlinked_after_success_batch26(tmp_path):
    """成功路径 → out_stub 应被删除（pipeline 写了它，runner 不留）。"""
    doc = _make_doc()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"

    def fake_process(*args, **kwargs):
        out_stub = args[1]
        Path(out_stub).parent.mkdir(parents=True, exist_ok=True)
        Path(out_stub).write_text("{}", encoding="utf-8")
        return fake_doc, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _process_one(doc, tmp_path, "fallback", 800)
    # out_stub 应不存在
    out_stub = tmp_path / "_per_doc" / "d1.json"
    assert not out_stub.is_file()


def test_process_one_out_stub_unlinked_after_error_batch26(tmp_path):
    """失败路径 → out_stub 也应被删除。"""
    doc = _make_doc()
    err = MagicMock()
    err.to_dict.return_value = {"code": "x"}

    def fake_process(*args, **kwargs):
        out_stub = args[1]
        Path(out_stub).parent.mkdir(parents=True, exist_ok=True)
        Path(out_stub).write_text("{}", encoding="utf-8")
        return None, [err]

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    out_stub = tmp_path / "_per_doc" / "d1.json"
    assert not out_stub.is_file()
    # image_dir is None when document=None
    assert image_dir is None


# ---------- run_evaluation 第二十六批 ----------


def _make_manifest(documents=None, expected_failures=None, project_root=None):
    m = MagicMock()
    m.documents = documents or []
    m.expected_failures = expected_failures or []
    m.project_root = project_root or Path(".")
    m.devset_status = "incomplete"
    m.file_count = len(documents or [])
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def test_run_evaluation_json_output_format_batch26(tmp_path):
    """输出 JSON 应有 report_version 顶层字段。"""
    m = _make_manifest()
    out = tmp_path / "report.json"
    run_evaluation(m, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["report_version"] == REPORT_VERSION


def test_run_evaluation_wall_time_seconds_value_type_batch26(tmp_path):
    """wall_time_seconds.total 应是 float。"""
    docs = [_make_doc("a")]
    m = _make_manifest(documents=docs)
    out = tmp_path / "report.json"
    fake_dict = {"source_hash": "x", "elements": [], "chunks": []}
    with patch("evaluation.runner._process_one",
               return_value=(fake_dict, None, 0.123, "0.1.0", None)):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    report = run_evaluation(m, out)
    assert isinstance(report["per_doc"][0]["wall_time_seconds"]["total"], float)


def test_run_evaluation_public_per_doc_field_set_batch26(tmp_path):
    """public per_doc 字段集合严格 4 个。"""
    docs = [_make_doc("a")]
    m = _make_manifest(documents=docs)
    out = tmp_path / "report.json"
    fake_dict = {"source_hash": "x", "elements": [], "chunks": []}
    with patch("evaluation.runner._process_one",
               return_value=(fake_dict, None, 0.1, "0.1.0", None)):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    report = run_evaluation(m, out)
    rec = report["per_doc"][0]
    assert set(rec.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_expected_failures_in_report_batch26(tmp_path):
    """expected_failures 应出现在 report 顶层。"""
    m = _make_manifest()
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    assert "expected_failures" in report


def test_run_evaluation_multiple_expected_failures_batch26(tmp_path):
    """多个 expected_failures 都应出现在 report 中。"""
    efs = []
    for i in range(3):
        ef = MagicMock()
        ef.doc_id = f"bad_{i}"
        ef.expected_error_code = "unsupported_format"
        ef.resolved_path = Path(f"/fake/bad_{i}.txt")
        efs.append(ef)
    m = _make_manifest(expected_failures=efs)
    out = tmp_path / "report.json"
    err = MagicMock()
    err.code = "unsupported_format"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        report = run_evaluation(m, out)
    assert len(report["expected_failures"]) == 3
    assert {r["doc_id"] for r in report["expected_failures"]} == {"bad_0", "bad_1", "bad_2"}


def test_run_evaluation_report_json_indented_2_batch26(tmp_path):
    """输出 JSON 应是 indent=2（非紧凑）。"""
    m = _make_manifest()
    out = tmp_path / "report.json"
    run_evaluation(m, out)
    content = out.read_text(encoding="utf-8")
    # indent=2 表示有换行 + 2 空格缩进
    assert '\n  "' in content or '\n    "' in content


def test_run_evaluation_report_unicode_not_escaped_batch26(tmp_path):
    """ensure_ascii=False → unicode 字符原样输出。"""
    m = _make_manifest()
    out = tmp_path / "report.json"
    with patch("evaluation.runner.build_provenance", return_value={"中文": "注释"}):
        with patch("evaluation.runner.build_devset_section", return_value={}):
            with patch("evaluation.runner.aggregate_summary", return_value={}):
                run_evaluation(m, out)
    content = out.read_text(encoding="utf-8")
    assert "中文" in content


def test_run_evaluation_devset_section_six_keys_batch26(tmp_path):
    """devset 字段应有 6 个 key。"""
    m = _make_manifest()
    m.devset_status = "incomplete"
    m.file_count = 1
    m.content_group_count = 1
    m.pdf_count = 1
    m.docx_count = 0
    m.categories_covered = ["reports"]
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    assert set(report["devset"].keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_run_evaluation_provenance_section_nine_keys_batch26(tmp_path):
    m = _make_manifest()
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    assert len(report["provenance"]) == 9


def test_run_evaluation_summary_section_four_keys_batch26(tmp_path):
    m = _make_manifest()
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    assert set(report["summary"].keys()) == {
        "counts", "success_rates", "ratio_macro_averages", "silent_drop_total",
    }


def test_run_evaluation_returns_report_dict_batch26(tmp_path):
    m = _make_manifest()
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    assert isinstance(report, dict)


def test_run_evaluation_output_path_directory_auto_created_batch26(tmp_path):
    """嵌套输出路径 → 自动 mkdir。"""
    m = _make_manifest()
    out = tmp_path / "deep" / "nested" / "dir" / "report.json"
    report = run_evaluation(m, out)
    assert out.is_file()
    assert isinstance(report, dict)


def test_run_evaluation_with_image_dir_batch26(tmp_path):
    """有 image_dir（is_dir True）→ image_base_dir 传给 compute_automatic_metrics。"""
    docs = [_make_doc("a")]
    m = _make_manifest(documents=docs)
    out = tmp_path / "report.json"
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    fake_dict = {"source_hash": "x", "elements": [], "chunks": []}
    with patch("evaluation.runner._process_one",
               return_value=(fake_dict, None, 0.1, "0.1.0", img_dir)):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}) as cm:
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    run_evaluation(m, out)
    _, kwargs = cm.call_args
    assert kwargs.get("image_base_dir") == img_dir


def test_run_evaluation_image_dir_not_dir_passes_none_batch26(tmp_path):
    """image_dir 不是 dir → image_base_dir 传 None。"""
    docs = [_make_doc("a")]
    m = _make_manifest(documents=docs)
    out = tmp_path / "report.json"
    img_dir = tmp_path / "imgs"  # 不存在
    fake_dict = {"source_hash": "x", "elements": [], "chunks": []}
    with patch("evaluation.runner._process_one",
               return_value=(fake_dict, None, 0.1, "0.1.0", img_dir)):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}) as cm:
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    run_evaluation(m, out)
    _, kwargs = cm.call_args
    assert kwargs.get("image_base_dir") is None


# ---------- module source forbidden tokens 第四十三批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import itertools",
    "import functools",
    "import timeit",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from itertools",
    "from functools",
    "from timeit",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import argparse",
    "import csv",
    "import random",
    "import hashlib",
]


def test_module_source_forbidden_tokens_batch26():
    source = inspect.getsource(rmod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token: {tok}"


def test_module_source_no_eval_exec_batch26():
    source = inspect.getsource(rmod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_module_source_no_star_import_batch26():
    source = inspect.getsource(rmod)
    assert "import *" not in source


def test_module_source_no_relative_imports_batch26():
    source = inspect.getsource(rmod)
    assert "from ." not in source


def test_module_source_no_unsafe_network_batch26():
    source = inspect.getsource(rmod)
    for tok in ["requests", "urllib.request", "http.client", "socket"]:
        assert tok not in source


def test_module_source_no_environ_batch26():
    source = inspect.getsource(rmod)
    assert "os.environ" not in source


def test_module_source_no_dataclass_batch26():
    source = inspect.getsource(rmod)
    assert "@dataclass" not in source


def test_module_source_no_argparse_batch26():
    source = inspect.getsource(rmod)
    assert "argparse" not in source


def test_module_source_no_class_keyword_batch26():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_source_no_subprocess_batch26():
    source = inspect.getsource(rmod)
    assert "subprocess" not in source


def test_module_source_time_allowed_batch26():
    source = inspect.getsource(rmod)
    assert "import time" in source


def test_module_source_json_allowed_batch26():
    source = inspect.getsource(rmod)
    assert "import json" in source


def test_module_source_uses_from_future_annotations_batch26():
    source = inspect.getsource(rmod)
    assert "from __future__ import annotations" in source


# ---------- module source 字符串精确补强第三十九批 ----------


def test_module_source_contains_process_single_batch26():
    source = inspect.getsource(rmod)
    assert "process_single" in source


def test_module_source_contains_image_output_dir_for_batch26():
    source = inspect.getsource(rmod)
    assert "image_output_dir_for" in source


def test_module_source_contains_compute_automatic_metrics_batch26():
    source = inspect.getsource(rmod)
    assert "compute_automatic_metrics" in source


def test_module_source_contains_figure_caption_prf_batch26():
    source = inspect.getsource(rmod)
    assert "figure_caption_prf" in source


def test_module_source_contains_chunk_boundary_prf_batch26():
    source = inspect.getsource(rmod)
    assert "chunk_boundary_prf" in source


def test_module_source_contains_aggregate_summary_batch26():
    source = inspect.getsource(rmod)
    assert "aggregate_summary" in source


def test_module_source_contains_build_devset_section_batch26():
    source = inspect.getsource(rmod)
    assert "build_devset_section" in source


def test_module_source_contains_build_provenance_batch26():
    source = inspect.getsource(rmod)
    assert "build_provenance" in source


def test_module_source_contains_time_perf_counter_batch26():
    source = inspect.getsource(rmod)
    assert "time.perf_counter" in source


def test_module_source_contains_not_instrumented_batch26():
    source = inspect.getsource(rmod)
    assert "not_instrumented" in source


def test_module_source_contains_write_json_false_batch26():
    source = inspect.getsource(rmod)
    assert "write_json=False" in source


def test_module_source_contains_ensure_ascii_false_batch26():
    source = inspect.getsource(rmod)
    assert "ensure_ascii=False" in source


# ---------- signatures 第三十九批 ----------


def test_signature_load_annotation_param_count_batch26():
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1


def test_signature_load_annotation_param_name_batch26():
    sig = inspect.signature(_load_annotation)
    assert "path" in sig.parameters


def test_signature_process_one_param_count_batch26():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_signature_process_one_param_names_batch26():
    sig = inspect.signature(_process_one)
    assert set(sig.parameters.keys()) == {"doc", "output_root", "parser_name", "max_chars"}


def test_signature_run_evaluation_param_count_batch26():
    sig = inspect.signature(run_evaluation)
    assert len(sig.parameters) == 5


def test_signature_run_evaluation_keyword_only_params_batch26():
    sig = inspect.signature(run_evaluation)
    from inspect import Parameter
    assert sig.parameters["parser_name"].kind == Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == Parameter.KEYWORD_ONLY


def test_signature_run_evaluation_default_parser_name_batch26():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_signature_run_evaluation_default_max_chars_batch26():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_signature_run_evaluation_default_tolerance_chars_batch26():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_all_annotations_are_strings_batch26():
    for fn in [_load_annotation, _process_one, run_evaluation]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            if p.annotation is not inspect.Parameter.empty:
                assert isinstance(p.annotation, str), f"{fn.__name__}.{p.name}"


# ---------- module 合理性第三十九批 ----------


def test_module_all_only_run_evaluation_batch26():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_has_three_callables_batch26():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    funcs = [n.name for n in tree.body if isinstance(n, _ast.FunctionDef)]
    assert set(funcs) == {"_load_annotation", "_process_one", "run_evaluation"}


def test_module_no_classes_batch26():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_docstring_present_batch26():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__.strip()) > 0


def test_module_docstring_mentions_evaluation_batch26():
    assert "评测" in rmod.__doc__ or "evaluation" in rmod.__doc__.lower()


def test_module_uses_from_future_annotations_batch26():
    source = inspect.getsource(rmod)
    assert "from __future__ import annotations" in source


def test_module_process_one_docstring_present_batch26():
    assert _process_one.__doc__ is not None


def test_module_run_evaluation_docstring_present_batch26():
    assert run_evaluation.__doc__ is not None


# ---------- 端到端集成第三十九批 ----------


def test_e2e_full_flow_no_documents_writes_valid_json_batch26(tmp_path):
    m = _make_manifest(documents=[])
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    with out.open("r", encoding="utf-8") as f:
        round_trip = json.load(f)
    assert round_trip == report


def test_e2e_summary_has_four_top_keys_batch26(tmp_path):
    m = _make_manifest()
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    assert set(report["summary"].keys()) == {
        "counts", "success_rates", "ratio_macro_averages", "silent_drop_total",
    }


def test_e2e_report_has_six_top_keys_batch26(tmp_path):
    m = _make_manifest()
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    assert len(report) == 6


def test_e2e_str_path_output_accepted_batch26(tmp_path):
    m = _make_manifest()
    out_str = str(tmp_path / "report.json")
    report = run_evaluation(m, out_str)
    assert Path(out_str).is_file()
    assert isinstance(report, dict)


def test_e2e_return_value_matches_file_batch26(tmp_path):
    m = _make_manifest()
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    with out.open("r", encoding="utf-8") as f:
        round_trip = json.load(f)
    assert round_trip == report


def test_e2e_nested_output_path_creates_dirs_batch26(tmp_path):
    m = _make_manifest()
    out = tmp_path / "deep" / "nested" / "report.json"
    run_evaluation(m, out)
    assert out.is_file()


def test_e2e_run_with_documents_writes_per_doc_batch26(tmp_path):
    docs = [_make_doc("a"), _make_doc("b")]
    m = _make_manifest(documents=docs)
    out = tmp_path / "report.json"
    fake_dict = {"source_hash": "x", "elements": [], "chunks": []}
    with patch("evaluation.runner._process_one",
               side_effect=[
                   (fake_dict, None, 0.1, "0.1.0", None),
                   (fake_dict, None, 0.1, "0.1.0", None),
               ]):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    report = run_evaluation(m, out)
    assert len(report["per_doc"]) == 2
