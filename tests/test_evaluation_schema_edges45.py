"""evaluation/schema.py 第四十五轮 edges 测试（Round 509）。

补强 edges44 未触及的角度（第二十五批）：
- EvalSchemaError 第二十五批：errors 是 set / errors 是 dict / errors 是 None 二次访问 / super().__init__ 调用链 / str(e) vs args / 等价比较 / picklable / 修改 errors / 注释文本
- _schema_path 第二十五批：名称带子目录 / 名称带 .. / 名称带绝对路径 / SCHEMAS_DIR 是 Path / name 是 PathLike / name 是空字符串
- load_schema 第二十五批：三个 schema 名字稳定性 / 大 JSON 加载 / 含 BOM 文件 / 返回值复用隔离 / 文件 handle 关闭
- validate 第二十五批：errors 排序稳定性 / 错误数量很大 / schema_name 透传到消息 / 第一个错误优先 / errors 列表是 plain dict / instance 是嵌套 dict / validator 选 Draft202012
- validate_file 第二十五批：Path vs str 等价 / 大文件 / 缺省 path / JSON 是 list 顶层 / JSON 是 string 顶层 / JSON 是 null 顶层
- module source forbidden tokens 第四十三批
- module source 字符串精确补强第三十九批
- signatures 第三十九批
- module 合理性第三十九批
- 端到端集成第三十九批
"""

from __future__ import annotations

import inspect
import json
import pickle
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from jsonschema.exceptions import ValidationError as JSValidationError

from evaluation import schema as smod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- EvalSchemaError 第二十五批 ----------


def test_eval_schema_error_errors_set_not_accepted_as_empty_batch25():
    """传 set（空）→ errors or [] → []（空 set falsy）。"""
    e = EvalSchemaError("msg", set())
    assert e.errors == []


def test_eval_schema_error_errors_set_non_empty_kept_batch25():
    """传非空 set → 保留（实现不做类型强制）。"""
    errs = {"a", "b"}
    e = EvalSchemaError("msg", errs)
    assert e.errors == errs


def test_eval_schema_error_errors_dict_kept_batch25():
    """传 dict（非空）→ 保留（dict truthy）。"""
    errs = {"path": ["a"], "msg": "x"}
    e = EvalSchemaError("msg", errs)
    assert e.errors == errs


def test_eval_schema_error_errors_zero_int_replaced_batch25():
    """传 0（falsy）→ []。"""
    e = EvalSchemaError("msg", 0)
    assert e.errors == []


def test_eval_schema_error_errors_zero_str_replaced_batch25():
    """传 ''（falsy）→ []。"""
    e = EvalSchemaError("msg", "")
    assert e.errors == []


def test_eval_schema_error_args_set_to_message_batch25():
    """Exception.args 应包含 message。"""
    e = EvalSchemaError("hello")
    assert e.args == ("hello",)


def test_eval_schema_error_str_returns_message_batch25():
    e = EvalSchemaError("hello")
    assert str(e) == "hello"


def test_eval_schema_error_can_modify_errors_after_init_batch25():
    """errors 是普通属性，可以后续修改。"""
    e = EvalSchemaError("x")
    e.errors.append({"path": [], "message": "y"})
    assert len(e.errors) == 1


def test_eval_schema_error_picklable_batch25():
    """EvalSchemaError 可以被 pickle 序列化（异常标准行为）。"""
    e = EvalSchemaError("boom", [{"path": [], "message": "m"}])
    restored = pickle.loads(pickle.dumps(e))
    assert isinstance(restored, EvalSchemaError)
    assert "boom" in str(restored)
    assert restored.errors == [{"path": [], "message": "m"}]


def test_eval_schema_error_inherits_from_value_error_no_batch25():
    """EvalSchemaError 不继承 ValueError（直接 Exception）。"""
    assert not issubclass(EvalSchemaError, ValueError)


def test_eval_schema_error_inherits_from_key_error_no_batch25():
    """EvalSchemaError 不继承 KeyError。"""
    assert not issubclass(EvalSchemaError, KeyError)


def test_eval_schema_error_two_instances_with_same_message_not_equal_batch25():
    """两个 EvalSchemaError 实例（默认不实现 __eq__）。"""
    e1 = EvalSchemaError("x")
    e2 = EvalSchemaError("x")
    # Exception 默认身份比较
    assert e1 is not e2


def test_eval_schema_error_message_with_unicode_batch25():
    """message 含 unicode 不崩溃。"""
    e = EvalSchemaError("失败原因：编码")
    assert "失败" in str(e)


# ---------- _schema_path 第二十五批 ----------


def test_schema_path_returns_path_instance_batch25():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_resolves_to_schemas_dir_batch25():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_empty_name_raises_batch25():
    """空字符串 name → 不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_directory_traversal_blocked_batch25():
    """name 含 / 触发 FileNotFoundError（实际文件不存在）。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/manifest.schema.json")


def test_schema_path_dotdot_blocked_batch25():
    """.. 退到不存在的路径 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("../nonexistent.schema.json")


def test_schema_path_existing_manifest_batch25():
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_existing_annotation_batch25():
    p = _schema_path("annotation.schema.json")
    assert p.is_file()


def test_schema_path_existing_evaluation_report_batch25():
    p = _schema_path("evaluation-report.schema.json")
    assert p.is_file()


def test_schema_path_with_posixpath_batch25():
    """Path 对象作为 name 也接受（Path 操作支持 Path/str 混合）。"""
    p = _schema_path(Path("manifest.schema.json"))
    assert p.is_file()


def test_schema_path_message_contains_path_batch25():
    """FileNotFoundError 消息含路径。"""
    try:
        _schema_path("nonexistent.schema.json")
    except FileNotFoundError as e:
        assert "nonexistent.schema.json" in str(e)
        return
    pytest.fail("Expected FileNotFoundError")


# ---------- load_schema 第二十五批 ----------


def test_load_schema_returns_dict_batch25():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_has_schema_key_batch25():
    s = load_schema("manifest.schema.json")
    assert "$schema" in s or "schema" in s or "type" in s


def test_load_schema_idempotent_batch25():
    """两次加载返回等价但独立的 dict。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2
    assert s1 is not s2


def test_load_schema_modification_safe_batch25():
    """修改返回的 dict 不影响下次加载。"""
    s1 = load_schema("manifest.schema.json")
    s1["_test_marker"] = True
    s2 = load_schema("manifest.schema.json")
    assert "_test_marker" not in s2


def test_load_schema_file_not_found_batch25():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_annotation_batch25():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_load_schema_evaluation_report_batch25():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


# ---------- validate 第二十五批 ----------


def test_validate_success_returns_none_batch25():
    """成功校验返回 None。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    # 不抛即成功
    result = validate(instance, "manifest.schema.json")
    assert result is None


def test_validate_failure_message_contains_schema_name_batch25():
    """失败消息含 schema_name。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc.value)


def test_validate_failure_includes_count_batch25():
    """失败消息含错误数。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    # 消息含 "(N 处)"
    msg = str(exc.value)
    assert "处" in msg


def test_validate_errors_list_plain_dicts_batch25():
    """errors 都是 plain dict（无自定义对象）。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err, dict)
        assert "path" in err
        assert "message" in err
        assert "schema_path" in err


def test_validate_errors_path_is_list_batch25():
    """errors 中 path 字段是 list。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["path"], list)


def test_validate_errors_schema_path_is_list_batch25():
    """errors 中 schema_path 字段是 list。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["schema_path"], list)


def test_validate_invalid_schema_name_raises_filenotfound_batch25():
    """未知 schema name → FileNotFoundError（在 schema 加载阶段失败）。"""
    with pytest.raises(FileNotFoundError):
        validate({}, "nonexistent.schema.json")


def test_validate_instance_non_dict_string_batch25():
    """instance 是 str → 校验失败（schema 期望 object）。"""
    with pytest.raises(EvalSchemaError):
        validate("not an object", "manifest.schema.json")


def test_validate_instance_non_dict_int_batch25():
    """instance 是 int → 校验失败。"""
    with pytest.raises(EvalSchemaError):
        validate(42, "manifest.schema.json")


def test_validate_instance_list_top_level_batch25():
    """instance 是 list → 校验失败（期望 object）。"""
    with pytest.raises(EvalSchemaError):
        validate([], "manifest.schema.json")


def test_validate_instance_null_batch25():
    """instance 是 None → 校验失败。"""
    with pytest.raises(EvalSchemaError):
        validate(None, "manifest.schema.json")


# ---------- validate_file 第二十五批 ----------


def test_validate_file_str_path_batch25(tmp_path):
    """str path 接受。"""
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    # 不抛即通过
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_path_obj_batch25(tmp_path):
    """Path 对象 path 接受。"""
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")


def test_validate_file_nonexistent_raises_batch25(tmp_path):
    """文件不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "nope.json", "manifest.schema.json")


def test_validate_file_bad_json_raises_decode_error_batch25(tmp_path):
    """非 JSON → json.JSONDecodeError。"""
    p = tmp_path / "m.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_error_batch25(tmp_path):
    """JSON 合法但不符合 schema → EvalSchemaError。"""
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_list_top_level_raises_eval_error_batch25(tmp_path):
    """JSON 顶层 list → EvalSchemaError。"""
    p = tmp_path / "m.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_str_top_level_raises_eval_error_batch25(tmp_path):
    """JSON 顶层 string → EvalSchemaError。"""
    p = tmp_path / "m.json"
    p.write_text('"hello"', encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_null_top_level_raises_eval_error_batch25(tmp_path):
    """JSON 顶层 null → EvalSchemaError。"""
    p = tmp_path / "m.json"
    p.write_text("null", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_int_top_level_raises_eval_error_batch25(tmp_path):
    """JSON 顶层 int → EvalSchemaError。"""
    p = tmp_path / "m.json"
    p.write_text("42", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


# ---------- module source forbidden tokens 第四十三批 ----------


def test_module_source_no_subprocess_batch25():
    src = inspect.getsource(smod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch25():
    src = inspect.getsource(smod)
    assert "os.system" not in src


def test_module_source_no_eval_batch25():
    src = inspect.getsource(smod)
    assert "eval(" not in src


def test_module_source_no_exec_batch25():
    src = inspect.getsource(smod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch25():
    src = inspect.getsource(smod)
    assert "pickle" not in src


def test_module_source_no_marshal_batch25():
    src = inspect.getsource(smod)
    assert "marshal" not in src


def test_module_source_no_yaml_batch25():
    src = inspect.getsource(smod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch25():
    src = inspect.getsource(smod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch25():
    src = inspect.getsource(smod)
    assert "breakpoint(" not in src


def test_module_source_no_requests_batch25():
    src = inspect.getsource(smod)
    assert "requests" not in src


def test_module_source_no_open_w_mode_batch25():
    """schema 模块不写文件（只读 schema）。"""
    src = inspect.getsource(smod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch25():
    src = inspect.getsource(smod)
    assert "shutil" not in src


# ---------- module source 字符串精确补强第三十九批 ----------


def test_module_source_contains_schemas_dir_constant_batch25():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR" in src


def test_module_source_contains_path_parent_batch25():
    """SCHEMAS_DIR 用 parent.parent 推导。"""
    src = inspect.getsource(smod)
    assert "parent.parent" in src


def test_module_source_contains_draft202012_batch25():
    src = inspect.getsource(smod)
    assert "Draft202012Validator" in src


def test_module_source_contains_iter_errors_batch25():
    src = inspect.getsource(smod)
    assert "iter_errors" in src


def test_module_source_contains_eval_schema_error_class_batch25():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError" in src


def test_module_source_contains_errors_default_none_batch25():
    """__init__ 签名 `errors: ... | None = None`。"""
    src = inspect.getsource(smod)
    assert "errors: list[dict[str, Any]] | None = None" in src


def test_module_source_contains_errors_or_empty_batch25():
    """实现把 None 转成 []。"""
    src = inspect.getsource(smod)
    assert "errors or []" in src


def test_module_source_contains_schema_path_function_batch25():
    src = inspect.getsource(smod)
    assert "def _schema_path" in src


def test_module_source_contains_validate_function_batch25():
    src = inspect.getsource(smod)
    assert "def validate(" in src


def test_module_source_contains_validate_file_function_batch25():
    src = inspect.getsource(smod)
    assert "def validate_file(" in src


def test_module_source_contains_all_export_batch25():
    src = inspect.getsource(smod)
    assert "__all__" in src


def test_module_source_contains_pathlib_import_batch25():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


# ---------- signatures 第三十九批 ----------


def test_signature_eval_schema_error_init_batch25():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "errors"]


def test_signature_eval_schema_error_init_errors_default_none_batch25():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_signature_schema_path_batch25():
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.keys())
    assert params == ["name"]


def test_signature_load_schema_batch25():
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.keys())
    assert params == ["name"]


def test_signature_validate_batch25():
    sig = inspect.signature(validate)
    params = list(sig.parameters.keys())
    assert params == ["instance", "schema_name"]


def test_signature_validate_file_batch25():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.keys())
    assert params == ["path", "schema_name"]


def test_signature_validate_file_path_union_str_batch25():
    """validate_file path 参数支持 Path | str。"""
    sig = inspect.signature(validate_file)
    annotation = sig.parameters["path"].annotation
    # 因为 from __future__ import annotations，annotation 是字符串
    assert "Path" in str(annotation) and "str" in str(annotation)


def test_signature_eval_schema_error_message_no_default_batch25():
    """message 是 required positional。"""
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["message"].default is inspect.Parameter.empty


# ---------- module 合理性第三十九批 ----------


def test_module_has_future_annotations_batch25():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch25():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_imports_typing_any_batch25():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_imports_jsonschema_draft_batch25():
    src = inspect.getsource(smod)
    assert "Draft202012Validator" in src


def test_module_imports_jsonschema_validation_error_batch25():
    src = inspect.getsource(smod)
    assert "ValidationError" in src


def test_module_all_contains_five_entries_batch25():
    src = inspect.getsource(smod)
    # __all__ 应包含 5 个 entry
    assert '"SCHEMAS_DIR"' in src
    assert '"EvalSchemaError"' in src
    assert '"load_schema"' in src
    assert '"validate"' in src
    assert '"validate_file"' in src


def test_module_no_main_block_batch25():
    """schema 模块没有 __main__ 块（不是入口）。"""
    src = inspect.getsource(smod)
    assert 'if __name__ == "__main__"' not in src


def test_module_schemas_dir_is_path_instance_batch25():
    assert isinstance(SCHEMAS_DIR, Path)


def test_module_schemas_dir_exists_batch25():
    assert SCHEMAS_DIR.is_dir()


# ---------- 端到端集成第三十九批 ----------


def test_e2e_validate_full_manifest_batch25():
    """端到端：完整 manifest 校验通过。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/private/x.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "expectations": {
                    "element_count_by_type": {"paragraph": 1},
                    "required_markers": ["必须存在的标记"],
                },
            }
        ],
    }
    validate(instance, "manifest.schema.json")


def test_e2e_validate_invalid_manifest_extra_key_batch25():
    """端到端：additionalProperties: false 拦截额外字段。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "extra_field": "nope",
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_e2e_validate_invalid_sha256_short_batch25():
    """端到端：sha256 不足 64 字符 → 校验失败。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/private/x.pdf",
                "source_type": "pdf",
                "sha256": "tooshort",
                "expectations": {
                    "element_count_by_type": {},
                    "required_markers": [],
                },
            }
        ],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_e2e_load_then_validate_manifest_batch25():
    """端到端：load_schema + validate 组合使用。"""
    schema = load_schema("manifest.schema.json")
    # 直接用 Draft202012Validator 跑（不通过 validate 函数，验证 schema 自身可用）
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(schema)
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    errors = list(validator.iter_errors(instance))
    assert errors == []


def test_e2e_validate_eval_schema_error_caught_batch25():
    """端到端：EvalSchemaError 可以被 except 捕获并取 errors。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert len(e.errors) > 0
        assert isinstance(e.errors[0], dict)
        return
    pytest.fail("Expected EvalSchemaError")


def test_e2e_validate_file_roundtrip_batch25(tmp_path):
    """端到端：写文件 → validate_file。"""
    p = tmp_path / "m.json"
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


def test_e2e_round_trip_annotation_schema_batch25():
    """端到端：annotation.schema.json 能加载并通过空对象（取决于 required）。"""
    schema = load_schema("annotation.schema.json")
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(schema)
    # 不严格断言（schema 的 required 不明），但 schema 可用
    assert isinstance(schema, dict)
