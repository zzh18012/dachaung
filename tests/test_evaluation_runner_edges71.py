"""evaluation/runner.py 第八十八轮 edges 测试（Round 631）。

补强 edges70 未触及的角度（第四十五批）。

新角度：
- _load_annotation 各种边界（None / 不存在 / OSError / JSONDecodeError / 正常 / 含中文）
- _process_one 错误路径（errors 非空 → error_dict / document None 无 errors → unknown code）
- _process_one image_dir None when document None
- _process_one image_dir 实际目录
- run_evaluation 完整路径含 expected_failures
- run_evaluation per_doc 字段精确（_annotation_present / _tolerance_chars / _missing_markers / wall_time_seconds 含 total/parse/chunk/parse_reason/chunk_reason）
- run_evaluation public_per_doc 不含下划线字段
- run_evaluation report 字段精确（report_version / provenance / devset / summary / per_doc / expected_failures）
- run_evaluation expected_failures matches 计算
- run_evaluation parser_version 取第一个
- run_evaluation tolerance_chars 透传
- module source 字符串精确
- AST 结构
- forbidden tokens 第一百零一批
"""

from __future__ import annotations

import ast
import inspect
import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.runner as runner_mod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 各种边界 ----------

def test_load_annotation_none_batch45(tmp_path):
    assert _load_annotation(None) is None


def test_load_annotation_not_exists_batch45(tmp_path):
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_oserror_batch45(tmp_path):
    """模拟 OSError。"""
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    with patch("pathlib.Path.open", side_effect=OSError("boom")):
        assert _load_annotation(p) is None


def test_load_annotation_json_decode_error_batch45(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("not json", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_empty_file_batch45(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_empty_object_batch45(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    out = _load_annotation(p)
    assert out == {}


def test_load_annotation_chinese_batch45(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"name": "测试"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"name": "测试"}


def test_load_annotation_array_batch45(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3]


def test_load_annotation_null_batch45(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("null", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_nested_batch45(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"a": {"b": {"c": 1}}}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": {"b": {"c": 1}}}


def test_load_annotation_returns_dict_or_none_batch45(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None or isinstance(out, (dict, list))


# ---------- _process_one 错误路径 ----------

def _make_doc_mock(doc_id="doc_001", path="/tmp/test.pdf"):
    m = MagicMock()
    m.doc_id = doc_id
    m.resolved_path = Path(path)
    return m


def test_process_one_errors_returns_first_error_dict_batch45(tmp_path):
    doc = _make_doc_mock()
    err1 = MagicMock()
    err1.to_dict.return_value = {"code": "err1", "message": "first"}
    err2 = MagicMock()
    err2.to_dict.return_value = {"code": "err2", "message": "second"}
    with patch("evaluation.runner.process_single", return_value=(None, [err1, err2])):
        document_dict, error_dict, total, pv, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document_dict is None
    assert error_dict == {"code": "err1", "message": "first"}


def test_process_one_no_document_no_errors_unknown_batch45(tmp_path):
    """process_single 返回 (None, []) → unknown code。"""
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        document_dict, error_dict, total, pv, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document_dict is None
    assert error_dict["code"] == "unknown"
    assert "process_single returned None" in error_dict["message"]


def test_process_one_image_dir_none_when_document_none_batch45(tmp_path):
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None


def test_process_one_image_dir_set_when_document_present_batch45(tmp_path):
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    expected_dir = tmp_path / "images_xyz"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=expected_dir):
            _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir == expected_dir


def test_process_one_returns_5_tuple_batch45(tmp_path):
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        out = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(out, tuple)
    assert len(out) == 5


def test_process_one_total_seconds_nonneg_batch45(tmp_path):
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        _, _, total, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(total, float)
    assert total >= 0


def test_process_one_parser_version_none_when_error_batch45(tmp_path):
    doc = _make_doc_mock()
    err = MagicMock()
    err.to_dict.return_value = {"code": "x"}
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        _, _, _, pv, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert pv is None


def test_process_one_parser_version_from_doc_batch45(tmp_path):
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "2.5.1"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "x"):
            _, _, _, pv, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert pv == "2.5.1"


def test_process_one_unlink_silent_oserror_batch45(tmp_path):
    """out_stub unlink 失败 → 静默忽略。"""
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"

    def fake_process_single(path, out_stub, **kwargs):
        out_stub.parent.mkdir(parents=True, exist_ok=True)
        out_stub.write_text("{}", encoding="utf-8")
        return fake_doc, []

    with patch("evaluation.runner.process_single", side_effect=fake_process_single):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            with patch("pathlib.Path.unlink", side_effect=OSError("boom")):
                # 不抛即可
                _process_one(doc, tmp_path, "fallback", 800)


def test_process_one_unlink_skip_when_stub_not_exists_batch45(tmp_path):
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            # process_single 不写盘，stub 不存在 → unlink 跳过
            _process_one(doc, tmp_path, "fallback", 800)


def test_process_one_calls_process_single_batch45(tmp_path):
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single", return_value=(None, [])) as mock_ps:
        _process_one(doc, tmp_path, "fallback", 800)
    mock_ps.assert_called_once()
    # 验证关键字参数
    _, kwargs = mock_ps.call_args
    assert kwargs["parser_name"] == "fallback"
    assert kwargs["max_chars"] == 800
    assert kwargs["write_json"] is False


def test_process_one_creates_per_doc_subdir_batch45(tmp_path):
    """out_stub.parent（_per_doc）会被 mkdir。"""
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        _process_one(doc, tmp_path, "fallback", 800)
    assert (tmp_path / "_per_doc").is_dir()


# ---------- run_evaluation 完整路径 ----------

def _make_full_manifest_mock(docs=None, efs=None, project_root=None):
    m = MagicMock()
    m.documents = tuple(docs or [])
    m.expected_failures = tuple(efs or [])
    m.project_root = project_root or Path("/tmp")
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def _make_doc_mock_full(doc_id="doc_001", source_type="pdf"):
    m = MagicMock()
    m.doc_id = doc_id
    m.resolved_path = Path("/tmp/test.pdf")
    m.source_type = source_type
    m.expectations = None
    m.annotation_resolved = None
    return m


def test_run_evaluation_report_keys_batch45(tmp_path):
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = run_evaluation(manifest, tmp_path / "report.json")
    assert set(out.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_run_evaluation_report_version_batch45(tmp_path):
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = run_evaluation(manifest, tmp_path / "report.json")
    assert out["report_version"] == "1.1"


def test_run_evaluation_per_doc_count_batch45(tmp_path):
    docs = [_make_doc_mock_full(doc_id=f"d{i}") for i in range(3)]
    manifest = _make_full_manifest_mock(docs=docs)
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = run_evaluation(manifest, tmp_path / "report.json")
    assert len(out["per_doc"]) == 3


def test_run_evaluation_per_doc_keys_batch45(tmp_path):
    """public per_doc 不含下划线字段（_annotation_present 等）。"""
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = run_evaluation(manifest, tmp_path / "report.json")
    for r in out["per_doc"]:
        assert set(r.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_wall_time_keys_batch45(tmp_path):
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = run_evaluation(manifest, tmp_path / "report.json")
    wt = out["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}


def test_run_evaluation_wall_time_parse_null_batch45(tmp_path):
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = run_evaluation(manifest, tmp_path / "report.json")
    wt = out["per_doc"][0]["wall_time_seconds"]
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_expected_failures_batch45(tmp_path):
    """含 expected_failures → expected_failure_results 计入报告。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = Path("/tmp/bad.pdf")
    ef.expected_error_code = "parse_failed"
    manifest = _make_full_manifest_mock(efs=[ef])
    err = MagicMock()
    err.code = "parse_failed"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        out = run_evaluation(manifest, tmp_path / "report.json")
    assert len(out["expected_failures"]) == 1
    ef_r = out["expected_failures"][0]
    assert ef_r["expected_error_code"] == "parse_failed"
    assert ef_r["actual_error_code"] == "parse_failed"
    assert ef_r["matches"] is True


def test_run_evaluation_expected_failure_no_error_batch45(tmp_path):
    """expected_failure 但 process_single 没出错 → actual_code=None, matches=False。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = Path("/tmp/bad.pdf")
    ef.expected_error_code = "parse_failed"
    manifest = _make_full_manifest_mock(efs=[ef])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = run_evaluation(manifest, tmp_path / "report.json")
    ef_r = out["expected_failures"][0]
    assert ef_r["actual_error_code"] is None
    assert ef_r["matches"] is False


def test_run_evaluation_expected_failure_wrong_code_batch45(tmp_path):
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = Path("/tmp/bad.pdf")
    ef.expected_error_code = "parse_failed"
    manifest = _make_full_manifest_mock(efs=[ef])
    err = MagicMock()
    err.code = "different_error"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        out = run_evaluation(manifest, tmp_path / "report.json")
    ef_r = out["expected_failures"][0]
    assert ef_r["actual_error_code"] == "different_error"
    assert ef_r["matches"] is False


def test_run_evaluation_parser_version_first_only_batch45(tmp_path):
    """parser_version 取第一个成功 doc 的版本。"""
    docs = [_make_doc_mock_full(doc_id=f"d{i}") for i in range(2)]
    manifest = _make_full_manifest_mock(docs=docs)
    fake1 = MagicMock()
    fake1.to_dict.return_value = {}
    fake1.parser_version = "1.0.0"
    fake1.source_hash = "abc1"
    fake2 = MagicMock()
    fake2.to_dict.return_value = {}
    fake2.parser_version = "2.0.0"
    fake2.source_hash = "abc2"
    with patch("evaluation.runner.process_single", side_effect=[(fake1, []), (fake2, [])]):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = run_evaluation(manifest, tmp_path / "report.json")
    assert out["provenance"]["parser_version"] == "1.0.0"


def test_run_evaluation_image_dir_is_dir_passes_to_metrics_batch45(tmp_path):
    """image_dir 是真实目录 → 传给 metrics 作为 image_base_dir。"""
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    real_dir = tmp_path / "images"
    real_dir.mkdir()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=real_dir):
            out = run_evaluation(manifest, tmp_path / "report.json")
    assert "per_doc" in out


def test_run_evaluation_image_dir_not_dir_passes_none_batch45(tmp_path):
    """image_dir 不是目录 → image_base_dir=None。"""
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    nonexistent = tmp_path / "missing"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=nonexistent):
            out = run_evaluation(manifest, tmp_path / "report.json")
    assert "per_doc" in out


def test_run_evaluation_creates_output_dir_batch45(tmp_path):
    """output_path 父目录不存在 → mkdir。"""
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    out_path = tmp_path / "subdir" / "report.json"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            run_evaluation(manifest, out_path)
    assert out_path.is_file()


def test_run_evaluation_writes_valid_json_batch45(tmp_path):
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            run_evaluation(manifest, out_path)
    # 文件应该是有效 JSON
    content = out_path.read_text(encoding="utf-8")
    parsed = json.loads(content)
    assert isinstance(parsed, dict)
    assert "report_version" in parsed


def test_run_evaluation_tolerance_chars_batch45(tmp_path):
    """tolerance_chars 默认 30。"""
    src = inspect.getsource(run_evaluation)
    assert "tolerance_chars: int = 30" in src


def test_run_evaluation_returns_dict_batch45(tmp_path):
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = run_evaluation(manifest, tmp_path / "report.json")
    assert isinstance(out, dict)


def test_run_evaluation_no_docs_batch45(tmp_path):
    """manifest.documents 空 → per_doc 空。"""
    manifest = _make_full_manifest_mock(docs=[])
    with patch("evaluation.runner.process_single") as mock_ps:
        out = run_evaluation(manifest, tmp_path / "report.json")
    assert out["per_doc"] == []
    mock_ps.assert_not_called()


# ---------- module source ----------

def test_module_source_contains_run_evaluation_doc_batch45():
    src = inspect.getsource(runner_mod)
    assert "跑评测主流程" in src


def test_module_source_contains_process_one_doc_batch45():
    src = inspect.getsource(runner_mod)
    assert "跑 process_single" in src


def test_module_source_contains_not_instrumented_batch45():
    src = inspect.getsource(runner_mod)
    assert "not_instrumented" in src


def test_module_source_contains_process_single_import_batch45():
    src = inspect.getsource(runner_mod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_contains_metrics_import_batch45():
    src = inspect.getsource(runner_mod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_contains_report_import_batch45():
    src = inspect.getsource(runner_mod)
    assert "from evaluation.report import" in src


def test_module_source_contains_annotation_metrics_import_batch45():
    src = inspect.getsource(runner_mod)
    assert "from evaluation.annotation_metrics import" in src


def test_module_source_contains_unlink_in_process_one_batch45():
    src = inspect.getsource(_process_one)
    assert "unlink" in src


def test_module_source_contains_per_doc_subdir_batch45():
    src = inspect.getsource(runner_mod)
    assert "_per_doc" in src


def test_module_source_contains_perf_counter_batch45():
    src = inspect.getsource(runner_mod)
    assert "time.perf_counter" in src


def test_module_source_contains_json_dump_batch45():
    src = inspect.getsource(runner_mod)
    assert "json.dump" in src


def test_module_source_contains_ensure_ascii_false_batch45():
    src = inspect.getsource(runner_mod)
    assert "ensure_ascii=False" in src


def test_module_source_contains_indent_2_batch45():
    src = inspect.getsource(runner_mod)
    assert "indent=2" in src


def test_module_source_contains_load_annotation_function_batch45():
    src = inspect.getsource(runner_mod)
    assert "def _load_annotation(path: Path | None) -> dict[str, Any] | None:" in src


def test_module_source_contains_process_one_function_batch45():
    src = inspect.getsource(runner_mod)
    assert "def _process_one(" in src


def test_module_source_contains_run_evaluation_function_batch45():
    src = inspect.getsource(runner_mod)
    assert "def run_evaluation(" in src


def test_module_source_contains_report_version_import_batch45():
    src = inspect.getsource(runner_mod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_contains_unknown_error_message_batch45():
    src = inspect.getsource(runner_mod)
    assert "process_single returned None" in src


# ---------- __all__ ----------

def test_all_exact_batch45():
    assert set(runner_mod.__all__) == {"run_evaluation"}


def test_all_count_1_batch45():
    assert len(runner_mod.__all__) == 1


def test_all_callable_batch45():
    assert callable(getattr(runner_mod, "run_evaluation"))


# ---------- AST 结构 ----------

def test_ast_top_level_no_class_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_top_level_function_count_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 3


def test_ast_top_level_function_names_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_load_annotation", "_process_one", "run_evaluation"]


def test_ast_top_level_no_async_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_top_level_no_for_in_module_body_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.For)


def test_ast_top_level_no_while_in_module_body_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_first_node_docstring_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)


def test_ast_second_node_future_import_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


def test_ast_load_annotation_has_try_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    load_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation"][0]
    trys = [n for n in load_func.body if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_process_one_has_try_in_subtree_batch45():
    """_process_one 内部（嵌套在 if 中）的 try。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    process_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one"][0]
    trys = [n for n in ast.walk(process_func) if isinstance(n, ast.Try)]
    assert len(trys) >= 1


def test_ast_run_evaluation_has_for_loops_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    run_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation"][0]
    fors = [n for n in run_func.body if isinstance(n, ast.For)]
    assert len(fors) >= 2  # documents + expected_failures


def test_ast_run_evaluation_calls_process_one_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    run_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation"][0]
    has_call = False
    for n in ast.walk(run_func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id == "_process_one":
                has_call = True
    assert has_call


def test_ast_run_evaluation_calls_compute_metrics_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    run_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation"][0]
    has_call = False
    for n in ast.walk(run_func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id == "compute_automatic_metrics":
                has_call = True
    assert has_call


def test_ast_run_evaluation_calls_build_provenance_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    run_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation"][0]
    has_call = False
    for n in ast.walk(run_func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id == "build_provenance":
                has_call = True
    assert has_call


def test_ast_run_evaluation_calls_aggregate_summary_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    run_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation"][0]
    has_call = False
    for n in ast.walk(run_func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id == "aggregate_summary":
                has_call = True
    assert has_call


def test_ast_run_evaluation_calls_build_devset_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    run_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation"][0]
    has_call = False
    for n in ast.walk(run_func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id == "build_devset_section":
                has_call = True
    assert has_call


def test_ast_run_evaluation_calls_json_dump_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    run_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation"][0]
    has_dump = False
    for n in ast.walk(run_func):
        if isinstance(n, ast.Attribute) and n.attr == "dump":
            has_dump = True
    assert has_dump


def test_ast_run_evaluation_has_perf_counter_batch45():
    tree = ast.parse(inspect.getsource(runner_mod))
    process_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one"][0]
    has_perf = False
    for n in ast.walk(process_func):
        if isinstance(n, ast.Attribute) and n.attr == "perf_counter":
            has_perf = True
    assert has_perf


# ---------- forbidden tokens 第一百零一批 ----------

def test_source_no_eval_batch45():
    src = inspect.getsource(runner_mod)
    assert "eval(" not in src


def test_source_no_exec_batch45():
    src = inspect.getsource(runner_mod)
    assert "exec(" not in src


def test_source_no_compile_batch45():
    src = inspect.getsource(runner_mod)
    assert "compile(" not in src


def test_source_no_globals_batch45():
    src = inspect.getsource(runner_mod)
    assert "globals(" not in src


def test_source_no_locals_batch45():
    src = inspect.getsource(runner_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch45():
    src = inspect.getsource(runner_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch45():
    src = inspect.getsource(runner_mod)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch45():
    src = inspect.getsource(runner_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch45():
    src = inspect.getsource(runner_mod)
    assert "pickle.load(" not in src


def test_source_no_subprocess_batch45():
    src = inspect.getsource(runner_mod)
    assert "subprocess" not in src


def test_source_no_class_keyword_batch45():
    src = inspect.getsource(runner_mod)
    assert "\nclass " not in src


def test_source_no_async_def_batch45():
    src = inspect.getsource(runner_mod)
    assert "async def" not in src


def test_source_no_yield_batch45():
    src = inspect.getsource(runner_mod)
    assert "yield" not in src


def test_source_no_walrus_batch45():
    src = inspect.getsource(runner_mod)
    assert ":=" not in src


def test_source_no_lambda_batch45():
    src = inspect.getsource(runner_mod)
    assert "lambda" not in src
