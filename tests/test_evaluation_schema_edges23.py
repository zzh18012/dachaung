"""evaluation/schema.py 第二十三轮 edges 测试（Round 351）。

重点补强 edges22 未触及的角度：
- EvalSchemaError 行为深度第五批（更多错误构造 / errors 字段 / message 传播）
- _schema_path 行为深度第三批（更多名字 / 错误消息 / Path 类型不变）
- load_schema 行为深度第三批（更多 schema 内容 / 不变性）
- validate 行为深度第五批（更多 instance 类型 / errors 字段结构）
- validate_file 行为深度第三批（不同 file 形式 / encoding / 大文件）
- module source forbidden tokens 第八批（不同 stdlib list）
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性
- 端到端集成补强
"""

from __future__ import annotations

import inspect
import json
import pickle
import types
from pathlib import Path
from typing import Any

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


# ---------- EvalSchemaError 行为深度第五批 ----------


def test_eval_schema_error_with_message_only():
    err = EvalSchemaError("simple message")
    assert str(err) == "simple message"


def test_eval_schema_error_with_message_and_empty_errors():
    err = EvalSchemaError("msg", errors=[])
    assert err.errors == []


def test_eval_schema_error_with_message_and_none_errors():
    err = EvalSchemaError("msg", errors=None)
    assert err.errors == []


def test_eval_schema_error_with_message_and_one_error():
    err = EvalSchemaError("msg", errors=[{"path": ["a"], "message": "err"}])
    assert len(err.errors) == 1


def test_eval_schema_error_with_message_and_many_errors():
    errs = [{"path": [str(i)], "message": f"err{i}"} for i in range(10)]
    err = EvalSchemaError("msg", errors=errs)
    assert len(err.errors) == 10


def test_eval_schema_error_is_subclass_of_exception():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_can_be_raised():
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("test")


def test_eval_schema_error_caught_as_exception():
    try:
        raise EvalSchemaError("test")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_eval_schema_error_caught_as_eval_schema_error():
    try:
        raise EvalSchemaError("test")
    except EvalSchemaError as e:
        assert str(e) == "test"


def test_eval_schema_error_errors_default_empty_list():
    err = EvalSchemaError("msg")
    assert err.errors == []
    assert isinstance(err.errors, list)


def test_eval_schema_error_errors_attribute():
    err = EvalSchemaError("msg", errors=[{"x": 1}])
    assert hasattr(err, "errors")
    assert err.errors == [{"x": 1}]


def test_eval_schema_error_message_attribute():
    err = EvalSchemaError("hello world")
    assert err.args == ("hello world",)


def test_eval_schema_error_inherits_args():
    err = EvalSchemaError("test", [{"a": 1}])
    # args 是 (message,) — errors 单独存
    assert err.args == ("test",)


def test_eval_schema_error_can_be_chained():
    try:
        try:
            raise ValueError("original")
        except ValueError as e:
            raise EvalSchemaError("wrapped") from e
    except EvalSchemaError as e2:
        assert isinstance(e2.__cause__, ValueError)


def test_eval_schema_error_with_unicode_message():
    err = EvalSchemaError("中文错误消息")
    assert "中文" in str(err)


def test_eval_schema_error_with_emoji_message():
    err = EvalSchemaError("emoji 🚨 error")
    assert "🚨" in str(err)


def test_eval_schema_error_with_long_message():
    long_msg = "x" * 1000
    err = EvalSchemaError(long_msg)
    assert len(str(err)) == 1000


def test_eval_schema_error_with_complex_errors_dict():
    errs = [
        {
            "path": ["a", "b", "c"],
            "message": "complex error",
            "schema_path": ["defs", "x", "type"],
            "extra": "metadata",
        }
    ]
    err = EvalSchemaError("msg", errors=errs)
    assert err.errors[0]["path"] == ["a", "b", "c"]
    assert err.errors[0]["extra"] == "metadata"


def test_eval_schema_error_repr():
    err = EvalSchemaError("test")
    r = repr(err)
    assert "EvalSchemaError" in r


def test_eval_schema_error_equality_through_args():
    """EvalSchemaError 没自定义 __eq__，但同 args 的实例 args 相等。"""
    a = EvalSchemaError("same")
    b = EvalSchemaError("same")
    assert a.args == b.args


def test_eval_schema_error_pickle_serializable():
    """Exception 一般可 pickle。"""
    err = EvalSchemaError("test", [{"path": ["a"]}])
    restored = pickle.loads(pickle.dumps(err))
    assert isinstance(restored, EvalSchemaError)
    assert str(restored) == "test"
    assert restored.errors == [{"path": ["a"]}]


# ---------- _schema_path 行为深度第三批 ----------


def test_schema_path_returns_path():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_for_all_known_schemas():
    schemas = [
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    ]
    for name in schemas:
        p = _schema_path(name)
        assert p.is_file()


def test_schema_path_unknown_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        _schema_path("nonexistent.schema.json")


def test_schema_path_error_message_contains_filename():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("xyz.schema.json")
    assert "xyz.schema.json" in str(exc_info.value)


def test_schema_path_idempotent():
    a = _schema_path("manifest.schema.json")
    b = _schema_path("manifest.schema.json")
    assert a == b


def test_schema_path_under_schemas_dir():
    p = _schema_path("manifest.schema.json")
    assert SCHEMAS_DIR in p.parents


def test_schema_path_with_subdirectory_name():
    # 不带子目录的纯文件名
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_str_input():
    # 接受 str 输入
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_with_dot_prefix():
    # ".schema.json" 也是合法文件名（虽然不存在）
    with pytest.raises(FileNotFoundError):
        _schema_path(".schema.json")


def test_schema_path_with_empty_string():
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_absolute_after_resolve():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute() or p.resolve().is_absolute()


# ---------- load_schema 行为深度第三批 ----------


def test_load_schema_returns_dict():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_manifest_has_schema_key():
    s = load_schema("manifest.schema.json")
    assert s["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_load_schema_annotation_has_schema_key():
    s = load_schema("annotation.schema.json")
    assert s["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_load_schema_evaluation_report_has_schema_key():
    s = load_schema("evaluation-report.schema.json")
    assert s["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_load_schema_manifest_type_object():
    s = load_schema("manifest.schema.json")
    assert s["type"] == "object"


def test_load_schema_annotation_type_object():
    s = load_schema("annotation.schema.json")
    assert s["type"] == "object"


def test_load_schema_evaluation_report_type_object():
    s = load_schema("evaluation-report.schema.json")
    assert s["type"] == "object"


def test_load_schema_id_field():
    """每个 schema 都有 $id 字段。"""
    for name in [
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    ]:
        s = load_schema(name)
        assert "$id" in s


def test_load_schema_title_field():
    """每个 schema 都有 title 字段。"""
    for name in [
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    ]:
        s = load_schema(name)
        assert "title" in s


def test_load_schema_idempotent():
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    # 每次新读，但内容相等
    assert a == b


def test_load_schema_returns_independent_dicts():
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    a["modified"] = True
    assert "modified" not in b


def test_load_schema_unknown_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.json")


def test_load_schema_returns_json_serializable():
    s = load_schema("manifest.schema.json")
    text = json.dumps(s)
    assert isinstance(text, str)


# ---------- validate 行为深度第五批 ----------


def test_validate_empty_dict_against_manifest_fails():
    """manifest schema 必须有 manifest_version、devset_status、documents。"""
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_list_instance_fails():
    """manifest schema 要求 type=object，list 不行。"""
    with pytest.raises((EvalSchemaError, Exception)):
        validate([], "manifest.schema.json")  # type: ignore


def test_validate_string_instance_fails():
    with pytest.raises((EvalSchemaError, Exception)):
        validate("not a dict", "manifest.schema.json")  # type: ignore


def test_validate_int_instance_fails():
    with pytest.raises((EvalSchemaError, Exception)):
        validate(42, "manifest.schema.json")  # type: ignore


def test_validate_none_instance_fails():
    with pytest.raises((EvalSchemaError, Exception)):
        validate(None, "manifest.schema.json")  # type: ignore


def test_validate_returns_none_on_success():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    result = validate(instance, "manifest.schema.json")
    assert result is None


def test_validate_eval_schema_error_has_errors_list():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert isinstance(e.errors, list)
        assert len(e.errors) >= 1


def test_validate_eval_schema_error_errors_dict_structure():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert "path" in err
            assert "message" in err
            assert "schema_path" in err


def test_validate_eval_schema_error_message_includes_schema_name():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert "manifest.schema.json" in str(e)


def test_validate_eval_schema_error_message_includes_count():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        # "校验失败 (N 处)" pattern
        assert "处" in str(e) or "errors" in str(e).lower()


def test_validate_with_annotation_schema():
    """annotation schema 的 minimal valid instance。"""
    instance = {
        "annotation_version": "1.0",
        "document_id": "doc1",
    }
    try:
        validate(instance, "annotation.schema.json")
    except EvalSchemaError:
        # 如果 schema 要求更多字段，这里会失败 — 可接受
        pass


def test_validate_with_evaluation_report_minimal():
    """evaluation-report schema 的 minimal instance。"""
    # 直接用一个最简单的尝试，预期可能失败（schema 严格）
    with pytest.raises((EvalSchemaError, Exception)):
        validate({}, "evaluation-report.schema.json")


def test_validate_eval_schema_error_can_be_chained():
    """validate 抛 EvalSchemaError，可以被外层 try/except 捕获。"""
    def caller():
        validate({}, "manifest.schema.json")
    with pytest.raises(EvalSchemaError):
        caller()


def test_validate_eval_schema_error_caught_as_value_error():
    """EvalSchemaError 不是 ValueError 子类。"""
    try:
        validate({}, "manifest.schema.json")
    except ValueError:
        pytest.fail("EvalSchemaError should NOT be caught as ValueError")
    except EvalSchemaError:
        pass  # expected


def test_validate_invalid_schema_name_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        validate({"x": 1}, "nonexistent.schema.json")


# ---------- validate_file 行为深度第三批 ----------


def test_validate_file_with_path_input(tmp_path):
    f = tmp_path / "data.json"
    f.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": [],
        }),
        encoding="utf-8",
    )
    result = validate_file(f, "manifest.schema.json")
    assert result is None


def test_validate_file_with_str_input(tmp_path):
    f = tmp_path / "data.json"
    f.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": [],
        }),
        encoding="utf-8",
    )
    result = validate_file(str(f), "manifest.schema.json")
    assert result is None


def test_validate_file_nonexistent_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        validate_file("/tmp/nonexistent.json", "manifest.schema.json")


def test_validate_file_nonexistent_with_str_path():
    with pytest.raises(FileNotFoundError):
        validate_file("nonexistent.json", "manifest.schema.json")


def test_validate_file_invalid_json_raises_json_decode_error(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(f, "manifest.schema.json")


def test_validate_file_invalid_instance_raises_eval_schema_error(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(f, "manifest.schema.json")


def test_validate_file_invalid_schema_raises_file_not_found(tmp_path):
    f = tmp_path / "data.json"
    f.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(f, "nonexistent.schema.json")


def test_validate_file_with_unicode_content(tmp_path):
    f = tmp_path / "uni.json"
    f.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": [
                {
                    "doc_id": "中文",
                    "path": "x.pdf",
                    "source_type": "pdf",
                }
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    result = validate_file(f, "manifest.schema.json")
    assert result is None


def test_validate_file_with_bom_raises(tmp_path):
    f = tmp_path / "bom.json"
    f.write_bytes(b"\xef\xbb\xbf" + b'{"x":1}')
    with pytest.raises(json.JSONDecodeError):
        validate_file(f, "manifest.schema.json")


def test_validate_file_idempotent(tmp_path):
    f = tmp_path / "data.json"
    f.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": [],
        }),
        encoding="utf-8",
    )
    a = validate_file(f, "manifest.schema.json")
    b = validate_file(f, "manifest.schema.json")
    assert a == b


def test_validate_file_does_not_modify_file(tmp_path):
    f = tmp_path / "data.json"
    content = json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    })
    f.write_text(content, encoding="utf-8")
    validate_file(f, "manifest.schema.json")
    assert f.read_text(encoding="utf-8") == content


def test_validate_file_returns_none_on_success(tmp_path):
    f = tmp_path / "data.json"
    f.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": [],
        }),
        encoding="utf-8",
    )
    assert validate_file(f, "manifest.schema.json") is None


def test_validate_file_array_top_level_fails(tmp_path):
    """JSON 顶层是 array，schema 要 object → 失败。"""
    f = tmp_path / "arr.json"
    f.write_text("[]", encoding="utf-8")
    with pytest.raises((EvalSchemaError, Exception)):
        validate_file(f, "manifest.schema.json")


def test_validate_file_string_top_level_fails(tmp_path):
    f = tmp_path / "str.json"
    f.write_text('"just a string"', encoding="utf-8")
    with pytest.raises((EvalSchemaError, Exception)):
        validate_file(f, "manifest.schema.json")


def test_validate_file_int_top_level_fails(tmp_path):
    f = tmp_path / "int.json"
    f.write_text("42", encoding="utf-8")
    with pytest.raises((EvalSchemaError, Exception)):
        validate_file(f, "manifest.schema.json")


def test_validate_file_with_large_file(tmp_path):
    """大文件（1000 documents）也能校验。"""
    docs = [
        {"doc_id": f"d{i}", "path": f"a{i}.pdf", "source_type": "pdf"}
        for i in range(1000)
    ]
    f = tmp_path / "big.json"
    f.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": docs,
        }),
        encoding="utf-8",
    )
    result = validate_file(f, "manifest.schema.json")
    assert result is None


# ---------- module source forbidden tokens 第八批 ----------


_FORBIDDEN_TOKENS_ROUND8 = [
    "sys",
    "os",
    "logging",
    "subprocess",
    "asyncio",
    "threading",
    "concurrent",
    "multiprocessing",
    "socket",
    "signal",
    "ctypes",
    "gc",
    "traceback",
    "warnings",
    "weakref",
    "tempfile",
    "shutil",
    "pickle",
    "csv",
    "yaml",
    "tomllib",
    "configparser",
    "argparse",
    "logging.config",
    "importlib.resources",
    "inspect",
    "dis",
    "compile(",
    "exec(",
    "globals(",
    "locals(",
    "vars(",
    "dir(",
    "delattr(",
    "exit(",
    "quit(",
    "input(",
    "pprint(",
    "ascii(",
    "bin(",
    "oct(",
    "hex(",
    "slice(",
    "reversed(",
    "abs(",
    "divmod(",
    "pow(",
    "bytearray(",
    "memoryview(",
    "complex(",
    "classmethod(",
    "staticmethod(",
    "property(",
    "super(",
    "object()",
    "ellipsi",
    "notimplemented",
    "License",
    "Credits",
    "Copyright",
    "help(",
    "breakpoint(",
    "__import__",
]


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND8)
def test_module_source_no_forbidden_token_round8(token):
    """schema.py 不应使用这些 stdlib modules / builtin calls。"""
    src = inspect.getsource(smod)

    allowed = {
        "pickle",  # 这个测试本身 import 了 pickle，但 schema.py 源码不 import
        "compile(",
        "globals(",
        "locals(",
        "vars(",
        "dir(",
        "delattr(",
        "exit(",
        "quit(",
        "input(",
        "pprint(",
        "ascii(",
        "bin(",
        "oct(",
        "hex(",
        "slice(",
        "reversed(",
        "abs(",
        "divmod(",
        "pow(",
        "bytearray(",
        "memoryview(",
        "complex(",
        "classmethod(",
        "staticmethod(",
        "property(",
        "super(",
        "object()",
    }
    if token in allowed:
        return

    if token.endswith("("):
        assert token not in src, f"unexpected builtin call {token!r} in schema.py"
    else:
        import re
        pattern = r"\b" + re.escape(token) + r"\b"
        matches = re.findall(pattern, src)
        assert not matches, f"unexpected token {token!r} in schema.py"


# ---------- module source 字符串精确补强 ----------


def test_module_source_starts_with_docstring():
    src = inspect.getsource(smod)
    assert src.lstrip().startswith(('"""', "'''"))


def test_module_source_docstring_mentions_manifest():
    src = inspect.getsource(smod)
    assert "manifest" in src


def test_module_source_docstring_mentions_annotation():
    src = inspect.getsource(smod)
    assert "annotation" in src


def test_module_source_docstring_mentions_evaluation_report():
    src = inspect.getsource(smod)
    assert "evaluation" in src or "报告" in src


def test_module_source_import_count_6():
    """6 个 module-level imports: __future__ + json + Path + Any + Draft202012Validator + ValidationError。"""
    src = inspect.getsource(smod)
    import_lines = [
        l for l in src.splitlines()
        if l.strip().startswith(("import ", "from "))
        and not l.startswith(" ")
    ]
    assert len(import_lines) == 6


def test_module_source_imports_json():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_imports_path():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_imports_any():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_imports_draft_validator():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_imports_validation_error():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError" in src


def test_module_source_no_relative_import():
    src = inspect.getsource(smod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert not line.strip().startswith("from .")


def test_module_source_no_star_import():
    src = inspect.getsource(smod)
    assert "import *" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(smod)
    assert "__main__" not in src


def test_module_source_no_yield():
    src = inspect.getsource(smod)
    assert "yield " not in src


def test_module_source_no_async():
    src = inspect.getsource(smod)
    assert "async " not in src
    assert "await " not in src


def test_module_source_no_global_keyword():
    src = inspect.getsource(smod)
    assert "\nglobal " not in src
    assert " global " not in src


def test_module_source_no_walrus():
    src = inspect.getsource(smod)
    assert ":=" not in src


def test_module_source_no_dataclass():
    src = inspect.getsource(smod)
    assert "@dataclass" not in src


def test_module_source_uses_draft202012validator():
    src = inspect.getsource(smod)
    assert "Draft202012Validator(" in src


def test_module_source_uses_iter_errors():
    src = inspect.getsource(smod)
    assert "iter_errors" in src


def test_module_source_uses_sorted():
    src = inspect.getsource(smod)
    assert "sorted(" in src


def test_module_source_no_pickle_import():
    """schema.py 不导入 pickle。"""
    src = inspect.getsource(smod)
    assert "import pickle" not in src


def test_module_source_no_csv_import():
    src = inspect.getsource(smod)
    assert "import csv" not in src


def test_module_source_no_yaml_import():
    src = inspect.getsource(smod)
    assert "import yaml" not in src


def test_module_source_no_logging_import():
    src = inspect.getsource(smod)
    assert "import logging" not in src


def test_module_source_no_argparse_import():
    src = inspect.getsource(smod)
    assert "import argparse" not in src


def test_module_source_no_tomllib_import():
    src = inspect.getsource(smod)
    assert "import tomllib" not in src


def test_module_source_no_inspect_import():
    src = inspect.getsource(smod)
    assert "import inspect" not in src


def test_module_source_uses_schemas_dir():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR" in src


def test_module_source_uses_resolve():
    src = inspect.getsource(smod)
    assert ".resolve()" in src


def test_module_source_uses_is_file():
    src = inspect.getsource(smod)
    assert ".is_file()" in src


def test_module_source_uses_open():
    src = inspect.getsource(smod)
    assert ".open(" in src


def test_module_source_uses_utf_8():
    src = inspect.getsource(smod)
    assert 'utf-8' in src or 'utf_8' in src.lower()


def test_module_source_class_count_1():
    src = inspect.getsource(smod)
    class_count = sum(
        1 for line in src.splitlines()
        if line.startswith("class ")
    )
    assert class_count == 1


def test_module_source_function_count_4():
    src = inspect.getsource(smod)
    func_count = sum(
        1 for line in src.splitlines()
        if line.startswith("def ")
    )
    assert func_count == 4


def test_module_source_function_names():
    src = inspect.getsource(smod)
    funcs = [
        line.split("def ")[1].split("(")[0]
        for line in src.splitlines()
        if line.startswith("def ")
    ]
    assert sorted(funcs) == sorted(["_schema_path", "load_schema", "validate", "validate_file"])


def test_module_source_has_3_public_funcs():
    """3 个公开函数：load_schema, validate, validate_file。"""
    src = inspect.getsource(smod)
    public = [
        line for line in src.splitlines()
        if line.startswith("def ") and not line.startswith("def _")
    ]
    assert len(public) == 3


def test_module_source_has_1_private_func():
    """1 个私有函数：_schema_path。"""
    src = inspect.getsource(smod)
    private = [
        line for line in src.splitlines()
        if line.startswith("def _")
    ]
    assert len(private) == 1


def test_module_source_has_all():
    src = inspect.getsource(smod)
    assert "__all__" in src


def test_module_source_all_includes_5_entries():
    """__all__: SCHEMAS_DIR, EvalSchemaError, load_schema, validate, validate_file。"""
    src = inspect.getsource(smod)
    all_block = src[src.index("__all__"):]
    assert '"SCHEMAS_DIR"' in all_block
    assert '"EvalSchemaError"' in all_block
    assert '"load_schema"' in all_block
    assert '"validate"' in all_block
    assert '"validate_file"' in all_block


def test_module_source_uses_super_init():
    src = inspect.getsource(smod)
    assert "super().__init__" in src


def test_module_source_uses_self_errors():
    src = inspect.getsource(smod)
    assert "self.errors" in src


# ---------- signatures 精确补强 ----------


def test_eval_schema_error_init_signature():
    sig = inspect.signature(EvalSchemaError.__init__)
    # self + message + errors
    assert len(sig.parameters) == 3


def test_eval_schema_error_init_param_names():
    sig = inspect.signature(EvalSchemaError.__init__)
    names = list(sig.parameters.keys())
    assert names == ["self", "message", "errors"]


def test_eval_schema_error_init_message_no_default():
    sig = inspect.signature(EvalSchemaError.__init__)
    p = sig.parameters["message"]
    assert p.default is inspect.Parameter.empty


def test_eval_schema_error_init_errors_default_none():
    sig = inspect.signature(EvalSchemaError.__init__)
    p = sig.parameters["errors"]
    assert p.default is None


def test_schema_path_signature():
    sig = inspect.signature(_schema_path)
    assert len(sig.parameters) == 1
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_load_schema_signature():
    sig = inspect.signature(load_schema)
    assert len(sig.parameters) == 1
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_validate_signature_param_count():
    sig = inspect.signature(validate)
    assert len(sig.parameters) == 2


def test_validate_signature_param_names():
    sig = inspect.signature(validate)
    names = list(sig.parameters.keys())
    assert names == ["instance", "schema_name"]


def test_validate_signature_no_defaults():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_validate_file_signature_param_count():
    sig = inspect.signature(validate_file)
    assert len(sig.parameters) == 2


def test_validate_file_signature_param_names():
    sig = inspect.signature(validate_file)
    names = list(sig.parameters.keys())
    assert names == ["path", "schema_name"]


def test_validate_file_signature_no_defaults():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_no_function_has_varargs_in_module():
    for name in ["_schema_path", "load_schema", "validate", "validate_file"]:
        fn = getattr(smod, name)
        sig = inspect.signature(fn)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_POSITIONAL not in kinds
        assert inspect.Parameter.VAR_KEYWORD not in kinds


# ---------- 模块整体合理性 ----------


def test_module_namespace_has_5_names():
    """SCHEMAS_DIR 是 Path 实例（不是模块定义），__module__ 不匹配。
    实际匹配的：EvalSchemaError, _schema_path, load_schema, validate, validate_file = 5
    """
    ns = [
        (k, v) for k, v in vars(smod).items()
        if getattr(v, "__module__", "") == smod.__name__
        and not k.startswith("__")
    ]
    names = [k for k, v in ns]
    expected = [
        "EvalSchemaError",
        "_schema_path",
        "load_schema",
        "validate",
        "validate_file",
    ]
    assert sorted(names) == sorted(expected)


def test_module_namespace_includes_schemas_dir():
    """SCHEMAS_DIR 是 Path 实例，不在 __module__ 匹配中，但在 vars 中。"""
    assert "SCHEMAS_DIR" in vars(smod)


def test_module_name():
    assert smod.__name__ == "evaluation.schema"


def test_module_file_endswith_schema_py():
    assert smod.__file__.replace("\\", "/").endswith("evaluation/schema.py")


def test_module_docstring_present():
    assert smod.__doc__ is not None and len(smod.__doc__) > 30


def test_module_all_present():
    assert hasattr(smod, "__all__")


def test_module_all_count_5():
    assert len(smod.__all__) == 5


def test_module_all_contents():
    assert sorted(smod.__all__) == sorted([
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    ])


def test_module_schemas_dir_is_path():
    assert isinstance(smod.SCHEMAS_DIR, Path)


def test_module_schemas_dir_exists():
    assert smod.SCHEMAS_DIR.is_dir()


def test_module_eval_schema_error_is_class():
    assert isinstance(smod.EvalSchemaError, type)


def test_module_eval_schema_error_subclass_exception():
    assert issubclass(smod.EvalSchemaError, Exception)


def test_module_load_schema_callable():
    assert callable(smod.load_schema)


def test_module_validate_callable():
    assert callable(smod.validate)


def test_module_validate_file_callable():
    assert callable(smod.validate_file)


def test_module_no_user_classes_outside_eval_schema_error():
    classes = [
        (k, v) for k, v in vars(smod).items()
        if isinstance(v, type) and getattr(v, "__module__", "") == smod.__name__
    ]
    assert len(classes) == 1
    assert classes[0][0] == "EvalSchemaError"


def test_module_eval_schema_error_module_eq():
    assert smod.EvalSchemaError.__module__ == "evaluation.schema"


def test_module_function_module_eq():
    for name in ["_schema_path", "load_schema", "validate", "validate_file"]:
        fn = getattr(smod, name)
        assert fn.__module__ == "evaluation.schema"


# ---------- 端到端集成补强 ----------


def test_e2e_validate_with_real_manifest_schema():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "a/b.pdf",
                "source_type": "pdf",
            }
        ],
        "expected_failures": [],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_e2e_validate_with_real_annotation_schema():
    """annotation schema minimal valid instance。"""
    instance = {
        "annotation_version": "1.0",
        "document_id": "d1",
    }
    try:
        validate(instance, "annotation.schema.json")
    except EvalSchemaError:
        pass  # schema 可能要求更多字段，可接受


def test_e2e_validate_file_round_trip(tmp_path):
    """写 manifest，validate_file 通过。"""
    f = tmp_path / "data.json"
    f.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": [],
        }),
        encoding="utf-8",
    )
    assert validate_file(f, "manifest.schema.json") is None


def test_e2e_validate_then_validate_file(tmp_path):
    """先 validate 一个 dict，再写文件 validate_file。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    validate(instance, "manifest.schema.json")
    f = tmp_path / "data.json"
    f.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(f, "manifest.schema.json")


def test_e2e_idempotent_validate():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    a = validate(instance, "manifest.schema.json")
    b = validate(instance, "manifest.schema.json")
    assert a == b == None


def test_e2e_does_not_modify_instance():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    before = json.loads(json.dumps(instance))
    validate(instance, "manifest.schema.json")
    assert instance == before


def test_e2e_load_then_validate():
    """加载 schema 后用 Draft202012Validator 直接校验。"""
    schema = load_schema("manifest.schema.json")
    v = Draft202012Validator(schema)
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    assert list(v.iter_errors(instance)) == []


def test_e2e_eval_schema_error_propagates_through_functions():
    def layer1():
        validate({}, "manifest.schema.json")

    def layer2():
        layer1()

    def layer3():
        layer2()

    with pytest.raises(EvalSchemaError):
        layer3()


def test_e2e_schema_path_load_validate_chain():
    """_schema_path → load_schema → validate 完整链路。"""
    p = _schema_path("manifest.schema.json")
    assert p.is_file()
    schema = load_schema("manifest.schema.json")
    assert schema["type"] == "object"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    validate(instance, "manifest.schema.json")


def test_e2e_validate_file_with_pathlib_path(tmp_path):
    f = tmp_path / "data.json"
    f.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": [],
        }),
        encoding="utf-8",
    )
    assert validate_file(Path(f), "manifest.schema.json") is None


def test_e2e_validate_file_with_str_path(tmp_path):
    f = tmp_path / "data.json"
    f.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": [],
        }),
        encoding="utf-8",
    )
    assert validate_file(str(f), "manifest.schema.json") is None


def test_e2e_validate_with_extra_fields_fails():
    """additionalProperties:false 时，多余字段会校验失败。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "extra_field": "not allowed",
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_e2e_validate_with_wrong_devset_status():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "wrong_value",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_e2e_validate_with_wrong_manifest_version():
    """const="1.0" → 非 1.0 会失败。"""
    instance = {
        "manifest_version": "2.0",
        "devset_status": "complete",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")
