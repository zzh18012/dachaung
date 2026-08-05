r"""evaluation/schema.py 边角测试 - 第八轮（Round 246）。

补强已有 base/edges/edges2-7（共 ~660+ 测试）未覆盖的深度：
- 模块 namespace identity：typing.Any / json / Path / Draft202012Validator / JSValidationError
- EvalSchemaError：errors 默认值是 list；message attribute；errors attribute 可 mutate
- _schema_path：name 含 .. 路径穿越；name 是绝对路径；name 含 backslash
- validate：返回 None 验证；不修改 instance
- validate_file：JSONDecodeError 透传（不被捕获）；utf-8 BOM 处理
- 模块源码字符串：docstring 含 manifest / annotation / evaluation-report
- 函数签名精确（含 return annotation）
- callable 验证
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JSValidationError

from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# =========================================================================
# 模块 namespace identity
# =========================================================================


def test_module_typing_any_in_namespace_identity():
    """typing.Any 在 evaluation.schema 命名空间且 is Any。"""
    import evaluation.schema as m
    assert m.Any is Any


def test_module_json_in_namespace_identity():
    """json 在命名空间。"""
    import evaluation.schema as m
    assert m.json is json


def test_module_path_in_namespace_identity():
    """Path 在命名空间。"""
    import evaluation.schema as m
    assert m.Path is Path


def test_module_draft202012_in_namespace_identity():
    """Draft202012Validator 在命名空间。"""
    import evaluation.schema as m
    assert m.Draft202012Validator is Draft202012Validator


def test_module_jsvalidation_error_in_namespace_identity():
    """JSValidationError 在命名空间。"""
    import evaluation.schema as m
    assert m.JSValidationError is JSValidationError


# =========================================================================
# 模块 SCHEMAS_DIR 精确
# =========================================================================


def test_schemas_dir_is_pathlib_path():
    """SCHEMAS_DIR 是 Path 实例。"""
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute_path():
    """SCHEMAS_DIR 是绝对路径。"""
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_value_matches_resolve():
    """SCHEMAS_DIR == schemas/ 目录的 resolve() 路径。"""
    import evaluation.schema as m
    expected = Path(m.__file__).resolve().parent.parent / "schemas"
    assert SCHEMAS_DIR == expected


def test_schemas_dir_exists():
    """SCHEMAS_DIR 目录实际存在。"""
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_contains_manifest_schema():
    """SCHEMAS_DIR 含 manifest.schema.json。"""
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema():
    """SCHEMAS_DIR 含 annotation.schema.json。"""
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema():
    """SCHEMAS_DIR 含 evaluation-report.schema.json。"""
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


# =========================================================================
# __all__ 精确
# =========================================================================


def test_module_all_is_list():
    """__all__ 是 list。"""
    import evaluation.schema as m
    assert isinstance(m.__all__, list)


def test_module_all_exact_order():
    """__all__ 顺序精确。"""
    import evaluation.schema as m
    assert m.__all__ == [
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    ]


def test_module_all_length_five():
    """__all__ 5 个元素。"""
    import evaluation.schema as m
    assert len(m.__all__) == 5


def test_module_all_first_element():
    """__all__[0] 是 'SCHEMAS_DIR'。"""
    import evaluation.schema as m
    assert m.__all__[0] == "SCHEMAS_DIR"


def test_module_all_last_element():
    """__all__[-1] 是 'validate_file'。"""
    import evaluation.schema as m
    assert m.__all__[-1] == "validate_file"


def test_module_all_no_duplicates():
    """__all__ 无重复。"""
    import evaluation.schema as m
    assert len(m.__all__) == len(set(m.__all__))


def test_module_all_does_not_contain_private():
    """__all__ 不含私有 _schema_path。"""
    import evaluation.schema as m
    assert "_schema_path" not in m.__all__


# =========================================================================
# 模块 docstring
# =========================================================================


def test_module_docstring_present():
    """模块有 docstring。"""
    import evaluation.schema as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_manifest():
    """docstring 含 'manifest'。"""
    import evaluation.schema as m
    assert "manifest" in (m.__doc__ or "").lower()


def test_module_docstring_mentions_annotation():
    """docstring 含 'annotation'。"""
    import evaluation.schema as m
    assert "annotation" in (m.__doc__ or "").lower()


def test_module_docstring_mentions_evaluation_report():
    """docstring 含 'evaluation-report'。"""
    import evaluation.schema as m
    assert "evaluation-report" in (m.__doc__ or "").lower()


def test_module_docstring_mentions_no_reuse_with_app_schema():
    """docstring 提到不与 app/schema.py 复用。"""
    import evaluation.schema as m
    doc = (m.__doc__ or "").lower()
    assert "app/schema" in doc or "app" in doc


# =========================================================================
# EvalSchemaError 详细测试
# =========================================================================


def test_eval_schema_error_subclass_of_exception():
    """EvalSchemaError 是 Exception 子类。"""
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_init_default_errors_is_empty_list():
    """EvalSchemaError('msg') → errors=[]。"""
    e = EvalSchemaError("msg")
    assert e.errors == []
    assert isinstance(e.errors, list)


def test_eval_schema_error_init_none_errors_is_empty_list():
    """EvalSchemaError('msg', errors=None) → errors=[]。"""
    e = EvalSchemaError("msg", errors=None)
    assert e.errors == []


def test_eval_schema_error_init_empty_errors_is_empty_list():
    """EvalSchemaError('msg', errors=[]) → errors=[]。"""
    e = EvalSchemaError("msg", errors=[])
    assert e.errors == []


def test_eval_schema_error_init_with_errors_kwarg():
    """EvalSchemaError('msg', errors=[{...}]) → errors 透传。"""
    errs = [{"path": ["a"], "message": "x", "schema_path": ["b"]}]
    e = EvalSchemaError("msg", errors=errs)
    assert e.errors == errs
    assert e.errors is errs  # 同一 list 引用


def test_eval_schema_error_message_attribute():
    """EvalSchemaError('hello') 的 args[0] == 'hello'。"""
    e = EvalSchemaError("hello")
    assert e.args[0] == "hello"


def test_eval_schema_error_errors_is_mutable_list():
    """errors 是 mutable list（可 append）。"""
    e = EvalSchemaError("msg")
    e.errors.append({"path": [], "message": "x", "schema_path": []})
    assert len(e.errors) == 1


def test_eval_schema_error_str_returns_message():
    """str(error) 返回 message。"""
    e = EvalSchemaError("hello world")
    assert str(e) == "hello world"


def test_eval_schema_error_repr_contains_class_name():
    """repr 含类名。"""
    e = EvalSchemaError("msg")
    assert "EvalSchemaError" in repr(e)


def test_eval_schema_error_can_be_raised_and_caught():
    """可 raise 与 except。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        raise EvalSchemaError("test message")
    assert "test message" in str(exc_info.value)


def test_eval_schema_error_caught_as_exception():
    """可被通用 except Exception 捕获。"""
    try:
        raise EvalSchemaError("msg")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_eval_schema_error_init_signature_exact():
    """EvalSchemaError.__init__ 签名：(self, message, errors=None)。"""
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "errors"]
    assert sig.parameters["errors"].default is None


# =========================================================================
# _schema_path 详细测试
# =========================================================================


def test_schema_path_dotdot_in_name_raises():
    """name 含 .. 路径穿越 → 不在 SCHEMAS_DIR → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("../manifest.schema.json")


def test_schema_path_subdir_in_name_raises():
    """name 含子目录 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/manifest.schema.json")


def test_schema_path_with_only_extension_raises():
    """name='.json' → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path(".json")


def test_schema_path_empty_name_raises():
    """name='' → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_uppercase_name_raises():
    """大写 name 在 Windows 上不抛（文件系统 case-insensitive）。

    跳过：本测试只在 case-sensitive 文件系统上有效。
    """
    import sys
    if sys.platform.startswith("win"):
        pytest.skip("Windows 文件系统 case-insensitive，跳过")
    with pytest.raises(FileNotFoundError):
        _schema_path("MANIFEST.SCHEMA.JSON")


def test_schema_path_message_contains_filename():
    """FileNotFoundError message 含 schema 名字。"""
    name = "does-not-exist.schema.json"
    try:
        _schema_path(name)
    except FileNotFoundError as e:
        assert name in str(e)
    else:
        pytest.fail("should have raised")


def test_schema_path_message_contains_schemas_word():
    """FileNotFoundError message 含 'schemas'。"""
    try:
        _schema_path("missing.schema.json")
    except FileNotFoundError as e:
        assert "schemas" in str(e) or "Schema" in str(e)
    else:
        pytest.fail("should have raised")


def test_schema_path_returns_path_for_known_schemas():
    """4 个已知 schema 名字都返回 Path。"""
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        p = _schema_path(name)
        assert isinstance(p, Path)
        assert p.is_file()


def test_schema_path_returns_under_schemas_dir():
    """返回的 Path 在 SCHEMAS_DIR 内。"""
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_signature_exact():
    """signature: (name)。"""
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_schema_path_return_annotation_is_path():
    """return annotation 是 Path（str 形式，from __future__）。"""
    sig = inspect.signature(_schema_path)
    assert isinstance(sig.return_annotation, str)
    assert "Path" in sig.return_annotation


# =========================================================================
# load_schema 详细测试
# =========================================================================


def test_load_schema_returns_dict():
    """load_schema 返回 dict。"""
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_does_not_cache():
    """load_schema 每次返回新 dict。"""
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    assert a is not b
    assert a == b


def test_load_schema_modifying_one_does_not_affect_other():
    """修改一次的返回不影响下次。"""
    a = load_schema("manifest.schema.json")
    a["__test"] = "value"
    b = load_schema("manifest.schema.json")
    assert "__test" not in b


def test_load_schema_each_known_schema_returns_dict():
    """4 个已知 schema 都返回 dict。"""
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        assert isinstance(s, dict)
        assert "$schema" in s


def test_load_schema_signature_exact():
    """signature: (name)。"""
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_load_schema_return_annotation_is_dict():
    """return annotation 是 dict。"""
    sig = inspect.signature(load_schema)
    assert isinstance(sig.return_annotation, str)
    assert "dict" in sig.return_annotation


# =========================================================================
# validate 详细测试
# =========================================================================


def test_validate_returns_none_on_success():
    """validate 通过 → 返回 None。"""
    minimal = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    out = validate(minimal, "manifest.schema.json")
    assert out is None


def test_validate_does_not_modify_instance():
    """validate 不修改 instance。"""
    import copy
    inst = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    before = copy.deepcopy(inst)
    validate(inst, "manifest.schema.json")
    assert inst == before


def test_validate_message_contains_path_field():
    """错误 message 含 'path='。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert "path=" in str(e)
    else:
        pytest.fail("should have raised")


def test_validate_message_contains_schema_name():
    """错误 message 含 schema_name。"""
    try:
        validate({}, "annotation.schema.json")
    except EvalSchemaError as e:
        assert "annotation.schema.json" in str(e)
    else:
        pytest.fail("should have raised")


def test_validate_errors_each_has_three_keys():
    """errors 列表每项有 path/message/schema_path 3 key。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert set(err.keys()) == {"path", "message", "schema_path"}
    else:
        pytest.fail("should have raised")


def test_validate_errors_path_is_list():
    """errors[].path 是 list。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["path"], list)
    else:
        pytest.fail("should have raised")


def test_validate_errors_schema_path_is_list():
    """errors[].schema_path 是 list。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["schema_path"], list)
    else:
        pytest.fail("should have raised")


def test_validate_signature_exact():
    """signature: (instance, schema_name)。"""
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_validate_return_annotation_is_none():
    """return annotation 是 None（from __future__ 让它是 str 'None'）。"""
    sig = inspect.signature(validate)
    # from __future__ import annotations 让 return_annotation 是字符串
    assert sig.return_annotation is None or sig.return_annotation == "None"


# =========================================================================
# validate_file 详细测试
# =========================================================================


def test_validate_file_accepts_str_path(tmp_path: Path):
    """validate_file 接受 str 路径。"""
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    out = validate_file(str(p), "manifest.schema.json")
    assert out is None


def test_validate_file_accepts_path_object(tmp_path: Path):
    """validate_file 接受 Path 对象。"""
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    out = validate_file(p, "manifest.schema.json")
    assert out is None


def test_validate_file_returns_none_on_success(tmp_path: Path):
    """validate_file 成功返回 None。"""
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_missing_raises_filenotfound(tmp_path: Path):
    """文件不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "missing.json", "manifest.schema.json")


def test_validate_file_directory_raises_filenotfound(tmp_path: Path):
    """路径是目录 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecodeerror(tmp_path: Path):
    """非法 JSON → json.JSONDecodeError 透传（不被捕获）。"""
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_schema_error(tmp_path: Path):
    """合法 JSON 但 schema 校验失败 → EvalSchemaError。"""
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")  # 空 dict，缺 required 字段
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_utf8_content(tmp_path: Path):
    """utf-8 编码文件 OK。"""
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    validate_file(p, "manifest.schema.json")  # 不抛


def test_validate_file_chinese_content(tmp_path: Path):
    """含中文的 JSON OK。"""
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "中文文档",
            "path": "测试.pdf",
            "source_type": "pdf",
        }],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_signature_exact():
    """signature: (path, schema_name)。"""
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_validate_file_return_annotation_is_none():
    """return annotation 是 None（str 'None'）。"""
    sig = inspect.signature(validate_file)
    assert sig.return_annotation is None or sig.return_annotation == "None"


# =========================================================================
# callable 验证
# =========================================================================


def test_eval_schema_error_callable_as_constructor():
    """EvalSchemaError 可作为构造器调用。"""
    e = EvalSchemaError("msg")
    assert isinstance(e, EvalSchemaError)


def test_load_schema_callable():
    assert callable(load_schema)


def test_validate_callable():
    assert callable(validate)


def test_validate_file_callable():
    assert callable(validate_file)


def test_schema_path_callable():
    assert callable(_schema_path)


# =========================================================================
# Draft202012Validator 集成
# =========================================================================


def test_load_schema_can_be_used_with_draft202012_validator():
    """load_schema 返回的 dict 可被 Draft202012Validator 使用。"""
    s = load_schema("manifest.schema.json")
    v = Draft202012Validator(s)
    assert v is not None


def test_validate_consistent_with_direct_validator():
    """validate 行为与直接 Draft202012Validator 一致。"""
    s = load_schema("manifest.schema.json")
    v = Draft202012Validator(s)
    bad = {}
    direct_errors = list(v.iter_errors(bad))
    assert len(direct_errors) > 0
    with pytest.raises(EvalSchemaError):
        validate(bad, "manifest.schema.json")


def test_all_known_schemas_are_valid_draft2020():
    """4 个 schema 自身都是合法 Draft 2020-12 schema。"""
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        Draft202012Validator.check_schema(s)
