r"""app/parsers/text_parser.py 边角测试 - 第五轮（Round 144）。

补强已有 base/edges/edges2/edges3/edges4（共 392 测试）未覆盖的深度：
- _TEXT_EXTENSIONS 常量
- _detect_text_source_type 深度
- _split_paragraphs 算法不变量
- TextParser 类属性
- 模块结构与签名
- 综合行为（多段落、空文件、CRLF/CR 换行）
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from app.models import Document, Element, WarningRecord
from app.parsers.base import Parser, ParserError
from app.parsers.text_parser import (
    _TEXT_EXTENSIONS,
    TextParser,
    _detect_text_source_type,
    _split_paragraphs,
)


# =========================================================================
# _TEXT_EXTENSIONS 常量
# =========================================================================


def test_text_extensions_count_two():
    assert len(_TEXT_EXTENSIONS) == 2


def test_text_extensions_contains_txt_and_text():
    assert ".txt" in _TEXT_EXTENSIONS
    assert ".text" in _TEXT_EXTENSIONS


def test_text_extensions_is_tuple():
    assert isinstance(_TEXT_EXTENSIONS, tuple)


# =========================================================================
# _detect_text_source_type 深度
# =========================================================================


def test_detect_text_source_type_txt():
    assert _detect_text_source_type(Path("a.txt")) == "text"


def test_detect_text_source_type_text():
    assert _detect_text_source_type(Path("a.text")) == "text"


def test_detect_text_source_type_uppercase():
    assert _detect_text_source_type(Path("a.TXT")) == "text"
    assert _detect_text_source_type(Path("a.TEXT")) == "text"


def test_detect_text_source_type_mixed_case():
    assert _detect_text_source_type(Path("a.TxT")) == "text"


def test_detect_text_source_type_rejects_pdf():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("a.pdf"))
    assert exc.value.code == "unsupported_type"


def test_detect_text_source_type_rejects_md():
    with pytest.raises(ParserError):
        _detect_text_source_type(Path("a.md"))


def test_detect_text_source_type_rejects_no_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("no_suffix"))
    assert "(无)" in exc.value.message


def test_detect_text_source_type_error_details_suffix_value():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("a.bin"))
    assert exc.value.details == {"suffix": ".bin"}


def test_detect_text_source_type_error_details_empty_when_no_suffix():
    with pytest.raises(ParserError) as exc:
        _detect_text_source_type(Path("README"))
    assert exc.value.details == {"suffix": ""}


# =========================================================================
# _split_paragraphs 深度
# =========================================================================


def test_split_paragraphs_empty_text():
    assert _split_paragraphs("") == []


def test_split_paragraphs_single_line():
    result = _split_paragraphs("hello")
    assert len(result) == 1
    assert result[0] == (1, "hello")


def test_split_paragraphs_two_paragraphs_one_blank_line():
    result = _split_paragraphs("para1\n\npara2")
    assert len(result) == 2
    assert result[0] == (1, "para1")
    assert result[1] == (3, "para2")


def test_split_paragraphs_two_paragraphs_multiple_blank_lines():
    """多个空行视为同一段落分隔。"""
    result = _split_paragraphs("para1\n\n\n\npara2")
    assert len(result) == 2
    assert result[0][1] == "para1"
    assert result[1][1] == "para2"
    # para2 在第 5 行
    assert result[1][0] == 5


def test_split_paragraphs_leading_blank_lines_skipped():
    result = _split_paragraphs("\n\nhello")
    assert len(result) == 1
    assert result[0] == (3, "hello")


def test_split_paragraphs_trailing_blank_lines_skipped():
    result = _split_paragraphs("hello\n\n")
    assert len(result) == 1
    assert result[0] == (1, "hello")


def test_split_paragraphs_only_blank_lines():
    assert _split_paragraphs("\n\n\n") == []


def test_split_paragraphs_whitespace_only_lines_skipped():
    """空白行（含 tab/space）视为空行。"""
    result = _split_paragraphs("hello\n   \nworld")
    assert len(result) == 2
    assert result[0] == (1, "hello")
    assert result[1] == (3, "world")


def test_split_paragraphs_multiline_paragraph():
    """连续非空行属于同一段落。"""
    result = _split_paragraphs("line1\nline2\nline3")
    assert len(result) == 1
    assert result[0] == (1, "line1\nline2\nline3")


def test_split_paragraphs_crlf_normalized():
    """CRLF → LF。"""
    result = _split_paragraphs("a\r\n\r\nb")
    assert len(result) == 2
    assert result[0][1] == "a"
    assert result[1][1] == "b"


def test_split_paragraphs_cr_normalized():
    """CR → LF。"""
    result = _split_paragraphs("a\r\rb")
    assert len(result) == 2


def test_split_paragraphs_returns_list_of_tuples():
    result = _split_paragraphs("x")
    assert isinstance(result, list)
    assert all(isinstance(t, tuple) for t in result)


def test_split_paragraphs_tuple_is_int_str():
    result = _split_paragraphs("x")
    assert isinstance(result[0][0], int)
    assert isinstance(result[0][1], str)


def test_split_paragraphs_content_strips_inner_lines():
    """段内每行内容不修改，但整体 strip。"""
    result = _split_paragraphs("  hello world  ")
    assert result[0][1] == "hello world"


def test_split_paragraphs_strips_each_para():
    result = _split_paragraphs("  a  \n\n  b  ")
    assert result[0][1] == "a"
    assert result[1][1] == "b"


# =========================================================================
# TextParser 类属性
# =========================================================================


def test_text_parser_name_value():
    assert TextParser.name == "text"


def test_text_parser_version_value():
    assert TextParser.version == "stdlib/0.1.0"


def test_text_parser_name_is_str():
    assert isinstance(TextParser.name, str)


def test_text_parser_version_is_str():
    assert isinstance(TextParser.version, str)


def test_text_parser_inherits_parser():
    assert issubclass(TextParser, Parser)


# =========================================================================
# TextParser.parse 行为
# =========================================================================


def test_parse_creates_paragraph_per_split(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("para1\n\npara2", encoding="utf-8")
    doc = TextParser().parse(p, source_hash="0" * 64)
    assert len(doc.elements) == 2
    assert all(e.type == "paragraph" for e in doc.elements)


def test_parse_element_id_format(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = TextParser().parse(p, source_hash="0" * 64)
    assert doc.elements[0].element_id.endswith("::e0000")


def test_parse_element_confidence_095(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = TextParser().parse(p, source_hash="0" * 64)
    assert doc.elements[0].confidence == 0.95


def test_parse_element_source_locator_line(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = TextParser().parse(p, source_hash="0" * 64)
    assert doc.elements[0].source_locator == {"line": 1}


def test_parse_element_metadata_empty(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = TextParser().parse(p, source_hash="0" * 64)
    assert doc.elements[0].metadata == {}


def test_parse_empty_file_emits_warning(tmp_path: Path):
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    doc = TextParser().parse(p, source_hash="0" * 64)
    assert doc.elements == []
    assert any(w.code == "text_no_content" for w in doc.warnings)


def test_parse_only_blank_lines_emits_warning(tmp_path: Path):
    p = tmp_path / "blank.txt"
    p.write_text("\n\n\n", encoding="utf-8")
    doc = TextParser().parse(p, source_hash="0" * 64)
    assert doc.elements == []
    assert any(w.code == "text_no_content" for w in doc.warnings)


def test_parse_metadata_text_true(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = TextParser().parse(p, source_hash="0" * 64)
    assert doc.metadata == {"text": True}


def test_parse_document_default_lists_empty(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = TextParser().parse(p, source_hash="0" * 64)
    assert doc.chunks == []
    assert doc.relations == []
    assert doc.errors == []


def test_parse_returns_document_instance(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc = TextParser().parse(p, source_hash="0" * 64)
    assert isinstance(doc, Document)


def test_parse_crlf_file(tmp_path: Path):
    """CRLF 文件应被正确处理。"""
    p = tmp_path / "x.txt"
    p.write_bytes(b"line1\r\n\r\nline2")
    doc = TextParser().parse(p, source_hash="0" * 64)
    assert len(doc.elements) == 2


def test_parse_invalid_utf8_falls_back_to_replace(tmp_path: Path):
    """非法 UTF-8 字节 → errors=replace。"""
    p = tmp_path / "x.txt"
    p.write_bytes(b"hello \xff\xfe world")
    doc = TextParser().parse(p, source_hash="0" * 64)
    # 不抛异常，至少有 1 个 element
    assert len(doc.elements) >= 1


# =========================================================================
# 错误路径
# =========================================================================


def test_parse_missing_file_raises(tmp_path: Path):
    missing = tmp_path / "missing.txt"
    with pytest.raises(ParserError) as exc:
        TextParser().parse(missing, source_hash="0" * 64)
    assert exc.value.code == "file_not_found"


def test_parse_unsupported_suffix_raises(tmp_path: Path):
    p = tmp_path / "x.pdf"
    p.write_text("hello", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        TextParser().parse(p, source_hash="0" * 64)
    assert exc.value.code == "unsupported_type"


def test_parse_oserror_raises_read_failed(tmp_path: Path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")

    def _raise(self, *args, **kwargs):
        raise OSError("simulated")

    monkeypatch.setattr(Path, "read_text", _raise)
    with pytest.raises(ParserError) as exc:
        TextParser().parse(p, source_hash="0" * 64)
    assert exc.value.code == "text_read_failed"


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_only_text_parser():
    from app.parsers.text_parser import __all__
    assert __all__ == ["TextParser"]


def test_module_imports_path():
    import app.parsers.text_parser as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import app.parsers.text_parser as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_document():
    import app.parsers.text_parser as mod
    src = inspect.getsource(mod)
    assert "Document" in src


def test_module_imports_parser_base():
    import app.parsers.text_parser as mod
    src = inspect.getsource(mod)
    assert "from app.parsers.base import" in src


def test_module_uses_future_annotations():
    import app.parsers.text_parser as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import app.parsers.text_parser as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_paragraph():
    import app.parsers.text_parser as mod
    assert "段落" in mod.__doc__ or "paragraph" in mod.__doc__.lower()


def test_module_docstring_mentions_utf8():
    import app.parsers.text_parser as mod
    assert "utf" in mod.__doc__.lower()


# =========================================================================
# 签名深度
# =========================================================================


def test_detect_text_source_type_signature_one_param():
    sig = inspect.signature(_detect_text_source_type)
    assert len(sig.parameters) == 1


def test_split_paragraphs_signature_one_param():
    sig = inspect.signature(_split_paragraphs)
    assert len(sig.parameters) == 1


def test_text_parser_parse_signature_three_params():
    sig = inspect.signature(TextParser.parse)
    # self, path, source_hash
    assert len(sig.parameters) == 3


def test_text_parser_parse_no_defaults():
    sig = inspect.signature(TextParser.parse)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


# =========================================================================
# 综合行为
# =========================================================================


def test_text_parser_uses_make_document_id(tmp_path: Path):
    """不同 source_hash → 不同 document_id。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc1 = TextParser().parse(p, source_hash="0" * 64)
    doc2 = TextParser().parse(p, source_hash="1" * 64)
    assert doc1.document_id != doc2.document_id


def test_text_parser_no_content_warning_details(tmp_path: Path):
    """text_no_content warning 的 reason 字段非空。"""
    p = tmp_path / "x.txt"
    p.write_text("", encoding="utf-8")
    doc = TextParser().parse(p, source_hash="0" * 64)
    w = next(w for w in doc.warnings if w.code == "text_no_content")
    assert w.reason


def test_text_parser_does_not_mutate_input_file(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello\n\nworld", encoding="utf-8")
    content_before = p.read_text(encoding="utf-8")
    TextParser().parse(p, source_hash="0" * 64)
    assert p.read_text(encoding="utf-8") == content_before
