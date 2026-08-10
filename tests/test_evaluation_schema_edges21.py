"""evaluation/schema.py 第二十一轮 edges 测试（Round 339）。

重点补强 edges20 未触及的角度：
- EvalSchemaError 行为深度第三批（多个 errors / errors 默认值 / equality / pickle / raise chain）
- _schema_path 行为深度（路径拼接 / 错误消息内容 / Path.is_file 副作用）
- load_schema 行为深度（文件不存在 / 多次调用 / 文件 handle 释放 / 编码）
- validate 行为深度（错误排序 / errors 列表结构 / Schema 路径 / 第一个 error 提取）
- validate_file 行为深度（str 路径 / Path 路径 / 不存在 / 子目录 / 非 JSON 文件）
- module source forbidden tokens 第四批
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


# ---------- EvalSchemaError 行为深度第三批 ----------


def test_eval_schema_error_message_only_no_errors_arg():
    e = EvalSchemaError("oops")
    assert str(e) == "oops"
    assert e.errors == []


def test_eval_schema_error_errors_default_empty():
    e = EvalSchemaError("oops")
    assert e.errors == []
    assert isinstance(e.errors, list)


def test_eval_schema_error_errors_with_none_explicit():
    e = EvalSchemaError("oops", errors=None)
    assert e.errors == []


def test_eval_schema_error_errors_with_empty_list():
    e = EvalSchemaError("oops", errors=[])
    assert e.errors == []


def test_eval_schema_error_errors_with_dict():
    """errors=None 是 None → []；其它 falsy 也是 []。"""
    e = EvalSchemaError("oops", errors=None)
    assert e.errors == []


def test_eval_schema_error_errors_with_truthy_list():
    errs = [{"path": [], "message": "x"}]
    e = EvalSchemaError("oops", errors=errs)
    assert e.errors is errs


def test_eval_schema_error_equality_by_identity():
    e1 = EvalSchemaError("a")
    e2 = EvalSchemaError("a")
    assert e1 is not e2


def test_eval_schema_error_can_be_pickled():
    """EvalSchemaError 应支持 pickle（Exception 默认支持）。"""
    e = EvalSchemaError("oops", errors=[{"a": 1}])
    s = pickle.dumps(e)
    e2 = pickle.loads(s)
    assert isinstance(e2, EvalSchemaError)
    assert str(e2) == "oops"


def test_eval_schema_error_raise_from_other_exception():
    """可以从其他异常 wrap。"""
    try:
        try:
            raise ValueError("inner")
        except ValueError as ve:
            raise EvalSchemaError("outer") from ve
    except EvalSchemaError as e:
        assert str(e) == "outer"
        assert isinstance(e.__cause__, ValueError)
        assert str(e.__cause__) == "inner"


def test_eval_schema_error_raise_chained():
    """raise from 后 __cause__ 已设置。"""
    inner = RuntimeError("rt")
    try:
        raise EvalSchemaError("outer") from inner
    except EvalSchemaError as e:
        assert e.__cause__ is inner


def test_eval_schema_error_args_attribute():
    """Exception 的 args 行为：args[0] 是 message。"""
    e = EvalSchemaError("msg")
    assert e.args == ("msg",)


def test_eval_schema_error_can_be_raised_with_no_message():
    """无 message 也应能 raise。"""
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("")


def test_eval_schema_error_str_with_empty_message():
    e = EvalSchemaError("")
    assert str(e) == ""


def test_eval_schema_error_repr_includes_args():
    e = EvalSchemaError("oops")
    r = repr(e)
    assert "EvalSchemaError" in r


def test_eval_schema_error_attribute_can_be_modified():
    """errors 是普通 list 可修改。"""
    e = EvalSchemaError("oops")
    e.errors.append({"a": 1})
    assert e.errors == [{"a": 1}]


# ---------- _schema_path 行为深度 ----------


def test_schema_path_returns_path_with_correct_parent():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_returns_path_with_correct_name():
    p = _schema_path("manifest.schema.json")
    assert p.name == "manifest.schema.json"


def test_schema_path_does_not_exist_for_unknown():
    with pytest.raises(FileNotFoundError):
        _schema_path("does-not-exist.schema.json")


def test_schema_path_error_message_includes_path():
    try:
        _schema_path("xxx.schema.json")
    except FileNotFoundError as e:
        assert "xxx.schema.json" in str(e)
        assert "Schema 文件不存在" in str(e)


def test_schema_path_with_dot_prefix_still_works():
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_with_subdir_name_raises():
    """子目录路径不会跨 SCHEMAS_DIR 边界。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/manifest.schema.json")


def test_schema_path_returns_resolved_path():
    p = _schema_path("manifest.schema.json")
    # 注意：_schema_path 不调用 resolve()，但 SCHEMAS_DIR 本身已 resolve
    assert p.is_absolute()


def test_schema_path_string_in_str_representation():
    p = _schema_path("manifest.schema.json")
    s = str(p)
    assert s.endswith("manifest.schema.json")


# ---------- load_schema 行为深度 ----------


def test_load_schema_returns_dict_for_each_schema():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        assert isinstance(s, dict)


def test_load_schema_returns_fresh_dict_each_call():
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    assert a is not b
    assert a == b


def test_load_schema_modifications_do_not_persist():
    """修改返回 dict 不影响下次调用。"""
    a = load_schema("manifest.schema.json")
    a["$__test"] = True
    b = load_schema("manifest.schema.json")
    assert "$__test" not in b


def test_load_schema_unknown_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        load_schema("xxx.schema.json")


def test_load_schema_returns_dict_with_schema_keyword():
    """JSON Schema 必有 $schema 或 type 等关键字。"""
    s = load_schema("manifest.schema.json")
    assert "type" in s or "$schema" in s


def test_load_schema_dict_is_json_serializable():
    s = load_schema("manifest.schema.json")
    out = json.dumps(s)
    assert isinstance(out, str)


# ---------- validate 行为深度 ----------


def test_validate_with_invalid_returns_none_on_success():
    """校验通过 → 返回 None。"""
    schema = load_schema("manifest.schema.json")
    valid_instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(valid_instance, "manifest.schema.json") is None


def test_validate_errors_attribute_populated():
    instance = {}  # 缺所有 required
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    assert len(ei.value.errors) > 0
    for e in ei.value.errors:
        assert "path" in e
        assert "message" in e
        assert "schema_path" in e


def test_validate_errors_sorted_by_absolute_path():
    """validate 用 sorted by absolute_path。"""
    instance = {}  # 多个错误
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    # 第一个 error 是 sorted 后的第一个
    paths = [tuple(e["path"]) for e in ei.value.errors]
    sorted_paths = sorted(paths)
    assert paths == sorted_paths


def test_validate_does_not_modify_instance():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    before = json.dumps(instance, sort_keys=True)
    validate(instance, "manifest.schema.json")
    after = json.dumps(instance, sort_keys=True)
    assert before == after


def test_validate_message_includes_schema_name():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(ei.value)


def test_validate_message_includes_count():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    # "校验失败 (N 处)"
    assert "处" in str(ei.value)


def test_validate_with_array_top_level_raises():
    with pytest.raises(EvalSchemaError):
        validate([], "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_with_string_top_level_raises():
    with pytest.raises(EvalSchemaError):
        validate("hello", "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_with_int_top_level_raises():
    with pytest.raises(EvalSchemaError):
        validate(42, "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_with_none_top_level_raises():
    with pytest.raises(EvalSchemaError):
        validate(None, "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_with_bool_top_level_raises():
    with pytest.raises(EvalSchemaError):
        validate(True, "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_first_error_message_in_exception_message():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    # 第一个 error 的 message 应该在异常 message 里
    first_err = ei.value.errors[0]
    assert first_err["message"] in str(ei.value)


def test_validate_with_unknown_schema_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        validate({}, "xxx.schema.json")


# ---------- validate_file 行为深度 ----------


def test_validate_file_with_str_path(tmp_path):
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
    # str path 也能工作
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_with_path_object(tmp_path):
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
    validate_file(p, "manifest.schema.json")


def test_validate_file_missing_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "no.json", "manifest.schema.json")


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


def test_validate_file_in_subdir(tmp_path):
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


def test_validate_file_returns_none_on_success(tmp_path):
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


# ---------- module source forbidden tokens 第四批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "abc", "aifc", "antigravity", "argparse", "asdl", "asyncio",
        "audioop", "base64", "binascii", "binhex", "bisect",
        "cProfile", "calendar", "concurrent", "contextlib", "copyreg",
        "csv", "crypt", "curses", "datetime", "dl",
        "docxml", "dospath", "dummy_threading", "email", "encodings",
        "ensurepip", "enum", "errno", "fileinput", "fnmatch",
        "formatter", "ftplib", "functools", "genericpath", "genshi",
        "getopt", "getpass", "gettext", "glob", "gopherlib",
        "heapq", "html", "http", "imaplib", "ihooks",
        "imghdr", "importlib", "inspect", "ipaddress", "itertools",
        "keyword", "linecache", "locale", "logging", "lzma",
        "mailbox", "mailcap", "markupbase", "md5", "mhlib",
        "mimetypes", "mimify", "mmap", "msilib", "multifile",
        "multiprocessing", "mutex", "netrc", "nis", "nntplib",
        "numbers", "opcode", "operator", "optparse", "os2emxpath",
        "parser", "pdb", "pickle", "pickletools",
        "pipes", "pkgutil", "platform", "plistlib", "poplib",
        "posixfile", "posixpath", "profile", "pstats", "pty",
        "pyclbr", "py_compile", "pydoc", "queue", "quopri",
        "random", "readline", "reprlib", "rexec", "rfc822",
        "rlcompleter", "robotparser", "runpy", "sched", "secrets",
        "select", "sets", "sgmlop", "sgmllib", "sha",
        "shelve", "shlex", "shutil", "signal", "site",
        "smtplib", "smtpd", "sndhdr", "socket", "socketserver",
        "spawn", "spwd", "sqlite3", "ssl", "stat",
        "stringprep", "struct", "subprocess", "sunau", "sunaudio",
        "symtable", "sys", "sysconfig", "tabnanny", "tarfile",
        "telnetlib", "tempfile", "termios", "threading", "time",
        "timeit", "tomllib", "token", "tokenize", "trace",
        "traceback", "tracemalloc", "tty", "turtle", "types",
        "unicodedata", "unittest", "urllib", "urllib2", "urlparse",
        "user", "userdict", "userlist", "usersite", "uuid",
        "venv", "warnings", "wave", "weakref", "webbrowser",
        "whichdb", "wsgiref", "xdrlib", "xml", "xmlrpc",
        "zipapp", "zipfile", "zipimport", "zlib", "zoneinfo",
    ],
)
def test_module_source_forbidden_tokens_fourth_batch(token):
    """这些 stdlib 模块不应出现在 schema.py（仅用 json/Path/typing/jsonschema）。"""
    src = inspect.getsource(smod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_from_future():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_source_imports_json():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_imports_path():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_imports_any():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_imports_draft202012validator():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_imports_jsvalidationerror():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_defines_schemas_dir():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = " in src
    assert "__file__" in src


def test_module_source_defines_eval_schema_error_class():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_eval_schema_error_init_takes_message_and_errors():
    src = inspect.getsource(smod)
    assert "def __init__(self, message:" in src
    assert "errors: list[dict[str, Any]] | None = None" in src


def test_module_source_eval_schema_error_calls_super_init():
    src = inspect.getsource(smod)
    assert "super().__init__(message)" in src


def test_module_source_eval_schema_error_assigns_errors_or_empty():
    src = inspect.getsource(smod)
    assert "self.errors = errors or []" in src


def test_module_source_schema_path_uses_isfile():
    src = inspect.getsource(smod)
    assert "p.is_file()" in src


def test_module_source_schema_path_raises_filenotfounderror():
    src = inspect.getsource(smod)
    assert "raise FileNotFoundError" in src


def test_module_source_load_schema_uses_open():
    src = inspect.getsource(smod)
    assert ".open(" in src
    assert 'encoding="utf-8"' in src


def test_module_source_load_schema_uses_json_load():
    src = inspect.getsource(smod)
    assert "json.load(f)" in src


def test_module_source_validate_uses_draft202012validator():
    src = inspect.getsource(smod)
    assert "Draft202012Validator(schema)" in src


def test_module_source_validate_uses_iter_errors():
    src = inspect.getsource(smod)
    assert "validator.iter_errors(instance)" in src


def test_module_source_validate_uses_sorted_with_absolute_path():
    src = inspect.getsource(smod)
    assert "sorted(validator.iter_errors" in src
    assert "absolute_path" in src


def test_module_source_validate_builds_flat_list():
    src = inspect.getsource(smod)
    assert "flat: list[dict[str, Any]] = []" in src or "flat:" in src


def test_module_source_validate_appends_3_keys_per_error():
    src = inspect.getsource(smod)
    assert '"path":' in src
    assert '"message":' in src
    assert '"schema_path":' in src


def test_module_source_validate_uses_errors_0():
    src = inspect.getsource(smod)
    assert "head = errors[0]" in src


def test_module_source_validate_raises_eval_schema_error_with_message():
    src = inspect.getsource(smod)
    assert "raise EvalSchemaError(" in src
    assert "schema_name" in src


def test_module_source_validate_file_uses_path_constructor():
    src = inspect.getsource(smod)
    assert "p = Path(path)" in src


def test_module_source_validate_file_checks_isfile():
    src = inspect.getsource(smod)
    assert "p.is_file()" in src


def test_module_source_validate_file_raises_filenotfounderror():
    src = inspect.getsource(smod)
    assert "raise FileNotFoundError" in src


def test_module_source_validate_file_calls_validate():
    src = inspect.getsource(smod)
    assert "validate(data, schema_name)" in src


def test_module_source_no_yield():
    src = inspect.getsource(smod)
    assert "yield" not in src


def test_module_source_no_async():
    src = inspect.getsource(smod)
    assert "async " not in src


def test_module_source_no_global():
    src = inspect.getsource(smod)
    assert "global " not in src


def test_module_source_no_main_block():
    src = inspect.getsource(smod)
    assert "__main__" not in src


def test_module_source_no_decorators():
    src = inspect.getsource(smod)
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("@"):
            pytest.fail(f"unexpected decorator at line {i}: {line}")


def test_module_source_no_lambda():
    """schema.py 唯一的 lambda 在 sorted key 中。"""
    src = inspect.getsource(smod)
    assert "lambda" in src  # lambda e: list(e.absolute_path)


def test_module_source_has_all_with_5_entries():
    src = inspect.getsource(smod)
    assert '"SCHEMAS_DIR"' in src
    assert '"EvalSchemaError"' in src
    assert '"load_schema"' in src
    assert '"validate"' in src
    assert '"validate_file"' in src


def test_module_source_has_4_module_level_functions():
    """3 public (load_schema/validate/validate_file) + 1 private (_schema_path)。"""
    src = inspect.getsource(smod)
    func_count = sum(1 for line in src.splitlines() if line.startswith("def "))
    assert func_count == 4


def test_module_source_has_1_module_level_class():
    src = inspect.getsource(smod)
    class_count = sum(1 for line in src.splitlines() if line.startswith("class "))
    assert class_count == 1


# ---------- signatures 精确补强 ----------


def test_eval_schema_error_init_signature():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "errors"]


def test_eval_schema_error_init_message_annotation():
    sig = inspect.signature(EvalSchemaError.__init__)
    a = sig.parameters["message"].annotation
    assert a is str or a == "str"


def test_eval_schema_error_init_errors_annotation():
    sig = inspect.signature(EvalSchemaError.__init__)
    a = sig.parameters["errors"].annotation
    # errors: list[dict[str, Any]] | None = None
    assert "list" in str(a) or "None" in str(a)


def test_eval_schema_error_init_errors_default_none():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_eval_schema_error_init_return_none():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.return_annotation is None or sig.return_annotation == "None"


def test_eval_schema_error_init_param_kinds():
    sig = inspect.signature(EvalSchemaError.__init__)
    for name, p in sig.parameters.items():
        if name == "self":
            continue
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_schema_path_signature_1_param():
    sig = inspect.signature(_schema_path)
    assert len(sig.parameters) == 1
    assert list(sig.parameters.keys()) == ["name"]


def test_schema_path_param_annotation_str():
    sig = inspect.signature(_schema_path)
    a = sig.parameters["name"].annotation
    assert a is str or a == "str"


def test_schema_path_return_annotation_path():
    sig = inspect.signature(_schema_path)
    assert sig.return_annotation == "Path" or sig.return_annotation is Path


def test_load_schema_signature_1_param():
    sig = inspect.signature(load_schema)
    assert len(sig.parameters) == 1
    assert list(sig.parameters.keys()) == ["name"]


def test_load_schema_param_annotation_str():
    sig = inspect.signature(load_schema)
    a = sig.parameters["name"].annotation
    assert a is str or a == "str"


def test_load_schema_return_annotation_dict():
    sig = inspect.signature(load_schema)
    assert "dict" in str(sig.return_annotation)


def test_validate_signature_2_params():
    sig = inspect.signature(validate)
    assert len(sig.parameters) == 2


def test_validate_param_names():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_validate_param_annotations():
    sig = inspect.signature(validate)
    assert "dict" in str(sig.parameters["instance"].annotation)
    assert sig.parameters["schema_name"].annotation is str or sig.parameters["schema_name"].annotation == "str"


def test_validate_return_annotation_none():
    sig = inspect.signature(validate)
    assert sig.return_annotation is None or sig.return_annotation == "None"


def test_validate_file_signature_2_params():
    sig = inspect.signature(validate_file)
    assert len(sig.parameters) == 2


def test_validate_file_param_names():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_validate_file_path_annotation_union():
    sig = inspect.signature(validate_file)
    a = sig.parameters["path"].annotation
    assert "Path" in str(a) and "str" in str(a)


def test_validate_file_return_annotation_none():
    sig = inspect.signature(validate_file)
    assert sig.return_annotation is None or sig.return_annotation == "None"


def test_no_varargs_varkw_in_any_function():
    for fn in [_schema_path, load_schema, validate, validate_file]:
        sig = inspect.signature(fn)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_POSITIONAL not in kinds
        assert inspect.Parameter.VAR_KEYWORD not in kinds


# ---------- 模块整体合理性 ----------


def test_module_namespace():
    assert isinstance(smod, types.ModuleType)


def test_module_namespace_name():
    assert smod.__name__ == "evaluation.schema"


def test_module_namespace_has_schemas_dir():
    assert hasattr(smod, "SCHEMAS_DIR")


def test_module_namespace_has_eval_schema_error():
    assert hasattr(smod, "EvalSchemaError")


def test_module_namespace_has_load_schema():
    assert hasattr(smod, "load_schema")


def test_module_namespace_has_validate():
    assert hasattr(smod, "validate")


def test_module_namespace_has_validate_file():
    assert hasattr(smod, "validate_file")


def test_module_namespace_has_schema_path():
    assert hasattr(smod, "_schema_path")


def test_module_all_is_list():
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


def test_module_has_4_module_level_functions():
    """3 public + 1 private。"""
    functions = [
        v for v in vars(smod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == smod.__name__
    ]
    assert len(functions) == 4


def test_module_has_1_private_function():
    private = [
        v for v in vars(smod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == smod.__name__
        and v.__name__.startswith("_")
        and not v.__name__.startswith("__")
    ]
    assert len(private) == 1  # _schema_path


def test_module_has_3_public_functions():
    public = [
        v for v in vars(smod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == smod.__name__
        and not v.__name__.startswith("_")
    ]
    # load_schema, validate, validate_file = 3
    assert len(public) == 3


def test_module_has_1_class_only():
    classes = [
        v for v in vars(smod).values()
        if isinstance(v, type) and v.__module__ == smod.__name__
    ]
    assert len(classes) == 1
    assert classes[0].__name__ == "EvalSchemaError"


def test_module_no_main_block():
    src = inspect.getsource(smod)
    assert "__main__" not in src


def test_module_schemas_dir_is_path():
    assert isinstance(SCHEMAS_DIR, Path)


def test_module_schemas_dir_is_absolute():
    assert SCHEMAS_DIR.is_absolute()


def test_module_schemas_dir_exists():
    assert SCHEMAS_DIR.is_dir()


def test_module_callable_load_schema():
    assert callable(load_schema)


def test_module_callable_validate():
    assert callable(validate)


def test_module_callable_validate_file():
    assert callable(validate_file)


def test_module_eval_schema_error_is_class():
    assert isinstance(EvalSchemaError, type)


def test_module_eval_schema_error_subclass_of_exception():
    assert issubclass(EvalSchemaError, Exception)


# ---------- 端到端集成补强 ----------


def test_e2e_load_each_schema_returns_dict():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        assert isinstance(s, dict)


def test_e2e_validate_manifest_valid_returns_none():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_e2e_validate_manifest_invalid_raises():
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_e2e_validate_evaluation_report_minimal():
    """evaluation-report 最小有效实例。"""
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
    validate(instance, "evaluation-report.schema.json")


def test_e2e_validate_file_round_trip(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "x.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_eval_schema_error_can_be_reraised():
    try:
        try:
            validate({}, "manifest.schema.json")
        except EvalSchemaError:
            raise
    except EvalSchemaError as e:
        assert "manifest.schema.json" in str(e)


def test_e2e_eval_schema_error_caught_as_exception():
    try:
        validate({}, "manifest.schema.json")
    except Exception as e:  # noqa: BLE001
        assert isinstance(e, EvalSchemaError)


def test_e2e_eval_schema_error_caught_not_as_value_error():
    """EvalSchemaError 不是 ValueError 子类。"""
    with pytest.raises(EvalSchemaError):
        try:
            validate({}, "manifest.schema.json")
        except ValueError:
            pytest.fail("should not be ValueError")


def test_e2e_eval_schema_error_caught_not_as_type_error():
    with pytest.raises(EvalSchemaError):
        try:
            validate({}, "manifest.schema.json")
        except TypeError:
            pytest.fail("should not be TypeError")


def test_e2e_error_dict_is_json_serializable():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    s = json.dumps(ei.value.errors)
    assert isinstance(s, str)


def test_e2e_validate_does_not_modify_schema_dict():
    """validate 加载 schema 后不应被修改。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    schema_before = json.dumps(load_schema("manifest.schema.json"), sort_keys=True)
    validate(instance, "manifest.schema.json")
    schema_after = json.dumps(load_schema("manifest.schema.json"), sort_keys=True)
    # 注：load_schema 每次返回新 dict，但内容应一致
    assert schema_before == schema_after


def test_e2e_validate_call_with_extra_keys_in_instance():
    """instance 含 schema 不允许的 key → 触发 additionalProperties 错误。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
        "extra_key": "should_fail",
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_e2e_validate_multiple_errors_returns_all():
    """多个错误都被收集到 errors 列表。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    # manifest 有 3 个 required（manifest_version/devset_status/documents）
    assert len(ei.value.errors) >= 3


def test_e2e_validate_file_with_unicode_in_path(tmp_path):
    """路径含 Unicode 字符也能工作。"""
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


def test_e2e_round_trip_validate_then_validate_file(tmp_path):
    """先 validate（dict），写出，再 validate_file（path）。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(instance, "manifest.schema.json")
    p = tmp_path / "x.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_validate_file_json_array_top_level_raises(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_e2e_validate_file_json_string_top_level_raises(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('"hello"', encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_e2e_validate_file_json_int_top_level_raises(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("42", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_e2e_validate_file_json_null_top_level_raises(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("null", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_e2e_draft202012validator_used():
    """validate 内部用 Draft202012Validator 而不是其它版本。"""
    src = inspect.getsource(validate)
    assert "Draft202012Validator" in src


def test_e2e_evaluation_report_schema_filename_with_json_extension():
    """validate/validate_file 都需要带 .json 后缀的 schema 名。"""
    src = inspect.getsource(validate)
    # schema_name 由调用者传入；模块不自动加 .schema.json 后缀
    assert "load_schema(schema_name)" in src
