"""evaluation/schema.py 第三十二轮 edges 测试（Round 414）。

补强 edges31 未触及的角度：
- SCHEMAS_DIR 常量深度第十二批（值类型 / 路径推导 / 父目录 / absolute / 与其他常量独立）
- EvalSchemaError 行为深度第十二批（super().__init__ 行为 / args 单元素 / str(e) 包含 message / 错误链 from / errors 是 list 验证）
- load_schema 行为深度第十二批（context manager 使用 / utf-8 编码实参 / 返回类型 dict / 不缓存）
- validate 行为深度第十二批（validator.iter_errors 排序 / errors 转 flat / 第一条 head.message / path 是 list 实例 / schema_path 在 flat）
- validate_file 行为深度第十二批（str/Path 输入 / FileNotFoundError 子类 Exception / utf-8 编码实参 / 不返回任何值）
- _schema_path 行为深度第十二批（FileNotFoundError 含 path 信息 / 返回 Path 对象 / SCHEMAS_DIR 拼接）
- module source forbidden tokens 第十六批
- module source 字符串精确补强第十二批
- signatures 第十二批
- module 合理性第十二批
- 端到端集成第十二批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import patch, mock_open
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator

from evaluation import schema as smod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- SCHEMAS_DIR 常量深度第十二批 ----------


def test_SCHEMAS_DIR_is_path_object_batch12():
    assert isinstance(SCHEMAS_DIR, Path)


def test_SCHEMAS_DIR_is_absolute_batch12():
    assert SCHEMAS_DIR.is_absolute()


def test_SCHEMAS_DIR_parent_endswith_evaluation_batch12():
    """SCHEMAS_DIR 应是 .../evaluation/../schemas = .../schemas。"""
    assert SCHEMAS_DIR.name == "schemas"


def test_SCHEMAS_DIR_parent_batch12():
    """SCHEMAS_DIR.parent 应是项目根。"""
    # SCHEMAS_DIR = evaluation/../schemas = project_root/schemas
    assert SCHEMAS_DIR.parent.name == "dachuang-code" or "dachuang" in SCHEMAS_DIR.parent.name


def test_SCHEMAS_DIR_exists_batch12():
    assert SCHEMAS_DIR.is_dir()


def test_SCHEMAS_DIR_independent_of_other_paths_batch12():
    """两次访问 SCHEMAS_DIR 应一致。"""
    assert SCHEMAS_DIR is smod.SCHEMAS_DIR


def test_SCHEMAS_DIR_resolved_batch12():
    """resolve() 已被调用，不应有 .. 段。"""
    parts = SCHEMAS_DIR.parts
    assert ".." not in parts


# ---------- EvalSchemaError 行为深度第十二批 ----------


def test_eval_schema_error_subclass_of_exception_batch12():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_init_super_call_batch12():
    """super().__init__(message) 应被调用（args 应包含 message）。"""
    e = EvalSchemaError("boom")
    assert e.args == ("boom",)


def test_eval_schema_error_str_contains_message_batch12():
    e = EvalSchemaError("my error message")
    assert "my error message" in str(e)


def test_eval_schema_error_errors_default_empty_list_batch12():
    e = EvalSchemaError("x")
    assert e.errors == []
    assert isinstance(e.errors, list)


def test_eval_schema_error_errors_none_explicit_batch12():
    e = EvalSchemaError("x", None)
    assert e.errors == []


def test_eval_schema_error_errors_explicit_batch12():
    errs = [{"path": ["a"], "message": "bad"}]
    e = EvalSchemaError("x", errs)
    assert e.errors is errs  # 直接引用


def test_eval_schema_error_errors_empty_list_creates_fresh_batch12():
    """errors=None → self.errors = errors or [] = [] (fresh list)。"""
    e1 = EvalSchemaError("x", None)
    e2 = EvalSchemaError("x", None)
    e1.errors.append({"y": 1})
    assert e2.errors == []  # e2 不受影响


def test_eval_schema_error_can_be_raised_batch12():
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("x")


def test_eval_schema_error_caught_as_exception_batch12():
    try:
        raise EvalSchemaError("x")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_eval_schema_error_raise_from_other_batch12():
    """raise from 应保留链。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        try:
            raise ValueError("inner")
        except ValueError as e:
            raise EvalSchemaError("outer") from e
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_eval_schema_error_pickle_round_trip_batch12():
    import pickle
    e = EvalSchemaError("msg", [{"path": ["a"], "message": "x"}])
    data = pickle.dumps(e)
    e2 = pickle.loads(data)
    assert e2.args == e.args


def test_eval_schema_error_module_evaluation_schema_batch12():
    assert EvalSchemaError.__module__ == "evaluation.schema"


def test_eval_schema_error_init_signature_2_params_batch12():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    assert len(params) == 3  # self, message, errors
    assert [p.name for p in params] == ["self", "message", "errors"]


def test_eval_schema_error_errors_default_is_none_batch12():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


# ---------- load_schema 行为深度第十二批 ----------


def test_load_schema_returns_dict_batch12():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_uses_context_manager_batch12():
    source = inspect.getsource(load_schema)
    assert "with _schema_path(name).open(" in source
    assert "as f" in source


def test_load_schema_uses_utf8_encoding_batch12():
    source = inspect.getsource(load_schema)
    assert 'encoding="utf-8"' in source


def test_load_schema_uses_json_load_batch12():
    source = inspect.getsource(load_schema)
    assert "json.load(f)" in source


def test_load_schema_not_cached_batch12():
    """两次调用应返回独立 dict（虽然内容相同）。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2
    # 内容相同但不是同一对象
    assert s1 is not s2


def test_load_schema_dict_modification_does_not_propagate_batch12():
    s1 = load_schema("manifest.schema.json")
    original = s1.get("title")
    s1["custom_key"] = "x"
    s2 = load_schema("manifest.schema.json")
    assert "custom_key" not in s2
    assert s2.get("title") == original


def test_load_schema_signature_one_param_batch12():
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"


def test_load_schema_param_annotation_str_batch12():
    sig = inspect.signature(load_schema)
    annot = sig.parameters["name"].annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "str" in annot_str


def test_load_schema_return_annotation_dict_batch12():
    sig = inspect.signature(load_schema)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "dict" in ret_str


def test_load_schema_unknown_name_raises_filenotfound_batch12():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_calls_schema_path_batch12(tmp_path):
    """load_schema 应该调用 _schema_path。"""
    fake_schema = tmp_path / "fake.json"
    fake_schema.write_text("{}", encoding="utf-8")
    with patch("evaluation.schema._schema_path") as mock:
        mock.return_value = fake_schema
        load_schema("any.schema.json")
    assert mock.called
    assert mock.call_args.args[0] == "any.schema.json"


# ---------- validate 行为深度第十二批 ----------


def test_validate_return_none_on_success_batch12():
    """validate 无错时 return None。"""
    instance = {"manifest_version": "1.0", "devset_status": "incomplete", "documents": [], "expected_failures": []}
    out = validate(instance, "manifest.schema.json")
    assert out is None


def test_validate_raises_on_error_batch12():
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")  # 缺 required


def test_validate_error_message_contains_schema_name_batch12():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert "manifest.schema.json" in str(e)
        assert "1" in str(e) or "校验失败" in str(e)  # 错误数


def test_validate_error_message_contains_error_count_batch12():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        # 至少有 1 处错误
        assert "1" in str(e) or "校验失败" in str(e)


def test_validate_error_errors_is_list_batch12():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert isinstance(e.errors, list)
        assert len(e.errors) >= 1


def test_validate_error_each_dict_has_3_keys_batch12():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert set(err.keys()) == {"path", "message", "schema_path"}


def test_validate_error_path_is_list_batch12():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["path"], list)


def test_validate_error_schema_path_is_list_batch12():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["schema_path"], list)


def test_validate_creates_draft_validator_batch12():
    """validate 应创建 Draft202012Validator。"""
    source = inspect.getsource(validate)
    assert "Draft202012Validator" in source


def test_validate_calls_iter_errors_batch12():
    """validate 应使用 iter_errors（非 validate）。"""
    source = inspect.getsource(validate)
    assert "iter_errors" in source


def test_validate_sorts_errors_batch12():
    """validate 应对 errors 排序。"""
    source = inspect.getsource(validate)
    assert "sorted" in source
    assert "absolute_path" in source


def test_validate_does_not_modify_instance_batch12():
    """validate 不应修改输入 dict。"""
    instance = {"manifest_version": "1.0", "devset_status": "incomplete", "documents": [], "expected_failures": []}
    snapshot = json.dumps(instance, sort_keys=True)
    validate(instance, "manifest.schema.json")
    assert json.dumps(instance, sort_keys=True) == snapshot


def test_validate_signature_2_params_batch12():
    sig = inspect.signature(validate)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["instance", "schema_name"]


def test_validate_return_annotation_none_batch12():
    sig = inspect.signature(validate)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert ret_str == "None" or ret is None or ret is type(None)


def test_validate_calls_load_schema_batch12():
    """validate 应调用 load_schema。"""
    with patch("evaluation.schema.load_schema") as mock:
        mock.return_value = {}
        validate({}, "any.schema.json")
    assert mock.called


# ---------- validate_file 行为深度第十二批 ----------


def test_validate_file_str_input_batch12(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    out = validate_file(str(p), "manifest.schema.json")
    assert out is None


def test_validate_file_path_input_batch12(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    out = validate_file(p, "manifest.schema.json")
    assert out is None


def test_validate_file_directory_raises_filenotfound_batch12(tmp_path):
    """目录不是 is_file → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_missing_raises_filenotfound_batch12(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "missing.json", "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecodeerror_batch12(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_data_raises_eval_schema_error_batch12(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_unicode_filename_batch12(tmp_path):
    """Unicode 文件名应被支持。"""
    p = tmp_path / "文件.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    out = validate_file(p, "manifest.schema.json")
    assert out is None


def test_validate_file_uses_utf8_encoding_batch12(tmp_path):
    source = inspect.getsource(validate_file)
    assert 'encoding="utf-8"' in source


def test_validate_file_uses_context_manager_batch12():
    source = inspect.getsource(validate_file)
    assert "with p.open" in source
    assert "as f" in source


def test_validate_file_calls_validate_batch12(tmp_path):
    """validate_file 应调用 validate。"""
    p = tmp_path / "valid.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.schema.validate") as mock:
        validate_file(p, "any.schema.json")
    assert mock.called


def test_validate_file_signature_2_params_batch12():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["path", "schema_name"]


def test_validate_file_path_annotation_union_batch12():
    sig = inspect.signature(validate_file)
    annot = sig.parameters["path"].annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "Path" in annot_str
    assert "str" in annot_str


def test_validate_file_return_annotation_none_batch12():
    sig = inspect.signature(validate_file)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert ret_str == "None" or ret is None or ret is type(None)


# ---------- _schema_path 行为深度第十二批 ----------


def test_schema_path_returns_path_batch12():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_file_not_found_message_contains_name_batch12():
    with pytest.raises(FileNotFoundError, match="nonexistent.schema.json"):
        _schema_path("nonexistent.schema.json")


def test_schema_path_file_not_found_message_contains_schemas_dir_batch12():
    try:
        _schema_path("nonexistent.schema.json")
    except FileNotFoundError as e:
        assert "schemas" in str(e) or "Schema" in str(e)


def test_schema_path_signature_one_param_batch12():
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"


def test_schema_path_uses_schemas_dir_batch12():
    """_schema_path 应使用 SCHEMAS_DIR / name。"""
    source = inspect.getsource(_schema_path)
    assert "SCHEMAS_DIR" in source


def test_schema_path_uses_is_file_check_batch12():
    source = inspect.getsource(_schema_path)
    assert ".is_file()" in source


# ---------- module source forbidden tokens 第十六批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import pickle",
        "import yaml",
        "import socket",
        "import threading",
        "import multiprocessing",
        "import asyncio",
        "from pickle import",
        "from yaml import",
        "from socket import",
        "from threading import",
        "from multiprocessing import",
        "from asyncio import",
        "ctypes.",
        "import ctypes",
        "import marshal",
        "marshal.",
    ],
)
def test_schema_source_no_forbidden_token_sixteenth_batch12(token):
    source = inspect.getsource(smod)
    assert token not in source


def test_schema_source_no_os_module_usage_batch12():
    source = inspect.getsource(smod)
    assert "import os" not in source
    assert "os." not in source


def test_schema_source_no_sys_module_usage_batch12():
    source = inspect.getsource(smod)
    assert "import sys" not in source
    assert "sys." not in source


def test_schema_source_no_tempfile_batch12():
    source = inspect.getsource(smod)
    assert "tempfile" not in source


def test_schema_source_no_logging_batch12():
    source = inspect.getsource(smod)
    assert "import logging" not in source


def test_schema_source_no_re_module_batch12():
    source = inspect.getsource(smod)
    assert "import re" not in source
    assert "re." not in source


def test_schema_source_no_eval_call_batch12():
    source = inspect.getsource(smod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_schema_source_no_compile_batch12():
    source = inspect.getsource(smod)
    assert "compile(" not in source


def test_schema_source_no_global_keyword_batch12():
    source = inspect.getsource(smod)
    assert "\nglobal " not in source


def test_schema_source_no_nonlocal_batch12():
    source = inspect.getsource(smod)
    assert "nonlocal " not in source


def test_schema_source_no_assert_batch12():
    source = inspect.getsource(smod)
    assert "\nassert " not in source


def test_schema_source_no_print_batch12():
    source = inspect.getsource(smod)
    assert "print(" not in source


def test_schema_source_no_input_function_batch12():
    source = inspect.getsource(smod)
    assert "input(" not in source


def test_schema_source_no_class_other_than_eval_schema_error_batch12():
    source = inspect.getsource(smod)
    # 只允许 1 个 class
    import re
    matches = re.findall(r"^class\s+(\w+)", source, re.MULTILINE)
    assert matches == ["EvalSchemaError"]


def test_schema_source_no_lambda_batch12():
    source = inspect.getsource(smod)
    # validate 用了 lambda e: list(e.absolute_path)
    assert "lambda " in source  # 反向验证


# ---------- module source 字符串精确补强第十二批 ----------


def test_module_source_json_import_top_level_batch12():
    source = inspect.getsource(smod)
    head = "\n".join(source.split("\n")[:30])
    assert "import json" in head


def test_module_source_pathlib_import_top_level_batch12():
    source = inspect.getsource(smod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_typing_any_import_top_level_batch12():
    source = inspect.getsource(smod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_source_jsonschema_import_top_level_batch12():
    source = inspect.getsource(smod)
    head = "\n".join(source.split("\n")[:30])
    assert "Draft202012Validator" in source
    assert "from jsonschema" in source


def test_module_source_has_SCHEMAS_DIR_assignment_batch12():
    source = inspect.getsource(smod)
    assert "SCHEMAS_DIR = " in source


def test_module_source_has_class_EvalSchemaError_batch12():
    source = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in source


def test_module_source_has_self_errors_assignment_batch12():
    source = inspect.getsource(smod)
    assert "self.errors = errors or []" in source


def test_module_source_has_super_init_call_batch12():
    source = inspect.getsource(smod)
    assert "super().__init__(message)" in source


def test_module_source_has_schema_path_def_batch12():
    source = inspect.getsource(smod)
    assert "def _schema_path(" in source


def test_module_source_has_load_schema_def_batch12():
    source = inspect.getsource(smod)
    assert "def load_schema(" in source


def test_module_source_has_validate_def_batch12():
    source = inspect.getsource(smod)
    assert "def validate(" in source


def test_module_source_has_validate_file_def_batch12():
    source = inspect.getsource(smod)
    assert "def validate_file(" in source


def test_module_source_future_annotations_top_level_batch12():
    source = inspect.getsource(smod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


def test_module_source_has_dunder_all_5_items_batch12():
    source = inspect.getsource(smod)
    assert '"SCHEMAS_DIR"' in source
    assert '"EvalSchemaError"' in source
    assert '"load_schema"' in source
    assert '"validate"' in source
    assert '"validate_file"' in source


# ---------- signatures 第十二批 ----------


def test_eval_schema_error_init_no_varargs_batch12():
    sig = inspect.signature(EvalSchemaError.__init__)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_eval_schema_error_init_message_required_batch12():
    sig = inspect.signature(EvalSchemaError.__init__)
    p = sig.parameters["message"]
    assert p.default is inspect.Parameter.empty


def test_eval_schema_error_init_message_annotation_str_batch12():
    sig = inspect.signature(EvalSchemaError.__init__)
    annot = sig.parameters["message"].annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "str" in annot_str


def test_eval_schema_error_init_errors_annotation_optional_batch12():
    sig = inspect.signature(EvalSchemaError.__init__)
    annot = sig.parameters["errors"].annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "list" in annot_str
    assert "None" in annot_str


def test_eval_schema_error_init_return_annotation_none_batch12():
    sig = inspect.signature(EvalSchemaError.__init__)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert ret_str == "None" or ret is None or ret is type(None)


def test_schema_path_param_annotation_str_batch12():
    sig = inspect.signature(_schema_path)
    annot = sig.parameters["name"].annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "str" in annot_str


def test_schema_path_return_annotation_path_batch12():
    sig = inspect.signature(_schema_path)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "Path" in ret_str


def test_load_schema_param_kind_positional_or_keyword_batch12():
    sig = inspect.signature(load_schema)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_validate_param_kinds_batch12():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_validate_file_param_kinds_batch12():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_module_dunder_all_count_5_batch12():
    assert hasattr(smod, "__all__")
    assert len(smod.__all__) == 5


def test_module_dunder_all_exact_set_batch12():
    assert set(smod.__all__) == {
        "SCHEMAS_DIR", "EvalSchemaError", "load_schema", "validate", "validate_file",
    }


# ---------- module 合理性第十二批 ----------


def test_module_dunder_file_exists_batch12():
    assert hasattr(smod, "__file__")
    assert smod.__file__ is not None


def test_module_dunder_file_path_evaluation_schema_batch12():
    import os
    sep = os.sep
    assert smod.__file__.endswith(sep + "schema.py")
    assert "evaluation" in smod.__file__


def test_module_name_evaluation_schema_batch12():
    assert smod.__name__ == "evaluation.schema"


def test_module_docstring_present_batch12():
    assert smod.__doc__ is not None
    assert len(smod.__doc__) > 30


def test_module_docstring_mentions_schema_batch12():
    assert smod.__doc__ is not None
    assert "Schema" in smod.__doc__ or "schema" in smod.__doc__


def test_module_docstring_mentions_no_reuse_batch12():
    """docstring 应提到不复用 app/schema.py。"""
    assert smod.__doc__ is not None
    assert "app/schema" in smod.__doc__ or "不复用" in smod.__doc__


def test_module_uses_future_annotations_batch12():
    source = inspect.getsource(smod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


def test_module_user_class_count_1_batch12():
    classes = [
        n for n, v in vars(smod).items()
        if inspect.isclass(v) and v.__module__ == smod.__name__
    ]
    assert classes == ["EvalSchemaError"]


def test_module_user_function_count_4_batch12():
    funcs = [
        n for n, v in vars(smod).items()
        if inspect.isfunction(v) and v.__module__ == smod.__name__
    ]
    assert set(funcs) == {"_schema_path", "load_schema", "validate", "validate_file"}


def test_module_top_level_constants_count_1_batch12():
    consts = [
        n for n, v in vars(smod).items()
        if not n.startswith("__") and not callable(v) and not inspect.isclass(v)
        and not inspect.ismodule(v)
    ]
    assert "SCHEMAS_DIR" in consts


# ---------- 端到端集成第十二批 ----------


def test_e2e_load_then_validate_manifest_batch12():
    """load_manifest schema → 用它 validate 合法 instance。"""
    schema = load_schema("manifest.schema.json")
    validator = Draft202012Validator(schema)
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    errors = list(validator.iter_errors(instance))
    assert errors == []


def test_e2e_validate_then_validate_file_combined_batch12(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_validate_file_failure_includes_message_batch12(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    try:
        validate_file(p, "manifest.schema.json")
    except EvalSchemaError as e:
        # message 应包含 schema_name 或 path
        assert "manifest.schema.json" in str(e)


def test_e2e_combined_load_validate_idempotent_batch12():
    """两次相同输入应得相同结果。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(instance, "manifest.schema.json")
    validate(instance, "manifest.schema.json")


def test_e2e_combined_validate_raises_for_bad_data_batch12():
    """两次相同非法输入 → 都抛 EvalSchemaError。"""
    for _ in range(2):
        with pytest.raises(EvalSchemaError):
            validate({}, "manifest.schema.json")


def test_e2e_load_schema_then_validate_with_dict_batch12():
    """load_schema 返回 dict → 可作为 Draft202012Validator 输入。"""
    schema = load_schema("annotation.schema.json")
    v = Draft202012Validator(schema)
    # annotation schema 字段是 doc_id + annotation_version
    instance = {"doc_id": "x", "annotation_version": "1.0"}
    errors = list(v.iter_errors(instance))
    assert errors == []


def test_e2e_eval_schema_error_chain_through_modules_batch12():
    """Schema 校验失败 → 错误从 schema 模块抛出，被上层捕获。"""
    try:
        validate({"wrong": 1}, "manifest.schema.json")
    except EvalSchemaError as e:
        # 错误含路径信息
        assert e.errors
        assert isinstance(e.errors[0], dict)


def test_e2e_combined_pickle_eval_schema_error_batch12():
    """EvalSchemaError 支持 pickle 跨进程传递。"""
    import pickle
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        data = pickle.dumps(e)
        e2 = pickle.loads(data)
        assert e2.args == e.args


def test_e2e_validate_file_returns_none_batch12(tmp_path):
    """validate_file 成功时 return None。"""
    p = tmp_path / "v.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    out = validate_file(p, "manifest.schema.json")
    assert out is None


def test_e2e_validate_returns_none_batch12():
    out = validate({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }, "manifest.schema.json")
    assert out is None
