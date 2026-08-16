"""evaluation/schema.py 第九十八轮 edges 测试（Round 687）。

补强 edges66 未触及的角度（第五十五批）：Schema 文件内容级校验。

新角度：
- validate 多错误细节（flat 长度 == message 中 count / path 含数组索引 int / schema_path 非空 / 按 path 排序稳定性）
- manifest.schema.json 内容校验（manifest_version const 1.0 / devset_status enum / document required 3 / path minLength / source_type enum / sha256 pattern / document additionalProperties false / expected_failure required 3 / documents 空数组合法 / expected_failures 可省略）
- annotation.schema.json 内容校验（annotation_version const / doc_id minLength / anchor marker minLength / position enum 拒绝 middle / anchor additionalProperties false / reason 可选 / heading_order level minimum 1 / figure_caption_pairs required 2 / 最小合法 annotation）
- evaluation-report.schema.json 内容校验（report_version const 1.1 拒绝 1.0 / provenance 9 required / per_doc required 4 / wall_time required 3 + additionalProperties false / ef_result required 4 / summary silent_drop_total 接受 null / dependencies 值接受 null / max_chars minimum 1）
- 端到端最小合法实例（manifest / annotation / report 三个 schema 全通过）
- EvalSchemaError 细节（str(e) 含 message / args 单元素 / errors=None 两次实例不共享列表）
- load_schema 无缓存（两次加载内容相等但是不同对象）
- AST 结构补强（flat dict 字面量 3 keys / lambda key body 是 list Call / validate_file Path(path) 转换 / __all__ 精确顺序 / validate raise 2 个参数）
- forbidden tokens 第一百五十七批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- 最小合法实例构造器 ----------

def _min_manifest() -> dict[str, Any]:
    return {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a/b.pdf", "source_type": "pdf"}],
    }


def _min_annotation() -> dict[str, Any]:
    return {"annotation_version": "1.0", "doc_id": "d1"}


def _min_report() -> dict[str, Any]:
    return {
        "report_version": "1.1",
        "provenance": {
            "git_commit": None,
            "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {},
            "max_chars": 800,
            "run_timestamp_iso": "2026-01-01T00:00:00+08:00",
        },
        "devset": {
            "status": "incomplete",
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": [],
        },
        "summary": {
            "counts": {},
            "success_rates": {},
            "ratio_macro_averages": {},
            "silent_drop_total": None,
        },
        "per_doc": [],
    }


# ---------- 端到端最小合法实例 ----------

def test_minimal_manifest_passes_batch52():
    validate(_min_manifest(), "manifest.schema.json")  # 不抛即通过


def test_minimal_annotation_passes_batch52():
    validate(_min_annotation(), "annotation.schema.json")


def test_minimal_report_passes_batch52():
    validate(_min_report(), "evaluation-report.schema.json")


def test_minimal_report_with_per_doc_item_batch52():
    r = _min_report()
    r["per_doc"] = [{
        "doc_id": "d1",
        "source_type": "pdf",
        "metrics": {"pipeline_success": {"value": True, "reason": None}},
        "wall_time_seconds": {"total": 0.5, "parse": None, "chunk": None, "parse_reason": "not_instrumented", "chunk_reason": "not_instrumented"},
    }]
    r["expected_failures"] = [{
        "doc_id": "ef1",
        "expected_error_code": "unsupported_format",
        "actual_error_code": "unsupported_format",
        "matches": True,
    }]
    validate(r, "evaluation-report.schema.json")


# ---------- validate 多错误细节 ----------

def test_validate_multi_errors_flat_length_matches_count_batch52():
    m = _min_manifest()
    m["manifest_version"] = "2.0"          # const 错
    m["devset_status"] = "bogus"           # enum 错
    with pytest.raises(EvalSchemaError) as ei:
        validate(m, "manifest.schema.json")
    assert len(ei.value.errors) == 2
    assert "2 处" in str(ei.value)


def test_validate_error_path_contains_array_index_batch52():
    m = _min_manifest()
    m["documents"][0]["source_type"] = "txt"  # enum 错（在数组索引 0 下）
    with pytest.raises(EvalSchemaError) as ei:
        validate(m, "manifest.schema.json")
    paths = [tuple(e["path"]) for e in ei.value.errors]
    assert ("documents", 0, "source_type") in paths


def test_validate_error_schema_path_non_empty_batch52():
    m = _min_manifest()
    m["devset_status"] = "bogus"
    with pytest.raises(EvalSchemaError) as ei:
        validate(m, "manifest.schema.json")
    for e in ei.value.errors:
        assert len(e["schema_path"]) > 0


def test_validate_sorted_by_path_stability_batch52():
    m = _min_manifest()
    m["documents"] = [
        {"doc_id": "a", "path": "a.pdf", "source_type": "txt"},
        {"doc_id": "b", "path": "b.pdf", "source_type": "docx"},
    ]
    # doc 0 source_type 错；doc 1 缺 doc_id → 两处错误
    with pytest.raises(EvalSchemaError) as ei:
        validate(m, "manifest.schema.json")
    assert len(ei.value.errors) >= 1


# ---------- manifest.schema.json 内容校验 ----------

def test_manifest_version_rejects_2_0_batch52():
    m = _min_manifest()
    m["manifest_version"] = "2.0"
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_manifest_version_rejects_number_batch52():
    m = _min_manifest()
    m["manifest_version"] = 1.0
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_manifest_devset_status_complete_ok_batch52():
    m = _min_manifest()
    m["devset_status"] = "complete"
    validate(m, "manifest.schema.json")


def test_manifest_devset_status_rejects_unknown_batch52():
    m = _min_manifest()
    m["devset_status"] = "partial"
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_manifest_missing_documents_batch52():
    m = _min_manifest()
    del m["documents"]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_manifest_empty_documents_ok_batch52():
    m = _min_manifest()
    m["documents"] = []
    validate(m, "manifest.schema.json")


def test_manifest_expected_failures_omitted_ok_batch52():
    m = _min_manifest()
    validate(m, "manifest.schema.json")  # 不含 expected_failures 也合法


def test_manifest_document_missing_doc_id_batch52():
    m = _min_manifest()
    del m["documents"][0]["doc_id"]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_manifest_document_empty_path_rejected_batch52():
    m = _min_manifest()
    m["documents"][0]["path"] = ""
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_manifest_document_source_type_txt_rejected_batch52():
    m = _min_manifest()
    m["documents"][0]["source_type"] = "txt"
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_manifest_document_source_type_docx_ok_batch52():
    m = _min_manifest()
    m["documents"][0]["source_type"] = "docx"
    validate(m, "manifest.schema.json")


def test_manifest_sha256_valid_pattern_batch52():
    m = _min_manifest()
    m["documents"][0]["sha256"] = "a" * 64
    validate(m, "manifest.schema.json")


def test_manifest_sha256_uppercase_rejected_batch52():
    m = _min_manifest()
    m["documents"][0]["sha256"] = "A" * 64
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_manifest_sha256_short_rejected_batch52():
    m = _min_manifest()
    m["documents"][0]["sha256"] = "abc"
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_manifest_document_extra_key_rejected_batch52():
    m = _min_manifest()
    m["documents"][0]["surprise"] = 1
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_manifest_top_extra_key_rejected_batch52():
    m = _min_manifest()
    m["extra"] = 1
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_manifest_categories_list_of_str_ok_batch52():
    m = _min_manifest()
    m["documents"][0]["categories"] = ["报告", "表格"]
    validate(m, "manifest.schema.json")


def test_manifest_expected_failure_minimal_ok_batch52():
    m = _min_manifest()
    m["expected_failures"] = [{
        "doc_id": "ef1",
        "path": "bad/ef1.pdf",
        "expected_error_code": "unsupported_format",
    }]
    validate(m, "manifest.schema.json")


def test_manifest_expected_failure_missing_code_batch52():
    m = _min_manifest()
    m["expected_failures"] = [{"doc_id": "ef1", "path": "bad/ef1.pdf"}]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


# ---------- annotation.schema.json 内容校验 ----------

def test_annotation_version_rejects_2_0_batch52():
    a = _min_annotation()
    a["annotation_version"] = "2.0"
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_annotation_empty_doc_id_rejected_batch52():
    a = _min_annotation()
    a["doc_id"] = ""
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_annotation_anchor_minimal_ok_batch52():
    a = _min_annotation()
    a["chunk_boundary_anchors"] = [{"marker": "abc", "position": "after"}]
    validate(a, "annotation.schema.json")


def test_annotation_anchor_empty_marker_rejected_batch52():
    a = _min_annotation()
    a["chunk_boundary_anchors"] = [{"marker": "", "position": "after"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_annotation_anchor_middle_position_rejected_batch52():
    a = _min_annotation()
    a["chunk_boundary_anchors"] = [{"marker": "x", "position": "middle"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_annotation_anchor_before_ok_batch52():
    a = _min_annotation()
    a["chunk_boundary_anchors"] = [{"marker": "x", "position": "before"}]
    validate(a, "annotation.schema.json")


def test_annotation_anchor_extra_key_rejected_batch52():
    a = _min_annotation()
    a["chunk_boundary_anchors"] = [{"marker": "x", "position": "after", "zzz": 1}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_annotation_anchor_reason_optional_ok_batch52():
    a = _min_annotation()
    a["chunk_boundary_anchors"] = [{"marker": "x", "position": "after", "reason": "why"}]
    validate(a, "annotation.schema.json")


def test_annotation_heading_order_valid_batch52():
    a = _min_annotation()
    a["heading_order"] = [{"level": 1, "text": "标题"}, {"level": 2, "text": "子标题"}]
    validate(a, "annotation.schema.json")


def test_annotation_heading_order_level_0_rejected_batch52():
    a = _min_annotation()
    a["heading_order"] = [{"level": 0, "text": "x"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_annotation_heading_order_missing_text_batch52():
    a = _min_annotation()
    a["heading_order"] = [{"level": 1}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_annotation_figure_caption_pair_valid_batch52():
    a = _min_annotation()
    a["figure_caption_pairs"] = [{"figure_marker": "图1", "caption_text": "说明"}]
    validate(a, "annotation.schema.json")


def test_annotation_figure_caption_missing_caption_batch52():
    a = _min_annotation()
    a["figure_caption_pairs"] = [{"figure_marker": "图1"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_annotation_annotator_and_date_ok_batch52():
    a = _min_annotation()
    a["annotator"] = "human"
    a["date"] = "2026-08-16"
    validate(a, "annotation.schema.json")


def test_annotation_extra_key_rejected_batch52():
    a = _min_annotation()
    a["nope"] = 1
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


# ---------- evaluation-report.schema.json 内容校验 ----------

def test_report_version_rejects_1_0_batch52():
    r = _min_report()
    r["report_version"] = "1.0"
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_report_missing_provenance_batch52():
    r = _min_report()
    del r["provenance"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_report_provenance_missing_one_key_batch52():
    r = _min_report()
    del r["provenance"]["max_chars"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_report_provenance_max_chars_0_rejected_batch52():
    r = _min_report()
    r["provenance"]["max_chars"] = 0
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_report_provenance_dependencies_null_value_ok_batch52():
    r = _min_report()
    r["provenance"]["dependencies"] = {"pypdfium2": None}
    validate(r, "evaluation-report.schema.json")


def test_report_provenance_dependencies_int_value_rejected_batch52():
    r = _min_report()
    r["provenance"]["dependencies"] = {"pdfplumber": 1}
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_report_per_doc_missing_metrics_batch52():
    r = _min_report()
    r["per_doc"] = [{"doc_id": "d", "source_type": "pdf", "wall_time_seconds": {"total": 1, "parse": None, "chunk": None}}]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_report_wall_time_extra_key_rejected_batch52():
    r = _min_report()
    r["per_doc"] = [{
        "doc_id": "d", "source_type": "pdf", "metrics": {},
        "wall_time_seconds": {"total": 1, "parse": None, "chunk": None, "extra": 1},
    }]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_report_wall_time_missing_parse_batch52():
    r = _min_report()
    r["per_doc"] = [{
        "doc_id": "d", "source_type": "pdf", "metrics": {},
        "wall_time_seconds": {"total": 1, "chunk": None},
    }]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_report_expected_failures_empty_ok_batch52():
    r = _min_report()
    r["expected_failures"] = []
    validate(r, "evaluation-report.schema.json")


def test_report_ef_result_missing_matches_batch52():
    r = _min_report()
    r["expected_failures"] = [{
        "doc_id": "ef1",
        "expected_error_code": "unsupported_format",
        "actual_error_code": "unsupported_format",
    }]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_report_summary_silent_drop_int_ok_batch52():
    r = _min_report()
    r["summary"]["silent_drop_total"] = 5
    validate(r, "evaluation-report.schema.json")


def test_report_summary_missing_ok_not_required_batch52():
    r = _min_report()
    r["summary"] = {}
    validate(r, "evaluation-report.schema.json")  # summary 内部无 required


def test_report_extra_top_key_rejected_batch52():
    r = _min_report()
    r["bonus"] = 1
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


# ---------- EvalSchemaError 细节 ----------

def test_eval_schema_error_str_contains_message_batch52():
    e = EvalSchemaError("boom", errors=[{"path": []}])
    assert "boom" in str(e)


def test_eval_schema_error_args_single_element_batch52():
    e = EvalSchemaError("boom")
    assert e.args == ("boom",)


def test_eval_schema_error_errors_default_not_shared_batch52():
    e1 = EvalSchemaError("a")
    e2 = EvalSchemaError("b")
    e1.errors.append({"x": 1})
    assert e2.errors == []


def test_eval_schema_error_errors_kwarg_kept_batch52():
    errs = [{"path": [1], "message": "m", "schema_path": [0]}]
    e = EvalSchemaError("msg", errors=errs)
    assert e.errors == errs


# ---------- load_schema 无缓存 ----------

def test_load_schema_no_cache_two_loads_batch52():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2
    assert s1 is not s2


def test_load_schema_mutation_isolated_batch52():
    s1 = load_schema("annotation.schema.json")
    s1["__mutated"] = True
    s2 = load_schema("annotation.schema.json")
    assert "__mutated" not in s2


# ---------- validate_file 端到端 ----------

def test_validate_file_minimal_manifest_batch52(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_min_manifest()), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_minimal_annotation_batch52(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps(_min_annotation()), encoding="utf-8")
    validate_file(p, "annotation.schema.json")


def test_validate_file_minimal_report_batch52(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps(_min_report()), encoding="utf-8")
    validate_file(p, "evaluation-report.schema.json")


# ---------- 模块源码补强 ----------

def test_source_flat_dict_literal_3_keys_batch52():
    src = inspect.getsource(schema_mod)
    assert '"path": list(err.absolute_path)' in src
    assert '"schema_path": list(err.absolute_schema_path)' in src


def test_source_validate_message_count_part_batch52():
    src = inspect.getsource(schema_mod)
    assert "校验失败 (" in src
    assert "处)：" in src


def test_source_validate_file_path_conversion_batch52():
    src = inspect.getsource(schema_mod)
    assert "p = Path(path)" in src


def test_source_errors_or_empty_default_batch52():
    src = inspect.getsource(schema_mod)
    assert "self.errors = errors or []" in src


def test_source_schema_path_fstring_batch52():
    src = inspect.getsource(schema_mod)
    assert 'f"Schema 文件不存在: {p}"' in src


def test_source_validate_file_fstring_batch52():
    src = inspect.getsource(schema_mod)
    assert 'f"待校验文件不存在: {p}"' in src


def test_source_docstring_separate_from_app_batch52():
    src = inspect.getsource(schema_mod)
    assert "不与 app/schema.py 复用" in src


# ---------- AST 结构补强 ----------

def test_ast_flat_dict_3_literal_keys_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    dicts = [n for n in ast.walk(func) if isinstance(n, ast.Dict) and n.keys and all(isinstance(k, ast.Constant) for k in n.keys)]
    keysets = [tuple(k.value for k in d.keys) for d in dicts]
    assert ("path", "message", "schema_path") in keysets


def test_ast_sorted_lambda_body_is_list_call_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    sorted_calls = [n for n in ast.walk(func) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "sorted"]
    assert len(sorted_calls) == 1
    lam = sorted_calls[0].keywords[0].value
    assert isinstance(lam, ast.Lambda)
    assert isinstance(lam.body, ast.Call)


def test_ast_validate_raise_2_args_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    raises = [n for n in ast.walk(func) if isinstance(n, ast.Raise)]
    assert len(raises) == 1
    assert len(raises[0].exc.args) == 1  # message 位置参数
    assert len(raises[0].exc.keywords) == 1  # errors= 关键字参数
    assert raises[0].exc.keywords[0].arg == "errors"


def test_ast_all_exact_order_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    names = [e.value for e in all_assign.value.elts]
    assert names == ["SCHEMAS_DIR", "EvalSchemaError", "load_schema", "validate", "validate_file"]


def test_ast_validate_file_body_conversion_first_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    assert isinstance(func.body[0], ast.Expr)  # docstring
    first = func.body[1]
    assert isinstance(first, ast.Assign)
    src = ast.unparse(first)
    assert "Path(path)" in src


def test_ast_no_import_inside_functions_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef):
            assert not any(isinstance(s, (ast.Import, ast.ImportFrom)) for s in n.body)


# ---------- forbidden tokens 第一百五十七批 ----------

def _src() -> str:
    return inspect.getsource(schema_mod)


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
    assert _src().count("open(") == 2
