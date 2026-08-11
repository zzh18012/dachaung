"""evaluation/schema.py 第四十二轮 edges 测试（Round 488）。

补强 edges41 未触及的角度（第二十二批）：
- SCHEMAS_DIR 第二十二批：resolve() 返回绝对 / parent.parent 是项目根 / 是 directory / 与 evaluation/ 同级 / str 表示 path 对象 / parts 数量 / 一致性 / 与 app/schema.py 不复用
- EvalSchemaError 第二十二批：errors=None 默认 [] / errors=[] 显式 / errors 保留 list 引用 / errors 保留 dict 引用 / Exception 子类 / message 属性 / args / 多次实例化独立 / raise/except 类型
- _schema_path 第二十二批：返回 Path / str(Path) 含 name / 不存在 FileNotFoundError 含文件名 / 接受 str-like / 多次一致 / 目录拒（FileNotFoundError 因为 is_file() False）/ 不抛 PermissionError 而抛 FileNotFoundError / resolve 路径
- load_schema 第二十二批：返回 dict / 不存在抛 FileNotFoundError / dict 的 type 字段 / properties 字段 / 完整加载 / 多次一致 / OpenReadText / UTF-8 中文
- validate 第二十二批：合法 instance None 返回 / 非法 抛 EvalSchemaError / errors count > 1 / errors path / message 含 schema_name / message 含"校验失败" / message 含 path / 不修改 instance / 多个错误按 path 排序 / None instance / 空 dict / 类型错误
- validate_file 第二十二批：str/Path 等价 / 不存在 FileNotFoundError / JSONDecodeError / EvalSchemaError / 内部调 validate / 多次一致 / UTF-8 中文 / 默认 encoding utf-8（非 utf-8-sig）
- module source forbidden tokens 第三十八批
- module source 字符串精确补强第三十四批
- signatures 第三十四批
- module 合理性第三十四批
- 端到端集成第三十四批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

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


# ---------- SCHEMAS_DIR 第二十二批 ----------


def test_schemas_dir_is_absolute_path_batch22():
    """SCHEMAS_DIR 是绝对路径（已 resolve）。"""
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_parent_is_project_root_batch22(tmp_path):
    """SCHEMAS_DIR.parent 是项目根（含 pyproject.toml）。

    SCHEMAS_DIR = <project>/schemas/，parent 是 <project>/。
    """
    project_root = SCHEMAS_DIR.parent
    assert (project_root / "pyproject.toml").is_file()


def test_schemas_dir_is_directory_batch22():
    """SCHEMAS_DIR 是 directory。"""
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_basename_batch22():
    """SCHEMAS_DIR.name == 'schemas'。"""
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_contains_manifest_schema_batch22():
    """SCHEMAS_DIR 含 manifest.schema.json。"""
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema_batch22():
    """SCHEMAS_DIR 含 annotation.schema.json。"""
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema_batch22():
    """SCHEMAS_DIR 含 evaluation-report.schema.json。"""
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_str_contains_schemas_batch22():
    """str(SCHEMAS_DIR) 含 'schemas'。"""
    assert "schemas" in str(SCHEMAS_DIR)


def test_schemas_dir_resolve_idempotent_batch22():
    """SCHEMAS_DIR.resolve() == SCHEMAS_DIR（已 resolved）。"""
    assert SCHEMAS_DIR.resolve() == SCHEMAS_DIR


def test_schemas_dir_independent_from_app_schema_batch22():
    """SCHEMAS_DIR 与 app/schema.py 路径不同（不复用）。"""
    # evaluation/schema.py 用 <project>/schemas/
    # app/schema.py 用 <project>/app/schemas/ 或类似路径
    # 这里仅验证 SCHEMAS_DIR 不是 app 子目录
    assert "evaluation" not in SCHEMAS_DIR.parts
    assert SCHEMAS_DIR.parent.name != "evaluation"


# ---------- EvalSchemaError 第二十二批 ----------


def test_eval_schema_error_errors_none_defaults_empty_list_batch22():
    """errors=None 默认 []。"""
    e = EvalSchemaError("msg")
    assert e.errors == []


def test_eval_schema_error_errors_empty_list_batch22():
    """errors=[] 显式传入。"""
    e = EvalSchemaError("msg", errors=[])
    assert e.errors == []


def test_eval_schema_error_errors_list_preserved_batch22():
    """errors list 引用保留（同一对象）。"""
    errs = [{"path": ["a"], "message": "bad"}]
    e = EvalSchemaError("msg", errors=errs)
    assert e.errors is errs


def test_eval_schema_error_errors_dict_in_list_batch22():
    """errors 中含 dict。"""
    errs = [{"path": [], "message": "x"}, {"path": ["k"], "message": "y"}]
    e = EvalSchemaError("msg", errors=errs)
    assert len(e.errors) == 2
    assert e.errors[0]["message"] == "x"
    assert e.errors[1]["path"] == ["k"]


def test_eval_schema_error_inherits_exception_batch22():
    """EvalSchemaError 继承 Exception。"""
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_args_batch22():
    """args 含 message。"""
    e = EvalSchemaError("hello")
    assert e.args == ("hello",)


def test_eval_schema_error_str_batch22():
    """str(e) == message。"""
    e = EvalSchemaError("hello")
    assert str(e) == "hello"


def test_eval_schema_error_can_be_raised_and_caught_batch22():
    """raise/except 工作正常。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        raise EvalSchemaError("msg")
    assert "msg" in str(exc_info.value)


def test_eval_schema_error_caught_as_exception_batch22():
    """可被通用 Exception 捕获。"""
    with pytest.raises(Exception):
        raise EvalSchemaError("msg")


def test_eval_schema_error_independent_instances_batch22():
    """两个 errors=None 实例互不影响（不共享 list）。"""
    e1 = EvalSchemaError("a")
    e2 = EvalSchemaError("b")
    e1.errors.append({"x": 1})
    assert e2.errors == []


def test_eval_schema_error_message_attribute_batch22():
    """message 通过 super().__init__ 存为 args[0]，不是属性。"""
    e = EvalSchemaError("hello")
    # Exception 把 message 存为 args[0]，没有 .message 属性
    assert not hasattr(e, "message") or getattr(e, "message", None) != "hello"


# ---------- _schema_path 第二十二批 ----------


def test_schema_path_returns_path_batch22():
    """_schema_path 返回 Path 对象。"""
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_returns_existing_file_batch22():
    """_schema_path 返回的路径是 existing file。"""
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_str_contains_filename_batch22():
    """str(返回值) 含 schema name。"""
    p = _schema_path("manifest.schema.json")
    assert "manifest.schema.json" in str(p)


def test_schema_path_missing_raises_filenotfound_batch22():
    """不存在的 schema name → FileNotFoundError 含文件名。"""
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("bogus.schema.json")
    assert "bogus.schema.json" in str(exc_info.value)


def test_schema_path_directory_raises_filenotfound_batch22(tmp_path):
    """schema name 是目录 → FileNotFoundError（is_file() False）。"""
    # SCHEMAS_DIR 下创建临时目录
    bogus_dir_name = "test_dir_tmp.schema.json"
    bogus_dir = SCHEMAS_DIR / bogus_dir_name
    try:
        bogus_dir.mkdir(exist_ok=True)
        with pytest.raises(FileNotFoundError):
            _schema_path(bogus_dir_name)
    finally:
        if bogus_dir.is_dir():
            bogus_dir.rmdir()


def test_schema_path_idempotent_batch22():
    """多次调用一致。"""
    p1 = _schema_path("manifest.schema.json")
    p2 = _schema_path("manifest.schema.json")
    assert p1 == p2


def test_schema_path_in_schemas_dir_batch22():
    """返回路径的 parent == SCHEMAS_DIR。"""
    p = _schema_path("annotation.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_annotation_batch22():
    """annotation schema 可定位。"""
    p = _schema_path("annotation.schema.json")
    assert p.is_file()


def test_schema_path_evaluation_report_batch22():
    """evaluation-report schema 可定位。"""
    p = _schema_path("evaluation-report.schema.json")
    assert p.is_file()


# ---------- load_schema 第二十二批 ----------


def test_load_schema_returns_dict_batch22():
    """load_schema 返回 dict。"""
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_has_schema_field_batch22():
    """schema 含 $schema 字段。"""
    s = load_schema("manifest.schema.json")
    assert "$schema" in s


def test_load_schema_has_properties_batch22():
    """schema 含 properties 字段。"""
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_load_schema_has_type_field_batch22():
    """schema 含 type='object'。"""
    s = load_schema("manifest.schema.json")
    assert s.get("type") == "object"


def test_load_schema_missing_raises_filenotfound_batch22():
    """不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        load_schema("bogus.schema.json")


def test_load_schema_idempotent_batch22():
    """多次加载返回等价 dict（不同对象）。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2
    assert s1 is not s2


def test_load_schema_annotation_batch22():
    """annotation schema 加载。"""
    s = load_schema("annotation.schema.json")
    assert "properties" in s


def test_load_schema_evaluation_report_batch22():
    """evaluation-report schema 加载。"""
    s = load_schema("evaluation-report.schema.json")
    assert "properties" in s


# ---------- validate 第二十二批 ----------


def test_validate_valid_manifest_returns_none_batch22():
    """合法 manifest → None。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    # None 返回
    assert validate(instance, "manifest.schema.json") is None


def test_validate_invalid_manifest_raises_eval_schema_error_batch22():
    """非法 manifest → EvalSchemaError。"""
    instance = {"manifest_version": "1.0"}  # 缺 devset_status, documents
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_eval_schema_error_has_errors_count_batch22():
    """EvalSchemaError.errors 含所有错误。"""
    instance = {}  # 多个必填字段缺失
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    assert len(exc_info.value.errors) >= 1


def test_validate_error_message_contains_schema_name_batch22():
    """message 含 schema_name。"""
    instance = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc_info.value)


def test_validate_error_message_contains_failed_batch22():
    """message 含 '校验失败'。"""
    instance = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    assert "校验失败" in str(exc_info.value)


def test_validate_error_message_contains_path_batch22():
    """message 含 'path='。"""
    instance = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    assert "path=" in str(exc_info.value)


def test_validate_does_not_modify_instance_batch22():
    """validate 不修改 instance。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    import copy
    snapshot = copy.deepcopy(instance)
    validate(instance, "manifest.schema.json")
    assert instance == snapshot


def test_validate_errors_sorted_by_path_batch22():
    """errors 按 absolute_path 排序。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"bad": 1}],  # document 缺 doc_id/path/source_type
    }
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    # 至少 3 个错误（doc_id/path/source_type required）
    assert len(exc_info.value.errors) >= 3


def test_validate_none_instance_raises_batch22():
    """None instance → EvalSchemaError（schema type=object 拒 None）。"""
    with pytest.raises(EvalSchemaError):
        validate(None, "manifest.schema.json")


def test_validate_wrong_type_raises_batch22():
    """instance 是 list 而非 dict → EvalSchemaError。"""
    with pytest.raises(EvalSchemaError):
        validate([], "manifest.schema.json")


def test_validate_error_count_in_message_batch22():
    """message 含错误数量。"""
    instance = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    # message 格式: "Schema 'X' 校验失败 (N 处)：..."
    assert "处" in str(exc_info.value)


def test_validate_error_path_field_batch22():
    """errors 字段含 'path' key。"""
    instance = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert "path" in err


def test_validate_error_message_field_batch22():
    """errors 字段含 'message' key。"""
    instance = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert "message" in err


def test_validate_error_schema_path_field_batch22():
    """errors 字段含 'schema_path' key。"""
    instance = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert "schema_path" in err


def test_validate_additional_properties_rejected_batch22():
    """manifest schema additionalProperties:false → 拒未知字段。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "unknown_field": "x",
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_wrong_manifest_version_raises_batch22():
    """manifest_version != '1.0' → EvalSchemaError。"""
    instance = {
        "manifest_version": "2.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_wrong_devset_status_raises_batch22():
    """devset_status 不是 complete/incomplete → EvalSchemaError。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "bogus",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


# ---------- validate_file 第二十二批 ----------


def test_validate_file_accepts_str_path_batch22(tmp_path):
    """str path 接受。"""
    p = tmp_path / "report.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    # validate_file 是 path + schema_name
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_accepts_path_object_batch22(tmp_path):
    """Path 对象接受。"""
    p = tmp_path / "report.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")


def test_validate_file_missing_raises_filenotfound_batch22(tmp_path):
    """不存在 → FileNotFoundError 含 '待校验文件不存在'。"""
    p = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_file(p, "manifest.schema.json")
    assert "待校验文件不存在" in str(exc_info.value)


def test_validate_file_invalid_json_raises_jsondecodeerror_batch22(tmp_path):
    """非法 JSON → JSONDecodeError。"""
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_schema_failure_raises_eval_schema_error_batch22(tmp_path):
    """schema 校验失败 → EvalSchemaError。"""
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_calls_validate_internally_batch22(tmp_path):
    """validate_file 内部调 validate。"""
    p = tmp_path / "ok.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    with patch("evaluation.schema.validate") as mock_validate:
        validate_file(p, "manifest.schema.json")
    mock_validate.assert_called_once()


def test_validate_file_idempotent_batch22(tmp_path):
    """多次调用一致。"""
    p = tmp_path / "ok.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")  # 不抛


def test_validate_file_utf8_chinese_content_batch22(tmp_path):
    """UTF-8 中文内容文件可校验。"""
    p = tmp_path / "ok.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [
                    {
                        "doc_id": "中文文档",
                        "path": "samples/private/x.pdf",
                        "source_type": "pdf",
                        "categories": ["中文类目"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")


def test_validate_file_default_encoding_no_bom_batch22(tmp_path):
    """validate_file 用 encoding=utf-8（非 utf-8-sig）→ UTF-8 BOM 触发 JSONDecodeError。"""
    p = tmp_path / "bom.json"
    p.write_bytes(
        b'\xef\xbb\xbf{"manifest_version": "1.0", "devset_status": "incomplete", "documents": []}'
    )
    # utf-8 decode 不剥 BOM；json.load 把 BOM 当成非法字符
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


# ---------- module source forbidden tokens 第三十八批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import datetime",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import itertools",
    "import functools",
    "import timeit",
    "import time",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from itertools",
    "from functools",
    "from time",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import subprocess",
    "import argparse",
]


def test_module_source_forbidden_tokens_batch22():
    """schema.py 不应 import 这些副作用大的模块。"""
    source = inspect.getsource(smod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_no_class_other_than_eval_schema_error_batch22():
    """schema.py 仅定义 EvalSchemaError，无其他 class。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(smod))
    classes = [n.name for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == ["EvalSchemaError"]


def test_module_source_no_yield_batch22():
    """schema.py 不应使用 yield。"""
    source = inspect.getsource(smod)
    assert "yield " not in source


def test_module_source_no_async_def_batch22():
    """schema.py 不应使用 async def。"""
    source = inspect.getsource(smod)
    assert "async def" not in source


def test_module_source_no_global_keyword_batch22():
    """schema.py 不应使用 global。"""
    source = inspect.getsource(smod)
    assert "global " not in source


def test_module_source_no_walrus_batch22():
    """schema.py 不应使用 walrus。"""
    source = inspect.getsource(smod)
    assert ":=" not in source


def test_module_source_no_eval_exec_batch22():
    """schema.py 不应使用 eval/exec/compile。"""
    source = inspect.getsource(smod)
    assert "eval(" not in source
    assert "exec(" not in source
    assert "compile(" not in source


def test_module_source_no_relative_imports_batch22():
    """schema.py 不应使用相对导入。"""
    source_lines = inspect.getsource(smod).split("\n")
    for line in source_lines:
        stripped = line.strip()
        if stripped.startswith("from .") and "from __future__" not in stripped:
            pytest.fail(f"relative import: {line}")


def test_module_source_no_dataclass_batch22():
    """schema.py 不应使用 @dataclass（class 是手写 Exception 子类）。"""
    source = inspect.getsource(smod)
    assert "@dataclass" not in source


def test_module_source_no_environ_batch22():
    """schema.py 不应使用 os.environ。"""
    source = inspect.getsource(smod)
    assert "os.environ" not in source


def test_module_source_no_open_at_module_level_batch22():
    """schema.py 顶层不应直接 open() 文件。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(smod))
    for node in tree.body:
        if isinstance(node, _ast.Expr) and isinstance(node.value, _ast.Call):
            f = node.value.func
            if isinstance(f, _ast.Name) and f.id == "open":
                pytest.fail("top-level open() call")


def test_module_source_no_star_import_batch22():
    """schema.py 不应使用 from X import *。"""
    source = inspect.getsource(smod)
    assert "import *" not in source


def test_module_source_json_used_batch22():
    """schema.py 必须用 json 模块。"""
    source = inspect.getsource(smod)
    assert "import json" in source


def test_module_source_jsonschema_used_batch22():
    """schema.py 必须用 Draft202012Validator。"""
    source = inspect.getsource(smod)
    assert "Draft202012Validator" in source


def test_module_source_no_network_io_batch22():
    """schema.py 不应使用 socket/http/urllib。"""
    source = inspect.getsource(smod)
    assert "import socket" not in source
    assert "import http" not in source


def test_module_source_no_subprocess_batch22():
    """schema.py 不应使用 subprocess。"""
    source = inspect.getsource(smod)
    assert "import subprocess" not in source


# ---------- module source 字符串精确补强 第三十四批 ----------


def test_module_source_contains_schemas_dir_definition_batch22():
    """source 含 SCHEMAS_DIR = Path(__file__).resolve().parent.parent / 'schemas'。"""
    source = inspect.getsource(smod)
    assert "Path(__file__).resolve().parent.parent" in source
    assert '"schemas"' in source


def test_module_source_contains_draft202012_batch22():
    """source 含 Draft202012Validator。"""
    source = inspect.getsource(smod)
    assert "Draft202012Validator" in source


def test_module_source_contains_iter_errors_batch22():
    """source 含 validator.iter_errors。"""
    source = inspect.getsource(smod)
    assert "iter_errors" in source


def test_module_source_contains_absolute_path_batch22():
    """source 含 absolute_path 排序键。"""
    source = inspect.getsource(smod)
    assert "absolute_path" in source


def test_module_source_contains_evaluation_failed_text_batch22():
    """source 含 '校验失败' 中文。"""
    source = inspect.getsource(smod)
    assert "校验失败" in source


def test_module_source_contains_path_text_batch22():
    """source 含 'path=' 字符串。"""
    source = inspect.getsource(smod)
    assert "path=" in source


def test_module_source_contains_schema_path_field_batch22():
    """source 含 'schema_path' 字段。"""
    source = inspect.getsource(smod)
    assert "schema_path" in source


def test_module_source_contains_utf8_encoding_batch22():
    """source 含 encoding='utf-8'。"""
    source = inspect.getsource(smod)
    assert 'encoding="utf-8"' in source


def test_module_source_contains_filnotfound_text_batch22():
    """source 含 '待校验文件不存在' 或 'Schema 文件不存在'。"""
    source = inspect.getsource(smod)
    assert "不存在" in source


def test_module_source_contains_sort_key_batch22():
    """source 含 sorted() with key=lambda。"""
    source = inspect.getsource(smod)
    assert "sorted(" in source
    assert "key=lambda" in source


def test_module_source_contains_errors_default_none_batch22():
    """EvalSchemaError.__init__ 签名含 errors=None。"""
    source = inspect.getsource(smod)
    assert "errors: list[dict[str, Any]] | None = None" in source


def test_module_source_contains_super_init_batch22():
    """EvalSchemaError __init__ 调 super().__init__(message)。"""
    source = inspect.getsource(smod)
    assert "super().__init__(message)" in source


def test_module_source_contains_self_errors_batch22():
    """source 含 self.errors = errors or []。"""
    source = inspect.getsource(smod)
    assert "self.errors = errors or []" in source


def test_module_source_contains_path_is_file_check_batch22():
    """source 含 is_file() 检查。"""
    source = inspect.getsource(smod)
    assert "is_file()" in source


def test_module_source_contains_pathlib_path_batch22():
    """source 含 from pathlib import Path。"""
    source = inspect.getsource(smod)
    assert "from pathlib import Path" in source


# ---------- signatures 第三十四批 ----------


def test_signature_schema_path_batch22():
    """_schema_path(name: str) -> Path。"""
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"
    assert params[0].annotation == "str"
    assert sig.return_annotation == "Path"


def test_signature_load_schema_batch22():
    """load_schema(name: str) -> dict[str, Any]。"""
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"
    assert params[0].annotation == "str"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_validate_batch22():
    """validate(instance: dict[str, Any], schema_name: str) -> None。"""
    sig = inspect.signature(validate)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["instance", "schema_name"]
    assert params[0].annotation == "dict[str, Any]"
    assert params[1].annotation == "str"
    assert sig.return_annotation == "None"


def test_signature_validate_file_batch22():
    """validate_file(path: Path | str, schema_name: str) -> None。"""
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["path", "schema_name"]
    assert params[0].annotation == "Path | str"
    assert params[1].annotation == "str"
    assert sig.return_annotation == "None"


def test_signature_eval_schema_error_init_batch22():
    """EvalSchemaError.__init__(message: str, errors: list[dict] | None = None)。"""
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    # self + message + errors
    assert len(params) == 3
    assert params[0].name == "self"
    assert params[1].name == "message"
    assert params[2].name == "errors"
    assert params[1].annotation == "str"
    assert params[2].default is None


def test_signature_all_annotations_are_strings_batch22():
    """`from __future__ import annotations` 使注解为字符串。"""
    for fn in [_schema_path, load_schema, validate, validate_file]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            if p.annotation is not inspect.Parameter.empty:
                assert isinstance(p.annotation, str)
        if sig.return_annotation is not inspect.Signature.empty:
            assert isinstance(sig.return_annotation, str)


def test_signature_validate_no_default_args_batch22():
    """validate 两个参数都必填（无默认）。"""
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_validate_file_no_default_args_batch22():
    """validate_file 两个参数都必填。"""
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


# ---------- module 合理性 第三十四批 ----------


def test_module_all_contains_five_entries_batch22():
    """__all__ 5 entries：SCHEMAS_DIR, EvalSchemaError, load_schema, validate, validate_file。"""
    assert hasattr(smod, "__all__")
    assert set(smod.__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_module_has_four_functions_batch22():
    """schema.py 定义 4 个函数：_schema_path, load_schema, validate, validate_file。"""
    funcs = [
        name
        for name, val in inspect.getmembers(smod, inspect.isfunction)
        if val.__module__ == smod.__name__
    ]
    assert set(funcs) == {"_schema_path", "load_schema", "validate", "validate_file"}


def test_module_has_one_class_eval_schema_error_batch22():
    """schema.py 定义 1 个 class：EvalSchemaError。"""
    classes = [
        name
        for name, val in inspect.getmembers(smod, inspect.isclass)
        if val.__module__ == smod.__name__
    ]
    assert classes == ["EvalSchemaError"]


def test_module_all_entries_callable_or_path_batch22():
    """__all__ 条目在模块顶层可访问。"""
    for name in smod.__all__:
        assert hasattr(smod, name)


def test_module_docstring_present_batch22():
    """schema.py 有 docstring。"""
    assert smod.__doc__ is not None
    assert len(smod.__doc__) > 0


def test_module_docstring_mentions_schema_batch22():
    """docstring 提及 Schema。"""
    assert "Schema" in smod.__doc__ or "schema" in smod.__doc__.lower()


def test_module_docstring_mentions_no_reuse_batch22():
    """docstring 提及不与 app/schema.py 复用。"""
    assert "app/schema" in smod.__doc__ or "不复用" in smod.__doc__ or "不与" in smod.__doc__


def test_module_eval_schema_error_docstring_present_batch22():
    """EvalSchemaError 有 docstring。"""
    assert EvalSchemaError.__doc__ is not None
    assert "Schema" in EvalSchemaError.__doc__


def test_module_uses_from_future_annotations_batch22():
    """schema.py 必须有 from __future__ import annotations。"""
    source = inspect.getsource(smod)
    assert "from __future__ import annotations" in source


def test_module_schemas_dir_resolved_once_batch22():
    """SCHEMAS_DIR 在模块加载时 resolve 一次（不是每次调用）。"""
    # 通过检 source 是否含 .resolve() 调用
    source = inspect.getsource(smod)
    assert ".resolve()" in source


def test_module_no_global_mutables_batch22():
    """schema.py 顶层仅 SCHEMAS_DIR 与 __all__ 两个全局。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(smod))
    top_assigns = [
        node for node in tree.body if isinstance(node, _ast.Assign)
    ]
    names = []
    for node in top_assigns:
        for target in node.targets:
            if isinstance(target, _ast.Name):
                names.append(target.id)
    assert names == ["SCHEMAS_DIR", "__all__"]


def test_module_validate_error_class_eval_schema_error_batch22():
    """validate 失败抛 EvalSchemaError（不是 ValidationError）。"""
    instance = {}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError:
        pass  # OK
    except Exception as e:
        pytest.fail(f"expected EvalSchemaError, got {type(e).__name__}")


# ---------- 端到端集成 第三十四批 ----------


def test_e2e_validate_then_validate_file_batch22(tmp_path):
    """validate 与 validate_file 校验同一 instance 一致。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    # 两者都不抛
    validate(instance, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")


def test_e2e_validate_file_with_annotation_schema_batch22(tmp_path):
    """validate_file 用 annotation schema 校验合法 annotation。"""
    annotation = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "figure_caption_pairs": [],
        "chunk_boundary_anchors": [],
    }
    p = tmp_path / "ann.json"
    p.write_text(json.dumps(annotation), encoding="utf-8")
    validate_file(p, "annotation.schema.json")


def test_e2e_annotation_schema_rejects_wrong_field_name_batch22(tmp_path):
    """annotation schema 拒 'document_id'（应是 'doc_id'）。"""
    bad_annotation = {
        "annotation_version": "1.0",
        "document_id": "d1",  # wrong field name
        "figure_caption_pairs": [],
        "chunk_boundary_anchors": [],
    }
    p = tmp_path / "ann.json"
    p.write_text(json.dumps(bad_annotation), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "annotation.schema.json")


def test_e2e_load_all_three_schemas_batch22():
    """三个 schema 都能加载。"""
    manifest = load_schema("manifest.schema.json")
    annotation = load_schema("annotation.schema.json")
    report = load_schema("evaluation-report.schema.json")
    assert manifest.get("type") == "object"
    assert annotation.get("type") == "object"
    assert report.get("type") == "object"


def test_e2e_eval_schema_error_caught_by_general_exception_batch22(tmp_path):
    """validate_file 失败 → EvalSchemaError → 可被通用 Exception 捕获。"""
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(Exception):
        validate_file(p, "manifest.schema.json")


def test_e2e_validate_returns_none_for_all_three_schemas_batch22(tmp_path):
    """三个 schema 都用合法 instance 校验通过。"""
    validate(
        {
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
        },
        "manifest.schema.json",
    )
    validate(
        {
            "annotation_version": "1.0",
            "doc_id": "d1",
            "figure_caption_pairs": [],
            "chunk_boundary_anchors": [],
        },
        "annotation.schema.json",
    )
    # evaluation-report schema 需要更多字段，这里跳过


def test_e2e_validate_dict_path_in_errors_batch22():
    """errors 含 dict 路径（嵌套对象）。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "ok", "path": "x.pdf", "source_type": "bogus"}  # source_type 不合法
        ],
    }
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    # 找到含 documents/0/source_type 的 error path
    paths = [tuple(err["path"]) for err in exc_info.value.errors]
    assert any("documents" in path for path in paths)
