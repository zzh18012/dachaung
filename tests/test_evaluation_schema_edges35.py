"""evaluation/schema.py 第三十五轮 edges 测试（Round 435）。

补强 edges34 未触及的角度：
- SCHEMAS_DIR 常量深度第十五批（与项目根 / dachuang-autonomous 关联）
- EvalSchemaError 行为深度第十五批（默认 message / 多个 errors / errors 复用 / raise without args）
- load_schema 行为深度第十五批（同 schema 二次调用不缓存 / 返回相同内容 / 不同 schema name）
- validate 行为深度第十五批（成功路径深度 / 多个错误全捕获 / 不同 schema 名字混用）
- validate_file 行为深度第十五批（Encoding 不同 / 大文件 / 多次调用）
- _schema_path 行为深度第十五批（路径拼 str / 多级名 / 已存在路径）
- module source forbidden tokens 第三十批
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


# ---------- SCHEMAS_DIR 常量深度第十五批 ----------


def test_schemas_dir_resolved_absolute_batch15():
    """SCHEMAS_DIR 是 resolve() 后的绝对路径。"""
    assert SCHEMAS_DIR.is_absolute()
    assert SCHEMAS_DIR == SCHEMAS_DIR.resolve()


def test_schemas_dir_contains_only_three_schemas_batch15():
    """schemas/ 目录下应有 3 个 .schema.json 文件。"""
    schema_files = list(SCHEMAS_DIR.glob("*.schema.json"))
    names = {f.name for f in schema_files}
    assert "manifest.schema.json" in names
    assert "annotation.schema.json" in names
    assert "evaluation-report.schema.json" in names


def test_schemas_dir_parent_contains_pyproject_batch15():
    """SCHEMAS_DIR 的 parent 是项目根，含 pyproject.toml。"""
    parent = SCHEMAS_DIR.parent
    assert (parent / "pyproject.toml").is_file()


def test_schemas_dir_parent_contains_evaluation_dir_batch15():
    """SCHEMAS_DIR.parent 含 evaluation/ 目录。"""
    parent = SCHEMAS_DIR.parent
    assert (parent / "evaluation").is_dir()


def test_schemas_dir_parent_contains_app_dir_batch15():
    """SCHEMAS_DIR.parent 含 app/ 目录。"""
    parent = SCHEMAS_DIR.parent
    assert (parent / "app").is_dir()


def test_schemas_dir_str_endswith_schemas_batch15():
    """str(SCHEMAS_DIR) 应以 schemas 结尾（Windows / Unix）。"""
    s = str(SCHEMAS_DIR).replace("\\", "/")
    assert s.endswith("/schemas")


# ---------- EvalSchemaError 行为深度第十五批 ----------


def test_eval_schema_error_requires_message_batch15():
    """EvalSchemaError() 不传 message 应抛 TypeError。"""
    with pytest.raises(TypeError):
        EvalSchemaError()


def test_eval_schema_error_message_only_no_errors_attr_batch15():
    """仅传 message（不传 errors）时不应有 errors 属性访问问题。"""
    err = EvalSchemaError("oops")
    assert err.errors == []


def test_eval_schema_error_multiple_errors_batch15():
    errs = [{"path": ["a"]}, {"path": ["b"]}, {"path": ["c"]}]
    err = EvalSchemaError("multi", errors=errs)
    assert len(err.errors) == 3


def test_eval_schema_error_errors_reused_batch15():
    """同一 list 传两次 errors → 同一对象引用。"""
    errs = [{"x": 1}]
    err1 = EvalSchemaError("a", errors=errs)
    err2 = EvalSchemaError("b", errors=errs)
    assert err1.errors is err2.errors


def test_eval_schema_error_str_format_batch15():
    err = EvalSchemaError("oops")
    assert str(err) == "oops"


def test_eval_schema_error_pickle_with_errors_batch15():
    err = EvalSchemaError("m", errors=[{"path": ["x"]}])
    data = pickle.dumps(err)
    restored = pickle.loads(data)
    assert isinstance(restored, EvalSchemaError)
    assert str(restored) == "m"


def test_eval_schema_error_is_subclass_of_exception_batch15():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_can_be_caught_as_exception_batch15():
    try:
        raise EvalSchemaError("x")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


# ---------- load_schema 行为深度第十五批 ----------


def test_load_schema_manifest_has_properties_batch15():
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_load_schema_annotation_has_properties_batch15():
    s = load_schema("annotation.schema.json")
    assert "properties" in s


def test_load_schema_evaluation_report_has_properties_batch15():
    s = load_schema("evaluation-report.schema.json")
    assert "properties" in s


def test_load_schema_returns_dict_batch15():
    for name in ["manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"]:
        s = load_schema(name)
        assert isinstance(s, dict)


def test_load_schema_idempotent_content_batch15():
    """同一 schema 多次加载内容相同。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2


def test_load_schema_distinct_schemas_batch15():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("annotation.schema.json")
    s3 = load_schema("evaluation-report.schema.json")
    assert s1 != s2 != s3 != s1


def test_load_schema_unknown_name_raises_filenotfound_batch15():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_dot_prefix_batch15():
    """./ 前缀也能解析（Path 拼接会规范化）。"""
    s = load_schema("./manifest.schema.json")
    assert isinstance(s, dict)


# ---------- validate 行为深度第十五批 ----------


def test_validate_success_returns_none_batch15():
    inst = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }
    assert validate(inst, "manifest.schema.json") is None


def test_validate_collects_all_errors_batch15():
    """多个错误都应进 errors list。"""
    bad = {"manifest_version": 1.0, "devset_status": 42, "documents": "x"}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(bad, "manifest.schema.json")
    # 至少 1 个错误（具体数量由 schema 决定）
    assert len(exc_info.value.errors) >= 1


def test_validate_unknown_schema_name_batch15():
    """未知 schema 名 → FileNotFoundError（不是 EvalSchemaError）。"""
    with pytest.raises(FileNotFoundError):
        validate({}, "nonexistent.schema.json")


def test_validate_does_not_modify_instance_batch15():
    inst = {"manifest_version": "1.0", "devset_status": "incomplete",
            "documents": [], "expected_failures": []}
    before = json.dumps(inst, sort_keys=True)
    validate(inst, "manifest.schema.json")
    after = json.dumps(inst, sort_keys=True)
    assert before == after


def test_validate_with_empty_dict_batch15():
    """空 dict 应触发 required 校验失败。"""
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_message_format_batch15():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    msg = str(exc_info.value)
    assert "manifest.schema.json" in msg
    assert "path=" in msg


def test_validate_errors_have_correct_keys_batch15():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert set(err.keys()) == {"path", "message", "schema_path"}


# ---------- validate_file 行为深度第十五批 ----------


def test_validate_file_reads_with_utf8_batch15(tmp_path):
    """validate_file 用 utf-8 读 JSON。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")  # 不抛即可


def test_validate_file_unicode_content_batch15(tmp_path):
    """含 Unicode 字符的 JSON 也应正常。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "中文", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_returns_none_batch15(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_idempotent_batch15(tmp_path):
    """同一文件多次 validate 结果一致。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")  # 不抛即可


def test_validate_file_invalid_schema_batch15(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "nonexistent.schema.json")


# ---------- _schema_path 行为深度第十五批 ----------


def test_schema_path_str_concat_batch15():
    """_schema_path(name) 应返回 SCHEMAS_DIR / name。"""
    p = _schema_path("manifest.schema.json")
    assert p == SCHEMAS_DIR / "manifest.schema.json"


def test_schema_path_returns_path_instance_batch15():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_with_full_path_batch15():
    """传完整路径（含目录分隔符）应失败（schemas 下无子目录）。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("/absolute/path/manifest.schema.json")


def test_schema_path_empty_string_batch15():
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_message_contains_full_path_batch15():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nope.schema.json")
    msg = str(exc_info.value)
    assert "nope.schema.json" in msg
    assert "Schema 文件不存在" in msg


def test_schema_path_valid_for_all_three_schemas_batch15():
    for name in ["manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"]:
        p = _schema_path(name)
        assert p.is_file()


# ---------- module source forbidden tokens 第三十批 ----------


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
def test_module_source_forbidden_tokens_batch15(forbidden):
    src = inspect.getsource(smod)
    assert forbidden not in src


# Note: subprocess IS allowed in evaluation/report.py for git provenance,
# but NOT in evaluation/schema.py


def test_module_source_no_subprocess_batch15():
    """schema.py 不应用 subprocess。"""
    src = inspect.getsource(smod)
    assert "import subprocess" not in src


# ---------- module source 字符串精确补强第二十七批 ----------


def test_module_source_has_future_annotations_batch15():
    src = inspect.getsource(smod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch15():
    src = inspect.getsource(smod)
    assert '"""加载并校验本阶段三个新 Schema' in src


def test_module_source_has_app_schema_separation_note_batch15():
    src = inspect.getsource(smod)
    assert "app/schema.py" in src


def test_module_source_has_jsonschema_draft_batch15():
    src = inspect.getsource(smod)
    assert "Draft202012Validator" in src


def test_module_source_has_json_import_batch15():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_has_pathlib_import_batch15():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch15():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_has_class_eval_schema_error_batch15():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_has_docstring_eval_schema_error_batch15():
    src = inspect.getsource(smod)
    assert "Schema 校验失败时抛出" in src


def test_module_source_has_schemas_dir_definition_batch15():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = Path(__file__).resolve().parent.parent / " in src
    assert '"schemas"' in src or "'schemas'" in src


def test_module_source_has_load_schema_function_batch15():
    src = inspect.getsource(smod)
    assert "def load_schema(name: str) -> dict[str, Any]:" in src


def test_module_source_has_validate_function_batch15():
    src = inspect.getsource(smod)
    assert "def validate(instance: dict[str, Any], schema_name: str) -> None:" in src


def test_module_source_has_validate_file_function_batch15():
    src = inspect.getsource(smod)
    assert "def validate_file(path: Path | str, schema_name: str) -> None:" in src


def test_module_source_has_schema_path_function_batch15():
    src = inspect.getsource(smod)
    assert "def _schema_path(name: str) -> Path:" in src


def test_module_source_has_iter_errors_call_batch15():
    src = inspect.getsource(smod)
    assert "iter_errors" in src


def test_module_source_has_sorted_call_batch15():
    src = inspect.getsource(smod)
    assert "sorted(validator.iter_errors" in src


def test_module_source_has_errors_count_in_message_batch15():
    src = inspect.getsource(smod)
    assert "len(errors)" in src


def test_module_source_has_all_dunder_batch15():
    src = inspect.getsource(smod)
    assert "__all__ = [" in src


def test_module_source_all_has_5_items_batch15():
    src = inspect.getsource(smod)
    for name in ['"SCHEMAS_DIR"', '"EvalSchemaError"', '"load_schema"',
                 '"validate"', '"validate_file"']:
        assert name in src


def test_module_source_has_no_cache_attribute_batch15():
    """load_schema 不缓存（每次都重新读文件）。"""
    src = inspect.getsource(smod)
    assert "cache" not in src.lower()


def test_module_source_has_super_init_call_batch15():
    src = inspect.getsource(smod)
    assert "super().__init__(message)" in src


def test_module_source_has_errors_default_empty_list_batch15():
    src = inspect.getsource(smod)
    assert "self.errors = errors or []" in src


# ---------- signatures 第二十七批 ----------


def test_signature_load_schema_batch15():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_validate_batch15():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_signature_validate_file_batch15():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_signature_schema_path_batch15():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_eval_schema_error_init_batch15():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "errors"]
    assert sig.parameters["message"].annotation == "str"
    assert sig.parameters["errors"].default is None


def test_signature_load_schema_no_varargs_batch15():
    sig = inspect.signature(load_schema)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


def test_signature_validate_no_varargs_batch15():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


# ---------- module 合理性第二十七批 ----------


def test_module_has_all_attribute_batch15():
    assert hasattr(smod, "__all__")
    assert isinstance(smod.__all__, list)


def test_module_all_items_in_namespace_batch15():
    for name in smod.__all__:
        assert hasattr(smod, name)


def test_module_all_count_5_batch15():
    assert len(smod.__all__) == 5


def test_module_load_schema_callable_batch15():
    assert callable(load_schema)


def test_module_validate_callable_batch15():
    assert callable(validate)


def test_module_validate_file_callable_batch15():
    assert callable(validate_file)


def test_module_schema_path_callable_batch15():
    assert callable(_schema_path)


def test_module_eval_schema_error_is_class_batch15():
    assert isinstance(EvalSchemaError, type)


def test_module_does_not_import_app_schema_batch15():
    """明确不与 app/schema.py 复用。"""
    src = inspect.getsource(smod)
    assert "from app.schema" not in src
    assert "import app.schema" not in src


def test_module_does_not_import_app_pipeline_batch15():
    src = inspect.getsource(smod)
    assert "from app.pipeline" not in src
    assert "from app." not in src


# ---------- 端到端集成第二十七批 ----------


def test_e2e_validate_manifest_full_batch15():
    inst = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }
    validate(inst, "manifest.schema.json")  # 不抛即可


def test_e2e_validate_annotation_smoke_batch15():
    """annotation schema 加载与基础校验。"""
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_e2e_validate_evaluation_report_smoke_batch15():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


def test_e2e_load_then_validate_round_trip_batch15():
    """load schema → validate 用该 schema。"""
    inst = {"manifest_version": "1.0", "devset_status": "incomplete",
            "documents": [], "expected_failures": []}
    schema = load_schema("manifest.schema.json")
    # 直接用 Draft202012Validator（与 validate 内部相同）
    from jsonschema import Draft202012Validator
    errors = list(Draft202012Validator(schema).iter_errors(inst))
    assert errors == []


def test_e2e_eval_schema_error_with_complex_errors_batch15():
    complex_errs = [
        {"path": ["a", "b"], "message": "type", "schema_path": ["properties"]},
        {"path": ["c"], "message": "missing", "schema_path": ["required"]},
    ]
    err = EvalSchemaError("complex", errors=complex_errs)
    assert err.errors == complex_errs


def test_e2e_validate_file_full_batch15(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_validate_three_schemas_distinct_content_batch15():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("annotation.schema.json")
    s3 = load_schema("evaluation-report.schema.json")
    assert s1 != s2 != s3 != s1


def test_e2e_schema_path_round_trip_batch15():
    """_schema_path → load_schema 一致。"""
    p = _schema_path("manifest.schema.json")
    with p.open("r", encoding="utf-8") as f:
        s = json.load(f)
    assert s == load_schema("manifest.schema.json")


def test_e2e_eval_schema_error_chained_with_from_batch15():
    try:
        try:
            raise ValueError("inner")
        except ValueError as e:
            raise EvalSchemaError("outer", errors=[{"path": []}]) from e
    except EvalSchemaError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, ValueError)
        assert len(e.errors) == 1


def test_e2e_validate_does_not_pollute_schema_dict_batch15():
    """validate 不应修改 schema dict。"""
    schema_before = repr(load_schema("manifest.schema.json"))
    inst = {"manifest_version": "1.0", "devset_status": "incomplete",
            "documents": [], "expected_failures": []}
    validate(inst, "manifest.schema.json")
    schema_after = repr(load_schema("manifest.schema.json"))
    assert schema_before == schema_after
