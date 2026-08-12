"""evaluation/schema.py 第五十二轮 edges 测试（Round 554）。

补强 edges50 未触及的角度（第三十一批）。
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


# ---------- EvalSchemaError 第三十一批


def test_eval_schema_error_errors_default_empty_each_instance_batch31():
    """errors 默认空 list，每个实例独立。"""
    e1 = EvalSchemaError("m1")
    e2 = EvalSchemaError("m2")
    e1.errors.append({"a": 1})
    assert e2.errors == []


def test_eval_schema_error_no_args_batch31():
    """message 是必需参数。"""
    with pytest.raises(TypeError):
        EvalSchemaError()


def test_eval_schema_error_with_empty_errors_list_batch31():
    e = EvalSchemaError("msg", [])
    assert e.errors == []


def test_eval_schema_error_with_errors_batch31():
    errs = [{"path": [0], "message": "x"}]
    e = EvalSchemaError("msg", errs)
    assert e.errors == errs


def test_eval_schema_error_is_exception_batch31():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_catch_by_exception_batch31():
    with pytest.raises(Exception):
        raise EvalSchemaError("x")


def test_eval_schema_error_raise_with_no_message_batch31():
    """message 必填，不可空构造。"""
    with pytest.raises(TypeError):
        raise EvalSchemaError()


def test_eval_schema_error_attributes_immutable_batch31():
    """errors 属性可写但默认值是新 list（不是共享类变量）。"""
    e = EvalSchemaError("msg")
    assert isinstance(e.errors, list)
    e.errors.append("x")
    assert "x" in e.errors


def test_eval_schema_error_module_class_batch31():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


# ---------- SCHEMAS_DIR 第三十一批


def test_schemas_dir_is_path_batch31():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_absolute_batch31():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_endswith_schemas_batch31():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_parent_has_pyproject_batch31():
    """父目录应包含 pyproject.toml（项目根）。"""
    assert (SCHEMAS_DIR.parent / "pyproject.toml").is_file()


def test_schemas_dir_contains_manifest_schema_batch31():
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema_batch31():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_eval_report_schema_batch31():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


# ---------- _schema_path 第三十一批


def test_schema_path_existing_batch31():
    p = _schema_path("manifest.schema.json")
    assert p.is_file()
    assert p.name == "manifest.schema.json"


def test_schema_path_missing_raises_batch31():
    with pytest.raises(FileNotFoundError) as exc:
        _schema_path("nonexistent.schema.json")
    assert "不存在" in str(exc.value)


def test_schema_path_returns_path_batch31():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_in_schemas_dir_batch31():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_str_name_batch31():
    p = _schema_path("manifest.schema.json")
    assert p.name == "manifest.schema.json"


# ---------- load_schema 第三十一批


def test_load_schema_returns_dict_batch31():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_manifest_has_type_batch31():
    s = load_schema("manifest.schema.json")
    assert s.get("type") == "object"


def test_load_schema_annotation_has_type_batch31():
    s = load_schema("annotation.schema.json")
    assert s.get("type") == "object"


def test_load_schema_eval_report_has_type_batch31():
    s = load_schema("evaluation-report.schema.json")
    assert s.get("type") == "object"


def test_load_schema_missing_raises_batch31():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_idempotent_batch31():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2


# ---------- validate 第三十一批


def test_validate_manifest_empty_dict_fails_batch31():
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_annotation_empty_dict_fails_batch31():
    with pytest.raises(EvalSchemaError):
        validate({}, "annotation.schema.json")


def test_validate_eval_report_empty_dict_fails_batch31():
    with pytest.raises(EvalSchemaError):
        validate({}, "evaluation-report.schema.json")


def test_validate_invalid_schema_name_raises_batch31():
    with pytest.raises(FileNotFoundError):
        validate({}, "nonexistent.schema.json")


def test_validate_minimal_manifest_batch31():
    """完整 manifest 应通过校验。"""
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")  # no raise


def test_validate_minimal_annotation_batch31():
    """完整 annotation 应通过校验。"""
    data = {
        "annotation_version": "1.0",
        "doc_id": "d1",
    }
    validate(data, "annotation.schema.json")  # no raise


def test_validate_eval_report_error_has_errors_attr_batch31():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert hasattr(exc.value, "errors")
    assert isinstance(exc.value.errors, list)


def test_validate_eval_report_error_message_contains_schema_name_batch31():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc.value)


def test_validate_eval_report_error_count_batch31():
    """错误数 ≥1。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert len(exc.value.errors) >= 1


def test_validate_error_item_has_path_message_schema_path_batch31():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    err = exc.value.errors[0]
    assert "path" in err
    assert "message" in err
    assert "schema_path" in err


# ---------- validate_file 第三十一批


def test_validate_file_existing_valid_batch31(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(p, "manifest.schema.json")  # no raise


def test_validate_file_existing_invalid_batch31(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_missing_raises_file_not_found_batch31(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "nonexistent.json", "manifest.schema.json")


def test_validate_file_str_path_batch31(tmp_path):
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


def test_validate_file_invalid_json_raises_json_decode_batch31(tmp_path):
    """非 JSON 文件 → json.JSONDecodeError（不捕获）。"""
    p = tmp_path / "m.json"
    p.write_text("not json {", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_str_schema_name_batch31(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(p, str("manifest.schema.json"))


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
    "urllib",
    "socket",
    "pty.",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch31(token):
    src = inspect.getsource(smod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch31():
    src = inspect.getsource(smod)
    assert "加载并校验" in src


def test_module_source_contains_future_annotations_batch31():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_json_import_batch31():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_contains_pathlib_import_batch31():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_import_batch31():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_contains_jsonschema_import_batch31():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_contains_jsvalidationerror_import_batch31():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_contains_schemas_dir_const_batch31():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = " in src


def test_module_source_contains_eval_schema_error_class_batch31():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_contains_schema_path_func_batch31():
    src = inspect.getsource(smod)
    assert "def _schema_path(" in src


def test_module_source_contains_load_schema_func_batch31():
    src = inspect.getsource(smod)
    assert "def load_schema(" in src


def test_module_source_contains_validate_func_batch31():
    src = inspect.getsource(smod)
    assert "def validate(" in src


def test_module_source_contains_validate_file_func_batch31():
    src = inspect.getsource(smod)
    assert "def validate_file(" in src


def test_module_source_contains_draft_validator_call_batch31():
    src = inspect.getsource(smod)
    assert "Draft202012Validator(" in src


def test_module_source_contains_iter_errors_call_batch31():
    src = inspect.getsource(smod)
    assert "iter_errors(" in src


def test_module_source_contains_absolute_path_batch31():
    src = inspect.getsource(smod)
    assert "absolute_path" in src


def test_module_source_contains_all_batch31():
    src = inspect.getsource(smod)
    assert "__all__" in src
    assert '"SCHEMAS_DIR"' in src
    assert '"EvalSchemaError"' in src
    assert '"load_schema"' in src
    assert '"validate"' in src
    assert '"validate_file"' in src


# ---------- signatures 第四十九批


def test_signature_eval_schema_error_params_batch31():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    # self, message, errors
    assert params == ["self", "message", "errors"]


def test_signature_eval_schema_error_errors_default_none_batch31():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_signature_schema_path_params_batch31():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_load_schema_params_batch31():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_validate_params_batch31():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_signature_validate_file_params_batch31():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_signature_load_schema_return_dict_batch31():
    sig = inspect.signature(load_schema)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_validate_return_none_batch31():
    sig = inspect.signature(validate)
    assert sig.return_annotation == "None"


def test_signature_validate_file_return_none_batch31():
    sig = inspect.signature(validate_file)
    assert sig.return_annotation == "None"


# ---------- module 合理性第四十九批


def test_module_has_future_annotations_batch31():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch31():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_has_eval_schema_error_class_batch31():
    assert hasattr(smod, "EvalSchemaError")
    assert issubclass(smod.EvalSchemaError, Exception)


def test_module_has_schemas_dir_const_batch31():
    assert hasattr(smod, "SCHEMAS_DIR")


def test_module_has_load_schema_func_batch31():
    assert callable(smod.load_schema)


def test_module_has_validate_func_batch31():
    assert callable(smod.validate)


def test_module_has_validate_file_func_batch31():
    assert callable(smod.validate_file)


def test_module_has_all_batch31():
    assert hasattr(smod, "__all__")
    assert "SCHEMAS_DIR" in smod.__all__
    assert "EvalSchemaError" in smod.__all__
    assert "load_schema" in smod.__all__
    assert "validate" in smod.__all__
    assert "validate_file" in smod.__all__


# ---------- 端到端集成第四十九批


def test_e2e_validate_full_manifest_batch31():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [
            {"doc_id": "bad1", "path": "bad.pdf", "expected_error_code": "E_PARSE"}
        ],
    }
    validate(data, "manifest.schema.json")  # no raise


def test_e2e_validate_full_annotation_batch31():
    data = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"}
        ],
    }
    validate(data, "annotation.schema.json")  # no raise


def test_e2e_idempotent_batch31():
    """同一 instance 重复校验结果一致。"""
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")
    validate(data, "manifest.schema.json")


def test_e2e_validate_file_idempotent_batch31(tmp_path):
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


def test_e2e_eval_schema_error_caught_batch31():
    """EvalSchemaError 可被 try/except 捕获。"""
    try:
        validate({}, "manifest.schema.json")
        raised = False
    except EvalSchemaError as e:
        raised = True
        assert "manifest.schema.json" in str(e)
    assert raised


def test_e2e_eval_schema_error_with_full_errors_attr_batch31():
    """错误对象的 errors 列表是详细的错误字典。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err, dict)
        assert "path" in err
        assert "message" in err
        assert "schema_path" in err
