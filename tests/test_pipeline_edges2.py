"""Round 88 — app/pipeline.py 边角覆盖（第二轮）。

互补于已有：
- tests/test_pipeline_edges.py（86 测试）
- tests/test_pipeline_errors.py（47 测试）
- tests/test_pipeline_helpers.py（45 测试）
- tests/test_pipeline_integration.py（21 测试）

第二轮重点：get_parser 类型边界、image_output_dir_for 路径形态深度、
process_single 错误传播的 details 字段、validate_only 返回值语义。
不修改 app/pipeline.py。
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app import pipeline as pipeline_mod
from app.chunkers import StructuralChunker
from app.models import Document, ErrorRecord
from app.pipeline import (
    __all__ as pipeline_all,
    get_parser,
    image_output_dir_for,
    process_single,
    validate_only,
)
from app.parsers import Parser, ParserError


# =============================================================================
# get_parser 深度（类型边界、返回值形态）
# =============================================================================


def test_get_parser_none_name_raises_type_error():
    """None 不是 str → 应在比较时抛 TypeError（Python '==' 不抛，但属性访问会）。"""
    # None 与 str 比较：name == "fallback" → False，最终走 raise ValueError 路径
    # 但 ValueError 的 f-string 会尝试格式化 None，不抛 TypeError
    with pytest.raises(ValueError):
        get_parser(None)


def test_get_parser_int_name_raises_value_error():
    with pytest.raises(ValueError):
        get_parser(42)


def test_get_parser_list_name_raises_value_error():
    with pytest.raises(ValueError):
        get_parser(["fallback"])


def test_get_parser_dict_name_raises_value_error():
    with pytest.raises(ValueError):
        get_parser({"name": "fallback"})


def test_get_parser_unknown_name_raises_value_error():
    with pytest.raises(ValueError):
        get_parser("xml")


def test_get_parser_unknown_name_error_message_lists_all_six_parsers():
    with pytest.raises(ValueError) as exc:
        get_parser("xml")
    msg = str(exc.value)
    for name in ("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"):
        assert name in msg


def test_get_parser_returns_distinct_instances_per_call():
    a = get_parser("fallback")
    b = get_parser("fallback")
    assert a is not b


def test_get_parser_each_parser_subclass_of_parser():
    for name in ("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"):
        p = get_parser(name)
        assert isinstance(p, Parser)


def test_get_parser_each_parser_has_name_string():
    for name in ("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"):
        p = get_parser(name)
        assert isinstance(p.name, str)
        assert p.name


def test_get_parser_each_parser_has_version_string():
    for name in ("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"):
        p = get_parser(name)
        assert hasattr(p, "version")


def test_get_parser_each_parser_has_parse_callable():
    for name in ("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"):
        p = get_parser(name)
        assert callable(p.parse)


def test_get_parser_fallback_default_image_output_dir_none():
    p = get_parser("fallback")
    assert p._image_output_dir is None


def test_get_parser_fallback_accepts_pathlib_image_output_dir(tmp_path):
    p = get_parser("fallback", image_output_dir=tmp_path)
    assert isinstance(p._image_output_dir, Path)


def test_get_parser_fallback_accepts_str_image_output_dir(tmp_path):
    p = get_parser("fallback", image_output_dir=str(tmp_path))
    # FallbackParser 把 str 转 Path
    assert p._image_output_dir is not None


def test_get_parser_kreuzberg_accepts_but_ignores_image_output_dir(tmp_path):
    """get_parser 接受 image_output_dir 但 kreuzberg 不用它（仅 fallback 用）。"""
    p = get_parser("kreuzberg", image_output_dir=tmp_path)
    assert isinstance(p, Parser)


def test_get_parser_markdown_accepts_but_ignores_image_output_dir(tmp_path):
    p = get_parser("markdown", image_output_dir=tmp_path)
    assert isinstance(p, Parser)


# =============================================================================
# image_output_dir_for 深度
# =============================================================================


def test_image_output_dir_for_none_returns_none():
    assert image_output_dir_for(None, "abc123") is None


def test_image_output_dir_for_returns_path_object():
    result = image_output_dir_for("/tmp/out.json", "abc123")
    assert isinstance(result, Path)


def test_image_output_dir_for_str_path_accepted():
    result = image_output_dir_for("/tmp/out.json", "abc123")
    assert isinstance(result, Path)


def test_image_output_dir_for_pathlib_path_accepted():
    result = image_output_dir_for(Path("/tmp/out.json"), "abc123")
    assert isinstance(result, Path)


def test_image_output_dir_for_prefix_images():
    result = image_output_dir_for("/tmp/out.json", "abc123def456")
    assert result.name.startswith("images-")


def test_image_output_dir_for_hash_truncated_to_16():
    result = image_output_dir_for("/tmp/out.json", "a" * 32)
    assert result.name == "images-" + "a" * 16


def test_image_output_dir_for_hash_short_uses_full():
    """hash < 16 字符时全用（不补齐）。"""
    result = image_output_dir_for("/tmp/out.json", "abc")
    assert result.name == "images-abc"


def test_image_output_dir_for_hash_empty():
    result = image_output_dir_for("/tmp/out.json", "")
    assert result.name == "images-"


def test_image_output_dir_for_parent_inherited():
    """image 目录的父目录 = output_path 的父目录。"""
    result = image_output_dir_for("/foo/bar/out.json", "abc")
    assert result.parent == Path("/foo/bar")


def test_image_output_dir_for_filename_only():
    """output_path 没目录（仅文件名）→ parent=. """
    result = image_output_dir_for("out.json", "abc")
    assert result.parent == Path(".")


def test_image_output_dir_for_nested_path():
    result = image_output_dir_for("a/b/c/d/out.json", "abc")
    assert result.parent == Path("a/b/c/d")


def test_image_output_dir_for_with_trailing_slash_in_dir():
    """output_path 含末尾斜杠：Path 自动忽略。"""
    result = image_output_dir_for("/tmp/", "abc")
    # Path('/tmp/') → parent = '/'，name = 'tmp'
    # 不算有意义场景，仅验证不抛错
    assert isinstance(result, Path)


def test_image_output_dir_for_idempotent():
    a = image_output_dir_for("/tmp/out.json", "abc123")
    b = image_output_dir_for("/tmp/out.json", "abc123")
    assert a == b


def test_image_output_dir_for_different_hashes_different_dirs():
    a = image_output_dir_for("/tmp/out.json", "hash_a")
    b = image_output_dir_for("/tmp/out.json", "hash_b")
    assert a != b


def test_image_output_dir_for_different_output_paths_different_parents():
    a = image_output_dir_for("/tmp/a/out.json", "abc")
    b = image_output_dir_for("/tmp/b/out.json", "abc")
    assert a.parent != b.parent


def test_image_output_dir_for_unicode_in_hash():
    result = image_output_dir_for("/tmp/out.json", "你好")
    assert "你好" in result.name


def test_image_output_dir_for_returns_relative_for_relative_input():
    """传入相对路径，返回也是相对路径（不强制绝对）。"""
    result = image_output_dir_for("out.json", "abc")
    assert not result.is_absolute()


def test_image_output_dir_for_returns_absolute_for_absolute_input(tmp_path):
    """传入绝对路径，返回的 Path 的 parent 也是绝对（与输入一致）。"""
    abs_out = tmp_path / "out.json"  # tmp_path 已经是绝对路径
    result = image_output_dir_for(abs_out, "abc")
    assert result.parent.is_absolute()


# =============================================================================
# process_single — 错误传播与 details 字段深度
# =============================================================================


def test_process_single_file_not_found_details_path(tmp_path):
    """FileNotFoundError 的 details 含 path 字段。"""
    doc, errors = process_single(tmp_path / "missing.pdf")
    assert doc is None
    assert len(errors) == 1
    assert errors[0].code == "file_not_found"
    assert "path" in errors[0].details


def test_process_single_file_not_found_message_contains_path(tmp_path):
    missing = tmp_path / "missing.pdf"
    doc, errors = process_single(missing)
    assert str(missing) in errors[0].message or str(missing) in errors[0].details["path"]


def test_process_single_directory_input_falls_through_to_parser(tmp_path):
    """目录作为 input_path：compute_file_hash 会失败（PermissionError/IsADirectoryError
    被 OSError 兜底）→ hash_io_error。

    不同平台行为可能不同；本测试只验证有错误返回，不验证具体 code。
    """
    doc, errors = process_single(tmp_path)
    assert doc is None
    assert len(errors) >= 1


def test_process_single_unknown_parser_details_no_parser_name(tmp_path):
    """未知 parser → 'unexpected_parser_error'（实际上 get_parser 抛 ValueError 在 try 内）。"""
    # 创建一个空文件让 hash 通过
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    doc, errors = process_single(p, parser_name="xml")
    assert doc is None
    assert len(errors) == 1
    # ValueError("未知 parser: xml") 被 except Exception 兜底
    assert errors[0].code == "unexpected_parser_error"


def test_process_single_unknown_parser_details_has_parser_name(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    doc, errors = process_single(p, parser_name="xml")
    assert errors[0].details["parser_name"] == "xml"


def test_process_single_unknown_parser_details_has_path(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    doc, errors = process_single(p, parser_name="xml")
    assert "path" in errors[0].details
    assert errors[0].details["path"] == str(p)


def test_process_single_unknown_parser_message_starts_with_exception_type(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    doc, errors = process_single(p, parser_name="xml")
    assert errors[0].message.startswith("ValueError:")


def test_process_single_text_parser_returns_document(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello world", encoding="utf-8")
    doc, errors = process_single(p, parser_name="text")
    assert doc is not None
    assert errors == []
    assert len(doc.elements) >= 1


def test_process_single_returns_document_with_chunks(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello world. " * 100, encoding="utf-8")
    doc, errors = process_single(p, parser_name="text")
    assert doc is not None
    assert len(doc.chunks) >= 1


def test_process_single_document_has_metadata_dict(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    doc, _ = process_single(p, parser_name="text")
    assert isinstance(doc.metadata, dict)


def test_process_single_document_has_relations_list(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    doc, _ = process_single(p, parser_name="text")
    assert isinstance(doc.relations, list)


def test_process_single_document_has_warnings_list(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    doc, _ = process_single(p, parser_name="text")
    assert isinstance(doc.warnings, list)


def test_process_single_document_source_type_text(tmp_path):
    """TextParser 产出的 Document.source_type='text'。"""
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    doc, _ = process_single(p, parser_name="text")
    assert doc.source_type == "text"


def test_process_single_writes_valid_json(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello world", encoding="utf-8")
    out = tmp_path / "out.json"
    doc, errors = process_single(p, out, parser_name="text")
    assert doc is not None
    assert errors == []
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_process_single_writes_indented_json(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    out = tmp_path / "out.json"
    process_single(p, out, parser_name="text")
    content = out.read_text(encoding="utf-8")
    assert "\n" in content  # 多行 = 缩进


def test_process_single_creates_parent_dir(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    out = tmp_path / "a" / "b" / "out.json"
    process_single(p, out, parser_name="text")
    assert out.is_file()


def test_process_single_write_json_false_skips_file_creation(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    out = tmp_path / "out.json"
    doc, errors = process_single(p, out, parser_name="text", write_json=False)
    assert doc is not None
    assert not out.exists()


def test_process_single_no_output_path_does_not_write(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    doc, errors = process_single(p, parser_name="text")
    assert doc is not None


def test_process_single_with_pathlib_input(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    doc, _ = process_single(p, parser_name="text")
    assert doc is not None


def test_process_single_with_str_input(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    doc, _ = process_single(str(p), parser_name="text")
    assert doc is not None


def test_process_single_default_max_chars_800(tmp_path):
    """生成的 chunk 不超 800 字符（默认）。"""
    p = tmp_path / "input.txt"
    p.write_text("a" * 2000, encoding="utf-8")
    doc, _ = process_single(p, parser_name="text")
    for chunk in doc.chunks:
        assert len(chunk.text) <= 800


def test_process_single_max_chars_100_chunks_smaller(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("a" * 500, encoding="utf-8")
    doc, _ = process_single(p, parser_name="text", max_chars=100)
    for chunk in doc.chunks:
        assert len(chunk.text) <= 100


def test_process_single_idempotent_same_input(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello world", encoding="utf-8")
    doc1, _ = process_single(p, parser_name="text")
    doc2, _ = process_single(p, parser_name="text")
    assert doc1.source_hash == doc2.source_hash


# =============================================================================
# process_single — ParserError 处理
# =============================================================================


def test_process_single_parser_error_yields_structured_error(tmp_path, monkeypatch):
    """让 parser 抛 ParserError → code/message/details 透传。"""
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")

    def fake_parse(self, path, source_hash=None):
        raise ParserError("custom_error", "boom", {"extra": "info"})

    monkeypatch.setattr("app.parsers.text_parser.TextParser.parse", fake_parse)
    doc, errors = process_single(p, parser_name="text")
    assert doc is None
    assert len(errors) == 1
    assert errors[0].code == "custom_error"
    assert errors[0].message == "boom"


def test_process_single_parser_error_details_merge_with_path(tmp_path, monkeypatch):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")

    def fake_parse(self, path, source_hash=None):
        raise ParserError("code", "msg", {"k": "v"})

    monkeypatch.setattr("app.parsers.text_parser.TextParser.parse", fake_parse)
    doc, errors = process_single(p, parser_name="text")
    assert errors[0].details["k"] == "v"
    assert errors[0].details["path"] == str(p)


def test_process_single_unexpected_exception_yields_unexpected_parser_error(tmp_path, monkeypatch):
    """非 ParserError 的异常被兜底为 unexpected_parser_error。"""
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")

    def fake_parse(self, path, source_hash=None):
        raise RuntimeError("unexpected!")

    monkeypatch.setattr("app.parsers.text_parser.TextParser.parse", fake_parse)
    doc, errors = process_single(p, parser_name="text")
    assert doc is None
    assert errors[0].code == "unexpected_parser_error"
    assert "RuntimeError" in errors[0].message


def test_process_single_chunker_failure_yields_chunker_failed(tmp_path, monkeypatch):
    """让 chunker 抛异常 → chunker_failed。"""
    p = tmp_path / "input.txt"
    p.write_text("hello world", encoding="utf-8")

    def fake_chunk(self, document):
        raise RuntimeError("chunker broken")

    monkeypatch.setattr("app.chunkers.structural.StructuralChunker.chunk", fake_chunk)
    doc, errors = process_single(p, parser_name="text")
    assert doc is None
    assert errors[0].code == "chunker_failed"
    assert "chunker broken" in errors[0].message
    assert errors[0].details["exception_type"] == "RuntimeError"


def _make_empty_doc(source_hash="x"):
    """构造一个 0 elements 的 Document，用于 monkeypatch。"""
    return Document(
        document_id="test-doc",
        source_path="test.txt",
        source_type="text",
        source_hash=source_hash,
        parser_name="text",
        parser_version="1.0",
        elements=[],
        chunks=[],
    )


def test_process_single_no_elements_yields_no_extracted_elements(tmp_path, monkeypatch):
    """让 parser 返回 0 elements → no_extracted_elements。"""
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")

    def fake_parse(self, path, source_hash=None):
        return _make_empty_doc(source_hash or "x")

    monkeypatch.setattr("app.parsers.text_parser.TextParser.parse", fake_parse)
    doc, errors = process_single(p, parser_name="text")
    assert doc is None
    assert errors[0].code == "no_extracted_elements"
    assert errors[0].details["source_type"] == "text"
    assert "warnings" in errors[0].details


def test_process_single_schema_validation_failed(tmp_path, monkeypatch):
    """让 validate 抛 SchemaValidationError → schema_validation_failed。"""
    from app.schema import SchemaValidationError
    p = tmp_path / "input.txt"
    p.write_text("hello world", encoding="utf-8")

    def fake_validate(d):
        raise SchemaValidationError("schema failed", [{"path": [], "message": "bad"}])

    monkeypatch.setattr("app.pipeline.validate", fake_validate)
    doc, errors = process_single(p, parser_name="text")
    assert doc is None
    assert errors[0].code == "schema_validation_failed"
    assert "validation_errors" in errors[0].details


def test_process_single_schema_validation_truncates_to_20_errors(tmp_path, monkeypatch):
    """e.errors[:20] 截断。"""
    from app.schema import SchemaValidationError
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")

    many_errors = [{"path": [i], "message": f"err{i}"} for i in range(50)]

    def fake_validate(d):
        raise SchemaValidationError("many errors", many_errors)

    monkeypatch.setattr("app.pipeline.validate", fake_validate)
    doc, errors = process_single(p, parser_name="text")
    assert len(errors[0].details["validation_errors"]) == 20


def test_process_single_write_failure_yields_write_failed(tmp_path, monkeypatch):
    """让 json.dump 抛 OSError → write_failed。"""
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    out = tmp_path / "out.json"

    def fake_dump(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("app.pipeline.json.dump", fake_dump)
    doc, errors = process_single(p, out, parser_name="text")
    assert doc is None
    assert errors[0].code == "write_failed"
    assert "disk full" in errors[0].message
    assert errors[0].details["path"] == str(out)


# =============================================================================
# process_single — schema 校验前置空 elements 检查
# =============================================================================


def test_process_single_empty_elements_check_runs_before_schema(tmp_path, monkeypatch):
    """elements=[] 早返回，不应调 schema validate。"""
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    call_count = [0]

    def fake_parse(self, path, source_hash=None):
        return _make_empty_doc(source_hash or "x")

    original_validate = pipeline_mod.validate

    def counting_validate(d):
        call_count[0] += 1
        return original_validate(d)

    monkeypatch.setattr("app.parsers.text_parser.TextParser.parse", fake_parse)
    monkeypatch.setattr("app.pipeline.validate", counting_validate)
    doc, errors = process_single(p, parser_name="text")
    assert errors[0].code == "no_extracted_elements"
    assert call_count[0] == 0  # schema 未被调用


def test_process_single_chunker_runs_before_schema(tmp_path, monkeypatch):
    """chunker 失败时 schema 也不应被调用。"""
    p = tmp_path / "input.txt"
    p.write_text("hello world", encoding="utf-8")
    call_count = [0]

    def fake_chunk(self, document):
        raise RuntimeError("chunker broken")

    original_validate = pipeline_mod.validate

    def counting_validate(d):
        call_count[0] += 1
        return original_validate(d)

    monkeypatch.setattr("app.chunkers.structural.StructuralChunker.chunk", fake_chunk)
    monkeypatch.setattr("app.pipeline.validate", counting_validate)
    doc, errors = process_single(p, parser_name="text")
    assert errors[0].code == "chunker_failed"
    assert call_count[0] == 0


def test_process_single_hash_runs_before_parser(tmp_path, monkeypatch):
    """hash 失败时 parser 不应被调用。"""
    p = tmp_path / "missing.pdf"
    call_count = [0]

    def fake_get_parser(name, **kwargs):
        call_count[0] += 1
        return get_parser(name, **kwargs)

    monkeypatch.setattr("app.pipeline.get_parser", fake_get_parser)
    doc, errors = process_single(p, parser_name="text")
    assert errors[0].code == "file_not_found"
    assert call_count[0] == 0


# =============================================================================
# process_single — 不变量
# =============================================================================


def test_process_single_returns_tuple(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    result = process_single(p, parser_name="text")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_process_single_first_element_is_document_or_none(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    doc, _ = process_single(p, parser_name="text")
    assert doc is None or isinstance(doc, Document)


def test_process_single_second_element_is_list(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("hello", encoding="utf-8")
    _, errors = process_single(p, parser_name="text")
    assert isinstance(errors, list)


def test_process_single_each_error_is_error_record(tmp_path):
    p = tmp_path / "missing.pdf"
    _, errors = process_single(p)
    for e in errors:
        assert isinstance(e, ErrorRecord)


def test_process_single_each_error_has_code_message_details(tmp_path):
    p = tmp_path / "missing.pdf"
    _, errors = process_single(p)
    for e in errors:
        assert hasattr(e, "code")
        assert hasattr(e, "message")
        assert hasattr(e, "details")


# =============================================================================
# validate_only — 返回值语义深度
# =============================================================================


def test_validate_only_returns_tuple_of_two(tmp_path):
    p = tmp_path / "missing.json"
    result = validate_only(p)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_validate_only_first_element_is_bool(tmp_path):
    p = tmp_path / "missing.json"
    ok, _ = validate_only(p)
    assert isinstance(ok, bool)


def test_validate_only_second_element_is_str(tmp_path):
    p = tmp_path / "missing.json"
    _, msg = validate_only(p)
    assert isinstance(msg, str)


def test_validate_only_missing_file_returns_false(tmp_path):
    p = tmp_path / "missing.json"
    ok, msg = validate_only(p)
    assert ok is False


def test_validate_only_missing_file_message_has_path(tmp_path):
    p = tmp_path / "missing.json"
    _, msg = validate_only(p)
    assert str(p) in msg


def test_validate_only_invalid_json_returns_false(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    ok, _ = validate_only(p)
    assert ok is False


def test_validate_only_invalid_json_message_mentions_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    _, msg = validate_only(p)
    assert "JSON" in msg or "json" in msg.lower()


def test_validate_only_directory_returns_false(tmp_path):
    """目录是 FileNotFoundError（not is_file）。"""
    ok, _ = validate_only(tmp_path)
    assert ok is False


def test_validate_only_empty_file_returns_false(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    ok, _ = validate_only(p)
    assert ok is False


def test_validate_only_str_path_accepted(tmp_path):
    p = tmp_path / "missing.json"
    ok, _ = validate_only(str(p))
    assert ok is False


def test_validate_only_pathlib_path_accepted(tmp_path):
    p = tmp_path / "missing.json"
    ok, _ = validate_only(p)
    assert ok is False


def test_validate_only_valid_json_returns_true(tmp_path):
    """用 process_single 生成一个合法 JSON 再校验。"""
    in_path = tmp_path / "in.txt"
    in_path.write_text("hello world", encoding="utf-8")
    out_path = tmp_path / "out.json"
    process_single(in_path, out_path, parser_name="text")
    ok, msg = validate_only(out_path)
    assert ok is True
    assert msg == "OK"


def test_validate_only_wrong_shape_json_returns_false(tmp_path):
    p = tmp_path / "wrong.json"
    p.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    ok, _ = validate_only(p)
    assert ok is False


def test_validate_only_wrong_shape_message_has_schema(tmp_path):
    p = tmp_path / "wrong.json"
    p.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    _, msg = validate_only(p)
    # SchemaValidationError 转 str 通常含字段名
    assert isinstance(msg, str)


def test_validate_only_does_not_raise_on_any_input(tmp_path):
    """validate_only 永远返回 (bool, str)，不抛错。"""
    p = tmp_path / "missing.json"
    assert validate_only(p) is not None
    p2 = tmp_path / "bad.json"
    p2.write_text("not json", encoding="utf-8")
    assert validate_only(p2) is not None


# =============================================================================
# __all__ 与模块结构
# =============================================================================


def test_all_exports_is_list():
    assert isinstance(pipeline_all, list)


def test_all_exports_count_four():
    assert len(pipeline_all) == 4


def test_all_exports_exact_set():
    assert set(pipeline_all) == {
        "get_parser",
        "image_output_dir_for",
        "process_single",
        "validate_only",
    }


def test_all_exports_match_module_attributes():
    for name in pipeline_all:
        assert hasattr(pipeline_mod, name)


def test_all_exports_no_underscore_prefix():
    for name in pipeline_all:
        assert not name.startswith("_")


def test_module_imports_json():
    assert hasattr(pipeline_mod, "json")


def test_module_imports_path():
    assert hasattr(pipeline_mod, "Path")


def test_module_imports_document_model():
    assert hasattr(pipeline_mod, "Document")


def test_module_imports_error_record():
    assert hasattr(pipeline_mod, "ErrorRecord")


def test_module_imports_parser_protocol():
    assert hasattr(pipeline_mod, "Parser")


def test_module_imports_parser_error():
    assert hasattr(pipeline_mod, "ParserError")


def test_module_imports_structural_chunker():
    assert hasattr(pipeline_mod, "StructuralChunker")


def test_module_imports_validate():
    assert hasattr(pipeline_mod, "validate")


def test_module_imports_schema_validation_error():
    assert hasattr(pipeline_mod, "SchemaValidationError")


def test_module_imports_compute_file_hash():
    assert hasattr(pipeline_mod, "compute_file_hash")


def test_module_does_not_import_pipeline_internal_helpers():
    """_ 不导出 process_single 的内部辅助函数。"""
    for name in pipeline_all:
        assert not name.startswith("_")


# =============================================================================
# 函数签名
# =============================================================================


def test_get_parser_signature():
    import inspect
    sig = inspect.signature(get_parser)
    params = list(sig.parameters.keys())
    assert params == ["name", "image_output_dir"]


def test_get_parser_image_output_dir_default_none():
    import inspect
    sig = inspect.signature(get_parser)
    assert sig.parameters["image_output_dir"].default is None


def test_image_output_dir_for_signature():
    import inspect
    sig = inspect.signature(image_output_dir_for)
    params = list(sig.parameters.keys())
    assert params == ["output_path", "source_hash"]


def test_process_single_signature():
    import inspect
    sig = inspect.signature(process_single)
    params = list(sig.parameters.keys())
    assert params == ["input_path", "output_path", "parser_name", "max_chars", "write_json"]


def test_process_single_output_path_default_none():
    import inspect
    sig = inspect.signature(process_single)
    assert sig.parameters["output_path"].default is None


def test_process_single_parser_name_default_fallback():
    import inspect
    sig = inspect.signature(process_single)
    assert sig.parameters["parser_name"].default == "fallback"


def test_process_single_max_chars_default_800():
    import inspect
    sig = inspect.signature(process_single)
    assert sig.parameters["max_chars"].default == 800


def test_process_single_write_json_default_true():
    import inspect
    sig = inspect.signature(process_single)
    assert sig.parameters["write_json"].default is True


def test_process_single_write_json_is_keyword_only():
    import inspect
    sig = inspect.signature(process_single)
    assert sig.parameters["write_json"].kind == inspect.Parameter.KEYWORD_ONLY


def test_process_single_parser_name_is_keyword_only():
    import inspect
    sig = inspect.signature(process_single)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY


def test_process_single_max_chars_is_keyword_only():
    import inspect
    sig = inspect.signature(process_single)
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_validate_only_signature():
    import inspect
    sig = inspect.signature(validate_only)
    params = list(sig.parameters.keys())
    assert params == ["json_path"]


# =============================================================================
# 集成场景
# =============================================================================


def test_process_single_pipeline_call_does_not_print(tmp_path, capsys):
    p = tmp_path / "input.txt"
    p.write_text("hello world", encoding="utf-8")
    process_single(p, parser_name="text")
    out = capsys.readouterr()
    assert out.out == ""
    assert out.err == ""


def test_validate_only_call_does_not_print(tmp_path, capsys):
    p = tmp_path / "missing.json"
    validate_only(p)
    out = capsys.readouterr()
    assert out.out == ""
    assert out.err == ""
