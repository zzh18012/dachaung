"""evaluation/schema.py 第一百零一轮 edges 测试（Round 708）。

补强 edges69 未触及的角度（第七十三批）。

新角度：
- validate 多错误负载（errors 按 absolute_path 排序 / devset_status 先于 documents / 每项恰 3 键 / 消息含计数）
- 根类型失败（list 实例 → path [] 空列表 / not of type 'object'）
- EvalSchemaError 默认与自定义（errors 默认 [] / args / str）
- load_schema 每次新 dict；四 schema 全部可加载 + $id 前缀；SCHEMAS_DIR 事实
- validate_file str 路径 / 相对路径 / 坏 JSON → JSONDecodeError / 不存在 → FileNotFoundError
- 跨 schema 结构锁（manifest required 3 + documents 无 minItems / annotation required 2 + props 恰 7 键 /
  evaluation-report required 5（expected_failures 不在）/ document required 13 键 / 根 additionalProperties）
- 源码补强（Draft202012Validator / 排序 lambda / 两处 FileNotFoundError / 消息模板 / errors=flat）
- AST 补强（super().__init__ 1 / 模块 Assign 2 / With 2 / validate 单裸 Return / Raise 3 / __all__ 5 项）
- forbidden tokens 第一百七十八批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    load_schema,
    validate,
    validate_file,
)


def _valid_manifest() -> dict:
    return {"manifest_version": "1.0", "devset_status": "incomplete", "documents": []}


# ---------- 多错误负载 ----------

def test_multi_error_sorted_by_path_batch53():
    bad = {"manifest_version": "1.0", "devset_status": "bogus",
           "documents": [{"bad": 1}]}
    with pytest.raises(EvalSchemaError) as ei:
        validate(bad, "manifest.schema.json")
    e = ei.value
    assert len(e.errors) >= 2
    assert e.errors[0]["path"] == ["devset_status"]  # 'devset_' < 'documents'
    assert e.errors[0]["path"] < e.errors[-1]["path"]


def test_error_entry_exact_keys_batch53():
    bad = {"devset_status": "bogus", "documents": "not-a-list"}
    with pytest.raises(EvalSchemaError) as ei:
        validate(bad, "manifest.schema.json")
    for entry in ei.value.errors:
        assert set(entry.keys()) == {"path", "message", "schema_path"}


def test_error_message_contains_count_and_path_batch53():
    bad = {"manifest_version": "1.0", "devset_status": "bogus", "documents": []}
    with pytest.raises(EvalSchemaError) as ei:
        validate(bad, "manifest.schema.json")
    msg = str(ei.value)
    assert "Schema 'manifest.schema.json' 校验失败 (1 处)" in msg
    assert "path=['devset_status']" in msg


# ---------- 根类型失败 ----------

def test_root_type_failure_empty_path_batch53():
    with pytest.raises(EvalSchemaError) as ei:
        validate([1, 2, 3], "manifest.schema.json")
    assert ei.value.errors[0]["path"] == []
    assert "is not of type 'object'" in ei.value.errors[0]["message"]


# ---------- EvalSchemaError 本体 ----------

def test_error_default_empty_list_batch53():
    e = EvalSchemaError("m")
    assert e.errors == []
    assert e.args == ("m",)
    assert str(e) == "m"


def test_error_custom_errors_preserved_batch53():
    errs = [{"path": ["a"], "message": "x", "schema_path": ["b"]}]
    e = EvalSchemaError("m", errors=errs)
    assert e.errors is errs


def test_validate_returns_none_on_success_batch53():
    assert validate(_valid_manifest(), "manifest.schema.json") is None


# ---------- load_schema ----------

def test_load_schema_fresh_dict_each_call_batch53():
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    assert a == b
    assert a is not b


def test_all_four_schemas_load_batch53():
    for name in ("manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json", "document.schema.json"):
        s = load_schema(name)
        assert isinstance(s, dict)
        assert "$schema" in s
        assert s["$id"].startswith("https://kvfs.local/schemas/")
        assert s["$id"].endswith(name)


def test_schemas_dir_facts_batch53():
    assert SCHEMAS_DIR.is_dir()
    assert SCHEMAS_DIR.name == "schemas"
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schema_path_missing_file_message_batch53():
    with pytest.raises(FileNotFoundError) as ei:
        load_schema("no-such.schema.json")
    assert "no-such.schema.json" in str(ei.value)


# ---------- validate_file 路径形式 ----------

def test_validate_file_str_path_batch53(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest()), encoding="utf-8")
    assert validate_file(str(p), "manifest.schema.json") is None


def test_validate_file_relative_path_batch53(tmp_path, monkeypatch):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest()), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert validate_file("m.json", "manifest.schema.json") is None


def test_validate_file_bad_json_raises_decode_batch53(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{oops", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_missing_raises_filenotfound_batch53(tmp_path):
    with pytest.raises(FileNotFoundError) as ei:
        validate_file(tmp_path / "ghost.json", "manifest.schema.json")
    assert "待校验文件不存在" in str(ei.value)


# ---------- 跨 schema 结构锁 ----------

def test_manifest_required_and_no_minitems_batch53():
    s = load_schema("manifest.schema.json")
    assert s["required"] == ["manifest_version", "devset_status", "documents"]
    assert s["additionalProperties"] is False
    assert "minItems" not in s["properties"]["documents"]  # 空 devset 合法


def test_annotation_required_and_props_batch53():
    s = load_schema("annotation.schema.json")
    assert s["required"] == ["annotation_version", "doc_id"]
    assert s["additionalProperties"] is False
    assert sorted(s["properties"].keys()) == [
        "annotation_version", "annotator", "chunk_boundary_anchors",
        "date", "doc_id", "figure_caption_pairs", "heading_order",
    ]


def test_evaluation_report_required_five_batch53():
    s = load_schema("evaluation-report.schema.json")
    assert s["required"] == ["report_version", "provenance", "devset",
                             "summary", "per_doc"]
    assert "expected_failures" not in s["required"]  # 可选段
    assert s["additionalProperties"] is False


def test_document_required_thirteen_batch53():
    s = load_schema("document.schema.json")
    assert s["required"] == [
        "schema_version", "document_id", "source_path", "source_type",
        "source_hash", "parser_name", "parser_version", "elements",
        "chunks", "relations", "warnings", "errors", "metadata",
    ]


def test_document_root_additional_unspecified_batch53():
    """document 根级未锁 additionalProperties（记录现状）。"""
    s = load_schema("document.schema.json")
    assert "additionalProperties" not in s


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(schema_mod)


def test_source_validator_construction_batch53():
    assert "Draft202012Validator(schema)" in _src()


def test_source_sort_lambda_batch53():
    assert "key=lambda e: list(e.absolute_path)" in _src()


def test_source_two_filenotfound_messages_batch53():
    src = _src()
    assert 'raise FileNotFoundError(f"Schema 文件不存在: {p}")' in src
    assert 'raise FileNotFoundError(f"待校验文件不存在: {p}")' in src


def test_source_error_message_template_batch53():
    src = _src()
    assert "Schema '{schema_name}' 校验失败 ({len(errors)} 处)：" in src
    assert "errors=flat" in src


def test_source_flat_entry_fields_batch53():
    src = _src()
    assert '"path": list(err.absolute_path),' in src
    assert '"message": err.message,' in src
    assert '"schema_path": list(err.absolute_schema_path),' in src


def test_source_errors_or_empty_batch53():
    assert "self.errors = errors or []" in _src()


def test_source_all_list_batch53():
    assert '"SCHEMAS_DIR",' in _src()
    assert '"validate_file",' in _src()


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(schema_mod))


def test_ast_init_super_call_batch53():
    tree = _tree()
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    supers = [c for c in ast.walk(init)
              if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
              and c.func.attr == "__init__"]
    assert len(supers) == 1


def test_ast_module_assign_names_batch53():
    tree = _tree()
    names = [n.targets[0].id for n in tree.body
             if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)]
    assert names == ["SCHEMAS_DIR", "__all__"]


def test_ast_with_count_two_batch53():
    tree = _tree()
    withs = [n for n in ast.walk(tree) if isinstance(n, ast.With)]
    assert len(withs) == 2


def test_ast_validate_single_bare_return_batch53():
    tree = _tree()
    func = next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "validate")
    # 裸 return 嵌在 if not errors: 里，须用 ast.walk 找
    rets = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(rets) == 1
    assert rets[0].value is None


def test_ast_raise_count_three_batch53():
    tree = _tree()
    raises = [n for n in ast.walk(tree) if isinstance(n, ast.Raise)]
    assert len(raises) == 3


def test_ast_all_unparse_batch53():
    tree = _tree()
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert ast.unparse(all_assign) == (
        "__all__ = ['SCHEMAS_DIR', 'EvalSchemaError', 'load_schema', "
        "'validate', 'validate_file']"
    )


# ---------- forbidden tokens 第一百七十八批 ----------

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
