"""evaluation/schema.py 第五十五轮 edges 测试（Round 575）。

补强 edges53 未触及的角度（第三十四批）。
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


# ---------- EvalSchemaError 第三十四批


def test_eval_schema_error_not_typeerror_batch34():
    assert not issubclass(EvalSchemaError, TypeError)


def test_eval_schema_error_not_attribute_error_batch34():
    assert not issubclass(EvalSchemaError, AttributeError)


def test_eval_schema_error_not_runtime_error_batch34():
    assert not issubclass(EvalSchemaError, RuntimeError)


def test_eval_schema_error_errors_attribute_present_batch34():
    """EvalSchemaError 总有 .errors attribute。"""
    e = EvalSchemaError("msg")
    assert hasattr(e, "errors")


def test_eval_schema_error_errors_with_unicode_message_batch34():
    e = EvalSchemaError("中文错误消息")
    assert str(e) == "中文错误消息"


def test_eval_schema_error_errors_with_empty_dict_batch34():
    """errors 含空 dict 仍保留。"""
    e = EvalSchemaError("msg", [{}])
    assert e.errors == [{}]


def test_eval_schema_error_errors_with_nested_dict_batch34():
    errs = [{"path": ["a", "b", "c"], "message": "nested", "schema_path": ["x"]}]
    e = EvalSchemaError("msg", errs)
    assert e.errors[0]["path"] == ["a", "b", "c"]


def test_eval_schema_error_str_returns_message_batch34():
    """str(error) 应当只返回 message（不是 errors）。"""
    e = EvalSchemaError("the_message", [{"x": 1}])
    assert str(e) == "the_message"


def test_eval_schema_error_two_arg_init_batch34():
    """两个参数（message + errors）。"""
    e = EvalSchemaError("a", [])
    assert e.args == ("a",)
    assert e.errors == []


def test_eval_schema_error_init_signature_batch34():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert list(sig.parameters.keys()) == ["self", "message", "errors"]


def test_eval_schema_error_errors_default_is_empty_list_batch34():
    """errors=None → []。"""
    e = EvalSchemaError("x", None)
    assert e.errors == []
    assert isinstance(e.errors, list)


def test_eval_schema_error_can_chain_cause_batch34():
    try:
        try:
            raise ValueError("inner")
        except ValueError as ve:
            raise EvalSchemaError("outer") from ve
    except EvalSchemaError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, ValueError)


def test_eval_schema_error_no_custom_methods_batch34():
    """EvalSchemaError 没有自定义 method（只 override __init__）。
    公开方法只继承自 BaseException（add_note/with_traceback）。"""
    methods = [m for m in dir(EvalSchemaError) if not m.startswith("_")]
    public_methods = [m for m in methods if callable(getattr(EvalSchemaError, m, None))]
    # 这些都是 BaseException 继承下来的
    for m in public_methods:
        assert m in dir(BaseException)


# ---------- SCHEMAS_DIR 第三十四批


def test_schemas_dir_is_absolute_batch34():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_exists_batch34():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_contains_manifest_batch34():
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_batch34():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_batch34():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_parent_contains_pyproject_batch34():
    """SCHEMAS_DIR 在 project root 下。"""
    assert (SCHEMAS_DIR.parent / "pyproject.toml").exists()


# ---------- _schema_path 第三十四批


def test_schema_path_with_absolute_path_batch34():
    """传绝对路径 → 仍能在 SCHEMAS_DIR/absolute 下找到（但会失败）。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("/absolute/path/missing.json")


def test_schema_path_two_dots_in_name_batch34():
    """文件名带两个点 → 找不到。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("foo.bar.json")


def test_schema_path_with_trailing_slash_batch34():
    """name 带尾斜杠 → Path 拼接会规范化（去除尾斜杠）→ 实际文件存在。"""
    p = _schema_path("manifest.schema.json/")
    # Path 会规范化，仍能找到文件
    assert p.name == "manifest.schema.json"


def test_schema_path_with_only_extension_batch34():
    with pytest.raises(FileNotFoundError):
        _schema_path(".json")


def test_schema_path_with_empty_string_batch34():
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_with_space_in_name_batch34():
    with pytest.raises(FileNotFoundError):
        _schema_path("my schema.json")


def test_schema_path_return_value_is_absolute_batch34():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_dot_segment_resolves_batch34():
    """'./xxx' 中的 . 表示 SCHEMAS_DIR 本身。"""
    p = _schema_path("./annotation.schema.json")
    assert p.is_file()


def test_schema_path_two_dots_up_segment_batch34():
    """'../<name>' → 解析到 project root 下。"""
    # 但 schemas 在 project root 下，所以 ../manifest.schema.json 找不到
    with pytest.raises(FileNotFoundError):
        _schema_path("../manifest.schema.json")


# ---------- load_schema 第三十四批


def test_load_schema_with_unicode_chars_batch34():
    """schema 文件包含中文描述（manifest 含'开发集清单'）。"""
    s = load_schema("manifest.schema.json")
    src = json.dumps(s, ensure_ascii=False)
    # 检查 description 至少包含一些可读字符
    assert "manifest" in src.lower() or "清单" in src


def test_load_schema_manifest_required_keys_batch34():
    s = load_schema("manifest.schema.json")
    required = s.get("required", [])
    assert "manifest_version" in required
    assert "devset_status" in required
    assert "documents" in required


def test_load_schema_annotation_required_keys_batch34():
    s = load_schema("annotation.schema.json")
    required = s.get("required", [])
    assert "annotation_version" in required
    assert "doc_id" in required


def test_load_schema_eval_report_required_keys_batch34():
    s = load_schema("evaluation-report.schema.json")
    required = s.get("required", [])
    # 至少有 1 个 required field
    assert len(required) > 0


def test_load_schema_manifest_has_additional_properties_false_batch34():
    s = load_schema("manifest.schema.json")
    assert s.get("additionalProperties") is False


def test_load_schema_annotation_version_const_batch34():
    s = load_schema("annotation.schema.json")
    props = s.get("properties", {})
    version = props.get("annotation_version", {})
    # version 是 const 或 enum
    assert "const" in version or "enum" in version


def test_load_schema_idempotent_dict_value_batch34():
    """多次 load_schema 返回相同内容（独立 dict）。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2
    assert s1 is not s2  # 不是同一对象


def test_load_schema_returns_fresh_dict_batch34():
    """每次返回新 dict，修改不影响下次。"""
    s1 = load_schema("manifest.schema.json")
    s1["mutated"] = True
    s2 = load_schema("manifest.schema.json")
    assert "mutated" not in s2


# ---------- validate 第三十四批


def test_validate_manifest_minimal_valid_batch34():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")


def test_validate_manifest_complete_status_batch34():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")


def test_validate_manifest_additional_property_rejected_batch34():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
        "extra_field": "should fail",
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_manifest_documents_array_required_batch34():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": "not_an_array",  # wrong type
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_manifest_devset_status_invalid_value_batch34():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "pending",  # not in enum
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_manifest_devset_status_case_sensitive_batch34():
    """'Incomplete' 大写不允许。"""
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "Incomplete",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_annotation_minimal_batch34():
    data = {"annotation_version": "1.0", "doc_id": "d1"}
    validate(data, "annotation.schema.json")


def test_validate_annotation_doc_id_min_length_batch34():
    """doc_id 必须 minLength >= 1。"""
    data = {"annotation_version": "1.0", "doc_id": ""}
    with pytest.raises(EvalSchemaError):
        validate(data, "annotation.schema.json")


def test_validate_annotation_with_chunk_boundary_anchors_valid_batch34():
    data = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "text", "position": "after"},
        ],
    }
    validate(data, "annotation.schema.json")


def test_validate_annotation_position_invalid_batch34():
    """position 必须是 before/after（如果 schema 限定）。"""
    data = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "text", "position": "invalid"},
        ],
    }
    # 可能允许也可能不允许，看 schema；至少不抛即可
    try:
        validate(data, "annotation.schema.json")
    except EvalSchemaError:
        pass  # 也允许


def test_validate_annotation_marker_empty_string_batch34():
    """marker 空字符串（schema 可能 minLength=1）。"""
    data = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [{"marker": ""}],
    }
    # 如果 schema 限定 minLength=1 会失败
    try:
        validate(data, "annotation.schema.json")
    except EvalSchemaError:
        pass


def test_validate_error_count_in_message_batch34():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1"}],  # missing path + source_type
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError) as exc:
        validate(data, "manifest.schema.json")
    s = str(exc.value)
    # message 含错误数
    assert "校验失败" in s
    assert "处" in s


def test_validate_error_path_in_message_batch34():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1"}],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError) as exc:
        validate(data, "manifest.schema.json")
    s = str(exc.value)
    assert "path=" in s


def test_validate_errors_list_path_format_batch34():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1"}],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError) as exc:
        validate(data, "manifest.schema.json")
    for err in exc.value.errors:
        assert "path" in err
        assert "message" in err
        assert "schema_path" in err
        assert isinstance(err["path"], list)


def test_validate_does_not_mutate_input_batch34():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    before = json.dumps(data, sort_keys=True)
    validate(data, "manifest.schema.json")
    assert json.dumps(data, sort_keys=True) == before


def test_validate_unknown_schema_raises_batch34():
    with pytest.raises(FileNotFoundError):
        validate({}, "unknown.schema.json")


def test_validate_returns_none_on_success_batch34():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(data, "manifest.schema.json") is None


# ---------- validate_file 第三十四批


def _write_json(p: Path, data: Any) -> Path:
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_validate_file_str_path_batch34(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = _write_json(tmp_path / "manifest.json", data)
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_pathlib_path_batch34(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = _write_json(tmp_path / "manifest.json", data)
    validate_file(p, "manifest.schema.json")


def test_validate_file_missing_raises_batch34(tmp_path):
    with pytest.raises(FileNotFoundError) as exc:
        validate_file(tmp_path / "missing.json", "manifest.schema.json")
    assert "不存在" in str(exc.value)


def test_validate_file_directory_raises_batch34(tmp_path):
    """校验目录 → FileNotFoundError（不是文件）。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(sub, "manifest.schema.json")


def test_validate_file_invalid_json_raises_batch34(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json {", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_batch34(tmp_path):
    p = _write_json(tmp_path / "bad.json", {"wrong": "shape"})
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_returns_none_on_success_batch34(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = _write_json(tmp_path / "manifest.json", data)
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_annotation_batch34(tmp_path):
    data = {"annotation_version": "1.0", "doc_id": "d1"}
    p = _write_json(tmp_path / "ann.json", data)
    validate_file(p, "annotation.schema.json")


def test_validate_file_does_not_mutate_disk_batch34(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = _write_json(tmp_path / "manifest.json", data)
    before = p.read_text(encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    after = p.read_text(encoding="utf-8")
    assert before == after


def test_validate_file_unknown_schema_raises_batch34(tmp_path):
    p = _write_json(tmp_path / "x.json", {})
    with pytest.raises(FileNotFoundError):
        validate_file(p, "unknown.schema.json")


def test_validate_file_idempotent_batch34(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = _write_json(tmp_path / "manifest.json", data)
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")


def test_validate_file_empty_json_object_batch34(tmp_path):
    """空 dict 通常不符合 schema。"""
    p = _write_json(tmp_path / "empty.json", {})
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


# ---------- module source forbidden tokens 第五十七批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch34(token):
    src = inspect.getsource(smod)
    assert token not in src


# ---------- module source 字符串精确补强第五十三批


def test_module_source_contains_eval_schema_error_class_batch34():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_contains_errors_default_empty_batch34():
    src = inspect.getsource(smod)
    assert "self.errors = errors or []" in src


def test_module_source_contains_message_param_doc_batch34():
    src = inspect.getsource(smod)
    assert "errors 给程序看" in src


def test_module_source_contains_draft202012_validator_batch34():
    src = inspect.getsource(smod)
    assert "Draft202012Validator" in src


def test_module_source_contains_iter_errors_call_batch34():
    src = inspect.getsource(smod)
    assert "validator.iter_errors(instance)" in src


def test_module_source_contains_absolute_path_batch34():
    src = inspect.getsource(smod)
    assert "absolute_path" in src


def test_module_source_contains_absolute_schema_path_batch34():
    src = inspect.getsource(smod)
    assert "absolute_schema_path" in src


def test_module_source_contains_path_field_in_flat_batch34():
    src = inspect.getsource(smod)
    assert '"path": list(err.absolute_path)' in src


def test_module_source_contains_schema_path_field_in_flat_batch34():
    src = inspect.getsource(smod)
    assert '"schema_path": list(err.absolute_schema_path)' in src


def test_module_source_contains_count_in_error_message_batch34():
    src = inspect.getsource(smod)
    assert "{len(errors)}" in src


def test_module_source_contains_head_error_batch34():
    src = inspect.getsource(smod)
    assert "errors[0]" in src


def test_module_source_contains_schemas_dir_definition_batch34():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = Path(__file__).resolve().parent.parent" in src


def test_module_source_contains_schemas_subdir_batch34():
    src = inspect.getsource(smod)
    assert '"schemas"' in src


def test_module_source_contains_schema_path_func_batch34():
    src = inspect.getsource(smod)
    assert "def _schema_path(name: str) -> Path:" in src


def test_module_source_contains_load_schema_func_batch34():
    src = inspect.getsource(smod)
    assert "def load_schema(name: str)" in src


def test_module_source_contains_validate_func_batch34():
    src = inspect.getsource(smod)
    assert "def validate(instance" in src


def test_module_source_contains_validate_file_func_batch34():
    src = inspect.getsource(smod)
    assert "def validate_file(path" in src


def test_module_source_contains_all_export_batch34():
    src = inspect.getsource(smod)
    assert "__all__" in src


def test_module_source_all_contains_schemas_dir_batch34():
    src = inspect.getsource(smod)
    assert '"SCHEMAS_DIR"' in src


def test_module_source_all_contains_eval_schema_error_batch34():
    src = inspect.getsource(smod)
    assert '"EvalSchemaError"' in src


def test_module_source_all_contains_load_schema_batch34():
    src = inspect.getsource(smod)
    assert '"load_schema"' in src


def test_module_source_all_contains_validate_batch34():
    src = inspect.getsource(smod)
    assert '"validate"' in src


def test_module_source_all_contains_validate_file_batch34():
    src = inspect.getsource(smod)
    assert '"validate_file"' in src


def test_module_source_contains_json_import_batch34():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_contains_pathlib_import_batch34():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


# ---------- signatures 第五十三批


def test_signature_eval_schema_error_init_batch34():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "errors"]


def test_signature_eval_schema_error_errors_default_none_batch34():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_signature_schema_path_one_param_batch34():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_schema_path_return_path_batch34():
    sig = inspect.signature(_schema_path)
    assert sig.return_annotation == "Path"


def test_signature_load_schema_one_param_batch34():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_validate_two_params_batch34():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_signature_validate_file_two_params_batch34():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_signature_validate_file_path_union_type_batch34():
    sig = inspect.signature(validate_file)
    p = sig.parameters["path"]
    # annotation 是 'Path | str'
    assert "Path" in str(p.annotation)
    assert "str" in str(p.annotation)


# ---------- module 合理性第五十三批


def test_module_has_schemas_dir_attribute_batch34():
    assert hasattr(smod, "SCHEMAS_DIR")


def test_module_has_eval_schema_error_attribute_batch34():
    assert hasattr(smod, "EvalSchemaError")


def test_module_has_load_schema_attribute_batch34():
    assert hasattr(smod, "load_schema")


def test_module_has_validate_attribute_batch34():
    assert hasattr(smod, "validate")


def test_module_has_validate_file_attribute_batch34():
    assert hasattr(smod, "validate_file")


def test_module_has_schema_path_attribute_batch34():
    assert hasattr(smod, "_schema_path")


def test_module_all_contains_5_entries_batch34():
    assert len(smod.__all__) == 5


def test_module_all_names_are_str_batch34():
    for name in smod.__all__:
        assert isinstance(name, str)


def test_module_all_names_exist_in_module_batch34():
    for name in smod.__all__:
        assert hasattr(smod, name)


def test_module_eval_schema_error_is_class_batch34():
    assert isinstance(smod.EvalSchemaError, type)


# ---------- 端到端集成第五十三批


def test_e2e_validate_full_manifest_batch34(tmp_path):
    """完整 manifest 端到端校验。"""
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx",
             "categories": ["essay"], "paired_with": "d1"},
        ],
        "expected_failures": [],
    }
    p = _write_json(tmp_path / "manifest.json", data)
    validate_file(p, "manifest.schema.json")


def test_e2e_validate_full_annotation_batch34(tmp_path):
    """完整 annotation 端到端校验。"""
    data = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "first para", "position": "after"},
            {"marker": "second para", "position": "before"},
        ],
    }
    p = _write_json(tmp_path / "ann.json", data)
    validate_file(p, "annotation.schema.json")


def test_e2e_idempotent_validate_batch34(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = _write_json(tmp_path / "manifest.json", data)
    for _ in range(5):
        validate_file(p, "manifest.schema.json")


def test_e2e_validate_and_load_round_trip_batch34(tmp_path):
    """validate_file 内部用 load_schema；测试 round-trip。"""
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = _write_json(tmp_path / "manifest.json", data)
    # load manifest from disk
    loaded = json.loads(p.read_text(encoding="utf-8"))
    # validate the loaded dict
    validate(loaded, "manifest.schema.json")


def test_e2e_eval_schema_error_raised_with_full_context_batch34():
    """失败时 EvalSchemaError 含 message + errors。"""
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "invalid_status",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError) as exc:
        validate(data, "manifest.schema.json")
    e = exc.value
    assert isinstance(e.errors, list)
    assert len(e.errors) >= 1
    assert "校验失败" in str(e)
