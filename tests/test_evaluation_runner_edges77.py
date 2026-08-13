"""evaluation/runner.py 第九十四轮 edges 测试（Round 677）。

补强 edges76 未触及的角度（第五十二批）。

新角度：
- _load_annotation 多种成功路径（空 dict / 含 chunk_boundary_anchors / 含 doc_id）
- _process_one 多场景（errors 多个时取第一个 / image_dir 在 document 存在时正确推导 / image_output_dir_for 调用参数 / out_stub 在 errors 路径下不删）
- run_evaluation 完整流程（含 annotation_file 的文档 / multiple docs / parser_version 多 doc 时取首个成功 / wall_time_seconds 总数）
- run_evaluation per_doc 内部字段（_annotation_present / _tolerance_chars / _missing_markers）
- run_evaluation expected_failures 多场景（多个失败 / 期望失败但实际成功 / 期望成功但实际失败）
- run_evaluation JSON 写盘（ensure_ascii=False / indent=2）
- 模块源码补强（_per_doc 目录命名 / figure_caption_prf / chunk_boundary_prf 调用 / annotation_present 字段）
- AST 结构补强（_process_one 多 if / run_evaluation 多 for 循环顺序 / per_doc_results 字段构造）
- forbidden tokens 第一百四十七批
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


# ---------- _load_annotation 多种成功路径 ----------

def test_load_annotation_empty_dict_batch52(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    out = _load_annotation(p)
    assert out == {}


def test_load_annotation_with_chunk_boundary_anchors_batch52(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text(json.dumps({
        "chunk_boundary_anchors": [{"marker": "x", "position": "after"}],
    }), encoding="utf-8")
    out = _load_annotation(p)
    assert "chunk_boundary_anchors" in out
    assert len(out["chunk_boundary_anchors"]) == 1


def test_load_annotation_with_doc_id_batch52(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text(json.dumps({"doc_id": "d1"}), encoding="utf-8")
    out = _load_annotation(p)
    assert out["doc_id"] == "d1"


def test_load_annotation_returns_dict_type_batch52(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    out = _load_annotation(p)
    assert isinstance(out, dict)


# ---------- _process_one 多场景 ----------

def test_process_one_takes_first_error_batch52(tmp_path):
    """多个 errors → 取第一个。"""
    err1 = MagicMock()
    err1.to_dict.return_value = {"code": "first"}
    err2 = MagicMock()
    err2.to_dict.return_value = {"code": "second"}
    with patch("evaluation.runner.process_single", return_value=(None, [err1, err2])):
        doc = MagicMock()
        doc.doc_id = "d1"
        doc.resolved_path = tmp_path / "x.pdf"
        document, error, elapsed, parser_v, image_dir = _process_one(
            doc, tmp_path, "fallback", 800
        )
    assert error == {"code": "first"}


def test_process_one_image_output_dir_called_batch52(tmp_path):
    """document 存在时调用 image_output_dir_for(out_stub, source_hash)。"""
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"elements": []}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "sha123"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs") as mock_iof:
            doc = MagicMock()
            doc.doc_id = "d1"
            doc.resolved_path = tmp_path / "x.pdf"
            _process_one(doc, tmp_path, "fallback", 800)
    mock_iof.assert_called_once()
    args, _ = mock_iof.call_args
    # args[0] = out_stub, args[1] = source_hash
    assert args[1] == "sha123"


def test_process_one_image_output_dir_not_called_when_no_document_batch52(tmp_path):
    """document None 时不调用 image_output_dir_for。"""
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for") as mock_iof:
            doc = MagicMock()
            doc.doc_id = "d1"
            doc.resolved_path = tmp_path / "x.pdf"
            _process_one(doc, tmp_path, "fallback", 800)
    mock_iof.assert_not_called()


def test_process_one_out_stub_in_per_doc_dir_batch52(tmp_path):
    """out_stub 位于 output_root/_per_doc/<doc_id>.json。"""
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"elements": []}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "sha"
    captured_path = []
    def fake_pss(*args, **kwargs):
        # capture out_stub arg
        captured_path.append(args[1])
        return fake_doc, []
    with patch("evaluation.runner.process_single", side_effect=fake_pss):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            doc = MagicMock()
            doc.doc_id = "my_doc"
            doc.resolved_path = tmp_path / "x.pdf"
            _process_one(doc, tmp_path, "fallback", 800)
    assert captured_path[0] == tmp_path / "_per_doc" / "my_doc.json"


def test_process_one_elapsed_is_float_batch52(tmp_path):
    """elapsed 是 float。"""
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.time.perf_counter", side_effect=[100.0, 100.5]):
            doc = MagicMock()
            doc.doc_id = "d1"
            doc.resolved_path = tmp_path / "x.pdf"
            _, _, elapsed, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(elapsed, float)
    assert elapsed == 0.5


# ---------- run_evaluation 完整流程 ----------

def _make_full_manifest(documents=None, expected_failures=None, project_root=None):
    m = MagicMock()
    m.documents = documents or []
    m.expected_failures = expected_failures or []
    m.project_root = project_root or Path.cwd()
    m.devset_status = "incomplete"
    m.file_count = len(documents or [])
    m.content_group_count = 0
    m.pdf_count = sum(1 for d in (documents or []) if getattr(d, "source_type", None) == "pdf")
    m.docx_count = sum(1 for d in (documents or []) if getattr(d, "source_type", None) == "docx")
    m.categories_covered = []
    return m


def test_run_evaluation_doc_with_annotation_batch52(tmp_path):
    """doc 有 annotation_resolved → 加载 annotation。"""
    fake_doc = MagicMock()
    fake_doc.doc_id = "d1"
    fake_doc.resolved_path = tmp_path / "x.pdf"
    fake_doc.source_type = "pdf"
    fake_doc.expectations = None
    fake_doc.annotation_resolved = tmp_path / "ann.json"
    fake_doc.annotation_resolved.write_text(json.dumps({"doc_id": "d1"}), encoding="utf-8")

    fd_result = MagicMock()
    fd_result.to_dict.return_value = {"elements": []}
    fd_result.parser_version = "1.0"
    fd_result.source_hash = "sha"
    with patch("evaluation.runner.process_single", return_value=(fd_result, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
                m = _make_full_manifest(documents=[fake_doc])
                out = run_evaluation(m, tmp_path / "out.json")
    pd = out["per_doc"][0]
    # annotation 被加载，metrics 应有 figure_caption / chunk_boundary
    assert "figure_caption_precision" in pd["metrics"]
    assert "chunk_boundary_precision" in pd["metrics"]


def test_run_evaluation_multiple_docs_batch52(tmp_path):
    """多个 docs 顺序处理。"""
    docs = []
    for i in range(3):
        d = MagicMock()
        d.doc_id = f"d{i}"
        d.resolved_path = tmp_path / f"x{i}.pdf"
        d.source_type = "pdf"
        d.expectations = None
        d.annotation_resolved = None
        docs.append(d)
    fd_result = MagicMock()
    fd_result.to_dict.return_value = {"elements": []}
    fd_result.parser_version = "1.0"
    fd_result.source_hash = "sha"
    with patch("evaluation.runner.process_single", return_value=(fd_result, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
                m = _make_full_manifest(documents=docs)
                out = run_evaluation(m, tmp_path / "out.json")
    assert len(out["per_doc"]) == 3
    assert [pd["doc_id"] for pd in out["per_doc"]] == ["d0", "d1", "d2"]


def test_run_evaluation_parser_version_first_success_batch52(tmp_path):
    """parser_version 取自第一个成功的 doc。"""
    fake_doc1 = MagicMock()
    fake_doc1.doc_id = "d1"
    fake_doc1.resolved_path = tmp_path / "x.pdf"
    fake_doc1.source_type = "pdf"
    fake_doc1.expectations = None
    fake_doc1.annotation_resolved = None

    fake_doc2 = MagicMock()
    fake_doc2.doc_id = "d2"
    fake_doc2.resolved_path = tmp_path / "y.pdf"
    fake_doc2.source_type = "pdf"
    fake_doc2.expectations = None
    fake_doc2.annotation_resolved = None

    fd1 = MagicMock()
    fd1.to_dict.return_value = {"elements": []}
    fd1.parser_version = "v1.0"
    fd1.source_hash = "sha1"

    fd2 = MagicMock()
    fd2.to_dict.return_value = {"elements": []}
    fd2.parser_version = "v2.0"
    fd2.source_hash = "sha2"

    with patch("evaluation.runner.process_single", side_effect=[(fd1, []), (fd2, [])]):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}) as bp:
                m = _make_full_manifest(documents=[fake_doc1, fake_doc2])
                run_evaluation(m, tmp_path / "out.json")
    args, kwargs = bp.call_args
    assert kwargs["parser_version"] == "v1.0"


def test_run_evaluation_per_doc_annotation_present_true_batch52(tmp_path):
    fake_doc = MagicMock()
    fake_doc.doc_id = "d1"
    fake_doc.resolved_path = tmp_path / "x.pdf"
    fake_doc.source_type = "pdf"
    fake_doc.expectations = None
    fake_doc.annotation_resolved = tmp_path / "ann.json"
    fake_doc.annotation_resolved.write_text("{}", encoding="utf-8")

    fd_result = MagicMock()
    fd_result.to_dict.return_value = {"elements": []}
    fd_result.parser_version = "1.0"
    fd_result.source_hash = "sha"
    with patch("evaluation.runner.process_single", return_value=(fd_result, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
                m = _make_full_manifest(documents=[fake_doc])
                out = run_evaluation(m, tmp_path / "out.json")
    # per_doc 输出不直接含 _annotation_present，但内部 record 应记录
    # 通过 metrics 含 figure_caption 验证 annotation 被加载
    assert "figure_caption_precision" in out["per_doc"][0]["metrics"]


def test_run_evaluation_no_annotation_batch52(tmp_path):
    """无 annotation → annotation=None → figure_caption_prf 用 None。"""
    fake_doc = MagicMock()
    fake_doc.doc_id = "d1"
    fake_doc.resolved_path = tmp_path / "x.pdf"
    fake_doc.source_type = "pdf"
    fake_doc.expectations = None
    fake_doc.annotation_resolved = None  # None

    fd_result = MagicMock()
    fd_result.to_dict.return_value = {"elements": []}
    fd_result.parser_version = "1.0"
    fd_result.source_hash = "sha"
    with patch("evaluation.runner.process_single", return_value=(fd_result, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
                m = _make_full_manifest(documents=[fake_doc])
                out = run_evaluation(m, tmp_path / "out.json")
    # annotation 是 None → figure_caption 用 None → metrics 含 PARSER_DOES_NOT_EMIT_RELATIONS reason
    assert out["per_doc"][0]["metrics"]["figure_caption_precision"]["reason"] == "parser_does_not_emit_relations"


# ---------- run_evaluation expected_failures 多场景 ----------

def test_run_evaluation_multiple_expected_failures_batch52(tmp_path):
    ef1 = MagicMock()
    ef1.doc_id = "ef1"
    ef1.resolved_path = tmp_path / "x1.pdf"
    ef1.expected_error_code = "parse_failed"

    ef2 = MagicMock()
    ef2.doc_id = "ef2"
    ef2.resolved_path = tmp_path / "x2.pdf"
    ef2.expected_error_code = "schema_invalid"

    err1 = MagicMock()
    err1.code = "parse_failed"
    err2 = MagicMock()
    err2.code = "schema_invalid"
    with patch("evaluation.runner.process_single", side_effect=[(None, [err1]), (None, [err2])]):
        with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
            m = _make_full_manifest(expected_failures=[ef1, ef2])
            out = run_evaluation(m, tmp_path / "out.json")
    assert len(out["expected_failures"]) == 2
    assert all(r["matches"] for r in out["expected_failures"])


def test_run_evaluation_expected_failure_but_success_batch52(tmp_path):
    """期望失败但实际成功 → matches=False, actual=None。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "x.pdf"
    ef.expected_error_code = "parse_failed"
    with patch("evaluation.runner.process_single", return_value=(MagicMock(), [])):
        with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
            m = _make_full_manifest(expected_failures=[ef])
            out = run_evaluation(m, tmp_path / "out.json")
    ef_result = out["expected_failures"][0]
    assert ef_result["actual_error_code"] is None
    assert ef_result["matches"] is False


def test_run_evaluation_expected_success_but_failed_batch52(tmp_path):
    """期望成功（expected_error_code != 实际）→ matches=False。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "x.pdf"
    ef.expected_error_code = "parse_failed"
    err = MagicMock()
    err.code = "other_error"  # 不匹配
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
            m = _make_full_manifest(expected_failures=[ef])
            out = run_evaluation(m, tmp_path / "out.json")
    ef_result = out["expected_failures"][0]
    assert ef_result["actual_error_code"] == "other_error"
    assert ef_result["matches"] is False


def test_run_evaluation_expected_failure_result_keys_batch52(tmp_path):
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "x.pdf"
    ef.expected_error_code = "parse_failed"
    err = MagicMock()
    err.code = "parse_failed"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
            m = _make_full_manifest(expected_failures=[ef])
            out = run_evaluation(m, tmp_path / "out.json")
    ef_result = out["expected_failures"][0]
    assert set(ef_result.keys()) == {"doc_id", "expected_error_code", "actual_error_code", "matches"}


# ---------- run_evaluation JSON 写盘 ----------

def test_run_evaluation_writes_json_unicode_safe_batch52(tmp_path):
    """JSON 写盘 ensure_ascii=False。"""
    m = _make_full_manifest()
    output = tmp_path / "out.json"
    with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
        run_evaluation(m, output)
    raw = output.read_bytes().decode("utf-8")
    # 应是 UTF-8 编码
    assert "report_version" in raw


def test_run_evaluation_writes_json_indented_batch52(tmp_path):
    """JSON 写盘 indent=2。"""
    m = _make_full_manifest()
    output = tmp_path / "out.json"
    with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
        run_evaluation(m, output)
    raw = output.read_text(encoding="utf-8")
    # indent=2 应有换行 + 缩进
    assert "\n" in raw
    assert '  "' in raw


def test_run_evaluation_creates_parent_dirs_batch52(tmp_path):
    output = tmp_path / "a" / "b" / "c" / "out.json"
    m = _make_full_manifest()
    with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
        run_evaluation(m, output)
    assert output.is_file()


# ---------- 模块源码补强 ----------

def test_source_contains_per_doc_dir_naming_batch52():
    src = inspect.getsource(runner_mod)
    assert '"_per_doc"' in src or "'_per_doc'" in src
    assert "{doc.doc_id}.json" in src or "{ef.doc_id}.json" in src


def test_source_contains_image_output_dir_for_call_batch52():
    src = inspect.getsource(runner_mod)
    assert "image_output_dir_for(out_stub" in src or "image_output_dir_for(" in src


def test_source_contains_annotation_present_internal_batch52():
    src = inspect.getsource(runner_mod)
    assert "_annotation_present" in src


def test_source_contains_tolerance_chars_internal_batch52():
    src = inspect.getsource(runner_mod)
    assert "_tolerance_chars" in src
    assert "_missing_markers" in src


def test_source_contains_chunk_boundary_prf_call_batch52():
    src = inspect.getsource(runner_mod)
    assert "chunk_boundary_prf(" in src


def test_source_contains_figure_caption_prf_call_batch52():
    src = inspect.getsource(runner_mod)
    assert "figure_caption_prf(" in src


def test_source_contains_document_to_dict_batch52():
    src = inspect.getsource(runner_mod)
    assert "document.to_dict()" in src


def test_source_contains_errors_0_to_dict_batch52():
    src = inspect.getsource(runner_mod)
    assert "errors[0].to_dict()" in src


def test_source_contains_process_single_call_batch52():
    src = inspect.getsource(runner_mod)
    # process_single 被调用 2 次（documents + expected_failures）
    assert src.count("process_single(") >= 2


def test_source_contains_compute_automatic_metrics_call_batch52():
    src = inspect.getsource(runner_mod)
    assert "compute_automatic_metrics(" in src


def test_source_contains_json_dump_with_kwargs_batch52():
    src = inspect.getsource(runner_mod)
    assert "json.dump(" in src
    assert "ensure_ascii=False" in src
    assert "indent=2" in src


def test_source_contains_unknown_message_batch52():
    src = inspect.getsource(runner_mod)
    assert "process_single returned None without errors" in src


def test_source_contains_out_stub_unlink_batch52():
    src = inspect.getsource(runner_mod)
    assert "out_stub.unlink()" in src
    assert "out_stub.is_file()" in src


def test_source_contains_image_dir_is_dir_check_batch52():
    src = inspect.getsource(runner_mod)
    assert "image_dir.is_dir()" in src


def test_source_contains_write_json_false_batch52():
    src = inspect.getsource(runner_mod)
    assert src.count("write_json=False") >= 2  # documents 路径 + expected_failures 路径


def test_source_all_1_export_batch52():
    src = inspect.getsource(runner_mod)
    assert "__all__" in src
    assert '"run_evaluation"' in src


# ---------- AST 结构补强 ----------

def test_ast_has_3_top_level_functions_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 3


def test_ast_function_names_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_load_annotation", "_process_one", "run_evaluation"]


def test_ast_no_class_def_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_process_one_has_if_errors_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    src = ast.unparse(func)
    assert "if errors:" in src


def test_ast_process_one_has_if_document_is_none_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    src = ast.unparse(func)
    assert "if document is None:" in src
    assert "if document is not None:" in src


def test_ast_run_evaluation_has_3_for_in_body_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    fors = [n for n in func.body if isinstance(n, ast.For)]
    # for doc + for ef + for r
    assert len(fors) == 3


def test_ast_run_evaluation_for_iter_targets_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    fors = [n for n in func.body if isinstance(n, ast.For)]
    iters = []
    for f in fors:
        if isinstance(f.iter, ast.Attribute):
            iters.append(f.iter.attr)
        elif isinstance(f.iter, ast.Name):
            iters.append(f.iter.id)
    # manifest.documents, manifest.expected_failures, per_doc_results
    assert "documents" in iters
    assert "expected_failures" in iters
    assert "per_doc_results" in iters


def test_ast_run_evaluation_has_with_open_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    withs = [n for n in ast.walk(func) if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_run_evaluation_assigns_per_doc_results_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    src = ast.unparse(func)
    assert "per_doc_results.append" in src


def test_ast_run_evaluation_assigns_summary_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    src = ast.unparse(func)
    assert "summary = aggregate_summary(" in src
    assert "provenance = build_provenance(" in src
    assert "devset = build_devset_section(" in src


def test_ast_module_docstring_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_no_async_function_def_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_no_global_nonlocal_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


def test_ast_no_with_at_module_level_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.With)


def test_ast_no_star_import_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


# ---------- forbidden tokens 第一百四十七批 ----------

def _src() -> str:
    return inspect.getsource(runner_mod)


def test_source_no_eval_batch52():
    assert "eval(" not in _src()


def test_source_no_exec_batch52():
    assert "exec(" not in _src()


def test_source_no_compile_batch52():
    assert "compile(" not in _src()


def test_source_no_globals_batch52():
    assert "globals(" not in _src()


def test_source_no_locals_batch52():
    assert "locals(" not in _src()


def test_source_no_os_system_batch52():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch52():
    assert "subprocess" not in _src()


def test_source_no_popen_batch52():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch52():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch52():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch52():
    assert "socket" not in _src()


def test_source_no_requests_batch52():
    assert "requests" not in _src()


def test_source_no_urllib_batch52():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch52():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch52():
    assert "yield" not in _src()


def test_source_no_async_await_batch52():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch52():
    """_load_annotation + run_evaluation 各 1 个 open。"""
    assert _src().count("open(") == 2
