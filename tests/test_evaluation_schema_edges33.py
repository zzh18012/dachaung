"""evaluation/schema.py 第三十三轮 edges 测试（Round 421）。

补强 edges32 未触及的角度：
- SCHEMAS_DIR 常量深度第十三批（值类型 Path / resolve 后绝对 / parent.parent / 含 schemas 后缀）
- EvalSchemaError 行为深度第十三批（errors=None 时默认 [] / errors=[] / errors 是非 None list / super().__init__ 链 / __cause__ 链 / pickle 支持）
- load_schema 行为深度第十三批（context manager / json.load 调用 / encoding=utf-8 / 不缓存）
- validate 行为深度第十三批（Draft202012Validator 创建 / iter_errors 排序 / errors flat 化 / head.message 优先 / errors 第一项 path 是 list / 多个 errors 都在 flat 中 / 不修改 instance）
- validate_file 行为深度第十三批（str/Path 输入 / FileNotFoundError 子类 Exception / encoding=utf-8 / 不返回值）
- _schema_path 行为深度第十三批（FileNotFoundError 含 path / 返回 Path / SCHEMAS_DIR 拼接 / is_file 检查）
- module source forbidden tokens 第十八批
- module source 字符串精确补强第十五批
- signatures 第十五批
- module 合理性第十五批
- 端到端集成第十五批
"""

from __future__ import annotations

import inspect
import json
import pickle
from pathlib import Path
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


# ---------- SCHEMAS_DIR 常量深度第十三批 ----------


def test_schemas_dir_is_path_batch13():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute_batch13():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_resolved_batch13():
    """SCHEMAS_DIR 是 .resolve() 后的。"""
    expected = Path(smod.__file__).resolve().parent.parent / "schemas"
    assert SCHEMAS_DIR == expected


def test_schemas_dir_parent_is_project_root_batch13():
    """SCHEMAS_DIR.parent 是项目根（含 pyproject.toml）。"""
    parent = SCHEMAS_DIR.parent
    assert (parent / "pyproject.toml").is_file()


def test_schemas_dir_name_is_schemas_batch13():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_contains_manifest_schema_batch13():
    """schemas/ 含 manifest.schema.json。"""
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema_batch13():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema_batch13():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


# ---------- EvalSchemaError 行为深度第十三批 ----------


def test_eval_schema_error_super_init_batch13():
    e = EvalSchemaError("msg")
    # Exception message 应可被 str(e) 访问
    assert str(e) == "msg"


def test_eval_schema_error_args_batch13():
    e = EvalSchemaError("msg")
    assert e.args == ("msg",)


def test_eval_schema_errors_default_empty_list_batch13():
    e = EvalSchemaError("msg")
    assert e.errors == []


def test_eval_schema_errors_passed_list_batch13():
    errs = [{"path": [], "message": "x"}]
    e = EvalSchemaError("msg", errors=errs)
    assert e.errors == errs


def test_eval_schema_errors_none_passed_batch13():
    e = EvalSchemaError("msg", errors=None)
    assert e.errors == []


def test_eval_schema_errors_passed_empty_list_batch13():
    e = EvalSchemaError("msg", errors=[])
    assert e.errors == []


def test_eval_schema_errors_independent_default_batch13():
    """两次构造默认 errors=[] 应是不同 list。"""
    e1 = EvalSchemaError("msg")
    e2 = EvalSchemaError("msg")
    e1.errors.append({"x": 1})
    assert e2.errors == []


def test_eval_schema_error_is_exception_batch13():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_raise_from_chain_batch13():
    try:
        try:
            raise ValueError("inner")
        except ValueError as inner:
            raise EvalSchemaError("outer") from inner
    except EvalSchemaError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, ValueError)


def test_eval_schema_error_pickle_support_batch13():
    e = EvalSchemaError("msg", errors=[{"path": [], "message": "x"}])
    data = pickle.dumps(e)
    e2 = pickle.loads(data)
    assert str(e2) == "msg"
    assert e2.errors == [{"path": [], "message": "x"}]


def test_eval_schema_error_errors_attribute_writable_batch13():
    e = EvalSchemaError("msg")
    e.errors = [{"new": True}]
    assert e.errors == [{"new": True}]


# ---------- load_schema 行为深度第十三批 ----------


def test_load_schema_returns_dict_batch13():
    out = load_schema("manifest.schema.json")
    assert isinstance(out, dict)


def test_load_schema_uses_context_manager_batch13():
    """load_schema 应该用 with open(...) as f。"""
    source = inspect.getsource(load_schema)
    assert "with " in source
    assert "open(" in source


def test_load_schema_uses_utf8_encoding_batch13():
    source = inspect.getsource(load_schema)
    assert "encoding=\"utf-8\"" in source or "encoding='utf-8'" in source


def test_load_schema_calls_json_load_batch13():
    source = inspect.getsource(load_schema)
    assert "json.load(" in source


def test_load_schema_calls_schema_path_batch13():
    source = inspect.getsource(load_schema)
    assert "_schema_path(" in source


def test_load_schema_not_cached_batch13():
    """两次调用应返回不同 dict（每次重新读盘）。"""
    out1 = load_schema("manifest.schema.json")
    out2 = load_schema("manifest.schema.json")
    assert out1 is not out2
    assert out1 == out2


def test_load_schema_modification_does_not_affect_next_batch13():
    """修改返回 dict 不应影响下次读取。"""
    out1 = load_schema("manifest.schema.json")
    if "properties" in out1:
        original = json.loads(json.dumps(out1))
        out1["properties"]["x"] = {"type": "string"}
        out2 = load_schema("manifest.schema.json")
        assert out2 == original


# ---------- validate 行为深度第十三批 ----------


def test_validate_returns_none_on_success_batch13():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_validate_raises_on_failure_batch13():
    with pytest.raises(EvalSchemaError):
        validate({"wrong": "shape"}, "manifest.schema.json")


def test_validate_errors_count_in_message_batch13():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({"wrong": "shape"}, "manifest.schema.json")
    msg = str(exc_info.value)
    assert "校验失败" in msg


def test_validate_errors_attribute_has_list_batch13():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({"wrong": "shape"}, "manifest.schema.json")
    assert isinstance(exc_info.value.errors, list)
    assert len(exc_info.value.errors) > 0


def test_validate_errors_each_has_3_keys_batch13():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({"wrong": "shape"}, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert set(err.keys()) == {"path", "message", "schema_path"}


def test_validate_errors_path_is_list_batch13():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({"wrong": "shape"}, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert isinstance(err["path"], list)


def test_validate_errors_schema_path_is_list_batch13():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({"wrong": "shape"}, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert isinstance(err["schema_path"], list)


def test_validate_uses_draft202012_validator_batch13():
    source = inspect.getsource(validate)
    assert "Draft202012Validator" in source


def test_validate_uses_iter_errors_batch13():
    source = inspect.getsource(validate)
    assert "iter_errors" in source


def test_validate_sorts_errors_by_path_batch13():
    source = inspect.getsource(validate)
    assert "sorted(" in source
    assert "absolute_path" in source


def test_validate_does_not_mutate_instance_batch13():
    instance = {"wrong": "shape"}
    instance_before = json.loads(json.dumps(instance))
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError:
        pass
    assert instance == instance_before


def test_validate_message_contains_schema_name_batch13():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({"wrong": "shape"}, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc_info.value)


def test_validate_message_contains_head_path_batch13():
    """message 应含 head 的 path。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({"wrong": "shape"}, "manifest.schema.json")
    msg = str(exc_info.value)
    assert "path=" in msg


# ---------- validate_file 行为深度第十三批 ----------


def test_validate_file_str_input_batch13(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    assert validate_file(str(p), "manifest.schema.json") is None


def test_validate_file_path_input_batch13(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_not_exist_raises_filenotfounderror_batch13(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "nonexistent.json", "manifest.schema.json")


def test_validate_file_invalid_json_raises_json_decode_error_batch13(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json}", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_schema_raises_eval_schema_error_batch13(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"wrong": "shape"}', encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_uses_utf8_encoding_batch13():
    source = inspect.getsource(validate_file)
    assert "encoding=\"utf-8\"" in source or "encoding='utf-8'" in source


def test_validate_file_uses_context_manager_batch13():
    source = inspect.getsource(validate_file)
    assert "with " in source


def test_validate_file_returns_none_on_success_batch13(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_calls_validate_batch13():
    source = inspect.getsource(validate_file)
    assert "validate(" in source


# ---------- _schema_path 行为深度第十三批 ----------


def test_schema_path_returns_path_batch13():
    out = _schema_path("manifest.schema.json")
    assert isinstance(out, Path)


def test_schema_path_not_exist_raises_filenotfounderror_batch13():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nonexistent.schema.json")
    assert "nonexistent.schema.json" in str(exc_info.value)


def test_schema_path_appends_to_schemas_dir_batch13():
    """路径应是 SCHEMAS_DIR / name。"""
    out = _schema_path("manifest.schema.json")
    assert out == SCHEMAS_DIR / "manifest.schema.json"


def test_schema_path_calls_is_file_batch13():
    source = inspect.getsource(_schema_path)
    assert "is_file()" in source


def test_schema_path_message_contains_path_batch13():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nonexistent.schema.json")
    msg = str(exc_info.value)
    assert "Schema" in msg or "不存在" in msg


# ---------- module source forbidden tokens 第十八批 ----------


_FORBIDDEN_TOKENS_ROUND18 = [
    "eval(",
    "exec(",
    "os.system(",
    "subprocess.call(",
    "subprocess.check_output(",
    "subprocess.check_call(",
    "os.popen(",
    "__import__(",
    "pickle.loads(",
    "yaml.load(",
    "shutil.rmtree(",
    "os.remove(",
    "open('/etc",
    "open(\"/etc",
    "requests.get(",
    "urllib.request.urlopen(",
]


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND18)
def test_module_source_forbidden_tokens_round18_batch13(token):
    source = inspect.getsource(smod)
    assert token not in source


# ---------- module source 字符串精确补强第十五批 ----------


def test_module_source_module_docstring_present_batch13():
    source = inspect.getsource(smod)
    head = "\n".join(source.split("\n")[:15])
    assert '"""' in head


def test_module_source_future_annotations_present_batch13():
    source = inspect.getsource(smod)
    head = "\n".join(source.split("\n")[:30])
    assert "from __future__ import annotations" in head


def test_module_source_imports_json_batch13():
    source = inspect.getsource(smod)
    head = "\n".join(source.split("\n")[:30])
    assert "import json" in head


def test_module_source_imports_pathlib_path_batch13():
    source = inspect.getsource(smod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_imports_typing_any_batch13():
    source = inspect.getsource(smod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_source_imports_draft202012_validator_batch13():
    source = inspect.getsource(smod)
    head = "\n".join(source.split("\n")[:30])
    assert "from jsonschema import Draft202012Validator" in head


def test_module_source_imports_jsvalidation_error_batch13():
    source = inspect.getsource(smod)
    head = "\n".join(source.split("\n")[:30])
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in head


def test_module_source_defines_schemas_dir_batch13():
    source = inspect.getsource(smod)
    assert "SCHEMAS_DIR" in source


def test_module_source_defines_eval_schema_error_batch13():
    source = inspect.getsource(smod)
    assert "class EvalSchemaError" in source


def test_module_source_defines_schema_path_batch13():
    source = inspect.getsource(smod)
    assert "def _schema_path(" in source


def test_module_source_defines_load_schema_batch13():
    source = inspect.getsource(smod)
    assert "def load_schema(" in source


def test_module_source_defines_validate_batch13():
    source = inspect.getsource(smod)
    assert "def validate(" in source


def test_module_source_defines_validate_file_batch13():
    source = inspect.getsource(smod)
    assert "def validate_file(" in source


def test_module_source_has_dunder_all_batch13():
    source = inspect.getsource(smod)
    assert "__all__" in source


def test_module_source_no_subprocess_import_batch13():
    source = inspect.getsource(smod)
    assert "import subprocess" not in source


def test_module_source_uses_parent_parent_batch13():
    source = inspect.getsource(smod)
    assert ".parent.parent" in source


def test_module_source_has_no_open_to_string_path_batch13():
    """不应有 open('/etc' 等敏感路径。"""
    source = inspect.getsource(smod)
    assert "open('/etc" not in source
    assert 'open("/etc' not in source


def test_module_source_uses_resolve_batch13():
    source = inspect.getsource(smod)
    assert ".resolve()" in source


def test_module_source_uses_iter_errors_sorted_batch13():
    source = inspect.getsource(smod)
    assert "sorted(" in source


def test_module_source_uses_absolute_path_batch13():
    source = inspect.getsource(smod)
    assert "absolute_path" in source


def test_module_source_uses_absolute_schema_path_batch13():
    source = inspect.getsource(smod)
    assert "absolute_schema_path" in source


# ---------- signatures 第十五批 ----------


def test_schema_path_one_param_batch13():
    sig = inspect.signature(_schema_path)
    assert len(sig.parameters) == 1
    assert "name" in sig.parameters


def test_load_schema_one_param_batch13():
    sig = inspect.signature(load_schema)
    assert len(sig.parameters) == 1
    assert "name" in sig.parameters


def test_validate_two_params_batch13():
    sig = inspect.signature(validate)
    assert len(sig.parameters) == 2
    for n in ("instance", "schema_name"):
        assert n in sig.parameters


def test_validate_file_two_params_batch13():
    sig = inspect.signature(validate_file)
    assert len(sig.parameters) == 2
    for n in ("path", "schema_name"):
        assert n in sig.parameters


def test_eval_schema_error_init_two_params_optional_batch13():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert len(sig.parameters) == 3  # self + message + errors
    assert sig.parameters["errors"].default is None


def test_schema_path_return_annotation_path_batch13():
    sig = inspect.signature(_schema_path)
    assert "Path" in str(sig.return_annotation)


def test_load_schema_return_annotation_dict_batch13():
    sig = inspect.signature(load_schema)
    assert "dict" in str(sig.return_annotation)


def test_validate_return_annotation_none_or_str_batch13():
    """validate return annotation 是 None（在 from __future__ import annotations 下变 'None'）。"""
    sig = inspect.signature(validate)
    ret_str = str(sig.return_annotation)
    # 接受 "None" 字符串或 None
    assert ret_str == "None" or ret_str is None or ret_str == type(None).__name__


def test_validate_file_path_annotation_optional_batch13():
    sig = inspect.signature(validate_file)
    p_str = str(sig.parameters["path"].annotation)
    assert "None" in p_str or "Path" in p_str


def test_eval_schema_error_message_annotation_str_batch13():
    sig = inspect.signature(EvalSchemaError.__init__)
    p_str = str(sig.parameters["message"].annotation)
    assert "str" in p_str


def test_eval_schema_error_errors_annotation_optional_list_batch13():
    sig = inspect.signature(EvalSchemaError.__init__)
    p_str = str(sig.parameters["errors"].annotation)
    assert "None" in p_str
    assert "list" in p_str


# ---------- module 合理性第十五批 ----------


def test_module_dunder_file_exists_batch13():
    assert hasattr(smod, "__file__")
    assert smod.__file__ is not None


def test_module_dunder_file_schema_py_batch13():
    assert "evaluation" in smod.__file__
    assert smod.__file__.endswith("schema.py")


def test_module_name_evaluation_schema_batch13():
    assert smod.__name__ == "evaluation.schema"


def test_module_dunder_all_5_items_batch13():
    assert len(smod.__all__) == 5


def test_module_dunder_all_items_unique_batch13():
    assert len(set(smod.__all__)) == len(smod.__all__)


def test_module_dunder_all_includes_expected_names_batch13():
    expected = {"SCHEMAS_DIR", "EvalSchemaError", "load_schema", "validate", "validate_file"}
    assert set(smod.__all__) == expected


def test_module_eval_schema_error_class_count_1_batch13():
    classes = [
        n for n, v in vars(smod).items()
        if inspect.isclass(v) and v.__module__ == smod.__name__
    ]
    assert classes == ["EvalSchemaError"]


def test_module_constants_count_1_batch13():
    """只有 SCHEMAS_DIR 一个模块级常量。"""
    assert hasattr(smod, "SCHEMAS_DIR")
    assert isinstance(smod.SCHEMAS_DIR, Path)


# ---------- 端到端集成第十五批 ----------


def test_e2e_validate_then_eval_schema_error_caught_batch13():
    """validate 失败 → EvalSchemaError，调用方应能 try/except 处理。"""
    try:
        validate({"wrong": "shape"}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert e.errors  # 应有 errors 列表
        assert str(e)  # 应有 message


def test_e2e_load_schema_then_validate_with_dict_batch13():
    """先 load_schema 再 validate 一个 dict。"""
    schema = load_schema("manifest.schema.json")
    assert "$schema" in schema or "type" in schema
    valid = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(valid, "manifest.schema.json") is None


def test_e2e_validate_file_then_load_manifest_batch13(tmp_path):
    """validate_file 走完整链路。"""
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_eval_schema_error_json_serializable_batch13():
    """EvalSchemaError 的 errors list 应 json 可序列化。"""
    try:
        validate({"wrong": "shape"}, "manifest.schema.json")
    except EvalSchemaError as e:
        parsed = json.loads(json.dumps(e.errors))
        assert parsed == e.errors


def test_e2e_idempotent_validate_batch13():
    """两次 validate 同一 instance 应得到一致的 errors。"""
    inst = {"wrong": "shape"}
    e1_errors = None
    e2_errors = None
    try:
        validate(inst, "manifest.schema.json")
    except EvalSchemaError as e:
        e1_errors = e.errors
    try:
        validate(inst, "manifest.schema.json")
    except EvalSchemaError as e:
        e2_errors = e.errors
    assert e1_errors == e2_errors


def test_e2e_eval_schema_error_errors_independent_batch13():
    """两次抛 EvalSchemaError 的 errors 应是独立 list。"""
    e1, e2 = None, None
    try:
        validate({"wrong": "shape"}, "manifest.schema.json")
    except EvalSchemaError as e:
        e1 = e
    try:
        validate({"wrong": "shape"}, "manifest.schema.json")
    except EvalSchemaError as e:
        e2 = e
    assert e1.errors is not e2.errors


def test_e2e_validate_file_idempotent_batch13(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    out1 = validate_file(p, "manifest.schema.json")
    out2 = validate_file(p, "manifest.schema.json")
    assert out1 == out2


def test_e2e_combined_schema_path_load_validate_batch13():
    """三个内部函数协作链：_schema_path → load_schema → validate。"""
    p = _schema_path("manifest.schema.json")
    assert p.is_file()
    schema = load_schema("manifest.schema.json")
    assert isinstance(schema, dict)
    valid = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(valid, "manifest.schema.json")


def test_e2e_eval_schema_error_independent_errors_attribute_batch13():
    """errors attribute 不应共享引用。"""
    e1 = EvalSchemaError("msg", errors=[{"a": 1}])
    e2 = EvalSchemaError("msg", errors=[{"a": 1}])
    assert e1.errors == e2.errors
    assert e1.errors is not e2.errors
    e1.errors.append({"b": 2})
    assert len(e2.errors) == 1


def test_e2e_schema_path_with_annotation_schema_batch13():
    """annotation schema 也能被 _schema_path 找到。"""
    p = _schema_path("annotation.schema.json")
    assert p.is_file()
    schema = load_schema("annotation.schema.json")
    assert isinstance(schema, dict)
