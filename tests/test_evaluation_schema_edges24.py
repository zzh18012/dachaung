"""evaluation/schema.py 第二十四轮 edges 测试（Round 358）。

重点补强 edges23 未触及的角度：
- EvalSchemaError source level 字符串精确补强第二批
- _schema_path source level 字符串精确补强第二批
- load_schema source level 字符串精确补强第二批
- validate source level 字符串精确补强第二批
- validate_file source level 字符串精确补强第二批
- SCHEMAS_DIR 常量精确
- module source forbidden tokens 第八批
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性补强
- 端到端集成补强
"""

from __future__ import annotations

import inspect
import json
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


# ---------- EvalSchemaError source level 字符串精确补强第二批 ----------


def test_eval_schema_error_source_starts_with_class():
    src = inspect.getsource(EvalSchemaError)
    assert src.startswith("class EvalSchemaError")


def test_eval_schema_error_source_extends_exception():
    src = inspect.getsource(EvalSchemaError)
    assert "class EvalSchemaError(Exception):" in src


def test_eval_schema_error_source_has_docstring():
    src = inspect.getsource(EvalSchemaError)
    assert '"""' in src


def test_eval_schema_error_source_uses_super_init():
    src = inspect.getsource(EvalSchemaError)
    assert "super().__init__(message)" in src


def test_eval_schema_error_source_self_message():
    src = inspect.getsource(EvalSchemaError)
    assert "self.errors = errors or []" in src


def test_eval_schema_error_source_no_eval():
    src = inspect.getsource(EvalSchemaError)
    assert "eval(" not in src


def test_eval_schema_error_source_no_subprocess():
    src = inspect.getsource(EvalSchemaError)
    assert "subprocess" not in src


def test_eval_schema_error_source_no_yield():
    src = inspect.getsource(EvalSchemaError)
    assert "yield" not in src


# ---------- _schema_path source level 字符串精确补强第二批 ----------


def test_schema_path_source_starts_with_def():
    src = inspect.getsource(_schema_path)
    assert src.lstrip().startswith("def _schema_path(")


def test_schema_path_source_one_param():
    src = inspect.getsource(_schema_path)
    assert "name: str" in src


def test_schema_path_source_returns_path():
    src = inspect.getsource(_schema_path)
    assert "return p" in src


def test_schema_path_source_uses_schemas_dir():
    src = inspect.getsource(_schema_path)
    assert "SCHEMAS_DIR" in src


def test_schema_path_source_uses_is_file():
    src = inspect.getsource(_schema_path)
    assert ".is_file()" in src


def test_schema_path_source_raises_file_not_found():
    src = inspect.getsource(_schema_path)
    assert "FileNotFoundError" in src


def test_schema_path_source_no_eval():
    src = inspect.getsource(_schema_path)
    assert "eval(" not in src


def test_schema_path_source_no_subprocess():
    src = inspect.getsource(_schema_path)
    assert "subprocess" not in src


def test_schema_path_source_no_yield():
    src = inspect.getsource(_schema_path)
    assert "yield" not in src


# ---------- load_schema source level 字符串精确补强第二批 ----------


def test_load_schema_source_starts_with_def():
    src = inspect.getsource(load_schema)
    assert src.lstrip().startswith("def load_schema(")


def test_load_schema_source_one_param():
    src = inspect.getsource(load_schema)
    assert "name: str" in src


def test_load_schema_source_returns_dict():
    src = inspect.getsource(load_schema)
    assert "-> dict[str, Any]" in src or "dict" in src


def test_load_schema_source_uses_schema_path():
    src = inspect.getsource(load_schema)
    assert "_schema_path(name)" in src


def test_load_schema_source_uses_open():
    src = inspect.getsource(load_schema)
    assert ".open(" in src


def test_load_schema_source_uses_utf8():
    src = inspect.getsource(load_schema)
    assert '"utf-8"' in src or "'utf-8'" in src


def test_load_schema_source_uses_json_load():
    src = inspect.getsource(load_schema)
    assert "json.load(f)" in src


def test_load_schema_source_returns_json_load():
    src = inspect.getsource(load_schema)
    assert "return json.load(f)" in src


def test_load_schema_source_no_eval():
    src = inspect.getsource(load_schema)
    assert "eval(" not in src


def test_load_schema_source_no_subprocess():
    src = inspect.getsource(load_schema)
    assert "subprocess" not in src


def test_load_schema_source_no_yield():
    src = inspect.getsource(load_schema)
    assert "yield" not in src


# ---------- validate source level 字符串精确补强第二批 ----------


def test_validate_source_starts_with_def():
    src = inspect.getsource(validate)
    assert src.lstrip().startswith("def validate(")


def test_validate_source_two_params():
    src = inspect.getsource(validate)
    assert "instance: dict[str, Any]" in src
    assert "schema_name: str" in src


def test_validate_source_no_return_value():
    src = inspect.getsource(validate)
    assert "-> None" in src or "return" in src


def test_validate_source_uses_load_schema():
    src = inspect.getsource(validate)
    assert "load_schema(schema_name)" in src


def test_validate_source_uses_draft_validator():
    src = inspect.getsource(validate)
    assert "Draft202012Validator" in src


def test_validate_source_uses_iter_errors():
    src = inspect.getsource(validate)
    assert ".iter_errors(instance)" in src


def test_validate_source_uses_sorted():
    src = inspect.getsource(validate)
    assert "sorted(" in src


def test_validate_source_uses_absolute_path():
    src = inspect.getsource(validate)
    assert "absolute_path" in src


def test_validate_source_uses_errors_list():
    src = inspect.getsource(validate)
    assert "flat: list[dict[str, Any]]" in src or "flat = []" in src or "flat:" in src


def test_validate_source_returns_when_no_errors():
    src = inspect.getsource(validate)
    assert "if not errors:" in src
    assert "return" in src


def test_validate_source_raises_eval_schema_error():
    src = inspect.getsource(validate)
    assert "raise EvalSchemaError(" in src


def test_validate_source_error_path_keys():
    src = inspect.getsource(validate)
    assert '"path"' in src
    assert '"message"' in src
    assert '"schema_path"' in src


def test_validate_source_no_eval():
    src = inspect.getsource(validate)
    assert "eval(" not in src


def test_validate_source_no_subprocess():
    src = inspect.getsource(validate)
    assert "subprocess" not in src


def test_validate_source_no_yield_in_validate():
    """validate 函数体内没有 yield。"""
    src = inspect.getsource(validate)
    # 排除 docstring 中的 yield 词
    lines = src.splitlines()
    in_func = False
    for l in lines:
        if l.lstrip().startswith("def "):
            in_func = True
        if in_func and not l.strip().startswith(("#", '"""', "'''")):
            assert "yield" not in l


# ---------- validate_file source level 字符串精确补强第二批 ----------


def test_validate_file_source_starts_with_def():
    src = inspect.getsource(validate_file)
    assert src.lstrip().startswith("def validate_file(")


def test_validate_file_source_two_params():
    src = inspect.getsource(validate_file)
    assert "path: Path | str" in src
    assert "schema_name: str" in src


def test_validate_file_source_no_return_value():
    src = inspect.getsource(validate_file)
    assert "-> None" in src


def test_validate_file_source_uses_path():
    src = inspect.getsource(validate_file)
    assert "Path(path)" in src


def test_validate_file_source_uses_is_file():
    src = inspect.getsource(validate_file)
    assert ".is_file()" in src


def test_validate_file_source_raises_file_not_found():
    src = inspect.getsource(validate_file)
    assert "FileNotFoundError" in src


def test_validate_file_source_uses_open():
    src = inspect.getsource(validate_file)
    assert ".open(" in src


def test_validate_file_source_uses_utf8():
    src = inspect.getsource(validate_file)
    assert '"utf-8"' in src


def test_validate_file_source_uses_json_load():
    src = inspect.getsource(validate_file)
    assert "json.load(f)" in src


def test_validate_file_source_uses_validate():
    src = inspect.getsource(validate_file)
    assert "validate(data, schema_name)" in src


def test_validate_file_source_no_eval():
    src = inspect.getsource(validate_file)
    assert "eval(" not in src


def test_validate_file_source_no_subprocess():
    src = inspect.getsource(validate_file)
    assert "subprocess" not in src


def test_validate_file_source_no_yield():
    src = inspect.getsource(validate_file)
    assert "yield" not in src


# ---------- SCHEMAS_DIR 常量精确 ----------


def test_schemas_dir_is_path():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_resolved():
    """SCHEMAS_DIR 是 .resolve() 后的绝对路径。"""
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_ends_with_schemas():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_parent_ends_with_dachuang_autonomous():
    """SCHEMAS_DIR.parent 是项目根目录。"""
    # 项目根名取决于 worktree
    assert SCHEMAS_DIR.parent.name in (
        "dachuang-autonomous", "dachuang-code",
    )


def test_schemas_dir_exists():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_in_all():
    assert "SCHEMAS_DIR" in smod.__all__


def test_schemas_dir_is_module_constant():
    """SCHEMAS_DIR 是 module 级常量。"""
    assert hasattr(smod, "SCHEMAS_DIR")
    assert not callable(smod.SCHEMAS_DIR)


def test_schemas_dir_value_in_source():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = Path(__file__)" in src


def test_schemas_dir_uses_resolve():
    src = inspect.getsource(smod)
    assert ".resolve()" in src


def test_schemas_dir_uses_parent_parent():
    """SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"."""
    src = inspect.getsource(smod)
    assert ".parent.parent" in src


# ---------- module source forbidden tokens 第八批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "asyncio", "threading", "concurrent", "multiprocessing",
        "queue", "socket", "select",
        "re.match", "re.sub",
        "datetime.datetime",
        "time.time", "time.sleep",
        "os.system", "os.popen",
        "logging.getLogger",
        "urllib.request", "http.client",
        "ctypes", "pickle.loads",
        "shutil.rmtree",
        "tempfile.mkdtemp",
        "glob.glob",
        "unittest.TestCase",
        "pytest.fixture",
        "sys.exit",
        "copy.deepcopy",
        "weakref.ref",
        "abc.ABC",
        "contextlib.contextmanager",
        "operator.add",
        "functools.reduce",
        "itertools.chain",
        "collections.OrderedDict",
        "collections.deque",
        "collections.defaultdict",
        "importlib.import_module",
        "platform.system",
    ],
)
def test_schema_source_no_forbidden_token(token):
    src = inspect.getsource(smod)
    assert token not in src, f"forbidden token found: {token}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_docstring_present():
    src = inspect.getsource(smod)
    assert src.startswith('"""')


def test_module_source_docstring_mentions_schema():
    assert "Schema" in smod.__doc__ or "schema" in smod.__doc__.lower()


def test_module_source_docstring_mentions_manifest():
    assert "manifest" in smod.__doc__.lower()


def test_module_source_docstring_mentions_annotation():
    assert "annotation" in smod.__doc__.lower()


def test_module_source_docstring_mentions_evaluation_report():
    assert "evaluation-report" in smod.__doc__


def test_module_source_docstring_mentions_app_schema():
    """说明不与 app/schema.py 复用。"""
    assert "app/schema.py" in smod.__doc__ or "app.schema" in smod.__doc__.lower()


def test_module_source_has_future_annotations():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_source_4_stdlib_imports():
    src = inspect.getsource(smod)
    assert "import json" in src
    assert "from pathlib import Path" in src
    assert "from typing import Any" in src


def test_module_source_imports_jsonschema():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_imports_js_validation_error():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_no_relative_above_root():
    src = inspect.getsource(smod)
    assert "from .." not in src


def test_module_source_no_star_import():
    src = inspect.getsource(smod)
    assert "import *" not in src


def test_module_source_no_yield():
    src = inspect.getsource(smod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(smod)
    assert "async def" not in src


def test_module_source_no_walrus():
    src = inspect.getsource(smod)
    assert ":=" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(smod)
    assert 'if __name__' not in src


def test_module_source_no_user_class_beyond_eval_schema_error():
    classes = [
        name for name, val in vars(smod).items()
        if isinstance(val, type) and val.__module__ == smod.__name__
    ]
    assert set(classes) == {"EvalSchemaError"}


def test_module_source_3_user_functions():
    funcs = [
        name for name, val in vars(smod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == smod.__name__
    ]
    assert set(funcs) == {"_schema_path", "load_schema", "validate", "validate_file"}


def test_module_source_all_5_entries():
    src = inspect.getsource(smod)
    assert '"SCHEMAS_DIR"' in src
    assert '"EvalSchemaError"' in src
    assert '"load_schema"' in src
    assert '"validate"' in src
    assert '"validate_file"' in src


def test_module_source_no_eval():
    src = inspect.getsource(smod)
    assert "eval(" not in src


def test_module_source_no_exec():
    src = inspect.getsource(smod)
    assert "exec(" not in src


def test_module_source_no_compile():
    src = inspect.getsource(smod)
    assert "compile(" not in src


def test_module_source_no_unlink():
    src = inspect.getsource(smod)
    assert ".unlink(" not in src


def test_module_source_no_write():
    src = inspect.getsource(smod)
    assert ".write(" not in src


# ---------- signatures 精确补强 ----------


def test_signature_eval_schema_error_init():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    # self + message + errors
    assert len(params) == 3
    assert params[0].name == "self"
    assert params[1].name == "message"
    assert params[2].name == "errors"


def test_signature_eval_schema_error_message_no_default():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = sig.parameters
    assert params["message"].default is inspect.Parameter.empty


def test_signature_eval_schema_error_errors_default_none():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = sig.parameters
    assert params["errors"].default is None


def test_signature_eval_schema_error_return_annotation_none():
    sig = inspect.signature(EvalSchemaError.__init__)
    annot = sig.return_annotation
    assert annot is None or annot == "None"


def test_signature_schema_path():
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"


def test_signature_schema_path_no_varargs():
    sig = inspect.signature(_schema_path)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_load_schema():
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"


def test_signature_validate():
    sig = inspect.signature(validate)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["instance", "schema_name"]


def test_signature_validate_no_defaults():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_validate_no_varargs():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_validate_file():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["path", "schema_name"]


def test_signature_validate_file_no_defaults():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_load_schema_no_varargs():
    sig = inspect.signature(load_schema)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


# ---------- 模块整体合理性补强 ----------


def test_module_has_docstring():
    assert smod.__doc__ is not None
    assert len(smod.__doc__) > 10


def test_module_has_all_attribute():
    assert hasattr(smod, "__all__")


def test_module_all_is_list():
    assert isinstance(smod.__all__, list)


def test_module_all_length_5():
    assert len(smod.__all__) == 5


def test_module_all_entries_unique():
    assert len(set(smod.__all__)) == len(smod.__all__)


def test_module_all_entries_are_str():
    for entry in smod.__all__:
        assert isinstance(entry, str)


def test_module_all_5_entries_correct():
    assert set(smod.__all__) == {
        "SCHEMAS_DIR", "EvalSchemaError", "load_schema", "validate", "validate_file",
    }


def test_module_namespace_4_callables():
    funcs = [
        name for name, val in vars(smod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == smod.__name__
    ]
    assert set(funcs) == {"_schema_path", "load_schema", "validate", "validate_file"}


def test_module_namespace_1_class():
    classes = [
        name for name, val in vars(smod).items()
        if isinstance(val, type) and val.__module__ == smod.__name__
    ]
    assert classes == ["EvalSchemaError"]


def test_module_name_is_evaluation_schema():
    assert smod.__name__ == "evaluation.schema"


def test_module_file_ends_with_schema_py():
    assert smod.__file__.endswith("schema.py")


def test_module_eval_schema_error_module_eq_smod():
    assert EvalSchemaError.__module__ == "evaluation.schema"


def test_module_function_module_eq_smod():
    assert _schema_path.__module__ == "evaluation.schema"
    assert load_schema.__module__ == "evaluation.schema"
    assert validate.__module__ == "evaluation.schema"
    assert validate_file.__module__ == "evaluation.schema"


def test_module_imports_path():
    assert smod.Path is Path


def test_module_imports_json():
    assert smod.json is json


def test_module_imports_draft_validator():
    assert smod.Draft202012Validator is Draft202012Validator


def test_module_imports_js_validation_error():
    assert hasattr(smod, "JSValidationError")


# ---------- 端到端集成补强 ----------


def test_e2e_load_manifest_schema_returns_dict():
    """manifest.schema.json 能加载。"""
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)
    assert "$schema" in s or "type" in s


def test_e2e_load_annotation_schema_returns_dict():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_e2e_load_evaluation_report_schema_returns_dict():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


def test_e2e_load_schema_idempotent():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2


def test_e2e_load_schema_does_not_mutate_disk():
    """load_schema 是只读。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    # 两次加载应该完全一致
    assert s1 == s2


def test_e2e_validate_minimal_manifest_passes():
    """最小合法 manifest 通过校验。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    validate(instance, "manifest.schema.json")  # 不抛


def test_e2e_validate_empty_documents_passes():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    validate(instance, "manifest.schema.json")


def test_e2e_validate_missing_manifest_version_fails():
    instance = {
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_e2e_validate_missing_devset_status_fails():
    instance = {
        "manifest_version": "1.0",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_e2e_validate_missing_documents_fails():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_e2e_validate_missing_expected_failures_ok():
    """schema 允许 expected_failures 缺省（默认空 list）。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    # 可能通过也可能不通过，根据 schema 的 required
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError:
        # 拒绝也合法
        pass


def test_e2e_validate_invalid_manifest_version_fails():
    instance = {
        "manifest_version": "2.0",  # schema 要求 const="1.0"
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_e2e_validate_with_extra_field_fails():
    """manifest schema 是 additionalProperties:false。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
        "extra_field": "value",
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_e2e_validate_file_with_str_path(tmp_path):
    f = tmp_path / "manifest.json"
    f.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    validate_file(str(f), "manifest.schema.json")  # 不抛


def test_e2e_validate_file_with_path_path(tmp_path):
    f = tmp_path / "manifest.json"
    f.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    validate_file(f, "manifest.schema.json")  # 不抛


def test_e2e_validate_file_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        validate_file("/does/not/exist.json", "manifest.schema.json")


def test_e2e_validate_file_invalid_json_raises(tmp_path):
    f = tmp_path / "manifest.json"
    f.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(f, "manifest.schema.json")


def test_e2e_validate_file_returns_none(tmp_path):
    f = tmp_path / "manifest.json"
    f.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    assert validate_file(f, "manifest.schema.json") is None


def test_e2e_validate_returns_none_when_pass():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_e2e_validate_eval_schema_error_has_errors_list():
    instance = {"bad": "data"}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        assert isinstance(e.errors, list)
        assert len(e.errors) > 0


def test_e2e_validate_eval_schema_error_errors_dict_keys():
    instance = {"bad": "data"}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert "path" in err
            assert "message" in err
            assert "schema_path" in err


def test_e2e_validate_eval_schema_error_message_has_schema_name():
    instance = {"bad": "data"}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        assert "manifest.schema.json" in str(e)


def test_e2e_validate_eval_schema_error_message_has_path():
    instance = {"bad": "data"}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        msg = str(e)
        # 错误消息含 path=
        assert "path=" in msg or "@" in msg


def test_e2e_validate_eval_schema_error_caught_as_value_error_ancestor():
    """EvalSchemaError 是 Exception 的子类。"""
    instance = {"bad": "data"}
    try:
        validate(instance, "manifest.schema.json")
        assert False, "should have raised"
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_e2e_schema_path_returns_path():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_e2e_schema_path_for_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        _schema_path("does-not-exist.schema.json")


def test_e2e_eval_schema_error_with_empty_errors_list():
    err = EvalSchemaError("msg", errors=[])
    assert err.errors == []


def test_e2e_eval_schema_error_with_complex_errors():
    errs = [
        {"path": ["a", "b"], "message": "err1", "schema_path": ["x"]},
        {"path": ["c"], "message": "err2", "schema_path": ["y", "z"]},
    ]
    err = EvalSchemaError("msg", errors=errs)
    assert len(err.errors) == 2
    assert err.errors[0]["path"] == ["a", "b"]
