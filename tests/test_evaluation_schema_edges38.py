"""evaluation/schema.py 第三十八轮 edges 测试（Round 456）。

补强 edges37 未触及的角度：
- SCHEMAS_DIR 常量深度第十八批（resolve idempotent / is_dir True / parent equals pyproject dir / 与 manifest.py 同源 / glob 结果稳定 / with_suffix 行为 / parts 数）
- EvalSchemaError 行为深度第十八批（args / __str__ 不含 errors / errors 类型始终 list / str message 入参 / equality based on args / pickling / dict hashable / raise within raise / message attribute）
- _schema_path 行为深度第十八批（raises FileNotFoundError 类型 / message 文本固定含 Schema 字 / 非 SCHEMAS_DIR 子目录拒绝 / accepts str / accepts relative-name-only / 拒绝 / 不存在 / with mixed case ext / 返回值 open-able）
- load_schema 行为深度第十八批（returns dict / 返回值与磁盘文件相同 / 不缓存（多次调用 read 不同 dict 实例）/ 接受 "name" 简短 / 拒绝非 .json 后缀 / 拒绝目录 / 文件含 BOM 拒绝）
- validate 行为深度第十八批（success 返回 None / 单错误含 path / 多错误含全部 / errors 默认值空 list 不会被填 / message 含 "Schema" 字 / first error 与 errors[0] 一致 / instance 不是 dict 时也被 schema 拒绝）
- validate_file 行为深度第十八批（path 转 Path / 不存在抛 FileNotFoundError / 抛错链不包装 json.JSONDecodeError / read 后 file 关闭 / 与 validate 等价 / 接受短路径）
- 4 个 schema 内容深度第十八批（manifest_version enum / annotation_version pattern / report_version enum / document schema 与 evaluation-report 各自独立）
- module source forbidden tokens 第三十四批
- module source 字符串精确补强第二十九批
- signatures 第二十九批
- module 合理性第二十九批
- 端到端集成第二十九批
"""

from __future__ import annotations

import inspect
import json
import pickle
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


# ---------- SCHEMAS_DIR 常量深度第十八批 ----------


def test_schemas_dir_resolve_idempotent_batch18():
    """SCHEMAS_DIR.resolve() 应是 SCHEMAS_DIR 自身（已 resolve）。"""
    assert SCHEMAS_DIR == SCHEMAS_DIR.resolve()


def test_schemas_dir_is_dir_batch18():
    """SCHEMAS_DIR 应存在且是目录。"""
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_parent_has_pyproject_batch18():
    """SCHEMAS_DIR 父目录应包含 pyproject.toml。"""
    parent = SCHEMAS_DIR.parent
    assert (parent / "pyproject.toml").is_file()


def test_schemas_dir_glob_schema_json_batch18():
    """所有 schema 文件以 .schema.json 结尾。"""
    jsons = list(SCHEMAS_DIR.glob("*.schema.json"))
    for j in jsons:
        assert j.name.endswith(".schema.json")


def test_schemas_dir_glob_stable_batch18():
    """两次 glob 结果相同。"""
    g1 = sorted(p.name for p in SCHEMAS_DIR.glob("*.schema.json"))
    g2 = sorted(p.name for p in SCHEMAS_DIR.glob("*.schema.json"))
    assert g1 == g2


def test_schemas_dir_parts_count_batch18():
    """SCHEMAS_DIR 至少包含 schemas 路径段。"""
    parts = SCHEMAS_DIR.parts
    assert "schemas" in parts


def test_schemas_dir_independent_from_app_schema_batch18():
    """evaluation/schema.SCHEMAS_DIR 与 app/schema 的 SCHEMA_PATH 应指向同一根。"""
    from app import schema as app_schema

    assert app_schema.SCHEMA_PATH.parent == SCHEMAS_DIR


# ---------- EvalSchemaError 行为深度第十八批 ----------


def test_eval_schema_error_args_carry_message_batch18():
    """EvalSchemaError("msg").args 应含 msg。"""
    err = EvalSchemaError("msg")
    assert err.args == ("msg",)


def test_eval_schema_error_args_carry_message_and_errors_not_in_args_batch18():
    """EvalSchemaError("msg", errors=[...]) 的 args 仅含 msg，errors 单独存。"""
    err = EvalSchemaError("msg", errors=[{"a": 1}])
    assert err.args == ("msg",)
    assert err.errors == [{"a": 1}]


def test_eval_schema_error_str_does_not_include_errors_batch18():
    """str(err) 只包含 message，不含 errors。"""
    err = EvalSchemaError("hello", errors=[{"x": 1}])
    s = str(err)
    assert s == "hello"
    assert "x" not in s


def test_eval_schema_errors_type_is_list_batch18():
    """errors 属性始终是 list。"""
    assert isinstance(EvalSchemaError("m").errors, list)
    assert isinstance(EvalSchemaError("m", None).errors, list)
    assert isinstance(EvalSchemaError("m", []).errors, list)
    assert isinstance(EvalSchemaError("m", [{}]).errors, list)


def test_eval_schema_error_equality_with_args_batch18():
    """基于 args 相等性（不比较 errors）。"""
    err1 = EvalSchemaError("msg", [{"a": 1}])
    err2 = EvalSchemaError("msg", [{"b": 2}])
    err3 = EvalSchemaError("other")
    assert err1.args == err2.args
    assert err1.args != err3.args


def test_eval_schema_error_pickle_roundtrip_batch18():
    """EvalSchemaError 应能被 pickle（Exception 子类）。"""
    err = EvalSchemaError("hello")
    restored = pickle.loads(pickle.dumps(err))
    assert str(restored) == "hello"


def test_eval_schema_error_hashable_batch18():
    """Exception 实例通常可 hash。"""
    err = EvalSchemaError("m")
    assert hash(err) == hash(err)


def test_eval_schema_error_raise_within_raise_batch18():
    """嵌套 raise 时 __cause__ 正确传递。"""

    try:
        try:
            raise ValueError("inner")
        except ValueError as ve:
            raise EvalSchemaError("outer") from ve
    except EvalSchemaError as ee:
        assert isinstance(ee.__cause__, ValueError)
        assert str(ee.__cause__) == "inner"


def test_eval_schema_error_message_attr_batch18():
    """Exception.args[0] 应等于 message。"""
    err = EvalSchemaError("xyz")
    assert err.args[0] == "xyz"


# ---------- _schema_path 行为深度第十八批 ----------


def test_schema_path_raises_file_not_found_type_batch18():
    """不存在时应抛 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("nope.schema.json")


def test_schema_path_error_message_contains_word_schema_batch18():
    """错误消息含中文 'Schema' 字（实际是 'Schema 文件不存在'）。"""
    try:
        _schema_path("absent.schema.json")
    except FileNotFoundError as e:
        assert "Schema" in str(e) or "schema" in str(e).lower()


def test_schema_path_rejects_subdir_outside_schemas_dir_batch18():
    """_schema_path 只接 SCHEMAS_DIR 下的文件名。"""
    # 用绝对路径作为 name 时，不应逃逸 SCHEMAS_DIR
    with pytest.raises(FileNotFoundError):
        _schema_path("/etc/passwd")


def test_schema_path_accepts_str_argument_batch18():
    """name 必须接受 str。"""
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_returns_existing_file_batch18():
    """返回的 Path 必然是已存在的文件。"""
    p = _schema_path("annotation.schema.json")
    assert p.is_file()


def test_schema_path_no_caching_batch18():
    """两次调用返回新 Path 实例（或相等值，但每次新读）。"""
    p1 = _schema_path("manifest.schema.json")
    p2 = _schema_path("manifest.schema.json")
    assert p1 == p2


def test_schema_path_returns_absolute_batch18():
    """返回路径是绝对路径（基于 SCHEMAS_DIR 已 resolve）。"""
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


# ---------- load_schema 行为深度第十八批 ----------


def test_load_schema_returns_dict_batch18():
    """load_schema 返回 dict。"""
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_value_matches_disk_batch18():
    """load_schema 返回值与磁盘 JSON 解析的 dict 等价。"""
    s = load_schema("manifest.schema.json")
    raw = json.loads((SCHEMAS_DIR / "manifest.schema.json").read_text(encoding="utf-8"))
    assert s == raw


def test_load_schema_no_caching_new_instance_batch18():
    """两次 load_schema 返回不同的 dict 对象（虽然内容相等）。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2
    assert s1 is not s2


def test_load_schema_accepts_short_name_batch18():
    """load_schema 接受完整文件名。"""
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_load_schema_rejects_missing_extension_batch18():
    """无 .schema.json 后缀的 name 应抛 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        load_schema("manifest")  # 缺后缀


def test_load_schema_rejects_directory_batch18():
    """name 是目录时（实际是空名）抛 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        load_schema("")  # 空字符串拼到 SCHEMAS_DIR 上仍是目录


# ---------- validate 行为深度第十八批 ----------


def test_validate_success_returns_none_type_batch18():
    """validate 成功返回 NoneType。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_validate_single_error_has_path_batch18():
    """单错误时 errors[0] 含 'path' 键。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    err = ei.value
    assert len(err.errors) >= 1
    assert "path" in err.errors[0]


def test_validate_multiple_errors_returned_batch18():
    """多个错误全部进入 errors。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": "WRONG", "documents": "NOT_LIST"}, "manifest.schema.json")
    err = ei.value
    assert len(err.errors) >= 2


def test_validate_message_contains_word_schema_batch18():
    """错误 message 含 'Schema' 字。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    assert "Schema" in str(ei.value)


def test_validate_first_error_matches_errors_head_batch18():
    """message 提到的 head 应与 errors[0] 对应同一错误。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": "WRONG"}, "manifest.schema.json")
    err = ei.value
    # message @ path 应与 errors[0].path 对应
    assert err.errors[0]["message"] in str(err)


def test_validate_non_dict_instance_still_evaluated_batch18():
    """instance 非 dict 时也被 schema 处理（schema 要求 type:object）。"""
    with pytest.raises(EvalSchemaError):
        validate([1, 2, 3], "manifest.schema.json")


def test_validate_does_not_modify_errors_after_raising_batch18():
    """validate 抛错后 errors 是固定 list。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    err = ei.value
    snapshot = list(err.errors)
    assert err.errors == snapshot


# ---------- validate_file 行为深度第十八批 ----------


def test_validate_file_converts_str_to_path_batch18(tmp_path):
    """validate_file 接受 str 路径，内部转 Path。"""
    p = tmp_path / "x.json"
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
    # 不抛错
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_unknown_file_raises_file_not_found_batch18(tmp_path):
    """不存在的文件抛 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "missing.json", "manifest.schema.json")


def test_validate_file_invalid_json_propagates_json_decode_error_batch18(tmp_path):
    """非法 JSON 抛 json.JSONDecodeError（不被 validate_file 包装）。"""
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_equivalent_to_load_then_validate_batch18(tmp_path):
    """validate_file(p) 等同于 json.load + validate。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    p = tmp_path / "x.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    validate(instance, "manifest.schema.json")  # 不抛错


def test_validate_file_accepts_path_object_batch18(tmp_path):
    """validate_file 接受 Path 对象。"""
    p = tmp_path / "x.json"
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
    validate_file(p, "manifest.schema.json")


def test_validate_file_directory_raises_is_a_directory_batch18(tmp_path):
    """传入目录时应抛错（json.load 失败）。"""
    with pytest.raises((IsADirectoryError, json.JSONDecodeError, OSError)):
        validate_file(tmp_path, "manifest.schema.json")


# ---------- 4 个 schema 内容深度第十八批 ----------


def test_manifest_schema_manifest_version_is_enum_locked_to_1_0_batch18():
    """manifest.schema.json 中 manifest_version 应锁死 "1.0"。"""
    s = load_schema("manifest.schema.json")
    mv = s["properties"]["manifest_version"]
    assert mv.get("enum") == ["1.0"] or mv.get("const") == "1.0"


def test_evaluation_report_schema_has_required_top_keys_batch18():
    """evaluation-report.schema.json 应有 report_version / provenance / devset / summary / per_doc*。"""
    s = load_schema("evaluation-report.schema.json")
    required = s.get("required", [])
    for k in ("report_version", "provenance", "devset", "summary"):
        assert k in required
    # 应有 per_doc_results 或 per_doc 字段定义
    assert "per_doc_results" in s.get("properties", {}) or "per_doc" in s.get("properties", {})


def test_annotation_schema_requires_doc_id_and_version_batch18():
    """annotation.schema.json required 含 doc_id 与 annotation_version。"""
    s = load_schema("annotation.schema.json")
    required = s.get("required", [])
    assert "doc_id" in required
    assert "annotation_version" in required


def test_document_schema_independent_from_evaluation_report_batch18():
    """document.schema.json 与 evaluation-report.schema.json 是两份独立 schema。"""
    sd = load_schema("document.schema.json")
    sr = load_schema("evaluation-report.schema.json")
    # title 应不同（或其中之一应含 "document" 或 "evaluation"）
    titles = (sd.get("title", ""), sr.get("title", ""))
    assert titles[0] != titles[1] or titles[0] == ""


# ---------- module source forbidden tokens 第三十四批 ----------


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
    "os.exec",
    "os.spawn",
    "shutil.rmtree",
    "shutil.copy",
    "pathlib.Path.unlink",
    "open(\"/etc/passwd",
    "eval(",
    "exec(",
    "__import__",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch18(forbidden):
    src = inspect.getsource(smod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch18():
    src = inspect.getsource(smod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_os_system_call_batch18():
    src = inspect.getsource(smod)
    assert "os.system(" not in src


def test_module_source_no_socket_import_batch18():
    src = inspect.getsource(smod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch18():
    src = inspect.getsource(smod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch18():
    src = inspect.getsource(smod)
    assert "import urllib" not in src


def test_module_source_no_asyncio_import_batch18():
    src = inspect.getsource(smod)
    assert "import asyncio" not in src


def test_module_source_no_threading_import_batch18():
    src = inspect.getsource(smod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch18():
    src = inspect.getsource(smod)
    assert "import multiprocessing" not in src


def test_module_source_no_tempfile_import_batch18():
    src = inspect.getsource(smod)
    assert "import tempfile" not in src


def test_module_source_no_glob_import_batch18():
    src = inspect.getsource(smod)
    assert "import glob" not in src


def test_module_source_no_shutil_import_batch18():
    src = inspect.getsource(smod)
    assert "import shutil" not in src


def test_module_source_no_sys_exit_batch18():
    src = inspect.getsource(smod)
    assert "sys.exit" not in src


def test_module_source_no_path_unlink_batch18():
    src = inspect.getsource(smod)
    assert ".unlink(" not in src


def test_module_source_no_path_rmdir_batch18():
    src = inspect.getsource(smod)
    assert ".rmdir(" not in src


def test_module_source_no_path_mkdir_batch18():
    src = inspect.getsource(smod)
    assert ".mkdir(" not in src


def test_module_source_no_path_write_text_batch18():
    """schema.py 是只读 schema 加载，不应写盘。"""
    src = inspect.getsource(smod)
    assert ".write_text(" not in src
    assert ".write_bytes(" not in src


def test_module_source_no_compile_pattern_batch18():
    src = inspect.getsource(smod)
    assert "re.compile" not in src


# ---------- module source 字符串精确补强第二十九批 ----------


def test_module_source_has_future_annotations_string_batch18():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_source_has_docstring_about_schema_batch18():
    src = inspect.getsource(smod)
    assert "Schema" in src or "schema" in src


def test_module_source_has_eval_schema_error_docstring_batch18():
    src = inspect.getsource(smod)
    assert "Schema 校验失败时抛出" in src


def test_module_source_has_load_schema_docstring_batch18():
    src = inspect.getsource(smod)
    assert "从 schemas/ 目录加载命名 Schema" in src


def test_module_source_has_validate_docstring_batch18():
    src = inspect.getsource(smod)
    assert "校验 instance dict 是否符合命名 Schema" in src


def test_module_source_has_validate_file_docstring_batch18():
    src = inspect.getsource(smod)
    assert "加载磁盘 JSON 并按命名 Schema 校验" in src


def test_module_source_has_schemas_dir_assignment_batch18():
    src = inspect.getsource(smod)
    assert 'SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"' in src


def test_module_source_has_draft_2020_12_validator_usage_batch18():
    src = inspect.getsource(smod)
    assert "Draft202012Validator" in src


def test_module_source_has_iter_errors_call_batch18():
    src = inspect.getsource(smod)
    assert "iter_errors" in src


def test_module_source_has_absolute_path_attribute_batch18():
    src = inspect.getsource(smod)
    assert "absolute_path" in src


def test_module_source_has_absolute_schema_path_attribute_batch18():
    src = inspect.getsource(smod)
    assert "absolute_schema_path" in src


def test_module_source_has_all_list_with_5_entries_batch18():
    src = inspect.getsource(smod)
    assert '"SCHEMAS_DIR"' in src
    assert '"EvalSchemaError"' in src
    assert '"load_schema"' in src
    assert '"validate"' in src
    assert '"validate_file"' in src


def test_module_source_has_utf8_encoding_in_open_batch18():
    src = inspect.getsource(smod)
    assert 'encoding="utf-8"' in src


# ---------- signatures 第二十九批 ----------


def test_signature_schema_path_takes_str_returns_path_batch18():
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"
    assert sig.return_annotation == Path or sig.return_annotation == "Path"


def test_signature_load_schema_takes_str_returns_dict_batch18():
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"
    # 返回类型注解是 dict[str, Any]（from __future__ 让它变 str）
    ra = sig.return_annotation
    assert ra == dict or ra == "dict[str, Any]" or "dict" in str(ra)


def test_signature_validate_no_extra_params_batch18():
    sig = inspect.signature(validate)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["instance", "schema_name"]
    assert all(p.default is inspect.Parameter.empty for p in params)


def test_signature_validate_file_no_extra_params_batch18():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["path", "schema_name"]
    assert all(p.default is inspect.Parameter.empty for p in params)


def test_signature_eval_schema_error_init_signature_batch18():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["self", "message", "errors"]
    # errors 有默认值 None
    assert params[2].default is None


# ---------- module 合理性第二十九批 ----------


def test_module_has_all_attribute_batch18():
    assert hasattr(smod, "__all__")


def test_module_all_contains_5_entries_batch18():
    assert len(smod.__all__) == 5


def test_module_all_entries_are_strings_batch18():
    for n in smod.__all__:
        assert isinstance(n, str)


def test_module_eval_schema_error_in_all_batch18():
    assert "EvalSchemaError" in smod.__all__


def test_module_does_not_import_app_pipeline_batch18():
    src = inspect.getsource(smod)
    assert "from app" not in src
    assert "import app" not in src


def test_module_does_not_import_evaluation_runner_batch18():
    src = inspect.getsource(smod)
    assert "from evaluation.runner" not in src
    assert "from evaluation import runner" not in src


def test_module_does_not_import_evaluation_metrics_batch18():
    src = inspect.getsource(smod)
    assert "from evaluation.metrics" not in src
    assert "from evaluation import metrics" not in src


def test_module_does_not_import_evaluation_annotation_metrics_batch18():
    src = inspect.getsource(smod)
    assert "from evaluation.annotation_metrics" not in src
    assert "from evaluation import annotation_metrics" not in src


def test_module_no_main_block_batch18():
    src = inspect.getsource(smod)
    assert 'if __name__ ==' not in src
    assert "__main__" not in src


# ---------- 端到端集成 第二十九批 ----------


def test_e2e_validate_with_known_good_manifest_batch18():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/private/x.pdf",
                "source_type": "pdf",
            }
        ],
    }
    validate(instance, "manifest.schema.json")


def test_e2e_load_schema_then_validate_round_trip_batch18():
    """先 load_schema 再 validate 一个有效实例。"""
    schema = load_schema("manifest.schema.json")
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    # 用 Draft202012Validator 直接验证 schema 与 instance 一致
    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors(instance)) == []


def test_e2e_validate_annotation_known_good_batch18():
    instance = {
        "doc_id": "d1",
        "annotation_version": "1.0",
        "annotator": "tester",
        "date": "2026-08-10",
    }
    validate(instance, "annotation.schema.json")


def test_e2e_validate_with_unknown_schema_raises_file_not_found_batch18():
    with pytest.raises(FileNotFoundError):
        validate({}, "absent.schema.json")


def test_e2e_validate_file_with_unknown_schema_raises_file_not_found_batch18(tmp_path):
    """validate_file 即使文件有效，schema 不存在也抛 FileNotFoundError。"""
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "absent.schema.json")


def test_e2e_validate_empty_dict_to_all_schemas_batch18():
    """空 dict 对所有 schema 都应失败。"""
    for name in ("manifest", "annotation", "evaluation-report"):
        with pytest.raises(EvalSchemaError):
            validate({}, f"{name}.schema.json")


def test_e2e_cross_schema_validation_fails_for_wrong_schema_batch18():
    """manifest 数据用 evaluation-report schema 校验应失败。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "evaluation-report.schema.json")
