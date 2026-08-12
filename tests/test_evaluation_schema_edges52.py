"""evaluation/schema.py 第五十三轮 edges 测试（Round 561）。

补强 edges51 未触及的角度（第三十二批）。
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


# ---------- EvalSchemaError 第三十二批


def test_eval_schema_error_super_init_with_kwargs_batch32():
    """errors 不传 → 默认空 list（不抛）。"""
    e = EvalSchemaError("msg with kwargs")
    assert e.args == ("msg with kwargs",)
    assert e.errors == []


def test_eval_schema_error_with_complex_errors_batch32():
    errs = [
        {"path": [0, "documents"], "message": "missing"},
        {"path": [1, "type"], "message": "wrong type"},
    ]
    e = EvalSchemaError("multiple", errs)
    assert len(e.errors) == 2
    assert e.errors[0]["path"] == [0, "documents"]


def test_eval_schema_error_can_be_raised_with_empty_message_batch32():
    with pytest.raises(EvalSchemaError) as exc:
        raise EvalSchemaError("")
    assert str(exc.value) == ""


def test_eval_schema_error_catch_as_value_error_batch32():
    """EvalSchemaError 不是 ValueError 子类，应当只被 Exception/自身捕获。"""
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("x")


def test_eval_schema_error_str_preserves_message_batch32():
    """message 是 unicode/ascii/特殊字符都保留。"""
    for msg in ["simple", "中文消息", "with\nnewline", "with\ttab"]:
        e = EvalSchemaError(msg)
        assert str(e) == msg


# ---------- SCHEMAS_DIR 第三十二批


def test_schemas_dir_resolved_batch32():
    """SCHEMAS_DIR 是 Path.resolve() 后的绝对路径。"""
    assert SCHEMAS_DIR.is_absolute()
    assert not ".." in str(SCHEMAS_DIR) or SCHEMAS_DIR == SCHEMAS_DIR.resolve()


def test_schemas_dir_in_project_root_batch32():
    """SCHEMAS_DIR 是 <project_root>/schemas/。"""
    # 父目录的子目录应包含 pyproject.toml
    assert (SCHEMAS_DIR.parent / "pyproject.toml").is_file()


def test_schemas_dir_contains_three_schemas_batch32():
    files = {f.name for f in SCHEMAS_DIR.iterdir() if f.is_file()}
    assert "manifest.schema.json" in files
    assert "annotation.schema.json" in files
    assert "evaluation-report.schema.json" in files


# ---------- _schema_path 第三十二批


def test_schema_path_string_argument_batch32():
    p = _schema_path("manifest.schema.json")
    assert p.name == "manifest.schema.json"
    assert p.parent == SCHEMAS_DIR


def test_schema_path_returns_absolute_batch32():
    p = _schema_path("annotation.schema.json")
    assert p.is_absolute()


def test_schema_path_file_not_found_error_message_batch32():
    with pytest.raises(FileNotFoundError) as exc:
        _schema_path("doesnotexist.schema.json")
    assert "Schema 文件不存在" in str(exc.value)
    assert "doesnotexist.schema.json" in str(exc.value)


# ---------- load_schema 第三十二批


def test_load_schema_manifest_has_properties_batch32():
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_load_schema_manifest_has_required_batch32():
    s = load_schema("manifest.schema.json")
    assert "required" in s


def test_load_schema_annotation_has_required_batch32():
    s = load_schema("annotation.schema.json")
    assert "required" in s


def test_load_schema_eval_report_has_required_batch32():
    s = load_schema("evaluation-report.schema.json")
    assert "required" in s


def test_load_schema_eval_report_has_properties_batch32():
    s = load_schema("evaluation-report.schema.json")
    assert "properties" in s


def test_load_schema_returns_dict_with_type_object_batch32():
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"):
        s = load_schema(name)
        assert s.get("type") == "object"


# ---------- validate 第三十二批


def test_validate_with_str_schema_name_batch32():
    """schema_name 接受 str。"""
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")  # no raise


def test_validate_errors_sorted_by_path_batch32():
    """errors 按 path 排序。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    # 第一个错误应按 absolute_path 排序
    errs = exc.value.errors
    paths = [tuple(e["path"]) for e in errs]
    assert paths == sorted(paths)


def test_validate_message_contains_path_batch32():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    msg = str(exc.value)
    assert "path=" in msg


def test_validate_message_contains_count_batch32():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    msg = str(exc.value)
    assert "处" in msg  # "(N 处)"


def test_validate_head_error_message_batch32():
    """错误信息含第一个 error 的 message。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    msg = str(exc.value)
    # 第一个错误是 manifest_version required
    assert "manifest_version" in msg or "required" in msg or "devset_status" in msg


def test_validate_does_not_mutate_input_batch32():
    import copy
    data = {"manifest_version": "wrong"}  # 缺字段，会失败
    data_before = copy.deepcopy(data)
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")
    assert data == data_before


def test_validate_does_not_mutate_schema_batch32():
    """重复 validate 不破坏 schema。"""
    for _ in range(3):
        with pytest.raises(EvalSchemaError):
            validate({}, "manifest.schema.json")


# ---------- validate_file 第三十二批


def test_validate_file_path_object_batch32(tmp_path):
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


def test_validate_file_returns_none_on_success_batch32(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    result = validate_file(p, "manifest.schema.json")
    assert result is None


def test_validate_file_invalid_data_raises_eval_schema_error_batch32(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_with_annotation_schema_batch32(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(
        json.dumps({"annotation_version": "1.0", "doc_id": "d1"}),
        encoding="utf-8",
    )
    validate_file(p, "annotation.schema.json")


def test_validate_file_with_eval_report_schema_batch32(tmp_path):
    """空 dict 不会通过 evaluation-report schema。"""
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "evaluation-report.schema.json")


def test_validate_file_does_not_mutate_file_batch32(tmp_path):
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
    "ctypes",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch32(token):
    src = inspect.getsource(smod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch32():
    src = inspect.getsource(smod)
    assert "Schema" in src


def test_module_source_contains_future_annotations_batch32():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_json_import_batch32():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_contains_pathlib_import_batch32():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_contains_jsonschema_validator_import_batch32():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_contains_schemas_dir_definition_batch32():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = Path" in src


def test_module_source_contains_schema_path_func_batch32():
    src = inspect.getsource(smod)
    assert "def _schema_path(" in src


def test_module_source_contains_load_schema_func_batch32():
    src = inspect.getsource(smod)
    assert "def load_schema(" in src


def test_module_source_contains_validate_func_batch32():
    src = inspect.getsource(smod)
    assert "def validate(" in src


def test_module_source_contains_validate_file_func_batch32():
    src = inspect.getsource(smod)
    assert "def validate_file(" in src


def test_module_source_contains_eval_schema_error_class_batch32():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_contains_all_batch32():
    src = inspect.getsource(smod)
    assert "__all__" in src
    assert '"SCHEMAS_DIR"' in src
    assert '"EvalSchemaError"' in src
    assert '"load_schema"' in src
    assert '"validate"' in src
    assert '"validate_file"' in src


# ---------- signatures 第四十九批


def test_signature_eval_schema_error_init_batch32():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert list(sig.parameters.keys()) == ["self", "message", "errors"]


def test_signature_eval_schema_error_errors_optional_batch32():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_signature_schema_path_one_param_batch32():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_load_schema_one_param_batch32():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_validate_two_params_batch32():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_signature_validate_file_two_params_batch32():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_signature_load_schema_return_annotation_batch32():
    sig = inspect.signature(load_schema)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_validate_return_none_batch32():
    sig = inspect.signature(validate)
    assert sig.return_annotation == "None"


# ---------- module 合理性第四十九批


def test_module_imports_json_batch32():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_imports_pathlib_batch32():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_imports_jsonschema_batch32():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_imports_typing_any_batch32():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_has_schemas_dir_const_batch32():
    assert hasattr(smod, "SCHEMAS_DIR")
    assert isinstance(smod.SCHEMAS_DIR, Path)


def test_module_has_all_with_five_entries_batch32():
    assert len(smod.__all__) == 5


# ---------- 端到端集成第四十九批


def test_e2e_validate_manifest_with_one_document_batch32():
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["x"]}
        ],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")


def test_e2e_validate_annotation_full_batch32():
    data = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "xyz", "position": "before"},
        ],
    }
    validate(data, "annotation.schema.json")


def test_e2e_validate_file_idempotent_batch32(tmp_path):
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
    validate_file(p, "manifest.schema.json")


def test_e2e_eval_schema_error_caught_batch32():
    try:
        validate({}, "manifest.schema.json")
        raised = False
    except EvalSchemaError as e:
        raised = True
        assert "manifest.schema.json" in str(e)
        assert len(e.errors) >= 1
    assert raised


def test_e2e_validate_with_pathlib_path_input_batch32(tmp_path):
    from evaluation import MANIFEST_VERSION
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    # validate_file 接受 Path 对象
    validate_file(p, "manifest.schema.json")
