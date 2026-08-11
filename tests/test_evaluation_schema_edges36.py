"""evaluation/schema.py 第三十六轮 edges 测试（Round 442）。

补强 edges35 未触及的角度：
- SCHEMAS_DIR 常量深度第十六批（resolve 等幂 / is_dir / parent 项目根 / sibling .gitignore）
- EvalSchemaError 行为深度第十六批（args 单元素 / str 默认 / raise with from / errors=None vs []）
- load_schema 行为深度第十六批（schema idempotent / 不同实例相同 / 多次调用相同 / load 后修改不影响下次）
- validate 行为深度第十六批（instance 多个错误 / instance 含额外字段 / instance 类型错误 / instance 字段类型错 / annotation schema 校验）
- validate_file 行为深度第十六批（path str / Path / 含 BOM / 多次调用一致 / 不修改文件）
- _schema_path 行为深度第十六批（多级 name 拒绝 / unicode name / 返回 SCHEMAS_DIR/name）
- module source forbidden tokens 第三十一批
- module source 字符串精确补强第二十七批
- signatures 第二十七批
- module 合理性第二十七批
- 端到端集成第二十七批
"""

from __future__ import annotations

import inspect
import json
import pickle
from pathlib import Path, PurePath
from unittest.mock import patch, MagicMock

import pytest

from evaluation import schema as smod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- SCHEMAS_DIR 常量深度第十六批 ----------


def test_schemas_dir_is_dir_batch16():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_resolved_idempotent_batch16():
    """resolve() 是幂等的。"""
    assert SCHEMAS_DIR == SCHEMAS_DIR.resolve()


def test_schemas_dir_parent_basename_batch16():
    """SCHEMAS_DIR.parent.basename 是项目根。"""
    parent = SCHEMAS_DIR.parent
    # 项目根有 pyproject.toml
    assert (parent / "pyproject.toml").is_file()


def test_schemas_dir_parent_has_evaluation_batch16():
    parent = SCHEMAS_DIR.parent
    assert (parent / "evaluation").is_dir()


def test_schemas_dir_parent_has_app_batch16():
    parent = SCHEMAS_DIR.parent
    assert (parent / "app").is_dir()


def test_schemas_dir_parent_has_tests_batch16():
    parent = SCHEMAS_DIR.parent
    assert (parent / "tests").is_dir()


def test_schemas_dir_parent_has_schemas_batch16():
    """SCHEMAS_DIR 是 parent/schemas。"""
    parent = SCHEMAS_DIR.parent
    assert (parent / "schemas").is_dir()


def test_schemas_dir_str_endswith_batch16():
    s = str(SCHEMAS_DIR).replace("\\", "/")
    assert s.endswith("/schemas")


def test_schemas_dir_count_files_batch16():
    files = list(SCHEMAS_DIR.glob("*.schema.json"))
    # 至少有 3 个 schema 文件
    assert len(files) >= 3


# ---------- EvalSchemaError 行为深度第十六批 ----------


def test_eval_schema_error_args_batch16():
    err = EvalSchemaError("msg")
    assert err.args == ("msg",)


def test_eval_schema_error_args_multiple_batch16():
    err = EvalSchemaError("msg", errors=[{"x": 1}])
    # super().__init__("msg") 只把 message 放 args
    assert err.args == ("msg",)


def test_eval_schema_error_str_default_batch16():
    err = EvalSchemaError("hello")
    assert str(err) == "hello"


def test_eval_schema_error_errors_default_empty_batch16():
    err = EvalSchemaError("msg")
    assert err.errors == []


def test_eval_schema_error_errors_none_to_empty_batch16():
    err = EvalSchemaError("msg", errors=None)
    assert err.errors == []


def test_eval_schema_error_errors_given_batch16():
    errs = [{"path": ["a"]}]
    err = EvalSchemaError("msg", errors=errs)
    assert err.errors == errs


def test_eval_schema_error_raise_with_from_batch16():
    """`raise X from Y` 应设 __cause__。"""
    try:
        try:
            raise ValueError("inner")
        except ValueError as e:
            raise EvalSchemaError("outer", errors=[{"path": []}]) from e
    except EvalSchemaError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, ValueError)


def test_eval_schema_error_can_be_raised_and_caught_batch16():
    with pytest.raises(EvalSchemaError) as exc_info:
        raise EvalSchemaError("x")
    assert exc_info.value.errors == []


def test_eval_schema_error_is_exception_batch16():
    err = EvalSchemaError("x")
    assert isinstance(err, Exception)


def test_eval_schema_error_pickle_roundtrip_batch16():
    err = EvalSchemaError("m", errors=[{"path": ["x"]}])
    data = pickle.dumps(err)
    restored = pickle.loads(data)
    assert isinstance(restored, EvalSchemaError)
    assert str(restored) == "m"


def test_eval_schema_error_errors_independent_batch16():
    """两次实例化的 errors 默认是不同 list 对象。"""
    e1 = EvalSchemaError("a")
    e2 = EvalSchemaError("b")
    assert e1.errors is not e2.errors
    e1.errors.append({"x": 1})
    assert e2.errors == []


# ---------- load_schema 行为深度第十六批 ----------


def test_load_schema_returns_dict_for_all_three_batch16():
    for name in ["manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json"]:
        s = load_schema(name)
        assert isinstance(s, dict)


def test_load_schema_idempotent_batch16():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2
    # 但是不同对象（每次都重新 json.load）
    assert s1 is not s2


def test_load_schema_modification_does_not_persist_batch16():
    """修改返回的 dict 不影响下次加载。"""
    s1 = load_schema("manifest.schema.json")
    s1["_test"] = "modified"
    s2 = load_schema("manifest.schema.json")
    assert "_test" not in s2


def test_load_schema_distinct_for_three_batch16():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("annotation.schema.json")
    s3 = load_schema("evaluation-report.schema.json")
    assert s1 != s2
    assert s2 != s3
    assert s1 != s3


def test_load_schema_unknown_raises_filenotfound_batch16():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_with_subpath_raises_filenotfound_batch16():
    """带子目录的 name 不存在。"""
    with pytest.raises(FileNotFoundError):
        load_schema("subdir/manifest.schema.json")


def test_load_schema_returns_schema_with_properties_batch16():
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_load_schema_manifest_has_documents_batch16():
    s = load_schema("manifest.schema.json")
    assert "documents" in s.get("properties", {})


# ---------- validate 行为深度第十六批 ----------


def test_validate_success_returns_none_batch16():
    inst = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }
    assert validate(inst, "manifest.schema.json") is None


def test_validate_invalid_returns_errors_batch16():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    # required 字段都缺 → 至少 3 个错误（manifest_version/devset_status/documents）
    assert len(exc_info.value.errors) >= 3


def test_validate_errors_path_is_list_batch16():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert isinstance(err["path"], list)


def test_validate_errors_message_is_str_batch16():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert isinstance(err["message"], str)


def test_validate_errors_schema_path_is_list_batch16():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert isinstance(err["schema_path"], list)


def test_validate_message_contains_count_batch16():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    msg = str(exc_info.value)
    assert "校验失败" in msg
    # 至少 4 个 required 错误
    assert "处" in msg


def test_validate_unknown_schema_raises_filenotfound_batch16():
    with pytest.raises(FileNotFoundError):
        validate({}, "nonexistent.schema.json")


def test_validate_does_not_modify_instance_batch16():
    inst = {"manifest_version": "1.0", "devset_status": "incomplete",
            "documents": [], "expected_failures": []}
    before = json.dumps(inst, sort_keys=True)
    validate(inst, "manifest.schema.json")
    after = json.dumps(inst, sort_keys=True)
    assert before == after


def test_validate_annotation_schema_batch16():
    """annotation schema 也校验通过。"""
    inst = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [],
    }
    validate(inst, "annotation.schema.json")


def test_validate_annotation_schema_invalid_batch16():
    """annotation schema 缺 doc_id → 校验失败。"""
    with pytest.raises(EvalSchemaError):
        validate({"annotation_version": "1.0"}, "annotation.schema.json")


def test_validate_evaluation_report_schema_batch16():
    """evaluation-report schema 的最小合法 instance。"""
    # 完整结构太复杂，只测路径
    # 缺字段 → 抛 EvalSchemaError
    with pytest.raises(EvalSchemaError):
        validate({}, "evaluation-report.schema.json")


def test_validate_extra_fields_rejected_batch16():
    """manifest schema 有 additionalProperties=False，应拒绝额外字段。"""
    inst = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
        "extra_field": "x",
    }
    with pytest.raises(EvalSchemaError):
        validate(inst, "manifest.schema.json")


# ---------- validate_file 行为深度第十六批 ----------


def test_validate_file_path_str_batch16(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_path_object_batch16(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_bom_fails_batch16(tmp_path):
    """UTF-8 BOM → json.load 失败。"""
    p = tmp_path / "m.json"
    content = json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }).encode("utf-8")
    p.write_bytes(b"\xef\xbb\xbf" + content)
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_idempotent_batch16(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")


def test_validate_file_not_exists_batch16(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "no.json", "manifest.schema.json")


def test_validate_file_invalid_json_batch16(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_does_not_modify_file_batch16(tmp_path):
    p = tmp_path / "m.json"
    content = json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    })
    p.write_text(content, encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    assert p.read_text(encoding="utf-8") == content


def test_validate_file_invalid_schema_name_batch16(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "nonexistent.schema.json")


# ---------- _schema_path 行为深度第十六批 ----------


def test_schema_path_concat_batch16():
    p = _schema_path("manifest.schema.json")
    assert p == SCHEMAS_DIR / "manifest.schema.json"


def test_schema_path_returns_path_batch16():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)
    assert p.is_file()


def test_schema_path_subdir_rejected_batch16():
    """子目录路径不存在。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/manifest.schema.json")


def test_schema_path_unicode_name_batch16():
    """Unicode name 也走 FileNotFoundError（schemas 下没有这种文件）。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("中文.schema.json")


def test_schema_path_empty_batch16():
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_message_format_batch16():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nope.schema.json")
    msg = str(exc_info.value)
    assert "nope.schema.json" in msg
    assert "Schema 文件不存在" in msg


def test_schema_path_valid_for_three_schemas_batch16():
    for name in ["manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json"]:
        p = _schema_path(name)
        assert p.is_file()


# ---------- module source forbidden tokens 第三十一批 ----------


@pytest.mark.parametrize("forbidden", [
    "pty.spawn",
    "commands.getoutput",
    "paramiko",
    "fabric.api",
    "ftplib",
    "smtplib",
    "telnetlib",
    "webbrowser.open",
    "socket.socket",
    "asyncio.open_connection",
    "multiprocessing.Process",
    "threading.Thread",
    "ctypes.CDLL",
    "pickle.dumps",
    "shutil.rmtree",
    "sys.exit",
])
def test_module_source_forbidden_tokens_batch16(forbidden):
    src = inspect.getsource(smod)
    assert forbidden not in src


def test_module_source_no_subprocess_batch16():
    src = inspect.getsource(smod)
    assert "import subprocess" not in src


def test_module_source_no_network_batch16():
    src = inspect.getsource(smod)
    assert "urllib.request" not in src
    assert "import requests" not in src


# ---------- module source 字符串精确补强第二十七批 ----------


def test_module_source_has_future_annotations_batch16():
    src = inspect.getsource(smod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch16():
    src = inspect.getsource(smod)
    assert "加载并校验本阶段三个新 Schema" in src


def test_module_source_has_json_import_batch16():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_has_pathlib_import_batch16():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch16():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_has_jsonschema_import_batch16():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_has_validation_error_import_batch16():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_has_schemas_dir_definition_batch16():
    src = inspect.getsource(smod)
    assert 'SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"' in src


def test_module_source_has_class_eval_schema_error_batch16():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_has_load_schema_function_batch16():
    src = inspect.getsource(smod)
    assert "def load_schema(name: str) -> dict[str, Any]:" in src


def test_module_source_has_validate_function_batch16():
    src = inspect.getsource(smod)
    assert "def validate(instance: dict[str, Any], schema_name: str) -> None:" in src


def test_module_source_has_validate_file_function_batch16():
    src = inspect.getsource(smod)
    assert "def validate_file(path: Path | str, schema_name: str) -> None:" in src


def test_module_source_has_schema_path_function_batch16():
    src = inspect.getsource(smod)
    assert "def _schema_path(name: str) -> Path:" in src


def test_module_source_has_iter_errors_batch16():
    src = inspect.getsource(smod)
    assert "iter_errors" in src


def test_module_source_has_all_dunder_batch16():
    src = inspect.getsource(smod)
    assert "__all__ = [" in src


def test_module_source_all_has_5_items_batch16():
    src = inspect.getsource(smod)
    for name in ['"SCHEMAS_DIR"', '"EvalSchemaError"', '"load_schema"',
                 '"validate"', '"validate_file"']:
        assert name in src


# ---------- signatures 第二十七批 ----------


def test_signature_load_schema_batch16():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_validate_batch16():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_signature_validate_file_batch16():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_signature_schema_path_batch16():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_eval_schema_error_init_batch16():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "errors"]
    assert sig.parameters["errors"].default is None


def test_signature_load_schema_no_varargs_batch16():
    sig = inspect.signature(load_schema)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


# ---------- module 合理性第二十七批 ----------


def test_module_has_all_attribute_batch16():
    assert hasattr(smod, "__all__")
    assert isinstance(smod.__all__, list)


def test_module_all_items_in_namespace_batch16():
    for name in smod.__all__:
        assert hasattr(smod, name)


def test_module_all_count_5_batch16():
    assert len(smod.__all__) == 5


def test_module_load_schema_callable_batch16():
    assert callable(load_schema)


def test_module_validate_callable_batch16():
    assert callable(validate)


def test_module_validate_file_callable_batch16():
    assert callable(validate_file)


def test_module_schema_path_callable_batch16():
    assert callable(_schema_path)


def test_module_does_not_import_app_schema_batch16():
    """不与 app/schema.py 复用。"""
    src = inspect.getsource(smod)
    assert "from app.schema" not in src
    assert "import app.schema" not in src


def test_module_does_not_import_unsafe_modules_batch16():
    src = inspect.getsource(smod)
    for unsafe in ["import pickle", "import marshal", "import shelve", "import subprocess"]:
        assert unsafe not in src


# ---------- 端到端集成第二十七批 ----------


def test_e2e_validate_manifest_full_batch16():
    inst = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }
    validate(inst, "manifest.schema.json")


def test_e2e_validate_annotation_full_batch16():
    inst = {
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [{"marker": "x", "position": "after"}],
    }
    validate(inst, "annotation.schema.json")


def test_e2e_load_then_validate_round_trip_batch16():
    """load schema → 直接用 Draft202012Validator 校验。"""
    inst = {"manifest_version": "1.0", "devset_status": "incomplete",
            "documents": [], "expected_failures": []}
    schema = load_schema("manifest.schema.json")
    from jsonschema import Draft202012Validator
    errors = list(Draft202012Validator(schema).iter_errors(inst))
    assert errors == []


def test_e2e_eval_schema_error_with_complex_errors_batch16():
    complex_errs = [
        {"path": ["a", "b"], "message": "type", "schema_path": ["properties"]},
        {"path": ["c"], "message": "missing", "schema_path": ["required"]},
    ]
    err = EvalSchemaError("complex", errors=complex_errs)
    assert err.errors == complex_errs


def test_e2e_validate_file_full_batch16(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_validate_three_schemas_distinct_content_batch16():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("annotation.schema.json")
    s3 = load_schema("evaluation-report.schema.json")
    assert s1 != s2 != s3 != s1


def test_e2e_schema_path_round_trip_batch16():
    """_schema_path → json.load == load_schema。"""
    p = _schema_path("manifest.schema.json")
    with p.open("r", encoding="utf-8") as f:
        s = json.load(f)
    assert s == load_schema("manifest.schema.json")


def test_e2e_eval_schema_error_chained_with_from_batch16():
    try:
        try:
            raise ValueError("inner")
        except ValueError as e:
            raise EvalSchemaError("outer", errors=[{"path": []}]) from e
    except EvalSchemaError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, ValueError)


def test_e2e_validate_does_not_pollute_schema_dict_batch16():
    """validate 不应修改 schema dict（每次重新 load）。"""
    schema_before = repr(load_schema("manifest.schema.json"))
    inst = {"manifest_version": "1.0", "devset_status": "incomplete",
            "documents": [], "expected_failures": []}
    validate(inst, "manifest.schema.json")
    schema_after = repr(load_schema("manifest.schema.json"))
    assert schema_before == schema_after


def test_e2e_validate_with_unicode_content_batch16():
    inst = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "中文", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }
    validate(inst, "manifest.schema.json")
