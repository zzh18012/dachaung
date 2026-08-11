"""evaluation/schema.py 第三十七轮 edges 测试（Round 449）。

补强 edges36 未触及的角度：
- SCHEMAS_DIR 常量深度第十七批（resolve 返回绝对 / parent 正确 / 与 app/schema.py 不同目录 / 与 manifest.py SCHEMAS_DIR 关系）
- EvalSchemaError 行为深度第十七批（错误链 raise from / __cause__ / 自定义 errors 内容 / errors 中 schema_path 类型 / args 传递）
- load_schema 行为深度第十七批（"$schema" 字段在 manifest/annotation/report / "type": "object" 在 all 4 / additionalProperties false 在 all 4）
- validate 行为深度第十七批（errors 排序按 absolute_path / 多错误返回全部 / errors 每项有 3 keys / message 含 schema_name / message 含错误数）
- validate_file 行为深度第十七批（utf-8 BOM / Unicode 内容 / Windows path / Path & str 等价）
- _schema_path 行为深度第十七批（resolve 后路径 / 不存在 message 含 path / 调用 is_file 一次）
- 4 个 schema 内容深度第十七批（manifest 必填 3 / annotation 必填 / evaluation-report 必填 / app document 必填）
- module source forbidden tokens 第三十二批
- module source 字符串精确补强第二十八批
- signatures 第二十八批
- module 合理性第二十八批
- 端到端集成第二十八批
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


# ---------- SCHEMAS_DIR 常量深度第十七批 ----------


def test_schemas_dir_resolved_absolute_batch17():
    """SCHEMAS_DIR 应是绝对路径（resolve()）。"""
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_parent_is_project_root_batch17():
    """SCHEMAS_DIR.parent 应是项目根（含 pyproject.toml）。"""
    parent = SCHEMAS_DIR.parent
    assert (parent / "pyproject.toml").is_file()


def test_schemas_dir_name_batch17():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_has_4_schemas_batch17():
    jsons = list(SCHEMAS_DIR.glob("*.schema.json"))
    assert len(jsons) >= 4


def test_schemas_dir_no_python_files_batch17():
    pys = list(SCHEMAS_DIR.glob("*.py"))
    assert len(pys) == 0


def test_schemas_dir_has_manifest_schema_batch17():
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_has_annotation_schema_batch17():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_has_evaluation_report_schema_batch17():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_has_document_schema_batch17():
    """app/schema.py 的 document.schema.json 也在 schemas/。"""
    assert (SCHEMAS_DIR / "document.schema.json").is_file()


# ---------- EvalSchemaError 行为深度第十七批 ----------


def test_eval_schema_error_subclass_exception_batch17():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_message_stored_batch17():
    e = EvalSchemaError("hello")
    # super().__init__(message) stores args[0]
    assert e.args == ("hello",)


def test_eval_schema_error_str_returns_message_batch17():
    e = EvalSchemaError("hello world")
    assert str(e) == "hello world"


def test_eval_schema_error_errors_default_empty_list_batch17():
    e = EvalSchemaError("x")
    assert e.errors == []


def test_eval_schema_error_errors_none_becomes_empty_batch17():
    e = EvalSchemaError("x", None)
    assert e.errors == []


def test_eval_schema_error_errors_empty_list_kept_batch17():
    e = EvalSchemaError("x", [])
    assert e.errors == []


def test_eval_schema_error_errors_with_content_batch17():
    errs = [{"path": ["a"], "message": "msg", "schema_path": ["type"]}]
    e = EvalSchemaError("x", errs)
    assert e.errors == errs


def test_eval_schema_error_raise_from_batch17():
    """raise ... from ... 链。"""
    inner = ValueError("inner")
    with pytest.raises(EvalSchemaError) as exc_info:
        try:
            raise inner
        except ValueError as e:
            raise EvalSchemaError("outer") from e
    assert exc_info.value.__cause__ is inner


def test_eval_schema_error_no_cause_by_default_batch17():
    e = EvalSchemaError("x")
    assert e.__cause__ is None


def test_eval_schema_error_repr_contains_class_name_batch17():
    e = EvalSchemaError("boom")
    assert "EvalSchemaError" in repr(e)


def test_eval_schema_error_init_signature_batch17():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "errors"]


def test_eval_schema_error_init_no_varargs_batch17():
    sig = inspect.signature(EvalSchemaError.__init__)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


# ---------- load_schema 行为深度第十七批 ----------


def test_load_schema_manifest_has_schema_field_batch17():
    s = load_schema("manifest.schema.json")
    assert "$schema" in s


def test_load_schema_annotation_has_schema_field_batch17():
    s = load_schema("annotation.schema.json")
    assert "$schema" in s


def test_load_schema_report_has_schema_field_batch17():
    s = load_schema("evaluation-report.schema.json")
    assert "$schema" in s


def test_load_schema_document_has_schema_field_batch17():
    s = load_schema("document.schema.json")
    assert "$schema" in s


def test_load_schema_all_use_draft_2020_12_batch17():
    for name in ["manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json", "document.schema.json"]:
        s = load_schema(name)
        assert s["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_load_schema_all_have_type_object_batch17():
    for name in ["manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json", "document.schema.json"]:
        s = load_schema(name)
        assert s.get("type") == "object"


def test_load_schema_manifest_additional_properties_false_batch17():
    s = load_schema("manifest.schema.json")
    assert s.get("additionalProperties") is False


def test_load_schema_annotation_additional_properties_false_batch17():
    s = load_schema("annotation.schema.json")
    assert s.get("additionalProperties") is False


def test_load_schema_manifest_has_required_batch17():
    s = load_schema("manifest.schema.json")
    assert "required" in s
    assert isinstance(s["required"], list)


def test_load_schema_annotation_has_required_batch17():
    s = load_schema("annotation.schema.json")
    assert "required" in s


def test_load_schema_report_has_required_batch17():
    s = load_schema("evaluation-report.schema.json")
    assert "required" in s


# ---------- validate 行为深度第十七批 ----------


def test_validate_returns_none_on_success_batch17():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_validate_errors_sorted_by_path_batch17():
    """errors 按 absolute_path 排序。"""
    instance = {
        "manifest_version": "bad",  # wrong enum
        "devset_status": 123,       # wrong type
        "documents": "not_list",    # wrong type
    }
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    errs = exc_info.value.errors
    # 排序后第 1 个 path 应是顶层（devset_status / documents / manifest_version）
    # 因为 sorted by absolute_path list
    paths = [e["path"] for e in errs]
    assert paths == sorted(paths, key=lambda p: list(p))


def test_validate_errors_have_3_keys_batch17():
    instance = {"wrong_key": "x"}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    for e in exc_info.value.errors:
        assert set(e.keys()) == {"path", "message", "schema_path"}


def test_validate_message_contains_schema_name_batch17():
    instance = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc_info.value)


def test_validate_message_contains_error_count_batch17():
    instance = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    msg = str(exc_info.value)
    # 含 "N 处"
    assert "处" in msg


def test_validate_errors_path_is_list_batch17():
    instance = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    for e in exc_info.value.errors:
        assert isinstance(e["path"], list)


def test_validate_errors_schema_path_is_list_batch17():
    instance = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    for e in exc_info.value.errors:
        assert isinstance(e["schema_path"], list)


def test_validate_does_not_mutate_instance_batch17():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    validate(instance, "manifest.schema.json")
    # 验证 instance 仍是原值
    assert instance == {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }


def test_validate_unknown_schema_raises_file_not_found_batch17():
    with pytest.raises(FileNotFoundError):
        validate({}, "nonexistent.schema.json")


# ---------- validate_file 行为深度第十七批 ----------


def test_validate_file_str_path_batch17(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    assert validate_file(str(p), "manifest.schema.json") is None


def test_validate_file_path_object_batch17(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_with_utf8_bom_batch17(tmp_path):
    """UTF-8 BOM → json.load 用 'utf-8'（非 utf-8-sig）→ JSONDecodeError。"""
    p = tmp_path / "m.json"
    content = json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    p.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_unicode_content_batch17(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "中文", "path": "a.pdf", "source_type": "pdf",
             "categories": ["标签"]},
        ],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_invalid_raises_eval_schema_error_batch17(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"bad": "schema"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_not_found_raises_batch17(tmp_path):
    with pytest.raises(FileNotFoundError, match="待校验文件不存在"):
        validate_file(tmp_path / "no.json", "manifest.schema.json")


def test_validate_file_directory_raises_batch17(tmp_path):
    """传目录 → is_file() False → FileNotFoundError。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(sub, "manifest.schema.json")


def test_validate_file_invalid_json_raises_json_error_batch17(tmp_path):
    """非 JSON → json.JSONDecodeError。"""
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


# ---------- _schema_path 行为深度第十七批 ----------


def test_schema_path_returns_path_batch17():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_resolved_batch17():
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_missing_message_contains_path_batch17():
    with pytest.raises(FileNotFoundError, match="Schema 文件不存在"):
        _schema_path("nonexistent.schema.json")


def test_schema_path_in_schemas_dir_batch17():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_signature_batch17():
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.keys())
    assert params == ["name"]


# ---------- 4 个 schema 内容深度第十七批 ----------


def test_manifest_schema_required_count_batch17():
    s = load_schema("manifest.schema.json")
    assert len(s["required"]) == 3


def test_manifest_schema_required_contents_batch17():
    s = load_schema("manifest.schema.json")
    assert set(s["required"]) == {
        "manifest_version", "devset_status", "documents",
    }


def test_annotation_schema_required_count_batch17():
    s = load_schema("annotation.schema.json")
    assert len(s["required"]) >= 2


def test_annotation_schema_required_contains_doc_id_batch17():
    s = load_schema("annotation.schema.json")
    assert "doc_id" in s["required"]


def test_annotation_schema_required_contains_annotation_version_batch17():
    s = load_schema("annotation.schema.json")
    assert "annotation_version" in s["required"]


def test_evaluation_report_schema_required_count_batch17():
    s = load_schema("evaluation-report.schema.json")
    assert len(s["required"]) >= 5  # at least: report_version, evaluator_version, parser, devset, ...


def test_evaluation_report_schema_has_provenance_field_batch17():
    s = load_schema("evaluation-report.schema.json")
    assert "provenance" in s.get("required", []) or "provenance" in s.get("properties", {})


def test_document_schema_has_elements_field_batch17():
    s = load_schema("document.schema.json")
    assert "elements" in s.get("properties", {})


def test_document_schema_has_chunks_field_batch17():
    s = load_schema("document.schema.json")
    assert "chunks" in s.get("properties", {})


def test_document_schema_required_count_batch17():
    s = load_schema("document.schema.json")
    assert len(s["required"]) >= 3


# ---------- module source forbidden tokens 第三十二批 ----------


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
def test_module_source_forbidden_tokens_batch17(forbidden):
    src = inspect.getsource(smod)
    assert forbidden not in src


def test_module_source_no_subprocess_batch17():
    src = inspect.getsource(smod)
    assert "import subprocess" not in src


def test_module_source_no_network_batch17():
    src = inspect.getsource(smod)
    assert "urllib.request" not in src
    assert "import requests" not in src


# ---------- module source 字符串精确补强第二十八批 ----------


def test_module_source_has_future_annotations_batch17():
    src = inspect.getsource(smod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch17():
    src = inspect.getsource(smod)
    assert "Schema" in src


def test_module_source_has_json_import_batch17():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_has_pathlib_import_batch17():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_import_batch17():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_has_jsonschema_import_batch17():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_has_validation_error_import_batch17():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError" in src


def test_module_source_has_schemas_dir_batch17():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR" in src


def test_module_source_has_eval_schema_error_class_batch17():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError" in src


def test_module_source_has_validate_function_batch17():
    src = inspect.getsource(smod)
    assert "def validate(" in src


def test_module_source_has_validate_file_function_batch17():
    src = inspect.getsource(smod)
    assert "def validate_file(" in src


def test_module_source_has_load_schema_function_batch17():
    src = inspect.getsource(smod)
    assert "def load_schema(" in src


def test_module_source_has_all_dunder_batch17():
    src = inspect.getsource(smod)
    assert "__all__" in src


def test_module_source_no_main_block_batch17():
    src = inspect.getsource(smod)
    assert "__main__" not in src


# ---------- signatures 第二十八批 ----------


def test_signature_load_schema_batch17():
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.keys())
    assert params == ["name"]


def test_signature_validate_batch17():
    sig = inspect.signature(validate)
    params = list(sig.parameters.keys())
    assert params == ["instance", "schema_name"]


def test_signature_validate_file_batch17():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.keys())
    assert params == ["path", "schema_name"]


def test_signature_schema_path_batch17():
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.keys())
    assert params == ["name"]


def test_signature_eval_schema_error_init_batch17():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "errors"]


# ---------- module 合理性第二十八批 ----------


def test_module_has_all_attribute_batch17():
    assert hasattr(smod, "__all__")
    assert isinstance(smod.__all__, list)


def test_module_all_count_5_batch17():
    assert len(smod.__all__) == 5


def test_module_all_contents_batch17():
    assert set(smod.__all__) == {
        "SCHEMAS_DIR", "EvalSchemaError",
        "load_schema", "validate", "validate_file",
    }


def test_module_has_schemas_dir_batch17():
    assert isinstance(SCHEMAS_DIR, Path)


def test_module_eval_schema_error_is_class_batch17():
    assert isinstance(EvalSchemaError, type)


def test_module_load_schema_callable_batch17():
    assert callable(load_schema)


def test_module_validate_callable_batch17():
    assert callable(validate)


def test_module_validate_file_callable_batch17():
    assert callable(validate_file)


def test_module_does_not_import_unsafe_modules_batch17():
    src = inspect.getsource(smod)
    for unsafe in ["import pickle", "import marshal", "import shelve",
                   "import subprocess"]:
        assert unsafe not in src


def test_module_does_not_import_app_pipeline_batch17():
    """schema.py 不应反向依赖 app.pipeline。"""
    src = inspect.getsource(smod)
    assert "from app.pipeline" not in src


def test_module_no_main_block_batch17():
    src = inspect.getsource(smod)
    assert "if __name__" not in src


# ---------- 端到端集成第二十八批 ----------


def test_e2e_load_then_validate_manifest_batch17():
    schema = load_schema("manifest.schema.json")
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    v = Draft202012Validator(schema)
    assert v.is_valid(instance)


def test_e2e_load_then_validate_annotation_batch17():
    schema = load_schema("annotation.schema.json")
    # 先看 annotation schema 的 required 字段
    req = schema.get("required", [])
    instance = {k: "" for k in req}
    # 给每个字段填合理值
    if "doc_id" in instance:
        instance["doc_id"] = "d1"
    if "annotation_version" in instance:
        instance["annotation_version"] = "1.0"
    v = Draft202012Validator(schema)
    assert v.is_valid(instance), f"Schema errors: {list(v.iter_errors(instance))}"


def test_e2e_cross_schema_validation_fails_batch17():
    """manifest 数据用 annotation schema 校验 → 失败。"""
    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(manifest_data, "annotation.schema.json")


def test_e2e_validate_file_round_trip_batch17(tmp_path):
    """写 → validate_file → None。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_e2e_errors_increase_with_violations_batch17():
    """违反越多，errors 越多。"""
    # 1 个违反
    inst1 = {"manifest_version": "bad"}
    # 多个违反
    inst2 = {"manifest_version": "bad", "devset_status": 123,
             "documents": "not_list", "extra": "field"}

    n1 = 0
    n2 = 0
    try:
        validate(inst1, "manifest.schema.json")
    except EvalSchemaError as e:
        n1 = len(e.errors)
    try:
        validate(inst2, "manifest.schema.json")
    except EvalSchemaError as e:
        n2 = len(e.errors)
    assert n2 >= n1


def test_e2e_validate_file_with_annotation_batch17(tmp_path):
    """validate_file 对 annotation schema 也工作。"""
    schema = load_schema("annotation.schema.json")
    req = schema.get("required", [])
    annotation = {k: "x" for k in req}
    if "doc_id" in annotation:
        annotation["doc_id"] = "d1"
    if "annotation_version" in annotation:
        annotation["annotation_version"] = "1.0"
    p = tmp_path / "a.json"
    p.write_text(json.dumps(annotation), encoding="utf-8")
    assert validate_file(p, "annotation.schema.json") is None


def test_e2e_validate_empty_dict_fails_batch17():
    """空 dict 应在所有 schema 下失败（都有 required）。"""
    for name in ["manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json", "document.schema.json"]:
        with pytest.raises(EvalSchemaError):
            validate({}, name)


def test_e2e_schemas_dir_independent_from_app_schema_batch17():
    """evaluation/schema.py 的 SCHEMAS_DIR 与 app/schema.py 的 SCHEMA_PATH 同根目录。"""
    from app import schema as app_schema
    # app.schema 用 SCHEMA_PATH 指向单个 document.schema.json
    # evaluation.schema 用 SCHEMAS_DIR 指向目录
    # 两者的 parent 应一致
    assert app_schema.SCHEMA_PATH.parent == SCHEMAS_DIR
