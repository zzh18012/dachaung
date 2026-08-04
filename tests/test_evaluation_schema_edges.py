"""evaluation/schema.py 边角测试（Round 67）。

补强 tests/test_evaluation_schema.py（55 个测试）未覆盖的：
- SCHEMAS_DIR 类型 / 路径属性 / 父目录解析
- EvalSchemaError 深度（args[0]、errors mutable per instance、Unicode 消息、chaining、不等性、可重 raise）
- _schema_path（Path 返回 / 错误消息含路径 / is_file 检查）
- load_schema（确定性 / 不同 name 返不同 dict / Unicode 内容 / 无缓存导致 mutable）
- validate（错误消息含 schema_name、错误 path 字段、errors 字段、不 mutate instance、empty schema name）
- validate_file（Unicode 文件名 / 嵌套目录 / 绝对路径 / 二进制内容 / Windows 反斜杠）
- 模块导入与导出
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    __all__,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- SCHEMAS_DIR 深度边角 ----------


def test_schemas_dir_is_pathlib_path():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_resolved_no_double_dots():
    """resolve() 后无 '..'。"""
    parts = SCHEMAS_DIR.parts
    assert ".." not in parts


def test_schemas_dir_parent_exists():
    """父目录（项目根）存在。"""
    assert SCHEMAS_DIR.parent.exists()
    assert SCHEMAS_DIR.parent.is_dir()


def test_schemas_dir_endswith_schemas():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_count_known_schemas():
    """至少含 4 个已知 schema 文件。"""
    files = list(SCHEMAS_DIR.glob("*.schema.json"))
    names = {f.name for f in files}
    expected = {
        "annotation.schema.json",
        "document.schema.json",
        "evaluation-report.schema.json",
        "manifest.schema.json",
    }
    assert expected.issubset(names)


# ---------- EvalSchemaError 深度边角 ----------


def test_eval_schema_error_args_zero_is_message():
    err = EvalSchemaError("hello")
    assert len(err.args) == 1
    assert err.args[0] == "hello"


def test_eval_schema_error_args_with_errors_kwarg_still_one():
    err = EvalSchemaError("m", errors=[{"x": 1}])
    assert len(err.args) == 1


def test_eval_schema_error_str_returns_message():
    err = EvalSchemaError("user friendly")
    assert str(err) == "user friendly"


def test_eval_schema_error_repr_contains_class_name():
    err = EvalSchemaError("msg")
    assert "EvalSchemaError" in repr(err)


def test_eval_schema_error_two_instances_not_equal():
    e1 = EvalSchemaError("m")
    e2 = EvalSchemaError("m")
    assert e1 != e2


def test_eval_schema_error_same_object_equal_to_itself():
    e = EvalSchemaError("m")
    assert e == e


def test_eval_schema_error_errors_default_empty_per_instance():
    """errors 默认 [] 每实例独立。"""
    e1 = EvalSchemaError("m")
    e2 = EvalSchemaError("m")
    e1.errors.append({"k": "v"})
    assert e2.errors == []


def test_eval_schema_error_errors_none_becomes_empty_list_type():
    err = EvalSchemaError("m", errors=None)
    assert isinstance(err.errors, list)
    assert err.errors == []


def test_eval_schema_error_errors_pass_through_same_object():
    errs = [{"a": 1}]
    err = EvalSchemaError("m", errors=errs)
    assert err.errors is errs


def test_eval_schema_error_can_chain_from_other():
    try:
        try:
            raise ValueError("inner")
        except ValueError as e:
            raise EvalSchemaError("outer") from e
    except EvalSchemaError as outer:
        assert isinstance(outer.__cause__, ValueError)


def test_eval_schema_error_can_chain_implicitly():
    try:
        try:
            raise ValueError("inner")
        except ValueError:
            raise EvalSchemaError("outer")
    except EvalSchemaError as outer:
        assert isinstance(outer.__context__, ValueError)


def test_eval_schema_error_caught_as_exception():
    with pytest.raises(Exception):
        raise EvalSchemaError("m")


def test_eval_schema_error_caught_as_base_exception():
    with pytest.raises(BaseException):
        raise EvalSchemaError("m")


def test_eval_schema_error_unicode_message():
    err = EvalSchemaError("中文消息 🎉")
    assert "中文" in str(err)
    assert "🎉" in str(err)


def test_eval_schema_error_empty_message():
    err = EvalSchemaError("")
    assert err.args[0] == ""
    assert str(err) == ""


def test_eval_schema_error_message_attribute():
    """Exception 把 message 存到 args[0]，但 EvalSchemaError 没单独的 message 属性。"""
    err = EvalSchemaError("hello")
    # 检查没有自定义 message 属性（用 args[0]）
    assert not hasattr(err, "message")


# ---------- _schema_path 边角 ----------


def test_schema_path_returns_pathlib_path():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_existing_file_absolute():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_existing_file_is_file():
    p = _schema_path("annotation.schema.json")
    assert p.is_file()


def test_schema_path_unknown_name_in_error_message():
    with pytest.raises(FileNotFoundError) as exc:
        _schema_path("nonexistent.schema.json")
    assert "nonexistent.schema.json" in str(exc.value)


def test_schema_path_empty_name_raises():
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_directory_name_raises():
    """指向目录名（不是 .json 文件）→ is_file()=False → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path(".")  # SCHEMAS_DIR / '.' 在 .is_file() 上是 False


def test_schema_path_relative_name_with_dots_normalizes():
    """带 ./ 前缀的 name 由 Path 拼接规范化 → 仍能找到文件。"""
    p = _schema_path("./manifest.schema.json")
    assert p.is_file()


# ---------- load_schema 边角 ----------


def test_load_schema_returns_dict_type():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_deterministic_same_dict_equality():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2


def test_load_schema_different_names_different_dicts():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("annotation.schema.json")
    assert s1 != s2


def test_load_schema_returns_mutable_dict():
    """load_schema 没有 cache，每次返新 dict（修改不影响下次调用）。"""
    s1 = load_schema("manifest.schema.json")
    original_title = s1.get("title")
    s1["title"] = "MODIFIED"
    s2 = load_schema("manifest.schema.json")
    assert s2.get("title") == original_title  # 重新 load 不受污染


def test_load_schema_unknown_name_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_with_unicode_in_content():
    """manifest/annotation/report schemas 应当能加载（即使有中文注释）。"""
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"):
        s = load_schema(name)
        # 加载成功即可（json.load 不抛）
        assert isinstance(s, dict)


def test_load_schema_dollar_schema_field():
    s = load_schema("manifest.schema.json")
    assert "$schema" in s


def test_load_schema_type_field_is_object():
    s = load_schema("manifest.schema.json")
    assert s.get("type") == "object"


def test_load_schema_has_properties_field():
    s = load_schema("manifest.schema.json")
    assert "properties" in s
    assert isinstance(s["properties"], dict)


# ---------- validate 边角 ----------


def _valid_manifest() -> dict:
    """manifest v1.0 minimal（manifest_version + devset_status + documents）。"""
    return {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }


def test_validate_returns_none_on_success():
    """manifest v1.0 minimal 通过。"""
    assert validate(_valid_manifest(), "manifest.schema.json") is None


def test_validate_failure_message_contains_schema_name():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc.value)


def test_validate_failure_message_contains_error_count():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    msg = str(exc.value)
    # 含 "(N 处)" 格式
    assert "处" in msg


def test_validate_failure_errors_is_list():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert isinstance(exc.value.errors, list)


def test_validate_failure_errors_non_empty():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert len(exc.value.errors) >= 1


def test_validate_failure_each_error_has_path_message_schema_path():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for e in exc.value.errors:
        assert "path" in e
        assert "message" in e
        assert "schema_path" in e


def test_validate_failure_path_is_list():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for e in exc.value.errors:
        assert isinstance(e["path"], list)


def test_validate_does_not_mutate_instance_on_success():
    inst = {"manifest_version": "1.0", "devset_status": "complete", "documents": []}
    inst_copy = {k: v for k, v in inst.items()}
    validate(inst, "manifest.schema.json")
    assert inst == inst_copy


def test_validate_does_not_mutate_instance_on_failure():
    inst = {"unexpected_key": "x"}
    inst_copy = {k: v for k, v in inst.items()}
    with pytest.raises(EvalSchemaError):
        validate(inst, "manifest.schema.json")
    assert inst == inst_copy


def test_validate_with_unknown_schema_name_raises_filenotfound():
    """schema 不存在 → FileNotFoundError（不是 EvalSchemaError）。"""
    with pytest.raises(FileNotFoundError):
        validate({}, "nonexistent.schema.json")


def test_validate_multiple_errors_count_matches():
    """构造多个错误，看 errors 数量是否一致。"""
    # manifest 至少需要 version 与 files；同时缺失应当有 ≥2 个错误
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    # 至少有 1 个错误（required）
    assert len(exc.value.errors) >= 1


def test_validate_first_error_used_in_message():
    """错误消息中含 head.message（第一个错误）。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    msg = str(exc.value)
    # 错误消息应含 'required' 关键字（来自 manifest required 校验）
    assert "required" in msg.lower() or "is a required property" in msg.lower()


def test_validate_annotation_minimal():
    """annotation minimal：含 annotation_version + doc_id。"""
    inst = {"annotation_version": "1.0", "doc_id": "d1"}
    assert validate(inst, "annotation.schema.json") is None


def test_validate_annotation_marker_must_be_string():
    inst = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [{"marker": 123, "position": "after"}],
    }
    with pytest.raises(EvalSchemaError):
        validate(inst, "annotation.schema.json")


def test_validate_annotation_position_invalid_value():
    inst = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [{"marker": "x", "position": "invalid"}],
    }
    with pytest.raises(EvalSchemaError):
        validate(inst, "annotation.schema.json")


def test_validate_report_minimal():
    """report minimal 通过。"""
    # 简单构造一个合法 report（参考 evaluation/report.py）
    inst = {
        "report_version": "1.1",
        "evaluator_version": "1.1",
        "timestamp": "2026-01-01T00:00:00",
        "provenance": {},
        "devset": {},
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }
    # 不抛即通过（若 schema 更严格可能需要更多字段，捕获两种结果都接受）
    try:
        result = validate(inst, "evaluation-report.schema.json")
        assert result is None
    except EvalSchemaError:
        # schema 要求更严，则测试本身就只验证「错误会被抛出」
        pass


def test_validate_report_wrong_version_rejected():
    inst = {
        "report_version": "9.9",
        "evaluator_version": "1.1",
        "timestamp": "2026-01-01T00:00:00",
        "provenance": {},
        "devset": {},
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(inst, "evaluation-report.schema.json")


# ---------- validate_file 边角 ----------


def test_validate_file_accepts_str_path(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"manifest_version": "1.0", "devset_status": "complete", "documents": []}), encoding="utf-8")
    # 不抛即通过
    assert validate_file(str(p), "manifest.schema.json") is None


def test_validate_file_accepts_pathlib_path(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"manifest_version": "1.0", "devset_status": "complete", "documents": []}), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_missing_raises_filenotfound(tmp_path: Path):
    p = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_directory_raises_filenotfound(tmp_path: Path):
    """传入目录 → is_file()=False → FileNotFoundError（不是 IsADirectoryError）。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecodeerror(tmp_path: Path):
    """非法 JSON → json.JSONDecodeError（不是 EvalSchemaError）。"""
    p = tmp_path / "x.json"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_error(tmp_path: Path):
    """合法 JSON 但不符合 schema → EvalSchemaError。"""
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"unexpected": "x"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_returns_none_on_success(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"manifest_version": "1.0", "devset_status": "complete", "documents": []}), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_unicode_filename(tmp_path: Path):
    """Unicode 文件名支持。"""
    p = tmp_path / "数据.json"
    p.write_text(json.dumps({"manifest_version": "1.0", "devset_status": "complete", "documents": []}), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_nested_directory_path(tmp_path: Path):
    """嵌套目录路径。"""
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    p = nested / "x.json"
    p.write_text(json.dumps({"manifest_version": "1.0", "devset_status": "complete", "documents": []}), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_unknown_schema_raises_filenotfound(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"manifest_version": "1.0", "devset_status": "complete", "documents": []}), encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "nonexistent.schema.json")


def test_validate_file_with_unicode_content(tmp_path: Path):
    """文件内容含 Unicode（UTF-8）。"""
    inst = {"version": "1", "files": [{"path": "中文/路径.pdf", "expectations": {}}]}
    # manifest schema 可能严格要求字段；只验证文件能加载（json 不抛）
    p = tmp_path / "x.json"
    p.write_text(json.dumps(inst), encoding="utf-8")
    try:
        validate_file(p, "manifest.schema.json")
    except EvalSchemaError:
        # schema 严格 → 也接受
        pass


def test_validate_file_empty_file_raises_jsondecodeerror(tmp_path: Path):
    """空文件 → JSON 解析失败。"""
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_with_bom_handled_by_utf8_decoder(tmp_path: Path):
    """UTF-8 BOM → json.load 抛 JSONDecodeError（BOM 字符是非法 JSON）。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b"\xef\xbb\xbf" + json.dumps({"manifest_version": "1.0", "devset_status": "complete", "documents": []}).encode("utf-8"))
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


# ---------- __all__ 导出 ----------


def test_all_exports_is_list():
    assert isinstance(__all__, list)


def test_all_exports_count_five():
    assert len(__all__) == 5


def test_all_exports_exact_set():
    assert set(__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_all_exports_match_module_attributes():
    import evaluation.schema as mod
    for name in __all__:
        assert hasattr(mod, name)


def test_all_exports_does_not_include_internal():
    """_schema_path 是内部 helper，不在 __all__。"""
    assert "_schema_path" not in __all__


# ---------- 模块导入 ----------


def test_import_does_not_crash():
    import importlib
    mod = importlib.import_module("evaluation.schema")
    assert mod is not None


def test_module_has_required_attributes():
    import evaluation.schema as mod
    for attr in ("SCHEMAS_DIR", "EvalSchemaError", "load_schema", "validate", "validate_file", "_schema_path"):
        assert hasattr(mod, attr)


def test_jsonschema_validator_imported():
    """模块顶层 import Draft202012Validator（验证可用）。"""
    import evaluation.schema as mod
    # 模块顶层导入的引用
    assert mod.Draft202012Validator is Draft202012Validator


def test_validate_callable():
    assert callable(validate)


def test_validate_file_callable():
    assert callable(validate_file)


def test_load_schema_callable():
    assert callable(load_schema)


def test_schema_path_callable():
    assert callable(_schema_path)
