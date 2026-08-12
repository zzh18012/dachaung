"""evaluation/runner.py 第六十四轮 edges 测试（Round 563）。

补强 edges61 未触及的角度（第三十四批）。
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
from evaluation import runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 第三十四批


def test_load_annotation_returns_dict_with_complex_data_batch34(tmp_path):
    """复杂嵌套 JSON 也能完整读出。"""
    p = tmp_path / "ann.json"
    data = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "xyz", "position": "before"},
        ],
        "nested": {"deep": {"value": [1, 2, 3]}},
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    out = _load_annotation(p)
    assert out == data


def test_load_annotation_file_path_attribute_batch34(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("{}", encoding="utf-8")
    out_path = _load_annotation(p)
    # 返回的是 dict，不是 Path
    assert isinstance(out_path, dict)


def test_load_annotation_unicode_content_batch34(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text(
        json.dumps({"中文": "测试", "emoji": "🎉"}),
        encoding="utf-8",
    )
    out = _load_annotation(p)
    assert out["中文"] == "测试"
    assert out["emoji"] == "🎉"


def test_load_annotation_empty_file_batch34(tmp_path):
    """空文件 → JSON 解析失败 → None。"""
    p = tmp_path / "ann.json"
    p.write_text("", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_with_null_top_level_batch34(tmp_path):
    """JSON 顶层 null → 返回 None（dict 类型但实际 None）。"""
    p = tmp_path / "ann.json"
    p.write_text("null", encoding="utf-8")
    out = _load_annotation(p)
    # null JSON 解析后是 Python None
    assert out is None


def test_load_annotation_with_list_top_level_batch34(tmp_path):
    """JSON 顶层 list → 返回 list（_load_annotation 不强制 dict）。"""
    p = tmp_path / "ann.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    out = _load_annotation(p)
    # 返回 list（函数不检查类型）
    assert out == [1, 2, 3]


def test_load_annotation_with_int_top_level_batch34(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("42", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 42


# ---------- _process_one 第三十四批


def _make_doc(tmp_path, doc_id="d1", content="hello"):
    p = tmp_path / f"{doc_id}.pdf"
    p.write_text(content, encoding="utf-8")
    return MagicMock(
        doc_id=doc_id,
        resolved_path=p,
        source_type="pdf",
        expectations=None,
        annotation_resolved=None,
    )


def test_process_one_passes_parser_name_to_pipeline_batch34(tmp_path):
    """parser_name 通过 process_single 传给 pipeline。"""
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        _process_one(doc, output_root, "kreuzberg", 800)
        # 验证 process_single 调用参数
        call = mock_proc.call_args
        assert call.kwargs.get("parser_name") == "kreuzberg"


def test_process_one_passes_max_chars_to_pipeline_batch34(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        _process_one(doc, output_root, "fallback", 1234)
        call = mock_proc.call_args
        assert call.kwargs.get("max_chars") == 1234


def test_process_one_passes_write_json_false_batch34(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        _process_one(doc, output_root, "fallback", 800)
        call = mock_proc.call_args
        assert call.kwargs.get("write_json") is False


def test_process_one_returns_parser_version_from_doc_batch34(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "fallback_3.2.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (fake_doc, [])
        _, _, _, parser_version, _ = _process_one(doc, output_root, "fallback", 800)
        assert parser_version == "fallback_3.2.0"


def test_process_one_out_stub_under_per_doc_batch34(tmp_path):
    """out_stub 路径是 output_root/_per_doc/<doc_id>.json。"""
    doc = _make_doc(tmp_path, doc_id="custom_id")
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        _process_one(doc, output_root, "fallback", 800)
        # process_single 接到的 out_stub 是 output_root/_per_doc/custom_id.json
        call = mock_proc.call_args
        out_stub = call.args[1]
        assert out_stub == output_root / "_per_doc" / "custom_id.json"


def test_process_one_unlinks_stub_silently_batch34(tmp_path):
    """stub 文件不存在时不抛（OSError 被吞掉）。"""
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        # stub 不存在（process_single 没创建）
        # _process_one 应该不抛
        result = _process_one(doc, output_root, "fallback", 800)
        assert result is not None


# ---------- run_evaluation 第三十四批


def _write_manifest_file(tmp_path: Path, documents=None, expected_failures=None) -> Path:
    if documents is None:
        documents = []
    if expected_failures is None:
        expected_failures = []
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": documents,
        "expected_failures": expected_failures,
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _make_real_manifest(tmp_path, documents=None, expected_failures=None):
    from evaluation.manifest import load_manifest
    p = _write_manifest_file(tmp_path, documents, expected_failures)
    return load_manifest(p, project_root=tmp_path)


def test_run_evaluation_accepts_path_object_batch34(tmp_path):
    """output_path 接受 Path 对象。"""
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path)
    assert out_path.is_file()
    assert isinstance(report, dict)


def test_run_evaluation_accepts_str_path_batch34(tmp_path):
    """output_path 接受 str。"""
    manifest = _make_real_manifest(tmp_path)
    out_path_str = str(tmp_path / "out" / "report.json")
    report = run_evaluation(manifest, out_path_str)
    assert Path(out_path_str).is_file()


def test_run_evaluation_creates_per_doc_subdir_when_documents_batch34(tmp_path):
    """有 documents 时 _per_doc 目录被创建。"""
    pdf = tmp_path / "a.pdf"
    pdf.write_text("x", encoding="utf-8")
    manifest = _make_real_manifest(
        tmp_path,
        documents=[{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
    )
    out_path = tmp_path / "out" / "report.json"
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"source_type": "pdf", "elements": [], "chunks": []}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (fake_doc, [])
        run_evaluation(manifest, out_path)
        assert (tmp_path / "out" / "_per_doc").is_dir()


def test_run_evaluation_first_parser_version_used_batch34(tmp_path):
    """多个文档中第一个成功的 parser_version 写入 provenance。"""
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_text("x", encoding="utf-8")
    pdf2 = tmp_path / "b.pdf"
    pdf2.write_text("y", encoding="utf-8")
    manifest = _make_real_manifest(
        tmp_path,
        documents=[
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf"},
        ],
    )
    out_path = tmp_path / "out" / "report.json"
    fake_doc1 = MagicMock()
    fake_doc1.to_dict.return_value = {"source_type": "pdf", "elements": [], "chunks": []}
    fake_doc1.parser_version = "v1.0"
    fake_doc1.source_hash = "abc"
    fake_doc2 = MagicMock()
    fake_doc2.to_dict.return_value = {"source_type": "pdf", "elements": [], "chunks": []}
    fake_doc2.parser_version = "v2.0"
    fake_doc2.source_hash = "def"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.side_effect = [(fake_doc1, []), (fake_doc2, [])]
        report = run_evaluation(manifest, out_path)
        # 第一个 parser_version 被记
        assert report["provenance"]["parser_version"] == "v1.0"


def test_run_evaluation_expected_failure_matches_batch34(tmp_path):
    """expected_failure 实际 code 与期望匹配 → matches=True。"""
    bad = tmp_path / "bad.pdf"
    bad.write_text("broken", encoding="utf-8")
    manifest = _make_real_manifest(
        tmp_path,
        expected_failures=[
            {"doc_id": "bad1", "path": "bad.pdf", "expected_error_code": "E_PARSE"}
        ],
    )
    out_path = tmp_path / "out" / "report.json"
    err = MagicMock()
    err.code = "E_PARSE"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [err])
        report = run_evaluation(manifest, out_path)
        assert report["expected_failures"][0]["matches"] is True


def test_run_evaluation_expected_failure_mismatch_batch34(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_text("broken", encoding="utf-8")
    manifest = _make_real_manifest(
        tmp_path,
        expected_failures=[
            {"doc_id": "bad1", "path": "bad.pdf", "expected_error_code": "E_PARSE"}
        ],
    )
    out_path = tmp_path / "out" / "report.json"
    err = MagicMock()
    err.code = "E_DIFFERENT"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [err])
        report = run_evaluation(manifest, out_path)
        assert report["expected_failures"][0]["matches"] is False


def test_run_evaluation_expected_failure_no_error_batch34(tmp_path):
    """expected_failure 文档实际成功 → matches=False（actual=None ≠ expected）。"""
    bad = tmp_path / "bad.pdf"
    bad.write_text("actually fine", encoding="utf-8")
    manifest = _make_real_manifest(
        tmp_path,
        expected_failures=[
            {"doc_id": "bad1", "path": "bad.pdf", "expected_error_code": "E_PARSE"}
        ],
    )
    out_path = tmp_path / "out" / "report.json"
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"source_type": "pdf", "elements": [], "chunks": []}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (fake_doc, [])  # 实际成功
        report = run_evaluation(manifest, out_path)
        assert report["expected_failures"][0]["actual_error_code"] is None
        assert report["expected_failures"][0]["matches"] is False


def test_run_evaluation_report_summary_present_batch34(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path)
    assert "summary" in report
    assert isinstance(report["summary"], dict)


def test_run_evaluation_provenance_present_batch34(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path)
    assert "provenance" in report
    assert isinstance(report["provenance"], dict)


# ---------- module source forbidden tokens 第五十三批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch34(token):
    src = inspect.getsource(rmod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch34():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


def test_module_source_contains_future_annotations_batch34():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_json_import_batch34():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_contains_time_import_batch34():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_contains_pipeline_import_batch34():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_contains_annotation_metrics_import_batch34():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import (" in src
    assert "chunk_boundary_prf" in src
    assert "figure_caption_prf" in src


def test_module_source_contains_metrics_import_batch34():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_contains_report_import_batch34():
    src = inspect.getsource(rmod)
    assert "aggregate_summary" in src
    assert "build_devset_section" in src
    assert "build_provenance" in src


def test_module_source_contains_load_annotation_func_batch34():
    src = inspect.getsource(rmod)
    assert "def _load_annotation(" in src


def test_module_source_contains_process_one_func_batch34():
    src = inspect.getsource(rmod)
    assert "def _process_one(" in src


def test_module_source_contains_run_evaluation_func_batch34():
    src = inspect.getsource(rmod)
    assert "def run_evaluation(" in src


def test_module_source_contains_perf_counter_call_batch34():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


def test_module_source_contains_not_instrumented_batch34():
    src = inspect.getsource(rmod)
    assert '"not_instrumented"' in src


def test_module_source_contains_all_only_run_evaluation_batch34():
    src = inspect.getsource(rmod)
    assert '__all__ = ["run_evaluation"]' in src


# ---------- signatures 第四十九批


def test_signature_load_annotation_path_param_batch34():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.keys())
    assert params == ["path"]
    assert "Path" in sig.parameters["path"].annotation or "path" in str(sig.parameters["path"].annotation)


def test_signature_process_one_params_batch34():
    sig = inspect.signature(_process_one)
    assert list(sig.parameters.keys()) == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_run_evaluation_keyword_only_batch34():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


# ---------- module 合理性第四十九批


def test_module_imports_json_batch34():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_imports_time_batch34():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_imports_pathlib_batch34():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_has_run_evaluation_func_batch34():
    assert callable(rmod.run_evaluation)


def test_module_has_load_annotation_func_batch34():
    assert callable(rmod._load_annotation)


def test_module_has_process_one_func_batch34():
    assert callable(rmod._process_one)


def test_module_all_only_run_evaluation_batch34():
    assert rmod.__all__ == ["run_evaluation"]


# ---------- 端到端集成第四十九批


def test_e2e_full_flow_with_documents_batch34(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_text("dummy", encoding="utf-8")
    manifest = _make_real_manifest(
        tmp_path,
        documents=[{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
    )
    out_path = tmp_path / "out" / "report.json"
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "hello", "element_id": "e1"}],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
    }
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (fake_doc, [])
        report = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=500, tolerance_chars=20)
        assert report["provenance"]["parser_name"] == "fallback"
        assert report["provenance"]["max_chars"] == 500
        assert len(report["per_doc"]) == 1
        pd = report["per_doc"][0]
        assert pd["doc_id"] == "d1"
        assert pd["source_type"] == "pdf"
        # 完整 metrics
        assert "pipeline_success" in pd["metrics"]
        assert "element_count_total" in pd["metrics"]


def test_e2e_two_documents_one_fails_batch34(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_text("good", encoding="utf-8")
    pdf2 = tmp_path / "b.pdf"
    pdf2.write_text("bad", encoding="utf-8")
    manifest = _make_real_manifest(
        tmp_path,
        documents=[
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf"},
        ],
    )
    out_path = tmp_path / "out" / "report.json"
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"source_type": "pdf", "elements": [], "chunks": []}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"
    err = MagicMock()
    err.to_dict.return_value = {"code": "E_PARSE", "message": "broken"}
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.side_effect = [(fake_doc, []), (None, [err])]
        report = run_evaluation(manifest, out_path)
        assert len(report["per_doc"]) == 2
        # success_rate = 0.5
        assert report["summary"]["success_rates"]["pipeline_success"]["success_count"] == 1
        assert report["summary"]["success_rates"]["pipeline_success"]["rate"] == 0.5


def test_e2e_idempotent_report_keys_batch34(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path1 = tmp_path / "out1" / "report.json"
    out_path2 = tmp_path / "out2" / "report.json"
    r1 = run_evaluation(manifest, out_path1)
    r2 = run_evaluation(manifest, out_path2)
    assert set(r1.keys()) == set(r2.keys())


def test_e2e_creates_deeply_nested_output_dir_batch34(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "a" / "b" / "c" / "d" / "report.json"
    run_evaluation(manifest, out_path)
    assert out_path.is_file()
