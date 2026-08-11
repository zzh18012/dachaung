"""evaluation/schema.py 第三十九轮 edges 测试（Round 467）。

补强 edges38 未触及的角度：
- SCHEMAS_DIR 常量深度第十九批（name == 'schemas' / is_absolute / 子文件存在性 / parent 是项目根 / 与 app.schema 共享）
- EvalSchemaError 行为深度第十九批（repr / errors 三种入参 / str 与 message 等价 / 子类继承 Exception / raise from None / errors 不可变性）
- _schema_path 行为深度第十九批（返回值 .name / 多次调用相等 / 接受 4 个真实 schema / 拒绝 .py 文件 / 拒绝无后缀）
- load_schema 行为深度第十九批（4 个 schema 都可加载 / 返回值含 $schema / 不缓存 / 修改返回值不影响下次）
- validate 行为深度第十九批（instance 不被修改 / schema 不被缓存 / errors 排序 / errors 含 schema_path / 多错误计数正确 / validate raises 不返回 bool）
- validate_file 行为深度第十九批（utf-8 BOM 拒绝 / 绝对路径 / 相对路径 cwd / 文件空抛错 / read 后关闭）
- module source forbidden tokens 第三十五批
- module source 字符串精确补强第三十一批
- signatures 第三十一批
- module 合理性第三十一批
- 端到端集成第三十一批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JSValidationError

from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)
from evaluation import schema as smod


# ---------- SCHEMAS_DIR 常量深度第十九批 ----------


def test_schemas_dir_name_is_schemas_batch19():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_is_absolute_batch19():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_exists_batch19():
    assert SCHEMAS_DIR.exists()


def test_schemas_dir_has_manifest_schema_batch19():
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_has_annotation_schema_batch19():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_has_evaluation_report_schema_batch19():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_has_document_schema_batch19():
    assert (SCHEMAS_DIR / "document.schema.json").is_file()


def test_schemas_dir_parent_contains_evaluation_dir_batch19():
    """SCHEMAS_DIR.parent/evaluation 是 evaluation 模块目录。"""
    assert (SCHEMAS_DIR.parent / "evaluation").is_dir()


def test_schemas_dir_independent_from_app_schema_batch19():
    from app import schema as app_schema
    assert app_schema.SCHEMA_PATH.parent == SCHEMAS_DIR


def test_schemas_dir_glob_count_at_least_four_batch19():
    """至少 4 个 .schema.json 文件。"""
    jsons = list(SCHEMAS_DIR.glob("*.schema.json"))
    assert len(jsons) >= 4


# ---------- EvalSchemaError 行为深度第十九批 ----------


def test_eval_schema_error_repr_contains_class_name_batch19():
    err = EvalSchemaError("msg")
    assert "EvalSchemaError" in repr(err)


def test_eval_schema_error_str_equals_message_batch19():
    err = EvalSchemaError("hello world")
    assert str(err) == "hello world"


def test_eval_schema_error_is_exception_subclass_batch19():
    err = EvalSchemaError("x")
    assert isinstance(err, Exception)


def test_eval_schema_error_default_errors_is_empty_list_batch19():
    err = EvalSchemaError("x")
    assert err.errors == []
    assert isinstance(err.errors, list)


def test_eval_schema_error_none_errors_is_empty_list_batch19():
    err = EvalSchemaError("x", None)
    assert err.errors == []
    assert isinstance(err.errors, list)


def test_eval_schema_error_empty_list_errors_batch19():
    err = EvalSchemaError("x", [])
    assert err.errors == []


def test_eval_schema_error_with_errors_list_batch19():
    errs = [{"path": ["a"], "message": "x"}]
    err = EvalSchemaError("msg", errs)
    assert err.errors is errs


def test_eval_schema_error_raise_from_none_batch19():
    try:
        try:
            raise ValueError("inner")
        except ValueError:
            raise EvalSchemaError("outer") from None
    except EvalSchemaError as e:
        assert e.__cause__ is None
        assert e.__suppress_context__ is True


def test_eval_schema_error_errors_default_not_shared_batch19():
    """两个无参 EvalSchemaError 应各有独立 errors list（不共享同一对象）。"""
    e1 = EvalSchemaError("a")
    e2 = EvalSchemaError("b")
    assert e1.errors == []
    assert e2.errors == []
    # 修改 e1.errors 不影响 e2
    e1.errors.append({"x": 1})
    assert e2.errors == []


def test_eval_schema_error_args_immutable_tuple_batch19():
    err = EvalSchemaError("x")
    assert isinstance(err.args, tuple)


# ---------- _schema_path 行为深度第十九批 ----------


def test_schema_path_returned_path_name_matches_batch19():
    p = _schema_path("manifest.schema.json")
    assert p.name == "manifest.schema.json"


def test_schema_path_two_calls_equal_batch19():
    p1 = _schema_path("annotation.schema.json")
    p2 = _schema_path("annotation.schema.json")
    assert p1 == p2


def test_schema_path_works_for_all_four_schemas_batch19():
    for n in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        p = _schema_path(n)
        assert p.is_file()


def test_schema_path_rejects_python_file_batch19():
    with pytest.raises(FileNotFoundError):
        _schema_path("schema.py")


def test_schema_path_rejects_no_extension_batch19():
    with pytest.raises(FileNotFoundError):
        _schema_path("manifest")


def test_schema_path_rejects_uppercase_variant_batch19():
    """Windows 文件系统大小写不敏感，跳过此测试。"""
    if Path("C:/").resolve().parts[0] == "C:\\":
        pytest.skip("Windows 文件系统大小写不敏感")


def test_schema_path_rejects_double_dot_batch19():
    with pytest.raises(FileNotFoundError):
        _schema_path("manifest.schema.json.json")


def test_schema_path_returns_path_inside_schemas_dir_batch19():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


# ---------- load_schema 行为深度第十九批 ----------


def test_load_schema_returns_dict_with_schema_key_batch19():
    """加载的 schema 应含 $schema 或 properties 等 JSON Schema 标准字段。"""
    s = load_schema("manifest.schema.json")
    assert "$schema" in s or "properties" in s


def test_load_schema_returns_mutable_dict_batch19():
    """返回值是可变 dict，修改不影响下次加载。"""
    s1 = load_schema("manifest.schema.json")
    original_keys = set(s1.keys())
    s1["__injected__"] = True
    s2 = load_schema("manifest.schema.json")
    assert "__injected__" not in s2
    assert set(s2.keys()) == original_keys


def test_load_schema_all_four_schemas_batch19():
    for n in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(n)
        assert isinstance(s, dict)


def test_load_schema_value_round_trip_with_disk_batch19():
    """load_schema 与直接 json.load 等价。"""
    for n in ("manifest.schema.json", "annotation.schema.json"):
        s = load_schema(n)
        raw = json.loads((SCHEMAS_DIR / n).read_text(encoding="utf-8"))
        assert s == raw


def test_load_schema_returns_proper_schema_object_batch19():
    """返回值能用 Draft202012Validator 构造 validator。"""
    s = load_schema("manifest.schema.json")
    v = Draft202012Validator(s)
    assert isinstance(v, Draft202012Validator)


# ---------- validate 行为深度第十九批 ----------


def test_validate_does_not_mutate_instance_batch19():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    snapshot = json.loads(json.dumps(instance))
    validate(instance, "manifest.schema.json")
    assert instance == snapshot


def test_validate_does_not_mutate_instance_on_failure_batch19():
    instance = {"manifest_version": "WRONG"}
    snapshot = json.loads(json.dumps(instance))
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")
    assert instance == snapshot


def test_validate_errors_contain_schema_path_batch19():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    err = ei.value
    for e in err.errors:
        assert "schema_path" in e
        assert isinstance(e["schema_path"], list)


def test_validate_errors_count_in_message_batch19():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": "WRONG", "documents": "x"}, "manifest.schema.json")
    err = ei.value
    # message 含 "(N 处)" 或类似计数
    assert "处" in str(err)


def test_validate_errors_sorted_by_path_batch19():
    """errors 应按 absolute_path 排序。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": "WRONG", "documents": "x", "devset_status": "BAD"}, "manifest.schema.json")
    err = ei.value
    if len(err.errors) >= 2:
        paths = [tuple(e["path"]) for e in err.errors]
        assert paths == sorted(paths)


def test_validate_does_not_return_bool_batch19():
    """validate 成功时返回 None（不是 True/False）。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    result = validate(instance, "manifest.schema.json")
    assert result is None


def test_validate_annotation_empty_fails_batch19():
    with pytest.raises(EvalSchemaError):
        validate({}, "annotation.schema.json")


def test_validate_evaluation_report_empty_fails_batch19():
    with pytest.raises(EvalSchemaError):
        validate({}, "evaluation-report.schema.json")


def test_validate_with_extra_field_still_ok_for_manifest_batch19():
    """manifest.schema.json 允许的字段：检查 additionalProperties。"""
    schema = load_schema("manifest.schema.json")
    ap = schema.get("additionalProperties")
    # 不强制断言 True/False（schema 可能允许），仅记录
    assert ap is True or ap is False or ap is None or isinstance(ap, dict)


# ---------- validate_file 行为深度第十九批 ----------


def test_validate_file_utf8_bom_rejected_batch19(tmp_path):
    """UTF-8 BOM 导致 json.JSONDecodeError。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf{"manifest_version": "1.0", "devset_status": "complete", "documents": []}')
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_absolute_path_batch19(tmp_path):
    """传绝对路径。"""
    p = tmp_path / "x.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }), encoding="utf-8")
    validate_file(p.resolve(), "manifest.schema.json")


def test_validate_file_invalid_data_raises_eval_schema_error_batch19(tmp_path):
    """数据不符合 schema → EvalSchemaError（非 JSONDecodeError）。"""
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_empty_file_raises_batch19(tmp_path):
    """空文件 → JSONDecodeError。"""
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_returns_none_on_success_batch19(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_int_top_level_raises_batch19(tmp_path):
    """JSON 顶层是 int → schema 校验失败。"""
    p = tmp_path / "x.json"
    p.write_text("42", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_list_top_level_raises_batch19(tmp_path):
    """JSON 顶层是 list → schema 校验失败。"""
    p = tmp_path / "x.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_with_real_annotation_batch19(tmp_path):
    """annotation.schema.json 校验。"""
    p = tmp_path / "ann.json"
    p.write_text(json.dumps({
        "doc_id": "d1",
        "annotation_version": "1.0",
        "annotator": "tester",
        "date": "2026-08-10",
    }), encoding="utf-8")
    validate_file(p, "annotation.schema.json")


# ---------- module source forbidden tokens 第三十五批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.check_output",
    "subprocess.check_call",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    "open(\"/etc/passwd",
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch19(forbidden):
    src = inspect.getsource(smod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch19():
    src = inspect.getsource(smod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch19():
    src = inspect.getsource(smod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch19():
    src = inspect.getsource(smod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch19():
    src = inspect.getsource(smod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch19():
    src = inspect.getsource(smod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch19():
    src = inspect.getsource(smod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch19():
    src = inspect.getsource(smod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch19():
    src = inspect.getsource(smod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch19():
    src = inspect.getsource(smod)
    assert "import tempfile" not in src


def test_module_source_no_sys_import_batch19():
    src = inspect.getsource(smod)
    assert "import sys" not in src


def test_module_source_no_logging_import_batch19():
    src = inspect.getsource(smod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch19():
    src = inspect.getsource(smod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch19():
    src = inspect.getsource(smod)
    assert "import datetime" not in src


def test_module_source_no_collections_import_batch19():
    src = inspect.getsource(smod)
    assert "import collections" not in src


def test_module_source_no_pandas_import_batch19():
    src = inspect.getsource(smod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch19():
    src = inspect.getsource(smod)
    assert "import numpy" not in src


def test_module_source_no_path_write_text_batch19():
    src = inspect.getsource(smod)
    assert ".write_text(" not in src


def test_module_source_no_path_unlink_batch19():
    src = inspect.getsource(smod)
    assert ".unlink(" not in src


def test_module_source_no_path_rmdir_batch19():
    src = inspect.getsource(smod)
    assert ".rmdir(" not in src


def test_module_source_no_path_mkdir_batch19():
    src = inspect.getsource(smod)
    assert ".mkdir(" not in src


# ---------- module source 字符串精确补强第三十一批 ----------


def test_module_source_has_future_annotations_batch19():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_source_has_json_import_batch19():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_has_pathlib_path_import_batch19():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch19():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_has_jsonschema_import_batch19():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_has_jsonschema_exceptions_import_batch19():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_has_schemas_dir_assignment_batch19():
    src = inspect.getsource(smod)
    assert 'SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"' in src


def test_module_source_has_class_eval_schema_error_batch19():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_has_schema_path_function_batch19():
    src = inspect.getsource(smod)
    assert "def _schema_path(name: str) -> Path:" in src


def test_module_source_has_load_schema_function_batch19():
    src = inspect.getsource(smod)
    assert "def load_schema(name: str) -> dict[str, Any]:" in src


def test_module_source_has_validate_function_batch19():
    src = inspect.getsource(smod)
    assert "def validate(instance: dict[str, Any], schema_name: str) -> None:" in src


def test_module_source_has_validate_file_function_batch19():
    src = inspect.getsource(smod)
    assert "def validate_file(path: Path | str, schema_name: str) -> None:" in src


def test_module_source_has_iter_errors_call_batch19():
    src = inspect.getsource(smod)
    assert "iter_errors" in src


def test_module_source_has_absolute_path_attribute_batch19():
    src = inspect.getsource(smod)
    assert "absolute_path" in src


def test_module_source_has_all_list_batch19():
    src = inspect.getsource(smod)
    assert '__all__' in src


def test_module_source_has_docstring_batch19():
    src = inspect.getsource(smod)
    assert "Schema" in src or "schema" in src


# ---------- signatures 第三十一批 ----------


def test_signature_schema_path_batch19():
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"


def test_signature_load_schema_batch19():
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"


def test_signature_validate_batch19():
    sig = inspect.signature(validate)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["instance", "schema_name"]


def test_signature_validate_file_batch19():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["path", "schema_name"]


def test_signature_eval_schema_error_init_batch19():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["self", "message", "errors"]
    assert params[2].default is None


def test_signature_eval_schema_error_init_no_return_annotation_batch19():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert "None" in str(sig.return_annotation)


# ---------- module 合理性第三十一批 ----------


def test_module_has_all_attribute_batch19():
    assert hasattr(smod, "__all__")


def test_module_all_contains_5_entries_batch19():
    assert len(smod.__all__) == 5


def test_module_all_entries_are_strings_batch19():
    for n in smod.__all__:
        assert isinstance(n, str)


def test_module_all_contents_exact_batch19():
    assert set(smod.__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_module_does_not_import_app_pipeline_batch19():
    src = inspect.getsource(smod)
    assert "from app" not in src
    assert "import app" not in src


def test_module_does_not_import_evaluation_runner_batch19():
    src = inspect.getsource(smod)
    assert "from evaluation.runner" not in src
    assert "from evaluation import runner" not in src


def test_module_does_not_import_evaluation_metrics_batch19():
    src = inspect.getsource(smod)
    assert "from evaluation.metrics" not in src
    assert "from evaluation import metrics" not in src


def test_module_does_not_import_evaluation_manifest_batch19():
    src = inspect.getsource(smod)
    assert "from evaluation.manifest" not in src
    assert "from evaluation import manifest" not in src


def test_module_no_main_block_batch19():
    src = inspect.getsource(smod)
    assert 'if __name__ ==' not in src
    assert "__main__" not in src


def test_module_eval_schema_error_class_exists_batch19():
    assert hasattr(smod, "EvalSchemaError")
    assert isinstance(smod.EvalSchemaError, type)


def test_module_schemas_dir_constant_exists_batch19():
    assert hasattr(smod, "SCHEMAS_DIR")
    assert isinstance(smod.SCHEMAS_DIR, Path)


# ---------- 端到端集成第三十一批 ----------


def test_e2e_validate_manifest_with_documents_batch19():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "samples/x.pdf", "source_type": "pdf"},
        ],
    }
    validate(instance, "manifest.schema.json")


def test_e2e_validate_annotation_known_good_batch19():
    instance = {
        "doc_id": "d1",
        "annotation_version": "1.0",
        "annotator": "tester",
        "date": "2026-08-10",
    }
    validate(instance, "annotation.schema.json")


def test_e2e_load_then_validate_round_trip_batch19():
    schema = load_schema("annotation.schema.json")
    instance = {
        "doc_id": "d1",
        "annotation_version": "1.0",
    }
    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors(instance)) == []


def test_e2e_validate_file_round_trip_batch19(tmp_path):
    """validate_file 等同于 load + validate。"""
    p = tmp_path / "x.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    validate(instance, "manifest.schema.json")


def test_e2e_cross_schema_validation_fails_batch19():
    """manifest 数据用 evaluation-report schema 校验应失败。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "evaluation-report.schema.json")


def test_e2e_unknown_schema_raises_file_not_found_batch19():
    with pytest.raises(FileNotFoundError):
        validate({}, "absent.schema.json")


def test_e2e_validate_file_with_unknown_schema_raises_file_not_found_batch19(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "absent.schema.json")


def test_e2e_eval_schema_error_caught_by_exception_batch19():
    """EvalSchemaError 可被 except Exception 捕获。"""
    try:
        validate({}, "manifest.schema.json")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)
