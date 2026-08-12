"""evaluation/schema.py 第四十七轮 edges 测试（Round 523）。

补强 edges46 未触及的角度（第二十七批）：
- EvalSchemaError 第二十七批：默认 errors=[] / errors 传入空 list / errors truthy / message 是空 str / str(e) 只含 message / __cause__ 默认 None
- _schema_path 第二十七批：返回 Path / Path is_absolute / 含 .. 路径 / 多个 . in name
- load_schema 第二十七批：annotation / evaluation-report schema 都能加载 / 返回非空 dict / 多次独立
- validate 第二十七批：单错误消息含 path / errors 含三项 / 空 errors 不抛 / instance 是 dict 才生效
- validate_file 第二十七批：返回 None / Path 与 str 等价 / 不存在 → FileNotFoundError / 编码 utf-8 强制
- module source forbidden tokens 第四十五批
- module source 字符串精确补强第四十一批
- signatures 第四十一批
- module 合理性第四十一批
- 端到端集成第四十一批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from jsonschema.exceptions import ValidationError as JSValidationError

from evaluation import schema as smod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- EvalSchemaError 第二十七批 ----------


def test_eval_schema_error_default_errors_empty_list_batch27():
    """无 errors 参数 → 默认空 list。"""
    e = EvalSchemaError("msg")
    assert e.errors == []


def test_eval_schema_error_pass_empty_list_batch27():
    e = EvalSchemaError("msg", [])
    assert e.errors == []


def test_eval_schema_error_pass_truthy_list_batch27():
    e = EvalSchemaError("msg", [{"x": 1}])
    assert bool(e.errors) is True


def test_eval_schema_error_message_empty_str_batch27():
    """message 是空 str 也合法。"""
    e = EvalSchemaError("")
    assert str(e) == ""


def test_eval_schema_error_str_is_message_batch27():
    """str(e) 只含 message，不含 errors。"""
    e = EvalSchemaError("hello", [{"x": 1}])
    assert str(e) == "hello"


def test_eval_schema_error_cause_default_none_batch27():
    e = EvalSchemaError("msg")
    assert e.__cause__ is None


def test_eval_schema_error_repr_batch27():
    """repr 含类名。"""
    e = EvalSchemaError("hello")
    assert "EvalSchemaError" in repr(e)


def test_eval_schema_error_is_exception_batch27():
    e = EvalSchemaError("hello")
    assert isinstance(e, Exception)


def test_eval_schema_error_can_be_caught_by_except_exception_batch27():
    try:
        raise EvalSchemaError("x")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


# ---------- _schema_path 第二十七批 ----------


def test_schema_path_returns_path_object_batch27():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_returns_absolute_batch27():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_with_dot_dot_batch27():
    """name 含 .. 路径组件 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("../manifest.schema.json")


def test_schema_path_name_multiple_dots_batch27():
    """name 含多个 .（但不存在）→ FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("manifest.schema.json.backup")


def test_schema_path_message_contains_path_batch27():
    """FileNotFoundError 消息含路径。"""
    try:
        _schema_path("nonexistent.json")
    except FileNotFoundError as e:
        assert "nonexistent.json" in str(e)
        return
    pytest.fail("Expected FileNotFoundError")


def test_schema_path_manifest_exists_batch27():
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_annotation_exists_batch27():
    p = _schema_path("annotation.schema.json")
    assert p.is_file()


def test_schema_path_evaluation_report_exists_batch27():
    p = _schema_path("evaluation-report.schema.json")
    assert p.is_file()


# ---------- load_schema 第二十七批 ----------


def test_load_schema_returns_dict_batch27():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_returns_non_empty_dict_batch27():
    s = load_schema("annotation.schema.json")
    assert len(s) > 0


def test_load_schema_idempotent_batch27():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2
    assert s1 is not s2


def test_load_schema_independent_objects_batch27():
    """修改 s1 不影响 s2。"""
    s1 = load_schema("manifest.schema.json")
    s1["_hack"] = "x"
    s2 = load_schema("manifest.schema.json")
    assert "_hack" not in s2


def test_load_schema_evaluation_report_batch27():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)
    assert s.get("type") == "object"


def test_load_schema_annotation_batch27():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_load_schema_unknown_raises_batch27():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


# ---------- validate 第二十七批 ----------


def test_validate_empty_dict_manifest_three_errors_batch27():
    """空 dict vs manifest schema → 3 个 required 错误。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert len(exc.value.errors) == 3  # manifest_version, devset_status, documents


def test_validate_errors_have_three_keys_batch27():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert set(err.keys()) == {"path", "message", "schema_path"}


def test_validate_no_errors_returns_none_batch27():
    """合法 instance → 返回 None。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_validate_message_contains_schema_name_batch27():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc.value)


def test_validate_message_contains_path_batch27():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    # message 含 "path="
    assert "path=" in str(exc.value)


def test_validate_message_contains_error_count_batch27():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert "3 处" in str(exc.value)


def test_validate_invalid_source_type_batch27():
    """source_type 不在 enum。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "weird"}
        ],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_valid_manifest_returns_none_batch27():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "sha256": "a" * 64}
        ],
    }
    validate(instance, "manifest.schema.json")


def test_validate_evaluation_report_schema_batch27():
    """evaluation-report schema 能用。"""
    s = load_schema("evaluation-report.schema.json")
    assert s.get("type") == "object"


# ---------- validate_file 第二十七批 ----------


def test_validate_file_returns_none_on_success_batch27(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_path_str_equiv_batch27(tmp_path):
    p = tmp_path / "m.json"
    content = json.dumps(
        {
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": [],
        }
    )
    p.write_text(content, encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_nonexistent_raises_batch27():
    with pytest.raises(FileNotFoundError):
        validate_file("/nonexistent/path.json", "manifest.schema.json")


def test_validate_file_directory_raises_batch27(tmp_path):
    """传目录而非文件 → FileNotFoundError。"""
    d = tmp_path / "subdir"
    d.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(d, "manifest.schema.json")


def test_validate_file_invalid_json_raises_batch27(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("not valid json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_data_raises_eval_error_batch27(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_unknown_schema_raises_batch27(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "nonexistent.schema.json")


def test_validate_file_no_input_modification_batch27(tmp_path):
    p = tmp_path / "m.json"
    content = json.dumps(
        {
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": [],
        }
    )
    p.write_text(content, encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    assert p.read_text(encoding="utf-8") == content


# ---------- module source forbidden tokens 第四十五批 ----------


def test_module_source_no_subprocess_batch27():
    src = inspect.getsource(smod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch27():
    src = inspect.getsource(smod)
    assert "os.system" not in src


def test_module_source_no_eval_batch27():
    src = inspect.getsource(smod)
    assert "eval(" not in src


def test_module_source_no_exec_batch27():
    src = inspect.getsource(smod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch27():
    src = inspect.getsource(smod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch27():
    src = inspect.getsource(smod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch27():
    src = inspect.getsource(smod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch27():
    src = inspect.getsource(smod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch27():
    """schema 模块只读。"""
    src = inspect.getsource(smod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch27():
    src = inspect.getsource(smod)
    assert "shutil" not in src


def test_module_source_no_requests_batch27():
    src = inspect.getsource(smod)
    assert "requests" not in src


def test_module_source_no_unlink_batch27():
    src = inspect.getsource(smod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十一批 ----------


def test_module_source_contains_module_docstring_batch27():
    src = inspect.getsource(smod)
    assert "加载并校验" in src


def test_module_source_contains_schemas_dir_batch27():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = " in src


def test_module_source_contains_eval_schema_error_class_batch27():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_contains_errors_param_batch27():
    src = inspect.getsource(smod)
    assert "errors: list[dict[str, Any]] | None = None" in src


def test_module_source_contains_default_empty_batch27():
    src = inspect.getsource(smod)
    assert "self.errors = errors or []" in src


def test_module_source_contains_schema_path_func_batch27():
    src = inspect.getsource(smod)
    assert "def _schema_path" in src


def test_module_source_contains_file_not_found_message_batch27():
    src = inspect.getsource(smod)
    assert "Schema 文件不存在" in src


def test_module_source_contains_load_schema_func_batch27():
    src = inspect.getsource(smod)
    assert "def load_schema" in src


def test_module_source_contains_validate_func_batch27():
    src = inspect.getsource(smod)
    assert "def validate(" in src


def test_module_source_contains_validate_file_func_batch27():
    src = inspect.getsource(smod)
    assert "def validate_file(" in src


def test_module_source_contains_draft_2020_12_batch27():
    src = inspect.getsource(smod)
    assert "Draft202012Validator" in src


def test_module_source_contains_absolute_path_batch27():
    src = inspect.getsource(smod)
    assert "absolute_path" in src


# ---------- signatures 第四十一批 ----------


def test_signature_eval_schema_error_init_batch27():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "errors"]


def test_signature_eval_schema_error_init_message_annotation_batch27():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["message"].annotation == "str"


def test_signature_eval_schema_error_init_errors_annotation_batch27():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert "list[dict[str, Any]] | None" in str(sig.parameters["errors"].annotation)


def test_signature_eval_schema_error_init_errors_default_batch27():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_signature_eval_schema_error_init_return_batch27():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.return_annotation == "None"


def test_signature_schema_path_batch27():
    sig = inspect.signature(_schema_path)
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "Path"


def test_signature_load_schema_batch27():
    sig = inspect.signature(load_schema)
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_validate_batch27():
    sig = inspect.signature(validate)
    assert sig.parameters["instance"].annotation == "dict[str, Any]"
    assert sig.parameters["schema_name"].annotation == "str"
    assert sig.return_annotation == "None"


def test_signature_validate_file_batch27():
    sig = inspect.signature(validate_file)
    assert "Path" in str(sig.parameters["path"].annotation)
    assert "str" in str(sig.parameters["path"].annotation)
    assert sig.parameters["schema_name"].annotation == "str"
    assert sig.return_annotation == "None"


# ---------- module 合理性第四十一批 ----------


def test_module_has_future_annotations_batch27():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch27():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_imports_pathlib_batch27():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch27():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_imports_jsonschema_batch27():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_imports_validation_error_batch27():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_schemas_dir_is_absolute_batch27():
    assert SCHEMAS_DIR.is_absolute()


def test_module_no_main_block_batch27():
    src = inspect.getsource(smod)
    assert 'if __name__ == "__main__"' not in src


def test_module_all_contains_five_entries_batch27():
    src = inspect.getsource(smod)
    for name in [
        '"SCHEMAS_DIR"',
        '"EvalSchemaError"',
        '"load_schema"',
        '"validate"',
        '"validate_file"',
    ]:
        assert name in src


# ---------- 端到端集成第四十一批 ----------


def test_e2e_validate_full_manifest_roundtrip_batch27(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "sha256": "a" * 64}
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_load_then_validate_batch27():
    """端到端：load_schema → validator → validate。"""
    s = load_schema("manifest.schema.json")
    v = __import__("jsonschema").Draft202012Validator(s)
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    errors = list(v.iter_errors(instance))
    assert errors == []


def test_e2e_eval_schema_error_caught_specifically_batch27():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert "manifest.schema.json" in str(e)
        return
    pytest.fail("Expected EvalSchemaError")


def test_e2e_three_schemas_all_present_batch27():
    for name in [
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    ]:
        p = _schema_path(name)
        assert p.is_file()


def test_e2e_validate_errors_complete_format_batch27():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["path"], list)
        assert isinstance(err["schema_path"], list)
        assert isinstance(err["message"], str)


def test_e2e_schemas_dir_contains_files_batch27():
    files = list(SCHEMAS_DIR.glob("*.json"))
    names = [f.name for f in files]
    assert "manifest.schema.json" in names
    assert "annotation.schema.json" in names
    assert "evaluation-report.schema.json" in names


def test_e2e_validate_idempotent_batch27():
    """端到端：相同输入两次得到相同结果。"""
    for _ in range(2):
        try:
            validate({}, "manifest.schema.json")
        except EvalSchemaError as e1:
            try:
                validate({}, "manifest.schema.json")
            except EvalSchemaError as e2:
                assert str(e1) == str(e2)
                assert e1.errors == e2.errors
                return
    pytest.fail("Expected EvalSchemaError")
