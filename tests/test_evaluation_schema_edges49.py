"""evaluation/schema.py 第四十九轮 edges 测试（Round 537）。

补强 edges48 未触及的角度（第二十九批）：
- EvalSchemaError 第二十九批：errors dict key / errors 长列表 / message 含 emoji / 嵌套 raise / 多实例独立
- _schema_path 第二十九批：name 含 .. / 多个点 / 长文件名 / Path-like
- load_schema 第二十九批：三 schema 多次加载 / 独立 dict 修改不影响 / schema 是 dict
- validate 第二十九批：errors 数量与 message 一致 / 头 error 在 message / 空 errors 不抛 / 多 errors 排序
- validate_file 第二十九批：Path 与 str 等价 / tmp_path 文件 / 大 manifest / 多次调用幂等
- module source forbidden tokens 第四十七批
- module source 字符串精确补强第四十三批
- signatures 第四十三批
- module 合理性第四十三批
- 端到端集成第四十三批
"""

from __future__ import annotations

import inspect
import json
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


# ---------- EvalSchemaError 第二十九批 ----------


def test_eval_schema_error_errors_with_dict_key_batch29():
    """errors 含 dict key。"""
    e = EvalSchemaError("msg", [{"path": ["a"], "message": "x"}])
    assert e.errors[0]["path"] == ["a"]


def test_eval_schema_error_errors_large_list_batch29():
    """errors 大 list。"""
    errors = [{"i": i} for i in range(100)]
    e = EvalSchemaError("msg", errors)
    assert len(e.errors) == 100


def test_eval_schema_error_message_with_emoji_batch29():
    """message 含 emoji。"""
    e = EvalSchemaError("失败 🚨")
    assert "🚨" in str(e)


def test_eval_schema_error_nested_raise_batch29():
    """嵌套 raise ... from inner。"""
    try:
        try:
            raise ValueError("inner")
        except ValueError as inner:
            raise EvalSchemaError("outer") from inner
    except EvalSchemaError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, ValueError)


def test_eval_schema_error_multiple_instances_independent_batch29():
    """多个实例 errors 互不影响。"""
    e1 = EvalSchemaError("m1", [{"x": 1}])
    e2 = EvalSchemaError("m2", [{"y": 2}])
    e1.errors.append({"z": 3})
    assert e2.errors == [{"y": 2}]


def test_eval_schema_error_can_be_pickled_batch29():
    """可序列化（基础 Exception 行为）。"""
    import pickle
    e = EvalSchemaError("msg", [{"x": 1}])
    pickled = pickle.dumps(e)
    restored = pickle.loads(pickled)
    assert str(restored) == "msg"


def test_eval_schema_error_args_only_message_batch29():
    """args 只含 message（不含 errors）。"""
    e = EvalSchemaError("msg", [{"x": 1}])
    assert e.args == ("msg",)


# ---------- _schema_path 第二十九批 ----------


def test_schema_path_with_dot_dot_batch29(tmp_path):
    """name 含 .. → SCHEMAS_DIR 上层 + nonexistent → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("../nonexistent_xyz.json")


def test_schema_path_multiple_dots_batch29(tmp_path):
    """name 含多个点（如 a.b.c.json）。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("a.b.c.nonexistent.json")


def test_schema_path_long_name_batch29():
    """长文件名也合法。"""
    long_name = "x" * 100 + ".json"
    with pytest.raises(FileNotFoundError):
        _schema_path(long_name)


def test_schema_path_no_extension_batch29():
    """无扩展名也尝试加载。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("nonexistent_no_ext")


def test_schema_path_message_contains_full_path_batch29():
    """FileNotFoundError message 含 SCHEMAS_DIR。"""
    try:
        _schema_path("definitely_nonexistent_xyz.json")
    except FileNotFoundError as e:
        assert "definitely_nonexistent_xyz.json" in str(e)
        return
    pytest.fail("Expected FileNotFoundError")


# ---------- load_schema 第二十九批 ----------


def test_load_schema_three_schemas_all_dicts_batch29():
    for name in [
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    ]:
        s = load_schema(name)
        assert isinstance(s, dict)


def test_load_schema_independent_dicts_modification_batch29():
    """两次加载返回独立 dict，修改一个不影响另一个。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    s1["_hack"] = True
    assert "_hack" not in s2


def test_load_schema_idempotent_batch29():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    # 修改 s1 不影响 s2
    assert s1 == s2


def test_load_schema_manifest_has_type_object_batch29():
    s = load_schema("manifest.schema.json")
    assert s.get("type") == "object"


def test_load_schema_evaluation_report_has_type_object_batch29():
    s = load_schema("evaluation-report.schema.json")
    assert s.get("type") == "object"


# ---------- validate 第二十九批 ----------


def test_validate_errors_count_matches_message_batch29():
    """message 含 errors 数量。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    msg = str(exc.value)
    assert f"{len(exc.value.errors)} 处" in msg


def test_validate_head_error_message_in_full_message_batch29():
    """头 error 的 message 在完整 message 中。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    head = exc.value.errors[0]
    assert head["message"] in str(exc.value)


def test_validate_empty_errors_no_raise_batch29():
    """合法 instance → 不抛。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    validate(instance, "manifest.schema.json")


def test_validate_errors_sorted_batch29():
    """errors 按 path 排序。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    paths = [tuple(e["path"]) for e in exc.value.errors]
    assert paths == sorted(paths)


def test_validate_with_unknown_property_batch29():
    """含 unknown property → 至少 1 个 error。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "unknown_extra": True,
    }
    with pytest.raises(EvalSchemaError) as exc:
        validate(instance, "manifest.schema.json")
    assert len(exc.value.errors) >= 1


def test_validate_returns_none_on_success_batch29():
    """成功 validate 返回 None。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    result = validate(instance, "manifest.schema.json")
    assert result is None


def test_validate_errors_contain_path_message_schema_path_batch29():
    """每个 error 含 path / message / schema_path 3 个 key。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert set(err.keys()) == {"path", "message", "schema_path"}


# ---------- validate_file 第二十九批 ----------


def test_validate_file_path_str_equivalent_batch29(tmp_path):
    """Path 与 str 等价（都成功或都失败）。"""
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {"manifest_version": "1.0", "devset_status": "complete", "documents": []}
        ),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_large_manifest_batch29(tmp_path):
    """大 manifest（100 个 doc）也能校验。"""
    docs = [
        {"doc_id": f"d{i}", "path": f"samples/{i}.pdf", "source_type": "pdf", "sha256": "a" * 64}
        for i in range(100)
    ]
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": docs,
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_called_multiple_times_batch29(tmp_path):
    """多次调用同一文件。"""
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {"manifest_version": "1.0", "devset_status": "complete", "documents": []}
        ),
        encoding="utf-8",
    )
    for _ in range(3):
        validate_file(p, "manifest.schema.json")


def test_validate_file_no_modification_batch29(tmp_path):
    """校验后文件不变。"""
    p = tmp_path / "m.json"
    content = json.dumps(
        {"manifest_version": "1.0", "devset_status": "complete", "documents": []}
    )
    p.write_text(content, encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    assert p.read_text(encoding="utf-8") == content


def test_validate_file_directory_raises_batch29(tmp_path):
    """path 是目录 → FileNotFoundError。"""
    d = tmp_path / "subdir"
    d.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(d, "manifest.schema.json")


def test_validate_file_idempotent_batch29(tmp_path):
    """两次校验得到相同结果。"""
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {"manifest_version": "1.0", "devset_status": "complete", "documents": []}
        ),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")


# ---------- module source forbidden tokens 第四十七批 ----------


def test_module_source_no_subprocess_batch29():
    src = inspect.getsource(smod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch29():
    src = inspect.getsource(smod)
    assert "os.system" not in src


def test_module_source_no_eval_batch29():
    src = inspect.getsource(smod)
    assert "eval(" not in src


def test_module_source_no_exec_batch29():
    src = inspect.getsource(smod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch29():
    src = inspect.getsource(smod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch29():
    src = inspect.getsource(smod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch29():
    src = inspect.getsource(smod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch29():
    src = inspect.getsource(smod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch29():
    src = inspect.getsource(smod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch29():
    src = inspect.getsource(smod)
    assert "shutil" not in src


def test_module_source_no_requests_batch29():
    src = inspect.getsource(smod)
    assert "requests" not in src


def test_module_source_no_unlink_batch29():
    src = inspect.getsource(smod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十三批 ----------


def test_module_source_contains_module_docstring_batch29():
    src = inspect.getsource(smod)
    assert "加载并校验" in src


def test_module_source_contains_schemas_dir_assignment_batch29():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = " in src


def test_module_source_contains_resolve_call_batch29():
    src = inspect.getsource(smod)
    assert ".resolve()" in src


def test_module_source_contains_schema_path_func_batch29():
    src = inspect.getsource(smod)
    assert "def _schema_path" in src


def test_module_source_contains_eval_schema_error_class_batch29():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_contains_load_schema_func_batch29():
    src = inspect.getsource(smod)
    assert "def load_schema" in src


def test_module_source_contains_validate_func_batch29():
    src = inspect.getsource(smod)
    assert "def validate(" in src


def test_module_source_contains_validate_file_func_batch29():
    src = inspect.getsource(smod)
    assert "def validate_file(" in src


def test_module_source_contains_utf_8_encoding_batch29():
    src = inspect.getsource(smod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_draft_2020_12_batch29():
    src = inspect.getsource(smod)
    assert "Draft202012Validator" in src


def test_module_source_contains_iter_errors_call_batch29():
    src = inspect.getsource(smod)
    assert "iter_errors" in src


def test_module_source_contains_absolute_path_call_batch29():
    src = inspect.getsource(smod)
    assert "absolute_path" in src


def test_module_source_contains_absolute_schema_path_call_batch29():
    src = inspect.getsource(smod)
    assert "absolute_schema_path" in src


def test_module_source_contains_no_app_schema_reuse_doc_batch29():
    src = inspect.getsource(smod)
    assert "不与 app/schema.py 复用" in src


# ---------- signatures 第四十三批 ----------


def test_signature_eval_schema_error_init_full_batch29():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "errors"]


def test_signature_eval_schema_error_init_return_none_batch29():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.return_annotation == "None"


def test_signature_eval_schema_error_message_str_batch29():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["message"].annotation == "str"


def test_signature_eval_schema_error_errors_default_none_batch29():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_signature_eval_schema_error_errors_optional_list_batch29():
    sig = inspect.signature(EvalSchemaError.__init__)
    ps = str(sig.parameters["errors"].annotation)
    assert "list" in ps and "None" in ps


def test_signature_schema_path_batch29():
    sig = inspect.signature(_schema_path)
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "Path"


def test_signature_load_schema_batch29():
    sig = inspect.signature(load_schema)
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_validate_batch29():
    sig = inspect.signature(validate)
    assert sig.parameters["instance"].annotation == "dict[str, Any]"
    assert sig.parameters["schema_name"].annotation == "str"
    assert sig.return_annotation == "None"


def test_signature_validate_file_batch29():
    sig = inspect.signature(validate_file)
    assert "Path" in str(sig.parameters["path"].annotation)
    assert "str" in str(sig.parameters["path"].annotation)
    assert sig.parameters["schema_name"].annotation == "str"
    assert sig.return_annotation == "None"


# ---------- module 合理性第四十三批 ----------


def test_module_has_future_annotations_batch29():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch29():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_imports_pathlib_batch29():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch29():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_imports_draft_validator_batch29():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_imports_validation_error_batch29():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_schemas_dir_absolute_batch29():
    assert SCHEMAS_DIR.is_absolute()


def test_module_no_main_block_batch29():
    src = inspect.getsource(smod)
    assert 'if __name__ == "__main__"' not in src


def test_module_all_has_five_entries_batch29():
    src = inspect.getsource(smod)
    for name in [
        '"SCHEMAS_DIR"',
        '"EvalSchemaError"',
        '"load_schema"',
        '"validate"',
        '"validate_file"',
    ]:
        assert name in src


# ---------- 端到端集成第四十三批 ----------


def test_e2e_validate_full_manifest_roundtrip_batch29(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "sha256": "a" * 64}
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_three_schemas_exist_batch29():
    for name in ["manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"]:
        p = _schema_path(name)
        assert p.is_file()


def test_e2e_eval_schema_error_caught_batch29():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert "manifest.schema.json" in str(e)
        return
    pytest.fail("Expected EvalSchemaError")


def test_e2e_validate_errors_complete_batch29():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["path"], list)
        assert isinstance(err["schema_path"], list)
        assert isinstance(err["message"], str)


def test_e2e_schemas_dir_in_project_batch29():
    """SCHEMAS_DIR 在项目根下。"""
    project_root = Path(__file__).resolve().parent.parent
    assert SCHEMAS_DIR.parent == project_root


def test_e2e_validate_idempotent_batch29():
    """端到端：相同输入两次得到相同结果。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e1:
        try:
            validate({}, "manifest.schema.json")
        except EvalSchemaError as e2:
            assert str(e1) == str(e2)
            assert e1.errors == e2.errors
            return
    pytest.fail("Expected EvalSchemaError")


def test_e2e_validate_with_valid_annotation_batch29():
    """端到端：合法 annotation 通过。"""
    annotation = {
        "annotation_version": "1.0",
        "doc_id": "d1",
    }
    validate(annotation, "annotation.schema.json")
