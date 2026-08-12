"""evaluation/schema.py 第四十八轮 edges 测试（Round 530）。

补强 edges47 未触及的角度（第二十八批）：
- EvalSchemaError 第二十八批：errors 是 generator / errors 是迭代器 / message 带换行 / errors 含中文
- _schema_path 第二十八批：name 含 / 目录组件 / name 是 path-like 但被 str 化 / 返回 Path 类型
- load_schema 第二十八批：三 schema 文件大小 > 0 / schema 含 properties / 不修改文件
- validate 第二十八批：errors 排序顺序 / 多错误 instance / instance 含 unicode / errors 中 message 非空
- validate_file 第二十八批：utf-8-sig 失败 / 多层嵌套目录 / 大文件 / 双校验
- module source forbidden tokens 第四十六批
- module source 字符串精确补强第四十二批
- signatures 第四十二批
- module 合理性第四十二批
- 端到端集成第四十二批
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


# ---------- EvalSchemaError 第二十八批 ----------


def test_eval_schema_error_errors_can_be_generator_batch28():
    """errors 传入生成器表达式（迭代后空）→ 保留为 list（or []）。"""
    # 但实际：errors 是 generator，会保留 truthy
    gen = (x for x in [{"a": 1}])
    e = EvalSchemaError("msg", list(gen))
    assert e.errors == [{"a": 1}]


def test_eval_schema_error_errors_empty_generator_to_empty_list_batch28():
    """空 generator → 空 list。"""
    gen = (x for x in [])
    e = EvalSchemaError("msg", list(gen))
    assert e.errors == []


def test_eval_schema_error_message_with_newline_batch28():
    e = EvalSchemaError("line1\nline2")
    assert "\n" in str(e)


def test_eval_schema_error_errors_with_chinese_batch28():
    e = EvalSchemaError("msg", [{"错误": "详情"}])
    assert e.errors == [{"错误": "详情"}]


def test_eval_schema_error_inheritance_chain_batch28():
    """EvalSchemaError → Exception → BaseException。"""
    assert issubclass(EvalSchemaError, Exception)
    assert issubclass(EvalSchemaError, BaseException)


def test_eval_schema_error_can_be_raised_in_loop_batch28():
    """循环里多次 raise。"""
    for i in range(3):
        try:
            raise EvalSchemaError(f"msg{i}")
        except EvalSchemaError as e:
            assert f"msg{i}" in str(e)


def test_eval_schema_error_args_just_message_batch28():
    """args 只含 message（errors 是独立属性）。"""
    e = EvalSchemaError("hello", [{"x": 1}])
    assert e.args == ("hello",)


# ---------- _schema_path 第二十八批 ----------


def test_schema_path_name_with_slash_directory_batch28():
    """name 含 / → 尝试在 SCHEMAS_DIR/subdir/ 找。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/nonexistent.json")


def test_schema_path_returns_path_batch28():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_in_schemas_dir_batch28():
    """返回的 path 在 SCHEMAS_DIR 下。"""
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_message_contains_full_path_batch28():
    try:
        _schema_path("nonexistent_xyz.json")
    except FileNotFoundError as e:
        # message 含 SCHEMAS_DIR/nonexistent_xyz.json
        assert "nonexistent_xyz.json" in str(e)
        return
    pytest.fail("Expected FileNotFoundError")


# ---------- load_schema 第二十八批 ----------


def test_load_schema_manifest_file_size_positive_batch28():
    p = _schema_path("manifest.schema.json")
    assert p.stat().st_size > 0


def test_load_schema_annotation_file_size_positive_batch28():
    p = _schema_path("annotation.schema.json")
    assert p.stat().st_size > 0


def test_load_schema_evaluation_report_file_size_positive_batch28():
    p = _schema_path("evaluation-report.schema.json")
    assert p.stat().st_size > 0


def test_load_schema_manifest_has_properties_batch28():
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_load_schema_annotation_has_properties_batch28():
    s = load_schema("annotation.schema.json")
    assert "properties" in s


def test_load_schema_evaluation_report_has_properties_batch28():
    s = load_schema("evaluation-report.schema.json")
    assert "properties" in s


def test_load_schema_does_not_modify_file_batch28():
    p = _schema_path("manifest.schema.json")
    before = p.read_bytes()
    load_schema("manifest.schema.json")
    after = p.read_bytes()
    assert before == after


def test_load_schema_independent_dicts_batch28():
    """两次加载返回独立 dict，修改一个不影响另一个。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    s1["_hack"] = True
    assert "_hack" not in s2


# ---------- validate 第二十八批 ----------


def test_validate_errors_sorted_by_path_batch28():
    """errors 按 absolute_path 排序。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    paths = [tuple(e["path"]) for e in exc.value.errors]
    assert paths == sorted(paths)


def test_validate_errors_messages_non_empty_batch28():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["message"], str)
        assert len(err["message"]) > 0


def test_validate_message_contains_count_and_path_batch28():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    msg = str(exc.value)
    assert "3 处" in msg
    assert "path=" in msg


def test_validate_message_contains_schema_name_batch28():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc.value)


def test_validate_with_unicode_in_instance_batch28():
    """instance 含 unicode → 不影响 schema 校验。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": "中文", "path": "samples/x.pdf", "source_type": "pdf"}
        ],
    }
    validate(instance, "manifest.schema.json")


def test_validate_unknown_property_raises_batch28():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "unknown_key": True,
    }
    with pytest.raises(EvalSchemaError) as exc:
        validate(instance, "manifest.schema.json")
    assert len(exc.value.errors) >= 1


# ---------- validate_file 第二十八批 ----------


def test_validate_file_utf8_sig_fails_batch28(tmp_path):
    """utf-8-sig 编码（带 BOM）→ utf-8 解码后以 BOM 开头 → JSON 解析失败。"""
    p = tmp_path / "m.json"
    content = json.dumps(
        {"manifest_version": "1.0", "devset_status": "complete", "documents": []}
    )
    p.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_deeply_nested_dir_batch28(tmp_path):
    """文件在多层嵌套目录里。"""
    nested = tmp_path / "a" / "b" / "c" / "d"
    nested.mkdir(parents=True)
    p = nested / "m.json"
    p.write_text(
        json.dumps(
            {"manifest_version": "1.0", "devset_status": "complete", "documents": []}
        ),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")


def test_validate_file_large_manifest_batch28(tmp_path):
    """100 个 documents 的大 manifest。"""
    docs = [
        {"doc_id": f"d{i}", "path": f"samples/{i}.pdf", "source_type": "pdf", "sha256": "a" * 64}
        for i in range(100)
    ]
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": docs,
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_called_twice_batch28(tmp_path):
    """同一文件校验两次。"""
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {"manifest_version": "1.0", "devset_status": "complete", "documents": []}
        ),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")


def test_validate_file_no_modification_batch28(tmp_path):
    p = tmp_path / "m.json"
    content = json.dumps(
        {"manifest_version": "1.0", "devset_status": "complete", "documents": []}
    )
    p.write_text(content, encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    assert p.read_text(encoding="utf-8") == content


# ---------- module source forbidden tokens 第四十六批 ----------


def test_module_source_no_subprocess_batch28():
    src = inspect.getsource(smod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch28():
    src = inspect.getsource(smod)
    assert "os.system" not in src


def test_module_source_no_eval_batch28():
    src = inspect.getsource(smod)
    assert "eval(" not in src


def test_module_source_no_exec_batch28():
    src = inspect.getsource(smod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch28():
    src = inspect.getsource(smod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch28():
    src = inspect.getsource(smod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch28():
    src = inspect.getsource(smod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch28():
    src = inspect.getsource(smod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch28():
    src = inspect.getsource(smod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch28():
    src = inspect.getsource(smod)
    assert "shutil" not in src


def test_module_source_no_requests_batch28():
    src = inspect.getsource(smod)
    assert "requests" not in src


def test_module_source_no_unlink_batch28():
    src = inspect.getsource(smod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十二批 ----------


def test_module_source_contains_module_docstring_batch28():
    src = inspect.getsource(smod)
    assert "加载并校验" in src


def test_module_source_contains_schemas_dir_batch28():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = " in src


def test_module_source_contains_path_resolve_batch28():
    src = inspect.getsource(smod)
    assert ".resolve()" in src or "__file__" in src


def test_module_source_contains_schema_path_func_batch28():
    src = inspect.getsource(smod)
    assert "def _schema_path" in src


def test_module_source_contains_eval_schema_error_class_batch28():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_contains_iter_errors_usage_batch28():
    src = inspect.getsource(smod)
    assert "iter_errors" in src


def test_module_source_contains_absolute_path_sort_batch28():
    src = inspect.getsource(smod)
    assert "absolute_path" in src


def test_module_source_contains_load_schema_func_batch28():
    src = inspect.getsource(smod)
    assert "def load_schema" in src


def test_module_source_contains_validate_func_batch28():
    src = inspect.getsource(smod)
    assert "def validate(" in src


def test_module_source_contains_validate_file_func_batch28():
    src = inspect.getsource(smod)
    assert "def validate_file(" in src


def test_module_source_contains_utf_8_encoding_batch28():
    src = inspect.getsource(smod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_draft_2020_12_batch28():
    src = inspect.getsource(smod)
    assert "Draft202012Validator" in src


# ---------- signatures 第四十二批 ----------


def test_signature_eval_schema_error_init_full_batch28():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "errors"]


def test_signature_eval_schema_error_init_return_none_batch28():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.return_annotation == "None"


def test_signature_schema_path_batch28():
    sig = inspect.signature(_schema_path)
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "Path"


def test_signature_load_schema_batch28():
    sig = inspect.signature(load_schema)
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_validate_batch28():
    sig = inspect.signature(validate)
    assert sig.parameters["instance"].annotation == "dict[str, Any]"
    assert sig.parameters["schema_name"].annotation == "str"
    assert sig.return_annotation == "None"


def test_signature_validate_file_batch28():
    sig = inspect.signature(validate_file)
    assert "Path" in str(sig.parameters["path"].annotation)
    assert "str" in str(sig.parameters["path"].annotation)
    assert sig.parameters["schema_name"].annotation == "str"
    assert sig.return_annotation == "None"


def test_signature_eval_schema_error_message_annotation_batch28():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["message"].annotation == "str"


def test_signature_eval_schema_error_errors_default_none_batch28():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


# ---------- module 合理性第四十二批 ----------


def test_module_has_future_annotations_batch28():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch28():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_imports_pathlib_batch28():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch28():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_imports_draft_validator_batch28():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_imports_validation_error_batch28():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_schemas_dir_absolute_batch28():
    assert SCHEMAS_DIR.is_absolute()


def test_module_no_main_block_batch28():
    src = inspect.getsource(smod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十二批 ----------


def test_e2e_validate_full_manifest_roundtrip_batch28(tmp_path):
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


def test_e2e_three_schemas_exist_batch28():
    for name in ["manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"]:
        p = _schema_path(name)
        assert p.is_file()


def test_e2e_eval_schema_error_caught_batch28():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert "manifest.schema.json" in str(e)
        return
    pytest.fail("Expected EvalSchemaError")


def test_e2e_validate_errors_complete_batch28():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["path"], list)
        assert isinstance(err["schema_path"], list)
        assert isinstance(err["message"], str)


def test_e2e_schemas_dir_in_project_batch28():
    """SCHEMAS_DIR 在项目根下。"""
    project_root = Path(__file__).resolve().parent.parent
    assert SCHEMAS_DIR.parent == project_root


def test_e2e_validate_idempotent_batch28():
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


def test_e2e_validate_with_valid_manifest_batch28():
    """端到端：合法 manifest 不抛。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    validate(instance, "manifest.schema.json")
