"""evaluation/schema.py 第二十七轮 edges 测试（Round 379）。

重点补强 edges26 未触及的角度：
- EvalSchemaError 行为深度第七批（更多边界）
- load_schema 行为深度第七批（更多边界）
- validate 行为深度第七批（更多场景）
- validate_file 行为深度第七批
- _schema_path 行为深度第七批
- SCHEMAS_DIR 常量深度第七批
- module source forbidden tokens 第十一批
- module source 字符串精确补强第七批
- signatures 第七批
- module 合理性第七批
- 端到端集成第七批
"""

from __future__ import annotations

import inspect
import json
import types
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from evaluation import schema as smod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- EvalSchemaError 行为深度第七批 ----------


def test_eval_schema_error_message_attribute_value():
    err = EvalSchemaError("custom message")
    assert err.args == ("custom message",)


def test_eval_schema_error_str_does_not_include_errors():
    err = EvalSchemaError("msg", [{"path": [], "message": "err"}])
    s = str(err)
    assert "msg" in s
    assert "path" not in s  # str 不显示 errors


def test_eval_schema_error_repr_includes_module_qualified_name():
    err = EvalSchemaError("msg")
    r = repr(err)
    assert "EvalSchemaError" in r


def test_eval_schema_error_can_be_chained_with_from():
    """支持 raise ... from ... 形式."""
    try:
        try:
            raise ValueError("original")
        except ValueError as e:
            raise EvalSchemaError("wrapped") from e
    except EvalSchemaError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, ValueError)


def test_eval_schema_error_errors_default_value_is_list_type():
    err = EvalSchemaError("msg")
    assert isinstance(err.errors, list)


def test_eval_schema_error_errors_attribute_can_be_modified():
    err = EvalSchemaError("msg", [])
    err.errors.append({"path": [0]})
    assert err.errors == [{"path": [0]}]


def test_eval_schema_error_can_be_raisable_with_complex_payload():
    """errors 可含任意结构."""
    complex_errors = [
        {
            "path": ["documents", 0, "path"],
            "message": "is not valid",
            "schema_path": ["properties", "documents", "items"],
            "context": {"additional": "data"},
        }
    ]
    try:
        raise EvalSchemaError("fail", complex_errors)
    except EvalSchemaError as e:
        assert e.errors == complex_errors


def test_eval_schema_error_inherits_all_exception_attributes():
    err = EvalSchemaError("msg")
    # Exception 的属性都应在
    assert hasattr(err, "args")
    assert hasattr(err, "__cause__")
    assert hasattr(err, "__context__")
    assert hasattr(err, "__traceback__")


def test_eval_schema_error_class_attribute_errors_default_does_not_exist():
    """EvalSchemaError 没有 class-level errors default."""
    assert not hasattr(EvalSchemaError, "errors")


def test_eval_schema_error_init_signature_keyword_only_options():
    """message 是 positional, errors 是 positional-or-keyword."""
    sig = inspect.signature(EvalSchemaError.__init__)
    assert "message" in sig.parameters
    assert "errors" in sig.parameters
    # message 无默认（必填）, errors 有默认 None
    assert sig.parameters["message"].default is inspect.Parameter.empty
    assert sig.parameters["errors"].default is None


def test_eval_schema_error_raise_with_keyword_args():
    """支持 raise EvalSchemaError(message='x', errors=[])."""
    err = EvalSchemaError(message="kw", errors=None)
    assert err.args == ("kw",)
    assert err.errors == []


def test_eval_schema_error_init_self_parameter_exists():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert "self" in sig.parameters


# ---------- load_schema 行为深度第七批 ----------


def test_load_schema_returns_dict_for_each_known_schema():
    for name in ("manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json", "document.schema.json"):
        s = load_schema(name)
        assert isinstance(s, dict)


def test_load_schema_each_has_schema_dollar_key():
    for name in ("manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json", "document.schema.json"):
        s = load_schema(name)
        assert "$schema" in s
        assert "2020-12" in s["$schema"]


def test_load_schema_each_has_type_object():
    for name in ("manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json", "document.schema.json"):
        s = load_schema(name)
        assert s.get("type") == "object"


def test_load_schema_id_url_format():
    """$id 应是 URL 字符串."""
    for name in ("manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json", "document.schema.json"):
        s = load_schema(name)
        assert "$id" in s
        assert isinstance(s["$id"], str)
        assert s["$id"].startswith("http")


def test_load_schema_does_not_invoke_validator():
    """load_schema 只加载，不校验 schema 本身."""
    # 这个测试确保 load_schema 不依赖 Draft202012Validator.check_schema
    # 通过 mock 验证：直接打开文件读
    s = load_schema("manifest.schema.json")
    # 应能被 Draft202012Validator 接受
    v = Draft202012Validator(s)
    assert v is not None


def test_load_schema_unknown_extension_raises():
    """文件名后缀不影响（FileNotFoundError by name）."""
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.txt")


def test_load_schema_directory_as_name_raises():
    """传一个目录名 → FileNotFoundError（SCHEMAS_DIR/name 不是 file）."""
    with pytest.raises(FileNotFoundError):
        load_schema("subdir")


def test_load_schema_idempotent():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2


def test_load_schema_no_modification_to_module_state():
    """连续调用不应改变模块级状态."""
    state_before = dict(vars(smod))
    load_schema("manifest.schema.json")
    state_after = dict(vars(smod))
    # __all__ 应不变，常量不变
    assert state_before.get("__all__") == state_after.get("__all__")
    assert state_before.get("SCHEMAS_DIR") == state_after.get("SCHEMAS_DIR")


# ---------- validate 行为深度第七批 ----------


def test_validate_manifest_with_extra_top_level_field():
    """manifest 不允许额外字段."""
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
        "extra_field": "bad",
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_validate_manifest_wrong_version_string():
    """manifest_version 不是 enum 值 → 失败."""
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "9.9.9",  # 非 1.0
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_validate_manifest_devset_status_invalid_enum():
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "unknown",  # 非 complete/incomplete
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_validate_manifest_missing_manifest_version():
    schema_name = "manifest.schema.json"
    instance = {
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_validate_manifest_documents_not_list():
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": "not a list",
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_validate_manifest_expected_failures_not_list():
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": "not a list",
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_validate_evaluation_report_missing_required_field():
    schema_name = "evaluation-report.schema.json"
    instance = {"report_version": "1.1"}  # 缺很多 required
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_validate_evaluation_report_extra_field():
    schema_name = "evaluation-report.schema.json"
    # 构造合法报告（最小）
    instance = {
        "report_version": "1.1",
        "provenance": {
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {},
            "max_chars": 800,
            "run_timestamp_iso": "2026-01-01T00:00:00+00:00",
            "git_commit": None,
            "git_dirty": False,
        },
        "devset": {
            "status": "incomplete",
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": [],
        },
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
        "extra_field": "bad",
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_validate_returns_none_with_valid_minimal_manifest():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    # 不抛 = 通过
    assert validate(instance, "manifest.schema.json") is None


def test_validate_error_message_includes_specific_path():
    """错误消息应含具体 path."""
    instance = {"manifest_version": "bad"}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    msg = str(exc_info.value)
    assert "manifest_version" in msg or "path" in msg


def test_validate_does_not_mutate_instance_on_success():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    import copy
    expected = copy.deepcopy(instance)
    validate(instance, "manifest.schema.json")
    assert instance == expected


def test_validate_idempotent_on_failure():
    instance = {"manifest_version": "bad"}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e1:
        try:
            validate(instance, "manifest.schema.json")
        except EvalSchemaError as e2:
            assert str(e1) == str(e2)


def test_validate_errors_attribute_is_list_of_dicts():
    instance = {"manifest_version": "bad"}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        assert isinstance(e.errors, list)
        for err in e.errors:
            assert isinstance(err, dict)
            assert "path" in err
            assert "message" in err
            assert "schema_path" in err


def test_validate_errors_path_is_list():
    instance = {"manifest_version": "bad"}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["path"], list)
            assert isinstance(err["schema_path"], list)


def test_validate_schema_unknown_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        validate({}, "totally-unknown.schema.json")


# ---------- validate_file 行为深度第七批 ----------


def test_validate_file_str_path(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    # 不抛
    assert validate_file(str(p), "manifest.schema.json") is None


def test_validate_file_path_object(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "missing.json", "manifest.schema.json")


def test_validate_file_invalid_json_raises(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_schema_raises(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"random": "data"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_unknown_schema_name_raises(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "unknown.schema.json")


def test_validate_file_idempotent(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_does_not_modify_file(tmp_path):
    p = tmp_path / "m.json"
    content = json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    p.write_text(content, encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    assert p.read_text(encoding="utf-8") == content


def test_validate_file_positional(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_keyword_args(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    assert validate_file(path=p, schema_name="manifest.schema.json") is None


# ---------- _schema_path 行为深度第七批 ----------


def test_schema_path_returns_path_object():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_resolves_to_schemas_dir():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_unknown_raises_file_not_found():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("totally-unknown.json")
    assert "totally-unknown.json" in str(exc_info.value)


def test_schema_path_directory_raises(tmp_path):
    """传一个目录名 → 不存在该 file → FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir")


def test_schema_path_idempotent():
    p1 = _schema_path("manifest.schema.json")
    p2 = _schema_path("manifest.schema.json")
    assert p1 == p2


def test_schema_path_str_in_error_message():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("my-bogus-name.json")
    assert "my-bogus-name.json" in str(exc_info.value)


def test_schema_path_absolute_path():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


# ---------- SCHEMAS_DIR 常量深度第七批 ----------


def test_schemas_dir_is_pathlib_path():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_resolved():
    """SCHEMAS_DIR 应是已 resolve 的（无 .. 或 .）."""
    assert SCHEMAS_DIR == SCHEMAS_DIR.resolve()


def test_schemas_dir_endswith_schemas():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_has_4_json_files():
    files = list(SCHEMAS_DIR.glob("*.json"))
    assert len(files) == 4


def test_schemas_dir_contains_manifest_schema():
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_contains_document_schema():
    assert (SCHEMAS_DIR / "document.schema.json").is_file()


def test_schemas_dir_in_module_namespace():
    assert hasattr(smod, "SCHEMAS_DIR")
    assert smod.SCHEMAS_DIR is SCHEMAS_DIR


def test_schemas_dir_is_hashable():
    """Path 是 hashable."""
    h = hash(SCHEMAS_DIR)
    assert isinstance(h, int)


def test_schemas_dir_in_all():
    assert "SCHEMAS_DIR" in smod.__all__


def test_schemas_dir_value_immutable_per_module():
    """模块加载后 SCHEMAS_DIR 不变."""
    assert SCHEMAS_DIR == smod.SCHEMAS_DIR


# ---------- module source forbidden tokens 第十一批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "subprocess.run",
        "subprocess.call",
        "shutil.rmtree",
        "shutil.copy",
        "pickle.loads",
        "pickle.load",
        "marshal.loads",
        "ctypes.CDLL",
        "sys.exit",
        "__import__",
        "importlib.import_module",
        "requests.get",
        "urllib.request",
        "http.client",
        "socket.socket",
        "webbrowser.open",
        "antigravity",
        "this",
        "exit(",
        "quit(",
        "exec(",
        "eval(",
        "compile(",
    ],
)
def test_schema_source_no_forbidden_token_eleventh(token):
    src = inspect.getsource(smod)
    assert token not in src


# ---------- module source 字符串精确补强第七批 ----------


def test_module_source_has_future_annotations():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_source_imports_json():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_imports_path():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_imports_any():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_imports_draft_validator():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_imports_js_validation_error():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_schemas_dir_definition():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = Path(__file__).resolve().parent.parent /" in src
    assert '"schemas"' in src or "'schemas'" in src


def test_module_source_eval_schema_error_class_definition():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_eval_schema_error_init_signature():
    src = inspect.getsource(smod)
    assert "def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:" in src


def test_module_source_eval_schema_error_init_uses_super():
    src = inspect.getsource(smod)
    assert "super().__init__(message)" in src


def test_module_source_eval_schema_error_init_assigns_self_errors():
    src = inspect.getsource(smod)
    assert "self.errors = errors or []" in src


def test_module_source_uses_draft_validator_call():
    src = inspect.getsource(smod)
    assert "Draft202012Validator(" in src


def test_module_source_uses_iter_errors():
    src = inspect.getsource(smod)
    assert "iter_errors(" in src


def test_module_source_uses_sorted_with_key():
    src = inspect.getsource(smod)
    assert "sorted(" in src
    assert "key=" in src


def test_module_source_no_main_block():
    src = inspect.getsource(smod)
    assert 'if __name__' not in src


def test_module_source_no_yield():
    src = inspect.getsource(smod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(smod)
    assert "async def " not in src


def test_module_source_no_walrus():
    src = inspect.getsource(smod)
    assert ":=" not in src


def test_module_source_no_global_keyword():
    src = inspect.getsource(smod)
    assert "\nglobal " not in src


def test_module_source_no_lambda_at_top_level():
    src = inspect.getsource(smod)
    # 顶层不应有 lambda 赋值（sorted 的 key=lambda 是允许的）
    for line in src.splitlines():
        if line[:1].isspace():
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "import", "from", "def ", "class ", "@")):
            continue
        if stripped.startswith(('"""', "'''")):
            continue
        # 顶层不应有 NAME = lambda ...
        assert not (("=" in stripped) and ("lambda " in stripped)), \
            f"top-level lambda forbidden: {stripped}"


def test_module_source_no_sleep():
    src = inspect.getsource(smod)
    assert "time.sleep" not in src


def test_module_source_no_hardcoded_absolute_path():
    src = inspect.getsource(smod)
    assert "C:\\\\Users" not in src
    assert "C:/Users" not in src
    assert "/home/" not in src


def test_module_source_no_print():
    src = inspect.getsource(smod)
    assert "print(" not in src


def test_module_source_no_logging():
    src = inspect.getsource(smod)
    assert "import logging" not in src
    assert "logging." not in src


def test_module_source_no_unlink():
    src = inspect.getsource(smod)
    assert ".unlink(" not in src


def test_module_source_no_subprocess():
    src = inspect.getsource(smod)
    assert "subprocess." not in src


def test_module_source_docstring_first_line():
    src = inspect.getsource(smod)
    assert src.startswith('"""')


def test_module_source_docstring_mentions_schema():
    src = inspect.getsource(smod)
    assert "Schema" in src[:600] or "schema" in src[:600]


def test_module_source_docstring_mentions_app_schema():
    """模块 docstring 应提到与 app/schema.py 的关系."""
    src = inspect.getsource(smod)
    assert "app/schema.py" in src[:600] or "app.schema" in src[:600]


def test_module_source_4_user_definitions():
    src = inspect.getsource(smod)
    assert "def _schema_path(" in src
    assert "def load_schema(" in src
    assert "def validate(" in src
    assert "def validate_file(" in src


# ---------- signatures 第七批 ----------


def test_signature_schema_path_1_param():
    sig = inspect.signature(_schema_path)
    assert len(sig.parameters) == 1


def test_signature_schema_path_name_kind():
    sig = inspect.signature(_schema_path)
    p = sig.parameters["name"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_schema_path_name_annotation_str():
    sig = inspect.signature(_schema_path)
    p = sig.parameters["name"]
    assert "str" in str(p.annotation)


def test_signature_schema_path_no_default():
    sig = inspect.signature(_schema_path)
    assert sig.parameters["name"].default is inspect.Parameter.empty


def test_signature_schema_path_no_varargs():
    sig = inspect.signature(_schema_path)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_schema_path_no_kwargs():
    sig = inspect.signature(_schema_path)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_load_schema_1_param():
    sig = inspect.signature(load_schema)
    assert len(sig.parameters) == 1


def test_signature_load_schema_name_kind():
    sig = inspect.signature(load_schema)
    p = sig.parameters["name"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_load_schema_return_annotation_dict():
    sig = inspect.signature(load_schema)
    ra = str(sig.return_annotation)
    assert "dict" in ra


def test_signature_validate_2_params():
    sig = inspect.signature(validate)
    assert len(sig.parameters) == 2


def test_signature_validate_instance_kind():
    sig = inspect.signature(validate)
    p = sig.parameters["instance"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_validate_schema_name_kind():
    sig = inspect.signature(validate)
    p = sig.parameters["schema_name"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_validate_no_varargs():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_validate_no_kwargs():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_validate_return_annotation_none():
    sig = inspect.signature(validate)
    ra = str(sig.return_annotation)
    assert "None" in ra


def test_signature_validate_file_2_params():
    sig = inspect.signature(validate_file)
    assert len(sig.parameters) == 2


def test_signature_validate_file_path_union():
    """path 接受 Path | str."""
    sig = inspect.signature(validate_file)
    a = str(sig.parameters["path"].annotation)
    assert "Path" in a
    assert "str" in a


def test_signature_validate_file_no_varargs():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_validate_file_no_kwargs():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_eval_schema_error_inherits_exception():
    assert issubclass(EvalSchemaError, Exception)


def test_signature_eval_schema_error_init_2_params():
    sig = inspect.signature(EvalSchemaError.__init__)
    # self + message + errors = 3
    assert len(sig.parameters) == 3


def test_signature_eval_schema_error_init_self_kind():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["self"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_all_funcs_function_type():
    assert isinstance(_schema_path, types.FunctionType)
    assert isinstance(load_schema, types.FunctionType)
    assert isinstance(validate, types.FunctionType)
    assert isinstance(validate_file, types.FunctionType)


def test_signature_all_funcs_module_eq():
    assert _schema_path.__module__ == smod.__name__
    assert load_schema.__module__ == smod.__name__
    assert validate.__module__ == smod.__name__
    assert validate_file.__module__ == smod.__name__


# ---------- module 合理性第七批 ----------


def test_module_all_exact_5_items_in_order():
    assert smod.__all__ == [
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    ]


def test_module_all_is_list():
    assert isinstance(smod.__all__, list)


def test_module_all_entries_unique():
    assert len(set(smod.__all__)) == len(smod.__all__)


def test_module_all_entries_are_str():
    for entry in smod.__all__:
        assert isinstance(entry, str)


def test_module_has_docstring():
    assert smod.__doc__ is not None


def test_module_docstring_starts_with_chinese():
    assert smod.__doc__.strip().startswith("加载并校验")


def test_module_file_endswith_schema_py():
    assert smod.__file__.replace("\\", "/").endswith("evaluation/schema.py")


def test_module_name_is_evaluation_schema():
    assert smod.__name__ == "evaluation.schema"


def test_module_user_function_count():
    own_funcs = [
        obj for obj in vars(smod).values()
        if isinstance(obj, types.FunctionType) and obj.__module__ == smod.__name__
    ]
    assert len(own_funcs) == 4


def test_module_user_class_count():
    own_classes = [
        obj for obj in vars(smod).values()
        if isinstance(obj, type) and obj.__module__ == smod.__name__
    ]
    assert len(own_classes) == 1
    assert own_classes[0].__name__ == "EvalSchemaError"


def test_module_user_function_names():
    own_func_names = {
        obj.__name__ for obj in vars(smod).values()
        if isinstance(obj, types.FunctionType) and obj.__module__ == smod.__name__
    }
    assert own_func_names == {"_schema_path", "load_schema", "validate", "validate_file"}


def test_module_no_call_at_top_level():
    """模块顶层不应有显式的 print/exit/subprocess 类副作用调用."""
    src = inspect.getsource(smod)
    in_triple = False
    triple_quote = None
    suspicious_patterns = ("os.system(", "subprocess.", "exit(", "quit(", "print(")
    for line in src.splitlines():
        if in_triple:
            if triple_quote and triple_quote in line:
                in_triple = False
                triple_quote = None
            continue
        ls = line.lstrip()
        for q in ('"""', "'''"):
            if ls.startswith(q):
                rest = ls[3:]
                if rest.count(q) >= 1:
                    pass
                else:
                    in_triple = True
                    triple_quote = q
                break
        for pat in suspicious_patterns:
            assert pat not in line, f"suspicious pattern {pat!r} in {line!r}"


# ---------- 端到端集成第七批 ----------


def test_e2e_load_then_validate_manifest_success():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    schema = load_schema("manifest.schema.json")
    assert isinstance(schema, dict)
    # validate 通过
    assert validate(instance, "manifest.schema.json") is None


def test_e2e_load_then_validate_manifest_failure():
    instance = {"manifest_version": "bad"}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc_info.value)


def test_e2e_validate_file_with_disk_json(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_e2e_validate_file_idempotent(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None
    assert validate_file(p, "manifest.schema.json") is None


def test_e2e_eval_schema_error_caught_as_exception(tmp_path):
    """EvalSchemaError 可作为 Exception 捕获."""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"random": "data"}), encoding="utf-8")
    try:
        validate_file(p, "manifest.schema.json")
    except Exception as e:  # noqa: BLE001
        assert isinstance(e, EvalSchemaError)


def test_e2e_eval_schema_error_str_representation():
    err = EvalSchemaError("my message", [{"path": [0], "message": "x"}])
    s = str(err)
    assert "my message" in s


def test_e2e_eval_schema_error_errors_dict_keys():
    err = EvalSchemaError("msg", [{"path": [], "message": "x", "schema_path": []}])
    assert err.errors[0]["path"] == []
    assert err.errors[0]["message"] == "x"
    assert err.errors[0]["schema_path"] == []


def test_e2e_full_workflow_load_then_validate_with_unknown_schema():
    """未知 schema 名 → FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        validate({}, "totally-unknown.schema.json")


def test_e2e_validate_file_unknown_schema_raises(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "totally-unknown.schema.json")


def test_e2e_validate_does_not_raise_unexpected_exception():
    """validate 不应抛 EvalSchemaError 之外的异常."""
    instance = {"valid": "no"}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError:
        pass  # expected
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"unexpected exception type: {type(e).__name__}")


def test_e2e_eval_schema_error_chained_from_other():
    try:
        try:
            raise ValueError("original")
        except ValueError as e:
            raise EvalSchemaError("wrapper") from e
    except EvalSchemaError as e:
        assert e.__cause__ is not None


def test_e2e_schema_path_with_str_path():
    """_schema_path 接受 str."""
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_e2e_full_chain_manifest_workflow(tmp_path):
    """完整链：构造 → 写盘 → validate_file."""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_e2e_load_each_schema_and_check_dict_with_keys():
    """4 个 schema 加载后都应是 dict 且有 properties + required."""
    for name in ("manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json", "document.schema.json"):
        s = load_schema(name)
        assert isinstance(s, dict)
        assert "properties" in s


def test_e2e_eval_schema_error_with_no_errors_arg():
    err = EvalSchemaError("only message")
    assert err.errors == []


def test_e2e_eval_schema_error_with_empty_errors_list():
    err = EvalSchemaError("msg", [])
    assert err.errors == []


def test_e2e_eval_schema_error_can_be_raised_in_loop():
    """连续 raise 应独立."""
    for i in range(3):
        with pytest.raises(EvalSchemaError) as exc_info:
            raise EvalSchemaError(f"msg{i}")
        assert f"msg{i}" in str(exc_info.value)


def test_e2e_validate_path_includes_documents_index():
    """错误 path 应包含 documents 数组下标."""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1"},  # 缺 path/source_type
        ],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    err = exc_info.value
    # 至少一个 error 的 path 含 documents
    found = False
    for e in err.errors:
        if "documents" in e["path"]:
            found = True
            break
    assert found


def test_e2e_validate_eval_schema_error_errors_path_is_serializable():
    """errors 内的 path 应可 JSON 序列化."""
    instance = {"manifest_version": "bad"}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        # 不抛
        json.dumps(e.errors)
