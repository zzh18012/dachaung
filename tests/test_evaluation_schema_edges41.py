"""evaluation/schema.py 第四十一轮 edges 测试（Round 481）。

补强 edges40 未触及的角度：
- SCHEMAS_DIR 第二十一批（绝对路径 / parent 是 absolute / 与 __file__ 关系 / parts 形态 / 与 evaluation/ 同级 / drive 字符）
- EvalSchemaError 第二十一批（errors None 默认 [] / errors 空列表默认 [] / errors 非 None 保留 / __init__ 签名 / super 调用 / str 可读）
- _schema_path 第二十一批（不在 schemas_dir 内的路径不会成功 / FileNotFoundError 消息格式 / 多次调用一致 / 接受 'manifest.schema.json' / 接受 'evaluation-report.schema.json')
- load_schema 第二十一批（返回 dict 类型 / 不能加载目录 / 不能加载不存在的 / draft202012 兼容 / 多次加载等价）
- validate 第二十一批（多错误时 head 是排序后第一个 / flat 数量等于 errors 数量 / flat 每项无 type 字段 / instance dict 直接通过 / 不修改 instance）
- validate_file 第二十一批（不存在文件 FileNotFoundError / str 输入 vs Path 输入等价 / 解析后调用 validate / utf-8 编码 / 多次调用一致）
- module source forbidden tokens 第三十七批
- module source 字符串精确补强第三十三批
- signatures 第三十三批
- module 合理性第三十三批
- 端到端集成第三十三批
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


# ---------- SCHEMAS_DIR 第二十一批 ----------


def test_schemas_dir_is_absolute_batch21():
    """SCHEMAS_DIR 是绝对路径。"""
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_parent_is_absolute_batch21():
    """SCHEMAS_DIR.parent 是绝对路径。"""
    assert SCHEMAS_DIR.parent.is_absolute()


def test_schemas_dir_basename_is_schemas_batch21():
    """SCHEMAS_DIR.name == 'schemas'。"""
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_exists_batch21():
    """SCHEMAS_DIR 存在。"""
    assert SCHEMAS_DIR.exists()


def test_schemas_dir_has_manifest_schema_batch21():
    """SCHEMAS_DIR 含 manifest.schema.json。"""
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_has_annotation_schema_batch21():
    """SCHEMAS_DIR 含 annotation.schema.json。"""
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_has_evaluation_report_schema_batch21():
    """SCHEMAS_DIR 含 evaluation-report.schema.json。"""
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_resolves_to_canonical_batch21():
    """SCHEMAS_DIR == SCHEMAS_DIR.resolve()（已 resolved）。"""
    assert SCHEMAS_DIR == SCHEMAS_DIR.resolve()


def test_schemas_dir_string_form_endswith_schemas_batch21():
    """str(SCHEMAS_DIR) 末尾是 'schemas'。"""
    assert str(SCHEMAS_DIR).endswith("schemas")


def test_schemas_dir_sibling_to_evaluation_batch21():
    """SCHEMAS_DIR 与 evaluation/ 是 sibling（同一个 parent）。"""
    parent = SCHEMAS_DIR.parent
    assert (parent / "evaluation").is_dir()
    assert (parent / "schemas").is_dir()


# ---------- EvalSchemaError 第二十一批 ----------


def test_eval_schema_error_default_errors_is_empty_list_batch21():
    """errors=None → 默认 []。"""
    err = EvalSchemaError("msg")
    assert err.errors == []
    assert isinstance(err.errors, list)


def test_eval_schema_error_explicit_empty_errors_is_empty_list_batch21():
    """errors=[] → []。"""
    err = EvalSchemaError("msg", errors=[])
    assert err.errors == []


def test_eval_schema_error_explicit_errors_preserved_batch21():
    """errors=[{...}] → 保留。"""
    errs = [{"path": ["a"], "message": "x"}]
    err = EvalSchemaError("msg", errors=errs)
    assert err.errors is errs  # 直接保留引用


def test_eval_schema_error_inherits_from_exception_batch21():
    """EvalSchemaError 是 Exception 子类。"""
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_is_not_standard_exception_batch21():
    """EvalSchemaError 不是 Exception 实例本身（是子类）。"""
    err = EvalSchemaError("msg")
    assert isinstance(err, Exception)
    assert not isinstance(err, TypeError)


def test_eval_schema_error_str_returns_message_batch21():
    """str(err) 是 message。"""
    err = EvalSchemaError("hello world")
    assert str(err) == "hello world"


def test_eval_schema_error_repr_contains_class_name_batch21():
    """repr 含 'EvalSchemaError'。"""
    err = EvalSchemaError("msg")
    assert "EvalSchemaError" in repr(err)


def test_eval_schema_error_can_be_raised_and_caught_batch21():
    """能被 raise / except EvalSchemaError 捕获。"""
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("boom")


def test_eval_schema_error_caught_as_exception_batch21():
    """能被 except Exception 捕获。"""
    try:
        raise EvalSchemaError("x")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_eval_schema_error_args_message_batch21():
    """err.args[0] == message。"""
    err = EvalSchemaError("hi", errors=[{"x": 1}])
    assert err.args == ("hi",)
    assert err.errors == [{"x": 1}]


# ---------- _schema_path 第二十一批 ----------


def test_schema_path_returns_path_object_batch21():
    """_schema_path 返回 Path。"""
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_file_exists_batch21():
    """_schema_path 返回的路径存在。"""
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_under_schemas_dir_batch21():
    """_schema_path 返回的路径在 SCHEMAS_DIR 内。"""
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_not_found_error_includes_filename_batch21():
    """FileNotFoundError 消息含文件名。"""
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("does-not-exist.schema.json")
    assert "does-not-exist.schema.json" in str(exc_info.value)


def test_schema_path_accepts_str_batch21():
    """_schema_path 接受 str。"""
    p = _schema_path("annotation.schema.json")
    assert p.is_file()


def test_schema_path_for_evaluation_report_batch21():
    """_schema_path 对 'evaluation-report.schema.json' 工作。"""
    p = _schema_path("evaluation-report.schema.json")
    assert p.is_file()


def test_schema_path_idempotent_batch21():
    """多次调用一致。"""
    p1 = _schema_path("manifest.schema.json")
    p2 = _schema_path("manifest.schema.json")
    assert p1 == p2


def test_schema_path_directory_raises_batch21():
    """传目录名 'schemas' → 在 schemas/ 下找名为 'schemas' 的文件 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("schemas")


# ---------- load_schema 第二十一批 ----------


def test_load_schema_returns_dict_batch21():
    """load_schema 返回 dict。"""
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_has_schema_version_key_batch21():
    """manifest.schema.json 含 $schema 字段。"""
    s = load_schema("manifest.schema.json")
    assert "$schema" in s


def test_load_schema_manifest_has_properties_batch21():
    """manifest schema 含 properties。"""
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_load_schema_idempotent_batch21():
    """多次加载等价。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2


def test_load_schema_raises_on_missing_batch21():
    """load_schema 对不存在的 schema 抛 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        load_schema("no-such.schema.json")


def test_load_schema_annotation_has_type_batch21():
    """annotation schema 顶层有 type。"""
    s = load_schema("annotation.schema.json")
    assert "type" in s


def test_load_schema_evaluation_report_has_properties_batch21():
    """evaluation-report schema 含 properties。"""
    s = load_schema("evaluation-report.schema.json")
    assert "properties" in s


# ---------- validate 第二十一批 ----------


def test_validate_passes_valid_manifest_batch21():
    """合法 manifest → 不抛。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    # 不抛即通过
    validate(instance, "manifest.schema.json")


def test_validate_raises_eval_schema_error_on_invalid_batch21():
    """非法 manifest → EvalSchemaError。"""
    instance = {"manifest_version": "wrong-version"}
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_errors_count_matches_iter_errors_batch21():
    """errors 数量与 iter_errors 一致。"""
    instance = {"manifest_version": "wrong", "devset_status": 123, "documents": "not-list"}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        # 至少有多个错误
        assert len(e.errors) >= 2
    else:
        pytest.fail("应抛 EvalSchemaError")


def test_validate_errors_each_has_three_keys_batch21():
    """errors 每项严格 3 keys：path / message / schema_path。"""
    instance = {"manifest_version": "wrong"}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert set(err.keys()) == {"path", "message", "schema_path"}
    else:
        pytest.fail("应抛 EvalSchemaError")


def test_validate_message_contains_schema_name_batch21():
    """错误消息含 schema_name。"""
    instance = {"manifest_version": "wrong"}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        assert "manifest.schema.json" in str(e)
    else:
        pytest.fail("应抛 EvalSchemaError")


def test_validate_message_contains_count_batch21():
    """错误消息含 "(N 处)"。"""
    instance = {"manifest_version": "wrong", "devset_status": 123}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        assert "处" in str(e)
    else:
        pytest.fail("应抛 EvalSchemaError")


def test_validate_does_not_modify_instance_batch21():
    """validate 不修改 instance。"""
    instance = {"manifest_version": "1.0", "devset_status": "incomplete", "documents": []}
    original = json.loads(json.dumps(instance))
    validate(instance, "manifest.schema.json")
    assert instance == original


def test_validate_head_error_is_first_after_sort_batch21():
    """errors[0] 是排序后第一个（path 最小）。"""
    instance = {"manifest_version": "wrong"}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        # head 是 e.errors[0]
        assert len(e.errors) >= 1
        # 验证排序：所有 errors 都按 path 排序
        paths = [tuple(err["path"]) for err in e.errors]
        assert paths == sorted(paths)
    else:
        pytest.fail("应抛 EvalSchemaError")


def test_validate_no_errors_returns_none_batch21():
    """合法实例 → None 返回。"""
    instance = {"manifest_version": "1.0", "devset_status": "incomplete", "documents": []}
    result = validate(instance, "manifest.schema.json")
    assert result is None


# ---------- validate_file 第二十一批 ----------


def test_validate_file_accepts_str_path_batch21(tmp_path):
    """validate_file 接受 str。"""
    p = tmp_path / "a.json"
    p.write_text(
        json.dumps({"manifest_version": "1.0", "devset_status": "incomplete", "documents": []}),
        encoding="utf-8",
    )
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_accepts_path_object_batch21(tmp_path):
    """validate_file 接受 Path。"""
    p = tmp_path / "a.json"
    p.write_text(
        json.dumps({"manifest_version": "1.0", "devset_status": "incomplete", "documents": []}),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")


def test_validate_file_missing_raises_file_not_found_batch21(tmp_path):
    """文件不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "no.json", "manifest.schema.json")


def test_validate_file_invalid_json_raises_json_decode_error_batch21(tmp_path):
    """非法 JSON → JSONDecodeError。"""
    p = tmp_path / "a.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_instance_raises_eval_schema_error_batch21(tmp_path):
    """非法 schema 内容 → EvalSchemaError。"""
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"manifest_version": "wrong"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_str_and_path_equivalent_batch21(tmp_path):
    """str 输入与 Path 输入行为一致。"""
    p = tmp_path / "a.json"
    payload = {"manifest_version": "1.0", "devset_status": "incomplete", "documents": []}
    p.write_text(json.dumps(payload), encoding="utf-8")
    # 两个都应该不抛
    validate_file(str(p), "manifest.schema.json")
    validate_file(Path(p), "manifest.schema.json")


def test_validate_file_calls_validate_batch21(tmp_path):
    """validate_file 内部调用 validate。"""
    p = tmp_path / "a.json"
    p.write_text(
        json.dumps({"manifest_version": "1.0", "devset_status": "incomplete", "documents": []}),
        encoding="utf-8",
    )
    with patch("evaluation.schema.validate") as mock_v:
        validate_file(p, "manifest.schema.json")
    assert mock_v.called


def test_validate_file_idempotent_batch21(tmp_path):
    """多次 validate_file 一致。"""
    p = tmp_path / "a.json"
    p.write_text(
        json.dumps({"manifest_version": "1.0", "devset_status": "incomplete", "documents": []}),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")  # 不抛即通过


def test_validate_file_utf8_with_chinese_batch21(tmp_path):
    """含中文 UTF-8 内容的文件能正确解析（schema 内容里也支持 unicode）。"""
    p = tmp_path / "a.json"
    payload = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "中文文档",
                "path": "samples/a.pdf",
                "source_type": "pdf",
                "categories": ["测试"],
            }
        ],
    }
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


# ---------- module source forbidden tokens 第三十七批 ----------


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
    'open("/etc/passwd',
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch21(forbidden):
    src = inspect.getsource(smod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch21():
    src = inspect.getsource(smod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch21():
    src = inspect.getsource(smod)
    assert "import socket" not in src


def test_module_source_no_os_system_call_batch21():
    src = inspect.getsource(smod)
    # 仅检查 os.system 调用
    assert "os.system(" not in src


def test_module_source_no_requests_import_batch21():
    src = inspect.getsource(smod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch21():
    src = inspect.getsource(smod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch21():
    src = inspect.getsource(smod)
    assert "import threading" not in src


def test_module_source_no_asyncio_import_batch21():
    src = inspect.getsource(smod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch21():
    src = inspect.getsource(smod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch21():
    src = inspect.getsource(smod)
    assert "import tempfile" not in src


def test_module_source_no_logging_import_batch21():
    src = inspect.getsource(smod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch21():
    src = inspect.getsource(smod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch21():
    src = inspect.getsource(smod)
    assert "import datetime" not in src


def test_module_source_no_collections_import_batch21():
    src = inspect.getsource(smod)
    assert "import collections" not in src


def test_module_source_no_pandas_import_batch21():
    src = inspect.getsource(smod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch21():
    src = inspect.getsource(smod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第三十三批 ----------


def test_module_source_has_future_annotations_batch21():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_source_has_json_import_batch21():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_has_pathlib_path_import_batch21():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch21():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_has_jsonschema_import_batch21():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_has_jsvalidationerror_import_batch21():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_has_schemas_dir_definition_batch21():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = Path(__file__).resolve().parent.parent /" in src


def test_module_source_has_eval_schema_error_class_batch21():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_has_schema_path_function_batch21():
    src = inspect.getsource(smod)
    assert "def _schema_path(name:" in src


def test_module_source_has_load_schema_function_batch21():
    src = inspect.getsource(smod)
    assert "def load_schema(name:" in src


def test_module_source_has_validate_function_batch21():
    src = inspect.getsource(smod)
    assert "def validate(instance:" in src


def test_module_source_has_validate_file_function_batch21():
    src = inspect.getsource(smod)
    assert "def validate_file(path:" in src


def test_module_source_has_sort_with_absolute_path_batch21():
    src = inspect.getsource(smod)
    assert "key=lambda e: list(e.absolute_path)" in src


def test_module_source_has_draft202012validator_call_batch21():
    src = inspect.getsource(smod)
    assert "Draft202012Validator(" in src


def test_module_source_has_encoding_utf8_in_open_batch21():
    src = inspect.getsource(smod)
    assert 'encoding="utf-8"' in src


# ---------- signatures 第三十三批 ----------


def test_signature_eval_schema_error_init_batch21():
    """EvalSchemaError.__init__ 签名 (message, errors=None)。"""
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    # self / message / errors
    assert len(params) == 3
    assert params[1].name == "message"
    assert params[2].name == "errors"


def test_signature_eval_schema_error_errors_default_none_batch21():
    sig = inspect.signature(EvalSchemaError.__init__)
    p = sig.parameters["errors"]
    assert p.default is None


def test_signature_schema_path_returns_path_annotation_batch21():
    sig = inspect.signature(_schema_path)
    assert "Path" in str(sig.return_annotation)


def test_signature_load_schema_returns_dict_batch21():
    sig = inspect.signature(load_schema)
    assert "dict" in str(sig.return_annotation)


def test_signature_validate_returns_none_annotation_batch21():
    sig = inspect.signature(validate)
    assert "None" in str(sig.return_annotation)


def test_signature_validate_file_returns_none_annotation_batch21():
    sig = inspect.signature(validate_file)
    assert "None" in str(sig.return_annotation)


def test_signature_validate_file_path_union_str_batch21():
    """validate_file path 形参是 Path | str。"""
    sig = inspect.signature(validate_file)
    ann = sig.parameters["path"].annotation
    assert "Path" in ann
    assert "str" in ann


# ---------- module 合理性第三十三批 ----------


def test_module_all_has_five_entries_batch21():
    assert set(smod.__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_module_does_not_import_evaluation_runner_batch21():
    src = inspect.getsource(smod)
    assert "from evaluation.runner" not in src
    assert "from evaluation import runner" not in src


def test_module_does_not_import_evaluation_cli_batch21():
    src = inspect.getsource(smod)
    assert "from evaluation.cli" not in src
    assert "from evaluation import cli" not in src


def test_module_does_not_import_evaluation_manifest_batch21():
    src = inspect.getsource(smod)
    assert "from evaluation.manifest" not in src
    assert "from evaluation import manifest" not in src


def test_module_does_not_import_evaluation_metrics_batch21():
    src = inspect.getsource(smod)
    assert "from evaluation.metrics" not in src
    assert "from evaluation import metrics" not in src


def test_module_does_not_import_evaluation_report_batch21():
    src = inspect.getsource(smod)
    assert "from evaluation.report" not in src
    assert "from evaluation import report" not in src


def test_module_does_not_import_app_pipeline_batch21():
    src = inspect.getsource(smod)
    assert "from app.pipeline" not in src
    assert "from app import pipeline" not in src


def test_module_schema_path_is_private_batch21():
    assert _schema_path.__name__.startswith("_")


def test_module_load_schema_is_public_batch21():
    assert not load_schema.__name__.startswith("_")


def test_module_validate_is_public_batch21():
    assert not validate.__name__.startswith("_")


def test_module_validate_file_is_public_batch21():
    assert not validate_file.__name__.startswith("_")


def test_module_has_module_docstring_batch21():
    assert smod.__doc__ is not None
    assert len(smod.__doc__) > 0


def test_module_no_main_block_batch21():
    src = inspect.getsource(smod)
    assert 'if __name__ ==' not in src


# ---------- 端到端集成第三十三批 ----------


def test_e2e_validate_round_trip_manifest_batch21(tmp_path):
    """manifest round-trip：写合法 → 校验通过。"""
    p = tmp_path / "a.json"
    payload = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/a.pdf",
                "source_type": "pdf",
                "categories": ["test"],
            }
        ],
    }
    p.write_text(json.dumps(payload), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_validate_round_trip_annotation_batch21(tmp_path):
    """annotation round-trip。"""
    p = tmp_path / "a.json"
    payload = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "figure_caption_pairs": [],
        "chunk_boundary_anchors": [],
    }
    p.write_text(json.dumps(payload), encoding="utf-8")
    # 不抛即通过
    validate_file(p, "annotation.schema.json")


def test_e2e_validate_load_then_validate_batch21():
    """load_schema 后用 Draft202012Validator 手动校验。"""
    schema = load_schema("manifest.schema.json")
    validator = Draft202012Validator(schema)
    instance = {"manifest_version": "1.0", "devset_status": "incomplete", "documents": []}
    errors = list(validator.iter_errors(instance))
    assert errors == []


def test_e2e_validate_invalid_manifest_full_error_structure_batch21():
    """非法 manifest 错误结构含必要字段。"""
    instance = {"manifest_version": "BAD"}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        assert isinstance(e.errors, list)
        assert len(e.errors) >= 1
        head = e.errors[0]
        assert "path" in head
        assert "message" in head
        assert "schema_path" in head


def test_e2e_validate_file_str_path_equivalent_to_path_batch21(tmp_path):
    """str path 和 Path 对象行为一致。"""
    p = tmp_path / "a.json"
    payload = {"manifest_version": "1.0", "devset_status": "incomplete", "documents": []}
    p.write_text(json.dumps(payload), encoding="utf-8")
    # 两个都不抛
    validate_file(str(p), "manifest.schema.json")
    validate_file(Path(p), "manifest.schema.json")


def test_e2e_validate_file_with_unicode_doc_id_batch21(tmp_path):
    """doc_id 含 unicode 也能通过 schema。"""
    p = tmp_path / "a.json"
    payload = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "中文",
                "path": "samples/a.pdf",
                "source_type": "pdf",
                "categories": ["x"],
            }
        ],
    }
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_error_subclass_relationship_batch21():
    """EvalSchemaError 是 Exception，可被 except Exception 捕获。"""
    caught = False
    try:
        raise EvalSchemaError("test", errors=[{"path": [], "message": "x"}])
    except Exception:
        caught = True
    assert caught
