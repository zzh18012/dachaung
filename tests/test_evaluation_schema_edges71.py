"""evaluation/schema.py 第一百零二轮 edges 测试（Round 715）。

补强 edges70 未触及的角度（第八十批）。

新角度：
- evaluation-report per_doc 变体（source_type txt 拒 / doc_id 空串拒 / wall_time total null 可）
- summary silent_drop_total 1.5 拒（integer|null）
- expected_failure_result doc_id 空串可（无 minLength，与 per_doc 对比）
- provenance evaluator_version 空串拒
- annotation 变体（chunk_boundary_anchors 空数组可 / heading_order level bool 拒 / date 无 format 约束任意非空串可 /
  boundary_anchor reason 非字符串拒 / 仅必填键+全空数组可）
- validate() 直跑 document.schema.json（合法全量 doc 过 / 缺键抛 EvalSchemaError）
- 四 schema type 全 object / $id 互异 / EvalSchemaError 继承 Exception
- 源码补强（jsonschema 双 import / SCHEMAS_DIR 表达式 / errors 注解 / flat 注解 / head = errors[0] / p = Path(path)）
- AST 补强（validate 2 个 JoinedStr / EvalSchemaError bases [Exception] / __init__ 参数与默认 / _schema_path 无 docstring 其余有）
- forbidden tokens 第一百八十五批
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    load_schema,
    validate,
)


def _valid_document() -> dict[str, Any]:
    return {
        "schema_version": "0.1.0", "document_id": "doc-1",
        "source_path": "samples/a.pdf", "source_type": "pdf",
        "source_hash": "a" * 64, "parser_name": "fallback", "parser_version": "1.0",
        "elements": [{"element_id": "e1", "type": "paragraph", "parent_id": None,
                      "content": "hello", "resource_path": None,
                      "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
                      "confidence": 1.0, "metadata": {}}],
        "chunks": [{"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"],
                    "metadata": {}}],
        "relations": [], "warnings": [], "errors": [], "metadata": {},
    }


def _min_report() -> dict:
    return {
        "report_version": "1.1",
        "provenance": {
            "git_commit": None, "git_dirty": False,
            "evaluator_version": "1.1", "report_version": "1.1",
            "parser_name": "fallback", "parser_version": None,
            "dependencies": {}, "max_chars": 800,
            "run_timestamp_iso": "2026-01-01T00:00:00+08:00",
        },
        "devset": {"status": "incomplete", "file_count": 0,
                   "content_group_count": 0, "pdf_count": 0, "docx_count": 0,
                   "categories_covered": []},
        "summary": {},
        "per_doc": [],
    }


def _pd(doc_id="d1", source_type="pdf") -> dict:
    return {
        "doc_id": doc_id, "source_type": source_type,
        "metrics": {},
        "wall_time_seconds": {"total": 0.1, "parse": None, "chunk": None},
    }


# ---------- evaluation-report per_doc 变体 ----------

def test_report_per_doc_txt_rejected_batch53():
    rep = _min_report()
    rep["per_doc"] = [_pd(source_type="txt")]
    with pytest.raises(EvalSchemaError):
        validate(rep, "evaluation-report.schema.json")


def test_report_per_doc_empty_doc_id_rejected_batch53():
    rep = _min_report()
    rep["per_doc"] = [_pd(doc_id="")]
    with pytest.raises(EvalSchemaError):
        validate(rep, "evaluation-report.schema.json")


def test_report_per_doc_wall_time_total_null_ok_batch53():
    rep = _min_report()
    rep["per_doc"] = [_pd()]
    rep["per_doc"][0]["wall_time_seconds"] = {
        "total": None, "parse": None, "chunk": None,
        "parse_reason": "not_instrumented", "chunk_reason": "not_instrumented",
    }
    validate(rep, "evaluation-report.schema.json")  # 不抛即过


def test_report_summary_silent_drop_float_rejected_batch53():
    rep = _min_report()
    rep["summary"] = {"silent_drop_total": 1.5}
    with pytest.raises(EvalSchemaError):
        validate(rep, "evaluation-report.schema.json")


def test_report_ef_empty_doc_id_ok_batch53():
    """ef 的 doc_id 无 minLength（与 per_doc 对比，记录现状）。"""
    rep = _min_report()
    rep["expected_failures"] = [
        {"doc_id": "", "expected_error_code": "x",
         "actual_error_code": None, "matches": False}]
    validate(rep, "evaluation-report.schema.json")


def test_report_provenance_evaluator_version_empty_rejected_batch53():
    rep = _min_report()
    rep["provenance"]["evaluator_version"] = ""
    with pytest.raises(EvalSchemaError):
        validate(rep, "evaluation-report.schema.json")


# ---------- annotation 变体 ----------

def _ann(**over) -> dict:
    base = {"annotation_version": "1.0", "doc_id": "d1"}
    base.update(over)
    return base


def test_annotation_empty_anchors_ok_batch53():
    validate(_ann(chunk_boundary_anchors=[]), "annotation.schema.json")


def test_annotation_heading_level_bool_rejected_batch53():
    with pytest.raises(EvalSchemaError):
        validate(_ann(heading_order=[{"level": True, "text": "x"}]),
                 "annotation.schema.json")


def test_annotation_date_no_format_constraint_batch53():
    """date 只是 minLength 1 的字符串，无 format 校验（记录现状）。"""
    validate(_ann(date="2024-13-99"), "annotation.schema.json")


def test_annotation_anchor_reason_non_string_rejected_batch53():
    with pytest.raises(EvalSchemaError):
        validate(_ann(chunk_boundary_anchors=[
            {"marker": "m", "position": "after", "reason": 5}]),
            "annotation.schema.json")


def test_annotation_all_empty_arrays_ok_batch53():
    a = _ann(annotator="", date="d", figure_caption_pairs=[],
             heading_order=[], chunk_boundary_anchors=[])
    validate(a, "annotation.schema.json")


# ---------- validate() 直跑 document.schema.json ----------

def test_validate_document_schema_valid_passes_batch53():
    validate(_valid_document(), "document.schema.json")


def test_validate_document_schema_missing_key_batch53():
    doc = _valid_document()
    del doc["source_hash"]
    with pytest.raises(EvalSchemaError) as ei:
        validate(doc, "document.schema.json")
    assert any("source_hash" in e["message"] for e in ei.value.errors)


# ---------- 跨 schema 事实 ----------

def test_all_schemas_type_object_batch53():
    for name in ("manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json", "document.schema.json"):
        assert load_schema(name)["type"] == "object"


def test_all_schema_ids_distinct_batch53():
    ids = [load_schema(n)["$id"] for n in
           ("manifest.schema.json", "annotation.schema.json",
            "evaluation-report.schema.json", "document.schema.json")]
    assert len(set(ids)) == 4


def test_eval_schema_error_is_exception_batch53():
    assert issubclass(EvalSchemaError, Exception)
    assert EvalSchemaError.__mro__[1] is Exception


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(schema_mod)


def test_source_jsonschema_imports_batch53():
    src = _src()
    assert "from jsonschema import Draft202012Validator" in src
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_source_schemas_dir_expr_batch53():
    assert 'SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"' in _src()


def test_source_annotations_batch53():
    src = _src()
    assert "errors: list[dict[str, Any]] | None = None" in src
    assert "flat: list[dict[str, Any]] = []" in src


def test_source_head_and_path_batch53():
    src = _src()
    assert "head = errors[0]" in src
    assert "p = Path(path)" in src


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(schema_mod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def test_ast_validate_one_joinedstr_batch53():
    f = _func("validate")
    js = [n for n in ast.walk(f) if isinstance(n, ast.JoinedStr)]
    # raise 消息的两段 f-string 隐式拼接成一个 JoinedStr
    assert len(js) == 1


def test_ast_error_class_base_exception_batch53():
    cls = next(n for n in _tree().body if isinstance(n, ast.ClassDef))
    assert cls.name == "EvalSchemaError"
    assert [ast.unparse(b) for b in cls.bases] == ["Exception"]


def test_ast_init_params_batch53():
    init = next(n for n in _tree().body if isinstance(n, ast.ClassDef))
    f = next(n for n in init.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    assert [a.arg for a in f.args.args] == ["self", "message", "errors"]
    assert [ast.unparse(d) for d in f.args.defaults] == ["None"]


def test_ast_docstring_presence_batch53():
    tree = _tree()
    has_doc = {}
    for n in tree.body:
        if isinstance(n, ast.FunctionDef):
            has_doc[n.name] = bool(n.body and isinstance(n.body[0], ast.Expr)
                                   and isinstance(n.body[0].value, ast.Constant))
    assert has_doc == {"load_schema": True, "validate": True,
                       "_schema_path": False, "validate_file": True}


# ---------- forbidden tokens 第一百八十五批 ----------

def test_source_no_eval_batch53():
    assert "eval(" not in _src()


def test_source_no_exec_batch53():
    assert "exec(" not in _src()


def test_source_no_compile_batch53():
    assert "compile(" not in _src()


def test_source_no_globals_batch53():
    assert "globals(" not in _src()


def test_source_no_locals_batch53():
    assert "locals(" not in _src()


def test_source_no_os_system_batch53():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch53():
    assert "subprocess" not in _src()


def test_source_no_popen_batch53():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch53():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch53():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch53():
    assert "socket" not in _src()


def test_source_no_requests_batch53():
    assert "requests" not in _src()


def test_source_no_urllib_batch53():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch53():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch53():
    assert "yield" not in _src()


def test_source_no_async_await_batch53():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch53():
    assert _src().count("open(") == 2
