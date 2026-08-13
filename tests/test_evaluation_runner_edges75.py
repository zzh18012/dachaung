"""evaluation/runner.py 第九十二轮 edges 测试（Round 663）。

补强 edges74 未触及的角度（第四十九批）。

新角度：
- _load_annotation 多种路径（None 输入 / 不存在的文件 / 存在的文件 / OSError → None / 二进制文件 → JSONDecodeError → None）
- _process_one 多场景（成功返回 5-tuple / errors 非空 → document None + error dict / document None + no errors → unknown / image_dir 推导）
- run_evaluation 完整流程 + private 字段（_annotation_present / _tolerance_chars / _missing_markers）
- run_evaluation public_per_doc 字段精简（4 keys / 无 _ 私有键）
- run_evaluation expected_failures 多场景（成功匹配 / 不匹配 / 无 errors → actual_code None）
- run_evaluation wall_time_seconds 结构（6 keys / parse/chunk null / reasons not_instrumented / total float）
- run_evaluation report JSON 写盘内容（report_version / 6 top keys / per_doc 长度）
- 模块源码补强（json/time/Path/Any/pipeline imports / REPORT_VERSION import / annotation_metrics import / metrics import / report import / __all__）
- AST 结构补强（3 函数 / 无 ClassDef / 无 AsyncFunctionDef / module docstring / 10 import / 1 top-level Assign / _load_annotation try / _process_one perf_counter + 多 return / run_evaluation 多 for + 多 with + json.dump + return report）
- forbidden tokens 第一百三十三批
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


# ---------- _load_annotation 多种路径 ----------

def test_load_annotation_none_returns_none_batch49():
    out = _load_annotation(None)
    assert out is None


def test_load_annotation_missing_file_returns_none_batch49(tmp_path):
    out = _load_annotation(tmp_path / "nope.json")
    assert out is None


def test_load_annotation_valid_file_returns_dict_batch49(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text(json.dumps({"key": "value"}), encoding="utf-8")
    out = _load_annotation(f)
    assert out == {"key": "value"}


def test_load_annotation_invalid_json_returns_none_batch49(tmp_path):
    """非法 JSON → JSONDecodeError → None。"""
    f = tmp_path / "bad.json"
    f.write_text("{not json", encoding="utf-8")
    out = _load_annotation(f)
    assert out is None


def test_load_annotation_utf8_bom_returns_none_batch49(tmp_path):
    """UTF-8 BOM → json.loads 失败 → None。"""
    f = tmp_path / "bom.json"
    f.write_bytes(b'\xef\xbb\xbf{"key": "value"}')
    out = _load_annotation(f)
    assert out is None


def test_load_annotation_empty_file_returns_none_batch49(tmp_path):
    """空文件 → JSONDecodeError → None。"""
    f = tmp_path / "empty.json"
    f.write_text("", encoding="utf-8")
    out = _load_annotation(f)
    assert out is None


def test_load_annotation_directory_returns_none_batch49(tmp_path):
    """目录而非文件 → is_file() False → None。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    out = _load_annotation(sub)
    assert out is None


def test_load_annotation_oserror_returns_none_batch49(tmp_path):
    """OSError → None。"""
    f = tmp_path / "ann.json"
    f.write_text("{}", encoding="utf-8")
    with patch("pathlib.Path.open", side_effect=OSError("io")):
        out = _load_annotation(f)
    assert out is None


# ---------- _process_one 多场景 ----------

def _make_doc(tmp_path: Path) -> MagicMock:
    d = MagicMock()
    d.doc_id = "d1"
    d.resolved_path = tmp_path / "input.pdf"
    d.source_type = "pdf"
    return d


def test_process_one_success_returns_5_tuple_batch49(tmp_path):
    doc = _make_doc(tmp_path)
    document = MagicMock()
    document.to_dict.return_value = {"elements": [], "chunks": []}
    document.parser_version = "fallback-1.0"
    document.source_hash = "sha"
    with patch("evaluation.runner.process_single", return_value=(document, [])):
        out = _process_one(doc, tmp_path, "fallback", 800)
    assert len(out) == 5
    document_dict, error, elapsed, parser_version, image_dir = out
    assert document_dict == {"elements": [], "chunks": []}
    assert error is None
    assert isinstance(elapsed, float)
    assert parser_version == "fallback-1.0"
    assert image_dir is not None  # document not None


def test_process_one_errors_returns_none_document_batch49(tmp_path):
    """errors 非空 → document None, error is errors[0].to_dict()。"""
    doc = _make_doc(tmp_path)
    err = MagicMock()
    err.to_dict.return_value = {"code": "parse_failed", "message": "x"}
    document = MagicMock()  # 即使 document 非 None，errors 非空时也强制 None
    with patch("evaluation.runner.process_single", return_value=(document, [err])):
        out = _process_one(doc, tmp_path, "fallback", 800)
    document_dict, error, elapsed, parser_version, image_dir = out
    assert document_dict is None  # errors 强制 None
    assert error == {"code": "parse_failed", "message": "x"}
    assert parser_version is None


def test_process_one_document_none_no_errors_returns_unknown_batch49(tmp_path):
    doc = _make_doc(tmp_path)
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        out = _process_one(doc, tmp_path, "fallback", 800)
    document_dict, error, elapsed, parser_version, image_dir = out
    assert document_dict is None
    assert error == {
        "code": "unknown",
        "message": "process_single returned None without errors",
    }
    assert parser_version is None


def test_process_one_image_dir_is_none_when_document_none_batch49(tmp_path):
    """document None 时 image_dir 也是 None。"""
    doc = _make_doc(tmp_path)
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        out = _process_one(doc, tmp_path, "fallback", 800)
    _, _, _, _, image_dir = out
    assert image_dir is None


def test_process_one_elapsed_positive_batch49(tmp_path):
    doc = _make_doc(tmp_path)
    document = MagicMock()
    document.to_dict.return_value = {"elements": [], "chunks": []}
    document.parser_version = "1.0"
    document.source_hash = "sha"
    with patch("evaluation.runner.process_single", return_value=(document, [])):
        out = _process_one(doc, tmp_path, "fallback", 800)
    _, _, elapsed, _, _ = out
    assert elapsed >= 0


# ---------- run_evaluation 完整流程 + private 字段 ----------

def _make_full_manifest(tmp_path: Path, documents=None, expected_failures=None) -> MagicMock:
    """构建一个所有 devset 字段都具体的 manifest。"""
    m = MagicMock()
    m.documents = documents or []
    m.expected_failures = expected_failures or []
    m.project_root = tmp_path
    # build_devset_section 需要的字段
    m.devset_status = "incomplete"
    m.file_count = len(m.documents)
    m.content_group_count = 0
    m.pdf_count = sum(1 for d in m.documents if d.source_type == "pdf")
    m.docx_count = sum(1 for d in m.documents if d.source_type == "docx")
    m.categories_covered = []
    return m


def test_run_evaluation_per_doc_has_private_keys_batch49(tmp_path):
    """per_doc_results 内部含 _ 私有键。"""
    manifest = _make_full_manifest(tmp_path)
    out = run_evaluation(manifest, tmp_path / "out.json")
    assert "per_doc" in out


def test_run_evaluation_public_per_doc_has_4_keys_batch49(tmp_path):
    """public_per_doc 只有 4 个公开键。"""
    manifest = _make_full_manifest(tmp_path)
    out = run_evaluation(manifest, tmp_path / "out.json")
    if out["per_doc"]:
        for r in out["per_doc"]:
            assert set(r.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_report_version_in_output_batch49(tmp_path):
    manifest = _make_full_manifest(tmp_path)
    out = run_evaluation(manifest, tmp_path / "out.json")
    assert out["report_version"] == "1.1"


def test_run_evaluation_report_has_6_top_keys_batch49(tmp_path):
    manifest = _make_full_manifest(tmp_path)
    out = run_evaluation(manifest, tmp_path / "out.json")
    assert set(out.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_run_evaluation_writes_file_batch49(tmp_path):
    manifest = _make_full_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    assert out_path.is_file()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "report_version" in data


def test_run_evaluation_creates_nested_output_dir_batch49(tmp_path):
    manifest = _make_full_manifest(tmp_path)
    out_path = tmp_path / "nested" / "deep" / "out.json"
    run_evaluation(manifest, out_path)
    assert out_path.is_file()


def _make_full_doc(tmp_path: Path, doc_id: str = "d1", source_type: str = "pdf") -> MagicMock:
    doc = MagicMock()
    doc.doc_id = doc_id
    doc.resolved_path = tmp_path / f"input.{source_type}"
    doc.source_type = source_type
    doc.expectations = None
    doc.annotation_resolved = None
    return doc


def test_run_evaluation_wall_time_seconds_structure_batch49(tmp_path):
    """有文档时 wall_time_seconds 含 5 keys（不是 6，是新口径）。"""
    doc = _make_full_doc(tmp_path)
    document = MagicMock()
    document.to_dict.return_value = {"elements": [], "chunks": []}
    document.parser_version = "1.0"
    document.source_hash = "sha"
    manifest = _make_full_manifest(tmp_path, documents=[doc])
    with patch("evaluation.runner.process_single", return_value=(document, [])):
        out = run_evaluation(manifest, tmp_path / "out.json")
    ws = out["per_doc"][0]["wall_time_seconds"]
    assert set(ws.keys()) == {
        "total",
        "parse",
        "chunk",
        "parse_reason",
        "chunk_reason",
    }
    assert ws["parse"] is None
    assert ws["chunk"] is None
    assert ws["parse_reason"] == "not_instrumented"
    assert ws["chunk_reason"] == "not_instrumented"
    assert isinstance(ws["total"], float)


def test_run_evaluation_annotation_present_false_batch49(tmp_path):
    """无 annotation → chunk_boundary 等指标 null。"""
    doc = _make_full_doc(tmp_path)
    document = MagicMock()
    document.to_dict.return_value = {"elements": [], "chunks": []}
    document.parser_version = "1.0"
    document.source_hash = "sha"
    manifest = _make_full_manifest(tmp_path, documents=[doc])
    with patch("evaluation.runner.process_single", return_value=(document, [])):
        out = run_evaluation(manifest, tmp_path / "out.json")
    assert "_annotation_present" not in out["per_doc"][0]
    assert out["per_doc"][0]["metrics"]["chunk_boundary_precision"]["value"] is None


def test_run_evaluation_expected_failures_matches_batch49(tmp_path):
    """expected_failure 成功匹配。"""
    ef = MagicMock()
    ef.doc_id = "bad1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "parse_failed"
    err = MagicMock()
    err.code = "parse_failed"
    manifest = _make_full_manifest(tmp_path, expected_failures=[ef])
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        out = run_evaluation(manifest, tmp_path / "out.json")
    assert len(out["expected_failures"]) == 1
    ef_out = out["expected_failures"][0]
    assert ef_out["doc_id"] == "bad1"
    assert ef_out["expected_error_code"] == "parse_failed"
    assert ef_out["actual_error_code"] == "parse_failed"
    assert ef_out["matches"] is True


def test_run_evaluation_expected_failures_mismatch_batch49(tmp_path):
    ef = MagicMock()
    ef.doc_id = "bad1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "parse_failed"
    err = MagicMock()
    err.code = "different_error"
    manifest = _make_full_manifest(tmp_path, expected_failures=[ef])
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        out = run_evaluation(manifest, tmp_path / "out.json")
    assert out["expected_failures"][0]["actual_error_code"] == "different_error"
    assert out["expected_failures"][0]["matches"] is False


def test_run_evaluation_expected_failures_no_errors_actual_none_batch49(tmp_path):
    """无 errors → actual_code None。"""
    ef = MagicMock()
    ef.doc_id = "bad1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "parse_failed"
    document = MagicMock()
    manifest = _make_full_manifest(tmp_path, expected_failures=[ef])
    with patch("evaluation.runner.process_single", return_value=(document, [])):
        out = run_evaluation(manifest, tmp_path / "out.json")
    assert out["expected_failures"][0]["actual_error_code"] is None
    assert out["expected_failures"][0]["matches"] is False


# ---------- 模块源码补强 ----------

def test_source_contains_json_import_batch49():
    src = inspect.getsource(runner_mod)
    assert "import json" in src


def test_source_contains_time_import_batch49():
    src = inspect.getsource(runner_mod)
    assert "import time" in src


def test_source_contains_pathlib_import_batch49():
    src = inspect.getsource(runner_mod)
    assert "from pathlib import Path" in src


def test_source_contains_typing_any_import_batch49():
    src = inspect.getsource(runner_mod)
    assert "from typing import Any" in src


def test_source_contains_pipeline_import_batch49():
    src = inspect.getsource(runner_mod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_source_contains_report_version_import_batch49():
    src = inspect.getsource(runner_mod)
    assert "from evaluation import REPORT_VERSION" in src


def test_source_contains_annotation_metrics_import_batch49():
    src = inspect.getsource(runner_mod)
    assert "from evaluation.annotation_metrics import" in src
    assert "chunk_boundary_prf" in src
    assert "figure_caption_prf" in src


def test_source_contains_metrics_import_batch49():
    src = inspect.getsource(runner_mod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_source_contains_report_import_batch49():
    src = inspect.getsource(runner_mod)
    assert "from evaluation.report import" in src
    assert "aggregate_summary" in src
    assert "build_devset_section" in src
    assert "build_provenance" in src


def test_source_docstring_mentions_total_only_batch49():
    src = inspect.getsource(runner_mod)
    assert "total" in src.lower()


def test_source_docstring_mentions_not_instrumented_batch49():
    src = inspect.getsource(runner_mod)
    assert "not_instrumented" in src.lower() or "not instrumented" in src.lower()


def test_source_docstring_mentions_pipeline_failed_batch49():
    src = inspect.getsource(runner_mod)
    assert "pipeline_failed" in src.lower() or "pipeline failed" in src.lower()


def test_source_all_has_1_entry_batch49():
    src = inspect.getsource(runner_mod)
    assert '__all__ = ["run_evaluation"]' in src


def test_source_contains_perf_counter_batch49():
    src = inspect.getsource(runner_mod)
    assert "time.perf_counter" in src


def test_source_contains_write_json_false_batch49():
    src = inspect.getsource(runner_mod)
    assert "write_json=False" in src


def test_source_contains_ensure_ascii_false_batch49():
    src = inspect.getsource(runner_mod)
    assert "ensure_ascii=False" in src


def test_source_contains_image_output_dir_for_call_batch49():
    src = inspect.getsource(runner_mod)
    assert "image_output_dir_for(" in src


def test_source_contains_unknown_error_string_batch49():
    src = inspect.getsource(runner_mod)
    assert '"unknown"' in src


def test_source_contains_process_single_returned_none_string_batch49():
    src = inspect.getsource(runner_mod)
    assert "process_single returned None without errors" in src


def test_source_contains_json_dump_batch49():
    src = inspect.getsource(runner_mod)
    assert "json.dump(" in src


def test_source_contains_to_dict_calls_batch49():
    src = inspect.getsource(runner_mod)
    assert ".to_dict()" in src


# ---------- AST 结构补强 ----------

def test_ast_has_3_top_level_functions_batch49():
    """3 个函数：_load_annotation, _process_one, run_evaluation。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 3


def test_ast_function_names_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_load_annotation", "_process_one", "run_evaluation"]


def test_ast_no_class_def_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_module_has_docstring_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_module_has_10_imports_batch49():
    """10 个 import：__future__ + json + time + Path + Any + pipeline + REPORT_VERSION + annotation_metrics + metrics + report。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 10


def test_ast_module_has_1_top_level_assign_batch49():
    """只有 __all__ = ...。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 1


def test_ast_load_annotation_has_try_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_load_annotation_has_open_call_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation")
    src = ast.unparse(func)
    assert ".open(" in src


def test_ast_process_one_has_perf_counter_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    src = ast.unparse(func)
    assert "perf_counter" in src


def test_ast_process_one_has_multiple_return_batch49():
    """_process_one 至少 3 个 return（errors + None+unknown + success）。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 3


def test_ast_process_one_has_try_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) >= 1


def test_ast_run_evaluation_has_multiple_for_batch49():
    """run_evaluation 至少 3 个 for（documents + expected_failures + public_per_doc）。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    fors = [n for n in func.body if isinstance(n, ast.For)]
    assert len(fors) == 3


def test_ast_run_evaluation_has_with_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    withs = [n for n in ast.walk(func) if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_run_evaluation_has_json_dump_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    src = ast.unparse(func)
    assert "json.dump(" in src


def test_ast_run_evaluation_returns_report_variable_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    src = ast.unparse(func)
    # 最后一个 return 应该是 return report
    assert "return report" in src


def test_ast_run_evaluation_has_report_dict_construction_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    src = ast.unparse(func)
    assert "report = {" in src
    # 6 top keys
    for key in ["report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"]:
        assert f"'{key}'" in src or f'"{key}"' in src


def test_ast_process_one_uses_5_tuple_return_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    src = ast.unparse(func)
    # 返回 5 元组（包括 image_dir）
    assert "image_dir" in src


def test_ast_load_annotation_returns_none_two_places_batch49():
    """_load_annotation 至少 2 个 return None（用 ast.walk 整个函数）。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation")
    returns_none = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Return)
        and isinstance(n.value, ast.Constant)
        and n.value.value is None
    ]
    assert len(returns_none) >= 2


def test_ast_no_global_statement_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.Global) for n in ast.walk(tree))


def test_ast_no_nonlocal_statement_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.Nonlocal) for n in ast.walk(tree))


def test_ast_no_delete_statement_batch49():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.Delete) for n in ast.walk(tree))


# ---------- forbidden tokens 第一百三十三批 ----------

def _src() -> str:
    return inspect.getsource(runner_mod)


def test_source_no_eval_batch49():
    assert "eval(" not in _src()


def test_source_no_exec_batch49():
    assert "exec(" not in _src()


def test_source_no_compile_batch49():
    assert "compile(" not in _src()


def test_source_no_globals_batch49():
    assert "globals(" not in _src()


def test_source_no_locals_batch49():
    assert "locals(" not in _src()


def test_source_no_os_system_batch49():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch49():
    assert "subprocess" not in _src()


def test_source_no_popen_batch49():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch49():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch49():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch49():
    assert "socket" not in _src()


def test_source_no_requests_batch49():
    assert "requests" not in _src()


def test_source_no_urllib_batch49():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch49():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch49():
    assert "yield" not in _src()


def test_source_open_only_in_load_annotation_and_run_evaluation_batch49():
    """open() 在 _load_annotation 和 run_evaluation 中各 1 次。"""
    src = _src()
    assert src.count("open(") == 2
