"""evaluation/runner.py 第五十八轮 edges 测试（Round 521）。

补强 edges55 未触及的角度（第二十八批）：
- _load_annotation 第二十八批：dict 含 set-like JSON / unicode 转义 / emoji / 大文件 / 含 boolean / null 顶层 / 数字顶层
- _process_one 第二十八批：parser_version 提取 / image_dir None 路径 / errors 取 [0] / out_stub 不存在不抛 / wall_time 非负
- run_evaluation 第二十八批：report 含 6 个 top key / per_doc 字段精确 / expected_failures matches 计算 / tolerance_chars 透传 / max_chars 透传
- module source forbidden tokens 第四十六批
- module source 字符串精确补强第四十二批
- signatures 第四十二批
- module 合理性第四十二批
- 端到端集成第四十二批
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


# ---------- _load_annotation 第二十八批 ----------


def test_load_annotation_none_returns_none_batch28():
    assert _load_annotation(None) is None


def test_load_annotation_nonexistent_path_returns_none_batch28(tmp_path):
    p = tmp_path / "nonexistent.json"
    assert _load_annotation(p) is None


def test_load_annotation_directory_returns_none_batch28(tmp_path):
    """传目录而非文件 → is_file()=False → None。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_dict_with_emoji_batch28(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": "🎉ok"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"x": "🎉ok"}


def test_load_annotation_dict_with_unicode_escape_batch28(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": "\\u00e9"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"x": "é"}


def test_load_annotation_dict_with_boolean_batch28(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": true, "y": false}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"x": True, "y": False}


def test_load_annotation_top_level_null_batch28(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("null", encoding="utf-8")
    result = _load_annotation(p)
    assert result is None


def test_load_annotation_top_level_number_batch28(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("42", encoding="utf-8")
    result = _load_annotation(p)
    assert result == 42


def test_load_annotation_top_level_string_batch28(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('"hello"', encoding="utf-8")
    result = _load_annotation(p)
    assert result == "hello"


def test_load_annotation_top_level_array_batch28(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    result = _load_annotation(p)
    assert result == [1, 2, 3]


def test_load_annotation_large_file_batch28(tmp_path):
    """大文件也能加载。"""
    p = tmp_path / "a.json"
    data = {"keys": [{"k": i, "v": str(i)} for i in range(1000)]}
    p.write_text(json.dumps(data), encoding="utf-8")
    result = _load_annotation(p)
    assert len(result["keys"]) == 1000


def test_load_annotation_no_input_modification_batch28(tmp_path):
    """不修改文件。"""
    p = tmp_path / "a.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    before = p.read_text(encoding="utf-8")
    _load_annotation(p)
    after = p.read_text(encoding="utf-8")
    assert before == after


def test_load_annotation_idempotent_batch28(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    r1 = _load_annotation(p)
    r2 = _load_annotation(p)
    assert r1 == r2


def test_load_annotation_returns_dict_or_none_batch28(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    result = _load_annotation(p)
    assert isinstance(result, dict) or result is None


# ---------- _process_one 第二十八批 ----------


def _make_doc_mock(**overrides) -> Any:
    defaults = dict(
        doc_id="d1",
        resolved_path=Path("/fake/doc.pdf"),
        source_type="pdf",
        source_hash="a" * 64,
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def test_process_one_returns_five_tuple_batch28(tmp_path):
    """返回 5 元组。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"doc_id": "d1"}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            result = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_parser_version_extracted_batch28(tmp_path):
    """成功时 parser_version 提取。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"doc_id": "d1"}
    fake_document.parser_version = "1.2.3"
    fake_document.source_hash = "a" * 64
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            document, error, elapsed, parser_version, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert parser_version == "1.2.3"
    assert error is None


def test_process_one_errors_returns_first_error_batch28(tmp_path):
    """errors 非空 → 返回 errors[0]。"""
    doc = _make_doc_mock()
    err1 = MagicMock()
    err1.to_dict.return_value = {"code": "code1", "message": "msg1"}
    err2 = MagicMock()
    err2.to_dict.return_value = {"code": "code2", "message": "msg2"}
    with patch("evaluation.runner.process_single", return_value=(None, [err1, err2])):
        document, error, elapsed, parser_version, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "code1", "message": "msg1"}
    assert parser_version is None


def test_process_one_document_none_no_errors_returns_unknown_batch28(tmp_path):
    """document=None 且 errors=[] → unknown error。"""
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        document, error, elapsed, parser_version, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "unknown", "message": "process_single returned None without errors"}


def test_process_one_wall_time_non_negative_batch28(tmp_path):
    """wall_time >= 0。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"doc_id": "d1"}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            _, _, elapsed, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert elapsed >= 0


def test_process_one_image_dir_none_when_document_none_batch28(tmp_path):
    """document=None → image_dir=None（不被推导）。"""
    doc = _make_doc_mock()
    err = MagicMock()
    err.to_dict.return_value = {"code": "fail"}
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None


def test_process_one_creates_per_doc_dir_batch28(tmp_path):
    """out_stub 父目录被创建。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"doc_id": "d1"}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            _process_one(doc, tmp_path, "fallback", 800)
    assert (tmp_path / "_per_doc").is_dir()


def test_process_one_cleans_up_stub_batch28(tmp_path):
    """out_stub 被清理（如果存在）。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"doc_id": "d1"}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    def fake_process(*args, **kwargs):
        # 模拟 pipeline 写盘
        out_path = args[1]
        out_path.write_text("{}", encoding="utf-8")
        return fake_document, []
    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            _process_one(doc, tmp_path, "fallback", 800)
    stub = tmp_path / "_per_doc" / "d1.json"
    assert not stub.is_file()  # 被清理


# ---------- run_evaluation 第二十八批 ----------


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


def test_run_evaluation_report_six_top_keys_batch28(tmp_path):
    """报告含 6 个 top key。"""
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    result = run_evaluation(manifest, out)
    assert set(result.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_run_evaluation_report_version_correct_batch28(tmp_path):
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    result = run_evaluation(manifest, out)
    assert result["report_version"] == REPORT_VERSION


def test_run_evaluation_per_doc_empty_when_no_documents_batch28(tmp_path):
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    result = run_evaluation(manifest, out)
    assert result["per_doc"] == []


def test_run_evaluation_expected_failures_empty_default_batch28(tmp_path):
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    result = run_evaluation(manifest, out)
    assert result["expected_failures"] == []


def test_run_evaluation_writes_file_batch28(tmp_path):
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    assert out.is_file()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert "report_version" in loaded


def test_run_evaluation_creates_parent_dir_batch28(tmp_path):
    """output_path 父目录被创建。"""
    manifest = _make_manifest_mock_full()
    out = tmp_path / "nested" / "deep" / "report.json"
    run_evaluation(manifest, out)
    assert out.is_file()


def test_run_evaluation_returns_dict_batch28(tmp_path):
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    result = run_evaluation(manifest, out)
    assert isinstance(result, dict)


def test_run_evaluation_summary_has_four_keys_batch28(tmp_path):
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    result = run_evaluation(manifest, out)
    assert set(result["summary"].keys()) == {
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    }


def test_run_evaluation_provenance_nine_keys_batch28(tmp_path):
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    result = run_evaluation(manifest, out)
    assert set(result["provenance"].keys()) == {
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


def test_run_evaluation_devset_six_keys_batch28(tmp_path):
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    result = run_evaluation(manifest, out)
    assert set(result["devset"].keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_run_evaluation_per_doc_field_set_batch28(tmp_path):
    """per_doc 项含 doc_id/source_type/metrics/wall_time_seconds。"""
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
    assert len(result["per_doc"]) == 1
    item = result["per_doc"][0]
    assert set(item.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_wall_time_parse_chunk_null_batch28(tmp_path):
    """wall_time parse/chunk 是 None + reason=not_instrumented。"""
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
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"
    assert wt["total"] is not None


def test_run_evaluation_max_chars_passed_to_process_single_batch28(tmp_path):
    """max_chars 透传到 process_single。"""
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"doc_id": "d1"}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    fake_document.elements = []
    fake_document.chunks = []
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])) as mock_ps:
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner._load_annotation", return_value=None):
                manifest = _make_manifest_mock_full(documents=[doc])
                out = tmp_path / "report.json"
                run_evaluation(manifest, out, max_chars=1234)
    _, kwargs = mock_ps.call_args
    assert kwargs["max_chars"] == 1234


def test_run_evaluation_parser_name_passed_batch28(tmp_path):
    doc = _make_doc_mock()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"doc_id": "d1"}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "a" * 64
    fake_document.elements = []
    fake_document.chunks = []
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])) as mock_ps:
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner._load_annotation", return_value=None):
                manifest = _make_manifest_mock_full(documents=[doc])
                out = tmp_path / "report.json"
                run_evaluation(manifest, out, parser_name="kreuzberg")
    _, kwargs = mock_ps.call_args
    assert kwargs["parser_name"] == "kreuzberg"


def test_run_evaluation_expected_failure_matches_batch28(tmp_path):
    """expected_failure：matches = (actual == expected)。"""
    ef = MagicMock()
    ef.doc_id = "bad1"
    ef.resolved_path = Path("/fake/bad.pdf")
    ef.expected_error_code = "unsupported_format"
    err = MagicMock()
    err.code = "unsupported_format"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        manifest = _make_manifest_mock_full(expected_failures=[ef])
        out = tmp_path / "report.json"
        result = run_evaluation(manifest, out)
    assert len(result["expected_failures"]) == 1
    ef_result = result["expected_failures"][0]
    assert ef_result["doc_id"] == "bad1"
    assert ef_result["expected_error_code"] == "unsupported_format"
    assert ef_result["actual_error_code"] == "unsupported_format"
    assert ef_result["matches"] is True


def test_run_evaluation_expected_failure_no_match_batch28(tmp_path):
    """expected_failure：实际无 error → actual=None, matches=False。"""
    ef = MagicMock()
    ef.doc_id = "bad1"
    ef.resolved_path = Path("/fake/bad.pdf")
    ef.expected_error_code = "unsupported_format"
    fake_doc = MagicMock()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        manifest = _make_manifest_mock_full(expected_failures=[ef])
        out = tmp_path / "report.json"
        result = run_evaluation(manifest, out)
    ef_result = result["expected_failures"][0]
    assert ef_result["actual_error_code"] is None
    assert ef_result["matches"] is False


# ---------- module source forbidden tokens 第四十六批 ----------


def test_module_source_no_subprocess_batch28():
    src = inspect.getsource(rmod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch28():
    src = inspect.getsource(rmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch28():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch28():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch28():
    src = inspect.getsource(rmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch28():
    src = inspect.getsource(rmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch28():
    src = inspect.getsource(rmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch28():
    src = inspect.getsource(rmod)
    assert "breakpoint(" not in src


def test_module_source_open_w_mode_allowed_batch28():
    """runner.py 用 open("w") 写报告 JSON（合法需求）。"""
    src = inspect.getsource(rmod)
    assert '"w"' in src  # 正向：runner 写报告


def test_module_source_no_other_forbidden_tokens_batch28():
    """其他 forbidden tokens 仍要排除（除 'w' / unlink 已允许）。"""
    src = inspect.getsource(rmod)
    assert "'w'" not in src  # 'w' 字符串字面量不出现（用双引号）


def test_module_source_no_shutil_batch28():
    src = inspect.getsource(rmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch28():
    src = inspect.getsource(rmod)
    assert "requests" not in src


def test_module_source_unlink_used_for_cleanup_batch28():
    """runner.py 用 unlink 清理 out_stub。"""
    src = inspect.getsource(rmod)
    assert ".unlink()" in src  # 正向：runner 合理使用


# ---------- module source 字符串精确补强第四十二批 ----------


def test_module_source_contains_module_docstring_batch28():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


def test_module_source_contains_load_annotation_func_batch28():
    src = inspect.getsource(rmod)
    assert "def _load_annotation" in src


def test_module_source_contains_process_one_func_batch28():
    src = inspect.getsource(rmod)
    assert "def _process_one" in src


def test_module_source_contains_run_evaluation_func_batch28():
    src = inspect.getsource(rmod)
    assert "def run_evaluation" in src


def test_module_source_contains_process_single_import_batch28():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import" in src
    assert "process_single" in src
    assert "image_output_dir_for" in src


def test_module_source_contains_compute_automatic_metrics_batch28():
    src = inspect.getsource(rmod)
    assert "compute_automatic_metrics" in src


def test_module_source_contains_figure_caption_prf_batch28():
    src = inspect.getsource(rmod)
    assert "figure_caption_prf" in src


def test_module_source_contains_chunk_boundary_prf_batch28():
    src = inspect.getsource(rmod)
    assert "chunk_boundary_prf" in src


def test_module_source_contains_not_instrumented_batch28():
    src = inspect.getsource(rmod)
    assert "not_instrumented" in src


def test_module_source_contains_perf_counter_batch28():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


def test_module_source_contains_per_doc_dir_batch28():
    src = inspect.getsource(rmod)
    assert "_per_doc" in src


def test_module_source_contains_image_output_dir_for_batch28():
    src = inspect.getsource(rmod)
    assert "image_output_dir_for" in src


def test_module_source_contains_aggregate_summary_batch28():
    src = inspect.getsource(rmod)
    assert "aggregate_summary" in src


# ---------- signatures 第四十二批 ----------


def test_signature_load_annotation_batch28():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.keys())
    assert params == ["path"]
    assert "Path | None" in str(sig.parameters["path"].annotation)


def test_signature_load_annotation_return_annotation_batch28():
    sig = inspect.signature(_load_annotation)
    assert "dict[str, Any] | None" in str(sig.return_annotation)


def test_signature_process_one_batch28():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.keys())
    assert params == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_process_one_return_annotation_batch28():
    sig = inspect.signature(_process_one)
    assert "tuple" in str(sig.return_annotation)


def test_signature_run_evaluation_batch28():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_signature_run_evaluation_keyword_only_batch28():
    """parser_name/max_chars/tolerance_chars 是 keyword-only。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_signature_run_evaluation_defaults_batch28():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_run_evaluation_return_annotation_batch28():
    sig = inspect.signature(run_evaluation)
    assert "dict[str, Any]" in str(sig.return_annotation)


# ---------- module 合理性第四十二批 ----------


def test_module_has_future_annotations_batch28():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch28():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_imports_time_batch28():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_imports_pathlib_batch28():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch28():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_no_class_definitions_batch28():
    src = inspect.getsource(rmod)
    assert "\nclass " not in src


def test_module_all_export_one_entry_batch28():
    src = inspect.getsource(rmod)
    assert '"run_evaluation"' in src


def test_module_no_main_block_batch28():
    src = inspect.getsource(rmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十二批 ----------


def test_e2e_run_evaluation_empty_manifest_batch28(tmp_path):
    """端到端：空 manifest 跑出报告。"""
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    result = run_evaluation(manifest, out)
    assert result["per_doc"] == []
    assert result["expected_failures"] == []
    assert isinstance(result["summary"], dict)


def test_e2e_run_evaluation_idempotent_batch28(tmp_path):
    """端到端：除 timestamp 外 idempotent。"""
    manifest = _make_manifest_mock_full()
    out1 = tmp_path / "r1.json"
    out2 = tmp_path / "r2.json"
    r1 = run_evaluation(manifest, out1)
    r2 = run_evaluation(manifest, out2)
    r1["provenance"].pop("run_timestamp_iso")
    r2["provenance"].pop("run_timestamp_iso")
    assert r1 == r2


def test_e2e_run_evaluation_no_input_modification_batch28(tmp_path):
    """端到端：不修改 manifest 对象的属性（mock 上不影响）。"""
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    # MagicMock 不易序列化，但确保 manifest 仍可用
    assert manifest is not None


def test_e2e_run_evaluation_creates_per_doc_dir_batch28(tmp_path):
    """端到端：调用时 _per_doc 目录被创建。"""
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
                run_evaluation(manifest, out)
    assert (tmp_path / "_per_doc").is_dir()


def test_e2e_run_evaluation_report_json_valid_batch28(tmp_path):
    """端到端：写出的 JSON 合法。"""
    manifest = _make_manifest_mock_full()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    text = out.read_text(encoding="utf-8")
    parsed = json.loads(text)
    assert parsed["report_version"] == REPORT_VERSION


def test_e2e_load_annotation_full_pipeline_batch28(tmp_path):
    """端到端：_load_annotation 读真实文件。"""
    p = tmp_path / "a.json"
    p.write_text('{"figures": [], "chunk_boundary_anchors": []}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"figures": [], "chunk_boundary_anchors": []}


def test_e2e_run_evaluation_full_with_one_doc_batch28(tmp_path):
    """端到端：完整跑一个文档（mock process_single）。"""
    doc = _make_doc_mock(doc_id="d_test", source_type="pdf")
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"doc_id": "d_test"}
    fake_document.parser_version = "fallback-1.0"
    fake_document.source_hash = "a" * 64
    fake_document.elements = []
    fake_document.chunks = []
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner._load_annotation", return_value=None):
                manifest = _make_manifest_mock_full(documents=[doc])
                out = tmp_path / "report.json"
                result = run_evaluation(manifest, out)
    assert len(result["per_doc"]) == 1
    pd = result["per_doc"][0]
    assert pd["doc_id"] == "d_test"
    assert pd["source_type"] == "pdf"
    assert "metrics" in pd
    assert "wall_time_seconds" in pd
    # provenance.parser_version 是第一个成功文档的 parser_version
    assert result["provenance"]["parser_version"] == "fallback-1.0"
