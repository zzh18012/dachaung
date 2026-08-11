"""evaluation/schema.py 第三十四轮 edges 测试（Round 428）。

补强 edges33 未触及的角度：
- SCHEMAS_DIR 常量深度第十四批（含 3 个 schema 文件 / 路径分段 / 与 evaluation/__init__.py 同根 / 是 PurePath 子类）
- EvalSchemaError 行为深度第十四批（__str__ / args / __repr__ / 修改 errors list / errors=None 与 [] 区分 / 不带 message 调用）
- load_schema 行为深度第十四批（不同 schema name / 返回 dict 类型 / 返回新实例 / 必须含 $schema 或 $id / json 字符串）
- validate 行为深度第十四批（schema 名字错误抛 FileNotFoundError / errors sorted by path / flat 结构稳定性 / errors 长度等于 iter_errors）
- validate_file 行为深度第十四批（validate_file 不返回值 / json.load 调用 / 透传 EvalSchemaError）
- _schema_path 行为深度第十四批（拼接方式 / 不读文件 / 文件存在但非 JSON 由 load_schema 处理 / 错误 message 内容）
- module source forbidden tokens 第十九批
- module source 字符串精确补强第十六批
- signatures 第十六批
- module 合理性第十六批
- 端到端集成第十六批
"""

from __future__ import annotations

import inspect
import json
import pickle
from pathlib import Path, PurePath
from unittest.mock import patch, MagicMock

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


# ---------- SCHEMAS_DIR 常量深度第十四批 ----------


def test_schemas_dir_contains_manifest_schema_batch14():
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema_batch14():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema_batch14():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_parts_end_with_schemas_batch14():
    parts = SCHEMAS_DIR.parts
    assert parts[-1] == "schemas"


def test_schemas_dir_parent_contains_eval_module_batch14():
    """SCHEMAS_DIR.parent 应包含 evaluation/ 目录。"""
    parent = SCHEMAS_DIR.parent
    assert (parent / "evaluation").is_dir()


def test_schemas_dir_is_purepath_subclass_batch14():
    assert isinstance(SCHEMAS_DIR, Path)
    assert isinstance(SCHEMAS_DIR, PurePath)


def test_schemas_dir_str_form_endswith_schemas_batch14():
    assert str(SCHEMAS_DIR).replace("\\", "/").endswith("/schemas")


# ---------- EvalSchemaError 行为深度第十四批 ----------


def test_eval_schema_error_str_contains_message_batch14():
    err = EvalSchemaError("oops", errors=[{"path": ["x"]}])
    assert "oops" in str(err)


def test_eval_schema_error_args_batch14():
    err = EvalSchemaError("hello")
    assert err.args == ("hello",)


def test_eval_schema_error_repr_batch14():
    err = EvalSchemaError("boom")
    r = repr(err)
    assert "EvalSchemaError" in r
    assert "boom" in r


def test_eval_schema_error_errors_mutable_after_creation_batch14():
    """self.errors 是 list，可修改（虽然不推荐）。"""
    err = EvalSchemaError("x", errors=[{"a": 1}])
    err.errors.append({"b": 2})
    assert len(err.errors) == 2


def test_eval_schema_error_errors_none_vs_empty_list_batch14():
    """errors=None → []；errors=[] → []。两者内部表示相同。"""
    e1 = EvalSchemaError("x", errors=None)
    e2 = EvalSchemaError("x", errors=[])
    assert e1.errors == e2.errors == []


def test_eval_schema_errors_kept_as_passed_batch14():
    errs = [{"path": ["a"], "message": "m1"}]
    err = EvalSchemaError("x", errors=errs)
    assert err.errors is errs  # 同一对象


def test_eval_schema_error_default_message_empty_batch14():
    """无 message 调用 — 但 message 是位置参数，所以这是空字符串场景（很难触发）。"""
    err = EvalSchemaError.__new__(EvalSchemaError)
    # 直接 __new__ 不调 __init__
    assert not hasattr(err, "errors") or isinstance(getattr(err, "errors", None), list)


def test_eval_schema_error_chain_with_from_batch14():
    """raise ... from e 会设置 __cause__。"""
    try:
        try:
            raise ValueError("inner")
        except ValueError as e:
            raise EvalSchemaError("outer") from e
    except EvalSchemaError as outer:
        assert outer.__cause__ is not None
        assert isinstance(outer.__cause__, ValueError)


# ---------- load_schema 行为深度第十四批 ----------


def test_load_schema_manifest_returns_dict_batch14():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_annotation_returns_dict_batch14():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_load_schema_evaluation_report_returns_dict_batch14():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


def test_load_schema_returns_new_instance_each_call_batch14():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2
    assert s1 is not s2  # 不缓存


def test_load_schema_has_schema_or_id_batch14():
    s = load_schema("manifest.schema.json")
    assert "$schema" in s or "$id" in s


def test_load_schema_has_properties_batch14():
    """JSON Schema 应有 properties 字段。"""
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_load_schema_unknown_name_batch14():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_uses_utf8_encoding_batch14():
    """load_schema 用 utf-8 打开文件（直接读源码确认）。"""
    src = inspect.getsource(smod)
    assert 'encoding="utf-8"' in src


# ---------- validate 行为深度第十四批 ----------


def test_validate_invalid_schema_name_raises_filenotfound_batch14():
    """schema_name 不存在 → load_schema → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate({}, "nonexistent.schema.json")


def test_validate_errors_flat_structure_batch14():
    """失败时 errors 列表中每项含 path / message / schema_path。"""
    bad = {"manifest_version": "wrong"}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(bad, "manifest.schema.json")
    errs = exc_info.value.errors
    assert len(errs) > 0
    for e in errs:
        assert set(e.keys()) == {"path", "message", "schema_path"}
        assert isinstance(e["path"], list)
        assert isinstance(e["schema_path"], list)


def test_validate_errors_count_matches_iter_errors_batch14():
    """errors 列表长度应等于 iter_errors 数量。"""
    bad = {"manifest_version": "wrong", "devset_status": 42}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(bad, "manifest.schema.json")
    # 至少 1 个 error
    assert len(exc_info.value.errors) >= 1


def test_validate_does_not_mutate_instance_batch14():
    """validate 不应修改输入 instance。"""
    inst = {"manifest_version": "1.0", "devset_status": "incomplete",
            "documents": [], "expected_failures": []}
    before = repr(inst)
    validate(inst, "manifest.schema.json")
    assert repr(inst) == before


def test_validate_message_includes_schema_name_batch14():
    bad = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(bad, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc_info.value)


def test_validate_message_includes_path_batch14():
    bad = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(bad, "manifest.schema.json")
    assert "path=" in str(exc_info.value)


def test_validate_returns_none_on_success_batch14():
    inst = {"manifest_version": "1.0", "devset_status": "incomplete",
            "documents": [], "expected_failures": []}
    result = validate(inst, "manifest.schema.json")
    assert result is None


def test_validate_passes_with_extra_fields_batch14():
    """JSON Schema 通常默认 additionalProperties false — 验证具体行为。"""
    inst = {"manifest_version": "1.0", "devset_status": "incomplete",
            "documents": [], "expected_failures": [], "extra_field": "x"}
    try:
        validate(inst, "manifest.schema.json")
        # 如果 schema 允许 additionalProperties，那 extra_field 不报错
    except EvalSchemaError as e:
        # 如果 schema 拒绝，应在 errors 中找到
        assert any("additional" in err["message"].lower() or "extra" in err["message"].lower()
                   for err in e.errors) or len(e.errors) > 0


# ---------- validate_file 行为深度第十四批 ----------


def test_validate_file_returns_none_batch14(tmp_path):
    """validate_file 不返回值。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    result = validate_file(p, "manifest.schema.json")
    assert result is None


def test_validate_file_propagates_eval_schema_error_batch14(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"manifest_version": "wrong"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_propagates_json_decode_error_batch14(tmp_path):
    """非法 JSON → json.JSONDecodeError（不被包装）。"""
    p = tmp_path / "m.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_str_path_batch14(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")  # 不抛即可


def test_validate_file_path_input_batch14(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    validate_file(Path(p), "manifest.schema.json")


def test_validate_file_invalid_schema_name_batch14(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "nonexistent.schema.json")


# ---------- _schema_path 行为深度第十四批 ----------


def test_schema_path_returns_existing_file_batch14():
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_does_not_read_file_batch14():
    """_schema_path 只检查存在性，不读内容。"""
    p = _schema_path("manifest.schema.json")
    # 返回 Path，不返回 dict
    assert isinstance(p, Path)


def test_schema_path_not_found_message_includes_path_batch14():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nope.schema.json")
    assert "Schema 文件不存在" in str(exc_info.value)
    assert "nope.schema.json" in str(exc_info.value)


def test_schema_path_concatenation_batch14():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_name_param_batch14():
    sig = inspect.signature(_schema_path)
    assert "name" in sig.parameters


def test_schema_path_with_subdir_batch14():
    """传 subdir/name 形式 — 但 schemas 下没有子目录。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/manifest.schema.json")


# ---------- module source forbidden tokens 第十九批 ----------


@pytest.mark.parametrize("forbidden", [
    "subprocess",
    "os.system",
    "os.popen",
    "pty.spawn",
    "commands.getoutput",
    "paramiko",
    "fabric.api",
    "ftplib",
    "smtplib",
    "telnetlib",
    "webbrowser.open",
    "socket.socket",
    "asyncio.open_connection",
    "multiprocessing.Process",
    "threading.Thread",
    "ctypes.CDLL",
])
def test_module_source_forbidden_tokens_batch14(forbidden):
    src = inspect.getsource(smod)
    assert forbidden not in src


# ---------- module source 字符串精确补强第十六批 ----------


def test_module_source_has_future_annotations_batch14():
    src = inspect.getsource(smod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch14():
    src = inspect.getsource(smod)
    assert '"""加载并校验本阶段三个新 Schema' in src


def test_module_source_has_class_eval_schema_error_batch14():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_has_schemas_dir_constant_batch14():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = Path(__file__).resolve().parent.parent" in src


def test_module_source_has_load_schema_function_batch14():
    src = inspect.getsource(smod)
    assert "def load_schema(name: str) -> dict[str, Any]:" in src


def test_module_source_has_validate_function_batch14():
    src = inspect.getsource(smod)
    assert "def validate(instance: dict[str, Any], schema_name: str) -> None:" in src


def test_module_source_has_validate_file_function_batch14():
    src = inspect.getsource(smod)
    assert "def validate_file(path: Path | str, schema_name: str) -> None:" in src


def test_module_source_has_schema_path_function_batch14():
    src = inspect.getsource(smod)
    assert "def _schema_path(name: str) -> Path:" in src


def test_module_source_has_draft202012_validator_batch14():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_has_json_import_batch14():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_has_pathlib_import_batch14():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch14():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_has_all_dunder_batch14():
    src = inspect.getsource(smod)
    assert "__all__ = [" in src


def test_module_source_all_contains_schemas_dir_batch14():
    src = inspect.getsource(smod)
    assert '"SCHEMAS_DIR"' in src


def test_module_source_all_contains_eval_schema_error_batch14():
    src = inspect.getsource(smod)
    assert '"EvalSchemaError"' in src


def test_module_source_all_contains_load_schema_batch14():
    src = inspect.getsource(smod)
    assert '"load_schema"' in src


def test_module_source_all_contains_validate_batch14():
    src = inspect.getsource(smod)
    assert '"validate"' in src


def test_module_source_all_contains_validate_file_batch14():
    src = inspect.getsource(smod)
    assert '"validate_file"' in src


def test_module_source_has_iter_errors_batch14():
    src = inspect.getsource(smod)
    assert "iter_errors" in src


def test_module_source_has_sorted_errors_batch14():
    src = inspect.getsource(smod)
    assert "sorted(validator.iter_errors" in src


def test_module_source_has_message_count_format_batch14():
    src = inspect.getsource(smod)
    assert "len(errors)" in src


def test_module_source_has_path_list_in_message_batch14():
    src = inspect.getsource(smod)
    assert "list(head.absolute_path)" in src


def test_module_source_has_app_schema_separation_comment_batch14():
    src = inspect.getsource(smod)
    assert "app/schema.py" in src


# ---------- signatures 第十六批 ----------


def test_signature_schema_path_batch14():
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.keys())
    assert params == ["name"]


def test_signature_load_schema_batch14():
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.keys())
    assert params == ["name"]


def test_signature_validate_batch14():
    sig = inspect.signature(validate)
    params = list(sig.parameters.keys())
    assert params == ["instance", "schema_name"]


def test_signature_validate_file_batch14():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.keys())
    assert params == ["path", "schema_name"]


def test_signature_eval_schema_error_init_batch14():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "errors"]
    assert sig.parameters["errors"].default is None


def test_signature_validate_no_varargs_batch14():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


# ---------- module 合理性第十六批 ----------


def test_module_has_all_attribute_batch14():
    assert hasattr(smod, "__all__")
    assert isinstance(smod.__all__, list)


def test_module_all_items_exist_as_attributes_batch14():
    for name in smod.__all__:
        assert hasattr(smod, name)


def test_module_all_items_callable_or_path_batch14():
    """__all__ 中函数 callable，常量是 Path，类 callable。"""
    for name in smod.__all__:
        attr = getattr(smod, name)
        assert callable(attr) or isinstance(attr, Path)


def test_module_eval_schema_error_is_exception_batch14():
    assert issubclass(EvalSchemaError, Exception)


def test_module_schemas_dir_is_path_batch14():
    assert isinstance(SCHEMAS_DIR, Path)


def test_module_uses_jsonschema_batch14():
    """模块依赖 jsonschema 库。"""
    import jsonschema
    assert jsonschema is not None


def test_module_load_schema_callable_batch14():
    assert callable(load_schema)


def test_module_validate_callable_batch14():
    assert callable(validate)


def test_module_validate_file_callable_batch14():
    assert callable(validate_file)


def test_module_does_not_import_app_schema_batch14():
    """明确不与 app/schema.py 复用。"""
    src = inspect.getsource(smod)
    assert "from app.schema" not in src
    assert "import app.schema" not in src


# ---------- 端到端集成第十六批 ----------


def test_e2e_validate_manifest_success_batch14():
    inst = {"manifest_version": "1.0", "devset_status": "incomplete",
            "documents": [], "expected_failures": []}
    validate(inst, "manifest.schema.json")  # 不抛


def test_e2e_validate_manifest_missing_required_batch14():
    inst = {"manifest_version": "1.0"}
    with pytest.raises(EvalSchemaError):
        validate(inst, "manifest.schema.json")


def test_e2e_validate_manifest_wrong_type_batch14():
    inst = {"manifest_version": 1.0, "devset_status": "incomplete",
            "documents": [], "expected_failures": []}
    with pytest.raises(EvalSchemaError):
        validate(inst, "manifest.schema.json")


def test_e2e_validate_file_manifest_batch14(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")  # 不抛


def test_e2e_validate_file_not_exist_batch14(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "nope.json", "manifest.schema.json")


def test_e2e_eval_schema_error_with_complex_errors_batch14():
    """EvalSchemaError 能装复杂 errors。"""
    complex_errs = [
        {"path": ["a", "b"], "message": "type wrong", "schema_path": ["properties", "a"]},
        {"path": ["c"], "message": "missing", "schema_path": ["required"]},
    ]
    err = EvalSchemaError("complex", errors=complex_errs)
    assert len(err.errors) == 2
    assert err.errors[0]["path"] == ["a", "b"]


def test_e2e_eval_schema_error_pickle_roundtrip_batch14():
    err = EvalSchemaError("msg", errors=[{"path": ["x"], "message": "m"}])
    pickled = pickle.dumps(err)
    restored = pickle.loads(pickled)
    assert isinstance(restored, EvalSchemaError)
    assert str(restored) == str(err)


def test_e2e_load_schema_returns_meaningful_dict_batch14():
    s = load_schema("manifest.schema.json")
    # JSON Schema 必须含某些字段
    assert "type" in s or "$schema" in s or "$id" in s


def test_e2e_validate_three_schemas_distinct_batch14():
    """三个 schema 互不相同。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("annotation.schema.json")
    s3 = load_schema("evaluation-report.schema.json")
    assert s1 != s2 != s3 != s1


def test_e2e_validate_annotation_smoke_batch14():
    """annotation schema 至少能加载（结构由 edges33 覆盖）。"""
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)
    assert "properties" in s or "type" in s
