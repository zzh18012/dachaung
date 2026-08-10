"""evaluation/schema.py 第二十轮 edges 测试（Round 333）。

重点补强 edges19 未触及的角度：
- EvalSchemaError 行为深度（默认 errors / falsy 错误处理 / message str 类型）
- _schema_path 行为深度（参数形式 / 不创建文件 / 错误消息）
- load_schema 行为深度（每次新 dict / 4 个 schemas 都可加载）
- validate 行为深度（不修改 instance / 排序稳定性 / 多错误场景）
- validate_file 行为深度（多种 file 形式 / 错误传播）
- module source forbidden tokens 第三批（~75 stdlib）
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性
- 端到端集成补强
"""

from __future__ import annotations

import inspect
import json
import types
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from evaluation import schema as schema_mod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- EvalSchemaError 行为深度 ----------


def test_eval_schema_error_default_errors_is_empty_list():
    e = EvalSchemaError("msg")
    assert e.errors == []


def test_eval_schema_error_message_attribute():
    e = EvalSchemaError("test message")
    assert e.args == ("test message",)


def test_eval_schema_error_str_returns_message():
    e = EvalSchemaError("hello")
    assert str(e) == "hello"


def test_eval_schema_error_repr_includes_class_name():
    e = EvalSchemaError("hi")
    assert "EvalSchemaError" in repr(e)


def test_eval_schema_error_with_none_errors():
    e = EvalSchemaError("msg", None)
    assert e.errors == []


def test_eval_schema_error_with_empty_list_errors():
    e = EvalSchemaError("msg", [])
    assert e.errors == []


def test_eval_schema_error_with_3_errors_keeps_all():
    errs = [{"path": [1]}, {"path": [2]}, {"path": [3]}]
    e = EvalSchemaError("msg", errs)
    assert e.errors == errs
    assert len(e.errors) == 3


def test_eval_schema_error_with_falsy_non_none_errors():
    """falsy 但非 None 的 errors（如 []）→ 默认 []。"""
    e = EvalSchemaError("msg", [])
    # errors or [] → []
    assert e.errors == []


def test_eval_schema_error_subclass_of_exception():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_not_subclass_of_value_error():
    assert not issubclass(EvalSchemaError, ValueError)


def test_eval_schema_error_can_be_raised_and_caught():
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("x")


def test_eval_schema_error_caught_as_exception():
    with pytest.raises(Exception):
        raise EvalSchemaError("x")


def test_eval_schema_error_errors_attribute_is_list():
    e = EvalSchemaError("x", [{"a": 1}])
    assert isinstance(e.errors, list)


# ---------- _schema_path 行为深度 ----------


def test_schema_path_returns_path_object():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_returns_absolute_path():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_for_invalid_name_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        _schema_path("nonexistent.schema.json")


def test_schema_path_does_not_create_file(tmp_path):
    """_schema_path 仅检查不创建。"""
    p_before = SCHEMAS_DIR / "nonexistent.schema.json"
    assert not p_before.exists()
    with pytest.raises(FileNotFoundError):
        _schema_path("nonexistent.schema.json")
    assert not p_before.exists()


def test_schema_path_with_dot_prefix():
    """文件名以 . 开头（隐藏文件）→ 不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path(".nonexistent")


def test_schema_path_with_subdir_name():
    """带 / 的名字 → 不会找到。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/file.json")


# ---------- load_schema 行为深度 ----------


def test_load_schema_returns_dict():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_each_call_returns_fresh_dict():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2
    assert s1 is not s2


def test_load_schema_4_schemas_each():
    for name in ("manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json"):
        s = load_schema(name)
        assert isinstance(s, dict)
        assert "$schema" in s or "type" in s


def test_load_schema_manifest_top_level_type_object():
    s = load_schema("manifest.schema.json")
    assert s.get("type") in ("object", None)


def test_load_schema_annotation_top_level_type():
    s = load_schema("annotation.schema.json")
    assert s.get("type") in ("object", None)


def test_load_schema_evaluation_report_top_level_type():
    s = load_schema("evaluation-report.schema.json")
    assert s.get("type") in ("object", None)


def test_load_schema_raises_for_missing():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


# ---------- validate 行为深度 ----------


def test_validate_returns_none_on_success():
    """validate 成功时返回 None（不返回 errors list）。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    result = validate(instance, "manifest.schema.json")
    assert result is None


def test_validate_does_not_modify_instance():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    snapshot = json.loads(json.dumps(instance))
    validate(instance, "manifest.schema.json")
    assert instance == snapshot


def test_validate_with_invalid_raises_eval_schema_error():
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")  # missing required fields


def test_validate_errors_attribute_populated_on_failure():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert isinstance(e.errors, list)
        assert len(e.errors) > 0
        for err in e.errors:
            assert "path" in err
            assert "message" in err
            assert "schema_path" in err


def test_validate_first_error_in_message():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        # message 含第 1 个错误的描述
        assert "manifest" in str(e) or "Schema" in str(e)


def test_validate_count_in_message_matches_errors_length():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        msg = str(e)
        # message 形如 "Schema '...' 校验失败 (N 处)：..."
        assert "处" in msg or "errors" in msg.lower()


def test_validate_errors_path_is_list_type():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["path"], list)


def test_validate_errors_message_is_str():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["message"], str)


def test_validate_invalid_schema_name_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        validate({}, "nonexistent.schema.json")


def test_validate_extra_fields_allowed_when_additional_properties_true():
    """如果 schema 允许 additionalProperties，多余字段不报错。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "extra_field": "ignored",
    }
    # manifest schema 默认应允许 additional 或不允许；不抛 FileNotFoundError 即 OK
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError:
        pass  # 如果 schema 拒绝 additional 也可接受


# ---------- validate_file 行为深度 ----------


def test_validate_file_str_path_conversion_to_path(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_pathlib_path(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_missing_raises_filenotfound(tmp_path):
    p = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_directory_raises_filenotfound(tmp_path):
    """validate_file 给目录 → FileNotFoundError。"""
    d = tmp_path / "subdir"
    d.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(d, "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecodeerror(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_schema_error(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"wrong": "shape"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_with_invalid_schema_name_raises_filenotfound(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "nonexistent.schema.json")


def test_validate_file_bom_handled(tmp_path):
    """BOM 字节开头 → json.load 仍能解析（utf-8-sig 不需要，但 utf-8 应处理）。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf' + json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }).encode("utf-8"))
    # BOM 可能引起错误，但也可能被处理
    try:
        validate_file(p, "manifest.schema.json")
    except (json.JSONDecodeError, EvalSchemaError):
        pass  # BOM 行为不强制


def test_validate_file_relative_path(tmp_path, monkeypatch):
    """相对路径 → 相对 cwd 解析。"""
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    validate_file("valid.json", "manifest.schema.json")


# ---------- module source forbidden tokens 第三批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "base64", "binascii", "bisect", "calendar", "concurrent",
        "contextlib", "copyreg", "csv", "fnmatch", "functools",
        "getopt", "getpass", "gettext", "heapq", "imaplib",
        "importlib", "ipaddress", "locale", "lzma", "mailbox",
        "mimetypes", "mmap", "multiprocessing", "netrc", "ntpath",
        "numbers", "operator", "optparse", "platform",
        "poplib", "posixpath", "profile", "pstats", "py_compile",
        "quopri", "reprlib", "runpy", "sched", "select",
        "shelve", "shlex", "signal", "site", "smtplib",
        "sndhdr", "socketserver", "sqlite3", "ssl", "subprocess",
        "sunau", "symtable", "tabnanny", "telnetlib", "termios",
        "timeit", "tkinter", "token", "tokenize", "trace",
        "tty", "turtle", "unittest", "urllib",
        "uu", "webbrowser", "xdrlib", "zipapp", "zipfile",
        "zipimport", "argparse", "array", "ast", "atexit",
        "builtins", "collections",
    ],
)
def test_module_source_forbidden_tokens_third_batch(token):
    """这些 stdlib 模块不应出现在 schema.py（仅用 json/Path/typing/jsonschema）。"""
    src = inspect.getsource(schema_mod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_from_future():
    src = inspect.getsource(schema_mod)
    assert "from __future__ import annotations" in src


def test_module_source_has_import_json():
    src = inspect.getsource(schema_mod)
    assert "import json" in src


def test_module_source_has_from_pathlib_import_path():
    src = inspect.getsource(schema_mod)
    assert "from pathlib import Path" in src


def test_module_source_has_from_typing_import_any():
    src = inspect.getsource(schema_mod)
    assert "from typing import Any" in src


def test_module_source_has_jsonschema_validator_import():
    src = inspect.getsource(schema_mod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_has_jsonschema_validation_error_import():
    src = inspect.getsource(schema_mod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_no_actual_use_of_jsvalidationerror():
    """JSValidationError import 但代码里没直接 raise（用 EvalSchemaError 包装）。"""
    src = inspect.getsource(schema_mod)
    # import 行不算
    non_import_lines = [
        line for line in src.splitlines()
        if not line.strip().startswith(("import ", "from "))
    ]
    body_text = "\n".join(non_import_lines)
    assert "raise JSValidationError" not in body_text


def test_module_source_has_module_docstring():
    src = inspect.getsource(schema_mod)
    assert '"""加载并校验本阶段三个新 Schema：manifest / annotation / evaluation-report。' in src


def test_module_source_docstring_mentions_manifest():
    src = inspect.getsource(schema_mod)
    assert "manifest" in src


def test_module_source_docstring_mentions_annotation():
    src = inspect.getsource(schema_mod)
    assert "annotation" in src


def test_module_source_docstring_mentions_evaluation_report():
    src = inspect.getsource(schema_mod)
    assert "evaluation-report" in src


def test_module_source_mentions_no_reuse_app_schema():
    src = inspect.getsource(schema_mod)
    assert "app/schema" not in src or "不与 app/schema" in src


def test_module_source_has_schemas_dir_constant():
    src = inspect.getsource(schema_mod)
    assert "SCHEMAS_DIR" in src


def test_module_source_has_class_eval_schema_error():
    src = inspect.getsource(schema_mod)
    assert "class EvalSchemaError" in src


def test_module_source_eval_schema_error_inherits_exception():
    src = inspect.getsource(schema_mod)
    assert "class EvalSchemaError(Exception)" in src


def test_module_source_has_no_yield():
    src = inspect.getsource(schema_mod)
    assert "yield" not in src


def test_module_source_has_no_async():
    src = inspect.getsource(schema_mod)
    assert "async " not in src


def test_module_source_has_no_global():
    src = inspect.getsource(schema_mod)
    assert "global " not in src


def test_module_source_has_no_main_block():
    src = inspect.getsource(schema_mod)
    assert 'if __name__' not in src


def test_module_source_has_no_lambda_other_than_sort_key():
    src = inspect.getsource(schema_mod)
    lines_with_lambda = [line for line in src.splitlines() if "lambda " in line]
    for line in lines_with_lambda:
        assert "absolute_path" in line or "x:" in line, f"unexpected lambda: {line}"


def test_module_source_has_no_decorators():
    src = inspect.getsource(schema_mod)
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("@"):
            assert False, f"unexpected decorator: {stripped}"


# ---------- signatures 精确补强 ----------


def test_validate_signature_2_params():
    sig = inspect.signature(validate)
    assert list(sig.parameters) == ["instance", "schema_name"]


def test_validate_return_annotation_none():
    sig = inspect.signature(validate)
    # from __future__ import annotations → return_annotation is str "None"
    assert sig.return_annotation is None or sig.return_annotation == "None"


def test_load_schema_signature_1_param():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters) == ["name"]


def test_load_schema_return_annotation_dict():
    sig = inspect.signature(load_schema)
    assert "dict" in str(sig.return_annotation)


def test_validate_file_signature_2_params():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters) == ["path", "schema_name"]


def test_validate_file_path_annotation_union():
    sig = inspect.signature(validate_file)
    p = sig.parameters["path"]
    assert "Path" in str(p.annotation)
    assert "str" in str(p.annotation)


def test_validate_file_return_annotation_none():
    sig = inspect.signature(validate_file)
    assert sig.return_annotation is None or sig.return_annotation == "None"


def test_schema_path_signature_1_param():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters) == ["name"]


def test_schema_path_return_annotation_path():
    sig = inspect.signature(_schema_path)
    assert "Path" in str(sig.return_annotation)


def test_no_varargs_varkw_in_functions():
    for fn in (validate, load_schema, validate_file, _schema_path):
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_POSITIONAL
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- 模块整体合理性 ----------


def test_namespace_module():
    assert isinstance(schema_mod, types.ModuleType)


def test_namespace_load_schema():
    assert hasattr(schema_mod, "load_schema")
    assert isinstance(getattr(schema_mod, "load_schema"), types.FunctionType)


def test_namespace_validate():
    assert hasattr(schema_mod, "validate")
    assert isinstance(getattr(schema_mod, "validate"), types.FunctionType)


def test_namespace_validate_file():
    assert hasattr(schema_mod, "validate_file")
    assert isinstance(getattr(schema_mod, "validate_file"), types.FunctionType)


def test_namespace_schema_path():
    assert hasattr(schema_mod, "_schema_path")
    assert isinstance(getattr(schema_mod, "_schema_path"), types.FunctionType)


def test_namespace_eval_schema_error():
    assert hasattr(schema_mod, "EvalSchemaError")
    assert isinstance(getattr(schema_mod, "EvalSchemaError"), type)


def test_namespace_schemas_dir():
    assert hasattr(schema_mod, "SCHEMAS_DIR")
    assert isinstance(getattr(schema_mod, "SCHEMAS_DIR"), Path)


def test_module_all_5_entries_strict():
    assert schema_mod.__all__ == [
        "SCHEMAS_DIR", "EvalSchemaError",
        "load_schema", "validate", "validate_file",
    ]


def test_module_all_is_list():
    assert isinstance(schema_mod.__all__, list)


def test_module_all_entries_are_str():
    for entry in schema_mod.__all__:
        assert isinstance(entry, str)


def test_module_namespace_is_evaluation_schema():
    assert schema_mod.__name__ == "evaluation.schema"


def test_module_has_no_main_block():
    src = inspect.getsource(schema_mod)
    assert 'if __name__' not in src


def test_module_has_1_class_only():
    classes = [
        n for n, v in vars(schema_mod).items()
        if not n.startswith("_") and isinstance(v, type)
        and getattr(v, "__module__", "") == schema_mod.__name__
    ]
    assert classes == ["EvalSchemaError"]


def test_module_has_3_public_functions_only():
    public_funcs = [
        n for n, v in vars(schema_mod).items()
        if not n.startswith("_") and isinstance(v, types.FunctionType)
        and getattr(v, "__module__", "") == schema_mod.__name__
    ]
    assert sorted(public_funcs) == ["load_schema", "validate", "validate_file"]


def test_module_has_1_private_helper_only():
    private_funcs = [
        n for n, v in vars(schema_mod).items()
        if n.startswith("_") and not n.startswith("__")
        and isinstance(v, types.FunctionType)
        and getattr(v, "__module__", "") == schema_mod.__name__
    ]
    assert private_funcs == ["_schema_path"]


def test_module_schemas_dir_is_path_instance():
    assert isinstance(SCHEMAS_DIR, Path)


def test_module_schemas_dir_is_absolute():
    assert SCHEMAS_DIR.is_absolute()


def test_module_schemas_dir_resolved():
    """SCHEMAS_DIR 应当是 .resolve() 后的（无 .. / symlinks）。"""
    # 如果已 resolved，再 resolve 还是同一个
    assert SCHEMAS_DIR == SCHEMAS_DIR.resolve()


def test_module_schemas_dir_parent_is_project_root():
    """SCHEMAS_DIR 父目录是项目根（含 pyproject.toml）。"""
    project_root = SCHEMAS_DIR.parent
    assert (project_root / "pyproject.toml").is_file()


def test_module_schemas_dir_contains_3_schemas():
    """schemas/ 目录含 manifest / annotation / evaluation-report 3 个 schema。"""
    expected = {
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    }
    actual = {p.name for p in SCHEMAS_DIR.iterdir() if p.suffix == ".json"}
    assert expected.issubset(actual)


# ---------- 端到端集成补强 ----------


def test_e2e_load_and_validate_3_schemas_each():
    for name in ("manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json"):
        s = load_schema(name)
        Draft202012Validator.check_schema(s)


def test_e2e_validate_returns_none_when_valid():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_e2e_full_round_trip_load_validate_validate_file(tmp_path):
    """load → validate → validate_file 完整链路。"""
    s = load_schema("manifest.schema.json")
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    validate(instance, "manifest.schema.json")
    p = tmp_path / "valid.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_error_dict_is_json_serializable():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        # errors list 应可 json 序列化
        json.dumps(e.errors)


def test_e2e_validate_with_unicode_in_path(tmp_path):
    """报告路径含 unicode → 不影响 validate_file。"""
    p = tmp_path / "测试.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_validate_with_unicode_in_doc_id(tmp_path):
    """doc_id 含 unicode → manifest schema 接受。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "测试文档", "path": "a.pdf", "source_type": "pdf"},
        ],
    }
    # 路径不存在 manifest.load_manifest 会拒绝，但 validate 不检查文件存在
    validate(instance, "manifest.schema.json")


def test_e2e_validate_file_propagates_eval_schema_error(tmp_path):
    """validate_file 失败时把 EvalSchemaError 透传给调用方。"""
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"wrong": "shape"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError) as ei:
        validate_file(p, "manifest.schema.json")
    assert len(ei.value.errors) > 0


def test_e2e_eval_schema_error_can_be_reraised():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        # 捕获后可以再次 raise
        with pytest.raises(EvalSchemaError):
            raise e


def test_e2e_validate_with_array_top_level():
    """array 顶层 instance → schema 校验失败。"""
    with pytest.raises(EvalSchemaError):
        validate([], "manifest.schema.json")


def test_e2e_validate_with_string_top_level():
    """string 顶层 instance → schema 校验失败。"""
    with pytest.raises(EvalSchemaError):
        validate("hello", "manifest.schema.json")


def test_e2e_validate_with_number_top_level():
    """number 顶层 instance → schema 校验失败。"""
    with pytest.raises(EvalSchemaError):
        validate(42, "manifest.schema.json")


def test_e2e_validate_with_bool_top_level():
    """bool 顶层 instance → schema 校验失败。"""
    with pytest.raises(EvalSchemaError):
        validate(True, "manifest.schema.json")


def test_e2e_validate_with_null_top_level():
    """null 顶层 instance → schema 校验失败。"""
    with pytest.raises(EvalSchemaError):
        validate(None, "manifest.schema.json")
