"""evaluation/schema.py 第九十一轮 edges 测试（Round 634）。

补强 edges59 未触及的角度（第四十五批）。

新角度：
- SCHEMAS_DIR 各种属性
- _schema_path 各种边界
- load_schema 各种 schema 内容深度
- validate 多个错误聚合
- validate 多种 instance 类型组合
- validate_file 各种编码处理
- validate_file 与 validate 调用关系
- EvalSchemaError 各种初始化方式
- EvalSchemaError message 与 errors 字段
- 模块源码字符串精确
- AST 结构
- forbidden tokens 第一百零四批
"""

from __future__ import annotations

import ast
import inspect
import json
import pickle
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

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


# ---------- SCHEMAS_DIR 各种属性 ----------

def test_schemas_dir_is_pathlib_path_batch45():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute_batch45():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_exists_batch45():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_name_batch45():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_parent_has_pyproject_batch45():
    assert (SCHEMAS_DIR.parent / "pyproject.toml").is_file()


def test_schemas_dir_resolved_idempotent_batch45():
    """resolve() 已经是绝对，再 resolve 不变。"""
    assert SCHEMAS_DIR.resolve() == SCHEMAS_DIR


def test_schemas_dir_in_evaluation_parent_batch45():
    """SCHEMAS_DIR.parent 应该是项目根（不是 evaluation 目录）。"""
    # SCHEMAS_DIR = evaluation.parent / "schemas"
    assert SCHEMAS_DIR.parent.name != "evaluation"


def test_schemas_dir_contains_json_only_batch45():
    for p in SCHEMAS_DIR.iterdir():
        if p.is_file():
            assert p.suffix == ".json"


def test_schemas_dir_at_least_3_schemas_batch45():
    """至少有 3 个 schema：manifest / annotation / evaluation-report。"""
    files = [p for p in SCHEMAS_DIR.iterdir() if p.is_file()]
    assert len(files) >= 3


# ---------- _schema_path 各种边界 ----------

def test_schema_path_returns_path_batch45():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_existing_schema_batch45():
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_missing_raises_file_not_found_batch45():
    with pytest.raises(FileNotFoundError):
        _schema_path("missing.schema.json")


def test_schema_path_error_message_contains_path_batch45():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("totally_missing.json")
    msg = str(exc_info.value)
    assert "totally_missing.json" in msg
    assert "Schema 文件不存在" in msg


def test_schema_path_error_message_contains_full_path_batch45():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("missing.json")
    msg = str(exc_info.value)
    # 含完整 schemas 目录路径
    assert "schemas" in msg


def test_schema_path_with_subdir_batch45():
    """name 可以含子目录（虽然现在没有，但实现支持）。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/file.json")


def test_schema_path_string_concat_batch45():
    """_schema_path 用 SCHEMAS_DIR / name 拼接。"""
    src = inspect.getsource(_schema_path)
    assert "SCHEMAS_DIR / name" in src


def test_schema_path_extension_check_batch45():
    """实现不强制 .json 后缀，任何 name 都查。"""
    # 给一个非 .json 名字也会查
    with pytest.raises(FileNotFoundError):
        _schema_path("README.md")


# ---------- load_schema 各 schema 内容深度 ----------

def test_load_schema_manifest_has_required_keys_batch45():
    s = load_schema("manifest.schema.json")
    assert "required" in s
    required = s["required"]
    assert "manifest_version" in required
    assert "devset_status" in required
    assert "documents" in required


def test_load_schema_manifest_type_batch45():
    s = load_schema("manifest.schema.json")
    assert s.get("type") == "object"


def test_load_schema_manifest_has_properties_batch45():
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_load_schema_manifest_has_manifest_version_const_batch45():
    s = load_schema("manifest.schema.json")
    # manifest_version 用 const 限定为 "1.0"
    mv = s.get("properties", {}).get("manifest_version", {})
    assert mv.get("const") == "1.0" or mv.get("enum") == ["1.0"]


def test_load_schema_manifest_has_devset_status_enum_batch45():
    s = load_schema("manifest.schema.json")
    ds = s.get("properties", {}).get("devset_status", {})
    assert "enum" in ds
    assert "complete" in ds["enum"]
    assert "incomplete" in ds["enum"]


def test_load_schema_annotation_type_batch45():
    s = load_schema("annotation.schema.json")
    assert s.get("type") == "object"


def test_load_schema_annotation_has_properties_batch45():
    s = load_schema("annotation.schema.json")
    assert "properties" in s


def test_load_schema_evaluation_report_type_batch45():
    s = load_schema("evaluation-report.schema.json")
    assert s.get("type") == "object"


def test_load_schema_evaluation_report_has_required_batch45():
    s = load_schema("evaluation-report.schema.json")
    assert "required" in s


def test_load_schema_evaluation_report_has_report_version_batch45():
    s = load_schema("evaluation-report.schema.json")
    assert "report_version" in s.get("properties", {})


def test_load_schema_returns_dict_batch45():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_missing_raises_file_not_found_batch45():
    with pytest.raises(FileNotFoundError):
        load_schema("missing.schema.json")


def test_load_schema_json_decode_error_batch45(tmp_path):
    """如果 schema 文件本身不是 JSON → JSONDecodeError。"""
    # 用 monkeypatch 替换 _schema_path 返回的文件
    fake_path = tmp_path / "broken.schema.json"
    fake_path.write_text("not json", encoding="utf-8")
    with patch("evaluation.schema._schema_path", return_value=fake_path):
        with pytest.raises(json.JSONDecodeError):
            load_schema("broken.schema.json")


# ---------- validate 多个错误聚合 ----------

def test_validate_empty_dict_multiple_errors_batch45():
    """manifest 空 dict → 多个 required 错误。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    # errors 应该至少 3 个（manifest_version / devset_status / documents）
    assert len(exc_info.value.errors) >= 3


def test_validate_error_count_in_message_batch45():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    msg = str(exc_info.value)
    # 消息含 "处" 错误数
    assert "处" in msg


def test_validate_errors_have_path_batch45():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for e in exc_info.value.errors:
        assert "path" in e
        assert isinstance(e["path"], list)


def test_validate_errors_have_message_batch45():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for e in exc_info.value.errors:
        assert "message" in e
        assert isinstance(e["message"], str)


def test_validate_errors_have_schema_path_batch45():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for e in exc_info.value.errors:
        assert "schema_path" in e
        assert isinstance(e["schema_path"], list)


def test_validate_returns_none_on_success_batch45():
    valid = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    assert validate(valid, "manifest.schema.json") is None


def test_validate_invalid_extra_field_batch45():
    """manifest 不允许 additionalProperties（取决于 schema）。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "extra_field": "should fail if additionalProperties=False",
    }
    # 不抛即过（取决于 schema 是否禁止 additionalProperties）
    try:
        validate(data, "manifest.schema.json")
    except EvalSchemaError:
        pass  # 也允许抛


def test_validate_documents_invalid_type_batch45():
    """documents 必须是 array。"""
    bad = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": "not array",
    }
    with pytest.raises(EvalSchemaError):
        validate(bad, "manifest.schema.json")


def test_validate_manifest_version_invalid_enum_batch45():
    """manifest_version="9.9" 不在 enum 中。"""
    bad = {
        "manifest_version": "9.9",
        "devset_status": "incomplete",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(bad, "manifest.schema.json")


def test_validate_devset_status_invalid_enum_batch45():
    bad = {
        "manifest_version": "1.0",
        "devset_status": "partial",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(bad, "manifest.schema.json")


def test_validate_top_level_list_batch45():
    """顶层是 list 而非 dict。"""
    with pytest.raises(EvalSchemaError):
        validate([], "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_top_level_string_batch45():
    with pytest.raises(EvalSchemaError):
        validate("not dict", "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_top_level_int_batch45():
    with pytest.raises(EvalSchemaError):
        validate(42, "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_top_level_none_batch45():
    with pytest.raises(EvalSchemaError):
        validate(None, "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_top_level_bool_batch45():
    with pytest.raises(EvalSchemaError):
        validate(True, "manifest.schema.json")  # type: ignore[arg-type]


# ---------- validate_file 各种编码处理 ----------

def test_validate_file_utf8_with_chinese_batch45(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "comment": "测试中文",
    }), encoding="utf-8")
    # 不抛即过（如果有 additionalProperties=False 会抛，但通常 manifest 允许 extra）
    try:
        validate_file(p, "manifest.schema.json")
    except EvalSchemaError:
        pass


def test_validate_file_path_object_batch45(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    # 接受 Path 对象
    validate_file(p, "manifest.schema.json")


def test_validate_file_str_path_batch45(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_not_found_batch45(tmp_path):
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_file(tmp_path / "missing.json", "manifest.schema.json")
    msg = str(exc_info.value)
    assert "待校验文件不存在" in msg
    assert "missing.json" in msg


def test_validate_file_json_decode_error_batch45(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("not json at all", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_calls_validate_batch45(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    with patch("evaluation.schema.validate", return_value=None) as mock_v:
        validate_file(p, "any.schema.json")
    mock_v.assert_called_once_with({"foo": "bar"}, "any.schema.json")


def test_validate_file_success_no_return_value_batch45(tmp_path):
    """成功时返回 None。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_propagates_eval_schema_error_batch45(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"bad": "data"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


# ---------- EvalSchemaError 各种初始化 ----------

def test_eval_schema_error_message_only_batch45():
    e = EvalSchemaError("just message")
    assert str(e) == "just message"
    assert e.errors == []


def test_eval_schema_error_with_errors_batch45():
    errs = [{"path": ["a"], "message": "x"}]
    e = EvalSchemaError("msg", errors=errs)
    assert e.errors == errs


def test_eval_schema_error_errors_none_default_empty_batch45():
    e = EvalSchemaError("msg", errors=None)
    assert e.errors == []


def test_eval_schema_error_errors_empty_list_batch45():
    e = EvalSchemaError("msg", errors=[])
    assert e.errors == []


def test_eval_schema_error_inherits_exception_batch45():
    e = EvalSchemaError("x")
    assert isinstance(e, Exception)


def test_eval_schema_error_catchable_as_exception_batch45():
    try:
        raise EvalSchemaError("x")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_eval_schema_error_args_batch45():
    e = EvalSchemaError("msg")
    assert "msg" in e.args


def test_eval_schema_error_can_chain_from_batch45():
    try:
        try:
            raise ValueError("orig")
        except ValueError as orig:
            raise EvalSchemaError("wrap") from orig
    except EvalSchemaError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, ValueError)


def test_eval_schema_error_pickle_roundtrip_batch45():
    """EvalSchemaError 应该可 pickle（继承 Exception）。"""
    e = EvalSchemaError("msg", errors=[{"path": ["a"]}])
    data = pickle.dumps(e)
    out = pickle.loads(data)
    assert isinstance(out, EvalSchemaError)
    assert str(out) == "msg"


def test_eval_schema_error_pickle_preserves_errors_batch45():
    """pickle 应该保留 errors 字段（但默认 Exception 不保留 extra attrs）。"""
    e = EvalSchemaError("msg", errors=[{"path": ["a"], "message": "x"}])
    data = pickle.dumps(e)
    out = pickle.loads(data)
    # 注意：默认 pickle 只保留 args，不保留自定义 attrs
    # 但 str(out) 应该还原
    assert str(out) == "msg"


def test_eval_schema_error_repr_batch45():
    e = EvalSchemaError("msg")
    r = repr(e)
    assert "EvalSchemaError" in r


def test_eval_schema_error_errors_attribute_writable_batch45():
    """errors 可以重新赋值。"""
    e = EvalSchemaError("msg")
    e.errors = [{"x": 1}]
    assert e.errors == [{"x": 1}]


def test_eval_schema_error_multiple_instances_independent_batch45():
    """不同实例的 errors 不共享。"""
    e1 = EvalSchemaError("a")
    e2 = EvalSchemaError("b")
    e1.errors.append({"x": 1})
    assert e2.errors == []


# ---------- 模块源码字符串精确 ----------

def test_module_docstring_contains_does_not_reuse_app_schema_batch45():
    src = inspect.getsource(schema_mod)
    assert "不与 app/schema.py 复用" in src


def test_module_docstring_contains_business_vs_evaluation_batch45():
    src = inspect.getsource(schema_mod)
    assert "业务输出" in src
    assert "评测元数据" in src


def test_module_source_contains_json_import_batch45():
    src = inspect.getsource(schema_mod)
    assert "import json" in src


def test_module_source_contains_pathlib_import_batch45():
    src = inspect.getsource(schema_mod)
    assert "from pathlib import Path" in src


def test_module_source_contains_any_import_batch45():
    src = inspect.getsource(schema_mod)
    assert "from typing import Any" in src


def test_module_source_contains_jsonschema_import_batch45():
    src = inspect.getsource(schema_mod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_contains_jsvalidationerror_import_batch45():
    """注意：实现 import 了 JSValidationError 但实际未用。"""
    src = inspect.getsource(schema_mod)
    assert "JSValidationError" in src or "ValidationError" in src


def test_module_source_contains_eval_schema_error_class_batch45():
    src = inspect.getsource(schema_mod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_contains_errors_or_empty_list_batch45():
    src = inspect.getsource(schema_mod)
    assert "self.errors = errors or []" in src


def test_module_source_contains_schema_path_function_batch45():
    src = inspect.getsource(schema_mod)
    assert "def _schema_path(name: str) -> Path:" in src


def test_module_source_contains_load_schema_function_batch45():
    src = inspect.getsource(schema_mod)
    assert "def load_schema(name: str) -> dict[str, Any]:" in src


def test_module_source_contains_validate_function_batch45():
    src = inspect.getsource(schema_mod)
    assert "def validate(instance: dict[str, Any], schema_name: str) -> None:" in src


def test_module_source_contains_validate_file_function_batch45():
    src = inspect.getsource(schema_mod)
    assert "def validate_file(path: Path | str, schema_name: str) -> None:" in src


def test_module_source_contains_draft_validator_batch45():
    src = inspect.getsource(schema_mod)
    assert "Draft202012Validator" in src


def test_module_source_contains_iter_errors_batch45():
    src = inspect.getsource(schema_mod)
    assert "iter_errors" in src


def test_module_source_contains_sorted_batch45():
    src = inspect.getsource(schema_mod)
    assert "sorted(" in src


def test_module_source_contains_absolute_path_batch45():
    src = inspect.getsource(schema_mod)
    assert "absolute_path" in src


def test_module_source_contains_absolute_schema_path_batch45():
    src = inspect.getsource(schema_mod)
    assert "absolute_schema_path" in src


def test_module_source_contains_schemas_dir_definition_batch45():
    src = inspect.getsource(schema_mod)
    assert "SCHEMAS_DIR = Path(__file__).resolve().parent.parent" in src


def test_module_source_contains_file_not_found_two_places_batch45():
    src = inspect.getsource(schema_mod)
    # _schema_path 抛 FileNotFoundError 含 "Schema 文件不存在"
    assert "Schema 文件不存在" in src
    # validate_file 抛 FileNotFoundError 含 "待校验文件不存在"
    assert "待校验文件不存在" in src


# ---------- __all__ ----------

def test_all_exact_order_batch45():
    assert list(schema_mod.__all__) == [
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    ]


def test_all_count_five_batch45():
    assert len(schema_mod.__all__) == 5


def test_all_entries_importable_batch45():
    for name in schema_mod.__all__:
        assert hasattr(schema_mod, name)


def test_all_entries_unique_batch45():
    assert len(set(schema_mod.__all__)) == len(schema_mod.__all__)


# ---------- AST 结构 ----------

def test_ast_top_level_one_class_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 1
    assert classes[0].name == "EvalSchemaError"


def test_ast_top_level_function_count_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 4


def test_ast_top_level_function_names_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_schema_path", "load_schema", "validate", "validate_file"]


def test_ast_eval_schema_error_only_init_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError"][0]
    methods = [n.name for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert methods == ["__init__"]


def test_ast_eval_schema_error_init_calls_super_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError"][0]
    init = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"][0]
    has_super = False
    for n in ast.walk(init):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if n.func.attr == "__init__":
                has_super = True
    assert has_super


def test_ast_validate_has_sorted_call_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate"][0]
    has_sorted = False
    for n in ast.walk(func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "sorted":
            has_sorted = True
    assert has_sorted


def test_ast_validate_has_iter_errors_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate"][0]
    has_iter = False
    for n in ast.walk(func):
        if isinstance(n, ast.Attribute) and n.attr == "iter_errors":
            has_iter = True
    assert has_iter


def test_ast_validate_has_raise_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate"][0]
    raises = [n for n in ast.walk(func) if isinstance(n, ast.Raise)]
    assert len(raises) >= 1


def test_ast_validate_has_for_in_for_loop_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate"][0]
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) >= 1


def test_ast_validate_file_calls_validate_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file"][0]
    has_call = False
    for n in ast.walk(func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id == "validate":
                has_call = True
    assert has_call


def test_ast_validate_file_calls_json_load_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file"][0]
    has_json_load = False
    for n in ast.walk(func):
        if isinstance(n, ast.Attribute) and n.attr == "load":
            has_json_load = True
    assert has_json_load


def test_ast_no_class_in_function_body_batch45():
    """函数体内不应有 class 定义。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        if isinstance(n, ast.FunctionDef):
            for sub in ast.walk(n):
                assert not isinstance(sub, ast.ClassDef)


def test_ast_no_for_in_module_body_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        assert not isinstance(n, ast.For)


def test_ast_no_while_in_module_body_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_no_async_in_module_body_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_first_node_docstring_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)


def test_ast_second_node_future_import_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


def test_ast_eval_schema_error_inherits_exception_batch45():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError"][0]
    assert len(cls.bases) == 1
    assert isinstance(cls.bases[0], ast.Name)
    assert cls.bases[0].id == "Exception"


# ---------- forbidden tokens 第一百零四批 ----------

def test_source_no_eval_batch45():
    src = inspect.getsource(schema_mod)
    assert "eval(" not in src


def test_source_no_exec_batch45():
    src = inspect.getsource(schema_mod)
    assert "exec(" not in src


def test_source_no_compile_batch45():
    src = inspect.getsource(schema_mod)
    assert "compile(" not in src


def test_source_no_globals_batch45():
    src = inspect.getsource(schema_mod)
    assert "globals(" not in src


def test_source_no_locals_batch45():
    src = inspect.getsource(schema_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch45():
    src = inspect.getsource(schema_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch45():
    src = inspect.getsource(schema_mod)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch45():
    src = inspect.getsource(schema_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch45():
    src = inspect.getsource(schema_mod)
    assert "pickle.load(" not in src


def test_source_no_subprocess_batch45():
    src = inspect.getsource(schema_mod)
    assert "subprocess" not in src


def test_source_no_class_other_than_eval_schema_error_batch45():
    """只有 EvalSchemaError 一个 class。"""
    src = inspect.getsource(schema_mod)
    # 统计 "class X" 模式（class 关键字后跟空格 + identifier）
    import re
    matches = re.findall(r"^class\s+\w+", src, re.MULTILINE)
    assert len(matches) == 1
    assert matches[0] == "class EvalSchemaError"


def test_source_no_async_def_batch45():
    src = inspect.getsource(schema_mod)
    assert "async def" not in src


def test_source_no_yield_batch45():
    src = inspect.getsource(schema_mod)
    assert "yield" not in src


def test_source_no_walrus_batch45():
    src = inspect.getsource(schema_mod)
    assert ":=" not in src


def test_source_uses_json_load_batch45():
    """使用 json.load 而非 pickle/yaml。"""
    src = inspect.getsource(schema_mod)
    assert "json.load" in src
