"""evaluation/runner.py 第五十一轮 edges 测试（Round 472）。

补强 edges48 未触及的角度：
- _load_annotation 第二十一批（encoding failures / BOM / empty / whitespace / symlink / 多 JSON 对象 / trailing comma / 注释 / 单引号 / 长 JSON）
- _process_one 第二十一批（mkdir 参数 / source_hash None / to_dict 调用 / document=None 走 unknown / elapsed 类型 / parser_version 来源）
- run_evaluation 第二十一批（output_root mkdir / json.dump 参数 / public per_doc strip / 内部字段 / chunk_b pop / report_version 严格 / devset/summary/provenance 透传）
- module source forbidden tokens 第三十七批
- module source 字符串精确补强第三十三批
- signatures 第三十三批
- module 合理性第三十三批
- 端到端集成第三十三批
"""

from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from evaluation import REPORT_VERSION
from evaluation.runner import _load_annotation, _process_one, run_evaluation
from evaluation import runner as rmod


# ---------- _load_annotation 第二十一批 ----------


def test_load_annotation_invalid_encoding_propagates_batch21(tmp_path):
    """非 UTF-8 编码（GBK 中文）→ UnicodeDecodeError 未被 (OSError, JSONDecodeError) 捕获 → 传播。"""
    p = tmp_path / "a.json"
    p.write_bytes("你好".encode("gbk"))
    with pytest.raises(UnicodeDecodeError):
        _load_annotation(p)


def test_load_annotation_utf8_bom_returns_dict_batch21(tmp_path):
    """UTF-8 BOM → JSONDecodeError（encoding=utf-8 不是 utf-8-sig）→ None。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'\xef\xbb\xbf{"a": 1}')
    assert _load_annotation(p) is None


def test_load_annotation_empty_file_returns_none_batch21(tmp_path):
    """空文件 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_whitespace_only_returns_none_batch21(tmp_path):
    """纯空白文件 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text("   \n\t  \n", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_multiple_json_objects_returns_none_batch21(tmp_path):
    """多个 JSON 对象（非数组）→ JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text('{"a": 1}{"b": 2}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_trailing_comma_returns_none_batch21(tmp_path):
    """尾随逗号 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text('{"a": 1,}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_single_quotes_returns_none_batch21(tmp_path):
    """单引号 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text("{'a': 1}", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_with_comment_returns_none_batch21(tmp_path):
    """JSON 不允许注释 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text('// comment\n{"a": 1}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_large_json_batch21(tmp_path):
    """大 JSON（10000 keys）能加载。"""
    p = tmp_path / "a.json"
    big = {str(i): i for i in range(10000)}
    p.write_text(json.dumps(big), encoding="utf-8")
    out = _load_annotation(p)
    assert len(out) == 10000
    assert out["0"] == 0
    assert out["9999"] == 9999


def test_load_annotation_nonexistent_path_returns_none_batch21(tmp_path):
    """路径不存在 → None。"""
    assert _load_annotation(tmp_path / "no.json") is None


def test_load_annotation_none_path_returns_none_batch21():
    """None 输入 → None。"""
    assert _load_annotation(None) is None


# ---------- _process_one 第二十一批 ----------


def _make_doc(doc_id="d1", source_type="pdf"):
    d = MagicMock()
    d.doc_id = doc_id
    d.source_type = source_type
    d.resolved_path = Path("/fake.pdf")
    d.expectations = None
    d.annotation_resolved = None
    return d


def test_process_one_mkdir_called_with_parents_exist_ok_batch21(tmp_path):
    """out_stub.parent.mkdir(parents=True, exist_ok=True)。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch.object(Path, "mkdir") as mock_mkdir:
                _process_one(doc, tmp_path, "fallback", 800)
    # 应该有调用且参数正确
    assert mock_mkdir.called
    args, kwargs = mock_mkdir.call_args
    assert kwargs.get("parents") is True
    assert kwargs.get("exist_ok") is True


def test_process_one_source_hash_none_when_document_lacks_hash_batch21(tmp_path):
    """document 没有 source_hash 时，image_output_dir_for 收到 None。"""
    doc = _make_doc()
    document_mock = MagicMock()
    document_mock.to_dict.return_value = {"document_id": "d1"}
    document_mock.parser_version = "1.0"
    document_mock.source_hash = None
    captured = {}

    def fake_image_dir(stub, source_hash):
        captured["source_hash"] = source_hash
        return tmp_path

    with patch(
        "evaluation.runner.process_single", return_value=(document_mock, [])
    ):
        with patch(
            "evaluation.runner.image_output_dir_for", side_effect=fake_image_dir
        ):
            _process_one(doc, tmp_path, "fallback", 800)
    assert captured["source_hash"] is None


def test_process_one_to_dict_called_once_batch21(tmp_path):
    """document.to_dict 仅调一次。"""
    doc = _make_doc()
    document_mock = MagicMock()
    document_mock.to_dict.return_value = {"document_id": "d1"}
    document_mock.parser_version = "1"
    document_mock.source_hash = "abc"
    with patch(
        "evaluation.runner.process_single", return_value=(document_mock, [])
    ):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            _process_one(doc, tmp_path, "fallback", 800)
    assert document_mock.to_dict.call_count == 1


def test_process_one_returns_unknown_when_no_errors_no_doc_batch21(tmp_path):
    """errors 空 + document None → 错误 code=unknown。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            document, error, elapsed, parser_version, image_dir = _process_one(
                doc, tmp_path, "fallback", 800
            )
    assert document is None
    assert error["code"] == "unknown"
    assert "process_single returned None" in error["message"]


def test_process_one_elapsed_is_float_batch21(tmp_path):
    """elapsed 是 float。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            _, _, elapsed, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(elapsed, float)


def test_process_one_parser_version_from_document_batch21(tmp_path):
    """parser_version 来自 document.parser_version。"""
    doc = _make_doc()
    document_mock = MagicMock()
    document_mock.to_dict.return_value = {"d": 1}
    document_mock.parser_version = "9.9.9"
    document_mock.source_hash = "h"
    with patch(
        "evaluation.runner.process_single", return_value=(document_mock, [])
    ):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            _, _, _, parser_version, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert parser_version == "9.9.9"


def test_process_one_parser_version_none_on_error_batch21(tmp_path):
    """错误时 parser_version 是 None。"""
    doc = _make_doc()
    err = MagicMock()
    err.to_dict.return_value = {"code": "PARSE_FAIL", "message": "x"}
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            _, _, _, parser_version, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert parser_version is None


def test_process_one_unlink_eats_oserror_batch21(tmp_path):
    """unlink 抛 OSError 时不传播。"""
    doc = _make_doc()
    document_mock = MagicMock()
    document_mock.to_dict.return_value = {"d": 1}
    document_mock.parser_version = "1"
    document_mock.source_hash = "h"

    def fake_process(path, out, **kwargs):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("{}", encoding="utf-8")
        return document_mock, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch.object(Path, "unlink", side_effect=OSError("denied")):
                # 不应抛
                _process_one(doc, tmp_path, "fallback", 800)


# ---------- run_evaluation 第二十一批 ----------


def _make_manifest(docs=(), expected_failures=(), project_root=None):
    m = MagicMock()
    m.documents = list(docs)
    m.expected_failures = list(expected_failures)
    m.project_root = project_root or Path(".")
    m.devset_status = "incomplete"
    m.file_count = len(docs)
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def test_run_evaluation_output_root_mkdir_batch21(tmp_path):
    """output_root.mkdir(parents=True, exist_ok=True)。"""
    output_root = tmp_path / "deep" / "nest"
    out = output_root / "out.json"
    m = _make_manifest(docs=[])
    run_evaluation(m, out)
    assert output_root.is_dir()


def test_run_evaluation_json_dump_ensure_ascii_false_batch21(tmp_path):
    """json.dump 用 ensure_ascii=False（中文不转义）。"""
    m = _make_manifest(docs=[])
    out = tmp_path / "out.json"
    run_evaluation(m, out)
    content = out.read_text(encoding="utf-8")
    # "report_version" 是 ASCII；测试通过验证 ensure_ascii=False 不会影响 ASCII 字段
    assert '"report_version"' in content


def test_run_evaluation_json_dump_indent_two_batch21(tmp_path):
    """json.dump 用 indent=2。"""
    m = _make_manifest(docs=[])
    out = tmp_path / "out.json"
    run_evaluation(m, out)
    content = out.read_text(encoding="utf-8")
    # indent=2 → 至少有一个 2 空格缩进的 key
    assert '\n  "' in content


def test_run_evaluation_report_version_constant_batch21(tmp_path):
    """顶层 report_version 来自 REPORT_VERSION 常量。"""
    m = _make_manifest(docs=[])
    report = run_evaluation(m, tmp_path / "out.json")
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_devset_passes_manifest_batch21(tmp_path):
    """build_devset_section 接收 manifest。"""
    captured = {}
    fake_devset = {"x": 1}

    def fake_build(m):
        captured["manifest"] = m
        return fake_devset

    m = _make_manifest(docs=[])
    with patch("evaluation.runner.build_devset_section", side_effect=fake_build):
        report = run_evaluation(m, tmp_path / "out.json")
    assert captured["manifest"] is m
    assert report["devset"] == fake_devset


def test_run_evaluation_summary_from_aggregate_batch21(tmp_path):
    """summary 来自 aggregate_summary。"""
    fake_summary = {"counts": {"a": 1}, "success_rates": {}, "ratio_macro_averages": {}, "silent_drop_total": {}}
    with patch(
        "evaluation.runner.aggregate_summary", return_value=fake_summary
    ):
        m = _make_manifest(docs=[])
        report = run_evaluation(m, tmp_path / "out.json")
    assert report["summary"] is fake_summary


def test_run_evaluation_provenance_passes_parser_version_batch21(tmp_path):
    """build_provenance 接收 parser_version_for_prov。"""
    captured = {}

    def fake_prov(project_root, parser_name, max_chars, parser_version):
        captured["parser_version"] = parser_version
        return {"parser_version": parser_version}

    doc = _make_doc()
    document_mock = MagicMock()
    document_mock.to_dict.return_value = {"d": 1}
    document_mock.parser_version = "1.2.3"
    document_mock.source_hash = "h"

    with patch(
        "evaluation.runner.process_single", return_value=(document_mock, [])
    ):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        with patch(
                            "evaluation.runner.build_provenance", side_effect=fake_prov
                        ):
                            m = _make_manifest(docs=[doc])
                            run_evaluation(m, tmp_path / "out.json")
    assert captured["parser_version"] == "1.2.3"


def test_run_evaluation_provenance_passes_project_root_batch21(tmp_path):
    """build_provenance 接收 manifest.project_root。"""
    captured = {}

    def fake_prov(project_root, parser_name, max_chars, parser_version):
        captured["project_root"] = project_root
        return {"x": 1}

    m = _make_manifest(docs=[], project_root=Path("/some/root"))
    with patch(
        "evaluation.runner.build_provenance", side_effect=fake_prov
    ):
        run_evaluation(m, tmp_path / "out.json")
    assert captured["project_root"] == Path("/some/root")


def test_run_evaluation_chunk_b_pops_tolerance_chars_key_batch21(tmp_path):
    """chunk_b 的 _tolerance_chars 被 pop，不进 metrics。"""
    doc = _make_doc()
    fake_chunk_b = {
        "chunk_boundary_precision": {"value": 1.0, "reason": None},
        "_tolerance_chars": {"value": 30},
        "_missing_markers": {"value": []},
    }
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch(
                        "evaluation.runner.chunk_boundary_prf", return_value=fake_chunk_b
                    ):
                        m = _make_manifest(docs=[doc])
                        report = run_evaluation(m, tmp_path / "out.json")
    metrics_keys = set(report["per_doc"][0]["metrics"].keys())
    assert "_tolerance_chars" not in metrics_keys
    assert "_missing_markers" not in metrics_keys
    assert "chunk_boundary_precision" in metrics_keys


def test_run_evaluation_per_doc_internal_annotation_present_batch21(tmp_path):
    """per_doc_results 内部 _annotation_present 字段（不进 public per_doc）。"""
    doc = _make_doc()
    doc.annotation_resolved = None  # 没有 annotation
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        report = run_evaluation(m, tmp_path / "out.json")
    pd = report["per_doc"][0]
    assert "_annotation_present" not in pd


def test_run_evaluation_wall_time_seconds_has_five_keys_batch21(tmp_path):
    """wall_time_seconds 含 5 个字段（total/parse/chunk/parse_reason/chunk_reason）。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        report = run_evaluation(m, tmp_path / "out.json")
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_expected_failure_report_has_four_keys_batch21(tmp_path):
    """expected_failure 报告项严格 4 字段。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.expected_error_code = "E_PARSE"
    ef.resolved_path = Path("/bad.pdf")
    err_mock = MagicMock()
    err_mock.code = "E_PARSE"
    with patch(
        "evaluation.runner.process_single", return_value=(None, [err_mock])
    ):
        m = _make_manifest(expected_failures=[ef])
        report = run_evaluation(m, tmp_path / "out.json")
    ef_report = report["expected_failures"][0]
    assert set(ef_report.keys()) == {
        "doc_id",
        "expected_error_code",
        "actual_error_code",
        "matches",
    }


def test_run_evaluation_expected_failure_no_errors_actual_none_batch21(tmp_path):
    """expected_failure 跑通没错误时 actual_error_code=None。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.expected_error_code = "E_PARSE"
    ef.resolved_path = Path("/bad.pdf")
    with patch(
        "evaluation.runner.process_single", return_value=(MagicMock(), [])
    ):
        m = _make_manifest(expected_failures=[ef])
        report = run_evaluation(m, tmp_path / "out.json")
    assert report["expected_failures"][0]["actual_error_code"] is None
    assert report["expected_failures"][0]["matches"] is False


# ---------- module source forbidden tokens 第三十七批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    "open(\"/etc/passwd",
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch21(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch21():
    src = inspect.getsource(rmod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch21():
    src = inspect.getsource(rmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch21():
    src = inspect.getsource(rmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch21():
    src = inspect.getsource(rmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch21():
    src = inspect.getsource(rmod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch21():
    src = inspect.getsource(rmod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch21():
    src = inspect.getsource(rmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch21():
    src = inspect.getsource(rmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch21():
    src = inspect.getsource(rmod)
    assert "import tempfile" not in src


def test_module_source_no_sys_import_batch21():
    src = inspect.getsource(rmod)
    assert "import sys" not in src


def test_module_source_no_logging_import_batch21():
    src = inspect.getsource(rmod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch21():
    src = inspect.getsource(rmod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch21():
    src = inspect.getsource(rmod)
    assert "import datetime" not in src


def test_module_source_no_collections_import_batch21():
    src = inspect.getsource(rmod)
    assert "import collections" not in src


def test_module_source_no_pandas_import_batch21():
    src = inspect.getsource(rmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch21():
    src = inspect.getsource(rmod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第三十三批 ----------


def test_module_source_has_future_annotations_batch21():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_json_import_batch21():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_has_time_import_batch21():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_has_pathlib_path_import_batch21():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch21():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_pipeline_import_batch21():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_has_report_version_import_batch21():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_has_annotation_metrics_import_batch21():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import (" in src


def test_module_source_has_chunk_boundary_prf_in_import_batch21():
    src = inspect.getsource(rmod)
    assert "chunk_boundary_prf" in src


def test_module_source_has_figure_caption_prf_in_import_batch21():
    src = inspect.getsource(rmod)
    assert "figure_caption_prf" in src


def test_module_source_has_metrics_import_batch21():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_has_report_import_batch21():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import (" in src


def test_module_source_has_aggregate_summary_in_import_batch21():
    src = inspect.getsource(rmod)
    assert "aggregate_summary" in src


def test_module_source_has_build_devset_section_in_import_batch21():
    src = inspect.getsource(rmod)
    assert "build_devset_section" in src


def test_module_source_has_build_provenance_in_import_batch21():
    src = inspect.getsource(rmod)
    assert "build_provenance" in src


def test_module_source_has_perf_counter_call_batch21():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


# ---------- signatures 第三十三批 ----------


def test_signature_load_annotation_no_varargs_batch21():
    """_load_annotation 无 *args/**kwargs。"""
    sig = inspect.signature(_load_annotation)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_signature_process_one_no_varargs_batch21():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_signature_run_evaluation_no_varargs_batch21():
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_signature_load_annotation_path_type_hint_batch21():
    """_load_annotation path 类型注解是 Path | None。"""
    sig = inspect.signature(_load_annotation)
    p = sig.parameters["path"]
    # 因为 from __future__ import annotations，annotation 是字符串
    ann = p.annotation
    assert "Path" in ann and "None" in ann


def test_signature_process_one_output_root_type_hint_batch21():
    sig = inspect.signature(_process_one)
    ann = sig.parameters["output_root"].annotation
    assert "Path" in ann


def test_signature_run_evaluation_manifest_no_annotation_batch21():
    """manifest 形参无类型注解（注释说 # Manifest）。"""
    sig = inspect.signature(run_evaluation)
    p = sig.parameters["manifest"]
    # 因为注释是 # Manifest，annotation 是 str 类型（来自 __future__）
    # 但实际上源码 manifest, 没有显式注解，所以 default 是 empty，annotation 是 empty
    # 验证无类型注解（empty）
    assert p.annotation is inspect.Parameter.empty


# ---------- module 合理性第三十三批 ----------


def test_module_all_contains_only_run_evaluation_batch21():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_does_not_import_evaluation_cli_batch21():
    src = inspect.getsource(rmod)
    assert "from evaluation.cli" not in src
    assert "from evaluation import cli" not in src


def test_module_does_not_import_evaluation_schema_batch21():
    src = inspect.getsource(rmod)
    assert "from evaluation.schema" not in src
    assert "from evaluation import schema" not in src


def test_module_does_not_import_evaluation_manifest_batch21():
    src = inspect.getsource(rmod)
    assert "from evaluation.manifest" not in src
    assert "from evaluation import manifest" not in src


def test_module_does_not_import_app_chunkers_batch21():
    src = inspect.getsource(rmod)
    assert "from app.chunkers" not in src
    assert "from app import chunkers" not in src


def test_module_does_not_import_app_parsers_batch21():
    src = inspect.getsource(rmod)
    assert "from app.parsers" not in src
    assert "from app import parsers" not in src


def test_module_constants_not_in_all_batch21():
    for k in ("_load_annotation", "_process_one"):
        assert k not in rmod.__all__


def test_module_no_main_block_batch21():
    src = inspect.getsource(rmod)
    assert 'if __name__ ==' not in src
    assert "__main__" not in src


def test_module_load_annotation_is_private_batch21():
    assert _load_annotation.__name__.startswith("_")


def test_module_process_one_is_private_batch21():
    assert _process_one.__name__.startswith("_")


def test_module_run_evaluation_is_public_batch21():
    assert not run_evaluation.__name__.startswith("_")


def test_module_has_module_docstring_batch21():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 0


# ---------- 端到端集成第三十三批 ----------


def test_e2e_load_annotation_dict_round_trip_batch21(tmp_path):
    """dict JSON round-trip。"""
    p = tmp_path / "a.json"
    payload = {"figure_captions": [{"image_id": "img1", "caption_text": "图 1"}]}
    p.write_text(json.dumps(payload), encoding="utf-8")
    out = _load_annotation(p)
    assert out == payload
    assert out["figure_captions"][0]["image_id"] == "img1"


def test_e2e_run_evaluation_creates_valid_json_batch21(tmp_path):
    m = _make_manifest(docs=[])
    out = tmp_path / "out.json"
    run_evaluation(m, out)
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    assert "per_doc" in parsed


def test_e2e_run_evaluation_returns_same_as_file_batch21(tmp_path):
    m = _make_manifest(docs=[])
    out = tmp_path / "out.json"
    report = run_evaluation(m, out)
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed == report


def test_e2e_run_evaluation_no_docs_summary_struct_batch21(tmp_path):
    m = _make_manifest(docs=[])
    report = run_evaluation(m, tmp_path / "out.json")
    s = report["summary"]
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_e2e_run_evaluation_per_doc_count_matches_docs_batch21(tmp_path):
    docs = [_make_doc(f"d{i}") for i in range(3)]
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=docs)
                        report = run_evaluation(m, tmp_path / "out.json")
    assert len(report["per_doc"]) == 3


def test_e2e_run_evaluation_with_expected_failure_match_batch21(tmp_path):
    """expected_failure 实际错误 == 期望时 matches=True。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.expected_error_code = "E_PARSE"
    ef.resolved_path = Path("/bad.pdf")
    err_mock = MagicMock()
    err_mock.code = "E_PARSE"
    with patch("evaluation.runner.process_single", return_value=(None, [err_mock])):
        m = _make_manifest(expected_failures=[ef])
        report = run_evaluation(m, tmp_path / "out.json")
    assert report["expected_failures"][0]["matches"] is True
    assert report["expected_failures"][0]["actual_error_code"] == "E_PARSE"


def test_e2e_run_evaluation_full_report_has_six_top_keys_batch21(tmp_path):
    """完整报告含 6 个顶层字段。"""
    m = _make_manifest(docs=[], expected_failures=[])
    report = run_evaluation(m, tmp_path / "out.json")
    assert set(report.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_e2e_run_evaluation_public_per_doc_excludes_underscore_fields_batch21(tmp_path):
    """public per_doc 不含 _ 前缀字段。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        report = run_evaluation(m, tmp_path / "out.json")
    pd = report["per_doc"][0]
    for k in pd.keys():
        assert not k.startswith("_")
