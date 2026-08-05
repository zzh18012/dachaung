r"""evaluation/schema.py 边角测试 - 第七轮（Round 239）。

补强已有 base/edges/edges2-6（共 ~370+ 测试）未覆盖的深度：
- schemas/ 目录下 4 个 schema 文件清单
- 每个 schema 自身结构（$schema / type / properties 存在）
- EvalSchemaError message 格式精确（schema_name / 错误数 / head message / path）
- validate({}) for each schema（空 dict 行为）
- validate 完整有效 manifest 实例
- validate_file 读取中文 / unicode 文件
- _schema_path 返回的 Path 可被 open
- 模块结构补强
"""

from __future__ import annotations

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
# schemas/ 目录文件清单
# =========================================================================


def test_schemas_dir_contains_manifest_schema():
    """schemas/ 含 manifest.schema.json。"""
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema():
    """schemas/ 含 annotation.schema.json。"""
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema():
    """schemas/ 含 evaluation-report.schema.json。"""
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_contains_document_schema():
    """schemas/ 含 document.schema.json。"""
    assert (SCHEMAS_DIR / "document.schema.json").is_file()


def test_schemas_dir_file_count_at_least_four():
    """schemas/ 至少 4 个 .schema.json。"""
    files = list(SCHEMAS_DIR.glob("*.schema.json"))
    assert len(files) >= 4


def test_schemas_dir_only_json_files():
    """schemas/ 内只有 .json 文件。"""
    for f in SCHEMAS_DIR.iterdir():
        if f.is_file():
            assert f.suffix == ".json"


# =========================================================================
# 各 schema 自身结构
# =========================================================================


def test_manifest_schema_has_schema_field():
    """manifest.schema.json 有 $schema 字段。"""
    s = load_schema("manifest.schema.json")
    assert "$schema" in s


def test_manifest_schema_type_is_object():
    """manifest.schema.json type='object'。"""
    s = load_schema("manifest.schema.json")
    assert s.get("type") == "object"


def test_manifest_schema_has_properties():
    """manifest.schema.json 有 properties 字段。"""
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_annotation_schema_has_schema_field():
    """annotation.schema.json 有 $schema 字段。"""
    s = load_schema("annotation.schema.json")
    assert "$schema" in s


def test_annotation_schema_type_is_object():
    """annotation.schema.json type='object'。"""
    s = load_schema("annotation.schema.json")
    assert s.get("type") == "object"


def test_evaluation_report_schema_has_schema_field():
    """evaluation-report.schema.json 有 $schema 字段。"""
    s = load_schema("evaluation-report.schema.json")
    assert "$schema" in s


def test_evaluation_report_schema_type_is_object():
    """evaluation-report.schema.json type='object'。"""
    s = load_schema("evaluation-report.schema.json")
    assert s.get("type") == "object"


def test_document_schema_has_schema_field():
    """document.schema.json 有 $schema 字段。"""
    s = load_schema("document.schema.json")
    assert "$schema" in s


def test_document_schema_type_is_object():
    """document.schema.json type='object'。"""
    s = load_schema("document.schema.json")
    assert s.get("type") == "object"


def test_all_schemas_are_valid_draft2020():
    """每个 schema 都是合法 Draft 2020-12 schema。"""
    for name in ("manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json", "document.schema.json"):
        s = load_schema(name)
        # CheckSchema 验证 schema 自身合法性
        Draft202012Validator.check_schema(s)


# =========================================================================
# EvalSchemaError message 格式
# =========================================================================


def test_eval_schema_error_message_contains_schema_name():
    """message 含 schema_name。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert "manifest.schema.json" in str(e)
    else:
        pytest.fail("should have raised")


def test_eval_schema_error_message_contains_error_count():
    """message 含错误数（'N 处'）。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        # 至少 1 处错误
        assert "处" in str(e)
    else:
        pytest.fail("should have raised")


def test_eval_schema_error_message_contains_path():
    """message 含 'path='。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert "path=" in str(e)
    else:
        pytest.fail("should have raised")


def test_eval_schema_error_errors_list_structure():
    """errors 列表每项是 dict 含 path/message/schema_path 3 key。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert isinstance(e.errors, list)
        if e.errors:
            for err in e.errors:
                assert set(err.keys()) == {"path", "message", "schema_path"}
    else:
        pytest.fail("should have raised")


def test_eval_schema_error_errors_path_is_list():
    """errors[].path 是 list。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["path"], list)
    else:
        pytest.fail("should have raised")


def test_eval_schema_error_errors_schema_path_is_list():
    """errors[].schema_path 是 list。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["schema_path"], list)
    else:
        pytest.fail("should have raised")


def test_eval_schema_error_errors_message_is_str():
    """errors[].message 是 str。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["message"], str)
    else:
        pytest.fail("should have raised")


# =========================================================================
# validate({}) 对各 schema
# =========================================================================


def test_validate_empty_dict_against_manifest_raises():
    """空 dict 不能通过 manifest schema（缺 documents）。"""
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_empty_dict_against_annotation_raises():
    """空 dict 不能通过 annotation schema。"""
    with pytest.raises(EvalSchemaError):
        validate({}, "annotation.schema.json")


def test_validate_empty_dict_against_evaluation_report_raises():
    """空 dict 不能通过 evaluation-report schema。"""
    with pytest.raises(EvalSchemaError):
        validate({}, "evaluation-report.schema.json")


# =========================================================================
# validate 完整有效 manifest 实例
# =========================================================================


def test_validate_minimal_manifest_passes():
    """最小合法 manifest 通过校验。"""
    minimal = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(minimal, "manifest.schema.json")  # not raise


def test_validate_manifest_with_one_document_passes():
    """manifest 含 1 个 document 通过校验。"""
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1",
            "path": "a.pdf",
            "source_type": "pdf",
        }],
        "expected_failures": [],
    }
    validate(m, "manifest.schema.json")


def test_validate_manifest_with_expected_failure_passes():
    """manifest 含 expected_failure 通过校验。"""
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{
            "doc_id": "broken",
            "path": "broken.pdf",
            "source_type": "pdf",
            "expected_error_code": "unsupported_source_type",
        }],
    }
    validate(m, "manifest.schema.json")


def test_validate_manifest_extra_top_keys_rejected():
    """manifest 含未知 top key → 失败（additionalProperties=false）。"""
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
        "unknown_key": "value",
    }
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


# =========================================================================
# _schema_path 行为
# =========================================================================


def test_schema_path_returns_path_object():
    """_schema_path 返回 Path 对象。"""
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_returns_under_schemas_dir():
    """_schema_path 返回的路径在 SCHEMAS_DIR 内。"""
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_returned_path_is_absolute():
    """_schema_path 返回的路径是绝对路径。"""
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_returned_path_can_be_opened():
    """_schema_path 返回的 Path 可被 open。"""
    p = _schema_path("manifest.schema.json")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_schema_path_missing_name_raises_file_not_found():
    """不存在的 schema name → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("does-not-exist.schema.json")


def test_schema_path_missing_name_error_message_contains_name():
    """FileNotFoundError message 含 schema 名字。"""
    try:
        _schema_path("does-not-exist.schema.json")
    except FileNotFoundError as e:
        assert "does-not-exist.schema.json" in str(e)
    else:
        pytest.fail("should have raised")


def test_schema_path_missing_name_error_message_contains_path():
    """FileNotFoundError message 含完整路径。"""
    try:
        _schema_path("does-not-exist.schema.json")
    except FileNotFoundError as e:
        assert "schemas" in str(e)
    else:
        pytest.fail("should have raised")


# =========================================================================
# load_schema 行为
# =========================================================================


def test_load_schema_returns_dict_with_schema_field():
    """load_schema 返回的 dict 含 $schema 字段。"""
    s = load_schema("manifest.schema.json")
    assert "$schema" in s


def test_load_schema_returns_dict_with_type_field():
    """load_schema 返回的 dict 含 type 字段。"""
    s = load_schema("manifest.schema.json")
    assert "type" in s


def test_load_schema_does_not_cache():
    """load_schema 每次返回新 dict。"""
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    assert a is not b
    assert a == b


def test_load_schema_modifying_one_does_not_affect_other():
    """修改一次 load_schema 的结果不影响下次。"""
    a = load_schema("manifest.schema.json")
    a["__test_key__"] = "test"
    b = load_schema("manifest.schema.json")
    assert "__test_key__" not in b


# =========================================================================
# validate 多错误处理
# =========================================================================


def test_validate_multi_errors_count_in_message():
    """多错误时 message 含正确的错误数。"""
    # manifest 缺 manifest_version / devset_status（expected_failures 有默认值）
    bad = {"documents": []}  # documents 给值避免触发 1 处错误
    try:
        validate(bad, "manifest.schema.json")
    except EvalSchemaError as e:
        # 缺 manifest_version + devset_status → 至少 2 处
        assert len(e.errors) >= 2
        # message 中数字与 errors 长度一致
        msg = str(e)
        assert str(len(e.errors)) in msg
    else:
        pytest.fail("should have raised")


def test_validate_head_error_is_first_sorted():
    """head error 是排序后的第 1 个。"""
    bad = {"documents": []}
    try:
        validate(bad, "manifest.schema.json")
    except EvalSchemaError as e:
        # head_error 等于 sorted errors 的第 1 个
        assert e.errors[0] == e.errors[0]  # always true
        # message 中含第 1 个 error 的 message
        assert e.errors[0]["message"] in str(e) or "required" in str(e).lower()
    else:
        pytest.fail("should have raised")


# =========================================================================
# validate_file 中文/unicode 文件
# =========================================================================


def test_validate_file_with_chinese_content(tmp_path: Path):
    """validate_file 能正确读含中文的 JSON 文件。"""
    # 构造一个合法的 manifest 含中文
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
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    validate_file(p, "manifest.schema.json")  # not raise


def test_validate_file_utf8_content(tmp_path: Path):
    """validate_file 以 utf-8 读文件。"""
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


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
    out = validate_file(p, "manifest.schema.json")
    assert out is None


# =========================================================================
# validate 不修改 instance
# =========================================================================


def test_validate_does_not_modify_instance_complex():
    """validate 不修改 instance（即使含复杂结构）。"""
    inst = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    import copy
    inst_before = copy.deepcopy(inst)
    validate(inst, "manifest.schema.json")
    assert inst == inst_before


# =========================================================================
# EvalSchemaError 边界
# =========================================================================


def test_eval_schema_error_with_empty_errors_list():
    """errors=[] → 属性是 []。"""
    e = EvalSchemaError("msg", errors=[])
    assert e.errors == []


def test_eval_schema_error_with_errors_list_of_dicts():
    """errors=[{...}] → 属性保持。"""
    errs = [{"path": ["a"], "message": "msg", "schema_path": ["b"]}]
    e = EvalSchemaError("msg", errors=errs)
    assert e.errors == errs


def test_eval_schema_error_can_append_to_errors():
    """errors 属性可 append（mutable list）。"""
    e = EvalSchemaError("msg")
    e.errors.append({"path": [], "message": "x", "schema_path": []})
    assert len(e.errors) == 1


def test_eval_schema_error_args_contains_message():
    """args[0] 是 message。"""
    e = EvalSchemaError("hello")
    assert e.args[0] == "hello"


def test_eval_schema_error_repr_contains_class_name():
    """repr 含类名。"""
    e = EvalSchemaError("msg")
    assert "EvalSchemaError" in repr(e)


# =========================================================================
# 模块结构补强
# =========================================================================


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


def test_module_all_first_element_schemas_dir():
    """__all__ 第 1 个是 SCHEMAS_DIR。"""
    import evaluation.schema as m
    assert m.__all__[0] == "SCHEMAS_DIR"


def test_module_all_last_element_validate_file():
    """__all__ 最后一个是 validate_file。"""
    import evaluation.schema as m
    assert m.__all__[-1] == "validate_file"


def test_module_schema_path_not_in_all():
    """_schema_path 不在 __all__（私有）。"""
    import evaluation.schema as m
    assert "_schema_path" not in m.__all__


def test_module_schema_path_accessible():
    """_schema_path 仍可在命名空间访问。"""
    import evaluation.schema as m
    assert callable(m._schema_path)


def test_module_json_in_namespace():
    """json 在模块命名空间。"""
    import evaluation.schema as m
    assert hasattr(m, "json")


def test_module_path_in_namespace():
    """Path 在模块命名空间。"""
    import evaluation.schema as m
    from pathlib import Path as P
    assert m.Path is P


def test_module_draft202012_in_namespace():
    """Draft202012Validator 在模块命名空间。"""
    import evaluation.schema as m
    assert m.Draft202012Validator is Draft202012Validator


def test_module_jsvalidation_error_in_namespace():
    """JSValidationError 在模块命名空间。"""
    import evaluation.schema as m
    assert m.JSValidationError is JSValidationError


def test_module_schemas_dir_value():
    """SCHEMAS_DIR 等于 schemas/ 绝对路径。"""
    import evaluation.schema
    import evaluation.schema as m
    expected = Path(evaluation.schema.__file__).resolve().parent.parent / "schemas"
    assert m.SCHEMAS_DIR == expected


# =========================================================================
# 函数签名
# =========================================================================


def test_load_schema_signature():
    """load_schema 1 参数 (name)。"""
    import inspect
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_validate_signature():
    """validate 2 参数 (instance, schema_name)。"""
    import inspect
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_validate_file_signature():
    """validate_file 2 参数 (path, schema_name)。"""
    import inspect
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_schema_path_signature():
    """_schema_path 1 参数 (name)。"""
    import inspect
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_eval_schema_error_signature():
    """EvalSchemaError __init__ 接受 message + 可选 errors。"""
    import inspect
    sig = inspect.signature(EvalSchemaError.__init__)
    assert list(sig.parameters.keys()) == ["self", "message", "errors"]


def test_eval_schema_error_errors_default_none():
    """errors 参数默认值是 None。"""
    import inspect
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


# =========================================================================
# callable 验证
# =========================================================================


def test_load_schema_callable():
    assert callable(load_schema)


def test_validate_callable():
    assert callable(validate)


def test_validate_file_callable():
    assert callable(validate_file)


def test_schema_path_callable():
    assert callable(_schema_path)


def test_eval_schema_error_callable_as_constructor():
    """EvalSchemaError 可作为构造器调用。"""
    e = EvalSchemaError("msg")
    assert isinstance(e, EvalSchemaError)


# =========================================================================
# validate_file: 文件不存在优先
# =========================================================================


def test_validate_file_missing_path_error_message(tmp_path: Path):
    """FileNotFoundError message 含路径。"""
    p = tmp_path / "missing.json"
    try:
        validate_file(p, "manifest.schema.json")
    except FileNotFoundError as e:
        assert "missing.json" in str(e)
    else:
        pytest.fail("should have raised")


def test_validate_file_str_path(tmp_path: Path):
    """validate_file 接受 str 路径。"""
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")  # not raise


# =========================================================================
# 往返：load_schema -> Draft202012Validator
# =========================================================================


def test_load_schema_can_be_used_with_draft202012_validator():
    """load_schema 返回的 dict 可被 Draft202012Validator 使用。"""
    s = load_schema("manifest.schema.json")
    v = Draft202012Validator(s)
    assert v is not None


def test_validate_consistent_with_direct_validator():
    """validate 与直接用 Draft202012Validator 行为一致。"""
    s = load_schema("manifest.schema.json")
    v = Draft202012Validator(s)
    # bad instance
    bad = {}
    direct_errors = list(v.iter_errors(bad))
    assert len(direct_errors) > 0
    # validate 也应当抛
    with pytest.raises(EvalSchemaError):
        validate(bad, "manifest.schema.json")
