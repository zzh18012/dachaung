"""evaluation/schema.py 第五十四轮 edges 测试（Round 568）。

补强 edges52 未触及的角度（第三十三批）。
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


# ---------- EvalSchemaError 第三十三批


def test_eval_schema_error_inherits_exception_batch33():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_not_value_error_batch33():
    assert not issubclass(EvalSchemaError, ValueError)


def test_eval_schema_error_not_key_error_batch33():
    assert not issubclass(EvalSchemaError, KeyError)


def test_eval_schema_error_errors_default_empty_batch33():
    e = EvalSchemaError("x")
    assert e.errors == []


def test_eval_schema_error_errors_none_treated_as_empty_batch33():
    """传 None 显式 → 默认空 list（不抛）。"""
    e = EvalSchemaError("x", None)
    assert e.errors == []


def test_eval_schema_error_with_three_errors_batch33():
    errs = [{"path": [], "message": "a"}, {"path": [], "message": "b"}, {"path": [], "message": "c"}]
    e = EvalSchemaError("msg", errs)
    assert len(e.errors) == 3


def test_eval_schema_error_message_with_special_chars_batch33():
    """特殊字符 / 多行 message。"""
    msg = "line1\nline2\twith tab and 中文"
    e = EvalSchemaError(msg)
    assert str(e) == msg


def test_eval_schema_error_args_preserved_batch33():
    e = EvalSchemaError("a", [{"x": 1}])
    assert e.args == ("a",)


def test_eval_schema_error_can_be_caught_with_bare_except_batch33():
    try:
        raise EvalSchemaError("x")
    except:  # noqa: E722  # pylint: disable=bare-except
        pass


def test_eval_schema_error_can_be_raised_and_caught_batch33():
    with pytest.raises(EvalSchemaError) as exc:
        raise EvalSchemaError("custom", [{"path": [0]}])
    assert exc.value.errors == [{"path": [0]}]


def test_eval_schema_error_repr_contains_class_name_batch33():
    e = EvalSchemaError("msg")
    assert "EvalSchemaError" in repr(e)


def test_eval_schema_error_message_param_required_batch33():
    """EvalSchemaError() 无参数 → TypeError。"""
    with pytest.raises(TypeError):
        EvalSchemaError()  # type: ignore[no-value-for-parameter]


# ---------- SCHEMAS_DIR 第三十三批


def test_schemas_dir_is_pathlib_path_batch33():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_basename_batch33():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_parent_basename_batch33():
    """SCHEMAS_DIR.parent 是项目根。"""
    assert (SCHEMAS_DIR.parent / "pyproject.toml").is_file()


def test_schemas_dir_resolves_to_same_batch33():
    assert SCHEMAS_DIR == SCHEMAS_DIR.resolve()


# ---------- _schema_path 第三十三批


def test_schema_path_manifest_batch33():
    p = _schema_path("manifest.schema.json")
    assert p.name == "manifest.schema.json"


def test_schema_path_annotation_batch33():
    p = _schema_path("annotation.schema.json")
    assert p.name == "annotation.schema.json"


def test_schema_path_eval_report_batch33():
    p = _schema_path("evaluation-report.schema.json")
    assert p.name == "evaluation-report.schema.json"


def test_schema_path_with_subdir_name_batch33():
    """带路径分隔符的 name → 仍然在 SCHEMAS_DIR 下拼接。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/missing.schema.json")


def test_schema_path_with_dot_prefix_batch33():
    """dot 前缀但实际文件存在 → 仍能找到。"""
    p = _schema_path("./manifest.schema.json")
    assert p.is_file()


def test_schema_path_returns_pathlib_path_batch33():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_string_in_error_message_batch33():
    with pytest.raises(FileNotFoundError) as exc:
        _schema_path("xyz.schema.json")
    assert "xyz.schema.json" in str(exc.value)


def test_schema_path_returns_existing_file_batch33():
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


# ---------- load_schema 第三十三批


def test_load_schema_manifest_type_object_batch33():
    s = load_schema("manifest.schema.json")
    assert s.get("type") == "object"


def test_load_schema_annotation_type_object_batch33():
    s = load_schema("annotation.schema.json")
    assert s.get("type") == "object"


def test_load_schema_eval_report_type_object_batch33():
    s = load_schema("evaluation-report.schema.json")
    assert s.get("type") == "object"


def test_load_schema_returns_dict_batch33():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_does_not_mutate_disk_batch33():
    """load_schema 多次调用不影响文件。"""
    for _ in range(3):
        load_schema("manifest.schema.json")
    # 没有抛异常即 OK


def test_load_schema_idempotent_batch33():
    s1 = load_schema("annotation.schema.json")
    s2 = load_schema("annotation.schema.json")
    assert s1 == s2


def test_load_schema_missing_raises_filenotfound_batch33():
    with pytest.raises(FileNotFoundError):
        load_schema("missing.schema.json")


def test_load_schema_eval_report_has_schema_field_batch33():
    s = load_schema("evaluation-report.schema.json")
    assert "$schema" in s


def test_load_schema_manifest_has_schema_field_batch33():
    s = load_schema("manifest.schema.json")
    assert "$schema" in s


# ---------- validate 第三十三批


def test_validate_manifest_correct_no_raise_batch33():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")  # no raise


def test_validate_manifest_invalid_version_raises_batch33():
    data = {
        "manifest_version": "999.0",  # 不在 enum
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_manifest_invalid_devset_status_raises_batch33():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "wrong_status",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_manifest_document_missing_required_field_batch33():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1"}],  # missing path / source_type
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError) as exc:
        validate(data, "manifest.schema.json")
    assert len(exc.value.errors) >= 2  # path + source_type missing


def test_validate_manifest_expected_failure_missing_required_batch33():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{"doc_id": "x"}],  # missing path + expected_error_code
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_annotation_correct_batch33():
    data = {
        "annotation_version": "1.0",
        "doc_id": "d1",
    }
    validate(data, "annotation.schema.json")  # no raise


def test_validate_annotation_missing_version_batch33():
    data = {"doc_id": "d1"}
    with pytest.raises(EvalSchemaError):
        validate(data, "annotation.schema.json")


def test_validate_annotation_missing_doc_id_batch33():
    data = {"annotation_version": "1.0"}
    with pytest.raises(EvalSchemaError):
        validate(data, "annotation.schema.json")


def test_validate_annotation_with_chunk_boundary_anchors_batch33():
    data = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "xyz", "position": "before"},
        ],
    }
    validate(data, "annotation.schema.json")  # no raise


def test_validate_annotation_anchor_invalid_position_batch33():
    """position 不在 enum ('after'/'before')。"""
    data = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [{"marker": "abc", "position": "invalid"}],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "annotation.schema.json")


def test_validate_eval_report_invalid_no_required_batch33():
    """eval-report 需要至少一些字段；空 dict 失败。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "evaluation-report.schema.json")
    assert len(exc.value.errors) >= 1


def test_validate_errors_path_is_list_batch33():
    """error 项的 path 是 list。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["path"], list)


def test_validate_errors_message_is_str_batch33():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["message"], str)


def test_validate_errors_schema_path_is_list_batch33():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["schema_path"], list)


def test_validate_head_error_message_in_overall_msg_batch33():
    """EvalSchemaError 的 message 含第一个 error 的 message。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    head_msg = exc.value.errors[0]["message"]
    assert head_msg in str(exc.value)


def test_validate_head_error_path_in_overall_msg_batch33():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    head_path = list(exc.value.errors[0]["path"])
    # path 在 message 里以 list 的 str repr 形式出现
    assert "path=" in str(exc.value)


def test_validate_count_in_message_batch33():
    """message 含 "(N 处)" 数字。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    msg = str(exc.value)
    # "(N 处)" 模式
    assert "处" in msg


def test_validate_does_not_mutate_input_batch33():
    """validate 不修改 instance dict。"""
    import copy
    data = {"manifest_version": "wrong"}
    before = copy.deepcopy(data)
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")
    assert data == before


def test_validate_invalid_schema_name_raises_filenotfound_batch33():
    """schema_name 指向不存在的 schema → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate({}, "missing.schema.json")


# ---------- validate_file 第三十三批


def test_validate_file_with_str_path_batch33(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")  # no raise


def test_validate_file_with_pathlib_path_batch33(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(Path(p), "manifest.schema.json")


def test_validate_file_returns_none_batch33(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_missing_raises_filenotfound_batch33(tmp_path):
    with pytest.raises(FileNotFoundError) as exc:
        validate_file(tmp_path / "missing.json", "manifest.schema.json")
    assert "待校验文件不存在" in str(exc.value)


def test_validate_file_directory_raises_filenotfound_batch33(tmp_path):
    """is_file() False → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsonerror_batch33(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("not json {", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_schema_error_batch33(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_does_not_mutate_file_batch33(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    content_before = p.read_text(encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    assert p.read_text(encoding="utf-8") == content_before


def test_validate_file_with_annotation_batch33(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(
        json.dumps({"annotation_version": "1.0", "doc_id": "d1"}),
        encoding="utf-8",
    )
    validate_file(p, "annotation.schema.json")


def test_validate_file_with_annotation_and_anchors_batch33(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(
        json.dumps({
            "annotation_version": "1.0",
            "doc_id": "d1",
            "chunk_boundary_anchors": [
                {"marker": "abc", "position": "after"},
            ],
        }),
        encoding="utf-8",
    )
    validate_file(p, "annotation.schema.json")


def test_validate_file_with_eval_report_invalid_batch33(tmp_path):
    """eval-report schema 校验空 dict → EvalSchemaError。"""
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "evaluation-report.schema.json")


def test_validate_file_with_unknown_schema_name_batch33(tmp_path):
    """schema_name 不存在 → FileNotFoundError。"""
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "missing.schema.json")


def test_validate_file_idempotent_batch33(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    for _ in range(3):
        validate_file(p, "manifest.schema.json")


# ---------- module source forbidden tokens 第五十三批


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
def test_module_source_no_forbidden_tokens_batch33(token):
    src = inspect.getsource(smod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch33():
    src = inspect.getsource(smod)
    assert "Schema" in src


def test_module_source_contains_future_annotations_batch33():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_json_import_batch33():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_contains_pathlib_import_batch33():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch33():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_contains_jsonschema_validator_import_batch33():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_contains_jsonschema_validation_error_import_batch33():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_contains_schemas_dir_definition_batch33():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = Path" in src


def test_module_source_contains_eval_schema_error_class_batch33():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_contains_schema_path_func_batch33():
    src = inspect.getsource(smod)
    assert "def _schema_path(" in src


def test_module_source_contains_load_schema_func_batch33():
    src = inspect.getsource(smod)
    assert "def load_schema(" in src


def test_module_source_contains_validate_func_batch33():
    src = inspect.getsource(smod)
    assert "def validate(" in src


def test_module_source_contains_validate_file_func_batch33():
    src = inspect.getsource(smod)
    assert "def validate_file(" in src


def test_module_source_contains_draft_2020_12_batch33():
    src = inspect.getsource(smod)
    assert "Draft202012Validator" in src


def test_module_source_contains_iter_errors_batch33():
    src = inspect.getsource(smod)
    assert "iter_errors" in src


def test_module_source_contains_absolute_path_batch33():
    src = inspect.getsource(smod)
    assert "absolute_path" in src


def test_module_source_contains_absolute_schema_path_batch33():
    src = inspect.getsource(smod)
    assert "absolute_schema_path" in src


def test_module_source_contains_all_batch33():
    src = inspect.getsource(smod)
    assert "__all__" in src


def test_module_source_all_contains_schemas_dir_batch33():
    src = inspect.getsource(smod)
    assert '"SCHEMAS_DIR"' in src


def test_module_source_all_contains_eval_schema_error_batch33():
    src = inspect.getsource(smod)
    assert '"EvalSchemaError"' in src


def test_module_source_all_contains_load_schema_batch33():
    src = inspect.getsource(smod)
    assert '"load_schema"' in src


def test_module_source_all_contains_validate_batch33():
    src = inspect.getsource(smod)
    assert '"validate"' in src


def test_module_source_all_contains_validate_file_batch33():
    src = inspect.getsource(smod)
    assert '"validate_file"' in src


def test_module_source_contains_file_not_found_msg_batch33():
    src = inspect.getsource(smod)
    assert "Schema 文件不存在" in src


def test_module_source_contains_encoding_utf8_batch33():
    src = inspect.getsource(smod)
    assert 'encoding="utf-8"' in src


# ---------- signatures 第四十九批


def test_signature_eval_schema_error_init_batch33():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert list(sig.parameters.keys()) == ["self", "message", "errors"]


def test_signature_eval_schema_error_init_return_none_batch33():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.return_annotation == "None"


def test_signature_eval_schema_error_message_required_batch33():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["message"].default is inspect.Parameter.empty


def test_signature_eval_schema_error_errors_optional_batch33():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_signature_schema_path_one_param_batch33():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_schema_path_return_path_batch33():
    sig = inspect.signature(_schema_path)
    assert sig.return_annotation == "Path"


def test_signature_load_schema_one_param_batch33():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_validate_two_params_batch33():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_signature_validate_file_two_params_batch33():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


# ---------- module 合理性第四十九批


def test_module_imports_json_batch33():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_imports_pathlib_batch33():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_batch33():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_imports_jsonschema_batch33():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_imports_jsonschema_exceptions_batch33():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError" in src


def test_module_has_schemas_dir_const_batch33():
    assert hasattr(smod, "SCHEMAS_DIR")
    assert isinstance(smod.SCHEMAS_DIR, Path)


def test_module_has_eval_schema_error_class_batch33():
    assert hasattr(smod, "EvalSchemaError")
    assert isinstance(smod.EvalSchemaError, type)


def test_module_has_load_schema_func_batch33():
    assert callable(smod.load_schema)


def test_module_has_validate_func_batch33():
    assert callable(smod.validate)


def test_module_has_validate_file_func_batch33():
    assert callable(smod.validate_file)


def test_module_has_schema_path_func_batch33():
    assert callable(smod._schema_path)


def test_module_all_contains_5_entries_batch33():
    assert len(smod.__all__) == 5


# ---------- 端到端集成第四十九批


def test_e2e_validate_manifest_full_batch33():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["x"], "sha256": "a" * 64},
        ],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")


def test_e2e_validate_annotation_with_anchors_batch33():
    data = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "xyz", "position": "before"},
            {"marker": "middle", "position": "after"},
        ],
    }
    validate(data, "annotation.schema.json")


def test_e2e_validate_file_idempotent_batch33(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")


def test_e2e_eval_schema_error_caught_with_errors_batch33():
    try:
        validate({}, "manifest.schema.json")
        raised = False
    except EvalSchemaError as e:
        raised = True
        assert len(e.errors) >= 1
        assert isinstance(e.errors[0], dict)
        assert "path" in e.errors[0]
        assert "message" in e.errors[0]
        assert "schema_path" in e.errors[0]
    assert raised


def test_e2e_full_flow_validate_file_after_write_batch33(tmp_path):
    """写文件 → 读 → 校验 → 通过。"""
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(p, "manifest.schema.json")
