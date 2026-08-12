"""evaluation/runner.py 第六十三轮 edges 测试（Round 556）。

补强 edges60 未触及的角度（第三十三批）。
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


# ---------- _load_annotation 第三十三批


def test_load_annotation_none_path_returns_none_batch33():
    assert _load_annotation(None) is None


def test_load_annotation_missing_file_returns_none_batch33(tmp_path):
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_valid_file_returns_dict_batch33(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"k": 1}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": 1}


def test_load_annotation_invalid_json_returns_none_batch33(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("not json", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_directory_returns_none_batch33(tmp_path):
    """path 是目录（is_file() False）→ None。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_returns_none_for_oserror_batch33(tmp_path):
    """模拟 OSError → 返回 None。"""
    p = tmp_path / "ann.json"
    p.write_text("{}", encoding="utf-8")
    original_open = Path.open
    with patch.object(Path, "open", side_effect=OSError("denied")):
        assert _load_annotation(p) is None


def test_load_annotation_signature_batch33():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.keys())
    assert params == ["path"]


def test_load_annotation_return_annotation_batch33():
    sig = inspect.signature(_load_annotation)
    assert sig.return_annotation == "dict[str, Any] | None"


def test_load_annotation_dict_value_batch33(tmp_path):
    """返回的 dict 包含完整 JSON 内容。"""
    p = tmp_path / "ann.json"
    p.write_text(
        json.dumps({"annotation_version": "1.0", "doc_id": "d1", "extra": [1, 2, 3]}),
        encoding="utf-8",
    )
    out = _load_annotation(p)
    assert out["annotation_version"] == "1.0"
    assert out["doc_id"] == "d1"
    assert out["extra"] == [1, 2, 3]


def test_load_annotation_empty_dict_batch33(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("{}", encoding="utf-8")
    out = _load_annotation(p)
    assert out == {}


# ---------- _process_one 第三十三批


def _make_doc(tmp_path, doc_id="d1", content="hello"):
    p = tmp_path / f"{doc_id}.pdf"
    p.write_text(content, encoding="utf-8")
    return MagicMock(
        doc_id=doc_id,
        resolved_path=p,
        source_type="pdf",
        expectations=None,
        annotation_resolved=None,
        categories=(),
        paired_with=None,
        sha256=None,
        annotation_file_str=None,
        path_str=f"{doc_id}.pdf",
    )


def test_process_one_signature_batch33():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.keys())
    assert params == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_return_annotation_batch33():
    sig = inspect.signature(_process_one)
    # 返回类型注解是 tuple
    assert "tuple" in sig.return_annotation


def test_process_one_creates_per_doc_dir_batch33(tmp_path):
    """_process_one 会创建 _per_doc 目录。"""
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        _process_one(doc, output_root, "fallback", 800)
        # _per_doc 目录应被创建
        assert (output_root / "_per_doc").is_dir()


def test_process_one_unlinks_stub_after_batch33(tmp_path):
    """成功时 _per_doc/<doc_id>.json 应被清理。"""
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"chunks": []}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (fake_doc, [])
        # process_single 接受 out_stub 路径，但实际不写文件
        # 我们手动创建 stub 来测试 unlink 逻辑
        def side_effect(*args, **kwargs):
            # args[1] 是 out_stub
            out_stub = args[1]
            out_stub.parent.mkdir(parents=True, exist_ok=True)
            out_stub.write_text("{}", encoding="utf-8")
            return fake_doc, []
        mock_proc.side_effect = side_effect
        _process_one(doc, output_root, "fallback", 800)
        # stub 应被清理
        assert not (output_root / "_per_doc" / "d1.json").is_file()


def test_process_one_returns_5_tuple_batch33(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        result = _process_one(doc, output_root, "fallback", 800)
        assert isinstance(result, tuple)
        assert len(result) == 5


def test_process_one_returns_document_dict_when_success_batch33(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"chunks": [], "doc_id": "d1"}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (fake_doc, [])
        document, error, total_seconds, parser_version, image_dir = _process_one(
            doc, output_root, "fallback", 800
        )
        assert document == {"chunks": [], "doc_id": "d1"}
        assert error is None
        assert parser_version == "1.0"


def test_process_one_returns_error_dict_when_fails_batch33(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    err = MagicMock()
    err.to_dict.return_value = {"code": "E_PARSE", "message": "broken"}
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [err])
        document, error, total_seconds, parser_version, image_dir = _process_one(
            doc, output_root, "fallback", 800
        )
        assert document is None
        assert error == {"code": "E_PARSE", "message": "broken"}
        assert parser_version is None


def test_process_one_returns_no_errors_none_document_batch33(tmp_path):
    """process_single 返回 (None, []) → unknown error。"""
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [])
        document, error, total_seconds, parser_version, image_dir = _process_one(
            doc, output_root, "fallback", 800
        )
        assert document is None
        assert error["code"] == "unknown"
        assert "process_single returned None" in error["message"]


def test_process_one_total_seconds_is_float_batch33(tmp_path):
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        _, _, total_seconds, _, _ = _process_one(doc, output_root, "fallback", 800)
        assert isinstance(total_seconds, float)
        assert total_seconds >= 0


def test_process_one_image_dir_none_when_document_none_batch33(tmp_path):
    """document=None → image_dir=None。"""
    doc = _make_doc(tmp_path)
    output_root = tmp_path / "out"
    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [MagicMock(code="E_X")])
        _, _, _, _, image_dir = _process_one(doc, output_root, "fallback", 800)
        assert image_dir is None


# ---------- run_evaluation 第三十三批


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


def test_run_evaluation_signature_batch33():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_run_evaluation_keyword_only_batch33():
    sig = inspect.signature(run_evaluation)
    # parser_name/max_chars/tolerance_chars 是 keyword-only（在 * 之后）
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_defaults_batch33():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_return_annotation_batch33():
    sig = inspect.signature(run_evaluation)
    assert sig.return_annotation == "dict[str, Any]"


def test_run_evaluation_empty_documents_batch33(tmp_path):
    """空 manifest → 报告含必要 key。"""
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path)
    assert "report_version" in report
    assert "provenance" in report
    assert "devset" in report
    assert "summary" in report
    assert "per_doc" in report
    assert "expected_failures" in report


def test_run_evaluation_report_version_batch33(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_writes_output_file_batch33(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    run_evaluation(manifest, out_path)
    assert out_path.is_file()
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert "report_version" in loaded


def test_run_evaluation_creates_output_root_batch33(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "deep" / "nested" / "report.json"
    run_evaluation(manifest, out_path)
    assert out_path.is_file()


def test_run_evaluation_per_doc_empty_when_no_documents_batch33(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path)
    assert report["per_doc"] == []


def test_run_evaluation_summary_keys_batch33(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path)
    assert "counts" in report["summary"]
    assert "success_rates" in report["summary"]
    assert "ratio_macro_averages" in report["summary"]
    assert "silent_drop_total" in report["summary"]


def test_run_evaluation_provenance_keys_batch33(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path)
    prov = report["provenance"]
    assert "git_commit" in prov
    assert "git_dirty" in prov
    assert "evaluator_version" in prov
    assert "report_version" in prov
    assert "parser_name" in prov
    assert "parser_version" in prov
    assert "dependencies" in prov
    assert "max_chars" in prov
    assert "run_timestamp_iso" in prov


def test_run_evaluation_devset_keys_batch33(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path)
    dev = report["devset"]
    assert "status" in dev
    assert "file_count" in dev
    assert "content_group_count" in dev
    assert "pdf_count" in dev
    assert "docx_count" in dev
    assert "categories_covered" in dev


def test_run_evaluation_expected_failures_empty_when_none_batch33(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path)
    assert report["expected_failures"] == []


def test_run_evaluation_parser_name_in_provenance_batch33(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path, parser_name="my_parser")
    assert report["provenance"]["parser_name"] == "my_parser"


def test_run_evaluation_max_chars_in_provenance_batch33(tmp_path):
    manifest = _make_real_manifest(tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(manifest, out_path, max_chars=1234)
    assert report["provenance"]["max_chars"] == 1234


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
    "urllib",
    "socket",
    "pty.",
    "ctypes",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch33(token):
    src = inspect.getsource(rmod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch33():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


def test_module_source_contains_future_annotations_batch33():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_json_import_batch33():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_contains_time_import_batch33():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_contains_pathlib_import_batch33():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_import_batch33():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_contains_pipeline_import_batch33():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_contains_report_version_import_batch33():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_contains_annotation_metrics_import_batch33():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import (" in src


def test_module_source_contains_metrics_import_batch33():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_contains_report_import_batch33():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import (" in src


def test_module_source_contains_load_annotation_func_batch33():
    src = inspect.getsource(rmod)
    assert "def _load_annotation(" in src


def test_module_source_contains_process_one_func_batch33():
    src = inspect.getsource(rmod)
    assert "def _process_one(" in src


def test_module_source_contains_run_evaluation_func_batch33():
    src = inspect.getsource(rmod)
    assert "def run_evaluation(" in src


def test_module_source_contains_perf_counter_call_batch33():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


def test_module_source_contains_not_instrumented_batch33():
    src = inspect.getsource(rmod)
    assert '"not_instrumented"' in src


def test_module_source_contains_per_doc_dir_batch33():
    src = inspect.getsource(rmod)
    assert '"_per_doc"' in src


def test_module_source_contains_process_single_call_batch33():
    src = inspect.getsource(rmod)
    assert "process_single(" in src


def test_module_source_contains_compute_automatic_metrics_call_batch33():
    src = inspect.getsource(rmod)
    assert "compute_automatic_metrics(" in src


def test_module_source_contains_all_batch33():
    src = inspect.getsource(rmod)
    assert '__all__ = ["run_evaluation"]' in src


# ---------- signatures 第四十九批


def test_signature_load_annotation_params_batch33():
    sig = inspect.signature(_load_annotation)
    assert list(sig.parameters.keys()) == ["path"]


def test_signature_process_one_params_batch33():
    sig = inspect.signature(_process_one)
    assert list(sig.parameters.keys()) == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_run_evaluation_params_batch33():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_signature_load_annotation_return_dict_or_none_batch33():
    sig = inspect.signature(_load_annotation)
    assert sig.return_annotation == "dict[str, Any] | None"


# ---------- module 合理性第四十九批


def test_module_has_future_annotations_batch33():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch33():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_imports_time_batch33():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_has_run_evaluation_func_batch33():
    assert callable(rmod.run_evaluation)


def test_module_has_load_annotation_func_batch33():
    assert callable(rmod._load_annotation)


def test_module_has_process_one_func_batch33():
    assert callable(rmod._process_one)


def test_module_has_all_batch33():
    assert hasattr(rmod, "__all__")
    assert "run_evaluation" in rmod.__all__


# ---------- 端到端集成第四十九批


def test_e2e_run_evaluation_with_one_document_batch33(tmp_path):
    """端到端：1 个 PDF 文档（mock pipeline 成功）。"""
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
        "elements": [],
        "chunks": [],
    }
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"

    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (fake_doc, [])
        report = run_evaluation(manifest, out_path)
        assert len(report["per_doc"]) == 1
        assert report["per_doc"][0]["doc_id"] == "d1"
        assert report["provenance"]["parser_version"] == "1.0"


def test_e2e_run_evaluation_with_failed_document_batch33(tmp_path):
    """端到端：1 个文档，pipeline 失败。"""
    pdf = tmp_path / "bad.pdf"
    pdf.write_text("broken", encoding="utf-8")
    manifest = _make_real_manifest(
        tmp_path,
        documents=[{"doc_id": "d1", "path": "bad.pdf", "source_type": "pdf"}],
    )
    out_path = tmp_path / "out" / "report.json"

    err = MagicMock()
    err.to_dict.return_value = {"code": "E_PARSE", "message": "broken"}

    with patch("evaluation.runner.process_single") as mock_proc:
        mock_proc.return_value = (None, [err])
        report = run_evaluation(manifest, out_path)
        assert len(report["per_doc"]) == 1
        assert report["per_doc"][0]["metrics"]["pipeline_success"]["value"] is False
        assert report["per_doc"][0]["metrics"]["error_code"]["value"] == "E_PARSE"


def test_e2e_run_evaluation_expected_failures_batch33(tmp_path):
    """端到端：1 个 expected_failure。"""
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
        assert len(report["expected_failures"]) == 1
        ef = report["expected_failures"][0]
        assert ef["doc_id"] == "bad1"
        assert ef["expected_error_code"] == "E_PARSE"
        assert ef["actual_error_code"] == "E_PARSE"
        assert ef["matches"] is True


def test_e2e_run_evaluation_idempotent_report_version_batch33(tmp_path):
    """两次调用都返回相同的 report_version。"""
    manifest = _make_real_manifest(tmp_path)
    out_path1 = tmp_path / "out1" / "report.json"
    out_path2 = tmp_path / "out2" / "report.json"
    r1 = run_evaluation(manifest, out_path1)
    r2 = run_evaluation(manifest, out_path2)
    assert r1["report_version"] == r2["report_version"]


def test_e2e_run_evaluation_wall_time_has_total_batch33(tmp_path):
    """per_doc 的 wall_time_seconds 含 total。"""
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
        wt = report["per_doc"][0]["wall_time_seconds"]
        assert "total" in wt
        assert "parse" in wt
        assert "chunk" in wt
        assert wt["parse"] is None
        assert wt["chunk"] is None
        assert wt["parse_reason"] == "not_instrumented"
        assert wt["chunk_reason"] == "not_instrumented"


def test_e2e_run_evaluation_public_per_doc_excludes_private_keys_batch33(tmp_path):
    """公开 per_doc 不含 _annotation_present / _tolerance_chars / _missing_markers。"""
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
        assert "_annotation_present" not in pd
        assert "_tolerance_chars" not in pd
        assert "_missing_markers" not in pd
