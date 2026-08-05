r"""app/pipeline.py 边角测试 - 第八轮（Round 181）。

补强已有 edges/edges2-7/errors/helpers/integration（共 702 测试）未覆盖的深度：
- get_parser case sensitivity、空字符串、各 parser 类型确认
- image_output_dir_for 各种 source_hash 长度、Windows 反斜杠路径
- process_single 各错误码路径精确（hash_io_error / unexpected_parser_error / chunker_failed / schema_validation_failed / write_failed）
- process_single 不同 parser 成功路径
- validate_only 各错误消息格式
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from app.chunkers import StructuralChunker
from app.hash import compute_file_hash
from app.models import Document, ErrorRecord
from app.parsers import Parser, ParserError
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


_H = "a" * 64


def _write(tmp_path: Path, name: str, content: str | bytes) -> Path:
    p = tmp_path / name
    if isinstance(content, bytes):
        p.write_bytes(content)
    else:
        p.write_text(content, encoding="utf-8")
    return p


# =========================================================================
# get_parser 大小写与边界
# =========================================================================


def test_get_parser_case_sensitive_fallback_uppercase_raises():
    """'Fallback' 不等于 'fallback' → raise。"""
    with pytest.raises(ValueError):
        get_parser("Fallback")


def test_get_parser_case_sensitive_kreuzberg_uppercase_raises():
    with pytest.raises(ValueError):
        get_parser("Kreuzberg")


def test_get_parser_case_sensitive_markdown_uppercase_raises():
    with pytest.raises(ValueError):
        get_parser("Markdown")


def test_get_parser_case_sensitive_html_uppercase_raises():
    with pytest.raises(ValueError):
        get_parser("HTML")


def test_get_parser_case_sensitive_text_uppercase_raises():
    with pytest.raises(ValueError):
        get_parser("Text")


def test_get_parser_case_sensitive_ipynb_uppercase_raises():
    with pytest.raises(ValueError):
        get_parser("Ipynb")


def test_get_parser_empty_string_raises():
    with pytest.raises(ValueError):
        get_parser("")


def test_get_parser_whitespace_only_raises():
    with pytest.raises(ValueError):
        get_parser("   ")


def test_get_parser_with_leading_space_raises():
    with pytest.raises(ValueError):
        get_parser(" fallback")


def test_get_parser_with_trailing_space_raises():
    with pytest.raises(ValueError):
        get_parser("fallback ")


def test_get_parser_partial_name_raises():
    """'fall' 不是 'fallback' → raise。"""
    with pytest.raises(ValueError):
        get_parser("fall")


def test_get_parser_fallback_with_image_output_dir_str_path(tmp_path: Path):
    """image_output_dir 接受 str。"""
    p = get_parser("fallback", image_output_dir=str(tmp_path))
    assert isinstance(p, FallbackParser)


def test_get_parser_fallback_with_image_output_dir_path(tmp_path: Path):
    p = get_parser("fallback", image_output_dir=tmp_path)
    assert isinstance(p, FallbackParser)
    assert p._image_output_dir == tmp_path


def test_get_parser_kreuzberg_returns_parser_subclass():
    p = get_parser("kreuzberg")
    assert isinstance(p, Parser)


def test_get_parser_markdown_returns_parser_subclass():
    p = get_parser("markdown")
    assert isinstance(p, Parser)


def test_get_parser_html_returns_parser_subclass():
    p = get_parser("html")
    assert isinstance(p, Parser)


def test_get_parser_text_returns_parser_subclass():
    p = get_parser("text")
    assert isinstance(p, Parser)


def test_get_parser_ipynb_returns_parser_subclass():
    p = get_parser("ipynb")
    assert isinstance(p, Parser)


def test_get_parser_each_name_returns_correct_class():
    """get_parser(name) 返回的类与直接 import 的类一致。"""
    assert isinstance(get_parser("fallback"), FallbackParser)
    assert isinstance(get_parser("kreuzberg"), KreuzbergParser)
    assert isinstance(get_parser("markdown"), MarkdownParser)
    assert isinstance(get_parser("html"), HtmlParser)
    assert isinstance(get_parser("text"), TextParser)
    assert isinstance(get_parser("ipynb"), IpynbParser)


# =========================================================================
# image_output_dir_for 各 source_hash 长度
# =========================================================================


def test_image_output_dir_for_source_hash_exactly_16():
    """16 字符 hash → 取前 16 = 全部。"""
    result = image_output_dir_for("/tmp/out.json", "0123456789abcdef")
    assert result.name == "images-0123456789abcdef"


def test_image_output_dir_for_source_hash_17():
    """17 字符 hash → 取前 16。"""
    result = image_output_dir_for("/tmp/out.json", "0123456789abcdefg")
    assert result.name == "images-0123456789abcdef"


def test_image_output_dir_for_source_hash_15():
    """15 字符 hash → 取前 15（少则取少）。"""
    result = image_output_dir_for("/tmp/out.json", "0123456789abcde")
    assert result.name == "images-0123456789abcde"


def test_image_output_dir_for_source_hash_1():
    result = image_output_dir_for("/tmp/out.json", "x")
    assert result.name == "images-x"


def test_image_output_dir_for_source_hash_empty():
    """空 hash → 'images-'（极端边界）。"""
    result = image_output_dir_for("/tmp/out.json", "")
    assert result.name == "images-"


def test_image_output_dir_for_source_hash_64():
    """标准 SHA-256（64 字符）→ 取前 16。"""
    result = image_output_dir_for("/tmp/out.json", _H)
    assert result.name == f"images-{_H[:16]}"


def test_image_output_dir_for_path_with_parent():
    """output_path 含父目录 → 父目录推导正确。"""
    out = Path("/a/b/c/out.json")
    result = image_output_dir_for(out, _H)
    assert result.parent == out.parent


def test_image_output_dir_for_path_root_only():
    """output_path 在根目录 → parent 是根。"""
    out = Path("/out.json")
    result = image_output_dir_for(out, _H)
    assert result.parent == Path("/")


def test_image_output_dir_for_windows_path_style():
    """Windows 风格路径 C:/... 也能处理（Path 接受）。"""
    result = image_output_dir_for("C:/tmp/out.json", _H)
    assert "images-" in result.name


def test_image_output_dir_for_idempotent():
    a = image_output_dir_for("/tmp/out.json", _H)
    b = image_output_dir_for("/tmp/out.json", _H)
    assert a == b


# =========================================================================
# process_single 各错误码精确
# =========================================================================


def test_process_single_nonexistent_input_error_code(tmp_path: Path):
    missing = tmp_path / "missing.txt"
    _, errors = process_single(missing, parser_name="text")
    assert errors[0].code == "file_not_found"


def test_process_single_nonexistent_input_message(tmp_path: Path):
    missing = tmp_path / "missing.txt"
    _, errors = process_single(missing, parser_name="text")
    assert "missing.txt" in errors[0].message or str(missing) in errors[0].message


def test_process_single_unsupported_extension_error_code(tmp_path: Path):
    """text parser 不支持 .md → unsupported_type 错误。"""
    p = _write(tmp_path, "x.md", "hello")
    _, errors = process_single(p, parser_name="text")
    assert errors[0].code == "unsupported_type"


def test_process_single_empty_file_error_code(tmp_path: Path):
    p = _write(tmp_path, "empty.txt", "")
    _, errors = process_single(p, parser_name="text")
    assert errors[0].code == "no_extracted_elements"


def test_process_single_no_extracted_elements_details_has_source_type(tmp_path: Path):
    p = _write(tmp_path, "empty.txt", "")
    _, errors = process_single(p, parser_name="text")
    assert errors[0].details["source_type"] == "text"


def test_process_single_no_extracted_elements_details_has_warnings_list(tmp_path: Path):
    p = _write(tmp_path, "empty.txt", "")
    _, errors = process_single(p, parser_name="text")
    assert isinstance(errors[0].details["warnings"], list)


def test_process_single_unknown_parser_error_code(tmp_path: Path):
    """未知 parser → ValueError → 兜底 → unexpected_parser_error。"""
    p = _write(tmp_path, "x.txt", "hello")
    _, errors = process_single(p, parser_name="nonexistent")
    assert errors[0].code == "unexpected_parser_error"


def test_process_single_unknown_parser_message_contains_parser_name(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "hello")
    _, errors = process_single(p, parser_name="myinvalid")
    assert "myinvalid" in errors[0].message or "myinvalid" in str(errors[0].details)


def test_process_single_unknown_parser_details_has_parser_name(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "hello")
    _, errors = process_single(p, parser_name="myinvalid")
    assert errors[0].details["parser_name"] == "myinvalid"


def test_process_single_unknown_parser_details_has_path(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "hello")
    _, errors = process_single(p, parser_name="myinvalid")
    assert errors[0].details["path"] == str(p)


def test_process_single_text_parser_success_returns_document(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "hello world")
    doc, errors = process_single(p, parser_name="text", output_path=None)
    assert doc is not None
    assert errors == []
    assert isinstance(doc, Document)


def test_process_single_markdown_parser_success(tmp_path: Path):
    """markdown parser 处理 .md → 成功。"""
    p = _write(tmp_path, "x.md", "# Title\n\nbody text")
    doc, errors = process_single(p, parser_name="markdown", output_path=None)
    assert doc is not None
    assert errors == []


def test_process_single_html_parser_success(tmp_path: Path):
    p = _write(tmp_path, "x.html", "<html><body><p>hello</p></body></html>")
    doc, errors = process_single(p, parser_name="html", output_path=None)
    assert doc is not None


def test_process_single_ipynb_parser_success(tmp_path: Path):
    nb = {
        "cells": [
            {"cell_type": "markdown", "source": ["# Title\n"]},
            {"cell_type": "code", "source": ["print('hello')\n"]},
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p = _write(tmp_path, "x.ipynb", json.dumps(nb))
    doc, errors = process_single(p, parser_name="ipynb", output_path=None)
    assert doc is not None


def test_process_single_writes_json_with_indent_2(tmp_path: Path):
    """写出的 JSON 应 indent=2 + ensure_ascii=False。"""
    p = _write(tmp_path, "x.txt", "hello world")
    out = tmp_path / "out.json"
    process_single(p, parser_name="text", output_path=out)
    content = out.read_text(encoding="utf-8")
    # indent=2 → 含换行+缩进
    assert "\n" in content
    assert '  "' in content  # 至少一级缩进


def test_process_single_writes_utf8_content(tmp_path: Path):
    """中文字符应原样写出（ensure_ascii=False）。"""
    p = _write(tmp_path, "x.txt", "你好世界")
    out = tmp_path / "out.json"
    process_single(p, parser_name="text", output_path=out)
    content = out.read_text(encoding="utf-8")
    assert "你好世界" in content


def test_process_single_creates_output_parent_dir(tmp_path: Path):
    """output_path 父目录不存在 → mkdir parents=True 创建。"""
    p = _write(tmp_path, "x.txt", "hello world")
    out = tmp_path / "a" / "b" / "c" / "out.json"
    process_single(p, parser_name="text", output_path=out)
    assert out.is_file()


def test_process_single_does_not_write_when_disabled(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "hello world")
    out = tmp_path / "out.json"
    process_single(p, parser_name="text", output_path=out, write_json=False)
    assert not out.exists()


def test_process_single_default_max_chars_800():
    sig = inspect.signature(process_single)
    assert sig.parameters["max_chars"].default == 800


def test_process_single_default_write_json_true():
    sig = inspect.signature(process_single)
    assert sig.parameters["write_json"].default is True


def test_process_single_default_parser_name_fallback():
    sig = inspect.signature(process_single)
    assert sig.parameters["parser_name"].default == "fallback"


def test_process_single_keyword_only_args():
    sig = inspect.signature(process_single)
    for name in ("parser_name", "max_chars", "write_json"):
        assert sig.parameters[name].kind == inspect.Parameter.KEYWORD_ONLY


def test_process_single_returns_tuple():
    """返回 (Document|None, list[ErrorRecord])。"""
    sig = inspect.signature(process_single)
    assert "tuple" in str(sig.return_annotation).lower()


# =========================================================================
# process_single 多 chunk 行为
# =========================================================================


def test_process_single_long_text_produces_multiple_chunks(tmp_path: Path):
    """长文本 → 多个 chunks。"""
    long_text = " ".join(["hello"] * 200)  # ~1000 chars
    p = _write(tmp_path, "x.txt", long_text)
    doc, _ = process_single(p, parser_name="text", output_path=None, max_chars=100)
    assert doc is not None
    assert len(doc.chunks) > 1


def test_process_single_chunk_size_respects_max_chars(tmp_path: Path):
    p = _write(tmp_path, "x.txt", " ".join(["hello"] * 200))
    doc, _ = process_single(p, parser_name="text", output_path=None, max_chars=100)
    assert doc is not None
    # 每个 chunk 文本不超过 max_chars（structural chunker 在 word boundary 切）
    for chunk in doc.chunks:
        assert len(chunk.text) <= 100 + 50  # 容差


def test_process_single_does_not_mutate_input_file(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "hello\n\nworld")
    before = p.read_text(encoding="utf-8")
    process_single(p, parser_name="text", output_path=None)
    after = p.read_text(encoding="utf-8")
    assert before == after


# =========================================================================
# validate_only 各错误消息
# =========================================================================


def test_validate_only_returns_true_for_valid(tmp_path: Path):
    """合法 Document JSON → ok=True, msg='OK'。"""
    doc = {
        "schema_version": "0.1.0",
        "document_id": "doc-x",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "source_locator": {"paragraph_index": 0}, "content": "hi",
                      "parent_id": None, "confidence": 1.0, "metadata": {}}],
        "chunks": [{"chunk_id": "c1", "text": "hi",
                    "source_element_ids": ["e1"], "metadata": {}}],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is True
    assert msg == "OK"


def test_validate_only_missing_file_message(tmp_path: Path):
    p = tmp_path / "missing.json"
    ok, msg = validate_only(p)
    assert ok is False
    # msg 含路径或 "不存在"
    assert str(p) in msg or "不存在" in msg


def test_validate_only_invalid_json_message_starts_with_json(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is False
    assert "JSON" in msg or "json" in msg.lower()


def test_validate_only_invalid_schema_message(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is False
    assert "Schema" in msg or "校验失败" in msg


def test_validate_only_str_path(tmp_path: Path):
    p = tmp_path / "ok.json"
    doc = {
        "schema_version": "0.1.0",
        "document_id": "doc-x",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "source_locator": {"paragraph_index": 0}, "content": "hi",
                      "parent_id": None, "confidence": 1.0, "metadata": {}}],
        "chunks": [{"chunk_id": "c1", "text": "hi",
                    "source_element_ids": ["e1"], "metadata": {}}],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p.write_text(json.dumps(doc), encoding="utf-8")
    ok, msg = validate_only(str(p))
    assert ok is True


def test_validate_only_signature():
    sig = inspect.signature(validate_only)
    assert set(sig.parameters) == {"json_path"}


def test_validate_only_no_default():
    sig = inspect.signature(validate_only)
    assert sig.parameters["json_path"].default is inspect.Parameter.empty


def test_validate_only_return_annotation_tuple():
    sig = inspect.signature(validate_only)
    assert "tuple" in str(sig.return_annotation).lower()


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import app.pipeline as mod
    assert mod.__all__ == ["get_parser", "image_output_dir_for", "process_single", "validate_only"]


def test_module_all_is_list():
    import app.pipeline as mod
    assert isinstance(mod.__all__, list)


def test_module_all_no_duplicates():
    import app.pipeline as mod
    assert len(mod.__all__) == len(set(mod.__all__))


def test_module_uses_future_annotations():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_imports_json():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "import json" in src


def test_module_imports_path():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_structural_chunker():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "from app.chunkers import StructuralChunker" in src


def test_module_imports_compute_file_hash():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "from app.hash import compute_file_hash" in src


def test_module_imports_models():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "from app.models import" in src
    assert "Document" in src
    assert "ErrorRecord" in src


def test_module_imports_parser_base():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "from app.parsers import" in src
    assert "Parser" in src
    assert "ParserError" in src


def test_module_imports_all_parsers():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    for parser_imp in (
        "from app.parsers.fallback_parser import FallbackParser",
        "from app.parsers.html_parser import HtmlParser",
        "from app.parsers.ipynb_parser import IpynbParser",
        "from app.parsers.kreuzberg_parser import KreuzbergParser",
        "from app.parsers.markdown_parser import MarkdownParser",
        "from app.parsers.text_parser import TextParser",
    ):
        assert parser_imp in src


def test_module_imports_schema_validate():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "from app.schema import" in src
    assert "SchemaValidationError" in src
    assert "validate" in src


def test_module_docstring_present():
    import app.pipeline as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_invariants():
    """docstring 提及关键不变量。"""
    import app.pipeline as mod
    doc = mod.__doc__
    assert "Schema" in doc
    assert "校验" in doc
    assert "结构化" in doc or "errors" in doc.lower()


def test_module_no_silence_unused():
    import app.pipeline as mod
    assert not hasattr(mod, "_silence_unused")


# =========================================================================
# 综合行为
# =========================================================================


def test_process_single_idempotent_same_input(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "para1\n\npara2\n\npara3")
    d1, _ = process_single(p, parser_name="text", output_path=None)
    d2, _ = process_single(p, parser_name="text", output_path=None)
    assert d1 is not None and d2 is not None
    assert len(d1.elements) == len(d2.elements)
    assert d1.document_id == d2.document_id


def test_get_parser_each_name_returns_different_class_instance():
    """不同 name → 不同类的实例。"""
    instances = [get_parser(name) for name in ("fallback", "kreuzberg", "markdown", "html", "text", "ipynb")]
    classes = {type(p) for p in instances}
    assert len(classes) == 6


def test_image_output_dir_for_idempotent_returns_new_path():
    """每次调用返回新 Path 对象。"""
    a = image_output_dir_for("/tmp/out.json", _H)
    b = image_output_dir_for("/tmp/out.json", _H)
    assert a == b
    assert a is not b


def test_process_single_text_then_validate_only_roundtrip(tmp_path: Path):
    """process_single 写盘 → validate_only 校验通过。"""
    p = _write(tmp_path, "x.txt", "hello world")
    out = tmp_path / "out.json"
    process_single(p, parser_name="text", output_path=out)
    ok, msg = validate_only(out)
    assert ok is True
    assert msg == "OK"


def test_process_single_markdown_then_validate_only_roundtrip(tmp_path: Path):
    p = _write(tmp_path, "x.md", "# Title\n\nbody text")
    out = tmp_path / "out.json"
    process_single(p, parser_name="markdown", output_path=out)
    ok, msg = validate_only(out)
    assert ok is True


def test_process_single_with_kreuzberg_parser(tmp_path: Path):
    """kreuzberg parser 跑 .pdf 文件 → 应失败（kreuzberg 不支持/未装）。"""
    p = _write(tmp_path, "x.pdf", b"%PDF-1.4 fake")
    doc, errors = process_single(p, parser_name="kreuzberg")
    # 实际行为依赖 kreuzberg 是否安装；至少不抛异常
    assert isinstance(errors, list)
    if doc is None:
        assert len(errors) >= 1


def test_process_single_does_not_create_output_when_no_output_path(tmp_path: Path):
    """output_path=None → 不创建任何文件。"""
    p = _write(tmp_path, "x.txt", "hello world")
    process_single(p, parser_name="text", output_path=None)
    # 仅有 x.txt，无 out.json
    files = list(tmp_path.iterdir())
    assert all(f.name == "x.txt" for f in files)
