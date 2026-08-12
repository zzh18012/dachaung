"""evaluation/runner.py 第六十一轮 edges 测试（Round 542）。

补强 edges58 未触及的角度（第三十一批）。
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


# ---------- _load_annotation 第三十一批 ----------


def test_load_annotation_path_is_directory_returns_none_batch31(tmp_path):
    """path 是目录 → is_file()=False → None。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_json_array_root_returns_array_batch31(tmp_path):
    """JSON 根是 array → 返回 list（不限定 dict）。"""
    p = tmp_path / "a.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3]


def test_load_annotation_json_int_root_returns_int_batch31(tmp_path):
    """JSON 根是 int → 返回 int。"""
    p = tmp_path / "a.json"
    p.write_text("42", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 42


def test_load_annotation_json_string_root_returns_string_batch31(tmp_path):
    """JSON 根是 string → 返回 str。"""
    p = tmp_path / "a.json"
    p.write_text('"hello"', encoding="utf-8")
    out = _load_annotation(p)
    assert out == "hello"


def test_load_annotation_empty_file_returns_none_batch31(tmp_path):
    """空文件 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_invalid_json_returns_none_batch31(tmp_path):
    """非 JSON → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text("{not json}", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_returns_dict_with_nested_keys_batch31(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(
        json.dumps({"annotation_version": "1.0", "doc_id": "x", "nested": {"a": [1, 2]}}),
        encoding="utf-8",
    )
    out = _load_annotation(p)
    assert out["doc_id"] == "x"
    assert out["nested"]["a"] == [1, 2]


def test_load_annotation_dict_with_none_value_batch31(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"x": None}), encoding="utf-8")
    out = _load_annotation(p)
    assert out["x"] is None


def test_load_annotation_does_not_raise_on_oserror_batch31(tmp_path):
    """OSError 也不抛（被 catch）。"""
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    with patch("pathlib.Path.open", side_effect=OSError("boom")):
        assert _load_annotation(p) is None


# ---------- _process_one 第三十一批 ----------


def _fake_doc(tmp_path, source_type="pdf"):
    """构造 DocumentEntry-like fake。"""
    src = tmp_path / "src.txt"
    src.write_text("hello", encoding="utf-8")
    fake = MagicMock()
    fake.doc_id = "d1"
    fake.source_type = source_type
    fake.resolved_path = src
    fake.expectations = None
    return fake


def test_process_one_unlinks_out_stub_when_file_exists_batch31(tmp_path):
    """out_stub 被创建后会被 unlink。"""
    fake_doc = _fake_doc(tmp_path)
    out_root = tmp_path / "outputs"
    out_stub = out_root / "_per_doc" / f"{fake_doc.doc_id}.json"
    with patch("evaluation.runner.process_single") as mock_proc, patch("evaluation.runner.image_output_dir_for", return_value=None):
        # process_single 写一个 stub 文件
        def _write(*args, **kwargs):
            out_stub.parent.mkdir(parents=True, exist_ok=True)
            out_stub.write_text("temp", encoding="utf-8")
            return None, []
        mock_proc.side_effect = _write
        _process_one(fake_doc, out_root, "fallback", 800)
    # 调用后 out_stub 应被 unlink
    assert not out_stub.is_file()


def test_process_one_out_stub_parent_created_batch31(tmp_path):
    """_per_doc 目录被创建。"""
    fake_doc = _fake_doc(tmp_path)
    out_root = tmp_path / "outputs"
    with patch("evaluation.runner.process_single", return_value=(None, [])) as mock_proc, patch("evaluation.runner.image_output_dir_for", return_value=None):
        _process_one(fake_doc, out_root, "fallback", 800)
        per_doc_dir = out_root / "_per_doc"
        assert per_doc_dir.is_dir()


def test_process_one_calls_process_single_with_write_json_false_batch31(tmp_path):
    fake_doc = _fake_doc(tmp_path)
    out_root = tmp_path / "outputs"
    with patch("evaluation.runner.process_single", return_value=(None, [])) as mock_proc, patch("evaluation.runner.image_output_dir_for", return_value=None):
        _process_one(fake_doc, out_root, "fallback", 800)
        args, kwargs = mock_proc.call_args
        assert kwargs["write_json"] is False
        assert kwargs["parser_name"] == "fallback"
        assert kwargs["max_chars"] == 800


def test_process_one_returns_five_tuple_no_document_no_errors_batch31(tmp_path):
    fake_doc = _fake_doc(tmp_path)
    out_root = tmp_path / "outputs"
    with patch("evaluation.runner.process_single", return_value=(None, [])), patch("evaluation.runner.image_output_dir_for", return_value=None):
        result = _process_one(fake_doc, out_root, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5
    document, error, elapsed, parser_version, image_dir = result
    assert document is None
    assert error == {"code": "unknown", "message": "process_single returned None without errors"}


def test_process_one_image_dir_when_document_returns_path_batch31(tmp_path):
    """document 非 None 时 image_dir 是 Path。"""
    fake_doc = _fake_doc(tmp_path)
    out_root = tmp_path / "outputs"
    fake_doc_with_ver = MagicMock()
    fake_doc_with_ver.source_hash = "abc"
    fake_doc_with_ver.parser_version = "1.0"
    fake_doc_with_ver.to_dict.return_value = {"elements": [], "chunks": []}
    fake_image_dir = tmp_path / "images"
    with patch("evaluation.runner.process_single", return_value=(fake_doc_with_ver, [])), patch("evaluation.runner.image_output_dir_for", return_value=fake_image_dir):
        document, error, elapsed, parser_version, image_dir = _process_one(fake_doc, out_root, "fallback", 800)
    assert parser_version == "1.0"
    assert image_dir == fake_image_dir


def test_process_one_elapsed_is_float_batch31(tmp_path):
    fake_doc = _fake_doc(tmp_path)
    out_root = tmp_path / "outputs"
    with patch("evaluation.runner.process_single", return_value=(None, [])), patch("evaluation.runner.image_output_dir_for", return_value=None):
        document, error, elapsed, parser_version, image_dir = _process_one(fake_doc, out_root, "fallback", 800)
    assert isinstance(elapsed, float)
    assert elapsed >= 0


# ---------- run_evaluation 第三十一批 ----------


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


def test_run_evaluation_empty_documents_creates_report_batch31(tmp_path):
    """空 documents 列表 → 报告仍创建。"""
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    out = run_evaluation(fake_manifest, out_path)
    assert isinstance(out, dict)
    assert out_path.is_file()


def test_run_evaluation_report_file_content_matches_dict_batch31(tmp_path):
    """写到文件的内容与返回 dict 一致。"""
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    out = run_evaluation(fake_manifest, out_path)
    with out_path.open("r", encoding="utf-8") as f:
        from_disk = json.load(f)
    assert from_disk == out


def test_run_evaluation_report_version_in_report_batch31(tmp_path):
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    out = run_evaluation(fake_manifest, out_path)
    assert out["report_version"] == REPORT_VERSION


def test_run_evaluation_public_per_doc_keys_set_batch31(tmp_path):
    """public_per_doc 的 keys 是 4 个：doc_id / source_type / metrics / wall_time_seconds。"""
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    out = run_evaluation(fake_manifest, out_path)
    for item in out["per_doc"]:
        assert set(item.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_public_per_doc_excludes_private_keys_batch31(tmp_path):
    """public_per_doc 不含 _annotation_present / _tolerance_chars / _missing_markers。"""
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    out = run_evaluation(fake_manifest, out_path)
    for item in out["per_doc"]:
        assert "_annotation_present" not in item
        assert "_tolerance_chars" not in item
        assert "_missing_markers" not in item


def test_run_evaluation_expected_failures_empty_batch31(tmp_path):
    fake_manifest = _fake_manifest(tmp_path, expected_failures=[])
    out_path = tmp_path / "report.json"
    out = run_evaluation(fake_manifest, out_path)
    assert out["expected_failures"] == []


def test_run_evaluation_expected_failure_with_errors_batch31(tmp_path):
    """预期失败文档 + process_single 返回 errors → matches 计算。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.resolved_path.write_text("bad", encoding="utf-8")
    ef.expected_error_code = "unsupported_source_type"

    fake_err = MagicMock()
    fake_err.code = "unsupported_source_type"

    fake_manifest = _fake_manifest(tmp_path, expected_failures=[ef])
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [fake_err])):
        out = run_evaluation(fake_manifest, out_path)
    assert out["expected_failures"][0]["matches"] is True
    assert out["expected_failures"][0]["actual_error_code"] == "unsupported_source_type"


def test_run_evaluation_expected_failure_with_no_errors_batch31(tmp_path):
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.resolved_path.write_text("bad", encoding="utf-8")
    ef.expected_error_code = "unsupported_source_type"

    fake_manifest = _fake_manifest(tmp_path, expected_failures=[ef])
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        out = run_evaluation(fake_manifest, out_path)
    assert out["expected_failures"][0]["matches"] is False
    assert out["expected_failures"][0]["actual_error_code"] is None


def test_run_evaluation_with_real_documents_batch31(tmp_path):
    """完整 e2e：含 1 个 document → per_doc 有 1 个条目。"""
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
        out = run_evaluation(fake_manifest, out_path)
    assert len(out["per_doc"]) == 1
    assert out["per_doc"][0]["doc_id"] == "d1"


def test_run_evaluation_no_modification_to_manifest_batch31(tmp_path):
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    # 记录 manifest 字段（mock 对象不能 json.dumps，但可记录属性）
    docs_before = list(fake_manifest.documents)
    efs_before = list(fake_manifest.expected_failures)
    run_evaluation(fake_manifest, out_path)
    assert list(fake_manifest.documents) == docs_before
    assert list(fake_manifest.expected_failures) == efs_before


def test_run_evaluation_provenance_has_correct_parser_name_batch31(tmp_path):
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    out = run_evaluation(fake_manifest, out_path, parser_name="kreuzberg")
    assert out["provenance"]["parser_name"] == "kreuzberg"


def test_run_evaluation_provenance_has_correct_max_chars_batch31(tmp_path):
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    out = run_evaluation(fake_manifest, out_path, max_chars=500)
    assert out["provenance"]["max_chars"] == 500


# ---------- module source forbidden tokens 第四十九批 ----------


def test_module_source_no_eval_batch31():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch31():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch31():
    src = inspect.getsource(rmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch31():
    src = inspect.getsource(rmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch31():
    src = inspect.getsource(rmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch31():
    src = inspect.getsource(rmod)
    assert "breakpoint(" not in src


def test_module_source_no_shutil_batch31():
    src = inspect.getsource(rmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch31():
    src = inspect.getsource(rmod)
    assert "requests" not in src


def test_module_source_no_subprocess_batch31():
    """runner.py 不直接 import subprocess（用 app.pipeline）。"""
    src = inspect.getsource(rmod)
    assert "subprocess" not in src


# ---------- module source 字符串精确补强第四十五批 ----------


def test_module_source_contains_module_docstring_batch31():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


def test_module_source_contains_process_single_import_batch31():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_contains_report_version_import_batch31():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_contains_annotation_metrics_import_batch31():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import (" in src
    assert "chunk_boundary_prf" in src
    assert "figure_caption_prf" in src


def test_module_source_contains_metrics_import_batch31():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_contains_report_import_batch31():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import (" in src
    assert "aggregate_summary" in src
    assert "build_devset_section" in src
    assert "build_provenance" in src


def test_module_source_contains_load_annotation_func_batch31():
    src = inspect.getsource(rmod)
    assert "def _load_annotation(" in src


def test_module_source_contains_process_one_func_batch31():
    src = inspect.getsource(rmod)
    assert "def _process_one(" in src


def test_module_source_contains_run_evaluation_func_batch31():
    src = inspect.getsource(rmod)
    assert "def run_evaluation(" in src


def test_module_source_contains_per_doc_subdir_batch31():
    src = inspect.getsource(rmod)
    assert "_per_doc" in src


def test_module_source_contains_image_dir_local_batch31():
    src = inspect.getsource(rmod)
    assert "image_dir" in src


def test_module_source_contains_not_instrumented_batch31():
    src = inspect.getsource(rmod)
    assert "not_instrumented" in src


def test_module_source_contains_perf_counter_batch31():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


def test_module_source_contains_json_dump_batch31():
    src = inspect.getsource(rmod)
    assert "json.dump" in src


def test_module_source_contains_unlink_call_batch31():
    src = inspect.getsource(rmod)
    assert "out_stub.unlink()" in src


def test_module_source_contains_write_json_false_batch31():
    src = inspect.getsource(rmod)
    assert "write_json=False" in src


def test_module_source_contains_image_output_dir_for_batch31():
    src = inspect.getsource(rmod)
    assert "image_output_dir_for" in src


# ---------- signatures 第四十五批 ----------


def test_signature_load_annotation_param_batch31():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.keys())
    assert params == ["path"]


def test_signature_load_annotation_return_batch31():
    sig = inspect.signature(_load_annotation)
    rs = str(sig.return_annotation)
    assert "dict" in rs and "None" in rs


def test_signature_process_one_params_batch31():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.keys())
    assert params == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_process_one_return_tuple_batch31():
    sig = inspect.signature(_process_one)
    rs = str(sig.return_annotation)
    assert "tuple" in rs


def test_signature_run_evaluation_manifest_param_batch31():
    sig = inspect.signature(run_evaluation)
    assert "manifest" in sig.parameters


def test_signature_run_evaluation_keyword_only_batch31():
    """parser_name / max_chars / tolerance_chars 是 keyword-only。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_signature_run_evaluation_defaults_batch31():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


# ---------- module 合理性第四十五批 ----------


def test_module_has_future_annotations_batch31():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch31():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_imports_time_batch31():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_imports_pathlib_batch31():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch31():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_has_all_export_batch31():
    src = inspect.getsource(rmod)
    assert "__all__" in src


def test_module_all_has_run_evaluation_batch31():
    src = inspect.getsource(rmod)
    assert '"run_evaluation"' in src


def test_module_no_main_block_batch31():
    src = inspect.getsource(rmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十五批 ----------


def test_e2e_full_run_with_one_document_batch31(tmp_path):
    """端到端：含 1 个 doc → report 完整。"""
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


def test_e2e_idempotent_batch31(tmp_path):
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    out1 = run_evaluation(fake_manifest, out_path)
    out2 = run_evaluation(fake_manifest, out_path)
    # 移除 timestamp 比较（每次都不同）
    out1["provenance"].pop("run_timestamp_iso", None)
    out2["provenance"].pop("run_timestamp_iso", None)
    assert out1 == out2


def test_e2e_no_input_modification_batch31(tmp_path):
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    run_evaluation(fake_manifest, out_path)
    # 多次调用不应抛
    run_evaluation(fake_manifest, out_path)


def test_e2e_returns_report_dict_batch31(tmp_path):
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


def test_e2e_report_file_written_to_disk_batch31(tmp_path):
    fake_manifest = _fake_manifest(tmp_path)
    out_path = tmp_path / "report.json"
    run_evaluation(fake_manifest, out_path)
    assert out_path.is_file()
    # 文件可被 json.load
    with out_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert "report_version" in data


def test_e2e_per_doc_wall_time_seconds_keys_batch31(tmp_path):
    """e2e：每个 per_doc wall_time_seconds 含 5 个 key。"""
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
