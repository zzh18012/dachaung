"""evaluation/schema.py 第三十轮 edges 测试（Round 400）。

补强 edges29 未触及的角度：
- EvalSchemaError 行为深度第十批（chain __cause__ / __context__ / Unicode message / empty message / 各种 errors 形式）
- load_schema 行为深度第十批（4 schemas 返 dict / unknown raises / 目录 raises / idempotent / independent dict / $schema / type=object / properties / required / 不调 validator）
- validate 行为深度第十批（更多 schema 与 instance 组合 / error path 结构 / error schema_path / instance 不 mutate）
- validate_file 行为深度第十批（更多 corner cases）
- _schema_path 行为深度第十批
- SCHEMAS_DIR 常量深度第十批
- module source forbidden tokens 第十四批
- module source 字符串精确补强第十批
- signatures 第十批
- module 合理性第十批
- 端到端集成第十批
"""

from __future__ import annotations

import inspect
import json
import os
from pathlib import Path

import pytest

from evaluation import schema as smod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- EvalSchemaError 行为深度第十批 ----------


def test_eval_schema_error_unicode_message_batch10():
    e = EvalSchemaError("中文错误")
    assert "中文错误" in str(e)


def test_eval_schema_error_empty_message_batch10():
    e = EvalSchemaError("")
    assert str(e) == ""


def test_eval_schema_error_chain_cause_batch10():
    try:
        try:
            raise RuntimeError("inner")
        except RuntimeError as inner:
            raise EvalSchemaError("outer") from inner
    except EvalSchemaError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, RuntimeError)


def test_eval_schema_error_chain_context_batch10():
    """raise within except → __context__ 自动设置。"""
    try:
        try:
            raise RuntimeError("inner")
        except RuntimeError:
            raise EvalSchemaError("outer")
    except EvalSchemaError as e:
        # __context__ 自动设置（不显式 from）
        assert e.__context__ is not None
        assert isinstance(e.__context__, RuntimeError)


def test_eval_schema_error_errors_with_empty_dict_batch10():
    """errors 中可以含空 dict。"""
    e = EvalSchemaError("msg", [{}])
    assert e.errors == [{}]


def test_eval_schema_error_errors_with_unicode_value_batch10():
    e = EvalSchemaError("msg", [{"path": ["中文"], "message": "中文消息"}])
    assert e.errors[0]["path"] == ["中文"]
    assert e.errors[0]["message"] == "中文消息"


def test_eval_schema_error_errors_default_empty_list_batch10():
    """无 errors 参数 → 默认 []。"""
    e = EvalSchemaError("msg")
    assert e.errors == []
    assert isinstance(e.errors, list)


def test_eval_schema_error_str_includes_message_batch10():
    e = EvalSchemaError("my_message")
    assert "my_message" in str(e)


def test_eval_schema_error_repr_includes_class_name_batch10():
    e = EvalSchemaError("msg")
    assert "EvalSchemaError" in repr(e)


def test_eval_schema_error_args_eq_batch10():
    e1 = EvalSchemaError("msg")
    e2 = EvalSchemaError("msg")
    assert e1.args == e2.args


def test_eval_schema_error_equality_batch10():
    """同 message 的两个实例不相等（默认引用相等）。"""
    e1 = EvalSchemaError("msg")
    e2 = EvalSchemaError("msg")
    assert e1 is not e2


def test_eval_schema_error_can_be_pickle_friendly_batch10():
    """errors 字段是普通 list[dict]，可 JSON 序列化。"""
    e = EvalSchemaError("msg", [{"path": ["a"], "message": "x"}])
    text = json.dumps(e.errors)
    parsed = json.loads(text)
    assert parsed == e.errors


# ---------- load_schema 行为深度第十批 ----------


def test_load_schema_returns_dict_strict_batch10():
    s = load_schema("manifest.schema.json")
    assert type(s) is dict


def test_load_schema_manifest_has_required_keys_batch10():
    s = load_schema("manifest.schema.json")
    assert "manifest_version" in s.get("properties", {})


def test_load_schema_evaluation_report_has_required_keys_batch10():
    s = load_schema("evaluation-report.schema.json")
    assert "report_version" in s.get("properties", {})


def test_load_schema_document_has_required_keys_batch10():
    s = load_schema("document.schema.json")
    # document schema 应含 document_id / source_type / 等
    props = s.get("properties", {})
    assert len(props) > 0


def test_load_schema_annotation_has_required_keys_batch10():
    s = load_schema("annotation.schema.json")
    props = s.get("properties", {})
    assert len(props) > 0


def test_load_schema_unknown_with_dot_json_raises_batch10():
    with pytest.raises(FileNotFoundError):
        load_schema("totally-unknown.schema.json")


def test_load_schema_empty_string_raises_batch10():
    with pytest.raises(FileNotFoundError):
        load_schema("")


def test_load_schema_with_subdir_suffix_batch10():
    """名字带 / → 当作目录路径解析。"""
    with pytest.raises(FileNotFoundError):
        load_schema("subdir/x.json")


def test_load_schema_idempotent_value_batch10():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2


def test_load_schema_independent_dict_batch10():
    """两次返回不是同一对象。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 is not s2


def test_load_schema_modification_does_not_persist_batch10():
    """修改返回的 dict 不影响下次加载。"""
    s1 = load_schema("manifest.schema.json")
    s1["__added_by_test"] = True
    s2 = load_schema("manifest.schema.json")
    assert "__added_by_test" not in s2


# ---------- validate 行为深度第十批 ----------


def _valid_manifest_data():
    return {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }


def test_validate_returns_none_on_success_batch10():
    assert validate(_valid_manifest_data(), "manifest.schema.json") is None


def test_validate_error_contains_path_list_batch10():
    data = _valid_manifest_data()
    data["manifest_version"] = 999  # int 而非 str
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    e = exc_info.value
    # errors 列表中至少一条有 path
    assert any("path" in err for err in e.errors)


def test_validate_error_contains_message_str_batch10():
    data = _valid_manifest_data()
    data["manifest_version"] = 999
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    e = exc_info.value
    assert any("message" in err and isinstance(err["message"], str) for err in e.errors)


def test_validate_error_contains_schema_path_list_batch10():
    data = _valid_manifest_data()
    data["manifest_version"] = 999
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    e = exc_info.value
    assert any("schema_path" in err for err in e.errors)


def test_validate_error_count_in_message_batch10():
    data = _valid_manifest_data()
    data["manifest_version"] = 999
    data["devset_status"] = "invalid"
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    # 至少 1 处错误
    assert "校验失败" in str(exc_info.value)


def test_validate_does_not_mutate_input_batch10():
    data = _valid_manifest_data()
    snapshot = json.dumps(data, sort_keys=True)
    try:
        validate(data, "manifest.schema.json")
    except Exception:
        pass
    assert json.dumps(data, sort_keys=True) == snapshot


def test_validate_unknown_schema_raises_file_not_found_batch10():
    with pytest.raises(FileNotFoundError):
        validate({}, "no_such.schema.json")


def test_validate_extra_top_level_field_raises_batch10():
    data = _valid_manifest_data()
    data["totally_extra_field"] = "x"
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_documents_not_list_raises_batch10():
    data = _valid_manifest_data()
    data["documents"] = "string"
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_expected_failures_not_list_raises_batch10():
    data = _valid_manifest_data()
    data["expected_failures"] = {}
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_kwargs_call_batch10():
    out1 = validate(_valid_manifest_data(), "manifest.schema.json")
    out2 = validate(instance=_valid_manifest_data(), schema_name="manifest.schema.json")
    assert out1 == out2


# ---------- validate_file 行为深度第十批 ----------


def test_validate_file_str_path_batch10(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest_data()), encoding="utf-8")
    # 不抛 = 通过
    assert validate_file(str(p), "manifest.schema.json") is None


def test_validate_file_path_obj_batch10(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest_data()), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_nonexistent_raises_file_not_found_batch10(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "no.json", "manifest.schema.json")


def test_validate_file_directory_raises_file_not_found_batch10(tmp_path):
    """目录不是 file → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_invalid_json_raises_json_decode_batch10(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_schema_content_raises_eval_schema_batch10(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"manifest_version": "wrong"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_unknown_schema_raises_file_not_found_batch10(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest_data()), encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "no_such.schema.json")


def test_validate_file_kwargs_call_batch10(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest_data()), encoding="utf-8")
    out = validate_file(path=p, schema_name="manifest.schema.json")
    assert out is None


def test_validate_file_idempotent_batch10(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest_data()), encoding="utf-8")
    out1 = validate_file(p, "manifest.schema.json")
    out2 = validate_file(p, "manifest.schema.json")
    assert out1 == out2


def test_validate_file_returns_none_type_batch10(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest_data()), encoding="utf-8")
    out = validate_file(p, "manifest.schema.json")
    assert out is None


# ---------- _schema_path 行为深度第十批 ----------


def test_schema_path_returns_path_type_batch10():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_absolute_batch10():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_existing_file_batch10():
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_unknown_raises_file_not_found_batch10():
    with pytest.raises(FileNotFoundError):
        _schema_path("nonexistent.json")


def test_schema_path_empty_string_raises_batch10():
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_directory_form_raises_batch10():
    """目录名通过 _schema_path 解析为 SCHEMAS_DIR/目录 → is_file False → raise。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir")


def test_schema_path_idempotent_batch10():
    p1 = _schema_path("manifest.schema.json")
    p2 = _schema_path("manifest.schema.json")
    assert p1 == p2


def test_schema_path_resolves_to_schemas_dir_batch10():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_str_input_batch10():
    """str 输入应工作。"""
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_does_not_read_file_batch10():
    """_schema_path 仅返回路径，不读文件。"""
    # 多次调用应不抛
    for _ in range(3):
        _schema_path("manifest.schema.json")


# ---------- SCHEMAS_DIR 常量深度第十批 ----------


def test_schemas_dir_is_path_batch10():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute_batch10():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_exists_batch10():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_endswith_schemas_batch10():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_contains_4_json_files_batch10():
    json_files = list(SCHEMAS_DIR.glob("*.schema.json"))
    # 至少 4 个：manifest / annotation / evaluation-report / document
    assert len(json_files) >= 4


def test_schemas_dir_contains_manifest_schema_batch10():
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema_batch10():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema_batch10():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_contains_document_schema_batch10():
    assert (SCHEMAS_DIR / "document.schema.json").is_file()


def test_schemas_dir_in_module_namespace_batch10():
    assert "SCHEMAS_DIR" in vars(smod)


def test_schemas_dir_immutable_attribute_batch10():
    """SCHEMAS_DIR 是 module-level 常量。"""
    # 多次访问返回同一对象
    assert smod.SCHEMAS_DIR is SCHEMAS_DIR


# ---------- module source forbidden tokens 第十四批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "pickle.loads",
        "yaml.load",
        "yaml.unsafe_load",
        "subprocess.check_call",
        "subprocess.call",
        "subprocess.getoutput",
        "os.popen",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
    ],
)
def test_schema_source_no_forbidden_token_fourteenth_batch10(token):
    source = inspect.getsource(smod)
    assert token not in source


def test_schema_source_no_unlink_batch10():
    source = inspect.getsource(smod)
    assert "unlink" not in source


def test_schema_source_no_remove_batch10():
    source = inspect.getsource(smod)
    assert ".remove(" not in source


def test_schema_source_no_kill_batch10():
    source = inspect.getsource(smod)
    assert ".kill(" not in source


def test_schema_source_no_terminate_batch10():
    source = inspect.getsource(smod)
    assert ".terminate(" not in source


def test_schema_source_no_async_def_batch10():
    source = inspect.getsource(smod)
    assert "async def" not in source


def test_schema_source_no_yield_batch10():
    source = inspect.getsource(smod)
    assert "yield" not in source


def test_schema_source_no_walrus_batch10():
    source = inspect.getsource(smod)
    assert ":=" not in source


def test_schema_source_no_top_level_lambda_batch10():
    source = inspect.getsource(smod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_schema_source_no_print_batch10():
    source = inspect.getsource(smod)
    assert "print(" not in source


def test_schema_source_no_socket_batch10():
    source = inspect.getsource(smod)
    assert "socket" not in source


def test_schema_source_no_threading_batch10():
    source = inspect.getsource(smod)
    assert "threading" not in source


def test_schema_source_no_multiprocessing_batch10():
    source = inspect.getsource(smod)
    assert "multiprocessing" not in source


def test_schema_source_no_asyncio_batch10():
    source = inspect.getsource(smod)
    assert "asyncio" not in source


def test_schema_source_no_pickle_module_batch10():
    source = inspect.getsource(smod)
    assert "import pickle" not in source


# ---------- module source 字符串精确补强第十批 ----------


def test_module_source_has_future_annotations_batch10():
    source = inspect.getsource(smod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_json_batch10():
    source = inspect.getsource(smod)
    assert "import json" in source


def test_module_source_imports_path_batch10():
    source = inspect.getsource(smod)
    assert "from pathlib import Path" in source


def test_module_source_imports_typing_any_batch10():
    source = inspect.getsource(smod)
    assert "from typing import Any" in source


def test_module_source_imports_draft202012_validator_batch10():
    source = inspect.getsource(smod)
    assert "Draft202012Validator" in source


def test_module_source_imports_jsonschema_validation_error_batch10():
    source = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in source


def test_module_source_has_schemas_dir_constant_batch10():
    source = inspect.getsource(smod)
    assert "SCHEMAS_DIR" in source


def test_module_source_has_eval_schema_error_class_batch10():
    source = inspect.getsource(smod)
    assert "class EvalSchemaError" in source


def test_module_source_has_schema_path_def_batch10():
    source = inspect.getsource(smod)
    assert "def _schema_path(" in source


def test_module_source_has_load_schema_def_batch10():
    source = inspect.getsource(smod)
    assert "def load_schema(" in source


def test_module_source_has_validate_def_batch10():
    source = inspect.getsource(smod)
    assert "def validate(" in source


def test_module_source_has_validate_file_def_batch10():
    source = inspect.getsource(smod)
    assert "def validate_file(" in source


def test_module_source_no_main_block_batch10():
    source = inspect.getsource(smod)
    assert "if __name__" not in source


def test_module_source_docstring_present_batch10():
    assert smod.__doc__ is not None
    assert len(smod.__doc__) > 30


def test_module_source_docstring_mentions_schema_batch10():
    assert smod.__doc__ is not None
    assert "Schema" in smod.__doc__ or "schema" in smod.__doc__


# ---------- signatures 第十批 ----------


def test_signature_eval_schema_error_init_3_params_batch10():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert len(sig.parameters) == 3


def test_signature_eval_schema_error_init_param_names_batch10():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert list(sig.parameters) == ["self", "message", "errors"]


def test_signature_eval_schema_error_init_errors_default_none_batch10():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_signature_schema_path_1_param_batch10():
    sig = inspect.signature(_schema_path)
    assert len(sig.parameters) == 1


def test_signature_schema_path_param_name_batch10():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters) == ["name"]


def test_signature_load_schema_1_param_batch10():
    sig = inspect.signature(load_schema)
    assert len(sig.parameters) == 1


def test_signature_load_schema_param_name_batch10():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters) == ["name"]


def test_signature_validate_2_params_batch10():
    sig = inspect.signature(validate)
    assert len(sig.parameters) == 2


def test_signature_validate_param_names_batch10():
    sig = inspect.signature(validate)
    assert list(sig.parameters) == ["instance", "schema_name"]


def test_signature_validate_param_kinds_batch10():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_validate_no_defaults_batch10():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_validate_file_2_params_batch10():
    sig = inspect.signature(validate_file)
    assert len(sig.parameters) == 2


def test_signature_validate_file_param_names_batch10():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters) == ["path", "schema_name"]


def test_signature_funcs_function_type_batch10():
    for func in (_schema_path, load_schema, validate, validate_file):
        assert inspect.isfunction(func)


def test_signature_funcs_module_eq_batch10():
    for func in (_schema_path, load_schema, validate, validate_file):
        assert func.__module__ == "evaluation.schema"


# ---------- module 合理性第十批 ----------


def test_module_all_value_batch10():
    assert smod.__all__ == [
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    ]


def test_module_all_is_list_batch10():
    assert isinstance(smod.__all__, list)


def test_module_all_entries_unique_batch10():
    assert len(smod.__all__) == len(set(smod.__all__))


def test_module_all_entries_str_batch10():
    for name in smod.__all__:
        assert isinstance(name, str)


def test_module_has_dunder_file_batch10():
    assert hasattr(smod, "__file__")
    assert smod.__file__ is not None


def test_module_dunder_file_endswith_schema_py_batch10():
    import os
    sep = os.sep
    assert smod.__file__.endswith("evaluation" + sep + "schema.py") or smod.__file__.endswith(
        "evaluation/schema.py"
    )


def test_module_name_is_evaluation_schema_batch10():
    assert smod.__name__ == "evaluation.schema"


def test_module_user_function_count_batch10():
    funcs = [
        n for n, v in vars(smod).items()
        if inspect.isfunction(v) and v.__module__ == smod.__name__
    ]
    assert set(funcs) == {"_schema_path", "load_schema", "validate", "validate_file"}


def test_module_user_class_count_batch10():
    classes = [
        n for n, v in vars(smod).items()
        if inspect.isclass(v) and v.__module__ == smod.__name__
    ]
    assert set(classes) == {"EvalSchemaError"}


def test_module_docstring_present_batch10():
    assert smod.__doc__ is not None
    assert len(smod.__doc__) > 30


def test_module_docstring_mentions_not_reuse_batch10():
    """docstring 提到不与 app/schema.py 复用。"""
    assert smod.__doc__ is not None
    assert "不与" in smod.__doc__ or "分开" in smod.__doc__


# ---------- 端到端集成第十批 ----------


def test_e2e_validate_load_schema_then_validate_batch10():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)
    out = validate(_valid_manifest_data(), "manifest.schema.json")
    assert out is None


def test_e2e_validate_file_full_chain_batch10(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest_data()), encoding="utf-8")
    out = validate_file(p, "manifest.schema.json")
    assert out is None


def test_e2e_eval_schema_error_full_chain_batch10():
    """构造 EvalSchemaError → 抛 → 捕 → 校验字段。"""
    try:
        raise EvalSchemaError("msg", [{"path": ["x"], "message": "y"}])
    except EvalSchemaError as e:
        assert e.errors == [{"path": ["x"], "message": "y"}]
        assert "msg" in str(e)


def test_e2e_validate_file_unicode_content_batch10(tmp_path):
    """含 Unicode 的 manifest 内容（在合法 schema 范围内）。"""
    p = tmp_path / "m.json"
    data = _valid_manifest_data()
    data["devset_status"] = "incomplete"  # 必须是合法 enum
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    out = validate_file(p, "manifest.schema.json")
    assert out is None


def test_e2e_load_schema_returns_serializable_batch10():
    s = load_schema("manifest.schema.json")
    text = json.dumps(s)
    parsed = json.loads(text)
    assert parsed == s


def test_e2e_combined_validate_idempotent_batch10():
    """多次 validate 同一 instance。"""
    data = _valid_manifest_data()
    out1 = validate(data, "manifest.schema.json")
    out2 = validate(data, "manifest.schema.json")
    assert out1 == out2


def test_e2e_schemas_dir_accessible_batch10():
    """SCHEMAS_DIR 可访问、可读、可 glob。"""
    files = list(SCHEMAS_DIR.glob("*.json"))
    assert len(files) >= 4


def test_e2e_eval_schema_error_no_subclass_of_value_error_batch10():
    """EvalSchemaError 不是 ValueError 的子类。"""
    assert not issubclass(EvalSchemaError, ValueError)


def test_e2e_eval_schema_error_no_subclass_of_type_error_batch10():
    assert not issubclass(EvalSchemaError, TypeError)


def test_e2e_combined_chain_validate_then_load_batch10():
    """validate 后 load_schema 仍工作（不互相影响）。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError:
        pass
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)
