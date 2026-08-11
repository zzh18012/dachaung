"""evaluation/runner.py 第四十九轮 edges 测试（Round 459）。

补强 edges46 未触及的角度：
- _load_annotation 行为深度第十九批（json 解析失败 / 非对象 JSON / str path 等价 / Unicode 复杂内容 / 异常被吞）
- _process_one 行为深度第十九批（out_stub 路径结构 / 多 errors 取第一个 / document.parser_version passthrough / image_dir None when no document / unlink 失败被吞）
- run_evaluation 行为深度第十九批（metrics 含 figure_caption_* / metrics 含 chunk_boundary_* / per_doc 含 _annotation_present / per_doc 含 _tolerance_chars / per_doc 含 _missing_markers / public per_doc 排除 _ 前缀 / wall_time parse_reason 固定 not_instrumented / parser_version 来自第一个成功 doc / report_version 来自 REPORT_VERSION 常量）
- module source forbidden tokens 第三十四批
- module source 字符串精确补强第二十九批
- signatures 第二十九批
- module 合理性第二十九批
- 端到端集成第二十九批
"""

from __future__ import annotations

import inspect
import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import REPORT_VERSION
from evaluation.runner import _load_annotation, _process_one, run_evaluation
from evaluation import runner as rmod


# ---------- _load_annotation 行为深度第十九批 ----------


def test_load_annotation_with_string_path_batch19(tmp_path):
    """传 str 路径应抛 AttributeError（要求 Path）— _load_annotation 内部用 path.is_file()。"""
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    # str 没有 is_file 方法
    with pytest.raises(AttributeError):
        _load_annotation(str(p))


def test_load_annotation_path_is_none_returns_none_batch19():
    """None 直接返回 None。"""
    assert _load_annotation(None) is None


def test_load_annotation_path_not_exist_returns_none_batch19(tmp_path):
    assert _load_annotation(tmp_path / "missing.json") is None


def test_load_annotation_returns_dict_for_valid_batch19(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"k": 1}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": 1}


def test_load_annotation_returns_none_for_invalid_json_batch19(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("{not valid", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_returns_array_for_array_batch19(tmp_path):
    """JSON 数组不被 _load_annotation 拒绝（返回 list）。"""
    p = tmp_path / "a.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3]


def test_load_annotation_returns_none_for_oserror_batch19(tmp_path):
    """path.open 抛 OSError 时返回 None。"""
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    original_open = Path.open

    def fake_open(self, *args, **kwargs):
        raise OSError("simulated")

    with patch.object(Path, "open", fake_open):
        assert _load_annotation(p) is None


def test_load_annotation_unicode_content_batch19(tmp_path):
    """Unicode 内容应正确解析。"""
    p = tmp_path / "a.json"
    p.write_text('{"k": "中文测试"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": "中文测试"}


def test_load_annotation_utf8_bom_rejected_batch19(tmp_path):
    """UTF-8 BOM 导致 json.JSONDecodeError，被吞为 None。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'\xef\xbb\xbf{"k": 1}')
    # encoding="utf-8" 不剥 BOM，json 解析失败
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_nested_dict_batch19(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"a": {"b": {"c": [1, 2]}}}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": {"b": {"c": [1, 2]}}}


def test_load_annotation_empty_dict_batch19(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    assert _load_annotation(p) == {}


def test_load_annotation_empty_file_returns_none_batch19(tmp_path):
    """空文件 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


# ---------- _process_one 行为深度第十九批 ----------


def _make_doc(doc_id="d1", source_type="pdf"):
    """构造一个 mock DocumentEntry。"""
    d = MagicMock()
    d.doc_id = doc_id
    d.source_type = source_type
    d.resolved_path = Path("/fake.pdf")
    d.expectations = None
    d.annotation_resolved = None
    return d


def test_process_one_out_stub_under_per_doc_batch19(tmp_path):
    """out_stub 应位于 output_root/_per_doc/{doc_id}.json。"""
    doc = _make_doc("xyz")
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            _process_one(doc, tmp_path, "fallback", 800)
    # _per_doc 目录应被创建
    assert (tmp_path / "_per_doc").is_dir()


def test_process_one_errors_returns_first_error_dict_batch19(tmp_path):
    """errors 非空时返回 errors[0].to_dict()。"""
    doc = _make_doc()
    err1 = MagicMock()
    err1.to_dict.return_value = {"code": "E1", "message": "first"}
    err2 = MagicMock()
    err2.to_dict.return_value = {"code": "E2", "message": "second"}
    with patch("evaluation.runner.process_single", return_value=(None, [err1, err2])):
        document, error, elapsed, parser_version, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "E1", "message": "first"}


def test_process_one_no_document_no_errors_returns_unknown_batch19(tmp_path):
    """document is None 且 errors 空 → error code='unknown'。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        document, error, elapsed, parser_version, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error == {
        "code": "unknown",
        "message": "process_single returned None without errors",
    }
    assert parser_version is None


def test_process_one_document_returned_batch19(tmp_path):
    """成功路径返回 document.to_dict()。"""
    doc = _make_doc()
    document_mock = MagicMock()
    document_mock.to_dict.return_value = {"document_id": "d1"}
    document_mock.parser_version = "1.0.0"
    document_mock.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(document_mock, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            document, error, elapsed, parser_version, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document == {"document_id": "d1"}
    assert error is None
    assert parser_version == "1.0.0"
    assert image_dir == tmp_path / "imgs"


def test_process_one_image_dir_when_document_none_batch19(tmp_path):
    """document is None 时 image_dir 是 None。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        document, error, elapsed, parser_version, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None


def test_process_one_elapsed_non_negative_batch19(tmp_path):
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        document, error, elapsed, parser_version, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert elapsed >= 0


def test_process_one_calls_image_output_dir_for_only_when_doc_present_batch19(tmp_path):
    """document None 时不调 image_output_dir_for。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for") as mock_img:
            _process_one(doc, tmp_path, "fallback", 800)
    assert mock_img.call_count == 0


def test_process_one_unlink_oserror_swallowed_batch19(tmp_path):
    """out_stub.unlink 抛 OSError 被吞（不传播）。"""
    doc = _make_doc()
    # 构造一个文件存在但 unlink 抛错的场景
    out_stub = tmp_path / "_per_doc" / "d1.json"
    out_stub.parent.mkdir(parents=True, exist_ok=True)
    out_stub.write_text("{}", encoding="utf-8")
    original_unlink = Path.unlink

    def fake_unlink(self, *args, **kwargs):
        raise OSError("simulated")

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch.object(Path, "unlink", fake_unlink):
            # 不应抛错
            _process_one(doc, tmp_path, "fallback", 800)


# ---------- run_evaluation 行为深度第十九批 ----------


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


def test_run_evaluation_metrics_contain_figure_caption_batch19(tmp_path):
    """metrics 应含 figure_caption_* 三项。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={
                    "figure_caption_precision": {"value": None, "reason": "parser_does_not_emit_relations"},
                    "figure_caption_recall": {"value": None, "reason": "parser_does_not_emit_relations"},
                    "figure_caption_f1": {"value": None, "reason": "parser_does_not_emit_relations"},
                }):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}) as cb:
                        m = _make_manifest(docs=[doc])
                        report = run_evaluation(m, tmp_path / "out.json")
    metric_keys = set(report["per_doc"][0]["metrics"].keys())
    assert "figure_caption_precision" in metric_keys
    assert "figure_caption_recall" in metric_keys
    assert "figure_caption_f1" in metric_keys


def test_run_evaluation_metrics_contain_chunk_boundary_batch19(tmp_path):
    """metrics 应含 chunk_boundary_* 三项（如果 annotation_metrics 返回）。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={
                        "chunk_boundary_precision": {"value": 1.0, "reason": None},
                        "chunk_boundary_recall": {"value": 1.0, "reason": None},
                        "chunk_boundary_f1": {"value": 1.0, "reason": None},
                        "_tolerance_chars": {"value": 30},
                        "_missing_markers": {"value": []},
                    }):
                        m = _make_manifest(docs=[doc])
                        report = run_evaluation(m, tmp_path / "out.json")
    metric_keys = set(report["per_doc"][0]["metrics"].keys())
    assert "chunk_boundary_precision" in metric_keys
    assert "chunk_boundary_recall" in metric_keys
    assert "chunk_boundary_f1" in metric_keys


def test_run_evaluation_per_doc_results_internal_annotation_present_batch19(tmp_path):
    """internal per_doc_results 应含 _annotation_present 字段（但 public per_doc 不含）。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        report = run_evaluation(m, tmp_path / "out.json")
    # public per_doc 不含 _annotation_present
    pd = report["per_doc"][0]
    assert "_annotation_present" not in pd
    assert "doc_id" in pd
    assert "source_type" in pd
    assert "metrics" in pd
    assert "wall_time_seconds" in pd


def test_run_evaluation_wall_time_parse_chunk_reason_batch19(tmp_path):
    """wall_time 含 parse_reason / chunk_reason 固定 not_instrumented。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        report = run_evaluation(m, tmp_path / "out.json")
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_parser_version_from_first_success_batch19(tmp_path):
    """parser_version 取第一个成功的 document。"""
    doc1 = _make_doc("d1")
    doc2 = _make_doc("d2")

    def fake_process(path, out, **kwargs):
        d1 = MagicMock()
        d1.to_dict.return_value = {"document_id": "d1"}
        d1.parser_version = "1.0.0"
        d1.source_hash = "abc"
        return d1, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc1, doc2])
                        report = run_evaluation(m, tmp_path / "out.json")
    assert report["provenance"]["parser_version"] == "1.0.0"


def test_run_evaluation_no_docs_parser_version_none_batch19(tmp_path):
    """没有 doc 时 parser_version 为 None。"""
    m = _make_manifest(docs=[])
    report = run_evaluation(m, tmp_path / "out.json")
    assert report["provenance"]["parser_version"] is None


def test_run_evaluation_report_top_keys_exact_batch19(tmp_path):
    m = _make_manifest(docs=[])
    report = run_evaluation(m, tmp_path / "out.json")
    assert set(report.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_run_evaluation_report_version_matches_module_batch19(tmp_path):
    m = _make_manifest(docs=[])
    report = run_evaluation(m, tmp_path / "out.json")
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_per_doc_order_preserved_batch19(tmp_path):
    """per_doc 顺序与 manifest.documents 一致。"""
    doc1 = _make_doc("alpha")
    doc2 = _make_doc("beta")
    doc3 = _make_doc("gamma")
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc1, doc2, doc3])
                        report = run_evaluation(m, tmp_path / "out.json")
    assert [d["doc_id"] for d in report["per_doc"]] == ["alpha", "beta", "gamma"]


def test_run_evaluation_output_file_written_unicode_safe_batch19(tmp_path):
    """输出文件用 ensure_ascii=False，能写 Unicode。"""
    m = _make_manifest(docs=[])
    out_path = tmp_path / "out.json"
    report = run_evaluation(m, out_path)
    content = out_path.read_text(encoding="utf-8")
    # 应是合法 JSON
    parsed = json.loads(content)
    assert parsed == report


def test_run_evaluation_image_dir_used_as_image_base_dir_batch19(tmp_path):
    """image_dir 是目录时传给 compute_automatic_metrics 作为 image_base_dir。"""
    doc = _make_doc()
    captured = {}

    def fake_metrics(**kwargs):
        captured.update(kwargs)
        return {}

    with patch("evaluation.runner.process_single", return_value=(MagicMock(
        to_dict=lambda: {"d": 1},
        parser_version="1",
        source_hash="abc",
    ), [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            (tmp_path / "imgs").mkdir(parents=True, exist_ok=True)
            with patch("evaluation.runner.compute_automatic_metrics", side_effect=fake_metrics):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        run_evaluation(m, tmp_path / "out.json")
    assert captured.get("image_base_dir") == tmp_path / "imgs"


def test_run_evaluation_image_dir_skipped_when_not_dir_batch19(tmp_path):
    """image_dir 存在但不是目录时传 None。"""
    doc = _make_doc()
    captured = {}

    def fake_metrics(**kwargs):
        captured.update(kwargs)
        return {}

    with patch("evaluation.runner.process_single", return_value=(MagicMock(
        to_dict=lambda: {"d": 1},
        parser_version="1",
        source_hash="abc",
    ), [])):
        # image_dir 不存在
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "notexist"):
            with patch("evaluation.runner.compute_automatic_metrics", side_effect=fake_metrics):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        run_evaluation(m, tmp_path / "out.json")
    assert captured.get("image_base_dir") is None


def test_run_evaluation_expected_failures_in_report_batch19(tmp_path):
    """expected_failures 被写入报告。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.expected_error_code = "E_PARSE"
    ef.resolved_path = Path("/bad.pdf")

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        m = _make_manifest(expected_failures=[ef])
        report = run_evaluation(m, tmp_path / "out.json")
    assert report["expected_failures"][0]["doc_id"] == "ef1"
    assert report["expected_failures"][0]["expected_error_code"] == "E_PARSE"
    assert report["expected_failures"][0]["actual_error_code"] is None
    assert report["expected_failures"][0]["matches"] is False


def test_run_evaluation_returns_dict_batch19(tmp_path):
    m = _make_manifest(docs=[])
    report = run_evaluation(m, tmp_path / "out.json")
    assert isinstance(report, dict)


def test_run_evaluation_creates_output_parent_dir_batch19(tmp_path):
    """output_path 的 parent 目录被创建。"""
    out_path = tmp_path / "deep" / "nested" / "out.json"
    m = _make_manifest(docs=[])
    run_evaluation(m, out_path)
    assert out_path.is_file()


# ---------- module source forbidden tokens 第三十四批 ----------


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
def test_module_source_forbidden_tokens_batch19(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch19():
    src = inspect.getsource(rmod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch19():
    src = inspect.getsource(rmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch19():
    src = inspect.getsource(rmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch19():
    src = inspect.getsource(rmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch19():
    src = inspect.getsource(rmod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch19():
    src = inspect.getsource(rmod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch19():
    src = inspect.getsource(rmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch19():
    src = inspect.getsource(rmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch19():
    src = inspect.getsource(rmod)
    assert "import tempfile" not in src


def test_module_source_no_unlink_unsafe_path_batch19():
    """unlink 仅用于清理 _per_doc stub。"""
    src = inspect.getsource(rmod)
    # 允许 unlink() 但不应有 unlink(/etc) 这种
    assert 'unlink("/' not in src


def test_module_source_no_path_rmdir_call_batch19():
    src = inspect.getsource(rmod)
    assert ".rmdir(" not in src


def test_module_source_no_path_mkdir_unsafe_batch19():
    """mkdir 仅用于 output_root。"""
    src = inspect.getsource(rmod)
    assert ".mkdir(" in src  # 合法用法
    assert 'mkdir("/' not in src


def test_module_source_no_sys_exit_batch19():
    src = inspect.getsource(rmod)
    assert "sys.exit" not in src


def test_module_source_no_re_compile_batch19():
    src = inspect.getsource(rmod)
    assert "re.compile" not in src


def test_module_source_no_pandas_import_batch19():
    src = inspect.getsource(rmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch19():
    src = inspect.getsource(rmod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第二十九批 ----------


def test_module_source_has_future_annotations_batch19():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_json_import_batch19():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_has_time_import_batch19():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_has_pathlib_path_import_batch19():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch19():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_pipeline_import_batch19():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_has_report_version_import_batch19():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_has_annotation_metrics_import_batch19():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import (" in src


def test_module_source_has_metrics_import_batch19():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_has_report_import_batch19():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import (" in src


def test_module_source_has_load_annotation_function_batch19():
    src = inspect.getsource(rmod)
    assert "def _load_annotation(" in src


def test_module_source_has_process_one_function_batch19():
    src = inspect.getsource(rmod)
    assert "def _process_one(" in src


def test_module_source_has_run_evaluation_function_batch19():
    src = inspect.getsource(rmod)
    assert "def run_evaluation(" in src


def test_module_source_has_perf_counter_call_batch19():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


def test_module_source_has_not_instrumented_strings_batch19():
    src = inspect.getsource(rmod)
    assert '"not_instrumented"' in src
    assert "not_instrumented" in src


def test_module_source_has_all_list_single_entry_batch19():
    src = inspect.getsource(rmod)
    assert '__all__ = ["run_evaluation"]' in src


def test_module_source_has_docstring_about_runner_batch19():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


# ---------- signatures 第二十九批 ----------


def test_signature_load_annotation_batch19():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["path"]


def test_signature_process_one_batch19():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_run_evaluation_batch19():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_signature_run_evaluation_keyword_only_batch19():
    """parser_name/max_chars/tolerance_chars 是 keyword-only。"""
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    # 第三个参数（parser_name）开始应是 keyword-only
    assert params[2].kind == inspect.Parameter.KEYWORD_ONLY
    assert params[3].kind == inspect.Parameter.KEYWORD_ONLY
    assert params[4].kind == inspect.Parameter.KEYWORD_ONLY


def test_signature_run_evaluation_defaults_batch19():
    sig = inspect.signature(run_evaluation)
    params = {p.name: p for p in sig.parameters.values()}
    assert params["parser_name"].default == "fallback"
    assert params["max_chars"].default == 800
    assert params["tolerance_chars"].default == 30


# ---------- module 合理性第二十九批 ----------


def test_module_has_all_attribute_batch19():
    assert hasattr(rmod, "__all__")


def test_module_all_count_1_batch19():
    assert len(rmod.__all__) == 1


def test_module_all_contents_batch19():
    assert "run_evaluation" in rmod.__all__


def test_module_does_not_import_evaluation_cli_batch19():
    src = inspect.getsource(rmod)
    assert "from evaluation.cli" not in src
    assert "from evaluation import cli" not in src


def test_module_does_not_import_evaluation_schema_batch19():
    src = inspect.getsource(rmod)
    assert "from evaluation.schema" not in src
    assert "from evaluation import schema" not in src


def test_module_does_not_import_evaluation_manifest_batch19():
    """runner.py 不直接 import manifest（Manifest 由 caller 加载好后传入）。"""
    src = inspect.getsource(rmod)
    assert "from evaluation.manifest" not in src
    assert "from evaluation import manifest" not in src


def test_module_constants_not_in_all_batch19():
    for k in ("_load_annotation", "_process_one"):
        assert k not in rmod.__all__


def test_module_no_main_block_batch19():
    src = inspect.getsource(rmod)
    assert 'if __name__ ==' not in src
    assert "__main__" not in src


def test_module_load_annotation_is_private_batch19():
    """_load_annotation 是内部辅助函数（下划线前缀）。"""
    assert _load_annotation.__name__.startswith("_")


def test_module_process_one_is_private_batch19():
    """_process_one 是内部辅助函数（下划线前缀）。"""
    assert _process_one.__name__.startswith("_")


# ---------- 端到端集成 第二十九批 ----------


def test_e2e_load_annotation_round_trip_batch19(tmp_path):
    """写入 JSON 然后读出应等价。"""
    p = tmp_path / "a.json"
    data = {"k": [1, 2, {"x": "y"}]}
    p.write_text(json.dumps(data), encoding="utf-8")
    assert _load_annotation(p) == data


def test_e2e_run_evaluation_creates_valid_json_batch19(tmp_path):
    """生成的 JSON 文件应可被 json.load 读取。"""
    m = _make_manifest(docs=[])
    out = tmp_path / "out.json"
    run_evaluation(m, out)
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    assert "per_doc" in parsed


def test_e2e_run_evaluation_returns_same_as_file_batch19(tmp_path):
    m = _make_manifest(docs=[])
    out = tmp_path / "out.json"
    report = run_evaluation(m, out)
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed == report


def test_e2e_run_evaluation_no_docs_summary_struct_batch19(tmp_path):
    m = _make_manifest(docs=[])
    report = run_evaluation(m, tmp_path / "out.json")
    s = report["summary"]
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_e2e_run_evaluation_per_doc_count_matches_docs_batch19(tmp_path):
    """per_doc 数量等于 manifest.documents 数量。"""
    docs = [_make_doc(f"d{i}") for i in range(3)]
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=docs)
                        report = run_evaluation(m, tmp_path / "out.json")
    assert len(report["per_doc"]) == 3


def test_e2e_run_evaluation_with_expected_failure_match_batch19(tmp_path):
    """expected_failure 命中时 matches=True。"""
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


def test_e2e_run_evaluation_public_per_doc_excludes_underscore_fields_batch19(tmp_path):
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
