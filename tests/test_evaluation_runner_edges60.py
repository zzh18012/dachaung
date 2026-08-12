"""evaluation/runner.py 第六十二轮 edges 测试（Round 549）。

补强 edges59 未触及的角度（第三十二批）。
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
from evaluation.runner import (
    _load_annotation,
    _process_one,
    run_evaluation,
)


# ---------- _load_annotation 第三十二批 ----------


def test_load_annotation_dict_with_chunk_boundary_anchors_batch32(tmp_path):
    """annotation 含 chunk_boundary_anchors list。"""
    p = tmp_path / "a.json"
    p.write_text(
        json.dumps({
            "annotation_version": "1.0",
            "doc_id": "d1",
            "chunk_boundary_anchors": [
                {"marker": "x", "position": "after"}
            ],
        }),
        encoding="utf-8",
    )
    out = _load_annotation(p)
    assert out["chunk_boundary_anchors"][0]["marker"] == "x"


def test_load_annotation_nested_dict_batch32(tmp_path):
    """嵌套 dict。"""
    p = tmp_path / "a.json"
    p.write_text(
        json.dumps({"l1": {"l2": {"l3": "deep"}}}),
        encoding="utf-8",
    )
    out = _load_annotation(p)
    assert out["l1"]["l2"]["l3"] == "deep"


def test_load_annotation_json_with_boolean_batch32(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": true, "y": false}', encoding="utf-8")
    out = _load_annotation(p)
    assert out["x"] is True
    assert out["y"] is False


def test_load_annotation_json_with_float_batch32(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": 1.5}', encoding="utf-8")
    out = _load_annotation(p)
    assert out["x"] == 1.5


def test_load_annotation_json_with_null_value_batch32(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": null}', encoding="utf-8")
    out = _load_annotation(p)
    assert out["x"] is None


# ---------- _process_one 第三十二批 ----------


def _fake_doc(tmp_path, source_type="pdf"):
    src = tmp_path / "src.txt"
    src.write_text("hello", encoding="utf-8")
    fake = MagicMock()
    fake.doc_id = "d1"
    fake.source_type = source_type
    fake.resolved_path = src
    fake.expectations = None
    return fake


def test_process_one_with_errors_returns_first_error_batch32(tmp_path):
    fake_doc = _fake_doc(tmp_path)
    out_root = tmp_path / "outputs"
    fake_err1 = MagicMock()
    fake_err1.to_dict.return_value = {"code": "first", "message": "m1"}
    fake_err2 = MagicMock()
    fake_err2.to_dict.return_value = {"code": "second", "message": "m2"}
    with patch("evaluation.runner.process_single", return_value=(None, [fake_err1, fake_err2])), patch("evaluation.runner.image_output_dir_for", return_value=None):
        document, error, elapsed, parser_version, image_dir = _process_one(fake_doc, out_root, "fallback", 800)
    assert document is None
    assert error == {"code": "first", "message": "m1"}


def test_process_one_document_none_no_errors_returns_unknown_batch32(tmp_path):
    fake_doc = _fake_doc(tmp_path)
    out_root = tmp_path / "outputs"
    with patch("evaluation.runner.process_single", return_value=(None, [])), patch("evaluation.runner.image_output_dir_for", return_value=None):
        document, error, elapsed, parser_version, image_dir = _process_one(fake_doc, out_root, "fallback", 800)
    assert document is None
    assert error == {"code": "unknown", "message": "process_single returned None without errors"}


def test_process_one_document_returns_to_dict_batch32(tmp_path):
    fake_doc = _fake_doc(tmp_path)
    out_root = tmp_path / "outputs"
    fake_document = MagicMock()
    fake_document.source_hash = "abc"
    fake_document.parser_version = "1.0"
    fake_document.to_dict.return_value = {"elements": [], "chunks": []}
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])), patch("evaluation.runner.image_output_dir_for", return_value=None):
        document, error, elapsed, parser_version, image_dir = _process_one(fake_doc, out_root, "fallback", 800)
    assert document == {"elements": [], "chunks": []}
    assert error is None
    assert parser_version == "1.0"


def test_process_one_image_dir_only_when_document_not_none_batch32(tmp_path):
    """document=None 时 image_dir 是 None（不调 image_output_dir_for）。"""
    fake_doc = _fake_doc(tmp_path)
    out_root = tmp_path / "outputs"
    with patch("evaluation.runner.process_single", return_value=(None, [])), patch("evaluation.runner.image_output_dir_for") as mock_image:
        document, error, elapsed, parser_version, image_dir = _process_one(fake_doc, out_root, "fallback", 800)
    mock_image.assert_not_called()
    assert image_dir is None


# ---------- run_evaluation 第三十二批 ----------


def _fake_manifest(tmp_path, documents=None, expected_failures=None):
    fake = MagicMock()
    fake.documents = documents or []
    fake.expected_failures = expected_failures or []
    fake.project_root = tmp_path
    fake.devset_status = "incomplete"
    fake.file_count = 0
    fake.content_group_count = 0
    fake.pdf_count = 0
    fake.docx_count = 0
    fake.categories_covered = []
    return fake


def test_run_evaluation_full_report_keys_set_batch32(tmp_path):
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    out = run_evaluation(fake_manifest, out_path)
    assert set(out.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_run_evaluation_provenance_keys_set_batch32(tmp_path):
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    out = run_evaluation(fake_manifest, out_path)
    assert set(out["provenance"].keys()) == {
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


def test_run_evaluation_devset_keys_set_batch32(tmp_path):
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    out = run_evaluation(fake_manifest, out_path)
    assert set(out["devset"].keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_run_evaluation_summary_keys_set_batch32(tmp_path):
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    out = run_evaluation(fake_manifest, out_path)
    assert set(out["summary"].keys()) == {
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    }


def test_run_evaluation_expected_failure_result_keys_set_batch32(tmp_path):
    """expected_failure 结果含 doc_id / expected_error_code / actual_error_code / matches。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.txt"
    ef.resolved_path.write_text("bad", encoding="utf-8")
    ef.expected_error_code = "unsupported_source_type"

    fake_manifest = _fake_manifest(tmp_path, expected_failures=[ef])
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        out = run_evaluation(fake_manifest, out_path)
    item = out["expected_failures"][0]
    assert set(item.keys()) == {"doc_id", "expected_error_code", "actual_error_code", "matches"}


def test_run_evaluation_with_two_documents_batch32(tmp_path):
    src = tmp_path / "a.pdf"
    src.write_text("dummy", encoding="utf-8")
    src2 = tmp_path / "b.pdf"
    src2.write_text("dummy", encoding="utf-8")

    def make_doc(doc_id, src_path):
        d = MagicMock()
        d.doc_id = doc_id
        d.source_type = "pdf"
        d.resolved_path = src_path
        d.expectations = None
        d.annotation_resolved = None
        return d

    docs = [make_doc("d1", src), make_doc("d2", src2)]
    fake_document = MagicMock()
    fake_document.source_hash = "abc"
    fake_document.parser_version = "1.0"
    fake_document.to_dict.return_value = {"elements": [], "chunks": []}

    fake_manifest = _fake_manifest(tmp_path, documents=docs)
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])), patch("evaluation.runner.image_output_dir_for", return_value=None):
        out = run_evaluation(fake_manifest, out_path)
    assert len(out["per_doc"]) == 2
    assert out["per_doc"][0]["doc_id"] == "d1"
    assert out["per_doc"][1]["doc_id"] == "d2"


def test_run_evaluation_uses_first_parser_version_batch32(tmp_path):
    """多个 doc 时取第一个非 None parser_version。"""
    src = tmp_path / "a.pdf"
    src.write_text("dummy", encoding="utf-8")

    doc = MagicMock()
    doc.doc_id = "d1"
    doc.source_type = "pdf"
    doc.resolved_path = src
    doc.expectations = None
    doc.annotation_resolved = None

    fake_document1 = MagicMock()
    fake_document1.source_hash = "abc"
    fake_document1.parser_version = "v1"
    fake_document1.to_dict.return_value = {"elements": [], "chunks": []}

    fake_manifest = _fake_manifest(tmp_path, documents=[doc])
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(fake_document1, [])), patch("evaluation.runner.image_output_dir_for", return_value=None):
        out = run_evaluation(fake_manifest, out_path)
    assert out["provenance"]["parser_version"] == "v1"


def test_run_evaluation_creates_per_doc_subdir_batch32(tmp_path):
    """_per_doc 子目录在含 documents 时被创建。"""
    src = tmp_path / "a.pdf"
    src.write_text("dummy", encoding="utf-8")
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.source_type = "pdf"
    doc.resolved_path = src
    doc.expectations = None
    doc.annotation_resolved = None
    fake_document = MagicMock()
    fake_document.source_hash = "abc"
    fake_document.parser_version = "1.0"
    fake_document.to_dict.return_value = {"elements": [], "chunks": []}

    fake_manifest = _fake_manifest(tmp_path, documents=[doc])
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])), patch("evaluation.runner.image_output_dir_for", return_value=None):
        run_evaluation(fake_manifest, out_path)
    per_doc_dir = out_path.parent / "_per_doc"
    assert per_doc_dir.is_dir()


def test_run_evaluation_creates_output_root_batch32(tmp_path):
    """output_root 不存在 → 创建。"""
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "deep" / "nested" / "report.json"
    run_evaluation(fake_manifest, out_path)
    assert out_path.is_file()


# ---------- module source forbidden tokens 第五十批 ----------


def test_module_source_no_eval_batch32():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch32():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch32():
    src = inspect.getsource(rmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch32():
    src = inspect.getsource(rmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch32():
    src = inspect.getsource(rmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch32():
    src = inspect.getsource(rmod)
    assert "breakpoint(" not in src


def test_module_source_no_shutil_batch32():
    src = inspect.getsource(rmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch32():
    src = inspect.getsource(rmod)
    assert "requests" not in src


def test_module_source_no_subprocess_batch32():
    src = inspect.getsource(rmod)
    assert "subprocess" not in src


# ---------- module source 字符串精确补强第四十六批 ----------


def test_module_source_contains_module_docstring_batch32():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


def test_module_source_contains_process_single_import_batch32():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_contains_report_version_import_batch32():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_contains_annotation_metrics_import_batch32():
    src = inspect.getsource(rmod)
    assert "chunk_boundary_prf" in src
    assert "figure_caption_prf" in src


def test_module_source_contains_metrics_import_batch32():
    src = inspect.getsource(rmod)
    assert "compute_automatic_metrics" in src


def test_module_source_contains_report_import_batch32():
    src = inspect.getsource(rmod)
    assert "aggregate_summary" in src
    assert "build_devset_section" in src
    assert "build_provenance" in src


def test_module_source_contains_load_annotation_func_batch32():
    src = inspect.getsource(rmod)
    assert "def _load_annotation(" in src


def test_module_source_contains_process_one_func_batch32():
    src = inspect.getsource(rmod)
    assert "def _process_one(" in src


def test_module_source_contains_run_evaluation_func_batch32():
    src = inspect.getsource(rmod)
    assert "def run_evaluation(" in src


def test_module_source_contains_per_doc_subdir_batch32():
    src = inspect.getsource(rmod)
    assert "_per_doc" in src


def test_module_source_contains_image_dir_local_batch32():
    src = inspect.getsource(rmod)
    assert "image_dir" in src


def test_module_source_contains_not_instrumented_batch32():
    src = inspect.getsource(rmod)
    assert "not_instrumented" in src


def test_module_source_contains_perf_counter_batch32():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


def test_module_source_contains_json_dump_batch32():
    src = inspect.getsource(rmod)
    assert "json.dump" in src


def test_module_source_contains_unlink_call_batch32():
    src = inspect.getsource(rmod)
    assert "out_stub.unlink()" in src


def test_module_source_contains_write_json_false_batch32():
    src = inspect.getsource(rmod)
    assert "write_json=False" in src


def test_module_source_contains_image_output_dir_for_batch32():
    src = inspect.getsource(rmod)
    assert "image_output_dir_for" in src


def test_module_source_contains_process_single_call_batch32():
    src = inspect.getsource(rmod)
    assert "process_single(" in src


def test_module_source_contains_image_dir_is_dir_batch32():
    src = inspect.getsource(rmod)
    assert "image_dir.is_dir()" in src


# ---------- signatures 第四十六批 ----------


def test_signature_load_annotation_param_batch32():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.keys())
    assert params == ["path"]


def test_signature_load_annotation_return_batch32():
    sig = inspect.signature(_load_annotation)
    rs = str(sig.return_annotation)
    assert "dict" in rs and "None" in rs


def test_signature_process_one_params_batch32():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.keys())
    assert params == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_process_one_return_tuple_batch32():
    sig = inspect.signature(_process_one)
    rs = str(sig.return_annotation)
    assert "tuple" in rs


def test_signature_run_evaluation_params_batch32():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_signature_run_evaluation_keyword_only_batch32():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_signature_run_evaluation_defaults_batch32():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


# ---------- module 合理性第四十六批 ----------


def test_module_has_future_annotations_batch32():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch32():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_imports_time_batch32():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_imports_pathlib_batch32():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch32():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_has_all_export_batch32():
    src = inspect.getsource(rmod)
    assert "__all__" in src


def test_module_all_has_run_evaluation_batch32():
    src = inspect.getsource(rmod)
    assert '"run_evaluation"' in src


def test_module_no_main_block_batch32():
    src = inspect.getsource(rmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十六批 ----------


def test_e2e_full_run_with_one_document_batch32(tmp_path):
    src = tmp_path / "a.pdf"
    src.write_text("dummy", encoding="utf-8")
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.source_type = "pdf"
    doc.resolved_path = src
    doc.expectations = None
    doc.annotation_resolved = None
    fake_document = MagicMock()
    fake_document.source_hash = "abc"
    fake_document.parser_version = "fallback-1.0"
    fake_document.to_dict.return_value = {
        "elements": [
            {
                "type": "paragraph",
                "content": "hello",
                "element_id": "e1",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]},
            }
        ],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
    }

    fake_manifest = _fake_manifest(tmp_path, documents=[doc])
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])), patch("evaluation.runner.image_output_dir_for", return_value=None):
        out = run_evaluation(fake_manifest, out_path)

    assert out["report_version"] == REPORT_VERSION
    assert len(out["per_doc"]) == 1
    assert out["per_doc"][0]["doc_id"] == "d1"
    assert out["per_doc"][0]["metrics"]["pipeline_success"]["value"] is True
    assert out["per_doc"][0]["metrics"]["element_count_total"]["value"] == 1
    assert out["summary"]["counts"]["element_count_total"]["sum"] == 1
    assert out["summary"]["success_rates"]["pipeline_success"]["rate"] == 1.0


def test_e2e_idempotent_batch32(tmp_path):
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    out1 = run_evaluation(fake_manifest, out_path)
    out2 = run_evaluation(fake_manifest, out_path)
    out1["provenance"].pop("run_timestamp_iso", None)
    out2["provenance"].pop("run_timestamp_iso", None)
    assert out1 == out2


def test_e2e_returns_report_dict_batch32(tmp_path):
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    out = run_evaluation(fake_manifest, out_path)
    assert isinstance(out, dict)
    assert set(out.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_e2e_report_file_written_to_disk_batch32(tmp_path):
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    run_evaluation(fake_manifest, out_path)
    assert out_path.is_file()
    with out_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert "report_version" in data


def test_e2e_per_doc_wall_time_seconds_keys_batch32(tmp_path):
    src = tmp_path / "a.pdf"
    src.write_text("dummy", encoding="utf-8")
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.source_type = "pdf"
    doc.resolved_path = src
    doc.expectations = None
    doc.annotation_resolved = None
    fake_document = MagicMock()
    fake_document.source_hash = "abc"
    fake_document.parser_version = None
    fake_document.to_dict.return_value = {"elements": [], "chunks": []}

    fake_manifest = _fake_manifest(tmp_path, documents=[doc])
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])), patch("evaluation.runner.image_output_dir_for", return_value=None):
        out = run_evaluation(fake_manifest, out_path)
    wt = out["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"
    assert isinstance(wt["total"], float)


def test_e2e_run_evaluation_default_kwargs_batch32(tmp_path):
    """run_evaluation 不传 parser_name/max_chars/tolerance_chars → 默认值。"""
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    out = run_evaluation(fake_manifest, out_path)
    assert out["provenance"]["parser_name"] == "fallback"
    assert out["provenance"]["max_chars"] == 800
