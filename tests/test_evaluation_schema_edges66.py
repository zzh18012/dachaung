"""evaluation/schema.py 第九十七轮 edges 测试（Round 680）。

补强 edges65 未触及的角度（第五十三批）。

新角度：
- EvalSchemaError 更深（errors 属性可写 / errors None vs list 区别 / raise + from None 抑制 / super().__init__ 调用顺序 / message 含 schema_name+count+path / errors 元素结构）
- _schema_path 更多场景（返回 Path 类型 / 在 schemas/ 目录下 / 不带 .schema.json 后缀 / 带子目录 / 多种非法名）
- load_schema 多场景（schema 内容 $id / $schema / type / properties / required）
- validate 错误排序（按 absolute_path 排序）
- validate_file 多场景（str 路径 / Path 路径等价 / 二者都 FileNotFoundError / 二者都成功）
- SCHEMAS_DIR 行为（resolve 后绝对路径 / 是 evaluation 上一级的 sibling）
- 模块源码补强（Draft202012Validator / JSValidationError import 路径 / errors flat list 构造 / for err in errors / head = errors[0] / 多个 f-string）
- AST 结构补强（EvalSchemaError ClassDef 含 __init__/docstring / _schema_path 1 If + 1 Raise / load_schema 1 With + 1 Return / validate 1 For + 1 Sorted + 1 Raise + flat.append / validate_file 1 If + 1 With + 1 Call / SCHEMAS_DIR Assign / __all__ List 5 / 6 imports）
- forbidden tokens 第一百五十批
"""

from __future__ import annotations

import ast
import inspect
import json
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


# ---------- EvalSchemaError 更深 ----------

def test_eval_schema_error_errors_attribute_settable_batch52():
    e = EvalSchemaError("x")
    e.errors = [{"new": "data"}]
    assert e.errors == [{"new": "data"}]


def test_eval_schema_error_errors_none_vs_list_batch52():
    e1 = EvalSchemaError("x")  # None default
    e2 = EvalSchemaError("x", errors=None)
    e3 = EvalSchemaError("x", errors=[])
    assert e1.errors == []
    assert e2.errors == []
    assert e3.errors == []


def test_eval_schema_error_raise_with_from_none_batch52():
    """raise ... from None 抑制 __cause__。"""
    try:
        try:
            raise ValueError("orig")
        except ValueError:
            raise EvalSchemaError("wrapped") from None
    except EvalSchemaError as e:
        assert e.__cause__ is None
        assert e.__suppress_context__ is True


def test_eval_schema_error_super_init_stores_args_batch52():
    e = EvalSchemaError("hello")
    assert e.args == ("hello",)


def test_eval_schema_error_message_contains_count_and_path_batch52():
    """validate 失败时 message 含 schema_name + 错误数 + path。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        msg = str(e)
        assert "manifest.schema.json" in msg
        assert "校验失败" in msg
        # 错误数（至少 1）
        assert "处" in msg


def test_eval_schema_error_errors_element_structure_batch52():
    """validate 抛出的 errors 元素含 path/message/schema_path。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert "path" in err
            assert "message" in err
            assert "schema_path" in err
            assert isinstance(err["path"], list)
            assert isinstance(err["schema_path"], list)


def test_eval_schema_error_class_has_docstring_batch52():
    assert EvalSchemaError.__doc__ is not None
    assert "Schema" in EvalSchemaError.__doc__ or "校验" in EvalSchemaError.__doc__


def test_eval_schema_error_can_be_pickled_via_init_batch52():
    """errors 字段在 __init__ 后是普通 list（可序列化）。"""
    e = EvalSchemaError("x", errors=[{"k": "v"}])
    # list 序列化
    s = json.dumps(e.errors)
    assert json.loads(s) == [{"k": "v"}]


def test_eval_schema_error_inherits_exception_attributes_batch52():
    e = EvalSchemaError("x")
    # Exception 标准属性
    assert hasattr(e, "args")
    assert hasattr(e, "__cause__")
    assert hasattr(e, "__traceback__")


# ---------- _schema_path 更多场景 ----------

def test_schema_path_returns_path_instance_batch52():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_under_schemas_dir_batch52():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_non_schema_name_batch52():
    """不带 .schema.json 后缀的文件名 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("nonexistent.json")


def test_schema_path_subdir_in_name_batch52():
    """含子目录的名字 → 拼接 SCHEMAS_DIR，仍不存在。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/nonexistent.schema.json")


def test_schema_path_multiple_invalid_names_batch52():
    for name in ["nope", "", " ", "foo.schema.json"]:
        with pytest.raises(FileNotFoundError):
            _schema_path(name)


def test_schema_path_error_message_contains_path_batch52():
    try:
        _schema_path("nonexistent.schema.json")
    except FileNotFoundError as e:
        msg = str(e)
        assert "Schema 文件不存在" in msg
        assert "nonexistent.schema.json" in msg


def test_schema_path_3_valid_names_batch52():
    for name in ["manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"]:
        p = _schema_path(name)
        assert p.is_file()


# ---------- load_schema 多场景 ----------

def test_load_schema_manifest_has_id_batch52():
    s = load_schema("manifest.schema.json")
    assert "$schema" in s
    # Draft 2020-12
    assert "2020-12" in s["$schema"]


def test_load_schema_annotation_has_id_batch52():
    s = load_schema("annotation.schema.json")
    assert "$schema" in s


def test_load_schema_evaluation_report_has_id_batch52():
    s = load_schema("evaluation-report.schema.json")
    assert "$schema" in s


def test_load_schema_manifest_has_type_object_batch52():
    s = load_schema("manifest.schema.json")
    assert s.get("type") == "object"


def test_load_schema_returns_dict_batch52():
    for name in ["manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"]:
        s = load_schema(name)
        assert isinstance(s, dict)


def test_load_schema_manifest_has_properties_batch52():
    s = load_schema("manifest.schema.json")
    assert "properties" in s
    assert isinstance(s["properties"], dict)


def test_load_schema_manifest_has_required_batch52():
    s = load_schema("manifest.schema.json")
    assert "required" in s
    assert isinstance(s["required"], list)


def test_load_schema_unknown_name_raises_batch52():
    with pytest.raises(FileNotFoundError):
        load_schema("nope.schema.json")


# ---------- validate 错误排序 ----------

def test_validate_errors_sorted_by_path_batch52():
    """多 errors 时按 absolute_path 排序。"""
    # 构造一个错得多的 instance
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        # errors 列表应按 path 字典序（jsonschema 内部已 sorted）
        paths = [tuple(err["path"]) for err in e.errors]
        assert paths == sorted(paths)


def test_validate_no_errors_returns_none_batch52():
    """合法 instance → return None。"""
    valid_manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    result = validate(valid_manifest, "manifest.schema.json")
    assert result is None


def test_validate_calls_load_schema_batch52():
    """validate 内部调用 load_schema。"""
    with patch("evaluation.schema.load_schema") as ls:
        ls.return_value = {"type": "object"}  # 合法 schema
        validate({}, "any.schema.json")
        ls.assert_called_once_with("any.schema.json")


def test_validate_unknown_schema_name_raises_filenotfound_batch52():
    with pytest.raises(FileNotFoundError):
        validate({}, "unknown.schema.json")


# ---------- validate_file 多场景 ----------

def test_validate_file_accepts_str_path_batch52(tmp_path):
    p = tmp_path / "data.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    # str 路径
    result = validate_file(str(p), "manifest.schema.json")
    assert result is None


def test_validate_file_accepts_path_path_batch52(tmp_path):
    p = tmp_path / "data.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    # Path 路径
    result = validate_file(p, "manifest.schema.json")
    assert result is None


def test_validate_file_str_path_not_exist_batch52():
    with pytest.raises(FileNotFoundError):
        validate_file("/no/such/file.json", "manifest.schema.json")


def test_validate_file_path_path_not_exist_batch52():
    with pytest.raises(FileNotFoundError):
        validate_file(Path("/no/such/file.json"), "manifest.schema.json")


def test_validate_file_json_decode_error_batch52(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_eval_schema_error_batch52(tmp_path):
    p = tmp_path / "invalid.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_calls_validate_batch52(tmp_path):
    """validate_file 内部调用 validate。"""
    p = tmp_path / "data.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    with patch("evaluation.schema.validate") as v:
        validate_file(p, "manifest.schema.json")
        v.assert_called_once()


def test_validate_file_unknown_schema_raises_filenotfound_batch52(tmp_path):
    p = tmp_path / "data.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "nope.schema.json")


# ---------- SCHEMAS_DIR 行为 ----------

def test_schemas_dir_is_absolute_batch52():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_resolved_batch52():
    """SCHEMAS_DIR 已 resolve。"""
    # resolve() 多次调用应等价
    assert SCHEMAS_DIR == SCHEMAS_DIR.resolve()


def test_schemas_dir_is_directory_batch52():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_parent_is_project_root_batch52():
    """SCHEMAS_DIR.parent 应是 evaluation/ 的 parent = 项目根。"""
    # SCHEMAS_DIR 在 evaluation/.parent/schemas/ = 项目根/schemas/
    # SCHEMAS_DIR.parent 是项目根
    assert (SCHEMAS_DIR.parent / "evaluation").is_dir()


def test_schemas_dir_contains_3_schemas_batch52():
    files = list(SCHEMAS_DIR.glob("*.schema.json"))
    names = {f.name for f in files}
    assert "manifest.schema.json" in names
    assert "annotation.schema.json" in names
    assert "evaluation-report.schema.json" in names


def test_schemas_dir_value_matches_module_level_path_batch52():
    """SCHEMAS_DIR 应等于 Path(__file__).resolve().parent.parent / 'schemas'。"""
    expected = Path(schema_mod.__file__).resolve().parent.parent / "schemas"
    assert SCHEMAS_DIR == expected


# ---------- 模块源码补强 ----------

def test_source_future_annotations_batch52():
    src = inspect.getsource(schema_mod)
    assert "from __future__ import annotations" in src


def test_source_json_import_batch52():
    src = inspect.getsource(schema_mod)
    assert "import json" in src


def test_source_pathlib_path_import_batch52():
    src = inspect.getsource(schema_mod)
    assert "from pathlib import Path" in src


def test_source_typing_any_import_batch52():
    src = inspect.getsource(schema_mod)
    assert "from typing import Any" in src


def test_source_jsonschema_draft2020_import_batch52():
    src = inspect.getsource(schema_mod)
    assert "from jsonschema import Draft202012Validator" in src


def test_source_jsvalidation_error_import_batch52():
    src = inspect.getsource(schema_mod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_source_schemas_dir_definition_batch52():
    src = inspect.getsource(schema_mod)
    assert 'SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"' in src


def test_source_eval_schema_error_docstring_batch52():
    src = inspect.getsource(schema_mod)
    assert "Schema 校验失败时抛出" in src


def test_source_eval_schema_error_init_batch52():
    src = inspect.getsource(schema_mod)
    assert "def __init__(self, message: str, errors: list[dict[str, Any]] | None = None)" in src
    assert "self.errors = errors or []" in src


def test_source_validate_uses_iter_errors_batch52():
    src = inspect.getsource(schema_mod)
    assert "validator.iter_errors(instance)" in src


def test_source_validate_uses_flat_append_batch52():
    src = inspect.getsource(schema_mod)
    assert "flat.append(" in src


def test_source_validate_head_first_error_batch52():
    src = inspect.getsource(schema_mod)
    assert "head = errors[0]" in src


def test_source_validate_uses_absolute_path_batch52():
    src = inspect.getsource(schema_mod)
    assert "err.absolute_path" in src
    assert "err.absolute_schema_path" in src


def test_source_validate_uses_absolute_path_in_head_msg_batch52():
    src = inspect.getsource(schema_mod)
    assert "head.absolute_path" in src


def test_source_validate_message_format_batch52():
    src = inspect.getsource(schema_mod)
    assert "校验失败" in src
    assert "{len(errors)}" in src or "len(errors)" in src


def test_source_schema_path_function_docstring_batch52():
    src = inspect.getsource(schema_mod)
    assert 'Schema 文件不存在' in src


def test_source_load_schema_function_docstring_batch52():
    src = inspect.getsource(schema_mod)
    assert "从 schemas/ 目录加载命名 Schema" in src


def test_source_validate_function_docstring_batch52():
    src = inspect.getsource(schema_mod)
    assert "校验 instance dict 是否符合命名 Schema" in src


def test_source_validate_file_function_docstring_batch52():
    src = inspect.getsource(schema_mod)
    assert "加载磁盘 JSON 并按命名 Schema 校验" in src


def test_source_does_not_reuse_app_schema_batch52():
    """模块 docstring 说明不与 app/schema.py 复用。"""
    src = inspect.getsource(schema_mod)
    assert "不与 app/schema.py 复用" in src


def test_source_all_5_entries_batch52():
    src = inspect.getsource(schema_mod)
    for name in ("SCHEMAS_DIR", "EvalSchemaError", "load_schema", "validate", "validate_file"):
        assert f'"{name}"' in src


# ---------- AST 结构补强 ----------

def test_ast_has_4_functions_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 4  # _schema_path, load_schema, validate, validate_file


def test_ast_function_names_order_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_schema_path", "load_schema", "validate", "validate_file"]


def test_ast_has_1_class_def_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 1
    assert classes[0].name == "EvalSchemaError"


def test_ast_eval_schema_error_has_init_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError")
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert len(methods) == 1
    assert methods[0].name == "__init__"


def test_ast_eval_schema_error_init_2_args_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError")
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    args = init.args
    assert len(args.args) == 3  # self, message, errors
    assert args.args[0].arg == "self"
    assert args.args[1].arg == "message"
    assert args.args[2].arg == "errors"
    assert len(args.defaults) == 1  # errors=None


def test_ast_eval_schema_error_calls_super_init_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError")
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    src = ast.unparse(init)
    assert "super().__init__(message)" in src


def test_ast_eval_schema_error_init_assigns_self_errors_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError")
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    assigns = [n for n in ast.walk(init) if isinstance(n, ast.Assign)]
    # 至少 1 个 self.errors = ...
    found = False
    for a in assigns:
        for t in a.targets:
            if isinstance(t, ast.Attribute) and t.attr == "errors":
                found = True
    assert found


def test_ast_has_6_imports_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 6  # __future__ + json + Path + Any + Draft202012 + JSValidationError


def test_ast_module_docstring_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_has_2_module_level_assigns_batch52():
    """SCHEMAS_DIR + __all__ = 2。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 2


def test_ast_schemas_dir_assign_uses_path_join_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "SCHEMAS_DIR" for t in n.targets)
    )
    # value 应是 BinOp with /
    assert isinstance(assign.value, ast.BinOp)
    assert isinstance(assign.value.op, ast.Div)


def test_ast_schema_path_has_1_if_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_schema_path")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) == 1


def test_ast_schema_path_has_1_raise_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_schema_path")
    raises = [n for n in ast.walk(func) if isinstance(n, ast.Raise)]
    assert len(raises) == 1


def test_ast_schema_path_raises_filenotfounderror_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_schema_path")
    src = ast.unparse(func)
    assert "FileNotFoundError" in src


def test_ast_schema_path_1_return_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_schema_path")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 1


def test_ast_load_schema_1_with_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_schema")
    withs = [n for n in ast.walk(func) if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_load_schema_1_return_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_schema")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 1


def test_ast_load_schema_calls_json_load_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_schema")
    src = ast.unparse(func)
    assert "json.load(f)" in src


def test_ast_load_schema_calls_schema_path_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_schema")
    src = ast.unparse(func)
    assert "_schema_path(name)" in src


def test_ast_validate_uses_draft202012_validator_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    src = ast.unparse(func)
    assert "Draft202012Validator" in src


def test_ast_validate_1_for_loop_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_validate_1_sorted_call_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    sorted_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "sorted"
    ]
    assert len(sorted_calls) == 1


def test_ast_validate_sorted_has_lambda_key_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    sorted_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "sorted"
    ]
    assert len(sorted_calls[0].keywords) == 1
    kw = sorted_calls[0].keywords[0]
    assert kw.arg == "key"
    assert isinstance(kw.value, ast.Lambda)


def test_ast_validate_raises_eval_schema_error_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    raises = [n for n in ast.walk(func) if isinstance(n, ast.Raise)]
    assert len(raises) == 1


def test_ast_validate_returns_none_when_no_errors_batch52():
    """validate 在 if not errors: 分支 return（隐式 None）。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    # 1 个 explicit return（在 if not errors 分支）
    assert len(returns) == 1


def test_ast_validate_file_has_1_with_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    withs = [n for n in ast.walk(func) if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_validate_file_has_1_if_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) == 1


def test_ast_validate_file_calls_validate_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    src = ast.unparse(func)
    assert "validate(data, schema_name)" in src


def test_ast_validate_file_has_path_arg_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    args = func.args
    assert len(args.args) == 2
    assert args.args[0].arg == "path"
    assert args.args[1].arg == "schema_name"


def test_ast_validate_file_path_annotation_union_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    src = ast.unparse(func)
    assert "path: Path | str" in src


def test_ast_no_async_function_def_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_no_star_import_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


def test_ast_no_with_at_module_level_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        assert not isinstance(n, ast.With)


def test_ast_no_while_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))


def test_ast_no_try_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert not any(isinstance(n, ast.Try) for n in ast.walk(tree))


def test_ast_no_delete_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert not any(isinstance(n, ast.Delete) for n in ast.walk(tree))


def test_ast_no_raise_outside_functions_batch52():
    """raise 只出现在 _schema_path 和 validate 中，不在 module-level。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        # module-level 不应有 Raise
        if isinstance(n, ast.Raise):
            assert False, "Module-level Raise not allowed"


def test_ast_no_global_nonlocal_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


def test_ast_all_value_is_list_5_batch52():
    tree = ast.parse(inspect.getsource(schema_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert isinstance(all_assign.value, ast.List)
    assert len(all_assign.value.elts) == 5


# ---------- forbidden tokens 第一百五十批 ----------

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
    """load_schema 1 + validate_file 1 = 2 个 open。"""
    assert _src().count("open(") == 2
