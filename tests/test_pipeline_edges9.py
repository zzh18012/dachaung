r"""app/pipeline.py 边角测试 - 第九轮（Round 203）。

补强已有 edges/edges2-8 + errors/helpers（共 ~767 测试）未覆盖的深度：
- get_parser 错误消息内容（含全部支持 parser 列表）
- get_parser 返回类型的 version/name 属性
- image_output_dir_for 各种 source_hash 长度边界
- image_output_dir_for None 路径 / 路径含 / 路径无 parent
- process_single 错误矩阵深度（hash_io_error/chunker_failed/write_failed/schema_validation_failed）
- process_single write_json=False 不写盘
- process_single output_path=None 不写盘
- process_single 返回值 tuple 长度与类型
- validate_only 各种消息格式
- 模块结构与签名深度
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from app.chunkers import StructuralChunker
from app.models import Document, ErrorRecord
from app.parsers import Parser
from app.parsers.fallback_parser import FallbackParser
from app.parsers.html_parser import HtmlParser
from app.parsers.ipynb_parser import IpynbParser
from app.parsers.kreuzberg_parser import KreuzbergParser
from app.parsers.markdown_parser import MarkdownParser
from app.parsers.text_parser import TextParser
from app.pipeline import (
    get_parser,
    image_output_dir_for,
    process_single,
    validate_only,
)


# =========================================================================
# get_parser 深度
# =========================================================================


def test_get_parser_fallback_returns_fallback_parser():
    p = get_parser("fallback")
    assert isinstance(p, FallbackParser)


def test_get_parser_kreuzberg_returns_kreuzberg_parser():
    p = get_parser("kreuzberg")
    assert isinstance(p, KreuzbergParser)


def test_get_parser_markdown_returns_markdown_parser():
    p = get_parser("markdown")
    assert isinstance(p, MarkdownParser)


def test_get_parser_html_returns_html_parser():
    p = get_parser("html")
    assert isinstance(p, HtmlParser)


def test_get_parser_text_returns_text_parser():
    p = get_parser("text")
    assert isinstance(p, TextParser)


def test_get_parser_ipynb_returns_ipynb_parser():
    p = get_parser("ipynb")
    assert isinstance(p, IpynbParser)


def test_get_parser_fallback_name_attribute():
    p = get_parser("fallback")
    assert p.name == "fallback"


def test_get_parser_kreuzberg_name_attribute():
    p = get_parser("kreuzberg")
    assert p.name == "kreuzberg"


def test_get_parser_markdown_name_attribute():
    p = get_parser("markdown")
    assert p.name == "markdown"


def test_get_parser_html_name_attribute():
    p = get_parser("html")
    assert p.name == "html"


def test_get_parser_text_name_attribute():
    p = get_parser("text")
    assert p.name == "text"


def test_get_parser_ipynb_name_attribute():
    p = get_parser("ipynb")
    assert p.name == "ipynb"


def test_get_parser_all_return_parser_subclass():
    for name in ("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"):
        p = get_parser(name)
        assert isinstance(p, Parser)


def test_get_parser_fallback_each_call_returns_new_instance():
    p1 = get_parser("fallback")
    p2 = get_parser("fallback")
    assert p1 is not p2


def test_get_parser_unknown_raises_value_error():
    with pytest.raises(ValueError):
        get_parser("unknown_parser")


def test_get_parser_unknown_error_message_lists_supported():
    with pytest.raises(ValueError) as ei:
        get_parser("unknown_parser")
    msg = str(ei.value)
    assert "fallback" in msg
    assert "kreuzberg" in msg
    assert "markdown" in msg
    assert "html" in msg
    assert "text" in msg
    assert "ipynb" in msg


def test_get_parser_unknown_error_message_contains_passed_name():
    with pytest.raises(ValueError) as ei:
        get_parser("xxx-yyy")
    assert "xxx-yyy" in str(ei.value)


def test_get_parser_signature():
    sig = inspect.signature(get_parser)
    params = list(sig.parameters)
    assert params == ["name", "image_output_dir"]
    assert sig.parameters["image_output_dir"].default is None


def test_get_parser_image_output_dir_passthrough_to_fallback():
    p = get_parser("fallback", image_output_dir="/tmp/imgs")
    assert isinstance(p, FallbackParser)


# =========================================================================
# image_output_dir_for 深度
# =========================================================================


def test_image_output_dir_for_none_returns_none():
    assert image_output_dir_for(None, "a" * 64) is None


def test_image_output_dir_for_str_path():
    result = image_output_dir_for("/tmp/out.json", "a" * 64)
    assert isinstance(result, Path)
    assert str(result).endswith(f"images-{'a' * 16}")


def test_image_output_dir_for_pathlib_path():
    result = image_output_dir_for(Path("/tmp/out.json"), "a" * 64)
    assert isinstance(result, Path)


def test_image_output_dir_for_short_hash_uses_full_hash_prefix():
    """source_hash[:16] 对短 hash 取全部。"""
    result = image_output_dir_for("/tmp/out.json", "abc")
    assert "images-abc" == result.name


def test_image_output_dir_for_empty_hash_empty_dir_name():
    """source_hash='' → source_hash[:16]='' → 目录名 images-。"""
    result = image_output_dir_for("/tmp/out.json", "")
    assert result.name == "images-"


def test_image_output_dir_for_uses_first_16_chars():
    result = image_output_dir_for("/tmp/out.json", "0123456789abcdefXYZ")
    assert result.name == "images-0123456789abcdef"


def test_image_output_dir_for_exactly_16():
    result = image_output_dir_for("/tmp/out.json", "0123456789abcdef")
    assert result.name == "images-0123456789abcdef"


def test_image_output_dir_for_15_chars():
    result = image_output_dir_for("/tmp/out.json", "0123456789abcde")
    assert result.name == "images-0123456789abcde"


def test_image_output_dir_for_1_char():
    result = image_output_dir_for("/tmp/out.json", "x")
    assert result.name == "images-x"


def test_image_output_dir_for_path_no_parent():
    """路径只有文件名（无 /）→ parent 是 cwd。"""
    result = image_output_dir_for("out.json", "a" * 64)
    assert result.parent == Path(".").resolve() or result.parent == Path(".")


def test_image_output_dir_for_path_with_parent():
    result = image_output_dir_for("/tmp/a/out.json", "a" * 64)
    assert result.parent == Path("/tmp/a")


def test_image_output_dir_for_path_deep_nested():
    result = image_output_dir_for("/a/b/c/d/e/out.json", "a" * 64)
    assert result.parent == Path("/a/b/c/d/e")


def test_image_output_dir_for_returns_path_or_none():
    result_none = image_output_dir_for(None, "a" * 64)
    result_path = image_output_dir_for("/tmp/out.json", "a" * 64)
    assert result_none is None
    assert isinstance(result_path, Path)


def test_image_output_dir_for_idempotent():
    a = image_output_dir_for("/tmp/out.json", "a" * 64)
    b = image_output_dir_for("/tmp/out.json", "a" * 64)
    assert a == b


def test_image_output_dir_for_signature():
    sig = inspect.signature(image_output_dir_for)
    params = list(sig.parameters)
    assert params == ["output_path", "source_hash"]


# =========================================================================
# process_single 错误矩阵深度
# =========================================================================


def test_process_single_nonexistent_input_returns_none(tmp_path):
    doc, errors = process_single(tmp_path / "nope.txt")
    assert doc is None
    assert len(errors) >= 1


def test_process_single_nonexistent_input_error_code(tmp_path):
    _, errors = process_single(tmp_path / "nope.txt")
    assert errors[0].code == "file_not_found"


def test_process_single_nonexistent_input_details_has_path(tmp_path):
    nope = tmp_path / "nope.txt"
    _, errors = process_single(nope)
    assert errors[0].details["path"] == str(nope)


def test_process_single_unsupported_extension_returns_none(tmp_path):
    p = tmp_path / "a.xyz"
    p.write_text("hello", encoding="utf-8")
    doc, errors = process_single(p)
    assert doc is None
    assert len(errors) >= 1


def test_process_single_unknown_parser_returns_none(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello", encoding="utf-8")
    doc, errors = process_single(p, parser_name="xxx")
    assert doc is None
    assert errors[0].code == "unexpected_parser_error"


def test_process_single_unknown_parser_details_has_parser_name(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello", encoding="utf-8")
    _, errors = process_single(p, parser_name="xxx")
    assert errors[0].details["parser_name"] == "xxx"


def test_process_single_unknown_parser_details_has_path(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello", encoding="utf-8")
    _, errors = process_single(p, parser_name="xxx")
    assert errors[0].details["path"] == str(p)


def test_process_single_empty_file_no_extracted_elements(tmp_path):
    """text parser 解析空文件 → 0 elements → no_extracted_elements。"""
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    doc, errors = process_single(p, parser_name="text")
    assert doc is None
    assert errors[0].code == "no_extracted_elements"


def test_process_single_no_extracted_elements_details_has_source_type(tmp_path):
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    _, errors = process_single(p, parser_name="text")
    assert errors[0].details["source_type"] == "text"


def test_process_single_no_extracted_elements_details_has_warnings(tmp_path):
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    _, errors = process_single(p, parser_name="text")
    assert "warnings" in errors[0].details
    assert isinstance(errors[0].details["warnings"], list)


def test_process_single_no_extracted_elements_message_mentions_scan(tmp_path):
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    _, errors = process_single(p, parser_name="text")
    assert "扫描件" in errors[0].message or "element" in errors[0].message


def test_process_single_chunker_failed_via_monkeypatch(tmp_path, monkeypatch):
    """强制 chunker 抛异常 → chunker_failed。"""
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")

    def boom(*args, **kwargs):
        raise RuntimeError("chunker boom")

    monkeypatch.setattr(StructuralChunker, "chunk", boom)
    _, errors = process_single(p, parser_name="text")
    codes = [e.code for e in errors]
    assert "chunker_failed" in codes


def test_process_single_chunker_failed_details_has_exception_type(tmp_path, monkeypatch):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")

    def boom(*args, **kwargs):
        raise RuntimeError("chunker boom")

    monkeypatch.setattr(StructuralChunker, "chunk", boom)
    _, errors = process_single(p, parser_name="text")
    chunker_err = next(e for e in errors if e.code == "chunker_failed")
    assert chunker_err.details["exception_type"] == "RuntimeError"


def test_process_single_write_failed_via_monkeypatch(tmp_path, monkeypatch):
    """write_json=True 时 json.dump 抛 OSError → write_failed。"""
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")
    out = tmp_path / "out.json"

    def boom(*args, **kwargs):
        raise OSError("disk full")

    from app import pipeline as pl

    monkeypatch.setattr(pl.json, "dump", boom)
    doc, errors = process_single(p, out, parser_name="text", write_json=True)
    codes = [e.code for e in errors]
    assert "write_failed" in codes


def test_process_single_hash_io_error_via_monkeypatch(tmp_path, monkeypatch):
    """compute_file_hash 抛 OSError → hash_io_error。"""
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")

    from app import pipeline as pl

    def boom(*args, **kwargs):
        raise OSError("io boom")

    monkeypatch.setattr(pl, "compute_file_hash", boom)
    _, errors = process_single(p, parser_name="text")
    assert errors[0].code == "hash_io_error"


def test_process_single_hash_io_error_details_has_exception_type(tmp_path, monkeypatch):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")

    from app import pipeline as pl

    def boom(*args, **kwargs):
        raise OSError("io boom")

    monkeypatch.setattr(pl, "compute_file_hash", boom)
    _, errors = process_single(p, parser_name="text")
    assert errors[0].details["exception_type"] == "OSError"


def test_process_single_hash_io_error_details_has_path(tmp_path, monkeypatch):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")

    from app import pipeline as pl

    def boom(*args, **kwargs):
        raise OSError("io boom")

    monkeypatch.setattr(pl, "compute_file_hash", boom)
    _, errors = process_single(p, parser_name="text")
    assert errors[0].details["path"] == str(p)


def test_process_single_schema_validation_failed_via_monkeypatch(tmp_path, monkeypatch):
    """validate 抛 SchemaValidationError → schema_validation_failed。"""
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")

    from app.schema import SchemaValidationError

    def boom(*args, **kwargs):
        raise SchemaValidationError("schema boom")

    from app import pipeline as pl

    monkeypatch.setattr(pl, "validate", boom)
    _, errors = process_single(p, parser_name="text")
    codes = [e.code for e in errors]
    assert "schema_validation_failed" in codes


def test_process_single_schema_validation_failed_truncates_errors(tmp_path, monkeypatch):
    """validation_errors 截断到前 20 条。"""
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")

    from app.schema import SchemaValidationError

    many_errors = [{"path": [str(i)], "message": "m", "schema_path": []} for i in range(50)]

    def boom(*args, **kwargs):
        raise SchemaValidationError("schema boom", errors=many_errors)

    from app import pipeline as pl

    monkeypatch.setattr(pl, "validate", boom)
    _, errors = process_single(p, parser_name="text")
    schema_err = next(e for e in errors if e.code == "schema_validation_failed")
    assert len(schema_err.details["validation_errors"]) <= 20


# =========================================================================
# process_single 写盘行为
# =========================================================================


def test_process_single_does_not_write_when_write_json_false(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")
    out = tmp_path / "out.json"
    process_single(p, out, parser_name="text", write_json=False)
    assert not out.exists()


def test_process_single_does_not_write_when_output_path_none(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")
    doc, errors = process_single(p, output_path=None, parser_name="text")
    assert doc is not None
    assert errors == []


def test_process_single_writes_when_output_given_and_write_true(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")
    out = tmp_path / "out.json"
    process_single(p, out, parser_name="text", write_json=True)
    assert out.exists()


def test_process_single_creates_nested_output_parent(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")
    out = tmp_path / "a" / "b" / "c" / "out.json"
    process_single(p, out, parser_name="text", write_json=True)
    assert out.exists()


def test_process_single_writes_valid_json_content(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")
    out = tmp_path / "out.json"
    process_single(p, out, parser_name="text", write_json=True)
    text = out.read_text(encoding="utf-8")
    data = json.loads(text)
    assert isinstance(data, dict)
    assert "document_id" in data


def test_process_single_writes_utf8_content(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("你好世界", encoding="utf-8")
    out = tmp_path / "out.json"
    process_single(p, out, parser_name="text", write_json=True)
    raw = out.read_bytes()
    text = raw.decode("utf-8")
    assert "你好世界" in text


def test_process_single_writes_with_indent_2(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello", encoding="utf-8")
    out = tmp_path / "out.json"
    process_single(p, out, parser_name="text", write_json=True)
    text = out.read_text(encoding="utf-8")
    assert "\n  " in text  # 缩进


def test_process_single_writes_ensure_ascii_false(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("中文", encoding="utf-8")
    out = tmp_path / "out.json"
    process_single(p, out, parser_name="text", write_json=True)
    text = out.read_text(encoding="utf-8")
    # ensure_ascii=False → 中文字符直接出现，不转 \uXXXX
    assert "中" in text


def test_process_single_does_not_mutate_input_file(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")
    snapshot = p.read_text(encoding="utf-8")
    process_single(p, tmp_path / "out.json", parser_name="text")
    assert p.read_text(encoding="utf-8") == snapshot


# =========================================================================
# process_single 成功路径深度
# =========================================================================


def test_process_single_text_success_returns_document(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")
    doc, errors = process_single(p, parser_name="text")
    assert isinstance(doc, Document)
    assert errors == []


def test_process_single_text_success_doc_has_chunks(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")
    doc, _ = process_single(p, parser_name="text")
    assert len(doc.chunks) >= 1


def test_process_single_text_success_chunk_has_text(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")
    doc, _ = process_single(p, parser_name="text")
    assert doc.chunks[0].text


def test_process_single_markdown_success(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("# Title\n\nbody", encoding="utf-8")
    doc, errors = process_single(p, parser_name="markdown")
    assert doc is not None
    assert errors == []


def test_process_single_html_success(tmp_path):
    p = tmp_path / "a.html"
    p.write_text("<html><body><p>hello</p></body></html>", encoding="utf-8")
    doc, errors = process_single(p, parser_name="html")
    assert doc is not None
    assert errors == []


def test_process_single_ipynb_success(tmp_path):
    p = tmp_path / "a.ipynb"
    nb = {
        "cells": [
            {"cell_type": "markdown", "source": ["# Title"]},
            {"cell_type": "code", "source": ["print(1)"]},
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc, errors = process_single(p, parser_name="ipynb")
    assert doc is not None
    assert errors == []


def test_process_single_default_parser_name_is_fallback_signature():
    """不传 parser_name → 默认 'fallback'（从签名验证）。"""
    sig = inspect.signature(process_single)
    assert sig.parameters["parser_name"].default == "fallback"


def test_process_single_default_max_chars_800(tmp_path):
    """默认 max_chars=800。"""
    p = tmp_path / "a.txt"
    p.write_text("a" * 1000, encoding="utf-8")
    doc, _ = process_single(p, parser_name="text")
    # 1000 chars / 800 应至少分 2 块
    assert len(doc.chunks) >= 2


def test_process_single_custom_max_chars(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("a" * 1000, encoding="utf-8")
    doc, _ = process_single(p, parser_name="text", max_chars=400)
    assert len(doc.chunks) >= 3


def test_process_single_returns_tuple(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello", encoding="utf-8")
    result = process_single(p, parser_name="text")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_process_single_signature():
    sig = inspect.signature(process_single)
    params = list(sig.parameters)
    assert params == ["input_path", "output_path", "parser_name", "max_chars", "write_json"]
    assert sig.parameters["output_path"].default is None
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["write_json"].default is True


def test_process_single_keyword_only_args():
    """parser_name/max_chars/write_json 是 keyword-only？检查是否有 *。"""
    sig = inspect.signature(process_single)
    # 实际：input_path, output_path, *, parser_name, max_chars, write_json
    # 检查 parser_name 是 KEYWORD_ONLY
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["write_json"].kind == inspect.Parameter.KEYWORD_ONLY


def test_process_single_parser_name_keyword_only_must_pass_by_keyword(tmp_path):
    """parser_name 必须以 keyword 传入（KEYWORD_ONLY）。"""
    p = tmp_path / "a.txt"
    p.write_text("hello", encoding="utf-8")
    out = tmp_path / "o.json"
    # positional input + output ok；parser_name 必须 keyword
    process_single(p, out, parser_name="text")
    assert out.exists()


def test_process_single_idempotent_same_input(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")
    doc1, errs1 = process_single(p, parser_name="text")
    doc2, errs2 = process_single(p, parser_name="text")
    assert doc1 is not None
    assert doc2 is not None
    assert doc1.to_dict() == doc2.to_dict()
    assert errs1 == errs2


# =========================================================================
# validate_only 深度
# =========================================================================


def test_validate_only_returns_true_for_valid(tmp_path, valid_doc):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(valid_doc), encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is True
    assert msg == "OK"


def test_validate_only_returns_false_for_missing_file(tmp_path):
    ok, msg = validate_only(tmp_path / "no.json")
    assert ok is False
    assert "no.json" in msg or "不存在" in msg


def test_validate_only_returns_false_for_invalid_json(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{not json", encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is False
    assert "JSON" in msg


def test_validate_only_returns_false_for_schema_failure(tmp_path, valid_doc):
    del valid_doc["document_id"]
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(valid_doc), encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is False
    assert "Schema" in msg or "校验" in msg


def test_validate_only_str_path(tmp_path, valid_doc):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(valid_doc), encoding="utf-8")
    ok, msg = validate_only(str(p))
    assert ok is True


def test_validate_only_returns_tuple(tmp_path, valid_doc):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(valid_doc), encoding="utf-8")
    result = validate_only(p)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_validate_only_first_element_bool(tmp_path, valid_doc):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(valid_doc), encoding="utf-8")
    ok, _ = validate_only(p)
    assert isinstance(ok, bool)


def test_validate_only_second_element_str(tmp_path, valid_doc):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(valid_doc), encoding="utf-8")
    _, msg = validate_only(p)
    assert isinstance(msg, str)


def test_validate_only_signature():
    sig = inspect.signature(validate_only)
    params = list(sig.parameters)
    assert params == ["json_path"]


def test_validate_only_no_default():
    """json_path 必填。"""
    sig = inspect.signature(validate_only)
    assert sig.parameters["json_path"].default is inspect.Parameter.empty


@pytest.fixture
def valid_doc() -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "/tmp/x.txt",
        "source_type": "text",
        "source_hash": "a" * 64,
        "parser_name": "text",
        "parser_version": "0.1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_all_exact():
    import app.pipeline as m
    assert set(m.__all__) == {
        "get_parser", "image_output_dir_for", "process_single", "validate_only",
    }


def test_module_all_is_list():
    import app.pipeline as m
    assert isinstance(m.__all__, list)


def test_module_all_no_duplicates():
    import app.pipeline as m
    assert len(m.__all__) == len(set(m.__all__))


def test_module_uses_future_annotations():
    import app.pipeline as m
    sig = inspect.signature(m.process_single)
    assert isinstance(sig.return_annotation, str)


def test_module_imports_json():
    import app.pipeline as m
    assert hasattr(m, "json")


def test_module_imports_path():
    import app.pipeline as m
    assert hasattr(m, "Path")


def test_module_imports_any():
    import app.pipeline as m
    assert hasattr(m, "Any")


def test_module_imports_structural_chunker():
    import app.pipeline as m
    assert hasattr(m, "StructuralChunker")


def test_module_imports_compute_file_hash():
    import app.pipeline as m
    assert hasattr(m, "compute_file_hash")


def test_module_imports_document_models():
    import app.pipeline as m
    assert hasattr(m, "Document")
    assert hasattr(m, "ErrorRecord")


def test_module_imports_parser_base():
    import app.pipeline as m
    assert hasattr(m, "Parser")
    assert hasattr(m, "ParserError")


def test_module_imports_all_parsers():
    import app.pipeline as m
    assert hasattr(m, "FallbackParser")
    assert hasattr(m, "HtmlParser")
    assert hasattr(m, "IpynbParser")
    assert hasattr(m, "KreuzbergParser")
    assert hasattr(m, "MarkdownParser")
    assert hasattr(m, "TextParser")


def test_module_imports_schema_validate():
    import app.pipeline as m
    assert hasattr(m, "validate")
    assert hasattr(m, "SchemaValidationError")


def test_module_docstring_present():
    import app.pipeline as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_invariants():
    import app.pipeline as m
    doc = m.__doc__
    assert "Schema 校验" in doc or "校验" in doc
    assert "单文件" in doc or "结构化" in doc


def test_module_no_silence_unused():
    """pipeline.py 没有保留未用 import 的辅助函数。"""
    import app.pipeline as m
    assert not hasattr(m, "_silence_unused_import")


def test_module_all_entries_exported():
    import app.pipeline as m
    for name in m.__all__:
        assert hasattr(m, name)


# =========================================================================
# 综合行为
# =========================================================================


def test_full_text_pipeline_with_chunks(tmp_path):
    """完整 text pipeline：多 chunk 生成。"""
    p = tmp_path / "a.txt"
    p.write_text("Sentence one. " * 100, encoding="utf-8")
    out = tmp_path / "o.json"
    doc, errors = process_single(p, out, parser_name="text", max_chars=200)
    assert doc is not None
    assert errors == []
    assert len(doc.chunks) >= 5
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "chunks" in data
    assert len(data["chunks"]) == len(doc.chunks)


def test_pipeline_roundtrip_validates(tmp_path):
    """写出的 JSON 能被 validate_only 通过。"""
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")
    out = tmp_path / "o.json"
    process_single(p, out, parser_name="text")
    ok, msg = validate_only(out)
    assert ok is True
    assert msg == "OK"


def test_pipeline_with_various_parsers_each_produces_valid_output(tmp_path):
    """每个 parser 处理对应文件后产出能通过 schema 校验的 JSON。"""
    cases = [
        ("a.txt", "hello world", "text"),
        ("a.md", "# T\n\nbody", "markdown"),
        ("a.html", "<p>hi</p>", "html"),
        ("a.ipynb", json.dumps({
            "cells": [{"cell_type": "markdown", "source": ["# T"]}],
            "metadata": {}, "nbformat": 4, "nbformat_minor": 5,
        }), "ipynb"),
    ]
    for fname, content, parser_name in cases:
        p = tmp_path / fname
        p.write_text(content, encoding="utf-8")
        out = tmp_path / (fname + ".json")
        doc, errors = process_single(p, out, parser_name=parser_name)
        assert doc is not None, f"{parser_name} failed: {errors}"
        assert errors == []
        ok, _ = validate_only(out)
        assert ok is True, f"{parser_name} output failed schema"
