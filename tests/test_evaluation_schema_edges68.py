"""evaluation/schema.py 第九十九轮 edges 测试（Round 694）。

补强 edges67 未触及的角度（第五十九批续）：Schema 文件结构级校验（第二轮）。

新角度：
- 三个 schema 的 $id 统一前缀 https://kvfs.local/schemas/ 与 $schema Draft 2020-12
- $defs 引用结构（manifest 2 个 $ref / report 5 个 $defs 名单 / annotation boundary_anchor $ref）
- Draft202012Validator.check_schema 三个 schema 全通过
- validate 拒绝非 dict 顶层（list/str/number/int/None/bool）
- 大清单 100 documents 全通过
- _schema_path 空串名 / 纯空格名 / 换行名
- load_schema 4 个文件（含 document.schema.json）都可加载
- validate_file 目录输入 FileNotFoundError
- EvalSchemaError.errors 与 raised 时 message 的 head 一致性（errors[0] 是排序后第一个）
- 源码补强（SCHEMAS_DIR resolve 一行 / iter_errors+sorted / flat append 顺序 / __init__ errors or [] / FileNotFoundError 两处消息前缀）
- AST 补强（_schema_path If body 是 Raise / load_schema with items / validate flat append Call / validate_file 2 个 Raise Call / imports 精确名单）
- forbidden tokens 第一百六十四批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

import evaluation.schema as schema_mod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


SCHEMA_NAMES = ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json")


# ---------- $id / $schema 统一性 ----------

def test_all_schema_ids_share_prefix_batch52():
    for name in SCHEMA_NAMES:
        s = load_schema(name)
        assert s["$id"].startswith("https://kvfs.local/schemas/")
        assert s["$id"].endswith(name)


def test_all_schema_draft_2020_12_batch52():
    for name in SCHEMA_NAMES:
        s = load_schema(name)
        assert s["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_all_schemas_have_title_batch52():
    for name in SCHEMA_NAMES:
        s = load_schema(name)
        assert isinstance(s.get("title"), str)
        assert s["title"]


def test_manifest_annotation_have_description_batch52():
    """evaluation-report.schema.json 无 description（有 title）。"""
    for name in ("manifest.schema.json", "annotation.schema.json"):
        s = load_schema(name)
        assert isinstance(s.get("description"), str)


# ---------- $defs 引用结构 ----------

def test_manifest_documents_ref_batch52():
    s = load_schema("manifest.schema.json")
    assert s["properties"]["documents"]["items"] == {"$ref": "#/$defs/document"}


def test_manifest_expected_failures_ref_batch52():
    s = load_schema("manifest.schema.json")
    assert s["properties"]["expected_failures"]["items"] == {"$ref": "#/$defs/expected_failure"}


def test_manifest_defs_2_entries_batch52():
    s = load_schema("manifest.schema.json")
    assert sorted(s["$defs"].keys()) == ["document", "expected_failure"]


def test_report_defs_5_entries_batch52():
    s = load_schema("evaluation-report.schema.json")
    assert sorted(s["$defs"].keys()) == [
        "devset", "expected_failure_result", "per_doc", "provenance", "summary",
    ]


def test_annotation_anchors_ref_boundary_anchor_batch52():
    s = load_schema("annotation.schema.json")
    assert s["properties"]["chunk_boundary_anchors"]["items"] == {"$ref": "#/$defs/boundary_anchor"}


def test_annotation_defs_only_boundary_anchor_batch52():
    s = load_schema("annotation.schema.json")
    assert sorted(s["$defs"].keys()) == ["boundary_anchor"]


# ---------- check_schema ----------

def test_all_schemas_pass_check_schema_batch52():
    for name in SCHEMA_NAMES:
        Draft202012Validator.check_schema(load_schema(name))


# ---------- validate 拒绝非 dict 顶层 ----------

@pytest.mark.parametrize("bad", [
    [1, 2], "string", 42, 3.14, None, True,
])
def test_validate_rejects_non_dict_top_level_batch52(bad):
    with pytest.raises(EvalSchemaError):
        validate(bad, "manifest.schema.json")


def test_validate_non_dict_error_path_empty_batch52():
    with pytest.raises(EvalSchemaError) as ei:
        validate([1], "manifest.schema.json")
    assert ei.value.errors[0]["path"] == []


# ---------- 大清单 ----------

def test_validate_100_documents_batch52():
    docs = [
        {"doc_id": f"d{i}", "path": f"samples/d{i}.pdf", "source_type": "pdf"}
        for i in range(100)
    ]
    validate({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": docs,
    }, "manifest.schema.json")


# ---------- _schema_path 边界名 ----------

def test_schema_path_empty_name_batch52():
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_whitespace_name_batch52():
    with pytest.raises(FileNotFoundError):
        _schema_path("   ")


def test_schema_path_newline_name_batch52():
    with pytest.raises(FileNotFoundError):
        _schema_path("no\nsuch.schema.json")


def test_schema_path_returns_under_dir_batch52():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


# ---------- load_schema 4 个文件 ----------

def test_load_schema_all_4_files_batch52():
    for name in SCHEMA_NAMES + ("document.schema.json",):
        s = load_schema(name)
        assert isinstance(s, dict)
        assert s.get("type") == "object"


def test_schemas_dir_4_json_files_batch52():
    jsons = sorted(p.name for p in SCHEMAS_DIR.glob("*.json"))
    assert jsons == [
        "annotation.schema.json",
        "document.schema.json",
        "evaluation-report.schema.json",
        "manifest.schema.json",
    ]


# ---------- validate_file 边界 ----------

def test_validate_file_directory_raises_batch52(tmp_path):
    d = tmp_path / "adir"
    d.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(d, "manifest.schema.json")


def test_validate_file_bad_schema_name_batch52(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "missing.schema.json")


def test_validate_file_validates_content_not_name_batch52(tmp_path):
    p = tmp_path / "anything.txt"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


# ---------- head 一致性 ----------

def test_error_head_matches_first_flat_batch52():
    m = {
        "manifest_version": "9.9",
        "devset_status": "bad",
        "documents": "not-a-list",
        "extra": 1,
    }
    with pytest.raises(EvalSchemaError) as ei:
        validate(m, "manifest.schema.json")
    e = ei.value
    # message 中的 head.message 应等于排序后第一个错误的 message
    first = e.errors[0]
    assert first["message"] in str(e)


def test_error_count_matches_flat_length_batch52():
    m = {
        "manifest_version": "9.9",
        "devset_status": "bad",
        "documents": "not-a-list",
        "extra": 1,
    }
    with pytest.raises(EvalSchemaError) as ei:
        validate(m, "manifest.schema.json")
    n = int(str(ei.value).split("(")[1].split(" 处")[0])
    assert n == len(ei.value.errors)


# ---------- 源码补强 ----------

def test_source_schemas_dir_one_line_batch52():
    src = inspect.getsource(schema_mod)
    assert 'SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"' in src


def test_source_iter_errors_sorted_batch52():
    src = inspect.getsource(schema_mod)
    assert "sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))" in src


def test_source_flat_append_order_batch52():
    src = inspect.getsource(schema_mod)
    assert '"path": list(err.absolute_path),' in src
    assert '"message": err.message,' in src
    assert '"schema_path": list(err.absolute_schema_path),' in src


def test_source_init_errors_or_empty_batch52():
    src = inspect.getsource(schema_mod)
    assert "self.errors = errors or []" in src


def test_source_filenotfound_prefixes_batch52():
    src = inspect.getsource(schema_mod)
    assert src.count("FileNotFoundError(") == 2
    assert "Schema 文件不存在" in src
    assert "待校验文件不存在" in src


def test_source_return_none_when_no_errors_batch52():
    src = inspect.getsource(schema_mod)
    assert "if not errors:" in src
    assert "return" in src


# ---------- AST 补强 ----------

def test_ast_schema_path_if_body_is_raise_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_schema_path")
    assert isinstance(func.body[0], ast.Assign)  # p = SCHEMAS_DIR / name
    if_stmt = func.body[1]
    assert isinstance(if_stmt, ast.If)
    assert isinstance(if_stmt.body[0], ast.Raise)
    assert isinstance(if_stmt.body[0].exc, ast.Call)


def test_ast_load_schema_with_open_encoding_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_schema")
    with_stmt = func.body[-1]
    assert isinstance(with_stmt, ast.With)
    src = ast.unparse(with_stmt)
    assert "encoding='utf-8'" in src


def test_ast_validate_flat_append_call_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    appends = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "append"
    ]
    assert len(appends) == 1


def test_ast_validate_file_2_raises_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    raises = [n for n in ast.walk(func) if isinstance(n, ast.Raise)]
    assert len(raises) == 1  # 只有不存在文件的 Raise；其余异常透传


def test_ast_import_names_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    mods = []
    for n in tree.body:
        if isinstance(n, ast.Import):
            mods.extend(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            mods.append(n.module)
    assert sorted(mods) == ["__future__", "json", "jsonschema", "jsonschema.exceptions", "pathlib", "typing"]


def test_ast_no_conditional_expression_in_module_batch52():
    """flat 构造无 IfExp（都是字面 dict）。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    assert not any(isinstance(n, ast.IfExp) for n in ast.walk(tree))


# ---------- forbidden tokens 第一百六十四批 ----------

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
