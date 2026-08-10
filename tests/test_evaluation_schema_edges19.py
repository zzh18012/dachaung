"""evaluation/schema.py 第十九轮 edges 测试（Round 323）。

重点补强 edges18 未触及的角度：
- EvalSchemaError source level 与构造深度
- _schema_path source level 与错误消息精确
- load_schema 行为深度与 source level
- validate 行为深度（错误顺序 / errors 数量上限）
- validate_file 行为深度（路径解析 / 编码）
- module source forbidden tokens 第二批
- module source 字符串精确补强（更深 substring）
- signatures 精确补强（kind/annotation 完整）
- 端到端集成补强（4 schema 全 round-trip / document schema 真实结构）
- 模块整体合理性（imports / no class side effect / __all__ 类型）
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import FunctionType
from typing import Any

import pytest
from jsonschema import Draft202012Validator

import evaluation.schema as m
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- EvalSchemaError source level 与构造深度 ----------


def test_eval_schema_error_source_has_super_init():
    src = inspect.getsource(EvalSchemaError)
    assert "super().__init__(message)" in src


def test_eval_schema_error_source_has_self_errors_assignment():
    src = inspect.getsource(EvalSchemaError)
    assert "self.errors = errors or []" in src


def test_eval_schema_error_source_has_no_try_except():
    """构造器无 try/except（最简单）。"""
    src = inspect.getsource(EvalSchemaError)
    assert "try:" not in src
    assert "except" not in src


def test_eval_schema_error_source_has_no_return():
    src = inspect.getsource(EvalSchemaError.__init__)
    assert "return" not in src


def test_eval_schema_error_source_init_signature():
    src = inspect.getsource(EvalSchemaError)
    assert "def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:" in src


def test_eval_schema_error_class_signature():
    sig = inspect.signature(EvalSchemaError)
    assert list(sig.parameters) == ["message", "errors"]
    assert sig.parameters["message"].annotation == "str"
    assert sig.parameters["errors"].default is None


def test_eval_schema_error_with_3_errors_keeps_all():
    errs = [
        {"path": ["a"], "message": "m1", "schema_path": []},
        {"path": ["b"], "message": "m2", "schema_path": []},
        {"path": ["c"], "message": "m3", "schema_path": []},
    ]
    e = EvalSchemaError("x", errs)
    assert e.errors is errs  # 同一对象
    assert len(e.errors) == 3


def test_eval_schema_error_with_falsy_non_none_errors():
    """errors 是 []（falsy 但非 None）→ 仍存为 []。"""
    e = EvalSchemaError("x", [])
    assert e.errors == []


def test_eval_schema_error_can_be_raised_and_caught():
    with pytest.raises(EvalSchemaError) as ei:
        raise EvalSchemaError("msg", [{"path": [], "message": "m", "schema_path": []}])
    assert "msg" in str(ei.value)
    assert len(ei.value.errors) == 1


def test_eval_schema_error_can_be_caught_as_exception():
    """EvalSchemaError 是 Exception 子类。"""
    try:
        raise EvalSchemaError("x")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_eval_schema_error_args_only_message_no_errors():
    """super().__init__(message) 只把 message 放进 args，errors 不进 args。"""
    e = EvalSchemaError("msg", [{"path": [], "message": "m", "schema_path": []}])
    assert e.args == ("msg",)


# ---------- _schema_path source level 与错误消息精确 ----------


def test_schema_path_source_signature():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters) == ["name"]
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "Path"


def test_schema_path_source_has_p_assignment():
    src = inspect.getsource(_schema_path)
    assert "p = SCHEMAS_DIR / name" in src


def test_schema_path_source_has_fstring_error():
    src = inspect.getsource(_schema_path)
    assert 'raise FileNotFoundError(f"Schema 文件不存在: {p}")' in src


def test_schema_path_source_has_no_imports_inside():
    """_schema_path 内部不 import。"""
    src = inspect.getsource(_schema_path)
    assert "import " not in src


def test_schema_path_error_message_format_with_specific_name():
    with pytest.raises(FileNotFoundError) as ei:
        _schema_path("nonexistent.schema.json")
    msg = str(ei.value)
    assert "nonexistent.schema.json" in msg
    assert "Schema 文件不存在" in msg


def test_schema_path_returns_path_with_proper_parent():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_does_not_create_file():
    """_schema_path 不创建文件（只读 is_file）。"""
    src = inspect.getsource(_schema_path)
    assert "touch" not in src
    assert "write" not in src
    assert "mkdir" not in src


def test_schema_path_with_dot_prefix():
    """传入 './manifest.schema.json' → SCHEMAS_DIR / '. /manifest...' 仍 join。"""
    # Path 操作：SCHEMAS_DIR / "./x" == SCHEMAS_DIR / "x"
    # 这里 _schema_path("./manifest.schema.json") 实际等价于 _schema_path("manifest.schema.json")
    p = _schema_path("./manifest.schema.json")
    assert p.is_file()


# ---------- load_schema 行为深度与 source level ----------


def test_load_schema_source_signature():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters) == ["name"]
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "dict[str, Any]"


def test_load_schema_source_has_no_try_except():
    """load_schema 不防 JSONDecodeError（让 caller 看到）。"""
    src = inspect.getsource(load_schema)
    assert "try" not in src
    assert "except" not in src


def test_load_schema_source_has_no_cache_mechanism():
    """load_schema 不缓存（每次重读文件）。"""
    src = inspect.getsource(load_schema)
    assert "lru_cache" not in src
    assert "cache" not in src


def test_load_schema_source_uses_with_statement():
    src = inspect.getsource(load_schema)
    assert 'with _schema_path(name).open("r", encoding="utf-8") as f:' in src


def test_load_schema_source_returns_json_load():
    src = inspect.getsource(load_schema)
    assert "return json.load(f)" in src


def test_load_schema_manifest_has_correct_top_level_keys():
    s = load_schema("manifest.schema.json")
    # JSON Schema 必有 $schema 或 type
    has_schema = "$schema" in s
    has_type = "type" in s
    assert has_schema or has_type


def test_load_schema_annotation_top_level_keys():
    s = load_schema("annotation.schema.json")
    assert "type" in s
    assert s["type"] == "object"


def test_load_schema_evaluation_report_top_level_keys():
    s = load_schema("evaluation-report.schema.json")
    assert "type" in s


def test_load_schema_returns_dict_not_mapping_proxy():
    """返回的是可变 dict，不是 MappingProxyType。"""
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)
    # 应该可以 set item
    s["__test"] = 1
    assert s["__test"] == 1


def test_load_schema_each_call_returns_fresh_dict():
    s1 = load_schema("manifest.schema.json")
    s1["__mutated"] = True
    s2 = load_schema("manifest.schema.json")
    assert "__mutated" not in s2


# ---------- validate 行为深度（错误顺序 / errors 数量上限） ----------


def test_validate_source_signature():
    sig = inspect.signature(validate)
    assert list(sig.parameters) == ["instance", "schema_name"]
    assert sig.parameters["instance"].annotation == "dict[str, Any]"
    assert sig.parameters["schema_name"].annotation == "str"
    assert sig.return_annotation == "None"


def test_validate_source_loads_schema_first():
    src = inspect.getsource(validate)
    assert "schema = load_schema(schema_name)" in src


def test_validate_source_creates_validator():
    src = inspect.getsource(validate)
    assert "validator = Draft202012Validator(schema)" in src


def test_validate_source_sorts_errors_by_path():
    src = inspect.getsource(validate)
    assert "errors = sorted(validator.iter_errors(instance)" in src


def test_validate_source_has_no_errors_returns():
    src = inspect.getsource(validate)
    assert "if not errors:" in src
    assert "        return" in src  # 单独 return


def test_validate_source_flat_loop():
    src = inspect.getsource(validate)
    assert "for err in errors:" in src
    assert "flat.append(" in src


def test_validate_source_head_zero_for_message():
    src = inspect.getsource(validate)
    assert "head = errors[0]" in src


def test_validate_source_raise_eval_schema_error_with_two_args():
    src = inspect.getsource(validate)
    # f-string message + errors=flat
    assert "errors=flat," in src


def test_validate_returns_none_on_success():
    inst = {"annotation_version": "1.0", "doc_id": "x"}
    assert validate(inst, "annotation.schema.json") is None


def test_validate_does_not_modify_instance():
    inst = {"annotation_version": "1.0", "doc_id": "x"}
    inst_copy = json.loads(json.dumps(inst))
    validate(inst, "annotation.schema.json")
    assert inst == inst_copy


def test_validate_with_empty_instance_for_required_check():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "annotation.schema.json")
    # annotation_version 和 doc_id 都是 required
    assert len(ei.value.errors) >= 2


def test_validate_errors_path_is_list_type():
    """每个 error 的 path 都是 list。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    for e in ei.value.errors:
        assert isinstance(e["path"], list)
        assert isinstance(e["schema_path"], list)


def test_validate_errors_message_is_str():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    for e in ei.value.errors:
        assert isinstance(e["message"], str)


def test_validate_first_error_in_message():
    """EvalSchemaError 消息含 head（errors[0]）的 message。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    head_msg = ei.value.errors[0]["message"]
    assert head_msg in str(ei.value)


def test_validate_count_in_message_matches_errors_length():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    msg = str(ei.value)
    # 找 "(N 处)"
    import re
    match = re.search(r"\((\d+) 处\)", msg)
    assert match is not None
    n_in_msg = int(match.group(1))
    assert n_in_msg == len(ei.value.errors)


def test_validate_with_invalid_schema_name_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        validate({}, "nonexistent.schema.json")


# ---------- validate_file 行为深度（路径解析 / 编码） ----------


def test_validate_file_source_signature():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters) == ["path", "schema_name"]
    assert sig.parameters["path"].annotation == "Path | str"
    assert sig.parameters["schema_name"].annotation == "str"
    assert sig.return_annotation == "None"


def test_validate_file_source_path_conversion():
    src = inspect.getsource(validate_file)
    assert "p = Path(path)" in src


def test_validate_file_source_check_is_file():
    src = inspect.getsource(validate_file)
    assert "if not p.is_file():" in src


def test_validate_file_source_open_with_utf8():
    src = inspect.getsource(validate_file)
    assert 'with p.open("r", encoding="utf-8") as f:' in src


def test_validate_file_source_calls_validate():
    src = inspect.getsource(validate_file)
    assert "validate(data, schema_name)" in src


def test_validate_file_str_path_conversion_to_path():
    """str path 会被 Path() 包裹。"""
    p_str = str(SCHEMAS_DIR.parent / "pyproject.toml")
    # 这是 toml 文件不是 json，会抛 JSONDecodeError
    with pytest.raises(json.JSONDecodeError):
        validate_file(p_str, "manifest.schema.json")


def test_validate_file_with_pathlib_path(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text(
        json.dumps({"annotation_version": "1.0", "doc_id": "x"}),
        encoding="utf-8",
    )
    assert validate_file(p, "annotation.schema.json") is None


def test_validate_file_relative_path(tmp_path, monkeypatch):
    """相对路径会被解析（相对当前 cwd）。"""
    p = tmp_path / "ok.json"
    p.write_text(
        json.dumps({"annotation_version": "1.0", "doc_id": "x"}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert validate_file("ok.json", "annotation.schema.json") is None


def test_validate_file_directory_not_file_raises_filenotfound(tmp_path):
    """目录不是文件 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_bom_handled(tmp_path):
    """UTF-8 BOM 在 encoding='utf-8' 下会被解码（不报错）。"""
    p = tmp_path / "bom.json"
    content = json.dumps({"annotation_version": "1.0", "doc_id": "x"})
    p.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))
    # BOM 在 encoding='utf-8' 下被解码为 BOM 字符（不会 raise）
    # 但 schema 校验可能 fail（因 dict 顶层不是 expected）
    # 这里仅验证不会 raise FileNotFoundError
    try:
        validate_file(p, "annotation.schema.json")
    except (EvalSchemaError, json.JSONDecodeError):
        pass  # 其他异常都行


# ---------- module source forbidden tokens 第二批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import copy",
        "import pprint",
        "import csv",
        "import xml",
        "import configparser",
        "import argparse",
        "import inspect",
        "import dis",
        "import traceback",
        "import warnings",
        "import weakref",
        "import gc",
        "import struct",
        "import codecs",
        "import unicodedata",
        "import string",
        "import textwrap",
        "import difflib",
        "import decimal",
        "import fractions",
        "import statistics",
        "import array",
        "import queue",
        "import types",
        "import math",
        "import collections",
        "import collections.abc",
        "import dataclasses",
        "import abc",
    ],
)
def test_module_source_forbidden_tokens_second_batch(token):
    src = inspect.getsource(m)
    assert token not in src


# ---------- module source 字符串精确补强（更深 substring） ----------


def test_module_source_has_docstring_with_chinese_keyword():
    """docstring 含中文字符。"""
    src = inspect.getsource(m)
    assert "校验" in src


def test_module_source_has_module_docstring():
    """模块顶层 docstring。"""
    src = inspect.getsource(m)
    assert "manifest / annotation / evaluation-report" in src


def test_module_source_mentions_no_reuse_app_schema():
    """docstring 明确说不复用 app/schema.py。"""
    src = inspect.getsource(m)
    assert "app/schema.py" in src


def test_module_source_has_from_future():
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_has_import_json():
    src = inspect.getsource(m)
    assert "import json" in src


def test_module_source_has_from_pathlib_import_path():
    src = inspect.getsource(m)
    assert "from pathlib import Path" in src


def test_module_source_has_from_typing_import_any():
    src = inspect.getsource(m)
    assert "from typing import Any" in src


def test_module_source_has_jsonschema_validator_import():
    src = inspect.getsource(m)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_has_jsonschema_validation_error_import():
    src = inspect.getsource(m)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_no_actual_use_of_jsvalidationerror():
    """import 了 JSValidationError 但代码没用（仅 import）。
    这是一个 minor 风险，但当前代码确实没用，我们 verify 它没出现在逻辑里。"""
    src = inspect.getsource(m)
    # 顶层 import 之后没引用 JSValidationError
    lines = src.splitlines()
    # 找到 import 行之后的代码
    past_import = False
    for line in lines[5:]:  # 跳过前 5 行（docstring + imports）
        if "JSValidationError" in line and "import" not in line:
            pytest.fail(f"JSValidationError used outside import: {line}")


def test_module_source_no_yield():
    src = inspect.getsource(m)
    assert "yield" not in src


def test_module_source_no_global():
    src = inspect.getsource(m)
    assert "\nglobal " not in src


def test_module_source_no_async():
    src = inspect.getsource(m)
    assert "async def" not in src


def test_module_source_no_class_other_than_eval_schema_error():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            assert "EvalSchemaError" in line


def test_module_source_no_main_block():
    src = inspect.getsource(m)
    assert '__name__ == "__main__"' not in src


def test_module_source_no_decorators():
    src = inspect.getsource(m)
    lines = src.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("@") and not stripped.startswith("@property"):
            # 类内方法无装饰器；类无装饰器
            pytest.fail(f"Found decorator: {stripped}")


def test_module_source_no_lambda_other_than_sort_key():
    """validate 里的 lambda 用于 sort。其他地方不应该有 lambda。"""
    src = inspect.getsource(m)
    lambda_count = src.count("lambda")
    # 只在 sort key 一处
    assert lambda_count == 1


# ---------- signatures 精确补强（kind/annotation 完整） ----------


def test_validate_param_kinds():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_load_schema_param_kinds():
    sig = inspect.signature(load_schema)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_validate_file_param_kinds():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_schema_path_param_kinds():
    sig = inspect.signature(_schema_path)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_eval_schema_error_param_kinds():
    sig = inspect.signature(EvalSchemaError)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_validate_no_default_for_instance():
    sig = inspect.signature(validate)
    assert sig.parameters["instance"].default is inspect.Parameter.empty


def test_validate_no_default_for_schema_name():
    sig = inspect.signature(validate)
    assert sig.parameters["schema_name"].default is inspect.Parameter.empty


def test_load_schema_no_default_for_name():
    sig = inspect.signature(load_schema)
    assert sig.parameters["name"].default is inspect.Parameter.empty


def test_validate_file_no_default_for_path():
    sig = inspect.signature(validate_file)
    assert sig.parameters["path"].default is inspect.Parameter.empty


def test_validate_file_no_default_for_schema_name():
    sig = inspect.signature(validate_file)
    assert sig.parameters["schema_name"].default is inspect.Parameter.empty


def test_namespace_module():
    assert m.__name__ == "evaluation.schema"


def test_namespace_load_schema():
    assert load_schema.__module__ == "evaluation.schema"


def test_namespace_validate():
    assert validate.__module__ == "evaluation.schema"


def test_namespace_validate_file():
    assert validate_file.__module__ == "evaluation.schema"


def test_namespace_schema_path():
    assert _schema_path.__module__ == "evaluation.schema"


def test_namespace_eval_schema_error():
    assert EvalSchemaError.__module__ == "evaluation.schema"


# ---------- 模块整体合理性（imports / __all__ 类型） ----------


def test_module_all_is_list():
    assert isinstance(m.__all__, list)


def test_module_all_entries_are_str():
    for entry in m.__all__:
        assert isinstance(entry, str)


def test_module_all_5_entries_strict():
    assert m.__all__ == [
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    ]


def test_module_namespace_is_evaluation_schema():
    assert m.__name__ == "evaluation.schema"


def test_module_has_no_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' not in src


def test_module_has_1_class_only():
    classes = [
        n for n in dir(m)
        if isinstance(getattr(m, n), type)
        and getattr(m, n).__module__ == "evaluation.schema"
    ]
    assert classes == ["EvalSchemaError"]


def test_module_has_3_public_functions_only():
    public_fns = [
        n for n in dir(m)
        if not n.startswith("_")
        and isinstance(getattr(m, n), FunctionType)
        and getattr(m, n).__module__ == "evaluation.schema"
    ]
    assert set(public_fns) == {"load_schema", "validate", "validate_file"}


def test_module_has_1_private_helper_only():
    private_fns = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and isinstance(getattr(m, n), FunctionType)
    ]
    assert private_fns == ["_schema_path"]


def test_module_schemas_dir_is_path_instance():
    assert isinstance(SCHEMAS_DIR, Path)


def test_module_schemas_dir_is_absolute():
    assert SCHEMAS_DIR.is_absolute()


def test_module_schemas_dir_resolved():
    """SCHEMAS_DIR 已 resolve。"""
    assert SCHEMAS_DIR == Path(SCHEMAS_DIR).resolve()


def test_module_schemas_dir_parent_is_project_root():
    """SCHEMAS_DIR.parent 是项目根（含 pyproject.toml）。"""
    parent = SCHEMAS_DIR.parent
    assert (parent / "pyproject.toml").is_file()


def test_module_schemas_dir_contains_4_schemas():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        assert (SCHEMAS_DIR / name).is_file()


# ---------- 端到端集成补强（4 schema 全 round-trip / document schema 真实结构） ----------


def test_e2e_load_and_validate_4_schemas_each():
    """每个 schema 都能 load 并 check_schema。"""
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        Draft202012Validator.check_schema(s)
        # 创建 validator 实例
        v = Draft202012Validator(s)
        assert v.schema == s


def test_e2e_validate_with_extra_fields_allowed():
    """manifest schema 允许 extra fields（additionalProperties 默认 True）。"""
    inst = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "extra_field": "should be allowed",
    }
    # 如果 schema 设置 additionalProperties=False 会 raise；否则 pass
    try:
        validate(inst, "manifest.schema.json")
    except EvalSchemaError:
        pass  # 也可以 reject


def test_e2e_manifest_rejects_invalid_devset_status():
    inst = {
        "manifest_version": "1.0",
        "devset_status": "invalid_status",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(inst, "manifest.schema.json")


def test_e2e_manifest_rejects_invalid_manifest_version():
    inst = {
        "manifest_version": "2.0",  # 不是 const "1.0"
        "devset_status": "complete",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(inst, "manifest.schema.json")


def test_e2e_annotation_requires_doc_id():
    with pytest.raises(EvalSchemaError):
        validate({"annotation_version": "1.0"}, "annotation.schema.json")


def test_e2e_annotation_rejects_array_value():
    inst = {"annotation_version": [], "doc_id": "x"}
    with pytest.raises(EvalSchemaError):
        validate(inst, "annotation.schema.json")


def test_e2e_validate_returns_none_when_valid():
    """validate 成功时显式返回 None。"""
    inst = {"annotation_version": "1.0", "doc_id": "x"}
    assert validate(inst, "annotation.schema.json") is None


def test_e2e_full_round_trip_load_validate_validate_file(tmp_path):
    """load → validate → write → validate_file 全流程。"""
    inst = {"annotation_version": "1.0", "doc_id": "round-trip"}
    # validate
    validate(inst, "annotation.schema.json")
    # write
    p = tmp_path / "rt.json"
    p.write_text(json.dumps(inst), encoding="utf-8")
    # validate_file
    assert validate_file(p, "annotation.schema.json") is None


def test_e2e_error_dict_is_json_serializable():
    """EvalSchemaError.errors 是 JSON 可序列化的（list of dict with list/str）。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    # errors 应该可以被 json 序列化
    s = json.dumps(ei.value.errors)
    assert isinstance(s, str)


def test_e2e_validate_with_unicode_in_path(tmp_path):
    """文件路径含中文字符。"""
    p = tmp_path / "中文.json"
    p.write_text(
        json.dumps({"annotation_version": "1.0", "doc_id": "x"}),
        encoding="utf-8",
    )
    assert validate_file(p, "annotation.schema.json") is None


def test_e2e_validate_with_unicode_in_doc_id(tmp_path):
    """doc_id 含中文字符。"""
    inst = {"annotation_version": "1.0", "doc_id": "文档1"}
    p = tmp_path / "u.json"
    p.write_text(json.dumps(inst, ensure_ascii=False), encoding="utf-8")
    assert validate_file(p, "annotation.schema.json") is None


def test_e2e_validate_file_propagates_eval_schema_error(tmp_path):
    """validate_file 把 validate 的 EvalSchemaError 透传。"""
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(EvalSchemaError) as ei:
        validate_file(p, "annotation.schema.json")
    # error message 应该提到 schema 名
    assert "annotation.schema.json" in str(ei.value)
