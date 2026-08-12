"""evaluation/runner.py 第六十轮 edges 测试（Round 535）。

补强 edges57 未触及的角度（第三十批）：
- _load_annotation 第三十批：path None / 不存在 path / 文件含 BOM 失败 / 大 JSON 文件
- _process_one 第三十批：errors 非空时返回 errors[0].to_dict() / parser_version 透传 / image_dir 在 None document 时为 None
- run_evaluation 第三十批：默认参数 / output_root 创建 / report 顶层 6 key / expected_failure matches True/False / per_doc item 5 key / wall_time_seconds 含 4 个 key
- module source forbidden tokens 第四十八批（'"w"' 和 unlink 允许）
- module source 字符串精确补强第四十四批
- signatures 第四十四批
- module 合理性第四十四批
- 端到端集成第四十四批
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


# ---------- _load_annotation 第三十批 ----------


def test_load_annotation_path_none_returns_none_batch30():
    """path=None → None。"""
    assert _load_annotation(None) is None


def test_load_annotation_nonexistent_path_returns_none_batch30(tmp_path):
    """path 不存在 → None。"""
    p = tmp_path / "doesnotexist.json"
    assert _load_annotation(p) is None


def test_load_annotation_utf8_bom_fails_batch30(tmp_path):
    """UTF-8 BOM（utf-8 解码失败）→ None。"""
    p = tmp_path / "a.json"
    p.write_bytes(b"\xef\xbb\xbf" + b'{"x": 1}')
    result = _load_annotation(p)
    # BOM 让 json 解析失败 → None
    assert result is None


def test_load_annotation_large_json_batch30(tmp_path):
    """大 JSON 文件正常加载。"""
    p = tmp_path / "big.json"
    data = {"items": [{"id": i} for i in range(1000)]}
    p.write_text(json.dumps(data), encoding="utf-8")
    result = _load_annotation(p)
    assert len(result["items"]) == 1000


def test_load_annotation_path_is_str_batch30(tmp_path):
    """path 是 str → 内部转 Path。"""
    p = tmp_path / "a.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"x": 1}


def test_load_annotation_dict_with_list_value_batch30(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"key": [1, 2, 3]}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"key": [1, 2, 3]}


# ---------- _process_one 第三十批 ----------


def _make_doc_mock(**overrides) -> Any:
    defaults = dict(
        doc_id="d1",
        resolved_path=Path("/fake/doc.pdf"),
        source_type="pdf",
        source_hash="a" * 64,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def test_process_one_errors_present_returns_first_error_dict_batch30(tmp_path):
    """errors 非空 → 返回 errors[0].to_dict()。"""
    doc = _make_doc_mock()
    fake_error = MagicMock()
    fake_error.to_dict.return_value = {"code": "parse_error", "message": "broken"}
    with patch("evaluation.runner.process_single", return_value=(None, [fake_error])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            document, error, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "parse_error", "message": "broken"}


def test_process_one_parser_version_transparent_batch30(tmp_path):
    """成功时 parser_version 透传。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "9.9.9"
    fake_document.source_hash = "a" * 64
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            _, _, _, parser_version, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert parser_version == "9.9.9"


def test_process_one_image_dir_none_when_document_none_batch30(tmp_path):
    """document=None（无 errors）→ image_dir 也是 None。"""
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            document, error, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error["code"] == "unknown"
    assert image_dir is None


def test_process_one_returns_five_tuple_batch30(tmp_path):
    """返回 5 元组。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            result = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_no_write_json_kwarg_when_default_batch30(tmp_path):
    """write_json=False 总是显式传入。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])) as mock_ps:
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            _process_one(doc, tmp_path, "fallback", 800)
    assert mock_ps.call_args[1]["write_json"] is False


def test_process_one_unlinks_out_stub_when_file_exists_batch30(tmp_path):
    """out_stub 是文件时被 unlink。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    # 让 process_single 内部写一个 stub 文件
    def fake_psingle(*args, **kwargs):
        out_stub = args[1]
        out_stub.parent.mkdir(parents=True, exist_ok=True)
        out_stub.write_text("stub", encoding="utf-8")
        return fake_document, []

    with patch("evaluation.runner.process_single", side_effect=fake_psingle):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            _process_one(doc, tmp_path, "fallback", 800)
    # stub 应被清理
    stub_path = tmp_path / "_per_doc" / "d1.json"
    assert not stub_path.is_file()


# ---------- run_evaluation 第三十批 ----------


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


def test_run_evaluation_default_parser_name_batch30(tmp_path):
    """默认 parser_name=fallback。"""
    manifest = _make_manifest_mock_full()
    out = tmp_path / "r.json"
    run_evaluation(manifest, out)
    # 默认参数应在 schema 校验通过
    assert out.is_file()


def test_run_evaluation_default_max_chars_batch30(tmp_path):
    """默认 max_chars=800。"""
    manifest = _make_manifest_mock_full()
    out = tmp_path / "r.json"
    run_evaluation(manifest, out)
    assert out.is_file()


def test_run_evaluation_default_tolerance_chars_batch30(tmp_path):
    """默认 tolerance_chars=30。"""
    manifest = _make_manifest_mock_full()
    out = tmp_path / "r.json"
    run_evaluation(manifest, out)
    assert out.is_file()


def test_run_evaluation_output_root_created_batch30(tmp_path):
    """output_root 不存在时被创建。"""
    out = tmp_path / "sub" / "deep" / "r.json"
    manifest = _make_manifest_mock_full()
    run_evaluation(manifest, out)
    assert out.is_file()


def test_run_evaluation_report_top_level_keys_count_batch30(tmp_path):
    """report 顶层 6 个 key。"""
    manifest = _make_manifest_mock_full()
    out = tmp_path / "r.json"
    result = run_evaluation(manifest, out)
    assert len(result) == 6


def test_run_evaluation_report_top_level_keys_set_batch30(tmp_path):
    manifest = _make_manifest_mock_full()
    out = tmp_path / "r.json"
    result = run_evaluation(manifest, out)
    assert set(result.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_run_evaluation_expected_failure_matches_true_batch30(tmp_path):
    """expected_failure matches=True 当 codes 相等。"""
    ef = MagicMock(
        doc_id="b1",
        resolved_path=Path("/fake/bad.pdf"),
        expected_error_code="parse_error",
    )
    manifest = _make_manifest_mock_full(expected_failures=[ef])
    fake_error = MagicMock(code="parse_error")
    with patch("evaluation.runner.process_single", return_value=(None, [fake_error])):
        out = tmp_path / "r.json"
        result = run_evaluation(manifest, out)
    assert result["expected_failures"][0]["matches"] is True


def test_run_evaluation_expected_failure_matches_false_batch30(tmp_path):
    """expected_failure matches=False 当 codes 不等。"""
    ef = MagicMock(
        doc_id="b1",
        resolved_path=Path("/fake/bad.pdf"),
        expected_error_code="unsupported_format",
    )
    manifest = _make_manifest_mock_full(expected_failures=[ef])
    fake_error = MagicMock(code="parse_error")  # 不匹配
    with patch("evaluation.runner.process_single", return_value=(None, [fake_error])):
        out = tmp_path / "r.json"
        result = run_evaluation(manifest, out)
    assert result["expected_failures"][0]["matches"] is False


def test_run_evaluation_expected_failure_actual_none_when_no_errors_batch30(tmp_path):
    """expected_failure 无 errors → actual_error_code=None。"""
    ef = MagicMock(
        doc_id="b1",
        resolved_path=Path("/fake/bad.pdf"),
        expected_error_code="unsupported_format",
    )
    manifest = _make_manifest_mock_full(expected_failures=[ef])
    fake_document = MagicMock()
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        out = tmp_path / "r.json"
        result = run_evaluation(manifest, out)
    assert result["expected_failures"][0]["actual_error_code"] is None
    assert result["expected_failures"][0]["matches"] is False


def test_run_evaluation_per_doc_item_keys_count_batch30(tmp_path):
    """public per_doc item 含 4 key（doc_id/source_type/metrics/wall_time_seconds）。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    fake_document.elements = []
    fake_document.chunks = []
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner._load_annotation", return_value=None):
                manifest = _make_manifest_mock_full(documents=[doc])
                out = tmp_path / "r.json"
                result = run_evaluation(manifest, out)
    item = result["per_doc"][0]
    assert set(item.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_wall_time_seconds_keys_count_batch30(tmp_path):
    """wall_time_seconds 含 5 key。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    fake_document.elements = []
    fake_document.chunks = []
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner._load_annotation", return_value=None):
                manifest = _make_manifest_mock_full(documents=[doc])
                out = tmp_path / "r.json"
                result = run_evaluation(manifest, out)
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {
        "total",
        "parse",
        "chunk",
        "parse_reason",
        "chunk_reason",
    }


def test_run_evaluation_wall_time_parse_chunk_null_batch30(tmp_path):
    """parse / chunk 是 None，reason='not_instrumented'。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    fake_document.elements = []
    fake_document.chunks = []
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner._load_annotation", return_value=None):
                manifest = _make_manifest_mock_full(documents=[doc])
                out = tmp_path / "r.json"
                result = run_evaluation(manifest, out)
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_uses_first_parser_version_batch30(tmp_path):
    """parser_version_for_prov 取第 1 个非 None 的 parser_version。"""
    doc1 = _make_doc_mock(doc_id="d1")
    doc2 = _make_doc_mock(doc_id="d2")
    fake_document_1 = MagicMock()
    fake_document_1.to_dict.return_value = {}
    fake_document_1.parser_version = "1.0.0"
    fake_document_1.source_hash = "a" * 64
    fake_document_1.elements = []
    fake_document_1.chunks = []

    fake_document_2 = MagicMock()
    fake_document_2.to_dict.return_value = {}
    fake_document_2.parser_version = "2.0.0"
    fake_document_2.source_hash = "b" * 64
    fake_document_2.elements = []
    fake_document_2.chunks = []
    with patch("evaluation.runner.process_single", side_effect=[(fake_document_1, []), (fake_document_2, [])]):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner._load_annotation", return_value=None):
                manifest = _make_manifest_mock_full(documents=[doc1, doc2])
                out = tmp_path / "r.json"
                result = run_evaluation(manifest, out)
    assert result["provenance"]["parser_version"] == "1.0.0"


def test_run_evaluation_idempotent_batch30(tmp_path):
    """幂等：相同输入两次得到相同 report（除 timestamp）。"""
    manifest = _make_manifest_mock_full()
    out1 = tmp_path / "r1.json"
    out2 = tmp_path / "r2.json"
    r1 = run_evaluation(manifest, out1)
    r2 = run_evaluation(manifest, out2)
    # 比较 report_version / devset / summary / per_doc / expected_failures（不含 provenance.timestamp）
    assert r1["report_version"] == r2["report_version"]
    assert r1["devset"] == r2["devset"]
    assert r1["summary"] == r2["summary"]
    assert r1["per_doc"] == r2["per_doc"]


def test_run_evaluation_returns_dict_batch30(tmp_path):
    manifest = _make_manifest_mock_full()
    out = tmp_path / "r.json"
    result = run_evaluation(manifest, out)
    assert isinstance(result, dict)


# ---------- module source forbidden tokens 第四十八批（'"w"' 和 unlink 允许） ----------


def test_module_source_no_subprocess_batch30():
    src = inspect.getsource(rmod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch30():
    src = inspect.getsource(rmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch30():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch30():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch30():
    src = inspect.getsource(rmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch30():
    src = inspect.getsource(rmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch30():
    src = inspect.getsource(rmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch30():
    src = inspect.getsource(rmod)
    assert "breakpoint(" not in src


def test_module_source_no_shutil_batch30():
    src = inspect.getsource(rmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch30():
    src = inspect.getsource(rmod)
    assert "requests" not in src


# ---------- module source 字符串精确补强第四十四批 ----------


def test_module_source_contains_module_docstring_batch30():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


def test_module_source_contains_pipeline_failed_doc_batch30():
    src = inspect.getsource(rmod)
    assert "pipeline_failed" in src


def test_module_source_contains_not_instrumented_doc_batch30():
    src = inspect.getsource(rmod)
    assert "not_instrumented" in src


def test_module_source_contains_process_single_import_batch30():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_contains_report_version_import_batch30():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_contains_annotation_metrics_import_batch30():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import (" in src


def test_module_source_contains_metrics_import_batch30():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_contains_report_import_batch30():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import (" in src


def test_module_source_contains_load_annotation_func_batch30():
    src = inspect.getsource(rmod)
    assert "def _load_annotation" in src


def test_module_source_contains_process_one_func_batch30():
    src = inspect.getsource(rmod)
    assert "def _process_one" in src


def test_module_source_contains_run_evaluation_func_batch30():
    src = inspect.getsource(rmod)
    assert "def run_evaluation" in src


def test_module_source_contains_per_doc_subdir_batch30():
    src = inspect.getsource(rmod)
    assert '"_per_doc"' in src


def test_module_source_contains_image_dir_local_batch30():
    src = inspect.getsource(rmod)
    assert "image_dir" in src


def test_module_source_contains_image_output_dir_for_call_batch30():
    src = inspect.getsource(rmod)
    assert "image_output_dir_for(" in src


def test_module_source_contains_perf_counter_call_batch30():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


def test_module_source_contains_json_dump_call_batch30():
    src = inspect.getsource(rmod)
    assert "json.dump(report" in src


def test_module_source_contains_ensure_ascii_false_batch30():
    src = inspect.getsource(rmod)
    assert "ensure_ascii=False" in src


def test_module_source_contains_run_timestamp_iso_in_doc_batch30():
    """注释提到 _tolerance_chars。"""
    src = inspect.getsource(rmod)
    assert "_tolerance_chars" in src


# ---------- signatures 第四十四批 ----------


def test_signature_load_annotation_param_batch30():
    sig = inspect.signature(_load_annotation)
    assert "path" in sig.parameters
    ps = sig.parameters["path"].annotation
    assert "Path" in ps and "None" in ps


def test_signature_load_annotation_return_batch30():
    sig = inspect.signature(_load_annotation)
    ps = str(sig.return_annotation)
    assert "dict" in ps and "None" in ps


def test_signature_process_one_params_count_batch30():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.keys())
    assert params == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_process_one_return_tuple_batch30():
    sig = inspect.signature(_process_one)
    assert "tuple" in str(sig.return_annotation)


def test_signature_run_evaluation_params_count_batch30():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_signature_run_evaluation_keyword_only_batch30():
    """parser_name / max_chars / tolerance_chars 是 keyword-only（* 后）。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind.name == "KEYWORD_ONLY"
    assert sig.parameters["max_chars"].kind.name == "KEYWORD_ONLY"
    assert sig.parameters["tolerance_chars"].kind.name == "KEYWORD_ONLY"


def test_signature_run_evaluation_parser_name_default_batch30():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_signature_run_evaluation_max_chars_default_batch30():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_signature_run_evaluation_tolerance_chars_default_batch30():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_run_evaluation_return_dict_batch30():
    sig = inspect.signature(run_evaluation)
    assert "dict[str, Any]" in str(sig.return_annotation)


# ---------- module 合理性第四十四批 ----------


def test_module_has_future_annotations_batch30():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch30():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_imports_time_batch30():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_imports_pathlib_batch30():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch30():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_has_all_export_batch30():
    src = inspect.getsource(rmod)
    assert "__all__" in src


def test_module_all_has_run_evaluation_batch30():
    src = inspect.getsource(rmod)
    assert '"run_evaluation"' in src


def test_module_no_main_block_batch30():
    src = inspect.getsource(rmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十四批 ----------


def test_e2e_run_evaluation_empty_manifest_full_report_batch30(tmp_path):
    """端到端：空 manifest → 完整报告结构。"""
    manifest = _make_manifest_mock_full()
    out = tmp_path / "r.json"
    result = run_evaluation(manifest, out)
    assert result["report_version"] == REPORT_VERSION
    assert result["per_doc"] == []
    assert result["expected_failures"] == []
    assert "summary" in result
    assert "provenance" in result
    assert "devset" in result


def test_e2e_run_evaluation_schema_valid_batch30(tmp_path):
    """端到端：报告通过 schema 校验。"""
    from evaluation.schema import validate_file
    manifest = _make_manifest_mock_full()
    out = tmp_path / "r.json"
    run_evaluation(manifest, out)
    validate_file(out, "evaluation-report.schema.json")


def test_e2e_run_evaluation_multiple_expected_failures_batch30(tmp_path):
    """端到端：多个 expected_failure。"""
    ef1 = MagicMock(
        doc_id="b1",
        resolved_path=Path("/fake/b1.pdf"),
        expected_error_code="code1",
    )
    ef2 = MagicMock(
        doc_id="b2",
        resolved_path=Path("/fake/b2.pdf"),
        expected_error_code="code2",
    )
    manifest = _make_manifest_mock_full(expected_failures=[ef1, ef2])
    fake_error_1 = MagicMock(code="code1")
    fake_error_2 = MagicMock(code="other")
    with patch("evaluation.runner.process_single", side_effect=[(None, [fake_error_1]), (None, [fake_error_2])]):
        out = tmp_path / "r.json"
        result = run_evaluation(manifest, out)
    assert len(result["expected_failures"]) == 2
    assert result["expected_failures"][0]["matches"] is True
    assert result["expected_failures"][1]["matches"] is False


def test_e2e_run_evaluation_no_modification_to_manifest_batch30(tmp_path):
    """端到端：不修改 manifest 对象（MagicMock 不会变）。"""
    manifest = _make_manifest_mock_full()
    out = tmp_path / "r.json"
    before_documents = list(manifest.documents)
    run_evaluation(manifest, out)
    assert list(manifest.documents) == before_documents


def test_e2e_run_evaluation_creates_output_file_batch30(tmp_path):
    """端到端：output_path 被写入。"""
    manifest = _make_manifest_mock_full()
    out = tmp_path / "r.json"
    run_evaluation(manifest, out)
    assert out.is_file()
    assert out.stat().st_size > 0


def test_e2e_run_evaluation_report_json_loadable_batch30(tmp_path):
    """端到端：写出的文件可被 json.load 读取。"""
    manifest = _make_manifest_mock_full()
    out = tmp_path / "r.json"
    run_evaluation(manifest, out)
    with out.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["report_version"] == REPORT_VERSION


def test_e2e_run_evaluation_doc_with_annotation_batch30(tmp_path):
    """端到端：document 配 annotation。"""
    doc = _make_doc_mock(doc_id="d_ann", annotation_resolved=None)
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"elements": [], "chunks": []}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    fake_document.elements = []
    fake_document.chunks = []
    fake_annotation = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner._load_annotation", return_value=fake_annotation):
                manifest = _make_manifest_mock_full(documents=[doc])
                out = tmp_path / "r.json"
                result = run_evaluation(manifest, out)
    assert result["per_doc"][0]["doc_id"] == "d_ann"
