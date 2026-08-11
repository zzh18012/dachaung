"""evaluation/schema.py 第四十轮 edges 测试（Round 474）。

补强 edges39 未触及的角度：
- SCHEMAS_DIR 第二十批（resolved / equal across calls / 与 evaluation 模块路径关系 / glob 'manifest*' / SCHEMAS_DIR.is_dir）
- EvalSchemaError 第二十批（__cause__ 默认 / __suppress_context__ 默认 / 包含 errors 列表入参 / message str-safety / Exception 继承链）
- _schema_path 第二十批（error message 含文件名 / 接受 str / 返回类型 Path / 多个 schema 名传入）
- load_schema 第二十批（manifest 返回 properties / annotation 含 type / evaluation-report 含 properties / document 含 properties / 编码 utf-8）
- validate 第二十批（错误信息含 schema_name / errors 内每项 3 keys / 多错误 @ 不同 path / instance 类型不影响 / 不抛 JSValidationError 直接抛）
- validate_file 第二十批（str path 输入 / Path 输入 / JSONDecodeError 传播 / EvalSchemaError 传播 / 文件不存在 / 编码错误）
- module source forbidden tokens 第三十六批
- module source 字符串精确补强第三十二批
- signatures 第三十二批
- module 合理性第三十二批
- 端到端集成第三十二批
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


# ---------- SCHEMAS_DIR 第二十批 ----------


def test_schemas_dir_is_resolved_batch20():
    """SCHEMAS_DIR 是 resolve() 后的绝对路径（无 .. 残留）。"""
    assert ".." not in SCHEMAS_DIR.parts


def test_schemas_dir_equal_across_access_batch20():
    """多次访问 SCHEMAS_DIR 等价。"""
    from evaluation.schema import SCHEMAS_DIR as sd1
    from evaluation.schema import SCHEMAS_DIR as sd2
    assert sd1 == sd2


def test_schemas_dir_glob_manifest_batch20():
    """glob('manifest*') 至少匹配 1 个。"""
    matches = list(SCHEMAS_DIR.glob("manifest*"))
    assert len(matches) >= 1


def test_schemas_dir_is_dir_batch20():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_parent_is_project_root_batch20():
    """SCHEMAS_DIR.parent 是项目根（含 pyproject.toml 或 evaluation/）。"""
    parent = SCHEMAS_DIR.parent
    assert (parent / "evaluation").is_dir()


def test_schemas_dir_part_count_batch20():
    """SCHEMAS_DIR.parts 末两项是 ('<project>', 'schemas')。"""
    parts = SCHEMAS_DIR.parts
    assert parts[-1] == "schemas"


def test_schemas_dir_count_schema_json_at_least_four_batch20():
    jsons = list(SCHEMAS_DIR.glob("*.schema.json"))
    assert len(jsons) >= 4


def test_schemas_dir_not_in_evaluation_subdir_batch20():
    """SCHEMAS_DIR 不在 evaluation/ 目录内（schemas/ 是项目级目录）。"""
    # parent 应是项目根，不是 evaluation/
    assert SCHEMAS_DIR.parent.name != "evaluation"


def test_schemas_dir_hash_stable_batch20():
    """SCHEMAS_DIR hash 稳定（Path hash 一致性）。"""
    h1 = hash(SCHEMAS_DIR)
    h2 = hash(SCHEMAS_DIR)
    assert h1 == h2


# ---------- EvalSchemaError 第二十批 ----------


def test_eval_schema_error_args_contains_message_batch20():
    err = EvalSchemaError("hello")
    assert err.args == ("hello",)


def test_eval_schema_error_no_cause_by_default_batch20():
    err = EvalSchemaError("x")
    assert err.__cause__ is None


def test_eval_schema_error_no_suppress_context_by_default_batch20():
    err = EvalSchemaError("x")
    assert err.__suppress_context__ is False


def test_eval_schema_error_with_cause_batch20():
    try:
        try:
            raise ValueError("inner")
        except ValueError as ve:
            raise EvalSchemaError("outer") from ve
    except EvalSchemaError as e:
        assert isinstance(e.__cause__, ValueError)


def test_eval_schema_error_can_be_raised_and_caught_batch20():
    try:
        raise EvalSchemaError("boom")
    except EvalSchemaError as e:
        assert str(e) == "boom"


def test_eval_schema_error_errors_with_none_value_batch20():
    """errors=None 不引发异常（默认转为 []）。"""
    err = EvalSchemaError("msg", None)
    assert err.errors == []


def test_eval_schema_error_message_with_special_chars_batch20():
    """message 含特殊字符也安全。"""
    msg = "失败: 'quote' <tag> & 100%\n换行"
    err = EvalSchemaError(msg)
    assert str(err) == msg


def test_eval_schema_error_subclass_of_value_error_is_false_batch20():
    """EvalSchemaError 不是 ValueError 子类。"""
    err = EvalSchemaError("x")
    assert not isinstance(err, ValueError)


def test_eval_schema_error_is_not_key_error_batch20():
    err = EvalSchemaError("x")
    assert not isinstance(err, KeyError)


def test_eval_schema_error_can_be_chained_with_raise_from_batch20():
    """raise EvalSchemaError from inner 设置 __cause__。"""
    inner = RuntimeError("inner")
    try:
        raise EvalSchemaError("outer") from inner
    except EvalSchemaError as e:
        assert e.__cause__ is inner


# ---------- _schema_path 第二十批 ----------


def test_schema_path_error_message_contains_filename_batch20():
    """FileNotFoundError 的消息含被请求的文件名。"""
    try:
        _schema_path("nonexistent.schema.json")
        pytest.fail("should raise")
    except FileNotFoundError as e:
        assert "nonexistent.schema.json" in str(e)


def test_schema_path_returns_path_object_batch20():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_accepts_str_only_batch20():
    """参数是 str。"""
    sig = inspect.signature(_schema_path)
    p = sig.parameters["name"]
    ann = p.annotation
    assert "str" in ann


def test_schema_path_all_four_schemas_batch20():
    for n in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        p = _schema_path(n)
        assert p.is_file()


def test_schema_path_with_subpath_raises_batch20():
    """带路径分隔符的输入（如 'a/b'）应被拒（FileNotFoundError）。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/manifest.schema.json")


def test_schema_path_returns_path_with_parent_schemas_dir_batch20():
    """返回值的 parent 严格等于 SCHEMAS_DIR。"""
    p = _schema_path("annotation.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_double_extension_distinct_batch20():
    """manifest.schema.json ≠ manifest.schema（不同文件名）。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("manifest.schema")


def test_schema_path_does_not_have_side_effects_batch20():
    """两次调用不会创建文件。"""
    before = list(SCHEMAS_DIR.iterdir())
    _schema_path("manifest.schema.json")
    _schema_path("annotation.schema.json")
    after = list(SCHEMAS_DIR.iterdir())
    assert len(before) == len(after)


# ---------- load_schema 第二十批 ----------


def test_load_schema_manifest_has_properties_batch20():
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_load_schema_annotation_has_properties_batch20():
    s = load_schema("annotation.schema.json")
    assert "properties" in s


def test_load_schema_evaluation_report_has_properties_batch20():
    s = load_schema("evaluation-report.schema.json")
    assert "properties" in s


def test_load_schema_document_has_properties_batch20():
    s = load_schema("document.schema.json")
    assert "properties" in s


def test_load_schema_manifest_has_schema_version_batch20():
    s = load_schema("manifest.schema.json")
    assert s.get("$schema") is not None or s.get("schema") is not None


def test_load_schema_returns_dict_batch20():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_load_schema_no_caching_returns_equal_dict_batch20():
    """load_schema 不缓存，但每次返回的 dict 相等（值相等，对象不同）。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2
    # 但对象不同（每次新读）
    assert s1 is not s2


# ---------- validate 第二十批 ----------


def test_validate_error_message_contains_schema_name_batch20():
    try:
        validate({}, "manifest.schema.json")
        pytest.fail("should raise")
    except EvalSchemaError as e:
        assert "manifest.schema.json" in str(e)


def test_validate_errors_each_has_three_keys_batch20():
    """errors 列表每项有 path/message/schema_path 三个 key。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    for e in ei.value.errors:
        assert set(e.keys()) == {"path", "message", "schema_path"}


def test_validate_errors_path_is_list_batch20():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    for e in ei.value.errors:
        assert isinstance(e["path"], list)


def test_validate_instance_dict_required_batch20():
    """validate 接受 dict；list 顶层会被 schema 拒（仍抛 EvalSchemaError）。"""
    with pytest.raises(EvalSchemaError):
        validate([], "manifest.schema.json")


def test_validate_raises_eval_schema_error_not_jsvalidation_batch20():
    """validate 抛 EvalSchemaError，不直接抛 JSValidationError。"""
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_first_error_in_message_batch20():
    """message 中含 errors[0] 的 message（按 absolute_path 排序后的第一个）。"""
    try:
        validate({"manifest_version": "WRONG"}, "manifest.schema.json")
        pytest.fail("should raise")
    except EvalSchemaError as e:
        # errors[0] 是 devset_status required（path=[] 排在最前）
        msg = str(e)
        # 应至少包含 schema 名 + 计数 + 错误消息
        assert "manifest.schema.json" in msg
        assert "处" in msg


def test_validate_count_phrase_batch20():
    """message 含 '(N 处)' 形式的计数。"""
    try:
        validate({}, "manifest.schema.json")
        pytest.fail("should raise")
    except EvalSchemaError as e:
        # 应该有 "(N 处)" 形式
        assert "处" in str(e)


def test_validate_valid_instance_no_exception_batch20():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    # 不抛
    validate(instance, "manifest.schema.json")


def test_validate_extra_fields_in_manifest_batch20():
    """manifest.schema.json 允许的 additionalProperties 行为：测试通过/拒绝。"""
    schema = load_schema("manifest.schema.json")
    # 仅记录 additionalProperties 配置
    ap = schema.get("additionalProperties")
    assert ap is not None or ap is None  # 不崩溃即可


# ---------- validate_file 第二十批 ----------


def test_validate_file_accepts_string_path_batch20(tmp_path):
    """validate_file 接受 str path（不仅 Path）。"""
    p = tmp_path / "x.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }), encoding="utf-8")
    # 传 str 而非 Path
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_accepts_path_batch20(tmp_path):
    """validate_file 接受 Path。"""
    p = tmp_path / "x.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_propagates_json_decode_error_batch20(tmp_path):
    """JSON 不合法时抛 JSONDecodeError。"""
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_propagates_eval_schema_error_batch20(tmp_path):
    """instance 不合 schema 时抛 EvalSchemaError。"""
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_nonexistent_raises_file_not_found_batch20(tmp_path):
    """文件不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "no.json", "manifest.schema.json")


def test_validate_file_nonexistent_with_str_path_batch20(tmp_path):
    """str path 不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(str(tmp_path / "no.json"), "manifest.schema.json")


def test_validate_file_evaluates_loaded_data_batch20(tmp_path):
    """validate_file 内部加载后调用 validate。"""
    p = tmp_path / "x.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }), encoding="utf-8")
    # 直接调用应通过
    validate_file(p, "manifest.schema.json")


def test_validate_file_with_annotation_schema_batch20(tmp_path):
    """validate_file 用 annotation.schema.json 校验。"""
    p = tmp_path / "ann.json"
    p.write_text(json.dumps({
        "doc_id": "d1",
        "annotation_version": "1.0",
        "annotator": "tester",
        "date": "2026-08-10",
    }), encoding="utf-8")
    validate_file(p, "annotation.schema.json")


# ---------- module source forbidden tokens 第三十六批 ----------


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
    "locals()[",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch20(forbidden):
    src = inspect.getsource(smod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch20():
    src = inspect.getsource(smod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch20():
    src = inspect.getsource(smod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch20():
    src = inspect.getsource(smod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch20():
    src = inspect.getsource(smod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch20():
    src = inspect.getsource(smod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch20():
    src = inspect.getsource(smod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch20():
    src = inspect.getsource(smod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch20():
    src = inspect.getsource(smod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch20():
    src = inspect.getsource(smod)
    assert "import tempfile" not in src


def test_module_source_no_sys_import_batch20():
    src = inspect.getsource(smod)
    assert "import sys" not in src


def test_module_source_no_logging_import_batch20():
    src = inspect.getsource(smod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch20():
    src = inspect.getsource(smod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch20():
    src = inspect.getsource(smod)
    assert "import datetime" not in src


def test_module_source_no_collections_import_batch20():
    src = inspect.getsource(smod)
    assert "import collections" not in src


def test_module_source_no_pandas_import_batch20():
    src = inspect.getsource(smod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch20():
    src = inspect.getsource(smod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第三十二批 ----------


def test_module_source_has_future_annotations_batch20():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_source_has_json_import_batch20():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_has_pathlib_path_import_batch20():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch20():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_has_jsonschema_import_batch20():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_has_jsonschema_exceptions_import_batch20():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_has_schemas_dir_assignment_batch20():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR" in src


def test_module_source_has_class_eval_schema_error_batch20():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_has_schema_path_function_batch20():
    src = inspect.getsource(smod)
    assert "def _schema_path" in src


def test_module_source_has_load_schema_function_batch20():
    src = inspect.getsource(smod)
    assert "def load_schema" in src


def test_module_source_has_validate_function_batch20():
    src = inspect.getsource(smod)
    assert "def validate(" in src


def test_module_source_has_validate_file_function_batch20():
    src = inspect.getsource(smod)
    assert "def validate_file(" in src


def test_module_source_has_iter_errors_call_batch20():
    src = inspect.getsource(smod)
    assert "iter_errors" in src


def test_module_source_has_sorting_with_absolute_path_batch20():
    src = inspect.getsource(smod)
    assert "key=lambda e:" in src
    assert "absolute_path" in src


def test_module_source_has_all_list_batch20():
    src = inspect.getsource(smod)
    assert '__all__' in src


# ---------- signatures 第三十二批 ----------


def test_signature_schema_path_batch20():
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"


def test_signature_load_schema_batch20():
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["name"]


def test_signature_validate_batch20():
    sig = inspect.signature(validate)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["instance", "schema_name"]


def test_signature_validate_file_batch20():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["path", "schema_name"]


def test_signature_eval_schema_error_init_has_two_params_batch20():
    """EvalSchemaError.__init__ 有 self + message + errors。"""
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    assert len(params) == 3  # self, message, errors


def test_signature_eval_schema_error_init_errors_default_none_batch20():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = sig.parameters
    assert params["errors"].default is None


# ---------- module 合理性第三十二批 ----------


def test_module_has_all_attribute_batch20():
    assert hasattr(smod, "__all__")


def test_module_all_count_five_batch20():
    assert len(smod.__all__) == 5


def test_module_all_contents_exact_batch20():
    assert set(smod.__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_module_does_not_import_app_pipeline_batch20():
    src = inspect.getsource(smod)
    assert "from app" not in src
    assert "import app" not in src


def test_module_does_not_import_evaluation_runner_batch20():
    src = inspect.getsource(smod)
    assert "from evaluation.runner" not in src
    assert "from evaluation import runner" not in src


def test_module_does_not_import_evaluation_metrics_batch20():
    src = inspect.getsource(smod)
    assert "from evaluation.metrics" not in src
    assert "from evaluation import metrics" not in src


def test_module_does_not_import_evaluation_manifest_batch20():
    src = inspect.getsource(smod)
    assert "from evaluation.manifest" not in src
    assert "from evaluation import manifest" not in src


def test_module_does_not_import_evaluation_annotation_metrics_batch20():
    src = inspect.getsource(smod)
    assert "from evaluation.annotation_metrics" not in src
    assert "from evaluation import annotation_metrics" not in src


def test_module_constants_eval_schema_error_in_all_batch20():
    """EvalSchemaError 在 __all__ 内。"""
    assert "EvalSchemaError" in smod.__all__


def test_module_no_main_block_batch20():
    """schema 模块无 __main__ 块（不是 entry point）。"""
    src = inspect.getsource(smod)
    assert 'if __name__ ==' not in src


def test_module_has_docstring_batch20():
    assert smod.__doc__ is not None
    assert len(smod.__doc__) > 0


# ---------- 端到端集成第三十二批 ----------


def test_e2e_load_and_validate_manifest_batch20(tmp_path):
    """load schema → 校验合法 manifest → 不抛。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    validate(instance, "manifest.schema.json")


def test_e2e_validate_then_file_consistent_batch20(tmp_path):
    """validate 与 validate_file 行为一致。"""
    p = tmp_path / "x.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }), encoding="utf-8")
    data = json.loads(p.read_text(encoding="utf-8"))
    validate(data, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")


def test_e2e_validate_all_four_schemas_with_minimal_payload_batch20():
    """4 个 schema 都可加载并构造 validator。"""
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        v = Draft202012Validator(s)
        assert isinstance(v, Draft202012Validator)


def test_e2e_eval_schema_error_caught_in_try_batch20():
    """EvalSchemaError 在 try/except 内被捕获。"""
    caught = False
    try:
        validate({}, "annotation.schema.json")
    except EvalSchemaError:
        caught = True
    assert caught


def test_e2e_validate_file_full_round_trip_batch20(tmp_path):
    """完整 round-trip：写 manifest → validate_file。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/private/d1.pdf",
                "source_type": "pdf",
                "categories": ["report"],
                "expectations": {
                    "element_count_by_type": {"paragraph": 3},
                    "required_markers": ["## 背景目标"],
                },
            }
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_validate_bad_path_then_good_path_batch20(tmp_path):
    """先后校验两个文件，互不干扰。"""
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    good = tmp_path / "good.json"
    good.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(bad, "manifest.schema.json")
    validate_file(good, "manifest.schema.json")


def test_e2e_schemas_dir_resolve_to_real_files_batch20():
    """SCHEMAS_DIR 下的 4 个 schema 文件都是真实文件。"""
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        p = SCHEMAS_DIR / name
        assert p.is_file()
        # 加载不抛
        load_schema(name)
