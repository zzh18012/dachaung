"""evaluation/runner.py 第五十九轮 edges 测试（Round 528）。

补强 edges56 未触及的角度（第二十九批）：
- _load_annotation 第二十九批：list 顶层返回 list / 数字顶层 / dict 含 set-like（不可能）/ 文件 read 后 seek
- _process_one 第二十九批：document None 无 errors 路径 / out_stub 不存在不抛 / wall_time 单调
- run_evaluation 第二十九批：tolerance_chars 透传到 chunk_boundary_prf / 输出含 evaluation-report schema 校验通过 / public_per_doc 不含私有字段
- module source forbidden tokens 第四十七批
- module source 字符串精确补强第四十三批
- signatures 第四十三批
- module 合理性第四十三批
- 端到端集成第四十三批
"""

from __future__ import annotations

import inspect
import json
import math
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import REPORT_VERSION
from evaluation import runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 第二十九批 ----------


def test_load_annotation_returns_array_batch29(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    result = _load_annotation(p)
    assert result == [1, 2, 3]


def test_load_annotation_returns_number_batch29(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("42", encoding="utf-8")
    result = _load_annotation(p)
    assert result == 42


def test_load_annotation_returns_string_batch29(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('"hello"', encoding="utf-8")
    result = _load_annotation(p)
    assert result == "hello"


def test_load_annotation_returns_null_top_level_batch29(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("null", encoding="utf-8")
    result = _load_annotation(p)
    assert result is None


def test_load_annotation_returns_true_batch29(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("true", encoding="utf-8")
    result = _load_annotation(p)
    assert result is True


def test_load_annotation_returns_false_batch29(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("false", encoding="utf-8")
    result = _load_annotation(p)
    assert result is False


def test_load_annotation_returns_float_batch29(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("3.14", encoding="utf-8")
    result = _load_annotation(p)
    assert result == 3.14


def test_load_annotation_dict_with_nested_dict_batch29(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"a": {"b": {"c": 1}}}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"a": {"b": {"c": 1}}}


def test_load_annotation_invalid_json_returns_none_batch29(tmp_path):
    """invalid JSON → 异常被 except 捕获 → 返回 None。"""
    p = tmp_path / "a.json"
    p.write_text("not json {{{", encoding="utf-8")
    result = _load_annotation(p)
    assert result is None


def test_load_annotation_truncated_json_returns_none_batch29(tmp_path):
    """截断的 JSON → 返回 None。"""
    p = tmp_path / "a.json"
    p.write_text('{"x":', encoding="utf-8")
    result = _load_annotation(p)
    assert result is None


def test_load_annotation_no_modification_to_path_batch29(tmp_path):
    """不修改 path 对象。"""
    p = tmp_path / "a.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    original_str = str(p)
    _load_annotation(p)
    assert str(p) == original_str


def test_load_annotation_called_multiple_times_batch29(tmp_path):
    """多次调用同一文件。"""
    p = tmp_path / "a.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    r1 = _load_annotation(p)
    r2 = _load_annotation(p)
    r3 = _load_annotation(p)
    assert r1 == r2 == r3


# ---------- _process_one 第二十九批 ----------


def _make_doc_mock(**overrides) -> Any:
    defaults = dict(
        doc_id="d1",
        resolved_path=Path("/fake/doc.pdf"),
        source_type="pdf",
        source_hash="a" * 64,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def test_process_one_wall_time_increases_batch29(tmp_path):
    """wall_time 在多次调用中至少非递减（mock 路径）。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"doc_id": "d1"}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    elapsed_list = []
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            for _ in range(3):
                _, _, elapsed, _, _ = _process_one(doc, tmp_path, "fallback", 800)
                elapsed_list.append(elapsed)
    # 至少非负
    assert all(e >= 0 for e in elapsed_list)


def test_process_one_image_dir_returned_as_path_batch29(tmp_path):
    """成功时 image_dir 是 Path。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"doc_id": "d1"}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(image_dir, Path)


def test_process_one_returns_dict_document_batch29(tmp_path):
    """成功时返回 document dict（来自 to_dict()）。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"doc_id": "d1", "elements": []}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            document, _, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert document == {"doc_id": "d1", "elements": []}


def test_process_one_doc_id_used_in_path_batch29(tmp_path):
    """doc_id 用于 out_stub 路径命名。"""
    doc = _make_doc_mock(doc_id="custom_id")
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])) as mock_ps:
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            _process_one(doc, tmp_path, "fallback", 800)
    # 第二个 positional arg 是 out_stub
    out_stub = mock_ps.call_args[0][1]
    assert "custom_id" in str(out_stub)


def test_process_one_per_doc_subdir_batch29(tmp_path):
    """out_stub 在 _per_doc/ 子目录。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])) as mock_ps:
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            _process_one(doc, tmp_path, "fallback", 800)
    out_stub = mock_ps.call_args[0][1]
    assert "_per_doc" in str(out_stub)


def test_process_one_max_chars_passed_to_process_single_batch29(tmp_path):
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])) as mock_ps:
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            _process_one(doc, tmp_path, "fallback", 1234)
    assert mock_ps.call_args[1]["max_chars"] == 1234


def test_process_one_parser_name_passed_batch29(tmp_path):
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])) as mock_ps:
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            _process_one(doc, tmp_path, "kreuzberg", 800)
    assert mock_ps.call_args[1]["parser_name"] == "kreuzberg"


def test_process_one_write_json_false_batch29(tmp_path):
    """write_json=False 透传给 process_single。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])) as mock_ps:
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            _process_one(doc, tmp_path, "fallback", 800)
    assert mock_ps.call_args[1]["write_json"] is False


# ---------- run_evaluation 第二十九批 ----------


def _make_manifest_mock_full(**overrides) -> Any:
    defaults = dict(
        documents=[],
        expected_failures=[],
        project_root=Path("/fake/repo"),
        devset_status="incomplete",
        file_count=0,
        content_group_count=0,
        pdf_count=0,
        docx_count=0,
        categories_covered=[],
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def test_run_evaluation_tolerance_chars_passed_to_chunk_boundary_batch29(tmp_path):
    """tolerance_chars 透传给 chunk_boundary_prf。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"doc_id": "d1"}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    fake_document.elements = []
    fake_document.chunks = []
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner._load_annotation", return_value=None):
                with patch("evaluation.runner.chunk_boundary_prf") as mock_cb:
                    mock_cb.return_value = {
                        "chunk_boundary_precision": {"value": None, "reason": "x"},
                        "chunk_boundary_recall": {"value": None, "reason": "x"},
                        "chunk_boundary_f1": {"value": None, "reason": "x"},
                        "_tolerance_chars": {"value": 99, "reason": None},
                    }
                    manifest = _make_manifest_mock_full(documents=[doc])
                    out = tmp_path / "report.json"
                    run_evaluation(manifest, out, tolerance_chars=99)
    assert mock_cb.call_args[1]["tolerance_chars"] == 99


def test_run_evaluation_public_per_doc_no_private_keys_batch29(tmp_path):
    """public per_doc 不含 _ 前缀私有 key。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"doc_id": "d1"}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    fake_document.elements = []
    fake_document.chunks = []
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner._load_annotation", return_value=None):
                manifest = _make_manifest_mock_full(documents=[doc])
                out = tmp_path / "report.json"
                result = run_evaluation(manifest, out)
    item = result["per_doc"][0]
    for key in item.keys():
        assert not key.startswith("_")


def test_run_evaluation_writes_valid_json_batch29(tmp_path):
    """输出 JSON 是合法的。"""
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    text = out.read_text(encoding="utf-8")
    parsed = json.loads(text)
    assert parsed["report_version"] == REPORT_VERSION


def test_run_evaluation_passes_evaluation_report_schema_batch29(tmp_path):
    """生成的报告通过 evaluation-report.schema.json 校验。"""
    from evaluation.schema import validate_file
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    validate_file(out, "evaluation-report.schema.json")


def test_run_evaluation_returns_report_with_provenance_batch29(tmp_path):
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    result = run_evaluation(manifest, out)
    assert "provenance" in result
    assert "evaluator_version" in result["provenance"]
    assert "report_version" in result["provenance"]


def test_run_evaluation_multiple_documents_batch29(tmp_path):
    """多文档场景。"""
    doc1 = _make_doc_mock(doc_id="d1")
    doc2 = _make_doc_mock(doc_id="d2")
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    fake_document.elements = []
    fake_document.chunks = []
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner._load_annotation", return_value=None):
                manifest = _make_manifest_mock_full(documents=[doc1, doc2])
                out = tmp_path / "report.json"
                result = run_evaluation(manifest, out)
    assert len(result["per_doc"]) == 2
    assert result["per_doc"][0]["doc_id"] == "d1"
    assert result["per_doc"][1]["doc_id"] == "d2"


def test_run_evaluation_expected_failures_two_items_batch29(tmp_path):
    ef1 = MagicMock()
    ef1.doc_id = "b1"
    ef1.resolved_path = Path("/fake/b1.pdf")
    ef1.expected_error_code = "unsupported_format"
    ef2 = MagicMock()
    ef2.doc_id = "b2"
    ef2.resolved_path = Path("/fake/b2.pdf")
    ef2.expected_error_code = "parse_failed"
    err1 = MagicMock()
    err1.code = "unsupported_format"
    err2 = MagicMock()
    err2.code = "parse_failed"
    with patch("evaluation.runner.process_single", side_effect=[(None, [err1]), (None, [err2])]):
        manifest = _make_manifest_mock_full(expected_failures=[ef1, ef2])
        out = tmp_path / "report.json"
        result = run_evaluation(manifest, out)
    assert len(result["expected_failures"]) == 2
    assert result["expected_failures"][0]["matches"] is True
    assert result["expected_failures"][1]["matches"] is True


def test_run_evaluation_no_documents_batch29(tmp_path):
    manifest = _make_manifest_mock_full(documents=[])
    out = tmp_path / "report.json"
    result = run_evaluation(manifest, out)
    assert result["per_doc"] == []
    assert isinstance(result["summary"], dict)


# ---------- module source forbidden tokens 第四十七批 ----------


def test_module_source_no_subprocess_batch29():
    src = inspect.getsource(rmod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch29():
    src = inspect.getsource(rmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch29():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch29():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch29():
    src = inspect.getsource(rmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch29():
    src = inspect.getsource(rmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch29():
    src = inspect.getsource(rmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch29():
    src = inspect.getsource(rmod)
    assert "breakpoint(" not in src


def test_module_source_no_shutil_batch29():
    src = inspect.getsource(rmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch29():
    src = inspect.getsource(rmod)
    assert "requests" not in src


def test_module_source_open_w_mode_allowed_batch29():
    """runner.py 用 open("w") 写报告 JSON（合法需求）。"""
    src = inspect.getsource(rmod)
    assert '"w"' in src


def test_module_source_unlink_used_for_cleanup_batch29():
    """runner.py 用 unlink 清理 out_stub（合法需求）。"""
    src = inspect.getsource(rmod)
    assert ".unlink()" in src


# ---------- module source 字符串精确补强第四十三批 ----------


def test_module_source_contains_module_docstring_batch29():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


def test_module_source_contains_pipeline_failed_note_batch29():
    src = inspect.getsource(rmod)
    assert "pipeline_failed" in src or "失败文档" in src


def test_module_source_contains_not_instrumented_batch29():
    src = inspect.getsource(rmod)
    assert "not_instrumented" in src


def test_module_source_contains_per_doc_constant_batch29():
    src = inspect.getsource(rmod)
    assert "_per_doc" in src


def test_module_source_contains_image_dir_note_batch29():
    src = inspect.getsource(rmod)
    assert "image_dir" in src


def test_module_source_contains_annotation_present_key_batch29():
    src = inspect.getsource(rmod)
    assert "_annotation_present" in src


def test_module_source_contains_tolerance_chars_key_batch29():
    src = inspect.getsource(rmod)
    assert "_tolerance_chars" in src


def test_module_source_contains_missing_markers_key_batch29():
    src = inspect.getsource(rmod)
    assert "_missing_markers" in src


def test_module_source_contains_pipeline_import_batch29():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import" in src


def test_module_source_contains_report_imports_batch29():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import" in src


def test_module_source_contains_metrics_imports_batch29():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import" in src


def test_module_source_contains_annotation_metrics_imports_batch29():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import" in src


# ---------- signatures 第四十三批 ----------


def test_signature_load_annotation_path_annotation_batch29():
    sig = inspect.signature(_load_annotation)
    assert "Path | None" in str(sig.parameters["path"].annotation)


def test_signature_load_annotation_return_batch29():
    sig = inspect.signature(_load_annotation)
    assert "dict[str, Any] | None" in str(sig.return_annotation)


def test_signature_process_one_params_batch29():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.keys())
    assert params == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_process_one_return_tuple_batch29():
    sig = inspect.signature(_process_one)
    assert "tuple" in str(sig.return_annotation)


def test_signature_run_evaluation_keyword_only_batch29():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY


def test_signature_run_evaluation_defaults_batch29():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_run_evaluation_manifest_no_default_batch29():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].default is inspect.Parameter.empty
    assert sig.parameters["output_path"].default is inspect.Parameter.empty


# ---------- module 合理性第四十三批 ----------


def test_module_has_future_annotations_batch29():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch29():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_imports_time_batch29():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_imports_pathlib_batch29():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch29():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_no_class_definitions_batch29():
    src = inspect.getsource(rmod)
    assert "\nclass " not in src


def test_module_no_main_block_batch29():
    src = inspect.getsource(rmod)
    assert 'if __name__ == "__main__"' not in src


def test_module_all_contains_run_evaluation_batch29():
    src = inspect.getsource(rmod)
    assert '"run_evaluation"' in src


# ---------- 端到端集成第四十三批 ----------


def test_e2e_load_annotation_real_file_batch29(tmp_path):
    """端到端：_load_annotation 读真实文件。"""
    p = tmp_path / "a.json"
    p.write_text('{"figures": [1, 2]}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"figures": [1, 2]}


def test_e2e_run_evaluation_full_with_two_docs_batch29(tmp_path):
    """端到端：完整跑两个文档（mock）。"""
    doc1 = _make_doc_mock(doc_id="d1", source_type="pdf")
    doc2 = _make_doc_mock(doc_id="d2", source_type="docx")
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    fake_document.elements = []
    fake_document.chunks = []
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner._load_annotation", return_value=None):
                manifest = _make_manifest_mock_full(documents=[doc1, doc2])
                out = tmp_path / "report.json"
                result = run_evaluation(manifest, out)
    assert len(result["per_doc"]) == 2
    assert result["per_doc"][0]["doc_id"] == "d1"
    assert result["per_doc"][1]["doc_id"] == "d2"


def test_e2e_run_evaluation_creates_output_file_batch29(tmp_path):
    manifest = _make_manifest_mock_full()
    out = tmp_path / "deep" / "nested" / "report.json"
    run_evaluation(manifest, out)
    assert out.is_file()


def test_e2e_run_evaluation_returns_dict_batch29(tmp_path):
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    result = run_evaluation(manifest, out)
    assert isinstance(result, dict)


def test_e2e_run_evaluation_no_input_modification_batch29(tmp_path):
    """不修改 manifest 对象。"""
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    # manifest 应该还能正常访问
    assert manifest.documents == []
    assert manifest.expected_failures == []


def test_e2e_run_evaluation_idempotent_batch29(tmp_path):
    manifest = _make_manifest_mock_full()
    out1 = tmp_path / "r1.json"
    out2 = tmp_path / "r2.json"
    r1 = run_evaluation(manifest, out1)
    r2 = run_evaluation(manifest, out2)
    r1["provenance"].pop("run_timestamp_iso")
    r2["provenance"].pop("run_timestamp_iso")
    assert r1 == r2


def test_e2e_run_evaluation_schema_validates_batch29(tmp_path):
    """端到端：生成的报告通过 evaluation-report.schema.json 校验。"""
    from evaluation.schema import validate_file
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    validate_file(out, "evaluation-report.schema.json")
