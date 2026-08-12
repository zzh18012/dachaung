"""evaluation/runner.py 第六十五轮 edges 测试（Round 570）。

补强 edges62 未触及的角度（第三十五批）。
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


# ---------- _load_annotation 第三十五批


def test_load_annotation_none_input_returns_none_batch35():
    """path=None → None。"""
    assert _load_annotation(None) is None


def test_load_annotation_nonexistent_file_returns_none_batch35(tmp_path):
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_directory_returns_none_batch35(tmp_path):
    """is_file() False → None。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_invalid_json_returns_none_batch35(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("not json {", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_oserror_returns_none_batch35(tmp_path):
    """模拟 OSError → None。"""
    p = tmp_path / "ann.json"
    p.write_text("{}", encoding="utf-8")
    with patch("pathlib.Path.open", side_effect=OSError("fail")):
        assert _load_annotation(p) is None


def test_load_annotation_with_anchor_data_batch35(tmp_path):
    """读出含 chunk_boundary_anchors 的标注。"""
    p = tmp_path / "ann.json"
    data = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
        ],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    out = _load_annotation(p)
    assert out["chunk_boundary_anchors"][0]["marker"] == "abc"


def test_load_annotation_large_data_batch35(tmp_path):
    """大 JSON（1000 anchors）。"""
    p = tmp_path / "ann.json"
    data = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": f"m{i}", "position": "after"} for i in range(1000)
        ],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    out = _load_annotation(p)
    assert len(out["chunk_boundary_anchors"]) == 1000


def test_load_annotation_returns_dict_when_valid_batch35(tmp_path):
    """合法 JSON → 返回 dict（即使内容很简单）。"""
    p = tmp_path / "ann.json"
    p.write_text("{}", encoding="utf-8")
    out = _load_annotation(p)
    assert isinstance(out, dict)
    assert out == {}


def test_load_annotation_special_chars_batch35(tmp_path):
    """JSON 含 emoji / 中文 / 换行。"""
    p = tmp_path / "ann.json"
    p.write_text(
        json.dumps({"emoji": "🎉", "中文": "测试", "newline": "a\nb"}),
        encoding="utf-8",
    )
    out = _load_annotation(p)
    assert out["emoji"] == "🎉"
    assert out["中文"] == "测试"
    assert out["newline"] == "a\nb"


# ---------- _process_one 第三十五批


def _make_doc(tmp_path, doc_id="d1", content="hello", source_type="pdf"):
    p = tmp_path / f"{doc_id}.pdf"
    p.write_text(content, encoding="utf-8")
    return MagicMock(
        doc_id=doc_id,
        resolved_path=p,
        source_type=source_type,
        expectations=None,
        annotation_resolved=None,
    )


def test_process_one_returns_5_tuple_batch35(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        result = _process_one(doc, output_root, "fallback", 800)
        assert isinstance(result, tuple)
        assert len(result) == 5


def test_process_one_returns_error_dict_when_errors_batch35(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    err = MagicMock()
    err.to_dict.return_value = {"code": "E_PARSE", "message": "broken"}
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [err])
        _, error, _, _, _ = _process_one(doc, output_root, "fallback", 800)
        assert error == {"code": "E_PARSE", "message": "broken"}


def test_process_one_returns_unknown_error_when_no_doc_no_errors_batch35(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [])
        _, error, _, _, _ = _process_one(doc, output_root, "fallback", 800)
        assert error["code"] == "unknown"
        assert "None without errors" in error["message"]


def test_process_one_returns_document_dict_when_success_batch35(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"elements": [], "chunks": []}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (fake_doc, [])
        document, error, _, _, _ = _process_one(doc, output_root, "fallback", 800)
        assert document == {"elements": [], "chunks": []}
        assert error is None


def test_process_one_elapsed_is_float_batch35(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        _, _, elapsed, _, _ = _process_one(doc, output_root, "fallback", 800)
        assert isinstance(elapsed, float)


def test_process_one_creates_per_doc_dir_batch35(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        _process_one(doc, output_root, "fallback", 800)
        assert (output_root / "_per_doc").is_dir()


def test_process_one_doc_id_in_stub_path_batch35(tmp_path):
    doc = _make_doc(tmp_path, doc_id="custom_doc_id")
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        _process_one(doc, output_root, "fallback", 800)
        call = mock_proc.call_args
        out_stub = call.args[1]
        assert "custom_doc_id.json" in str(out_stub)


def test_process_one_calls_process_single_batch35(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        _process_one(doc, output_root, "fallback", 800)
        assert mock_proc.call_count == 1


def test_process_one_passes_resolved_path_batch35(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        _process_one(doc, output_root, "fallback", 800)
        call = mock_proc.call_args
        assert call.args[0] == doc.resolved_path


def test_process_one_unlinks_existing_stub_batch35(tmp_path):
    """stub 文件存在 → unlink。"""
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    (output_root / "_per_doc").mkdir(parents=True)
    stub = output_root / "_per_doc" / "d1.json"
    stub.write_text("x", encoding="utf-8")
    with patch("evaluation.runner.process_single") as mock_proc:
        # process_single 模拟不写 stub（stub 已经存在）
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        _process_one(doc, output_root, "fallback", 800)
        # stub 应被 _process_one 清理
        assert not stub.is_file()


def test_process_one_unlink_oserror_swallowed_batch35(tmp_path):
    """unlink 抛 OSError → 静默吞掉。"""
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        with patch("pathlib.Path.unlink", side_effect=OSError("deny")):
            # 不抛
            result = _process_one(doc, output_root, "fallback", 800)
            assert result is not None


def test_process_one_image_dir_computed_when_doc_present_batch35(tmp_path):
    """document 存在时 image_dir 被 compute。"""
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single") as mock_proc, \
         patch("evaluation.runner.image_output_dir_for") as mock_img_dir:
        mock_proc.return_value = (fake_doc, [])
        mock_img_dir.return_value = Path("/fake/images")
        _, _, _, _, image_dir = _process_one(doc, output_root, "fallback", 800)
        assert image_dir == Path("/fake/images")


def test_process_one_image_dir_none_when_doc_none_batch35(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        _, _, _, _, image_dir = _process_one(doc, output_root, "fallback", 800)
        assert image_dir is None


# ---------- run_evaluation 第三十五批


def _write_manifest(tmp_path, documents=None, expected_failures=None):
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
    p = _write_manifest(tmp_path, documents, expected_failures)
    return load_manifest(p, project_root=tmp_path)


def test_run_evaluation_creates_output_dir_batch35(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "deeply" / "nested" / "out.json"
    run_evaluation(manifest, out_path)
    assert out_path.is_file()


def test_run_evaluation_writes_report_with_correct_version_batch35(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    run_evaluation(manifest, out_path)
    with out_path.open("r", encoding="utf-8") as f:
        report = json.load(f)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_report_has_5_top_keys_batch35(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path)
    assert set(report.keys()) == {
        "report_version", "provenance", "devset", "summary", "per_doc",
        "expected_failures",
    }


def test_run_evaluation_empty_documents_empty_per_doc_batch35(tmp_path):
    manifest = _make_real_manifest(tmp_path, documents=[])
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path)
    assert report["per_doc"] == []


def test_run_evaluation_empty_documents_empty_expected_failures_batch35(tmp_path):
    manifest = _make_real_manifest(tmp_path, expected_failures=[])
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path)
    assert report["expected_failures"] == []


def test_run_evaluation_creates_per_doc_dir_when_docs_present_batch35(tmp_path):
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


def test_run_evaluation_no_per_doc_dir_when_no_documents_batch35(tmp_path):
    """没有 documents → 不创建 _per_doc 目录。"""
    manifest = _make_real_manifest(tmp_path, documents=[])
    out_path = tmp_path / "out" / "report.json"
    run_evaluation(manifest, out_path)
    assert not (tmp_path / "out" / "_per_doc").is_dir()


def test_run_evaluation_provenance_parser_version_first_success_batch35(tmp_path):
    """parser_version 取第一个成功的。"""
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
    fake_doc1.parser_version = "first"
    fake_doc1.source_hash = "abc"
    fake_doc2 = MagicMock()
    fake_doc2.to_dict.return_value = {"source_type": "pdf", "elements": [], "chunks": []}
    fake_doc2.parser_version = "second"
    fake_doc2.source_hash = "def"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.side_effect = [(fake_doc1, []), (fake_doc2, [])]
        report = run_evaluation(manifest, out_path)
        assert report["provenance"]["parser_version"] == "first"


def test_run_evaluation_provenance_parser_name_batch35(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path, parser_name="kreuzberg")
    assert report["provenance"]["parser_name"] == "kreuzberg"


def test_run_evaluation_provenance_max_chars_batch35(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path, max_chars=1234)
    assert report["provenance"]["max_chars"] == 1234


def test_run_evaluation_expected_failure_matches_with_actual_code_batch35(tmp_path):
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
        ef = report["expected_failures"][0]
        assert ef["doc_id"] == "bad1"
        assert ef["expected_error_code"] == "E_PARSE"
        assert ef["actual_error_code"] == "E_PARSE"
        assert ef["matches"] is True


def test_run_evaluation_expected_failure_no_errors_actual_none_batch35(tmp_path):
    """expected_failure 文档实际无错误 → actual=None, matches=False。"""
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
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (fake_doc, [])  # 实际成功
        report = run_evaluation(manifest, out_path)
        ef = report["expected_failures"][0]
        assert ef["actual_error_code"] is None
        assert ef["matches"] is False


def test_run_evaluation_per_doc_has_doc_id_and_source_type_batch35(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_text("x", encoding="utf-8")
    manifest = _make_real_manifest(
        tmp_path,
        documents=[{"doc_id": "d_custom", "path": "a.pdf", "source_type": "pdf"}],
    )
    out_path = tmp_path / "out" / "report.json"
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"source_type": "pdf", "elements": [], "chunks": []}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (fake_doc, [])
        report = run_evaluation(manifest, out_path)
        pd = report["per_doc"][0]
        assert pd["doc_id"] == "d_custom"
        assert pd["source_type"] == "pdf"


def test_run_evaluation_per_doc_has_wall_time_batch35(tmp_path):
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
        report = run_evaluation(manifest, out_path)
        pd = report["per_doc"][0]
        assert "wall_time_seconds" in pd
        wt = pd["wall_time_seconds"]
        assert "total" in wt
        assert wt["parse"] is None
        assert wt["chunk"] is None
        assert wt["parse_reason"] == "not_instrumented"
        assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_summary_present_batch35(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path)
    assert "summary" in report
    assert isinstance(report["summary"], dict)


def test_run_evaluation_devset_present_batch35(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path)
    assert "devset" in report
    assert isinstance(report["devset"], dict)
    assert report["devset"]["status"] == "incomplete"


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
def test_module_source_no_forbidden_tokens_batch35(token):
    src = inspect.getsource(rmod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch35():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


def test_module_source_contains_future_annotations_batch35():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_json_import_batch35():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_contains_time_import_batch35():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_contains_pathlib_import_batch35():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch35():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_contains_pipeline_import_batch35():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_contains_report_version_import_batch35():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_contains_annotation_metrics_import_batch35():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import (" in src
    assert "chunk_boundary_prf" in src
    assert "figure_caption_prf" in src


def test_module_source_contains_metrics_import_batch35():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_contains_report_import_batch35():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import (" in src
    assert "aggregate_summary" in src
    assert "build_devset_section" in src
    assert "build_provenance" in src


def test_module_source_contains_load_annotation_func_batch35():
    src = inspect.getsource(rmod)
    assert "def _load_annotation(" in src


def test_module_source_contains_process_one_func_batch35():
    src = inspect.getsource(rmod)
    assert "def _process_one(" in src


def test_module_source_contains_run_evaluation_func_batch35():
    src = inspect.getsource(rmod)
    assert "def run_evaluation(" in src


def test_module_source_contains_not_instrumented_batch35():
    src = inspect.getsource(rmod)
    assert '"not_instrumented"' in src


def test_module_source_contains_per_doc_dir_batch35():
    src = inspect.getsource(rmod)
    assert '"_per_doc"' in src


def test_module_source_contains_perf_counter_call_batch35():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


def test_module_source_contains_json_dump_call_batch35():
    src = inspect.getsource(rmod)
    assert "json.dump(report" in src


def test_module_source_contains_ensure_ascii_false_batch35():
    src = inspect.getsource(rmod)
    assert "ensure_ascii=False" in src


def test_module_source_contains_image_output_dir_for_call_batch35():
    src = inspect.getsource(rmod)
    assert "image_output_dir_for(" in src


def test_module_source_contains_keyword_only_marker_batch35():
    """run_evaluation 用 * 强制 keyword-only。"""
    src = inspect.getsource(rmod)
    assert "*,\n    parser_name" in src or "*,  " in src or "    *" in src


def test_module_source_contains_all_only_run_evaluation_batch35():
    src = inspect.getsource(rmod)
    assert '__all__ = ["run_evaluation"]' in src


# ---------- signatures 第四十九批


def test_signature_load_annotation_one_param_batch35():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.keys())
    assert params == ["path"]


def test_signature_process_one_params_batch35():
    sig = inspect.signature(_process_one)
    assert list(sig.parameters.keys()) == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_run_evaluation_keyword_only_batch35():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_signature_run_evaluation_defaults_batch35():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_process_one_returns_tuple_batch35():
    sig = inspect.signature(_process_one)
    assert "tuple" in str(sig.return_annotation)


# ---------- module 合理性第四十九批


def test_module_imports_json_batch35():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_imports_time_batch35():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_imports_pathlib_batch35():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_has_run_evaluation_func_batch35():
    assert callable(rmod.run_evaluation)


def test_module_has_load_annotation_func_batch35():
    assert callable(rmod._load_annotation)


def test_module_has_process_one_func_batch35():
    assert callable(rmod._process_one)


def test_module_all_only_run_evaluation_batch35():
    assert rmod.__all__ == ["run_evaluation"]


# ---------- 端到端集成第四十九批


def test_e2e_full_flow_with_two_documents_batch35(tmp_path):
    """两文档，一成一败。"""
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
        assert report["summary"]["success_rates"]["pipeline_success"]["success_count"] == 1


def test_e2e_idempotent_report_keys_batch35(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path1 = tmp_path / "out1" / "report.json"
    out_path2 = tmp_path / "out2" / "report.json"
    r1 = run_evaluation(manifest, out_path1)
    r2 = run_evaluation(manifest, out_path2)
    assert set(r1.keys()) == set(r2.keys())


def test_e2e_creates_deeply_nested_output_dir_batch35(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "a" / "b" / "c" / "d" / "report.json"
    run_evaluation(manifest, out_path)
    assert out_path.is_file()


def test_e2e_report_is_json_serializable_batch35(tmp_path):
    """生成的报告 dict 应能被 json.dump（验证没有非可序列化对象）。"""
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
        report = run_evaluation(manifest, out_path)
        json.dumps(report)  # 不抛即 OK


def test_e2e_run_with_expected_failure_only_batch35(tmp_path):
    """只有 expected_failures，没有 documents。"""
    bad = tmp_path / "bad.pdf"
    bad.write_text("broken", encoding="utf-8")
    manifest = _make_real_manifest(
        tmp_path,
        expected_failures=[
            {"doc_id": "bad1", "path": "bad.pdf", "expected_error_code": "E"}
        ],
    )
    out_path = tmp_path / "out" / "report.json"
    err = MagicMock()
    err.code = "E"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [err])
        report = run_evaluation(manifest, out_path)
        assert len(report["expected_failures"]) == 1
        assert report["expected_failures"][0]["matches"] is True
        assert report["per_doc"] == []
