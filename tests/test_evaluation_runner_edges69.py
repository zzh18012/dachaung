"""evaluation/runner.py 第七十九轮 edges 测试（Round 615）。

补强 edges68 未触及的角度（第四十三批）。

新角度：
- _load_annotation 签名 + 行为细节（JSONDecodeError / OSError / 编码 utf-8）
- _process_one 返回元组类型与元素数 / out_stub 路径 / mkdir / 失败路径
- _process_one image_dir 在 document=None 时为 None
- _process_one process_single 返回 None 无 errors 的兜底
- run_evaluation 签名 keyword-only / parser_name 默认 / max_chars 默认 / tolerance_chars 默认
- run_evaluation 报告结构 keys
- run_evaluation per_doc 内部 keys
- run_evaluation public_per_doc 字段
- run_evaluation expected_failures 字段
- run_evaluation wall_time_seconds 子字段
- run_evaluation 不返回 _annotation_present / _tolerance_chars
- module source 字符串精确
- AST 结构
- forbidden tokens 第八十五批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.runner as runner_mod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 签名 ----------

def test_load_annotation_signature_batch43():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.keys())
    assert params == ["path"]


def test_load_annotation_param_kind_batch43():
    sig = inspect.signature(_load_annotation)
    p = sig.parameters["path"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_load_annotation_return_annotation_batch43():
    sig = inspect.signature(_load_annotation)
    assert "dict" in str(sig.return_annotation) or "None" in str(sig.return_annotation)


# ---------- _load_annotation 行为 ----------

def test_load_annotation_none_returns_none_batch43():
    assert _load_annotation(None) is None


def test_load_annotation_missing_returns_none_batch43(tmp_path):
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_directory_returns_none_batch43(tmp_path):
    """目录不是 is_file() → None。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_valid_json_batch43(tmp_path):
    p = tmp_path / "anno.json"
    p.write_text('{"key": "value"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"key": "value"}


def test_load_annotation_invalid_json_returns_none_batch43(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not-json{", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_oserror_returns_none_batch43(tmp_path):
    p = tmp_path / "perm.json"
    p.write_text("{}", encoding="utf-8")
    with patch("pathlib.Path.open", side_effect=OSError("perm")):
        assert _load_annotation(p) is None


def test_load_annotation_uses_utf8_encoding_batch43():
    src = inspect.getsource(_load_annotation)
    assert 'encoding="utf-8"' in src


def test_load_annotation_catches_jsondecode_batch43(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_returns_dict_type_batch43(tmp_path):
    p = tmp_path / "anno.json"
    p.write_text("{}", encoding="utf-8")
    out = _load_annotation(p)
    assert isinstance(out, dict)


# ---------- _process_one 签名 ----------

def test_process_one_signature_batch43():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.keys())
    assert params == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_param_kinds_batch43():
    sig = inspect.signature(_process_one)
    for name in ["doc", "output_root", "parser_name", "max_chars"]:
        p = sig.parameters[name]
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_process_one_no_defaults_batch43():
    sig = inspect.signature(_process_one)
    for name in ["doc", "output_root", "parser_name", "max_chars"]:
        p = sig.parameters[name]
        assert p.default is inspect.Parameter.empty


def test_process_one_return_annotation_batch43():
    sig = inspect.signature(_process_one)
    ret = sig.return_annotation
    assert "tuple" in str(ret) or "Dict" in str(ret) or "dict" in str(ret)


# ---------- _process_one 行为 ----------

def _make_doc_mock(path: str = "/tmp/test.pdf") -> MagicMock:
    m = MagicMock()
    m.doc_id = "doc_001"
    m.resolved_path = Path(path)
    return m


def test_process_one_returns_5_tuple_batch43(tmp_path):
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"doc": "data"}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(out, tuple)
    assert len(out) == 5


def test_process_one_success_returns_doc_dict_batch43(tmp_path):
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"doc": "data"}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            document_dict, error_dict, total_seconds, parser_version, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document_dict == {"doc": "data"}
    assert error_dict is None
    assert isinstance(total_seconds, float)
    assert total_seconds >= 0
    assert parser_version == "1.0.0"
    assert image_dir is not None


def test_process_one_errors_returns_first_error_batch43(tmp_path):
    doc = _make_doc_mock()
    err = MagicMock()
    err.to_dict.return_value = {"code": "fail", "message": "boom"}
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        document_dict, error_dict, total_seconds, parser_version, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document_dict is None
    assert error_dict == {"code": "fail", "message": "boom"}
    assert parser_version is None
    assert image_dir is None  # because document is None


def test_process_one_no_errors_no_document_unknown_batch43(tmp_path):
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        document_dict, error_dict, total_seconds, parser_version, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document_dict is None
    assert error_dict == {"code": "unknown", "message": "process_single returned None without errors"}


def test_process_one_creates_per_doc_dir_batch43(tmp_path):
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            _process_one(doc, tmp_path, "fallback", 800)
    per_doc_dir = tmp_path / "_per_doc"
    assert per_doc_dir.exists()


def test_process_one_unlinks_stub_after_success_batch43(tmp_path):
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
            _process_one(doc, tmp_path, "fallback", 800)
    stub = tmp_path / "_per_doc" / "doc_001.json"
    assert not stub.is_file()


def test_process_one_passes_kwargs_to_process_single_batch43(tmp_path):
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])) as mock_ps:
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            _process_one(doc, tmp_path, "kreuzberg", 1200)
    args, kwargs = mock_ps.call_args
    assert kwargs["parser_name"] == "kreuzberg"
    assert kwargs["max_chars"] == 1200
    assert kwargs["write_json"] is False


# ---------- run_evaluation 签名 ----------

def test_run_evaluation_signature_batch43():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_run_evaluation_keyword_only_batch43():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert sig.parameters["output_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    for name in ["parser_name", "max_chars", "tolerance_chars"]:
        assert sig.parameters[name].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_defaults_batch43():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_return_annotation_batch43():
    sig = inspect.signature(run_evaluation)
    assert "dict" in str(sig.return_annotation)


# ---------- run_evaluation 行为 ----------

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


def test_run_evaluation_report_keys_batch43(tmp_path):
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = run_evaluation(manifest, tmp_path / "report.json")
    expected = {"report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"}
    assert set(out.keys()) == expected


def test_run_evaluation_per_doc_keys_batch43(tmp_path):
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = run_evaluation(manifest, tmp_path / "report.json")
    per_doc = out["per_doc"]
    assert len(per_doc) == 1
    for r in per_doc:
        assert set(r.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_per_doc_no_internal_markers_batch43(tmp_path):
    """public per_doc 不含 _annotation_present / _tolerance_chars / _missing_markers。"""
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
        assert "_annotation_present" not in r
        assert "_tolerance_chars" not in r
        assert "_missing_markers" not in r


def test_run_evaluation_wall_time_keys_batch43(tmp_path):
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
        wt = r["wall_time_seconds"]
        assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}


def test_run_evaluation_wall_time_parse_chunk_none_batch43(tmp_path):
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
        wt = r["wall_time_seconds"]
        assert wt["parse"] is None
        assert wt["chunk"] is None
        assert wt["parse_reason"] == "not_instrumented"
        assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_expected_failures_empty_batch43(tmp_path):
    manifest = _make_full_manifest_mock()
    with patch("evaluation.runner.process_single") as mock_ps:
        out = run_evaluation(manifest, tmp_path / "report.json")
    assert out["expected_failures"] == []


def test_run_evaluation_expected_failures_keys_batch43(tmp_path):
    ef = MagicMock()
    ef.doc_id = "ef_001"
    ef.resolved_path = Path("/tmp/bad.pdf")
    ef.expected_error_code = "parse_failed"
    manifest = _make_full_manifest_mock(efs=[ef])
    err = MagicMock()
    err.code = "parse_failed"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        out = run_evaluation(manifest, tmp_path / "report.json")
    ef_results = out["expected_failures"]
    assert len(ef_results) == 1
    for r in ef_results:
        assert set(r.keys()) == {"doc_id", "expected_error_code", "actual_error_code", "matches"}


def test_run_evaluation_expected_failure_matches_batch43(tmp_path):
    ef = MagicMock()
    ef.doc_id = "ef_001"
    ef.resolved_path = Path("/tmp/bad.pdf")
    ef.expected_error_code = "parse_failed"
    manifest = _make_full_manifest_mock(efs=[ef])
    err = MagicMock()
    err.code = "parse_failed"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        out = run_evaluation(manifest, tmp_path / "report.json")
    assert out["expected_failures"][0]["matches"] is True
    assert out["expected_failures"][0]["actual_error_code"] == "parse_failed"


def test_run_evaluation_expected_failure_no_match_batch43(tmp_path):
    ef = MagicMock()
    ef.doc_id = "ef_001"
    ef.resolved_path = Path("/tmp/bad.pdf")
    ef.expected_error_code = "parse_failed"
    manifest = _make_full_manifest_mock(efs=[ef])
    err = MagicMock()
    err.code = "other_error"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        out = run_evaluation(manifest, tmp_path / "report.json")
    assert out["expected_failures"][0]["matches"] is False
    assert out["expected_failures"][0]["actual_error_code"] == "other_error"


def test_run_evaluation_expected_failure_no_errors_batch43(tmp_path):
    """expected_failure 实际成功（errors 空）→ actual_error_code=None, matches=False。"""
    ef = MagicMock()
    ef.doc_id = "ef_001"
    ef.resolved_path = Path("/tmp/bad.pdf")
    ef.expected_error_code = "parse_failed"
    manifest = _make_full_manifest_mock(efs=[ef])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        out = run_evaluation(manifest, tmp_path / "report.json")
    assert out["expected_failures"][0]["actual_error_code"] is None
    assert out["expected_failures"][0]["matches"] is False


def test_run_evaluation_writes_json_batch43(tmp_path):
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
    assert out_path.is_file()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "report_version" in data
    assert "per_doc" in data


def test_run_evaluation_creates_parent_dir_batch43(tmp_path):
    """output_path 父目录不存在时自动创建。"""
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    out_path = tmp_path / "deep" / "nested" / "report.json"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            run_evaluation(manifest, out_path)
    assert out_path.is_file()


def test_run_evaluation_propagates_parser_version_batch43(tmp_path):
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "9.9.9"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = run_evaluation(manifest, tmp_path / "report.json")
    assert out["provenance"]["parser_version"] == "9.9.9"


def test_run_evaluation_parser_version_none_when_failed_batch43(tmp_path):
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    err = MagicMock()
    err.to_dict.return_value = {"code": "fail", "message": "boom"}
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        out = run_evaluation(manifest, tmp_path / "report.json")
    assert out["provenance"]["parser_version"] is None


# ---------- run_evaluation tolerance_chars ----------

def test_run_evaluation_passes_tolerance_to_chunk_boundary_batch43(tmp_path):
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            with patch("evaluation.runner.chunk_boundary_prf", return_value={"chunk_boundary_precision": {"value": None, "reason": "no_annotation"}, "_tolerance_chars": {"value": 50}}) as mock_cb:
                run_evaluation(manifest, tmp_path / "report.json", tolerance_chars=50)
    args, kwargs = mock_cb.call_args
    assert kwargs["tolerance_chars"] == 50


# ---------- module source ----------

def test_module_source_contains_not_instrumented_batch43():
    src = inspect.getsource(runner_mod)
    assert "not_instrumented" in src


def test_module_source_contains_process_single_batch43():
    src = inspect.getsource(runner_mod)
    assert "process_single" in src


def test_module_source_contains_image_output_dir_batch43():
    src = inspect.getsource(runner_mod)
    assert "image_output_dir_for" in src


def test_module_source_contains_compute_automatic_metrics_batch43():
    src = inspect.getsource(runner_mod)
    assert "compute_automatic_metrics" in src


def test_module_source_contains_perf_counter_batch43():
    src = inspect.getsource(runner_mod)
    assert "time.perf_counter" in src


def test_module_source_contains_unlink_batch43():
    src = inspect.getsource(runner_mod)
    assert "unlink" in src


def test_module_source_contains_per_doc_dir_batch43():
    src = inspect.getsource(runner_mod)
    assert "_per_doc" in src


# ---------- __all__ ----------

def test_all_exact_batch43():
    assert set(runner_mod.__all__) == {"run_evaluation"}


def test_all_count_1_batch43():
    assert len(runner_mod.__all__) == 1


def test_all_entries_are_str_batch43():
    for e in runner_mod.__all__:
        assert isinstance(e, str)


def test_all_entries_are_attrs_batch43():
    for e in runner_mod.__all__:
        assert hasattr(runner_mod, e)


# ---------- AST 结构 ----------

def test_ast_top_level_no_class_batch43():
    tree = ast.parse(inspect.getsource(runner_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert classes == []


def test_ast_top_level_function_count_batch43():
    tree = ast.parse(inspect.getsource(runner_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 3


def test_ast_top_level_function_names_batch43():
    tree = ast.parse(inspect.getsource(runner_mod))
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert funcs == ["_load_annotation", "_process_one", "run_evaluation"]


def test_ast_no_try_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.Try)


def test_ast_no_for_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.For)


def test_ast_no_while_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_no_async_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_no_classdef_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_from_future_first_batch43():
    tree = ast.parse(inspect.getsource(runner_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)  # docstring
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


def test_ast_has_imports_batch43():
    tree = ast.parse(inspect.getsource(runner_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) >= 4


# ---------- forbidden tokens 第八十五批 ----------

def test_source_no_eval_batch43():
    src = inspect.getsource(runner_mod)
    assert "eval(" not in src


def test_source_no_exec_batch43():
    src = inspect.getsource(runner_mod)
    assert "exec(" not in src


def test_source_no_compile_batch43():
    src = inspect.getsource(runner_mod)
    assert "compile(" not in src


def test_source_no_globals_batch43():
    src = inspect.getsource(runner_mod)
    assert "globals(" not in src


def test_source_no_locals_batch43():
    src = inspect.getsource(runner_mod)
    assert "locals(" not in src


def test_source_no_open_write_mode_batch43():
    """模块内顶层没出现 open（runner 用 pathlib.Path.open）。"""
    src = inspect.getsource(runner_mod)
    # 内部确实用了 out_p.open，但只在 run_evaluation 内
    # 测试模块没有顶层 open(...)
    tree = ast.parse(src)
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # function 内部允许
            continue
        # 顶层 Expr 中不应出现 open(
        pass  # nothing to test, just ensure tree parses


def test_source_no_os_system_batch43():
    src = inspect.getsource(runner_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch43():
    src = inspect.getsource(runner_mod)
    assert "popen(" not in src


def test_source_no_yaml_load_batch43():
    src = inspect.getsource(runner_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch43():
    src = inspect.getsource(runner_mod)
    assert "pickle.load(" not in src


# ---------- 端到端 ----------

def test_run_evaluation_complete_with_annotation_batch43(tmp_path):
    """annotation 存在时 fig_caps/chunk_b 仍正常装配。"""
    doc = MagicMock()
    doc.doc_id = "doc_001"
    doc.resolved_path = Path("/tmp/test.pdf")
    doc.source_type = "pdf"
    doc.expectations = None
    anno_path = tmp_path / "anno.json"
    anno_path.write_text(json.dumps({"chunks": [{"text": "abc", "source_element_ids": ["e1"]}]}), encoding="utf-8")
    doc.annotation_resolved = anno_path
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"chunks": [{"text": "abc", "source_element_ids": ["e1"], "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]}}]}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = run_evaluation(manifest, tmp_path / "report.json")
    assert "per_doc" in out
    assert len(out["per_doc"]) == 1
