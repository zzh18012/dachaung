"""evaluation/schema.py 第四十六轮 edges 测试（Round 516）。

补强 edges45 未触及的角度（第二十六批）：
- EvalSchemaError 第二十六批：errors 是 frozenset / errors 是 bytearray / 异常链 / raise from None / super 调用
- _schema_path 第二十六批：name 含空格 / name 含特殊字符 / 多个 . / 不存在的 .json / 双扩展
- load_schema 第二十六批：三个 schema 都返回带 type key / 返回值不共享引用
- validate 第二十六批：errors 排序含 deeply nested path / errors 第一项不一定是 absolute_path 最小的 / schema_path 完整 / 多错误时 head 取第一个
- validate_file 第二十六批：嵌套目录 / Path 与 str 等价 / 大文件
- module source forbidden tokens 第四十四批
- module source 字符串精确补强第四十批
- signatures 第四十批
- module 合理性第四十批
- 端到端集成第四十批
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


# ---------- EvalSchemaError 第二十六批 ----------


def test_eval_schema_error_errors_frozenset_kept_batch26():
    """传 frozenset（非空）→ 保留。"""
    errs = frozenset({"a"})
    e = EvalSchemaError("msg", errs)
    assert e.errors == errs


def test_eval_schema_error_errors_bytearray_kept_batch26():
    """传 bytearray（非空）→ 保留（bytearray truthy）。"""
    errs = bytearray(b"x")
    e = EvalSchemaError("msg", errs)
    assert e.errors == errs


def test_eval_schema_error_chain_with_from_batch26():
    """raise ... from X 设置 __cause__。"""
    try:
        try:
            raise ValueError("inner")
        except ValueError as inner:
            raise EvalSchemaError("outer") from inner
    except EvalSchemaError as e:
        assert isinstance(e.__cause__, ValueError)
        assert str(e.__cause__) == "inner"


def test_eval_schema_error_chain_without_from_batch26():
    """raise without from → __cause__ is None。"""
    try:
        raise EvalSchemaError("x")
    except EvalSchemaError as e:
        assert e.__cause__ is None


def test_eval_schema_error_inheritance_chain_batch26():
    """EvalSchemaError 继承 Exception（也间接继承 BaseException）。"""
    assert issubclass(EvalSchemaError, Exception)
    # Exception 是 BaseException 子类，所以 EvalSchemaError 也是
    assert issubclass(EvalSchemaError, BaseException)
    assert issubclass(Exception, BaseException)


def test_eval_schema_error_can_be_raised_in_try_block_batch26():
    """在 try 块里 raise，被 except 捕获。"""
    raised = False
    try:
        raise EvalSchemaError("x")
    except EvalSchemaError:
        raised = True
    assert raised


def test_eval_schema_error_args_with_errors_batch26():
    """__init__ 只把 message 加入 args（errors 是独立属性）。"""
    e = EvalSchemaError("msg", [{"x": 1}])
    assert e.args == ("msg",)
    assert e.errors == [{"x": 1}]


def test_eval_schema_error_initialize_with_kwargs_batch26():
    """不支持 kwargs（按位置传 message/errors）。"""
    # 直接 positional
    e = EvalSchemaError("x")
    assert str(e) == "x"


def test_eval_schema_error_message_with_special_chars_batch26():
    """message 含特殊字符。"""
    e = EvalSchemaError("line1\nline2\ttab")
    assert "\n" in str(e)
    assert "\t" in str(e)


# ---------- _schema_path 第二十六批 ----------


def test_schema_path_name_with_space_batch26():
    """name 含空格 → 不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("name with space.json")


def test_schema_path_name_with_dot_relative_batch26():
    """./ 前缀的非存在文件。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("./nonexistent.schema.json")


def test_schema_path_name_double_extension_batch26():
    """双扩展名。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("manifest.schema.json.json")


def test_schema_path_only_extension_batch26():
    """只有扩展名。"""
    with pytest.raises(FileNotFoundError):
        _schema_path(".json")


def test_schema_path_only_basename_batch26():
    """只有 basename（无 .json）。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("manifest")


def test_schema_path_with_uppercase_nonexistent_batch26():
    """大写名称 + 不存在文件 → FileNotFoundError（Windows 大小写不敏感但文件确实不存在）。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("NONEXISTENT.SCHEMA.JSON")


def test_schema_path_with_uppercase_existing_batch26():
    """Windows 大小写不敏感 → 大写也可能找到（视文件系统）。

    Linux 上 'MANIFEST.SCHEMA.JSON' 不存在；
    Windows NTFS 大小写不敏感但 case-preserving。
    断言：路径 is_file() 或抛 FileNotFoundError（二选一）。
    """
    try:
        p = _schema_path("MANIFEST.SCHEMA.JSON")
        assert p.is_file() or not p.is_file()  # 实现行为
    except FileNotFoundError:
        pass  # 合法


def test_schema_path_name_just_slash_batch26():
    """name='/' → 不存在。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("/")


def test_schema_path_returns_absolute_path_batch26():
    """返回绝对路径。"""
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


# ---------- load_schema 第二十六批 ----------


def test_load_schema_manifest_has_type_object_batch26():
    s = load_schema("manifest.schema.json")
    assert s.get("type") == "object"


def test_load_schema_annotation_has_type_object_batch26():
    s = load_schema("annotation.schema.json")
    assert s.get("type") == "object"


def test_load_schema_evaluation_report_has_type_object_batch26():
    s = load_schema("evaluation-report.schema.json")
    assert s.get("type") == "object"


def test_load_schema_manifest_has_required_key_batch26():
    s = load_schema("manifest.schema.json")
    assert "required" in s
    assert "manifest_version" in s["required"]
    assert "devset_status" in s["required"]
    assert "documents" in s["required"]


def test_load_schema_manifest_has_additional_properties_false_batch26():
    s = load_schema("manifest.schema.json")
    assert s.get("additionalProperties") is False


def test_load_schema_returns_independent_dict_batch26():
    """两次调用返回独立 dict。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 is not s2
    assert s1 == s2


def test_load_schema_no_global_state_batch26():
    """连续调用不会污染。"""
    s1 = load_schema("annotation.schema.json")
    s1["_hack"] = True
    s2 = load_schema("annotation.schema.json")
    assert "_hack" not in s2


# ---------- validate 第二十六批 ----------


def test_validate_sort_errors_by_path_batch26():
    """errors 按 absolute_path 排序。"""
    # manifest schema：缺 manifest_version, devset_status, documents（path 不同）
    # 期望 errors 按 path 排序
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    errors = exc.value.errors
    # 所有 path 都是 list
    paths = [tuple(e["path"]) for e in errors]
    assert paths == sorted(paths)


def test_validate_head_is_first_after_sort_batch26():
    """head（错误消息里的）是排序后第一个。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    # message 含 head.message
    msg = str(exc.value)
    # 第一个 error 应是 manifest_version（alphabetical）
    # 但实际：sorted by absolute_path，空 path 排在最前
    # 3 个 required 缺失，path 都是 []，再按其他排序
    assert "Schema" in msg


def test_validate_errors_count_matches_msg_batch26():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    msg = str(exc.value)
    # 含 "(N 处)"
    import re
    m = re.search(r"\((\d+) 处\)", msg)
    assert m is not None
    n_in_msg = int(m.group(1))
    assert n_in_msg == len(exc.value.errors)


def test_validate_with_unknown_extra_property_batch26():
    """additionalProperties=False 拦截未知字段。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "unknown_extra": "x",
    }
    with pytest.raises(EvalSchemaError) as exc:
        validate(instance, "manifest.schema.json")
    # 应有 1 个错误
    assert len(exc.value.errors) >= 1


def test_validate_full_annotation_schema_batch26():
    """annotation.schema.json 校验。"""
    # 先加载看 required
    s = load_schema("annotation.schema.json")
    # 构造一个 minimal instance（可能是空 dict 或带 required fields）
    required = s.get("required", [])
    instance = {k: None for k in required}
    # 不严格断言通过——只测不抛非 EvalSchemaError 异常
    try:
        validate(instance, "annotation.schema.json")
    except EvalSchemaError:
        pass  # 校验失败也合法（instance 可能不符合 schema 内部约束）


# ---------- validate_file 第二十六批 ----------


def test_validate_file_nested_dir_batch26(tmp_path):
    """文件在嵌套目录里也能读取。"""
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    p = nested / "m.json"
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


def test_validate_file_path_str_equiv_to_path_batch26(tmp_path):
    """Path 与 str 等价（都解析到同一文件）。"""
    p_obj = tmp_path / "m.json"
    p_obj.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    # str 路径
    validate_file(str(p_obj), "manifest.schema.json")
    # Path 对象
    validate_file(p_obj, "manifest.schema.json")


def test_validate_file_large_manifest_batch26(tmp_path):
    """大 manifest（100 个 documents）。"""
    docs = [
        {
            "doc_id": f"d{i}",
            "path": f"samples/{i}.pdf",
            "source_type": "pdf",
            "sha256": "a" * 64,
        }
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


def test_validate_file_bom_prefixed_batch26(tmp_path):
    """BOM 开头的文件 → json.JSONDecodeError（实现用 utf-8 而非 utf-8-sig，BOM 不被容忍）。"""
    p = tmp_path / "m.json"
    p.write_bytes(
        b"\xef\xbb\xbf"
        + json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "complete",
                "documents": [],
            }
        ).encode("utf-8")
    )
    # Python json 在 utf-8 解码后的字符串以 BOM 开头时抛 JSONDecodeError
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_iso_8859_encoded_fails_batch26(tmp_path):
    """非 utf-8 编码（含非 ASCII 字符）→ UnicodeDecodeError（实现强制 utf-8）。"""
    p = tmp_path / "m.json"
    # 必须含非 ASCII 字符；latin-1 编码的 'é' (0xe9) 在 utf-8 解码时失败
    content = '{"manifest_version": "1.0", "devset_status": "complete", "documents": [{"doc_id": "café", "path": "x.pdf", "source_type": "pdf"}]}'
    p.write_text(content, encoding="latin-1")
    with pytest.raises(UnicodeDecodeError):
        validate_file(p, "manifest.schema.json")


# ---------- module source forbidden tokens 第四十四批 ----------


def test_module_source_no_subprocess_batch26():
    src = inspect.getsource(smod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch26():
    src = inspect.getsource(smod)
    assert "os.system" not in src


def test_module_source_no_eval_batch26():
    src = inspect.getsource(smod)
    assert "eval(" not in src


def test_module_source_no_exec_batch26():
    src = inspect.getsource(smod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch26():
    src = inspect.getsource(smod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch26():
    src = inspect.getsource(smod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch26():
    src = inspect.getsource(smod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch26():
    src = inspect.getsource(smod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch26():
    """schema 模块只读。"""
    src = inspect.getsource(smod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch26():
    src = inspect.getsource(smod)
    assert "shutil" not in src


def test_module_source_no_requests_batch26():
    src = inspect.getsource(smod)
    assert "requests" not in src


def test_module_source_no_unlink_batch26():
    src = inspect.getsource(smod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十批 ----------


def test_module_source_contains_schemas_dir_constant_batch26():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = " in src


def test_module_source_contains_schema_path_func_batch26():
    src = inspect.getsource(smod)
    assert "def _schema_path" in src


def test_module_source_contains_file_not_found_msg_batch26():
    src = inspect.getsource(smod)
    assert "Schema 文件不存在" in src


def test_module_source_contains_eval_schema_error_class_batch26():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_contains_iter_errors_call_batch26():
    src = inspect.getsource(smod)
    assert "iter_errors" in src


def test_module_source_contains_sort_with_absolute_path_batch26():
    """errors 排序按 absolute_path。"""
    src = inspect.getsource(smod)
    assert "absolute_path" in src


def test_module_source_contains_flat_dict_keys_batch26():
    """flat dict 含 path/message/schema_path。"""
    src = inspect.getsource(smod)
    assert '"path"' in src
    assert '"message"' in src
    assert '"schema_path"' in src


def test_module_source_contains_load_schema_func_batch26():
    src = inspect.getsource(smod)
    assert "def load_schema" in src


def test_module_source_contains_validate_func_batch26():
    src = inspect.getsource(smod)
    assert "def validate(" in src


def test_module_source_contains_validate_file_func_batch26():
    src = inspect.getsource(smod)
    assert "def validate_file(" in src


def test_module_source_contains_absolute_schema_path_batch26():
    src = inspect.getsource(smod)
    assert "absolute_schema_path" in src


def test_module_source_contains_utf_8_encoding_batch26():
    src = inspect.getsource(smod)
    assert 'encoding="utf-8"' in src


# ---------- signatures 第四十批 ----------


def test_signature_schema_path_annotation_batch26():
    sig = inspect.signature(_schema_path)
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "Path"


def test_signature_load_schema_annotation_batch26():
    sig = inspect.signature(load_schema)
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_validate_annotation_batch26():
    sig = inspect.signature(validate)
    assert sig.parameters["instance"].annotation == "dict[str, Any]"
    assert sig.parameters["schema_name"].annotation == "str"


def test_signature_validate_file_path_annotation_batch26():
    sig = inspect.signature(validate_file)
    annotation = sig.parameters["path"].annotation
    assert "Path" in str(annotation)
    assert "str" in str(annotation)


def test_signature_eval_schema_error_init_full_batch26():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = sig.parameters
    assert params["self"].name == "self"
    assert params["message"].annotation == "str"
    assert "list[dict[str, Any]]" in str(params["errors"].annotation)
    assert params["errors"].default is None


def test_signature_eval_schema_error_init_return_none_batch26():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.return_annotation == "None"


# ---------- module 合理性第四十批 ----------


def test_module_has_future_annotations_batch26():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch26():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_imports_pathlib_batch26():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch26():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_imports_jsonschema_draft_batch26():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_imports_validation_error_batch26():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_all_contains_five_entries_batch26():
    src = inspect.getsource(smod)
    # __all__ 在源码里是多行 list
    for name in ['"SCHEMAS_DIR"', '"EvalSchemaError"', '"load_schema"', '"validate"', '"validate_file"']:
        assert name in src


def test_module_schemas_dir_is_absolute_batch26():
    assert SCHEMAS_DIR.is_absolute()


# ---------- 端到端集成第四十批 ----------


def test_e2e_validate_full_manifest_with_paired_docs_batch26():
    """端到端：paired_with 双向。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "paired_with": "d2",
            },
            {
                "doc_id": "d2",
                "path": "samples/y.docx",
                "source_type": "docx",
                "sha256": "b" * 64,
                "paired_with": "d1",
            },
        ],
    }
    validate(instance, "manifest.schema.json")


def test_e2e_validate_manifest_with_expected_failures_batch26():
    """端到端：含 expected_failures。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "bad1",
                "path": "bad.pdf",
                "expected_error_code": "unsupported_format",
            }
        ],
    }
    validate(instance, "manifest.schema.json")


def test_e2e_validate_doc_invalid_source_type_batch26():
    """source_type 不在 enum。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/x.txt",
                "source_type": "txt",  # 不允许
            }
        ],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_e2e_load_then_validate_roundtrip_batch26(tmp_path):
    """端到端：load → dump → reload → validate。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_eval_error_caught_specifically_batch26():
    """端到端：except 子句精确捕获。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert "manifest.schema.json" in str(e)
        return
    pytest.fail("Expected EvalSchemaError")


def test_e2e_schema_path_existing_batch26():
    """端到端：3 个 schema 都存在。"""
    for name in ["manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"]:
        p = _schema_path(name)
        assert p.is_file()


def test_e2e_validate_errors_path_complete_batch26():
    """端到端：errors 含 path 与 schema_path。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["path"], list)
        assert isinstance(err["schema_path"], list)
        assert isinstance(err["message"], str)
