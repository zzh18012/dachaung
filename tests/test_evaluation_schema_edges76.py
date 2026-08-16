"""evaluation/schema.py 第一百零七轮 edges 测试（Round 750）。

补强 edges74/edges75 未触及的角度（第一百一十五批）。

新角度：
- 错误排序头选择：iter_errors 先命中 manifest_version 类型/const 两处、
  后命中缺失 devset_status，但 sorted 后 head 是 path=[] 的缺_required
  —— 证明 validate 用排序结果而非首次命中
- 同 path 双错（type + const 都在 ['manifest_version']）→ flat 里两行
- EvalSchemaError.errors 三态：缺省 []、显式 [] 仍 []、显式列表原样保留
- load_schema 每次新 dict：相等不同一、改动不串味
- SCHEMAS_DIR monkeypatch → 自备迷你 schema 全链路（load + validate_file）
- BOM 文件 → json.JSONDecodeError "Unexpected UTF-8 BOM"（现状记录：
  读取用 utf-8 而非 utf-8-sig）
- 目录当文件 → FileNotFoundError（待校验文件不存在）
- annotation.schema.json 顶层键 9 个精确
- forbidden tokens 第二百二十批
"""

from __future__ import annotations

import ast
import collections
import inspect
import json

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    load_schema,
    validate,
    validate_file,
)


# ---------- 排序头选择 ----------

def test_sorted_head_is_missing_required_batch54():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": 1.0, "documents": []},
                 "manifest.schema.json")
    assert ei.value.args[0].startswith(
        "Schema 'manifest.schema.json' 校验失败 (3 处)："
        "'devset_status' is a required property @ path=[]")


def test_same_path_two_errors_flat_batch54():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": 1.0}, "manifest.schema.json")
    paths = [f["path"] for f in ei.value.errors]
    assert paths.count(["manifest_version"]) == 2


def test_flat_error_row_shape_batch54():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": 1.0, "documents": []},
                 "manifest.schema.json")
    rows = [r for r in ei.value.errors if r["path"] == ["manifest_version"]]
    assert len(rows) == 2
    assert set(rows[0]) == {"path", "message", "schema_path"}
    assert rows[0]["message"].startswith("1.0 is not of type 'string'")


# ---------- EvalSchemaError.errors 三态 ----------

def test_error_class_default_empty_batch54():
    assert EvalSchemaError("m").errors == []


def test_error_class_explicit_empty_still_empty_batch54():
    assert EvalSchemaError("m", []).errors == []


def test_error_class_explicit_preserved_batch54():
    e = EvalSchemaError("m", [{"path": ["x"]}])
    assert e.errors == [{"path": ["x"]}]
    assert str(e) == "m"
    assert isinstance(e, Exception)


# ---------- load_schema 纯度 ----------

def test_load_schema_fresh_dict_each_call_batch54():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2
    assert s1 is not s2


def test_load_schema_mutation_isolated_batch54():
    s1 = load_schema("manifest.schema.json")
    s1["zzz"] = 1
    assert "zzz" not in load_schema("manifest.schema.json")


# ---------- SCHEMAS_DIR 可移植 ----------

def test_schemas_dir_shape_batch54():
    assert SCHEMAS_DIR.name == "schemas"
    assert SCHEMAS_DIR.is_absolute()
    assert SCHEMAS_DIR.is_dir()


def test_custom_schemas_dir_full_chain_batch54(tmp_path, monkeypatch):
    (tmp_path / "t.schema.json").write_text(
        json.dumps({"type": "object"}), encoding="utf-8")
    monkeypatch.setattr(schema_mod, "SCHEMAS_DIR", tmp_path)
    assert load_schema("t.schema.json") == {"type": "object"}
    validate_file(str(tmp_path / "t.schema.json"), "t.schema.json")
    with pytest.raises(FileNotFoundError) as fi:
        load_schema("missing.json")
    assert "Schema 文件不存在" in str(fi.value)


# ---------- validate_file 输入形态 ----------

def test_validate_file_bom_json_decode_error_batch54(tmp_path):
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf{"manifest_version": "1.0"}')
    with pytest.raises(json.JSONDecodeError) as ji:
        validate_file(p, "manifest.schema.json")
    assert "Unexpected UTF-8 BOM" in str(ji.value)


def test_validate_file_directory_rejected_batch54(tmp_path):
    with pytest.raises(FileNotFoundError) as fi:
        validate_file(tmp_path, "manifest.schema.json")
    assert "待校验文件不存在" in str(fi.value)


def test_validate_file_non_json_decode_error_batch54(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_unknown_schema_name_batch54():
    with pytest.raises(FileNotFoundError):
        validate({}, "nope.schema.json")


def test_validate_success_returns_none_batch54():
    assert validate({"manifest_version": "1.0",
                     "devset_status": "incomplete",
                     "documents": []}, "manifest.schema.json") is None


# ---------- annotation schema 顶层键 ----------

def test_annotation_schema_top_keys_nine_batch54():
    assert sorted(load_schema("annotation.schema.json")) == [
        "$defs", "$id", "$schema", "additionalProperties", "description",
        "properties", "required", "title", "type"]


# ---------- __all__ 与 AST ----------

def test_all_export_five_names_batch54():
    assert schema_mod.__all__ == [
        "SCHEMAS_DIR", "EvalSchemaError", "load_schema", "validate",
        "validate_file"]


def test_ast_module_structure_batch54():
    tree = ast.parse(inspect.getsource(schema_mod))
    c = collections.Counter(type(n).__name__ for n in ast.walk(tree))
    assert (c["FunctionDef"], c["Raise"], c["With"], c["If"],
            c["Try"]) == (5, 3, 2, 3, 0)


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(schema_mod)


def test_source_sort_key_and_flat_batch54():
    src = _src()
    assert "key=lambda e: list(e.absolute_path)" in src
    assert "errors or []" in src


# ---------- forbidden tokens 第二百二十批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch54():
    assert _src().count("open(") == 2
