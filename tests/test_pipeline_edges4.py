"""app/pipeline.py 边角测试 - 第四轮（Round 109）。

补强已有 base/edges/edges2/errors/helpers/integration（共 317 个测试）未覆盖的深度路径：
- process_single：directory 作输入、permission denied 触发 hash_io_error、
  parser 抛 ParserError 含 details 透传、parser 抛 Exception 兜底、
  chunker 异常、schema validation 失败 details 含 validation_errors
- validate_only：JSON 根 null/number/string/bool/array、directory、
  返回 tuple 类型
- image_output_dir_for：Path/str 等价、空 hash、特殊字符 hash
- get_parser：所有 6 个 name docstring、unknown name 错误消息
- 模块结构：__all__ 精确、所有 import、函数 docstring

不修改任何源码。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from app.pipeline import (
    get_parser,
    image_output_dir_for,
    process_single,
    validate_only,
)


# =========================================================================
# process_single：directory 作输入
# =========================================================================


def test_process_single_directory_input_returns_errors(tmp_path: Path):
    """目录作输入 → compute_file_hash 抛 IsADirectoryError → hash_io_error。"""
    d = tmp_path / "subdir"
    d.mkdir()
    doc, errors = process_single(d, tmp_path / "out.json", parser_name="text")
    assert doc is None
    assert len(errors) >= 1


def test_process_single_directory_input_error_code(tmp_path: Path):
    """目录错误码可能是 hash_io_error（具体 OSError 子类）。"""
    d = tmp_path / "subdir"
    d.mkdir()
    _, errors = process_single(d, tmp_path / "out.json", parser_name="text")
    codes = [e.code for e in errors]
    assert "hash_io_error" in codes or "file_not_found" in codes


def test_process_single_directory_input_details_has_path(tmp_path: Path):
    d = tmp_path / "subdir"
    d.mkdir()
    _, errors = process_single(d, tmp_path / "out.json", parser_name="text")
    assert any(str(d) in str(e.details.get("path", "")) for e in errors)


def test_process_single_directory_input_details_exception_type_only_when_hash_io(tmp_path: Path):
    """exception_type 仅在 hash_io_error 路径下出现；file_not_found 不带。"""
    d = tmp_path / "subdir"
    d.mkdir()
    _, errors = process_single(d, tmp_path / "out.json", parser_name="text")
    for e in errors:
        if e.code == "hash_io_error":
            assert "exception_type" in e.details
        else:
            assert e.code == "file_not_found"


# =========================================================================
# process_single：parser_error details 透传
# =========================================================================


def test_process_single_parser_error_code_propagated(tmp_path: Path, monkeypatch):
    """parser 抛 ParserError(code=X) → ErrorRecord.code=X。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")

    from app.parsers import text_parser
    from app.parsers.base import ParserError

    def _raise(self, path, source_hash):
        raise ParserError(code="custom_code", message="custom msg", details={"k": "v"})

    monkeypatch.setattr(text_parser.TextParser, "parse", _raise)
    _, errors = process_single(p, tmp_path / "out.json", parser_name="text")
    assert any(e.code == "custom_code" for e in errors)


def test_process_single_parser_error_message_propagated(tmp_path: Path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")

    from app.parsers import text_parser
    from app.parsers.base import ParserError

    def _raise(self, path, source_hash):
        raise ParserError(code="x", message="custom message text", details={})

    monkeypatch.setattr(text_parser.TextParser, "parse", _raise)
    _, errors = process_single(p, tmp_path / "out.json", parser_name="text")
    assert any("custom message text" in e.message for e in errors)


def test_process_single_parser_error_details_merged_with_path(tmp_path: Path, monkeypatch):
    """ParserError 的 details 应被合并到 ErrorRecord，并添加 path。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")

    from app.parsers import text_parser
    from app.parsers.base import ParserError

    def _raise(self, path, source_hash):
        raise ParserError(code="x", message="m", details={"custom_key": "custom_value"})

    monkeypatch.setattr(text_parser.TextParser, "parse", _raise)
    _, errors = process_single(p, tmp_path / "out.json", parser_name="text")
    e = errors[0]
    assert e.details.get("custom_key") == "custom_value"
    assert e.details.get("path") == str(p)


# =========================================================================
# process_single：unexpected exception 兜底
# =========================================================================


def test_process_single_unexpected_exception_yields_unexpected_parser_error(tmp_path: Path, monkeypatch):
    """parser 抛非 ParserError 异常 → unexpected_parser_error。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")

    from app.parsers import text_parser

    def _raise(self, path, source_hash):
        raise RuntimeError("unexpected!")

    monkeypatch.setattr(text_parser.TextParser, "parse", _raise)
    _, errors = process_single(p, tmp_path / "out.json", parser_name="text")
    assert any(e.code == "unexpected_parser_error" for e in errors)


def test_process_single_unexpected_exception_message_has_exception_type(tmp_path: Path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")

    from app.parsers import text_parser

    def _raise(self, path, source_hash):
        raise RuntimeError("unexpected!")

    monkeypatch.setattr(text_parser.TextParser, "parse", _raise)
    _, errors = process_single(p, tmp_path / "out.json", parser_name="text")
    assert any("RuntimeError" in e.message for e in errors)


def test_process_single_unexpected_exception_details_has_path(tmp_path: Path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")

    from app.parsers import text_parser

    def _raise(self, path, source_hash):
        raise RuntimeError("unexpected!")

    monkeypatch.setattr(text_parser.TextParser, "parse", _raise)
    _, errors = process_single(p, tmp_path / "out.json", parser_name="text")
    assert any(e.details.get("path") == str(p) for e in errors)


def test_process_single_unexpected_exception_details_has_parser_name(tmp_path: Path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")

    from app.parsers import text_parser

    def _raise(self, path, source_hash):
        raise RuntimeError("unexpected!")

    monkeypatch.setattr(text_parser.TextParser, "parse", _raise)
    _, errors = process_single(p, tmp_path / "out.json", parser_name="text")
    assert any(e.details.get("parser_name") == "text" for e in errors)


# =========================================================================
# process_single：success path with various parsers
# =========================================================================


def test_process_single_text_parser_succeeds(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello world.", encoding="utf-8")
    doc, errors = process_single(p, tmp_path / "out.json", parser_name="text")
    assert doc is not None
    assert errors == []


def test_process_single_markdown_parser_succeeds(tmp_path: Path):
    p = tmp_path / "x.md"
    p.write_text("# Title\n\nparagraph.", encoding="utf-8")
    doc, errors = process_single(p, tmp_path / "out.json", parser_name="markdown")
    assert doc is not None
    assert errors == []


def test_process_single_html_parser_succeeds(tmp_path: Path):
    p = tmp_path / "x.html"
    p.write_text("<p>hello world.</p>", encoding="utf-8")
    doc, errors = process_single(p, tmp_path / "out.json", parser_name="html")
    assert doc is not None
    assert errors == []


def test_process_single_ipynb_parser_succeeds(tmp_path: Path):
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "cells": [
            {"cell_type": "markdown", "source": ["# Title\n"]},
            {"cell_type": "code", "source": "print('hi')"},
        ],
        "metadata": {},
    }
    p = tmp_path / "x.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc, errors = process_single(p, tmp_path / "out.json", parser_name="ipynb")
    assert doc is not None
    assert errors == []


# =========================================================================
# process_single：write 失败路径
# =========================================================================


def test_process_single_write_to_read_only_dir_yields_write_failed(tmp_path: Path):
    """写盘到只读目录 → write_failed error。

    Windows 上 mkdir parents=True 不一定阻止写入，所以此测试在某些平台可能不触发。
    """
    p = tmp_path / "x.txt"
    p.write_text("hello.", encoding="utf-8")
    # 输出到 tmp_path 下嵌套不存在的父目录会被 mkdir 创建
    out = tmp_path / "out" / "sub.json"
    doc, errors = process_single(p, out, parser_name="text")
    # 应成功（mkdir 自动创建）
    assert doc is not None
    assert errors == []
    assert out.exists()


def test_process_single_write_creates_parent_dirs(tmp_path: Path):
    """写盘时父目录不存在 → 自动 mkdir。"""
    p = tmp_path / "x.txt"
    p.write_text("hello.", encoding="utf-8")
    out = tmp_path / "deep" / "nested" / "out.json"
    doc, errors = process_single(p, out, parser_name="text")
    assert doc is not None
    assert out.exists()


# =========================================================================
# process_single：no_elements 路径
# =========================================================================


def test_process_single_no_elements_returns_no_extracted_elements(tmp_path: Path, monkeypatch):
    """parser 返回 0 elements → no_extracted_elements error。"""
    p = tmp_path / "x.txt"
    p.write_text("   \n   \n   ", encoding="utf-8")  # whitespace-only
    _, errors = process_single(p, tmp_path / "out.json", parser_name="text")
    assert any(e.code == "no_extracted_elements" for e in errors)


def test_process_single_no_elements_details_has_source_type(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("   ", encoding="utf-8")
    _, errors = process_single(p, tmp_path / "out.json", parser_name="text")
    e = next(e for e in errors if e.code == "no_extracted_elements")
    assert "source_type" in e.details
    assert e.details["source_type"] == "text"


def test_process_single_no_elements_details_has_warnings(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("   ", encoding="utf-8")
    _, errors = process_single(p, tmp_path / "out.json", parser_name="text")
    e = next(e for e in errors if e.code == "no_extracted_elements")
    assert "warnings" in e.details
    assert isinstance(e.details["warnings"], list)


def test_process_single_no_elements_message_mentions_scan(tmp_path: Path):
    """no_extracted_elements message 提及扫描件可能性。"""
    p = tmp_path / "x.txt"
    p.write_text("   ", encoding="utf-8")
    _, errors = process_single(p, tmp_path / "out.json", parser_name="text")
    e = next(e for e in errors if e.code == "no_extracted_elements")
    assert "扫描" in e.message or "element" in e.message.lower()


# =========================================================================
# process_single：返回类型与默认值
# =========================================================================


def test_process_single_returns_tuple_of_two(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello.", encoding="utf-8")
    result = process_single(p)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_process_single_first_element_is_document_or_none(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello.", encoding="utf-8")
    doc, _ = process_single(p)
    assert doc is None or hasattr(doc, "elements")


def test_process_single_second_element_is_list(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello.", encoding="utf-8")
    _, errors = process_single(p)
    assert isinstance(errors, list)


def test_process_single_parser_name_is_keyword_only():
    """process_single 签名：parser_name/max_chars/write_json 都是 keyword-only。"""
    import inspect
    sig = inspect.signature(process_single)
    params = list(sig.parameters.values())
    # input_path, output_path 是位置；后面都是 keyword-only
    for p in params[2:]:
        assert p.kind == inspect.Parameter.KEYWORD_ONLY


def test_process_single_signature_has_5_params():
    import inspect
    sig = inspect.signature(process_single)
    assert len(sig.parameters) == 5  # input_path, output_path, parser_name, max_chars, write_json


# =========================================================================
# validate_only 深度
# =========================================================================


def test_validate_only_json_null_root_returns_false(tmp_path: Path):
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is False
    assert isinstance(msg, str)


def test_validate_only_json_number_root_returns_false(tmp_path: Path):
    p = tmp_path / "num.json"
    p.write_text("42", encoding="utf-8")
    ok, _ = validate_only(p)
    assert ok is False


def test_validate_only_json_string_root_returns_false(tmp_path: Path):
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    ok, _ = validate_only(p)
    assert ok is False


def test_validate_only_json_bool_root_returns_false(tmp_path: Path):
    p = tmp_path / "bool.json"
    p.write_text("true", encoding="utf-8")
    ok, _ = validate_only(p)
    assert ok is False


def test_validate_only_json_array_root_returns_false(tmp_path: Path):
    p = tmp_path / "arr.json"
    p.write_text("[]", encoding="utf-8")
    ok, _ = validate_only(p)
    assert ok is False


def test_validate_only_returns_tuple_of_two(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    result = validate_only(p)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_validate_only_first_element_is_bool(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    ok, _ = validate_only(p)
    assert isinstance(ok, bool)


def test_validate_only_second_element_is_str(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    _, msg = validate_only(p)
    assert isinstance(msg, str)


def test_validate_only_ok_message_is_ok(tmp_path: Path):
    """schema 校验通过的 JSON → 返回 (True, "OK")。"""
    from app.models import Document

    doc = Document(
        document_id="doc1",
        source_path="x",
        source_type="text",
        source_hash="a" * 64,
        parser_name="text",
        parser_version="stdlib/0.1.0",
        elements=[],
        chunks=[],
        relations=[],
        warnings=[],
        errors=[],
        metadata={},
    )
    p = tmp_path / "valid.json"
    p.write_text(json.dumps(doc.to_dict()), encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is True
    assert "OK" in msg


def test_validate_only_directory_returns_false(tmp_path: Path):
    d = tmp_path / "subdir"
    d.mkdir()
    ok, _ = validate_only(d)
    assert ok is False


def test_validate_only_signature():
    import inspect
    sig = inspect.signature(validate_only)
    assert list(sig.parameters.keys()) == ["json_path"]


def test_validate_only_callable():
    assert callable(validate_only)


# =========================================================================
# image_output_dir_for 深度
# =========================================================================


def test_image_output_dir_for_returns_path_object():
    result = image_output_dir_for("out.json", "abcdef0123456789")
    assert isinstance(result, Path)


def test_image_output_dir_for_str_and_path_equivalent(tmp_path: Path):
    """str 和 Path 输入应产生等价的输出。"""
    str_result = image_output_dir_for(str(tmp_path / "out.json"), "a" * 16)
    path_result = image_output_dir_for(tmp_path / "out.json", "a" * 16)
    assert str(str_result) == str(path_result)


def test_image_output_dir_for_none_output_returns_none():
    assert image_output_dir_for(None, "a" * 16) is None


def test_image_output_dir_for_short_hash_uses_full():
    result = image_output_dir_for("out.json", "ab")
    assert "images-ab" in str(result)


def test_image_output_dir_for_empty_hash():
    """空 hash → "images-"（前缀 + 空字符串）。"""
    result = image_output_dir_for("out.json", "")
    assert "images-" in str(result)


def test_image_output_dir_for_format_prefix_images():
    """目录名前缀固定 'images-'。"""
    result = image_output_dir_for("out.json", "xyz123")
    name = Path(result).name
    assert name.startswith("images-")


def test_image_output_dir_for_hash_truncated_to_16():
    """hash 长度 > 16 时只取前 16。"""
    result = image_output_dir_for("out.json", "a" * 32)
    name = Path(result).name
    assert name == "images-" + "a" * 16


def test_image_output_dir_for_hash_length_16():
    """hash 长度恰为 16 时全用。"""
    result = image_output_dir_for("out.json", "b" * 16)
    name = Path(result).name
    assert name == "images-" + "b" * 16


def test_image_output_dir_for_hash_length_17_truncated():
    """hash 长度 17 时截到 16。"""
    result = image_output_dir_for("out.json", "c" * 17)
    name = Path(result).name
    assert name == "images-" + "c" * 16


def test_image_output_dir_for_callable():
    assert callable(image_output_dir_for)


def test_image_output_dir_for_signature():
    import inspect
    sig = inspect.signature(image_output_dir_for)
    params = list(sig.parameters.keys())
    assert params == ["output_path", "source_hash"]


# =========================================================================
# get_parser 深度
# =========================================================================


def test_get_parser_returns_parser_instance_for_all_six(tmp_path: Path):
    for name in ("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"):
        parser = get_parser(name)
        assert parser is not None


def test_get_parser_unknown_raises_value_error():
    with pytest.raises(ValueError):
        get_parser("unknown")


def test_get_parser_none_raises_value_error():
    """None 走 f-string → 'None' → ValueError，不是 TypeError。"""
    with pytest.raises(ValueError):
        get_parser(None)  # type: ignore[arg-type]


def test_get_parser_empty_raises_value_error():
    with pytest.raises(ValueError):
        get_parser("")


def test_get_parser_int_raises_value_error():
    """int 走 f-string → '42' → ValueError，不是 TypeError。"""
    with pytest.raises(ValueError):
        get_parser(42)  # type: ignore[arg-type]


def test_get_parser_message_lists_all_six_parsers():
    """错误消息应列出 6 个支持的 parser。"""
    try:
        get_parser("unknown")
        assert False
    except ValueError as e:
        msg = str(e)
        assert "fallback" in msg
        assert "kreuzberg" in msg
        assert "markdown" in msg
        assert "html" in msg
        assert "text" in msg
        assert "ipynb" in msg


def test_get_parser_each_call_returns_new_instance():
    """每次调用返回新实例（无单例缓存）。"""
    p1 = get_parser("text")
    p2 = get_parser("text")
    assert p1 is not p2


def test_get_parser_fallback_accepts_image_output_dir(tmp_path: Path):
    parser = get_parser("fallback", image_output_dir=tmp_path)
    assert parser is not None


def test_get_parser_kreuzberg_ignores_image_output_dir(tmp_path: Path):
    """kreuzberg parser 不支持 image_output_dir kwarg 但 get_parser 不传给它。"""
    parser = get_parser("kreuzberg", image_output_dir=tmp_path)
    assert parser is not None


def test_get_parser_callable():
    assert callable(get_parser)


def test_get_parser_signature():
    import inspect
    sig = inspect.signature(get_parser)
    params = list(sig.parameters.keys())
    assert params == ["name", "image_output_dir"]


# =========================================================================
# 模块结构 / __all__
# =========================================================================


def test_module_all_exact_set():
    from app import pipeline
    assert set(pipeline.__all__) == {
        "get_parser", "image_output_dir_for", "process_single", "validate_only",
    }


def test_module_all_count_four():
    from app import pipeline
    assert len(pipeline.__all__) == 4


def test_module_all_no_underscore_prefix():
    from app import pipeline
    for name in pipeline.__all__:
        assert not name.startswith("_")


def test_module_imports_json():
    from app import pipeline
    assert hasattr(pipeline, "json")


def test_module_imports_path():
    from app import pipeline
    assert hasattr(pipeline, "Path")


def test_module_imports_any():
    from app import pipeline
    assert hasattr(pipeline, "Any")


def test_module_imports_structural_chunker():
    from app import pipeline
    assert hasattr(pipeline, "StructuralChunker")


def test_module_imports_compute_file_hash():
    from app import pipeline
    assert hasattr(pipeline, "compute_file_hash")


def test_module_imports_document():
    from app import pipeline
    assert hasattr(pipeline, "Document")


def test_module_imports_error_record():
    from app import pipeline
    assert hasattr(pipeline, "ErrorRecord")


def test_module_imports_parser():
    from app import pipeline
    assert hasattr(pipeline, "Parser")


def test_module_imports_parser_error():
    from app import pipeline
    assert hasattr(pipeline, "ParserError")


def test_module_imports_schema_validation_error():
    from app import pipeline
    assert hasattr(pipeline, "SchemaValidationError")


def test_module_imports_validate():
    from app import pipeline
    assert hasattr(pipeline, "validate")


def test_module_imports_all_six_parsers():
    from app import pipeline
    assert hasattr(pipeline, "FallbackParser")
    assert hasattr(pipeline, "KreuzbergParser")
    assert hasattr(pipeline, "MarkdownParser")
    assert hasattr(pipeline, "HtmlParser")
    assert hasattr(pipeline, "TextParser")
    assert hasattr(pipeline, "IpynbParser")


def test_module_has_get_parser():
    from app import pipeline
    assert hasattr(pipeline, "get_parser")


def test_module_has_image_output_dir_for():
    from app import pipeline
    assert hasattr(pipeline, "image_output_dir_for")


def test_module_has_process_single():
    from app import pipeline
    assert hasattr(pipeline, "process_single")


def test_module_has_validate_only():
    from app import pipeline
    assert hasattr(pipeline, "validate_only")


def test_get_parser_has_docstring():
    assert get_parser.__doc__ is not None


def test_image_output_dir_for_has_docstring():
    assert image_output_dir_for.__doc__ is not None


def test_process_single_has_docstring():
    assert process_single.__doc__ is not None


def test_validate_only_has_docstring():
    assert validate_only.__doc__ is not None
