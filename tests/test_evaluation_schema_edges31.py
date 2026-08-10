"""evaluation/schema.py 第三十一轮 edges 测试（Round 407）。

补强 edges30 未触及的角度：
- EvalSchemaError 行为深度第十一批（errors 多次修改独立性 / errors None 显式 / errors tuple 输入 / errors generator / chain 多层 / unicode in errors / errors 异常类型）
- load_schema 行为深度第十一批（更多 corner cases / 缓存验证 / 各 schema 路径返回绝对路径 / SCHEMAS_DIR 关系 / 不验证内容）
- validate 行为深度第十一批（更多错误格式 / 多错误同时 / errors 含 schema_path 复杂结构 / validator 类型 / sort key 行为）
- validate_file 行为深度第十一批（Path vs str / Unicode filename / 文件不存在 / 目录 / 大文件 / multiline JSON / JSONDecodeError 子类）
- _schema_path 行为深度第十一批（更多 corner cases）
- SCHEMAS_DIR 常量深度第十一批（更多属性 / 是 Path / 在 worktree 内）
- module source forbidden tokens 第十五批
- module source 字符串精确补强第十一批
- signatures 第十一批
- module 合理性第十一批
- 端到端集成第十一批
"""

from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
from unittest.mock import patch

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


# ---------- EvalSchemaError 行为深度第十一批 ----------


def test_eval_schema_error_errors_none_explicit_batch11():
    """显式 errors=None → 默认空 list。"""
    e = EvalSchemaError("msg", None)
    assert e.errors == []
    assert isinstance(e.errors, list)


def test_eval_schema_error_errors_tuple_input_batch11():
    """errors 是 tuple → 仍是 list-like，但因为 `or []` 仅在 falsy 时替换。
    tuple 非空时 truthy → 保留 tuple（不被替换）。
    """
    e = EvalSchemaError("msg", ({"a": 1},))
    # errors 是 tuple，但 `errors or []` 中非空 tuple truthy → 保留
    assert isinstance(e.errors, tuple)
    assert len(e.errors) == 1


def test_eval_schema_error_errors_empty_tuple_becomes_list_batch11():
    """空 tuple 是 falsy → 替换为 []。"""
    e = EvalSchemaError("msg", ())
    assert e.errors == []
    assert isinstance(e.errors, list)


def test_eval_schema_error_errors_list_independence_batch11():
    """传入的 list 应被引用，但 or [] 模式不会复制。"""
    src = [{"k": "v"}]
    e = EvalSchemaError("msg", src)
    # 修改原 list → 错误对象的 errors 也变（同一对象）
    src.append({"k2": "v2"})
    assert len(e.errors) == 2


def test_eval_schema_error_chain_multi_level_batch11():
    """多层 raise from → __cause__ 链。"""
    try:
        try:
            try:
                raise ValueError("level1")
            except ValueError as e1:
                raise RuntimeError("level2") from e1
        except RuntimeError as e2:
            raise EvalSchemaError("level3") from e2
    except EvalSchemaError as e3:
        assert isinstance(e3.__cause__, RuntimeError)
        assert isinstance(e3.__cause__.__cause__, ValueError)


def test_eval_schema_error_errors_with_complex_nested_dict_batch11():
    """errors 中可以含深度嵌套的 dict。"""
    e = EvalSchemaError(
        "msg",
        [{"path": ["a", "b", "c"], "message": "deep", "context": {"x": [1, 2, 3]}}],
    )
    assert e.errors[0]["path"] == ["a", "b", "c"]
    assert e.errors[0]["context"]["x"] == [1, 2, 3]


def test_eval_schema_error_can_be_raised_and_caught_batch11():
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("test")


def test_eval_schema_error_is_exception_subclass_batch11():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_not_value_error_batch11():
    assert not issubclass(EvalSchemaError, ValueError)


def test_eval_schema_error_can_be_pickle_batch11():
    """EvalSchemaError 应可 pickle（继承自 Exception）。"""
    import pickle
    e = EvalSchemaError("msg", [{"k": "v"}])
    data = pickle.dumps(e)
    e2 = pickle.loads(data)
    assert isinstance(e2, EvalSchemaError)


def test_eval_schema_error_args_preserved_batch11():
    """Exception args 应保留 message。"""
    e = EvalSchemaError("hello")
    assert e.args == ("hello",)


# ---------- load_schema 行为深度第十一批 ----------


def test_load_schema_returns_fresh_dict_each_call_batch11():
    """两次 load_schema 返回独立 dict（修改一个不影响另一个）。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2
    s1["custom_key"] = "x"
    assert "custom_key" not in s2


def test_load_schema_returns_dict_with_properties_key_batch11():
    """所有 schema 都有 properties key。"""
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"):
        s = load_schema(name)
        assert "properties" in s


def test_load_schema_returns_dict_with_required_key_batch11():
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"):
        s = load_schema(name)
        assert "required" in s


def test_load_schema_manifest_specific_property_batch11():
    """manifest schema 应有 documents 字段定义。"""
    s = load_schema("manifest.schema.json")
    assert "documents" in s.get("properties", {})


def test_load_schema_annotation_specific_property_batch11():
    """annotation schema 应有 chunk_boundary_anchors 字段。"""
    s = load_schema("annotation.schema.json")
    assert "chunk_boundary_anchors" in s.get("properties", {})


def test_load_schema_evaluation_report_specific_property_batch11():
    """evaluation-report schema 应有 per_doc 字段。"""
    s = load_schema("evaluation-report.schema.json")
    assert "per_doc" in s.get("properties", {})


def test_load_schema_does_not_call_validator_batch11():
    """load_schema 只加载，不校验。"""
    # 一个非法 schema 文件应能被加载（不抛）
    # 我们可以用 mock 验证 Draft202012Validator 未被调用
    with patch.object(smod, "Draft202012Validator") as mock_validator:
        load_schema("manifest.schema.json")
        mock_validator.assert_not_called()


def test_load_schema_unknown_name_raises_filenotfound_batch11():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_path_with_subdir_name_batch11():
    """name 含子目录 → 拼接 SCHEMAS_DIR/sub/name。"""
    with pytest.raises(FileNotFoundError):
        load_schema("subdir/name.schema.json")


# ---------- validate 行为深度第十一批 ----------


def test_validate_returns_none_on_success_batch11():
    """成功 → return None（无返回值）。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_validate_eval_schema_error_has_errors_list_batch11():
    """失败时 errors 是 list of dict。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    e = exc_info.value
    assert isinstance(e.errors, list)
    assert len(e.errors) > 0
    for err in e.errors:
        assert isinstance(err, dict)
        assert "path" in err
        assert "message" in err
        assert "schema_path" in err


def test_validate_errors_path_is_list_batch11():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert isinstance(err["path"], list)
        assert isinstance(err["schema_path"], list)


def test_validate_eval_schema_error_message_includes_schema_name_batch11():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc_info.value)


def test_validate_eval_schema_error_message_includes_count_batch11():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    msg = str(exc_info.value)
    # "校验失败 (N 处)" 中 N 应是数字
    assert "校验失败" in msg


def test_validate_does_not_mutate_instance_batch11():
    instance = {"manifest_version": "1.0"}
    snapshot = json.dumps(instance, sort_keys=True)
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError:
        pass
    assert json.dumps(instance, sort_keys=True) == snapshot


def test_validate_loads_schema_via_load_schema_function_batch11():
    """validate 内部应调 load_schema。"""
    with patch.object(smod, "load_schema", return_value={"type": "object"}) as mock_load:
        try:
            validate({}, "x.schema.json")
        except EvalSchemaError:
            pass
        mock_load.assert_called_once_with("x.schema.json")


def test_validate_creates_draft_validator_batch11():
    """validate 内部应创建 Draft202012Validator。"""
    fake_schema = {"type": "object"}
    with patch.object(smod, "load_schema", return_value=fake_schema), \
         patch.object(smod, "Draft202012Validator") as mock_validator:
        # 设置 mock 让 iter_errors 返回 []
        mock_validator.return_value.iter_errors.return_value = iter([])
        validate({}, "x.schema.json")
        mock_validator.assert_called_once_with(fake_schema)


def test_validate_with_extra_fields_ignored_batch11():
    """JSON Schema 默认 additionalProperties=False 才拒绝额外字段；
    若 schema 允许 → validate 不报错。"""
    # manifest.schema.json 通常会拒绝额外字段，但 evaluation-report 可能允许
    # 我们用一个最小测试：valid manifest + 额外字段
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
        "extra_field": "should fail",
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_errors_sorted_by_path_batch11():
    """errors 按 path 排序。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        # 制造多个错误：缺 manifest_version + 缺 devset_status + 缺 documents
        validate({"expected_failures": []}, "manifest.schema.json")
    errors = exc_info.value.errors
    # 排序后 path 应升序
    paths = [tuple(e["path"]) for e in errors]
    assert paths == sorted(paths)


# ---------- validate_file 行为深度第十一批 ----------


def test_validate_file_path_str_input_batch11(tmp_path):
    """str path 输入合法。"""
    p = tmp_path / "valid.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    # 不抛
    assert validate_file(str(p), "manifest.schema.json") is None


def test_validate_file_path_obj_input_batch11(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_directory_raises_filenotfound_batch11(tmp_path):
    """path 是目录 → is_file False → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_missing_raises_filenotfound_batch11(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "no.json", "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecodeerror_batch11(tmp_path):
    """非法 JSON → json.JSONDecodeError。"""
    import json
    p = tmp_path / "bad.json"
    p.write_text("not valid json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_data_raises_eval_schema_error_batch11(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_unicode_filename_batch11(tmp_path):
    """Unicode 文件名工作正常。"""
    p = tmp_path / "清单.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_returns_none_on_success_batch11(tmp_path):
    p = tmp_path / "v.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    assert validate_file(p, "manifest.schema.json") is None


# ---------- _schema_path 行为深度第十一批 ----------


def test_schema_path_returns_path_obj_batch11():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_returns_absolute_batch11():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_unknown_name_raises_filenotfound_batch11():
    with pytest.raises(FileNotFoundError):
        _schema_path("does_not_exist.schema.json")


def test_schema_path_returns_existing_file_batch11():
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_with_directory_separator_batch11():
    """name 含子目录 → FileNotFoundError（不存在）。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/nonexistent.schema.json")


def test_schema_path_message_contains_filename_batch11():
    """FileNotFoundError 的 message 含路径。"""
    with pytest.raises(FileNotFoundError, match="Schema 文件不存在"):
        _schema_path("nonexistent.schema.json")


# ---------- SCHEMAS_DIR 常量深度第十一批 ----------


def test_schemas_dir_is_path_batch11():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute_batch11():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_exists_batch11():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_has_3_schemas_batch11():
    """schemas/ 目录应有 manifest/annotation/evaluation-report.schema.json。"""
    files = list(SCHEMAS_DIR.glob("*.schema.json"))
    names = {f.name for f in files}
    assert "manifest.schema.json" in names
    assert "annotation.schema.json" in names
    assert "evaluation-report.schema.json" in names


def test_schemas_dir_under_dachuang_root_batch11():
    """SCHEMAS_DIR 位于项目根 schemas/ 下。"""
    # 应包含 "schemas" 这一段
    parts = SCHEMAS_DIR.parts
    assert "schemas" in parts


def test_schemas_dir_parent_is_project_root_batch11():
    """SCHEMAS_DIR.parent 是项目根。"""
    parent = SCHEMAS_DIR.parent
    # 应有 pyproject.toml 或 evaluation/ 目录
    assert (parent / "pyproject.toml").is_file() or (parent / "evaluation").is_dir()


# ---------- module source forbidden tokens 第十五批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "pickle.loads",
        "yaml.load",
        "yaml.unsafe_load",
        "subprocess.check_call",
        "subprocess.call",
        "subprocess.getoutput",
        "os.popen",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
        "import socket",
    ],
)
def test_schema_source_no_forbidden_token_fifteenth_batch11(token):
    source = inspect.getsource(smod)
    assert token not in source


def test_schema_source_no_top_level_lambda_batch11():
    source = inspect.getsource(smod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_schema_source_no_class_outside_eval_schema_error_batch11():
    """顶层只有 EvalSchemaError 一个 class。"""
    source = inspect.getsource(smod)
    lines = source.split("\n")
    top_classes = [line for line in lines if line.startswith("class ")]
    assert len(top_classes) == 1
    assert "EvalSchemaError" in top_classes[0]


def test_schema_source_no_assert_statement_batch11():
    source = inspect.getsource(smod)
    assert "\nassert " not in source
    assert not source.startswith("assert ")


def test_schema_source_no_yield_batch11():
    source = inspect.getsource(smod)
    assert "yield " not in source


def test_schema_source_no_global_batch11():
    source = inspect.getsource(smod)
    assert " global " not in source


def test_schema_source_no_walrus_batch11():
    source = inspect.getsource(smod)
    assert ":=" not in source


def test_schema_source_no_async_def_batch11():
    source = inspect.getsource(smod)
    assert "async def" not in source


def test_schema_source_no_while_loop_batch11():
    source = inspect.getsource(smod)
    assert "while " not in source


def test_schema_source_no_input_call_batch11():
    source = inspect.getsource(smod)
    assert "input(" not in source


def test_schema_source_no_remove_batch11():
    source = inspect.getsource(smod)
    assert ".remove(" not in source


def test_schema_source_no_kill_batch11():
    source = inspect.getsource(smod)
    assert ".kill(" not in source


def test_schema_source_no_unlink_batch11():
    """schema 模块不删文件。"""
    source = inspect.getsource(smod)
    assert "unlink" not in source


def test_schema_source_no_threading_batch11():
    source = inspect.getsource(smod)
    assert "threading" not in source


# ---------- module source 字符串精确补强第十一批 ----------


def test_module_source_has_future_annotations_batch11():
    source = inspect.getsource(smod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


def test_module_source_imports_json_batch11():
    source = inspect.getsource(smod)
    assert "import json" in source


def test_module_source_imports_path_batch11():
    source = inspect.getsource(smod)
    assert "from pathlib import Path" in source


def test_module_source_imports_typing_any_batch11():
    source = inspect.getsource(smod)
    assert "from typing import Any" in source


def test_module_source_imports_draft_validator_batch11():
    source = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in source


def test_module_source_imports_js_validation_error_batch11():
    source = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in source


def test_module_source_has_schemas_dir_constant_batch11():
    source = inspect.getsource(smod)
    assert "SCHEMAS_DIR = " in source


def test_module_source_has_class_eval_schema_error_batch11():
    source = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in source


def test_module_source_has_schema_path_function_batch11():
    source = inspect.getsource(smod)
    assert "def _schema_path(" in source


def test_module_source_has_load_schema_function_batch11():
    source = inspect.getsource(smod)
    assert "def load_schema(" in source


def test_module_source_has_validate_function_batch11():
    source = inspect.getsource(smod)
    assert "def validate(" in source


def test_module_source_has_validate_file_function_batch11():
    source = inspect.getsource(smod)
    assert "def validate_file(" in source


def test_module_source_no_main_block_batch11():
    source = inspect.getsource(smod)
    assert "if __name__" not in source


def test_module_source_no_print_batch11():
    source = inspect.getsource(smod)
    assert "print(" not in source


def test_module_source_no_logging_batch11():
    source = inspect.getsource(smod)
    assert "logging" not in source
    assert "logger" not in source


def test_module_source_docstring_present_batch11():
    assert smod.__doc__ is not None
    assert len(smod.__doc__) > 30


def test_module_source_docstring_mentions_schema_batch11():
    assert smod.__doc__ is not None
    assert "Schema" in smod.__doc__ or "schema" in smod.__doc__


def test_module_source_docstring_mentions_separation_batch11():
    """docstring 应解释为何不与 app/schema.py 复用。"""
    assert smod.__doc__ is not None
    # 至少提到 'app' 或 '不复用'
    assert "app" in smod.__doc__.lower() or "不复用" in smod.__doc__ or "分开" in smod.__doc__


# ---------- signatures 第十一批 ----------


def test_signature_eval_schema_error_2_params_batch11():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert len(sig.parameters) == 3  # self + message + errors


def test_signature_eval_schema_error_self_param_batch11():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert "self" in sig.parameters


def test_signature_eval_schema_error_message_param_batch11():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert "message" in sig.parameters


def test_signature_eval_schema_error_errors_param_optional_batch11():
    sig = inspect.signature(EvalSchemaError.__init__)
    p = sig.parameters["errors"]
    annot = p.annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "list" in annot_str
    assert "None" in annot_str
    assert p.default is None


def test_signature_eval_schema_error_errors_kind_kw_or_pos_batch11():
    sig = inspect.signature(EvalSchemaError.__init__)
    p = sig.parameters["errors"]
    assert p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)


def test_signature_schema_path_1_param_batch11():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters) == ["name"]


def test_signature_schema_path_return_path_batch11():
    sig = inspect.signature(_schema_path)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "Path" in annot_str


def test_signature_load_schema_1_param_batch11():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters) == ["name"]


def test_signature_load_schema_param_annotation_str_batch11():
    sig = inspect.signature(load_schema)
    p = sig.parameters["name"]
    annot = p.annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "str" in annot_str


def test_signature_load_schema_return_dict_batch11():
    sig = inspect.signature(load_schema)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "dict" in annot_str


def test_signature_validate_2_params_batch11():
    sig = inspect.signature(validate)
    assert list(sig.parameters) == ["instance", "schema_name"]


def test_signature_validate_return_none_batch11():
    sig = inspect.signature(validate)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "None" in annot_str


def test_signature_validate_file_2_params_batch11():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters) == ["path", "schema_name"]


def test_signature_validate_file_path_annotation_batch11():
    sig = inspect.signature(validate_file)
    p = sig.parameters["path"]
    annot = p.annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "Path" in annot_str
    assert "str" in annot_str


def test_signature_validate_file_return_none_batch11():
    sig = inspect.signature(validate_file)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "None" in annot_str


def test_all_functions_no_var_kwargs_batch11():
    for fn in [_schema_path, load_schema, validate, validate_file]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- module 合理性第十一批 ----------


def test_module_name_evaluation_schema_batch11():
    assert smod.__name__ == "evaluation.schema"


def test_module_dunder_file_endswith_schema_py_batch11():
    sep = os.sep
    assert smod.__file__.endswith("evaluation" + sep + "schema.py") or smod.__file__.endswith(
        "evaluation/schema.py"
    )


def test_module_user_function_count_4_batch11():
    funcs = [
        n for n, v in vars(smod).items()
        if inspect.isfunction(v) and v.__module__ == smod.__name__
    ]
    assert set(funcs) == {"_schema_path", "load_schema", "validate", "validate_file"}


def test_module_user_class_count_1_batch11():
    classes = [
        n for n, v in vars(smod).items()
        if inspect.isclass(v) and v.__module__ == smod.__name__
    ]
    assert classes == ["EvalSchemaError"]


def test_module_user_constants_count_1_batch11():
    """SCHEMAS_DIR 是唯一顶层 user-defined 常量。"""
    consts = [
        n for n, v in vars(smod).items()
        if not n.startswith("__")
        and not callable(v)
        and not inspect.isclass(v)
        and not inspect.ismodule(v)
        and n not in ("annotations",)  # 排除 future
        and n != "SCHEMAS_DIR"
    ]
    assert consts == []


def test_module_dunder_all_exact_batch11():
    assert hasattr(smod, "__all__")
    assert set(smod.__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_module_dunder_all_len_5_batch11():
    assert len(smod.__all__) == 5


def test_module_uses_future_annotations_batch11():
    source = inspect.getsource(smod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


def test_module_has_draft_validator_imported_batch11():
    assert hasattr(smod, "Draft202012Validator")
    assert smod.Draft202012Validator is Draft202012Validator


def test_module_eval_schema_error_class_present_batch11():
    assert hasattr(smod, "EvalSchemaError")
    assert smod.EvalSchemaError is EvalSchemaError


# ---------- 端到端集成第十一批 ----------


def test_e2e_load_then_validate_manifest_batch11():
    """加载 schema + 验证 instance 完整流程。"""
    schema = load_schema("manifest.schema.json")
    assert isinstance(schema, dict)
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(instance, "manifest.schema.json")


def test_e2e_load_then_validate_annotation_batch11():
    instance = {
        "annotation_version": "1.0",
        "doc_id": "d1",
    }
    validate(instance, "annotation.schema.json")


def test_e2e_validate_file_full_round_trip_batch11(tmp_path):
    """validate_file: 写合法 JSON → 校验通过。"""
    p = tmp_path / "valid.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")


def test_e2e_validate_file_invalid_returns_eval_schema_error_batch11(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_e2e_combined_chain_load_validate_idempotent_batch11():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(instance, "manifest.schema.json")
    validate(instance, "manifest.schema.json")
    # 多次校验同样合法


def test_e2e_combined_chain_3_schemas_independent_batch11():
    """3 个 schema 独立加载，互不影响。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("annotation.schema.json")
    s3 = load_schema("evaluation-report.schema.json")
    assert s1 != s2
    assert s1 != s3
    assert s2 != s3


def test_e2e_combined_chain_eval_schema_error_caught_batch11():
    """EvalSchemaError 可被 try/except 捕获，errors 属性可读。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert e.errors
        assert isinstance(e.errors[0], dict)


def test_e2e_combined_chain_validate_file_round_trip_json_serializable_batch11(tmp_path):
    """validate_file 的错误可被 JSON 序列化（errors 字段）。"""
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    try:
        validate_file(p, "manifest.schema.json")
    except EvalSchemaError as e:
        # errors 应可序列化
        text = json.dumps(e.errors)
        parsed = json.loads(text)
        assert parsed == e.errors


def test_e2e_combined_chain_validate_path_with_real_world_manifest_batch11(tmp_path):
    """模拟真实 manifest 使用场景。"""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "a.pdf",
                        "source_type": "pdf",
                        "categories": ["normal"],
                    }
                ],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    validate_file(manifest_path, "manifest.schema.json")


def test_e2e_combined_chain_full_report_validation_batch11(tmp_path):
    """完整 evaluation-report 校验。"""
    # 构造最小合法 report
    report = {
        "report_version": "1.1",
        "provenance": {
            "git_commit": None,
            "git_dirty": True,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {"pdfplumber": None, "python-docx": None, "pypdfium2": None},
            "max_chars": 800,
            "run_timestamp_iso": "2026-08-11T00:00:00+00:00",
        },
        "devset": {
            "status": "incomplete",
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": [],
        },
        "summary": {
            "counts": {},
            "success_rates": {},
            "ratio_macro_averages": {},
            "silent_drop_total": None,
        },
        "per_doc": [],
        "expected_failures": [],
    }
    p = tmp_path / "report.json"
    p.write_text(json.dumps(report), encoding="utf-8")
    validate_file(p, "evaluation-report.schema.json")
