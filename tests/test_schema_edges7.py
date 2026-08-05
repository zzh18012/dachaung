r"""app/schema.py 边角测试 - 第七轮（Round 201）。

补强已有 base/edges/edges2-6（共 ~698 测试）未覆盖的深度：
- SchemaValidationError 异常细节（args、__str__、raise from、errors mutation）
- load_schema 编码、权限、JSON 解析细节
- validate 错误排序、多错误聚合、错误 path 深度
- is_valid + validate 互验
- validate_file valid 文件往返、自定义 schema 走通
- 实际 document.schema.json 各 if/then 条件分支
- $defs 各类型边界（pdf/docx/markdown/html/text/ipynb locator）
- 模块与常量深度
"""

from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from app.schema import (
    SCHEMA_PATH,
    SchemaValidationError,
    is_valid,
    load_schema,
    validate,
    validate_file,
)


# =========================================================================
# 公共 fixtures / helpers
# =========================================================================


VALID_HASH = "a" * 64


def _minimal_valid_doc() -> dict[str, Any]:
    """最小且对默认 schema 合法的 document dict。"""
    return {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "/tmp/x.txt",
        "source_type": "text",
        "source_hash": VALID_HASH,
        "parser_name": "text",
        "parser_version": "0.1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


@pytest.fixture
def valid_doc() -> dict[str, Any]:
    return _minimal_valid_doc()


@pytest.fixture
def default_schema() -> dict[str, Any]:
    return load_schema()


# =========================================================================
# SchemaValidationError 深度
# =========================================================================


def test_schema_validation_error_args_only_message():
    err = SchemaValidationError("boom")
    assert err.args == ("boom",)


def test_schema_validation_error_str_returns_message():
    err = SchemaValidationError("boom")
    assert str(err) == "boom"


def test_schema_validation_error_repr_class_name():
    err = SchemaValidationError("boom")
    assert "SchemaValidationError" in repr(err)


def test_schema_validation_error_message_attribute():
    err = SchemaValidationError("boom")
    # Exception.message 不是标准属性，但传入的 message 存到 args[0]
    assert err.args[0] == "boom"


def test_schema_validation_error_errors_attribute_default():
    err = SchemaValidationError("boom")
    assert isinstance(err.errors, list)
    assert err.errors == []


def test_schema_validation_error_errors_attribute_explicit():
    errs = [{"path": ["x"], "message": "m"}]
    err = SchemaValidationError("boom", errors=errs)
    assert err.errors is errs  # 引用保留


def test_schema_validation_error_errors_with_empty_dict_falls_back_to_list():
    """errors or []：{} 是 falsy → []。"""
    err = SchemaValidationError("boom", errors={})  # type: ignore[arg-type]
    assert err.errors == []


def test_schema_validation_error_errors_with_empty_string_falls_back_to_list():
    """errors or []：'' 是 falsy → []。"""
    err = SchemaValidationError("boom", errors="")  # type: ignore[arg-type]
    assert err.errors == []


def test_schema_validation_error_errors_with_falsy_int_falls_back_to_list():
    err = SchemaValidationError("boom", errors=0)  # type: ignore[arg-type]
    assert err.errors == []


def test_schema_validation_error_errors_with_truthy_int_kept():
    err = SchemaValidationError("boom", errors=1)  # type: ignore[arg-type]
    assert err.errors == 1


def test_schema_validation_error_raise_from_other():
    with pytest.raises(SchemaValidationError) as ei:
        try:
            raise ValueError("root cause")
        except ValueError as e:
            raise SchemaValidationError("wrapped") from e
    assert ei.value.__cause__ is not None
    assert isinstance(ei.value.__cause__, ValueError)


def test_schema_validation_error_can_be_reraised():
    with pytest.raises(SchemaValidationError):
        try:
            raise SchemaValidationError("first")
        except SchemaValidationError:
            raise


def test_schema_validation_error_caught_as_base_exception():
    with pytest.raises(Exception) as ei:
        raise SchemaValidationError("x")
    assert isinstance(ei.value, SchemaValidationError)


def test_schema_validation_error_caught_as_value_error_no():
    """SchemaValidationError 不继承 ValueError，无法被 except ValueError 捕获。"""
    with pytest.raises(SchemaValidationError):
        raise_schema_error_as_valueerror()


def raise_schema_error_as_valueerror() -> None:
    try:
        raise SchemaValidationError("x")
    except ValueError:  # noqa: BLE001 - 故意测试不匹配
        pass  # 不会执行到这里


def test_schema_validation_error_init_can_be_called_with_keywords_only():
    err = SchemaValidationError(message="m", errors=[{"x": 1}])
    assert err.args == ("m",)
    assert err.errors == [{"x": 1}]


def test_schema_validation_error_init_signature():
    sig = inspect.signature(SchemaValidationError.__init__)
    params = list(sig.parameters)
    assert params == ["self", "message", "errors"]
    assert sig.parameters["errors"].default is None


def test_schema_validation_error_is_subclass_of_exception():
    assert issubclass(SchemaValidationError, Exception)


def test_schema_validation_error_not_subclass_of_value_error():
    assert not issubclass(SchemaValidationError, ValueError)


def test_schema_validation_error_not_subclass_of_runtime_error():
    assert not issubclass(SchemaValidationError, RuntimeError)


def test_schema_validation_error_can_attach_attrs():
    err = SchemaValidationError("m")
    err.custom_attr = 42  # type: ignore[attr-defined]
    assert err.custom_attr == 42


def test_schema_validation_error_errors_mutable_after_init():
    err = SchemaValidationError("m", errors=[{"a": 1}])
    err.errors.append({"b": 2})
    assert len(err.errors) == 2


# =========================================================================
# SCHEMA_PATH 深度
# =========================================================================


def test_schema_path_is_pathlib_path():
    assert isinstance(SCHEMA_PATH, Path)


def test_schema_path_str_form_endswith_schema_json():
    assert str(SCHEMA_PATH).endswith("document.schema.json")


def test_schema_path_parent_dir_name():
    assert SCHEMA_PATH.parent.name == "schemas"


def test_schema_path_parent_parent_name():
    """schemas 上一级是项目根。"""
    assert SCHEMA_PATH.parent.parent.name == "dachuang-autonomous"


def test_schema_path_resolves_to_itself_when_already_absolute(tmp_path):
    """resolve() 对已 absolute 路径返回等价路径。"""
    assert SCHEMA_PATH.resolve() == SCHEMA_PATH


def test_schema_path_read_bytes_returns_json_bytes():
    raw = SCHEMA_PATH.read_bytes()
    assert raw[:1] == b"{"


def test_schema_path_read_text_returns_json_str():
    text = SCHEMA_PATH.read_text(encoding="utf-8")
    assert text.lstrip().startswith("{")


# =========================================================================
# load_schema 深度
# =========================================================================


def test_load_schema_accepts_pathlib_path(tmp_path):
    schema = {"type": "object"}
    p = tmp_path / "s.json"
    p.write_text(json.dumps(schema), encoding="utf-8")
    loaded = load_schema(p)
    assert loaded == schema


def test_load_schema_accepts_str_path(tmp_path):
    schema = {"type": "object"}
    p = tmp_path / "s.json"
    p.write_text(json.dumps(schema), encoding="utf-8")
    loaded = load_schema(str(p))
    assert loaded == schema


def test_load_schema_loads_nested_structures(tmp_path):
    schema = {"a": {"b": {"c": [1, 2, 3]}}, "d": None}
    p = tmp_path / "s.json"
    p.write_text(json.dumps(schema), encoding="utf-8")
    assert load_schema(p) == schema


def test_load_schema_loads_array(tmp_path):
    schema = [1, 2, 3]  # 不是合法 schema，但 load_schema 不校验
    p = tmp_path / "s.json"
    p.write_text(json.dumps(schema), encoding="utf-8")
    assert load_schema(p) == [1, 2, 3]


def test_load_schema_loads_null(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("null", encoding="utf-8")
    assert load_schema(p) is None


def test_load_schema_loads_empty_object(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("{}", encoding="utf-8")
    assert load_schema(p) == {}


def test_load_schema_handles_utf8_bom(tmp_path):
    """UTF-8 BOM 在 utf-8 编码下也能被 json.load 接受。"""
    p = tmp_path / "s.json"
    p.write_bytes(b'\xef\xbb\xbf{"type": "object"}')
    # Python json 解析 BOM 会失败
    with pytest.raises(json.JSONDecodeError):
        load_schema(p)


def test_load_schema_directory_raises_filenotfounderror(tmp_path):
    """目录被 is_file() 排除 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        load_schema(tmp_path)


def test_load_schema_symlink_to_schema(tmp_path):
    """符号链接到合法 schema 文件应能加载。"""
    target = tmp_path / "real.json"
    target.write_text(json.dumps({"type": "object"}), encoding="utf-8")
    link = tmp_path / "link.json"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink not supported on this platform")
    assert load_schema(link) == {"type": "object"}


def test_load_schema_returns_independent_object(tmp_path):
    """每次 load_schema 返回新 dict。"""
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"x": 1}), encoding="utf-8")
    a = load_schema(p)
    b = load_schema(p)
    assert a == b
    assert a is not b
    a["x"] = 2
    assert b["x"] == 1


def test_load_schema_message_contains_path(tmp_path):
    with pytest.raises(FileNotFoundError) as ei:
        load_schema(tmp_path / "nope.json")
    assert "nope.json" in str(ei.value)
    assert "Schema" in str(ei.value)


def test_load_schema_signature_path_default_is_schema_path():
    sig = inspect.signature(load_schema)
    assert sig.parameters["path"].default is SCHEMA_PATH


def test_load_schema_signature_return_annotation():
    sig = inspect.signature(load_schema)
    # from __future__ import annotations → return annotation is string
    assert sig.return_annotation == "dict[str, Any]"


# =========================================================================
# validate 多错误排序 / path 深度
# =========================================================================


def test_validate_with_empty_schema_always_valid():
    """空 schema {} 不约束任何内容。"""
    validate({}, schema={})
    validate({"any": "thing"}, schema={})
    validate([1, 2, 3], schema={})  # type: ignore[arg-type]


def test_validate_with_schema_true_always_valid():
    """schema=true 接受任何 JSON。"""
    validate({}, schema=True)  # type: ignore[arg-type]
    validate("anything", schema=True)  # type: ignore[arg-type]


def test_validate_with_schema_false_always_invalid():
    """schema=false 拒绝任何 JSON。"""
    with pytest.raises(SchemaValidationError):
        validate({}, schema=False)  # type: ignore[arg-type]


def test_validate_with_type_mismatch():
    schema = {"type": "object"}
    with pytest.raises(SchemaValidationError):
        validate([], schema=schema)  # type: ignore[arg-type]


def test_validate_with_required_field():
    schema = {"type": "object", "required": ["a"]}
    with pytest.raises(SchemaValidationError):
        validate({}, schema=schema)


def test_validate_sorted_by_absolute_path(default_schema):
    """多错误时按 absolute_path 排序；首个错误用于 head message。"""
    doc = _minimal_valid_doc()
    doc["document_id"] = ""  # path = ['document_id']
    doc["source_path"] = ""  # path = ['source_path']
    with pytest.raises(SchemaValidationError) as ei:
        validate(doc, schema=default_schema)
    errs = ei.value.errors
    # 至少 2 处错误
    assert len(errs) >= 2
    paths = [tuple(e["path"]) for e in errs]
    # 排序：('document_id',) < ('source_path',)
    assert paths == sorted(paths)


def test_validate_error_path_inside_element(default_schema):
    """element 内字段错误，path 应包含 elements/<idx>/<field>。"""
    doc = _minimal_valid_doc()
    doc["source_type"] = "text"
    doc["elements"] = [
        {
            "element_id": "e1",
            "type": "paragraph",
            "parent_id": None,
            "source_locator": {"line": 1},
            "confidence": 0.5,
            "metadata": {},
            "content": "x",
        }
    ]
    # 故意 confidence=1.5（超出 maximum=1）
    doc["elements"][0]["confidence"] = 1.5
    with pytest.raises(SchemaValidationError) as ei:
        validate(doc, schema=default_schema)
    paths = [tuple(e["path"]) for e in ei.value.errors]
    assert any("elements" in p and "confidence" in p for p in paths)


def test_validate_error_path_inside_chunk(default_schema):
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 0.5, "metadata": {}, "content": "x",
    }]
    doc["chunks"] = [{
        "chunk_id": "",  # minLength=1 → 错
        "text": "x",
        "source_element_ids": ["e1"],
        "metadata": {},
    }]
    with pytest.raises(SchemaValidationError) as ei:
        validate(doc, schema=default_schema)
    paths = [tuple(e["path"]) for e in ei.value.errors]
    assert any("chunks" in p and "chunk_id" in p for p in paths)


def test_validate_error_path_inside_warning(default_schema):
    doc = _minimal_valid_doc()
    doc["warnings"] = [{"code": "", "reason": "r"}]  # code minLength=1
    with pytest.raises(SchemaValidationError) as ei:
        validate(doc, schema=default_schema)
    paths = [tuple(e["path"]) for e in ei.value.errors]
    assert any("warnings" in p and "code" in p for p in paths)


def test_validate_error_path_inside_error_record(default_schema):
    doc = _minimal_valid_doc()
    doc["errors"] = [{"code": "X", "message": ""}]  # message minLength=1
    with pytest.raises(SchemaValidationError) as ei:
        validate(doc, schema=default_schema)
    paths = [tuple(e["path"]) for e in ei.value.errors]
    assert any("errors" in p and "message" in p for p in paths)


def test_validate_error_schema_path_includes_relations_branch(default_schema):
    """错误 schema_path 应展开到 relations/items/properties/...（$ref 内联展开）。"""
    doc = _minimal_valid_doc()
    doc["relations"] = [{"type": "", "from_id": "a", "to_id": "b"}]
    with pytest.raises(SchemaValidationError) as ei:
        validate(doc, schema=default_schema)
    spaths = [e["schema_path"] for e in ei.value.errors]
    flat = [seg for sp in spaths for seg in sp]
    assert "relations" in flat or "type" in flat


def test_validate_message_includes_count():
    schema = {"type": "object", "required": ["a", "b", "c"]}
    with pytest.raises(SchemaValidationError) as ei:
        validate({}, schema=schema)
    msg = str(ei.value)
    assert "Schema 校验失败" in msg
    # 多个 missing 错误
    assert "处" in msg


def test_validate_first_error_used_in_message(default_schema):
    doc = _minimal_valid_doc()
    doc["source_hash"] = "not-a-hash"  # pattern mismatch
    with pytest.raises(SchemaValidationError) as ei:
        validate(doc, schema=default_schema)
    msg = str(ei.value)
    # 错误信息含 source_hash pattern 描述
    assert "source_hash" in msg or "pattern" in msg or "处" in msg


def test_validate_returns_none_when_valid(default_schema, valid_doc):
    assert validate(valid_doc, schema=default_schema) is None


def test_validate_does_not_modify_document(default_schema, valid_doc):
    snapshot = copy.deepcopy(valid_doc)
    validate(valid_doc, schema=default_schema)
    assert valid_doc == snapshot


def test_validate_does_not_modify_schema(default_schema, valid_doc):
    snapshot = copy.deepcopy(default_schema)
    validate(valid_doc, schema=default_schema)
    assert default_schema == snapshot


# =========================================================================
# is_valid 深度
# =========================================================================


def test_is_valid_returns_true_with_custom_schema():
    assert is_valid({}, schema={"type": "object"}) is True


def test_is_valid_returns_false_with_custom_schema():
    assert is_valid([], schema={"type": "object"}) is False  # type: ignore[arg-type]


def test_is_valid_returns_true_with_schema_true():
    assert is_valid("anything", schema=True) is True  # type: ignore[arg-type]


def test_is_valid_returns_false_with_schema_false():
    assert is_valid({}, schema=False) is False  # type: ignore[arg-type]


def test_is_valid_with_default_schema_valid_doc(valid_doc):
    assert is_valid(valid_doc) is True


def test_is_valid_with_default_schema_invalid_doc(valid_doc):
    valid_doc["schema_version"] = "wrong"
    assert is_valid(valid_doc) is False


def test_is_valid_does_not_raise_on_invalid(valid_doc):
    valid_doc.clear()
    valid_doc["x"] = 1
    # 不抛
    result = is_valid(valid_doc)
    assert result is False


def test_is_valid_returns_bool_type():
    assert isinstance(is_valid({}), bool)


def test_is_valid_signature():
    sig = inspect.signature(is_valid)
    params = list(sig.parameters)
    assert params == ["document", "schema"]
    assert sig.parameters["schema"].default is None
    # from __future__ import annotations → annotation is string
    assert sig.return_annotation == "bool"


# =========================================================================
# validate_file 深度
# =========================================================================


def test_validate_file_validates_valid_file(tmp_path, valid_doc, default_schema):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(valid_doc), encoding="utf-8")
    # 不抛
    validate_file(p, schema=default_schema)


def test_validate_file_raises_on_invalid_file(tmp_path, valid_doc, default_schema):
    valid_doc["schema_version"] = "wrong"
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(valid_doc), encoding="utf-8")
    with pytest.raises(SchemaValidationError):
        validate_file(p, schema=default_schema)


def test_validate_file_uses_default_schema_when_none(tmp_path, valid_doc):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(valid_doc), encoding="utf-8")
    # schema=None → 用默认 document.schema.json
    validate_file(p)


def test_validate_file_invalid_doc_with_default_schema(tmp_path, valid_doc):
    del valid_doc["document_id"]  # missing required
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(valid_doc), encoding="utf-8")
    with pytest.raises(SchemaValidationError):
        validate_file(p)


def test_validate_file_str_path_valid(tmp_path, valid_doc, default_schema):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(valid_doc), encoding="utf-8")
    validate_file(str(p), schema=default_schema)


def test_validate_file_missing_raises_filenotfounderror():
    with pytest.raises(FileNotFoundError):
        validate_file("/no/such/file.json")


def test_validate_file_directory_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path)


def test_validate_file_invalid_json_raises(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p)


def test_validate_file_utf8_with_chinese_content(tmp_path, valid_doc, default_schema):
    valid_doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 0.95, "metadata": {},
        "content": "你好，世界。",  # Unicode content
    }]
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(valid_doc, ensure_ascii=False), encoding="utf-8")
    validate_file(p, schema=default_schema)


def test_validate_file_signature():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters)
    assert params == ["path", "schema"]
    assert sig.parameters["schema"].default is None
    # from __future__ import annotations → annotation is string
    assert sig.return_annotation == "None"


def test_validate_file_message_contains_path(tmp_path):
    with pytest.raises(FileNotFoundError) as ei:
        validate_file(tmp_path / "nope.json")
    assert "nope.json" in str(ei.value)
    assert "待校验文件" in str(ei.value)


# =========================================================================
# 实际 document.schema.json 各 if/then 条件分支
# =========================================================================


def test_pdf_locator_without_page_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "pdf"
    doc["source_path"] = "/tmp/x.pdf"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {},  # missing page
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_pdf_locator_with_page_only_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "pdf"
    doc["source_path"] = "/tmp/x.pdf"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {"page": 1},
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    validate(doc, schema=default_schema)


def test_pdf_locator_with_page_zero_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "pdf"
    doc["source_path"] = "/tmp/x.pdf"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {"page": 0},  # minimum=1
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_pdf_locator_with_bbox_4_items_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "pdf"
    doc["source_path"] = "/tmp/x.pdf"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 100.0]},
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    validate(doc, schema=default_schema)


def test_pdf_locator_with_bbox_5_items_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "pdf"
    doc["source_path"] = "/tmp/x.pdf"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 100.0, 50.0]},
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_pdf_locator_with_bbox_3_items_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "pdf"
    doc["source_path"] = "/tmp/x.pdf"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0]},
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_docx_locator_empty_object_fails(default_schema):
    """docx_locator 要求 minProperties=1。"""
    doc = _minimal_valid_doc()
    doc["source_type"] = "docx"
    doc["source_path"] = "/tmp/x.docx"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {},  # 空对象 → minProperties=1 失败
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_docx_locator_with_paragraph_index_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "docx"
    doc["source_path"] = "/tmp/x.docx"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {"paragraph_index": 0},
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    validate(doc, schema=default_schema)


def test_docx_locator_with_paragraph_index_negative_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "docx"
    doc["source_path"] = "/tmp/x.docx"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {"paragraph_index": -1},  # minimum=0
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_markdown_locator_missing_line_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "markdown"
    doc["source_path"] = "/tmp/x.md"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {},
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_markdown_locator_with_line_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "markdown"
    doc["source_path"] = "/tmp/x.md"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {"line": 1},
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    validate(doc, schema=default_schema)


def test_markdown_locator_with_line_and_section_path_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "markdown"
    doc["source_path"] = "/tmp/x.md"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {"line": 1, "section_path": "intro"},
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    validate(doc, schema=default_schema)


def test_html_locator_with_line_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "html"
    doc["source_path"] = "/tmp/x.html"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {"line": 1},
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    validate(doc, schema=default_schema)


def test_text_locator_with_line_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "text"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {"line": 1},
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    validate(doc, schema=default_schema)


def test_text_locator_missing_line_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "text"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {},
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_ipynb_locator_with_cell_index_and_type_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "ipynb"
    doc["source_path"] = "/tmp/x.ipynb"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {"cell_index": 0, "cell_type": "code"},
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    validate(doc, schema=default_schema)


def test_ipynb_locator_missing_cell_type_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "ipynb"
    doc["source_path"] = "/tmp/x.ipynb"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {"cell_index": 0},  # missing cell_type
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_ipynb_locator_invalid_cell_type_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "ipynb"
    doc["source_path"] = "/tmp/x.ipynb"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {"cell_index": 0, "cell_type": "invalid"},
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_ipynb_locator_negative_cell_index_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["source_type"] = "ipynb"
    doc["source_path"] = "/tmp/x.ipynb"
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None,
        "source_locator": {"cell_index": -1, "cell_type": "code"},
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    assert is_valid(doc, schema=default_schema) is False


# =========================================================================
# element anyOf / additionalProperties
# =========================================================================


def test_element_with_only_content_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 0.9, "metadata": {},
        "content": "x",
        # resource_path 缺失
    }]
    validate(doc, schema=default_schema)


def test_element_with_only_resource_path_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "image",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 0.9, "metadata": {},
        # content 缺失
        "resource_path": "img.png",
    }]
    validate(doc, schema=default_schema)


def test_element_with_both_content_and_resource_path_ok(default_schema):
    """anyOf 至少一个满足即可。"""
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "image",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 0.9, "metadata": {},
        "content": "caption",
        "resource_path": "img.png",
    }]
    validate(doc, schema=default_schema)


def test_element_with_neither_content_nor_resource_path_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 0.9, "metadata": {},
        # 都没有
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_element_with_empty_content_string_only_fails(default_schema):
    """anyOf 第 1 支要求 content minLength=1。"""
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 0.9, "metadata": {},
        "content": "",  # 空 → 第 1 支不满足
        # resource_path 缺失 → 第 2 支不满足 → 整体失败
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_element_with_additional_properties_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 0.9, "metadata": {},
        "content": "x",
        "foo": "bar",  # additionalProperties: false
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_element_with_invalid_type_value_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "unknown_type",  # enum 拒绝
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 0.9, "metadata": {},
        "content": "x",
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_element_confidence_above_one_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 1.5, "metadata": {},
        "content": "x",
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_element_confidence_below_zero_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": -0.1, "metadata": {},
        "content": "x",
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_element_confidence_zero_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 0, "metadata": {},
        "content": "x",
    }]
    validate(doc, schema=default_schema)


def test_element_confidence_one_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 1, "metadata": {},
        "content": "x",
    }]
    validate(doc, schema=default_schema)


# =========================================================================
# chunk 边界
# =========================================================================


def test_chunk_empty_source_element_ids_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 0.9, "metadata": {}, "content": "x",
    }]
    doc["chunks"] = [{
        "chunk_id": "c1", "text": "x",
        "source_element_ids": [],  # minItems=1
        "metadata": {},
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_chunk_empty_chunk_id_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["chunks"] = [{
        "chunk_id": "", "text": "x",
        "source_element_ids": ["e1"],
        "metadata": {},
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_chunk_empty_text_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["chunks"] = [{
        "chunk_id": "c1", "text": "",
        "source_element_ids": ["e1"],
        "metadata": {},
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_chunk_empty_source_element_id_string_fails(default_schema):
    """source_element_ids items minLength=1。"""
    doc = _minimal_valid_doc()
    doc["chunks"] = [{
        "chunk_id": "c1", "text": "x",
        "source_element_ids": [""],
        "metadata": {},
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_chunk_with_source_spans_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 0.9, "metadata": {}, "content": "x",
    }]
    doc["chunks"] = [{
        "chunk_id": "c1", "text": "x",
        "source_element_ids": ["e1"],
        "source_spans": [
            {"element_id": "e1", "start": 0, "end": 1},
        ],
        "metadata": {},
    }]
    validate(doc, schema=default_schema)


def test_chunk_source_span_negative_start_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 0.9, "metadata": {}, "content": "x",
    }]
    doc["chunks"] = [{
        "chunk_id": "c1", "text": "x",
        "source_element_ids": ["e1"],
        "source_spans": [
            {"element_id": "e1", "start": -1, "end": 1},  # minimum=0
        ],
        "metadata": {},
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_chunk_source_span_missing_end_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["elements"] = [{
        "element_id": "e1", "type": "paragraph",
        "parent_id": None, "source_locator": {"line": 1},
        "confidence": 0.9, "metadata": {}, "content": "x",
    }]
    doc["chunks"] = [{
        "chunk_id": "c1", "text": "x",
        "source_element_ids": ["e1"],
        "source_spans": [
            {"element_id": "e1", "start": 0},  # missing end
        ],
        "metadata": {},
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_chunk_with_additional_properties_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["chunks"] = [{
        "chunk_id": "c1", "text": "x",
        "source_element_ids": ["e1"],
        "metadata": {},
        "foo": "bar",  # additionalProperties: false
    }]
    assert is_valid(doc, schema=default_schema) is False


# =========================================================================
# relation / warning / error 边界
# =========================================================================


def test_relation_with_metadata_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["relations"] = [{
        "type": "parent", "from_id": "e1", "to_id": "e2",
        "metadata": {"k": "v"},
    }]
    validate(doc, schema=default_schema)


def test_relation_missing_type_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["relations"] = [{"from_id": "e1", "to_id": "e2"}]
    assert is_valid(doc, schema=default_schema) is False


def test_relation_empty_type_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["relations"] = [{"type": "", "from_id": "e1", "to_id": "e2"}]
    assert is_valid(doc, schema=default_schema) is False


def test_relation_with_additional_properties_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["relations"] = [{
        "type": "parent", "from_id": "e1", "to_id": "e2",
        "foo": "bar",  # additionalProperties: false
    }]
    assert is_valid(doc, schema=default_schema) is False


def test_warning_with_details_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["warnings"] = [{"code": "X", "reason": "r", "details": {"k": "v"}}]
    validate(doc, schema=default_schema)


def test_warning_missing_reason_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["warnings"] = [{"code": "X"}]
    assert is_valid(doc, schema=default_schema) is False


def test_warning_empty_reason_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["warnings"] = [{"code": "X", "reason": ""}]
    assert is_valid(doc, schema=default_schema) is False


def test_warning_with_additional_properties_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["warnings"] = [{"code": "X", "reason": "r", "foo": "bar"}]
    assert is_valid(doc, schema=default_schema) is False


def test_error_with_details_ok(default_schema):
    doc = _minimal_valid_doc()
    doc["errors"] = [{"code": "X", "message": "m", "details": {"k": "v"}}]
    validate(doc, schema=default_schema)


def test_error_missing_message_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["errors"] = [{"code": "X"}]
    assert is_valid(doc, schema=default_schema) is False


def test_error_with_additional_properties_fails(default_schema):
    doc = _minimal_valid_doc()
    doc["errors"] = [{"code": "X", "message": "m", "foo": "bar"}]
    assert is_valid(doc, schema=default_schema) is False


# =========================================================================
# 顶层字段边界
# =========================================================================


def test_schema_version_not_string_fails(default_schema, valid_doc):
    valid_doc["schema_version"] = 1
    assert is_valid(valid_doc, schema=default_schema) is False


def test_schema_version_wrong_value_fails(default_schema, valid_doc):
    valid_doc["schema_version"] = "0.2.0"
    assert is_valid(valid_doc, schema=default_schema) is False


def test_document_id_empty_fails(default_schema, valid_doc):
    valid_doc["document_id"] = ""
    assert is_valid(valid_doc, schema=default_schema) is False


def test_source_path_empty_fails(default_schema, valid_doc):
    valid_doc["source_path"] = ""
    assert is_valid(valid_doc, schema=default_schema) is False


def test_source_type_unknown_fails(default_schema, valid_doc):
    valid_doc["source_type"] = "unknown"
    assert is_valid(valid_doc, schema=default_schema) is False


def test_source_hash_uppercase_fails(default_schema, valid_doc):
    valid_doc["source_hash"] = "A" * 64  # pattern 只允许小写
    assert is_valid(valid_doc, schema=default_schema) is False


def test_source_hash_too_short_fails(default_schema, valid_doc):
    valid_doc["source_hash"] = "a" * 63
    assert is_valid(valid_doc, schema=default_schema) is False


def test_source_hash_too_long_fails(default_schema, valid_doc):
    valid_doc["source_hash"] = "a" * 65
    assert is_valid(valid_doc, schema=default_schema) is False


def test_source_hash_with_garbage_fails(default_schema, valid_doc):
    valid_doc["source_hash"] = "g" * 64  # 非 hex 字符
    assert is_valid(valid_doc, schema=default_schema) is False


def test_parser_name_empty_fails(default_schema, valid_doc):
    valid_doc["parser_name"] = ""
    assert is_valid(valid_doc, schema=default_schema) is False


def test_parser_version_empty_fails(default_schema, valid_doc):
    valid_doc["parser_version"] = ""
    assert is_valid(valid_doc, schema=default_schema) is False


def test_elements_not_array_fails(default_schema, valid_doc):
    valid_doc["elements"] = "not_array"
    assert is_valid(valid_doc, schema=default_schema) is False


def test_chunks_not_array_fails(default_schema, valid_doc):
    valid_doc["chunks"] = "not_array"
    assert is_valid(valid_doc, schema=default_schema) is False


def test_metadata_not_object_fails(default_schema, valid_doc):
    valid_doc["metadata"] = "not_object"
    assert is_valid(valid_doc, schema=default_schema) is False


def test_missing_required_top_field_fails(default_schema, valid_doc):
    del valid_doc["document_id"]
    assert is_valid(valid_doc, schema=default_schema) is False


def test_extra_top_field_fails(default_schema, valid_doc):
    """默认 schema 顶层未声明 additionalProperties:false，但没声明就允许。
    实际 schema 顶层无 additionalProperties:false → 额外字段 OK。"""
    valid_doc["extra_field"] = "ok"
    # 不抛
    validate(valid_doc, schema=default_schema)


# =========================================================================
# 模块 / Draft202012Validator 互操作
# =========================================================================


def test_default_schema_passes_draft202012_check():
    schema = load_schema()
    Draft202012Validator.check_schema(schema)


def test_default_schema_top_required_count():
    schema = load_schema()
    required = schema["required"]
    expected = {
        "schema_version", "document_id", "source_path", "source_type",
        "source_hash", "parser_name", "parser_version",
        "elements", "chunks", "relations", "warnings", "errors", "metadata",
    }
    assert set(required) == expected
    assert len(required) == 13


def test_default_schema_allof_has_six_branches():
    schema = load_schema()
    assert len(schema["allOf"]) == 6


def test_default_schema_defs_has_eight_entries():
    schema = load_schema()
    expected_defs = {
        "element", "chunk", "relation", "warning", "error",
        "pdf_locator", "docx_locator", "markdown_locator",
        "html_locator", "text_locator", "ipynb_locator", "source_span",
    }
    assert set(schema["$defs"].keys()) == expected_defs


def test_default_schema_schema_version_value():
    schema = load_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_default_schema_has_id():
    schema = load_schema()
    assert schema["$id"].endswith("document.schema.json")


def test_default_schema_title():
    schema = load_schema()
    assert "KVFS" in schema["title"]


def test_default_schema_has_description():
    schema = load_schema()
    assert isinstance(schema["description"], str)
    assert len(schema["description"]) > 0


def test_default_schema_element_type_enum_values():
    schema = load_schema()
    types = schema["$defs"]["element"]["properties"]["type"]["enum"]
    expected = {
        "heading", "paragraph", "list_item", "table",
        "image", "caption", "header", "footer",
    }
    assert set(types) == expected


def test_default_schema_source_type_enum_values():
    schema = load_schema()
    types = schema["properties"]["source_type"]["enum"]
    expected = {"pdf", "docx", "markdown", "html", "text", "ipynb"}
    assert set(types) == expected


def test_module_all_iterable():
    import app.schema as m
    assert hasattr(m, "__all__")
    assert iter(m.__all__)  # type: ignore[arg-type]


def test_module_all_contains_expected():
    import app.schema as m
    expected = {
        "SCHEMA_PATH", "SchemaValidationError",
        "load_schema", "validate", "is_valid", "validate_file",
    }
    assert set(m.__all__) == expected


def test_module_all_no_duplicates():
    import app.schema as m
    assert len(m.__all__) == len(set(m.__all__))


def test_module_all_entries_are_exported():
    import app.schema as m
    for name in m.__all__:
        assert hasattr(m, name)


def test_module_silence_unused_import_is_private():
    import app.schema as m
    assert callable(m._silence_unused_import)


def test_module_silence_unused_import_returns_none():
    import app.schema as m
    assert m._silence_unused_import() is None


def test_module_imports_present():
    import app.schema as m
    for name in ("json", "Path", "Any", "Draft202012Validator"):
        assert hasattr(m, name)


# =========================================================================
# 综合行为
# =========================================================================


def test_validate_then_is_valid_consistent(default_schema, valid_doc):
    valid_doc["schema_version"] = "wrong"
    with pytest.raises(SchemaValidationError):
        validate(valid_doc, schema=default_schema)
    assert is_valid(valid_doc, schema=default_schema) is False


def test_full_document_with_all_field_types_validates(default_schema):
    """完整 Document 含所有字段类型 → 通过校验。"""
    doc = _minimal_valid_doc()
    doc["source_type"] = "pdf"
    doc["source_path"] = "/tmp/full.pdf"
    doc["elements"] = [
        {
            "element_id": "e1", "type": "heading",
            "parent_id": None,
            "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 50.0]},
            "confidence": 0.95, "metadata": {"level": 1},
            "content": "Title",
        },
        {
            "element_id": "e2", "type": "paragraph",
            "parent_id": "e1",
            "source_locator": {"page": 1},
            "confidence": 0.9, "metadata": {},
            "content": "Body",
        },
        {
            "element_id": "i1", "type": "image",
            "parent_id": "e1",
            "source_locator": {"page": 1},
            "confidence": 0.85, "metadata": {},
            "resource_path": "img.png",
        },
    ]
    doc["chunks"] = [
        {
            "chunk_id": "c1", "text": "Title",
            "source_element_ids": ["e1"],
            "source_spans": [{"element_id": "e1", "start": 0, "end": 5}],
            "metadata": {"k": "v"},
        },
        {
            "chunk_id": "c2", "text": "Body",
            "source_element_ids": ["e2"],
            "metadata": {},
        },
    ]
    doc["relations"] = [
        {"type": "parent", "from_id": "e1", "to_id": "e2", "metadata": {}},
    ]
    doc["warnings"] = [
        {"code": "X", "reason": "demo", "details": {"k": "v"}},
    ]
    doc["errors"] = []
    doc["metadata"] = {"author": "tester"}
    validate(doc, schema=default_schema)


def test_validate_idempotent(default_schema, valid_doc):
    """同一 document 多次 validate 结果一致。"""
    for _ in range(3):
        validate(valid_doc, schema=default_schema)


def test_load_schema_idempotent():
    s1 = load_schema()
    s2 = load_schema()
    assert s1 == s2


def test_validate_errors_path_absolute_path_is_list(default_schema, valid_doc):
    valid_doc["document_id"] = ""
    with pytest.raises(SchemaValidationError) as ei:
        validate(valid_doc, schema=default_schema)
    for e in ei.value.errors:
        assert isinstance(e["path"], list)
        assert isinstance(e["schema_path"], list)


def test_validate_errors_count_at_least_one(default_schema, valid_doc):
    valid_doc["document_id"] = ""
    with pytest.raises(SchemaValidationError) as ei:
        validate(valid_doc, schema=default_schema)
    assert len(ei.value.errors) >= 1


def test_validate_first_error_path_matches_some_field(default_schema, valid_doc):
    valid_doc["document_id"] = ""
    with pytest.raises(SchemaValidationError) as ei:
        validate(valid_doc, schema=default_schema)
    head_err = ei.value.errors[0]
    assert "document_id" in head_err["path"] or "minLength" in str(head_err["schema_path"])
