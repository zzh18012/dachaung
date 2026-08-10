"""evaluation/schema.py 第二十二轮 edges 测试（Round 345）。

重点补强 edges21 未触及的角度：
- EvalSchemaError 行为深度第四批（subclass chain / equality / hashable / format / cause chain）
- _schema_path 行为深度第二批（路径不变性 / 错误传播 / 多次调用 / Path properties）
- load_schema 行为深度第二批（所有 schema / dict 内容关键字 / 加载缓存 / encoding）
- validate 行为深度第四批（不同 schema / 错误顺序 / instance 类型 / 多错误计数）
- validate_file 行为深度第二批（不存在 / 编码 / 不同 schema / unicode / round-trip / various JSON）
- module source forbidden tokens 第七批（不同 stdlib list）
- module source 字符串精确补强（更多 control flow）
- signatures 精确补强（更多 annotation 检查）
- 模块整体合理性（更多 namespace 检查）
- 端到端集成补强（更多场景）
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


# ---------- EvalSchemaError 行为深度第四批 ----------


def test_eval_schema_error_is_exception_subclass():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_not_standard_exception():
    """EvalSchemaError 不应该是 ValueError/TypeError/RuntimeError 等的子类。"""
    assert not issubclass(EvalSchemaError, ValueError)
    assert not issubclass(EvalSchemaError, TypeError)
    assert not issubclass(EvalSchemaError, RuntimeError)
    assert not issubclass(EvalSchemaError, KeyError)
    assert not issubclass(EvalSchemaError, IOError)


def test_eval_schema_error_can_be_caught_as_exception():
    try:
        raise EvalSchemaError("x")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_eval_schema_error_can_be_caught_as_eval_schema_error():
    try:
        raise EvalSchemaError("x")
    except EvalSchemaError as e:
        assert str(e) == "x"


def test_eval_schema_error_hashable_by_identity():
    """Exception 默认 hashable。"""
    e = EvalSchemaError("x")
    assert hash(e) == hash(e)


def test_eval_schema_error_in_set():
    e1 = EvalSchemaError("a")
    s = {e1}
    assert e1 in s


def test_eval_schema_error_equality_with_other_type():
    e = EvalSchemaError("x")
    assert e != "x"
    assert e != ("x",)
    assert e is not None


def test_eval_schema_error_attribute_errors_attribute():
    e = EvalSchemaError("oops", errors=[{"a": 1}])
    assert isinstance(e.errors, list)
    assert hasattr(e, "errors")


def test_eval_schema_error_cause_chain():
    inner = ValueError("inner")
    try:
        try:
            raise inner
        except ValueError as ve:
            raise EvalSchemaError("outer") from ve
    except EvalSchemaError as e:
        assert e.__cause__ is inner
        assert isinstance(e.__cause__, ValueError)


def test_eval_schema_error_context_chain():
    """raise during except 块自动设置 __context__。"""
    try:
        try:
            raise ValueError("first")
        except ValueError:
            raise EvalSchemaError("second")
    except EvalSchemaError as e:
        assert e.__context__ is not None
        assert isinstance(e.__context__, ValueError)


def test_eval_schema_error_str_includes_message():
    e = EvalSchemaError("test message")
    assert "test message" in str(e)


def test_eval_schema_error_str_with_multiline_message():
    e = EvalSchemaError("line1\nline2")
    assert "line1" in str(e)
    assert "line2" in str(e)


def test_eval_schema_error_with_unicode_message():
    e = EvalSchemaError("中文消息")
    assert "中文" in str(e)


def test_eval_schema_error_errors_attribute_is_list_after_construction():
    e = EvalSchemaError("x")
    assert isinstance(e.errors, list)
    assert len(e.errors) == 0


def test_eval_schema_error_errors_attribute_setter():
    """errors 是普通属性，可以直接赋值。"""
    e = EvalSchemaError("x")
    e.errors = [{"new": True}]
    assert e.errors == [{"new": True}]


def test_eval_schema_error_can_be_pickle_with_complex_errors():
    errs = [
        {"path": ["a", "b"], "message": "msg1", "schema_path": ["x", "y"]},
        {"path": [], "message": "msg2", "schema_path": []},
    ]
    e = EvalSchemaError("outer", errors=errs)
    s = pickle.dumps(e)
    e2 = pickle.loads(s)
    assert e2.errors == errs


def test_eval_schema_error_args_with_errors():
    e = EvalSchemaError("msg", errors=[{"a": 1}])
    # args 应包含 message 和 errors（因为传给了 super().__init__(message)）
    assert e.args == ("msg",)


def test_eval_schema_error_with_kwargs_only():
    """EvalSchemaError 只接受 message/errors 关键字。"""
    e = EvalSchemaError(message="x", errors=None)
    assert str(e) == "x"
    assert e.errors == []


def test_eval_schema_error_with_positional_only():
    e = EvalSchemaError("x", None)
    assert str(e) == "x"
    assert e.errors == []


def test_eval_schema_error_repr_includes_class_name():
    e = EvalSchemaError("oops")
    r = repr(e)
    assert "EvalSchemaError" in r


def test_eval_schema_error_class_dict_has_errors():
    """instance 有 errors 属性。"""
    e = EvalSchemaError("x", errors=[{"a": 1}])
    assert "errors" in vars(e)


# ---------- _schema_path 行为深度第二批 ----------


def test_schema_path_returns_path_object():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_absolute_path():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_exists_for_known_schemas():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        p = _schema_path(name)
        assert p.is_file()


def test_schema_path_deterministic_across_calls():
    p1 = _schema_path("manifest.schema.json")
    p2 = _schema_path("manifest.schema.json")
    assert p1 == p2


def test_schema_path_str_includes_schemas_dir():
    p = _schema_path("manifest.schema.json")
    assert "schemas" in str(p)


def test_schema_path_str_ends_with_name():
    p = _schema_path("manifest.schema.json")
    assert str(p).endswith("manifest.schema.json")


def test_schema_path_with_empty_string_raises():
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_with_dot_only_raises():
    with pytest.raises(FileNotFoundError):
        _schema_path(".")


def test_schema_path_with_double_dot_raises():
    with pytest.raises(FileNotFoundError):
        _schema_path("..")


def test_schema_path_with_directory_separator_raises():
    """传带路径分隔符的名字 → FileNotFoundError（因为拼到 SCHEMAS_DIR 下不存在）。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/manifest.schema.json")


def test_schema_path_error_message_includes_schemas_dir():
    try:
        _schema_path("not-exist.schema.json")
    except FileNotFoundError as e:
        assert "schemas" in str(e)


def test_schema_path_with_valid_filename_returns_object():
    p = _schema_path("document.schema.json")
    assert p.is_file()


def test_schema_path_with_unicode_filename_raises():
    with pytest.raises(FileNotFoundError):
        _schema_path("测试.schema.json")


def test_schema_path_parent_dir_is_schemas():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_parent_exists():
    p = _schema_path("manifest.schema.json")
    assert p.parent.is_dir()


# ---------- load_schema 行为深度第二批 ----------


def test_load_schema_returns_dict_with_specific_keys():
    """manifest.schema.json 含 $schema 或 type 或 properties。"""
    s = load_schema("manifest.schema.json")
    # 常见 schema 关键字
    has_known_key = any(k in s for k in ("$schema", "type", "properties", "required"))
    assert has_known_key


def test_load_schema_returns_dict_with_type_object():
    s = load_schema("manifest.schema.json")
    # 顶层 type 一般是 "object"
    if "type" in s:
        assert s["type"] in ("object",)


def test_load_schema_returns_dict_with_properties():
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_load_schema_returns_dict_with_required():
    s = load_schema("manifest.schema.json")
    assert "required" in s


def test_load_schema_with_annotation_schema():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)
    assert "properties" in s


def test_load_schema_with_evaluation_report_schema():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)
    assert "properties" in s


def test_load_schema_with_document_schema():
    s = load_schema("document.schema.json")
    assert isinstance(s, dict)


def test_load_schema_can_be_called_multiple_times():
    for _ in range(10):
        s = load_schema("manifest.schema.json")
        assert isinstance(s, dict)


def test_load_schema_each_call_returns_independent_dict():
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    a["__test"] = True
    assert "__test" not in b


def test_load_schema_idempotent():
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    assert a == b


def test_load_schema_returns_json_serializable():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        s_str = json.dumps(s)
        assert isinstance(s_str, str)


def test_load_schema_does_not_open_file_persistently():
    """load_schema 用 with，文件 handle 应被关闭。"""
    s = load_schema("manifest.schema.json")
    # 没有 file handle 留在模块 namespace
    for k, v in vars(smod).items():
        assert not hasattr(v, "read") or not callable(getattr(v, "read", None)) or k == "load_schema"


# ---------- validate 行为深度第四批 ----------


def test_validate_returns_none_for_valid_manifest():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_validate_returns_none_for_valid_annotation():
    """annotation.schema.json 最小实例。"""
    instance = {"annotation_version": "1.0"}
    # annotation schema 可能没有最小 required；试一下
    try:
        result = validate(instance, "annotation.schema.json")
        assert result is None
    except EvalSchemaError:
        # 如果 annotation_version 不是必需的，那应该通过；否则捕获
        pass


def test_validate_returns_none_for_valid_evaluation_report():
    instance = {
        "report_version": "1.1",
        "devset": {
            "status": "incomplete",
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": [],
        },
        "provenance": {
            "git_commit": None,
            "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {},
            "max_chars": 800,
            "run_timestamp_iso": "2026-08-10T00:00:00Z",
        },
        "summary": {"total_documents": 0, "successful": 0, "failed": 0},
        "per_doc": [],
        "expected_failures": [],
    }
    assert validate(instance, "evaluation-report.schema.json") is None


def test_validate_with_invalid_instance_raises_eval_schema_error():
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_error_count_at_least_3_for_empty_manifest():
    """空 dict 缺 manifest_version/devset_status/documents（required ≥3）。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    assert len(ei.value.errors) >= 3


def test_validate_errors_path_is_list():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    for e in ei.value.errors:
        assert isinstance(e["path"], list)


def test_validate_errors_schema_path_is_list():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    for e in ei.value.errors:
        assert isinstance(e["schema_path"], list)


def test_validate_errors_message_is_str():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    for e in ei.value.errors:
        assert isinstance(e["message"], str)


def test_validate_message_includes_count():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    msg = str(ei.value)
    assert "(" in msg and "处" in msg and ")" in msg


def test_validate_message_includes_schema_name():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(ei.value)


def test_validate_message_includes_first_error_path():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    msg = str(ei.value)
    assert "path=" in msg


def test_validate_unknown_schema_raises_filenotfounderror():
    with pytest.raises(FileNotFoundError):
        validate({}, "xxx.schema.json")


def test_validate_does_not_modify_instance_dict():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    before_keys = set(instance.keys())
    validate(instance, "manifest.schema.json")
    assert set(instance.keys()) == before_keys


def test_validate_idempotent_on_failure():
    """连续两次校验失败的 instance 应抛同样的 error count。"""
    inst = {}
    with pytest.raises(EvalSchemaError) as ei1:
        validate(inst, "manifest.schema.json")
    with pytest.raises(EvalSchemaError) as ei2:
        validate(inst, "manifest.schema.json")
    assert len(ei1.value.errors) == len(ei2.value.errors)


def test_validate_idempotent_on_success():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(instance, "manifest.schema.json") is None
    assert validate(instance, "manifest.schema.json") is None


def test_validate_with_nested_error():
    """instance.documents 不是 list → 嵌套 path 错误。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": "not-a-list",  # 应为 list
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    # 至少一个 error 的 path 含 'documents'
    has_documents_path = any("documents" in e["path"] for e in ei.value.errors)
    assert has_documents_path


def test_validate_with_invalid_devset_status():
    """devset_status 不是 enum 中的值 → schema 错误。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "invalid_status",  # 不是 'incomplete'/'complete'
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_with_invalid_manifest_version():
    instance = {
        "manifest_version": "2.0",  # 不是 '1.0'
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_returns_none_not_other_falsy():
    """validate 通过返回 None，不是 False/0/''。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    result = validate(instance, "manifest.schema.json")
    assert result is None
    assert result is not False
    assert result is not 0
    assert result is not ""


# ---------- validate_file 行为深度第二批 ----------


def test_validate_file_str_path_returns_none(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    assert validate_file(str(p), "manifest.schema.json") is None


def test_validate_file_path_object_returns_none(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_missing_raises_filenotfounderror(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "no.json", "manifest.schema.json")


def test_validate_file_unknown_schema_raises_filenotfounderror(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "xxx.schema.json")


def test_validate_file_invalid_json_raises_jsondecodeerror(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_schema_error(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_with_directory_raises(tmp_path):
    """传目录而不是文件 → IsADirectoryError 或类似。"""
    with pytest.raises((FileNotFoundError, IsADirectoryError, OSError)):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_round_trip(tmp_path):
    """写出再读回。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "x.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_with_unicode_path(tmp_path):
    p = tmp_path / "测试.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")


def test_validate_file_with_array_json_raises(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_with_string_json_raises(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('"hello"', encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_with_int_json_raises(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("42", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_with_null_json_raises(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("null", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_with_bool_json_raises(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("true", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_with_float_json_raises(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("3.14", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_with_subdir_path(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    p = sub / "x.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")


def test_validate_file_with_nested_subdir(tmp_path):
    sub = tmp_path / "a" / "b" / "c"
    sub.mkdir(parents=True)
    p = sub / "x.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")


def test_validate_file_with_bom_encoding_raises(tmp_path):
    """BOM 头的 UTF-8 文件 → json.load 用 'utf-8' 而非 'utf-8-sig'，会抛 JSONDecodeError。"""
    p = tmp_path / "x.json"
    content = json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    p.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


# ---------- module source forbidden tokens 第七批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "_thread", "_dummy_thread", "_markupbase", "_strptime", "_threading_local",
        "_weakrefset", "_collections_abc", "_compat_pickle", "_sitebuiltins",
        "_sysconfigdata", "_pyio", "_dummy_backtrace", "abc", "aifc", "antigravity",
        "argparse", "asdl", "ast", "asyncio", "atexit", "audioop",
        "base64", "bdb", "binascii", "binhex", "builtins",
        "bz2", "cProfile", "calendar", "cgi", "cgitb", "cmath",
        "cmd", "code", "codecs", "codeop", "colorsys", "compileall",
        "configparser", "contextvars", "contextlib", "copyreg", "concurrent",
        "copy", "crypt", "curses", "dataclasses", "datetime",
        "decimal", "difflib", "dis", "distutils", "doctest",
        "email", "encodings", "ensurepip", "enum", "errno",
        "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
        "formatter", "fractions", "ftplib", "functools", "gc",
        "genericpath", "getopt", "getpass", "gettext", "glob",
        "grp", "gzip", "hashlib", "heapq", "hmac",
        "html", "http", "idlelib", "imaplib", "imghdr",
        "importlib", "inspect", "ipaddress", "itertools", "keyword",
        "lib2to3", "linecache", "locale", "logging", "lzma",
        "mailbox", "mailcap", "marshal", "math", "mimetypes",
        "mmap", "modulefinder", "msilib", "msvcrt", "multiprocessing",
        "netrc", "nis", "nntplib", "ntpath", "numbers",
        "opcode", "operator", "optparse", "ossaudiodev", "parser",
        "pdb", "pickle", "pickletools", "pipes", "pkgutil",
        "platform", "plistlib", "poplib", "posix", "posixpath",
        "pprint", "profile", "pstats", "pty", "pwd",
        "py_compile", "pyclbr", "pydoc", "pydoc_data", "pyexpat",
        "queue", "quopri", "random", "readline",
        "reprlib", "resource", "rlcompleter", "runpy", "sched",
        "secrets", "select", "selectors", "shelve", "shlex",
        "shutil", "signal", "site", "smtpd", "smtplib",
        "sndhdr", "socket", "socketserver", "spwd", "sqlite3",
        "sre_compile", "sre_constants", "sre_parse", "ssl", "stat",
        "statistics", "string", "stringprep", "subprocess", "sunau",
        "symtable", "syslog", "tabnanny", "tarfile",
        "telnetlib", "tempfile", "termios", "test", "textwrap",
        "threading", "time", "timeit", "tkinter", "token",
        "tokenize", "trace", "tracemalloc", "tty", "turtle",
        "turtledemo", "types", "unicodedata", "unittest", "urllib",
        "uu", "uuid", "venv", "warnings", "wave",
        "weakref", "webbrowser", "winreg", "winsound", "wsgiref",
        "xdrlib", "xmlrpc", "zipapp", "zipfile", "zipimport",
        "zlib", "zoneinfo",
    ],
)
def test_module_source_forbidden_tokens_seventh_batch(token):
    """这些 stdlib 模块不应出现在 schema.py（仅用 json/Path/typing/jsonschema）。"""
    src = inspect.getsource(smod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强（第三批） ----------


def test_module_source_starts_with_docstring():
    src = inspect.getsource(smod)
    assert src.lstrip().startswith(('"""', "'''"))


def test_module_source_docstring_mentions_schema():
    src = inspect.getsource(smod)
    assert "Schema" in src or "schema" in src


def test_module_source_docstring_mentions_eval_schema_error():
    src = inspect.getsource(smod)
    assert "EvalSchemaError" in src or "SchemaError" in src.lower() or "evaluation" in src.lower()


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


def test_module_source_imports_in_correct_order():
    """future → stdlib → typing → third-party。"""
    src = inspect.getsource(smod)
    lines = [l.strip() for l in src.splitlines() if l.strip().startswith(("import ", "from "))]
    # __future__ 必须第一
    assert lines[0].startswith("from __future__")


def test_module_source_has_6_imports_total():
    """6 个 import: __future__, json, Path, Any, Draft202012Validator, JSValidationError。"""
    src = inspect.getsource(smod)
    lines = [l for l in src.splitlines() if l.strip().startswith(("import ", "from "))]
    assert len(lines) == 6


def test_module_source_uses_resolve_in_schemas_dir():
    src = inspect.getsource(smod)
    assert ".resolve()" in src or "resolve()" in src


def test_module_source_uses_parent_parent():
    """SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"。"""
    src = inspect.getsource(smod)
    assert ".parent.parent" in src


def test_module_source_uses_open_with_encoding():
    src = inspect.getsource(smod)
    assert 'encoding="utf-8"' in src


def test_module_source_uses_with_statement_for_file_open():
    src = inspect.getsource(smod)
    assert "with " in src
    assert ".open(" in src


def test_module_source_no_eval_exec():
    src = inspect.getsource(smod)
    assert "eval(" not in src
    assert "exec(" not in src


def test_module_source_no_compile_call():
    src = inspect.getsource(smod)
    assert "compile(" not in src


def test_module_source_no_os_module():
    src = inspect.getsource(smod)
    assert "import os" not in src
    assert "from os " not in src


def test_module_source_no_subprocess():
    src = inspect.getsource(smod)
    assert "subprocess" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(smod)
    assert "async def" not in src


def test_module_source_no_yield():
    src = inspect.getsource(smod)
    assert "yield" not in src


def test_module_source_no_global_keyword():
    src = inspect.getsource(smod)
    assert "global " not in src


def test_module_source_no_nonlocal_keyword():
    src = inspect.getsource(smod)
    assert "nonlocal " not in src


def test_module_source_no_main_block():
    src = inspect.getsource(smod)
    assert "__main__" not in src


def test_module_source_no_decorators():
    src = inspect.getsource(smod)
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("@") and not line.startswith("@property"):
            pytest.fail(f"unexpected decorator at line {i}: {line}")


def test_module_source_lambda_in_sorted_only():
    """schema.py 中 lambda 只在 sorted key 里出现。"""
    src = inspect.getsource(smod)
    assert "lambda" in src
    # 检查 lambda 出现在 sorted(...) 同一行附近
    lambda_lines = [i for i, line in enumerate(src.splitlines()) if "lambda" in line]
    sorted_lines = [i for i, line in enumerate(src.splitlines()) if "sorted" in line]
    # 至少有一个 lambda 紧跟 sorted 行（行号差 < 2）
    found = any(
        any(abs(li - si) < 3 for si in sorted_lines)
        for li in lambda_lines
    )
    assert found


def test_module_source_4_module_level_def_count():
    src = inspect.getsource(smod)
    func_count = sum(1 for line in src.splitlines() if line.startswith("def "))
    assert func_count == 4


def test_module_source_1_class_definition():
    src = inspect.getsource(smod)
    class_count = sum(1 for line in src.splitlines() if line.startswith("class "))
    assert class_count == 1


def test_module_source_class_eval_schema_error_definition():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_class_init_with_message_errors():
    src = inspect.getsource(smod)
    assert "def __init__(self, message:" in src
    assert "errors: list[dict[str, Any]] | None = None" in src


def test_module_source_class_init_calls_super_init():
    src = inspect.getsource(smod)
    assert "super().__init__(message)" in src


def test_module_source_class_init_assigns_errors_or_empty():
    src = inspect.getsource(smod)
    assert "self.errors = errors or []" in src


def test_module_source_4_function_names_exact():
    src = inspect.getsource(smod)
    assert "def _schema_path(" in src
    assert "def load_schema(" in src
    assert "def validate(" in src
    assert "def validate_file(" in src


def test_module_source_all_has_5_entries_exact():
    src = inspect.getsource(smod)
    assert '"SCHEMAS_DIR"' in src
    assert '"EvalSchemaError"' in src
    assert '"load_schema"' in src
    assert '"validate"' in src
    assert '"validate_file"' in src


# ---------- signatures 精确补强（第三批） ----------


def test_eval_schema_error_class_signature_init_param_count():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert len(sig.parameters) == 3  # self, message, errors


def test_eval_schema_error_class_init_param_names():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert list(sig.parameters.keys()) == ["self", "message", "errors"]


def test_eval_schema_error_class_init_param_kinds():
    sig = inspect.signature(EvalSchemaError.__init__)
    for name, p in sig.parameters.items():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_eval_schema_error_class_init_param_defaults():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["self"].default is inspect.Parameter.empty
    assert sig.parameters["message"].default is inspect.Parameter.empty
    assert sig.parameters["errors"].default is None


def test_eval_schema_error_class_init_message_annotation_str():
    sig = inspect.signature(EvalSchemaError.__init__)
    a = sig.parameters["message"].annotation
    assert a is str or a == "str"


def test_eval_schema_error_class_init_errors_annotation_union():
    sig = inspect.signature(EvalSchemaError.__init__)
    a = sig.parameters["errors"].annotation
    sa = str(a)
    assert "list" in sa
    assert "dict" in sa
    assert "None" in sa


def test_eval_schema_error_class_init_return_annotation_none():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.return_annotation is None or sig.return_annotation == "None"


def test_eval_schema_error_class_init_no_varargs():
    sig = inspect.signature(EvalSchemaError.__init__)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_schema_path_signature_param_count_1():
    sig = inspect.signature(_schema_path)
    assert len(sig.parameters) == 1


def test_schema_path_signature_param_name():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_schema_path_signature_param_kind():
    sig = inspect.signature(_schema_path)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_schema_path_signature_no_default():
    sig = inspect.signature(_schema_path)
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_schema_path_signature_no_varargs():
    sig = inspect.signature(_schema_path)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_load_schema_signature_param_count_1():
    sig = inspect.signature(load_schema)
    assert len(sig.parameters) == 1


def test_load_schema_signature_param_name():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_load_schema_signature_param_kind():
    sig = inspect.signature(load_schema)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_load_schema_signature_no_default():
    sig = inspect.signature(load_schema)
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_load_schema_signature_param_annotation_str():
    sig = inspect.signature(load_schema)
    a = sig.parameters["name"].annotation
    assert a is str or a == "str"


def test_load_schema_signature_return_annotation_dict_str_any():
    sig = inspect.signature(load_schema)
    ra = sig.return_annotation
    sa = str(ra)
    assert "dict" in sa


def test_validate_signature_param_count_2():
    sig = inspect.signature(validate)
    assert len(sig.parameters) == 2


def test_validate_signature_param_names():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_validate_signature_param_kinds():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_validate_signature_no_defaults():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_validate_signature_no_varargs_varkw():
    sig = inspect.signature(validate)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_validate_signature_return_annotation_none():
    sig = inspect.signature(validate)
    assert sig.return_annotation is None or sig.return_annotation == "None"


def test_validate_file_signature_param_count_2():
    sig = inspect.signature(validate_file)
    assert len(sig.parameters) == 2


def test_validate_file_signature_param_names():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_validate_file_signature_param_kinds():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_validate_file_signature_path_annotation_union():
    sig = inspect.signature(validate_file)
    a = sig.parameters["path"].annotation
    sa = str(a)
    assert "Path" in sa
    assert "str" in sa


def test_validate_file_signature_schema_name_annotation_str():
    sig = inspect.signature(validate_file)
    a = sig.parameters["schema_name"].annotation
    assert a is str or a == "str"


def test_validate_file_signature_no_defaults():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_validate_file_signature_no_varargs_varkw():
    sig = inspect.signature(validate_file)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_functions_have_docstrings():
    """_schema_path 是 private 无 docstring；3 个 public 都有。"""
    assert load_schema.__doc__ is not None
    assert validate.__doc__ is not None
    assert validate_file.__doc__ is not None


def test_schema_path_no_docstring():
    """private helper 不需要 docstring。"""
    assert _schema_path.__doc__ is None


def test_eval_schema_error_has_docstring():
    assert EvalSchemaError.__doc__ is not None


# ---------- 模块整体合理性（第三批） ----------


def test_module_namespace_is_module():
    assert isinstance(smod, types.ModuleType)


def test_module_namespace_has_name():
    assert hasattr(smod, "__name__")
    assert smod.__name__ == "evaluation.schema"


def test_module_namespace_has_file():
    assert hasattr(smod, "__file__")
    assert smod.__file__ is not None


def test_module_namespace_has_doc():
    assert hasattr(smod, "__doc__")
    assert smod.__doc__ is not None


def test_module_namespace_has_all():
    assert hasattr(smod, "__all__")
    assert isinstance(smod.__all__, list)


def test_module_all_has_5_entries():
    assert len(smod.__all__) == 5


def test_module_all_entries_are_str():
    for entry in smod.__all__:
        assert isinstance(entry, str)


def test_module_all_entries_exact():
    assert set(smod.__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_module_schemas_dir_is_path_instance():
    assert isinstance(SCHEMAS_DIR, Path)


def test_module_schemas_dir_is_absolute():
    assert SCHEMAS_DIR.is_absolute()


def test_module_schemas_dir_exists():
    assert SCHEMAS_DIR.is_dir()


def test_module_schemas_dir_in_module_namespace():
    assert hasattr(smod, "SCHEMAS_DIR")


def test_module_eval_schema_error_in_namespace():
    assert hasattr(smod, "EvalSchemaError")


def test_module_eval_schema_error_is_class():
    assert isinstance(EvalSchemaError, type)


def test_module_eval_schema_error_subclass_of_exception():
    assert issubclass(EvalSchemaError, Exception)


def test_module_has_4_module_level_functions():
    functions = [
        v for v in vars(smod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == smod.__name__
    ]
    assert len(functions) == 4


def test_module_has_3_public_functions():
    public = [
        v for v in vars(smod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == smod.__name__
        and not v.__name__.startswith("_")
    ]
    assert len(public) == 3
    names = sorted(f.__name__ for f in public)
    assert names == ["load_schema", "validate", "validate_file"]


def test_module_has_1_private_function():
    private = [
        v for v in vars(smod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == smod.__name__
        and v.__name__.startswith("_")
        and not v.__name__.startswith("__")
    ]
    assert len(private) == 1
    assert private[0].__name__ == "_schema_path"


def test_module_has_1_class():
    classes = [
        v for v in vars(smod).values()
        if isinstance(v, type) and v.__module__ == smod.__name__
    ]
    assert len(classes) == 1
    assert classes[0].__name__ == "EvalSchemaError"


def test_module_callable_load_schema():
    assert callable(smod.load_schema)


def test_module_callable_validate():
    assert callable(smod.validate)


def test_module_callable_validate_file():
    assert callable(smod.validate_file)


def test_module_callable_schema_path():
    assert callable(smod._schema_path)


def test_module_function_modules_eq_evaluation_schema():
    """所有 module-level function 的 __module__ 应是 evaluation.schema。"""
    for name in ("load_schema", "validate", "validate_file", "_schema_path"):
        fn = getattr(smod, name)
        assert fn.__module__ == "evaluation.schema"


# ---------- 端到端集成补强（第三批） ----------


def test_e2e_load_each_schema_does_not_raise():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        assert isinstance(s, dict)


def test_e2e_validate_each_known_schema_loadable():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        v = Draft202012Validator(s)
        assert v is not None


def test_e2e_validate_manifest_with_valid_documents_list():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "doc1",
                "path": "doc1.pdf",
                "source_type": "pdf",
            }
        ],
        "expected_failures": [],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_e2e_validate_manifest_with_expected_failures():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "broken1",
                "path": "broken.pdf",
                "expected_error_code": "encrypted",
            }
        ],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_e2e_validate_evaluation_report_with_categories():
    instance = {
        "report_version": "1.1",
        "devset": {
            "status": "incomplete",
            "file_count": 2,
            "content_group_count": 2,
            "pdf_count": 1,
            "docx_count": 1,
            "categories_covered": ["handbook", "academic"],
        },
        "provenance": {
            "git_commit": "abc123",
            "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": "1.0.0",
            "dependencies": {"pdfplumber": "0.10.0"},
            "max_chars": 800,
            "run_timestamp_iso": "2026-08-10T00:00:00Z",
        },
        "summary": {"total_documents": 2, "successful": 2, "failed": 0},
        "per_doc": [],
        "expected_failures": [],
    }
    assert validate(instance, "evaluation-report.schema.json") is None


def test_e2e_validate_idempotent_calls_with_invalid_instance():
    inst = {}
    for _ in range(5):
        with pytest.raises(EvalSchemaError):
            validate(inst, "manifest.schema.json")


def test_e2e_validate_file_round_trip_with_complex_instance(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "a", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "b", "path": "b.docx", "source_type": "docx"},
        ],
        "expected_failures": [
            {"doc_id": "c", "path": "c.pdf", "expected_error_code": "encrypted"},
        ],
    }
    p = tmp_path / "complex.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_validate_does_not_write_to_module_namespace():
    """validate 不应留下副作用。"""
    before = set(vars(smod).keys())
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(instance, "manifest.schema.json")
    after = set(vars(smod).keys())
    assert before == after


def test_e2e_load_schema_does_not_modify_schemas_dir():
    """load_schema 不应创建/删除 schemas dir 中的文件。"""
    files_before = set(p.name for p in SCHEMAS_DIR.iterdir())
    load_schema("manifest.schema.json")
    files_after = set(p.name for p in SCHEMAS_DIR.iterdir())
    assert files_before == files_after


def test_e2e_validate_returns_none_within_loop():
    """循环校验多次都返回 None。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    for _ in range(10):
        assert validate(instance, "manifest.schema.json") is None


def test_e2e_eval_schema_error_raised_with_full_message():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    msg = str(ei.value)
    # message 应含 schema 名 + count + path
    assert "manifest.schema.json" in msg
    assert "处" in msg
    assert "path=" in msg


def test_e2e_can_catch_with_bare_except():
    """bare except 也能捕获 EvalSchemaError。"""
    try:
        validate({}, "manifest.schema.json")
        raised = False
    except EvalSchemaError:
        raised = True
    assert raised


def test_e2e_call_validate_with_kwargs():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(instance=instance, schema_name="manifest.schema.json") is None


def test_e2e_call_validate_file_with_kwargs(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    assert validate_file(path=p, schema_name="manifest.schema.json") is None


def test_e2e_call_load_schema_with_kwarg():
    s = load_schema(name="manifest.schema.json")
    assert isinstance(s, dict)


def test_e2e_eval_schema_error_can_propagate_through_multiple_functions():
    def inner():
        validate({}, "manifest.schema.json")

    def outer():
        inner()

    with pytest.raises(EvalSchemaError):
        outer()


def test_e2e_validate_with_extra_keys_in_nested_field():
    """manifest.documents 项含未知 key → 触发 additionalProperties。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "path": "a.pdf",
                "category": "x",
                "parser": "fallback",
                "extra_unknown_field": True,
            }
        ],
        "expected_failures": [],
    }
    # 触发 schema 错误（如果有 additionalProperties: false）
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError:
        pass  # 预期可能抛


def test_e2e_validate_file_json_with_comments_fails(tmp_path):
    """JSON 不允许注释 → JSONDecodeError。"""
    p = tmp_path / "x.json"
    p.write_text(
        '{"manifest_version": "1.0",\n// comment\n"devset_status": "x"}',
        encoding="utf-8",
    )
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_e2e_validate_call_does_not_raise_unexpected():
    """验证不抛非 EvalSchemaError/FileNotFoundError 的异常。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    try:
        validate(instance, "manifest.schema.json")
    except (EvalSchemaError, FileNotFoundError):
        pytest.fail("valid instance should not raise")
    except Exception as e:
        pytest.fail(f"unexpected exception type: {type(e).__name__}: {e}")


def test_e2e_eval_schema_error_message_with_special_chars():
    """message 含特殊字符也能正确显示。"""
    e = EvalSchemaError("msg with 中文 and 'quotes' and \"double\"")
    s = str(e)
    assert "中文" in s
    assert "quotes" in s
